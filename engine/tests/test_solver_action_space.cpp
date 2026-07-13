// Catch2 tests for Task 6: legal_player_actions() action-space enumeration.
// Verifies move listing, mega-variant generation, and Struggle fallback.
#include <catch2/catch_test_macros.hpp>

#include "move_exec.h"
#include "solver/action_space.h"
#include "state.h"

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

// Alakazam (species 65) + Alakazite (item 579): a real mega entry in the table.
static constexpr int32_t SPECIES_ALAKAZAM = 65;
static constexpr int32_t ITEM_ALAKAZITE   = 579;

// Build a minimal 1v1 BattleState with the given player species/item/pp values.
static BattleState make_state(int32_t species, int32_t item,
                               int32_t pp0, int32_t pp1,
                               bool mega_used = false,
                               bool is_mega   = false) {
    BattleState s{};

    PokemonState mon{};
    mon.species = species;
    mon.item    = item;
    mon.is_mega = is_mega;
    mon.level   = 50;
    mon.has_stats = true;
    mon.stat_hp = 200; mon.stat_atk = 100; mon.stat_def = 80;
    mon.stat_spa = 80; mon.stat_spd = 80; mon.stat_spe = 80;
    mon.has_max_hp = true; mon.max_hp = 200;
    mon.has_hp = true;     mon.hp    = 200;
    // Two move slots
    mon.move_id0 = 33; mon.move_pp0 = pp0;  // TACKLE
    mon.move_id1 = 45; mon.move_pp1 = pp1;  // GROWL

    s.side0.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side0.mega_used = mega_used;

    // Opponent (minimal — required by 1v1 precondition check)
    PokemonState opp{};
    opp.species = 1;
    opp.level   = 50;
    opp.has_stats = true;
    opp.stat_hp = 200; opp.stat_atk = 80; opp.stat_def = 80;
    opp.stat_spa = 80; opp.stat_spd = 80; opp.stat_spe = 60;
    opp.has_max_hp = true; opp.max_hp = 200;
    opp.has_hp = true;     opp.hp    = 200;
    opp.move_id0 = 33; opp.move_pp0 = 35;

    s.side1.team.push_back(opp);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// 2 usable moves + matching mega stone → 4 actions (2 base + 2 mega variants).
TEST_CASE("action_space: 2 moves + matching mega stone → 4 actions", "[action_space]") {
    BattleState s = make_state(SPECIES_ALAKAZAM, ITEM_ALAKAZITE, 35, 35);
    auto actions = legal_player_actions(s);

    REQUIRE(actions.size() == 4);

    // Exactly 2 non-mega and 2 mega
    int non_mega = 0, mega = 0;
    for (const auto& a : actions) {
        REQUIRE(a.kind == 0);  // all MOVE
        if (a.mega) ++mega; else ++non_mega;
    }
    REQUIRE(non_mega == 2);
    REQUIRE(mega == 2);

    // Each mega variant must share move_slot with a non-mega base action
    for (const auto& a : actions) {
        if (!a.mega) continue;
        bool found = false;
        for (const auto& b : actions)
            if (!b.mega && b.move_slot == a.move_slot) { found = true; break; }
        REQUIRE(found);
    }
}

// Same setup but mega already used this battle → 2 actions only (no mega variants).
TEST_CASE("action_space: mega_used=true → 2 actions (no mega variants)", "[action_space]") {
    BattleState s = make_state(SPECIES_ALAKAZAM, ITEM_ALAKAZITE, 35, 35, /*mega_used=*/true);
    auto actions = legal_player_actions(s);

    REQUIRE(actions.size() == 2);
    for (const auto& a : actions)
        REQUIRE_FALSE(a.mega);
}

// Wrong stone: item has a mega entry but pre_species != active species → 2 actions.
TEST_CASE("action_space: wrong mega stone (pre_species mismatch) → 2 actions", "[action_space]") {
    // ITEM_ALAKAZITE pre_species=65 (Alakazam); species=1 (Bulbasaur) → mismatch
    BattleState s = make_state(/*species=*/1, ITEM_ALAKAZITE, 35, 35);
    auto actions = legal_player_actions(s);

    REQUIRE(actions.size() == 2);
    for (const auto& a : actions)
        REQUIRE_FALSE(a.mega);
}

// All moves at 0 PP → exactly 1 Struggle action (move_slot == -2), no mega variant.
// Python generates Struggle AFTER the mega block, so Struggle never gets a mega variant.
TEST_CASE("action_space: all PP 0 → exactly 1 Struggle, no mega variant", "[action_space]") {
    BattleState s = make_state(SPECIES_ALAKAZAM, ITEM_ALAKAZITE, 0, 0);
    auto actions = legal_player_actions(s);

    REQUIRE(actions.size() == 1);
    REQUIRE(actions[0].move_slot == -2);
    REQUIRE_FALSE(actions[0].mega);
}
