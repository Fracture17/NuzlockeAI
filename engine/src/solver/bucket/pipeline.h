// Bucket-solver pipeline (plan Task 10, amendment 18): pessimal LOSS-pruner → Solver B
// WIN-certifier. LOSS is reported only from the sound pessimal stage; pessimal WIN and
// INDETERMINATE are identical (never evidence) and route to B. B WIN → WIN; B FAIL or
// INDETERMINATE → UNKNOWN. Exceptions from either stage PROPAGATE (never swallowed).
// TEST-ONLY seams inject stage verdicts to unit-test the lattice without real search.
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_PIPELINE_H
#define NUZLOCKE_SOLVER_BUCKET_PIPELINE_H

#include "solver/bsolver.h"
#include "solver/bucket/win_solver.h"
#include "solver/question.h"
#include "state.h"

#include <array>
#include <cstdint>
#include <functional>

// Composed pipeline verdict. LOSS is sound (pessimal); WIN is sound (Solver B);
// UNKNOWN is the dispute set (pessimal-survived ∧ B-not-certified) — Solver C's queue.
enum class PipelineVerdict { WIN, LOSS, UNKNOWN };

// TEST-ONLY stage seams. Null in production (real bsolver_certify / bucket_win_certify).
// The pessimal seam receives the mode-forced config; the B seam the win config.
using PessimalFn = std::function<BsolverResult(const BattleState&, const Question&,
                                               const BsolverConfig&)>;
using BWinFn     = std::function<BucketWinResult(const BattleState&, const Question&,
                                                 const BucketWinConfig&)>;

struct PipelineConfig {
    BsolverConfig   pessimal_cfg;   // mode is FORCED to Pessimal internally
    BucketWinConfig win_cfg;
    PessimalFn      pessimal_override;  // TEST ONLY — bypasses bsolver_certify
    BWinFn          bwin_override;      // TEST ONLY — bypasses bucket_win_certify
};

struct PipelineResult {
    PipelineVerdict verdict = PipelineVerdict::UNKNOWN;

    // Pessimal stage (always runs).
    BVerdict             pessimal_verdict = BVerdict::INDETERMINATE;
    BIndeterminateReason pessimal_reason  = BIndeterminateReason::None;

    // Solver B stage (runs iff pessimal is not LOSS).
    bool                 b_ran     = false;
    BucketWinVerdict     b_verdict = BucketWinVerdict::FAIL;
    BucketWinIndetReason b_reason  = BucketWinIndetReason::None;
    std::array<uint64_t, 32> concession_histogram{};  // pass-through from B
    BucketWinStats           b_stats;

    // Per-stage wall time (microseconds).
    uint64_t pessimal_us = 0;
    uint64_t b_us        = 0;
};

// Run the composed pipeline from initial_state under q. See file-header for the lattice.
PipelineResult run_pipeline(const BattleState& initial_state, const Question& q,
                            const PipelineConfig& cfg = {});

#endif // NUZLOCKE_SOLVER_BUCKET_PIPELINE_H
