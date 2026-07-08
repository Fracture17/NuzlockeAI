// Implementation of full-field state equality + a consistent hash for the BattleState graph.
// Equality compares the SAME fields Python's dataclass __eq__ does. Set fields
// (imprisoned_moves, exp_participants inner sets) are decoded pre-sorted by the codec, so
// order-sensitive vector compare is correct; the hash still mixes them order-independently.
#include "state_eq.h"

#include <cstdint>
#include <functional>
#include <vector>

namespace {

// boost-style hash combine.
inline void hash_combine(std::size_t& seed, std::size_t h) {
    seed ^= h + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

template <typename T>
inline void mix(std::size_t& seed, const T& v) {
    hash_combine(seed, std::hash<T>{}(v));
}

// Order-independent mix of an int vector (set field): XOR of per-element hashes,
// so insertion order does not affect the result.
inline std::size_t hash_int_set(const std::vector<int32_t>& v) {
    std::size_t acc = 0;
    for (int32_t x : v) acc ^= std::hash<int32_t>{}(static_cast<int>(x));
    return acc;
}

bool equal_timed(const std::vector<TimedVolatile>& a, const std::vector<TimedVolatile>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i)
        if (a[i].effect != b[i].effect || a[i].turns != b[i].turns) return false;
    return true;
}

bool equal_side_conditions(const std::vector<SideConditionEntry>& a,
                           const std::vector<SideConditionEntry>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i)
        if (a[i].condition != b[i].condition || a[i].turns != b[i].turns) return false;
    return true;
}

bool equal_pseudo(const std::vector<PseudoWeatherEntry>& a,
                  const std::vector<PseudoWeatherEntry>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i)
        if (a[i].effect != b[i].effect || a[i].turns != b[i].turns) return false;
    return true;
}

}  // namespace

// ---------------------------------------------------------------------------
// PokemonState
// ---------------------------------------------------------------------------

bool state_equal(const PokemonState& a, const PokemonState& b) {
    return a.species == b.species && a.nature == b.nature &&
           a.iv_hp == b.iv_hp && a.iv_atk == b.iv_atk && a.iv_def == b.iv_def &&
           a.iv_spa == b.iv_spa && a.iv_spd == b.iv_spd && a.iv_spe == b.iv_spe &&
           a.gender == b.gender && a.level == b.level && a.exp == b.exp &&
           a.ability == b.ability && a.item == b.item && a.status == b.status &&
           a.move_id0 == b.move_id0 && a.move_id1 == b.move_id1 &&
           a.move_id2 == b.move_id2 && a.move_id3 == b.move_id3 &&
           a.move_pp0 == b.move_pp0 && a.move_pp1 == b.move_pp1 &&
           a.move_pp2 == b.move_pp2 && a.move_pp3 == b.move_pp3 &&
           // Optional stats: presence flag paired with values (None-vs-value distinction).
           a.has_stats == b.has_stats &&
           (!a.has_stats ||
            (a.stat_hp == b.stat_hp && a.stat_atk == b.stat_atk && a.stat_def == b.stat_def &&
             a.stat_spa == b.stat_spa && a.stat_spd == b.stat_spd && a.stat_spe == b.stat_spe)) &&
           a.has_max_hp == b.has_max_hp && (!a.has_max_hp || a.max_hp == b.max_hp) &&
           a.has_hp == b.has_hp && (!a.has_hp || a.hp == b.hp) &&
           a.has_types == b.has_types && (!a.has_types || a.types == b.types) &&
           a.stage0 == b.stage0 && a.stage1 == b.stage1 && a.stage2 == b.stage2 &&
           a.stage3 == b.stage3 && a.stage4 == b.stage4 && a.stage5 == b.stage5 &&
           a.stage6 == b.stage6 &&
           a.volatiles == b.volatiles && equal_timed(a.timed_volatiles, b.timed_volatiles) &&
           a.turns_in_battle == b.turns_in_battle && a.toxic_turns == b.toxic_turns &&
           a.sleep_turns == b.sleep_turns && a.confusion_turns == b.confusion_turns &&
           a.is_rest_sleep == b.is_rest_sleep && a.locked_slot == b.locked_slot &&
           a.charging_move_slot == b.charging_move_slot && a.sub_hp == b.sub_hp &&
           a.last_used_slot == b.last_used_slot && a.fainted == b.fainted &&
           a.has_acted == b.has_acted && a.crit_stage == b.crit_stage &&
           a.metronome_count == b.metronome_count &&
           a.metronome_last_move == b.metronome_last_move &&
           a.mirror_move_last_move == b.mirror_move_last_move &&
           a.consumed_berry == b.consumed_berry &&
           a.took_damage_this_turn == b.took_damage_this_turn &&
           a.had_stat_lowered_this_turn == b.had_stat_lowered_this_turn &&
           a.had_stat_raised_this_turn == b.had_stat_raised_this_turn &&
           a.last_move_failed == b.last_move_failed &&
           a.last_physical_damage_taken == b.last_physical_damage_taken &&
           a.last_special_damage_taken == b.last_special_damage_taken &&
           a.last_damage_taken == b.last_damage_taken &&
           a.sucker_punch_last_turn == b.sucker_punch_last_turn &&
           a.base_ability == b.base_ability && a.saved_ability == b.saved_ability &&
           a.is_mega == b.is_mega && a.moves_used == b.moves_used &&
           a.rollout_hits == b.rollout_hits && a.defense_curl_used == b.defense_curl_used &&
           // exact float equality (Python uses ==, no epsilon)
           a.weight_kg_reduced == b.weight_kg_reduced &&
           a.protect_counter == b.protect_counter &&
           a.stockpile_count == b.stockpile_count &&
           a.stockpile_def_boost == b.stockpile_def_boost &&
           a.stockpile_spd_boost == b.stockpile_spd_boost;
}

// ---------------------------------------------------------------------------
// SideState
// ---------------------------------------------------------------------------

bool state_equal(const SideState& a, const SideState& b) {
    if (a.team.size() != b.team.size()) return false;
    for (std::size_t i = 0; i < a.team.size(); ++i)
        if (!state_equal(a.team[i], b.team[i])) return false;

    return a.format == b.format && a.active_indices == b.active_indices &&
           equal_side_conditions(a.side_conditions, b.side_conditions) &&
           a.mega_used == b.mega_used &&
           // baton_pass_data: presence flag + raw JSON value.
           a.has_baton_pass_data == b.has_baton_pass_data &&
           (!a.has_baton_pass_data || a.baton_pass_data_raw == b.baton_pass_data_raw) &&
           a.ally_fainted_last_turn == b.ally_fainted_last_turn &&
           a.has_wish_pending == b.has_wish_pending &&
           (!a.has_wish_pending ||
            (a.wish_turns == b.wish_turns && a.wish_hp == b.wish_hp && a.wish_slot == b.wish_slot)) &&
           a.has_future_sight_pending == b.has_future_sight_pending &&
           (!a.has_future_sight_pending ||
            (a.fs_turns == b.fs_turns && a.fs_damage == b.fs_damage &&
             a.fs_move == b.fs_move && a.fs_target_slot == b.fs_target_slot)) &&
           // imprisoned_moves: set field, decoded pre-sorted -> vector compare is correct.
           a.imprisoned_moves == b.imprisoned_moves &&
           a.redirect_target == b.redirect_target &&
           a.redirect_is_rage_powder == b.redirect_is_rage_powder;
}

// ---------------------------------------------------------------------------
// BattleState
// ---------------------------------------------------------------------------

bool state_equal(const BattleState& a, const BattleState& b) {
    return state_equal(a.side0, b.side0) && state_equal(a.side1, b.side1) &&
           a.weather == b.weather && a.weather_turns == b.weather_turns &&
           a.terrain == b.terrain && a.terrain_turns == b.terrain_turns &&
           equal_pseudo(a.pseudo_weather, b.pseudo_weather) &&
           a.turn_number == b.turn_number &&
           a.echoed_voice_multiplier == b.echoed_voice_multiplier &&
           a.echoed_voice_used_this_turn == b.echoed_voice_used_this_turn &&
           a.battle_last_move == b.battle_last_move && a.format == b.format &&
           a.turn_order == b.turn_order && a.prev_turn_order == b.prev_turn_order &&
           a.is_trainer_battle == b.is_trainer_battle &&
           a.has_level_cap == b.has_level_cap &&
           (!a.has_level_cap || a.level_cap == b.level_cap) &&
           a.exp_participants == b.exp_participants;  // outer ordered, inner pre-sorted
}

// ---------------------------------------------------------------------------
// Hash (consistent with state_equal; sets mixed order-independently)
// ---------------------------------------------------------------------------

namespace {

std::size_t hash_pokemon(const PokemonState& p) {
    std::size_t seed = 0;
    mix(seed, p.species); mix(seed, p.nature);
    mix(seed, p.iv_hp); mix(seed, p.iv_atk); mix(seed, p.iv_def);
    mix(seed, p.iv_spa); mix(seed, p.iv_spd); mix(seed, p.iv_spe);
    mix(seed, p.gender); mix(seed, p.level); mix(seed, p.exp);
    mix(seed, p.ability); mix(seed, p.item); mix(seed, p.status);
    mix(seed, p.move_id0); mix(seed, p.move_id1); mix(seed, p.move_id2); mix(seed, p.move_id3);
    mix(seed, p.move_pp0); mix(seed, p.move_pp1); mix(seed, p.move_pp2); mix(seed, p.move_pp3);
    mix(seed, p.has_stats);
    if (p.has_stats) {
        mix(seed, p.stat_hp); mix(seed, p.stat_atk); mix(seed, p.stat_def);
        mix(seed, p.stat_spa); mix(seed, p.stat_spd); mix(seed, p.stat_spe);
    }
    mix(seed, p.has_max_hp); if (p.has_max_hp) mix(seed, p.max_hp);
    mix(seed, p.has_hp);     if (p.has_hp)     mix(seed, p.hp);
    mix(seed, p.has_types);
    if (p.has_types) for (int32_t t : p.types) mix(seed, t);
    mix(seed, p.stage0); mix(seed, p.stage1); mix(seed, p.stage2); mix(seed, p.stage3);
    mix(seed, p.stage4); mix(seed, p.stage5); mix(seed, p.stage6);
    mix(seed, p.volatiles);
    for (const auto& tv : p.timed_volatiles) { mix(seed, tv.effect); mix(seed, tv.turns); }
    mix(seed, p.turns_in_battle); mix(seed, p.toxic_turns);
    mix(seed, p.sleep_turns); mix(seed, p.confusion_turns); mix(seed, p.is_rest_sleep);
    mix(seed, p.locked_slot); mix(seed, p.charging_move_slot); mix(seed, p.sub_hp);
    mix(seed, p.last_used_slot); mix(seed, p.fainted); mix(seed, p.has_acted);
    mix(seed, p.crit_stage); mix(seed, p.metronome_count); mix(seed, p.metronome_last_move);
    mix(seed, p.mirror_move_last_move); mix(seed, p.consumed_berry);
    mix(seed, p.took_damage_this_turn); mix(seed, p.had_stat_lowered_this_turn);
    mix(seed, p.had_stat_raised_this_turn); mix(seed, p.last_move_failed);
    mix(seed, p.last_physical_damage_taken); mix(seed, p.last_special_damage_taken);
    mix(seed, p.last_damage_taken); mix(seed, p.sucker_punch_last_turn);
    mix(seed, p.base_ability); mix(seed, p.saved_ability); mix(seed, p.is_mega);
    mix(seed, p.moves_used); mix(seed, p.rollout_hits); mix(seed, p.defense_curl_used);
    mix(seed, p.weight_kg_reduced); mix(seed, p.protect_counter);
    mix(seed, p.stockpile_count); mix(seed, p.stockpile_def_boost); mix(seed, p.stockpile_spd_boost);
    return seed;
}

std::size_t hash_side(const SideState& s) {
    std::size_t seed = 0;
    for (const auto& mon : s.team) hash_combine(seed, hash_pokemon(mon));
    mix(seed, s.format);
    for (int32_t ai : s.active_indices) mix(seed, ai);
    for (const auto& sc : s.side_conditions) { mix(seed, sc.condition); mix(seed, sc.turns); }
    mix(seed, s.mega_used);
    mix(seed, s.has_baton_pass_data);
    if (s.has_baton_pass_data)
        hash_combine(seed, std::hash<std::string>{}(s.baton_pass_data_raw.dump()));
    mix(seed, s.ally_fainted_last_turn);
    mix(seed, s.has_wish_pending);
    if (s.has_wish_pending) { mix(seed, s.wish_turns); mix(seed, s.wish_hp); mix(seed, s.wish_slot); }
    mix(seed, s.has_future_sight_pending);
    if (s.has_future_sight_pending) {
        mix(seed, s.fs_turns); mix(seed, s.fs_damage); mix(seed, s.fs_move); mix(seed, s.fs_target_slot);
    }
    // imprisoned_moves is a set: mix order-independently.
    hash_combine(seed, hash_int_set(s.imprisoned_moves));
    mix(seed, s.redirect_target); mix(seed, s.redirect_is_rage_powder);
    return seed;
}

}  // namespace

std::size_t state_hash(const BattleState& s) {
    std::size_t seed = 0;
    hash_combine(seed, hash_side(s.side0));
    hash_combine(seed, hash_side(s.side1));
    mix(seed, s.weather); mix(seed, s.weather_turns);
    mix(seed, s.terrain); mix(seed, s.terrain_turns);
    for (const auto& pw : s.pseudo_weather) { mix(seed, pw.effect); mix(seed, pw.turns); }
    mix(seed, s.turn_number); mix(seed, s.echoed_voice_multiplier);
    mix(seed, s.echoed_voice_used_this_turn); mix(seed, s.battle_last_move); mix(seed, s.format);
    for (int32_t t : s.turn_order) mix(seed, t);
    for (int32_t t : s.prev_turn_order) mix(seed, t);
    mix(seed, s.is_trainer_battle);
    mix(seed, s.has_level_cap); if (s.has_level_cap) mix(seed, s.level_cap);
    // exp_participants: outer ordered, each inner set order-independent.
    for (const auto& inner : s.exp_participants) hash_combine(seed, hash_int_set(inner));
    return seed;
}
