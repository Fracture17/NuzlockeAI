// Catch2 tests for the E1a rich LogEvent-stream logger (event_log.h) and the five
// "silent" event emit sites wired into the engine mechanics.
// Verifies: POD guarantee, nullptr=off no-op, each emit helper records one correct
// entry, and real mechanic paths (charge/semi-invuln via cpp_pre_damage_checks,
// Psych Up via cpp_apply_status_move) fire the right events. Solver-turn isolation:
// with no rich log registered the direct solver entry records nothing and is unchanged.
#include <catch2/catch_test_macros.hpp>

#include <cstdint>
#include <type_traits>
#include <vector>

#include "event_log.h"
#include "state.h"
#include "move_exec_guards.h"     // cpp_pre_damage_checks, GuardLuck, ExecCtx
#include "effects.h"             // cpp_apply_status_move, EffectsLuck
#include "effects_internal.h"    // active_mon
#include "core_leaf.h"           // TurnLuck
#include "move_exec.h"           // ExecAction
#include "move_exec_damage.h"    // DamageLoopLuck
#include "oracle.h"              // OracleOverrides
#include "solver_turn.h"         // cpp_run_one_turn_solver
#include "effects_consts.h"      // STATUS_PARALYSIS

// Move ids (mirrors the constants in move_exec_guards.cpp).
static constexpr int32_t MV_FLY = 19, MV_SOLAR_BEAM = 76, MV_SKULL_BASH = 130,
                         MV_PSYCH_UP = 244;
static constexpr int32_t ITM_POWER_HERB = 271;      // engine/src/move_exec_guards.cpp
static constexpr int32_t WEATHER_HARSH_SUN_ID = 6;  // effects_consts.h WEATHER_HARSH_SUN

// LogEvent integer constants (liveplay/logger.py).
static constexpr int EV_CHARGE_TURN = 38, EV_SEMI_ENTER = 39, EV_SEMI_EXIT = 40,
                     EV_STAT_COPY = 55, EV_BATON_PASS = 92;

// ---------------------------------------------------------------------------
// (1) POD / trivially copyable guarantee
// ---------------------------------------------------------------------------

TEST_CASE("RichEventEntry is trivially copyable", "[rich_event][layout]") {
    static_assert(std::is_trivially_copyable_v<RichEventEntry>,
                  "RichEventEntry must be trivially copyable (POD)");
    SUCCEED();
}

// ---------------------------------------------------------------------------
// (2) Toggle off (nullptr): emit helpers are no-ops
// ---------------------------------------------------------------------------

TEST_CASE("Rich logger off (nullptr) records nothing", "[rich_event][toggle]") {
    set_rich_event_log(nullptr);
    rich_log_charge_turn(1, /*species=*/25, /*move=*/MV_FLY);
    rich_log_semi_invuln_enter(1, 25, MV_FLY);
    rich_log_semi_invuln_exit(1, 25, MV_FLY);
    rich_log_baton_pass_transfer(1, /*side=*/0, /*species=*/25);
    rich_log_stat_copy(1, /*side=*/0, /*copier=*/25, /*source=*/6);
    REQUIRE(get_rich_event_log() == nullptr);
}

// ---------------------------------------------------------------------------
// (3) Toggle on: each helper produces exactly one entry with correct fields
// ---------------------------------------------------------------------------

TEST_CASE("Each rich emit helper records one correct entry", "[rich_event][emit]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    rich_log_charge_turn(3, /*species=*/25, /*move=*/MV_FLY);
    rich_log_semi_invuln_enter(3, 25, MV_FLY);
    rich_log_semi_invuln_exit(4, 25, MV_FLY);
    rich_log_baton_pass_transfer(5, /*side=*/1, /*species=*/6);
    rich_log_stat_copy(6, /*side=*/0, /*copier=*/9, /*source=*/3);

    REQUIRE(sink.size() == 5);

    const RichEventEntry& c = sink.at(0);
    REQUIRE(c.event == EV_CHARGE_TURN);
    REQUIRE(c.turn == 3);
    REQUIRE(c.species == 25);
    REQUIRE(c.aux0 == MV_FLY);

    const RichEventEntry& en = sink.at(1);
    REQUIRE(en.event == EV_SEMI_ENTER);
    REQUIRE(en.species == 25);
    REQUIRE(en.aux0 == MV_FLY);

    const RichEventEntry& ex = sink.at(2);
    REQUIRE(ex.event == EV_SEMI_EXIT);
    REQUIRE(ex.turn == 4);
    REQUIRE(ex.aux0 == MV_FLY);

    const RichEventEntry& bp = sink.at(3);
    REQUIRE(bp.event == EV_BATON_PASS);
    REQUIRE(bp.side == 1);
    REQUIRE(bp.species == 6);

    const RichEventEntry& sc = sink.at(4);
    REQUIRE(sc.event == EV_STAT_COPY);
    REQUIRE(sc.side == 0);
    REQUIRE(sc.species == 9);   // copier
    REQUIRE(sc.aux0 == 3);      // source

    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// Scenario fixture: a 1v1 state whose active mon knows one charge move at slot 0.
// ---------------------------------------------------------------------------

static BattleState make_charge_state(int32_t move_id, int32_t attacker_species = 25) {
    BattleState s{};
    PokemonState mon{};
    mon.species = attacker_species;
    mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    mon.move_id0 = move_id;
    mon.move_pp0 = 15;
    PokemonState def = mon;
    def.species = 6;
    s.side0.team.push_back(mon);
    s.side1.team.push_back(def);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

static size_t count_events(const RichEventLog& log, int event) {
    size_t n = 0;
    for (size_t i = 0; i < log.size(); ++i)
        if (log.at(i).event == event) ++n;
    return n;
}

// ---------------------------------------------------------------------------
// (4a) Charge turn: Fly (semi-invuln two-turn) -> CHARGE_TURN + ENTER, no release.
// ---------------------------------------------------------------------------

TEST_CASE("Fly charge turn emits CHARGE_TURN and SEMI_INVULNERABLE_ENTER",
          "[rich_event][charge]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(MV_FLY);
    GuardLuck luck{};        // deterministic, no rng
    ExecCtx ctx{};
    // Charge turn: is_charging=false, proceeds to store the charge (returns false).
    bool proceed = cpp_pre_damage_checks(s, /*side=*/0, /*defender=*/1, MV_FLY,
                                         luck, ctx, /*effective_slot=*/0);
    REQUIRE(proceed == false);  // charging: no damage this turn

    REQUIRE(count_events(sink, EV_CHARGE_TURN) == 1);
    REQUIRE(count_events(sink, EV_SEMI_ENTER) == 1);
    REQUIRE(count_events(sink, EV_SEMI_EXIT) == 0);
    // Identity payload
    for (size_t i = 0; i < sink.size(); ++i) {
        const RichEventEntry& e = sink.at(i);
        if (e.event == EV_CHARGE_TURN || e.event == EV_SEMI_ENTER) {
            REQUIRE(e.species == 25);
            REQUIRE(e.aux0 == MV_FLY);
        }
    }
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (4b) Release turn: EXIT fires (before damage).
// ---------------------------------------------------------------------------

TEST_CASE("Fly release turn emits SEMI_INVULNERABLE_EXIT", "[rich_event][charge]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(MV_FLY);
    GuardLuck luck{};
    ExecCtx ctx{};
    // Simulate the charge turn having already stored state: mon is mid-charge.
    eff_internal::active_mon(s, 0).charging_move_slot = 0;
    eff_internal::active_mon(s, 0).timed_volatiles.push_back(TimedVolatile{27, -1});  // VE_SEMI_INVULNERABLE

    bool proceed = cpp_pre_damage_checks(s, 0, 1, MV_FLY, luck, ctx, /*effective_slot=*/0);
    REQUIRE(proceed == true);   // release: proceeds to damage

    REQUIRE(count_events(sink, EV_SEMI_EXIT) == 1);
    REQUIRE(count_events(sink, EV_CHARGE_TURN) == 0);
    REQUIRE(count_events(sink, EV_SEMI_ENTER) == 0);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (4c) Solar Beam under harsh sun: skip_charge -> NO CHARGE_TURN, NO ENTER.
// ---------------------------------------------------------------------------

TEST_CASE("Solar Beam under harsh sun skips charge (no events)",
          "[rich_event][charge]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(MV_SOLAR_BEAM);
    s.weather = WEATHER_HARSH_SUN_ID;
    GuardLuck luck{};
    ExecCtx ctx{};
    bool proceed = cpp_pre_damage_checks(s, 0, 1, MV_SOLAR_BEAM, luck, ctx, 0);
    REQUIRE(proceed == true);   // damages same turn

    REQUIRE(count_events(sink, EV_CHARGE_TURN) == 0);
    REQUIRE(count_events(sink, EV_SEMI_ENTER) == 0);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (4d) Power Herb + a charge move: skip_charge -> NO CHARGE_TURN, NO ENTER.
// ---------------------------------------------------------------------------

TEST_CASE("Power Herb skips charge (no events)", "[rich_event][charge]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(MV_FLY);
    eff_internal::active_mon(s, 0).item = ITM_POWER_HERB;
    GuardLuck luck{};
    ExecCtx ctx{};
    bool proceed = cpp_pre_damage_checks(s, 0, 1, MV_FLY, luck, ctx, 0);
    REQUIRE(proceed == true);

    REQUIRE(count_events(sink, EV_CHARGE_TURN) == 0);
    REQUIRE(count_events(sink, EV_SEMI_ENTER) == 0);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (4e) Non-semi-invuln two-turn (Skull Bash): CHARGE_TURN but NOT ENTER.
// ---------------------------------------------------------------------------

TEST_CASE("Skull Bash charge emits CHARGE_TURN but not ENTER",
          "[rich_event][charge]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(MV_SKULL_BASH);
    GuardLuck luck{};
    ExecCtx ctx{};
    bool proceed = cpp_pre_damage_checks(s, 0, 1, MV_SKULL_BASH, luck, ctx, 0);
    REQUIRE(proceed == false);

    REQUIRE(count_events(sink, EV_CHARGE_TURN) == 1);
    REQUIRE(count_events(sink, EV_SEMI_ENTER) == 0);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (4f) Psych Up vs a boosted target: STAT_COPY fires once with copier + source.
// ---------------------------------------------------------------------------

TEST_CASE("Psych Up emits STAT_COPY once with copier and source species",
          "[rich_event][stat_copy]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    // side0 uses Psych Up on side1's boosted mon.
    BattleState s = make_charge_state(MV_PSYCH_UP, /*attacker_species=*/9);
    s.side1.team[0].species = 3;
    s.side1.team[0].stage0 = 2;   // target has +2 Atk to copy

    EffectsLuck luck{};
    ExecCtx ctx{};
    cpp_apply_status_move(s, /*side_idx=*/0, MV_PSYCH_UP, luck, ctx, /*attacker_slot=*/0);

    REQUIRE(count_events(sink, EV_STAT_COPY) == 1);
    const RichEventEntry* sc = nullptr;
    for (size_t i = 0; i < sink.size(); ++i)
        if (sink.at(i).event == EV_STAT_COPY) sc = &sink.at(i);
    REQUIRE(sc != nullptr);
    REQUIRE(sc->side == 0);
    REQUIRE(sc->species == 9);  // copier
    REQUIRE(sc->aux0 == 3);     // source (copied-from)
    // Sanity: the copy actually happened.
    REQUIRE(s.side0.team[0].stage0 == 2);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (5) Solver isolation: cpp_run_one_turn_solver with NO rich log registered
//     records nothing and behaves unchanged.
// ---------------------------------------------------------------------------

static BattleState make_switch_ready_state() {
    BattleState s{};
    PokemonState mon{};
    mon.species = 1; mon.level = 50;
    mon.has_stats = true;
    mon.stat_hp = 100; mon.stat_atk = 60; mon.stat_def = 60;
    mon.stat_spa = 60; mon.stat_spd = 60; mon.stat_spe = 60;
    mon.has_max_hp = true; mon.max_hp = 100;
    mon.has_hp = true;     mon.hp = 100;
    s.side0.team.push_back(mon);
    s.side0.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side1.team.push_back(mon);
    s.side0.active_indices.push_back(0);
    s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

TEST_CASE("Solver turn records nothing when no rich log registered",
          "[rich_event][solver_isolation]") {
    set_rich_event_log(nullptr);

    BattleState state = make_switch_ready_state();
    std::vector<ExecAction> ap0, ap1;
    ExecAction e0; e0.kind = 1; e0.switch_to_slot = 1; e0.source_slot = 0; ap0.push_back(e0);
    ExecAction e1; e1.kind = 1; e1.switch_to_slot = 1; e1.source_slot = 0; ap1.push_back(e1);

    DamageLoopLuck lp0{}, lp1{};
    TurnLuck tl0{}, tl1{};
    OracleOverrides ov;

    SolverTurnResult r = cpp_run_one_turn_solver(state, ap0, ap1, lp0, lp1, tl0, tl1,
                                                 false, false, ov);
    REQUIRE(r.ok);
    REQUIRE(get_rich_event_log() == nullptr);
}

// ===========================================================================
// E1b: consumed-event emit helpers + real-mechanic chokepoint tests.
// ===========================================================================

// LogEvent integer constants for the E1b consumed events (liveplay/logger.py).
static constexpr int EV_CANT_SLEEP = 5, EV_CANT_FROZEN = 8, EV_CANT_PARALYSIS = 10,
                     EV_CANT_FLINCH = 11, EV_HIT_SELF_CONFUSION = 13, EV_CANT_INFAT = 14,
                     EV_MOVE_USE = 27, EV_MOVE_MISS = 33, EV_DAMAGE = 45, EV_CRIT = 46,
                     EV_HITCOUNT = 48, EV_HEAL = 51, EV_STAT_BOOST = 53,
                     EV_STATUS_APPLY = 61, EV_VOLATILE_APPLY = 64, EV_FAINT = 123,
                     EV_EXP_GAIN = 132, EV_LEVEL_UP = 133;

// ---------------------------------------------------------------------------
// (E1b-1) Each consumed-event emit helper records one entry with correct fields.
// ---------------------------------------------------------------------------

// E1b tests reach into internal chokepoints (change_stat_stage / apply_status_to
// live in eff_internal; STATUS_PARALYSIS in eff). Pull them into scope here.
using eff::STATUS_PARALYSIS;
using eff_internal::change_stat_stage;
using eff_internal::apply_status_to;

TEST_CASE("E1b emit helpers record correct entries", "[rich_event][e1b][emit]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    rich_log_move_use(1, /*species=*/25, /*move=*/33, /*side=*/0);
    rich_log_presence(1, EV_CRIT, /*species=*/6);
    rich_log_presence(1, EV_CANT_PARALYSIS, /*species=*/6);
    rich_log_presence(1, EV_MOVE_MISS, /*species=*/25);
    rich_log_cant_sleep(1, /*species=*/6, /*turns=*/2);
    rich_log_hit_self_confusion(1, /*species=*/25, /*damage=*/12, /*side=*/0);
    rich_log_status_apply(1, /*species=*/6, /*status=*/STATUS_PARALYSIS, /*side=*/1, SourceTag::MOVE);
    rich_log_stat_boost(1, /*species=*/25, /*stat=*/0, /*stages=*/2, /*side=*/0, SourceTag::MOVE);
    rich_log_volatile_apply(1, /*species=*/6, VolatileTag::CONFUSED, /*side=*/1, SourceTag::MOVE);
    rich_log_hitcount(1, /*species=*/25, /*side=*/0);
    rich_log_damage(1, /*species=*/6, /*amount=*/40, /*hp_after=*/60,
                    /*attacker_side=*/0, /*attacker_slot=*/0, /*defender_side=*/1, SourceTag::MOVE);
    rich_log_heal(1, /*species=*/25, /*amount=*/33, /*hp_after=*/100, /*side=*/0, SourceTag::BERRY);
    rich_log_faint(1, /*species=*/6, /*side=*/1);
    rich_log_exp_gain(1, /*species=*/25, /*amount=*/240);
    rich_log_level_up(1, /*species=*/25, /*new_level=*/51);

    REQUIRE(sink.size() == 15);

    REQUIRE(sink.at(0).event == EV_MOVE_USE);
    REQUIRE(sink.at(0).species == 25);
    REQUIRE(sink.at(0).move == 33);
    REQUIRE(sink.at(0).side == 0);

    REQUIRE(sink.at(4).event == EV_CANT_SLEEP);
    REQUIRE(sink.at(4).aux0 == 2);   // turns

    REQUIRE(sink.at(6).event == EV_STATUS_APPLY);
    REQUIRE(sink.at(6).status == STATUS_PARALYSIS);
    REQUIRE(sink.at(6).side == 1);
    REQUIRE(sink.at(6).source_tag == static_cast<int32_t>(SourceTag::MOVE));

    REQUIRE(sink.at(7).event == EV_STAT_BOOST);
    REQUIRE(sink.at(7).stat == 0);
    REQUIRE(sink.at(7).stages == 2);

    REQUIRE(sink.at(8).event == EV_VOLATILE_APPLY);
    REQUIRE(sink.at(8).volatile_tag == static_cast<int32_t>(VolatileTag::CONFUSED));

    REQUIRE(sink.at(10).event == EV_DAMAGE);
    REQUIRE(sink.at(10).amount == 40);
    REQUIRE(sink.at(10).hp_after == 60);
    REQUIRE(sink.at(10).attacker_side == 0);
    REQUIRE(sink.at(10).defender_side == 1);
    REQUIRE(sink.at(10).source_tag == static_cast<int32_t>(SourceTag::MOVE));

    REQUIRE(sink.at(11).event == EV_HEAL);
    REQUIRE(sink.at(11).source_tag == static_cast<int32_t>(SourceTag::BERRY));

    REQUIRE(sink.at(13).event == EV_EXP_GAIN);
    REQUIRE(sink.at(13).amount == 240);
    REQUIRE(sink.at(14).event == EV_LEVEL_UP);
    REQUIRE(sink.at(14).new_level == 51);

    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (E1b-2) Fail-loud invariant guards.
// ---------------------------------------------------------------------------

TEST_CASE("E1b emit helpers fail loud on bad invariants", "[rich_event][e1b][faill]") {
    RichEventLog sink;
    set_rich_event_log(&sink);
    REQUIRE_THROWS_AS(rich_log_status_apply(1, /*species=*/5, STATUS_PARALYSIS,
                                            /*side=*/-1, SourceTag::MOVE), std::runtime_error);
    REQUIRE_THROWS_AS(rich_log_faint(1, /*species=*/-1, /*side=*/0), std::runtime_error);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (E1b-3) change_stat_stage chokepoint: STAT_BOOST once on a real change, none
//         when the change clamps to zero (already at +6).
// ---------------------------------------------------------------------------

TEST_CASE("change_stat_stage emits STAT_BOOST only on a real change",
          "[rich_event][e1b][stat_boost]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(/*move_id=*/33, /*attacker_species=*/25);
    // Raise Atk +2 from stage 0 -> one STAT_BOOST(stages=+2). Positive delta avoids
    // Defiant/Competitive/White Herb side paths.
    change_stat_stage(s, /*side_idx=*/0, /*stat_idx=*/0, /*delta=*/2,
                      false, false, false, nullptr);
    REQUIRE(count_events(sink, EV_STAT_BOOST) == 1);

    sink.clear();
    // Already at +6: a further +1 clamps to 0 actual -> no emit.
    eff_internal::active_mon(s, 0).stage0 = 6;
    change_stat_stage(s, 0, 0, +1, false, false, false, nullptr);
    REQUIRE(count_events(sink, EV_STAT_BOOST) == 0);

    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (E1b-4) apply_status_to chokepoint emits STATUS_APPLY.
// ---------------------------------------------------------------------------

TEST_CASE("apply_status_to emits STATUS_APPLY", "[rich_event][e1b][status]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(/*move_id=*/33, /*attacker_species=*/25);
    apply_status_to(s, /*side_idx=*/1, STATUS_PARALYSIS);
    REQUIRE(count_events(sink, EV_STATUS_APPLY) == 1);
    const RichEventEntry* e = nullptr;
    for (size_t i = 0; i < sink.size(); ++i)
        if (sink.at(i).event == EV_STATUS_APPLY) e = &sink.at(i);
    REQUIRE(e != nullptr);
    REQUIRE(e->status == STATUS_PARALYSIS);
    REQUIRE(e->side == 1);
    set_rich_event_log(nullptr);
}

// ---------------------------------------------------------------------------
// (E1b-5) FAINT is single-fire: cpp_faint_active's idempotent guard prevents a
//         second emit on the same already-fainted mon.
// ---------------------------------------------------------------------------

TEST_CASE("cpp_faint_active emits FAINT exactly once (idempotent guard)",
          "[rich_event][e1b][faint]") {
    RichEventLog sink;
    set_rich_event_log(&sink);

    BattleState s = make_charge_state(/*move_id=*/33, /*attacker_species=*/25);
    cpp_faint_active(s, /*side_idx=*/1, /*notify_soul_heart=*/false, /*slot=*/0);
    REQUIRE(count_events(sink, EV_FAINT) == 1);
    // Second call on the already-fainted mon: guard returns early, no second emit.
    cpp_faint_active(s, 1, false, 0);
    REQUIRE(count_events(sink, EV_FAINT) == 1);
    set_rich_event_log(nullptr);
}
