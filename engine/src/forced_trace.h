// Forced-trace replay data structures and JSON parser for golden-trace parity.
// ForcedTrace holds the rng (Cat-B) map and ordered answers (Cat-A) stream consumed
// during replay. Mismatches throw runtime_error with "forced_trace_mismatch: ..." prefix.
#pragma once
#ifndef NUZLOCKE_FORCED_TRACE_H
#define NUZLOCKE_FORCED_TRACE_H

#include "oracle.h"
#include <nlohmann/json.hpp>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// One Cat-B outcome stored in the rng map.
struct ForcedOutcome {
    int kind;        // 0=int, 1=double, 2=bool
    int64_t i;
    double d;
    bool b;
    bool consumed = false;
};

// One Cat-A answer from the ordered answer stream.
struct ForcedAnswer {
    int turn;
    int event;
    int side;        // -1 when N/A (ACTION_SELECT uses -1)
    int i0;
    int i1;
    nlohmann::json actions_p0;   // null unless ACTION_SELECT
    nlohmann::json actions_p1;
};

// Complete forced-trace for one game replay.
struct ForcedTrace {
    // Cat-B rng map keyed by (turn<<24)|(event<<16)|occurrence.
    std::unordered_map<uint64_t, ForcedOutcome> rng;
    // Per-(turn,event) next-occurrence counters for typed consume helpers.
    std::unordered_map<uint64_t, int> next_occ;
    // Ordered Cat-A answer stream.
    std::vector<ForcedAnswer> answers;
    size_t cursor = 0;

    static uint64_t key(int turn, int event, int occurrence) {
        if (occurrence < 0 || occurrence > 0xFFFF)
            throw std::runtime_error(
                "forced_trace_mismatch: occurrence out of 0-65535 range: "
                + std::to_string(occurrence));
        if (event < 0 || event > 0xFF)
            throw std::runtime_error(
                "forced_trace_mismatch: event out of 0-255 range: "
                + std::to_string(event));
        return (static_cast<uint64_t>(turn) << 24)
             | (static_cast<uint64_t>(event) << 16)
             | static_cast<uint64_t>(occurrence);
    }

    // Look up and mark consumed; throw forced_trace_mismatch if absent or already consumed.
    ForcedOutcome& catb(int turn, RngEventC event, int occurrence) {
        uint64_t k = key(turn, static_cast<int>(event), occurrence);
        auto it = rng.find(k);
        if (it == rng.end())
            throw std::runtime_error(
                "forced_trace_mismatch: missing rng outcome turn="
                + std::to_string(turn) + " event="
                + std::to_string(static_cast<int>(event)) + " occ="
                + std::to_string(occurrence));
        if (it->second.consumed)
            throw std::runtime_error(
                "forced_trace_mismatch: rng outcome already consumed turn="
                + std::to_string(turn) + " event="
                + std::to_string(static_cast<int>(event)) + " occ="
                + std::to_string(occurrence));
        it->second.consumed = true;
        return it->second;
    }

    // Return answers[cursor++]; throw on exhaustion or turn/event/side mismatch.
    const ForcedAnswer& next_answer(int expected_turn, RngEventC expected_event, int expected_side) {
        if (cursor >= answers.size())
            throw std::runtime_error(
                "forced_trace_mismatch: answer stream exhausted (cursor="
                + std::to_string(cursor) + ", total="
                + std::to_string(answers.size()) + ") expected turn="
                + std::to_string(expected_turn) + " event="
                + std::to_string(static_cast<int>(expected_event)));

        const ForcedAnswer& a = answers[cursor];
        int ev_int = static_cast<int>(expected_event);

        if (a.turn != expected_turn)
            throw std::runtime_error(
                "forced_trace_mismatch: answer turn mismatch: expected "
                + std::to_string(expected_turn) + " found "
                + std::to_string(a.turn) + " (cursor=" + std::to_string(cursor) + ")");
        if (a.event != ev_int)
            throw std::runtime_error(
                "forced_trace_mismatch: answer event mismatch: expected "
                + std::to_string(ev_int) + " found "
                + std::to_string(a.event) + " (cursor=" + std::to_string(cursor) + ")");
        if (expected_side != -1 && a.side != expected_side)
            throw std::runtime_error(
                "forced_trace_mismatch: answer side mismatch: expected "
                + std::to_string(expected_side) + " found "
                + std::to_string(a.side) + " (cursor=" + std::to_string(cursor) + ")");

        ++cursor;
        return a;
    }

    // Typed consume helpers: auto-increment per-(turn,event) occurrence, then call catb().
    // Throw forced_trace_mismatch if kind doesn't match expected type.
    static uint64_t occ_key(int turn, int event) {
        return (static_cast<uint64_t>(turn) << 8) | static_cast<uint64_t>(event);
    }

    bool force_bool(int turn, RngEventC ev) {
        int event_i = static_cast<int>(ev);
        int occ = next_occ[occ_key(turn, event_i)]++;
        ForcedOutcome& fo = catb(turn, ev, occ);
        if (fo.kind != 2)
            throw std::runtime_error(
                "forced_trace_mismatch: kind mismatch (expected bool=2) turn="
                + std::to_string(turn) + " event=" + std::to_string(event_i)
                + " occ=" + std::to_string(occ) + " got kind=" + std::to_string(fo.kind));
        return fo.b;
    }

    double force_double(int turn, RngEventC ev) {
        int event_i = static_cast<int>(ev);
        int occ = next_occ[occ_key(turn, event_i)]++;
        ForcedOutcome& fo = catb(turn, ev, occ);
        if (fo.kind != 1)
            throw std::runtime_error(
                "forced_trace_mismatch: kind mismatch (expected double=1) turn="
                + std::to_string(turn) + " event=" + std::to_string(event_i)
                + " occ=" + std::to_string(occ) + " got kind=" + std::to_string(fo.kind));
        return fo.d;
    }

    int64_t force_int(int turn, RngEventC ev) {
        int event_i = static_cast<int>(ev);
        int occ = next_occ[occ_key(turn, event_i)]++;
        ForcedOutcome& fo = catb(turn, ev, occ);
        if (fo.kind != 0)
            throw std::runtime_error(
                "forced_trace_mismatch: kind mismatch (expected int=0) turn="
                + std::to_string(turn) + " event=" + std::to_string(event_i)
                + " occ=" + std::to_string(occ) + " got kind=" + std::to_string(fo.kind));
        return fo.i;
    }

    // Throw forced_trace_mismatch if any answers remain or any rng entry was not consumed.
    void verify_exhausted() const {
        size_t leftover_answers = answers.size() - cursor;
        size_t leftover_rng = 0;
        for (const auto& kv : rng)
            if (!kv.second.consumed) ++leftover_rng;

        if (leftover_answers > 0 || leftover_rng > 0)
            throw std::runtime_error(
                "forced_trace_mismatch: trace not fully consumed at game end: "
                + std::to_string(leftover_answers) + " answer(s) remaining, "
                + std::to_string(leftover_rng) + " rng entry/entries unconsumed");
    }
};

// Parse a ForcedTrace from the payload JSON shape:
//   {"rng": [{turn, event, occurrence, outcome}, ...], "answers": [{...}, ...]}
// outcome typed by JSON value: boolean->kind 2, integer->kind 0, else double->kind 1.
ForcedTrace forced_trace_from_json(const nlohmann::json& j);

#endif // NUZLOCKE_FORCED_TRACE_H
