// C1.7d Unit 3: the pre-damage guard chain + accuracy (see move_exec_guards.h). Byte-identical
// mirror of the _handle_pre_damage_* family in src/engine/core.py on deterministic paths. Python
// log() calls are state-neutral and omitted. Accuracy stages, item/ability modifiers, type
// immunity (stateful absorption), Protect/Wide/Quick guard, doubles redirect, move-type resolution.
// random_mode draws via NativeRng (rng must be non-null in GuardLuck when random_mode=true).
#include "move_exec_guards.h"
#include "rng_resolver.h"        // rng_resolve_accuracy
#include "move_exec_helpers.h"   // cpp_apply_damage, cpp_reset_stockpile, MoveExecLuck
#include "effects_internal.h"    // active_mon, side_at, change_stat_stage, apply_form_change, ...
#include "effects_consts.h"
#include "damage.h"              // cpp_calculate_damage, LuckProfileC
#include "type_chart_lookup.h"   // cpp_type_effectiveness
#include "event_log.h"           // rich_log_charge_turn / semi_invuln_enter / exit
#include "../generated/move_data.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

using namespace eff;
using eff_internal::active_mon;
using eff_internal::side_at;
using eff_internal::change_stat_stage;
using eff_internal::apply_form_change;
using eff_internal::can_apply_status;
using eff_internal::apply_status_to;

namespace {

// MOVE_TABLE lookup + triage bump are defined with internal linkage in core_leaf.cpp; reimplemented
// here (identical) to avoid a cross-TU dependency on those file-local symbols.
constexpr int MOVE_TABLE_COUNT = 813;
const MoveData* move_data_get(int32_t move_id) {
    int lo = 0, hi = MOVE_TABLE_COUNT;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid;
    }
    if (lo < MOVE_TABLE_COUNT && MOVE_TABLE[lo].move_id == move_id) return &MOVE_TABLE[lo];
    return nullptr;
}
const MoveData& move_data_get_or_throw(int32_t move_id) {
    const MoveData* md = move_data_get(move_id);
    if (md == nullptr)
        throw std::runtime_error("move_exec_guards: move id " + std::to_string(move_id) + " not found");
    return *md;
}
// _triage_priority_bump: Triage (ability 205) grants +3 priority to recovery/drain moves.
constexpr int32_t AB_TRIAGE = 205, TAG_RECOVERY = 4;
int32_t triage_priority_bump(int32_t ability, const MoveData& md) {
    if (ability != AB_TRIAGE) return 0;
    bool recovery = (md.tags & TAG_RECOVERY) != 0;
    bool drain = md.drain_num != -1;
    return (recovery || drain) ? 3 : 0;
}

// ---- Constants not in effects_consts.h ----
constexpr int32_t VE_SEMI_INVULNERABLE = 27;
constexpr int32_t VOLATILE_PROTEAN_USED = 67108864;
// effects_consts.h omits these type ids; mirror the Type enum exactly.
constexpr int32_t TYPE_GROUND = 8, TYPE_PSYCHIC = 10, TYPE_DRAGON = 14, TYPE_FAIRY = 17;

// Moves
constexpr int32_t MV_NONE = 0, MV_FLY = 19, MV_JUMP_KICK = 26, MV_DIG = 91, MV_SURF = 57,
    MV_GUST = 16, MV_BLIZZARD = 59, MV_EARTHQUAKE = 89, MV_THUNDER = 87, MV_DIVE = 291,
    MV_TWISTER = 239, MV_MAGNITUDE = 222, MV_FISSURE = 90, MV_BOUNCE = 340, MV_PHANTOM_FORCE = 566,
    MV_HURRICANE = 542, MV_SKY_UPPERCUT = 327, MV_SMACK_DOWN = 479, MV_SKY_DROP = 507,
    MV_THOUSAND_ARROWS = 614, MV_WHIRLPOOL = 250, MV_HIGH_JUMP_KICK = 136, MV_SUPERCELL_SLAM = 916,
    MV_HIDDEN_POWER = 237, MV_WEATHER_BALL = 311, MV_NATURAL_GIFT = 363, MV_MULTI_ATTACK = 718,
    MV_SHEER_COLD = 329, MV_GUILLOTINE = 12, MV_HORN_DRILL = 32, MV_STEEL_BEAM = 796,
    MV_STEEL_ROLLER = 798, MV_DREAM_EATER = 138, MV_BURN_UP = 682, MV_LAST_RESORT = 387,
    MV_SPIT_UP = 255, MV_BRICK_BREAK = 280, MV_PSYCHIC_FANGS = 706, MV_SUCKER_PUNCH = 389,
    MV_FOCUS_PUNCH = 264, MV_HYPERSPACE_FURY = 621, MV_HYPERSPACE_HOLE = 593, MV_FEINT = 364,
    MV_PLAY_NICE = 589, MV_ME_FIRST = 382, MV_ROLLOUT = 205, MV_ICE_BALL = 301;

// Items
constexpr int32_t ITM_NONE = 0, ITM_BRIGHT_POWDER = 213, ITM_WIDE_LENS = 265,
    ITM_SAFETY_GOGGLES = 650, ITM_BLUNDER_POLICY = 1121, ITM_METRONOME = 277,
    ITM_NORMAL_GEM = 564;

// Abilities
constexpr int32_t AB_HUSTLE = 55, AB_VICTORY_STAR = 162, AB_TANGLED_FEET = 77, AB_SAND_VEIL = 8,
    AB_SNOW_CLOAK = 81, AB_NO_GUARD = 99, AB_COMPOUND_EYES = 14, AB_KEEN_EYE = 51,
    AB_UNAWARE = 109, AB_NORMALIZE = 96, AB_LIQUID_VOICE = 204, AB_SOUNDPROOF = 43,
    AB_BULLETPROOF = 171, AB_OVERCOAT = 142, AB_ICE_FACE = 248, AB_WONDER_GUARD = 25,
    AB_PROTEAN = 168, AB_LIBERO = 236, AB_LIGHTNING_ROD = 31, AB_STORM_DRAIN = 114,
    AB_DAZZLING = 219, AB_QUEENLY_MAJESTY = 214, AB_ARMOR_TAIL = 296, AB_UNSEEN_FIST = 260,
    AB_LONG_REACH = 203, AB_MAGIC_GUARD = 98, AB_STANCE_CHANGE = 176, AB_DAMP = 6,
    AB_VOLT_ABSORB = 10, AB_MOTOR_DRIVE = 78, AB_WATER_ABSORB = 11, AB_DRY_SKIN = 87,
    AB_SAP_SIPPER = 157, AB_EARTH_EATER = 297, AB_LEVITATE = 26, AB_COMATOSE = 213;

// Move tags
constexpr int32_t TAG_CONTACT = 128, TAG_SOUND = 256, TAG_BULLET = 512, TAG_POWDER = 16384;

// Species
constexpr int32_t SP_AEGISLASH = 681, SP_AEGISLASH_BLADE = 1156, SP_HOOPA_UNBOUND = 1168,
    SP_EISCUE = 875, SP_EISCUE_NOICE = 1224;

// Protect special-move ids
constexpr int32_t MV_KINGS_SHIELD = 588, MV_SPIKY_SHIELD = 596, MV_BANEFUL_BUNKER = 661,
    MV_OBSTRUCT = 792;

// Two-turn / charge sets
constexpr int32_t MV_SOLAR_BEAM = 76, MV_SOLAR_BLADE = 669, MV_METEOR_BEAM = 800,
    MV_FUTURE_SIGHT = 248, MV_DOOM_DESIRE = 353, MV_FAKE_OUT = 252, MV_FIRST_IMPRESSION = 660,
    MV_BELCH = 562, MV_POLTERGEIST = 809, MV_DESTINY_BOND = 194;
constexpr int32_t ITM_POWER_HERB = 271;

// SideCondition screen ids
constexpr int32_t SC_REFLECT_ID = 1, SC_LIGHT_SCREEN_ID = 2, SC_AURORA_VEIL_ID = 3;

// FormatEnum
constexpr int32_t FORMAT_DOUBLES = 1;

// MoveCategory
constexpr int32_t CAT_PHYSICAL = 0, CAT_STATUS = 2;
// MoveTarget
constexpr int32_t TGT_ALL_ADJACENT_FOES = 2, TGT_ALL_ADJACENT = 3;
// ActionKind
constexpr int32_t AK_SWITCH = 1;

const int32_t HJK_MOVES[] = {MV_HIGH_JUMP_KICK, MV_JUMP_KICK, MV_SUPERCELL_SLAM};
const int32_t OHKO_MOVES[] = {MV_GUILLOTINE, MV_HORN_DRILL, MV_FISSURE, MV_SHEER_COLD};

const double ACC_STAGE_MULT[13] = {
    3.0/9, 3.0/8, 3.0/7, 3.0/6, 3.0/5, 3.0/4, 1.0, 4.0/3, 5.0/3, 2.0/1, 7.0/3, 8.0/3, 3.0/1
};

bool in_list(int32_t v, const int32_t* arr, int n) {
    for (int i = 0; i < n; ++i) if (arr[i] == v) return true;
    return false;
}
bool is_hjk(int32_t m) { return in_list(m, HJK_MOVES, 3); }
bool is_ohko(int32_t m) { return in_list(m, OHKO_MOVES, 4); }
bool is_mold_breaker(int32_t a) { return eff_internal::is_mold_breaker(a); }

// _TWO_TURN_MOVES membership (src/data/moves.py). Includes weather-skip + semi-invuln + charge moves.
constexpr int32_t MV_RAZOR_WIND = 13, MV_SKULL_BASH = 130, MV_SKY_ATTACK = 143;
// TWO_TURN_MOVES (src/data/moves.py): exactly these 11 moves.
bool is_two_turn(int32_t m) {
    switch (m) {
        case MV_SOLAR_BEAM: case MV_SOLAR_BLADE: case MV_BOUNCE: case MV_DIVE: case MV_FLY:
        case MV_PHANTOM_FORCE: case MV_METEOR_BEAM: case MV_SKULL_BASH: case MV_DIG:
        case MV_SKY_ATTACK: case MV_RAZOR_WIND:
            return true;
        default: return false;
    }
}
bool is_weather_skip_charge(int32_t m) { return m == MV_SOLAR_BEAM || m == MV_SOLAR_BLADE; }
bool is_semi_invuln_move(int32_t m) {
    return m == MV_BOUNCE || m == MV_FLY || m == MV_DIVE || m == MV_DIG || m == MV_PHANTOM_FORCE;
}
bool is_protect_bypass(int32_t m) {
    return m == MV_FEINT || m == MV_HYPERSPACE_FURY || m == MV_HYPERSPACE_HOLE
        || m == MV_PHANTOM_FORCE || m == MV_PLAY_NICE;
}

// _GEM_ITEMS: Normal Gem (564) -> NORMAL; typed gems 4001..4017 -> (item-4000), EXCEPT Grass
// (4003) and Electric (4004) which are transposed vs the Type enum (ELECTRIC=3, GRASS=4).
int32_t gem_type_of(int32_t item) {
    if (item == ITM_NORMAL_GEM) return TYPE_NORMAL;
    if (item == 4003) return TYPE_GRASS;        // Grass Gem
    if (item == 4004) return TYPE_ELECTRIC;     // Electric Gem
    if (item >= 4001 && item <= 4017) return item - 4000;
    return -1;
}

// _ATE_ABILITIES: ability -> converted type (only when move_type == NORMAL).
// PIXILATE 182->FAIRY(17), REFRIGERATE 174->ICE, AERILATE 184->FLYING(9), GALVANIZE 206->ELECTRIC.
int32_t ate_type_of(int32_t ability) {
    switch (ability) {
        case 182: return 17;            // PIXILATE -> FAIRY
        case 174: return TYPE_ICE;      // REFRIGERATE -> ICE
        case 184: return TYPE_FLYING;   // AERILATE -> FLYING
        case 206: return TYPE_ELECTRIC; // GALVANIZE -> ELECTRIC
        default:  return -1;
    }
}

// _IGNORE_ABILITY_MOVES (Moongeist/Sunsteel/Photon Geyser): bypass Wonder Guard.
bool is_ignore_ability_move(int32_t m) { return m == 713 || m == 714 || m == 722; }

// stat_stages accessors by index 0..6.
int32_t get_stage(const PokemonState& m, int i) {
    switch (i) {
        case 0: return m.stage0; case 1: return m.stage1; case 2: return m.stage2;
        case 3: return m.stage3; case 4: return m.stage4; case 5: return m.stage5;
        default: return m.stage6;
    }
}
int32_t move_id_at(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_id0; case 1: return m.move_id1;
        case 2: return m.move_id2; case 3: return m.move_id3;
        default: return 0;
    }
}
int32_t move_pp_at(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_pp0; case 1: return m.move_pp1;
        case 2: return m.move_pp2; case 3: return m.move_pp3;
        default: return 0;
    }
}

bool has_type(const PokemonState& m, int32_t t) {
    return eff_internal::has_type(m, t);
}
bool has_pseudo_gravity(const BattleState& s) {
    return eff_internal::has_pseudo(s, PW_GRAVITY);
}
bool either_no_guard(const PokemonState& a, const PokemonState& d) {
    return a.ability == AB_NO_GUARD || d.ability == AB_NO_GUARD;
}
bool has_semi_invuln_ve(const PokemonState& m) {
    return eff_internal::has_timed_volatile(m, VE_SEMI_INVULNERABLE);
}
bool has_throat_chop(const PokemonState& m) {
    return eff_internal::has_timed_volatile(m, VE_THROAT_CHOPPED);
}


// ---------------------------------------------------------------------------
// semi_invuln_interaction (src/data/moves.py): returns hits_through for the charge state.
// ---------------------------------------------------------------------------
bool semi_invuln_hits_through(int32_t charging_move, int32_t attacking_move) {
    // Airborne (Fly/Bounce/Sky Drop)
    if (charging_move == MV_FLY || charging_move == MV_BOUNCE || charging_move == MV_SKY_DROP) {
        switch (attacking_move) {
            case MV_GUST: case MV_TWISTER: case MV_THUNDER: case MV_HURRICANE:
            case MV_SKY_UPPERCUT: case MV_SMACK_DOWN: case MV_THOUSAND_ARROWS:
                return true;
            default: return false;
        }
    }
    // Underground (Dig)
    if (charging_move == MV_DIG) {
        return attacking_move == MV_EARTHQUAKE || attacking_move == MV_MAGNITUDE
            || attacking_move == MV_FISSURE;
    }
    // Underwater (Dive)
    if (charging_move == MV_DIVE) {
        return attacking_move == MV_SURF || attacking_move == MV_WHIRLPOOL;
    }
    return false;
}

// ---------------------------------------------------------------------------
// _apply_accuracy_modifiers (No Guard, Compound Eyes, Gravity, acc/eva stages).
// acc carries (value, is_none). Returns updated value; sets is_none.
// ---------------------------------------------------------------------------
void apply_accuracy_modifiers(double& acc, bool& is_none, const PokemonState& attacker,
                              const PokemonState& defender, const BattleState& state,
                              bool apply_stat_stages) {
    if (attacker.ability == AB_NO_GUARD || defender.ability == AB_NO_GUARD) { is_none = true; return; }
    if (is_none) return;
    if (attacker.ability == AB_COMPOUND_EYES) acc = std::min(acc * 1.3, 100.0);
    if (has_pseudo_gravity(state)) acc = std::min(acc * 5.0 / 3.0, 100.0);
    if (apply_stat_stages) {
        int32_t def_eva = get_stage(defender, 6);
        if (attacker.ability == AB_KEEN_EYE) def_eva = std::min(0, def_eva);
        if (attacker.ability == AB_UNAWARE) def_eva = 0;
        int32_t atk_acc = get_stage(attacker, 5);
        if (defender.ability == AB_UNAWARE && !is_mold_breaker(attacker.ability)) atk_acc = 0;
        int combined = std::max(-6, std::min(6, atk_acc - def_eva));
        acc = acc * ACC_STAGE_MULT[combined + 6];
    }
}

// _apply_item_ability_accuracy_modifiers (Bright Powder, Wide Lens, Tangled Feet, Sand/Snow, Victory Star).
void apply_item_ability_accuracy_modifiers(double& acc, bool& is_none, const PokemonState& attacker,
                                           const PokemonState& defender, const BattleState& state) {
    if (is_none) return;
    if (defender.item == ITM_BRIGHT_POWDER) acc *= 0.9;
    if (attacker.item == ITM_WIDE_LENS) acc = std::min(acc * 1.1, 100.0);
    if (defender.ability == AB_TANGLED_FEET && (defender.volatiles & VOLATILE_CONFUSED)
            && !is_mold_breaker(attacker.ability)) acc *= 0.5;
    if (defender.ability == AB_SAND_VEIL && state.weather == WEATHER_SANDSTORM
            && !is_mold_breaker(attacker.ability)) acc *= 0.8;
    if (defender.ability == AB_SNOW_CLOAK && state.weather == WEATHER_HAIL
            && !is_mold_breaker(attacker.ability)) acc *= 0.8;
    if (attacker.ability == AB_VICTORY_STAR) acc = std::min(acc * 1.1, 100.0);
}

// _compute_effective_accuracy: returns (value, is_none).
void compute_effective_accuracy(double& acc, bool& is_none, const PokemonState& attacker,
                                int32_t move, const MoveData& md, const BattleState& state,
                                BattleState& mut_state, int side_idx, int defender_idx) {
    const PokemonState& defender = active_mon(mut_state, defender_idx);
    // md.accuracy: -1 = always hits (None).
    is_none = (md.accuracy < 0);
    acc = is_none ? 0.0 : (double)md.accuracy;

    if (move == MV_SHEER_COLD) {
        is_none = false;
        acc = std::max(1.0, (double)(attacker.level - defender.level + 30));
    }
    if (attacker.ability == AB_HUSTLE && md.category == CAT_PHYSICAL && md.accuracy >= 0) {
        acc = md.accuracy * 0.8;
        is_none = false;
    }
    apply_accuracy_modifiers(acc, is_none, attacker, active_mon(mut_state, defender_idx),
                             state, /*apply_stat_stages*/true);
    apply_item_ability_accuracy_modifiers(acc, is_none, attacker,
                                          active_mon(mut_state, defender_idx), state);

    // Weather accuracy overrides.
    if (move == MV_HURRICANE) {
        if (state.weather == WEATHER_RAINY || state.weather == WEATHER_HEAVY_RAIN) is_none = true;
        else if (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN) {
            is_none = false; acc = 50.0;
        }
    } else if (move == MV_THUNDER) {
        if (state.weather == WEATHER_RAINY || state.weather == WEATHER_HEAVY_RAIN) is_none = true;
        else if (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN) {
            is_none = false; acc = 50.0;
        }
    } else if (move == MV_BLIZZARD) {
        if (state.weather == WEATHER_HAIL) is_none = true;
    }
}

// _apply_protect_contact_penalty (King's Shield -1 Atk, Spiky Shield 1/8, Baneful Bunker poison, Obstruct -2 Def).
void apply_protect_contact_penalty(BattleState& state, int attacker_idx, int defender_idx,
                                   int32_t move, const MoveData& md, const ExecCtx& ctx) {
    PokemonState& attacker = active_mon(state, attacker_idx);
    if (!(md.tags & TAG_CONTACT) || attacker.ability == AB_LONG_REACH) return;
    int32_t protect_move = ctx.protect_move[defender_idx];
    if (protect_move < 0) return;
    if (protect_move == MV_KINGS_SHIELD) {
        change_stat_stage(state, attacker_idx, 0, -1, false, false, false);
    } else if (protect_move == MV_SPIKY_SHIELD) {
        PokemonState& a = active_mon(state, attacker_idx);
        if (!a.fainted && a.ability != AB_MAGIC_GUARD) {
            int32_t dmg = std::max(1, a.max_hp / 8);
            int32_t new_hp = std::max(0, a.hp - dmg);
            a.hp = new_hp;
            // Mirror Python faint_active: release inflicted traps on self-KO.
            if (new_hp == 0) cpp_faint_active(state, attacker_idx, false, 0);
        }
    } else if (protect_move == MV_BANEFUL_BUNKER) {
        PokemonState& a = active_mon(state, attacker_idx);
        if (can_apply_status(a, STATUS_POISON, MV_NONE, AB_NONE, state)) {
            apply_status_to(state, attacker_idx, STATUS_POISON);
        }
    } else if (protect_move == MV_OBSTRUCT) {
        change_stat_stage(state, attacker_idx, 1, -2, false, false, false);
    }
}

} // namespace

// ---------------------------------------------------------------------------
// _check_type_immunity: STATEFUL absorption. Returns true (move absorbed/blocked) and mutates state.
// ---------------------------------------------------------------------------
bool check_type_immunity(BattleState& state, int attacker_side_idx, int32_t move_type, int32_t move) {
    PokemonState& attacker = active_mon(state, attacker_side_idx);
    if (is_mold_breaker(attacker.ability)) return false;

    int def_side_idx = 1 - attacker_side_idx;
    int32_t ability = active_mon(state, def_side_idx).ability;

    auto apply_heal = [&]() {
        PokemonState& cur = active_mon(state, def_side_idx);
        int32_t healed = std::min(cur.max_hp, cur.hp + cur.max_hp / 4);
        cur.hp = healed;
    };
    auto apply_boost = [&](int stat_idx) {
        change_stat_stage(state, def_side_idx, stat_idx, +1, /*caused_by_opp*/false,
                          /*ignore_simple*/false, /*mold_breaker*/false);
    };

    // _ABSORB_TABLE rows (trigger_type, abilities, effect).
    if (move_type == eff::TYPE_FIRE && ability == eff::AB_FLASH_FIRE) {
        PokemonState& h = active_mon(state, def_side_idx);
        h.volatiles |= VOLATILE_FLASH_FIRE;
        return true;
    }
    if (move_type == eff::TYPE_ELECTRIC && ability == AB_VOLT_ABSORB) { apply_heal(); return true; }
    if (move_type == eff::TYPE_ELECTRIC && ability == AB_MOTOR_DRIVE) { apply_boost(4); return true; }
    if (move_type == eff::TYPE_ELECTRIC && ability == AB_LIGHTNING_ROD) { apply_boost(2); return true; }
    if (move_type == eff::TYPE_WATER && (ability == AB_WATER_ABSORB || ability == AB_DRY_SKIN)) {
        apply_heal(); return true;
    }
    if (move_type == eff::TYPE_WATER && ability == AB_STORM_DRAIN) { apply_boost(2); return true; }
    if (move_type == eff::TYPE_GRASS && ability == eff::AB_SAP_SIPPER) { apply_boost(0); return true; }
    if (move_type == eff::TYPE_GROUND && ability == AB_EARTH_EATER) { apply_heal(); return true; }

    PokemonState& defender = active_mon(state, def_side_idx);
    if (ability == eff::AB_LEVITATE && move_type == eff::TYPE_GROUND) {
        if (move == MV_THOUSAND_ARROWS) return false;
        if (has_pseudo_gravity(state)) return false;
        if (defender.item == ITEM_IRON_BALL) return false;
        return true;
    }
    if (defender.item == ITEM_AIR_BALLOON && move_type == eff::TYPE_GROUND) {
        if (has_pseudo_gravity(state)) return false;
        return true;
    }
    return false;
}

// ===========================================================================
// _handle_pre_damage_checks
// ===========================================================================
bool cpp_pre_damage_checks(BattleState& state, int side_idx, int defender_idx,
                           int32_t move, const GuardLuck& luck, const ExecCtx& ctx,
                           int effective_slot) {
    const MoveData& md = move_data_get_or_throw(move);
    int32_t eff_slot = (effective_slot >= 0) ? effective_slot : ctx.opp_action_move_slot;
    // Python defaults eff_slot to action.move_slot; the probe always supplies effective_slot >= 0
    // for two-turn paths. ctx.opp_action_move_slot is the defender's slot, not the attacker's, so
    // it is only reached when effective_slot < 0 AND the move is not two-turn (never indexed).

    // Two-turn moves.
    if (is_two_turn(move)) {
        PokemonState& attacker = active_mon(state, side_idx);
        bool is_charging = (attacker.charging_move_slot == eff_slot && eff_slot >= 0);
        if (is_charging) {
            // SEMI_INVULNERABLE_EXIT fires before the release damage resolves, and only
            // when the mon actually was semi-invulnerable (Fly/Dig/Dive/... — not a plain
            // charge move like Skull Bash). Emit before the volatile is cleared below.
            if (is_semi_invuln_move(move) || has_semi_invuln_ve(attacker)) {
                rich_log_semi_invuln_exit(state.turn_number, attacker.species, move);
            }
            attacker.charging_move_slot = -1;
            auto& tv = attacker.timed_volatiles;
            // In-place filter (InlineVec has no erase-range API).
            std::size_t w = 0;
            for (std::size_t r = 0; r < tv.size(); ++r) {
                const auto& e = tv[r];
                if (e.effect != VE_SEMI_INVULNERABLE && e.effect != VE_CHARGING_MOVE)
                    tv[w++] = e;
            }
            while (tv.size() > w) tv.pop_back();
            // Fall through to deal damage.
        } else {
            bool skip_charge = false;
            if (is_weather_skip_charge(move)
                    && (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN)) {
                skip_charge = true;
            } else if (attacker.item == ITM_POWER_HERB) {
                attacker.item = ITEM_NONE;
                skip_charge = true;
            }
            if (!skip_charge) {
                PokemonState& a = active_mon(state, side_idx);
                // CHARGE_TURN fires for ALL two-turn charge moves on the charge turn;
                // SEMI_INVULNERABLE_ENTER only when the move is semi-invulnerable.
                rich_log_charge_turn(state.turn_number, a.species, move);
                if (is_semi_invuln_move(move)) {
                    rich_log_semi_invuln_enter(state.turn_number, a.species, move);
                    a.timed_volatiles.push_back(TimedVolatile{VE_SEMI_INVULNERABLE, -1});
                }
                // Called two-turn move (Metronome/Copycat/Mirror Move): the slot holds the
                // CALLER; store the charged move id — release dispatch reads it back.
                if (eff_slot >= 0 && move_id_at(a, eff_slot) != move) {
                    a.timed_volatiles.push_back(TimedVolatile{VE_CHARGING_MOVE, move});
                }
                a.charging_move_slot = eff_slot;
                if (move == MV_METEOR_BEAM) {
                    change_stat_stage(state, side_idx, 2, +1, false, false, false);
                }
                return false;
            }
        }
    }

    // Future Sight / Doom Desire.
    if (move == MV_FUTURE_SIGHT || move == MV_DOOM_DESIRE) {
        PokemonState& attacker = active_mon(state, side_idx);
        // calculate_damage uses default crit/damage_roll (LuckProfile defaults).
        LuckProfileC fs_luck;
        fs_luck.crit_threshold = 50.0;
        fs_luck.damage_roll = 0.5;
        fs_luck.proc_threshold = luck.proc_threshold;
        fs_luck.random_mode = luck.random_mode;
        fs_luck.rng = luck.rng;
        // Pre-schedule damage preview: mirrors Python core.py:1557, which draws (and in
        // random mode records) CRIT + DAMAGE_ROLL at schedule time — resolve crit internally.
        int32_t dmg = cpp_calculate_damage(attacker, move, active_mon(state, defender_idx),
                                           state, fs_luck, fs_luck, 0, -1, false, -1, false);
        int32_t target_slot_pos = 0;  // action.target_slot defaults to 0 in the probe.
        SideState& def_side = side_at(state, defender_idx);
        def_side.has_future_sight_pending = true;
        def_side.fs_turns = 3;
        def_side.fs_damage = dmg;
        def_side.fs_move = move;
        def_side.fs_target_slot = target_slot_pos;
        return false;
    }

    // Imprison.
    SideState& def_side = side_at(state, defender_idx);
    if (!def_side.imprisoned_moves.empty()
            && in_list(move, def_side.imprisoned_moves.data(), (int)def_side.imprisoned_moves.size())) {
        PokemonState& a = active_mon(state, side_idx);
        a.last_move_failed = true;
        return false;
    }

    // Fake Out / First Impression.
    {
        PokemonState& a = active_mon(state, side_idx);
        if ((move == MV_FAKE_OUT || move == MV_FIRST_IMPRESSION) && a.turns_in_battle > 0) {
            a.last_move_failed = true;
            return false;
        }
        // Belch.
        if (move == MV_BELCH && a.consumed_berry == ITEM_NONE) {
            a.last_move_failed = true;
            return false;
        }
    }

    // Poltergeist.
    if (move == MV_POLTERGEIST && active_mon(state, defender_idx).item == ITEM_NONE) {
        PokemonState& a = active_mon(state, side_idx);
        a.last_move_failed = true;
        return false;
    }

    // Destiny Bond clear.
    {
        PokemonState& a = active_mon(state, side_idx);
        if ((a.volatiles & VOLATILE_DESTINY_BOND) && move != MV_DESTINY_BOND) {
            a.volatiles &= ~VOLATILE_DESTINY_BOND;
        }
    }

    // Throat Chop block.
    {
        PokemonState& a = active_mon(state, side_idx);
        if (has_throat_chop(a) && (md.tags & TAG_SOUND)) {
            a.last_move_failed = true;
            return false;
        }
    }

    return true;
}

// ===========================================================================
// Phase 1: _pdg_move_specific_fail_guards
// ===========================================================================
namespace {
bool pdg_move_specific_fail_guards(BattleState& state, int side_idx, int defender_idx,
                                   int32_t move, const MoveData& md, const ExecCtx& ctx,
                                   bool& abort) {
    abort = false;
    PokemonState& attacker = active_mon(state, side_idx);

    // Damp blocks self-destruct moves.
    static const int32_t EXPLOSION_MOVES[] = {153, 120, 802, 720};  // Explosion/SelfDestruct/MistyExpl/MindBlown
    if (in_list(move, EXPLOSION_MOVES, 4) && !is_mold_breaker(attacker.ability)) {
        for (int s = 0; s < 2; ++s) {
            SideState& side = side_at(state, s);
            for (int32_t ai : side.active_indices) {
                if (side.team[ai].ability == AB_DAMP) { abort = true; return true; }
            }
        }
    }

    // Stance Change.
    if (attacker.ability == AB_STANCE_CHANGE && attacker.species == SP_AEGISLASH
            && md.category != CAT_STATUS) {
        apply_form_change(state, side_idx, SP_AEGISLASH_BLADE);
    }

    // Sucker Punch.
    if (move == MV_SUCKER_PUNCH && ctx.opp_action_kind >= 0) {
        bool sp_fails;
        if (!ctx.opp_action_present || ctx.opp_action_kind == AK_SWITCH) {
            sp_fails = true;
        } else if (ctx.opp_action_kind == 0
                   && (ctx.opp_action_move_slot >= 0 || ctx.opp_action_move_override >= 0)) {
            int32_t opp_move;
            if (ctx.opp_action_move_override >= 0) {
                opp_move = ctx.opp_action_move_override;
            } else {
                SideState& ds = side_at(state, defender_idx);
                const PokemonState& om = ds.team[ds.active_indices[0]];
                opp_move = move_id_at(om, ctx.opp_action_move_slot);
            }
            const MoveData* omd = move_data_get(opp_move);
            sp_fails = (omd == nullptr
                        || (omd->category == CAT_STATUS && opp_move != MV_ME_FIRST));
        } else {
            sp_fails = true;
        }
        PokemonState& a = active_mon(state, side_idx);
        if (sp_fails) {
            a.last_move_failed = true;
            a.sucker_punch_last_turn = true;
            abort = true;
            return true;
        }
        a.sucker_punch_last_turn = true;
    }

    // Focus Punch.
    {
        PokemonState& a = active_mon(state, side_idx);
        if (move == MV_FOCUS_PUNCH && a.took_damage_this_turn) {
            a.last_move_failed = true; abort = true; return true;
        }
        // Hyperspace Fury.
        if (move == MV_HYPERSPACE_FURY && a.species != SP_HOOPA_UNBOUND) {
            a.last_move_failed = true; abort = true; return true;
        }
    }

    // Steel Roller.
    if (move == MV_STEEL_ROLLER && state.terrain == TERRAIN_NONE) {
        active_mon(state, side_idx).last_move_failed = true; abort = true; return true;
    }

    // Dream Eater.
    if (move == MV_DREAM_EATER) {
        const PokemonState& d = active_mon(state, defender_idx);
        bool dreaming = (d.status == STATUS_SLEEP || d.ability == AB_COMATOSE);
        if (!dreaming) {
            active_mon(state, side_idx).last_move_failed = true; abort = true; return true;
        }
    }

    // Burn Up.
    if (move == MV_BURN_UP && !has_type(active_mon(state, side_idx), TYPE_FIRE)) {
        active_mon(state, side_idx).last_move_failed = true; abort = true; return true;
    }

    // Last Resort.
    if (move == MV_LAST_RESORT) {
        PokemonState& a = active_mon(state, side_idx);
        bool has_unused = false;
        for (int slot = 0; slot < 4; ++slot) {
            int32_t mv = move_id_at(a, slot);
            if (mv == MV_NONE || mv == MV_LAST_RESORT) continue;
            if (!(a.moves_used & (1 << slot))) { has_unused = true; break; }
        }
        if (has_unused) { a.last_move_failed = true; abort = true; return true; }
    }

    // Spit Up.
    if (move == MV_SPIT_UP && active_mon(state, side_idx).stockpile_count == 0) {
        active_mon(state, side_idx).last_move_failed = true; abort = true; return true;
    }

    // Brick Break / Psychic Fangs: strip screens.
    if (move == MV_BRICK_BREAK || move == MV_PSYCHIC_FANGS) {
        SideState& ds = side_at(state, defender_idx);
        auto& sc = ds.side_conditions;
        // In-place filter (InlineVec has no erase-range API).
        std::size_t w = 0;
        for (std::size_t r = 0; r < sc.size(); ++r) {
            const auto& e = sc[r];
            if (e.condition != SC_REFLECT_ID && e.condition != SC_LIGHT_SCREEN_ID
                    && e.condition != SC_AURORA_VEIL_ID)
                sc[w++] = e;
        }
        while (sc.size() > w) sc.pop_back();
    }

    // Sheer Cold: Ice immunity.
    if (move == MV_SHEER_COLD) {
        if (has_type(active_mon(state, defender_idx), TYPE_ICE)) { abort = true; return true; }
    }

    return false;  // no abort decision triggered (proceed)
}

// ===========================================================================
// Phase 2: _pdg_accuracy_and_miss. Returns true if aborted. Sets eff_acc/eff_acc_is_none.
// ===========================================================================
bool pdg_accuracy_and_miss(BattleState& state, int side_idx, int defender_idx, int32_t move,
                           const MoveData& md, const BattleState& ro_state, const GuardLuck& luck_atk,
                           double& eff_acc, bool& eff_acc_is_none) {
    const PokemonState& attacker = active_mon(state, side_idx);
    compute_effective_accuracy(eff_acc, eff_acc_is_none, attacker, move, md, ro_state,
                               state, side_idx, defender_idx);

    const RngLogCtx catb_ctx{
        RngParticipants{
            (int8_t)side_idx,     (int8_t)side_at(state, side_idx).active_indices[0],
            (int8_t)defender_idx, (int8_t)side_at(state, defender_idx).active_indices[0]},
        state.turn_number};
    if (rng_resolve_accuracy(eff_acc, eff_acc_is_none, luck_atk.accuracy_threshold,
                             luck_atk.random_mode, luck_atk.rng, &catb_ctx))
        return false;

    // Miss consequences.
    active_mon(state, side_idx).last_move_failed = true;

    // HJK / Jump Kick / Supercell Slam crash. Mirrors Python core.py: on self-KO,
    // route through cpp_faint_active so inflicted traps are released (faint_active).
    {
        PokemonState& a = active_mon(state, side_idx);
        if (is_hjk(move) && !a.fainted && a.ability != AB_MAGIC_GUARD) {
            int32_t crash = std::max(1, a.max_hp / 2);
            int32_t new_hp = std::max(0, a.hp - crash);
            a.hp = new_hp;
            if (new_hp == 0) cpp_faint_active(state, side_idx, false, 0);
        }
    }
    // Steel Beam.
    {
        PokemonState& a = active_mon(state, side_idx);
        if (move == MV_STEEL_BEAM && !a.fainted && a.ability != AB_MAGIC_GUARD) {
            int32_t sb = std::max(1, a.max_hp / 2);
            int32_t new_hp = std::max(0, a.hp - sb);
            a.hp = new_hp;
            if (new_hp == 0) cpp_faint_active(state, side_idx, false, 0);
        }
    }
    // Gem consume.
    {
        PokemonState& a = active_mon(state, side_idx);
        int32_t gt = gem_type_of(a.item);
        if (gt >= 0) {
            int32_t move_type_miss = move_data_get_or_throw(move).move_type;
            if (gt == move_type_miss) a.item = ITEM_NONE;
        }
    }
    // Blunder Policy.
    {
        PokemonState& a = active_mon(state, side_idx);
        if (a.item == ITM_BLUNDER_POLICY && !is_ohko(move)) {
            a.item = ITEM_NONE;
            change_stat_stage(state, side_idx, 4, +2, false, false, false);
        }
    }
    // Metronome item.
    if (md.category != CAT_STATUS) {
        PokemonState& a = active_mon(state, side_idx);
        if (a.item == ITM_METRONOME) { a.metronome_count = 0; a.metronome_last_move = -1; }
    }
    // Rollout / Ice Ball.
    if (move == MV_ROLLOUT || move == MV_ICE_BALL) {
        PokemonState& a = active_mon(state, side_idx);
        if (a.rollout_hits > 0) a.rollout_hits = 0;
    }
    // Spit Up.
    if (move == MV_SPIT_UP) cpp_reset_stockpile(state, side_idx);

    return true;
}

// ===========================================================================
// Phase 3: _pdg_priority_and_protection_guards. Returns true if aborted.
// ===========================================================================
bool pdg_priority_and_protection_guards(BattleState& state, int side_idx, int defender_idx,
                                        int32_t move, const MoveData& md, ExecCtx& ctx) {
    PokemonState& attacker = active_mon(state, side_idx);

    // Semi-invulnerability miss.
    {
        const PokemonState& def_si = active_mon(state, defender_idx);
        if (has_semi_invuln_ve(def_si) && !either_no_guard(attacker, def_si)) {
            // VE_CHARGING_MOVE wins (called two-turn: slot holds the caller).
            int32_t charging_move = (def_si.charging_move_slot >= 0)
                ? move_id_at(def_si, def_si.charging_move_slot) : MV_NONE;
            for (const TimedVolatile& tv : def_si.timed_volatiles) {
                if (tv.effect == VE_CHARGING_MOVE) { charging_move = tv.turns; break; }
            }
            if (!semi_invuln_hits_through(charging_move, move)) {
                active_mon(state, side_idx).last_move_failed = true;
                return true;
            }
        }
    }

    int32_t eff_priority = md.priority + triage_priority_bump(attacker.ability, md);

    // Psychic Terrain.
    if (eff_priority > 0 && state.terrain == TERRAIN_PSYCHIC
            && eff_internal::is_grounded(active_mon(state, defender_idx), state)) {
        return true;
    }

    // Dazzling / Queenly Majesty / Armor Tail.
    if (eff_priority > 0 && !is_mold_breaker(attacker.ability)) {
        SideState& ds = side_at(state, defender_idx);
        for (int32_t ai : ds.active_indices) {
            int32_t ab = ds.team[ai].ability;
            if (ab == AB_DAZZLING || ab == AB_QUEENLY_MAJESTY || ab == AB_ARMOR_TAIL) return true;
        }
    }

    // Doubles redirect: Lightning Rod / Storm Drain.
    if (state.format == FORMAT_DOUBLES) {
        SideState& ds = side_at(state, defender_idx);
        int32_t current_defender_ai = ds.active_indices[0];
        for (size_t slot_pos = 0; slot_pos < ds.active_indices.size(); ++slot_pos) {
            int32_t other_ai = ds.active_indices[slot_pos];
            if (other_ai == current_defender_ai) continue;
            const PokemonState& other = ds.team[other_ai];
            bool redirects = false;
            if (other.ability == AB_LIGHTNING_ROD && md.move_type == TYPE_ELECTRIC
                    && !is_mold_breaker(attacker.ability)) redirects = true;
            else if (other.ability == AB_STORM_DRAIN && md.move_type == TYPE_WATER
                     && !is_mold_breaker(attacker.ability)) redirects = true;
            if (redirects) {
                // _active_slot_swapped: temporarily make active_indices[0] the redirector, then
                // boost its SpA. change_stat_stage / active_mon read active_indices[0].
                std::swap(ds.active_indices[0], ds.active_indices[slot_pos]);
                change_stat_stage(state, defender_idx, 2, +1, false, false, false);
                std::swap(ds.active_indices[0], ds.active_indices[slot_pos]);
                return true;
            }
        }
    }

    // Protect.
    if (ctx.protected_sides[defender_idx]) {
        if (!is_protect_bypass(move)) {
            bool unseen_fist_bypass = (attacker.ability == AB_UNSEEN_FIST
                                       && (md.tags & TAG_CONTACT));
            apply_protect_contact_penalty(state, side_idx, defender_idx, move, md, ctx);
            if (!unseen_fist_bypass) return true;
        } else {
            if (move == MV_FEINT) {
                ctx.protected_sides[defender_idx] = false;
            }
        }
    }

    // Wide Guard.
    if (ctx.wide_guard_sides[defender_idx]
            && (md.target == TGT_ALL_ADJACENT_FOES || md.target == TGT_ALL_ADJACENT)) {
        return true;
    }

    // Quick Guard.
    if (ctx.quick_guard_sides[defender_idx]) {
        int32_t qg = md.priority + triage_priority_bump(active_mon(state, side_idx).ability, md);
        if (qg > 0) return true;
    }

    return false;
}

// ===========================================================================
// Phase 4: _pdg_ability_item_immunity_guards. Returns true if aborted.
// ===========================================================================
bool pdg_ability_item_immunity_guards(BattleState& state, int side_idx, int defender_idx,
                                      int32_t move, const MoveData& md) {
    const PokemonState& attacker = active_mon(state, side_idx);
    PokemonState& defender = active_mon(state, defender_idx);

    if ((md.tags & TAG_SOUND) && !is_mold_breaker(attacker.ability)
            && defender.ability == AB_SOUNDPROOF) return true;
    if ((md.tags & TAG_BULLET) && !is_mold_breaker(attacker.ability)
            && defender.ability == AB_BULLETPROOF) return true;
    if ((md.tags & TAG_POWDER) && defender.item == ITM_SAFETY_GOGGLES) return true;
    if ((md.tags & TAG_POWDER) && defender.ability == AB_OVERCOAT
            && !is_mold_breaker(attacker.ability)) return true;

    if (defender.ability == AB_ICE_FACE && defender.species == SP_EISCUE
            && md.category == CAT_PHYSICAL && !is_mold_breaker(attacker.ability)) {
        apply_form_change(state, defender_idx, SP_EISCUE_NOICE);
        return true;
    }
    return false;
}

// ===========================================================================
// Phase 5: _pdg_resolve_move_type. Returns true if aborted. Sets move_type.
// ===========================================================================
bool pdg_resolve_move_type(BattleState& state, int side_idx, int defender_idx, int32_t move,
                           const MoveData& md, int32_t& move_type) {
    PokemonState& attacker = active_mon(state, side_idx);
    move_type = md.move_type;

    if (move == MV_HIDDEN_POWER) move_type = hidden_power_type(attacker);
    // Natural Gift: type is determined by the held berry (mirrors Python core.py:2258-2259).
    // Must resolve before the type immunity check below or immune matchups abort with the wrong type.
    if (move == MV_NATURAL_GIFT) {
        int32_t ng_type = cpp_natural_gift_type(attacker.item);
        if (ng_type >= 0) move_type = ng_type;
        // If no berry (ng_type == -1), move_type stays NORMAL; the move will fail in the damage loop.
    }
    if (move == MV_MULTI_ATTACK && attacker.has_types && !attacker.types.empty())
        move_type = attacker.types[0];
    if (attacker.ability == AB_LIQUID_VOICE && (md.tags & TAG_SOUND)) move_type = TYPE_WATER;

    if (attacker.ability == AB_NORMALIZE) {
        move_type = TYPE_NORMAL;
    } else {
        int32_t ate = ate_type_of(attacker.ability);
        if (ate >= 0 && move_type == TYPE_NORMAL) move_type = ate;
    }

    if (move == MV_WEATHER_BALL && state.weather != WEATHER_NONE) {
        if (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN) move_type = TYPE_FIRE;
        else if (state.weather == WEATHER_RAINY || state.weather == WEATHER_HEAVY_RAIN) move_type = TYPE_WATER;
        else if (state.weather == WEATHER_SANDSTORM) move_type = TYPE_ROCK;
        else if (state.weather == WEATHER_HAIL) move_type = TYPE_ICE;
    }

    if (state.weather == WEATHER_HEAVY_RAIN && move_type == TYPE_FIRE) return true;
    if (state.weather == WEATHER_HARSH_SUN && move_type == TYPE_WATER) return true;

    if (check_type_immunity(state, side_idx, move_type, move)) return true;

    PokemonState& defender = active_mon(state, defender_idx);
    if (defender.ability == AB_WONDER_GUARD) {
        if (!is_mold_breaker(attacker.ability) && !is_ignore_ability_move(move)) {
            double eff = 1.0;
            if (defender.has_types)
                for (int32_t t : defender.types) eff *= cpp_type_effectiveness(move_type, t);
            if (eff > 0.0 && eff <= 1.0) return true;
        }
    }

    PokemonState& atk2 = active_mon(state, side_idx);
    if (atk2.ability == AB_PROTEAN || atk2.ability == AB_LIBERO) {
        if (!(atk2.volatiles & VOLATILE_PROTEAN_USED)) {
            atk2.has_types = true;
            atk2.types.assign(1, move_type);
            atk2.volatiles |= VOLATILE_PROTEAN_USED;
        }
    }
    return false;
}
} // namespace

// ===========================================================================
// _handle_pre_damage_guards (orchestrator)
// ===========================================================================
GuardResult cpp_pre_damage_guards(BattleState& state, int side_idx, int defender_idx,
                                  int32_t move, const GuardLuck& luck_atk,
                                  const GuardLuck& luck_def, ExecCtx& ctx) {
    (void)luck_def;  // Mirrors the Python signature; def-side luck is unused by the guard chain.
    GuardResult res;
    const MoveData& md = move_data_get_or_throw(move);

    bool abort = false;
    if (pdg_move_specific_fail_guards(state, side_idx, defender_idx, move, md, ctx, abort) || abort) {
        res.should_abort = true; return res;
    }

    double eff_acc = 0.0; bool eff_acc_is_none = true;
    if (pdg_accuracy_and_miss(state, side_idx, defender_idx, move, md, state, luck_atk,
                              eff_acc, eff_acc_is_none)) {
        res.should_abort = true; return res;
    }

    if (pdg_priority_and_protection_guards(state, side_idx, defender_idx, move, md, ctx)) {
        res.should_abort = true; return res;
    }

    if (pdg_ability_item_immunity_guards(state, side_idx, defender_idx, move, md)) {
        res.should_abort = true; return res;
    }

    int32_t move_type = -1;
    if (pdg_resolve_move_type(state, side_idx, defender_idx, move, md, move_type)) {
        res.should_abort = true; return res;
    }

    res.should_abort = false;
    res.move_type = move_type;
    res.effective_acc = eff_acc;
    res.effective_acc_is_none = eff_acc_is_none;
    return res;
}

// Exported thin wrapper so Unit 5's status path can reuse the contact-penalty body (the
// implementation lives in this TU's anonymous namespace).
void cpp_apply_protect_contact_penalty(BattleState& state, int attacker_idx, int defender_idx,
                                       int32_t move, const MoveData& md, const ExecCtx& ctx) {
    apply_protect_contact_penalty(state, attacker_idx, defender_idx, move, md, ctx);
}
