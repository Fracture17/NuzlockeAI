// Bucket solver Task 4 tests: BreakpointRegistry + Bucket core.
// Tests written BEFORE implementation; each names the exact behaviour it locks in.
//
// Coverage:
//   1. Sitrus (odd max HP) — boundary matches hp_thresholds; partition contains no
//      interior breakpoints; segment_of round-trips every hp in [0, max_hp].
//   2. Question keepHp inserts a boundary on the player axis.
//   3. residual_unknown (Lum Berry holder) → instantiate throws.
//   4. Full-HP boundary present even when current HP < max (anti-gating).
//   5. Merge same d+support (adjacent intervals) merges; different d does not.
//   6. classify_bucket: opp interval {0} + player alive → WIN; keepHp-straddling
//      bucket construction throws.
//   7. Concrete-consistency sweep: ≥20 sampled HPs in a classified bucket agree
//      with concrete classify().
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/breakpoints.h"
#include "solver/bucket/bucket.h"
#include "solver/engine_queries.h"
#include "solver/question.h"
#include "solver/state_codec.h"
#include "state.h"

#include <algorithm>
#include <set>
#include <stdexcept>

// ---------------------------------------------------------------------------
// Helpers — hand-built 1v1 states (mirrors test_bucket_replay.cpp pattern).
// ---------------------------------------------------------------------------

static PokemonState make_mon(int32_t species, int32_t max_hp, int32_t hp,
                             int32_t item, int32_t ability, int32_t speed = 80,
                             int32_t move0 = 33) {
    PokemonState p{};
    p.species    = species;
    p.level      = 50;
    p.has_stats  = true;
    p.stat_hp    = max_hp; p.stat_atk = 100; p.stat_def = 80;
    p.stat_spa   = 80;     p.stat_spd = 80;  p.stat_spe = speed;
    p.has_max_hp = true;   p.max_hp   = max_hp;
    p.has_hp     = true;   p.hp       = hp;
    p.move_id0   = move0;  p.move_pp0 = 35;
    p.item       = item;
    p.ability    = ability;
    return p;
}

static BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

// Standard Question: default (requireOppFaint=true, requireNoFaint=true, no keepHp).
static Question default_question() {
    Question q;
    return q;
}

// ---------------------------------------------------------------------------
// Test 1: Instantiate on a hand-built Sitrus holder with ODD max HP.
//   - Sitrus half-HP boundary equals hp_thresholds() output exactly (floor(max/2)).
//   - Partition contains no interior breakpoints.
//   - segment_of round-trips every hp in [0, max_hp].
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: instantiate Sitrus with odd max_hp matches hp_thresholds exactly",
          "[bucket][breakpoints]")
{
    static constexpr int32_t ITEM_SITRUS = 158;
    static constexpr int32_t ODD_MAX = 201;   // odd, exercises floor(201/2)=100

    PokemonState p = make_mon(1, ODD_MAX, ODD_MAX, ITEM_SITRUS, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());

    // Sitrus half-HP threshold: hp_thresholds returns floor(201/2) = 100.
    HpThresholds th = hp_thresholds(s, 0);
    int32_t expected_sitrus = -1;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::Half) { expected_sitrus = t.threshold_hp; break; }
    }
    REQUIRE(expected_sitrus == 100);

    // Player-axis breakpoints must contain 0, max_hp, and the Sitrus threshold.
    const std::vector<int32_t>& pl_bps = bp.player_breakpoints();
    REQUIRE(std::find(pl_bps.begin(), pl_bps.end(), 0) != pl_bps.end());
    REQUIRE(std::find(pl_bps.begin(), pl_bps.end(), ODD_MAX) != pl_bps.end());
    REQUIRE(std::find(pl_bps.begin(), pl_bps.end(), expected_sitrus) != pl_bps.end());

    // Breakpoints must be sorted ascending and unique.
    for (size_t i = 1; i < pl_bps.size(); ++i) {
        REQUIRE(pl_bps[i-1] < pl_bps[i]);
    }

    // Partition contains no interior breakpoints — validate that every non-singleton
    // segment lies strictly between two consecutive breakpoints (or against 0/max_hp).
    const std::vector<HpSegment>& segs = bp.player_segments();
    REQUIRE_FALSE(segs.empty());
    for (const HpSegment& seg : segs) {
        REQUIRE(seg.lo <= seg.hi);
        if (seg.lo != seg.hi) {
            // Non-singleton: no breakpoint may fall in [seg.lo, seg.hi].
            for (int32_t b : pl_bps) {
                REQUIRE_FALSE((b >= seg.lo && b <= seg.hi));
            }
        }
    }

    // segment_of must round-trip every HP in [0, max_hp].
    for (int32_t hp = 0; hp <= ODD_MAX; ++hp) {
        int idx = bp.player_segment_of(hp);
        REQUIRE(idx >= 0);
        REQUIRE(idx < static_cast<int>(segs.size()));
        REQUIRE(segs[idx].lo <= hp);
        REQUIRE(hp <= segs[idx].hi);
    }
}

// ---------------------------------------------------------------------------
// Test 2: Question with keepHp = 30 inserts a boundary at 30 on the player axis.
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: Question keepHp inserts a player-axis boundary",
          "[bucket][breakpoints]")
{
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    Question q;
    q.keepHp = 30;

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, q);

    const std::vector<int32_t>& pl_bps = bp.player_breakpoints();
    REQUIRE(std::find(pl_bps.begin(), pl_bps.end(), 30) != pl_bps.end());
}

// ---------------------------------------------------------------------------
// Test 3: residual_unknown state (Lum Berry holder) → instantiate throws.
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: residual_unknown holder causes instantiate to throw",
          "[bucket][breakpoints][fail_loud]")
{
    static constexpr int32_t ITEM_LUM = 157;   // status-cure berry, marked unknown

    PokemonState p = make_mon(1, 200, 200, ITEM_LUM, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    // Sanity: hp_thresholds must flag residual_unknown for this state.
    HpThresholds th = hp_thresholds(s, 0);
    REQUIRE(th.residual_unknown);

    BreakpointRegistry reg;
    REQUIRE_THROWS_AS(reg.instantiate(s, default_question()), std::runtime_error);
}

// ---------------------------------------------------------------------------
// Test 4: Full-HP boundary present even when current HP < max (anti-gating).
// hp_thresholds only emits full-HP entries when currently at full, but the
// max_hp breakpoint must always be present because recovery / Sash / Sturdy /
// Multiscale semantics all pivot on it.
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: max_hp is always a boundary even when current HP is below max",
          "[bucket][breakpoints][anti_gating]")
{
    PokemonState p = make_mon(1, 200, 120, 0, 0);   // 120 < 200
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());

    const std::vector<int32_t>& pl_bps = bp.player_breakpoints();
    REQUIRE(std::find(pl_bps.begin(), pl_bps.end(), 200) != pl_bps.end());

    // Same on the opponent axis.
    const std::vector<int32_t>& op_bps = bp.opp_breakpoints();
    REQUIRE(std::find(op_bps.begin(), op_bps.end(), 200) != op_bps.end());
}

// ---------------------------------------------------------------------------
// Test 5: Merge behavior.
//   Same d + support fingerprint, adjacent player intervals, equal opp intervals
//     → merged with union interval.
//   Same intervals but different d → NOT merged.
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: merge unions adjacent same-d buckets, rejects different-d",
          "[bucket][merge]")
{
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());

    ContextInterner interner;

    // Build a d-key from the healthy state; opp is alive so classify won't be WIN,
    // just ensures both buckets share d. Use a player-axis segment that admits at
    // least two adjacent sub-intervals with no interior breakpoint (a segment
    // strictly between consecutive breakpoints).
    // Pick a segment safely away from any breakpoint (e.g. inside 101..199 for
    // max_hp=200 with Sitrus off). No Sitrus here → breakpoints are {0, 200}.
    // Segment [1, 199] contains no interior breakpoints, so any sub-interval works.
    HpInterval p_lo{50, 100};
    HpInterval p_hi{101, 150};        // adjacent to p_lo (hi = lo-1 boundary)
    HpInterval o_iv{100, 150};

    uint32_t d1 = interner.pack(s) >> 32;  // extract ctx_id via helper

    Bucket a(d1, p_lo, o_iv, /*support_fp=*/1234u, bp);
    Bucket b(d1, p_hi, o_iv, /*support_fp=*/1234u, bp);

    // Same d, same support, adjacent player intervals, equal opp intervals: merge.
    auto merged_opt = try_merge(a, b);
    REQUIRE(merged_opt.has_value());
    REQUIRE(merged_opt->player_hp().lo == 50);
    REQUIRE(merged_opt->player_hp().hi == 150);
    REQUIRE(merged_opt->opp_hp().lo == o_iv.lo);
    REQUIRE(merged_opt->opp_hp().hi == o_iv.hi);

    // Different d: build a burned player state — burn status changes d.
    static constexpr int32_t STATUS_BURN = 4;
    PokemonState p_burn = p;
    p_burn.status = STATUS_BURN;
    BattleState s_burn = make_state(p_burn, o);
    uint32_t d2 = interner.pack(s_burn) >> 32;
    REQUIRE(d1 != d2);

    // Re-instantiate breakpoints under the burned state (may or may not differ, but
    // we only need consistent segments for construction).
    BpSet bp2 = reg.instantiate(s_burn, default_question());
    Bucket c(d2, p_hi, o_iv, /*support_fp=*/1234u, bp2);

    // Different d → merge rejected.
    auto merged_diff_d = try_merge(a, c);
    REQUIRE_FALSE(merged_diff_d.has_value());
}

// ---------------------------------------------------------------------------
// Test 6a: classify_bucket — opp interval entirely {0}, player alive → WIN under
// default Question (requireOppFaint=true, requireNoFaint=true).
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: classify_bucket WIN when opp interval == {0} and player alive",
          "[bucket][classify]")
{
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 0, 0, 0, 60);  // opp already at 0 for context
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    ContextInterner interner;
    uint32_t d = interner.pack(s) >> 32;

    // Player alive interval (well away from breakpoints), opp singleton at 0.
    HpInterval p_iv{100, 150};
    HpInterval o_iv{0, 0};

    Bucket b(d, p_iv, o_iv, /*support_fp=*/0u, bp);

    REQUIRE(classify_bucket(b, default_question(), interner) == Outcome::WIN);
}

// ---------------------------------------------------------------------------
// Test 6b: Bucket construction throws when an interval straddles a breakpoint
// (keepHp = 30 introduces a player-axis breakpoint at 30; interval [25, 35]
// contains that breakpoint strictly interior).
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: Bucket construction throws when interval straddles a breakpoint",
          "[bucket][fail_loud]")
{
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    Question q;
    q.keepHp = 30;

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, q);
    ContextInterner interner;
    uint32_t d = interner.pack(s) >> 32;

    HpInterval o_iv{100, 150};
    HpInterval straddle{25, 35};   // strictly contains keepHp=30

    REQUIRE_THROWS_AS(Bucket(d, straddle, o_iv, /*support_fp=*/0u, bp),
                      std::runtime_error);
}

// ---------------------------------------------------------------------------
// Test 7: Concrete-consistency — sampled concrete states inside a WIN-classified
// bucket must all classify() to WIN (agrees with question.h's concrete classifier).
// ---------------------------------------------------------------------------

TEST_CASE("bucket core: classify_bucket agrees with concrete classify on sampled points",
          "[bucket][classify][consistency]")
{
    // Build a state whose bucket is unambiguously WIN under default Question:
    //   - opp at HP 0 (fainted)
    //   - player alive across a range on the player axis
    // Materialize each sampled (pl_hp, opp_hp=0) via the interner and check concrete.
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 0, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    ContextInterner interner;
    PackedKey seed_key = interner.pack(s);
    uint32_t d = static_cast<uint32_t>(seed_key >> 32);

    HpInterval p_iv{50, 199};        // 150 sample points available
    HpInterval o_iv{0, 0};

    Bucket b(d, p_iv, o_iv, /*support_fp=*/0u, bp);
    Outcome bucket_v = classify_bucket(b, default_question(), interner);
    REQUIRE(bucket_v == Outcome::WIN);

    // Sample ≥20 concrete HP values inside the bucket and verify agreement.
    constexpr int N_SAMPLES = 25;
    int step = (p_iv.hi - p_iv.lo) / (N_SAMPLES - 1);
    if (step < 1) step = 1;
    int checked = 0;
    for (int32_t hp = p_iv.lo; hp <= p_iv.hi && checked < N_SAMPLES; hp += step) {
        PackedKey k = make_packed_key(d,
                                      static_cast<uint16_t>(hp),
                                      static_cast<uint16_t>(o_iv.lo));
        BattleState concrete = interner.unpack(k);
        // The concrete classifier requires opp actually fainted; unpack sets hp=0,
        // but classify() reads .fainted OR hp<=0, so opp with hp=0 counts as fainted.
        Outcome concrete_v = classify(concrete, default_question());
        REQUIRE(concrete_v == bucket_v);
        ++checked;
    }
    REQUIRE(checked >= 20);
}
