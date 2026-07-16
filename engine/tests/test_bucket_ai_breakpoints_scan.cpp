// Bucket solver Task 9 mask-scan audit gate: over a MatchupGen corpus, sweep each HP
// axis and require EVERY adjacent AI-support flip (support_fingerprint change) to be
// covered by an instantiated breakpoint (h or h+1). This is the soundness gate for
// ai_breakpoint_entries: a missed flip means a bucket could straddle a support change
// (INV-1 violation). Uses support_fingerprint directly (NOT query_support_slots, which
// conflates switch/move slots). Pinch/Defeatist attacker regimes are swept separately.
#include <catch2/catch_test_macros.hpp>

#include "solver/bucket/ai_breakpoints.h"
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/expand.h"          // support_fingerprint
#include "solver/matchup_gen.h"
#include "solver/question.h"
#include "ai_analytic.h"                    // cpp_compute_action_probabilities
#include "ai_shared.h"                      // active_mon
#include "state.h"

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

namespace {

constexpr int32_t AB_BLAZE = 66, AB_TORRENT = 67, AB_OVERGROW = 65, AB_SWARM = 68;
constexpr int32_t AB_DEFEATIST = 129;

bool is_pinch(int32_t ab) {
    return ab == AB_BLAZE || ab == AB_TORRENT || ab == AB_OVERGROW || ab == AB_SWARM;
}
bool has(const std::vector<int32_t>& v, int32_t x) {
    return std::find(v.begin(), v.end(), x) != v.end();
}
int32_t max_hp_of(const PokemonState& m) {
    return m.has_max_hp ? m.max_hp : m.stat_hp;
}
int32_t cur_hp_of(const PokemonState& m) {
    return m.has_hp ? m.hp : max_hp_of(m);
}

struct Census {
    int scanned = 0;      // matchups whose instantiate succeeded (fully swept)
    int residual = 0, form = 0, gambit = 0, bench = 0;   // skipped-by-reason
    long flips = 0, explained = 0, unexplained = 0;
};

// Sweep one axis with the opposite side pinned at other_hp. Returns false and records the
// offending flip (via FAIL) on the first unexplained flip.
void sweep_axis(const BattleState& base, int axis_side, const std::vector<int32_t>& bps,
                int32_t axis_max, int other_side, int32_t other_hp,
                const std::string& tag, int idx, Census& cen) {
    BattleState pinned = base;
    { SideState& os = (other_side == 0) ? pinned.side0 : pinned.side1;
      os.team[os.active_indices[0]].hp = other_hp; }

    uint64_t prev = 0; bool have_prev = false;
    for (int32_t h = 1; h <= axis_max; ++h) {
        BattleState st = pinned;
        SideState& as = (axis_side == 0) ? st.side0 : st.side1;
        as.team[as.active_indices[0]].hp = h;
        uint64_t fp = support_fingerprint(cpp_compute_action_probabilities(st, 1));
        if (have_prev && fp != prev) {
            ++cen.flips;
            if (has(bps, h) || has(bps, h - 1)) {
                ++cen.explained;
            } else {
                ++cen.unexplained;
                FAIL("UNEXPLAINED FLIP class=" << tag << " idx=" << idx
                     << " axis=" << axis_side << " h=" << h
                     << " other_hp=" << other_hp
                     << " fp[h-1]=" << prev << " fp[h]=" << fp);
            }
        }
        prev = fp; have_prev = true;
    }
}

} // namespace

TEST_CASE("ai breakpoints mask-scan: zero unexplained AI-support flips over the corpus",
          "[bucket][ai_breakpoints][corpus]")
{
    static const std::string repo_root = NUZLOCKE_REPO_ROOT;
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    constexpr int N_PER_CLASS = 100;
    constexpr uint64_t SEED   = 1;

    const MatchupGen::Class classes[] = {
        MatchupGen::Class::Uniform,
        MatchupGen::Class::BerryHolders,
        MatchupGen::Class::SashSturdy,
    };
    const std::string names[] = { "uniform", "berry", "sash" };

    BreakpointRegistry reg;
    Question q;

    for (int c = 0; c < 3; ++c) {
        MatchupGen gen(SEED, classes[c], 0, 1, paths);
        Census cen;
        for (int i = 0; i < N_PER_CLASS; ++i) {
            BattleState s = gen.next();

            BpSet bp;
            try {
                bp = reg.instantiate(s, q);
            } catch (const std::runtime_error& ex) {
                std::string m = ex.what();
                if      (m.find("residual_unknown") != std::string::npos) ++cen.residual;
                else if (m.find("form-change")      != std::string::npos) ++cen.form;
                else if (m.find("ai-final-gambit")  != std::string::npos) ++cen.gambit;
                else if (m.find("ai-bench")         != std::string::npos) ++cen.bench;
                else FAIL("unexpected throw class=" << names[c] << " idx=" << i
                          << ": " << m);
                continue;
            }
            ++cen.scanned;

            const PokemonState& pl = active_mon(s, 0);
            const PokemonState& ai = active_mon(s, 1);
            int32_t pl_max = max_hp_of(pl), ai_max = max_hp_of(ai);

            // Player axis (AI attacking): AI at root, plus pinch/Defeatist regimes.
            sweep_axis(s, 0, bp.player_breakpoints(), pl_max, 1, cur_hp_of(ai),
                       names[c], i, cen);
            if (is_pinch(ai.ability))
                sweep_axis(s, 0, bp.player_breakpoints(), pl_max, 1, std::max(1, ai_max/3),
                           names[c], i, cen);
            if (ai.ability == AB_DEFEATIST)
                sweep_axis(s, 0, bp.player_breakpoints(), pl_max, 1, std::max(1, ai_max/2),
                           names[c], i, cen);

            // AI axis (player attacking): player at root, plus pinch/Defeatist regimes.
            sweep_axis(s, 1, bp.opp_breakpoints(), ai_max, 0, cur_hp_of(pl),
                       names[c], i, cen);
            if (is_pinch(pl.ability))
                sweep_axis(s, 1, bp.opp_breakpoints(), ai_max, 0, std::max(1, pl_max/3),
                           names[c], i, cen);
            if (pl.ability == AB_DEFEATIST)
                sweep_axis(s, 1, bp.opp_breakpoints(), ai_max, 0, std::max(1, pl_max/2),
                           names[c], i, cen);
        }

        REQUIRE(cen.unexplained == 0);
        REQUIRE(cen.scanned > 0);
        WARN("=== ai-bp mask-scan [" << names[c] << "] scanned=" << cen.scanned
             << " residual=" << cen.residual << " form=" << cen.form
             << " gambit=" << cen.gambit << " bench=" << cen.bench
             << " flips=" << cen.flips << " explained=" << cen.explained
             << " unexplained=" << cen.unexplained);
    }
}
