// Stage 2+3 AI scorer: score distributions for actions and deterministic switch scoring.
// Ports: src/ai.py _dist_*, _dist_action, _blend_damage_dist, _post_ko_switch_score,
//   _cond2_valid_slots, _has_valid_switch_candidate, _select_voluntary_switch_target,
//   select_post_ko_switch.
// Public interface: cpp_dist_action, cpp_blend_damage_dist, cpp_ai_faster,
//   and the Stage-3 switch functions.
#pragma once
#ifndef NUZLOCKE_AI_SCORER_H
#define NUZLOCKE_AI_SCORER_H

#include "state.h"
#include "move_exec.h"   // ExecAction

#include <cstdint>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

// Thrown by the switch-target selectors when no valid candidate exists.
// Callers that treat "no candidate" as a legitimate outcome must catch THIS
// type specifically — never std::runtime_error — so real engine errors stay loud.
struct NoSwitchCandidate : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// Score distribution: list of (score, probability) pairs (not necessarily canonical).
using ScoreDistC = std::vector<std::pair<int32_t, double>>;

// Full score distribution for a single action (mirrors Python _dist_action).
// p_highest: P(this move is highest damage); kills: whether it KOs the opponent.
// ai_fst: true if AI acts before the player this turn.
ScoreDistC cpp_dist_action(const BattleState& state, int ai_idx, const ExecAction& action,
                           double p_highest, bool kills, bool ai_fst);

// Blend three _dist_action branches by (p_kill, p_nokill) weights (mirrors _blend_damage_dist).
ScoreDistC cpp_blend_damage_dist(const BattleState& state, int ai_idx, const ExecAction& action,
                                 double p_kill, double p_nokill, bool ai_fst);

// True if AI's effective speed >= player's (ties count as AI faster, per AI.md).
bool cpp_ai_faster(const BattleState& state, int ai_idx);

// ---------------------------------------------------------------------------
// Stage 3: deterministic switch scoring/selection (mirrors src/ai.py lines 1490-1641)
// ---------------------------------------------------------------------------

// Post-KO switch-in score for bench_mon against player_active (mirrors _post_ko_switch_score).
// Higher = better. Ditto: +2 additive. Wynaut/Wobbuffet: +2 unless slower AND player OHKOs.
// 7-tier general scoring uses _MAX_DAMAGE_LUCK with rollout_max_bp=True, check_pp=False.
int cpp_post_ko_switch_score(const PokemonState& bench, const PokemonState& player_active,
                             const BattleState& state);

// Voluntary-switch candidate filter (mirrors _cond2_valid_slots).
// MUST replicate the found_faster bug: once a faster non-OHKO'd mon is found in party order,
// subsequent slower mons enter the faster-branch too.
std::set<int> cpp_cond2_valid_slots(const BattleState& state, int ai_idx);

// True iff cpp_cond2_valid_slots is non-empty (mirrors _has_valid_switch_candidate).
bool cpp_has_valid_switch_candidate(const BattleState& state, int ai_idx);

// Best cond2-valid slot by score; ties broken by party order (first wins).
// Throws NoSwitchCandidate if no cond2 slots exist.
int cpp_select_voluntary_switch_target(const BattleState& state, int ai_idx);

// Best non-fainted bench slot by score; ties broken by party order.
// Throws NoSwitchCandidate if all bench mons are fainted.
int cpp_select_post_ko_switch(const BattleState& state, int ai_idx);

#endif // NUZLOCKE_AI_SCORER_H
