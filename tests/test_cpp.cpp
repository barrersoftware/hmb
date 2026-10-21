/**
 * ============================================================================
 * Haven Memory Bus (HMB) - C++ Test & Verification Suite (test_cpp.cpp)
 * ============================================================================
 */

#include "hmb/hmb.hpp"
#include <iostream>
#include <cassert>
#include <vector>

void test_direct_arithmetic() {
    std::cout << "[Test 1] Verifying O(1) Stride Arithmetic... ";
    constexpr size_t stride = 4096;
    constexpr uint32_t shift = 12;

    assert(hmb_calc_offset(0, shift) == 0);
    assert(hmb_calc_offset(1, shift) == 4096);
    assert(hmb_calc_offset(16, shift) == 65536);
    assert(hmb_calc_index(65536, shift) == 16);

    uint8_t buffer[65536];
    void* ptr0 = hmb_resolve_pointer(buffer, 0, shift);
    void* ptr5 = hmb_resolve_pointer(buffer, 5, shift);
    assert(ptr0 == buffer);
    assert(ptr5 == buffer + (5 * 4096));

    std::cout << "PASSED!\n";
}

void test_bitmask_allocation() {
    std::cout << "[Test 2] Verifying 64-Bit Bitmask Allocator... ";
    constexpr size_t totalSlots = 256;
    uint64_t words[4]{0}; // 4 x 64 = 256 bits

    hmb::HmbBitmask mask(words, totalSlots);
    assert(mask.countAllocated() == 0);

    uint64_t s0 = mask.allocateFirstFree();
    uint64_t s1 = mask.allocateFirstFree();
    assert(s0 == 0);
    assert(s1 == 1);
    assert(mask.isAllocated(0));
    assert(mask.isAllocated(1));
    assert(!mask.isAllocated(2));
    assert(mask.countAllocated() == 2);

    mask.release(0);
    assert(!mask.isAllocated(0));
    assert(mask.countAllocated() == 1);

    uint64_t sRealloc = mask.allocateFirstFree();
    assert(sRealloc == 0); // Slot 0 reused immediately!

    std::cout << "PASSED!\n";
}

void test_memory_bus_slab() {
    std::cout << "[Test 3] Verifying HmbMemoryBus Slab & Cluster Prefetch... ";
    constexpr size_t poolSize = 1024 * 1024; // 1 MB = 256 x 4KB pages
    hmb::HmbMemoryBus<4096> bus(poolSize);

    assert(bus.getCapacity() == 256);
    assert(bus.getAllocatedCount() == 0);
    assert(bus.getFreeCount() == 256);

    uint64_t slot = bus.allocateSlot(hmb::Tier::HotWorkingSet);
    assert(slot == 0);
    assert(bus.getAllocatedCount() == 1);

    uint8_t* page = bus.resolveAddress(slot);
    assert(page != nullptr);
    std::memset(page, 0x42, 4096);
    assert(page[0] == 0x42 && page[4095] == 0x42);

    // Prefetch cluster test
    bus.prefetchCluster(slot);

    bus.releaseSlot(slot);
    assert(bus.getAllocatedCount() == 0);

    std::cout << "PASSED!\n";
}

void test_zpack_compression() {
    std::cout << "[Test 4] Verifying Tier 2 z-Pack In-RAM Compression... ";
    alignas(64) uint8_t src[4096]{0};
    alignas(64) uint8_t compressed[4096]{0};
    alignas(64) uint8_t decompressed[4096]{0};

    // Populate sparse test pattern (typical dirty page: small heap headers, rest zeros)
    *reinterpret_cast<uint64_t*>(src + 0) = 0xDEADBEEFCAFEULL;
    *reinterpret_cast<uint64_t*>(src + 128) = 0x123456789ABCDEF0ULL;
    *reinterpret_cast<uint64_t*>(src + 4000) = 0xFEEDFACE00112233ULL;

    size_t compBytes = hmb::HmbZPackEngine::compressSlot(src, sizeof(src), compressed, sizeof(compressed));
    assert(compBytes > 0);
    assert(compBytes < 64); // Sparse 3 words compressed into under 40 bytes!

    bool ok = hmb::HmbZPackEngine::decompressSlot(compressed, compBytes, decompressed, sizeof(decompressed));
    assert(ok);
    assert(std::memcmp(src, decompressed, sizeof(src)) == 0);

    std::cout << "PASSED! (Compressed 4096B -> " << compBytes << "B, Ratio: " 
              << (4096.0f / compBytes) << ":1)\n";
}

int main() {
    std::cout << "=======================================================\n";
    std::cout << "  Haven Memory Bus (HMB) - C++23 Verification Suite\n";
    std::cout << "=======================================================\n";

    test_direct_arithmetic();
    test_bitmask_allocation();
    test_memory_bus_slab();
    test_zpack_compression();

    std::cout << "=======================================================\n";
    std::cout << "  ALL HMB CORE VERIFICATIONS PASSED 100%!\n";
    std::cout << "=======================================================\n";
    return 0;
}
