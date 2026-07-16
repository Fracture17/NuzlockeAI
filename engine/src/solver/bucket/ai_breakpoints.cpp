// AI-scorer HP breakpoint derivation (Task 9). See ai_breakpoints.h for the axis /
// throw contract. Structure: two axis builders (player_axis / ai_axis), each iterating
// pinch/Defeatist/Multiscale regime representatives on BattleState copies and calling
// the scorer's own damage helpers, plus flip-pair bisection for percentage/integer
// scorer gates. NEVER re-derives damage arithmetic.
#include "solver/bucket/ai_breakpoints.h"

#include "ai_analytic.h"          // cpp_compute_action_probabilities (support seam)
#include "ai_damage.h"            // cpp_build_damage_context, cpp_expected_damage
#include "ai_scorer_internal.h"   // ai_scorer::MAX_LUCK_C / AVERAGE_LUCK_C
#include "ai_shared.h"            // active_mon, move_id_at, is_trapping, MV_* ids
#include "orchestrate.h"          // cpp_enumerate_legal_actions

#include "../generated/ai_move_sets.h"  // ai_set_contains, POISON_INFLICT_MOVES, recovery sets

#include <algorithm>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Mechanic constants (mirrored from damage.cpp / ai_scorer*.cpp).
// ---------------------------------------------------------------------------

namespace {

constexpr int32_t AI_SIDE = 1;   // AI is always side 1; player is side 0.

// Attacker-side damage regimes.
constexpr int32_t AB_OVERGROW  = 65;
constexpr int32_t AB_BLAZE     = 66;
constexpr int32_t AB_TORRENT   = 67;
constexpr int32_t AB_SWARM     = 68;
constexpr int32_t AB_DEFEATIST = 129;
// Defender-side full-HP damage regimes.
constexpr int32_t AB_MULTISCALE    = 136;
constexpr int32_t AB_SHADOW_SHIELD = 231;

// Scorer move ids that produce HP breakpoints (values mirror ai_shared.h / internal).
constexpr int32_t MV_SUPER_FANG      = 162;
constexpr int32_t MV_NATURE_S_MADNESS= 717;
constexpr int32_t MV_FUTURE_SIGHT    = 248;
constexpr int32_t MV_RELIC_SONG      = 547;
constexpr int32_t MV_METEOR_BEAM     = 800;
constexpr int32_t MV_FINAL_GAMBIT    = 515;
constexpr int32_t MV_PURSUIT         = 228;
constexpr int32_t MV_SUBSTITUTE      = 164;
constexpr int32_t MV_BELLY_DRUM      = 187;
constexpr int32_t MV_MEMENTO         = 262;
constexpr int32_t MV_REST            = 156;
constexpr int32_t MV_EXPLOSION       = 153;
constexpr int32_t MV_SELF_DESTRUCT   = 120;
constexpr int32_t MV_MISTY_EXPLOSION = 802;

constexpr int32_t TAG_RECOVERY = 4;   // MoveTag::RECOVERY (ai_scorer_internal.h)

// ---------------------------------------------------------------------------
// Small helpers.
// ---------------------------------------------------------------------------

int32_t mon_max_hp(const PokemonState& m) {
    return m.has_max_hp ? m.max_hp : m.stat_hp;
}
int32_t mon_cur_hp(const PokemonState& m) {
    return m.has_hp ? m.hp : mon_max_hp(m);
}

bool knows(const PokemonState& m, int32_t move_id) {
    return m.move_id0 == move_id || m.move_id1 == move_id
        || m.move_id2 == move_id || m.move_id3 == move_id;
}

bool has_pinch_ability(const PokemonState& m) {
    return m.ability == AB_BLAZE || m.ability == AB_TORRENT
        || m.ability == AB_OVERGROW || m.ability == AB_SWARM;
}
bool has_full_hp_reduction(const PokemonState& m) {
    return m.ability == AB_MULTISCALE || m.ability == AB_SHADOW_SHIELD;
}

// Attacker-HP regime representatives: full HP (boosts off) plus pinch/Defeatist
// activation points (cur <= max/3 / cur <= max/2 in damage.cpp).
std::vector<int32_t> attacker_regimes(const PokemonState& m) {
    int32_t mx = mon_max_hp(m);
    std::vector<int32_t> reps = { mx };
    if (has_pinch_ability(m)) reps.push_back(std::max(1, mx / 3));
    if (m.ability == AB_DEFEATIST) reps.push_back(std::max(1, mx / 2));
    return reps;
}
// Defender-HP regime representatives: Multiscale/Shadow Shield halve only at cur==max,
// so full and just-below-full bracket both damage regimes. Non-reducers: current HP.
std::vector<int32_t> defender_regimes(const PokemonState& m) {
    int32_t mx = mon_max_hp(m);
    if (has_full_hp_reduction(m)) return { mx, std::max(1, mx - 1) };
    return { mon_cur_hp(m) };
}

void set_active_hp(BattleState& s, int side, int32_t hp) {
    SideState& ss = (side == 0) ? s.side0 : s.side1;
    PokemonState& m = ss.team[ss.active_indices[0]];
    m.hp = hp;
    m.has_hp = true;
}

// Emit both endpoints of the single adjacent (h, h+1) flip of a monotone predicate over
// [lo, hi]. No emission when pred is constant on the range.
template <class Pred>
void emit_flip_pair(Pred pred, int32_t lo, int32_t hi, AiBpKind kind,
                    std::vector<AiBpEntry>& out) {
    if (hi <= lo) return;
    bool flo = pred(lo);
    if (flo == pred(hi)) return;
    int32_t a = lo, b = hi;
    while (b - a > 1) {
        int32_t mid = a + (b - a) / 2;
        if (pred(mid) == flo) a = mid; else b = mid;
    }
    out.push_back({a, kind});
    out.push_back({b, kind});
}

bool ai_knows_recovery_family(const PokemonState& ai) {
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(ai, slot);
        if (mid == MV_NONE) continue;
        if (mid == MV_REST) return true;
        if (ai_set_contains(RECOVERY_MOVE_SET, N_RECOVERY_MOVE_SET, mid)) return true;
        if (ai_set_contains(WEATHER_RECOVERY_MOVES, N_WEATHER_RECOVERY_MOVES, mid)) return true;
        const MoveData* md = ai_move_data_get(mid);
        if (md && (md->tags & TAG_RECOVERY)) return true;
    }
    return false;
}

bool ai_knows_poison_move(const PokemonState& ai) {
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(ai, slot);
        if (mid == MV_NONE) continue;
        if (ai_set_contains(POISON_INFLICT_MOVES, N_POISON_INFLICT_MOVES, mid)) return true;
    }
    return false;
}

bool is_exception_kill_move(int32_t move_id) {
    return is_trapping(move_id) || move_id == MV_FUTURE_SIGHT
        || move_id == MV_RELIC_SONG || move_id == MV_METEOR_BEAM;
}

// ---------------------------------------------------------------------------
// Player-axis (axis_side == 0): breakpoints on PLAYER HP.
// ---------------------------------------------------------------------------

// P1 (RollValue) + P3 (ExceptionKillEstimate) + P6 (SuperFangTie): all values derived
// from the AI's damage estimates against the player on this concrete state copy.
void collect_ai_to_player_values(const BattleState& copy, std::vector<AiBpEntry>& out) {
    const PokemonState& ai = active_mon(copy, AI_SIDE);
    const PokemonState& pl = active_mon(copy, 0);

    std::vector<ExecAction> actions = cpp_enumerate_legal_actions(copy, AI_SIDE, 0);
    DamageContext ctx = cpp_build_damage_context(copy, AI_SIDE, actions);

    bool superfang = knows(ai, MV_SUPER_FANG) || knows(ai, MV_NATURE_S_MADNESS);

    // P1: every distinct roll value is a cap/kill breakpoint on the player axis.
    // P6 prep: gather values of every OTHER (non-Super-Fang) ctx array for the HD tie.
    std::vector<int32_t> other_vals;
    for (size_t i = 0; i < ctx.slots.size(); ++i) {
        int32_t mid = move_id_at(ai, ctx.slots[i]);
        bool is_sf = (mid == MV_SUPER_FANG || mid == MV_NATURE_S_MADNESS);
        for (int32_t v : ctx.roll_arrays[i]) {
            out.push_back({v, AiBpKind::RollValue});
            if (!is_sf) other_vals.push_back(v);
        }
    }

    // P6: Super Fang damage floor(pl.hp/2) ties with each fixed value v at pl.hp in
    // {2v, 2v+1}; the max(1,..) clamp adds the boundary at 1.
    if (superfang) {
        out.push_back({1, AiBpKind::SuperFangTie});
        for (int32_t v : other_vals) {
            out.push_back({2 * v,     AiBpKind::SuperFangTie});
            out.push_back({2 * v + 1, AiBpKind::SuperFangTie});
        }
    }

    // P3: exception kill estimates (trapping / Future Sight / Relic Song / Meteor Beam).
    // PP is ignored deliberately (robust to PP exhaustion; superset-sound).
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(ai, slot);
        if (mid == MV_NONE || !is_exception_kill_move(mid)) continue;
        int32_t dmg = cpp_expected_damage(ai, mid, pl, copy, ai_scorer::MAX_LUCK_C,
                                          -1, false, -1);
        out.push_back({dmg, AiBpKind::ExceptionKillEstimate});
    }
}

void player_axis_entries(const BattleState& state, std::vector<AiBpEntry>& out) {
    const PokemonState& ai = active_mon(state, AI_SIDE);
    const PokemonState& pl = active_mon(state, 0);
    int32_t pl_max = mon_max_hp(pl);

    // Regime union: AI attacker (pinch/Defeatist) x player defender (Multiscale/SS).
    std::vector<int32_t> ai_reps = attacker_regimes(ai);
    std::vector<int32_t> pl_reps = defender_regimes(pl);
    for (int32_t ai_hp : ai_reps) {
        for (int32_t pl_hp : pl_reps) {
            BattleState copy = state;
            set_active_hp(copy, AI_SIDE, ai_hp);
            set_active_hp(copy, 0, pl_hp);
            collect_ai_to_player_values(copy, out);
        }
    }

    // P4: Pursuit tiers over the verbatim (double)pl.hp/pl.max <= {0.20, 0.40}.
    if (knows(ai, MV_PURSUIT)) {
        emit_flip_pair([&](int32_t h) { return (double)h / pl_max <= 0.20; },
                       1, pl_max, AiBpKind::PursuitPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / pl_max <= 0.40; },
                       1, pl_max, AiBpKind::PursuitPct, out);
    }

    // P5: poison combo gate over the verbatim integer pl.hp*100/pl.max > 20.
    if (ai_knows_poison_move(ai)) {
        emit_flip_pair([&](int32_t h) { return h * 100 / pl_max > 20; },
                       1, pl_max, AiBpKind::PoisonPct, out);
    }
}

// ---------------------------------------------------------------------------
// AI-axis (axis_side == 1): breakpoints on AI HP.
// ---------------------------------------------------------------------------

void ai_axis_entries(const BattleState& state, std::vector<AiBpEntry>& out) {
    const PokemonState& ai = active_mon(state, AI_SIDE);
    const PokemonState& pl = active_mon(state, 0);
    int32_t ai_max = mon_max_hp(ai);

    bool recovery = ai_knows_recovery_family(ai);
    int32_t heal_half = (int32_t)(ai_max * 0.5);
    int32_t heal_sun  = (int32_t)(ai_max * 0.67);

    // A1/A2/A3-RecoverKoAfter: player->AI damage estimates E_i under the regime union of
    // player attacker (pinch/Defeatist) x AI defender (Multiscale/SS). E_i itself varies
    // with AI HP only via the full-HP reduction, hence both defender reps.
    std::vector<int32_t> pl_reps = attacker_regimes(pl);
    std::vector<int32_t> ai_reps = defender_regimes(ai);
    for (int32_t pl_hp : pl_reps) {
        for (int32_t ai_hp : ai_reps) {
            BattleState copy = state;
            set_active_hp(copy, 0, pl_hp);
            set_active_hp(copy, AI_SIDE, ai_hp);
            const PokemonState& ai2 = active_mon(copy, AI_SIDE);
            const PokemonState& pl2 = active_mon(copy, 0);
            for (int slot = 0; slot < 4; ++slot) {
                int32_t mid = move_id_at(pl2, slot);
                if (mid == MV_NONE) continue;
                const MoveData* md = ai_move_data_get(mid);
                if (!md || md->base_power == 0) continue;
                int32_t e = cpp_expected_damage(pl2, mid, ai2, copy,
                                                ai_scorer::AVERAGE_LUCK_C, -1, false, -1);
                out.push_back({e,     AiBpKind::PlayerKoEstimate});
                out.push_back({2 * e, AiBpKind::PlayerTwoHitEstimate});
                if (recovery) {
                    out.push_back({e - heal_half, AiBpKind::RecoverKoAfter});
                    out.push_back({e - heal_sun,  AiBpKind::RecoverKoAfter});
                }
            }
        }
    }

    // A3/A4: should_recover + dist_recovery/Rest HP-percent gates (verbatim expressions).
    if (recovery) {
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max <= 0.4;  }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.66; }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.5;  }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.7;  }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max >= 0.85; }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max >= 1.0;  }, 1, ai_max,
                       AiBpKind::RecoverPct, out);
    }

    // A5: Substitute ai.hp*100/ai.max <= 50 (verbatim integer).
    if (knows(ai, MV_SUBSTITUTE)) {
        emit_flip_pair([&](int32_t h) { return h * 100 / ai_max <= 50; }, 1, ai_max,
                       AiBpKind::SubPct50, out);
    }

    // A6: Belly Drum ai.hp <= ai.max/2 (verbatim integer).
    if (knows(ai, MV_BELLY_DRUM)) {
        emit_flip_pair([&](int32_t h) { return h <= ai_max / 2; }, 1, ai_max,
                       AiBpKind::BellyDrumHalf, out);
    }

    // A7: Explosion !kill ai-HP tiers (verbatim doubles).
    if (knows(ai, MV_EXPLOSION) || knows(ai, MV_SELF_DESTRUCT)
        || knows(ai, MV_MISTY_EXPLOSION)) {
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.10; }, 1, ai_max,
                       AiBpKind::ExplosionPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.33; }, 1, ai_max,
                       AiBpKind::ExplosionPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.66; }, 1, ai_max,
                       AiBpKind::ExplosionPct, out);
    }

    // A8: Memento ai-HP tiers (verbatim doubles).
    if (knows(ai, MV_MEMENTO)) {
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.10; }, 1, ai_max,
                       AiBpKind::MementoPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.33; }, 1, ai_max,
                       AiBpKind::MementoPct, out);
        emit_flip_pair([&](int32_t h) { return (double)h / ai_max < 0.66; }, 1, ai_max,
                       AiBpKind::MementoPct, out);
    }
}

// Throw for cross-axis mechanics that cannot be a fixed per-axis HP breakpoint.
void throw_if_unmodelable(const BattleState& state) {
    const PokemonState& ai = active_mon(state, AI_SIDE);
    if (knows(ai, MV_FINAL_GAMBIT)) {
        throw std::runtime_error(
            "ai_breakpoint_entries: Final Gambit (ai.hp vs pl.hp diagonal) is not a "
            "fixed per-axis HP breakpoint — ai-final-gambit, out of scope");
    }
    const SideState& ai_side = state.side1;
    for (int i = 0; i < (int)ai_side.team.size(); ++i) {
        bool is_active = false;
        for (int a : ai_side.active_indices) if (a == i) { is_active = true; break; }
        if (!is_active && !ai_side.team[i].fainted) {
            throw std::runtime_error(
                "ai_breakpoint_entries: AI has a living bench mon — switch-target "
                "selection is bench-composition-dependent (ai-bench), out of scope");
        }
    }
}

} // namespace

std::vector<AiBpEntry> ai_breakpoint_entries(const BattleState& state, int axis_side) {
    throw_if_unmodelable(state);

    std::vector<AiBpEntry> out;
    if (axis_side == 0)      player_axis_entries(state, out);
    else if (axis_side == 1) ai_axis_entries(state, out);
    else throw std::runtime_error("ai_breakpoint_entries: axis_side must be 0 or 1");
    return out;
}
