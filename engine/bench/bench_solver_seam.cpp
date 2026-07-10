// D5 seam benchmark: measures the costs that matter for the RNG-bucketing solver and
// the eventual Stage E sweep re-point, on a REAL representative BattleState loaded from
// a golden-trace-derived payload (SCRIPTS/gen_seam_payload.py -> /tmp/d5_seam_payload.json).
// Standalone (no Python/pybind); NOT registered with ctest so it never slows correctness.
//
// Metrics (single-threaded, Release/-O2, machine-specific — label as such in reports):
//   1. per-turn direct cost   : cpp_run_one_turn_solver (the solver hot path; no JSON).
//   2. state copy throughput  : BattleState memcpy-able copy (the D2 win).
//   3. NodePool throughput    : allocate()+copy and emplace() into the slab allocator.
//   4. JSON round-trip cost   : battle_state_to_json + battle_state_from_json (bridge overhead).
//   5. state_hash_solver cost : the per-node hash the solver computes on every state.
// Then derives per-boundary projections at _SWEEP_BRANCH_CAP=1000 full-turn sims for the
// direct path vs a JSON-bridge-per-turn path, so the report shows if codec is material.
//
// D5 batched-API decision (deferred): the codec dominates the bridge (~63-138 us/state),
// but a batched entry (iter_damage_configs idiom) amortizes only the PER-CROSSING pybind
// fixed cost (~53 ns, measured) across N — it still decodes each state, so it does NOT
// remove the codec cost. The already-built D4 direct path (cpp_run_one_turn_solver) is the
// real win: it keeps states resident in C++ and pays zero JSON. So the correct Stage E
// design is resident-state + direct turns, not a batched JSON API. Groundwork deferred.
//
// Usage: bench_solver_seam [iters] [payload_path]
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "codec.h"
#include "core_leaf.h"          // TurnLuck
#include "move_exec.h"          // ExecAction
#include "move_exec_damage.h"   // DamageLoopLuck
#include "node_pool.h"
#include "oracle.h"             // OracleOverrides
#include "solver_turn.h"        // cpp_run_one_turn_solver
#include "state.h"
#include "state_eq.h"           // state_hash_solver

namespace {

// _SWEEP_BRANCH_CAP in the frozen liveplay sweep (src/simulation_runner.py:81): ~1000
// full-turn sims per decision boundary. The projection scale factor.
constexpr long kSweepBranchCap = 1000;

using Clock = std::chrono::steady_clock;

double seconds_since(Clock::time_point t0) {
    return std::chrono::duration<double>(Clock::now() - t0).count();
}

std::string read_state_json(const std::string& path) {
    std::ifstream f(path);
    if (!f) {
        std::fprintf(stderr,
                     "cannot open %s (run: .venv/bin/python SCRIPTS/gen_seam_payload.py)\n",
                     path.c_str());
        std::exit(1);
    }
    std::stringstream ss;
    ss << f.rdbuf();
    nlohmann::json j = nlohmann::json::parse(ss.str());
    return j["state"].dump();
}

ExecAction move_action(int move_slot, int source_slot) {
    ExecAction e;
    e.kind = 0;  // AK_MOVE
    e.move_slot = move_slot;
    e.source_slot = source_slot;
    return e;
}

// Run one clean solver turn on a fresh copy of base; return whether it executed without
// an unresolved oracle pause. Reports honestly which action regime the harness landed on.
bool try_solver_turn(const BattleState& base,
                     const std::vector<ExecAction>& a0,
                     const std::vector<ExecAction>& a1,
                     std::string* err) {
    BattleState s = base;
    DamageLoopLuck lp0{}, lp1{};
    TurnLuck tl0{}, tl1{};
    OracleOverrides ov;
    SolverTurnResult r =
        cpp_run_one_turn_solver(s, a0, a1, lp0, lp1, tl0, tl1, false, false, ov);
    if (!r.ok) *err = r.error;
    return r.ok;
}

}  // namespace

int main(int argc, char** argv) {
    long iters = (argc > 1) ? std::atol(argv[1]) : 200000;
    std::string payload_path =
        (argc > 2) ? argv[2] : "/tmp/d5_seam_payload.json";

    std::string state_json = read_state_json(payload_path);
    BattleState base = battle_state_from_json(state_json);

    std::printf("=== D5 seam benchmark ===\n");
    std::printf("payload            : %s\n", payload_path.c_str());
    std::printf("state json bytes   : %zu\n", state_json.size());
    std::printf("sizeof(BattleState): %zu bytes\n", sizeof(BattleState));
    std::printf("iters              : %ld\n", iters);
    std::printf("build              : Release (-O2/-march=native/-ffp-contract=off), single-threaded\n\n");

    // -----------------------------------------------------------------------
    // Pick the per-turn action regime. Prefer a real MOVE turn (exercises move
    // resolution); the golden state has distinct speeds so no SPEED_TIE. Fall
    // back to a SWITCH turn if a Category-A pause surfaces (fail loud: report it).
    // -----------------------------------------------------------------------
    std::vector<ExecAction> a0_move = {move_action(0, 0)};
    std::vector<ExecAction> a1_move = {move_action(0, 0)};

    std::string move_err;
    bool move_ok = try_solver_turn(base, a0_move, a1_move, &move_err);
    const std::vector<ExecAction>* a0 = nullptr;
    const std::vector<ExecAction>* a1 = nullptr;
    const char* regime = nullptr;
    if (move_ok) {
        a0 = &a0_move; a1 = &a1_move; regime = "MOVE (real move resolution)";
    } else {
        // Single-mon party in this fixture: a switch has no legal target, so a MOVE
        // turn is the representative clean turn. If MOVE paused, surface loudly.
        std::fprintf(stderr, "MOVE turn paused (%s); no switch fallback on 1-mon party.\n",
                     move_err.c_str());
        std::exit(2);
    }
    std::printf("per-turn regime    : %s\n\n", regime);

    volatile uint64_t sink = 0;

    // -----------------------------------------------------------------------
    // 1. Per-turn direct cost (cpp_run_one_turn_solver). Copy base each iter so
    //    every turn starts from the same live state (copy cost measured separately
    //    below and subtracted out for the pure-turn figure).
    // -----------------------------------------------------------------------
    {
        DamageLoopLuck lp0{}, lp1{};
        TurnLuck tl0{}, tl1{};
        OracleOverrides ov;
        auto t0 = Clock::now();
        for (long i = 0; i < iters; ++i) {
            BattleState s = base;                 // includes one copy
            DamageLoopLuck l0 = lp0, l1 = lp1;
            SolverTurnResult r = cpp_run_one_turn_solver(
                s, *a0, *a1, l0, l1, tl0, tl1, false, false, ov);
            sink += r.ok ? 1u : 0u;
            sink += s.turn_number;
        }
        double sec = seconds_since(t0);
        std::printf("1. per-turn direct (copy+turn) : %8.3f ns/iter  %10.0f turns/s\n",
                    (sec / iters) * 1e9, iters / sec);
    }

    // -----------------------------------------------------------------------
    // 2. State copy throughput (the D2 memcpy win). Trivially copyable => flat copy.
    // -----------------------------------------------------------------------
    {
        std::vector<BattleState> dst(1);
        auto t0 = Clock::now();
        for (long i = 0; i < iters; ++i) {
            dst[0] = base;                        // trivially-copyable assignment
            sink += dst[0].turn_number;
        }
        double sec = seconds_since(t0);
        std::printf("2. state copy                  : %8.3f ns/copy  %10.0f copies/s\n",
                    (sec / iters) * 1e9, iters / sec);
    }

    // -----------------------------------------------------------------------
    // 3. NodePool throughput. Real solver usage: grow the pool across a boundary
    //    (many allocate()s, slabs added on demand), then bulk reset() once. We
    //    measure a full fill (OS slab growth AMORTIZED across all nodes, as it is
    //    in the search) plus copy/emplace, then the standalone reset cost. Mixing
    //    a periodic mass-free INTO the alloc loop (earlier draft) measured malloc
    //    churn, not the pool — so fill and reset are timed separately here.
    //    Node budget bounds RSS (nodes * 8312 B); iters may exceed it, so we run
    //    ceil(iters/budget) fill+reset cycles and average per node.
    //    NOTE: 3a≈3b because NodePool's make_unique<Chunk> value-initializes (zeroes)
    //    every 8312 B slot on slab growth; that first-touch zeroing dominates, so the
    //    D2 flat-copy (metric 2) is nearly free on top of it. This is inherent to
    //    slabbing full 8 KB states, not a copy cost.
    // -----------------------------------------------------------------------
    constexpr long kNodeBudget = 200000;  // ~1.7 GB peak at 8312 B/node
    {
        NodePool<BattleState> pool;
        long done = 0;
        double sec = 0.0;
        while (done < iters) {
            long batch = std::min(kNodeBudget, iters - done);
            auto t0 = Clock::now();
            for (long i = 0; i < batch; ++i) {
                BattleState* slot = pool.allocate();
                *slot = base;
                sink += slot->turn_number;
            }
            sec += seconds_since(t0);
            pool.reset();  // not timed here
            done += batch;
        }
        std::printf("3a. NodePool allocate()+copy   : %8.3f ns/node  %10.0f nodes/s\n",
                    (sec / iters) * 1e9, iters / sec);
    }
    {
        NodePool<BattleState> pool;
        long done = 0;
        double sec = 0.0;
        while (done < iters) {
            long batch = std::min(kNodeBudget, iters - done);
            auto t0 = Clock::now();
            for (long i = 0; i < batch; ++i) {
                BattleState* slot = pool.emplace();  // value-inits (zeroes) the node
                sink += slot->turn_number;
            }
            sec += seconds_since(t0);
            pool.reset();  // not timed here
            done += batch;
        }
        std::printf("3b. NodePool emplace()         : %8.3f ns/node  %10.0f nodes/s\n",
                    (sec / iters) * 1e9, iters / sec);
    }
    {
        // Standalone reset(): fill a full budget, time only the bulk free.
        NodePool<BattleState> pool;
        for (long i = 0; i < kNodeBudget; ++i) pool.emplace();
        auto t0 = Clock::now();
        pool.reset();
        double sec = seconds_since(t0);
        std::printf("3c. NodePool reset() (%ld nodes): %8.3f us total  %10.3f ns/node freed\n",
                    kNodeBudget, sec * 1e6, (sec / kNodeBudget) * 1e9);
    }

    // -----------------------------------------------------------------------
    // 4. JSON round-trip cost at the bridge: encode + decode. This is the overhead
    //    the direct path avoids entirely.
    // -----------------------------------------------------------------------
    double json_ns = 0.0;
    {
        // Fewer iters: JSON is orders of magnitude slower; keep wall time reasonable.
        long jiters = iters / 20 > 0 ? iters / 20 : 1;
        auto t0 = Clock::now();
        for (long i = 0; i < jiters; ++i) {
            std::string enc = battle_state_to_json(base);
            BattleState dec = battle_state_from_json(enc);
            sink += enc.size();
            sink += dec.turn_number;
        }
        double sec = seconds_since(t0);
        json_ns = (sec / jiters) * 1e9;
        std::printf("4. JSON round-trip (enc+dec)   : %8.3f ns/iter  %10.0f rt/s   (%ld iters)\n",
                    json_ns, jiters / sec, jiters);
    }

    // -----------------------------------------------------------------------
    // 5. state_hash_solver cost (per solver node).
    // -----------------------------------------------------------------------
    {
        auto t0 = Clock::now();
        for (long i = 0; i < iters; ++i) {
            sink += state_hash_solver(base);
        }
        double sec = seconds_since(t0);
        std::printf("5. state_hash_solver           : %8.3f ns/hash  %10.0f hashes/s\n",
                    (sec / iters) * 1e9, iters / sec);
    }

    // -----------------------------------------------------------------------
    // Per-boundary projection at _SWEEP_BRANCH_CAP full-turn sims. Direct path =
    // per-turn direct only (state already resident). Bridge path = per-turn direct
    // + one JSON round-trip per turn (crossing the pybind boundary each sim).
    // Re-time the two components cleanly for the projection.
    // -----------------------------------------------------------------------
    double direct_turn_ns = 0.0;
    {
        DamageLoopLuck lp0{}, lp1{};
        TurnLuck tl0{}, tl1{};
        OracleOverrides ov;
        auto t0 = Clock::now();
        for (long i = 0; i < iters; ++i) {
            BattleState s = base;
            DamageLoopLuck l0 = lp0, l1 = lp1;
            SolverTurnResult r = cpp_run_one_turn_solver(
                s, *a0, *a1, l0, l1, tl0, tl1, false, false, ov);
            sink += r.ok ? s.turn_number : 0u;
        }
        direct_turn_ns = (seconds_since(t0) / iters) * 1e9;
    }
    double direct_boundary_us = direct_turn_ns * kSweepBranchCap / 1e3;
    double bridge_boundary_us = (direct_turn_ns + json_ns) * kSweepBranchCap / 1e3;
    double codec_pct = 100.0 * json_ns / (direct_turn_ns + json_ns);

    std::printf("\n=== per-boundary projection (cap=%ld full-turn sims) ===\n", kSweepBranchCap);
    std::printf("direct path  (turn only)       : %8.2f us/boundary\n", direct_boundary_us);
    std::printf("bridge path  (turn + JSON rt)  : %8.2f us/boundary\n", bridge_boundary_us);
    std::printf("codec share of bridge per-turn : %8.1f %%\n", codec_pct);

    std::printf("\nsink=%llu\n", (unsigned long long)sink);
    return 0;
}
