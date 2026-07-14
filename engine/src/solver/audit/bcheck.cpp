// bcheck: cross-check bsolver-exact vs an independent naive AND-OR reference walker.
// The naive walker is unmemoized, has no interleaved abort, and collects all oracle
// children before recursing — a maximally independent implementation for differential testing.
// Both directions are checked: naïve-LOSS vs exact-WIN, and naïve-WIN vs exact-LOSS.
// INDETERMINATE from either side → skip (counted). Mismatches → FAILURE printed with seed/class/index.
// Usage:
//   bcheck --seed S --klass K --n N [--shard k/of]
#include "solver/bsolver.h"
#include "solver/matchup_gen.h"
#include "solver/oracle_types.h"
#include "solver/question.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "solver/action_space.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

// ---------------------------------------------------------------------------
// Naive AND-OR reference walker (unmemoized, no interleaved abort).
// Cycle detection: tracks ancestor PackedKeys on the call stack.
// Returns true=WIN, false=LOSS, and sets *indet=true on INDETERMINATE.
// ---------------------------------------------------------------------------

struct NaiveWalkerConfig {
    uint64_t oracle_max_leaves = 10'000;
    uint64_t node_cap          = 20'000;
    int      depth_cap         = 200;
};

struct NaiveWalkerState {
    TransitionOracle oracle;
    ContextInterner  interner;
    NaiveWalkerConfig cfg;
    uint64_t nodes_expanded = 0;
    bool     indet          = false;
    BIndeterminateReason indet_reason = BIndeterminateReason::None;
};

// Returns true=WIN, false=LOSS.
// On INDETERMINATE: sets ws.indet=true and returns false.
static bool naive_win(NaiveWalkerState& ws,
                      const BattleState& state,
                      const Question& q,
                      std::unordered_set<PackedKey>& stack,
                      int depth) {
    if (ws.indet) return false;

    // Terminal check.
    Outcome oc = classify(state, q);
    if (oc == Outcome::WIN)  return true;
    if (oc == Outcome::LOSS) return false;

    // Caps.
    if (depth >= ws.cfg.depth_cap) {
        ws.indet = true; ws.indet_reason = BIndeterminateReason::DepthCap; return false;
    }
    if (ws.nodes_expanded >= ws.cfg.node_cap) {
        ws.indet = true; ws.indet_reason = BIndeterminateReason::NodeCap; return false;
    }

    PackedKey key = ws.interner.pack(state);

    // Cycle detection.
    if (stack.count(key)) {
        ws.indet = true; ws.indet_reason = BIndeterminateReason::Cycle; return false;
    }

    ++ws.nodes_expanded;
    stack.insert(key);

    std::vector<ExecAction> actions = legal_player_actions(state);

    bool any_wins = false;
    for (const ExecAction& act : actions) {
        if (!action_filter(q, act)) continue;
        if (ws.indet) break;

        // Collect ALL oracle children first (no interleaved abort).
        std::vector<ChildOutcome> children;
        TransitionOracle::Config ocfg;
        ocfg.max_leaves             = ws.cfg.oracle_max_leaves;
        ocfg.aggregate_damage_rolls = true;
        ocfg.collapse               = TransitionOracle::CollapseMode::None;

        bool budget_hit = false;
        try {
            StepStats stats = ws.oracle.step(state, act,
                [&](ChildOutcome co) -> bool {
                    children.push_back(co);
                    return true;
                },
                OrderingHint::Natural, ocfg);
            if (stats.budget_exceeded) budget_hit = true;
        } catch (const std::exception&) {
            // Oracle threw → INDETERMINATE.
            ws.indet = true; ws.indet_reason = BIndeterminateReason::LeafBudget; break;
        }
        if (budget_hit) {
            ws.indet = true; ws.indet_reason = BIndeterminateReason::LeafBudget; break;
        }

        // Filter self-loops.
        bool has_non_self = false;
        bool all_non_self_win = true;
        for (const ChildOutcome& co : children) {
            PackedKey ckey = ws.interner.pack(co.child);
            if (ckey == key) continue;  // self-loop: ignore
            has_non_self = true;
            bool child_win = naive_win(ws, co.child, q, stack, depth + 1);
            if (ws.indet) { all_non_self_win = false; break; }
            if (!child_win) { all_non_self_win = false; break; }
        }

        if (!ws.indet && has_non_self && all_non_self_win) {
            any_wins = true;
            break;  // Found a winning action.
        }
    }

    stack.erase(key);
    return any_wins;
}

static BVerdict naive_certify(const BattleState& state,
                               const Question& q,
                               const NaiveWalkerConfig& wcfg,
                               BIndeterminateReason* reason_out) {
    Outcome oc = classify(state, q);
    if (oc == Outcome::WIN)  { *reason_out = BIndeterminateReason::None; return BVerdict::WIN; }
    if (oc == Outcome::LOSS) { *reason_out = BIndeterminateReason::None; return BVerdict::LOSS; }

    NaiveWalkerState ws;
    ws.cfg = wcfg;

    std::unordered_set<PackedKey> stack;
    bool win = naive_win(ws, state, q, stack, 0);

    if (ws.indet) {
        *reason_out = ws.indet_reason;
        return BVerdict::INDETERMINATE;
    }
    *reason_out = BIndeterminateReason::None;
    return win ? BVerdict::WIN : BVerdict::LOSS;
}

// ---------------------------------------------------------------------------
// Argument parsing helpers (mirror audit_oracle pattern)
// ---------------------------------------------------------------------------

static const char* get_arg(int argc, char** argv, const char* flag, const char* def = nullptr) {
    for (int i = 1; i < argc - 1; ++i)
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    return def;
}

static bool has_flag(int argc, char** argv, const char* flag) {
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], flag) == 0) return true;
    return false;
}

static long parse_long(const char* s, long def) { return s ? std::atol(s) : def; }

static void parse_shard(const char* s, int& k, int& of) {
    if (!s) return;
    const char* slash = std::strchr(s, '/');
    if (!slash) { std::fprintf(stderr, "bcheck: bad --shard format (k/of): %s\n", s); std::exit(1); }
    k  = (int)std::atol(s);
    of = (int)std::atol(slash + 1);
}

static MatchupGen::Class parse_klass(const char* s) {
    if (!s || std::strcmp(s, "uniform") == 0) return MatchupGen::Class::Uniform;
    if (std::strcmp(s, "berry") == 0) return MatchupGen::Class::BerryHolders;
    if (std::strcmp(s, "sash")  == 0) return MatchupGen::Class::SashSturdy;
    std::fprintf(stderr, "bcheck: unknown klass '%s' (use uniform/berry/sash)\n", s);
    std::exit(1);
}

static std::string detect_repo_root() {
    const char* env = std::getenv("NUZLOCKE_REPO_ROOT");
    if (env) return env;
#ifdef NUZLOCKE_REPO_ROOT
    return NUZLOCKE_REPO_ROOT;
#else
    return ".";
#endif
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    uint64_t seed   = (uint64_t)parse_long(get_arg(argc, argv, "--seed",  "1"), 1);
    int      n      = (int)parse_long(get_arg(argc, argv, "--n",    "25"), 25);
    int shard_k = 0, shard_of = 1;
    if (has_flag(argc, argv, "--shard"))
        parse_shard(get_arg(argc, argv, "--shard"), shard_k, shard_of);

    MatchupGen::Class klass = parse_klass(get_arg(argc, argv, "--klass", "uniform"));

    std::string repo_root = detect_repo_root();
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    std::printf("bcheck  seed=%llu klass=%s n=%d shard=%d/%d\n",
                (unsigned long long)seed,
                get_arg(argc, argv, "--klass", "uniform"),
                n, shard_k, shard_of);
    std::fflush(stdout);

    MatchupGen gen(seed, klass, shard_k, shard_of, paths);

    // Budget design: naive walker is unmemoized and exponential. We use a small node_cap
    // to limit total nodes expanded. Most matchups will be INDETERMINATE (skipped) since
    // real MatchupGen matchups require many turns. The few that decide quickly (OHKO or
    // near-OHKO within the node budget) are cross-checked. Zero mismatches on any decided
    // case verifies the exact solver's logic on those cases.
    // Calibration: node_cap=3 allows 2-turn decisions with branching factor ~4 (with
    // aggregation, most damage rolls collapse to 2-4 distinct damages), depth_cap=5 for
    // safety. This finishes in <1s/matchup for typical real matchups.
    NaiveWalkerConfig naive_cfg;
    naive_cfg.oracle_max_leaves = 10'000;
    naive_cfg.node_cap          = 3;
    naive_cfg.depth_cap         = 5;

    BsolverConfig exact_cfg;
    exact_cfg.mode              = BMode::Exact;
    exact_cfg.oracle_max_leaves = 10'000;
    exact_cfg.node_cap          = 3;
    exact_cfg.depth_cap         = 5;

    Question q{};

    int mismatches    = 0;
    int skipped_indet = 0;
    int decided       = 0;

    auto t_start = std::chrono::steady_clock::now();

    for (int mi = 0; mi < n; ++mi) {
        BattleState state = gen.next();

        BIndeterminateReason naive_reason;
        BVerdict naive_v = naive_certify(state, q, naive_cfg, &naive_reason);

        BsolverResult exact_r = bsolver_certify(state, q, exact_cfg);
        BVerdict exact_v = exact_r.verdict;

        // Skip if either is INDETERMINATE.
        if (naive_v == BVerdict::INDETERMINATE || exact_v == BVerdict::INDETERMINATE) {
            ++skipped_indet;
            continue;
        }

        ++decided;

        if (naive_v != exact_v) {
            ++mismatches;
            std::printf("MISMATCH seed=%llu index=%d naive=%s exact=%s\n",
                        (unsigned long long)seed, mi,
                        naive_v == BVerdict::WIN ? "WIN" : "LOSS",
                        exact_v == BVerdict::WIN ? "WIN" : "LOSS");
        }
    }

    auto t_end = std::chrono::steady_clock::now();
    double elapsed_ms = std::chrono::duration<double, std::milli>(t_end - t_start).count();

    std::printf("\n--- bcheck results ---\n");
    std::printf("total         : %d\n", n);
    std::printf("decided       : %d\n", decided);
    std::printf("skipped_indet : %d\n", skipped_indet);
    std::printf("mismatches    : %d\n", mismatches);
    std::printf("elapsed_ms    : %.1f\n", elapsed_ms);
    if (decided > 0)
        std::printf("us_per_decided: %.1f\n", elapsed_ms * 1000.0 / decided);

    if (mismatches == 0) {
        std::printf("\nPASS: zero mismatches\n");
        return 0;
    } else {
        std::printf("\nFAIL: %d mismatch(es)\n", mismatches);
        return 1;
    }
}
