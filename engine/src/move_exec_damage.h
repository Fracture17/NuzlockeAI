// C1.7d Unit 4: the damage hit-loop body, ported from src/engine/core.py.
// Covers _handle_damage_action (spread/redirect target loop + post-hit), the inner
// _handle_damage_loop (multi-hit loop: hit count, per-hit damage/crit overrides, Substitute,
// type-resist berry, drain, Rough Skin/Iron Barbs, Rocky Helmet, KO faint effects, Disguise),
// _apply_defender_faint_effects, and _handle_fixed_damage_action. Mutates the live BattleState.
// random_mode=true with rng=nullptr throws; random_mode=false leaves rng unused (null OK).
#pragma once
#ifndef NUZLOCKE_MOVE_EXEC_DAMAGE_H
#define NUZLOCKE_MOVE_EXEC_DAMAGE_H

#include "state.h"
#include "move_exec_guards.h"   // ExecCtx
#include "effects.h"            // PendingSwitch
#include "native_rng.h"         // NativeRng
#include "oracle.h"             // OracleOverrides
#include <cstdint>
#include <unordered_map>
#include <vector>

// Deterministic injectable-luck subset consumed by the hit loop's resolvers. crit_threshold +
// damage_roll feed cpp_calculate_damage; multi_hit_roll feeds resolve_multi_hit; the per-hit arrays
// override damage_roll/crit_threshold for multi-hit moves (empty + *_present=false means None).
// proc_threshold/secondary_threshold thread into the post-hit + leaf helpers.
// random_mode=true: rng must be non-null (cpp_run_game seeds and threads it); else throws.
struct DamageLoopLuck {
    double crit_threshold      = 50.0;
    double damage_roll         = 0.5;
    double proc_threshold      = 50.0;
    double secondary_threshold = 50.0;
    double multi_hit_roll      = 0.5;
    double rampage_duration_roll = 0.5;         // resolve_rampage_duration: >=0.5 -> 3 turns else 2
    std::vector<double> damage_rolls_per_hit;   // present iff damage_rolls_present
    std::vector<double> crits_per_hit;          // present iff crits_present
    bool damage_rolls_present = false;
    bool crits_present        = false;
    bool random_mode          = false;
    NativeRng* rng            = nullptr;  // non-null iff random_mode=true
    const OracleOverrides* overrides = nullptr;  // threaded from GameDriver; null on plain run_game path
    // Plain-mode pre-inject map; nullptr = absent key → byte-identical path.
    const std::unordered_map<int,int>* pre_inject = nullptr;

    // Unit 5: remaining LuckProfile fields so a Dancer re-trigger (which re-runs the full move body)
    // can rebuild the sub-luck structs (PreMove/Guard/Effects/Psywave). The U4 decoder leaves these
    // at defaults; only the U5 execute_action path populates them.
    double accuracy_threshold           = 50.0;
    double psywave_roll                 = 0.5;
    double flinch_threshold             = 50.0;
    double binding_duration_roll        = 0.5;
    double wake_threshold               = 50.0;
    double defrost_threshold            = 20.0;
    double paralysis_threshold          = 50.0;
    double confusion_snap_threshold     = 50.0;
    double confusion_self_hit_threshold = 50.0;
    double attract_threshold            = 50.0;
};

// _handle_damage_action: resolve targets (+ doubles spread penalty / Follow Me / Rage Powder
// redirect), run the damage loop per target, apply post-hit effects, bump Rollout, reset Spit Up.
// Dancer re-trigger (damaging dance move, not from_dancer) is out of Unit-4 scope -> fail-loud.
// effective_acc_is_none mirrors Python's None (always-hit) accuracy sentinel.
void cpp_handle_damage_action(BattleState& state, int side_idx, int defender_idx,
                              int32_t move, int32_t move_type, ExecCtx& ctx,
                              const DamageLoopLuck& luck_atk, const DamageLoopLuck& luck_def,
                              int effective_slot, double effective_acc, bool effective_acc_is_none,
                              bool from_dancer, int target_side, int target_slot,
                              std::vector<PendingSwitch>& pending_switches);

// _handle_fixed_damage_action: -2 fail -> MOVE_FAIL + post-hit; >=0 -> type-immunity check, fixed
// damage, faint/on-KO, Final Gambit self-faint, Rocky Helmet, post-hit. Mutates state in place.
void cpp_handle_fixed_damage_action(BattleState& state, int side_idx, int defender_idx,
                                    int32_t move, int32_t move_type, int32_t fixed_dmg,
                                    ExecCtx& ctx, const DamageLoopLuck& luck_atk,
                                    const DamageLoopLuck& luck_def, int effective_slot,
                                    std::vector<PendingSwitch>& pending_switches);

#endif // NUZLOCKE_MOVE_EXEC_DAMAGE_H
