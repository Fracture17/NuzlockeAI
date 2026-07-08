// Typed JSON codec: from_json/to_json for the BattleState graph using sweep_io.py wire format.
// Tags: __type__ for dataclasses, __enum__ for enums, __tuple__, __frozenset__, __dict__.
// Also provides luck decoders shared by module.cpp, game_driver.cpp, and bench_driver.cpp.
// Throws std::runtime_error on unknown tags, missing fields, or type mismatches.
#pragma once
#ifndef NUZLOCKE_CODEC_H
#define NUZLOCKE_CODEC_H

#include <string>
#include <nlohmann/json.hpp>
#include "state.h"
#include "move_exec_damage.h"  // DamageLoopLuck
#include "core_leaf.h"         // TurnLuck

// Decode a JSON string (tagged wire format) into a typed BattleState.
BattleState battle_state_from_json(const std::string& s);

// Encode a typed BattleState into the tagged wire format JSON string.
std::string battle_state_to_json(const BattleState& state);

// Decode a DamageLoopLuck from its JSON dict (sweep_io DamageLoopLuck payload).
DamageLoopLuck damage_luck_from_json(const nlohmann::json& lj);

// Decode a TurnLuck from its JSON dict (sweep_io TurnLuck payload).
TurnLuck turn_luck_from_json(const nlohmann::json& lj);

#endif // NUZLOCKE_CODEC_H
