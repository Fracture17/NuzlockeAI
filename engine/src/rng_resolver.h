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
                                1, {0, 1});
        return true;
    }
    if (eff_acc <= 0.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::ACCURACY),
                                ctx ? ctx->who : RngParticipants{},
                                0, {0, 1});
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
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::ACCURACY),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1});
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
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::ACCURACY),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1});
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
                                0, {0, 1});
        return false;
    }
    if (crit_chance == 1.0f && crit_threshold <= 100.0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::CRIT),
                                ctx ? ctx->who : RngParticipants{},
                                1, {0, 1});
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
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::CRIT),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1});
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
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::CRIT),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1});
    return result;
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
                                min_hits, {min_hits});
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
        analytical_rng_log_draw(ctx ? ctx->turn : 0,
                                static_cast<int>(RngEventC::MULTI_HIT_COUNT),
                                ctx ? ctx->who : RngParticipants{},
                                r, {min_hits, max_hits});
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
    analytical_rng_log_draw(ctx ? ctx->turn : 0,
                            static_cast<int>(RngEventC::MULTI_HIT_COUNT),
                            ctx ? ctx->who : RngParticipants{},
                            result, {min_hits, max_hits});
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
                                ctx ? ctx->who : RngParticipants{}, 1, {0, 1});
        return true;
    }
    if (chance <= 0) {
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{}, 0, {0, 1});
        return false;
    }

    uint32_t occ = catb_internal::bump_occurrence(static_cast<int>(event));
    CategoryBInjection::Outcome* forced = nullptr;
    if (catb_internal::try_consume_injection(static_cast<int>(event), occ, forced)) {
        if (forced->kind != 2)
            throw std::runtime_error(
                "CategoryBInjection: kind mismatch (expected bool for chance-based event)");
        analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                                ctx ? ctx->who : RngParticipants{},
                                forced->b ? 1 : 0, {0, 1});
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
    analytical_rng_log_draw(ctx ? ctx->turn : 0, static_cast<int>(event),
                            ctx ? ctx->who : RngParticipants{},
                            result ? 1 : 0, {0, 1});
    return result;
}

#endif // NUZLOCKE_RNG_RESOLVER_H
