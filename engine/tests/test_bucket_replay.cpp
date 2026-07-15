// Bucket solver Task 3 tests: oracle extensions.
// Extension 1: per-leaf AI-action attribution in LeafDebugInfo.
// Extension 2: replay_path — forced-prefix single-turn replay with sequence verification.
// Tests written BEFORE implementation; they are expected to fail until the code exists.
#include <catch2/catch_test_macros.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/oracle_types.h"
#include "solver/transition_oracle.h"
#include "state.h"
#include "state_eq.h"

// ---------------------------------------------------------------------------
// Test helpers (mirror test_solver_oracle.cpp helpers)
// ---------------------------------------------------------------------------

static BattleState make_basic_state(int speed0 = 80, int speed1 = 60,
                                    int32_t player_move0 = 33,   // TACKLE
                                    int32_t opp_move0 = 33,
                                    int32_t player_item = 0,
                                    int32_t opp_item = 0,
                                    int32_t player_ability = 0,
                                    int32_t opp_ability = 0,
                                    int32_t opp_hp = 200,
                                    int32_t player_hp = 200) {
    BattleState s{};
    PokemonState mon{};
    mon.species    = 1;
    mon.level      = 50;
    mon.has_stats  = true;
    mon.stat_hp    = 200; mon.stat_atk = 100; mon.stat_def = 80;
    mon.stat_spa   = 80;  mon.stat_spd = 80;  mon.stat_spe = speed0;
    mon.has_max_hp = true; mon.max_hp = 200;
    mon.has_hp     = true; mon.hp     = player_hp;
    mon.move_id0   = player_move0; mon.move_pp0 = 35;
    mon.item       = player_item;
    mon.ability    = player_ability;
    s.side0.team.push_back(mon);
    s.side0.active_indices.push_back(0);

    PokemonState opp{};
    opp.species    = 2;
    opp.level      = 50;
    opp.has_stats  = true;
    opp.stat_hp    = 200; opp.stat_atk = 100; opp.stat_def = 80;
    opp.stat_spa   = 80;  opp.stat_spd = 80;  opp.stat_spe = speed1;
    opp.has_max_hp = true; opp.max_hp = 200;
    opp.has_hp     = true; opp.hp     = opp_hp;
    opp.move_id0   = opp_move0; opp.move_pp0 = 35;
    opp.item       = opp_item;
    opp.ability    = opp_ability;
    s.side1.team.push_back(opp);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;
    return s;
}

static ExecAction player_move_action(int slot = 0) {
    ExecAction a{};
    a.kind = 0; a.move_slot = slot;
    a.source_slot = 0; a.target_side = 1; a.target_slot = 0;
    return a;
}

// ---------------------------------------------------------------------------
// Test 5 (regression + identity foundation): oracle leaf multiset must be
// bit-identical with and without a debug callback installed.
// This is listed as test 5 in the spec but we put it first since it's purely
// additive and validates the null-check pattern before testing content.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: debug callback does not alter leaf multiset",
          "[bucket][regression]")
{
    // Tackle (33) with Shell Armor (75) removes crit: 16 distinct roll leaves.
    BattleState s = make_basic_state(80, 60, 33, 150, 0, 0, 0, 75);
    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Without debug callback
    std::vector<ChildOutcome> leaves_no_debug;
    {
        TransitionOracle::Config cfg;
        oracle.step(s, pa, [&](ChildOutcome co) -> bool {
            leaves_no_debug.push_back(co);
            return true;
        }, OrderingHint::Natural, cfg);
    }

    // With debug callback
    std::vector<ChildOutcome> leaves_with_debug;
    std::vector<LeafDebugInfo> captured_debug;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            captured_debug.push_back(dbg);
        };
        oracle.step(s, pa, [&](ChildOutcome co) -> bool {
            leaves_with_debug.push_back(co);
            return true;
        }, OrderingHint::Natural, cfg);
    }

    REQUIRE(leaves_no_debug.size() == leaves_with_debug.size());
    REQUIRE(captured_debug.size() == leaves_with_debug.size());

    // Build sorted multisets by (hash, prob) and compare.
    auto to_multiset = [](const std::vector<ChildOutcome>& v) {
        std::vector<std::pair<uint64_t,double>> ms;
        ms.reserve(v.size());
        for (const auto& c : v)
            ms.push_back({state_hash_solver(c.child), c.prob});
        std::sort(ms.begin(), ms.end());
        return ms;
    };
    REQUIRE(to_multiset(leaves_no_debug) == to_multiset(leaves_with_debug));

    // Each leaf must have non-empty path
    for (const auto& dbg : captured_debug)
        REQUIRE_FALSE(dbg.path.empty());
}

// ---------------------------------------------------------------------------
// Test 4: AI-action attribution — captured leaves grouped by the new ai_action
// field partition the leaf set; every leaf carries a valid action; grouping
// matches the AI support set from cpp_compute_action_probabilities.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: ai_action attribution partitions leaf set by support",
          "[bucket][attribution]")
{
    // Use Tackle (player) vs two-move opp (Tackle + Splash) so AI has 2 support actions.
    // Player faster: speed0=80, speed1=60.
    // Opp has Tackle (33) slot0 and Splash (150) slot1 → 2 distinct AI actions.
    BattleState s{};
    PokemonState mon{};
    mon.species    = 1; mon.level = 50; mon.has_stats = true;
    mon.stat_hp    = 200; mon.stat_atk = 100; mon.stat_def = 80;
    mon.stat_spa   = 80;  mon.stat_spd = 80;  mon.stat_spe = 80;
    mon.has_max_hp = true; mon.max_hp = 200; mon.has_hp = true; mon.hp = 200;
    mon.move_id0 = 33; mon.move_pp0 = 35;
    s.side0.team.push_back(mon); s.side0.active_indices.push_back(0);

    PokemonState opp{};
    opp.species    = 2; opp.level = 50; opp.has_stats = true;
    opp.stat_hp    = 200; opp.stat_atk = 100; opp.stat_def = 80;
    opp.stat_spa   = 80;  opp.stat_spd = 80;  opp.stat_spe = 60;
    opp.has_max_hp = true; opp.max_hp = 200; opp.has_hp = true; opp.hp = 200;
    opp.move_id0 = 33; opp.move_pp0 = 35;
    opp.move_id1 = 150; opp.move_pp1 = 40;  // Splash
    opp.ability = 75;  // Shell Armor: no crits
    s.side1.team.push_back(opp); s.side1.active_indices.push_back(0);
    s.turn_number = 1;

    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Collect with debug callback
    std::vector<ChildOutcome> leaves;
    std::vector<LeafDebugInfo> debug_infos;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            debug_infos.push_back(dbg);
        };
        oracle.step(s, pa, [&](ChildOutcome co) -> bool {
            leaves.push_back(co);
            return true;
        }, OrderingHint::Natural, cfg);
    }

    REQUIRE(leaves.size() == debug_infos.size());
    REQUIRE_FALSE(debug_infos.empty());

    // Every leaf must have a valid ai_action (kind must be 0 or a valid switch kind).
    for (const auto& dbg : debug_infos) {
        // ai_action.kind==0 means move action
        REQUIRE(dbg.ai_action.kind == 0);
        // prob must be in (0,1]
        REQUIRE(dbg.ai_action_prob > 0.0);
        REQUIRE(dbg.ai_action_prob <= 1.0 + 1e-9);
    }

    // Leaves must partition by ai_action: groups sum to total leaf count.
    // Get AI support from cpp_compute_action_probabilities.
    std::vector<ActionProb> support = cpp_compute_action_probabilities(s, 1);
    REQUIRE(support.size() >= 2);  // Tackle + Splash at minimum

    // Group leaves by ai_action move_slot.
    std::unordered_map<int, int> slot_count;
    for (const auto& dbg : debug_infos)
        slot_count[dbg.ai_action.move_slot]++;

    // Every support action's slot must appear in the leaf groups.
    for (const auto& ap : support) {
        if (ap.prob > 0.0) {
            REQUIRE(slot_count.count(ap.action.move_slot) > 0);
        }
    }

    // Total leaf count equals sum of group sizes (trivially true but confirms no orphans).
    int total_counted = 0;
    for (const auto& kv : slot_count) total_counted += kv.second;
    REQUIRE(total_counted == static_cast<int>(leaves.size()));

    // Structural partition properties (magic-number leaf counts are avoided because
    // aggregated damage rolls collapse to distinct-value groups and opponent-side
    // attacks contribute additional branch points: player Tackle vs Shell-Armor opp
    // = DAMAGE_ROLL only; opp Tackle back = CRIT × DAMAGE_ROLL; opp Splash = no branch).
    // The invariants that MUST hold:
    //   (1) Every AI support action with p>0 appears in slot_count.
    //   (2) Every leaf's ai_action.move_slot is in the support set.
    //   (3) Leaves partition exactly by ai_action (already checked via total_counted).
    std::unordered_map<int, double> support_by_slot;
    for (const auto& ap : support) support_by_slot[ap.action.move_slot] = ap.prob;
    for (const auto& kv : slot_count) {
        REQUIRE(support_by_slot.count(kv.first) > 0);
        REQUIRE(support_by_slot[kv.first] > 0.0);
    }
}

// ---------------------------------------------------------------------------
// Test 1: Capture-and-replay identity.
// Run step() with debug capture; for each (ai_action, path), call replay_path
// from the same state → child must be bit-identical to the captured leaf's child.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: capture-and-replay identity",
          "[bucket][replay][identity]")
{
    // Tackle (player, Shell Armor opponent) → 16 deterministic leaves per AI action.
    // Use single AI action (Splash) to keep leaf count manageable.
    BattleState s = make_basic_state(80, 60, 33, 150, 0, 0, 0, 75);
    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Capture leaves and debug info
    std::vector<ChildOutcome> leaves;
    std::vector<LeafDebugInfo> debug_infos;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            debug_infos.push_back(dbg);
        };
        oracle.step(s, pa, [&](ChildOutcome co) -> bool {
            leaves.push_back(co);
            return true;
        }, OrderingHint::Natural, cfg);
    }

    REQUIRE(leaves.size() == debug_infos.size());
    REQUIRE_FALSE(leaves.empty());

    // For each captured leaf, replay_path must produce a child identical to the captured child.
    for (size_t i = 0; i < leaves.size(); ++i) {
        const LeafDebugInfo& dbg = debug_infos[i];
        const BattleState& expected_child = leaves[i].child;

        // replay_path signature:
        //   ReplayResult replay_path(BattleState, ExecAction player, ExecAction ai,
        //                            std::vector<LeafPathEntry> prefix) const;
        // Returns: {child: BattleState, observed_sequence: vector<LeafPathEntry>}
        // Throws on divergence.
        ReplayResult rr = oracle.replay_path(s, pa, dbg.ai_action, dbg.path);

        REQUIRE(state_equal_solver(rr.child, expected_child));
    }
}

// ---------------------------------------------------------------------------
// Test 2: Tamper — mutate one prefix entry's event/option → replay_path throws.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: tampered prefix throws",
          "[bucket][replay][tamper]")
{
    BattleState s = make_basic_state(80, 60, 33, 150, 0, 0, 0, 75);
    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Capture first leaf
    std::vector<LeafDebugInfo> debug_infos;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            if (debug_infos.empty()) debug_infos.push_back(dbg);  // first leaf only
        };
        oracle.step(s, pa, [&](ChildOutcome) -> bool {
            return debug_infos.empty();  // abort after first leaf
        }, OrderingHint::Natural, cfg);
    }

    REQUIRE_FALSE(debug_infos.empty());
    LeafDebugInfo dbg = debug_infos[0];

    // We need at least one path entry to tamper with.
    REQUIRE_FALSE(dbg.path.empty());

    // Tamper: flip the value of the first entry to something different.
    // For a DAMAGE_ROLL entry (value = roll index 0..15), change value by ±1 mod 16.
    // For any other event, just flip value bit.
    std::vector<LeafPathEntry> tampered = dbg.path;
    tampered[0].value = (tampered[0].value + 1) % 16;  // shift value by 1

    // replay_path must throw std::runtime_error naming the divergence.
    REQUIRE_THROWS_AS(oracle.replay_path(s, pa, dbg.ai_action, tampered),
                      std::runtime_error);
}

// ---------------------------------------------------------------------------
// Test 3: Divergence — Sitrus Berry fires extra events when HP drops below 50%.
// Capture a path on a state where opp HP is ABOVE the Sitrus threshold after the hit
// (berry does NOT fire); replay from a state where the hit drops opp BELOW threshold
// (berry fires → extra branch-point events) → throws, diagnostic names the diverging event.
//
// Sitrus Berry (item 158 from item lookup): fires when HP <= max_hp / 2.
// Setup: opp max_hp=200, threshold=100.
// State A (capture): opp hp=160. Tackle deals ~10-20 dmg → ends at ~140-150, above 100. No berry.
// State B (replay):  opp hp=115. Tackle deals ~10-20 dmg → ends at ~95-105, CROSSES threshold.
//                    Berry fires → extra Cat-B draw → sequence longer → throw.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: Sitrus berry divergence throws with diagnostic",
          "[bucket][replay][divergence]")
{
    // Item IDs: Sitrus Berry
    static constexpr int32_t ITEM_SITRUS_BERRY = 158;

    // State A: opp at hp=160 → Tackle (10-20 dmg) keeps opp well above 100.
    BattleState state_a = make_basic_state(
        80, 60,
        33,    // player: Tackle
        150,   // opp: Splash (deterministic, so only player Tackle has damage roll)
        0, ITEM_SITRUS_BERRY,  // opp holds Sitrus
        0, 75,                 // opp has Shell Armor (no crit, simplifies path)
        160, 200               // opp_hp=160, player_hp=200
    );

    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Capture one path from state A (berry does not fire).
    std::vector<LeafDebugInfo> captured;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            if (captured.empty()) captured.push_back(dbg);
        };
        oracle.step(state_a, pa, [&](ChildOutcome) -> bool {
            return captured.empty();
        }, OrderingHint::Natural, cfg);
    }

    REQUIRE_FALSE(captured.empty());

    // State B: opp at hp=110 → Tackle deals enough to cross 100 → Sitrus fires.
    BattleState state_b = make_basic_state(
        80, 60,
        33, 150,
        0, ITEM_SITRUS_BERRY,
        0, 75,
        110, 200  // opp_hp=110 (will cross 100 threshold)
    );

    // Replay state_A's path on state_B: on state_b the berry fires (opp hp crosses the
    // Sitrus 50% threshold), so the observed HP change no longer matches the pure-shift
    // implied by the prefix's DAMAGE_ROLL entries — replay_path's shift-property check
    // detects the divergence and throws.
    bool threw = false;
    try {
        oracle.replay_path(state_b, pa, captured[0].ai_action, captured[0].path);
    } catch (const std::runtime_error& e) {
        threw = true;
        // Diagnostic must mention the diverging event (some event ID or description).
        std::string what = e.what();
        REQUIRE_FALSE(what.empty());
    }
    // Note: if the min-damage roll on the first path happens to not cross threshold on
    // state_b either (unlikely with max_hp=200, threshold=100, hp=110, ~10 dmg min),
    // this test is conservative and won't throw.  We assert the throw was expected.
    // For the test to be reliable we need to ensure the damage DOES cross. At level 50,
    // Tackle deals approximately 10-18 damage, so hp=110 - 10 = 100 = exactly threshold
    // (border case). Use hp=115 to ensure crossing: 115 - 10 = 105 > 100 (no fire);
    // but 115 - 15 = 100 (fire). Since the FIRST captured path is the smallest roll,
    // and the smallest roll gives ~10 dmg, 115-10=105 > 100: might NOT fire.
    // Use hp=105: 105 - 10 = 95 < 100 → ALWAYS fires even on min roll.
    // Re-do with hp=105:
    BattleState state_b2 = make_basic_state(
        80, 60, 33, 150, 0, ITEM_SITRUS_BERRY, 0, 75, 105, 200
    );
    REQUIRE_THROWS_AS(
        oracle.replay_path(state_b2, pa, captured[0].ai_action, captured[0].path),
        std::runtime_error
    );
}

// ---------------------------------------------------------------------------
// Observed sequence content: replay_path returns dmg_by_roll group structure
// for DAMAGE_ROLL events in the observed sequence.
// ---------------------------------------------------------------------------

TEST_CASE("bucket replay: observed sequence contains damage group info for DAMAGE_ROLL",
          "[bucket][replay][observed_seq]")
{
    // Tackle with Shell Armor → no crit, just 16 roll branches (aggregated to distinct dmg).
    // Use aggregate=false equivalent: replay_path returns the full unaggregated sequence.
    // For a DAMAGE_ROLL entry in the sequence, has_dmg_by_roll must be true with real values.
    BattleState s = make_basic_state(80, 60, 33, 150, 0, 0, 0, 75);
    ExecAction pa = player_move_action(0);
    TransitionOracle oracle;

    // Capture first path
    std::vector<LeafDebugInfo> captured;
    {
        TransitionOracle::Config cfg;
        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            if (captured.empty()) captured.push_back(dbg);
        };
        oracle.step(s, pa, [&](ChildOutcome) -> bool {
            return captured.empty();
        }, OrderingHint::Natural, cfg);
    }
    REQUIRE_FALSE(captured.empty());

    ReplayResult rr = oracle.replay_path(s, pa, captured[0].ai_action, captured[0].path);

    // The observed sequence must include a DAMAGE_ROLL entry.
    bool found_dmg = false;
    static constexpr int EV_DAMAGE_ROLL = 5;  // RngEventC::DAMAGE_ROLL = 5
    for (const auto& entry : rr.observed_sequence) {
        if (entry.event == EV_DAMAGE_ROLL) {
            found_dmg = true;
            // Must carry damage group structure.
            REQUIRE(entry.has_dmg_by_roll);
            // dmg_by_roll[0..15] must contain non-negative values.
            for (int i = 0; i < 16; ++i)
                REQUIRE(entry.dmg_by_roll[i] >= 0);
        }
    }
    REQUIRE(found_dmg);
}
