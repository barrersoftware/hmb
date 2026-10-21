/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Clustered DMA Burst Engine (hmb_cluster.hpp)
 * Standard: HMB Spec 2.0
 * 
 * Implements Tier 0 / Tier 1 clustered memory transfers.
 * Eliminates single 4KB page fault micro-stutters by prefetching
 * contiguous power-of-two clusters in a single DMA transaction.
 * ============================================================================
 */

#pragma once

#include "hmb_slab.hpp"
#include <cstdint>
#include <cstddef>
#include <concepts>

namespace hmb {

template <size_t StrideBytes, size_t ClusterSlots = 8>
    requires (ClusterSlots >= 1 && (ClusterSlots & (ClusterSlots - 1)) == 0) // Power of 2
class HmbClusterEngine {
public:
    static constexpr size_t CLUSTER_BYTES = StrideBytes * ClusterSlots;
    static constexpr uint32_t CLUSTER_SHIFT = []() constexpr {
        uint32_t shift = 0;
        size_t temp = ClusterSlots;
        while (temp > 1) { temp >>= 1; shift++; }
        return shift;
    }();

    struct ClusterDescriptor {
        uint64_t clusterId{0};
        uint64_t baseSlotIndex{0};
        uint64_t byteOffset{0};
        size_t   byteLength{CLUSTER_BYTES};
        uint8_t* memoryAddress{nullptr};
    };

    /**
     * @brief Given a slot index, calculate the surrounding cluster descriptor for batch DMA.
     */
    static inline ClusterDescriptor getClusterForSlot(const HmbSlab<StrideBytes>& slab, uint64_t slotIndex) noexcept {
        ClusterDescriptor desc{};
        desc.clusterId = slotIndex >> CLUSTER_SHIFT;
        desc.baseSlotIndex = desc.clusterId << CLUSTER_SHIFT;
        desc.byteOffset = slab.getByteOffset(desc.baseSlotIndex);
        desc.byteLength = CLUSTER_BYTES;
        desc.memoryAddress = slab.resolve(desc.baseSlotIndex);
        return desc;
    }

    /**
     * @brief Prefetch an entire cluster into CPU L1/L2 cache lines via hardware prefetch hints.
     */
    static inline void prefetchCluster(const ClusterDescriptor& desc) noexcept {
        if (!desc.memoryAddress) return;
        const uint8_t* p = desc.memoryAddress;
        for (size_t offset = 0; offset < desc.byteLength; offset += 64) {
#if defined(__GNUC__) || defined(__clang__)
            __builtin_prefetch(p + offset, 0, 3);
#elif defined(_MSC_VER) && (defined(__x86_64__) || defined(_M_X64))
            _mm_prefetch(reinterpret_cast<const char*>(p + offset), _MM_HINT_T0);
#endif
        }
    }
};

} // namespace hmb
