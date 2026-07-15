// analytic/analytic.h — wave-0 greedy certifier: pure single-hit damage race.
// Returns WIN (P(win,no faint)=1 certified), LOSS (realizable losing line exists),
// or UNKNOWN (out-of-scope mechanic, tripped guard, or unclear tightness — routing only).
// Internal invariant violations THROW std::runtime_error (fail loud).
// See SOLVER_PHASE2_PLAN.md Task 5 and port/docs/ANALYTIC.md for design rationale.
#pragma once
#ifndef NUZLOCKE_SOLVER_ANALYTIC_H
#define NUZLOCKE_SOLVER_ANALYTIC_H

#include "solver/move_scope.h"   // SCOPE_* bitmask (shared with bucket concede detectors)
#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Verdict
// ---------------------------------------------------------------------------

enum class AVerdict { WIN, LOSS, UNKNOWN };

// ---------------------------------------------------------------------------
// Tag: primary reason for UNKNOWN (or AT_OK for WIN/LOSS).
// AT_* naming mirrors the prototype's shape; wave-0 subset only.
// ---------------------------------------------------------------------------
enum ATag : int {
    AT_OK       = 0,   // decided (WIN or LOSS)
    AT_SCOPE    = 1,   // matchup or entry context outside the wave-0 allowlist
    AT_MASK     = 2,   // AI support not provably constant across the opp-HP interval
    AT_THRESH   = 3,   // item/KO threshold strictly inside the opp-HP interval
    AT_NOT_TIGHT = 4,  // race lost but a non-tight step occurred: LOSS degraded
    AT_STALL    = 5,   // opponent has no effective damaging move
    AT_CAP      = 6,   // turn/line/depth cap hit
};

// Scope-reason bitmask (SCOPE_*) is defined in solver/move_scope.h, included above,
// and shared with the bucket concede detectors. ALL failing scope reasons accumulate
// into scope_mask before returning UNKNOWN(AT_SCOPE).

// ---------------------------------------------------------------------------
// AnalyticResult
// ---------------------------------------------------------------------------

struct AnalyticResult {
    AVerdict verdict    = AVerdict::UNKNOWN;
    int      tag        = AT_OK;        // primary reason (AT_* enum value)
    uint32_t scope_mask = 0;            // ALL applicable scope bits (accumulated)
    bool     tight      = true;         // every step realizable by a single named branch
    int      kill_turn  = 0;            // set for WIN: the turn of the certified kill
    std::vector<std::string> lines;     // per-turn human-readable trace (for Task 6 trace tool)
};

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

// Certify whether the player can guarantee P(win, no faint) == 1.
// Non-default Question fields → UNKNOWN with SCOPE_NONDEFAULT_QUESTION bit.
// Internal inconsistencies (inverted interval, unexpected engine reply) THROW.
AnalyticResult analytic_certify(const BattleState& state, const Question& q);

#endif // NUZLOCKE_SOLVER_ANALYTIC_H
