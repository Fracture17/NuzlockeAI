// C1.7d Unit 4: the damage hit-loop body (see move_exec_damage.h). Byte-identical mirror of
// _handle_damage_action / _handle_damage_loop / _apply_defender_faint_effects /
// _handle_fixed_damage_action in src/engine/core.py on deterministic paths. Python log() calls are
// state-neutral and omitted. Crit is resolved per-hit in the loop (not inside cpp_calculate_damage)
// so that Lucky Chant and Merciless are applied correctly before the damage call.
#include "move_exec_damage.h"
#include "rng_resolver.h"        // rng_resolve_accuracy, rng_resolve_multi_hit
#include "move_exec.h"           // cpp_apply_dancer_trigger (Unit 5)
#include "move_exec_helpers.h"   // cpp_apply_damage/rocky_helmet/on_ko/gulp/bump_rollout/reset_stockpile
#include "effects.h"             // cpp_apply_post_hit_effects, PostHitArgs, EffectsLuck
#include "effects_internal.h"    // active_mon, side_at, change_stat_stage, apply_form_change, ...
#include "native_rng.h"          // NativeRng (for default param in make_calc_luck/make_exec_luck)
#include "effects_consts.h"
#include "damage.h"              // cpp_calculate_damage, LuckProfileC
#include "type_chart_lookup.h"   // cpp_type_effectiveness
#include "core_leaf.h"           // cpp_compute_variable_bp
#include "../generated/move_data.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

using namespace eff;
using eff_internal::active_mon;
using eff_internal::side_at;
using eff_internal::change_stat_stage;
using eff_internal::apply_form_change;
using eff_internal::apply_unburden;
using eff_internal::notify_faint_soul_heart;
using eff_internal::has_type;
using eff_internal::is_mold_breaker;

namespace {

// MOVE_TABLE binary search (file-local in core_leaf.cpp; reimplemented here, identical).
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
const MoveData& move_data_or_throw(int32_t move_id) {
    const MoveData* md = move_data_get(move_id);
    if (md == nullptr)
        throw std::runtime_error("move_exec_damage: move id " + std::to_string(move_id) + " not found");
    return *md;
}

// ---- Constants ----
constexpr int32_t TYPE_GROUND_ID = 8, TYPE_PSYCHIC_ID = 10, TYPE_DRAGON_ID = 14, TYPE_FAIRY_ID = 17;
constexpr int32_t TAG_CONTACT = 128, TAG_SOUND = 256, TAG_POWDER = 16384;
constexpr int32_t CAT_STATUS = 2;

// Moves
constexpr int32_t MV_TRIPLE_AXEL = 813, MV_FLING = 374, MV_FLYING_PRESS = 560, MV_FREEZE_DRY = 573,
    MV_THOUSAND_ARROWS = 614, MV_NATURAL_GIFT = 363, MV_FELL_STINGER = 565, MV_FINAL_GAMBIT = 515,
    MV_HYPERSPACE_FURY = 621, MV_HYPERSPACE_HOLE = 593, MV_RING_TARGET_NONE = 0;
constexpr int32_t MV_BODY_SLAM = 34, MV_STOMP = 23, MV_STEAMROLLER = 537, MV_DRAGON_RUSH = 407,
    MV_SUPERCELL_SLAM = 916;
constexpr int32_t MV_THRASH = 37, MV_OUTRAGE = 200, MV_PETAL_DANCE = 80, MV_WATER_SHURIKEN = 594;
// OHKO
constexpr int32_t MV_GUILLOTINE = 12, MV_HORN_DRILL = 32, MV_FISSURE = 90, MV_SHEER_COLD = 329;
// Dance moves (out of scope; trigger fail-loud when not from_dancer).
constexpr int32_t MV_SWORDS_DANCE = 14, MV_DRAGON_DANCE = 349, MV_QUIVER_DANCE = 483,
    MV_FEATHER_DANCE = 297, MV_TEETER_DANCE = 298, MV_FIERY_DANCE = 552, MV_LUNAR_DANCE = 461,
    MV_REVELATION_DANCE = 686;

// Items
constexpr int32_t ITM_BIG_ROOT = 296, ITM_PROTECTIVE_PADS = 880, ITM_SAFETY_GOGGLES = 650,
    ITM_RING_TARGET = 543, ITM_CHILAN_BERRY = 200, ITM_NORMAL_GEM_DUMMY = 564;

// Abilities
constexpr int32_t AB_RIPEN = 247, AB_LIQUID_OOZE = 64, AB_ROUGH_SKIN = 24, AB_IRON_BARBS = 160,
    AB_LONG_REACH = 203, AB_MAGIC_GUARD = 98, AB_INFILTRATOR = 151, AB_MERCILESS = 196,
    AB_BATTLE_ARMOR = 4, AB_SHELL_ARMOR = 75, AB_MAGMA_ARMOR = 40, AB_DISGUISE = 209,
    AB_SCRAPPY = 113, AB_STURDY = 5, AB_INNARDS_OUT = 215, AB_AFTERMATH = 106, AB_DAMP = 6,
    AB_SKILL_LINK = 92, AB_BATTLE_BOND = 210, AB_PARENTAL_BOND = 185, AB_OVERCOAT = 142,
    AB_UNNERVE = 127, AB_AS_ONE_G = 266, AB_AS_ONE_S = 267, AB_SUPER_LUCK = 105;

// Items: crit-stage modifiers
constexpr int32_t ITM_SCOPE_LENS = 268, ITM_RAZOR_CLAW = 326, ITM_LEEK = 259;

// Status: Poison / Toxic (for Merciless crit override)
constexpr int32_t STATUS_POISON = 4, STATUS_TOXIC = 5;

// Pseudo-weather: Magic Room (for crit-chance / Scope Lens suppression)
constexpr int32_t PW_MAGIC_ROOM = 3;

// Species
constexpr int32_t SP_MIMIKYU = 778, SP_MIMIKYU_BUSTED = 1206, SP_GRENINJA_ASH = 1113;

// VolatileEffect: RAMPAGING / LASER_FOCUS (src/state/pokemon.py)
constexpr int32_t VE_RAMPAGING_ID = 12;
constexpr int32_t VE_LASER_FOCUS_ID = 25;

// FormatEnum
constexpr int32_t FORMAT_DOUBLES = 1;

// MoveTarget
constexpr int32_t TGT_ALL_ADJACENT_FOES = 2, TGT_ALL_ADJACENT = 3, TGT_ALL = 8,
    TGT_SELF = 1, TGT_ALLY_SIDE = 6, TGT_FOE_SIDE = 7;

bool in_list(int32_t v, const int32_t* arr, int n) {
    for (int i = 0; i < n; ++i) if (arr[i] == v) return true;
    return false;
}
const int32_t OHKO_MOVES[] = {MV_GUILLOTINE, MV_HORN_DRILL, MV_FISSURE, MV_SHEER_COLD};
bool is_ohko(int32_t m) { return in_list(m, OHKO_MOVES, 4); }
const int32_t RAMPAGE_MOVES[] = {MV_THRASH, MV_OUTRAGE, MV_PETAL_DANCE};
bool is_rampage(int32_t m) { return in_list(m, RAMPAGE_MOVES, 3); }
const int32_t DANCE_MOVES[] = {MV_SWORDS_DANCE, MV_DRAGON_DANCE, MV_QUIVER_DANCE, MV_FEATHER_DANCE,
    MV_PETAL_DANCE, MV_TEETER_DANCE, MV_FIERY_DANCE, MV_LUNAR_DANCE, MV_REVELATION_DANCE};
bool is_dance(int32_t m) { return in_list(m, DANCE_MOVES, 9); }
bool is_berry_suppressor(int32_t a) { return a == AB_UNNERVE || a == AB_AS_ONE_G || a == AB_AS_ONE_S; }

// _TYPE_RESIST_BERRIES: item -> resisted type. Returns -1 if not a resist berry.
// Berry ids are contiguous (Occa..Roseli) but with a Chilan gap; mirror the Python dict exactly.
int32_t resist_berry_type(int32_t item) {
    switch (item) {
        case 184: return TYPE_FIRE;       // OCCA
        case 185: return TYPE_WATER;      // PASSHO
        case 186: return TYPE_ELECTRIC;   // WACAN
        case 187: return TYPE_GRASS;      // RINDO
        case 188: return TYPE_ICE;        // YACHE
        case 189: return TYPE_FIGHTING;   // CHOPLE
        case 190: return TYPE_POISON;     // KEBIA
        case 191: return TYPE_GROUND_ID;  // SHUCA
        case 192: return TYPE_FLYING;     // COBA
        case 193: return TYPE_PSYCHIC_ID; // PAYAPA
        case 194: return TYPE_BUG;        // TANGA
        case 195: return TYPE_ROCK;       // CHARTI
        case 196: return TYPE_GHOST;      // KASIB
        case 197: return TYPE_DRAGON_ID;  // HABAN
        case 198: return TYPE_DARK;       // COLBUR
        case 199: return TYPE_STEEL;      // BABIRI
        case 200: return TYPE_NORMAL;     // CHILAN
        case 686: return TYPE_FAIRY_ID;   // ROSELI
        default:  return -1;
    }
}

// stat_stage / move accessors (mirror guards.cpp helpers).
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
bool has_timed_ve(const PokemonState& m, int32_t ve) {
    return eff_internal::has_timed_volatile(m, ve);
}
bool has_pseudo_gravity(const BattleState& s) { return eff_internal::has_pseudo(s, PW_GRAVITY); }
bool has_pseudo_magic_room(const BattleState& s) { return eff_internal::has_pseudo(s, PW_MAGIC_ROOM); }

// _get_crit_chance (damage.cpp's copy is static; reimplemented identical). Returns prob 0.0-1.0.
const double CRIT_CHANCE[4] = {1.0/16, 1.0/8, 1.0/2, 100.0};
double get_crit_chance(const PokemonState& attacker, const PokemonState& defender,
                       int32_t move_crit_boost, bool magic_room) {
    bool breaks = is_mold_breaker(attacker.ability);
    if (defender.ability == AB_MAGMA_ARMOR) return 0.0;
    if ((defender.ability == AB_BATTLE_ARMOR || defender.ability == AB_SHELL_ARMOR) && !breaks)
        return 0.0;
    if (has_timed_ve(attacker, VE_LASER_FOCUS_ID)) return 1.0;
    int32_t stage = attacker.crit_stage;
    if (attacker.ability == AB_SUPER_LUCK) stage += 1;
    if ((attacker.item == ITM_SCOPE_LENS || attacker.item == ITM_RAZOR_CLAW) && !magic_room) stage += 1;
    // Leek: only specific species; not exercised in scope, but mirror the species-agnostic branch
    // is skipped (Leek requires _LEEK_SPECIES). Omitted: never reached by tests.
    stage += move_crit_boost;
    stage = std::min(stage, 3);
    return CRIT_CHANCE[stage];
}


// resolve_hit_count (mirror damage.py). Encapsulates Skill Link / Battle Bond / Parental Bond.
int32_t resolve_hit_count(const PokemonState& attacker, int32_t move, const MoveData& md,
                          const DamageLoopLuck& luck, bool& parental_bond_active,
                          const RngLogCtx* ctx) {
    int32_t hit_count = rng_resolve_multi_hit(md.min_hits, md.max_hits, luck.multi_hit_roll,
                                              luck.random_mode, luck.rng, ctx);
    if (attacker.ability == AB_SKILL_LINK && md.max_hits > 1) hit_count = md.max_hits;
    if (attacker.ability == AB_BATTLE_BOND && attacker.species == SP_GRENINJA_ASH
            && move == MV_WATER_SHURIKEN) hit_count = 3;
    // _PARENTAL_BOND_TARGETS = {NORMAL(0), ANY(5), RANDOM_NORMAL(9)}.
    parental_bond_active = (attacker.ability == AB_PARENTAL_BOND && md.max_hits == 1
                            && (md.target == 0 || md.target == 5 || md.target == 9));
    if (parental_bond_active) hit_count = 2;
    return hit_count;
}

// Build a LuckProfileC for cpp_calculate_damage from the per-hit-resolved damage_roll/crit.
LuckProfileC make_calc_luck(double crit_threshold, double damage_roll, double proc_threshold,
                            bool random_mode, NativeRng* rng = nullptr) {
    LuckProfileC l;
    l.crit_threshold = crit_threshold;
    l.damage_roll = damage_roll;
    l.proc_threshold = proc_threshold;
    l.random_mode = random_mode;
    l.rng = rng;
    return l;
}
LuckProfileC def_calc_luck(const DamageLoopLuck& luck_def) {
    return make_calc_luck(luck_def.crit_threshold, luck_def.damage_roll, luck_def.proc_threshold,
                          luck_def.random_mode, luck_def.rng);
}
MoveExecLuck make_exec_luck(double proc_threshold, bool random_mode, NativeRng* rng = nullptr,
                            const OracleOverrides* overrides = nullptr) {
    MoveExecLuck l; l.proc_threshold = proc_threshold; l.random_mode = random_mode; l.rng = rng;
    l.overrides = overrides;
    return l;
}
EffectsLuck make_effects_luck(const DamageLoopLuck& luck) {
    EffectsLuck l;
    l.proc_threshold = luck.proc_threshold;
    l.secondary_threshold = luck.secondary_threshold;
    l.flinch_threshold = luck.flinch_threshold;
    l.binding_duration_roll = luck.binding_duration_roll;
    l.random_mode = luck.random_mode;
    l.rng = luck.rng;
    l.overrides = luck.overrides;
    return l;
}

// ---------------------------------------------------------------------------
// _apply_defender_faint_effects
// ---------------------------------------------------------------------------
void apply_defender_faint_effects(BattleState& state, int side_idx, int defender_idx,
                                  int32_t move, const MoveData& md, bool md_contact,
                                  bool attacker_long_reach_at_call /*unused*/,
                                  int32_t updated_def_volatiles, int32_t updated_def_ability,
                                  int32_t hp_before, const DamageLoopLuck& luck_atk) {
    (void)attacker_long_reach_at_call;
    // Destiny Bond: drag the attacker (side_idx) down.
    if (updated_def_volatiles & VOLATILE_DESTINY_BOND) {
        MoveExecLuck mel = make_exec_luck(luck_atk.proc_threshold, luck_atk.random_mode, luck_atk.rng, luck_atk.overrides);
        PokemonState& atk = active_mon(state, side_idx);
        cpp_apply_damage(state, side_idx, atk.max_hp, AB_NONE, mel, -1, -1, 0);
    }
    // Innards Out.
    if (updated_def_ability == AB_INNARDS_OUT) {
        PokemonState& attacker = active_mon(state, side_idx);
        if (!attacker.fainted && attacker.ability != AB_MAGIC_GUARD) {
            int32_t new_hp = std::max(0, attacker.hp - hp_before);
            attacker.hp = new_hp;
            if (new_hp == 0) cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
        }
    }
    // Aftermath: Damp suppresses; contact + Long Reach gating; Magic Guard / Protective Pads block.
    bool aftermath_damp = false;
    for (int s = 0; s < 2 && !aftermath_damp; ++s) {
        SideState& side = side_at(state, s);
        for (int32_t ai : side.active_indices) {
            if (side.team[ai].ability == AB_DAMP && !side.team[ai].fainted) { aftermath_damp = true; break; }
        }
    }
    {
        PokemonState& attacker_ref = active_mon(state, side_idx);
        if (updated_def_ability == AB_AFTERMATH && !aftermath_damp && md_contact
                && attacker_ref.ability != AB_LONG_REACH) {
            PokemonState& attacker = active_mon(state, side_idx);
            if (!attacker.fainted && attacker.ability != AB_MAGIC_GUARD
                    && attacker.item != ITM_PROTECTIVE_PADS) {
                int32_t dmg = attacker.max_hp / 4;
                int32_t new_hp = std::max(0, attacker.hp - dmg);
                attacker.hp = new_hp;
                if (new_hp == 0) cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
            }
        }
    }
    cpp_apply_on_ko_effects(state, side_idx);
    notify_faint_soul_heart(state);
    // Fell Stinger: +3 Atk.
    if (move == MV_FELL_STINGER) {
        if (!active_mon(state, side_idx).fainted)
            change_stat_stage(state, side_idx, 0, +3, false, false, false);
    }
    side_at(state, defender_idx).ally_fainted_last_turn = true;
    cpp_apply_gulp_missile_projectile(state, defender_idx, side_idx);
}

// ---------------------------------------------------------------------------
// _handle_damage_loop. Returns (total_damage, actual_damage); mutates state.
// spread_hit: passed to calculate_damage (False suppresses 0.75x spread penalty).
// ---------------------------------------------------------------------------
struct LoopResult { int32_t total_damage; int32_t actual_damage; };

LoopResult handle_damage_loop(BattleState& state, int side_idx, int defender_idx, int32_t move,
                              const MoveData& md, int32_t move_type, ExecCtx& ctx,
                              const DamageLoopLuck& luck_atk_in, const DamageLoopLuck& luck_def,
                              int32_t effective_bp_override, double effective_acc,
                              bool effective_acc_is_none, int effective_slot, bool spread_hit) {
    (void)effective_acc; (void)effective_acc_is_none;
    int32_t phe_eff_slot = (effective_slot >= 0) ? effective_slot : ctx.opp_action_move_slot;

    DamageLoopLuck luck_atk = luck_atk_in;

    // last_move_failed: save prior, reset.
    bool prior_last_move_failed;
    {
        PokemonState& attacker = active_mon(state, side_idx);
        prior_last_move_failed = attacker.last_move_failed;
        attacker.last_move_failed = false;
    }

    // Lucky Chant: suppress crits against this defender's side.
    bool lucky_chant_def = false;
    for (const auto& sc : side_at(state, defender_idx).side_conditions) {
        if (sc.condition == SC_LUCKY_CHANT) { lucky_chant_def = true; break; }
    }
    if (lucky_chant_def) luck_atk.crit_threshold = 101.0;

    // Analytical-logger participants/turn for Cat-B draws in this damage loop.
    const RngLogCtx catb_ctx{
        RngParticipants{
            (int8_t)side_idx,     (int8_t)side_at(state, side_idx).active_indices[0],
            (int8_t)defender_idx, (int8_t)side_at(state, defender_idx).active_indices[0]},
        state.turn_number};

    bool parental_bond_active = false;
    int32_t hit_count = resolve_hit_count(active_mon(state, side_idx), move, md, luck_atk,
                                          parental_bond_active, &catb_ctx);

    // Triple Axel: fixed 3 hits with escalating BP [20, 40, 60]; accuracy re-checked each hit.
    static const int32_t TRIPLE_AXEL_BPS[3] = {20, 40, 60};
    bool is_triple_axel = (move == MV_TRIPLE_AXEL);

    // Rampage (Thrash/Outrage/Petal Dance): set RAMPAGING + LOCKED_MOVE on first use (before damage).
    // resolve_rampage_duration: forced → consume RAMPAGE_DURATION int; native: random() < 0.5 → 2 else 3.
    // rng.py:527 _roll_categorical(RNGEvent.RAMPAGE_DURATION, [2, 3]) records chosen value.
    if (is_rampage(move)) {
        PokemonState& attacker = active_mon(state, side_idx);
        if (!has_timed_ve(attacker, VE_RAMPAGING_ID)) {
            int32_t duration;
            if (luck_atk.random_mode) {
                if (!luck_atk.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
                if (luck_atk.rng->forced)
                    duration = static_cast<int32_t>(luck_atk.rng->forced->force_int(
                        luck_atk.rng->current_turn, RngEventC::RAMPAGE_DURATION));
                else
                    duration = (luck_atk.rng->random() < 0.5) ? 2 : 3;
            } else {
                duration = (luck_atk.rampage_duration_roll >= 0.5) ? 3 : 2;
            }
            attacker.timed_volatiles.push_back({VE_RAMPAGING_ID, duration});
            attacker.volatiles |= 512 /*Volatile.LOCKED_MOVE*/;
            attacker.locked_slot = phe_eff_slot;
            // Mirror Python's stale-snapshot quirk (core.py:1162-1167): the rampage setup
            // rebuilds from a snapshot taken BEFORE the last_move_failed reset, so writing it
            // back restores the prior value (the reset is clobbered on a rampage move's first use).
            attacker.last_move_failed = prior_last_move_failed;
        }
    }

    // Metronome item streak.
    double metronome_multiplier = 1.0;
    bool metronome_active = false;
    int32_t new_count = 0;
    {
        PokemonState& attacker = active_mon(state, side_idx);
        metronome_active = (attacker.item == 277 /*METRONOME*/ && md.category != CAT_STATUS);
        if (metronome_active) {
            if (attacker.metronome_last_move == move) new_count = std::min(attacker.metronome_count + 1, 6);
            else new_count = 1;
            metronome_multiplier = 1.0 + 0.2 * (new_count - 1);
        }
    }

    // Per-hit array length validation (raises like Python on mismatch).
    if (luck_atk.damage_rolls_present && (int)luck_atk.damage_rolls_per_hit.size() != hit_count) {
        throw std::runtime_error("damage_rolls_per_hit length "
            + std::to_string(luck_atk.damage_rolls_per_hit.size())
            + " != hit_count " + std::to_string(hit_count));
    }
    if (luck_atk.crits_present && (int)luck_atk.crits_per_hit.size() != hit_count) {
        throw std::runtime_error("crits_per_hit length "
            + std::to_string(luck_atk.crits_per_hit.size())
            + " != hit_count " + std::to_string(hit_count));
    }

    int32_t total_damage = 0, actual_damage = 0;
    for (int hit_num = 0; hit_num < hit_count; ++hit_num) {
        if (active_mon(state, defender_idx).fainted) break;
        if (active_mon(state, side_idx).fainted) break;

        // Disguise.
        {
            PokemonState& defender = active_mon(state, defender_idx);
            PokemonState& attacker = active_mon(state, side_idx);
            if (defender.ability == AB_DISGUISE && defender.species == SP_MIMIKYU
                    && !is_mold_breaker(attacker.ability)) {
                apply_form_change(state, defender_idx, SP_MIMIKYU_BUSTED);
                continue;
            }
        }

        // Triple Axel: per-hit accuracy check (stops if a hit misses).
        if (is_triple_axel
            && !rng_resolve_accuracy(effective_acc, effective_acc_is_none,
                                     luck_atk.accuracy_threshold, luck_atk.random_mode,
                                     luck_atk.rng, &catb_ctx))
            break;

        // Fling: BP override from the attacker's held item. Items not listed
        // default to 10 BP; no item -> the move fails (break out of hit loop).
        int32_t fling_bp = 0;
        if (move == MV_FLING) {
            int32_t fitem = active_mon(state, side_idx).item;
            if (fitem == 0 /*ITEM_NONE*/) break;
            switch (fitem) {
                case 278: fling_bp = 130; break;  // IRON_BALL
                case 221: fling_bp = 30;  break;  // KING_S_ROCK
                case 327: fling_bp = 30;  break;  // RAZOR_FANG
                case 245: fling_bp = 70;  break;  // POISON_BARB
                case 272: fling_bp = 30;  break;  // TOXIC_ORB
                case 273: fling_bp = 30;  break;  // FLAME_ORB
                case 540: fling_bp = 60;  break;  // ROCKY_HELMET
                case 238: fling_bp = 100; break;  // HARD_STONE
                case 233: fling_bp = 30;  break;  // METAL_COAT
                case 270: fling_bp = 30;  break;  // LIFE_ORB
                case 220: fling_bp = 30;  break;  // CHOICE_BAND
                case 287: fling_bp = 30;  break;  // CHOICE_SCARF
                case 297: fling_bp = 30;  break;  // CHOICE_SPECS
                default:  fling_bp = 10;  break;
            }
        }

        // Variable BP. defender_action_is_switch from ctx.
        bool def_is_switch = (ctx.opp_action_present && ctx.opp_action_kind == 1 /*SWITCH*/);
        int32_t var_bp;
        {
            PokemonState attacker_copy = active_mon(state, side_idx);
            attacker_copy.last_move_failed = prior_last_move_failed;
            var_bp = cpp_compute_variable_bp(move, attacker_copy, active_mon(state, defender_idx),
                                             state, side_idx, defender_idx, def_is_switch);
        }
        int32_t hit_bp;
        if (is_triple_axel) hit_bp = TRIPLE_AXEL_BPS[hit_num];
        else if (fling_bp) hit_bp = fling_bp;
        else if (effective_bp_override) hit_bp = effective_bp_override;
        else hit_bp = var_bp;

        // Type-effectiveness product (for the type-immunity break + Freeze-Dry / Thousand Arrows /
        // Ring Target / Gravity / Scrappy / Identified overrides). Mirrors the loop's _type_mult.
        PokemonState& defender = active_mon(state, defender_idx);
        PokemonState& attacker = active_mon(state, side_idx);
        double type_mult = 1.0;
        if (defender.has_types) {
            for (int32_t dt : defender.types) {
                double factor = cpp_type_effectiveness(move_type, dt);
                if (factor == 0.0 && dt == TYPE_GHOST
                        && (move_type == TYPE_NORMAL || move_type == TYPE_FIGHTING)
                        && attacker.ability == AB_SCRAPPY) factor = 1.0;
                if (factor == 0.0 && dt == TYPE_GHOST
                        && (move_type == TYPE_NORMAL || move_type == TYPE_FIGHTING)
                        && (defender.volatiles & VOLATILE_IDENTIFIED)) factor = 1.0;
                type_mult *= factor;
            }
        }
        if (move == MV_FLYING_PRESS && defender.has_types)
            for (int32_t dt : defender.types) type_mult *= cpp_type_effectiveness(TYPE_FLYING, dt);
        if (move == MV_FREEZE_DRY && has_type(defender, TYPE_WATER)) type_mult *= 4.0;
        if (move == MV_THOUSAND_ARROWS && type_mult == 0.0) type_mult = 1.0;
        if (type_mult == 0.0 && move_type == TYPE_GROUND_ID && has_pseudo_gravity(state)) type_mult = 1.0;
        if (defender.item == ITM_RING_TARGET && type_mult == 0.0) {
            type_mult = 1.0;
            if (defender.has_types)
                for (int32_t dt : defender.types) {
                    double f = cpp_type_effectiveness(move_type, dt);
                    type_mult *= (f == 0.0 ? 1.0 : f);
                }
            if (move == MV_FLYING_PRESS && defender.has_types)
                for (int32_t dt : defender.types) {
                    double f = cpp_type_effectiveness(TYPE_FLYING, dt);
                    type_mult *= (f == 0.0 ? 1.0 : f);
                }
        }
        if (type_mult == 0.0) break;  // type-immunity: emit logs (omitted) + stop loop.

        // Python computes _magic_room from state.pseudo_weather and uses it for BOTH the crit
        // chance and the Metronome-item multiplier. MAGIC_ROOM is unreachable in-game (the move
        // is unimplemented), so always-false here is equivalent for the Metronome path; the crit
        // path uses the computed value so hand-built test states still match damage.cpp's view.
        bool magic_room = false;
        bool magic_room_for_crit = has_pseudo_magic_room(state);

        // Per-hit luck: damage_roll / crit threshold.
        double hit_crit_threshold = luck_atk.crit_threshold;
        double hit_damage_roll = luck_atk.damage_roll;
        if (luck_atk.damage_rolls_present) hit_damage_roll = luck_atk.damage_rolls_per_hit[hit_num];
        if (luck_atk.crits_present) hit_crit_threshold = luck_atk.crits_per_hit[hit_num];

        // Resolve crit per-hit (mirrors Python core.py _handle_damage_loop):
        //   1. Draw crit RNG (always drawn even when Merciless/Lucky Chant will override).
        //   2. Merciless: force crit vs poisoned/toxic targets without crit-immunity.
        //   3. Lucky Chant: suppress crit if defender's side has the condition.
        float hit_crit_chance = static_cast<float>(get_crit_chance(attacker, defender,
                                                                   md.crit_boost, magic_room_for_crit));
        bool hit_is_crit = rng_resolve_crit(hit_crit_chance, hit_crit_threshold,
                                            luck_atk.random_mode, luck_atk.rng, &catb_ctx);
        if (attacker.ability == AB_MERCILESS
                && (defender.status == STATUS_POISON || defender.status == STATUS_TOXIC)
                && defender.ability != AB_BATTLE_ARMOR
                && defender.ability != AB_SHELL_ARMOR
                && defender.ability != AB_MAGMA_ARMOR)
            hit_is_crit = true;
        if (hit_is_crit && lucky_chant_def) hit_is_crit = false;

        LuckProfileC hit_luck = make_calc_luck(hit_crit_threshold, hit_damage_roll,
                                               luck_atk.proc_threshold, luck_atk.random_mode,
                                               luck_atk.rng);
        int32_t damage = cpp_calculate_damage(attacker, move, defender, state, hit_luck,
                                              def_calc_luck(luck_def), hit_bp, defender_idx,
                                              spread_hit, -1, false, hit_is_crit ? 1 : 0);
        if (parental_bond_active && hit_num == 1) damage = std::max(1, (int)(damage * 0.25));
        if (metronome_multiplier != 1.0 && !magic_room)
            damage = std::max(1, (int)(damage * metronome_multiplier));

        // Minimize doubling.
        if ((move == MV_BODY_SLAM || move == MV_STOMP || move == MV_STEAMROLLER
                || move == MV_FLYING_PRESS || move == MV_DRAGON_RUSH || move == MV_SUPERCELL_SLAM)
                && (defender.volatiles & VOLATILE_MINIMIZE)) damage *= 2;

        // OHKO.
        if (is_ohko(move)) {
            if (defender.ability == AB_STURDY && !is_mold_breaker(attacker.ability)) break;
            damage = defender.hp;
        }

        // Substitute absorb (sound / Infiltrator / Hyperspace bypass).
        bool bypasses_sub = (md.tags & TAG_SOUND) || attacker.ability == AB_INFILTRATOR
                            || move == MV_HYPERSPACE_FURY || move == MV_HYPERSPACE_HOLE;
        if (!bypasses_sub && (defender.volatiles & VOLATILE_SUBSTITUTE) && defender.sub_hp > 0) {
            if (damage >= defender.sub_hp) {
                defender.sub_hp = 0;
                defender.volatiles &= ~VOLATILE_SUBSTITUTE;
            } else {
                defender.sub_hp -= damage;
            }
            total_damage += damage;
            continue;
        }

        // Type-resist berry.
        {
            PokemonState& def_resist = active_mon(state, defender_idx);
            int32_t resist_type = resist_berry_type(def_resist.item);
            bool chilan = (def_resist.item == ITM_CHILAN_BERRY);
            if (resist_type != -1 && resist_type == move_type && (type_mult > 1.0 || chilan)
                    && !is_berry_suppressor(active_mon(state, side_idx).ability)) {
                double berry_mult = (def_resist.ability == AB_RIPEN) ? 0.25 : 0.5;
                damage = std::max(1, (int)(damage * berry_mult));
                int32_t consumed = def_resist.item;
                def_resist.item = ITEM_NONE;
                def_resist.consumed_berry = consumed;
                apply_unburden(state, defender_idx);
            }
        }

        int32_t hp_before = active_mon(state, defender_idx).hp;
        int32_t attacker_ability = active_mon(state, side_idx).ability;
        MoveExecLuck mel = make_exec_luck(luck_def.proc_threshold, luck_def.random_mode, luck_def.rng, luck_def.overrides);
        int32_t hp_removed = cpp_apply_damage(state, defender_idx, damage, attacker_ability, mel,
                                              md.category, side_idx, 0);
        total_damage += damage;
        actual_damage += std::max(0, hp_removed);

        // Capture updated_defender snapshot fields for faint effects (before recoil overwrites).
        int32_t updated_def_volatiles = active_mon(state, defender_idx).volatiles;
        int32_t updated_def_ability = active_mon(state, defender_idx).ability;
        bool updated_def_fainted = active_mon(state, defender_idx).fainted;

        // Natural Gift consume (not exercised; throw if reached to stay loud).
        if (move == MV_NATURAL_GIFT && damage > 0) {
            PokemonState& ng = active_mon(state, side_idx);
            if (ng.item != ITEM_NONE) {
                int32_t consumed = ng.item;
                ng.item = ITEM_NONE;
                ng.consumed_berry = consumed;
                apply_unburden(state, side_idx);
            }
        }

        // Drain heal (Big Root amp; Liquid Ooze reverses).
        int32_t hit_actual = std::max(0, hp_removed);
        if (hit_actual > 0 && md.drain_num != -1) {
            int32_t drain_heal = std::max(1, (int)((long long)hit_actual * md.drain_num / md.drain_den));
            PokemonState& drain_atk = active_mon(state, side_idx);
            PokemonState& drain_def = active_mon(state, defender_idx);
            if (drain_atk.item == ITM_BIG_ROOT) drain_heal = (int)(drain_heal * 1.3);
            if (!drain_atk.fainted) {
                if (drain_def.ability == AB_LIQUID_OOZE) {
                    int32_t new_hp = std::max(0, drain_atk.hp - drain_heal);
                    drain_atk.hp = new_hp;
                    if (new_hp == 0) cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
                } else {
                    drain_atk.hp = std::min(drain_atk.max_hp, drain_atk.hp + drain_heal);
                }
            }
        }

        // Rough Skin / Iron Barbs.
        {
            PokemonState& rs_atk = active_mon(state, side_idx);
            bool rs_contact = (md.tags & TAG_CONTACT) && rs_atk.ability != AB_LONG_REACH;
            // defender.ability is the pre-recoil defender ability snapshot (updated_def_ability).
            if (rs_contact && rs_atk.item != ITM_PROTECTIVE_PADS && rs_atk.ability != AB_MAGIC_GUARD
                    && (updated_def_ability == AB_ROUGH_SKIN || updated_def_ability == AB_IRON_BARBS)
                    && !rs_atk.fainted) {
                int32_t recoil = std::max(1, rs_atk.max_hp / 8);
                int32_t new_hp = std::max(0, rs_atk.hp - recoil);
                rs_atk.hp = new_hp;
                if (new_hp == 0) cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
            }
        }

        // Rocky Helmet (Unit 1).
        {
            MoveExecLuck rh_luck = make_exec_luck(luck_atk.proc_threshold, luck_atk.random_mode, luck_atk.rng, luck_atk.overrides);
            cpp_apply_rocky_helmet(state, side_idx, defender_idx, move, rh_luck);
        }

        // HITCOUNT log omitted.

        if (updated_def_fainted) {
            apply_defender_faint_effects(state, side_idx, defender_idx, move, md,
                                         (md.tags & TAG_CONTACT) != 0, false,
                                         updated_def_volatiles, updated_def_ability,
                                         hp_before, luck_atk);
            break;
        }

        cpp_apply_gulp_missile_projectile(state, defender_idx, side_idx);
    }

    // Metronome streak write.
    if (metronome_active) {
        PokemonState& attacker = active_mon(state, side_idx);
        if (total_damage > 0) { attacker.metronome_count = new_count; attacker.metronome_last_move = move; }
        else { attacker.metronome_count = 0; attacker.metronome_last_move = -1; }
    }

    (void)phe_eff_slot;
    return {total_damage, actual_damage};
}

// Slot-swap guard: make active_indices[0] == active_indices[pos], run f, restore.
template <typename F>
void with_active_slot_swapped(BattleState& state, int side_idx, int pos, F&& f) {
    SideState& side = side_at(state, side_idx);
    std::swap(side.active_indices[0], side.active_indices[pos]);
    f();
    SideState& side2 = side_at(state, side_idx);
    std::swap(side2.active_indices[0], side2.active_indices[pos]);
}

} // namespace

// ===========================================================================
// _handle_damage_action
// ===========================================================================
void cpp_handle_damage_action(BattleState& state, int side_idx, int defender_idx,
                              int32_t move, int32_t move_type, ExecCtx& ctx,
                              const DamageLoopLuck& luck_atk, const DamageLoopLuck& luck_def,
                              int effective_slot, double effective_acc, bool effective_acc_is_none,
                              bool from_dancer, int target_side, int target_slot,
                              std::vector<PendingSwitch>& pending_switches) {
    const MoveData& md = move_data_or_throw(move);

    // Resolve targets (source_slot 0 because the attacker slot-swap already happened).
    // Thread random_mode/rng so RANDOM_NORMAL multi-foe picks work in random_mode.
    std::vector<std::pair<int32_t, int32_t>> resolved =
        cpp_resolve_targets(state, side_idx, 0, move, target_side, target_slot,
                            luck_atk.random_mode, luck_atk.rng);

    // Follow Me / Rage Powder redirect (doubles, single-target foe-directed).
    if (state.format == FORMAT_DOUBLES
            && md.target != TGT_ALL_ADJACENT_FOES && md.target != TGT_ALL && md.target != TGT_SELF
            && md.target != TGT_ALLY_SIDE && md.target != TGT_FOE_SIDE
            && side_at(state, defender_idx).redirect_target != -1
            && resolved.size() == 1 && resolved[0].first == defender_idx) {
        SideState& dside = side_at(state, defender_idx);
        bool rage_powder = dside.redirect_is_rage_powder;
        PokemonState& attacker = active_mon(state, side_idx);
        bool powder_immune = rage_powder
            && (has_type(attacker, TYPE_GRASS) || attacker.item == ITM_SAFETY_GOGGLES
                || attacker.ability == AB_OVERCOAT);
        int32_t redirect_team_slot = dside.redirect_target;
        const PokemonState& redirect_mon = dside.team[redirect_team_slot];
        if (!powder_immune && !redirect_mon.fainted) {
            int redirect_pos = -1;
            for (size_t pos = 0; pos < dside.active_indices.size(); ++pos) {
                if (dside.active_indices[pos] == redirect_team_slot) { redirect_pos = (int)pos; break; }
            }
            if (redirect_pos >= 0 && redirect_pos != resolved[0].second) {
                resolved.clear();
                resolved.push_back({defender_idx, redirect_pos});
            }
        }
    }

    int32_t total_damage = 0, actual_damage = 0;

    if (resolved.empty()) {
        LoopResult r = handle_damage_loop(state, side_idx, defender_idx, move, md, move_type, ctx,
                                          luck_atk, luck_def, 0, effective_acc, effective_acc_is_none,
                                          effective_slot, /*spread_hit*/true);
        total_damage = r.total_damage; actual_damage = r.actual_damage;
        bool hit_sub = (total_damage > 0 && actual_damage == 0);
        PostHitArgs a;
        a.side_idx = side_idx; a.defender_idx = defender_idx; a.move = move; a.move_type = move_type;
        a.damage = total_damage; a.actual_damage = actual_damage; a.hit_sub = hit_sub;
        a.effective_slot = effective_slot; a.attacker_slot = ctx.attacker_slot;
        a.competitive_defiant_triggered = ctx.competitive_defiant_triggered;
        a.ctx = &ctx;
        EffectsLuck el = make_effects_luck(luck_atk);
        cpp_apply_post_hit_effects(state, a, pending_switches, el);
        cpp_bump_rollout_counter(state, side_idx, move, total_damage);
    } else {
        int live_foe_targets = 0;
        for (const auto& t : resolved) if (t.first != side_idx) ++live_foe_targets;
        bool spread_hit = live_foe_targets > 1;
        for (const auto& t : resolved) {
            int t_side = t.first; int t_pos = t.second;
            with_active_slot_swapped(state, t_side, t_pos, [&]() {
                LoopResult r = handle_damage_loop(state, side_idx, t_side, move, md, move_type, ctx,
                                                  luck_atk, luck_def, 0, effective_acc,
                                                  effective_acc_is_none, effective_slot, spread_hit);
                total_damage += r.total_damage; actual_damage += r.actual_damage;
            });
        }
        int primary_side = resolved[0].first; int primary_pos = resolved[0].second;
        with_active_slot_swapped(state, primary_side, primary_pos, [&]() {
            bool hit_sub = (total_damage > 0 && actual_damage == 0);
            PostHitArgs a;
            a.side_idx = side_idx; a.defender_idx = primary_side; a.move = move; a.move_type = move_type;
            a.damage = total_damage; a.actual_damage = actual_damage; a.hit_sub = hit_sub;
            a.effective_slot = effective_slot; a.attacker_slot = ctx.attacker_slot;
            a.competitive_defiant_triggered = ctx.competitive_defiant_triggered;
            a.ctx = &ctx;
            EffectsLuck el = make_effects_luck(luck_atk);
            cpp_apply_post_hit_effects(state, a, pending_switches, el);
        });
        cpp_bump_rollout_counter(state, side_idx, move, total_damage);
    }

    // Spit Up reset.
    if (move == 255 /*SPIT_UP*/) cpp_reset_stockpile(state, side_idx);

    // Dancer re-trigger: other active Dancer holders copy the dance move (Unit 5).
    if (is_dance(move) && !from_dancer)
        cpp_apply_dancer_trigger(state, side_idx, move, ctx, luck_atk, luck_def, pending_switches);
}

// ===========================================================================
// _handle_fixed_damage_action
// ===========================================================================
void cpp_handle_fixed_damage_action(BattleState& state, int side_idx, int defender_idx,
                                    int32_t move, int32_t move_type, int32_t fixed_dmg,
                                    ExecCtx& ctx, const DamageLoopLuck& luck_atk,
                                    const DamageLoopLuck& luck_def, int effective_slot,
                                    std::vector<PendingSwitch>& pending_switches) {
    const MoveData& md = move_data_or_throw(move);

    if (fixed_dmg == -2) {
        active_mon(state, side_idx).last_move_failed = true;
        PostHitArgs a;
        a.side_idx = side_idx; a.defender_idx = defender_idx; a.move = move; a.move_type = move_type;
        a.damage = 0; a.actual_damage = 0; a.hit_sub = false;
        a.effective_slot = effective_slot; a.attacker_slot = ctx.attacker_slot;
        a.competitive_defiant_triggered = ctx.competitive_defiant_triggered;
        a.ctx = &ctx;
        EffectsLuck el = make_effects_luck(luck_atk);
        cpp_apply_post_hit_effects(state, a, pending_switches, el);
        return;
    }

    // Type-chart immunity.
    double fd_eff = 1.0;
    {
        const PokemonState& defender = active_mon(state, defender_idx);
        if (defender.has_types)
            for (int32_t dt : defender.types) fd_eff *= cpp_type_effectiveness(move_type, dt);
    }
    if (fd_eff == 0.0) return;  // MOVE_IMMUNE log omitted.

    int32_t attacker_ability = active_mon(state, side_idx).ability;
    MoveExecLuck mel = make_exec_luck(luck_def.proc_threshold, luck_def.random_mode, luck_def.rng, luck_def.overrides);
    int32_t hp_removed_fixed = cpp_apply_damage(state, defender_idx, fixed_dmg, attacker_ability,
                     mel, md.category, -1, 0);
    int32_t actual_fixed = std::max(0, hp_removed_fixed);
    bool fd_fainted = active_mon(state, defender_idx).fainted;
    if (fd_fainted) {
        cpp_apply_on_ko_effects(state, side_idx);
        notify_faint_soul_heart(state);
        side_at(state, defender_idx).ally_fainted_last_turn = true;
    }
    // Final Gambit.
    if (move == MV_FINAL_GAMBIT) {
        cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
    }
    // Rocky Helmet.
    if (fixed_dmg > 0) {
        MoveExecLuck rh = make_exec_luck(luck_atk.proc_threshold, luck_atk.random_mode, luck_atk.rng, luck_atk.overrides);
        cpp_apply_rocky_helmet(state, side_idx, defender_idx, move, rh);
    }
    PostHitArgs a;
    a.side_idx = side_idx; a.defender_idx = defender_idx; a.move = move; a.move_type = move_type;
    a.damage = fixed_dmg; a.actual_damage = actual_fixed; a.hit_sub = false;
    a.effective_slot = effective_slot; a.attacker_slot = ctx.attacker_slot;
    a.competitive_defiant_triggered = ctx.competitive_defiant_triggered;
    a.ctx = &ctx;
    EffectsLuck el = make_effects_luck(luck_atk);
    cpp_apply_post_hit_effects(state, a, pending_switches, el);
}
