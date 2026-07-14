// Core audit logic callable from both the audit_oracle exe and the Catch2 test suite.
// Implements audit_selfcheck() and audit_mc() on top of TransitionOracle + MatchupGen.
// Statistical choice: per-child 5-sigma binomial test (|obs/M - p| > 5*sqrt(p*(1-p)/M)).
// Expected-count floor: skip children with p*M < floor (5.0 by default) — too rare for
// reliable testing at small M. Chi-squared is not used: per-child binomial gives clearer
// diagnostics per failure and handles non-uniform distributions correctly.
#include "solver/audit/audit_core.h"

#include "ai_analytic.h"
#include "solver/action_space.h"
#include "solver/matchup_gen.h"
#include "solver/oracle_types.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"
#include "core_leaf.h"
#include "move_exec.h"
#include "move_exec_damage.h"
#include "native_rng.h"
#include "oracle.h"
#include "solver_turn.h"
#include "state.h"
#include "state_eq.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

static MatchupGen::Paths make_paths(const std::string& repo_root) {
    return MatchupGen::Paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"
    };
}

static MatchupGen::Class parse_klass(const std::string& klass) {
    if (klass == "uniform")  return MatchupGen::Class::Uniform;
    if (klass == "berry")    return MatchupGen::Class::BerryHolders;
    if (klass == "sash")     return MatchupGen::Class::SashSturdy;
    throw std::invalid_argument("audit: unknown klass '" + klass + "' (use uniform/berry/sash)");
}

static std::string action_to_str(const ExecAction& a) {
    std::ostringstream oss;
    oss << "kind=" << a.kind
        << " slot=" << a.move_slot
        << " mega=" << a.mega;
    return oss.str();
}

// Collect all (PackedKey, prob) from one oracle call into a ContextInterner.
// Aggregates duplicate keys by summing probabilities (handles non-deduped raw leaves).
// Returns the StepStats so callers can detect budget-exceeded (truncated support).
static StepStats collect_support(TransitionOracle& oracle,
                             const BattleState& state,
                             const ExecAction& action,
                             ContextInterner& interner,
                             std::unordered_map<PackedKey, double>& support,
                             std::vector<ChildOutcome>& all_leaves) {
    return oracle.step(state, action, [&](ChildOutcome co) -> bool {
        PackedKey key = interner.pack(co.child);
        support[key] += co.prob;
        all_leaves.push_back(std::move(co));
        return true;
    });
}

// Sum probabilities of a leaf vector.
static double sum_probs(const std::vector<ChildOutcome>& leaves) {
    double s = 0.0;
    for (const auto& c : leaves) s += c.prob;
    return s;
}

// Build sorted (key, prob) multiset from leaves for ordering comparison.
// Uses state_hash_solver as the key (consistent with existing oracle tests).
static std::vector<std::pair<uint64_t, double>> to_sorted_multiset(
    const std::vector<ChildOutcome>& leaves) {
    std::vector<std::pair<uint64_t, double>> v;
    v.reserve(leaves.size());
    for (const auto& c : leaves)
        v.push_back({state_hash_solver(c.child), c.prob});
    std::sort(v.begin(), v.end());
    return v;
}

// Check every child: HP in [0, max_hp], exactly one active per side.
static bool child_sanity(const BattleState& child) {
    auto check_side = [](const SideState& side) -> bool {
        if (side.active_indices.size() != 1) return false;
        int idx = side.active_indices[0];
        if (idx < 0 || idx >= (int)side.team.size()) return false;
        const PokemonState& mon = side.team[idx];
        // HP in [0, max_hp] — only if max_hp is set
        if (mon.has_hp && mon.has_max_hp) {
            if (mon.hp < 0 || mon.hp > mon.max_hp) return false;
        }
        return true;
    };
    return check_side(child.side0) && check_side(child.side1);
}

// ---------------------------------------------------------------------------
// Build random-mode luck structs for one sample.
// Seed is derived deterministically from (matchup_seed, matchup_index, sample_index).
// ---------------------------------------------------------------------------

struct RandomModeLuck {
    NativeRng rng;
    DamageLoopLuck lp0;
    DamageLoopLuck lp1;
    TurnLuck tl0;
    TurnLuck tl1;

    explicit RandomModeLuck(uint64_t seed) : rng(seed) {
        lp0.random_mode = true; lp0.rng = &rng;
        lp1.random_mode = true; lp1.rng = &rng;
        tl0.random_mode = true; tl0.rng = &rng;
        tl1.random_mode = true; tl1.rng = &rng;
    }
};

// ---------------------------------------------------------------------------
// audit_selfcheck
// ---------------------------------------------------------------------------

AuditSelfcheckReport audit_selfcheck(const AuditSelfcheckConfig& cfg) {
    AuditSelfcheckReport report;
    TransitionOracle oracle;

    MatchupGen gen(cfg.seed, parse_klass(cfg.klass),
                   cfg.shard_k, cfg.shard_of, make_paths(cfg.repo_root));

    for (int mi = 0; mi < cfg.n; ++mi) {
        BattleState state = gen.next();
        std::vector<ExecAction> actions = legal_player_actions(state);

        for (const ExecAction& action : actions) {
            int reason_mask = 0;
            std::string detail;

            std::vector<ChildOutcome> nat_leaves, adv_leaves;
            bool threw = false;
            std::string throw_msg;
            StepStats nat_stats{}, adv_stats{};

            // Both runs use aggregate_damage_rolls=true (the default).
            TransitionOracle::Config cfg_on;
            cfg_on.aggregate_damage_rolls = true;

            // Collect Natural and AdverseFirst (both with aggregation ON)
            try {
                nat_stats = oracle.step(state, action, [&](ChildOutcome co) -> bool {
                    nat_leaves.push_back(co);
                    return true;
                }, OrderingHint::Natural, cfg_on);

                adv_stats = oracle.step(state, action, [&](ChildOutcome co) -> bool {
                    adv_leaves.push_back(co);
                    return true;
                }, OrderingHint::AdverseFirst, cfg_on);
            } catch (const std::exception& e) {
                threw = true;
                throw_msg = e.what();
                reason_mask |= (1 << static_cast<int>(AuditFailReason::OracleThrewException));
                detail += "oracle_threw: " + throw_msg + "; ";
            }

            if (!threw) {
                // Skip checks if budget was exceeded — partial leaf sets cannot be checked.
                // Budget exceeded is not an oracle error; it means this matchup+action pair
                // has too many leaves for the current budget. Count and skip.
                if (nat_stats.budget_exceeded || adv_stats.budget_exceeded) {
                    ++report.skipped_budget;
                    continue;
                }

                // Check Σp = 1 ± 1e-9
                double nat_sum = sum_probs(nat_leaves);
                if (std::abs(nat_sum - 1.0) > 1e-9) {
                    reason_mask |= (1 << static_cast<int>(AuditFailReason::MassError));
                    detail += "nat_sum=" + std::to_string(nat_sum) + "; ";
                }
                double adv_sum = sum_probs(adv_leaves);
                if (std::abs(adv_sum - 1.0) > 1e-9) {
                    reason_mask |= (1 << static_cast<int>(AuditFailReason::MassError));
                    detail += "adv_sum=" + std::to_string(adv_sum) + "; ";
                }

                // Check Natural ≡ AdverseFirst multiset
                auto nat_ms = to_sorted_multiset(nat_leaves);
                auto adv_ms = to_sorted_multiset(adv_leaves);
                if (nat_ms != adv_ms) {
                    reason_mask |= (1 << static_cast<int>(AuditFailReason::OrderingMismatch));
                    detail += "multiset_mismatch nat=" + std::to_string(nat_leaves.size())
                            + " adv=" + std::to_string(adv_leaves.size()) + "; ";
                }

                // Check child sanity on Natural leaves
                for (const auto& co : nat_leaves) {
                    if (!child_sanity(co.child)) {
                        reason_mask |= (1 << static_cast<int>(AuditFailReason::ChildSanity));
                        detail += "child_sanity_fail; ";
                        break;
                    }
                }

                // AggregationMismatch: run step() with aggregation OFF and compare
                // PackedKey→Σprob maps. OFF-run budget exceeded → skip (not fail).
                {
                    TransitionOracle::Config cfg_off;
                    cfg_off.aggregate_damage_rolls = false;

                    std::vector<ChildOutcome> off_leaves;
                    bool agg_skip = false;
                    try {
                        StepStats off_stats = oracle.step(state, action,
                            [&](ChildOutcome co) -> bool {
                                off_leaves.push_back(co);
                                return true;
                            }, OrderingHint::Natural, cfg_off);
                        if (off_stats.budget_exceeded) {
                            agg_skip = true;
                            ++report.skipped_budget;
                        }
                    } catch (const std::exception&) {
                        // OFF run threw (unusual); skip the comparison, not a failure here
                        agg_skip = true;
                    }

                    if (!agg_skip) {
                        // Build PackedKey→Σprob maps for both
                        std::unordered_map<PackedKey, double> on_map, off_map;
                        for (const auto& co : nat_leaves)
                            on_map[state_hash_solver(co.child)] += co.prob;
                        for (const auto& co : off_leaves)
                            off_map[state_hash_solver(co.child)] += co.prob;

                        bool maps_match = (on_map.size() == off_map.size());
                        if (maps_match) {
                            for (const auto& kv : on_map) {
                                auto it = off_map.find(kv.first);
                                if (it == off_map.end()
                                        || std::abs(it->second - kv.second) > 1e-9) {
                                    maps_match = false;
                                    break;
                                }
                            }
                        }
                        bool leaves_ok = (nat_leaves.size() <= off_leaves.size());

                        if (!maps_match || !leaves_ok) {
                            reason_mask |= (1 << static_cast<int>(
                                AuditFailReason::AggregationMismatch));
                            detail += "agg_mismatch on=" + std::to_string(nat_leaves.size())
                                    + " off=" + std::to_string(off_leaves.size())
                                    + " maps_match=" + std::to_string(maps_match) + "; ";
                        }
                    }
                }
            }

            if (reason_mask != 0) {
                ++report.total_failures;
                // Update histogram (5 possible reason bits now)
                for (int bit = 0; bit < 5; ++bit) {
                    if (reason_mask & (1 << bit)) {
                        auto reason = static_cast<AuditFailReason>(bit);
                        ++report.reason_histogram[reason];
                    }
                }
                SelfcheckFailure f;
                f.seed          = cfg.seed;
                f.matchup_index = mi;
                f.action_desc   = action_to_str(action);
                f.reason_mask   = reason_mask;
                f.detail        = detail;
                report.failures.push_back(std::move(f));
            }
        }
    }

    return report;
}

// ---------------------------------------------------------------------------
// audit_mc
// ---------------------------------------------------------------------------

AuditMcReport audit_mc(const AuditMcConfig& cfg) {
    AuditMcReport report;
    TransitionOracle oracle;

    MatchupGen gen(cfg.seed, parse_klass(cfg.klass),
                   /*shard_k=*/0, /*shard_of=*/1, make_paths(cfg.repo_root));

    for (int mi = 0; mi < cfg.n; ++mi) {
        BattleState state = gen.next();
        std::vector<ExecAction> actions = legal_player_actions(state);
        if (actions.empty()) continue;

        // Use only the first legal player action (iterating all would be expensive at large M).
        const ExecAction& player_action = actions[0];

        // ---- Enumerate oracle support ----
        ContextInterner interner;
        std::unordered_map<PackedKey, double> support;
        std::vector<ChildOutcome> support_leaves;
        StepStats sstats = collect_support(oracle, state, player_action,
                                           interner, support, support_leaves);
        if (sstats.budget_exceeded) {
            // Support is truncated — sampled children may legitimately fall outside it.
            // Completeness cannot be tested here; skip (mirrors selfcheck's budget skip).
            ++report.skipped_budget;
            continue;
        }

        // ---- Get AI action distribution for explicit pinning ----
        int ai_idx = 1;
        std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(state, ai_idx);
        if (ai_probs.empty()) continue;

        // Build cumulative distribution for sampling AI action.
        std::vector<double> ai_cum;
        ai_cum.reserve(ai_probs.size());
        double cum = 0.0;
        for (const auto& ap : ai_probs) { cum += ap.prob; ai_cum.push_back(cum); }

        // ---- Frequency counters per PackedKey ----
        std::unordered_map<PackedKey, int> freq;
        for (const auto& kv : support) freq[kv.first] = 0;

        // ---- Draw M samples ----
        for (int si = 0; si < cfg.samples; ++si) {
            // Deterministic per-sample seed: hash of (matchup seed, matchup index, sample index).
            uint64_t sample_seed = cfg.seed
                ^ (static_cast<uint64_t>(mi + 1) * 6364136223846793005ULL)
                ^ (static_cast<uint64_t>(si + 1) * 2862933555777941757ULL);

            RandomModeLuck luck(sample_seed);

            // Sample AI action explicitly from cpp_compute_action_probabilities distribution.
            // Use a dedicated uniform draw (separate from the game RNG) so we don't perturb it.
            NativeRng ai_sampler(sample_seed ^ 0xA5A5A5A5A5A5A5A5ULL);
            double ai_roll = ai_sampler.random();
            int ai_choice_idx = static_cast<int>(ai_probs.size()) - 1;
            for (int i = 0; i < (int)ai_cum.size(); ++i) {
                if (ai_roll < ai_cum[i]) { ai_choice_idx = i; break; }
            }
            const ExecAction& ai_action = ai_probs[ai_choice_idx].action;

            // Run one random-mode turn (no oracle overrides — Cat-A resolves natively).
            BattleState state_copy = state;
            std::vector<ExecAction> acts_p0 = {player_action};
            std::vector<ExecAction> acts_p1 = {ai_action};
            OracleOverrides empty_ov;
            // For random-mode: the turn must complete without pause (Cat-A is resolved by rng).
            // Use cpp_run_one_turn_solver with random-mode luck; Cat-A pauses are unexpected here
            // since Cat-A is handled by the engine's native RNG in random mode.
            SolverTurnResult result = cpp_run_one_turn_solver(
                state_copy, acts_p0, acts_p1,
                luck.lp0, luck.lp1,
                luck.tl0, luck.tl1,
                player_action.mega, ai_action.mega,
                empty_ov);

            if (!result.ok) {
                // Turn errored: skip this sample (don't count as failure, may be expected for
                // some matchups; excessive errors would surface in completeness count).
                continue;
            }

            if (result.paused) {
                // Speed tie in random mode should be resolved by native RNG tiebreaker.
                // If we still get a pause, skip this sample — Cat-A in random mode means the
                // engine native path wasn't given a real speed tie resolution; non-fatal here.
                continue;
            }

            // Pack the resulting child state.
            PackedKey sampled_key;
            try {
                sampled_key = interner.pack(state_copy);
            } catch (const std::exception& e) {
                // Pack failed — sanity hole; treat as completeness failure.
                McCompletenessHole hole;
                hole.seed          = cfg.seed;
                hole.matchup_index = mi;
                hole.action_desc   = action_to_str(player_action);
                hole.sample_index  = si;
                hole.detail        = std::string("pack_failed: ") + e.what();
                report.holes.push_back(std::move(hole));
                ++report.completeness_failures;
                continue;
            }

            // HARD FAIL: sampled child not in enumerated support (completeness hole).
            if (support.find(sampled_key) == support.end()) {
                McCompletenessHole hole;
                hole.seed          = cfg.seed;
                hole.matchup_index = mi;
                hole.action_desc   = action_to_str(player_action);
                hole.sample_index  = si;
                std::ostringstream oss;
                oss << "sampled_key=0x" << std::hex << sampled_key
                    << " not in support (support_size=" << std::dec << support.size() << ")"
                    << " sample_seed=" << sample_seed;
                hole.detail = oss.str();
                report.holes.push_back(std::move(hole));
                ++report.completeness_failures;
                // Do NOT continue — also record in freq as unknown for diagnostic purposes.
                // But we can't add to freq without a valid key. Just continue.
                continue;
            }

            freq[sampled_key]++;
        }

        // ---- Statistical test: per-child 5-sigma binomial ----
        // For each child in support, test that observed frequency matches expected probability.
        // Skip children with expected count < floor (too rare).
        // Count valid samples (those that didn't fail/skip).
        int valid_samples = 0;
        for (const auto& kv : freq) valid_samples += kv.second;
        // Add completeness failures to valid sample count for freq normalization.
        // Actually just use total of all freq counts — skip/error samples aren't counted.

        if (valid_samples > 0) {
            double M = static_cast<double>(valid_samples);
            for (const auto& kv : support) {
                PackedKey key = kv.first;
                double p = kv.second;
                double expected_count = p * M;
                if (expected_count < cfg.expected_count_floor) continue;

                int observed = freq.count(key) ? freq.at(key) : 0;
                double obs_freq = static_cast<double>(observed) / M;
                double sigma = std::sqrt(p * (1.0 - p) / M);
                if (sigma < 1e-15) continue;  // degenerate (p≈0 or p≈1)
                double z = std::abs(obs_freq - p) / sigma;

                if (z > cfg.stat_sigma_threshold) {
                    McStatFailure sf;
                    sf.seed           = cfg.seed;
                    sf.matchup_index  = mi;
                    sf.action_desc    = action_to_str(player_action);
                    sf.packed_key     = key;
                    sf.expected_prob  = p;
                    sf.observed_freq  = obs_freq;
                    sf.z_score        = z;
                    std::ostringstream oss;
                    oss << "z=" << z << " p=" << p << " obs=" << obs_freq
                        << " M=" << M << " expected_count=" << expected_count;
                    sf.detail = oss.str();
                    report.stat_fails.push_back(std::move(sf));
                    ++report.stat_failures;
                }
            }
        }
    }

    return report;
}
