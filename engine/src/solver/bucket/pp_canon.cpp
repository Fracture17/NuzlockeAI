// PP canonicalization: masked-slot PP rewrite + cycle-capable classification + PP horizon,
// plus the certificate PP-use audit DP (Task 3).
#include "solver/bucket/pp_canon.h"

#include <stdexcept>
#include <utility>

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

// ---------------------------------------------------------------------------
// Certificate PP-use audit DP (Task 3).
// ---------------------------------------------------------------------------

std::size_t PpSlotKeyHash::operator()(const PpSlotKey& k) const {
    std::size_t h = 1469598103934665603ULL;
    auto mix = [&](uint32_t v) { h ^= v; h *= 1099511628211ULL; };
    mix(static_cast<uint32_t>(k.side));
    mix(static_cast<uint32_t>(k.mon));
    mix(static_cast<uint32_t>(k.slot));
    return h;
}

namespace {

// Add `src` into `dst` slot-wise (sequential consumption along one path).
void add_into(PpConsumption& dst, const PpConsumption& src) {
    for (const auto& [slot, v] : src) dst[slot] += v;
}

// Take the slot-wise MAX of `src` into `dst` (alternative AND-children — the realized line
// takes one path, so children contribute a max rather than a sum).
void max_into(PpConsumption& dst, const PpConsumption& src) {
    for (const auto& [slot, v] : src) {
        auto it = dst.find(slot);
        if (it == dst.end() || v > it->second) dst[slot] = v;
    }
}

// Recursive DP with a 3-color cycle guard. color: 0=unseen, 1=on-path, 2=done.
const PpConsumption& visit_node(const PpCertGraph& g, int i,
                                std::vector<int>& color,
                                std::vector<PpConsumption>& memo) {
    if (color[i] == 2) return memo[i];
    if (color[i] == 1)
        throw std::logic_error("pp_max_consumption: cycle in certificate DAG");
    color[i] = 1;

    const PpCertNode& node = g.nodes[i];
    PpConsumption acc;
    if (node.player_cost > 0) acc[node.player_slot] += node.player_cost;

    PpConsumption child_max;
    for (const PpCertEdge& e : node.children) {
        PpConsumption branch;
        if (e.opp_cost > 0) branch[e.opp_slot] += e.opp_cost;
        if (e.child >= 0) add_into(branch, visit_node(g, e.child, color, memo));
        max_into(child_max, branch);
    }
    add_into(acc, child_max);

    color[i] = 2;
    memo[i] = std::move(acc);
    return memo[i];
}

}  // namespace

PpConsumption pp_max_consumption(const PpCertGraph& graph) {
    if (graph.nodes.empty()) return {};
    std::vector<int> color(graph.nodes.size(), 0);
    std::vector<PpConsumption> memo(graph.nodes.size());
    return visit_node(graph, graph.root, color, memo);
}

bool pp_cert_audit_ok(const PpConsumption& consumption, const PpRootPp& root_pp) {
    for (const auto& [slot, consumed] : consumption) {
        auto it = root_pp.find(slot);
        if (it == root_pp.end())
            throw std::logic_error(
                "pp_cert_audit_ok: consumed slot absent from root PP snapshot");
        const PpRootSlot& rs = it->second;
        if (is_cycle_capable_move(rs.move_id)) continue;   // exact-tracked, exempt
        if (rs.real_pp > 0 && consumed >= rs.real_pp) return false;
    }
    return true;
}
