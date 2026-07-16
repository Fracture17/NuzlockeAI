// rcheck referee core (plan Task 10): runs the bucket pipeline over a MatchupGen corpus
// and classifies each matchup against the exact bsolver referee. Mirrors the
// audit_analytic_core injected-seam contract (injected matchups + pipeline/exact fns,
// mutually exclusive with the generator). Emits one JSONL record per matchup plus a
// shard-completeness summary line; the pure classifier + census-key helper are unit-tested.
#pragma once
#ifndef NUZLOCKE_SOLVER_AUDIT_RCHECK_CORE_H
#define NUZLOCKE_SOLVER_AUDIT_RCHECK_CORE_H

#include "solver/bsolver.h"
#include "solver/bucket/pipeline.h"
#include "solver/question.h"
#include "state.h"

#include <array>
#include <cstdint>
#include <exception>
#include <functional>
#include <ostream>
#include <string>
#include <unordered_map>
#include <vector>

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

// Nine mutually-exclusive bins. THROWN takes precedence over any exact verdict;
// REFEREE_INDET absorbs a non-thrown matchup whose exact referee is INDETERMINATE
// (excluded from soundness, still counted). The two HARD_FAIL bins are soundness
// violations (must be zero). CONSERVATIVE_* are refinement signals (Solver C queue).
enum class RcheckClass {
    THROWN = 0,
    REFEREE_INDET,
    SOUND_AGREE_WIN,
    SOUND_AGREE_LOSS,
    HARD_FAIL_B_WIN,          // pipeline WIN  × exact LOSS
    HARD_FAIL_PESSIMAL_LOSS,  // pipeline LOSS × exact WIN
    SOUND_UNKNOWN_ON_LOSS,    // pipeline UNKNOWN × exact LOSS (sound)
    CONSERVATIVE_TAGGED,      // pipeline UNKNOWN, concessions≠0 × exact WIN
    CONSERVATIVE_UNTAGGED,    // pipeline UNKNOWN, concessions==0 × exact WIN
    COUNT
};

const char* rcheck_class_name(RcheckClass c);

// Whether a class is a hard soundness failure.
bool rcheck_is_hard_fail(RcheckClass c);

// Everything the classifier needs from one pipeline execution.
struct PipelineOutcome {
    PipelineVerdict      verdict         = PipelineVerdict::UNKNOWN;  // ignored if thrown
    bool                 thrown          = false;
    std::string          throw_key;      // census key (only meaningful if thrown)
    std::string          throw_what;     // full what() (only meaningful if thrown)
    uint32_t             concession_mask = 0;  // OR of B concession bits (tagged vs untagged)
    BucketWinIndetReason b_reason        = BucketWinIndetReason::None;
};

// Pure classifier: (pipeline outcome × exact referee verdict) → bin. See enum comment.
RcheckClass classify_rcheck(const PipelineOutcome& po, BVerdict exact);

// Map an exception to a throw-census key: ExpandError → "expand:<StageName>";
// runtime_error whose what() contains residual_unknown / form-change / ai-final-gambit /
// ai-bench → that key; otherwise "other:<first 60 chars of what()>".
std::string throw_census_key(const std::exception& e);

// ---------------------------------------------------------------------------
// Shard run loop
// ---------------------------------------------------------------------------

// Seam: run the pipeline for one matchup. Null → real run_pipeline with the built config.
using RcheckPipelineFn = std::function<PipelineResult(const BattleState&, const Question&)>;
// Seam: run the exact referee for one matchup. Null → real bsolver_certify (Exact).
using RcheckExactFn = std::function<BsolverResult(const BattleState&, const Question&)>;

struct RcheckConfig {
    uint64_t    seed     = 1;
    std::string klass    = "uniform";   // uniform / berry / sash
    int         n        = 100;         // per-shard matchup count (MatchupGen::next() calls)
    int         shard_k  = 0;
    int         shard_of = 1;
    std::string repo_root;

    // Budgets (mirroring ccheck defaults; CLI overrides them for calibration/full runs).
    uint64_t exact_leaves = 5'000;
    uint64_t exact_nodes  = 1'000;
    uint64_t pess_leaves  = 5'000;
    uint64_t pess_nodes   = 1'000;
    int      b_depth      = 500;
    uint64_t b_visits     = 1'000'000;

    // Corpus-level A/B determinism switch. False disables both the B-solver edge cache
    // and verdict memo (CLI --no-cache); leaves cache ownership untouched (always local).
    bool     enable_cache = true;

    // Injected matchups + seams (tests / pipeline coverage). Non-empty injected → the
    // generator is NOT used. injected non-empty AND repo_root non-empty → throws.
    std::vector<BattleState> injected;
    RcheckPipelineFn         pipeline_fn;  // null → real run_pipeline
    RcheckExactFn            exact_fn;      // null → real exact bsolver
};

// Aggregate counters returned for assertions; the authoritative record is the JSONL stream.
struct RcheckReport {
    int                                  n = 0;         // matchups actually processed
    std::array<int, (int)RcheckClass::COUNT> bins{};    // per-class counts
    int                                  hard_fails = 0;
    std::unordered_map<std::string, int> throw_census;
    std::array<uint64_t, 32>             concession_histogram{};
};

// Run the shard: for each matchup, execute the pipeline (catch → THROWN), execute the
// exact referee, classify, write one JSONL record to out. Writes a final summary JSONL
// line (shard-completeness marker) and prints hard-fails live to stdout. Returns the report.
RcheckReport rcheck_run(const RcheckConfig& cfg, std::ostream& out);

#endif // NUZLOCKE_SOLVER_AUDIT_RCHECK_CORE_H
