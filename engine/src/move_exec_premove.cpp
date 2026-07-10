// C1.7d Unit 2: pre-move gating (see move_exec_premove.h). Byte-identical mirror of
// _pre_move_checks in src/engine/core.py on deterministic paths; Python log() calls are
// state-neutral and omitted. Each resolver replicates src/rng.py's exact comparison direction
// and saturation short-circuit. random_mode draws via NativeRng (rng must be non-null).
#include "move_exec_premove.h"
#include "move_exec_helpers.h"   // cpp_apply_damage (confusion self-hit)
#include "damage.h"              // cpp_effective_stat
#include "effects_internal.h"    // active_mon
#include "forced_trace.h"
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

// _saturated(chance, high, low): >=100 -> high, <=0 -> low, else need_roll sentinel (returns 2).
// Returns 1/0 for the saturated outcome, 2 if a threshold comparison is required.
int saturated(double chance, bool high, bool low) {
    if (chance >= 100) return high ? 1 : 0;
    if (chance <= 0) return low ? 1 : 0;
    return 2;
}

// resolve_wake / resolve_confusion_snap / resolve_defrost share the "fire iff chance>=threshold"
// shape with saturation high=true, low=false.
// random_mode: forced → consume event bool; else random.random()*100 < chance.
// Saturation precedes forced lookup (Python _saturated guards these, rng.py:96-103).
bool resolve_fire_high(double chance, double threshold, bool random_mode, NativeRng* rng,
                       RngEventC event = RngEventC::WAKE) {
    int s = saturated(chance, /*high*/true, /*low*/false);
    if (s != 2) return s == 1;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py: _roll_bernoulli(event, chance) for WAKE/CONFUSION_SNAP/DEFROST
            return rng->forced->force_bool(rng->current_turn, event);
        return rng->random() * 100.0 < chance;
    }
    return chance >= threshold;
}

// resolve_attract / resolve_paralysis: returns "CAN act" (good outcome). Saturation high=false,
// low=true; non-saturated: chance >= threshold.
// random_mode: forced → consume inner Bernoulli bool (stored pre-negation), return !bool;
//   else random.random()*100 >= chance.
// Python rng.py:494,508: return not _roll_bernoulli(event, chance). Stored bool = inner result.
bool resolve_can_act(double chance, double threshold, bool random_mode, NativeRng* rng,
                     RngEventC event = RngEventC::FULL_PARALYSIS) {
    int s = saturated(chance, /*high*/false, /*low*/true);
    if (s != 2) return s == 1;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // Stored bool = inner Bernoulli (True = blocked). Return !bool so True → cannot act.
            return !rng->forced->force_bool(rng->current_turn, event);
        return rng->random() * 100.0 >= chance;
    }
    return chance >= threshold;
}

// resolve_confusion_self_hit: True means NOT hitting self (good). No saturation.
// random_mode: forced → consume CONFUSION_SELF_HIT bool directly (no inversion);
//   else random.random() < 66.7/100.
// Python rng.py:479 _roll_bernoulli(CONFUSION_SELF_HIT, 66.7): True = not self-hit.
constexpr double CONFUSION_NO_SELF_HIT_CHANCE = 66.7;
bool resolve_confusion_self_hit(double threshold, bool random_mode, NativeRng* rng) {
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:479 _roll_bernoulli(CONFUSION_SELF_HIT, 66.7): stored bool = result directly
            return rng->forced->force_bool(rng->current_turn, RngEventC::CONFUSION_SELF_HIT);
        return rng->random() < CONFUSION_NO_SELF_HIT_CHANCE / 100.0;
    }
    return CONFUSION_NO_SELF_HIT_CHANCE >= threshold;
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
                               RngEventC::WAKE)) {
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
                                      RngEventC::DEFROST)) {
            rich_log_presence(state.turn_number, RICH_EV_CANT_FROZEN, attacker.species);
            return false;
        } else {
            attacker.status = STATUS_NONE;
        }
    }

    if (attacker.status == STATUS_PARALYSIS) {
        // rng.py:508 _roll_bernoulli(FULL_PARALYSIS, chance); stored bool = inner Bernoulli
        if (!resolve_can_act(25.0, luck.paralysis_threshold, luck.random_mode, luck.rng,
                             RngEventC::FULL_PARALYSIS)) {
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
                               luck.random_mode, luck.rng, RngEventC::CONFUSION_SNAP)) {
            attacker.volatiles &= ~VOLATILE_CONFUSED;
            attacker.confusion_turns = 0;
        } else if (!resolve_confusion_self_hit(luck.confusion_self_hit_threshold,
                                               luck.random_mode, luck.rng)) {
            // Re-read after counter mutation; references can be invalidated only by vector growth,
            // which never happens here, but read fresh for clarity.
            PokemonState& self = active_mon(state, side_idx);
            int32_t atk_stat = cpp_effective_stat(self, 1);
            int32_t def_stat = cpp_effective_stat(self, 2);
            int32_t level = self.level;
            // Fixed typeless 40-BP self-damage: integer // truncation matches Python exactly.
            int32_t dmg = (2 * level / 5 + 2) * 40 * atk_stat / def_stat / 50 + 2;
            // resolve_damage_roll: rng.py:387 _roll_uniform(DAMAGE_ROLL).
            double roll;
            if (luck.random_mode) {
                if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
                if (luck.rng->forced)
                    roll = luck.rng->forced->force_double(luck.rng->current_turn, RngEventC::DAMAGE_ROLL);
                else
                    roll = luck.rng->random();
            } else {
                roll = luck.damage_roll;
            }
            dmg = dmg * (85 + (int32_t)(roll * 15)) / 100;
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
    // rng.py:494 _roll_bernoulli(ATTRACT_IMMOBILIZE, chance); stored bool = inner Bernoulli
    PokemonState& after = active_mon(state, side_idx);
    if (after.volatiles & VOLATILE_ATTRACTED) {
        if (!resolve_can_act(50.0, luck.attract_threshold, luck.random_mode, luck.rng,
                             RngEventC::ATTRACT_IMMOBILIZE)) {
            rich_log_presence(state.turn_number, RICH_EV_CANT_INFATUATION, after.species);
            return false;
        }
    }

    return true;
}
