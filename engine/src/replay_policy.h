// ReplayPolicy: consumes Cat-A switch answers from a ForcedTrace during forced replay.
// select() and select_phaze() throw forced_trace_mismatch immediately — they are never
// called in forced mode (ACTION_SELECT is handled directly in GameDriver::_run()).
#pragma once
#ifndef NUZLOCKE_REPLAY_POLICY_H
#define NUZLOCKE_REPLAY_POLICY_H

#include "policy.h"
#include "forced_trace.h"
#include "native_rng.h"
#include "oracle.h"
#include "orchestrate.h"   // cpp_action_from_json
#include <stdexcept>
#include <string>
#include <vector>

// Replay policy for forced-trace mode. Handles post-faint and forced-pivot switches by
// consuming the next ForcedAnswer from the trace; all other selects throw immediately.
struct ReplayPolicy : Policy {
    ForcedTrace* trace;
    NativeRng*   rng;
    int          side;

    ReplayPolicy(ForcedTrace* t, NativeRng* r, int s)
        : trace(t), rng(r), side(s) {}

    ExecAction select(const std::vector<ExecAction>& /*legal*/,
                      const BattleState& /*state*/, int /*side_idx*/) override {
        throw std::runtime_error(
            "forced_trace_mismatch: policy select() called in forced mode");
    }

    ExecAction select_phaze(const std::vector<ExecAction>& bench,
                            const BattleState& /*state*/, int /*side_idx*/) override {
        const ForcedAnswer& a = trace->next_answer(rng->current_turn, RngEventC::ROAR_TARGET, -1);
        for (const ExecAction& cand : bench) {
            if (cand.switch_to_slot == a.i0)
                return cand;
        }
        throw std::runtime_error(
            "forced_trace_mismatch: no phaze candidate with switch_to_slot="
            + std::to_string(a.i0) + " turn=" + std::to_string(rng->current_turn));
    }

    ExecAction select_switch(const std::vector<ExecAction>& candidates,
                             const BattleState& /*state*/, int side_idx,
                             SwitchCtx ctx) override {
        RngEventC event = (ctx == SwitchCtx::POST_FAINT)
                          ? RngEventC::POST_FAINT_SWITCH
                          : RngEventC::FORCED_SWITCH;
        const ForcedAnswer& a = trace->next_answer(rng->current_turn, event, side_idx);

        // Find the candidate whose switch_to_slot matches a.i0.
        for (const ExecAction& cand : candidates) {
            if (cand.switch_to_slot == a.i0)
                return cand;
        }
        throw std::runtime_error(
            "forced_trace_mismatch: no candidate with switch_to_slot="
            + std::to_string(a.i0) + " for side=" + std::to_string(side_idx)
            + " turn=" + std::to_string(rng->current_turn));
    }
};

#endif // NUZLOCKE_REPLAY_POLICY_H
