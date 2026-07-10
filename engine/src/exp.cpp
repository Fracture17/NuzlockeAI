// C++ port of EXP distribution (src/engine/exp.py, C1.7a).
// Float/floor arithmetic mirrors Python exactly; species data via isolated species_exp_lookup TU.
#include "exp.h"
#include "species_exp_lookup.h"
#include "stats.h"
#include "event_log.h"           // rich_log_exp_gain / rich_log_level_up

#include <algorithm>
#include <cmath>
#include <set>

namespace {

constexpr int32_t SPECIES_SHEDINJA = 292;

// GrowthRate enum values (mirror cpp/generated/growth_rate.h).
enum : int32_t {
    GR_MEDIUM_FAST = 0, GR_ERRATIC = 1, GR_FLUCTUATING = 2,
    GR_MEDIUM_SLOW = 3, GR_FAST = 4, GR_SLOW = 5,
};

}  // namespace

int64_t cpp_exp_for_level(int32_t growth_rate, int32_t level) {
    const int64_t n = level;
    const int64_t n3 = n * n * n;
    int64_t result;
    switch (growth_rate) {
        case GR_MEDIUM_FAST:
            result = n3;
            break;
        case GR_ERRATIC:
            if (n <= 50)      result = ((100 - n) * n3) / 50;
            else if (n <= 68) result = ((150 - n) * n3) / 100;
            else if (n <= 98) result = ((1911 - 10 * n) / 3) * n3 / 500;
            else              result = (160 - n) * n3 / 100;
            break;
        case GR_FLUCTUATING:
            if (n < 15)       result = (((n + 1) / 3) + 24) * n3 / 50;
            else if (n <= 36) result = (n + 14) * n3 / 50;
            else              result = ((n / 2) + 32) * n3 / 50;
            break;
        case GR_MEDIUM_SLOW:
            result = (6 * n3 / 5) - 15 * n * n + 100 * n - 140;
            break;
        case GR_FAST:
            result = 4 * n3 / 5;
            break;
        case GR_SLOW:
            result = 5 * n3 / 4;
            break;
        default:
            throw std::runtime_error("cpp_exp_for_level: unknown growth rate "
                                     + std::to_string(growth_rate));
    }
    return std::max<int64_t>(0, result);
}

int32_t cpp_calc_exp_gain(int32_t fainted_species, int32_t fainted_level, int32_t winner_level,
                          bool is_ot, bool is_unevolved) {
    int32_t b = cpp_species_exp_data(fainted_species).exp_yield;
    double L = fainted_level;
    double Lp = winner_level;
    double t = is_ot ? 1.0 : 1.5;
    double v = is_unevolved ? (4915.0 / 4096.0) : 1.0;
    double e = std::floor(b * L / 5.0);
    e = e * std::pow((2 * L + 10) / (L + Lp + 10), 2.5);
    e = std::floor((e + 1) * t);
    return static_cast<int32_t>(std::floor(e * v));
}

void cpp_recalc_stats(PokemonState& mon) {
    SpeciesExpData sp = cpp_species_exp_data(mon.species);
    int32_t bases[6] = {sp.base_hp, sp.base_atk, sp.base_def, sp.base_spa, sp.base_spd, sp.base_spe};
    int32_t ivs[6] = {mon.iv_hp, mon.iv_atk, mon.iv_def, mon.iv_spa, mon.iv_spd, mon.iv_spe};
    int32_t new_stats[6];
    for (int i = 0; i < 6; ++i)
        new_stats[i] = compute_stat(i, bases[i], ivs[i], mon.nature, mon.level);

    int32_t new_max_hp, new_hp;
    if (mon.species == SPECIES_SHEDINJA) {
        new_stats[0] = 1;
        new_max_hp = 1;
        new_hp = std::min(1, mon.hp);
    } else {
        new_max_hp = new_stats[0];
        new_hp = std::min(new_max_hp, mon.hp + (new_max_hp - mon.max_hp));
    }
    mon.has_stats = true;
    mon.stat_hp = new_stats[0]; mon.stat_atk = new_stats[1]; mon.stat_def = new_stats[2];
    mon.stat_spa = new_stats[3]; mon.stat_spd = new_stats[4]; mon.stat_spe = new_stats[5];
    mon.has_max_hp = true; mon.max_hp = new_max_hp;
    mon.has_hp = true; mon.hp = new_hp;
}

int32_t cpp_apply_exp_gain(PokemonState& mon, int32_t exp_amount,
                           bool has_level_cap, int32_t level_cap, int32_t growth_rate) {
    if (exp_amount <= 0) return 0;
    if (mon.level >= 100) return 0;
    if (has_level_cap && mon.level >= level_cap) return 0;

    int32_t original_exp = mon.exp;
    int32_t hard_cap = has_level_cap ? std::min(level_cap, 100) : 100;

    int64_t new_exp = static_cast<int64_t>(mon.exp) + exp_amount;
    if (hard_cap < 100)
        new_exp = std::min<int64_t>(new_exp, cpp_exp_for_level(growth_rate, hard_cap + 1) - 1);

    mon.exp = static_cast<int32_t>(new_exp);
    while (mon.level < hard_cap && new_exp >= cpp_exp_for_level(growth_rate, mon.level + 1)) {
        mon.level += 1;
        cpp_recalc_stats(mon);
    }

    if (has_level_cap && mon.level >= level_cap) {
        int32_t cap_exp = static_cast<int32_t>(cpp_exp_for_level(growth_rate, level_cap));
        if (mon.exp != cap_exp) mon.exp = cap_exp;
    }

    return mon.exp - original_exp;
}

void cpp_distribute_exp(BattleState& state, int fainted_team_idx,
                        std::vector<std::vector<int32_t>>& exp_participants,
                        bool allow_fainted_winners) {
    if (exp_participants.empty()) return;

    SideState& opp = state.side1;
    SideState& player = state.side0;

    // Locate the active slot position for fainted_team_idx.
    int slot_pos = -1;
    for (size_t i = 0; i < opp.active_indices.size(); ++i) {
        if (opp.active_indices[i] == fainted_team_idx) { slot_pos = (int)i; break; }
    }
    if (slot_pos < 0 || slot_pos >= (int)exp_participants.size()) return;

    std::vector<int32_t>& participants = exp_participants[slot_pos];
    if (participants.empty()) {
        participants.clear();
        return;
    }

    const PokemonState& fainted_mon = opp.team[fainted_team_idx];
    int32_t fainted_species = fainted_mon.species;
    int32_t fainted_level = fainted_mon.level;

    // Sorted iteration (mirror Python sorted(participants)).
    std::set<int32_t> sorted_participants(participants.begin(), participants.end());
    for (int32_t team_idx : sorted_participants) {
        if (team_idx >= (int32_t)player.team.size()) continue;
        PokemonState& winner = player.team[team_idx];
        if (winner.fainted && !allow_fainted_winners) continue;
        int32_t old_level = winner.level;
        int32_t exp_amount = cpp_calc_exp_gain(fainted_species, fainted_level, winner.level);
        SpeciesExpData wd = cpp_species_exp_data(winner.species);
        int32_t net_gained = cpp_apply_exp_gain(winner, exp_amount, state.has_level_cap,
                                                state.level_cap, wd.growth_rate);
        // EXP_GAIN + LEVEL_UP observation (Python exp.py:152-154). The "gained X Exp"
        // message shows GROSS exp_amount when the mon actually gained (net>0); a mon
        // already at the cap gains nothing and shows no message, so log 0 to preserve
        // the message count. One LEVEL_UP per level crossed.
        rich_log_exp_gain(state.turn_number, winner.species, net_gained > 0 ? exp_amount : 0);
        for (int32_t nl = old_level + 1; nl <= winner.level; ++nl)
            rich_log_level_up(state.turn_number, winner.species, nl);
    }

    exp_participants[slot_pos].clear();
}

void cpp_flush_opponent_faint_exp(BattleState& state,
                                  std::vector<std::vector<int32_t>>& exp_participants,
                                  bool allow_fainted_winners) {
    SideState& opp = state.side1;
    for (int32_t team_idx : opp.active_indices) {
        if (team_idx < 0 || team_idx >= (int32_t)opp.team.size()) continue;
        if (opp.team[team_idx].fainted)
            cpp_distribute_exp(state, team_idx, exp_participants, allow_fainted_winners);
    }
}
