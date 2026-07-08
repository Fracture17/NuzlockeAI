// C1.7c: pure leaf helpers ported from src/engine/core.py.
// _compute_variable_bp / _compute_fixed_damage / _resolve_targets, plus the deterministic
// resolve_psywave_roll. No state mutation; byte-identical integer/list parity with Python.
#pragma once
#ifndef NUZLOCKE_CORE_LEAF_H
#define NUZLOCKE_CORE_LEAF_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include "oracle.h"       // OracleOverrides, NeedsRNG (SPEED_TIE pause/override)
#include <cstdint>
#include <utility>
#include <vector>

// Minimal luck subset for Psywave: injectable roll + random_mode guard.
// random_mode=true: rng must be non-null; random_mode=false: rng may be null.
struct PsywaveLuck {
    double psywave_roll = 0.5;
    bool   random_mode  = false;
    NativeRng* rng      = nullptr;  // non-null iff random_mode=true
};

// Psywave roll: random_mode draws rng->random(); deterministic returns luck.psywave_roll.
double cpp_resolve_psywave_roll(const PsywaveLuck& luck);

// Variable base-power moves (mirror _compute_variable_bp). Returns 0 if not applicable.
// defender_idx<0 means None; defender_action_is_switch flags the Fishious/Bolt Beak switch read.
int32_t cpp_compute_variable_bp(int32_t move, const PokemonState& attacker,
                                const PokemonState& defender, const BattleState& state,
                                int side_idx, int defender_idx,
                                bool defender_action_is_switch);

// Fixed-damage moves (mirror _compute_fixed_damage). Returns -1 if not applicable, -2 if fails.
int32_t cpp_compute_fixed_damage(int32_t move, const PokemonState& attacker,
                                 const PokemonState& defender, const BattleState& state,
                                 int side_idx, const PsywaveLuck& luck);

// Mirrors core.py _FIXED_DAMAGE_MOVES: true iff cpp_compute_fixed_damage handles the move.
bool cpp_is_fixed_damage_move(int32_t move);

// Move targets (mirror _resolve_targets). Returns (defender_side_idx, defender_active_slot) pairs.
// target_side/target_slot are the flat Action fields.
// RANDOM_NORMAL multi-foe: random_mode=true picks via rng->choice; controlled mode throws (unported).
std::vector<std::pair<int32_t, int32_t>> cpp_resolve_targets(
    const BattleState& state, int side_idx, int source_slot,
    int32_t move, int target_side, int target_slot,
    bool random_mode = false, NativeRng* rng = nullptr);

// Mirrors core.py _move_has_target: true if the move has at least one live target.
// Draw-free (never consumes the RANDOM_NORMAL target roll). SELF/ALLY_SIDE/FOE_SIDE
// always true. Damaging moves with no live target must fail ("no_target").
bool cpp_move_has_target(const BattleState& state, int side_idx, int source_slot,
                         int32_t move, int target_side, int target_slot);

// ---------------------------------------------------------------------------
// C1.7c Unit B: turn-order helpers (_check_priority_item / _build_queue chain).
// ---------------------------------------------------------------------------

// Flat Action mirror (src/engine/actions.py Action subset used by turn order).
struct ActionC {
    int32_t kind = 0;          // ActionKind: 0=MOVE, 1=SWITCH
    int32_t move_slot = -1;
    int32_t target_slot = 0;
    int32_t switch_to_slot = -1;
    int32_t source_slot = 0;
    int32_t target_side = -1;
};

// Per-side luck subset referenced by the turn-order code.
struct TurnLuck {
    double quick_claw_threshold = 50.0;
    double secondary_threshold  = 50.0;
    int32_t luck_tier           = 1;
    bool random_mode            = false;
    NativeRng* rng              = nullptr;  // non-null iff random_mode=true (Stage A2)
};

// Rich per-entry metadata used by dynamic queue selection. Tiebreaker and priority-item flags
// are resolved once at build time (Custap may be consumed, Quick Draw RNG drawn) and reused.
struct Entry {
    int side_idx;
    int source_slot;
    ActionC action;
    TurnLuck luck;
    double tie;
    bool priority_item_fires;
    bool quick_draw_fires;
};

// _effective_speed (mirror src/engine/_helpers.py). Pure int speed for the priority bracket.
int32_t cpp_effective_speed(const PokemonState& mon, const SideState& side,
                            const BattleState& state);

// _check_priority_item: Quick Claw / Custap. MUTATES state (consumes Custap). Returns the bool.
bool cpp_check_priority_item(BattleState& state, int side_idx, const ActionC& action,
                             const TurnLuck& luck, int source_slot);

// cpp_build_pending_entries: resolve per-entry metadata once (tiebreaker, priority item, Quick Draw).
// MUTATES state (Custap consumed). Does NOT sort. Python _build_pending_entries was deleted;
// the tiebreaker logic here mirrors Python _build_queue's resolve_speed_tiebreaker calls.
std::vector<Entry> cpp_build_pending_entries(
    BattleState& state,
    const std::vector<ActionC>& actions_p1, const std::vector<ActionC>& actions_p2,
    const TurnLuck& luck_p1, const TurnLuck& luck_p2);

// _select_next_action: pick the highest-priority entry from pending against current state.
// Speed-tie handling (SPEED_TIE oracle):
//   - overrides->speed_tie set: resolve ALL ties by the ordering's rank (both modes).
//   - else random_mode: native tiebreaker (the per-entry tie field) resolves it.
//   - else controlled cross-side MOVE tie: throw NeedsRNG{SPEED_TIE} so the driver pauses.
// On equal sort keys, returns the FIRST element achieving the max (matches Python max + stable_sort).
Entry cpp_select_next_action(const BattleState& state, std::vector<Entry>& pending,
                             const OracleOverrides* overrides = nullptr);

#endif // NUZLOCKE_CORE_LEAF_H
