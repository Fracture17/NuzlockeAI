// Random 1v1 BattleState generator for audit and benchmark harnesses.
// Loads liveplay/data/generated_learnsets.json + generated_abilities.json at construction.
// Produces a deterministic, shardable stream: shard k/of n yields indices ≡ k (mod n).
// Generation RNG is IDENTICAL regardless of shard args (generate-then-filter).
// Level: fixed at 50. All moves drawn from species learnset; abilities from generated table.
#pragma once
#ifndef NUZLOCKE_SOLVER_MATCHUP_GEN_H
#define NUZLOCKE_SOLVER_MATCHUP_GEN_H

#include "state.h"

#include <cstdint>
#include <random>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class MatchupGen {
public:
    // Generation class: controls item selection constraints.
    // PLAYER side (side0): item is NONE with 30% probability in EVERY class, else the
    // class item below. USER decision: the wave-0 analytic only certifies item-free
    // players, and the prototype's calibration generator gave each side 30% NONE —
    // without this weighting, analytic audits structurally decide nothing.
    // OPPONENT side (side1): always the class item (mirrors battle_gen.py opponent logic).
    enum class Class {
        Uniform,       // any item from GENERAL_ITEMS
        BerryHolders,  // stress berry (Sitrus/Custap/pinch)
        SashSturdy,    // Focus Sash, Focus Band, or Sturdy ability
    };

    // Paths to the two JSON data files.
    struct Paths {
        std::string learnsets_path;
        std::string abilities_path;
    };

    // Construct and load data files. Throws std::runtime_error if files are missing or malformed.
    // shard_k: this shard's index (0-based). shard_of: total shard count.
    // next() yields only states at global indices ≡ shard_k (mod shard_of).
    MatchupGen(uint64_t seed, Class klass, int shard_k, int shard_of, const Paths& paths);

    // Advance to and return the next state for this shard.
    BattleState next();

    // True iff the given species has the given move_id in its learnset. Used by tests.
    bool learnset_contains(int32_t species_id, int32_t move_id) const;

private:
    std::mt19937_64 rng_;
    Class           klass_;
    int             shard_k_;
    int             shard_of_;
    uint64_t        global_index_; // next state index to generate (unsharded counter)

    // species_id → {move_ids in learnset}
    std::unordered_map<int32_t, std::unordered_set<int32_t>> learnsets_;
    // species_id → move_ids as vector (for sampling)
    std::unordered_map<int32_t, std::vector<int32_t>> learnset_vec_;
    // species_id → {normal ability ids}
    std::unordered_map<int32_t, std::vector<int32_t>> normal_abilities_;
    // species_id → {normal + hidden ability ids}
    std::unordered_map<int32_t, std::vector<int32_t>> all_abilities_;
    // corpus pool: sorted vector of species_ids eligible for generation
    std::vector<int32_t> species_pool_;

    // Generate one BattleState without shard filtering (increments global_index_).
    BattleState generate_one();
    // Generate one side's single PokemonState.
    // is_player: apply the player-side 30% item-free override (see Class comment).
    PokemonState generate_mon(int32_t species_id, bool is_player);
    // Sample an item for the given class and species_id.
    int32_t sample_item(int32_t species_id);
};

#endif // NUZLOCKE_SOLVER_MATCHUP_GEN_H
