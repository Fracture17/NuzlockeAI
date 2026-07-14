// analytic_trace: single-matchup analytic trace printer.
// Prints both mons, speed comparison, damage tables, analytic per-turn lines,
// verdict/tag/scope_mask, and bsolver verdicts (pessimal + exact).
// With --action SLOT: enumerates oracle children and marks losers.
// Usage:
//   analytic_trace --seed S --klass K --index I [--action SLOT]
#include "solver/audit/audit_analytic_core.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

static const char* get_arg(int argc, char** argv, const char* flag, const char* def = nullptr) {
    for (int i = 1; i < argc - 1; ++i)
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    return def;
}

static long parse_long(const char* s, long def) { return s ? std::atol(s) : def; }

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
    if (argc < 2) {
        std::fprintf(stderr,
            "Usage: analytic_trace --seed S --klass K --index I [--action SLOT]\n");
        return 1;
    }

    AnalyticTraceConfig cfg;
    cfg.seed        = (uint64_t)parse_long(get_arg(argc, argv, "--seed",  "1"), 1);
    cfg.klass       = get_arg(argc, argv, "--klass",  "uniform");
    cfg.index       = (int)parse_long(get_arg(argc, argv, "--index", "0"), 0);
    cfg.action_slot = (int)parse_long(get_arg(argc, argv, "--action", nullptr), -1);
    cfg.repo_root   = detect_repo_root();

    AnalyticTraceOutput out = analytic_trace_run(cfg);
    std::printf("%s", out.text.c_str());
    return 0;
}
