// Isolated TU exposing per-species EXP/stat fields (avoids enum class Type clash with move_data.h).
// Provides base stats, growth rate, and EXP yield needed by the EXP port (exp.cpp).
#pragma once
#ifndef NUZLOCKE_SPECIES_EXP_LOOKUP_H
#define NUZLOCKE_SPECIES_EXP_LOOKUP_H

#include <cstdint>

// Subset of generated SpeciesData fields consumed by the EXP port.
struct SpeciesExpData {
    int32_t base_hp, base_atk, base_def, base_spa, base_spd, base_spe;
    int32_t growth_rate;  // GrowthRate enum value
    int32_t exp_yield;
};

// Throws std::runtime_error if species_id not found.
SpeciesExpData cpp_species_exp_data(int32_t species_id);

#endif // NUZLOCKE_SPECIES_EXP_LOOKUP_H
