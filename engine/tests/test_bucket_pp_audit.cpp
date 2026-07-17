// Certificate PP-use audit tests (PP-canon Task 3), written BEFORE implementation.
// Two layers: (1) pure DP over fabricated certificate DAGs (no search), and (2) end-to-end
// through bucket_win_certify with enable_pp_canon. File-local 1v1 helpers duplicate the
// sibling bucket-solver tests per their "deliberately not shared" convention.
#include <catch2/catch_test_macros.hpp>

#include "ai_analytic.h"
#include "move_exec.h"
#include "solver/bucket/bucket.h"
#include "solver/bucket/expand.h"
#include "solver/bucket/pp_canon.h"
#include "solver/bucket/transition_cache.h"
#include "solver/bucket/win_solver.h"
#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <stdexcept>

// ===========================================================================
// Layer 1 — pure DP over fabricated certificate DAGs.
// ===========================================================================
namespace {

constexpr int32_t MV_TACKLE   = 33;
constexpr int32_t MV_SPLASH   = 150;
constexpr int32_t MV_RECOVER  = 105;   // cycle-capable (self-heal)
constexpr int32_t AB_SHELL_ARMOR = 75;
constexpr int32_t AB_PRESSURE    = 46;

PpSlotKey pslot(int slot) { return PpSlotKey{0, 0, slot}; }   // player, mon 0
PpSlotKey oslot(int slot) { return PpSlotKey{1, 0, slot}; }   // opponent, mon 0

// A single-child edge to node `child` (or a terminal leaf when child < 0), no opp cost.
PpCertEdge edge_to(int child) { return PpCertEdge{oslot(0), 0, child}; }

}  // namespace

TEST_CASE("pp_audit DP: linear chain consumes slot once per node", "[pp_audit]") {
    // node2 -> node1 -> node0 (root), each player_cost 1 on slot 0, last node a leaf.
    PpCertGraph g;
    PpCertNode n0; n0.player_slot = pslot(0); n0.player_cost = 1;   // leaf (index 0)
    PpCertNode n1; n1.player_slot = pslot(0); n1.player_cost = 1;
    n1.children.push_back(edge_to(0));
    PpCertNode n2; n2.player_slot = pslot(0); n2.player_cost = 1;
    n2.children.push_back(edge_to(1));
    g.nodes = {n0, n1, n2};
    g.root  = 2;

    PpConsumption c = pp_max_consumption(g);
    REQUIRE(c.at(pslot(0)) == 3);

    // Strict-< acceptance: real PP 4 accepts, 3 rejects, 2 rejects.
    PpRootPp root4{{pslot(0), {4, MV_TACKLE}}};
    PpRootPp root3{{pslot(0), {3, MV_TACKLE}}};
    REQUIRE(pp_cert_audit_ok(c, root4));
    REQUIRE_FALSE(pp_cert_audit_ok(c, root3));
}

TEST_CASE("pp_audit DP: AND-diamond takes per-slot MAX over children, not sum", "[pp_audit]") {
    // Two leaf children each consume slot 0 twice; root adds 1. Max(2,2)+1 = 3, NOT 5.
    PpCertGraph g;
    PpCertNode leaf; leaf.player_slot = pslot(0); leaf.player_cost = 2;   // index 0 and 1
    PpCertNode root; root.player_slot = pslot(0); root.player_cost = 1;
    root.children.push_back(edge_to(0));
    root.children.push_back(edge_to(1));
    g.nodes = {leaf, leaf, root};
    g.root  = 2;

    PpConsumption c = pp_max_consumption(g);
    REQUIRE(c.at(pslot(0)) == 3);

    PpRootPp root3{{pslot(0), {3, MV_TACKLE}}};
    PpRootPp root4{{pslot(0), {4, MV_TACKLE}}};
    REQUIRE_FALSE(pp_cert_audit_ok(c, root3));   // 3 >= 3
    REQUIRE(pp_cert_audit_ok(c, root4));         // 3 < 4
}

TEST_CASE("pp_audit DP: Pressure doubles player cost, flipping a passing PP to a reject",
          "[pp_audit]") {
    // Same 3-node chain but every node costs 2 (opposing Pressure): consumption 6.
    PpCertGraph g;
    PpCertNode n0; n0.player_slot = pslot(0); n0.player_cost = 2;
    PpCertNode n1; n1.player_slot = pslot(0); n1.player_cost = 2; n1.children.push_back(edge_to(0));
    PpCertNode n2; n2.player_slot = pslot(0); n2.player_cost = 2; n2.children.push_back(edge_to(1));
    g.nodes = {n0, n1, n2};
    g.root  = 2;

    PpConsumption c = pp_max_consumption(g);
    REQUIRE(c.at(pslot(0)) == 6);

    // Real PP 4 would PASS at cost 1 (consumption 3) but REJECTS at cost 2 (consumption 6).
    PpRootPp root4{{pslot(0), {4, MV_TACKLE}}};
    REQUIRE_FALSE(pp_cert_audit_ok(c, root4));
}

TEST_CASE("pp_audit DP: opponent slot accounting is symmetric with the player", "[pp_audit]") {
    // Chain where each edge charges the OPPONENT slot 0 once (opp_cost 1) and the player
    // does nothing (player_cost 0). Two edges deep -> opponent consumption 2.
    PpCertGraph g;
    PpCertNode leaf;  leaf.player_slot = pslot(0);  leaf.player_cost = 0;   // index 0
    PpCertNode mid;   mid.player_slot  = pslot(0);  mid.player_cost  = 0;
    mid.children.push_back(PpCertEdge{oslot(0), 1, 0});                     // charges opp once
    PpCertNode root;  root.player_slot = pslot(0);  root.player_cost = 0;
    root.children.push_back(PpCertEdge{oslot(0), 1, 1});                    // charges opp once
    g.nodes = {leaf, mid, root};
    g.root  = 2;

    PpConsumption c = pp_max_consumption(g);
    REQUIRE(c.at(oslot(0)) == 2);
    REQUIRE(c.count(pslot(0)) == 0);   // player never consumed

    PpRootPp ok{{oslot(0), {3, MV_SPLASH}}};
    PpRootPp bad{{oslot(0), {2, MV_SPLASH}}};
    REQUIRE(pp_cert_audit_ok(c, ok));
    REQUIRE_FALSE(pp_cert_audit_ok(c, bad));
}

TEST_CASE("pp_audit DP: cycle-capable slots are exempt from the audit", "[pp_audit]") {
    // Player hammers Recover (cycle-capable) far past its PP; audit still accepts.
    PpCertGraph g;
    PpCertNode n0; n0.player_slot = pslot(0); n0.player_cost = 1;
    PpCertNode n1; n1.player_slot = pslot(0); n1.player_cost = 1; n1.children.push_back(edge_to(0));
    PpCertNode n2; n2.player_slot = pslot(0); n2.player_cost = 1; n2.children.push_back(edge_to(1));
    g.nodes = {n0, n1, n2};
    g.root  = 2;

    PpConsumption c = pp_max_consumption(g);
    PpRootPp root_recover{{pslot(0), {1, MV_RECOVER}}};   // real PP 1, consumption 3
    REQUIRE(pp_cert_audit_ok(c, root_recover));           // exempt -> accepted
}

TEST_CASE("pp_audit DP: a cyclic graph throws (impossible-if-sound certificate)", "[pp_audit]") {
    // node0 -> node1 -> node0 : a policy loop. pp_max_consumption must fail loud.
    PpCertGraph g;
    PpCertNode n0; n0.player_slot = pslot(0); n0.player_cost = 1; n0.children.push_back(edge_to(1));
    PpCertNode n1; n1.player_slot = pslot(0); n1.player_cost = 1; n1.children.push_back(edge_to(0));
    g.nodes = {n0, n1};
    g.root  = 0;
    REQUIRE_THROWS_AS(pp_max_consumption(g), std::logic_error);
}

TEST_CASE("pp_audit DP: consumed slot missing from the root snapshot throws", "[pp_audit]") {
    PpCertGraph g;
    PpCertNode n0; n0.player_slot = pslot(0); n0.player_cost = 1;
    g.nodes = {n0};
    g.root  = 0;
    PpConsumption c = pp_max_consumption(g);
    PpRootPp empty;
    REQUIRE_THROWS_AS(pp_cert_audit_ok(c, empty), std::logic_error);
}

// ===========================================================================
// Layer 2 — end-to-end through bucket_win_certify with enable_pp_canon.
//
// File-local 1v1 state builders (duplicated per convention).
// ===========================================================================
namespace {

struct MonSpec {
    int32_t species = 1;
    int32_t max_hp  = 200;
    int32_t hp      = 200;
    int32_t ability = 0;
    int32_t speed   = 80;
    int32_t move0   = MV_TACKLE;
    int32_t pp0     = 35;
};

PokemonState make_mon(const MonSpec& sp) {
    PokemonState p{};
    p.species = sp.species; p.level = 50; p.has_stats = true;
    p.stat_hp = sp.max_hp; p.stat_atk = 100; p.stat_def = 80; p.stat_spa = 80;
    p.stat_spd = 80; p.stat_spe = sp.speed;
    p.has_max_hp = true; p.max_hp = sp.max_hp;
    p.has_hp = true; p.hp = sp.hp;
    p.move_id0 = sp.move0; p.move_pp0 = sp.move0 ? sp.pp0 : 0;
    p.ability = sp.ability;
    return p;
}

BattleState make_state(const PokemonState& p, const PokemonState& o) {
    BattleState s{};
    s.side0.team.push_back(p); s.side0.active_indices.push_back(0);
    s.side1.team.push_back(o); s.side1.active_indices.push_back(0);
    s.turn_number = 1;
    return s;
}

Bucket child_bucket(const Bucket& A, ExpandContext& ctx, int32_t op) {
    return Bucket(A.d(), A.player_hp(), HpInterval{op, op}, A.support_fp(), *ctx.bp);
}

// A fabricated winning line: player Tackle drops the opponent 20 HP/turn to 0 (terminal WIN).
// Chain length (turns) = ceil(start_hp / 20); the player consumes slot 0 that many times.
ExpandResult chain_override(const Bucket& A, const ExecAction& action, ExpandContext& ctx) {
    ExpandResult r;
    int32_t next = A.opp_hp().hi - 20;
    if (next < 0) next = 0;
    r.children.push_back(ChildBucket{child_bucket(A, ctx, next), action});
    return r;
}

}  // namespace

// ---------------------------------------------------------------------------
// E1 — a WIN whose only line over-uses a masked slot beyond real PP -> PpAuditFail.
// ---------------------------------------------------------------------------

TEST_CASE("pp_audit: masked slot over-use downgrades WIN to INDETERMINATE(PpAuditFail)",
          "[pp_audit]") {
    // Opponent at 60 HP, dropping 20/turn -> 3 player Tackles. Real Tackle PP = 2 < 3.
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE, .pp0 = 2});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 60,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH,
                               .pp0 = 20});
    BattleState s = make_state(p, o);

    BucketWinConfig cfg;
    cfg.enable_pp_canon = true;
    cfg.expand_override = chain_override;
    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);

    REQUIRE(r.verdict == BucketWinVerdict::INDETERMINATE);
    REQUIRE(r.reason == BucketWinIndetReason::PpAuditFail);
    REQUIRE(r.stats.pp_audit_rejects == 1);
    // Policy is deliberately retained for diagnostics.
    REQUIRE_FALSE(r.policy.empty());
}

TEST_CASE("pp_audit: ample real PP keeps the same line a WIN with zero rejects", "[pp_audit]") {
    // Identical shape, but real Tackle PP = 8 > 3 consumption -> WIN survives.
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE, .pp0 = 8});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 60,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH,
                               .pp0 = 20});
    BattleState s = make_state(p, o);

    BucketWinConfig cfg;
    cfg.enable_pp_canon = true;
    cfg.expand_override = chain_override;
    BucketWinResult r = bucket_win_certify(s, Question{}, cfg);

    REQUIRE(r.verdict == BucketWinVerdict::WIN);
    REQUIRE(r.reason == BucketWinIndetReason::None);
    REQUIRE(r.stats.pp_audit_rejects == 0);
}

// ---------------------------------------------------------------------------
// E2 — sound real-expand WIN: enable_pp_canon must not perturb it, and the audit
// path is a pure cache-hit walk (no re-expansions).
// ---------------------------------------------------------------------------

TEST_CASE("pp_audit: sound one-hit-kill WIN survives the audit unchanged", "[pp_audit]") {
    PokemonState p = make_mon({.hp = 200, .speed = 80, .move0 = MV_TACKLE});
    PokemonState o = make_mon({.species = 2, .max_hp = 200, .hp = 5,
                               .ability = AB_SHELL_ARMOR, .speed = 60, .move0 = MV_SPLASH});
    BattleState s = make_state(p, o);

    BucketWinConfig off;              // flag OFF baseline
    BucketWinResult r_off = bucket_win_certify(s, Question{}, off);
    REQUIRE(r_off.verdict == BucketWinVerdict::WIN);

    BucketWinConfig on;
    on.enable_pp_canon = true;
    BucketWinResult r_on = bucket_win_certify(s, Question{}, on);
    REQUIRE(r_on.verdict == BucketWinVerdict::WIN);          // verdict matches flag-OFF
    REQUIRE(r_on.reason == BucketWinIndetReason::None);
    REQUIRE(r_on.stats.pp_audit_rejects == 0);
    REQUIRE(r_on.stats.audit_expands == 0);                 // cache-hit walk, no re-expansion
}
