// Species type lookup: isolated TU to avoid enum class Type redefinition with move_data.h.
// Returns a species' reset types (1 or 2 entries) as raw int32_t Type values.
#pragma once
#ifndef NUZLOCKE_SPECIES_TYPES_LOOKUP_H
#define NUZLOCKE_SPECIES_TYPES_LOOKUP_H

#include <cstdint>
#include <vector>

// Throws std::runtime_error if species_id not found.
std::vector<int32_t> cpp_species_types(int32_t species_id);

#endif // NUZLOCKE_SPECIES_TYPES_LOOKUP_H
