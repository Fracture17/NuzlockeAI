// Shared type definitions for the transition oracle seam. Header-only.
#pragma once
#ifndef NUZLOCKE_SOLVER_ORACLE_TYPES_H
#define NUZLOCKE_SOLVER_ORACLE_TYPES_H

#include "move_exec.h"  // ExecAction
#include "state.h"      // BattleState

#include <cstdint>
#include <functional>
#include <stdexcept>
#include <vector>

// One child state produced by the oracle, with its probability weight.
struct ChildOutcome {
    BattleState child;
    double prob;
};

// Emit callback type: receives one ChildOutcome per oracle leaf.
// Returns false to abort enumeration early; true to continue.
using OracleEmitFn = std::function<bool(ChildOutcome)>;

// Ordering hint for the DFS traversal: Natural visits outcomes in default order;
// AdverseFirst visits opponent-favoring outcomes first (min player HP, max opp HP, etc.).
// Must not change the emitted multiset — only the visitation order.
enum class OrderingHint {
    Natural      = 0,
    AdverseFirst = 1,
};

// Per-call statistics returned by step().
struct StepStats {
    uint64_t leaves            = 0;
    uint64_t turn_executions   = 0;
    bool     aborted           = false;
    bool     budget_exceeded   = false;
};

// ---------------------------------------------------------------------------
// Per-leaf debug path: one entry per DFS prefix step leading to a leaf.
// Used by solver_trace to reconstruct the full event path. Null debug callback
// in Config means zero overhead on the hot path (single nullptr check per leaf).
// ---------------------------------------------------------------------------

// Channel tag matching the internal PrefixEntry channel.
enum class LeafChannel : int {
    CatB = 0,
    CatA = 1,
};

// One branch step in the DFS path to a leaf. Mirrors the internal PrefixEntry structure
// but is the public-facing type for debug callbacks, solver_trace, and replay_path.
struct LeafPathEntry {
    LeafChannel channel;
    int         event;       // RngEventC integer value
    int         occurrence;  // occurrence index (Cat-B only; 0 for Cat-A)
    int         value;       // forced outcome (bool→0/1, int, Cat-A option)
    double      prob;        // probability of this branch choice
    int         value2 = -1; // second pick for MOODY_STATS pair; -1 = not a pair event

    // DAMAGE_ROLL group structure: populated in the observed_sequence returned by replay_path.
    // has_dmg_by_roll=1 iff dmg_by_roll[] is valid (requires the log annotation to be present).
    // dmg_by_roll[i] = final damage value for roll_index i (0..15).
    // Used by the bucket solver to compare damage groups across interval endpoints.
    uint8_t  has_dmg_by_roll   = 0;
    int32_t  dmg_by_roll[16]   = {};
};

// Debug metadata emitted alongside each leaf (only when debug_emit is non-null in Config).
struct LeafDebugInfo {
    std::vector<LeafPathEntry> path;  // full DFS prefix leading to this leaf
    double                     cumulative_prob;  // product of all prefix probs × p(ai)
    // AI (opponent) action that generated this leaf's outer DFS branch, and its probability.
    // Allows consumers to group leaves by opponent move without re-running the AI scorer.
    ExecAction                 ai_action;
    double                     ai_action_prob = 0.0;
};

// Debug callback: called immediately before the normal emit() for each leaf.
// Returning false from the normal emit() still aborts; the debug callback does not control flow.
using LeafDebugFn = std::function<void(const LeafDebugInfo&)>;

// ---------------------------------------------------------------------------
// replay_path result: child state + observed branch-point sequence.
// The observed sequence mirrors the forced prefix that was supplied; it can be
// compared across interval endpoints by the bucket solver to detect shift-property
// violations (mismatched sequences → missing breakpoint → throw in Expand).
// ---------------------------------------------------------------------------

struct ReplayResult {
    BattleState                child;             // state after one forced turn
    std::vector<LeafPathEntry> observed_sequence; // branch points encountered, in order
};

// Engine queries (damage tables and HP-threshold sets) have moved to
// solver/engine_queries.h — the real implementation replacing these stubs.

#endif // NUZLOCKE_SOLVER_ORACLE_TYPES_H
