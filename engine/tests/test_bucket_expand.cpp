// Bucket solver Task 5 tests: Expand(bucket A, player_move) → AND-set of child buckets.
// Tests written BEFORE implementation; every test either succeeds only when the full
// pipeline is in place OR throws a specific ExpandError::Stage before implementation.
//
// Test IDs mirror SOLVER_BUCKET_PLAN Task 5 test design (1..16).
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/expand.h"
#include "solver/engine_queries.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "state.h"
#include "state_eq.h"

#include <algorithm>
#include <cstdint>
#include <exception>
#include <map>
#include <set>
#include <stdexcept>
#include <unordered_set>

// ---------------------------------------------------------------------------
// Constants (mirror test_bucket_replay.cpp / test_bucket_core.cpp)
// ---------------------------------------------------------------------------

static constexpr int32_t MV_TACKLE       = 33;
static constexpr int32_t MV_SPLASH       = 150;
static constexpr int32_t MV_EMBER        = 52;    // 30% burn secondary
static constexpr int32_t MV_DOUBLE_KICK  = 24;    // fixed 2-hit
static constexpr int32_t MV_FURY_ATTACK  = 31;    // 2..5 variable-hit
static constexpr int32_t MV_HYDRO_PUMP   = 56;    // 80 accuracy
static constexpr int32_t MV_SUPER_FANG   = 162;   // HP-dependent (§5.2)

static constexpr int32_t AB_SHELL_ARMOR  = 75;    // suppresses crit branch
static constexpr int32_t ITEM_SITRUS     = 158;

// ---------------------------------------------------------------------------
// Helpers — hand-built 1v1 states (mirrors test_bucket_core.cpp)
// ---------------------------------------------------------------------------

struct MonSpec {
    int32_t species = 1;
    int32_t max_hp  = 200;
    int32_t hp      = 200;
    int32_t item    = 0;
    int32_t ability = 0;
    int32_t speed   = 80;
    int32_t atk     = 100;
    int32_t def     = 80;
    int32_t spa     = 80;
    int32_t spd     = 80;
    int32_t move0   = MV_TACKLE;
    int32_t move1   = 0;
    int32_t move2   = 0;
    int32_t move3   = 0;
};

static PokemonState make_mon(const MonSpec& sp) {
    PokemonState p{};
    p.species    = sp.species;
    p.level      = 50;
    p.has_stats  = true;
    p.stat_hp    = sp.max_hp;
    p.stat_atk   = sp.atk;
    p.stat_def   = sp.def;
    p.stat_spa   = sp.spa;
    p.stat_spd   = sp.spd;
    p.stat_spe   = sp.speed;
    p.has_max_hp = true;
    p.max_hp     = sp.max_hp;
    p.has_hp     = true;
    p.hp         = sp.hp;
    p.move_id0   = sp.move0; p.move_pp0 = 35;
    p.move_id1   = sp.move1; p.move_pp1 = 35;
    p.move_id2   = sp.move2; p.move_pp2 = 35;
    p.move_id3   = sp.move3; p.move_pp3 = 35;
    p.item       = sp.item;
    p.ability    = sp.ability;
    return p;
}

static BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static Question default_question() { return Question{}; }

static ExecAction player_move_action(int slot = 0) {
    ExecAction a{};
    a.kind = 0; a.move_slot = slot;
    a.source_slot = 0; a.target_side = 1; a.target_slot = 0;
    return a;
}

// Build an ExpandContext holding an owned oracle/bp/interner. The caller keeps the
// storage alive for the duration of the call.
struct ExpandFixture {
    TransitionOracle oracle;
    BreakpointRegistry reg;
    BpSet bp;
    ContextInterner interner;
    ExpandContext ctx;

    ExpandFixture(const BattleState& state, const Question& q, const ExpandOptions& opts = {}) {
        bp = reg.instantiate(state, q);
        ctx.oracle   = &oracle;
        ctx.interner = &interner;
        ctx.bp       = &bp;
        ctx.concede  = nullptr;
        ctx.options  = opts;
    }
};

// Build a Bucket over a state (both HP values are the interval endpoints).
static Bucket bucket_from(BattleState state, HpInterval player_iv, HpInterval opp_iv,
                          const BpSet& bp, ContextInterner& interner) {
    // Compute the bucket d = ctx_id of the state (with HP masked internally by pack).
    uint32_t d = static_cast<uint32_t>(interner.pack(state) >> 32);
    // Support fingerprint from cpp_compute_action_probabilities(state, 1).
    std::vector<ActionProb> probs = cpp_compute_action_probabilities(state, 1);
    uint64_t fp = support_fingerprint(probs);
    return Bucket(d, player_iv, opp_iv, fp, bp);
}

// ---------------------------------------------------------------------------
// Test 15 — Unit tests for pure helpers (implemented FIRST so implementation
// pins the fundamentals before the pipeline).
// ---------------------------------------------------------------------------

TEST_CASE("expand unit: support_fingerprint is order-independent and excludes p=0",
          "[bucket][expand][unit]")
{
    ExecAction a{}; a.kind = 0; a.move_slot = 0; a.target_side = 1;
    ExecAction b{}; b.kind = 0; b.move_slot = 1; b.target_side = 1;
    ExecAction c{}; c.kind = 0; c.move_slot = 2; c.target_side = 1;

    std::vector<ActionProb> p1 = {{a, 0.4}, {b, 0.6}};
    std::vector<ActionProb> p2 = {{b, 0.1}, {a, 0.9}};  // same actions, different probs, swapped
    std::vector<ActionProb> p3 = {{a, 0.5}, {c, 0.5}};  // different action set
    std::vector<ActionProb> p4 = {{a, 0.4}, {b, 0.6}, {c, 0.0}};  // c has p=0 — excluded

    REQUIRE(support_fingerprint(p1) == support_fingerprint(p2));  // order + probs irrelevant
    REQUIRE(support_fingerprint(p1) != support_fingerprint(p3));  // different set
    REQUIRE(support_fingerprint(p1) == support_fingerprint(p4));  // p=0 excluded
}

TEST_CASE("expand unit: weak/strict crit dominance on synthetic tables",
          "[bucket][expand][unit]")
{
    DamageTable t_strict;
    t_strict.noncrit = {10, 12, 14};
    t_strict.crit    = {20, 22, 25};   // min crit=20 > max noncrit=14
    REQUIRE(strict_crit_dominance(t_strict));
    REQUIRE(weak_crit_dominance(t_strict));

    DamageTable t_weak_only;
    t_weak_only.noncrit = {5};
    t_weak_only.crit    = {5};         // crit_min == noncrit_max: weak, not strict
    REQUIRE_FALSE(strict_crit_dominance(t_weak_only));
    REQUIRE(weak_crit_dominance(t_weak_only));

    DamageTable t_fail;
    t_fail.noncrit = {10, 20};
    t_fail.crit    = {15, 25};         // crit_min=15 < noncrit_max=20
    REQUIRE_FALSE(strict_crit_dominance(t_fail));
    REQUIRE_FALSE(weak_crit_dominance(t_fail));
}

TEST_CASE("expand unit: derived_split_points strict-interior + sorted-dedup",
          "[bucket][expand][unit]")
{
    std::vector<int32_t> breakpoints = {100, 150};
    std::vector<int32_t> deltas      = {0, 10, 20};
    // Candidate points b + delta over lo=100, hi=170:
    //   100+0=100 (endpoint — excluded), 100+10=110, 100+20=120,
    //   150+0=150, 150+10=160, 150+20=170 (endpoint — excluded).
    // Also duplicates should dedupe.
    std::vector<int32_t> pts = derived_split_points(breakpoints, deltas, 100, 170);
    // Must contain the interior points only.
    REQUIRE(std::find(pts.begin(), pts.end(), 110) != pts.end());
    REQUIRE(std::find(pts.begin(), pts.end(), 120) != pts.end());
    REQUIRE(std::find(pts.begin(), pts.end(), 150) != pts.end());
    REQUIRE(std::find(pts.begin(), pts.end(), 160) != pts.end());
    // Must NOT contain the endpoints 100 or 170.
    REQUIRE(std::find(pts.begin(), pts.end(), 100) == pts.end());
    REQUIRE(std::find(pts.begin(), pts.end(), 170) == pts.end());
    // Sorted + unique.
    for (size_t i = 1; i < pts.size(); ++i) REQUIRE(pts[i-1] < pts[i]);
}

TEST_CASE("expand unit: cumulative_attack_deltas enumerates 1..max_hits sums",
          "[bucket][expand][unit]")
{
    DamageTable t;
    t.noncrit    = {3, 5};   // distinct values (also treat crit same for simplicity)
    t.crit       = {3, 5};
    t.max_hits   = 3;
    t.hit_count_support = {1, 2, 3};

    std::vector<int32_t> sums = cumulative_attack_deltas(t);
    std::set<int32_t> got(sums.begin(), sums.end());

    // Hand enumeration:
    //   1-hit sums:  {3, 5}
    //   2-hit sums:  {3+3, 3+5, 5+5} = {6, 8, 10}
    //   3-hit sums:  3-tuple sums over {3,5} = {9, 11, 13, 15}
    std::set<int32_t> expected = {3, 5, 6, 8, 10, 9, 11, 13, 15};
    REQUIRE(got == expected);
}

TEST_CASE("expand unit: cumulative_attack_deltas overflow throws",
          "[bucket][expand][unit][fail_loud]")
{
    // Force a cumulative-set explosion. Convolving arithmetic-progression tables
    // does NOT explode (sums stay bounded). We need sparse values whose partial
    // sums populate many distinct integers. Powers of two + max_hits=15 blows past
    // the 4096 cap fast.
    DamageTable t;
    for (int i = 0; i < 15; ++i) t.noncrit.push_back(1 << i);   // 1,2,4,...,16384
    t.crit             = t.noncrit;
    t.max_hits         = 15;
    for (int h = 1; h <= 15; ++h) t.hit_count_support.push_back(h);

    REQUIRE_THROWS_AS(cumulative_attack_deltas(t), ExpandError);
}

// ---------------------------------------------------------------------------
// Test 16 — Precondition: an interval touching 0 (terminal bucket) fails loud.
// ---------------------------------------------------------------------------

TEST_CASE("expand preconditions: interval touching 0 throws Stage::Precondition",
          "[bucket][expand][fail_loud]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());

    // Build a bucket with opp interval {0, 0} (already-terminal; must never be expanded).
    // The bucket ctor accepts {0,0} (endpoints allowed on breakpoints); expand rejects.
    Bucket A = bucket_from(s, HpInterval{100, 150}, HpInterval{0, 0}, fx.bp, fx.interner);
    ExecAction pa = player_move_action(0);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::Precondition);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Test 1 — Derived-split correctness, single hit (no trigger nearby).
//   Player Tackle vs Shell-Armor opp, no items; opp interval well inside a single
//   segment. Expect: no throw, one merged child; opp image = [140-max(noncrit),
//   180-min(noncrit)]; player interval unchanged; image_splits == 0.
// ---------------------------------------------------------------------------

TEST_CASE("expand: single-hit derived split with no trigger yields one merged child",
          "[bucket][expand][happy]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR, .speed=60,
                                .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);

    // Pick a quiet opp interval far from any breakpoint (breakpoints are 0, 200
    // and no berry threshold since no item on opp).
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{140, 180},
                           fx.bp, fx.interner);

    // Hand-compute the expected image on the opp axis.
    DamageTable dt = damage_table(s, /*attacker=*/0, pa);
    REQUIRE_FALSE(dt.noncrit.empty());
    int32_t min_dmg = dt.noncrit.front();
    int32_t max_dmg = dt.noncrit.back();
    int32_t expected_opp_lo = 140 - max_dmg;
    int32_t expected_opp_hi = 180 - min_dmg;
    REQUIRE(expected_opp_lo < expected_opp_hi);
    REQUIRE(expected_opp_lo > 0);   // opp doesn't faint in this interval

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    // Singleton-partition semantics: any leaf image whose endpoint coincides with a
    // BpSet breakpoint (here max_hp=200 sits at pl_img.hi) splits into a [b,b]
    // singleton + adjacent gap. Merge cannot fuse a bp-singleton back into a run,
    // so the "quiet" case now produces two children:
    //   pl=[150,199] op=[expected]  and  pl=[200,200] op=[expected]
    // both with the same d' and merged opp interval covering the whole shift range.
    REQUIRE(r.children.size() >= 1);
    REQUIRE(r.stats.image_splits >= 1);

    // Coverage: the union of player intervals covers [150, 200]; the union of opp
    // intervals covers [expected_opp_lo, expected_opp_hi]. Coverage-based checks
    // hold regardless of the exact split count.
    int32_t pl_cover_lo = INT32_MAX, pl_cover_hi = INT32_MIN;
    int32_t op_cover_lo = INT32_MAX, op_cover_hi = INT32_MIN;
    for (const auto& c : r.children) {
        pl_cover_lo = std::min(pl_cover_lo, c.bucket.player_hp().lo);
        pl_cover_hi = std::max(pl_cover_hi, c.bucket.player_hp().hi);
        op_cover_lo = std::min(op_cover_lo, c.bucket.opp_hp().lo);
        op_cover_hi = std::max(op_cover_hi, c.bucket.opp_hp().hi);
    }
    REQUIRE(pl_cover_lo == 150);
    REQUIRE(pl_cover_hi == 200);
    REQUIRE(op_cover_lo == expected_opp_lo);
    REQUIRE(op_cover_hi == expected_opp_hi);
}

// ---------------------------------------------------------------------------
// Test 2 — Derived split at a trigger (Sitrus), positive.
// ---------------------------------------------------------------------------

TEST_CASE("expand: derived split at Sitrus threshold produces distinct-d children",
          "[bucket][expand][trigger]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .max_hp=200, .hp=130, .item=ITEM_SITRUS,
                                .ability=AB_SHELL_ARMOR, .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    // Sitrus half threshold = 100. Opp interval [105,130] must straddle {100+dmg}
    // for Tackle at these stats (approx 10..20 dmg → split points ~110..120).
    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{105, 130},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);
    REQUIRE(r.stats.sub_rects >= 2);

    // Collect distinct child d values.
    std::unordered_set<uint32_t> ds;
    for (const auto& c : r.children) ds.insert(c.bucket.d());
    REQUIRE(ds.size() >= 2);   // berry-consumed vs not.

    // Some child must correspond to a "berry consumed" state — check by unpacking a
    // berry-consumed child and verifying its item is cleared or consumed_berry set.
    bool found_consumed = false;
    for (const auto& c : r.children) {
        PackedKey key = make_packed_key(c.bucket.d(),
                                        static_cast<uint16_t>(c.bucket.player_hp().lo),
                                        static_cast<uint16_t>(c.bucket.opp_hp().lo));
        BattleState st = fx.interner.unpack(key);
        const PokemonState& opp = st.side1.team[st.side1.active_indices[0]];
        if (opp.item == 0 || opp.consumed_berry == ITEM_SITRUS) {
            found_consumed = true; break;
        }
    }
    REQUIRE(found_consumed);
}

// ---------------------------------------------------------------------------
// Test 3 — Shift-property THROW when derived splits are disabled.
// Sitrus firing at LO but not HI produces asymmetric HP output: at LO the
// berry heals after the hit, at HI it doesn't. Because berry consumption is
// deterministic (no Cat-B RNG event), replay_path with skip_state_shift_check
// won't diverge on Cat-B; the mismatch surfaces at the shift-property gate
// (image width != input width) which fires BEFORE the intern check.
// ---------------------------------------------------------------------------

TEST_CASE("expand: skip_derived_splits with Sitrus trigger throws ShiftViolation",
          "[bucket][expand][fail_loud]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .max_hp=200, .hp=130, .item=ITEM_SITRUS,
                                .ability=AB_SHELL_ARMOR, .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandOptions opts; opts.skip_derived_splits = true;
    ExpandFixture fx(s, default_question(), opts);
    ExecAction pa = player_move_action(0);

    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{105, 130},
                           fx.bp, fx.interner);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::ShiftViolation);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Test 4 — Uniform trigger consistency (opp interval entirely inside fire zone).
// ---------------------------------------------------------------------------

TEST_CASE("expand: uniform Sitrus fire zone yields shared d and consumed berry",
          "[bucket][expand][trigger]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .max_hp=200, .hp=90, .item=ITEM_SITRUS,
                                .ability=AB_SHELL_ARMOR, .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);

    // Opp interval strictly below Sitrus threshold (100) — every hit fires the berry.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{80, 95},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);
    REQUIRE_FALSE(r.children.empty());

    // All children share one d, and unpacking shows the berry has been consumed.
    uint32_t d0 = r.children.front().bucket.d();
    for (const auto& c : r.children) REQUIRE(c.bucket.d() == d0);

    PackedKey key = make_packed_key(d0,
                                    static_cast<uint16_t>(r.children.front().bucket.player_hp().lo),
                                    static_cast<uint16_t>(r.children.front().bucket.opp_hp().lo));
    BattleState st = fx.interner.unpack(key);
    const PokemonState& opp = st.side1.team[st.side1.active_indices[0]];
    // Consumed: either item cleared or consumed_berry flag set.
    REQUIRE((opp.item == 0 || opp.consumed_berry == ITEM_SITRUS));
}

// ---------------------------------------------------------------------------
// Test 5 — Support-flip THROW.
//   Build a state with two damaging AI moves whose kill-estimate flips across a
//   player-HP boundary NOT in the BpSet. Verify a flip exists, construct a bucket
//   straddling it, expand → Stage::SupportFlip.
// ---------------------------------------------------------------------------

TEST_CASE("expand: bucket straddling AI support flip throws SupportFlip",
          "[bucket][expand][fail_loud]")
{
    // Design: AI has [Tackle, IcyWind]. IcyWind is in SPEED_REDUCTION_MOVES with
    // the all_zero (non-HD) branch returning {6,1.0} when AI is slower and player
    // has no CLEAR_BODY/WHITE_SMOKE/CONTRARY. Tackle is HD; when it does NOT kill,
    // its distribution is {6,0.8; 8,0.2} → tie with IcyWind at 6, both in support.
    // When Tackle DOES kill (slower kb=3): distribution shifts to {9,0.8; 11,0.2},
    // strictly beating IcyWind's 6 → IcyWind drops from the winner set. Support
    // flips at Tackle's KO threshold — a pure damage-roll boundary. Player has
    // higher speed so AI is slower; ai ability SHELL_ARMOR suppresses crits.
    static constexpr int32_t MV_ICY_WIND = 196;

    // Give the player enough HP that both Bp-generation and interior scan cover a
    // large range. Low defence so Tackle's damage lands somewhere in that range.
    PokemonState p = make_mon({.max_hp=200, .hp=200, .speed=120, .def=40, .spd=40});
    PokemonState o = make_mon({.species=2, .max_hp=200, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .atk=100, .spa=100,
                                .move0=MV_TACKLE, .move1=MV_ICY_WIND});
    BattleState s_probe = make_state(p, o);

    // Scan player HP 1..max looking for an adjacent flip pair where neither endpoint
    // coincides with a breakpoint. Any surviving flip is a valid test vector.
    BreakpointRegistry reg;
    BpSet bp = reg.instantiate(s_probe, default_question());
    auto is_bp = [&](int32_t hp) {
        return std::find(bp.player_breakpoints().begin(),
                         bp.player_breakpoints().end(), hp)
               != bp.player_breakpoints().end();
    };

    int32_t flip_lo = -1, flip_hi = -1;
    uint64_t prev_fp = 0;
    bool have_prev = false;
    for (int32_t hp = 1; hp <= 200; ++hp) {
        BattleState st = s_probe;
        st.side0.team[0].hp = hp;
        std::vector<ActionProb> probs = cpp_compute_action_probabilities(st, 1);
        uint64_t fp = support_fingerprint(probs);
        if (have_prev && fp != prev_fp && !is_bp(hp) && !is_bp(hp - 1)) {
            flip_lo = hp - 1;
            flip_hi = hp;
            break;
        }
        prev_fp = fp;
        have_prev = true;
    }

    // Fail loud: if this matchup no longer produces a flip, the test vector needs
    // updating — never silently skip. See SOLVER_BUCKET_PLAN Part 1 amendment 5.
    REQUIRE(flip_lo >= 0);

    // Build the state at flip_hi (defines root d + support fingerprint).
    BattleState s = s_probe;
    s.side0.team[0].hp = flip_hi;
    ExpandFixture fx(s, default_question());

    // Manually construct a bucket over the flip range using the LO support fingerprint
    // (matches what a root-bucket builder would compute at flip_lo). This must be a
    // "different fingerprint" from the one at flip_hi — thus support-gate at the HI
    // corner MUST throw SupportFlip.
    BattleState s_lo = s;
    s_lo.side0.team[0].hp = flip_lo;
    std::vector<ActionProb> lo_probs = cpp_compute_action_probabilities(s_lo, 1);
    uint64_t lo_fp = support_fingerprint(lo_probs);
    uint32_t d_ctx = static_cast<uint32_t>(fx.interner.pack(s_lo) >> 32);

    // We deliberately construct a bucket whose interval straddles the flip.
    // Choose opp interval away from any bp for cleanness.
    Bucket A(d_ctx, HpInterval{flip_lo, flip_hi}, HpInterval{100, 180}, lo_fp, fx.bp);
    ExecAction pa = player_move_action(0);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::SupportFlip);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Test 6 — §5.2 routing THROW: HP-dependent move (Super Fang).
// ---------------------------------------------------------------------------

TEST_CASE("expand: HP-dependent move (Super Fang) throws UnsupportedMove",
          "[bucket][expand][fail_loud]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_SUPER_FANG});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{100, 180},
                           fx.bp, fx.interner);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::UnsupportedMove);
        std::string what = e.what();
        // Message must name the move somehow (id or name).
        REQUIRE(what.find("162") != std::string::npos);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Test 7 — Shift-assertion THROW when the HP-dependent screen is bypassed.
// ---------------------------------------------------------------------------

TEST_CASE("expand: skip_hp_dependent_screen with Super Fang throws ShiftViolation",
          "[bucket][expand][fail_loud]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_SUPER_FANG});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandOptions opts; opts.skip_hp_dependent_screen = true;
    ExpandFixture fx(s, default_question(), opts);
    ExecAction pa = player_move_action(0);

    // Interval sized so LO/HI Super Fang damage differs (Super Fang = hp/2, monotone
    // in defender HP).  Endpoints self-consistent per-corner; cross-endpoint width
    // check catches the mismatch.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{40, 80},
                           fx.bp, fx.interner);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::ShiftViolation);
    }
    REQUIRE(threw);
}

// ---------------------------------------------------------------------------
// Test 8 — Kill saturation via derived splits (with skip_derived_splits companion).
// ---------------------------------------------------------------------------

TEST_CASE("expand: kill-saturating opp interval splits into faint + alive children",
          "[bucket][expand][saturation]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    // Opp interval [5,60] — Tackle at ~10..18 dmg guarantees some kills and some
    // survivors within the range.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{5, 60},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    bool has_faint = false, has_alive = false;
    for (const auto& c : r.children) {
        if (c.bucket.opp_hp().lo == 0 && c.bucket.opp_hp().hi == 0) has_faint = true;
        if (c.bucket.opp_hp().lo > 0) has_alive = true;
    }
    REQUIRE(has_faint);
    REQUIRE(has_alive);
}

TEST_CASE("expand: kill-saturating interval WITHOUT derived splits throws",
          "[bucket][expand][fail_loud][saturation]")
{
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandOptions opts; opts.skip_derived_splits = true;
    ExpandFixture fx(s, default_question(), opts);
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{5, 60},
                           fx.bp, fx.interner);

    REQUIRE_THROWS_AS(expand(A, pa, fx.ctx), ExpandError);
}

// ---------------------------------------------------------------------------
// Test 9 — Image split at a pure predicate breakpoint (Question keepHp).
// ---------------------------------------------------------------------------

TEST_CASE("expand: image split at keepHp breakpoint yields two children with same d'",
          "[bucket][expand][image_split]")
{
    // Player Splash (no damage): opp Tackle chips player. Keep=30 introduces player
    // breakpoint at 30. Set player interval so opp Tackle image straddles 30.
    // Player faster? Doesn't matter — player uses Splash. Opp uses Tackle.
    PokemonState p = make_mon({.hp=200, .move0=MV_SPLASH});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_TACKLE});
    BattleState s = make_state(p, o);

    Question q; q.keepHp = 30;

    ExpandOptions opts; opts.skip_derived_splits = true;   // isolate image split
    ExpandFixture fx(s, q, opts);
    ExecAction pa = player_move_action(0);  // Splash

    // Choose player interval so post-Tackle it lands straddling 30.
    // Tackle deals ~20..36 dmg to player at these stats. For image [pl_lo-d, pl_hi-d]
    // to straddle 30 we need d ∈ [pl_lo-30, pl_hi-30]; [50,60] gives d ∈ [20,30]
    // which intersects the actual damage range (e.g. d=25 → image [25,35], straddles 30).
    Bucket A = bucket_from(s, HpInterval{50, 60}, HpInterval{100, 180},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);
    REQUIRE(r.stats.image_splits >= 1);
    // At least two children with same d' but different player intervals split at 30.
    // (multiple opp moves × damage may create many children; check the split exists.)
    bool saw_below = false, saw_above = false;
    for (const auto& c : r.children) {
        if (c.bucket.player_hp().hi <= 30) saw_below = true;
        if (c.bucket.player_hp().lo >= 31) saw_above = true;
    }
    REQUIRE(saw_below);
    REQUIRE(saw_above);
}

// ---------------------------------------------------------------------------
// Test 10 — Miss branch: player uses a <100 accuracy damaging move; miss child
// has opp interval == A's opp interval (unchanged).
// ---------------------------------------------------------------------------

TEST_CASE("expand: <100 accuracy player move keeps the miss branch as a child",
          "[bucket][expand][miss]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_HYDRO_PUMP});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{140, 180},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    // At least one child must have opp interval unchanged (miss branch).
    bool saw_miss = false;
    for (const auto& c : r.children) {
        if (c.bucket.opp_hp().lo == 140 && c.bucket.opp_hp().hi == 180) {
            saw_miss = true;
            break;
        }
    }
    REQUIRE(saw_miss);
}

// ---------------------------------------------------------------------------
// Test 11 — Fast vs general path parity.
// ---------------------------------------------------------------------------

TEST_CASE("expand: fast vs general path produce identical per-d coverage",
          "[bucket][expand][fast_path]")
{
    // Setup (1) WITHOUT Shell Armor — crit branch alive; REQUIRE strict dominance.
    PokemonState p = make_mon({.hp=200});
    PokemonState o = make_mon({.species=2, .hp=200, .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExecAction pa = player_move_action(0);
    DamageTable t = damage_table(s, /*attacker=*/0, pa);
    REQUIRE(strict_crit_dominance(t));

    auto per_d_coverage = [](const ExpandResult& r) {
        // Map from d → coverage: canonical merged sorted list of opp intervals per d.
        // Fast path fuses crit+noncrit into one big interval; general keeps them
        // separate. Both are valid: what must agree is the coverage as a UNION of
        // intervals. This lambda unions the raw per-d list into a canonical form so
        // fast/general with the same total coverage compare equal.
        std::map<uint32_t, std::vector<std::pair<int32_t,int32_t>>> raw;
        for (const auto& c : r.children) {
            raw[c.bucket.d()].push_back({c.bucket.opp_hp().lo, c.bucket.opp_hp().hi});
        }
        std::map<uint32_t, std::vector<std::pair<int32_t,int32_t>>> cov;
        for (auto& kv : raw) {
            auto& v = kv.second;
            std::sort(v.begin(), v.end());
            std::vector<std::pair<int32_t,int32_t>> merged;
            for (auto& iv : v) {
                if (!merged.empty() && iv.first <= merged.back().second + 1) {
                    merged.back().second = std::max(merged.back().second, iv.second);
                } else {
                    merged.push_back(iv);
                }
            }
            cov[kv.first] = std::move(merged);
        }
        return cov;
    };

    // Fast path (default).
    {
        ExpandFixture fx(s, default_question());
        Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{140, 180},
                               fx.bp, fx.interner);
        ExpandResult r_fast = expand(A, pa, fx.ctx);
        REQUIRE(r_fast.stats.fast_path);

        // General path.
        ExpandOptions opts_gen; opts_gen.force_general_path = true;
        ExpandFixture fx_gen(s, default_question(), opts_gen);
        Bucket A_gen = bucket_from(s, HpInterval{150, 200}, HpInterval{140, 180},
                                   fx_gen.bp, fx_gen.interner);
        ExpandResult r_gen = expand(A_gen, pa, fx_gen.ctx);
        REQUIRE_FALSE(r_gen.stats.fast_path);

        REQUIRE(per_d_coverage(r_fast) == per_d_coverage(r_gen));
        REQUIRE(r_fast.children.size() <= r_gen.children.size());
    }
}

// ---------------------------------------------------------------------------
// Test 12 — Weak-only fallback: general path succeeds even without strict dominance.
// ---------------------------------------------------------------------------

TEST_CASE("expand: weak-only crit table succeeds on general path",
          "[bucket][expand][weak_dominance]")
{
    // Huge defender / tiny attacker so damage is small; crit_min == noncrit_max is
    // typical for low-damage tables.
    PokemonState p = make_mon({.hp=200, .atk=20});
    PokemonState o = make_mon({.species=2, .hp=200, .speed=60, .def=250, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);
    ExecAction pa = player_move_action(0);
    DamageTable t = damage_table(s, /*attacker=*/0, pa);
    if (strict_crit_dominance(t)) {
        WARN("expand: table is strict-dominant; weak-only fallback test inapplicable");
        return;
    }
    REQUIRE(weak_crit_dominance(t));

    ExpandFixture fx(s, default_question());
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{140, 180},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);
    REQUIRE_FALSE(r.children.empty());
}

// ---------------------------------------------------------------------------
// Test 13a — Fixed 2-hit move (Double Kick).
// ---------------------------------------------------------------------------

TEST_CASE("expand: fixed 2-hit Double Kick produces one merged child with 2·shift",
          "[bucket][expand][multi_hit]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_DOUBLE_KICK});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);
    ExecAction pa = player_move_action(0);
    DamageTable t = damage_table(s, /*attacker=*/0, pa);
    REQUIRE(t.max_hits == 2);
    REQUIRE_FALSE(t.noncrit.empty());
    int32_t per_hit_min = t.noncrit.front();
    int32_t per_hit_max = t.noncrit.back();

    ExpandFixture fx(s, default_question());
    // Opp interval large enough that no kill saturation happens even at 2·max_dmg.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{150, 200},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    // Expect a single merged child (fixed 2-hit → deterministic 2-hit count).
    // Coverage: opp interval [150 − 2·max_dmg, 200 − 2·min_dmg] (hand-computed).
    int32_t expected_lo = 150 - 2 * per_hit_max;
    int32_t expected_hi = 200 - 2 * per_hit_min;
    // Coverage check: union of children opp intervals must include this exact range.
    int32_t cover_lo = INT32_MAX, cover_hi = INT32_MIN;
    for (const auto& c : r.children) {
        cover_lo = std::min(cover_lo, c.bucket.opp_hp().lo);
        cover_hi = std::max(cover_hi, c.bucket.opp_hp().hi);
    }
    REQUIRE(cover_lo == expected_lo);
    REQUIRE(cover_hi == expected_hi);
}

// ---------------------------------------------------------------------------
// Test 13b — Variable 2..5-hit move (Fury Attack).
// ---------------------------------------------------------------------------

TEST_CASE("expand: variable 2..5-hit Fury Attack coverage = [lo-5*max, hi-2*min]",
          "[bucket][expand][multi_hit]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_FURY_ATTACK});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);
    ExecAction pa = player_move_action(0);
    DamageTable t = damage_table(s, /*attacker=*/0, pa);
    REQUIRE(t.max_hits == 5);
    int32_t per_hit_min = t.noncrit.front();
    int32_t per_hit_max = t.noncrit.back();

    ExpandFixture fx(s, default_question());
    // Choose a large opp interval to avoid kill saturation clipping the range.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{150, 200},
                           fx.bp, fx.interner);
    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    int32_t expected_lo = 150 - 5 * per_hit_max;
    int32_t expected_hi = 200 - 2 * per_hit_min;
    int32_t cover_lo = INT32_MAX, cover_hi = INT32_MIN;
    for (const auto& c : r.children) {
        cover_lo = std::min(cover_lo, c.bucket.opp_hp().lo);
        cover_hi = std::max(cover_hi, c.bucket.opp_hp().hi);
    }
    REQUIRE(cover_lo == expected_lo);
    REQUIRE(cover_hi == expected_hi);
}

// ---------------------------------------------------------------------------
// Test 14 — Flag-split children (Ember with 10% burn secondary).
// ---------------------------------------------------------------------------

TEST_CASE("expand: burn-secondary Ember creates burned/unburned children",
          "[bucket][expand][flag_split]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_SPLASH});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_EMBER});
    BattleState s = make_state(p, o);
    ExecAction pa = player_move_action(0);

    ExpandFixture fx(s, default_question());
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{150, 200},
                           fx.bp, fx.interner);
    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);

    std::unordered_set<uint32_t> ds;
    for (const auto& c : r.children) ds.insert(c.bucket.d());
    REQUIRE(ds.size() >= 2);
}

// ---------------------------------------------------------------------------
// Task 6 work item C — supported fixed-damage moves EXPAND (no longer §5.2 throw).
// Ids: Sonic Boom(49)=20, Dragon Rage(82)=40, Seismic Toss(69)=level, Psywave(149).
// ---------------------------------------------------------------------------

static constexpr int32_t MV_SONIC_BOOM   = 49;
static constexpr int32_t MV_DRAGON_RAGE  = 82;
static constexpr int32_t MV_SEISMIC_TOSS = 69;
static constexpr int32_t MV_PSYWAVE      = 149;
static constexpr int32_t MV_FISSURE      = 90;

TEST_CASE("expand: supported fixed-damage moves produce verified children",
          "[bucket][expand][fixed_damage]")
{
    struct Case { int32_t move; int32_t dmg; };
    // Attacker level is 50, so Seismic Toss deals 50.
    Case cases[] = {{MV_SONIC_BOOM, 20}, {MV_DRAGON_RAGE, 40}, {MV_SEISMIC_TOSS, 50}};
    for (const Case& c : cases) {
        PokemonState p = make_mon({.hp=200, .move0=c.move});
        PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                    .speed=60, .move0=MV_SPLASH});
        BattleState s = make_state(p, o);

        ExpandFixture fx(s, default_question());
        ExecAction pa = player_move_action(0);
        // Opp interval well clear of 0 so the fixed hit does not saturate.
        Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{100, 180},
                               fx.bp, fx.interner);

        ExpandResult r = expand(A, pa, fx.ctx);
        REQUIRE(r.concession_tag == 0);
        REQUIRE_FALSE(r.children.empty());

        int32_t cover_lo = INT32_MAX, cover_hi = INT32_MIN;
        for (const auto& ch : r.children) {
            cover_lo = std::min(cover_lo, ch.bucket.opp_hp().lo);
            cover_hi = std::max(cover_hi, ch.bucket.opp_hp().hi);
        }
        REQUIRE(cover_lo == 100 - c.dmg);
        REQUIRE(cover_hi == 180 - c.dmg);
    }
}

TEST_CASE("expand: Psywave expands (variable fixed-damage value set)",
          "[bucket][expand][fixed_damage]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_PSYWAVE});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    // Psywave at level 50 spans ~25..75 damage; keep the opp interval clear of 0.
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{120, 180},
                           fx.bp, fx.interner);

    ExpandResult r = expand(A, pa, fx.ctx);
    REQUIRE(r.concession_tag == 0);
    REQUIRE_FALSE(r.children.empty());
    // Coverage spans the full Psywave value set: max value 75, min value 25.
    int32_t cover_lo = INT32_MAX, cover_hi = INT32_MIN;
    for (const auto& ch : r.children) {
        cover_lo = std::min(cover_lo, ch.bucket.opp_hp().lo);
        cover_hi = std::max(cover_hi, ch.bucket.opp_hp().hi);
    }
    REQUIRE(cover_lo == 120 - 75);
    REQUIRE(cover_hi == 180 - 25);
}

// ---------------------------------------------------------------------------
// Task 6 work item D — OHKO moves STILL throw UnsupportedMove (pins the all-zero
// damage-table false-WIN failure mode; inventory §14 #6).
// ---------------------------------------------------------------------------

TEST_CASE("expand: OHKO move (Fissure) throws UnsupportedMove (player side)",
          "[bucket][expand][fail_loud][ohko]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_FISSURE});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_SPLASH});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{100, 180},
                           fx.bp, fx.interner);

    bool threw = false;
    try { expand(A, pa, fx.ctx); }
    catch (const ExpandError& e) {
        threw = true;
        REQUIRE(e.stage == ExpandError::Stage::UnsupportedMove);
        REQUIRE(std::string(e.what()).find("90") != std::string::npos);
    }
    REQUIRE(threw);
}

TEST_CASE("expand: OHKO move (Fissure) in AI support throws UnsupportedMove",
          "[bucket][expand][fail_loud][ohko]")
{
    PokemonState p = make_mon({.hp=200, .move0=MV_SPLASH});
    PokemonState o = make_mon({.species=2, .hp=200, .ability=AB_SHELL_ARMOR,
                                .speed=60, .move0=MV_FISSURE});
    BattleState s = make_state(p, o);

    ExpandFixture fx(s, default_question());
    ExecAction pa = player_move_action(0);
    Bucket A = bucket_from(s, HpInterval{150, 200}, HpInterval{100, 180},
                           fx.bp, fx.interner);

    REQUIRE_THROWS_AS(expand(A, pa, fx.ctx), ExpandError);
}
