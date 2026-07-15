// Expand(bucket A, player_move) → AND-set of child buckets, per SOLVER_BUCKET_PLAN
// Task 5. Pipeline (in strict order):
//   1. Support gate on A (LO/HI corners must share the p>0 action set AND match
//      A.support_fp()).
//   2. Concede seam (Task 6 fills in; null here => never concede).
//   3. Per-move damage-table check (§5.2 HP-dependent screen) + weak crit dominance
//      assertion.
//   4. Derived input splits: cartesian product of per-axis breakpoint + delta split
//      points (attack deltas ⊕ residual deltas ⊕ consumable heals).
//   5. Per sub-rect: capture LO leaves via oracle->step(debug_emit), replay each at
//      HI via oracle->replay_path.
//   6. Shift assertion (image width == input width, saturation exemption).
//   7. Ctx-id interning: both endpoint children intern to same d'.
//   8. Image splits at BpSet breakpoints.
//   9. Merge + exact-dedupe.
// Every gate throws ExpandError on failure; no auto-bisect anywhere.
#include "solver/bucket/expand.h"

#include "ai_analytic.h"                 // cpp_compute_action_probabilities
#include "core_leaf.h"                   // damage_table lives via engine_queries.h
#include "effects_internal.h"            // is_berry (Cheek Pouch gate)
#include "residuals.h"                   // residual constants referenced in comments

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

// ---------------------------------------------------------------------------
// ExpandError
// ---------------------------------------------------------------------------

ExpandError::ExpandError(Stage st, const std::string& msg)
    : std::runtime_error(msg), stage(st) {}

// ---------------------------------------------------------------------------
// support_fingerprint
// ---------------------------------------------------------------------------

// Order-independent FNV-1a xor-fold over sorted (kind, move_slot, switch_to_slot,
// target_side, target_slot) tuples with p > 0. Probabilities are excluded so
// support-set equality drives the fingerprint, not the AI distribution.
uint64_t support_fingerprint(const std::vector<ActionProb>& probs) {
    struct Key {
        int32_t kind, move_slot, switch_to_slot, target_side, target_slot;
        bool operator<(const Key& o) const {
            return std::tie(kind, move_slot, switch_to_slot, target_side, target_slot)
                 < std::tie(o.kind, o.move_slot, o.switch_to_slot, o.target_side, o.target_slot);
        }
    };
    std::vector<Key> keys;
    keys.reserve(probs.size());
    for (const auto& ap : probs) {
        if (!(ap.prob > 0.0)) continue;
        keys.push_back({ap.action.kind, ap.action.move_slot, ap.action.switch_to_slot,
                        ap.action.target_side, ap.action.target_slot});
    }
    std::sort(keys.begin(), keys.end());

    uint64_t h = 1469598103934665603ULL;   // FNV-1a offset basis
    auto mix = [&](int32_t v) {
        h ^= static_cast<uint64_t>(static_cast<uint32_t>(v));
        h *= 1099511628211ULL;
    };
    for (const Key& k : keys) {
        mix(k.kind); mix(k.move_slot); mix(k.switch_to_slot);
        mix(k.target_side); mix(k.target_slot);
        mix(0x5eadbeef);   // per-entry separator
    }
    return h;
}

// ---------------------------------------------------------------------------
// Dominance predicates
// ---------------------------------------------------------------------------

// Vacuous cases: empty crit/noncrit lists AND all-zero tables (status moves like
// Splash, and immune matchups). Status moves are damage-free and can never veto the
// fast-path dominance check — no crit branching to worry about.
static bool table_is_vacuous(const DamageTable& t) {
    if (t.crit.empty() || t.noncrit.empty()) return true;
    for (int32_t v : t.noncrit) if (v != 0) return false;
    for (int32_t v : t.crit)    if (v != 0) return false;
    return true;
}

bool strict_crit_dominance(const DamageTable& t) {
    if (table_is_vacuous(t)) return true;
    int32_t crit_min    = *std::min_element(t.crit.begin(),    t.crit.end());
    int32_t noncrit_max = *std::max_element(t.noncrit.begin(), t.noncrit.end());
    return crit_min > noncrit_max;
}

bool weak_crit_dominance(const DamageTable& t) {
    if (table_is_vacuous(t)) return true;
    int32_t crit_min    = *std::min_element(t.crit.begin(),    t.crit.end());
    int32_t noncrit_max = *std::max_element(t.noncrit.begin(), t.noncrit.end());
    return crit_min >= noncrit_max;
}

// ---------------------------------------------------------------------------
// cumulative_attack_deltas
// ---------------------------------------------------------------------------

// Union of noncrit and crit distinct values, then set-convolve up to max_hits.
// Guard: throws DerivedSplitOverflow past 4096 accumulated distinct sums.
std::vector<int32_t> cumulative_attack_deltas(const DamageTable& t) {
    static constexpr size_t kCap = 4096;
    std::set<int32_t> per_hit;
    for (int32_t v : t.noncrit) per_hit.insert(v);
    for (int32_t v : t.crit)    per_hit.insert(v);
    if (per_hit.empty()) return {};

    int max_hits = t.max_hits >= 1 ? t.max_hits : 1;

    std::set<int32_t> all;
    std::set<int32_t> prev = per_hit;   // 1-hit sums
    for (int32_t v : prev) all.insert(v);

    for (int h = 2; h <= max_hits; ++h) {
        std::set<int32_t> next;
        for (int32_t a : prev) {
            for (int32_t b : per_hit) {
                next.insert(a + b);
                if (next.size() > kCap) {
                    throw ExpandError(ExpandError::Stage::DerivedSplitOverflow,
                        "cumulative_attack_deltas: cumulative distinct-sum set exceeded "
                        + std::to_string(kCap));
                }
            }
        }
        for (int32_t v : next) all.insert(v);
        if (all.size() > kCap) {
            throw ExpandError(ExpandError::Stage::DerivedSplitOverflow,
                "cumulative_attack_deltas: union-of-hit-counts exceeded "
                + std::to_string(kCap));
        }
        prev.swap(next);
    }
    return std::vector<int32_t>(all.begin(), all.end());
}

// ---------------------------------------------------------------------------
// residual_delta_candidates
// ---------------------------------------------------------------------------

namespace {

// Item / ability / status IDs referenced below. Sourced by inspection of engine
// residual code (residuals.cpp / effects.cpp — see file-header record).
constexpr int32_t I_LEFTOVERS      = 234;   // residuals.cpp:30 heal max(1, max/16)
constexpr int32_t I_BLACK_SLUDGE   = 281;   // heal (poison-type) OR damage max(1, max/8)
constexpr int32_t I_SITRUS_BERRY   = 158;   // effects.cpp:406 heal max_hp/4 (denom=4)
constexpr int32_t I_ORAN_BERRY     = 155;   // effects.cpp:407 flat +10
constexpr int32_t I_BERRY_JUICE    = 34;    // effects.cpp:408 flat +20
constexpr int32_t I_FIGY_BERRY     = 159;   // effects.cpp:416 heal max_hp/2 (denom=2)
constexpr int32_t I_WIKI_BERRY     = 160;
constexpr int32_t I_MAGO_BERRY     = 161;
constexpr int32_t I_AGUAV_BERRY    = 162;
constexpr int32_t I_IAPAPA_BERRY   = 163;
constexpr int32_t I_STICKY_BARB    = 288;   // residuals.cpp:458 damage max(1, max/8)
constexpr int32_t I_BINDING_BAND   = 544;   // residuals.cpp:510 bound divisor 6 vs 8
constexpr int32_t I_BIG_ROOT       = 296;   // residuals.cpp:303 leech-seed heal *1.3
constexpr int32_t I_ROCKY_HELMET   = 540;   // move_exec_helpers.cpp:174 recoil max(1, max/6)
constexpr int32_t I_LIFE_ORB       = 270;   // post_hit.cpp:945 recoil max(1, max/10)

// Statuses: canonical ids from effects_consts.h (STATUS_BURN=1 is DISTINCT from
// STATUS_POISON=4 — a prior version of this file incorrectly aliased both to 4).
constexpr int32_t STATUS_POISON = 4;
constexpr int32_t STATUS_TOXIC  = 5;
constexpr int32_t STATUS_BURN   = 1;
constexpr int32_t STATUS_SLEEP  = 6;

// Abilities referenced by §7/§8 rows below (residuals.cpp / move_exec_damage.cpp /
// post_hit.cpp — see per-row comments for exact source line).
constexpr int32_t AB_MAGIC_GUARD  = 98;
constexpr int32_t AB_POISON_HEAL  = 90;    // residuals.cpp:318 heal max(1, max/8)
constexpr int32_t AB_RAIN_DISH    = 44;    // residuals.cpp:131 heal max(1, max/16)
constexpr int32_t AB_DRY_SKIN     = 87;    // residuals.cpp:137 heal/damage max(1, max/8)
constexpr int32_t AB_SOLAR_POWER  = 94;    // residuals.cpp:152 damage max(1, max/8)
constexpr int32_t AB_BAD_DREAMS   = 123;   // residuals.cpp:419 opp damage max(1, max/8)
constexpr int32_t AB_RIPEN        = 247;   // effects.cpp: doubles HP-berry heals (not Berry Juice)
constexpr int32_t AB_LIQUID_OOZE  = 64;    // residuals.cpp:296 flips leech-seed heal to damage
constexpr int32_t AB_ROUGH_SKIN   = 24;    // move_exec_damage.cpp:78 opp recoil max(1, max/8)
constexpr int32_t AB_IRON_BARBS   = 160;   // same formula as Rough Skin
constexpr int32_t AB_AFTERMATH    = 106;   // move_exec_damage.cpp:279 opp dmg max_hp/4, NO floor

constexpr int32_t VE_NIGHTMARE = 26;       // residuals.cpp:470 damage max(1, max/4)
constexpr int32_t VE_BOUND     = 4;        // residuals.cpp:495 damage max(1, max/8 or max/6)
constexpr int32_t VOL_CURSED        = 4;         // residuals.cpp:483 damage max(1, max/4)
constexpr int32_t VOL_LEECH_SEEDED  = 2;         // residuals.cpp:273 drain max(1, max/8)

constexpr int32_t WEATHER_SANDSTORM = 3;   // residuals.cpp:104 chip max(1, max/16)
constexpr int32_t WEATHER_HAIL      = 4;   // residuals.cpp:114 chip max(1, max/16)
constexpr int32_t WEATHER_SUNNY     = 1;
constexpr int32_t WEATHER_RAINY     = 2;
constexpr int32_t WEATHER_HARSH_SUN = 6;
constexpr int32_t WEATHER_HEAVY_RAIN = 5;

constexpr int32_t MOVE_HIGH_JUMP_KICK    = 136;  // move_exec_guards.cpp:695 crash max(1, max/2)
constexpr int32_t MOVE_JUMP_KICK         = 26;
constexpr int32_t MOVE_SUPERCELL_SLAM    = 916;
constexpr int32_t MOVE_STEEL_BEAM        = 796;  // post_hit.cpp: self cost max(1, max/2)
constexpr int32_t MOVE_SPIKY_SHIELD      = 596;  // move_exec_guards.cpp:335 attacker dmg max(1, max/8)

constexpr int32_t AB_CHEEK_POUCH = 167;    // post_hit.cpp:233 self heal max(1, max/3) on berry eat

const PokemonState& active_of(const BattleState& s, int side) {
    const SideState& ss = (side == 0) ? s.side0 : s.side1;
    return ss.team[ss.active_indices[0]];
}

int32_t safe_max_hp(const PokemonState& m) {
    return m.has_max_hp ? m.max_hp : (m.has_stats ? m.stat_hp : 0);
}

// Look up move id by slot for the active mon of `side`. Returns 0 if slot out of range.
int32_t move_id_at_slot(const BattleState& s, int side, int slot) {
    const SideState& ss = (side == 0) ? s.side0 : s.side1;
    const PokemonState& m = ss.team[ss.active_indices[0]];
    switch (slot) {
        case 0: return m.move_id0;
        case 1: return m.move_id1;
        case 2: return m.move_id2;
        case 3: return m.move_id3;
        default: return 0;
    }
}

// Resolve a move id from an action (override wins over slot).
int32_t resolve_action_move_id(const BattleState& s, int side, const ExecAction& a) {
    if (a.move_override >= 0) return a.move_override;
    return move_id_at_slot(s, side, a.move_slot);
}

// The five HP-INDEPENDENT fixed-damage moves are SUPPORTED (record fixed_damage_supported):
// their damage never reads defender HP and cannot crit, so a synthesized damage set drives
// ordinary derived splits + replay verification. All OTHER cpp_is_fixed_damage_move ids
// (Super Fang, Endeavor, Counter, ...) stay UnsupportedMove. Ids: Sonic Boom/Dragon Rage/
// Seismic Toss/Night Shade/Psywave (core_leaf.cpp:417-446).
constexpr int32_t SUPPORTED_FIXED_DAMAGE[] = {49, 82, 69, 101, 149};
// OHKO moves (move_exec_damage.cpp:67): damage = defender HP applied OUTSIDE
// cpp_calculate_damage, so damage_table is all-zero → the equality screen would pass and
// produce a false all-survive image. Inventory §14 #6: THROW UnsupportedMove; the
// always-kill fast path is the future refinement.
constexpr int32_t OHKO_MOVES[] = {12, 32, 90, 329};

bool in_move_list(const int32_t* arr, int n, int32_t v) {
    for (int i = 0; i < n; ++i) if (arr[i] == v) return true;
    return false;
}
bool is_supported_fixed_move(int32_t id) {
    return in_move_list(SUPPORTED_FIXED_DAMAGE, 5, id);
}
bool is_ohko_move(int32_t id) {
    return in_move_list(OHKO_MOVES, 4, id);
}

// Distinct positive damage values for a supported fixed-damage move (HP-independent),
// mirroring cpp_compute_fixed_damage (core_leaf.cpp:417-446).
std::vector<int32_t> supported_fixed_damage_set(const BattleState& s, int attacker_side,
                                                int32_t move_id) {
    const PokemonState& atk = active_of(s, attacker_side);
    std::set<int32_t> vals;
    switch (move_id) {
        case 49:  vals.insert(20); break;                              // Sonic Boom
        case 82:  vals.insert(40); break;                              // Dragon Rage
        case 69:                                                        // Seismic Toss
        case 101: vals.insert(std::max(1, atk.level)); break;          // Night Shade
        case 149: {                                                     // Psywave: k in [0,100]
            int64_t level = atk.level;
            for (int k = 0; k <= 100; ++k) {
                int64_t roll_int = 50 + k;
                vals.insert(static_cast<int32_t>(std::max<int64_t>(1, roll_int * level / 100)));
            }
            break;
        }
        default: break;
    }
    return std::vector<int32_t>(vals.begin(), vals.end());
}

// Damage table used for delta-pool construction. Supported fixed-damage moves return a
// synthesized HP-independent table with an EMPTY crit class (crit-vacuous: they cannot
// crit); every other move uses the real damage_table.
DamageTable effective_damage_table(const BattleState& s, int attacker_side,
                                   const ExecAction& act) {
    int32_t mid = resolve_action_move_id(s, attacker_side, act);
    if (mid > 0 && is_supported_fixed_move(mid)) {
        DamageTable t;
        t.noncrit = supported_fixed_damage_set(s, attacker_side, mid);
        // crit left empty on purpose — fixed-damage moves cannot crit.
        t.max_hits = 1;
        t.immune = t.noncrit.empty();
        return t;
    }
    return damage_table(s, attacker_side, act);
}

} // namespace

namespace {
bool residual_knows_move(const PokemonState& m, int32_t move_id) {
    return m.move_id0 == move_id || m.move_id1 == move_id
        || m.move_id2 == move_id || m.move_id3 == move_id;
}
bool residual_has_ve(const PokemonState& m, int32_t ve) {
    for (const auto& tv : m.timed_volatiles) if (tv.effect == ve) return true;
    return false;
}
} // namespace

// Superset of one-turn HP-delta candidates for one side's active mon. Positive =
// heal (image shift by +delta), negative = damage (image shift by -delta / opposite
// convention downstream). Always includes 0. Missed sources produce over-splitting
// (sound) or a gate throw, never unsoundness.
//
// Task 8 Step 3: every magnitude below is added with BOTH signs (item C.1) — this
// makes trigger-direction bugs (e.g. Poison Heal reversing poison damage into a heal)
// self-correcting without extra branching, since both signs are already candidates.
// Secondary gating conditions (contact-only, type immunity, Safety Goggles, ...) are
// DELIBERATELY not modeled here — omitting them only over-includes candidate deltas,
// which is sound per the Expand contract; only under-inclusion would be unsound.
std::vector<int32_t> residual_delta_candidates(const BattleState& state, int side) {
    const PokemonState& mon = active_of(state, side);
    const PokemonState& opp = active_of(state, 1 - side);
    const SideState& own_side = (side == 0) ? state.side0 : state.side1;
    int32_t max_hp = safe_max_hp(mon);
    std::set<int32_t> deltas = {0};

    if (max_hp <= 0) return {0};

    auto add = [&](int32_t d) { deltas.insert(d); };
    auto add_both = [&](int32_t magnitude) { deltas.insert(magnitude); deltas.insert(-magnitude); };

    bool ripen = mon.ability == AB_RIPEN;

    // --- §7: own-axis residual chip/heal magnitudes ---

    // Burn: max(1, max/16) (residuals.cpp:347-350).
    if (mon.status == STATUS_BURN) add_both(std::max(1, max_hp / 16));
    // Poison / Poison Heal: max(1, max/8) — both signs cover Poison Heal's reversed
    // direction (residuals.cpp:316-338).
    if (mon.status == STATUS_POISON || mon.status == STATUS_TOXIC
        || mon.ability == AB_POISON_HEAL) {
        add_both(std::max(1, max_hp / 8));
    }
    // Toxic: max(1, max*counter/16) (residuals.cpp:325). Enumerate counters 1..15.
    if (mon.status == STATUS_TOXIC) {
        int32_t counter = mon.toxic_turns > 0 ? mon.toxic_turns : 1;
        for (int c = counter; c <= 15; ++c) {
            int32_t dmg = std::max(1, static_cast<int32_t>(
                static_cast<int64_t>(max_hp) * c / 16));
            add_both(dmg);
        }
    }
    // Leftovers / Rain Dish / Dry Skin(rain) / Grassy Terrain / Aqua Ring / Ingrain /
    // Black Sludge (poison heal) / sandstorm / hail: all max(1, max/16).
    if (mon.item == I_LEFTOVERS) add_both(std::max(1, max_hp / 16));
    if (mon.ability == AB_RAIN_DISH) add_both(std::max(1, max_hp / 16));
    if (mon.ability == AB_DRY_SKIN
        && (state.weather == WEATHER_RAINY || state.weather == WEATHER_HEAVY_RAIN)) {
        add_both(std::max(1, max_hp / 16));
    }
    if (state.terrain == 2 /*TERRAIN_GRASSY*/) add_both(std::max(1, max_hp / 16));
    if (mon.volatiles & 32768 /*VOL_AQUA_RING*/) add_both(std::max(1, max_hp / 16));
    if (mon.volatiles & 65536 /*VOL_INGRAIN*/) add_both(std::max(1, max_hp / 16));
    if (mon.item == I_BLACK_SLUDGE) add_both(std::max(1, max_hp / 16));
    if (state.weather == WEATHER_SANDSTORM || state.weather == WEATHER_HAIL) {
        add_both(std::max(1, max_hp / 16));
    }
    // Black Sludge non-poison damage / Solar Power / Dry Skin(sun) / Sticky Barb /
    // own Bad Dreams victim / opp Bad Dreams source magnitude / Leech Seed drain: all
    // max(1, max/8).
    if (mon.item == I_BLACK_SLUDGE) add_both(std::max(1, max_hp / 8));
    if (mon.ability == AB_SOLAR_POWER
        && (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN)) {
        add_both(std::max(1, max_hp / 8));
    }
    if (mon.ability == AB_DRY_SKIN
        && (state.weather == WEATHER_SUNNY || state.weather == WEATHER_HARSH_SUN)) {
        add_both(std::max(1, max_hp / 8));
    }
    if (mon.item == I_STICKY_BARB) add_both(std::max(1, max_hp / 8));
    if (mon.status == STATUS_SLEEP && opp.ability == AB_BAD_DREAMS) {
        // Own axis takes the Bad Dreams damage when THIS mon is the sleeping victim.
        add_both(std::max(1, max_hp / 8));
    }
    if (mon.volatiles & VOL_LEECH_SEEDED) add_both(std::max(1, max_hp / 8));
    // Nightmare / residual Curse: max(1, max/4).
    if (residual_has_ve(mon, VE_NIGHTMARE) && mon.status == STATUS_SLEEP) {
        add_both(std::max(1, max_hp / 4));
    }
    if (mon.volatiles & VOL_CURSED) add_both(std::max(1, max_hp / 4));
    // Bound: max(1, max/8), or max(1, max/6) if the opponent holds Binding Band.
    if (residual_has_ve(mon, VE_BOUND)) {
        add_both(std::max(1, max_hp / 8));
        add_both(std::max(1, max_hp / 6));
    }

    // --- Cross-axis: Leech Seed's drain lands as damage on the seeded mon (own axis,
    // handled above) but the SAME drain becomes a heal (or Liquid Ooze damage) on the
    // seed source's own axis. When querying that source's side, add the pool too.
    if (opp.volatiles & VOL_LEECH_SEEDED) {
        int32_t drain = std::max(1, safe_max_hp(opp) / 8);
        add_both(drain);
        if (mon.item == I_BIG_ROOT) {
            add_both(static_cast<int32_t>(static_cast<int64_t>(drain) * 13 / 10));
        }
    }

    // --- Consumable HP-berry heals — Ripen doubles every one EXCEPT Berry Juice. ---
    // Ripen doubling is computed as max_hp*2/denom directly (NOT (max_hp/denom)*2 —
    // effects.cpp:454 preserves the extra precision from doubling before dividing).
    if (mon.item == I_SITRUS_BERRY) {
        int32_t a = ripen ? static_cast<int32_t>(static_cast<int64_t>(max_hp) * 2 / 4)
                          : max_hp / 4;
        if (a > 0) add_both(a);
    }
    if (mon.item == I_ORAN_BERRY) add_both(ripen ? 20 : 10);
    if (mon.item == I_BERRY_JUICE) add_both(20);   // Berry Juice never doubles under Ripen.
    if (mon.item == I_FIGY_BERRY || mon.item == I_WIKI_BERRY
        || mon.item == I_MAGO_BERRY || mon.item == I_AGUAV_BERRY
        || mon.item == I_IAPAPA_BERRY) {
        int32_t a = ripen ? static_cast<int32_t>(static_cast<int64_t>(max_hp) * 2 / 2)
                          : max_hp / 2;
        if (a > 0) add_both(a);
    }
    // Cheek Pouch: max(1, max/3) self-heal on ANY berry consumption.
    if (mon.ability == AB_CHEEK_POUCH && eff_internal::is_berry(mon.item)) {
        add_both(std::max(1, max_hp / 3));
    }

    // --- §8: fraction-of-max on-hit deltas (own axis, keyed off self OR opponent). ---
    if (mon.item == I_LIFE_ORB && mon.ability != AB_MAGIC_GUARD) {
        add_both(std::max(1, max_hp / 10));
    }
    if (residual_knows_move(mon, MOVE_STEEL_BEAM)) add_both(std::max(1, max_hp / 2));
    if (residual_knows_move(mon, MOVE_HIGH_JUMP_KICK)
        || residual_knows_move(mon, MOVE_JUMP_KICK)
        || residual_knows_move(mon, MOVE_SUPERCELL_SLAM)) {
        add_both(std::max(1, max_hp / 2));
    }
    if (residual_knows_move(mon, MOVE_SPIKY_SHIELD)) add_both(std::max(1, max_hp / 8));
    // Opponent's contact-punish item/abilities land on THIS mon's axis (attacker side).
    if (opp.item == I_ROCKY_HELMET) add_both(std::max(1, max_hp / 6));
    if (opp.ability == AB_ROUGH_SKIN || opp.ability == AB_IRON_BARBS) {
        add_both(std::max(1, max_hp / 8));
    }
    // Aftermath: the ONE mechanic with NO max(1,...) floor (move_exec_damage.cpp:279).
    if (opp.ability == AB_AFTERMATH) add_both(max_hp / 4);

    return std::vector<int32_t>(deltas.begin(), deltas.end());
}

// ---------------------------------------------------------------------------
// derived_split_points
// ---------------------------------------------------------------------------

// Return strict-interior split points x in (lo, hi) of the form x = b + delta.
std::vector<int32_t> derived_split_points(const std::vector<int32_t>& breakpoints,
                                          const std::vector<int32_t>& deltas,
                                          int32_t lo, int32_t hi) {
    std::set<int32_t> pts;
    for (int32_t b : breakpoints) {
        for (int32_t d : deltas) {
            int64_t x = static_cast<int64_t>(b) + static_cast<int64_t>(d);
            if (x > lo && x < hi) pts.insert(static_cast<int32_t>(x));
        }
    }
    return std::vector<int32_t>(pts.begin(), pts.end());
}

// ===========================================================================
// Expand pipeline
// ===========================================================================

namespace {

// Wrap unpack: build the concrete state for one bucket corner.
BattleState corner_state(const Bucket& A, int32_t pl_hp, int32_t opp_hp,
                         const ContextInterner& interner) {
    PackedKey k = make_packed_key(A.d(),
                                  static_cast<uint16_t>(pl_hp),
                                  static_cast<uint16_t>(opp_hp));
    return interner.unpack(k);
}

// True iff the support at LO equals that at HI (p>0 sets equal) AND both match
// A.support_fp(). Throws ExpandError{SupportFlip} otherwise. Bucket LO/HI is
// (player_hp.lo, opp_hp.lo) and (player_hp.hi, opp_hp.hi).
void support_gate_or_throw(const Bucket& A, const BattleState& lo, const BattleState& hi) {
    std::vector<ActionProb> lo_probs = cpp_compute_action_probabilities(lo, /*ai_idx=*/1);
    std::vector<ActionProb> hi_probs = cpp_compute_action_probabilities(hi, /*ai_idx=*/1);
    uint64_t lo_fp = support_fingerprint(lo_probs);
    uint64_t hi_fp = support_fingerprint(hi_probs);
    if (lo_fp != hi_fp || lo_fp != A.support_fp()) {
        throw ExpandError(ExpandError::Stage::SupportFlip,
            "expand: support fingerprint mismatch — bucket_fp="
            + std::to_string(A.support_fp()) + " lo_fp=" + std::to_string(lo_fp)
            + " hi_fp=" + std::to_string(hi_fp));
    }
}

// Compare two damage tables value-wise. Used by the §5.2 HP-dependent screen — if
// the table differs across the corner states, the move's damage depends on defender
// current HP → throw UnsupportedMove.
bool damage_tables_equal(const DamageTable& a, const DamageTable& b) {
    if (a.noncrit != b.noncrit) return false;
    if (a.crit    != b.crit)    return false;
    if (a.max_hits != b.max_hits) return false;
    if (a.hit_count_support != b.hit_count_support) return false;
    return true;
}

// Enumerate AI move actions from a support distribution (kind=0 only).
std::vector<ExecAction> ai_move_actions(const std::vector<ActionProb>& probs) {
    std::vector<ExecAction> out;
    for (const auto& ap : probs) {
        if (!(ap.prob > 0.0)) continue;
        if (ap.action.kind != 0) continue;
        out.push_back(ap.action);
    }
    return out;
}

// Per-side residual + consumable-heal candidate deltas UNION with the per-move attack
// deltas for every move hitting that side. Attack deltas are negated (damage) and
// zero is always included.
std::vector<int32_t> collect_axis_deltas(
    const std::vector<int32_t>& attack_deltas_neg_hits,   // already negated
    const std::vector<int32_t>& residual_deltas) {
    std::set<int32_t> u;
    u.insert(0);
    for (int32_t d : attack_deltas_neg_hits) u.insert(d);
    for (int32_t d : residual_deltas)        u.insert(d);
    return std::vector<int32_t>(u.begin(), u.end());
}

// Cartesian split of [lo, hi] at strict-interior points; convention x → [lo,x],[x+1,hi].
// A split point equal to cur produces a singleton (cur, cur) — legitimate; a point x >= hi
// falls out of range and is skipped.
std::vector<std::pair<int32_t,int32_t>> split_axis(
    int32_t lo, int32_t hi, const std::vector<int32_t>& pts) {
    std::vector<std::pair<int32_t,int32_t>> out;
    int32_t cur = lo;
    for (int32_t x : pts) {
        if (x < cur || x >= hi) continue;
        out.push_back({cur, x});
        cur = x + 1;
    }
    out.push_back({cur, hi});
    return out;
}

// Given an HpInterval and a BpSet, split into the sub-intervals induced by the
// breakpoint singleton-segment partition (mirrors build_segments in breakpoints.cpp).
// Convention-agnostic: every breakpoint b that touches iv becomes its own singleton
// [b,b]; non-breakpoint runs between become gap segments. Using the singleton
// convention is safe for every kind of breakpoint (WIN-side keepHp, berry trigger,
// Sturdy, etc.) because it never groups distinct semantic classes into one piece.
// Strict-interior would silently fuse breakpoint values with adjacent runs and can
// produce INV-3-mixed children under keepHp semantics.
std::vector<HpInterval> split_at_breakpoints(HpInterval iv,
                                             const std::vector<int32_t>& bps) {
    std::vector<int32_t> touching;
    for (int32_t b : bps) if (b >= iv.lo && b <= iv.hi) touching.push_back(b);
    std::sort(touching.begin(), touching.end());
    touching.erase(std::unique(touching.begin(), touching.end()), touching.end());

    std::vector<HpInterval> out;
    int32_t cursor = iv.lo;
    for (int32_t b : touching) {
        if (b > cursor) out.push_back({cursor, b - 1});   // gap segment below b
        out.push_back({b, b});                            // breakpoint singleton
        cursor = b + 1;
    }
    if (cursor <= iv.hi) out.push_back({cursor, iv.hi});
    if (out.empty()) out.push_back(iv);
    return out;
}

// Read HP for the active mon of one side.
int32_t hp_of(const BattleState& s, int side) {
    return active_of(s, side).hp;
}
int32_t max_hp_of(const BattleState& s, int side) {
    return safe_max_hp(active_of(s, side));
}

// Result of expanding one sub-rectangle: list of (LO leaf's ai_action, LO child,
// HI child) triples for downstream shift/intern/image-split processing.
struct SubRectLeaf {
    ExecAction  ai_action;
    BattleState lo_child;
    BattleState hi_child;
    bool        was_crit_leaf = false;   // one-bit crit-class provenance (for merge)
};

// Detect whether a captured path involves any CRIT event landing on the true (crit)
// branch. Used by the general-path merge to prevent crit / noncrit child coalescing.
bool path_took_crit(const std::vector<LeafPathEntry>& path) {
    for (const auto& e : path) {
        // CRIT event id = 2. value == 1 means crit landed.
        if (e.channel == LeafChannel::CatB && e.event == static_cast<int>(RngEventC::CRIT)
            && e.value == 1) {
            return true;
        }
    }
    return false;
}

// Run oracle->step at LO with debug capture, then replay each leaf at HI. Return
// SubRectLeaf list. Wraps replay throws as Stage::ReplayDivergence.
std::vector<SubRectLeaf> run_leaves(const TransitionOracle& oracle,
                                    const BattleState& lo, const BattleState& hi,
                                    const ExecAction& player_move,
                                    uint64_t& replays_counter) {
    std::vector<SubRectLeaf> out;
    std::vector<LeafDebugInfo> debug_infos;
    std::vector<BattleState>   lo_children;

    TransitionOracle::Config cfg;
    cfg.debug_emit = [&](const LeafDebugInfo& dbg) {
        debug_infos.push_back(dbg);
    };
    oracle.step(lo, player_move, [&](ChildOutcome co) -> bool {
        lo_children.push_back(std::move(co.child));
        return true;
    }, OrderingHint::Natural, cfg);

    if (lo_children.size() != debug_infos.size()) {
        throw ExpandError(ExpandError::Stage::ReplayDivergence,
            "expand: LO leaf/debug count mismatch — " + std::to_string(lo_children.size())
            + " vs " + std::to_string(debug_infos.size()));
    }

    out.reserve(lo_children.size());
    for (size_t i = 0; i < lo_children.size(); ++i) {
        SubRectLeaf leaf;
        leaf.ai_action     = debug_infos[i].ai_action;
        leaf.lo_child      = std::move(lo_children[i]);
        leaf.was_crit_leaf = path_took_crit(debug_infos[i].path);

        ReplayResult rr;
        try {
            TransitionOracle::ReplayOptions ropts;
            ropts.skip_state_shift_check = true;   // expand runs its own endpoint-paired shift gate
            rr = oracle.replay_path(hi, player_move, debug_infos[i].ai_action,
                                    debug_infos[i].path, ropts);
        } catch (const std::runtime_error& e) {
            throw ExpandError(ExpandError::Stage::ReplayDivergence,
                std::string("expand: replay_path diverged — ") + e.what());
        }
        ++replays_counter;
        leaf.hi_child = std::move(rr.child);
        out.push_back(std::move(leaf));
    }
    return out;
}

// Shift assertion (spec §4 step iv): per axis, hi_child_hp - lo_child_hp must equal
// hi_in - lo_in. Saturation exemption: pass if both endpoints coincide at a clamp
// (both 0 for faint, or both == max_hp for full-heal cap).
void shift_gate_or_throw(int32_t lo_in, int32_t hi_in,
                         int32_t lo_out, int32_t hi_out,
                         int32_t max_hp, const char* axis) {
    int32_t in_width  = hi_in  - lo_in;
    int32_t out_width = hi_out - lo_out;
    if (out_width == in_width) return;

    // Saturation exemption: full pin at 0 or at max_hp (both endpoints share the pin).
    bool pinned_zero = (lo_out == 0 && hi_out == 0);
    bool pinned_max  = (lo_out == max_hp && hi_out == max_hp);
    if (pinned_zero || pinned_max) return;

    throw ExpandError(ExpandError::Stage::ShiftViolation,
        std::string("expand: shift violation on ") + axis
        + " axis — in_width=" + std::to_string(in_width)
        + " out_width=" + std::to_string(out_width)
        + " (lo_in=" + std::to_string(lo_in) + " hi_in=" + std::to_string(hi_in)
        + " lo_out=" + std::to_string(lo_out) + " hi_out=" + std::to_string(hi_out) + ")");
}

// After passing all gates, form the child image rectangle from LO/HI end states.
// Ensures LO endpoint <= HI endpoint (monotonicity per INV-2).
HpInterval image_interval(int32_t lo_hp, int32_t hi_hp) {
    if (lo_hp <= hi_hp) return {lo_hp, hi_hp};
    return {hi_hp, lo_hp};   // never expected under INV-2 but keep the ctor happy
}

// Intern both endpoint children; require identical ctx_ids; return the d'.
uint32_t intern_and_match(ContextInterner& interner,
                          const BattleState& lo_child, const BattleState& hi_child) {
    uint32_t lo_ctx = static_cast<uint32_t>(interner.pack(lo_child) >> 32);
    uint32_t hi_ctx = static_cast<uint32_t>(interner.pack(hi_child) >> 32);
    if (lo_ctx != hi_ctx) {
        throw ExpandError(ExpandError::Stage::InternMismatch,
            "expand: interned ctx mismatch — lo_ctx="
            + std::to_string(lo_ctx) + " hi_ctx=" + std::to_string(hi_ctx));
    }
    return lo_ctx;
}

// Deterministic sort key for merge/dedupe: (d, player_lo, player_hi, opp_lo, opp_hi,
// support_fp, ai_slot).
struct ChildKey {
    uint32_t d;
    int32_t pl_lo, pl_hi, opp_lo, opp_hi;
    uint64_t fp;
    int32_t ai_slot;
    bool crit_provenance;
    bool operator<(const ChildKey& o) const {
        return std::tie(d, pl_lo, pl_hi, opp_lo, opp_hi, fp, ai_slot, crit_provenance)
             < std::tie(o.d, o.pl_lo, o.pl_hi, o.opp_lo, o.opp_hi, o.fp, o.ai_slot, o.crit_provenance);
    }
    bool operator==(const ChildKey& o) const {
        return d == o.d && pl_lo == o.pl_lo && pl_hi == o.pl_hi
            && opp_lo == o.opp_lo && opp_hi == o.opp_hi && fp == o.fp
            && ai_slot == o.ai_slot && crit_provenance == o.crit_provenance;
    }
};

// True iff merging a and b would destroy singleton-partition semantics on this axis.
// Two cases:
//   (a) union strictly contains a breakpoint (lo < b < hi in the union) — classic
//       INV-1 violation.
//   (b) either input IS a breakpoint-singleton [b,b] with b in the bp set — merging
//       fuses it into its neighbor, losing the semantic distinction the singleton
//       encodes (e.g. keepHp boundary). Downstream consumers (image_splits stat,
//       kill/no-kill classification at hp=b) depend on the singleton remaining
//       distinct even when the merged bucket would otherwise satisfy INV-1.
bool merge_veto_axis(const HpInterval& a, const HpInterval& b,
                     const std::vector<int32_t>& bps) {
    int32_t lo = std::min(a.lo, b.lo);
    int32_t hi = std::max(a.hi, b.hi);
    for (int32_t x : bps) if (x > lo && x < hi) return true;
    auto is_singleton_bp = [&](const HpInterval& iv) {
        if (iv.lo != iv.hi) return false;
        return std::find(bps.begin(), bps.end(), iv.lo) != bps.end();
    };
    if (is_singleton_bp(a) || is_singleton_bp(b)) {
        if (a.lo != b.lo || a.hi != b.hi) return true;   // identical singletons are fine
    }
    return false;
}

// Attempt a one-pass merge over already-sorted children under the same d + support_fp
// + ai_slot (and crit-provenance if general path). Uses the existing bucket try_merge.
// Vetoes any candidate merge whose union strictly contains a BpSet breakpoint on the
// changing axis — that would break INV-1 (the merged bucket's members would no longer
// share support/trigger semantics). Returns the merged children.
std::vector<ChildBucket> merge_pass(std::vector<ChildBucket> children,
                                    std::vector<bool> crit_provenance,
                                    bool general_path,
                                    const BpSet& bp) {
    // Sort by (d, ai_slot, [crit_prov], pl_lo, opp_lo).
    struct Entry {
        ChildBucket child;
        bool        crit;
    };
    std::vector<Entry> entries;
    entries.reserve(children.size());
    for (size_t i = 0; i < children.size(); ++i)
        entries.push_back({std::move(children[i]), crit_provenance[i]});
    std::sort(entries.begin(), entries.end(), [general_path](const Entry& a, const Entry& b) {
        if (a.child.bucket.d() != b.child.bucket.d())
            return a.child.bucket.d() < b.child.bucket.d();
        if (a.child.ai_action.move_slot != b.child.ai_action.move_slot)
            return a.child.ai_action.move_slot < b.child.ai_action.move_slot;
        if (general_path && a.crit != b.crit)
            return static_cast<int>(a.crit) < static_cast<int>(b.crit);
        if (a.child.bucket.player_hp().lo != b.child.bucket.player_hp().lo)
            return a.child.bucket.player_hp().lo < b.child.bucket.player_hp().lo;
        return a.child.bucket.opp_hp().lo < b.child.bucket.opp_hp().lo;
    });

    // One-pass fixed-point merge.
    bool changed = true;
    while (changed) {
        changed = false;
        for (size_t i = 0; i + 1 < entries.size(); ++i) {
            // Only merge same d + same ai_slot (already grouped by sort).
            if (entries[i].child.bucket.d() != entries[i+1].child.bucket.d()) continue;
            if (entries[i].child.ai_action.move_slot
                != entries[i+1].child.ai_action.move_slot) continue;
            if (general_path && entries[i].crit != entries[i+1].crit) continue;
            // Breakpoint veto: refuse merges whose union straddles a breakpoint on the
            // changing axis. try_merge is bp-unaware and would produce an INV-1
            // violator via make_unchecked when adjacency/overlap happens exactly at a
            // breakpoint boundary.
            const auto& pa = entries[i].child.bucket.player_hp();
            const auto& pb = entries[i+1].child.bucket.player_hp();
            const auto& oa = entries[i].child.bucket.opp_hp();
            const auto& ob = entries[i+1].child.bucket.opp_hp();
            if (merge_veto_axis(pa, pb, bp.player_breakpoints())) continue;
            if (merge_veto_axis(oa, ob, bp.opp_breakpoints()))    continue;
            auto m = try_merge(entries[i].child.bucket, entries[i+1].child.bucket);
            if (!m.has_value()) continue;
            entries[i].child.bucket = *m;
            entries.erase(entries.begin() + i + 1);
            changed = true;
            break;
        }
    }

    std::vector<ChildBucket> out;
    out.reserve(entries.size());
    for (auto& e : entries) out.push_back(std::move(e.child));
    return out;
}

} // namespace

// ---------------------------------------------------------------------------
// expand — top-level
// ---------------------------------------------------------------------------

ExpandResult expand(const Bucket& A, const ExecAction& player_move, ExpandContext& ctx) {
    // ---- Preconditions ----
    if (!ctx.oracle || !ctx.interner || !ctx.bp) {
        throw ExpandError(ExpandError::Stage::Precondition,
            "expand: null oracle/interner/bp in ExpandContext");
    }
    if (A.player_hp().lo < 1 || A.opp_hp().lo < 1) {
        throw ExpandError(ExpandError::Stage::Precondition,
            "expand: bucket interval touches 0 (terminal) — never expand a terminal bucket");
    }

    ExpandResult result;
    ExpandStats& stats = result.stats;
    stats.fast_path = true;   // will be cleared as soon as any table is only weak-dominant

    ContextInterner& interner = *ctx.interner;
    const TransitionOracle& oracle = *ctx.oracle;
    const BpSet& bp = *ctx.bp;

    // ---- LO / HI corner states ----
    BattleState lo_state = corner_state(A, A.player_hp().lo, A.opp_hp().lo, interner);
    BattleState hi_state = corner_state(A, A.player_hp().hi, A.opp_hp().hi, interner);

    // Step 1: support gate on A.
    support_gate_or_throw(A, lo_state, hi_state);

    // Step 2: concede seam.
    if (ctx.concede) {
        uint32_t tag = ctx.concede(lo_state, hi_state, player_move);
        if (tag != 0) {
            result.concession_tag = tag;
            return result;
        }
    }

    // Step 3: damage tables + §5.2 screen + crit dominance.
    // §5.2 HP-dependent-move screen has TWO parts:
    //   (a) damage_tables_equal at both corners — catches variable-BP moves whose damage
    //       calc reads HP (Reversal/Flail, Water Spout/Eruption, HP-scaled BP).
    //   (b) cpp_is_fixed_damage_move — catches fixed-damage moves (Super Fang, Endeavor,
    //       Final Gambit, Counter, Metal Burst, ...). These bypass cpp_calculate_damage so
    //       damage_table returns zeros even for HP-DEPENDENT effects like defender.hp/2.
    //       We defer the fine-grained "which fixed-damage moves are HP-safe" question to
    //       Task 6 concede coverage; here we route ALL fixed-damage moves to UnsupportedMove.
    //       Delegating to the engine's own classifier avoids a hardcoded move-ID list.
    // Player move table at both corners.
    {
        DamageTable dt_lo = damage_table(lo_state, /*attacker=*/0, player_move);
        DamageTable dt_hi = damage_table(hi_state, /*attacker=*/0, player_move);
        int32_t pl_mid = move_id_at_slot(lo_state, 0, player_move.move_slot);
        if (!ctx.options.skip_hp_dependent_screen) {
            if (pl_mid > 0 && is_ohko_move(pl_mid)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: player move slot=" + std::to_string(player_move.move_slot)
                    + " move_id=" + std::to_string(pl_mid)
                    + " is an OHKO move (inventory §14 #6 all-zero damage-table) — UnsupportedMove");
            }
            // Supported fixed-damage moves (fixed_damage_supported) pass through; only the
            // HP-dependent fixed-damage moves (Super Fang, Endeavor, Counter, ...) throw.
            if (pl_mid > 0 && cpp_is_fixed_damage_move(pl_mid) && !is_supported_fixed_move(pl_mid)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: player move slot=" + std::to_string(player_move.move_slot)
                    + " move_id=" + std::to_string(pl_mid)
                    + " is a fixed-damage move (§5.2) — routed to UnsupportedMove");
            }
            if (!damage_tables_equal(dt_lo, dt_hi)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: player move slot=" + std::to_string(player_move.move_slot)
                    + " move_id=" + std::to_string(pl_mid)
                    + " has HP-dependent damage table — routed to §5.2 (UnsupportedMove)");
            }
        }
        if (!weak_crit_dominance(dt_lo) || !weak_crit_dominance(dt_hi)) {
            throw ExpandError(ExpandError::Stage::WeakDominanceViolation,
                "expand: player move violates weak crit dominance");
        }
        if (!strict_crit_dominance(dt_lo) || !strict_crit_dominance(dt_hi))
            stats.fast_path = false;
    }

    // Same for every AI support move (attacker side 1).
    std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(lo_state, /*ai_idx=*/1);
    std::vector<ExecAction> ai_actions = ai_move_actions(ai_probs);
    for (const ExecAction& aim : ai_actions) {
        DamageTable dt_lo = damage_table(lo_state, /*attacker=*/1, aim);
        DamageTable dt_hi = damage_table(hi_state, /*attacker=*/1, aim);
        int32_t ai_mid = move_id_at_slot(lo_state, 1, aim.move_slot);
        if (!ctx.options.skip_hp_dependent_screen) {
            if (ai_mid > 0 && is_ohko_move(ai_mid)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: AI move slot=" + std::to_string(aim.move_slot)
                    + " move_id=" + std::to_string(ai_mid)
                    + " is an OHKO move (inventory §14 #6 all-zero damage-table) — UnsupportedMove");
            }
            if (ai_mid > 0 && cpp_is_fixed_damage_move(ai_mid) && !is_supported_fixed_move(ai_mid)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: AI move slot=" + std::to_string(aim.move_slot)
                    + " move_id=" + std::to_string(ai_mid)
                    + " is a fixed-damage move (§5.2) — routed to UnsupportedMove");
            }
            if (!damage_tables_equal(dt_lo, dt_hi)) {
                throw ExpandError(ExpandError::Stage::UnsupportedMove,
                    "expand: AI move slot=" + std::to_string(aim.move_slot)
                    + " move_id=" + std::to_string(ai_mid)
                    + " has HP-dependent damage table — routed to §5.2");
            }
        }
        if (!weak_crit_dominance(dt_lo) || !weak_crit_dominance(dt_hi)) {
            throw ExpandError(ExpandError::Stage::WeakDominanceViolation,
                "expand: AI move slot=" + std::to_string(aim.move_slot)
                + " violates weak crit dominance");
        }
        if (!strict_crit_dominance(dt_lo) || !strict_crit_dominance(dt_hi))
            stats.fast_path = false;
    }

    // ---- Step 4: derived input splits (per axis) ----
    // Derived split points come from b + delta where b is a breakpoint and delta is a
    // per-turn HP change candidate. Threshold b is crossed exactly when h = b + d (for
    // damage) or h = b - d (for heal). To cover every candidate crossing across the whole
    // damage range, we push both signs of every attainable cumulative damage AND fill in
    // the ENTIRE integer range [d_min, d_max] (union over noncrit/crit and hit counts).
    // Over-kill singleton zone: for each axis we track the largest possible damage the
    // attacker into that axis may deal. Every h in [1, max_dmg] must be a singleton
    // piece — otherwise a leaf with dmg >= h clamps h_out=0 with last_damage_taken=h_in,
    // and two h_in values in the same piece produce different last_damage_taken → intern
    // mismatch (amendment 20b overkill coupling). We satisfy this by splitting at every
    // integer in [1, max_dmg] on the damaged axis (see split-point construction below).
    // This over-splits (sound) rather than missing (unsound); merge collapses redundancy.
    std::vector<int32_t> pl_delta_pool;   // deltas applied to PLAYER hp this turn
    std::vector<int32_t> op_delta_pool;   // deltas applied to OPP hp this turn
    int32_t pl_max_dmg = 0;
    int32_t op_max_dmg = 0;

    auto push_attack_pool = [](std::vector<int32_t>& pool, int32_t& max_dmg_out,
                                const DamageTable& dt) {
        std::vector<int32_t> sums = cumulative_attack_deltas(dt);
        if (sums.empty()) return;
        int32_t dmin = sums.front();
        int32_t dmax = sums.back();
        if (dmax > max_dmg_out) max_dmg_out = dmax;
        for (int32_t d : sums) {
            pool.push_back(-d);
            pool.push_back(+d);
        }
        // Also enumerate the integer range [dmin, dmax] to catch crossings at any HP the
        // engine may observe (e.g. crit tables can reach values outside noncrit union).
        for (int32_t d = dmin; d <= dmax; ++d) {
            pool.push_back(-d);
            pool.push_back(+d);
        }
    };

    {
        // Supported fixed-damage moves have an all-zero real damage_table; synthesize
        // their HP-independent damage set so derived splits + kill-zone singletons fire.
        for (const ExecAction& aim : ai_actions) {
            DamageTable dt = effective_damage_table(lo_state, 1, aim);
            push_attack_pool(pl_delta_pool, pl_max_dmg, dt);
        }
        {
            DamageTable dt = effective_damage_table(lo_state, 0, player_move);
            push_attack_pool(op_delta_pool, op_max_dmg, dt);
        }
        for (int32_t d : residual_delta_candidates(lo_state, 0)) pl_delta_pool.push_back(d);
        for (int32_t d : residual_delta_candidates(lo_state, 1)) op_delta_pool.push_back(d);
    }

    std::vector<int32_t> pl_deltas = collect_axis_deltas(pl_delta_pool, {});
    std::vector<int32_t> op_deltas = collect_axis_deltas(op_delta_pool, {});

    // Overkill singleton zone (amendment 20b): every h in [1, max_dmg-1] must be its
    // own singleton so no piece straddles two "died-at-different-HP" cells. Splitting
    // at h in [1, max_dmg-1] (convention [lo,x],[x+1,hi]) produces {…,[h,h],…} pieces.
    // Include max_dmg's split too (it separates the death zone from survivable range).
    auto add_kill_zone_singletons = [](std::vector<int32_t>& sp, int32_t max_dmg,
                                        int32_t lo, int32_t hi) {
        if (max_dmg <= 0) return;
        int32_t upper = std::min<int32_t>(max_dmg, hi);
        for (int32_t h = std::max<int32_t>(1, lo); h <= upper; ++h) sp.push_back(h);
    };

    std::vector<int32_t> pl_split_pts, op_split_pts;
    if (!ctx.options.skip_derived_splits) {
        pl_split_pts = derived_split_points(bp.player_breakpoints(), pl_deltas,
                                            A.player_hp().lo, A.player_hp().hi);
        op_split_pts = derived_split_points(bp.opp_breakpoints(), op_deltas,
                                            A.opp_hp().lo, A.opp_hp().hi);
        add_kill_zone_singletons(pl_split_pts, pl_max_dmg,
                                 A.player_hp().lo, A.player_hp().hi);
        add_kill_zone_singletons(op_split_pts, op_max_dmg,
                                 A.opp_hp().lo, A.opp_hp().hi);
        // Re-sort/dedupe/clip; kill-zone singletons need x >= lo (split at lo yields
        // [lo,lo],[lo+1,hi] under split_axis's [lo,x],[x+1,hi] convention).
        auto normalize_sp = [](std::vector<int32_t>& v, int32_t lo, int32_t hi) {
            std::set<int32_t> u;
            for (int32_t x : v) if (x >= lo && x < hi) u.insert(x);
            v.assign(u.begin(), u.end());
        };
        normalize_sp(pl_split_pts, A.player_hp().lo, A.player_hp().hi);
        normalize_sp(op_split_pts, A.opp_hp().lo, A.opp_hp().hi);
    }
    stats.derived_split_points = pl_split_pts.size() + op_split_pts.size();

    auto pl_pieces = split_axis(A.player_hp().lo, A.player_hp().hi, pl_split_pts);
    auto op_pieces = split_axis(A.opp_hp().lo,    A.opp_hp().hi,    op_split_pts);

    // ---- Steps 5–8: per sub-rectangle ----
    std::vector<ChildBucket> raw_children;
    std::vector<bool>        raw_crit_prov;

    for (const auto& plp : pl_pieces) {
        for (const auto& opp : op_pieces) {
            ++stats.sub_rects;

            BattleState lo_sr = corner_state(A, plp.first,  opp.first,  interner);
            BattleState hi_sr = corner_state(A, plp.second, opp.second, interner);

            // Support gate on sub-rectangle corners (INV-1 backstop until Task 9).
            support_gate_or_throw(A, lo_sr, hi_sr);

            std::vector<SubRectLeaf> leaves = run_leaves(oracle, lo_sr, hi_sr,
                                                         player_move, stats.replays);
            stats.leaves += leaves.size();

            for (const SubRectLeaf& leaf : leaves) {
                // Shift assertion per axis using this leaf's child HPs.
                int32_t pl_lo_out = hp_of(leaf.lo_child, 0);
                int32_t pl_hi_out = hp_of(leaf.hi_child, 0);
                int32_t op_lo_out = hp_of(leaf.lo_child, 1);
                int32_t op_hi_out = hp_of(leaf.hi_child, 1);
                int32_t pl_max    = max_hp_of(leaf.lo_child, 0);
                int32_t op_max    = max_hp_of(leaf.lo_child, 1);

                shift_gate_or_throw(plp.first, plp.second, pl_lo_out, pl_hi_out,
                                    pl_max, "player");
                shift_gate_or_throw(opp.first, opp.second, op_lo_out, op_hi_out,
                                    op_max, "opp");

                uint32_t d_prime = intern_and_match(interner, leaf.lo_child, leaf.hi_child);

                // Compute child image rectangle from LO/HI corners (INV-2).
                HpInterval pl_img = image_interval(pl_lo_out, pl_hi_out);
                HpInterval op_img = image_interval(op_lo_out, op_hi_out);

                // Support fingerprint of the child at its LO corner. We use LO here
                // because upstream gates already ensured LO/HI support match at the
                // parent bucket; child support gates fire again during the child's
                // own expand.
                std::vector<ActionProb> ch_probs = cpp_compute_action_probabilities(
                    leaf.lo_child, /*ai_idx=*/1);
                uint64_t ch_fp = support_fingerprint(ch_probs);

                // Image splits at BpSet breakpoints on both axes (per-child d' preserved).
                auto pl_pieces_img = split_at_breakpoints(pl_img, bp.player_breakpoints());
                auto op_pieces_img = split_at_breakpoints(op_img, bp.opp_breakpoints());
                if (pl_pieces_img.size() > 1 || op_pieces_img.size() > 1)
                    ++stats.image_splits;

                for (const HpInterval& pl_seg : pl_pieces_img) {
                    for (const HpInterval& op_seg : op_pieces_img) {
                        Bucket child_b(d_prime, pl_seg, op_seg, ch_fp, bp);
                        ChildBucket cb{child_b, leaf.ai_action};
                        raw_children.push_back(std::move(cb));
                        raw_crit_prov.push_back(leaf.was_crit_leaf);
                    }
                }
            }
        }
    }

    stats.children_before_merge = raw_children.size();

    // ---- Step 9: exact-dedupe + merge ----
    // Exact dedupe first (identical children with identical crit provenance).
    {
        std::vector<ChildBucket> dedup;
        std::vector<bool>        dedup_crit;
        std::set<std::tuple<uint32_t,int32_t,int32_t,int32_t,int32_t,uint64_t,int32_t,int>> seen;
        for (size_t i = 0; i < raw_children.size(); ++i) {
            const auto& c = raw_children[i];
            auto k = std::make_tuple(c.bucket.d(),
                                     c.bucket.player_hp().lo, c.bucket.player_hp().hi,
                                     c.bucket.opp_hp().lo,    c.bucket.opp_hp().hi,
                                     c.bucket.support_fp(),
                                     c.ai_action.move_slot,
                                     static_cast<int>(raw_crit_prov[i]));
            if (seen.insert(k).second) {
                dedup.push_back(c);
                dedup_crit.push_back(raw_crit_prov[i]);
            }
        }
        raw_children.swap(dedup);
        raw_crit_prov.swap(dedup_crit);
    }

    bool general_path = ctx.options.force_general_path || !stats.fast_path;
    if (ctx.options.force_general_path) stats.fast_path = false;

    result.children = merge_pass(std::move(raw_children), std::move(raw_crit_prov),
                                 general_path, bp);
    stats.children_after_merge = result.children.size();

    return result;
}
