// Solver-facing single-turn entry point. Thin wrapper over cpp_run_one_turn — the
// existing oracle-mode loop handles all Category-A answers from overrides. A TurnPause
// (unresolved Cat-A event) now becomes a pause result so the transition oracle can
// enumerate branches; other exceptions become error results.
#include "solver_turn.h"

#include "oracle.h"
#include "turn.h"

#include <cstdint>
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
    // Thread overrides into the per-side luck structs, mirroring GameDriver
    // (game_driver.cpp lp*_tmpl_.overrides). cpp_run_one_turn threads pre_inject
    // into luck but NOT overrides; without this, oracle_resolve sites reached via
    // luck.overrides (e.g. Starf's check_berry) see nullptr and pause forever
    // regardless of the answers supplied — an infinite prefix-extension loop.
    luck_p0.overrides = &overrides;
    luck_p1.overrides = &overrides;
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
        // Normal Cat-A branch point: surface as a pause, not an error.
        // State has been restored to pre-action by the pause mechanism in cpp_run_one_turn.
        r.paused = true;
        r.event  = tp.needs.event;
        for (int opt : tp.needs.options)
            r.options.push_back(static_cast<int32_t>(opt));
    } catch (const NeedsRNG& nr) {
        // Plain-mode NeedsRNG should not surface here (we always pass overrides), but
        // catch defensively so the solver never sees a raw exception at this boundary.
        r.ok    = false;
        r.error = "solver_turn: NeedsRNG surfaced event="
                  + std::to_string(static_cast<int>(nr.event));
    } catch (const std::runtime_error& e) {
        r.ok    = false;
        r.error = std::string("solver_turn: runtime_error: ") + e.what();
    }
    return r;
}
