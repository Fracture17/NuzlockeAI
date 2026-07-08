// C++ structs mirroring Python frozen dataclasses from src/state/ and src/engine/actions.py.
// Field names and order match sweep_io.py registry; enums carry same integer values as Python IntEnum/IntFlag.
// All enum fields stored as raw int32_t to avoid conflicts with generated-header enum definitions.
#pragma once
#ifndef NUZLOCKE_STATE_H
#define NUZLOCKE_STATE_H

#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

// ---------------------------------------------------------------------------
// PokemonState (src/state/pokemon.py)
// ---------------------------------------------------------------------------

// One entry in timed_volatiles: (VolatileEffect int value, turns_remaining)
struct TimedVolatile {
    int32_t effect;  // VolatileEffect enum int value
    int32_t turns;
};

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
    std::vector<int32_t> types;  // Type int values

    // stat_stages: tuple of 7 ints (Atk,Def,SpA,SpD,Spe,Acc,Eva)
    int32_t stage0 = 0, stage1 = 0, stage2 = 0, stage3 = 0, stage4 = 0, stage5 = 0, stage6 = 0;

    int32_t volatiles = 0;  // Volatile IntFlag bitmask

    std::vector<TimedVolatile> timed_volatiles;

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

struct SideConditionEntry {
    int32_t condition;  // SideCondition int value
    int32_t turns;
};

struct SideState {
    std::vector<PokemonState> team;
    int32_t format = 0;  // FormatEnum int value

    std::vector<int32_t> active_indices;
    std::vector<SideConditionEntry> side_conditions;

    bool mega_used = false;

    // baton_pass_data: null or complex nested tuple — stored as raw JSON to preserve structure
    bool          has_baton_pass_data = false;
    nlohmann::json baton_pass_data_raw;

    bool    ally_fainted_last_turn = false;

    // wish_pending: null or (turns, hp, slot)
    bool    has_wish_pending = false;
    int32_t wish_turns = 0, wish_hp = 0, wish_slot = 0;

    // future_sight_pending: null or (turns, damage, Move int, target_slot)
    bool    has_future_sight_pending = false;
    int32_t fs_turns = 0, fs_damage = 0, fs_move = 0, fs_target_slot = 0;

    // imprisoned_moves: frozenset of Move int values (stored sorted)
    std::vector<int32_t> imprisoned_moves;

    int32_t redirect_target          = -1;
    bool    redirect_is_rage_powder  = false;
};

// ---------------------------------------------------------------------------
// BattleState (src/state/battle.py)
// ---------------------------------------------------------------------------

struct PseudoWeatherEntry {
    int32_t effect;  // PseudoWeather int value
    int32_t turns;
};

struct BattleState {
    SideState side0, side1;

    int32_t weather       = 0;
    int32_t weather_turns = 0;
    int32_t terrain       = 0;
    int32_t terrain_turns = 0;

    std::vector<PseudoWeatherEntry> pseudo_weather;

    int32_t turn_number                 = 1;
    int32_t echoed_voice_multiplier     = 0;
    bool    echoed_voice_used_this_turn = false;
    int32_t battle_last_move            = -1;
    int32_t format                      = 0;  // FormatEnum int value

    std::vector<int32_t> turn_order;
    std::vector<int32_t> prev_turn_order;  // stored as __tuple__

    bool    is_trainer_battle = true;

    bool    has_level_cap = false;
    int32_t level_cap     = 0;

    // exp_participants: tuple of frozensets of int (each inner vec sorted)
    std::vector<std::vector<int32_t>> exp_participants;
};

#endif // NUZLOCKE_STATE_H
