// bucket_win_certify — Solver B DFS core (spec §6 / plan Task 7). Tri-valued recursion
// over Expand's AND-set children; OR over legal player actions. On-stack repeated bucket
// = FAIL (amendment 16(a), deliberately diverging from bsolver's INDETERMINATE(Cycle)).
// Runs on a dedicated-stack pthread (bsolver pattern): exceptions captured via
// exception_ptr and rethrown on the caller thread after join.
#include "solver/bucket/win_solver.h"

#include "ai_analytic.h"                 // cpp_compute_action_probabilities
#include "solver/action_space.h"         // legal_player_actions
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/concede.h"       // concede_tags
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"

#include <chrono>
#include <exception>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#include <unordered_set>
#include <utility>
#include <vector>

// ---------------------------------------------------------------------------
// BucketKey hashing
// ---------------------------------------------------------------------------

std::size_t BucketKeyHash::operator()(const BucketKey& k) const {
    // FNV-1a over the five 32-bit fields.
    std::size_t h = 1469598103934665603ULL;
    auto mix = [&](uint32_t v) {
        h ^= static_cast<std::size_t>(v);
        h *= 1099511628211ULL;
    };
    mix(k.d);
    mix(static_cast<uint32_t>(k.pl_lo));
    mix(static_cast<uint32_t>(k.pl_hi));
    mix(static_cast<uint32_t>(k.op_lo));
    mix(static_cast<uint32_t>(k.op_hi));
    return h;
}

namespace {

BucketKey key_of(const Bucket& b) {
    return BucketKey{b.d(), b.player_hp().lo, b.player_hp().hi,
                     b.opp_hp().lo, b.opp_hp().hi};
}

// Local tri-valued verdict for the recursion.
enum class V { WIN, FAIL, INDET };

// Per-certify-call solver state (threaded through the DFS).
struct WinState {
    TransitionOracle   oracle;
    ContextInterner    interner;
    BreakpointRegistry registry;
    BpSet              bp;
    ExpandContext      ctx;           // one persistent context (interner mutated in place)

    const Question&         q;
    const BucketWinConfig&  cfg;

    // Buckets currently on the recursion stack (on-stack repeat = FAIL).
    std::unordered_set<BucketKey, BucketKeyHash> stack;

    // Sticky visit-cap flag: once tripped, every deeper call short-circuits to INDET.
    bool visit_cap_hit = false;
    // First cap reason observed (records DepthCap vs VisitCap).
    BucketWinIndetReason first_reason = BucketWinIndetReason::None;

    BucketWinResult result;

    WinState(const Question& q_, const BucketWinConfig& cfg_) : q(q_), cfg(cfg_) {}
};

// Unpack the LO corner of a bucket into a concrete state. Legality of player actions
// depends only on d (context), not HP, so the LO corner is a valid enumeration point.
BattleState lo_corner_state(WinState& S, const Bucket& A) {
    PackedKey k = make_packed_key(A.d(),
                                  static_cast<uint16_t>(A.player_hp().lo),
                                  static_cast<uint16_t>(A.opp_hp().lo));
    return S.interner.unpack(k);
}

void record_reason(WinState& S, BucketWinIndetReason r) {
    if (S.first_reason == BucketWinIndetReason::None) S.first_reason = r;
}

// Accumulate the per-bit concession histogram + counters for a conceded branch.
void tally_concession(WinState& S, uint32_t tag) {
    for (int bit = 0; bit < 32; ++bit) {
        if (tag & (1u << bit)) S.result.concession_histogram[bit]++;
    }
    S.result.stats.conceded_branches++;
}

V dfs(WinState& S, const Bucket& A, int depth);

// AND over one action's children; bail on the first non-WIN child (FAIL or INDET wins).
V and_over_children(WinState& S, const ExpandResult& r, int depth) {
    for (const ChildBucket& child : r.children) {
        V cv = dfs(S, child.bucket, depth + 1);
        if (cv != V::WIN) return cv;   // first non-WIN decides (INDET or FAIL)
    }
    return V::WIN;
}

V dfs(WinState& S, const Bucket& A, int depth) {
    S.result.stats.buckets_visited++;
    if (depth > S.result.stats.max_depth) S.result.stats.max_depth = depth;

    // Step 1: terminal classification.
    Outcome oc = classify_bucket(A, S.q, S.interner);
    if (oc != Outcome::CONTINUE) {
        S.result.stats.terminal_buckets++;
        return oc == Outcome::WIN ? V::WIN : V::FAIL;
    }

    // Step 2: depth cap.
    if (depth >= S.cfg.depth_cap) {
        record_reason(S, BucketWinIndetReason::DepthCap);
        return V::INDET;
    }

    // Step 3: on-stack repeated bucket → FAIL (amendment 16(a)).
    BucketKey key = key_of(A);
    if (S.stack.count(key)) return V::FAIL;

    // Step 4: sticky visit cap → INDET.
    if (S.visit_cap_hit || S.result.stats.buckets_visited > S.cfg.visit_cap) {
        S.visit_cap_hit = true;
        record_reason(S, BucketWinIndetReason::VisitCap);
        return V::INDET;
    }

    S.stack.insert(key);

    // Step 5: enumerate legal player actions from the LO corner, filtered by the Question.
    BattleState lo_state = lo_corner_state(S, A);
    std::vector<ExecAction> actions = legal_player_actions(lo_state);

    bool any_indet = false;
    V bucket_verdict = V::FAIL;

    // Step 6/7: OR over actions.
    for (const ExecAction& action : actions) {
        if (!action_filter(S.q, action)) continue;

        ExpandResult r = S.cfg.expand_override
                             ? S.cfg.expand_override(A, action, S.ctx)
                             : expand(A, action, S.ctx);

        // Aggregate telemetry.
        S.result.stats.expand_calls++;
        S.result.stats.replays      += r.stats.replays;
        S.result.stats.oracle_leaves += r.stats.leaves;

        if (r.concession_tag != 0) {
            tally_concession(S, r.concession_tag);
            continue;   // conceded action FAILs definitively
        }

        if (r.children.empty()) {
            // Non-conceded expansion must yield at least one child (fail loud).
            throw std::logic_error(
                "bucket_win_certify: expand produced no children with concession_tag=0");
        }

        V av = and_over_children(S, r, depth);
        if (av == V::WIN) {
            bucket_verdict = V::WIN;
            S.result.policy[key] = action;
            break;   // OR: first winning action suffices
        }
        if (av == V::INDET) any_indet = true;
        // FAIL action: keep trying other actions.
    }

    S.stack.erase(key);

    // Step 7 resolution: WIN if any action won; else INDET if any action was
    // indeterminate; else FAIL (all actions FAILed definitively).
    if (bucket_verdict == V::WIN) return V::WIN;
    return any_indet ? V::INDET : V::FAIL;
}

// ---------------------------------------------------------------------------
// Dedicated-stack pthread trampoline (bsolver pattern).
// ---------------------------------------------------------------------------

struct WinThreadArgs {
    WinState*          S;
    const Bucket*      root;
    V                  result    = V::FAIL;
    std::exception_ptr exception = nullptr;
};

void* win_thread_fn(void* arg) {
    auto* a = static_cast<WinThreadArgs*>(arg);
    try {
        a->result = dfs(*a->S, *a->root, 0);
    } catch (...) {
        a->exception = std::current_exception();
    }
    return nullptr;
}

}  // namespace

// ---------------------------------------------------------------------------
// Public entry point.
// ---------------------------------------------------------------------------

BucketWinResult bucket_win_certify(const BattleState& initial_state, const Question& q,
                                   const BucketWinConfig& cfg) {
    // Root terminal shortcut (no thread spawn): classify the concrete initial state.
    {
        Outcome oc = classify(initial_state, q);
        if (oc == Outcome::WIN) {
            BucketWinResult r;
            r.verdict = BucketWinVerdict::WIN;
            return r;
        }
        if (oc == Outcome::LOSS) {
            BucketWinResult r;
            r.verdict = BucketWinVerdict::FAIL;
            return r;
        }
    }

    auto S = std::make_unique<WinState>(q, cfg);

    // Instantiate the breakpoint set and wire the persistent ExpandContext.
    S->bp = S->registry.instantiate(initial_state, q);
    S->ctx.oracle   = &S->oracle;
    S->ctx.interner = &S->interner;
    S->ctx.bp       = &S->bp;
    S->ctx.concede  = concede_tags;
    S->ctx.options  = ExpandOptions{};

    // Root bucket: singleton HP intervals at the concrete initial HP. d = context id;
    // support_fp is the canonical support fingerprint (MUST pair pack + support per
    // expand.h). support_fingerprint over cpp_compute_action_probabilities(state, 1).
    PackedKey root_key = S->interner.pack(initial_state);
    uint32_t  root_d   = ctx_id_of(root_key);
    int32_t   pl_hp    = pl_hp_of(root_key);
    int32_t   op_hp    = opp_hp_of(root_key);
    uint64_t  root_fp  = support_fingerprint(
        cpp_compute_action_probabilities(initial_state, 1));

    Bucket root(root_d, HpInterval{pl_hp, pl_hp}, HpInterval{op_hp, op_hp}, root_fp, S->bp);

    // Run the DFS on a dedicated-stack thread; measure wall-clock across spawn/join.
    WinThreadArgs args;
    args.S    = S.get();
    args.root = &root;

    auto t0 = std::chrono::steady_clock::now();

    pthread_attr_t attr;
    int rc = pthread_attr_init(&attr);
    if (rc != 0)
        throw std::runtime_error("bucket_win_certify: pthread_attr_init failed: "
                                 + std::to_string(rc));
    rc = pthread_attr_setstacksize(&attr, cfg.stack_size);
    if (rc != 0) {
        pthread_attr_destroy(&attr);
        throw std::runtime_error("bucket_win_certify: pthread_attr_setstacksize failed: "
                                 + std::to_string(rc));
    }
    pthread_t thread;
    rc = pthread_create(&thread, &attr, win_thread_fn, &args);
    pthread_attr_destroy(&attr);
    if (rc != 0)
        throw std::runtime_error("bucket_win_certify: pthread_create failed: "
                                 + std::to_string(rc));
    rc = pthread_join(thread, nullptr);
    if (rc != 0)
        throw std::runtime_error("bucket_win_certify: pthread_join failed: "
                                 + std::to_string(rc));

    auto t1 = std::chrono::steady_clock::now();

    // Propagate any worker-thread exception to the caller.
    if (args.exception) std::rethrow_exception(args.exception);

    S->result.stats.elapsed_us =
        std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0).count();

    switch (args.result) {
    case V::WIN:
        S->result.verdict = BucketWinVerdict::WIN;
        S->result.reason  = BucketWinIndetReason::None;
        break;
    case V::INDET:
        S->result.verdict = BucketWinVerdict::INDETERMINATE;
        S->result.reason  = S->first_reason;
        break;
    case V::FAIL:
    default:
        S->result.verdict = BucketWinVerdict::FAIL;
        S->result.reason  = BucketWinIndetReason::None;
        break;
    }

    return std::move(S->result);
}
