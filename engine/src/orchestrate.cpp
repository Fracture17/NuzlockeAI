// C1.7h Stage 1+2+3+5: orchestration primitives, legal-action enumeration, and game loop.
// cpp_apply_switch mirrors the post-faint path of Python _apply_switch (effects.py:514).
// cpp_enumerate_legal_actions mirrors Python enumerate_legal_actions (actions.py:44) exactly;
// mega variants are omitted (deferred boundary).
// cpp_run_game mirrors Python Simulator clean-path state machine for singles and doubles.
// Stage 5: per-slot action selection (one policy call per active slot per side); action_log
// emits p0/p1 as JSON arrays (always, even singles 1-element); fainted active slots are skipped;
// joint switch legality enforced (slot 1 cannot claim same bench slot as slot 0).
// Baton Pass transfer IS ported: cpp_apply_switch applies stored baton_pass_data (stat_stages,
// allowlisted volatiles, timed_volatiles, crit_stage, sub_hp) to the incoming mon, mirroring
// Python _apply_switch (effects.py:533). The throws in that block are malformed-JSON guards only.
#include "orchestrate.h"
#include "effects.h"
#include "effects_internal.h"
#include "effects_consts.h"
#include "move_exec_guards.h"    // ExecCtx (for cpp_apply_switch ctx param)
#include "turn.h"
#include "policy.h"
#include "ai_policy.h"
#include "codec.h"               // battle_state_to_json for debug_ai_decisions

#include <algorithm>
#include <stdexcept>
#include <string>

using eff_internal::side_at;
using eff_internal::has_type;
using eff_internal::has_pseudo;
using eff_internal::has_timed_volatile;
using eff_internal::is_grounded;

// ---------------------------------------------------------------------------
// Local constants (mirrors of Python enums/consts used only in enumeration).
// ---------------------------------------------------------------------------

// Volatile flag bits (Volatile IntFlag in python)
constexpr int32_t EV_RECHARGING    = 256;
constexpr int32_t EV_LOCKED_MOVE   = 512;
constexpr int32_t EV_ENCORE_ACTIVE = 8;
constexpr int32_t EV_CHOICE_LOCKED = 262144;
constexpr int32_t EV_TAUNT_ACTIVE  = 16;

// VolatileEffect ids for timed trapping conditions
constexpr int32_t VE_BOUND_ENUM   = 4;   // VolatileEffect.BOUND
constexpr int32_t VE_TRAPPED_ENUM = 22;  // VolatileEffect.TRAPPED

// Pseudo-weather
constexpr int32_t PW_GRAVITY_ENUM = 2;   // PseudoWeather.GRAVITY

// Ability ids
constexpr int32_t AB_SHADOW_TAG   = 23;
constexpr int32_t AB_MAGNET_PULL  = 42;
constexpr int32_t AB_ARENA_TRAP   = 71;

// Mold Breaker family (same set as MOLD_BREAKER_ABILITIES in move_exec.cpp)
static bool is_mold_breaker_enum(int32_t a) {
    return a == 104 /*MOLD_BREAKER*/ || a == 163 /*TURBOBLAZE*/ || a == 164 /*TERAVOLT*/;
}

// Type ids
constexpr int32_t TYPE_GHOST = 13;
constexpr int32_t TYPE_STEEL = 16;

// Item ids
constexpr int32_t ITM_SHED_SHELL   = 295;
constexpr int32_t ITM_ASSAULT_VEST = 640;

// MoveCategory (value 2 = STATUS, matches generated MoveData.category)
constexpr int8_t CAT_STATUS_ENUM = 2;

// Move.STRUGGLE int value and sentinel slot (mirrors Python STRUGGLE_SLOT = -2)
constexpr int32_t MV_STRUGGLE_ID   = 165;
constexpr int32_t STRUGGLE_SLOT_ID = -2;

// Gravity-blocked move ids (same array as move_exec.cpp GRAVITY_BLOCKED_MOVES)
static const int32_t GRAVITY_BLOCKED[] = {19, 26, 136, 150, 340, 393, 477, 507};
static bool is_gravity_blocked_enum(int32_t m) {
    for (int32_t g : GRAVITY_BLOCKED) if (g == m) return true;
    return false;
}

// ActionKind values
constexpr int32_t AK_MOVE   = 0;
constexpr int32_t AK_SWITCH = 1;

// ---------------------------------------------------------------------------
// Local helpers
// ---------------------------------------------------------------------------

static const SideState& const_side_at(const BattleState& s, int idx) {
    return idx == 0 ? s.side0 : s.side1;
}

static int32_t move_id_at_slot(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_id0; case 1: return m.move_id1;
        case 2: return m.move_id2; case 3: return m.move_id3;
        default: return 0;
    }
}

static int32_t move_pp_at_slot(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_pp0; case 1: return m.move_pp1;
        case 2: return m.move_pp2; case 3: return m.move_pp3;
        default: return 0;
    }
}

// Look up MoveData.category for a move id. Returns -1 if not found.
// Reuses the generated MOVE_TABLE from move_data.h (included via effects_consts.h chain).
#include "move_data.h"
static int8_t move_category(int32_t move_id) {
    int lo = 0, hi = 813;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid;
    }
    if (lo < 813 && MOVE_TABLE[lo].move_id == move_id) return MOVE_TABLE[lo].category;
    return -1;
}

static ExecAction make_move_action(int32_t move_slot, int32_t move_override = -1) {
    ExecAction a;
    a.kind = AK_MOVE;
    a.move_slot = move_slot;
    a.move_override = move_override;
    return a;
}

static ExecAction make_switch_action(int32_t switch_to_slot) {
    ExecAction a;
    a.kind = AK_SWITCH;
    a.switch_to_slot = switch_to_slot;
    return a;
}

static ExecAction struggle_action() {
    return make_move_action(STRUGGLE_SLOT_ID, MV_STRUGGLE_ID);
}

// ---------------------------------------------------------------------------
// Local helper: temporarily swap active_indices[0] with active_indices[pos] so
// entry functions that read active_indices[0] see the entering mon.
// Mirrors the file-local with_active_slot_swapped in move_exec.cpp.
// ---------------------------------------------------------------------------
template <typename F>
static void slot_swapped(BattleState& state, int side_idx, int pos, F&& f) {
    SideState& side = side_at(state, side_idx);
    if (pos == 0 || pos >= (int)side.active_indices.size()) { f(); return; }
    std::swap(side.active_indices[0], side.active_indices[pos]);
    try { f(); } catch (...) {
        std::swap(side.active_indices[0], side.active_indices[pos]);
        throw;
    }
    std::swap(side.active_indices[0], side.active_indices[pos]);
}

// ---------------------------------------------------------------------------
// cpp_apply_switch
// ---------------------------------------------------------------------------
void cpp_apply_switch(BattleState& state, int side_idx, int new_slot, int source_slot, ExecCtx* ctx) {
    SideState& side = side_at(state, side_idx);

    // Initialize exp_participants if not yet committed (new battle or test state).
    // Mirrors Python's Simulator.start() faint path: creates one empty set per side-1 active slot.
    // In the real game loop cpp_run_one_turn always commits this; initialization here handles
    // test states and the very first post-faint switch of a battle.
    if (state.exp_participants.empty()) {
        // One empty ExpParticipantSet per side-1 active slot.
        for (std::size_t i = 0; i < state.side1.active_indices.size(); ++i)
            state.exp_participants.push_back(ExpParticipantSet{});
    }

    // Reset exp_participants for this slot when opponent (side 1) switches in.
    // For the between-turns post-faint path there is no ExecCtx, so we clear the
    // committed state field directly (mirrors what ctx.exp_participants[slot] = set()
    // followed by _finalize_turn commit would produce).
    if (side_idx == 1 && source_slot < (int)state.exp_participants.size())
        state.exp_participants[source_slot].members.clear();

    int old_active_idx = side.active_indices[source_slot];
    cpp_apply_switch_out_reset(state, side_idx, old_active_idx);

    side.active_indices[source_slot] = new_slot;
    PokemonState& new_poke = side.team[new_slot];

    // Baton Pass: transfer stored state (stat_stages, volatiles, timed_volatiles, crit_stage,
    // sub_hp) BEFORE the turns_in_battle reset, mirroring Python's _apply_switch order.
    // baton_pass_data is the typed struct populated by _apply_baton_pass_capture.
    if (side.has_baton_pass_data) {
        const BatonPassData& bp = side.baton_pass_data;
        new_poke.stage0 = bp.stage0;
        new_poke.stage1 = bp.stage1;
        new_poke.stage2 = bp.stage2;
        new_poke.stage3 = bp.stage3;
        new_poke.stage4 = bp.stage4;
        new_poke.stage5 = bp.stage5;
        new_poke.stage6 = bp.stage6;

        // Volatile bitmask: OR into existing volatiles
        new_poke.volatiles |= bp.volatiles_bitmask;

        // Timed volatiles: append transferred entries
        for (const auto& tv : bp.timed_volatiles) new_poke.timed_volatiles.push_back(tv);

        new_poke.crit_stage = bp.crit_stage;
        new_poke.sub_hp     = bp.sub_hp;

        side.has_baton_pass_data = false;
        side.baton_pass_data = BatonPassData{};
    }

    new_poke.turns_in_battle = 0;
    new_poke.toxic_turns = 0;
    new_poke.sleep_turns = 0;

    // Slot-swap: entry functions read active_indices[0] as the entering mon.
    slot_swapped(state, side_idx, source_slot, [&]() {
        cpp_apply_entry_hazards(state, side_idx);
        int entering_ai = side_at(state, side_idx).active_indices[0];
        if (!side_at(state, side_idx).team[entering_ai].fainted)
            cpp_apply_entry_effects(state, side_idx, ctx);
    });
}

// ---------------------------------------------------------------------------
// cpp_battle_over
// ---------------------------------------------------------------------------
bool cpp_battle_over(const BattleState& state) {
    for (int si = 0; si < 2; ++si) {
        const SideState& side = (si == 0) ? state.side0 : state.side1;
        bool all_fainted = true;
        for (const PokemonState& p : side.team) {
            if (!p.fainted) { all_fainted = false; break; }
        }
        if (all_fainted) return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// cpp_compute_winner
// ---------------------------------------------------------------------------
std::optional<int> cpp_compute_winner(const BattleState& state) {
    auto all_fainted = [](const SideState& side) {
        for (const PokemonState& p : side.team)
            if (!p.fainted) return false;
        return true;
    };
    bool side0_dead = all_fainted(state.side0);
    bool side1_dead = all_fainted(state.side1);
    if (side0_dead && side1_dead) return std::nullopt;
    if (side0_dead)               return 1;
    if (side1_dead)               return 0;
    return std::nullopt;
}

// ---------------------------------------------------------------------------
// cpp_enumerate_legal_actions
// Mirrors Python enumerate_legal_actions (actions.py:44) branch-for-branch.
// Branch order: RECHARGING → charging → LOCKED_MOVE → ENCORE → CHOICE_LOCKED
//   → main (per-move filters + switches + Struggle fallback).
// Mega variants are intentionally omitted (deferred).
// ---------------------------------------------------------------------------
std::vector<ExecAction> cpp_enumerate_legal_actions(const BattleState& state,
                                                     int side_idx, int slot) {
    const SideState& side = const_side_at(state, side_idx);
    int active_idx = side.active_indices[slot];
    const PokemonState& pokemon = side.team[active_idx];

    // Branch 1: RECHARGING — must skip the next turn
    if (pokemon.volatiles & EV_RECHARGING)
        return { make_move_action(-1) };

    // Branch 2: mid two-turn move (Fly/Dig/Bounce/Solar Beam etc.) — attack turn forced
    if (pokemon.charging_move_slot >= 0)
        return { make_move_action(pokemon.charging_move_slot) };

    // Branch 3: LOCKED_MOVE (Outrage/Thrash/Petal Dance rampage)
    if (pokemon.volatiles & EV_LOCKED_MOVE)
        return { make_move_action(pokemon.locked_slot) };

    // Branch 4: ENCORE_ACTIVE — repeat the encored slot
    if (pokemon.volatiles & EV_ENCORE_ACTIVE)
        return { make_move_action(pokemon.locked_slot) };

    // Branch 5: CHOICE_LOCKED — locked slot if PP > 0 else Struggle, plus all legal switches
    if (pokemon.volatiles & EV_CHOICE_LOCKED) {
        std::vector<ExecAction> locked_move_actions;
        if (move_pp_at_slot(pokemon, pokemon.locked_slot) > 0)
            locked_move_actions.push_back(make_move_action(pokemon.locked_slot));

        std::vector<ExecAction> switch_actions;
        for (int i = 0; i < (int)side.team.size(); ++i) {
            if (i == active_idx) continue;
            if (side.team[i].fainted) continue;
            switch_actions.push_back(make_switch_action(i));
        }

        if (locked_move_actions.empty())
            locked_move_actions.push_back(struggle_action());

        std::vector<ExecAction> result;
        result.insert(result.end(), locked_move_actions.begin(), locked_move_actions.end());
        result.insert(result.end(), switch_actions.begin(), switch_actions.end());
        return result;
    }

    // Branch 6: main path
    bool gravity_active = has_pseudo(state, PW_GRAVITY_ENUM);

    std::vector<ExecAction> actions;
    for (int move_slot = 0; move_slot < 4; ++move_slot) {
        int32_t pp   = move_pp_at_slot(pokemon, move_slot);
        int32_t move = move_id_at_slot(pokemon, move_slot);
        if (pp <= 0) continue;
        if (gravity_active && is_gravity_blocked_enum(move)) continue;
        int8_t cat = move_category(move);
        if ((pokemon.volatiles & EV_TAUNT_ACTIVE) && cat == CAT_STATUS_ENUM) continue;
        if (pokemon.item == ITM_ASSAULT_VEST && cat == CAT_STATUS_ENUM) continue;
        actions.push_back(make_move_action(move_slot));
    }

    // Switch eligibility: check timed-volatile trapping and ability trapping.
    bool bound   = has_timed_volatile(pokemon, VE_BOUND_ENUM);
    bool trapped = has_timed_volatile(pokemon, VE_TRAPPED_ENUM);

    const SideState& opp_side = const_side_at(state, 1 - side_idx);
    bool mold_breaker_active = is_mold_breaker_enum(pokemon.ability);
    bool shed_shell          = (pokemon.item == ITM_SHED_SHELL);
    bool is_steel            = has_type(pokemon, TYPE_STEEL);
    bool is_ghost            = has_type(pokemon, TYPE_GHOST);

    // Collect active non-fainted opponents
    bool shadow_tag_trapped   = false;
    bool magnet_pull_trapped  = false;
    bool arena_trap_trapped   = false;
    for (int i : opp_side.active_indices) {
        if (opp_side.team[i].fainted) continue;
        int32_t opp_ability = opp_side.team[i].ability;

        // Shadow Tag: traps non-Ghost unless user also has Shadow Tag, Shed Shell, or Mold Breaker
        if (opp_ability == AB_SHADOW_TAG && !is_ghost && !shed_shell
                && pokemon.ability != AB_SHADOW_TAG && !mold_breaker_active)
            shadow_tag_trapped = true;

        // Magnet Pull: traps Steel-types
        if (opp_ability == AB_MAGNET_PULL && is_steel && !shed_shell && !mold_breaker_active)
            magnet_pull_trapped = true;

        // Arena Trap: traps grounded non-Ghost
        if (opp_ability == AB_ARENA_TRAP && !is_ghost && !shed_shell && !mold_breaker_active
                && is_grounded(pokemon, state))
            arena_trap_trapped = true;
    }

    bool ability_trapped = shadow_tag_trapped || magnet_pull_trapped || arena_trap_trapped;
    // Shed Shell bypasses BOUND but not TRAPPED or ability trapping
    bool can_switch = (!trapped && !ability_trapped) && (!bound || shed_shell);

    if (can_switch) {
        for (int i = 0; i < (int)side.team.size(); ++i) {
            if (i == active_idx) continue;
            if (side.team[i].fainted) continue;
            actions.push_back(make_switch_action(i));
        }
    }

    // Mega block intentionally omitted (deferred boundary).

    // If no MOVE action exists, force Struggle (appended after switches, same as Python)
    bool has_move = false;
    for (const ExecAction& a : actions)
        if (a.kind == AK_MOVE) { has_move = true; break; }
    if (!has_move)
        actions.push_back(struggle_action());

    return actions;
}

// ---------------------------------------------------------------------------
// cpp_run_game helpers
// ---------------------------------------------------------------------------

// Serialize an ExecAction to JSON dict (mirrors the action_log format for Stage 5 replay).
nlohmann::json cpp_action_to_json(const ExecAction& a) {
    nlohmann::json j;
    j["kind"]           = a.kind;
    j["move_slot"]      = a.move_slot;
    j["move_override"]  = a.move_override;
    j["switch_to_slot"] = a.switch_to_slot;
    j["target_side"]    = a.target_side;
    j["target_slot"]    = a.target_slot;
    j["source_slot"]    = a.source_slot;
    return j;
}

// Deserialize an ExecAction from a JSON dict (reverse of cpp_action_to_json).
ExecAction cpp_action_from_json(const nlohmann::json& aj) {
    ExecAction a;
    a.kind           = aj.value("kind", 0);
    a.move_slot      = aj.value("move_slot", -1);
    a.move_override  = aj.value("move_override", -1);
    a.switch_to_slot = aj.value("switch_to_slot", -1);
    a.target_side    = aj.value("target_side", -1);
    a.target_slot    = aj.value("target_slot", 0);
    a.source_slot    = aj.value("source_slot", 0);
    a.mega           = aj.value("mega", false);
    return a;
}

// Build the faint queue as Python _check_fainted did (simulator.py:815):
// for each side si in 0,1: if any bench mon alive → for each active slot whose active fainted
// → append (si, slot_pos). Also called by cpp_drain_faint_queue to rebuild after replacements.
std::vector<std::pair<int,int>> cpp_build_faint_queue(const BattleState& state) {
    std::vector<std::pair<int,int>> queue;
    for (int si = 0; si < 2; ++si) {
        const SideState& side = (si == 0) ? state.side0 : state.side1;
        // Check bench availability: any team member not active and not fainted.
        bool bench_available = false;
        for (int i = 0; i < (int)side.team.size(); ++i) {
            bool is_active = false;
            for (int ai : side.active_indices) if (ai == i) { is_active = true; break; }
            if (!is_active && !side.team[i].fainted) { bench_available = true; break; }
        }
        if (!bench_available) continue;
        for (int slot_pos = 0; slot_pos < (int)side.active_indices.size(); ++slot_pos) {
            int team_idx = side.active_indices[slot_pos];
            if (side.team[team_idx].fainted)
                queue.push_back({si, slot_pos});
        }
    }
    return queue;
}

// Mirror Python _current_faint_round (simulator.py:912): first pending (si, slot_pos) per side.
static std::vector<std::pair<int,int>> current_faint_round(
        const std::vector<std::pair<int,int>>& queue) {
    std::vector<std::pair<int,int>> round;
    bool seen[2] = {false, false};
    for (const auto& [si, sp] : queue) {
        if (!seen[si]) {
            round.push_back({si, sp});
            seen[si] = true;
        }
    }
    return round;
}

// Build the bench switch candidates for a side/slot_pos: non-active, non-fainted team indices.
static std::vector<ExecAction> bench_switch_actions(const BattleState& state, int si, int slot_pos) {
    const SideState& side = (si == 0) ? state.side0 : state.side1;
    int active_idx = side.active_indices[slot_pos];
    std::vector<ExecAction> acts;
    for (int i = 0; i < (int)side.team.size(); ++i) {
        if (i == active_idx) continue;
        if (side.team[i].fainted) continue;
        // Also skip if already active in another slot (doubles safety; singles has only 1 slot)
        bool other_active = false;
        for (int ai : side.active_indices) if (ai == i && ai != active_idx) { other_active = true; break; }
        if (other_active) continue;
        ExecAction a;
        a.kind = AK_SWITCH;
        a.switch_to_slot = i;
        acts.push_back(a);
    }
    return acts;
}

// EE/Wimp Out ability constants for entry-hazard crossing check.
static constexpr int32_t EE_ABILITY_EE   = 194;  // EMERGENCY_EXIT
static constexpr int32_t EE_ABILITY_WO   = 193;  // WIMP_OUT

// After a mon is switched in, check if it crossed 50% HP via entry hazards (Site 3).
// hp_before_hazards: HP of the incoming mon captured BEFORE cpp_apply_switch was called.
// The crossing check is strict: hp_before > half AND hp_after <= half AND alive AND bench exists.
// When the crossing holds, resolves one FORCED_PIVOT and writes the result into *next_hp_before
// (pre-hazard HP of the newly-active mon) so the caller can loop.
// Returns the new team_idx of the replacement (>=0) or -1 if no crossing / no bench.
// NeedsRNG propagates out in plain mode; oracle mode throws NeedsRNG via oracle_resolve.
int cpp_entry_ee_step(BattleState& state, int si, int active_team_idx,
                              int32_t hp_before_hazards,
                              Policy* policies[2],
                              std::vector<std::vector<int32_t>>& exp_participants,
                              const OracleOverrides* overrides,
                              NativeRng* rng, ExecCtx* ctx,
                              nlohmann::json* action_log,
                              int32_t* next_hp_before_out) {
    const SideState& side = side_at(state, si);
    int ai = side.active_indices[0];
    const PokemonState& mon = side.team[ai];
    if (mon.ability != EE_ABILITY_EE && mon.ability != EE_ABILITY_WO) return -1;
    if (mon.fainted || mon.hp <= 0) return -1;
    int32_t half = mon.max_hp / 2;
    if (!(hp_before_hazards > half && half >= mon.hp)) return -1;
    // Live bench check.
    bool bench = false;
    for (int i = 0; i < (int)side.team.size(); ++i) {
        bool is_active = false;
        for (int32_t a : side.active_indices) if (a == i) { is_active = true; break; }
        if (!is_active && !side.team[i].fainted) { bench = true; break; }
    }
    if (!bench) return -1;
    // Get the bench candidates and capture the replacement's pre-hazard HP before switching.
    auto candidates = bench_switch_actions(state, si, 0);
    if (candidates.empty()) return -1;
    // Determine which mon will be switched in (need HP before hazards).
    // We must select the mon first, then capture its HP, then call cpp_apply_switch.
    // oracle_resolve may throw NeedsRNG here (oracle mode) — that's correct behavior.
    int new_team_idx;
    if (rng && rng->forced) {
        new_team_idx = policies[si]->select_switch(candidates, state, si,
                                                    SwitchCtx::FORCED_PIVOT).switch_to_slot;
    } else if (overrides) {
        std::vector<int> options;
        for (const ExecAction& c : candidates) options.push_back(c.switch_to_slot);
        std::sort(options.begin(), options.end());
        RngParticipants who{(int8_t)si, (int8_t)ai, -1, -1};
        new_team_idx = oracle_resolve(overrides, RngEventC::FORCED_SWITCH, options,
                                      who, state.turn_number);
    } else {
        new_team_idx = policies[si]->select_switch(candidates, state, si,
                                                    SwitchCtx::FORCED_PIVOT).switch_to_slot;
    }
    // Capture pre-hazard HP of the incoming replacement BEFORE the switch applies hazards.
    if (next_hp_before_out)
        *next_hp_before_out = side_at(state, si).team[new_team_idx].hp;
    // Apply exp clear for side-1 (mirrors effects.py:519-522).
    if (si == 1 && !exp_participants.empty()) exp_participants[0].clear();
    cpp_apply_switch(state, si, new_team_idx, 0, ctx);
    if (action_log) {
        nlohmann::json entry;
        entry["phase"] = "forced_switch";
        entry["p0"] = (si == 0) ? nlohmann::json(new_team_idx) : nlohmann::json(nullptr);
        entry["p1"] = (si == 1) ? nlohmann::json(new_team_idx) : nlohmann::json(nullptr);
        action_log->push_back(std::move(entry));
    }
    return new_team_idx;
}

// Drain the faint queue via policies; appends post_faint entries to action_log.
// After the queue empties, REBUILDS it (cpp_build_faint_queue) and keeps draining:
// a replacement that dies to entry hazards during the drain is re-prompted, matching
// the real game (record faint_queue_no_rebuild_bug — the retired Python engine's
// single-pass drain gave the opponent a free turn against an empty slot).
// Terminates: every hazard death permanently shrinks the side's alive pool, and the
// rebuild only enqueues fainted actives whose side still has a live bench.
void cpp_drain_faint_queue(BattleState& state,
                            std::vector<std::pair<int,int>>& faint_queue,
                            Policy* policies[2],
                            nlohmann::json& action_log,
                            const OracleOverrides* overrides,
                            NativeRng* rng) {
    // exp_participants placeholder (not tracked in post-faint drain path).
    std::vector<std::vector<int32_t>> exp_dummy;

    while (!faint_queue.empty()) {
        auto round = current_faint_round(faint_queue);

        // Collect the chosen team index for each side (null = side not in this round).
        nlohmann::json p0_choice = nullptr;
        nlohmann::json p1_choice = nullptr;

        for (const auto& [si, slot_pos] : round) {
            auto candidates = bench_switch_actions(state, si, slot_pos);
            // If no candidates exist (all bench fainted), skip — nothing to send in.
            if (candidates.empty()) {
                if (si == 0) p0_choice = nullptr;
                else         p1_choice = nullptr;
                continue;
            }
            ExecAction chosen = policies[si]->select_switch(candidates, state, si, SwitchCtx::POST_FAINT);
            int team_idx = chosen.switch_to_slot;
            // Capture HP before entry hazards apply (inside cpp_apply_switch).
            int32_t hp_before = side_at(state, si).team[team_idx].hp;
            cpp_apply_switch(state, si, team_idx, slot_pos);
            // EE/Wimp Out entry-hazard loop: re-prompt if each new active crosses 50% on entry.
            int32_t next_hp_before = 0;
            while (cpp_entry_ee_step(state, si, team_idx, hp_before, policies, exp_dummy,
                                      overrides, rng, nullptr, &action_log, &next_hp_before) >= 0) {
                team_idx   = side_at(state, si).active_indices[0];
                hp_before  = next_hp_before;
            }
            if (si == 0) p0_choice = side_at(state, si).active_indices[slot_pos];
            else         p1_choice = side_at(state, si).active_indices[slot_pos];
        }

        nlohmann::json entry;
        entry["phase"] = "post_faint";
        entry["p0"] = p0_choice;
        entry["p1"] = p1_choice;
        action_log.push_back(std::move(entry));

        // Remove drained pairs (mirror Python: remove each (si, slot_pos) in round).
        for (const auto& pair : round) {
            auto it = std::find(faint_queue.begin(), faint_queue.end(), pair);
            if (it != faint_queue.end()) faint_queue.erase(it);
        }

        // Rebuild: if a replacement died on entry (hazards), re-prompt while a live
        // bench remains. Only refill once the current queue is exhausted so the
        // original round-by-round order is preserved.
        if (faint_queue.empty())
            faint_queue = cpp_build_faint_queue(state);
    }
}

// ---------------------------------------------------------------------------
// cpp_run_game
// ---------------------------------------------------------------------------

// Wraps another policy and appends a record to ai_decisions for every select/select_switch call.
// select_phaze is NOT recorded (game-mechanic random, not an agent decision).
struct RecordingPolicy : Policy {
    RecordingPolicy(Policy* inner, int side_idx, nlohmann::json& records)
        : inner_(inner), side_(side_idx), records_(records) {}

    ExecAction select(const std::vector<ExecAction>& legal,
                      const BattleState& state, int side_idx) override {
        nlohmann::json state_snap = nlohmann::json::parse(battle_state_to_json(state));
        ExecAction chosen = inner_->select(legal, state, side_idx);
        nlohmann::json rec;
        rec["ctx"]    = "normal";
        rec["side"]   = side_;
        rec["state"]  = std::move(state_snap);
        rec["action"] = cpp_action_to_json(chosen);
        records_.push_back(std::move(rec));
        return chosen;
    }

    ExecAction select_switch(const std::vector<ExecAction>& candidates,
                             const BattleState& state, int side_idx, SwitchCtx ctx) override {
        nlohmann::json state_snap = nlohmann::json::parse(battle_state_to_json(state));
        ExecAction chosen = inner_->select_switch(candidates, state, side_idx, ctx);
        nlohmann::json rec;
        rec["ctx"]    = (ctx == SwitchCtx::POST_FAINT) ? "post_faint" : "forced_pivot";
        rec["side"]   = side_;
        rec["state"]  = std::move(state_snap);
        rec["action"] = cpp_action_to_json(chosen);
        records_.push_back(std::move(rec));
        return chosen;
    }

    ExecAction select_phaze(const std::vector<ExecAction>& bench,
                            const BattleState& state, int side_idx) override {
        // Not recorded — phaze is a game-mechanic oracle, not an agent decision.
        return inner_->select_phaze(bench, state, side_idx);
    }

private:
    Policy* inner_;
    int side_;
    nlohmann::json& records_;
};

// Construct a Policy by name. Throws loudly on unknown kind.
std::unique_ptr<Policy> cpp_make_policy(const std::string& kind, uint64_t seed) {
    if (kind == "random") return std::make_unique<RandomPolicy>(seed);
    if (kind == "ai")     return std::make_unique<AIPolicy>(seed);
    throw std::runtime_error("make_policy: unknown policy kind '" + kind
                             + "' (expected 'random' or 'ai')");
}

GameResult cpp_run_game(BattleState state, uint64_t seed,
                        const DamageLoopLuck& luck_p0_tmpl, const DamageLoopLuck& luck_p1_tmpl,
                        const TurnLuck& tl0, const TurnLuck& tl1, int max_turns,
                        bool debug_snapshots,
                        const std::string& policy_p0, const std::string& policy_p1,
                        bool debug_ai_decisions) {
    GameResult result;
    result.turn_count = 0;
    result.action_log = nlohmann::json::array();
    result.ai_decisions = nlohmann::json::array();

    // Deterministic policy seeding: two independent streams from one seed.
    // Same seeds as before for "random"/"random" — preserves exact backward compat.
    std::unique_ptr<Policy> p0 = cpp_make_policy(policy_p0, seed);
    std::unique_ptr<Policy> p1 = cpp_make_policy(policy_p1, seed ^ 0x9E3779B97F4A7C15ULL);

    // Optionally wrap AI-side policies with recorders for the structural gate.
    std::unique_ptr<RecordingPolicy> rec0, rec1;
    if (debug_ai_decisions) {
        if (policy_p0 == "ai") {
            rec0 = std::make_unique<RecordingPolicy>(p0.get(), 0, result.ai_decisions);
        }
        if (policy_p1 == "ai") {
            rec1 = std::make_unique<RecordingPolicy>(p1.get(), 1, result.ai_decisions);
        }
    }

    Policy* policies[2] = {
        rec0 ? static_cast<Policy*>(rec0.get()) : p0.get(),
        rec1 ? static_cast<Policy*>(rec1.get()) : p1.get()
    };

    // Initial faint drain (mirrors Simulator::start — if any active fainted and bench alive,
    // drain before first AWAIT_ACTIONS).
    {
        auto fq = cpp_build_faint_queue(state);
        if (!fq.empty())
            cpp_drain_faint_queue(state, fq, policies, result.action_log);
    }

    while (!cpp_battle_over(state) && result.turn_count < max_turns) {
        // For each side, collect one action per active slot and build the per-side action vectors.
        // Singles: one slot (identical to previous behaviour).
        // Doubles: two slots; slot 1's switch choices are filtered to prevent both slots switching
        // to the same bench mon (joint legality). Filtering can never empty the list because
        // non-switch move actions always remain in the legal set.
        std::vector<ExecAction> actions0, actions1;
        for (int side = 0; side < 2; ++side) {
            const SideState& sside = (side == 0) ? state.side0 : state.side1;
            int num_slots = static_cast<int>(sside.active_indices.size());
            std::vector<ExecAction>& vec = (side == 0) ? actions0 : actions1;
            vec.reserve(num_slots);

            // Track switch_to_slot choices made by earlier slots on this side.
            std::vector<int> claimed_switch_slots;
            for (int slot = 0; slot < num_slots; ++slot) {
                // Skip fainted active slots — they cannot act and are excluded from the queue.
                int active_team_idx = sside.active_indices[slot];
                if (sside.team[active_team_idx].fainted) continue;
                auto legal = cpp_enumerate_legal_actions(state, side, slot);
                if (slot > 0 && !claimed_switch_slots.empty()) {
                    // Remove switch candidates conflicting with an earlier slot's chosen bench mon.
                    std::vector<ExecAction> filtered;
                    filtered.reserve(legal.size());
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
                ExecAction chosen = policies[side]->select(legal, state, side);
                chosen.source_slot = slot;
                if (chosen.kind == AK_SWITCH)
                    claimed_switch_slots.push_back(chosen.switch_to_slot);
                vec.push_back(chosen);
            }
        }

        // Log chosen actions as per-slot arrays (always array, even singles).
        nlohmann::json actions_entry;
        actions_entry["phase"] = "actions";
        nlohmann::json p0_arr = nlohmann::json::array();
        for (const ExecAction& a : actions0) p0_arr.push_back(cpp_action_to_json(a));
        nlohmann::json p1_arr = nlohmann::json::array();
        for (const ExecAction& a : actions1) p1_arr.push_back(cpp_action_to_json(a));
        actions_entry["p0"] = std::move(p0_arr);
        actions_entry["p1"] = std::move(p1_arr);
        result.action_log.push_back(std::move(actions_entry));

        // Fresh luck copies per turn — templates are immutable.
        DamageLoopLuck lp0 = luck_p0_tmpl;
        DamageLoopLuck lp1 = luck_p1_tmpl;

        try {
            // finalize_on_post_faint=true: post-faint turns return normally with exp_participants
            // committed and fainted actives left in place; drain_faint_queue handles replacements.
            // Pass policies and action_log so mid-turn forced switches (pivot moves) are resolved.
            cpp_run_one_turn(state, actions0, actions1, lp0, lp1, tl0, tl1, false, false, true,
                             policies, &result.action_log);
        } catch (const std::runtime_error& e) {
            std::string msg = e.what();
            if (msg.rfind("unported:", 0) == 0) {
                // Genuine unported boundary (doubles/mega/sub_move/etc.): report and abort.
                result.status = msg;
                result.final_state = state;
                result.winner = std::nullopt;
                return result;
            }
            throw;  // re-throw unexpected errors
        }

        ++result.turn_count;

        // Post-faint drain: cpp_build_faint_queue finds any fainted actives with live bench available.
        // Runs on every turn (normal or post-faint) since residuals can also cause faints.
        {
            auto fq = cpp_build_faint_queue(state);
            if (!fq.empty())
                cpp_drain_faint_queue(state, fq, policies, result.action_log);
        }

        if (debug_snapshots)
            result.turn_states.push_back(state);  // post-turn, post-drain snapshot
    }

    result.final_state = state;
    result.status = cpp_battle_over(state) ? "completed" : "max_turns";
    result.winner = cpp_battle_over(state) ? cpp_compute_winner(state) : std::nullopt;
    return result;
}
