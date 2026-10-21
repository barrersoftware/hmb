/**
 * ============================================================================
 * Haven Memory Bus (HMB) - 64-Bit Bit Memory Vector Engine (hmb_bitmask.hpp)
 * Standard: HMB Spec 2.0
 * 
 * Implements hardware-accelerated 64-bit word bitmaps for lock-free
 * state tracking of memory slots across all 4 HMB tiers.
 * ============================================================================
 */

#pragma once

#include <cstdint>
#include <cstddef>
#include <atomic>

#if defined(_MSC_VER) && !defined(__clang__)
#include <intrin.h>
#endif

namespace hmb {

class HmbBitmask {
private:
    uint64_t* m_words{nullptr};
    size_t    m_totalSlots{0};
    size_t    m_wordCount{0};

public:
    constexpr HmbBitmask() noexcept = default;

    HmbBitmask(uint64_t* wordBuffer, size_t totalSlots) noexcept
        : m_words(wordBuffer), m_totalSlots(totalSlots), m_wordCount((totalSlots + 63) / 64) {}

    void bind(uint64_t* wordBuffer, size_t totalSlots) noexcept {
        m_words = wordBuffer;
        m_totalSlots = totalSlots;
        m_wordCount = (totalSlots + 63) / 64;
    }

    void clearAll() noexcept {
        if (!m_words) return;
        for (size_t i = 0; i < m_wordCount; ++i) {
            m_words[i] = 0;
        }
    }

    /**
     * @brief Find first available (clear) bit and atomically set it.
     * @return Allocated slot index, or UINT64_MAX if fully exhausted.
     */
    [[nodiscard]] uint64_t allocateFirstFree() noexcept {
        if (!m_words) return UINT64_MAX;

        for (size_t w = 0; w < m_wordCount; ++w) {
            auto* atomicWord = reinterpret_cast<std::atomic<uint64_t>*>(&m_words[w]);
            uint64_t current = atomicWord->load(std::memory_order_relaxed);

            while (current != 0xFFFFFFFFFFFFFFFFULL) {
                // Find index of first zero bit using trailing zeros of inverted word
                uint64_t inverted = ~current;
#if defined(__x86_64__) || defined(_M_X64)
#if defined(__GNUC__) || defined(__clang__)
                int bit = __builtin_ctzll(inverted);
#else
                unsigned long bit = 0;
                _BitScanForward64(&bit, inverted);
#endif
#else
                int bit = 0;
                while ((inverted & (1ULL << bit)) == 0 && bit < 64) bit++;
#endif
                uint64_t targetIndex = (w * 64) + bit;
                if (targetIndex >= m_totalSlots) return UINT64_MAX;

                uint64_t updated = current | (1ULL << bit);
                if (atomicWord->compare_exchange_weak(current, updated, std::memory_order_acquire, std::memory_order_relaxed)) {
                    return targetIndex;
                }
            }
        }
        return UINT64_MAX;
    }

    /**
     * @brief Release an allocated slot by clearing its corresponding bit.
     */
    void release(uint64_t slotIndex) noexcept {
        if (!m_words || slotIndex >= m_totalSlots) return;

        size_t wordIdx = slotIndex / 64;
        int bitIdx = static_cast<int>(slotIndex % 64);
        auto* atomicWord = reinterpret_cast<std::atomic<uint64_t>*>(&m_words[wordIdx]);

        atomicWord->fetch_and(~(1ULL << bitIdx), std::memory_order_release);
    }

    /**
     * @brief Test whether a specific slot is currently allocated.
     */
    [[nodiscard]] bool isAllocated(uint64_t slotIndex) const noexcept {
        if (!m_words || slotIndex >= m_totalSlots) return false;
        size_t wordIdx = slotIndex / 64;
        int bitIdx = static_cast<int>(slotIndex % 64);
        return (m_words[wordIdx] & (1ULL << bitIdx)) != 0;
    }

    /**
     * @brief Count total currently allocated slots across all 64-bit words.
     */
    [[nodiscard]] size_t countAllocated() const noexcept {
        if (!m_words) return 0;
        size_t total = 0;
        for (size_t i = 0; i < m_wordCount; ++i) {
#if defined(__GNUC__) || defined(__clang__)
            total += __builtin_popcountll(m_words[i]);
#elif defined(_MSC_VER) && (defined(__x86_64__) || defined(_M_X64))
            total += __popcnt64(m_words[i]);
#else
            uint64_t v = m_words[i];
            v = v - ((v >> 1) & 0x5555555555555555ULL);
            v = (v & 0x3333333333333333ULL) + ((v >> 2) & 0x3333333333333333ULL);
            total += (((v + (v >> 4)) & 0x0F0F0F0F0F0F0F0FULL) * 0x0101010101010101ULL) >> 56;
#endif
        }
        return total;
    }

    [[nodiscard]] size_t getTotalSlots() const noexcept { return m_totalSlots; }
    [[nodiscard]] size_t getWordCount() const noexcept { return m_wordCount; }
};

} // namespace hmb
