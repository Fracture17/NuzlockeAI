// PP canonicalization: masked-slot PP rewrite + cycle-capable classification + PP horizon.
#include "solver/bucket/pp_canon.h"

namespace {

// Pure self-target heal moves this engine implements (effects.cpp apply_recovery_move,
// self-target branches only): RECOVERY_HALF, Life Dew, Wish, Swallow, Strength Sap, Rest.
// Heal Pulse (heals the OPPONENT) and Heal Bell / Aromatherapy (cure status, no heal) are
// deliberately excluded.
bool is_self_heal(int32_t move_id) {
    switch (move_id) {
        case 105:  // Recover
        case 135:  // Soft-Boiled
        case 208:  // Milk Drink
        case 303:  // Slack Off
        case 456:  // Heal Order
        case 355:  // Roost
        case 234:  // Moonlight
        case 235:  // Morning Sun
        case 236:  // Synthesis
        case 659:  // Shore Up
        case 791:  // Life Dew
        case 273:  // Wish
        case 256:  // Swallow
        case 668:  // Strength Sap
        case 156:  // Rest
            return true;
        default:
            return false;
    }
}

// Apply the {0,>0}-preserving rewrite to one (move_id, pp) slot in place.
void canonicalize_slot(int32_t move_id, int32_t& pp) {
    if (is_cycle_capable_move(move_id)) return;
    if (pp > 0) pp = kPpSentinel;
}

// Every engine read of turns_in_battle is a threshold check with threshold < kTurnsInBattleClamp
// (see pp_canon.h audit table), so collapsing every value >= the clamp to the clamp itself is
// fully behavior-preserving -- unlike PP masking, this loses no accuracy and needs no audit.
constexpr int32_t kTurnsInBattleClamp = 5;

void canonicalize_mon(PokemonState& m) {
    canonicalize_slot(m.move_id0, m.move_pp0);
    canonicalize_slot(m.move_id1, m.move_pp1);
    canonicalize_slot(m.move_id2, m.move_pp2);
    canonicalize_slot(m.move_id3, m.move_pp3);
    if (m.turns_in_battle > kTurnsInBattleClamp) m.turns_in_battle = kTurnsInBattleClamp;
}

int32_t mon_pp_sum(const PokemonState& m) {
    int32_t s = 0;
    if (m.move_pp0 > 0) s += m.move_pp0;
    if (m.move_pp1 > 0) s += m.move_pp1;
    if (m.move_pp2 > 0) s += m.move_pp2;
    if (m.move_pp3 > 0) s += m.move_pp3;
    return s;
}

}  // namespace

bool is_cycle_capable_move(int32_t move_id) {
    return is_self_heal(move_id);
}

void canonicalize_pp(BattleState& s) {
    for (auto& m : s.side0.team) canonicalize_mon(m);
    for (auto& m : s.side1.team) canonicalize_mon(m);
}

int32_t pp_horizon(const BattleState& s) {
    int32_t total = 0;
    for (const auto& m : s.side0.team) total += mon_pp_sum(m);
    for (const auto& m : s.side1.team) total += mon_pp_sum(m);
    return total + 8;
}
