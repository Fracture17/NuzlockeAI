// run_pipeline — pessimal → Solver B lattice (amendment 18). Pessimal LOSS is the only
// LOSS source; pessimal WIN/INDET both route to B (never evidence, record
// pessimal_loss_pruner_only). Stage exceptions propagate to the caller unchanged.
#include "solver/bucket/pipeline.h"

#include <chrono>

namespace {

uint64_t elapsed_us(std::chrono::steady_clock::time_point a,
                    std::chrono::steady_clock::time_point b) {
    return (uint64_t)std::chrono::duration_cast<std::chrono::microseconds>(b - a).count();
}

}  // namespace

PipelineResult run_pipeline(const BattleState& initial_state, const Question& q,
                            const PipelineConfig& cfg) {
    PipelineResult out;

    // Stage 1: pessimal LOSS-pruner. Mode is forced regardless of caller config.
    BsolverConfig pess_cfg = cfg.pessimal_cfg;
    pess_cfg.mode = BMode::Pessimal;

    auto t0 = std::chrono::steady_clock::now();
    BsolverResult pr = cfg.pessimal_override
                           ? cfg.pessimal_override(initial_state, q, pess_cfg)
                           : bsolver_certify(initial_state, q, pess_cfg);
    auto t1 = std::chrono::steady_clock::now();

    out.pessimal_verdict = pr.verdict;
    out.pessimal_reason  = pr.reason;
    out.pessimal_us      = elapsed_us(t0, t1);

    // Pessimal LOSS is conclusive; Solver B is NOT invoked.
    if (pr.verdict == BVerdict::LOSS) {
        out.verdict = PipelineVerdict::LOSS;
        return out;
    }

    // Pessimal WIN and INDETERMINATE are identical here — neither is evidence. Run B.
    auto t2 = std::chrono::steady_clock::now();
    BucketWinResult br = cfg.bwin_override
                             ? cfg.bwin_override(initial_state, q, cfg.win_cfg)
                             : bucket_win_certify(initial_state, q, cfg.win_cfg);
    auto t3 = std::chrono::steady_clock::now();

    out.b_ran                = true;
    out.b_verdict            = br.verdict;
    out.b_reason             = br.reason;
    out.concession_histogram = br.concession_histogram;
    out.b_stats              = br.stats;
    out.b_us                 = elapsed_us(t2, t3);

    // B WIN is sound; B FAIL and INDETERMINATE both fold into UNKNOWN.
    out.verdict = (br.verdict == BucketWinVerdict::WIN) ? PipelineVerdict::WIN
                                                        : PipelineVerdict::UNKNOWN;
    return out;
}
