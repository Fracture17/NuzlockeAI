// C++ port of mutating move-effect units from src/engine/effects.py and post_hit.py (C1.4).
// Ported branches reach exact Python state parity; unported branches throw std::runtime_error("unported: ...").
#pragma once
#ifndef NUZLOCKE_EFFECTS_H
#define NUZLOCKE_EFFECTS_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include "oracle.h"       // OracleOverrides
#include <cstdint>

// Probe options threaded from the binding (mirrors the deterministic LuckProfile fields the
// ported branches consume). Defaults reproduce GOOD_LUCK semantics used by the test harness.
// random_mode=true: rng must be non-null for any draw; random_mode=false: rng may be null.
struct EffectsLuck {
    double proc_threshold = 0.0;       // resolve_proc deterministic: fires iff chance >= proc_threshold
    double secondary_threshold = 0.0;  // resolve_secondary deterministic
    double flinch_threshold = 0.0;     // resolve_flinch deterministic
    double binding_duration_roll = 1.0; // resolve_binding_duration: >=0.5 -> 5 turns else 4
    bool   random_mode = false;        // true = draws come from rng
    NativeRng* rng = nullptr;          // non-null iff random_mode=true
    const OracleOverrides* overrides = nullptr;  // threaded from GameDriver; null on plain run_game path
};

// _apply_entry_hazards(sides, entering_side_idx, state): SR / Spikes / T-Spikes / Sticky Web.
void cpp_apply_entry_hazards(BattleState& state, int entering_side_idx);

// _apply_entry_effects(sides, entering_side_idx, state, ctx=None): on-entry ability/item triggers
// (Intimidate, weather/terrain setters, Trace, Imposter, Download, seeds, Soul Dew, Forecast,
// RKS, Screen Cleaner, Pastel Veil, Truant re-loaf, Neutralizing Gas sync). Deterministic.
struct ExecCtx;  // forward; full definition in move_exec_guards.h
void cpp_apply_entry_effects(BattleState& state, int entering_side_idx, ExecCtx* ctx = nullptr);

// C1.7e begin-turn / end-of-turn leaf helpers (driven by cpp_run_one_turn). Each mirrors the
// corresponding Python helper exactly; the turn driver owns sequencing.

// _apply_terrain_seeds (residuals.py:38): consume matching Terrain Seed for grounded actives.
void cpp_apply_terrain_seeds(BattleState& state);

// _apply_turn_start_effects (core.py:841): RKS/Silvally memory-item type sync + Castform Forecast.
// Fail-loud: throws "unported: turn_start" if an active Castform or Silvally-family mon is present.
void cpp_apply_turn_start_effects(BattleState& state);

// _apply_eot_form_changes -> apply_eot_form_changes (effects.py:1534): Hunger Switch, Power
// Construct, Ice Face, Forecast, Schooling, Shields Down, Zen Mode end-of-turn transitions.
void cpp_apply_eot_form_changes(BattleState& state);

// _apply_eot_volatile_clear (simulator.py:1275): clear FLINCHED/ENDURE_ACTIVE/HELPING_HAND
// volatiles, reset redirect_target=-1, advance Echoed Voice multiplier.
void cpp_apply_eot_volatile_clear(BattleState& state);

// _apply_eot_weather_terrain (simulator.py:1293): decrement weather/terrain/side_conditions/
// pseudo_weather counters; expire to NONE/0; -1 (infinite) stays unchanged.
void cpp_apply_eot_weather_terrain(BattleState& state);

// ExecCtx (defined in move_exec_guards.h) carries per-turn Protect state across movers. Forward-
// declared here so apply_status_move can record protected_sides without a header cycle.
struct ExecCtx;

// _apply_status_move dispatch (protect -> hazard -> field -> [volatile STUB] -> recovery ->
// [self_status STUB] -> interaction). Throws for unported branches. ctx accumulates Protect-family
// side state (protected_sides / protect_move / wide_guard / quick_guard) for the turn.
void cpp_apply_status_move(BattleState& state, int side_idx, int32_t move_id, const EffectsLuck& luck,
                           ExecCtx& ctx, int attacker_slot = 0);

// _apply_switch_out_reset(side, team_slot): clear volatiles + Natural Cure / Regenerator.
void cpp_apply_switch_out_reset(BattleState& state, int side_idx, int team_slot);

// _sec_self_stat_changes(sides, side_idx, hit_ctx): self-drops from move_data.self_stat_changes.
void cpp_sec_self_stat_changes(BattleState& state, int side_idx, int32_t move_id, int damage);

// Pending-switch request appended by post-hit effects: (side index, reason string).
struct PendingSwitch {
    int side_idx;
    std::string reason;
};

// Scalar args reconstructing the HitContext + call site for _apply_post_hit_effects.
struct PostHitArgs {
    int side_idx;
    int defender_idx;
    int32_t move;
    int32_t move_type;
    int damage;
    int actual_damage;
    bool hit_sub;
    int effective_slot;
    int attacker_slot;
    // Pointer to ExecCtx.competitive_defiant_triggered[2] (Defiant/Competitive once-per-turn
    // dedup). nullptr = no dedup (fire unconditionally).
    bool* competitive_defiant_triggered = nullptr;
    // ExecCtx for eject_pack signaling: change_stat_stage appends to ctx->eject_pack_sides
    // when non-null; throws "unported: eject_pack" when null.
    ExecCtx* ctx = nullptr;
};

// _apply_post_hit_effects: full post-damage reaction pipeline. Mutates state in place and
// appends forced-switch requests to pending_switches. Unported branches throw loudly.
void cpp_apply_post_hit_effects(BattleState& state, const PostHitArgs& args,
                                std::vector<PendingSwitch>& pending_switches,
                                const EffectsLuck& luck);

// release_inflicted_traps(sides, departed_side_idx, departed_team_idx): strip BOUND/TRAPPED
// (and their SOURCE_ID companions) from every active victim on the opponent's side whose trap
// was inflicted by the departed mon. Mirrors Python's faint_active -> release_inflicted_traps.
void cpp_release_inflicted_traps(BattleState& state, int departed_side_idx,
                                 int32_t departed_team_idx);

// faint_active(sides, side_idx, notify_soul_heart, slot=0): canonical faint transition mirroring
// Python's faint_active. Idempotent; sets hp=0/fainted=true, releases inflicted traps, optionally
// notifies Soul-Heart. Does NOT emit a FAINT log; callers keep their own.
void cpp_faint_active(BattleState& state, int side_idx, bool notify_soul_heart, int slot = 0);

#endif // NUZLOCKE_EFFECTS_H
