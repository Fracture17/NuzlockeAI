// Regression suite for Task R2 faint-semantics bugs (USER 2026-07-15).
// Covers Destiny Bond direct-faint (survival mechanics must NOT apply), Explosion
// self-faint on miss/Protect/normal-hit, Curse Ghost at/below-half self-faint,
// and Memento activation-gated faint (miss/Protect/Substitute suppress).
#include <catch2/catch_test_macros.hpp>

#include "state.h"
#include "effects.h"
#include "effects_consts.h"
#include "move_exec.h"
#include "move_exec_guards.h"
#include "move_exec_damage.h"

#include <cstdint>
#include <vector>

// effects_consts.h defines VOLATILE_* etc. inside namespace eff.
using namespace eff;

// --- Move ids (mirrors ai_shared.h / ai_scorer_internal.h) ---
static constexpr int32_t MV_TACKLE_ID    = 33;
static constexpr int32_t MV_EXPLOSION_ID = 153;
static constexpr int32_t MV_CURSE_ID     = 174;
static constexpr int32_t MV_MEMENTO_ID   = 262;

// --- Abilities ---
static constexpr int32_t AB_STURDY_ID     = 5;
static constexpr int32_t AB_CLEAR_BODY_ID = 29;

// --- Items ---
static constexpr int32_t ITM_FOCUS_SASH_ID = 275;

// VOLATILE_CURSED is a file-local constant in effects.cpp; mirror the same bit here.
static constexpr int32_t VOLATILE_CURSED_BIT = 4;

// ---------------------------------------------------------------------------
// Shared state builder: two singles mons with configurable stats.
// ---------------------------------------------------------------------------
struct FaintSemMon {
    int32_t species    = 25;   // Pikachu
    int32_t level      = 50;
    int32_t max_hp     = 100;
    int32_t hp         = 100;
    int32_t stat_atk   = 60;
    int32_t stat_def   = 60;
    int32_t stat_spa   = 60;
    int32_t stat_spd   = 60;
    int32_t stat_spe   = 60;
    int32_t ability    = 0;
    int32_t item       = 0;
    int32_t move_id0   = MV_TACKLE_ID;
    int32_t move_pp0   = 35;
    std::vector<int32_t> types;  // empty leaves has_types=false
    int32_t stage5     = 0;      // accuracy stage
};

static void install_mon(SideState& side, const FaintSemMon& spec) {
    PokemonState mon{};
    mon.species    = spec.species;
    mon.level      = spec.level;
    mon.has_stats  = true;
    mon.stat_hp    = spec.max_hp;
    mon.stat_atk   = spec.stat_atk;
    mon.stat_def   = spec.stat_def;
    mon.stat_spa   = spec.stat_spa;
    mon.stat_spd   = spec.stat_spd;
    mon.stat_spe   = spec.stat_spe;
    mon.has_max_hp = true; mon.max_hp = spec.max_hp;
    mon.has_hp     = true; mon.hp     = spec.hp;
    mon.ability    = spec.ability;
    mon.item       = spec.item;
    mon.move_id0   = spec.move_id0;
    mon.move_pp0   = spec.move_pp0;
    mon.stage5     = spec.stage5;
    if (!spec.types.empty()) {
        mon.has_types = true;
        for (int32_t t : spec.types) mon.types.push_back(t);
    }
    side.team.push_back(mon);
    side.active_indices.push_back((int32_t)side.team.size() - 1);
}

static BattleState build_state(const FaintSemMon& atk, const FaintSemMon& def) {
    BattleState s{};
    install_mon(s.side0, atk);
    // side1 has a distinct default species so identity tests don't collide.
    FaintSemMon def_final = def;
    if (def_final.species == 25) def_final.species = 9;  // Blastoise default for defender
    install_mon(s.side1, def_final);
    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// Destiny Bond direct-faint tests
// ---------------------------------------------------------------------------
// Trigger: opp holds VOLATILE_DESTINY_BOND, attacker KOs opp with Tackle. Attacker
// must faint regardless of Focus Sash / Sturdy at full HP.
// We drive the KO by invoking cpp_execute_action directly.
// ---------------------------------------------------------------------------

static BattleState build_db_state(int32_t attacker_ability, int32_t attacker_item) {
    FaintSemMon atk;
    atk.species = 25; atk.max_hp = 100; atk.hp = 100;
    atk.stat_atk = 250;  // huge Atk to guarantee OHKO with Tackle
    atk.ability = attacker_ability;
    atk.item    = attacker_item;
    atk.move_id0 = MV_TACKLE_ID; atk.move_pp0 = 35;

    FaintSemMon def;
    def.species = 9; def.max_hp = 40; def.hp = 1;  // 1 HP so Tackle KOs
    def.stat_def = 10;
    BattleState s = build_state(atk, def);
    // Set defender's DESTINY_BOND volatile.
    s.side1.team[0].volatiles |= VOLATILE_DESTINY_BOND;
    return s;
}

TEST_CASE("Destiny Bond: Focus Sash at full HP does not save attacker",
          "[destiny_bond][faint][r2]") {
    BattleState s = build_db_state(/*ability=*/0, /*item=*/ITM_FOCUS_SASH_ID);
    REQUIRE(s.side0.team[0].hp == s.side0.team[0].max_hp);
    REQUIRE(s.side1.team[0].volatiles & VOLATILE_DESTINY_BOND);

    ExecAction action{};
    action.kind = 0; action.move_slot = 0;

    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.damage_roll = 1.0;  // max roll for OHKO reliability
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // Defender KO'd, DB triggered, attacker MUST be fainted regardless of Sash.
    REQUIRE(s.side1.team[0].fainted == true);
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
}

TEST_CASE("Destiny Bond: Sturdy at full HP does not save attacker",
          "[destiny_bond][faint][r2]") {
    BattleState s = build_db_state(/*ability=*/AB_STURDY_ID, /*item=*/0);
    REQUIRE(s.side0.team[0].hp == s.side0.team[0].max_hp);
    REQUIRE(s.side1.team[0].volatiles & VOLATILE_DESTINY_BOND);

    ExecAction action{};
    action.kind = 0; action.move_slot = 0;

    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.damage_roll = 1.0;
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    REQUIRE(s.side1.team[0].fainted == true);
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
}

// ---------------------------------------------------------------------------
// Explosion self-faint tests
// ---------------------------------------------------------------------------

static BattleState build_boom_state() {
    FaintSemMon atk;
    atk.species = 25; atk.max_hp = 100; atk.hp = 100;
    atk.stat_atk = 100;
    atk.move_id0 = MV_EXPLOSION_ID; atk.move_pp0 = 5;

    FaintSemMon def;
    def.species = 9; def.max_hp = 200; def.hp = 200;
    def.stat_def = 80;

    return build_state(atk, def);
}

TEST_CASE("Explosion: normal hit self-faints attacker (regression)",
          "[explosion][faint][r2]") {
    BattleState s = build_boom_state();

    ExecAction action{};
    action.kind = 0; action.move_slot = 0;

    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.damage_roll = 0.5;
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // Attacker faints after hitting.
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
}

TEST_CASE("Explosion: user faints even on miss",
          "[explosion][faint][miss][r2]") {
    BattleState s = build_boom_state();
    // Drop attacker accuracy to -6 so effective acc = 100 * 3/9 ~= 33.3.
    s.side0.team[0].stage5 = -6;

    ExecAction action{};
    action.kind = 0; action.move_slot = 0;

    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.accuracy_threshold = 50.0;  // deterministic: 33.3 < 50 -> miss
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // Move missed (defender untouched) but user MUST still faint.
    REQUIRE(s.side1.team[0].hp == s.side1.team[0].max_hp);
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side0.team[0].last_move_failed == true);
}

TEST_CASE("Explosion: user faints when target Protects",
          "[explosion][faint][protect][r2]") {
    BattleState s = build_boom_state();

    ExecAction action{};
    action.kind = 0; action.move_slot = 0;

    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.damage_roll = 0.5;
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};
    ctx.protected_sides[1] = true;   // defender protects
    ctx.protect_move[1]    = 182;    // vanilla Protect (id doesn't matter for damage)

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // Defender took no damage (Protect blocked), user MUST still faint.
    REQUIRE(s.side1.team[0].hp == s.side1.team[0].max_hp);
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
}

// ---------------------------------------------------------------------------
// Ghost Curse self-faint tests
// ---------------------------------------------------------------------------
// Above half: 1/2 max_hp cost, defender cursed, user alive.
// At/below half: user pays ALL remaining HP (faint) AND defender cursed.
// ---------------------------------------------------------------------------

static BattleState build_curse_state(int32_t user_hp, int32_t user_max_hp) {
    FaintSemMon atk;
    atk.species = 92; atk.max_hp = user_max_hp; atk.hp = user_hp;
    atk.types = {TYPE_GHOST};
    atk.move_id0 = MV_CURSE_ID; atk.move_pp0 = 10;

    FaintSemMon def;
    def.species = 9; def.max_hp = 100; def.hp = 100;

    return build_state(atk, def);
}

TEST_CASE("Curse Ghost: above half — user pays max_hp/2, defender cursed",
          "[curse][ghost][above_half][r2]") {
    BattleState s = build_curse_state(/*hp=*/80, /*max=*/100);

    EffectsLuck luck{}; ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_CURSE_ID, luck, ctx, /*attacker_slot=*/0);

    REQUIRE(s.side0.team[0].hp == 30);  // 80 - 50
    REQUIRE(s.side0.team[0].fainted == false);
    REQUIRE((s.side1.team[0].volatiles & VOLATILE_CURSED_BIT) != 0);
}

TEST_CASE("Curse Ghost: at exactly half — defender cursed, user self-faints",
          "[curse][ghost][boundary][r2]") {
    // max=100, cost=50, hp=50 -> hp <= cost triggers self-faint branch.
    BattleState s = build_curse_state(/*hp=*/50, /*max=*/100);

    EffectsLuck luck{}; ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_CURSE_ID, luck, ctx, /*attacker_slot=*/0);

    REQUIRE((s.side1.team[0].volatiles & VOLATILE_CURSED_BIT) != 0);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side0.team[0].fainted == true);
}

TEST_CASE("Curse Ghost: at 1 HP — defender cursed, user self-faints",
          "[curse][ghost][r2]") {
    BattleState s = build_curse_state(/*hp=*/1, /*max=*/100);

    EffectsLuck luck{}; ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_CURSE_ID, luck, ctx, /*attacker_slot=*/0);

    REQUIRE((s.side1.team[0].volatiles & VOLATILE_CURSED_BIT) != 0);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side0.team[0].fainted == true);
}

// ---------------------------------------------------------------------------
// Memento tests — verification. Faint iff move activates.
// ---------------------------------------------------------------------------

static BattleState build_memento_state(int32_t target_ability = 0) {
    FaintSemMon atk;
    atk.species = 25; atk.max_hp = 100; atk.hp = 100;
    atk.move_id0 = MV_MEMENTO_ID; atk.move_pp0 = 10;

    FaintSemMon def;
    def.species = 9; def.max_hp = 100; def.hp = 100;
    def.ability = target_ability;

    return build_state(atk, def);
}

TEST_CASE("Memento: normal hit — user faints, target -2 Atk/-2 SpA",
          "[memento][faint][r2]") {
    BattleState s = build_memento_state();

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side1.team[0].stage0 == -2);
    REQUIRE(s.side1.team[0].stage2 == -2);
}

TEST_CASE("Memento: target already at -6 Atk and -6 SpA — user still faints",
          "[memento][minus6][r2]") {
    BattleState s = build_memento_state();
    s.side1.team[0].stage0 = -6;
    s.side1.team[0].stage2 = -6;

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // USER spec 2026-07-15: faint fires whenever the move activates, including when
    // both stats are already at minimum (no early-fail).
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side1.team[0].stage0 == -6);
    REQUIRE(s.side1.team[0].stage2 == -6);
}

TEST_CASE("Memento: Clear Body target — user still faints, no stat drops",
          "[memento][clear_body][r2]") {
    BattleState s = build_memento_state(/*target_ability=*/AB_CLEAR_BODY_ID);

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    // Faint-first-then-drop order: user faints even if Clear Body blocks drops.
    REQUIRE(s.side0.team[0].fainted == true);
    REQUIRE(s.side0.team[0].hp == 0);
    REQUIRE(s.side1.team[0].stage0 == 0);
    REQUIRE(s.side1.team[0].stage2 == 0);
}

TEST_CASE("Memento: miss — user does NOT faint",
          "[memento][miss][r2]") {
    BattleState s = build_memento_state();
    // Drop accuracy to force miss (Memento base acc=100 -> effective 33.3 at -6).
    s.side0.team[0].stage5 = -6;

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    la.accuracy_threshold = 50.0;
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    REQUIRE(s.side0.team[0].fainted == false);
    REQUIRE(s.side0.team[0].hp == s.side0.team[0].max_hp);
    REQUIRE(s.side1.team[0].stage0 == 0);
    REQUIRE(s.side1.team[0].stage2 == 0);
    REQUIRE(s.side0.team[0].last_move_failed == true);
}

TEST_CASE("Memento: target behind Substitute — user does NOT faint",
          "[memento][substitute][r2]") {
    BattleState s = build_memento_state();
    // Give defender an active substitute.
    s.side1.team[0].volatiles |= VOLATILE_SUBSTITUTE;
    s.side1.team[0].sub_hp = 25;

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    REQUIRE(s.side0.team[0].fainted == false);
    REQUIRE(s.side0.team[0].hp == s.side0.team[0].max_hp);
    REQUIRE(s.side1.team[0].stage0 == 0);
    REQUIRE(s.side1.team[0].stage2 == 0);
}

TEST_CASE("Memento: target Protects — user does NOT faint",
          "[memento][protect][r2]") {
    BattleState s = build_memento_state();

    ExecAction action{}; action.kind = 0; action.move_slot = 0;
    DamageLoopLuck la{}; DamageLoopLuck ld{};
    std::vector<PendingSwitch> pending;
    ExecCtx ctx{};
    ctx.protected_sides[1] = true;
    ctx.protect_move[1]    = 182;

    cpp_execute_action(s, /*side_idx=*/0, action, la, ld, pending, ctx, /*source_slot=*/0);

    REQUIRE(s.side0.team[0].fainted == false);
    REQUIRE(s.side0.team[0].hp == s.side0.team[0].max_hp);
    REQUIRE(s.side1.team[0].stage0 == 0);
    REQUIRE(s.side1.team[0].stage2 == 0);
}
