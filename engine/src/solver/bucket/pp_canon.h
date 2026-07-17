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

#include <cstdint>

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

#endif // NUZLOCKE_SOLVER_BUCKET_PP_CANON_H
