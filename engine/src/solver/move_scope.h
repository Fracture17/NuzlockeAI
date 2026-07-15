// Shared move-scope classifier: the SCOPE_* bitmask plus the HP-dependent and
// binding/trapping move lists. Extracted from analytic.cpp so the bucket concede
// detectors reuse one source of truth (no forked move-id lists).
#pragma once
#ifndef NUZLOCKE_SOLVER_MOVE_SCOPE_H
#define NUZLOCKE_SOLVER_MOVE_SCOPE_H

#include <cstdint>

// ---------------------------------------------------------------------------
// Scope-reason bitmask: each bit marks a mechanic that removes a move from the
// "simple single-hit damaging move" allowlist. Callers accumulate every bit.
// ---------------------------------------------------------------------------

constexpr uint32_t SCOPE_MULTI_HIT          = (1u << 0);  // player or opp has multi-hit move
constexpr uint32_t SCOPE_ACCURACY_LT100     = (1u << 1);  // move accuracy < 100 (and != -1)
constexpr uint32_t SCOPE_SECONDARY          = (1u << 2);  // move has non-trivial secondary effect
constexpr uint32_t SCOPE_RECOIL             = (1u << 3);  // move has recoil
constexpr uint32_t SCOPE_DRAIN              = (1u << 4);  // move has drain
constexpr uint32_t SCOPE_BINDING            = (1u << 5);  // move is a binding/trapping move
constexpr uint32_t SCOPE_CHARGE_TURN        = (1u << 6);  // move requires a charge turn
constexpr uint32_t SCOPE_PRIORITY          = (1u << 7);   // move has non-zero priority
constexpr uint32_t SCOPE_HP_DEP_BP          = (1u << 8);  // move has HP-dependent base power
constexpr uint32_t SCOPE_WEATHER_SCREEN     = (1u << 9);  // active weather, terrain, or screens
constexpr uint32_t SCOPE_ENTRY_DIRTY        = (1u << 10); // non-clean entry (status/boost/volatile/side cond)
constexpr uint32_t SCOPE_ITEM_NOT_ALLOWED   = (1u << 11); // player or opp item outside allowlist
constexpr uint32_t SCOPE_OPP_NO_DAMAGE      = (1u << 12); // opp has no effective damaging move (AT_STALL)
constexpr uint32_t SCOPE_NONDEFAULT_QUESTION = (1u << 13); // non-default Question field set
constexpr uint32_t SCOPE_RESIDUAL_UNKNOWN   = (1u << 14); // hp_thresholds residual_unknown on either side

// ---------------------------------------------------------------------------
// Move classifiers.
// ---------------------------------------------------------------------------

// Accumulated scope bits for one move id (0 for an in-scope move or move_id <= 0).
uint32_t check_move_scope(int32_t move_id);

// True iff the move's effective damage depends on HP (HP-scaled base power or
// fixed-damage / reflect moves whose table value is unsound). Mirrors HP_DEP_MOVES.
bool is_hp_dep_move(int32_t move_id);

// True iff the move is a binding/trapping move (multi-turn chip).
bool is_binding_move(int32_t move_id);

#endif // NUZLOCKE_SOLVER_MOVE_SCOPE_H
