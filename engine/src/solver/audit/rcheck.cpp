// rcheck: bucket-pipeline referee audit vs the exact bsolver over a MatchupGen shard.
// Emits one JSONL record per matchup + a summary line to --out (or stdout). Exit 0 iff
// zero hard soundness failures. Thin CLI over rcheck_core; SCRIPTS/rcheck_aggregate.py
// merges shard outputs.
// Usage:
//   rcheck --seed S --klass {uniform|berry|sash} --n N --shard k/of --out PATH
//          [--exact-leaves N --exact-nodes N --pess-leaves N --pess-nodes N
//           --b-depth N --b-visits N]
#include "solver/audit/rcheck_core.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

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
    if (!slash) { std::fprintf(stderr, "rcheck: bad --shard format (k/of): %s\n", s); std::exit(1); }
    k  = (int)std::atol(s);
    of = (int)std::atol(slash + 1);
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

int main(int argc, char** argv) {
    RcheckConfig cfg;
    cfg.seed  = (uint64_t)parse_long(get_arg(argc, argv, "--seed", "1"), 1);
    cfg.n     = (int)parse_long(get_arg(argc, argv, "--n", "100"), 100);
    cfg.klass = get_arg(argc, argv, "--klass", "uniform");
    if (has_flag(argc, argv, "--shard"))
        parse_shard(get_arg(argc, argv, "--shard"), cfg.shard_k, cfg.shard_of);
    cfg.repo_root = detect_repo_root();

    cfg.exact_leaves = (uint64_t)parse_long(get_arg(argc, argv, "--exact-leaves", "5000"), 5000);
    cfg.exact_nodes  = (uint64_t)parse_long(get_arg(argc, argv, "--exact-nodes",  "1000"), 1000);
    cfg.pess_leaves  = (uint64_t)parse_long(get_arg(argc, argv, "--pess-leaves",  "5000"), 5000);
    cfg.pess_nodes   = (uint64_t)parse_long(get_arg(argc, argv, "--pess-nodes",   "1000"), 1000);
    cfg.b_depth      = (int)parse_long(get_arg(argc, argv, "--b-depth", "500"), 500);
    cfg.b_visits     = (uint64_t)parse_long(get_arg(argc, argv, "--b-visits", "1000000"), 1000000);

    const char* out_path = get_arg(argc, argv, "--out", nullptr);

    std::fprintf(stderr,
                 "rcheck  seed=%llu klass=%s n=%d shard=%d/%d out=%s\n",
                 (unsigned long long)cfg.seed, cfg.klass.c_str(), cfg.n,
                 cfg.shard_k, cfg.shard_of, out_path ? out_path : "(stdout)");
    std::fflush(stderr);

    std::ofstream fout;
    if (out_path) {
        fout.open(out_path);
        if (!fout) { std::fprintf(stderr, "rcheck: cannot open --out %s\n", out_path); return 2; }
    }
    std::ostream& out = out_path ? fout : std::cout;

    RcheckReport report = rcheck_run(cfg, out);

    std::fprintf(stderr, "rcheck done: n=%d hard_fails=%d\n", report.n, report.hard_fails);
    if (report.hard_fails == 0) {
        std::fprintf(stderr, "PASS: zero soundness failures\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d soundness failure(s)\n", report.hard_fails);
    return 1;
}
