// Catch2 smoke tests: verify core pure functions compile and return known values.
// Scaffold — deeper native tests come in Stage D.
#include <catch2/catch_test_macros.hpp>
#include "stats.h"
#include "type_chart_lookup.h"

// HP stat for Charizard (base 78, IV 31, neutral nature index 0, level 50):
// floor((2*78 + 31) * 50 / 100) + 50 + 10 = floor(187 * 0.5) + 60 = 93 + 60 = 153
TEST_CASE("compute_stat HP matches known Charizard value", "[stats]") {
    int32_t hp = compute_stat(0, 78, 31, 0, 50);
    REQUIRE(hp == 153);
}

// Non-HP stat: Charizard Speed (base 100, IV 31, neutral nature 0, level 50):
// floor((2*100 + 31) * 50 / 100) + 5 = floor(231 * 0.5) + 5 = 115 + 5 = 120, no nature mod.
TEST_CASE("compute_stat non-HP matches known Charizard speed value", "[stats]") {
    int32_t spd = compute_stat(5, 100, 31, 0, 50);
    REQUIRE(spd == 120);
}

// Type indices: FIRE=1, GRASS=4, WATER=2 (from type_chart.h enum).
// Fire (1) vs Grass (4) is 2x super-effective.
TEST_CASE("cpp_type_effectiveness fire vs grass is 2.0", "[type_chart]") {
    float eff = cpp_type_effectiveness(1, 4);
    REQUIRE(eff == 2.0f);
}

// Water (2) vs Fire (1) is 2x super-effective.
TEST_CASE("cpp_type_effectiveness water vs fire is 2.0", "[type_chart]") {
    float eff = cpp_type_effectiveness(2, 1);
    REQUIRE(eff == 2.0f);
}
