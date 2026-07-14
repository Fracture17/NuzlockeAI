// Catch2 detection-level tests for Emergency Exit (ability 194) and Wimp Out (ability 193).
// Tests call cpp_apply_post_hit_effects and emergency_exit_check directly to verify the
// pending/residual_switches vectors without needing a Policy.
// Site 3 (entry-hazard resolution) requires Policy so those cases live in the Python suite.
#include <catch2/catch_test_macros.hpp>

#include "state.h"
#include "effects.h"
#include "effects_consts.h"
#include "residuals.h"    // cpp_apply_residuals, emergency_exit_check

// Ability constants (local; mirrors post_hit.cpp and residuals.cpp declarations).
static constexpr int32_t AB_EMERGENCY_EXIT = 194;
static constexpr int32_t AB_WIMP_OUT       = 193;
static constexpr int32_t AB_NONE           = 0;

// Item constant for no item.
static constexpr int32_t ITEM_NONE = 0;

// ---------------------------------------------------------------------------
// State construction helpers
// ---------------------------------------------------------------------------

// Build a minimal BattleState with active mon on each side.
// The defender (side di) has the given ability, max_hp, and current hp.
// Optionally adds a bench mon for side di.
static BattleState make_state(int32_t defender_ability, int32_t def_maxhp, int32_t def_hp,
                               bool add_bench) {
    BattleState s{};

    // Attacker (side 0)
    PokemonState atk{};
    atk.species   = 25;  // Pikachu
    atk.level     = 50;
    atk.has_stats = true;
    atk.has_max_hp = true; atk.max_hp = 100;
    atk.has_hp     = true; atk.hp     = 100;
    atk.stat_atk   = 60; atk.stat_def = 60;
    atk.stat_spa   = 60; atk.stat_spd = 60;
    atk.stat_spe   = 60; atk.stat_hp  = 100;
    s.side0.team.push_back(atk);
    s.side0.active_indices.push_back(0);

    // Defender (side 1) with the given ability and HP values.
    PokemonState def{};
    def.species   = 9;  // Blastoise
    def.level     = 50;
    def.ability   = defender_ability;
    def.has_stats = true;
    def.has_max_hp = true; def.max_hp = def_maxhp;
    def.has_hp     = true; def.hp     = def_hp;
    def.stat_atk   = 60; def.stat_def = 60;
    def.stat_spa   = 60; def.stat_spd = 60;
    def.stat_spe   = 60; def.stat_hp  = def_maxhp;
    s.side1.team.push_back(def);
    s.side1.active_indices.push_back(0);

    if (add_bench) {
        PokemonState bench{};
        bench.species   = 143;  // Snorlax
        bench.level     = 50;
        bench.has_stats = true;
        bench.has_max_hp = true; bench.max_hp = 200;
        bench.has_hp     = true; bench.hp     = 200;
        bench.stat_hp    = 200;
        s.side1.team.push_back(bench);
    }

    s.turn_number = 1;
    return s;
}

// Build PostHitArgs for a simple damage hit.
static PostHitArgs make_args(int si, int di, int actual_damage, bool hit_sub = false) {
    PostHitArgs a{};
    a.side_idx        = si;
    a.defender_idx    = di;
    a.move            = 33;  // TACKLE
    a.move_type       = 1;   // NORMAL
    a.damage          = actual_damage;
    a.actual_damage   = actual_damage;
    a.hit_sub         = hit_sub;
    a.effective_slot  = 0;
    a.attacker_slot   = 0;
    return a;
}

// ---------------------------------------------------------------------------
// Test 1: Move-damage crossing with Emergency Exit queues "emergency_exit".
// ---------------------------------------------------------------------------
TEST_CASE("EE: move-damage crossing queues emergency_exit in pending", "[ee][move]") {
    // Defender: max_hp=100, starts at 60 (above 50), takes 20 damage -> 40 hp (<= 50).
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 60, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    // Simulate: hp was 60, actual_damage=20, so hp now = 40.
    s.side1.team[0].hp = 40;
    PostHitArgs a = make_args(0, 1, 20);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.size() == 1);
    REQUIRE(pending[0].side_idx == 1);
    REQUIRE(pending[0].reason == "emergency_exit");
}

// ---------------------------------------------------------------------------
// Test 2: Wimp Out produces identical queue entry.
// ---------------------------------------------------------------------------
TEST_CASE("WO: move-damage crossing queues emergency_exit in pending", "[ee][move]") {
    BattleState s = make_state(AB_WIMP_OUT, 100, 60, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 40;
    PostHitArgs a = make_args(0, 1, 20);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.size() == 1);
    REQUIRE(pending[0].side_idx == 1);
    REQUIRE(pending[0].reason == "emergency_exit");
}

// ---------------------------------------------------------------------------
// Test 3: No live bench → no push.
// ---------------------------------------------------------------------------
TEST_CASE("EE: no live bench suppresses push", "[ee][move]") {
    // No bench added → bench pool empty.
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 60, /*bench=*/false);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 40;
    PostHitArgs a = make_args(0, 1, 20);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Test 4: hit_sub=true → no push (move hit the substitute, not the mon).
// ---------------------------------------------------------------------------
TEST_CASE("EE: hit_sub suppresses push", "[ee][move]") {
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 60, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 40;
    PostHitArgs a = make_args(0, 1, 20, /*hit_sub=*/true);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Test 5a: Exactly-50% boundary — hp_now == maxhp/2 and hp_before > half → push present.
// ---------------------------------------------------------------------------
TEST_CASE("EE: boundary hp_now==half (crossed) pushes", "[ee][move][boundary]") {
    // max_hp=100, half=50. hp after hit = 50, hp before = 51 => crossed.
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 51, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 50;
    PostHitArgs a = make_args(0, 1, 1);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.size() == 1);
    REQUIRE(pending[0].reason == "emergency_exit");
}

// ---------------------------------------------------------------------------
// Test 5b: hp_now == half+1 (not crossed, still above half) → no push.
// ---------------------------------------------------------------------------
TEST_CASE("EE: boundary hp_now==half+1 (not crossed) no push", "[ee][move][boundary]") {
    // max_hp=100, half=50. hp after = 51, hp before = 52 → not crossed (51 > 50).
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 52, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 51;
    PostHitArgs a = make_args(0, 1, 1);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Test 5c: hp_before <= half already → no push (strict crossing requires before > half).
// ---------------------------------------------------------------------------
TEST_CASE("EE: hp_before<=half (already below threshold) no push", "[ee][move][boundary]") {
    // max_hp=100, half=50. Start at 50 (= half), take 10 → hp_before=50 is NOT > half.
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 50, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    s.side1.team[0].hp = 40;
    PostHitArgs a = make_args(0, 1, 10);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Test 6: Fainted defender (hp=0) → no push.
// ---------------------------------------------------------------------------
TEST_CASE("EE: fainted defender (hp=0) no push", "[ee][move]") {
    BattleState s = make_state(AB_EMERGENCY_EXIT, 100, 60, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    EffectsLuck luck{};
    // Faint the defender.
    s.side1.team[0].hp     = 0;
    s.side1.team[0].fainted = true;
    PostHitArgs a = make_args(0, 1, 60);
    cpp_apply_post_hit_effects(s, a, pending, luck);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Helper: build a state for residual emergency_exit_check tests.
// active_hp is the HP AFTER residual damage; hp_before is captured before damage.
// ---------------------------------------------------------------------------
static BattleState make_residual_state(int32_t ability, int32_t max_hp, int32_t active_hp,
                                        bool add_bench) {
    BattleState s{};

    PokemonState opp{};
    opp.species = 25; opp.level = 50;
    opp.has_stats = opp.has_max_hp = opp.has_hp = true;
    opp.max_hp = 100; opp.hp = 100; opp.stat_hp = 100;
    s.side0.team.push_back(opp);
    s.side0.active_indices.push_back(0);

    PokemonState mon{};
    mon.species  = 9; mon.level = 50;
    mon.ability  = ability;
    mon.has_stats = mon.has_max_hp = mon.has_hp = true;
    mon.max_hp   = max_hp;
    mon.hp       = active_hp;
    mon.stat_hp  = max_hp;
    s.side1.team.push_back(mon);
    s.side1.active_indices.push_back(0);

    if (add_bench) {
        PokemonState bench{};
        bench.species = 143; bench.level = 50;
        bench.has_stats = bench.has_max_hp = bench.has_hp = true;
        bench.max_hp = 200; bench.hp = 200; bench.stat_hp = 200;
        s.side1.team.push_back(bench);
    }
    s.turn_number = 1;
    return s;
}

// emergency_exit_check is declared in residuals.h (exported for native tests).

// ---------------------------------------------------------------------------
// Test 7a: EE mon at <=half after residual, alive, bench → queued.
// ---------------------------------------------------------------------------
TEST_CASE("residuals: EE mon crosses half via residual → queued", "[ee][residuals]") {
    // max_hp=100, hp before residual=60, after=40 → crossed (60>50 and 40<=50).
    BattleState s = make_residual_state(AB_EMERGENCY_EXIT, 100, 40, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    emergency_exit_check(s, 1, 0, /*hp_before=*/60, pending);
    REQUIRE(pending.size() == 1);
    REQUIRE(pending[0].side_idx == 1);
    REQUIRE(pending[0].reason == "emergency_exit");
}

// ---------------------------------------------------------------------------
// Test 7b: Non-EE ability → nothing queued.
// ---------------------------------------------------------------------------
TEST_CASE("residuals: non-EE ability → not queued", "[ee][residuals]") {
    BattleState s = make_residual_state(AB_NONE, 100, 40, /*bench=*/true);
    std::vector<PendingSwitch> pending;
    emergency_exit_check(s, 1, 0, 60, pending);
    REQUIRE(pending.empty());
}

// ---------------------------------------------------------------------------
// Test 7c: hp==0 (fainted) → not queued.
// ---------------------------------------------------------------------------
TEST_CASE("residuals: fainted mon (hp=0) → not queued", "[ee][residuals]") {
    BattleState s = make_residual_state(AB_EMERGENCY_EXIT, 100, 0, /*bench=*/true);
    s.side1.team[0].fainted = true;
    std::vector<PendingSwitch> pending;
    emergency_exit_check(s, 1, 0, 60, pending);
    REQUIRE(pending.empty());
}
