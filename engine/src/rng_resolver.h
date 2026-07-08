// Category-B RNG resolvers (accuracy, crit, multi-hit, secondary/proc/flinch chance).
// All inline over primitives — no luck-struct or state headers.
// In forced mode (rng->forced != nullptr), each resolver consumes the pre-recorded outcome
// from the trace keyed by (current_turn, event, occurrence) via ForcedTrace::force_*.
// Saturation short-circuits fire BEFORE forced lookup (Python never records saturated draws).
// Category-A oracle events have their own choke point in oracle.h.
#pragma once
#ifndef NUZLOCKE_RNG_RESOLVER_H
#define NUZLOCKE_RNG_RESOLVER_H

#include "native_rng.h"
#include "forced_trace.h"
#include <cstdint>
#include <cmath>
#include <stdexcept>
#include <vector>

// rng_resolve_accuracy: is_none (None accuracy) always hits; >=100 always hits; <=0 always misses.
// random_mode: forced → consume ACCURACY bool; else rng->random()*100 < eff_acc.
// Deterministic: eff_acc >= threshold. Saturation precedes forced lookup (Python rng.py:329-334).
inline bool rng_resolve_accuracy(double eff_acc, bool is_none, double threshold,
                                 bool random_mode, NativeRng* rng) {
    if (is_none) return true;
    if (eff_acc >= 100.0) return true;
    if (eff_acc <= 0.0) return false;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:337 _roll_bernoulli(RNGEvent.ACCURACY, effective_accuracy)
            return rng->forced->force_bool(rng->current_turn, RngEventC::ACCURACY);
        return rng->random() * 100.0 < eff_acc;
    }
    return eff_acc >= threshold;
}

// rng_resolve_crit: crit_chance <= 0.0 never crits; == 1.0 with threshold <= 100 always crits.
// random_mode: forced → consume CRIT bool; else rng->random() < crit_chance.
// Deterministic: crit_chance >= threshold. Saturation precedes forced lookup (rng.py:346-350).
// Note: float/double cast mirrors damage.cpp exactly — do not change.
inline bool rng_resolve_crit(float crit_chance, double crit_threshold,
                             bool random_mode, NativeRng* rng) {
    if (crit_chance <= 0.0f) return false;
    if (crit_chance == 1.0f && crit_threshold <= 100.0) return true;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:353 _roll_bernoulli(RNGEvent.CRIT, effective_crit_chance)
            return rng->forced->force_bool(rng->current_turn, RngEventC::CRIT);
        return rng->random() < static_cast<double>(crit_chance);
    }
    return crit_chance >= static_cast<float>(crit_threshold);
}

// rng_resolve_multi_hit: min==max shortcut. random_mode (2,5) range uses weighted choices
// {2,3,4,5} with weights {35,35,15,15}; else randint(min,max).
// Forced mode: consume MULTI_HIT_COUNT int directly (Python records the chosen value).
// Deterministic (2,5) uses cumulative bucket thresholds 0.35/0.70/0.85; general: floor.
inline int32_t rng_resolve_multi_hit(int min_hits, int max_hits, double multi_hit_roll,
                                     bool random_mode, NativeRng* rng) {
    if (min_hits == max_hits) return min_hits;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:408 _roll_categorical(RNGEvent.MULTI_HIT_COUNT, ...) records chosen value
            return static_cast<int32_t>(rng->forced->force_int(rng->current_turn, RngEventC::MULTI_HIT_COUNT));
        if (min_hits == 2 && max_hits == 5) {
            static const std::vector<int> vals = {2, 3, 4, 5};
            static const std::vector<int> wts  = {35, 35, 15, 15};
            return rng->choices(vals, wts);
        }
        return rng->randint(min_hits, max_hits);
    }
    if (min_hits == 2 && max_hits == 5) {
        double r = multi_hit_roll;
        if (r < 0.35) return 2;
        if (r < 0.70) return 3;
        if (r < 0.85) return 4;
        return 5;
    }
    int span = max_hits - min_hits;
    return (int)std::floor(min_hits + multi_hit_roll * span + 0.5);
}

// rng_resolve_chance: chance>=100 always fires; <=0 never fires.
// random_mode: forced → consume the event-specific bool; else rng->random()*100 < chance.
// Deterministic: (double)chance >= threshold. Saturation precedes forced lookup.
inline bool rng_resolve_chance(int chance, double threshold, bool random_mode, NativeRng* rng,
                               RngEventC event = RngEventC::SECONDARY_FIRES) {
    if (chance >= 100) return true;
    if (chance <= 0) return false;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:368 _roll_bernoulli(event, chance) for SECONDARY_FIRES/PROC_FIRES/FLINCH/etc.
            return rng->forced->force_bool(rng->current_turn, event);
        return rng->random() * 100.0 < (double)chance;
    }
    return (double)chance >= threshold;
}

#endif // NUZLOCKE_RNG_RESOLVER_H
