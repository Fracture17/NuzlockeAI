// C1.7h Stage 2 / C1.7i Stage 6: Policy abstraction for action selection.
// Defines the Policy interface, RandomPolicy (seeded mt19937_64), and ScriptedPolicy (queue).
// Three decision contexts: select (normal turn), select_switch (post-faint/forced-pivot agent
// decision), select_phaze (game-mechanic uniform roar/whirlwind draw — always random).
// NNPolicy seam: an NNPolicy would implement select() by featurizing (state, legal) into a
// tensor, running inference, and returning the argmax action. It does NOT belong here yet —
// no tensor ABI or layout is committed. Add it in the NN build stage when the ABI is decided.
#pragma once
#ifndef NUZLOCKE_POLICY_H
#define NUZLOCKE_POLICY_H

#include "state.h"
#include "move_exec.h"  // ExecAction
#include <vector>
#include <random>
#include <stdexcept>
#include <string>

// Which kind of agent-controlled forced switch triggered select_switch.
enum class SwitchCtx { POST_FAINT, FORCED_PIVOT };

// Abstract policy: given the current legal actions and battle state, pick one.
struct Policy {
    virtual ExecAction select(const std::vector<ExecAction>& legal,
                              const BattleState& state, int side_idx) = 0;

    // Agent-controlled forced replacement (post-faint or pivot/eject/red_card).
    // Default delegates to select() so RandomPolicy stays uniform without change.
    virtual ExecAction select_switch(const std::vector<ExecAction>& candidates,
                                     const BattleState& state, int side_idx, SwitchCtx) {
        return select(candidates, state, side_idx);
    }

    // Game-mechanic uniform phaze/roar draw. Must remain uniform-random even for AI-controlled
    // sides — phazing is not an agent decision. Default delegates to select().
    virtual ExecAction select_phaze(const std::vector<ExecAction>& bench,
                                    const BattleState& state, int side_idx) {
        return select(bench, state, side_idx);
    }

    virtual ~Policy() = default;
};

// Picks uniformly at random from the legal action list. Reproducible given the seed.
struct RandomPolicy : Policy {
    explicit RandomPolicy(uint64_t seed) : rng_(seed) {}

    ExecAction select(const std::vector<ExecAction>& legal,
                      const BattleState& /*state*/, int /*side_idx*/) override {
        if (legal.empty()) throw std::runtime_error("RandomPolicy: empty legal action list");
        std::uniform_int_distribution<size_t> dist(0, legal.size() - 1);
        return legal[dist(rng_)];
    }

private:
    std::mt19937_64 rng_;
};

// Returns a pre-specified sequence of actions in order. Throws when the queue is exhausted.
struct ScriptedPolicy : Policy {
    explicit ScriptedPolicy(std::vector<ExecAction> actions)
        : actions_(std::move(actions)), idx_(0) {}

    ExecAction select(const std::vector<ExecAction>& /*legal*/,
                      const BattleState& /*state*/, int /*side_idx*/) override {
        if (idx_ >= actions_.size())
            throw std::runtime_error("ScriptedPolicy: action queue exhausted");
        return actions_[idx_++];
    }

private:
    std::vector<ExecAction> actions_;
    size_t idx_;
};

#endif // NUZLOCKE_POLICY_H
