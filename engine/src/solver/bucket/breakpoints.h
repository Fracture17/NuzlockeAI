// Bucket solver breakpoint set: global one-time BreakpointRegistry that instantiates
// a per-matchup+question BpSet of HP-axis breakpoints. A breakpoint is any HP value
// whose crossing can change AI support, transition semantics, trigger state, or the
// Question's success/failure verdict. Skeleton fill (Task 4) delegates HP-item/ability
// thresholds to hp_thresholds(); Task 8 extends with per-mechanic registry entries.
//
// Partition convention (see partition() / segment_of()): each breakpoint b is its own
// singleton segment [b, b]; every maximal contiguous run of non-breakpoint HP values
// in [0, max_hp] is a segment [lo, hi]. Every HP in [0, max_hp] belongs to exactly one
// segment. A bucket interval is valid iff no breakpoint lies STRICTLY inside (lo, hi)
// — endpoints may equal breakpoints (see bucket.h). This matches spec §1.3 ("no
// breakpoint falls strictly inside").
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_BREAKPOINTS_H
#define NUZLOCKE_SOLVER_BUCKET_BREAKPOINTS_H

#include "solver/question.h"
#include "state.h"

#include <cstdint>
#include <vector>

// A maximal breakpoint-free interval on one HP axis, OR a singleton segment at a
// breakpoint. lo <= hi (inclusive on both sides).
struct HpSegment {
    int32_t lo;
    int32_t hi;
};

// Per-matchup+question instantiated breakpoint set (one axis per side). Contains the
// sorted+deduped breakpoint list, the derived segment partition, and O(log n) lookup.
class BpSet {
public:
    BpSet() = default;

    // Populated by BreakpointRegistry::instantiate. Callers must not construct directly.
    BpSet(std::vector<int32_t> player_bps, std::vector<int32_t> opp_bps,
          int32_t player_max_hp, int32_t opp_max_hp);

    const std::vector<int32_t>& player_breakpoints() const { return player_bps_; }
    const std::vector<int32_t>& opp_breakpoints()    const { return opp_bps_; }
    const std::vector<HpSegment>& player_segments()  const { return player_segs_; }
    const std::vector<HpSegment>& opp_segments()     const { return opp_segs_; }

    int32_t player_max_hp() const { return player_max_hp_; }
    int32_t opp_max_hp()    const { return opp_max_hp_; }

    // Return the index of the segment containing hp, or -1 if hp is out of [0,max_hp].
    int player_segment_of(int32_t hp) const;
    int opp_segment_of(int32_t hp)    const;

    // True iff a breakpoint value lies STRICTLY inside (lo, hi). Endpoints don't count.
    // Used by Bucket construction to enforce "no interior breakpoint" (spec §1.3).
    bool player_has_interior_breakpoint(int32_t lo, int32_t hi) const;
    bool opp_has_interior_breakpoint(int32_t lo, int32_t hi)    const;

private:
    std::vector<int32_t>   player_bps_;
    std::vector<int32_t>   opp_bps_;
    std::vector<HpSegment> player_segs_;
    std::vector<HpSegment> opp_segs_;
    int32_t                player_max_hp_ = 0;
    int32_t                opp_max_hp_    = 0;
};

// Global one-time registry of per-mechanic breakpoint formulas. Skeleton: delegates
// per-axis to hp_thresholds() plus the mandatory {0, max_hp} boundaries and the
// Question's HP boundaries. Task 8 extends this with per-mechanic entries keyed by
// item/ability/move ID + source-reference strings.
class BreakpointRegistry {
public:
    BreakpointRegistry() = default;

    // Instantiate the BpSet for a concrete matchup + question. THROWS
    // std::runtime_error if hp_thresholds() reports residual_unknown on either side —
    // a deliberate difference from analytic UNKNOWN-routing (fail loud; later audits
    // absorb the throw census). Also throws (via registry_static_entries) on any
    // form-changing ability (Power Construct/Schooling/Shields Down/Zen Mode/Gulp
    // Missile) — those mechanics are postponed (Task 8 §4).
    BpSet instantiate(const BattleState& state, const Question& q) const;
};

// Kind tag for a registry_static_entries() breakpoint — identifies the SOURCE
// mechanic (SOLVER_BREAKPOINT_INVENTORY.md §4/§5/§6/§9), not a computed value.
// HalfCrossing:    Berserk/Emergency Exit/Wimp Out, own axis, max_hp/2.
// PinchThird:      Blaze/Torrent/Overgrow/Swarm, own axis, max_hp/3.
// DefeatistHalf:   Defeatist, own axis, max_hp/2.
// BrineHalf:       Brine known by the OTHER side, this axis, max_hp/2.
// SubCostQuarter:  Substitute known, own axis, max_hp/4.
// CostHalf:        Belly Drum known, OR Curse known + Ghost-type user, own axis, max_hp/2.
// HealCapKink:     recovery/heal moves and abilities, own axis, max_hp - heal_amount.
// HazardKink:      Stealth Rock / Spikes, own axis, damage value itself (not max_hp-damage).
enum class BpEntryKind {
    HalfCrossing,
    PinchThird,
    DefeatistHalf,
    BrineHalf,
    SubCostQuarter,
    CostHalf,
    HealCapKink,
    HazardKink,
};

struct BpEntry {
    int32_t hp;
    BpEntryKind kind;
};

// Per-mechanic static breakpoint entries for one axis (side). Reads BOTH actives —
// cross-axis mechanics (Brine, Heal Pulse) key off the OTHER side's moveset but land
// their breakpoint on THIS side's axis. THROWS std::runtime_error containing
// "form-change" if the active mon on `side` holds a form-changing ability (Power
// Construct/Schooling/Shields Down/Zen Mode/Gulp Missile) — those mechanics reshape
// max_hp or stat lines mid-battle and are out of scope for Task 8 (postponed, not
// dropped; see plan §4).
std::vector<BpEntry> registry_static_entries(const BattleState& state, int side);

#endif // NUZLOCKE_SOLVER_BUCKET_BREAKPOINTS_H
