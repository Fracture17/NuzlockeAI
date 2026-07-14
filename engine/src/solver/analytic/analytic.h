// analytic/analytic.h — wave-0 greedy certifier: pure single-hit damage race.
// Returns WIN (P(win,no faint)=1 certified), LOSS (realizable losing line exists),
// or UNKNOWN (out-of-scope mechanic, tripped guard, or unclear tightness — routing only).
// Internal invariant violations THROW std::runtime_error (fail loud).
// See SOLVER_PHASE2_PLAN.md Task 5 and port/docs/ANALYTIC.md for design rationale.
#pragma once
#ifndef NUZLOCKE_SOLVER_ANALYTIC_H
#define NUZLOCKE_SOLVER_ANALYTIC_H

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

// ---------------------------------------------------------------------------
// Scope-reason bitmask: ALL failing scope reasons accumulate into scope_mask.
// The analytic accumulates every bit before returning UNKNOWN(AT_SCOPE) so
// callers and audit tools see the complete reason set, not just the first.
// ---------------------------------------------------------------------------

// Both-or-neither: accumulate even when another bit is set first.
constexpr uint32_t SCOPE_MULTI_HIT          = (1u << 0);  // player or opp has multi-hit move
constexpr uint32_t SCOPE_ACCURACY_LT100     = (1u << 1);  // move accuracy < 100 (and != -1)
constexpr uint32_t SCOPE_SECONDARY          = (1u << 2);  // move has non-trivial secondary effect
constexpr uint32_t SCOPE_RECOIL             = (1u << 3);  // move has recoil
constexpr uint32_t SCOPE_DRAIN              = (1u << 4);  // move has drain
constexpr uint32_t SCOPE_BINDING            = (1u << 5);  // move is a binding/trapping move
constexpr uint32_t SCOPE_CHARGE_TURN        = (1u << 6);  // move requires a charge turn
constexpr uint32_t SCOPE_PRIORITY          = (1u << 7);   // move has non-zero priority
constexpr uint32_t SCOPE_HP_DEP_BP          = (1u << 8);  // move has HP-dependent base power
constexpr uint32_t SCOPE_WEATHER_SCREEN     = (1u << 9);  // active weather, terrain, or screens
constexpr uint32_t SCOPE_ENTRY_DIRTY        = (1u << 10); // non-clean entry (status/boost/volatile/side cond)
constexpr uint32_t SCOPE_ITEM_NOT_ALLOWED   = (1u << 11); // player or opp item outside allowlist
constexpr uint32_t SCOPE_OPP_NO_DAMAGE      = (1u << 12); // opp has no effective damaging move (AT_STALL)
constexpr uint32_t SCOPE_NONDEFAULT_QUESTION = (1u << 13); // non-default Question field set
constexpr uint32_t SCOPE_RESIDUAL_UNKNOWN   = (1u << 14); // hp_thresholds residual_unknown on either side

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
