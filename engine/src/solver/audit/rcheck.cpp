// rcheck: bucket-pipeline referee audit vs the exact bsolver over a MatchupGen shard.
// Emits one JSONL record per matchup + a summary line to --out (or stdout). Exit 0 iff
// zero hard soundness failures. Thin CLI over rcheck_core; SCRIPTS/rcheck_aggregate.py
// merges shard outputs.
// Usage:
//   rcheck --seed S --klass {uniform|berry|sash} --n N --shard k/of --out PATH
//          [--exact-leaves N --exact-nodes N --pess-leaves N --pess-nodes N
//           --b-depth N --b-visits N --no-cache --pp-canon]
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

// Every value-taking flag (consumes the following argv token).
static const char* const VALUE_FLAGS[] = {
    "--seed", "--n", "--klass", "--shard", "--out",
    "--exact-leaves", "--exact-nodes", "--pess-leaves", "--pess-nodes",
    "--b-depth", "--b-visits",
};
// Every boolean flag (no following token).
static const char* const BOOL_FLAGS[] = {"--no-cache", "--pp-canon", "--help", "-h"};

static bool in_list(const char* s, const char* const* list, int n) {
    for (int i = 0; i < n; ++i)
        if (std::strcmp(s, list[i]) == 0) return true;
    return false;
}

static void print_usage(std::FILE* f) {
    std::fprintf(f,
        "usage: rcheck [flags]\n"
        "  --seed S              RNG seed (default 1)\n"
        "  --klass K             matchup class: uniform|berry|sash (default uniform)\n"
        "  --n N                 matchups per shard (default 100)\n"
        "  --shard k/of          shard index / count (default 0/1)\n"
        "  --out PATH            JSONL output path (default stdout)\n"
        "  --exact-leaves N      exact referee oracle leaf budget (default 5000)\n"
        "  --exact-nodes N       exact referee node cap (default 1000)\n"
        "  --pess-leaves N       pessimal oracle leaf budget (default 5000)\n"
        "  --pess-nodes N        pessimal node cap (default 1000)\n"
        "  --b-depth N           B-solver depth cap (default 500)\n"
        "  --b-visits N          B-solver visit cap (default 1000000)\n"
        "  --no-cache            disable B-solver edge cache + verdict memo\n"
        "  --pp-canon            enable PP canonicalization + certificate PP audit\n"
        "  --help, -h            print this help and exit 0\n");
}

// Validate every argv token. --help/-h → print usage to stdout, exit 0. Any unrecognized
// argument → print usage to stderr, exit nonzero. Value flags consume their next token.
// (Fixes the silent-ignore bug where a stray flag started a default run.)
static void validate_args(int argc, char** argv) {
    const int nval  = (int)(sizeof(VALUE_FLAGS) / sizeof(VALUE_FLAGS[0]));
    const int nbool = (int)(sizeof(BOOL_FLAGS) / sizeof(BOOL_FLAGS[0]));
    for (int i = 1; i < argc; ++i) {
        const char* a = argv[i];
        if (std::strcmp(a, "--help") == 0 || std::strcmp(a, "-h") == 0) {
            print_usage(stdout);
            std::exit(0);
        }
        if (in_list(a, VALUE_FLAGS, nval)) { ++i; continue; }  // skip its value
        if (in_list(a, BOOL_FLAGS, nbool)) continue;
        std::fprintf(stderr, "rcheck: unrecognized argument '%s'\n", a);
        print_usage(stderr);
        std::exit(2);
    }
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
    validate_args(argc, argv);

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
    cfg.enable_cache    = !has_flag(argc, argv, "--no-cache");
    cfg.enable_pp_canon = has_flag(argc, argv, "--pp-canon");

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
