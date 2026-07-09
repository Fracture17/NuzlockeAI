// File-local constants and helpers shared between ai_scorer.cpp (public dispatcher +
// switch scoring) and ai_scorer_dist.cpp (dist_* score-distribution family).
// Not part of the public probe API. All identifiers keep their original names.
#pragma once
#ifndef NUZLOCKE_AI_SCORER_INTERNAL_H
#define NUZLOCKE_AI_SCORER_INTERNAL_H

#include "ai_scorer.h"       // cpp_ai_faster (used by should_recover); ScoreDistC
#include "ai_shared.h"
#include "ai_damage.h"
#include "damage.h"          // LuckProfileC, cpp_effective_stat, cpp_expected_damage
#include "core_leaf.h"       // cpp_effective_speed (indirect)
#include "state.h"
#include "type_chart_lookup.h"

#include "../generated/ai_move_sets.h"

#include <cstdint>
#include <initializer_list>
#include <utility>
#include <vector>

namespace ai_scorer {

// ---------------------------------------------------------------------------
// Move / item / ability / status / type / volatile / weather constants.
// Kept as inline constexpr (C++17 ODR-safe across TUs).
// ---------------------------------------------------------------------------

// Move IDs (scorer-specific)
inline constexpr int32_t MV_OVERHEAT          = 315;
inline constexpr int32_t MV_LEAF_STORM        = 437;
inline constexpr int32_t MV_SUPERPOWER        = 276;
inline constexpr int32_t MV_FAKE_OUT          = 252;
inline constexpr int32_t MV_FIRST_IMPRESSION  = 660;
inline constexpr int32_t MV_FELL_STINGER      = 565;
inline constexpr int32_t MV_ACID_SPRAY        = 491;
inline constexpr int32_t MV_GRASSY_GLIDE      = 803;
inline constexpr int32_t MV_SUCKER_PUNCH      = 389;
inline constexpr int32_t MV_PURSUIT           = 228;
inline constexpr int32_t MV_FLAME_CHARGE      = 488;
inline constexpr int32_t MV_SMACK_DOWN        = 479;
inline constexpr int32_t MV_THOUSAND_ARROWS   = 614;
inline constexpr int32_t MV_STEALTH_ROCK      = 446;
inline constexpr int32_t MV_SPIKES            = 191;
inline constexpr int32_t MV_TOXIC_SPIKES      = 390;
inline constexpr int32_t MV_STICKY_WEB        = 564;
inline constexpr int32_t MV_LIGHT_SCREEN      = 113;
inline constexpr int32_t MV_REFLECT           = 115;
inline constexpr int32_t MV_REST              = 156;
inline constexpr int32_t MV_SUBSTITUTE        = 164;
inline constexpr int32_t MV_BELLY_DRUM        = 187;
inline constexpr int32_t MV_SHELL_SMASH       = 504;
inline constexpr int32_t MV_FOCUS_ENERGY      = 116;
inline constexpr int32_t MV_LASER_FOCUS       = 673;
inline constexpr int32_t MV_NASTY_PLOT        = 417;
inline constexpr int32_t MV_TAIL_GLOW         = 294;
inline constexpr int32_t MV_WORK_UP           = 526;
inline constexpr int32_t MV_COACHING          = 811;
inline constexpr int32_t MV_TAILWIND          = 366;
inline constexpr int32_t MV_TRICK_ROOM        = 433;
inline constexpr int32_t MV_ROLE_PLAY         = 272;
inline constexpr int32_t MV_IMPRISON          = 286;
inline constexpr int32_t MV_SLEEP_TALK        = 214;
inline constexpr int32_t MV_LEECH_SEED        = 73;
inline constexpr int32_t MV_YAWN              = 281;
inline constexpr int32_t MV_SCARY_FACE        = 184;
inline constexpr int32_t MV_HELPING_HAND      = 270;
inline constexpr int32_t MV_FOLLOW_ME         = 266;
inline constexpr int32_t MV_TAUNT             = 269;
inline constexpr int32_t MV_BATON_PASS        = 226;
inline constexpr int32_t MV_MEMENTO           = 262;
inline constexpr int32_t MV_ENCORE            = 227;
inline constexpr int32_t MV_COUNTER           = 68;
inline constexpr int32_t MV_MIRROR_COAT       = 243;
inline constexpr int32_t MV_MAGNET_RISE       = 393;
inline constexpr int32_t MV_DEFOG             = 432;
inline constexpr int32_t MV_TROP_KICK         = 688;
inline constexpr int32_t MV_BREAKING_SWIPE    = 784;
inline constexpr int32_t MV_WILL_O_WISP       = 261;

// Item IDs (scorer-specific)
inline constexpr int32_t ITM_POWER_HERB       = 271;
inline constexpr int32_t ITM_LUM_BERRY        = 157;
inline constexpr int32_t ITM_CHESTO_BERRY     = 150;
inline constexpr int32_t ITM_SITRUS_BERRY     = 158;
inline constexpr int32_t ITM_FOCUS_SASH       = 275;
inline constexpr int32_t ITM_LIGHT_CLAY       = 269;
inline constexpr int32_t ITM_SCOPE_LENS       = 232;
inline constexpr int32_t ITM_SAFETY_GOGGLES   = 650;
inline constexpr int32_t ITM_TERRAIN_EXTENDER = 879;

// Ability IDs (scorer-specific)
inline constexpr int32_t AB_CONTRARY          = 126;
inline constexpr int32_t AB_EARLY_BIRD        = 48;
inline constexpr int32_t AB_SHED_SKIN         = 61;
inline constexpr int32_t AB_HYDRATION         = 93;
inline constexpr int32_t AB_STURDY            = 5;
inline constexpr int32_t AB_INFILTRATOR       = 151;
inline constexpr int32_t AB_LIMBER            = 7;
inline constexpr int32_t AB_CORROSION         = 212;
inline constexpr int32_t AB_INNER_FOCUS       = 39;
inline constexpr int32_t AB_SHIELD_DUST       = 19;
inline constexpr int32_t AB_SUPER_LUCK        = 105;
inline constexpr int32_t AB_SNIPER            = 97;
inline constexpr int32_t AB_CLEAR_BODY        = 29;
inline constexpr int32_t AB_WHITE_SMOKE       = 73;
inline constexpr int32_t AB_SHELL_ARMOR       = 75;
inline constexpr int32_t AB_BATTLE_ARMOR      = 4;
inline constexpr int32_t AB_INSOMNIA          = 15;
inline constexpr int32_t AB_VITAL_SPIRIT      = 72;
inline constexpr int32_t AB_OVERCOAT          = 142;
inline constexpr int32_t AB_UNAWARE           = 109;

// Status values
inline constexpr int32_t STATUS_SLEEP         = 6;
inline constexpr int32_t STATUS_FREEZE        = 2;
inline constexpr int32_t STATUS_BURN          = 1;
inline constexpr int32_t STATUS_PARALYSIS     = 3;
inline constexpr int32_t STATUS_NONE          = 0;

// Type values
inline constexpr int32_t TYPE_FIRE            = 1;
inline constexpr int32_t TYPE_ELECTRIC        = 3;
inline constexpr int32_t TYPE_GROUND          = 8;
inline constexpr int32_t TYPE_GRASS           = 4;
inline constexpr int32_t TYPE_GHOST           = 13;
inline constexpr int32_t TYPE_DARK            = 15;
inline constexpr int32_t TYPE_STEEL           = 16;
inline constexpr int32_t TYPE_POISON          = 7;
inline constexpr int32_t TYPE_FLYING          = 9;

// Volatile bitmask values
inline constexpr int32_t VOL_RECHARGING       = 256;
inline constexpr int32_t VOL_SUBSTITUTE       = 4096;
inline constexpr int32_t VOL_LEECH_SEEDED     = 2;
inline constexpr int32_t VOL_CURSED           = 4;
inline constexpr int32_t VOL_PERISH_SONG      = 16384;
inline constexpr int32_t VOL_ATTRACTED        = 8388608;
inline constexpr int32_t VOL_TAUNT_ACTIVE     = 16;
inline constexpr int32_t VOL_ENCORE_ACTIVE    = 8;

// VolatileEffect int values (for timed_volatiles)
inline constexpr int32_t VE_DROWSY            = 20;
inline constexpr int32_t VE_MAGNET_RISE       = 8;
inline constexpr int32_t VE_LASER_FOCUS       = 25;
inline constexpr int32_t VE_GROUNDED          = 24;

// SideCondition int values
inline constexpr int32_t SC_REFLECT           = 1;
inline constexpr int32_t SC_LIGHT_SCREEN      = 2;
inline constexpr int32_t SC_AURORA_VEIL       = 3;
inline constexpr int32_t SC_STEALTH_ROCK      = 4;
inline constexpr int32_t SC_SPIKES_1          = 5;
inline constexpr int32_t SC_SPIKES_2          = 6;
inline constexpr int32_t SC_SPIKES_3          = 7;
inline constexpr int32_t SC_TOXIC_SPIKES_1    = 8;
inline constexpr int32_t SC_TOXIC_SPIKES_2    = 9;
inline constexpr int32_t SC_STICKY_WEB        = 10;
inline constexpr int32_t SC_TAILWIND          = 11;

// PseudoWeather int values
inline constexpr int32_t PW_TRICK_ROOM        = 1;

// Weather int values
inline constexpr int32_t WE_SUNNY             = 1;
inline constexpr int32_t WE_HARSH_SUN         = 6;

// Terrain int values
inline constexpr int32_t TE_PSYCHIC           = 3;
inline constexpr int32_t TE_GRASSY            = 2;
inline constexpr int32_t TE_ELECTRIC          = 1;
inline constexpr int32_t TE_MISTY             = 4;

// FormatEnum
inline constexpr int32_t FMT_SINGLES          = 0;
inline constexpr int32_t FMT_DOUBLES          = 1;

// MoveTag bitmask values
inline constexpr int32_t TAG_RECOVERY         = 4;
inline constexpr int32_t TAG_HAZARD           = 32;
inline constexpr int32_t TAG_SCREEN           = 64;
inline constexpr int32_t TAG_POWDER           = 16384;
inline constexpr int32_t TAG_SETUP            = 2;
inline constexpr int32_t TAG_STATUS_BIT       = 8;

// MoveCategory values
inline constexpr int32_t CAT_PHYSICAL         = 0;
inline constexpr int32_t CAT_SPECIAL          = 1;
inline constexpr int32_t CAT_STATUS           = 2;

// MoveTarget values
inline constexpr int32_t TGT_SELF             = 1;

// Species IDs
inline constexpr int32_t SP_MELOETTA_PIROUETTE = 1107;

// ActionKind
inline constexpr int32_t AK_MOVE              = 0;
inline constexpr int32_t AK_SWITCH            = 1;

// ---------------------------------------------------------------------------
// AVERAGE_LUCK / MAX_LUCK profiles. inline const is C++17 ODR-safe.
// AVERAGE_LUCK differs from MAX_LUCK only in crit_threshold (50 vs 100).
// MAX_LUCK's multi_hit_roll=0.0 gives min hits (2) for 2-5 hit moves.
// ---------------------------------------------------------------------------
inline LuckProfileC make_average_luck() {
    LuckProfileC l;
    l.crit_threshold  = 50.0;
    l.damage_roll     = 1.0;
    l.proc_threshold  = 50.0;
    l.random_mode     = false;
    return l;
}
inline const LuckProfileC AVERAGE_LUCK_C = make_average_luck();

inline LuckProfileC make_max_damage_luck_scorer() {
    LuckProfileC l;
    l.crit_threshold  = 100.0;
    l.damage_roll     = 1.0;
    l.proc_threshold  = 101.0;
    l.random_mode     = false;
    l.multi_hit_roll  = 0.0;
    return l;
}
inline const LuckProfileC MAX_LUCK_C = make_max_damage_luck_scorer();

// ---------------------------------------------------------------------------
// Setup kind (shared between dist_setup and cpp_dist_action).
// ---------------------------------------------------------------------------
enum class SetupKind { OFFENSIVE, DEFENSIVE, SPEED };

// ---------------------------------------------------------------------------
// Stat access helpers.
// ---------------------------------------------------------------------------
inline int32_t mon_stage(const PokemonState& m, int idx) {
    switch (idx) {
        case 0: return m.stage0; case 1: return m.stage1; case 2: return m.stage2;
        case 3: return m.stage3; case 4: return m.stage4; case 5: return m.stage5;
        case 6: return m.stage6;
        default: return 0;
    }
}

// Raw stored stat (before stage). idx: 0=HP, 1=ATK, 2=DEF, 3=SPA, 4=SPD, 5=SPE.
inline int32_t mon_stat_raw(const PokemonState& m, int idx) {
    switch (idx) {
        case 0: return m.stat_hp; case 1: return m.stat_atk; case 2: return m.stat_def;
        case 3: return m.stat_spa; case 4: return m.stat_spd; case 5: return m.stat_spe;
        default: return 0;
    }
}

// ---------------------------------------------------------------------------
// Predicates (shared by dispatcher and dist_* helpers).
// ---------------------------------------------------------------------------
inline bool is_type_immune(const MoveData& md, const PokemonState& defender) {
    for (int32_t t : defender.types) {
        float eff = cpp_type_effectiveness((int32_t)md.move_type, t);
        if (eff == 0.0f && defender.item != ITM_RING_TARGET) return true;
    }
    return false;
}

inline bool is_incapacitated(const PokemonState& mon) {
    return (mon.status == STATUS_SLEEP || mon.status == STATUS_FREEZE
            || (mon.volatiles & VOL_RECHARGING));
}

inline bool has_protect_debuff(const PokemonState& mon) {
    if (mon.status == STATUS_POISON || mon.status == STATUS_TOXIC || mon.status == STATUS_BURN)
        return true;
    if (mon.volatiles & (VOL_CURSED | VOL_LEECH_SEEDED | VOL_PERISH_SONG | VOL_ATTRACTED))
        return true;
    for (const auto& tv : mon.timed_volatiles)
        if (tv.effect == VE_DROWSY) return true;
    return false;
}

// True if move_id is super-effective against pl_mon.
inline bool is_move_super_effective(int32_t move_id, const PokemonState& pl_mon) {
    const MoveData& md = ai_move_data_or_throw(move_id);
    float eff = 1.0f;
    for (int32_t t : pl_mon.types) {
        float f = cpp_type_effectiveness((int32_t)md.move_type, t);
        if (f == 0.0f && pl_mon.item == ITM_RING_TARGET) f = 1.0f;
        eff *= f;
    }
    return eff > 1.0f;
}

// True if pl_mon has at least one move of given category with PP>0.
inline bool player_has_split(const PokemonState& pl_mon, int32_t category) {
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        int32_t pp = move_pp_at(pl_mon, slot);
        if (pp == 0) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (md && (int32_t)md->category == category) return true;
    }
    return false;
}

inline bool player_can_ko_ai(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    if (ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp) return false;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        if (move_pp_at(pl_mon, slot) == 0) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md || md->base_power == 0) continue;
        if (cpp_ai_can_ko(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C, false)) return true;
    }
    return false;
}

// True if player can n-HKO AI's active mon using AVERAGE_LUCK.
inline bool player_can_nhko_ai(const BattleState& state, int ai_idx, int n) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        if (move_pp_at(pl_mon, slot) == 0) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md || md->base_power == 0) continue;
        int32_t dmg = cpp_expected_damage(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C,
                                          -1, false, -1);
        if ((int64_t)dmg * n >= ai_mon.hp) return true;
    }
    return false;
}

// Returns (p_true, p_false) for 'should recover' check (mirrors Python _should_recover).
// Uses ::cpp_ai_faster (declared in ai_scorer.h, which every including TU pulls in).
inline std::pair<double,double> should_recover(const BattleState& state, int ai_idx, double heal_pct) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    if (ai_mon.status == STATUS_TOXIC) return {0.0, 1.0};

    int32_t heal = (int32_t)(ai_mon.max_hp * heal_pct);
    int32_t max_pl_dmg = 0;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        if (move_pp_at(pl_mon, slot) == 0) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md || md->base_power == 0) continue;
        int32_t d = cpp_expected_damage(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C,
                                        -1, false, -1);
        if (d > max_pl_dmg) max_pl_dmg = d;
    }

    if (max_pl_dmg >= heal) return {0.0, 1.0};

    double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
    bool ai_fst = cpp_ai_faster(state, ai_idx);
    bool pl_can_ko = player_can_ko_ai(state, ai_idx);
    int32_t healed_hp = std::min(ai_mon.max_hp, ai_mon.hp + heal);
    bool pl_can_ko_after = max_pl_dmg >= healed_hp;

    if (ai_fst) {
        if (pl_can_ko && !pl_can_ko_after) return {1.0, 0.0};
        if (!pl_can_ko) {
            if (hp_pct <= 0.4) return {1.0, 0.0};
            if (hp_pct < 0.66) return {0.5, 0.5};
        }
    } else {
        if (hp_pct < 0.5) return {1.0, 0.0};
        if (hp_pct < 0.7) return {0.75, 0.25};
    }
    return {0.0, 1.0};
}

inline bool side_has_condition(const SideState& side, int32_t cond) {
    for (const auto& sc : side.side_conditions)
        if (sc.condition == cond) return true;
    return false;
}

inline int count_side_conditions(const SideState& side, std::initializer_list<int32_t> conds) {
    int count = 0;
    for (const auto& sc : side.side_conditions)
        for (int32_t c : conds)
            if (sc.condition == c) { ++count; break; }
    return count;
}

inline bool has_pseudo_weather(const BattleState& state, int32_t effect) {
    for (const auto& pw : state.pseudo_weather)
        if (pw.effect == effect) return true;
    return false;
}

inline bool has_timed_volatile(const PokemonState& mon, int32_t effect) {
    for (const auto& tv : mon.timed_volatiles)
        if (tv.effect == effect) return true;
    return false;
}

// ---------------------------------------------------------------------------
// dist_* forward declarations (defined in ai_scorer_dist.cpp).
// Called from cpp_dist_action in ai_scorer.cpp.
// ---------------------------------------------------------------------------
using ::ScoreDistC;

ScoreDistC dist_recovery(const BattleState& state, int ai_idx, double heal_pct = 0.5);
ScoreDistC dist_protect(const BattleState& state, int ai_idx);
ScoreDistC dist_hazard(const BattleState& state, int ai_idx, int32_t move_id);
ScoreDistC dist_screen(const BattleState& state, int ai_idx, int32_t move_id);
ScoreDistC dist_paralysis(const BattleState& state, int ai_idx, int32_t move_id);
ScoreDistC dist_setup(const BattleState& state, int ai_idx, SetupKind kind);
ScoreDistC dist_tailwind(const BattleState& state, int ai_idx);
ScoreDistC dist_trick_room(const BattleState& state, int ai_idx);
ScoreDistC dist_terrain(const BattleState& state, int ai_idx);
ScoreDistC dist_poison_move(const BattleState& state, int ai_idx, int32_t move_id);
ScoreDistC dist_will_o_wisp(const BattleState& state, int ai_idx);
ScoreDistC dist_status_special(const BattleState& state, int ai_idx, int32_t move_id,
                               const PokemonState& ai_mon, const PokemonState& pl_mon, bool ai_fst);
ScoreDistC dist_damage(const BattleState& state, int ai_idx, int32_t move_id, const MoveData& md,
                       double p_highest, bool kills, bool ai_fst);

} // namespace ai_scorer

#endif // NUZLOCKE_AI_SCORER_INTERNAL_H
