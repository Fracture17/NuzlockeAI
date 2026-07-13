// Stub implementations for phase-4 engine queries. Both throw until phase 4 lands.
#include "oracle_types.h"

void oracle_damage_table_query(const BattleState* /*state*/) {
    throw std::logic_error("not implemented until phase 4");
}

void oracle_hp_threshold_set_query(const BattleState* /*state*/) {
    throw std::logic_error("not implemented until phase 4");
}
