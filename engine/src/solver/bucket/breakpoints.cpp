// BpSet + BreakpointRegistry implementation. Delegates HP-threshold discovery to
// hp_thresholds(); adds mandatory {0, max_hp} boundaries and the Question's HP
// boundaries. Fails loud when hp_thresholds() reports residual_unknown.
#include "solver/bucket/breakpoints.h"

#include "solver/engine_queries.h"

#include <algorithm>
#include <set>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Get the active mon's max HP for a side (mirrors hp_thresholds internal reading).
static int32_t get_max_hp(const BattleState& state, int side) {
    const SideState& ss = (side == 0) ? state.side0 : state.side1;
    if (ss.active_indices.empty())
        throw std::invalid_argument("breakpoints: side has no active mon");
    const PokemonState& mon = ss.team[ss.active_indices[0]];
    return mon.has_max_hp ? mon.max_hp : (mon.has_stats ? mon.stat_hp : 0);
}

// Sort, dedup, clip breakpoints to [0, max_hp]. Values outside are dropped
// (they cannot be reached and cannot lie strictly inside any bucket in-range).
static std::vector<int32_t> normalize(std::vector<int32_t>& raw, int32_t max_hp) {
    std::set<int32_t> uniq;
    for (int32_t v : raw) {
        if (v < 0 || v > max_hp) continue;
        uniq.insert(v);
    }
    return std::vector<int32_t>(uniq.begin(), uniq.end());
}

// Build the segment partition for one axis given the sorted+deduped breakpoint list.
// Each breakpoint b becomes a singleton segment [b, b]; each maximal run of
// non-breakpoint values in [0, max_hp] becomes a segment [lo, hi] with lo <= hi.
// Emitted in ascending HP order.
static std::vector<HpSegment> build_segments(const std::vector<int32_t>& bps,
                                             int32_t max_hp) {
    std::vector<HpSegment> segs;
    if (max_hp < 0) return segs;

    int32_t cursor = 0;
    for (int32_t b : bps) {
        if (b > cursor) {
            // Gap segment [cursor, b-1].
            segs.push_back({cursor, b - 1});
        }
        // Singleton at the breakpoint (guaranteed b >= cursor here, so b-1 gap above).
        // If b < cursor it means duplicate/out-of-order — normalize already prevents.
        if (b >= cursor) {
            segs.push_back({b, b});
            cursor = b + 1;
        }
    }
    if (cursor <= max_hp) {
        segs.push_back({cursor, max_hp});
    }
    return segs;
}

// Binary search: return the index of the segment containing hp, or -1.
static int segment_of(const std::vector<HpSegment>& segs, int32_t hp) {
    if (segs.empty()) return -1;
    // Segments are strictly non-overlapping and sorted by lo; use lower_bound on hi.
    int lo = 0;
    int hi = static_cast<int>(segs.size()) - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (hp < segs[mid].lo) hi = mid - 1;
        else if (hp > segs[mid].hi) lo = mid + 1;
        else return mid;
    }
    return -1;
}

// Return true iff any breakpoint value lies STRICTLY inside (lo, hi).
static bool has_interior_breakpoint(const std::vector<int32_t>& bps,
                                    int32_t lo, int32_t hi) {
    if (lo >= hi) return false;   // singleton or empty: no strict interior
    // Find first bp > lo.
    auto it = std::upper_bound(bps.begin(), bps.end(), lo);
    if (it == bps.end()) return false;
    return *it < hi;
}

// ---------------------------------------------------------------------------
// BpSet
// ---------------------------------------------------------------------------

BpSet::BpSet(std::vector<int32_t> player_bps, std::vector<int32_t> opp_bps,
             int32_t player_max_hp, int32_t opp_max_hp)
    : player_bps_(std::move(player_bps)),
      opp_bps_(std::move(opp_bps)),
      player_max_hp_(player_max_hp),
      opp_max_hp_(opp_max_hp) {
    player_segs_ = build_segments(player_bps_, player_max_hp_);
    opp_segs_    = build_segments(opp_bps_,    opp_max_hp_);
}

int BpSet::player_segment_of(int32_t hp) const { return segment_of(player_segs_, hp); }
int BpSet::opp_segment_of(int32_t hp) const    { return segment_of(opp_segs_,    hp); }

bool BpSet::player_has_interior_breakpoint(int32_t lo, int32_t hi) const {
    return has_interior_breakpoint(player_bps_, lo, hi);
}
bool BpSet::opp_has_interior_breakpoint(int32_t lo, int32_t hi) const {
    return has_interior_breakpoint(opp_bps_, lo, hi);
}

// ---------------------------------------------------------------------------
// BreakpointRegistry::instantiate
// ---------------------------------------------------------------------------

// Seed one axis with mandatory + Question-derived boundaries and delegate the
// item/ability HP thresholds to hp_thresholds(). Anti-gating requirement (USER):
// max_hp is ALWAYS a boundary regardless of current HP — recovery clamps, Sash /
// Sturdy / Multiscale all pivot on it.
static std::vector<int32_t> seed_axis(const BattleState& state, int side,
                                      int32_t question_hp_boundary) {
    HpThresholds th = hp_thresholds(state, side);
    if (th.residual_unknown) {
        throw std::runtime_error(
            std::string("BreakpointRegistry::instantiate: residual_unknown on side ") +
            std::to_string(side) +
            " — hp_thresholds cannot model this item; fail loud (see plan Task 4)");
    }

    int32_t max_hp = get_max_hp(state, side);

    std::vector<int32_t> bps;
    bps.reserve(th.thresholds.size() + 3);

    // Mandatory boundaries: faint (0) and max_hp — anti-gating: max_hp always present.
    bps.push_back(0);
    if (max_hp > 0) bps.push_back(max_hp);

    // hp_thresholds output (delegated — do NOT re-derive floor arithmetic).
    for (const HpThreshold& t : th.thresholds) {
        bps.push_back(t.threshold_hp);
    }

    // Question HP boundary for this axis (0 = unset).
    if (question_hp_boundary > 0) bps.push_back(question_hp_boundary);

    return normalize(bps, max_hp);
}

BpSet BreakpointRegistry::instantiate(const BattleState& state, const Question& q) const {
    // Question::keepHp applies to the PLAYER (side 0) — see question.h.
    std::vector<int32_t> pl_bps  = seed_axis(state, 0, q.keepHp);
    std::vector<int32_t> opp_bps = seed_axis(state, 1, /*question_hp_boundary=*/0);

    int32_t pl_max  = get_max_hp(state, 0);
    int32_t opp_max = get_max_hp(state, 1);

    return BpSet(std::move(pl_bps), std::move(opp_bps), pl_max, opp_max);
}
