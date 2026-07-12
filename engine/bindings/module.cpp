// pybind11 module for nuzlocke_engine_cpp.
// Exposes the permanent single-turn driver `run_one_turn` (used by src/cpp_bridge.py),
// the Phase-2 sweep stub seam, and the C1.7h Stage 1-3 orchestration primitives
// (apply_switch, battle_over, compute_winner, enumerate_legal_actions, run_game).
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <stdexcept>
#include <optional>

#include "codec.h"
#include "native_rng.h"
#include "state_eq.h"
#include "stats.h"
#include "lookup.h"
#include "damage.h"
#include "effects.h"
#include "residuals.h"
#include "exp.h"
#include "core_leaf.h"
#include "move_exec_helpers.h"
#include "move_exec_premove.h"
#include "move_exec_guards.h"
#include "move_exec_damage.h"
#include "move_exec.h"
#include "turn.h"
#include "orchestrate.h"
#include "policy.h"
#include "ai_policy.h"
#include "ai_damage.h"
#include "ai_scorer.h"
#include "ai_scorer_internal.h"  // exception_move_sees_kill, namespace ai_scorer
#include "ai_analytic.h"
#include "game_driver.h"
#include "logger.h"           // CategoryBInjection / CategoryBOccurrenceCounters bindings
#include "event_log.h"        // RichEventLog / RichEventEntry bindings (E1a)

namespace py = pybind11;


// Raises NotImplementedError — placeholder for the real sweep once ported.
static py::object run_candidate_sweep_cpp(py::args /*args*/, py::kwargs /*kwargs*/) {
    PyErr_SetString(PyExc_NotImplementedError,
                    "run_candidate_sweep_cpp is not yet implemented (C++ engine stub)");
    throw py::error_already_set();
}

PYBIND11_MODULE(nuzlocke_engine_cpp, m) {
    m.doc() = "NuzlockeAI C++ engine extension (C1.2 — typed structs + codec)";

    m.def("run_candidate_sweep_cpp", &run_candidate_sweep_cpp,
          "Stub seam for the C++ sweep implementation. Raises NotImplementedError.");

    m.def("is_stub", []() { return false; },
          "Returns False — engine runs full games (not a no-op stub).");

    m.def("version", []() -> std::string { return "0.2.0-stageC"; },
          "Extension version string.");

    // Full deterministic single-turn driver — the permanent C++ entry point used by the
    // Python bridge (src/cpp_bridge.py:run_one_turn_cpp). Payload keys: state, action_p0,
    // action_p1 (flat action dict for singles OR a JSON array of action dicts for doubles),
    // luck_p0, luck_p1 (DamageLoopLuck), turn_luck_p0, turn_luck_p1 (TurnLuck), mega_p0,
    // mega_p1 (bool). Returns {state} on success; pause boundaries raise RuntimeError("unported:").
    m.def("run_one_turn",
          [](const std::string& args_json) -> std::string {
              auto j = nlohmann::json::parse(args_json);
              BattleState s = battle_state_from_json(j["state"].dump());

              // Delegates to the hoisted cpp_action_from_json in orchestrate.cpp.
              auto decode_action = [](const nlohmann::json& aj) -> ExecAction {
                  return cpp_action_from_json(aj);
              };

              // Dual-shape decode: accept either a single action dict (singles, back-compat)
              // or a JSON array of action dicts (doubles).
              auto decode_actions = [&](const std::string& key) -> std::vector<ExecAction> {
                  const nlohmann::json& v = j[key];
                  std::vector<ExecAction> result;
                  if (v.is_array()) {
                      for (const auto& item : v)
                          result.push_back(decode_action(item));
                  } else {
                      result.push_back(decode_action(v));
                  }
                  return result;
              };

              std::vector<ExecAction> a0 = decode_actions("action_p0");
              std::vector<ExecAction> a1 = decode_actions("action_p1");
              DamageLoopLuck luck_p0 = damage_luck_from_json(j["luck_p0"]);
              DamageLoopLuck luck_p1 = damage_luck_from_json(j["luck_p1"]);
              TurnLuck tl0 = turn_luck_from_json(j["turn_luck_p0"]);
              TurnLuck tl1 = turn_luck_from_json(j["turn_luck_p1"]);
              bool mega_p0 = j.value("mega_p0", false);
              bool mega_p1 = j.value("mega_p1", false);
              // finalize_on_post_faint (default false): when true, a fainted active with a
              // live bench does NOT throw "unported: post_faint_switch" — the turn finalizes
              // with fainted actives in place so the caller can apply the observed replacement
              // via apply_switch between turns (sweep replay layer, E2 Task 4 decision).
              bool finalize_on_post_faint = j.value("finalize_on_post_faint", false);

              // speed_tie_order (optional, sweep replay hook): a JSON array of [side, slot]
              // pairs giving the forced act-order for a controlled cross-side speed tie. When
              // present, resolves the tie by this ordering's rank instead of throwing NeedsRNG
              // (sticky/re-fired for the whole turn). Absent → today's throwing behavior.
              SpeedTieOrder forced_tie;
              const SpeedTieOrder* forced_tie_ptr = nullptr;
              if (j.contains("speed_tie_order") && j["speed_tie_order"].is_array()) {
                  for (const auto& pair : j["speed_tie_order"])
                      forced_tie.order.emplace_back(pair.at(0).get<int>(), pair.at(1).get<int>());
                  forced_tie_ptr = &forced_tie;
              }

              // pre_inject (optional, sweep plain-mode hook): JSON object mapping event name
              // strings to int values. Supported events: METRONOME_MOVE, SLEEP_TALK_MOVE,
              // EFFECT_SPORE_WHICH, ACUPRESSURE_STAT, ROAR_TARGET, TRI_ATTACK_STATUS.
              // Sticky/non-consuming (re-used on every resolution site this turn).
              // Unknown name → throw; absent/null key → nullptr (byte-identical engine path).
              static const std::unordered_map<std::string, int> PRE_INJECT_NAME_TABLE = {
                  {"METRONOME_MOVE",    static_cast<int>(RngEventC::METRONOME_MOVE)},
                  {"SLEEP_TALK_MOVE",  static_cast<int>(RngEventC::SLEEP_TALK_MOVE)},
                  {"EFFECT_SPORE_WHICH", static_cast<int>(RngEventC::EFFECT_SPORE_WHICH)},
                  {"ACUPRESSURE_STAT", static_cast<int>(RngEventC::ACUPRESSURE_STAT)},
                  {"ROAR_TARGET",      static_cast<int>(RngEventC::ROAR_TARGET)},
                  {"TRI_ATTACK_STATUS", static_cast<int>(RngEventC::TRI_ATTACK_STATUS)},
              };
              std::unordered_map<int,int> pre_inject_map;
              const std::unordered_map<int,int>* pre_inject_ptr = nullptr;
              if (j.contains("pre_inject") && j["pre_inject"].is_object()) {
                  for (const auto& [name, val] : j["pre_inject"].items()) {
                      auto it = PRE_INJECT_NAME_TABLE.find(name);
                      if (it == PRE_INJECT_NAME_TABLE.end())
                          throw std::runtime_error("pre_inject: unknown event " + name);
                      pre_inject_map[it->second] = val.get<int>();
                  }
                  pre_inject_ptr = &pre_inject_map;
              }

              // luck_p0_slot1/luck_p1_slot1 (optional, doubles sweep replay): per-slot-1 attacker
              // luck. When present, overrides the side-level attacker luck when source_slot==1.
              // Absent → nullptr, side-level luck applies to all slots (all existing behavior).
              DamageLoopLuck luck_p0_slot1_val, luck_p1_slot1_val;
              DamageLoopLuck* luck_p0_slot1_ptr = nullptr;
              DamageLoopLuck* luck_p1_slot1_ptr = nullptr;
              if (j.contains("luck_p0_slot1") && !j["luck_p0_slot1"].is_null()) {
                  luck_p0_slot1_val = damage_luck_from_json(j["luck_p0_slot1"]);
                  luck_p0_slot1_ptr = &luck_p0_slot1_val;
              }
              if (j.contains("luck_p1_slot1") && !j["luck_p1_slot1"].is_null()) {
                  luck_p1_slot1_val = damage_luck_from_json(j["luck_p1_slot1"]);
                  luck_p1_slot1_ptr = &luck_p1_slot1_val;
              }

              cpp_run_one_turn(s, a0, a1, luck_p0, luck_p1, tl0, tl1, mega_p0, mega_p1,
                               finalize_on_post_faint, nullptr, nullptr, nullptr, nullptr,
                               forced_tie_ptr, luck_p0_slot1_ptr, luck_p1_slot1_ptr,
                               pre_inject_ptr);

              nlohmann::json out;
              out["state"] = nlohmann::json::parse(battle_state_to_json(s));
              return out.dump();
          },
          "Run one full deterministic turn: deserialize actions/luck/turn-luck, return {state}. "
          "action_p0/action_p1 may be a single dict (singles) or a list of dicts (doubles). "
          "Optional finalize_on_post_faint (default false): finalize with fainted actives in "
          "place instead of throwing, for the sweep replay layer. "
          "Optional speed_tie_order ([[side,slot],...]): force a controlled cross-side speed tie "
          "by this ordering instead of throwing NeedsRNG (sweep replay layer). "
          "Optional luck_p0_slot1/luck_p1_slot1 (DamageLoopLuck dicts): per-slot-1 attacker luck "
          "for doubles sweep replay. When present, overrides the side-level attacker luck when "
          "source_slot==1. Absent/null → side-level luck for all slots. "
          "Optional pre_inject ({event_name: int}): plain-mode sweep hook for Category-A events. "
          "Supported names: METRONOME_MOVE, SLEEP_TALK_MOVE, EFFECT_SPORE_WHICH, ACUPRESSURE_STAT, "
          "ROAR_TARGET, TRI_ATTACK_STATUS. Unknown name → RuntimeError. Absent/null → nullptr. "
          "Pause boundaries raise RuntimeError(unported:).");

    // C1.7h Stage 1+4: post-faint switch primitive. JSON-in/JSON-out.
    // Applies cpp_apply_switch in place and returns the mutated state JSON.
    // Transfers Baton Pass state (stat_stages, volatiles, timed_volatiles, crit_stage, sub_hp) if pending.
    m.def("apply_switch",
          [](const std::string& state_json, int side_idx, int new_slot, int source_slot) -> std::string {
              BattleState s = battle_state_from_json(state_json);
              cpp_apply_switch(s, side_idx, new_slot, source_slot);
              return battle_state_to_json(s);
          },
          "apply_switch(state_json, side_idx, new_slot, source_slot) -> state_json. "
          "Post-faint switch: runs switch-out reset, entry hazards, entry effects. "
          "Transfers Baton Pass state if has_baton_pass_data is set.");

    // C1.7h Stage 1: battle-over predicate. Returns True if either side is fully fainted.
    m.def("battle_over",
          [](const std::string& state_json) -> bool {
              BattleState s = battle_state_from_json(state_json);
              return cpp_battle_over(s);
          },
          "battle_over(state_json) -> bool. True if either side has all Pokemon fainted.");

    // C1.7h Stage 1: winner computation. Returns 0, 1, or None.
    m.def("compute_winner",
          [](const std::string& state_json) -> py::object {
              BattleState s = battle_state_from_json(state_json);
              std::optional<int> winner = cpp_compute_winner(s);
              if (winner.has_value()) return py::int_(*winner);
              return py::none();
          },
          "compute_winner(state_json) -> int | None. Winner side index (0 or 1), or None for draw/ongoing.");

    // C1.7h Stage 2: legal-action enumeration. Returns a list of dicts, one per ExecAction.
    // Each dict has keys: kind, move_slot, move_override, switch_to_slot, target_side, target_slot.
    // Mega variants are intentionally omitted. Struggle uses move_slot=-2, move_override=165.
    m.def("enumerate_legal_actions",
          [](const std::string& state_json, int side_idx, int slot) -> py::list {
              BattleState s = battle_state_from_json(state_json);
              std::vector<ExecAction> actions = cpp_enumerate_legal_actions(s, side_idx, slot);
              py::list result;
              for (const ExecAction& a : actions) {
                  py::dict d;
                  d["kind"]           = a.kind;
                  d["move_slot"]      = a.move_slot;
                  d["move_override"]  = a.move_override;
                  d["switch_to_slot"] = a.switch_to_slot;
                  d["target_side"]    = a.target_side;
                  d["target_slot"]    = a.target_slot;
                  result.append(d);
              }
              return result;
          },
          py::arg("state_json"), py::arg("side_idx"), py::arg("slot") = 0,
          "enumerate_legal_actions(state_json, side_idx, slot=0) -> list[dict]. "
          "All legal ExecActions for the given side/slot. Mega variants omitted. "
          "Struggle: move_slot=-2, move_override=165.");

    // C1.7h Stage 3 / C1.7i Stage 6: full multi-turn game loop. JSON-in/JSON-out.
    // Input JSON keys: state, seed (uint64), luck_p0, luck_p1 (DamageLoopLuck),
    //   turn_luck_p0, turn_luck_p1 (TurnLuck), max_turns (int),
    //   policy_p0 (str, default "random"), policy_p1 (str, default "random"),
    //   debug_ai_decisions (bool, default false).
    //   Valid policy values: "random" | "ai". Unknown values throw.
    // Output JSON: {final_state, winner (int|null), turn_count, action_log, status,
    //   ai_decisions (list, only when debug_ai_decisions=true)}.
    // status: "completed" | "max_turns" | "unported:<reason>".
    // action_log entries: {phase:"actions",p0:{...},p1:{...}} or {phase:"post_faint",p0:int|null,p1:int|null}.
    // ai_decisions entries: {ctx:"normal"|"post_faint"|"forced_pivot", side:int, state:{...}, action:{...}}.
    m.def("run_game",
          [](const std::string& args_json) -> std::string {
              auto j = nlohmann::json::parse(args_json);
              BattleState s = battle_state_from_json(j["state"].dump());
              uint64_t seed = j.value("seed", uint64_t(0));
              DamageLoopLuck lp0 = damage_luck_from_json(j["luck_p0"]);
              DamageLoopLuck lp1 = damage_luck_from_json(j["luck_p1"]);
              TurnLuck tl0 = turn_luck_from_json(j["turn_luck_p0"]);
              TurnLuck tl1 = turn_luck_from_json(j["turn_luck_p1"]);
              int max_turns = j.value("max_turns", 200);
              bool debug_snapshots = j.value("debug_snapshots", false);
              std::string policy_p0 = j.value("policy_p0", std::string("random"));
              std::string policy_p1 = j.value("policy_p1", std::string("random"));
              bool debug_ai_decisions = j.value("debug_ai_decisions", false);

              // One NativeRng per game: created iff either side requests random_mode.
              // Seeded from the game seed so results are reproducible given the same seed.
              // Both sides share one RNG stream (interleaved draws, same as a single battle RNG).
              std::unique_ptr<NativeRng> game_rng;
              if (lp0.random_mode || lp1.random_mode || tl0.random_mode || tl1.random_mode) {
                  game_rng = std::make_unique<NativeRng>(seed ^ 0xDEADBEEFCAFEBABEULL);
                  if (lp0.random_mode) lp0.rng = game_rng.get();
                  if (lp1.random_mode) lp1.rng = game_rng.get();
                  // Stage A2: turn-luck oracles (speed-tie tiebreaker, Quick Claw) share the
                  // same per-game NativeRng stream so results stay reproducible by seed.
                  if (tl0.random_mode) tl0.rng = game_rng.get();
                  if (tl1.random_mode) tl1.rng = game_rng.get();
              }

              GameResult res = cpp_run_game(s, seed, lp0, lp1, tl0, tl1, max_turns,
                                            debug_snapshots, policy_p0, policy_p1,
                                            debug_ai_decisions);

              nlohmann::json out;
              out["final_state"] = nlohmann::json::parse(battle_state_to_json(res.final_state));
              if (res.winner.has_value())
                  out["winner"] = *res.winner;
              else
                  out["winner"] = nullptr;
              out["turn_count"] = res.turn_count;
              out["action_log"] = res.action_log;
              out["status"] = res.status;
              if (debug_snapshots) {
                  nlohmann::json snaps = nlohmann::json::array();
                  for (const BattleState& ts : res.turn_states)
                      snaps.push_back(nlohmann::json::parse(battle_state_to_json(ts)));
                  out["turn_states"] = std::move(snaps);
              }
              if (debug_ai_decisions)
                  out["ai_decisions"] = res.ai_decisions;
              return out.dump();
          },
          "run_game(args_json) -> result_json. Full multi-turn game loop (singles, slot 0). "
          "Returns {final_state, winner, turn_count, action_log, status}. "
          "status: 'completed' | 'max_turns' | 'unported:<reason>'. "
          "policy_p0/policy_p1: 'random' (default) | 'ai'. "
          "debug_ai_decisions=true: adds ai_decisions list to output.");

    // C1.7i Stage 0: AI scoring seam. Returns {actions, scores, switch_target}.
    // actions: list of dicts (same 6-key shape as enumerate_legal_actions).
    // scores: list of ints parallel to actions (all zero in Stage 0).
    // switch_target: None in Stage 0 (nullopt).
    // C1.7i Stage 1: AI damage context for test-only parity validation.
    // Enumerates legal actions for ai_idx, builds the damage context (slots, roll_arrays,
    // assumed_hit_counts), and computes highest-damage probabilities against the opponent's HP.
    // Returns dict with keys: slots, roll_arrays, assumed_hit_counts, highest_probs.
    m.def("ai_damage_context",
          [](const std::string& state_json, int ai_idx) -> py::dict {
              BattleState s = battle_state_from_json(state_json);
              std::vector<ExecAction> actions = cpp_enumerate_legal_actions(s, ai_idx, 0);

              DamageContext ctx = cpp_build_damage_context(s, ai_idx, actions);

              // Opponent's active HP for highest-damage probability computation.
              const SideState& opp_side = (ai_idx == 0) ? s.side1 : s.side0;
              const PokemonState& opp_mon = opp_side.team[opp_side.active_indices[0]];
              int32_t opp_hp = opp_mon.hp;

              std::vector<std::pair<double, double>> probs =
                  cpp_compute_highest_damage_probs(ctx.roll_arrays, opp_hp);

              // Build Python return dict.
              py::list py_slots, py_rolls, py_hits, py_probs;
              for (int32_t slot : ctx.slots) py_slots.append(slot);
              for (const auto& arr : ctx.roll_arrays) {
                  py::list row;
                  for (int32_t v : arr) row.append(v);
                  py_rolls.append(row);
              }
              for (int32_t h : ctx.assumed_hit_counts) py_hits.append(h);
              for (auto& [pk, pnk] : probs) {
                  py::list pair;
                  pair.append(pk);
                  pair.append(pnk);
                  py_probs.append(pair);
              }

              py::dict out;
              out["slots"]               = py_slots;
              out["roll_arrays"]         = py_rolls;
              out["assumed_hit_counts"]  = py_hits;
              out["highest_probs"]       = py_probs;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          "ai_damage_context(state_json, ai_idx) -> dict. "
          "Enumerates legal actions, builds per-move damage context and highest-damage probs. "
          "Returns {slots, roll_arrays, assumed_hit_counts, highest_probs}.");

    // Helper: serialize one ExecAction to a Python dict (6 keys).
    auto make_action_dict = [](const ExecAction& a) -> py::dict {
        py::dict d;
        d["kind"]           = a.kind;
        d["move_slot"]      = a.move_slot;
        d["move_override"]  = a.move_override;
        d["switch_to_slot"] = a.switch_to_slot;
        d["target_side"]    = a.target_side;
        d["target_slot"]    = a.target_slot;
        return d;
    };

    // C1.7i Stage 4: stochastic AI scorer. seed controls the mt19937_64 used for
    // damage-roll sampling and score sampling. Same seed => identical results.
    // Returns {actions, scores, switch_target} where switch_target is None or a 6-key dict.
    m.def("score_ai_actions",
          [make_action_dict](const std::string& state_json, int ai_idx,
                             uint64_t seed) -> py::dict {
              BattleState s = battle_state_from_json(state_json);
              std::mt19937_64 rng(seed);
              AIScoreResult res = cpp_score_ai_actions(s, ai_idx, rng);

              py::list actions;
              for (const ExecAction& a : res.actions)
                  actions.append(make_action_dict(a));

              py::list scores;
              for (int sc : res.scores)
                  scores.append(sc);

              py::object switch_target = res.switch_target.has_value()
                  ? py::object(make_action_dict(*res.switch_target))
                  : py::none();

              py::dict out;
              out["actions"]       = actions;
              out["scores"]        = scores;
              out["switch_target"] = switch_target;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"), py::arg("seed") = uint64_t(0),
          "score_ai_actions(state_json, ai_idx, seed=0) -> dict{actions, scores, switch_target}. "
          "Stage-4 stochastic sampler: scores drawn from cpp_dist_action distributions. "
          "seed controls the mt19937_64; same seed => identical result.");

    // C1.7i Stage 4: histogram binding for the empirical parity gate.
    // Parses state once, then runs n_samples scoring calls with a single rng seeded once.
    // Returns {actions:[dict...], histograms:[{score:count}...]} with action list stable
    // across samples (action set is fixed for a given state). Score keys are ints.
    m.def("score_ai_actions_histogram",
          [make_action_dict](const std::string& state_json, int ai_idx,
                             int n_samples, uint64_t seed) -> py::dict {
              BattleState s = battle_state_from_json(state_json);
              std::mt19937_64 rng(seed);

              // action key: (kind, move_slot, move_override, switch_to_slot, target_side, target_slot)
              using ActionKey = std::tuple<int32_t,int32_t,int32_t,int32_t,int32_t,int32_t>;
              auto to_key = [](const ExecAction& a) -> ActionKey {
                  return {a.kind, a.move_slot, a.move_override,
                          a.switch_to_slot, a.target_side, a.target_slot};
              };

              // Custom hash for ActionKey (std::tuple has no default hash).
              struct AKHash {
                  size_t operator()(const ActionKey& k) const noexcept {
                      size_t h = 0;
                      auto combine = [&](auto v) {
                          h ^= std::hash<int32_t>{}((int32_t)v) + 0x9e3779b9 + (h<<6) + (h>>2);
                      };
                      combine(std::get<0>(k)); combine(std::get<1>(k));
                      combine(std::get<2>(k)); combine(std::get<3>(k));
                      combine(std::get<4>(k)); combine(std::get<5>(k));
                      return h;
                  }
              };

              // Stable ordered action list and per-action score histograms.
              std::vector<ExecAction> stable_actions;
              std::vector<std::unordered_map<int,int>> histograms;
              std::unordered_map<ActionKey, size_t, AKHash> key_idx;

              for (int sample = 0; sample < n_samples; ++sample) {
                  AIScoreResult res = cpp_score_ai_actions(s, ai_idx, rng);
                  for (size_t i = 0; i < res.actions.size(); ++i) {
                      ActionKey k = to_key(res.actions[i]);
                      auto it = key_idx.find(k);
                      size_t idx;
                      if (it == key_idx.end()) {
                          idx = stable_actions.size();
                          key_idx[k] = idx;
                          stable_actions.push_back(res.actions[i]);
                          histograms.emplace_back();
                      } else {
                          idx = it->second;
                      }
                      histograms[idx][res.scores[i]]++;
                  }
              }

              py::list py_actions, py_hists;
              for (const ExecAction& a : stable_actions)
                  py_actions.append(make_action_dict(a));
              for (const auto& hist : histograms) {
                  py::dict d;
                  for (const auto& [score, count] : hist)
                      d[py::int_(score)] = count;
                  py_hists.append(d);
              }

              py::dict out;
              out["actions"]    = py_actions;
              out["histograms"] = py_hists;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          py::arg("n_samples"), py::arg("seed") = uint64_t(0),
          "score_ai_actions_histogram(state_json, ai_idx, n_samples, seed=0) -> "
          "{actions:[dict...], histograms:[{score:count}...]}. "
          "Runs n_samples scoring calls with one rng seeded once; tallies per-action score counts. "
          "Action list is stable (ordered by first appearance). Score keys are ints.");

    // Stage 2 AI scorer: per-action score distributions.
    // Returns dict{actions, dists, ai_fst}. actions is parallel to enumerate_legal_actions.
    // dists[i] is a list of [score, prob] pairs for actions[i]. ai_fst is the speed comparison result.
    // Mirrors _py_action_dists contract: damaging moves in damage context use cpp_blend_damage_dist;
    // all others use cpp_dist_action(p_highest=0.0, kills=false).
    m.def("ai_action_dists",
          [](const std::string& state_json, int ai_idx) -> py::dict {
              BattleState s = battle_state_from_json(state_json);
              std::vector<ExecAction> actions = cpp_enumerate_legal_actions(s, ai_idx, 0);

              bool ai_fst = cpp_ai_faster(s, ai_idx);

              // Build damage context and highest-probability splits.
              DamageContext ctx = cpp_build_damage_context(s, ai_idx, actions);
              const SideState& opp_side = (ai_idx == 0) ? s.side1 : s.side0;
              int32_t opp_hp = opp_side.team[opp_side.active_indices[0]].hp;
              std::vector<std::pair<double,double>> split_probs =
                  cpp_compute_highest_damage_probs(ctx.roll_arrays, opp_hp);

              // Map move_slot → (p_kill, p_nokill) for damaging context slots.
              std::unordered_map<int32_t, std::pair<double,double>> split_by_slot;
              for (size_t i = 0; i < ctx.slots.size(); ++i)
                  split_by_slot[ctx.slots[i]] = split_probs[i];

              auto make_action_dict = [](const ExecAction& a) -> py::dict {
                  py::dict d;
                  d["kind"]           = a.kind;
                  d["move_slot"]      = a.move_slot;
                  d["move_override"]  = a.move_override;
                  d["switch_to_slot"] = a.switch_to_slot;
                  d["target_side"]    = a.target_side;
                  d["target_slot"]    = a.target_slot;
                  return d;
              };

              // Compute exception-kill flag and marginal sees_kill probability for
              // non-damaging moves: p = exc ? 1.0 : 1 − Π_j count(raw_j < opp_hp)/16
              // (rolls independent across moves, so product over all context slots).
              bool exc = ai_scorer::exception_move_sees_kill(s, ai_idx);
              double p_sees_kill_nd;
              if (exc) {
                  p_sees_kill_nd = 1.0;
              } else {
                  // Probability that NO context move kills = product of P(roll < hp) per move.
                  double p_no_kill = 1.0;
                  for (const auto& arr : ctx.roll_arrays) {
                      int count_lt = 0;
                      for (int32_t r : arr) if (r < opp_hp) ++count_lt;
                      p_no_kill *= (double)count_lt / 16.0;
                  }
                  p_sees_kill_nd = 1.0 - p_no_kill;
              }

              py::list py_actions, py_dists;
              for (const ExecAction& a : actions) {
                  py_actions.append(make_action_dict(a));

                  ScoreDistC dist;
                  auto it = split_by_slot.find(a.move_slot);
                  if (a.kind == 0 && a.move_slot >= 0 && it != split_by_slot.end()) {
                      // Damaging move in context: blend kill/nokill/none branches.
                      // sees_kill=false: damaging dists ignore the flag (no STATUS path).
                      dist = cpp_blend_damage_dist(s, ai_idx, a, it->second.first, it->second.second, ai_fst, false);
                  } else {
                      // Non-damaging: blend exact marginal p·dist(true) + (1−p)·dist(false).
                      ScoreDistC d_false = cpp_dist_action(s, ai_idx, a, 0.0, false, ai_fst, false);
                      ScoreDistC d_true  = cpp_dist_action(s, ai_idx, a, 0.0, false, ai_fst, true);
                      double p_true = p_sees_kill_nd;
                      double p_false = 1.0 - p_true;
                      std::unordered_map<int32_t, double> merged;
                      if (p_false > 0) for (auto [sc, pr] : d_false) merged[sc] += p_false * pr;
                      if (p_true  > 0) for (auto [sc, pr] : d_true)  merged[sc] += p_true  * pr;
                      for (auto& [sc, pr] : merged) dist.push_back({sc, pr});
                      std::sort(dist.begin(), dist.end());
                  }

                  py::list d_list;
                  for (auto [sc, prob] : dist) {
                      py::list pair;
                      pair.append(sc);
                      pair.append(prob);
                      d_list.append(pair);
                  }
                  py_dists.append(d_list);
              }

              py::dict out;
              out["actions"] = py_actions;
              out["dists"]   = py_dists;
              out["ai_fst"]  = ai_fst;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          "ai_action_dists(state_json, ai_idx) -> dict{actions, dists, ai_fst}. "
          "Per-action score distributions for the AI. dists[i] is a list of [score, prob] pairs. "
          "Damaging moves with context use blend_damage_dist; others use dist_action(p=0, kills=false).");

    // Stage 5: iter_damage_configs test-only binding.
    // dm_rolls: list of lists of 16 ints. hp: int. Returns list of dicts {weight, is_highest, kills}.
    m.def("iter_damage_configs",
          [](const std::vector<std::vector<int32_t>>& dm_rolls_py, int32_t hp) -> py::list {
              // Convert to vector of array<int32_t,16>
              std::vector<std::array<int32_t, 16>> dm_rolls;
              dm_rolls.reserve(dm_rolls_py.size());
              for (const auto& row : dm_rolls_py) {
                  if (row.size() != 16)
                      throw std::invalid_argument("each dm_rolls entry must have exactly 16 elements");
                  std::array<int32_t, 16> arr;
                  for (int i = 0; i < 16; ++i) arr[i] = row[i];
                  dm_rolls.push_back(arr);
              }
              auto configs = cpp_iter_damage_configs(dm_rolls, hp);
              py::list result;
              for (const DamageConfig& cfg : configs) {
                  py::dict d;
                  d["weight"] = cfg.weight;
                  py::list ih, kl;
                  for (char v : cfg.is_highest) ih.append((bool)v);
                  for (char v : cfg.kills)      kl.append((bool)v);
                  d["is_highest"] = ih;
                  d["kills"]      = kl;
                  result.append(d);
              }
              return result;
          },
          py::arg("dm_rolls"), py::arg("hp"),
          "iter_damage_configs(dm_rolls, hp) -> [{weight, is_highest, kills}]. "
          "Test-only: C++ _iter_damage_configs collapse (Stage 5).");

    // Stage 5: analytic action probability distribution.
    // Returns {actions:[dict...], probs:[float...]} parallel arrays.
    m.def("compute_action_probabilities",
          [make_action_dict](const std::string& state_json, int ai_idx) -> py::dict {
              BattleState s = battle_state_from_json(state_json);
              auto dist = cpp_compute_action_probabilities(s, ai_idx);
              py::list py_actions, py_probs;
              for (const ActionProb& ap : dist) {
                  py_actions.append(make_action_dict(ap.action));
                  py_probs.append(ap.prob);
              }
              py::dict out;
              out["actions"] = py_actions;
              out["probs"]   = py_probs;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          "compute_action_probabilities(state_json, ai_idx) -> {actions, probs}. "
          "Exact analytic probability for each legal action (Stage 5).");

    // Oracle GameDriver: resumable multi-turn driver with Category-A pause/resume support.
    // Created with a JSON args string (same keys as run_game plus optional "overrides" dict).
    // step()            → advance until DONE or NeedsRNG; returns result JSON.
    // step(answer_json) → resume from pause with {"i0": <int>}; returns result JSON.
    // Result JSON: {"status":"pending","event":<int>,"options":[...],"state":{...}}
    //           or {"status":"done"|"max_turns","winner":<int|null>,"state":{...},"action_log":[...]}
    py::class_<GameDriver>(m, "GameDriver")
        .def(py::init<const std::string&>(), py::arg("args_json"),
             "Create a GameDriver from a JSON args string (same keys as run_game + optional overrides).")
        .def("step",
             [](GameDriver& self) -> std::string { return self.step(); },
             "Advance until DONE or NeedsRNG. Returns result JSON.")
        .def("step",
             [](GameDriver& self, const std::string& answer_json) -> std::string {
                 return self.step(answer_json);
             },
             py::arg("answer_json"),
             "Resume from NeedsRNG pause with answer_json={\"i0\":<int>}. Returns result JSON.");

    // Stage 5: analytic support (actions with p>0).
    // Returns list of action dicts.
    m.def("possible_ai_actions",
          [make_action_dict](const std::string& state_json, int ai_idx) -> py::list {
              BattleState s = battle_state_from_json(state_json);
              auto actions = cpp_possible_ai_actions(s, ai_idx);
              py::list result;
              for (const ExecAction& a : actions)
                  result.append(make_action_dict(a));
              return result;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          "possible_ai_actions(state_json, ai_idx) -> [action_dict,...]. "
          "Deterministic analytic support: actions with p>0 (Stage 5).");

    // Stage 3 AI switch info: deterministic switch scoring/selection for test-only parity.
    // Returns dict{post_ko_switch, has_candidate, voluntary_target, cond2_slots, switch_scores}.
    // post_ko_switch / voluntary_target are None when the C++ function would throw (no candidates).
    // switch_scores maps slot (str key for JSON compat) -> score for every non-fainted bench slot.
    // cond2_slots: sorted list of ints.
    m.def("ai_switch_info",
          [](const std::string& state_json, int ai_idx) -> py::dict {
              BattleState s = battle_state_from_json(state_json);

              const SideState& side = (ai_idx == 0) ? s.side0 : s.side1;
              int active_slot = side.active_indices[0];
              const PokemonState& pl = (ai_idx == 0)
                  ? s.side1.team[s.side1.active_indices[0]]
                  : s.side0.team[s.side0.active_indices[0]];

              // switch_scores: every non-fainted bench slot
              py::dict switch_scores;
              for (int slot = 0; slot < (int)side.team.size(); ++slot) {
                  if (slot == active_slot || side.team[slot].fainted)
                      continue;
                  int sc = cpp_post_ko_switch_score(side.team[slot], pl, s);
                  switch_scores[py::str(std::to_string(slot))] = sc;
              }

              // post_ko_switch: None if all bench fainted
              py::object post_ko;
              try {
                  post_ko = py::int_(cpp_select_post_ko_switch(s, ai_idx));
              } catch (const NoSwitchCandidate&) {
                  post_ko = py::none();
              }

              // cond2_slots
              std::set<int> cond2 = cpp_cond2_valid_slots(s, ai_idx);
              py::list cond2_list;
              for (int slot : cond2) cond2_list.append(slot);

              bool has_cand = !cond2.empty();

              // voluntary_target: None if no cond2 slots
              py::object vol_target;
              try {
                  vol_target = py::int_(cpp_select_voluntary_switch_target(s, ai_idx));
              } catch (const NoSwitchCandidate&) {
                  vol_target = py::none();
              }

              py::dict out;
              out["post_ko_switch"]   = post_ko;
              out["has_candidate"]    = has_cand;
              out["voluntary_target"] = vol_target;
              out["cond2_slots"]      = cond2_list;
              out["switch_scores"]    = switch_scores;
              return out;
          },
          py::arg("state_json"), py::arg("ai_idx"),
          "ai_switch_info(state_json, ai_idx) -> dict. "
          "Stage-3 switch scoring: {post_ko_switch, has_candidate, voluntary_target, "
          "cond2_slots, switch_scores}. post_ko_switch/voluntary_target are None when "
          "C++ would throw (no valid candidates). switch_scores: {slot_str: score}.");

    // --- Category-B occurrence counters (D3 follow-up: GameDriver-owned per-turn reset) ---
    // Solver-side tools use these to key injection lookups by draw-occurrence within a turn.
    // GameDriver invokes reset_catb_occurrence_counters_if_registered() at each turn start.
    py::class_<CategoryBOccurrenceCounters>(m, "CategoryBOccurrenceCounters")
        .def(py::init<>())
        .def("get", [](const CategoryBOccurrenceCounters& self, int event) -> uint32_t {
            if (event < 0 || event >= (int)CategoryBOccurrenceCounters::MAX_EVENTS)
                throw std::runtime_error("event out of range");
            return self.counts[event];
        }, py::arg("event"),
           "Return the current occurrence count for the given event id (no bump).")
        .def("reset", &CategoryBOccurrenceCounters::reset,
             "Reset all counters to zero.");

    m.def("set_catb_occ_counters",
          [](CategoryBOccurrenceCounters* c) { set_catb_occ_counters(c); },
          py::arg("counters").none(true),
          "Register (or clear with None) the global CategoryBOccurrenceCounters used by "
          "GameDriver's per-turn reset.");

    // --- E1a: rich LogEvent-stream logger (event_log.h) ---
    // Mirrors the CategoryBOccurrenceCounters binding pattern. RichEventEntry fields are
    // read-only; string kwargs are int-enum tags whose strings live in the Python shim.
    py::class_<RichEventEntry>(m, "RichEventEntry")
        .def_readonly("turn", &RichEventEntry::turn)
        .def_readonly("event", &RichEventEntry::event)
        .def_readonly("species", &RichEventEntry::species)
        .def_readonly("side", &RichEventEntry::side)
        .def_readonly("amount", &RichEventEntry::amount)
        .def_readonly("stages", &RichEventEntry::stages)
        .def_readonly("attacker_side", &RichEventEntry::attacker_side)
        .def_readonly("attacker_slot", &RichEventEntry::attacker_slot)
        .def_readonly("defender_side", &RichEventEntry::defender_side)
        .def_readonly("status", &RichEventEntry::status)
        .def_readonly("new_level", &RichEventEntry::new_level)
        .def_readonly("move", &RichEventEntry::move)
        .def_readonly("stat", &RichEventEntry::stat)
        .def_readonly("hp_after", &RichEventEntry::hp_after)
        .def_readonly("aux0", &RichEventEntry::aux0)
        .def_readonly("aux1", &RichEventEntry::aux1)
        .def_readonly("source_tag", &RichEventEntry::source_tag)
        .def_readonly("volatile_tag", &RichEventEntry::volatile_tag)
        .def_readonly("cause_tag", &RichEventEntry::cause_tag);

    py::class_<RichEventLog>(m, "RichEventLog")
        .def(py::init<>())
        .def("size", &RichEventLog::size)
        .def("at", &RichEventLog::at, py::arg("i"),
             py::return_value_policy::reference_internal)
        .def("clear", &RichEventLog::clear)
        .def("__len__", &RichEventLog::size)
        .def("__getitem__", [](const RichEventLog& self, size_t i) -> const RichEventEntry& {
            if (i >= self.size()) throw py::index_error();
            return self.at(i);
        }, py::return_value_policy::reference_internal)
        .def("__iter__", [](const RichEventLog& self) {
            return py::make_iterator(self.entries.begin(), self.entries.end());
        }, py::keep_alive<0, 1>());

    m.def("set_rich_event_log",
          [](RichEventLog* log) { set_rich_event_log(log); },
          py::arg("log").none(true),
          "Register (or clear with None) the global rich LogEvent-stream logger.");

    // Emit helpers exposed so the Python shim/tests can build entries via the same
    // single source of truth as the engine (no duplicated field layout in Python).
    m.def("rich_log_charge_turn", &rich_log_charge_turn,
          py::arg("turn"), py::arg("species"), py::arg("move"));
    m.def("rich_log_semi_invuln_enter", &rich_log_semi_invuln_enter,
          py::arg("turn"), py::arg("species"), py::arg("move"));
    m.def("rich_log_semi_invuln_exit", &rich_log_semi_invuln_exit,
          py::arg("turn"), py::arg("species"), py::arg("move"));
    m.def("rich_log_baton_pass_transfer", &rich_log_baton_pass_transfer,
          py::arg("turn"), py::arg("side"), py::arg("species"));
    m.def("rich_log_stat_copy", &rich_log_stat_copy,
          py::arg("turn"), py::arg("side"), py::arg("copier_species"),
          py::arg("source_species"));

    // E1b consumed-event emit helpers. Tag params are taken as ints and cast to the
    // SourceTag/VolatileTag enums so the Python shim/tests use the same single source
    // of truth for the entry layout.
    m.def("rich_log_move_use", &rich_log_move_use,
          py::arg("turn"), py::arg("species"), py::arg("move"), py::arg("side"));
    m.def("rich_log_presence", &rich_log_presence,
          py::arg("turn"), py::arg("event"), py::arg("species"));
    m.def("rich_log_cant_sleep", &rich_log_cant_sleep,
          py::arg("turn"), py::arg("species"), py::arg("turns"));
    m.def("rich_log_hit_self_confusion", &rich_log_hit_self_confusion,
          py::arg("turn"), py::arg("species"), py::arg("damage"), py::arg("side"));
    m.def("rich_log_status_apply",
          [](int turn, int32_t species, int32_t status, int32_t side, int32_t source) {
              rich_log_status_apply(turn, species, status, side, static_cast<SourceTag>(source));
          }, py::arg("turn"), py::arg("species"), py::arg("status"), py::arg("side"),
             py::arg("source"));
    m.def("rich_log_stat_boost",
          [](int turn, int32_t species, int32_t stat, int32_t stages, int32_t side, int32_t source) {
              rich_log_stat_boost(turn, species, stat, stages, side, static_cast<SourceTag>(source));
          }, py::arg("turn"), py::arg("species"), py::arg("stat"), py::arg("stages"),
             py::arg("side"), py::arg("source"));
    m.def("rich_log_volatile_apply",
          [](int turn, int32_t species, int32_t vol, int32_t side, int32_t source) {
              rich_log_volatile_apply(turn, species, static_cast<VolatileTag>(vol), side,
                                      static_cast<SourceTag>(source));
          }, py::arg("turn"), py::arg("species"), py::arg("volatile_tag"), py::arg("side"),
             py::arg("source"));
    m.def("rich_log_hitcount", &rich_log_hitcount,
          py::arg("turn"), py::arg("species"), py::arg("side"));
    m.def("rich_log_damage",
          [](int turn, int32_t species, int32_t amount, int32_t hp_after, int32_t attacker_side,
             int32_t attacker_slot, int32_t defender_side, int32_t source) {
              rich_log_damage(turn, species, amount, hp_after, attacker_side, attacker_slot,
                              defender_side, static_cast<SourceTag>(source));
          }, py::arg("turn"), py::arg("species"), py::arg("amount"), py::arg("hp_after"),
             py::arg("attacker_side"), py::arg("attacker_slot"), py::arg("defender_side"),
             py::arg("source"));
    m.def("rich_log_heal",
          [](int turn, int32_t species, int32_t amount, int32_t hp_after, int32_t side, int32_t source) {
              rich_log_heal(turn, species, amount, hp_after, side, static_cast<SourceTag>(source));
          }, py::arg("turn"), py::arg("species"), py::arg("amount"), py::arg("hp_after"),
             py::arg("side"), py::arg("source"));
    m.def("rich_log_faint", &rich_log_faint,
          py::arg("turn"), py::arg("species"), py::arg("side"));
    m.def("rich_log_exp_gain", &rich_log_exp_gain,
          py::arg("turn"), py::arg("species"), py::arg("amount"));
    m.def("rich_log_level_up", &rich_log_level_up,
          py::arg("turn"), py::arg("species"), py::arg("new_level"));
}
