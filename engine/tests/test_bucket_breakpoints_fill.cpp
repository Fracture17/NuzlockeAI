// Bucket solver Task 8 Step 2 tests: BreakpointRegistry content fill
// (registry_static_entries — per-mechanic HP breakpoints beyond hp_thresholds()).
// Tests written BEFORE implementation; each locks in one SOLVER_BREAKPOINT_INVENTORY.md
// mechanic's exact trigger condition + formula, per Part 3.5 Task 8 of the bucket plan.
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/breakpoints.h"
#include "solver/engine_queries.h"
#include "solver/question.h"
#include "state.h"

#include <algorithm>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Helpers — mirrors test_bucket_core.cpp fixture conventions.
// ---------------------------------------------------------------------------

static PokemonState make_mon(int32_t species, int32_t max_hp, int32_t hp,
                             int32_t item, int32_t ability, int32_t speed = 80,
                             int32_t move0 = 33, int32_t move1 = 0,
                             int32_t move2 = 0, int32_t move3 = 0) {
    PokemonState p{};
    p.species    = species;
    p.level      = 50;
    p.has_stats  = true;
    p.stat_hp    = max_hp; p.stat_atk = 100; p.stat_def = 80;
    p.stat_spa   = 80;     p.stat_spd = 80;  p.stat_spe = speed;
    p.has_max_hp = true;   p.max_hp   = max_hp;
    p.has_hp     = true;   p.hp       = hp;
    p.move_id0   = move0;  p.move_pp0 = 35;
    p.move_id1   = move1;  p.move_id2 = move2; p.move_id3 = move3;
    p.item       = item;
    p.ability    = ability;
    return p;
}

static BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static Question default_question() {
    Question q;
    return q;
}

static bool has(const std::vector<int32_t>& bps, int32_t v) {
    return std::find(bps.begin(), bps.end(), v) != bps.end();
}

static constexpr int32_t MOVE_TACKLE = 33;

// Type constants (effects_consts.h).
static constexpr int32_t TYPE_FIRE   = 1;
static constexpr int32_t TYPE_FLYING = 9;

// ---------------------------------------------------------------------------
// HalfCrossing: Berserk 201 / Emergency Exit 194 / Wimp Out 193 (own axis, max_hp/2).
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Berserk crosses at max_hp/2 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_BERSERK = 201;
    static constexpr int32_t ODD_MAX = 201;   // 201/2 = 100

    PokemonState p = make_mon(1, ODD_MAX, ODD_MAX, 0, AB_BERSERK);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 100));
}

TEST_CASE("breakpoints fill: no HalfCrossing entry without the ability",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t ODD_MAX = 201;
    PokemonState p = make_mon(1, ODD_MAX, ODD_MAX, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), 100));
}

TEST_CASE("breakpoints fill: Emergency Exit crosses at max_hp/2 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_EMERGENCY_EXIT = 194;
    static constexpr int32_t ODD_MAX = 201;
    PokemonState p = make_mon(1, ODD_MAX, ODD_MAX, 0, AB_EMERGENCY_EXIT);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 100));
}

// ---------------------------------------------------------------------------
// PinchThird: Blaze/Torrent/Overgrow/Swarm (own axis, max_hp/3).
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Blaze crosses at max_hp/3 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_BLAZE = 66;
    static constexpr int32_t MAX_HP = 205;   // 205/3 = 68
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, AB_BLAZE);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 68));
}

// ---------------------------------------------------------------------------
// DefeatistHalf: ability 129 (own axis, max_hp/2).
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Defeatist crosses at max_hp/2 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_DEFEATIST = 129;
    static constexpr int32_t ODD_MAX = 201;
    PokemonState p = make_mon(1, ODD_MAX, ODD_MAX, 0, AB_DEFEATIST);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 100));
}

// ---------------------------------------------------------------------------
// BrineHalf: move 362 known by the OTHER side -> max_hp/2 on the defender's axis.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Brine known by opponent crosses on player's own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_BRINE = 362;
    static constexpr int32_t PLAYER_MAX = 201;  // 201/2 = 100
    PokemonState p = make_mon(1, PLAYER_MAX, PLAYER_MAX, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60, MOVE_BRINE);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 100));
}

TEST_CASE("breakpoints fill: Brine known by player crosses on opponent's own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_BRINE = 362;
    static constexpr int32_t OPP_MAX = 155;  // 155/2 = 77
    PokemonState p = make_mon(1, 200, 200, 0, 0, 80, MOVE_BRINE);
    PokemonState o = make_mon(2, OPP_MAX, OPP_MAX, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.opp_breakpoints(), 77));
}

TEST_CASE("breakpoints fill: Brine known by neither side crosses nowhere",
          "[bucket][breakpoints][fill]") {
    PokemonState p = make_mon(1, 201, 201, 0, 0);
    PokemonState o = make_mon(2, 155, 155, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), 100));
    REQUIRE_FALSE(has(bp.opp_breakpoints(), 77));
}

// ---------------------------------------------------------------------------
// SubCostQuarter: move 164 known -> max_hp/4 on own axis.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Substitute known crosses at max_hp/4 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_SUBSTITUTE = 164;
    static constexpr int32_t MAX_HP = 203;   // 203/4 = 50
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_SUBSTITUTE);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 50));
}

// ---------------------------------------------------------------------------
// CostHalf: Belly Drum 187 known, OR Curse 174 known + user is Ghost-type.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Belly Drum known crosses at max_hp/2 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_BELLY_DRUM = 187;
    static constexpr int32_t MAX_HP = 187;   // odd/2 not needed; use even for clarity
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_BELLY_DRUM);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), MAX_HP / 2));
}

TEST_CASE("breakpoints fill: Curse known + Ghost-type crosses at max_hp/2 on own axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_CURSE = 174;
    static constexpr int32_t MAX_HP = 174;   // 174/2 = 101 (odd-flavored check below uses 174-1)
    static constexpr int32_t TYPE_GHOST = 13;

    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_CURSE);
    p.has_types = true;
    p.types.push_back(TYPE_GHOST);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), MAX_HP / 2));
}

TEST_CASE("breakpoints fill: Curse known but non-Ghost user has no CostHalf entry",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_CURSE = 174;
    static constexpr int32_t MAX_HP = 174;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_CURSE);
    p.has_types = true;
    p.types.push_back(0);  // Normal, not Ghost
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), MAX_HP / 2));
}

// ---------------------------------------------------------------------------
// HealCapKink: recovery moves (Recover family), breakpoint = max_hp - c.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Recover known emits three heal-cap kinks",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_RECOVER = 105;
    static constexpr int32_t MAX_HP = 203;   // {102,153,68}
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_RECOVER);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& bps = bp.player_breakpoints();
    REQUIRE(has(bps, 102));
    REQUIRE(has(bps, 153));
    REQUIRE(has(bps, 68));
}

TEST_CASE("breakpoints fill: Swallow known emits two heal-cap kinks",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_SWALLOW = 256;
    static constexpr int32_t MAX_HP = 203;   // {153,102}
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_SWALLOW);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& bps = bp.player_breakpoints();
    REQUIRE(has(bps, 153));
    REQUIRE(has(bps, 102));
}

TEST_CASE("breakpoints fill: Heal Pulse known by opponent emits a kink on player axis",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_HEAL_PULSE = 505;
    static constexpr int32_t MAX_HP = 203;   // 203-101 = 102
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60, MOVE_HEAL_PULSE);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 102));
}

TEST_CASE("breakpoints fill: Strength Sap known emits a kink at max_hp minus opp effective atk",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_STRENGTH_SAP = 668;
    static constexpr int32_t MAX_HP = 203;   // opp atk stat_atk=100, stage 0 -> 100; 203-100=103
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_STRENGTH_SAP);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);   // stat_atk = 100 (make_mon default)
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 103));
}

TEST_CASE("breakpoints fill: Wish known emits max_hp/2 kink, plus pending wish_hp kink",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MOVE_WISH = 273;
    static constexpr int32_t MAX_HP = 203;   // 203-101 = 102
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_WISH);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.has_wish_pending = true;
    s.side0.wish_hp = 77;   // 203-77 = 126

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& bps = bp.player_breakpoints();
    REQUIRE(has(bps, 102));
    REQUIRE(has(bps, 126));
}

TEST_CASE("breakpoints fill: Absorb-ability holder emits a heal-cap kink at max_hp - max_hp/4",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_WATER_ABSORB = 11;
    static constexpr int32_t MAX_HP = 203;   // 203-50 = 153
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, AB_WATER_ABSORB);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 153));
}

// ---------------------------------------------------------------------------
// HazardKink: Stealth Rock / Spikes.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Stealth Rock with 4x weakness crosses at max_hp*4/8",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;   // floor(203*4.0/8.0) = 101
    static constexpr int32_t SC_STEALTH_ROCK = 4;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.has_types = true;
    p.types.push_back(TYPE_FIRE);
    p.types.push_back(TYPE_FLYING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_STEALTH_ROCK, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 101));
}

TEST_CASE("breakpoints fill: Stealth Rock with neutral effectiveness crosses at max_hp/8",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;   // floor(203/8.0) = 25
    static constexpr int32_t SC_STEALTH_ROCK = 4;
    static constexpr int32_t TYPE_NORMAL = 0;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.has_types = true;
    p.types.push_back(TYPE_NORMAL);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_STEALTH_ROCK, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 25));
}

TEST_CASE("breakpoints fill: Heavy-Duty Boots holder has no Stealth Rock kink",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;
    static constexpr int32_t SC_STEALTH_ROCK = 4;
    static constexpr int32_t ITEM_HEAVY_DUTY_BOOTS = 1120;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, ITEM_HEAVY_DUTY_BOOTS, 0);
    p.has_types = true;
    p.types.push_back(TYPE_FIRE);
    p.types.push_back(TYPE_FLYING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_STEALTH_ROCK, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), 101));
}

TEST_CASE("breakpoints fill: Magic Guard holder has no Stealth Rock kink",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;
    static constexpr int32_t SC_STEALTH_ROCK = 4;
    static constexpr int32_t AB_MAGIC_GUARD = 98;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, AB_MAGIC_GUARD);
    p.has_types = true;
    p.types.push_back(TYPE_FIRE);
    p.types.push_back(TYPE_FLYING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_STEALTH_ROCK, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), 101));
}

TEST_CASE("breakpoints fill: Spikes L3 crosses at max_hp/4 for a grounded mon",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;   // 203/4 = 50
    static constexpr int32_t SC_SPIKES_3 = 7;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.has_types = true;
    p.types.push_back(0);  // Normal, grounded
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_SPIKES_3, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE(has(bp.player_breakpoints(), 50));
}

TEST_CASE("breakpoints fill: Spikes has no kink for a Flying-type (non-grounded) mon",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t MAX_HP = 203;
    static constexpr int32_t SC_SPIKES_3 = 7;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.has_types = true;
    p.types.push_back(TYPE_FLYING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.side0.side_conditions.push_back({SC_SPIKES_3, -1});

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    REQUIRE_FALSE(has(bp.player_breakpoints(), 50));
}

// ---------------------------------------------------------------------------
// Form-change abilities: fail loud.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: Schooling holder throws form-change from registry_static_entries",
          "[bucket][breakpoints][fill][fail_loud]") {
    static constexpr int32_t AB_SCHOOLING = 208;
    PokemonState p = make_mon(1, 208, 208, 0, AB_SCHOOLING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    bool threw = false;
    try {
        registry_static_entries(s, 0);
    } catch (const std::runtime_error& e) {
        threw = true;
        REQUIRE(std::string(e.what()).find("form-change") != std::string::npos);
    }
    REQUIRE(threw);
}

TEST_CASE("breakpoints fill: Schooling holder throws form-change from instantiate",
          "[bucket][breakpoints][fill][fail_loud]") {
    static constexpr int32_t AB_SCHOOLING = 208;
    PokemonState p = make_mon(1, 208, 208, 0, AB_SCHOOLING);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    bool threw = false;
    try {
        reg.instantiate(s, default_question());
    } catch (const std::runtime_error& e) {
        threw = true;
        REQUIRE(std::string(e.what()).find("form-change") != std::string::npos);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Clean mon (no items/abilities/moves triggering anything): exactly {0, max_hp}
// (+ Question keepHp if set). Also structural sorted/unique/in-range.
// ---------------------------------------------------------------------------

TEST_CASE("breakpoints fill: clean mon yields exactly {0, max_hp}",
          "[bucket][breakpoints][fill]") {
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    // Opponent has no damaging move so no Task-9 AI roll-value breakpoints land on the
    // player axis; this keeps the assertion focused on player-side registry cleanliness.
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60, /*move0=*/0);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& bps = bp.player_breakpoints();
    REQUIRE(bps.size() == 2);
    REQUIRE(bps[0] == 0);
    REQUIRE(bps[1] == 200);
}

TEST_CASE("breakpoints fill: structural sorted/unique/in-range holds under a busy state",
          "[bucket][breakpoints][fill]") {
    static constexpr int32_t AB_BLAZE = 66;
    static constexpr int32_t MOVE_RECOVER = 105;
    static constexpr int32_t MAX_HP = 203;
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, AB_BLAZE, 80, MOVE_RECOVER);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& bps = bp.player_breakpoints();
    for (size_t i = 0; i < bps.size(); ++i) {
        REQUIRE(bps[i] >= 0);
        REQUIRE(bps[i] <= MAX_HP);
        if (i > 0) REQUIRE(bps[i-1] < bps[i]);
    }
}
