// Bucket construction (with interior-breakpoint guard), conservative merge, and
// endpoint-corner classify_bucket. See bucket.h for invariants.
#include "solver/bucket/bucket.h"

#include <algorithm>
#include <stdexcept>
#include <string>

// ---------------------------------------------------------------------------
// Bucket
// ---------------------------------------------------------------------------

// Throw if the interval violates INV-1 for its axis (range out of [0,max_hp],
// inverted, or containing a strictly-interior breakpoint).
static void validate_interval(const char* axis, const HpInterval& iv,
                              const BpSet& bp, bool is_player) {
    if (iv.lo > iv.hi) {
        throw std::runtime_error(std::string("Bucket: ") + axis
            + " interval has lo > hi (lo=" + std::to_string(iv.lo)
            + ", hi=" + std::to_string(iv.hi) + ")");
    }
    int32_t max_hp = is_player ? bp.player_max_hp() : bp.opp_max_hp();
    if (iv.lo < 0 || iv.hi > max_hp) {
        throw std::runtime_error(std::string("Bucket: ") + axis
            + " interval [" + std::to_string(iv.lo) + ", " + std::to_string(iv.hi)
            + "] out of range [0, " + std::to_string(max_hp) + "]");
    }
    bool bad = is_player ? bp.player_has_interior_breakpoint(iv.lo, iv.hi)
                         : bp.opp_has_interior_breakpoint(iv.lo, iv.hi);
    if (bad) {
        throw std::runtime_error(std::string("Bucket: ") + axis
            + " interval [" + std::to_string(iv.lo) + ", " + std::to_string(iv.hi)
            + "] contains an interior breakpoint (INV-1 violated)");
    }
}

Bucket::Bucket(uint32_t d, HpInterval player_hp, HpInterval opp_hp,
               uint64_t support_fp, const BpSet& bp)
    : d_(d), player_hp_(player_hp), opp_hp_(opp_hp), support_fp_(support_fp) {
    validate_interval("player", player_hp_, bp, /*is_player=*/true);
    validate_interval("opp",    opp_hp_,    bp, /*is_player=*/false);
}

Bucket Bucket::make_unchecked(uint32_t d, HpInterval player_hp,
                              HpInterval opp_hp, uint64_t support_fp) {
    return Bucket(UncheckedTag{}, d, player_hp, opp_hp, support_fp);
}

// ---------------------------------------------------------------------------
// try_merge
// ---------------------------------------------------------------------------

// Adjacent-or-overlapping test on inclusive intervals: overlap iff min(hi) >= max(lo);
// otherwise adjacent (touching by 1) iff one hi + 1 == other lo.
static bool adjacent_or_overlapping(const HpInterval& a, const HpInterval& b) {
    int32_t lo = std::max(a.lo, b.lo);
    int32_t hi = std::min(a.hi, b.hi);
    if (hi >= lo) return true;
    if (a.hi + 1 == b.lo) return true;
    if (b.hi + 1 == a.lo) return true;
    return false;
}

static bool intervals_equal(const HpInterval& a, const HpInterval& b) {
    return a.lo == b.lo && a.hi == b.hi;
}

static HpInterval union_interval(const HpInterval& a, const HpInterval& b) {
    return HpInterval{std::min(a.lo, b.lo), std::max(a.hi, b.hi)};
}

std::optional<Bucket> try_merge(const Bucket& a, const Bucket& b) {
    // Same d and same support fingerprint are required — never merge on damage
    // coincidence alone (spec §1.3).
    if (a.d() != b.d()) return std::nullopt;
    if (a.support_fp() != b.support_fp()) return std::nullopt;

    const HpInterval& pa = a.player_hp();
    const HpInterval& pb = b.player_hp();
    const HpInterval& oa = a.opp_hp();
    const HpInterval& ob = b.opp_hp();

    bool pl_eq  = intervals_equal(pa, pb);
    bool opp_eq = intervals_equal(oa, ob);

    if (pl_eq && opp_eq) return a;  // identical → idempotent merge

    // Union is safe against INV-1 because both source buckets already satisfy INV-1
    // and adjacency implies no breakpoint sits strictly between them (else one of
    // them would have contained it).
    if (pl_eq && adjacent_or_overlapping(oa, ob)) {
        return Bucket::make_unchecked(a.d(), a.player_hp(),
                                      union_interval(oa, ob), a.support_fp());
    }
    if (opp_eq && adjacent_or_overlapping(pa, pb)) {
        return Bucket::make_unchecked(a.d(), union_interval(pa, pb),
                                      a.opp_hp(), a.support_fp());
    }
    return std::nullopt;
}

// ---------------------------------------------------------------------------
// classify_bucket
// ---------------------------------------------------------------------------

// Unpack (d, pl_hp, opp_hp) and run the concrete Question classifier on it.
static Outcome classify_corner(uint32_t d, int32_t pl_hp, int32_t opp_hp,
                               const Question& q, const ContextInterner& interner) {
    if (pl_hp  < 0 || pl_hp  > 0xFFFF ||
        opp_hp < 0 || opp_hp > 0xFFFF) {
        throw std::runtime_error("classify_bucket: HP endpoint out of 16-bit range");
    }
    PackedKey k = make_packed_key(d,
                                  static_cast<uint16_t>(pl_hp),
                                  static_cast<uint16_t>(opp_hp));
    BattleState concrete = interner.unpack(k);
    return classify(concrete, q);
}

Outcome classify_bucket(const Bucket& b, const Question& q, const ContextInterner& interner) {
    const HpInterval& pi = b.player_hp();
    const HpInterval& oi = b.opp_hp();

    Outcome c00 = classify_corner(b.d(), pi.lo, oi.lo, q, interner);
    Outcome c01 = classify_corner(b.d(), pi.lo, oi.hi, q, interner);
    Outcome c10 = classify_corner(b.d(), pi.hi, oi.lo, q, interner);
    Outcome c11 = classify_corner(b.d(), pi.hi, oi.hi, q, interner);

    // WIN iff every corner is WIN (INV-3); CONTINUE iff every corner is non-terminal;
    // LOSS iff any concrete corner is LOSS (any failing member ⇒ bucket fails).
    // Mixed WIN/CONTINUE with no losing corner means the bucket straddles a goal
    // boundary at an endpoint — impossible for buckets built from the segment
    // partition, so it is a builder bug: fail loud (INV-3).
    auto all_eq = [&](Outcome o) {
        return c00 == o && c01 == o && c10 == o && c11 == o;
    };
    if (all_eq(Outcome::WIN))      return Outcome::WIN;
    if (all_eq(Outcome::CONTINUE)) return Outcome::CONTINUE;
    if (c00 == Outcome::LOSS || c01 == Outcome::LOSS ||
        c10 == Outcome::LOSS || c11 == Outcome::LOSS) {
        return Outcome::LOSS;
    }
    throw std::runtime_error(
        "classify_bucket: mixed WIN/CONTINUE corners with no losing corner — "
        "bucket straddles a goal boundary (missing split; INV-3 violation)");
}
