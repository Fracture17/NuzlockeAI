// Stage 2+3 AI scorer: score distributions for actions and deterministic switch scoring.
// Ports src/ai.py _dist_*, _dist_action, _blend_damage_dist, _ai_faster,
//   _post_ko_switch_score, _cond2_valid_slots, _has_valid_switch_candidate,
//   _select_voluntary_switch_target, select_post_ko_switch.
// All _dist_* helpers are file-static; public interface is in ai_scorer.h.
#include "ai_scorer.h"
#include "ai_shared.h"
#include "ai_damage.h"
#include "damage.h"          // cpp_effective_stat
#include "type_chart_lookup.h"
#include "core_leaf.h"       // cpp_effective_speed

#include "../generated/ai_move_sets.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <set>
#include <stdexcept>
#include <vector>

// ---------------------------------------------------------------------------
// Local constants
// ---------------------------------------------------------------------------

// Move IDs (scorer-specific)
static constexpr int32_t MV_OVERHEAT          = 315;
static constexpr int32_t MV_LEAF_STORM        = 437;
static constexpr int32_t MV_SUPERPOWER        = 276;
static constexpr int32_t MV_FAKE_OUT          = 252;
static constexpr int32_t MV_FIRST_IMPRESSION  = 660;
static constexpr int32_t MV_FELL_STINGER      = 565;
static constexpr int32_t MV_ACID_SPRAY        = 491;
static constexpr int32_t MV_GRASSY_GLIDE      = 803;
static constexpr int32_t MV_SUCKER_PUNCH      = 389;
static constexpr int32_t MV_PURSUIT           = 228;
static constexpr int32_t MV_FLAME_CHARGE      = 488;
static constexpr int32_t MV_SMACK_DOWN        = 479;
static constexpr int32_t MV_THOUSAND_ARROWS   = 614;
static constexpr int32_t MV_STEALTH_ROCK      = 446;
static constexpr int32_t MV_SPIKES            = 191;
static constexpr int32_t MV_TOXIC_SPIKES      = 390;
static constexpr int32_t MV_STICKY_WEB        = 564;
static constexpr int32_t MV_LIGHT_SCREEN      = 113;
static constexpr int32_t MV_REFLECT           = 115;
static constexpr int32_t MV_REST              = 156;
static constexpr int32_t MV_SUBSTITUTE        = 164;
static constexpr int32_t MV_BELLY_DRUM        = 187;
static constexpr int32_t MV_SHELL_SMASH       = 504;
static constexpr int32_t MV_FOCUS_ENERGY      = 116;
static constexpr int32_t MV_LASER_FOCUS       = 673;
static constexpr int32_t MV_NASTY_PLOT        = 417;
static constexpr int32_t MV_TAIL_GLOW         = 294;
static constexpr int32_t MV_WORK_UP           = 526;
static constexpr int32_t MV_COACHING          = 811;
static constexpr int32_t MV_TAILWIND          = 366;
static constexpr int32_t MV_TRICK_ROOM        = 433;
static constexpr int32_t MV_ROLE_PLAY         = 272;
static constexpr int32_t MV_IMPRISON          = 286;
static constexpr int32_t MV_SLEEP_TALK        = 214;
static constexpr int32_t MV_LEECH_SEED        = 73;
// MV_FINAL_GAMBIT inherited from ai_shared.h
static constexpr int32_t MV_YAWN              = 281;
static constexpr int32_t MV_SCARY_FACE        = 184;
static constexpr int32_t MV_HELPING_HAND      = 270;
static constexpr int32_t MV_FOLLOW_ME         = 266;
static constexpr int32_t MV_TAUNT             = 269;
static constexpr int32_t MV_BATON_PASS        = 226;
static constexpr int32_t MV_MEMENTO           = 262;
static constexpr int32_t MV_ENCORE            = 227;
static constexpr int32_t MV_COUNTER           = 68;
static constexpr int32_t MV_MIRROR_COAT       = 243;
static constexpr int32_t MV_MAGNET_RISE       = 393;
static constexpr int32_t MV_DEFOG             = 432;
static constexpr int32_t MV_TROP_KICK         = 688;
static constexpr int32_t MV_BREAKING_SWIPE    = 784;
static constexpr int32_t MV_WILL_O_WISP       = 261;

// Item IDs (scorer-specific)
static constexpr int32_t ITM_POWER_HERB       = 271;
static constexpr int32_t ITM_LUM_BERRY        = 157;
static constexpr int32_t ITM_CHESTO_BERRY     = 150;
static constexpr int32_t ITM_SITRUS_BERRY     = 158;
static constexpr int32_t ITM_FOCUS_SASH       = 275;
static constexpr int32_t ITM_LIGHT_CLAY       = 269;
static constexpr int32_t ITM_SCOPE_LENS       = 232;
static constexpr int32_t ITM_SAFETY_GOGGLES   = 650;
static constexpr int32_t ITM_TERRAIN_EXTENDER = 879;

// Ability IDs (scorer-specific)
static constexpr int32_t AB_CONTRARY          = 126;
static constexpr int32_t AB_EARLY_BIRD        = 48;
static constexpr int32_t AB_SHED_SKIN         = 61;
static constexpr int32_t AB_HYDRATION         = 93;
static constexpr int32_t AB_STURDY            = 5;
static constexpr int32_t AB_INFILTRATOR       = 151;
static constexpr int32_t AB_LIMBER            = 7;
static constexpr int32_t AB_CORROSION         = 212;
static constexpr int32_t AB_INNER_FOCUS       = 39;
static constexpr int32_t AB_SHIELD_DUST       = 19;
static constexpr int32_t AB_SUPER_LUCK        = 105;
static constexpr int32_t AB_SNIPER            = 97;
static constexpr int32_t AB_CLEAR_BODY        = 29;
static constexpr int32_t AB_WHITE_SMOKE       = 73;
static constexpr int32_t AB_SHELL_ARMOR       = 75;
static constexpr int32_t AB_BATTLE_ARMOR      = 4;
static constexpr int32_t AB_INSOMNIA          = 15;
static constexpr int32_t AB_VITAL_SPIRIT      = 72;
static constexpr int32_t AB_OVERCOAT          = 142;
static constexpr int32_t AB_UNAWARE           = 109;

// Status values
static constexpr int32_t STATUS_SLEEP         = 6;
static constexpr int32_t STATUS_FREEZE        = 2;
static constexpr int32_t STATUS_BURN          = 1;
static constexpr int32_t STATUS_PARALYSIS     = 3;
static constexpr int32_t STATUS_NONE          = 0;

// Type values
static constexpr int32_t TYPE_FIRE            = 1;
static constexpr int32_t TYPE_ELECTRIC        = 3;
static constexpr int32_t TYPE_GROUND          = 8;
static constexpr int32_t TYPE_GRASS           = 4;
static constexpr int32_t TYPE_GHOST           = 13;
static constexpr int32_t TYPE_DARK            = 15;
static constexpr int32_t TYPE_STEEL           = 16;
static constexpr int32_t TYPE_POISON          = 7;
static constexpr int32_t TYPE_FLYING          = 9;

// Volatile bitmask values
static constexpr int32_t VOL_RECHARGING       = 256;
static constexpr int32_t VOL_SUBSTITUTE       = 4096;
static constexpr int32_t VOL_LEECH_SEEDED     = 2;
static constexpr int32_t VOL_CURSED           = 4;
static constexpr int32_t VOL_PERISH_SONG      = 16384;
static constexpr int32_t VOL_ATTRACTED        = 8388608;
static constexpr int32_t VOL_TAUNT_ACTIVE     = 16;
static constexpr int32_t VOL_ENCORE_ACTIVE    = 8;

// VolatileEffect int values (for timed_volatiles)
static constexpr int32_t VE_DROWSY            = 20;
static constexpr int32_t VE_MAGNET_RISE       = 8;
static constexpr int32_t VE_LASER_FOCUS       = 25;
static constexpr int32_t VE_GROUNDED          = 24;

// SideCondition int values
static constexpr int32_t SC_REFLECT           = 1;
static constexpr int32_t SC_LIGHT_SCREEN      = 2;
static constexpr int32_t SC_AURORA_VEIL       = 3;
static constexpr int32_t SC_STEALTH_ROCK      = 4;
static constexpr int32_t SC_SPIKES_1          = 5;
static constexpr int32_t SC_SPIKES_2          = 6;
static constexpr int32_t SC_SPIKES_3          = 7;
static constexpr int32_t SC_TOXIC_SPIKES_1    = 8;
static constexpr int32_t SC_TOXIC_SPIKES_2    = 9;
static constexpr int32_t SC_STICKY_WEB        = 10;
static constexpr int32_t SC_TAILWIND          = 11;

// PseudoWeather int values
static constexpr int32_t PW_TRICK_ROOM        = 1;

// Weather int values
static constexpr int32_t WE_SUNNY             = 1;
static constexpr int32_t WE_HARSH_SUN         = 6;

// Terrain int values
static constexpr int32_t TE_PSYCHIC           = 3;
static constexpr int32_t TE_GRASSY            = 2;
static constexpr int32_t TE_ELECTRIC          = 1;
static constexpr int32_t TE_MISTY             = 4;

// FormatEnum
static constexpr int32_t FMT_SINGLES          = 0;
static constexpr int32_t FMT_DOUBLES          = 1;

// MoveTag bitmask values
static constexpr int32_t TAG_RECOVERY         = 4;
static constexpr int32_t TAG_HAZARD           = 32;
static constexpr int32_t TAG_SCREEN           = 64;
static constexpr int32_t TAG_POWDER           = 16384;
static constexpr int32_t TAG_SETUP            = 2;
static constexpr int32_t TAG_STATUS_BIT       = 8;

// MoveCategory values
static constexpr int32_t CAT_PHYSICAL         = 0;
static constexpr int32_t CAT_SPECIAL          = 1;
static constexpr int32_t CAT_STATUS           = 2;

// MoveTarget values
static constexpr int32_t TGT_SELF             = 1;

// Species IDs
static constexpr int32_t SP_MELOETTA_PIROUETTE = 1107;

// ActionKind
static constexpr int32_t AK_MOVE             = 0;
static constexpr int32_t AK_SWITCH           = 1;

// ---------------------------------------------------------------------------
// AVERAGE_LUCK profile for threat-checking (_player_can_ko_ai etc.)
// crit_threshold=50, damage_roll=1.0, proc_threshold=50, random_mode=false
// Differs from _MAX_DAMAGE_LUCK only in crit_threshold (50 vs 100).
// ---------------------------------------------------------------------------
static LuckProfileC make_average_luck() {
    LuckProfileC l;
    l.crit_threshold  = 50.0;
    l.damage_roll     = 1.0;
    l.proc_threshold  = 50.0;
    l.random_mode     = false;
    return l;
}
static const LuckProfileC AVERAGE_LUCK_C = make_average_luck();

// _MAX_DAMAGE_LUCK: BAD_LUCK with damage_roll=1.0.
// multi_hit_roll=0.0 (inherited from BAD_LUCK) gives min hits (2) for 2-5 hit moves.
static LuckProfileC make_max_damage_luck_scorer() {
    LuckProfileC l;
    l.crit_threshold  = 100.0;
    l.damage_roll     = 1.0;
    l.proc_threshold  = 101.0;
    l.random_mode     = false;
    l.multi_hit_roll  = 0.0;  // BAD_LUCK default: minimum hit count
    return l;
}
static const LuckProfileC MAX_LUCK_C = make_max_damage_luck_scorer();

// ---------------------------------------------------------------------------
// Stat access helpers
// ---------------------------------------------------------------------------

static int32_t mon_stage(const PokemonState& m, int idx) {
    switch (idx) {
        case 0: return m.stage0; case 1: return m.stage1; case 2: return m.stage2;
        case 3: return m.stage3; case 4: return m.stage4; case 5: return m.stage5;
        case 6: return m.stage6;
        default: return 0;
    }
}

// Physical stat (raw, before stage): maps to stats array index.
// Using cpp_effective_stat for stage-modified stat comparisons.
// For raw stat we use the stored stat fields.
static int32_t mon_stat_raw(const PokemonState& m, int idx) {
    // idx: 0=HP, 1=ATK, 2=DEF, 3=SPA, 4=SPD, 5=SPE
    switch (idx) {
        case 0: return m.stat_hp; case 1: return m.stat_atk; case 2: return m.stat_def;
        case 3: return m.stat_spa; case 4: return m.stat_spd; case 5: return m.stat_spe;
        default: return 0;
    }
}

// ---------------------------------------------------------------------------
// Predicates (mirrors Python helpers)
// ---------------------------------------------------------------------------

static bool is_type_immune(const MoveData& md, const PokemonState& defender) {
    // Returns true if defender is type-immune to the move (Ring Target removes immunities).
    for (int32_t t : defender.types) {
        float eff = cpp_type_effectiveness((int32_t)md.move_type, t);
        if (eff == 0.0f && defender.item != ITM_RING_TARGET) return true;
    }
    return false;
}

static bool is_incapacitated(const PokemonState& mon) {
    return (mon.status == STATUS_SLEEP || mon.status == STATUS_FREEZE
            || (mon.volatiles & VOL_RECHARGING));
}

static bool has_protect_debuff(const PokemonState& mon) {
    if (mon.status == STATUS_POISON || mon.status == STATUS_TOXIC || mon.status == STATUS_BURN)
        return true;
    if (mon.volatiles & (VOL_CURSED | VOL_LEECH_SEEDED | VOL_PERISH_SONG | VOL_ATTRACTED))
        return true;
    for (const auto& tv : mon.timed_volatiles)
        if (tv.effect == VE_DROWSY) return true;
    return false;
}

// True if move_id is super-effective against pl_mon.
static bool is_move_super_effective(int32_t move_id, const PokemonState& pl_mon) {
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
static bool player_has_split(const PokemonState& pl_mon, int32_t category) {
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

static bool player_can_ko_ai(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    // Sturdy at full HP prevents OHKO
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
static bool player_can_nhko_ai(const BattleState& state, int ai_idx, int n) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        if (move_pp_at(pl_mon, slot) == 0) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md || md->base_power == 0) continue;
        int32_t dmg = cpp_expected_damage(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C,
                                          /*roll_index=*/-1, false, /*hit_count_override=*/-1);
        if ((int64_t)dmg * n >= ai_mon.hp) return true;
    }
    return false;
}

// Returns (p_true, p_false) for 'should recover' check (mirrors Python _should_recover).
static std::pair<double,double> should_recover(const BattleState& state, int ai_idx, double heal_pct) {
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

// True if side_conditions contains given condition.
static bool side_has_condition(const SideState& side, int32_t cond) {
    for (const auto& sc : side.side_conditions)
        if (sc.condition == cond) return true;
    return false;
}

// Count occurrences of any of several conditions in side_conditions.
static int count_side_conditions(const SideState& side, std::initializer_list<int32_t> conds) {
    int count = 0;
    for (const auto& sc : side.side_conditions)
        for (int32_t c : conds)
            if (sc.condition == c) { ++count; break; }
    return count;
}

static bool has_pseudo_weather(const BattleState& state, int32_t effect) {
    for (const auto& pw : state.pseudo_weather)
        if (pw.effect == effect) return true;
    return false;
}

static bool has_timed_volatile(const PokemonState& mon, int32_t effect) {
    for (const auto& tv : mon.timed_volatiles)
        if (tv.effect == effect) return true;
    return false;
}

// ---------------------------------------------------------------------------
// _dist_recovery
// ---------------------------------------------------------------------------

static ScoreDistC dist_recovery(const BattleState& state, int ai_idx, double heal_pct = 0.5) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
    if (hp_pct >= 1.0) return {{-20, 1.0}};
    if (hp_pct >= 0.85) return {{-6, 1.0}};
    auto [p_true, p_false] = should_recover(state, ai_idx, heal_pct);
    ScoreDistC out;
    if (p_true > 0) out.push_back({7, p_true});
    if (p_false > 0) out.push_back({5, p_false});
    if (out.empty()) out.push_back({5, 1.0});
    return out;
}

// ---------------------------------------------------------------------------
// _dist_protect
// ---------------------------------------------------------------------------

static ScoreDistC dist_protect(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    int base = 6;
    if (has_protect_debuff(ai_mon)) base -= 2;
    if (has_protect_debuff(pl_mon)) base += 1;
    if (ai_mon.turns_in_battle == 0 && state.format != FMT_DOUBLES) base -= 1;
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_hazard
// ---------------------------------------------------------------------------

static ScoreDistC dist_hazard(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const SideState& opp_side = side_at(state, 1 - ai_idx);
    bool first_turn = ai_mon.turns_in_battle == 0;

    if (move_id == MV_STEALTH_ROCK) {
        if (side_has_condition(opp_side, SC_STEALTH_ROCK)) return {{-20, 1.0}};
        return first_turn ? ScoreDistC{{8, 0.25}, {9, 0.75}} : ScoreDistC{{6, 0.25}, {7, 0.75}};
    }
    if (move_id == MV_SPIKES) {
        int existing = count_side_conditions(opp_side, {SC_SPIKES_1, SC_SPIKES_2, SC_SPIKES_3});
        if (existing >= 3) return {{-20, 1.0}};
        int adj = (existing > 0) ? -1 : 0;
        return first_turn ? ScoreDistC{{8+adj, 0.25}, {9+adj, 0.75}} : ScoreDistC{{6+adj, 0.25}, {7+adj, 0.75}};
    }
    if (move_id == MV_TOXIC_SPIKES) {
        int existing = count_side_conditions(opp_side, {SC_TOXIC_SPIKES_1, SC_TOXIC_SPIKES_2});
        if (existing >= 2) return {{-20, 1.0}};
        int adj = (existing > 0) ? -1 : 0;
        return first_turn ? ScoreDistC{{8+adj, 0.25}, {9+adj, 0.75}} : ScoreDistC{{6+adj, 0.25}, {7+adj, 0.75}};
    }
    if (move_id == MV_STICKY_WEB) {
        if (side_has_condition(opp_side, SC_STICKY_WEB)) return {{-20, 1.0}};
        return first_turn ? ScoreDistC{{9, 0.25}, {12, 0.75}} : ScoreDistC{{6, 0.25}, {9, 0.75}};
    }
    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_screen
// ---------------------------------------------------------------------------

static ScoreDistC dist_screen(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    bool is_lscreen = (move_id == MV_LIGHT_SCREEN);
    const SideState& ai_side = side_at(state, ai_idx);
    if (is_lscreen && side_has_condition(ai_side, SC_LIGHT_SCREEN)) return {{-40, 1.0}};
    if (!is_lscreen && side_has_condition(ai_side, SC_REFLECT)) return {{-40, 1.0}};

    int base = 6;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md) continue;
        bool relevant = (is_lscreen && (int32_t)md->category == CAT_SPECIAL)
                     || (!is_lscreen && (int32_t)md->category == CAT_PHYSICAL);
        if (relevant) {
            int clay_bonus = (ai_mon.item == ITM_LIGHT_CLAY) ? 1 : 0;
            return {{base + clay_bonus + 1, 0.5}, {base + clay_bonus, 0.5}};
        }
    }
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_paralysis
// ---------------------------------------------------------------------------

static ScoreDistC dist_paralysis(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    const MoveData& md = ai_move_data_or_throw(move_id);

    // Electric-type: blocked by Ground, Electric type, or Limber
    if ((int32_t)md.move_type == TYPE_ELECTRIC) {
        for (int32_t t : pl_mon.types) {
            if (t == TYPE_GROUND || t == TYPE_ELECTRIC) return {{-40, 1.0}};
        }
        if (pl_mon.ability == AB_LIMBER) return {{-40, 1.0}};
    }
    if (pl_mon.ability == AB_LIMBER) return {{-40, 1.0}};
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};

    // cpp_effective_stat for raw speed (stat index 5)
    int32_t pl_spe = cpp_effective_stat(pl_mon, 5);
    int32_t ai_spe = cpp_effective_stat(ai_mon, 5);
    int32_t para_spe = std::max(1, pl_spe / 4);
    bool speed_flip = (pl_spe > ai_spe && para_spe < ai_spe);
    int base = speed_flip ? 8 : 7;
    return {{base - 1, 0.5}, {base, 0.5}};
}

// ---------------------------------------------------------------------------
// _dist_setup (SetupKind: OFFENSIVE=0, DEFENSIVE=1, SPEED=2)
// ---------------------------------------------------------------------------
enum class SetupKind { OFFENSIVE, DEFENSIVE, SPEED };

static ScoreDistC dist_setup(const BattleState& state, int ai_idx, SetupKind kind) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    if (kind == SetupKind::SPEED) {
        return cpp_ai_faster(state, ai_idx) ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{7, 1.0}};
    }

    // Threatened → never setup
    if (player_can_ko_ai(state, ai_idx)) {
        bool sash = (ai_mon.item == ITM_FOCUS_SASH && ai_mon.hp == ai_mon.max_hp);
        bool sturdy = (ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp);
        if (!sash && !sturdy) return {{-20, 1.0}};
    }

    bool slower_2hko = (!cpp_ai_faster(state, ai_idx) && player_can_nhko_ai(state, ai_idx, 2));
    bool incap = is_incapacitated(pl_mon);

    if (kind == SetupKind::OFFENSIVE) {
        int base = 6;
        if (incap) base += 3;
        if (slower_2hko) base -= 5;
        return {{base, 1.0}};
    }

    // DEFENSIVE
    int base = 6;
    if (slower_2hko) base -= 5;
    if (incap) return {{base + 2, 0.95}, {base, 0.05}};
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_tailwind
// ---------------------------------------------------------------------------

static ScoreDistC dist_tailwind(const BattleState& state, int ai_idx) {
    const SideState& ai_side = side_at(state, ai_idx);
    if (side_has_condition(ai_side, SC_TAILWIND)) return {{-40, 1.0}};
    const SideState& pl_side = side_at(state, 1 - ai_idx);
    bool useful = false;
    for (int ai_i : ai_side.active_indices) {
        if (ai_side.team[ai_i].fainted) continue;
        int32_t ai_spe = cpp_effective_stat(ai_side.team[ai_i], 5);
        for (int pl_i : pl_side.active_indices) {
            if (pl_side.team[pl_i].fainted) continue;
            int32_t pl_spe = cpp_effective_stat(pl_side.team[pl_i], 5);
            if (ai_spe < pl_spe) { useful = true; break; }
        }
        if (useful) break;
    }
    return useful ? ScoreDistC{{9, 1.0}} : ScoreDistC{{5, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_trick_room
// ---------------------------------------------------------------------------

static ScoreDistC dist_trick_room(const BattleState& state, int ai_idx) {
    if (has_pseudo_weather(state, PW_TRICK_ROOM)) return {{-20, 1.0}};
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    int32_t ai_spe = cpp_effective_stat(ai_mon, 5);
    int32_t pl_spe = cpp_effective_stat(pl_mon, 5);
    return (ai_spe < pl_spe) ? ScoreDistC{{10, 1.0}} : ScoreDistC{{5, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_terrain
// ---------------------------------------------------------------------------

static ScoreDistC dist_terrain(const BattleState& state, int ai_idx) {
    if (state.terrain != 0) return {{-40, 1.0}};
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    return (ai_mon.item == ITM_TERRAIN_EXTENDER) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{8, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_poison_move
// ---------------------------------------------------------------------------

static ScoreDistC dist_poison_move(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    // Toxic blocked on Poison/Steel unless Corrosion
    if (move_id == 92 /*TOXIC*/) {  // Move.TOXIC = 92
        bool blocked = false;
        for (int32_t t : pl_mon.types)
            if (t == TYPE_POISON || t == TYPE_STEEL) { blocked = true; break; }
        if (blocked && ai_mon.ability != AB_CORROSION) return {{-40, 1.0}};
    }
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_will_o_wisp
// ---------------------------------------------------------------------------

static ScoreDistC dist_will_o_wisp(const BattleState& state, int ai_idx) {
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    for (int32_t t : pl_mon.types)
        if (t == TYPE_FIRE) return {{-20, 1.0}};
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
    return {{7, 0.37}, {6, 0.63}};
}

// ---------------------------------------------------------------------------
// _dist_status_special
// ---------------------------------------------------------------------------

static ScoreDistC dist_status_special(const BattleState& state, int ai_idx, int32_t move_id,
                                      const PokemonState& ai_mon, const PokemonState& pl_mon,
                                      bool ai_fst) {
    // Role Play: -20 in singles
    if (move_id == MV_ROLE_PLAY) {
        if (state.format != FMT_DOUBLES) return {{-20, 1.0}};
        const SideState& ai_side = side_at(state, ai_idx);
        for (size_t pi = 1; pi < ai_side.active_indices.size(); ++pi) {
            int slot = ai_side.active_indices[pi];
            const PokemonState& partner = ai_side.team[slot];
            if (!partner.fainted
                && ai_set_contains(ROLE_PLAY_VALUABLE_ABILITIES, N_ROLE_PLAY_VALUABLE_ABILITIES, partner.ability)
                && partner.ability != ai_mon.ability)
                return {{9, 1.0}};
        }
        return {{-20, 1.0}};
    }

    // Imprison
    if (move_id == MV_IMPRISON) {
        const SideState& pl_side = side_at(state, 1 - ai_idx);
        if (!pl_side.imprisoned_moves.empty()) return {{-20, 1.0}};
        // Check if AI and player share a move
        for (int slot = 0; slot < 4; ++slot) {
            int32_t ai_mid = move_id_at(ai_mon, slot);
            if (ai_mid == MV_NONE) continue;
            for (int pslot = 0; pslot < 4; ++pslot) {
                int32_t pl_mid = move_id_at(pl_mon, pslot);
                if (pl_mid == MV_NONE) continue;
                if (ai_mid == pl_mid) return {{9, 1.0}};
            }
        }
        return {{-20, 1.0}};
    }

    // Sleep Talk
    if (move_id == MV_SLEEP_TALK) {
        return (ai_mon.status == STATUS_SLEEP) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{-40, 1.0}};
    }

    // Leech Seed
    if (move_id == MV_LEECH_SEED) {
        for (int32_t t : pl_mon.types)
            if (t == TYPE_GRASS) return {{-20, 1.0}};
        if (pl_mon.volatiles & VOL_LEECH_SEEDED) return {{-20, 1.0}};
        return {{6, 1.0}};
    }

    // Final Gambit
    if (move_id == MV_FINAL_GAMBIT) {
        if (ai_fst && ai_mon.hp > pl_mon.hp) return {{8, 1.0}};
        if (ai_fst && player_can_ko_ai(state, ai_idx)) return {{7, 1.0}};
        return {{6, 1.0}};
    }

    // Yawn
    if (move_id == MV_YAWN) {
        if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
        if (state.terrain == TE_ELECTRIC || state.terrain == TE_MISTY) return {{-20, 1.0}};
        if (pl_mon.ability == AB_INSOMNIA || pl_mon.ability == AB_VITAL_SPIRIT) return {{-20, 1.0}};
        return {{6, 1.0}};
    }

    // Scary Face
    if (move_id == MV_SCARY_FACE) {
        return ai_fst ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Helping Hand / Follow Me: 0 in singles (+6 default - 6 singles penalty)
    if (move_id == MV_HELPING_HAND || move_id == MV_FOLLOW_ME) {
        return (state.format != FMT_DOUBLES) ? ScoreDistC{{0, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Weather moves: -40 if target weather already active
    if (ai_set_contains(WEATHER_MOVE_IDS, N_WEATHER_MOVES, move_id)) {
        // Find the target weather for this move
        for (int i = 0; i < N_WEATHER_MOVES; ++i) {
            if (WEATHER_MOVE_IDS[i] == move_id) {
                if (state.weather == WEATHER_MOVE_WEATHERS[i]) return {{-40, 1.0}};
                return {{6, 1.0}};
            }
        }
    }

    // Taunt
    if (move_id == MV_TAUNT) {
        if (pl_mon.volatiles & VOL_TAUNT_ACTIVE) return {{-40, 1.0}};
        bool tr_active = has_pseudo_weather(state, PW_TRICK_ROOM);
        bool has_tr = false;
        for (int slot = 0; slot < 4; ++slot)
            if (move_id_at(pl_mon, slot) == MV_TRICK_ROOM) { has_tr = true; break; }
        if (has_tr && !tr_active) return {{9, 1.0}};
        bool has_defog = false;
        for (int slot = 0; slot < 4; ++slot)
            if (move_id_at(pl_mon, slot) == MV_DEFOG) { has_defog = true; break; }
        const SideState& ai_side = side_at(state, ai_idx);
        bool has_aurora_veil = side_has_condition(ai_side, SC_AURORA_VEIL);
        if (has_defog && has_aurora_veil && ai_fst) return {{9, 1.0}};
        return {{5, 1.0}};
    }

    // Baton Pass
    if (move_id == MV_BATON_PASS) {
        bool has_sub = (ai_mon.volatiles & VOL_SUBSTITUTE) != 0;
        bool has_boost = false;
        for (int i = 0; i < 7; ++i)
            if (mon_stage(ai_mon, i) > 0) { has_boost = true; break; }
        if (has_sub || has_boost) return {{14, 1.0}};
        int ai_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        if (ai_living == 1) return {{-20, 1.0}};
        return {{0, 1.0}};
    }

    // Memento
    if (move_id == MV_MEMENTO) {
        int ai_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        if (ai_living == 1) return {{-40, 1.0}};
        double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
        if (hp_pct < 0.10) return {{16, 1.0}};
        if (hp_pct < 0.33) return {{14, 0.70}, {6, 0.30}};
        if (hp_pct < 0.66) return {{13, 0.50}, {6, 0.50}};
        return {{13, 0.05}, {6, 0.95}};
    }

    // Encore
    if (move_id == MV_ENCORE) {
        if (pl_mon.volatiles & VOL_ENCORE_ACTIVE) return {{-40, 1.0}};
        if (pl_mon.last_used_slot == -1) return {{-40, 1.0}};
        if (!ai_fst) return {{5, 0.5}, {6, 0.5}};
        return {{6, 1.0}};
    }

    // Counter / Mirror Coat
    if (move_id == MV_COUNTER || move_id == MV_MIRROR_COAT) {
        bool is_counter = (move_id == MV_COUNTER);
        if (is_counter) {
            for (int32_t t : pl_mon.types)
                if (t == TYPE_GHOST) return {{-20, 1.0}};
        } else {
            for (int32_t t : pl_mon.types)
                if (t == TYPE_DARK) return {{-20, 1.0}};
        }
        int32_t relevant_cat = is_counter ? CAT_PHYSICAL : CAT_SPECIAL;
        if (!player_has_split(pl_mon, relevant_cat)) return {{-20, 1.0}};
        if (player_can_ko_ai(state, ai_idx)
            && ai_mon.item != ITM_FOCUS_SASH
            && !(ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp))
            return {{-20, 1.0}};

        int32_t other_cat = is_counter ? CAT_SPECIAL : CAT_PHYSICAL;
        bool player_only_split = !player_has_split(pl_mon, other_cat);

        // Check if player has any STATUS moves with PP>0
        bool pl_has_status = false;
        for (int slot = 0; slot < 4; ++slot) {
            int32_t mid = move_id_at(pl_mon, slot);
            if (mid == MV_NONE) continue;
            if (move_pp_at(pl_mon, slot) == 0) continue;
            const MoveData* md = ai_move_data_get(mid);
            if (md && (int32_t)md->category == CAT_STATUS) { pl_has_status = true; break; }
        }

        int base = 6;
        if (player_only_split) {
            if (player_can_ko_ai(state, ai_idx)) {
                base = 8;
            } else {
                // Complex expansion: [(8,0.80),(6,0.20)] then ai_fst and pl_has_status expansions
                ScoreDistC dist = {{8, 0.80}, {6, 0.20}};
                if (ai_fst) {
                    ScoreDistC nd;
                    for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
                    dist = nd;
                }
                if (pl_has_status) {
                    ScoreDistC nd;
                    for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
                    dist = nd;
                }
                return dist;
            }
        }
        ScoreDistC dist = {{base, 1.0}};
        if (ai_fst) {
            ScoreDistC nd;
            for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
            dist = nd;
        }
        if (pl_has_status) {
            ScoreDistC nd;
            for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
            dist = nd;
        }
        return dist;
    }

    // Magnet Rise
    if (move_id == MV_MAGNET_RISE) {
        if (has_timed_volatile(ai_mon, VE_MAGNET_RISE)) return {{-40, 1.0}};
        if (ai_fst) {
            for (int slot = 0; slot < 4; ++slot) {
                int32_t mid = move_id_at(pl_mon, slot);
                if (mid == MV_NONE) continue;
                if (move_pp_at(pl_mon, slot) == 0) continue;
                const MoveData* md = ai_move_data_get(mid);
                if (md && (int32_t)md->move_type == TYPE_GROUND && md->base_power > 0)
                    return {{8, 1.0}};
            }
        }
        return {{5, 1.0}};
    }

    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_damage
// ---------------------------------------------------------------------------

static ScoreDistC dist_damage(const BattleState& state, int ai_idx, int32_t move_id,
                              const MoveData& md, double p_highest, bool kills, bool ai_fst) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    // Rollout: always +7
    if (move_id == MV_ROLLOUT) return {{7, 1.0}};

    // Relic Song: Meloetta form-dependent
    if (move_id == MV_RELIC_SONG) {
        return (ai_mon.species == SP_MELOETTA_PIROUETTE)
            ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{10, 1.0}};
    }

    // Meteor Beam: Power Herb conditional
    if (move_id == MV_METEOR_BEAM) {
        return (ai_mon.item == ITM_POWER_HERB) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{-20, 1.0}};
    }

    // Contrary: treat Overheat/Leaf Storm/Superpower as setup when not HD and not killing
    if (ai_mon.ability == AB_CONTRARY && !kills && p_highest <= 0.0
        && (move_id == MV_OVERHEAT || move_id == MV_LEAF_STORM || move_id == MV_SUPERPOWER)) {
        return is_incapacitated(pl_mon) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Fake Out
    bool fake_out_first_turn = false;
    if (move_id == MV_FAKE_OUT) {
        if (pl_mon.ability == AB_SHIELD_DUST || pl_mon.ability == AB_INNER_FOCUS)
            return {{-40, 1.0}};
        if (ai_mon.turns_in_battle != 0) return {{-40, 1.0}};
        // Type immunity check
        bool fo_immune = false;
        for (int32_t t : pl_mon.types) {
            float eff = cpp_type_effectiveness((int32_t)md.move_type, t);
            if (eff == 0.0f && pl_mon.item != ITM_RING_TARGET) { fo_immune = true; break; }
        }
        if (fo_immune) return {{-40, 1.0}};
        fake_out_first_turn = true;
    }

    // First Impression: -50 after first turn
    if (move_id == MV_FIRST_IMPRESSION && ai_mon.turns_in_battle > 0) return {{-50, 1.0}};

    // Fell Stinger: forced score when killing and Atk not maxed
    if (move_id == MV_FELL_STINGER && kills && ai_mon.stage0 < 6) {
        return ai_fst ? ScoreDistC{{21, 0.8}, {23, 0.2}} : ScoreDistC{{15, 0.8}, {17, 0.2}};
    }

    // Psychic Terrain blocks priority
    if (state.terrain == TE_PSYCHIC && md.priority > 0) return {{-40, 1.0}};

    // Fixed-damage moves: -40 if type-immune
    if (is_fixed_damage_rank_move(move_id)) {
        if (is_type_immune(md, pl_mon)) return {{-40, 1.0}};
    }

    // Explosion / Self-Destruct / Misty Explosion
    if (move_id == MV_EXPLOSION || move_id == MV_SELF_DESTRUCT || move_id == MV_MISTY_EXPLOSION) {
        if (is_type_immune(md, pl_mon)) return {{-40, 1.0}};
        int ai_living = 0, pl_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        for (const auto& m : side_at(state, 1 - ai_idx).team) if (!m.fainted) ++pl_living;
        if (ai_living == 1 && pl_living >= 2) return {{-40, 1.0}};
        if (!kills) {
            double ai_hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
            ScoreDistC base_dist;
            if (ai_hp_pct < 0.10)      base_dist = {{10, 1.0}};
            else if (ai_hp_pct < 0.33) base_dist = {{8, 0.70}, {0, 0.30}};
            else if (ai_hp_pct < 0.66) base_dist = {{7, 0.50}, {0, 0.50}};
            else                       base_dist = {{7, 0.05}, {0, 0.95}};
            if (ai_living == 1 && pl_living == 1) {
                for (auto& [s, p] : base_dist) s -= 1;
            }
            return base_dist;
        }
        // Kill case falls through
    }

    // Base kill/HD distribution
    ScoreDistC base_dist;
    if (kills) {
        int kb = ai_fst ? 6 : 3;
        int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
        base_dist = {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
    } else if (p_highest <= 0.0) {
        base_dist = {{0, 1.0}};
    } else if (p_highest >= 1.0) {
        base_dist = {{6, 0.8}, {8, 0.2}};
    } else {
        base_dist = {{6, 0.8 * p_highest}, {8, 0.2 * p_highest}, {0, 1.0 - p_highest}};
    }

    // Acid Spray: +6 bonus
    if (move_id == MV_ACID_SPRAY) {
        for (auto& [s, p] : base_dist) s += 6;
    }

    // Fake Out first-turn: +9 bonus
    if (fake_out_first_turn) {
        for (auto& [s, p] : base_dist) s += 9;
    }

    // Priority bonus (+11): AI slower, player can KO AI, move is priority
    bool is_priority_move = (md.priority > 0)
        || (move_id == MV_GRASSY_GLIDE && state.terrain == TE_GRASSY);
    if (player_can_ko_ai(state, ai_idx) && !ai_fst && is_priority_move) {
        for (auto& [s, p] : base_dist) s += 11;
    }

    // Future Sight: compute independently
    if (move_id == MV_FUTURE_SIGHT) {
        int32_t fs_dmg = cpp_expected_damage(ai_mon, move_id, pl_mon, state, MAX_LUCK_C,
                                             -1, false, -1);
        if (fs_dmg >= pl_mon.hp) {
            int kb = ai_fst ? 6 : 3;
            int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
            return {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
        }
        int score = (ai_fst && player_can_ko_ai(state, ai_idx)) ? 8 : 6;
        return {{score, 1.0}};
    }

    // Trapping moves: always +6/+8, own kill check
    if (is_trapping(move_id)) {
        int32_t tm_dmg = cpp_expected_damage(ai_mon, move_id, pl_mon, state, MAX_LUCK_C,
                                             -1, false, -1);
        if (tm_dmg >= pl_mon.hp) {
            int kb = ai_fst ? 6 : 3;
            int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
            return {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
        }
        return {{6, 0.8}, {8, 0.2}};
    }

    // Sucker Punch last-turn penalty
    if (move_id == MV_SUCKER_PUNCH && ai_mon.sucker_punch_last_turn) {
        ScoreDistC nd;
        for (auto [s, p] : base_dist) { nd.push_back({s - 20, p * 0.5}); nd.push_back({s, p * 0.5}); }
        base_dist = nd;
    }

    // Pursuit
    if (move_id == MV_PURSUIT && !kills) {
        double pl_hp_pct = (double)pl_mon.hp / pl_mon.max_hp;
        if (pl_hp_pct <= 0.20) {
            for (auto& [s, p] : base_dist) s += 10;
        } else if (pl_hp_pct <= 0.40) {
            ScoreDistC nd;
            for (auto [s, p] : base_dist) { nd.push_back({s + 8, p * 0.5}); nd.push_back({s, p * 0.5}); }
            base_dist = nd;
        }
        if (ai_fst) for (auto& [s, p] : base_dist) s += 3;
    } else if (move_id == MV_PURSUIT && kills) {
        for (auto& [s, p] : base_dist) s += 10;
        if (ai_fst) for (auto& [s, p] : base_dist) s += 3;
    }

    // Speed-reduction moves: +6 or +5 when not HD and not killing
    if (ai_set_contains(SPEED_REDUCTION_MOVES, N_SPEED_REDUCTION_MOVES, move_id) && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            bool blocked = ai_set_contains(STAT_REDUCTION_ABILITIES, N_STAT_REDUCTION_ABILITIES,
                                           pl_mon.ability);
            return (!blocked && !ai_fst) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{5, 1.0}};
        }
    }

    // Stat-reduction damaging moves: +6 or +5 when not HD and not killing
    if (ai_set_contains(STAT_REDUCTION_DAMAGE_MOVES, N_STAT_REDUCTION_DAMAGE_MOVES, move_id) && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            bool physical_move = (move_id == MV_TROP_KICK || move_id == MV_BREAKING_SWIPE);
            int32_t relevant_split = physical_move ? CAT_PHYSICAL : CAT_SPECIAL;
            bool has_split = player_has_split(pl_mon, relevant_split);
            bool blocked = ai_set_contains(STAT_REDUCTION_ABILITIES, N_STAT_REDUCTION_ABILITIES,
                                           pl_mon.ability);
            return (!blocked && has_split) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{5, 1.0}};
        }
    }

    // Flame Charge: +6 when AI slower, 0 when AI faster
    if (move_id == MV_FLAME_CHARGE && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            return ai_fst ? ScoreDistC{{0, 1.0}} : ScoreDistC{{6, 1.0}};
        }
    }

    // Smack Down / Thousand Arrows: +6 grounding bonus if player is groundable
    if (move_id == MV_SMACK_DOWN || move_id == MV_THOUSAND_ARROWS) {
        bool already_grounded = has_timed_volatile(pl_mon, VE_GROUNDED);
        bool groundable = false;
        for (int32_t t : pl_mon.types) if (t == TYPE_FLYING) { groundable = true; break; }
        if (!groundable && pl_mon.ability == 26 /* LEVITATE */) groundable = true; // Levitate=26
        if (groundable && !already_grounded) {
            for (auto& [s, p] : base_dist) s += 6;
        }
    }

    // High-crit SE bonus: +1 at 50% rate
    if (ai_set_contains(HIGH_CRIT_MOVES, N_HIGH_CRIT_MOVES, move_id)
        && is_move_super_effective(move_id, pl_mon)) {
        ScoreDistC nd;
        for (auto [s, p] : base_dist) {
            nd.push_back({s, p * 0.5});
            nd.push_back({s + 1, p * 0.5});
        }
        base_dist = nd;
    }

    return base_dist;
}

// ---------------------------------------------------------------------------
// Public: cpp_ai_faster
// ---------------------------------------------------------------------------

bool cpp_ai_faster(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    const SideState& ai_side = side_at(state, ai_idx);
    const SideState& pl_side = side_at(state, 1 - ai_idx);
    int32_t ai_spe = cpp_ai_effective_speed(ai_mon, ai_side, state);
    int32_t pl_spe = cpp_ai_effective_speed(pl_mon, pl_side, state);
    return ai_spe >= pl_spe;
}

// ---------------------------------------------------------------------------
// Public: cpp_dist_action
// ---------------------------------------------------------------------------

ScoreDistC cpp_dist_action(const BattleState& state, int ai_idx, const ExecAction& action,
                           double p_highest, bool kills, bool ai_fst) {
    // Switch or recharge
    if (action.kind == AK_SWITCH) return {{0, 1.0}};

    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    int32_t slot = action.move_slot;
    if (slot < 0) return {{0, 1.0}};  // recharge

    int32_t move_id = move_id_at(ai_mon, slot);
    if (move_id == MV_NONE) return {{0, 1.0}};

    const MoveData* mdp = ai_move_data_get(move_id);
    if (mdp == nullptr) return {{6, 1.0}};  // md is None → [(6, 1.0)]
    const MoveData& md = *mdp;

    // --- Damaging moves ---
    if (move_id == MV_ROLLOUT || move_id == MV_RELIC_SONG || move_id == MV_METEOR_BEAM
        || is_fixed_damage_rank_move(move_id)
        || (md.tags & TAG_DAMAGE)) {
        return dist_damage(state, ai_idx, move_id, md, p_highest, kills, ai_fst);
    }

    // --- Protect ---
    if (ai_set_contains(PROTECT_MOVES, N_PROTECT_MOVES, move_id)) {
        return dist_protect(state, ai_idx);
    }

    // --- Recovery (tag-based, then explicit lists, then REST) ---
    if (md.tags & TAG_RECOVERY || ai_set_contains(RECOVERY_MOVE_SET, N_RECOVERY_MOVE_SET, move_id)) {
        return dist_recovery(state, ai_idx, 0.5);
    }
    if (ai_set_contains(WEATHER_RECOVERY_MOVES, N_WEATHER_RECOVERY_MOVES, move_id)) {
        bool sun = (state.weather == WE_SUNNY || state.weather == WE_HARSH_SUN);
        return dist_recovery(state, ai_idx, sun ? 0.67 : 0.5);
    }
    if (move_id == MV_REST) {
        auto [p_true, p_false] = should_recover(state, ai_idx, 1.0);
        double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
        if (hp_pct >= 1.0) return {{-20, 1.0}};
        if (hp_pct >= 0.85) return {{-6, 1.0}};
        bool has_cure = (ai_mon.item == ITM_LUM_BERRY || ai_mon.item == ITM_CHESTO_BERRY
                         || ai_mon.ability == AB_EARLY_BIRD || ai_mon.ability == AB_SHED_SKIN
                         || ai_mon.ability == AB_HYDRATION);
        int recover_score = has_cure ? 8 : 7;
        ScoreDistC out;
        if (p_true > 0) out.push_back({recover_score, p_true});
        if (p_false > 0) out.push_back({5, p_false});
        if (out.empty()) out.push_back({5, 1.0});
        return out;
    }

    // --- Hazards ---
    if (md.tags & TAG_HAZARD) {
        return dist_hazard(state, ai_idx, move_id);
    }

    // --- Screens ---
    if (md.tags & TAG_SCREEN) {
        return dist_screen(state, ai_idx, move_id);
    }

    // --- Powder moves ---
    if (md.tags & TAG_POWDER) {
        for (int32_t t : pl_mon.types) if (t == TYPE_GRASS) return {{-50, 1.0}};
        if (pl_mon.ability == AB_OVERCOAT || pl_mon.item == ITM_SAFETY_GOGGLES)
            return {{-50, 1.0}};
    }

    // --- Paralysis ---
    if (ai_set_contains(PARALYSIS_MOVES, N_PARALYSIS_MOVES, move_id)) {
        return dist_paralysis(state, ai_idx, move_id);
    }

    // --- Will-O-Wisp ---
    if (move_id == MV_WILL_O_WISP) {
        return dist_will_o_wisp(state, ai_idx);
    }

    // --- Poison ---
    if (ai_set_contains(POISON_INFLICT_MOVES, N_POISON_INFLICT_MOVES, move_id)) {
        return dist_poison_move(state, ai_idx, move_id);
    }

    // --- Substitute ---
    if (move_id == MV_SUBSTITUTE) {
        if (ai_mon.hp * 100 / ai_mon.max_hp <= 50) return {{-40, 1.0}};
        if (pl_mon.ability == AB_INFILTRATOR) return {{-40, 1.0}};
        if (ai_mon.volatiles & VOL_SUBSTITUTE) return {{-40, 1.0}};
        return {{6, 1.0}};
    }

    // --- Belly Drum ---
    if (move_id == MV_BELLY_DRUM) {
        if (ai_mon.stage0 >= 6 || ai_mon.hp <= ai_mon.max_hp / 2) return {{-40, 1.0}};
        if (is_incapacitated(pl_mon)) return {{9, 1.0}};
        int32_t post_drum_hp = ai_mon.max_hp / 2;
        if (ai_mon.item == ITM_SITRUS_BERRY) post_drum_hp += ai_mon.max_hp / 4;
        post_drum_hp = std::min(post_drum_hp, ai_mon.max_hp);
        bool threatened_after = false;
        for (int slot = 0; slot < 4; ++slot) {
            int32_t mid = move_id_at(pl_mon, slot);
            if (mid == MV_NONE) continue;
            if (move_pp_at(pl_mon, slot) == 0) continue;
            const MoveData* mdp2 = ai_move_data_get(mid);
            if (!mdp2 || mdp2->base_power == 0) continue;
            int32_t dmg = cpp_expected_damage(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C,
                                              -1, false, -1);
            if (dmg >= post_drum_hp) { threatened_after = true; break; }
        }
        return threatened_after ? ScoreDistC{{6, 0.5}, {4, 0.5}} : ScoreDistC{{8, 1.0}};
    }

    // --- Shell Smash: block if Atk stage already raised ---
    if (move_id == MV_SHELL_SMASH) {
        if (ai_mon.stage0 >= 1 || ai_mon.stage2 >= 6) return {{-20, 1.0}};
        // Fall through to offensive setup
    }

    // --- Focus Energy / Laser Focus ---
    if (move_id == MV_FOCUS_ENERGY || move_id == MV_LASER_FOCUS) {
        bool already_active;
        if (move_id == MV_FOCUS_ENERGY) {
            already_active = (ai_mon.crit_stage >= 2);
        } else {
            already_active = has_timed_volatile(ai_mon, VE_LASER_FOCUS);
        }
        if (already_active) return {{-40, 1.0}};
        if (pl_mon.ability == AB_SHELL_ARMOR || pl_mon.ability == AB_BATTLE_ARMOR)
            return {{-40, 1.0}};
        if (player_can_ko_ai(state, ai_idx)
            && ai_mon.item != ITM_FOCUS_SASH
            && !(ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp))
            return {{-40, 1.0}};
        // Crit incentive
        bool has_crit = (ai_mon.ability == AB_SUPER_LUCK || ai_mon.ability == AB_SNIPER
                         || ai_mon.item == ITM_SCOPE_LENS);
        if (!has_crit) {
            for (int slot = 0; slot < 4; ++slot)
                if (ai_set_contains(HIGH_CRIT_MOVES, N_HIGH_CRIT_MOVES, move_id_at(ai_mon, slot))) {
                    has_crit = true; break;
                }
        }
        return has_crit ? ScoreDistC{{14, 0.25}, {7, 0.75}} : ScoreDistC{{6, 1.0}};
    }

    // --- Speed setup ---
    if (ai_set_contains(SPEED_SETUP_MOVES, N_SPEED_SETUP_MOVES, move_id)) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::SPEED);
    }

    // --- Nasty Plot / Tail Glow / Work Up: SpAtk stage >= 2 penalty ---
    if (move_id == MV_NASTY_PLOT || move_id == MV_TAIL_GLOW || move_id == MV_WORK_UP) {
        if (pl_mon.ability == AB_UNAWARE) return {{-40, 1.0}};
        ScoreDistC base_dist_np = dist_setup(state, ai_idx, SetupKind::OFFENSIVE);
        if (ai_mon.stage2 >= 2) {
            for (auto& [s, p] : base_dist_np) s -= 1;
        }
        return base_dist_np;
    }

    // --- Coaching ---
    if (move_id == MV_COACHING) {
        if (state.format != FMT_DOUBLES) return {{-20, 1.0}};
        const SideState& ai_side = side_at(state, ai_idx);
        const PokemonState* partner = nullptr;
        for (size_t pi = 1; pi < ai_side.active_indices.size(); ++pi) {
            int pslot = ai_side.active_indices[pi];
            if (!ai_side.team[pslot].fainted) { partner = &ai_side.team[pslot]; break; }
        }
        if (!partner || partner->ability == AB_CONTRARY) return {{-20, 1.0}};
        int score = 6;
        for (int i : {0, 1}) {  // Atk, Def stages
            int stage = (i == 0) ? partner->stage0 : partner->stage1;
            if (stage < 2) score += 1 - stage;
        }
        return {{score, 0.20}, {score + 1, 0.80}};
    }

    // --- Offensive setup ---
    // Shell Smash falls through here after the stat-stage check above
    bool is_offensive_setup = (move_id == MV_SHELL_SMASH)
        || ai_set_contains(OFFENSIVE_SETUP_MOVES, N_OFFENSIVE_SETUP_MOVES, move_id)
        || ((md.tags & TAG_SETUP) && (int32_t)md.category == CAT_STATUS && (int32_t)md.target == TGT_SELF);
    if (is_offensive_setup) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::OFFENSIVE);
    }

    // --- Defensive setup ---
    if (ai_set_contains(DEFENSIVE_SETUP_MOVES, N_DEFENSIVE_SETUP_MOVES, move_id)) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::DEFENSIVE);
    }

    // --- Tailwind ---
    if (move_id == MV_TAILWIND) return dist_tailwind(state, ai_idx);

    // --- Trick Room ---
    if (move_id == MV_TRICK_ROOM) return dist_trick_room(state, ai_idx);

    // --- Terrain ---
    if (ai_set_contains(TERRAIN_MOVES, N_TERRAIN_MOVES, move_id)) {
        return dist_terrain(state, ai_idx);
    }

    // --- STATUS-branch special handlers ---
    return dist_status_special(state, ai_idx, move_id, ai_mon, pl_mon, ai_fst);
}

// ---------------------------------------------------------------------------
// Public: cpp_blend_damage_dist
// ---------------------------------------------------------------------------

ScoreDistC cpp_blend_damage_dist(const BattleState& state, int ai_idx, const ExecAction& action,
                                 double p_kill, double p_nokill, bool ai_fst) {
    double p_none = std::max(0.0, 1.0 - p_kill - p_nokill);

    // Build components in kill → nokill → none order (mirrors Python list order)
    struct Component { double w; ScoreDistC dist; };
    std::vector<Component> components;
    if (p_kill > 0)
        components.push_back({p_kill, cpp_dist_action(state, ai_idx, action, 1.0, true, ai_fst)});
    if (p_nokill > 0)
        components.push_back({p_nokill, cpp_dist_action(state, ai_idx, action, 1.0, false, ai_fst)});
    if (p_none > 0)
        components.push_back({p_none, cpp_dist_action(state, ai_idx, action, 0.0, false, ai_fst)});

    // Merge into sorted map (std::map preserves insertion order for same key — we use map for
    // accumulation, then convert to sorted vector). Same semantics as Python dict merge.
    std::map<int32_t, double> merged;
    for (const auto& comp : components) {
        for (auto [s, p] : comp.dist) {
            merged[s] += comp.w * p;
        }
    }

    ScoreDistC result;
    result.reserve(merged.size());
    for (auto [s, p] : merged) result.push_back({s, p});
    return result;
}

// ---------------------------------------------------------------------------
// Stage 3: switch scoring constants
// ---------------------------------------------------------------------------

static constexpr int32_t SP_DITTO      = 132;
static constexpr int32_t SP_WYNAUT     = 360;
static constexpr int32_t SP_WOBBUFFET  = 202;

// ---------------------------------------------------------------------------
// Public: cpp_post_ko_switch_score
// ---------------------------------------------------------------------------

int cpp_post_ko_switch_score(const PokemonState& bench, const PokemonState& player_active,
                             const BattleState& state) {
    int score = 0;

    // Ditto: +2 additive (before general scoring)
    if (bench.species == SP_DITTO)
        score += 2;

    // Wynaut / Wobbuffet: +2 unless bench_slower AND player_ohkos → +0
    if (bench.species == SP_WYNAUT || bench.species == SP_WOBBUFFET) {
        int32_t bench_spd  = cpp_effective_stat(bench, 5);
        int32_t player_spd = cpp_effective_stat(player_active, 5);
        bool bench_slower  = bench_spd <= player_spd;
        int32_t best_pl_mv = cpp_ai_best_damage_move(player_active, bench, state,
                                                     MAX_LUCK_C, /*check_pp=*/false,
                                                     /*rollout_max_bp=*/true);
        bool player_ohkos = (best_pl_mv != MV_NONE)
            && cpp_ai_can_ko(player_active, best_pl_mv, bench, state,
                             MAX_LUCK_C, /*rollout_max_bp=*/true);
        if (!(bench_slower && player_ohkos))
            score += 2;
        // else +0 from this block
    }

    // General 7-tier scoring (mirrors Python lines 1513-1553)
    int32_t bench_spd  = cpp_effective_stat(bench, 5);
    int32_t player_spd = cpp_effective_stat(player_active, 5);
    bool bench_faster  = bench_spd > player_spd;  // strict: ties are NOT faster

    int32_t best_bench_mv = cpp_ai_best_damage_move(bench, player_active, state,
                                                    MAX_LUCK_C, /*check_pp=*/false,
                                                    /*rollout_max_bp=*/true);
    int32_t best_pl_mv    = cpp_ai_best_damage_move(player_active, bench, state,
                                                    MAX_LUCK_C, /*check_pp=*/false,
                                                    /*rollout_max_bp=*/true);

    bool bench_ohkos = (best_bench_mv != MV_NONE)
        && cpp_ai_can_ko(bench, best_bench_mv, player_active, state,
                         MAX_LUCK_C, /*rollout_max_bp=*/true);
    bool player_ohkos = (best_pl_mv != MV_NONE)
        && cpp_ai_can_ko(player_active, best_pl_mv, bench, state,
                         MAX_LUCK_C, /*rollout_max_bp=*/true);

    // Use max_hp if set, otherwise fall back to stat_hp (mirrors Python: max_hp = stats[0] when None).
    int32_t player_max_hp = player_active.has_max_hp ? player_active.max_hp : player_active.stat_hp;
    int32_t bench_max_hp  = bench.has_max_hp         ? bench.max_hp         : bench.stat_hp;

    double bench_dmg_pct = 0.0;
    if (best_bench_mv != MV_NONE && player_max_hp > 0) {
        int32_t dmg = cpp_expected_damage(bench, best_bench_mv, player_active, state,
                                          MAX_LUCK_C, /*roll_index=*/-1,
                                          /*rollout_max_bp=*/true, /*hit_count_override=*/-1);
        bench_dmg_pct = (double)dmg / player_max_hp;
    }
    double player_dmg_pct = 0.0;
    if (best_pl_mv != MV_NONE && bench_max_hp > 0) {
        int32_t dmg = cpp_expected_damage(player_active, best_pl_mv, bench, state,
                                          MAX_LUCK_C, /*roll_index=*/-1,
                                          /*rollout_max_bp=*/true, /*hit_count_override=*/-1);
        player_dmg_pct = (double)dmg / bench_max_hp;
    }
    bool bench_deals_more_pct = bench_dmg_pct > player_dmg_pct;

    if (bench_faster && bench_ohkos)
        return score + 5;
    if (!bench_faster && bench_ohkos && !player_ohkos)
        return score + 4;
    if (bench_faster && bench_deals_more_pct)
        return score + 3;
    if (!bench_faster && bench_deals_more_pct)
        return score + 2;
    if (bench_faster)
        return score + 1;
    if (!bench_faster && player_ohkos)
        return score + (-1);
    return score + 0;
}

// ---------------------------------------------------------------------------
// Public: cpp_cond2_valid_slots
// ---------------------------------------------------------------------------

std::set<int> cpp_cond2_valid_slots(const BattleState& state, int ai_idx) {
    const SideState& side    = side_at(state, ai_idx);
    int active_slot          = side.active_indices[0];
    const PokemonState& pl   = active_mon(state, 1 - ai_idx);
    int32_t pl_spe           = cpp_effective_stat(pl, 5);

    bool found_faster = false;  // bug: once true, stays true for later (slower) mons
    std::set<int> valid;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        const PokemonState& mon = side.team[slot];
        if (slot == active_slot || mon.fainted)
            continue;

        int32_t bench_spe = cpp_effective_stat(mon, 5);
        bool is_faster    = bench_spe > pl_spe;

        if (is_faster || found_faster) {
            // Faster-branch (or bug-propagated): valid iff player doesn't OHKO
            int32_t best_pl_mv = cpp_ai_best_damage_move(pl, mon, state, MAX_LUCK_C,
                                                         /*check_pp=*/false,
                                                         /*rollout_max_bp=*/true);
            bool player_ohkos = (best_pl_mv != MV_NONE)
                && cpp_ai_can_ko(pl, best_pl_mv, mon, state,
                                 MAX_LUCK_C, /*rollout_max_bp=*/true);
            if (!player_ohkos)
                valid.insert(slot);
            if (is_faster)
                found_faster = true;  // bug: subsequent mons also treated as faster
        } else {
            // Slower-branch: valid if player can't 2HKO (dmg*2 < mon.hp, or no player move)
            int32_t best_pl_mv = cpp_ai_best_damage_move(pl, mon, state, MAX_LUCK_C,
                                                         /*check_pp=*/false,
                                                         /*rollout_max_bp=*/true);
            if (best_pl_mv == MV_NONE) {
                valid.insert(slot);
            } else {
                int32_t dmg = cpp_expected_damage(pl, best_pl_mv, mon, state,
                                                  MAX_LUCK_C, /*roll_index=*/-1,
                                                  /*rollout_max_bp=*/true,
                                                  /*hit_count_override=*/-1);
                if ((int64_t)dmg * 2 < (int64_t)mon.hp)
                    valid.insert(slot);
            }
        }
    }
    return valid;
}

// ---------------------------------------------------------------------------
// Public: cpp_has_valid_switch_candidate
// ---------------------------------------------------------------------------

bool cpp_has_valid_switch_candidate(const BattleState& state, int ai_idx) {
    return !cpp_cond2_valid_slots(state, ai_idx).empty();
}

// ---------------------------------------------------------------------------
// Public: cpp_select_voluntary_switch_target
// ---------------------------------------------------------------------------

int cpp_select_voluntary_switch_target(const BattleState& state, int ai_idx) {
    std::set<int> valid_slots = cpp_cond2_valid_slots(state, ai_idx);
    const SideState& side     = side_at(state, ai_idx);
    const PokemonState& pl    = active_mon(state, 1 - ai_idx);

    int best_score = 0;
    bool found     = false;
    int best_slot  = -1;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        if (valid_slots.find(slot) == valid_slots.end())
            continue;
        int sc = cpp_post_ko_switch_score(side.team[slot], pl, state);
        if (!found || sc > best_score) {
            best_score = sc;
            best_slot  = slot;
            found      = true;
        }
    }

    if (!found)
        throw NoSwitchCandidate("No Cond2-valid switch target found");
    return best_slot;
}

// ---------------------------------------------------------------------------
// Public: cpp_select_post_ko_switch
// ---------------------------------------------------------------------------

int cpp_select_post_ko_switch(const BattleState& state, int ai_idx) {
    const SideState& side  = side_at(state, ai_idx);
    int active_slot        = side.active_indices[0];
    const PokemonState& pl = active_mon(state, 1 - ai_idx);

    int best_score = 0;
    bool found     = false;
    int best_slot  = -1;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        if (slot == active_slot)
            continue;
        const PokemonState& mon = side.team[slot];
        if (mon.fainted)
            continue;
        int sc = cpp_post_ko_switch_score(mon, pl, state);
        if (!found || sc > best_score) {
            best_score = sc;
            best_slot  = slot;
            found      = true;
        }
    }

    if (!found)
        throw NoSwitchCandidate("No valid switch target: all bench mons are fainted");
    return best_slot;
}
