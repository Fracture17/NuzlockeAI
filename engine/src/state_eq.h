// Full-field structural equality + a self-consistent hash for the BattleState graph.
// Mirrors Python's auto-generated dataclass __eq__ (compares the ENTIRE field tuple) so
// in-engine candidate dedup matches src/simulation_runner.py's set-of-BattleState semantics.
// The hash need NOT match Python's; it only must satisfy state_equal(a,b) => state_hash(a)==state_hash(b).
#pragma once
#ifndef NUZLOCKE_STATE_EQ_H
#define NUZLOCKE_STATE_EQ_H

#include <cstddef>
#include "state.h"

// Full-field equality (order-sensitive for lists/tuples, order-independent for set fields).
bool state_equal(const PokemonState& a, const PokemonState& b);
bool state_equal(const SideState& a, const SideState& b);
bool state_equal(const BattleState& a, const BattleState& b);

// Hash consistent with state_equal over the same field set.
std::size_t state_hash(const BattleState& s);

// ---------------------------------------------------------------------------
// rng resolver coverage map (C1.6 audit — HISTORICAL; the deferred list below has long
// been ported). resolve_* names refer to src/rng.py. The C++ Category-B resolution
// choke point is now cpp/src/rng_resolver.h (Stage A Step 3 consolidation).
//
// REACHED by ported units (damage/effects/post_hit/residuals) and parity-covered, incl.
// saturation early-outs, by existing test_cpp_{damage,effects,posthit}.py:
//   resolve_crit, resolve_secondary, resolve_proc, resolve_damage_roll,
//   resolve_flinch, resolve_binding_duration.
//
// DEFERRED to C1.7 (NOT reached by any ported unit yet):
//   resolve_accuracy, resolve_multi_hit, resolve_speed_tie_between, resolve_wake,
//   resolve_confusion_snap, resolve_defrost, resolve_confusion_self_hit, resolve_attract,
//   resolve_paralysis, resolve_rampage_duration, resolve_quick_claw,
//   resolve_psywave_roll      (only reached from core.py Psywave fixed-damage; not in the
//                              ported damage.calculate_damage path),
//   resolve_ancient_power_boost (no call site in src/engine/* — currently dead).
// EXCLUDED from parity (uncontrolled randomness): random_mode.
// (resolve_roar deleted 2026-07-04: Roar targets resolve via the ROAR_TARGET oracle pause.)
// ---------------------------------------------------------------------------

#endif // NUZLOCKE_STATE_EQ_H
