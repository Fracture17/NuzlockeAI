// C++ port of mutating move-effect units (C1.4). See effects.h.
// Only state mutations are reproduced; Python log() calls have no state effect and are omitted.
// Unported branches throw std::runtime_error("unported: <name>") — never a silent default.
#include "effects.h"
#include "rng_resolver.h"          // rng_resolve_chance
#include "effects_internal.h"
#include "effects_consts.h"
#include "move_exec_guards.h"      // ExecCtx (Protect-family per-turn side state)
#include "type_chart_lookup.h"
#include "species_types_lookup.h"
#include "damage.h"
#include "event_log.h"            // rich_log_stat_copy

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include <move_data.h>

using namespace eff;
using namespace eff_internal;

// ---------------------------------------------------------------------------
// Generated-table lookups (binary search; throw on miss, matching Python KeyError-loud)
// ---------------------------------------------------------------------------
static const MoveData& lookup_move(int32_t move_id) {
    int lo = 0, hi = 813;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid;
    }
    if (lo >= 813 || MOVE_TABLE[lo].move_id != move_id)
        throw std::runtime_error("lookup_move: id " + std::to_string(move_id) + " not found");
    return MOVE_TABLE[lo];
}

// ---------------------------------------------------------------------------
// Shared helpers ported from src/engine/_helpers.py (exposed via effects_internal.h).
// ---------------------------------------------------------------------------
namespace eff_internal {

// ---------------------------------------------------------------------------
// Side / active accessors (mirror _get_active / _set_active using active_indices[0])
// ---------------------------------------------------------------------------
SideState& side_at(BattleState& s, int idx) { return idx == 0 ? s.side0 : s.side1; }

PokemonState& active_mon(BattleState& s, int side_idx) {
    SideState& side = side_at(s, side_idx);
    return side.team[side.active_indices[0]];
}

// ---------------------------------------------------------------------------
// Predicates ported from helpers
// ---------------------------------------------------------------------------
bool is_mold_breaker(int32_t ability) {
    for (int32_t a : MOLD_BREAKER_IDS) if (a == ability) return true;
    return false;
}

bool has_type(const PokemonState& mon, int32_t type) {
    for (int32_t t : mon.types) if (t == type) return true;
    return false;
}

bool has_pseudo(const BattleState& s, int32_t pw) {
    for (const auto& e : s.pseudo_weather) if (e.effect == pw) return true;
    return false;
}

bool has_timed_volatile(const PokemonState& mon, int32_t ve) {
    for (const auto& tv : mon.timed_volatiles) if (tv.effect == ve) return true;
    return false;
}

// _is_grounded (src/engine/damage.py) — mirrors damage.cpp:529-542 exactly.
bool is_grounded(const PokemonState& mon, const BattleState& s) {
    if (has_pseudo(s, PW_GRAVITY)) return true;
    if (mon.item == ITEM_IRON_BALL) return true;
    if (has_timed_volatile(mon, VE_GROUNDED)) return true;
    if (has_type(mon, TYPE_FLYING)) return false;
    if (mon.ability == AB_LEVITATE) return false;
    if (mon.item == ITEM_AIR_BALLOON) return false;
    if (has_timed_volatile(mon, VE_MAGNET_RISE)) return false;
    if (has_timed_volatile(mon, VE_TELEKINESIS)) return false;
    return true;
}

int32_t effective_weather(const BattleState& s) {
    for (int si = 0; si < 2; ++si) {
        const SideState& side = (si == 0) ? s.side0 : s.side1;
        for (int32_t idx : side.active_indices) {
            const PokemonState& m = side.team[idx];
            if (!m.fainted && (m.ability == AB_AIR_LOCK || m.ability == AB_CLOUD_NINE))
                return WEATHER_NONE;
        }
    }
    return s.weather;
}

// Powder moves (Grass immunity in _can_apply_status); ids from _POWDER_MOVES.
static bool is_powder_move(int32_t m) {
    static const int32_t POWDER[6] = {77, 78, 79, 147, 178, 476};
    for (int32_t p : POWDER) if (p == m) return true;
    return false;
}

// ---------------------------------------------------------------------------
// stat_stages accessors (stat_stages: 0=Atk,1=Def,2=SpA,3=SpD,4=Spe,5=Acc,6=Eva)
// ---------------------------------------------------------------------------
int32_t get_stage(const PokemonState& m, int i) {
    switch (i) { case 0: return m.stage0; case 1: return m.stage1; case 2: return m.stage2;
        case 3: return m.stage3; case 4: return m.stage4; case 5: return m.stage5;
        default: return m.stage6; }
}
void set_stage(PokemonState& m, int i, int32_t v) {
    switch (i) { case 0: m.stage0 = v; break; case 1: m.stage1 = v; break; case 2: m.stage2 = v; break;
        case 3: m.stage3 = v; break; case 4: m.stage4 = v; break; case 5: m.stage5 = v; break;
        default: m.stage6 = v; break; }
}

// Volatile bit constants (Volatile IntFlag values from src/state/pokemon.py).
static constexpr int32_t VOLATILE_UNBURDEN = 524288;
static constexpr int32_t VOLATILE_PROTECT_USED = 4194304;
static constexpr int32_t VOLATILE_ENDURE_ACTIVE = 2097152;

// _apply_unburden (src/engine/_helpers.py)
void apply_unburden(BattleState& s, int side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.ability == AB_UNBURDEN && mon.item == ITEM_NONE
        && !(mon.volatiles & VOLATILE_UNBURDEN))
        mon.volatiles |= VOLATILE_UNBURDEN;
}

// Status-curing berries (incl. Lum); used to detect _check_status_berry paths.
bool is_status_berry_relevant(int32_t item) {
    static const int32_t IDS[6] = {149, 150, 151, 152, 153, 157};
    for (int32_t i : IDS) if (i == item) return true;
    return false;
}

static const int32_t ITEM_LUM_BERRY = 157;

// _berry_suppressed: opp active with Unnerve-family ability blocks berries (fainted opp does not).
static const int32_t BERRY_SUPPRESSORS[3] = {127, 266, 267};
static bool berry_suppressed(BattleState& s, int opp_side_idx) {
    if (opp_side_idx < 0) return false;
    const PokemonState& opp = active_mon(s, opp_side_idx);
    if (opp.fainted) return false;
    for (int32_t a : BERRY_SUPPRESSORS) if (a == opp.ability) return true;
    return false;
}

// _on_berry_consumed: Cheek Pouch heal + Symbiosis pass + Unburden flag. Singles has no ally,
// so Symbiosis is a no-op.
static const int32_t AB_CHEEK_POUCH = 167;
static void on_berry_consumed(BattleState& s, int side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.ability == AB_CHEEK_POUCH) {
        int32_t extra = std::max<int32_t>(1, mon.max_hp / 3);
        int32_t hp_before = mon.hp;
        mon.hp = std::min<int32_t>(mon.max_hp, mon.hp + extra);
        // HEAL source=cheek_pouch: consumer counts per-side occurrences (Python
        // _helpers.py:679). Emit unconditionally to mirror Python (fires even at full HP).
        rich_log_heal(s.turn_number, mon.species, mon.hp - hp_before, mon.hp, side_idx,
                      SourceTag::CHEEK_POUCH);
    }
    apply_unburden(s, side_idx);
}

// _STATUS_BERRY_CURES: berry item -> set of statuses it cures (Lum cures all, handled separately).
static bool status_berry_cures(int32_t item, int32_t status) {
    switch (item) {
        case 152: return status == STATUS_BURN;                              // Rawst
        case 151: return status == STATUS_POISON || status == STATUS_TOXIC;  // Pecha
        case 150: return status == STATUS_SLEEP;                             // Chesto
        case 153: return status == STATUS_FREEZE;                           // Aspear
        case 149: return status == STATUS_PARALYSIS;                        // Cheri
        default:  return false;
    }
}

// _check_status_berry: consume a status-curing berry if applicable. Returns true if consumed.
bool check_status_berry(BattleState& s, int side_idx, int opp_side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (berry_suppressed(s, opp_side_idx)) return false;

    if (mon.item == ITEM_LUM_BERRY) {
        bool is_confused = (mon.volatiles & VOLATILE_CONFUSED) != 0;
        bool has_status = mon.status != STATUS_NONE;
        if (!is_confused && !has_status) return false;
        mon.status = STATUS_NONE;
        if (is_confused) mon.volatiles &= ~VOLATILE_CONFUSED;
        mon.item = ITEM_NONE;
        mon.consumed_berry = ITEM_LUM_BERRY;
        on_berry_consumed(s, side_idx);
        return true;
    }
    if (mon.status == STATUS_NONE || !is_status_berry_relevant(mon.item)) return false;
    if (status_berry_cures(mon.item, mon.status)) {
        mon.consumed_berry = mon.item;
        mon.status = STATUS_NONE;
        mon.item = ITEM_NONE;
        on_berry_consumed(s, side_idx);
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// _check_white_herb (src/engine/_helpers.py)
// ---------------------------------------------------------------------------
static void check_white_herb(BattleState& s, int side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.item != ITEM_WHITE_HERB) return;
    bool any_neg = false;
    for (int i = 0; i < 7; ++i) if (get_stage(mon, i) < 0) { any_neg = true; break; }
    if (!any_neg) return;
    // Per-stat STAT_BOOST for each restored negative stage (Python _helpers.py:515):
    // stages = -old_stage (positive restore). Emit before zeroing to read old_stage.
    for (int i = 0; i < 7; ++i) {
        int32_t old_stage = get_stage(mon, i);
        if (old_stage < 0)
            rich_log_stat_boost(s.turn_number, mon.species, i, -old_stage, side_idx, SourceTag::ITEM);
    }
    for (int i = 0; i < 7; ++i) if (get_stage(mon, i) < 0) set_stage(mon, i, 0);
    mon.item = ITEM_NONE;
    apply_unburden(s, side_idx);
}

// ---------------------------------------------------------------------------
// _change_stat_stage (src/engine/_helpers.py) — returns actual applied delta.
// Ports: Contrary, opponent-caused protective abilities, Simple, clamp, per-turn flags,
//        White Herb, Eject Pack. Logging omitted.
// ctx: when non-null, Eject Pack triggers append to ctx->eject_pack_sides (consumed after
//      execute_action in cpp_run_one_turn, mirroring Python's _advance_queue drain).
// ---------------------------------------------------------------------------
int32_t change_stat_stage(BattleState& s, int side_idx, int stat_idx, int delta,
                          bool caused_by_opponent, bool ignore_simple, bool mold_breaker,
                          ExecCtx* ctx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.ability == AB_CONTRARY && !mold_breaker) delta = -delta;
    if (caused_by_opponent && delta < 0) {
        if (mon.ability == AB_HYPER_CUTTER && stat_idx == 0 && !mold_breaker) return 0;
        if ((mon.ability == AB_CLEAR_BODY || mon.ability == AB_WHITE_SMOKE) && !mold_breaker) return 0;
        if (mon.ability == AB_FULL_METAL_BODY) return 0;
        if (mon.ability == AB_KEEN_EYE && stat_idx == 5 && !mold_breaker) return 0;
        if (mon.ability == AB_FLOWER_VEIL && has_type(mon, TYPE_GRASS)) return 0;
    }
    if (mon.ability == AB_SIMPLE && !ignore_simple) delta *= 2;
    int32_t old_stage = get_stage(mon, stat_idx);
    int32_t new_stage = std::max(-6, std::min(6, old_stage + delta));
    int32_t actual = new_stage - old_stage;
    set_stage(mon, stat_idx, new_stage);
    // STAT_BOOST fires only on a real change (Python _helpers.py:581). Consumer reads
    // side/target/direction only; source is unread, so the broad MOVE tag suffices.
    if (actual != 0)
        rich_log_stat_boost(s.turn_number, mon.species, stat_idx, actual, side_idx, SourceTag::MOVE);
    if (actual < 0) mon.had_stat_lowered_this_turn = true;
    else if (actual > 0) mon.had_stat_raised_this_turn = true;
    if (actual < 0) check_white_herb(s, side_idx);
    if (actual < 0 && caused_by_opponent) {
        PokemonState& holder = active_mon(s, side_idx);
        if (holder.item == ITEM_EJECT_PACK) {
            SideState& side = side_at(s, side_idx);
            bool bench = false;
            for (size_t i = 0; i < side.team.size(); ++i) {
                bool is_active = false;
                for (int32_t ai : side.active_indices) if ((int)i == ai) { is_active = true; break; }
                if (!is_active && !side.team[i].fainted) { bench = true; break; }
            }
            if (bench) {
                // Consume item immediately in both cases (mirrors Python: _replace(item=NONE)).
                holder.item = ITEM_NONE;
                if (ctx) {
                    // With ctx: queue the switch (mirrors Python ctx.eject_pack_sides.append).
                    // Dedup: only append if not already recorded for this side this action.
                    bool already = false;
                    for (int32_t ep : ctx->eject_pack_sides) if (ep == side_idx) { already = true; break; }
                    if (!already) ctx->eject_pack_sides.push_back(static_cast<int32_t>(side_idx));
                }
                // Without ctx (e.g. turn-1 entry effects called without ctx, or residuals):
                // mirrors Python _change_stat_stage(ctx=None): item consumed, no switch queued.
            }
        }
    }
    return actual;
}

// _on_stat_dropped: Defiant/Competitive. With a dedup array, fires at most once per side per turn.
void on_stat_dropped(BattleState& s, int side_idx, int /*stat_idx*/,
                     bool* competitive_defiant_triggered) {
    if (competitive_defiant_triggered && competitive_defiant_triggered[side_idx]) return;
    PokemonState& mon = active_mon(s, side_idx);
    if (mon.ability == AB_DEFIANT) {
        change_stat_stage(s, side_idx, 0, +2, false, false, false);
        if (competitive_defiant_triggered) competitive_defiant_triggered[side_idx] = true;
    } else if (mon.ability == AB_COMPETITIVE) {
        change_stat_stage(s, side_idx, 2, +2, false, false, false);
        if (competitive_defiant_triggered) competitive_defiant_triggered[side_idx] = true;
    }
}

// ---------------------------------------------------------------------------
// _can_apply_status (src/engine/_helpers.py)
// ---------------------------------------------------------------------------
bool can_apply_status(const PokemonState& target, int32_t status, int32_t move,
                             int32_t attacker_ability, const BattleState& s) {
    if (target.status != STATUS_NONE) return false;
    if (target.species == SPECIES_MINIOR_METEOR) return false;
    if (s.terrain == TERRAIN_MISTY && is_grounded(target, s)) return false;
    if (target.ability == AB_COMATOSE) return false;
    bool mb = is_mold_breaker(attacker_ability);
    if (target.ability == AB_LEAF_GUARD && !mb) {
        int32_t w = effective_weather(s);
        if (w == WEATHER_SUNNY || w == WEATHER_HARSH_SUN) return false;
    }
    if (status == STATUS_POISON || status == STATUS_TOXIC) {
        if (attacker_ability != AB_CORROSION) {
            if (target.ability == AB_IMMUNITY && !mb) return false;
            if (has_type(target, TYPE_POISON) || has_type(target, TYPE_STEEL)) return false;
        }
    }
    if (status == STATUS_BURN) {
        if ((target.ability == AB_WATER_VEIL || target.ability == AB_WATER_BUBBLE) && !mb) return false;
        if (has_type(target, TYPE_FIRE)) return false;
    }
    if (status == STATUS_FREEZE) {
        if (target.ability == AB_MAGMA_ARMOR && !mb) return false;
        if (has_type(target, TYPE_ICE)) return false;
        int32_t w = effective_weather(s);
        if (w == WEATHER_SUNNY || w == WEATHER_HARSH_SUN) return false;
    }
    if (status == STATUS_SLEEP) {
        if ((target.ability == AB_INSOMNIA || target.ability == AB_VITAL_SPIRIT) && !mb) return false;
        if (s.terrain == TERRAIN_ELECTRIC && is_grounded(target, s)) return false;
    }
    if (status == STATUS_PARALYSIS) {
        if (target.ability == AB_LIMBER && !mb) return false;
        if (has_type(target, TYPE_ELECTRIC)) return false;
    }
    if (is_powder_move(move) && has_type(target, TYPE_GRASS)) return false;
    if (status == STATUS_SLEEP && target.ability == AB_SWEET_VEIL && !mb) return false;
    if ((status == STATUS_POISON || status == STATUS_TOXIC)
        && target.ability == AB_PASTEL_VEIL && !mb) return false;
    if (target.ability == AB_FLOWER_VEIL && !mb && has_type(target, TYPE_GRASS)) return false;
    return true;
}

// _apply_status_to: set status (Toxic seeds toxic_turns=1).
void apply_status_to(BattleState& s, int side_idx, int32_t status) {
    PokemonState& mon = active_mon(s, side_idx);
    int32_t toxic_turns = (status == STATUS_TOXIC) ? 1 : mon.toxic_turns;
    mon.status = status;
    mon.toxic_turns = toxic_turns;
    // Python _helpers.py:499 always tags STATUS_APPLY source="move"; consumer reads
    // side/target/status only.
    rich_log_status_apply(s.turn_number, mon.species, status, side_idx, SourceTag::MOVE);
}

// BERRY_ITEMS membership (src/data/items.py). Sorted; binary search.
bool is_berry(int32_t item) {
    static const int32_t BERRIES[53] = {149,150,151,152,153,154,155,156,157,158,159,160,161,162,
        163,169,170,171,172,173,174,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,
        199,200,201,202,203,204,205,206,207,208,209,210,211,212,686,687,688};
    int lo = 0, hi = 53;
    while (lo < hi) { int mid = (lo + hi) / 2; if (BERRIES[mid] < item) lo = mid + 1; else hi = mid; }
    return lo < 53 && BERRIES[lo] == item;
}

// ---------------------------------------------------------------------------
// _check_confusion_berry (Persim Berry).
// ---------------------------------------------------------------------------
static const int32_t ITEM_PERSIM_BERRY = 156;
void check_confusion_berry(BattleState& s, int side_idx, int opp_side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    if (berry_suppressed(s, opp_side_idx)) return;
    if (!(mon.volatiles & VOLATILE_CONFUSED)) return;
    if (mon.item != ITEM_PERSIM_BERRY) return;
    mon.volatiles &= ~VOLATILE_CONFUSED;
    mon.item = ITEM_NONE;
    mon.consumed_berry = ITEM_PERSIM_BERRY;
    on_berry_consumed(s, side_idx);
}

// ---------------------------------------------------------------------------
// _check_berry (HP-threshold berry). Mirrors src/engine/_helpers.py _check_berry.
// kind: 0=HP, 1=STAT, 2=CRIT, 3=RANDOM_STAT.
// HP amount encoded as (flat_hp, frac_denom); STAT uses (stat_idx, delta).
// ---------------------------------------------------------------------------
static const int32_t AB_GLUTTONY = 82, AB_RIPEN = 247;
static const int32_t ITEM_BERRY_JUICE = 34;

struct BerryEffect {
    int32_t threshold_denom;
    int32_t kind;
    int32_t a0, a1;      // HP: (flat_hp, frac_denom); STAT/RANDOM: a0=delta; STAT: a1=stat_idx
    int32_t confused_stat;  // flavour berry: Stat enum (ATK=1..SPE=5) that confuses if nature-lowered; -1 none
};

// item -> BerryEffect. Returns false if not an HP-threshold berry.
static bool hp_threshold_berry(int32_t item, BerryEffect& out) {
    switch (item) {
        case 158: out = {2, 0, 0, 4, -1};  return true;  // Sitrus: restore 25%
        case 155: out = {2, 0, 10, 0, -1}; return true;  // Oran: restore 10 flat
        case 34:  out = {2, 0, 20, 0, -1}; return true;  // Berry Juice: restore 20 flat
        case 203: out = {4, 1, 1, 4, -1};  return true;  // Salac: Spe +1 (stat_idx 4)
        case 201: out = {4, 1, 1, 0, -1};  return true;  // Liechi: Atk +1
        case 204: out = {4, 1, 1, 2, -1};  return true;  // Petaya: SpA +1
        case 205: out = {4, 1, 1, 3, -1};  return true;  // Apicot: SpD +1
        case 202: out = {4, 1, 1, 1, -1};  return true;  // Ganlon: Def +1
        case 207: out = {4, 3, 2, 0, -1};  return true;  // Starf: random stat +2
        case 206: out = {4, 2, 1, 0, -1};  return true;  // Lansat: crit +1
        case 159: out = {4, 0, 0, 2, 1};   return true;  // Figy: restore 50%, confuse if -Atk
        case 160: out = {4, 0, 0, 2, 3};   return true;  // Wiki: -SpA
        case 161: out = {4, 0, 0, 2, 5};   return true;  // Mago: -Spe
        case 162: out = {4, 0, 0, 2, 4};   return true;  // Aguav: -SpD
        case 163: out = {4, 0, 0, 2, 2};   return true;  // Iapapa: -Def
        default:  return false;
    }
}

// NATURE_DATA[nature].lowered as Stat enum (HP=0 unused; ATK=1,DEF=2,SPA=3,SPD=4,SPE=5); -1 = neutral.
static int32_t nature_lowered_stat(int32_t nature) {
    static const int32_t L[25] = {-1,2,5,3,4,1,-1,5,3,4,1,2,-1,3,4,1,2,5,-1,4,1,2,5,3,-1};
    if (nature < 0 || nature >= 25) return -1;
    return L[nature];
}

bool check_berry(BattleState& s, int side_idx, int opp_side_idx, NativeRng* rng,
                 const OracleOverrides* overrides) {
    PokemonState& mon = active_mon(s, side_idx);
    if (berry_suppressed(s, opp_side_idx)) return false;
    BerryEffect eff;
    if (mon.fainted || !hp_threshold_berry(mon.item, eff)) return false;

    int32_t threshold_denom = eff.threshold_denom;
    if (threshold_denom == 4 && mon.ability == AB_GLUTTONY) threshold_denom = 2;
    int32_t threshold_hp = mon.max_hp / threshold_denom;
    if (mon.hp > threshold_hp) return false;

    int32_t berry = mon.item;
    bool ripen = mon.ability == AB_RIPEN;

    if (eff.kind == 0) {  // HP
        int32_t flat_hp = eff.a0, frac_denom = eff.a1;
        int32_t heal;
        if (frac_denom == 0) {
            heal = flat_hp;
            if (ripen && berry != ITEM_BERRY_JUICE) heal *= 2;
        } else {
            if (ripen && berry != ITEM_BERRY_JUICE) heal = (int32_t)((long long)mon.max_hp * 2 / frac_denom);
            else heal = mon.max_hp / frac_denom;
        }
        int32_t hp_before = mon.hp;
        mon.hp = std::min(mon.max_hp, mon.hp + heal);
        mon.item = ITEM_NONE;
        mon.consumed_berry = berry;
        // HEAL source=berry: the reconciler matches these one-for-one per side against
        // observed restore messages (Python _helpers.py:726).
        rich_log_heal(s.turn_number, mon.species, mon.hp - hp_before, mon.hp, side_idx,
                      SourceTag::BERRY);
        if (eff.confused_stat != -1) {
            PokemonState& m2 = active_mon(s, side_idx);
            if (nature_lowered_stat(m2.nature) == eff.confused_stat)
                m2.volatiles |= VOLATILE_CONFUSED;
        }
    } else if (eff.kind == 2) {  // CRIT (Lansat)
        mon.crit_stage += 1;
        mon.item = ITEM_NONE;
        mon.consumed_berry = berry;
    } else if (eff.kind == 3) {  // RANDOM_STAT (Starf): +2 to a random stat (0-4). random_mode
        // draws natively via rng->randint(0,4) mirroring Python's else-branch (_helpers.py:739);
        // forced mode consumes the trace answer; controlled mode uses oracle_resolve.
        int chosen_stat;
        if (rng) {
            if (rng->forced) {
                const ForcedAnswer& a = rng->forced->next_answer(rng->current_turn, RngEventC::STARF_BERRY_STAT, -1);
                chosen_stat = a.i0;
            } else {
                chosen_stat = rng->randint(0, 4);
            }
        } else {
            const SideState& mside = side_at(s, side_idx);
            const SideState& oside = side_at(s, opp_side_idx);
            RngParticipants who{
                (int8_t)side_idx, (int8_t)mside.active_indices[0],
                (int8_t)opp_side_idx, (int8_t)oside.active_indices[0]};
            chosen_stat = oracle_resolve(overrides, RngEventC::STARF_BERRY_STAT,
                                         {0,1,2,3,4}, who, s.turn_number);
        }
        mon.item = ITEM_NONE;
        mon.consumed_berry = berry;
        int32_t boost = ripen ? eff.a0 * 2 : eff.a0;
        change_stat_stage(s, side_idx, chosen_stat, boost, false, false, false);
    } else {  // STAT
        mon.item = ITEM_NONE;
        mon.consumed_berry = berry;
        int32_t boost = ripen ? eff.a0 * 2 : eff.a0;  // STAT: a0=delta, a1=stat_idx
        change_stat_stage(s, side_idx, eff.a1, boost, false, false, false);
    }
    on_berry_consumed(s, side_idx);
    return true;
}

// _notify_faint_soul_heart: +1 SpA per active non-fainted Soul-Heart holder (both sides).
static const int32_t AB_SOUL_HEART = 220;
void notify_faint_soul_heart(BattleState& s) {
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (size_t slot_pos = 0; slot_pos < side.active_indices.size(); ++slot_pos) {
            int32_t slot = side.active_indices[slot_pos];
            PokemonState& mon = side.team[slot];
            if (!mon.fainted && mon.ability == AB_SOUL_HEART) {
                int32_t saved = side.active_indices[0];
                side.active_indices[0] = slot;
                change_stat_stage(s, si, 2, +1, false, false, false);
                side.active_indices[0] = saved;
            }
        }
    }
}

// Volatile constant used by try_apply_flinch (AB_INNER_FOCUS/AB_STEADFAST live in effects_consts.h).
static constexpr int32_t VOLATILE_FLINCHED = 64;

// _try_apply_flinch: set FLINCHED unless Inner Focus (bypassed by Mold Breaker); Steadfast +1 Spe.
void try_apply_flinch(BattleState& s, int defender_idx, bool mold_breaker) {
    PokemonState& defender = active_mon(s, defender_idx);
    if (defender.ability != AB_INNER_FOCUS || mold_breaker) {
        defender.volatiles |= VOLATILE_FLINCHED;
        if (defender.ability == AB_STEADFAST)
            change_stat_stage(s, defender_idx, 4, +1, false, false, false);
    }
}

// Resolvers: chance>=100 -> true (no RNG), chance<=0 -> false (no RNG).
// Each forwards to rng_resolve_chance with the appropriate threshold field and event id.
// D3-follow-up: threads participant/turn context (ctx) into the underlying resolver
// so the analytical logger and Category-B injection channel see attacker/defender
// attribution for every secondary/proc/flinch draw.
bool resolve_secondary_det(int chance, const EffectsLuck& luck, const RngLogCtx* ctx) {
    // rng.py:368 SECONDARY_FIRES
    return rng_resolve_chance(chance, luck.secondary_threshold, luck.random_mode, luck.rng,
                              RngEventC::SECONDARY_FIRES, ctx);
}
bool resolve_proc_det(int chance, const EffectsLuck& luck, const RngLogCtx* ctx) {
    // rng.py:378 PROC_FIRES
    return rng_resolve_chance(chance, luck.proc_threshold, luck.random_mode, luck.rng,
                              RngEventC::PROC_FIRES, ctx);
}
bool resolve_flinch_det(int chance, const EffectsLuck& luck, const RngLogCtx* ctx) {
    // rng.py:538 FLINCH
    return rng_resolve_chance(chance, luck.flinch_threshold, luck.random_mode, luck.rng,
                              RngEventC::FLINCH, ctx);
}

} // namespace eff_internal

// Entry-effect entry points (cpp_apply_entry_hazards / cpp_apply_entry_effects) and
// their file-local Intimidate/Trace/Imposter/Download/seed/Forecast/RKS/Screen Cleaner
// helpers live in effects_entry.cpp. Four of those helpers (is_silvally,
// is_castform_form, memory_type, update_castform) are also called by the turn-start
// and EOT paths below; they are declared in effects_internal.h and defined there
// under namespace eff_internal.

// ===========================================================================
// _sec_self_stat_changes
// ===========================================================================
void cpp_sec_self_stat_changes(BattleState& s, int side_idx, int32_t move_id, int damage) {
    const MoveData& md = lookup_move(move_id);
    if (damage > 0 && md.num_self_stat_changes > 0) {
        for (int i = 0; i < md.num_self_stat_changes; ++i)
            change_stat_stage(s, side_idx, md.self_stat_changes[i].stat_idx,
                              md.self_stat_changes[i].delta, false, false, false);
    }
}

// ===========================================================================
// release_inflicted_traps: strip BOUND/TRAPPED (+ SOURCE companions) from every
// active opponent victim whose trap was inflicted by the departed mon. Mirrors
// src/engine/trap_release.py::release_inflicted_traps. Idempotent.
// ===========================================================================
void cpp_release_inflicted_traps(BattleState& s, int departed_side_idx, int32_t departed_team_idx) {
    SideState& victim_side = side_at(s, 1 - departed_side_idx);
    for (int32_t active_team_idx : victim_side.active_indices) {
        PokemonState& victim = victim_side.team[active_team_idx];
        if (victim.fainted) continue;

        bool bound_match = false, trapped_match = false;
        for (const auto& tv : victim.timed_volatiles) {
            if (tv.effect == VE_BOUND_SOURCE_ID && tv.turns == departed_team_idx) bound_match = true;
            if (tv.effect == VE_TRAPPED_SOURCE_ID && tv.turns == departed_team_idx) trapped_match = true;
        }
        if (!bound_match && !trapped_match) continue;

        std::vector<TimedVolatile> kept;
        for (const auto& tv : victim.timed_volatiles) {
            if (bound_match && (tv.effect == VE_BOUND || tv.effect == VE_BOUND_SOURCE_ID
                                || tv.effect == VE_BOUND_SOURCE_SLOT))
                continue;
            if (trapped_match && (tv.effect == VE_TRAPPED || tv.effect == VE_TRAPPED_SOURCE_ID))
                continue;
            kept.push_back(tv);
        }
        victim.timed_volatiles.assign_from(kept);
    }
}

// faint_active: canonical faint transition. Mirrors Python's faint_active exactly.
// Order: idempotent check -> hp=0/fainted -> release traps -> optional soul-heart notify.
void cpp_faint_active(BattleState& s, int side_idx, bool notify_soul_heart, int slot) {
    SideState& side = side_at(s, side_idx);
    int32_t team_idx = side.active_indices[slot];
    PokemonState& mon = side.team[team_idx];
    if (mon.fainted) return;
    mon.hp = 0;
    mon.fainted = true;
    // Single-fire FAINT chokepoint (the idempotent guard above ensures one emit per KO).
    // Consumer reads side+species for identity/ordering; cause is unread.
    rich_log_faint(s.turn_number, mon.species, side_idx);
    cpp_release_inflicted_traps(s, side_idx, team_idx);
    if (notify_soul_heart) notify_faint_soul_heart(s);
}

// ===========================================================================
// _apply_switch_out_reset
// ===========================================================================
void cpp_apply_switch_out_reset(BattleState& s, int side_idx, int old_idx) {
    SideState& side = side_at(s, side_idx);
    PokemonState& mon = side.team[old_idx];

    if (!mon.fainted) {
        if (mon.ability == AB_NATURAL_CURE && mon.status != STATUS_NONE)
            mon.status = STATUS_NONE;
        if (mon.ability == AB_REGENERATOR) {
            int32_t heal = mon.max_hp / 3;
            mon.hp = std::min(mon.max_hp, mon.hp + heal);
        }
    }
    if (!side.imprisoned_moves.empty()) side.imprisoned_moves.clear();

    // reset_types from species (isolated TU to avoid enum class Type clash)
    mon.types.assign_from(cpp_species_types(mon.species));
    mon.has_types = true;

    mon.turns_in_battle = 0;
    mon.toxic_turns = 0;
    mon.volatiles = 0;
    mon.timed_volatiles.clear();
    mon.sub_hp = 0;
    mon.locked_slot = -1;
    mon.stage0 = mon.stage1 = mon.stage2 = mon.stage3 = mon.stage4 = mon.stage5 = mon.stage6 = 0;
    mon.confusion_turns = 0;
    mon.charging_move_slot = -1;
    mon.crit_stage = 0;
    mon.metronome_count = 0;
    mon.metronome_last_move = -1;
    mon.mirror_move_last_move = -1;
    mon.rollout_hits = 0;
    mon.defense_curl_used = false;
    mon.weight_kg_reduced = 0.0;
    mon.protect_counter = 0;
    mon.took_damage_this_turn = false;
    mon.had_stat_lowered_this_turn = false;
    mon.had_stat_raised_this_turn = false;
    mon.last_move_failed = false;
    mon.sucker_punch_last_turn = false;
    mon.last_physical_damage_taken = 0;
    mon.last_special_damage_taken = 0;
    mon.last_damage_taken = 0;
    mon.stockpile_count = 0;
    mon.stockpile_def_boost = 0;
    mon.stockpile_spd_boost = 0;

    // Release any traps the departing mon was inflicting on the opponent.
    cpp_release_inflicted_traps(s, side_idx, old_idx);
}

// ===========================================================================
// _apply_status_move dispatch
// ===========================================================================

// --- _apply_protect_move (Protect family only; Endure/Mat Block stubbed) ---
static const int32_t PROTECT_MOVES_IDS[9] = {182, 197, 455, 469, 501, 588, 596, 661, 792};
static bool is_protect_move(int32_t m) {
    for (int32_t p : PROTECT_MOVES_IDS) if (p == m) return true;
    return false;
}
// Wide Guard / Quick Guard share the chain but record their own ctx side sets (no state mutation).
static constexpr int32_t MOVE_ENDURE = 203, MOVE_MAT_BLOCK = 561;
static constexpr int32_t MOVE_WIDE_GUARD = 469, MOVE_QUICK_GUARD = 501;

static bool apply_protect_move(BattleState& s, int side_idx, int32_t move,
                               const EffectsLuck& luck, ExecCtx& ctx) {
    // Endure: same consecutive-use chain as Protect; sets ENDURE_ACTIVE | PROTECT_USED. No ctx
    // protection set (Endure does not block moves; it only guarantees survival at 1 HP).
    if (move == MOVE_ENDURE) {
        PokemonState& attacker = active_mon(s, side_idx);
        if (attacker.protect_counter > 0) {
            // Python uses round() (banker's); lround() (half-away) differs only on *.5, which
            // 100/counter never yields here (counter in {3,9,27,81} -> 33,11,4,1). Equivalent.
            int chance = (int)std::lround(100.0 / attacker.protect_counter);
            // Self-only proc (no defender attribution).
            const RngLogCtx ctx_endure{
                RngParticipants{(int8_t)side_idx,
                                (int8_t)side_at(s, side_idx).active_indices[0], -1, -1},
                s.turn_number};
            if (!resolve_proc_det(chance, luck, &ctx_endure)) { attacker.protect_counter = 0; return true; }
        }
        attacker.protect_counter = attacker.protect_counter > 0 ? attacker.protect_counter * 3 : 3;
        attacker.volatiles |= VOLATILE_ENDURE_ACTIVE | VOLATILE_PROTECT_USED;
        return true;
    }
    // Mat Block: only usable on the user's first turn out. Success records ctx protection (blocks
    // incoming damaging moves for the turn); when not first turn it fails (no ctx, no state diff).
    if (move == MOVE_MAT_BLOCK) {
        const PokemonState& attacker = active_mon(s, side_idx);
        if (attacker.turns_in_battle == 0) {
            ctx.protected_sides[side_idx] = true;
            ctx.protect_move[side_idx] = move;
        }
        return true;
    }
    if (!is_protect_move(move)) return false;
    PokemonState& attacker = active_mon(s, side_idx);
    if (attacker.protect_counter > 0) {
        // See Endure note above: lround vs Python round() only differ on *.5, unreachable here.
        int chance = (int)std::lround(100.0 / attacker.protect_counter);
        // Self-only proc (protect consecutive-use chain).
        const RngLogCtx ctx_protect{
            RngParticipants{(int8_t)side_idx,
                            (int8_t)side_at(s, side_idx).active_indices[0], -1, -1},
            s.turn_number};
        if (!resolve_proc_det(chance, luck, &ctx_protect)) {
            attacker.protect_counter = 0;
            return true;  // consecutive-use failure: no protection recorded
        }
    }
    int32_t new_counter = attacker.protect_counter > 0 ? attacker.protect_counter * 3 : 3;
    attacker.protect_counter = new_counter;
    attacker.volatiles |= VOLATILE_PROTECT_USED;
    // Record the per-turn ctx side state so a later mover's guard chain sees this protection.
    if (move == MOVE_WIDE_GUARD) {
        ctx.wide_guard_sides[side_idx] = true;
    } else if (move == MOVE_QUICK_GUARD) {
        ctx.quick_guard_sides[side_idx] = true;
    } else {
        ctx.protected_sides[side_idx] = true;
        ctx.protect_move[side_idx] = move;
    }
    return true;
}

// --- _apply_hazard_move ---
static void remove_sc(SideState& side, int32_t cond) {
    std::vector<SideConditionEntry> kept;
    for (const auto& e : side.side_conditions) if (e.condition != cond) kept.push_back(e);
    side.side_conditions.assign_from(kept);
}
static bool side_has(const SideState& side, int32_t cond) {
    for (const auto& e : side.side_conditions) if (e.condition == cond) return true;
    return false;
}

static bool apply_hazard_move(BattleState& s, int side_idx, int32_t move) {
    int opp_idx = 1 - side_idx;
    SideState& opp = side_at(s, opp_idx);

    if (move == MOVE_STEALTH_ROCK) {
        if (!side_has(opp, SC_STEALTH_ROCK)) opp.side_conditions.push_back({SC_STEALTH_ROCK, -1});
        return true;
    }
    if (move == MOVE_SPIKES) {
        bool h1 = side_has(opp, SC_SPIKES_1), h2 = side_has(opp, SC_SPIKES_2), h3 = side_has(opp, SC_SPIKES_3);
        if (!h1 && !h2 && !h3) opp.side_conditions.push_back({SC_SPIKES_1, -1});
        else if (h1) { remove_sc(opp, SC_SPIKES_1); opp.side_conditions.push_back({SC_SPIKES_2, -1}); }
        else if (h2) { remove_sc(opp, SC_SPIKES_2); opp.side_conditions.push_back({SC_SPIKES_3, -1}); }
        return true;
    }
    if (move == MOVE_TOXIC_SPIKES) {
        bool h1 = side_has(opp, SC_TOXIC_SPIKES_1), h2 = side_has(opp, SC_TOXIC_SPIKES_2);
        if (!h1 && !h2) opp.side_conditions.push_back({SC_TOXIC_SPIKES_1, -1});
        else if (h1 && !h2) { remove_sc(opp, SC_TOXIC_SPIKES_1); opp.side_conditions.push_back({SC_TOXIC_SPIKES_2, -1}); }
        return true;
    }
    if (move == MOVE_STICKY_WEB) {
        if (!side_has(opp, SC_STICKY_WEB)) opp.side_conditions.push_back({SC_STICKY_WEB, -1});
        return true;
    }
    if (move == MOVE_DEFOG) {
        static const int32_t CLEARS[10] = {SC_STEALTH_ROCK, SC_SPIKES_1, SC_SPIKES_2, SC_SPIKES_3,
            SC_TOXIC_SPIKES_1, SC_TOXIC_SPIKES_2, SC_STICKY_WEB, SC_REFLECT, SC_LIGHT_SCREEN, SC_AURORA_VEIL};
        auto in_clears = [&](int32_t c) {
            for (int32_t x : CLEARS) if (x == c) return true; return false; };
        for (int t : {opp_idx, side_idx}) {
            SideState& tside = side_at(s, t);
            std::vector<SideConditionEntry> kept;
            for (const auto& e : tside.side_conditions) if (!in_clears(e.condition)) kept.push_back(e);
            tside.side_conditions.assign_from(kept);
        }
        return true;
    }
    return false;
}

// _apply_terrain_seeds (residuals.py): consume matching Terrain Seed for grounded actives, +1 stat.
static const int32_t ITEM_ELECTRIC_SEED = 881, ITEM_GRASSY_SEED = 884,
                     ITEM_PSYCHIC_SEED = 882, ITEM_MISTY_SEED = 883;
static void apply_terrain_seeds(BattleState& s) {
    int32_t seed_item = ITEM_NONE, stat_idx = -1;
    switch (s.terrain) {
        case TERRAIN_ELECTRIC: seed_item = ITEM_ELECTRIC_SEED; stat_idx = 1; break;
        case TERRAIN_GRASSY:   seed_item = ITEM_GRASSY_SEED;   stat_idx = 1; break;
        case TERRAIN_PSYCHIC:  seed_item = ITEM_PSYCHIC_SEED;  stat_idx = 3; break;
        case TERRAIN_MISTY:    seed_item = ITEM_MISTY_SEED;    stat_idx = 3; break;
        default: return;
    }
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (int32_t ai : side.active_indices) {
            PokemonState& mon = side.team[ai];
            if (mon.fainted || mon.item != seed_item) continue;
            if (!is_grounded(mon, s)) continue;
            mon.item = ITEM_NONE;
            change_stat_stage(s, si, stat_idx, +1, false, false, false);
        }
    }
}

// --- _apply_field_move ---
static bool apply_field_move(BattleState& s, int side_idx, int32_t move) {
    SideState& side = side_at(s, side_idx);
    PokemonState& attacker = active_mon(s, side_idx);

    if (move == MOVE_REFLECT || move == MOVE_LIGHT_SCREEN || move == MOVE_AURORA_VEIL) {
        if (move == MOVE_AURORA_VEIL && s.weather != WEATHER_HAIL) return true;
        int8_t duration = (attacker.item == ITEM_LIGHT_CLAY) ? 8 : 5;
        int32_t cond = (move == MOVE_REFLECT) ? SC_REFLECT
                     : (move == MOVE_LIGHT_SCREEN) ? SC_LIGHT_SCREEN : SC_AURORA_VEIL;
        if (!side_has(side, cond)) side.side_conditions.push_back({cond, duration});
        return true;
    }
    if (move == MOVE_TAILWIND) {
        if (!side_has(side, SC_TAILWIND)) side.side_conditions.push_back({SC_TAILWIND, 4});
        return true;
    }
    if (move == MOVE_LUCKY_CHANT) {
        if (!side_has(side, SC_LUCKY_CHANT)) side.side_conditions.push_back({SC_LUCKY_CHANT, 5});
        return true;
    }
    if (move == MOVE_SAFEGUARD) {
        if (!side_has(side, SC_SAFEGUARD)) side.side_conditions.push_back({SC_SAFEGUARD, 5});
        return true;
    }
    // Weather moves
    {
        int32_t w = WEATHER_NONE, rock = ITEM_NONE;
        if (move == 240) { w = WEATHER_RAINY; rock = ITEM_DAMP_ROCK; }
        else if (move == 241) { w = WEATHER_SUNNY; rock = ITEM_HEAT_ROCK; }
        else if (move == 201) { w = WEATHER_SANDSTORM; rock = ITEM_SMOOTH_ROCK; }
        else if (move == 258) { w = WEATHER_HAIL; rock = ITEM_ICY_ROCK; }
        if (w != WEATHER_NONE) {
            int32_t duration = (attacker.item == rock) ? 8 : 5;
            s.weather = w;
            s.weather_turns = static_cast<int8_t>(duration);
            return true;
        }
    }
    // Terrain moves (Electric/Grassy/Psychic/Misty) + Terrain Seed item consumption.
    {
        int32_t terrain = TERRAIN_NONE;
        if (move == 604) terrain = TERRAIN_ELECTRIC;
        else if (move == 580) terrain = TERRAIN_GRASSY;
        else if (move == 678) terrain = TERRAIN_PSYCHIC;
        else if (move == 581) terrain = TERRAIN_MISTY;
        if (terrain != TERRAIN_NONE) {
            int32_t duration = (attacker.item == ITEM_TERRAIN_EXTENDER) ? 8 : 5;
            s.terrain = terrain;
            s.terrain_turns = static_cast<int8_t>(duration);
            apply_terrain_seeds(s);
            return true;
        }
    }
    if (move == MOVE_GRAVITY) {
        if (!has_pseudo(s, PW_GRAVITY)) s.pseudo_weather.push_back({PW_GRAVITY, 5});
        return true;
    }
    if (move == MOVE_TRICK_ROOM) {
        if (has_pseudo(s, PW_TRICK_ROOM)) {
            std::vector<PseudoWeatherEntry> kept;
            for (const auto& e : s.pseudo_weather) if (e.effect != PW_TRICK_ROOM) kept.push_back(e);
            s.pseudo_weather.assign_from(kept);
        } else {
            s.pseudo_weather.push_back({PW_TRICK_ROOM, 5});
        }
        // Room Service: -1 Speed for each active holder; item consumed.
        for (int si = 0; si < 2; ++si)
            for (int32_t ai : side_at(s, si).active_indices)
                if (side_at(s, si).team[ai].item == ITEM_ROOM_SERVICE) {
                    side_at(s, si).team[ai].item = ITEM_NONE;
                    change_stat_stage(s, si, 4, -1, false, false, false);
                }
        return true;
    }
    return false;
}

static const int32_t VOLATILE_MOVE_IDS[27] = {48, 50, 73, 109, 164, 171, 186, 193, 194, 195,
    207, 212, 213, 227, 259, 260, 269, 281, 298, 316, 335, 367, 393, 477, 673, 748, 753};
static bool is_volatile_move(int32_t m) {
    for (int32_t v : VOLATILE_MOVE_IDS) if (v == m) return true;
    return false;
}

static bool has_timed(const PokemonState& m, int32_t effect) {
    for (const auto& tv : m.timed_volatiles) if (tv.effect == effect) return true;
    return false;
}

// _can_confuse: not already confused, no Own Tempo, not grounded in Misty Terrain.
static bool can_confuse(const PokemonState& def, const BattleState& s) {
    return !(def.volatiles & VOLATILE_CONFUSED)
        && def.ability != AB_OWN_TEMPO
        && !(s.terrain == TERRAIN_MISTY && is_grounded(def, s));
}

static bool side_has_safeguard(const SideState& side) {
    for (const auto& sc : side.side_conditions) if (sc.condition == SC_SAFEGUARD) return true;
    return false;
}

// _apply_volatile_move: volatile-setting + trapping moves. Returns true if handled.
// ACUPRESSURE (random target stat) is oracle-driven and stays unported.
static bool apply_volatile_move(BattleState& s, int side_idx, int32_t move, int attacker_slot,
                                const EffectsLuck& luck) {
    int opp = 1 - side_idx;
    PokemonState& attacker = active_mon(s, side_idx);
    bool mb = is_mold_breaker(attacker.ability);

    if (move == MOVE_LEECH_SEED) {
        PokemonState& def = active_mon(s, opp);
        if (has_type(def, TYPE_GRASS)) return true;
        if (def.ability == AB_SAP_SIPPER && !mb) { change_stat_stage(s, opp, 0, +1, false, false, false); return true; }
        if (!(def.volatiles & VOLATILE_LEECH_SEEDED)) {
            def.volatiles |= VOLATILE_LEECH_SEEDED;
            def.timed_volatiles.push_back({VE_LEECH_SEED_SOURCE_SLOT, attacker_slot});
        }
        return true;
    }
    if (move == MOVE_TAUNT) {
        PokemonState& def = active_mon(s, opp);
        bool oblivious = (def.ability == AB_OBLIVIOUS && !mb);
        bool aroma = (def.ability == AB_AROMA_VEIL && !mb);
        if (!(def.volatiles & VOLATILE_TAUNT_ACTIVE) && !oblivious && !aroma) {
            def.volatiles |= VOLATILE_TAUNT_ACTIVE;
            def.timed_volatiles.push_back({VE_TAUNT, 3});
        }
        return true;
    }
    if (move == MOVE_ENCORE) {
        PokemonState& def = active_mon(s, opp);
        if (def.last_used_slot >= 0 && !(def.volatiles & VOLATILE_ENCORE_ACTIVE)
            && def.ability != AB_AROMA_VEIL) {
            def.volatiles |= VOLATILE_ENCORE_ACTIVE;
            def.locked_slot = def.last_used_slot;
            def.timed_volatiles.push_back({VE_ENCORE, 3});
        }
        return true;
    }
    if (move == MOVE_CONFUSE_RAY || move == MOVE_SUPERSONIC || move == MOVE_SWEET_KISS) {
        if (side_has_safeguard(side_at(s, opp)) && attacker.ability != AB_INFILTRATOR) return true;
        PokemonState& def = active_mon(s, opp);
        if (can_confuse(def, s)) {
            def.volatiles |= VOLATILE_CONFUSED;
            rich_log_volatile_apply(s.turn_number, def.species, VolatileTag::CONFUSED, opp, SourceTag::MOVE);
        }
        return true;
    }
    if (move == MOVE_FLATTER) {
        change_stat_stage(s, opp, 2, +1, false, false, false);
        PokemonState& def = active_mon(s, opp);
        if (can_confuse(def, s)) {
            def.volatiles |= VOLATILE_CONFUSED;
            rich_log_volatile_apply(s.turn_number, def.species, VolatileTag::CONFUSED, opp, SourceTag::MOVE);
        }
        return true;
    }
    if (move == MOVE_SWAGGER) {
        change_stat_stage(s, opp, 0, +2, false, false, false);
        PokemonState& def = active_mon(s, opp);
        if (can_confuse(def, s)) {
            def.volatiles |= VOLATILE_CONFUSED;
            rich_log_volatile_apply(s.turn_number, def.species, VolatileTag::CONFUSED, opp, SourceTag::MOVE);
        }
        return true;
    }
    if (move == MOVE_ATTRACT) {
        PokemonState& def = active_mon(s, opp);
        bool oblivious = (def.ability == AB_OBLIVIOUS && !mb);
        if (!oblivious && def.ability != AB_OWN_TEMPO && def.ability != AB_AROMA_VEIL
            && !(def.volatiles & VOLATILE_ATTRACTED))
            def.volatiles |= VOLATILE_ATTRACTED;
        return true;
    }
    if (move == MOVE_SUBSTITUTE) {
        PokemonState& mon = active_mon(s, side_idx);
        int32_t cost = mon.max_hp / 4;
        if (mon.hp > cost && !(mon.volatiles & VOLATILE_SUBSTITUTE)) {
            mon.hp -= cost; mon.sub_hp = cost; mon.volatiles |= VOLATILE_SUBSTITUTE;
        }
        return true;
    }
    if (move == MOVE_DISABLE) {
        PokemonState& def = active_mon(s, opp);
        if (def.last_used_slot >= 0 && def.ability != AB_AROMA_VEIL && !has_timed(def, VE_DISABLE))
            def.timed_volatiles.push_back({VE_DISABLE, 4});
        return true;
    }
    if (move == MOVE_TORMENT) {
        PokemonState& def = active_mon(s, opp);
        if (!(def.volatiles & VOLATILE_TORMENT) && def.ability != AB_AROMA_VEIL)
            def.volatiles |= VOLATILE_TORMENT;
        return true;
    }
    if (move == MOVE_PERISH_SONG) {
        for (int si = 0; si < 2; ++si) {
            SideState& side = side_at(s, si);
            for (int32_t ai : side.active_indices) {
                PokemonState& mon = side.team[ai];
                if (!(mon.volatiles & VOLATILE_PERISH_SONG_ACTIVE)) {
                    mon.volatiles |= VOLATILE_PERISH_SONG_ACTIVE;
                    mon.timed_volatiles.push_back({VE_PERISH_SONG, 4});
                }
            }
        }
        return true;
    }
    if (move == MOVE_DESTINY_BOND) {
        active_mon(s, side_idx).volatiles |= VOLATILE_DESTINY_BOND;
        return true;
    }
    if (move == MOVE_FORESIGHT || move == MOVE_ODOR_SLEUTH) {
        PokemonState& def = active_mon(s, opp);
        if (!def.fainted) def.volatiles |= VOLATILE_IDENTIFIED;
        return true;
    }
    if (move == MOVE_OCTOLOCK) {
        PokemonState& def = active_mon(s, opp);
        if (!def.fainted && !has_timed(def, VE_TRAPPED)) {
            def.timed_volatiles.push_back({VE_TRAPPED, -1});
            def.timed_volatiles.push_back({VE_OCTOLOCK, -1});
        }
        return true;
    }
    if (move == MOVE_YAWN) {
        PokemonState& def = active_mon(s, opp);
        bool already_drowsy = has_timed(def, VE_DROWSY);
        bool safeguard = side_has_safeguard(side_at(s, opp));
        bool infiltrator = (attacker.ability == AB_INFILTRATOR);
        bool misty = (s.terrain == TERRAIN_MISTY && is_grounded(def, s));
        bool sleep_ab = ((def.ability == AB_SWEET_VEIL || def.ability == AB_INSOMNIA
                          || def.ability == AB_VITAL_SPIRIT) && !mb);
        if (!already_drowsy && def.status == STATUS_NONE && !sleep_ab && !misty
            && !(safeguard && !infiltrator))
            def.timed_volatiles.push_back({VE_DROWSY, 2});
        return true;
    }
    if (move == MOVE_NIGHTMARE) {
        PokemonState& def = active_mon(s, opp);
        if (def.status != STATUS_SLEEP) return true;
        if (!has_timed(def, VE_NIGHTMARE)) def.timed_volatiles.push_back({VE_NIGHTMARE, -1});
        return true;
    }
    if (move == MOVE_BLOCK || move == MOVE_MEAN_LOOK) {
        PokemonState& def = active_mon(s, opp);
        if (!has_timed(def, VE_TRAPPED)) {
            // Python also records the trapper's team index as TRAPPED_SOURCE_ID so
            // trap_release can free the victim when the trapper leaves.
            int32_t attacker_team_idx = side_at(s, side_idx).active_indices[0];
            def.timed_volatiles.push_back({VE_TRAPPED, -1});
            def.timed_volatiles.push_back({VE_TRAPPED_SOURCE_ID, attacker_team_idx});
        }
        return true;
    }
    if (move == MOVE_TEETER_DANCE) {
        PokemonState& def = active_mon(s, opp);
        if (can_confuse(def, s)) def.volatiles |= VOLATILE_CONFUSED;
        return true;
    }
    if (move == MOVE_NO_RETREAT) {
        PokemonState& mon = active_mon(s, side_idx);
        if (has_timed(mon, VE_NO_RETREAT)) return true;
        for (int stat_i = 0; stat_i < 5; ++stat_i) change_stat_stage(s, side_idx, stat_i, +1, false, false, false);
        PokemonState& mon2 = active_mon(s, side_idx);
        mon2.timed_volatiles.push_back({VE_TRAPPED, -1});
        mon2.timed_volatiles.push_back({VE_NO_RETREAT, -1});
        return true;
    }
    if (move == MOVE_LASER_FOCUS) {
        active_mon(s, side_idx).timed_volatiles.push_back({VE_LASER_FOCUS, 2});
        return true;
    }
    if (move == MOVE_MAGNET_RISE) {
        PokemonState& mon = active_mon(s, side_idx);
        if (!has_timed(mon, VE_MAGNET_RISE)) mon.timed_volatiles.push_back({VE_MAGNET_RISE, 5});
        return true;
    }
    if (move == MOVE_TELEKINESIS) {
        PokemonState& def = active_mon(s, opp);
        if (!has_timed(def, VE_TELEKINESIS)) def.timed_volatiles.push_back({VE_TELEKINESIS, 3});
        return true;
    }
    if (move == MOVE_ACUPRESSURE) {
        // +2 to a random stat (0-6). random_mode draws natively via rng->randint(0,6) mirroring
        // Python's else-branch (effects.py:937); forced mode consumes the trace answer;
        // controlled mode resolves via oracle_resolve.
        int stat_idx;
        if (luck.random_mode) {
            if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
            if (luck.rng->forced) {
                const ForcedAnswer& a = luck.rng->forced->next_answer(luck.rng->current_turn, RngEventC::ACUPRESSURE_STAT, -1);
                stat_idx = a.i0;
            } else {
                stat_idx = luck.rng->randint(0, 6);
            }
        } else {
            const SideState& mside = side_at(s, side_idx);
            const SideState& oside = side_at(s, opp);
            RngParticipants who{
                (int8_t)side_idx, (int8_t)mside.active_indices[0],
                (int8_t)opp,      (int8_t)oside.active_indices[0]};
            stat_idx = oracle_resolve(luck.overrides, RngEventC::ACUPRESSURE_STAT,
                                      {0,1,2,3,4,5,6}, who, s.turn_number);
        }
        change_stat_stage(s, side_idx, stat_idx, +2, false, false, false);
        return true;
    }

    return false;
}

// --- _apply_recovery_move (simple recovery moves only; complex variants throw) ---
static const int32_t RECOVERY_HALF[10] = {105, 303, 456, 135, 355, 236, 234, 235, 208, 659};
static const int32_t MOVE_LIFE_DEW = 791;
static const int32_t WEATHER_RECOVERY[4] = {234, 235, 236, 659}; // Moonlight/MorningSun/Synthesis/ShoreUp
static const int32_t HEAL_BELL_IDS[2] = {215, 312};

static bool is_in(const int32_t* arr, int n, int32_t v) {
    for (int i = 0; i < n; ++i) if (arr[i] == v) return true; return false;
}

// _reset_stockpile (_helpers.py): zero counter/boosts, revert accumulated Def/SpD stages.
static void reset_stockpile(BattleState& s, int side_idx) {
    PokemonState& mon = active_mon(s, side_idx);
    int32_t saved_def = mon.stockpile_def_boost;
    int32_t saved_spd = mon.stockpile_spd_boost;
    mon.stockpile_count = 0;
    mon.stockpile_def_boost = 0;
    mon.stockpile_spd_boost = 0;
    if (saved_def != 0) change_stat_stage(s, side_idx, 1, -saved_def, false, false, false);
    if (saved_spd != 0) change_stat_stage(s, side_idx, 3, -saved_spd, false, false, false);
}

static bool apply_recovery_move(BattleState& s, int side_idx, int32_t move, int attacker_slot) {
    int opp_idx = 1 - side_idx;

    if (is_in(HEAL_BELL_IDS, 2, move)) {
        SideState& side = side_at(s, side_idx);
        for (auto& mon : side.team) {
            if (mon.fainted) continue;
            if (mon.ability == AB_SAP_SIPPER) {
                mon.stage0 = std::min<int32_t>(6, mon.stage0 + 1);
                continue;
            }
            if (mon.status != STATUS_NONE) { mon.status = STATUS_NONE; mon.toxic_turns = 0; }
        }
        return true;
    }

    if (move == MOVE_HEAL_PULSE) {
        PokemonState& target = active_mon(s, opp_idx);
        int32_t heal = target.max_hp / 2;
        target.hp = std::min(target.max_hp, target.hp + heal);
        return true;
    }

    if (move == MOVE_WISH) {
        PokemonState& mon = active_mon(s, side_idx);
        SideState& side = side_at(s, side_idx);
        side.has_wish_pending = true;
        side.wish_turns = 2;
        side.wish_hp = mon.max_hp / 2;
        side.wish_slot = attacker_slot;
        return true;
    }

    if (move == MOVE_STRENGTH_SAP) {
        PokemonState& target = active_mon(s, opp_idx);
        if (target.stage0 == -6) return true;  // strength_sap_fail
        int32_t heal_amount = cpp_effective_stat(target, 1);
        PokemonState& user = active_mon(s, side_idx);
        if (target.ability == AB_LIQUID_OOZE) {
            int32_t new_hp = std::max(0, user.hp - heal_amount);
            user.hp = new_hp;
            if (new_hp == 0) cpp_faint_active(s, side_idx, /*notify_soul_heart=*/false);
        } else {
            user.hp = std::min(user.max_hp, user.hp + heal_amount);
        }
        change_stat_stage(s, opp_idx, 0, -1, false, false, false);
        return true;
    }

    bool is_recovery = is_in(RECOVERY_HALF, 10, move) || move == MOVE_LIFE_DEW;
    if (is_recovery) {
        PokemonState& mon = active_mon(s, side_idx);
        if (mon.hp >= mon.max_hp) { mon.last_move_failed = true; return true; }

        int32_t heal;
        if (is_in(WEATHER_RECOVERY, 4, move)) {
            int32_t w = s.weather;
            if (w == WEATHER_SUNNY || w == WEATHER_HARSH_SUN) heal = mon.max_hp * 2 / 3;
            else if (move == 659 /*SHORE_UP*/ && w == WEATHER_SANDSTORM) heal = mon.max_hp * 2 / 3;
            else if (w == WEATHER_RAINY || w == WEATHER_HEAVY_RAIN || w == WEATHER_SANDSTORM || w == WEATHER_HAIL)
                heal = mon.max_hp / 4;
            else heal = mon.max_hp / 2;
        } else if (move == MOVE_LIFE_DEW) {
            heal = mon.max_hp / 4;
        } else {
            heal = mon.max_hp / 2;
        }
        mon.hp = std::min(mon.max_hp, mon.hp + heal);

        // Roost: drop Flying type for the turn (restored at EOT via VE_ROOST timer).
        if (move == MOVE_ROOST && has_type(mon, TYPE_FLYING)) {
            bool pure_flying = true;
            for (int32_t t : mon.types) if (t != TYPE_FLYING) { pure_flying = false; break; }
            if (mon.types.size() == 1 || pure_flying) {
                for (auto& t : mon.types) t = TYPE_NORMAL;
            } else {
                std::vector<int32_t> kept;
                for (int32_t t : mon.types) if (t != TYPE_FLYING) kept.push_back(t);
                mon.types.assign_from(kept);
            }
            mon.timed_volatiles.push_back({VE_ROOST, 1});
        }
        return true;
    }

    if (move == MOVE_SWALLOW) {
        PokemonState& mon = active_mon(s, side_idx);
        if (mon.stockpile_count == 0) { mon.last_move_failed = true; return true; }
        if (mon.hp >= mon.max_hp) { mon.last_move_failed = true; return true; }
        int32_t denom = (mon.stockpile_count == 1) ? 4 : (mon.stockpile_count == 2) ? 2 : 1;
        int32_t heal = mon.max_hp / denom;
        mon.hp = std::min(mon.max_hp, mon.hp + heal);
        reset_stockpile(s, side_idx);
        return true;
    }

    return false;
}

static const int32_t SELF_STATUS_IDS[8] = {116, 187, 254, 266, 270, 286, 476, 747};
static bool is_self_status_move(int32_t m) {
    for (int32_t v : SELF_STATUS_IDS) if (v == m) return true;
    return false;
}

// _apply_self_status_move: user-affecting / redirection moves. Returns true if handled.
// Helping Hand / Follow Me / Rage Powder are no-ops in singles (no ally) — matches Python.
static bool apply_self_status_move(BattleState& s, int side_idx, int32_t move) {
    SideState& side = side_at(s, side_idx);
    int user_slot = side.active_indices[0];

    if (move == MOVE_HELPING_HAND) {
        for (int32_t slot : side.active_indices)
            if (slot != user_slot && !side.team[slot].fainted)
                side.team[slot].volatiles |= VOLATILE_HELPING_HAND;
        return true;
    }
    if (move == MOVE_FOLLOW_ME || move == MOVE_RAGE_POWDER) {
        if (side.active_indices.size() <= 1) return true;  // fails in singles
        side.redirect_target = user_slot;
        side.redirect_is_rage_powder = (move == MOVE_RAGE_POWDER);
        return true;
    }
    if (move == MOVE_FOCUS_ENERGY) {
        PokemonState& mon = side.team[user_slot];
        if (mon.crit_stage < 2) mon.crit_stage += 2;
        return true;
    }
    if (move == MOVE_IMPRISON) {
        PokemonState& mon = side.team[user_slot];
        std::vector<int32_t> imp;
        for (int32_t m : {mon.move_id0, mon.move_id1, mon.move_id2, mon.move_id3})
            if (m != MOVE_NONE) imp.push_back(m);
        std::sort(imp.begin(), imp.end());
        imp.erase(std::unique(imp.begin(), imp.end()), imp.end());
        side.imprisoned_moves.assign_from(imp);
        return true;
    }
    if (move == MOVE_BELLY_DRUM) {
        PokemonState& mon = side.team[user_slot];
        if (mon.stage0 >= 6) return true;
        int32_t cost = mon.max_hp / 2;
        if (mon.hp <= cost) return true;
        mon.hp -= cost;
        int32_t delta = 6 - side.team[user_slot].stage0;
        if (delta > 0) change_stat_stage(s, side_idx, 0, delta, false, false, false);
        return true;
    }
    if (move == MOVE_STOCKPILE) {
        PokemonState& mon = side.team[user_slot];
        if (mon.stockpile_count >= 3) { mon.last_move_failed = true; return true; }
        mon.stockpile_count += 1;
        int32_t def_delta = change_stat_stage(s, side_idx, 1, +1, false, false, false);
        int32_t spd_delta = change_stat_stage(s, side_idx, 3, +1, false, false, false);
        PokemonState& m2 = side.team[user_slot];
        m2.stockpile_def_boost += def_delta;
        m2.stockpile_spd_boost += spd_delta;
        return true;
    }
    if (move == MOVE_STUFF_CHEEKS) {
        PokemonState& mon = side.team[user_slot];
        if (!is_berry(mon.item)) return true;
        mon.consumed_berry = mon.item;
        mon.item = ITEM_NONE;
        change_stat_stage(s, side_idx, 1, +2, false, false, false);
        return true;
    }
    return false;
}

// --- _apply_interaction_move (status-inflict + stat-change subset; complex variants throw) ---
struct StatusInflict { int32_t move, status; bool self_target; };
static const StatusInflict STATUS_INFLICT[17] = {
    {86,3,false},{78,3,false},{137,3,false},{609,3,false},{92,5,false},{672,5,false},
    {77,4,false},{139,4,false},{261,1,false},{79,6,false},{147,6,false},{47,6,false},
    {320,6,false},{142,6,false},{95,6,false},{464,6,false},{156,6,true}};

struct StatEffect { int8_t stat; int8_t delta; bool self_target; };
// Returns nullptr-equivalent via found flag; fills a small vector.
static bool status_move_effects(int32_t move, std::vector<StatEffect>& out) {
    struct Row { int32_t move; std::vector<StatEffect> eff; };
    // Mirror _STATUS_MOVE_EFFECTS exactly.
    switch (move) {
        case 14: out={{0,2,true}}; return true;
        case 97: out={{4,2,true}}; return true;
        case 475: out={{4,2,true}}; return true;
        case 112: out={{1,2,true}}; return true;
        case 334: out={{1,2,true}}; return true;
        case 151: out={{1,2,true}}; return true;
        case 133: out={{3,2,true}}; return true;
        case 417: out={{2,2,true}}; return true;
        case 294: out={{2,3,true}}; return true;
        case 339: out={{0,1,true},{1,1,true}}; return true;
        case 347: out={{2,1,true},{3,1,true}}; return true;
        case 349: out={{0,1,true},{4,1,true}}; return true;
        case 483: out={{2,1,true},{3,1,true},{4,1,true}}; return true;
        case 504: out={{1,-1,true},{3,-1,true},{0,2,true},{2,2,true},{4,2,true}}; return true;
        case 489: out={{0,1,true},{1,1,true},{5,1,true}}; return true;
        case 468: out={{0,1,true},{5,1,true}}; return true;
        case 322: out={{1,1,true},{3,1,true}}; return true;
        case 526: out={{0,1,true},{2,1,true}}; return true;
        case 74:  out={{0,1,true},{2,1,true}}; return true;
        case 397: out={{4,2,true}}; return true;
        case 508: out={{4,2,true},{0,1,true}}; return true;
        case 104: out={{6,1,true}}; return true;
        case 107: out={{6,1,true}}; return true;
        case 111: out={{1,1,true}}; return true;
        case 336: out={{0,1,true}}; return true;
        case 184: out={{4,-2,false}}; return true;
        case 45:  out={{0,-1,false}}; return true;
        case 608: out={{0,-1,false}}; return true;
        case 204: out={{0,-2,false}}; return true;
        case 297: out={{0,-2,false}}; return true;
        case 39:  out={{1,-1,false}}; return true;
        case 43:  out={{1,-1,false}}; return true;
        case 103: out={{1,-2,false}}; return true;
        case 321: out={{0,-1,false},{1,-1,false}}; return true;
        case 313: out={{3,-2,false}}; return true;
        case 319: out={{3,-2,false}}; return true;
        case 598: out={{2,-2,false}}; return true;
        case 568: out={{0,-1,false},{2,-1,false}}; return true;
        case 715: out={{0,-1,false},{2,-1,false}}; return true;
        case 590: out={{2,-1,false}}; return true;
        case 589: out={{0,-1,false}}; return true;
        case 28:  out={{5,-1,false}}; return true;
        case 134: out={{5,-1,false}}; return true;
        case 148: out={{5,-1,false}}; return true;
        case 108: out={{5,-1,false}}; return true;
        case 230: out={{6,-2,false}}; return true;
        default: return false;
    }
}

// --- Complex interaction moves ---
static const int32_t MOVE_HAZE = 114, MOVE_TRANSFORM = 144, MOVE_CURSE = 174, MOVE_PSYCH_UP = 244,
    MOVE_MEMENTO = 262, MOVE_ROLE_PLAY = 272, MOVE_SKILL_SWAP = 285, MOVE_CAPTIVATE = 445,
    MOVE_SOAK = 487;
static const int32_t TRICK_IDS[2] = {271, 415};  // Trick, Switcheroo
static const int32_t VOLATILE_CURSED = 4, VOLATILE_TRUANT_LOAFING = 16777216;
static const int32_t ITEM_STICKY_BARB = 288;

// Item/species guard sets for Trick/Switcheroo (cannot swap these).
static const int32_t MEGA_STONE_IDS[46] = {40,41,573,575,576,577,578,579,580,582,583,584,585,
    586,587,588,589,590,591,592,594,596,598,599,602,605,607,608,612,613,614,615,616,617,618,
    619,620,621,622,623,625,626,627,628,629,630};
static const int32_t SILVALLY_IDS[18] = {773,1176,1177,1178,1179,1180,1181,1182,1183,1184,1185,
    1186,1187,1188,1189,1190,1191,1192};
static const int32_t MEMORY_ITEM_IDS[17] = {901,902,903,904,905,906,907,908,909,910,911,912,
    913,914,915,916,917};

template <int N> static bool in_set(const int32_t (&arr)[N], int32_t v) {
    for (int32_t x : arr) if (x == v) return true; return false;
}

// Returns true if handled. Mirrors the complex tail of _apply_interaction_move.
static bool apply_complex_interaction(BattleState& s, int side_idx, int32_t move,
                                      bool* competitive_defiant_triggered, ExecCtx* ctx) {
    int opp_idx = 1 - side_idx;

    if (move == MOVE_ROLE_PLAY) {
        active_mon(s, side_idx).ability = active_mon(s, opp_idx).ability;
        return true;
    }
    if (move == MOVE_SKILL_SWAP) {
        PokemonState& user = active_mon(s, side_idx);
        PokemonState& target = active_mon(s, opp_idx);
        int32_t ua = user.ability, ta = target.ability;
        user.ability = ta;
        target.ability = ua;
        if (user.ability == AB_TRUANT && user.has_acted) user.volatiles |= VOLATILE_TRUANT_LOAFING;
        if (target.ability == AB_TRUANT && target.has_acted) target.volatiles |= VOLATILE_TRUANT_LOAFING;
        return true;
    }
    if (move == MOVE_PSYCH_UP) {
        PokemonState& target = active_mon(s, opp_idx);
        PokemonState& mon = active_mon(s, side_idx);
        mon.stage0 = target.stage0; mon.stage1 = target.stage1; mon.stage2 = target.stage2;
        mon.stage3 = target.stage3; mon.stage4 = target.stage4; mon.stage5 = target.stage5;
        mon.stage6 = target.stage6;
        mon.crit_stage = target.crit_stage;
        if (has_timed_volatile(target, VE_LASER_FOCUS) && !has_timed_volatile(mon, VE_LASER_FOCUS))
            mon.timed_volatiles.push_back({VE_LASER_FOCUS, 1});
        rich_log_stat_copy(s.turn_number, side_idx, mon.species, target.species);
        return true;
    }
    if (move == MOVE_TRANSFORM) {
        PokemonState& target = active_mon(s, opp_idx);
        PokemonState& mon = active_mon(s, side_idx);
        mon.types = target.types;
        mon.has_types = true;
        mon.stage0 = target.stage0; mon.stage1 = target.stage1; mon.stage2 = target.stage2;
        mon.stage3 = target.stage3; mon.stage4 = target.stage4; mon.stage5 = target.stage5;
        mon.stage6 = target.stage6;
        mon.ability = target.ability;
        // stats: keep own HP, copy the rest.
        mon.stat_atk = target.stat_atk; mon.stat_def = target.stat_def;
        mon.stat_spa = target.stat_spa; mon.stat_spd = target.stat_spd; mon.stat_spe = target.stat_spe;
        mon.move_id0 = target.move_id0; mon.move_id1 = target.move_id1;
        mon.move_id2 = target.move_id2; mon.move_id3 = target.move_id3;
        mon.move_pp0 = std::min(5, target.move_pp0); mon.move_pp1 = std::min(5, target.move_pp1);
        mon.move_pp2 = std::min(5, target.move_pp2); mon.move_pp3 = std::min(5, target.move_pp3);
        return true;
    }
    if (move == MOVE_MEMENTO) {
        PokemonState& target = active_mon(s, opp_idx);
        if (target.stage0 <= -6 && target.stage2 <= -6) return true;  // memento_no_effect
        cpp_faint_active(s, side_idx, /*notify_soul_heart=*/false);
        change_stat_stage(s, opp_idx, 0, -2, false, false, false);
        change_stat_stage(s, opp_idx, 2, -2, false, false, false);
        return true;
    }
    if (move == MOVE_CURSE) {
        PokemonState& mon = active_mon(s, side_idx);
        if (has_type(mon, TYPE_GHOST)) {
            int32_t cost = mon.max_hp / 2;
            if (mon.hp <= cost) return true;
            mon.hp -= cost;
            active_mon(s, opp_idx).volatiles |= VOLATILE_CURSED;
        } else {
            change_stat_stage(s, side_idx, 0, +1, false, false, false);
            change_stat_stage(s, side_idx, 1, +1, false, false, false);
            change_stat_stage(s, side_idx, 4, -1, false, false, false);
        }
        return true;
    }
    if (move == MOVE_HAZE) {
        for (int si = 0; si < 2; ++si) {
            SideState& side = side_at(s, si);
            for (int32_t ai : side.active_indices) {
                PokemonState& m = side.team[ai];
                m.stage0 = m.stage1 = m.stage2 = m.stage3 = m.stage4 = m.stage5 = m.stage6 = 0;
            }
        }
        return true;
    }
    if (in_set(TRICK_IDS, move)) {
        PokemonState& mon = active_mon(s, side_idx);
        PokemonState& target = active_mon(s, opp_idx);
        if (target.ability == AB_STICKY_HOLD && target.item != ITEM_STICKY_BARB) return true;
        if (in_set(MEGA_STONE_IDS, mon.item) || in_set(MEGA_STONE_IDS, target.item)) return true;
        if (in_set(SILVALLY_IDS, mon.species) && in_set(MEMORY_ITEM_IDS, mon.item)) return true;
        if (in_set(SILVALLY_IDS, target.species) && in_set(MEMORY_ITEM_IDS, target.item)) return true;
        int32_t mi = mon.item, ti = target.item;
        mon.item = ti;
        target.item = mi;
        return true;
    }
    if (move == MOVE_CAPTIVATE) {
        PokemonState& attacker = active_mon(s, side_idx);
        PokemonState& defender = active_mon(s, opp_idx);
        bool mb = is_mold_breaker(attacker.ability);
        bool oblivious_blocks = (defender.ability == AB_OBLIVIOUS && !mb);
        if (!oblivious_blocks) {
            change_stat_stage(s, opp_idx, 2, -2, true, false, mb, ctx);
            on_stat_dropped(s, opp_idx, 2, competitive_defiant_triggered);
        }
        return true;
    }
    if (move == MOVE_SOAK) {
        PokemonState& target = active_mon(s, opp_idx);
        target.types = {TYPE_WATER};
        target.has_types = true;
        return true;
    }
    return false;
}

static void apply_interaction_move(BattleState& s, int side_idx, int32_t move,
                                   bool* competitive_defiant_triggered, ExecCtx* ctx) {
    int opp_idx = 1 - side_idx;

    // Status infliction
    for (const auto& si : STATUS_INFLICT) {
        if (si.move != move) continue;
        int target_idx = si.self_target ? side_idx : opp_idx;
        PokemonState& attacker = active_mon(s, side_idx);
        int32_t att_ability = attacker.ability;
        PokemonState& target = active_mon(s, target_idx);

        // Flash Fire absorbs Fire-type status moves
        if (!si.self_target) {
            const MoveData& md = lookup_move(move);
            if (md.move_type == TYPE_FIRE && target.ability == AB_FLASH_FIRE
                && !is_mold_breaker(att_ability)) {
                target.volatiles |= VOLATILE_FLASH_FIRE;
                return;
            }
        }
        if (!can_apply_status(target, si.status, move, att_ability, s)) return;

        if (!si.self_target) {
            const SideState& tside = side_at(s, target_idx);
            bool has_safeguard = side_has(tside, SC_SAFEGUARD);
            bool infiltrator = (att_ability == AB_INFILTRATOR);
            if (has_safeguard && !infiltrator) return;
        }

        if (si.self_target && move == MOVE_REST) {
            // REST: full heal + sleep + is_rest_sleep.
            PokemonState& m = active_mon(s, side_idx);
            m.hp = m.max_hp;
            m.status = STATUS_SLEEP;
            m.is_rest_sleep = true;
            // Rest applies sleep inline (not via apply_status_to), so it emits STATUS_APPLY
            // directly (Python effects.py:1265).
            rich_log_status_apply(s.turn_number, m.species, STATUS_SLEEP, side_idx, SourceTag::MOVE);
        } else {
            apply_status_to(s, target_idx, si.status);
            if (si.status == STATUS_TOXIC) active_mon(s, target_idx).toxic_turns = 1;
            check_status_berry(s, target_idx, 1 - target_idx);
            // Synchronize: reflect Burn/Paralysis/Poison/Toxic back to the attacker.
            PokemonState& tgt_now = active_mon(s, target_idx);
            bool reflectable = (si.status == STATUS_BURN || si.status == STATUS_PARALYSIS
                                || si.status == STATUS_POISON || si.status == STATUS_TOXIC);
            if (tgt_now.ability == AB_SYNCHRONIZE && reflectable && !si.self_target) {
                PokemonState& attacker_now = active_mon(s, side_idx);
                if (can_apply_status(attacker_now, si.status, MOVE_NONE, AB_NONE, s)) {
                    apply_status_to(s, side_idx, si.status);
                    if (si.status == STATUS_TOXIC) active_mon(s, side_idx).toxic_turns = 1;
                    check_status_berry(s, side_idx, target_idx);
                }
            }
        }
        return;
    }

    // Stat changes
    std::vector<StatEffect> effs;
    if (status_move_effects(move, effs)) {
        PokemonState& attacker = active_mon(s, side_idx);
        bool mb = is_mold_breaker(attacker.ability);
        for (const auto& e : effs) {
            bool is_opp = !e.self_target;
            int target_idx = is_opp ? opp_idx : side_idx;
            change_stat_stage(s, target_idx, e.stat, e.delta, /*opp*/is_opp,
                              /*ignore_simple*/(mb && is_opp), /*mold_breaker*/(mb && is_opp),
                              /*ctx*/is_opp ? ctx : nullptr);
            if (e.delta < 0 && is_opp)
                on_stat_dropped(s, opp_idx, e.stat, competitive_defiant_triggered);
        }
        if (move == MOVE_MINIMIZE) active_mon(s, side_idx).volatiles |= VOLATILE_MINIMIZE;
        if (move == MOVE_GROWTH && (s.weather == WEATHER_SUNNY || s.weather == WEATHER_HARSH_SUN)) {
            change_stat_stage(s, side_idx, 0, +1, false, false, false);
            change_stat_stage(s, side_idx, 2, +1, false, false, false);
        }
        if (move == MOVE_AUTOTOMIZE)
            active_mon(s, side_idx).weight_kg_reduced += 100.0;
        if (move == MOVE_DEFENSE_CURL) {
            PokemonState& m = active_mon(s, side_idx);
            m.defense_curl_used = true;
            m.volatiles |= VOLATILE_DEFENSE_CURL;
        }
        return;
    }

    if (apply_complex_interaction(s, side_idx, move, competitive_defiant_triggered, ctx)) return;

    // Status moves that reach the end of _apply_interaction_move in Python are genuine
    // silent no-ops (Python has no else-raise; these ids match none of its handled sets).
    // We enumerate them so unrecognized ids still fail loudly rather than silently no-op.
    static const int32_t INTERACTION_NOOP_MOVES[] = {
        0, 18, 46, 81, 96, 100, 106, 118, 119, 150, 159, 178, 214, 220, 226, 267, 274,
        275, 277, 289, 361, 373, 379, 382, 383, 392, 461, 502, 538, 569, 575, 578, 600,
        666, 671, 743, 775, 777, 811, 816, 849, 852, 880, 908,
    };
    for (int32_t m : INTERACTION_NOOP_MOVES)
        if (m == move) return;  // known Python no-op

    throw std::runtime_error("unported: _apply_status_move fallthrough move " + std::to_string(move));
}

void cpp_apply_status_move(BattleState& s, int side_idx, int32_t move, const EffectsLuck& luck,
                           ExecCtx& ctx, int attacker_slot) {
    if (apply_protect_move(s, side_idx, move, luck, ctx)) return;
    if (apply_hazard_move(s, side_idx, move)) return;
    if (apply_field_move(s, side_idx, move)) return;
    if (is_volatile_move(move)) { apply_volatile_move(s, side_idx, move, attacker_slot, luck); return; }
    if (apply_recovery_move(s, side_idx, move, attacker_slot)) return;
    if (is_self_status_move(move)) { apply_self_status_move(s, side_idx, move); return; }
    apply_interaction_move(s, side_idx, move, ctx.competitive_defiant_triggered, &ctx);
}

// ---------------------------------------------------------------------------
// C1.7e begin-turn / end-of-turn leaf helpers.
// ---------------------------------------------------------------------------

void cpp_apply_terrain_seeds(BattleState& s) {
    apply_terrain_seeds(s);
}

void cpp_apply_turn_start_effects(BattleState& s) {
    // Mirrors core.py _apply_turn_start_effects. Uses raw s.weather (not effective/air-lock-
    // suppressed weather) — parity-critical. Order within each side: type-sync first, then Forecast.
    for (int si = 0; si < 2; ++si) {
        {
            PokemonState& mon = active_mon(s, si);
            if (!mon.fainted && (mon.ability == AB_RKS_SYSTEM || is_silvally(mon.species))) {
                int32_t new_type = memory_type(mon.item);
                if (mon.types.size() != 1 || mon.types[0] != new_type) {
                    mon.has_types = true;
                    mon.types = {new_type};
                }
            }
        }
        {
            PokemonState& mon = active_mon(s, si);
            if (!mon.fainted && mon.ability == AB_FORECAST && is_castform_form(mon.species))
                update_castform(s, si, s.weather);
        }
    }
}

void cpp_apply_eot_form_changes(BattleState& s) {
    // effects.py apply_eot_form_changes: per-active end-of-turn form transitions.
    constexpr int32_t AB_HUNGER_SWITCH = 258, AB_ICE_FACE = 248, AB_SHIELDS_DOWN = 197,
                      AB_ZEN_MODE = 161;
    constexpr int32_t SP_MORPEKO = 877, SP_MORPEKO_HANGRY = 1226, SP_ZYGARDE = 1166,
                      SP_ZYGARDE_COMPLETE = 1167, SP_EISCUE = 875, SP_EISCUE_NOICE = 1224,
                      SP_WISHIWASHI = 746, SP_WISHIWASHI_SCHOOL = 1175, SP_MINIOR = 774,
                      SP_DARMANITAN = 555, SP_DARMANITAN_ZEN = 1092, SP_DARMANITAN_GALAR = 990,
                      SP_DARMANITAN_GALAR_ZEN = 1093;
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        for (int32_t ai : side.active_indices) {
            const PokemonState& pokemon = side.team[ai];
            if (pokemon.fainted) continue;
            int32_t ab = pokemon.ability, sp = pokemon.species;
            int32_t half = pokemon.max_hp / 2;
            if (ab == AB_HUNGER_SWITCH) {
                if (sp == SP_MORPEKO) apply_form_change(s, si, SP_MORPEKO_HANGRY);
                else if (sp == SP_MORPEKO_HANGRY) apply_form_change(s, si, SP_MORPEKO);
            } else if (ab == AB_POWER_CONSTRUCT && sp == SP_ZYGARDE && pokemon.hp <= half) {
                apply_form_change(s, si, SP_ZYGARDE_COMPLETE);
            } else if (ab == AB_ICE_FACE && sp == SP_EISCUE_NOICE && s.weather == WEATHER_HAIL) {
                apply_form_change(s, si, SP_EISCUE);
            } else if (ab == AB_FORECAST && is_castform_form(sp)) {
                update_castform(s, si, s.weather);
            } else if (ab == AB_SCHOOLING) {
                if (pokemon.hp > pokemon.max_hp / 4) {
                    if (sp == SP_WISHIWASHI) apply_form_change(s, si, SP_WISHIWASHI_SCHOOL);
                } else {
                    if (sp == SP_WISHIWASHI_SCHOOL) apply_form_change(s, si, SP_WISHIWASHI);
                }
            } else if (ab == AB_SHIELDS_DOWN) {
                if (pokemon.hp <= half) {
                    if (sp == SPECIES_MINIOR_METEOR) apply_form_change(s, si, SP_MINIOR);
                } else {
                    if (sp == SP_MINIOR) apply_form_change(s, si, SPECIES_MINIOR_METEOR);
                }
            } else if (ab == AB_ZEN_MODE) {
                if (pokemon.hp <= half) {
                    if (sp == SP_DARMANITAN) apply_form_change(s, si, SP_DARMANITAN_ZEN);
                    else if (sp == SP_DARMANITAN_GALAR) apply_form_change(s, si, SP_DARMANITAN_GALAR_ZEN);
                } else {
                    if (sp == SP_DARMANITAN_ZEN) apply_form_change(s, si, SP_DARMANITAN);
                    else if (sp == SP_DARMANITAN_GALAR_ZEN) apply_form_change(s, si, SP_DARMANITAN_GALAR);
                }
            }
        }
    }
}

void cpp_apply_eot_volatile_clear(BattleState& s) {
    constexpr int32_t V_FLINCHED = 64, V_ENDURE_ACTIVE = 2097152, V_HELPING_HAND = 33554432;
    constexpr int32_t CLEAR_MASK = V_FLINCHED | V_ENDURE_ACTIVE | V_HELPING_HAND;
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        side.redirect_target = -1;
        for (auto& poke : side.team)
            if (poke.volatiles & CLEAR_MASK) poke.volatiles &= ~CLEAR_MASK;
    }
    if (s.echoed_voice_used_this_turn) {
        s.echoed_voice_multiplier = std::min(4, s.echoed_voice_multiplier + 1);
        s.echoed_voice_used_this_turn = false;
    } else {
        s.echoed_voice_multiplier = 0;
    }
}

void cpp_apply_eot_weather_terrain(BattleState& s) {
    int32_t new_weather = s.weather, new_weather_turns = s.weather_turns;
    if (new_weather != WEATHER_NONE && new_weather_turns != -1) {
        new_weather_turns -= 1;
        if (new_weather_turns <= 0) { new_weather = WEATHER_NONE; new_weather_turns = 0; }
    }
    int32_t new_terrain = s.terrain, new_terrain_turns = s.terrain_turns;
    if (new_terrain != TERRAIN_NONE && new_terrain_turns != -1) {
        new_terrain_turns -= 1;
        if (new_terrain_turns <= 0) new_terrain = TERRAIN_NONE;
    }
    for (int si = 0; si < 2; ++si) {
        SideState& side = side_at(s, si);
        std::vector<SideConditionEntry> kept;
        for (const auto& e : side.side_conditions) {
            if (e.turns == -1) kept.push_back({e.condition, -1});
            else if (e.turns > 1) kept.push_back({e.condition, static_cast<int8_t>(e.turns - 1)});
        }
        side.side_conditions.assign_from(kept);
    }
    s.weather = new_weather; s.weather_turns = static_cast<int8_t>(new_weather_turns);
    s.terrain = new_terrain; s.terrain_turns = static_cast<int8_t>(new_terrain_turns);
    std::vector<PseudoWeatherEntry> new_pw;
    for (const auto& e : s.pseudo_weather) {
        if (e.turns == -1) new_pw.push_back({e.effect, -1});
        else if (e.turns - 1 > 0) new_pw.push_back({e.effect, static_cast<int8_t>(e.turns - 1)});
    }
    s.pseudo_weather.assign_from(new_pw);
}
