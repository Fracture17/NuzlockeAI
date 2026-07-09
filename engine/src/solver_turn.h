// Minimal, exception-free single-turn entry point for the RNG-bucketing solver.
// Wraps cpp_run_one_turn in oracle mode with pre-loaded OracleOverrides. Any
// unresolved Category-A pause (NeedsRNG/TurnPause) becomes an error return —
// the solver enumerates its own RNG buckets, so a pause here means the caller's
// answer set was incomplete. That's a bug: fail loudly at the boundary rather
// than propagating a thrown exception through millions of turn executions.
#pragma once
#ifndef NUZLOCKE_SOLVER_TURN_H
#define NUZLOCKE_SOLVER_TURN_H

#include "core_leaf.h"          // TurnLuck
#include "move_exec.h"          // ExecAction
#include "move_exec_damage.h"   // DamageLoopLuck
#include "oracle.h"             // OracleOverrides
#include "state.h"

#include <string>
#include <vector>

// Result of a single solver-driven turn execution.
// ok=true: state has been mutated to post-turn; error is empty.
// ok=false: an unresolved Category-A oracle pause or runtime error occurred; state
//   contents are undefined (the solver must discard this bucket). error describes
//   the cause for diagnostics.
struct SolverTurnResult {
    bool ok = true;
    std::string error;
};

// Run exactly one turn in place with pre-loaded oracle answers, no JSON encode/decode.
// - Mirrors cpp_run_one_turn(state, ..., finalize_on_post_faint=true, ..., overrides=&ov)
//   so post-turn semantics match the driver's per-turn commit.
// - policies is intentionally omitted: the solver enumerates its own decisions ahead of
//   time via ov, so pivot/phaze paths that would need a policy should be pre-answered.
// - No pause/resume machinery: any TurnPause becomes SolverTurnResult{ok=false}.
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
