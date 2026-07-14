// C1.7h Stage 1+2+3+4 / C1.7i Stage 6: pure-C++ multi-turn orchestration + legal-action enumeration.
// Stage 1: _apply_switch (post-faint path), _is_battle_over, _compute_winner.
// Stage 2: enumerate_legal_actions — mirrors Python src/engine/actions.py exactly (mega omitted).
// Stage 3: cpp_run_game — full multi-turn game loop mirroring Python Simulator clean path.
// Stage 4: Baton Pass state transfer in cpp_apply_switch (stat_stages, volatiles, timed_volatiles, crit_stage, sub_hp).
// Stage 6: cpp_run_game accepts optional policy_p0/policy_p1 ("random"|"ai"); default "random" preserves backward compat.
#pragma once
#ifndef NUZLOCKE_ORCHESTRATE_H
#define NUZLOCKE_ORCHESTRATE_H

#include "state.h"
#include "move_exec.h"
#include "turn.h"
#include "policy.h"
#include "ai_policy.h"
#include <nlohmann/json.hpp>
#include <memory>
#include <optional>
#include <utility>
#include <vector>
#include <string>

struct ExecCtx;  // forward; full definition in move_exec_guards.h

// Post-faint switch primitive mirroring Python _apply_switch (effects.py:514).
// Clears exp_participants[source_slot] from state (committed field) when side_idx==1.
// Transfers Baton Pass state (stat_stages, volatiles, timed_volatiles, crit_stage, sub_hp) if pending.
// ctx: when non-null, threaded to cpp_apply_entry_effects for eject_pack signaling on entry.
void cpp_apply_switch(BattleState& state, int side_idx, int new_slot, int source_slot = 0,
                      ExecCtx* ctx = nullptr);

// Returns true if either side has all team members fainted. Mirrors _is_battle_over.
bool cpp_battle_over(const BattleState& state);

// Returns winner side index (0 or 1), or std::nullopt for draw/ongoing. Mirrors _compute_winner.
std::optional<int> cpp_compute_winner(const BattleState& state);

// All legal ExecActions for a side/slot this turn. Mirrors Python enumerate_legal_actions
// (actions.py:44) exactly in branch order. Mega variants are intentionally omitted (deferred).
// Struggle uses move_slot=-2, move_override=165 (Move.STRUGGLE) — same sentinel as Python
// STRUGGLE_SLOT / _struggle_action().
std::vector<ExecAction> cpp_enumerate_legal_actions(const BattleState& state,
                                                     int side_idx, int slot = 0);

// Result of a full multi-turn game run.
struct GameResult {
    BattleState final_state;
    std::optional<int> winner;
    int turn_count;
    nlohmann::json action_log;   // ordered list: {phase,p0,p1} entries
    std::string status;          // "completed" | "max_turns" | "unported:<reason>"
    // Per-turn state snapshots (post-turn, post-drain), one per completed turn. Empty unless
    // debug_snapshots=true. Used by the Stage 5 parity gate's --per-turn debug mode to localize
    // the first divergent turn rather than only detecting terminal mismatch.
    std::vector<BattleState> turn_states;
    // Per-AI-decision records for structural gate. Empty unless debug_ai_decisions=true.
    // Each entry: {ctx: "normal"|"post_faint"|"forced_pivot", side: int,
    //              state: <battle_state_json>, action: <action_dict>}.
    // "normal" = select(), "post_faint"/"forced_pivot" = select_switch().
    // Phaze decisions (select_phaze) are NOT recorded — they are game-mechanic randoms.
    nlohmann::json ai_decisions;
};

// Serialize an ExecAction to JSON dict (mirrors the action_log format for replay).
nlohmann::json cpp_action_to_json(const ExecAction& a);

// Deserialize an ExecAction from a JSON dict (reverse of cpp_action_to_json).
// Handles both action_log format and forced_trace actions_p0/p1 entries.
ExecAction cpp_action_from_json(const nlohmann::json& aj);

// Build the post-faint replacement queue: (side, slot_pos) pairs for fainted actives with live bench.
// Mirrors Python _check_fainted (simulator.py:815).
std::vector<std::pair<int,int>> cpp_build_faint_queue(const BattleState& state);

// Check and apply one Emergency Exit / Wimp Out switch on entry to hazards.
// Returns the new team_idx of the replacement (>=0) or -1 if no crossing / no bench.
// Captures *next_hp_before_out = incoming replacement's HP before their hazards (if non-null).
// NeedsRNG propagates out in plain mode; oracle mode throws NeedsRNG via oracle_resolve.
int cpp_entry_ee_step(BattleState& state, int si, int active_team_idx,
                      int32_t hp_before_hazards,
                      Policy* policies[2],
                      std::vector<std::vector<int32_t>>& exp_participants,
                      const OracleOverrides* overrides,
                      NativeRng* rng, ExecCtx* ctx,
                      nlohmann::json* action_log,
                      int32_t* next_hp_before_out);

// Drain the faint queue via policies; appends post_faint entries to action_log.
// Rebuilds the queue after each pass until no fainted active with live bench remains
// (re-prompts replacements killed by entry hazards; record faint_queue_no_rebuild_bug).
// overrides/rng: optional oracle context for EE entry-hazard chain resolution.
void cpp_drain_faint_queue(BattleState& state,
                            std::vector<std::pair<int,int>>& faint_queue,
                            Policy* policies[2],
                            nlohmann::json& action_log,
                            const OracleOverrides* overrides = nullptr,
                            NativeRng* rng = nullptr);

// Construct a Policy by kind ("random" or "ai"). Throws loudly on unknown kind.
std::unique_ptr<Policy> cpp_make_policy(const std::string& kind, uint64_t seed);

// Full multi-turn game loop mirroring Python Simulator clean-path state machine (singles, slot 0).
// luck_p0_tmpl/luck_p1_tmpl are pinned templates; a fresh copy is made every turn so cpp_run_one_turn
// cannot mutate the templates. On "unported:" runtime_error, returns immediately with partial log.
// When debug_snapshots=true, GameResult.turn_states records the state after each completed turn.
// policy_p0/policy_p1: "random" (default) or "ai". Unknown strings throw std::runtime_error.
// Backward compat: callers omitting these params get the same random-vs-random behavior as before.
// debug_ai_decisions: when true, GameResult.ai_decisions records every AI normal/switch decision.
GameResult cpp_run_game(BattleState state, uint64_t seed,
                        const DamageLoopLuck& luck_p0_tmpl, const DamageLoopLuck& luck_p1_tmpl,
                        const TurnLuck& tl0, const TurnLuck& tl1, int max_turns,
                        bool debug_snapshots = false,
                        const std::string& policy_p0 = "random",
                        const std::string& policy_p1 = "random",
                        bool debug_ai_decisions = false);

#endif // NUZLOCKE_ORCHESTRATE_H
