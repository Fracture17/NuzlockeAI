// C1.7d Unit 5: the move-execution dispatcher, ported from src/engine/core.py.
// Covers _execute_action (+ slot-swap + EXP flush), _execute_action_body (Truant, Gravity, pre-move
// gating, Choice/Assault Vest/Natural Gift, PP/Pressure/Leppa, last-move record, Nature Power/Copycat/
// Mirror Move redirects, status vs damage vs fixed-damage dispatch), _handle_status_action,
// _handle_switch_action, _handle_recharge_action, and _apply_dancer_trigger. Mutates the live
// BattleState. random_mode draws via NativeRng; uncontrolled-oracle branches throw "unported: ...".
#pragma once
#ifndef NUZLOCKE_MOVE_EXEC_H
#define NUZLOCKE_MOVE_EXEC_H

#include "state.h"
#include "move_exec_guards.h"   // ExecCtx
#include "move_exec_damage.h"   // DamageLoopLuck, PendingSwitch (via effects.h)
#include "effects.h"            // PendingSwitch
#include <cstdint>
#include <vector>

// Flat Action mirror for execute_action (src/engine/actions.py subset used by move execution).
struct ExecAction {
    int32_t kind           = 0;   // ActionKind: 0=MOVE, 1=SWITCH
    int32_t move_slot      = -1;
    int32_t move_override  = -1;  // -1 means None
    int32_t switch_to_slot = -1;
    int32_t target_side    = -1;
    int32_t target_slot    = 0;
    int32_t source_slot    = 0;   // which active slot within the side (0 in singles, 0 or 1 in doubles)
    bool    mega           = false;  // mega-evolve before moving (Action.mega); GameDriver folds
                                     // per-side any(mega) into the run_one_turn mega_pX scalars.
};

// _execute_action: apply one action (move or switch) on side_idx, acting slot source_slot. Threads
// the full deterministic luck (DamageLoopLuck is the superset used to rebuild sub-luck structs).
// EXP is flushed (via ctx.exp_participants) exactly once at each return, mirroring Python.
void cpp_execute_action(BattleState& state, int side_idx, const ExecAction& action,
                        DamageLoopLuck& luck_atk, DamageLoopLuck& luck_def,
                        std::vector<PendingSwitch>& pending_switches,
                        ExecCtx& ctx, int source_slot);

// _apply_dancer_trigger: re-execute a dance move for every other active Dancer holder (from_dancer=
// True to prevent re-triggering). Declared here so move_exec_damage.cpp can call it after a damaging
// dance move. luck_atk/luck_def are the full (superset) luck for the copied execution.
void cpp_apply_dancer_trigger(BattleState& state, int original_user_idx, int32_t move,
                              ExecCtx& ctx, const DamageLoopLuck& luck_atk,
                              const DamageLoopLuck& luck_def,
                              std::vector<PendingSwitch>& pending_switches);

// Sub-move option builders for Metronome/Sleep Talk native resolution (mirroring
// src/data/moves.py metronome_options() and sleep_talk_options()).
std::vector<int> metronome_options();
std::vector<int> sleep_talk_options(const PokemonState& mon);

#endif // NUZLOCKE_MOVE_EXEC_H
