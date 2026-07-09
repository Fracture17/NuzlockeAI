// Catch2 tests for the D3 analytical RNG logger + consumable OracleOverrides queue
// + occurrence-keyed Category-B injection channel.
// Verifies: (1) logger records event/participants/chosen/options for Cat-A and Cat-B
// draws; (2) OracleOverrides.answers consume-once with loud failure on exhaustion;
// (3) CategoryBInjection forces a specific occurrence and fails loud on unconsumed.
#include <catch2/catch_test_macros.hpp>

#include <stdexcept>
#include <type_traits>

#include "logger.h"
#include "oracle.h"
#include "rng_resolver.h"
#include "native_rng.h"
#include "effects.h"
#include "effects_internal.h"
#include "core_leaf.h"

// ---------------- POD/trivial-copyable guarantee ----------------

TEST_CASE("AnalyticalRngEntry is trivially copyable", "[logger][layout]") {
    static_assert(std::is_trivially_copyable_v<AnalyticalRngEntry>,
                  "AnalyticalRngEntry must be trivially copyable (POD)");
    static_assert(std::is_trivially_copyable_v<RngParticipants>,
                  "RngParticipants must be trivially copyable (POD)");
    SUCCEED();
}

// ---------------- Toggle: nullptr = off, no work ----------------

TEST_CASE("Logger off (nullptr) records nothing", "[logger][toggle]") {
    set_analytical_rng_log(nullptr);
    // A draw with no sink should be a no-op.
    analytical_rng_log_draw(1, 5, RngParticipants{0, 0, 1, 0}, 1, {0, 1});
    REQUIRE(get_analytical_rng_log() == nullptr);
}

TEST_CASE("Logger captures Cat-B accuracy draw with participants", "[logger][catb]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    RngParticipants who{0, 0, 1, 0};
    analytical_rng_log_draw(3, static_cast<int>(RngEventC::ACCURACY),
                            who, /*chosen=*/1, {0, 1});

    REQUIRE(sink.size() == 1);
    const AnalyticalRngEntry& e = sink.at(0);
    REQUIRE(e.turn == 3);
    REQUIRE(e.event == static_cast<int>(RngEventC::ACCURACY));
    REQUIRE(e.who.attacker_side == 0);
    REQUIRE(e.who.attacker_slot == 0);
    REQUIRE(e.who.defender_side == 1);
    REQUIRE(e.who.defender_slot == 0);
    REQUIRE(e.chosen == 1);
    REQUIRE(e.options.size() == 2);
    REQUIRE(e.options[0] == 0);
    REQUIRE(e.options[1] == 1);
    REQUIRE(e.options_truncated == 0);

    set_analytical_rng_log(nullptr);
}

TEST_CASE("Logger truncates over-16 options but records count", "[logger][options]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    std::vector<int32_t> big_opts;
    for (int i = 0; i < 32; ++i) big_opts.push_back(i);
    analytical_rng_log_draw(1, static_cast<int>(RngEventC::METRONOME_MOVE),
                            RngParticipants{0, 0, -1, -1}, /*chosen=*/17,
                            big_opts.data(), big_opts.size());

    REQUIRE(sink.size() == 1);
    const AnalyticalRngEntry& e = sink.at(0);
    REQUIRE(e.options_count == 32);
    REQUIRE(e.options_truncated == 1);
    REQUIRE(e.options.size() == 0);  // truncated: inline vec left empty
    REQUIRE(e.chosen == 17);

    set_analytical_rng_log(nullptr);
}

// ---------------- rng_resolve_* logs draws when sink is on ----------------

TEST_CASE("rng_resolve_accuracy logs an entry through resolver plumbing",
          "[logger][resolver]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    // Deterministic mode: eff_acc >= threshold (100 >= 50) -> hit. Should still log.
    NativeRng rng(12345);
    rng.current_turn = 4;
    RngLogCtx ctx{ RngParticipants{0, 0, 1, 0}, /*turn=*/4 };
    bool hit = rng_resolve_accuracy(100.0, /*is_none=*/false, /*threshold=*/50.0,
                                    /*random_mode=*/false, &rng, &ctx);
    (void)hit;

    // Saturation (100 >= threshold) short-circuits BEFORE any RNG, but resolver
    // still records an entry so the solver sees the decision.
    REQUIRE(sink.size() == 1);
    REQUIRE(sink.at(0).event == static_cast<int>(RngEventC::ACCURACY));
    REQUIRE(sink.at(0).chosen == 1);
    REQUIRE(sink.at(0).who.attacker_side == 0);

    set_analytical_rng_log(nullptr);
}

// ---------------- Consumable OracleOverrides queue ----------------

TEST_CASE("OracleOverrides.answers consume once then throw NeedsRNG",
          "[oracle][consume]") {
    OracleOverrides ov;
    OracleAnswer a; a.i0 = 42;
    ov.answers[static_cast<int>(RngEventC::EFFECT_SPORE_WHICH)].push_back(a);

    int first = oracle_resolve(&ov, RngEventC::EFFECT_SPORE_WHICH, {1, 2, 3});
    REQUIRE(first == 42);

    REQUIRE_THROWS_AS(
        oracle_resolve(&ov, RngEventC::EFFECT_SPORE_WHICH, {1, 2, 3}),
        NeedsRNG
    );
}

TEST_CASE("OracleOverrides.answers queue consumes N answers in order",
          "[oracle][consume]") {
    OracleOverrides ov;
    OracleAnswer a1; a1.i0 = 10;
    OracleAnswer a2; a2.i0 = 20;
    ov.answers[static_cast<int>(RngEventC::TRI_ATTACK_STATUS)].push_back(a1);
    ov.answers[static_cast<int>(RngEventC::TRI_ATTACK_STATUS)].push_back(a2);

    REQUIRE(oracle_resolve(&ov, RngEventC::TRI_ATTACK_STATUS, {1,2,3}) == 10);
    REQUIRE(oracle_resolve(&ov, RngEventC::TRI_ATTACK_STATUS, {1,2,3}) == 20);
    REQUIRE_THROWS_AS(
        oracle_resolve(&ov, RngEventC::TRI_ATTACK_STATUS, {1,2,3}),
        NeedsRNG
    );
}

TEST_CASE("OracleOverrides pair queue consume-once (MOODY_STATS)",
          "[oracle][consume][pair]") {
    OracleOverrides ov;
    OracleAnswer a; a.i0 = 3; a.i1 = 5;
    ov.answers[static_cast<int>(RngEventC::MOODY_STATS)].push_back(a);

    OracleAnswer got = oracle_resolve_pair(&ov, RngEventC::MOODY_STATS, {0,1,2,3,4,5,6});
    REQUIRE(got.i0 == 3);
    REQUIRE(got.i1 == 5);

    REQUIRE_THROWS_AS(
        oracle_resolve_pair(&ov, RngEventC::MOODY_STATS, {0,1,2,3,4,5,6}),
        NeedsRNG
    );
}

// ---------------- Occurrence-keyed Category-B injection ----------------

TEST_CASE("CategoryBInjection forces a specific occurrence", "[catb_inject]") {
    CategoryBInjection inj;
    // Force the 2nd accuracy check to miss (event=ACCURACY, occurrence=1).
    inj.push_bool(static_cast<int>(RngEventC::ACCURACY), 1, false);

    // 1st occurrence: no injection -> resolver falls through.
    REQUIRE(inj.find(static_cast<int>(RngEventC::ACCURACY), 0) == nullptr);

    // 2nd occurrence: injected. find returns the outcome; we mark it consumed manually
    // (resolvers will do this).
    auto* o = inj.find(static_cast<int>(RngEventC::ACCURACY), 1);
    REQUIRE(o != nullptr);
    REQUIRE(o->kind == 2);
    REQUIRE(o->b == false);
    o->consumed = true;

    // After consuming, find returns nullptr for the same key.
    REQUIRE(inj.find(static_cast<int>(RngEventC::ACCURACY), 1) == nullptr);
}

TEST_CASE("CategoryBInjection verify_exhausted throws on leftover", "[catb_inject][fail_loud]") {
    CategoryBInjection inj;
    inj.push_bool(static_cast<int>(RngEventC::CRIT), 0, true);
    // Never consumed.
    REQUIRE_THROWS_AS(inj.verify_exhausted(), std::runtime_error);
}

TEST_CASE("CategoryBInjection verify_exhausted OK when all consumed", "[catb_inject]") {
    CategoryBInjection inj;
    inj.push_bool(static_cast<int>(RngEventC::CRIT), 0, true);
    auto* o = inj.find(static_cast<int>(RngEventC::CRIT), 0);
    REQUIRE(o != nullptr);
    o->consumed = true;
    REQUIRE_NOTHROW(inj.verify_exhausted());
}

// ---------------- End-to-end: resolver consumes injection at the right occurrence ----------------

TEST_CASE("rng_resolve_accuracy honors occurrence-keyed injection",
          "[catb_inject][resolver]") {
    CategoryBInjection inj;
    CategoryBOccurrenceCounters occ;
    set_catb_injection(&inj);
    set_catb_occ_counters(&occ);

    // Register: the 1st accuracy check MISSES even though threshold says hit.
    inj.push_bool(static_cast<int>(RngEventC::ACCURACY), 0, /*value=*/false);

    NativeRng rng(1);
    rng.current_turn = 1;
    RngLogCtx ctx{ RngParticipants{0, 0, 1, 0}, /*turn=*/1 };

    // Deterministic path with eff_acc(75) > threshold(50) would normally hit, but the
    // injection overrides the outcome. This is the key solver ability. eff_acc must be
    // strictly < 100 so the saturation shortcut doesn't fire before injection lookup.
    bool hit1 = rng_resolve_accuracy(75.0, false, 50.0, false, &rng, &ctx);
    REQUIRE(hit1 == false);  // forced miss

    // Next accuracy check (occurrence 1) has no injection, so it uses normal path (hit).
    bool hit2 = rng_resolve_accuracy(75.0, false, 50.0, false, &rng, &ctx);
    REQUIRE(hit2 == true);

    // Injection must be fully consumed by turn end.
    REQUIRE_NOTHROW(inj.verify_exhausted());

    set_catb_injection(nullptr);
    set_catb_occ_counters(nullptr);
}

// ---------------- Fix 1: det-wrappers thread participants through ----------------

TEST_CASE("resolve_secondary_det logs entry with participants from ctx",
          "[logger][det_wrapper]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    EffectsLuck luck;
    luck.secondary_threshold = 50.0;
    luck.random_mode = false;
    // Deterministic: chance=60 > threshold=50 -> true; ctx carries participants.
    RngLogCtx ctx{ RngParticipants{0, 0, 1, 0}, /*turn=*/7 };
    bool res = eff_internal::resolve_secondary_det(60, luck, &ctx);
    REQUIRE(res == true);

    REQUIRE(sink.size() == 1);
    const AnalyticalRngEntry& e = sink.at(0);
    REQUIRE(e.event == static_cast<int>(RngEventC::SECONDARY_FIRES));
    REQUIRE(e.who.attacker_side == 0);
    REQUIRE(e.who.attacker_slot == 0);
    REQUIRE(e.who.defender_side == 1);
    REQUIRE(e.who.defender_slot == 0);
    REQUIRE(e.turn == 7);

    set_analytical_rng_log(nullptr);
}

TEST_CASE("resolve_flinch_det logs entry with participants from ctx",
          "[logger][det_wrapper]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    EffectsLuck luck;
    luck.flinch_threshold = 50.0;
    luck.random_mode = false;
    RngLogCtx ctx{ RngParticipants{1, 0, 0, 0}, /*turn=*/3 };
    (void)eff_internal::resolve_flinch_det(10, luck, &ctx);

    REQUIRE(sink.size() == 1);
    const AnalyticalRngEntry& e = sink.at(0);
    REQUIRE(e.event == static_cast<int>(RngEventC::FLINCH));
    REQUIRE(e.who.attacker_side == 1);
    REQUIRE(e.who.defender_side == 0);

    set_analytical_rng_log(nullptr);
}

TEST_CASE("resolve_proc_det logs entry with participants from ctx",
          "[logger][det_wrapper]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    EffectsLuck luck;
    luck.proc_threshold = 50.0;
    luck.random_mode = false;
    RngLogCtx ctx{ RngParticipants{0, 0, -1, -1}, /*turn=*/2 };
    (void)eff_internal::resolve_proc_det(30, luck, &ctx);

    REQUIRE(sink.size() == 1);
    const AnalyticalRngEntry& e = sink.at(0);
    REQUIRE(e.event == static_cast<int>(RngEventC::PROC_FIRES));
    REQUIRE(e.who.attacker_side == 0);
    REQUIRE(e.who.defender_side == -1);

    set_analytical_rng_log(nullptr);
}

// ---------------- Fix 2: SPEED_TIE logs an analytical entry ----------------

// Build a minimal Entry for the tiebreaker path. Only the fields needed by
// cpp_select_next_action's speed-tie detection are set.
static Entry _make_entry(int side_idx, int source_slot, double tie) {
    Entry e{};
    e.side_idx = side_idx;
    e.source_slot = source_slot;
    e.action = ActionC{};
    e.action.kind = 0;  // ACTION_MOVE
    e.action.source_slot = source_slot;
    e.luck = TurnLuck{};
    e.luck.random_mode = true;  // native-tiebreaker path (no throw)
    e.tie = tie;
    e.priority_item_fires = false;
    e.quick_draw_fires = false;
    return e;
}

TEST_CASE("cpp_select_next_action logs SPEED_TIE with tied movers",
          "[logger][speed_tie]") {
    AnalyticalRngLog sink;
    set_analytical_rng_log(&sink);

    // Minimal battle state: two mons with identical speed on opposite sides. Only the
    // fields consulted by action_sort_key/effective_speed matter — species=0 with
    // has_stats=true short-circuits base-stat lookup.
    BattleState state{};
    PokemonState mon{};
    mon.has_stats = true;
    mon.stat_spe = 100;
    mon.has_max_hp = true;
    mon.max_hp = 100;
    mon.has_hp = true;
    mon.hp = 100;
    // Both sides get one active mon at team[0].
    state.side0.team.push_back(mon);
    state.side1.team.push_back(mon);
    state.side0.active_indices.push_back(0);
    state.side1.active_indices.push_back(0);

    // Two tied entries (same priority/speed/etc) with different tie values so the
    // native path picks a winner. p1 has the larger tie -> wins.
    std::vector<Entry> pending;
    pending.push_back(_make_entry(/*side=*/0, /*slot=*/0, /*tie=*/0.25));
    pending.push_back(_make_entry(/*side=*/1, /*slot=*/0, /*tie=*/0.75));

    Entry picked = cpp_select_next_action(state, pending, /*overrides=*/nullptr);

    // Expect exactly one SPEED_TIE entry recording the tied set and the winner.
    size_t st_count = 0;
    for (size_t i = 0; i < sink.size(); ++i)
        if (sink.at(i).event == static_cast<int>(RngEventC::SPEED_TIE))
            ++st_count;
    REQUIRE(st_count == 1);
    // Find it
    const AnalyticalRngEntry* st = nullptr;
    for (size_t i = 0; i < sink.size(); ++i)
        if (sink.at(i).event == static_cast<int>(RngEventC::SPEED_TIE))
            st = &sink.at(i);
    REQUIRE(st != nullptr);

    // chosen = side*10+slot of winning entry (side 1, slot 0 -> 10).
    REQUIRE(st->chosen == picked.side_idx * 10 + picked.source_slot);
    REQUIRE(picked.side_idx == 1);
    // Options list both tied entry codes (sorted).
    REQUIRE(st->options.size() == 2);
    REQUIRE(st->options[0] == 0);   // side 0, slot 0
    REQUIRE(st->options[1] == 10);  // side 1, slot 0
    // Participants: both tied movers are present (attacker/defender attribution).
    REQUIRE(st->who.attacker_side != -1);
    REQUIRE(st->who.defender_side != -1);

    set_analytical_rng_log(nullptr);
}

// ---------------- Fix 3: reset helper is a no-op when no counters registered ----------------

TEST_CASE("reset_catb_occurrence_counters_if_registered no-ops when unset",
          "[catb_inject][reset]") {
    // No counters registered -> the helper must not crash and must remain a no-op.
    set_catb_occ_counters(nullptr);
    REQUIRE_NOTHROW(reset_catb_occurrence_counters_if_registered());
}

TEST_CASE("reset_catb_occurrence_counters_if_registered zeros the counters",
          "[catb_inject][reset]") {
    CategoryBOccurrenceCounters occ;
    set_catb_occ_counters(&occ);
    // Bump ACCURACY twice; then reset.
    (void)occ.next(static_cast<int>(RngEventC::ACCURACY));
    (void)occ.next(static_cast<int>(RngEventC::ACCURACY));
    // Verify the counter advanced.
    REQUIRE(occ.counts[static_cast<int>(RngEventC::ACCURACY)] == 2);

    reset_catb_occurrence_counters_if_registered();
    REQUIRE(occ.counts[static_cast<int>(RngEventC::ACCURACY)] == 0);

    set_catb_occ_counters(nullptr);
}
