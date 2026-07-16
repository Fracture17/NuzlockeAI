// Bucket solver Task 10: run_pipeline lattice (amendment 18). Injected stage seams
// exercise every lattice edge without real search: pessimal LOSS short-circuits B;
// pessimal WIN/INDET both route to B and are never evidence; B WIN → WIN, B FAIL/INDET
// → UNKNOWN; stage exceptions propagate. One real terminal-state case proves the
// production path decides at the root without spawning a search.
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/pipeline.h"
#include "solver/bucket/expand.h"   // ExpandError
#include "solver/question.h"
#include "state.h"

#include <array>
#include <stdexcept>

namespace {

BsolverResult pess(BVerdict v, BIndeterminateReason r = BIndeterminateReason::None) {
    BsolverResult res;
    res.verdict = v;
    res.reason  = r;
    return res;
}

BucketWinResult bwin(BucketWinVerdict v,
                     BucketWinIndetReason r = BucketWinIndetReason::None,
                     std::array<uint64_t, 32> hist = {}) {
    BucketWinResult res;
    res.verdict = v;
    res.reason  = r;
    res.concession_histogram = hist;
    return res;
}

// Seam config: pessimal returns pv; B returns whatever bfn yields (may throw).
PipelineConfig with_seams(BsolverResult pv, BWinFn bfn) {
    PipelineConfig cfg;
    cfg.pessimal_override = [pv](const BattleState&, const Question&,
                                 const BsolverConfig&) { return pv; };
    cfg.bwin_override = std::move(bfn);
    return cfg;
}

// A minimal, non-terminal state (both mons alive) so the production path would search.
BattleState alive_state() {
    BattleState s{};
    PokemonState p{};
    p.species = 1; p.level = 50; p.has_stats = true;
    p.stat_hp = 100; p.has_max_hp = true; p.max_hp = 100; p.has_hp = true; p.hp = 100;
    p.move_id0 = 33; p.move_pp0 = 35;
    PokemonState o = p; o.species = 2;
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

}  // namespace

TEST_CASE("pipeline: pessimal LOSS short-circuits, B never runs", "[bucket][pipeline]") {
    bool b_called = false;
    auto cfg = with_seams(pess(BVerdict::LOSS),
                          [&](const BattleState&, const Question&, const BucketWinConfig&) {
                              b_called = true; return bwin(BucketWinVerdict::WIN);
                          });
    PipelineResult r = run_pipeline(alive_state(), Question{}, cfg);
    REQUIRE(r.verdict == PipelineVerdict::LOSS);
    REQUIRE(r.b_ran == false);
    REQUIRE(b_called == false);
    REQUIRE(r.pessimal_verdict == BVerdict::LOSS);
}

TEST_CASE("pipeline: pessimal WIN + B WIN → WIN (B still runs)", "[bucket][pipeline]") {
    bool b_called = false;
    auto cfg = with_seams(pess(BVerdict::WIN),
                          [&](const BattleState&, const Question&, const BucketWinConfig&) {
                              b_called = true; return bwin(BucketWinVerdict::WIN);
                          });
    PipelineResult r = run_pipeline(alive_state(), Question{}, cfg);
    REQUIRE(r.verdict == PipelineVerdict::WIN);
    REQUIRE(r.b_ran == true);
    REQUIRE(b_called == true);
    REQUIRE(r.b_verdict == BucketWinVerdict::WIN);
}

TEST_CASE("pipeline: pessimal INDET + B WIN → WIN", "[bucket][pipeline]") {
    auto cfg = with_seams(pess(BVerdict::INDETERMINATE, BIndeterminateReason::NodeCap),
                          [](const BattleState&, const Question&, const BucketWinConfig&) {
                              return bwin(BucketWinVerdict::WIN);
                          });
    PipelineResult r = run_pipeline(alive_state(), Question{}, cfg);
    REQUIRE(r.verdict == PipelineVerdict::WIN);
    REQUIRE(r.b_ran == true);
    REQUIRE(r.pessimal_verdict == BVerdict::INDETERMINATE);
}

TEST_CASE("pipeline: pessimal INDET + B FAIL → UNKNOWN, histogram preserved",
          "[bucket][pipeline]") {
    std::array<uint64_t, 32> hist{};
    hist[3] = 7; hist[10] = 2;  // arbitrary concession counts
    auto cfg = with_seams(pess(BVerdict::INDETERMINATE),
                          [hist](const BattleState&, const Question&, const BucketWinConfig&) {
                              return bwin(BucketWinVerdict::FAIL,
                                          BucketWinIndetReason::None, hist);
                          });
    PipelineResult r = run_pipeline(alive_state(), Question{}, cfg);
    REQUIRE(r.verdict == PipelineVerdict::UNKNOWN);
    REQUIRE(r.b_ran == true);
    REQUIRE(r.concession_histogram == hist);
}

TEST_CASE("pipeline: pessimal INDET + B INDET(DepthCap) → UNKNOWN, reason preserved",
          "[bucket][pipeline]") {
    auto cfg = with_seams(pess(BVerdict::WIN),
                          [](const BattleState&, const Question&, const BucketWinConfig&) {
                              return bwin(BucketWinVerdict::INDETERMINATE,
                                          BucketWinIndetReason::DepthCap);
                          });
    PipelineResult r = run_pipeline(alive_state(), Question{}, cfg);
    REQUIRE(r.verdict == PipelineVerdict::UNKNOWN);
    REQUIRE(r.b_verdict == BucketWinVerdict::INDETERMINATE);
    REQUIRE(r.b_reason == BucketWinIndetReason::DepthCap);
}

TEST_CASE("pipeline: B seam throwing ExpandError propagates with stage intact",
          "[bucket][pipeline]") {
    auto cfg = with_seams(pess(BVerdict::WIN),
                          [](const BattleState&, const Question&, const BucketWinConfig&)
                              -> BucketWinResult {
                              throw ExpandError(ExpandError::Stage::ShiftViolation,
                                                "test shift violation");
                          });
    try {
        run_pipeline(alive_state(), Question{}, cfg);
        FAIL("expected ExpandError to propagate");
    } catch (const ExpandError& e) {
        REQUIRE(e.stage == ExpandError::Stage::ShiftViolation);
    }
}

TEST_CASE("pipeline: real terminal state (opp fainted) → WIN without search",
          "[bucket][pipeline]") {
    BattleState s = alive_state();
    // Faint the AI active mon: production classify() → WIN at the root.
    s.side1.team[0].hp = 0;
    s.side1.team[0].has_hp = true;
    s.side1.team[0].fainted = true;

    PipelineResult r = run_pipeline(s, Question{}, PipelineConfig{});  // no seams
    REQUIRE(r.verdict == PipelineVerdict::WIN);
    REQUIRE(r.b_ran == true);
    // Root terminal shortcut in bucket_win_certify: no DFS buckets visited.
    REQUIRE(r.b_stats.buckets_visited == 0);
}
