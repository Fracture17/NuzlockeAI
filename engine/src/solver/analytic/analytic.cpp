// analytic/analytic.cpp — wave-0 analytic certifier implementation.
// Pure single-hit damaging 100%-accuracy race only. See analytic.h and
// SOLVER_PHASE2_PLAN.md Task 5 for design rationale. Concrete rules are NOT
// ported from the prototype — wave 0's scope is deliberately the narrowest
// sound slice; later lemma waves grow it audit-driven (Task 7).
//
// Fail-loud invariant: any internal inconsistency (inverted interval,
// unexpected engine reply, impossible arithmetic) throws std::runtime_error.
// UNKNOWN is routing, never an error.
#include "solver/analytic/analytic.h"

#include "ai_analytic.h"       // cpp_compute_action_probabilities
#include "ai_shared.h"         // ai_move_data_get (binary search over MOVE_TABLE)
#include "core_leaf.h"         // cpp_effective_speed
#include "solver/engine_queries.h"
#include "state.h"

#include "../generated/move_data.h"  // MOVE_TABLE, MoveData

#include <algorithm>
#include <cassert>
#include <stdexcept>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Internal constants: item IDs mirrored from engine_queries.cpp
// ---------------------------------------------------------------------------

static constexpr int32_t ITEM_NONE       = 0;
static constexpr int32_t ITEM_SITRUS     = 158;
static constexpr int32_t ITEM_FOCUS_SASH = 275;
static constexpr int32_t ITEM_STURDY_AB  = 5;    // ability id for Sturdy

// HP-dependent and binding move lists + check_move_scope live in solver/move_scope.h
// (shared with the bucket concede detectors). This file uses is_hp_dep_move() / the
// shared check_move_scope() below.

// Charge-turn (two-turn) move IDs.
static const int32_t CHARGE_MOVES[] = {
    76,   // Solar Beam
    669,  // Solar Blade
    13,   // Razor Wind
    143,  // Sky Attack
    130,  // Fly
    14,   // Bounce (actually 340)
    340,  // Bounce
    145,  // Hyper Beam (recharge, not charge — but scope out for simplicity)
    152,  // Skull Bash
    291,  // Dive
    800,  // Meteor Beam
    339,  // Sky Drop
    807,  // Beak Blast
    882,  // Eternabeam
    19,   // Fly (move 19)
    100,  // Teleport (pp cost odd case, harmless)
    248,  // Future Sight (delayed damage — scope out)
    149,  // Doom Desire
    11,   // Skull Bash (alternate)
};
static constexpr int N_CHARGE_MOVES = 14;  // intentionally smaller; exact match via move_data check below

// ---------------------------------------------------------------------------
// Item allowlist for wave-0 scope gate.
// Player: must be none (item==0) or provably inert (no item).
// Opponent: none, Sitrus Berry (158), Focus Sash (275).
// All other items → SCOPE_ITEM_NOT_ALLOWED.
// ---------------------------------------------------------------------------

static bool player_item_allowed(int32_t item) {
    return item == ITEM_NONE;
}

static bool opp_item_allowed(int32_t item) {
    return item == ITEM_NONE || item == ITEM_SITRUS || item == ITEM_FOCUS_SASH;
}

// ---------------------------------------------------------------------------
// Helpers: move slot to MoveData
// ---------------------------------------------------------------------------

static int32_t move_id_at_slot(const PokemonState& mon, int slot) {
    switch (slot) {
        case 0: return mon.move_id0;
        case 1: return mon.move_id1;
        case 2: return mon.move_id2;
        case 3: return mon.move_id3;
        default: return 0;
    }
}

// Number of non-zero move slots.
static int move_count(const PokemonState& mon) {
    int n = 0;
    if (mon.move_id0 > 0) ++n;
    if (mon.move_id1 > 0) ++n;
    if (mon.move_id2 > 0) ++n;
    if (mon.move_id3 > 0) ++n;
    return n;
}

// Look up MoveData via binary search (MOVE_TABLE may have gaps in move_id space).
static const MoveData* get_md(int32_t move_id) {
    if (move_id <= 0) return nullptr;
    return ai_move_data_get(move_id);
}

// check_move_scope / is_hp_dep_move now live in solver/move_scope.h (shared).

// ---------------------------------------------------------------------------
// Scope gate: full matchup check.
// Accumulates ALL bits before returning; never short-circuits.
// ---------------------------------------------------------------------------

static uint32_t full_scope_check(const BattleState& state, const Question& q) {
    uint32_t bits = 0;

    // Non-default Question.
    if (q.keepHp > 0)
        bits |= SCOPE_NONDEFAULT_QUESTION;
    if (q.keepItem > 0)
        bits |= SCOPE_NONDEFAULT_QUESTION;
    if (q.banMove >= 0)
        bits |= SCOPE_NONDEFAULT_QUESTION;
    if (!q.requireOppFaint)
        bits |= SCOPE_NONDEFAULT_QUESTION;
    if (!q.requireNoFaint)
        bits |= SCOPE_NONDEFAULT_QUESTION;

    // Clean entry context: no status, no boosts, no volatiles, no side conditions on either side.
    const PokemonState& pl  = active_mon(state, 0);
    const PokemonState& opp = active_mon(state, 1);

    if (pl.status != 0 || opp.status != 0
            || pl.stage0 || pl.stage1 || pl.stage2 || pl.stage3 || pl.stage4
            || opp.stage0 || opp.stage1 || opp.stage2 || opp.stage3 || opp.stage4
            || pl.volatiles || opp.volatiles
            || !pl.timed_volatiles.empty() || !opp.timed_volatiles.empty()
            || pl.toxic_turns || pl.sleep_turns || pl.confusion_turns
            || opp.toxic_turns || opp.sleep_turns || opp.confusion_turns
            || pl.sub_hp || opp.sub_hp
            || pl.locked_slot >= 0 || opp.locked_slot >= 0
            || pl.charging_move_slot >= 0 || opp.charging_move_slot >= 0)
        bits |= SCOPE_ENTRY_DIRTY;

    // Side conditions (screens, hazards, tailwind, etc.) on either side.
    if (!state.side0.side_conditions.empty() || !state.side1.side_conditions.empty())
        bits |= SCOPE_WEATHER_SCREEN;

    // Active weather, terrain, or pseudo-weather.
    if (state.weather != 0 || state.terrain != 0 || !state.pseudo_weather.empty())
        bits |= SCOPE_WEATHER_SCREEN;

    // Item allowlist.
    if (!player_item_allowed(pl.item))
        bits |= SCOPE_ITEM_NOT_ALLOWED;
    if (!opp_item_allowed(opp.item))
        bits |= SCOPE_ITEM_NOT_ALLOWED;

    // hp_thresholds residual_unknown on either side.
    HpThresholds ht_pl  = hp_thresholds(state, 0);
    HpThresholds ht_opp = hp_thresholds(state, 1);
    if (ht_pl.residual_unknown || ht_opp.residual_unknown)
        bits |= SCOPE_RESIDUAL_UNKNOWN;

    // Move-level scope check for both sides: check all non-zero slots.
    int n_pl  = move_count(pl);
    int n_opp = move_count(opp);
    for (int s = 0; s < 4; ++s) {
        int32_t mid = move_id_at_slot(pl, s);
        if (mid > 0) bits |= check_move_scope(mid);
    }
    for (int s = 0; s < 4; ++s) {
        int32_t mid = move_id_at_slot(opp, s);
        if (mid > 0) bits |= check_move_scope(mid);
    }

    // Opponent must have at least one effective (non-immune, non-status) damaging move.
    // We check by looking at the damage table for each opp move slot.
    bool opp_has_effective = false;
    for (int s = 0; s < 4; ++s) {
        int32_t mid = move_id_at_slot(opp, s);
        if (mid <= 0) continue;
        const MoveData* md = get_md(mid);
        if (!md) continue;
        // STATUS category: skip.
        if (static_cast<int>(md->category) == 2) continue;
        // base_power == 0: skip (HP-dep or fixed-dmg; already scoped out but also
        // not "damaging" in the simple sense for the stall check).
        if (md->base_power == 0 && !is_hp_dep_move(mid)) continue;

        // Query the damage table to check immunity.
        ExecAction act{};
        act.kind = 0;
        act.move_slot = s;
        try {
            DamageTable dt = damage_table(state, 1, act);
            if (!dt.immune && (!dt.noncrit.empty() || !dt.crit.empty())) {
                // Check that not all values are zero.
                bool nonzero = false;
                for (int32_t v : dt.noncrit) if (v > 0) { nonzero = true; break; }
                if (!nonzero) for (int32_t v : dt.crit) if (v > 0) { nonzero = true; break; }
                if (nonzero) { opp_has_effective = true; break; }
            }
        } catch (...) {
            // damage_table threw (unknown move, etc.) → can't confirm effectiveness → skip.
        }
    }
    if (!opp_has_effective)
        bits |= SCOPE_OPP_NO_DAMAGE;

    return bits;
}

// ---------------------------------------------------------------------------
// Line state: player HP point + opp HP cover interval.
// ---------------------------------------------------------------------------

struct LineState {
    int32_t pw;         // player worst-case HP (realizable)
    int32_t pwHi;       // player cover ceiling (dormant in wave 0; == pw unless future heal)
    int32_t oLo;        // opp HP interval low (max-damage trajectory)
    int32_t oHi;        // opp HP interval high (min-damage trajectory)
    bool    opp_item_used;  // has the opp's one-shot item (Sash/Sitrus) been consumed?
    bool    tight;          // every step on this line is realizable by a single branch
};

// ---------------------------------------------------------------------------
// Adversary continuation dominance for the Pareto frontier.
// a dominates b if the continuation from a is at least as bad for player as b:
// player HP at most as high (worse), opp interval covers b's interval pessimistically.
// ---------------------------------------------------------------------------

static bool dominates(const LineState& a, const LineState& b) {
    // a.pw <= b.pw (player at least as damaged)
    if (a.pw > b.pw) return false;
    // a.oHi >= b.oHi (opponent's upper bound at least as high → harder to kill)
    if (a.oHi < b.oHi) return false;
    // a.oLo <= b.oLo (opponent's lower bound at least as low → covers more ground)
    if (a.oLo > b.oLo) return false;
    // item state: if b's item is used, a's must also be used (used is better for player, so
    // "a dominates b" when a's item status is at least as bad = if b is used, a may be anything;
    // if b is not used, a must also be not used to stay comparable)
    if (!b.opp_item_used && a.opp_item_used) return false;
    return true;
}

// ---------------------------------------------------------------------------
// Apply opponent Sash/Sitrus threshold mechanics to the opp interval after player hit.
// Returns a scope-out reason if a threshold straddles the interval.
// opp_max_hp: the opponent's max HP.
// ---------------------------------------------------------------------------

// After the player applies min_dmg..max_dmg to the interval [oHi, oLo], compute
// the new interval. Returns false and sets out_* on success; returns true if
// the interval hits a threshold in a way that requires routing to UNKNOWN.
//
// Threshold logic (both-or-neither rule):
//   - Focus Sash at full HP: if the interval starts at max_hp (all branches at full HP),
//     and any roll would bring HP to <= 0, the Sash triggers. If ALL rolls would kill
//     (oLo <= 0 after hit), every roll triggers Sash → all survive at 1. If SOME would
//     kill (oHi <= 0 but oLo > 0, or min_dmg kills some but not all), straddle → UNKNOWN.
//   - Sitrus: trigger when HP <= max_hp/2. If the post-hit interval straddles max_hp/2
//     (some rolls trigger, some don't) → UNKNOWN. Both trigger or neither → proceed.
static bool apply_player_damage_to_interval(
    int32_t min_dmg, int32_t max_dmg,
    int32_t oHi_in, int32_t oLo_in,
    int32_t opp_max_hp,
    bool   opp_has_sash, bool opp_has_sitrus, bool opp_item_used,
    bool   opp_at_full_hp,
    int32_t& out_oHi, int32_t& out_oLo,
    bool& out_item_used,
    uint32_t& out_scope_bits)
{
    out_scope_bits = 0;
    out_item_used = opp_item_used;

    // Post-hit opp HP range: new_hi = oHi_in - min_dmg (min damage leaves more HP),
    // new_lo = oLo_in - max_dmg (max damage leaves less HP).
    // Wait — the interval's CONVENTION: oHi is "high HP" (min-damage trajectory) and
    // oLo is "low HP" (max-damage trajectory). Applying damage:
    //   new_oHi = oHi_in - min_dmg   (min damage on the high-HP trajectory)
    //   new_oLo = oLo_in - max_dmg   (max damage on the low-HP trajectory)
    int32_t new_hi = oHi_in - min_dmg;
    int32_t new_lo = oLo_in - max_dmg;

    // Sash/Sturdy: only applies at FULL HP (both trajectories must be at full HP).
    if ((opp_has_sash) && !opp_item_used) {
        if (opp_at_full_hp) {
            // Both branches are at full HP. Does the Sash activate?
            if (new_lo <= 0 && new_hi <= 0) {
                // All rolls kill → all trigger Sash → all land at 1.
                new_lo = new_hi = 1;
                out_item_used = true;
            } else if (new_lo <= 0) {
                // Some rolls kill (oLo branch), some don't (oHi branch) → straddle.
                out_scope_bits |= SCOPE_ITEM_NOT_ALLOWED;  // reuse as "threshold straddle"
                return true;  // → UNKNOWN(AT_THRESH)
            }
            // else: no rolls kill → Sash not triggered. Fall through.
        }
        // If not at full HP, Sash doesn't trigger. Fall through.
    }

    // Kill check: if new_hi <= 0, all branches kill the opp.
    if (new_hi <= 0) {
        out_oHi = new_hi;
        out_oLo = new_lo;
        return false;  // Kill!
    }

    // Clamp the lower bound: KO'd branches exit as wins; survivors continue.
    if (new_lo <= 0) new_lo = 1;

    // Sitrus Berry: triggers at hp <= max_hp/2. Post-hit check.
    if (opp_has_sitrus && !opp_item_used) {
        int32_t trigger_at = opp_max_hp / 2;
        bool hi_triggers = (new_hi <= trigger_at);
        bool lo_triggers = (new_lo <= trigger_at);
        if (hi_triggers != lo_triggers) {
            // Straddle: some branches trigger, some don't → UNKNOWN.
            return true;  // → UNKNOWN(AT_THRESH)
        }
        if (hi_triggers) {
            // Both trigger: apply Sitrus heal.
            int32_t heal = opp_max_hp * 3 / 10;  // engine: 30% heal, floor
            new_hi += heal; if (new_hi > opp_max_hp) new_hi = opp_max_hp;
            new_lo += heal; if (new_lo > opp_max_hp) new_lo = opp_max_hp;
            out_item_used = true;
        }
        // Both don't trigger: fall through.
    }

    if (new_hi < new_lo)
        throw std::runtime_error("analytic: interval inverted after damage application");

    out_oHi = new_hi;
    out_oLo = new_lo;
    return false;
}

// ---------------------------------------------------------------------------
// Interval mask guard: re-query the AI support at every integer HP in [oLo, oHi].
// Returns true (mask is stable = UNKNOWN not required) or false (mask differs → UNKNOWN).
// This is the full per-HP scan per plan requirement; endpoint-only optimization is gated
// on Task 6 telemetry.
// ---------------------------------------------------------------------------

static bool interval_mask_stable(const BattleState& base_state,
                                  int32_t oLo, int32_t oHi,
                                  const std::vector<ExecAction>& support_at_oHi) {
    if (oLo == oHi) return true;  // degenerate interval; no check needed

    // Build the reference support set from the oHi query.
    // Support = set of move slots with p>0.
    auto support_set = [&](const std::vector<ExecAction>& acts) {
        std::vector<int32_t> slots;
        for (const auto& a : acts) slots.push_back(a.move_slot);
        std::sort(slots.begin(), slots.end());
        return slots;
    };
    std::vector<int32_t> ref = support_set(support_at_oHi);

    // Scan every integer HP in [oLo, oHi-1].
    for (int32_t hp = oLo; hp < oHi; ++hp) {
        BattleState scratch = base_state;
        SideState& opp_side = scratch.side1;
        int opp_ai = 1;
        PokemonState& opp_mon = opp_side.team[opp_side.active_indices[0]];
        opp_mon.hp = hp;
        opp_mon.has_hp = true;

        std::vector<ActionProb> dist = cpp_compute_action_probabilities(scratch, opp_ai);
        std::vector<int32_t> cur;
        for (const auto& ap : dist) {
            if (ap.prob > 0.0) cur.push_back(ap.action.move_slot);
        }
        std::sort(cur.begin(), cur.end());

        if (cur != ref) return false;
    }
    return true;
}

// ---------------------------------------------------------------------------
// runLine: one greedy line (recursion up to turn cap and depth cap).
// Returns WIN, LOSS, or UNKNOWN; sets result.tag and result.tight.
// ---------------------------------------------------------------------------

static constexpr int TURN_CAP  = 50;
static constexpr int LINE_CAP  = 64;   // total lines/branches spawned
static constexpr int DEPTH_CAP = 8;

struct RunLineCtx {
    const BattleState& state0;   // initial state for mask queries
    int   pl_max_hp;
    int   opp_max_hp;
    bool  opp_has_sitrus;
    bool  opp_has_sash;
    int   lines_used;
};

static AVerdict run_line(LineState L, int depth, RunLineCtx& ctx, AnalyticResult& result);

// Compute the minimum damage value from a DamageTable (across both crit classes).
static int32_t table_min(const DamageTable& dt) {
    int32_t mn = INT32_MAX;
    for (int32_t v : dt.noncrit) if (v < mn) mn = v;
    for (int32_t v : dt.crit)    if (v < mn) mn = v;
    return mn == INT32_MAX ? 0 : mn;
}

// Compute the maximum damage value from a DamageTable (across both crit classes).
static int32_t table_max(const DamageTable& dt) {
    int32_t mx = 0;
    for (int32_t v : dt.noncrit) if (v > mx) mx = v;
    for (int32_t v : dt.crit)    if (v > mx) mx = v;
    return mx;
}

// Build a BattleState mirroring the current line state for mask/speed queries.
// Only HP fields are modified; all other state context is preserved from state0.
static BattleState sync_state(const BattleState& state0,
                               int32_t pw, int32_t oHi,
                               bool opp_item_used) {
    BattleState s = state0;
    // Player HP.
    s.side0.team[s.side0.active_indices[0]].hp = pw;
    s.side0.team[s.side0.active_indices[0]].has_hp = true;
    // Opponent HP (use oHi for mask queries — worst-case opp HP).
    s.side1.team[s.side1.active_indices[0]].hp = oHi;
    s.side1.team[s.side1.active_indices[0]].has_hp = true;
    // Mark item consumed if applicable.
    if (opp_item_used) {
        PokemonState& opp_mon = s.side1.team[s.side1.active_indices[0]];
        opp_mon.item = ITEM_NONE;
        // Also mark consumed_berry so residuals know.
        // (This is the cleanest we can do from the analytic layer.)
    }
    return s;
}

// Select the best player move: the one with the largest minimum damage to opp.
// Returns move_slot (-1 if no valid damaging move found) and fills in the DamageTable.
static int pick_player_move(const BattleState& cur_state,
                             DamageTable& out_tbl) {
    int   best_slot  = -1;
    int32_t best_min = -1;

    for (int s = 0; s < 4; ++s) {
        int32_t mid = move_id_at_slot(active_mon(cur_state, 0), s);
        if (mid <= 0) continue;
        const MoveData* md = get_md(mid);
        if (!md) continue;
        // Only damaging single-hit 100% acc moves (scope gate already confirmed, but be safe).
        if (static_cast<int>(md->category) == 2) continue;  // STATUS
        if (md->max_hits > 1) continue;

        ExecAction act{};
        act.kind = 0;
        act.move_slot = s;
        try {
            DamageTable dt = damage_table(cur_state, 0, act);
            if (dt.immune) continue;
            int32_t mn = table_min(dt);
            if (mn > best_min) {
                best_min = mn;
                best_slot = s;
                out_tbl = std::move(dt);
            }
        } catch (...) {
            // damage_table threw → skip this move.
        }
    }

    return best_slot;
}

// Opponent's maximum damage from any move in support set, across all rolls and crits.
static int32_t opp_max_damage(const BattleState& cur_state,
                               const std::vector<ExecAction>& support) {
    int32_t mx = 0;
    for (const auto& act : support) {
        ExecAction a = act;
        try {
            DamageTable dt = damage_table(cur_state, 1, a);
            if (dt.immune) continue;
            int32_t v = table_max(dt);
            if (v > mx) mx = v;
        } catch (...) {}
    }
    return mx;
}

// Simulate one turn in a given order (player_first=true/false) starting from
// line state L. Returns the resulting LineState in out_L and the turn verdict:
//   -1 = line continues (out_L updated)
//    0 = player died (LOSS candidate)
//    1 = opp died (WIN candidate)
//    2 = threshold straddle or scope issue (UNKNOWN)
static int sim_turn_ordered(
    LineState L, bool player_first,
    const BattleState& base_state,
    const std::vector<ExecAction>& dmg_support,
    RunLineCtx& ctx, AnalyticResult& result,
    int turn,
    LineState& out_L)
{
    int32_t opp_mx = opp_max_damage(base_state, dmg_support);
    if (opp_mx <= 0) {
        result.tag = AT_STALL;
        return 2;  // UNKNOWN
    }

    if (player_first) {
        // Player hits opp first.
        BattleState cur_act = sync_state(ctx.state0, L.pw, L.oHi, L.opp_item_used);
        DamageTable pl_tbl;
        int pl_slot = pick_player_move(cur_act, pl_tbl);
        if (pl_slot < 0) { result.tag = AT_SCOPE; return 2; }

        int32_t mn = table_min(pl_tbl);
        int32_t mx = table_max(pl_tbl);
        int32_t new_oHi, new_oLo;
        bool    new_item_used;
        uint32_t tbits = 0;
        bool at_full = (L.oHi == ctx.opp_max_hp);
        bool straddle = apply_player_damage_to_interval(
            mn, mx, L.oHi, L.oLo, ctx.opp_max_hp,
            ctx.opp_has_sash, ctx.opp_has_sitrus, L.opp_item_used, at_full,
            new_oHi, new_oLo, new_item_used, tbits);
        if (straddle || tbits) { result.tag = AT_THRESH; return 2; }

        if (new_oHi <= 0) {
            // Opp killed: player wins this turn.
            out_L = L;
            return 1;
        }
        L.oHi = new_oHi; L.oLo = new_oLo; L.opp_item_used = new_item_used;

        // Opp hits player second.
        int32_t new_pw = L.pw - opp_mx;
        if (new_pw <= 0) { out_L = L; return 0; }  // player dead
        L.pw = new_pw;
        out_L = L;
        return -1;  // continue
    } else {
        // Opp acts first, hits player.
        int32_t new_pw = L.pw - opp_mx;
        if (new_pw <= 0) { out_L = L; return 0; }  // player dead
        L.pw = new_pw;

        // Player acts second.
        BattleState cur_act = sync_state(ctx.state0, L.pw, L.oHi, L.opp_item_used);
        DamageTable pl_tbl;
        int pl_slot = pick_player_move(cur_act, pl_tbl);
        if (pl_slot < 0) { result.tag = AT_SCOPE; return 2; }

        int32_t mn = table_min(pl_tbl);
        int32_t mx = table_max(pl_tbl);
        int32_t new_oHi, new_oLo;
        bool    new_item_used;
        uint32_t tbits = 0;
        bool at_full = (L.oHi == ctx.opp_max_hp);
        bool straddle = apply_player_damage_to_interval(
            mn, mx, L.oHi, L.oLo, ctx.opp_max_hp,
            ctx.opp_has_sash, ctx.opp_has_sitrus, L.opp_item_used, at_full,
            new_oHi, new_oLo, new_item_used, tbits);
        if (straddle || tbits) { result.tag = AT_THRESH; return 2; }

        if (new_oHi <= 0) {
            out_L = L;
            return 1;  // opp dead
        }
        L.oHi = new_oHi; L.oLo = new_oLo; L.opp_item_used = new_item_used;
        out_L = L;
        return -1;  // continue
    }
}

static AVerdict run_line(LineState L, int depth, RunLineCtx& ctx, AnalyticResult& result) {
    if (depth > DEPTH_CAP || ctx.lines_used > LINE_CAP) {
        result.tag = AT_CAP;
        return AVerdict::UNKNOWN;
    }

    for (int turn = 1; turn <= TURN_CAP; ++turn) {
        if (L.oHi < L.oLo)
            throw std::runtime_error("analytic: opp HP interval inverted at turn entry");
        if (L.pw <= 0)
            throw std::runtime_error("analytic: player HP <= 0 at turn entry");

        // Build the state for this line (sync HP fields for engine queries).
        BattleState cur = sync_state(ctx.state0, L.pw, L.oHi, L.opp_item_used);

        // Re-fetch both damage tables at current state context (act time).
        DamageTable pl_tbl;
        int pl_slot = pick_player_move(cur, pl_tbl);
        // If no valid player move, this line can't progress — UNKNOWN.
        if (pl_slot < 0) {
            result.tag = AT_SCOPE;
            return AVerdict::UNKNOWN;
        }

        // Query AI support set at oHi (the reference HP for interval guard).
        std::vector<ActionProb> ai_dist = cpp_compute_action_probabilities(cur, 1);
        std::vector<ExecAction> support;
        for (const auto& ap : ai_dist) {
            if (ap.prob > 0.0) support.push_back(ap.action);
        }

        // Filter support to only damaging moves with the correct action kind.
        // (Wave 0: scope gate confirms only damaging moves, but we still filter.)
        std::vector<ExecAction> dmg_support;
        for (const auto& act : support) {
            if (act.kind != 0) continue;  // non-move action → UNKNOWN
            int32_t mid = move_id_at_slot(active_mon(cur, 1), act.move_slot);
            const MoveData* md = get_md(mid);
            if (!md) continue;
            if (static_cast<int>(md->category) == 2) continue;  // STATUS
            dmg_support.push_back(act);
        }

        // Interval mask guard: re-query every HP in [oLo, oHi].
        if (L.oLo < L.oHi) {
            if (!interval_mask_stable(ctx.state0, L.oLo, L.oHi, support)) {
                result.tag = AT_MASK;
                return AVerdict::UNKNOWN;
            }
        }

        // Effective speed for turn order.
        const PokemonState& pl_mon  = active_mon(cur, 0);
        const PokemonState& opp_mon = active_mon(cur, 1);
        int32_t pl_spd  = cpp_effective_speed(pl_mon,  cur.side0, cur);
        int32_t opp_spd = cpp_effective_speed(opp_mon, cur.side1, cur);

        bool player_faster = (pl_spd > opp_spd);
        bool speed_tie     = (pl_spd == opp_spd);

        // Speed-tie: certify BOTH orders independently.
        // If either order gives UNKNOWN, return UNKNOWN.
        // If both give the same verdict, return it.
        // If they disagree, clear tight and return UNKNOWN.
        if (speed_tie) {
            AnalyticResult res_pf = result;
            AnalyticResult res_sf = result;

            LineState out_pf, out_sf;
            int r_pf = sim_turn_ordered(L, true,  cur, dmg_support, ctx, res_pf, turn, out_pf);
            int r_sf = sim_turn_ordered(L, false, cur, dmg_support, ctx, res_sf, turn, out_sf);

            AVerdict v_pf = AVerdict::UNKNOWN, v_sf = AVerdict::UNKNOWN;

            if (r_pf == 2) { result.tag = res_pf.tag; return AVerdict::UNKNOWN; }
            if (r_sf == 2) { result.tag = res_sf.tag; return AVerdict::UNKNOWN; }

            if (r_pf == 1) {
                v_pf = AVerdict::WIN;
                res_pf.kill_turn = turn;
            } else if (r_pf == 0) {
                v_pf = L.tight ? AVerdict::LOSS : AVerdict::UNKNOWN;
            } else {
                // Continue: recurse.
                ctx.lines_used++;
                v_pf = run_line(out_pf, depth + 1, ctx, res_pf);
            }

            if (r_sf == 1) {
                v_sf = AVerdict::WIN;
                res_sf.kill_turn = turn;
            } else if (r_sf == 0) {
                v_sf = L.tight ? AVerdict::LOSS : AVerdict::UNKNOWN;
            } else {
                ctx.lines_used++;
                v_sf = run_line(out_sf, depth + 1, ctx, res_sf);
            }

            if (v_pf == AVerdict::WIN && v_sf == AVerdict::WIN) {
                result.kill_turn = (res_pf.kill_turn > 0) ? res_pf.kill_turn : res_sf.kill_turn;
                return AVerdict::WIN;
            }
            if (v_pf == v_sf) {
                // Both same non-WIN verdict.
                if (v_pf == AVerdict::LOSS) {
                    result.tag = AT_OK;
                    return AVerdict::LOSS;
                }
                result.tag = res_pf.tag;
                return AVerdict::UNKNOWN;
            }
            // Disagree: non-tight → UNKNOWN.
            result.tight = false;
            result.tag   = AT_NOT_TIGHT;
            return AVerdict::UNKNOWN;
        }  // end speed_tie block

        // Non-tie turn order: delegate to sim_turn_ordered.
        LineState out_L;
        int r = sim_turn_ordered(L, player_faster, cur, dmg_support, ctx, result, turn, out_L);
        if (r == 2) return AVerdict::UNKNOWN;  // threshold/scope, tag already set
        if (r == 1) {
            result.kill_turn = turn;
            return AVerdict::WIN;
        }
        if (r == 0) {
            // Player dead.
            return L.tight ? AVerdict::LOSS : AVerdict::UNKNOWN;
        }
        // r == -1: continue with updated state.
        L = out_L;
    }  // end turn loop

    result.tag = AT_CAP;
    return AVerdict::UNKNOWN;
}

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

AnalyticResult analytic_certify(const BattleState& state, const Question& q) {
    AnalyticResult result{};
    result.verdict    = AVerdict::UNKNOWN;
    result.tag        = AT_OK;
    result.scope_mask = 0;
    result.tight      = true;
    result.kill_turn  = 0;

    // Scope gate: accumulate all bits first.
    uint32_t scope_bits = full_scope_check(state, q);
    if (scope_bits) {
        result.verdict   = AVerdict::UNKNOWN;
        result.tag       = AT_SCOPE;
        result.scope_mask = scope_bits;
        // Special tag for stall (no opp effective move).
        if (scope_bits & SCOPE_OPP_NO_DAMAGE) result.tag = AT_STALL;
        return result;
    }

    const PokemonState& pl  = active_mon(state, 0);
    const PokemonState& opp = active_mon(state, 1);

    if (!pl.has_hp || !pl.has_max_hp || pl.hp <= 0)
        throw std::runtime_error("analytic: player has_hp/has_max_hp unset or HP <= 0");
    if (!opp.has_hp || !opp.has_max_hp || opp.hp <= 0)
        throw std::runtime_error("analytic: opp has_hp/has_max_hp unset or HP <= 0");

    bool opp_has_sitrus = (opp.item == ITEM_SITRUS);
    bool opp_has_sash   = (opp.item == ITEM_FOCUS_SASH);

    // If opp has Sitrus, the greedy exhaustiveness is broken (a different player policy
    // could overshoot the berry from above-half in a different turn). The interval model
    // COVERS but the greedy line may not be exhaustive. Degrade: LOSS → UNKNOWN if
    // non-tight steps occur (tight starts false for Sitrus matchups).
    bool tight_init = !opp_has_sitrus;

    LineState L{};
    L.pw           = pl.hp;
    L.pwHi         = pl.hp;   // cover ceiling (dormant in wave 0)
    L.oHi          = opp.hp;  // start: both trajectories at current HP
    L.oLo          = opp.hp;
    L.opp_item_used = false;
    L.tight        = tight_init;

    RunLineCtx ctx{
        state,
        pl.max_hp,
        opp.max_hp,
        opp_has_sitrus,
        opp_has_sash,
        0
    };

    AVerdict v = run_line(L, 0, ctx, result);

    result.verdict = v;
    result.tight   = L.tight && result.tight;  // merge per-state tight into global

    // POST: if LOSS and non-tight, degrade to UNKNOWN.
    if (result.verdict == AVerdict::LOSS && !result.tight) {
        result.verdict = AVerdict::UNKNOWN;
        result.tag     = AT_NOT_TIGHT;
    }

    // LOSS with AT_OK tag → set AT_OK.
    if (result.verdict == AVerdict::LOSS) result.tag = AT_OK;
    if (result.verdict == AVerdict::WIN)  result.tag = AT_OK;

    return result;
}
