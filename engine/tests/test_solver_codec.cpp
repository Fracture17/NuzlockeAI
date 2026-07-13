// Tests for Task 3: PackedKey state codec + context interner.
// Verifies round-trip fidelity, context identity rules, and overflow guards.
#include <catch2/catch_test_macros.hpp>

#include <cstdint>
#include <stdexcept>

#include "state.h"
#include "state_eq.h"
#include "solver/state_codec.h"

// ---------------------------------------------------------------------------
// Fixture: minimal 1v1 BattleState (mirrors conventions from test_solver_projection.cpp)
// ---------------------------------------------------------------------------

static BattleState make_codec_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    mon.move_id0 = 33;
    mon.move_pp0 = 35;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// Test 1: Round-trip pack→unpack → state_equal_solver + exact HP values
// ---------------------------------------------------------------------------

TEST_CASE("codec round-trip: unpack equals original under state_equal_solver",
          "[codec][round_trip]") {
    ContextInterner interner;
    BattleState original = make_codec_state();
    original.side0.team[0].hp = 73;
    original.side1.team[0].hp = 51;

    PackedKey key = interner.pack(original);
    BattleState restored = interner.unpack(key);

    REQUIRE(state_equal_solver(original, restored));
    // HP values must be exact on both actives.
    REQUIRE(restored.side0.team[0].hp == 73);
    REQUIRE(restored.side1.team[0].hp == 51);
}

// ---------------------------------------------------------------------------
// Test 2: Two states differing ONLY in active HP → same ctx_id, different keys
// ---------------------------------------------------------------------------

TEST_CASE("codec: HP-only diff produces same ctx_id but different PackedKey",
          "[codec][context]") {
    ContextInterner interner;
    BattleState s1 = make_codec_state();
    BattleState s2 = s1;
    s1.side0.team[0].hp = 80;
    s2.side0.team[0].hp = 60;

    PackedKey k1 = interner.pack(s1);
    PackedKey k2 = interner.pack(s2);

    REQUIRE(ctx_id_of(k1) == ctx_id_of(k2));
    REQUIRE(k1 != k2);
}

// ---------------------------------------------------------------------------
// Test 3: Two states differing in PP → different ctx_id
// ---------------------------------------------------------------------------

TEST_CASE("codec: PP diff produces different ctx_id", "[codec][context]") {
    ContextInterner interner;
    BattleState s1 = make_codec_state();
    BattleState s2 = s1;
    s2.side0.team[0].move_pp0 = 10;  // originally 35

    PackedKey k1 = interner.pack(s1);
    PackedKey k2 = interner.pack(s2);

    REQUIRE(ctx_id_of(k1) != ctx_id_of(k2));
}

// ---------------------------------------------------------------------------
// Test 4: turn_number diff → same ctx_id (turn_number IS in the solver exclusion set)
// ---------------------------------------------------------------------------

// state_eq.h documents that turn_number is excluded from state_hash_solver /
// state_equal_solver. Therefore two states differing only in turn_number map to
// the same context. This test asserts that behavior.
TEST_CASE("codec: turn_number-only diff produces same ctx_id",
          "[codec][context][turn_number]") {
    ContextInterner interner;
    BattleState s1 = make_codec_state();
    BattleState s2 = s1;
    s2.turn_number = s1.turn_number + 5;

    PackedKey k1 = interner.pack(s1);
    PackedKey k2 = interner.pack(s2);

    // Same ctx because turn_number is excluded by state_hash_solver.
    REQUIRE(ctx_id_of(k1) == ctx_id_of(k2));
    // Keys are identical (same HP values too).
    REQUIRE(k1 == k2);
}

// ---------------------------------------------------------------------------
// Test 5: Re-pack idempotence: pack(unpack(pack(s))) == pack(s)
// ---------------------------------------------------------------------------

TEST_CASE("codec: re-pack idempotence", "[codec][idempotent]") {
    ContextInterner interner;
    BattleState s = make_codec_state();
    s.side0.team[0].hp = 55;
    s.side1.team[0].hp = 88;

    PackedKey k1 = interner.pack(s);
    BattleState restored = interner.unpack(k1);
    PackedKey k2 = interner.pack(restored);

    REQUIRE(k1 == k2);
}

// ---------------------------------------------------------------------------
// Test 6: context_count() reflects interning
// ---------------------------------------------------------------------------

TEST_CASE("codec: context_count grows only on distinct contexts", "[codec][count]") {
    ContextInterner interner;
    REQUIRE(interner.context_count() == 0);

    BattleState s1 = make_codec_state();
    BattleState s2 = s1;
    s2.side0.team[0].hp = 50;  // same context as s1 (HP-only diff)

    BattleState s3 = s1;
    s3.side0.team[0].move_pp0 = 10;  // different context

    interner.pack(s1);
    REQUIRE(interner.context_count() == 1);

    interner.pack(s2);  // same ctx
    REQUIRE(interner.context_count() == 1);

    interner.pack(s3);  // new ctx
    REQUIRE(interner.context_count() == 2);
}

// ---------------------------------------------------------------------------
// Test 7: Fail loud — non-1v1 state (no active) throws
// ---------------------------------------------------------------------------

TEST_CASE("codec: throws on missing active (0 actives per side)", "[codec][fail_loud]") {
    ContextInterner interner;
    BattleState s = make_codec_state();
    s.side0.active_indices.clear();  // violate 1v1

    REQUIRE_THROWS_AS(interner.pack(s), std::invalid_argument);
}

TEST_CASE("codec: throws on multiple actives (not 1v1)", "[codec][fail_loud]") {
    ContextInterner interner;
    BattleState s = make_codec_state();
    s.side0.active_indices.push_back(0);  // now size=2

    REQUIRE_THROWS_AS(interner.pack(s), std::invalid_argument);
}

// ---------------------------------------------------------------------------
// Test 8: Fail loud — HP overflow (> 65535) throws
// ---------------------------------------------------------------------------

TEST_CASE("codec: throws on player active HP > 65535", "[codec][fail_loud]") {
    ContextInterner interner;
    BattleState s = make_codec_state();
    s.side0.team[0].hp = 70000;  // > 0xFFFF

    REQUIRE_THROWS_AS(interner.pack(s), std::overflow_error);
}

TEST_CASE("codec: throws on opponent active HP > 65535", "[codec][fail_loud]") {
    ContextInterner interner;
    BattleState s = make_codec_state();
    s.side1.team[0].hp = 70000;

    REQUIRE_THROWS_AS(interner.pack(s), std::overflow_error);
}
