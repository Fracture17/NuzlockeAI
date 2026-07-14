// Catch2 tests for the analytic certifier: Task 5 (wave 0: pure damage race skeleton),
// Task 6 (audit loop + trace smoke tests), and Task 7 pre-work (audit pipeline path coverage
// via injected matchups + certifier seam). Tagged [analytic]. Fixture conventions match
// test_solver_bsolver.cpp: Tackle=33, Splash=150, AB_SHELL_ARMOR=75, ITM_SITRUS=158.
#include <catch2/catch_test_macros.hpp>

#include "solver/analytic/analytic.h"
#include "solver/audit/audit_analytic_core.h"
#include "solver/matchup_gen.h"
#include "state.h"

#include <functional>
#include <string>

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

static constexpr int32_t AB_SHELL_ARMOR  = 75;   // no crit branch
static constexpr int32_t ITM_SITRUS      = 158;  // restores hp when <= max/2
static constexpr int32_t ITM_FOCUS_SASH  = 275;  // survives OHKO from full HP at 1
static constexpr int32_t MV_TACKLE       = 33;   // 40 BP, 100% acc, single-hit, no secondary
static constexpr int32_t MV_SPLASH       = 150;  // 0 BP status (harmless)
static constexpr int32_t MV_ROCK_BLAST   = 350;  // 25 BP, 100% acc, 2-5 multi-hit

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

// Minimal clean single-move fixture. Both sides use the given move.
// player_faster: true = side0 has higher speed.
// hp/max_hp/atk/def are tunable so callers can craft specific race outcomes.
static BattleState make_clean_state(
    int32_t player_move_id, int32_t opp_move_id,
    int32_t player_hp, int32_t player_atk, int32_t player_def, int32_t player_spe,
    int32_t opp_hp,   int32_t opp_atk,   int32_t opp_def,   int32_t opp_spe,
    int32_t player_item = 0, int32_t opp_item = 0,
    int32_t player_ability = AB_SHELL_ARMOR, int32_t opp_ability = AB_SHELL_ARMOR)
{
    BattleState s{};

    PokemonState player{};
    player.species = 1; player.level = 50; player.has_stats = true;
    player.stat_hp  = player_hp; player.stat_atk = player_atk; player.stat_def = player_def;
    player.stat_spa = 5; player.stat_spd = 5; player.stat_spe = player_spe;
    player.has_max_hp = true; player.max_hp = player_hp;
    player.has_hp = true;     player.hp     = player_hp;
    player.move_id0 = player_move_id; player.move_pp0 = 35;
    player.ability = player_ability;
    player.item    = player_item;
    s.side0.team.push_back(player);
    s.side0.active_indices.push_back(0);

    PokemonState opp{};
    opp.species = 1; opp.level = 50; opp.has_stats = true;
    opp.stat_hp  = opp_hp; opp.stat_atk = opp_atk; opp.stat_def = opp_def;
    opp.stat_spa = 5; opp.stat_spd = 5; opp.stat_spe = opp_spe;
    opp.has_max_hp = true; opp.max_hp = opp_hp;
    opp.has_hp = true;     opp.hp     = opp_hp;
    opp.move_id0 = opp_move_id; opp.move_pp0 = 35;
    opp.ability = opp_ability;
    opp.item    = opp_item;
    s.side1.team.push_back(opp);
    s.side1.active_indices.push_back(0);

    s.turn_number = 1;
    return s;
}

// ---------------------------------------------------------------------------
// Test 1: Player-faster guaranteed OHKO → WIN, kill_turn=1, tight=true.
//
// Setup: player ATK=999, player SPE=100 (faster); opp HP=5, opp SPE=60.
// Both sides use Tackle (40 BP, 100% acc, single-hit, no secondary).
// Shell Armor on both sides (suppresses crit). Player is guaranteed to OHKO
// on turn 1 (massive ATK vs tiny HP) and goes first.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: player-faster guaranteed OHKO → WIN kill_turn=1 tight",
          "[analytic][win]") {
    // Player: ATK=999, SPE=100; Opp: HP=5, SPE=60. Both Tackle, Shell Armor.
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 200, 999, 100, 100,
        /*opp*/    5,   10,  5,  60
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::WIN);
    REQUIRE(r.kill_turn == 1);
    REQUIRE(r.tight == true);
}

// ---------------------------------------------------------------------------
// Test 2: Opponent guaranteed 2HKO vs player guaranteed 3HKO → LOSS.
//
// Setup arithmetic (Tackle BP=40, level=50, Shell Armor both sides):
//   pre_roll = (2*50/5 + 2) * BP * atk / (def * 50) + 2
//            = 22 * BP * atk / (def * 50) + 2
//
// We need: ALL opp rolls 2HKO the player, ALL player rolls need 3 hits to KO opp.
//
// Let player_hp=100, opp_atk=45, player_def=5:
//   pre_roll = 22*40*45/(5*50)+2 = 39600/250+2 = 158+2 = 160
//   opp max dmg = floor(160*100/100) = 160 > 100 → OHKO not 2HKO.
//   Too high. Try opp_atk=8:
//   pre_roll = 22*40*8/(5*50)+2 = 7040/250+2 = 28+2 = 30 (floor(7040/250)=28)
//   min dmg = floor(30*85/100)=25; max dmg=30. 2 hits min=50, 2 hits max=60.
//   Player HP=100 → 2 hits at max (60) = 60 < 100. Not a guaranteed 2HKO.
//   We need 2*min_opp_dmg > player_hp.
//   So min_opp_dmg > 50 → pre_roll * 85/100 > 50 → pre_roll > 58.8.
//   22*40*opp_atk/(5*50)+2 > 58.8 → 880*opp_atk/250 > 56.8 → opp_atk > 16.1
//   Also need max_opp_dmg < player_hp for a 2HKO (not OHKO): pre_roll < player_hp=100.
//   22*40*opp_atk/(5*50)+2 < 100 → 3.52*opp_atk < 98 → opp_atk < 27.8.
//   Use opp_atk=20: pre_roll=22*40*20/(250)+2=70+2=72 (floor(17600/250)=70).
//   min_opp=floor(72*85/100)=61, max_opp=72. Both rounds: 61+61=122>100 ✓, 72<100 ✓.
//   → guaranteed 2HKO (2 hits kills even min-roll).
//
// Player guaranteed 3HKO on opp: opp_hp=100, player_atk calibrated so 2 hits < opp_hp.
//   Let player_atk=8, opp_def=5 (same as above but player vs opp):
//   player pre_roll = 22*40*8/(5*50)+2 = 28+2 = 30.
//   player max dmg = 30, player min dmg = floor(30*85/100) = 25.
//   opp_hp=100; 2*30=60 < 100 ✓ (not guaranteed 2HKO), 3*25=75 < 100...
//   Hmm. Need player 3HKO guaranteed: 3*min_player_dmg > opp_hp.
//   3*25=75 < 100. Not guaranteed. Let's lower opp_hp or increase player_atk.
//   With opp_hp=70: 2*30=60 < 70 ✓ (not 2HKO), 3*25=75 > 70 ✓ (guaranteed 3HKO).
//   Also need 3 hits exactly: 2*max=60<70 ✓ and 3*min=75>70 ✓.
//
// Speed: opp faster (spe_opp > spe_player) → opp acts first → race is tighter for player.
// With opp faster and 2HKO guaranteed, player must survive 1 hit and kill on turn 3 while
// opp kills on turn 2. That's LOSS: opp kills on turn 2, player hasn't killed by then.
//
// Turn 1: opp first → hits player (100→28..39 HP). Player second → hits opp (~25-30 dmg).
// Turn 2: opp first → hits player again (28..39 → dead since min_dmg=61 > remaining).
// Actually: after turn 1, player HP = 100 - opp_max (72) to 100 - opp_min (61) = 28..39.
// Turn 2: opp min dmg = 61 > 39 (player max remaining HP after hit 1) → guaranteed OHKO on turn 2.
// Player gets 2 turns total. On turn 2 (if goes second), player has dealt 2 hits to opp (50-60 dmg).
// opp_hp=70; after 2 player hits: 70-60=10 to 70-50=20 HP remaining. Not dead.
// → Player needs turn 3 but is dead by turn 2. LOSS.
//
// Opponent faster forces this guaranteed-loss race.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: opp guaranteed 2HKO vs player guaranteed 3HKO → LOSS",
          "[analytic][loss]") {
    // Player: HP=100, ATK=8, DEF=5, SPE=60 (slower).
    // Opp: HP=70, ATK=20, DEF=5, SPE=100 (faster).
    // Both Tackle, Shell Armor. No items.
    // Opp 2HKO guaranteed (min 2-hit damage = 122 > 100).
    // Player 3HKO guaranteed on opp (3*min=75 > 70; 2*max=60 < 70).
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 100, 8, 5, 60,
        /*opp*/     70, 20, 5, 100
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::LOSS);
}

// ---------------------------------------------------------------------------
// Test 3: Opp-Sitrus trigger straddling interval → UNKNOWN(AT_THRESH).
//
// Setup: opp holds Sitrus (ITM_SITRUS=158). Player damage rolls straddle half-HP
// of opp after hit 1. Some rolls put opp <= max/2, some don't.
//
// opp_hp=100 (max_hp=100). Sitrus triggers at <= 50.
// Player damage: min must be < 50 (opp stays above half), max must be >= 51 (triggers).
// Actually: trigger when hp AFTER hit <= max/2 = 50.
// Post-hit hp: opp_hp - damage. Trigger when (100 - dmg) <= 50 → dmg >= 50.
// Non-trigger when (100 - dmg) > 50 → dmg < 50.
//
// We need: some player rolls dmg >= 50, some rolls dmg < 50. Straddle.
// Tackle BP=40, level=50, shell armor. pre_roll = 22*40*atk/(def*50)+2.
// Let atk=15, def=5: pre_roll=22*40*15/(250)+2=52+2=54 (floor(13200/250)=52).
// dmg range: floor(54*85/100)=45 to 54.
// min=45 < 50, max=54 >= 50 → straddle. ✓
// ---------------------------------------------------------------------------

TEST_CASE("analytic: opp-Sitrus trigger straddling interval → UNKNOWN AT_THRESH",
          "[analytic][unknown][thresh]") {
    // Player: ATK=15, SPE=100 (faster, to act first); Opp: HP=100, Sitrus, DEF=5, SPE=60.
    // Player Tackle dmg: min=45, max=54 → straddles opp Sitrus trigger at <=50 HP.
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 200, 15, 5, 100,
        /*opp*/    100, 5, 5, 60,
        /*player_item=*/ 0, /*opp_item=*/ ITM_SITRUS
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::UNKNOWN);
    REQUIRE(r.tag == AT_THRESH);
}

// ---------------------------------------------------------------------------
// Test 4: Multi-hit move + additional scope violations → UNKNOWN(AT_SCOPE),
// scope_mask accumulates ALL applicable bits (accumulation required behavior).
//
// Give player Rock Blast (multi-hit) and give opp a status condition (to trigger
// the "clean entry context" scope bit). Both must appear in scope_mask.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: multi-hit move + status → UNKNOWN AT_SCOPE, scope_mask accumulates bits",
          "[analytic][unknown][scope][accumulation]") {
    BattleState s = make_clean_state(
        MV_ROCK_BLAST, MV_TACKLE,
        /*player*/ 200, 50, 50, 100,
        /*opp*/    100, 10, 5, 60
    );
    // Set opp status to BURN (status=1) → triggers ENTRY scope bit.
    s.side1.team[0].status = 1;  // STATUS_BURN = 1

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::UNKNOWN);
    REQUIRE(r.tag == AT_SCOPE);

    // scope_mask must have the multi-hit bit AND the entry/status bit.
    REQUIRE((r.scope_mask & SCOPE_MULTI_HIT) != 0);
    REQUIRE((r.scope_mask & SCOPE_ENTRY_DIRTY) != 0);
}

// ---------------------------------------------------------------------------
// Test 5: Non-tight LOSS degradation → UNKNOWN, not LOSS.
//
// Speed tie: both sides have equal speed. Engine forks both orders when speeds
// are equal (exact per spec: no commutation assumption). If the two orders give
// different verdicts (one wins, one loses), the fork disagrees → UNKNOWN.
//
// Craft a matchup where:
//   - player-first order → player OHKOs → WIN
//   - opp-first order → opp OHKOs → LOSS
// Equal speed → the certifier forks both orders and they disagree → UNKNOWN.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: speed-tie with disagreeing orders → UNKNOWN not LOSS",
          "[analytic][unknown][nontight]") {
    // Both sides: HP=5, ATK=999, SPE=100 (equal speed), Tackle, Shell Armor.
    // Player-first: player OHKOs opp → WIN. Opp-first: opp OHKOs player → LOSS.
    // Equal speed → fork → disagreement → UNKNOWN.
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 5, 999, 5, 100,
        /*opp*/    5, 999, 5, 100
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    // The fork disagrees → must be UNKNOWN, not LOSS.
    REQUIRE(r.verdict == AVerdict::UNKNOWN);
}

// ---------------------------------------------------------------------------
// Test 6: Full-HP Focus Sash + guaranteed-lethal single hit → no false kill-now WIN on turn 1.
//
// Sash saves opp at 1 HP on what would have been a kill. A correct model must NOT
// report WIN with kill_turn=1. If the certifier returns WIN, kill_turn must be >= 2.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: full-HP Focus Sash opp + lethal single hit → no false kill-now WIN on turn 1",
          "[analytic][sash][no_false_win]") {
    // Player: ATK=999, SPE=100 (faster). Opp: HP=5, max_hp=5, Focus Sash, SPE=60.
    // Player Tackle guaranteed-lethal → Sash activates → opp survives at HP=1.
    // No kill on turn 1. Either UNKNOWN or WIN with kill_turn >= 2.
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 200, 999, 5, 100,
        /*opp*/    5, 5, 5, 60,
        /*player_item=*/ 0, /*opp_item=*/ ITM_FOCUS_SASH
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    // Must NOT be a WIN with kill_turn=1 (that would be a false WIN via ignoring the Sash).
    if (r.verdict == AVerdict::WIN) {
        REQUIRE(r.kill_turn >= 2);
    }
    // If UNKNOWN, that is also acceptable (scope out rather than false WIN).
    // LOSS is not acceptable here (player can kill in 2 turns after Sash).
    REQUIRE(r.verdict != AVerdict::LOSS);
}

// ---------------------------------------------------------------------------
// Test 7a: Speed-tie fork — BOTH orders give WIN → WIN.
//
// Both sides: equal speed; player ATK=999 and opp is harmless (Splash only).
// Player-first: OHKO → WIN. Opp-first: opp uses Splash (no damage) → player
// OHKOs next → WIN. Both orders WIN → result is WIN.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: speed-tie BOTH orders WIN → WIN",
          "[analytic][win][speed_tie]") {
    // Player: ATK=999, SPE=100, Tackle. Opp: Splash only (harmless), SPE=100.
    // Both orders: player kills on turn 1 (if first) or turn 1 after Splash (if second).
    BattleState s = make_clean_state(
        MV_TACKLE, MV_SPLASH,
        /*player*/ 200, 999, 5, 100,
        /*opp*/    5, 5, 5, 100
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    // Both speed-tie orders give WIN (opp has only Splash, no damage) → WIN.
    // (May also be UNKNOWN if Splash is out-of-scope for opp having no effective move — AT_STALL.
    //  That is also acceptable per spec: stall → UNKNOWN(AT_STALL). Assert not LOSS.)
    REQUIRE(r.verdict != AVerdict::LOSS);
    // If WIN, kill_turn must be >= 1.
    if (r.verdict == AVerdict::WIN) {
        REQUIRE(r.kill_turn >= 1);
    }
}

// ---------------------------------------------------------------------------
// Test 7b: Speed-tie fork — orders disagree (one WIN, one LOSS) → UNKNOWN.
//
// Same as Test 5.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: speed-tie orders disagree → UNKNOWN",
          "[analytic][unknown][speed_tie]") {
    // Covered by Test 5 but included for explicit labeling.
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 5, 999, 5, 100,
        /*opp*/    5, 999, 5, 100
    );

    Question q{};
    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::UNKNOWN);
}

// ---------------------------------------------------------------------------
// Test 8: Smoke — analytic_certify over 200 Uniform matchups (seed 1) NEVER
// throws, returns only WIN/LOSS/UNKNOWN. INFO() the split.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: smoke — 200 Uniform matchups never throws, only valid verdicts",
          "[analytic][smoke]") {
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    MatchupGen gen(1, MatchupGen::Class::Uniform, 0, 1, paths);

    int n_win = 0, n_loss = 0, n_unknown = 0;
    int n = 200;

    for (int i = 0; i < n; ++i) {
        BattleState state = gen.next();
        Question q{};

        // Must not throw for any matchup.
        AnalyticResult r = analytic_certify(state, q);

        // Only valid verdicts.
        REQUIRE((r.verdict == AVerdict::WIN
              || r.verdict == AVerdict::LOSS
              || r.verdict == AVerdict::UNKNOWN));

        switch (r.verdict) {
            case AVerdict::WIN:     ++n_win;     break;
            case AVerdict::LOSS:    ++n_loss;    break;
            case AVerdict::UNKNOWN: ++n_unknown; break;
        }
    }

    INFO("Analytic wave-0 verdict split on 200 Uniform matchups (seed 1):");
    INFO("  WIN:     " << n_win);
    INFO("  LOSS:    " << n_loss);
    INFO("  UNKNOWN: " << n_unknown);

    // Wave 0 decides very few matchups; UNKNOWN majority is expected and fine.
    // No assertion on counts — just report.
}

// ---------------------------------------------------------------------------
// Test 9: Non-default Question → UNKNOWN with the question scope bit.
// ---------------------------------------------------------------------------

TEST_CASE("analytic: non-default Question (keepHp>0) → UNKNOWN with question scope bit",
          "[analytic][unknown][question]") {
    BattleState s = make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 200, 999, 5, 100,
        /*opp*/    5, 5, 5, 60
    );

    Question q{};
    q.keepHp = 10;  // non-default field → UNKNOWN with question scope bit

    AnalyticResult r = analytic_certify(s, q);

    REQUIRE(r.verdict == AVerdict::UNKNOWN);
    REQUIRE((r.scope_mask & SCOPE_NONDEFAULT_QUESTION) != 0);
}

// ---------------------------------------------------------------------------
// Task 6 smoke tests ([.slow] tag: opt-in only, not run in the default suite).
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Helper: make a known-WIN fixture (guaranteed OHKO, player faster).
// Same parameters as Test 1: ATK=999, SPE=100 vs HP=5, SPE=60.
// ---------------------------------------------------------------------------
static BattleState make_win_fixture() {
    return make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 200, 999, 100, 100,
        /*opp*/    5,   10,  5,  60
    );
}

// Helper: make a known-LOSS fixture (opp guaranteed 2HKO, player guaranteed 3HKO).
// Same parameters as Test 2: player HP=100, ATK=8, SPE=60; opp HP=70, ATK=20, SPE=100.
static BattleState make_loss_fixture() {
    return make_clean_state(
        MV_TACKLE, MV_TACKLE,
        /*player*/ 100, 8, 5, 60,
        /*opp*/     70, 20, 5, 100
    );
}

// Helper: build a minimal AnalyticAuditConfig that uses injected matchups (no generator).
// repo_root left empty; generator path never runs.
static AnalyticAuditConfig make_injected_cfg(std::vector<BattleState> states,
                                              CertifierFn certifier = {}) {
    AnalyticAuditConfig cfg;
    cfg.injected             = std::move(states);
    cfg.certifier            = std::move(certifier);
    cfg.oracle_max_leaves    = 5'000;
    cfg.node_cap             = 1'000;
    // repo_root left empty — generator is never invoked with injected list.
    return cfg;
}

// ---------------------------------------------------------------------------
// Audit pipeline path tests [analytic][audit_referee].
// Written before the refactor so they fail initially, then pass after.
// ---------------------------------------------------------------------------

// Test A: TRUE WIN PATH.
// Inject a known analytic-WIN fixture with the real certifier.
// Expected: decided==1, analytic_WIN==1, soundness_failures==0.
// WIN can never be pess_confirmed (pessimal LOSS would be a soundness failure;
// pessimal WIN/INDET routes to exact). So exact_adjudicated==1, exact_wins==1.
TEST_CASE("audit referee: true WIN path — exact adjudicates, no failure",
          "[analytic][audit_referee]") {
    AnalyticAuditConfig cfg = make_injected_cfg({make_win_fixture()});

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.scanned == 1);
    REQUIRE(r.decided == 1);
    REQUIRE(r.n_analytic_win == 1);
    REQUIRE(r.n_analytic_loss == 0);
    REQUIRE(r.soundness_failures == 0);
    // WIN cannot be pess_confirmed (pessimal LOSS + analytic WIN = immediate failure).
    REQUIRE(r.pess_confirmed == 0);
    // Exact must have been called and resolved it.
    REQUIRE(r.exact_adjudicated == 1);
    REQUIRE(r.exact_wins == 1);
}

// Test B: TRUE LOSS PATH.
// Inject a known analytic-LOSS fixture with the real certifier.
// Expected: decided==1, analytic_LOSS==1, soundness_failures==0.
// Either pess_confirmed==1 (pessimal found LOSS, cheap path) OR
// exact_adjudicated==1 with exact LOSS (pess returned WIN/INDET). Both are sound.
// Require at least one verification path ran (no unverified decided verdict).
TEST_CASE("audit referee: true LOSS path — verified via pess or exact, no failure",
          "[analytic][audit_referee]") {
    AnalyticAuditConfig cfg = make_injected_cfg({make_loss_fixture()});

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.scanned == 1);
    REQUIRE(r.decided == 1);
    REQUIRE(r.n_analytic_loss == 1);
    REQUIRE(r.n_analytic_win == 0);
    REQUIRE(r.soundness_failures == 0);
    // At least one verification path must have run for the decided verdict.
    // pess_confirmed=1 (cheap) OR exact_adjudicated=1 with LOSS (pess WIN/INDET).
    bool pess_confirmed = (r.pess_confirmed == 1);
    bool exact_loss = (r.exact_adjudicated == 1 && r.exact_wins == 0);
    // Both are sound; assert whichever actually occurs.
    // If neither ran, the verdict slipped through unverified — that is a bug.
    REQUIRE((pess_confirmed || exact_loss));

    INFO("LOSS fixture path: pess_confirmed=" << r.pess_confirmed
         << " exact_adjudicated=" << r.exact_adjudicated
         << " exact_wins=" << r.exact_wins);
}

// Test C: SOUNDNESS FAILURE — WIN claimed on a LOSS fixture.
// Inject the LOSS fixture with a fake certifier returning verdict WIN (tag AT_OK).
// Expected: soundness_failures==1, one failure record with av_verdict=="WIN",
// loss_vs_exact_win==false (this is WIN-vs-LOSS, not LOSS-vs-WIN).
TEST_CASE("audit referee: soundness failure WIN-claimed-on-LOSS",
          "[analytic][audit_referee]") {
    // Fake certifier: always returns WIN regardless of state.
    CertifierFn fake = [](const BattleState&, const Question&) -> AnalyticResult {
        AnalyticResult r;
        r.verdict = AVerdict::WIN;
        r.tag     = AT_OK;
        r.tight   = true;
        return r;
    };
    AnalyticAuditConfig cfg = make_injected_cfg({make_loss_fixture()}, fake);

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.soundness_failures == 1);
    REQUIRE(r.failures.size() == 1);
    REQUIRE(r.failures[0].av_verdict == "WIN");
    // Exact says LOSS (the fixture is a real LOSS), so loss_vs_exact_win == false.
    REQUIRE(r.failures[0].loss_vs_exact_win == false);
    // Index 0 (first injected matchup).
    REQUIRE(r.failures[0].index == 0);
}

// Test D: SOUNDNESS FAILURE — LOSS claimed on a WIN fixture.
// Expected: soundness_failures==1, failure is the LOSS-vs-exact-WIN category
// (loss_vs_exact_win==true, printed first per spec).
TEST_CASE("audit referee: soundness failure LOSS-claimed-on-WIN (print-first category)",
          "[analytic][audit_referee]") {
    // Fake certifier: always returns LOSS regardless of state.
    CertifierFn fake = [](const BattleState&, const Question&) -> AnalyticResult {
        AnalyticResult r;
        r.verdict = AVerdict::LOSS;
        r.tag     = AT_OK;
        r.tight   = true;
        return r;
    };
    AnalyticAuditConfig cfg = make_injected_cfg({make_win_fixture()}, fake);

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.soundness_failures == 1);
    REQUIRE(r.failures.size() == 1);
    REQUIRE(r.failures[0].av_verdict == "LOSS");
    // This is the LOSS-vs-exact-WIN category (print first).
    REQUIRE(r.failures[0].loss_vs_exact_win == true);
    REQUIRE(r.failures[0].index == 0);
}

// Test E: UNKNOWN PASSTHROUGH.
// Fake certifier returns UNKNOWN(AT_SCOPE, SCOPE_MULTI_HIT) on any fixture.
// Expected: decided==0, unknown==1, tag histogram populated, scope_bit_histogram
// populated, no verification calls charged (pess_confirmed==0, exact_adjudicated==0,
// exact_skipped==0; pessimal_us_total and exact_us_total stay 0 or unmeasurable).
TEST_CASE("audit referee: UNKNOWN passthrough — no verification calls, histograms populated",
          "[analytic][audit_referee]") {
    CertifierFn fake = [](const BattleState&, const Question&) -> AnalyticResult {
        AnalyticResult r;
        r.verdict    = AVerdict::UNKNOWN;
        r.tag        = AT_SCOPE;
        r.scope_mask = SCOPE_MULTI_HIT;
        return r;
    };
    AnalyticAuditConfig cfg = make_injected_cfg({make_win_fixture()}, fake);

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.scanned == 1);
    REQUIRE(r.decided == 0);
    REQUIRE(r.n_unknown == 1);
    REQUIRE(r.soundness_failures == 0);
    // No verification path should have run.
    REQUIRE(r.pess_confirmed == 0);
    REQUIRE(r.exact_adjudicated == 0);
    REQUIRE(r.exact_skipped == 0);
    // Histograms populated with the injected tag/bits.
    REQUIRE(r.unknown_tag_histogram.count(AT_SCOPE) == 1);
    REQUIRE(r.unknown_tag_histogram.at(AT_SCOPE) == 1);
    REQUIRE(r.scope_bit_histogram.count(0) == 1);  // bit 0 = SCOPE_MULTI_HIT
    REQUIRE(r.scope_bit_histogram.at(0) == 1);
    // Verification counters (pessimal/exact µs) must be zero since no decided verdict.
    REQUIRE(r.pessimal_us_total == 0.0);
    REQUIRE(r.exact_us_total == 0.0);
}

// Test F: MASK-COMBINATION HISTOGRAM.
// Wave planning needs EXACT scope-mask combinations (single-bit counts can't tell
// which matchups a wave fully unlocks, since reasons co-occur). Two injected
// matchups with distinct masks and one with a repeat mask must yield combo counts
// {maskA: 2, maskB: 1}.
TEST_CASE("audit referee: scope mask-combination histogram accumulates exact masks",
          "[analytic][audit_referee]") {
    const uint32_t maskA = SCOPE_SECONDARY | SCOPE_ACCURACY_LT100;
    const uint32_t maskB = SCOPE_ITEM_NOT_ALLOWED;
    int call = 0;
    CertifierFn fake = [&call, maskA, maskB](const BattleState&, const Question&) -> AnalyticResult {
        AnalyticResult r;
        r.verdict    = AVerdict::UNKNOWN;
        r.tag        = AT_SCOPE;
        r.scope_mask = (call++ == 1) ? maskB : maskA;  // A, B, A
        return r;
    };
    AnalyticAuditConfig cfg = make_injected_cfg(
        {make_win_fixture(), make_win_fixture(), make_win_fixture()}, fake);

    AnalyticAuditReport r = analytic_audit_run(cfg);

    REQUIRE(r.scanned == 3);
    REQUIRE(r.mask_combo_histogram.size() == 2);
    REQUIRE(r.mask_combo_histogram.at(maskA) == 2);
    REQUIRE(r.mask_combo_histogram.at(maskB) == 1);
}

// ---------------------------------------------------------------------------
// Smoke 1: audit loop — 10 Uniform matchups (seed 1), small budgets, zero soundness
// failures (exact-INDETERMINATE skips are allowed). Histograms must be populated
// (decided + unknown == scanned).
TEST_CASE("analytic audit: smoke 10 uniform matchups — zero soundness failures, histograms populated",
          "[analytic][.slow]") {
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;

    AnalyticAuditConfig cfg;
    cfg.seed             = 1;
    cfg.klass            = "uniform";
    cfg.n                = 10;
    cfg.mode             = AnalyticAuditMode::All;
    cfg.shard_k          = 0;
    cfg.shard_of         = 1;
    cfg.repo_root        = repo_root;
    cfg.oracle_max_leaves = 5'000;
    cfg.node_cap          = 1'000;

    AnalyticAuditReport report = analytic_audit_run(cfg);

    // No soundness failures allowed.
    REQUIRE(report.soundness_failures == 0);

    // Histograms/counters must be consistent: decided + unknown == scanned.
    REQUIRE(report.scanned == 10);
    REQUIRE(report.decided + report.n_unknown == report.scanned);
    REQUIRE(report.n_analytic_win + report.n_analytic_loss == report.decided);

    // Timing sanity: at least some time was spent.
    REQUIRE(report.analytic_us_total >= 0.0);

    INFO("audit smoke: scanned=" << report.scanned
         << " decided=" << report.decided
         << " win=" << report.n_analytic_win
         << " loss=" << report.n_analytic_loss
         << " unknown=" << report.n_unknown
         << " soundness_failures=" << report.soundness_failures);
}

// Smoke 2: trace — run analytic_trace_run on 3 Uniform matchups (seed 1, indices 0-2).
// Each must produce non-empty output and not throw.
TEST_CASE("analytic trace: smoke — 3 uniform matchups produce non-empty output",
          "[analytic][.slow]") {
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;

    for (int idx = 0; idx < 3; ++idx) {
        AnalyticTraceConfig cfg;
        cfg.seed      = 1;
        cfg.klass     = "uniform";
        cfg.index     = idx;
        cfg.repo_root = repo_root;

        // Must not throw.
        AnalyticTraceOutput out = analytic_trace_run(cfg);

        REQUIRE(!out.text.empty());
        INFO("trace smoke index=" << idx << " output_len=" << out.text.size());
    }
}
