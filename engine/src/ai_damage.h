// Stage 1 AI damage machinery: deterministic damage scoring helpers consumed by the AI scorer.
// Ports src/queries.py (expected_damage, damage_roll_values) and src/ai.py
// (_fixed_damage_rolls, _ai_assumed_hit_count, _build_damage_context,
// _compute_highest_damage_probs) plus thin query wrappers for later stages.
#pragma once
#ifndef NUZLOCKE_AI_DAMAGE_H
#define NUZLOCKE_AI_DAMAGE_H

#include "state.h"
#include "damage.h"
#include "move_exec.h"   // ExecAction
#include "../generated/move_data.h"

#include <array>
#include <cstdint>
#include <optional>
#include <vector>

// ---------------------------------------------------------------------------
// queries.py ports
// ---------------------------------------------------------------------------

// Total damage across all hits (mirrors Python expected_damage).
// roll_index: -1 = use luck's damage_roll for every hit.
// hit_count_override: -1 = resolve via resolve_hit_count; >=0 = force this count.
// rollout_max_bp: if true and move==ROLLOUT, override BP to 480 (AI Bug #25).
int32_t cpp_expected_damage(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    int32_t roll_index,       // -1 = none
    bool    rollout_max_bp,
    int32_t hit_count_override // -1 = none
);

// 16-element array of per-roll damage totals (roll_index 0..15).
std::array<int32_t, 16> cpp_damage_roll_values(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    int32_t hit_count_override  // -1 = none
);

// ---------------------------------------------------------------------------
// ai.py ports
// ---------------------------------------------------------------------------

// 16-element fixed-damage array for a proactive fixed-damage move, or nullopt if not applicable.
// Type-immune matchup yields [0]*16. Only PSYWAVE varies across rolls (banker's rounding).
std::optional<std::array<int32_t, 16>> cpp_fixed_damage_rolls(
    int32_t move_id, const MoveData& md,
    const PokemonState& ai_mon, const PokemonState& pl_mon
);

// AI's assumed hit count for HD ranking (mirrors _ai_assumed_hit_count).
int32_t cpp_ai_assumed_hit_count(const PokemonState& atk, const MoveData& md);

// Per-move damage context for the AI scorer.
struct DamageContext {
    std::vector<int32_t>                   slots;
    std::vector<std::array<int32_t, 16>>   roll_arrays;
    std::vector<int32_t>                   assumed_hit_counts;
};

// Build damage context for ai_idx (mirrors _build_damage_context).
// actions: legal ExecActions for ai_idx (from cpp_enumerate_legal_actions).
DamageContext cpp_build_damage_context(
    const BattleState& state, int ai_idx,
    const std::vector<ExecAction>& actions
);

// Analytically compute P(move i is highest AND kills, highest AND no-kill) for each move.
// Returns vector of (p_kill, p_nokill) pairs parallel to roll_arrays.
// hp: defender's current HP (cap for ranking; raw damage compared for KO).
std::vector<std::pair<double, double>> cpp_compute_highest_damage_probs(
    const std::vector<std::array<int32_t, 16>>& roll_arrays, int32_t hp
);

// ---------------------------------------------------------------------------
// Thin query wrappers (used by Stage 3 and later)
// ---------------------------------------------------------------------------

// Effective speed for a Pokemon (mirrors queries.effective_speed).
int32_t cpp_ai_effective_speed(
    const PokemonState& mon, const SideState& side, const BattleState& state
);

// True if attacker can KO defender with move under luck (mirrors queries.can_ko).
bool cpp_ai_can_ko(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck, bool rollout_max_bp
);

// Best-damage move (highest expected_damage > 0), or 0 (Move.NONE) if none.
// Mirrors queries.best_damage_move. check_pp: skip moves with pp==0.
int32_t cpp_ai_best_damage_move(
    const PokemonState& atk, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    bool check_pp, bool rollout_max_bp
);

#endif // NUZLOCKE_AI_DAMAGE_H
