// Bucket solver transition-cache tests (plan Tasks 1+2). Tests written BEFORE the
// implementation. File-local state helpers are duplicated from test_bucket_win_solver.cpp
// per that file's "deliberately not shared" convention (MonSpec etc.).
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/concede.h"
#include "solver/bucket/expand.h"
#include "solver/bucket/transition_cache.h"
#include "solver/bucket/win_solver.h"
#include "solver/engine_queries.h"
#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <vector>

// ===========================================================================
// Task 1 — TransitionCache core
// ===========================================================================

namespace {

BpSet cache_test_bp() {
    return BpSet(std::vector<int32_t>{0, 200}, std::vector<int32_t>{0, 200}, 200, 200);
}

Bucket cache_test_bucket(const BpSet& bp, int32_t pl, int32_t op) {
    return Bucket(0, HpInterval{pl, pl}, HpInterval{op, op}, 0, bp);
}

ExpandResult two_child_result(const BpSet& bp) {
    ExpandResult r;
    ExecAction a{};
    r.children.push_back(ChildBucket{cache_test_bucket(bp, 100, 50), a});
    r.children.push_back(ChildBucket{cache_test_bucket(bp, 100, 40), a});
    return r;
}

EdgeKey base_edge_key() {
    EdgeKey k{};
    k.bucket = BucketKey{5, 10, 20, 30, 40};
    k.bp_fp = 0x1234;
    k.kind = 0;
    k.move_slot = 0;
    k.move_override = -1;
    k.switch_to_slot = -1;
    k.target_side = 1;
    k.target_slot = 0;
    k.source_slot = 0;
    k.mega = false;
    return k;
}

}  // namespace

TEST_CASE("transition_cache: insert/lookup roundtrip and stats", "[transition_cache]") {
    BpSet bp = cache_test_bp();
    TransitionCache cache;
    EdgeKey key = base_edge_key();

    cache.insert(key, two_child_result(bp));
    REQUIRE(cache.entries() == 1);

    const ExpandResult* got = cache.lookup(key);
    REQUIRE(got != nullptr);
    REQUIRE(got->children.size() == 2);
    REQUIRE(cache.stats.hits == 1);
    REQUIRE(cache.stats.misses == 0);

    EdgeKey absent = base_edge_key();
    absent.bucket.d = 999;
    REQUIRE(cache.lookup(absent) == nullptr);
    REQUIRE(cache.stats.hits == 1);
    REQUIRE(cache.stats.misses == 1);
    REQUIRE(cache.entries() == 1);
}

TEST_CASE("transition_cache: duplicate insert throws logic_error", "[transition_cache]") {
    BpSet bp = cache_test_bp();
    TransitionCache cache;
    EdgeKey key = base_edge_key();
    cache.insert(key, two_child_result(bp));
    REQUIRE_THROWS_AS(cache.insert(key, two_child_result(bp)), std::logic_error);
}

TEST_CASE("transition_cache: every discriminating field distinguishes keys",
          "[transition_cache]") {
    BpSet bp = cache_test_bp();
    TransitionCache cache;
    EdgeKey key = base_edge_key();
    cache.insert(key, two_child_result(bp));

    std::vector<EdgeKey> variants;
    auto add = [&](EdgeKey v) { variants.push_back(v); };

    { EdgeKey v = base_edge_key(); v.bucket.d += 1;     add(v); }
    { EdgeKey v = base_edge_key(); v.bucket.pl_lo += 1; add(v); }
    { EdgeKey v = base_edge_key(); v.bucket.pl_hi += 1; add(v); }
    { EdgeKey v = base_edge_key(); v.bucket.op_lo += 1; add(v); }
    { EdgeKey v = base_edge_key(); v.bucket.op_hi += 1; add(v); }
    { EdgeKey v = base_edge_key(); v.bp_fp += 1;        add(v); }
    { EdgeKey v = base_edge_key(); v.move_slot += 1;    add(v); }
    { EdgeKey v = base_edge_key(); v.kind += 1;         add(v); }
    { EdgeKey v = base_edge_key(); v.switch_to_slot += 1; add(v); }
    { EdgeKey v = base_edge_key(); v.mega = true;       add(v); }

    for (const EdgeKey& v : variants)
        REQUIRE(cache.lookup(v) == nullptr);
}

TEST_CASE("transition_cache: bp_fingerprint sensitivity", "[transition_cache]") {
    BpSet a(std::vector<int32_t>{0, 100, 200}, std::vector<int32_t>{0, 50, 200}, 200, 200);
    BpSet a2(std::vector<int32_t>{0, 100, 200}, std::vector<int32_t>{0, 50, 200}, 200, 200);
    REQUIRE(bp_fingerprint(a) == bp_fingerprint(a2));

    BpSet perturb_bp(std::vector<int32_t>{0, 101, 200}, std::vector<int32_t>{0, 50, 200},
                     200, 200);
    REQUIRE(bp_fingerprint(a) != bp_fingerprint(perturb_bp));

    BpSet perturb_hp(std::vector<int32_t>{0, 100, 200}, std::vector<int32_t>{0, 50, 200},
                     201, 200);
    REQUIRE(bp_fingerprint(a) != bp_fingerprint(perturb_hp));

    BpSet swapped(std::vector<int32_t>{0, 50, 200}, std::vector<int32_t>{0, 100, 200},
                  200, 200);
    REQUIRE(bp_fingerprint(a) != bp_fingerprint(swapped));
}

// ===========================================================================
// Task 2 — win_solver integration: edge cache + verdict memo
//
// File-local 1v1 state helpers duplicate test_bucket_win_solver.cpp per that file's
// "deliberately not shared" convention.
// ===========================================================================

namespace {

constexpr int32_t MV_TACKLE   = 33;
constexpr int32_t MV_SPLASH   = 150;
constexpr int32_t MV_RECOVER  = 105;
constexpr int32_t AB_SHELL_ARMOR = 75;

struct MonSpec {
    int32_t species = 1;
    int32_t max_hp  = 200;
    int32_t hp      = 200;
    int32_t item    = 0;
    int32_t ability = 0;
    int32_t speed   = 80;
    int32_t atk     = 100;
    int32_t def     = 80;
    int32_t spa     = 80;
    int32_t spd     = 80;
    int32_t move0   = MV_TACKLE;
    int32_t move1   = 0;
    int32_t pp0     = 35;
    int32_t pp1     = 35;
};

PokemonState make_mon(const MonSpec& sp) {
    PokemonState p{};
    p.species    = sp.species;
    p.level      = 50;
    p.has_stats  = true;
    p.stat_hp    = sp.max_hp;
    p.stat_atk   = sp.atk;
    p.stat_def   = sp.def;
    p.stat_spa   = sp.spa;
    p.stat_spd   = sp.spd;
    p.stat_spe   = sp.speed;
    p.has_max_hp = true;
    p.max_hp     = sp.max_hp;
    p.has_hp     = true;
    p.hp         = sp.hp;
    p.move_id0   = sp.move0; p.move_pp0 = sp.move0 ? sp.pp0 : 0;
    p.move_id1   = sp.move1; p.move_pp1 = sp.move1 ? sp.pp1 : 0;
    p.move_id2   = 0;        p.move_pp2 = 0;
    p.move_id3   = 0;        p.move_pp3 = 0;
    p.item       = sp.item;
    p.ability    = sp.ability;
    return p;
}

BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

ExecAction move_action(int slot, int target_side) {
    ExecAction a{};
    a.kind = 0; a.move_slot = slot;
    a.source_slot = 0; a.target_side = target_side; a.target_slot = 0;
    return a;
}

// A base non-terminal 1v1 state: player Tackle vs inert Shell-Armor opponent at full HP.
BattleState nonterminal_base(int player_moves = 1) {
    MonSpec ps{.hp = 200, .speed = 80, .move0 = MV_TACKLE};
    if (player_moves >= 2) ps.move1 = MV_SPLASH;
    PokemonState p = make_mon(ps);
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
    return make_state(p, o);
}

// Build a same-d child bucket at singleton opp HP `op` (player interval preserved).
Bucket child_bucket(const Bucket& A, ExpandContext& ctx, int32_t op_lo, int32_t op_hi) {
    return Bucket(A.d(), A.player_hp(), HpInterval{op_lo, op_hi}, A.support_fp(), *ctx.bp);
}

Bucket child_bucket(const Bucket& A, ExpandContext& ctx, int32_t op) {
    return child_bucket(A, ctx, op, op);
}

bool all_new_counters_zero(const BucketWinResult& r) {
    return r.stats.edge_hits == 0 && r.stats.edge_misses == 0 && r.stats.memo_hits == 0
        && r.stats.memo_stores == 0 && r.stats.memo_suppressed == 0
        && r.stats.memo_containment_missed == 0;
}

}  // namespace

// ---------------------------------------------------------------------------
// C1 — cross-call edge reuse over a shared cache.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: shared cache reuses edges across certify calls",
          "[transition_cache]") {
    BattleState s = nonterminal_base();

    int override_calls = 0;
    BucketWinConfig cfg;
    TransitionCache cache;
    cfg.cache = &cache;
    // R(op200) -> op100 -> terminal WIN(op0). One player action throughout.
    cfg.expand_override = [&](const Bucket& A, const ExecAction& action,
                              ExpandContext& ctx) -> ExpandResult {
        ++override_calls;
        ExpandResult r;
        int oh = A.opp_hp().hi;
        r.children.push_back(ChildBucket{child_bucket(A, ctx, oh == 200 ? 100 : 0), action});
        return r;
    };

    BucketWinResult r1 = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r1.verdict == BucketWinVerdict::WIN);
    REQUIRE(r1.stats.edge_misses >= 1);
    uint64_t call1_misses = r1.stats.edge_misses;
    int call1_override = override_calls;
    REQUIRE(call1_override > 0);

    override_calls = 0;
    BucketWinResult r2 = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r2.verdict == r1.verdict);
    REQUIRE(r2.stats.edge_misses == 0);
    REQUIRE(r2.stats.edge_hits == call1_misses);
    REQUIRE(override_calls == 0);
    REQUIRE(r2.stats.expand_calls == 0);
}

// ---------------------------------------------------------------------------
// C2 — verdict memo collapses a diamond: X evaluated once, reused via memo.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: verdict memo reuses a shared child in a diamond",
          "[transition_cache]") {
    BattleState s = nonterminal_base();

    int x_expansions = 0;
    BucketWinConfig cfg;
    cfg.expand_override = [&](const Bucket& A, const ExecAction& action,
                              ExpandContext& ctx) -> ExpandResult {
        int oh = A.opp_hp().hi;
        if (oh == 50) ++x_expansions;   // X as input
        ExpandResult r;
        if (oh == 200) {                // R -> AND[B1(100), B2(80)]
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 100), action});
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 80), action});
        } else if (oh == 100 || oh == 80) {   // B1/B2 -> X(50)
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 50), action});
        } else {                        // X(50) -> terminal WIN(0)
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 0), action});
        }
        return r;
    };

    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(x_expansions == 1);         // X expanded once (B2->X served from memo)
    REQUIRE(r.stats.memo_hits >= 1);
}

// ---------------------------------------------------------------------------
// C3 — cycle-contamination soundness: a contaminated FAIL must NOT be memoized.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: contaminated FAIL is not memoized (cycle soundness)",
          "[transition_cache]") {
    BattleState s = nonterminal_base(/*player_moves=*/2);

    int x_slot0_expansions = 0;
    BucketWinConfig cfg;
    // R(op200): AND[A(100), X(50)] in order.
    // A(op100): slot0 -> X(50) ; slot1 -> terminal WIN(0).
    // X(op50): every slot -> A(100).
    cfg.expand_override = [&](const Bucket& A, const ExecAction& action,
                              ExpandContext& ctx) -> ExpandResult {
        int oh = A.opp_hp().hi;
        if (oh == 50 && action.move_slot == 0) ++x_slot0_expansions;
        ExpandResult r;
        if (oh == 200) {                       // R -> AND[A, X]
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 100), action});
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 50), action});
        } else if (oh == 100) {                // A
            if (action.move_slot == 0)
                r.children.push_back(ChildBucket{child_bucket(A, ctx, 50), action});   // -> X
            else
                r.children.push_back(ChildBucket{child_bucket(A, ctx, 0), action});    // WIN
        } else {                               // X(50) -> A
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 100), action});
        }
        return r;
    };

    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r.verdict == BucketWinVerdict::WIN);     // buggy memo would pin FAIL
    REQUIRE(r.stats.memo_suppressed >= 1);           // contaminated X-FAIL withheld
    REQUIRE(x_slot0_expansions == 1);                // X re-reached via an edge hit
}

// ---------------------------------------------------------------------------
// C4 — determinism: cache/memo flags are pure optimizations.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: flags off match defaults on real expansions",
          "[transition_cache]") {
    struct Scenario { BattleState state; Question q; };
    std::vector<Scenario> scenarios;

    // T1: one-hit kill.
    {
        PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
        PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 5,
                                   .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
        scenarios.push_back({make_state(p, o), Question{}});
    }
    // T2: guaranteed loss.
    {
        PokemonState p = make_mon({.hp = 5, .ability = AB_SHELL_ARMOR, .speed = 80,
                                   .move0 = MV_SPLASH});
        PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200, .speed = 120,
                                   .move0 = MV_TACKLE});
        scenarios.push_back({make_state(p, o), Question{}});
    }
    // T3: HP-adaptive Recover WIN.
    {
        PokemonState p = make_mon({.max_hp = 200, .hp = 200, .ability = AB_SHELL_ARMOR,
                                   .speed = 120, .move0 = 49 /*Sonic Boom*/, .move1 = MV_RECOVER});
        PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 40,
                                   .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_TACKLE,
                                   .move1 = MV_SPLASH, .pp0 = 1});
        BattleState st = make_state(p, o);
        DamageTable dt = damage_table(st, /*attacker=*/1, move_action(0, 0));
        Question q; q.keepHp = 200 - dt.noncrit.back() + 1;
        scenarios.push_back({st, q});
    }
    // T9: multi-turn WIN.
    {
        PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
        PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 30,
                                   .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
        scenarios.push_back({make_state(p, o), Question{}});
    }

    for (const Scenario& sc : scenarios) {
        BucketWinResult def = bucket_win_certify(sc.state, sc.q);

        BucketWinConfig off;
        off.enable_edge_cache   = false;
        off.enable_verdict_memo = false;
        BucketWinResult flags_off = bucket_win_certify(sc.state, sc.q, off);

        REQUIRE(flags_off.verdict == def.verdict);
        REQUIRE(flags_off.reason == def.reason);
        REQUIRE(flags_off.policy.empty() == def.policy.empty());
        REQUIRE(all_new_counters_zero(flags_off));
    }
}

// ---------------------------------------------------------------------------
// C5 — self-loop FAIL is legitimately memoized and stable across shared-cache calls.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: self-loop stays FAIL across shared-cache calls",
          "[transition_cache]") {
    BattleState s = nonterminal_base();

    BucketWinConfig cfg;
    TransitionCache cache;
    cfg.cache = &cache;
    cfg.expand_override = [](const Bucket& A, const ExecAction& action,
                             ExpandContext&) -> ExpandResult {
        ExpandResult r;
        r.children.push_back(ChildBucket{A, action});   // child == parent (self-loop)
        return r;
    };

    BucketWinResult r1 = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r1.verdict == BucketWinVerdict::FAIL);

    BucketWinResult r2 = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r2.verdict == BucketWinVerdict::FAIL);
}

// ---------------------------------------------------------------------------
// C6 — rectangle-containment counter fires on a strict sub-rectangle exact miss.
// ---------------------------------------------------------------------------

TEST_CASE("transition_cache: containment counter flags a covered sub-rectangle",
          "[transition_cache]") {
    BattleState s = nonterminal_base();

    BucketWinConfig cfg;
    // R -> AND[Wide, Narrow] (same d). Wide is a wide rectangle memoized WIN; Narrow is a
    // strict sub-rectangle at the same d (exact-key miss) -> containment counter.
    cfg.expand_override = [&](const Bucket& A, const ExecAction& action,
                              ExpandContext& ctx) -> ExpandResult {
        ExpandResult r;
        int oh = A.opp_hp().hi;
        if (oh == 200) {                 // R -> AND[Wide, Narrow] (rectangle on the opp axis)
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 50, 150), action});
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 80, 120), action});
        } else {                         // Wide / Narrow -> terminal WIN(op 0)
            r.children.push_back(ChildBucket{child_bucket(A, ctx, 0), action});
        }
        return r;
    };

    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.stats.memo_containment_missed >= 1);
}
