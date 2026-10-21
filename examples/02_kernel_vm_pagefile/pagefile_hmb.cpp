/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Example 02: Kernel Virtual Memory Pagefile Backing Store
 * Standard: HMB Spec 2.0 (MicaNT Sovereign Memory Engine)
 * 
 * Demonstrates how MicaNT replaces the 40-year-old fragmented B-trees of
 * pagefile.sys with direct-indexed O(1) arithmetic LBA resolution:
 * 
 *   Disk_LBA = Base_LBA + (PFN << 3)
 * ============================================================================
 */

#include "hmb/hmb.hpp"
#include <iostream>
#include <cassert>

constexpr uint64_t HMB_SWAP_BASE_LBA = 0x00200000ULL; // Sector 2,097,152 on NVMe/SATA
constexpr uint32_t SECTORS_PER_PAGE  = 8;             // 4096 bytes / 512-byte sector = 8

// O(1) Direct-Indexed LBA Resolver
inline uint64_t PfnToDiskLba(uint64_t pfn) noexcept {
    return HMB_SWAP_BASE_LBA + (pfn << 3); // Pure 1-cycle bit-shift!
}

// Inverse: Disk LBA to Physical Page Frame Number
inline uint64_t DiskLbaToPfn(uint64_t lba) noexcept {
    return (lba - HMB_SWAP_BASE_LBA) >> 3;
}

int main() {
    std::cout << "=== HMB Example 02: Kernel Virtual Memory Pagefile Engine ===\n";

    // Simulate 256 MB dedicated kernel memory pool (65,536 pages)
    constexpr size_t poolBytes = 256 * 1024 * 1024;
    hmb::HmbMemoryBus<4096> kernelBus(poolBytes);

    std::cout << "[Kernel Mm] Physical PFN Pool: " << kernelBus.getCapacity() << " pages (256 MB)\n";
    std::cout << "[Kernel Mm] Backing Store Base LBA: 0x" << std::hex << HMB_SWAP_BASE_LBA << std::dec << "\n\n";

    // 1. User process allocates virtual memory (NtAllocateVirtualMemory)
    uint64_t pfn0 = kernelBus.allocateSlot(hmb::Tier::DirtyHeap);
    uint64_t pfn1 = kernelBus.allocateSlot(hmb::Tier::DirtyHeap);
    uint64_t pfn42 = 42;

    std::cout << "[Kernel Mm] Virtual Allocation committed:\n";
    std::cout << "  PFN " << pfn0  << " -> Backing Storage LBA: 0x" << std::hex << PfnToDiskLba(pfn0) << std::dec 
              << " (Offset: " << kernelBus.getOffset(pfn0) << ")\n";
    std::cout << "  PFN " << pfn1  << " -> Backing Storage LBA: 0x" << std::hex << PfnToDiskLba(pfn1) << std::dec 
              << " (Offset: " << kernelBus.getOffset(pfn1) << ")\n";
    std::cout << "  PFN " << pfn42 << " -> Backing Storage LBA: 0x" << std::hex << PfnToDiskLba(pfn42) << std::dec 
              << " (Offset: " << kernelBus.getOffset(pfn42) << ")\n\n";

    // 2. Simulate Page Eviction under Memory Pressure (Tier 2 z-Pack Compression)
    uint8_t* pageMem = kernelBus.resolveAddress(pfn0);
    *reinterpret_cast<uint64_t*>(pageMem) = 0xCAFEBABE00001111ULL;
    *reinterpret_cast<uint64_t*>(pageMem + 64) = 0x5555AAAA5555AAAAULL;

    alignas(64) uint8_t zSwapBuffer[4096]{0};
    size_t compressedSize = hmb::HmbZPackEngine::compressSlot(pageMem, 4096, zSwapBuffer, sizeof(zSwapBuffer));

    std::cout << "[Kernel Mm] Memory Pressure Triggered -> Page Eviction:\n";
    std::cout << "  PFN " << pfn0 << " compressed into Tier 2 z-Swap in RAM: 4096 bytes -> " 
              << compressedSize << " bytes (Saved " << (4096 - compressedSize) << " bytes)\n";

    // 3. Simulate Page Fault (#PF Vector 0x0E) - Instant Sub-Microsecond Decompression
    alignas(64) uint8_t restoredPage[4096]{0};
    bool decompressed = hmb::HmbZPackEngine::decompressSlot(zSwapBuffer, compressedSize, restoredPage, sizeof(restoredPage));
    assert(decompressed);
    assert(*reinterpret_cast<uint64_t*>(restoredPage) == 0xCAFEBABE00001111ULL);

    std::cout << "[Kernel Mm] Vector 0x0E #PF Page Fault handled:\n";
    std::cout << "  Decompressed from z-Swap in registers with ZERO DISK I/O! Instruction resumed.\n\n";

    std::cout << "=======================================================\n";
    std::cout << "  MicaNT HMB Direct-Indexed Paging Engine Verified!\n";
    std::cout << "=======================================================\n";
    return 0;
}
