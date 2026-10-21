/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Master C++23 Modern Interface (hmb.hpp)
 * Standard: HMB Spec 2.0 (64-Bit Sovereign Memory Architecture)
 * 
 * Clean-room freestanding ISO C++23. Zero external dependencies.
 * ============================================================================
 */

#pragma once

#include "hmb.h"
#include "hmb_bitmask.hpp"
#include "hmb_slab.hpp"
#include "hmb_cluster.hpp"
#include "hmb_zpack.hpp"
#include <cstdint>
#include <cstddef>
#include <vector>
#include <memory>
#include <string_view>

namespace hmb {

// Tier aliases matching HmbTier enum
enum class Tier : uint32_t {
    HotWorkingSet  = HMB_TIER_HOT_WORKING_SET,
    DirtyHeap       = HMB_TIER_DIRTY_HEAP,
    ZSwapCompressed = HMB_TIER_ZSWAP_COMPRESSED,
    CleanImmutable  = HMB_TIER_CLEAN_IMMUTABLE
};

/**
 * @brief Master Sovereign Memory Bus class managing the full 4-tier memory plane.
 */
template <size_t PageStride = 4096>
class HmbMemoryBus {
public:
    static constexpr size_t PAGE_STRIDE = PageStride;

private:
    HmbSlab<PageStride> m_slab;
    std::vector<uint8_t> m_backingStorage;
    std::vector<uint64_t> m_bitmapStorage;
    bool m_initialized{false};

public:
    HmbMemoryBus() noexcept = default;

    /**
     * @brief Allocate an internal memory pool of given total byte size.
     */
    explicit HmbMemoryBus(size_t totalBytes) {
        initialize(totalBytes);
    }

    void initialize(size_t totalBytes) {
        size_t slots = totalBytes / PAGE_STRIDE;
        size_t words = (slots + 63) / 64;

        m_backingStorage.resize(totalBytes, 0);
        m_bitmapStorage.resize(words, 0);

        m_slab.bind(m_backingStorage.data(), totalBytes, m_bitmapStorage.data());
        m_initialized = true;
    }

    /**
     * @brief Attach the bus over existing hardware memory (e.g. NVMe DMA BAR, Host DRAM slab, or shm).
     */
    void attachExternal(void* memoryBase, size_t totalBytes, uint64_t* bitmapBase) noexcept {
        m_slab.bind(memoryBase, totalBytes, bitmapBase);
        m_initialized = true;
    }

    /**
     * @brief Allocate an O(1) direct slot in the memory bus.
     */
    [[nodiscard]] uint64_t allocateSlot(Tier tier = Tier::HotWorkingSet) noexcept {
        (void)tier;
        return m_slab.allocateSlot();
    }

    /**
     * @brief Release a slot.
     */
    void releaseSlot(uint64_t slotIndex) noexcept {
        m_slab.releaseSlot(slotIndex);
    }

    /**
     * @brief Resolve direct pointer in O(1) time.
     */
    [[nodiscard]] inline uint8_t* resolveAddress(uint64_t slotIndex) const noexcept {
        return m_slab.resolve(slotIndex);
    }

    /**
     * @brief Get physical/virtual byte offset of slot from base.
     */
    [[nodiscard]] inline uint64_t getOffset(uint64_t slotIndex) const noexcept {
        return m_slab.getByteOffset(slotIndex);
    }

    /**
     * @brief Prefetch surrounding cluster into CPU cache for zero-stutter access.
     */
    inline void prefetchCluster(uint64_t slotIndex) const noexcept {
        auto desc = HmbClusterEngine<PageStride>::getClusterForSlot(m_slab, slotIndex);
        HmbClusterEngine<PageStride>::prefetchCluster(desc);
    }

    [[nodiscard]] size_t getCapacity() const noexcept { return m_slab.getCapacity(); }
    [[nodiscard]] size_t getAllocatedCount() const noexcept { return m_slab.getAllocatedCount(); }
    [[nodiscard]] size_t getFreeCount() const noexcept { return m_slab.getFreeCount(); }
    [[nodiscard]] bool isInitialized() const noexcept { return m_initialized; }
    [[nodiscard]] uint8_t* getBase() const noexcept { return m_slab.getBasePointer(); }
};

} // namespace hmb
