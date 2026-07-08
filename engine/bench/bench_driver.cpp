// Standalone throughput/profiling driver for cpp_run_game — NO Python, NO pybind.
// Parses one payload (/tmp/bench_payload.json) ONCE, then measures two regimes:
//   (A) pure compute: cpp_run_game on a pre-parsed BattleState copy (the NN native-binding path);
//   (B) boundary-inclusive: JSON parse of state + run + JSON dump of final_state every iteration
//       (mirrors what nuzlocke_engine_cpp.run_game does across the pybind boundary).
// The delta between (A) and (B) is the serialization cost. Built with -pg for gprof attribution.
//
// Usage: bench_driver <iters> [mode]   mode = A (pure compute) | B (JSON) | AB (both, default)
#include <nlohmann/json.hpp>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#include "codec.h"
#include "orchestrate.h"
#include "core_leaf.h"
#include "damage.h"


int main(int argc, char** argv) {
    long iters = (argc > 1) ? std::atol(argv[1]) : 20000;
    std::string mode = (argc > 2) ? argv[2] : "AB";
    bool run_A = (mode.find('A') != std::string::npos);
    bool run_B = (mode.find('B') != std::string::npos);

    std::ifstream f("/tmp/bench_payload.json");
    if (!f) { std::fprintf(stderr, "cannot open /tmp/bench_payload.json\n"); return 1; }
    std::stringstream ss; ss << f.rdbuf();
    std::string payload_str = ss.str();
    nlohmann::json j = nlohmann::json::parse(payload_str);

    std::string state_json = j["state"].dump();
    BattleState base = battle_state_from_json(state_json);
    uint64_t seed = j.value("seed", uint64_t(0));
    DamageLoopLuck lp0 = damage_luck_from_json(j["luck_p0"]);
    DamageLoopLuck lp1 = damage_luck_from_json(j["luck_p1"]);
    TurnLuck tl0 = turn_luck_from_json(j["turn_luck_p0"]);
    TurnLuck tl1 = turn_luck_from_json(j["turn_luck_p1"]);
    int max_turns = j.value("max_turns", 1000);

    // Warm up + establish turn_count for this fixed battle.
    GameResult warm = cpp_run_game(base, seed, lp0, lp1, tl0, tl1, max_turns, false);
    long turns_per_battle = warm.turn_count;
    std::printf("fixture: turns/battle=%ld status=%s iters=%ld\n",
                turns_per_battle, warm.status.c_str(), iters);

    long total_turns = turns_per_battle * iters;
    volatile long sink = 0;
    double secA = 0.0, secB = 0.0;

    if (run_A) {
        // (A) Pure compute: no JSON at the boundary.
        auto tA0 = std::chrono::steady_clock::now();
        for (long i = 0; i < iters; ++i) {
            GameResult r = cpp_run_game(base, seed, lp0, lp1, tl0, tl1, max_turns, false);
            sink += r.turn_count;
        }
        auto tA1 = std::chrono::steady_clock::now();
        secA = std::chrono::duration<double>(tA1 - tA0).count();
        std::printf("(A) pure compute       : %.3fs  %8.0f battles/s  %9.0f turns/s  %6.2f us/turn\n",
                    secA, iters / secA, total_turns / secA, (secA / total_turns) * 1e6);
    }

    if (run_B) {
        // (B) Boundary-inclusive: parse state JSON + run + dump final_state JSON every iter.
        auto tB0 = std::chrono::steady_clock::now();
        for (long i = 0; i < iters; ++i) {
            BattleState s = battle_state_from_json(state_json);
            GameResult r = cpp_run_game(s, seed, lp0, lp1, tl0, tl1, max_turns, false);
            std::string out = battle_state_to_json(r.final_state);
            sink += out.size();
        }
        auto tB1 = std::chrono::steady_clock::now();
        secB = std::chrono::duration<double>(tB1 - tB0).count();
        std::printf("(B) +JSON parse+dump   : %.3fs  %8.0f battles/s  %9.0f turns/s  %6.2f us/turn\n",
                    secB, iters / secB, total_turns / secB, (secB / total_turns) * 1e6);
    }

    if (run_A && run_B) {
        std::printf("    JSON boundary cost : %.2f us/battle  (%.0f%% of B)\n",
                    ((secB - secA) / iters) * 1e6, 100.0 * (secB - secA) / secB);
    }
    std::printf("sink=%ld\n", (long)sink);
    return 0;
}
