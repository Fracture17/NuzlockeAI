// ContextInterner implementation for PackedKey codec.
#include "solver/state_codec.h"
#include "state_eq.h"

#include <stdexcept>

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

// Return the active PokemonState index in the team for a side that has exactly
// one active. Throws std::invalid_argument if active_indices.size() != 1.
static int get_sole_active_idx(const SideState& side, const char* side_name) {
    if (side.active_indices.size() != 1) {
        throw std::invalid_argument(
            std::string("state_codec: ") + side_name +
            " must have exactly 1 active for 1v1 solver");
    }
    return side.active_indices[0];
}

// ---------------------------------------------------------------------------
// ContextInterner::mask_hp
// ---------------------------------------------------------------------------

BattleState ContextInterner::mask_hp(const BattleState& state) {
    // Validate active counts before masking; errors surface here, not silently.
    int pl_idx  = get_sole_active_idx(state.side0, "side0");
    int opp_idx = get_sole_active_idx(state.side1, "side1");

    BattleState masked = state;
    masked.side0.team[pl_idx].hp  = 0;
    masked.side1.team[opp_idx].hp = 0;
    return masked;
}

// ---------------------------------------------------------------------------
// ContextInterner::pack
// ---------------------------------------------------------------------------

PackedKey ContextInterner::pack(const BattleState& state) {
    // Validate 1v1 assumption and read active HPs before masking.
    int pl_idx  = get_sole_active_idx(state.side0, "side0");
    int opp_idx = get_sole_active_idx(state.side1, "side1");

    int32_t raw_pl_hp  = state.side0.team[pl_idx].hp;
    int32_t raw_opp_hp = state.side1.team[opp_idx].hp;

    if (raw_pl_hp  > 0xFFFF || raw_pl_hp  < 0)
        throw std::overflow_error("state_codec: player active HP does not fit 16 bits");
    if (raw_opp_hp > 0xFFFF || raw_opp_hp < 0)
        throw std::overflow_error("state_codec: opponent active HP does not fit 16 bits");

    const auto pl_hp  = static_cast<uint16_t>(raw_pl_hp);
    const auto opp_hp = static_cast<uint16_t>(raw_opp_hp);

    // Build masked context and look up or intern it.
    BattleState masked = mask_hp(state);
    const std::size_t h = state_hash_solver(masked);

    auto& bucket = buckets_[h];
    for (uint32_t id : bucket.ids) {
        if (state_equal_solver(exemplars_[id], masked)) {
            return make_packed_key(id, pl_hp, opp_hp);
        }
    }

    // New context: assign next id.
    if (exemplars_.size() >= static_cast<std::size_t>(UINT32_MAX))
        throw std::overflow_error("state_codec: context id overflow (> 2^32 contexts)");

    const auto new_id = static_cast<uint32_t>(exemplars_.size());
    exemplars_.push_back(masked);
    bucket.ids.push_back(new_id);
    return make_packed_key(new_id, pl_hp, opp_hp);
}

// ---------------------------------------------------------------------------
// ContextInterner::unpack
// ---------------------------------------------------------------------------

BattleState ContextInterner::unpack(PackedKey key) const {
    const uint32_t id      = ctx_id_of(key);
    const uint16_t pl_hp   = pl_hp_of(key);
    const uint16_t opp_hp  = opp_hp_of(key);

    if (id >= exemplars_.size())
        throw std::out_of_range("state_codec: ctx_id out of range in unpack");

    BattleState result = exemplars_[id];
    // Restore HP values into the active slots (1v1: exactly one active each side).
    int pl_idx  = get_sole_active_idx(result.side0, "side0");
    int opp_idx = get_sole_active_idx(result.side1, "side1");
    result.side0.team[pl_idx].hp  = static_cast<int32_t>(pl_hp);
    result.side1.team[opp_idx].hp = static_cast<int32_t>(opp_hp);
    return result;
}
