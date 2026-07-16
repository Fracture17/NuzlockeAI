// Bucket solver Task 10: rcheck referee classifier + census-key + shard run loop.
// Unit tests exercise all nine classifier cells (incl. both hard-fail classes, tagged vs
// untagged UNKNOWN-on-WIN, UNKNOWN-on-LOSS, THROWN precedence, exact-INDET → REFEREE_INDET)
// and every census-key branch. An injected-pairs run (seams, no generator) proves the loop
// counts, hard_fails, JSONL shape, and summary consistency BEFORE any corpus run. A small
// real-solver smoke run over one shard proves the end-to-end path.
#include <catch2/catch_test_macros.hpp>

#include "solver/audit/rcheck_core.h"
#include "solver/bucket/expand.h"     // ExpandError
#include "solver/matchup_gen.h"
#include "state.h"

#include "nlohmann/json.hpp"

#include <array>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using nlohmann::json;

namespace {

PipelineOutcome outcome(PipelineVerdict v, uint32_t mask = 0) {
    PipelineOutcome po;
    po.verdict = v;
    po.concession_mask = mask;
    return po;
}

PipelineOutcome thrown_outcome(const std::string& key) {
    PipelineOutcome po;
    po.thrown = true;
    po.throw_key = key;
    return po;
}

BattleState alive_state(int32_t opp_species = 2) {
    BattleState s{};
    PokemonState p{};
    p.species = 1; p.level = 50; p.has_stats = true;
    p.stat_hp = 100; p.has_max_hp = true; p.max_hp = 100; p.has_hp = true; p.hp = 100;
    p.move_id0 = 33; p.move_pp0 = 35;
    PokemonState o = p; o.species = opp_species;
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

}  // namespace

// ---------------------------------------------------------------------------
// classify_rcheck: all nine cells
// ---------------------------------------------------------------------------

TEST_CASE("rcheck classifier: nine cells + THROWN precedence", "[bucket][rcheck]") {
    // THROWN takes precedence over any exact verdict.
    REQUIRE(classify_rcheck(thrown_outcome("expand:ShiftViolation"), BVerdict::WIN)
            == RcheckClass::THROWN);
    REQUIRE(classify_rcheck(thrown_outcome("residual_unknown"), BVerdict::LOSS)
            == RcheckClass::THROWN);

    // Non-thrown × exact INDET → REFEREE_INDET (regardless of pipeline verdict).
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::WIN), BVerdict::INDETERMINATE)
            == RcheckClass::REFEREE_INDET);
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::UNKNOWN), BVerdict::INDETERMINATE)
            == RcheckClass::REFEREE_INDET);

    // Sound agreements.
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::WIN), BVerdict::WIN)
            == RcheckClass::SOUND_AGREE_WIN);
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::LOSS), BVerdict::LOSS)
            == RcheckClass::SOUND_AGREE_LOSS);

    // Hard fails (both directions).
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::WIN), BVerdict::LOSS)
            == RcheckClass::HARD_FAIL_B_WIN);
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::LOSS), BVerdict::WIN)
            == RcheckClass::HARD_FAIL_PESSIMAL_LOSS);

    // UNKNOWN on exact LOSS is sound.
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::UNKNOWN), BVerdict::LOSS)
            == RcheckClass::SOUND_UNKNOWN_ON_LOSS);

    // UNKNOWN on exact WIN: tagged vs untagged conservatism split.
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::UNKNOWN, 0), BVerdict::WIN)
            == RcheckClass::CONSERVATIVE_UNTAGGED);
    REQUIRE(classify_rcheck(outcome(PipelineVerdict::UNKNOWN, 0x8), BVerdict::WIN)
            == RcheckClass::CONSERVATIVE_TAGGED);

    REQUIRE(rcheck_is_hard_fail(RcheckClass::HARD_FAIL_B_WIN));
    REQUIRE(rcheck_is_hard_fail(RcheckClass::HARD_FAIL_PESSIMAL_LOSS));
    REQUIRE_FALSE(rcheck_is_hard_fail(RcheckClass::CONSERVATIVE_TAGGED));
}

// ---------------------------------------------------------------------------
// throw_census_key
// ---------------------------------------------------------------------------

TEST_CASE("rcheck census key: ExpandError stage + runtime substrings + other",
          "[bucket][rcheck]") {
    REQUIRE(throw_census_key(ExpandError(ExpandError::Stage::ShiftViolation, "x"))
            == "expand:ShiftViolation");
    REQUIRE(throw_census_key(ExpandError(ExpandError::Stage::SupportFlip, "x"))
            == "expand:SupportFlip");

    REQUIRE(throw_census_key(std::runtime_error("... residual_unknown on side 0"))
            == "residual_unknown");
    REQUIRE(throw_census_key(std::runtime_error("registry: form-change ability (211)"))
            == "form-change");
    REQUIRE(throw_census_key(std::runtime_error("blah ai-final-gambit out of scope"))
            == "ai-final-gambit");
    REQUIRE(throw_census_key(std::runtime_error("... ai-bench living bench mon"))
            == "ai-bench");

    // Unrecognized runtime_error → "other:" + first 60 chars.
    std::string key = throw_census_key(std::runtime_error("something totally different"));
    REQUIRE(key.rfind("other:", 0) == 0);
    REQUIRE(key == "other:something totally different");
}

// ---------------------------------------------------------------------------
// Injected-pairs run: seams, no generator (MUST pass before any corpus run)
// ---------------------------------------------------------------------------

TEST_CASE("rcheck injected-pairs run: counts, hard_fails, JSONL shape, summary",
          "[bucket][rcheck]") {
    // Four matchups: a sound WIN, and one of each hard-fail, plus a conservative-untagged.
    std::vector<BattleState> matchups = {
        alive_state(2), alive_state(3), alive_state(4), alive_state(5)};

    // Pipeline seam: verdict per index.
    RcheckConfig cfg;
    cfg.injected = matchups;
    cfg.pipeline_fn = [&](const BattleState& s, const Question&) -> PipelineResult {
        PipelineResult r;
        int idx = s.side1.team[0].species;  // 2..5 encode the case
        if (idx == 2) { r.verdict = PipelineVerdict::WIN;     r.b_ran = true; }
        if (idx == 3) { r.verdict = PipelineVerdict::WIN;     r.b_ran = true; }   // hard fail B-WIN
        if (idx == 4) { r.verdict = PipelineVerdict::LOSS; }                       // hard fail pess-LOSS
        if (idx == 5) { r.verdict = PipelineVerdict::UNKNOWN; r.b_ran = true; }    // conservative-untagged
        return r;
    };
    cfg.exact_fn = [&](const BattleState& s, const Question&) -> BsolverResult {
        BsolverResult r;
        int idx = s.side1.team[0].species;
        r.verdict = (idx == 2) ? BVerdict::WIN
                  : (idx == 3) ? BVerdict::LOSS   // exact LOSS vs pipeline WIN → hard fail
                  : (idx == 4) ? BVerdict::WIN    // exact WIN vs pipeline LOSS → hard fail
                               : BVerdict::WIN;    // idx 5: conservative-untagged
        return r;
    };

    std::ostringstream out;
    RcheckReport rep = rcheck_run(cfg, out);

    REQUIRE(rep.n == 4);
    REQUIRE(rep.hard_fails == 2);
    REQUIRE(rep.bins[(int)RcheckClass::SOUND_AGREE_WIN] == 1);
    REQUIRE(rep.bins[(int)RcheckClass::HARD_FAIL_B_WIN] == 1);
    REQUIRE(rep.bins[(int)RcheckClass::HARD_FAIL_PESSIMAL_LOSS] == 1);
    REQUIRE(rep.bins[(int)RcheckClass::CONSERVATIVE_UNTAGGED] == 1);

    // Output = 4 records + 1 summary, all parseable JSON.
    std::vector<json> lines;
    std::string line;
    std::istringstream in(out.str());
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        lines.push_back(json::parse(line));
    }
    REQUIRE(lines.size() == 5);
    for (int i = 0; i < 4; ++i) {
        REQUIRE(lines[i].contains("classification"));
        REQUIRE(lines[i].contains("pipeline"));
        REQUIRE(lines[i].contains("exact"));
        REQUIRE(lines[i].contains("timing_us"));
    }
    // Last line is the summary; bins recomputed from records must match embedded summary.
    json summary = lines[4]["summary"];
    REQUIRE(summary["n"] == 4);
    REQUIRE(summary["hard_fails"] == 2);

    std::array<int, (int)RcheckClass::COUNT> recomputed{};
    for (int i = 0; i < 4; ++i) {
        std::string cn = lines[i]["classification"];
        for (int c = 0; c < (int)RcheckClass::COUNT; ++c)
            if (cn == rcheck_class_name((RcheckClass)c)) recomputed[c]++;
    }
    for (int c = 0; c < (int)RcheckClass::COUNT; ++c) {
        int embedded = summary["bins"][rcheck_class_name((RcheckClass)c)];
        REQUIRE(embedded == recomputed[c]);
    }
}

TEST_CASE("rcheck injected: thrown pipeline → THROWN + census", "[bucket][rcheck]") {
    RcheckConfig cfg;
    cfg.injected = {alive_state(2)};
    cfg.pipeline_fn = [](const BattleState&, const Question&) -> PipelineResult {
        throw ExpandError(ExpandError::Stage::ShiftViolation, "boom");
    };
    cfg.exact_fn = [](const BattleState&, const Question&) -> BsolverResult {
        BsolverResult r; r.verdict = BVerdict::WIN; return r;
    };
    std::ostringstream out;
    RcheckReport rep = rcheck_run(cfg, out);
    REQUIRE(rep.bins[(int)RcheckClass::THROWN] == 1);
    REQUIRE(rep.throw_census["expand:ShiftViolation"] == 1);
    REQUIRE(rep.hard_fails == 0);
}

TEST_CASE("rcheck: injected + repo_root is mutually exclusive (throws)", "[bucket][rcheck]") {
    RcheckConfig cfg;
    cfg.injected = {alive_state()};
    cfg.repo_root = "/some/path";
    std::ostringstream out;
    REQUIRE_THROWS_AS(rcheck_run(cfg, out), std::invalid_argument);
}

// ---------------------------------------------------------------------------
// Smoke corpus (real solvers): uniform seed 1 n=20 shard 0/1, small budgets
// ---------------------------------------------------------------------------

TEST_CASE("rcheck smoke corpus: real solvers, zero hard fails, consistent summary",
          "[bucket][rcheck][corpus]") {
    RcheckConfig cfg;
    cfg.seed      = 1;
    cfg.klass     = "uniform";
    cfg.n         = 20;
    cfg.shard_k   = 0;
    cfg.shard_of  = 1;
    cfg.repo_root = NUZLOCKE_REPO_ROOT;
    // Small budgets: most matchups INDETERMINATE, but the loop must complete cleanly.
    // Exact bsolver dominates runtime, so its budget is kept tiny for the smoke test;
    // the injected-pairs test covers the soundness-classification logic exhaustively.
    cfg.exact_leaves = 400; cfg.exact_nodes = 60;
    cfg.pess_leaves  = 1'500; cfg.pess_nodes = 300;
    cfg.b_depth      = 30;    cfg.b_visits   = 300;

    std::ostringstream out;
    RcheckReport rep = rcheck_run(cfg, out);

    REQUIRE(rep.n == 20);
    REQUIRE(rep.hard_fails == 0);

    int bin_sum = 0;
    for (int c = 0; c < (int)RcheckClass::COUNT; ++c) bin_sum += rep.bins[c];
    REQUIRE(bin_sum == 20);

    // Parse lines; last must be the summary and internally consistent.
    std::vector<json> lines;
    std::string line;
    std::istringstream in(out.str());
    while (std::getline(in, line))
        if (!line.empty()) lines.push_back(json::parse(line));
    REQUIRE(lines.size() == 21);  // 20 records + summary
    REQUIRE(lines.back().contains("summary"));
    REQUIRE(lines.back()["summary"]["n"] == 20);
    REQUIRE(lines.back()["summary"]["hard_fails"] == 0);
}
