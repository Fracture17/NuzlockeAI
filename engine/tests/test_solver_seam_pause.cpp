// Tests for Task 2: SolverTurnResult pause extension + oracle_types.h scaffolding.
// Verifies that a SPEED_TIE with no override queued returns paused=true with the
// correct event and options, and that a normal (no-pause) turn returns ok=true, paused=false.
#include <catch2/catch_test_macros.hpp>

#include <cstdint>
#include <vector>

#include "core_leaf.h"        // TurnLuck
#include "move_exec.h"        // ExecAction
#include "move_exec_damage.h" // DamageLoopLuck
#include "oracle.h"           // OracleOverrides, RngEventC
#include "solver_turn.h"      // cpp_run_one_turn_solver, SolverTurnResult
#include "state.h"
#include "turn.h"             // TurnPause

#include "solver/oracle_types.h"  // ChildOutcome, OrderingHint, StepStats, emit callback

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

// Minimal 1v1 state with identical speeds (stat_spe=60) — guaranteed to produce a
// controlled SPEED_TIE when both sides use a move.
static BattleState make_speed_tie_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    mon.move_id0 = 33;  // arbitrary move id
    mon.move_pp0 = 35;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static std::vector<ExecAction> move_actions(int source_slot, int move_slot) {
    ExecAction e;
    e.kind = 0;  // AK_MOVE
    e.source_slot = source_slot;
    e.move_slot = move_slot;
    std::vector<ExecAction> a;
    a.push_back(e);
    return a;
}

// ---------------------------------------------------------------------------
// Test 1: Equal-speed tie with no speed_tie_queue → paused=true, SPEED_TIE event
// ---------------------------------------------------------------------------

TEST_CASE("solver turn pauses on SPEED_TIE with empty override queue",
          "[solver_seam][pause]") {
    BattleState state = make_speed_tie_state();

    std::vector<ExecAction> ap0 = move_actions(0, 0);
    std::vector<ExecAction> ap1 = move_actions(0, 0);

    DamageLoopLuck lp0{}, lp1{};
    TurnLuck tl0{}, tl1{};
    OracleOverrides ov;  // empty — no SPEED_TIE ordering queued

    SolverTurnResult r = cpp_run_one_turn_solver(state, ap0, ap1,
                                                  lp0, lp1, tl0, tl1,
                                                  false, false, ov);

    // Must be a clean pause, not an error.
    REQUIRE(r.ok == true);
    REQUIRE(r.paused == true);
    REQUIRE(r.event == RngEventC::SPEED_TIE);

    // Options are encoded as side_idx*10 + source_slot.
    // Singles: side0 slot0 → 0; side1 slot0 → 10.
    REQUIRE(r.options.size() == 2);
    bool has_side0 = false, has_side1 = false;
    for (int32_t opt : r.options) {
        if (opt == 0)  has_side0 = true;
        if (opt == 10) has_side1 = true;
    }
    REQUIRE(has_side0);
    REQUIRE(has_side1);
}

// ---------------------------------------------------------------------------
// Test 2: Normal turn (switch, no Cat-A pause) → ok=true, paused=false
// ---------------------------------------------------------------------------

static BattleState make_switch_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1; mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    // Two mons so a switch to team_idx=1 is legal.
    s.side0.team.push_back(mon);
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

TEST_CASE("solver turn returns ok=true, paused=false on clean switch turn",
          "[solver_seam][no_pause]") {
    BattleState state = make_switch_state();

    ExecAction sw;
    sw.kind = 1;  // AK_SWITCH
    sw.source_slot = 0;
    sw.switch_to_slot = 1;
    std::vector<ExecAction> ap0{sw}, ap1{sw};

    DamageLoopLuck lp0{}, lp1{};
    TurnLuck tl0{}, tl1{};
    OracleOverrides ov;

    SolverTurnResult r = cpp_run_one_turn_solver(state, ap0, ap1,
                                                  lp0, lp1, tl0, tl1,
                                                  false, false, ov);

    REQUIRE(r.ok == true);
    REQUIRE(r.paused == false);
    REQUIRE(r.options.empty());
}

// ---------------------------------------------------------------------------
// Test 3: oracle_types.h — ChildOutcome, OrderingHint, StepStats compile and hold values
// ---------------------------------------------------------------------------

TEST_CASE("oracle_types compile and hold expected values", "[solver_seam][oracle_types]") {
    // ChildOutcome
    BattleState bs = make_speed_tie_state();
    ChildOutcome co{bs, 0.5};
    REQUIRE(co.prob == 0.5);

    // OrderingHint enum values
    REQUIRE(static_cast<int>(OrderingHint::Natural)     == 0);
    REQUIRE(static_cast<int>(OrderingHint::AdverseFirst) == 1);

    // StepStats zero-init
    StepStats ss{};
    REQUIRE(ss.leaves == 0);
    REQUIRE(ss.turn_executions == 0);
    REQUIRE(ss.aborted == false);
    REQUIRE(ss.budget_exceeded == false);
}

// ---------------------------------------------------------------------------
// Test 4: Declared-but-throwing stubs throw std::logic_error
// ---------------------------------------------------------------------------

TEST_CASE("oracle stub damage_table_query throws logic_error", "[solver_seam][stub]") {
    REQUIRE_THROWS_AS(oracle_damage_table_query(nullptr), std::logic_error);
}

TEST_CASE("oracle stub hp_threshold_set_query throws logic_error", "[solver_seam][stub]") {
    REQUIRE_THROWS_AS(oracle_hp_threshold_set_query(nullptr), std::logic_error);
}
