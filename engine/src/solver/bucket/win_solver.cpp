// bucket_win_certify — Solver B DFS core (spec §6 / plan Task 7). Tri-valued recursion
// over Expand's AND-set children; OR over legal player actions. On-stack repeated bucket
// = FAIL (amendment 16(a), deliberately diverging from bsolver's INDETERMINATE(Cycle)).
// Runs on a dedicated-stack pthread (bsolver pattern): exceptions captured via
// exception_ptr and rethrown on the caller thread after join.
#include "solver/bucket/win_solver.h"

#include "ai_analytic.h"                 // cpp_compute_action_probabilities
#include "effects_consts.h"              // AB_PRESSURE
#include "solver/action_space.h"         // legal_player_actions
#include "solver/bucket/breakpoints.h"
#include "solver/bucket/concede.h"       // concede_tags
#include "solver/bucket/pp_canon.h"      // canonicalize_pp, pp_horizon, cert audit (Tasks 2-3)
#include "solver/bucket/transition_cache.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"

#include <algorithm>
#include <chrono>
#include <exception>
#include <limits>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#include <unordered_map>
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

// Sentinel lowlink meaning "no on-stack ancestor referenced by this subtree".
constexpr int kLowlinkInf = std::numeric_limits<int>::max();

// One DFS return: the tri-valued verdict plus the Tarjan-style lowlink (min on-stack
// depth referenced anywhere in the subtree, kLowlinkInf if none). See win_solver.h.
struct DfsResult {
    V   verdict;
    int lowlink;
};

// Per-certify-call solver state (threaded through the DFS). The edge cache (owning the
// oracle + interner) is external when cfg.cache is set, else privately owned.
struct WinState {
    TransitionCache*                 cache;        // active edge cache (external or owned)
    std::unique_ptr<TransitionCache> owned_cache;  // non-null iff cfg.cache was null
    BreakpointRegistry registry;
    BpSet              bp;
    uint64_t           bp_fp = 0;     // fingerprint of bp; edge-key scope (computed once)
    ExpandContext      ctx;           // one persistent context (interner mutated in place)

    const Question&         q;
    const BucketWinConfig&  cfg;

    // Buckets currently on the recursion stack -> their depth (on-stack repeat = FAIL,
    // with lowlink = the ancestor's depth for cycle-contamination tracking).
    std::unordered_map<BucketKey, int, BucketKeyHash> stack;

    // Per-question verdict memo: BucketKey -> win (WIN always cached; FAIL only when
    // uncontaminated; INDET never). Dies with this certify call.
    std::unordered_map<BucketKey, bool, BucketKeyHash> memo;
    // Secondary index by d for the rectangle-containment counter (measurement only).
    std::unordered_map<int32_t, std::vector<std::pair<BucketKey, bool>>> memo_by_d;

    // Effective depth cap: cfg.depth_cap, tightened to the real root's pp_horizon when
    // enable_pp_canon is set (PP-canon Task 2). Set once in bucket_win_certify.
    int effective_depth_cap = 0;

    // Sticky visit-cap flag: once tripped, every deeper call short-circuits to INDET.
    bool visit_cap_hit = false;
    // First cap reason observed (records DepthCap vs VisitCap).
    BucketWinIndetReason first_reason = BucketWinIndetReason::None;

    BucketWinResult result;

    ContextInterner& interner() { return cache->interner; }

    WinState(const Question& q_, const BucketWinConfig& cfg_) : q(q_), cfg(cfg_) {
        if (cfg.cache) {
            cache = cfg.cache;
        } else {
            owned_cache = std::make_unique<TransitionCache>();
            cache = owned_cache.get();
        }
    }
};

// Assemble the edge-cache key for (bucket, action) under the current BpSet scope.
EdgeKey make_edge_key(const BucketKey& key, uint64_t bp_fp, const ExecAction& a) {
    EdgeKey ek{};
    ek.bucket         = key;
    ek.bp_fp          = bp_fp;
    ek.kind           = a.kind;
    ek.move_slot      = a.move_slot;
    ek.move_override  = a.move_override;
    ek.switch_to_slot = a.switch_to_slot;
    ek.target_side    = a.target_side;
    ek.target_slot    = a.target_slot;
    ek.source_slot    = a.source_slot;
    ek.mega           = a.mega;
    return ek;
}

// Unpack the LO corner of a bucket into a concrete state. Legality of player actions
// depends only on d (context), not HP, so the LO corner is a valid enumeration point.
BattleState lo_corner_state(WinState& S, const Bucket& A) {
    PackedKey k = make_packed_key(A.d(),
                                  static_cast<uint16_t>(A.player_hp().lo),
                                  static_cast<uint16_t>(A.opp_hp().lo));
    return S.interner().unpack(k);
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

DfsResult dfs(WinState& S, const Bucket& A, int depth);

// Perform one real expansion (override seam intercepts every real expand) and accumulate
// its work telemetry. Called only on an edge-cache MISS (or when caching is disabled).
ExpandResult do_expand(WinState& S, const Bucket& A, const ExecAction& action) {
    ExpandResult r = S.cfg.expand_override
                         ? S.cfg.expand_override(A, action, S.ctx)
                         : expand(A, action, S.ctx);
    S.result.stats.expand_calls++;
    S.result.stats.replays       += r.stats.replays;
    S.result.stats.oracle_leaves += r.stats.leaves;
    return r;
}

// Obtain the ExpandResult for (A, action). With edge caching on, consult/populate the
// shared cache (hit = no real work); with it off, expand into `local`. The returned
// pointer stays valid for the caller's use (unordered_map references are insert-stable;
// `local` outlives the call site).
const ExpandResult* edge_expand(WinState& S, const Bucket& A, const BucketKey& key,
                                const ExecAction& action, ExpandResult& local) {
    if (!S.cfg.enable_edge_cache) {
        local = do_expand(S, A, action);
        return &local;
    }
    EdgeKey ek = make_edge_key(key, S.bp_fp, action);
    if (const ExpandResult* hit = S.cache->lookup(ek)) {
        S.result.stats.edge_hits++;
        return hit;   // reuse: NO real work counted
    }
    S.result.stats.edge_misses++;
    ExpandResult fresh = do_expand(S, A, action);
    S.cache->insert(ek, fresh);   // copy into cache
    local = std::move(fresh);
    return &local;
}

// Persist a decided verdict to the memo (+ the by-d secondary index for containment).
void store_memo(WinState& S, const BucketKey& key, bool win) {
    S.memo[key] = win;
    S.memo_by_d[static_cast<int32_t>(key.d)].push_back({key, win});
    S.result.stats.memo_stores++;
}

// Measurement only: on an exact memo miss, count queries that a rectangle-aware memo
// WOULD have covered (a same-d cached WIN whose rectangle contains the query, or a same-d
// cached FAIL whose rectangle is contained by the query). The verdict is NOT taken from it.
void containment_scan(WinState& S, const BucketKey& q) {
    auto it = S.memo_by_d.find(static_cast<int32_t>(q.d));
    if (it == S.memo_by_d.end()) return;
    for (const auto& [k, win] : it->second) {
        bool covered =
            win ? (k.pl_lo <= q.pl_lo && k.pl_hi >= q.pl_hi
                   && k.op_lo <= q.op_lo && k.op_hi >= q.op_hi)
                : (k.pl_lo >= q.pl_lo && k.pl_hi <= q.pl_hi
                   && k.op_lo >= q.op_lo && k.op_hi <= q.op_hi);
        if (covered) {
            S.result.stats.memo_containment_missed++;
            return;
        }
    }
}

// AND over one action's children: WIN iff every child WINs; the first non-WIN child
// decides. lowlink is the min over every child actually evaluated.
DfsResult and_over_children(WinState& S, const ExpandResult& r, int depth) {
    int low = kLowlinkInf;
    for (const ChildBucket& child : r.children) {
        DfsResult cr = dfs(S, child.bucket, depth + 1);
        low = std::min(low, cr.lowlink);
        if (cr.verdict != V::WIN) return {cr.verdict, low};   // first non-WIN decides
    }
    return {V::WIN, low};
}

DfsResult dfs(WinState& S, const Bucket& A, int depth) {
    S.result.stats.buckets_visited++;
    if (depth > S.result.stats.max_depth) S.result.stats.max_depth = depth;

    // Step 1: terminal classification (verdict independent of depth/cycle → lowlink +INF).
    Outcome oc = classify_bucket(A, S.q, S.interner());
    if (oc != Outcome::CONTINUE) {
        S.result.stats.terminal_buckets++;
        return {oc == Outcome::WIN ? V::WIN : V::FAIL, kLowlinkInf};
    }

    BucketKey key = key_of(A);

    // Step 2: verdict memo lookup (decided entries are depth-independent → lowlink +INF).
    if (S.cfg.enable_verdict_memo) {
        auto it = S.memo.find(key);
        if (it != S.memo.end()) {
            S.result.stats.memo_hits++;
            return {it->second ? V::WIN : V::FAIL, kLowlinkInf};
        }
        containment_scan(S, key);   // exact miss → measure rectangle coverage
    }

    // Step 3: depth cap (tightened to pp_horizon under PP-canon).
    if (depth >= S.effective_depth_cap) {
        record_reason(S, BucketWinIndetReason::DepthCap);
        return {V::INDET, kLowlinkInf};
    }

    // Step 4: on-stack repeated bucket → FAIL (amendment 16(a)); lowlink = ancestor depth.
    // Counted unconditionally: previously reachable only via test overrides, now the
    // canonical heal-stall collapse makes it a live path.
    if (auto sit = S.stack.find(key); sit != S.stack.end()) {
        S.result.stats.canonical_repeats++;
        return {V::FAIL, sit->second};
    }

    // Step 5: sticky visit cap → INDET.
    if (S.visit_cap_hit || S.result.stats.buckets_visited > S.cfg.visit_cap) {
        S.visit_cap_hit = true;
        record_reason(S, BucketWinIndetReason::VisitCap);
        return {V::INDET, kLowlinkInf};
    }

    S.stack.emplace(key, depth);

    // Step 6: enumerate legal player actions from the LO corner, filtered by the Question.
    BattleState lo_state = lo_corner_state(S, A);
    std::vector<ExecAction> actions = legal_player_actions(lo_state);

    bool any_indet = false;
    V    bucket_verdict = V::FAIL;
    int  node_lowlink   = kLowlinkInf;

    // Step 7: OR over actions.
    for (const ExecAction& action : actions) {
        if (!action_filter(S.q, action)) continue;

        ExpandResult local;
        const ExpandResult* r = edge_expand(S, A, key, action, local);

        if (r->concession_tag != 0) {
            tally_concession(S, r->concession_tag);
            continue;   // conceded action FAILs definitively
        }

        if (r->children.empty()) {
            // Non-conceded expansion must yield at least one child (fail loud).
            throw std::logic_error(
                "bucket_win_certify: expand produced no children with concession_tag=0");
        }

        DfsResult av = and_over_children(S, *r, depth);
        node_lowlink = std::min(node_lowlink, av.lowlink);
        if (av.verdict == V::WIN) {
            bucket_verdict = V::WIN;
            S.result.policy[key] = action;
            break;   // OR: first winning action suffices
        }
        if (av.verdict == V::INDET) any_indet = true;
        // FAIL action: keep trying other actions.
    }

    S.stack.erase(key);

    // Step 7 resolution: WIN if any action won; else INDET if any action was
    // indeterminate; else FAIL (all actions FAILed definitively).
    V verdict = bucket_verdict == V::WIN ? V::WIN
              : any_indet             ? V::INDET
                                      : V::FAIL;

    // Memoize: WIN always; FAIL iff uncontaminated by an on-stack cycle; INDET never.
    if (S.cfg.enable_verdict_memo) {
        if (verdict == V::WIN) {
            store_memo(S, key, true);
        } else if (verdict == V::FAIL) {
            if (node_lowlink >= depth) store_memo(S, key, false);
            else S.result.stats.memo_suppressed++;
        }
    }

    // A WIN proof is independent of any pruned contaminated branch → +INF upward.
    int out_lowlink = verdict == V::WIN ? kLowlinkInf : node_lowlink;
    return {verdict, out_lowlink};
}

// ---------------------------------------------------------------------------
// Certificate PP-use audit (PP-canon Task 3). After a WIN, walk the winning certificate
// (policy action -> edge-cache children -> non-terminal child buckets) into a PpCertGraph,
// then require every masked slot's max path-wise consumption strictly below its real root
// PP. A violation downgrades WIN to INDETERMINATE(PpAuditFail). Runs on the DFS worker
// thread (its dedicated stack) so the recursive walk cannot overflow the caller stack.
// ---------------------------------------------------------------------------

// Consumption cost of one action on its own slot: 0 for switch / Struggle / recharge
// (move_slot < 0), else 1, doubled to 2 when the OPPOSING active mon has Pressure.
int32_t action_pp_cost(const ExecAction& a, bool opposing_pressure) {
    if (a.kind != 0 || a.move_slot < 0) return 0;   // kind 0 = MOVE
    return opposing_pressure ? 2 : 1;
}

// Snapshot real (pre-canon) PP + move id for every move slot of every mon on both sides.
PpRootPp snapshot_root_pp(const BattleState& s) {
    PpRootPp out;
    auto add_side = [&](const SideState& side, int32_t side_idx) {
        for (std::size_t mon = 0; mon < side.team.size(); ++mon) {
            const PokemonState& m = side.team[mon];
            const int32_t ids[4] = {m.move_id0, m.move_id1, m.move_id2, m.move_id3};
            const int32_t pps[4] = {m.move_pp0, m.move_pp1, m.move_pp2, m.move_pp3};
            for (int32_t slot = 0; slot < 4; ++slot)
                out[PpSlotKey{side_idx, static_cast<int32_t>(mon), slot}] =
                    PpRootSlot{pps[slot], ids[slot]};
        }
    };
    add_side(s.side0, 0);
    add_side(s.side1, 1);
    return out;
}

// Obtain the ExpandResult for (A, action) during the audit walk WITHOUT perturbing search
// telemetry: an edge-cache hit reuses the search's expansion; a miss (edge caching disabled
// or an override bypassed the cache) re-expands and is counted in audit_expands.
const ExpandResult* audit_edge(WinState& S, const Bucket& A, const BucketKey& key,
                               const ExecAction& action, ExpandResult& local) {
    if (S.cfg.enable_edge_cache) {
        EdgeKey ek = make_edge_key(key, S.bp_fp, action);
        if (const ExpandResult* hit = S.cache->lookup(ek)) return hit;
    }
    local = S.cfg.expand_override ? S.cfg.expand_override(A, action, S.ctx)
                                  : expand(A, action, S.ctx);
    S.result.stats.audit_expands++;
    return &local;
}

// Build (memoized) the certificate DAG node for WIN bucket A. THROWS std::logic_error on an
// on-stack revisit (a cycle in a WIN certificate is impossible if sound — fail loud); a
// cross-branch revisit (DAG diamond) returns the already-built node index.
int build_cert_node(WinState& S, PpCertGraph& g,
                    std::unordered_map<BucketKey, int, BucketKeyHash>& built,
                    std::unordered_set<BucketKey, BucketKeyHash>& on_stack,
                    const Bucket& A) {
    BucketKey key = key_of(A);
    if (on_stack.count(key))
        throw std::logic_error("bucket_win_certify: cycle in WIN certificate during PP audit");
    if (auto it = built.find(key); it != built.end()) return it->second;

    auto pit = S.result.policy.find(key);
    if (pit == S.result.policy.end())
        throw std::logic_error(
            "bucket_win_certify: WIN certificate node missing a policy entry during PP audit");
    const ExecAction& action = pit->second;

    on_stack.insert(key);

    // Unpack the bucket's LO corner to read active mon indices + Pressure on both sides.
    BattleState st = S.interner().unpack(make_packed_key(
        key.d, static_cast<uint16_t>(key.pl_lo), static_cast<uint16_t>(key.op_lo)));
    int32_t pl_active = st.side0.active_indices[0];
    int32_t op_active = st.side1.active_indices[0];
    bool op_pressure = st.side1.team[op_active].ability == eff::AB_PRESSURE;
    bool pl_pressure = st.side0.team[pl_active].ability == eff::AB_PRESSURE;

    PpCertNode node;
    node.player_slot = PpSlotKey{0, pl_active, action.move_slot};
    node.player_cost = action_pp_cost(action, op_pressure);

    ExpandResult local;
    const ExpandResult* r = audit_edge(S, A, key, action, local);
    for (const ChildBucket& child : r->children) {
        PpCertEdge e;
        e.opp_slot = PpSlotKey{1, op_active, child.ai_action.move_slot};
        e.opp_cost = action_pp_cost(child.ai_action, pl_pressure);
        Outcome oc = classify_bucket(child.bucket, S.q, S.interner());
        e.child = (oc == Outcome::WIN) ? -1   // terminal WIN leaf: stop recursion
                                       : build_cert_node(S, g, built, on_stack, child.bucket);
        node.children.push_back(e);
    }

    on_stack.erase(key);
    int idx = static_cast<int>(g.nodes.size());
    g.nodes.push_back(std::move(node));
    built[key] = idx;
    return idx;
}

// Audit the WIN certificate rooted at `root`. Returns true iff the WIN survives (every masked
// slot's max consumption strictly below its real root PP). real_state is the pre-canon state.
bool pp_cert_audit(WinState& S, const Bucket& root, const BattleState& real_state) {
    // A non-terminal WIN root always carries a policy entry; without one there is nothing
    // consumed to audit.
    if (!S.result.policy.count(key_of(root))) return true;

    PpCertGraph g;
    std::unordered_map<BucketKey, int, BucketKeyHash> built;
    std::unordered_set<BucketKey, BucketKeyHash> on_stack;
    g.root = build_cert_node(S, g, built, on_stack, root);

    PpConsumption consumption = pp_max_consumption(g);
    return pp_cert_audit_ok(consumption, snapshot_root_pp(real_state));
}

// ---------------------------------------------------------------------------
// Dedicated-stack pthread trampoline (bsolver pattern).
// ---------------------------------------------------------------------------

struct WinThreadArgs {
    WinState*          S;
    const Bucket*      root;
    const BattleState* real_state = nullptr;  // pre-canon state for the PP audit
    V                  result    = V::FAIL;
    std::exception_ptr exception = nullptr;
};

void* win_thread_fn(void* arg) {
    auto* a = static_cast<WinThreadArgs*>(arg);
    try {
        a->result = dfs(*a->S, *a->root, 0).verdict;
        // Certificate PP-use audit (Task 3): a masked-slot over-use downgrades WIN to
        // INDETERMINATE(PpAuditFail). Policy is deliberately left intact for diagnostics.
        if (a->result == V::WIN && a->S->cfg.enable_pp_canon
            && !pp_cert_audit(*a->S, *a->root, *a->real_state)) {
            a->S->result.stats.pp_audit_rejects = 1;
            a->S->first_reason = BucketWinIndetReason::PpAuditFail;
            a->result = V::INDET;
        }
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

    // PP-canon regime (Task 2): bind the cache to canonical/exact once (throws on a mismatched
    // shared cache), snapshot the REAL root's PP horizon, and tighten the effective depth cap.
    S->cache->require_mode(cfg.enable_pp_canon ? TransitionCache::Mode::Canonical
                                               : TransitionCache::Mode::Exact);
    S->effective_depth_cap = cfg.depth_cap;
    if (cfg.enable_pp_canon) {
        int32_t horizon = pp_horizon(initial_state);
        S->result.stats.pp_horizon_used = horizon;
        S->effective_depth_cap = std::min(cfg.depth_cap, horizon);
    }

    // Instantiate the breakpoint set and wire the persistent ExpandContext to the cache's
    // oracle + interner. bp_fp scopes edge-cache keys and is computed once per certify.
    S->bp    = S->registry.instantiate(initial_state, q);
    S->bp_fp = bp_fingerprint(S->bp);
    S->ctx.oracle          = &S->cache->oracle;
    S->ctx.interner        = &S->cache->interner;
    S->ctx.bp              = &S->bp;
    S->ctx.concede         = concede_tags;
    S->ctx.options         = ExpandOptions{};
    S->ctx.canonicalize_pp = cfg.enable_pp_canon;

    // Root pack/intern uses a PP-canonicalized copy when canonicalizing, so the root context
    // d matches the canonical child contexts. Terminal classify above stayed on the real state.
    BattleState root_state = initial_state;
    if (cfg.enable_pp_canon) canonicalize_pp(root_state);

    // Root bucket: singleton HP intervals at the concrete initial HP. d = context id;
    // support_fp is the canonical support fingerprint (MUST pair pack + support per
    // expand.h). support_fingerprint over cpp_compute_action_probabilities(state, 1).
    PackedKey root_key = S->cache->interner.pack(root_state);
    uint32_t  root_d   = ctx_id_of(root_key);
    int32_t   pl_hp    = pl_hp_of(root_key);
    int32_t   op_hp    = opp_hp_of(root_key);
    uint64_t  root_fp  = support_fingerprint(
        cpp_compute_action_probabilities(root_state, 1));

    Bucket root(root_d, HpInterval{pl_hp, pl_hp}, HpInterval{op_hp, op_hp}, root_fp, S->bp);

    // Run the DFS on a dedicated-stack thread; measure wall-clock across spawn/join.
    WinThreadArgs args;
    args.S          = S.get();
    args.root       = &root;
    args.real_state = &initial_state;

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
