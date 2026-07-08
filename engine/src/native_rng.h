// Native C++ RNG wrapper for random_mode resolver draws (Stage A1).
// Header-only. Wraps std::mt19937_64 with helpers that mirror the Python random module
// shapes used by rng.py: random(), randint(a,b), choice(vec), choices(values, weights).
// NOT stream-compatible with CPython's Mersenne Twister — parity is behavioural, not bitwise.
#pragma once
#ifndef NUZLOCKE_NATIVE_RNG_H
#define NUZLOCKE_NATIVE_RNG_H

#include <cstdint>
#include <random>
#include <stdexcept>
#include <vector>

struct ForcedTrace;  // forward declaration; see forced_trace.h

// NativeRng: thin wrapper around mt19937_64. One instance per game, seeded from the
// game seed so random_mode runs are reproducible given the same seed.
struct NativeRng {
    explicit NativeRng(uint64_t seed) : engine_(seed) {}

    // Non-null in forced replay mode; wired to draw sites in a later task.
    ForcedTrace* forced = nullptr;
    // Current game turn; maintained by GameDriver for keyed lookups in forced mode.
    int current_turn = 0;

    // random() -> [0, 1)  (mirrors Python random.random())
    double random() {
        return std::uniform_real_distribution<double>(0.0, 1.0)(engine_);
    }

    // randint(a, b) -> inclusive [a, b]  (mirrors Python random.randint(a, b))
    int randint(int a, int b) {
        return std::uniform_int_distribution<int>(a, b)(engine_);
    }

    // choice(vec) -> one element uniformly  (mirrors Python random.choice(seq))
    int choice(const std::vector<int>& values) {
        if (values.empty()) throw std::runtime_error("NativeRng::choice: empty sequence");
        int idx = std::uniform_int_distribution<int>(0, (int)values.size() - 1)(engine_);
        return values[idx];
    }

    // choices(values, weights) -> weighted sample of one element
    // (mirrors Python random.choices([...], weights=[...])[0])
    int choices(const std::vector<int>& values, const std::vector<int>& weights) {
        if (values.size() != weights.size() || values.empty())
            throw std::runtime_error("NativeRng::choices: bad sizes");
        int total = 0;
        for (int w : weights) total += w;
        std::uniform_int_distribution<int> dist(0, total - 1);
        int r = dist(engine_);
        int acc = 0;
        for (size_t i = 0; i < weights.size(); ++i) {
            acc += weights[i];
            if (r < acc) return values[i];
        }
        throw std::logic_error("NativeRng::choices: weights did not cover draw");
    }

private:
    std::mt19937_64 engine_;
};

#endif // NUZLOCKE_NATIVE_RNG_H
