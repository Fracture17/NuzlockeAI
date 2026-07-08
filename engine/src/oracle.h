// Pause-and-resume oracle layer for Category-A RNG events.
// Provides the RngEventC enum (values must equal Python RNGEvent auto() sequence),
// OracleOverrides for pre-injected answers, NeedsRNG thrown when no answer is set,
// and oracle_resolve() which either returns an override or throws NeedsRNG.
#pragma once
#ifndef NUZLOCKE_ORACLE_H
#define NUZLOCKE_ORACLE_H

#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// Integer values must match Python src/rng.py RNGEvent (auto() starting at 1).
// Category B (1-18) are threshold-controlled; Category A (19-31) are oracle events.
// Category B engine events (32-33) are appended out of section order to keep stable values.
enum class RngEventC : int {
    // Category B — controlled
    ACCURACY          = 1,
    CRIT              = 2,
    SECONDARY_FIRES   = 3,
    PROC_FIRES        = 4,
    DAMAGE_ROLL       = 5,
    PSYWAVE_ROLL      = 6,
    MULTI_HIT_COUNT   = 7,
    WAKE              = 8,
    CONFUSION_SNAP    = 9,
    DEFROST           = 10,
    CONFUSION_SELF_HIT   = 11,
    ATTRACT_IMMOBILIZE   = 12,
    FULL_PARALYSIS       = 13,
    FLINCH               = 14,
    QUICK_CLAW           = 15,
    ANCIENT_POWER_BOOST  = 16,
    BINDING_DURATION     = 17,
    RAMPAGE_DURATION     = 18,
    // Category A — uncontrolled; these events cause pause-or-override
    ACTION_SELECT        = 19,
    FORCED_SWITCH        = 20,
    POST_FAINT_SWITCH    = 21,
    METRONOME_MOVE       = 22,
    SLEEP_TALK_MOVE      = 23,
    ASSIST_MOVE          = 24,
    ACUPRESSURE_STAT     = 25,
    ROAR_TARGET          = 26,
    EFFECT_SPORE_WHICH   = 27,
    TRI_ATTACK_STATUS    = 28,
    MOODY_STATS          = 29,
    STARF_BERRY_STAT     = 30,
    SPEED_TIE            = 31,
    // Category B engine events (appended out of section order; values fixed by Python RNGEvent)
    SPEED_TIEBREAKER     = 32,
    RANDOM_TARGET        = 33,
};

// Single discrete oracle answer. i1 used only for MOODY_STATS (two picks).
struct OracleAnswer {
    int i0 = -1;
    int i1 = -1;
};

// Speed-tie resolution: ordered list of (side, priority) pairs. Defined now; used in a later stage.
struct SpeedTieOrder {
    std::vector<std::pair<int, int>> order;
};

// Pre-injected override map. Read-only on lookup (never consumed) so an override
// fires on every occurrence of that event until explicitly changed.
struct OracleOverrides {
    std::optional<SpeedTieOrder> speed_tie;
    std::unordered_map<int, OracleAnswer> answers;  // keyed by RngEventC int value

    // Transient channel: answers accumulated for the current replay region.
    // mutable because OracleOverrides is threaded as const* through luck/ctx structs.
    mutable std::unordered_map<int, std::vector<OracleAnswer>> transient;
    mutable std::unordered_map<int, size_t> transient_cursor;
    mutable std::vector<SpeedTieOrder> transient_ties;
    mutable size_t transient_tie_cursor = 0;

    // Zero all transient cursors so replay re-consumes from the start.
    void reset_transient_cursors() const {
        for (auto& kv : transient_cursor) kv.second = 0;
        transient_tie_cursor = 0;
    }

    // Called when a region completes without pause. Fails loud if replay diverged
    // (not all accumulated answers were consumed), then clears all transient state.
    void clear_transient() const {
        for (const auto& kv : transient) {
            auto it = transient_cursor.find(kv.first);
            size_t cursor = (it != transient_cursor.end()) ? it->second : 0;
            if (cursor != kv.second.size())
                throw std::runtime_error(
                    "oracle transient answers not fully consumed on region completion");
        }
        if (transient_tie_cursor != transient_ties.size())
            throw std::runtime_error(
                "oracle transient answers not fully consumed on region completion");
        transient.clear();
        transient_cursor.clear();
        transient_ties.clear();
        transient_tie_cursor = 0;
    }
};

// Thrown when an oracle event has no pre-injected override, signaling the driver to pause.
// Inherits std::exception so callers can catch by type or by std::exception&.
struct NeedsRNG : std::exception {
    RngEventC event;
    std::vector<int> options;

    NeedsRNG(RngEventC ev, std::vector<int> opts)
        : event(ev), options(std::move(opts)) {}

    const char* what() const noexcept override { return "NeedsRNG: oracle event unresolved"; }
};

// Resolve a Category-A oracle event. Consults transient queue first (for resume replays),
// then falls back to persistent answers, then throws NeedsRNG to pause.
inline int oracle_resolve(const OracleOverrides* ov, RngEventC ev, std::vector<int> options) {
    if (ov) {
        int key = static_cast<int>(ev);
        auto tit = ov->transient.find(key);
        if (tit != ov->transient.end()) {
            size_t& cursor = ov->transient_cursor[key];
            if (cursor < tit->second.size())
                return tit->second[cursor++].i0;
        }
        auto it = ov->answers.find(key);
        if (it != ov->answers.end())
            return it->second.i0;
    }
    throw NeedsRNG{ev, std::move(options)};
}

// Resolve a two-pick Category-A oracle event (MOODY_STATS: boost=i0, drop=i1). Consults
// transient queue first, then persistent answers, then throws NeedsRNG.
inline OracleAnswer oracle_resolve_pair(const OracleOverrides* ov, RngEventC ev,
                                        std::vector<int> options) {
    if (ov) {
        int key = static_cast<int>(ev);
        auto tit = ov->transient.find(key);
        if (tit != ov->transient.end()) {
            size_t& cursor = ov->transient_cursor[key];
            if (cursor < tit->second.size())
                return tit->second[cursor++];
        }
        auto it = ov->answers.find(key);
        if (it != ov->answers.end())
            return it->second;
    }
    throw NeedsRNG{ev, std::move(options)};
}

#endif // NUZLOCKE_ORACLE_H
