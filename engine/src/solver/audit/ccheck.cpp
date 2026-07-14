// ccheck: pessimal/coarse-vs-exact theorem audit.
// THEOREM CHECK (hard fail, printed FIRST): every pessimal/coarse LOSS must be exact-LOSS.
//   A cheap-tier LOSS that exact calls WIN is a soundness violation — the subset-support
//   theorem guarantees this cannot happen; if it does, there is a bug in the collapse logic.
// COST REPORT (not a failure): cheap-tier WIN where exact is LOSS = false-positive.
//   Expected behavior per user confirmation: exact-LOSS with pessimal-WIN is acceptable.
// Also reports µs/matchup per tier and decided/indeterminate counts.
// Usage:
//   ccheck --seed S --klass K --n N [--shard k/of]
#include "solver/bsolver.h"
#include "solver/matchup_gen.h"
#include "solver/question.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Argument parsing helpers
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
    if (!slash) { std::fprintf(stderr, "ccheck: bad --shard format (k/of): %s\n", s); std::exit(1); }
    k  = (int)std::atol(s);
    of = (int)std::atol(slash + 1);
}

static MatchupGen::Class parse_klass(const char* s) {
    if (!s || std::strcmp(s, "uniform") == 0) return MatchupGen::Class::Uniform;
    if (std::strcmp(s, "berry") == 0) return MatchupGen::Class::BerryHolders;
    if (std::strcmp(s, "sash")  == 0) return MatchupGen::Class::SashSturdy;
    std::fprintf(stderr, "ccheck: unknown klass '%s' (use uniform/berry/sash)\n", s);
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

static const char* verdict_str(BVerdict v) {
    switch (v) {
    case BVerdict::WIN:           return "WIN";
    case BVerdict::LOSS:          return "LOSS";
    case BVerdict::INDETERMINATE: return "INDET";
    }
    return "?";
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    uint64_t seed = (uint64_t)parse_long(get_arg(argc, argv, "--seed",  "1"), 1);
    int      n    = (int)parse_long(get_arg(argc, argv, "--n",    "25"), 25);
    int shard_k = 0, shard_of = 1;
    if (has_flag(argc, argv, "--shard"))
        parse_shard(get_arg(argc, argv, "--shard"), shard_k, shard_of);

    MatchupGen::Class klass = parse_klass(get_arg(argc, argv, "--klass", "uniform"));

    std::string repo_root = detect_repo_root();
    MatchupGen::Paths paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };

    std::printf("ccheck  seed=%llu klass=%s n=%d shard=%d/%d\n",
                (unsigned long long)seed,
                get_arg(argc, argv, "--klass", "uniform"),
                n, shard_k, shard_of);
    std::fflush(stdout);

    MatchupGen gen(seed, klass, shard_k, shard_of, paths);

    BsolverConfig cfg_exact, cfg_pess, cfg_coarse;
    cfg_exact.mode  = BMode::Exact;
    cfg_pess.mode   = BMode::Pessimal;
    cfg_coarse.mode = BMode::Coarse;
    // Budgets sized for acceptance grid. Per-matchup cost is 3 bsolver calls
    // (exact, pessimal, coarse); must complete in under a few seconds per matchup.
    // With real matchups from MatchupGen, most will be INDETERMINATE at moderate budgets.
    // The few that decide within budget verify the theorem. INDETERMINATE skips are counted.
    // depth_cap uses BsolverConfig default (500); node/leaf budgets gate INDETERMINATE earlier.
    uint64_t leaves = 5'000;
    uint64_t nodes  = 1'000;
    // depth_cap uses BsolverConfig default (500): safe now that bsolver runs on a dedicated
    // 256 MB pthread stack. The previous depth=20 workaround for stack overflow is removed.
    cfg_exact.oracle_max_leaves  = leaves; cfg_exact.node_cap  = nodes;
    cfg_pess.oracle_max_leaves   = leaves; cfg_pess.node_cap   = nodes;
    cfg_coarse.oracle_max_leaves = leaves; cfg_coarse.node_cap = nodes;

    Question q{};

    // Per-tier accumulators.
    int pess_soundness_failures  = 0;
    int coarse_soundness_failures = 0;
    int pess_fp = 0, coarse_fp = 0;
    int decided_exact = 0, indet_exact = 0;
    int decided_pess  = 0, indet_pess  = 0;
    int decided_coarse = 0, indet_coarse = 0;
    double exact_us = 0, pess_us = 0, coarse_us = 0;

    for (int mi = 0; mi < n; ++mi) {
        BattleState state = gen.next();

        auto t0 = std::chrono::steady_clock::now();
        BsolverResult r_exact  = bsolver_certify(state, q, cfg_exact);
        auto t1 = std::chrono::steady_clock::now();
        BsolverResult r_pess   = bsolver_certify(state, q, cfg_pess);
        auto t2 = std::chrono::steady_clock::now();
        BsolverResult r_coarse = bsolver_certify(state, q, cfg_coarse);
        auto t3 = std::chrono::steady_clock::now();

        exact_us  += std::chrono::duration<double, std::micro>(t1 - t0).count();
        pess_us   += std::chrono::duration<double, std::micro>(t2 - t1).count();
        coarse_us += std::chrono::duration<double, std::micro>(t3 - t2).count();

        if (r_exact.verdict  == BVerdict::INDETERMINATE) ++indet_exact;  else ++decided_exact;
        if (r_pess.verdict   == BVerdict::INDETERMINATE) ++indet_pess;   else ++decided_pess;
        if (r_coarse.verdict == BVerdict::INDETERMINATE) ++indet_coarse; else ++decided_coarse;

        // Skip if exact is INDETERMINATE (can't check theorem).
        if (r_exact.verdict == BVerdict::INDETERMINATE) continue;

        // THEOREM CHECK: cheap LOSS must be exact LOSS.
        if (r_pess.verdict == BVerdict::LOSS && r_exact.verdict == BVerdict::WIN) {
            ++pess_soundness_failures;
            std::printf("SOUNDNESS_FAIL[pessimal] seed=%llu index=%d exact=WIN pess=LOSS\n",
                        (unsigned long long)seed, mi);
        }
        if (r_coarse.verdict == BVerdict::LOSS && r_exact.verdict == BVerdict::WIN) {
            ++coarse_soundness_failures;
            std::printf("SOUNDNESS_FAIL[coarse] seed=%llu index=%d exact=WIN coarse=LOSS\n",
                        (unsigned long long)seed, mi);
        }

        // Count false positives (cheap WIN + exact LOSS) — allowed, just reported.
        if (r_pess.verdict   == BVerdict::WIN && r_exact.verdict == BVerdict::LOSS) ++pess_fp;
        if (r_coarse.verdict == BVerdict::WIN && r_exact.verdict == BVerdict::LOSS) ++coarse_fp;
    }

    int total_soundness = pess_soundness_failures + coarse_soundness_failures;

    // Soundness failures printed FIRST if any.
    if (total_soundness > 0) {
        std::printf("\n!!! SOUNDNESS FAILURES (subset-support theorem violated) !!!\n");
        std::printf("pessimal_soundness_failures : %d\n", pess_soundness_failures);
        std::printf("coarse_soundness_failures   : %d\n", coarse_soundness_failures);
    }

    std::printf("\n--- ccheck results ---\n");
    std::printf("total                       : %d\n", n);
    std::printf("\n");
    std::printf("exact   decided/indet        : %d/%d\n", decided_exact, indet_exact);
    std::printf("pessimal decided/indet        : %d/%d\n", decided_pess, indet_pess);
    std::printf("coarse  decided/indet         : %d/%d\n", decided_coarse, indet_coarse);
    std::printf("\n");
    std::printf("pess_soundness_failures      : %d  (MUST be 0)\n", pess_soundness_failures);
    std::printf("coarse_soundness_failures    : %d  (MUST be 0)\n", coarse_soundness_failures);
    std::printf("\n");
    // FP rate: among decided-exact matchups, how many does the cheap tier call WIN when exact calls LOSS?
    if (decided_exact > 0) {
        std::printf("pess_false_positive_rate     : %d/%d = %.1f%%  (allowed)\n",
                    pess_fp, decided_exact, 100.0 * pess_fp / decided_exact);
        std::printf("coarse_false_positive_rate   : %d/%d = %.1f%%  (allowed)\n",
                    coarse_fp, decided_exact, 100.0 * coarse_fp / decided_exact);
    }
    std::printf("\n");
    if (n > 0) {
        std::printf("us_per_matchup exact         : %.1f\n", exact_us / n);
        std::printf("us_per_matchup pessimal      : %.1f\n", pess_us / n);
        std::printf("us_per_matchup coarse        : %.1f\n", coarse_us / n);
    }

    if (total_soundness == 0) {
        std::printf("\nPASS: zero soundness failures\n");
        return 0;
    } else {
        std::printf("\nFAIL: %d soundness failure(s)\n", total_soundness);
        return 1;
    }
}
