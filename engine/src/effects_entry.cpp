// Entry-hazard and entry-ability/item triggers split from effects.cpp.
// Hosts cpp_apply_entry_hazards, cpp_apply_entry_effects, and the file-local
// helpers (Intimidate, Trace, Imposter, Download, seeds, Forecast, RKS, Screen
// Cleaner, Pastel Veil, Truant, Neutralizing Gas). The four helpers reused by
// turn-start / EOT paths in effects.cpp are exposed via effects_internal.h.
#include "effects.h"
#include "effects_internal.h"
#include "effects_consts.h"
#include "move_exec_guards.h"      // ExecCtx (Eject Pack signaling from change_stat_stage)
#include "type_chart_lookup.h"
#include "damage.h"                // cpp_effective_stat (Download)

#include <algorithm>
#include <cstdint>
#include <vector>

using namespace eff;
using namespace eff_internal;

// ===========================================================================
// _apply_entry_hazards
// ===========================================================================
void cpp_apply_entry_hazards(BattleState& s, int entering_side_idx) {
    SideState& side = side_at(s, entering_side_idx);
    int ai = side.active_indices[0];
    PokemonState& mon = side.team[ai];

    auto has_sc = [&](int32_t cond) {
        for (const auto& e : side.side_conditions) if (e.condition == cond) return true;
        return false;
    };

    if (mon.item == ITEM_HEAVY_DUTY_BOOTS) return;

    // Stealth Rock
    if (has_sc(SC_STEALTH_ROCK)) {
        if (mon.ability != AB_MAGIC_GUARD) {
            double effv = 1.0;
            for (int32_t t : mon.types) effv *= cpp_type_effectiveness(TYPE_ROCK, t);
            int32_t damage = std::max(1, (int32_t)(mon.max_hp * effv / 8.0));
            int32_t new_hp = std::max(0, mon.hp - damage);
            mon.hp = new_hp;
            mon.fainted = (new_hp == 0);
            // Mirror Python faint_active (entry hazards): release inflicted traps on faint.
            if (mon.fainted) { cpp_release_inflicted_traps(s, entering_side_idx, ai); return; }
        }
    }
    if (mon.fainted) return;

    // Toxic Spikes
    bool ts1 = has_sc(SC_TOXIC_SPIKES_1), ts2 = has_sc(SC_TOXIC_SPIKES_2);
    if ((ts1 || ts2) && is_grounded(mon, s)) {
        if (has_type(mon, TYPE_POISON)) {
            std::vector<SideConditionEntry> kept;
            for (const auto& e : side.side_conditions)
                if (e.condition != SC_TOXIC_SPIKES_1 && e.condition != SC_TOXIC_SPIKES_2)
                    kept.push_back(e);
            side.side_conditions.assign_from(kept);
        } else {
            int32_t new_status = ts2 ? STATUS_TOXIC : STATUS_POISON;
            if (can_apply_status(mon, new_status, MOVE_NONE, AB_NONE, s)) {
                mon.status = new_status;
                mon.toxic_turns = (new_status == STATUS_TOXIC) ? 1 : 0;
            }
        }
    }

    // Spikes
    if (is_grounded(mon, s) && mon.ability != AB_MAGIC_GUARD) {
        int32_t spike_damage = 0;
        if (has_sc(SC_SPIKES_3)) spike_damage = mon.max_hp / 4;
        else if (has_sc(SC_SPIKES_2)) spike_damage = mon.max_hp / 6;
        else if (has_sc(SC_SPIKES_1)) spike_damage = mon.max_hp / 8;
        if (spike_damage > 0) {
            spike_damage = std::max(1, spike_damage);
            int32_t new_hp = std::max(0, mon.hp - spike_damage);
            mon.hp = new_hp;
            mon.fainted = (new_hp == 0);
            // Mirror Python faint_active (entry hazards): release inflicted traps on faint.
            if (mon.fainted) { cpp_release_inflicted_traps(s, entering_side_idx, ai); return; }
        }
    }

    // Sticky Web — entry hazard path has no ExecCtx; Eject Pack cannot trigger here.
    if (has_sc(SC_STICKY_WEB) && is_grounded(mon, s)) {
        change_stat_stage(s, entering_side_idx, 4, -1, /*opp*/true, false, false, nullptr);
        on_stat_dropped(s, entering_side_idx, 4);
    }
}

// ===========================================================================
// _apply_entry_effects (src/engine/effects.py 315–491) + file-local sub-helpers.
// Deterministic on-entry ability/item triggers. Logging is state-neutral (omitted).
// ===========================================================================
namespace {

// Slot-swap guard: make active_indices[0] == active_indices[pos], run f, restore.
// Mirrors _active_slot_swapped so change_stat_stage / on_stat_dropped target the right opponent.
template <typename F>
void with_active_slot_swapped(BattleState& state, int side_idx, int pos, F&& f) {
    SideState& side = side_at(state, side_idx);
    std::swap(side.active_indices[0], side.active_indices[pos]);
    f();
    SideState& side2 = side_at(state, side_idx);
    std::swap(side2.active_indices[0], side2.active_indices[pos]);
}

constexpr int32_t TRUANT_LOAFING_BIT = 16777216;  // Volatile.TRUANT_LOAFING

// _ABILITY_WEATHER_MAP lookup (-1 = miss).
int32_t ability_weather(int32_t ability) {
    switch (ability) {
        case AB_DRIZZLE:        return WEATHER_RAINY;
        case AB_PRIMORDIAL_SEA: return WEATHER_HEAVY_RAIN;
        case AB_DROUGHT:        return WEATHER_SUNNY;
        case AB_DESOLATE_LAND:  return WEATHER_HARSH_SUN;
        case AB_SAND_STREAM:    return WEATHER_SANDSTORM;
        case AB_SNOW_WARNING:   return WEATHER_HAIL;
        default:                return -1;
    }
}

// _ABILITY_TERRAIN_MAP lookup (-1 = miss).
int32_t ability_terrain(int32_t ability) {
    switch (ability) {
        case AB_ELECTRIC_SURGE: return TERRAIN_ELECTRIC;
        case AB_GRASSY_SURGE:   return TERRAIN_GRASSY;
        case AB_PSYCHIC_SURGE:  return TERRAIN_PSYCHIC;
        case AB_MISTY_SURGE:    return TERRAIN_MISTY;
        default:                return -1;
    }
}

// _TERRAIN_SEEDS: terrain -> (seed item, stat_idx). Returns false on miss.
// Item ids mirror Item.ELECTRIC_SEED(881)/GRASSY_SEED(884)/PSYCHIC_SEED(882)/MISTY_SEED(883).
bool terrain_seed(int32_t terrain, int32_t& seed_item, int& stat_idx) {
    switch (terrain) {
        case TERRAIN_ELECTRIC: seed_item = 881; stat_idx = 1; return true;
        case TERRAIN_GRASSY:   seed_item = 884; stat_idx = 1; return true;
        case TERRAIN_PSYCHIC:  seed_item = 882; stat_idx = 3; return true;
        case TERRAIN_MISTY:    seed_item = 883; stat_idx = 3; return true;
        default: return false;
    }
}

// _SKIP_TRACE: abilities Trace must not copy.
bool skip_trace(int32_t ability) {
    switch (ability) {
        case AB_TRACE: case AB_WONDER_GUARD: case AB_ILLUSION: case AB_IMPOSTER:
        case AB_POWER_CONSTRUCT: case AB_RECEIVER: case AB_MULTITYPE: case AB_RKS_SYSTEM:
        case AB_STANCE_CHANGE: case AB_SCHOOLING: case AB_FORECAST: case AB_NEUTRALIZING_GAS:
        case AB_NONE:
            return true;
        default:
            return false;
    }
}

// _INTIMIDATE_IMMUNE_ALWAYS (never breakable).
bool intim_immune_always(int32_t ability) {
    return ability == AB_CLEAR_BODY || ability == AB_WHITE_SMOKE
        || ability == AB_HYPER_CUTTER || ability == AB_FULL_METAL_BODY || ability == AB_SCRAPPY;
}

// _INTIMIDATE_IMMUNE_BREAKABLE (suppressible by Mold Breaker).
bool intim_immune_breakable(int32_t ability) {
    return ability == AB_INNER_FOCUS || ability == AB_OBLIVIOUS || ability == AB_OWN_TEMPO;
}

// _SCREEN_CONDITIONS: side conditions cleared by Screen Cleaner.
bool is_screen_condition(int32_t cond) {
    return cond == SC_REFLECT || cond == SC_LIGHT_SCREEN || cond == SC_AURORA_VEIL;
}

// _FORECAST_WEATHER_FORM: weather -> target Castform species (Species.CASTFORM default).
int32_t forecast_form(int32_t weather) {
    switch (weather) {
        case WEATHER_SUNNY: case WEATHER_HARSH_SUN: return SP_CASTFORM_SUNNY;
        case WEATHER_RAINY: case WEATHER_HEAVY_RAIN: return SP_CASTFORM_RAINY;
        case WEATHER_HAIL:                           return SP_CASTFORM_SNOWY;
        default:                                     return SP_CASTFORM;
    }
}

// _sync_neutralizing_gas (src/engine/_helpers.py 870–891): suppress non-Gas abilities while Gas
// is active on the field; restore saved abilities once Gas leaves.
void sync_neutralizing_gas(BattleState& s) {
    bool gas_active = false;
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (int32_t ai : side.active_indices)
            if (side.team[ai].ability == AB_NEUTRALIZING_GAS) gas_active = true;
    }
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (int32_t ai : side.active_indices) {
            PokemonState& p = side.team[ai];
            if (gas_active && p.ability != AB_NEUTRALIZING_GAS) {
                if (p.saved_ability == AB_NONE) {
                    p.saved_ability = p.ability;
                    p.ability = AB_NONE;
                }
            } else if (!gas_active && p.saved_ability != AB_NONE) {
                p.ability = p.saved_ability;
                p.saved_ability = AB_NONE;
            }
        }
    }
}

}  // namespace

// Shared with effects.cpp turn-start / EOT paths — defined in eff_internal.
namespace eff_internal {

bool is_silvally(int32_t species) {
    static const int32_t SILVALLY_FORMS[18] = {
        773, 1176, 1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184,
        1185, 1186, 1187, 1188, 1189, 1190, 1191, 1192,
    };
    for (int32_t sp : SILVALLY_FORMS) if (sp == species) return true;
    return false;
}

bool is_castform_form(int32_t species) {
    return species == SP_CASTFORM || species == SP_CASTFORM_SUNNY
        || species == SP_CASTFORM_RAINY || species == SP_CASTFORM_SNOWY;
}

// _MEMORY_TYPE: Memory item -> Type (NORMAL default, matching .get(item, Type.NORMAL)).
int32_t memory_type(int32_t item) {
    switch (item) {
        case ITEM_FIRE_MEMORY:     return TYPE_FIRE;
        case ITEM_WATER_MEMORY:    return TYPE_WATER;
        case ITEM_GRASS_MEMORY:    return TYPE_GRASS;
        case ITEM_ELECTRIC_MEMORY: return TYPE_ELECTRIC;
        case ITEM_ICE_MEMORY:      return TYPE_ICE;
        case ITEM_FIGHTING_MEMORY: return TYPE_FIGHTING;
        case ITEM_POISON_MEMORY:   return TYPE_POISON;
        case ITEM_GROUND_MEMORY:   return TYPE_GROUND;
        case ITEM_FLYING_MEMORY:   return TYPE_FLYING;
        case ITEM_PSYCHIC_MEMORY:  return TYPE_PSYCHIC;
        case ITEM_BUG_MEMORY:      return TYPE_BUG;
        case ITEM_ROCK_MEMORY:     return TYPE_ROCK;
        case ITEM_GHOST_MEMORY:    return TYPE_GHOST;
        case ITEM_DRAGON_MEMORY:   return TYPE_DRAGON;
        case ITEM_DARK_MEMORY:     return TYPE_DARK;
        case ITEM_STEEL_MEMORY:    return TYPE_STEEL;
        case ITEM_FAIRY_MEMORY:    return TYPE_FAIRY;
        default:                   return TYPE_NORMAL;
    }
}

// _update_castform (src/engine/_helpers.py 834–841): change Castform to the weather's form.
void update_castform(BattleState& s, int side_idx, int32_t weather) {
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.ability != AB_FORECAST || !is_castform_form(mon.species)) return;
    int32_t target = forecast_form(weather);
    if (mon.species != target) apply_form_change(s, side_idx, target);
}

} // namespace eff_internal

void cpp_apply_entry_effects(BattleState& s, int entering_side_idx, ExecCtx* ctx) {
    SideState& entering_side = side_at(s, entering_side_idx);
    int entering_ai = entering_side.active_indices[0];
    int opp_idx = 1 - entering_side_idx;

    int32_t ability = entering_side.team[entering_ai].ability;

    if (ability == AB_INTIMIDATE) {
        bool intim_mb = is_mold_breaker(side_at(s, entering_side_idx).team[entering_ai].base_ability);
        SideState& opp_side = side_at(s, opp_idx);
        std::vector<int32_t> opp_active(opp_side.active_indices.begin(), opp_side.active_indices.end());  // copy (list(...))
        for (int32_t opp_ai : opp_active) {
            PokemonState& opp_mon0 = side_at(s, opp_idx).team[opp_ai];
            if (opp_mon0.volatiles & VOLATILE_SUBSTITUTE) continue;
            bool immune = intim_immune_always(opp_mon0.ability)
                || (intim_immune_breakable(opp_mon0.ability) && !intim_mb);
            if (immune) continue;
            int32_t old_stage = get_stage(opp_mon0, 0);
            // _opp_pos = position of opp_ai within active_indices (after the swap above? no — current).
            SideState& opp_now = side_at(s, opp_idx);
            int opp_pos = 0;
            for (size_t i = 0; i < opp_now.active_indices.size(); ++i)
                if (opp_now.active_indices[i] == opp_ai) { opp_pos = (int)i; break; }
            with_active_slot_swapped(s, opp_idx, opp_pos, [&]() {
                PokemonState& om = side_at(s, opp_idx).team[opp_ai];
                if (om.ability == AB_GUARD_DOG) {
                    change_stat_stage(s, opp_idx, 0, +1, false, false, false);
                } else {
                    change_stat_stage(s, opp_idx, 0, -1, /*opp*/true, false, intim_mb, ctx);
                    int32_t actual_delta = get_stage(side_at(s, opp_idx).team[opp_ai], 0) - old_stage;
                    if (actual_delta < 0) {
                        on_stat_dropped(s, opp_idx, 0);
                        PokemonState& om2 = side_at(s, opp_idx).team[opp_ai];
                        if (om2.item == ITEM_ADRENALINE_ORB) {
                            om2.item = ITEM_NONE;
                            change_stat_stage(s, opp_idx, 4, +1, false, false, false);
                        }
                        PokemonState& om3 = side_at(s, opp_idx).team[opp_ai];
                        if (om3.ability == AB_RATTLED)
                            change_stat_stage(s, opp_idx, 4, +1, false, false, false);
                    }
                }
            });
        }
    } else if (ability_weather(ability) != -1) {
        s.weather = ability_weather(ability);
        s.weather_turns = -1;
    } else if (ability_terrain(ability) != -1) {
        s.terrain = ability_terrain(ability);
        s.terrain_turns = -1;
    } else if (is_mold_breaker(ability)) {
        // log-only (Mold Breaker / Teravolt / Turboblaze)
    } else if (ability == AB_UNNERVE || ability == AB_AS_ONE_GLASTRIER
               || ability == AB_AS_ONE_SPECTRIER) {
        // log-only
    } else if (ability == AB_PRESSURE) {
        // log-only
    } else if (ability == AB_TRACE) {
        SideState& opp_side = side_at(s, opp_idx);
        if (!opp_side.active_indices.empty()) {
            int32_t copied = opp_side.team[opp_side.active_indices[0]].ability;
            if (!skip_trace(copied))
                side_at(s, entering_side_idx).team[entering_ai].ability = copied;
        }
    } else if (ability == AB_IMPOSTER) {
        SideState& opp_side = side_at(s, opp_idx);
        if (!opp_side.active_indices.empty()) {
            const PokemonState& target = opp_side.team[opp_side.active_indices[0]];
            PokemonState& self = side_at(s, entering_side_idx).team[entering_ai];
            self.species = target.species;
            self.has_types = target.has_types;
            self.types = target.types;
            self.has_stats = target.has_stats;
            self.stat_hp = target.stat_hp; self.stat_atk = target.stat_atk;
            self.stat_def = target.stat_def; self.stat_spa = target.stat_spa;
            self.stat_spd = target.stat_spd; self.stat_spe = target.stat_spe;
            self.ability = target.ability;
            self.move_id0 = target.move_id0; self.move_id1 = target.move_id1;
            self.move_id2 = target.move_id2; self.move_id3 = target.move_id3;
            self.move_pp0 = std::min(5, target.move_pp0);
            self.move_pp1 = std::min(5, target.move_pp1);
            self.move_pp2 = std::min(5, target.move_pp2);
            self.move_pp3 = std::min(5, target.move_pp3);
            self.stage0 = target.stage0; self.stage1 = target.stage1; self.stage2 = target.stage2;
            self.stage3 = target.stage3; self.stage4 = target.stage4; self.stage5 = target.stage5;
            self.stage6 = target.stage6;
            self.is_mega = target.is_mega;
        }
    } else if (ability == AB_INTREPID_SWORD) {
        change_stat_stage(s, entering_side_idx, 0, +1, false, false, false);
    } else if (ability == AB_DAUNTLESS_SHIELD) {
        change_stat_stage(s, entering_side_idx, 1, +1, false, false, false);
    } else if (ability == AB_DOWNLOAD) {
        SideState& opp_side = side_at(s, opp_idx);
        if (!opp_side.active_indices.empty()) {
            const PokemonState& opp_mon = opp_side.team[opp_side.active_indices[0]];
            int32_t opp_def = cpp_effective_stat(opp_mon, 2);
            int32_t opp_spd = cpp_effective_stat(opp_mon, 4);
            if (opp_spd <= opp_def) change_stat_stage(s, entering_side_idx, 2, +1, false, false, false);
            else change_stat_stage(s, entering_side_idx, 0, +1, false, false, false);
        }
    }

    // Screen Cleaner: remove both sides' Reflect / Light Screen / Aurora Veil.
    if (ability == AB_SCREEN_CLEANER) {
        for (int si : {opp_idx, entering_side_idx}) {
            SideState& side = side_at(s, si);
            std::vector<SideConditionEntry> kept;
            for (const auto& e : side.side_conditions)
                if (!is_screen_condition(e.condition)) kept.push_back(e);
            side.side_conditions.assign_from(kept);
        }
    }

    // Terrain seed for the entering Pokemon.
    {
        int32_t seed_item; int stat_idx;
        if (terrain_seed(s.terrain, seed_item, stat_idx)) {
            PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
            if (!mon.fainted && mon.item == seed_item && is_grounded(mon, s)) {
                mon.item = ITEM_NONE;
                change_stat_stage(s, entering_side_idx, stat_idx, +1, false, false, false);
            }
        }
    }

    // Soul Dew: Latias/Latios +1 SpA, +1 SpD.
    {
        PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
        if (!mon.fainted && mon.item == ITEM_SOUL_DEW
            && (mon.species == SP_LATIAS || mon.species == SP_LATIOS)) {
            change_stat_stage(s, entering_side_idx, 2, +1, false, false, false);
            change_stat_stage(s, entering_side_idx, 3, +1, false, false, false);
        }
    }

    // Forecast: Castform form per current weather.
    {
        PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
        if (mon.ability == AB_FORECAST && is_castform_form(mon.species))
            update_castform(s, entering_side_idx, s.weather);
    }

    // RKS System: Silvally adopts its Memory item's type.
    {
        PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
        if (mon.ability == AB_RKS_SYSTEM || is_silvally(mon.species)) {
            mon.has_types = true;
            mon.types = {memory_type(mon.item)};
        }
    }

    sync_neutralizing_gas(s);

    // Pastel Veil: cure poison/toxic on self and allies.
    {
        PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
        if (!mon.fainted && mon.ability == AB_PASTEL_VEIL) {
            SideState& side = side_at(s, entering_side_idx);
            for (auto& m : side.team) {
                if (!m.fainted && (m.status == STATUS_POISON || m.status == STATUS_TOXIC)) {
                    m.status = STATUS_NONE;
                    m.toxic_turns = 0;
                }
            }
        }
    }

    // Truant: re-apply TRUANT_LOAFING if this Pokemon already acted this battle.
    {
        PokemonState& mon = side_at(s, entering_side_idx).team[entering_ai];
        if (!mon.fainted && mon.ability == AB_TRUANT && mon.has_acted)
            mon.volatiles |= TRUANT_LOAFING_BIT;
    }
}
