// Shared internal helpers ported from src/engine/_helpers.py, used by both effects.cpp and
// post_hit.cpp. Not part of the public probe API. See effects.cpp for the implementations.
#pragma once
#ifndef NUZLOCKE_EFFECTS_INTERNAL_H
#define NUZLOCKE_EFFECTS_INTERNAL_H

#include "state.h"
#include "effects.h"
#include <cstdint>

// Forward declaration of global ExecCtx (defined in move_exec_guards.h).
// Declared here so change_stat_stage can accept it without pulling in the full header.
struct ExecCtx;

namespace eff_internal {

SideState& side_at(BattleState& s, int idx);
PokemonState& active_mon(BattleState& s, int side_idx);

bool is_mold_breaker(int32_t ability);
bool has_type(const PokemonState& mon, int32_t type);
bool has_pseudo(const BattleState& s, int32_t pw);
bool has_timed_volatile(const PokemonState& mon, int32_t ve);
bool is_grounded(const PokemonState& mon, const BattleState& s);

// Effective weather: state.weather suppressed to WEATHER_NONE by an active Air Lock / Cloud Nine.
// Shared by damage.cpp / effects.cpp / core_leaf.cpp (was a per-TU static copy).
int32_t effective_weather(const BattleState& s);

int32_t get_stage(const PokemonState& m, int i);
void set_stage(PokemonState& m, int i, int32_t v);

void apply_unburden(BattleState& s, int side_idx);
bool is_status_berry_relevant(int32_t item);
bool is_berry(int32_t item);

// _change_stat_stage (returns applied delta). source param omitted (logging only).
// ctx: optional ExecCtx pointer; when non-null and Eject Pack triggers, the side is appended
// to ctx->eject_pack_sides rather than throwing. Pass nullptr for callers without a ctx.
int32_t change_stat_stage(BattleState& s, int side_idx, int stat_idx, int delta,
                          bool caused_by_opponent, bool ignore_simple, bool mold_breaker,
                          ExecCtx* ctx = nullptr);

// _on_stat_dropped (Defiant/Competitive). competitive_defiant_triggered: optional pointer to a
// 2-element per-side dedup array (ExecCtx) ensuring it fires at most once per turn per side;
// nullptr fires unconditionally.
void on_stat_dropped(BattleState& s, int side_idx, int stat_idx,
                     bool* competitive_defiant_triggered = nullptr);

bool can_apply_status(const PokemonState& target, int32_t status, int32_t move,
                      int32_t attacker_ability, const BattleState& s);
void apply_status_to(BattleState& s, int side_idx, int32_t status);

// _check_status_berry: consume a status-curing berry (Lum/Rawst/.../Chesto) if applicable.
// side_idx is the holder; opp_side_idx supplies Unnerve-family berry suppression (-1 = none).
// Returns true if a berry was consumed.
bool check_status_berry(BattleState& s, int side_idx, int opp_side_idx);

// _check_confusion_berry: consume Persim Berry to cure confusion. Returns nothing.
void check_confusion_berry(BattleState& s, int side_idx, int opp_side_idx);

// _check_berry: HP-threshold berry (Sitrus/Oran/pinch/flavour/Lansat). rng resolves Starf's random
// stat pick in random_mode (non-null); overrides resolves it via oracle in controlled mode (null=fail-loud).
// Returns true if consumed.
bool check_berry(BattleState& s, int side_idx, int opp_side_idx, NativeRng* rng = nullptr,
                 const OracleOverrides* overrides = nullptr);

// _notify_faint_soul_heart: +1 SpA to every active non-fainted Soul-Heart holder on both sides.
void notify_faint_soul_heart(BattleState& s);

// _apply_form_change: recompute all 6 stats + types for a form change (Power Construct HP growth).
// Promoted from post_hit.cpp's anonymous namespace so move_exec_helpers.cpp can share it.
void apply_form_change(BattleState& s, int side_idx, int32_t new_species);

// _try_apply_flinch (Inner Focus block + Steadfast +1 Spe).
void try_apply_flinch(BattleState& s, int defender_idx, bool mold_breaker);

// True if the item is a mega stone or primal orb (Blue/Red Orb are in the MEGA_ITEMS set).
// Used by the C1.7e turn driver's primal/mega-reversion fail-loud guard.
bool is_mega_item(int32_t item);

// resolve_* deterministic mirrors (non-random_mode). chance 0-100.
bool resolve_secondary_det(int chance, const EffectsLuck& luck);
bool resolve_proc_det(int chance, const EffectsLuck& luck);
bool resolve_flinch_det(int chance, const EffectsLuck& luck);

// Entry-effects helpers also used by turn-start / EOT form-change paths in effects.cpp.
// Defined in effects_entry.cpp.
bool is_silvally(int32_t species);
bool is_castform_form(int32_t species);
int32_t memory_type(int32_t item);
void update_castform(BattleState& s, int side_idx, int32_t weather);

} // namespace eff_internal

#endif // NUZLOCKE_EFFECTS_INTERNAL_H
