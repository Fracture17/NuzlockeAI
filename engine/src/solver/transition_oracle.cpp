// DFS prefix-replay transition oracle. Each leaf = one unique forced-RNG path through a
// (state, player action, opp action) triple. Uses CategoryBInjection for Cat-B forcing and
// OracleOverrides for Cat-A answers; scans AnalyticalRngLog to find the next branch point.
#include "solver/transition_oracle.h"

#include "ai_analytic.h"
#include "core_leaf.h"
#include "logger.h"
#include "move_exec_damage.h"
#include "oracle.h"
#include "rng_resolver.h"
#include "solver/oracle_types.h"
#include "solver_turn.h"
#include "state.h"
#include "state_eq.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

// Which system a prefix entry belongs to.
enum class Channel { CatB, CatA };

// One forced choice along the DFS path leading to the current leaf.
struct PrefixEntry {
    Channel channel;
    int     event;       // RngEventC value
    int     occurrence;  // for CatB: the per-turn occurrence index; for CatA: 0 (unused)
    int     value;       // forced outcome (bool as 0/1, int, or Cat-A option)
    double  prob;        // probability of choosing this value at this branch point
    // For Cat-A pair events (MOODY_STATS): second pick stored here; -1 = not a pair event.
    int     value2 = -1;
};

// ---------------------------------------------------------------------------
// Cat-A probability table
// ---------------------------------------------------------------------------

// Returns the probability of a specific Cat-A option.
// options: the full option vector from the pause payload.
// chosen: the specific option value we want the probability for.
// For SPEED_TIE and boolean-ish events with exactly 2 options: 0.5 each.
// For uniform events (METRONOME, SLEEP_TALK, STARF, ACUPRESSURE): 1/n.
// For EFFECT_SPORE: {11/30, 10/30, 9/30} in option order (SLEEP/PARA/POISON).
// For TRI_ATTACK: 1/3 each.
// For MOODY: handled as 1/7 for boost × 1/6 for drop (called separately per pick).
// Throws for unmodeled events.

// EFFECT_SPORE option order — VERIFIED against post_hit.cpp:387-401: the options
// vector is {STATUS_SLEEP, STATUS_PARALYSIS, STATUS_POISON} and the random-mode
// draw is r=randint(1,30): r<=11 SLEEP, r<=21 PARA, else POISON. So by option
// INDEX: 0=SLEEP=11/30, 1=PARA=10/30, 2=POISON=9/30.
static double cat_a_prob_single(int event_val, const std::vector<int>& options, int chosen_idx) {
    using E = RngEventC;
    auto ev = static_cast<E>(event_val);
    switch (ev) {
    case E::SPEED_TIE:
        // 0.5/0.5 for exactly 2 options (1v1 only ever has 2 combatants).
        if (options.size() != 2)
            throw std::runtime_error("TransitionOracle: SPEED_TIE expected 2 options, got "
                                     + std::to_string(options.size()));
        return 0.5;

    case E::EFFECT_SPORE_WHICH:
        // {11/30, 10/30, 9/30} by option index: SLEEP/PARA/POISON (post_hit.cpp:387).
        if (options.size() != 3)
            throw std::runtime_error("TransitionOracle: EFFECT_SPORE_WHICH expected 3 options");
        if (chosen_idx == 0) return 11.0/30.0;
        if (chosen_idx == 1) return 10.0/30.0;
        if (chosen_idx == 2) return  9.0/30.0;
        throw std::runtime_error("TransitionOracle: EFFECT_SPORE_WHICH bad index");

    case E::TRI_ATTACK_STATUS:
        return 1.0 / 3.0;

    case E::METRONOME_MOVE:
    case E::SLEEP_TALK_MOVE:
    case E::STARF_BERRY_STAT:
    case E::ACUPRESSURE_STAT:
        if (options.empty())
            throw std::runtime_error("TransitionOracle: Cat-A uniform event has empty options");
        return 1.0 / static_cast<double>(options.size());

    case E::MOODY_STATS:
        // Probability per boost pick: 1/7 (7 stat options). Drop pick: 1/6 (excl boost).
        // We handle the PAIR in the DFS separately; this gives the probability for the boost
        // pick only (which is called for the outer loop with 7 options).
        return 1.0 / 7.0;

    // Impossible in 1v1 phase 1 → throw
    case E::ACTION_SELECT:
    case E::FORCED_SWITCH:
    case E::POST_FAINT_SWITCH:
    case E::ROAR_TARGET:
        throw std::logic_error("TransitionOracle: impossible Cat-A event in 1v1 phase 1: "
                               + std::to_string(event_val));

    default:
        throw std::runtime_error("TransitionOracle: unmodeled Cat-A event: "
                                 + std::to_string(event_val));
    }
}

// ---------------------------------------------------------------------------
// Precondition checks
// ---------------------------------------------------------------------------

// ABILITY_QUICK_DRAW from core_leaf.cpp
static constexpr int32_t ABILITY_QUICK_DRAW = 259;

static void check_preconditions(const BattleState& state, const ExecAction& player_action) {
    // Exactly one active per side
    if (state.side0.active_indices.size() != 1 || state.side1.active_indices.size() != 1)
        throw std::runtime_error("TransitionOracle: phase 1 requires exactly 1 active per side");

    const PokemonState& p0 = state.side0.team[state.side0.active_indices[0]];
    const PokemonState& p1 = state.side1.team[state.side1.active_indices[0]];

    // Both actives alive
    if (p0.fainted || p0.hp <= 0)
        throw std::runtime_error("TransitionOracle: player active is fainted/HP=0");
    if (p1.fainted || p1.hp <= 0)
        throw std::runtime_error("TransitionOracle: opponent active is fainted/HP=0");

    // No Quick Draw on either active
    if (p0.ability == ABILITY_QUICK_DRAW || p0.base_ability == ABILITY_QUICK_DRAW)
        throw std::runtime_error("TransitionOracle: Quick Draw on player active (phase 1 exclusion)");
    if (p1.ability == ABILITY_QUICK_DRAW || p1.base_ability == ABILITY_QUICK_DRAW)
        throw std::runtime_error("TransitionOracle: Quick Draw on opponent active (phase 1 exclusion)");

    // Player action legal-ish: move_slot in range or Struggle
    if (player_action.kind == 0) {
        // MOVE action
        int slot = player_action.move_slot;
        // Struggle sentinel: move_slot == -2
        if (slot != -2) {
            if (slot < 0 || slot > 3)
                throw std::runtime_error("TransitionOracle: player move_slot out of range");
        }
    }
    // Switch actions are not expected in 1v1 phase 1 but we don't hard-fail on them
}

// ---------------------------------------------------------------------------
// Build OracleOverrides from CatA prefix entries
// ---------------------------------------------------------------------------

static OracleOverrides build_overrides(const std::vector<PrefixEntry>& prefix) {
    OracleOverrides ov;
    for (const auto& pe : prefix) {
        if (pe.channel != Channel::CatA) continue;
        int key = pe.event;
        if (static_cast<RngEventC>(key) == RngEventC::SPEED_TIE) {
            // SPEED_TIE answer is a SpeedTieOrder. The option value is the side*10+slot of
            // the winner; we build an ordering with winner first, then the other entry.
            // The full options set is implicit (only 2 combatants in 1v1).
            SpeedTieOrder sto;
            // winner is encoded as side*10+slot
            int winner_code = pe.value;
            int winner_side = winner_code / 10;
            int winner_slot = winner_code % 10;
            sto.order.push_back({winner_side, winner_slot});
            // The "loser" is the other side — construct from context: if winner is side 0,
            // loser is side 1, and vice versa (1v1 always has exactly 2 tied entries).
            int loser_side = 1 - winner_side;
            int loser_slot = 0;  // always slot 0 in singles
            sto.order.push_back({loser_side, loser_slot});
            ov.speed_tie_queue.push_back(std::move(sto));
        } else if (static_cast<RngEventC>(key) == RngEventC::MOODY_STATS) {
            // MOODY_STATS is a pair event: i0=boost, i1=drop
            OracleAnswer a; a.i0 = pe.value; a.i1 = pe.value2;
            ov.answers[key].push_back(a);
        } else {
            OracleAnswer a; a.i0 = pe.value;
            ov.answers[key].push_back(a);
        }
    }
    return ov;
}

// ---------------------------------------------------------------------------
// Build CategoryBInjection from CatB prefix entries
// ---------------------------------------------------------------------------

static CategoryBInjection build_catb_injection(const std::vector<PrefixEntry>& prefix) {
    CategoryBInjection inj;
    for (const auto& pe : prefix) {
        if (pe.channel != Channel::CatB) continue;
        // Determine the kind from the event type
        // Damage-roll and psywave-roll and multi-hit-count are int; everything else bool or int.
        // We store the branch as an int in value and push_int always; the resolver handles it.
        // Actually the resolvers distinguish kind. Let's map by event:
        using E = RngEventC;
        auto ev = static_cast<E>(pe.event);
        switch (ev) {
        case E::ACCURACY:
        case E::CRIT:
        case E::SECONDARY_FIRES:
        case E::PROC_FIRES:
        case E::FLINCH:
        case E::QUICK_CLAW:
        case E::ANCIENT_POWER_BOOST:
        case E::WAKE:
        case E::CONFUSION_SNAP:
        case E::DEFROST:
        case E::CONFUSION_SELF_HIT:
        case E::ATTRACT_IMMOBILIZE:
        case E::FULL_PARALYSIS:
            inj.push_bool(pe.event, pe.occurrence, pe.value != 0);
            break;
        case E::DAMAGE_ROLL:
        case E::MULTI_HIT_COUNT:
        case E::PSYWAVE_ROLL:
        case E::BINDING_DURATION:
        case E::RAMPAGE_DURATION:
            inj.push_int(pe.event, pe.occurrence, pe.value);
            break;
        default:
            // Unknown Cat-B event (Cat-A values shouldn't reach here)
            inj.push_int(pe.event, pe.occurrence, pe.value);
            break;
        }
    }
    return inj;
}

// Compute product of all probabilities in the prefix.
static double prefix_prob(const std::vector<PrefixEntry>& prefix) {
    double p = 1.0;
    for (const auto& pe : prefix) p *= pe.prob;
    return p;
}

// ---------------------------------------------------------------------------
// DFS state
// ---------------------------------------------------------------------------

struct DFSState {
    const BattleState&         input_state;
    const ExecAction&          player_action;
    const ExecAction&          opp_action;
    double                     opp_prob;
    const OracleEmitFn&        emit;
    const LeafDebugFn*         debug_emit;   // nullptr = off (hot-path null check)
    OrderingHint               hint;
    uint64_t                   max_leaves;
    bool                       aggregate_damage_rolls;
    TransitionOracle::CollapseMode collapse;
    uint64_t                   leaves        = 0;
    uint64_t                   turn_execs    = 0;
    bool                       aborted       = false;
    bool                       budget_exceeded = false;
    CategoryBOccurrenceCounters occ_counters;
    AnalyticalRngLog            log;
    DamageLoopLuck              luck_p0;
    DamageLoopLuck              luck_p1;
    TurnLuck                    tl0;
    TurnLuck                    tl1;
};

// ---------------------------------------------------------------------------
// Expand options for the next Cat-B branch point
// ---------------------------------------------------------------------------

// Returns all (value, prob) pairs for a Cat-B log entry.
// For truncated PSYWAVE_ROLL: oracle owns the domain (k=0..100).
// For any other truncated entry: throw.
// For DAMAGE_ROLL with aggregate=true: group rolls by identical dmg_by_roll value;
//   one branch per distinct-damage bucket, value = lowest roll in bucket, prob = count/16.
//   Requires has_dmg_by_roll; throws if annotation is missing (fail loud).
// For DAMAGE_ROLL with aggregate=false (or CONFUSION_SELF_HIT 15-way): individual rolls.
// Unknown Cat-B events: throw naming the event id.
//
// Collapse semantics (when CollapseMode != None):
//   - Pessimal: return only the single worst-for-player option (p=1.0) for eligible events.
//   - Coarse: for DAMAGE_ROLL only, return {min, max} dmg rolls (2 per crit class); all else exact.
//   - Eligible event table and starvation rule are enforced here (see collapse_rule comments below).
//
// Non-static so tests can call it directly for the unknown-event throw test.
std::vector<std::pair<int,double>> expand_catb_options_for_test(const AnalyticalRngEntry& entry);

// ---------------------------------------------------------------------------
// Collapse-eligible event table (Lemma (o) re-derivation for this engine).
//
// Rule: collapse ONLY randomness that ALWAYS PROGRESSES regardless of outcome.
// Starvation caveat: if an event can gate whether the PLAYER's action does anything
// (e.g. player's accuracy miss leaves both sides unchanged → pure self-loop), collapsing
// to the worst outcome can fabricate an all-self-loop action → false LOSS. Therefore:
//   - NEVER collapse events that gate whether the player acts (player accuracy, player
//     full-paralysis, player flinch, player attract, player confusion self-hit, quick claw
//     on player side) — these can starve the player's action into a self-loop.
//   - Safely collapse: events that change game state regardless of outcome (damage quantity,
//     crit multiplier, hit count, opponent-side gating events).
//
// Per-event decision (attacker_side=0 → player is attacker; attacker_side=1 → opp is attacker):
//
// DAMAGE_ROLL (5): ELIGIBLE. Damage always lands; only magnitude varies. This is the primary
//   source of tree branching. Worst: max damage when opp attacks (attacker_side=1), min when
//   player attacks. In Coarse mode: {min, max} dmg values per crit class.
//
// CRIT (2): ELIGIBLE. A hit is already guaranteed to land when crit rolls. Crit only changes
//   multiplier, never gates whether the move executes. Worst: crit (1) when opp attacks
//   (amplifies opp damage), no-crit (0) when player attacks (reduces player damage).
//
// MULTI_HIT_COUNT (7): ELIGIBLE. The first hit always progresses; subsequent hits are bonus.
//   Worst: max hits (opp attacks more), min hits (player attacks less).
//
// ACCURACY (1): NOT ELIGIBLE for player's moves (starvation: miss → no state change →
//   self-loop → fabricated failure). For opponent accuracy: collapse to always-hit is
//   subset-sound (opp hit is worse for player and progresses). HOWEVER, distinguishing
//   who is attacker reliably at this site requires checking attacker_side. We ONLY collapse
//   accuracy when attacker_side == 1 (opponent is attacker); leave player accuracy intact.
//
// SECONDARY_FIRES (3): NOT ELIGIBLE. A secondary effect miss leaves the primary damage
//   path intact (primary already landed), but it gates an ADDITIONAL effect. Collapsing
//   "secondary fires" to "always fires" is sound by subset logic — it doesn't cause
//   starvation. However, "secondary doesn't fire" (worst when player's secondary would
//   help) and "always fires" (worst when opp's secondary damages player) both progress.
//   The attacker-side split applies here too. Conservatively: NOT COLLAPSED (sound; slower).
//   Justification: secondary effects are uncommon and the gain is marginal; staying exact here.
//
// PROC_FIRES (4): Same analysis as SECONDARY_FIRES. NOT COLLAPSED (conservative, sound).
//
// FLINCH (14): NOT ELIGIBLE for player's moves as defender (player flinches → player can't
//   act → starvation of player's next action). For opp flinch (player's move causes opp to
//   flinch): opp flinch is beneficial for player — collapsing to "always flinch" is safe but
//   the worst-for-player direction is "no flinch". Tracking who the flinch affects (attacker
//   side + move category) is complex. Conservatively: NOT COLLAPSED (sound).
//
// FULL_PARALYSIS (13): NOT ELIGIBLE for player side. If player is fully paralyzed → can't
//   act → starvation. For opponent full-paralysis (opp can't act = good for player): worst =
//   no full paralysis. But distinguishing who is affected (attacker vs defender) is event-
//   contextual. The 'who' field has attacker_side. Full paralysis is a DEFENDER event
//   (para'd mon can't act). If attacker_side==0 (player is the one who might be para'd,
//   as defender of the move), NOT eligible. If attacker_side==1 (opp might be para'd),
//   collapse to not-paralyzed (worst = opp acts). Conservatively: NOT COLLAPSED.
//
// ATTRACT_IMMOBILIZE (12): NOT ELIGIBLE for player side. Attract immobilizes the ATTACKER
//   (the one with the crush). If player is immobilized → no action → starvation. who.attacker_side
//   identifies who's immobilized. NOT COLLAPSED (conservative: attacker attribution complex).
//
// CONFUSION_SELF_HIT (11): NOT ELIGIBLE for player side. If player hits itself → loses HP but
//   progresses (not a self-loop since HP changes). However confusion snapping (CONFUSION_SNAP)
//   is the gate for whether confusion persists. Strictly: CONFUSION_SELF_HIT does progress
//   (player's HP changes) but it replaces the intended action. Complex to reason soundly.
//   NOT COLLAPSED (conservative).
//
// CONFUSION_SNAP (9): Gates whether confusion lifts. Affects player turn routing but doesn't
//   starve (after snap, player still acts with full move choice). NOT COLLAPSED (conservative).
//
// WAKE (8): Gates whether sleep lifts. If player stays asleep → can't act → starvation.
//   NOT COLLAPSED (player could be asleep; collapsing "always wake" or "always sleep" is
//   risky without side-specific tracking).
//
// DEFROST (10): Gates whether freeze lifts. Same analysis as WAKE. NOT COLLAPSED.
//
// QUICK_CLAW (15): Gates whether the mon with Quick Claw moves first. If player has Quick
//   Claw and it activates → player goes first (potential win path). Collapsing to "never
//   activates" could starve a player action slot. NOT COLLAPSED.
//
// ANCIENT_POWER_BOOST (16): Gates a stat boost after Ancient Power hits. Boosts always
//   follow a hit (the move hit for primary damage). Collapsing "no boost" is worst when
//   player uses it, "always boost" is worst when opp uses it. Doesn't gate whether the
//   primary move fires. WOULD BE ELIGIBLE but rare enough to not bother. NOT COLLAPSED.
//
// BINDING_DURATION (17): Duration of binding effects (2 or 3 turns). Progresses regardless.
//   Worst: more turns (opp binds player longer). ELIGIBLE in principle. NOT COLLAPSED for
//   simplicity (marginal; binding is rare).
//
// RAMPAGE_DURATION (18): Duration of rampage/thrash/petal-dance (2 or 3 turns). Similar to
//   binding. NOT COLLAPSED for simplicity.
//
// SPEED_TIEBREAKER (32): Cat-B speed tie resolution. Determines order but doesn't eliminate
//   actions. Worst for player = opp goes first. ELIGIBLE in principle. NOT COLLAPSED because
//   speed ties are already rare in 1v1 and order resolution is complex here.
//
// RANDOM_TARGET (33): Random target for multi-target moves (irrelevant in 1v1 singles).
//   NOT COLLAPSED.
//
// Summary: collapsed in Pessimal: DAMAGE_ROLL, CRIT, MULTI_HIT_COUNT, ACCURACY (opp only).
// Collapsed in Coarse: DAMAGE_ROLL only ({min,max} per crit class).
// ---------------------------------------------------------------------------

// Returns the collapse rule for an event in Pessimal mode.
// Returns:
//   {eligible=true, worst_value=X} if the event should be collapsed to value X.
//   {eligible=false} if the event should NOT be collapsed.
// Uses the entry's who field for attacker_side attribution.
struct CollapseDecision {
    bool eligible = false;
    int  worst_value = 0;  // valid iff eligible
};

static CollapseDecision collapse_rule(const AnalyticalRngEntry& entry) {
    using E = RngEventC;
    auto ev = static_cast<E>(entry.event);

    switch (ev) {
    case E::DAMAGE_ROLL:
        // ELIGIBLE. Worst: max damage when opp attacks, min when player attacks.
        // Must use dmg_by_roll annotation to pick an outcome that actually exists.
        // If annotation missing, fall through to NOT collapsed (safe, never guesses).
        if (!entry.has_dmg_by_roll || entry.options_count != 16) return {false, 0};
        {
            bool opp_attacks = (entry.who.attacker_side == 1);
            // Worst for player: if opp attacks, max damage (highest dmg_by_roll roll index).
            //   If player attacks, min damage (lowest dmg_by_roll roll index).
            int32_t target_dmg = opp_attacks ? entry.dmg_by_roll[0] : entry.dmg_by_roll[0];
            int worst_roll = 0;
            for (int ri = 0; ri < 16; ++ri) {
                int32_t dmg = entry.dmg_by_roll[ri];
                if (opp_attacks ? (dmg > target_dmg) : (dmg < target_dmg)) {
                    target_dmg = dmg;
                    worst_roll = ri;
                }
            }
            return {true, worst_roll};
        }

    case E::CRIT:
        // ELIGIBLE. Worst: crit (1) when opp attacks, no-crit (0) when player attacks.
        if (entry.options.size() < 2) return {false, 0};
        {
            bool opp_attacks = (entry.who.attacker_side == 1);
            int worst = opp_attacks ? 1 : 0;  // crit=1 hurts player when opp attacks
            return {true, worst};
        }

    case E::MULTI_HIT_COUNT:
        // ELIGIBLE. Worst: max hits when opp attacks (more opp damage),
        //   min hits when player attacks (less player damage).
        if (entry.options.size() < 1) return {false, 0};
        {
            bool opp_attacks = (entry.who.attacker_side == 1);
            // Find max/min from options
            int32_t best = entry.options[0];
            for (size_t i = 1; i < entry.options.size(); ++i) {
                if (opp_attacks ? (entry.options[i] > best) : (entry.options[i] < best))
                    best = entry.options[i];
            }
            return {true, static_cast<int>(best)};
        }

    case E::ACCURACY:
        // ELIGIBLE only for opponent's moves (attacker_side==1).
        // Player accuracy: NOT collapsed (starvation guard).
        if (entry.who.attacker_side != 1) return {false, 0};
        // Worst for player: opp always hits (value=1 in {0=miss, 1=hit}).
        return {true, 1};

    default:
        // All other events: not collapsed. Conservative = always sound.
        return {false, 0};
    }
}

static std::vector<std::pair<int,double>> expand_catb_options(
        const AnalyticalRngEntry& entry,
        bool aggregate_damage_rolls,
        TransitionOracle::CollapseMode collapse) {
    using E = RngEventC;
    auto ev = static_cast<E>(entry.event);

    // ---------------------------------------------------------------------------
    // Pessimal collapse: apply BEFORE any format-specific expansion.
    // For eligible events, return a single-element list with the worst outcome.
    // Prob is NaN: collapsed subsets are not probability distributions. The bsolver
    // only uses these for possibility (p>0), never reads the numeric prob value.
    // ---------------------------------------------------------------------------
    if (collapse == TransitionOracle::CollapseMode::Pessimal) {
        CollapseDecision d = collapse_rule(entry);
        if (d.eligible) {
            // Verify the worst value actually exists in the option list (p>0 in exact tree).
            // For DAMAGE_ROLL: worst_value is a roll index 0..15 — always valid.
            // For other events: it's a value from the options vector; search for it.
            bool value_valid = false;
            if (ev == E::DAMAGE_ROLL) {
                // Roll index 0..15 is always valid for a 16-outcome DAMAGE_ROLL.
                value_valid = (entry.options_count == 16 && d.worst_value >= 0 && d.worst_value < 16);
            } else {
                for (size_t i = 0; i < entry.options.size(); ++i) {
                    if (entry.options[i] == d.worst_value) { value_valid = true; break; }
                }
            }
            // If the worst value can't be verified, fall through to exact (safe, never guesses).
            if (value_valid)
                return {{d.worst_value, std::numeric_limits<double>::quiet_NaN()}};
        }
        // Non-eligible events in Pessimal: fall through to exact expansion.
    }

    // ---------------------------------------------------------------------------
    // Coarse collapse: only DAMAGE_ROLL → {min_roll, max_roll} per crit class.
    // All other events expand exactly.
    // Probs are NaN: the {min,max} selection is possibility-only, not a distribution.
    // ---------------------------------------------------------------------------
    if (collapse == TransitionOracle::CollapseMode::Coarse && ev == E::DAMAGE_ROLL) {
        int count = static_cast<int>(entry.options_count);
        if (count == 16) {
            // Requires dmg_by_roll annotation for min/max selection.
            // If annotation missing, fall through to normal expansion (safe).
            if (!entry.has_dmg_by_roll) {
                // Fall through below; aggregation path will throw if aggregate=ON.
            } else {
                // Find roll indices with min and max damage.
                int min_roll = 0, max_roll = 0;
                int32_t min_dmg = entry.dmg_by_roll[0], max_dmg = entry.dmg_by_roll[0];
                for (int ri = 1; ri < 16; ++ri) {
                    if (entry.dmg_by_roll[ri] < min_dmg) { min_dmg = entry.dmg_by_roll[ri]; min_roll = ri; }
                    if (entry.dmg_by_roll[ri] > max_dmg) { max_dmg = entry.dmg_by_roll[ri]; max_roll = ri; }
                }
                const double nan = std::numeric_limits<double>::quiet_NaN();
                if (min_roll == max_roll) {
                    // All rolls identical → single branch. Prob NaN: not a distribution.
                    return {{min_roll, nan}};
                }
                // Two branches: min and max damage rolls. Probs NaN: this is a
                // possibility-only subset, not a probability distribution. Soundness
                // of the subset-support theorem requires only that both outcomes exist
                // in the exact distribution, not that probs are correct.
                return {{min_roll, nan}, {max_roll, nan}};
            }
        }
        // 15-way confusion roll or annotation missing: fall through to exact.
    }

    if (entry.options_truncated) {
        // Only PSYWAVE_ROLL is permitted to be truncated
        if (ev != E::PSYWAVE_ROLL)
            throw std::runtime_error(
                "TransitionOracle: truncated Cat-B entry for unmodeled event "
                + std::to_string(entry.event));
        // Oracle-owned domain: k=0..100, p=1/200 at endpoints, 1/100 interior
        std::vector<std::pair<int,double>> opts;
        opts.reserve(101);
        opts.push_back({0, 1.0/200.0});
        for (int k = 1; k <= 99; ++k)
            opts.push_back({k, 1.0/100.0});
        opts.push_back({100, 1.0/200.0});
        return opts;
    }

    // p_chosen must be valid for all non-truncated Cat-B entries
    if (entry.p_chosen < 0.0)
        throw std::runtime_error(
            "TransitionOracle: Cat-B entry has p_chosen==-1 for event "
            + std::to_string(entry.event));

    // Build options list from the inline options vector
    size_t n = entry.options.size();
    if (n == 0)
        throw std::runtime_error(
            "TransitionOracle: Cat-B entry has empty options for event "
            + std::to_string(entry.event));

    // For boolean events (2 options {0,1}): the probability of the unchosen is complement.
    if (n == 2 && (ev == E::ACCURACY || ev == E::CRIT || ev == E::SECONDARY_FIRES ||
                   ev == E::PROC_FIRES || ev == E::FLINCH || ev == E::QUICK_CLAW ||
                   ev == E::ANCIENT_POWER_BOOST || ev == E::WAKE || ev == E::CONFUSION_SNAP ||
                   ev == E::DEFROST || ev == E::CONFUSION_SELF_HIT ||
                   ev == E::ATTRACT_IMMOBILIZE || ev == E::FULL_PARALYSIS)) {
        std::vector<std::pair<int,double>> opts;
        opts.push_back({entry.options[0], entry.options[0] == entry.chosen ?
                        entry.p_chosen : (1.0 - entry.p_chosen)});
        opts.push_back({entry.options[1], entry.options[1] == entry.chosen ?
                        entry.p_chosen : (1.0 - entry.p_chosen)});
        return opts;
    }

    if (ev == E::BINDING_DURATION || ev == E::RAMPAGE_DURATION) {
        // 2 options {4,5} or {2,3}, each p=0.5
        std::vector<std::pair<int,double>> opts;
        for (size_t i = 0; i < n; ++i) opts.push_back({entry.options[i], 0.5});
        return opts;
    }

    if (ev == E::DAMAGE_ROLL) {
        int count = static_cast<int>(entry.options_count);
        // CONFUSION_SELF_HIT roll: 15 outcomes — never aggregated (not a multiplicative branch).
        // Main damage roll: 16 outcomes — aggregated when flag is set and annotation present.
        if (count == 16 && aggregate_damage_rolls) {
            // Aggregation path: merge rolls with identical final damage into buckets.
            // Soundness: the turn state at this draw point is branch-invariant (DFS
            // prefix replay is deterministic up to here), so equal final damage ⇒
            // identical subtree from this draw forward. Merging is exact: Σp=1 is
            // preserved; distinct-damage rolls remain as individual branches.
            if (!entry.has_dmg_by_roll)
                throw std::runtime_error(
                    "TransitionOracle: DAMAGE_ROLL aggregation is ON but "
                    "has_dmg_by_roll=0 — annotation missing from damage.cpp");

            // Group roll indices by identical dmg_by_roll value.
            // Use a sorted map keyed by damage value; each entry stores the lowest roll index
            // and the count (to compute prob = count/16).
            // Ascending by damage: keeps AdverseFirst ordering semantics (lower = more adverse
            // for the attacker — best-effort, same as phase-1 Natural ordering).
            std::map<int32_t, std::pair<int,int>> buckets;  // dmg → (lowest_roll, count)
            for (int ri = 0; ri < 16; ++ri) {
                int32_t dmg = entry.dmg_by_roll[ri];
                auto it = buckets.find(dmg);
                if (it == buckets.end())
                    buckets[dmg] = {ri, 1};
                else
                    it->second.second += 1;
            }
            std::vector<std::pair<int,double>> opts;
            opts.reserve(buckets.size());
            for (const auto& kv : buckets) {
                int  lowest_roll = kv.second.first;
                int  cnt         = kv.second.second;
                opts.push_back({lowest_roll, cnt / 16.0});
            }
            return opts;
        }

        // No aggregation (or 15-way confusion roll): individual options, uniform p.
        std::vector<std::pair<int,double>> opts;
        opts.reserve(count);
        for (int i = 0; i < count; ++i)
            opts.push_back({i, 1.0 / static_cast<double>(count)});
        return opts;
    }

    if (ev == E::MULTI_HIT_COUNT) {
        // log records options as {min_hits, max_hits} for non-fixed or single for fixed
        // For (2,5) weighted distribution:
        if (n == 2 && entry.options[0] == 2 && entry.options[1] == 5) {
            return {{2, 0.35}, {3, 0.35}, {4, 0.15}, {5, 0.15}};
        }
        // General: entries are {min,max} → uniform
        if (n == 2) {
            int mn = entry.options[0], mx = entry.options[1];
            int cnt = mx - mn + 1;
            std::vector<std::pair<int,double>> opts;
            for (int v = mn; v <= mx; ++v)
                opts.push_back({v, 1.0/cnt});
            return opts;
        }
        // Fixed (single option): shouldn't branch
        return {{entry.options[0], 1.0}};
    }

    // Fail loud: unmodeled Cat-B event. Previously this guessed the distribution
    // shape — that silently produced wrong probabilities. A throw is always safer:
    // if any real event hits this path, the audit will catch it immediately.
    throw std::runtime_error(
        "TransitionOracle: unmodeled Cat-B event id=" + std::to_string(entry.event)
        + " — add explicit handling in expand_catb_options");
}

// Non-static test shim: calls with aggregate=false, collapse=None so tests can probe unknown-event throw.
std::vector<std::pair<int,double>> expand_catb_options_for_test(const AnalyticalRngEntry& entry) {
    return expand_catb_options(entry, /*aggregate_damage_rolls=*/false,
                               TransitionOracle::CollapseMode::None);
}

// ---------------------------------------------------------------------------
// Main DFS recursion
// ---------------------------------------------------------------------------

// Hard cap on prefix depth (= recursion depth). A legitimate 1v1 turn has at most
// a few dozen RNG draws; hundreds means the prefix/log alignment is broken (a forced
// draw not recognized as consumed, so the same branch point re-appears forever).
// Fail loud with a prefix dump instead of overflowing the stack.
static constexpr size_t MAX_PREFIX_DEPTH = 128;

static std::string dump_prefix(const std::vector<PrefixEntry>& prefix) {
    std::string s;
    size_t start = prefix.size() > 24 ? prefix.size() - 24 : 0;
    if (start > 0) s += "... (" + std::to_string(start) + " earlier entries)\n";
    for (size_t i = start; i < prefix.size(); ++i) {
        const auto& pe = prefix[i];
        s += "  [" + std::to_string(i) + "] "
           + (pe.channel == Channel::CatB ? "CatB" : "CatA")
           + " event=" + std::to_string(pe.event)
           + " occ=" + std::to_string(pe.occurrence)
           + " value=" + std::to_string(pe.value)
           + " p=" + std::to_string(pe.prob) + "\n";
    }
    return s;
}

// prefix_catb_count: number of CatB entries in the prefix (for log indexing)
static void dfs(DFSState& ds,
                std::vector<PrefixEntry>& prefix,
                int prefix_catb_count,
                int prefix_cata_count) {
    if (ds.aborted || ds.budget_exceeded) return;

    if (prefix.size() > MAX_PREFIX_DEPTH) {
        set_catb_injection(nullptr);
        set_catb_occ_counters(nullptr);
        set_analytical_rng_log(nullptr);
        throw std::runtime_error(
            "TransitionOracle: prefix depth exceeded " + std::to_string(MAX_PREFIX_DEPTH)
            + " — runaway branch extension (prefix/log misalignment). Prefix tail:\n"
            + dump_prefix(prefix));
    }

    // Rebuild infrastructure from prefix
    ds.occ_counters.reset();
    CategoryBInjection inj = build_catb_injection(prefix);
    OracleOverrides ov = build_overrides(prefix);

    set_catb_injection(&inj);
    set_catb_occ_counters(&ds.occ_counters);
    ds.log.clear();
    set_analytical_rng_log(&ds.log);

    BattleState state_copy = ds.input_state;

    // Build action lists (side0 = player, side1 = AI opponent)
    std::vector<ExecAction> actions_p0 = {ds.player_action};
    std::vector<ExecAction> actions_p1 = {ds.opp_action};
    bool mega_p0 = ds.player_action.mega;
    bool mega_p1 = ds.opp_action.mega;

    SolverTurnResult result = cpp_run_one_turn_solver(
        state_copy, actions_p0, actions_p1,
        ds.luck_p0, ds.luck_p1,
        ds.tl0, ds.tl1,
        mega_p0, mega_p1,
        ov);

    ++ds.turn_execs;

    // Always verify injection exhausted after each replay (fail loud on mismatch)
    try {
        inj.verify_exhausted();
    } catch (const std::exception& e) {
        set_catb_injection(nullptr);
        set_catb_occ_counters(nullptr);
        set_analytical_rng_log(nullptr);
        throw std::runtime_error(
            std::string("TransitionOracle: prefix divergence (verify_exhausted): ") + e.what());
    }

    set_catb_injection(nullptr);
    set_catb_occ_counters(nullptr);
    set_analytical_rng_log(nullptr);

    if (!result.ok) {
        throw std::runtime_error(
            "TransitionOracle: turn execution failed: " + result.error);
    }

    if (result.paused) {
        // Cat-A branch point: extend prefix for each option and recurse
        int ev_val = static_cast<int>(result.event);
        std::vector<int> options(result.options.begin(), result.options.end());

        if (static_cast<RngEventC>(ev_val) == RngEventC::MOODY_STATS) {
            // MOODY is a pair event: outer loop over boost (7 options),
            // inner loop over drop (6 options, excluding boost).
            // The pause options vector should carry the stat indices {0..6}.
            if (options.size() != 7)
                throw std::runtime_error("TransitionOracle: MOODY_STATS expected 7 options");
            for (int boost_val : options) {
                double boost_p = 1.0 / 7.0;
                // Drop options: all stats except boost
                for (int drop_val = 0; drop_val < 7; ++drop_val) {
                    if (drop_val == boost_val) continue;
                    double drop_p = 1.0 / 6.0;
                    PrefixEntry pe;
                    pe.channel = Channel::CatA;
                    pe.event = ev_val;
                    pe.occurrence = 0;
                    pe.value = boost_val;
                    pe.prob = boost_p * drop_p;
                    pe.value2 = drop_val;
                    prefix.push_back(pe);
                    dfs(ds, prefix, prefix_catb_count, prefix_cata_count + 1);
                    prefix.pop_back();
                    if (ds.aborted || ds.budget_exceeded) return;
                }
            }
        } else {
            // Standard single-pick Cat-A event
            for (size_t idx = 0; idx < options.size(); ++idx) {
                int opt_val = options[idx];
                double opt_p = cat_a_prob_single(ev_val, options, static_cast<int>(idx));
                PrefixEntry pe;
                pe.channel = Channel::CatA;
                pe.event = ev_val;
                pe.occurrence = 0;
                pe.value = opt_val;
                pe.prob = opt_p;
                pe.value2 = -1;
                prefix.push_back(pe);
                dfs(ds, prefix, prefix_catb_count, prefix_cata_count + 1);
                prefix.pop_back();
                if (ds.aborted || ds.budget_exceeded) return;
            }
        }
        return;
    }

    // Turn completed (ok && !paused): scan log for next Cat-B branch beyond the prefix
    // Count Cat-B entries in the log: the prefix consumed exactly prefix_catb_count of them.
    // Any entry beyond that is the next branch point.
    int catb_in_log = 0;
    int next_branch_idx = -1;
    for (size_t i = 0; i < ds.log.size(); ++i) {
        const AnalyticalRngEntry& e = ds.log.at(i);
        int ev = e.event;
        // Only Cat-B events (values 1-18 and 32-33)
        bool is_catb = (ev >= 1 && ev <= 18) || ev == 32 || ev == 33;
        if (!is_catb) continue;

        // Skip saturated draws (p_chosen == 1.0 means no real branch — outcome is certain)
        if (std::abs(e.p_chosen - 1.0) < 1e-12) continue;

        if (catb_in_log < prefix_catb_count) {
            ++catb_in_log;
            continue;
        }
        // This is the first Cat-B draw beyond the prefix → next branch point
        next_branch_idx = static_cast<int>(i);
        break;
    }

    if (next_branch_idx < 0) {
        // LEAF: no more Cat-B draws beyond prefix
        if (ds.leaves >= ds.max_leaves) {
            ds.budget_exceeded = true;
            return;
        }
        ++ds.leaves;
        double leaf_prob = prefix_prob(prefix) * ds.opp_prob;

        // Under any collapse mode, the emitted children no longer form a probability
        // distribution (siblings were pruned). Force NaN to expose accidental prob reads.
        // Exact mode (None) keeps real probabilities for the psolver contract.
        if (ds.collapse != TransitionOracle::CollapseMode::None)
            leaf_prob = std::numeric_limits<double>::quiet_NaN();

        // Debug callback (null-guarded; zero cost on hot path).
        if (ds.debug_emit && *ds.debug_emit) {
            LeafDebugInfo dbg;
            dbg.cumulative_prob  = leaf_prob;  // NaN in collapse modes by design
            dbg.ai_action        = ds.opp_action;
            dbg.ai_action_prob   = ds.opp_prob;
            dbg.path.reserve(prefix.size());
            for (const auto& pe : prefix) {
                LeafPathEntry lpe;
                lpe.channel    = (pe.channel == Channel::CatB) ? LeafChannel::CatB : LeafChannel::CatA;
                lpe.event      = pe.event;
                lpe.occurrence = pe.occurrence;
                lpe.value      = pe.value;
                lpe.prob       = pe.prob;
                lpe.value2     = pe.value2;
                dbg.path.push_back(lpe);
            }
            (*ds.debug_emit)(dbg);
        }

        ChildOutcome co;
        co.child = state_copy;
        co.prob  = leaf_prob;
        bool cont = ds.emit(co);
        if (!cont) ds.aborted = true;
        return;
    }

    // Branch on the next Cat-B draw
    const AnalyticalRngEntry& branch_entry = ds.log.at(static_cast<size_t>(next_branch_idx));
    int branch_event = branch_entry.event;

    // Determine the occurrence index for this branch point.
    // The occurrence counter (bump_occurrence) is called ONLY for non-saturated draws;
    // saturated draws (p_chosen==1.0) return before bump_occurrence in all resolvers.
    // So the occurrence index = number of previous non-saturated draws for this event.
    int occ_of_branch = 0;
    for (int i = 0; i < next_branch_idx; ++i) {
        const AnalyticalRngEntry& e = ds.log.at(static_cast<size_t>(i));
        if (e.event != branch_event) continue;
        bool is_catb = (e.event >= 1 && e.event <= 18) || e.event == 32 || e.event == 33;
        if (!is_catb) continue;
        // Only non-saturated draws call bump_occurrence
        if (std::abs(e.p_chosen - 1.0) > 1e-12) ++occ_of_branch;
    }

    // Expand options for this branch (collapse mode applied here).
    std::vector<std::pair<int,double>> branch_opts = expand_catb_options(branch_entry,
                                                                           ds.aggregate_damage_rolls,
                                                                           ds.collapse);

    // Sanity: branch option probabilities must sum to 1±1e-9.
    // Skip when any prob is NaN: collapsed subsets are not distributions (NaN is
    // intentional under Pessimal/Coarse for collapsed branches). For non-collapsed
    // events that fall through to exact expansion (even under collapse modes), the
    // probs are still real and the check remains active — a valid internal invariant.
    {
        bool has_nan = false;
        double s = 0.0;
        for (const auto& kv : branch_opts) {
            if (std::isnan(kv.second)) { has_nan = true; break; }
            s += kv.second;
        }
        if (!has_nan && std::abs(s - 1.0) > 1e-9)
            throw std::runtime_error(
                "TransitionOracle: Cat-B branch probs don't sum to 1 for event "
                + std::to_string(branch_event) + " (sum=" + std::to_string(s) + ")");
    }

    // AdverseFirst ordering: sort options to put player-adverse outcomes first.
    // This is a best-effort heuristic; must not change the multiset.
    // All comparators sort by VALUE (a.first / b.first), never by prob — safe under NaN.
    // For a damage-roll: lower player roll first (if player is attacker) or higher if opponent.
    // We approximate: for DAMAGE_ROLL, sort ascending (lower damage first = more adverse for player).
    // For ACCURACY/CRIT: put miss/no-crit first (adverse for player attacker).
    // For MULTI_HIT_COUNT: fewer hits first (adverse for player if player attacks).
    if (ds.hint == OrderingHint::AdverseFirst) {
        auto ev = static_cast<RngEventC>(branch_event);
        if (ev == RngEventC::DAMAGE_ROLL) {
            // Lower roll = less damage = adverse for attacker (player or opp — best-effort)
            std::stable_sort(branch_opts.begin(), branch_opts.end(),
                             [](const std::pair<int,double>& a, const std::pair<int,double>& b){
                                 return a.first < b.first; });
        } else if (ev == RngEventC::ACCURACY) {
            // Miss (0) before hit (1)
            std::stable_sort(branch_opts.begin(), branch_opts.end(),
                             [](const std::pair<int,double>& a, const std::pair<int,double>& b){
                                 return a.first < b.first; });
        } else if (ev == RngEventC::CRIT) {
            // No-crit (0) before crit (1) — non-crit more adverse for player attacker
            // Actually crit-first is more adverse for the OPPONENT, which is adversarial.
            // "Opponent-favoring" = opp crit before non-crit = crit (1) first.
            std::stable_sort(branch_opts.begin(), branch_opts.end(),
                             [](const std::pair<int,double>& a, const std::pair<int,double>& b){
                                 return a.first > b.first; });
        } else if (ev == RngEventC::MULTI_HIT_COUNT) {
            // Fewer hits = less player damage = adverse for player
            std::stable_sort(branch_opts.begin(), branch_opts.end(),
                             [](const std::pair<int,double>& a, const std::pair<int,double>& b){
                                 return a.first < b.first; });
        }
    }

    for (const auto& opt : branch_opts) {
        // Skip zero-probability branches (they contribute nothing and cannot be sampled).
        // NaN != 0.0 (IEEE 754), so collapsed branches with NaN prob are NOT skipped here
        // — they are kept as possibility branches for the bsolver.
        if (opt.second == 0.0) continue;
        PrefixEntry pe;
        pe.channel = Channel::CatB;
        pe.event = branch_event;
        pe.occurrence = occ_of_branch;
        pe.value = opt.first;
        pe.prob = opt.second;
        pe.value2 = -1;
        prefix.push_back(pe);
        dfs(ds, prefix, prefix_catb_count + 1, prefix_cata_count);
        prefix.pop_back();
        if (ds.aborted || ds.budget_exceeded) return;
    }
}

// ---------------------------------------------------------------------------
// Helpers: convert log entries to the public LeafPathEntry sequence
// ---------------------------------------------------------------------------

// True for Cat-B event IDs (values 1-18 and 32-33). Cat-A events are the complement.
static bool is_catb_event(int ev) {
    return (ev >= 1 && ev <= 18) || ev == 32 || ev == 33;
}

// Build the public LeafPathEntry sequence from the observed log, carrying dmg_by_roll
// for DAMAGE_ROLL entries. Only non-saturated Cat-B entries and Cat-A entries are included
// (saturated draws, p_chosen==1.0, are not real branch points).
static std::vector<LeafPathEntry> log_to_sequence(const AnalyticalRngLog& log) {
    std::vector<LeafPathEntry> seq;
    for (size_t i = 0; i < log.size(); ++i) {
        const AnalyticalRngEntry& e = log.at(i);
        // Include non-saturated Cat-B draws and all Cat-A draws (Cat-A always branch).
        bool is_catb = is_catb_event(e.event);
        bool saturated = is_catb && (std::abs(e.p_chosen - 1.0) < 1e-12);
        if (saturated) continue;

        LeafPathEntry lpe{};
        lpe.channel    = is_catb ? LeafChannel::CatB : LeafChannel::CatA;
        lpe.event      = e.event;
        lpe.occurrence = 0;  // occurrence recomputed below for Cat-B
        lpe.value      = e.chosen;
        lpe.prob       = e.p_chosen;
        lpe.value2     = -1;

        // For DAMAGE_ROLL: copy dmg_by_roll annotation if present.
        if (e.event == static_cast<int>(RngEventC::DAMAGE_ROLL) && e.has_dmg_by_roll) {
            lpe.has_dmg_by_roll = 1;
            for (int ri = 0; ri < 16; ++ri) lpe.dmg_by_roll[ri] = e.dmg_by_roll[ri];
        }

        seq.push_back(lpe);
    }

    // Recompute occurrence indices for Cat-B entries (matches the DFS occurrence counter logic).
    // occurrence = number of previous non-saturated draws of the same event before this one.
    std::map<int,int> occ_counts;
    for (auto& lpe : seq) {
        if (lpe.channel == LeafChannel::CatB) {
            lpe.occurrence = occ_counts[lpe.event]++;
        }
    }

    return seq;
}

// ---------------------------------------------------------------------------
// TransitionOracle::replay_path
// ---------------------------------------------------------------------------

ReplayResult TransitionOracle::replay_path(const BattleState& state,
                                            const ExecAction& player_action,
                                            const ExecAction& ai_action,
                                            const std::vector<LeafPathEntry>& prefix,
                                            const ReplayOptions& opts) const {
    check_preconditions(state, player_action);

    // Convert public prefix to internal PrefixEntry format.
    std::vector<PrefixEntry> internal_prefix;
    internal_prefix.reserve(prefix.size());
    for (const auto& lpe : prefix) {
        PrefixEntry pe{};
        pe.channel    = (lpe.channel == LeafChannel::CatB) ? Channel::CatB : Channel::CatA;
        pe.event      = lpe.event;
        pe.occurrence = lpe.occurrence;
        pe.value      = lpe.value;
        pe.prob       = lpe.prob;
        pe.value2     = lpe.value2;
        internal_prefix.push_back(pe);
    }

    // Build injection and overrides from the prefix (same as DFS does per-leaf).
    CategoryBOccurrenceCounters occ_counters;
    CategoryBInjection inj = build_catb_injection(internal_prefix);
    OracleOverrides ov = build_overrides(internal_prefix);

    set_catb_injection(&inj);
    set_catb_occ_counters(&occ_counters);

    AnalyticalRngLog log;
    log.clear();
    set_analytical_rng_log(&log);

    BattleState state_copy = state;

    std::vector<ExecAction> actions_p0 = {player_action};
    std::vector<ExecAction> actions_p1 = {ai_action};
    bool mega_p0 = player_action.mega;
    bool mega_p1 = ai_action.mega;

    DamageLoopLuck luck_p0{};
    DamageLoopLuck luck_p1{};
    TurnLuck tl0{};
    TurnLuck tl1{};

    SolverTurnResult result = cpp_run_one_turn_solver(
        state_copy, actions_p0, actions_p1,
        luck_p0, luck_p1, tl0, tl1,
        mega_p0, mega_p1, ov);

    // Attempt to verify that all prefix CatB entries were consumed. An unconsumed entry
    // means fewer branch points occurred than the prefix expected — e.g. the turn ended
    // before a later draw that the prefix forced. This is a divergence.
    bool verify_threw = false;
    std::string verify_error;
    try {
        inj.verify_exhausted();
    } catch (const std::exception& e) {
        verify_threw = true;
        verify_error = e.what();
    }

    set_catb_injection(nullptr);
    set_catb_occ_counters(nullptr);
    set_analytical_rng_log(nullptr);

    if (!result.ok) {
        throw std::runtime_error(
            "TransitionOracle::replay_path: turn execution failed: " + result.error);
    }

    // Build the observed sequence from the log.
    std::vector<LeafPathEntry> observed = log_to_sequence(log);

    // Sequence divergence check: compare observed vs prefix on STRUCTURE only
    // (event identity + occurrence + options-count). Chosen values and probs are
    // NOT compared here — the injection forces the prefix's value, so those tautologically
    // match; instead, value integrity is verified below via bucket-representative logic
    // (DAMAGE_ROLL) and the shift-property state check.
    //   (a) The count of Cat-B branch points in the observed sequence matches the prefix Cat-B count.
    //   (b) Each Cat-B branch point's (event, occurrence) matches.

    // Count Cat-B entries in the prefix and observed sequence.
    size_t prefix_catb = 0;
    for (const auto& lpe : prefix)
        if (lpe.channel == LeafChannel::CatB) ++prefix_catb;

    size_t observed_catb = 0;
    for (const auto& lpe : observed)
        if (lpe.channel == LeafChannel::CatB) ++observed_catb;

    // If prefix had unconsumed entries (verify_exhausted threw), the observed sequence
    // has fewer Cat-B events than expected → divergence.
    if (verify_threw) {
        throw std::runtime_error(
            "TransitionOracle::replay_path: prefix divergence — fewer branch points "
            "observed than prefix expected (verify_exhausted: " + verify_error
            + "). Prefix Cat-B count=" + std::to_string(prefix_catb)
            + " observed Cat-B count=" + std::to_string(observed_catb));
    }

    // If observed has MORE Cat-B events than the prefix forced, extra events fired
    // (e.g. berry or flinch beyond what the prefix covered) → divergence.
    if (observed_catb > prefix_catb) {
        // Find the first diverging entry: the (prefix_catb+1)-th Cat-B entry in observed.
        size_t extra_idx = 0;
        size_t catb_seen = 0;
        for (size_t i = 0; i < observed.size(); ++i) {
            if (observed[i].channel == LeafChannel::CatB) {
                if (catb_seen == prefix_catb) {
                    extra_idx = i;
                    break;
                }
                ++catb_seen;
            }
        }
        const auto& extra = observed[extra_idx];
        throw std::runtime_error(
            "TransitionOracle::replay_path: prefix divergence — extra Cat-B event "
            "observed beyond prefix end: event=" + std::to_string(extra.event)
            + " occurrence=" + std::to_string(extra.occurrence)
            + ". Prefix Cat-B count=" + std::to_string(prefix_catb)
            + " observed Cat-B count=" + std::to_string(observed_catb));
    }

    // Verify (event, occurrence) alignment between prefix Cat-B entries and observed Cat-B entries.
    // Also perform DAMAGE_ROLL bucket-representative verification: the prefix's value for a
    // DAMAGE_ROLL entry must be the LOWEST roll in the bucket {i : dmg_by_roll[i] == dmg_by_roll[value]}.
    // The DFS always picks the bucket-lowest roll as the representative; a value that isn't the
    // minimum of its bucket indicates a tampered prefix.
    {
        size_t obs_pos = 0;
        size_t pre_pos = 0;
        while (pre_pos < prefix.size() && obs_pos < observed.size()) {
            if (prefix[pre_pos].channel != LeafChannel::CatB) { ++pre_pos; continue; }
            while (obs_pos < observed.size() && observed[obs_pos].channel != LeafChannel::CatB)
                ++obs_pos;
            if (obs_pos >= observed.size()) break;  // already caught by count check above

            const LeafPathEntry& pe = prefix[pre_pos];
            const LeafPathEntry& oe = observed[obs_pos];
            if (pe.event != oe.event || pe.occurrence != oe.occurrence) {
                throw std::runtime_error(
                    "TransitionOracle::replay_path: prefix divergence at Cat-B position "
                    + std::to_string(obs_pos)
                    + " — expected event=" + std::to_string(pe.event)
                    + " occ=" + std::to_string(pe.occurrence)
                    + " got event=" + std::to_string(oe.event)
                    + " occ=" + std::to_string(oe.occurrence));
            }

            // DAMAGE_ROLL bucket-representative check (aggregated capture invariant).
            if (pe.event == static_cast<int>(RngEventC::DAMAGE_ROLL) && oe.has_dmg_by_roll) {
                int v = pe.value;
                if (v < 0 || v >= 16) {
                    throw std::runtime_error(
                        "TransitionOracle::replay_path: DAMAGE_ROLL prefix value out of range "
                        "at position " + std::to_string(obs_pos)
                        + " — value=" + std::to_string(v));
                }
                int32_t target_dmg = oe.dmg_by_roll[v];
                int bucket_min = -1;
                for (int i = 0; i < 16; ++i) {
                    if (oe.dmg_by_roll[i] == target_dmg) { bucket_min = i; break; }
                }
                if (bucket_min != v) {
                    throw std::runtime_error(
                        "TransitionOracle::replay_path: DAMAGE_ROLL prefix value is not the "
                        "bucket representative at position " + std::to_string(obs_pos)
                        + " — value=" + std::to_string(v)
                        + " but bucket-min for dmg=" + std::to_string(target_dmg)
                        + " is " + std::to_string(bucket_min)
                        + " (indicates tampered prefix or mismatched damage table)");
                }
            }
            ++pre_pos; ++obs_pos;
        }
    }

    // Shift-property (state) verification. For each DAMAGE_ROLL prefix entry, the expected
    // damage dealt is dmg_by_roll[value]. Sum the expected damage per defender side and
    // compare against the observed HP change from input to output. Any mismatch indicates
    // an "extra" HP-changing effect (berry heal, recoil, weather, etc.) not accounted for
    // in the prefix — a divergence between the DFS's captured leaf semantics and the
    // replay's actual semantics (e.g. Sitrus firing on a different-HP replay state).
    // Cap adjustment: if the observed hp reached 0 or is capped by max_hp, we detect that
    // and skip the strict comparison for that side (bucket-cap edge cases are handled by
    // §5.2 special cases, not here).
    // Bucket-solver expand runs its own endpoint-paired shift check and opts out
    // (opts.skip_state_shift_check=true) because this DAMAGE_ROLL-only check throws even
    // when a consumable berry fires identically at both LO and HI corners.
    if (!opts.skip_state_shift_check) {
        // Expected damage per defender side (0 or 1). Attacker's side takes no damage from
        // the DAMAGE_ROLL entry itself (recoil is a separate mechanic).
        int32_t expected_damage[2] = {0, 0};
        // Walk the log (not the sequence) to get participant sides per DAMAGE_ROLL entry.
        size_t catb_seen = 0;
        for (size_t i = 0; i < log.size(); ++i) {
            const AnalyticalRngEntry& le = log.at(i);
            bool is_catb = is_catb_event(le.event);
            if (!is_catb) continue;
            bool saturated = std::abs(le.p_chosen - 1.0) < 1e-12;
            if (saturated) continue;

            if (catb_seen >= prefix_catb) break;
            // Prefix entry corresponding to this log entry (walk prefix synchronously).
            size_t pi = 0, pcount = 0;
            while (pi < prefix.size()) {
                if (prefix[pi].channel == LeafChannel::CatB) {
                    if (pcount == catb_seen) break;
                    ++pcount;
                }
                ++pi;
            }
            ++catb_seen;
            if (pi >= prefix.size()) break;

            if (le.event == static_cast<int>(RngEventC::DAMAGE_ROLL) && le.has_dmg_by_roll) {
                int v = prefix[pi].value;
                if (v < 0 || v >= 16) continue;  // already caught above
                int8_t def_side = le.who.defender_side;
                if (def_side < 0 || def_side > 1) continue;
                expected_damage[def_side] += le.dmg_by_roll[v];
            }
        }

        // Actual HP change per side. Use active mons (phase 1 = 1v1, exactly one active per side).
        auto hp_of = [](const BattleState& s, int side) -> int32_t {
            const SideState& sd = (side == 0) ? s.side0 : s.side1;
            const PokemonState& m = sd.team[sd.active_indices[0]];
            return m.hp;
        };
        auto max_hp_of = [](const BattleState& s, int side) -> int32_t {
            const SideState& sd = (side == 0) ? s.side0 : s.side1;
            const PokemonState& m = sd.team[sd.active_indices[0]];
            return m.max_hp;
        };

        for (int side = 0; side < 2; ++side) {
            int32_t hp_before = hp_of(state, side);
            int32_t hp_after  = hp_of(state_copy, side);
            int32_t max_hp    = max_hp_of(state, side);
            int32_t actual_damage = hp_before - hp_after;
            int32_t expected = expected_damage[side];

            // Skip strict comparison when the target fainted (damage was capped by HP).
            if (hp_after <= 0) continue;
            // Skip when max_hp cap applies (heal past max — unlikely for damage but possible
            // for a defensive equivalence).
            if (hp_after >= max_hp && actual_damage < 0) continue;

            if (actual_damage != expected) {
                throw std::runtime_error(
                    "TransitionOracle::replay_path: shift-property violation on side "
                    + std::to_string(side)
                    + " — expected damage from prefix DAMAGE_ROLL entries = "
                    + std::to_string(expected)
                    + " but observed HP delta = " + std::to_string(actual_damage)
                    + " (hp " + std::to_string(hp_before) + " -> " + std::to_string(hp_after)
                    + "). This indicates an unaccounted HP-changing effect (berry heal, "
                    "recoil, residual) that fires only at the replay state — the DFS-captured "
                    "prefix does not describe the replay state's semantics.");
            }
        }
    }

    ReplayResult rr;
    rr.child             = state_copy;
    rr.observed_sequence = std::move(observed);
    return rr;
}

// ---------------------------------------------------------------------------
// TransitionOracle::step
// ---------------------------------------------------------------------------

StepStats TransitionOracle::step(const BattleState& state,
                                  const ExecAction& player_action,
                                  const OracleEmitFn& emit,
                                  OrderingHint hint,
                                  const Config& cfg) const {
    check_preconditions(state, player_action);

    // Determine AI side index: in 1v1 phase 1, player is side0, AI is side1.
    int ai_idx = 1;

    // Outer branch: AI action distribution
    std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(state, ai_idx);

    if (ai_probs.empty())
        throw std::runtime_error("TransitionOracle: AI action distribution is empty");

    {
        double ai_sum = 0.0;
        for (const auto& ap : ai_probs) ai_sum += ap.prob;
        if (std::abs(ai_sum - 1.0) > 1e-9)
            throw std::runtime_error(
                "TransitionOracle: AI action probs don't sum to 1 (sum="
                + std::to_string(ai_sum) + ")");
    }

    StepStats stats;

    // Build shared (deterministic) luck structs: no random_mode, no rng
    DamageLoopLuck luck_p0{};
    DamageLoopLuck luck_p1{};
    TurnLuck tl0{};
    TurnLuck tl1{};

    for (const auto& ap : ai_probs) {
        if (stats.aborted || stats.budget_exceeded) break;

        // Zero-probability AI actions contribute nothing to the child distribution
        // and can never be sampled — skip the entire subtree.
        if (ap.prob == 0.0) continue;

        // Pass pointer to the Config's debug_emit (stable for duration of step()).
        const LeafDebugFn* dbg = cfg.debug_emit ? &cfg.debug_emit : nullptr;
        DFSState ds{
            state, player_action, ap.action, ap.prob,
            emit, dbg, hint, cfg.max_leaves,
            cfg.aggregate_damage_rolls,
            cfg.collapse,
            0, 0, false, false,
            CategoryBOccurrenceCounters{},
            AnalyticalRngLog{},
            luck_p0, luck_p1, tl0, tl1
        };

        std::vector<PrefixEntry> prefix;
        dfs(ds, prefix, 0, 0);

        stats.leaves          += ds.leaves;
        stats.turn_executions += ds.turn_execs;
        if (ds.aborted)          stats.aborted = true;
        if (ds.budget_exceeded)  stats.budget_exceeded = true;
    }

    // Clean up global state (should already be null from dfs, but be safe)
    set_catb_injection(nullptr);
    set_catb_occ_counters(nullptr);
    set_analytical_rng_log(nullptr);

    return stats;
}
