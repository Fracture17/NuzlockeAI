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
    // absorb the throw census).
    BpSet instantiate(const BattleState& state, const Question& q) const;
};

#endif // NUZLOCKE_SOLVER_BUCKET_BREAKPOINTS_H
