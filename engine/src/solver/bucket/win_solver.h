// Solver B — bucket_win_certify: sound WIN pruner over the Expand transition (spec §6,
// plan Task 7). Tri-valued DFS: WIN is a proof (holds for every bucket member); FAIL is
// "not proven WIN" (includes concessions), never a LOSS certificate; INDETERMINATE marks
// depth/visit-cap exhaustion. On-stack repeated bucket = FAIL (amendment 16(a)). DFS runs
// on a dedicated 256 MB pthread; any exception is captured and rethrown on the caller.
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_WIN_SOLVER_H
#define NUZLOCKE_SOLVER_BUCKET_WIN_SOLVER_H

#include "move_exec.h"                   // ExecAction
#include "solver/bucket/bucket.h"
#include "solver/bucket/expand.h"        // ExpandResult, ExpandContext
#include "solver/question.h"
#include "state.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <unordered_map>

// Certification verdict. FAIL is NOT a LOSS certificate (it folds in concessions and
// on-stack repeats); the pipeline treats FAIL and INDETERMINATE alike as UNKNOWN.
enum class BucketWinVerdict { WIN, FAIL, INDETERMINATE };

// Why an INDETERMINATE verdict was returned. Records the FIRST cap hit.
enum class BucketWinIndetReason { None, DepthCap, VisitCap };

// Bucket identity for on-stack repeat detection + policy map (amendment 16(a): d plus
// both HP intervals; support_fp is derived from d and excluded).
struct BucketKey {
    uint32_t d;
    int32_t  pl_lo, pl_hi, op_lo, op_hi;
    bool operator==(const BucketKey& o) const {
        return d == o.d && pl_lo == o.pl_lo && pl_hi == o.pl_hi
            && op_lo == o.op_lo && op_hi == o.op_hi;
    }
};

struct BucketKeyHash {
    std::size_t operator()(const BucketKey& k) const;
};

// Test-only expand seam. When null, bucket_win_certify calls the real expand().
using ExpandFn = std::function<ExpandResult(const Bucket&, const ExecAction&, ExpandContext&)>;

struct BucketWinConfig {
    int      depth_cap  = 500;
    uint64_t visit_cap  = 1'000'000;
    std::size_t stack_size = 256ull * 1024 * 1024;
    ExpandFn expand_override;   // TEST ONLY — bypasses real expand()
};

struct BucketWinStats {
    uint64_t buckets_visited   = 0;
    uint64_t terminal_buckets  = 0;
    uint64_t expand_calls      = 0;
    uint64_t replays           = 0;
    uint64_t oracle_leaves     = 0;
    uint64_t conceded_branches = 0;
    int      max_depth         = 0;
    uint64_t elapsed_us        = 0;
};

struct BucketWinResult {
    BucketWinVerdict     verdict = BucketWinVerdict::FAIL;
    BucketWinIndetReason reason  = BucketWinIndetReason::None;
    // Winning action per WIN-decided bucket (keyed by BucketKey identity).
    std::unordered_map<BucketKey, ExecAction, BucketKeyHash> policy;
    // Per-tag-bit concession counts accumulated on FAILing (conceded) branches.
    std::array<uint64_t, 32> concession_histogram{};
    BucketWinStats stats;
};

// Certify whether the player has a guaranteed (probability-1, outcome-adaptive) win from
// initial_state under q. Self-contained: allocates oracle / ContextInterner /
// BreakpointRegistry internally and wires ctx.concede = concede_tags. Terminal roots are
// decided by classify() before any thread spawn (WIN→WIN, LOSS→FAIL).
BucketWinResult bucket_win_certify(const BattleState& initial_state, const Question& q,
                                   const BucketWinConfig& cfg = {});

#endif // NUZLOCKE_SOLVER_BUCKET_WIN_SOLVER_H
