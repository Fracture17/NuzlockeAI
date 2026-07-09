// Solver-facing single-turn entry point. Thin wrapper over cpp_run_one_turn — the
// existing oracle-mode loop already does everything we need when overrides carry
// all Category-A answers up front. We only add: (1) no policies plumbing, (2) any
// pause/error becomes an error return instead of a thrown exception.
#include "solver_turn.h"

#include "oracle.h"
#include "turn.h"

#include <stdexcept>
#include <string>

SolverTurnResult cpp_run_one_turn_solver(BattleState& state,
                                         const std::vector<ExecAction>& actions_p0,
                                         const std::vector<ExecAction>& actions_p1,
                                         DamageLoopLuck& luck_p0,
                                         DamageLoopLuck& luck_p1,
                                         const TurnLuck& tl0,
                                         const TurnLuck& tl1,
                                         bool mega_p0,
                                         bool mega_p1,
                                         const OracleOverrides& overrides) {
    SolverTurnResult r;
    try {
        cpp_run_one_turn(state, actions_p0, actions_p1,
                         luck_p0, luck_p1, tl0, tl1,
                         mega_p0, mega_p1,
                         /*finalize_on_post_faint=*/true,
                         /*policies=*/nullptr,
                         /*action_log=*/nullptr,
                         /*overrides=*/&overrides,
                         /*resume_snap=*/nullptr);
    } catch (const TurnPause& tp) {
        r.ok = false;
        r.error = "solver_turn: unresolved oracle pause event="
                  + std::to_string(static_cast<int>(tp.needs.event));
    } catch (const NeedsRNG& nr) {
        // Plain-mode NeedsRNG should not surface here (we always pass overrides), but
        // catch defensively so the solver never sees a raw exception at this boundary.
        r.ok = false;
        r.error = "solver_turn: NeedsRNG surfaced event="
                  + std::to_string(static_cast<int>(nr.event));
    } catch (const std::runtime_error& e) {
        r.ok = false;
        r.error = std::string("solver_turn: runtime_error: ") + e.what();
    }
    return r;
}
