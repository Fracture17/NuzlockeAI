// Player action-space enumeration for the 1v1 solver.
#include "solver/action_space.h"

#include "orchestrate.h"
#include "turn.h"

#include <stdexcept>

std::vector<ExecAction> legal_player_actions(const BattleState& state) {
    const SideState& side0 = state.side0;

    if (side0.active_indices.size() != 1)
        throw std::runtime_error("legal_player_actions: side 0 must have exactly one active");
    int active_idx = side0.active_indices[0];
    const PokemonState& active = side0.team[active_idx];
    if (active.hp <= 0)
        throw std::runtime_error("legal_player_actions: side 0 active is fainted");

    std::vector<ExecAction> actions = cpp_enumerate_legal_actions(state, /*side_idx=*/0, /*slot=*/0);

    // Append mega variants iff:
    //   - held item maps to a mega entry whose pre_species matches active.species
    //   - active is not already mega-evolved
    //   - side has not used mega this battle
    // Struggle (move_slot == -2) is excluded: Python appends it after the mega block.
    const MegaEntry* entry = cpp_find_mega_entry(active.item);
    bool can_mega = entry != nullptr
                    && entry->pre_species == active.species
                    && !active.is_mega
                    && !side0.mega_used;

    if (can_mega) {
        // Collect base move actions first; size is stable during iteration since we extend after.
        std::size_t base_count = actions.size();
        for (std::size_t i = 0; i < base_count; ++i) {
            // Struggle (move_slot == -2) never gets a mega variant.
            if (actions[i].move_slot == -2) continue;
            ExecAction mega_variant = actions[i];
            mega_variant.mega = true;
            actions.push_back(mega_variant);
        }
    }

    return actions;
}
