// AI-scorer HP breakpoints (Task 9): HP values whose crossing can change the AI's
// action support, derived analytically from the scorer code (ai_scorer*.cpp,
// ai_damage.cpp, ai_analytic.cpp) — NOT sampled. The AI is always side 1; the player
// is side 0. Two axes: axis_side=0 = player-HP breakpoints (AI attacking / thresholds
// on player HP), axis_side=1 = AI-own-HP breakpoints (AI self-evaluation).
//
// Cardinal rules (see SOLVER_BUCKET_PLAN.md Task 9): never re-derive damage arithmetic
// — always call cpp_build_damage_context / cpp_expected_damage with the scorer's own
// LuckProfiles on BattleState copies; percentage thresholds via flip-pair bisection over
// the VERBATIM scorer expression, emitting BOTH pair values; superset emission is sound,
// omission is not. Cross-axis mechanics that cannot be represented as a fixed per-axis
// HP breakpoint THROW: Final Gambit (ai.hp vs pl.hp diagonal) and any AI living bench
// (switch-target selection is bench-composition-dependent).
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_AI_BREAKPOINTS_H
#define NUZLOCKE_SOLVER_BUCKET_AI_BREAKPOINTS_H

#include "state.h"

#include <cstdint>
#include <vector>

// Kind tag identifying the SOURCE scorer mechanic of an AI breakpoint (for auditing /
// tests), not a computed value. See ai_breakpoints.cpp for the per-kind derivation.
enum class AiBpKind {
    RollValue,            // ctx damage-roll value (cap/kill of AI's HD ranking)
    ExceptionKillEstimate,// trapping/Future Sight/Relic Song/Meteor Beam kill estimate
    SuperFangTie,         // Super Fang / Nature's Madness fractional-HP HD tie
    PursuitPct,           // Pursuit <=0.20 / <=0.40 player-HP tiers
    PoisonPct,            // poison combo gate pl.hp*100/pl.max > 20
    PlayerKoEstimate,     // player AVERAGE_LUCK damage estimate E_i vs AI HP
    PlayerTwoHitEstimate, // 2*E_i (slower-2HKO setup gate)
    RecoverKoAfter,       // E_i - heal (should_recover pl_can_ko_after)
    RecoverPct,           // should_recover / dist_recovery / Rest HP-percent thresholds
    SubPct50,             // Substitute ai.hp*100/ai.max <= 50
    BellyDrumHalf,        // Belly Drum ai.hp <= ai.max/2
    ExplosionPct,         // Explosion !kill ai-HP tiers <0.10/0.33/0.66
    MementoPct,           // Memento ai-HP tiers <0.10/0.33/0.66
};

struct AiBpEntry {
    int32_t   hp;
    AiBpKind  kind;
};

// AI-scorer HP breakpoints for one axis. AI is always side 1; axis_side selects the
// axis: 0 = player-HP entries, 1 = AI-own-HP entries. Values may fall outside
// [0, max_hp] (e.g. negative RecoverKoAfter) — the caller (seed_axis) normalizes.
// THROWS std::runtime_error containing "ai-final-gambit" when the AI active mon knows
// Final Gambit, and "ai-bench" when the AI side has a living non-active bench mon.
std::vector<AiBpEntry> ai_breakpoint_entries(const BattleState& state, int axis_side);

#endif // NUZLOCKE_SOLVER_BUCKET_AI_BREAKPOINTS_H
