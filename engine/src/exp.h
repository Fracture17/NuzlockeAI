// C++ port of EXP distribution (src/engine/exp.py, C1.7a).
// Mirrors calc_exp_gain / recalc_stats / apply_exp_gain / distribute_exp / flush_opponent_faint_exp
// exactly so whole-BattleState equality holds. Python log() calls are state-neutral and omitted.
#pragma once
#ifndef NUZLOCKE_EXP_H
#define NUZLOCKE_EXP_H

#include "state.h"
#include <cstdint>

// Total EXP required to reach `level` for the given growth rate (mirrors exp_for_level).
int64_t cpp_exp_for_level(int32_t growth_rate, int32_t level);

// Gen VIII EXP formula (mirrors calc_exp_gain). is_ot/is_unevolved default to Python defaults.
int32_t cpp_calc_exp_gain(int32_t fainted_species, int32_t fainted_level, int32_t winner_level,
                          bool is_ot = true, bool is_unevolved = false);

// Recompute stats/max_hp/hp for a level (mirrors recalc_stats); mutates `mon` in place.
void cpp_recalc_stats(PokemonState& mon);

// Add exp to `mon`, level up respecting level_cap + hard 100 cap (mirrors apply_exp_gain).
// `has_level_cap`/`level_cap` mirror Optional[int]. Returns net EXP gained; mutates `mon`.
int32_t cpp_apply_exp_gain(PokemonState& mon, int32_t exp_amount,
                           bool has_level_cap, int32_t level_cap, int32_t growth_rate);

// Award EXP to participants of a fainted opponent slot (mirrors distribute_exp).
// Clears the slot's participant set in `exp_participants` after distribution (idempotent).
// allow_fainted_winners=true lets fainted participants still receive EXP (residual-phase flushes).
void cpp_distribute_exp(BattleState& state, int fainted_team_idx,
                        std::vector<std::vector<int32_t>>& exp_participants,
                        bool allow_fainted_winners = false);

// Scan side-1 active mons for fainted ones and award EXP (mirrors flush_opponent_faint_exp).
void cpp_flush_opponent_faint_exp(BattleState& state,
                                  std::vector<std::vector<int32_t>>& exp_participants,
                                  bool allow_fainted_winners = false);

#endif // NUZLOCKE_EXP_H
