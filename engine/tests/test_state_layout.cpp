// Catch2 tests for the D2 slab-ready state layout: BattleState is trivially copyable,
// InlineVec pushes/inserts fail loud on overflow, and NodePool grows in chunks + bulk-frees.
#include <catch2/catch_test_macros.hpp>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
#include <sys/types.h>
#include <unistd.h>
#include <type_traits>

#include "inline_vec.h"
#include "node_pool.h"
#include "state.h"

// -------- BattleState / SideState / PokemonState: trivially copyable ----------

TEST_CASE("BattleState is trivially copyable (memcpy-safe for solver)", "[state][layout]") {
    static_assert(std::is_trivially_copyable_v<PokemonState>,
                  "PokemonState must be trivially copyable");
    static_assert(std::is_trivially_copyable_v<SideState>,
                  "SideState must be trivially copyable");
    static_assert(std::is_trivially_copyable_v<BattleState>,
                  "BattleState must be trivially copyable");
    SUCCEED();
}

// Round-trip: memcpy of a mutated BattleState must equal the source under state_equal.
// Sanity check that the trivially-copyable claim is honored end-to-end.
#include "state_eq.h"
#include <cstring>

TEST_CASE("BattleState memcpy round-trip preserves state_equal", "[state][layout]") {
    BattleState a{};
    a.turn_number = 42;
    a.weather = 3;
    a.side0.team.push_back(PokemonState{});
    a.side0.team[0].species = 100;
    a.side0.team[0].hp = 55;
    a.side0.active_indices.push_back(0);
    a.side0.side_conditions.push_back(SideConditionEntry{4, 5});
    a.pseudo_weather.push_back(PseudoWeatherEntry{1, 8});
    a.turn_order.push_back(0);
    a.turn_order.push_back(1);

    BattleState b{};
    std::memcpy(&b, &a, sizeof(BattleState));

    REQUIRE(state_equal(a, b));
    REQUIRE(state_hash(a) == state_hash(b));
}

// -------- InlineVec fail-loud on overflow --------

// Fork-based death test: the child aborts on overflow; parent asserts nonzero exit status.
static bool child_aborted(int status) {
    if (WIFSIGNALED(status)) return true;  // SIGABRT
    if (WIFEXITED(status) && WEXITSTATUS(status) != 0) return true;
    return false;
}

// Silence child stdio so Catch2's abort handler / SIGABRT report doesn't pollute test output.
static void silence_child_output() {
    std::freopen("/dev/null", "w", stdout);
    std::freopen("/dev/null", "w", stderr);
}

TEST_CASE("InlineVec push_back fails loudly on overflow", "[inline_vec][overflow]") {
    pid_t pid = fork();
    REQUIRE(pid >= 0);
    if (pid == 0) {
        silence_child_output();
        InlineVec<int, 3> v;
        v.push_back(1); v.push_back(2); v.push_back(3);
        v.push_back(4);  // must abort
        _exit(0);        // if we get here, overflow was silently accepted
    }
    int status = 0;
    waitpid(pid, &status, 0);
    REQUIRE(child_aborted(status));
}

TEST_CASE("InlineVec assign fails loudly on overflow", "[inline_vec][overflow]") {
    pid_t pid = fork();
    REQUIRE(pid >= 0);
    if (pid == 0) {
        silence_child_output();
        InlineVec<int, 2> v;
        v.assign(static_cast<std::size_t>(5), 42);  // must abort
        _exit(0);
    }
    int status = 0;
    waitpid(pid, &status, 0);
    REQUIRE(child_aborted(status));
}

TEST_CASE("InlineVec insert_at fails loudly on overflow", "[inline_vec][overflow]") {
    pid_t pid = fork();
    REQUIRE(pid >= 0);
    if (pid == 0) {
        silence_child_output();
        InlineVec<int, 2> v;
        v.push_back(1); v.push_back(2);
        v.insert_at(0, 9);  // must abort
        _exit(0);
    }
    int status = 0;
    waitpid(pid, &status, 0);
    REQUIRE(child_aborted(status));
}

// -------- InlineVec basic behavior --------

TEST_CASE("InlineVec basic push/read/clear/equality", "[inline_vec]") {
    InlineVec<int, 4> v;
    REQUIRE(v.empty());
    v.push_back(10);
    v.push_back(20);
    v.push_back(30);
    REQUIRE(v.size() == 3);
    REQUIRE(v[0] == 10);
    REQUIRE(v[2] == 30);

    InlineVec<int, 4> w;
    w.push_back(10); w.push_back(20); w.push_back(30);
    REQUIRE(v == w);

    v.pop_back();
    REQUIRE(v.size() == 2);
    REQUIRE(!(v == w));

    v.clear();
    REQUIRE(v.empty());
}

TEST_CASE("InlineVec insert_at shifts elements right", "[inline_vec]") {
    InlineVec<int, 5> v;
    v.push_back(1); v.push_back(3); v.push_back(4);
    v.insert_at(1, 2);
    REQUIRE(v.size() == 4);
    REQUIRE(v[0] == 1);
    REQUIRE(v[1] == 2);
    REQUIRE(v[2] == 3);
    REQUIRE(v[3] == 4);
}

TEST_CASE("InlineVec is trivially copyable for int payload", "[inline_vec][layout]") {
    static_assert(std::is_trivially_copyable_v<InlineVec<int, 8>>,
                  "InlineVec<int,N> must be trivially copyable");
    SUCCEED();
}

// -------- NodePool --------

TEST_CASE("NodePool grows in chunks and reset frees all", "[node_pool]") {
    NodePool<BattleState, 4> pool;
    REQUIRE(pool.size() == 0);
    REQUIRE(pool.capacity() == 0);

    for (int i = 0; i < 4; ++i) {
        BattleState* n = pool.emplace();
        REQUIRE(n != nullptr);
    }
    REQUIRE(pool.size() == 4);
    REQUIRE(pool.chunk_count() == 1);

    (void)pool.emplace();  // triggers new chunk
    REQUIRE(pool.size() == 5);
    REQUIRE(pool.chunk_count() == 2);

    pool.reset();
    REQUIRE(pool.size() == 0);
    REQUIRE(pool.chunk_count() == 0);
}

TEST_CASE("NodePool nodes stay stable within a chunk", "[node_pool]") {
    NodePool<int, 8> pool;
    int* a = pool.emplace();
    int* b = pool.emplace();
    *a = 111;
    *b = 222;
    REQUIRE(*a == 111);
    REQUIRE(*b == 222);
    REQUIRE(a != b);
}
