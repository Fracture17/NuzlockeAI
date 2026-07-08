// Shared inline helpers and constants for ai_damage.cpp and ai_scorer.cpp.
// Extracted from ai_damage.cpp to avoid duplication. Both files include this header.
#pragma once
#ifndef NUZLOCKE_AI_SHARED_H
#define NUZLOCKE_AI_SHARED_H

#include "state.h"
#include "../generated/move_data.h"

#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Move/item/ability/status integer constants (mirrors Python enums)
// ---------------------------------------------------------------------------

// Move IDs
static constexpr int32_t MV_NONE             = 0;
static constexpr int32_t MV_PAYBACK          = 371;
static constexpr int32_t MV_BOLT_BEAK        = 754;
static constexpr int32_t MV_FISHIOUS_REND    = 755;
static constexpr int32_t MV_TRIPLE_AXEL      = 813;
static constexpr int32_t MV_ROLLOUT          = 205;
static constexpr int32_t MV_SONIC_BOOM       = 49;
static constexpr int32_t MV_DRAGON_RAGE      = 82;
static constexpr int32_t MV_SEISMIC_TOSS     = 69;
static constexpr int32_t MV_NIGHT_SHADE      = 101;
static constexpr int32_t MV_SUPER_FANG       = 162;
static constexpr int32_t MV_NATURE_S_MADNESS = 717;
static constexpr int32_t MV_PSYWAVE          = 149;
static constexpr int32_t MV_VENOSHOCK        = 474;
static constexpr int32_t MV_BELCH            = 562;
static constexpr int32_t MV_EXPLOSION        = 153;
static constexpr int32_t MV_SELF_DESTRUCT    = 120;
static constexpr int32_t MV_MISTY_EXPLOSION  = 802;
static constexpr int32_t MV_FINAL_GAMBIT     = 515;
static constexpr int32_t MV_METEOR_BEAM      = 800;
static constexpr int32_t MV_RELIC_SONG       = 547;
static constexpr int32_t MV_FUTURE_SIGHT     = 248;

// Trapping moves (_TRAPPING_MOVES in ai.py)
static constexpr int32_t TRAPPING_MOVES[] = {
    250,  // WHIRLPOOL
    83,   // FIRE_SPIN
    328,  // SAND_TOMB
    463,  // MAGMA_STORM
    611,  // INFESTATION
    128,  // CLAMP
    35,   // WRAP
    20,   // BIND
};
static constexpr int N_TRAPPING = 8;

// MoveTag bitmask values (mirrors Python MoveTag IntFlag)
static constexpr int32_t TAG_DAMAGE = 1;

// Item IDs
static constexpr int32_t ITM_NONE        = 0;
static constexpr int32_t ITM_RING_TARGET = 543;

// Ability IDs
static constexpr int32_t AB_SKILL_LINK = 92;

// Status IDs (mirrors Python Status IntEnum)
static constexpr int32_t STATUS_POISON = 4;
static constexpr int32_t STATUS_TOXIC  = 5;

// AI Bug #8 boosted BPs
static constexpr int32_t PAYBACK_BOOSTED_BP   = 100;
static constexpr int32_t FANG_MOVE_BOOSTED_BP = 170;

// Triple Axel per-hit BPs
static constexpr int32_t TRIPLE_AXEL_BPS[3] = {20, 40, 60};

// ---------------------------------------------------------------------------
// Inline helpers (mirror ai_damage.cpp file-static helpers)
// ---------------------------------------------------------------------------

// Binary-search the MOVE_TABLE (sorted by move_id). Returns nullptr if not found.
inline const MoveData* ai_move_data_get(int32_t move_id) {
    int lo = 0, hi = 813;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid;
    }
    if (lo < 813 && MOVE_TABLE[lo].move_id == move_id) return &MOVE_TABLE[lo];
    return nullptr;
}

inline const MoveData& ai_move_data_or_throw(int32_t move_id) {
    const MoveData* md = ai_move_data_get(move_id);
    if (!md) throw std::runtime_error("ai: move id " + std::to_string(move_id) + " not found");
    return *md;
}

// Banker's rounding (round-half-to-even), mirroring Python's built-in round().
inline int64_t banker_round(double x) {
    double fl = std::floor(x);
    double diff = x - fl;
    if (diff < 0.5) return (int64_t)fl;
    if (diff > 0.5) return (int64_t)fl + 1;
    int64_t n = (int64_t)fl;
    return (n % 2 == 0) ? n : n + 1;
}

// Access the active Pokémon for a given side index.
inline const SideState& side_at(const BattleState& state, int idx) {
    return idx == 0 ? state.side0 : state.side1;
}

inline const PokemonState& active_mon(const BattleState& state, int side_idx) {
    const SideState& s = side_at(state, side_idx);
    return s.team[s.active_indices[0]];
}

// True if move_id is in the trapping set.
inline bool is_trapping(int32_t move_id) {
    for (int i = 0; i < N_TRAPPING; ++i)
        if (TRAPPING_MOVES[i] == move_id) return true;
    return false;
}

// True if move_id is in _EXCLUDED_FROM_DAMAGE_RANK (ai.py:58-62).
inline bool is_excluded_from_damage_rank(int32_t move_id) {
    switch (move_id) {
        case MV_EXPLOSION: case MV_SELF_DESTRUCT: case MV_MISTY_EXPLOSION:
        case MV_FINAL_GAMBIT: case MV_ROLLOUT: case MV_METEOR_BEAM:
        case MV_RELIC_SONG: case MV_FUTURE_SIGHT:
            return true;
        default:
            return is_trapping(move_id);
    }
}

// True if move_id is a proactive fixed-damage move (_FIXED_DAMAGE_RANK_MOVES in ai.py).
inline bool is_fixed_damage_rank_move(int32_t move_id) {
    switch (move_id) {
        case MV_SONIC_BOOM: case MV_DRAGON_RAGE: case MV_SEISMIC_TOSS:
        case MV_NIGHT_SHADE: case MV_SUPER_FANG: case MV_NATURE_S_MADNESS:
        case MV_PSYWAVE:
            return true;
        default:
            return false;
    }
}

// Get move_id from a PokemonState by slot index.
inline int32_t move_id_at(const PokemonState& mon, int slot) {
    switch (slot) {
        case 0: return mon.move_id0; case 1: return mon.move_id1;
        case 2: return mon.move_id2; case 3: return mon.move_id3;
        default: return MV_NONE;
    }
}

// Get move_pp from a PokemonState by slot index.
inline int32_t move_pp_at(const PokemonState& mon, int slot) {
    switch (slot) {
        case 0: return mon.move_pp0; case 1: return mon.move_pp1;
        case 2: return mon.move_pp2; case 3: return mon.move_pp3;
        default: return 0;
    }
}

#endif // NUZLOCKE_AI_SHARED_H
