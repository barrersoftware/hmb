/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Fixed-Stride Contiguous Slab Manager (hmb_slab.hpp)
 * Standard: HMB Spec 2.0
 * 
 * Manages contiguous memory blocks with power-of-2 strides.
 * Guaranteed O(1) slot resolution via bit-shifts.
 * ============================================================================
 */

#pragma once

#include "hmb.h"
#include "hmb_bitmask.hpp"
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <concepts>

namespace hmb {

template <size_t StrideBytes>
    requires (StrideBytes >= 64 && (StrideBytes & (StrideBytes - 1)) == 0) // Must be power of 2 >= 64
class HmbSlab {
public:
    static constexpr size_t STRIDE = StrideBytes;
    static constexpr uint32_t STRIDE_SHIFT = []() constexpr {
        uint32_t shift = 0;
        size_t temp = StrideBytes;
        while (temp > 1) { temp >>= 1; shift++; }
        return shift;
    }();

private:
    uint8_t*   m_baseMemory{nullptr};
    size_t     m_totalBytes{0};
    size_t     m_slotCapacity{0};
    uint64_t*  m_bitmapMemory{nullptr};
    HmbBitmask m_bitmask;
    bool       m_ownsMemory{false};

public:
    HmbSlab() noexcept = default;

    /**
     * @brief Construct an HMB slab over an externally provided contiguous memory buffer.
     */
    HmbSlab(void* baseMemory, size_t totalBytes, void* bitmapBuffer = nullptr) noexcept {
        bind(baseMemory, totalBytes, bitmapBuffer);
    }

    ~HmbSlab() noexcept {
        if (m_ownsMemory && m_baseMemory) {
            delete[] m_baseMemory;
            m_baseMemory = nullptr;
        }
    }

    // Move constructible
    HmbSlab(HmbSlab&& other) noexcept
        : m_baseMemory(other.m_baseMemory),
          m_totalBytes(other.m_totalBytes),
          m_slotCapacity(other.m_slotCapacity),
          m_bitmapMemory(other.m_bitmapMemory),
          m_bitmask(other.m_bitmask),
          m_ownsMemory(other.m_ownsMemory)
    {
        other.m_baseMemory = nullptr;
        other.m_ownsMemory = false;
    }

    HmbSlab& operator=(HmbSlab&& other) noexcept {
        if (this != &other) {
            if (m_ownsMemory && m_baseMemory) delete[] m_baseMemory;
            m_baseMemory = other.m_baseMemory;
            m_totalBytes = other.m_totalBytes;
            m_slotCapacity = other.m_slotCapacity;
            m_bitmapMemory = other.m_bitmapMemory;
            m_bitmask = other.m_bitmask;
            m_ownsMemory = other.m_ownsMemory;
            other.m_baseMemory = nullptr;
            other.m_ownsMemory = false;
        }
        return *this;
    }

    void bind(void* baseMemory, size_t totalBytes, void* bitmapBuffer = nullptr) noexcept {
        m_baseMemory = static_cast<uint8_t*>(baseMemory);
        m_totalBytes = totalBytes;
        m_slotCapacity = totalBytes / STRIDE;
        m_ownsMemory = false;

        if (bitmapBuffer) {
            m_bitmapMemory = static_cast<uint64_t*>(bitmapBuffer);
            m_bitmask.bind(m_bitmapMemory, m_slotCapacity);
        }
    }

    /**
     * @brief Pure O(1) Address Resolution: Offset = slotIndex << STRIDE_SHIFT.
     */
    [[nodiscard]] inline uint8_t* resolve(uint64_t slotIndex) const noexcept {
        if (!m_baseMemory || slotIndex >= m_slotCapacity) return nullptr;
        return m_baseMemory + (slotIndex << STRIDE_SHIFT);
    }

    /**
     * @brief Inverse Resolution: slotIndex = (ptr - base) >> STRIDE_SHIFT.
     */
    [[nodiscard]] inline uint64_t getSlotIndex(const void* ptr) const noexcept {
        if (!m_baseMemory || ptr < m_baseMemory) return UINT64_MAX;
        uintptr_t diff = reinterpret_cast<uintptr_t>(ptr) - reinterpret_cast<uintptr_t>(m_baseMemory);
        uint64_t idx = static_cast<uint64_t>(diff >> STRIDE_SHIFT);
        return (idx < m_slotCapacity) ? idx : UINT64_MAX;
    }

    /**
     * @brief Pure O(1) byte offset from slab base.
     */
    [[nodiscard]] inline uint64_t getByteOffset(uint64_t slotIndex) const noexcept {
        return slotIndex << STRIDE_SHIFT;
    }

    [[nodiscard]] uint64_t allocateSlot() noexcept {
        return m_bitmask.allocateFirstFree();
    }

    void releaseSlot(uint64_t slotIndex) noexcept {
        m_bitmask.release(slotIndex);
    }

    [[nodiscard]] bool isSlotAllocated(uint64_t slotIndex) const noexcept {
        return m_bitmask.isAllocated(slotIndex);
    }

    [[nodiscard]] size_t getCapacity() const noexcept { return m_slotCapacity; }
    [[nodiscard]] size_t getTotalBytes() const noexcept { return m_totalBytes; }
    [[nodiscard]] size_t getAllocatedCount() const noexcept { return m_bitmask.countAllocated(); }
    [[nodiscard]] size_t getFreeCount() const noexcept {
        size_t allocated = getAllocatedCount();
        return (m_slotCapacity > allocated) ? (m_slotCapacity - allocated) : 0;
    }
    [[nodiscard]] uint8_t* getBasePointer() const noexcept { return m_baseMemory; }
    [[nodiscard]] static constexpr size_t getStride() noexcept { return STRIDE; }
    [[nodiscard]] static constexpr uint32_t getStrideShift() noexcept { return STRIDE_SHIFT; }
};

} // namespace hmb
