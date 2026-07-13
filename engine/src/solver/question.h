// Question struct and free-function classifier/filter for 1v1 solver certification.
// A Question is a CONJUNCTION of positively-asserted required terminal conditions;
// unasserted fields are unconstrained. classify() and action_filter() operate on const state.
#pragma once
#ifndef NUZLOCKE_SOLVER_QUESTION_H
#define NUZLOCKE_SOLVER_QUESTION_H

#include "state.h"
#include "move_exec.h"

// Classification outcome returned by classify().
enum class Outcome { WIN, LOSS, CONTINUE };

// Certified question: each field is either asserted (non-default value) or unconstrained.
// keepHp is only meaningful when requireNoFaint is true (document: checking HP >= N when
// the player may be fainted is incoherent; callers should not set keepHp with requireNoFaint=false).
struct Question {
    bool    requireOppFaint = true;  // opponent must be fainted at terminal
    bool    requireNoFaint  = true;  // player must NOT be fainted at terminal
    int32_t keepHp          = 0;     // if >0: player HP must be >= keepHp at terminal
    int32_t keepItem        = 0;     // if >0: player item at terminal must equal this item id.
                                     // Positive terminal-state assertion: a Harvest-restored
                                     // berry counts as kept; Knock Off/Trick loss fails it.
    int32_t banMove         = -1;    // move slot player may never use (-1 = no ban)
};

// Classify a state under a Question.
// Terminal = at least one active is fainted (cpp_compute_winner logic: 1v1 battle over).
// At terminal: WIN iff every asserted condition holds; otherwise LOSS.
// Non-terminal: CONTINUE.
// NOTE: keepItem early-fail is intentionally disabled. Harvest (residuals.cpp) can
// restore a consumed berry mid-battle, so the constraint is not monotone. A future
// optimization may early-fail when no restoration path exists (no Harvest, or
// consumed_berry != keepItem).
Outcome classify(const BattleState& state, const Question& q);

// Return true if the action is permitted under the Question's banMove constraint.
// Struggle (move_slot == -2) is always permitted.
bool action_filter(const Question& q, const ExecAction& action);

#endif // NUZLOCKE_SOLVER_QUESTION_H
