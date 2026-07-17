// PP-canonicalization tests (PP-canon Tasks 1+2), written BEFORE the implementation.
// File-local 1v1 state helpers duplicate test_bucket_win_solver.cpp per that file's
// "deliberately not shared" convention.
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "ai_shared.h"                     // MOVE_TABLE, MoveData (behavioral cross-check)
#include "effects.h"                       // PendingSwitch
#include "move_exec.h"                     // cpp_execute_action, ExecAction, DamageLoopLuck
#include "move_exec_guards.h"              // ExecCtx
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/expand.h"
#include "solver/bucket/pp_canon.h"
#include "solver/bucket/transition_cache.h"
#include "solver/bucket/win_solver.h"
#include "solver/state_codec.h"
#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <stdexcept>
#include <vector>

// ===========================================================================
// Move ids (mirror effects.cpp apply_recovery_move + common non-heal moves).
// ===========================================================================
namespace {

constexpr int32_t MV_TACKLE   = 33;
constexpr int32_t MV_TOXIC    = 92;
constexpr int32_t MV_PROTECT  = 182;
constexpr int32_t MV_GIGA_DRAIN = 202;
constexpr int32_t MV_SPLASH   = 150;
constexpr int32_t AB_SHELL_ARMOR = 75;

// Curated pure self-heal ids (== is_cycle_capable_move truth set).
const int32_t kSelfHealIds[] = {
    105 /*Recover*/, 135 /*Soft-Boiled*/, 208 /*Milk Drink*/, 303 /*Slack Off*/,
    456 /*Heal Order*/, 355 /*Roost*/, 234 /*Moonlight*/, 235 /*Morning Sun*/,
    236 /*Synthesis*/, 659 /*Shore Up*/, 791 /*Life Dew*/, 273 /*Wish*/,
    256 /*Swallow*/, 668 /*Strength Sap*/, 156 /*Rest*/,
};

}  // namespace

// ===========================================================================
// Task 1 — classification
// ===========================================================================

TEST_CASE("pp_canon: curated self-heal moves classify as cycle-capable", "[pp_canon]") {
    for (int32_t id : kSelfHealIds) {
        INFO("self-heal move id " << id);
        REQUIRE(is_cycle_capable_move(id));
    }
}

TEST_CASE("pp_canon: attack/status/drain moves are not cycle-capable", "[pp_canon]") {
    REQUIRE_FALSE(is_cycle_capable_move(MV_TACKLE));
    REQUIRE_FALSE(is_cycle_capable_move(MV_TOXIC));
    REQUIRE_FALSE(is_cycle_capable_move(MV_PROTECT));
    REQUIRE_FALSE(is_cycle_capable_move(MV_GIGA_DRAIN));   // drain excluded (heals via damage)
    REQUIRE_FALSE(is_cycle_capable_move(0));               // empty slot
}

// ===========================================================================
// Task 1 — canonicalize_pp rewrite rules
// ===========================================================================
namespace {

// Minimal single mon with move (id,pp) in slots 0..1.
PokemonState canon_mon(int32_t m0, int32_t pp0, int32_t m1 = 0, int32_t pp1 = 0,
                       int32_t item = 0) {
    PokemonState p{};
    p.species = 1; p.level = 50; p.has_stats = true;
    p.stat_hp = 100; p.stat_atk = 60; p.stat_def = 60; p.stat_spa = 60;
    p.stat_spd = 60; p.stat_spe = 60;
    p.has_max_hp = true; p.max_hp = 100; p.has_hp = true; p.hp = 100;
    p.move_id0 = m0; p.move_pp0 = pp0; p.move_id1 = m1; p.move_pp1 = pp1;
    p.item = item;
    return p;
}

BattleState canon_state(const PokemonState& a, const PokemonState& b) {
    BattleState s{};
    s.side0.team.push_back(a); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(b); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

}  // namespace

TEST_CASE("pp_canon: masked slot pp>0 -> sentinel, pp==0 -> 0", "[pp_canon]") {
    // slot0 Tackle pp=7 (masked), slot1 Recover pp=6 (cycle-capable, preserved).
    BattleState s = canon_state(canon_mon(MV_TACKLE, 7, 105 /*Recover*/, 6),
                                canon_mon(MV_TACKLE, 0, MV_SPLASH, 12));
    canonicalize_pp(s);

    REQUIRE(s.side0.team[0].move_pp0 == kPpSentinel);   // masked attack, was 7
    REQUIRE(s.side0.team[0].move_pp1 == 6);             // Recover preserved
    REQUIRE(s.side1.team[0].move_pp0 == 0);             // masked, was 0 -> stays 0
    REQUIRE(s.side1.team[0].move_pp1 == kPpSentinel);   // masked Splash, was 12
}

TEST_CASE("pp_canon: canonicalize_pp is idempotent", "[pp_canon]") {
    BattleState once = canon_state(canon_mon(MV_TACKLE, 7, 105, 6),
                                   canon_mon(MV_SPLASH, 12, 0, 0));
    canonicalize_pp(once);
    BattleState twice = once;
    canonicalize_pp(twice);

    REQUIRE(twice.side0.team[0].move_pp0 == once.side0.team[0].move_pp0);
    REQUIRE(twice.side0.team[0].move_pp1 == once.side0.team[0].move_pp1);
    REQUIRE(twice.side1.team[0].move_pp0 == once.side1.team[0].move_pp0);
}

TEST_CASE("pp_canon: states differing only in masked pp become one context", "[pp_canon]") {
    // Two states differ only in masked slot0 (attack) nonzero PP.
    BattleState a = canon_state(canon_mon(MV_TACKLE, 20, MV_SPLASH, 15),
                                canon_mon(MV_TACKLE, 30, 0, 0));
    BattleState b = canon_state(canon_mon(MV_TACKLE, 5, MV_SPLASH, 3),
                                canon_mon(MV_TACKLE, 30, 0, 0));
    canonicalize_pp(a);
    canonicalize_pp(b);

    ContextInterner interner;
    PackedKey ka = interner.pack(a);
    PackedKey kb = interner.pack(b);
    REQUIRE(ctx_id_of(ka) == ctx_id_of(kb));   // same context id after canonicalization
    REQUIRE(ka == kb);                         // identical HP too => identical packed key
}

TEST_CASE("pp_canon: Leppa holder is masked like any mon (no throw, sentinel applied)",
          "[pp_canon]") {
    constexpr int32_t ITEM_LEPPA_BERRY = 154;   // effects_consts.h
    // Sanity: our constant must actually be the engine's Leppa id; if it changes, the
    // "no special-casing" guarantee below is what matters, not the exact number.
    BattleState s = canon_state(
        canon_mon(MV_TACKLE, 8, 105 /*Recover*/, 4, ITEM_LEPPA_BERRY),
        canon_mon(MV_SPLASH, 10, 0, 0));

    REQUIRE_NOTHROW(canonicalize_pp(s));
    REQUIRE(s.side0.team[0].move_pp0 == kPpSentinel);   // masked despite Leppa
    REQUIRE(s.side0.team[0].move_pp1 == 4);             // Recover still preserved
    REQUIRE(s.side0.team[0].item == ITEM_LEPPA_BERRY);  // item untouched
}

TEST_CASE("pp_canon: turns_in_battle clamps to 5, below-threshold values preserved",
          "[pp_canon]") {
    BattleState s = canon_state(canon_mon(MV_TACKLE, 7), canon_mon(MV_SPLASH, 5));
    s.side0.team[0].turns_in_battle = 37;
    s.side1.team[0].turns_in_battle = 3;
    canonicalize_pp(s);
    REQUIRE(s.side0.team[0].turns_in_battle == 5);   // clamped
    REQUIRE(s.side1.team[0].turns_in_battle == 3);   // below threshold, preserved

    s.side0.team[0].turns_in_battle = 0;
    canonicalize_pp(s);
    REQUIRE(s.side0.team[0].turns_in_battle == 0);   // preserved
}

// ===========================================================================
// Task 1 — behavioral cross-check over the whole move DB (slow).
//
// Probe: a damaged user (hp=1/100) uses each move once against an inert full-HP target.
// Any move that RAISES the user's HP without changing the target's HP (i.e. without
// dealing damage / draining) is a pure immediate self-heal and MUST be cycle-capable.
// Delayed (Wish) / conditional (Swallow) heals do not surface here — they are covered by
// the curated classification test above. Moves that throw (unported Cat-A) are skipped.
// ===========================================================================

TEST_CASE("pp_canon: every immediate self-heal move in the DB is cycle-capable",
          "[pp_canon][slow]") {
    for (int i = 0; i < 813; ++i) {
        int32_t mid = MOVE_TABLE[i].move_id;

        PokemonState user{};
        user.species = 1; user.level = 50; user.has_stats = true;
        user.stat_hp = 100; user.stat_atk = 80; user.stat_def = 80; user.stat_spa = 80;
        user.stat_spd = 80; user.stat_spe = 80;
        user.has_max_hp = true; user.max_hp = 100; user.has_hp = true; user.hp = 1;
        user.move_id0 = mid; user.move_pp0 = 30;

        PokemonState target{};
        target.species = 2; target.level = 50; target.has_stats = true;
        target.stat_hp = 200; target.stat_atk = 80; target.stat_def = 80; target.stat_spa = 80;
        target.stat_spd = 80; target.stat_spe = 60;
        target.has_max_hp = true; target.max_hp = 200; target.has_hp = true; target.hp = 200;
        target.ability = AB_SHELL_ARMOR;
        target.move_id0 = MV_SPLASH; target.move_pp0 = 40;

        BattleState s = canon_state(user, target);

        ExecAction a{};
        a.kind = 0; a.move_slot = 0; a.source_slot = 0; a.target_side = 1; a.target_slot = 0;
        DamageLoopLuck luck_atk{}, luck_def{};
        std::vector<PendingSwitch> pending;
        ExecCtx ctx{};

        int32_t user_before = s.side0.team[0].hp;
        int32_t tgt_before  = s.side1.team[0].hp;
        try {
            cpp_execute_action(s, 0, a, luck_atk, luck_def, pending, ctx, 0);
        } catch (...) {
            continue;   // unported / RNG-gated move — cannot cleanly probe
        }
        int32_t user_after = s.side0.team[0].hp;
        int32_t tgt_after  = s.side1.team[0].hp;

        if (user_after > user_before && tgt_after == tgt_before) {
            INFO("move id " << mid << " healed the user without touching the target");
            REQUIRE(is_cycle_capable_move(mid));
        }
    }
}

// ===========================================================================
// Task 2 — canonical expansion plumbing
//
// File-local 1v1 win_solver helpers (duplicated per convention).
// ===========================================================================
namespace {

struct MonSpec {
    int32_t species = 1;
    int32_t max_hp  = 200;
    int32_t hp      = 200;
    int32_t ability = 0;
    int32_t speed   = 80;
    int32_t move0   = MV_TACKLE;
    int32_t move1   = 0;
    int32_t pp0     = 35;
    int32_t pp1     = 35;
};

PokemonState make_mon(const MonSpec& sp) {
    PokemonState p{};
    p.species = sp.species; p.level = 50; p.has_stats = true;
    p.stat_hp = sp.max_hp; p.stat_atk = 100; p.stat_def = 80; p.stat_spa = 80;
    p.stat_spd = 80; p.stat_spe = sp.speed;
    p.has_max_hp = true; p.max_hp = sp.max_hp;
    p.has_hp = true; p.hp = sp.hp;
    p.move_id0 = sp.move0; p.move_pp0 = sp.move0 ? sp.pp0 : 0;
    p.move_id1 = sp.move1; p.move_pp1 = sp.move1 ? sp.pp1 : 0;
    p.ability = sp.ability;
    return p;
}

BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

// A non-terminal 1v1 root: player Tackle(+Splash) vs inert opponent at op HP 50.
BattleState nonterminal_base(int32_t slot1_pp = 20) {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE,
                               .move1 = MV_SPLASH, .pp1 = slot1_pp});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 50,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
    return make_state(p, o);
}

Bucket child_bucket(const Bucket& A, ExpandContext& ctx, int32_t op) {
    return Bucket(A.d(), A.player_hp(), HpInterval{op, op}, A.support_fp(), *ctx.bp);
}

// R -> single terminal-WIN child (op 0). Root becomes the sole policy-carrying bucket.
ExpandResult win_override(const Bucket& A, const ExecAction& action, ExpandContext& ctx) {
    ExpandResult r;
    r.children.push_back(ChildBucket{child_bucket(A, ctx, 0), action});
    return r;
}

uint32_t root_d(const BucketWinResult& r) {
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.policy.size() == 1);
    return r.policy.begin()->first.d;
}

}  // namespace

// ---------------------------------------------------------------------------
// T2a — root canonicalization: two roots differing only in a masked move's PP.
// ---------------------------------------------------------------------------

TEST_CASE("pp_canon: flag ON collapses masked-PP roots to one context d", "[pp_canon]") {
    BattleState a = nonterminal_base(/*slot1_pp=*/20);   // Splash pp=20 (masked)
    BattleState b = nonterminal_base(/*slot1_pp=*/10);   // Splash pp=10 (masked)

    // Flag ON: shared canonical cache -> identical root d.
    TransitionCache cache_on;
    BucketWinConfig on;
    on.cache = &cache_on;
    on.enable_pp_canon = true;
    on.expand_override = win_override;
    uint32_t da_on = root_d(bucket_win_certify(a, Question{}, on));
    uint32_t db_on = root_d(bucket_win_certify(b, Question{}, on));
    REQUIRE(da_on == db_on);

    // Flag OFF: shared exact cache -> distinct root d (PP differs -> different context).
    TransitionCache cache_off;
    BucketWinConfig off;
    off.cache = &cache_off;
    off.expand_override = win_override;
    uint32_t da_off = root_d(bucket_win_certify(a, Question{}, off));
    uint32_t db_off = root_d(bucket_win_certify(b, Question{}, off));
    REQUIRE(da_off != db_off);
}

// ---------------------------------------------------------------------------
// T2b — cache-mode mismatch: canonical then exact on one cache throws.
// ---------------------------------------------------------------------------

TEST_CASE("pp_canon: mixing canonical and exact on one cache throws", "[pp_canon]") {
    BattleState s = nonterminal_base();
    TransitionCache cache;

    BucketWinConfig canonical;
    canonical.cache = &cache;
    canonical.enable_pp_canon = true;
    canonical.expand_override = win_override;
    (void)bucket_win_certify(s, Question{}, canonical);   // binds cache to Canonical

    BucketWinConfig exact;
    exact.cache = &cache;
    exact.expand_override = win_override;
    REQUIRE_THROWS_AS(bucket_win_certify(s, Question{}, exact), std::logic_error);
}

// ---------------------------------------------------------------------------
// T2c — pp_horizon insurance cap: tiny real PP caps depth below cfg.depth_cap.
// ---------------------------------------------------------------------------

TEST_CASE("pp_canon: pp_horizon caps depth on an endless non-repeating chain",
          "[pp_canon]") {
    // Real root PP total = 1 (player) + 1 (opp) = 2 -> horizon = 10.
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE, .pp0 = 1});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 50,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH,
                               .pp0 = 1});
    BattleState s = make_state(p, o);
    int32_t expected_horizon = pp_horizon(s);
    REQUIRE(expected_horizon == 10);
    // Start op low so the strictly-increasing chain (op+1/turn) never exits [0, max_hp]
    // before the horizon cap fires.
    REQUIRE(50 + expected_horizon <= o.max_hp);

    BucketWinConfig cfg;
    cfg.enable_pp_canon = true;
    cfg.depth_cap = 500;
    // Endless chain: op strictly increases each turn (distinct buckets, never repeats).
    cfg.expand_override = [](const Bucket& A, const ExecAction& action,
                             ExpandContext& ctx) -> ExpandResult {
        ExpandResult r;
        r.children.push_back(ChildBucket{child_bucket(A, ctx, A.opp_hp().hi + 1), action});
        return r;
    };

    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r.verdict == BucketWinVerdict::INDETERMINATE);
    REQUIRE(r.reason == BucketWinIndetReason::DepthCap);
    REQUIRE(r.stats.pp_horizon_used == expected_horizon);
    REQUIRE(r.stats.max_depth <= expected_horizon);
    REQUIRE(r.stats.max_depth < 500);   // horizon, not cfg.depth_cap, bounded the search
}

// ---------------------------------------------------------------------------
// T2d — flag OFF leaves the new counters at 0 and the verdict unchanged.
// ---------------------------------------------------------------------------

TEST_CASE("pp_canon: flag OFF keeps new counters zero and verdict intact", "[pp_canon]") {
    // One-hit kill: non-terminal root -> terminal WIN child, no cycle.
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 5,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    BucketWinResult r = bucket_win_certify(s, Question{});   // default: flag OFF
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.stats.canonical_repeats == 0);
    REQUIRE(r.stats.pp_horizon_used == 0);
}

// ---------------------------------------------------------------------------
// T2e — live cycle detection on a REAL matchup (no expand_override): Splash-vs-Splash
// never faints either side, so the real oracle's turns are pure no-progress loops.
// PP masking alone cannot collapse this (Splash PP is masked either way and every turn
// still advances turns_in_battle); the turns_in_battle clamp is what makes the repeat
// observable. Flag OFF must NOT collapse it (context keeps diverging every turn).
// ---------------------------------------------------------------------------

TEST_CASE("pp_canon: live cycle detection collapses a real Splash-vs-Splash stall",
          "[pp_canon]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_SPLASH, .pp0 = 40});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH,
                               .pp0 = 40});
    BattleState s = make_state(p, o);

    // depth_cap kept well under Splash's real PP (40): without pp_canon, real PP keeps
    // depleting turn-over-turn (no repeat), and past PP exhaustion Struggle's recoil would
    // eventually force a real termination -- this test isolates the CYCLE-COLLAPSE effect,
    // not PP exhaustion, so the cap must fire before Struggle becomes reachable.
    BucketWinConfig on;
    on.enable_pp_canon = true;
    on.depth_cap = 30;
    BucketWinResult r_on = bucket_win_certify(s, Question{}, on);
    REQUIRE(r_on.verdict == BucketWinVerdict::FAIL);
    REQUIRE(r_on.stats.canonical_repeats > 0);
    REQUIRE(r_on.stats.max_depth < 10);   // repeat fires almost immediately, far below the cap

    BucketWinConfig off;
    off.depth_cap = 30;
    BucketWinResult r_off = bucket_win_certify(s, Question{}, off);
    REQUIRE(r_off.verdict == BucketWinVerdict::INDETERMINATE);
    REQUIRE(r_off.reason == BucketWinIndetReason::DepthCap);
    // Flag OFF never collapses -> visits far more buckets than the ON run before capping.
    REQUIRE(r_off.stats.buckets_visited > r_on.stats.buckets_visited * 2);
}
