// Species lookup: isolated TU to avoid enum class Type redefinition with move_data.h.
#include "lookup.h"
#include <species_data.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

static constexpr int SPECIES_COUNT_TBL = 1220;

std::string lookup_species_json(int32_t id) {
    int lo = 0, hi = SPECIES_COUNT_TBL;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (SPECIES_TABLE[mid].species_id < id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= SPECIES_COUNT_TBL || SPECIES_TABLE[lo].species_id != id) {
        throw std::runtime_error("lookup_species: id " + std::to_string(id) + " not found");
    }
    const SpeciesData& sp = SPECIES_TABLE[lo];
    nlohmann::json j;
    j["type1"]       = sp.type1;
    j["type2"]       = sp.type2;
    j["base_hp"]     = sp.base_hp;
    j["base_atk"]    = sp.base_atk;
    j["base_def"]    = sp.base_def;
    j["base_spa"]    = sp.base_spa;
    j["base_spd"]    = sp.base_spd;
    j["base_spe"]    = sp.base_spe;
    j["weight_kg"]   = sp.weight_kg;
    j["growth_rate"] = sp.growth_rate;
    j["exp_yield"]   = sp.exp_yield;
    j["species_id"]  = sp.species_id;
    return j.dump();
}
