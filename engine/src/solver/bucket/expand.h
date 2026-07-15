// Expand(bucket A, player_move) → AND-set of child buckets (spec §4 / plan Task 5).
// Ordering: derived input splits first, endpoint-paired replay verification, support-
// equality gate, shift assertion (image width == input width), image splits at BpSet
// with per-child d'. Any mismatch throws ExpandError (never auto-bisect). Fast path
// gated on strict crit dominance; general path preserves crit-class provenance during
// merge. Concede-seam and options are pluggable for Task 6 / test coverage.
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_EXPAND_H
#define NUZLOCKE_SOLVER_BUCKET_EXPAND_H

#include "ai_analytic.h"                 // ActionProb
#include "move_exec.h"                   // ExecAction
#include "solver/bucket/bucket.h"
#include "solver/bucket/breakpoints.h"
#include "solver/engine_queries.h"       // DamageTable
#include "solver/oracle_types.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "state.h"

#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Errors + options
// ---------------------------------------------------------------------------

// Fail-loud error carrying a stage for downstream throw census (Task 10 rcheck).
struct ExpandError : std::runtime_error {
    enum class Stage {
        Precondition,
        WeakDominanceViolation,
        UnsupportedMove,          // §5.2 HP-dependent moves
        SupportFlip,
        ReplayDivergence,
        ShiftViolation,
        InternMismatch,
        DerivedSplitOverflow,
        ImageSplit                // invalid child produced during image splitting
    };
    Stage stage;
    ExpandError(Stage st, const std::string& msg);
};

// Test-only seams; all default false in production.
struct ExpandOptions {
    bool force_general_path       = false;  // bypass strict-dominance fast path
    bool skip_hp_dependent_screen = false;  // reach the shift/replay backstop
    bool skip_derived_splits      = false;  // prove gate/image-split backstops fire
};

// Day-one telemetry aggregated across one Expand call (Task 7 collects these).
struct ExpandStats {
    uint64_t leaves                 = 0;
    uint64_t replays                = 0;
    uint64_t sub_rects              = 0;
    uint64_t derived_split_points   = 0;
    uint64_t image_splits           = 0;
    uint64_t children_before_merge  = 0;
    uint64_t children_after_merge   = 0;
    bool     fast_path              = false;  // strict crit dominance held for every table
};

// Concede seam (§4 step 2). Task 6 fills; Task 5 accepts null = never concede.
// Returns nonzero tag id to concede the whole (bucket, player_move) branch.
using ConcedeFn = std::function<uint32_t(const BattleState& lo_corner,
                                         const BattleState& hi_corner,
                                         const ExecAction& player_move)>;

// One AND-child produced by Expand. ai_action is provenance/diagnostics.
struct ChildBucket {
    Bucket     bucket;
    ExecAction ai_action;
};

struct ExpandResult {
    uint32_t                 concession_tag = 0;  // nonzero => branch conceded; empty children
    std::vector<ChildBucket> children;
    ExpandStats              stats;
};

struct ExpandContext {
    const TransitionOracle* oracle;
    ContextInterner*        interner;   // mutable — child contexts get interned
    const BpSet*            bp;
    ConcedeFn               concede;    // may be null
    ExpandOptions           options;
};

// Expand a bucket under one player action. See file-header comment for pipeline.
// Throws ExpandError on any gate/precondition violation.
ExpandResult expand(const Bucket& A, const ExecAction& player_move, ExpandContext& ctx);

// ---------------------------------------------------------------------------
// Pure helpers (unit-tested directly)
// ---------------------------------------------------------------------------

// Canonical support fingerprint: order-independent hash of the p>0 action set
// (kind, move_slot, target fields; probabilities excluded). Same function root-bucket
// builders and downstream users MUST use.
uint64_t support_fingerprint(const std::vector<ActionProb>& probs);

// Strict crit dominance: min(crit values) > max(noncrit values). Enables the
// fast merge path where crit/noncrit children can coalesce freely.
bool strict_crit_dominance(const DamageTable& t);

// Weak crit dominance: min(crit values) >= max(noncrit values). Required for any
// expand call — failure is a hard throw (spec §3 / Part 1 amendment 5).
bool weak_crit_dominance(const DamageTable& t);

// All achievable partial-sum deltas for 1..max_hits hits over t's distinct damage
// values (union of noncrit and crit classes), by iterative set convolution.
// Throws ExpandError{DerivedSplitOverflow} once the cumulative set exceeds a size cap.
std::vector<int32_t> cumulative_attack_deltas(const DamageTable& t);

// Deterministic residual/consumable HP-delta candidates for one side, mirroring
// engine arithmetic (burn/poison/toxic-by-counter, Leftovers, consumable heal amounts).
// Always includes 0. Best-effort superset — a missed source degrades to an image split
// or gate throw, never to unsoundness.
std::vector<int32_t> residual_delta_candidates(const BattleState& state, int side);

// Split points x strictly inside (lo, hi) with x = b + delta for some b in breakpoints
// and delta in deltas. Result is sorted and deduped.
std::vector<int32_t> derived_split_points(const std::vector<int32_t>& breakpoints,
                                          const std::vector<int32_t>& deltas,
                                          int32_t lo, int32_t hi);

#endif // NUZLOCKE_SOLVER_BUCKET_EXPAND_H
