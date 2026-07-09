// Fixed-capacity, header-only small-vector template. Trivially copyable when T is.
// Overflow fails loudly (abort with a message) in ALL build configurations.
// Solver hot path: BattleState will be memcpy-copied millions of times, so no heap ownership.
#pragma once
#ifndef NUZLOCKE_INLINE_VEC_H
#define NUZLOCKE_INLINE_VEC_H

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <type_traits>
#include <utility>

// Fail-loud helper: prints the failure and aborts. Not compiled out in Release.
// Kept as a function-like macro so it captures __FILE__/__LINE__ at the call site.
#define NUZLOCKE_INLINE_VEC_ABORT(msg) \
    do { \
        std::fprintf(stderr, "InlineVec fatal: %s at %s:%d\n", (msg), __FILE__, __LINE__); \
        std::abort(); \
    } while (0)

template <typename T, std::size_t N>
struct InlineVec {
    static_assert(N > 0, "InlineVec capacity must be > 0");

    // Storage: raw array plus a size counter. Both trivially copyable when T is.
    T data_[N]{};
    std::uint16_t size_ = 0;

    // ---- capacity / size ----
    static constexpr std::size_t capacity() { return N; }
    std::size_t size() const { return static_cast<std::size_t>(size_); }
    bool empty() const { return size_ == 0; }

    // ---- element access ----
    T&       operator[](std::size_t i)       { return data_[i]; }
    const T& operator[](std::size_t i) const { return data_[i]; }
    T*       data()       { return data_; }
    const T* data() const { return data_; }
    T&       front()       { return data_[0]; }
    const T& front() const { return data_[0]; }
    T&       back()       { return data_[size_ - 1]; }
    const T& back() const { return data_[size_ - 1]; }

    // ---- iteration ----
    T*       begin()       { return data_; }
    const T* begin() const { return data_; }
    T*       end()       { return data_ + size_; }
    const T* end() const { return data_ + size_; }

    // ---- mutation ----
    void clear() {
        // Overwrite live slots with T{} so state equality/hashing on the tail remains stable.
        for (std::size_t i = 0; i < size_; ++i) data_[i] = T{};
        size_ = 0;
    }

    void push_back(const T& v) {
        if (size_ >= N) NUZLOCKE_INLINE_VEC_ABORT("InlineVec push_back overflow");
        data_[size_++] = v;
    }

    void pop_back() {
        if (size_ == 0) NUZLOCKE_INLINE_VEC_ABORT("InlineVec pop_back underflow");
        --size_;
        data_[size_] = T{};
    }

    // Replace contents with `count` copies of `v` (mirrors std::vector::assign).
    void assign(std::size_t count, const T& v) {
        if (count > N) NUZLOCKE_INLINE_VEC_ABORT("InlineVec assign overflow");
        for (std::size_t i = 0; i < count; ++i) data_[i] = v;
        for (std::size_t i = count; i < size_; ++i) data_[i] = T{};
        size_ = static_cast<std::uint16_t>(count);
    }

    // Assign from an iterator range. Fails loud on overflow.
    // SFINAE-guarded so `assign(count, value)` unambiguously picks the count/value overload.
    template <typename It,
              typename = decltype(*std::declval<It>()),
              typename = decltype(++std::declval<It&>())>
    void assign(It first, It last) {
        std::size_t count = 0;
        for (It it = first; it != last; ++it) {
            if (count >= N) NUZLOCKE_INLINE_VEC_ABORT("InlineVec assign(range) overflow");
            data_[count++] = *it;
        }
        for (std::size_t i = count; i < size_; ++i) data_[i] = T{};
        size_ = static_cast<std::uint16_t>(count);
    }

    // Initializer-list assign — enables `x = {a, b, c}` semantics via a helper.
    void assign(std::initializer_list<T> il) {
        assign(il.begin(), il.end());
    }

    // operator= from initializer_list — matches std::vector<T> = {a,b,c} usage.
    InlineVec& operator=(std::initializer_list<T> il) {
        assign(il);
        return *this;
    }

    // Replace contents from any container providing begin()/end() (e.g. std::vector).
    template <typename C>
    void assign_from(const C& c) {
        assign(c.begin(), c.end());
    }

    // Insert `v` before position `pos` (shifts right). Fails loud on overflow.
    void insert_at(std::size_t pos, const T& v) {
        if (size_ >= N) NUZLOCKE_INLINE_VEC_ABORT("InlineVec insert_at overflow");
        if (pos > size_) NUZLOCKE_INLINE_VEC_ABORT("InlineVec insert_at out-of-range");
        for (std::size_t i = size_; i > pos; --i) data_[i] = data_[i - 1];
        data_[pos] = v;
        ++size_;
    }

    // Erase element at `pos`. Shifts subsequent elements left.
    void erase_at(std::size_t pos) {
        if (pos >= size_) NUZLOCKE_INLINE_VEC_ABORT("InlineVec erase_at out-of-range");
        for (std::size_t i = pos + 1; i < size_; ++i) data_[i - 1] = data_[i];
        --size_;
        data_[size_] = T{};
    }

    // Equality: element-by-element in the live range.
    bool operator==(const InlineVec& other) const {
        if (size_ != other.size_) return false;
        for (std::size_t i = 0; i < size_; ++i)
            if (!(data_[i] == other.data_[i])) return false;
        return true;
    }
    bool operator!=(const InlineVec& other) const { return !(*this == other); }
};

#endif // NUZLOCKE_INLINE_VEC_H
