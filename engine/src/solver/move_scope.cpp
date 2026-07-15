// Shared move-scope classifier implementation. Bit-identical to the former
// analytic.cpp file-statics (regression gate: test_solver_analytic + audits).
#include "solver/move_scope.h"

#include "ai_shared.h"                 // ai_move_data_get
#include "../generated/move_data.h"    // MOVE_TABLE, MoveData, SecondaryEffect

#include <cstddef>

// ---------------------------------------------------------------------------
// HP-dependent move IDs (effective bp / damage differs from the table's base
// power, making a table-based damage approach unsound). Source: core_leaf.cpp
// constants, damage.cpp compute_bp.
// ---------------------------------------------------------------------------

static const int32_t HP_DEP_MOVES[] = {
    284,  // Eruption
    323,  // Water Spout
    175,  // Flail
    179,  // Reversal
    360,  // Gyro Ball
    486,  // Electro Ball
    378,  // Wring Out
    462,  // Crush Grip
    49,   // Sonic Boom (fixed non-HP-table damage, same issue)
    82,   // Dragon Rage
    69,   // Seismic Toss
    101,  // Night Shade
    162,  // Super Fang
    717,  // Nature's Madness
    149,  // Psywave (RNG-dependent damage)
    515,  // Final Gambit
    283,  // Endeavor
    68,   // Counter
    243,  // Mirror Coat
    368,  // Metal Burst
    255,  // Spit Up
    514,  // Retaliate (damage doubles if ally fainted)
    500,  // Stored Power (boost-dependent)
    681,  // Power Trip
    386,  // Punishment
    363,  // Natural Gift (item-dependent)
    497,  // Echoed Voice
    205,  // Rollout
    301,  // Ice Ball
    419,  // Avalanche / Assurance (damage-history dependent)
    372,  // Assurance
    279,  // Revenge
    371,  // Payback
    362,  // Brine
    707,  // Stomping Tantrum
    512,  // Acrobatics
    755,  // Fishious Rend
    754,  // Bolt Beak
    804,  // Rising Voltage
    265,  // Smelling Salts
    358,  // Wake-Up Slap
    506,  // Hex
    263,  // Facade
    474,  // Venoshock
};

// ---------------------------------------------------------------------------
// Binding/trapping move IDs (multi-turn chip). Source: ai_shared.h TRAPPING_MOVES.
// ---------------------------------------------------------------------------

static const int32_t BINDING_MOVES[] = {
    250,  // Whirlpool
    83,   // Fire Spin
    328,  // Sand Tomb
    463,  // Magma Storm
    611,  // Infestation
    128,  // Clamp
    35,   // Wrap
    20,   // Bind
};

// Array-size-aware membership (avoids the manual-count off-by-one the extracted
// analytic constant carried: N_HP_DEP_MOVES was 45 for a 44-element array).
template <std::size_t N>
static bool in_list(const int32_t (&arr)[N], int32_t val) {
    for (std::size_t i = 0; i < N; ++i) if (arr[i] == val) return true;
    return false;
}

static const MoveData* get_md(int32_t move_id) {
    if (move_id <= 0) return nullptr;
    return ai_move_data_get(move_id);
}

bool is_hp_dep_move(int32_t move_id) {
    return in_list(HP_DEP_MOVES, move_id);
}

bool is_binding_move(int32_t move_id) {
    return in_list(BINDING_MOVES, move_id);
}

uint32_t check_move_scope(int32_t move_id) {
    uint32_t bits = 0;

    if (move_id <= 0) return 0;  // no move — not a violation

    const MoveData* md = get_md(move_id);
    if (!md) {
        // Unknown move ID → conservative scope out via HP_DEP_BP bit as a catch-all.
        bits |= SCOPE_HP_DEP_BP;
        return bits;
    }

    // Multi-hit: max_hits > 1.
    if (md->max_hits > 1)
        bits |= SCOPE_MULTI_HIT;

    // Accuracy < 100 (and not always-hit, which is accuracy == -1).
    if (md->accuracy >= 0 && md->accuracy < 100)
        bits |= SCOPE_ACCURACY_LT100;

    // Recoil: recoil_num >= 0 means the move has recoil.
    if (md->recoil_num >= 0)
        bits |= SCOPE_RECOIL;

    // Drain: drain_num >= 0 means the move drains.
    if (md->drain_num >= 0)
        bits |= SCOPE_DRAIN;

    // Non-zero priority.
    if (md->priority != 0)
        bits |= SCOPE_PRIORITY;

    // HP-dependent base power: explicit list of known HP-dep move IDs.
    if (is_hp_dep_move(move_id))
        bits |= SCOPE_HP_DEP_BP;

    // Binding/trapping moves.
    if (is_binding_move(move_id))
        bits |= SCOPE_BINDING;

    // Secondary effect: scope out if the move has a non-trivial secondary
    // (status, flinch, volatile, or stat change on the TARGET). Self-stat
    // changes are fine — those just affect the attacker's future damage tables.
    const SecondaryEffect& sec = md->secondary;
    bool has_opp_secondary = false;
    if (sec.chance > 0) {
        if (sec.has_status) has_opp_secondary = true;
        if (sec.flinch) has_opp_secondary = true;
        if (sec.volatile_confused > 0) has_opp_secondary = true;
        for (int i = 0; i < sec.num_stat_changes; ++i) {
            if (sec.stat_changes[i].self_flag == 0) {
                has_opp_secondary = true;
                break;
            }
        }
    }
    // Also check secondary2.
    if (!has_opp_secondary) {
        const SecondaryEffect& sec2 = md->secondary2;
        if (sec2.chance > 0) {
            if (sec2.has_status || sec2.flinch || sec2.volatile_confused > 0)
                has_opp_secondary = true;
            for (int i = 0; i < sec2.num_stat_changes && !has_opp_secondary; ++i)
                if (sec2.stat_changes[i].self_flag == 0) has_opp_secondary = true;
        }
    }
    if (has_opp_secondary)
        bits |= SCOPE_SECONDARY;

    return bits;
}
