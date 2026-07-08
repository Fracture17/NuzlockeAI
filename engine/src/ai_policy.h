// C1.7i Stage 4+6: real AI scoring seam and AIPolicy.
// cpp_score_ai_actions: full stochastic sampler mirroring Python _score_ai_actions.
// AIPolicy::select: mirrors Python select_ai_action (max-score tie-break + 50% switch gate).
// AIPolicy::select_switch: uses cpp_select_post_ko_switch for post-faint and forced-pivot
//   replacements (mirrors select_post_ko_switch). Throws if no candidate matches.
// AIPolicy::select_phaze: uniform-random draw (game mechanic, NOT an agent decision).
#pragma once
#ifndef NUZLOCKE_AI_POLICY_H
#define NUZLOCKE_AI_POLICY_H

#include "state.h"
#include "move_exec.h"   // ExecAction
#include "policy.h"      // Policy base, SwitchCtx
#include <vector>
#include <optional>
#include <random>

struct AIScoreResult {
    std::vector<ExecAction> actions;
    std::vector<int> scores;
    std::optional<ExecAction> switch_target;
};

// Score all legal actions for ai_idx via stochastic sampling (mirrors _score_ai_actions).
// Draws from rng for damage-roll sampling and score sampling.
AIScoreResult cpp_score_ai_actions(const BattleState& state, int ai_idx, std::mt19937_64& rng);

// Policy that uses cpp_score_ai_actions for action selection (mirrors select_ai_action).
struct AIPolicy : Policy {
    explicit AIPolicy(uint64_t seed);

    // Normal turn action via stochastic sampler.
    ExecAction select(const std::vector<ExecAction>& legal,
                      const BattleState& state, int side_idx) override;

    // Post-faint / forced-pivot replacement via cpp_select_post_ko_switch.
    // Throws std::runtime_error if no candidate's switch_to_slot matches the scorer result.
    ExecAction select_switch(const std::vector<ExecAction>& candidates,
                             const BattleState& state, int side_idx, SwitchCtx ctx) override;

    // Game-mechanic uniform roar/phaze draw (NOT an agent decision — always uniform).
    ExecAction select_phaze(const std::vector<ExecAction>& bench,
                            const BattleState& state, int side_idx) override;

private:
    std::mt19937_64 rng_;
};

#endif // NUZLOCKE_AI_POLICY_H
