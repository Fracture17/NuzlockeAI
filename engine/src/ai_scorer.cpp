// Stage 2+3 AI scorer: cpp_ai_faster, cpp_dist_action dispatcher, cpp_blend_damage_dist,
// and Stage-3 deterministic switch selection (_post_ko_switch_score, _cond2_valid_slots,
// _has_valid_switch_candidate, _select_voluntary_switch_target, select_post_ko_switch).
// The dist_* score-distribution family lives in ai_scorer_dist.cpp. Shared file-local
// constants, LuckProfile statics, and predicate helpers live in ai_scorer_internal.h.
#include "ai_scorer.h"
#include "ai_scorer_internal.h"
#include "ai_shared.h"
#include "ai_damage.h"
#include "damage.h"          // cpp_effective_stat
#include "type_chart_lookup.h"
#include "core_leaf.h"       // cpp_effective_speed

#include "../generated/ai_move_sets.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <map>
#include <set>
#include <stdexcept>
#include <vector>

using namespace ai_scorer;

// ---------------------------------------------------------------------------
// Public: cpp_ai_faster
// ---------------------------------------------------------------------------

bool cpp_ai_faster(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    const SideState& ai_side = side_at(state, ai_idx);
    const SideState& pl_side = side_at(state, 1 - ai_idx);
    int32_t ai_spe = cpp_ai_effective_speed(ai_mon, ai_side, state);
    int32_t pl_spe = cpp_ai_effective_speed(pl_mon, pl_side, state);
    return ai_spe >= pl_spe;
}

// ---------------------------------------------------------------------------
// Public: cpp_dist_action
// ---------------------------------------------------------------------------

ScoreDistC cpp_dist_action(const BattleState& state, int ai_idx, const ExecAction& action,
                           double p_highest, bool kills, bool ai_fst, bool sees_kill) {
    // Switch or recharge
    if (action.kind == AK_SWITCH) return {{0, 1.0}};

    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    int32_t slot = action.move_slot;
    if (slot < 0) return {{0, 1.0}};  // recharge

    int32_t move_id = move_id_at(ai_mon, slot);
    if (move_id == MV_NONE) return {{0, 1.0}};

    const MoveData* mdp = ai_move_data_get(move_id);
    if (mdp == nullptr) return {{6, 1.0}};  // md is None → [(6, 1.0)]
    const MoveData& md = *mdp;

    // --- Damaging moves ---
    if (move_id == MV_ROLLOUT || move_id == MV_RELIC_SONG || move_id == MV_METEOR_BEAM
        || is_fixed_damage_rank_move(move_id)
        || (md.tags & TAG_DAMAGE)) {
        return dist_damage(state, ai_idx, move_id, md, p_highest, kills, ai_fst);
    }

    // --- Protect ---
    if (ai_set_contains(PROTECT_MOVES, N_PROTECT_MOVES, move_id)) {
        return dist_protect(state, ai_idx);
    }

    // --- Recovery (tag-based, then explicit lists, then REST) ---
    if (md.tags & TAG_RECOVERY || ai_set_contains(RECOVERY_MOVE_SET, N_RECOVERY_MOVE_SET, move_id)) {
        return dist_recovery(state, ai_idx, 0.5);
    }
    if (ai_set_contains(WEATHER_RECOVERY_MOVES, N_WEATHER_RECOVERY_MOVES, move_id)) {
        bool sun = (state.weather == WE_SUNNY || state.weather == WE_HARSH_SUN);
        return dist_recovery(state, ai_idx, sun ? 0.67 : 0.5);
    }
    if (move_id == MV_REST) {
        auto [p_true, p_false] = should_recover(state, ai_idx, 1.0);
        double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
        if (hp_pct >= 1.0) return {{-20, 1.0}};
        if (hp_pct >= 0.85) return {{-6, 1.0}};
        bool has_cure = (ai_mon.item == ITM_LUM_BERRY || ai_mon.item == ITM_CHESTO_BERRY
                         || ai_mon.ability == AB_EARLY_BIRD || ai_mon.ability == AB_SHED_SKIN
                         || ai_mon.ability == AB_HYDRATION);
        int recover_score = has_cure ? 8 : 7;
        ScoreDistC out;
        if (p_true > 0) out.push_back({recover_score, p_true});
        if (p_false > 0) out.push_back({5, p_false});
        if (out.empty()) out.push_back({5, 1.0});
        return out;
    }

    // --- Hazards ---
    if (md.tags & TAG_HAZARD) {
        return dist_hazard(state, ai_idx, move_id);
    }

    // --- Screens ---
    if (md.tags & TAG_SCREEN) {
        return dist_screen(state, ai_idx, move_id);
    }

    // --- Powder moves ---
    if (md.tags & TAG_POWDER) {
        for (int32_t t : pl_mon.types) if (t == TYPE_GRASS) return {{-50, 1.0}};
        if (pl_mon.ability == AB_OVERCOAT || pl_mon.item == ITM_SAFETY_GOGGLES)
            return {{-50, 1.0}};
    }

    // --- Paralysis ---
    if (ai_set_contains(PARALYSIS_MOVES, N_PARALYSIS_MOVES, move_id)) {
        return dist_paralysis(state, ai_idx, move_id);
    }

    // --- Will-O-Wisp ---
    if (move_id == MV_WILL_O_WISP) {
        return dist_will_o_wisp(state, ai_idx);
    }

    // --- Poison ---
    if (ai_set_contains(POISON_INFLICT_MOVES, N_POISON_INFLICT_MOVES, move_id)) {
        return dist_poison_move(state, ai_idx, move_id, sees_kill);
    }

    // --- Substitute ---
    if (move_id == MV_SUBSTITUTE) {
        if (ai_mon.hp * 100 / ai_mon.max_hp <= 50) return {{-40, 1.0}};
        if (pl_mon.ability == AB_INFILTRATOR) return {{-40, 1.0}};
        if (ai_mon.volatiles & VOL_SUBSTITUTE) return {{-40, 1.0}};
        return {{6, 1.0}};
    }

    // --- Belly Drum ---
    if (move_id == MV_BELLY_DRUM) {
        if (ai_mon.stage0 >= 6 || ai_mon.hp <= ai_mon.max_hp / 2) return {{-40, 1.0}};
        if (is_incapacitated(pl_mon)) return {{9, 1.0}};
        int32_t post_drum_hp = ai_mon.max_hp / 2;
        if (ai_mon.item == ITM_SITRUS_BERRY) post_drum_hp += ai_mon.max_hp / 4;
        post_drum_hp = std::min(post_drum_hp, ai_mon.max_hp);
        bool threatened_after = false;
        for (int slot = 0; slot < 4; ++slot) {
            int32_t mid = move_id_at(pl_mon, slot);
            if (mid == MV_NONE) continue;
            if (move_pp_at(pl_mon, slot) == 0) continue;
            const MoveData* mdp2 = ai_move_data_get(mid);
            if (!mdp2 || mdp2->base_power == 0) continue;
            int32_t dmg = cpp_expected_damage(pl_mon, mid, ai_mon, state, AVERAGE_LUCK_C,
                                              -1, false, -1);
            if (dmg >= post_drum_hp) { threatened_after = true; break; }
        }
        return threatened_after ? ScoreDistC{{6, 0.5}, {4, 0.5}} : ScoreDistC{{8, 1.0}};
    }

    // --- Shell Smash: block if Atk stage already raised ---
    if (move_id == MV_SHELL_SMASH) {
        if (ai_mon.stage0 >= 1 || ai_mon.stage2 >= 6) return {{-20, 1.0}};
        // Fall through to offensive setup
    }

    // --- Focus Energy / Laser Focus ---
    if (move_id == MV_FOCUS_ENERGY || move_id == MV_LASER_FOCUS) {
        bool already_active;
        if (move_id == MV_FOCUS_ENERGY) {
            already_active = (ai_mon.crit_stage >= 2);
        } else {
            already_active = has_timed_volatile(ai_mon, VE_LASER_FOCUS);
        }
        if (already_active) return {{-40, 1.0}};
        if (pl_mon.ability == AB_SHELL_ARMOR || pl_mon.ability == AB_BATTLE_ARMOR)
            return {{-40, 1.0}};
        if (player_can_ko_ai(state, ai_idx)
            && ai_mon.item != ITM_FOCUS_SASH
            && !(ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp))
            return {{-40, 1.0}};
        // Crit incentive
        bool has_crit = (ai_mon.ability == AB_SUPER_LUCK || ai_mon.ability == AB_SNIPER
                         || ai_mon.item == ITM_SCOPE_LENS);
        if (!has_crit) {
            for (int slot = 0; slot < 4; ++slot)
                if (ai_set_contains(HIGH_CRIT_MOVES, N_HIGH_CRIT_MOVES, move_id_at(ai_mon, slot))) {
                    has_crit = true; break;
                }
        }
        return has_crit ? ScoreDistC{{14, 0.25}, {7, 0.75}} : ScoreDistC{{6, 1.0}};
    }

    // --- Speed setup ---
    if (ai_set_contains(SPEED_SETUP_MOVES, N_SPEED_SETUP_MOVES, move_id)) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::SPEED);
    }

    // --- Nasty Plot / Tail Glow / Work Up: SpAtk stage >= 2 penalty ---
    if (move_id == MV_NASTY_PLOT || move_id == MV_TAIL_GLOW || move_id == MV_WORK_UP) {
        if (pl_mon.ability == AB_UNAWARE) return {{-40, 1.0}};
        ScoreDistC base_dist_np = dist_setup(state, ai_idx, SetupKind::OFFENSIVE);
        if (ai_mon.stage2 >= 2) {
            for (auto& [s, p] : base_dist_np) s -= 1;
        }
        return base_dist_np;
    }

    // --- Coaching ---
    if (move_id == MV_COACHING) {
        if (state.format != FMT_DOUBLES) return {{-20, 1.0}};
        const SideState& ai_side = side_at(state, ai_idx);
        const PokemonState* partner = nullptr;
        for (size_t pi = 1; pi < ai_side.active_indices.size(); ++pi) {
            int pslot = ai_side.active_indices[pi];
            if (!ai_side.team[pslot].fainted) { partner = &ai_side.team[pslot]; break; }
        }
        if (!partner || partner->ability == AB_CONTRARY) return {{-20, 1.0}};
        int score = 6;
        for (int i : {0, 1}) {  // Atk, Def stages
            int stage = (i == 0) ? partner->stage0 : partner->stage1;
            if (stage < 2) score += 1 - stage;
        }
        return {{score, 0.20}, {score + 1, 0.80}};
    }

    // --- Offensive setup ---
    // Shell Smash falls through here after the stat-stage check above
    bool is_offensive_setup = (move_id == MV_SHELL_SMASH)
        || ai_set_contains(OFFENSIVE_SETUP_MOVES, N_OFFENSIVE_SETUP_MOVES, move_id)
        || ((md.tags & TAG_SETUP) && (int32_t)md.category == CAT_STATUS && (int32_t)md.target == TGT_SELF);
    if (is_offensive_setup) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::OFFENSIVE);
    }

    // --- Defensive setup ---
    if (ai_set_contains(DEFENSIVE_SETUP_MOVES, N_DEFENSIVE_SETUP_MOVES, move_id)) {
        if (pl_mon.ability == AB_UNAWARE
            && !ai_set_contains(UNAWARE_SETUP_EXCEPTIONS, N_UNAWARE_SETUP_EXCEPTIONS, move_id))
            return {{-40, 1.0}};
        return dist_setup(state, ai_idx, SetupKind::DEFENSIVE);
    }

    // --- Tailwind ---
    if (move_id == MV_TAILWIND) return dist_tailwind(state, ai_idx);

    // --- Trick Room ---
    if (move_id == MV_TRICK_ROOM) return dist_trick_room(state, ai_idx);

    // --- Terrain ---
    if (ai_set_contains(TERRAIN_MOVES, N_TERRAIN_MOVES, move_id)) {
        return dist_terrain(state, ai_idx);
    }

    // --- STATUS-branch special handlers ---
    return dist_status_special(state, ai_idx, move_id, ai_mon, pl_mon, ai_fst, sees_kill);
}

// ---------------------------------------------------------------------------
// Public: cpp_blend_damage_dist
// ---------------------------------------------------------------------------

ScoreDistC cpp_blend_damage_dist(const BattleState& state, int ai_idx, const ExecAction& action,
                                 double p_kill, double p_nokill, bool ai_fst, bool sees_kill) {
    double p_none = std::max(0.0, 1.0 - p_kill - p_nokill);

    // Build components in kill → nokill → none order (mirrors Python list order)
    struct Component { double w; ScoreDistC dist; };
    std::vector<Component> components;
    if (p_kill > 0)
        components.push_back({p_kill, cpp_dist_action(state, ai_idx, action, 1.0, true, ai_fst, sees_kill)});
    if (p_nokill > 0)
        components.push_back({p_nokill, cpp_dist_action(state, ai_idx, action, 1.0, false, ai_fst, sees_kill)});
    if (p_none > 0)
        components.push_back({p_none, cpp_dist_action(state, ai_idx, action, 0.0, false, ai_fst, sees_kill)});

    // Merge into sorted map (std::map preserves insertion order for same key — we use map for
    // accumulation, then convert to sorted vector). Same semantics as Python dict merge.
    std::map<int32_t, double> merged;
    for (const auto& comp : components) {
        for (auto [s, p] : comp.dist) {
            merged[s] += comp.w * p;
        }
    }

    ScoreDistC result;
    result.reserve(merged.size());
    for (auto [s, p] : merged) result.push_back({s, p});
    return result;
}

// ---------------------------------------------------------------------------
// Stage 3: switch scoring constants
// ---------------------------------------------------------------------------

static constexpr int32_t SP_DITTO      = 132;
static constexpr int32_t SP_WYNAUT     = 360;
static constexpr int32_t SP_WOBBUFFET  = 202;

// ---------------------------------------------------------------------------
// Public: cpp_post_ko_switch_score
// ---------------------------------------------------------------------------

int cpp_post_ko_switch_score(const PokemonState& bench, const PokemonState& player_active,
                             const BattleState& state) {
    int score = 0;

    // Ditto: +2 additive (before general scoring)
    if (bench.species == SP_DITTO)
        score += 2;

    // Wynaut / Wobbuffet: +2 unless bench_slower AND player_ohkos → +0
    if (bench.species == SP_WYNAUT || bench.species == SP_WOBBUFFET) {
        int32_t bench_spd  = cpp_effective_stat(bench, 5);
        int32_t player_spd = cpp_effective_stat(player_active, 5);
        bool bench_slower  = bench_spd <= player_spd;
        int32_t best_pl_mv = cpp_ai_best_damage_move(player_active, bench, state,
                                                     MAX_LUCK_C, /*check_pp=*/false,
                                                     /*rollout_max_bp=*/true);
        bool player_ohkos = (best_pl_mv != MV_NONE)
            && cpp_ai_can_ko(player_active, best_pl_mv, bench, state,
                             MAX_LUCK_C, /*rollout_max_bp=*/true);
        if (!(bench_slower && player_ohkos))
            score += 2;
        // else +0 from this block
    }

    // General 7-tier scoring (mirrors Python lines 1513-1553)
    int32_t bench_spd  = cpp_effective_stat(bench, 5);
    int32_t player_spd = cpp_effective_stat(player_active, 5);
    bool bench_faster  = bench_spd > player_spd;  // strict: ties are NOT faster

    int32_t best_bench_mv = cpp_ai_best_damage_move(bench, player_active, state,
                                                    MAX_LUCK_C, /*check_pp=*/false,
                                                    /*rollout_max_bp=*/true);
    int32_t best_pl_mv    = cpp_ai_best_damage_move(player_active, bench, state,
                                                    MAX_LUCK_C, /*check_pp=*/false,
                                                    /*rollout_max_bp=*/true);

    bool bench_ohkos = (best_bench_mv != MV_NONE)
        && cpp_ai_can_ko(bench, best_bench_mv, player_active, state,
                         MAX_LUCK_C, /*rollout_max_bp=*/true);
    bool player_ohkos = (best_pl_mv != MV_NONE)
        && cpp_ai_can_ko(player_active, best_pl_mv, bench, state,
                         MAX_LUCK_C, /*rollout_max_bp=*/true);

    // Use max_hp if set, otherwise fall back to stat_hp (mirrors Python: max_hp = stats[0] when None).
    int32_t player_max_hp = player_active.has_max_hp ? player_active.max_hp : player_active.stat_hp;
    int32_t bench_max_hp  = bench.has_max_hp         ? bench.max_hp         : bench.stat_hp;

    double bench_dmg_pct = 0.0;
    if (best_bench_mv != MV_NONE && player_max_hp > 0) {
        int32_t dmg = cpp_expected_damage(bench, best_bench_mv, player_active, state,
                                          MAX_LUCK_C, /*roll_index=*/-1,
                                          /*rollout_max_bp=*/true, /*hit_count_override=*/-1);
        bench_dmg_pct = (double)dmg / player_max_hp;
    }
    double player_dmg_pct = 0.0;
    if (best_pl_mv != MV_NONE && bench_max_hp > 0) {
        int32_t dmg = cpp_expected_damage(player_active, best_pl_mv, bench, state,
                                          MAX_LUCK_C, /*roll_index=*/-1,
                                          /*rollout_max_bp=*/true, /*hit_count_override=*/-1);
        player_dmg_pct = (double)dmg / bench_max_hp;
    }
    bool bench_deals_more_pct = bench_dmg_pct > player_dmg_pct;

    if (bench_faster && bench_ohkos)
        return score + 5;
    if (!bench_faster && bench_ohkos && !player_ohkos)
        return score + 4;
    if (bench_faster && bench_deals_more_pct)
        return score + 3;
    if (!bench_faster && bench_deals_more_pct)
        return score + 2;
    if (bench_faster)
        return score + 1;
    if (!bench_faster && player_ohkos)
        return score + (-1);
    return score + 0;
}

// ---------------------------------------------------------------------------
// Public: cpp_cond2_valid_slots
// ---------------------------------------------------------------------------

std::set<int> cpp_cond2_valid_slots(const BattleState& state, int ai_idx) {
    const SideState& side    = side_at(state, ai_idx);
    int active_slot          = side.active_indices[0];
    const PokemonState& pl   = active_mon(state, 1 - ai_idx);
    int32_t pl_spe           = cpp_effective_stat(pl, 5);

    bool found_faster = false;  // bug: once true, stays true for later (slower) mons
    std::set<int> valid;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        const PokemonState& mon = side.team[slot];
        if (slot == active_slot || mon.fainted)
            continue;

        int32_t bench_spe = cpp_effective_stat(mon, 5);
        bool is_faster    = bench_spe > pl_spe;

        if (is_faster || found_faster) {
            // Faster-branch (or bug-propagated): valid iff player doesn't OHKO
            int32_t best_pl_mv = cpp_ai_best_damage_move(pl, mon, state, MAX_LUCK_C,
                                                         /*check_pp=*/false,
                                                         /*rollout_max_bp=*/true);
            bool player_ohkos = (best_pl_mv != MV_NONE)
                && cpp_ai_can_ko(pl, best_pl_mv, mon, state,
                                 MAX_LUCK_C, /*rollout_max_bp=*/true);
            if (!player_ohkos)
                valid.insert(slot);
            if (is_faster)
                found_faster = true;  // bug: subsequent mons also treated as faster
        } else {
            // Slower-branch: valid if player can't 2HKO (dmg*2 < mon.hp, or no player move)
            int32_t best_pl_mv = cpp_ai_best_damage_move(pl, mon, state, MAX_LUCK_C,
                                                         /*check_pp=*/false,
                                                         /*rollout_max_bp=*/true);
            if (best_pl_mv == MV_NONE) {
                valid.insert(slot);
            } else {
                int32_t dmg = cpp_expected_damage(pl, best_pl_mv, mon, state,
                                                  MAX_LUCK_C, /*roll_index=*/-1,
                                                  /*rollout_max_bp=*/true,
                                                  /*hit_count_override=*/-1);
                if ((int64_t)dmg * 2 < (int64_t)mon.hp)
                    valid.insert(slot);
            }
        }
    }
    return valid;
}

// ---------------------------------------------------------------------------
// Public: cpp_has_valid_switch_candidate
// ---------------------------------------------------------------------------

bool cpp_has_valid_switch_candidate(const BattleState& state, int ai_idx) {
    return !cpp_cond2_valid_slots(state, ai_idx).empty();
}

// ---------------------------------------------------------------------------
// Public: cpp_select_voluntary_switch_target
// ---------------------------------------------------------------------------

int cpp_select_voluntary_switch_target(const BattleState& state, int ai_idx) {
    std::set<int> valid_slots = cpp_cond2_valid_slots(state, ai_idx);
    const SideState& side     = side_at(state, ai_idx);
    const PokemonState& pl    = active_mon(state, 1 - ai_idx);

    int best_score = 0;
    bool found     = false;
    int best_slot  = -1;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        if (valid_slots.find(slot) == valid_slots.end())
            continue;
        int sc = cpp_post_ko_switch_score(side.team[slot], pl, state);
        if (!found || sc > best_score) {
            best_score = sc;
            best_slot  = slot;
            found      = true;
        }
    }

    if (!found)
        throw NoSwitchCandidate("No Cond2-valid switch target found");
    return best_slot;
}

// ---------------------------------------------------------------------------
// Public: cpp_select_post_ko_switch
// ---------------------------------------------------------------------------

int cpp_select_post_ko_switch(const BattleState& state, int ai_idx) {
    const SideState& side  = side_at(state, ai_idx);
    int active_slot        = side.active_indices[0];
    const PokemonState& pl = active_mon(state, 1 - ai_idx);

    int best_score = 0;
    bool found     = false;
    int best_slot  = -1;

    for (int slot = 0; slot < (int)side.team.size(); ++slot) {
        if (slot == active_slot)
            continue;
        const PokemonState& mon = side.team[slot];
        if (mon.fainted)
            continue;
        int sc = cpp_post_ko_switch_score(mon, pl, state);
        if (!found || sc > best_score) {
            best_score = sc;
            best_slot  = slot;
            found      = true;
        }
    }

    if (!found)
        throw NoSwitchCandidate("No valid switch target: all bench mons are fainted");
    return best_slot;
}
