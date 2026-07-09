// C++ structs mirroring Python frozen dataclasses from src/state/ and src/engine/actions.py.
// Field names and order match sweep_io.py registry; enums carry same integer values as Python IntEnum/IntFlag.
// All enum fields stored as raw int32_t to avoid conflicts with generated-header enum definitions.
// D2 (2026-07-09): heap-owning members replaced with InlineVec so BattleState is trivially
// copyable (memcpy-able) for the RNG-bucketing solver. Capacities are hard game-semantics
// bounds; overflow aborts (fail-loud) — see inline_vec.h.
#pragma once
#ifndef NUZLOCKE_STATE_H
#define NUZLOCKE_STATE_H

#include <cstdint>

#include "inline_vec.h"

// ---------------------------------------------------------------------------
// PokemonState (src/state/pokemon.py)
// ---------------------------------------------------------------------------

// One entry in timed_volatiles: (VolatileEffect int value, turns_remaining OR payload).
// The int field is dual-purpose: a duration for tickers (0..8, -1=infinite) OR a payload
// (Move id for VE_CHARGING_MOVE, team_idx for VE_BOUND_SOURCE_ID/etc.), so it stays int32_t.
struct TimedVolatile {
    int32_t effect;  // VolatileEffect enum int value
    int32_t turns;
};

// Type entries: max 2 (dual-type mons). 3 for safety on Roost-restore transient combinations.
constexpr std::size_t POKEMON_TYPES_CAP = 3;
// TimedVolatile entries per mon: <= distinct VolatileEffect kinds (~25). 32 for headroom.
constexpr std::size_t POKEMON_TIMED_VOLATILES_CAP = 32;

struct PokemonState {
    // Required fields
    int32_t species = 0;   // Species int value
    int32_t nature  = 0;   // Nature int value
    // ivs: (hp,atk,def,spa,spd,spe) — encoded as __tuple__
    int32_t iv_hp = 0, iv_atk = 0, iv_def = 0, iv_spa = 0, iv_spd = 0, iv_spe = 0;
    int32_t gender = 0;    // GenderEnum int value

    // Optional construction fields
    int32_t level  = 50;
    int32_t exp    = 0;
    int32_t ability = 0;   // Ability int value
    int32_t item    = 0;   // Item int value
    int32_t status  = 0;   // Status int value

    // Move slots
    int32_t move_id0 = 0, move_id1 = 0, move_id2 = 0, move_id3 = 0;
    int32_t move_pp0 = 0, move_pp1 = 0, move_pp2 = 0, move_pp3 = 0;

    // Optional stats (null when not set in Python)
    bool has_stats = false;
    int32_t stat_hp = 0, stat_atk = 0, stat_def = 0, stat_spa = 0, stat_spd = 0, stat_spe = 0;

    bool has_max_hp = false;
    int32_t max_hp  = 0;

    bool has_hp = false;
    int32_t hp  = 0;

    // Optional types (null when not set)
    bool has_types = false;
    InlineVec<int32_t, POKEMON_TYPES_CAP> types;  // Type int values

    // stat_stages: tuple of 7 ints (Atk,Def,SpA,SpD,Spe,Acc,Eva)
    int32_t stage0 = 0, stage1 = 0, stage2 = 0, stage3 = 0, stage4 = 0, stage5 = 0, stage6 = 0;

    int32_t volatiles = 0;  // Volatile IntFlag bitmask

    InlineVec<TimedVolatile, POKEMON_TIMED_VOLATILES_CAP> timed_volatiles;

    int32_t turns_in_battle    = 0;
    int32_t toxic_turns        = 0;
    int32_t sleep_turns        = 0;
    int32_t confusion_turns    = 0;
    bool    is_rest_sleep      = false;
    int32_t locked_slot        = -1;
    int32_t charging_move_slot = -1;
    int32_t sub_hp             = 0;
    int32_t last_used_slot     = -1;
    bool    fainted            = false;
    bool    has_acted          = false;
    int32_t crit_stage         = 0;
    int32_t metronome_count    = 0;
    int32_t metronome_last_move = -1;
    int32_t mirror_move_last_move = -1;
    int32_t consumed_berry     = 0;   // Item int value

    bool    took_damage_this_turn      = false;
    bool    had_stat_lowered_this_turn = false;
    bool    had_stat_raised_this_turn  = false;
    bool    last_move_failed           = false;
    int32_t last_physical_damage_taken = 0;
    int32_t last_special_damage_taken  = 0;
    int32_t last_damage_taken          = 0;
    bool    sucker_punch_last_turn     = false;

    int32_t base_ability  = 0;  // Ability int value
    int32_t saved_ability = 0;  // Ability int value
    bool    is_mega       = false;
    int32_t moves_used    = 0;
    int32_t rollout_hits  = 0;
    bool    defense_curl_used = false;
    double  weight_kg_reduced = 0.0;
    int32_t protect_counter   = 0;
    int32_t stockpile_count   = 0;
    int32_t stockpile_def_boost = 0;
    int32_t stockpile_spd_boost = 0;
};

// ---------------------------------------------------------------------------
// SideState (src/state/side.py)
// ---------------------------------------------------------------------------

// SideCondition duration: 0..8 turns or -1 (infinite ability-set weather-side effects).
struct SideConditionEntry {
    int32_t condition;  // SideCondition int value
    int8_t  turns;
};

// Party size max (canonical Nuzlocke party = 6).
constexpr std::size_t SIDE_TEAM_CAP = 6;
// Active slots: singles=1, doubles=2.
constexpr std::size_t SIDE_ACTIVE_CAP = 2;
// SideCondition kinds <= 13 (see SC_* in effects_consts.h); 16 for headroom.
constexpr std::size_t SIDE_CONDITIONS_CAP = 16;
// Imprisoned moves: at most 4 per imprisoner, up to 2 imprisoners active per side (doubles).
constexpr std::size_t SIDE_IMPRISONED_MOVES_CAP = 8;

// Baton Pass transfer payload (Python side.py: baton_pass_data tuple[
//   tuple[int,...]*7 stat_stages, int volatiles_bitmask, tuple timed_volatiles,
//   int crit_stage, int sub_hp]).
// Encodes exactly the fields transferred; JSON codec still emits the original wire shape.
struct BatonPassData {
    int32_t stage0 = 0, stage1 = 0, stage2 = 0, stage3 = 0, stage4 = 0, stage5 = 0, stage6 = 0;
    int32_t volatiles_bitmask = 0;
    int32_t crit_stage = 0;
    int32_t sub_hp = 0;
    InlineVec<TimedVolatile, POKEMON_TIMED_VOLATILES_CAP> timed_volatiles;
};

struct SideState {
    InlineVec<PokemonState, SIDE_TEAM_CAP> team;
    int32_t format = 0;  // FormatEnum int value

    InlineVec<int32_t, SIDE_ACTIVE_CAP> active_indices;
    InlineVec<SideConditionEntry, SIDE_CONDITIONS_CAP> side_conditions;

    bool mega_used = false;

    // Baton Pass pending payload (typed; codec re-encodes the Python nested-tuple shape).
    bool          has_baton_pass_data = false;
    BatonPassData baton_pass_data;

    bool    ally_fainted_last_turn = false;

    // wish_pending: null or (turns_remaining, hp_to_heal, slot_index). Wish always resolves
    // on the next turn so turns is 0..2 -> int8_t.
    bool    has_wish_pending = false;
    int8_t  wish_turns = 0;
    int32_t wish_hp = 0, wish_slot = 0;

    // future_sight_pending: null or (turns_remaining, damage, Move int, target_slot). turns 0..3.
    bool    has_future_sight_pending = false;
    int8_t  fs_turns = 0;
    int32_t fs_damage = 0, fs_move = 0, fs_target_slot = 0;

    // imprisoned_moves: frozenset of Move int values (stored sorted).
    InlineVec<int32_t, SIDE_IMPRISONED_MOVES_CAP> imprisoned_moves;

    int32_t redirect_target          = -1;
    bool    redirect_is_rage_powder  = false;
};

// ---------------------------------------------------------------------------
// BattleState (src/state/battle.py)
// ---------------------------------------------------------------------------

// PseudoWeather duration: 0..8, -1=infinite.
struct PseudoWeatherEntry {
    int32_t effect;  // PseudoWeather int value
    int8_t  turns;
};

// PseudoWeather kinds: currently 2 (Trick Room, Gravity, plus Magic Room). 8 for headroom.
constexpr std::size_t BATTLE_PSEUDO_WEATHER_CAP = 8;
// Turn order: doubles has 2 movers per side => 4 entries.
constexpr std::size_t BATTLE_TURN_ORDER_CAP = 4;
// exp_participants: outer indexed by opponent active slot (<= SIDE_ACTIVE_CAP-ish but reserved
// for a full team of 6 across game — sized to team cap for safety); inner participant set
// size <= team size.
constexpr std::size_t BATTLE_EXP_PARTICIPANT_OUTER_CAP = SIDE_TEAM_CAP;
constexpr std::size_t BATTLE_EXP_PARTICIPANT_INNER_CAP = SIDE_TEAM_CAP;

// Inner set: sorted list of team indices contributing to a KO's EXP payout.
struct ExpParticipantSet {
    InlineVec<int32_t, BATTLE_EXP_PARTICIPANT_INNER_CAP> members;

    bool operator==(const ExpParticipantSet& o) const { return members == o.members; }
    bool operator!=(const ExpParticipantSet& o) const { return !(*this == o); }
};

struct BattleState {
    SideState side0, side1;

    int32_t weather       = 0;
    int8_t  weather_turns = 0;
    int32_t terrain       = 0;
    int8_t  terrain_turns = 0;

    InlineVec<PseudoWeatherEntry, BATTLE_PSEUDO_WEATHER_CAP> pseudo_weather;

    int32_t turn_number                 = 1;
    int32_t echoed_voice_multiplier     = 0;
    bool    echoed_voice_used_this_turn = false;
    int32_t battle_last_move            = -1;
    int32_t format                      = 0;  // FormatEnum int value

    InlineVec<int32_t, BATTLE_TURN_ORDER_CAP> turn_order;
    InlineVec<int32_t, BATTLE_TURN_ORDER_CAP> prev_turn_order;  // stored as __tuple__

    bool    is_trainer_battle = true;

    bool    has_level_cap = false;
    int32_t level_cap     = 0;

    // exp_participants: tuple of frozensets of int (each inner set sorted).
    InlineVec<ExpParticipantSet, BATTLE_EXP_PARTICIPANT_OUTER_CAP> exp_participants;
};

#endif // NUZLOCKE_STATE_H
