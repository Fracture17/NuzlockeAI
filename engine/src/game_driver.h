// Resumable GameDriver wrapping the cpp_run_one_turn unified loop (turn.h) with oracle
// pause/resume support. On Category-A events, the driver can pause and surface a NeedsRNG
// request to the caller, who supplies an answer and calls step() again to resume.
// Overrides can also be pre-set so the event resolves without pausing.
#pragma once
#ifndef NUZLOCKE_GAME_DRIVER_H
#define NUZLOCKE_GAME_DRIVER_H

#include "state.h"
#include "move_exec.h"          // ExecAction
#include "move_exec_damage.h"   // DamageLoopLuck
#include "core_leaf.h"          // TurnLuck, Entry
#include "move_exec_guards.h"   // ExecCtx
#include "oracle.h"             // OracleOverrides, NeedsRNG, OracleAnswer, RngEventC
#include "orchestrate.h"        // GameResult, cpp_run_game helpers, cpp_action_from_json
#include "turn.h"               // ActionSnapshot, TurnPause (moved here from game_driver.h)
#include "policy.h"
#include "forced_trace.h"
#include "replay_policy.h"
#include <nlohmann/json.hpp>
#include <memory>
#include <optional>
#include <string>
#include <vector>

// Resumable multi-turn game driver. Owns all game state.
// step()         → runs forward until DONE or NeedsRNG; returns result JSON.
// step(answer)   → resumes from a NeedsRNG pause with the supplied answer.
// Result JSON:
//   pending: {"status":"pending","event":<int>,"options":[...],"state":{...}}
//   done:    {"status":"done"|"max_turns","winner":<int|null>,"state":{...},"action_log":[...]}
struct GameDriver {
    // Construct from JSON args (same keys as run_game: state, seed, luck_p0/p1, turn_luck, max_turns,
    // policy_p0/p1, overrides{effect_spore_which:int}).
    explicit GameDriver(const std::string& args_json);

    // Advance until pause or done. Returns result JSON.
    std::string step();

    // Resume from a NeedsRNG pause by injecting an answer, then continue.
    // answer_json: {"i0":<int>} (plus "i1" for the two-pick MOODY_STATS event).
    std::string step(const std::string& answer_json);

private:
    // Run forward from current position. Returns result JSON.
    std::string _run();

    // Serialize the current paused result.
    std::string _make_pending_result() const;

    // Serialize the done/max_turns result.
    std::string _make_done_result() const;

    // ---- persistent game state ----
    BattleState state_;
    uint64_t seed_;
    DamageLoopLuck lp0_tmpl_, lp1_tmpl_;
    TurnLuck tl0_, tl1_;
    int max_turns_;
    std::string policy_p0_, policy_p1_;
    OracleOverrides overrides_;

    std::unique_ptr<Policy> p0_;
    std::unique_ptr<Policy> p1_;
    Policy* policies_[2];

    // Shared NativeRng for the game (non-null if any side uses random_mode).
    std::unique_ptr<NativeRng> game_rng_;

    // Forced-trace replay state (null in normal mode).
    std::unique_ptr<ForcedTrace> forced_;
    std::unique_ptr<ReplayPolicy> replay_p0_;
    std::unique_ptr<ReplayPolicy> replay_p1_;

    nlohmann::json action_log_;
    int turn_count_ = 0;

    // ---- pause state ----
    bool paused_ = false;
    bool done_ = false;
    std::optional<TurnPause> pending_pause_;  // set when paused_=true

    // Per-turn state (actions chosen, luck copies) — replayed on resume.
    std::vector<ExecAction> cur_actions0_, cur_actions1_;
};

#endif // NUZLOCKE_GAME_DRIVER_H
