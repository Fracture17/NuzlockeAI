// Stub that delegates to the per-table lookup_impl files.
// The three generated headers (species_data.h, move_data.h, item_data.h) all define
// 'enum class Type', so they cannot be included in the same TU.
// lookup_species_json / lookup_move_json / lookup_item_json are each in their own .cpp.
// This file intentionally empty — actual definitions in lookup_species.cpp / lookup_move.cpp / lookup_item.cpp.
