// Bucket solver Task 1 audit: verifies the crit-ordering invariant over the MatchupGen
// corpus. GUARANTEED invariant (USER 2026-07-14, amends spec §3 / plan amendment 5):
// WEAK dominance — crit_min >= noncrit_max (no true interleaving of ranges).
// Strict dominance (crit_min > noncrit_max) is NOT guaranteed: at low damage values
// integer truncation collapses them (pre_roll=5: crit_min = floor(floor(7.5)*0.85) = 5
// = noncrit_max). Strict dominance still holds almost always and is a per-table
// FAST-PATH PREDICATE the solver checks (one integer compare) and exploits when true;
// this test reports its measured frequency. The spec's 1.275x ratio claim is FALSE in
// integer math (actual ~1.25 = floor-composed 1.5*0.85); measured informationally only.
//
// Fixed-damage / HP-dependent moves ignore crit entirely (identical crit/noncrit
// vectors, so multi-valued ones violate even weak dominance, e.g. Psywave);
// all weak-dominance violators must be on the §5.2 allowlist.
// Test A: corpus audit over ≥500 matchups per class (uniform/berry/sash), seed 1.
// Test B: sanity anchor with a hand-built Tackle state.
#include <catch2/catch_test_macros.hpp>

#include "solver/engine_queries.h"
#include "solver/matchup_gen.h"
#include "move_exec.h"
#include "state.h"

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// §5.2 fixed-damage / HP-dependent allowlist
// IDs sourced from core_leaf.cpp (lines 65-68) and move_exec_damage.cpp (line 67).
// These moves are known to violate crit ordering because they ignore the normal
// damage formula: cpp_compute_fixed_damage is called before the crit multiplier applies,
// so crit_override has no effect on the returned value.
// ---------------------------------------------------------------------------

// Fixed-damage family (level-scaled, current-HP-dependent, or reflect-based):
static constexpr int32_t MV_SEISMIC_TOSS    = 69;   // core_leaf.cpp:65 — deals attacker.level dmg
static constexpr int32_t MV_NIGHT_SHADE     = 101;  // core_leaf.cpp:65 — deals attacker.level dmg
static constexpr int32_t MV_SUPER_FANG      = 162;  // core_leaf.cpp:66 — deals defender.hp / 2
static constexpr int32_t MV_NATURES_MADNESS = 717;  // core_leaf.cpp:66 — deals defender.hp / 2
static constexpr int32_t MV_FINAL_GAMBIT    = 515;  // core_leaf.cpp:66 — deals attacker.hp
static constexpr int32_t MV_ENDEAVOR        = 283;  // core_leaf.cpp:67 — equalises HP
static constexpr int32_t MV_COUNTER         = 68;   // core_leaf.cpp:67 — reflects phys damage
static constexpr int32_t MV_MIRROR_COAT     = 243;  // core_leaf.cpp:67 — reflects spec damage
static constexpr int32_t MV_METAL_BURST     = 368;  // core_leaf.cpp:67 — reflects last damage
// Additional fixed-damage moves in the engine:
static constexpr int32_t MV_DRAGON_RAGE     = 82;   // core_leaf.cpp:65 — always 40 damage
static constexpr int32_t MV_SONIC_BOOM      = 49;   // core_leaf.cpp:65 — always 20 damage
static constexpr int32_t MV_PSYWAVE         = 149;  // core_leaf.cpp:68 — roll-based (50±50% level)
// OHKO moves (move_exec_damage.cpp:67 — damage = defender.hp):
static constexpr int32_t MV_GUILLOTINE      = 12;
static constexpr int32_t MV_HORN_DRILL      = 32;
static constexpr int32_t MV_FISSURE         = 90;
static constexpr int32_t MV_SHEER_COLD      = 329;

// The weak-dominance allowlist: moves that may violate crit_min >= noncrit_max.
// Fixed-damage moves have identical crit/noncrit vectors, so any multi-valued one
// (e.g. Psywave's roll spread) has crit_min = vector_min < vector_max = noncrit_max.
// Single-valued ones sit at equality (weak-OK) and reflect moves return 0/0 (skipped),
// but the whole family is allowlisted since crit never applies to any of them.
static const std::set<int32_t> FIXED_DAMAGE_ALLOWLIST = {
    MV_SEISMIC_TOSS, MV_NIGHT_SHADE,
    MV_SUPER_FANG,   MV_NATURES_MADNESS,
    MV_FINAL_GAMBIT, MV_ENDEAVOR,
    MV_COUNTER,      MV_MIRROR_COAT, MV_METAL_BURST,
    MV_DRAGON_RAGE,  MV_SONIC_BOOM,  MV_PSYWAVE,
    MV_GUILLOTINE,   MV_HORN_DRILL,  MV_FISSURE,  MV_SHEER_COLD,
};

// ---------------------------------------------------------------------------
// Violation record (weak dominance failure: crit_min < noncrit_max)
// ---------------------------------------------------------------------------

struct Violation {
    std::string klass_name;
    int         matchup_index;
    int         attacker_side;
    int32_t     move_id;
    int32_t     noncrit_max;
    int32_t     crit_min;
};

// ---------------------------------------------------------------------------
// Helper: return move_id for a given slot
// ---------------------------------------------------------------------------

static int32_t move_id_for_slot(const PokemonState& mon, int slot) {
    switch (slot) {
        case 0: return mon.move_id0;
        case 1: return mon.move_id1;
        case 2: return mon.move_id2;
        case 3: return mon.move_id3;
        default: return 0;
    }
}

// ---------------------------------------------------------------------------
// Audit one BattleState for both sides over all occupied move slots.
// Asserted invariant: WEAK dominance (crit_min >= noncrit_max); violations appended.
// Measured informationally: strict dominance frequency (the solver's fast-path
// predicate) and 1.275x ratio failures.
// ---------------------------------------------------------------------------

static void audit_state(const BattleState& state,
                        const std::string& klass_name,
                        int matchup_index,
                        std::vector<Violation>& violations,
                        int& moves_checked,
                        int& tables_skipped,
                        int& strict_holds,
                        int& ratio_violations)
{
    for (int side = 0; side <= 1; ++side) {
        for (int slot = 0; slot < 4; ++slot) {
            const SideState& ss = (side == 0) ? state.side0 : state.side1;
            if (ss.team.empty() || ss.active_indices.empty()) continue;
            const PokemonState& mon = ss.team[ss.active_indices[0]];
            int32_t mid = move_id_for_slot(mon, slot);
            if (mid <= 0) continue;

            ExecAction action{};
            action.kind = 0;
            action.move_slot = slot;

            DamageTable tbl = damage_table(state, side, action);

            // Skip immune or all-zero tables (no damage possible).
            if (tbl.immune) { ++tables_skipped; continue; }
            if (tbl.noncrit.empty() || tbl.crit.empty()) { ++tables_skipped; continue; }

            int32_t nc_max = tbl.noncrit.back();
            int32_t c_min  = tbl.crit.front();

            // Skip if both are zero (status move or fixed-damage returning 0).
            if (nc_max == 0 && c_min == 0) { ++tables_skipped; continue; }

            ++moves_checked;

            // Asserted invariant: weak dominance (crit range never dips below noncrit).
            if (c_min < nc_max) {
                violations.push_back({klass_name, matchup_index, side, mid, nc_max, c_min});
            }

            // Informational: strict dominance — the fast-path predicate the solver
            // checks per damage table and exploits when true (almost always).
            if (c_min > nc_max) ++strict_holds;

            // Informational: 1.275× ratio check (40*crit_min >= 51*noncrit_max).
            // Known to fail due to integer rounding (actual ratio ≈ 1.25 from floor(1.5*0.85)).
            // Tracked separately and reported, but NOT the basis for the assertion.
            if (nc_max > 0 &&
                !(static_cast<int64_t>(40) * c_min >= static_cast<int64_t>(51) * nc_max)) {
                ++ratio_violations;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Test A — Corpus audit
// ---------------------------------------------------------------------------

TEST_CASE("bucket crit-ordering audit: corpus ≥500/class, all violators on allowlist",
          "[bucket][crit_ordering][corpus]")
{
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    constexpr int N_PER_CLASS = 500;
    constexpr uint64_t SEED   = 1;

    const MatchupGen::Class classes[] = {
        MatchupGen::Class::Uniform,
        MatchupGen::Class::BerryHolders,
        MatchupGen::Class::SashSturdy,
    };
    const std::string class_names[] = { "uniform", "berry", "sash" };

    std::vector<Violation> violations;
    std::map<int32_t, int> violator_histogram;  // move_id -> count (weak-dominance failures)
    int moves_checked   = 0;
    int tables_skipped  = 0;
    int strict_holds    = 0;   // informational: fast-path predicate frequency
    int ratio_violations = 0;  // informational: 1.275× check failures (not basis for assertion)

    for (int c = 0; c < 3; ++c) {
        MatchupGen gen(SEED, classes[c], 0, 1, paths);
        for (int i = 0; i < N_PER_CLASS; ++i) {
            BattleState state = gen.next();
            audit_state(state, class_names[c], i, violations, moves_checked, tables_skipped,
                        strict_holds, ratio_violations);
        }
    }

    // Accumulate weak-dominance violator histogram.
    for (const auto& v : violations) {
        violator_histogram[v.move_id]++;
    }

    // --- Informational output: always printed via WARN so it appears unconditionally ---
    WARN("=== Crit-ordering audit: weak-dominance violator histogram ===");
    for (const auto& [mid, cnt] : violator_histogram) {
        bool on_list = (FIXED_DAMAGE_ALLOWLIST.count(mid) > 0);
        WARN("  move_id=" << mid << " count=" << cnt
             << (on_list ? " [allowlist]" : " [*** UNEXPECTED ***]"));
    }
    WARN("moves_checked=" << moves_checked
         << " tables_skipped=" << tables_skipped
         << " weak_dom_violations=" << violations.size()
         << " strict_dom_holds=" << strict_holds
         << " (" << (moves_checked ? 100.0 * strict_holds / moves_checked : 0.0)
         << "% — solver fast-path frequency)"
         << " ratio_1275_violations=" << ratio_violations
         << " (ratio check informational: ~all standard moves fail it;"
            " actual ratio ~1.25 = floor(1.5*0.85), not 1.275)");

    // --- Unexpected violations: those outside the allowlist ---
    bool any_unexpected = false;
    for (const auto& v : violations) {
        if (FIXED_DAMAGE_ALLOWLIST.count(v.move_id) == 0) {
            any_unexpected = true;
            WARN("UNEXPECTED VIOLATION: class=" << v.klass_name
                 << " matchup=" << v.matchup_index
                 << " side=" << v.attacker_side
                 << " move_id=" << v.move_id
                 << " noncrit_max=" << v.noncrit_max
                 << " crit_min=" << v.crit_min);
        }
    }

    // Assert every weak-dominance violator is on the allowlist.
    REQUIRE_FALSE(any_unexpected);

    // Sanity: we must have checked a meaningful number of moves, and the strict
    // fast-path must remain overwhelmingly common (guards against a damage-formula
    // regression silently degrading the solver to the slow path everywhere).
    REQUIRE(moves_checked > 0);
    REQUIRE(strict_holds * 10 >= moves_checked * 9);  // >= 90%
}

// ---------------------------------------------------------------------------
// Test B — Sanity anchor: Tackle on a hand-built state must strictly dominate
// (crit_min > noncrit_max). Also documents the 1.275× ratio finding:
// the ratio check fails (crit/noncrit ≈ 1.25) but strict dominance holds.
// ---------------------------------------------------------------------------

TEST_CASE("bucket crit-ordering sanity: Tackle crit strictly dominates noncrit",
          "[bucket][crit_ordering][sanity]")
{
    static constexpr int32_t MV_TACKLE = 33;
    static constexpr int32_t AB_NONE   = 0;  // no crit suppression, so crit branch exists

    BattleState s{};

    PokemonState attacker{};
    attacker.species   = 1;
    attacker.level     = 50;
    attacker.has_stats = true;
    attacker.stat_hp   = 200; attacker.stat_atk = 100; attacker.stat_def = 80;
    attacker.stat_spa  = 60;  attacker.stat_spd = 60;  attacker.stat_spe = 100;
    attacker.has_max_hp = true; attacker.max_hp = 200;
    attacker.has_hp     = true; attacker.hp     = 200;
    attacker.move_id0   = MV_TACKLE; attacker.move_pp0 = 35;
    attacker.ability    = AB_NONE;
    attacker.item       = 0;
    s.side0.team.push_back(attacker);
    s.side0.active_indices.push_back(0);

    PokemonState defender{};
    defender.species   = 2;
    defender.level     = 50;
    defender.has_stats = true;
    defender.stat_hp   = 200; defender.stat_atk = 60; defender.stat_def = 80;
    defender.stat_spa  = 60;  defender.stat_spd = 60; defender.stat_spe = 60;
    defender.has_max_hp = true; defender.max_hp = 200;
    defender.has_hp     = true; defender.hp     = 200;
    defender.move_id0   = MV_TACKLE; defender.move_pp0 = 35;
    defender.ability    = AB_NONE;
    defender.item       = 0;
    s.side1.team.push_back(defender);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;

    ExecAction action{};
    action.kind      = 0;
    action.move_slot = 0;

    DamageTable tbl = damage_table(s, /*attacker_side=*/0, action);

    REQUIRE_FALSE(tbl.immune);
    REQUIRE_FALSE(tbl.noncrit.empty());
    REQUIRE_FALSE(tbl.crit.empty());

    int32_t nc_max = tbl.noncrit.back();
    int32_t c_min  = tbl.crit.front();

    INFO("Tackle noncrit range: [" << tbl.noncrit.front() << ", " << nc_max << "]");
    INFO("Tackle crit   range: [" << c_min << ", " << tbl.crit.back() << "]");
    INFO("Actual ratio c_min/nc_max = " << (double)c_min / nc_max
         << " (expected ~1.25 from floor(1.5 * 0.85); 1.275x ratio check fails by design)");

    // Strict dominance holds for Tackle: crit_min > noncrit_max.
    // This is the property the solver requires (no interleaving of ranges).
    REQUIRE(c_min > nc_max);

    // Document the 1.275× ratio finding: CHECK (not REQUIRE) so it records without
    // failing the test. The ratio is ~1.25 due to integer truncation, not a bug.
    // The solver only needs strict dominance, not the 1.275× ratio.
    bool ratio_ok = (static_cast<int64_t>(40) * c_min >= static_cast<int64_t>(51) * nc_max);
    INFO("1.275x ratio check (40*c_min >= 51*nc_max): " << (ratio_ok ? "PASS" : "FAIL — expected, see comment"));
    // Not asserting ratio_ok here — documented finding: ratio is ~1.25, not 1.275.
}
