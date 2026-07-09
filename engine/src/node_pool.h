// Header-only slab/chunk pool for fixed-size trivially-copyable nodes (solver groundwork).
// O(1) allocate; grows by adding CHUNK-sized slabs; bulk-freed via reset(). Not thread-safe.
// Nothing uses it yet — this is a standalone tool for the RNG-bucketing solver.
#pragma once
#ifndef NUZLOCKE_NODE_POOL_H
#define NUZLOCKE_NODE_POOL_H

#include <cstddef>
#include <memory>
#include <type_traits>
#include <utility>
#include <vector>

template <typename T, std::size_t ChunkNodes = 1024>
class NodePool {
    static_assert(std::is_trivially_copyable_v<T>,
                  "NodePool node type must be trivially copyable");
    static_assert(ChunkNodes > 0, "ChunkNodes must be > 0");

public:
    NodePool() = default;
    ~NodePool() = default;

    // Non-copyable (owns raw buffers), movable.
    NodePool(const NodePool&) = delete;
    NodePool& operator=(const NodePool&) = delete;
    NodePool(NodePool&&) noexcept = default;
    NodePool& operator=(NodePool&&) noexcept = default;

    // Return a pointer to an uninitialized T slot. O(1); allocates a new slab when the
    // current one is exhausted. Pointer stays stable until reset().
    T* allocate() {
        if (chunks_.empty() || cursor_ == ChunkNodes) {
            chunks_.push_back(std::make_unique<Chunk>());
            cursor_ = 0;
        }
        T* slot = &chunks_.back()->nodes[cursor_++];
        ++size_;
        return slot;
    }

    // Convenience: allocate then default-construct in place (value-init: zeroes trivial types).
    T* emplace() {
        T* slot = allocate();
        *slot = T{};
        return slot;
    }

    // Bulk-free all slabs. Invalidates all previously returned pointers.
    void reset() {
        chunks_.clear();
        cursor_ = 0;
        size_ = 0;
    }

    // Live node count and current buffer capacity.
    std::size_t size() const { return size_; }
    std::size_t capacity() const { return chunks_.size() * ChunkNodes; }
    std::size_t chunk_count() const { return chunks_.size(); }
    static constexpr std::size_t chunk_size() { return ChunkNodes; }

private:
    struct Chunk {
        T nodes[ChunkNodes];
    };
    std::vector<std::unique_ptr<Chunk>> chunks_;
    std::size_t cursor_ = 0;  // next unused slot in the last chunk
    std::size_t size_ = 0;
};

#endif // NUZLOCKE_NODE_POOL_H
