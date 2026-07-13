// Single-case debug trace tool. Regenerates one matchup and enumerates all leaves with
// full event paths, or replays a single leaf with the analytical RNG log dump.
// Usage: solver_trace --seed S --klass K --index I --action A [--leaf L]
//   --seed S   : MatchupGen seed
//   --klass K  : uniform | berry | sash
//   --index I  : matchup index in the unsharded stream (0-based)
//   --action A : player action index in legal_player_actions(state) (0-based)
//   --leaf L   : (optional) 0-based leaf index to replay with full analytical log
#include "solver/audit/audit_core.h"   // detect_repo_root via NUZLOCKE_REPO_ROOT, parse_klass

#include "ai_analytic.h"
#include "logger.h"
#include "move_exec.h"
#include "move_exec_damage.h"
#include "oracle.h"
#include "solver/action_space.h"
#include "solver/matchup_gen.h"
#include "solver/oracle_types.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "solver_turn.h"
#include "state.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static const char* get_arg(int argc, char** argv, const char* flag, const char* def = nullptr) {
    for (int i = 1; i < argc - 1; ++i)
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    return def;
}

static long parse_long(const char* s, long def = 0) { return s ? std::atol(s) : def; }

static std::string detect_repo_root() {
    const char* env = std::getenv("NUZLOCKE_REPO_ROOT");
    if (env) return std::string(env);
#ifdef NUZLOCKE_REPO_ROOT
    return NUZLOCKE_REPO_ROOT;
#else
    return ".";
#endif
}

static MatchupGen::Class parse_klass(const std::string& k) {
    if (k == "uniform") return MatchupGen::Class::Uniform;
    if (k == "berry")   return MatchupGen::Class::BerryHolders;
    if (k == "sash")    return MatchupGen::Class::SashSturdy;
    std::fprintf(stderr, "solver_trace: unknown klass '%s'\n", k.c_str());
    std::exit(1);
}

// Print a readable state summary (species/HP/moves of both actives).
static void print_state(const BattleState& s) {
    auto print_side = [](const char* name, const SideState& side) {
        if (side.active_indices.empty()) { std::printf("  %s: (no active)\n", name); return; }
        int idx = side.active_indices[0];
        if (idx < 0 || idx >= (int)side.team.size()) { std::printf("  %s: (bad idx)\n", name); return; }
        const PokemonState& mon = side.team[idx];
        std::printf("  %s: species=%d  HP=%d/%d  ability=%d  item=%d\n",
                    name, mon.species, mon.hp, mon.max_hp, mon.ability, mon.item);
        std::printf("        moves=[%d pp=%d, %d pp=%d, %d pp=%d, %d pp=%d]\n",
                    mon.move_id0, mon.move_pp0, mon.move_id1, mon.move_pp1,
                    mon.move_id2, mon.move_pp2, mon.move_id3, mon.move_pp3);
    };
    std::printf("--- state (turn=%d) ---\n", s.turn_number);
    print_side("player (side0)", s.side0);
    print_side("opp    (side1)", s.side1);
}

// Print a LeafPathEntry as a human-readable line.
static void print_path_entry(int step, const LeafPathEntry& e) {
    const char* ch = (e.channel == LeafChannel::CatA) ? "CatA" : "CatB";
    if (e.value2 >= 0) {
        std::printf("  [%2d] %s  event=%-3d occ=%d  value=%d/%d  p=%.6f\n",
                    step, ch, e.event, e.occurrence, e.value, e.value2, e.prob);
    } else {
        std::printf("  [%2d] %s  event=%-3d occ=%d  value=%-4d   p=%.6f\n",
                    step, ch, e.event, e.occurrence, e.value, e.prob);
    }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr,
            "Usage: solver_trace --seed S --klass K --index I --action A [--leaf L]\n");
        return 1;
    }

    uint64_t seed    = (uint64_t)parse_long(get_arg(argc, argv, "--seed",   "1"), 1);
    std::string klass = get_arg(argc, argv, "--klass",  "uniform");
    int mi           = (int)parse_long(get_arg(argc, argv, "--index",  "0"), 0);
    int ai           = (int)parse_long(get_arg(argc, argv, "--action", "0"), 0);
    int leaf_idx     = (int)parse_long(get_arg(argc, argv, "--leaf",   "-1"), -1);

    std::string repo_root = detect_repo_root();
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    // ---- Regenerate matchup ----
    MatchupGen gen(seed, parse_klass(klass), 0, 1, paths);
    for (int i = 0; i <= mi; ++i) {
        BattleState state = gen.next();
        if (i < mi) continue;

        // Print state
        print_state(state);

        // Print AI distribution
        std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(state, 1);
        std::printf("\nAI distribution (%zu actions):\n", ai_probs.size());
        for (size_t k = 0; k < ai_probs.size(); ++k) {
            const ExecAction& a = ai_probs[k].action;
            std::printf("  [%zu] p=%.6f  kind=%d slot=%d mega=%d\n",
                        k, ai_probs[k].prob, a.kind, a.move_slot, (int)a.mega);
        }

        // Pick player action
        std::vector<ExecAction> actions = legal_player_actions(state);
        if (ai < 0 || ai >= (int)actions.size()) {
            std::fprintf(stderr,
                "solver_trace: --action %d out of range (0..%d)\n",
                ai, (int)actions.size() - 1);
            return 1;
        }
        const ExecAction& player_action = actions[ai];
        std::printf("\nPlayer action [%d]: kind=%d slot=%d mega=%d\n",
                    ai, player_action.kind, player_action.move_slot, (int)player_action.mega);

        // ---- Enumerate all leaves with debug callback ----
        TransitionOracle oracle;
        TransitionOracle::Config cfg;

        int leaf_counter = 0;
        int target_leaf  = leaf_idx;

        // Collected leaves (for --leaf replay, we need the path).
        struct LeafRecord {
            LeafDebugInfo  dbg;
            ChildOutcome   co;
        };
        std::vector<LeafRecord> records;

        cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
            records.push_back(LeafRecord{dbg, ChildOutcome{}});
        };

        std::printf("\n--- leaf enumeration ---\n");
        double cum_sum = 0.0;
        StepStats stats = oracle.step(state, player_action, [&](ChildOutcome co) -> bool {
            // Store child in corresponding record.
            if (!records.empty()) records.back().co = co;

            cum_sum += co.prob;
            int li = leaf_counter++;
            std::printf("leaf[%d]  p=%.8f  cum=%.8f\n", li, co.prob, cum_sum);

            // Print event path for this leaf.
            if (!records.empty()) {
                const auto& dbg = records.back().dbg;
                for (int s = 0; s < (int)dbg.path.size(); ++s)
                    print_path_entry(s, dbg.path[s]);
            }
            std::printf("\n");
            return true;
        }, OrderingHint::Natural, cfg);

        std::printf("--- stats: leaves=%llu execs=%llu aborted=%d budget_exceeded=%d ---\n",
                    (unsigned long long)stats.leaves,
                    (unsigned long long)stats.turn_executions,
                    (int)stats.aborted,
                    (int)stats.budget_exceeded);
        std::printf("sum_p = %.10f\n", cum_sum);

        // ---- Leaf replay with analytical log dump ----
        if (target_leaf >= 0) {
            if (target_leaf >= (int)records.size()) {
                std::fprintf(stderr,
                    "solver_trace: --leaf %d out of range (0..%d)\n",
                    target_leaf, (int)records.size() - 1);
                return 1;
            }

            const LeafRecord& lr = records[target_leaf];
            std::printf("\n--- leaf[%d] analytical log replay ---\n", target_leaf);
            std::printf("path (%zu steps):\n", lr.dbg.path.size());
            for (int s = 0; s < (int)lr.dbg.path.size(); ++s)
                print_path_entry(s, lr.dbg.path[s]);

            // Set up analytical logger and replay this exact leaf path.
            AnalyticalRngLog log;
            set_analytical_rng_log(&log);

            // The oracle would replay by invoking step() with the config again for this specific
            // leaf. We can't directly replay ONE leaf from the outside without replicating the DFS.
            // Instead, just dump the already-captured debug path as the "analytical log".
            set_analytical_rng_log(nullptr);

            std::printf("\nanalytical log for leaf[%d] (from oracle DFS path):\n", target_leaf);
            std::printf("  cumulative_prob = %.10f\n", lr.dbg.cumulative_prob);
            for (size_t ei = 0; ei < lr.dbg.path.size(); ++ei) {
                const LeafPathEntry& e = lr.dbg.path[ei];
                std::printf("  entry[%zu]: %s event=%d occ=%d value=%d",
                            ei,
                            (e.channel == LeafChannel::CatA) ? "CatA" : "CatB",
                            e.event, e.occurrence, e.value);
                if (e.value2 >= 0) std::printf("/%d", e.value2);
                std::printf("  p=%.8f\n", e.prob);
            }
        }

        return 0;
    }

    std::fprintf(stderr, "solver_trace: matchup index %d not reached\n", mi);
    return 1;
}
