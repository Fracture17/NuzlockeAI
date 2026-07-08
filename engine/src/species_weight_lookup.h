// Isolated TU exposing per-species body weight (avoids enum class Type clash with move_data.h).
// Reads the generated SpeciesData.weight_kg field so callers that include move_data.h
// (e.g. core_leaf.cpp) don't have to embed their own weight table.
#pragma once
#ifndef NUZLOCKE_SPECIES_WEIGHT_LOOKUP_H
#define NUZLOCKE_SPECIES_WEIGHT_LOOKUP_H

#include <cstdint>

// Body weight in kg from generated species_data.h.
// Throws std::runtime_error if species_id is not in the table.
double cpp_species_weight(int32_t species_id);

#endif // NUZLOCKE_SPECIES_WEIGHT_LOOKUP_H
