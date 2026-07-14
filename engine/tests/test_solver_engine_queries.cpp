// Catch2 tests for Task 4: read-only engine queries — damage tables and HP-threshold sets.
// Tests are tagged [engine_queries]. Run with: nuzlocke_native_tests "[engine_queries]"
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>

#include "solver/engine_queries.h"
#include "solver/transition_oracle.h"
#include "logger.h"
#include "move_exec.h"
#include "state.h"
#include "state_eq.h"

#include <cmath>
#include <cstdint>
#include <set>
#include <unordered_set>
#include <vector>

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

static constexpr int32_t AB_SHELL_ARMOR   = 75;    // suppresses crits
static constexpr int32_t AB_STURDY        = 5;
static constexpr int32_t AB_MULTISCALE    = 136;
static constexpr int32_t AB_SHADOW_SHIELD = 231;
static constexpr int32_t AB_NONE         = 0;

static constexpr int32_t ITEM_NONE       = 0;
static constexpr int32_t ITEM_FOCUS_SASH = 275;
static constexpr int32_t ITEM_SITRUS     = 158;
static constexpr int32_t ITEM_CUSTAP     = 210;    // Quarter threshold
static constexpr int32_t ITEM_LIECHI     = 201;    // Quarter threshold
static constexpr int32_t ITEM_LUM        = 157;    // status berry — unrecognized consumable

// TACKLE = move 33: Normal, Physical, 40 BP, 100% acc, single-hit, no secondary.
static constexpr int32_t MOVE_TACKLE     = 33;
// ROCK_BLAST = move 350: Rock, Physical, 25 BP, 90% acc, 2-5 hits.
static constexpr int32_t MOVE_ROCK_BLAST = 350;
// Scratch = move 10: Normal, Physical, 40 BP, 100% acc, single-hit (similar to Tackle).
static constexpr int32_t MOVE_SCRATCH    = 10;

// Make a basic 1v1 state. Both sides have Shell Armor by default (suppresses crits
// for the context-change tests where we don't want crit complications).
static BattleState make_basic_state(
        int32_t move_id0   = MOVE_TACKLE,
        int32_t move_id1   = MOVE_TACKLE,
        int32_t ability0   = AB_SHELL_ARMOR,
        int32_t ability1   = AB_SHELL_ARMOR,
        int32_t item0      = ITEM_NONE,
        int32_t item1      = ITEM_NONE,
        int32_t speed0     = 100,
        int32_t speed1     = 60,
        int32_t atk0       = 80,
        int32_t def1       = 80,
        int32_t max_hp0    = 200,
        int32_t max_hp1    = 200) {
    BattleState s{};

    PokemonState p0{};
    p0.species = 1; p0.level = 50;
    p0.has_stats = true;
    p0.stat_hp  = max_hp0; p0.stat_atk = atk0; p0.stat_def = def1;
    p0.stat_spa = 60;      p0.stat_spd = 60;   p0.stat_spe = speed0;
    p0.has_max_hp = true;  p0.max_hp = max_hp0;
    p0.has_hp = true;      p0.hp    = max_hp0;
    p0.move_id0 = move_id0; p0.move_pp0 = 35;
    p0.ability = ability0;
    p0.item = item0;
    s.side0.team.push_back(p0);
    s.side0.active_indices.push_back(0);

    PokemonState p1{};
    p1.species = 2; p1.level = 50;
    p1.has_stats = true;
    p1.stat_hp  = max_hp1; p1.stat_atk = atk0; p1.stat_def = def1;
    p1.stat_spa = 60;      p1.stat_spd = 60;   p1.stat_spe = speed1;
    p1.has_max_hp = true;  p1.max_hp = max_hp1;
    p1.has_hp = true;      p1.hp    = max_hp1;
    p1.move_id0 = move_id1; p1.move_pp0 = 35;
    p1.ability = ability1;
    p1.item = item1;
    s.side1.team.push_back(p1);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;
    return s;
}

// Build a ExecAction for move slot 0.
static ExecAction move_action(int32_t slot = 0) {
    ExecAction a{};
    a.kind = 0;
    a.move_slot = slot;
    return a;
}

// ---------------------------------------------------------------------------
// Test 1 — Oracle cross-check (the key test).
// Build a matchup where the player uses Tackle (100% acc, no secondary, single-hit).
// Use Shell Armor on BOTH sides to suppress crits — this gives us a clean pure
// noncrit distribution. Then separately verify crit > noncrit in Test 4.
// Assert every oracle child's HP delta appears in tbl.noncrit, and vice versa.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: oracle cross-check — damage table values match oracle children",
          "[engine_queries]") {
    // Shell Armor on both → no crit branch, pure noncrit distribution.
    // atk=120, def=80 so damage varies meaningfully over the 16 rolls.
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_SHELL_ARMOR, AB_SHELL_ARMOR,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60,  // player faster (speed0=100, speed1=60)
                                      120, 80,  // atk0=120, def1=80
                                      300, 300);

    ExecAction action = move_action(0);
    DamageTable tbl = damage_table(s, 0, action);  // attacker side=0

    // Collect oracle children's HP deltas (opponent HP change = player damage).
    TransitionOracle oracle;
    TransitionOracle::Config cfg{};
    cfg.max_leaves = 1'000'000;

    std::set<int32_t> oracle_deltas;
    int32_t opp_start_hp = s.side1.team[0].hp;

    OracleEmitFn emit = [&](ChildOutcome co) -> bool {
        int32_t delta = opp_start_hp - co.child.side1.team[0].hp;
        if (delta > 0) oracle_deltas.insert(delta);  // ignore 0-delta (opp attacked player)
        return true;
    };

    oracle.step(s, action, emit, OrderingHint::Natural, cfg);

    REQUIRE_FALSE(oracle_deltas.empty());

    // Every oracle-seen delta must appear in tbl.noncrit (Shell Armor → no crits).
    for (int32_t d : oracle_deltas) {
        bool found = false;
        for (int32_t v : tbl.noncrit) if (v == d) { found = true; break; }
        INFO("oracle delta " << d << " not in table noncrit");
        REQUIRE(found);
    }

    // Converse: every table noncrit value must appear in oracle output.
    // Tackle has 100% accuracy → no miss branch → all values appear.
    for (int32_t v : tbl.noncrit) {
        if (v == 0) continue;  // skip 0 if present (shouldn't be for non-immune)
        bool found = oracle_deltas.count(v) > 0;
        INFO("table noncrit value " << v << " not seen in oracle children");
        REQUIRE(found);
    }

    // immune flag must be false (no type set → effectiveness=1.0).
    REQUIRE_FALSE(tbl.immune);

    // Single-hit move.
    REQUIRE(tbl.max_hits == 1);
    REQUIRE(tbl.hit_count_support.size() == 1);
    REQUIRE(tbl.hit_count_support[0] == 1);

    // Crit table should match noncrit table exactly when Shell Armor suppresses crits
    // (crit_override=1 still runs through the formula — but Shell Armor ability prevents
    // crits from landing in actual play, while damage_table still evaluates the formula
    // with crit_override=1 regardless of ability).
    // Rather, just assert immune=false and single-hit structure.
    REQUIRE_FALSE(tbl.noncrit.empty());
}

// ---------------------------------------------------------------------------
// Test 2 — Context sensitivity.
// A burn on the attacker, a Reflect screen on the defender, and an attack boost
// each change the noncrit table vs the clean fixture.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: context sensitivity — burn/screen/boost change the table",
          "[engine_queries]") {
    // Baseline: clean state
    BattleState base = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                         AB_SHELL_ARMOR, AB_SHELL_ARMOR,
                                         ITEM_NONE, ITEM_NONE,
                                         100, 60, 120, 60, 300, 300);
    ExecAction action = move_action(0);

    DamageTable baseline_tbl = damage_table(base, 0, action);
    REQUIRE_FALSE(baseline_tbl.noncrit.empty());

    // Subtest A: burn on attacker halves physical damage.
    {
        BattleState burned = base;
        burned.side0.team[0].status = 1;  // STATUS_BURN=1
        DamageTable burned_tbl = damage_table(burned, 0, action);
        // Burn halves physical damage — min(burned) < min(baseline)
        REQUIRE(burned_tbl.noncrit.front() < baseline_tbl.noncrit.front());
    }

    // Subtest B: Reflect on defender's side halves physical damage in deterministic mode.
    {
        BattleState screened = base;
        SideConditionEntry sc{};
        sc.condition = 1;  // SC_REFLECT=1
        sc.turns     = 5;
        screened.side1.side_conditions.push_back(sc);
        // Need a non-null def_side_idx for screens to apply → pass side=0 (defender = side1).
        DamageTable screen_tbl = damage_table(screened, 0, action);
        // Reflect halves physical damage.
        REQUIRE(screen_tbl.noncrit.front() < baseline_tbl.noncrit.front());
    }

    // Subtest C: +1 attack boost on attacker increases damage.
    // ATK stat_idx=1 → stage_idx=0 → PokemonState.stage0 (damage.cpp:584-588).
    {
        BattleState boosted = base;
        boosted.side0.team[0].stage0 = 1;  // +1 ATK stage (stage0 = ATK stage)
        DamageTable boosted_tbl = damage_table(boosted, 0, action);
        REQUIRE(boosted_tbl.noncrit.back() > baseline_tbl.noncrit.back());
    }
}

// ---------------------------------------------------------------------------
// Test 3 — Immune matchup.
// Normal-type move vs Ghost-type defender → all-zero rolls + immune=true.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: immune matchup — Normal vs Ghost immune flag",
          "[engine_queries]") {
    // Explicitly set Ghost type on the defender so type immunity applies.
    // PokemonState.types is not auto-populated from species; must be set manually.
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_SHELL_ARMOR, AB_SHELL_ARMOR);
    // Give defender Ghost type explicitly (TYPE_GHOST=13 from damage.cpp constants).
    s.side1.team[0].has_types = true;
    s.side1.team[0].types.push_back(13);  // TYPE_GHOST=13

    ExecAction action = move_action(0);
    DamageTable tbl = damage_table(s, 0, action);  // Normal Tackle vs Ghost

    REQUIRE(tbl.immune);
    // Immune → all entries zero or empty, or just {0}.
    for (int32_t v : tbl.noncrit) REQUIRE(v == 0);
    for (int32_t v : tbl.crit)    REQUIRE(v == 0);
}

// ---------------------------------------------------------------------------
// Test 4 — Crit list ≥ noncrit list pointwise.
// For any move, crit always deals at least as much damage as noncrit
// at the same roll index (min(crit) ≥ min(noncrit), max(crit) ≥ max(noncrit)).
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: crit values >= noncrit values pointwise",
          "[engine_queries]") {
    // No Shell Armor so crit branch exists.
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 300, 300);
    ExecAction action = move_action(0);
    DamageTable tbl = damage_table(s, 0, action);

    REQUIRE_FALSE(tbl.immune);
    REQUIRE_FALSE(tbl.noncrit.empty());
    REQUIRE_FALSE(tbl.crit.empty());

    // min(crit) >= min(noncrit)
    REQUIRE(tbl.crit.front() >= tbl.noncrit.front());
    // max(crit) >= max(noncrit)
    REQUIRE(tbl.crit.back() >= tbl.noncrit.back());

    // Pointwise when equal length: crit[i] >= noncrit[i].
    if (tbl.crit.size() == tbl.noncrit.size()) {
        for (size_t i = 0; i < tbl.crit.size(); ++i) {
            INFO("index " << i << ": crit=" << tbl.crit[i] << " noncrit=" << tbl.noncrit[i]);
            REQUIRE(tbl.crit[i] >= tbl.noncrit[i]);
        }
    }
}

// ---------------------------------------------------------------------------
// Test 5 — Multi-hit move (Rock Blast).
// max_hits > 1 and hit_count_support matches the engine's (2,5) distribution.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: multi-hit move — Rock Blast metadata",
          "[engine_queries]") {
    // Rock Blast: min_hits=2, max_hits=5 (from MOVE_TABLE).
    // Using type Rock (move 350) vs a non-Rock, non-Ghost defender to avoid immunity.
    BattleState s = make_basic_state(MOVE_ROCK_BLAST, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 300, 300);
    ExecAction action = move_action(0);
    DamageTable tbl = damage_table(s, 0, action);

    REQUIRE(tbl.max_hits == 5);
    // hit_count_support for (2,5) = {2,3,4,5} (all possible values).
    std::set<int> support(tbl.hit_count_support.begin(), tbl.hit_count_support.end());
    REQUIRE(support.count(2) == 1);
    REQUIRE(support.count(3) == 1);
    REQUIRE(support.count(4) == 1);
    REQUIRE(support.count(5) == 1);
    REQUIRE(support.size() == 4);
}

// ---------------------------------------------------------------------------
// Test 5b — Skill Link: Rock Blast with Skill Link → always 5 hits.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: multi-hit with Skill Link — always max hits",
          "[engine_queries]") {
    static constexpr int32_t AB_SKILL_LINK = 92;
    BattleState s = make_basic_state(MOVE_ROCK_BLAST, MOVE_TACKLE,
                                      AB_SKILL_LINK, AB_NONE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 300, 300);
    ExecAction action = move_action(0);
    DamageTable tbl = damage_table(s, 0, action);

    REQUIRE(tbl.max_hits == 5);
    REQUIRE(tbl.hit_count_support.size() == 1);
    REQUIRE(tbl.hit_count_support[0] == 5);
}

// ---------------------------------------------------------------------------
// Test 6 — Thresholds.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: thresholds — Sitrus Berry holder", "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_SITRUS,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);  // side 1 holds Sitrus

    // Sitrus: threshold = max_hp / 2 = 100, kind = Half.
    // Engine trigger: mon.hp <= max_hp / 2 (floor division; check_berry line 442).
    REQUIRE_FALSE(th.residual_unknown);
    bool found_sitrus = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::Half && t.threshold_hp == 100) {
            found_sitrus = true;
        }
    }
    REQUIRE(found_sitrus);
}

TEST_CASE("engine_queries: thresholds — Focus Sash at full HP", "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_FOCUS_SASH,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);

    REQUIRE_FALSE(th.residual_unknown);
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::FullHp && t.threshold_hp == 200) {
            found = true;
        }
    }
    REQUIRE(found);
}

TEST_CASE("engine_queries: thresholds — Sturdy ability", "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_STURDY,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);

    REQUIRE_FALSE(th.residual_unknown);
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::FullHp && t.threshold_hp == 200) {
            found = true;
        }
    }
    REQUIRE(found);
}

TEST_CASE("engine_queries: thresholds — no items/abilities → empty, no unknown",
          "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th0 = hp_thresholds(s, 0);
    HpThresholds th1 = hp_thresholds(s, 1);

    REQUIRE(th0.thresholds.empty());
    REQUIRE_FALSE(th0.residual_unknown);
    REQUIRE(th1.thresholds.empty());
    REQUIRE_FALSE(th1.residual_unknown);
}

TEST_CASE("engine_queries: thresholds — Lum Berry → residual_unknown=true",
          "[engine_queries]") {
    // Lum Berry (157) is a status-curing berry the engine will consume,
    // but hp_thresholds doesn't model it → residual_unknown=true.
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_LUM,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);
    REQUIRE(th.residual_unknown);
}

TEST_CASE("engine_queries: thresholds — Custap Berry → Quarter threshold",
          "[engine_queries]") {
    // Custap Berry (210): triggers at max_hp / 4.
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_CUSTAP,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);

    REQUIRE_FALSE(th.residual_unknown);
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::Quarter && t.threshold_hp == 50) {
            found = true;
        }
    }
    REQUIRE(found);
}

TEST_CASE("engine_queries: thresholds — Multiscale → FullHp threshold",
          "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_MULTISCALE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);

    REQUIRE_FALSE(th.residual_unknown);
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::FullHp && t.threshold_hp == 200) {
            found = true;
        }
    }
    REQUIRE(found);
}

// ---------------------------------------------------------------------------
// Test 7 — Purity: attaching an AnalyticalRngLog and CategoryBOccurrenceCounters
// shows the log stays EMPTY and counters are untouched after both queries.
// Also verifies the BattleState is bit-identical after the calls.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: purity — no RNG consumption, state unchanged",
          "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_NONE,
                                      100, 60, 120, 80, 300, 300);
    ExecAction action = move_action(0);

    // Snapshot the state before.
    BattleState s_before = s;

    // Attach a log sink.
    AnalyticalRngLog log;
    set_analytical_rng_log(&log);

    // Attach occurrence counters.
    CategoryBOccurrenceCounters counters{};
    set_catb_occ_counters(&counters);

    // Run both queries.
    DamageTable tbl = damage_table(s, 0, action);
    HpThresholds th = hp_thresholds(s, 0);

    // Detach.
    set_analytical_rng_log(nullptr);
    set_catb_occ_counters(nullptr);

    // Log must be empty — no RNG draws logged.
    INFO("log has " << log.size() << " entries");
    REQUIRE(log.size() == 0);

    // Counters must be zero — no occurrence bumps.
    bool any_nonzero = false;
    for (size_t i = 0; i < CategoryBOccurrenceCounters::MAX_EVENTS; ++i) {
        if (counters.counts[i] != 0) { any_nonzero = true; break; }
    }
    REQUIRE_FALSE(any_nonzero);

    // State bit-identical after queries.
    REQUIRE(state_equal_solver(s, s_before));
}

// ---------------------------------------------------------------------------
// Test 8 — Invalid input: throw on malformed inputs.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: invalid input — non-move action throws",
          "[engine_queries]") {
    BattleState s = make_basic_state();

    ExecAction switch_action{};
    switch_action.kind = 1;  // SWITCH
    switch_action.switch_to_slot = 1;

    REQUIRE_THROWS_AS(damage_table(s, 0, switch_action), std::invalid_argument);
}

TEST_CASE("engine_queries: invalid input — no active on side throws",
          "[engine_queries]") {
    BattleState s = make_basic_state();
    s.side0.active_indices.clear();  // remove the active mon

    ExecAction action = move_action(0);
    REQUIRE_THROWS_AS(damage_table(s, 0, action), std::invalid_argument);
}

TEST_CASE("engine_queries: invalid input — invalid side index throws",
          "[engine_queries]") {
    BattleState s = make_basic_state();
    ExecAction action = move_action(0);
    REQUIRE_THROWS_AS(damage_table(s, 2, action), std::invalid_argument);
    REQUIRE_THROWS_AS(hp_thresholds(s, 2), std::invalid_argument);
}

// ---------------------------------------------------------------------------
// Test 9 — Focus Sash NOT triggered when HP is not full.
// When the holder is at less than full HP, Focus Sash gives no protection.
// The threshold should not be included.
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: thresholds — Focus Sash not at full HP → not included",
          "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_FOCUS_SASH,
                                      100, 60, 120, 80, 200, 200);
    // Reduce HP below max
    s.side1.team[0].hp = 150;

    HpThresholds th = hp_thresholds(s, 1);
    REQUIRE_FALSE(th.residual_unknown);
    // Sash is only active at full HP; since hp < max_hp, no FullHp threshold.
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::FullHp) found = true;
    }
    REQUIRE_FALSE(found);
}

// ---------------------------------------------------------------------------
// Test 10 — Liechi Berry → Quarter threshold (pinch stat berry).
// ---------------------------------------------------------------------------

TEST_CASE("engine_queries: thresholds — Liechi Berry → Quarter threshold",
          "[engine_queries]") {
    BattleState s = make_basic_state(MOVE_TACKLE, MOVE_TACKLE,
                                      AB_NONE, AB_NONE,
                                      ITEM_NONE, ITEM_LIECHI,
                                      100, 60, 120, 80, 200, 200);
    HpThresholds th = hp_thresholds(s, 1);

    REQUIRE_FALSE(th.residual_unknown);
    bool found = false;
    for (const auto& t : th.thresholds) {
        if (t.kind == ThresholdKind::Quarter && t.threshold_hp == 50) {
            found = true;
        }
    }
    REQUIRE(found);
}
