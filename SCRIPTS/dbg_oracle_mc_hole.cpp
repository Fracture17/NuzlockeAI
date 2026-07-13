// Debug repro for mc completeness holes: seed=7 uniform matchup=4.
// Re-runs a failing sample with the analytical RNG log attached, dumps the
// sampled run's draw sequence and the sampled child's key fields, and compares
// against oracle support entries with the same HP pair.
#include "solver/matchup_gen.h"
#include "solver/transition_oracle.h"
#include "solver/state_codec.h"
#include "solver/oracle_types.h"
#include "solver/action_space.h"
#include "ai_analytic.h"
#include "logger.h"
#include "move_exec.h"
#include "move_exec_damage.h"
#include "native_rng.h"
#include "oracle.h"
#include "solver_turn.h"
#include "state.h"

#include <cstdio>
#include <cstdint>
#include <vector>
#include <unordered_map>

static void dump_mon(const char* tag, const PokemonState& m) {
    std::printf("  %s: sp=%d hp=%d/%d status=%d item=%d cberry=%d stages=[%d %d %d %d %d %d %d] vol=0x%x pp=[%d %d %d %d] crit=%d\n",
        tag, m.species, m.hp, m.max_hp, m.status, m.item, m.consumed_berry,
        m.stage0, m.stage1, m.stage2, m.stage3, m.stage4, m.stage5, m.stage6,
        (unsigned)m.volatiles,
        m.move_pp0, m.move_pp1, m.move_pp2, m.move_pp3, m.crit_stage);
}

int main() {
    MatchupGen::Paths paths{
        std::string(NUZLOCKE_REPO_ROOT) + "/liveplay/data/generated_learnsets.json",
        std::string(NUZLOCKE_REPO_ROOT) + "/liveplay/data/generated_abilities.json"};
    MatchupGen gen(7, MatchupGen::Class::Uniform, 0, 1, paths);
    BattleState state;
    for (int i = 0; i <= 4; ++i) state = gen.next();

    std::vector<ExecAction> actions = legal_player_actions(state);
    const ExecAction& player_action = actions[0];

    // --- oracle support ---
    TransitionOracle oracle;
    ContextInterner interner;
    std::unordered_map<PackedKey, double> support;
    std::vector<BattleState> support_children;
    oracle.step(state, player_action, [&](ChildOutcome co) -> bool {
        support[interner.pack(co.child)] += co.prob;
        support_children.push_back(co.child);
        return true;
    });
    std::printf("support size: %zu keys, %zu leaves\n", support.size(), support_children.size());

    // --- failing sample ---
    uint64_t sample_seed = 17793609081811507740ULL;
    // AI action: sample same way as audit_core
    std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(state, 1);
    std::vector<double> ai_cum; double cum = 0;
    for (auto& ap : ai_probs) { cum += ap.prob; ai_cum.push_back(cum); }
    NativeRng ai_sampler(sample_seed ^ 0xA5A5A5A5A5A5A5A5ULL);
    double ai_roll = ai_sampler.random();
    int ai_choice = (int)ai_probs.size() - 1;
    for (int i = 0; i < (int)ai_cum.size(); ++i) if (ai_roll < ai_cum[i]) { ai_choice = i; break; }
    std::printf("AI action sampled: idx=%d slot=%d p=%f\n", ai_choice,
                ai_probs[ai_choice].action.move_slot, ai_probs[ai_choice].prob);

    NativeRng rng(sample_seed);
    DamageLoopLuck lp0{}, lp1{};
    TurnLuck tl0{}, tl1{};
    lp0.random_mode = true; lp0.rng = &rng;
    lp1.random_mode = true; lp1.rng = &rng;
    tl0.random_mode = true; tl0.rng = &rng;
    tl1.random_mode = true; tl1.rng = &rng;

    AnalyticalRngLog log;
    set_analytical_rng_log(&log);

    BattleState child = state;
    std::vector<ExecAction> a0 = {player_action};
    std::vector<ExecAction> a1 = {ai_probs[ai_choice].action};
    OracleOverrides empty_ov;
    SolverTurnResult res = cpp_run_one_turn_solver(child, a0, a1, lp0, lp1, tl0, tl1,
                                                   false, false, empty_ov);
    set_analytical_rng_log(nullptr);
    std::printf("sample run: ok=%d paused=%d err=%s\n", (int)res.ok, (int)res.paused, res.error.c_str());

    std::printf("--- sampled run RNG log (%zu entries) ---\n", log.size());
    for (size_t i = 0; i < log.size(); ++i) {
        const AnalyticalRngEntry& e = log.at(i);
        std::printf("  [%zu] event=%d chosen=%d p_chosen=%f n_opts=%d trunc=%d\n",
                    i, e.event, e.chosen, e.p_chosen, (int)e.options_count, (int)e.options_truncated);
    }

    std::printf("--- sampled child ---\n");
    dump_mon("player", child.side0.team[0]);
    dump_mon("opp   ", child.side1.team[0]);

    PackedKey k = interner.pack(child);
    std::printf("sampled key=0x%llx in_support=%d\n", (unsigned long long)k,
                (int)(support.find(k) != support.end()));

    // Compare against support children with the same HP pair
    int shown = 0;
    for (const auto& c : support_children) {
        if (c.side0.team[0].hp == child.side0.team[0].hp &&
            c.side1.team[0].hp == child.side1.team[0].hp) {
            std::printf("--- support child with same HP pair (key=0x%llx) ---\n",
                        (unsigned long long)interner.pack(c));
            dump_mon("player", c.side0.team[0]);
            dump_mon("opp   ", c.side1.team[0]);
            if (++shown >= 3) break;
        }
    }
    if (!shown) std::printf("(no support child with same HP pair %d/%d)\n",
                            child.side0.team[0].hp, child.side1.team[0].hp);
    return 0;
}
