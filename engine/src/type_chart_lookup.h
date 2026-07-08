// Type effectiveness lookup: isolated TU to avoid enum class Type redefinition with move_data.h.
// Exposes a single function operating on raw int32_t type indices.
#pragma once
#ifndef NUZLOCKE_TYPE_CHART_LOOKUP_H
#define NUZLOCKE_TYPE_CHART_LOOKUP_H

#include <cstdint>

// Returns TYPE_CHART[atk_type][def_type]. Indices 0-18 (TYPELESS=18 always returns 1.0).
float cpp_type_effectiveness(int32_t atk_type, int32_t def_type);

#endif // NUZLOCKE_TYPE_CHART_LOOKUP_H
