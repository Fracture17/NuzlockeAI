// rcheck referee core implementation. Pure classifier + census-key helper, then the
// shard run loop that emits JSONL records and a completeness summary. Mirrors
// audit_analytic_core's injected-seam contract (record audit_referee_seam).
#include "solver/audit/rcheck_core.h"

#include "solver/bucket/concede.h"     // concession_tag_names
#include "solver/bucket/expand.h"      // ExpandError
#include "solver/matchup_gen.h"

#include "nlohmann/json.hpp"

#include <chrono>
#include <cstdio>
#include <memory>
#include <stdexcept>

using nlohmann::json;

// ---------------------------------------------------------------------------
// Enum → string helpers
// ---------------------------------------------------------------------------

const char* rcheck_class_name(RcheckClass c) {
    switch (c) {
    case RcheckClass::THROWN:                  return "THROWN";
    case RcheckClass::REFEREE_INDET:           return "REFEREE_INDET";
    case RcheckClass::SOUND_AGREE_WIN:         return "SOUND_AGREE_WIN";
    case RcheckClass::SOUND_AGREE_LOSS:        return "SOUND_AGREE_LOSS";
    case RcheckClass::HARD_FAIL_B_WIN:         return "HARD_FAIL_B_WIN";
    case RcheckClass::HARD_FAIL_PESSIMAL_LOSS: return "HARD_FAIL_PESSIMAL_LOSS";
    case RcheckClass::SOUND_UNKNOWN_ON_LOSS:   return "SOUND_UNKNOWN_ON_LOSS";
    case RcheckClass::CONSERVATIVE_TAGGED:     return "CONSERVATIVE_TAGGED";
    case RcheckClass::CONSERVATIVE_UNTAGGED:   return "CONSERVATIVE_UNTAGGED";
    case RcheckClass::COUNT:                   return "?";
    }
    return "?";
}

bool rcheck_is_hard_fail(RcheckClass c) {
    return c == RcheckClass::HARD_FAIL_B_WIN
        || c == RcheckClass::HARD_FAIL_PESSIMAL_LOSS;
}

namespace {

const char* bverdict_str(BVerdict v) {
    switch (v) {
    case BVerdict::WIN:           return "WIN";
    case BVerdict::LOSS:          return "LOSS";
    case BVerdict::INDETERMINATE: return "INDET";
    }
    return "?";
}

const char* bindet_str(BIndeterminateReason r) {
    switch (r) {
    case BIndeterminateReason::None:       return "None";
    case BIndeterminateReason::LeafBudget: return "LeafBudget";
    case BIndeterminateReason::NodeCap:    return "NodeCap";
    case BIndeterminateReason::DepthCap:   return "DepthCap";
    case BIndeterminateReason::Cycle:      return "Cycle";
    }
    return "?";
}

const char* pverdict_str(PipelineVerdict v) {
    switch (v) {
    case PipelineVerdict::WIN:     return "WIN";
    case PipelineVerdict::LOSS:    return "LOSS";
    case PipelineVerdict::UNKNOWN: return "UNKNOWN";
    }
    return "?";
}

const char* bwverdict_str(BucketWinVerdict v) {
    switch (v) {
    case BucketWinVerdict::WIN:           return "WIN";
    case BucketWinVerdict::FAIL:          return "FAIL";
    case BucketWinVerdict::INDETERMINATE: return "INDET";
    }
    return "?";
}

const char* bwindet_str(BucketWinIndetReason r) {
    switch (r) {
    case BucketWinIndetReason::None:        return "None";
    case BucketWinIndetReason::DepthCap:    return "DepthCap";
    case BucketWinIndetReason::VisitCap:    return "VisitCap";
    case BucketWinIndetReason::PpAuditFail: return "PpAuditFail";
    }
    return "?";
}

// ExpandError stage → census suffix (expand.h Stage enum).
const char* expand_stage_name(ExpandError::Stage st) {
    switch (st) {
    case ExpandError::Stage::Precondition:           return "Precondition";
    case ExpandError::Stage::WeakDominanceViolation: return "WeakDominanceViolation";
    case ExpandError::Stage::UnsupportedMove:        return "UnsupportedMove";
    case ExpandError::Stage::SupportFlip:            return "SupportFlip";
    case ExpandError::Stage::ReplayDivergence:       return "ReplayDivergence";
    case ExpandError::Stage::ShiftViolation:         return "ShiftViolation";
    case ExpandError::Stage::InternMismatch:         return "InternMismatch";
    case ExpandError::Stage::DerivedSplitOverflow:   return "DerivedSplitOverflow";
    case ExpandError::Stage::ImageSplit:             return "ImageSplit";
    }
    return "Unknown";
}

MatchupGen::Class parse_klass(const std::string& k) {
    if (k == "uniform") return MatchupGen::Class::Uniform;
    if (k == "berry")   return MatchupGen::Class::BerryHolders;
    if (k == "sash")    return MatchupGen::Class::SashSturdy;
    throw std::invalid_argument("rcheck: unknown klass '" + k + "' (use uniform/berry/sash)");
}

MatchupGen::Paths make_paths(const std::string& repo_root) {
    return MatchupGen::Paths{
        repo_root + "/liveplay/data/generated_learnsets.json",
        repo_root + "/liveplay/data/generated_abilities.json"};
}

uint64_t now_us(std::chrono::steady_clock::time_point a,
                std::chrono::steady_clock::time_point b) {
    return (uint64_t)std::chrono::duration_cast<std::chrono::microseconds>(b - a).count();
}

// OR-reduce a per-bit concession histogram to a mask (bit set iff count > 0).
uint32_t mask_of(const std::array<uint64_t, 32>& hist) {
    uint32_t m = 0;
    for (int bit = 0; bit < 32; ++bit)
        if (hist[bit]) m |= (1u << bit);
    return m;
}

// {tag_name: count} for every nonzero concession bit.
json concessions_json(const std::array<uint64_t, 32>& hist) {
    json j = json::object();
    for (int bit = 0; bit < 32; ++bit) {
        if (!hist[bit]) continue;
        std::string name = concession_tag_names(1u << bit);
        if (name.empty()) name = "bit" + std::to_string(bit);
        j[name] = hist[bit];
    }
    return j;
}

json telemetry_json(const BucketWinStats& s) {
    return json{
        {"buckets_visited",   s.buckets_visited},
        {"terminal_buckets",  s.terminal_buckets},
        {"expand_calls",      s.expand_calls},
        {"replays",           s.replays},
        {"oracle_leaves",     s.oracle_leaves},
        {"conceded_branches", s.conceded_branches},
        {"max_depth",         s.max_depth},
        {"b_elapsed_us",      s.elapsed_us},
        {"edge_hits",               s.edge_hits},
        {"edge_misses",             s.edge_misses},
        {"memo_hits",               s.memo_hits},
        {"memo_stores",             s.memo_stores},
        {"memo_suppressed",         s.memo_suppressed},
        {"memo_containment_missed", s.memo_containment_missed},
        {"canonical_repeats",       s.canonical_repeats},
        {"pp_horizon_used",         s.pp_horizon_used},
        {"audit_expands",           s.audit_expands},
        {"pp_audit_rejects",        s.pp_audit_rejects},
    };
}

}  // namespace

// ---------------------------------------------------------------------------
// Pure classifier
// ---------------------------------------------------------------------------

RcheckClass classify_rcheck(const PipelineOutcome& po, BVerdict exact) {
    if (po.thrown)                     return RcheckClass::THROWN;
    if (exact == BVerdict::INDETERMINATE) return RcheckClass::REFEREE_INDET;

    switch (po.verdict) {
    case PipelineVerdict::WIN:
        return exact == BVerdict::WIN ? RcheckClass::SOUND_AGREE_WIN
                                      : RcheckClass::HARD_FAIL_B_WIN;      // WIN × LOSS
    case PipelineVerdict::LOSS:
        return exact == BVerdict::LOSS ? RcheckClass::SOUND_AGREE_LOSS
                                       : RcheckClass::HARD_FAIL_PESSIMAL_LOSS;  // LOSS × WIN
    case PipelineVerdict::UNKNOWN:
        if (exact == BVerdict::LOSS) return RcheckClass::SOUND_UNKNOWN_ON_LOSS;
        // exact WIN: tagged vs untagged conservatism split.
        return po.concession_mask != 0 ? RcheckClass::CONSERVATIVE_TAGGED
                                       : RcheckClass::CONSERVATIVE_UNTAGGED;
    }
    return RcheckClass::REFEREE_INDET;  // unreachable
}

// ---------------------------------------------------------------------------
// Census key
// ---------------------------------------------------------------------------

std::string throw_census_key(const std::exception& e) {
    if (const auto* ee = dynamic_cast<const ExpandError*>(&e))
        return std::string("expand:") + expand_stage_name(ee->stage);

    std::string what = e.what();
    auto has = [&](const char* sub) { return what.find(sub) != std::string::npos; };
    if (has("residual_unknown")) return "residual_unknown";
    if (has("form-change"))      return "form-change";
    if (has("ai-final-gambit"))  return "ai-final-gambit";
    if (has("ai-bench"))         return "ai-bench";

    return "other:" + what.substr(0, 60);
}

// ---------------------------------------------------------------------------
// Shard run loop
// ---------------------------------------------------------------------------

RcheckReport rcheck_run(const RcheckConfig& cfg, std::ostream& out) {
    // Fail loud: injected list and generator path are mutually exclusive.
    if (!cfg.injected.empty() && !cfg.repo_root.empty())
        throw std::invalid_argument(
            "rcheck_run: injected list and repo_root both set — mutually exclusive; "
            "clear repo_root when injecting matchups");

    const bool use_injected = !cfg.injected.empty();

    std::unique_ptr<MatchupGen> gen;
    if (!use_injected)
        gen = std::make_unique<MatchupGen>(cfg.seed, parse_klass(cfg.klass),
                                           cfg.shard_k, cfg.shard_of,
                                           make_paths(cfg.repo_root));

    // Build the production stage configs (used when the seams are null).
    PipelineConfig pcfg;
    pcfg.pessimal_cfg.oracle_max_leaves = cfg.pess_leaves;
    pcfg.pessimal_cfg.node_cap          = cfg.pess_nodes;
    pcfg.win_cfg.depth_cap              = cfg.b_depth;
    pcfg.win_cfg.visit_cap              = cfg.b_visits;
    // Cache ownership: leave win_cfg.cache = nullptr so bucket_win_certify builds a
    // per-certify local cache. rcheck runs one question per matchup and matchups never
    // share d, so a shard-lifetime shared cache would add unbounded memory for zero
    // cross-matchup hits; the pass-in seam exists for future same-matchup question families.
    pcfg.win_cfg.enable_edge_cache      = cfg.enable_cache;
    pcfg.win_cfg.enable_verdict_memo    = cfg.enable_cache;
    pcfg.win_cfg.enable_pp_canon        = cfg.enable_pp_canon;

    BsolverConfig exact_cfg;
    exact_cfg.mode              = BMode::Exact;
    exact_cfg.oracle_max_leaves = cfg.exact_leaves;
    exact_cfg.node_cap          = cfg.exact_nodes;

    const Question q{};  // default: kill-opponent + no-faint (mirrors ccheck)

    const int total = use_injected ? (int)cfg.injected.size() : cfg.n;

    RcheckReport report;

    for (int i = 0; i < total; ++i) {
        BattleState state = use_injected ? cfg.injected[i] : gen->next();
        const int global_index = cfg.shard_k + i * cfg.shard_of;

        // --- Pipeline (catch → THROWN) ---
        PipelineResult pres;
        PipelineOutcome po;
        bool thrown = false;
        std::string thrown_key, thrown_what;
        try {
            pres = cfg.pipeline_fn ? cfg.pipeline_fn(state, q)
                                   : run_pipeline(state, q, pcfg);
            po.verdict         = pres.verdict;
            po.b_reason        = pres.b_reason;
            po.concession_mask = mask_of(pres.concession_histogram);
        } catch (const std::exception& e) {
            thrown        = true;
            po.thrown     = true;
            thrown_key    = throw_census_key(e);
            thrown_what   = e.what();
            po.throw_key  = thrown_key;
            po.throw_what = thrown_what;
        }

        // --- Exact referee (always) ---
        auto te0 = std::chrono::steady_clock::now();
        BsolverResult ex = cfg.exact_fn ? cfg.exact_fn(state, q)
                                        : bsolver_certify(state, q, exact_cfg);
        auto te1 = std::chrono::steady_clock::now();
        const uint64_t exact_us = now_us(te0, te1);

        RcheckClass klass = classify_rcheck(po, ex.verdict);

        // Accumulate report.
        ++report.n;
        report.bins[(int)klass]++;
        if (rcheck_is_hard_fail(klass)) ++report.hard_fails;
        if (thrown) report.throw_census[thrown_key]++;
        if (!thrown) {
            for (int bit = 0; bit < 32; ++bit)
                report.concession_histogram[bit] += pres.concession_histogram[bit];
        }

        // --- JSONL record ---
        json pipeline_j;
        if (thrown) {
            pipeline_j = json{
                {"verdict",  nullptr},
                {"b_ran",    false},
                {"thrown",   json{{"key", thrown_key}, {"what", thrown_what}}},
            };
        } else {
            pipeline_j = json{
                {"verdict",          pverdict_str(pres.verdict)},
                {"pessimal_verdict", bverdict_str(pres.pessimal_verdict)},
                {"pessimal_reason",  bindet_str(pres.pessimal_reason)},
                {"b_ran",            pres.b_ran},
                {"b_verdict",        bwverdict_str(pres.b_verdict)},
                {"b_reason",         bwindet_str(pres.b_reason)},
                {"concessions",      concessions_json(pres.concession_histogram)},
                {"thrown",           nullptr},
            };
        }

        json rec{
            {"klass",          cfg.klass},
            {"seed",           cfg.seed},
            {"index",          global_index},
            {"shard",          json{{"k", cfg.shard_k}, {"of", cfg.shard_of}}},
            {"classification", rcheck_class_name(klass)},
            {"pipeline",       pipeline_j},
            {"exact",          json{{"verdict", bverdict_str(ex.verdict)},
                                    {"reason",  bindet_str(ex.reason)}}},
            {"timing_us",      json{{"pessimal", thrown ? 0 : pres.pessimal_us},
                                    {"b",        thrown ? 0 : pres.b_us},
                                    {"exact",    exact_us}}},
            {"telemetry",      thrown ? telemetry_json(BucketWinStats{})
                                      : telemetry_json(pres.b_stats)},
        };
        out << rec.dump() << '\n';

        // Live hard-fail print.
        if (rcheck_is_hard_fail(klass)) {
            std::printf("HARD_FAIL[%s] klass=%s seed=%llu index=%d pipeline=%s exact=%s\n",
                        rcheck_class_name(klass), cfg.klass.c_str(),
                        (unsigned long long)cfg.seed, global_index,
                        po.thrown ? "THROWN" : pverdict_str(po.verdict),
                        bverdict_str(ex.verdict));
            std::fflush(stdout);
        }
    }

    // --- Summary line (shard-completeness marker) ---
    json bins_j = json::object();
    for (int c = 0; c < (int)RcheckClass::COUNT; ++c)
        bins_j[rcheck_class_name((RcheckClass)c)] = report.bins[c];

    json census_j = json::object();
    for (const auto& kv : report.throw_census) census_j[kv.first] = kv.second;

    json chist_j = json::object();
    for (int bit = 0; bit < 32; ++bit) {
        if (!report.concession_histogram[bit]) continue;
        std::string name = concession_tag_names(1u << bit);
        if (name.empty()) name = "bit" + std::to_string(bit);
        chist_j[name] = report.concession_histogram[bit];
    }

    json summary{
        {"summary", json{
            {"klass",                cfg.klass},
            {"seed",                 cfg.seed},
            {"shard",                json{{"k", cfg.shard_k}, {"of", cfg.shard_of}}},
            {"n",                    report.n},
            {"bins",                 bins_j},
            {"throw_census",         census_j},
            {"concession_histogram", chist_j},
            {"hard_fails",           report.hard_fails},
        }}};
    out << summary.dump() << '\n';

    return report;
}
