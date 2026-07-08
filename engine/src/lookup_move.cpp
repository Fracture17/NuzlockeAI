// Move lookup: isolated TU to avoid enum class Type redefinition with species_data.h.
#include "lookup.h"
#include <move_data.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

static constexpr int MOVE_COUNT_TBL = 813;

std::string lookup_move_json(int32_t id) {
    int lo = 0, hi = MOVE_COUNT_TBL;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= MOVE_COUNT_TBL || MOVE_TABLE[lo].move_id != id) {
        throw std::runtime_error("lookup_move: id " + std::to_string(id) + " not found");
    }
    const MoveData& mv = MOVE_TABLE[lo];
    nlohmann::json j;
    j["move_type"]  = mv.move_type;
    j["category"]   = mv.category;
    j["base_power"] = mv.base_power;
    j["accuracy"]   = mv.accuracy;
    j["pp"]         = mv.pp;
    j["priority"]   = mv.priority;
    j["move_id"]    = mv.move_id;
    return j.dump();
}
