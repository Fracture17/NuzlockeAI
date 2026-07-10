// C++ port of end-of-turn residuals (src/engine/residuals.py, C1.5).
// Mirrors _apply_residuals mutation order exactly so whole-BattleState equality holds.
// Python log() calls are state-neutral and omitted. Unported branches throw "unported: ...".
#include "residuals.h"
#include "effects.h"
#include "effects_internal.h"
#include "effects_consts.h"
#include "species_types_lookup.h"
#include "exp.h"
#include "forced_trace.h"
#include "rng_resolver.h"  // RngLogCtx for participant plumbing on residual procs
#include "event_log.h"     // rich_log_status_apply (Yawn/Drowsy sleep)

#include <algorithm>
#include <stdexcept>
#include <vector>

using namespace eff;
using namespace eff_internal;

namespace {

// --- ids not already in effects_consts.h ---
constexpr int32_t AB_SPEED_BOOST = 3, AB_HARVEST = 139, AB_MOODY = 141, AB_SHED_SKIN = 61,
    AB_HYDRATION = 93, AB_HEALER = 131, AB_POISON_HEAL = 90, AB_HEATPROOF = 85,
    AB_LIQUID_OOZE_R = 64, AB_RAIN_DISH = 44, AB_DRY_SKIN = 87, AB_SOLAR_POWER = 94,
    AB_ICE_BODY = 115, AB_BAD_DREAMS = 123, AB_COMATOSE_R = 213, AB_EMERGENCY_EXIT = 194,
    AB_WIMP_OUT = 193, AB_KLUTZ = 103;

constexpr int32_t I_LEFTOVERS = 234, I_BLACK_SLUDGE = 281, I_STICKY_BARB = 288, I_FLAME_ORB = 273,
    I_TOXIC_ORB = 272, I_SAFETY_GOGGLES = 650, I_BIG_ROOT = 296, I_BINDING_BAND = 544;

constexpr int32_t PW_MAGIC_ROOM = 3;

constexpr int32_t VOL_AQUA_RING = 32768, VOL_INGRAIN = 65536, VOL_LEECH_SEEDED = 2,
    VOL_CURSED = 4, VOL_LOCKED_MOVE = 512, VOL_TAUNT_ACTIVE = 16, VOL_ENCORE_ACTIVE = 8,
    VOL_CONFUSED = 1, VOL_PERISH_SONG_ACTIVE = 16384;

constexpr int32_t VE_RAMPAGING = 12;

// Sandstorm/hail immune types & abilities.
bool has_any_type(const PokemonState& m, std::initializer_list<int32_t> ts) {
    for (int32_t t : ts) if (has_type(m, t)) return true;
    return false;
}
bool sandstorm_immune_ability(int32_t a) {
    return a == 8 /*SAND_VEIL*/ || a == 146 /*SAND_RUSH*/ || a == 159 /*SAND_FORCE*/
        || a == 245 /*SAND_SPIT*/ || a == 142 /*OVERCOAT*/;
}
bool hail_immune_ability(int32_t a) {
    return a == AB_ICE_BODY || a == 81 /*SNOW_CLOAK*/ || a == 142 /*OVERCOAT*/;
}

// ---- shared accessors mirroring the field-wide pass ----
const EffectsLuck& luck_for(const ResidualLuck& L, int side_idx) {
    return side_idx == 0 ? L.side0 : L.side1;
}

bool has_magic_room(const BattleState& s) {
    for (const auto& e : s.pseudo_weather) if (e.effect == PW_MAGIC_ROOM) return true;
    return false;
}

// _effective_weather: weather suppressed by Air Lock / Cloud Nine on either active mon.
int32_t effective_weather_r(const BattleState& s) {
    for (int si = 0; si < 2; ++si) {
        const SideState& side = si == 0 ? s.side0 : s.side1;
        for (int32_t ai : side.active_indices) {
            const PokemonState& m = side.team[ai];
            if (!m.fainted && (m.ability == 76 /*AIR_LOCK*/ || m.ability == 13 /*CLOUD_NINE*/))
                return WEATHER_NONE;
        }
    }
    return s.weather;
}

bool has_ve(const PokemonState& m, int32_t ve) {
    for (const auto& tv : m.timed_volatiles) if (tv.effect == ve) return true;
    return false;
}
// First turns value for a timed-volatile effect, or sentinel if absent.
bool ve_value(const PokemonState& m, int32_t ve, int32_t& out) {
    for (const auto& tv : m.timed_volatiles) if (tv.effect == ve) { out = tv.turns; return true; }
    return false;
}

int32_t get_speed(const PokemonState& m) {
    int32_t base = m.has_stats ? m.stat_spe : 0;
    int32_t stage = m.stage4;
    if (stage >= 0) return base * (2 + stage) / 2;
    return base * 2 / (2 - stage);
}

// ===========================================================================
// Per-band handlers. Signature mirrors Python: mutate the active mon at side[active_idx];
// return whether the slot fainted (callers skip remaining bands).
// ===========================================================================

PokemonState& amon(BattleState& s, int side_idx) { return active_mon(s, side_idx); }

// Band 1: weather chip + onWeather abilities.
bool band_weather(BattleState& s, int si, int active_idx, int32_t weather) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (weather == WEATHER_SANDSTORM) {
        if (!has_any_type(p, {TYPE_ROCK, TYPE_STEEL, 8 /*GROUND*/})
            && !sandstorm_immune_ability(p.ability)
            && p.ability != AB_MAGIC_GUARD && p.item != I_SAFETY_GOGGLES)
            p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 16));
    } else if (weather == WEATHER_HAIL) {
        if (p.ability == AB_ICE_BODY) {
            p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
        } else if (!has_type(p, TYPE_ICE) && !hail_immune_ability(p.ability)
                   && p.ability != AB_MAGIC_GUARD && p.item != I_SAFETY_GOGGLES) {
            p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 16));
        }
    }
    if (p.ability == AB_RAIN_DISH && (weather == WEATHER_RAINY || weather == WEATHER_HEAVY_RAIN)) {
        p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
    } else if (p.ability == AB_DRY_SKIN) {
        if (weather == WEATHER_RAINY || weather == WEATHER_HEAVY_RAIN)
            p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 8));
        else if (weather == WEATHER_SUNNY || weather == WEATHER_HARSH_SUN)
            p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 8));
    }
    if (p.ability == AB_SOLAR_POWER && (weather == WEATHER_SUNNY || weather == WEATHER_HARSH_SUN))
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 8));

    if (p.hp == 0) {
        rich_log_faint(s.turn_number, p.species, si);
        p.fainted = true;
        notify_faint_soul_heart(s);
        cpp_release_inflicted_traps(s, si, active_idx);
        return true;
    }
    return false;
}

// Band 5.1: Grassy Terrain heal.
bool band_grassy_terrain(BattleState& s, int si, int active_idx) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (s.terrain == TERRAIN_GRASSY && is_grounded(p, s))
        p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
    return false;
}

// Band 5.3: Shed Skin / Hydration / Healer.
bool band_status_cure(BattleState& s, int si, int active_idx, int32_t weather, const ResidualLuck& L) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];
    // Self-only residual proc: attribute to (si, active_idx); no defender.
    const RngLogCtx self_ctx{
        RngParticipants{(int8_t)si, (int8_t)active_idx, -1, -1}, s.turn_number};
    if (p.ability == AB_SHED_SKIN && p.status != STATUS_NONE) {
        if (resolve_proc_det(33, luck_for(L, si), &self_ctx)) p.status = STATUS_NONE;
    }
    if (p.ability == AB_HYDRATION && p.status != STATUS_NONE
        && (weather == WEATHER_RAINY || weather == WEATHER_HEAVY_RAIN))
        p.status = STATUS_NONE;
    if (p.ability == AB_HEALER && side.active_indices.size() > 1) {
        for (int32_t ally_slot : side.active_indices) {
            if (ally_slot == active_idx) continue;
            PokemonState& ally = side.team[ally_slot];
            // Ally-target: attacker=(si, active_idx) uses the ability; defender=(si, ally_slot).
            const RngLogCtx heal_ctx{
                RngParticipants{(int8_t)si, (int8_t)active_idx,
                                (int8_t)si, (int8_t)ally_slot}, s.turn_number};
            if (resolve_proc_det(30, luck_for(L, si), &heal_ctx) && ally.status != STATUS_NONE)
                ally.status = STATUS_NONE;
            break;
        }
    }
    return false;
}

// Band 5.4: Leftovers / Black Sludge.
bool band_item_heal(BattleState& s, int si, int active_idx) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (p.item == I_LEFTOVERS) {
        if (p.ability == AB_KLUTZ || has_magic_room(s)) {}
        else p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
    } else if (p.item == I_BLACK_SLUDGE) {
        if (p.ability == AB_KLUTZ || has_magic_room(s)) {}
        else if (has_type(p, TYPE_POISON))
            p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
        else {
            p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 8));
            if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; cpp_release_inflicted_traps(s, si, active_idx); return true; }
        }
    }
    return false;
}

// Band 6/7: Aqua Ring / Ingrain heal.
bool band_aqua_ring(BattleState& s, int si, int active_idx) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (p.volatiles & VOL_AQUA_RING) p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
    return false;
}
bool band_ingrain(BattleState& s, int si, int active_idx) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (p.volatiles & VOL_INGRAIN) p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 16));
    return false;
}

// Band 8: Leech Seed.
bool band_leech_seed(BattleState& s, int si, int active_idx, int opp_idx) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];
    if (!(p.volatiles & VOL_LEECH_SEEDED)) return false;
    if (p.ability == AB_MAGIC_GUARD) return false;
    int32_t drain = std::max(1, p.max_hp / 8);
    drain = std::min(drain, p.hp);
    p.hp = std::max(0, p.hp - drain);

    SideState& opp_side = side_at(s, opp_idx);
    int32_t seed_slot;
    int32_t opp_active_idx;
    if (ve_value(p, VE_LEECH_SEED_SOURCE_SLOT, seed_slot)
        && seed_slot < (int32_t)opp_side.active_indices.size()) {
        opp_active_idx = opp_side.active_indices[seed_slot];
    } else {
        opp_active_idx = opp_side.active_indices[0];
        for (int32_t ti : opp_side.active_indices)
            if (!opp_side.team[ti].fainted) { opp_active_idx = ti; break; }
    }
    PokemonState& opp = opp_side.team[opp_active_idx];
    if (!opp.fainted) {
        if (p.ability == AB_LIQUID_OOZE_R) {
            opp.hp = std::max(0, opp.hp - drain);
        } else {
            int32_t heal = (opp.item == I_BIG_ROOT) ? (int32_t)(drain * 1.3) : drain;
            opp.hp = std::min(opp.max_hp, opp.hp + heal);
        }
    }
    if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; notify_faint_soul_heart(s); cpp_release_inflicted_traps(s, si, active_idx); return true; }
    return false;
}

// Band 9: Poison Heal / Toxic / Poison. Commits HP + berry check.
bool band_poison(BattleState& s, int si, int active_idx, int opp_idx, const ResidualLuck& L) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (p.ability == AB_POISON_HEAL && (p.status == STATUS_POISON || p.status == STATUS_TOXIC)) {
        p.hp = std::min(p.max_hp, p.hp + std::max(1, p.max_hp / 8));
    } else if (p.status == STATUS_TOXIC && p.ability != AB_MAGIC_GUARD) {
        int32_t dmg = std::max(1, (int32_t)((long long)p.max_hp * p.toxic_turns / 16));
        p.hp = std::max(0, p.hp - dmg);
        p.toxic_turns = std::min(p.toxic_turns + 1, 15);
    } else if (p.status == STATUS_POISON && p.ability != AB_MAGIC_GUARD) {
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 8));
    }
    if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; notify_faint_soul_heart(s); cpp_release_inflicted_traps(s, si, active_idx); return true; }
    check_berry(s, si, opp_idx, luck_for(L, si).rng, luck_for(L, si).overrides);
    return false;
}

// Band 10: Burn. Commits HP + berry check.
bool band_burn(BattleState& s, int si, int active_idx, int opp_idx, const ResidualLuck& L) {
    PokemonState& p = side_at(s, si).team[active_idx];
    if (p.status == STATUS_BURN && p.ability != AB_MAGIC_GUARD) {
        int32_t divisor = (p.ability == AB_HEATPROOF) ? 32 : 16;
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / divisor));
    }
    if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; notify_faint_soul_heart(s); cpp_release_inflicted_traps(s, si, active_idx); return true; }
    check_berry(s, si, opp_idx, luck_for(L, si).rng, luck_for(L, si).overrides);
    return false;
}

// Band 28: Speed Boost / Harvest / Moody / Bad Dreams / Flame Orb / Toxic Orb.
bool band_late(BattleState& s, int si, int active_idx, int opp_idx, int32_t weather,
               const ResidualLuck& L, const ResidualCtx& ctx) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];

    if (p.ability == AB_SPEED_BOOST && p.turns_in_battle > 0) {
        p.stage4 = std::min(6, p.stage4 + 1);
    }
    if (p.ability == AB_HARVEST && p.item == ITEM_NONE && p.consumed_berry != ITEM_NONE) {
        int harvest_chance = (weather == WEATHER_SUNNY || weather == WEATHER_HARSH_SUN) ? 100 : 50;
        const RngLogCtx harvest_ctx{
            RngParticipants{(int8_t)si, (int8_t)active_idx, -1, -1}, s.turn_number};
        if (resolve_proc_det(harvest_chance, luck_for(L, si), &harvest_ctx)) p.item = p.consumed_berry;
    }
    if (p.ability == AB_MOODY) {
        // +2 to one stat (0-6), -1 to a different stat (0-6 excl boost). R&B: acc/eva
        // eligible for both picks. Mirrors residuals.py:347-360. Dual path (like ROAR_TARGET):
        // random_mode draws natively (2 draws, uniform 6 non-boost candidates for drop);
        // GameDriver oracle path resolves MOODY_STATS via boost=i0%7, drop=i1%7 and fails
        // loud if boost==drop; plain run_game/bridge path stays fail-loud at Phase-1 boundary.
        const EffectsLuck& el = luck_for(L, si);
        int boost_idx, drop_idx;
        if (el.random_mode) {
            if (!el.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
            if (el.rng->forced) {
                // Consume the Cat-A MOODY_STATS answer (i0=boost, i1=drop); mirrors Python residuals.py:350.
                const ForcedAnswer& a = el.rng->forced->next_answer(el.rng->current_turn, RngEventC::MOODY_STATS, -1);
                boost_idx = a.i0;
                drop_idx = a.i1;
            } else {
                boost_idx = el.rng->randint(0, 6);
                drop_idx = el.rng->randint(0, 5);
                if (drop_idx >= boost_idx) drop_idx += 1;
            }
        } else if (el.overrides) {
            OracleAnswer ans = oracle_resolve_pair(
                el.overrides, RngEventC::MOODY_STATS, {0, 1, 2, 3, 4, 5, 6},
                RngParticipants{(int8_t)si, (int8_t)active_idx, (int8_t)(1 - si), (int8_t)opp_idx},
                s.turn_number);
            boost_idx = ans.i0 % 7;
            drop_idx = ans.i1 % 7;
            if (boost_idx == drop_idx)
                throw std::runtime_error("MOODY_STATS answer boost==drop");
        } else {
            throw std::runtime_error("unported: moody");
        }
        change_stat_stage(s, si, boost_idx, +2, false, false, false);
        change_stat_stage(s, si, drop_idx, -1, false, false, false);
    }

    SideState& opp_side = side_at(s, opp_idx);
    int32_t opp_active_idx = opp_side.active_indices[0];
    for (int32_t ti : opp_side.active_indices)
        if (!opp_side.team[ti].fainted) { opp_active_idx = ti; break; }
    PokemonState& opp = opp_side.team[opp_active_idx];
    if (p.ability == AB_BAD_DREAMS
        && (opp.status == STATUS_SLEEP || opp.ability == AB_COMATOSE_R)
        && !opp.fainted && opp.ability != AB_MAGIC_GUARD) {
        int32_t dmg = std::max(1, opp.max_hp / 8);
        int32_t nh = std::max(0, opp.hp - dmg);
        opp.hp = nh;
        opp.fainted = (nh == 0);
        if (nh == 0) {
            rich_log_faint(s.turn_number, opp.species, opp_idx);
            cpp_release_inflicted_traps(s, opp_idx, opp_active_idx);
        }
    }

    if (p.item == I_FLAME_ORB && p.status == STATUS_NONE) {
        if (can_apply_status(p, STATUS_BURN, MOVE_NONE, AB_NONE, s)) apply_status_to(s, si, STATUS_BURN);
    }
    if (p.item == I_TOXIC_ORB && p.status == STATUS_NONE) {
        if (can_apply_status(p, STATUS_TOXIC, MOVE_NONE, AB_NONE, s)) {
            apply_status_to(s, si, STATUS_TOXIC);
            side.team[active_idx].toxic_turns = 1;
        }
    }
    return false;
}

// inflictor_gone (trap_release.py:7): True if the trap's inflictor (a team index on the
// opponent's side) has fainted or is no longer active.
static bool inflictor_gone(BattleState& s, int opp_idx, int32_t source_team_idx) {
    SideState& opp = side_at(s, opp_idx);
    if (opp.team[source_team_idx].fainted) return true;
    for (int32_t ai : opp.active_indices) if (ai == source_team_idx) return false;
    return true;
}

// Late per-slot: Sticky Barb / Octolock / Nightmare / Curse / Bound. Berry check at end.
bool band_late_damage(BattleState& s, int si, int active_idx, int opp_idx, const ResidualLuck& L) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];

    if (p.item == I_STICKY_BARB && p.ability != AB_MAGIC_GUARD) {
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 8));
        if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; notify_faint_soul_heart(s); cpp_release_inflicted_traps(s, si, active_idx); return true; }
    }
    if (has_ve(p, VE_OCTOLOCK)) {
        change_stat_stage(s, si, 1, -1, false, false, false);
        change_stat_stage(s, si, 3, -1, false, false, false);
    }
    if (has_ve(p, VE_NIGHTMARE) && p.status == STATUS_SLEEP && p.ability != AB_MAGIC_GUARD) {
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 4));
        if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; cpp_release_inflicted_traps(s, si, active_idx); return true; }
    }
    if (has_ve(p, VE_NIGHTMARE) && p.status != STATUS_SLEEP) {
        std::vector<TimedVolatile> kept;
        for (const auto& tv : p.timed_volatiles) if (tv.effect != VE_NIGHTMARE) kept.push_back(tv);
        p.timed_volatiles.assign_from(kept);
    }
    if ((p.volatiles & VOL_CURSED) && p.ability != AB_MAGIC_GUARD) {
        p.hp = std::max(0, p.hp - std::max(1, p.max_hp / 4));
        if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; cpp_release_inflicted_traps(s, si, active_idx); return true; }
    }

    int32_t bound_turns;
    // BOUND counter holds exact ticks remaining (4/5/7); every turn it is >= 1 deals a tick,
    // including the final counter==1 turn. res_tick_timed_volatiles decrements/clears afterwards.
    if (ve_value(p, VE_BOUND, bound_turns) && bound_turns >= 1 && p.ability != AB_MAGIC_GUARD) {
        // If the inflictor already left earlier this residual phase, skip the tick.
        int32_t bound_source_id;
        bool inflictor_already_gone = ve_value(p, VE_BOUND_SOURCE_ID, bound_source_id)
            && inflictor_gone(s, opp_idx, bound_source_id);
        if (inflictor_already_gone) { check_berry(s, si, opp_idx, luck_for(L, si).rng, luck_for(L, si).overrides); return false; }
        int32_t bound_slot;
        SideState& opp_side = side_at(s, opp_idx);
        PokemonState* opp_active;
        if (ve_value(p, VE_BOUND_SOURCE_SLOT, bound_slot)
            && bound_slot < (int32_t)opp_side.active_indices.size()
            && !opp_side.team[opp_side.active_indices[bound_slot]].fainted)
            opp_active = &opp_side.team[opp_side.active_indices[bound_slot]];
        else
            opp_active = &opp_side.team[opp_side.active_indices[0]];
        int32_t bound_dmg = (opp_active->item == I_BINDING_BAND)
            ? std::max(1, p.max_hp / 6) : std::max(1, p.max_hp / 8);
        p.hp = std::max(0, p.hp - bound_dmg);
        if (p.hp == 0) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; cpp_release_inflicted_traps(s, si, active_idx); return true; }
    }

    check_berry(s, si, opp_idx, luck_for(L, si).rng, luck_for(L, si).overrides);
    return false;
}

// Decrement timed volatile counters: Perish Song faint, Rampage->Confusion, Drowsy->Sleep, Roost restore.
bool res_tick_timed_volatiles(BattleState& s, int si, int active_idx) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];
    std::vector<TimedVolatile> new_timed;
    bool perish_faint = false;

    for (const auto& tvc : p.timed_volatiles) {
        int32_t effect = tvc.effect, turns = tvc.turns;
        if (turns < 0) { new_timed.push_back({effect, turns}); continue; }
        if (effect == VE_LEECH_SEED_SOURCE_SLOT || effect == VE_BOUND_SOURCE_SLOT
            || effect == VE_BOUND_SOURCE_ID || effect == VE_TRAPPED_SOURCE_ID
            || effect == VE_CHARGING_MOVE) {
            new_timed.push_back({effect, turns}); continue;
        }
        if (effect == VE_RAMPAGING && p.status == STATUS_SLEEP) {
            p.volatiles &= ~VOL_LOCKED_MOVE; p.locked_slot = -1; continue;
        }
        int32_t new_turns = turns - 1;
        if (new_turns > 0) { new_timed.push_back({effect, new_turns}); continue; }
        // expired
        if (effect == VE_TAUNT) p.volatiles &= ~VOL_TAUNT_ACTIVE;
        else if (effect == VE_ENCORE) { p.volatiles &= ~VOL_ENCORE_ACTIVE; p.locked_slot = -1; }
        else if (effect == VE_PERISH_SONG) perish_faint = true;
        else if (effect == VE_RAMPAGING) {
            if (p.status == STATUS_SLEEP) { p.volatiles &= ~VOL_LOCKED_MOVE; p.locked_slot = -1; }
            else { p.volatiles = (p.volatiles & ~VOL_LOCKED_MOVE) | VOL_CONFUSED; p.locked_slot = -1; }
        } else if (effect == VE_ROOST) {
            std::vector<int32_t> base = cpp_species_types(p.species);
            bool base_has_flying = false; for (int32_t t : base) if (t == TYPE_FLYING) base_has_flying = true;
            bool cur_has_flying = has_type(p, TYPE_FLYING);
            if (base_has_flying && !cur_has_flying) {
                if (base.size() == 1) { p.types = {TYPE_FLYING}; p.has_types = true; }
                else {
                    int flying_slot = 0;
                    for (size_t i = 0; i < base.size(); ++i) if (base[i] == TYPE_FLYING) { flying_slot = (int)i; break; }
                    std::vector<int32_t> restored(p.types.begin(), p.types.end());
                    restored.insert(restored.begin() + flying_slot, TYPE_FLYING);
                    bool base_has_normal = false; for (int32_t t : base) if (t == TYPE_NORMAL) base_has_normal = true;
                    std::vector<int32_t> filtered;
                    for (int32_t t : restored) if (t != TYPE_NORMAL || base_has_normal) filtered.push_back(t);
                    p.types.assign_from(filtered); p.has_types = true;
                }
            }
        } else if (effect == VE_DROWSY) {
            if (can_apply_status(p, STATUS_SLEEP, MOVE_NONE, AB_NONE, s)) {
                p.status = STATUS_SLEEP;
                // Yawn/Drowsy applies sleep inline; STATUS_APPLY emitted directly
                // (Python residuals.py:584). Consumer reads side/target/status only.
                rich_log_status_apply(s.turn_number, p.species, STATUS_SLEEP, si, SourceTag::MOVE);
            }
        }
        // DISABLE/THROAT_CHOPPED/LASER_FOCUS/SEMI_INVULNERABLE: just expire (no-op)
    }
    // If BOUND expired naturally, drop its orphaned BOUND_SOURCE_SLOT/BOUND_SOURCE_ID companions.
    bool still_bound = false;
    for (const auto& tv : new_timed) if (tv.effect == VE_BOUND) { still_bound = true; break; }
    if (!still_bound) {
        std::vector<TimedVolatile> filtered;
        for (const auto& tv : new_timed)
            if (tv.effect != VE_BOUND_SOURCE_SLOT && tv.effect != VE_BOUND_SOURCE_ID)
                filtered.push_back(tv);
        new_timed = filtered;
    }
    p.timed_volatiles.assign_from(new_timed);
    if (perish_faint) { rich_log_faint(s.turn_number, p.species, si); p.fainted = true; p.hp = 0; cpp_release_inflicted_traps(s, si, active_idx); return true; }
    return false;
}

// Emergency Exit / Wimp Out: queue a pending switch if HP crossed half.
void emergency_exit_check(BattleState& s, int si, int active_idx, int hp_before,
                          std::vector<PendingSwitch>& pending) {
    SideState& side = side_at(s, si);
    PokemonState& p = side.team[active_idx];
    if (p.ability != AB_EMERGENCY_EXIT && p.ability != AB_WIMP_OUT) return;
    if (p.hp <= 0) return;
    int32_t half = p.max_hp / 2;
    if (!(hp_before > half && half >= p.hp)) return;
    bool bench = false;
    for (size_t i = 0; i < side.team.size(); ++i) {
        bool active = false;
        for (int32_t ai : side.active_indices) if ((int)i == ai) { active = true; break; }
        if (!active && !side.team[i].fainted) { bench = true; break; }
    }
    if (bench) pending.push_back({si, "emergency_exit"});
}

// _apply_damage (Future Sight path): Endure / Focus Band / Focus Sash / Sturdy + berry check.
constexpr int32_t VOL_ENDURE_ACTIVE = 2097152;  // Volatile.ENDURE_ACTIVE (was wrongly 128 = CHARGING)
constexpr int32_t I_FOCUS_BAND = 230, I_FOCUS_SASH = 275;
constexpr int32_t AB_STURDY = 5;
void apply_damage_fs(BattleState& s, int defender_idx, int damage,
                     const EffectsLuck& luck, int opp_side_idx) {
    PokemonState& d = active_mon(s, defender_idx);
    int32_t new_hp = std::max(0, d.hp - damage);
    int32_t new_item = d.item;
    if (new_hp == 0 && (d.volatiles & VOL_ENDURE_ACTIVE)) new_hp = 1;
    else if (new_hp == 0 && d.item == I_FOCUS_BAND) {
        // Future Sight path: attacker unknown (residual damage), defender = the fs target.
        const RngLogCtx fb_ctx{
            RngParticipants{-1, -1, (int8_t)defender_idx,
                            (int8_t)side_at(s, defender_idx).active_indices[0]},
            s.turn_number};
        if (resolve_proc_det(10, luck, &fb_ctx)) new_hp = 1;
    }
    else if (new_hp == 0 && d.item == I_FOCUS_SASH && d.hp == d.max_hp) { new_hp = 1; new_item = ITEM_NONE; }
    else if (new_hp == 0 && d.ability == AB_STURDY && d.hp == d.max_hp) new_hp = 1;

    int32_t actual_taken = std::min(damage, d.hp);
    bool fainted = (new_hp == 0);
    bool new_took = d.took_damage_this_turn || (actual_taken > 0);
    d.hp = new_hp; d.fainted = fainted; d.item = new_item; d.took_damage_this_turn = new_took;
    if (fainted) cpp_release_inflicted_traps(s, defender_idx, side_at(s, defender_idx).active_indices[0]);
    if (!fainted) check_berry(s, defender_idx, opp_side_idx, luck.rng, luck.overrides);
}

// EXP flush: award EXP for any fainted opponent (side-1) active mon (C1.7a port).
// Mutates the per-slot participant lists (cleared on award) so repeated flushes are idempotent.
void exp_flush(BattleState& s, std::vector<std::vector<int32_t>>& exp_participants,
               bool allow_fainted_winners = false) {
    cpp_flush_opponent_faint_exp(s, exp_participants, allow_fainted_winners);
}

// tib gating per tib_counts_initiators: increment only for initiators (or all if ctx unset/null).
bool is_initiator(const ResidualCtx& ctx, int side_idx, int team_idx) {
    if (!ctx.ctx_present || ctx.turn_start_active_null) return true;
    for (const auto& pr : ctx.turn_start_active)
        if (pr.first == side_idx && pr.second == team_idx) return true;
    return false;
}

} // namespace

// ===========================================================================
// cpp_apply_residuals
// ===========================================================================
void cpp_apply_residuals(BattleState& s, const ResidualLuck& L, const ResidualCtx& ctx,
                         std::vector<PendingSwitch>& pending) {

    // Mutable copy of the ctx participant lists; flushes clear awarded slots (idempotent).
    std::vector<std::vector<int32_t>> exp_participants = ctx.exp_participants;

    // --- Per-slot setup: tib counter, flag resets, pre-damage berry checks ---
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (size_t slot_pos = 0; slot_pos < side.active_indices.size(); ++slot_pos) {
            int32_t active_idx = side.active_indices[slot_pos];
            PokemonState& p = side.team[active_idx];
            if (p.fainted) continue;
            bool initiated = is_initiator(ctx, si, active_idx);
            p.turns_in_battle += initiated ? 1 : 0;
            p.took_damage_this_turn = false;
            p.had_stat_lowered_this_turn = false;
            p.had_stat_raised_this_turn = false;
            p.last_physical_damage_taken = 0;
            p.last_special_damage_taken = 0;
            p.last_damage_taken = 0;
            p.sucker_punch_last_turn = false;
            // status / confusion berry pre-checks (slot-swap to this position)
            int32_t saved = side.active_indices[0];
            side.active_indices[0] = active_idx;
            check_status_berry(s, si, 1 - si);
            check_confusion_berry(s, si, 1 - si);
            side.active_indices[0] = saved;
        }
    }

    int32_t weather = effective_weather_r(s);

    // Collect (side, slot_pos) active non-fainted entries.
    auto active_entries = [&]() {
        std::vector<std::pair<int,int>> out;
        for (int si = 0; si < 2; ++si) {
            SideState& side = side_at(s, si);
            for (size_t sp = 0; sp < side.active_indices.size(); ++sp) {
                int32_t ai = side.active_indices[sp];
                if (!side.team[ai].fainted) out.push_back({si, (int)sp});
            }
        }
        return out;
    };

    // Snapshot HP for Emergency Exit.
    int hp_before_arr[2][2];
    for (auto& row : hp_before_arr) for (int& v : row) v = 0;
    for (auto& e : active_entries()) {
        int32_t ai = side_at(s, e.first).active_indices[e.second];
        hp_before_arr[e.first][e.second] = side_at(s, e.first).team[ai].hp;
    }

    // --- Per-battler chain loop (battler-major; mirrors _apply_residuals) ---
    // Fixed order: speed descending, ties by side index ascending. Computed ONCE over ALL
    // active slots (including fainted, which are then skipped) so mid-phase speed changes do
    // NOT reorder remaining battlers. Each battler runs its ENTIRE chain (all 10 bands + the
    // late per-slot handlers + Emergency Exit) before the next battler starts, breaking on faint.
    std::vector<std::pair<int,int>> battler_order;
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (size_t sp = 0; sp < side.active_indices.size(); ++sp)
            battler_order.push_back({si, (int)sp});
    }
    std::stable_sort(battler_order.begin(), battler_order.end(), [&](auto& a, auto& b) {
        int sa = get_speed(side_at(s, a.first).team[side_at(s, a.first).active_indices[a.second]]);
        int sb = get_speed(side_at(s, b.first).team[side_at(s, b.first).active_indices[b.second]]);
        if (sa != sb) return sa > sb;
        return a.first < b.first;
    });

    for (auto& e : battler_order) {
        int si = e.first, sp = e.second;
        SideState& side = side_at(s, si);
        int32_t active_idx = side.active_indices[sp];
        if (side.team[active_idx].fainted) continue;  // skip fainted battler (no EXP flush)
        int opp_idx = 1 - si;
        // Slot-swap so band helpers that call shared helpers (change_stat_stage etc.) see this slot.
        int32_t saved = side.active_indices[0];
        side.active_indices[0] = active_idx;

        // Run all band handlers in order; stop the chain immediately on faint.
        for (int band = 0; band < 10; ++band) {
            if (side.team[active_idx].fainted) break;
            switch (band) {
                case 0: band_weather(s, si, active_idx, weather); break;
                case 1: band_grassy_terrain(s, si, active_idx); break;
                case 2: band_status_cure(s, si, active_idx, weather, L); break;
                case 3: band_item_heal(s, si, active_idx); break;
                case 4: band_aqua_ring(s, si, active_idx); break;
                case 5: band_ingrain(s, si, active_idx); break;
                case 6: band_leech_seed(s, si, active_idx, opp_idx); break;
                case 7: band_poison(s, si, active_idx, opp_idx, L); break;
                case 8: band_burn(s, si, active_idx, opp_idx, L); break;
                case 9: band_late(s, si, active_idx, opp_idx, weather, L, ctx); break;
            }
        }

        // Late per-slot handlers (Sticky Barb damage, timed-volatile tick) then Emergency Exit.
        if (!side.team[active_idx].fainted)
            band_late_damage(s, si, active_idx, opp_idx, L);
        if (!side.team[active_idx].fainted)
            res_tick_timed_volatiles(s, si, active_idx);
        if (!side.team[active_idx].fainted)
            emergency_exit_check(s, si, active_idx, hp_before_arr[si][sp], pending);

        side.active_indices[0] = saved;

        // Centralized EXP flush after this battler's full chain completes.
        exp_flush(s, exp_participants, /*allow_fainted_winners=*/true);
    }

    // --- Wish ---
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        if (side.has_wish_pending) {
            int32_t turns_left = side.wish_turns - 1;
            if (turns_left <= 0) {
                int actual_pos = std::min((int)side.wish_slot, (int)side.active_indices.size() - 1);
                int32_t rid = side.active_indices[actual_pos];
                PokemonState& r = side.team[rid];
                if (!r.fainted) r.hp = std::min(r.max_hp, r.hp + side.wish_hp);
                side.has_wish_pending = false;
                side.wish_turns = side.wish_hp = side.wish_slot = 0;
            } else {
                side.wish_turns = turns_left;
            }
        }
    }

    // --- Future Sight / Doom Desire ---
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        if (side.has_future_sight_pending) {
            int32_t turns_left = side.fs_turns - 1;
            if (turns_left <= 0) {
                int actual_pos = std::min((int)side.fs_target_slot, (int)side.active_indices.size() - 1);
                int32_t rid = side.active_indices[actual_pos];
                if (!side.team[rid].fainted) {
                    int32_t saved = side.active_indices[0];
                    side.active_indices[0] = rid;
                    apply_damage_fs(s, si, side.fs_damage, luck_for(L, si), 1 - si);
                    side.active_indices[0] = saved;
                }
                side.has_future_sight_pending = false;
                side.fs_turns = side.fs_damage = side.fs_move = side.fs_target_slot = 0;
            } else {
                side.fs_turns = turns_left;
            }
        }
    }
    exp_flush(s, exp_participants);
}
