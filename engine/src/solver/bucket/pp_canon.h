// PP canonicalization for the bucket solver (PP-canon Tasks 1+2).
//
// Representative canonicalization: masked slots' PP is rewritten to a sentinel BEFORE a
// state is interned, so the interned context `d` is itself canonical (no companion keys;
// BucketKey/EdgeKey/memo/stack/lowlink machinery is untouched). Masked = every move that is
// NOT pure self-healing. The rewrite preserves each slot's {0, >0} profile, which is the
// ONLY thing the engine reads for legality and AI scoring:
//   - legality pp<=0 checks (incl. Choice lock, Struggle's all-zero trigger)
//   - every AI-scorer PP read is `== 0` (ai_scorer.cpp:149; ai_scorer_internal.h:316/331/
//     346/369; ai_scorer_dist.cpp:228/471/517/786; ai_damage.cpp:442)
//
// Sites that read EXACT PP and are DELIBERATELY accepted as divergences (a later
// certificate-PP audit keeps WINs sound):
//   - cpp_check_leppa_berry: fires only at pp == 0; masked slots never reach 0 in canonical
//     space, so a Leppa holder's masked slots simply never trigger the berry there.
//   - Pressure double-consumption: affects the PP DECREMENT rate only, not the {0,>0}
//     profile a single expansion reads.
//
// Trump Card / Spite / Grudge / Eerie Spell (moves whose effect scales with or drains exact
// PP) are ABSENT from this engine; if ever ported, this classification MUST be revisited.
//
// turns_in_battle clamp (fully behavior-preserving, no audit dependency, no accuracy loss):
// every engine read of PokemonState::turns_in_battle is a threshold check with threshold < 5,
// so any value >= 5 is behaviorally identical to 5. All read sites, verified against the
// engine source:
//   - state.h:72 (declaration)
//   - residuals.cpp:366 (> 0)
//   - move_exec.cpp:320, orchestrate.cpp:214, effects.cpp:654 (reset to 0 on switch-in)
//   - turn.cpp:443 (== 0)
//   - move_exec_guards.cpp:523 (> 0)
//   - core_leaf.cpp:681, damage.cpp:1081 (< 5, Slow Start)
//   - ai_scorer_dist.cpp:49/59/582/594 (== 0 / != 0 / > 0)
//   - effects.cpp:726 (== 0)
// canonicalize_pp() clamps to min(turns_in_battle, 5) alongside the PP rewrite, both sides,
// bench included, idempotent -- collapsing the otherwise-unbounded per-turn counter that would
// keep interned contexts diverging turn-over-turn even with PP masked.
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_PP_CANON_H
#define NUZLOCKE_SOLVER_BUCKET_PP_CANON_H

#include "state.h"

#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <vector>

// Out-of-band non-zero PP sentinel: >= 3 and above any real move's max PP.
constexpr int32_t kPpSentinel = 99;

// True iff move_id is a pure self-healing move able to sustain a heal-stall loop (Recover
// family, Rest, Wish, Swallow, Strength Sap, Life Dew — every self-target heal the engine
// implements). Drain moves are EXCLUDED (they recover HP only by dealing damage). These
// moves keep REAL PP through canonicalization so finite heal loops stay depth/horizon-bounded.
//
// Misclassification here is never unsound, only imprecise: a mislabeled masked heal move
// surfaces as a canonical on-stack repeat (FAIL) or is caught by the certificate-PP audit;
// a mislabeled cycle-capable non-heal move merely keeps real PP (no canonical collapse).
// Keep the list conservative and simple.
bool is_cycle_capable_move(int32_t move_id);

// Rewrite every masked slot's PP to the {0,>0}-preserving representative, for every mon on
// both sides (bench included). Idempotent. No Leppa exception — Leppa holders are masked
// like any other mon. Also clamps turns_in_battle to min(value, 5) for every mon on both
// sides (see turns_in_battle clamp note above); also idempotent.
void canonicalize_pp(BattleState& s);

// Sum of REAL nonzero PP across all move slots on both sides plus +8 slack. Call on the
// REAL (pre-canonicalization) state; used as an insurance depth cap in canonical space.
int32_t pp_horizon(const BattleState& s);

// ---------------------------------------------------------------------------
// Certificate PP-use audit (PP-canon Task 3).
//
// A canonical WIN may over-use a masked slot beyond its REAL PP: the turn cap bounds the
// certificate's LENGTH, not per-slot use. After a WIN is proven, the winning certificate
// (a DAG) is audited: the MAX path-wise consumption of every masked slot must stay strictly
// below that slot's real root PP (never reaching 0 — the post-exhaustion {0,>0} profile flip
// changes AI support/legality/Leppa). See pp_cert_audit_soundness. Cycle-capable slots keep
// real PP in canonical space and are exempt.
//
// The DP below runs over a struct-based certificate DAG (win_solver builds it from policy +
// edge cache). Consumption is path-wise: a node's per-slot value = own action cost + per-slot
// MAX over its children (RNG/adversarial AND-children are alternatives — the realized line
// takes one path, so children contribute a MAX, not a sum).
// ---------------------------------------------------------------------------

// One move slot to audit: side (0=player, 1=opponent), team index, move slot 0..3.
struct PpSlotKey {
    int32_t side;
    int32_t mon;
    int32_t slot;
    bool operator==(const PpSlotKey& o) const {
        return side == o.side && mon == o.mon && slot == o.slot;
    }
};

struct PpSlotKeyHash {
    std::size_t operator()(const PpSlotKey& k) const;
};

// Max consumption per slot over the certificate.
using PpConsumption = std::unordered_map<PpSlotKey, int32_t, PpSlotKeyHash>;

// One AND-child of a certificate node: the opponent's action consumption on that branch plus
// the child subtree. child < 0 marks a terminal-WIN leaf (no further node).
struct PpCertEdge {
    PpSlotKey opp_slot;
    int32_t   opp_cost;   // 0 (switch/struggle/recharge), 1, or 2 (opposing Pressure)
    int       child = -1; // index into PpCertGraph::nodes, or < 0 for a terminal leaf
};

// One non-terminal WIN bucket: the player's action consumption plus its AND-children.
struct PpCertNode {
    PpSlotKey               player_slot;
    int32_t                 player_cost = 0;  // 0, 1, or 2 (opposing Pressure)
    std::vector<PpCertEdge> children;
};

// Certificate DAG. Diamonds share a node index; nodes are stored children-before-parent, so
// root is normally the last-appended node (win_solver sets it explicitly).
struct PpCertGraph {
    std::vector<PpCertNode> nodes;
    int root = 0;
};

// Max path-wise consumption per slot over the DAG rooted at graph.root. Memoizes per node
// (DAG diamonds are visited once). THROWS std::logic_error on a cycle (an impossible-if-sound
// WIN certificate — fail loud). Returns empty for an empty graph.
PpConsumption pp_max_consumption(const PpCertGraph& graph);

// Real root PP + move id for one audited slot, snapshotted from the REAL pre-canon state.
struct PpRootSlot {
    int32_t real_pp;
    int32_t move_id;
};
using PpRootPp = std::unordered_map<PpSlotKey, PpRootSlot, PpSlotKeyHash>;

// True iff every masked (non-cycle-capable) slot's consumption is STRICTLY below its real root
// PP (for slots with real PP > 0). Cycle-capable slots are exempt (real PP kept in canonical
// space). THROWS std::logic_error if a consumed slot is absent from the root snapshot.
bool pp_cert_audit_ok(const PpConsumption& consumption, const PpRootPp& root_pp);

#endif // NUZLOCKE_SOLVER_BUCKET_PP_CANON_H
