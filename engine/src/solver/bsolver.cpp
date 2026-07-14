// Exact AND-OR boolean certifier over the transition oracle.
// Interleaved enumeration: each child is recursed inside the oracle emit callback;
// the oracle call aborts immediately on the first losing child (AdverseFirst ordering).
// Memo geometry: per-context (ctx_id) planes over (plHP × oppHP) — two flat 2D bit
// arrays (WIN plane and LOSS plane) sized dynamically to the observed HP range.
// b_win runs on a dedicated pthread with a configurable stack (default 256 MB) so
// depth_cap=500 is safe: each level uses ~100 KB of stack (BattleState copies in the
// oracle DFS frames), and 500 × 100 KB = 50 MB, well within the 256 MB budget.
#include "solver/bsolver.h"

#include "solver/action_space.h"
#include "solver/oracle_types.h"
#include "solver/question.h"
#include "solver/state_codec.h"
#include "solver/transition_oracle.h"

#include <exception>
#include <pthread.h>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// ---------------------------------------------------------------------------
// Per-context bitmap plane: decided-WIN and decided-LOSS bits over (plHP, oppHP).
// HP values are uint16 (≤65535). We use a flat hash map as the backing store
// rather than a full 65536×65536 bitmap (that's 512 MB each). The plane is
// sparse in practice; a hash map of (plHP<<16|oppHP) → 2-bit value is compact.
// This matches the spec ("bitmap planes keyed by exact (plHP,oppHP)") — a hash
// map implements that logical structure without the impractical allocation.
// ---------------------------------------------------------------------------
struct BitmapPlane {
    // Packed key: (plHP << 16) | oppHP.  Bit 0 = WIN, bit 1 = LOSS.
    std::unordered_map<uint32_t, uint8_t> bits;

    static uint32_t key(uint16_t plHP, uint16_t oppHP) {
        return (static_cast<uint32_t>(plHP) << 16) | static_cast<uint32_t>(oppHP);
    }

    bool is_win(uint16_t plHP, uint16_t oppHP) const {
        auto it = bits.find(key(plHP, oppHP));
        return it != bits.end() && (it->second & 1);
    }
    bool is_loss(uint16_t plHP, uint16_t oppHP) const {
        auto it = bits.find(key(plHP, oppHP));
        return it != bits.end() && (it->second & 2);
    }
    void set_win(uint16_t plHP, uint16_t oppHP) {
        bits[key(plHP, oppHP)] |= 1;
    }
    void set_loss(uint16_t plHP, uint16_t oppHP) {
        bits[key(plHP, oppHP)] |= 2;
    }
};

// ---------------------------------------------------------------------------
// Per-certify-call solver state.
// ---------------------------------------------------------------------------
struct BsolverState {
    TransitionOracle   oracle;
    ContextInterner    interner;
    // Per-context bitmap planes: ctx_id → plane.
    std::unordered_map<uint32_t, BitmapPlane> planes;
    // Recursion stack: set of PackedKeys currently being expanded (for cycle detection).
    std::unordered_set<PackedKey> stack;
    // Cached config.
    const Question&      q;
    const BsolverConfig& cfg;
    TransitionOracle::Config oracle_cfg;
    // Stats.
    uint64_t nodes_expanded    = 0;
    uint64_t oracle_step_calls = 0;
    uint64_t memo_hits         = 0;

    // Reason if we short-circuit with INDETERMINATE.
    BIndeterminateReason early_stop = BIndeterminateReason::None;
    // Ancestor key that closed a cycle; valid iff early_stop == Cycle.
    PackedKey cycle_key = 0;

    // Policy: WIN states → chosen action.
    std::unordered_map<PackedKey, ExecAction> policy;

    explicit BsolverState(const Question& q_, const BsolverConfig& cfg_)
        : q(q_), cfg(cfg_) {
        oracle_cfg.max_leaves             = cfg_.oracle_max_leaves;
        oracle_cfg.aggregate_damage_rolls = true;
        // Map BMode → CollapseMode. Exact = None (unchanged behavior, bit-for-bit identical).
        switch (cfg_.mode) {
        case BMode::Exact:
            oracle_cfg.collapse = TransitionOracle::CollapseMode::None;
            break;
        case BMode::Pessimal:
            oracle_cfg.collapse = TransitionOracle::CollapseMode::Pessimal;
            break;
        case BMode::Coarse:
            oracle_cfg.collapse = TransitionOracle::CollapseMode::Coarse;
            break;
        }
    }

    BitmapPlane& plane_for(uint32_t ctx_id) {
        return planes[ctx_id];
    }

    // Lookup a packed key in the memo planes. Returns true and sets *win if decided.
    bool memo_lookup(PackedKey key, bool& win_out) {
        uint32_t ctx = ctx_id_of(key);
        uint16_t plHP  = pl_hp_of(key);
        uint16_t oppHP = opp_hp_of(key);
        auto it = planes.find(ctx);
        if (it == planes.end()) return false;
        const BitmapPlane& p = it->second;
        if (p.is_win(plHP, oppHP))  { win_out = true;  return true; }
        if (p.is_loss(plHP, oppHP)) { win_out = false; return true; }
        return false;
    }
};

// Forward declaration.
static bool b_win(BsolverState& S, const BattleState& state, int depth);

// ---------------------------------------------------------------------------
// Core AND-OR recursion.
// Returns true = WIN, false = LOSS.
// Sets S.early_stop (non-None) and returns false on any INDETERMINATE condition.
// ---------------------------------------------------------------------------
static bool b_win(BsolverState& S, const BattleState& state, int depth) {
    // Terminals: classify() decides WIN/LOSS immediately.
    Outcome oc = classify(state, S.q);
    if (oc == Outcome::WIN)  return true;
    if (oc == Outcome::LOSS) return false;
    // CONTINUE: non-terminal, recurse.

    // Depth cap.
    if (depth >= S.cfg.depth_cap) {
        S.early_stop = BIndeterminateReason::DepthCap;
        return false;
    }

    // Pack the state for memo / cycle checks.
    PackedKey key = S.interner.pack(state);
    uint32_t  ctx = ctx_id_of(key);

    // Memo lookup.
    {
        bool w;
        if (S.memo_lookup(key, w)) {
            ++S.memo_hits;
            return w;
        }
    }

    // Cycle detection: is this key currently on the recursion stack?
    if (S.stack.count(key)) {
        // Non-parent ancestor on the stack → INDETERMINATE(Cycle).
        S.early_stop = BIndeterminateReason::Cycle;
        S.cycle_key  = key;
        return false;
    }

    // Node cap.
    if (S.nodes_expanded >= S.cfg.node_cap) {
        S.early_stop = BIndeterminateReason::NodeCap;
        return false;
    }
    ++S.nodes_expanded;

    S.stack.insert(key);

    // Enumerate legal player actions, filtered by Question.
    std::vector<ExecAction> actions = legal_player_actions(state);

    bool any_action_wins = false;
    ExecAction winning_action{};

    for (const ExecAction& action : actions) {
        if (!action_filter(S.q, action)) continue;

        // OR node: try this action. Abort the oracle enum on the first LOSS child.
        // An action WINs iff all p>0 non-self-loop children WIN.
        bool action_wins = true;
        bool has_non_self = false;   // must have at least one non-self child

        ++S.oracle_step_calls;
        StepStats stats = S.oracle.step(
            state, action,
            [&](ChildOutcome co) -> bool {
                // Pack child and check for self-loop.
                PackedKey child_key = S.interner.pack(co.child);

                // Self-loop: child is same state as parent → skip (neither win nor loss).
                if (child_key == key) return true;

                has_non_self = true;

                // Recurse into child (interleaved enumeration).
                bool child_win = b_win(S, co.child, depth + 1);

                if (S.early_stop != BIndeterminateReason::None) {
                    // Propagate INDETERMINATE up: abort enumeration.
                    action_wins = false;
                    return false;
                }

                if (!child_win) {
                    // First losing child: abort enumeration for this action.
                    action_wins = false;
                    return false;
                }
                return true;  // continue enumeration
            },
            OrderingHint::AdverseFirst,
            S.oracle_cfg
        );

        // Budget exceeded → INDETERMINATE.
        if (stats.budget_exceeded) {
            S.early_stop = BIndeterminateReason::LeafBudget;
            action_wins = false;
        }

        // Propagate INDETERMINATE from children.
        if (S.early_stop != BIndeterminateReason::None) {
            S.stack.erase(key);
            return false;
        }

        // An action whose p>0 children are ALL self-loops fails (no progress).
        if (!has_non_self) action_wins = false;

        if (action_wins) {
            any_action_wins = true;
            winning_action  = action;
            break;  // AND-OR: one winning action is sufficient
        }
    }

    S.stack.erase(key);

    // Memoize the decided verdict.
    BitmapPlane& p = S.plane_for(ctx);
    uint16_t plHP  = pl_hp_of(key);
    uint16_t oppHP = opp_hp_of(key);
    if (any_action_wins) {
        p.set_win(plHP, oppHP);
        S.policy[key] = winning_action;
    } else {
        p.set_loss(plHP, oppHP);
    }

    return any_action_wins;
}

// ---------------------------------------------------------------------------
// Thread trampoline for the dedicated-stack pthread.
// ---------------------------------------------------------------------------

struct BwinThreadArgs {
    BsolverState*      S;
    const BattleState* state;
    bool               result    = false;
    std::exception_ptr exception = nullptr;
};

static void* b_win_thread_fn(void* arg) {
    auto* a = static_cast<BwinThreadArgs*>(arg);
    try {
        a->result = b_win(*a->S, *a->state, 0);
    } catch (...) {
        a->exception = std::current_exception();
    }
    return nullptr;
}

// ---------------------------------------------------------------------------
// Public entry point.
// ---------------------------------------------------------------------------
BsolverResult bsolver_certify(const BattleState& state,
                               const Question& q,
                               const BsolverConfig& cfg) {
    BsolverResult result{};

    BsolverState S(q, cfg);

    // Handle terminals before any recursion (avoids spawning a thread for trivial cases).
    Outcome oc = classify(state, q);
    if (oc == Outcome::WIN) {
        result.verdict = BVerdict::WIN;
        result.reason  = BIndeterminateReason::None;
        return result;
    }
    if (oc == Outcome::LOSS) {
        result.verdict = BVerdict::LOSS;
        result.reason  = BIndeterminateReason::None;
        return result;
    }

    // Run b_win on a dedicated pthread with an explicit stack size so deep recursion
    // (depth_cap=500, ~100 KB/level) never overflows the default 8 MB OS stack.
    BwinThreadArgs args;
    args.S     = &S;
    args.state = &state;

    pthread_attr_t attr;
    int rc = pthread_attr_init(&attr);
    if (rc != 0)
        throw std::runtime_error("bsolver_certify: pthread_attr_init failed: " + std::to_string(rc));

    rc = pthread_attr_setstacksize(&attr, cfg.stack_size);
    if (rc != 0) {
        pthread_attr_destroy(&attr);
        throw std::runtime_error("bsolver_certify: pthread_attr_setstacksize failed: " + std::to_string(rc));
    }

    pthread_t thread;
    rc = pthread_create(&thread, &attr, b_win_thread_fn, &args);
    pthread_attr_destroy(&attr);
    if (rc != 0)
        throw std::runtime_error("bsolver_certify: pthread_create failed: " + std::to_string(rc));

    rc = pthread_join(thread, nullptr);
    if (rc != 0)
        throw std::runtime_error("bsolver_certify: pthread_join failed: " + std::to_string(rc));

    // Propagate exceptions from the worker thread to the caller.
    if (args.exception)
        std::rethrow_exception(args.exception);

    bool win = args.result;

    result.nodes_expanded    = S.nodes_expanded;
    result.oracle_step_calls = S.oracle_step_calls;
    result.memo_hits         = S.memo_hits;

    if (S.early_stop != BIndeterminateReason::None) {
        result.verdict   = BVerdict::INDETERMINATE;
        result.reason    = S.early_stop;
        result.cycle_key = S.cycle_key;
        return result;
    }

    result.verdict = win ? BVerdict::WIN : BVerdict::LOSS;
    result.reason  = BIndeterminateReason::None;
    result.policy  = std::move(S.policy);
    return result;
}
