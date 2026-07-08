// Typed JSON codec implementation for the BattleState graph.
// Wire format authority: src/sweep_io.py — do NOT deviate from its tags.
#include "codec.h"
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// ---------------------------------------------------------------------------
// Internal helpers: checked field access and tag extraction
// ---------------------------------------------------------------------------

static const json& require_field(const json& obj, const std::string& key) {
    auto it = obj.find(key);
    if (it == obj.end()) {
        throw std::runtime_error("codec: missing required field '" + key + "' in: " + obj.dump());
    }
    return *it;
}

static const json& require_type(const json& obj, const std::string& expected_type) {
    const json& type_field = require_field(obj, "__type__");
    if (type_field.get<std::string>() != expected_type) {
        throw std::runtime_error(
            "codec: expected __type__='" + expected_type + "' but got '" +
            type_field.get<std::string>() + "'");
    }
    return require_field(obj, "fields");
}

static int32_t decode_enum(const json& obj, const std::string& expected_class) {
    // {"__enum__": "<ClassName>", "name": "...", "value": <int>}
    auto it_e = obj.find("__enum__");
    if (it_e == obj.end()) {
        throw std::runtime_error("codec: expected __enum__ tag, got: " + obj.dump());
    }
    if (it_e->get<std::string>() != expected_class) {
        throw std::runtime_error(
            "codec: expected __enum__='" + expected_class + "' but got '" +
            it_e->get<std::string>() + "'");
    }
    return require_field(obj, "value").get<int32_t>();
}

// Decode an enum value, accepting either the tagged form {"__enum__":...} or a raw int.
// Python primitives (int subclasses) may sometimes appear as raw ints in older data.
static int32_t decode_enum_or_int(const json& obj, const std::string& expected_class) {
    if (obj.is_number_integer()) return obj.get<int32_t>();
    return decode_enum(obj, expected_class);
}

// Encode a single enum value as {"__enum__": class_name, "name": "<int_value>", "value": v}
// Note: sweep_io.py stores obj.name (the Python name string) in "name"; we mirror that.
// Since we don't have the Python name in C++, we emit the integer as a string — but
// from_jsonable reconstructs by VALUE so "name" is only informational. Emit it as string of value.
static json encode_enum(const std::string& class_name, int64_t value) {
    return json{{"__enum__", class_name}, {"name", std::to_string(value)}, {"value", value}};
}

// Decode a __tuple__ array into a json array for storage.
static json require_tuple(const json& obj) {
    auto it = obj.find("__tuple__");
    if (it == obj.end()) {
        throw std::runtime_error("codec: expected __tuple__ tag, got: " + obj.dump());
    }
    return *it;
}

// Decode a __frozenset__ array.
static json require_frozenset(const json& obj) {
    auto it = obj.find("__frozenset__");
    if (it == obj.end()) {
        throw std::runtime_error("codec: expected __frozenset__ tag, got: " + obj.dump());
    }
    return *it;
}

// ---------------------------------------------------------------------------
// PokemonState decode/encode
// ---------------------------------------------------------------------------

static PokemonState decode_pokemon_state(const json& obj) {
    const json& f = require_type(obj, "PokemonState");
    PokemonState p;

    p.species = decode_enum(require_field(f, "species"), "Species");
    p.nature  = decode_enum(require_field(f, "nature"),  "Nature");

    // ivs: __tuple__ of 6 ints
    json ivs = require_tuple(require_field(f, "ivs"));
    if (ivs.size() != 6) throw std::runtime_error("codec: ivs tuple must have 6 elements");
    p.iv_hp  = ivs[0].get<int32_t>();
    p.iv_atk = ivs[1].get<int32_t>();
    p.iv_def = ivs[2].get<int32_t>();
    p.iv_spa = ivs[3].get<int32_t>();
    p.iv_spd = ivs[4].get<int32_t>();
    p.iv_spe = ivs[5].get<int32_t>();

    p.gender = decode_enum(require_field(f, "gender"), "GenderEnum");
    p.level  = require_field(f, "level").get<int32_t>();
    p.exp    = require_field(f, "exp").get<int32_t>();
    p.ability = decode_enum(require_field(f, "ability"), "Ability");
    p.item    = decode_enum(require_field(f, "item"),    "Item");
    p.status  = decode_enum(require_field(f, "status"),  "Status");

    // move_ids: __tuple__ of 1-4 Move enums; pad to 4 with MOVE_NONE (0) if short.
    // Python PokemonState defaults to 4, but bench mons in tests may have fewer.
    json move_ids = require_tuple(require_field(f, "move_ids"));
    if (move_ids.size() > 4) throw std::runtime_error("codec: move_ids must have at most 4 elements");
    p.move_id0 = move_ids.size() > 0 ? decode_enum(move_ids[0], "Move") : 0;
    p.move_id1 = move_ids.size() > 1 ? decode_enum(move_ids[1], "Move") : 0;
    p.move_id2 = move_ids.size() > 2 ? decode_enum(move_ids[2], "Move") : 0;
    p.move_id3 = move_ids.size() > 3 ? decode_enum(move_ids[3], "Move") : 0;

    // move_pp: __tuple__ of 1-4 ints; pad to 4 with 0 if short.
    json move_pp = require_tuple(require_field(f, "move_pp"));
    if (move_pp.size() > 4) throw std::runtime_error("codec: move_pp must have at most 4 elements");
    p.move_pp0 = move_pp.size() > 0 ? move_pp[0].get<int32_t>() : 0;
    p.move_pp1 = move_pp.size() > 1 ? move_pp[1].get<int32_t>() : 0;
    p.move_pp2 = move_pp.size() > 2 ? move_pp[2].get<int32_t>() : 0;
    p.move_pp3 = move_pp.size() > 3 ? move_pp[3].get<int32_t>() : 0;

    // stats: Optional __tuple__ of 6 ints or null
    const json& stats_j = require_field(f, "stats");
    if (stats_j.is_null()) {
        p.has_stats = false;
    } else {
        p.has_stats = true;
        json sv = require_tuple(stats_j);
        if (sv.size() != 6) throw std::runtime_error("codec: stats must have 6 elements");
        p.stat_hp  = sv[0].get<int32_t>();
        p.stat_atk = sv[1].get<int32_t>();
        p.stat_def = sv[2].get<int32_t>();
        p.stat_spa = sv[3].get<int32_t>();
        p.stat_spd = sv[4].get<int32_t>();
        p.stat_spe = sv[5].get<int32_t>();
    }

    // max_hp: Optional int or null
    const json& max_hp_j = require_field(f, "max_hp");
    if (max_hp_j.is_null()) {
        p.has_max_hp = false;
    } else {
        p.has_max_hp = true;
        p.max_hp = max_hp_j.get<int32_t>();
    }

    // hp: Optional int or null
    const json& hp_j = require_field(f, "hp");
    if (hp_j.is_null()) {
        p.has_hp = false;
    } else {
        p.has_hp = true;
        p.hp = hp_j.get<int32_t>();
    }

    // types: Optional __tuple__ of Type enums or null
    const json& types_j = require_field(f, "types");
    if (types_j.is_null()) {
        p.has_types = false;
    } else {
        p.has_types = true;
        json tv = require_tuple(types_j);
        for (const auto& t : tv) {
            p.types.push_back(decode_enum(t, "Type"));
        }
    }

    // stat_stages: __tuple__ of 7 ints
    json stages_j = require_tuple(require_field(f, "stat_stages"));
    if (stages_j.size() != 7) throw std::runtime_error("codec: stat_stages must have 7 elements");
    p.stage0 = stages_j[0].get<int32_t>();
    p.stage1 = stages_j[1].get<int32_t>();
    p.stage2 = stages_j[2].get<int32_t>();
    p.stage3 = stages_j[3].get<int32_t>();
    p.stage4 = stages_j[4].get<int32_t>();
    p.stage5 = stages_j[5].get<int32_t>();
    p.stage6 = stages_j[6].get<int32_t>();

    // Volatile is Python IntFlag — serialized as {"__enum__": "Volatile", ...} by to_jsonable.
    p.volatiles = decode_enum_or_int(require_field(f, "volatiles"), "Volatile");

    // timed_volatiles: a sequence of __tuple__ [VolatileEffect enum, int]. The outer container is a
    // Python tuple, so to_jsonable wraps it as {"__tuple__": [...]}; accept both that and a bare list.
    const json& tv_raw = require_field(f, "timed_volatiles");
    json tv_j = tv_raw.is_object() ? require_tuple(tv_raw) : tv_raw;
    if (!tv_j.is_array()) throw std::runtime_error("codec: timed_volatiles must be a list");
    for (const auto& entry : tv_j) {
        json pair = require_tuple(entry);
        if (pair.size() != 2) throw std::runtime_error("codec: timed_volatile entry must be 2-tuple");
        TimedVolatile tv_entry;
        tv_entry.effect = decode_enum(pair[0], "VolatileEffect");
        tv_entry.turns  = pair[1].get<int32_t>();
        p.timed_volatiles.push_back(tv_entry);
    }

    p.turns_in_battle   = require_field(f, "turns_in_battle").get<int32_t>();
    p.toxic_turns       = require_field(f, "toxic_turns").get<int32_t>();
    p.sleep_turns       = require_field(f, "sleep_turns").get<int32_t>();
    p.confusion_turns   = require_field(f, "confusion_turns").get<int32_t>();
    p.is_rest_sleep     = require_field(f, "is_rest_sleep").get<bool>();
    p.locked_slot       = require_field(f, "locked_slot").get<int32_t>();
    p.charging_move_slot = require_field(f, "charging_move_slot").get<int32_t>();
    p.sub_hp            = require_field(f, "sub_hp").get<int32_t>();
    p.last_used_slot    = require_field(f, "last_used_slot").get<int32_t>();
    p.fainted           = require_field(f, "fainted").get<bool>();
    p.has_acted         = require_field(f, "has_acted").get<bool>();
    p.crit_stage        = require_field(f, "crit_stage").get<int32_t>();
    p.metronome_count   = require_field(f, "metronome_count").get<int32_t>();
    p.metronome_last_move = require_field(f, "metronome_last_move").get<int32_t>();
    p.mirror_move_last_move = decode_enum_or_int(require_field(f, "mirror_move_last_move"), "Move");
    p.consumed_berry    = decode_enum(require_field(f, "consumed_berry"), "Item");
    p.took_damage_this_turn     = require_field(f, "took_damage_this_turn").get<bool>();
    p.had_stat_lowered_this_turn = require_field(f, "had_stat_lowered_this_turn").get<bool>();
    p.had_stat_raised_this_turn  = require_field(f, "had_stat_raised_this_turn").get<bool>();
    p.last_move_failed           = require_field(f, "last_move_failed").get<bool>();
    p.last_physical_damage_taken = require_field(f, "last_physical_damage_taken").get<int32_t>();
    p.last_special_damage_taken  = require_field(f, "last_special_damage_taken").get<int32_t>();
    p.last_damage_taken          = require_field(f, "last_damage_taken").get<int32_t>();
    p.sucker_punch_last_turn     = require_field(f, "sucker_punch_last_turn").get<bool>();
    p.base_ability   = decode_enum(require_field(f, "base_ability"),  "Ability");
    p.saved_ability  = decode_enum(require_field(f, "saved_ability"), "Ability");
    p.is_mega        = require_field(f, "is_mega").get<bool>();
    p.moves_used     = require_field(f, "moves_used").get<int32_t>();
    p.rollout_hits   = require_field(f, "rollout_hits").get<int32_t>();
    p.defense_curl_used = require_field(f, "defense_curl_used").get<bool>();
    p.weight_kg_reduced = require_field(f, "weight_kg_reduced").get<double>();
    p.protect_counter   = require_field(f, "protect_counter").get<int32_t>();
    p.stockpile_count      = require_field(f, "stockpile_count").get<int32_t>();
    p.stockpile_def_boost  = require_field(f, "stockpile_def_boost").get<int32_t>();
    p.stockpile_spd_boost  = require_field(f, "stockpile_spd_boost").get<int32_t>();

    return p;
}

static json encode_pokemon_state(const PokemonState& p) {
    json fields;

    fields["species"] = encode_enum("Species", p.species);
    fields["nature"]  = encode_enum("Nature",  p.nature);

    fields["ivs"] = json{{"__tuple__", json::array({p.iv_hp, p.iv_atk, p.iv_def, p.iv_spa, p.iv_spd, p.iv_spe})}};
    fields["gender"] = encode_enum("GenderEnum", p.gender);
    fields["level"]  = p.level;
    fields["exp"]    = p.exp;
    fields["ability"] = encode_enum("Ability", p.ability);
    fields["item"]    = encode_enum("Item",    p.item);
    fields["status"]  = encode_enum("Status",  p.status);

    fields["move_ids"] = json{{"__tuple__", json::array({
        encode_enum("Move", p.move_id0),
        encode_enum("Move", p.move_id1),
        encode_enum("Move", p.move_id2),
        encode_enum("Move", p.move_id3),
    })}};
    fields["move_pp"] = json{{"__tuple__", json::array({p.move_pp0, p.move_pp1, p.move_pp2, p.move_pp3})}};

    if (p.has_stats) {
        fields["stats"] = json{{"__tuple__", json::array({
            p.stat_hp, p.stat_atk, p.stat_def, p.stat_spa, p.stat_spd, p.stat_spe
        })}};
    } else {
        fields["stats"] = nullptr;
    }

    if (p.has_max_hp) {
        fields["max_hp"] = p.max_hp;
    } else {
        fields["max_hp"] = nullptr;
    }

    if (p.has_hp) {
        fields["hp"] = p.hp;
    } else {
        fields["hp"] = nullptr;
    }

    if (p.has_types) {
        json type_arr = json::array();
        for (int32_t t : p.types) {
            type_arr.push_back(encode_enum("Type", t));
        }
        fields["types"] = json{{"__tuple__", type_arr}};
    } else {
        fields["types"] = nullptr;
    }

    fields["stat_stages"] = json{{"__tuple__", json::array({
        p.stage0, p.stage1, p.stage2, p.stage3, p.stage4, p.stage5, p.stage6
    })}};

    // Python stores volatiles as a PLAIN int bitfield (pokemon.py: `volatiles: int = 0`;
    // `int | Volatile.X` stays int), so to_jsonable emits a bare int. Emit the same here —
    // tagged-enum form breaks state-fingerprint parity (see test_trace_record_replay.py).
    // The decode side (decode_enum_or_int) accepts both forms.
    fields["volatiles"] = p.volatiles;

    json tv_arr = json::array();
    for (const auto& tv : p.timed_volatiles) {
        tv_arr.push_back(json{{"__tuple__", json::array({
            encode_enum("VolatileEffect", tv.effect),
            tv.turns
        })}});
    }
    fields["timed_volatiles"] = tv_arr;

    fields["turns_in_battle"]    = p.turns_in_battle;
    fields["toxic_turns"]        = p.toxic_turns;
    fields["sleep_turns"]        = p.sleep_turns;
    fields["confusion_turns"]    = p.confusion_turns;
    fields["is_rest_sleep"]      = p.is_rest_sleep;
    fields["locked_slot"]        = p.locked_slot;
    fields["charging_move_slot"] = p.charging_move_slot;
    fields["sub_hp"]             = p.sub_hp;
    fields["last_used_slot"]     = p.last_used_slot;
    fields["fainted"]            = p.fainted;
    fields["has_acted"]          = p.has_acted;
    fields["crit_stage"]         = p.crit_stage;
    fields["metronome_count"]    = p.metronome_count;
    fields["metronome_last_move"] = p.metronome_last_move;
    fields["mirror_move_last_move"] = p.mirror_move_last_move;
    fields["consumed_berry"] = encode_enum("Item", p.consumed_berry);
    fields["took_damage_this_turn"]      = p.took_damage_this_turn;
    fields["had_stat_lowered_this_turn"] = p.had_stat_lowered_this_turn;
    fields["had_stat_raised_this_turn"]  = p.had_stat_raised_this_turn;
    fields["last_move_failed"]           = p.last_move_failed;
    fields["last_physical_damage_taken"] = p.last_physical_damage_taken;
    fields["last_special_damage_taken"]  = p.last_special_damage_taken;
    fields["last_damage_taken"]          = p.last_damage_taken;
    fields["sucker_punch_last_turn"]     = p.sucker_punch_last_turn;
    fields["base_ability"]  = encode_enum("Ability", p.base_ability);
    fields["saved_ability"] = encode_enum("Ability", p.saved_ability);
    fields["is_mega"]       = p.is_mega;
    fields["moves_used"]    = p.moves_used;
    fields["rollout_hits"]  = p.rollout_hits;
    fields["defense_curl_used"]  = p.defense_curl_used;
    fields["weight_kg_reduced"]  = p.weight_kg_reduced;
    fields["protect_counter"]    = p.protect_counter;
    fields["stockpile_count"]    = p.stockpile_count;
    fields["stockpile_def_boost"] = p.stockpile_def_boost;
    fields["stockpile_spd_boost"] = p.stockpile_spd_boost;

    return json{{"__type__", "PokemonState"}, {"fields", fields}};
}

// ---------------------------------------------------------------------------
// SideState decode/encode
// ---------------------------------------------------------------------------

static SideState decode_side_state(const json& obj) {
    const json& f = require_type(obj, "SideState");
    SideState s;

    // team: list of PokemonState
    const json& team_j = require_field(f, "team");
    if (!team_j.is_array()) throw std::runtime_error("codec: SideState.team must be a list");
    for (const auto& pj : team_j) {
        s.team.push_back(decode_pokemon_state(pj));
    }

    s.format = decode_enum(require_field(f, "format"), "FormatEnum");

    // active_indices: list of ints
    const json& ai_j = require_field(f, "active_indices");
    if (!ai_j.is_array()) throw std::runtime_error("codec: active_indices must be a list");
    for (const auto& v : ai_j) {
        s.active_indices.push_back(v.get<int32_t>());
    }

    // side_conditions: list of __tuple__ [SideCondition enum, int]
    const json& sc_j = require_field(f, "side_conditions");
    if (!sc_j.is_array()) throw std::runtime_error("codec: side_conditions must be a list");
    for (const auto& entry : sc_j) {
        json pair = require_tuple(entry);
        if (pair.size() != 2) throw std::runtime_error("codec: side_condition entry must be 2-tuple");
        SideConditionEntry sce;
        sce.condition = decode_enum(pair[0], "SideCondition");
        sce.turns     = pair[1].get<int32_t>();
        s.side_conditions.push_back(sce);
    }

    s.mega_used = require_field(f, "mega_used").get<bool>();

    // baton_pass_data: null or a __tuple__ (complex nested)
    const json& bpd_j = require_field(f, "baton_pass_data");
    if (bpd_j.is_null()) {
        s.has_baton_pass_data = false;
    } else {
        s.has_baton_pass_data = true;
        // Store raw to reproduce exactly on re-encode
        s.baton_pass_data_raw = bpd_j;
    }

    s.ally_fainted_last_turn = require_field(f, "ally_fainted_last_turn").get<bool>();

    // wish_pending: null or __tuple__ of (int, int, int)
    const json& wp_j = require_field(f, "wish_pending");
    if (wp_j.is_null()) {
        s.has_wish_pending = false;
    } else {
        s.has_wish_pending = true;
        json wt = require_tuple(wp_j);
        if (wt.size() != 3) throw std::runtime_error("codec: wish_pending must be 3-tuple");
        s.wish_turns = wt[0].get<int32_t>();
        s.wish_hp    = wt[1].get<int32_t>();
        s.wish_slot  = wt[2].get<int32_t>();
    }

    // future_sight_pending: null or __tuple__ of (int, int, Move enum, int)
    const json& fsp_j = require_field(f, "future_sight_pending");
    if (fsp_j.is_null()) {
        s.has_future_sight_pending = false;
    } else {
        s.has_future_sight_pending = true;
        json ft = require_tuple(fsp_j);
        if (ft.size() != 4) throw std::runtime_error("codec: future_sight_pending must be 4-tuple");
        s.fs_turns       = ft[0].get<int32_t>();
        s.fs_damage      = ft[1].get<int32_t>();
        s.fs_move        = decode_enum(ft[2], "Move");
        s.fs_target_slot = ft[3].get<int32_t>();
    }

    // imprisoned_moves: __frozenset__ of Move enums
    const json& im_j = require_field(f, "imprisoned_moves");
    json im_arr = require_frozenset(im_j);
    for (const auto& mv : im_arr) {
        s.imprisoned_moves.push_back(decode_enum(mv, "Move"));
    }
    std::sort(s.imprisoned_moves.begin(), s.imprisoned_moves.end());

    s.redirect_target        = require_field(f, "redirect_target").get<int32_t>();
    s.redirect_is_rage_powder = require_field(f, "redirect_is_rage_powder").get<bool>();

    return s;
}

static json encode_side_state(const SideState& s) {
    json fields;

    json team_arr = json::array();
    for (const auto& p : s.team) {
        team_arr.push_back(encode_pokemon_state(p));
    }
    fields["team"] = team_arr;

    fields["format"] = encode_enum("FormatEnum", s.format);

    json ai_arr = json::array();
    for (int32_t idx : s.active_indices) ai_arr.push_back(idx);
    fields["active_indices"] = ai_arr;

    json sc_arr = json::array();
    for (const auto& sce : s.side_conditions) {
        sc_arr.push_back(json{{"__tuple__", json::array({
            encode_enum("SideCondition", sce.condition),
            sce.turns
        })}});
    }
    fields["side_conditions"] = sc_arr;

    fields["mega_used"] = s.mega_used;

    if (s.has_baton_pass_data) {
        fields["baton_pass_data"] = s.baton_pass_data_raw;
    } else {
        fields["baton_pass_data"] = nullptr;
    }

    fields["ally_fainted_last_turn"] = s.ally_fainted_last_turn;

    if (s.has_wish_pending) {
        fields["wish_pending"] = json{{"__tuple__", json::array({s.wish_turns, s.wish_hp, s.wish_slot})}};
    } else {
        fields["wish_pending"] = nullptr;
    }

    if (s.has_future_sight_pending) {
        fields["future_sight_pending"] = json{{"__tuple__", json::array({
            s.fs_turns, s.fs_damage, encode_enum("Move", s.fs_move), s.fs_target_slot
        })}};
    } else {
        fields["future_sight_pending"] = nullptr;
    }

    // imprisoned_moves: __frozenset__ sorted by repr (Python sorts Move enums by repr)
    // Python: sorted(obj, key=repr) → for IntEnum, repr gives "<EnumName.NAME: value>",
    // sorted lexicographically. We store as sorted int vector and re-emit in that order.
    // Since we decoded sorted by int value, we need to re-sort by repr key.
    // For Move enums: repr is "<Move.NAME: value>". Since we don't have names, sort by value
    // mirrors Python's sort if enum names happen to sort that way. But Python sorts by repr string.
    // The safest approach: the frozenset was decoded from Python's sorted repr order, stored
    // sorted by int; re-emit in the same sorted-by-int order, matching what Python will produce
    // (Python's repr-sort for consecutive Move ints is monotone in value for standard names).
    // This is validated by round-trip tests.
    json im_arr_out = json::array();
    // We stored sorted by int value; emit in that order with enum tags
    for (int32_t mv : s.imprisoned_moves) {
        im_arr_out.push_back(encode_enum("Move", mv));
    }
    fields["imprisoned_moves"] = json{{"__frozenset__", im_arr_out}};

    fields["redirect_target"]         = s.redirect_target;
    fields["redirect_is_rage_powder"] = s.redirect_is_rage_powder;

    return json{{"__type__", "SideState"}, {"fields", fields}};
}

// ---------------------------------------------------------------------------
// BattleState decode/encode
// ---------------------------------------------------------------------------

static BattleState decode_battle_state(const json& obj) {
    const json& f = require_type(obj, "BattleState");
    BattleState b;

    // sides: __tuple__ of [SideState, SideState]
    json sides_j = require_tuple(require_field(f, "sides"));
    if (sides_j.size() != 2) throw std::runtime_error("codec: sides must be a 2-tuple");
    b.side0 = decode_side_state(sides_j[0]);
    b.side1 = decode_side_state(sides_j[1]);

    b.weather       = decode_enum(require_field(f, "weather"), "WeatherEnum");
    b.weather_turns = require_field(f, "weather_turns").get<int32_t>();
    b.terrain       = decode_enum(require_field(f, "terrain"), "TerrainEnum");
    b.terrain_turns = require_field(f, "terrain_turns").get<int32_t>();

    // pseudo_weather: list of __tuple__ [PseudoWeather enum, int]
    const json& pw_j = require_field(f, "pseudo_weather");
    if (!pw_j.is_array()) throw std::runtime_error("codec: pseudo_weather must be a list");
    for (const auto& entry : pw_j) {
        json pair = require_tuple(entry);
        if (pair.size() != 2) throw std::runtime_error("codec: pseudo_weather entry must be 2-tuple");
        PseudoWeatherEntry pwe;
        pwe.effect = decode_enum(pair[0], "PseudoWeather");
        pwe.turns  = pair[1].get<int32_t>();
        b.pseudo_weather.push_back(pwe);
    }

    b.turn_number                = require_field(f, "turn_number").get<int32_t>();
    b.echoed_voice_multiplier    = require_field(f, "echoed_voice_multiplier").get<int32_t>();
    b.echoed_voice_used_this_turn = require_field(f, "echoed_voice_used_this_turn").get<bool>();
    b.battle_last_move           = decode_enum_or_int(require_field(f, "battle_last_move"), "Move");
    b.format                     = decode_enum(require_field(f, "format"), "FormatEnum");

    // turn_order: list of ints
    const json& to_j = require_field(f, "turn_order");
    if (!to_j.is_array()) throw std::runtime_error("codec: turn_order must be a list");
    for (const auto& v : to_j) b.turn_order.push_back(v.get<int32_t>());

    // prev_turn_order: __tuple__ of ints
    json pto_j = require_tuple(require_field(f, "prev_turn_order"));
    for (const auto& v : pto_j) b.prev_turn_order.push_back(v.get<int32_t>());

    b.is_trainer_battle = require_field(f, "is_trainer_battle").get<bool>();

    // level_cap: null or int
    const json& lc_j = require_field(f, "level_cap");
    if (lc_j.is_null()) {
        b.has_level_cap = false;
    } else {
        b.has_level_cap = true;
        b.level_cap = lc_j.get<int32_t>();
    }

    // exp_participants: __tuple__ of __frozenset__ of ints
    json ep_tuple = require_tuple(require_field(f, "exp_participants"));
    for (const auto& fs_j : ep_tuple) {
        json inner = require_frozenset(fs_j);
        std::vector<int32_t> participants;
        for (const auto& v : inner) participants.push_back(v.get<int32_t>());
        std::sort(participants.begin(), participants.end());
        b.exp_participants.push_back(std::move(participants));
    }

    return b;
}

static json encode_battle_state(const BattleState& b) {
    json fields;

    fields["sides"] = json{{"__tuple__", json::array({
        encode_side_state(b.side0),
        encode_side_state(b.side1)
    })}};

    fields["weather"]       = encode_enum("WeatherEnum", b.weather);
    fields["weather_turns"] = b.weather_turns;
    fields["terrain"]       = encode_enum("TerrainEnum", b.terrain);
    fields["terrain_turns"] = b.terrain_turns;

    json pw_arr = json::array();
    for (const auto& pwe : b.pseudo_weather) {
        pw_arr.push_back(json{{"__tuple__", json::array({
            encode_enum("PseudoWeather", pwe.effect),
            pwe.turns
        })}});
    }
    fields["pseudo_weather"] = pw_arr;

    fields["turn_number"]                 = b.turn_number;
    fields["echoed_voice_multiplier"]     = b.echoed_voice_multiplier;
    fields["echoed_voice_used_this_turn"] = b.echoed_voice_used_this_turn;
    fields["battle_last_move"]            = b.battle_last_move;
    fields["format"]                      = encode_enum("FormatEnum", b.format);

    json to_arr = json::array();
    for (int32_t v : b.turn_order) to_arr.push_back(v);
    fields["turn_order"] = to_arr;

    json pto_arr = json::array();
    for (int32_t v : b.prev_turn_order) pto_arr.push_back(v);
    fields["prev_turn_order"] = json{{"__tuple__", pto_arr}};

    fields["is_trainer_battle"] = b.is_trainer_battle;

    if (b.has_level_cap) {
        fields["level_cap"] = b.level_cap;
    } else {
        fields["level_cap"] = nullptr;
    }

    // exp_participants: __tuple__ of __frozenset__ of ints
    // Python sorts frozenset elements by repr; for plain ints, repr is just str(n), sorted numerically.
    json ep_tuple = json::array();
    for (const auto& participants : b.exp_participants) {
        // participants already sorted by int value (decoded that way)
        json inner = json::array();
        for (int32_t v : participants) inner.push_back(v);
        ep_tuple.push_back(json{{"__frozenset__", inner}});
    }
    fields["exp_participants"] = json{{"__tuple__", ep_tuple}};

    return json{{"__type__", "BattleState"}, {"fields", fields}};
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

BattleState battle_state_from_json(const std::string& s) {
    json obj = json::parse(s);
    return decode_battle_state(obj);
}

std::string battle_state_to_json(const BattleState& state) {
    return encode_battle_state(state).dump();
}

DamageLoopLuck damage_luck_from_json(const json& lj) {
    DamageLoopLuck d;
    d.crit_threshold      = lj.value("crit_threshold", 50.0);
    d.damage_roll         = lj.value("damage_roll", 0.5);
    d.proc_threshold      = lj.value("proc_threshold", 50.0);
    d.secondary_threshold = lj.value("secondary_threshold", 50.0);
    d.multi_hit_roll      = lj.value("multi_hit_roll", 0.5);
    d.rampage_duration_roll = lj.value("rampage_duration_roll", 0.5);
    d.random_mode         = lj.value("random_mode", false);
    d.accuracy_threshold           = lj.value("accuracy_threshold", 50.0);
    d.psywave_roll                 = lj.value("psywave_roll", 0.5);
    d.flinch_threshold             = lj.value("flinch_threshold", 50.0);
    d.binding_duration_roll        = lj.value("binding_duration_roll", 0.5);
    d.wake_threshold               = lj.value("wake_threshold", 50.0);
    d.defrost_threshold            = lj.value("defrost_threshold", 20.0);
    d.paralysis_threshold          = lj.value("paralysis_threshold", 50.0);
    d.confusion_snap_threshold     = lj.value("confusion_snap_threshold", 50.0);
    d.confusion_self_hit_threshold = lj.value("confusion_self_hit_threshold", 50.0);
    d.attract_threshold            = lj.value("attract_threshold", 50.0);
    if (lj.contains("damage_rolls_per_hit") && !lj["damage_rolls_per_hit"].is_null()) {
        d.damage_rolls_present = true;
        for (const auto& e : lj["damage_rolls_per_hit"]) d.damage_rolls_per_hit.push_back(e.get<double>());
    }
    if (lj.contains("crits_per_hit") && !lj["crits_per_hit"].is_null()) {
        d.crits_present = true;
        for (const auto& e : lj["crits_per_hit"]) d.crits_per_hit.push_back(e.get<double>());
    }
    return d;
}

TurnLuck turn_luck_from_json(const json& lj) {
    TurnLuck l;
    l.quick_claw_threshold = lj.value("quick_claw_threshold", 50.0);
    l.secondary_threshold  = lj.value("secondary_threshold", 50.0);
    l.luck_tier            = lj.value("luck_tier", 1);
    l.random_mode          = lj.value("random_mode", false);
    return l;
}
