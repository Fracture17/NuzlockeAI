// Minimal, exception-free single-turn entry point for the RNG-bucketing solver.
// Wraps cpp_run_one_turn in oracle mode with pre-loaded OracleOverrides. Any
// unresolved Category-A pause (NeedsRNG/TurnPause) either sets paused=true (normal
// oracle branch point) or ok=false (unexpected runtime error). The distinction lets
// the transition oracle enumerate Cat-A branches rather than treating them as errors.
#pragma once
#ifndef NUZLOCKE_SOLVER_TURN_H
#define NUZLOCKE_SOLVER_TURN_H

#include "core_leaf.h"          // TurnLuck
#include "move_exec.h"          // ExecAction
#include "move_exec_damage.h"   // DamageLoopLuck
#include "oracle.h"             // OracleOverrides, RngEventC
#include "state.h"

#include <cstdint>
#include <string>
#include <vector>

// Result of a single solver-driven turn execution.
// ok=true, paused=false: state has been mutated to post-turn; error is empty.
// ok=true, paused=true: the turn halted at a Category-A branch point (e.g. SPEED_TIE);
//   state is restored to pre-action; event and options carry the NeedsRNG payload.
//   The caller must supply an answer and replay to continue enumeration.
// ok=false: an unexpected runtime error occurred; state contents are undefined;
//   error describes the cause for diagnostics.
struct SolverTurnResult {
    bool ok = true;
    std::string error;

    // Pause fields — meaningful only when ok=true && paused=true.
    bool paused = false;
    RngEventC event = RngEventC::SPEED_TIE;  // sentinel default; only valid when paused
    std::vector<int32_t> options;             // encoded as side_idx*10+source_slot for SPEED_TIE
};

// Run exactly one turn in place with pre-loaded oracle answers, no JSON encode/decode.
// - Mirrors cpp_run_one_turn(state, ..., finalize_on_post_faint=true, ..., overrides=&ov)
//   so post-turn semantics match the driver's per-turn commit.
// - policies is intentionally omitted: the solver enumerates its own decisions ahead of
//   time via ov, so pivot/phaze paths that would need a policy should be pre-answered.
// - TurnPause (Cat-A branch point) → ok=true, paused=true with event+options populated.
// - NeedsRNG or runtime_error → ok=false with error message.
SolverTurnResult cpp_run_one_turn_solver(BattleState& state,
                                         const std::vector<ExecAction>& actions_p0,
                                         const std::vector<ExecAction>& actions_p1,
                                         DamageLoopLuck& luck_p0,
                                         DamageLoopLuck& luck_p1,
                                         const TurnLuck& tl0,
                                         const TurnLuck& tl1,
                                         bool mega_p0,
                                         bool mega_p1,
                                         const OracleOverrides& overrides);

#endif // NUZLOCKE_SOLVER_TURN_H
