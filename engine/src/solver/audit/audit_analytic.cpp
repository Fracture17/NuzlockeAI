// audit_analytic: tiered analytic-certifier audit harness.
// Verifies analytic WIN/LOSS against pessimal and (when needed) exact bsolver.
// Usage:
//   audit_analytic --seed S --klass K --n N --mode {all|collect|fast}
//                  [--shard k/of] [--mask-scan M] [--combo-top N]
#include "solver/audit/audit_analytic_core.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

// ---------------------------------------------------------------------------
// Argument parsing
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
    if (!slash) {
        std::fprintf(stderr, "audit_analytic: bad --shard format (k/of): %s\n", s);
        std::exit(1);
    }
    k  = (int)std::atol(s);
    of = (int)std::atol(slash + 1);
}

static AnalyticAuditMode parse_mode(const char* s) {
    if (!s || std::strcmp(s, "all") == 0)     return AnalyticAuditMode::All;
    if (std::strcmp(s, "collect") == 0) return AnalyticAuditMode::Collect;
    if (std::strcmp(s, "fast") == 0)    return AnalyticAuditMode::Fast;
    std::fprintf(stderr, "audit_analytic: unknown --mode '%s' (use all/collect/fast)\n", s);
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
// Print helpers
// ---------------------------------------------------------------------------

static const char* atag_name(int tag) {
    switch (tag) {
    case 0: return "AT_OK";
    case 1: return "AT_SCOPE";
    case 2: return "AT_MASK";
    case 3: return "AT_THRESH";
    case 4: return "AT_NOT_TIGHT";
    case 5: return "AT_STALL";
    case 6: return "AT_CAP";
    default: return "AT_?";
    }
}

static const char* scope_bit_name(int bit) {
    switch (bit) {
    case 0:  return "MULTI_HIT";
    case 1:  return "ACCURACY_LT100";
    case 2:  return "SECONDARY";
    case 3:  return "RECOIL";
    case 4:  return "DRAIN";
    case 5:  return "BINDING";
    case 6:  return "CHARGE_TURN";
    case 7:  return "PRIORITY";
    case 8:  return "HP_DEP_BP";
    case 9:  return "WEATHER_SCREEN";
    case 10: return "ENTRY_DIRTY";
    case 11: return "ITEM_NOT_ALLOWED";
    case 12: return "OPP_NO_DAMAGE";
    case 13: return "NONDEFAULT_QUESTION";
    case 14: return "RESIDUAL_UNKNOWN";
    default: return "BIT_?";
    }
}

static void print_report(const AnalyticAuditReport& r, int n,
                          const std::string& klass, uint64_t seed,
                          AnalyticAuditMode mode, int combo_top) {
    // Soundness failures FIRST.
    if (r.soundness_failures > 0) {
        std::printf("\n!!! SOUNDNESS FAILURES !!!\n");
        for (const auto& f : r.failures) {
            if (f.loss_vs_exact_win)
                std::printf("SOUNDNESS_FAIL[LOSS-vs-exact-WIN] "
                            "seed=%llu klass=%s index=%d analytic=%s exact=%s "
                            "tag=%s scope_mask=0x%x tight=%d\n",
                            (unsigned long long)f.seed, f.klass.c_str(), f.index,
                            f.av_verdict.c_str(), f.bv_verdict.c_str(),
                            atag_name(f.tag), f.scope_mask, (int)f.tight);
        }
        for (const auto& f : r.failures) {
            if (!f.loss_vs_exact_win)
                std::printf("SOUNDNESS_FAIL seed=%llu klass=%s index=%d "
                            "analytic=%s bsolver=%s tag=%s scope_mask=0x%x tight=%d\n",
                            (unsigned long long)f.seed, f.klass.c_str(), f.index,
                            f.av_verdict.c_str(), f.bv_verdict.c_str(),
                            atag_name(f.tag), f.scope_mask, (int)f.tight);
        }
    }

    std::printf("\n--- audit_analytic results ---\n");
    std::printf("seed=%-10llu klass=%-10s n=%-5d mode=%s\n",
                (unsigned long long)seed, klass.c_str(), n,
                mode == AnalyticAuditMode::All ? "all" :
                mode == AnalyticAuditMode::Collect ? "collect" : "fast");
    if (r.collect_cap_hit)
        std::printf("WARNING: collect mode hit scan cap before reaching N decided\n");
    std::printf("\n");
    std::printf("scanned                    : %d\n", r.scanned);
    std::printf("decided                    : %d (%.1f%% of scanned)\n",
                r.decided, r.scanned > 0 ? 100.0 * r.decided / r.scanned : 0.0);
    std::printf("  analytic_WIN             : %d\n", r.n_analytic_win);
    std::printf("  analytic_LOSS            : %d\n", r.n_analytic_loss);
    std::printf("unknown                    : %d\n", r.n_unknown);
    std::printf("\n");
    if (mode != AnalyticAuditMode::Fast) {
        std::printf("pess_confirmed             : %d (cheap LOSS+LOSS, no exact needed)\n",
                    r.pess_confirmed);
        std::printf("exact_adjudicated          : %d\n", r.exact_adjudicated);
        std::printf("  exact_wins               : %d (%.1f%% of adjudicated)\n",
                    r.exact_wins,
                    r.exact_adjudicated > 0 ? 100.0 * r.exact_wins / r.exact_adjudicated : 0.0);
        std::printf("exact_skipped_indet        : %d\n", r.exact_skipped);
        std::printf("soundness_failures         : %d  (MUST be 0)\n", r.soundness_failures);
        std::printf("\n");
    }

    // UNKNOWN tag histogram.
    if (!r.unknown_tag_histogram.empty()) {
        std::printf("UNKNOWN tag histogram:\n");
        // Print in tag order.
        for (int tag = 0; tag <= 6; ++tag) {
            auto it = r.unknown_tag_histogram.find(tag);
            if (it != r.unknown_tag_histogram.end())
                std::printf("  %-15s : %d\n", atag_name(tag), it->second);
        }
        std::printf("\n");
    }

    // Scope-reason bitmask histogram.
    if (!r.scope_bit_histogram.empty()) {
        std::printf("Scope-reason bit histogram (bit → count, co-occurrence counted):\n");
        for (int b = 0; b < 15; ++b) {
            auto it = r.scope_bit_histogram.find(b);
            if (it != r.scope_bit_histogram.end())
                std::printf("  bit%-2d %-20s : %d\n", b, scope_bit_name(b), it->second);
        }
        std::printf("\n");
    }

    // Exact scope-mask combinations (wave planning: a wave clearing bit-set W
    // fully unlocks exactly the matchups whose mask ⊆ W). Top combo_top by count
    // (--combo-top N; SCRIPTS/wave_unlock.py consumes the full list).
    if (!r.mask_combo_histogram.empty()) {
        std::vector<std::pair<uint32_t, int>> combos(
            r.mask_combo_histogram.begin(), r.mask_combo_histogram.end());
        std::sort(combos.begin(), combos.end(),
                  [](const auto& a, const auto& b) {
                      return a.second != b.second ? a.second > b.second
                                                  : a.first < b.first;
                  });
        std::printf("Scope-mask combination histogram (top %d of %d combos):\n",
                    (int)std::min<size_t>((size_t)combo_top, combos.size()),
                    (int)combos.size());
        int shown = 0;
        for (const auto& [mask, count] : combos) {
            if (shown++ >= combo_top) break;
            std::printf("  0x%04x : %-6d [", mask, count);
            bool first = true;
            for (int b = 0; b < 15; ++b) {
                if (mask & (1u << b)) {
                    std::printf("%s%s", first ? "" : "|", scope_bit_name(b));
                    first = false;
                }
            }
            std::printf("]\n");
        }
        std::printf("\n");
    }

    // Timing.
    if (r.scanned > 0) {
        std::printf("analytic us/matchup        : %.1f\n",
                    r.analytic_us_total / r.scanned);
    }
    if (mode != AnalyticAuditMode::Fast) {
        int verified = r.pess_confirmed + r.exact_adjudicated + r.exact_skipped;
        if (verified > 0) {
            std::printf("pessimal us/verified       : %.1f\n",
                        r.pessimal_us_total / verified);
            if (r.exact_adjudicated + r.exact_skipped > 0)
                std::printf("exact    us/adjudicated    : %.1f\n",
                            r.exact_us_total / (r.exact_adjudicated + r.exact_skipped));
        }
    }
}

static void print_mask_report(const MaskScanReport& r) {
    std::printf("\n--- mask-scan results ---\n");
    std::printf("matchups_scanned           : %d\n", r.matchups_scanned);
    std::printf("total_hp_points_swept      : %d\n", r.total_hp_points);
    std::printf("multi_crossing_actions     : %d\n", r.multi_crossing_actions);
    std::printf("\nPer-slot stats:\n");
    for (const auto& ss : r.slot_stats) {
        std::printf("  slot %d: total_crossings=%d  multi_crossing_matchups=%d\n",
                    ss.move_slot, ss.total_crossings, ss.multi_crossing_matchups);
    }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr,
            "Usage: audit_analytic --seed S --klass K --n N --mode {all|collect|fast}"
            " [--shard k/of] [--mask-scan M]\n");
        return 1;
    }

    uint64_t seed = (uint64_t)parse_long(get_arg(argc, argv, "--seed",  "1"), 1);
    int      n    = (int)parse_long(get_arg(argc, argv, "--n",    "25"), 25);
    int shard_k = 0, shard_of = 1;
    if (has_flag(argc, argv, "--shard"))
        parse_shard(get_arg(argc, argv, "--shard"), shard_k, shard_of);

    const char* klass_str = get_arg(argc, argv, "--klass", "uniform");
    AnalyticAuditMode mode = parse_mode(get_arg(argc, argv, "--mode", "all"));

    std::string repo_root = detect_repo_root();

    std::printf("audit_analytic  seed=%llu klass=%s n=%d mode=%s shard=%d/%d\n",
                (unsigned long long)seed, klass_str, n,
                mode == AnalyticAuditMode::All ? "all" :
                mode == AnalyticAuditMode::Collect ? "collect" : "fast",
                shard_k, shard_of);
    std::fflush(stdout);

    // --mask-scan mode (independent of the main audit).
    int mask_n = (int)parse_long(get_arg(argc, argv, "--mask-scan", nullptr), 0);
    if (mask_n > 0) {
        MaskScanConfig mcfg;
        mcfg.seed      = seed;
        mcfg.klass     = klass_str;
        mcfg.n         = mask_n;
        mcfg.shard_k   = shard_k;
        mcfg.shard_of  = shard_of;
        mcfg.repo_root = repo_root;

        MaskScanReport mr = analytic_mask_scan(mcfg);
        print_mask_report(mr);
        // mask-scan is telemetry only; exit 0 regardless.
        return 0;
    }

    AnalyticAuditConfig cfg;
    cfg.seed             = seed;
    cfg.klass            = klass_str;
    cfg.n                = n;
    cfg.mode             = mode;
    cfg.shard_k          = shard_k;
    cfg.shard_of         = shard_of;
    cfg.repo_root        = repo_root;
    cfg.oracle_max_leaves = 5'000;
    cfg.node_cap          = 1'000;

    int combo_top = (int)parse_long(get_arg(argc, argv, "--combo-top", "20"), 20);

    AnalyticAuditReport report = analytic_audit_run(cfg);
    print_report(report, n, klass_str, seed, mode, combo_top);

    if (report.soundness_failures == 0) {
        std::printf("\nPASS: zero soundness failures\n");
        return 0;
    } else {
        std::printf("\nFAIL: %d soundness failure(s)\n", report.soundness_failures);
        return 1;
    }
}
