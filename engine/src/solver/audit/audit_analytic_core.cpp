// Analytic-certifier audit and trace implementation.
// analytic_audit_run: tiered (analytic → pessimal → exact) verification loop.
// analytic_trace_run: single-matchup printout with damage tables and per-turn lines.
// analytic_mask_scan: sweeps opp HP to count AI support-set crossings.
#include "solver/audit/audit_analytic_core.h"

#include "ai_analytic.h"      // cpp_compute_action_probabilities
#include "ai_shared.h"        // active_mon
#include "core_leaf.h"        // cpp_effective_speed
#include "solver/action_space.h"
#include "solver/analytic/analytic.h"
#include "solver/bsolver.h"
#include "solver/engine_queries.h"
#include "solver/matchup_gen.h"
#include "solver/oracle_types.h"
#include "solver/question.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "state.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <functional>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

static MatchupGen::Class parse_klass_core(const std::string& k) {
    if (k == "uniform") return MatchupGen::Class::Uniform;
    if (k == "berry")   return MatchupGen::Class::BerryHolders;
    if (k == "sash")    return MatchupGen::Class::SashSturdy;
    throw std::invalid_argument("unknown klass: " + k + " (use uniform/berry/sash)");
}

static const char* averdict_str(AVerdict v) {
    switch (v) {
    case AVerdict::WIN:     return "WIN";
    case AVerdict::LOSS:    return "LOSS";
    case AVerdict::UNKNOWN: return "UNKNOWN";
    }
    return "?";
}

static const char* bverdict_str(BVerdict v) {
    switch (v) {
    case BVerdict::WIN:           return "WIN";
    case BVerdict::LOSS:          return "LOSS";
    case BVerdict::INDETERMINATE: return "INDET";
    }
    return "?";
}

static const char* atag_str(int tag) {
    switch (tag) {
    case AT_OK:        return "AT_OK";
    case AT_SCOPE:     return "AT_SCOPE";
    case AT_MASK:      return "AT_MASK";
    case AT_THRESH:    return "AT_THRESH";
    case AT_NOT_TIGHT: return "AT_NOT_TIGHT";
    case AT_STALL:     return "AT_STALL";
    case AT_CAP:       return "AT_CAP";
    default:           return "AT_?";
    }
}

// Names for the 15 SCOPE_* bits.
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

// Decode scope_mask bits into a human-readable string.
static std::string decode_scope_mask(uint32_t mask) {
    std::string s;
    for (int b = 0; b < 15; ++b) {
        if (mask & (1u << b)) {
            if (!s.empty()) s += "|";
            s += scope_bit_name(b);
        }
    }
    return s.empty() ? "(none)" : s;
}

// Build MatchupGen::Paths from a repo_root string.
static MatchupGen::Paths make_paths(const std::string& repo_root) {
    return MatchupGen::Paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };
}

// Advance gen forward to reach a specific global index (no shard filter).
// gen is constructed with shard 0/1 so every index is yielded.
static BattleState advance_to_index(MatchupGen& gen, int target) {
    BattleState s{};
    for (int i = 0; i <= target; ++i) s = gen.next();
    return s;
}

// Build a BsolverConfig for the audit loop.
static BsolverConfig make_bsolver_cfg(BMode mode,
                                       uint64_t oracle_max_leaves,
                                       uint64_t node_cap) {
    BsolverConfig cfg;
    cfg.mode              = mode;
    cfg.oracle_max_leaves = oracle_max_leaves;
    cfg.node_cap          = node_cap;
    return cfg;
}

// ---------------------------------------------------------------------------
// analytic_audit_run
// ---------------------------------------------------------------------------

AnalyticAuditReport analytic_audit_run(const AnalyticAuditConfig& cfg) {
    AnalyticAuditReport report;

    // Fail loud: injected list and generator path are mutually exclusive.
    if (!cfg.injected.empty() && !cfg.repo_root.empty())
        throw std::invalid_argument(
            "analytic_audit_run: injected list and repo_root both set — "
            "these are mutually exclusive; clear repo_root when using injected matchups");

    // Select certifier: use injection seam when provided, real function otherwise.
    auto certify = cfg.certifier
        ? cfg.certifier
        : CertifierFn(analytic_certify);

    // Two execution paths: injected list or MatchupGen.
    // When using the generator, construct it here; otherwise it is never touched.
    std::unique_ptr<MatchupGen> gen_ptr;
    if (cfg.injected.empty()) {
        gen_ptr = std::make_unique<MatchupGen>(
            cfg.seed, parse_klass_core(cfg.klass),
            cfg.shard_k, cfg.shard_of, make_paths(cfg.repo_root));
    }

    BsolverConfig pess_cfg = make_bsolver_cfg(BMode::Pessimal,
                                               cfg.oracle_max_leaves, cfg.node_cap);
    BsolverConfig exact_cfg = make_bsolver_cfg(BMode::Exact,
                                                cfg.oracle_max_leaves, cfg.node_cap);
    Question q{};

    // Injected mode: n is the injected list size; no collect/scan cap logic.
    bool use_injected = !cfg.injected.empty();
    int  injected_n   = use_injected ? (int)cfg.injected.size() : 0;

    // Termination for generator path: all/fast → scan exactly n; collect → scan until n decided (capped).
    bool collect = !use_injected && (cfg.mode == AnalyticAuditMode::Collect);
    bool fast    = !use_injected && (cfg.mode == AnalyticAuditMode::Fast);
    int scan_limit = collect ? cfg.n * cfg.collect_scan_cap_mult : cfg.n;
    int decided_target = collect ? cfg.n : -1;

    std::vector<AnalyticSoundnessFailure> loss_vs_win_failures;  // print first
    std::vector<AnalyticSoundnessFailure> other_failures;

    for (int mi = 0; ; ++mi) {
        // Termination checks.
        if (use_injected) {
            if (mi >= injected_n) break;
        } else if (collect) {
            if (report.decided >= decided_target) break;
            if (mi >= scan_limit) { report.collect_cap_hit = true; break; }
        } else {
            if (mi >= cfg.n) break;
        }

        BattleState state = use_injected ? cfg.injected[mi] : gen_ptr->next();
        ++report.scanned;

        // --- Analytic (or injected certifier) ---
        auto t0 = std::chrono::steady_clock::now();
        AnalyticResult ar = certify(state, q);
        auto t1 = std::chrono::steady_clock::now();
        report.analytic_us_total +=
            std::chrono::duration<double, std::micro>(t1 - t0).count();

        bool decided = (ar.verdict != AVerdict::UNKNOWN);

        if (!decided) {
            ++report.n_unknown;
            report.unknown_tag_histogram[ar.tag]++;
            // Accumulate scope bits even for unknown.
            for (int b = 0; b < 15; ++b) {
                if (ar.scope_mask & (1u << b))
                    report.scope_bit_histogram[b]++;
            }
            // Exact mask combination (wave-planning input; only nonzero masks carry info).
            if (ar.scope_mask != 0)
                report.mask_combo_histogram[ar.scope_mask]++;
        } else {
            ++report.decided;
            if (ar.verdict == AVerdict::WIN)  ++report.n_analytic_win;
            if (ar.verdict == AVerdict::LOSS) ++report.n_analytic_loss;
            // Accumulate scope bits for decided too (scope_mask may have context bits).
            for (int b = 0; b < 15; ++b) {
                if (ar.scope_mask & (1u << b))
                    report.scope_bit_histogram[b]++;
            }
        }

        // Fast mode: analytic only.
        if (fast || !decided) continue;

        // --- Pessimal ---
        auto t2 = std::chrono::steady_clock::now();
        BsolverResult pr = bsolver_certify(state, q, pess_cfg);
        auto t3 = std::chrono::steady_clock::now();
        report.pessimal_us_total +=
            std::chrono::duration<double, std::micro>(t3 - t2).count();

        // Soundness: analytic WIN + pessimal LOSS → immediate failure (conclusive theorem).
        if (ar.verdict == AVerdict::WIN && pr.verdict == BVerdict::LOSS) {
            AnalyticSoundnessFailure f;
            f.seed       = cfg.seed;
            f.klass      = cfg.klass;
            f.index      = mi;
            f.av_verdict = "WIN";
            f.bv_verdict = "LOSS(pessimal)";
            f.tag        = ar.tag;
            f.scope_mask = ar.scope_mask;
            f.tight      = ar.tight;
            f.loss_vs_exact_win = false;
            other_failures.push_back(f);
            ++report.soundness_failures;
            continue;
        }

        // Cheap-confirmed: analytic LOSS + pessimal LOSS → no exact needed.
        if (ar.verdict == AVerdict::LOSS && pr.verdict == BVerdict::LOSS) {
            ++report.pess_confirmed;
            continue;
        }

        // All other decided combinations: adjudicate with exact bsolver.
        // (analytic WIN + pessimal WIN/INDET, analytic LOSS + pessimal WIN/INDET)
        auto t4 = std::chrono::steady_clock::now();
        BsolverResult er = bsolver_certify(state, q, exact_cfg);
        auto t5 = std::chrono::steady_clock::now();
        report.exact_us_total +=
            std::chrono::duration<double, std::micro>(t5 - t4).count();

        if (er.verdict == BVerdict::INDETERMINATE) {
            ++report.exact_skipped;
            continue;
        }

        ++report.exact_adjudicated;
        if (er.verdict == BVerdict::WIN) ++report.exact_wins;

        // Soundness check: analytic verdict must match exact.
        bool av_win = (ar.verdict == AVerdict::WIN);
        bool ev_win = (er.verdict == BVerdict::WIN);
        if (av_win != ev_win) {
            AnalyticSoundnessFailure f;
            f.seed       = cfg.seed;
            f.klass      = cfg.klass;
            f.index      = mi;
            f.av_verdict = averdict_str(ar.verdict);
            f.bv_verdict = bverdict_str(er.verdict);
            f.tag        = ar.tag;
            f.scope_mask = ar.scope_mask;
            f.tight      = ar.tight;
            // LOSS-vs-exact-WIN: print first.
            f.loss_vs_exact_win = (!av_win && ev_win);
            if (f.loss_vs_exact_win)
                loss_vs_win_failures.push_back(f);
            else
                other_failures.push_back(f);
            ++report.soundness_failures;
        }
    }

    // LOSS-vs-exact-WIN failures go first, as per spec.
    for (auto& f : loss_vs_win_failures)  report.failures.push_back(f);
    for (auto& f : other_failures)         report.failures.push_back(f);

    return report;
}

// ---------------------------------------------------------------------------
// analytic_mask_scan
// ---------------------------------------------------------------------------

// Query AI support set (move slots with p>0) at a given opp HP.
static std::vector<int> query_support_slots(const BattleState& base, int32_t opp_hp) {
    BattleState s = base;
    PokemonState& opp_mon = s.side1.team[s.side1.active_indices[0]];
    opp_mon.hp     = opp_hp;
    opp_mon.has_hp = true;

    std::vector<ActionProb> dist = cpp_compute_action_probabilities(s, 1);
    std::vector<int> slots;
    for (const auto& ap : dist) {
        if (ap.prob > 0.0) slots.push_back(ap.action.move_slot);
    }
    std::sort(slots.begin(), slots.end());
    return slots;
}

MaskScanReport analytic_mask_scan(const MaskScanConfig& cfg) {
    MaskScanReport report;

    MatchupGen gen(cfg.seed, parse_klass_core(cfg.klass),
                   cfg.shard_k, cfg.shard_of, make_paths(cfg.repo_root));

    for (int mi = 0; mi < cfg.n; ++mi) {
        BattleState state = gen.next();
        ++report.matchups_scanned;

        const PokemonState& opp = active_mon(state, 1);
        int32_t max_hp = opp.has_max_hp ? opp.max_hp : opp.stat_hp;
        if (max_hp <= 0) continue;

        // Build per-slot crossing counters (map slot → crossing count this matchup).
        std::unordered_map<int, int> slot_crossings;

        // Collect reference support at hp=1 to start sweep.
        std::vector<int> prev_slots = query_support_slots(state, 1);
        report.total_hp_points += (int)(max_hp);  // 1..max_hp

        for (int32_t hp = 2; hp <= max_hp; ++hp) {
            std::vector<int> cur_slots = query_support_slots(state, hp);

            // Find changed slots.
            std::vector<int> all_slots;
            for (int s : prev_slots) all_slots.push_back(s);
            for (int s : cur_slots)  all_slots.push_back(s);
            std::sort(all_slots.begin(), all_slots.end());
            all_slots.erase(std::unique(all_slots.begin(), all_slots.end()), all_slots.end());

            for (int s : all_slots) {
                bool in_prev = std::binary_search(prev_slots.begin(), prev_slots.end(), s);
                bool in_cur  = std::binary_search(cur_slots.begin(), cur_slots.end(), s);
                if (in_prev != in_cur) slot_crossings[s]++;
            }

            prev_slots = cur_slots;
        }

        // Accumulate into report.
        for (auto& [slot, count] : slot_crossings) {
            if (count == 0) continue;

            // Find or create slot entry.
            MaskScanSlotStats* entry = nullptr;
            for (auto& ss : report.slot_stats) {
                if (ss.move_slot == slot) { entry = &ss; break; }
            }
            if (!entry) {
                report.slot_stats.push_back(MaskScanSlotStats{slot, 0, 0});
                entry = &report.slot_stats.back();
            }
            entry->total_crossings += count;
            if (count > 1) {
                ++entry->multi_crossing_matchups;
                ++report.multi_crossing_actions;
            }
        }
    }

    return report;
}

// ---------------------------------------------------------------------------
// analytic_trace_run
// ---------------------------------------------------------------------------

// Print both mons' details into a stringstream.
static void print_mon_info(std::ostringstream& ss, const char* label,
                           const PokemonState& mon) {
    ss << label << ": species=" << mon.species
       << "  HP=" << mon.hp << "/" << mon.max_hp
       << "  ability=" << mon.ability
       << "  item=" << mon.item << "\n";
    ss << "  moves=["
       << mon.move_id0 << " (pp=" << mon.move_pp0 << "), "
       << mon.move_id1 << " (pp=" << mon.move_pp1 << "), "
       << mon.move_id2 << " (pp=" << mon.move_pp2 << "), "
       << mon.move_id3 << " (pp=" << mon.move_pp3 << ")]\n";
    ss << "  stats: HP=" << mon.stat_hp
       << " Atk=" << mon.stat_atk
       << " Def=" << mon.stat_def
       << " SpA=" << mon.stat_spa
       << " SpD=" << mon.stat_spd
       << " Spe=" << mon.stat_spe << "\n";
}

// Print damage table for a side/slot.
static void print_damage_table(std::ostringstream& ss, const BattleState& state,
                                int attacker_side, int slot) {
    ExecAction act{};
    act.kind = 0;
    act.move_slot = slot;
    try {
        DamageTable dt = damage_table(state, attacker_side, act);
        if (dt.immune) {
            ss << "    slot " << slot << ": IMMUNE\n";
            return;
        }
        ss << "    slot " << slot << ": noncrit=[";
        for (size_t i = 0; i < dt.noncrit.size(); ++i) {
            if (i) ss << ",";
            ss << dt.noncrit[i];
        }
        ss << "] crit=[";
        for (size_t i = 0; i < dt.crit.size(); ++i) {
            if (i) ss << ",";
            ss << dt.crit[i];
        }
        ss << "]\n";
    } catch (const std::exception& e) {
        ss << "    slot " << slot << ": (error: " << e.what() << ")\n";
    }
}

AnalyticTraceOutput analytic_trace_run(const AnalyticTraceConfig& cfg) {
    std::ostringstream ss;

    MatchupGen gen(cfg.seed, parse_klass_core(cfg.klass),
                   0, 1, make_paths(cfg.repo_root));  // no sharding for index-based seek

    BattleState state = advance_to_index(gen, cfg.index);

    const PokemonState& pl  = active_mon(state, 0);
    const PokemonState& opp = active_mon(state, 1);

    ss << "=== analytic_trace seed=" << cfg.seed
       << " klass=" << cfg.klass
       << " index=" << cfg.index << " ===\n\n";

    ss << "--- Pokemon ---\n";
    print_mon_info(ss, "player (side0)", pl);
    print_mon_info(ss, "opp    (side1)", opp);
    ss << "\n";

    // Speed comparison.
    int32_t pl_spd  = cpp_effective_speed(pl,  state.side0, state);
    int32_t opp_spd = cpp_effective_speed(opp, state.side1, state);
    ss << "--- Speed ---\n";
    ss << "player_effective_speed=" << pl_spd
       << "  opp_effective_speed=" << opp_spd << "\n";
    if (pl_spd > opp_spd)       ss << "  → player FASTER\n";
    else if (pl_spd < opp_spd)  ss << "  → opp FASTER\n";
    else                         ss << "  → SPEED TIE\n";
    ss << "\n";

    // Damage tables per side per slot.
    ss << "--- Damage tables ---\n";
    ss << "  player (side0 → opp):\n";
    for (int s = 0; s < 4; ++s) print_damage_table(ss, state, 0, s);
    ss << "  opp (side1 → player):\n";
    for (int s = 0; s < 4; ++s) print_damage_table(ss, state, 1, s);
    ss << "\n";

    // Analytic certify.
    Question q{};
    AnalyticResult ar = analytic_certify(state, q);

    ss << "--- Analytic result ---\n";
    ss << "verdict=" << averdict_str(ar.verdict)
       << "  tag=" << atag_str(ar.tag)
       << "  tight=" << (ar.tight ? "true" : "false")
       << "  kill_turn=" << ar.kill_turn << "\n";
    ss << "scope_mask=0x" << std::hex << ar.scope_mask << std::dec
       << "  (" << decode_scope_mask(ar.scope_mask) << ")\n";

    if (!ar.lines.empty()) {
        ss << "per-turn lines:\n";
        for (const auto& line : ar.lines) ss << "  " << line << "\n";
    }
    ss << "\n";

    // Bsolver verdicts (pessimal + exact) for the root state.
    // Small budgets: trace is a diagnostic tool; INDETERMINATE is acceptable and common.
    // stack_size reduced to 4 MB for trace calls (depth_cap implicitly safe at these budgets).
    BsolverConfig pess_cfg  = make_bsolver_cfg(BMode::Pessimal, 5'000, 1'000);
    BsolverConfig exact_cfg = make_bsolver_cfg(BMode::Exact,    5'000, 1'000);
    pess_cfg.stack_size  = 4ull * 1024 * 1024;
    exact_cfg.stack_size = 4ull * 1024 * 1024;
    // Child bsolver: minimal — shows child structure only, not exhaustive certs.
    BsolverConfig child_cfg = make_bsolver_cfg(BMode::Exact, 200, 50);
    child_cfg.stack_size    = 4ull * 1024 * 1024;

    BsolverResult pr = bsolver_certify(state, q, pess_cfg);
    BsolverResult er = bsolver_certify(state, q, exact_cfg);

    ss << "--- Bsolver ---\n";
    ss << "pessimal verdict=" << bverdict_str(pr.verdict)
       << "  nodes=" << pr.nodes_expanded << "\n";
    ss << "exact    verdict=" << bverdict_str(er.verdict)
       << "  nodes=" << er.nodes_expanded << "\n";
    ss << "\n";

    // --action: enumerate oracle children (aggregated) and mark losers.
    if (cfg.action_slot >= 0) {
        ss << "--- Oracle children for player action slot=" << cfg.action_slot << " ---\n";

        ExecAction player_act{};
        player_act.kind = 0;
        player_act.move_slot = cfg.action_slot;

        // Collect distinct children, deduped by (player_hp, opp_hp) for display.
        // Full PackedKey dedup would require a ContextInterner that may throw on
        // complex states; HP-pair dedup suffices for the trace view.
        struct ChildEntry {
            BattleState state;
            double prob;
        };
        std::vector<ChildEntry> children;
        // Key: (player_hp << 16) | opp_hp — fast dedup for display purposes.
        std::unordered_map<uint32_t, int> hp_to_idx;

        TransitionOracle oracle;
        TransitionOracle::Config ocfg;
        ocfg.max_leaves             = 200;   // very small: trace is diagnostic, not exhaustive
        ocfg.aggregate_damage_rolls = true;

        StepStats stats = oracle.step(state, player_act,
            [&](ChildOutcome co) -> bool {
                const PokemonState& cpl  = active_mon(co.child, 0);
                const PokemonState& copp = active_mon(co.child, 1);
                uint32_t hp_key = ((uint32_t)(uint16_t)cpl.hp << 16) |
                                  (uint32_t)(uint16_t)copp.hp;
                auto it = hp_to_idx.find(hp_key);
                if (it != hp_to_idx.end()) {
                    children[it->second].prob += co.prob;
                } else {
                    hp_to_idx[hp_key] = (int)children.size();
                    children.push_back(ChildEntry{co.child, co.prob});
                }
                return true;
            },
            OrderingHint::Natural, ocfg);

        ss << "distinct_children=" << children.size()
           << "  oracle_leaves=" << stats.leaves
           << "  budget_exceeded=" << stats.budget_exceeded << "\n";

        // Certify each distinct child.
        for (int i = 0; i < (int)children.size(); ++i) {
            const BattleState& child = children[i].state;
            Outcome oc = classify(child, q);

            std::string verdict_str;
            if (oc == Outcome::WIN)  { verdict_str = "WIN(terminal)"; }
            else if (oc == Outcome::LOSS) { verdict_str = "LOSS(terminal)"; }
            else {
                // Non-terminal: run exact bsolver with small budget.
                BsolverResult cr = bsolver_certify(child, q, child_cfg);
                verdict_str = std::string(bverdict_str(cr.verdict));
            }

            const PokemonState& cpl  = active_mon(child, 0);
            const PokemonState& copp = active_mon(child, 1);

            ss << "  child[" << i << "] p=" << children[i].prob
               << "  player_hp=" << cpl.hp
               << "  opp_hp=" << copp.hp
               << "  verdict=" << verdict_str;
            if (verdict_str.find("LOSS") != std::string::npos)
                ss << "  *** LOSER ***";
            ss << "\n";
        }
        ss << "\n";
    }

    return AnalyticTraceOutput{ss.str()};
}
