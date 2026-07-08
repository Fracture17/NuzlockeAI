// compute_stat implementation. Isolated in its own TU to avoid enum conflicts with move_data.h.
#include "stats.h"
#include <cmath>
#include <nature_data.h>  // from generated/

static const double NATURE_BOOST = 1.1;
static const double NATURE_LOWER = 0.9;

int32_t compute_stat(int stat_idx, int base, int iv, int nature_idx, int level) {
    if (stat_idx == 0) {
        // HP: floor((2*base + iv) * level / 100) + level + 10
        return static_cast<int32_t>(
            std::floor(static_cast<double>(2 * base + iv) * level / 100.0))
            + level + 10;
    }
    // Non-HP: floor((2*base + iv) * level / 100) + 5, then nature modifier
    int32_t intermediate = static_cast<int32_t>(
        std::floor(static_cast<double>(2 * base + iv) * level / 100.0)) + 5;

    if (nature_idx < 0 || nature_idx > 24) {
        throw std::runtime_error("compute_stat: invalid nature_idx " + std::to_string(nature_idx));
    }
    const NatureData& nat = NATURE_TABLE[nature_idx];

    if (nat.boosted == stat_idx) {
        return static_cast<int32_t>(std::floor(static_cast<double>(intermediate) * NATURE_BOOST));
    } else if (nat.lowered == stat_idx) {
        return static_cast<int32_t>(std::floor(static_cast<double>(intermediate) * NATURE_LOWER));
    }
    return intermediate;
}
