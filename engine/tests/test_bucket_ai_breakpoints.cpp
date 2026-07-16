// Bucket solver Task 9 unit + property tests: ai_breakpoint_entries — AI-scorer HP
// breakpoints on the player axis (AI is side 1) and the AI-own axis. Tests written
// alongside implementation; each locks one scorer mechanic's HP-dependence (roll
// values, exception kills, Super Fang ties, Pursuit/poison pct, player KO estimates,
// recovery/Substitute/Belly Drum/Explosion/Memento thresholds), plus regime-union and
// throw behavior. Property block sweeps axes and requires every support flip to be
// covered by an instantiated breakpoint (h or h+1).
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/ai_breakpoints.h"
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/expand.h"          // support_fingerprint
#include "solver/question.h"
#include "ai_analytic.h"                    // cpp_compute_action_probabilities
#include "ai_damage.h"                      // cpp_expected_damage
#include "ai_scorer_internal.h"             // ai_scorer::AVERAGE_LUCK_C
#include "ai_shared.h"                      // active_mon
#include "state.h"

#include <algorithm>
#include <string>
#include <vector>

namespace {

// Move ids.
constexpr int32_t TMV_TACKLE       = 33;
constexpr int32_t TMV_SPLASH       = 150;
constexpr int32_t TMV_DRAGON_RAGE  = 82;
constexpr int32_t TMV_SEISMIC_TOSS = 69;
constexpr int32_t TMV_PSYWAVE      = 149;
constexpr int32_t TMV_WRAP         = 20;
constexpr int32_t TMV_SUPER_FANG   = 162;
constexpr int32_t TMV_PURSUIT      = 228;
constexpr int32_t TMV_TOXIC        = 92;
constexpr int32_t TMV_RECOVER      = 105;
constexpr int32_t TMV_SUBSTITUTE   = 164;
constexpr int32_t TMV_BELLY_DRUM   = 187;
constexpr int32_t TMV_EXPLOSION    = 153;
constexpr int32_t TMV_MEMENTO      = 262;
constexpr int32_t TMV_FINAL_GAMBIT = 515;
constexpr int32_t TMV_EMBER        = 52;

constexpr int32_t TAB_BLAZE = 66;

PokemonState make_mon(int32_t species, int32_t max_hp, int32_t hp,
                      int32_t ability = 0, int32_t speed = 80,
                      int32_t move0 = TMV_TACKLE, int32_t move1 = 0,
                      int32_t move2 = 0, int32_t move3 = 0) {
    PokemonState p{};
    p.species    = species;
    p.level      = 50;
    p.has_stats  = true;
    p.stat_hp    = max_hp; p.stat_atk = 100; p.stat_def = 80;
    p.stat_spa   = 80;     p.stat_spd = 80;  p.stat_spe = speed;
    p.has_max_hp = true;   p.max_hp   = max_hp;
    p.has_hp     = true;   p.hp       = hp;
    p.move_id0 = move0; p.move_pp0 = 35;
    p.move_id1 = move1; p.move_pp1 = 35;
    p.move_id2 = move2; p.move_pp2 = 35;
    p.move_id3 = move3; p.move_pp3 = 35;
    p.ability  = ability;
    return p;
}

// p = player (side 0), o = AI (side 1).
BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

Question default_question() { return Question{}; }

bool has_kind(const std::vector<AiBpEntry>& e, AiBpKind k, int32_t v) {
    for (const auto& x : e) if (x.kind == k && x.hp == v) return true;
    return false;
}
bool any_kind(const std::vector<AiBpEntry>& e, AiBpKind k) {
    for (const auto& x : e) if (x.kind == k) return true;
    return false;
}
bool has(const std::vector<int32_t>& v, int32_t x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}

// Support fingerprint with the given side's active HP set to hp.
uint64_t fp_at(const BattleState& base, int side, int32_t hp) {
    BattleState s = base;
    SideState& ss = (side == 0) ? s.side0 : s.side1;
    ss.team[ss.active_indices[0]].hp = hp;
    return support_fingerprint(cpp_compute_action_probabilities(s, 1));
}

// Adjacent flip pair (a, a+1) of a monotone predicate over [1, max]; returns a or -1.
template <class Pred>
int32_t flip_a(Pred pred, int32_t max) {
    for (int32_t h = 1; h < max; ++h)
        if (pred(h) != pred(h + 1)) return h;
    return -1;
}

} // namespace

// ---------------------------------------------------------------------------
// 4a — player-axis mechanics (AI = side 1 attacking / thresholding player HP).
// ---------------------------------------------------------------------------

TEST_CASE("ai bp: AI Dragon Rage emits fixed 40 on player axis and flips support at 40/41",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_DRAGON_RAGE, TMV_SPLASH);
    BattleState s = make_state(p, o);

    auto e = ai_breakpoint_entries(s, 0);
    REQUIRE(has_kind(e, AiBpKind::RollValue, 40));
    // With a companion move (Splash), the Dragon Rage KO changes the winner set.
    REQUIRE(fp_at(s, 0, 40) != fp_at(s, 0, 41));
}

TEST_CASE("ai bp: AI Seismic Toss emits level (50); Psywave spot values 25 and 75",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o1 = make_mon(2, 200, 200, 0, 60, TMV_SEISMIC_TOSS);
    REQUIRE(has_kind(ai_breakpoint_entries(make_state(p, o1), 0), AiBpKind::RollValue, 50));

    PokemonState o2 = make_mon(2, 200, 200, 0, 60, TMV_PSYWAVE);
    auto e = ai_breakpoint_entries(make_state(p, o2), 0);
    REQUIRE(has_kind(e, AiBpKind::RollValue, 25));   // roll 0
    REQUIRE(has_kind(e, AiBpKind::RollValue, 75));   // roll 15
}

TEST_CASE("ai bp: AI Wrap emits its exact exception kill estimate and flips there",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_WRAP, TMV_SPLASH);
    BattleState s = make_state(p, o);

    const PokemonState& ai = active_mon(s, 1);
    const PokemonState& pl = active_mon(s, 0);
    int32_t wrap_dmg = cpp_expected_damage(ai, TMV_WRAP, pl, s, ai_scorer::MAX_LUCK_C,
                                           -1, false, -1);
    auto e = ai_breakpoint_entries(s, 0);
    REQUIRE(has_kind(e, AiBpKind::ExceptionKillEstimate, wrap_dmg));
    REQUIRE(fp_at(s, 0, wrap_dmg) != fp_at(s, 0, wrap_dmg + 1));
}

TEST_CASE("ai bp: AI Super Fang + Dragon Rage emits tie points 80, 81, 1 on player axis",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_SUPER_FANG, TMV_DRAGON_RAGE);
    auto e = ai_breakpoint_entries(make_state(p, o), 0);
    REQUIRE(has_kind(e, AiBpKind::SuperFangTie, 80));   // 2 * 40
    REQUIRE(has_kind(e, AiBpKind::SuperFangTie, 81));   // 2 * 40 + 1
    REQUIRE(has_kind(e, AiBpKind::SuperFangTie, 1));    // max(1,..) clamp boundary
}

TEST_CASE("ai bp: AI Pursuit emits pct flip pairs 40/41 and 80/81 for player max 200",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_PURSUIT);
    auto e = ai_breakpoint_entries(make_state(p, o), 0);
    // Derive expected pairs from the verbatim scorer expressions.
    int32_t a20 = flip_a([](int32_t h) { return (double)h / 200 <= 0.20; }, 200);
    int32_t a40 = flip_a([](int32_t h) { return (double)h / 200 <= 0.40; }, 200);
    REQUIRE(has_kind(e, AiBpKind::PursuitPct, a20));
    REQUIRE(has_kind(e, AiBpKind::PursuitPct, a20 + 1));
    REQUIRE(has_kind(e, AiBpKind::PursuitPct, a40));
    REQUIRE(has_kind(e, AiBpKind::PursuitPct, a40 + 1));
}

TEST_CASE("ai bp: AI Toxic emits the exact integer poison-gate flip pair (player max 201)",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 201, 201);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_TOXIC);
    auto e = ai_breakpoint_entries(make_state(p, o), 0);
    int32_t a = flip_a([](int32_t h) { return h * 100 / 201 > 20; }, 201);
    REQUIRE(a >= 0);
    REQUIRE(has_kind(e, AiBpKind::PoisonPct, a));
    REQUIRE(has_kind(e, AiBpKind::PoisonPct, a + 1));
}

// ---------------------------------------------------------------------------
// 4a — AI-own-axis mechanics.
// ---------------------------------------------------------------------------

TEST_CASE("ai bp: player damaging move yields E and 2E on the AI axis",
          "[bucket][ai_breakpoints]") {
    // NB: fixed-damage player moves (base_power==0, e.g. Seismic Toss) are SKIPPED by
    // the scorer's threat loops, so they produce no AI-axis estimate; use a real
    // damaging move and compute E via the scorer's own helper (never re-derived).
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_SPLASH);
    BattleState s = make_state(p, o);
    const PokemonState& ai = active_mon(s, 1);
    const PokemonState& pl = active_mon(s, 0);
    int32_t e_i = cpp_expected_damage(pl, TMV_TACKLE, ai, s, ai_scorer::AVERAGE_LUCK_C,
                                      -1, false, -1);
    auto e = ai_breakpoint_entries(s, 1);
    REQUIRE(has_kind(e, AiBpKind::PlayerKoEstimate, e_i));
    REQUIRE(has_kind(e, AiBpKind::PlayerTwoHitEstimate, 2 * e_i));
}

TEST_CASE("ai bp: AI Recover emits the recovery pct flip pairs; instantiate clips negatives",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_RECOVER);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    const auto& ai_axis = bp.opp_breakpoints();   // AI is side 1

    struct T { double thr; bool leq; };
    const T thresholds[] = {
        {0.85, false /* >= */}, {0.4, true /* <= */},
        {0.66, false}, {0.5, false}, {0.7, false},
    };
    for (const auto& t : thresholds) {
        int32_t a = flip_a([&](int32_t h) {
            double x = (double)h / 200;
            return t.leq ? (x <= t.thr) : (t.thr == 0.85 ? (x >= 0.85) : (x < t.thr));
        }, 200);
        REQUIRE(a >= 0);
        REQUIRE(has(ai_axis, a));
        REQUIRE(has(ai_axis, a + 1));
    }
    // No breakpoint may be negative or exceed max after instantiate normalization.
    for (int32_t v : ai_axis) { REQUIRE(v >= 0); REQUIRE(v <= 200); }
}

TEST_CASE("ai bp: AI Substitute flips at 101/102 for max 200, NOT at 100",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_SUBSTITUTE);
    auto e = ai_breakpoint_entries(make_state(p, o), 1);
    REQUIRE(has_kind(e, AiBpKind::SubPct50, 101));
    REQUIRE(has_kind(e, AiBpKind::SubPct50, 102));
    REQUIRE_FALSE(has_kind(e, AiBpKind::SubPct50, 100));
}

TEST_CASE("ai bp: AI Belly Drum flips at max/2 = 100 for max 201",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 201, 201, 0, 60, TMV_BELLY_DRUM);
    auto e = ai_breakpoint_entries(make_state(p, o), 1);
    REQUIRE(has_kind(e, AiBpKind::BellyDrumHalf, 100));   // 201/2
}

TEST_CASE("ai bp: AI Explosion emits the three ai-HP tier flip pairs (max 200)",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_EXPLOSION);
    auto e = ai_breakpoint_entries(make_state(p, o), 1);
    for (double thr : {0.10, 0.33, 0.66}) {
        int32_t a = flip_a([&](int32_t h) { return (double)h / 200 < thr; }, 200);
        REQUIRE(a >= 0);
        REQUIRE(has_kind(e, AiBpKind::ExplosionPct, a));
        REQUIRE(has_kind(e, AiBpKind::ExplosionPct, a + 1));
    }
}

TEST_CASE("ai bp: AI Memento emits the three ai-HP tier flip pairs (max 200)",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_MEMENTO);
    auto e = ai_breakpoint_entries(make_state(p, o), 1);
    for (double thr : {0.10, 0.33, 0.66}) {
        int32_t a = flip_a([&](int32_t h) { return (double)h / 200 < thr; }, 200);
        REQUIRE(has_kind(e, AiBpKind::MementoPct, a));
        REQUIRE(has_kind(e, AiBpKind::MementoPct, a + 1));
    }
}

// ---------------------------------------------------------------------------
// 4a(13) — throws.
// ---------------------------------------------------------------------------

TEST_CASE("ai bp: Final Gambit throws ai-final-gambit from instantiate",
          "[bucket][ai_breakpoints][fail_loud]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_FINAL_GAMBIT);
    BattleState s = make_state(p, o);
    BreakpointRegistry reg;
    bool threw = false;
    try { reg.instantiate(s, default_question()); }
    catch (const std::runtime_error& ex) {
        threw = true;
        REQUIRE(std::string(ex.what()).find("ai-final-gambit") != std::string::npos);
    }
    REQUIRE(threw);
}

TEST_CASE("ai bp: AI living bench mon throws ai-bench",
          "[bucket][ai_breakpoints][fail_loud]") {
    PokemonState p = make_mon(1, 200, 200);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_TACKLE);
    BattleState s = make_state(p, o);
    // Add a living bench mon to the AI side (side 1).
    s.side1.team.push_back(make_mon(3, 180, 180, 0, 55, TMV_TACKLE));

    bool threw = false;
    try { ai_breakpoint_entries(s, 1); }
    catch (const std::runtime_error& ex) {
        threw = true;
        REQUIRE(std::string(ex.what()).find("ai-bench") != std::string::npos);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// 4a(14) — negative: Tackle-only AI produces no special-kind entries.
// ---------------------------------------------------------------------------

TEST_CASE("ai bp: Tackle-only AI has no special-kind breakpoints",
          "[bucket][ai_breakpoints]") {
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 200, 200, 0, 60, TMV_TACKLE);
    BattleState s = make_state(p, o);
    auto pa = ai_breakpoint_entries(s, 0);
    auto aa = ai_breakpoint_entries(s, 1);
    for (const auto& e : {pa, aa}) {
        REQUIRE_FALSE(any_kind(e, AiBpKind::SuperFangTie));
        REQUIRE_FALSE(any_kind(e, AiBpKind::ExceptionKillEstimate));
        REQUIRE_FALSE(any_kind(e, AiBpKind::PursuitPct));
        REQUIRE_FALSE(any_kind(e, AiBpKind::PoisonPct));
        REQUIRE_FALSE(any_kind(e, AiBpKind::RecoverPct));
        REQUIRE_FALSE(any_kind(e, AiBpKind::RecoverKoAfter));
        REQUIRE_FALSE(any_kind(e, AiBpKind::SubPct50));
        REQUIRE_FALSE(any_kind(e, AiBpKind::BellyDrumHalf));
        REQUIRE_FALSE(any_kind(e, AiBpKind::ExplosionPct));
        REQUIRE_FALSE(any_kind(e, AiBpKind::MementoPct));
    }
}

// ---------------------------------------------------------------------------
// 4a(12) + 4c — regime union + property sweep: every support flip is covered.
// ---------------------------------------------------------------------------

namespace {
// Sweep an axis over [1,max] at a fixed opposite-side HP, requiring every support flip
// (h,h+1) to have h or h+1 in the instantiated breakpoint list for that axis.
void assert_axis_covered(const BattleState& base, int axis_side,
                         const std::vector<int32_t>& axis_bps, int32_t axis_max,
                         int32_t other_side, int32_t other_hp) {
    BattleState s = base;
    { SideState& os = (other_side == 0) ? s.side0 : s.side1;
      os.team[os.active_indices[0]].hp = other_hp; }
    uint64_t prev = 0; bool have_prev = false;
    for (int32_t h = 1; h <= axis_max; ++h) {
        BattleState st = s;
        SideState& as = (axis_side == 0) ? st.side0 : st.side1;
        as.team[as.active_indices[0]].hp = h;
        uint64_t fp = support_fingerprint(cpp_compute_action_probabilities(st, 1));
        if (have_prev && fp != prev) {
            INFO("axis_side=" << axis_side << " flip at h=" << h
                 << " other_hp=" << other_hp);
            REQUIRE((has(axis_bps, h) || has(axis_bps, h - 1)));
        }
        prev = fp; have_prev = true;
    }
}
} // namespace

TEST_CASE("ai bp: Blaze + Fire move regime union covers player-axis flips at pinch HP",
          "[bucket][ai_breakpoints]") {
    // AI (side 1) has Blaze + Ember; sweeping the player axis with the AI at its pinch
    // HP (max/3) must have every AI-support flip covered by the instantiated axis.
    PokemonState p = make_mon(1, 200, 200, 0, 80, TMV_TACKLE);
    PokemonState o = make_mon(2, 201, 201, TAB_BLAZE, 60, TMV_EMBER, TMV_SPLASH);
    BattleState s = make_state(p, o);

    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s, default_question());
    // AI at full HP (pinch off) and AI at max/3 (pinch on).
    assert_axis_covered(s, 0, bp.player_breakpoints(), 200, 1, 201);
    assert_axis_covered(s, 0, bp.player_breakpoints(), 200, 1, 201 / 3);
}

TEST_CASE("ai bp property sweep: hand matchups have every support flip covered",
          "[bucket][ai_breakpoints]") {
    struct Case { PokemonState p, o; };
    std::vector<Case> cases;
    // (a) damaging-only.
    cases.push_back({make_mon(1, 200, 200, 0, 80, TMV_TACKLE),
                     make_mon(2, 200, 200, 0, 60, TMV_TACKLE, TMV_SPLASH)});
    // (b) recovery.
    cases.push_back({make_mon(1, 200, 200, 0, 80, TMV_TACKLE),
                     make_mon(2, 200, 200, 0, 60, TMV_RECOVER, TMV_TACKLE)});
    // (c) Pursuit + poison.
    cases.push_back({make_mon(1, 200, 200, 0, 80, TMV_TACKLE),
                     make_mon(2, 200, 200, 0, 60, TMV_PURSUIT, TMV_TOXIC)});
    // (d) Super Fang.
    cases.push_back({make_mon(1, 200, 200, 0, 80, TMV_TACKLE),
                     make_mon(2, 200, 200, 0, 60, TMV_SUPER_FANG, TMV_DRAGON_RAGE)});

    BreakpointRegistry reg;
    for (auto& c : cases) {
        BattleState s = make_state(c.p, c.o);
        BpSet bp = reg.instantiate(s, default_question());
        int32_t pl_max = active_mon(s, 0).max_hp;
        int32_t ai_max = active_mon(s, 1).max_hp;
        // Player axis: AI (side 1) at root HP.
        assert_axis_covered(s, 0, bp.player_breakpoints(), pl_max, 1, ai_max);
        // AI axis: player (side 0) at root HP.
        assert_axis_covered(s, 1, bp.opp_breakpoints(), ai_max, 0, pl_max);
    }
}
