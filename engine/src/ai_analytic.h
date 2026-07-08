// Stage 5 AI analytic probability computation.
// Ports: _iter_damage_configs, compute_action_probabilities, possible_ai_actions.
// cpp_iter_damage_configs collapses the 16^m roll grid to O(levels·2^m) configs.
// cpp_compute_action_probabilities enumerates configs × score-dists analytically.
#pragma once
#ifndef NUZLOCKE_AI_ANALYTIC_H
#define NUZLOCKE_AI_ANALYTIC_H

#include "state.h"
#include "move_exec.h"

#include <array>
#include <cstdint>
#include <vector>

// Per-(is_highest, kills) config with its exact summed weight over the 16^m roll grid.
struct DamageConfig {
    double             weight;
    std::vector<char>  is_highest;  // bool per damaging move
    std::vector<char>  kills;       // bool per damaging move
};

// Collapse 16^m roll grid into distinct (is_highest, kills) configs (mirrors _iter_damage_configs).
// dm_rolls: one 16-element array per damaging move.
// hp: opponent's current HP (for KO / ranking cap).
std::vector<DamageConfig> cpp_iter_damage_configs(
    const std::vector<std::array<int32_t, 16>>& dm_rolls, int32_t hp);

// (action, probability) pair output from the analytic computation.
struct ActionProb {
    ExecAction action;
    double     prob;
};

// Exact analytical action probability distribution (mirrors Python compute_action_probabilities).
// Float-exact: product enumeration order matches itertools.product(*all_dists_seq).
std::vector<ActionProb> cpp_compute_action_probabilities(
    const BattleState& state, int ai_idx);

// Deterministic analytic support: actions with p>0 in cpp_compute_action_probabilities.
// Does NOT mirror Python's sampler-based possible_ai_actions.
std::vector<ExecAction> cpp_possible_ai_actions(
    const BattleState& state, int ai_idx);

#endif // NUZLOCKE_AI_ANALYTIC_H
