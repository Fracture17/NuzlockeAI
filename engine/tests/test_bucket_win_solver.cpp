// Bucket solver Task 7 tests: bucket_win_certify DFS core (spec §6). Tests written
// BEFORE implementation. Helpers duplicate test_bucket_expand.cpp conventions (file-local
// statics — deliberately not shared) with MonSpec extended for status / sleep_turns / PP.
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/concede.h"
#include "solver/bucket/expand.h"
#include "solver/bucket/win_solver.h"
#include "solver/engine_queries.h"
#include "solver/question.h"
#include "state.h"

#include <array>
#include <cstdint>
#include <unordered_set>
#include <vector>

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

static constexpr int32_t MV_TACKLE      = 33;
static constexpr int32_t MV_SPLASH      = 150;
static constexpr int32_t MV_SONIC_BOOM  = 49;
static constexpr int32_t MV_RECOVER     = 105;
static constexpr int32_t MV_HYDRO_PUMP  = 56;
static constexpr int32_t MV_FISSURE     = 90;

static constexpr int32_t AB_SHELL_ARMOR = 75;
static constexpr int32_t STATUS_SLEEP   = 6;   // effects_consts.h:64

// ---------------------------------------------------------------------------
// Helpers — hand-built 1v1 states
// ---------------------------------------------------------------------------

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
    int32_t move2   = 0;
    int32_t move3   = 0;
    int32_t pp0     = 35;
    int32_t pp1     = 35;
    int32_t status      = 0;
    int32_t sleep_turns = 0;
};

static PokemonState make_mon(const MonSpec& sp) {
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
    // Empty move slots carry PP 0 so legal_player_actions never enumerates them
    // (mirrors real states — cpp_enumerate_legal_actions filters only on PP > 0).
    p.move_id0   = sp.move0; p.move_pp0 = sp.move0 ? sp.pp0 : 0;
    p.move_id1   = sp.move1; p.move_pp1 = sp.move1 ? sp.pp1 : 0;
    p.move_id2   = sp.move2; p.move_pp2 = sp.move2 ? 35 : 0;
    p.move_id3   = sp.move3; p.move_pp3 = sp.move3 ? 35 : 0;
    p.item        = sp.item;
    p.ability     = sp.ability;
    p.status      = sp.status;
    p.sleep_turns = sp.sleep_turns;
    return p;
}

static BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static ExecAction move_action(int slot, int target_side) {
    ExecAction a{};
    a.kind = 0; a.move_slot = slot;
    a.source_slot = 0; a.target_side = target_side; a.target_slot = 0;
    return a;
}

// True iff any policy entry uses the given move slot.
static bool policy_has_slot(const BucketWinResult& r, int slot) {
    for (const auto& kv : r.policy)
        if (kv.second.move_slot == slot) return true;
    return false;
}

// True iff any policy key matches the given singleton intervals AND move slot.
static bool policy_has_singleton(const BucketWinResult& r, int32_t pl, int32_t op, int slot) {
    for (const auto& kv : r.policy) {
        const BucketKey& k = kv.first;
        if (k.pl_lo == pl && k.pl_hi == pl && k.op_lo == op && k.op_hi == op
            && kv.second.move_slot == slot)
            return true;
    }
    return false;
}

static bool histogram_all_zero(const BucketWinResult& r) {
    for (uint64_t v : r.concession_histogram) if (v != 0) return false;
    return true;
}

// ---------------------------------------------------------------------------
// T1 — trivial WIN.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: trivial one-hit kill certifies WIN with policy", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 5, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    // Precondition: Tackle noncrit min must guarantee the KO (opp hp 5).
    DamageTable dt = damage_table(s, /*attacker=*/0, move_action(0, 1));
    REQUIRE_FALSE(dt.noncrit.empty());
    REQUIRE(dt.noncrit.front() >= 5);

    BucketWinResult r = bucket_win_certify(s, Question{});
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.reason == BucketWinIndetReason::None);
    REQUIRE(policy_has_singleton(r, 200, 5, 0));   // root bucket, Tackle (slot 0)
    REQUIRE(histogram_all_zero(r));
    REQUIRE(r.stats.buckets_visited >= 1);
    REQUIRE(r.stats.expand_calls >= 1);
    REQUIRE(r.stats.replays >= 1);
    REQUIRE(r.stats.max_depth >= 1);
    REQUIRE(r.stats.elapsed_us > 0);
}

// ---------------------------------------------------------------------------
// T2 — guaranteed loss FAIL.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: guaranteed loss returns FAIL, empty policy", "[win_solver]") {
    PokemonState p = make_mon({.hp = 5, .ability = AB_SHELL_ARMOR, .speed = 80,
                               .move0 = MV_SPLASH});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200, .speed = 120,
                               .move0 = MV_TACKLE});
    BattleState s = make_state(p, o);

    // Opp Tackle min roll must KO the player (hp 5).
    DamageTable dt = damage_table(s, /*attacker=*/1, move_action(0, 0));
    REQUIRE_FALSE(dt.noncrit.empty());
    REQUIRE(dt.noncrit.front() >= 5);

    BucketWinResult r = bucket_win_certify(s, Question{});
    REQUIRE(r.verdict == BucketWinVerdict::FAIL);
    REQUIRE(r.reason == BucketWinIndetReason::None);
    REQUIRE(r.policy.empty());
    REQUIRE(histogram_all_zero(r));
}

// ---------------------------------------------------------------------------
// T3 — adaptivity CORE: per-bucket policy split between Sonic Boom and Recover.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: HP-adaptive policy uses both attack and Recover", "[win_solver]") {
    PokemonState p = make_mon({.max_hp = 200, .hp = 200, .ability = AB_SHELL_ARMOR,
                               .speed = 120, .move0 = MV_SONIC_BOOM, .move1 = MV_RECOVER});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 40, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_TACKLE, .move1 = MV_SPLASH,
                               .pp0 = 1});
    BattleState s = make_state(p, o);

    DamageTable dt = damage_table(s, /*attacker=*/1, move_action(0, 0));  // opp Tackle
    REQUIRE_FALSE(dt.noncrit.empty());
    int32_t d_lo = dt.noncrit.front();
    int32_t d_hi = dt.noncrit.back();
    REQUIRE(d_lo < d_hi);

    SECTION("Recover available -> WIN with both slots in policy") {
        Question q;
        q.keepHp = 200 - d_hi + 1;
        BucketWinResult r = bucket_win_certify(s, q);
        REQUIRE(r.verdict == BucketWinVerdict::WIN);
        REQUIRE(policy_has_slot(r, 0));   // Sonic Boom
        REQUIRE(policy_has_slot(r, 1));   // Recover
    }

    SECTION("Recover banned -> not WIN") {
        Question q;
        q.keepHp  = 200 - d_hi + 1;
        q.banMove = 1;   // Recover slot banned
        BucketWinResult r = bucket_win_certify(s, q);
        REQUIRE(r.verdict != BucketWinVerdict::WIN);
    }
}

// ---------------------------------------------------------------------------
// T4 — miss branch is adversarial: FAIL.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: sub-100 accuracy miss branch forces FAIL", "[win_solver]") {
    PokemonState p = make_mon({.hp = 5, .ability = AB_SHELL_ARMOR, .speed = 120,
                               .move0 = MV_HYDRO_PUMP});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 5, .speed = 60,
                               .move0 = MV_TACKLE});
    BattleState s = make_state(p, o);

    BucketWinResult r = bucket_win_certify(s, Question{});
    REQUIRE(r.verdict == BucketWinVerdict::FAIL);
    REQUIRE(histogram_all_zero(r));
}

// ---------------------------------------------------------------------------
// T5 — on-stack repeated bucket = FAIL (via expand override).
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: on-stack repeated bucket is FAIL not INDETERMINATE", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    SECTION("self-loop: child equals parent") {
        BucketWinConfig cfg;
        cfg.expand_override = [](const Bucket& A, const ExecAction& action,
                                 ExpandContext&) -> ExpandResult {
            ExpandResult r;
            r.children.push_back(ChildBucket{A, action});   // child = parent
            return r;
        };
        BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
        REQUIRE(r.verdict == BucketWinVerdict::FAIL);
    }

    SECTION("2-cycle A->B->A") {
        BucketWinConfig cfg;
        cfg.expand_override = [](const Bucket& A, const ExecAction& action,
                                 ExpandContext& ctx) -> ExpandResult {
            // Distinguish A (opp interval != {199,199}) from B (opp {199,199}).
            ExpandResult r;
            if (A.opp_hp().lo == 199) {
                // B -> A: rebuild the original opp interval.
                Bucket back(A.d(), A.player_hp(), HpInterval{200, 200},
                            A.support_fp(), *ctx.bp);
                r.children.push_back(ChildBucket{back, action});
            } else {
                // A -> B: opp interval {199,199}, same d.
                Bucket fwd(A.d(), A.player_hp(), HpInterval{199, 199},
                           A.support_fp(), *ctx.bp);
                r.children.push_back(ChildBucket{fwd, action});
            }
            return r;
        };
        BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
        REQUIRE(r.verdict == BucketWinVerdict::FAIL);
    }
}

// ---------------------------------------------------------------------------
// T6 — depth cap INDETERMINATE.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: depth cap yields INDETERMINATE(DepthCap)", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_SPLASH});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    BucketWinConfig cfg;
    cfg.depth_cap = 5;
    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);
    REQUIRE(r.verdict == BucketWinVerdict::INDETERMINATE);
    REQUIRE(r.reason == BucketWinIndetReason::DepthCap);
    REQUIRE(r.stats.max_depth == 5);
}

// ---------------------------------------------------------------------------
// T7 — concession histogram.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: sleeping player concedes with histogram bit 0", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE,
                               .status = STATUS_SLEEP, .sleep_turns = 2});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 100, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    BucketWinResult r = bucket_win_certify(s, Question{});
    REQUIRE(r.verdict == BucketWinVerdict::FAIL);
    REQUIRE(r.concession_histogram[0] == 1);   // CONCEDE_SLEEP_ACTING == bit 0
    for (size_t i = 1; i < r.concession_histogram.size(); ++i)
        REQUIRE(r.concession_histogram[i] == 0);
    REQUIRE(r.stats.conceded_branches == 1);
    REQUIRE(r.policy.empty());
}

// ---------------------------------------------------------------------------
// T8 — ExpandError propagation to the caller thread.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: ExpandError propagates from worker thread", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_FISSURE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 200, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    bool threw = false;
    try {
        bucket_win_certify(s, Question{});
    } catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::UnsupportedMove);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// T9 — multi-turn WIN telemetry.
// ---------------------------------------------------------------------------

TEST_CASE("win_solver: multi-turn WIN emits depth/leaf telemetry", "[win_solver]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 30, .ability = AB_SHELL_ARMOR,
                               .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    BucketWinResult r = bucket_win_certify(s, Question{});
    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.stats.max_depth >= 2);
    REQUIRE(r.stats.buckets_visited >= 2);
    REQUIRE(r.stats.replays >= r.stats.buckets_visited);
    REQUIRE(r.stats.terminal_buckets >= 1);
    REQUIRE(r.stats.oracle_leaves > 0);
}
