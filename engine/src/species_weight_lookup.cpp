// Isolated TU exposing per-species body weight (avoids enum class Type clash with move_data.h).
#include "species_weight_lookup.h"

#include <stdexcept>
#include <string>

#include <species_data.h>

static constexpr int SPECIES_COUNT_TBL = 1220;

double cpp_species_weight(int32_t species_id) {
    int lo = 0, hi = SPECIES_COUNT_TBL;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (SPECIES_TABLE[mid].species_id < species_id) lo = mid + 1; else hi = mid;
    }
    if (lo >= SPECIES_COUNT_TBL || SPECIES_TABLE[lo].species_id != species_id)
        throw std::runtime_error("cpp_species_weight: id " + std::to_string(species_id) + " not found");
    return SPECIES_TABLE[lo].weight_kg;
}
