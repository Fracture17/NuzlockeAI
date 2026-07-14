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
#include <utility>
#include <vector>

// Test shim: expand Cat-B options with aggregate_damage_rolls=false. Exposed so tests can
// directly trigger the unknown-event throw path without going through step().
struct AnalyticalRngEntry;
std::vector<std::pair<int,double>> expand_catb_options_for_test(const AnalyticalRngEntry& entry);

// Stateless transition oracle. All per-call state lives on the stack.
class TransitionOracle {
public:
    // Controls collapse of Cat-B random outcomes at each branch point.
    // None (default): enumerate all branches exactly — exact mode. ChildOutcome.prob is a
    //   real probability; leaves form a distribution summing to 1. Bit-for-bit unchanged.
    // Pessimal: collapse every collapse-eligible event to its single worst-for-player outcome.
    //   ChildOutcome.prob is NaN — not a distribution, possibility-only semantics.
    // Coarse: exact on all events except DAMAGE_ROLL, which collapses to {min, max} per
    //   crit class (2 branches instead of up to 16).
    //   ChildOutcome.prob is NaN — not a distribution, possibility-only semantics.
    // Soundness invariant: Pessimal and Coarse explore a subset of each node's true p>0
    //   outcomes. By the subset-support theorem, a LOSS found within the subset is a
    //   conclusive LOSS; a WIN is only a routing candidate for exact. See SOLVER_PHASE2_PLAN.md.
    // NaN poison: any consumer that reads .prob under non-None modes will see NaN and
    //   propagate it, making accidental prob reads fail loudly.
    enum class CollapseMode {
        None,
        Pessimal,
        Coarse,
    };

    struct Config {
        uint64_t    max_leaves  = 1'000'000;
        // Merge identical-damage DAMAGE_ROLL outcomes before DFS recursion.
        // ON (default): group rolls 0..15 by identical final damage; one branch per group.
        // OFF: enumerate all 16 branches individually (for audit A/B comparison only).
        bool        aggregate_damage_rolls = true;
        // Collapse mode for cheap tiers. Default None = exact (bit-for-bit unchanged).
        CollapseMode collapse = CollapseMode::None;
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
