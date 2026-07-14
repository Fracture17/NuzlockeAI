// Read-only engine queries for the analytic solver tier.
// Provides per-action damage tables (distinct roll values per crit class) and
// HP-threshold sets (one-shot discontinuities from items/abilities). Pure — no
// state mutation, no RNG consumption. Sanctioned seam into engine internals.
//
// CAVEAT: damage_table reflects cpp_calculate_damage's view only — caller-side
// modifiers applied outside it (Parental Bond, Metronome item ramp, Minimize doubling,
// OHKO overrides) are NOT in the table; those sit behind analytic scope bits.
#pragma once
#ifndef NUZLOCKE_SOLVER_ENGINE_QUERIES_H
#define NUZLOCKE_SOLVER_ENGINE_QUERIES_H

#include "state.h"
#include "move_exec.h"  // ExecAction

#include <cstdint>
#include <stdexcept>
#include <vector>

// ---------------------------------------------------------------------------
// DamageTable
// ---------------------------------------------------------------------------

// Per-crit-class sorted distinct final-damage values for one (state, attacker, move) triple.
// Each entry is computed by calling cpp_calculate_damage with roll_index=0..15 and
// crit_override=0 (noncrit) or 1 (crit), ai_scoring_view=false, and the real def_side_idx
// so screens/weather apply. Computed entirely from cpp_calculate_damage — no RNG consumed.
struct DamageTable {
    std::vector<int32_t> noncrit;       // crit_override=0: sorted distinct damage values
    std::vector<int32_t> crit;          // crit_override=1: sorted distinct damage values
    bool immune = false;                // true iff all rolls of both classes return 0

    // Multi-hit metadata (no total-damage math — mid-sequence context drift makes naive
    // totals unsound; analytic wave 0 scopes multi-hit out).
    int max_hits = 1;                   // 1 = single-hit move
    std::vector<int> hit_count_support; // possible hit counts, mirroring resolve_hit_count
};

// Query the damage table for one player action. attacker_side is 0 or 1.
// action must be a MOVE action (kind=0) with a valid move_slot; throws std::invalid_argument
// otherwise, or if the side has zero active mons.
DamageTable damage_table(const BattleState& state, int attacker_side, const ExecAction& action);

// ---------------------------------------------------------------------------
// HpThresholds
// ---------------------------------------------------------------------------

// Kind of HP discontinuity.
enum class ThresholdKind {
    FullHp,   // triggered when HP == max_hp (Focus Sash, Sturdy, Multiscale, Shadow Shield)
    Half,     // triggered when HP <= max_hp / 2 (Sitrus Berry)
    Quarter,  // triggered when HP <= max_hp / 4 (pinch/stat/Custap berries)
};

struct HpThreshold {
    int32_t threshold_hp;  // computed floor value matching engine trigger arithmetic
    ThresholdKind kind;
};

// One-shot HP discontinuities for the active mon on the given side.
struct HpThresholds {
    std::vector<HpThreshold> thresholds;
    // True iff the mon holds an unrecognized consumable item the engine may consume
    // but that this table doesn't model. Analytic callers must scope out when set.
    // This is deliberate UNKNOWN-routing, not a throw — the one place fail-loud is wrong.
    bool residual_unknown = false;
};

// Query one-shot HP discontinuities for the active mon on the given side.
// Throws std::invalid_argument if side is out of range or has no active mon.
HpThresholds hp_thresholds(const BattleState& state, int side);

#endif // NUZLOCKE_SOLVER_ENGINE_QUERIES_H
