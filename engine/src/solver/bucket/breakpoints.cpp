// BpSet + BreakpointRegistry implementation. Delegates HP-threshold discovery to
// hp_thresholds(); adds mandatory {0, max_hp} boundaries and the Question's HP
// boundaries. Fails loud when hp_thresholds() reports residual_unknown.
#include "solver/bucket/breakpoints.h"

#include "solver/bucket/ai_breakpoints.h"
#include "solver/engine_queries.h"

#include "damage.h"              // cpp_effective_stat
#include "effects_internal.h"    // eff_internal::has_type, is_grounded
#include "type_chart_lookup.h"   // cpp_type_effectiveness

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
// registry_static_entries — per-mechanic breakpoints (Task 8 §4/§5/§6/§9).
// Source IDs mirrored from damage.cpp, post_hit.cpp, effects.cpp, effects_entry.cpp,
// move_exec_guards.cpp, effects_consts.h. See breakpoints.h for the BpEntryKind table.
// ---------------------------------------------------------------------------

static constexpr int32_t AB_BERSERK          = 201;  // post_hit.cpp:97
static constexpr int32_t AB_EMERGENCY_EXIT   = 194;  // post_hit.cpp:97
static constexpr int32_t AB_WIMP_OUT         = 193;  // post_hit.cpp:97
static constexpr int32_t AB_OVERGROW         = 65;   // damage.cpp:29
static constexpr int32_t AB_BLAZE            = 66;   // damage.cpp:30
static constexpr int32_t AB_TORRENT          = 67;   // damage.cpp:31
static constexpr int32_t AB_SWARM            = 68;   // damage.cpp:32
static constexpr int32_t AB_DEFEATIST        = 129;  // damage.cpp:58
static constexpr int32_t AB_POWER_CONSTRUCT  = 211;  // form-change, postponed (§4)
static constexpr int32_t AB_SCHOOLING        = 208;
static constexpr int32_t AB_SHIELDS_DOWN     = 197;
static constexpr int32_t AB_ZEN_MODE         = 161;
static constexpr int32_t AB_GULP_MISSILE     = 241;
static constexpr int32_t AB_MAGIC_GUARD_BP   = 98;   // effects_consts.h
static constexpr int32_t AB_VOLT_ABSORB      = 10;   // move_exec_guards.cpp:89
static constexpr int32_t AB_WATER_ABSORB     = 11;
static constexpr int32_t AB_DRY_SKIN_BP      = 87;
static constexpr int32_t AB_EARTH_EATER      = 297;

static constexpr int32_t MOVE_BRINE          = 362;  // core_leaf.cpp:53
static constexpr int32_t MOVE_SUBSTITUTE_BP  = 164;  // effects_consts.h:129
static constexpr int32_t MOVE_BELLY_DRUM_BP  = 187;  // effects_consts.h:138
static constexpr int32_t MOVE_CURSE_BP       = 174;  // effects.cpp:1423
static constexpr int32_t MOVE_SWALLOW_BP     = 256;  // effects_consts.h:125
static constexpr int32_t MOVE_HEAL_PULSE_BP  = 505;  // effects_consts.h:125
static constexpr int32_t MOVE_WISH_BP        = 273;  // effects_consts.h:125
static constexpr int32_t MOVE_STRENGTH_SAP_BP= 668;  // effects_consts.h:125
static constexpr int32_t MOVE_LIFE_DEW_BP    = 791;  // effects.cpp:1153
static constexpr int32_t RECOVERY_HALF_BP[10] = {105, 303, 456, 135, 355, 236, 234, 235, 208, 659};

static constexpr int32_t TYPE_GHOST_BP       = 13;   // effects_consts.h:70
static constexpr int32_t TYPE_ROCK_BP        = 12;   // effects_consts.h:70

static constexpr int32_t SC_STEALTH_ROCK_BP  = 4;    // effects_consts.h
static constexpr int32_t SC_SPIKES_1_BP      = 5;
static constexpr int32_t SC_SPIKES_2_BP      = 6;
static constexpr int32_t SC_SPIKES_3_BP      = 7;

static constexpr int32_t ITEM_HEAVY_DUTY_BOOTS_BP = 1120;  // effects_consts.h

static bool knows_move(const PokemonState& mon, int32_t move_id) {
    return mon.move_id0 == move_id || mon.move_id1 == move_id
        || mon.move_id2 == move_id || mon.move_id3 == move_id;
}

static bool is_form_change_ability(int32_t ability) {
    return ability == AB_POWER_CONSTRUCT || ability == AB_SCHOOLING
        || ability == AB_SHIELDS_DOWN || ability == AB_ZEN_MODE
        || ability == AB_GULP_MISSILE;
}

std::vector<BpEntry> registry_static_entries(const BattleState& state, int side) {
    const SideState& own_side = (side == 0) ? state.side0 : state.side1;
    const SideState& opp_side = (side == 0) ? state.side1 : state.side0;
    const PokemonState& own = own_side.team[own_side.active_indices[0]];
    const PokemonState& opp = opp_side.team[opp_side.active_indices[0]];

    if (is_form_change_ability(own.ability)) {
        throw std::runtime_error(
            "registry_static_entries: form-change ability (" + std::to_string(own.ability) +
            ") is out of scope for Task 8 — postponed, not modeled");
    }

    int32_t max_hp = get_max_hp(state, side);
    std::vector<BpEntry> entries;

    // --- §4: crossing/pinch abilities (own axis) ---
    if (own.ability == AB_BERSERK || own.ability == AB_EMERGENCY_EXIT
        || own.ability == AB_WIMP_OUT) {
        entries.push_back({max_hp / 2, BpEntryKind::HalfCrossing});
    }
    if (own.ability == AB_BLAZE || own.ability == AB_TORRENT
        || own.ability == AB_OVERGROW || own.ability == AB_SWARM) {
        entries.push_back({max_hp / 3, BpEntryKind::PinchThird});
    }
    if (own.ability == AB_DEFEATIST) {
        entries.push_back({max_hp / 2, BpEntryKind::DefeatistHalf});
    }

    // --- §5: self-cost moves (own axis) ---
    if (knows_move(own, MOVE_SUBSTITUTE_BP)) {
        entries.push_back({max_hp / 4, BpEntryKind::SubCostQuarter});
    }
    bool ghost_curse = knows_move(own, MOVE_CURSE_BP) && eff_internal::has_type(own, TYPE_GHOST_BP);
    if (knows_move(own, MOVE_BELLY_DRUM_BP) || ghost_curse) {
        entries.push_back({max_hp / 2, BpEntryKind::CostHalf});
    }

    // --- §6: Brine (defender's own axis, keyed off the OTHER side's moveset) ---
    if (knows_move(opp, MOVE_BRINE)) {
        entries.push_back({max_hp / 2, BpEntryKind::BrineHalf});
    }

    // --- §9: heal-cap kinks (own axis, breakpoint = max_hp - heal_amount) ---
    bool is_recovery_move = false;
    for (int32_t m : RECOVERY_HALF_BP) if (m == own.move_id0 || m == own.move_id1
                                            || m == own.move_id2 || m == own.move_id3)
        is_recovery_move = true;
    if (is_recovery_move || knows_move(own, MOVE_LIFE_DEW_BP)) {
        int32_t candidates[3] = {max_hp / 2, max_hp / 4,
                                 (int32_t)((int64_t)max_hp * 2 / 3)};
        for (int32_t c : candidates)
            entries.push_back({max_hp - c, BpEntryKind::HealCapKink});
    }
    if (knows_move(own, MOVE_SWALLOW_BP)) {
        int32_t candidates[2] = {max_hp / 4, max_hp / 2};
        for (int32_t c : candidates)
            entries.push_back({max_hp - c, BpEntryKind::HealCapKink});
    }
    if (knows_move(opp, MOVE_HEAL_PULSE_BP)) {
        entries.push_back({max_hp - max_hp / 2, BpEntryKind::HealCapKink});
    }
    if (knows_move(own, MOVE_STRENGTH_SAP_BP)) {
        // 13 candidates: opponent's effective Atk at stage -6..+6.
        for (int32_t stage = -6; stage <= 6; ++stage) {
            PokemonState opp_at_stage = opp;
            opp_at_stage.stage0 = stage;
            int32_t atk = cpp_effective_stat(opp_at_stage, /*stat_idx=*/1);
            entries.push_back({max_hp - atk, BpEntryKind::HealCapKink});
        }
    }
    if (own.ability == AB_VOLT_ABSORB || own.ability == AB_WATER_ABSORB
        || own.ability == AB_DRY_SKIN_BP || own.ability == AB_EARTH_EATER) {
        entries.push_back({max_hp - max_hp / 4, BpEntryKind::HealCapKink});
    }
    if (knows_move(own, MOVE_WISH_BP)) {
        entries.push_back({max_hp - max_hp / 2, BpEntryKind::HealCapKink});
    }
    if (own_side.has_wish_pending && own_side.wish_hp > 0) {
        entries.push_back({max_hp - own_side.wish_hp, BpEntryKind::HealCapKink});
    }

    // --- §9: entry-hazard kinks (own axis, breakpoint = damage value itself) ---
    auto has_sc = [&](int32_t cond) {
        for (const auto& e : own_side.side_conditions) if (e.condition == cond) return true;
        return false;
    };
    if (has_sc(SC_STEALTH_ROCK_BP) && own.ability != AB_MAGIC_GUARD_BP
        && own.item != ITEM_HEAVY_DUTY_BOOTS_BP) {
        double effv = 1.0;
        for (int32_t t : own.types) effv *= cpp_type_effectiveness(TYPE_ROCK_BP, t);
        int32_t damage = std::max(1, (int32_t)(max_hp * effv / 8.0));
        entries.push_back({damage, BpEntryKind::HazardKink});
    }
    if (eff_internal::is_grounded(own, state) && own.ability != AB_MAGIC_GUARD_BP) {
        int32_t spike_damage = 0;
        if (has_sc(SC_SPIKES_3_BP)) spike_damage = max_hp / 4;
        else if (has_sc(SC_SPIKES_2_BP)) spike_damage = max_hp / 6;
        else if (has_sc(SC_SPIKES_1_BP)) spike_damage = max_hp / 8;
        if (spike_damage > 0) {
            entries.push_back({std::max(1, spike_damage), BpEntryKind::HazardKink});
        }
    }

    return entries;
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

    // Task 8: per-mechanic registry entries (§4-§9). May throw "form-change".
    for (const BpEntry& e : registry_static_entries(state, side)) {
        bps.push_back(e.hp);
    }

    // Task 9: AI-scorer support breakpoints (AI is side 1). May throw
    // "ai-final-gambit" / "ai-bench". Values outside [0,max_hp] are dropped by normalize.
    for (const AiBpEntry& e : ai_breakpoint_entries(state, side)) {
        bps.push_back(e.hp);
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
