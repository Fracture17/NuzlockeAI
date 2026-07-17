// TransitionCache — question-independent (bucket, action) -> ExpandResult edge cache for
// the bucket DAG search (plan Task 1). Owns the oracle + ContextInterner the cached
// ExpandResults were produced against, so cached child ctx_ids stay meaningful.
//
// NOT thread-safe. No size cap. Entries are valid ONLY for buckets whose ctx_ids came
// from THIS cache's interner (a cached child's d indexes this interner's contexts).
// bp_fp scopes entries per BpSet: a differing breakpoint set is a different key. A cache
// populated via a test expand_override must NEVER be reused for real runs — the cached
// ExpandResults are fabricated, not real expansions.
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_TRANSITION_CACHE_H
#define NUZLOCKE_SOLVER_BUCKET_TRANSITION_CACHE_H

#include "move_exec.h"                    // ExecAction
#include "solver/bucket/breakpoints.h"    // BpSet
#include "solver/bucket/expand.h"         // ExpandResult
#include "solver/bucket/win_solver.h"     // BucketKey, BucketKeyHash
#include "solver/state_codec.h"           // ContextInterner
#include "solver/transition_oracle.h"     // TransitionOracle

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>

// FNV-1a over player_bps, opp_bps (each preceded by its length as a separator), then
// player_max_hp, opp_max_hp. Distinguishes a player/opp vector swap and any perturbation.
uint64_t bp_fingerprint(const BpSet& bp);

// Cache key: bucket identity + breakpoint-set fingerprint + every discriminating
// ExecAction field. Two edges collide iff they name the same expansion input.
struct EdgeKey {
    BucketKey bucket;
    uint64_t  bp_fp;
    int32_t   kind;
    int32_t   move_slot;
    int32_t   move_override;
    int32_t   switch_to_slot;
    int32_t   target_side;
    int32_t   target_slot;
    int32_t   source_slot;
    bool      mega;

    bool operator==(const EdgeKey& o) const {
        return bucket == o.bucket && bp_fp == o.bp_fp && kind == o.kind
            && move_slot == o.move_slot && move_override == o.move_override
            && switch_to_slot == o.switch_to_slot && target_side == o.target_side
            && target_slot == o.target_slot && source_slot == o.source_slot
            && mega == o.mega;
    }
};

struct EdgeKeyHash {
    std::size_t operator()(const EdgeKey& k) const;
};

struct TransitionCacheStats {
    uint64_t hits   = 0;
    uint64_t misses = 0;
};

class TransitionCache {
public:
    // PP-canon mode tag (Task 2). Exact and Canonical entries are keyed by interner
    // context ids from incompatible interning regimes and MUST never share a cache.
    enum class Mode { Unset, Exact, Canonical };

    TransitionOracle oracle;
    ContextInterner  interner;
    TransitionCacheStats stats;

    // Bind this cache to one canonicalization regime. First call sets it; a later call
    // under the OTHER mode THROWS std::logic_error (mirrors edge_cache_owns_interner:
    // canonical and exact contexts can never coexist in one interner/cache).
    void require_mode(Mode m);
    Mode mode() const { return mode_; }

    // Return the cached ExpandResult for key, or null on miss. Counts hit/miss.
    const ExpandResult* lookup(const EdgeKey& key);

    // Insert result under key. THROWS std::logic_error on a duplicate key.
    void insert(const EdgeKey& key, ExpandResult result);

    std::size_t entries() const { return edges_.size(); }

private:
    std::unordered_map<EdgeKey, ExpandResult, EdgeKeyHash> edges_;
    Mode mode_ = Mode::Unset;
};

#endif // NUZLOCKE_SOLVER_BUCKET_TRANSITION_CACHE_H
