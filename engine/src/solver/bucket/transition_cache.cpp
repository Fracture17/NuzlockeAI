// TransitionCache: FNV-1a keying + hit/miss-counting edge store (plan Task 1).
#include "solver/bucket/transition_cache.h"

#include <utility>

namespace {

constexpr std::size_t kFnvOffset = 1469598103934665603ULL;
constexpr std::size_t kFnvPrime  = 1099511628211ULL;

inline void fnv_mix(std::size_t& h, uint64_t v) {
    h ^= static_cast<std::size_t>(v);
    h *= kFnvPrime;
}

}  // namespace

uint64_t bp_fingerprint(const BpSet& bp) {
    std::size_t h = kFnvOffset;
    const auto& player = bp.player_breakpoints();
    const auto& opp    = bp.opp_breakpoints();
    fnv_mix(h, player.size());
    for (int32_t v : player) fnv_mix(h, static_cast<uint32_t>(v));
    fnv_mix(h, opp.size());
    for (int32_t v : opp) fnv_mix(h, static_cast<uint32_t>(v));
    fnv_mix(h, static_cast<uint32_t>(bp.player_max_hp()));
    fnv_mix(h, static_cast<uint32_t>(bp.opp_max_hp()));
    return h;
}

std::size_t EdgeKeyHash::operator()(const EdgeKey& k) const {
    std::size_t h = kFnvOffset;
    fnv_mix(h, k.bucket.d);
    fnv_mix(h, static_cast<uint32_t>(k.bucket.pl_lo));
    fnv_mix(h, static_cast<uint32_t>(k.bucket.pl_hi));
    fnv_mix(h, static_cast<uint32_t>(k.bucket.op_lo));
    fnv_mix(h, static_cast<uint32_t>(k.bucket.op_hi));
    fnv_mix(h, k.bp_fp);
    fnv_mix(h, static_cast<uint32_t>(k.kind));
    fnv_mix(h, static_cast<uint32_t>(k.move_slot));
    fnv_mix(h, static_cast<uint32_t>(k.move_override));
    fnv_mix(h, static_cast<uint32_t>(k.switch_to_slot));
    fnv_mix(h, static_cast<uint32_t>(k.target_side));
    fnv_mix(h, static_cast<uint32_t>(k.target_slot));
    fnv_mix(h, static_cast<uint32_t>(k.source_slot));
    fnv_mix(h, k.mega ? 1u : 0u);
    return h;
}

void TransitionCache::require_mode(Mode m) {
    if (mode_ == Mode::Unset) {
        mode_ = m;
        return;
    }
    if (mode_ != m)
        throw std::logic_error(
            "TransitionCache::require_mode: canonical/exact regime mismatch on a shared cache");
}

const ExpandResult* TransitionCache::lookup(const EdgeKey& key) {
    auto it = edges_.find(key);
    if (it == edges_.end()) {
        ++stats.misses;
        return nullptr;
    }
    ++stats.hits;
    return &it->second;
}

void TransitionCache::insert(const EdgeKey& key, ExpandResult result) {
    auto [it, inserted] = edges_.emplace(key, std::move(result));
    (void)it;
    if (!inserted)
        throw std::logic_error("TransitionCache::insert: duplicate EdgeKey");
}
