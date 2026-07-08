// Type effectiveness isolated TU — includes only type_chart.h to avoid enum redefinition.
#include "type_chart_lookup.h"
#include <type_chart.h>

float cpp_type_effectiveness(int32_t atk_type, int32_t def_type) {
    if (atk_type < 0 || atk_type > 18 || def_type < 0 || def_type > 18) return 1.0f;
    return TYPE_CHART[atk_type][def_type];
}
