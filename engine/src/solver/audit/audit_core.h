// Linkable audit logic shared between the audit_oracle executable and the Catch2 test suite.
// Exports audit_selfcheck() and audit_mc() as free functions on config structs so tests can
// call them directly without spawning a subprocess.
#pragma once
#ifndef NUZLOCKE_SOLVER_AUDIT_CORE_H
#define NUZLOCKE_SOLVER_AUDIT_CORE_H

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

// Bitmask reasons for selfcheck failures. Stored as an enum for readable histogram keys.
enum class AuditFailReason : int {
    MassError         = 0,  // bit 0: Σp ≠ 1 ± 1e-9
    OrderingMismatch  = 1,  // bit 1: Natural ≠ AdverseFirst multiset
    ChildSanity       = 2,  // bit 2: HP out of [0,max] or active-count wrong
    OracleThrewException = 3, // bit 3: oracle threw an exception
};

// Description of one selfcheck failure (printed for regression fixture capture).
struct SelfcheckFailure {
    uint64_t seed;
    int      matchup_index;
    // Action serialized as a readable string for display.
    std::string action_desc;
    int      reason_mask;   // OR of (1 << AuditFailReason) bits
    std::string detail;     // human-readable detail line
};

// Configuration for audit_selfcheck().
struct AuditSelfcheckConfig {
    uint64_t    seed      = 1;
    std::string klass     = "uniform";   // "uniform", "berry", "sash"
    int         n         = 10;
    int         shard_k   = 0;
    int         shard_of  = 1;
    std::string repo_root;               // path to repo root (for data files)
};

// Result of audit_selfcheck().
struct AuditSelfcheckReport {
    int total_failures = 0;
    int skipped_budget = 0;  // (matchup, action) pairs skipped because budget was exceeded
    std::unordered_map<AuditFailReason, int> reason_histogram;
    std::vector<SelfcheckFailure> failures;  // every failure, for regression capture
};

// Run selfcheck over N matchups × all legal player actions. For each (matchup, action):
//   - Call step() twice (Natural, AdverseFirst).
//   - Check: Σp = 1 ± 1e-9 (MassError); multisets equal (OrderingMismatch);
//     every child HP in [0, max_hp] and exactly one active per side (ChildSanity).
//   - On oracle throw: mark OracleThrewException, continue.
// Returns a report with failure counts and all failure details.
AuditSelfcheckReport audit_selfcheck(const AuditSelfcheckConfig& cfg);

// ============================================================================
// MC (Monte Carlo) audit
// ============================================================================

// Description of one MC completeness hole (sampled child not in enumerated support).
struct McCompletenessHole {
    uint64_t    seed;
    int         matchup_index;
    std::string action_desc;
    int         sample_index;
    std::string detail;  // diagnostic: what child was sampled
};

// Description of one statistical failure (chi-squared or 5-sigma binomial per child).
struct McStatFailure {
    uint64_t    seed;
    int         matchup_index;
    std::string action_desc;
    uint64_t    packed_key;
    double      expected_prob;
    double      observed_freq;
    double      z_score;        // |observed - expected| / sigma (binomial test)
    std::string detail;
};

// Configuration for audit_mc().
struct AuditMcConfig {
    uint64_t    seed    = 1;
    std::string klass   = "uniform";
    int         n       = 3;
    int         samples = 2000;
    std::string repo_root;

    // Statistical test: per-child 5-sigma binomial check with expected-count floor.
    // Children with expected count < floor are skipped (too rare to test reliably).
    double stat_sigma_threshold   = 5.0;
    double expected_count_floor   = 5.0;
};

// Result of audit_mc().
struct AuditMcReport {
    int completeness_failures = 0;  // HARD FAIL: sampled child not in enumerated support
    int stat_failures         = 0;  // chi-squared / 5-sigma failures
    int skipped_budget        = 0;  // matchups skipped: support enumeration exceeded leaf budget
    std::vector<McCompletenessHole> holes;
    std::vector<McStatFailure>      stat_fails;
};

// Run MC audit over N matchups × first legal player action (iterating all is expensive).
// For each (matchup, action):
//   - Enumerate oracle support into a PackedKey→prob map.
//   - Draw M random-mode samples (both actions pinned explicitly, per-sample deterministic seed).
//   - Completeness: if sampled child not in support → record hole (HARD FAIL class).
//   - Statistics: per-child binomial 5-sigma test (expected count ≥ floor).
AuditMcReport audit_mc(const AuditMcConfig& cfg);

#endif // NUZLOCKE_SOLVER_AUDIT_CORE_H
