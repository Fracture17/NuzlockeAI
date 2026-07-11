// C1.7d Unit 1: shared mutating leaf helpers (see move_exec_helpers.h).
// Mirrors src/engine/_helpers.py / core.py byte-for-byte on the deterministic paths; Python log()
// calls are state-neutral and omitted. random_mode draws via NativeRng when rng is non-null.
#include "move_exec_helpers.h"
#include "rng_resolver.h"          // rng_resolve_chance
#include "effects.h"
#include "effects_internal.h"
#include "damage.h"                // cpp_effective_stat (Shell Side Arm physical/special split)
#include "species_exp_lookup.h"    // base stats for Beast Boost raw-stat comparison
#include "stats.h"                 // compute_stat for Beast Boost raw stats
#include "event_log.h"             // rich_log_faint (damage-caused KO observation)

#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

#include <move_data.h>

using namespace eff_internal;

namespace {

// --- enum int values (mirror Python enums) ---
constexpr int32_t ITEM_NONE = 0, ITEM_FOCUS_BAND = 230, ITEM_FOCUS_SASH = 275,
    ITEM_ROCKY_HELMET = 540, ITEM_PROTECTIVE_PADS = 880, ITEM_LEPPA_BERRY = 154;

constexpr int32_t AB_NONE = 0, AB_STURDY = 5, AB_MAGIC_GUARD = 98, AB_LONG_REACH = 203,
    AB_MOXIE = 153, AB_CHILLING_NEIGH = 264, AB_AS_ONE_GLASTRIER = 266, AB_GRIM_NEIGH = 265,
    AB_AS_ONE_SPECTRIER = 267, AB_BEAST_BOOST = 224, AB_BATTLE_BOND = 210, AB_RIPEN = 247;

constexpr int32_t SP_CRAMORANT = 845, SP_CRAMORANT_GULPING = 1211, SP_CRAMORANT_GORGING = 1212,
    SP_GRENINJA_BOND = 1112, SP_GRENINJA_ASH = 1113;

constexpr int32_t MOVE_NONE = 0, MOVE_SHELL_SIDE_ARM = 801, MOVE_ROLLOUT = 205, MOVE_ICE_BALL = 301;

constexpr int32_t MOVECAT_PHYSICAL = 0, MOVECAT_SPECIAL = 1;
constexpr int32_t STATUS_PARALYSIS = 3;
constexpr int32_t TAG_CONTACT = 128;
constexpr int32_t VOLATILE_ENDURE_ACTIVE = 2097152;

// Mold Breaker family (Sturdy survival is bypassed by these).
bool is_mold_breaker_atk(int32_t ability) { return eff_internal::is_mold_breaker(ability); }

// resolve_proc: forwards to rng_resolve_chance with MoveExecLuck.proc_threshold.
bool resolve_proc_me(int chance, const MoveExecLuck& luck) {
    // rng.py:378 PROC_FIRES
    return rng_resolve_chance(chance, luck.proc_threshold, luck.random_mode, luck.rng,
                              RngEventC::PROC_FIRES);
}

// active mon at a specific active slot (defaults to slot 0 via active_indices[slot]).
PokemonState& active_at_slot(BattleState& s, int side_idx, int slot) {
    SideState& side = side_at(s, side_idx);
    return side.team[side.active_indices[slot]];
}

const MoveData& lookup_move_me(int32_t move_id) {
    int lo = 0, hi = 813;
    while (lo < hi) { int mid = (lo + hi) / 2; if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid; }
    if (lo >= 813 || MOVE_TABLE[lo].move_id != move_id)
        throw std::runtime_error("lookup_move_me: id " + std::to_string(move_id) + " not found");
    return MOVE_TABLE[lo];
}

int32_t move_pp_at(const PokemonState& m, int slot) {
    switch (slot) { case 0: return m.move_pp0; case 1: return m.move_pp1;
        case 2: return m.move_pp2; default: return m.move_pp3; }
}
void set_move_pp_at(PokemonState& m, int slot, int32_t v) {
    switch (slot) { case 0: m.move_pp0 = v; break; case 1: m.move_pp1 = v; break;
        case 2: m.move_pp2 = v; break; default: m.move_pp3 = v; break; }
}
int32_t move_id_at(const PokemonState& m, int slot) {
    switch (slot) { case 0: return m.move_id0; case 1: return m.move_id1;
        case 2: return m.move_id2; default: return m.move_id3; }
}

} // namespace

// ---------------------------------------------------------------------------
// _apply_damage
// ---------------------------------------------------------------------------
int32_t cpp_apply_damage(BattleState& state, int defender_idx, int32_t damage,
                         int32_t attacker_ability, const MoveExecLuck& luck,
                         int32_t move_category, int opp_side_idx, int defender_slot) {
    PokemonState& defender = active_at_slot(state, defender_idx, defender_slot);
    if (defender.fainted) {
        // No legitimate path damages a corpse (moves fail with no_target, residuals
        // check liveness). Reaching here means an upstream targeting bug — the class
        // that let Focus Band revive a 0-HP corpse (trace_7216781346045368782).
        throw std::runtime_error(
            "cpp_apply_damage called on already-fainted defender (species "
            + std::to_string(defender.species) + ", side " + std::to_string(defender_idx) + ")");
    }
    int32_t new_hp = std::max(0, defender.hp - damage);
    int32_t new_item = defender.item;

    if (new_hp == 0 && (defender.volatiles & VOLATILE_ENDURE_ACTIVE)) {
        new_hp = 1;
    } else if (new_hp == 0 && defender.item == ITEM_FOCUS_BAND) {
        if (resolve_proc_me(10, luck)) new_hp = 1;
    } else if (new_hp == 0 && defender.item == ITEM_FOCUS_SASH && defender.hp == defender.max_hp) {
        new_hp = 1;
        new_item = ITEM_NONE;
    } else if (new_hp == 0 && defender.ability == AB_STURDY
               && !is_mold_breaker_atk(attacker_ability)
               && defender.hp == defender.max_hp) {
        new_hp = 1;
    }

    int32_t actual_taken = std::min(damage, defender.hp);
    bool fainted = new_hp == 0;
    bool new_took_damage = defender.took_damage_this_turn || (actual_taken > 0);
    int32_t new_phys = defender.last_physical_damage_taken;
    int32_t new_spec = defender.last_special_damage_taken;
    int32_t new_last = defender.last_damage_taken;
    if (actual_taken > 0 && move_category >= 0) {
        new_last = actual_taken;
        if (move_category == MOVECAT_PHYSICAL) new_phys = actual_taken;
        else if (move_category == MOVECAT_SPECIAL) new_spec = actual_taken;
    }
    int32_t damage_taken = defender.hp - new_hp;
    defender.hp = new_hp;
    defender.has_hp = true;
    defender.fainted = fainted;
    defender.item = new_item;
    defender.took_damage_this_turn = new_took_damage;
    defender.last_physical_damage_taken = new_phys;
    defender.last_special_damage_taken = new_spec;
    defender.last_damage_taken = new_last;

    if (fainted) {
        // Mirror Python's faint_active -> release_inflicted_traps: when a mon faints via
        // _apply_damage, strip traps it was inflicting from active opponents immediately.
        int32_t fainted_team_idx = side_at(state, defender_idx).active_indices[defender_slot];
        cpp_release_inflicted_traps(state, defender_idx, fainted_team_idx);
        // FAINT emit: cpp_apply_damage faints inline (not via cpp_faint_active), so this is
        // the observation point for every damage-caused KO (Python emits it at the call site
        // after faint_active, e.g. core.py:1078/2427). Skeleton ignores DAMAGE/HITCOUNT, so
        // firing here vs. after HITCOUNT keeps the MOVE_USE/FAINT order identical.
        rich_log_faint(state.turn_number, defender.species, defender_idx);
    }

    if (!fainted) {
        // _check_berry uses active_indices[0]; slot 0 is the defender.
        // Starf Berry's oracle stat pick escapes as a NeedsRNG event (inherits std::exception,
        // not std::runtime_error) and reaches the GameDriver's TurnPause handler directly.
        check_berry(state, defender_idx, opp_side_idx, luck.rng, luck.overrides);
    }
    return damage_taken;
}

// ---------------------------------------------------------------------------
// _apply_rocky_helmet
// ---------------------------------------------------------------------------
void cpp_apply_rocky_helmet(BattleState& state, int side_idx, int defender_idx,
                            int32_t move, const MoveExecLuck& luck) {
    PokemonState& attacker = active_mon(state, side_idx);
    PokemonState& defender = active_mon(state, defender_idx);
    bool is_contact;
    if (move == MOVE_SHELL_SIDE_ARM) {
        int32_t phys = cpp_effective_stat(attacker, 1) * cpp_effective_stat(defender, 4);
        int32_t spec = cpp_effective_stat(attacker, 3) * cpp_effective_stat(defender, 2);
        if (phys > spec) is_contact = attacker.ability != AB_LONG_REACH;
        else if (spec > phys) is_contact = false;
        else is_contact = resolve_proc_me(50, luck) && attacker.ability != AB_LONG_REACH;
    } else {
        const MoveData& md = lookup_move_me(move);
        is_contact = (md.tags & TAG_CONTACT) && attacker.ability != AB_LONG_REACH;
    }
    if (is_contact
        && attacker.item != ITEM_PROTECTIVE_PADS
        && defender.item == ITEM_ROCKY_HELMET
        && !attacker.fainted
        && attacker.ability != AB_MAGIC_GUARD) {
        int32_t recoil = std::max(1, attacker.max_hp / 6);
        int32_t new_hp = std::max(0, attacker.hp - recoil);
        attacker.hp = new_hp;
        attacker.has_hp = true;
        if (new_hp == 0) {
            // Mirror Python's _apply_rocky_helmet -> faint_active: route the faint through the
            // canonical transition so traps the attacker was inflicting get released.
            cpp_faint_active(state, side_idx, /*notify_soul_heart=*/false);
        }
    }
}

// ---------------------------------------------------------------------------
// _apply_gulp_missile_projectile
// ---------------------------------------------------------------------------
void cpp_apply_gulp_missile_projectile(BattleState& state, int defender_idx, int attacker_idx) {
    int32_t def_species = active_mon(state, defender_idx).species;
    if (def_species != SP_CRAMORANT_GULPING && def_species != SP_CRAMORANT_GORGING) return;

    PokemonState& attacker = active_mon(state, attacker_idx);
    if (!attacker.fainted) {
        int32_t proj_dmg = attacker.max_hp / 4;
        int32_t new_hp = std::max(0, attacker.hp - proj_dmg);
        bool fainted = new_hp == 0;
        attacker.hp = new_hp;
        attacker.has_hp = true;
        attacker.fainted = fainted;
        if (def_species == SP_CRAMORANT_GULPING) {
            change_stat_stage(state, attacker_idx, 1, -1, /*caused_by_opponent*/true, false, false);
        } else if (!fainted) {
            // Re-read attacker_now (matches the Python snapshot taken before HP edit; ability/status
            // are unchanged so can_apply_status on the post-hit mon is equivalent).
            const PokemonState& att_now = active_mon(state, attacker_idx);
            if (can_apply_status(att_now, STATUS_PARALYSIS, MOVE_NONE, AB_NONE, state))
                apply_status_to(state, attacker_idx, STATUS_PARALYSIS);
        }
    }
    apply_form_change(state, defender_idx, SP_CRAMORANT);
}

// ---------------------------------------------------------------------------
// _apply_on_ko_effects
// ---------------------------------------------------------------------------
void cpp_apply_on_ko_effects(BattleState& state, int attacker_idx) {
    int32_t ability = active_mon(state, attacker_idx).ability;

    if (ability == AB_MOXIE || ability == AB_CHILLING_NEIGH || ability == AB_AS_ONE_GLASTRIER) {
        change_stat_stage(state, attacker_idx, 0, +1, false, false, false);
    } else if (ability == AB_GRIM_NEIGH || ability == AB_AS_ONE_SPECTRIER) {
        change_stat_stage(state, attacker_idx, 2, +1, false, false, false);
    } else if (ability == AB_BEAST_BOOST) {
        const PokemonState& attacker = active_mon(state, attacker_idx);
        SpeciesExpData sp = cpp_species_exp_data(attacker.species);
        int32_t bases[5] = {sp.base_atk, sp.base_def, sp.base_spa, sp.base_spd, sp.base_spe};
        int32_t ivs[5] = {attacker.iv_atk, attacker.iv_def, attacker.iv_spa,
                          attacker.iv_spd, attacker.iv_spe};
        int32_t raw[5];
        for (int i = 0; i < 5; ++i)
            raw[i] = compute_stat(i + 1, bases[i], ivs[i], attacker.nature, attacker.level);
        // raw.index(max(raw)): first index attaining the max (Python list.index semantics).
        int best = 0;
        for (int i = 1; i < 5; ++i) if (raw[i] > raw[best]) best = i;
        change_stat_stage(state, attacker_idx, best, +1, false, false, false);
    } else if (ability == AB_BATTLE_BOND) {
        if (active_mon(state, attacker_idx).species == SP_GRENINJA_BOND) {
            change_stat_stage(state, attacker_idx, 0, +1, false, false, false);
            change_stat_stage(state, attacker_idx, 2, +1, false, false, false);
            change_stat_stage(state, attacker_idx, 4, +1, false, false, false);
            apply_form_change(state, attacker_idx, SP_GRENINJA_ASH);
        }
    }
}

// ---------------------------------------------------------------------------
// _consume_pp
// ---------------------------------------------------------------------------
void cpp_consume_pp(BattleState& state, int side_idx, int slot, int extra_pp) {
    if (slot < 0)
        throw std::runtime_error(
            "_consume_pp called with sentinel slot " + std::to_string(slot)
            + "; Struggle/recharge spend no PP");
    PokemonState& mon = active_mon(state, side_idx);
    int32_t cur = move_pp_at(mon, slot);
    set_move_pp_at(mon, slot, std::max(0, cur - 1 - extra_pp));
}

// ---------------------------------------------------------------------------
// _check_leppa_berry
// ---------------------------------------------------------------------------
bool cpp_check_leppa_berry(BattleState& state, int side_idx, int slot, int opp_side_idx) {
    // _berry_suppressed: opp Unnerve-family blocks berries; replicate via check on opp active.
    if (opp_side_idx >= 0) {
        const PokemonState& opp = active_mon(state, opp_side_idx);
        static const int32_t SUPPRESSORS[3] = {127, 266, 267};  // Unnerve, As One G/S
        if (!opp.fainted)
            for (int32_t a : SUPPRESSORS) if (a == opp.ability) return false;
    }
    PokemonState& mon = active_mon(state, side_idx);
    if (mon.fainted || mon.item != ITEM_LEPPA_BERRY || slot < 0) return false;
    if (move_pp_at(mon, slot) != 0) return false;
    int32_t restore = mon.ability == AB_RIPEN ? 20 : 10;
    int32_t max_pp = lookup_move_me(move_id_at(mon, slot)).pp;
    set_move_pp_at(mon, slot, std::min(max_pp, restore));
    mon.item = ITEM_NONE;
    mon.consumed_berry = ITEM_LEPPA_BERRY;
    // _on_berry_consumed: Cheek Pouch heal FIRST, then Symbiosis (no ally in singles), then Unburden.
    {
        PokemonState& m2 = active_mon(state, side_idx);
        static const int32_t AB_CHEEK_POUCH = 167;
        if (m2.ability == AB_CHEEK_POUCH) {
            int32_t extra = std::max(1, m2.max_hp / 3);
            int32_t hp_before_pouch = m2.hp;
            m2.hp = std::min(m2.max_hp, m2.hp + extra);
            // HEAL source=cheek_pouch (Python _helpers.py:679): emit unconditionally,
            // mirroring effects.cpp on_berry_consumed.
            rich_log_heal(state.turn_number, m2.species, m2.hp - hp_before_pouch, m2.hp,
                          side_idx, SourceTag::CHEEK_POUCH);
        }
    }
    apply_unburden(state, side_idx);
    return true;
}

// ---------------------------------------------------------------------------
// _bump_rollout_counter
// ---------------------------------------------------------------------------
void cpp_bump_rollout_counter(BattleState& state, int side_idx, int32_t move, int32_t total_damage) {
    if ((move != MOVE_ROLLOUT && move != MOVE_ICE_BALL) || total_damage == 0) return;
    PokemonState& mon = active_mon(state, side_idx);
    mon.rollout_hits = mon.rollout_hits >= 4 ? 0 : mon.rollout_hits + 1;
}

// ---------------------------------------------------------------------------
// _reset_stockpile
// ---------------------------------------------------------------------------
void cpp_reset_stockpile(BattleState& state, int side_idx) {
    PokemonState& mon = active_mon(state, side_idx);
    int32_t saved_def = mon.stockpile_def_boost;
    int32_t saved_spd = mon.stockpile_spd_boost;
    mon.stockpile_count = 0;
    mon.stockpile_def_boost = 0;
    mon.stockpile_spd_boost = 0;
    if (saved_def != 0) change_stat_stage(state, side_idx, 1, -saved_def, false, false, false);
    if (saved_spd != 0) change_stat_stage(state, side_idx, 3, -saved_spd, false, false, false);
}
