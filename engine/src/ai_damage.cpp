// Stage 1 AI damage machinery implementation.
// Ports: queries.py (expected_damage, damage_roll_values), ai.py (_fixed_damage_rolls,
// _ai_assumed_hit_count, _build_damage_context, _compute_highest_damage_probs).
// Delegates to cpp_calculate_damage; never mutates state.
#include "ai_damage.h"
#include "ai_shared.h"
#include "damage.h"
#include "type_chart_lookup.h"
#include "core_leaf.h"
#include "orchestrate.h"        // cpp_enumerate_legal_actions
#include "../generated/move_data.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <unordered_map>

// resolve_multi_hit: mirrors move_exec_damage anonymous-namespace version.
// random_mode draws from rng (rng must be non-null); deterministic uses multi_hit_roll.
static int32_t ai_resolve_multi_hit(int min_hits, int max_hits, const LuckProfileC& luck) {
    if (min_hits == max_hits) return min_hits;
    if (luck.random_mode) {
        if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (min_hits == 2 && max_hits == 5) {
            // Python: choices([2,3,4,5], weights=[35,35,15,15])
            return luck.rng->choices({2, 3, 4, 5}, {35, 35, 15, 15});
        }
        return luck.rng->randint(min_hits, max_hits);
    }
    double multi_hit_roll = luck.multi_hit_roll;
    if (min_hits == 2 && max_hits == 5) {
        if (multi_hit_roll < 0.35) return 2;
        if (multi_hit_roll < 0.70) return 3;
        if (multi_hit_roll < 0.85) return 4;
        return 5;
    }
    int span = max_hits - min_hits;
    return (int)std::floor(min_hits + multi_hit_roll * span + 0.5);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

// Find which side (0 or 1) owns the given PokemonState by address. Throws if not found.
static int side_index_of(const PokemonState& mon, const BattleState& state) {
    for (const PokemonState& m : state.side0.team) {
        if (&m == &mon) return 0;
    }
    for (const PokemonState& m : state.side1.team) {
        if (&m == &mon) return 1;
    }
    throw std::runtime_error("ai_damage: attacker not found on either side");
}

// Mirrors Python _prev_turn_acted_first/second (damage.py:816-823).
static bool prev_turn_acted_first(const BattleState& state, int side_idx) {
    return state.prev_turn_order.size() >= 2 && state.prev_turn_order[0] == side_idx;
}
static bool prev_turn_acted_second(const BattleState& state, int side_idx) {
    return state.prev_turn_order.size() >= 2 && state.prev_turn_order[1] == side_idx;
}

// Build a DamageLoopLuck with the given damage_roll for use in resolve_hit_count.
// All other fields set to defaults (crit never, no random_mode).
static DamageLoopLuck make_max_damage_luck() {
    DamageLoopLuck d;
    d.crit_threshold = 100.0;   // never crit (mirrors _MAX_DAMAGE_LUCK = BAD_LUCK.crit_threshold=100)
    d.damage_roll    = 1.0;     // max damage roll
    d.proc_threshold = 101.0;
    d.secondary_threshold = 101.0;
    d.multi_hit_roll = 0.0;     // minimum hit count (matches BAD_LUCK multi_hit_roll=0)
    d.random_mode    = false;
    return d;
}

// ---------------------------------------------------------------------------
// cpp_fixed_damage_rolls
// ---------------------------------------------------------------------------

std::optional<std::array<int32_t, 16>> cpp_fixed_damage_rolls(
    int32_t move_id, const MoveData& md,
    const PokemonState& ai_mon, const PokemonState& pl_mon)
{
    if (!is_fixed_damage_rank_move(move_id))
        return std::nullopt;

    // Type immunity check: iterate all defender types, honor Ring Target.
    bool immune = false;
    for (int32_t def_type : pl_mon.types) {
        float eff = cpp_type_effectiveness((int32_t)md.move_type, def_type);
        if (eff == 0.0f && pl_mon.item != ITM_RING_TARGET) {
            immune = true;
            break;
        }
    }
    if (immune) {
        std::array<int32_t, 16> zeros;
        zeros.fill(0);
        return zeros;
    }

    std::array<int32_t, 16> rolls;

    if (move_id == MV_DRAGON_RAGE) {
        rolls.fill(40);
        return rolls;
    }
    if (move_id == MV_SONIC_BOOM) {
        rolls.fill(20);
        return rolls;
    }
    if (move_id == MV_SEISMIC_TOSS || move_id == MV_NIGHT_SHADE) {
        rolls.fill(ai_mon.level);
        return rolls;
    }
    if (move_id == MV_SUPER_FANG || move_id == MV_NATURE_S_MADNESS) {
        int32_t dmg = std::max(1, pl_mon.hp / 2);
        rolls.fill(dmg);
        return rolls;
    }
    // PSYWAVE: roll_int = 50 + round(i/15 * 100), then max(1, roll_int * level // 100).
    // round() is Python banker's rounding.
    for (int i = 0; i < 16; ++i) {
        int64_t roll_int = 50 + banker_round((double)i / 15.0 * 100.0);
        int64_t dmg64 = roll_int * (int64_t)ai_mon.level / 100LL;
        if (dmg64 < 1) dmg64 = 1;
        rolls[i] = (int32_t)dmg64;
    }
    return rolls;
}

// ---------------------------------------------------------------------------
// cpp_ai_assumed_hit_count
// ---------------------------------------------------------------------------

int32_t cpp_ai_assumed_hit_count(const PokemonState& atk, const MoveData& md) {
    if (md.max_hits <= 1) return 1;
    if (md.min_hits == md.max_hits) return md.max_hits;
    return (atk.ability == AB_SKILL_LINK) ? 5 : 3;
}

// ---------------------------------------------------------------------------
// cpp_expected_damage
// ---------------------------------------------------------------------------

int32_t cpp_expected_damage(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    int32_t roll_index, bool rollout_max_bp, int32_t hit_count_override)
{
    const MoveData& md = ai_move_data_or_throw(move_id);

    int32_t hit_count;
    bool parental_bond_active;
    if (hit_count_override >= 0) {
        hit_count = hit_count_override;
        parental_bond_active = false;
    } else {
        // multi_hit_roll: now carried in LuckProfileC (mirrors Python LuckProfile.multi_hit_roll).
        // Default 0.5 preserves AVERAGE_LUCK behavior; MAX_LUCK_C sets it to 0.0 (BAD_LUCK default).
        hit_count = ai_resolve_multi_hit(md.min_hits, md.max_hits, luck);
        // Skill Link overrides to max_hits for multi-hit moves.
        if (atk.ability == AB_SKILL_LINK && md.max_hits > 1)
            hit_count = md.max_hits;
        // Battle Bond Greninja: Water Shuriken always 3 hits.
        static constexpr int32_t AB_BATTLE_BOND = 210, SP_GRENINJA_ASH = 1113,
            MV_WATER_SHURIKEN_ID = 594;
        if (atk.ability == AB_BATTLE_BOND && atk.species == SP_GRENINJA_ASH
                && move_id == MV_WATER_SHURIKEN_ID)
            hit_count = 3;
        // Parental Bond: NORMAL(0), ANY(5), RANDOM_NORMAL(9) targets; single-hit only.
        static constexpr int32_t AB_PARENTAL_BOND = 185;
        parental_bond_active = (atk.ability == AB_PARENTAL_BOND && md.max_hits == 1
                                && (md.target == 0 || md.target == 5 || md.target == 9));
        if (parental_bond_active) hit_count = 2;
    }

    // AI Bug #8: order-dependent BP boosts judged by PREVIOUS turn's move order.
    int32_t order_bp_override = 0;
    int atk_side_idx = side_index_of(atk, state);
    int def_side_idx = side_index_of(def, state);
    if (move_id == MV_PAYBACK && prev_turn_acted_second(state, atk_side_idx)) {
        order_bp_override = PAYBACK_BOOSTED_BP;
    } else if ((move_id == MV_BOLT_BEAK || move_id == MV_FISHIOUS_REND)
               && prev_turn_acted_first(state, atk_side_idx)) {
        order_bp_override = FANG_MOVE_BOOSTED_BP;
    }

    int32_t total = 0;
    for (int hit_num = 0; hit_num < hit_count; ++hit_num) {
        int32_t bp_override;
        if (move_id == MV_TRIPLE_AXEL) {
            bp_override = TRIPLE_AXEL_BPS[hit_num];
        } else if (rollout_max_bp && move_id == MV_ROLLOUT) {
            bp_override = 480;
        } else {
            bp_override = order_bp_override;
        }

        int32_t dmg = cpp_calculate_damage(atk, move_id, def, state, luck, luck,
                                           bp_override, def_side_idx, /*spread_hit=*/true,
                                           roll_index, /*ai_scoring_view=*/true);
        if (parental_bond_active && hit_num == 1) {
            dmg = std::max(1, (int)(dmg * 0.25));
        }
        total += dmg;
    }
    return total;
}

// ---------------------------------------------------------------------------
// cpp_damage_roll_values
// ---------------------------------------------------------------------------

std::array<int32_t, 16> cpp_damage_roll_values(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    int32_t hit_count_override)
{
    std::array<int32_t, 16> result;
    for (int r = 0; r < 16; ++r) {
        result[r] = cpp_expected_damage(atk, move_id, def, state, luck,
                                        r, /*rollout_max_bp=*/false, hit_count_override);
    }
    return result;
}

// ---------------------------------------------------------------------------
// cpp_build_damage_context
// ---------------------------------------------------------------------------

DamageContext cpp_build_damage_context(
    const BattleState& state, int ai_idx,
    const std::vector<ExecAction>& actions)
{
    DamageContext ctx;
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    // _MAX_DAMAGE_LUCK: BAD_LUCK with damage_roll=1.0 (mirrors ai.py).
    // crit_threshold=100 (no crits), proc_threshold=101, secondary_threshold=101.
    LuckProfileC max_luck;
    max_luck.crit_threshold = 100.0;
    max_luck.damage_roll    = 1.0;
    max_luck.proc_threshold = 101.0;
    max_luck.random_mode    = false;

    // DamageLoopLuck for resolve_hit_count (hit_count_override=1 always used, so not needed,
    // but we build it for the fixed-damage path's call to cpp_fixed_damage_rolls).
    DamageLoopLuck dloop = make_max_damage_luck();

    for (const ExecAction& action : actions) {
        // ActionKind::MOVE = 0; move_slot < 0 means recharge/Struggle
        if (action.kind != 0 || action.move_slot < 0) continue;

        int32_t move_id = move_id_at(ai_mon, action.move_slot);
        if (move_id == MV_NONE) continue;

        // Try to get MoveData — skip moves without data.
        const MoveData* mdp = ai_move_data_get(move_id);
        if (mdp == nullptr) continue;
        const MoveData& md = *mdp;

        // Proactive fixed-damage moves bypass the DAMAGE tag check.
        if (is_fixed_damage_rank_move(move_id)) {
            auto fixed_opt = cpp_fixed_damage_rolls(move_id, md, ai_mon, pl_mon);
            if (fixed_opt.has_value()) {
                ctx.slots.push_back(action.move_slot);
                ctx.roll_arrays.push_back(*fixed_opt);
                ctx.assumed_hit_counts.push_back(1);
            }
            continue;
        }

        // Must have DAMAGE tag and not be excluded.
        if (!(md.tags & TAG_DAMAGE) || is_excluded_from_damage_rank(move_id)) continue;

        // Belch requires a consumed berry.
        if (move_id == MV_BELCH && ai_mon.consumed_berry == ITM_NONE) continue;

        // assumed hit count for this move.
        int32_t ahits = cpp_ai_assumed_hit_count(ai_mon, md);

        // Get per-single-hit roll values (hit_count_override=1, mirrors Python comment at 1127-1141).
        std::array<int32_t, 16> rolls = cpp_damage_roll_values(
            ai_mon, move_id, pl_mon, state, max_luck, /*hit_count_override=*/1);

        // Venoshock doubles when defender is poisoned/toxic (mirrors ai.py:1138-1139).
        if (move_id == MV_VENOSHOCK &&
            (pl_mon.status == STATUS_POISON || pl_mon.status == STATUS_TOXIC)) {
            for (auto& d : rolls) d *= 2;
        }

        // Scale by assumed hit count.
        if (ahits > 1) {
            for (auto& d : rolls) d *= ahits;
        }

        ctx.slots.push_back(action.move_slot);
        ctx.roll_arrays.push_back(rolls);
        ctx.assumed_hit_counts.push_back(ahits);
    }

    return ctx;
}

// ---------------------------------------------------------------------------
// cpp_compute_highest_damage_probs
// ---------------------------------------------------------------------------

std::vector<std::pair<double, double>> cpp_compute_highest_damage_probs(
    const std::vector<std::array<int32_t, 16>>& roll_arrays, int32_t hp)
{
    int m = (int)roll_arrays.size();
    if (m == 0) return {};

    if (m == 1) {
        int ko_count = 0;
        for (int32_t d : roll_arrays[0]) if (d >= hp) ++ko_count;
        double frac_kill = ko_count / 16.0;
        return {{frac_kill, 1.0 - frac_kill}};
    }

    // Build per-move histograms: g[j][d] = count of rolls giving capped damage exactly d.
    // g_kill[j][d]: count where raw damage also KOs.
    // g_nokill[j][d]: count where capped==d but raw < hp.
    using HistMap = std::unordered_map<int32_t, int32_t>;
    std::vector<HistMap> g(m), g_kill(m), g_nokill(m);

    for (int j = 0; j < m; ++j) {
        for (int32_t raw : roll_arrays[j]) {
            int32_t d = std::min(raw, hp);
            g[j][d]++;
            if (raw >= hp) g_kill[j][d]++;
            else           g_nokill[j][d]++;
        }
    }

    // Collect all unique damage levels (descending).
    std::vector<int32_t> all_d_vec;
    for (int j = 0; j < m; ++j)
        for (auto& kv : g[j]) {
            bool found = false;
            for (int32_t v : all_d_vec) if (v == kv.first) { found = true; break; }
            if (!found) all_d_vec.push_back(kv.first);
        }
    std::sort(all_d_vec.begin(), all_d_vec.end(), std::greater<int32_t>());

    std::vector<double> probs_kill(m, 0.0), probs_nokill(m, 0.0);
    std::vector<int32_t> a(m, 0);  // rolls above current d

    for (int32_t d : all_d_vec) {
        // gd[j], gd_kill[j], gd_nokill[j], bd[j]
        std::vector<int32_t> gd(m), gd_kill(m), gd_nokill(m), bd(m);
        for (int j = 0; j < m; ++j) {
            auto it = g[j].find(d);
            gd[j] = (it != g[j].end()) ? it->second : 0;
            auto itk = g_kill[j].find(d);
            gd_kill[j] = (itk != g_kill[j].end()) ? itk->second : 0;
            auto itnk = g_nokill[j].find(d);
            gd_nokill[j] = (itnk != g_nokill[j].end()) ? itnk->second : 0;
            bd[j] = 16 - a[j] - gd[j];
        }

        // Group: moves with gd[j] > 0.
        std::vector<int> group;
        for (int j = 0; j < m; ++j) if (gd[j] > 0) group.push_back(j);

        // Non-group factor: product of (bd[j]/16) for j not in group.
        double non_group_factor = 1.0;
        for (int j = 0; j < m; ++j) {
            if (gd[j] == 0)
                non_group_factor *= bd[j] / 16.0;
        }

        // For each group member i: enumerate subsets T of group\{i}.
        for (int gi = 0; gi < (int)group.size(); ++gi) {
            int i = group[gi];
            // others = group without i
            std::vector<int> others;
            for (int j : group) if (j != i) others.push_back(j);
            int n_others = (int)others.size();

            double inner = 0.0;
            for (int mask = 0; mask < (1 << n_others); ++mask) {
                int tie_size = 1 + __builtin_popcount(mask);
                double p_subset = 1.0 / tie_size;
                for (int k = 0; k < n_others; ++k) {
                    int j = others[k];
                    if (mask & (1 << k))
                        p_subset *= gd[j] / 16.0;
                    else
                        p_subset *= bd[j] / 16.0;
                }
                inner += p_subset;
            }

            probs_kill[i]   += (gd_kill[i] / 16.0)   * non_group_factor * inner;
            probs_nokill[i] += (gd_nokill[i] / 16.0) * non_group_factor * inner;
        }

        for (int j = 0; j < m; ++j) a[j] += gd[j];
    }

    std::vector<std::pair<double, double>> result(m);
    for (int i = 0; i < m; ++i)
        result[i] = {probs_kill[i], probs_nokill[i]};
    return result;
}

// ---------------------------------------------------------------------------
// Thin query wrappers
// ---------------------------------------------------------------------------

int32_t cpp_ai_effective_speed(
    const PokemonState& mon, const SideState& side, const BattleState& state)
{
    return cpp_effective_speed(mon, side, state);
}

bool cpp_ai_can_ko(
    const PokemonState& atk, int32_t move_id, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck, bool rollout_max_bp)
{
    if (def.hp <= 0) return true;
    int32_t dmg = cpp_expected_damage(atk, move_id, def, state, luck,
                                      /*roll_index=*/-1, rollout_max_bp, /*hit_count_override=*/-1);
    return dmg >= def.hp;
}

int32_t cpp_ai_best_damage_move(
    const PokemonState& atk, const PokemonState& def,
    const BattleState& state, const LuckProfileC& luck,
    bool check_pp, bool rollout_max_bp)
{
    int32_t best_move = MV_NONE;
    int32_t best_dmg  = 0;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t move_id = move_id_at(atk, slot);
        if (move_id == MV_NONE) continue;
        if (check_pp && move_pp_at(atk, slot) == 0) continue;
        int32_t dmg = cpp_expected_damage(atk, move_id, def, state, luck,
                                          /*roll_index=*/-1, rollout_max_bp, /*hit_count_override=*/-1);
        if (dmg > best_dmg) {
            best_dmg  = dmg;
            best_move = move_id;
        }
    }
    return best_move;
}
