// Standalone audit oracle executable. Modes:
//   selfcheck --seed S --klass K --n N [--shard k/of]: completeness + ordering + child sanity.
//   mc --seed S --klass K --n N --samples M: oracle support enumeration + random-mode MC check.
// Every failure prints seed/index/action/detail for regression fixture capture.
// Non-zero failures → non-zero exit code.
#include "solver/audit/audit_core.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// ---------------------------------------------------------------------------
// Argument parsing helpers
// ---------------------------------------------------------------------------

static const char* get_arg(int argc, char** argv, const char* flag, const char* default_val = nullptr) {
    for (int i = 1; i < argc - 1; ++i) {
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    }
    return default_val;
}

static bool has_arg(int argc, char** argv, const char* flag) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], flag) == 0) return true;
    }
    return false;
}

static long parse_long(const char* s, long default_val = 0) {
    return s ? std::atol(s) : default_val;
}

// Parse "k/of" shard argument, filling shard_k and shard_of.
static void parse_shard(const char* s, int& shard_k, int& shard_of) {
    if (!s) return;
    const char* slash = std::strchr(s, '/');
    if (!slash) {
        std::fprintf(stderr, "audit_oracle: bad --shard format (expected k/of): %s\n", s);
        std::exit(1);
    }
    shard_k  = (int)std::atol(s);
    shard_of = (int)std::atol(slash + 1);
}

// Derive repo root: walk up from __FILE__ until liveplay/ exists, else use env var or fallback.
// For a hermetic build this should be provided explicitly, but we try to auto-detect.
static std::string detect_repo_root() {
    // Try environment variable first.
    const char* env = std::getenv("NUZLOCKE_REPO_ROOT");
    if (env) return std::string(env);
    // Use compile-time definition if available (same as test build).
#ifdef NUZLOCKE_REPO_ROOT
    return NUZLOCKE_REPO_ROOT;
#else
    return ".";
#endif
}

// ---------------------------------------------------------------------------
// Mode: selfcheck
// ---------------------------------------------------------------------------

static int run_selfcheck(int argc, char** argv) {
    AuditSelfcheckConfig cfg;
    cfg.seed     = (uint64_t)parse_long(get_arg(argc, argv, "--seed",    "1"), 1);
    cfg.klass    = get_arg(argc, argv, "--klass", "uniform");
    cfg.n        = (int)parse_long(get_arg(argc, argv, "--n", "25"), 25);
    cfg.repo_root = detect_repo_root();

    if (has_arg(argc, argv, "--shard")) {
        parse_shard(get_arg(argc, argv, "--shard"), cfg.shard_k, cfg.shard_of);
    }

    std::printf("audit_oracle selfcheck  seed=%llu klass=%s n=%d shard=%d/%d\n",
                (unsigned long long)cfg.seed, cfg.klass.c_str(), cfg.n,
                cfg.shard_k, cfg.shard_of);
    std::fflush(stdout);

    AuditSelfcheckReport report = audit_selfcheck(cfg);

    // Print failure histogram (always, even when zero).
    std::printf("\n--- selfcheck results ---\n");
    std::printf("total_failures : %d\n", report.total_failures);
    std::printf("skipped_budget : %d  (budget exceeded; not failures)\n", report.skipped_budget);
    std::printf("MassError      : %d\n", report.reason_histogram.count(AuditFailReason::MassError)
                                          ? report.reason_histogram.at(AuditFailReason::MassError) : 0);
    std::printf("OrderingMismatch: %d\n", report.reason_histogram.count(AuditFailReason::OrderingMismatch)
                                          ? report.reason_histogram.at(AuditFailReason::OrderingMismatch) : 0);
    std::printf("ChildSanity    : %d\n", report.reason_histogram.count(AuditFailReason::ChildSanity)
                                          ? report.reason_histogram.at(AuditFailReason::ChildSanity) : 0);
    std::printf("OracleThrewException: %d\n", report.reason_histogram.count(AuditFailReason::OracleThrewException)
                                          ? report.reason_histogram.at(AuditFailReason::OracleThrewException) : 0);

    // Print each failure for regression capture.
    if (!report.failures.empty()) {
        std::printf("\n--- failures (seed/index/action/detail) ---\n");
        for (const auto& f : report.failures) {
            std::printf("FAIL seed=%llu matchup=%d action=[%s] mask=%d detail=%s\n",
                        (unsigned long long)f.seed,
                        f.matchup_index,
                        f.action_desc.c_str(),
                        f.reason_mask,
                        f.detail.c_str());
        }
    }

    if (report.total_failures == 0) {
        std::printf("\nPASS: zero failures\n");
        return 0;
    } else {
        std::printf("\nFAIL: %d failure(s)\n", report.total_failures);
        return 1;
    }
}

// ---------------------------------------------------------------------------
// Mode: mc
// ---------------------------------------------------------------------------

static int run_mc(int argc, char** argv) {
    AuditMcConfig cfg;
    cfg.seed    = (uint64_t)parse_long(get_arg(argc, argv, "--seed",    "1"), 1);
    cfg.klass   = get_arg(argc, argv, "--klass", "uniform");
    cfg.n       = (int)parse_long(get_arg(argc, argv, "--n", "3"), 3);
    cfg.samples = (int)parse_long(get_arg(argc, argv, "--samples", "2000"), 2000);
    cfg.repo_root = detect_repo_root();

    std::printf("audit_oracle mc  seed=%llu klass=%s n=%d samples=%d\n",
                (unsigned long long)cfg.seed, cfg.klass.c_str(), cfg.n, cfg.samples);
    std::fflush(stdout);

    AuditMcReport report = audit_mc(cfg);

    // HARD FAIL class printed FIRST, loudly.
    if (report.completeness_failures > 0) {
        std::printf("\n!!! COMPLETENESS HOLES (WORST FAILURE CLASS) !!!\n");
        std::printf("completeness_failures: %d\n", report.completeness_failures);
        for (const auto& h : report.holes) {
            std::printf("HOLE seed=%llu matchup=%d sample=%d action=[%s] detail=%s\n",
                        (unsigned long long)h.seed,
                        h.matchup_index,
                        h.sample_index,
                        h.action_desc.c_str(),
                        h.detail.c_str());
        }
    }

    // Statistical failures.
    std::printf("\n--- mc results ---\n");
    std::printf("completeness_failures: %d\n", report.completeness_failures);
    std::printf("stat_failures        : %d\n", report.stat_failures);
    std::printf("skipped_budget       : %d  (support truncated by leaf budget; not failures)\n",
                report.skipped_budget);

    if (report.stat_failures > 0) {
        std::printf("\n--- statistical failures ---\n");
        for (const auto& sf : report.stat_fails) {
            std::printf("STAT seed=%llu matchup=%d action=[%s] key=0x%llx detail=%s\n",
                        (unsigned long long)sf.seed,
                        sf.matchup_index,
                        sf.action_desc.c_str(),
                        (unsigned long long)sf.packed_key,
                        sf.detail.c_str());
        }
    }

    int total = report.completeness_failures + report.stat_failures;
    if (total == 0) {
        std::printf("\nPASS: zero failures\n");
        return 0;
    } else {
        std::printf("\nFAIL: %d completeness + %d stat failures\n",
                    report.completeness_failures, report.stat_failures);
        return 1;
    }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

static void print_usage(const char* prog) {
    std::fprintf(stderr,
        "Usage:\n"
        "  %s selfcheck --seed S --klass K --n N [--shard k/of]\n"
        "  %s mc        --seed S --klass K --n N --samples M\n"
        "\n"
        "klass: uniform | berry | sash\n"
        "Environment: NUZLOCKE_REPO_ROOT (or compile-time define) for data file paths.\n",
        prog, prog);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char* mode = argv[1];
    if (std::strcmp(mode, "selfcheck") == 0) return run_selfcheck(argc, argv);
    if (std::strcmp(mode, "mc")        == 0) return run_mc(argc, argv);

    std::fprintf(stderr, "audit_oracle: unknown mode '%s'\n", mode);
    print_usage(argv[0]);
    return 1;
}
