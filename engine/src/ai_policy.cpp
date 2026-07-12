// C1.7i Stage 4+6: real AI scoring sampler and AIPolicy implementation.
// cpp_score_ai_actions: mirrors Python _score_ai_actions (stochastic, one roll per move).
// AIPolicy::select: mirrors Python select_ai_action (max-score tie-break, 50% switch gate).
// AIPolicy::select_switch: deterministic post-KO/forced-pivot scorer (cpp_select_post_ko_switch).
// AIPolicy::select_phaze: uniform-random game-mechanic draw over bench candidates.
#include "ai_policy.h"
#include "ai_scorer.h"
#include "ai_scorer_internal.h"  // exception_move_sees_kill, namespace ai_scorer
#include "ai_damage.h"
#include "ai_shared.h"
#include "orchestrate.h"  // cpp_enumerate_legal_actions
#include <algorithm>
#include <stdexcept>

// ---------------------------------------------------------------------------
// Local constants
// ---------------------------------------------------------------------------

static constexpr int32_t AK_MOVE   = 0;
static constexpr int32_t AK_SWITCH = 1;
static constexpr int32_t FMT_DOUBLES = 1;

// ---------------------------------------------------------------------------
// _sample_highest_slots: mirrors Python _sample_highest_slots.
// Draws one roll per move [0,15]; raw = roll_arrays[i][roll]; capped = min(raw, hp).
// highest_slots: move slots where capped == max(capped).
// kill_slots: move slots where raw >= hp.
// ---------------------------------------------------------------------------
static void sample_highest_slots(
    const std::vector<int32_t>& slots,
    const std::vector<std::array<int32_t, 16>>& roll_arrays,
    int32_t hp,
    std::mt19937_64& rng,
    std::set<int32_t>& highest_slots,
    std::set<int32_t>& kill_slots)
{
    highest_slots.clear();
    kill_slots.clear();
    if (roll_arrays.empty()) return;

    std::uniform_int_distribution<int> roll_dist(0, 15);
    int m = (int)slots.size();

    std::vector<int32_t> raw(m), capped(m);
    for (int i = 0; i < m; ++i) {
        int roll = roll_dist(rng);
        raw[i]    = roll_arrays[i][roll];
        capped[i] = std::min(raw[i], hp);
    }

    int32_t best = *std::max_element(capped.begin(), capped.end());
    for (int i = 0; i < m; ++i) {
        if (capped[i] == best) highest_slots.insert(slots[i]);
        if (raw[i] >= hp)     kill_slots.insert(slots[i]);
    }
}

// ---------------------------------------------------------------------------
// _sample_score: mirrors Python _sample_score.
// Switch actions always score 0. Damaging/status moves draw from cpp_dist_action
// via cumulative-sum pick using a [0,1) uniform draw.
// ---------------------------------------------------------------------------
static int sample_score(
    const BattleState& state, int ai_idx, const ExecAction& action,
    bool is_highest, bool kills, bool ai_fst, bool sees_kill,
    std::mt19937_64& rng)
{
    if (action.kind == AK_SWITCH) return 0;

    ScoreDistC dist = cpp_dist_action(state, ai_idx, action,
                                      is_highest ? 1.0 : 0.0, kills, ai_fst, sees_kill);
    if (dist.empty()) return 0;

    std::uniform_real_distribution<double> real_dist(0.0, 1.0);
    double r = real_dist(rng);
    double cumulative = 0.0;
    for (const auto& [score, prob] : dist) {
        cumulative += prob;
        if (r < cumulative) return score;
    }
    return dist.back().first;
}

// ---------------------------------------------------------------------------
// cpp_score_ai_actions: full stochastic sampler (mirrors Python _score_ai_actions).
// No mega filter because ExecAction has no mega field and cpp_enumerate_legal_actions
// never emits mega variants. Doubles expansion requires format == DOUBLES.
// ---------------------------------------------------------------------------
AIScoreResult cpp_score_ai_actions(const BattleState& state, int ai_idx, std::mt19937_64& rng) {
    AIScoreResult result;

    std::vector<ExecAction> actions = cpp_enumerate_legal_actions(state, ai_idx, 0);
    if (actions.empty()) return result;

    bool ai_fst = cpp_ai_faster(state, ai_idx);

    // Build damage context from original actions (before doubles expansion).
    DamageContext ctx = cpp_build_damage_context(state, ai_idx, actions);

    const SideState& pl_side_ref = (ai_idx == 0) ? state.side1 : state.side0;
    int32_t pl_hp = pl_side_ref.team[pl_side_ref.active_indices[0]].hp;

    std::set<int32_t> highest_slots, kill_slots;
    sample_highest_slots(ctx.slots, ctx.roll_arrays, pl_hp, rng, highest_slots, kill_slots);

    // Compute once per turn: does any exception move (trapping/Future Sight) see a kill?
    bool exc = ai_scorer::exception_move_sees_kill(state, ai_idx);

    // Doubles expansion: append target_slot=1 copies of damaging MOVE actions.
    if (state.format == FMT_DOUBLES && pl_side_ref.active_indices.size() >= 2) {
        std::vector<ExecAction> extra;
        const PokemonState& ai_mon = active_mon(state, ai_idx);
        for (const ExecAction& a : actions) {
            if (a.kind != AK_MOVE || a.move_slot < 0 || a.target_slot != 0) continue;
            int32_t move_id = move_id_at(ai_mon, a.move_slot);
            const MoveData* mdp = ai_move_data_get(move_id);
            if (mdp == nullptr || !(mdp->tags & TAG_DAMAGE)) continue;
            ExecAction dup = a;
            dup.target_slot = 1;
            extra.push_back(dup);
        }
        for (const ExecAction& e : extra) actions.push_back(e);
    }

    // Separate move vs switch actions for switch-target logic.
    std::vector<const ExecAction*> move_actions, switch_actions;
    for (const ExecAction& a : actions) {
        if (a.kind == AK_MOVE)   move_actions.push_back(&a);
        else                      switch_actions.push_back(&a);
    }

    // Score each action.
    std::vector<int> scores;
    scores.reserve(actions.size());
    for (const ExecAction& action : actions) {
        bool is_highest = (action.kind == AK_MOVE && highest_slots.count(action.move_slot) > 0);
        bool roll_kills = (action.kind == AK_MOVE && kill_slots.count(action.move_slot) > 0);
        bool kills      = is_highest && roll_kills;
        bool sees_kill  = exc || !kill_slots.empty();
        scores.push_back(sample_score(state, ai_idx, action, is_highest, kills, ai_fst, sees_kill, rng));
    }

    result.actions = std::move(actions);
    result.scores  = std::move(scores);

    // Switch-target condition: switch_actions non-empty, move_actions non-empty,
    // not doubles, AI HP >= 50%, all move scores <= +5, valid cond2 candidate.
    if (!switch_actions.empty() && !move_actions.empty()
            && state.format != FMT_DOUBLES) {
        const PokemonState& ai_mon_ref = active_mon(state, ai_idx);
        double hp_pct = (double)ai_mon_ref.hp / ai_mon_ref.max_hp;
        if (hp_pct >= 0.5) {
            // Collect move scores (parallel to result.actions).
            bool all_low = true;
            for (size_t i = 0; i < result.actions.size(); ++i) {
                if (result.actions[i].kind == AK_MOVE && result.scores[i] > 5) {
                    all_low = false;
                    break;
                }
            }
            if (all_low && cpp_has_valid_switch_candidate(state, ai_idx)) {
                int best_slot = cpp_select_voluntary_switch_target(state, ai_idx);
                // Find the switch action with switch_to_slot == best_slot; fallback first.
                const ExecAction* chosen = switch_actions[0];
                for (const ExecAction* sa : switch_actions) {
                    if (sa->switch_to_slot == best_slot) { chosen = sa; break; }
                }
                result.switch_target = *chosen;
            }
        }
    }

    return result;
}

// ---------------------------------------------------------------------------
// AIPolicy::select: mirrors Python select_ai_action.
// ---------------------------------------------------------------------------

AIPolicy::AIPolicy(uint64_t seed) : rng_(seed) {}

ExecAction AIPolicy::select(const std::vector<ExecAction>& /*legal*/,
                             const BattleState& state, int side_idx) {
    AIScoreResult res = cpp_score_ai_actions(state, side_idx, rng_);
    if (res.actions.empty())
        throw std::runtime_error("AIPolicy: no legal actions");

    // 50% gate: return switch_target if set.
    if (res.switch_target.has_value()) {
        std::uniform_real_distribution<double> gate(0.0, 1.0);
        if (gate(rng_) < 0.5) return *res.switch_target;
    }

    // Tie-break over MOVE actions only — switches are only reachable via the gate above.
    std::vector<size_t> move_indices;
    for (size_t i = 0; i < res.actions.size(); ++i)
        if (res.actions[i].kind == AK_MOVE) move_indices.push_back(i);
    if (move_indices.empty())
        throw std::runtime_error("AIPolicy::select: no move actions available (Struggle must always exist)");

    int max_score = res.scores[move_indices[0]];
    for (size_t idx : move_indices)
        if (res.scores[idx] > max_score) max_score = res.scores[idx];

    std::vector<const ExecAction*> winners;
    for (size_t idx : move_indices)
        if (res.scores[idx] == max_score) winners.push_back(&res.actions[idx]);

    std::uniform_int_distribution<size_t> pick(0, winners.size() - 1);
    return *winners[pick(rng_)];
}

ExecAction AIPolicy::select_switch(const std::vector<ExecAction>& candidates,
                                    const BattleState& state, int side_idx, SwitchCtx /*ctx*/) {
    // Deterministic scorer picks the best bench slot; find the matching candidate action.
    int best_slot = cpp_select_post_ko_switch(state, side_idx);
    for (const ExecAction& c : candidates)
        if (c.switch_to_slot == best_slot) return c;
    // No match is a scoring/routing bug — fail loudly rather than silently falling back.
    throw std::runtime_error(
        "AIPolicy::select_switch: no candidate matches cpp_select_post_ko_switch result "
        "(slot " + std::to_string(best_slot) + ")");
}

ExecAction AIPolicy::select_phaze(const std::vector<ExecAction>& bench,
                                   const BattleState& /*state*/, int /*side_idx*/) {
    // Uniform draw: phazing is a game-mechanic oracle, not an agent decision.
    if (bench.empty()) throw std::runtime_error("AIPolicy::select_phaze: empty bench");
    std::uniform_int_distribution<size_t> dist(0, bench.size() - 1);
    return bench[dist(rng_)];
}
