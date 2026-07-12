// Stage 5 AI analytic probability computation.
// Ports _iter_damage_configs, compute_action_probabilities, possible_ai_actions from src/ai.py.
// Critical invariant: cartesian product iterates LAST dimension fastest (mirrors itertools.product).
#include "ai_analytic.h"
#include "ai_scorer.h"
#include "ai_scorer_internal.h"  // exception_move_sees_kill, namespace ai_scorer
#include "ai_damage.h"
#include "ai_shared.h"
#include "orchestrate.h"

#include <algorithm>
#include <stdexcept>
#include <unordered_map>
#include <cmath>

// ---------------------------------------------------------------------------
// Local constants
// ---------------------------------------------------------------------------

static constexpr int32_t AK_MOVE   = 0;
static constexpr int32_t AK_SWITCH = 1;
static constexpr int32_t FMT_DOUBLES = 1;

// ---------------------------------------------------------------------------
// cpp_iter_damage_configs
// Mirrors Python _iter_damage_configs exactly (O(levels * 2^m)).
// ---------------------------------------------------------------------------

std::vector<DamageConfig> cpp_iter_damage_configs(
    const std::vector<std::array<int32_t, 16>>& dm_rolls, int32_t hp)
{
    int m = (int)dm_rolls.size();
    std::vector<DamageConfig> result;
    if (m == 0) return result;

    // Capped roll arrays and per-level counts.
    // eq_counts[j][v] = count of rolls of move j capped to v.
    std::vector<std::unordered_map<int32_t, int32_t>> eq_counts(m);
    for (int j = 0; j < m; ++j) {
        for (int32_t raw : dm_rolls[j]) {
            int32_t v = std::min(raw, hp);
            eq_counts[j][v]++;
        }
    }

    // Collect all unique capped levels, descending.
    std::vector<int32_t> levels;
    {
        std::unordered_map<int32_t, bool> seen;
        for (int j = 0; j < m; ++j)
            for (auto& [v, _] : eq_counts[j])
                seen[v] = true;
        for (auto& [v, _] : seen)
            levels.push_back(v);
    }
    std::sort(levels.begin(), levels.end(), std::greater<int32_t>());

    for (int32_t v : levels) {
        bool kill_flag = (v == hp);

        // p_eq[j] = count_eq/16.0, p_lt[j] = sum(count where val<v)/16.0
        std::vector<double> p_eq(m, 0.0), p_lt(m, 0.0);
        for (int j = 0; j < m; ++j) {
            auto it = eq_counts[j].find(v);
            if (it != eq_counts[j].end())
                p_eq[j] = it->second / 16.0;
            // sum counts for values strictly less than v
            int32_t lt_count = 0;
            for (auto& [val, cnt] : eq_counts[j])
                if (val < v) lt_count += cnt;
            p_lt[j] = lt_count / 16.0;
        }

        // group = moves where p_eq[j] > 0, ascending order
        std::vector<int> group;
        for (int j = 0; j < m; ++j)
            if (p_eq[j] > 0.0) group.push_back(j);
        int n_g = (int)group.size();

        // Non-empty subsets H of group (masks 1..(1<<n_g)-1), ascending
        for (int mask = 1; mask < (1 << n_g); ++mask) {
            // Build in_h: true for moves in this subset H
            std::vector<char> in_h(m, 0);
            for (int k = 0; k < n_g; ++k)
                if (mask & (1 << k)) in_h[group[k]] = 1;

            // w = product: p_eq[j] if in_h[j] else p_lt[j]
            double w = 1.0;
            for (int j = 0; j < m; ++j)
                w *= in_h[j] ? p_eq[j] : p_lt[j];

            if (w == 0.0) continue;  // exact zero check, not epsilon

            std::vector<char> kills(m, 0);
            for (int j = 0; j < m; ++j)
                kills[j] = (in_h[j] && kill_flag) ? 1 : 0;

            result.push_back({w, std::move(in_h), std::move(kills)});
        }
    }
    return result;
}

// ---------------------------------------------------------------------------
// _max_possible_move_score: helper for all_ineffective gate.
// Mirrors Python _max_possible_move_score (ai.py 1364-1371).
// ---------------------------------------------------------------------------

static int32_t max_possible_move_score(
    const BattleState& state, int ai_idx, const ExecAction& action,
    bool in_damage_ctx, double p_k, double p_nk, bool ai_fst)
{
    // sees_kill=false throughout: gate-neutral because unblocked sleep/toxic base
    // is already 6 (>5), and blocked variants are negative in both sees_kill variants.
    if (in_damage_ctx) {
        // max over three cases: highest+kill, highest+nokill, not-highest
        int32_t s_hk = -999, s_hnk = -999;
        if (p_k > 0.0) {
            ScoreDistC d = cpp_dist_action(state, ai_idx, action, 1.0, true, ai_fst, false);
            for (auto& [s, _] : d) s_hk = std::max(s_hk, s);
        }
        if (p_nk > 0.0) {
            ScoreDistC d = cpp_dist_action(state, ai_idx, action, 1.0, false, ai_fst, false);
            for (auto& [s, _] : d) s_hnk = std::max(s_hnk, s);
        }
        // always compute s_none
        int32_t s_none = -999;
        {
            ScoreDistC d = cpp_dist_action(state, ai_idx, action, 0.0, false, ai_fst, false);
            for (auto& [s, _] : d) s_none = std::max(s_none, s);
        }
        return std::max({s_hk, s_hnk, s_none});
    } else {
        // non-damaging: use dist at p_highest=0, kills=false
        ScoreDistC d = cpp_dist_action(state, ai_idx, action, 0.0, false, ai_fst, false);
        int32_t best = -999;
        for (auto& [s, _] : d) best = std::max(best, s);
        return best;
    }
}

// ---------------------------------------------------------------------------
// _accumulate_with_other: inner product loop.
// Enumerates itertools.product(*all_dists_seq) with LAST dimension fastest.
// dm_fixed_dists: index i (into actions) -> ScoreDistC for damaging moves.
// other_dists: index i (into actions) -> ScoreDistC for non-damaging moves.
// all_indices: dm_fixed keys (in insertion order) then other_dists keys.
// Matches Python exactly: combo_prob starts at roll_weight, multiplied per pair.
// ---------------------------------------------------------------------------

static void accumulate_with_other(
    double roll_weight,
    const std::vector<int>& dm_indices,      // action indices for damaging moves
    const std::vector<ScoreDistC>& dm_dists, // parallel to dm_indices
    const std::vector<int>& other_indices,   // action indices for other moves
    const std::vector<ScoreDistC>& other_dists,
    std::vector<double>& probs)
{
    // all_indices = dm_indices ++ other_indices (Python dict insertion order)
    // all_dists_seq = dm_dists ++ other_dists
    int n_dm    = (int)dm_indices.size();
    int n_other = (int)other_indices.size();
    int n_total = n_dm + n_other;

    // Sizes of each distribution
    std::vector<int> sizes(n_total);
    for (int k = 0; k < n_dm;    ++k) sizes[k]        = (int)dm_dists[k].size();
    for (int k = 0; k < n_other; ++k) sizes[n_dm + k] = (int)other_dists[k].size();

    // Total number of combos
    int64_t n_combos = 1;
    for (int k = 0; k < n_total; ++k) {
        if (sizes[k] == 0) return;  // empty dist => no valid combos
        n_combos *= sizes[k];
    }

    // Iterate combos with indices array; LAST dimension fastest (rightmost increments first).
    std::vector<int> idx(n_total, 0);

    for (int64_t combo_num = 0; combo_num < n_combos; ++combo_num) {
        // Compute combo_prob = roll_weight * product(p for each slot's chosen pair)
        double combo_prob = roll_weight;
        for (int k = 0; k < n_total; ++k) {
            double p;
            if (k < n_dm)
                p = dm_dists[k][idx[k]].second;
            else
                p = other_dists[k - n_dm][idx[k]].second;
            combo_prob *= p;
            if (combo_prob == 0.0) goto next_combo;  // exact zero skip
        }
        {
            // Find max score and winners; accumulate into probs in ascending all_indices position order
            int32_t max_score = INT32_MIN;
            for (int k = 0; k < n_total; ++k) {
                int32_t s;
                if (k < n_dm)
                    s = dm_dists[k][idx[k]].first;
                else
                    s = other_dists[k - n_dm][idx[k]].first;
                if (s > max_score) max_score = s;
            }

            std::vector<int> winners;
            winners.reserve(n_total);
            for (int k = 0; k < n_total; ++k) {
                int32_t s;
                if (k < n_dm)
                    s = dm_dists[k][idx[k]].first;
                else
                    s = other_dists[k - n_dm][idx[k]].first;
                if (s == max_score) {
                    // push actual action index
                    winners.push_back(k < n_dm ? dm_indices[k] : other_indices[k - n_dm]);
                }
            }

            double share = combo_prob / (double)winners.size();
            for (int action_idx : winners)
                probs[action_idx] += share;
        }
        next_combo:;

        // Advance indices: increment last dimension first (rightmost fastest)
        for (int k = n_total - 1; k >= 0; --k) {
            idx[k]++;
            if (idx[k] < sizes[k]) break;
            idx[k] = 0;
        }
    }
}

// ---------------------------------------------------------------------------
// cpp_compute_action_probabilities
// Mirrors Python compute_action_probabilities (ai.py 1323-1467).
// ---------------------------------------------------------------------------

std::vector<ActionProb> cpp_compute_action_probabilities(
    const BattleState& state, int ai_idx)
{
    std::vector<ExecAction> actions = cpp_enumerate_legal_actions(state, ai_idx, 0);
    if (actions.empty()) return {};

    bool ai_fst = cpp_ai_faster(state, ai_idx);

    DamageContext ctx = cpp_build_damage_context(state, ai_idx, actions);

    const SideState& pl_side = (ai_idx == 0) ? state.side1 : state.side0;
    int32_t pl_hp = pl_side.team[pl_side.active_indices[0]].hp;

    // split_by_slot: move_slot -> (p_kill, p_nokill)
    std::unordered_map<int32_t, std::pair<double, double>> split_by_slot;
    if (!ctx.roll_arrays.empty()) {
        auto split_probs = cpp_compute_highest_damage_probs(ctx.roll_arrays, pl_hp);
        for (int i = 0; i < (int)ctx.slots.size(); ++i)
            split_by_slot[ctx.slots[i]] = split_probs[i];
    }

    // Separate move vs switch actions (with original indices into actions vector)
    std::vector<std::pair<int, const ExecAction*>> move_actions, switch_actions;
    for (int i = 0; i < (int)actions.size(); ++i) {
        if (actions[i].kind == AK_MOVE)
            move_actions.push_back({i, &actions[i]});
        else
            switch_actions.push_back({i, &actions[i]});
    }

    const PokemonState& ai_mon = active_mon(state, ai_idx);

    // Partition move actions into damaging (in split_by_slot) and non-damaging
    std::vector<std::pair<int, const ExecAction*>> damaging_moves, other_moves;
    for (auto& [i, a] : move_actions) {
        if (split_by_slot.count(a->move_slot))
            damaging_moves.push_back({i, a});
        else
            other_moves.push_back({i, a});
    }

    // Compute exception-move kill flag once per turn.
    bool exc = ai_scorer::exception_move_sees_kill(state, ai_idx);

    // Build fixed dists for non-damaging move actions in both sees_kill variants.
    // Two parallel vectors: [0]=sees_kill=false, [1]=sees_kill=true.
    // Damaging dists ignore sees_kill (sleep/toxic are STATUS moves, never reach
    // dist_damage), so the get_dist cache key stays valid using sees_kill=false.
    std::vector<int> other_indices;
    std::vector<ScoreDistC> other_dists_false_vec;  // sees_kill=false
    std::vector<ScoreDistC> other_dists_true_vec;   // sees_kill=true
    for (auto& [i, a] : other_moves) {
        other_indices.push_back(i);
        other_dists_false_vec.push_back(cpp_dist_action(state, ai_idx, *a, 0.0, false, ai_fst, false));
        other_dists_true_vec.push_back(cpp_dist_action(state, ai_idx, *a, 0.0, false, ai_fst, true));
    }

    // Determine all_ineffective gate
    bool all_ineffective = false;
    if (!move_actions.empty() && !switch_actions.empty()
        && state.format != FMT_DOUBLES
        && (double)ai_mon.hp / ai_mon.max_hp >= 0.5
        && cpp_has_valid_switch_candidate(state, ai_idx))
    {
        // Check max possible score for every move action
        bool all_low = true;
        for (auto& [i, a] : move_actions) {
            bool in_ctx = split_by_slot.count(a->move_slot) > 0;
            double p_k = 0.0, p_nk = 0.0;
            if (in_ctx) {
                auto& [pk, pnk] = split_by_slot[a->move_slot];
                p_k = pk; p_nk = pnk;
            }
            int32_t max_s = max_possible_move_score(state, ai_idx, *a, in_ctx, p_k, p_nk, ai_fst);
            if (max_s > 5) { all_low = false; break; }
        }
        all_ineffective = all_low;
    }

    // Accumulate probs
    std::vector<double> probs(actions.size(), 0.0);

    if (damaging_moves.empty()) {
        // No damaging moves: no kill_slots possible, so sees_kill = exc alone.
        const std::vector<ScoreDistC>& other_dists_vec =
            exc ? other_dists_true_vec : other_dists_false_vec;
        accumulate_with_other(1.0,
            {}, {},
            other_indices, other_dists_vec,
            probs);
    } else {
        int m = (int)damaging_moves.size();
        std::vector<int> dm_indices_vec;
        std::vector<const ExecAction*> dm_actions;
        for (auto& [i, a] : damaging_moves) {
            dm_indices_vec.push_back(i);
            dm_actions.push_back(a);
        }

        // dm_rolls[j] = roll_arrays[first index in ctx.slots equal to dm_actions[j]->move_slot]
        std::vector<std::array<int32_t, 16>> dm_rolls(m);
        for (int j = 0; j < m; ++j) {
            int32_t ms = dm_actions[j]->move_slot;
            // find first index in ctx.slots equal to ms
            int slot_idx = -1;
            for (int si = 0; si < (int)ctx.slots.size(); ++si) {
                if (ctx.slots[si] == ms) { slot_idx = si; break; }
            }
            if (slot_idx < 0)
                throw std::runtime_error("ai_analytic: move_slot not in ctx.slots");
            dm_rolls[j] = ctx.roll_arrays[slot_idx];
        }

        // Cache: (j, is_highest, kills) -> ScoreDistC
        // key: j * 4 + (is_highest ? 2 : 0) + (kills ? 1 : 0)
        std::unordered_map<int, ScoreDistC> dist_cache;

        // Damaging dists: sees_kill=false — damaging moves never reach dist_poison /
        // dist_status_special, so the flag has no effect; cache key remains valid.
        auto get_dist = [&](int j, bool is_highest, bool kills) -> const ScoreDistC& {
            int cache_key = j * 4 + (is_highest ? 2 : 0) + (kills ? 1 : 0);
            auto it = dist_cache.find(cache_key);
            if (it != dist_cache.end()) return it->second;
            double p_h = is_highest ? 1.0 : 0.0;
            dist_cache[cache_key] = cpp_dist_action(
                state, ai_idx, *dm_actions[j], p_h, kills, ai_fst, false);
            return dist_cache[cache_key];
        };

        // Enumerate damage configs
        std::vector<DamageConfig> configs = cpp_iter_damage_configs(dm_rolls, pl_hp);

        for (const DamageConfig& cfg : configs) {
            // Build dm_dists parallel to dm_indices_vec
            std::vector<ScoreDistC> dm_dists(m);
            bool any_kill = false;
            for (int j = 0; j < m; ++j) {
                bool ih = (bool)cfg.is_highest[j];
                bool kl = (bool)cfg.kills[j];
                dm_dists[j] = get_dist(j, ih, kl);
                if (kl) any_kill = true;
            }

            bool cfg_sees_kill = exc || any_kill;
            const std::vector<ScoreDistC>& other_dists_vec =
                cfg_sees_kill ? other_dists_true_vec : other_dists_false_vec;

            accumulate_with_other(cfg.weight,
                dm_indices_vec, dm_dists,
                other_indices, other_dists_vec,
                probs);
        }
    }

    // Apply all_ineffective scaling
    std::vector<ActionProb> result;
    result.reserve(actions.size());

    if (all_ineffective && !switch_actions.empty()) {
        int target_slot = cpp_select_voluntary_switch_target(state, ai_idx);
        // Find the switch action with switch_to_slot == target_slot; fallback to switch_actions[0]
        const ExecAction* target_action = switch_actions[0].second;
        for (auto& [i, a] : switch_actions) {
            if (a->switch_to_slot == target_slot) { target_action = a; break; }
        }

        for (int i = 0; i < (int)actions.size(); ++i) {
            const ExecAction& a = actions[i];
            if (a.kind == AK_SWITCH) {
                // Compare all 6 ExecAction fields
                bool is_target = (a.kind == target_action->kind
                    && a.move_slot == target_action->move_slot
                    && a.move_override == target_action->move_override
                    && a.switch_to_slot == target_action->switch_to_slot
                    && a.target_side == target_action->target_side
                    && a.target_slot == target_action->target_slot);
                result.push_back({a, is_target ? 0.5 : 0.0});
            } else {
                result.push_back({a, probs[i] * 0.5});
            }
        }
    } else {
        for (int i = 0; i < (int)actions.size(); ++i)
            result.push_back({actions[i], probs[i]});
    }

    // Doubles expansion: if format==DOUBLES and opponent has >=2 active, expand damaging moves
    if (state.format == FMT_DOUBLES) {
        const SideState& opp_side = (ai_idx == 0) ? state.side1 : state.side0;
        if ((int)opp_side.active_indices.size() >= 2) {
            const PokemonState& ai_mon_ref = active_mon(state, ai_idx);
            std::vector<ActionProb> expanded;
            expanded.reserve(result.size() * 2);

            for (const ActionProb& ap : result) {
                const ExecAction& a = ap.action;
                if (a.kind == AK_MOVE && a.move_slot >= 0 && a.target_slot == 0) {
                    int32_t move_id = move_id_at(ai_mon_ref, a.move_slot);
                    const MoveData* mdp = ai_move_data_get(move_id);
                    if (mdp != nullptr && (mdp->tags & TAG_DAMAGE)) {
                        // Push original (target_slot=0) then clone (target_slot=1)
                        expanded.push_back({a, ap.prob * 0.5});
                        ExecAction clone = a;
                        clone.target_slot = 1;
                        expanded.push_back({clone, ap.prob * 0.5});
                        continue;
                    }
                }
                expanded.push_back(ap);
            }
            result = std::move(expanded);
        }
    }

    return result;
}

// ---------------------------------------------------------------------------
// cpp_possible_ai_actions: analytic support (p>0) of cpp_compute_action_probabilities.
// ---------------------------------------------------------------------------

std::vector<ExecAction> cpp_possible_ai_actions(
    const BattleState& state, int ai_idx)
{
    auto dist = cpp_compute_action_probabilities(state, ai_idx);
    std::vector<ExecAction> result;
    for (const ActionProb& ap : dist)
        if (ap.prob > 0.0) result.push_back(ap.action);
    return result;
}
