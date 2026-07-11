// C1.7e/C1.7h.2/Stage-4/Stage-5b unified turn driver. Mirrors src/simulator.py's single-turn slice.
// Handles pivot-move switches (u_turn/volt_switch/flip_turn), eject button, red card, eject pack,
// and phaze (roar/whirlwind/dragon_tail/circle_throw) forced switches via cpp_resolve_pending_switches.
// Singles and doubles (Stage 4): accepts a list of actions per side, each carrying source_slot.
// Plain mode (overrides==nullptr): deterministic; NeedsRNG propagates unchanged; no deep copies.
// Oracle mode (overrides!=nullptr): per-action snapshot + NeedsRNG→TurnPause catch/restore.
#include "turn.h"
#include "effects.h"            // cpp_apply_terrain_seeds / turn_start / EOT helpers, cpp_apply_entry_effects
#include "effects_internal.h"   // active_mon, side_at, is_mega_item
#include "effects_consts.h"     // AB_SUCTION_CUPS, MOLD_BREAKER_IDS
#include "residuals.h"          // cpp_apply_residuals
#include "core_leaf.h"          // cpp_build_pending_entries, cpp_select_next_action, ActionC
#include "forced_trace.h"       // ForcedAnswer, ForcedTrace (Cat-A forced consumption)
#include "event_log.h"          // rich_log_presence (CANT_FLINCH)
#include <algorithm>
#include <random>
#include <stdexcept>
#include <vector>

// Forward-declare cpp_apply_switch to avoid circular include (orchestrate.h includes turn.h).
void cpp_apply_switch(BattleState& state, int side_idx, int new_slot, int source_slot = 0,
                      ExecCtx* ctx = nullptr);

using eff_internal::active_mon;
using eff_internal::side_at;
using eff_internal::is_mega_item;
using eff_internal::apply_form_change;

// MEGA_DATA: item_id → {mega_species_id, mega_ability_id, pre_species_id}
// Mirrors src/data/mega.py MEGA_DATA + MEGA_PRE_SPECIES. Item/Species/Ability IDs are .value.
// Primal orbs (RED_ORB=40, BLUE_ORB=41) are listed first; remaining stones follow sorted by item id.
// MegaEntry struct is declared in turn.h (shared with game_driver.cpp).
static const MegaEntry MEGA_TABLE[] = {
    {40,  955, 190, 383},  // RED_ORB       → GROUDON_PRIMAL  / DESOLATE_LAND   / GROUDON
    {41,  954, 189, 382},  // BLUE_ORB      → KYOGRE_PRIMAL   / PRIMORDIAL_SEA  / KYOGRE
    {573, 947, 159, 445},  // GARCHOMPITE   → GARCHOMP_MEGA   / SAND_FORCE      / GARCHOMP
    {575, 949, 117, 460},  // ABOMASITE     → ABOMASNOW_MEGA  / SNOW_WARNING    / ABOMASNOW
    {576, 940, 156, 359},  // ABSOLITE      → ABSOL_MEGA      / MAGIC_BOUNCE    / ABSOL
    {577, 918, 181, 142},  // AERODACTYLITE → AERODACTYL_MEGA / TOUGH_CLAWS     / AERODACTYL
    {578, 933, 111, 306},  // AGGRONITE     → AGGRON_MEGA     / FILTER          / AGGRON
    {579, 912,  36,  65},  // ALAKAZITE     → ALAKAZAM_MEGA   / TRACE           / ALAKAZAM
    {580, 921, 104, 181},  // AMPHAROSITE   → AMPHAROS_MEGA   / MOLD_BREAKER    / AMPHAROS
    {582, 939, 158, 354},  // BANETTITE     → BANETTE_MEGA    / PRANKSTER       / BANETTE
    {583, 909, 178,   9},  // BLASTOISINITE → BLASTOISE_MEGA  / MEGA_LAUNCHER   / BLASTOISE
    {584, 928,   3, 257},  // BLAZIKENITE   → BLAZIKEN_MEGA   / SPEED_BOOST     / BLAZIKEN
    {585, 907, 181,   6},  // CHARIZARDITE_X→ CHARIZARD_MEGA_X/ TOUGH_CLAWS     / CHARIZARD
    {586, 908,  70,   6},  // CHARIZARDITE_Y→ CHARIZARD_MEGA_Y/ DROUGHT         / CHARIZARD
    {587, 930, 182, 282},  // GARDEVOIRITE  → GARDEVOIR_MEGA  / PIXILATE        / GARDEVOIR
    {588, 914,  23,  94},  // GENGARITE     → GENGAR_MEGA     / SHADOW_TAG      / GENGAR
    {589, 917, 104, 130},  // GYARADOSITE   → GYARADOS_MEGA   / MOLD_BREAKER    / GYARADOS
    {590, 924,  92, 214},  // HERACRONITE   → HERACROSS_MEGA  / SKILL_LINK      / HERACROSS
    {591, 925,  94, 229},  // HOUNDOOMINITE → HOUNDOOM_MEGA   / SOLAR_POWER     / HOUNDOOM
    {592, 915, 185, 115},  // KANGASKHANITE → KANGASKHAN_MEGA / PARENTAL_BOND   / KANGASKHAN
    {594, 948,  91, 448},  // LUCARIONITE   → LUCARIO_MEGA    / ADAPTABILITY    / LUCARIO
    {596, 935,  22, 310},  // MANECTITE     → MANECTRIC_MEGA  / INTIMIDATE      / MANECTRIC
    {598, 932,  37, 303},  // MAWILITE      → MAWILE_MEGA     / HUGE_POWER      / MAWILE
    {599, 934,  74, 308},  // MEDICHAMITE   → MEDICHAM_MEGA   / PURE_POWER      / MEDICHAM
    {602, 916, 184, 127},  // PINSIRITE     → PINSIR_MEGA     / AERILATE        / PINSIR
    {605, 923, 101, 212},  // SCIZORITE     → SCIZOR_MEGA     / TECHNICIAN      / SCIZOR
    {607, 926,  45, 248},  // TYRANITARITE  → TYRANITAR_MEGA  / SAND_STREAM     / TYRANITAR
    {608, 906,  47,   3},  // VENUSAURITE   → VENUSAUR_MEGA   / THICK_FAT       / VENUSAUR
    {612, 929,  33, 260},  // SWAMPERTITE   → SWAMPERT_MEGA   / SWIFT_SWIM      / SWAMPERT
    {613, 927,  31, 254},  // SCEPTILITE    → SCEPTILE_MEGA   / LIGHTNING_ROD   / SCEPTILE
    {614, 931, 156, 302},  // SABLENITE     → SABLEYE_MEGA    / MAGIC_BOUNCE    / SABLEYE
    {615, 938, 182, 334},  // ALTARIANITE   → ALTARIA_MEGA    / PIXILATE        / ALTARIA
    {616, 950,  39, 475},  // GALLADITE     → GALLADE_MEGA    / INNER_FOCUS     / GALLADE
    {617, 951, 131, 531},  // AUDINITE      → AUDINO_MEGA     / HEALER          / AUDINO
    {618, 943, 181, 376},  // METAGROSSITE  → METAGROSS_MEGA  / TOUGH_CLAWS     / METAGROSS
    {619, 936, 173, 319},  // SHARPEDONITE  → SHARPEDO_MEGA   / STRONG_JAW      / SHARPEDO
    {620, 913,  75,  80},  // SLOWBRONITE   → SLOWBRO_MEGA    / SHELL_ARMOR     / SLOWBRO
    {621, 922, 159, 208},  // STEELIXITE    → STEELIX_MEGA    / SAND_FORCE      / STEELIX
    {622, 911,  99,  18},  // PIDGEOTITE    → PIDGEOT_MEGA    / NO_GUARD        / PIDGEOT
    {623, 941, 174, 362},  // GLALITITE     → GLALIE_MEGA     / REFRIGERATE     / GLALIE
    {625, 937, 125, 323},  // CAMERUPTITE   → CAMERUPT_MEGA   / SHEER_FORCE     / CAMERUPT
    {626, 946, 113, 428},  // LOPUNNITE     → LOPUNNY_MEGA    / SCRAPPY         / LOPUNNY
    {627, 942, 184, 373},  // SALAMENCITE   → SALAMENCE_MEGA  / AERILATE        / SALAMENCE
    {628, 910,  91,  15},  // BEEDRILLITE   → BEEDRILL_MEGA   / ADAPTABILITY    / BEEDRILL
    {629, 944,  26, 380},  // LATIASITE     → LATIAS_MEGA     / LEVITATE        / LATIAS
    {630, 945,  26, 381},  // LATIOSITE     → LATIOS_MEGA     / LEVITATE        / LATIOS
};
static constexpr int MEGA_TABLE_SIZE = static_cast<int>(sizeof(MEGA_TABLE) / sizeof(MEGA_TABLE[0]));
// Primal orbs: item ids 40 (RED_ORB) and 41 (BLUE_ORB). Table entries [0] and [1].
static constexpr int32_t ITEM_RED_ORB = 40, ITEM_BLUE_ORB = 41;

const MegaEntry* cpp_find_mega_entry(int32_t item) {
    for (int i = 0; i < MEGA_TABLE_SIZE; ++i)
        if (MEGA_TABLE[i].item == item) return &MEGA_TABLE[i];
    return nullptr;
}

bool cpp_is_primal_orb(int32_t item) {
    return item == ITEM_RED_ORB || item == ITEM_BLUE_ORB;
}

// Mirror core_leaf.cpp's has_trick_room (static there; exported here for game_driver.cpp).
bool cpp_turn_has_trick_room(const BattleState& s) {
    constexpr int32_t PSEUDO_TRICK_ROOM = 1;
    for (const auto& e : s.pseudo_weather)
        if (e.effect == PSEUDO_TRICK_ROOM) return true;
    return false;
}

namespace {

constexpr int32_t FORMAT_SINGLES = 0;
constexpr int32_t V_RECHARGING = 256, V_FLINCHED = 64;
constexpr int32_t MV_METRONOME = 118, MV_SLEEP_TALK = 214, MV_ASSIST = 274;
constexpr int32_t AK_MOVE = 0;

int32_t move_id_at(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_id0; case 1: return m.move_id1;
        case 2: return m.move_id2; case 3: return m.move_id3;
        default: return 0;
    }
}

// Flatten ExecAction into the ActionC the turn-order builder consumes.
ActionC to_action_c(const ExecAction& a) {
    ActionC c;
    c.kind           = a.kind;
    c.move_slot      = a.move_slot;
    c.target_slot    = a.target_slot;
    c.switch_to_slot = a.switch_to_slot;
    c.source_slot    = a.source_slot;
    c.target_side    = a.target_side;
    return c;
}

// Rebuild EffectsLuck (the residual luck subset) from the full per-side DamageLoopLuck.
EffectsLuck effects_luck_from(const DamageLoopLuck& d) {
    EffectsLuck e;
    e.proc_threshold         = d.proc_threshold;
    e.secondary_threshold    = d.secondary_threshold;
    e.flinch_threshold       = d.flinch_threshold;
    e.binding_duration_roll  = d.binding_duration_roll;
    e.random_mode            = d.random_mode;
    e.rng                    = d.rng;
    e.overrides              = d.overrides;
    return e;
}

} // namespace

// Build bench switch candidates for a side: non-active, non-fainted team members.
// Build bench switch candidates for a side. Duplicated from orchestrate.cpp bench_switch_actions
// to avoid circular include (orchestrate.h includes turn.h).
static std::vector<ExecAction> bench_switch_candidates(BattleState& state, int si) {
    const SideState& side = side_at(state, si);
    int active_idx = side.active_indices[0];
    std::vector<ExecAction> acts;
    for (int i = 0; i < (int)side.team.size(); ++i) {
        if (i == active_idx) continue;
        if (side.team[i].fainted) continue;
        ExecAction a;
        a.kind = 1;  // AK_SWITCH
        a.switch_to_slot = i;
        acts.push_back(a);
    }
    return acts;
}

// Resolve a non-empty pending list after cpp_execute_action. Mirrors Python's
// _handle_pending_switches (simulator.py:1159): partition into roar vs player switches.
// Roar/phazing causes ("roar") are handled first via RNG oracle draw (phaze target).
// Player-selected causes (u_turn, eject_button, red_card; eject_pack is relabeled
// "eject_button" by the drain above) are resolved via Policy.
// Other causes throw "unported: pending_switch" to fail loudly.
// When policies/action_log are null, any pending switch throws.
// ctx: threaded to cpp_apply_switch for entry effects (Intimidate etc.) on the incoming mon.
// exp_participants: working sets; side-1 clear is done here (not in cpp_apply_switch) to avoid
//   _finalize_turn overwriting it.
static bool is_mold_breaker_turn(int32_t ability) {
    for (int32_t id : eff::MOLD_BREAKER_IDS) if (id == ability) return true;
    return false;
}

void cpp_resolve_pending_switches(BattleState& state,
                                  const std::vector<PendingSwitch>& pending,
                                  Policy* policies[2],
                                  nlohmann::json* action_log,
                                  std::vector<std::vector<int32_t>>& exp_participants,
                                  ExecCtx* ctx = nullptr,
                                  const OracleOverrides* overrides = nullptr,
                                  NativeRng* rng = nullptr) {
    // Validate: only known causes are allowed.
    for (const PendingSwitch& ps : pending) {
        if (ps.reason != "roar" && ps.reason != "u_turn"
                && ps.reason != "eject_button" && ps.reason != "red_card")
            throw std::runtime_error("unported: pending_switch");
    }

    // Require policies + action_log for any resolution.
    if (!policies || !action_log)
        throw std::runtime_error("unported: pending_switch");

    // --- Phaze (roar) causes: handled FIRST, matching Python's _handle_pending_switches order ---
    // Python processes the first roar switch entry; multiple roar entries in singles are impossible
    // (only one defender), so take the first "roar" entry if present.
    for (const PendingSwitch& ps : pending) {
        if (ps.reason != "roar") continue;

        int phaze_side = ps.side_idx;        // side being phazed (switches involuntarily)
        int attacker_side = 1 - phaze_side;  // side that used the phaze move

        // Suction Cups immunity: mirrors Python simulator.py:1169-1171.
        // Suction Cups (id=21) on the phazed mon blocks phazing unless attacker has Mold Breaker.
        const PokemonState& phaze_target = active_mon(state, phaze_side);
        const PokemonState& attacker_mon = active_mon(state, attacker_side);
        bool mold_breaker = is_mold_breaker_turn(attacker_mon.ability);
        if (phaze_target.ability == eff::AB_SUCTION_CUPS && !mold_breaker)
            break;  // immune: no switch, no log entry — matches Python's "pass" branch

        auto bench = bench_switch_candidates(state, phaze_side);
        if (bench.empty()) break;  // no live bench: phaze has no effect (Python skips too)

        // Phaze target resolution (ROAR_TARGET). Forced mode (rng->forced set): consume the
        // Cat-A answer via policy select_phaze (ReplayPolicy reads from the trace).
        // Oracle pause mode (overrides != null, not forced): oracle_resolve honors an injected
        // answer or throws NeedsRNG so the GameDriver pauses.
        // Plain whole-game runner (overrides == null): policy does a uniform random draw.
        int team_idx;
        if (rng && rng->forced) {
            team_idx = policies[phaze_side]->select_phaze(bench, state, phaze_side).switch_to_slot;
        } else if (overrides) {
            std::vector<int> options;
            for (const ExecAction& c : bench) options.push_back(c.switch_to_slot);
            std::sort(options.begin(), options.end());
            RngParticipants who{
                (int8_t)attacker_side, (int8_t)side_at(state, attacker_side).active_indices[0],
                (int8_t)phaze_side,    (int8_t)side_at(state, phaze_side).active_indices[0]};
            team_idx = oracle_resolve(overrides, RngEventC::ROAR_TARGET, options,
                                      who, state.turn_number);
        } else {
            team_idx = policies[phaze_side]->select_phaze(bench, state, phaze_side).switch_to_slot;
        }

        if (phaze_side == 1 && !exp_participants.empty())
            exp_participants[0].clear();
        cpp_apply_switch(state, phaze_side, team_idx, 0, ctx);

        nlohmann::json phaze_entry;
        phaze_entry["phase"] = "phaze";
        phaze_entry["side"] = phaze_side;
        phaze_entry["target"] = team_idx;
        action_log->push_back(std::move(phaze_entry));
        break;  // singles: at most one roar entry
    }

    // --- Player-forced switches (u_turn, eject_button, red_card) ---
    // Mirrors Python: sides_needing = set(s for s, _ in player_switches).
    bool needs_switch[2] = {false, false};
    for (const PendingSwitch& ps : pending) {
        if (ps.reason != "roar" && (ps.side_idx == 0 || ps.side_idx == 1))
            needs_switch[ps.side_idx] = true;
    }

    bool any_player_switch = needs_switch[0] || needs_switch[1];
    if (!any_player_switch) return;

    nlohmann::json p0_choice = nullptr;
    nlohmann::json p1_choice = nullptr;

    for (int si = 0; si < 2; ++si) {
        if (!needs_switch[si]) continue;
        auto candidates = bench_switch_candidates(state, si);
        // Mirrors Python: if no live bench, no switch is applied.
        if (candidates.empty()) continue;
        ExecAction chosen = policies[si]->select_switch(candidates, state, si, SwitchCtx::FORCED_PIVOT);
        int team_idx = chosen.switch_to_slot;
        // Clear exp_participants for side-1 switches (mirrors effects.py:519-522).
        if (si == 1 && !exp_participants.empty())
            exp_participants[0].clear();
        cpp_apply_switch(state, si, team_idx, 0, ctx);
        if (si == 0) p0_choice = team_idx;
        else         p1_choice = team_idx;
    }

    nlohmann::json entry;
    entry["phase"] = "forced_switch";
    entry["p0"] = p0_choice;
    entry["p1"] = p1_choice;
    action_log->push_back(std::move(entry));
}

void cpp_run_one_turn(BattleState& state,
                      const std::vector<ExecAction>& actions_p0,
                      const std::vector<ExecAction>& actions_p1,
                      DamageLoopLuck& luck_p0, DamageLoopLuck& luck_p1,
                      const TurnLuck& tl0, const TurnLuck& tl1,
                      bool mega_p0, bool mega_p1,
                      bool finalize_on_post_faint,
                      Policy* policies[2],
                      nlohmann::json* action_log,
                      const OracleOverrides* overrides,
                      const ActionSnapshot* resume_snap,
                      const SpeedTieOrder* forced_tie) {
    // Plain mode: no snapshots, NeedsRNG propagates unchanged.
    // Oracle mode: per-action snapshot + NeedsRNG→TurnPause catch/restore.
    const bool oracle = (overrides != nullptr);

    // Mutable per-side action lists (recharge forcing rewrites entries before the queue is built).
    std::vector<ExecAction> actions[2] = {actions_p0, actions_p1};

    std::vector<std::vector<int32_t>> exp_participants;
    std::vector<std::pair<int,int>> turn_start_active;
    std::vector<Entry> pending;

    if (resume_snap) {
        // Resume from snapshot: restore the 4 mutable pieces (state already restored by caller).
        exp_participants  = resume_snap->exp_participants;
        turn_start_active = resume_snap->turn_start_active;
        pending           = resume_snap->pending;
        // turn_order keeps the value from the restored state (partially filled by prior movers).
    } else {
        // === _begin_turn ===
        // Initialize the per-turn exp-participant sets (from state, else one empty set per opp active slot).
        if (!state.exp_participants.empty()) {
            // Copy from InlineVec<ExpParticipantSet>: each inner is the frozenset members.
            exp_participants.clear();
            for (const auto& eps : state.exp_participants) {
                exp_participants.emplace_back(eps.members.begin(), eps.members.end());
            }
        } else {
            exp_participants.assign(state.side1.active_indices.size(), {});
        }
        // turn_start_active: every active slot at turn start ((side, team_idx)).
        for (int si = 0; si < 2; ++si)
            for (int32_t ti : side_at(state, si).active_indices)
                turn_start_active.push_back({si, ti});

        // Clear ally_fainted_last_turn both sides.
        state.side0.ally_fainted_last_turn = false;
        state.side1.ally_fainted_last_turn = false;

        cpp_apply_terrain_seeds(state);

        // Turn-1 entry effects for leads still on their first turn.
        if (state.turn_number == 1) {
            for (int si = 0; si < 2; ++si) {
                PokemonState& m = active_mon(state, si);
                if (m.turns_in_battle == 0 && !m.fainted)
                    cpp_apply_entry_effects(state, si);
            }
        }

        cpp_apply_turn_start_effects(state);  // RKS/Silvally type sync + Castform Forecast (ported, Issue 2).

        // Primal reversion: Blue/Red Orb holders auto-revert at turn start (no mega flag needed).
        // Mirrors simulator.py:543-563. Order: side 0 then side 1.
        for (int si = 0; si < 2; ++si) {
            PokemonState& mon = active_mon(state, si);
            SideState& side = side_at(state, si);
            if (!cpp_is_primal_orb(mon.item)) continue;
            const MegaEntry* e = cpp_find_mega_entry(mon.item);
            if (!e) continue;
            if (mon.is_mega || side.mega_used || mon.species != e->pre_species) continue;
            apply_form_change(state, si, e->mega_species);
            active_mon(state, si).ability = e->mega_ability;
            active_mon(state, si).is_mega = true;
            side_at(state, si).mega_used = true;
            cpp_apply_entry_effects(state, si, nullptr);
        }

        // Mega evolution: collect qualifying sides flagged with mega_pX, sort by speed, then evolve.
        // Mirrors simulator.py:565-598.
        {
            const bool mega_flags[2] = {mega_p0, mega_p1};
            std::vector<int> mega_sides;
            for (int si = 0; si < 2; ++si) {
                if (!mega_flags[si]) continue;
                const PokemonState& mon = active_mon(state, si);
                const SideState& side = side_at(state, si);
                const MegaEntry* e = cpp_find_mega_entry(mon.item);
                if (!e) continue;
                if (mon.is_mega || side.mega_used || mon.species != e->pre_species) continue;
                mega_sides.push_back(si);
            }
            bool tr = cpp_turn_has_trick_room(state);
            std::stable_sort(mega_sides.begin(), mega_sides.end(),
                [&](int a, int b) {
                    int32_t sa = cpp_effective_speed(active_mon(state, a), side_at(state, a), state);
                    int32_t sb = cpp_effective_speed(active_mon(state, b), side_at(state, b), state);
                    return tr ? (sa < sb) : (sa > sb);
                });
            for (int si : mega_sides) {
                // Re-validate after previous side's entry effects (e.g. Neutralizing Gas edge cases).
                const MegaEntry* e = cpp_find_mega_entry(active_mon(state, si).item);
                if (!e) continue;
                apply_form_change(state, si, e->mega_species);
                active_mon(state, si).ability = e->mega_ability;
                active_mon(state, si).is_mega = true;
                side_at(state, si).mega_used = true;
                cpp_apply_entry_effects(state, si, nullptr);
            }
        }

        // Force recharge: for each action, if the acting mon has RECHARGING, override to move_slot -1.
        // Mirrors Python simulator.py:601-606 which iterates all actions per side.
        for (int si = 0; si < 2; ++si) {
            for (ExecAction& act : actions[si]) {
                if (act.kind == AK_MOVE) {
                    const SideState& side = side_at(state, si);
                    int32_t team_idx = side.active_indices[act.source_slot];
                    if (side.team[team_idx].volatiles & V_RECHARGING) {
                        ExecAction recharge;
                        recharge.kind = AK_MOVE;
                        recharge.move_slot = -1;
                        recharge.source_slot = act.source_slot;
                        act = recharge;
                    }
                }
            }
        }

        // Build the pending-entries list once (resolves tiebreaker/priority-item/Quick Draw once,
        // mutating state for Custap). Dynamic re-selection mirrors Python _build_queue's entry
        // construction + _select_next_action: sort key is recomputed each pick against current state.
        std::vector<ActionC> ap0, ap1;
        for (const ExecAction& a : actions[0]) ap0.push_back(to_action_c(a));
        for (const ExecAction& a : actions[1]) ap1.push_back(to_action_c(a));
        pending = cpp_build_pending_entries(state, ap0, ap1, tl0, tl1);
        state.turn_order.clear();
    }

    // === _advance_queue (dynamic per-pick selection) ===
    // ONE ExecCtx for the whole turn, mirroring Python's single per-turn TurnContext. Protect-family
    // side state (protected_sides / protect_move / wide_guard_sides / quick_guard_sides) accumulates
    // across movers — e.g. mover 1's Protect must still be visible when mover 2 attacks. Per-actor
    // fields are overwritten each iteration below.
    ExecCtx ctx;
    ctx.overrides = overrides;  // no-op in plain mode (nullptr); threaded into ExecCtx in oracle mode

    // In oracle mode: snapshot before each action (perf gate: plain mode never allocates these).
    // Declared once and filled at top of each iteration to avoid reuse-after-move.
    ActionSnapshot snap;

    // Helper to restore snap and throw TurnPause (oracle mode only).
    auto pause = [&](NeedsRNG& nr) {
        state            = snap.state;
        ctx              = snap.ctx;
        exp_participants = snap.exp_participants;
        pending          = snap.pending;
        turn_start_active = snap.turn_start_active;
        throw TurnPause{std::move(nr), std::move(snap)};
    };

    while (!pending.empty()) {
        // Take snapshot BEFORE selecting+executing the next action (oracle mode only).
        // This covers state, ctx, exp_participants, and pending (with the next entry still in it).
        if (oracle) {
            snap.state            = state;
            snap.ctx              = ctx;
            snap.exp_participants = exp_participants;
            snap.pending          = pending;
            snap.turn_start_active = turn_start_active;
            snap.mega_p0          = mega_p0;
            snap.mega_p1          = mega_p1;
            snap.lp0              = luck_p0;
            snap.lp1              = luck_p1;
        }

        Entry best;
        try {
            best = cpp_select_next_action(state, pending, overrides, forced_tie);
        } catch (NeedsRNG& nr) {
            // SPEED_TIE with no ordering override: restore snapshot and surface pause.
            if (!oracle) throw;
            pause(nr);
        }
        int side_idx = best.side_idx;
        int source_slot = best.source_slot;
        SideState& side = side_at(state, side_idx);
        int32_t active_team_idx = side.active_indices[source_slot];
        PokemonState& active = side.team[active_team_idx];

        if (active.fainted) continue;  // fainted before their turn

        if (active.volatiles & V_FLINCHED) {
            active.volatiles &= ~V_FLINCHED;
            rich_log_presence(state.turn_number, RICH_EV_CANT_FLINCH, active.species);
            continue;  // flinched mons do not act, not recorded in turn_order
        }

        state.turn_order.push_back(side_idx);

        // Retrieve this actor's action by matching source_slot. Each action carries source_slot
        // so the pending entry's source_slot always identifies exactly which action to use.
        const ExecAction* action_ptr = nullptr;
        for (const ExecAction& a : actions[side_idx])
            if (a.source_slot == source_slot) { action_ptr = &a; break; }
        if (!action_ptr) throw std::runtime_error("cpp_run_one_turn: missing action for source_slot");
        const ExecAction& action = *action_ptr;

        // opp_action: slot-0 action from the opponent (mirrors Python turn_ctx.actions[1-side]=actions[1-side][0]).
        // Guarded against empty list (should not occur in a valid turn).
        const std::vector<ExecAction>& opp_actions = actions[1 - side_idx];
        const ExecAction* opp_ptr = opp_actions.empty() ? nullptr : &opp_actions[0];

        int32_t used_move = (action.kind == AK_MOVE && action.move_slot >= 0)
                                ? move_id_at(active, action.move_slot) : -1;
        // Two-turn release of a CALLED move (Metronome -> Solar Beam): the slot still holds
        // the caller, but the mon is locked mid-charge — skip the sub-move roll; the dispatch
        // executes the stored VE_CHARGING_MOVE volatile directly (mirrors Python _advance_queue).
        if ((used_move == MV_METRONOME || used_move == MV_SLEEP_TALK)
                && active.charging_move_slot != action.move_slot) {
            DamageLoopLuck& mv_luck = (side_idx == 0) ? luck_p0 : luck_p1;

            // Plain controlled mode: fail loud BEFORE building options (no else-random branch in
            // Python _phase_await_sub_move — sub_move in controlled mode is oracle-only).
            if (!oracle && !mv_luck.random_mode)
                throw std::runtime_error("unported: sub_move");

            std::vector<int> options = (used_move == MV_METRONOME)
                ? metronome_options()
                : sleep_talk_options(active);

            if (options.empty()) {
                // No callable sub-move: fail the move (mirrors Assist no-options path).
                active.last_move_failed = true;
                continue;
            }

            int32_t chosen;
            if (mv_luck.random_mode) {
                // Forced mode: consume the Cat-A answer (mirrors Python _phase_await_sub_move pause).
                // Native mode: uniform choice over callable options (no else-random branch in Python,
                // so uniform is correct for the random_mode live path).
                if (mv_luck.rng->forced) {
                    RngEventC sub_event = (used_move == MV_METRONOME)
                        ? RngEventC::METRONOME_MOVE : RngEventC::SLEEP_TALK_MOVE;
                    const ForcedAnswer& fa = mv_luck.rng->forced->next_answer(mv_luck.rng->current_turn, sub_event, -1);
                    chosen = fa.i0;
                    bool valid = false;
                    for (int o : options) if (o == chosen) { valid = true; break; }
                    if (!valid) continue;  // out-of-options answer: sub-move fails
                } else {
                    chosen = mv_luck.rng->choice(options);
                }
            } else {
                // Only reachable in oracle mode (plain controlled throws above).
                // Sub-move selection (METRONOME_MOVE / SLEEP_TALK_MOVE) is a Category-A oracle event:
                // the answer is the chosen move id, options are the callable-move list. Mirrors
                // Python simulator.py _phase_await_sub_move (answer not in options => sub-move fails).
                RngEventC sub_event = (used_move == MV_METRONOME)
                    ? RngEventC::METRONOME_MOVE : RngEventC::SLEEP_TALK_MOVE;
                try {
                    RngParticipants who{
                        (int8_t)side_idx, (int8_t)source_slot,
                        (int8_t)(1 - side_idx),
                        (int8_t)side_at(state, 1 - side_idx).active_indices[0]};
                    chosen = oracle_resolve(overrides, sub_event, options,
                                            who, state.turn_number);
                } catch (NeedsRNG& nr) {
                    pause(nr);
                }
                bool valid = false;
                for (int o : options) if (o == chosen) { valid = true; break; }
                if (!valid) continue;  // out-of-options answer: sub-move fails, advance the queue
            }

            // Build sub_action: PP consumed from original slot (Metronome/Sleep Talk slot).
            ExecAction sub_action;
            sub_action.kind          = AK_MOVE;
            sub_action.move_slot     = action.move_slot;
            sub_action.move_override = chosen;
            sub_action.source_slot   = source_slot;

            // Sleep Talk: temporarily clear SLEEP so _pre_move_checks doesn't block the sub-move.
            bool sleep_override = (used_move == MV_SLEEP_TALK && active.status == eff::STATUS_SLEEP);
            if (sleep_override)
                active.status = eff::STATUS_NONE;

            // Track field presence (same as normal per-actor path below).
            for (auto& participant_set : exp_participants)
                for (int32_t pi : state.side0.active_indices) {
                    bool present = false;
                    for (int32_t x : participant_set) if (x == pi) { present = true; break; }
                    if (!present) participant_set.push_back(pi);
                }

            // Set per-actor ExecCtx fields (same as normal path).
            // cpp_execute_action sets ctx.attacker_slot = source_slot internally; do not double-set.
            if (opp_ptr) {
                ctx.opp_action_present       = true;
                ctx.opp_action_kind          = opp_ptr->kind;
                ctx.opp_action_move_slot     = opp_ptr->move_slot;
                ctx.opp_action_move_override = opp_ptr->move_override;
            } else {
                ctx.opp_action_present = false;
            }
            ctx.has_exp_participants = true;
            ctx.exp_participants = exp_participants;
            ctx.overrides = overrides;

            DamageLoopLuck& luck_atk_sub = (side_idx == 0) ? luck_p0 : luck_p1;
            DamageLoopLuck& luck_def_sub = (side_idx == 0) ? luck_p1 : luck_p0;

            std::vector<PendingSwitch> pending_sub;
            try {
                cpp_execute_action(state, side_idx, sub_action, luck_atk_sub, luck_def_sub,
                                   pending_sub, ctx, source_slot);
            } catch (NeedsRNG& nr) {
                if (!oracle) throw;
                pause(nr);
            }

            exp_participants = ctx.exp_participants;

            // Sleep Talk: restore SLEEP after execution if mon is still alive and status is NONE.
            if (sleep_override) {
                SideState& post_side = side_at(state, side_idx);
                PokemonState& active_post = post_side.team[post_side.active_indices[source_slot]];
                if (!active_post.fainted && active_post.status == eff::STATUS_NONE)
                    active_post.status = eff::STATUS_SLEEP;
            }

            // Drain eject_pack_sides into pending, resolve pending switches.
            for (int32_t ep : ctx.eject_pack_sides)
                pending_sub.push_back({ep, "eject_button"});
            ctx.eject_pack_sides.clear();

            if (!pending_sub.empty()) {
                try {
                    cpp_resolve_pending_switches(state, pending_sub, policies, action_log,
                                                exp_participants, &ctx, overrides,
                                                luck_p0.random_mode ? luck_p0.rng : nullptr);
                } catch (NeedsRNG& nr) {
                    if (!oracle) throw;
                    pause(nr);
                }
            }
            if (oracle && overrides) overrides->clear_transient();
            continue;
        }
        if (used_move == MV_ASSIST) {
            // Assist in singles has no partner move: the move fails (no pause).
            active.last_move_failed = true;
            continue;
        }
        // Track field presence: every player (side 0) active index joins each opponent's set.
        for (auto& participant_set : exp_participants)
            for (int32_t pi : state.side0.active_indices) {
                bool present = false;
                for (int32_t x : participant_set) if (x == pi) { present = true; break; }
                if (!present) participant_set.push_back(pi);
            }

        // Per-actor ExecCtx fields (overwritten each mover; Protect-family side state persists).
        // opp_action: slot-0 of opponent's actions, mirroring Python turn_ctx.actions[1-side]=actions[1-side][0].
        // cpp_execute_action sets ctx.attacker_slot = source_slot internally — do NOT set it here.
        if (opp_ptr) {
            ctx.opp_action_present       = true;
            ctx.opp_action_kind          = opp_ptr->kind;
            ctx.opp_action_move_slot     = opp_ptr->move_slot;
            ctx.opp_action_move_override = opp_ptr->move_override;
        } else {
            ctx.opp_action_present = false;
        }
        ctx.has_exp_participants = true;
        ctx.exp_participants = exp_participants;
        ctx.overrides = overrides;

        DamageLoopLuck& luck_atk = (side_idx == 0) ? luck_p0 : luck_p1;
        DamageLoopLuck& luck_def = (side_idx == 0) ? luck_p1 : luck_p0;

        std::vector<PendingSwitch> pending_switches;
        try {
            cpp_execute_action(state, side_idx, action, luck_atk, luck_def, pending_switches, ctx, source_slot);
        } catch (NeedsRNG& nr) {
            // Restore to the pre-action snapshot and surface the pause to the driver.
            if (!oracle) throw;
            pause(nr);
        }

        // Carry the (possibly mutated) exp-participant sets forward.
        exp_participants = ctx.exp_participants;

        // Drain eject_pack_sides into pending_switches (mirrors Python _advance_queue lines 779-781):
        // for ep_side in ctx.eject_pack_sides: pending.append((ep_side, "eject_button"))
        // Cause "eject_button" matches Python's labeling of both eject_button AND eject_pack triggers.
        for (int32_t ep : ctx.eject_pack_sides)
            pending_switches.push_back({ep, "eject_button"});
        ctx.eject_pack_sides.clear();

        if (!pending_switches.empty()) {
            try {
                cpp_resolve_pending_switches(state, pending_switches, policies, action_log,
                                            exp_participants, &ctx, overrides,
                                            luck_p0.random_mode ? luck_p0.rng : nullptr);
            } catch (NeedsRNG& nr) {
                if (!oracle) throw;
                pause(nr);
            }
        }
        if (oracle && overrides) overrides->clear_transient();
    }

    // === _finish_turn ===
    ResidualLuck rluck;
    rluck.side0 = effects_luck_from(luck_p0);
    rluck.side1 = effects_luck_from(luck_p1);

    ResidualCtx rctx;
    rctx.ctx_present = true;
    rctx.turn_start_active_null = false;
    rctx.turn_start_active = turn_start_active;
    rctx.has_exp_participants = !exp_participants.empty();
    rctx.exp_participants = exp_participants;
    rctx.has_oracle = true;
    rctx.random_mode = luck_p0.random_mode || luck_p1.random_mode;
    // Use p0's rng if p0 is in random_mode, otherwise p1's. Both sides share one NativeRng per game.
    rctx.rng = luck_p0.random_mode ? luck_p0.rng : luck_p1.rng;

    std::vector<PendingSwitch> residual_switches;

    // Residual Category-A oracle events (e.g. MOODY_STATS) throw NeedsRNG mid-residuals. Snapshot
    // the pre-residual state with an EMPTY pending list so resume re-enters, skips the (already-
    // completed) mover loop, and deterministically re-runs residuals with the override set.
    // In plain mode NeedsRNG propagates out unchanged (how run_game surfaces "NeedsRNG: oracle
    // event unresolved" to the gates today).
    if (oracle) {
        ActionSnapshot rsnap;
        rsnap.state             = state;
        rsnap.ctx               = ctx;
        rsnap.exp_participants   = exp_participants;
        rsnap.pending           = {};  // empty => resume skips the mover loop, lands at _finish_turn
        rsnap.turn_start_active = turn_start_active;
        rsnap.mega_p0           = mega_p0;
        rsnap.mega_p1           = mega_p1;
        rsnap.lp0               = luck_p0;
        rsnap.lp1               = luck_p1;
        try {
            cpp_apply_residuals(state, rluck, rctx, residual_switches);
        } catch (NeedsRNG& nr) {
            state            = rsnap.state;
            ctx              = rsnap.ctx;
            exp_participants = rsnap.exp_participants;
            turn_start_active = rsnap.turn_start_active;
            throw TurnPause{std::move(nr), std::move(rsnap)};
        }
        overrides->clear_transient();
    } else {
        cpp_apply_residuals(state, rluck, rctx, residual_switches);
    }

    // Replay distribute_exp's post-award clear (exp.py:156) for opponent slots that fainted.
    // cpp_apply_residuals consumed a CONST copy of the participant sets (rctx.exp_participants),
    // so any KO-driven clear inside the residual phase never reached the driver's `exp_participants`.
    // Clearing fainted opponent slots here keeps the committed sets in parity (action-phase clears
    // are already threaded back through ctx, so re-clearing those empty slots is a no-op).
    //
    // Doubles guard: when active_indices has duplicate entries (two slots pointing to the same
    // team_idx — e.g. [0,0] after a voluntary switch to an already-active mon), only the FIRST
    // occurrence is cleared. The second slot's exp_participants belong to that slot's accumulated
    // history and must survive to be distributed in a future turn (mirroring Python's _finalize_turn
    // which commits exp_participants as-is, without any faint-based clearing).
    {
        std::vector<bool> ti_seen(state.side1.team.size(), false);
        for (size_t i = 0; i < state.side1.active_indices.size() && i < exp_participants.size(); ++i) {
            int32_t ti = state.side1.active_indices[i];
            if (ti < 0 || ti >= (int32_t)state.side1.team.size()) continue;
            if (!state.side1.team[ti].fainted) continue;
            if (ti_seen[ti]) continue;  // duplicate slot: skip to match Python's no-clear behaviour
            ti_seen[ti] = true;
            exp_participants[i].clear();
        }
    }

    cpp_apply_eot_form_changes(state);
    cpp_apply_eot_volatile_clear(state);
    cpp_apply_eot_weather_terrain(state);

    // ACCEPTED unported boundary (NOT a Category-A oracle gap). Residual-triggered forced
    // switches (Emergency Exit / Wimp Out) are deliberately left unported: Python's _finish_turn
    // re-runs on resume and double-applies every residual for the turn (a known bug we are
    // intentionally freezing, not replicating). EMERGENCY_EXIT/WIMP_OUT are pruned from all
    // parity corpora. See RECORDS/INTENTIONAL_DIVERGENCES.md #2.
    if (!residual_switches.empty())
        throw std::runtime_error("unported: residual_switch");


    // === _check_fainted ===
    // Detect whether any active has fainted with a live bench available (replacement needed).
    bool replacement_needed = false;
    for (int si = 0; si < 2; ++si) {
        const SideState& side = side_at(state, si);
        bool has_bench = false;
        for (size_t i = 0; i < side.team.size(); ++i) {
            bool is_active = false;
            for (int32_t ai : side.active_indices) if (ai == (int32_t)i) { is_active = true; break; }
            if (!is_active && !side.team[i].fainted) { has_bench = true; break; }
        }
        if (!has_bench) continue;
        for (int32_t ai : side.active_indices)
            if (side.team[ai].fainted) { replacement_needed = true; break; }
        if (replacement_needed) break;
    }
    if (replacement_needed && !finalize_on_post_faint)
        throw std::runtime_error("unported: post_faint_switch");
    // When finalize_on_post_faint=true: fall through to _finalize_turn with fainted actives in place.

    // === _finalize_turn ===
    state.prev_turn_order = state.turn_order;
    state.turn_number += 1;
    // Commit exp-participant sets sorted + deduped (Python frozensets; serializer expects sorted ints).
    for (auto& participants : exp_participants) {
        std::sort(participants.begin(), participants.end());
        participants.erase(std::unique(participants.begin(), participants.end()), participants.end());
    }
    // Write back to InlineVec<ExpParticipantSet, N>.
    state.exp_participants.clear();
    for (const auto& participants : exp_participants) {
        ExpParticipantSet eps;
        for (int32_t v : participants) eps.members.push_back(v);
        state.exp_participants.push_back(eps);
    }
}
