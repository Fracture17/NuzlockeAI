// Read-only engine queries for the analytic solver tier.
// damage_table: sweeps cpp_calculate_damage over roll_index=0..15 × crit_override={0,1},
// collecting distinct sorted values per crit class. Consumes NO RNG — roll_index and
// crit_override both bypass rng_resolve_damage_roll / rng_resolve_crit entirely.
// hp_thresholds: reads item/ability fields to enumerate one-shot HP discontinuities.
#include "solver/engine_queries.h"

#include "ai_shared.h"       // move_id_at, ai_move_data_get
#include "damage.h"          // cpp_calculate_damage, LuckProfileC
#include "move_exec.h"       // ExecAction
#include "state.h"

#include <algorithm>
#include <set>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Item / ability IDs mirrored from engine source.
// Source: move_exec_helpers.cpp, damage.cpp, effects.cpp, core_leaf.cpp.
// ---------------------------------------------------------------------------

// Full-HP protections (source: move_exec_helpers.cpp:25, residuals.cpp:595-596)
static constexpr int32_t ITEM_FOCUS_SASH  = 275;   // move_exec_helpers.cpp:25
static constexpr int32_t AB_STURDY        = 5;      // move_exec_helpers.cpp:28
static constexpr int32_t AB_MULTISCALE    = 136;    // damage.cpp:90
static constexpr int32_t AB_SHADOW_SHIELD = 231;    // damage.cpp:91

// Half-HP berries (threshold_denom=2 in hp_threshold_berry, effects.cpp:406-408).
// Trigger condition: mon.hp <= max_hp / 2 (effects.cpp:442 "if (mon.hp > threshold_hp) return false").
// NOTE: threshold_hp = max_hp / 2 (floor division). Trigger is hp <= threshold_hp (i.e. <= max_hp/2).
static constexpr int32_t ITEM_SITRUS      = 158;    // effects.cpp:406
static constexpr int32_t ITEM_ORAN        = 155;    // effects.cpp:407
static constexpr int32_t ITEM_BERRY_JUICE = 34;     // effects.cpp:408

// Quarter-HP berries (threshold_denom=4 in hp_threshold_berry, effects.cpp:409-420).
// Trigger condition: mon.hp <= max_hp / 4.
// Liechi=201, Petaya=204, Salac=203, Apicot=205, Ganlon=202 (effects.cpp:409-413).
// Starf=207, Lansat=206 (effects.cpp:414-415).
// Figy=159, Wiki=160, Mago=161, Aguav=162, Iapapa=163 (effects.cpp:416-420).
static const int32_t QUARTER_BERRIES[] = {
    201, 204, 203, 205, 202, 207, 206, 159, 160, 161, 162, 163
};
static constexpr int N_QUARTER_BERRIES = 12;

// Custap Berry (210): HP threshold = max_hp / 4 (core_leaf.cpp:726-731).
// Triggers "goes first" priority at <= max_hp/4. Gluttony widens to <= max_hp/2 but
// we conservatively model the default (non-Gluttony) quarter threshold here.
static constexpr int32_t ITEM_CUSTAP = 210;

// Unrecognized consumables: items the engine will consume but that hp_thresholds does not model.
// These set residual_unknown=true so the analytic caller scopes out.
//
// Status-curing berries (check_status_berry / check_confusion_berry; effects.cpp:138-205):
//   Chesto=149, Pecha=150, Rawst=152, Aspear=153, Cheri=151, Lum=157.
// Persim Berry (156): confusion-curing (effects.cpp:376-386).
// Leppa Berry (154): PP restore (move_exec_helpers.cpp:288-294).
// Focus Band (230): proc-based survival, not a deterministic threshold (move_exec_helpers.cpp:25).
// White Herb (214): stat stage restore — consumed but not HP threshold.
// Oran Berry (155) and Berry Juice (34) are modeled above as Half; they are NOT in unknown.
static const int32_t UNRECOGNIZED_CONSUMABLES[] = {
    149, 150, 151, 152, 153,  // Chesto/Pecha/Cheri/Rawst/Aspear (status berries)
    156,                       // Persim (confusion berry)
    157,                       // Lum (universal status curer)
    154,                       // Leppa (PP restore)
    230,                       // Focus Band (proc-based, not deterministic)
    214,                       // White Herb (stat stage restore)
};
static constexpr int N_UNRECOGNIZED = 6 + 4;  // 10 entries

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Get the active PokemonState for a side (const).
static const PokemonState& get_active(const BattleState& state, int side) {
    const SideState& ss = (side == 0) ? state.side0 : state.side1;
    return ss.team[ss.active_indices[0]];
}

// Validate side and single-active precondition; throw std::invalid_argument on failure.
static void validate_side(const BattleState& state, int side) {
    if (side < 0 || side > 1)
        throw std::invalid_argument("engine_queries: side must be 0 or 1");
    const SideState& ss = (side == 0) ? state.side0 : state.side1;
    if (ss.active_indices.empty())
        throw std::invalid_argument("engine_queries: side " + std::to_string(side)
                                    + " has no active mon");
}

// Construct an inert LuckProfileC for damage_table calls: random_mode=false, rng=nullptr.
// With roll_index and crit_override explicit, cpp_calculate_damage bypasses both
// rng_resolve_damage_roll and rng_resolve_crit entirely — no RNG draw occurs.
static LuckProfileC inert_luck() {
    LuckProfileC l{};
    l.random_mode = false;
    l.rng = nullptr;
    return l;
}

// ---------------------------------------------------------------------------
// damage_table
// ---------------------------------------------------------------------------

DamageTable damage_table(const BattleState& state, int attacker_side, const ExecAction& action) {
    if (attacker_side < 0 || attacker_side > 1)
        throw std::invalid_argument("engine_queries: attacker_side must be 0 or 1");
    validate_side(state, attacker_side);

    if (action.kind != 0)
        throw std::invalid_argument("engine_queries: action must be a MOVE (kind=0)");

    const PokemonState& attacker = get_active(state, attacker_side);
    int def_side = 1 - attacker_side;
    validate_side(state, def_side);
    const PokemonState& defender = get_active(state, def_side);

    // Resolve move_id from the action's move_slot.
    int32_t move_id;
    if (action.move_override >= 0) {
        move_id = action.move_override;
    } else {
        int slot = action.move_slot;
        if (slot < 0 || slot > 3)
            throw std::invalid_argument("engine_queries: move_slot out of range (0-3)");
        move_id = move_id_at(attacker, slot);
    }

    if (move_id <= 0)
        throw std::invalid_argument("engine_queries: resolved move_id is 0 (no move at slot)");

    // Look up move data for multi-hit metadata.
    const MoveData* md = ai_move_data_get(move_id);
    if (!md)
        throw std::invalid_argument("engine_queries: unknown move id "
                                    + std::to_string(move_id));

    LuckProfileC atk_luck = inert_luck();
    LuckProfileC def_luck = inert_luck();

    // Sweep roll_index=0..15 × crit_override={0,1} and collect distinct damage values.
    std::set<int32_t> noncrit_set, crit_set;

    for (int roll = 0; roll < 16; ++roll) {
        for (int crit = 0; crit <= 1; ++crit) {
            int32_t dmg = cpp_calculate_damage(
                attacker, move_id, defender, state,
                atk_luck, def_luck,
                /*bp_override=*/0,
                /*def_side_idx=*/def_side,
                /*spread_hit=*/false,
                /*roll_index=*/roll,
                /*ai_scoring_view=*/false,
                /*crit_override=*/crit);
            if (crit == 0)
                noncrit_set.insert(dmg);
            else
                crit_set.insert(dmg);
        }
    }

    DamageTable tbl;
    tbl.noncrit.assign(noncrit_set.begin(), noncrit_set.end());
    tbl.crit.assign(crit_set.begin(), crit_set.end());

    // immune: all rolls of both classes returned 0.
    // cpp_calculate_damage returns 0 for immune matchups and >= 1 otherwise.
    bool all_zero = true;
    for (int32_t v : tbl.noncrit) if (v != 0) { all_zero = false; break; }
    if (all_zero) for (int32_t v : tbl.crit) if (v != 0) { all_zero = false; break; }
    tbl.immune = all_zero;

    // Multi-hit metadata: mirror resolve_hit_count (move_exec_damage.cpp:188-201).
    // Sources: Skill Link (AB=92) forces max_hits; Battle Bond Greninja Shuriken forces 3.
    // General (2,5) distribution support = {2,3,4,5}; uniform (min,max) = {min..max}.
    static constexpr int32_t AB_SKILL_LINK  = 92;
    static constexpr int32_t AB_BATTLE_BOND = 210;
    static constexpr int32_t SP_GRENINJA_ASH = 10018;  // species id for Ash-Greninja
    static constexpr int32_t MV_WATER_SHURIKEN = 360;

    int min_h = md->min_hits;
    int max_h = md->max_hits;

    if (min_h <= 0) min_h = 1;
    if (max_h <= 0) max_h = 1;

    tbl.max_hits = max_h;

    if (max_h == 1) {
        // Single-hit move (or Parental Bond — scoped out as noted in header).
        tbl.hit_count_support = {1};
    } else if (attacker.ability == AB_SKILL_LINK && max_h > 1) {
        // Skill Link: always max hits (move_exec_damage.cpp:194).
        tbl.hit_count_support = {max_h};
    } else if (attacker.ability == AB_BATTLE_BOND
               && attacker.species == SP_GRENINJA_ASH
               && move_id == MV_WATER_SHURIKEN) {
        // Battle Bond Greninja Water Shuriken: always 3 (move_exec_damage.cpp:195-196).
        tbl.hit_count_support = {3};
    } else {
        // General: enumerate support.
        // (2,5) weighted distribution: support = {2,3,4,5} (rng_resolver.h:227-232).
        // Uniform: support = {min_h .. max_h}.
        if (min_h == 2 && max_h == 5) {
            tbl.hit_count_support = {2, 3, 4, 5};
        } else {
            for (int h = min_h; h <= max_h; ++h)
                tbl.hit_count_support.push_back(h);
        }
    }

    return tbl;
}

// ---------------------------------------------------------------------------
// hp_thresholds
// ---------------------------------------------------------------------------

HpThresholds hp_thresholds(const BattleState& state, int side) {
    validate_side(state, side);

    const PokemonState& mon = get_active(state, side);
    HpThresholds result;

    int32_t item    = mon.item;
    int32_t ability = mon.ability;
    int32_t max_hp  = mon.has_max_hp ? mon.max_hp
                                     : (mon.has_stats ? mon.stat_hp : 0);
    int32_t cur_hp  = mon.has_hp ? mon.hp : max_hp;

    // --- Full-HP effects ---
    // Focus Sash (275): triggered when hp==max_hp AND damage would KO (move_exec_helpers.cpp:103-105).
    // Include only when the mon is currently at full HP (otherwise it cannot trigger).
    if (item == ITEM_FOCUS_SASH && cur_hp == max_hp) {
        result.thresholds.push_back({max_hp, ThresholdKind::FullHp});
    }

    // Sturdy (5): triggered when hp==max_hp AND not bypassed by Mold Breaker (move_exec_helpers.cpp:106-108).
    if (ability == AB_STURDY && cur_hp == max_hp) {
        result.thresholds.push_back({max_hp, ThresholdKind::FullHp});
    }

    // Multiscale (136): halves damage when hp==max_hp (damage.cpp:1401-1406).
    if (ability == AB_MULTISCALE && cur_hp == max_hp) {
        result.thresholds.push_back({max_hp, ThresholdKind::FullHp});
    }

    // Shadow Shield (231): halves damage when hp==max_hp (damage.cpp:1409-1416).
    if (ability == AB_SHADOW_SHIELD && cur_hp == max_hp) {
        result.thresholds.push_back({max_hp, ThresholdKind::FullHp});
    }

    // --- Half-HP berries (threshold_denom=2) ---
    // Trigger condition: mon.hp <= max_hp / 2 (effects.cpp:441-442 "threshold_hp = max_hp / threshold_denom;
    // if (mon.hp > threshold_hp) return false").
    // threshold_hp = max_hp / 2 (floor division).
    if (item == ITEM_SITRUS || item == ITEM_ORAN || item == ITEM_BERRY_JUICE) {
        int32_t threshold_hp = max_hp / 2;
        result.thresholds.push_back({threshold_hp, ThresholdKind::Half});
    }

    // --- Quarter-HP berries (threshold_denom=4) and Custap ---
    // Trigger condition: mon.hp <= max_hp / 4.
    // threshold_hp = max_hp / 4 (floor division).
    bool is_quarter_berry = false;
    for (int i = 0; i < N_QUARTER_BERRIES; ++i) {
        if (item == QUARTER_BERRIES[i]) { is_quarter_berry = true; break; }
    }
    if (is_quarter_berry) {
        int32_t threshold_hp = max_hp / 4;
        result.thresholds.push_back({threshold_hp, ThresholdKind::Quarter});
    }

    // Custap Berry (210): consumed at <= max_hp / 4 (core_leaf.cpp:726-728).
    if (item == ITEM_CUSTAP) {
        int32_t threshold_hp = max_hp / 4;
        result.thresholds.push_back({threshold_hp, ThresholdKind::Quarter});
    }

    // --- Unrecognized consumable check ---
    // If the mon holds an item the engine will consume but that this table doesn't model,
    // set residual_unknown=true so analytic callers scope out.
    // We only flag items we know the engine CONSUMES (berries + Focus Band + White Herb).
    // Passive items (Life Orb, Choice Band, etc.) do not set this flag.
    if (item != 0) {
        // Check if already fully modeled above (no unknown).
        bool modeled = (item == ITEM_FOCUS_SASH
                     || item == ITEM_SITRUS || item == ITEM_ORAN || item == ITEM_BERRY_JUICE
                     || item == ITEM_CUSTAP
                     || is_quarter_berry);
        if (!modeled) {
            for (int i = 0; i < N_UNRECOGNIZED; ++i) {
                if (item == UNRECOGNIZED_CONSUMABLES[i]) {
                    result.residual_unknown = true;
                    break;
                }
            }
        }
    }

    return result;
}
