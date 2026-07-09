// Analytical RNG logger for the solver / search layer.
// Header-only. One global toggle pointer (nullptr=off, zero work) — NO preprocessor gating.
// Entries are POD (trivially copyable): {turn, event, participants, chosen, options[]}.
// Stage E will add a separate richer LogEvent-stream logger; this one stays lean.
#pragma once
#ifndef NUZLOCKE_LOGGER_H
#define NUZLOCKE_LOGGER_H

#include "inline_vec.h"
#include <cstdint>
#include <initializer_list>
#include <stdexcept>
#include <type_traits>
#include <utility>
#include <vector>

// Participant identifiers for a single RNG draw. side/slot=-1 = "not applicable"
// (e.g. field-scoped draws like SPEED_TIE). defender fields = -1 for self-only draws
// (e.g. WAKE, ACUPRESSURE self boost).
struct RngParticipants {
    int8_t attacker_side = -1;
    int8_t attacker_slot = -1;
    int8_t defender_side = -1;
    int8_t defender_slot = -1;
};

// One recorded draw. Options are stored inline up to 16 entries (covers all Cat-B
// and every Cat-A event whose option set is small); for events with wider option
// sets (METRONOME_MOVE, SLEEP_TALK_MOVE, ACTION_SELECT) options_truncated=true and
// options_count reports how many were dropped. chosen is the resolved outcome
// (bool -> 0/1, int -> the value); event is the RngEventC integer.
struct AnalyticalRngEntry {
    int32_t turn = 0;
    int32_t event = 0;          // RngEventC value
    RngParticipants who{};
    int32_t chosen = 0;
    InlineVec<int32_t, 16> options{};
    uint16_t options_count = 0;  // total option count (may exceed options.size())
    uint8_t  options_truncated = 0;  // 1 when options_count > 16
    uint8_t  _pad = 0;
};

static_assert(std::is_trivially_copyable<AnalyticalRngEntry>::value,
              "AnalyticalRngEntry must be trivially copyable (POD)");

// Log sink: a POD entry vector. Off = nullptr; enable/disable via g_analytical_rng_log.
struct AnalyticalRngLog {
    std::vector<AnalyticalRngEntry> entries;

    void clear() { entries.clear(); }
    size_t size() const { return entries.size(); }
    const AnalyticalRngEntry& at(size_t i) const { return entries.at(i); }
};

// The one runtime toggle. nullptr = logger off; nothing happens on draws.
// Set by whoever owns a sink (test harness / bridge / solver driver).
inline AnalyticalRngLog*& g_analytical_rng_log() {
    static AnalyticalRngLog* p = nullptr;
    return p;
}

inline void set_analytical_rng_log(AnalyticalRngLog* log) { g_analytical_rng_log() = log; }
inline AnalyticalRngLog* get_analytical_rng_log() { return g_analytical_rng_log(); }

// Record one draw. options_span is used to populate options[] up to capacity.
// Only builds the entry when the sink is non-null; the branch is one comparison
// when the logger is off. Cheap enough to inline everywhere.
inline void analytical_rng_log_draw(int turn, int event_id,
                                    RngParticipants who,
                                    int chosen,
                                    const int32_t* options, size_t n_options) {
    AnalyticalRngLog* sink = g_analytical_rng_log();
    if (!sink) return;
    AnalyticalRngEntry e{};
    e.turn = turn;
    e.event = event_id;
    e.who = who;
    e.chosen = chosen;
    e.options_count = static_cast<uint16_t>(n_options);
    if (n_options <= e.options.capacity()) {
        for (size_t i = 0; i < n_options; ++i) e.options.push_back(options[i]);
        e.options_truncated = 0;
    } else {
        e.options_truncated = 1;
    }
    sink->entries.push_back(e);
}

// Convenience overload for initializer_list (used by Category-B call sites with
// small fixed options like {0,1} for hit/miss or {0,1} for crit).
inline void analytical_rng_log_draw(int turn, int event_id,
                                    RngParticipants who,
                                    int chosen,
                                    std::initializer_list<int32_t> options) {
    analytical_rng_log_draw(turn, event_id, who, chosen,
                            options.begin(), options.size());
}

// Occurrence-keyed Category-B injection channel.
// Solver need: force a SPECIFIC occurrence of a Category-B draw (e.g. "the 2nd
// accuracy check this turn misses"). Off by default (nullptr); zero effect when
// unused. When set, resolvers consult it BEFORE any threshold/random path; a
// forced outcome overrides both. Loud failure surfaced via runtime_error when
// an occurrence key is registered but the resolver's kind does not match.
struct CategoryBInjection {
    // Occurrence-keyed outcome. kind: 0=int, 1=double, 2=bool. Consumed=true once
    // fetched by a resolver; verify_exhausted() at turn end throws if any remain
    // unconsumed (fail loud on solver misuse).
    struct Outcome {
        int8_t kind = 2;
        bool b = false;
        int32_t i = 0;
        double d = 0.0;
        bool consumed = false;
    };

    // Keyed by (event_id, occurrence). Occurrence is per (turn, event) and is
    // maintained by the caller through next_occ counters.
    // Note: keys are integers; test/solver code populates them before running.
    // We use a small vector-of-pairs to keep this trivially inspectable, but a
    // map is fine — we intentionally keep the surface tiny.
    struct Key { int event; int occurrence; };

    std::vector<std::pair<uint64_t, Outcome>> entries;

    static uint64_t make_key(int event, int occurrence) {
        return (static_cast<uint64_t>(event) << 32) | static_cast<uint32_t>(occurrence);
    }

    void push_bool(int event, int occurrence, bool value) {
        Outcome o{}; o.kind = 2; o.b = value;
        entries.push_back({make_key(event, occurrence), o});
    }
    void push_int(int event, int occurrence, int32_t value) {
        Outcome o{}; o.kind = 0; o.i = value;
        entries.push_back({make_key(event, occurrence), o});
    }
    void push_double(int event, int occurrence, double value) {
        Outcome o{}; o.kind = 1; o.d = value;
        entries.push_back({make_key(event, occurrence), o});
    }

    // Look up by (event, occurrence). Returns nullptr if not registered.
    Outcome* find(int event, int occurrence) {
        uint64_t k = make_key(event, occurrence);
        for (auto& kv : entries)
            if (kv.first == k && !kv.second.consumed) return &kv.second;
        return nullptr;
    }

    void clear() { entries.clear(); }
    size_t size() const { return entries.size(); }

    // Throw if any pushed outcomes remain unconsumed. Call at turn end.
    void verify_exhausted() const {
        for (const auto& kv : entries)
            if (!kv.second.consumed)
                throw std::runtime_error(
                    "CategoryBInjection: unconsumed occurrence outcome (fail loud)");
    }
};

// Global toggle for the injection channel — mirrors the logger's on/off model.
inline CategoryBInjection*& g_catb_injection() {
    static CategoryBInjection* p = nullptr;
    return p;
}
inline void set_catb_injection(CategoryBInjection* c) { g_catb_injection() = c; }
inline CategoryBInjection* get_catb_injection() { return g_catb_injection(); }

// Per-(turn, event) occurrence counter — a global "how many times has this event
// resolved this turn?" table used by resolvers to key injection lookups. This
// state lives OUTSIDE BattleState so BattleState stays trivially copyable.
// GameDriver resets it on each new turn. Off-path (no injection registered)
// still updates the counter to keep occurrence indices meaningful.
struct CategoryBOccurrenceCounters {
    // Flat vector: index = event_id, value = occurrence count for this turn.
    // Sized to the max RngEventC value (currently 33); grow if needed.
    static constexpr size_t MAX_EVENTS = 64;
    uint32_t counts[MAX_EVENTS] = {};

    uint32_t next(int event) {
        if (event < 0 || static_cast<size_t>(event) >= MAX_EVENTS)
            throw std::runtime_error("CategoryBOccurrenceCounters: event out of range");
        return counts[event]++;
    }
    void reset() { for (size_t i = 0; i < MAX_EVENTS; ++i) counts[i] = 0; }
};

inline CategoryBOccurrenceCounters*& g_catb_occ_counters() {
    static CategoryBOccurrenceCounters* p = nullptr;
    return p;
}
inline void set_catb_occ_counters(CategoryBOccurrenceCounters* c) { g_catb_occ_counters() = c; }
inline CategoryBOccurrenceCounters* get_catb_occ_counters() { return g_catb_occ_counters(); }

// GameDriver calls this at each turn boundary so occurrence indices restart per turn.
// Zero effect when no counters are registered (nullptr fast path).
inline void reset_catb_occurrence_counters_if_registered() {
    if (CategoryBOccurrenceCounters* c = g_catb_occ_counters()) c->reset();
}

#endif // NUZLOCKE_LOGGER_H
