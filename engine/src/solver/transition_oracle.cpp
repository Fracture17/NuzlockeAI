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
static std::vector<std::pair<int,double>> expand_catb_options(const AnalyticalRngEntry& entry) {
    using E = RngEventC;
    auto ev = static_cast<E>(entry.event);

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
        // Boolean: chosen either 0 or 1; complement is sibling.
        // Use p_chosen for the logged chosen value; compute complement.
        // For robustness we return both options using the re-run approach described in the spec.
        // Since we know p_chosen from the log, we derive the sibling as 1-p_chosen.
        // We must identify which option was chosen.
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
        // 16 options [0..15], each p=1/16
        // options_count may report 16 or 15 (confusion self-hit) from options field
        // Use options_count to determine which variant
        int count = static_cast<int>(entry.options_count);
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

    // For any other Cat-B event with n options: read from p_chosen + complement pattern.
    // This handles any new events not explicitly covered above.
    // Use uniform if all have equal probability; otherwise use p_chosen for the chosen option
    // and distribute the remainder uniformly over other options.
    // This is the "structure-derived" approach for unknown events.
    {
        double uniform_p = 1.0 / static_cast<double>(n);
        double eps = 1e-12;
        bool looks_uniform = (std::abs(entry.p_chosen - uniform_p) < eps);
        std::vector<std::pair<int,double>> opts;
        if (looks_uniform) {
            for (size_t i = 0; i < n; ++i)
                opts.push_back({entry.options[i], uniform_p});
        } else {
            // p_chosen for chosen option; divide remainder over others
            double p_other = (1.0 - entry.p_chosen) / static_cast<double>(n - 1);
            for (size_t i = 0; i < n; ++i) {
                double p = (entry.options[i] == entry.chosen) ? entry.p_chosen : p_other;
                opts.push_back({entry.options[i], p});
            }
        }
        return opts;
    }
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

        // Debug callback (null-guarded; zero cost on hot path).
        if (ds.debug_emit && *ds.debug_emit) {
            LeafDebugInfo dbg;
            dbg.cumulative_prob = leaf_prob;
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

    // Expand options for this branch
    std::vector<std::pair<int,double>> branch_opts = expand_catb_options(branch_entry);

    // Sanity: branch option probabilities must sum to 1±1e-9
    {
        double s = 0.0;
        for (const auto& kv : branch_opts) s += kv.second;
        if (std::abs(s - 1.0) > 1e-9)
            throw std::runtime_error(
                "TransitionOracle: Cat-B branch probs don't sum to 1 for event "
                + std::to_string(branch_event) + " (sum=" + std::to_string(s) + ")");
    }

    // AdverseFirst ordering: sort options to put player-adverse outcomes first.
    // This is a best-effort heuristic; must not change the multiset.
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
        // Skip zero-probability branch values (defensive; contributes nothing).
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
