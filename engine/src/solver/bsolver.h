// Exact AND-OR boolean certifier: WIN iff P(win, no faint) == 1.
// Semantics: WIN(s) iff some legal filtered action has ALL p>0 oracle children WIN.
// Self-loop children (same PackedKey as parent) are ignored; non-parent ancestors
// on the recursion stack trigger INDETERMINATE(Cycle). Only sees the oracle.
// b_win runs on a dedicated pthread with a 256 MB stack (stack_size in BsolverConfig),
// making depth_cap=500 genuinely safe (256 MB ≈ 2000+ levels at ~100 KB/level).
#pragma once
#ifndef NUZLOCKE_SOLVER_BSOLVER_H
#define NUZLOCKE_SOLVER_BSOLVER_H

#include "solver/oracle_types.h"
#include "solver/question.h"
#include "solver/state_codec.h"
#include "move_exec.h"
#include "state.h"

#include <cstdint>
#include <unordered_map>

enum class BVerdict {
    WIN,
    LOSS,
    INDETERMINATE,
};

// Pessimal/Coarse LOSS is conclusive by the subset-support theorem (subset of p>0 outcomes
// explored; a LOSS within that subset exists in the full tree). WIN is NOT a certificate
// for non-Exact modes — callers must know the mode's meaning. Non-Exact mode policy is
// stored but should not be relied upon as a guaranteed winning strategy.
// Under Pessimal/Coarse, ChildOutcome.prob is NaN by design (fail-loud poison; the oracle
// emits possibility-only children, not a probability distribution). Never read probs in
// non-Exact modes — the bsolver ignores them entirely.
enum class BMode {
    Exact,    // enumerate all p>0 outcomes; WIN and LOSS are certificates.
    Pessimal, // collapse eligible events to single worst outcome; LOSS conclusive, WIN is routing.
    Coarse,   // DAMAGE_ROLL → {min,max} per crit class; all else exact; LOSS conclusive, WIN is routing.
};

enum class BIndeterminateReason {
    None,          // only set when verdict != INDETERMINATE
    LeafBudget,    // oracle step() budget_exceeded
    NodeCap,       // total distinct nodes expanded exceeded node_cap
    DepthCap,      // recursion depth exceeded depth_cap
    Cycle,         // non-parent ancestor found on recursion stack
};

struct BsolverConfig {
    BMode    mode              = BMode::Exact;
    uint64_t oracle_max_leaves = 1'000'000;  // forwarded to oracle Config.max_leaves
    uint64_t node_cap          = 500'000;    // total distinct non-terminal nodes expanded
    int      depth_cap         = 500;        // maximum recursion depth
    size_t   stack_size        = 256ull * 1024 * 1024;  // pthread stack for b_win (256 MB)
};

struct BsolverResult {
    BVerdict             verdict;
    BIndeterminateReason reason;       // set iff verdict == INDETERMINATE
    // Winning action at every decided-WIN node encountered during search.
    std::unordered_map<PackedKey, ExecAction> policy;
    // Diagnostic counters for tests and audit tooling.
    uint64_t nodes_expanded    = 0;    // distinct non-terminal nodes expanded
    uint64_t oracle_step_calls = 0;    // calls to oracle.step()
    uint64_t memo_hits         = 0;    // lookups resolved from memo (no oracle call)
    PackedKey cycle_key        = 0;    // valid iff reason == Cycle: the ancestor key that closed the cycle
};

// Certify whether the player can guarantee a win (per Question q) from state.
// Allocates all per-call state internally (memo, interner, stack); stateless externally.
BsolverResult bsolver_certify(const BattleState& state,
                               const Question& q,
                               const BsolverConfig& cfg);

#endif // NUZLOCKE_SOLVER_BSOLVER_H
