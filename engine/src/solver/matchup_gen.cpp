// MatchupGen: deterministic, shardable stream of random-but-legal 1v1 BattleStates.
// Level is fixed at 50 (competitive standard, avoids level-scaling concerns for the solver).
// Both sides use corpus_species_pool rules: all learnset moves eligible, normal+hidden abilities.
// RNG stream is seeded once; shard k/of n filters by index ≡ k (mod n) without splitting RNG.
#include "solver/matchup_gen.h"

#include <enum_names.h>  // generated: SPECIES/MOVE/ABILITY_NAME_TABLE (gen_cpp_data.py)
#include "species_data.h"       // SPECIES_TABLE for base stats
#include "stats.h"              // compute_stat

#include <nlohmann/json.hpp>

#include <algorithm>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

static constexpr int    GEN_LEVEL    = 50;
static constexpr int    GEN_IV       = 31;
static constexpr int32_t NATURE_HARDY = 0;  // neutral nature (no stat changes)

// GenderEnum int values (mirrors liveplay/state/pokemon.py)
static constexpr int32_t GENDER_MALE       = 0;
static constexpr int32_t GENDER_FEMALE     = 1;
static constexpr int32_t GENDER_GENDERLESS = 2;

// Quick Draw ability id (core_leaf.cpp:77)
static constexpr int32_t ABILITY_QUICK_DRAW = 259;
// Sturdy ability id (liveplay/data/abilities.py)
static constexpr int32_t ABILITY_STURDY     = 5;

// Item ids for SashSturdy class
static constexpr int32_t ITEM_FOCUS_SASH = 275;
static constexpr int32_t ITEM_FOCUS_BAND = 230;
static constexpr int32_t ITEM_NONE       = 0;

// Corpus banned species names (mirrors battle_gen.py CORPUS_BANNED_SPECIES)
static const std::unordered_set<std::string> CORPUS_BANNED = { "GOLISOPOD", "WIMPOD" };

// ---------------------------------------------------------------------------
// Stress-berry item pool for BerryHolders class.
// Includes: Sitrus, Custap, stat-pinch berries, confusion-pinch berries.
// Source: liveplay/data/items.py + battle_gen.py GENERAL_ITEMS comments.
// ---------------------------------------------------------------------------
static const int32_t STRESS_BERRIES[] = {
    158,  // SITRUS_BERRY
    210,  // CUSTAP_BERRY
    201, 202, 203, 204, 205, 206, 207,  // LIECHI, GANLON, SALAC, PETAYA, APICOT, LANSAT, STARF
    159, 160, 161, 162, 163,            // FIGY, WIKI, MAGO, AGUAV, IAPAPA
};
static const int STRESS_BERRIES_COUNT =
    static_cast<int>(sizeof(STRESS_BERRIES) / sizeof(STRESS_BERRIES[0]));

// SashSturdy item pool: Focus Sash and Focus Band.
static const int32_t SASH_STURDY_ITEMS[] = { ITEM_FOCUS_SASH, ITEM_FOCUS_BAND };
static const int SASH_STURDY_ITEM_COUNT = 2;

// General item pool (mirrors GENERAL_ITEMS from liveplay/battle_gen.py; validated at Python import).
// 122 items — no ITEM_NONE entry. Item-free PLAYER mons come from the explicit 30%
// override in generate_mon (see matchup_gen.h Class comment); opponents always hold one.
static const int32_t GENERAL_ITEMS[] = {
    158, 157, 155, 149, 150, 151, 152, 153, 154, 156,     // Status-curing / HP berries
    159, 160, 161, 162, 163,                               // Confusion/pinch berries
    201, 202, 203, 204, 205, 206, 207, 210,               // Stat-pinch berries
    687, 688,                                             // Kee, Maranga
    184, 185, 186, 187, 188, 189, 190, 191, 192, 193,    // Type-resist berries (Occa-Payapa)
    194, 195, 196, 197, 198, 199, 200, 686,               // Tanga-Roseli
    564,                                                  // NORMAL_GEM
    4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008,      // Gems (fire-flying)
    4009, 4010, 4011, 4012, 4013, 4014, 4015, 4016, 4017,// Gems (psychic-fairy)
    234, 270, 275, 230, 220, 297, 287,                    // Leftovers, Life Orb, Focus Sash/Band, Choice items
    640, 538, 281, 540,                                   // Assault Vest, Eviolite, Black Sludge, Rocky Helmet
    217, 265, 232, 268, 266, 267,                         // Quick Claw, Wide Lens, Scope Lens, Expert Belt, Muscle Band, Wise Glasses
    221, 326, 327,                                        // King's Rock, Razor Claw, Razor Fang
    213, 279, 278, 541,                                   // Bright Powder, Lagging Tail, Iron Ball, Air Balloon
    214, 271,                                             // White Herb, Power Herb
    296,                                                  // Big Root
    269, 285, 284, 283, 282,                              // Light Clay, Damp Rock, Heat Rock, Smooth Rock, Icy Rock
    277, 272, 273, 288,                                   // Metronome, Toxic Orb, Flame Orb, Sticky Barb
    542, 547,                                             // Red Card, Eject Button
    650, 880,                                             // Safety Goggles, Protective Pads
    1118, 846, 1121, 639,                                 // Throat Spray, Adrenaline Orb, Blunder Policy, Weakness Policy
    249, 243, 239, 242, 248, 246, 241, 240, 244, 245,    // Type-boost items (Charcoal-Poison Barb)
    237, 238, 251, 222, 247, 250, 233,                   // Soft Sand-Metal Coat
};
static const int GENERAL_ITEMS_COUNT =
    static_cast<int>(sizeof(GENERAL_ITEMS) / sizeof(GENERAL_ITEMS[0]));

// ---------------------------------------------------------------------------
// Binary search helpers over sorted NameIdEntry tables
// ---------------------------------------------------------------------------

static int32_t lookup_name(const NameIdEntry* table, int count, const std::string& name) {
    int lo = 0, hi = count;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        int cmp = std::strcmp(table[mid].name, name.c_str());
        if (cmp < 0)      lo = mid + 1;
        else if (cmp > 0) hi = mid;
        else              return table[mid].id;
    }
    return -1;  // not found
}

// ---------------------------------------------------------------------------
// Species base-stat lookup by species_id (binary search on SPECIES_TABLE)
// ---------------------------------------------------------------------------

static const SpeciesData* find_species_data(int32_t species_id) {
    int lo = 0, hi = 1220;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (SPECIES_TABLE[mid].species_id < species_id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= 1220 || SPECIES_TABLE[lo].species_id != species_id) return nullptr;
    return &SPECIES_TABLE[lo];
}

// ---------------------------------------------------------------------------
// JSON loading helpers
// ---------------------------------------------------------------------------

static nlohmann::json load_json_file(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open())
        throw std::runtime_error("MatchupGen: cannot open file: " + path);
    std::string content((std::istreambuf_iterator<char>(f)),
                         std::istreambuf_iterator<char>());
    try {
        return nlohmann::json::parse(content);
    } catch (const std::exception& e) {
        throw std::runtime_error("MatchupGen: JSON parse error in " + path + ": " + e.what());
    }
}

// ---------------------------------------------------------------------------
// MatchupGen construction
// ---------------------------------------------------------------------------

MatchupGen::MatchupGen(uint64_t seed, Class klass, int shard_k, int shard_of,
                       const Paths& paths)
    : rng_(seed), klass_(klass), shard_k_(shard_k), shard_of_(shard_of), global_index_(0)
{
    if (shard_of <= 0)
        throw std::runtime_error("MatchupGen: shard_of must be > 0");
    if (shard_k < 0 || shard_k >= shard_of)
        throw std::runtime_error("MatchupGen: shard_k must be in [0, shard_of)");

    nlohmann::json learnsets_json = load_json_file(paths.learnsets_path);
    nlohmann::json abilities_json = load_json_file(paths.abilities_path);

    if (!learnsets_json.is_object())
        throw std::runtime_error("MatchupGen: learnsets JSON must be an object");
    if (!abilities_json.is_object())
        throw std::runtime_error("MatchupGen: abilities JSON must be an object");

    // Build per-species learnset and ability maps; collect corpus pool.
    for (auto it = learnsets_json.begin(); it != learnsets_json.end(); ++it) {
        const std::string& sname = it.key();

        // Skip corpus-banned species
        if (CORPUS_BANNED.count(sname)) continue;

        // Resolve species_id from name table
        int32_t sp_id = lookup_name(SPECIES_NAME_TABLE, SPECIES_NAME_COUNT, sname);
        if (sp_id < 0) continue;  // unknown to C++ engine

        // Require at least one normal ability (mirrors generatable_species())
        auto abl_it = abilities_json.find(sname);
        if (abl_it == abilities_json.end()) continue;
        const auto& abl_entry = *abl_it;
        if (!abl_entry.is_object()) continue;

        auto normal_it = abl_entry.find("normal");
        if (normal_it == abl_entry.end() || !normal_it->is_array() || normal_it->empty())
            continue;

        // Build normal ability list
        std::vector<int32_t> normal_abls, all_abls;
        for (const auto& ab_name : *normal_it) {
            if (!ab_name.is_string()) continue;
            int32_t ab_id = lookup_name(ABILITY_NAME_TABLE, ABILITY_NAME_COUNT,
                                        ab_name.get<std::string>());
            if (ab_id < 0) continue;
            if (ab_id == ABILITY_QUICK_DRAW) continue;  // blocklist
            normal_abls.push_back(ab_id);
            all_abls.push_back(ab_id);
        }
        if (normal_abls.empty()) continue;  // no usable ability

        auto hidden_it = abl_entry.find("hidden");
        if (hidden_it != abl_entry.end() && hidden_it->is_array()) {
            for (const auto& ab_name : *hidden_it) {
                if (!ab_name.is_string()) continue;
                int32_t ab_id = lookup_name(ABILITY_NAME_TABLE, ABILITY_NAME_COUNT,
                                            ab_name.get<std::string>());
                if (ab_id < 0) continue;
                if (ab_id == ABILITY_QUICK_DRAW) continue;  // blocklist
                all_abls.push_back(ab_id);
            }
        }

        // Build learnset move list
        std::unordered_set<int32_t> move_set;
        std::vector<int32_t> move_vec;
        const auto& moves_obj = it.value();
        if (!moves_obj.is_object()) continue;
        for (auto mit = moves_obj.begin(); mit != moves_obj.end(); ++mit) {
            int32_t mv_id = lookup_name(MOVE_NAME_TABLE, MOVE_NAME_COUNT, mit.key());
            if (mv_id <= 0) continue;  // unknown move or NONE (id=0)
            move_set.insert(mv_id);
            move_vec.push_back(mv_id);
        }
        if (move_vec.empty()) continue;

        learnsets_[sp_id]       = std::move(move_set);
        learnset_vec_[sp_id]    = std::move(move_vec);
        normal_abilities_[sp_id] = std::move(normal_abls);
        all_abilities_[sp_id]    = std::move(all_abls);
        species_pool_.push_back(sp_id);
    }

    if (species_pool_.empty())
        throw std::runtime_error("MatchupGen: empty species pool after filtering");

    std::sort(species_pool_.begin(), species_pool_.end());
}

// ---------------------------------------------------------------------------
// Item sampling
// ---------------------------------------------------------------------------

int32_t MatchupGen::sample_item(int32_t species_id) {
    // SashSturdy: always one of Focus Sash / Focus Band (Sturdy comes from ability selection)
    if (klass_ == Class::SashSturdy) {
        return SASH_STURDY_ITEMS[rng_() % SASH_STURDY_ITEM_COUNT];
    }
    // BerryHolders: always a stress berry
    if (klass_ == Class::BerryHolders) {
        return STRESS_BERRIES[rng_() % STRESS_BERRIES_COUNT];
    }
    // Uniform: pick from GENERAL_ITEMS (no NONE — both sides hold an item, matching opponent logic)
    return GENERAL_ITEMS[rng_() % GENERAL_ITEMS_COUNT];
}

// ---------------------------------------------------------------------------
// Mon generation
// ---------------------------------------------------------------------------

PokemonState MatchupGen::generate_mon(int32_t species_id, bool is_player) {
    const SpeciesData* sd = find_species_data(species_id);
    if (!sd)
        throw std::runtime_error("MatchupGen: no SpeciesData for id " +
                                 std::to_string(species_id));

    const std::vector<int32_t>& moves = learnset_vec_.at(species_id);
    const std::vector<int32_t>& abls  = all_abilities_.at(species_id);

    // Sample up to 4 distinct moves. Guarantee at least one move (pool non-empty by construction).
    // Simple uniform sampling without replacement (no weighting — pure random per spec).
    std::vector<int32_t> pool = moves;
    std::vector<int32_t> chosen;
    chosen.reserve(4);
    while (chosen.size() < 4 && !pool.empty()) {
        int idx = static_cast<int>(rng_() % pool.size());
        chosen.push_back(pool[idx]);
        pool.erase(pool.begin() + idx);
    }
    while (chosen.size() < 4) chosen.push_back(0);  // NONE

    // Sample ability
    int32_t ability_id = abls[rng_() % abls.size()];

    // For SashSturdy: if Sturdy is available, 50% chance to use Sturdy (ability) instead of item.
    // This is handled post-item-sample: if item is Focus Sash/Band and Sturdy is available,
    // flip to Sturdy+any-item with 50% probability.
    // Actually: simpler — sample item first, then conditionally override with Sturdy ability.
    int32_t item_id = sample_item(species_id);

    // SashSturdy ability override: if the species has Sturdy and we haven't already forced Sturdy,
    // give each mon a 1/3 chance of Sturdy (vs Focus Sash vs Focus Band).
    if (klass_ == Class::SashSturdy) {
        // Check if Sturdy is available for this species
        bool has_sturdy = false;
        for (int32_t a : all_abilities_.at(species_id)) {
            if (a == ABILITY_STURDY) { has_sturdy = true; break; }
        }
        if (has_sturdy) {
            // Pick uniformly from {Focus Sash + random ability, Focus Band + random ability,
            // any item + Sturdy}. Simpler: 1/3 force Sturdy; 2/3 keep sampled item.
            int choice = static_cast<int>(rng_() % 3);
            if (choice == 2) {
                ability_id = ABILITY_STURDY;
                // item can be anything from general pool
                item_id = GENERAL_ITEMS[rng_() % GENERAL_ITEMS_COUNT];
            }
            // else keep item_id (Sash or Band) and sampled ability
        }
        // species without Sturdy: just use Focus Sash or Focus Band (already sampled)
    }

    // Player-side item-free override (USER decision; see matchup_gen.h Class comment):
    // 30% NONE in every class so wave-0+ analytic audits get in-scope matchups.
    // The draw is unconditional for the player so the RNG stream stays aligned
    // regardless of outcome. Applied AFTER all class item logic (a SashSturdy mon
    // that kept Sturdy via the override above remains a valid stress mon item-free).
    if (is_player && (rng_() % 100) < 30)
        item_id = ITEM_NONE;

    // Sample nature (uniform, Hardy=neutral is index 0)
    int32_t nature_id = static_cast<int32_t>(rng_() % 25);

    // Sample gender
    int32_t gender;
    float male_ratio = sd->male_ratio;
    if (male_ratio < 0.0f) {
        gender = GENDER_GENDERLESS;
    } else {
        // Generate a value in [0, 1) using upper 32 bits of rng for uniformity
        double r = static_cast<double>(rng_() >> 32) / 4294967296.0;
        gender = (r < male_ratio) ? GENDER_MALE : GENDER_FEMALE;
    }

    // Compute stats (IVs all 31, no EVs)
    int32_t stat_hp  = compute_stat(0, sd->base_hp,  GEN_IV, nature_id, GEN_LEVEL);
    int32_t stat_atk = compute_stat(1, sd->base_atk, GEN_IV, nature_id, GEN_LEVEL);
    int32_t stat_def = compute_stat(2, sd->base_def, GEN_IV, nature_id, GEN_LEVEL);
    int32_t stat_spa = compute_stat(3, sd->base_spa, GEN_IV, nature_id, GEN_LEVEL);
    int32_t stat_spd = compute_stat(4, sd->base_spd, GEN_IV, nature_id, GEN_LEVEL);
    int32_t stat_spe = compute_stat(5, sd->base_spe, GEN_IV, nature_id, GEN_LEVEL);

    PokemonState mon{};
    mon.species   = species_id;
    mon.nature    = nature_id;
    mon.iv_hp = mon.iv_atk = mon.iv_def = mon.iv_spa = mon.iv_spd = mon.iv_spe = GEN_IV;
    mon.gender    = gender;
    mon.level     = GEN_LEVEL;
    mon.ability   = ability_id;
    mon.base_ability = ability_id;
    mon.item      = item_id;
    mon.move_id0  = chosen[0]; mon.move_id1 = chosen[1];
    mon.move_id2  = chosen[2]; mon.move_id3 = chosen[3];
    // PP not set here — engine uses base PP from move table (not stored in solver states).
    // Set PP to a large sentinel (40) so legal_player_actions always has moves available.
    mon.move_pp0 = (chosen[0] != 0) ? 40 : 0;
    mon.move_pp1 = (chosen[1] != 0) ? 40 : 0;
    mon.move_pp2 = (chosen[2] != 0) ? 40 : 0;
    mon.move_pp3 = (chosen[3] != 0) ? 40 : 0;
    mon.has_stats  = true;
    mon.stat_hp  = stat_hp; mon.stat_atk = stat_atk; mon.stat_def = stat_def;
    mon.stat_spa = stat_spa; mon.stat_spd = stat_spd; mon.stat_spe = stat_spe;
    mon.has_max_hp = true; mon.max_hp = stat_hp;
    mon.has_hp     = true; mon.hp     = stat_hp;

    return mon;
}

// ---------------------------------------------------------------------------
// State generation
// ---------------------------------------------------------------------------

BattleState MatchupGen::generate_one() {
    const int pool_size = static_cast<int>(species_pool_.size());

    // Sample two distinct species (player then opponent)
    int idx0 = static_cast<int>(rng_() % pool_size);
    int idx1 = static_cast<int>(rng_() % (pool_size - 1));
    if (idx1 >= idx0) ++idx1;  // skip idx0
    int32_t sp0 = species_pool_[idx0];
    int32_t sp1 = species_pool_[idx1];

    PokemonState mon0 = generate_mon(sp0, /*is_player=*/true);
    PokemonState mon1 = generate_mon(sp1, /*is_player=*/false);

    BattleState s{};
    s.side0.team.push_back(mon0);
    s.side0.active_indices.push_back(0);
    s.side1.team.push_back(mon1);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    s.is_trainer_battle = true;

    ++global_index_;
    return s;
}

BattleState MatchupGen::next() {
    // Generate-then-filter: advance through the global stream until we hit an index
    // ≡ shard_k_ (mod shard_of_). RNG stream is identical regardless of shard args.
    while (true) {
        // global_index_ is the index of the NEXT state to generate
        uint64_t idx = global_index_;
        BattleState s = generate_one();  // increments global_index_
        if (shard_of_ == 1 || static_cast<int>(idx % shard_of_) == shard_k_)
            return s;
        // Discard and continue
    }
}

// ---------------------------------------------------------------------------
// learnset_contains (used by tests)
// ---------------------------------------------------------------------------

bool MatchupGen::learnset_contains(int32_t species_id, int32_t move_id) const {
    auto it = learnsets_.find(species_id);
    if (it == learnsets_.end()) return false;
    return it->second.count(move_id) > 0;
}
