// C1.7d Unit 3: the pre-damage guard chain + accuracy, ported from src/engine/core.py.
// Covers _handle_pre_damage_checks (two-turn charge/release, Future Sight, Imprison, Fake Out,
// Belch, Poltergeist, Destiny Bond clear, Throat Chop) and _handle_pre_damage_guards
// (move-specific fail guards, accuracy + miss consequences, priority/protection guards incl.
// doubles redirect, ability/item immunity, move-type resolution). Mutates the live BattleState.
// random_mode=true requires rng non-null in GuardLuck; random_mode=false is unaffected.
#pragma once
#ifndef NUZLOCKE_MOVE_EXEC_GUARDS_H
#define NUZLOCKE_MOVE_EXEC_GUARDS_H

#include "state.h"
#include "native_rng.h"   // NativeRng
#include "oracle.h"       // OracleOverrides
#include <cstdint>

struct MoveData;

// ---------------------------------------------------------------------------
// ExecCtx: the TurnContext reduced to flat scalars (TurnContext is NOT part of
// BattleState). Units 4 & 5 reuse and may extend this struct. Each field below
// mirrors a TurnContext member read by the guard chain.
// ---------------------------------------------------------------------------
struct ExecCtx {
    // Original active-slot position (0 or 1) of the acting Pokemon before slot-swap.
    int32_t attacker_slot = 0;

    // Per-side Protect state. protected_sides[i] = side i is protected this turn.
    // protect_move[i] = the Move id that granted side i's protection (-1 = none); drives the
    // contact penalty (King's Shield / Spiky Shield / Baneful Bunker / Obstruct).
    bool    protected_sides[2] = {false, false};
    int32_t protect_move[2]    = {-1, -1};

    // Per-side Wide Guard / Quick Guard state for this turn.
    bool    wide_guard_sides[2]  = {false, false};
    bool    quick_guard_sides[2] = {false, false};

    // The opponent's submitted Action (for Sucker Punch). opp_action_present=false means
    // ctx.actions has no entry for the defender (treated as a fail for Sucker Punch).
    // opp_action_kind: 0=MOVE, 1=SWITCH. opp_action_move_override = -1 means None.
    bool    opp_action_present       = false;
    int32_t opp_action_kind          = 0;
    int32_t opp_action_move_slot     = -1;
    int32_t opp_action_move_override = -1;

    // Defiant/Competitive once-per-turn dedup (mirrors TurnContext.competitive_defiant_triggered,
    // a per-side set shared across the whole turn — NOT reset per actor). Index = receiving side.
    bool competitive_defiant_triggered[2] = {false, false};

    // Unit 5: per-opponent-slot EXP participant sets (ctx.exp_participants). Used by the switch
    // handler (reset the switching slot's set when side 1 switches) and the EXP flush. The U3/U4
    // decoders leave this empty (has_exp_participants=false); only execute_action populates it.
    bool has_exp_participants = false;
    std::vector<std::vector<int32_t>> exp_participants;

    // Mirrors TurnContext.eject_pack_sides: sides where Eject Pack consumed during this action.
    // change_stat_stage appends the side index here instead of throwing. cpp_run_one_turn drains
    // this after each mover (same point Python drains eject_pack_sides in _advance_queue).
    std::vector<int32_t> eject_pack_sides;

    // Oracle override map for Category-A events. null = no overrides (all events throw NeedsRNG
    // or the legacy "unported:" runtime_error when not wired). Non-null = look up answer first.
    const OracleOverrides* overrides = nullptr;
};

// Deterministic injectable-luck subset for the resolvers reached here. accuracy_threshold drives
// resolve_accuracy; proc_threshold threads into the protect-contact / immunity helpers.
// random_mode=true: rng must be non-null; random_mode=false: rng may be null.
struct GuardLuck {
    double accuracy_threshold = 50.0;
    double proc_threshold     = 0.0;
    bool   random_mode        = false;
    NativeRng* rng            = nullptr;  // non-null iff random_mode=true
};

// Result of the guard chain. should_abort=true means the caller returns immediately.
// On proceed, move_type/effective_acc carry the resolved values (effective_acc_is_none mirrors
// Python's None = always-hit sentinel; move_type=-1 only when aborted before resolution).
struct GuardResult {
    bool    should_abort         = false;
    int32_t move_type            = -1;
    double  effective_acc        = 0.0;
    bool    effective_acc_is_none = true;
};

// _handle_pre_damage_checks: abort-early checks before damage (two-turn charge/release, Future
// Sight/Doom Desire, Imprison, Fake Out/First Impression, Belch, Poltergeist, Destiny Bond clear,
// Throat Chop). Returns true if the move should proceed, false to abort. Mutates state in place.
bool cpp_pre_damage_checks(BattleState& state, int side_idx, int defender_idx,
                           int32_t move, const GuardLuck& luck, const ExecCtx& ctx,
                           int effective_slot);

// _handle_pre_damage_guards: full guard chain for a damaging move. Mutates state in place.
// ctx is mutated in C++ via the returned struct's redirect fields if needed (Feint clears
// protection — surfaced through the result so the probe can echo it back; not needed here since
// the test re-derives ctx each call). Returns the GuardResult.
GuardResult cpp_pre_damage_guards(BattleState& state, int side_idx, int defender_idx,
                                  int32_t move, const GuardLuck& luck_atk,
                                  const GuardLuck& luck_def, ExecCtx& ctx);

// Exported wrapper around the file-local _apply_protect_contact_penalty, so Unit 5's status
// path can reuse it (King's Shield / Spiky Shield / Baneful Bunker / Obstruct on contact).
void cpp_apply_protect_contact_penalty(BattleState& state, int attacker_idx, int defender_idx,
                                       int32_t move, const MoveData& md, const ExecCtx& ctx);

// Stateful absorption check: returns true (and mutates state) when the move is absorbed/blocked
// by the defender's ability or item. attacker_side_idx = the move's user.
bool check_type_immunity(BattleState& state, int attacker_side_idx, int32_t move_type, int32_t move);

#endif // NUZLOCKE_MOVE_EXEC_GUARDS_H
