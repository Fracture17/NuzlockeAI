// compute_stat declaration: mirrors Python compute_stat from src/state/pokemon.py.
// Implementation in stats.cpp to isolate nature_data.h from other TUs.
#pragma once
#ifndef NUZLOCKE_STATS_H
#define NUZLOCKE_STATS_H

#include <cstdint>
#include <stdexcept>
#include <string>

// Compute a single stat value; stat_idx: 0=HP, 1=ATK, 2=DEF, 3=SPA, 4=SPD, 5=SPE.
// No EVs. Mirrors Python compute_stat using double+floor arithmetic.
// Throws std::runtime_error on invalid nature_idx.
int32_t compute_stat(int stat_idx, int base, int iv, int nature_idx, int level);

#endif // NUZLOCKE_STATS_H
