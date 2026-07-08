// C1.7d Unit 2: pre-move gating (_pre_move_checks) ported from src/engine/core.py.
// Sleep counter/wake, freeze thaw, full paralysis, confusion snap/self-hit, attract immobilize.
// Mutates the active mon on side_idx (active slot 0; caller does any slot-swap). Returns whether the
// attacker can act. random_mode=true requires rng non-null; random_mode=false leaves rng unused.
#pragma once
#ifndef NUZLOCKE_MOVE_EXEC_PREMOVE_H
#define NUZLOCKE_MOVE_EXEC_PREMOVE_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include <cstdint>

// Injectable-luck subset consumed by the resolvers reached in _pre_move_checks.
// Each threshold mirrors the matching LuckProfile field; comparison direction is per-resolver
// (some return "good outcome" on chance>=threshold, see move_exec_premove.cpp).
// random_mode=true: rng must be non-null; random_mode=false: rng may be null (unused).
struct PreMoveLuck {
    double wake_threshold                 = 50.0;
    double defrost_threshold              = 20.0;
    double paralysis_threshold            = 50.0;
    double confusion_snap_threshold       = 50.0;
    double confusion_self_hit_threshold   = 50.0;
    double attract_threshold              = 50.0;
    double damage_roll                    = 0.5;  // confusion self-hit roll
    double proc_threshold                 = 0.0;  // threaded into the self-hit _apply_damage (Focus Band)
    bool   random_mode                    = false;
    NativeRng* rng                        = nullptr;  // non-null iff random_mode=true
};

// _pre_move_checks: returns true if the attacker on side_idx can act, false if blocked by a status or
// volatile. fire_type_move signals the chosen move thaws freeze (Fire-type / defrost-user moves). The
// move id is needed for the _SLEEP_USABLE_MOVES bypass. state supplies weather (sun thaw).
bool cpp_pre_move_checks(BattleState& state, int side_idx, const PreMoveLuck& luck,
                         bool fire_type_move, int32_t move);

#endif // NUZLOCKE_MOVE_EXEC_PREMOVE_H
