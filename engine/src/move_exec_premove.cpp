// C1.7d Unit 2: pre-move gating (see move_exec_premove.h). Byte-identical mirror of
// _pre_move_checks in src/engine/core.py on deterministic paths; Python log() calls are
// state-neutral and omitted. Each resolver replicates src/rng.py's exact comparison direction
// and saturation short-circuit. random_mode draws via NativeRng (rng must be non-null).
#include "move_exec_premove.h"
#include "move_exec_helpers.h"   // cpp_apply_damage (confusion self-hit)
#include "damage.h"              // cpp_effective_stat
#include "effects_internal.h"    // active_mon
#include "forced_trace.h"
#include "rng_resolver.h"        // catb_internal, analytical_rng_log_draw, rng_resolve_confusion_self_hit_roll
#include "event_log.h"           // rich_log_cant_*/hit_self_confusion

#include <cmath>
#include <stdexcept>

using eff_internal::active_mon;

namespace {

constexpr int32_t STATUS_NONE = 0, STATUS_FREEZE = 2, STATUS_PARALYSIS = 3, STATUS_SLEEP = 6;
constexpr int32_t VOLATILE_CONFUSED = 1, VOLATILE_ATTRACTED = 8388608;
constexpr int32_t AB_NONE = 0, AB_EARLY_BIRD = 48;
constexpr int32_t MOVE_SNORE = 173, MOVE_SLEEP_TALK = 214;  // _SLEEP_USABLE_MOVES
constexpr int32_t WEATHER_SUNNY = 1, WEATHER_HARSH_SUN = 6;
// rng.py:479: 66.7% chance to NOT hit self in confusion; 33.3% self-hit.
constexpr double CONFUSION_NO_SELF_HIT_CHANCE = 66.7;

// resolve_fire_high: fires (returns true) when chance fires. Semantics: chance >= threshold.
// Occurrence-keyed injection + analytical log added on top of original logic.
// p_chosen = chance/100 when fires, 1-chance/100 when doesn't fire.
bool resolve_fire_high(double chance, double threshold, bool random_mode, NativeRng* rng,
                       RngEventC event, int turn = 0, RngParticipants who = {}) {
    // Saturation short-circuits before injection.
    if (chance >= 100.0) {
        analytical_rng_log_draw(turn, static_cast<int>(event), who, 1, {0, 1}, 1.0);
        return true;
    }
    if (chance <= 0.0) {
        analytical_rng_log_draw(turn, static_cast<int>(event), who, 0, {0, 1}, 1.0);
        return false;
    }
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(event));
    CategoryBInjection::Outcome* forced_out = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(event), occ, forced_out)) {
        if (forced_out->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for fire_high event)");
        double p = forced_out->b ? (chance / 100.0) : (1.0 - chance / 100.0);
        analytical_rng_log_draw(turn, static_cast<int>(event), who,
                                forced_out->b ? 1 : 0, {0, 1}, p);
        return forced_out->b;
    }
    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = rng->forced->force_bool(rng->current_turn, event);
        else
            result = rng->random() * 100.0 < chance;
    } else {
        result = chance >= threshold;
    }
    double p = result ? (chance / 100.0) : (1.0 - chance / 100.0);
    analytical_rng_log_draw(turn, static_cast<int>(event), who,
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// resolve_can_act: returns true = CAN ACT (not blocked). Semantics: chance >= threshold (can act).
// Blocked probability = chance/100; can-act probability = 1 - chance/100.
// p_chosen: probability of the chosen outcome (blocked: chance/100, can-act: 1-chance/100).
// Injection: push_bool true = inner Bernoulli = blocked (cannot act).
bool resolve_can_act(double chance, double threshold, bool random_mode, NativeRng* rng,
                     RngEventC event, int turn = 0, RngParticipants who = {}) {
    // Saturation: chance >= 100 → always blocked; chance <= 0 → always can act.
    if (chance >= 100.0) {
        analytical_rng_log_draw(turn, static_cast<int>(event), who, 0, {0, 1}, 1.0);
        return false;  // always blocked
    }
    if (chance <= 0.0) {
        analytical_rng_log_draw(turn, static_cast<int>(event), who, 1, {0, 1}, 1.0);
        return true;  // never blocked
    }
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(event));
    CategoryBInjection::Outcome* forced_out = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(event), occ, forced_out)) {
        if (forced_out->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for can_act event)");
        // Stored bool = inner Bernoulli = true means blocked (cannot act).
        bool blocked = forced_out->b;
        double p = blocked ? (chance / 100.0) : (1.0 - chance / 100.0);
        // chosen=1 = fires (blocked), chosen=0 = can act. Log as fires/not-fires.
        analytical_rng_log_draw(turn, static_cast<int>(event), who,
                                blocked ? 1 : 0, {0, 1}, p);
        return !blocked;  // return CAN ACT
    }
    bool result;  // result = CAN ACT
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // stored bool = inner Bernoulli = blocked; return !blocked = can act
            result = !rng->forced->force_bool(rng->current_turn, event);
        else
            result = rng->random() * 100.0 >= chance;  // >= chance: can act
    } else {
        result = chance >= threshold;  // original deterministic: chance >= threshold = can act
    }
    bool blocked = !result;
    double p = blocked ? (chance / 100.0) : (1.0 - chance / 100.0);
    analytical_rng_log_draw(turn, static_cast<int>(event), who,
                            blocked ? 1 : 0, {0, 1}, p);
    return result;
}

// resolve_confusion_self_hit: true = NOT hitting self (66.7%). Occurrence-keyed + logged.
// p_chosen = 0.667 when not self-hit, 0.333 when self-hit.
bool resolve_confusion_self_hit(double threshold, bool random_mode, NativeRng* rng,
                                int turn = 0, RngParticipants who = {}) {
    constexpr double chance = CONFUSION_NO_SELF_HIT_CHANCE;  // 66.7
    // No saturation special-case (chance is always interior).
    uint32_t occ = catb_internal::bump_occurrence(
        static_cast<int>(RngEventC::CONFUSION_SELF_HIT));
    CategoryBInjection::Outcome* forced_out = nullptr;
    if (catb_internal::try_consume_injection(
            static_cast<int>(RngEventC::CONFUSION_SELF_HIT), occ, forced_out)) {
        if (forced_out->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for CONFUSION_SELF_HIT)");
        // Stored bool = direct result: true = NOT self-hit.
        double p = forced_out->b ? (chance / 100.0) : (1.0 - chance / 100.0);
        analytical_rng_log_draw(turn, static_cast<int>(RngEventC::CONFUSION_SELF_HIT), who,
                                forced_out->b ? 1 : 0, {0, 1}, p);
        return forced_out->b;
    }
    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = rng->forced->force_bool(rng->current_turn, RngEventC::CONFUSION_SELF_HIT);
        else
            result = rng->random() < chance / 100.0;
    } else {
        result = chance >= threshold;  // original: CONFUSION_NO_SELF_HIT_CHANCE >= threshold
    }
    double p = result ? (chance / 100.0) : (1.0 - chance / 100.0);
    analytical_rng_log_draw(turn, static_cast<int>(RngEventC::CONFUSION_SELF_HIT), who,
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

} // namespace

bool cpp_pre_move_checks(BattleState& state, int side_idx, const PreMoveLuck& luck,
                         bool fire_type_move, int32_t move) {
    PokemonState& attacker = active_mon(state, side_idx);

    // Sleep-usable moves bypass the sleep gate entirely.
    if (attacker.status == STATUS_SLEEP && (move == MOVE_SNORE || move == MOVE_SLEEP_TALK))
        return true;

    if (attacker.status == STATUS_SLEEP) {
        int32_t increment = (attacker.ability == AB_EARLY_BIRD) ? 2 : 1;
        attacker.sleep_turns += increment;

        int32_t t = attacker.sleep_turns;
        double wake_chance;
        if (attacker.is_rest_sleep) {
            wake_chance = (t >= 2) ? 100.0 : 0.0;
        } else if (t <= 1) {
            wake_chance = 0.0;
        } else if (t == 2) {
            wake_chance = 33.3;
        } else if (t == 3) {
            wake_chance = 50.0;
        } else {
            wake_chance = 100.0;
        }

        if (!resolve_fire_high(wake_chance, luck.wake_threshold, luck.random_mode, luck.rng,
                               RngEventC::WAKE, state.turn_number)) {
            rich_log_cant_sleep(state.turn_number, attacker.species, attacker.sleep_turns);
            return false;
        }
        attacker.status = STATUS_NONE;
        attacker.sleep_turns = 0;
        attacker.is_rest_sleep = false;
    }

    if (attacker.status == STATUS_FREEZE) {
        if (fire_type_move) {
            attacker.status = STATUS_NONE;
        } else if (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN) {
            // Python reads state.weather directly (raw, not effective) for the sun thaw.
            attacker.status = STATUS_NONE;
        } else if (!resolve_fire_high(20.0, luck.defrost_threshold, luck.random_mode, luck.rng,
                                      RngEventC::DEFROST, state.turn_number)) {
            rich_log_presence(state.turn_number, RICH_EV_CANT_FROZEN, attacker.species);
            return false;
        } else {
            attacker.status = STATUS_NONE;
        }
    }

    if (attacker.status == STATUS_PARALYSIS) {
        // rng.py:508 _roll_bernoulli(FULL_PARALYSIS, chance); stored bool = inner Bernoulli.
        if (!resolve_can_act(25.0, luck.paralysis_threshold, luck.random_mode, luck.rng,
                             RngEventC::FULL_PARALYSIS, state.turn_number)) {
            rich_log_presence(state.turn_number, RICH_EV_CANT_PARALYSIS, attacker.species);
            return false;
        }
    }

    // Confusion: increment counter, check snap, then possibly self-hit.
    if (attacker.volatiles & VOLATILE_CONFUSED) {
        attacker.confusion_turns += 1;
        int32_t t = attacker.confusion_turns;
        double snap_chance;
        if (t <= 1) snap_chance = 0.0;
        else if (t == 2) snap_chance = 25.0;
        else if (t == 3) snap_chance = 33.3;
        else if (t == 4) snap_chance = 50.0;
        else snap_chance = 100.0;

        if (resolve_fire_high(snap_chance, luck.confusion_snap_threshold,
                              luck.random_mode, luck.rng, RngEventC::CONFUSION_SNAP,
                              state.turn_number)) {
            attacker.volatiles &= ~VOLATILE_CONFUSED;
            attacker.confusion_turns = 0;
        } else if (!resolve_confusion_self_hit(luck.confusion_self_hit_threshold,
                                               luck.random_mode, luck.rng,
                                               state.turn_number)) {
            // Re-read after counter mutation; references can be invalidated only by vector growth,
            // which never happens here, but read fresh for clarity.
            PokemonState& self = active_mon(state, side_idx);
            int32_t atk_stat = cpp_effective_stat(self, 1);
            int32_t def_stat = cpp_effective_stat(self, 2);
            int32_t level = self.level;
            // Fixed typeless 40-BP self-damage: integer // truncation matches Python exactly.
            int32_t dmg = (2 * level / 5 + 2) * 40 * atk_stat / def_stat / 50 + 2;
            // Confusion self-hit roll: 15 outcomes (int(roll*15) = 0..14 -> 85..99 multiplier).
            // Uses DAMAGE_ROLL event; occurrence-keyed and logged with p_chosen=1/15.
            int32_t roll_int = rng_resolve_confusion_self_hit_roll(
                luck.random_mode, luck.rng, luck.damage_roll);
            dmg = dmg * (85 + roll_int) / 100;
            rich_log_hit_self_confusion(state.turn_number, self.species, dmg, side_idx);
            MoveExecLuck self_luck;
            self_luck.proc_threshold = luck.proc_threshold;
            self_luck.random_mode = luck.random_mode;
            self_luck.rng = luck.rng;
            cpp_apply_damage(state, side_idx, dmg, AB_NONE, self_luck,
                             /*move_category*/-1, /*opp_side_idx*/-1, /*defender_slot*/0);
            return false;
        }
    }

    // Attract: 50% chance to be unable to act.
    // rng.py:494 _roll_bernoulli(ATTRACT_IMMOBILIZE, chance); stored bool = inner Bernoulli.
    PokemonState& after = active_mon(state, side_idx);
    if (after.volatiles & VOLATILE_ATTRACTED) {
        if (!resolve_can_act(50.0, luck.attract_threshold, luck.random_mode, luck.rng,
                             RngEventC::ATTRACT_IMMOBILIZE, state.turn_number)) {
            rich_log_presence(state.turn_number, RICH_EV_CANT_INFATUATION, after.species);
            return false;
        }
    }

    return true;
}
