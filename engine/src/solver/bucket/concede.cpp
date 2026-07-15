// Concede detectors — see concede.h. Constants are sourced from engine code with
// file:line references (verified 2026-07-15). Every detector is a pure read; the
// public concede_tags() unions f(lo)|f(hi) so the damage_table-reading MULTI_HIT_HARD
// detector fires if it fires at either corner.
#include "solver/bucket/concede.h"

#include "ai_analytic.h"                 // cpp_compute_action_probabilities, ActionProb
#include "ai_shared.h"                   // ai_move_data_get
#include "core_leaf.h"                   // cpp_effective_speed
#include "solver/engine_queries.h"       // damage_table, hp_thresholds
#include "solver/move_scope.h"           // is_hp_dep_move

#include "../generated/move_data.h"      // MoveData, SecondaryEffect

#include <algorithm>
#include <vector>

namespace {

// ---- Engine-mirrored IDs (source references) -----------------------------
// effects_consts.h:63-64
constexpr int32_t STATUS_FREEZE = 2, STATUS_PARALYSIS = 3, STATUS_SLEEP = 6;
// effects_consts.h:91 / move_exec.cpp:52-56
constexpr int32_t VOLATILE_CONFUSED = 1, VOLATILE_MINIMIZE = 1024, VOLATILE_SUBSTITUTE = 4096,
    V_RECHARGING = 256, VOLATILE_ATTRACTED = 8388608;
// move_exec.cpp:106 / move_exec_damage.cpp:66
constexpr int32_t RAMPAGE_MOVES[] = {37, 80, 200};             // Thrash/Petal Dance/Outrage
// post_hit.cpp:115 (Hyper Beam family)
constexpr int32_t RECHARGE_MOVES[] = {63, 307, 308, 338, 416, 439, 794};
// move_exec_damage.cpp:67 (OHKO — Expand throws; never tagged)
constexpr int32_t OHKO_MOVES[] = {12, 32, 90, 329};
// core_leaf.cpp:87 / :77
constexpr int32_t ITEM_QUICK_CLAW = 217, ABILITY_QUICK_DRAW = 259;
// post_hit.cpp:87
constexpr int32_t ITEM_KINGS_ROCK = 221, ITEM_RAZOR_FANG = 327;
// ai_damage.cpp:173 / move_exec_damage.cpp:82
constexpr int32_t AB_PARENTAL_BOND = 185;
// move_exec_damage.cpp:371
constexpr int32_t ITEM_METRONOME = 277;
// ai_scorer_internal.h:116
constexpr int32_t AB_INNER_FOCUS = 39;
// effects_consts.h:129
constexpr int32_t MOVE_SUBSTITUTE = 164;
// core_leaf.cpp:94
constexpr int32_t PSEUDO_TRICK_ROOM = 1;
// core_leaf.cpp:453-459: the five HP-INDEPENDENT fixed-damage moves are SUPPORTED, so
// they are NOT §5.2 concessions (record fixed_damage_supported).
constexpr int32_t SUPPORTED_FIXED_DAMAGE[] = {49, 82, 69, 101, 149};  // Sonic Boom/Dragon Rage/Seismic Toss/Night Shade/Psywave
// move_exec_damage.cpp:123-145: type-resist berry item id range (Occa 184 .. Chilan 200, Roseli 686).
constexpr int32_t MOVECAT_STATUS = 2;

template <int N>
bool in_ids(const int32_t (&arr)[N], int32_t v) {
    for (int i = 0; i < N; ++i) if (arr[i] == v) return true;
    return false;
}

bool is_resist_berry(int32_t item) {
    return (item >= 184 && item <= 200) || item == 686;
}

const PokemonState& active(const BattleState& s, int side) {
    const SideState& ss = (side == 0) ? s.side0 : s.side1;
    return ss.team[ss.active_indices[0]];
}
const SideState& side_of(const BattleState& s, int side) {
    return (side == 0) ? s.side0 : s.side1;
}

int32_t move_id_at_slot(const PokemonState& m, int slot) {
    switch (slot) {
        case 0: return m.move_id0;
        case 1: return m.move_id1;
        case 2: return m.move_id2;
        case 3: return m.move_id3;
        default: return 0;
    }
}

// Resolve a move id from an action against the acting mon (override wins).
int32_t resolve_move_id(const PokemonState& m, const ExecAction& a) {
    if (a.move_override >= 0) return a.move_override;
    return move_id_at_slot(m, a.move_slot);
}

int32_t move_priority(int32_t move_id) {
    if (move_id <= 0) return 0;
    const MoveData* md = ai_move_data_get(move_id);
    return md ? md->priority : 0;
}

bool trick_room(const BattleState& s) {
    for (const auto& e : s.pseudo_weather)
        if (e.effect == PSEUDO_TRICK_ROOM) return true;
    return false;
}

// True iff the mon on `first_side` acts STRICTLY before `second_side` for the given
// move ids (priority bracket, then effective speed with Trick Room inversion). Equal
// priority AND equal speed is a tie → false (that is ORDER_RNG's business).
bool acts_strictly_first(const BattleState& s, int first_side, int32_t first_move,
                         int second_side, int32_t second_move) {
    int32_t p1 = move_priority(first_move), p2 = move_priority(second_move);
    if (p1 != p2) return p1 > p2;
    int32_t s1 = cpp_effective_speed(active(s, first_side), side_of(s, first_side), s);
    int32_t s2 = cpp_effective_speed(active(s, second_side), side_of(s, second_side), s);
    if (s1 == s2) return false;
    return trick_room(s) ? (s1 < s2) : (s1 > s2);
}

bool same_bracket_speed_tie(const BattleState& s, int32_t player_move, int32_t ai_move) {
    if (move_priority(player_move) != move_priority(ai_move)) return false;
    int32_t sp = cpp_effective_speed(active(s, 0), side_of(s, 0), s);
    int32_t sa = cpp_effective_speed(active(s, 1), side_of(s, 1), s);
    return sp == sa;
}

// The move flinches its target (own flinch secondary, or holder's King's Rock / Razor
// Fang added flinch on a damaging move). item is the AI holder's item.
bool move_can_flinch(int32_t move_id, int32_t holder_item) {
    const MoveData* md = ai_move_data_get(move_id);
    if (!md) return false;
    if (md->secondary.chance > 0 && md->secondary.flinch) return true;
    if (md->secondary2.chance > 0 && md->secondary2.flinch) return true;
    if ((holder_item == ITEM_KINGS_ROCK || holder_item == ITEM_RAZOR_FANG)
        && md->category != MOVECAT_STATUS)
        return true;
    return false;
}

// HP_DEP_MOVE tag for one move: HP-dependent AND not a supported fixed-damage move.
// (OHKO ids are not in the HP-dep list, so they are never tagged — Expand throws.)
bool hp_dep_tagged(int32_t move_id) {
    if (move_id <= 0) return false;
    if (in_ids(SUPPORTED_FIXED_DAMAGE, move_id)) return false;
    return is_hp_dep_move(move_id);
}

// MULTI_HIT_HARD in one direction: attacker's move is multi-hit AND the defender has a
// live Half/Quarter consumable threshold t AND the move's max single-hit damage > t.
// Cheap d-checks gate the damage_table read.
bool multi_hit_hard(const BattleState& s, int attacker_side, int32_t move_id, int move_slot) {
    if (move_id <= 0 || move_slot < 0) return false;
    const MoveData* md = ai_move_data_get(move_id);
    if (!md || md->max_hits <= 1) return false;

    int defender_side = 1 - attacker_side;
    HpThresholds ht = hp_thresholds(s, defender_side);   // residual_unknown ignored here
    std::vector<int32_t> ts;
    for (const HpThreshold& h : ht.thresholds)
        if (h.kind == ThresholdKind::Half || h.kind == ThresholdKind::Quarter)
            ts.push_back(h.threshold_hp);
    if (ts.empty()) return false;

    ExecAction act{};
    act.kind = 0;
    act.move_slot = move_slot;
    act.source_slot = 0;
    act.target_side = defender_side;
    act.target_slot = 0;
    DamageTable dt = damage_table(s, attacker_side, act);
    int32_t max_hit = 0;
    if (!dt.crit.empty()) max_hit = dt.crit.back();
    else if (!dt.noncrit.empty()) max_hit = dt.noncrit.back();

    for (int32_t t : ts) if (max_hit > t) return true;
    return false;
}

// All tags firing at a single concrete state for the given player move.
uint32_t tags_at(const BattleState& s, const ExecAction& player_move) {
    uint32_t tags = 0;

    const PokemonState& pl  = active(s, 0);
    const PokemonState& opp = active(s, 1);
    int32_t pl_move_id = resolve_move_id(pl, player_move);

    // ---- §5.1 stunlock — PLAYER side only (record stunlock_concede_player_only) ----
    if (pl.status == STATUS_SLEEP)     tags |= CONCEDE_SLEEP_ACTING;  // incl. Rest self-sleep
    if (pl.status == STATUS_FREEZE)    tags |= CONCEDE_FREEZE;
    if (pl.status == STATUS_PARALYSIS) tags |= CONCEDE_PARALYSIS;
    if (pl.volatiles & VOLATILE_CONFUSED)  tags |= CONCEDE_CONFUSION;
    if (pl.volatiles & VOLATILE_ATTRACTED) tags |= CONCEDE_ATTRACT;
    // VE_DROWSY (Yawn pending) is a timed volatile, not a status — never fires (Part 1 #1).

    // ---- LOCK_MOVE: player's chosen rampage move ----
    if (pl_move_id > 0 && in_ids(RAMPAGE_MOVES, pl_move_id)) tags |= CONCEDE_LOCK_MOVE;

    // ---- RECHARGE ----
    bool forced_recharge = (player_move.kind == 0 && player_move.move_slot < 0
                            && player_move.move_override < 0);
    if ((pl_move_id > 0 && in_ids(RECHARGE_MOVES, pl_move_id))
        || (pl.volatiles & V_RECHARGING)
        || forced_recharge)
        tags |= CONCEDE_RECHARGE;

    // ---- SUBSTITUTE (either active, or player selecting Substitute) ----
    // Opponent SELECTING Substitute needs no scan: the child carries the volatile and
    // concedes on its own expand.
    if ((pl.volatiles & VOLATILE_SUBSTITUTE) || (opp.volatiles & VOLATILE_SUBSTITUTE)
        || pl_move_id == MOVE_SUBSTITUTE)
        tags |= CONCEDE_SUBSTITUTE;

    // ---- DMG_TABLE_CAVEAT (either attacker/defender) ----
    auto caveat_mon = [](const PokemonState& m) {
        return m.ability == AB_PARENTAL_BOND || m.item == ITEM_METRONOME
            || (m.volatiles & VOLATILE_MINIMIZE) || is_resist_berry(m.item);
    };
    if (caveat_mon(pl) || caveat_mon(opp)) tags |= CONCEDE_DMG_TABLE_CAVEAT;

    // ---- ORDER_RNG: Quick Claw / Quick Draw on either active (conservative over-tag) ----
    if (pl.item == ITEM_QUICK_CLAW || opp.item == ITEM_QUICK_CLAW
        || pl.ability == ABILITY_QUICK_DRAW || opp.ability == ABILITY_QUICK_DRAW)
        tags |= CONCEDE_ORDER_RNG;

    // ---- Player-move HP-dep + MULTI_HIT_HARD (player -> opp direction) ----
    if (hp_dep_tagged(pl_move_id)) tags |= CONCEDE_HP_DEP_MOVE;
    if (multi_hit_hard(s, /*attacker=*/0, pl_move_id, player_move.move_slot))
        tags |= CONCEDE_MULTI_HIT_HARD;

    // ---- AI support scan: FLINCH_SLOWER, ORDER_RNG tie, HP_DEP, MULTI_HIT_HARD ----
    std::vector<ActionProb> ai_probs = cpp_compute_action_probabilities(s, /*ai_idx=*/1);
    for (const ActionProb& ap : ai_probs) {
        if (!(ap.prob > 0.0)) continue;
        if (ap.action.kind != 0) continue;
        int32_t ai_move_id = resolve_move_id(opp, ap.action);
        if (ai_move_id <= 0) continue;

        if (hp_dep_tagged(ai_move_id)) tags |= CONCEDE_HP_DEP_MOVE;

        if (same_bracket_speed_tie(s, pl_move_id, ai_move_id)) tags |= CONCEDE_ORDER_RNG;

        // FLINCH_SLOWER: opponent can flinch AND acts strictly first AND player is not
        // Inner Focus. Ties do not count (ORDER_RNG owns them).
        if (pl.ability != AB_INNER_FOCUS
            && move_can_flinch(ai_move_id, opp.item)
            && acts_strictly_first(s, /*first=*/1, ai_move_id, /*second=*/0, pl_move_id))
            tags |= CONCEDE_FLINCH_SLOWER;

        if (multi_hit_hard(s, /*attacker=*/1, ai_move_id, ap.action.move_slot))
            tags |= CONCEDE_MULTI_HIT_HARD;
    }

    return tags;
}

}  // namespace

uint32_t concede_tags(const BattleState& lo, const BattleState& hi,
                      const ExecAction& player_move) {
    return tags_at(lo, player_move) | tags_at(hi, player_move);
}

std::string concession_tag_names(uint32_t mask) {
    struct Named { uint32_t bit; const char* name; };
    static const Named kNames[] = {
        {CONCEDE_SLEEP_ACTING,    "SLEEP_ACTING"},
        {CONCEDE_FREEZE,          "FREEZE"},
        {CONCEDE_PARALYSIS,       "PARALYSIS"},
        {CONCEDE_CONFUSION,       "CONFUSION"},
        {CONCEDE_ATTRACT,         "ATTRACT"},
        {CONCEDE_LOCK_MOVE,       "LOCK_MOVE"},
        {CONCEDE_RECHARGE,        "RECHARGE"},
        {CONCEDE_FLINCH_SLOWER,   "FLINCH_SLOWER"},
        {CONCEDE_ORDER_RNG,       "ORDER_RNG"},
        {CONCEDE_HP_DEP_MOVE,     "HP_DEP_MOVE"},
        {CONCEDE_MULTI_HIT_HARD,  "MULTI_HIT_HARD"},
        {CONCEDE_SUBSTITUTE,      "SUBSTITUTE"},
        {CONCEDE_DMG_TABLE_CAVEAT,"DMG_TABLE_CAVEAT"},
    };
    std::string out;
    for (const Named& n : kNames) {
        if (mask & n.bit) {
            if (!out.empty()) out += '|';
            out += n.name;
        }
    }
    return out;
}
