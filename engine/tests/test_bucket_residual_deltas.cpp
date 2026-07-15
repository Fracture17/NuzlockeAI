// Bucket solver Task 8 Step 3 tests: residual_delta_candidates content fill.
// Tests written BEFORE implementation; each locks in one SOLVER_BREAKPOINT_INVENTORY.md
// §7/§8 residual/on-hit magnitude, always as a BOTH-SIGNS candidate pair.
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/expand.h"
#include "state.h"

#include <algorithm>

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

static bool has(const std::vector<int32_t>& v, int32_t x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}

static constexpr int32_t STATUS_BURN   = 1;
static constexpr int32_t STATUS_POISON = 4;

TEST_CASE("residual deltas: burn and poison use distinct, correct magnitudes",
          "[bucket][expand][deltas]") {
    static constexpr int32_t MAX_HP = 203;   // burn: max(1,203/16)=12; poison: max(1,203/8)=25
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.status = STATUS_BURN;
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 12));
    REQUIRE(has(d, -12));
    REQUIRE_FALSE(has(d, 25));

    PokemonState p2 = p;
    p2.status = STATUS_POISON;
    BattleState s2 = make_state(p2, o);
    std::vector<int32_t> d2 = residual_delta_candidates(s2, 0);
    REQUIRE(has(d2, 25));
    REQUIRE(has(d2, -25));
    REQUIRE_FALSE(has(d2, 12));
}

TEST_CASE("residual deltas: Leftovers magnitude max(1,max/16)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t ITEM_LEFTOVERS = 234;
    static constexpr int32_t MAX_HP = 203;   // 203/16 = 12
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, ITEM_LEFTOVERS, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 12));
    REQUIRE(has(d, -12));
}

TEST_CASE("residual deltas: Sticky Barb magnitude max(1,max/8)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t ITEM_STICKY_BARB = 288;
    static constexpr int32_t MAX_HP = 203;   // 203/8 = 25
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, ITEM_STICKY_BARB, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 25));
    REQUIRE(has(d, -25));
}

TEST_CASE("residual deltas: Nightmare magnitude max(1,max/4)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t VE_NIGHTMARE = 26;
    static constexpr int32_t STATUS_SLEEP = 6;
    static constexpr int32_t MAX_HP = 203;   // 203/4 = 50
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.status = STATUS_SLEEP;
    p.timed_volatiles.push_back({VE_NIGHTMARE, 5});
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 50));
    REQUIRE(has(d, -50));
}

TEST_CASE("residual deltas: Bound emits both max/8 and Binding-Band max/6",
          "[bucket][expand][deltas]") {
    static constexpr int32_t VE_BOUND = 4;
    static constexpr int32_t I_BINDING_BAND = 544;
    static constexpr int32_t MAX_HP = 203;   // 203/8=25, 203/6=33
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.timed_volatiles.push_back({VE_BOUND, 4});
    PokemonState o = make_mon(2, 200, 200, I_BINDING_BAND, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 25));
    REQUIRE(has(d, -25));
    REQUIRE(has(d, 33));
    REQUIRE(has(d, -33));
}

TEST_CASE("residual deltas: sandstorm chip magnitude max(1,max/16)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t WEATHER_SANDSTORM = 3;
    static constexpr int32_t MAX_HP = 203;   // 203/16 = 12
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);
    s.weather = WEATHER_SANDSTORM;

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 12));
    REQUIRE(has(d, -12));
}

TEST_CASE("residual deltas: opponent Rocky Helmet magnitude max(1,max/6)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t ITEM_ROCKY_HELMET = 540;
    static constexpr int32_t MAX_HP = 203;   // 203/6 = 33
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, ITEM_ROCKY_HELMET, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 33));
    REQUIRE(has(d, -33));
}

TEST_CASE("residual deltas: opponent Rough Skin magnitude max(1,max/8)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t AB_ROUGH_SKIN = 24;
    static constexpr int32_t MAX_HP = 203;   // 203/8 = 25
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, AB_ROUGH_SKIN, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 25));
    REQUIRE(has(d, -25));
}

TEST_CASE("residual deltas: Life Orb magnitude max(1,max/10)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t ITEM_LIFE_ORB = 270;
    static constexpr int32_t MAX_HP = 203;   // 203/10 = 20
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, ITEM_LIFE_ORB, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 20));
    REQUIRE(has(d, -20));
}

TEST_CASE("residual deltas: HJK known magnitude max(1,max/2)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t MOVE_HIGH_JUMP_KICK = 136;
    static constexpr int32_t MAX_HP = 203;   // 203/2 = 101
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0, 80, MOVE_HIGH_JUMP_KICK);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 101));
    REQUIRE(has(d, -101));
}

TEST_CASE("residual deltas: opponent Bad Dreams magnitude max(1,max/8)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t AB_BAD_DREAMS = 123;
    static constexpr int32_t STATUS_SLEEP = 6;
    static constexpr int32_t MAX_HP = 203;   // 203/8 = 25
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.status = STATUS_SLEEP;
    PokemonState o = make_mon(2, 200, 200, 0, AB_BAD_DREAMS, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 25));
    REQUIRE(has(d, -25));
}

TEST_CASE("residual deltas: Leech Seed cross-axis — own drain and opp heal/Liquid-Ooze pool",
          "[bucket][expand][deltas]") {
    static constexpr int32_t VOL_LEECH_SEEDED = 2;
    static constexpr int32_t I_BIG_ROOT = 296;
    static constexpr int32_t MAX_HP = 203;   // drain=max(1,203/8)=25; big root 1.3x -> 32
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    p.volatiles |= VOL_LEECH_SEEDED;
    // o is the seed SOURCE — Big Root on o's own item boosts o's own-axis leech heal.
    PokemonState o = make_mon(2, 200, 200, I_BIG_ROOT, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d_own = residual_delta_candidates(s, 0);
    REQUIRE(has(d_own, 25));
    REQUIRE(has(d_own, -25));

    std::vector<int32_t> d_opp = residual_delta_candidates(s, 1);
    REQUIRE(has(d_opp, 25));
    REQUIRE(has(d_opp, -25));
    REQUIRE(has(d_opp, 32));
    REQUIRE(has(d_opp, -32));
}

TEST_CASE("residual deltas: Ripen doubles Sitrus heal to max/2",
          "[bucket][expand][deltas]") {
    static constexpr int32_t AB_RIPEN = 247;
    static constexpr int32_t ITEM_SITRUS = 158;
    static constexpr int32_t MAX_HP = 203;   // ripen: 203*2/4 = 101
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, ITEM_SITRUS, AB_RIPEN);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 101));
    REQUIRE(has(d, -101));
}

TEST_CASE("residual deltas: opponent Aftermath magnitude max_hp/4 with NO max(1,)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t AB_AFTERMATH = 106;
    static constexpr int32_t MAX_HP = 203;   // 203/4 = 50 (integer division; NOT max(1,...))
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, AB_AFTERMATH, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 50));
    REQUIRE(has(d, -50));
}

TEST_CASE("residual deltas: opponent Aftermath at max_hp=4 gives magnitude 1 (no max(1,) needed)",
          "[bucket][expand][deltas]") {
    static constexpr int32_t AB_AFTERMATH = 106;
    static constexpr int32_t MAX_HP = 4;   // 4/4 = 1
    PokemonState p = make_mon(1, MAX_HP, MAX_HP, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, AB_AFTERMATH, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(has(d, 1));
    REQUIRE(has(d, -1));
}

TEST_CASE("residual deltas: clean mon yields exactly {0}",
          "[bucket][expand][deltas]") {
    PokemonState p = make_mon(1, 200, 200, 0, 0);
    PokemonState o = make_mon(2, 200, 200, 0, 0, 60);
    BattleState s = make_state(p, o);

    std::vector<int32_t> d = residual_delta_candidates(s, 0);
    REQUIRE(d.size() == 1);
    REQUIRE(d[0] == 0);
}
