// Benchmark harness for TransitionOracle::step(). Measures per-(state,action) wall-time
// and leaf throughput across MatchupGen classes. Prints percentiles, leaves/sec, leaf-count
// histogram, and budget-exceeded count. EXCLUDE_FROM_ALL; never slows the default build.
//
// Usage: bench_oracle [--seed N] [--g N] [--klass uniform|berry|sash|all] [--budget N]
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include "solver/action_space.h"
#include "solver/matchup_gen.h"
#include "solver/oracle_types.h"
#include "solver/transition_oracle.h"
#include "state.h"

namespace {

using Clock = std::chrono::steady_clock;

// Detect repo root from compile-time define, then env, then ".".
std::string detect_repo_root() {
    const char* env = std::getenv("NUZLOCKE_REPO_ROOT");
    if (env) return std::string(env);
#ifdef NUZLOCKE_REPO_ROOT
    return NUZLOCKE_REPO_ROOT;
#else
    return ".";
#endif
}

// Argument helpers (same pattern as audit_oracle.cpp).
static const char* get_arg(int argc, char** argv, const char* flag, const char* default_val) {
    for (int i = 1; i < argc - 1; ++i) {
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    }
    return default_val;
}

MatchupGen::Class parse_single_klass(const char* s) {
    if (std::strcmp(s, "uniform") == 0) return MatchupGen::Class::Uniform;
    if (std::strcmp(s, "berry")   == 0) return MatchupGen::Class::BerryHolders;
    if (std::strcmp(s, "sash")    == 0) return MatchupGen::Class::SashSturdy;
    std::fprintf(stderr, "bench_oracle: unknown klass '%s' (expected uniform|berry|sash|all)\n", s);
    std::exit(1);
}

const char* klass_name(MatchupGen::Class k) {
    switch (k) {
        case MatchupGen::Class::Uniform:      return "uniform";
        case MatchupGen::Class::BerryHolders: return "berry";
        case MatchupGen::Class::SashSturdy:   return "sash";
    }
    return "?";
}

// Histogram buckets: exactly 1, ≤16, ≤512, ≤32768, >32768.
struct LeafHistogram {
    uint64_t eq1    = 0;
    uint64_t le16   = 0;
    uint64_t le512  = 0;
    uint64_t le32k  = 0;
    uint64_t gt32k  = 0;

    void record(uint64_t leaves) {
        if      (leaves == 1)     ++eq1;
        else if (leaves <= 16)    ++le16;
        else if (leaves <= 512)   ++le512;
        else if (leaves <= 32768) ++le32k;
        else                      ++gt32k;
    }
};

// Per-class (or overall) aggregated stats.
struct ClassStats {
    std::vector<double> durations_ns;  // one entry per (state,action) step() call
    uint64_t total_leaves         = 0;
    uint64_t total_turn_execs     = 0;
    uint64_t budget_exceeded      = 0;
    double   total_wall_sec       = 0.0;
    LeafHistogram hist;
};

double percentile(std::vector<double>& sorted_v, double p) {
    if (sorted_v.empty()) return 0.0;
    double idx = p * (sorted_v.size() - 1);
    size_t lo = (size_t)idx;
    size_t hi = lo + 1 < sorted_v.size() ? lo + 1 : lo;
    double frac = idx - lo;
    return sorted_v[lo] * (1.0 - frac) + sorted_v[hi] * frac;
}

void print_class_report(const char* label, ClassStats& cs) {
    std::sort(cs.durations_ns.begin(), cs.durations_ns.end());

    double p50  = percentile(cs.durations_ns, 0.50);
    double p90  = percentile(cs.durations_ns, 0.90);
    double p99  = percentile(cs.durations_ns, 0.99);
    double pmax = cs.durations_ns.empty() ? 0.0 : cs.durations_ns.back();

    double leaves_per_sec = cs.total_wall_sec > 0.0
        ? (double)cs.total_leaves / cs.total_wall_sec
        : 0.0;

    std::printf("\n=== class: %s ===\n", label);
    std::printf("  (state,action) calls  : %zu\n", cs.durations_ns.size());
    std::printf("  total leaves          : %llu\n",   (unsigned long long)cs.total_leaves);
    std::printf("  total turn executions : %llu\n",   (unsigned long long)cs.total_turn_execs);
    std::printf("  budget_exceeded       : %llu\n",   (unsigned long long)cs.budget_exceeded);
    std::printf("  leaves/sec            : %.0f\n",   leaves_per_sec);
    std::printf("  wall time (sec)       : %.3f\n",   cs.total_wall_sec);
    std::printf("  step() wall-time percentiles (ns):\n");
    std::printf("    p50  = %.1f ns\n",  p50);
    std::printf("    p90  = %.1f ns\n",  p90);
    std::printf("    p99  = %.1f ns\n",  p99);
    std::printf("    max  = %.1f ns\n",  pmax);
    std::printf("  leaf-count histogram:\n");
    std::printf("    == 1      : %llu\n", (unsigned long long)cs.hist.eq1);
    std::printf("    (1,16]    : %llu\n", (unsigned long long)cs.hist.le16);
    std::printf("    (16,512]  : %llu\n", (unsigned long long)cs.hist.le512);
    std::printf("    (512,32k] : %llu\n", (unsigned long long)cs.hist.le32k);
    std::printf("    >32k      : %llu\n", (unsigned long long)cs.hist.gt32k);
}

void accumulate(ClassStats& dst, const ClassStats& src) {
    dst.durations_ns.insert(dst.durations_ns.end(),
                            src.durations_ns.begin(), src.durations_ns.end());
    dst.total_leaves     += src.total_leaves;
    dst.total_turn_execs += src.total_turn_execs;
    dst.budget_exceeded  += src.budget_exceeded;
    dst.total_wall_sec   += src.total_wall_sec;
    dst.hist.eq1   += src.hist.eq1;
    dst.hist.le16  += src.hist.le16;
    dst.hist.le512 += src.hist.le512;
    dst.hist.le32k += src.hist.le32k;
    dst.hist.gt32k += src.hist.gt32k;
}

// Run benchmark for one class. Returns accumulated stats.
ClassStats run_class(MatchupGen::Class klass, int g, uint64_t seed,
                     uint64_t budget, const MatchupGen::Paths& paths) {
    MatchupGen gen(seed, klass, 0, 1, paths);
    TransitionOracle oracle;
    TransitionOracle::Config cfg;
    cfg.max_leaves = budget;

    ClassStats cs;

    for (int i = 0; i < g; ++i) {
        BattleState state = gen.next();

        std::vector<ExecAction> actions;
        try {
            actions = legal_player_actions(state);
        } catch (const std::exception& e) {
            std::fprintf(stderr, "bench_oracle: legal_player_actions threw (klass=%s matchup=%d): %s\n",
                         klass_name(klass), i, e.what());
            std::exit(1);
        }

        for (const ExecAction& action : actions) {
            uint64_t leaf_count  = 0;
            double   prob_sum    = 0.0;

            OracleEmitFn emit = [&](ChildOutcome co) -> bool {
                ++leaf_count;
                prob_sum += co.prob;
                return true;
            };

            auto t0 = Clock::now();
            StepStats stats = oracle.step(state, action, emit, OrderingHint::Natural, cfg);
            double elapsed_ns = std::chrono::duration<double, std::nano>(Clock::now() - t0).count();

            cs.durations_ns.push_back(elapsed_ns);
            cs.total_leaves     += stats.leaves;
            cs.total_turn_execs += stats.turn_executions;
            cs.total_wall_sec   += elapsed_ns * 1e-9;
            cs.hist.record(stats.leaves);
            if (stats.budget_exceeded) ++cs.budget_exceeded;

            (void)prob_sum;  // counted as a side-effect sanity sink; not reported
        }
    }

    return cs;
}

}  // namespace

int main(int argc, char** argv) {
    uint64_t seed   = (uint64_t)std::atoll(get_arg(argc, argv, "--seed",   "1"));
    int      g      = (int)std::atol(get_arg(argc, argv, "--g",      "50"));
    uint64_t budget = (uint64_t)std::atoll(get_arg(argc, argv, "--budget", "1000000"));
    const char* klass_arg = get_arg(argc, argv, "--klass", "all");

    std::vector<MatchupGen::Class> klasses;
    if (std::strcmp(klass_arg, "all") == 0) {
        klasses = {MatchupGen::Class::Uniform,
                   MatchupGen::Class::BerryHolders,
                   MatchupGen::Class::SashSturdy};
    } else {
        klasses = {parse_single_klass(klass_arg)};
    }

    std::string repo_root = detect_repo_root();
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    std::printf("=== bench_oracle ===\n");
    std::printf("seed   : %llu\n", (unsigned long long)seed);
    std::printf("g      : %d matchups per class\n", g);
    std::printf("klass  : %s\n", klass_arg);
    std::printf("budget : %llu max_leaves\n", (unsigned long long)budget);
    std::printf("repo   : %s\n", repo_root.c_str());
    std::fflush(stdout);

    ClassStats overall;
    for (MatchupGen::Class k : klasses) {
        std::printf("\n[running class: %s ...]\n", klass_name(k));
        std::fflush(stdout);
        ClassStats cs = run_class(k, g, seed, budget, paths);
        print_class_report(klass_name(k), cs);
        accumulate(overall, cs);
    }

    if (klasses.size() > 1) {
        print_class_report("OVERALL", overall);
    }

    std::printf("\ndone.\n");
    return 0;
}
