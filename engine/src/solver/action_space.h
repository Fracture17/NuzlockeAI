// Player action-space enumeration for the 1v1 solver.
// Wraps cpp_enumerate_legal_actions and appends mega variants per matching mega stone.
#pragma once
#ifndef NUZLOCKE_SOLVER_ACTION_SPACE_H
#define NUZLOCKE_SOLVER_ACTION_SPACE_H

#include "move_exec.h"
#include "state.h"
#include <vector>

// All legal actions for the player (side 0) this turn.
// Includes base moves (with Struggle fallback when all PP are 0) plus one mega variant
// per base move when the active holds a matching mega stone and mega has not been used
// this battle. Mega+Struggle is never generated (mirrors liveplay/actions.py:187-191).
// Throws std::runtime_error if side 0 does not have exactly one alive active.
std::vector<ExecAction> legal_player_actions(const BattleState& state);

#endif // NUZLOCKE_SOLVER_ACTION_SPACE_H
