// C1.7d Unit 1: shared mutating leaf helpers ported from src/engine/_helpers.py and core.py.
// Central HP-removal (_apply_damage), Rocky Helmet recoil, Gulp Missile projectile, on-KO ability
// boosts, PP consumption + Leppa, Unburden flag, stockpile reset, rollout counter. Units 2-5 call
// these. Uncontrolled-oracle/random_mode branches with rng=nullptr throw loudly.
#pragma once
#ifndef NUZLOCKE_MOVE_EXEC_HELPERS_H
#define NUZLOCKE_MOVE_EXEC_HELPERS_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include "oracle.h"       // OracleOverrides
#include <cstdint>

// Deterministic injectable-luck subset consumed by the resolvers reached here (resolve_proc:
// Focus Band 10% survival, Shell Side Arm 50% contact tie).
// random_mode=true: rng must be non-null; random_mode=false: rng may be null.
struct MoveExecLuck {
    double proc_threshold = 0.0;  // resolve_proc fires iff chance >= proc_threshold
    bool   random_mode    = false;
    NativeRng* rng        = nullptr;  // non-null iff random_mode=true
    const OracleOverrides* overrides = nullptr;  // threaded from DamageLoopLuck; null on plain path
};

// _apply_damage: remove `damage` HP from the active mon on defender_idx (active slot defender_slot),
// applying Endure / Focus Band / Focus Sash / Sturdy survival, HP clamp, per-turn damage tracking,
// and (when not fainted) the post-hit HP-threshold berry. move_category < 0 means None (no tracking).
// opp_side_idx < 0 means None (no Unnerve suppression). Returns HP actually removed (pre-berry-heal).
// Starf Berry's oracle stat pick escapes as a NeedsRNG event reaching the GameDriver's pause handler.
int32_t cpp_apply_damage(BattleState& state, int defender_idx, int32_t damage,
                         int32_t attacker_ability, const MoveExecLuck& luck,
                         int32_t move_category, int opp_side_idx, int defender_slot);

// _apply_rocky_helmet: contact recoil to the attacker (1/6 max, min 1), gated by Long Reach /
// Protective Pads / Magic Guard / Rocky Helmet held / not already fainted. Fires on a lethal hit.
// Shell Side Arm's physical/special tie uses resolve_proc(50) → random_mode throws.
void cpp_apply_rocky_helmet(BattleState& state, int side_idx, int defender_idx,
                            int32_t move, const MoveExecLuck& luck);

// _apply_gulp_missile_projectile: Cramorant Gulping/Gorging projectile (1/4 attacker max), Gulping
// → attacker Def -1, Gorging → paralysis; then revert defender to base Cramorant. No-op off-form.
void cpp_apply_gulp_missile_projectile(BattleState& state, int defender_idx, int attacker_idx);

// _apply_on_ko_effects: attacker on-KO ability boosts. Moxie/Chilling Neigh/As One(G) +1 Atk;
// Grim Neigh/As One(S) +1 SpA; Beast Boost +1 to the single highest RAW non-HP stat; Battle Bond
// (Greninja-Bond) +1 Atk/SpA/Spe then Ash form.
void cpp_apply_on_ko_effects(BattleState& state, int attacker_idx);

// _consume_pp: decrement move_pp[slot] by 1+extra_pp (floored at 0). slot < 0 throws (sentinel).
void cpp_consume_pp(BattleState& state, int side_idx, int slot, int extra_pp);

// _check_leppa_berry: restore PP to 10 (20 w/ Ripen) when move_pp[slot] hit 0 and Leppa held.
// opp_side_idx < 0 means None. Returns true if consumed.
bool cpp_check_leppa_berry(BattleState& state, int side_idx, int slot, int opp_side_idx);

// _bump_rollout_counter: increment Rollout/Ice Ball hit counter on damage; resets after 5 hits.
void cpp_bump_rollout_counter(BattleState& state, int side_idx, int32_t move, int32_t total_damage);

// _reset_stockpile: zero stockpile counter/boosts, revert the accumulated Def/SpD stat stages.
void cpp_reset_stockpile(BattleState& state, int side_idx);

#endif // NUZLOCKE_MOVE_EXEC_HELPERS_H
