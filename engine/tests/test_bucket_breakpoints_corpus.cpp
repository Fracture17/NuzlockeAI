// Bucket solver Task 8 Step 4: corpus sweep audit over BreakpointRegistry::instantiate
// and residual_delta_candidates(). Mirrors the MatchupGen loader pattern established
// in test_bucket_crit_ordering.cpp (Uniform/BerryHolders/SashSturdy, seed 1, 500/class).
// Every matchup+side must land in one of three allowed buckets: (a) instantiate()
// succeeds with structural invariants intact, (b) throws runtime_error containing
// "residual_unknown", (c) throws runtime_error containing "form-change". Any other
// outcome (unexpected exception type, wrong message, structural violation) fails
// the test outright. residual_delta_candidates() must never throw and must always
// include 0.
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/breakpoints.h"
#include "solver/bucket/expand.h"
#include "solver/engine_queries.h"
#include "solver/matchup_gen.h"
#include "solver/question.h"
#include "state.h"

#include <algorithm>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

Question default_question() {
    Question q;
    return q;
}

// Structural checks on one instantiated axis: sorted+unique, in [0,max_hp], and
// {0,max_hp} present (mandatory boundaries per breakpoints.h docstring).
void check_axis_structure(const std::vector<int32_t>& bps, int32_t max_hp) {
    for (size_t i = 0; i + 1 < bps.size(); ++i) {
        REQUIRE(bps[i] < bps[i + 1]);   // strictly increasing => sorted + unique
    }
    for (int32_t b : bps) {
        REQUIRE(b >= 0);
        REQUIRE(b <= max_hp);
    }
    REQUIRE(std::find(bps.begin(), bps.end(), 0) != bps.end());
    REQUIRE(std::find(bps.begin(), bps.end(), max_hp) != bps.end());
}

int32_t axis_max_hp(const BattleState& state, int side) {
    const SideState& ss = (side == 0) ? state.side0 : state.side1;
    const PokemonState& m = ss.team[ss.active_indices[0]];
    return m.has_max_hp ? m.max_hp : (m.has_stats ? m.stat_hp : 0);
}

} // namespace

TEST_CASE("breakpoints corpus sweep: instantiate() lands in an allowed outcome bucket",
          "[bucket][breakpoints][corpus]")
{
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    constexpr int N_PER_CLASS = 500;
    constexpr uint64_t SEED   = 1;

    const MatchupGen::Class classes[] = {
        MatchupGen::Class::Uniform,
        MatchupGen::Class::BerryHolders,
        MatchupGen::Class::SashSturdy,
    };
    const std::string class_names[] = { "uniform", "berry", "sash" };

    BreakpointRegistry reg;
    int success_count = 0;
    int residual_unknown_count = 0;
    int form_change_count = 0;
    int total = 0;

    for (int c = 0; c < 3; ++c) {
        MatchupGen gen(SEED, classes[c], 0, 1, paths);
        for (int i = 0; i < N_PER_CLASS; ++i) {
            BattleState state = gen.next();
            ++total;
            try {
                BpSet bp = reg.instantiate(state, default_question());
                check_axis_structure(bp.player_breakpoints(), axis_max_hp(state, 0));
                check_axis_structure(bp.opp_breakpoints(),    axis_max_hp(state, 1));
                ++success_count;
            } catch (const std::runtime_error& e) {
                std::string msg = e.what();
                if (msg.find("residual_unknown") != std::string::npos) {
                    ++residual_unknown_count;
                } else if (msg.find("form-change") != std::string::npos) {
                    ++form_change_count;
                } else {
                    FAIL("unexpected runtime_error (class=" << class_names[c]
                         << " idx=" << i << "): " << msg);
                }
            }
        }
    }

    REQUIRE(total == 1500);
    REQUIRE(success_count + residual_unknown_count + form_change_count == total);

    WARN("=== Breakpoint corpus sweep ===");
    WARN("  total=" << total
         << " success=" << success_count
         << " residual_unknown=" << residual_unknown_count
         << " form_change=" << form_change_count);
}

TEST_CASE("residual delta corpus sweep: residual_delta_candidates never throws, always includes 0",
          "[bucket][expand][corpus]")
{
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    constexpr int N_PER_CLASS = 500;
    constexpr uint64_t SEED   = 1;

    const MatchupGen::Class classes[] = {
        MatchupGen::Class::Uniform,
        MatchupGen::Class::BerryHolders,
        MatchupGen::Class::SashSturdy,
    };

    int checked = 0;
    for (int c = 0; c < 3; ++c) {
        MatchupGen gen(SEED, classes[c], 0, 1, paths);
        for (int i = 0; i < N_PER_CLASS; ++i) {
            BattleState state = gen.next();
            for (int side = 0; side <= 1; ++side) {
                std::vector<int32_t> deltas = residual_delta_candidates(state, side);
                REQUIRE(std::find(deltas.begin(), deltas.end(), 0) != deltas.end());
                for (int32_t d : deltas) {
                    REQUIRE(d > std::numeric_limits<int32_t>::min());
                    REQUIRE(d < std::numeric_limits<int32_t>::max());
                }
                ++checked;
            }
        }
    }
    REQUIRE(checked == 3000);
}
