// C1.7e/Stage-4/Stage-5b: the unified single-turn driver (plain + oracle).
// (_begin_turn / _advance_queue / _finish_turn / _check_fainted / _finalize_turn + EOT helpers).
// Singles and doubles (Stage 4). Plain mode (overrides==nullptr): deterministic, NeedsRNG propagates
// unchanged, sub_move in controlled mode throws "unported: sub_move". Oracle mode (overrides!=nullptr):
// per-action snapshot, NeedsRNG→TurnPause restore; resume_snap non-null skips _begin_turn.
#pragma once
#ifndef NUZLOCKE_TURN_H
#define NUZLOCKE_TURN_H

#include "state.h"
#include "move_exec.h"          // ExecAction
#include "move_exec_damage.h"   // DamageLoopLuck
#include "move_exec_guards.h"   // ExecCtx
#include "core_leaf.h"          // TurnLuck, Entry
#include "oracle.h"             // OracleOverrides, NeedsRNG
#include "policy.h"             // Policy
#include <nlohmann/json.hpp>
#include <vector>

// Mega table row: maps a held item id to its mega/primal form, ability, and pre-evolution species.
struct MegaEntry { int32_t item; int32_t mega_species; int32_t mega_ability; int32_t pre_species; };

// Look up a MegaEntry by item id. Returns nullptr if the item has no mega/primal entry.
const MegaEntry* cpp_find_mega_entry(int32_t item);

// Returns true if the item is a Primal Orb (Red Orb or Blue Orb).
bool cpp_is_primal_orb(int32_t item);

// Returns true if Trick Room is active in the given battle state.
bool cpp_turn_has_trick_room(const BattleState& s);

// Snapshot of per-turn state taken before each action, used to restore on NeedsRNG pause.
struct ActionSnapshot {
    BattleState state;
    ExecCtx ctx;
    std::vector<std::vector<int32_t>> exp_participants;
    std::vector<Entry> pending;           // remaining entries including the current one
    std::vector<std::pair<int,int>> turn_start_active;
    bool mega_p0 = false;
    bool mega_p1 = false;
    // Luck copies (per-turn fresh copies, so they capture any turn-init mutations).
    DamageLoopLuck lp0;
    DamageLoopLuck lp1;
};

// Thrown internally when a NeedsRNG is caught mid-turn; carries both the oracle request
// and the pre-action snapshot so GameDriver can restore and resume.
struct TurnPause {
    NeedsRNG needs;
    ActionSnapshot snapshot;
};

// cpp_run_one_turn: run ONE full turn in place. On success, state is the post-turn BattleState
// (turn_number incremented, prev_turn_order set, exp_participants committed). Accepts a list of
// actions per side: one element for singles, two for doubles (each with source_slot set).
// Plain mode (overrides==nullptr): NeedsRNG propagates unchanged; controlled sub_move throws
//   "unported: sub_move". No per-action snapshots — plain whole-game runner pays no extra cost.
// Oracle mode (overrides!=nullptr): threads overrides into ExecCtx; per-action snapshot built each
//   iteration; NeedsRNG→restore snapshot+throw TurnPause. resume_snap non-null skips _begin_turn.
// finalize_on_post_faint=false (default): throw "unported: post_faint_switch" when a fainted
//   active has bench replacements available — used by the Python bridge (run_one_turn binding).
// finalize_on_post_faint=true: instead of throwing, run _finalize_turn normally and return,
//   leaving fainted actives in place — used by cpp_run_game so exp_participants is committed.
// policies: nullable two-element array [side0, side1] for forced-switch selection (pivot moves)
//   and phaze oracle draws. When null, any pending switch throws "unported: pending_switch".
// action_log: nullable JSON array; when non-null, forced_switch entries are appended here.
// mega_p0/mega_p1: scalar bools — doubles mega is slot-0 only (mirrors Python simulator.py).
// forced_tie: nullable plain-mode SPEED_TIE ordering (sweep replay hook). When non-null, a
//   controlled cross-side MOVE speed tie is resolved by this ordering's rank instead of throwing
//   NeedsRNG — sticky/re-fired for the whole turn (mirrors OLD sweep pre_rng_inject re-fire). No
//   effect in oracle mode (overrides takes precedence) or when no tie occurs. nullptr = today.
void cpp_run_one_turn(BattleState& state,
                      const std::vector<ExecAction>& actions_p0,
                      const std::vector<ExecAction>& actions_p1,
                      DamageLoopLuck& luck_p0, DamageLoopLuck& luck_p1,
                      const TurnLuck& tl0, const TurnLuck& tl1,
                      bool mega_p0, bool mega_p1,
                      bool finalize_on_post_faint = false,
                      Policy* policies[2] = nullptr,
                      nlohmann::json* action_log = nullptr,
                      const OracleOverrides* overrides = nullptr,
                      const ActionSnapshot* resume_snap = nullptr,
                      const SpeedTieOrder* forced_tie = nullptr);

#endif // NUZLOCKE_TURN_H
