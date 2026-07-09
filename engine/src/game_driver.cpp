// Resumable oracle-aware game driver (Stage 0+1).
// cpp_run_one_turn (turn.cpp) is the unified loop: oracle mode selected by overrides!=nullptr.
// GameDriver owns the full turn loop (mirrors cpp_run_game) plus pause/resume state.
#include "game_driver.h"
#include "turn.h"
#include "orchestrate.h"       // cpp_battle_over, cpp_compute_winner, cpp_enumerate_legal_actions,
                               // cpp_build_faint_queue, cpp_drain_faint_queue, cpp_make_policy,
                               // cpp_action_to_json, cpp_apply_switch, cpp_action_from_json
#include "forced_trace.h"
#include "replay_policy.h"
#include "effects.h"
#include "effects_internal.h"
#include "effects_consts.h"
#include "residuals.h"
#include "core_leaf.h"
#include "move_exec.h"
#include "move_exec_guards.h"
#include "codec.h"
#include "policy.h"
#include "ai_policy.h"
#include "logger.h"            // reset_catb_occurrence_counters_if_registered
#include <nlohmann/json.hpp>
#include <algorithm>
#include <stdexcept>

using eff_internal::active_mon;
using eff_internal::side_at;

namespace {
constexpr int32_t AK_SWITCH = 1;
} // anonymous namespace

// ---------------------------------------------------------------------------
// GameDriver
// ---------------------------------------------------------------------------

GameDriver::GameDriver(const std::string& args_json) {
    auto j = nlohmann::json::parse(args_json);
    state_ = battle_state_from_json(j["state"].dump());
    seed_  = j.value("seed", uint64_t(0));

    lp0_tmpl_ = damage_luck_from_json(j["luck_p0"]);
    lp1_tmpl_ = damage_luck_from_json(j["luck_p1"]);
    tl0_ = turn_luck_from_json(j["turn_luck_p0"]);
    tl1_ = turn_luck_from_json(j["turn_luck_p1"]);
    max_turns_ = j.value("max_turns", 200);
    policy_p0_ = j.value("policy_p0", std::string("random"));
    policy_p1_ = j.value("policy_p1", std::string("random"));

    // Decode overrides if present. Each override key accepts either a SCALAR (single
    // answer queued once) or an ARRAY (N answers, consumed in order — consume-once
    // semantics: the resolver pops one per occurrence and throws NeedsRNG when the
    // queue is empty). Mirrors Python `_rng_inject` reference behavior.
    auto push_scalar_or_array = [](std::vector<OracleAnswer>& queue,
                                   const nlohmann::json& node) {
        if (node.is_array()) {
            for (const auto& v : node) {
                OracleAnswer a; a.i0 = v.get<int>(); queue.push_back(a);
            }
        } else {
            OracleAnswer a; a.i0 = node.get<int>(); queue.push_back(a);
        }
    };
    if (j.contains("overrides") && !j["overrides"].is_null()) {
        const auto& ov = j["overrides"];
        if (ov.contains("effect_spore_which") && !ov["effect_spore_which"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::EFFECT_SPORE_WHICH)],
                ov["effect_spore_which"]);
        }
        if (ov.contains("tri_attack_status") && !ov["tri_attack_status"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::TRI_ATTACK_STATUS)],
                ov["tri_attack_status"]);
        }
        if (ov.contains("acupressure_stat") && !ov["acupressure_stat"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::ACUPRESSURE_STAT)],
                ov["acupressure_stat"]);
        }
        if (ov.contains("starf_berry_stat") && !ov["starf_berry_stat"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::STARF_BERRY_STAT)],
                ov["starf_berry_stat"]);
        }
        if (ov.contains("roar_target") && !ov["roar_target"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::ROAR_TARGET)],
                ov["roar_target"]);
        }
        // Sub-move selection: the answer is the chosen move id (i0).
        if (ov.contains("metronome_move") && !ov["metronome_move"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::METRONOME_MOVE)],
                ov["metronome_move"]);
        }
        if (ov.contains("sleep_talk_move") && !ov["sleep_talk_move"].is_null()) {
            push_scalar_or_array(
                overrides_.answers[static_cast<int>(RngEventC::SLEEP_TALK_MOVE)],
                ov["sleep_talk_move"]);
        }
        // MOODY_STATS: two picks [boost_idx, drop_idx]. boost=i0, drop=i1 (mirrors residuals.py).
        // Accepts either a single pair [boost, drop] or an array of pairs [[b,d],[b,d],...].
        if (ov.contains("moody_stats") && !ov["moody_stats"].is_null()) {
            auto& moody_queue =
                overrides_.answers[static_cast<int>(RngEventC::MOODY_STATS)];
            const auto& node = ov["moody_stats"];
            const bool is_pair_of_pairs =
                node.is_array() && !node.empty() && node[0].is_array();
            if (is_pair_of_pairs) {
                for (const auto& pr : node) {
                    OracleAnswer a;
                    a.i0 = pr[0].get<int>();
                    a.i1 = pr[1].get<int>();
                    moody_queue.push_back(a);
                }
            } else {
                OracleAnswer a;
                a.i0 = node[0].get<int>();
                a.i1 = node[1].get<int>();
                moody_queue.push_back(a);
            }
        }
        // SPEED_TIE: a doubles-compatible ordering of (side,slot) pairs, earliest acts first.
        // Accepts either a single ordering or an array of orderings (consume-once).
        if (ov.contains("speed_tie") && !ov["speed_tie"].is_null()) {
            const auto& node = ov["speed_tie"];
            const bool is_array_of_orders =
                node.is_array() && !node.empty() && node[0].is_array()
                && !node[0].empty() && node[0][0].is_array();
            if (is_array_of_orders) {
                for (const auto& order : node) {
                    SpeedTieOrder sto;
                    for (const auto& pr : order)
                        sto.order.push_back({pr[0].get<int>(), pr[1].get<int>()});
                    overrides_.speed_tie_queue.push_back(std::move(sto));
                }
            } else {
                SpeedTieOrder sto;
                for (const auto& pr : node)
                    sto.order.push_back({pr[0].get<int>(), pr[1].get<int>()});
                overrides_.speed_tie_queue.push_back(std::move(sto));
            }
        }
    }

    // Shared RNG
    if (lp0_tmpl_.random_mode || lp1_tmpl_.random_mode || tl0_.random_mode || tl1_.random_mode) {
        game_rng_ = std::make_unique<NativeRng>(seed_ ^ 0xDEADBEEFCAFEBABEULL);
        if (lp0_tmpl_.random_mode) lp0_tmpl_.rng = game_rng_.get();
        if (lp1_tmpl_.random_mode) lp1_tmpl_.rng = game_rng_.get();
        if (tl0_.random_mode) tl0_.rng = game_rng_.get();
        if (tl1_.random_mode) tl1_.rng = game_rng_.get();
    }

    // Thread overrides pointer into luck templates. overrides_ is stable (owned by driver, not
    // moved after construction); per-turn copies copy the pointer and see any injected answers.
    lp0_tmpl_.overrides = &overrides_;
    lp1_tmpl_.overrides = &overrides_;

    // Parse optional forced_trace payload.
    if (j.contains("forced_trace") && !j["forced_trace"].is_null()) {
        // Forced mode requires ALL FOUR luck structs to be in random_mode.
        if (!lp0_tmpl_.random_mode || !lp1_tmpl_.random_mode ||
            !tl0_.random_mode || !tl1_.random_mode)
            throw std::runtime_error(
                "forced_trace requires random_mode luck (all four luck structs must have random_mode=true)");

        forced_ = std::make_unique<ForcedTrace>(forced_trace_from_json(j["forced_trace"]));
        game_rng_->forced = forced_.get();

        // Replace both policies with ReplayPolicies that consume from the trace.
        replay_p0_ = std::make_unique<ReplayPolicy>(forced_.get(), game_rng_.get(), 0);
        replay_p1_ = std::make_unique<ReplayPolicy>(forced_.get(), game_rng_.get(), 1);
        policies_[0] = replay_p0_.get();
        policies_[1] = replay_p1_.get();
    } else {
        p0_ = cpp_make_policy(policy_p0_, seed_);
        p1_ = cpp_make_policy(policy_p1_, seed_ ^ 0x9E3779B97F4A7C15ULL);
        policies_[0] = p0_.get();
        policies_[1] = p1_.get();
    }

    action_log_ = nlohmann::json::array();

    // Initial faint drain
    {
        auto fq = cpp_build_faint_queue(state_);
        if (!fq.empty()) cpp_drain_faint_queue(state_, fq, policies_, action_log_);
    }
}

std::string GameDriver::step() {
    if (done_) {
        return _make_done_result();
    }
    if (paused_) {
        throw std::runtime_error("GameDriver: in paused state; call step(answer_json) to resume");
    }
    return _run();
}

std::string GameDriver::step(const std::string& answer_json) {
    if (!paused_) {
        throw std::runtime_error("GameDriver: not paused; call step() without an answer");
    }
    auto ans_j = nlohmann::json::parse(answer_json);
    RngEventC ev = pending_pause_->needs.event;

    if (ev == RngEventC::SPEED_TIE) {
        // SPEED_TIE's answer is a full slot ordering {"order":[[side,slot],...]}.
        // Push into transient_ties; the replay cursor will consume it from the start.
        if (!ans_j.contains("order"))
            throw std::runtime_error("GameDriver: SPEED_TIE resume requires an 'order' field");
        SpeedTieOrder sto;
        for (const auto& pr : ans_j["order"])
            sto.order.push_back({pr[0].get<int>(), pr[1].get<int>()});
        overrides_.transient_ties.push_back(std::move(sto));
    } else {
        // Single discrete answer {"i0":..,"i1":..} pushed into the transient queue for this event.
        OracleAnswer ans;
        ans.i0 = ans_j.value("i0", -1);
        ans.i1 = ans_j.value("i1", -1);
        overrides_.transient[static_cast<int>(ev)].push_back(ans);
    }

    // Reset all transient cursors so the replay re-consumes answers from the start.
    overrides_.reset_transient_cursors();

    // Restore to pre-action snapshot and continue.
    ActionSnapshot snap = pending_pause_->snapshot;
    state_ = snap.state;
    DamageLoopLuck lp0 = snap.lp0;
    DamageLoopLuck lp1 = snap.lp1;

    paused_ = false;
    pending_pause_.reset();

    // Resume from the snapshot: pass snap so _advance_queue starts from the saved pending list
    // (which includes the entry for the action that paused), skipping _begin_turn entirely.
    // This prevents re-executing movers that already ran before the pause.
    try {
        // mega flags false: resume skips _begin_turn entirely, so mega evolution (a
        // _begin_turn step) was already applied and is baked into the snapshot state.
        cpp_run_one_turn(state_, cur_actions0_, cur_actions1_,
                         lp0, lp1, tl0_, tl1_, false, false, true,
                         policies_, &action_log_, &overrides_, &snap);
    } catch (TurnPause& tp) {
        paused_ = true;
        pending_pause_ = std::move(tp);
        return _make_pending_result();
    } catch (const std::runtime_error& e) {
        done_ = true;
        nlohmann::json out;
        out["status"] = std::string(e.what());
        out["state"]  = nlohmann::json::parse(battle_state_to_json(state_));
        out["winner"] = nullptr;
        out["action_log"] = action_log_;
        return out.dump();
    }

    ++turn_count_;
    if (game_rng_) game_rng_->current_turn = turn_count_;
    {
        auto fq = cpp_build_faint_queue(state_);
        if (!fq.empty()) cpp_drain_faint_queue(state_, fq, policies_, action_log_);
    }

    if (cpp_battle_over(state_) || turn_count_ >= max_turns_) {
        done_ = true;
        return _make_done_result();
    }

    return _run();
}

std::string GameDriver::_run() {
    while (!cpp_battle_over(state_) && turn_count_ < max_turns_) {
        // Per-turn occurrence-counter reset: solver injections key on (event, occurrence)
        // where occurrence is the k-th draw of that event within the turn. The driver is
        // the single-writer for turn boundaries, so it owns the reset — any harness that
        // forgets to reset otherwise gets silent index drift. No-op when no counters
        // are registered (null-fast-path).
        reset_catb_occurrence_counters_if_registered();
        std::vector<ExecAction> actions0, actions1;

        if (forced_) {
            // Forced mode: set current_turn then consume ACTION_SELECT from trace.
            game_rng_->current_turn = turn_count_ + 1;
            try {
                const ForcedAnswer& fa = forced_->next_answer(
                    turn_count_ + 1, RngEventC::ACTION_SELECT, -1);
                if (fa.actions_p0.is_null() || fa.actions_p1.is_null())
                    throw std::runtime_error(
                        "forced_trace_mismatch: one-sided ACTION_SELECT unsupported");
                for (int i = 0; i < (int)fa.actions_p0.size(); ++i) {
                    ExecAction a = cpp_action_from_json(fa.actions_p0[i]);
                    a.source_slot = i;
                    actions0.push_back(a);
                }
                for (int i = 0; i < (int)fa.actions_p1.size(); ++i) {
                    ExecAction a = cpp_action_from_json(fa.actions_p1[i]);
                    a.source_slot = i;
                    actions1.push_back(a);
                }
            } catch (const std::runtime_error& e) {
                done_ = true;
                nlohmann::json out;
                out["status"]     = std::string(e.what());
                out["state"]      = nlohmann::json::parse(battle_state_to_json(state_));
                out["winner"]     = nullptr;
                out["action_log"] = action_log_;
                return out.dump();
            }
        } else {
            // Normal mode: ask policies (same logic as cpp_run_game).
            for (int side = 0; side < 2; ++side) {
                const SideState& sside = (side == 0) ? state_.side0 : state_.side1;
                int num_slots = static_cast<int>(sside.active_indices.size());
                std::vector<ExecAction>& vec = (side == 0) ? actions0 : actions1;
                std::vector<int> claimed_switch_slots;
                for (int slot = 0; slot < num_slots; ++slot) {
                    int active_team_idx = sside.active_indices[slot];
                    if (sside.team[active_team_idx].fainted) continue;
                    auto legal = cpp_enumerate_legal_actions(state_, side, slot);
                    if (slot > 0 && !claimed_switch_slots.empty()) {
                        std::vector<ExecAction> filtered;
                        for (const ExecAction& act : legal) {
                            if (act.kind == AK_SWITCH) {
                                bool conflict = false;
                                for (int taken : claimed_switch_slots)
                                    if (act.switch_to_slot == taken) { conflict = true; break; }
                                if (conflict) continue;
                            }
                            filtered.push_back(act);
                        }
                        legal = std::move(filtered);
                    }
                    ExecAction chosen = policies_[side]->select(legal, state_, side);
                    chosen.source_slot = slot;
                    if (chosen.kind == AK_SWITCH)
                        claimed_switch_slots.push_back(chosen.switch_to_slot);
                    vec.push_back(chosen);
                }
            }
        }

        // Log actions
        nlohmann::json actions_entry;
        actions_entry["phase"] = "actions";
        nlohmann::json p0_arr = nlohmann::json::array();
        for (const ExecAction& a : actions0) p0_arr.push_back(cpp_action_to_json(a));
        nlohmann::json p1_arr = nlohmann::json::array();
        for (const ExecAction& a : actions1) p1_arr.push_back(cpp_action_to_json(a));
        actions_entry["p0"] = std::move(p0_arr);
        actions_entry["p1"] = std::move(p1_arr);
        action_log_.push_back(std::move(actions_entry));

        // Store for potential resume (the resume path needs to replay with same actions).
        cur_actions0_ = actions0;
        cur_actions1_ = actions1;

        DamageLoopLuck lp0 = lp0_tmpl_;
        DamageLoopLuck lp1 = lp1_tmpl_;

        // Fold per-action mega flags into the per-side run_one_turn scalars (mirrors Python
        // Simulator.step reading Action.mega). Forced traces carry mega on the recorded
        // actions; policy mode never emits mega (enumeration omits it), so this stays false.
        bool mega0 = false, mega1 = false;
        for (const ExecAction& a : actions0) mega0 = mega0 || a.mega;
        for (const ExecAction& a : actions1) mega1 = mega1 || a.mega;

        try {
            cpp_run_one_turn(state_, actions0, actions1, lp0, lp1, tl0_, tl1_,
                             mega0, mega1, true, policies_, &action_log_, &overrides_);
        } catch (TurnPause& tp) {
            if (forced_) {
                // In forced mode, any oracle pause is a desync.
                done_ = true;
                nlohmann::json out;
                out["status"] = "forced_trace_mismatch: unexpected oracle pause event="
                                + std::to_string(static_cast<int>(tp.needs.event));
                out["state"]      = nlohmann::json::parse(battle_state_to_json(state_));
                out["winner"]     = nullptr;
                out["action_log"] = action_log_;
                return out.dump();
            }
            paused_ = true;
            pending_pause_ = std::move(tp);
            return _make_pending_result();
        } catch (const std::runtime_error& e) {
            done_ = true;
            nlohmann::json out;
            out["status"] = std::string(e.what());
            out["state"]  = nlohmann::json::parse(battle_state_to_json(state_));
            out["winner"] = nullptr;
            out["action_log"] = action_log_;
            return out.dump();
        }

        ++turn_count_;
        // Update current_turn to the completed turn number so post-faint switches
        // use the correct turn when consuming from the trace.
        if (game_rng_) game_rng_->current_turn = turn_count_;

        {
            auto fq = cpp_build_faint_queue(state_);
            if (!fq.empty()) cpp_drain_faint_queue(state_, fq, policies_, action_log_);
        }
    }

    done_ = true;

    // In forced mode, verify all trace entries were consumed.
    if (forced_) {
        try {
            forced_->verify_exhausted();
        } catch (const std::runtime_error& e) {
            nlohmann::json out;
            out["status"]     = std::string(e.what());
            out["state"]      = nlohmann::json::parse(battle_state_to_json(state_));
            out["winner"]     = nullptr;
            out["action_log"] = action_log_;
            return out.dump();
        }
    }

    return _make_done_result();
}

std::string GameDriver::_make_pending_result() const {
    nlohmann::json out;
    out["status"]  = "pending";
    out["event"]   = static_cast<int>(pending_pause_->needs.event);
    out["options"] = pending_pause_->needs.options;
    out["state"]   = nlohmann::json::parse(battle_state_to_json(pending_pause_->snapshot.state));
    return out.dump();
}

std::string GameDriver::_make_done_result() const {
    nlohmann::json out;
    out["status"] = cpp_battle_over(state_) ? "done" : "max_turns";
    if (cpp_battle_over(state_)) {
        auto w = cpp_compute_winner(state_);
        out["winner"] = w.has_value() ? nlohmann::json(*w) : nlohmann::json(nullptr);
    } else {
        out["winner"] = nullptr;
    }
    out["state"]      = nlohmann::json::parse(battle_state_to_json(state_));
    out["action_log"] = action_log_;
    return out.dump();
}
