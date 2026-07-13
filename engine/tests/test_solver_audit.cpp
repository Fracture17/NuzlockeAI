// Catch2 tests for Task 8: audit harness logic.
// Inline selfcheck smoke: runs audit_selfcheck() over 10 Uniform matchups — expects zero failures.
// MC smoke tagged [.slow]: runs mc logic over 3 matchups with M=2000.
// Both tests call linkable library functions from solver/audit/audit_core.h — NOT the exe.
#include <catch2/catch_test_macros.hpp>

#include <string>

#include "solver/audit/audit_core.h"

#ifndef NUZLOCKE_REPO_ROOT
#error "NUZLOCKE_REPO_ROOT must be defined at compile time (see CMakeLists.txt)"
#endif

static std::string repo_root() { return NUZLOCKE_REPO_ROOT; }

// ---------------------------------------------------------------------------
// Selfcheck smoke: 10 Uniform matchups, zero failures expected
// ---------------------------------------------------------------------------

TEST_CASE("audit: selfcheck smoke 10 Uniform matchups", "[audit][selfcheck]") {
    AuditSelfcheckConfig cfg;
    cfg.seed     = 42;
    cfg.klass    = "uniform";
    cfg.n        = 10;
    cfg.shard_k  = 0;
    cfg.shard_of = 1;
    cfg.repo_root = repo_root();

    AuditSelfcheckReport report = audit_selfcheck(cfg);

    INFO("total failures: " << report.total_failures);
    INFO("mass_error failures: " << report.reason_histogram[AuditFailReason::MassError]);
    INFO("ordering_mismatch failures: " << report.reason_histogram[AuditFailReason::OrderingMismatch]);
    INFO("child_sanity failures: " << report.reason_histogram[AuditFailReason::ChildSanity]);
    INFO("oracle_threw failures: " << report.reason_histogram[AuditFailReason::OracleThrewException]);

    REQUIRE(report.total_failures == 0);
}

// ---------------------------------------------------------------------------
// MC smoke: 3 Uniform matchups, M=2000 samples — tagged [.slow] so it doesn't
// run by default (Catch2 hidden tag). Run with: nuzlocke_native_tests "[.slow]"
// ---------------------------------------------------------------------------

TEST_CASE("audit: mc smoke 3 Uniform matchups 2000 samples", "[.slow][audit][mc]") {
    AuditMcConfig cfg;
    cfg.seed      = 42;
    cfg.klass     = "uniform";
    cfg.n         = 3;
    cfg.samples   = 2000;
    cfg.repo_root = repo_root();

    AuditMcReport report = audit_mc(cfg);

    INFO("completeness_failures: " << report.completeness_failures);
    INFO("stat_failures: " << report.stat_failures);

    // Completeness holes = worst class; must be zero
    REQUIRE(report.completeness_failures == 0);
    // Statistical failures with M=2000 over 3 matchups: allow none (strong signal)
    REQUIRE(report.stat_failures == 0);
}

// ---------------------------------------------------------------------------
// Regression: Starf-holder matchup (seed=7 uniform index=35).
// The player holds a Starf Berry (item 207). Before the fix, cpp_run_one_turn_solver
// did not thread overrides into the DamageLoopLuck structs, so Starf's check_berry
// (reached via luck.overrides) always saw nullptr → NeedsRNG → pause, no matter how
// many answers the DFS supplied → infinite prefix extension → stack-overflow segfault.
// Also guards the fail-loud MAX_PREFIX_DEPTH check (throws instead of segfaulting).
// ---------------------------------------------------------------------------

#include "solver/matchup_gen.h"
#include "solver/transition_oracle.h"
#include "state.h"
#include "move_exec.h"

#include <cmath>

TEST_CASE("oracle regression: Starf-holder matchup enumerates (seed=7 idx=35 action=3)",
          "[audit][oracle][regression][starf]") {
    MatchupGen::Paths paths{
        repo_root() + "/liveplay/data/generated_learnsets.json",
        repo_root() + "/liveplay/data/generated_abilities.json"};
    MatchupGen gen(7, MatchupGen::Class::Uniform, 0, 1, paths);
    BattleState state{};
    for (int i = 0; i <= 35; ++i) state = gen.next();

    // Sanity: this is the fixture we think it is (player holds Starf = item 207).
    REQUIRE(state.side0.team[0].item == 207);

    ExecAction action{};
    action.kind = 0;
    action.move_slot = 3;

    TransitionOracle oracle;
    double total = 0.0;
    uint64_t leaves = 0;
    StepStats stats = oracle.step(state, action, [&](ChildOutcome co) -> bool {
        total += co.prob;
        ++leaves;
        return true;
    });

    REQUIRE_FALSE(stats.budget_exceeded);
    REQUIRE(leaves > 0);
    REQUIRE(std::abs(total - 1.0) < 1e-9);
}
