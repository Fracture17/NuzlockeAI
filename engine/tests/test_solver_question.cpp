// Tests for Task 4: Question struct, classify(), and action_filter().
// Covers terminal classification under various Question configurations, early-fail
// for monotone keepItem (disabled — Harvest can restore; see question.cpp), and
// banMove action filtering.
#include <catch2/catch_test_macros.hpp>

#include <stdexcept>

#include "state.h"
#include "move_exec.h"
#include "solver/question.h"

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

// Minimal 1v1 BattleState. Both actives alive by default (hp=100).
static BattleState make_q_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    mon.move_id0 = 33; mon.move_pp0 = 35;
    mon.move_id1 = 85; mon.move_pp1 = 15;
    mon.move_id2 = 10; mon.move_pp2 = 20;
    mon.move_id3 = 55; mon.move_pp3 = 25;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    return s;
}

// Mark active as fainted.
static void faint(BattleState& s, int side_idx) {
    auto& team = (side_idx == 0 ? s.side0 : s.side1).team;
    team[0].hp = 0;
    team[0].fainted = true;
}

// Build a MOVE action for the given slot.
static ExecAction move_action(int slot) {
    ExecAction a{};
    a.kind = 0;  // MOVE
    a.move_slot = slot;
    return a;
}

// Struggle sentinel: move_slot = -2.
static ExecAction struggle_action() {
    ExecAction a{};
    a.kind = 0;
    a.move_slot = -2;
    a.move_override = 165;
    return a;
}

// ---------------------------------------------------------------------------
// Section 1: Default question — 4 terminal faint combos
// ---------------------------------------------------------------------------

TEST_CASE("classify: default question, opponent fainted only -> WIN",
          "[question][terminal][default]") {
    BattleState s = make_q_state();
    faint(s, 1);  // opponent fainted; player alive
    Question q{};  // requireOppFaint=true, requireNoFaint=true
    REQUIRE(classify(s, q) == Outcome::WIN);
}

TEST_CASE("classify: default question, player fainted only -> LOSS",
          "[question][terminal][default]") {
    BattleState s = make_q_state();
    faint(s, 0);  // player fainted; opponent alive
    Question q{};
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

TEST_CASE("classify: default question, both fainted -> LOSS",
          "[question][terminal][default]") {
    BattleState s = make_q_state();
    faint(s, 0);
    faint(s, 1);
    Question q{};
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

TEST_CASE("classify: default question, neither fainted -> CONTINUE",
          "[question][terminal][default]") {
    BattleState s = make_q_state();
    Question q{};
    REQUIRE(classify(s, q) == Outcome::CONTINUE);
}

// ---------------------------------------------------------------------------
// Section 2: requireNoFaint=false combos
// ---------------------------------------------------------------------------

TEST_CASE("classify: requireNoFaint=false, both fainted -> WIN",
          "[question][terminal][no_faint_false]") {
    BattleState s = make_q_state();
    faint(s, 0);
    faint(s, 1);
    Question q{};
    q.requireNoFaint = false;
    REQUIRE(classify(s, q) == Outcome::WIN);
}

TEST_CASE("classify: requireNoFaint=false, player fainted only -> LOSS (opp not fainted)",
          "[question][terminal][no_faint_false]") {
    BattleState s = make_q_state();
    faint(s, 0);  // player fainted; opponent alive
    Question q{};
    q.requireNoFaint = false;
    // requireOppFaint=true but opponent alive at terminal -> LOSS
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

// ---------------------------------------------------------------------------
// Section 3: keepItem — terminal WIN/LOSS and non-terminal behavior
// ---------------------------------------------------------------------------

// Item int value 185 = Sitrus Berry (arbitrary non-zero for testing).
constexpr int32_t TEST_BERRY_ITEM = 185;

TEST_CASE("classify: keepItem, terminal, item held -> WIN",
          "[question][keepItem][terminal]") {
    BattleState s = make_q_state();
    s.side0.team[0].item = TEST_BERRY_ITEM;  // item still held
    s.side0.team[0].consumed_berry = 0;       // not consumed
    faint(s, 1);
    Question q{};
    q.keepItem = TEST_BERRY_ITEM;
    REQUIRE(classify(s, q) == Outcome::WIN);
}

TEST_CASE("classify: keepItem, terminal, berry consumed (consumed_berry set) -> LOSS",
          "[question][keepItem][terminal]") {
    BattleState s = make_q_state();
    s.side0.team[0].item = 0;                  // item gone from slot
    s.side0.team[0].consumed_berry = TEST_BERRY_ITEM;  // consumed
    faint(s, 1);
    Question q{};
    q.keepItem = TEST_BERRY_ITEM;
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

// keepItem is a positive terminal-state assertion: a Harvest-restored berry counts
// as kept (the item carries into the next fight); a different item (Trick) fails it.
TEST_CASE("classify: keepItem, terminal, Harvest-restored berry (consumed_berry set, item back) -> WIN",
          "[question][keepItem][terminal]") {
    BattleState s = make_q_state();
    s.side0.team[0].item = TEST_BERRY_ITEM;             // restored by Harvest
    s.side0.team[0].consumed_berry = TEST_BERRY_ITEM;   // was consumed earlier
    faint(s, 1);
    Question q{};
    q.keepItem = TEST_BERRY_ITEM;
    REQUIRE(classify(s, q) == Outcome::WIN);
}

TEST_CASE("classify: keepItem, terminal, different item held (Trick swap) -> LOSS",
          "[question][keepItem][terminal]") {
    BattleState s = make_q_state();
    s.side0.team[0].item = TEST_BERRY_ITEM + 1;  // some other item
    s.side0.team[0].consumed_berry = 0;
    faint(s, 1);
    Question q{};
    q.keepItem = TEST_BERRY_ITEM;
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

// Harvest CAN restore consumed items (residuals.cpp:373), so keepItem is NOT
// monotone. Non-terminal with consumed berry must return CONTINUE, not early LOSS.
TEST_CASE("classify: keepItem, non-terminal, berry consumed -> CONTINUE (not early LOSS; Harvest exists)",
          "[question][keepItem][non_terminal]") {
    BattleState s = make_q_state();
    s.side0.team[0].item = 0;
    s.side0.team[0].consumed_berry = TEST_BERRY_ITEM;
    // neither fainted -> non-terminal
    Question q{};
    q.keepItem = TEST_BERRY_ITEM;
    REQUIRE(classify(s, q) == Outcome::CONTINUE);
}

// ---------------------------------------------------------------------------
// Section 4: keepHp boundary (requires requireNoFaint=true)
// ---------------------------------------------------------------------------

TEST_CASE("classify: keepHp boundary, player HP == N -> WIN",
          "[question][keepHp][boundary]") {
    BattleState s = make_q_state();
    constexpr int32_t N = 42;
    s.side0.team[0].hp = N;
    faint(s, 1);
    Question q{};
    q.keepHp = N;
    REQUIRE(classify(s, q) == Outcome::WIN);
}

TEST_CASE("classify: keepHp boundary, player HP == N-1 -> LOSS",
          "[question][keepHp][boundary]") {
    BattleState s = make_q_state();
    constexpr int32_t N = 42;
    s.side0.team[0].hp = N - 1;
    faint(s, 1);
    Question q{};
    q.keepHp = N;
    REQUIRE(classify(s, q) == Outcome::LOSS);
}

// ---------------------------------------------------------------------------
// Section 5: action_filter — banMove
// ---------------------------------------------------------------------------

TEST_CASE("action_filter: bans exactly the banned move slot",
          "[question][action_filter][banMove]") {
    Question q{};
    q.banMove = 2;  // ban slot 2

    REQUIRE_FALSE(action_filter(q, move_action(2)));  // banned
    REQUIRE(action_filter(q, move_action(0)));         // allowed
    REQUIRE(action_filter(q, move_action(1)));         // allowed
    REQUIRE(action_filter(q, move_action(3)));         // allowed
}

TEST_CASE("action_filter: Struggle (slot -2) always allowed even with banMove set",
          "[question][action_filter][banMove][struggle]") {
    Question q{};
    q.banMove = 0;  // ban slot 0

    REQUIRE(action_filter(q, struggle_action()));
}

TEST_CASE("action_filter: no banMove (-1) allows all slots",
          "[question][action_filter][no_ban]") {
    Question q{};
    // banMove defaults to -1 (none)

    REQUIRE(action_filter(q, move_action(0)));
    REQUIRE(action_filter(q, move_action(1)));
    REQUIRE(action_filter(q, move_action(2)));
    REQUIRE(action_filter(q, move_action(3)));
    REQUIRE(action_filter(q, struggle_action()));
}
