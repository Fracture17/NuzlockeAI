// C++ port of the post-damage reaction pipeline (src/engine/post_hit.py, C1.4).
// Only state mutations are reproduced (Python log() calls are state-neutral and omitted).
// Forced-switch requests are appended to pending_switches. Python mutation ORDER is preserved
// exactly so whole-BattleState equality holds. Unported branches throw "unported: ...".
#include "effects.h"
#include "effects_internal.h"
#include "effects_consts.h"
#include "type_chart_lookup.h"
#include "damage.h"  // cpp_check_type_immunity for Weakness Policy
#include "species_exp_lookup.h"    // base stats for _apply_form_change
#include "species_types_lookup.h"  // reset types for _apply_form_change
#include "stats.h"                 // compute_stat for _apply_form_change
#include "move_exec_guards.h"      // ExecCtx (for ctx->overrides in contact effects)
#include "oracle.h"                // oracle_resolve, RngEventC, NeedsRNG
#include "event_log.h"             // rich_log_volatile_apply (secondary confusion)
#include "forced_trace.h"
#include "rng_resolver.h"          // RngLogCtx for participant plumbing

#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

#include <move_data.h>

using namespace eff;
using namespace eff_internal;

// _apply_form_change: recompute all 6 stats + types for a form change. HP grows by the
// max_hp delta when max_hp increases (Power Construct), else is capped to the new max.
// Lives in eff_internal so move_exec_helpers.cpp shares one definition (Gulp Missile revert).
namespace eff_internal {
void apply_form_change(BattleState& s, int side_idx, int32_t new_species) {
    PokemonState& mon = active_mon(s, side_idx);
    SpeciesExpData sp = cpp_species_exp_data(new_species);
    int32_t bases[6] = {sp.base_hp, sp.base_atk, sp.base_def, sp.base_spa, sp.base_spd, sp.base_spe};
    int32_t ivs[6] = {mon.iv_hp, mon.iv_atk, mon.iv_def, mon.iv_spa, mon.iv_spd, mon.iv_spe};
    int32_t new_stats[6];
    for (int i = 0; i < 6; ++i)
        new_stats[i] = compute_stat(i, bases[i], ivs[i], mon.nature, mon.level);
    int32_t new_max_hp = new_stats[0];
    int32_t new_hp = (new_max_hp > mon.max_hp)
                         ? mon.hp + (new_max_hp - mon.max_hp)
                         : std::min(mon.hp, new_max_hp);
    mon.species = new_species;
    mon.has_stats = true;
    mon.stat_hp = new_stats[0]; mon.stat_atk = new_stats[1]; mon.stat_def = new_stats[2];
    mon.stat_spa = new_stats[3]; mon.stat_spd = new_stats[4]; mon.stat_spe = new_stats[5];
    mon.has_max_hp = true; mon.max_hp = new_max_hp;
    mon.has_hp = true; mon.hp = new_hp;
    mon.has_types = true; mon.types.assign_from(cpp_species_types(new_species));
}
} // namespace eff_internal

namespace {

// Build an RngLogCtx attributing (attacker=si, defender=di) with active-slot indices,
// tagged with the current turn number. Used everywhere post_hit resolves a
// secondary/proc/flinch draw so the analytical logger sees full participant info.
inline RngLogCtx make_rng_ctx(BattleState& s, int si, int di) {
    return RngLogCtx{
        RngParticipants{
            (int8_t)si, (int8_t)side_at(s, si).active_indices[0],
            (int8_t)di, (int8_t)side_at(s, di).active_indices[0]},
        s.turn_number};
}

const MoveData& lookup_move_ph(int32_t move_id) {
    int lo = 0, hi = 813;
    while (lo < hi) { int mid = (lo + hi) / 2; if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid; }
    if (lo >= 813 || MOVE_TABLE[lo].move_id != move_id)
        throw std::runtime_error("lookup_move_ph: id " + std::to_string(move_id) + " not found");
    return MOVE_TABLE[lo];
}

// --- named ids (mirror Python enum values) ---
constexpr int32_t M_KNOCK_OFF=282, M_FLING=374, M_TRI_ATTACK=161, M_JAW_LOCK=746,
    M_THOUSAND_WAVES=615, M_THOUSAND_ARROWS=614, M_SMACK_DOWN=479, M_BURN_UP=682,
    M_STEEL_BEAM=796, M_HYPERSPACE_FURY=621, M_SMELLING_SALTS=265, M_WAKE_UP_SLAP=358,
    M_INCINERATE=510, M_PLUCK=365, M_BUG_BITE=450, M_STEEL_ROLLER=798, M_RAPID_SPIN=229,
    M_MORTAL_SPIN=866, M_THROAT_CHOP=675, M_STRUGGLE=165, M_RELIC_SONG=547,
    M_ECHOED_VOICE=497, M_BURNING_JEALOUSY=807, M_SURF=291, M_DIVE=57;

constexpr int32_t I_AIR_BALLOON=541, I_WEAKNESS_POLICY=639, I_EJECT_BUTTON=547, I_RED_CARD=542,
    I_CELL_BATTERY=546, I_SNOWBALL=649, I_ABSORB_BULB=545, I_LUMINOUS_MOSS=648,
    I_KEE_BERRY=687, I_MARANGA_BERRY=688, I_STICKY_BARB=288, I_PROTECTIVE_PADS=880,
    I_SAFETY_GOGGLES=650, I_COVERT_CLOAK=1885, I_KINGS_ROCK=221, I_RAZOR_FANG=327,
    I_THROAT_SPRAY=1118, I_LIFE_ORB=270, I_SHELL_BELL=253;

constexpr int32_t A_JUSTIFIED=154, A_RATTLED=155, A_STAMINA=192, A_WATER_COMPACTION=195,
    A_STEAM_ENGINE=243, A_SAND_SPIT=245, A_COTTON_DOWN=238, A_GULP_MISSILE=241,
    A_STICKY_HOLD=60, A_LONG_REACH=203, A_COLOR_CHANGE=16, A_WEAK_ARMOR=133, A_MAGICIAN=170,
    A_GORILLA_TACTICS=255, A_SHEER_FORCE=125, A_SERENE_GRACE=32, A_SHIELD_DUST=19,
    A_OWN_TEMPO=20, A_MUMMY=152, A_WANDERING_SPIRIT=254, A_GOOEY=183, A_TANGLING_HAIR=221,
    A_PERISH_BODY=253, A_FLAME_BODY=49, A_STATIC=9, A_POISON_POINT=38, A_EFFECT_SPORE=27,
    A_OVERCOAT=142, A_CUTE_CHARM=56, A_OBLIVIOUS=12, A_POISON_TOUCH=143, A_CURSED_BODY=130,
    A_ROCK_HEAD=69, A_BERSERK=201, A_EMERGENCY_EXIT=194, A_WIMP_OUT=193, A_STENCH=1;

constexpr int32_t SP_CRAMORANT=845, SP_CRAMORANT_GULPING=1211, SP_CRAMORANT_GORGING=1212,
    SP_MELOETTA=648, SP_MELOETTA_PIROUETTE=1107;

constexpr int32_t V_CHOICE_LOCKED=262144, V_RECHARGING=256, V_ATTRACTED=8388608, V_CONFUSED=1,
    V_PERISH_SONG_ACTIVE=16384;
// VE_DISABLE / VE_TRAPPED / VE_GROUNDED / VE_BOUND / VE_BOUND_SOURCE_SLOT / VE_THROAT_CHOPPED /
// VE_PERISH_SONG come from effects_consts.h (namespace eff).

constexpr int32_t MOVECAT_PHYSICAL=0, MOVECAT_SPECIAL=1, MOVECAT_STATUS=2;
constexpr int32_t TAG_CONTACT=128, TAG_SOUND=256;

// id sets
const int32_t PIVOT_MOVES[] = {369, 521, 812};
const int32_t PHASING_MOVES[] = {509, 525};
const int32_t BINDING_MOVES[] = {20, 35, 83, 128, 250, 328, 463, 611};
const int32_t TRAP_DEFENDER_MOVES[] = {662, 677};
const int32_t RECHARGE_MOVES[] = {63, 307, 308, 338, 416, 439, 794};
const int32_t DEFROST_TARGET_MOVES[] = {221, 503, 682, 815};
const int32_t CHOICE_ITEMS[] = {220, 287, 297};
const int32_t MEGA_ITEMS[] = {40,41,573,575,576,577,578,579,580,582,583,584,585,586,587,588,589,
    590,591,592,594,596,598,599,602,605,607,608,612,613,614,615,616,617,618,619,620,621,622,623,
    625,626,627,628,629,630};
const int32_t MEMORY_ITEMS[] = {901,902,903,904,905,906,907,908,909,910,911,912,913,914,915,916,917};
const int32_t SILVALLY_SPECIES[] = {773,1176,1177,1178,1179,1180,1181,1182,1183,1184,1185,1186,
    1187,1188,1189,1190,1191,1192};
const int32_t SPIN_HAZARDS[] = {SC_STEALTH_ROCK, SC_SPIKES_1, SC_SPIKES_2, SC_SPIKES_3,
    SC_TOXIC_SPIKES_1, SC_TOXIC_SPIKES_2, SC_STICKY_WEB};

template <size_t N> bool in_set(const int32_t (&arr)[N], int32_t v) {
    for (int32_t x : arr) if (x == v) return true; return false;
}

// Gem item id -> Type (src/engine/damage.py _GEM_ITEMS). NOTE: gem ids are NOT a clean
// (item-4000)==Type mapping — Grass (4003) and Electric (4004) are transposed relative to the
// Type enum (ELECTRIC=3, GRASS=4), so those two must be handled explicitly.
int32_t gem_type(int32_t item) {
    if (item == 564) return TYPE_NORMAL;        // Normal Gem
    if (item == 4003) return TYPE_GRASS;        // Grass Gem
    if (item == 4004) return TYPE_ELECTRIC;     // Electric Gem
    if (item >= 4001 && item <= 4017) return item - 4000;
    return -1;
}

// CANTSUPPRESS abilities (Mummy / Wandering Spirit identity guard).
const int32_t CANTSUPPRESS_IDS[] = {
    // MULTITYPE, STANCE_CHANGE, POWER_CONSTRUCT, RKS_SYSTEM, SCHOOLING, COMATOSE, BATTLE_BOND,
    // SHIELDS_DOWN, ZEN_MODE, AS_ONE_GLASTRIER, AS_ONE_SPECTRIER, NONE, DISGUISE, ICE_FACE,
    // GULP_MISSILE, MUMMY, WANDERING_SPIRIT
    121, 176, 211, 225, 208, 213, 210, 197, 161, 266, 267, 0, 209, 248, 241, 152, 254};
bool cantsuppress(int32_t ability) { return in_set(CANTSUPPRESS_IDS, ability); }

bool is_memory_item(int32_t it) { return in_set(MEMORY_ITEMS, it); }
bool is_silvally(int32_t sp) { return in_set(SILVALLY_SPECIES, sp); }

bool bench_exists(BattleState& s, int side_idx) {
    SideState& side = side_at(s, side_idx);
    for (size_t i = 0; i < side.team.size(); ++i) {
        bool active = false;
        for (int32_t ai : side.active_indices) if ((int)i == ai) { active = true; break; }
        if (!active && !side.team[i].fainted) return true;
    }
    return false;
}

// ===========================================================================
// _apply_post_hit_items
// ===========================================================================
void apply_post_hit_items(BattleState& s, const PostHitArgs& a,
                          std::vector<PendingSwitch>& pending, const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;
    int32_t move = a.move, move_type = a.move_type;
    const MoveData& md = lookup_move_ph(move);

    // Knock Off
    if (move == M_KNOCK_OFF) {
        PokemonState& attacker = active_mon(s, si);
        PokemonState& defender = active_mon(s, di);
        bool knock_sticky = (defender.ability == A_STICKY_HOLD
                             && !is_mold_breaker(attacker.ability)
                             && defender.item != I_STICKY_BARB);
        if (defender.item != ITEM_NONE && !is_mega_item(defender.item)
            && !(is_silvally(defender.species) && is_memory_item(defender.item))
            && !knock_sticky) {
            defender.item = ITEM_NONE;
            apply_unburden(s, di);
        }
    }

    // Air Balloon
    {
        PokemonState& defender = active_mon(s, di);
        if (defender.item == I_AIR_BALLOON && !a.hit_sub) defender.item = ITEM_NONE;
    }

    // Fling
    if (move == M_FLING) {
        PokemonState& attacker = active_mon(s, si);
        if (!attacker.fainted) { attacker.item = ITEM_NONE; apply_unburden(s, si); }
    }

    // Weakness Policy: +2 Atk and +2 SpA when hit by a super-effective move; not on KO.
    {
        PokemonState& defender = active_mon(s, di);
        if (defender.item == I_WEAKNESS_POLICY && !defender.fainted && !a.hit_sub) {
            const PokemonState& attacker = active_mon(s, si);
            double eff = cpp_check_type_immunity(attacker, move, move_type, defender, s);
            if (eff > 1.0) {
                defender.item = ITEM_NONE;
                change_stat_stage(s, di, 0, +2, false, false, false);  // Atk +2
                change_stat_stage(s, di, 2, +2, false, false, false);  // SpA +2
            }
        }
    }

    // On-hit stat items
    {
        PokemonState& defender = active_mon(s, di);
        int32_t it = defender.item;
        int stat_idx = -1; bool by_type = false; int32_t expected = 0;
        if      (it == I_CELL_BATTERY)  { stat_idx = 0; by_type = true;  expected = TYPE_ELECTRIC; }
        else if (it == I_SNOWBALL)      { stat_idx = 0; by_type = true;  expected = TYPE_ICE; }
        else if (it == I_ABSORB_BULB)   { stat_idx = 2; by_type = true;  expected = TYPE_WATER; }
        else if (it == I_LUMINOUS_MOSS) { stat_idx = 3; by_type = true;  expected = TYPE_WATER; }
        else if (it == I_KEE_BERRY)     { stat_idx = 1; by_type = false; expected = MOVECAT_PHYSICAL; }
        else if (it == I_MARANGA_BERRY) { stat_idx = 3; by_type = false; expected = MOVECAT_SPECIAL; }
        if (stat_idx >= 0 && !defender.fainted && !a.hit_sub && md.category != MOVECAT_STATUS) {
            bool triggered = by_type ? (move_type == expected) : (md.category == expected);
            if (triggered) {
                int32_t consumed = it;
                if (is_berry(consumed)) {
                    defender.item = ITEM_NONE; defender.consumed_berry = consumed;
                    change_stat_stage(s, di, stat_idx, +1, false, false, false);
                    // _on_berry_consumed: Cheek Pouch heal + Symbiosis (no-op in singles) + Unburden.
                    PokemonState& holder = active_mon(s, di);
                    if (holder.ability == /*CHEEK_POUCH*/ 167) {
                        int32_t extra = std::max<int32_t>(1, holder.max_hp / 3);
                        int32_t hp_before_pouch = holder.hp;
                        holder.hp = std::min<int32_t>(holder.max_hp, holder.hp + extra);
                        // HEAL source=cheek_pouch (Python _helpers.py:679): emit
                        // unconditionally, mirroring effects.cpp on_berry_consumed.
                        rich_log_heal(s.turn_number, holder.species,
                                      holder.hp - hp_before_pouch, holder.hp, di,
                                      SourceTag::CHEEK_POUCH);
                    }
                    apply_unburden(s, di);
                } else {
                    defender.item = ITEM_NONE;
                    change_stat_stage(s, di, stat_idx, +1, false, false, false);
                    apply_unburden(s, di);
                }
            }
        }
    }

    // Eject Button / Red Card (mutually exclusive: else branch)
    {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && defender.item == I_EJECT_BUTTON) {
            if (bench_exists(s, di)) { defender.item = ITEM_NONE; pending.push_back({di, "eject_button"}); }
        } else {
            PokemonState& d2 = active_mon(s, di);
            if (!d2.fainted && d2.item == I_RED_CARD) {
                if (bench_exists(s, si)) { d2.item = ITEM_NONE; pending.push_back({si, "red_card"}); }
            }
        }
    }
}

// ===========================================================================
// _apply_on_hit_ability_reactions
// ===========================================================================
void apply_on_hit_ability_reactions(BattleState& s, const PostHitArgs& a, bool /*mold_breaker*/) {
    int si = a.side_idx, di = a.defender_idx;
    int32_t move = a.move, mt = a.move_type;

    if (active_mon(s, di).ability == A_JUSTIFIED && mt == TYPE_DARK && !a.hit_sub)
        change_stat_stage(s, di, 0, +1, false, false, false);
    if (active_mon(s, di).ability == A_RATTLED && (mt == TYPE_BUG || mt == TYPE_GHOST || mt == TYPE_DARK))
        change_stat_stage(s, di, 4, +1, false, false, false);
    if (active_mon(s, di).ability == A_STAMINA)
        change_stat_stage(s, di, 1, +1, false, false, false);
    if (active_mon(s, di).ability == A_WATER_COMPACTION && mt == TYPE_WATER)
        change_stat_stage(s, di, 1, +2, false, false, false);
    if (active_mon(s, di).ability == A_STEAM_ENGINE && (mt == TYPE_FIRE || mt == TYPE_WATER) && !a.hit_sub)
        change_stat_stage(s, di, 4, +6, false, false, false);
    if (active_mon(s, di).ability == A_SAND_SPIT) { s.weather = WEATHER_SANDSTORM; s.weather_turns = -1; }
    if (active_mon(s, di).ability == A_COTTON_DOWN)
        change_stat_stage(s, si, 4, -1, false, false, false);

    // Gulp Missile: Cramorant "gulps" a fish after using Surf or Dive.
    if (move == M_SURF || move == M_DIVE) {
        PokemonState& atk = active_mon(s, si);
        if (atk.ability == A_GULP_MISSILE && !atk.fainted
            && (atk.species == SP_CRAMORANT || atk.species == SP_CRAMORANT_GULPING
                || atk.species == SP_CRAMORANT_GORGING)) {
            int32_t form = (atk.hp > atk.max_hp / 2) ? SP_CRAMORANT_GULPING : SP_CRAMORANT_GORGING;
            apply_form_change(s, si, form);
        }
    }
    // Relic Song: toggle Meloetta form after hitting.
    if (move == M_RELIC_SONG) {
        PokemonState& atk = active_mon(s, si);
        if (atk.species == SP_MELOETTA)
            apply_form_change(s, si, SP_MELOETTA_PIROUETTE);
        else if (atk.species == SP_MELOETTA_PIROUETTE)
            apply_form_change(s, si, SP_MELOETTA);
    }
}

// ===========================================================================
// _apply_contact_effects
// ===========================================================================
void apply_contact_effects(BattleState& s, const PostHitArgs& a, bool mold_breaker,
                           const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;

    if (active_mon(s, si).item != I_PROTECTIVE_PADS) {
        if (!active_mon(s, di).fainted) {
            // Mummy
            if (active_mon(s, di).ability == A_MUMMY) {
                if (!cantsuppress(active_mon(s, si).base_ability))
                    active_mon(s, si).ability = A_MUMMY;
            } else if (active_mon(s, di).ability == A_WANDERING_SPIRIT) {
                if (!cantsuppress(active_mon(s, si).base_ability)) {
                    int32_t atk_ab = active_mon(s, si).ability;
                    int32_t def_ab = active_mon(s, di).ability;
                    active_mon(s, si).ability = def_ab;
                    active_mon(s, di).ability = atk_ab;
                }
            }
            // Sticky Barb transfer
            if (active_mon(s, di).item == I_STICKY_BARB && active_mon(s, si).item == ITEM_NONE) {
                active_mon(s, si).item = I_STICKY_BARB;
                active_mon(s, di).item = ITEM_NONE;
            }
            // Gooey / Tangling Hair
            if (active_mon(s, di).ability == A_GOOEY || active_mon(s, di).ability == A_TANGLING_HAIR) {
                if (!active_mon(s, si).fainted)
                    change_stat_stage(s, si, 4, -1, false, false, false);
            }
            // Perish Body
            if (active_mon(s, di).ability == A_PERISH_BODY) {
                if (!(active_mon(s, si).volatiles & V_PERISH_SONG_ACTIVE)) {
                    for (int idx : {si, di}) {
                        PokemonState& t = active_mon(s, idx);
                        if (!(t.volatiles & V_PERISH_SONG_ACTIVE)) {
                            t.volatiles |= V_PERISH_SONG_ACTIVE;
                            t.timed_volatiles.push_back({VE_PERISH_SONG, 4});
                        }
                    }
                }
            }
        }

        // Flame Body / Static / Poison Point (30%)
        if (!active_mon(s, si).fainted) {
            int32_t contact_status = STATUS_NONE;
            int32_t dab = active_mon(s, di).ability;
            if (dab == A_FLAME_BODY) contact_status = STATUS_BURN;
            else if (dab == A_STATIC) contact_status = STATUS_PARALYSIS;
            else if (dab == A_POISON_POINT) contact_status = STATUS_POISON;
            const RngLogCtx contact_ctx = make_rng_ctx(s, si, di);
            if (contact_status != STATUS_NONE && resolve_proc_det(30, luck, &contact_ctx)) {
                if (can_apply_status(active_mon(s, si), contact_status, MOVE_NONE, AB_NONE, s)) {
                    apply_status_to(s, si, contact_status);
                    check_status_berry(s, si, di);
                }
            }
        }

        // Effect Spore (30%): SLEEP (11/30), PARALYSIS (10/30), POISON (9/30).
        // random_mode draws the status natively via rng->randint(1,30) mirroring Python's
        // else-branch (post_hit.py:325). Controlled mode uses oracle_resolve: if an override
        // is set in ctx->overrides, it is used; otherwise NeedsRNG is thrown so the driver pauses.
        if (!active_mon(s, si).fainted && active_mon(s, di).ability == A_EFFECT_SPORE) {
            PokemonState& atk = active_mon(s, si);
            const RngLogCtx spore_ctx = make_rng_ctx(s, si, di);
            if (!has_type(atk, TYPE_GRASS) && atk.item != I_SAFETY_GOGGLES
                && atk.ability != A_OVERCOAT && resolve_proc_det(30, luck, &spore_ctx)) {
                int32_t spore_status;
                if (luck.random_mode) {
                    if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
                    if (luck.rng->forced) {
                        // Consume the Cat-A answer; mirrors Python post_hit.py:325 pause condition.
                        const ForcedAnswer& fa = luck.rng->forced->next_answer(luck.rng->current_turn, RngEventC::EFFECT_SPORE_WHICH, -1);
                        spore_status = fa.i0;
                    } else {
                        int r = luck.rng->randint(1, 30);
                        spore_status = (r <= 11) ? STATUS_SLEEP : (r <= 21 ? STATUS_PARALYSIS : STATUS_POISON);
                    }
                } else {
                    // pre_inject_or_oracle: checks pre_inject map first (plain-mode sweep hook),
                    // then falls through to oracle_resolve (throws NeedsRNG if no answer).
                    const OracleOverrides* ov = (a.ctx ? a.ctx->overrides : nullptr);
                    const std::unordered_map<int,int>* pinj = (a.ctx ? a.ctx->pre_inject : nullptr);
                    // Effect Spore is a defender ability firing on the attacker: participants
                    // are (attacker=si, defender=di); we store (si, di) as (side, opp).
                    RngParticipants who{
                        (int8_t)si, (int8_t)side_at(s, si).active_indices[0],
                        (int8_t)di, (int8_t)side_at(s, di).active_indices[0]};
                    spore_status = pre_inject_or_oracle(pinj, ov, RngEventC::EFFECT_SPORE_WHICH,
                                                        {STATUS_SLEEP, STATUS_PARALYSIS, STATUS_POISON},
                                                        who, s.turn_number);
                }
                if (can_apply_status(active_mon(s, si), spore_status, MOVE_NONE, AB_NONE, s)) {
                    apply_status_to(s, si, spore_status);
                    check_status_berry(s, si, di);
                }
            }
        }

        // Cute Charm (30%)
        if (!active_mon(s, si).fainted && active_mon(s, di).ability == A_CUTE_CHARM
            && !a.hit_sub) {
            PokemonState& atk = active_mon(s, si);
            const RngLogCtx cc_ctx = make_rng_ctx(s, si, di);
            if (atk.ability != A_OBLIVIOUS && atk.ability != A_OWN_TEMPO
                && !(atk.volatiles & V_ATTRACTED) && resolve_proc_det(30, luck, &cc_ctx))
                atk.volatiles |= V_ATTRACTED;
        }
    }

    // Poison Touch (attacker ability, 30%)
    {
        PokemonState& defender = active_mon(s, di);
        bool blocked = ((defender.ability == A_SHIELD_DUST && !mold_breaker)
                        || defender.item == I_COVERT_CLOAK);
        const RngLogCtx pt_ctx = make_rng_ctx(s, si, di);
        if (!defender.fainted && active_mon(s, si).ability == A_POISON_TOUCH
            && !blocked && resolve_proc_det(30, luck, &pt_ctx)) {
            if (can_apply_status(active_mon(s, di), STATUS_POISON, MOVE_NONE, AB_NONE, s)) {
                apply_status_to(s, di, STATUS_POISON);
                check_status_berry(s, di, si);
            }
        }
    }

    // Cursed Body (30%)
    {
        PokemonState& attacker = active_mon(s, si);
        const RngLogCtx cb_ctx = make_rng_ctx(s, si, di);
        if (active_mon(s, di).ability == A_CURSED_BODY && !attacker.fainted && !a.hit_sub
            && !has_timed_volatile(attacker, VE_DISABLE) && resolve_proc_det(30, luck, &cb_ctx))
            active_mon(s, si).timed_volatiles.push_back({VE_DISABLE, 4});
    }
}

// ===========================================================================
// secondary effect appliers
// ===========================================================================
void sec_standard_secondary(BattleState& s, const PostHitArgs& a, bool mold_breaker,
                            const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;
    const MoveData& md = lookup_move_ph(a.move);
    const SecondaryEffect& sec = md.secondary;
    PokemonState atk_snapshot = active_mon(s, si);  // attacker fetched once at entry (matches Python)
    // Mirror Python's `move_data.secondary is not None` as `sec.chance != 0` (record
    // secondary_is_chance_nonzero), NOT field-decomposition: Tri Attack has chance=20 with all
    // fields empty (its status is oracle-picked), so field-decomposition wrongly returned early.
    if (!(a.damage > 0 && sec.chance != 0 && atk_snapshot.ability != A_SHEER_FORCE))
        return;
    int eff_chance = (atk_snapshot.ability == A_SERENE_GRACE) ? sec.chance * 2 : sec.chance;
    const RngLogCtx sec_ctx = make_rng_ctx(s, si, di);
    bool flinch_only = sec.flinch && !sec.has_status && sec.num_stat_changes == 0 && sec.volatile_confused != 1;
    if (flinch_only) {
        bool sd = (active_mon(s, di).ability == A_SHIELD_DUST && !mold_breaker);
        if (!sd && resolve_flinch_det(eff_chance, luck, &sec_ctx)) try_apply_flinch(s, di, mold_breaker);
        return;
    }
    if (!resolve_secondary_det(eff_chance, luck, &sec_ctx)) return;
    bool sd = (active_mon(s, di).ability == A_SHIELD_DUST && !mold_breaker);
    if (a.move == M_TRI_ATTACK && !sd) {
        // random_mode picks BURN/FREEZE/PARALYSIS uniformly via rng->choice, mirroring Python's
        // else-branch random.choice (post_hit.py:411). Controlled mode uses oracle_resolve: an
        // override in ctx->overrides is honored, otherwise NeedsRNG is thrown so the driver pauses.
        int32_t chosen;
        if (luck.random_mode) {
            if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
            if (luck.rng->forced) {
                // Consume the Cat-A answer; mirrors Python post_hit.py:411 pause condition.
                const ForcedAnswer& fa = luck.rng->forced->next_answer(luck.rng->current_turn, RngEventC::TRI_ATTACK_STATUS, -1);
                chosen = fa.i0;
            } else {
                chosen = luck.rng->choice({STATUS_BURN, STATUS_FREEZE, STATUS_PARALYSIS});
            }
        } else {
            const OracleOverrides* ov = (a.ctx ? a.ctx->overrides : nullptr);
            const std::unordered_map<int,int>* pinj = (a.ctx ? a.ctx->pre_inject : nullptr);
            RngParticipants who{
                (int8_t)si, (int8_t)side_at(s, si).active_indices[0],
                (int8_t)di, (int8_t)side_at(s, di).active_indices[0]};
            chosen = pre_inject_or_oracle(pinj, ov, RngEventC::TRI_ATTACK_STATUS,
                                          {STATUS_BURN, STATUS_FREEZE, STATUS_PARALYSIS},
                                          who, s.turn_number);
        }
        if (can_apply_status(active_mon(s, di), chosen, a.move, atk_snapshot.ability, s)) {
            apply_status_to(s, di, chosen);
            check_status_berry(s, di, si);
        }
    }
    if (sec.has_status && !sd) {
        if (can_apply_status(active_mon(s, di), sec.status, a.move, atk_snapshot.ability, s)) {
            apply_status_to(s, di, sec.status);
            check_status_berry(s, di, si);
        }
    }
    if (sec.flinch && !sd) try_apply_flinch(s, di, mold_breaker);
    for (int i = 0; i < sec.num_stat_changes; ++i) {
        const StatChangeEntry& sc = sec.stat_changes[i];
        bool self = sc.self_flag != 0;
        int target = self ? si : di;
        if (self || !sd) {
            // Mirrors Python sec_standard_secondary: ctx not passed here (item consumed, no switch queued).
            // Eject Pack from secondary stat drops is intentionally NOT queued in Python (ctx=None path).
            // Status-move stat drops (apply_interaction_move) DO pass ctx and correctly queue the switch.
            change_stat_stage(s, target, sc.stat_idx, sc.delta,
                              /*opp*/!self, /*ignore_simple*/(mold_breaker && !self),
                              /*mb*/(mold_breaker && !self), /*ctx*/nullptr);
            if (sc.delta < 0 && !self)
                on_stat_dropped(s, di, sc.stat_idx, a.competitive_defiant_triggered);
        }
    }
    if (sec.volatile_confused == 1 && !sd) {
        PokemonState& defender = active_mon(s, di);
        if (!(defender.volatiles & V_CONFUSED) && defender.ability != A_OWN_TEMPO
            && !(s.terrain == TERRAIN_MISTY && is_grounded(defender, s))) {
            defender.volatiles |= V_CONFUSED;
            rich_log_volatile_apply(s.turn_number, defender.species, VolatileTag::CONFUSED, di, SourceTag::MOVE);
        }
    }
}

void sec_burning_jealousy(BattleState& s, const PostHitArgs& a) {
    int si = a.side_idx, di = a.defender_idx;
    if (a.move == M_ECHOED_VOICE && a.damage > 0) s.echoed_voice_used_this_turn = true;
    if (a.move == M_BURNING_JEALOUSY && a.damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        PokemonState& defender = active_mon(s, di);
        if (attacker.ability != A_SHEER_FORCE && defender.had_stat_raised_this_turn && !defender.fainted) {
            if (can_apply_status(defender, STATUS_BURN, a.move, attacker.ability, s)) {
                apply_status_to(s, di, STATUS_BURN);
                check_status_berry(s, di, si);
            }
        }
    }
}

void sec_secondary2(BattleState& s, const PostHitArgs& a, bool mold_breaker, const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;
    const MoveData& md = lookup_move_ph(a.move);
    const SecondaryEffect& sec2 = md.secondary2;
    bool has_sec2 = sec2.has_status || sec2.flinch || sec2.num_stat_changes > 0 || sec2.has_volatile;
    PokemonState attacker = active_mon(s, si);
    if (!(a.damage > 0 && has_sec2 && attacker.ability != A_SHEER_FORCE)) return;
    int eff_chance2 = (attacker.ability == A_SERENE_GRACE) ? sec2.chance * 2 : sec2.chance;
    const RngLogCtx sec2_ctx = make_rng_ctx(s, si, di);
    bool flinch_only2 = sec2.flinch && !sec2.has_status && sec2.num_stat_changes == 0;
    if (flinch_only2) {
        bool sd = (active_mon(s, di).ability == A_SHIELD_DUST && !mold_breaker);
        if (!sd && resolve_flinch_det(eff_chance2, luck, &sec2_ctx)) try_apply_flinch(s, di, mold_breaker);
        return;
    }
    if (!resolve_secondary_det(eff_chance2, luck, &sec2_ctx)) return;
    bool sd = (active_mon(s, di).ability == A_SHIELD_DUST && !mold_breaker);
    if (sec2.has_status && !sd) {
        if (can_apply_status(active_mon(s, di), sec2.status, a.move, attacker.ability, s)) {
            apply_status_to(s, di, sec2.status);
            check_status_berry(s, di, si);
        }
    }
    if (sec2.flinch && !sd) try_apply_flinch(s, di, mold_breaker);
}

void sec_self_stat_changes(BattleState& s, const PostHitArgs& a) {
    const MoveData& md = lookup_move_ph(a.move);
    if (a.damage > 0 && md.num_self_stat_changes > 0)
        for (int i = 0; i < md.num_self_stat_changes; ++i)
            change_stat_stage(s, a.side_idx, md.self_stat_changes[i].stat_idx,
                              md.self_stat_changes[i].delta, false, false, false);
}

void sec_item_and_ability_flinch(BattleState& s, const PostHitArgs& a, bool mold_breaker,
                                 const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;
    const MoveData& md = lookup_move_ph(a.move);
    PokemonState attacker = active_mon(s, si);
    bool move_has_flinch = md.secondary.flinch;
    const RngLogCtx iaf_ctx = make_rng_ctx(s, si, di);
    if (a.damage > 0 && (attacker.item == I_KINGS_ROCK || attacker.item == I_RAZOR_FANG)) {
        if (!move_has_flinch) {
            if (!active_mon(s, di).fainted && resolve_flinch_det(10, luck, &iaf_ctx))
                try_apply_flinch(s, di, mold_breaker);
        }
    }
    if (attacker.ability == A_STENCH && a.damage > 0 && !move_has_flinch) {
        PokemonState& defender = active_mon(s, di);
        bool sd = ((defender.ability == A_SHIELD_DUST && !mold_breaker) || defender.item == I_COVERT_CLOAK);
        if (!defender.fainted && !sd && resolve_flinch_det(10, luck, &iaf_ctx))
            try_apply_flinch(s, di, mold_breaker);
    }
}

void apply_secondary_effects(BattleState& s, const PostHitArgs& a, const EffectsLuck& luck) {
    bool mold_breaker = is_mold_breaker(active_mon(s, a.side_idx).ability);
    sec_standard_secondary(s, a, mold_breaker, luck);
    sec_burning_jealousy(s, a);
    sec_secondary2(s, a, mold_breaker, luck);
    sec_self_stat_changes(s, a);
    sec_item_and_ability_flinch(s, a, mold_breaker, luck);
}

} // namespace

namespace eff_internal {
// Mega stones + primal orbs (Blue/Red Orb live in MEGA_ITEMS). Exposed for the C1.7e turn driver.
bool is_mega_item(int32_t item) { return in_set(MEGA_ITEMS, item); }
} // namespace eff_internal

// ===========================================================================
// _apply_post_hit_effects
// ===========================================================================
void cpp_apply_post_hit_effects(BattleState& s, const PostHitArgs& a,
                                std::vector<PendingSwitch>& pending, const EffectsLuck& luck) {
    int si = a.side_idx, di = a.defender_idx;
    int32_t move = a.move, mt = a.move_type;
    int damage = a.damage, actual_damage = a.actual_damage;
    const MoveData& md = lookup_move_ph(move);

    // attacker snapshot passed by caller = active mon at side_idx (pre-hit).
    bool mold_breaker = is_mold_breaker(active_mon(s, si).ability);
    bool is_contact = (md.tags & TAG_CONTACT) && active_mon(s, si).ability != A_LONG_REACH;

    if (damage > 0) {
        apply_post_hit_items(s, a, pending, luck);
        apply_on_hit_ability_reactions(s, a, mold_breaker);

        // Color Change
        {
            PokemonState& defender = active_mon(s, di);
            if (!defender.fainted && defender.ability == A_COLOR_CHANGE && !a.hit_sub
                && !has_type(defender, mt)) {
                defender.types.clear();
                defender.types.push_back(mt);
                defender.has_types = true;
            }
        }
        // Gem consumption
        {
            PokemonState& attacker = active_mon(s, si);
            int32_t gt = gem_type(attacker.item);
            if (gt >= 0 && gt == mt) {
                bool magic_room = false;
                for (const auto& e : s.pseudo_weather) if (e.effect == /*MAGIC_ROOM*/ 3) magic_room = true;
                if (!magic_room) attacker.item = ITEM_NONE;
            }
        }
        // Choice lock / Gorilla Tactics
        {
            PokemonState& attacker = active_mon(s, si);
            bool is_choice = in_set(CHOICE_ITEMS, attacker.item);
            if (is_choice && !(attacker.volatiles & V_CHOICE_LOCKED)) {
                attacker.volatiles |= V_CHOICE_LOCKED;
                attacker.locked_slot = a.effective_slot;
            } else if (attacker.ability == A_GORILLA_TACTICS && !(attacker.volatiles & V_CHOICE_LOCKED)) {
                attacker.volatiles |= V_CHOICE_LOCKED;
                attacker.locked_slot = a.effective_slot;
            }
        }
    }

    // Magician
    if (damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        PokemonState& defender = active_mon(s, di);
        bool magician_sticky = (defender.ability == A_STICKY_HOLD && !is_mold_breaker(attacker.ability));
        if (attacker.ability == A_MAGICIAN && attacker.item == ITEM_NONE && !defender.fainted
            && defender.item != ITEM_NONE && !is_mega_item(defender.item) && !magician_sticky) {
            attacker.item = defender.item;
            defender.item = ITEM_NONE;
        }
    }

    // Weak Armor
    if (damage > 0 && !a.hit_sub && md.category == MOVECAT_PHYSICAL) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && defender.ability == A_WEAK_ARMOR) {
            change_stat_stage(s, di, 1, -1, false, false, false);
            change_stat_stage(s, di, 4, +2, false, false, false);
        }
    }

    if (is_contact && !a.hit_sub && damage > 0)
        apply_contact_effects(s, a, mold_breaker, luck);

    // Trapping moves (ANCHOR_SHOT, SPIRIT_SHACKLE): apply TRAPPED + TRAPPED_SOURCE_ID to defender.
    if (in_set(TRAP_DEFENDER_MOVES, move) && damage > 0 && active_mon(s, si).ability != A_SHEER_FORCE) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && !has_timed_volatile(defender, VE_TRAPPED)) {
            int32_t atk_team_idx = side_at(s, si).active_indices[a.attacker_slot];
            defender.timed_volatiles.push_back({VE_TRAPPED, -1});
            defender.timed_volatiles.push_back({VE_TRAPPED_SOURCE_ID, atk_team_idx});
        }
    }
    // Jaw Lock: traps both attacker and defender; each records the OTHER mon as TRAPPED_SOURCE_ID.
    if (move == M_JAW_LOCK && damage > 0) {
        int32_t jaw_atk_team_idx = side_at(s, si).active_indices[a.attacker_slot];
        int32_t jaw_def_team_idx = side_at(s, di).active_indices[0];
        // Python calls faint_active (which calls release_inflicted_traps) BEFORE post_hit runs.
        // If the defender fainted this hit, Python already stripped any of the attacker's TRAPPED
        // that the defender was inflicting. Mirror that: if defender fainted, strip the attacker's
        // TRAPPED+SOURCE_ID where SOURCE_ID matches the fainted defender's team index.
        if (active_mon(s, di).fainted) {
            PokemonState& atk = active_mon(s, si);
            bool has_source = false;
            for (const auto& tv : atk.timed_volatiles)
                if (tv.effect == VE_TRAPPED_SOURCE_ID && tv.turns == jaw_def_team_idx) { has_source = true; break; }
            if (has_source) {
                std::vector<TimedVolatile> kept;
                for (const auto& tv : atk.timed_volatiles)
                    if (tv.effect != VE_TRAPPED && tv.effect != VE_TRAPPED_SOURCE_ID) kept.push_back(tv);
                atk.timed_volatiles.assign_from(kept);
            }
        }
        for (auto [trap_idx, source_team_idx] :
             {std::make_pair(si, jaw_def_team_idx), std::make_pair(di, jaw_atk_team_idx)}) {
            PokemonState& t = active_mon(s, trap_idx);
            if (!t.fainted && !has_timed_volatile(t, VE_TRAPPED)) {
                t.timed_volatiles.push_back({VE_TRAPPED, -1});
                t.timed_volatiles.push_back({VE_TRAPPED_SOURCE_ID, source_team_idx});
            }
        }
    }
    // Thousand Waves
    if (move == M_THOUSAND_WAVES && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && !has_timed_volatile(defender, VE_TRAPPED)) {
            int32_t tw_atk_team_idx = side_at(s, si).active_indices[a.attacker_slot];
            defender.timed_volatiles.push_back({VE_TRAPPED, -1});
            defender.timed_volatiles.push_back({VE_TRAPPED_SOURCE_ID, tw_atk_team_idx});
        }
    }
    // Thousand Arrows / Smack Down
    if ((move == M_THOUSAND_ARROWS || move == M_SMACK_DOWN) && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && !has_timed_volatile(defender, VE_GROUNDED))
            defender.timed_volatiles.push_back({VE_GROUNDED, -1});
    }
    // Burn Up
    if (move == M_BURN_UP && damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        if (!attacker.fainted) {
            std::vector<int32_t> nt;
            for (int32_t t : attacker.types) if (t != TYPE_FIRE) nt.push_back(t);
            if (nt.empty()) nt.push_back(18); // TYPELESS
            attacker.types.assign_from(nt); attacker.has_types = true;
        }
    }
    // Steel Beam
    if (move == M_STEEL_BEAM && damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        if (!attacker.fainted && attacker.ability != AB_MAGIC_GUARD) {
            int32_t cost = std::max(1, attacker.max_hp / 2);
            int32_t nh = std::max(0, attacker.hp - cost);
            attacker.hp = nh;
            if (nh == 0) cpp_faint_active(s, si, /*notify_soul_heart=*/false);
        }
    }
    // Hyperspace Fury
    if (move == M_HYPERSPACE_FURY && damage > 0) {
        if (!active_mon(s, si).fainted) change_stat_stage(s, si, 1, -1, false, false, false);
    }
    // Smelling Salts
    if (move == M_SMELLING_SALTS && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && defender.status == STATUS_PARALYSIS) defender.status = STATUS_NONE;
    }
    // Wake-Up Slap
    if (move == M_WAKE_UP_SLAP && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && defender.status == STATUS_SLEEP) defender.status = STATUS_NONE;
    }
    // Incinerate
    if (move == M_INCINERATE && damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        PokemonState& defender = active_mon(s, di);
        bool sticky = (defender.ability == A_STICKY_HOLD && !is_mold_breaker(attacker.ability));
        if (!defender.fainted && is_berry(defender.item) && !sticky) {
            defender.item = ITEM_NONE; apply_unburden(s, di);
        }
    }
    // Pluck / Bug Bite: steal and consume the defender's held Berry.
    if ((move == M_PLUCK || move == M_BUG_BITE) && damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        PokemonState& defender = active_mon(s, di);
        bool sticky = (defender.ability == A_STICKY_HOLD && !is_mold_breaker(attacker.ability));
        if (!defender.fainted && is_berry(defender.item) && !sticky) {
            int32_t stolen = defender.item;
            defender.item = ITEM_NONE;
            apply_unburden(s, di);
            PokemonState& thief = active_mon(s, si);
            if (!thief.fainted) {
                thief.item = stolen;
                thief.consumed_berry = stolen;
                check_berry(s, si, di, luck.rng, luck.overrides);
                check_status_berry(s, si, di);
            }
        }
    }
    // Steel Roller
    if (move == M_STEEL_ROLLER && damage > 0) { s.terrain = TERRAIN_NONE; s.terrain_turns = 0; }
    // Binding moves
    if (in_set(BINDING_MOVES, move) && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted && !has_type(defender, TYPE_GHOST) && !has_timed_volatile(defender, VE_BOUND)) {
            // resolve_binding_duration: Grip Claw=7. random_mode forced → consume BINDING_DURATION int;
            // rng.py:519 _roll_categorical(RNGEvent.BINDING_DURATION, [4, 5]); p=0.5 each.
            int32_t duration;
            // Grip Claw item id: 286.
            if (active_mon(s, si).item == 286) duration = 7;
            else duration = rng_resolve_binding_duration(
                luck.random_mode, luck.rng, luck.binding_duration_roll);
            int32_t attacker_team_idx = side_at(s, si).active_indices[a.attacker_slot];
            defender.timed_volatiles.push_back({VE_BOUND, duration});
            defender.timed_volatiles.push_back({VE_BOUND_SOURCE_SLOT, a.attacker_slot});
            defender.timed_volatiles.push_back({VE_BOUND_SOURCE_ID, attacker_team_idx});
        }
    }
    // Pivot / Phasing
    if (in_set(PIVOT_MOVES, move) && damage > 0) {
        if (bench_exists(s, si)) pending.push_back({si, "u_turn"});
    } else if (in_set(PHASING_MOVES, move) && damage > 0) {
        if (!active_mon(s, di).fainted && bench_exists(s, di)) pending.push_back({di, "roar"});
    }
    // Fire thaw
    if (damage > 0 && mt == TYPE_FIRE) {
        PokemonState& defender = active_mon(s, di);
        if (defender.status == STATUS_FREEZE) defender.status = STATUS_NONE;
    }
    // Defrost target moves
    if (in_set(DEFROST_TARGET_MOVES, move) && damage > 0) {
        PokemonState& defender = active_mon(s, di);
        if (defender.status == STATUS_FREEZE) defender.status = STATUS_NONE;
    }
    // Recharge
    if (in_set(RECHARGE_MOVES, move) && damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        if (!attacker.fainted) attacker.volatiles |= V_RECHARGING;
    }
    // Move recoil
    if (actual_damage > 0 && md.recoil_num >= 0) {
        PokemonState& attacker = active_mon(s, si);
        if (attacker.ability != A_ROCK_HEAD && attacker.ability != AB_MAGIC_GUARD) {
            int32_t recoil = std::max(1, (int32_t)((long long)actual_damage * md.recoil_num / md.recoil_den));
            if (!attacker.fainted) {
                int32_t nh = std::max(0, attacker.hp - recoil);
                attacker.hp = nh;
                // Mirror Python post_hit.py:831 log(DAMAGE, source="recoil"): no attacker
                // kwargs; defender_side = the recoiling mon's own side (state-neutral).
                rich_log_damage(s.turn_number, attacker.species, recoil, nh,
                                RICH_UNSET, RICH_UNSET, si, SourceTag::RECOIL);
                if (nh == 0) cpp_faint_active(s, si, /*notify_soul_heart=*/false);
            }
        }
    }
    // Struggle recoil
    if (move == M_STRUGGLE && actual_damage > 0) {
        PokemonState& attacker = active_mon(s, si);
        if (attacker.ability != AB_MAGIC_GUARD && !attacker.fainted) {
            int32_t recoil = std::max(1, attacker.max_hp / 4);
            int32_t nh = std::max(0, attacker.hp - recoil);
            attacker.hp = nh;
            // Mirror Python post_hit.py:849 log(DAMAGE, source="recoil") for Struggle.
            rich_log_damage(s.turn_number, attacker.species, recoil, nh,
                            RICH_UNSET, RICH_UNSET, si, SourceTag::RECOIL);
            if (nh == 0) cpp_faint_active(s, si, /*notify_soul_heart=*/false);
        }
    }
    // Explosion — USER spec 2026-07-15 (Task R2): self-faint whenever the move actually
    // executed (miss/Protect self-faints are handled in the guard chain; the damage=0
    // gate is removed so hitting Substitute for exactly sub_hp still self-faints).
    if (in_set(EXPLOSION_MOVE_IDS, move)) {
        if (!active_mon(s, si).fainted) cpp_faint_active(s, si, /*notify_soul_heart=*/false);
    }
    // Rapid Spin / Mortal Spin
    if ((move == M_RAPID_SPIN || move == M_MORTAL_SPIN) && damage > 0) {
        SideState& side = side_at(s, si);
        std::vector<SideConditionEntry> kept;
        for (const auto& e : side.side_conditions) if (!in_set(SPIN_HAZARDS, e.condition)) kept.push_back(e);
        side.side_conditions.assign_from(kept);
        PokemonState& attacker = active_mon(s, si);
        std::vector<TimedVolatile> ntv;
        for (const auto& tv : attacker.timed_volatiles) if (tv.effect != VE_BOUND) ntv.push_back(tv);
        attacker.timed_volatiles.assign_from(ntv);
    }
    // Throat Spray
    {
        PokemonState& attacker = active_mon(s, si);
        if (attacker.item == I_THROAT_SPRAY && (md.tags & TAG_SOUND)) {
            attacker.item = ITEM_NONE;
            change_stat_stage(s, si, 2, +1, false, false, false);
        }
    }
    // Throat Chop
    {
        PokemonState& attacker = active_mon(s, si);
        if (move == M_THROAT_CHOP && damage > 0 && attacker.ability != A_SHEER_FORCE) {
            PokemonState& defender = active_mon(s, di);
            if (!defender.fainted) defender.timed_volatiles.push_back({VE_THROAT_CHOPPED, 2});
        }
    }

    apply_secondary_effects(s, a, luck);

    // Berserk / Emergency Exit / Wimp Out
    if (actual_damage > 0 && !a.hit_sub) {
        PokemonState& defender = active_mon(s, di);
        if (!defender.fainted) {
            int32_t hp_before = defender.hp + actual_damage;
            int32_t half = defender.max_hp / 2;
            bool crossed = hp_before > half && half >= defender.hp;
            if (crossed) {
                bool berserk_sf = (is_mold_breaker(active_mon(s, si).ability) == false
                                   && active_mon(s, si).ability == A_SHEER_FORCE && md.secondary.chance != 0);
                // Python: _berserk_sheer_force uses attacker.ability == SHEER_FORCE and secondary is not None.
                bool sf = (active_mon(s, si).ability == A_SHEER_FORCE)
                          && (md.secondary.has_status || md.secondary.flinch
                              || md.secondary.num_stat_changes > 0 || md.secondary.has_volatile);
                (void)berserk_sf;
                if (defender.ability == A_BERSERK && !sf)
                    change_stat_stage(s, di, 2, +1, false, false, false);
                if (defender.ability == A_EMERGENCY_EXIT || defender.ability == A_WIMP_OUT) {
                    if (bench_exists(s, di)) pending.push_back({di, "emergency_exit"});
                }
            }
        }
    }

    // Life Orb / Shell Bell
    if (damage > 0) {
        bool magic_room = false;
        for (const auto& e : s.pseudo_weather) if (e.effect == /*MAGIC_ROOM*/ 3) magic_room = true;
        PokemonState& attacker = active_mon(s, si);
        // Mirror Python's `secondary is not None` (post_hit.py) and the Sheer Force damage
        // boost (damage.cpp): a secondary exists iff chance != 0, even if it carries no
        // status/stat/flinch/volatile payload (e.g. BUBBLE). Field-decomposition undercounts.
        bool sf_suppressed = (attacker.ability == A_SHEER_FORCE) && (md.secondary.chance != 0);
        if (attacker.item == I_LIFE_ORB && !attacker.fainted && attacker.ability != AB_MAGIC_GUARD
            && !sf_suppressed && !magic_room) {
            int32_t recoil = std::max(1, attacker.max_hp / 10);
            int32_t nh = std::max(0, attacker.hp - recoil);
            attacker.hp = nh;
            if (nh == 0) cpp_faint_active(s, si, /*notify_soul_heart=*/false);
        }
        PokemonState& atk2 = active_mon(s, si);
        if (atk2.item == I_SHELL_BELL && !atk2.fainted && actual_damage > 0 && !magic_room) {
            int32_t heal = std::max(1, actual_damage / 8);
            int32_t sb_hp_before = atk2.hp;
            atk2.hp = std::min(atk2.max_hp, atk2.hp + heal);
            // Mirror Python post_hit.py:942 log(HEAL, source="item") Shell Bell heal
            rich_log_heal(s.turn_number, atk2.species, atk2.hp - sb_hp_before, atk2.hp,
                          si, SourceTag::ITEM);
        }
    }
}
