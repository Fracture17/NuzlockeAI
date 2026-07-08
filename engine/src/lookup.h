// Lookup declarations for sorted generated tables.
// Implementations in lookup.cpp to isolate conflicting enum definitions across generated headers.
#pragma once
#ifndef NUZLOCKE_LOOKUP_H
#define NUZLOCKE_LOOKUP_H

#include <cstdint>
#include <string>

// Each function looks up by integer id and returns a JSON string of the data row.
// Throws std::runtime_error when id is not found.
std::string lookup_species_json(int32_t id);
std::string lookup_move_json(int32_t id);
std::string lookup_item_json(int32_t id);

#endif // NUZLOCKE_LOOKUP_H
