// C1.7d Unit 5: the move-execution dispatcher (see move_exec.h). Byte-identical mirror of
// _execute_action / _execute_action_body / _handle_status_action / _handle_switch_action /
// _handle_recharge_action / _apply_dancer_trigger in src/engine/core.py on deterministic paths.
// Python log() calls are state-neutral and omitted. Calls into U1-U4 + effects/exp; never
// reimplements their bodies. Uncontrolled-oracle / random_mode / Baton Pass serialization throw.
#include "move_exec.h"
#include "rng_resolver.h"        // rng_resolve_accuracy
#include "move_exec_premove.h"   // cpp_pre_move_checks, PreMoveLuck
#include "move_exec_guards.h"    // cpp_pre_damage_checks/guards, ExecCtx, GuardLuck, GuardResult
#include "move_exec_damage.h"    // cpp_handle_damage_action/fixed, DamageLoopLuck
#include "move_exec_helpers.h"   // cpp_consume_pp, cpp_check_leppa_berry, MoveExecLuck
#include "effects.h"             // cpp_apply_status_move, switch_out_reset, entry_hazards/effects, EffectsLuck
#include "effects_internal.h"    // active_mon, side_at, change_stat_stage, apply_form_change, ...
#include "effects_consts.h"
#include "exp.h"                 // cpp_flush_opponent_faint_exp
#include "core_leaf.h"           // cpp_compute_fixed_damage, PsywaveLuck
#include "type_chart_lookup.h"   // cpp_type_effectiveness
#include "event_log.h"           // rich_log_baton_pass_transfer
#include "../generated/move_data.h"

#include <algorithm>
#include <functional>
#include <stdexcept>

using namespace eff;
using eff_internal::active_mon;
using eff_internal::side_at;
using eff_internal::change_stat_stage;
using eff_internal::apply_form_change;
using eff_internal::is_mold_breaker;
using eff_internal::is_grounded;
using eff_internal::has_type;
using eff_internal::has_pseudo;
using eff_internal::has_timed_volatile;

namespace {

// ---- MOVE_TABLE lookup (file-local in core_leaf.cpp; reimplemented identical). ----
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

// ---- Constants (mirror the Python enums/sets). ----
constexpr int32_t TYPE_ELECTRIC = 3, TYPE_POISON = 7, TYPE_DARK = 15;

// Volatile bits
constexpr int32_t V_TRUANT_LOAFING = 16777216, V_CHOICE_LOCKED = 262144,
    V_SUBSTITUTE = 4096, V_PROTECT_USED = 4194304, V_PROTEAN_USED = 67108864,
    V_RECHARGING = 256;

// VolatileEffect ids
constexpr int32_t VE_TRAPPED = 22, VE_SEMI_INVULNERABLE = 27;

// MoveTag bits
constexpr int32_t TAG_SOUND = 256, TAG_POWDER = 16384;

// MoveCategory / MoveTarget
constexpr int32_t CAT_STATUS = 2;
constexpr int32_t TGT_SELF = 1, TGT_ALLY_SIDE = 6, TGT_FOE_SIDE = 7, TGT_ALL = 8,
    TGT_ALL_ADJACENT_FOES = 2, TGT_ALL_ADJACENT = 3;

// ActionKind
constexpr int32_t AK_SWITCH = 1;

// TerrainEnum
constexpr int32_t TERRAIN_PSYCHIC = 3;

// Abilities
constexpr int32_t AB_TRUANT = 54, AB_PRESSURE = 46, AB_PROTEAN = 168, AB_LIBERO = 236,
    AB_PRANKSTER = 158, AB_WONDER_SKIN = 147, AB_SOUNDPROOF = 43, AB_OVERCOAT = 142,
    AB_MAGIC_BOUNCE = 156, AB_INFILTRATOR = 151, AB_STANCE_CHANGE = 176, AB_DAZZLING = 219,
    AB_QUEENLY_MAJESTY = 214, AB_ARMOR_TAIL = 296, AB_NO_GUARD = 99, AB_COMPOUND_EYES = 14,
    AB_KEEN_EYE = 51, AB_UNAWARE = 109, AB_TANGLED_FEET = 77, AB_SAND_VEIL = 8, AB_SNOW_CLOAK = 81,
    AB_VICTORY_STAR = 162, AB_TRIAGE = 205;

// Items
constexpr int32_t ITM_ASSAULT_VEST = 640, ITM_THROAT_SPRAY = 1118, ITM_SAFETY_GOGGLES = 650,
    ITM_BRIGHT_POWDER = 213, ITM_WIDE_LENS = 265;

// Species
constexpr int32_t SP_AEGISLASH = 681;

// Moves
constexpr int32_t MV_NONE = 0, MV_ENDURE = 203, MV_NATURE_POWER = 267, MV_COPYCAT = 383,
    MV_MIRROR_MOVE = 119, MV_THUNDER_WAVE = 86, MV_TOXIC = 92, MV_NATURAL_GIFT = 363,
    MV_TRI_ATTACK = 161, MV_BATON_PASS = 226, MV_KINGS_SHIELD = 588, MV_PLAY_NICE = 589;

// Move tag RECOVERY (for Triage priority bump) + drain.
constexpr int32_t TAG_RECOVERY = 4;

bool in_list(int32_t v, const int32_t* arr, int n) {
    for (int i = 0; i < n; ++i) if (arr[i] == v) return true;
    return false;
}

// Move sets (ids dumped from src/data — see core.py imports).
const int32_t PROTECT_MOVES[] = {182, 197, 455, 469, 501, 588, 596, 661, 792};
const int32_t TWO_TURN_MOVES[] = {13, 19, 76, 91, 130, 143, 291, 340, 566, 669, 800};
const int32_t RAMPAGE_MOVES[] = {37, 80, 200};
const int32_t DANCE_MOVES[] = {14, 80, 297, 298, 349, 461, 483, 552, 686};
const int32_t GRAVITY_BLOCKED_MOVES[] = {19, 26, 136, 150, 340, 393, 477, 507};
const int32_t DEFROST_TARGET_MOVES[] = {221, 503, 682, 815};
const int32_t PHASING_STATUS_MOVES[] = {18, 46};        // ROAR, WHIRLWIND
const int32_t PROTECT_BYPASS_MOVES[] = {364, 566, 589, 593, 621};
const int32_t NON_REFLECTABLE_MOVES[] = {262, 777};     // MEMENTO, DECORATE
const int32_t MOLD_BREAKER_ABILITIES[] = {104, 163, 164};
const int32_t CHOICE_ITEMS[] = {220, 287, 297};
const int32_t COPYCAT_EXCLUDED[] = {19, 68, 91, 118, 119, 144, 165, 168, 182, 194, 197, 203, 214,
    243, 264, 266, 270, 274, 289, 291, 343, 364, 382, 383, 448, 476, 509, 525, 562, 596, 690, 704};
const int32_t MIRROR_MOVE_EXCLUDED[] = {118, 119, 165, 214, 264, 274, 383, 690, 704};
// Exclusion sets mirroring src/data/moves.py METRONOME_EXCLUDED and SLEEP_TALK_EXCLUDED.
const int32_t METRONOME_EXCLUDED[] = {
    12, 19, 32, 68, 90, 91, 118, 119, 130, 143, 144, 165, 182, 194, 197, 203, 214, 243,
    250, 253, 255, 264, 266, 267, 270, 274, 289, 291, 340, 343, 364, 382, 383, 448, 476,
    505, 507, 553, 554, 561, 562, 588, 617, 661, 690, 704, 713, 714, 721, 722, 730, 744,
    775, 776, 779, 783, 787, 788, 874, 889, 890};
const int32_t SLEEP_TALK_EXCLUDED[] = {
    13, 19, 76, 91, 119, 130, 143, 214, 253, 264, 274, 289, 291, 340, 382, 383,
    507, 562, 566, 669, 690, 704, 800, 905};
constexpr int32_t MV_STRUGGLE_LOCAL = 165;
// NATURAL_GIFT_TABLE keys (berry items that give Natural Gift a usable type/power).
const int32_t NATURAL_GIFT_KEYS[] = {149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160,
    161, 162, 163, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199,
    200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 686, 687, 688};

bool is_protect_move(int32_t m) { return in_list(m, PROTECT_MOVES, 9); }
bool is_two_turn(int32_t m) { return in_list(m, TWO_TURN_MOVES, 11); }
bool is_rampage(int32_t m) { return in_list(m, RAMPAGE_MOVES, 3); }
bool is_dance(int32_t m) { return in_list(m, DANCE_MOVES, 9); }
bool is_gravity_blocked(int32_t m) { return in_list(m, GRAVITY_BLOCKED_MOVES, 8); }
bool is_defrost_target(int32_t m) { return in_list(m, DEFROST_TARGET_MOVES, 4); }
bool is_phasing_status(int32_t m) { return in_list(m, PHASING_STATUS_MOVES, 2); }
bool is_protect_bypass(int32_t m) { return in_list(m, PROTECT_BYPASS_MOVES, 5); }
bool is_non_reflectable(int32_t m) { return in_list(m, NON_REFLECTABLE_MOVES, 2); }
bool is_mold_breaker_ability(int32_t a) { return in_list(a, MOLD_BREAKER_ABILITIES, 3); }
bool is_choice_item(int32_t i) { return in_list(i, CHOICE_ITEMS, 3); }
bool copycat_valid(int32_t m) {
    return !in_list(m, COPYCAT_EXCLUDED, (int)(sizeof(COPYCAT_EXCLUDED) / sizeof(int32_t)));
}
bool mirror_move_valid(int32_t m) {
    return !in_list(m, MIRROR_MOVE_EXCLUDED, (int)(sizeof(MIRROR_MOVE_EXCLUDED) / sizeof(int32_t)));
}
bool is_natural_gift_berry(int32_t item) {
    return in_list(item, NATURAL_GIFT_KEYS, (int)(sizeof(NATURAL_GIFT_KEYS) / sizeof(int32_t)));
}
bool target_applies_stages(int32_t target) {
    // _status_apply_stages: target not in (SELF, ALLY_SIDE, FOE_SIDE, ALL).
    return target != TGT_SELF && target != TGT_ALLY_SIDE && target != TGT_FOE_SIDE && target != TGT_ALL;
}

// stat_stage accessor.
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
bool has_timed_ve(const PokemonState& m, int32_t ve) { return has_timed_volatile(m, ve); }

// _triage_priority_bump (ability 205 grants +3 to recovery/drain moves).
int32_t triage_priority_bump(int32_t ability, const MoveData& md) {
    if (ability != AB_TRIAGE) return 0;
    bool recovery = (md.tags & TAG_RECOVERY) != 0;
    bool drain = md.drain_num != -1;
    return (recovery || drain) ? 3 : 0;
}

bool either_no_guard(const PokemonState& a, const PokemonState& d) {
    return a.ability == AB_NO_GUARD || d.ability == AB_NO_GUARD;
}

// ---------------------------------------------------------------------------
// Accuracy modifiers — re-implemented file-local (the guards.cpp copies are anonymous-namespace
// statics; re-implemented here to avoid cross-TU/ODR coupling, matching src/engine exactly).
// acc carries (value, is_none); is_none mirrors Python's None (always-hit) accuracy sentinel.
// ---------------------------------------------------------------------------
const double ACC_STAGE_MULT[13] = {
    3.0/9, 3.0/8, 3.0/7, 3.0/6, 3.0/5, 3.0/4, 1.0, 4.0/3, 5.0/3, 2.0/1, 7.0/3, 8.0/3, 3.0/1
};

void apply_accuracy_modifiers(double& acc, bool& is_none, const PokemonState& attacker,
                              const PokemonState& defender, const BattleState& state,
                              bool apply_stat_stages) {
    if (attacker.ability == AB_NO_GUARD || defender.ability == AB_NO_GUARD) { is_none = true; return; }
    if (is_none) return;
    if (attacker.ability == AB_COMPOUND_EYES) acc = std::min(acc * 1.3, 100.0);
    if (has_pseudo(state, PW_GRAVITY)) acc = std::min(acc * 5.0 / 3.0, 100.0);
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

// ---------------------------------------------------------------------------
// with_active_slot_swapped: temporarily make active_indices[0] point to the acting slot, so helpers
// that read active_indices[0] see the right Pokemon. Mirror of U4's file-local helper.
// ---------------------------------------------------------------------------
template <typename F>
void with_active_slot_swapped(BattleState& state, int side_idx, int pos, F&& f) {
    SideState& side = side_at(state, side_idx);
    if (pos == 0 || pos >= (int)side.active_indices.size()) { f(); return; }
    std::swap(side.active_indices[0], side.active_indices[pos]);
    try { f(); } catch (...) { std::swap(side.active_indices[0], side.active_indices[pos]); throw; }
    std::swap(side.active_indices[0], side.active_indices[pos]);
}

// ---- Luck sub-struct builders from the superset DamageLoopLuck. ----
PreMoveLuck make_premove_luck(const DamageLoopLuck& l) {
    PreMoveLuck p;
    p.wake_threshold               = l.wake_threshold;
    p.defrost_threshold            = l.defrost_threshold;
    p.paralysis_threshold          = l.paralysis_threshold;
    p.confusion_snap_threshold     = l.confusion_snap_threshold;
    p.confusion_self_hit_threshold = l.confusion_self_hit_threshold;
    p.attract_threshold            = l.attract_threshold;
    p.damage_roll                  = l.damage_roll;
    p.proc_threshold               = l.proc_threshold;
    p.random_mode                  = l.random_mode;
    p.rng                          = l.rng;
    return p;
}
GuardLuck make_guard_luck(const DamageLoopLuck& l) {
    GuardLuck g;
    g.accuracy_threshold = l.accuracy_threshold;
    g.proc_threshold     = l.proc_threshold;
    g.random_mode        = l.random_mode;
    g.rng                = l.rng;
    return g;
}
EffectsLuck make_effects_luck(const DamageLoopLuck& l) {
    EffectsLuck e;
    e.proc_threshold         = l.proc_threshold;
    e.secondary_threshold    = l.secondary_threshold;
    e.flinch_threshold       = l.flinch_threshold;
    e.binding_duration_roll  = l.binding_duration_roll;
    e.random_mode            = l.random_mode;
    e.rng                    = l.rng;
    e.overrides              = l.overrides;
    return e;
}
PsywaveLuck make_psywave_luck(const DamageLoopLuck& l) {
    PsywaveLuck p;
    p.psywave_roll = l.psywave_roll;
    p.random_mode  = l.random_mode;
    p.rng          = l.rng;
    return p;
}

// Forward declarations for the mutually-recursive body / dancer.
void execute_action_body(BattleState& state, int side_idx, const ExecAction& action,
                         DamageLoopLuck& luck_atk, DamageLoopLuck& luck_def,
                         std::vector<PendingSwitch>& pending_switches, ExecCtx& ctx,
                         bool from_dancer);

// ---------------------------------------------------------------------------
// _handle_recharge_action
// ---------------------------------------------------------------------------
void handle_recharge_action(BattleState& state, int side_idx) {
    PokemonState& attacker = active_mon(state, side_idx);
    attacker.volatiles &= ~V_RECHARGING;
}

// ---------------------------------------------------------------------------
// _handle_switch_action
// ---------------------------------------------------------------------------
void handle_switch_action(BattleState& state, int side_idx, const ExecAction& action,
                          ExecCtx& ctx, int source_slot) {
    // Reset participant set for this slot when opponent (side 1) switches.
    if (side_idx == 1 && ctx.has_exp_participants
            && source_slot < (int)ctx.exp_participants.size()) {
        ctx.exp_participants[source_slot].clear();
    }
    SideState& side = side_at(state, side_idx);
    int old_active_idx = side.active_indices[source_slot];
    cpp_apply_switch_out_reset(state, side_idx, old_active_idx);
    side.active_indices[source_slot] = action.switch_to_slot;
    PokemonState& new_poke = side.team[action.switch_to_slot];
    new_poke.turns_in_battle = 0;
    new_poke.toxic_turns = 0;
    new_poke.sleep_turns = 0;
    // Slot-swap: entry functions read active_indices[0] as the entering mon.
    with_active_slot_swapped(state, side_idx, source_slot, [&]() {
        cpp_apply_entry_hazards(state, side_idx);
        int entering_ai = side_at(state, side_idx).active_indices[0];
        if (!side_at(state, side_idx).team[entering_ai].fainted)
            cpp_apply_entry_effects(state, side_idx);
    });
}

// Forward decl: defined below handle_status_action but referenced by it (Soundproof gate).
bool target_applies_stages_no_foeside(int32_t target);

// ---------------------------------------------------------------------------
// _handle_status_action
// ---------------------------------------------------------------------------
void handle_status_action(BattleState& state, int side_idx, int defender_idx, int32_t move,
                          const MoveData& md, ExecCtx& ctx,
                          std::vector<PendingSwitch>& pending_switches, bool from_dancer,
                          int effective_slot, const DamageLoopLuck& luck_atk,
                          const DamageLoopLuck& luck_def) {
    // Protean / Libero: type change at move use (status moves included).
    {
        PokemonState& attacker = active_mon(state, side_idx);
        if ((attacker.ability == AB_PROTEAN || attacker.ability == AB_LIBERO)
                && !(attacker.volatiles & V_PROTEAN_USED)) {
            attacker.types = {md.move_type};
            attacker.volatiles |= V_PROTEAN_USED;
        }
    }
    // Reset last_move_failed at the start of execution.
    active_mon(state, side_idx).last_move_failed = false;

    bool target_stages = target_applies_stages(md.target);

    // Effective accuracy.
    double eff_acc; bool eff_is_none;
    eff_is_none = (md.accuracy < 0);
    eff_acc = eff_is_none ? 0.0 : (double)md.accuracy;
    {
        PokemonState& attacker = active_mon(state, side_idx);
        if (move == MV_THUNDER_WAVE && has_type(attacker, TYPE_ELECTRIC)) eff_is_none = true;
        if (move == MV_TOXIC && has_type(attacker, TYPE_POISON)) eff_is_none = true;
    }
    apply_accuracy_modifiers(eff_acc, eff_is_none, active_mon(state, side_idx),
                             active_mon(state, defender_idx), state, target_stages);
    if (target_stages) {
        apply_item_ability_accuracy_modifiers(eff_acc, eff_is_none, active_mon(state, side_idx),
                                              active_mon(state, defender_idx), state);
    }
    // Wonder Skin: caps status move accuracy at 50 (Mold Breaker bypasses).
    if (!eff_is_none && target_stages
            && !is_mold_breaker_ability(active_mon(state, side_idx).ability)) {
        if (active_mon(state, defender_idx).ability == AB_WONDER_SKIN)
            eff_acc = std::min(eff_acc, 50.0);
    }
    const RngLogCtx catb_ctx{
        RngParticipants{
            (int8_t)side_idx,     (int8_t)side_at(state, side_idx).active_indices[0],
            (int8_t)defender_idx, (int8_t)side_at(state, defender_idx).active_indices[0]},
        state.turn_number};
    if (!rng_resolve_accuracy(eff_acc, eff_is_none, luck_atk.accuracy_threshold,
                              luck_atk.random_mode, luck_atk.rng, &catb_ctx)) {
        active_mon(state, side_idx).last_move_failed = true;
        return;
    }
    // Semi-invuln miss for opponent-targeting status moves.
    if (target_stages) {
        PokemonState& def_si = active_mon(state, defender_idx);
        if (has_timed_ve(def_si, VE_SEMI_INVULNERABLE)
                && !either_no_guard(active_mon(state, side_idx), def_si)) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
    }
    // Protect.
    if (target_stages && ctx.protected_sides[defender_idx]) {
        if (!is_protect_bypass(move)) {
            cpp_apply_protect_contact_penalty(state, side_idx, defender_idx, move, md, ctx);
            return;
        }
    }
    // Wide Guard: spread status moves.
    if (ctx.wide_guard_sides[defender_idx]
            && (md.target == TGT_ALL_ADJACENT_FOES || md.target == TGT_ALL_ADJACENT)) {
        return;
    }
    // Quick Guard: priority status moves.
    if (ctx.quick_guard_sides[defender_idx]) {
        int32_t qg_pri = md.priority + triage_priority_bump(active_mon(state, side_idx).ability, md);
        if (qg_pri > 0) return;
    }
    // Soundproof.
    if ((md.tags & TAG_SOUND) && target_applies_stages_no_foeside(md.target)
            && !is_mold_breaker_ability(active_mon(state, side_idx).ability)) {
        if (active_mon(state, defender_idx).ability == AB_SOUNDPROOF) return;
    }
    // Prankster: status moves fail vs Dark-type targets.
    if (active_mon(state, side_idx).ability == AB_PRANKSTER && target_stages) {
        if (has_type(active_mon(state, defender_idx), TYPE_DARK)) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
    }
    // Safety Goggles / Overcoat: powder/spore immunity.
    if ((md.tags & TAG_POWDER) && target_stages) {
        PokemonState& def = active_mon(state, defender_idx);
        if (def.item == ITM_SAFETY_GOGGLES) return;
        if (def.ability == AB_OVERCOAT && !is_mold_breaker_ability(active_mon(state, side_idx).ability))
            return;
    }
    // Magic Bounce: reflect status moves back at attacker.
    if (md.target != TGT_SELF && md.target != TGT_ALLY_SIDE && md.target != TGT_ALL
            && !is_non_reflectable(move)
            && !is_mold_breaker_ability(active_mon(state, side_idx).ability)) {
        PokemonState& def = active_mon(state, defender_idx);
        if (def.ability == AB_MAGIC_BOUNCE) {
            if (has_timed_ve(def, VE_SEMI_INVULNERABLE)
                    && !either_no_guard(active_mon(state, side_idx), def)) {
                active_mon(state, side_idx).last_move_failed = true;
                return;
            }
            EffectsLuck el = make_effects_luck(luck_atk);
            cpp_apply_status_move(state, defender_idx, move, el, ctx, ctx.attacker_slot);
            return;
        }
    }
    // Priority-block guards (silent).
    if (target_stages) {
        int32_t eff_pri = md.priority
            + triage_priority_bump(active_mon(state, side_idx).ability, md)
            + (active_mon(state, side_idx).ability == AB_PRANKSTER ? 1 : 0);
        if (eff_pri > 0 && state.terrain == TERRAIN_PSYCHIC
                && is_grounded(active_mon(state, defender_idx), state)) {
            return;
        }
        if (eff_pri > 0 && !is_mold_breaker_ability(active_mon(state, side_idx).ability)) {
            SideState& dside = side_at(state, defender_idx);
            for (int32_t dqm_idx : dside.active_indices) {
                int32_t ab = dside.team[dqm_idx].ability;
                if (ab == AB_DAZZLING || ab == AB_QUEENLY_MAJESTY || ab == AB_ARMOR_TAIL) return;
            }
        }
    }
    // Ability-based type immunity for STATUS moves.
    if (target_stages) {
        if (check_type_immunity(state, side_idx, md.move_type, move)) return;
    }
    // Type-chart immunity for Electric paralysis moves vs Ground.
    if (target_stages && md.move_type == TYPE_ELECTRIC) {
        PokemonState& def = active_mon(state, defender_idx);
        double mult = 1.0;
        for (int32_t t : def.types) mult *= cpp_type_effectiveness(md.move_type, t);
        if (mult == 0.0) return;
    }
    // Substitute gate.
    if (target_stages) {
        PokemonState& def = active_mon(state, defender_idx);
        if ((def.volatiles & V_SUBSTITUTE) && def.sub_hp > 0) {
            bool bypassed = (md.tags & TAG_SOUND)
                || active_mon(state, side_idx).ability == AB_INFILTRATOR
                || move == MV_PLAY_NICE;
            if (!bypassed) return;
        }
    }
    {
        EffectsLuck el = make_effects_luck(luck_atk);
        cpp_apply_status_move(state, side_idx, move, el, ctx, ctx.attacker_slot);
    }
    // Throat Spray: +1 SpA after a sound-based status move; consumed.
    if (md.tags & TAG_SOUND) {
        PokemonState& attacker = active_mon(state, side_idx);
        if (attacker.item == ITM_THROAT_SPRAY) {
            attacker.item = ITEM_NONE;
            change_stat_stage(state, side_idx, 2, +1, false, false, false);
        }
    }
    // Phasing STATUS moves: force defender to switch.
    if (is_phasing_status(move)) {
        SideState& opp = side_at(state, defender_idx);
        bool bench = false;
        for (int i = 0; i < (int)opp.team.size(); ++i) {
            bool is_active = false;
            for (int32_t ai : opp.active_indices) if (ai == i) { is_active = true; break; }
            if (!is_active && !opp.team[i].fainted) { bench = true; break; }
        }
        if (bench) pending_switches.push_back({defender_idx, "roar"});
    } else if (move == MV_BATON_PASS) {
        // Baton Pass: if a healthy benched mon exists, store the passer's transferable
        // state on the side and queue a u-turn switch. baton_pass_data is a nested tuple
        // (stat_stages, allowlisted volatiles, timed_volatiles, crit_stage, sub_hp); it is
        // round-tripped through the codec as raw JSON, so we build it in to_jsonable shape.
        SideState& myside = side_at(state, side_idx);
        bool bench = false;
        for (int i = 0; i < (int)myside.team.size(); ++i) {
            bool is_active = false;
            for (int32_t ai : myside.active_indices) if (ai == i) { is_active = true; break; }
            if (!is_active && !myside.team[i].fainted) { bench = true; break; }
        }
        if (bench) {
            const PokemonState& bp = active_mon(state, side_idx);
            // BATON_PASS_TRANSFER fires once, only when a pass actually happens. The
            // switch-in target is not yet resolved here (queued via pending_switches), so
            // we log the passer's (currently active) species — the mon whose state is
            // being carried forward.
            rich_log_baton_pass_transfer(state.turn_number, side_idx, bp.species);
            // CONFUSED|LEECH_SEEDED|CURSED|AQUA_RING|INGRAIN|POWER_TRICK|SUBSTITUTE|FLASH_FIRE
            constexpr int32_t BP_VOLATILE_ALLOWLIST = 1282055;
            int32_t bp_vol = bp.volatiles & BP_VOLATILE_ALLOWLIST;

            BatonPassData data;
            data.stage0 = bp.stage0; data.stage1 = bp.stage1; data.stage2 = bp.stage2;
            data.stage3 = bp.stage3; data.stage4 = bp.stage4; data.stage5 = bp.stage5;
            data.stage6 = bp.stage6;
            data.volatiles_bitmask = bp_vol;
            data.crit_stage = bp.crit_stage;
            data.sub_hp     = bp.sub_hp;
            for (const auto& t : bp.timed_volatiles) data.timed_volatiles.push_back(t);

            myside.has_baton_pass_data = true;
            myside.baton_pass_data = data;
            pending_switches.push_back({side_idx, "u_turn"});
        }
    }
    // King's Shield: return Aegislash to Shield forme.
    if (active_mon(state, side_idx).ability == AB_STANCE_CHANGE && move == MV_KINGS_SHIELD) {
        apply_form_change(state, side_idx, SP_AEGISLASH);
    }
    // Choice lock after a STATUS move with a Choice item.
    {
        PokemonState& attacker = active_mon(state, side_idx);
        if (is_choice_item(attacker.item) && !(attacker.volatiles & V_CHOICE_LOCKED)) {
            attacker.volatiles |= V_CHOICE_LOCKED;
            attacker.locked_slot = effective_slot;
        }
    }
    // Dancer: other active Dancer holders copy dance moves.
    if (is_dance(move) && !from_dancer)
        cpp_apply_dancer_trigger(state, side_idx, move, ctx, luck_atk, luck_def, pending_switches);
}

// Soundproof gate uses the same exclusion as the (SELF/ALLY_SIDE/ALL) set (no FOE_SIDE check).
bool target_applies_stages_no_foeside(int32_t target) {
    return target != TGT_SELF && target != TGT_ALLY_SIDE && target != TGT_ALL;
}

// ---------------------------------------------------------------------------
// _execute_action_body
// ---------------------------------------------------------------------------
void execute_action_body(BattleState& state, int side_idx, const ExecAction& action,
                         DamageLoopLuck& luck_atk, DamageLoopLuck& luck_def,
                         std::vector<PendingSwitch>& pending_switches, ExecCtx& ctx,
                         bool from_dancer) {
    if (action.move_slot == -1) { handle_recharge_action(state, side_idx); return; }

    int defender_idx = 1 - side_idx;

    // Truant.
    {
        PokemonState& attacker = active_mon(state, side_idx);
        if (attacker.ability == AB_TRUANT) {
            if (attacker.volatiles & V_TRUANT_LOAFING) {
                attacker.volatiles &= ~V_TRUANT_LOAFING;
                return;
            } else {
                attacker.volatiles |= V_TRUANT_LOAFING;
            }
        }
    }

    // Peek move for Fire-thaw + Gravity gating.
    int32_t peek_move = (action.move_override != -1) ? action.move_override
        : (action.move_slot >= 0 ? move_id_at(active_mon(state, side_idx), action.move_slot) : MV_NONE);
    const MoveData* peek_data = move_data_get(peek_move);
    bool is_fire_move = (peek_data != nullptr && peek_data->move_type == 1 /*FIRE*/)
        || is_defrost_target(peek_move);

    // Gravity: block airborne/levitation moves.
    if (has_pseudo(state, PW_GRAVITY) && is_gravity_blocked(peek_move)) return;

    // Snapshot attacker BEFORE pre-move checks. Python's _execute_action_body holds a stale
    // `attacker` variable captured before _pre_move_checks runs; the protect_counter/PROTECT_USED
    // clear at the use-site rebuilds the state from that stale snapshot via _replace(). Mirror
    // that exactly: capture now, use below to restore ALL non-protect fields from pre-premove state.
    PokemonState pre_premove_attacker = active_mon(state, side_idx);

    if (!from_dancer) {
        PreMoveLuck pml = make_premove_luck(luck_atk);
        if (!cpp_pre_move_checks(state, side_idx, pml, is_fire_move, peek_move)) {
            PokemonState& blocked = active_mon(state, side_idx);
            if (!blocked.has_acted) blocked.has_acted = true;
            return;
        }
    }

    // Choice lock: redirect to locked slot.
    int effective_slot = action.move_slot;
    {
        PokemonState& attacker = active_mon(state, side_idx);
        if (action.move_slot >= 0 && (attacker.volatiles & V_CHOICE_LOCKED)
                && attacker.locked_slot >= 0 && action.move_slot != attacker.locked_slot) {
            effective_slot = attacker.locked_slot;
        }
    }

    int32_t move = (action.move_override != -1) ? action.move_override
        : move_id_at(active_mon(state, side_idx), effective_slot);

    // Two-turn release of a CALLED move (Metronome/Copycat -> Solar Beam etc.): the slot
    // holds the caller; execute the stored charged move so the caller is not re-run
    // (Showdown Gen 8 twoturnmove.onLockMove). Absent volatile = normal two-turn, no change.
    if (action.move_override == -1 && effective_slot >= 0
            && active_mon(state, side_idx).charging_move_slot == effective_slot) {
        for (const TimedVolatile& tv : active_mon(state, side_idx).timed_volatiles) {
            if (tv.effect == VE_CHARGING_MOVE) { move = tv.turns; break; }
        }
    }

    // Assault Vest: holder cannot use status-category moves.
    {
        const MoveData* mdc = move_data_get(move);
        if (active_mon(state, side_idx).item == ITM_ASSAULT_VEST
                && mdc != nullptr && mdc->category == CAT_STATUS) {
            return;
        }
    }

    // Natural Gift with no usable Berry: still executes & fails, so it spends PP.
    if (move == MV_NATURAL_GIFT && !is_natural_gift_berry(active_mon(state, side_idx).item)) {
        if (action.move_override == -1 && !from_dancer && effective_slot >= 0)
            cpp_consume_pp(state, side_idx, effective_slot, 0);
        PokemonState& failed = active_mon(state, side_idx);
        if (!failed.has_acted) failed.has_acted = true;
        return;
    }

    // Clear protect_counter / PROTECT_USED for a non-protect-family move.
    // Python uses a stale `attacker` snapshot (captured before _pre_move_checks) as the base
    // for _replace(protect_counter=0, ...), so ALL pre-premove fields are restored here when
    // protect_counter > 0 or PROTECT_USED. Mirror that: use pre_premove_attacker as base.
    if (move != MV_ENDURE && !is_protect_move(move)) {
        if (pre_premove_attacker.protect_counter > 0 || (pre_premove_attacker.volatiles & V_PROTECT_USED)) {
            active_mon(state, side_idx) = pre_premove_attacker;
            active_mon(state, side_idx).protect_counter = 0;
            active_mon(state, side_idx).volatiles &= ~V_PROTECT_USED;
        }
    }

    int32_t prev_battle_last_move = -1;

    // Two-turn release: pay PP on the charge turn only.
    bool two_turn_release = is_two_turn(move) && effective_slot >= 0
        && active_mon(state, side_idx).charging_move_slot == effective_slot;
    if (!from_dancer && !two_turn_release && effective_slot >= 0) {
        // Pressure: extra PP when targeting an opponent with PRESSURE.
        int pressure_extra = 0;
        int32_t move_check = move_id_at(active_mon(state, side_idx), effective_slot);
        const MoveData* mdc = move_data_get(move_check);
        if (mdc != nullptr) {
            if (mdc->target != TGT_SELF && mdc->target != TGT_ALLY_SIDE && mdc->target != TGT_ALL) {
                if (active_mon(state, 1 - side_idx).ability == AB_PRESSURE) pressure_extra = 1;
            }
        }
        cpp_consume_pp(state, side_idx, effective_slot, pressure_extra);
        cpp_check_leppa_berry(state, side_idx, effective_slot, 1 - side_idx);
    }

    if (!from_dancer) {
        PokemonState& attacker = active_mon(state, side_idx);
        int32_t slot_mask = (effective_slot >= 0) ? (1 << effective_slot) : 0;
        attacker.last_used_slot = effective_slot;
        attacker.moves_used |= slot_mask;
        attacker.has_acted = true;
        prev_battle_last_move = state.battle_last_move;
        state.battle_last_move = move;
        active_mon(state, side_idx).mirror_move_last_move = move;
    }

    const MoveData* move_data = move_data_get(move);
    if (move_data == nullptr) return;

    // Nature Power: redirect to terrain-based move.
    if (move == MV_NATURE_POWER) {
        int32_t nature_move;
        switch (state.terrain) {
            case 1: nature_move = 85; break;   // ELECTRIC -> THUNDERBOLT
            case 2: nature_move = 412; break;  // GRASSY -> ENERGY_BALL
            case 3: nature_move = 94; break;   // PSYCHIC -> PSYCHIC
            case 4: nature_move = 585; break;  // MISTY -> MOONBLAST
            default: nature_move = MV_TRI_ATTACK; break;
        }
        const MoveData* nd = move_data_get(nature_move);
        if (nd == nullptr) return;
        move = nature_move;
        move_data = nd;
    }

    // Copycat.
    if (move == MV_COPYCAT) {
        int32_t cc = prev_battle_last_move;
        if (cc == -1 || !copycat_valid(cc)) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
        const MoveData* cd = move_data_get(cc);
        if (cd == nullptr) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
        move = cc;
        move_data = cd;
    }

    // Mirror Move.
    if (move == MV_MIRROR_MOVE) {
        int32_t mm = active_mon(state, defender_idx).mirror_move_last_move;
        if (mm == -1 || !mirror_move_valid(mm)) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
        const MoveData* mmd = move_data_get(mm);
        if (mmd == nullptr) {
            active_mon(state, side_idx).last_move_failed = true;
            return;
        }
        move = mm;
        move_data = mmd;
    }

    // Pre-damage checks.
    {
        GuardLuck gl = make_guard_luck(luck_atk);
        if (!cpp_pre_damage_checks(state, side_idx, defender_idx, move, gl, ctx, effective_slot))
            return;
    }

    // A move with no live target fails outright — no accuracy/damage rolls. Applies to
    // STATUS moves too (Showdown Gen 8: Thunder Wave into a corpse fails; side/field
    // targets never need a live target). Mirrors core.py _execute_action_body
    // "no_target" fail (corpus trace_7216781346045368782: Final Gambit self-KO, then
    // Seismic Toss into the corpse revived it via Focus Band recomputing fainted=false).
    if (!cpp_move_has_target(state, side_idx, 0, move, action.target_side, action.target_slot)) {
        active_mon(state, side_idx).last_move_failed = true;
        return;
    }

    // Status dispatch.
    if (move_data->category == CAT_STATUS) {
        handle_status_action(state, side_idx, defender_idx, move, *move_data, ctx,
                             pending_switches, from_dancer, effective_slot, luck_atk, luck_def);
        return;
    }

    // Pre-damage guards.
    GuardResult gr;
    {
        GuardLuck gla = make_guard_luck(luck_atk);
        GuardLuck gld = make_guard_luck(luck_def);
        gr = cpp_pre_damage_guards(state, side_idx, defender_idx, move, gla, gld, ctx);
    }
    if (gr.should_abort) return;
    int32_t move_type = gr.move_type;

    // Fixed-damage moves bypass the formula. Doubles: they must honor the resolved
    // target slot (incl. NORMAL auto-retarget) — blindly hitting foe active_indices[0]
    // re-damaged corpses and hit the wrong slot. All fixed-damage moves are
    // single-target NORMAL, so this resolution is draw-free and a no-op in singles;
    // non-empty is guaranteed by the no_target guard above. Mirrors core.py.
    if (cpp_is_fixed_damage_move(move)) {
        auto fd_targets = cpp_resolve_targets(state, side_idx, 0, move,
                                              action.target_side, action.target_slot);
        int fd_side = static_cast<int>(fd_targets.at(0).first);
        int fd_pos = static_cast<int>(fd_targets.at(0).second);
        with_active_slot_swapped(state, fd_side, fd_pos, [&]() {
            PsywaveLuck pl = make_psywave_luck(luck_atk);
            int32_t fixed_dmg = cpp_compute_fixed_damage(move, active_mon(state, side_idx),
                                                         active_mon(state, fd_side), state, side_idx, pl);
            cpp_handle_fixed_damage_action(state, side_idx, fd_side, move, move_type, fixed_dmg,
                                           ctx, luck_atk, luck_def, effective_slot, pending_switches);
        });
        return;
    }

    cpp_handle_damage_action(state, side_idx, defender_idx, move, move_type, ctx, luck_atk, luck_def,
                             effective_slot, gr.effective_acc, gr.effective_acc_is_none, from_dancer,
                             action.target_side, action.target_slot, pending_switches);
}

} // namespace

// ===========================================================================
// Sub-move option builders (public; used by turn.cpp Metronome/Sleep Talk resolution).
// Mirrors src/data/moves.py metronome_options() and sleep_talk_options().
// ===========================================================================

std::vector<int> metronome_options() {
    // Iterate the full move table; skip id 0 (NONE), 165 (Struggle), and METRONOME_EXCLUDED.
    std::vector<int> result;
    for (int i = 0; i < MOVE_TABLE_COUNT; ++i) {
        int32_t mid = MOVE_TABLE[i].move_id;
        if (mid == 0 || mid == MV_STRUGGLE_LOCAL) continue;
        if (in_list(mid, METRONOME_EXCLUDED, (int)(sizeof(METRONOME_EXCLUDED) / sizeof(int32_t)))) continue;
        result.push_back(mid);
    }
    return result;
}

std::vector<int> sleep_talk_options(const PokemonState& mon) {
    // Mon's 4 move slots minus id 0 and SLEEP_TALK_EXCLUDED; slot order, no pp filter.
    std::vector<int> result;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(mon, slot);
        if (mid == 0) continue;
        if (in_list(mid, SLEEP_TALK_EXCLUDED, (int)(sizeof(SLEEP_TALK_EXCLUDED) / sizeof(int32_t)))) continue;
        result.push_back(mid);
    }
    return result;
}

// ===========================================================================
// _apply_dancer_trigger (public; called from move_exec_damage.cpp + the status path).
// ===========================================================================
void cpp_apply_dancer_trigger(BattleState& state, int original_user_idx, int32_t move,
                              ExecCtx& ctx, const DamageLoopLuck& luck_atk,
                              const DamageLoopLuck& luck_def,
                              std::vector<PendingSwitch>& pending_switches) {
    if (!is_dance(move)) return;
    constexpr int32_t AB_DANCER = 216;
    DamageLoopLuck la = luck_atk, ld = luck_def;
    for (int dancer_side_idx = 0; dancer_side_idx < 2; ++dancer_side_idx) {
        SideState& dancer_side = side_at(state, dancer_side_idx);
        std::vector<int32_t> slots(dancer_side.active_indices.begin(), dancer_side.active_indices.end());  // copy: slot-swap mutates the vector
        for (int32_t slot : slots) {
            PokemonState& mon = dancer_side.team[slot];
            if (mon.fainted) continue;
            if (dancer_side_idx == original_user_idx && slot == dancer_side.active_indices[0]) continue;
            if (mon.ability != AB_DANCER) continue;
            ExecAction dancer_action;
            dancer_action.kind = 0;
            dancer_action.move_slot = 0;
            dancer_action.move_override = move;
            // Position of this slot in active_indices (0 if it is already slot 0).
            int pos = 0;
            for (int p = 0; p < (int)dancer_side.active_indices.size(); ++p)
                if (dancer_side.active_indices[p] == slot) { pos = p; break; }
            with_active_slot_swapped(state, dancer_side_idx, pos, [&]() {
                execute_action_body(state, dancer_side_idx, dancer_action, la, ld,
                                    pending_switches, ctx, /*from_dancer*/true);
            });
        }
    }
}

// ===========================================================================
// _execute_action (public).
// ===========================================================================
void cpp_execute_action(BattleState& state, int side_idx, const ExecAction& action,
                        DamageLoopLuck& luck_atk, DamageLoopLuck& luck_def,
                        std::vector<PendingSwitch>& pending_switches,
                        ExecCtx& ctx, int source_slot) {
    if (action.kind == AK_SWITCH) {
        handle_switch_action(state, side_idx, action, ctx, source_slot);
        cpp_flush_opponent_faint_exp(state, ctx.exp_participants);
        return;
    }

    ctx.attacker_slot = source_slot;
    with_active_slot_swapped(state, side_idx, source_slot, [&]() {
        execute_action_body(state, side_idx, action, luck_atk, luck_def,
                            pending_switches, ctx, /*from_dancer*/false);
    });
    cpp_flush_opponent_faint_exp(state, ctx.exp_participants);
}
