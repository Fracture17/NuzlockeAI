// Concede detectors (spec §5 / plan Task 6). concede_tags() unions the firing tags
// over both bucket corners; a nonzero result marks the whole (bucket, player_move)
// branch FAIL in Expand. Player = side 0, AI = side 1. §5.1 stunlock is PLAYER-side
// only. NO overkill tag exists — overkill THROWS in Expand (record overkill_coupling_throw).
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_CONCEDE_H
#define NUZLOCKE_SOLVER_BUCKET_CONCEDE_H

#include "move_exec.h"   // ExecAction
#include "state.h"

#include <cstdint>
#include <string>

// ---------------------------------------------------------------------------
// Concession tag bits.
// ---------------------------------------------------------------------------

constexpr uint32_t CONCEDE_NONE            = 0;
constexpr uint32_t CONCEDE_SLEEP_ACTING    = 1u << 0;  // player status==SLEEP (NOT Yawn-pending)
constexpr uint32_t CONCEDE_FREEZE          = 1u << 1;
constexpr uint32_t CONCEDE_PARALYSIS       = 1u << 2;
constexpr uint32_t CONCEDE_CONFUSION       = 1u << 3;  // player VOLATILE_CONFUSED only
constexpr uint32_t CONCEDE_ATTRACT         = 1u << 4;
constexpr uint32_t CONCEDE_LOCK_MOVE       = 1u << 5;  // Thrash(37)/Petal Dance(80)/Outrage(200)
constexpr uint32_t CONCEDE_RECHARGE        = 1u << 6;  // Hyper Beam family or V_RECHARGING(256)
constexpr uint32_t CONCEDE_FLINCH_SLOWER   = 1u << 7;
constexpr uint32_t CONCEDE_ORDER_RNG       = 1u << 8;  // speed tie / Quick Claw(217) / Quick Draw(259)
constexpr uint32_t CONCEDE_HP_DEP_MOVE     = 1u << 9;  // §5.2 minus supported fixed-damage
constexpr uint32_t CONCEDE_MULTI_HIT_HARD  = 1u << 10;
constexpr uint32_t CONCEDE_SUBSTITUTE      = 1u << 11;
constexpr uint32_t CONCEDE_DMG_TABLE_CAVEAT= 1u << 12;

// Union of every firing tag across both corners for the (bucket, player_move) branch.
// Matches expand.h's ConcedeFn signature. All detectors are d-only reads except
// MULTI_HIT_HARD (reads the damage_table); the lo|hi union exists to cover it.
uint32_t concede_tags(const BattleState& lo, const BattleState& hi, const ExecAction& player_move);

// Human-readable "SLEEP_ACTING|ORDER_RNG"; "" for mask 0.
std::string concession_tag_names(uint32_t mask);

#endif // NUZLOCKE_SOLVER_BUCKET_CONCEDE_H
