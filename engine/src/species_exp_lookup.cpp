// Isolated TU exposing per-species EXP/stat fields (avoids enum class Type clash with move_data.h).
#include "species_exp_lookup.h"

#include <stdexcept>
#include <string>

#include <species_data.h>

SpeciesExpData cpp_species_exp_data(int32_t species_id) {
    int lo = 0, hi = 1220;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (SPECIES_TABLE[mid].species_id < species_id) lo = mid + 1; else hi = mid;
    }
    if (lo >= 1220 || SPECIES_TABLE[lo].species_id != species_id)
        throw std::runtime_error("cpp_species_exp_data: id " + std::to_string(species_id) + " not found");
    const SpeciesData& sd = SPECIES_TABLE[lo];
    return SpeciesExpData{
        sd.base_hp, sd.base_atk, sd.base_def, sd.base_spa, sd.base_spd, sd.base_spe,
        sd.growth_rate, sd.exp_yield,
    };
}
