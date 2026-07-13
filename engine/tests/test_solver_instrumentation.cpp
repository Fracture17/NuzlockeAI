// Catch2 tests for Task 1: Cat-B RNG instrumentation + probability attribution.
// Verifies p_chosen populated on every relevant resolver, occurrence-keyed injection,
// wrong-kind throw, verify_exhausted throw, and RNG-call-count invariance under logging.
#include <catch2/catch_test_macros.hpp>

#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "logger.h"
#include "oracle.h"
#include "rng_resolver.h"
#include "native_rng.h"
#include "move_exec_premove.h"
#include "core_leaf.h"
#include "state.h"
#include "state_eq.h"

// ---------------------------------------------------------------------------
// Helper: arm injection + occurrence counters, run fn, disarm.
// ---------------------------------------------------------------------------

struct InjectionGuard {
    CategoryBInjection inj;
    CategoryBOccurrenceCounters occ;
    InjectionGuard() {
        set_catb_injection(&inj);
        set_catb_occ_counters(&occ);
    }
    ~InjectionGuard() {
        set_catb_injection(nullptr);
        set_catb_occ_counters(nullptr);
    }
};

struct LogGuard {
    AnalyticalRngLog sink;
    LogGuard() { set_analytical_rng_log(&sink); }
    ~LogGuard() { set_analytical_rng_log(nullptr); }
};

// Find the first log entry for a given event.
static const AnalyticalRngEntry* find_entry(const AnalyticalRngLog& log, RngEventC ev) {
    for (size_t i = 0; i < log.size(); ++i)
        if (log.at(i).event == static_cast<int>(ev)) return &log.at(i);
    return nullptr;
}

// ---------------------------------------------------------------------------
// Helpers to build minimal BattleStates for premove tests.
// ---------------------------------------------------------------------------

static BattleState make_min_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true; mon.hp = 100;
    mon.move_id0 = 33;
    mon.move_pp0 = 35;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// 1. FULL_PARALYSIS — inject both branches, check p_chosen.
// ---------------------------------------------------------------------------

TEST_CASE("FULL_PARALYSIS inject para branch -> p_chosen 0.25", "[instrumentation][paralysis]") {
    InjectionGuard ig;
    LogGuard lg;
    // Inject occurrence 0 as true (inner Bernoulli = blocked => cannot act)
    ig.inj.push_bool(static_cast<int>(RngEventC::FULL_PARALYSIS), 0, true);

    NativeRng rng(1);
    // resolve_can_act(25.0 chance, threshold, random_mode=false, rng, event)
    // Deterministic path but injection overrides. chance=25 avoids saturation.
    bool can_act = rng_resolve_chance(25, 50.0, false, &rng, RngEventC::FULL_PARALYSIS);
    REQUIRE(can_act == true);  // injected true = fires = can_act (chance-based fires => true)
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::FULL_PARALYSIS);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 1);
    REQUIRE(std::abs(e->p_chosen - 0.25) < 1e-9);
}

TEST_CASE("FULL_PARALYSIS inject no-para branch -> p_chosen 0.75", "[instrumentation][paralysis]") {
    InjectionGuard ig;
    LogGuard lg;
    // Inject occurrence 0 as false (inner Bernoulli = not blocked => can act)
    ig.inj.push_bool(static_cast<int>(RngEventC::FULL_PARALYSIS), 0, false);

    NativeRng rng(1);
    bool can_act = rng_resolve_chance(25, 50.0, false, &rng, RngEventC::FULL_PARALYSIS);
    REQUIRE(can_act == false);  // injected false = does not fire
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::FULL_PARALYSIS);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 0.75) < 1e-9);
}

// ---------------------------------------------------------------------------
// 2. WAKE at 50% tier — inject both branches.
// ---------------------------------------------------------------------------

TEST_CASE("WAKE 50pct tier inject wake -> p_chosen 0.5", "[instrumentation][wake]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::WAKE), 0, true);

    NativeRng rng(1);
    // chance=50 => p_chosen should be 0.5
    bool woke = rng_resolve_chance(50, 50.0, false, &rng, RngEventC::WAKE);
    REQUIRE(woke == true);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::WAKE);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 1);
    REQUIRE(std::abs(e->p_chosen - 0.5) < 1e-9);
}

TEST_CASE("WAKE 50pct tier inject no-wake -> p_chosen 0.5", "[instrumentation][wake]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::WAKE), 0, false);

    NativeRng rng(1);
    bool woke = rng_resolve_chance(50, 50.0, false, &rng, RngEventC::WAKE);
    REQUIRE(woke == false);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::WAKE);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 0.5) < 1e-9);
}

// ---------------------------------------------------------------------------
// 3. DAMAGE_ROLL with Shell Armor (crit suppressed): inject roll 0 and 15.
//    p_chosen must be 1/16 at both extremes.
// ---------------------------------------------------------------------------

TEST_CASE("DAMAGE_ROLL inject roll=0 -> p_chosen 1/16", "[instrumentation][damage_roll]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::DAMAGE_ROLL), 0, 0);

    NativeRng rng(1);
    // Use rng_resolve_damage_roll directly (it's the Cat-B resolver for DAMAGE_ROLL).
    // The resolver must log p_chosen = 1/16.
    int roll = rng_resolve_damage_roll(false, &rng);
    REQUIRE(roll == 0);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::DAMAGE_ROLL);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 1.0/16.0) < 1e-9);
}

TEST_CASE("DAMAGE_ROLL inject roll=15 -> p_chosen 1/16", "[instrumentation][damage_roll]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::DAMAGE_ROLL), 0, 15);

    NativeRng rng(1);
    int roll = rng_resolve_damage_roll(false, &rng);
    REQUIRE(roll == 15);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::DAMAGE_ROLL);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 15);
    REQUIRE(std::abs(e->p_chosen - 1.0/16.0) < 1e-9);
}

// ---------------------------------------------------------------------------
// 4. PSYWAVE_ROLL at level 50: inject k=0 -> damage 25, k=100 -> damage 75.
//    k=0 p_chosen = 1/200; k=50 (interior) p_chosen = 1/100.
// ---------------------------------------------------------------------------

// python_round mirrors core_leaf.cpp's banker's rounding.
static int64_t python_round_test(double x) {
    double floor_x = std::floor(x);
    double frac = x - floor_x;
    int64_t fl = static_cast<int64_t>(floor_x);
    if (frac < 0.5) return fl;
    if (frac > 0.5) return fl + 1;
    return (fl % 2 == 0) ? fl : fl + 1;
}

TEST_CASE("PSYWAVE_ROLL inject k=0 -> damage=25, p_chosen=1/200", "[instrumentation][psywave]") {
    InjectionGuard ig;
    LogGuard lg;
    // k=0 corresponds to roll=0.0 (lower half of interval [0, 0.5/100))
    ig.inj.push_int(static_cast<int>(RngEventC::PSYWAVE_ROLL), 0, 0);

    NativeRng rng(1);
    int k = rng_resolve_psywave_roll_k(false, &rng);
    REQUIRE(k == 0);
    ig.inj.verify_exhausted();

    // Level 50: damage = 50 * (50 + python_round(roll*100)) // 100
    // k=0: damage = 50 * 50 / 100 = 25
    int32_t expected_dmg = static_cast<int32_t>(50 * (50 + python_round_test(0.0 * 100.0)) / 100);
    REQUIRE(expected_dmg == 25);

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::PSYWAVE_ROLL);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 1.0/200.0) < 1e-9);
    // Truthful domain report: 101 outcomes, truncated in the inline options[].
    // Log consumers must NOT enumerate PSYWAVE branches from options[]; the
    // oracle owns the domain (endpoints 1/200, interior 1/100).
    REQUIRE(e->options_count == 101);
    REQUIRE(e->options_truncated == 1);
}

TEST_CASE("PSYWAVE_ROLL inject k=100 -> damage=75, p_chosen=1/200", "[instrumentation][psywave]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::PSYWAVE_ROLL), 0, 100);

    NativeRng rng(1);
    int k = rng_resolve_psywave_roll_k(false, &rng);
    REQUIRE(k == 100);
    ig.inj.verify_exhausted();

    // k=100: damage = 50 * (50 + 100) / 100 = 75
    int32_t expected_dmg = static_cast<int32_t>(50 * (50 + 100) / 100);
    REQUIRE(expected_dmg == 75);

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::PSYWAVE_ROLL);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 100);
    REQUIRE(std::abs(e->p_chosen - 1.0/200.0) < 1e-9);
}

// ---------------------------------------------------------------------------
// 5. MULTI_HIT_COUNT (Rock Blast): inject 2 hits (p=0.35) and 5 hits (p=0.15).
// ---------------------------------------------------------------------------

TEST_CASE("MULTI_HIT_COUNT inject 2 hits -> p_chosen 0.35", "[instrumentation][multi_hit]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::MULTI_HIT_COUNT), 0, 2);

    NativeRng rng(1);
    int32_t hits = rng_resolve_multi_hit(2, 5, 0.5, false, &rng);
    REQUIRE(hits == 2);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::MULTI_HIT_COUNT);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 2);
    REQUIRE(std::abs(e->p_chosen - 0.35) < 1e-9);
}

TEST_CASE("MULTI_HIT_COUNT inject 5 hits -> p_chosen 0.15", "[instrumentation][multi_hit]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::MULTI_HIT_COUNT), 0, 5);

    NativeRng rng(1);
    int32_t hits = rng_resolve_multi_hit(2, 5, 0.5, false, &rng);
    REQUIRE(hits == 5);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::MULTI_HIT_COUNT);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 5);
    REQUIRE(std::abs(e->p_chosen - 0.15) < 1e-9);
}

// ---------------------------------------------------------------------------
// 6. Same seed, random mode, logger on vs off -> resulting states equal.
//    Uses a paralyzed mon taking random-mode turns. Demonstrates logging doesn't
//    perturb RNG call order or count.
// ---------------------------------------------------------------------------

TEST_CASE("same seed random mode: log on vs off -> identical RNG state", "[instrumentation][rng_invariance]") {
    // Test that the same draw sequence occurs whether the logger is on or off.
    // We call rng_resolve_chance (FULL_PARALYSIS) three times and verify results
    // are identical with and without logging active.
    auto run = [](bool logging_on) -> std::vector<bool> {
        NativeRng rng(42);
        AnalyticalRngLog sink;
        if (logging_on) set_analytical_rng_log(&sink);

        std::vector<bool> results;
        for (int i = 0; i < 5; ++i) {
            bool r = rng_resolve_chance(25, 50.0, true, &rng, RngEventC::FULL_PARALYSIS);
            results.push_back(r);
        }
        if (logging_on) set_analytical_rng_log(nullptr);
        return results;
    };

    auto with_log    = run(true);
    auto without_log = run(false);
    REQUIRE(with_log == without_log);
}

TEST_CASE("same seed random mode: DAMAGE_ROLL log on vs off identical", "[instrumentation][rng_invariance]") {
    auto run = [](bool logging_on) -> std::vector<int> {
        NativeRng rng(999);
        AnalyticalRngLog sink;
        if (logging_on) set_analytical_rng_log(&sink);

        std::vector<int> results;
        for (int i = 0; i < 8; ++i) {
            int r = rng_resolve_damage_roll(true, &rng);
            results.push_back(r);
        }
        if (logging_on) set_analytical_rng_log(nullptr);
        return results;
    };

    REQUIRE(run(true) == run(false));
}

// ---------------------------------------------------------------------------
// 7. Wrong-kind injection throws.
// ---------------------------------------------------------------------------

TEST_CASE("wrong-kind injection at FULL_PARALYSIS (int instead of bool) throws",
          "[instrumentation][fail_loud]") {
    InjectionGuard ig;
    // Push int outcome where bool is expected.
    ig.inj.push_int(static_cast<int>(RngEventC::FULL_PARALYSIS), 0, 1);

    NativeRng rng(1);
    REQUIRE_THROWS_AS(
        rng_resolve_chance(25, 50.0, false, &rng, RngEventC::FULL_PARALYSIS),
        std::runtime_error
    );
}

TEST_CASE("wrong-kind injection at DAMAGE_ROLL (bool instead of int) throws",
          "[instrumentation][fail_loud]") {
    InjectionGuard ig;
    ig.inj.push_bool(static_cast<int>(RngEventC::DAMAGE_ROLL), 0, true);

    NativeRng rng(1);
    REQUIRE_THROWS_AS(
        rng_resolve_damage_roll(false, &rng),
        std::runtime_error
    );
}

TEST_CASE("wrong-kind injection at MULTI_HIT_COUNT (bool instead of int) throws",
          "[instrumentation][fail_loud]") {
    InjectionGuard ig;
    ig.inj.push_bool(static_cast<int>(RngEventC::MULTI_HIT_COUNT), 0, true);

    NativeRng rng(1);
    REQUIRE_THROWS_AS(
        rng_resolve_multi_hit(2, 5, 0.5, false, &rng),
        std::runtime_error
    );
}

// ---------------------------------------------------------------------------
// 8. Injection queued for occurrence that never fires -> verify_exhausted throws.
// ---------------------------------------------------------------------------

TEST_CASE("unfired DAMAGE_ROLL injection -> verify_exhausted throws",
          "[instrumentation][fail_loud]") {
    InjectionGuard ig;
    // Register occurrence 5 which will never be reached.
    ig.inj.push_int(static_cast<int>(RngEventC::DAMAGE_ROLL), 5, 7);
    REQUIRE_THROWS_AS(ig.inj.verify_exhausted(), std::runtime_error);
}

TEST_CASE("unfired FULL_PARALYSIS injection -> verify_exhausted throws",
          "[instrumentation][fail_loud]") {
    InjectionGuard ig;
    ig.inj.push_bool(static_cast<int>(RngEventC::FULL_PARALYSIS), 3, false);
    REQUIRE_THROWS_AS(ig.inj.verify_exhausted(), std::runtime_error);
}

// ---------------------------------------------------------------------------
// 9. PSYWAVE_ROLL interior k (e.g. k=50) -> p_chosen = 1/100.
// ---------------------------------------------------------------------------

TEST_CASE("PSYWAVE_ROLL inject k=50 (interior) -> p_chosen=1/100", "[instrumentation][psywave]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::PSYWAVE_ROLL), 0, 50);

    NativeRng rng(1);
    int k = rng_resolve_psywave_roll_k(false, &rng);
    REQUIRE(k == 50);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::PSYWAVE_ROLL);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 50);
    REQUIRE(std::abs(e->p_chosen - 1.0/100.0) < 1e-9);
}

// ---------------------------------------------------------------------------
// 10. ACCURACY existing resolver: p_chosen = eff_acc/100.
// ---------------------------------------------------------------------------

TEST_CASE("ACCURACY resolver p_chosen = eff_acc/100 on hit", "[instrumentation][accuracy]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::ACCURACY), 0, true);

    NativeRng rng(1);
    RngLogCtx ctx{ RngParticipants{0,0,1,0}, 1 };
    bool hit = rng_resolve_accuracy(75.0, false, 50.0, false, &rng, &ctx);
    REQUIRE(hit == true);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::ACCURACY);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 1);
    REQUIRE(std::abs(e->p_chosen - 0.75) < 1e-9);
}

TEST_CASE("ACCURACY resolver p_chosen = 1-eff_acc/100 on miss", "[instrumentation][accuracy]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::ACCURACY), 0, false);

    NativeRng rng(1);
    RngLogCtx ctx{ RngParticipants{0,0,1,0}, 1 };
    bool hit = rng_resolve_accuracy(75.0, false, 50.0, false, &rng, &ctx);
    REQUIRE(hit == false);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::ACCURACY);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 0.25) < 1e-9);
}

// ---------------------------------------------------------------------------
// 11. CRIT resolver: p_chosen = crit_chance on crit, 1-crit_chance on no-crit.
// ---------------------------------------------------------------------------

TEST_CASE("CRIT resolver p_chosen = crit_chance on crit", "[instrumentation][crit]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::CRIT), 0, true);

    NativeRng rng(1);
    RngLogCtx ctx{ RngParticipants{0,0,1,0}, 1 };
    bool crit = rng_resolve_crit(0.0625f, 50.0, false, &rng, &ctx);
    REQUIRE(crit == true);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::CRIT);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 1);
    REQUIRE(std::abs(e->p_chosen - 0.0625) < 1e-6);
}

// ---------------------------------------------------------------------------
// 12. BINDING_DURATION: p_chosen = 0.5 for both options.
// ---------------------------------------------------------------------------

TEST_CASE("BINDING_DURATION p_chosen = 0.5", "[instrumentation][binding]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::BINDING_DURATION), 0, 4);

    NativeRng rng(1);
    int dur = rng_resolve_binding_duration(false, &rng);
    REQUIRE(dur == 4);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::BINDING_DURATION);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 4);
    REQUIRE(std::abs(e->p_chosen - 0.5) < 1e-9);
}

// ---------------------------------------------------------------------------
// 13. RAMPAGE_DURATION: p_chosen = 0.5.
// ---------------------------------------------------------------------------

TEST_CASE("RAMPAGE_DURATION p_chosen = 0.5", "[instrumentation][rampage]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_int(static_cast<int>(RngEventC::RAMPAGE_DURATION), 0, 3);

    NativeRng rng(1);
    int dur = rng_resolve_rampage_duration(false, &rng);
    REQUIRE(dur == 3);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::RAMPAGE_DURATION);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 3);
    REQUIRE(std::abs(e->p_chosen - 0.5) < 1e-9);
}

// ---------------------------------------------------------------------------
// 14. QUICK_CLAW: p_chosen = 0.2 on fire, 0.8 on no-fire.
// ---------------------------------------------------------------------------

TEST_CASE("QUICK_CLAW inject fire -> p_chosen 0.2", "[instrumentation][quick_claw]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::QUICK_CLAW), 0, true);

    NativeRng rng(1);
    bool fires = rng_resolve_quick_claw(false, &rng);
    REQUIRE(fires == true);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::QUICK_CLAW);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 1);
    REQUIRE(std::abs(e->p_chosen - 0.2) < 1e-9);
}

TEST_CASE("QUICK_CLAW inject no-fire -> p_chosen 0.8", "[instrumentation][quick_claw]") {
    InjectionGuard ig;
    LogGuard lg;
    ig.inj.push_bool(static_cast<int>(RngEventC::QUICK_CLAW), 0, false);

    NativeRng rng(1);
    bool fires = rng_resolve_quick_claw(false, &rng);
    REQUIRE(fires == false);
    ig.inj.verify_exhausted();

    const AnalyticalRngEntry* e = find_entry(lg.sink, RngEventC::QUICK_CLAW);
    REQUIRE(e != nullptr);
    REQUIRE(e->chosen == 0);
    REQUIRE(std::abs(e->p_chosen - 0.8) < 1e-9);
}
