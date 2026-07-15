// Bucket solver Task 6 tests: concede detectors. Tests written BEFORE implementation.
// Baseline: P{Tackle, speed 100} vs O{Tackle, speed 80}, 200/200 HP, no items/abilities.
// Most tests call concede_tags(s, s, act) and CHECK exact masks. The Yawn regression
// (test 2) is the most important: VE_DROWSY must NEVER fire a concession.
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/concede.h"
#include "solver/bucket/expand.h"
#include "solver/engine_queries.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "state.h"

#include <cstdint>
#include <string>

// ---- Move / item / ability / status ids (generated/enum_names.h + effects_consts.h) ----
static constexpr int32_t MV_TACKLE = 33, MV_SPLASH = 150, MV_OUTRAGE = 200, MV_THRASH = 37;
static constexpr int32_t MV_HYPER_BEAM = 63, MV_BITE = 44, MV_QUICK_ATTACK = 98;
static constexpr int32_t MV_SUPER_FANG = 162, MV_FLAIL = 175, MV_FURY_ATTACK = 31;
static constexpr int32_t MV_SEISMIC_TOSS = 69, MV_NIGHT_SHADE = 101, MV_FISSURE = 90;
static constexpr int32_t MV_SUBSTITUTE = 164;

static constexpr int32_t ITEM_SITRUS = 158, ITEM_QUICK_CLAW = 217, ITEM_KINGS_ROCK = 221;
static constexpr int32_t ITEM_METRONOME = 277, ITEM_OCCA = 184;
static constexpr int32_t AB_SHELL_ARMOR = 75, AB_QUICK_DRAW = 259, AB_INNER_FOCUS = 39;
static constexpr int32_t AB_PARENTAL_BOND = 185;

static constexpr int32_t STATUS_FREEZE = 2, STATUS_PARALYSIS = 3, STATUS_SLEEP = 6;
static constexpr int32_t V_CONFUSED = 1, V_MINIMIZE = 1024, V_SUBSTITUTE = 4096;
static constexpr int32_t V_RECHARGING = 256, V_ATTRACTED = 8388608;
static constexpr int32_t VE_DROWSY = 20;

// ---------------------------------------------------------------------------
// State helpers (mirror test_bucket_expand.cpp conventions, level 50).
// ---------------------------------------------------------------------------

struct MonSpec {
    int32_t species = 1;
    int32_t max_hp  = 200;
    int32_t hp      = 200;
    int32_t item    = 0;
    int32_t ability = 0;
    int32_t speed   = 100;
    int32_t atk     = 100;
    int32_t def     = 80;
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
    p.stat_spa   = sp.atk;
    p.stat_spd   = sp.def;
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

static ExecAction move_action(int slot = 0) {
    ExecAction a{};
    a.kind = 0; a.move_slot = slot;
    a.source_slot = 0; a.target_side = 1; a.target_slot = 0;
    return a;
}

// Baseline P vs O; O gets Shell Armor by default to suppress crit noise in damage tables.
static BattleState baseline() {
    PokemonState p = make_mon({.speed = 100});
    PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
    return make_state(p, o);
}

static uint32_t tags_of(const BattleState& s, const ExecAction& a = move_action(0)) {
    return concede_tags(s, s, a);
}

// ===========================================================================
// 1. Clean baseline → 0.
// ===========================================================================
TEST_CASE("concede: clean baseline is no concession", "[bucket][concede]") {
    REQUIRE(tags_of(baseline()) == CONCEDE_NONE);
}

// ===========================================================================
// 2. YAWN REGRESSION (most important): drowsy never fires; asleep does.
// ===========================================================================
TEST_CASE("concede: Yawn-pending (VE_DROWSY) never concedes", "[bucket][concede][yawn]") {
    BattleState s = baseline();
    PokemonState& p = s.side0.team[0];
    p.status = 0;                                    // NOT asleep yet
    p.timed_volatiles.push_back(TimedVolatile{VE_DROWSY, 1});
    REQUIRE(tags_of(s) == CONCEDE_NONE);
}

TEST_CASE("concede: asleep concedes SLEEP_ACTING", "[bucket][concede][yawn]") {
    BattleState s = baseline();
    PokemonState& p = s.side0.team[0];
    p.status = STATUS_SLEEP; p.sleep_turns = 2;
    REQUIRE(tags_of(s) == CONCEDE_SLEEP_ACTING);
}

TEST_CASE("concede: Rest self-sleep concedes SLEEP_ACTING", "[bucket][concede][yawn]") {
    BattleState s = baseline();
    PokemonState& p = s.side0.team[0];
    p.status = STATUS_SLEEP; p.sleep_turns = 3;      // Rest sets a full sleep
    REQUIRE(tags_of(s) == CONCEDE_SLEEP_ACTING);
}

// ===========================================================================
// 3. Freeze / paralysis.
// ===========================================================================
TEST_CASE("concede: freeze / paralysis (player side)", "[bucket][concede]") {
    {
        BattleState s = baseline();
        s.side0.team[0].status = STATUS_FREEZE;
        REQUIRE(tags_of(s) == CONCEDE_FREEZE);
    }
    {
        BattleState s = baseline();
        s.side0.team[0].status = STATUS_PARALYSIS;   // halved 50 vs opp 80: no order tie
        REQUIRE(tags_of(s) == CONCEDE_PARALYSIS);
    }
}

// ===========================================================================
// 4/5. Confusion — player concedes, opponent does NOT.
// ===========================================================================
TEST_CASE("concede: player confusion concedes; opponent confusion does not",
          "[bucket][concede]") {
    {
        BattleState s = baseline();
        s.side0.team[0].volatiles |= V_CONFUSED;
        REQUIRE(tags_of(s) == CONCEDE_CONFUSION);
    }
    {
        BattleState s = baseline();
        s.side1.team[0].volatiles |= V_CONFUSED;     // opp confused — adversarial, not conceded
        REQUIRE(tags_of(s) == CONCEDE_NONE);
    }
}

// ===========================================================================
// 6. Attract (player).
// ===========================================================================
TEST_CASE("concede: player attracted concedes ATTRACT", "[bucket][concede]") {
    BattleState s = baseline();
    s.side0.team[0].volatiles |= V_ATTRACTED;
    REQUIRE(tags_of(s) == CONCEDE_ATTRACT);
}

// ===========================================================================
// 7. Lock moves (Outrage / Thrash).
// ===========================================================================
TEST_CASE("concede: player rampage move concedes LOCK_MOVE", "[bucket][concede]") {
    {
        PokemonState p = make_mon({.move0 = MV_OUTRAGE});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_LOCK_MOVE);
    }
    {
        PokemonState p = make_mon({.move0 = MV_THRASH});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_LOCK_MOVE);
    }
}

// ===========================================================================
// 8. Recharge (Hyper Beam / V_RECHARGING / forced recharge action).
// ===========================================================================
TEST_CASE("concede: recharge lines concede RECHARGE", "[bucket][concede]") {
    {
        PokemonState p = make_mon({.move0 = MV_HYPER_BEAM});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_RECHARGE);
    }
    {
        BattleState s = baseline();
        s.side0.team[0].volatiles |= V_RECHARGING;
        REQUIRE(tags_of(s) == CONCEDE_RECHARGE);
    }
    {
        BattleState s = baseline();
        ExecAction forced{};                          // kind=0, move_slot=-1, override=-1
        forced.kind = 0; forced.move_slot = -1;
        REQUIRE(concede_tags(s, s, forced) == CONCEDE_RECHARGE);
    }
}

// ===========================================================================
// 9. Flinch while slower.
// ===========================================================================
TEST_CASE("concede: opponent flinch move while player slower → FLINCH_SLOWER",
          "[bucket][concede][flinch]") {
    auto make = [](int32_t p_speed, int32_t p_ability, int32_t p_move,
                   int32_t o_item, int32_t o_move) {
        PokemonState p = make_mon({.ability = p_ability, .speed = p_speed, .move0 = p_move});
        PokemonState o = make_mon({.species = 2, .item = o_item, .ability = AB_SHELL_ARMOR,
                                    .speed = 100, .move0 = o_move});
        return make_state(p, o);
    };

    // Opponent Bite (30% flinch), opponent faster → exactly FLINCH_SLOWER.
    REQUIRE(tags_of(make(60, 0, MV_TACKLE, 0, MV_BITE)) == CONCEDE_FLINCH_SLOWER);

    // Player strictly faster → no flinch tag.
    REQUIRE(tags_of(make(140, 0, MV_TACKLE, 0, MV_BITE)) == CONCEDE_NONE);

    // Player slower but uses a priority move (Quick Attack) → acts first → 0.
    REQUIRE(tags_of(make(60, 0, MV_QUICK_ATTACK, 0, MV_BITE)) == CONCEDE_NONE);

    // Player Inner Focus, slower → immune to flinch → 0.
    REQUIRE(tags_of(make(60, AB_INNER_FOCUS, MV_TACKLE, 0, MV_BITE)) == CONCEDE_NONE);

    // King's Rock on a plain damaging move, opponent faster → FLINCH_SLOWER.
    REQUIRE(tags_of(make(60, 0, MV_TACKLE, ITEM_KINGS_ROCK, MV_TACKLE)) == CONCEDE_FLINCH_SLOWER);
}

// ===========================================================================
// 10. Order RNG (speed tie / Quick Claw / Quick Draw).
// ===========================================================================
TEST_CASE("concede: order RNG (speed tie, Quick Claw, Quick Draw)", "[bucket][concede][order]") {
    // Speed tie both 100.
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 100});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_ORDER_RNG);
    }
    // Quick Claw present (speeds differ so only the item triggers).
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .item = ITEM_QUICK_CLAW,
                                    .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_ORDER_RNG);
    }
    // Quick Draw ability present.
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_QUICK_DRAW, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_ORDER_RNG);
    }
}

// ===========================================================================
// 11. HP-dependent moves.
// ===========================================================================
TEST_CASE("concede: HP-dependent moves concede HP_DEP_MOVE", "[bucket][concede]") {
    {
        PokemonState p = make_mon({.move0 = MV_SUPER_FANG});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_HP_DEP_MOVE);
    }
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80,
                                    .move0 = MV_FLAIL});
        REQUIRE((tags_of(make_state(p, o)) & CONCEDE_HP_DEP_MOVE) != 0);
    }
}

// ===========================================================================
// 12. Supported fixed-damage moves are NOT conceded.
// ===========================================================================
TEST_CASE("concede: supported fixed-damage moves are not conceded", "[bucket][concede]") {
    {
        PokemonState p = make_mon({.move0 = MV_SEISMIC_TOSS});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_NONE);
    }
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80,
                                    .move0 = MV_NIGHT_SHADE});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_NONE);
    }
}

// ===========================================================================
// 13. OHKO move is not tagged HP_DEP_MOVE.
// ===========================================================================
TEST_CASE("concede: OHKO move never sets HP_DEP_MOVE", "[bucket][concede]") {
    PokemonState p = make_mon({.speed = 100});
    PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80,
                                .move0 = MV_FISSURE});
    REQUIRE((tags_of(make_state(p, o)) & CONCEDE_HP_DEP_MOVE) == 0);
}

// ===========================================================================
// 14. Multi-hit hard sub-case.
// ===========================================================================
TEST_CASE("concede: multi-hit that spans a heal threshold in one hit → MULTI_HIT_HARD",
          "[bucket][concede][multihit]") {
    // Player Fury Attack into a small Sitrus opponent; huge attack so one hit clears half.
    PokemonState p = make_mon({.speed = 100, .atk = 250, .move0 = MV_FURY_ATTACK});
    PokemonState o = make_mon({.species = 2, .max_hp = 30, .hp = 30, .item = ITEM_SITRUS,
                                .ability = AB_SHELL_ARMOR, .speed = 80, .def = 40});
    BattleState s = make_state(p, o);

    // Self-validating: max single hit must exceed the Sitrus half threshold (max_hp/2 = 15).
    DamageTable dt = damage_table(s, /*attacker=*/0, move_action(0));
    REQUIRE(dt.max_hits > 1);
    REQUIRE_FALSE(dt.noncrit.empty());
    REQUIRE(dt.noncrit.back() > 30 / 2);
    REQUIRE((tags_of(s) & CONCEDE_MULTI_HIT_HARD) != 0);

    // Easy sub-case: big defender, weak attacker — one hit cannot clear half → no tag.
    {
        PokemonState p2 = make_mon({.speed = 100, .atk = 20, .move0 = MV_FURY_ATTACK});
        PokemonState o2 = make_mon({.species = 2, .max_hp = 400, .hp = 400, .item = ITEM_SITRUS,
                                     .ability = AB_SHELL_ARMOR, .speed = 80, .def = 250});
        BattleState s2 = make_state(p2, o2);
        DamageTable dt2 = damage_table(s2, 0, move_action(0));
        REQUIRE(dt2.noncrit.back() < 400 / 2);
        REQUIRE((tags_of(s2) & CONCEDE_MULTI_HIT_HARD) == 0);
    }

    // No berry → no threshold → no tag.
    {
        PokemonState p3 = make_mon({.speed = 100, .atk = 250, .move0 = MV_FURY_ATTACK});
        PokemonState o3 = make_mon({.species = 2, .max_hp = 30, .hp = 30,
                                     .ability = AB_SHELL_ARMOR, .speed = 80, .def = 40});
        REQUIRE((tags_of(make_state(p3, o3)) & CONCEDE_MULTI_HIT_HARD) == 0);
    }

    // AI-side direction: opponent Fury Attack into a small-Sitrus player.
    {
        PokemonState p4 = make_mon({.max_hp = 30, .hp = 30, .item = ITEM_SITRUS,
                                     .speed = 80, .def = 40});
        PokemonState o4 = make_mon({.species = 2, .ability = AB_SHELL_ARMOR,
                                     .speed = 100, .atk = 250, .move0 = MV_FURY_ATTACK});
        REQUIRE((tags_of(make_state(p4, o4)) & CONCEDE_MULTI_HIT_HARD) != 0);
    }
}

// ===========================================================================
// 15. Substitute.
// ===========================================================================
TEST_CASE("concede: substitute (either active volatile, or player selecting it)",
          "[bucket][concede]") {
    {
        BattleState s = baseline();
        s.side0.team[0].volatiles |= V_SUBSTITUTE;
        s.side0.team[0].sub_hp = 50;
        REQUIRE(tags_of(s) == CONCEDE_SUBSTITUTE);
    }
    {
        BattleState s = baseline();
        s.side1.team[0].volatiles |= V_SUBSTITUTE;
        s.side1.team[0].sub_hp = 50;
        REQUIRE(tags_of(s) == CONCEDE_SUBSTITUTE);
    }
    {
        PokemonState p = make_mon({.speed = 100, .move0 = MV_SUBSTITUTE});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(tags_of(make_state(p, o)) == CONCEDE_SUBSTITUTE);
    }
}

// ===========================================================================
// 16. Damage-table caveats.
// ===========================================================================
TEST_CASE("concede: damage-table caveats set DMG_TABLE_CAVEAT", "[bucket][concede]") {
    auto has_caveat = [](const BattleState& s) {
        return (tags_of(s) & CONCEDE_DMG_TABLE_CAVEAT) != 0;
    };
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_PARENTAL_BOND, .speed = 80});
        REQUIRE(has_caveat(make_state(p, o)));
    }
    {
        PokemonState p = make_mon({.item = ITEM_METRONOME, .speed = 100});
        PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(has_caveat(make_state(p, o)));
    }
    {
        PokemonState p = make_mon({.speed = 100});
        PokemonState o = make_mon({.species = 2, .item = ITEM_OCCA,
                                    .ability = AB_SHELL_ARMOR, .speed = 80});
        REQUIRE(has_caveat(make_state(p, o)));
    }
    {
        BattleState s = baseline();
        s.side1.team[0].volatiles |= V_MINIMIZE;
        REQUIRE(has_caveat(s));
    }
}

// ===========================================================================
// 17. Union of tags across mechanics.
// ===========================================================================
TEST_CASE("concede: paralysis + Quick Claw → PARALYSIS|ORDER_RNG", "[bucket][concede]") {
    PokemonState p = make_mon({.speed = 100});
    PokemonState o = make_mon({.species = 2, .item = ITEM_QUICK_CLAW,
                                .ability = AB_SHELL_ARMOR, .speed = 80});
    BattleState s = make_state(p, o);
    s.side0.team[0].status = STATUS_PARALYSIS;
    REQUIRE(tags_of(s) == (CONCEDE_PARALYSIS | CONCEDE_ORDER_RNG));
}

// ===========================================================================
// 18. Expand seam integration.
// ===========================================================================
TEST_CASE("concede: Expand seam conceded vs clean", "[bucket][concede][expand]") {
    // Clean baseline first → non-empty children, tag 0.
    PokemonState p = make_mon({.speed = 100});
    PokemonState o = make_mon({.species = 2, .ability = AB_SHELL_ARMOR, .speed = 80,
                                .move0 = MV_SPLASH});
    BattleState clean = make_state(p, o);

    TransitionOracle oracle;
    BreakpointRegistry reg;
    Question q;
    ContextInterner interner;

    auto build_ctx = [&](BpSet& bp) {
        ExpandContext ctx;
        ctx.oracle = &oracle; ctx.interner = &interner; ctx.bp = &bp;
        ctx.concede = concede_tags;
        return ctx;
    };
    auto make_bucket = [&](const BattleState& st, const BpSet& bp) {
        uint32_t d = static_cast<uint32_t>(interner.pack(st) >> 32);
        std::vector<ActionProb> probs = cpp_compute_action_probabilities(st, 1);
        uint64_t fp = support_fingerprint(probs);
        return Bucket(d, HpInterval{150, 200}, HpInterval{140, 180}, fp, bp);
    };

    {
        BpSet bp = reg.instantiate(clean, q);
        ExpandContext ctx = build_ctx(bp);
        Bucket A = make_bucket(clean, bp);
        ExpandResult r = expand(A, move_action(0), ctx);
        REQUIRE(r.concession_tag == 0);
        REQUIRE_FALSE(r.children.empty());
    }

    // Player asleep → conceded, empty children.
    {
        BattleState asleep = clean;
        asleep.side0.team[0].status = STATUS_SLEEP;
        asleep.side0.team[0].sleep_turns = 2;
        BpSet bp = reg.instantiate(asleep, q);
        ExpandContext ctx = build_ctx(bp);
        Bucket A = make_bucket(asleep, bp);
        ExpandResult r = expand(A, move_action(0), ctx);
        REQUIRE((r.concession_tag & CONCEDE_SLEEP_ACTING) != 0);
        REQUIRE(r.children.empty());
    }
}

// ===========================================================================
// 19. concession_tag_names.
// ===========================================================================
TEST_CASE("concede: concession_tag_names formatting", "[bucket][concede]") {
    REQUIRE(concession_tag_names(0) == "");
    REQUIRE(concession_tag_names(CONCEDE_SLEEP_ACTING) == "SLEEP_ACTING");
    REQUIRE(concession_tag_names(CONCEDE_SLEEP_ACTING | CONCEDE_ORDER_RNG)
            == "SLEEP_ACTING|ORDER_RNG");
}
