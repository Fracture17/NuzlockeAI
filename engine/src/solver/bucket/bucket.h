// Bucket: (d = context id, player HP interval, opp HP interval, support fingerprint).
// Guaranteed by construction to contain no interior breakpoint on either axis
// (spec §1.3, INV-1). Conservative merge combines two buckets iff same d + support
// fingerprint AND adjacent/overlapping intervals on one axis with the other axis
// equal — NEVER on damage coincidence. classify_bucket delegates to concrete
// classify() at interval endpoints (valid per INV-2 monotonicity).
#pragma once
#ifndef NUZLOCKE_SOLVER_BUCKET_BUCKET_H
#define NUZLOCKE_SOLVER_BUCKET_BUCKET_H

#include "solver/bucket/breakpoints.h"
#include "solver/question.h"
#include "solver/state_codec.h"

#include <cstdint>
#include <optional>

// Inclusive HP interval [lo, hi] on one axis. lo <= hi.
struct HpInterval {
    int32_t lo;
    int32_t hi;
};

// One bucket in the partition search. d = ContextInterner ctx_id; support_fp is a
// hash/fingerprint of the AI support set (constant across the bucket by INV-1). The
// constructor THROWS std::runtime_error if either interval contains an interior
// breakpoint per the given BpSet or if lo > hi.
class Bucket {
public:
    Bucket(uint32_t d, HpInterval player_hp, HpInterval opp_hp,
           uint64_t support_fp, const BpSet& bp);

    // Internal factory: build a Bucket bypassing the interior-breakpoint check.
    // ONLY for use by try_merge (and future in-package callers) where the
    // resulting bucket's validity is derivable from the invariants of the
    // inputs (both source buckets already validated, adjacency implies no
    // hidden breakpoint sits between them).
    static Bucket make_unchecked(uint32_t d, HpInterval player_hp,
                                 HpInterval opp_hp, uint64_t support_fp);

    uint32_t          d()          const { return d_; }
    const HpInterval& player_hp()  const { return player_hp_; }
    const HpInterval& opp_hp()     const { return opp_hp_; }
    uint64_t          support_fp() const { return support_fp_; }

private:
    struct UncheckedTag {};
    Bucket(UncheckedTag, uint32_t d, HpInterval player_hp,
           HpInterval opp_hp, uint64_t support_fp)
        : d_(d), player_hp_(player_hp), opp_hp_(opp_hp), support_fp_(support_fp) {}

    uint32_t   d_;
    HpInterval player_hp_;
    HpInterval opp_hp_;
    uint64_t   support_fp_;
};

// Conservative merge (spec §1.3 / SOLVER_BUCKET_PLAN Part 1 amendment): return the
// unioned bucket iff a and b share d + support_fp AND their intervals differ on
// exactly one axis with adjacent/overlapping ranges (the other axis equal). Returns
// std::nullopt otherwise. Never merges on damage coincidence.
std::optional<Bucket> try_merge(const Bucket& a, const Bucket& b);

// Classify a bucket under a Question by evaluating concrete classify() at both HP
// endpoint corners (INV-2 monotonicity ⇒ endpoints suffice):
//   WIN     iff every corner classifies WIN
//   CONTINUE iff every corner classifies CONTINUE
//   LOSS otherwise (mixture or any LOSS)
// Consistency (see question_conjunctive_semantics record): the bucket verdict must
// agree with concrete classify() on every member — enforced by tests.
Outcome classify_bucket(const Bucket& b, const Question& q, const ContextInterner& interner);

#endif // NUZLOCKE_SOLVER_BUCKET_BUCKET_H
