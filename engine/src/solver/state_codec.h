// Packed state key for solver memoization. Splits a BattleState into a context
// (everything except both actives' HP) and the two HP values. Enables compact memo
// tables and HP-segment math in phase 4.
#pragma once
#ifndef NUZLOCKE_SOLVER_STATE_CODEC_H
#define NUZLOCKE_SOLVER_STATE_CODEC_H

#include "state.h"

#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <vector>

// 64-bit key: [ctx_id (32 bits)] | [player active HP (16 bits)] | [opp active HP (16 bits)]
using PackedKey = uint64_t;

// Extract fields from a PackedKey.
inline uint32_t ctx_id_of(PackedKey k)   { return static_cast<uint32_t>(k >> 32); }
inline uint16_t pl_hp_of(PackedKey k)    { return static_cast<uint16_t>((k >> 16) & 0xFFFF); }
inline uint16_t opp_hp_of(PackedKey k)   { return static_cast<uint16_t>(k & 0xFFFF); }

// Assemble a key from its three components.
inline PackedKey make_packed_key(uint32_t ctx_id, uint16_t pl_hp, uint16_t opp_hp) {
    return (static_cast<uint64_t>(ctx_id) << 32)
         | (static_cast<uint64_t>(pl_hp)  << 16)
         |  static_cast<uint64_t>(opp_hp);
}

// Interner for battle-state contexts. Each unique context (state with both actives'
// HP masked to zero) gets a stable 32-bit id. Stores full masked-exemplar BattleStates
// so unpack() can re-materialize the exact original state. Not thread-safe by design;
// use one instance per solve.
class ContextInterner {
public:
    // Encode a BattleState into a PackedKey. Throws if:
    //   - either side has != 1 active (std::invalid_argument)
    //   - either active's HP exceeds 16 bits (std::overflow_error)
    //   - context count would exceed 2^32 (std::overflow_error)
    PackedKey pack(const BattleState& state);

    // Decode a PackedKey back into a BattleState with exact HP values restored.
    BattleState unpack(PackedKey key) const;

    // Number of distinct contexts interned so far.
    std::size_t context_count() const { return exemplars_.size(); }

private:
    // Mask both actives' HP to 0, returning the canonical context state.
    // Isolated here as the phase-4 extension lever for interval certification.
    static BattleState mask_hp(const BattleState& state);

    // Map from context hash → index into exemplars_ (for collision-safe lookup).
    // Uses state_hash_solver as key; collisions resolved by linear scan of bucket.
    struct ContextBucket {
        std::vector<uint32_t> ids;  // exemplars_ indices in this hash bucket
    };

    std::unordered_map<std::size_t, ContextBucket> buckets_;
    std::vector<BattleState> exemplars_;  // masked exemplar per context id
};

#endif // NUZLOCKE_SOLVER_STATE_CODEC_H
