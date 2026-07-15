// Regression: Rest at full HP must fail (no sleep, no heal) but still consume PP.
// Mirrors mainline Emerald behavior confirmed by the project owner (SOLVER_BUCKET_PLAN Part 1
// amendment 20a / Task R). Below full HP, Rest heals to full and applies rest-sleep.
// Fixed: engine/src/effects.cpp apply_interaction_move / MOVE_REST branch.
#include <catch2/catch_test_macros.hpp>

#include "state.h"
#include "effects.h"           // cpp_apply_status_move, EffectsLuck
#include "move_exec.h"         // cpp_execute_action, ExecAction, DamageLoopLuck
#include "move_exec_guards.h"  // ExecCtx

#include <cstdint>
#include <vector>

// --- Move / status ids (mirroring engine/src/effects_consts.h) ---
static constexpr int32_t MV_REST      = 156;
static constexpr int32_t ST_NONE      = 0;
static constexpr int32_t ST_SLEEP     = 6;

// Build a minimal singles state with one full-HP attacker and one healthy defender.
// Both hold no items, no abilities that affect status, and no types that block Sleep.
// Rest sits in move slot 0; other slots are empty.
static BattleState make_rest_state(int32_t user_hp, int32_t user_max_hp,
                                   int32_t user_status = ST_NONE,
                                   int32_t rest_pp = 10) {
    BattleState s{};

    PokemonState user{};
    user.species = 1; user.level = 50;
    user.has_stats = true;
    user.stat_hp = user_max_hp; user.stat_atk = 60; user.stat_def = 60;
    user.stat_spa = 60;         user.stat_spd = 60; user.stat_spe = 60;
    user.has_max_hp = true; user.max_hp = user_max_hp;
    user.has_hp     = true; user.hp     = user_hp;
    user.status     = user_status;
    user.move_id0   = MV_REST; user.move_pp0 = rest_pp;
    user.ability    = 0; user.item = 0;
    // Types: use Normal so no immunities kick in. has_types must be true or engine
    // treats types as unset — set to a single Normal type (id 0 is unused; use 1 = NORMAL
    // per effects_consts.h TYPE_NORMAL=1... but we don't need to worry about type-based
    // blockers here since can_apply_status only checks POISON/STEEL/FIRE/ICE/ELECTRIC/GRASS.
    // Leaving has_types=false is what other tests do; can_apply_status handles it.
    s.side0.team.push_back(user);
    s.side0.active_indices.push_back(0);

    PokemonState opp{};
    opp.species = 2; opp.level = 50;
    opp.has_stats = true;
    opp.stat_hp = 100; opp.stat_atk = 60; opp.stat_def = 60;
    opp.stat_spa = 60; opp.stat_spd = 60; opp.stat_spe = 60;
    opp.has_max_hp = true; opp.max_hp = 100;
    opp.has_hp     = true; opp.hp     = 100;
    opp.move_id0   = 33 /* Tackle */; opp.move_pp0 = 35;
    opp.ability    = 0; opp.item = 0;
    s.side1.team.push_back(opp);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// (A) Rest at full HP fails: HP unchanged, status unchanged, last_move_failed=true.
// Drives the effect directly through cpp_apply_status_move; PP consumption is
// handled upstream in cpp_execute_action and is exercised in test (C).
// ---------------------------------------------------------------------------

TEST_CASE("Rest at full HP fails: no sleep, no heal, last_move_failed set",
          "[rest][full_hp][fail]") {
    BattleState s = make_rest_state(/*user_hp=*/100, /*user_max_hp=*/100);

    // Sanity: pre-conditions.
    REQUIRE(s.side0.team[0].hp == 100);
    REQUIRE(s.side0.team[0].max_hp == 100);
    REQUIRE(s.side0.team[0].status == ST_NONE);
    REQUIRE(s.side0.team[0].is_rest_sleep == false);
    REQUIRE(s.side0.team[0].last_move_failed == false);

    EffectsLuck luck{};
    ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_REST, luck, ctx, /*attacker_slot=*/0);

    // Fail-path invariants: no HP change, no status, no rest-sleep flag, fail flag set.
    REQUIRE(s.side0.team[0].hp == 100);
    REQUIRE(s.side0.team[0].status == ST_NONE);
    REQUIRE(s.side0.team[0].is_rest_sleep == false);
    REQUIRE(s.side0.team[0].last_move_failed == true);
}

// ---------------------------------------------------------------------------
// (B) Rest below full HP heals to full and sets sleep + is_rest_sleep.
// This is the pre-existing correct behavior — guards against regressions when
// adding the full-HP fail check.
// ---------------------------------------------------------------------------

TEST_CASE("Rest below full HP heals to full and applies rest-sleep",
          "[rest][below_full][succeed]") {
    BattleState s = make_rest_state(/*user_hp=*/40, /*user_max_hp=*/100);

    EffectsLuck luck{};
    ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_REST, luck, ctx, /*attacker_slot=*/0);

    REQUIRE(s.side0.team[0].hp == 100);
    REQUIRE(s.side0.team[0].status == ST_SLEEP);
    REQUIRE(s.side0.team[0].is_rest_sleep == true);
    REQUIRE(s.side0.team[0].last_move_failed == false);
}

// ---------------------------------------------------------------------------
// (C) End-to-end via cpp_execute_action: PP is still consumed when Rest fails
// at full HP. Mirrors mainline Emerald: a failed move still spends its PP.
// ---------------------------------------------------------------------------

TEST_CASE("Rest at full HP consumes PP even when it fails",
          "[rest][full_hp][pp]") {
    BattleState s = make_rest_state(/*user_hp=*/100, /*user_max_hp=*/100,
                                    /*user_status=*/ST_NONE, /*rest_pp=*/10);

    ExecAction action{};
    action.kind      = 0;   // MOVE
    action.move_slot = 0;   // Rest is in slot 0

    DamageLoopLuck luck_atk{};
    DamageLoopLuck luck_def{};
    std::vector<PendingSwitch> pending_switches;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, luck_atk, luck_def,
                       pending_switches, ctx, /*source_slot=*/0);

    // PP consumed, but Rest failed (no sleep, no heal).
    REQUIRE(s.side0.team[0].move_pp0 == 9);
    REQUIRE(s.side0.team[0].hp == 100);
    REQUIRE(s.side0.team[0].status == ST_NONE);
    REQUIRE(s.side0.team[0].is_rest_sleep == false);
    REQUIRE(s.side0.team[0].last_move_failed == true);
}
