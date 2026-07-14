// Reusable analytic-audit and trace-printer logic. Thin main()s in audit_analytic.cpp
// and analytic_trace.cpp wrap these; Catch2 smoke tests call them directly.
// audit_analytic_run() runs the tiered verification pipeline; analytic_trace_run() prints
// a single-matchup trace. analytic_mask_scan() sweeps opp HP and reports support crossings.
#pragma once
#ifndef NUZLOCKE_SOLVER_AUDIT_ANALYTIC_CORE_H
#define NUZLOCKE_SOLVER_AUDIT_ANALYTIC_CORE_H

#include "solver/analytic/analytic.h"
#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

// Certifier function type: same signature as analytic_certify. Tests inject fake
// certifiers to exercise specific pipeline paths. Empty = use analytic_certify.
using CertifierFn = std::function<AnalyticResult(const BattleState&, const Question&)>;

// ---------------------------------------------------------------------------
// Analytic Audit
// ---------------------------------------------------------------------------

// Mode controls which matchups are scanned and what verification runs.
enum class AnalyticAuditMode {
    All,     // scan exactly N matchups
    Collect, // keep scanning until N DECIDED analytic verdicts (or scan cap)
    Fast,    // analytic only (no bsolver) — for latency measurement
};

struct AnalyticAuditConfig {
    uint64_t    seed      = 1;
    std::string klass     = "uniform";    // "uniform", "berry", "sash"
    int         n         = 10;           // matchups (all/fast) or decided verdicts (collect)
    AnalyticAuditMode mode = AnalyticAuditMode::All;
    int         shard_k   = 0;
    int         shard_of  = 1;
    std::string repo_root;

    // bsolver budgets (small defaults for smoke tests; callers override for real runs).
    uint64_t oracle_max_leaves = 5'000;
    uint64_t node_cap          = 1'000;
    // collect-mode scan cap: max total scans = collect_scan_cap_mult * n
    int collect_scan_cap_mult  = 200;

    // Injected matchups (tests / pipeline coverage). Non-empty → generator is NOT used.
    // Contradictory: injected non-empty AND repo_root non-empty → throws.
    std::vector<BattleState> injected;

    // Certifier seam. Empty → real analytic_certify. Tests inject fake certifiers to
    // prove soundness-failure detection works without needing real wrong verdicts.
    CertifierFn certifier;
};

// One soundness failure record (printed FIRST for LOSS-vs-WIN failures).
struct AnalyticSoundnessFailure {
    uint64_t    seed;
    std::string klass;
    int         index;       // global matchup index
    std::string av_verdict;  // "WIN" or "LOSS"
    std::string bv_verdict;  // "WIN" or "LOSS"
    int         tag;         // ATag value
    uint32_t    scope_mask;
    bool        tight;
    bool        loss_vs_exact_win;  // true = LOSS mismatch (print first)
};

struct AnalyticAuditReport {
    // Counters.
    int scanned           = 0;
    int decided           = 0;   // WIN + LOSS
    int n_analytic_win    = 0;
    int n_analytic_loss   = 0;
    int n_unknown         = 0;
    int pess_confirmed    = 0;   // analytic-LOSS + pessimal-LOSS (no exact needed)
    int exact_skipped     = 0;   // exact returned INDETERMINATE (not a failure)
    int exact_adjudicated = 0;   // exact returned WIN or LOSS
    int exact_wins        = 0;   // exact returned WIN (among adjudicated)
    int soundness_failures = 0;
    std::vector<AnalyticSoundnessFailure> failures;

    // Tag histogram for UNKNOWN matchups (ATag → count).
    std::unordered_map<int, int> unknown_tag_histogram;
    // Scope-reason bitmask histogram (bit index → count, counting every set bit per matchup).
    std::unordered_map<int, int> scope_bit_histogram;
    // Exact scope-mask combination histogram (full mask → count). Wave planning input:
    // a candidate wave clearing bit-set W fully unlocks exactly the matchups whose
    // mask ⊆ W — computable only from exact combinations, not per-bit counts.
    std::unordered_map<uint32_t, int> mask_combo_histogram;

    // Timing (microseconds).
    double analytic_us_total  = 0;
    double pessimal_us_total  = 0;
    double exact_us_total     = 0;

    // Collect-mode: set if the scan cap was hit before reaching N decided.
    bool collect_cap_hit = false;
};

// Run the analytic audit loop. Returns a report; nonzero soundness_failures indicates failure.
AnalyticAuditReport analytic_audit_run(const AnalyticAuditConfig& cfg);

// ---------------------------------------------------------------------------
// Mask scan: sweep opp HP and count AI support-set crossings
// ---------------------------------------------------------------------------

struct MaskScanConfig {
    uint64_t    seed      = 1;
    std::string klass     = "uniform";
    int         n         = 20;          // matchups to sweep
    int         shard_k   = 0;
    int         shard_of  = 1;
    std::string repo_root;
};

// Per-move-slot crossing statistics.
struct MaskScanSlotStats {
    int move_slot     = 0;
    int total_crossings  = 0;  // total support-set transitions for this slot across all matchups
    int multi_crossing_matchups = 0;  // matchups where this slot flipped > once
};

struct MaskScanReport {
    int matchups_scanned   = 0;
    int total_hp_points    = 0;   // total HP values swept across all matchups
    int multi_crossing_actions = 0;  // actions with >1 flip in any matchup
    std::vector<MaskScanSlotStats> slot_stats;
};

// Sweep opp HP from 1..max_hp for each generated matchup, query the AI support set at each HP,
// and count support-set crossings (bit changes) per action across the sweep.
MaskScanReport analytic_mask_scan(const MaskScanConfig& cfg);

// ---------------------------------------------------------------------------
// Analytic trace
// ---------------------------------------------------------------------------

struct AnalyticTraceConfig {
    uint64_t    seed  = 1;
    std::string klass = "uniform";
    int         index = 0;   // matchup index to trace (global, not shard)
    int         action_slot = -1;  // if >= 0, enumerate oracle children for this player action
    std::string repo_root;
};

struct AnalyticTraceOutput {
    std::string text;   // full printout as a string (for test assertions and display)
};

// Generate and print the trace for a single matchup.
AnalyticTraceOutput analytic_trace_run(const AnalyticTraceConfig& cfg);

#endif // NUZLOCKE_SOLVER_AUDIT_ANALYTIC_CORE_H
