// Isolated TU exposing species reset-types (avoids enum class Type clash with move_data.h).
#include "species_types_lookup.h"

#include <stdexcept>
#include <string>

#include <species_data.h>

std::vector<int32_t> cpp_species_types(int32_t species_id) {
    int lo = 0, hi = 1220;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (SPECIES_TABLE[mid].species_id < species_id) lo = mid + 1; else hi = mid;
    }
    if (lo >= 1220 || SPECIES_TABLE[lo].species_id != species_id)
        throw std::runtime_error("cpp_species_types: id " + std::to_string(species_id) + " not found");
    const SpeciesData& sd = SPECIES_TABLE[lo];
    std::vector<int32_t> out;
    out.push_back(sd.type1);
    if (sd.type2 >= 0) out.push_back(sd.type2);
    return out;
}
