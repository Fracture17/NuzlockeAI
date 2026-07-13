// classify() and action_filter() implementation for the solver Question type.
#include "solver/question.h"

#include <stdexcept>

// Terminal condition: mirrors cpp_battle_over / cpp_compute_winner in orchestrate.h.
// In 1v1, the battle is over when either side's active is fainted (hp==0 / fainted==true).
// We check active_indices[0] on each side; an empty active_indices means no active = fainted side.
static bool side_active_fainted(const SideState& side) {
    if (side.active_indices.size() != 1) {
        throw std::invalid_argument("classify: expected exactly 1 active per side (1v1 only)");
    }
    const PokemonState& active = side.team[side.active_indices[0]];
    return active.fainted || active.hp <= 0;
}

Outcome classify(const BattleState& state, const Question& q) {
    bool player_fainted = side_active_fainted(state.side0);
    bool opp_fainted    = side_active_fainted(state.side1);

    bool terminal = player_fainted || opp_fainted;
    if (!terminal) {
        return Outcome::CONTINUE;
    }

    // At terminal: WIN iff every asserted condition holds.
    if (q.requireOppFaint && !opp_fainted)    return Outcome::LOSS;
    if (q.requireNoFaint  && player_fainted)  return Outcome::LOSS;

    if (q.keepItem > 0) {
        // Positive terminal-state assertion: the player's item at terminal must equal
        // keepItem. A Harvest-restored berry counts as kept (it carries into the next
        // fight); Knock Off/Trick/consumption without restoration fails it.
        const PokemonState& player = state.side0.team[state.side0.active_indices[0]];
        if (player.item != q.keepItem) return Outcome::LOSS;
    }

    if (q.keepHp > 0) {
        const PokemonState& player = state.side0.team[state.side0.active_indices[0]];
        if (player.hp < q.keepHp) return Outcome::LOSS;
    }

    return Outcome::WIN;
}

bool action_filter(const Question& q, const ExecAction& action) {
    // Struggle sentinel (move_slot == -2) is always permitted.
    if (action.move_slot == -2) return true;
    if (q.banMove < 0) return true;
    return action.move_slot != q.banMove;
}
