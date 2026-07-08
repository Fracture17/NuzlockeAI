// Item lookup: isolated TU. item_data.h has no Type enum conflict but isolated for consistency.
#include "lookup.h"
#include <item_data.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

static constexpr int ITEM_COUNT_TBL = 332;

std::string lookup_item_json(int32_t id) {
    int lo = 0, hi = ITEM_COUNT_TBL;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (ITEM_TABLE[mid].item_id < id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= ITEM_COUNT_TBL || ITEM_TABLE[lo].item_id != id) {
        throw std::runtime_error("lookup_item: id " + std::to_string(id) + " not found");
    }
    const ItemData& it = ITEM_TABLE[lo];
    nlohmann::json j;
    j["name"]    = it.name;
    j["item_id"] = it.item_id;
    return j.dump();
}
