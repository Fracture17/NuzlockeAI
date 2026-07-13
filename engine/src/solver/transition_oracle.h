// TransitionOracle: DFS prefix-replay enumeration of all (child, prob) outcomes from one
// (state, player action) pair. Outer branches over AI actions; inner DFS forces every
// Category-B draw and handles Category-A pauses. Emits leaves via a callback.
// One-way dependency: uses nuzlocke_core (never the reverse).
#pragma once
#ifndef NUZLOCKE_SOLVER_TRANSITION_ORACLE_H
#define NUZLOCKE_SOLVER_TRANSITION_ORACLE_H

#include "solver/oracle_types.h"
#include "move_exec.h"   // ExecAction
#include "state.h"

#include <cstdint>
#include <functional>

// Stateless transition oracle. All per-call state lives on the stack.
class TransitionOracle {
public:
    struct Config {
        uint64_t    max_leaves  = 1'000'000;
        // Optional per-leaf debug callback. Null (default) = zero overhead on hot path.
        // When set, called before each leaf emit with the full DFS prefix path.
        LeafDebugFn debug_emit;
    };

    // Enumerate all child states reachable from (state, player_action) in one turn.
    // emit receives each ChildOutcome; returning false aborts enumeration.
    // Throws std::runtime_error on precondition violations or unmodeled events.
    // hint controls leaf visitation order (does not change the emitted multiset).
    StepStats step(const BattleState& state,
                   const ExecAction& player_action,
                   const OracleEmitFn& emit,
                   OrderingHint hint,
                   const Config& cfg) const;

    // Overload with default config.
    StepStats step(const BattleState& state,
                   const ExecAction& player_action,
                   const OracleEmitFn& emit,
                   OrderingHint hint = OrderingHint::Natural) const {
        return step(state, player_action, emit, hint, Config{});
    }
};

#endif // NUZLOCKE_SOLVER_TRANSITION_ORACLE_H
