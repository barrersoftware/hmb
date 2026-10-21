/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Example 01: AI Tensor Streaming
 * Standard: HMB Spec 2.0
 * 
 * Demonstrates streaming model weights and KV cache tensors into fixed-stride
 * memory slabs with pure O(1) addressing and zero memory copies.
 * ============================================================================
 */

#include "hmb/hmb.hpp"
#include <iostream>
#include <vector>
#include <cmath>

struct TensorBlock {
    static constexpr size_t DIM = 1024; // 1024 floats = 4096 bytes (Exact 4KB Page)
    float weights[DIM];
};

int main() {
    std::cout << "=== HMB Example 01: Zero-Copy AI Tensor Streaming ===\n";

    // 1. Initialize a 64 MB HMB bus with 4096-byte (4KB) strides
    constexpr size_t totalBytes = 64 * 1024 * 1024;
    hmb::HmbMemoryBus<sizeof(TensorBlock)> bus(totalBytes);

    std::cout << "[AI Stream] Memory Bus initialized: " << totalBytes / (1024 * 1024) 
              << " MB, Capacity: " << bus.getCapacity() << " tensor blocks.\n";

    // 2. Stream 8 model layers into Tier 0 (Hot Working Set)
    std::vector<uint64_t> layerSlots;
    for (int layer = 0; layer < 8; ++layer) {
        uint64_t slot = bus.allocateSlot(hmb::Tier::HotWorkingSet);
        layerSlots.push_back(slot);

        // Resolve direct pointer and populate weights
        auto* block = reinterpret_cast<TensorBlock*>(bus.resolveAddress(slot));
        for (size_t d = 0; d < TensorBlock::DIM; ++d) {
            block->weights[d] = std::sin(static_cast<float>(layer * 100 + d));
        }

        std::cout << "  Layer " << layer << " -> Slot " << slot 
                  << " [Offset 0x" << std::hex << bus.getOffset(slot) << std::dec << "]\n";
    }

    // 3. Clustered prefetch before inference forward pass
    bus.prefetchCluster(layerSlots[0]);
    std::cout << "[AI Stream] Clustered DMA burst prefetched for Layer 0.\n";

    // 4. Zero-copy read during forward pass
    const auto* layer0 = reinterpret_cast<const TensorBlock*>(bus.resolveAddress(layerSlots[0]));
    std::cout << "[AI Stream] Inferred Layer 0 Weight[0]: " << layer0->weights[0] 
              << ", Weight[1023]: " << layer0->weights[1023] << "\n";

    // Cleanup
    for (auto slot : layerSlots) {
        bus.releaseSlot(slot);
    }
    std::cout << "[AI Stream] All tensor slabs cleanly released. Active: " << bus.getAllocatedCount() << "\n";
    return 0;
}
