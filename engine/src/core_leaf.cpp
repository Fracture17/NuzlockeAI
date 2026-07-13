// C1.7c: pure leaf helpers ported from src/engine/core.py.
// Variable BP / fixed damage / target resolution + deterministic Psywave roll.
// Includes move_data.h (MoveData.base_power / .target); cpp_effective_stat from damage.h;
// is_grounded from effects_internal.h. Species body weights come from the generated
// species_data.h via cpp_species_weight() (isolated TU; can't include species_data.h here
// directly because it clashes with move_data.h's enum class Type).
#include "core_leaf.h"
#include "damage.h"
#include "effects_internal.h"
#include "species_weight_lookup.h"
#include "forced_trace.h"
#include "rng_resolver.h"   // rng_resolve_psywave_roll_k, rng_resolve_quick_claw

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>

#include <move_data.h>

// Natural Gift item -> BP (mirror src.data.items.NATURAL_GIFT_TABLE second field).
// Defined below; declared here so the BP path can call it.
static bool core_leaf_natural_gift(int32_t item, uint8_t& out_bp);

// Reproduces CPython float.__floordiv__ exactly (mirrors Python int(a // b)).
// Needed because C++ floor(a/b) diverges at IEEE boundaries (e.g. 18.0/3.6).
static double py_float_floordiv(double a, double b) {
    double mod = std::fmod(a, b);
    double div = (a - mod) / b;
    if (mod != 0.0) {
        if ((b < 0.0) != (mod < 0.0)) { div -= 1.0; }
    }
    double floordiv;
    if (div != 0.0) {
        floordiv = std::floor(div);
        if (div - floordiv > 0.5) floordiv += 1.0;
    } else {
        floordiv = std::copysign(0.0, a / b);
    }
    return floordiv;
}

namespace {

// ---------------------------------------------------------------------------
// Enum int constants (mirroring Python IntEnum/IntFlag values).
// ---------------------------------------------------------------------------
// Moves
constexpr int32_t MOVE_POWER_TRIP = 681, MOVE_STORED_POWER = 500, MOVE_PUNISHMENT = 386;
constexpr int32_t MOVE_HEX = 506, MOVE_FACADE = 263, MOVE_ASSURANCE = 372, MOVE_LASH_OUT = 808;
constexpr int32_t MOVE_VENOSHOCK = 474, MOVE_AVALANCHE = 419, MOVE_REVENGE = 279;
constexpr int32_t MOVE_PAYBACK = 371, MOVE_BRINE = 362, MOVE_STOMPING_TANTRUM = 707;
constexpr int32_t MOVE_ACROBATICS = 512, MOVE_FISHIOUS_REND = 755, MOVE_BOLT_BEAK = 754;
constexpr int32_t MOVE_RISING_VOLTAGE = 804, MOVE_GRAV_APPLE = 788, MOVE_SMELLING_SALTS = 265;
constexpr int32_t MOVE_WAKE_UP_SLAP = 358, MOVE_ERUPTION = 284, MOVE_WATER_SPOUT = 323;
constexpr int32_t MOVE_WRING_OUT = 378, MOVE_CRUSH_GRIP = 462, MOVE_FLAIL = 175, MOVE_REVERSAL = 179;
constexpr int32_t MOVE_SPIT_UP = 255, MOVE_GYRO_BALL = 360, MOVE_ELECTRO_BALL = 486;
constexpr int32_t MOVE_HEAVY_SLAM = 484, MOVE_HEAT_CRASH = 535, MOVE_LOW_KICK = 67, MOVE_GRASS_KNOT = 447;
constexpr int32_t MOVE_RETALIATE = 514, MOVE_BODY_SLAM = 34, MOVE_STOMP = 23, MOVE_STEAMROLLER = 537;
constexpr int32_t MOVE_FLYING_PRESS = 560, MOVE_DRAGON_RUSH = 407, MOVE_SUPERCELL_SLAM = 916;
constexpr int32_t MOVE_SOLAR_BEAM = 76, MOVE_SOLAR_BLADE = 669, MOVE_EXPANDING_FORCE = 797;
constexpr int32_t MOVE_NATURAL_GIFT = 363, MOVE_ECHOED_VOICE = 497, MOVE_ROLLOUT = 205, MOVE_ICE_BALL = 301;
// Fixed-damage moves
constexpr int32_t MOVE_DRAGON_RAGE = 82, MOVE_SONIC_BOOM = 49, MOVE_SEISMIC_TOSS = 69, MOVE_NIGHT_SHADE = 101;
constexpr int32_t MOVE_SUPER_FANG = 162, MOVE_NATURES_MADNESS = 717, MOVE_FINAL_GAMBIT = 515;
constexpr int32_t MOVE_ENDEAVOR = 283, MOVE_COUNTER = 68, MOVE_MIRROR_COAT = 243, MOVE_METAL_BURST = 368;
constexpr int32_t MOVE_PSYWAVE = 149;

// Abilities
constexpr int32_t ABILITY_COMATOSE = 213, ABILITY_QUICK_FEET = 95;
constexpr int32_t ABILITY_HEAVY_METAL = 134, ABILITY_LIGHT_METAL = 135;
// Turn-order abilities
constexpr int32_t ABILITY_SWIFT_SWIM = 33, ABILITY_CHLOROPHYLL = 34, ABILITY_GLUTTONY = 82;
constexpr int32_t ABILITY_UNBURDEN = 84, ABILITY_SLOW_START = 112, ABILITY_SAND_RUSH = 146;
constexpr int32_t ABILITY_PRANKSTER = 158, ABILITY_GALE_WINGS = 177, ABILITY_SLUSH_RUSH = 202;
constexpr int32_t ABILITY_TRIAGE = 205, ABILITY_SURGE_SURFER = 207, ABILITY_QUICK_DRAW = 259;
constexpr int32_t ABILITY_MYCELIUM_MIGHT = 298;
constexpr int32_t ABILITY_UNNERVE = 127, ABILITY_AS_ONE_GLASTRIER = 266, ABILITY_AS_ONE_SPECTRIER = 267;

// Status
constexpr int32_t STATUS_NONE = 0, STATUS_BURN = 1, STATUS_FREEZE = 2, STATUS_PARALYSIS = 3;
constexpr int32_t STATUS_POISON = 4, STATUS_TOXIC = 5, STATUS_SLEEP = 6;

// Items
constexpr int32_t ITEM_NONE = 0;
constexpr int32_t ITEM_CUSTAP_BERRY = 210, ITEM_QUICK_CLAW = 217;
constexpr int32_t ITEM_IRON_BALL = 278, ITEM_LAGGING_TAIL = 279, ITEM_CHOICE_SCARF = 287;

// Weather / Terrain / PseudoWeather
constexpr int32_t WEATHER_SUNNY = 1, WEATHER_RAINY = 2, WEATHER_HEAVY_RAIN = 5;
constexpr int32_t WEATHER_SANDSTORM = 3, WEATHER_HAIL = 4, WEATHER_HARSH_SUN = 6;
constexpr int32_t TERRAIN_ELECTRIC = 1, TERRAIN_GRASSY = 2, TERRAIN_PSYCHIC = 3;
constexpr int32_t PSEUDO_GRAVITY = 2, PSEUDO_TRICK_ROOM = 1;

// Status / side conditions / move tags / move category
constexpr int32_t STATUS_NONE_ = 0;
constexpr int32_t SIDE_TAILWIND = 11;
constexpr int32_t MOVETAG_RECOVERY = 4;
constexpr int8_t  MOVECAT_STATUS = 2;
constexpr int32_t FORMAT_DOUBLES = 1;

// ActionKind
constexpr int32_t ACTION_MOVE = 0, ACTION_SWITCH = 1;

// Volatile flags
constexpr int32_t VOL_MINIMIZE = 1024, VOL_DEFENSE_CURL = 2048;
constexpr int32_t VOL_UNBURDEN = 524288;

// MoveTarget
constexpr int8_t TARGET_NORMAL = 0, TARGET_SELF = 1, TARGET_ALL_ADJACENT_FOES = 2;
constexpr int8_t TARGET_ALL_ADJACENT = 3, TARGET_ALLY = 4, TARGET_ANY = 5;
constexpr int8_t TARGET_ALLY_SIDE = 6, TARGET_FOE_SIDE = 7, TARGET_ALL = 8, TARGET_RANDOM_NORMAL = 9;

// Mold breaker family.
bool is_mold_breaker(int32_t ability) {
    return ability == 104 || ability == 163 || ability == 164;
}

constexpr int MOVE_COUNT = 813;

// Returns pointer to MoveData or nullptr (mirrors MOVE_DATA.get(move) -> None).
const MoveData* move_data_get(int32_t move_id) {
    int lo = 0, hi = MOVE_COUNT;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1; else hi = mid;
    }
    if (lo < MOVE_COUNT && MOVE_TABLE[lo].move_id == move_id) return &MOVE_TABLE[lo];
    return nullptr;
}

// Move lookup that throws (mirrors MOVE_DATA[move]) — used by _resolve_targets, where the
// move is always present in tests.
const MoveData& move_data_get_or_throw(int32_t move_id) {
    const MoveData* md = move_data_get(move_id);
    if (md == nullptr)
        throw std::runtime_error("core_leaf: move id " + std::to_string(move_id) + " not found");
    return *md;
}

// stat_stages first 7 entries: ATK,DEF,SPA,SPD,SPE,ACC,EVA.
int32_t stage_at(const PokemonState& m, int i) {
    switch (i) {
        case 0: return m.stage0; case 1: return m.stage1; case 2: return m.stage2;
        case 3: return m.stage3; case 4: return m.stage4; case 5: return m.stage5;
        case 6: return m.stage6; default: return 0;
    }
}

// sum(max(0, s) for s in stat_stages[:7]).
int32_t sum_positive_boosts(const PokemonState& m) {
    int32_t total = 0;
    for (int i = 0; i < 7; ++i) total += std::max(0, stage_at(m, i));
    return total;
}

bool has_pseudo(const BattleState& s, int32_t pw) {
    for (const auto& e : s.pseudo_weather)
        if (e.effect == pw) return true;
    return false;
}

const SideState& side_const(const BattleState& s, int idx) {
    return idx == 0 ? s.side0 : s.side1;
}

// Python round() — banker's rounding (round-half-to-even).
int64_t python_round(double x) {
    double floor_x = std::floor(x);
    double frac = x - floor_x;
    int64_t fl = static_cast<int64_t>(floor_x);
    if (frac < 0.5) return fl;
    if (frac > 0.5) return fl + 1;
    // Exactly .5 -> round to even.
    return (fl % 2 == 0) ? fl : fl + 1;
}

} // namespace

// ---------------------------------------------------------------------------
double cpp_resolve_psywave_roll(const PsywaveLuck& luck) {
    // Python rng.py:393 _roll_uniform(RNGEvent.PSYWAVE_ROLL)
    if (luck.random_mode) {
        if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (luck.rng->forced)
            return luck.rng->forced->force_double(luck.rng->current_turn, RngEventC::PSYWAVE_ROLL);
        return luck.rng->random();
    }
    return luck.psywave_roll;
}

// ---------------------------------------------------------------------------
int32_t cpp_compute_variable_bp(int32_t move, const PokemonState& attacker,
                                const PokemonState& defender, const BattleState& state,
                                int side_idx, int defender_idx,
                                bool defender_action_is_switch) {
    const MoveData* md = move_data_get(move);
    if (md == nullptr) return 0;
    int32_t base = md->base_power;

    if (move == MOVE_POWER_TRIP || move == MOVE_STORED_POWER)
        return 20 + 20 * sum_positive_boosts(attacker);

    if (move == MOVE_PUNISHMENT)
        return std::min(200, 60 + 20 * sum_positive_boosts(defender));

    if (move == MOVE_HEX) {
        bool has_status = (defender.status != STATUS_NONE || defender.ability == ABILITY_COMATOSE);
        return has_status ? base * 2 : 0;
    }

    if (move == MOVE_FACADE) {
        bool s = (attacker.status == STATUS_BURN || attacker.status == STATUS_POISON
                  || attacker.status == STATUS_TOXIC || attacker.status == STATUS_PARALYSIS
                  || attacker.status == STATUS_FREEZE);
        return s ? base * 2 : 0;
    }

    if (move == MOVE_ASSURANCE)
        return defender.took_damage_this_turn ? base * 2 : 0;

    if (move == MOVE_LASH_OUT)
        return attacker.had_stat_lowered_this_turn ? base * 2 : 0;

    if (move == MOVE_VENOSHOCK)
        return (defender.status == STATUS_POISON || defender.status == STATUS_TOXIC) ? base * 2 : 0;

    if (move == MOVE_AVALANCHE || move == MOVE_REVENGE)
        return attacker.took_damage_this_turn ? base * 2 : 0;

    if (move == MOVE_PAYBACK) {
        bool acted_second = (state.turn_order.size() >= 2 && state.turn_order[1] == side_idx);
        return acted_second ? base * 2 : 0;
    }

    if (move == MOVE_BRINE)
        return defender.hp <= defender.max_hp / 2 ? base * 2 : 0;

    if (move == MOVE_STOMPING_TANTRUM)
        return attacker.last_move_failed ? base * 2 : 0;

    if (move == MOVE_ACROBATICS)
        return attacker.item == ITEM_NONE ? base * 2 : 0;

    if (move == MOVE_FISHIOUS_REND || move == MOVE_BOLT_BEAK) {
        bool acted_first = (!state.turn_order.empty() && state.turn_order[0] == side_idx);
        bool target_just_switched_in = (defender_idx >= 0 && defender_action_is_switch);
        return (acted_first || target_just_switched_in) ? base * 2 : 0;
    }

    if (move == MOVE_RISING_VOLTAGE) {
        if (state.terrain == TERRAIN_ELECTRIC && eff_internal::is_grounded(defender, state))
            return base * 2;
        return 0;
    }

    if (move == MOVE_GRAV_APPLE) {
        if (has_pseudo(state, PSEUDO_GRAVITY)) return base * 3 / 2;
        return 0;
    }

    if (move == MOVE_SMELLING_SALTS)
        return defender.status == STATUS_PARALYSIS ? base * 2 : 0;

    if (move == MOVE_WAKE_UP_SLAP) {
        bool asleep = (defender.status == STATUS_SLEEP || defender.ability == ABILITY_COMATOSE);
        return asleep ? base * 2 : 0;
    }

    if (move == MOVE_ERUPTION || move == MOVE_WATER_SPOUT)
        return std::max(1, 150 * attacker.hp / attacker.max_hp);

    if (move == MOVE_WRING_OUT)
        return std::max(1, 120 * defender.hp / defender.max_hp + 1);

    if (move == MOVE_CRUSH_GRIP)
        return std::max(1, 120 * defender.hp / defender.max_hp);

    if (move == MOVE_FLAIL || move == MOVE_REVERSAL) {
        int32_t ratio = attacker.hp * 48 / attacker.max_hp;
        if (ratio < 2) return 200;
        if (ratio < 6) return 150;
        if (ratio < 13) return 100;
        if (ratio < 22) return 80;
        if (ratio < 30) return 40;
        return 20;
    }

    if (move == MOVE_SPIT_UP)
        return 100 * attacker.stockpile_count;

    if (move == MOVE_GYRO_BALL) {
        int32_t def_spd = cpp_effective_stat(defender, 5);
        int32_t atk_spd = cpp_effective_stat(attacker, 5);
        if (attacker.status == STATUS_PARALYSIS && attacker.ability != ABILITY_QUICK_FEET)
            atk_spd = std::max(1, atk_spd / 4);
        if (defender.status == STATUS_PARALYSIS && defender.ability != ABILITY_QUICK_FEET)
            def_spd = std::max(1, def_spd / 4);
        return std::min(150, 25 * def_spd / std::max(1, atk_spd) + 1);
    }

    if (move == MOVE_ELECTRO_BALL) {
        int32_t atk_spd = cpp_effective_stat(attacker, 5);
        int32_t def_spd = cpp_effective_stat(defender, 5);
        if (attacker.status == STATUS_PARALYSIS && attacker.ability != ABILITY_QUICK_FEET)
            atk_spd = std::max(1, atk_spd / 4);
        if (defender.status == STATUS_PARALYSIS && defender.ability != ABILITY_QUICK_FEET)
            def_spd = std::max(1, def_spd / 4);
        int32_t ratio = atk_spd / std::max(1, def_spd);
        if (ratio >= 4) return 150;
        if (ratio >= 3) return 120;
        if (ratio >= 2) return 80;
        if (ratio >= 1) return 60;
        return 40;
    }

    // Weight-based BP (Autotomize floors at 0.1 kg).
    double atk_weight = std::max(0.1, cpp_species_weight(attacker.species) - attacker.weight_kg_reduced);
    double def_weight = std::max(0.1, cpp_species_weight(defender.species) - defender.weight_kg_reduced);

    if (move == MOVE_HEAVY_SLAM || move == MOVE_HEAT_CRASH) {
        if (defender.ability == ABILITY_HEAVY_METAL && !is_mold_breaker(attacker.ability))
            def_weight *= 2;
        else if (defender.ability == ABILITY_LIGHT_METAL && !is_mold_breaker(attacker.ability))
            def_weight /= 2;
        int32_t hs_bp;
        if (def_weight <= 0) {
            hs_bp = 40;
        } else {
            int32_t ratio = static_cast<int32_t>(py_float_floordiv(atk_weight, def_weight));
            if (ratio >= 5) hs_bp = 120;
            else if (ratio >= 4) hs_bp = 100;
            else if (ratio >= 3) hs_bp = 80;
            else if (ratio >= 2) hs_bp = 60;
            else hs_bp = 40;
        }
        return (defender.volatiles & VOL_MINIMIZE) ? hs_bp * 2 : hs_bp;
    }

    if (move == MOVE_LOW_KICK || move == MOVE_GRASS_KNOT) {
        if (defender.ability == ABILITY_HEAVY_METAL && !is_mold_breaker(attacker.ability))
            def_weight *= 2;
        else if (defender.ability == ABILITY_LIGHT_METAL && !is_mold_breaker(attacker.ability))
            def_weight /= 2;
        if (def_weight < 10) return 20;
        if (def_weight < 25) return 40;
        if (def_weight < 50) return 60;
        if (def_weight < 100) return 80;
        if (def_weight < 200) return 100;
        return 120;
    }

    if (move == MOVE_RETALIATE) {
        if (side_const(state, side_idx).ally_fainted_last_turn) return base * 2;
        return 0;
    }

    if (move == MOVE_BODY_SLAM || move == MOVE_STOMP || move == MOVE_STEAMROLLER
        || move == MOVE_FLYING_PRESS || move == MOVE_DRAGON_RUSH || move == MOVE_SUPERCELL_SLAM)
        return 0;

    if (move == MOVE_SOLAR_BEAM || move == MOVE_SOLAR_BLADE) {
        if (state.weather == WEATHER_RAINY || state.weather == WEATHER_HEAVY_RAIN
            || state.weather == WEATHER_SANDSTORM || state.weather == WEATHER_HAIL)
            return base / 2;
        return 0;
    }

    if (move == MOVE_EXPANDING_FORCE) {
        if (state.terrain == TERRAIN_PSYCHIC && eff_internal::is_grounded(attacker, state))
            return base * 3 / 2;
        return 0;
    }

    if (move == MOVE_NATURAL_GIFT) {
        uint8_t ng_bp;
        if (core_leaf_natural_gift(attacker.item, ng_bp)) return ng_bp;
        return 0;
    }

    if (move == MOVE_ECHOED_VOICE)
        return 40 * (state.echoed_voice_multiplier + 1);

    if (move == MOVE_ROLLOUT || move == MOVE_ICE_BALL) {
        int32_t bp_rollout = 30 * (1 << attacker.rollout_hits);
        if (attacker.defense_curl_used || (attacker.volatiles & VOL_DEFENSE_CURL))
            bp_rollout *= 2;
        return bp_rollout;
    }

    return 0;
}

static bool core_leaf_natural_gift(int32_t item, uint8_t& out_bp) {
    static const struct { int32_t item; uint8_t bp; } TABLE[] = {
        {149, 60}, {150, 60}, {151, 60}, {152, 60}, {153, 60}, {154, 60},
        {155, 60}, {156, 60}, {157, 80}, {158, 80}, {159, 80}, {160, 80},
        {161, 80}, {162, 80}, {163, 80}, {184, 80}, {185, 80}, {186, 80},
        {187, 80}, {188, 80}, {189, 80}, {190, 80}, {191, 80}, {192, 80},
        {193, 80}, {194, 80}, {195, 80}, {196, 80}, {197, 80}, {198, 80},
        {199, 80}, {200, 80}, {201, 100}, {202, 100}, {203, 100}, {204, 100},
        {205, 100}, {206, 100}, {207, 100}, {208, 100}, {209, 100}, {210, 100},
        {211, 100}, {212, 100}, {686, 80}, {687, 100}, {688, 100},
    };
    constexpr int N = sizeof(TABLE) / sizeof(TABLE[0]);
    for (int i = 0; i < N; ++i) {
        if (TABLE[i].item == item) { out_bp = TABLE[i].bp; return true; }
    }
    return false;
}

// ---------------------------------------------------------------------------
int32_t cpp_compute_fixed_damage(int32_t move, const PokemonState& attacker,
                                 const PokemonState& defender, const BattleState& /*state*/,
                                 int /*side_idx*/, const PsywaveLuck& luck) {
    if (move == MOVE_DRAGON_RAGE) return 40;
    if (move == MOVE_SONIC_BOOM) return 20;
    if (move == MOVE_SEISMIC_TOSS || move == MOVE_NIGHT_SHADE) return attacker.level;
    if (move == MOVE_SUPER_FANG || move == MOVE_NATURES_MADNESS)
        return std::max(1, defender.hp / 2);
    if (move == MOVE_FINAL_GAMBIT) return attacker.hp;
    if (move == MOVE_ENDEAVOR) {
        int32_t dmg = defender.hp - attacker.hp;
        if (dmg <= 0) return -2;
        return dmg;
    }
    if (move == MOVE_COUNTER) {
        if (attacker.last_physical_damage_taken <= 0) return -2;
        return std::max(1, attacker.last_physical_damage_taken * 2);
    }
    if (move == MOVE_MIRROR_COAT) {
        if (attacker.last_special_damage_taken <= 0) return -2;
        return std::max(1, attacker.last_special_damage_taken * 2);
    }
    if (move == MOVE_METAL_BURST) {
        if (attacker.last_damage_taken <= 0) return -2;
        return std::max(1, attacker.last_damage_taken * 3 / 2);
    }
    if (move == MOVE_PSYWAVE) {
        // Use occurrence-keyed resolver: k = python_round(roll*100) in [0,100].
        // Endpoints k=0,100 have p=1/200; interior have p=1/100.
        int k = rng_resolve_psywave_roll_k(luck.random_mode, luck.rng, luck.psywave_roll);
        int64_t roll_int = 50 + static_cast<int64_t>(k);
        return static_cast<int32_t>(std::max<int64_t>(1, roll_int * attacker.level / 100));
    }
    return -1;
}

// Mirrors core.py _FIXED_DAMAGE_MOVES: moves handled by cpp_compute_fixed_damage
// (returns != -1). All are single-target NORMAL moves, so resolving their doubles
// target is draw-free.
bool cpp_is_fixed_damage_move(int32_t move) {
    return move == MOVE_DRAGON_RAGE || move == MOVE_SONIC_BOOM
        || move == MOVE_SEISMIC_TOSS || move == MOVE_NIGHT_SHADE
        || move == MOVE_SUPER_FANG || move == MOVE_NATURES_MADNESS
        || move == MOVE_FINAL_GAMBIT || move == MOVE_ENDEAVOR
        || move == MOVE_COUNTER || move == MOVE_MIRROR_COAT
        || move == MOVE_METAL_BURST || move == MOVE_PSYWAVE;
}

// ---------------------------------------------------------------------------
std::vector<std::pair<int32_t, int32_t>> cpp_resolve_targets(
    const BattleState& state, int side_idx, int source_slot,
    int32_t move, int target_side, int target_slot,
    bool random_mode, NativeRng* rng) {
    const MoveData& md = move_data_get_or_throw(move);
    int8_t target = md.target;
    int foe_idx = 1 - side_idx;

    auto active_slots = [&](int side_idx_) -> std::vector<int> {
        const SideState& side = side_const(state, side_idx_);
        std::vector<int> out;
        for (size_t pos = 0; pos < side.active_indices.size(); ++pos) {
            int team_idx = side.active_indices[pos];
            if (!side.team[team_idx].fainted) out.push_back(static_cast<int>(pos));
        }
        return out;
    };

    std::vector<std::pair<int32_t, int32_t>> result;

    if (target == TARGET_SELF) {
        result.push_back({side_idx, source_slot});
        return result;
    }
    if (target == TARGET_ALLY_SIDE || target == TARGET_FOE_SIDE) {
        return result;  // empty
    }
    if (target == TARGET_ALL) {
        for (int pos : active_slots(side_idx)) result.push_back({side_idx, pos});
        for (int pos : active_slots(foe_idx)) result.push_back({foe_idx, pos});
        return result;
    }
    if (target == TARGET_ALL_ADJACENT_FOES) {
        for (int pos : active_slots(foe_idx)) result.push_back({foe_idx, pos});
        return result;
    }
    if (target == TARGET_ALL_ADJACENT) {
        for (int pos : active_slots(foe_idx)) result.push_back({foe_idx, pos});
        for (int pos : active_slots(side_idx))
            if (pos != source_slot) result.push_back({side_idx, pos});
        return result;
    }
    if (target == TARGET_RANDOM_NORMAL) {
        // Python rng.py:568-576: len==1 → no draw; len>=2 → categorical draw.
        // Forced mode with multi-foe: consume RANDOM_TARGET int (the chosen foe slot).
        std::vector<int> foe_slots = active_slots(foe_idx);
        if (foe_slots.empty()) return result;
        if (foe_slots.size() > 1) {
            if (!random_mode) {
                throw std::runtime_error("unported: RANDOM_NORMAL random.choice (multi-foe)");
            }
            if (!rng) throw std::runtime_error("random_mode=true but rng=nullptr in cpp_resolve_targets");
            if (rng->forced) {
                // rng.py:576 _roll_categorical(RNGEvent.RANDOM_TARGET, foe_slots) records chosen slot
                int chosen = static_cast<int>(rng->forced->force_int(rng->current_turn, RngEventC::RANDOM_TARGET));
                result.push_back({foe_idx, chosen});
            } else {
                result.push_back({foe_idx, rng->choice(foe_slots)});
            }
            return result;
        }
        result.push_back({foe_idx, foe_slots[0]});
        return result;
    }
    if (target == TARGET_NORMAL) {
        std::vector<int> foe_slots = active_slots(foe_idx);
        if (foe_slots.empty()) return result;
        for (int s : foe_slots)
            if (s == target_slot) { result.push_back({foe_idx, target_slot}); return result; }
        result.push_back({foe_idx, foe_slots[0]});
        return result;
    }
    if (target == TARGET_ANY) {
        int t_side = target_side >= 0 ? target_side : foe_idx;
        std::vector<int> t_slots = active_slots(t_side);
        for (int s : t_slots)
            if (s == target_slot) { result.push_back({t_side, target_slot}); return result; }
        return result;  // ANY does not auto-retarget
    }
    if (target == TARGET_ALLY) {
        std::vector<int> ally_slots;
        for (int pos : active_slots(side_idx))
            if (pos != source_slot) ally_slots.push_back(pos);
        if (ally_slots.empty()) return result;
        for (int s : ally_slots)
            if (s == target_slot) { result.push_back({side_idx, target_slot}); return result; }
        result.push_back({side_idx, ally_slots[0]});
        return result;
    }
    // Fallback: treat as NORMAL.
    std::vector<int> foe_slots = active_slots(foe_idx);
    if (foe_slots.empty()) return result;
    result.push_back({foe_idx, foe_slots[0]});
    return result;
}

bool cpp_move_has_target(const BattleState& state, int side_idx, int source_slot,
                         int32_t move, int target_side, int target_slot) {
    // Mirrors core.py _move_has_target: true if the move has at least one live
    // target. Draw-free — must NOT consume the RANDOM_NORMAL target roll.
    // SELF and side-condition targets (ALLY_SIDE/FOE_SIDE) never require one.
    const MoveData& md = move_data_get_or_throw(move);
    int8_t target = md.target;
    if (target == TARGET_SELF || target == TARGET_ALLY_SIDE || target == TARGET_FOE_SIDE)
        return true;
    if (target == TARGET_ALL) return true;  // includes the user itself
    int foe_idx = 1 - side_idx;

    auto live_slots = [&](int side_idx_) -> std::vector<int> {
        const SideState& side = side_const(state, side_idx_);
        std::vector<int> out;
        for (size_t pos = 0; pos < side.active_indices.size(); ++pos) {
            int team_idx = side.active_indices[pos];
            if (!side.team[team_idx].fainted) out.push_back(static_cast<int>(pos));
        }
        return out;
    };

    if (target == TARGET_ANY) {
        int t_side = target_side >= 0 ? target_side : foe_idx;
        for (int s : live_slots(t_side))
            if (s == target_slot) return true;  // ANY does not retarget
        return false;
    }
    if (target == TARGET_ALLY) {
        for (int pos : live_slots(side_idx))
            if (pos != source_slot) return true;
        return false;
    }
    if (target == TARGET_ALL_ADJACENT) {
        if (!live_slots(foe_idx).empty()) return true;
        for (int pos : live_slots(side_idx))
            if (pos != source_slot) return true;
        return false;
    }
    // NORMAL, RANDOM_NORMAL, ALL_ADJACENT_FOES, fallback: need a live foe.
    return !live_slots(foe_idx).empty();
}

// ===========================================================================
// C1.7c Unit B: turn-order helpers (_check_priority_item / _build_queue chain).
// ===========================================================================
namespace {

// Mutable side/active accessors over BattleState storage (side0/side1 ARE the lists).
SideState& side_mut(BattleState& s, int idx) { return idx == 0 ? s.side0 : s.side1; }

PokemonState& active_slot_mut(BattleState& s, int side_idx, int slot) {
    SideState& side = side_mut(s, side_idx);
    return side.team[side.active_indices[slot]];
}
const PokemonState& active_slot_c(const BattleState& s, int side_idx, int slot) {
    const SideState& side = side_const(s, side_idx);
    return side.team[side.active_indices[slot]];
}

// move_ids[slot] accessor (PokemonState stores moves as move_id0..move_id3).
int32_t move_id_at(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_id0; case 1: return m.move_id1;
        case 2: return m.move_id2; case 3: return m.move_id3; default: return 0;
    }
}

bool is_protect_move(int32_t m) {
    // _PROTECT_MOVES (src/data/moves.py).
    switch (m) {
        case 182: case 197: case 455: case 588: case 596: case 661: case 792:  // protect family
        case 469: case 501:                                                    // Wide/Quick Guard
            return true;
        default: return false;
    }
}
constexpr int32_t MOVE_GRASSY_GLIDE = 803, MOVE_WIDE_GUARD = 469, MOVE_QUICK_GUARD = 501;
constexpr int32_t TYPE_FLYING = 9;

bool is_berry_suppressor(int32_t ability) {
    return ability == ABILITY_UNNERVE || ability == ABILITY_AS_ONE_GLASTRIER
           || ability == ABILITY_AS_ONE_SPECTRIER;
}

// resolve_quick_claw_det: wrapper that threads TurnLuck into the occurrence-keyed resolver.
bool resolve_quick_claw_det(const TurnLuck& luck) {
    return rng_resolve_quick_claw(luck.random_mode, luck.rng, luck.quick_claw_threshold);
}

// _triage_priority_bump.
int32_t triage_priority_bump(int32_t ability, const MoveData& md) {
    if (ability != ABILITY_TRIAGE) return 0;
    bool recovery = (md.tags & MOVETAG_RECOVERY) != 0;
    bool drain = md.drain_num != -1;
    return (recovery || drain) ? 3 : 0;
}

}  // namespace

// _effective_speed — mirror src/engine/_helpers.py operation-for-operation.
int32_t cpp_effective_speed(const PokemonState& mon, const SideState& side,
                            const BattleState& state) {
    int32_t spe = cpp_effective_stat(mon, 5);
    if (mon.ability == ABILITY_QUICK_FEET && mon.status != STATUS_NONE_)
        spe = static_cast<int32_t>(spe * 1.5);
    else if (mon.status == 3 /* PARALYSIS */)
        spe = std::max(1, spe / 4);
    for (const auto& sc : side.side_conditions)
        if (sc.condition == SIDE_TAILWIND) { spe *= 2; break; }
    int32_t eff_w = eff_internal::effective_weather(state);
    if (mon.ability == ABILITY_SWIFT_SWIM && eff_w == WEATHER_RAINY)
        spe *= 2;
    else if (mon.ability == ABILITY_CHLOROPHYLL
             && (eff_w == WEATHER_SUNNY || eff_w == WEATHER_HARSH_SUN))
        spe *= 2;
    else if (mon.ability == ABILITY_SAND_RUSH && eff_w == WEATHER_SANDSTORM)
        spe *= 2;
    else if (mon.ability == ABILITY_SLUSH_RUSH && eff_w == WEATHER_HAIL)
        spe *= 2;
    else if (mon.ability == ABILITY_SURGE_SURFER && state.terrain == TERRAIN_ELECTRIC)
        spe *= 2;
    if (mon.ability == ABILITY_SLOW_START && mon.turns_in_battle < 5)
        spe = spe / 2;
    if ((mon.volatiles & VOL_UNBURDEN) && mon.item == ITEM_NONE)
        spe *= 2;
    if (mon.item == ITEM_LAGGING_TAIL)
        return -9999;
    if (mon.item == ITEM_CHOICE_SCARF)
        spe = static_cast<int32_t>(spe * 1.5);
    else if (mon.item == ITEM_IRON_BALL)
        spe = std::max(1, spe / 2);
    return std::max(1, spe);
}

// _has_trick_room.
static bool has_trick_room(const BattleState& s) {
    for (const auto& e : s.pseudo_weather)
        if (e.effect == PSEUDO_TRICK_ROOM) return true;
    return false;
}

// _check_priority_item — mutates state (Custap consumed). Returns the bool.
bool cpp_check_priority_item(BattleState& state, int side_idx, const ActionC& action,
                             const TurnLuck& luck, int source_slot) {
    PokemonState& pokemon = active_slot_mut(state, side_idx, source_slot);
    int32_t move_priority;
    if (action.move_slot < 0) {
        move_priority = 0;
    } else {
        int32_t move = move_id_at(pokemon, action.move_slot);
        const MoveData* md = move_data_get(move);
        move_priority = md ? md->priority : 0;
    }
    if (move_priority > 0) return false;
    if (pokemon.ability == ABILITY_MYCELIUM_MIGHT && action.move_slot >= 0) {
        int32_t move = move_id_at(pokemon, action.move_slot);
        const MoveData* md = move_data_get(move);
        if (md && md->category == MOVECAT_STATUS) return false;
    }
    if (pokemon.item == ITEM_QUICK_CLAW) {
        return resolve_quick_claw_det(luck);  // log() omitted (not compared)
    }
    if (pokemon.item == ITEM_CUSTAP_BERRY) {
        int opp_idx = 1 - side_idx;
        const PokemonState& opp = active_slot_c(state, opp_idx, 0);
        if (is_berry_suppressor(opp.ability)) return false;
        int32_t threshold = (pokemon.ability == ABILITY_GLUTTONY)
                                ? pokemon.max_hp / 2 : pokemon.max_hp / 4;
        if (pokemon.hp <= threshold) {
            pokemon.item = ITEM_NONE;  // Custap consumed
            return true;
        }
    }
    return false;
}

namespace {

// Sort key mirroring _action_sort_key: (move_priority, speed_key, tie). Higher sorts earlier.
struct SortKey {
    int32_t move_priority;
    int32_t speed_key;
    double  tie;
    bool top_two_equal(const SortKey& o) const {
        return move_priority == o.move_priority && speed_key == o.speed_key;
    }
    // Returns true if *this is strictly "earlier" (greater) than o, mirroring reverse sort.
    bool greater(const SortKey& o) const {
        if (move_priority != o.move_priority) return move_priority > o.move_priority;
        if (speed_key != o.speed_key) return speed_key > o.speed_key;
        return tie > o.tie;
    }
    bool equal(const SortKey& o) const {
        return move_priority == o.move_priority && speed_key == o.speed_key && tie == o.tie;
    }
};

// Resolve Quick Draw ONCE per Entry (action_sort_key is called O(n^2) + in the sort
// comparator, so a per-call random draw would be inconsistent). Controlled mode matches
// Python: fires only when secondary_threshold <= 30.0 (GOOD-only real-game). random_mode is
// an INTENTIONAL C++-only divergence: Python never fires QD in random_mode (secondary_threshold
// stays 50.0), but C++ fires 30% via native RNG. See RECORDS/INTENTIONAL_DIVERGENCES.md.
bool resolve_quick_draw(const BattleState& state, int side_idx, int source_slot,
                        const ActionC& a, const TurnLuck& luck) {
    if (a.kind != ACTION_MOVE || a.move_slot < 0)
        return false;
    const PokemonState& attacker = active_slot_c(state, side_idx, source_slot);
    if (attacker.ability != ABILITY_QUICK_DRAW)
        return false;
    const MoveData* md = move_data_get(move_id_at(attacker, a.move_slot));
    if (!(md && md->category != MOVECAT_STATUS))
        return false;
    if (luck.random_mode) {
        if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        // INTENTIONAL_DIVERGENCES.md #1: Quick Draw has no Python record in forced mode.
        // In forced replay return false (never fires) without consuming a trace entry.
        if (luck.rng->forced) return false;
        return luck.rng->random() < 0.3;
    }
    return luck.secondary_threshold <= 30.0;
}

// _action_sort_key for one entry against current state.
SortKey action_sort_key(const BattleState& state, const Entry& e) {
    if (e.action.kind == ACTION_SWITCH)
        return {7, 0, 0.0};
    const PokemonState& attacker = active_slot_c(state, e.side_idx, e.source_slot);
    int32_t slot = e.action.move_slot;
    int32_t move_priority;
    int32_t move = -1;
    if (slot < 0) {
        move_priority = 0;
    } else {
        move = move_id_at(attacker, slot);
        const MoveData* md = move_data_get(move);
        move_priority = md ? md->priority : 0;
        if (is_protect_move(move) && move != MOVE_WIDE_GUARD && move != MOVE_QUICK_GUARD)
            move_priority = 4;
        if (attacker.ability == ABILITY_GALE_WINGS && md && md->move_type == TYPE_FLYING)
            move_priority += 1;
        if (attacker.ability == ABILITY_PRANKSTER && md && md->category == MOVECAT_STATUS)
            move_priority += 1;
        if (md)
            move_priority += triage_priority_bump(attacker.ability, *md);
        if (move == MOVE_GRASSY_GLIDE && state.terrain == TERRAIN_GRASSY
            && eff_internal::is_grounded(attacker, state))
            move_priority += 1;
    }
    int32_t speed;
    if (e.action.kind == ACTION_MOVE && (e.priority_item_fires || e.quick_draw_fires))
        speed = 9999;
    else
        speed = cpp_effective_speed(attacker, side_const(state, e.side_idx), state);
    bool tr = has_trick_room(state);
    int32_t speed_key = tr ? -speed : speed;
    return {move_priority, speed_key, e.tie};
}

// _tiebreaker (core.py:336): random_mode draws rng->random() per-side; else luck_tier as float.
// Forced mode: consume SPEED_TIEBREAKER float from trace (rng.py:564 per-side uniform draw).
double tiebreaker(const TurnLuck& luck) {
    if (luck.random_mode) {
        if (!luck.rng) throw std::runtime_error("random_mode=true but rng=nullptr (misconfiguration)");
        if (luck.rng->forced)
            // rng.py:564 _roll_uniform(RNGEvent.SPEED_TIEBREAKER) per action
            return luck.rng->forced->force_double(luck.rng->current_turn, RngEventC::SPEED_TIEBREAKER);
        return luck.rng->random();
    }
    return static_cast<double>(luck.luck_tier);
}

int effective_source_slot_for_action(const ActionC& a) {
    if (a.kind == ACTION_SWITCH)
        return a.target_slot != 0 ? a.target_slot : a.source_slot;
    return a.source_slot;
}

// SPEED_TIE ordering resolution: rank of (side,slot) in the override ordering, converted to a
// tie value where an EARLIER position sorts first (larger value under SortKey::greater). Only
// the tie field is affected, so entries that aren't truly tied on (priority,speed) are unmoved.
// Fail-loud if a tied slot is absent from the ordering (the override must cover every slot).
double speed_tie_value_from_order(const SpeedTieOrder& sto, int side_idx, int source_slot) {
    for (size_t pos = 0; pos < sto.order.size(); ++pos)
        if (sto.order[pos].first == side_idx && sto.order[pos].second == source_slot)
            return static_cast<double>(sto.order.size() - pos);
    throw std::runtime_error("speed_tie override ordering missing slot ("
        + std::to_string(side_idx) + "," + std::to_string(source_slot) + ")");
}

// Encode the orderable set as side*10+slot for the NeedsRNG options (doubles-ready); the caller
// returns a full ordering of these slots via {"order":[[side,slot],...]}.
std::vector<int> encode_speed_tie_options(const std::vector<Entry>& entries) {
    std::vector<int> opts;
    for (const auto& e : entries) opts.push_back(e.side_idx * 10 + e.source_slot);
    std::sort(opts.begin(), opts.end());
    opts.erase(std::unique(opts.begin(), opts.end()), opts.end());
    return opts;
}

}  // namespace

// cpp_build_pending_entries: resolve tiebreaker, priority item, and Quick Draw once per entry.
// MUTATES state (Custap consumed). Does NOT sort or check speed ties.
// Python _build_pending_entries was deleted; tiebreaker mirrors _build_queue's resolve_speed_tiebreaker.
std::vector<Entry> cpp_build_pending_entries(
    BattleState& state,
    const std::vector<ActionC>& actions_p1, const std::vector<ActionC>& actions_p2,
    const TurnLuck& luck_p1, const TurnLuck& luck_p2) {

    std::vector<Entry> pending;
    auto build_side = [&](int side_idx, const std::vector<ActionC>& actions, const TurnLuck& luck) {
        for (const auto& a : actions) {
            int ss = effective_source_slot_for_action(a);
            double tb = tiebreaker(luck);
            bool pif = (a.kind == ACTION_MOVE)
                       && cpp_check_priority_item(state, side_idx, a, luck, ss);
            bool qdf = resolve_quick_draw(state, side_idx, ss, a, luck);
            pending.push_back({side_idx, ss, a, luck, tb, pif, qdf});
        }
    };
    build_side(0, actions_p1, luck_p1);
    build_side(1, actions_p2, luck_p2);
    return pending;
}

// _select_next_action: pick and erase the highest-priority entry from pending against current state.
// Mirrors Python _select_next_action: detects speed ties (controlled → throw; random_mode → native),
// then picks the FIRST entry achieving the max sort key (matches Python max + stable_sort first-wins).
Entry cpp_select_next_action(const BattleState& state, std::vector<Entry>& pending,
                             const OracleOverrides* overrides,
                             const SpeedTieOrder* forced_tie) {
    if (pending.empty())
        throw std::runtime_error("cpp_select_next_action called with empty pending");

    // SPEED_TIE oracle. Consult transient first (resume replay), then the persistent
    // consumable queue (each occurrence pops one ordering), then detect and throw
    // NeedsRNG for unresolved controlled cross-side ties.
    if (overrides && overrides->transient_tie_cursor < overrides->transient_ties.size()) {
        const SpeedTieOrder& sto = overrides->transient_ties[overrides->transient_tie_cursor++];
        for (Entry& e : pending)
            e.tie = speed_tie_value_from_order(sto, e.side_idx, e.source_slot);
    } else if (overrides &&
               overrides->persistent_tie_cursor < overrides->speed_tie_queue.size()) {
        const SpeedTieOrder& sto =
            overrides->speed_tie_queue[overrides->persistent_tie_cursor++];
        for (Entry& e : pending)
            e.tie = speed_tie_value_from_order(sto, e.side_idx, e.source_slot);
    } else if (pending.size() > 1) {
        bool forced_applied = false;
        for (size_t i = 0; i < pending.size() && !forced_applied; ++i)
            for (size_t j = i + 1; j < pending.size(); ++j)
                if (action_sort_key(state, pending[i]).top_two_equal(
                        action_sort_key(state, pending[j]))) {
                    if (pending[i].luck.random_mode || pending[j].luck.random_mode)
                        continue;  // native tiebreaker (tie field) resolves it
                    bool cross_side = pending[i].side_idx != pending[j].side_idx;
                    bool both_moves = pending[i].action.kind == ACTION_MOVE
                                   && pending[j].action.kind == ACTION_MOVE;
                    if (cross_side && both_moves) {
                        // Plain-mode sweep hook: resolve the controlled tie by the forced ordering
                        // instead of pausing. Sticky (re-fired for every tie this turn), applied to
                        // ALL entries so multi-entry ties resolve consistently. Fail-loud if the
                        // ordering omits any tied slot (speed_tie_value_from_order throws).
                        if (forced_tie) {
                            for (Entry& e : pending)
                                e.tie = speed_tie_value_from_order(*forced_tie, e.side_idx, e.source_slot);
                            forced_applied = true;
                            break;
                        }
                        throw NeedsRNG{RngEventC::SPEED_TIE, encode_speed_tie_options(pending)};
                    }
                    // Same-side or switch ties: stable sort / first-max pick handles them.
                }
    }

    // Pick first entry achieving the strict max (matches Python max() first-element-wins semantics
    // and the existing stable_sort descending first-wins order).
    size_t best_idx = 0;
    for (size_t i = 1; i < pending.size(); ++i)
        if (action_sort_key(state, pending[i]).greater(action_sort_key(state, pending[best_idx])))
            best_idx = i;

    Entry best = pending[best_idx];

    // Analytical SPEED_TIE log: when >=2 entries tie on (priority, speed) the outcome IS an
    // ordering decision. Log the resolution so the solver's RNG-bucketing sees speed ties as
    // Cat-B draws. Encoding: chosen = winner's side*10+slot, options = sorted codes of the
    // tied entries; participants = (winner, first tied loser). Only emitted when the winning
    // set has >= 2 entries (a real tie); if pending.size() == 1 no tie exists.
    if (pending.size() > 1) {
        std::vector<int> tied_codes;
        int loser_side = -1, loser_slot = -1;
        for (size_t i = 0; i < pending.size(); ++i) {
            if (i == best_idx) {
                tied_codes.push_back(pending[i].side_idx * 10 + pending[i].source_slot);
            } else if (action_sort_key(state, pending[i]).top_two_equal(
                           action_sort_key(state, pending[best_idx]))) {
                tied_codes.push_back(pending[i].side_idx * 10 + pending[i].source_slot);
                if (loser_side < 0) { loser_side = pending[i].side_idx;
                                      loser_slot = pending[i].source_slot; }
            }
        }
        if (tied_codes.size() >= 2) {
            std::sort(tied_codes.begin(), tied_codes.end());
            const RngParticipants who{
                (int8_t)best.side_idx, (int8_t)best.source_slot,
                (int8_t)loser_side, (int8_t)loser_slot};
            analytical_rng_log_draw(state.turn_number,
                                    static_cast<int>(RngEventC::SPEED_TIE),
                                    who,
                                    best.side_idx * 10 + best.source_slot,
                                    tied_codes.data(), tied_codes.size());
        }
    }

    pending.erase(pending.begin() + static_cast<std::ptrdiff_t>(best_idx));
    return best;
}
