// Category-B RNG resolvers (accuracy, crit, multi-hit, secondary/proc/flinch chance).
// All inline over primitives — no luck-struct or state headers.
// In forced mode (rng->forced != nullptr), each resolver consumes the pre-recorded outcome
// from the trace keyed by (current_turn, event, occurrence) via ForcedTrace::force_*.
// Saturation short-circuits fire BEFORE forced lookup (Python never records saturated draws).
// Category-A oracle events have their own choke point in oracle.h.
//
// D3 additions (analytical logger + occurrence-keyed injection):
//   - Every resolver accepts an optional RngLogCtx pointer carrying participants
//     (side+slot of attacker/defender) and the current turn. When the analytical
//     logger sink is set, each Cat-B draw is recorded with participants+options+chosen.
//   - Every resolver consults g_catb_injection() (occurrence-keyed) BEFORE any RNG
//     draw. If a forced outcome is registered for (event, occurrence), it overrides
//     everything else. Off by default (nullptr = zero effect).
#pragma once
#ifndef NUZLOCKE_RNG_RESOLVER_H
#define NUZLOCKE_RNG_RESOLVER_H

#include "native_rng.h"
#include "forced_trace.h"
#include "logger.h"
#include <cstdint>
#include <cmath>
#include <stdexcept>
#include <vector>

// Participant + turn context for a Category-B resolution. Optional at all call
// sites; when nullptr, resolvers still emit log entries with empty participants
// (side/slot = -1) and turn=0. New instrumentation is being added incrementally
// so existing call sites can stay unchanged.
struct RngLogCtx {
    RngParticipants who{};
    int turn = 0;
};

// Resolve an occurrence-keyed Category-B injection. Returns true and fills `out`
// if a forced outcome is registered for this (event, occurrence); marks it consumed.
// Returns false if no injection is active OR no entry matches. Increments the per-
// (event, turn) occurrence counter as a side effect so subsequent calls key correctly.
namespace catb_internal {
    inline uint32_t bump_occurrence(int event) {
        CategoryBOccurrenceCounters* counters = g_catb_occ_counters();
        if (!counters) return 0;  // no injection channel active
        return counters->next(event);
    }

    inline bool try_consume_injection(int event, uint32_t occurrence,
                                      CategoryBInjection::Outcome*& out) {
        CategoryBInjection* inj = g_catb_injection();
        if (!inj) { out = nullptr; return false; }
        out = inj->find(event, static_cast<int>(occurrence));
        if (!out) return false;
        out->consumed = true;
        return true;
    }
}

// rng_resolve_accuracy: is_none (None accuracy) always hits; >=100 always hits; <=0 always misses.
// random_mode: forced → consume ACCURACY bool; else rng->random()*100 < eff_acc.
// Deterministic: eff_acc >= threshold. Saturation precedes forced lookup (Python rng.py:329-334).
// D3: ctx (optional) plumbs participants for the analytical logger and keys the
// occurrence-injection channel (any active injection wins over threshold/RNG).
inline bool rng_resolve_accuracy(double eff_acc, bool is_none, double threshold,
                                 bool random_mode, NativeRng* rng,
                                 const RngLogCtx* ctx = nullptr) {
    if (is_none) return true;
    if (eff_acc >= 100.0) {
        // Saturation short-circuit — still visible to the analytical logger.
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::ACCURACY),
                                ctx ? ctx->who : RngParticipants{},
                                1, {0, 1}, 1.0);
        return true;
    }
    if (eff_acc <= 0.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::ACCURACY),
                                ctx ? ctx->who : RngParticipants{},
                                0, {0, 1}, 1.0);
        return false;
    }

    // Injection channel (occurrence-keyed). Consulted BEFORE any RNG/threshold path.
    // Bumps the per-turn occurrence counter regardless so keys stay meaningful.
    uint32_t occ = catb_internal::bump_occurrence(
        static_cast<int>(RngEventC::ACCURACY));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(
            static_cast<int>(RngEventC::ACCURACY), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for ACCURACY)");
        double p = forced->b ? (eff_acc / 100.0) : (1.0 - eff_acc / 100.0);
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::ACCURACY),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1}, p);
        return forced->b;
    }

    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:337 _roll_bernoulli(RNGEvent.ACCURACY, effective_accuracy)
            result = rng->forced->force_bool(rng->current_turn, RngEventC::ACCURACY);
        else
            result = rng->random() * 100.0 < eff_acc;
    } else {
        result = eff_acc >= threshold;
    }
    double p = result ? (eff_acc / 100.0) : (1.0 - eff_acc / 100.0);
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::ACCURACY),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// rng_resolve_crit: crit_chance <= 0.0 never crits; == 1.0 with threshold <= 100 always crits.
// random_mode: forced → consume CRIT bool; else rng->random() < crit_chance.
// Deterministic: crit_chance >= threshold. Saturation precedes forced lookup (rng.py:346-350).
// Note: float/double cast mirrors damage.cpp exactly — do not change.
inline bool rng_resolve_crit(float crit_chance, double crit_threshold,
                             bool random_mode, NativeRng* rng,
                             const RngLogCtx* ctx = nullptr) {
    if (crit_chance <= 0.0f) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::CRIT),
                                ctx ? ctx->who : RngParticipants{},
                                0, {0, 1}, 1.0);
        return false;
    }
    if (crit_chance == 1.0f && crit_threshold <= 100.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::CRIT),
                                ctx ? ctx->who : RngParticipants{},
                                1, {0, 1}, 1.0);
        return true;
    }

    uint32_t occ = catb_internal::bump_occurrence(
        static_cast<int>(RngEventC::CRIT));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(
            static_cast<int>(RngEventC::CRIT), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for CRIT)");
        double p = forced->b ? static_cast<double>(crit_chance)
                             : (1.0 - static_cast<double>(crit_chance));
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::CRIT),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1}, p);
        return forced->b;
    }

    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:353 _roll_bernoulli(RNGEvent.CRIT, effective_crit_chance)
            result = rng->forced->force_bool(rng->current_turn, RngEventC::CRIT);
        else
            result = rng->random() < static_cast<double>(crit_chance);
    } else {
        result = crit_chance >= static_cast<float>(crit_threshold);
    }
    double p = result ? static_cast<double>(crit_chance)
                      : (1.0 - static_cast<double>(crit_chance));
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::CRIT),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// Probability of a multi-hit outcome for the (2,5) weighted distribution.
// 2 or 3 hits: 35/100; 4 or 5 hits: 15/100. Used for p_chosen attribution.
inline double multi_hit_prob_25(int hits) {
    if (hits == 2 || hits == 3) return 0.35;
    if (hits == 4 || hits == 5) return 0.15;
    return -1.0;  // out of range: caller bug
}

// rng_resolve_multi_hit: min==max shortcut. random_mode (2,5) range uses weighted choices
// {2,3,4,5} with weights {35,35,15,15}; else randint(min,max).
// Forced mode: consume MULTI_HIT_COUNT int directly (Python records the chosen value).
// Deterministic (2,5) uses cumulative bucket thresholds 0.35/0.70/0.85; general: floor.
inline int32_t rng_resolve_multi_hit(int min_hits, int max_hits, double multi_hit_roll,
                                     bool random_mode, NativeRng* rng,
                                     const RngLogCtx* ctx = nullptr) {
    if (min_hits == max_hits) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::MULTI_HIT_COUNT),
                                ctx ? ctx->who : RngParticipants{},
                                min_hits, {min_hits}, 1.0);
        return min_hits;
    }

    uint32_t occ = catb_internal::bump_occurrence(
        static_cast<int>(RngEventC::MULTI_HIT_COUNT));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(
            static_cast<int>(RngEventC::MULTI_HIT_COUNT), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for MULTI_HIT_COUNT)");
        int32_t r = forced->i;
        double p = (min_hits == 2 && max_hits == 5)
                       ? multi_hit_prob_25(r)
                       : (1.0 / (max_hits - min_hits + 1));
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::MULTI_HIT_COUNT),
                                ctx ? ctx->who : RngParticipants{},
                                r, {min_hits, max_hits}, p);
        return r;
    }

    int32_t result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:408 _roll_categorical(RNGEvent.MULTI_HIT_COUNT, ...) records chosen value
            result = static_cast<int32_t>(rng->forced->force_int(rng->current_turn, RngEventC::MULTI_HIT_COUNT));
        else if (min_hits == 2 && max_hits == 5) {
            static const std::vector<int> vals = {2, 3, 4, 5};
            static const std::vector<int> wts  = {35, 35, 15, 15};
            result = rng->choices(vals, wts);
        } else {
            result = rng->randint(min_hits, max_hits);
        }
    } else if (min_hits == 2 && max_hits == 5) {
        double r = multi_hit_roll;
        if (r < 0.35)      result = 2;
        else if (r < 0.70) result = 3;
        else if (r < 0.85) result = 4;
        else               result = 5;
    } else {
        int span = max_hits - min_hits;
        result = (int)std::floor(min_hits + multi_hit_roll * span + 0.5);
    }
    double p = (min_hits == 2 && max_hits == 5)
                   ? multi_hit_prob_25(result)
                   : (1.0 / (max_hits - min_hits + 1));
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::MULTI_HIT_COUNT),
                            ctx ? ctx->who : RngParticipants{},
                            result, {min_hits, max_hits}, p);
    return result;
}

// rng_resolve_chance: chance>=100 always fires; <=0 never fires.
// random_mode: forced → consume the event-specific bool; else rng->random()*100 < chance.
// Deterministic: (double)chance >= threshold. Saturation precedes forced lookup.
inline bool rng_resolve_chance(int chance, double threshold, bool random_mode, NativeRng* rng,
                               RngEventC event = RngEventC::SECONDARY_FIRES,
                               const RngLogCtx* ctx = nullptr) {
    if (chance >= 100) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{}, 1, {0, 1}, 1.0);
        return true;
    }
    if (chance <= 0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{}, 0, {0, 1}, 1.0);
        return false;
    }

    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(event));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(event), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for chance-based event)");
        double p = forced->b ? (chance / 100.0) : (1.0 - chance / 100.0);
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1}, p);
        return forced->b;
    }

    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            // rng.py:368 _roll_bernoulli(event, chance) for SECONDARY_FIRES/PROC_FIRES/FLINCH/etc.
            result = rng->forced->force_bool(rng->current_turn, event);
        else
            result = rng->random() * 100.0 < (double)chance;
    } else {
        result = (double)chance >= threshold;
    }
    double p = result ? (chance / 100.0) : (1.0 - chance / 100.0);
    analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// rng_resolve_chance_d: double-precision chance variant for sites like WAKE (33.3%) where
// the chance is not an integer. Semantics identical to rng_resolve_chance.
inline bool rng_resolve_chance_d(double chance, double threshold, bool random_mode, NativeRng* rng,
                                  RngEventC event, const RngLogCtx* ctx = nullptr) {
    if (chance >= 100.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{}, 1, {0, 1}, 1.0);
        return true;
    }
    if (chance <= 0.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{}, 0, {0, 1}, 1.0);
        return false;
    }

    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(event));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(event), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for chance-based event)");
        double p = forced->b ? (chance / 100.0) : (1.0 - chance / 100.0);
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1}, p);
        return forced->b;
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
    analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// ---------------------------------------------------------------------------
// New standalone Cat-B resolvers for sites previously uninstrumented.
// All follow the same pattern: saturation → bump_occurrence →
// try_consume_injection (kind-check throw) → threshold/random → log w/ p_chosen.
// ---------------------------------------------------------------------------

// rng_resolve_damage_roll: draws an integer roll in [0,15] (16 equiprobable outcomes).
// random_mode native: rng->randint(0,15). Deterministic: int(damage_roll * 15).
// Forced-trace mode is handled at the call site in damage.cpp; this resolver is the
// NEW occurrence-keyed + analytical-log layer used by the solver oracle.
// NOTE: the confusion self-hit roll uses a separate 15-outcome draw; this is the main site.
inline int rng_resolve_damage_roll(bool random_mode, NativeRng* rng,
                                   double damage_roll_det = 0.5,
                                   const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::DAMAGE_ROLL));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::DAMAGE_ROLL), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for DAMAGE_ROLL)");
        int32_t roll_opts[16]; for (int i = 0; i < 16; ++i) roll_opts[i] = i;
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::DAMAGE_ROLL),
                                ctx ? ctx->who : RngParticipants{},
                                forced->i, roll_opts, 16, 1.0/16.0);
        return forced->i;
    }
    int32_t result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = static_cast<int32_t>(rng->forced->force_double(
                rng->current_turn, RngEventC::DAMAGE_ROLL) * 15.0);
        else
            result = rng->randint(0, 15);
    } else {
        result = static_cast<int32_t>(damage_roll_det * 15);
    }
    int32_t roll_opts[16]; for (int i = 0; i < 16; ++i) roll_opts[i] = i;
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::DAMAGE_ROLL),
                            ctx ? ctx->who : RngParticipants{},
                            result, roll_opts, 16, 1.0/16.0);
    return result;
}

// rng_resolve_confusion_self_hit_roll: draws the confusion self-hit damage multiplier.
// 15 outcomes: roll in [0,1) -> int(roll*15) = 0..14 -> multiplier 85..99.
// The chosen outcome is the integer in [0,14]; p_chosen = 1/15.
inline int rng_resolve_confusion_self_hit_roll(bool random_mode, NativeRng* rng,
                                               double det_roll = 0.5,
                                               const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::DAMAGE_ROLL));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::DAMAGE_ROLL), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for confusion DAMAGE_ROLL)");
        int32_t opts[15]; for (int i = 0; i < 15; ++i) opts[i] = i;
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::DAMAGE_ROLL),
                                ctx ? ctx->who : RngParticipants{},
                                forced->i, opts, 15, 1.0/15.0);
        return forced->i;
    }
    double roll;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            roll = rng->forced->force_double(rng->current_turn, RngEventC::DAMAGE_ROLL);
        else
            roll = rng->random();
    } else {
        roll = det_roll;
    }
    int32_t result = static_cast<int32_t>(roll * 15);  // 0..14
    int32_t opts[15]; for (int i = 0; i < 15; ++i) opts[i] = i;
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::DAMAGE_ROLL),
                            ctx ? ctx->who : RngParticipants{},
                            result, opts, 15, 1.0/15.0);
    return result;
}

// rng_resolve_psywave_roll_k: Psywave integer outcome k in [0,100].
// k=0 and k=100 are half-width endpoints: p_chosen=1/200.
// Interior k in [1,99]: p_chosen=1/100.
// Maps from roll in [0,1) via 50+python_round(roll*100) truncated to [0,100].
// The injection key is k directly (int); random draw returns the raw double, but
// the log records k (the integer outcome). Returns k.
inline int rng_resolve_psywave_roll_k(bool random_mode, NativeRng* rng,
                                      double det_roll = 0.5,
                                      const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::PSYWAVE_ROLL));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::PSYWAVE_ROLL), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for PSYWAVE_ROLL)");
        int k = forced->i;
        double p = (k == 0 || k == 100) ? (1.0/200.0) : (1.0/100.0);
        // True domain is k in [0,100] (101 outcomes). Report options_count=101 with
        // options_truncated=1 so log consumers cannot silently enumerate a subset;
        // the oracle must own the PSYWAVE domain (endpoints 1/200, interior 1/100).
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::PSYWAVE_ROLL),
                                ctx ? ctx->who : RngParticipants{},
                                k, nullptr, 101, p);
        return k;
    }
    double roll;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            roll = rng->forced->force_double(rng->current_turn, RngEventC::PSYWAVE_ROLL);
        else
            roll = rng->random();
    } else {
        roll = det_roll;
    }
    // Mirror core_leaf.cpp: 50 + python_round(roll*100), clamped [0,100] relative to base 50.
    // Actually Psywave damage = level * (50 + python_round(roll*100)) / 100; k = python_round(roll*100).
    auto py_round = [](double x) -> int64_t {
        double fl = std::floor(x);
        double frac = x - fl;
        int64_t f = static_cast<int64_t>(fl);
        if (frac < 0.5) return f;
        if (frac > 0.5) return f + 1;
        return (f % 2 == 0) ? f : f + 1;
    };
    int k = static_cast<int>(py_round(roll * 100.0));
    if (k < 0) k = 0;
    if (k > 100) k = 100;
    double p = (k == 0 || k == 100) ? (1.0/200.0) : (1.0/100.0);
    // Truthful domain report: options_count=101, options_truncated=1 (see above).
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::PSYWAVE_ROLL),
                            ctx ? ctx->who : RngParticipants{},
                            k, nullptr, 101, p);
    return k;
}

// rng_resolve_quick_claw: 20% proc. bool result: true=fires.
inline bool rng_resolve_quick_claw(bool random_mode, NativeRng* rng,
                                   double det_threshold = 50.0,
                                   const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::QUICK_CLAW));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::QUICK_CLAW), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for QUICK_CLAW)");
        double p = forced->b ? 0.2 : 0.8;
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::QUICK_CLAW),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1}, p);
        return forced->b;
    }
    bool result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = rng->forced->force_bool(rng->current_turn, RngEventC::QUICK_CLAW);
        else
            result = rng->random() < 0.2;
    } else {
        result = det_threshold <= 20.0;
    }
    double p = result ? 0.2 : 0.8;
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::QUICK_CLAW),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1}, p);
    return result;
}

// rng_resolve_binding_duration: 4 or 5 turns, each with probability 0.5.
// random_mode native: random() < 0.5 -> 4 else 5. Deterministic: roll >= 0.5 -> 5 else 4.
inline int rng_resolve_binding_duration(bool random_mode, NativeRng* rng,
                                        double det_roll = 0.5,
                                        const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::BINDING_DURATION));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::BINDING_DURATION), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for BINDING_DURATION)");
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::BINDING_DURATION),
                                ctx ? ctx->who : RngParticipants{},
                                forced->i, {4, 5}, 0.5);
        return forced->i;
    }
    int result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = static_cast<int>(rng->forced->force_int(rng->current_turn, RngEventC::BINDING_DURATION));
        else
            result = (rng->random() < 0.5) ? 4 : 5;
    } else {
        result = (det_roll >= 0.5) ? 5 : 4;
    }
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::BINDING_DURATION),
                            ctx ? ctx->who : RngParticipants{},
                            result, {4, 5}, 0.5);
    return result;
}

// rng_resolve_rampage_duration: 2 or 3 turns, each with probability 0.5.
// random_mode native: random() < 0.5 -> 2 else 3. Deterministic: roll >= 0.5 -> 3 else 2.
inline int rng_resolve_rampage_duration(bool random_mode, NativeRng* rng,
                                        double det_roll = 0.5,
                                        const RngLogCtx* ctx = nullptr) {
    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(RngEventC::RAMPAGE_DURATION));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(RngEventC::RAMPAGE_DURATION), occ, forced)) {
        if (forced->kind != 0)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected int for RAMPAGE_DURATION)");
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::RAMPAGE_DURATION),
                                ctx ? ctx->who : RngParticipants{},
                                forced->i, {2, 3}, 0.5);
        return forced->i;
    }
    int result;
    if (random_mode) {
        if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (rng->forced)
            result = static_cast<int>(rng->forced->force_int(rng->current_turn, RngEventC::RAMPAGE_DURATION));
        else
            result = (rng->random() < 0.5) ? 2 : 3;
    } else {
        result = (det_roll >= 0.5) ? 3 : 2;
    }
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::RAMPAGE_DURATION),
                            ctx ? ctx->who : RngParticipants{},
                            result, {2, 3}, 0.5);
    return result;
}

#endif // NUZLOCKE_RNG_RESOLVER_H
