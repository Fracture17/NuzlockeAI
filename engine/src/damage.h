// C++ port of src/engine/damage.py — calculate_damage and helpers.
// Exact integer parity with Python: uses double + floor wherever Python does.
#pragma once
#ifndef NUZLOCKE_DAMAGE_H
#define NUZLOCKE_DAMAGE_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include <cstdint>
#include <optional>

// LuckProfile fields needed for damage resolution (subset of Python LuckProfile).
// random_mode=true: rng must be non-null; random_mode=false: rng may be null.
struct LuckProfileC {
    double  crit_threshold   = 50.0;
    double  damage_roll      = 0.5;
    double  proc_threshold   = 50.0;   // used for Shell Side Arm 50/50
    bool    random_mode      = false;
    double  multi_hit_roll   = 0.5;    // mirrors Python multi_hit_roll; 0.0=min hits, 0.5=mid, 1.0=max
    NativeRng* rng           = nullptr;  // non-null iff random_mode=true
};

// Effective stat: applies stage multiplier to pokemon.stats[stat_idx].
// stat_idx: 1=ATK, 2=DEF, 3=SPA, 4=SPD (HP/SPE not used for damage formula).
// is_crit: clamps unfavorable stages on offensive/defensive stats.
int32_t cpp_effective_stat(const PokemonState& pokemon, int stat_idx, bool is_crit = false);

// Main damage function — mirrors Python calculate_damage signature exactly.
// Returns 0 for immune matchups, otherwise returns the damage dealt (≥ 1).
// def_side_idx: -1 means None (screens, Analytic, Friend Guard skipped).
// roll_index: -1 means None (derive from atk_luck.damage_roll).
// crit_override: -1 = resolve internally (legacy callers); 0 = forced non-crit; 1 = forced crit.
//   When >= 0, skips both rng_resolve_crit and the Merciless override (caller already applied them).
int32_t cpp_calculate_damage(
    const PokemonState& attacker,
    int32_t             move_id,
    const PokemonState& defender,
    const BattleState&  state,
    const LuckProfileC& atk_luck,
    const LuckProfileC& def_luck,
    int32_t             bp_override,    // 0 = no override
    int32_t             def_side_idx,   // -1 = None
    bool                spread_hit,
    int32_t             roll_index,     // -1 = None
    bool                ai_scoring_view,
    int32_t             crit_override = -1  // -1 = resolve internally
);

// Type-effectiveness product for an attack (port of _check_type_immunity).
// Returns the cumulative effectiveness multiplier (0.0 = immune). Used by
// post-hit Weakness Policy, which fires iff the result is > 1.0.
double cpp_check_type_immunity(
    const PokemonState& attacker, int32_t move_id, int32_t move_type,
    const PokemonState& defender, const BattleState& state);

// Natural Gift type for the given item. Returns -1 if the item is not a berry with NG data.
// Used by pdg_resolve_move_type so type immunity is checked against the actual berry type.
int32_t cpp_natural_gift_type(int32_t item_id);

// Hidden Power type from a Pokemon's IVs. Shared by damage.cpp and move_exec_guards.cpp.
int32_t hidden_power_type(const PokemonState& mon);

#endif // NUZLOCKE_DAMAGE_H
