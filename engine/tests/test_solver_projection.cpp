// Catch2 tests for D4:
//   (1) solver-view equality/hash excludes turn_number, exp_participants, prev_turn_order
//       but distinguishes every other field the full state_equal compares.
//   (2) equal implies equal-hash on constructed pairs.
//   (3) stale InlineVec capacity slots (beyond size_) and struct padding do NOT affect the
//       solver hash — the hash must be field-wise over the LIVE range only.
//   (4) direct solver turn execution matches the driver path on the same state/actions and
//       fails loudly when an oracle answer is missing.
#include <catch2/catch_test_macros.hpp>

#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include "core_leaf.h"           // TurnLuck
#include "move_exec.h"           // ExecAction
#include "move_exec_damage.h"    // DamageLoopLuck
#include "oracle.h"              // OracleOverrides, NeedsRNG
#include "solver_turn.h"         // cpp_run_one_turn_solver
#include "state.h"
#include "state_eq.h"            // state_equal, state_hash, state_equal_solver, state_hash_solver
#include "turn.h"                // cpp_run_one_turn

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

// Build a minimal 1v1 BattleState with two live mons that have identical layouts.
// Doubles-safe: sets active_indices to a single slot each side.
static BattleState make_min_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    mon.move_id0 = 33;  // TACKLE-like id; not looked up in these tests
    mon.move_pp0 = 35;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// (1) Solver view excludes bookkeeping fields but retains everything else
// ---------------------------------------------------------------------------

TEST_CASE("solver equality ignores turn_number", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.turn_number = a.turn_number + 5;

    REQUIRE_FALSE(state_equal(a, b));  // full equality: differ
    REQUIRE(state_equal_solver(a, b)); // solver: same
    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
}

TEST_CASE("solver equality ignores prev_turn_order", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    a.prev_turn_order.push_back(0);
    a.prev_turn_order.push_back(1);
    b.prev_turn_order.push_back(1);
    b.prev_turn_order.push_back(0);

    REQUIRE_FALSE(state_equal(a, b));
    REQUIRE(state_equal_solver(a, b));
    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
}

TEST_CASE("solver equality ignores exp_participants", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    ExpParticipantSet eps;
    eps.members.push_back(0);
    a.exp_participants.push_back(eps);

    REQUIRE_FALSE(state_equal(a, b));
    REQUIRE(state_equal_solver(a, b));
    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
}

TEST_CASE("solver equality distinguishes HP", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side0.team[0].hp = 42;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes stat stages", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side0.team[0].stage0 = 2;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes volatiles bitmask", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side1.team[0].volatiles = 0x100;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes PP", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side0.team[0].move_pp0 = 10;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes item", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side0.team[0].item = 99;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes weather turns", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    a.weather = 2; a.weather_turns = 3;
    b.weather = 2; b.weather_turns = 5;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes terrain", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    a.terrain = 1; a.terrain_turns = 2;
    b.terrain = 3; b.terrain_turns = 2;

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes timed volatile turns", "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    TimedVolatile tv{7, 3};
    a.side0.team[0].timed_volatiles.push_back(tv);
    TimedVolatile tv2{7, 4};
    b.side0.team[0].timed_volatiles.push_back(tv2);

    REQUIRE_FALSE(state_equal_solver(a, b));
}

TEST_CASE("solver equality distinguishes turn_order (live, not prev)",
          "[solver_view][equality]") {
    BattleState a = make_min_state();
    BattleState b = a;
    a.turn_order.push_back(0);
    a.turn_order.push_back(1);
    b.turn_order.push_back(1);
    b.turn_order.push_back(0);

    REQUIRE_FALSE(state_equal_solver(a, b));
}

// ---------------------------------------------------------------------------
// (2) Equal implies equal hash
// ---------------------------------------------------------------------------

TEST_CASE("solver: equal implies equal hash (identical)", "[solver_view][hash]") {
    BattleState a = make_min_state();
    BattleState b = a;
    REQUIRE(state_equal_solver(a, b));
    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
}

TEST_CASE("solver: equal implies equal hash (differ only on excluded fields)",
          "[solver_view][hash]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.turn_number = a.turn_number + 100;
    a.prev_turn_order.push_back(0);
    a.prev_turn_order.push_back(1);
    b.prev_turn_order.push_back(1);
    ExpParticipantSet eps; eps.members.push_back(0);
    b.exp_participants.push_back(eps);
    REQUIRE(state_equal_solver(a, b));
    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
}

// Multiple field variations, each pair identical, should collapse into fewer buckets
// than full state hash would produce.
TEST_CASE("solver: distinct HPs produce distinct hashes (probabilistic)",
          "[solver_view][hash]") {
    BattleState a = make_min_state();
    BattleState b = a;
    b.side0.team[0].hp = 42;
    // Not a strict guarantee, but a well-mixed hash must differ for a single-field change.
    REQUIRE(state_hash_solver(a) != state_hash_solver(b));
}

// ---------------------------------------------------------------------------
// (3) Stale capacity slots and struct padding do not affect the hash
// ---------------------------------------------------------------------------

TEST_CASE("solver hash ignores stale InlineVec capacity slots (team level)",
          "[solver_view][hash][stale]") {
    BattleState a = make_min_state();
    BattleState b = a;

    // Mutate a raw slot BEYOND size_ in team storage on b: use the second team slot
    // even though only slot 0 is live (size_==1). Direct data_ write bypasses size_.
    // Sanity-check the setup: capacity must be > 1 so a stale slot exists.
    REQUIRE(b.side0.team.capacity() > b.side0.team.size());
    b.side0.team.data_[1].species = 0x7EAD;
    b.side0.team.data_[1].hp      = 0x7EAF;

    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
    REQUIRE(state_equal_solver(a, b));
}

TEST_CASE("solver hash ignores stale slot in a mon's types InlineVec",
          "[solver_view][hash][stale]") {
    BattleState a = make_min_state();
    a.side0.team[0].has_types = true;
    a.side0.team[0].types.push_back(1);  // FIRE

    BattleState b = a;
    // Overwrite slot beyond size_ in b's types; live range is just [0].
    REQUIRE(b.side0.team[0].types.capacity() > b.side0.team[0].types.size());
    b.side0.team[0].types.data_[1] = 0xBEEF;

    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
    REQUIRE(state_equal_solver(a, b));
}

TEST_CASE("solver hash ignores stale slot in side_conditions InlineVec",
          "[solver_view][hash][stale]") {
    BattleState a = make_min_state();
    a.side0.side_conditions.push_back(SideConditionEntry{1, 3});

    BattleState b = a;
    REQUIRE(b.side0.side_conditions.capacity() > b.side0.side_conditions.size());
    b.side0.side_conditions.data_[1] = SideConditionEntry{99, 8};

    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
    REQUIRE(state_equal_solver(a, b));
}

TEST_CASE("solver hash ignores stale slot in exp_participants outer InlineVec",
          "[solver_view][hash][stale]") {
    // exp_participants IS excluded, so this is trivially covered — but confirm the
    // full-state hash is also robust to stale outer slots (its own contract).
    BattleState a = make_min_state();
    BattleState b = a;
    // Write beyond exp_participants.size_ (which is 0).
    REQUIRE(b.exp_participants.capacity() > 0);
    b.exp_participants.data_[0].members.data_[0] = 0xC0DE;

    REQUIRE(state_hash_solver(a) == state_hash_solver(b));
    REQUIRE(state_hash(a) == state_hash(b));
}

// ---------------------------------------------------------------------------
// (4) Direct solver turn execution
// ---------------------------------------------------------------------------

// Build a 2v2 team-size state with a switch action so the turn runs cleanly with
// no Cat-A pauses and no move-data lookups.
static BattleState make_switch_ready_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1; mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    // 2-mon party per side so a switch to team_idx=1 is legal.
    s.side0.team.push_back(mon);
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static std::vector<ExecAction> switch_actions(int source_slot, int to_slot) {
    std::vector<ExecAction> a;
    ExecAction e;
    e.kind = 1;                     // AK_SWITCH
    e.switch_to_slot = to_slot;
    e.source_slot = source_slot;
    a.push_back(e);
    return a;
}

// Run one turn via the standard driver (oracle mode with overrides pre-loaded) and
// compare to the direct solver entry point.
TEST_CASE("solver direct turn matches oracle-mode driver on same input",
          "[solver_turn][parity]") {
    BattleState state_a = make_switch_ready_state();
    BattleState state_b = state_a;

    // Both sides switch — no move resolution, no Cat-A RNG draws.
    std::vector<ExecAction> ap0 = switch_actions(0, 1);
    std::vector<ExecAction> ap1 = switch_actions(0, 1);

    DamageLoopLuck lp0{}; DamageLoopLuck lp1{};
    TurnLuck tl0{}; TurnLuck tl1{};
    OracleOverrides ov;

    // Driver reference: full oracle mode.
    DamageLoopLuck lp0_ref = lp0, lp1_ref = lp1;
    cpp_run_one_turn(state_a, ap0, ap1, lp0_ref, lp1_ref, tl0, tl1,
                     /*mega_p0=*/false, /*mega_p1=*/false,
                     /*finalize_on_post_faint=*/true,
                     /*policies=*/nullptr, /*action_log=*/nullptr,
                     /*overrides=*/&ov, /*resume_snap=*/nullptr);

    // Solver direct path: same inputs -> same output.
    DamageLoopLuck lp0_solver = lp0, lp1_solver = lp1;
    SolverTurnResult r = cpp_run_one_turn_solver(state_b, ap0, ap1,
                                                  lp0_solver, lp1_solver,
                                                  tl0, tl1,
                                                  /*mega_p0=*/false,
                                                  /*mega_p1=*/false,
                                                  ov);
    REQUIRE(r.ok);
    REQUIRE(state_equal(state_a, state_b));
}

TEST_CASE("solver direct turn errors loudly on missing oracle answer",
          "[solver_turn][fail_loud]") {
    // Force a Category-A pause: METRONOME_MOVE with no override queued. The plain solver
    // path must NOT throw NeedsRNG (that's the whole point) — it must surface an error
    // via SolverTurnResult.ok=false so the search harness knows its RNG enumeration
    // was wrong.
    // We reuse a state where side0 has an item and moves that would trigger metronome
    // resolution. Instead of setting up move data, we manually seed the OracleOverrides
    // with a mismatched event that IS consumed, then force the code path via a
    // synthetic call: since we can't cheaply build a Metronome scenario in isolation,
    // we exercise the API through a state that would need SPEED_TIE resolution — two
    // mons with identical effective speed and no ordering override.
    BattleState state = make_min_state();
    // Identical speeds are already set by make_min_state (stat_spe=60 both sides).
    // Speed-tie in controlled mode + no override -> NeedsRNG SPEED_TIE.

    // Build real MOVE actions so cpp_build_pending_entries builds two entries that will
    // tie on speed. move_slot=0 references move_id0 which we set to 33 (arbitrary).
    std::vector<ExecAction> ap0, ap1;
    ExecAction e0; e0.kind = 0; e0.move_slot = 0; e0.source_slot = 0; ap0.push_back(e0);
    ExecAction e1; e1.kind = 0; e1.move_slot = 0; e1.source_slot = 0; ap1.push_back(e1);

    DamageLoopLuck lp0{}; DamageLoopLuck lp1{};
    TurnLuck tl0{}; TurnLuck tl1{};
    // random_mode=false (controlled) so speed tie must be resolved by override or throw.
    OracleOverrides ov;  // empty — no SPEED_TIE ordering queued.

    SolverTurnResult r = cpp_run_one_turn_solver(state, ap0, ap1,
                                                  lp0, lp1, tl0, tl1,
                                                  false, false, ov);
    REQUIRE(r.ok == false);
    REQUIRE(!r.error.empty());
}

// ---------------------------------------------------------------------------
// (5) Pre-sorted set invariant fails loudly (fork-based death test, matching
//     the InlineVec overflow tests in test_state_layout.cpp)
// ---------------------------------------------------------------------------

#include <sys/wait.h>
#include <unistd.h>
#include <cstdio>

namespace {
bool sorted_child_aborted(int status) {
    if (WIFSIGNALED(status)) return true;  // SIGABRT
    if (WIFEXITED(status) && WEXITSTATUS(status) != 0) return true;
    return false;
}
}  // namespace

TEST_CASE("state_equal aborts on unsorted imprisoned_moves (invariant guard)",
          "[solver_view][invariant]") {
    pid_t pid = fork();
    REQUIRE(pid >= 0);
    if (pid == 0) {
        std::freopen("/dev/null", "w", stdout);
        std::freopen("/dev/null", "w", stderr);
        BattleState a = make_min_state();
        BattleState b = make_min_state();
        a.side0.imprisoned_moves.push_back(50);
        a.side0.imprisoned_moves.push_back(10);  // unsorted: violates codec invariant
        b.side0.imprisoned_moves.push_back(50);
        b.side0.imprisoned_moves.push_back(10);
        volatile bool eq = state_equal(a, b);  // must abort before returning
        (void)eq;
        _exit(0);  // reaching here means the invariant guard is broken
    }
    int status = 0;
    waitpid(pid, &status, 0);
    REQUIRE(sorted_child_aborted(status));
}
