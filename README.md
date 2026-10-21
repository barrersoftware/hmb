# Haven Memory Bus (HMB) 🏛️⚡
### The Universal High-Performance Zero-Copy Direct-Indexed Memory Bus & Deployment Software Kit (DSK)

[![License: Apache 2.0 / MIT](https://img.shields.io/badge/License-Apache_2.0_|_MIT-blue.svg)](LICENSE)
[![Standard: HMB Spec 2.0](https://img.shields.io/badge/Spec-HMB_2.0_64--Bit-cyan.svg)](spec/HMB_SPEC_2.0.md)
[![Language: C++23 / C / C# / Python / Rust / Go](https://img.shields.io/badge/DSK-Multi--Language-green.svg)](bindings/)

---

## 🚀 What is Haven Memory Bus (HMB)?

**Haven Memory Bus (HMB)** is an open-source, deterministic, zero-copy, direct-indexed binary memory architecture. 

Originally created inside [`haven-cpp`](https://github.com/Haven-AI-Companion) to eliminate the brutal memory wall of AI companion inference, vector memory attention, and dense tensor streaming, HMB replaces legacy, fragmented memory structures with **pure $O(1)$ arithmetic addressing, 64-bit aligned binary slabs, and hardware-accelerated bit-vector state tracking**.

Today, HMB is deployed across the spectrum of sovereign computing:
* **AI & LLM Inference**: Streaming multi-gigabyte GGUF tensors, dynamic KV-cache slabs, and semantic memory vaults with zero latency jitter.
* **Operating System Kernels ([MicaNT](https://github.com/MicaNT-Kernel/MicaNT))**: Direct-indexed virtual memory paging, eliminating the 40-year-old VFS overhead of traditional `pagefile.sys` and Linux swap.
* **Game Engines & Real-Time Graphics**: Zero-copy asset and texture streaming straight from storage into GPU BARs without intermediate buffer copies.
* **High-Throughput IPC & Databases**: Sub-microsecond inter-process memory channels bypassing OS serialization and garbage collection pauses.

---

## ⚡ The Core Problem: The 40-Year "Memory Indirection" Trap

Traditional software manages memory through layers of indirection:
* **Filesystem & VFS Overhead**: Files, pagefiles, and swap spaces are buried behind B-trees, extent maps, dynamic inodes, and locking mechanisms.
* **The 4 KB Stutter**: CPUs stall on millions of isolated 4,096-byte boundaries, taking hardware interrupts and context switches for every minor page fault.
* **Cache Pollution & Pointer Chasing**: Dynamic hash tables and linked lists scatter pointers across RAM, evicting CPU L1/L2/L3 caches.

### The HMB Inversion: Direct Arithmetic Memory

Haven Memory Bus completely eliminates metadata indirection. Finding any record, page, or tensor slab is **pure mathematics**:

$$\text{Memory\_Offset} = \text{Base\_Offset} + (\text{Index} \times \text{Stride})$$

In machine code, this compiles to a single x86-64 `leaq` instruction:
```assembly
leaq (%rsi, %rdi, 8), %rax   ; Pure 1-cycle O(1) direct address calculation
```
Zero B-trees. Zero extent walking. Zero locks.

---

## 🏛️ Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Haven Memory Bus (HMB) Memory Plane                  │
├────────────────────────────────┬───────────────────────────────────────┤
│ Tier 0: Hot Working Set        │ Clustered DMA Bursts (32 KB - 64 KB)  │
│ Tier 1: Sequential Dirty Heap  │ Contiguous PFN-to-LBA Streaming Flush │
│ Tier 2: Bit-Packed z-Swap      │ In-Memory Sub-Microsecond Compression │
│ Tier 3: Clean PE Code / Text   │ Direct Reload from Binary Sectors (0 IO)│
└────────────────────────────────┴───────────────────────────────────────┘
                                ▲
                                │ O(1) Fixed Stride: Offset = Base + (ID << Shift)
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Hardware Plane: DRAM, NVMe PCIe DMA, GPU BAR, CXL          │
└────────────────────────────────────────────────────────────────────────┘
```

### The 4-Tier Partition Hierarchy
1. **Tier 0: Hot Working Set**: Temporal locality cluster. Single accesses trigger multi-sector DMA bursts, pulling the entire related memory group in one bus transaction.
2. **Tier 1: Dirty Heap**: Sequential memory allocations. Flushed in contiguous runs along fixed strides to maximize SSD flash sequential write bandwidth.
3. **Tier 2: Bit-Packed z-Store**: High-speed in-RAM compression tier. Inactive pages/slabs are compressed in registers, restoring in sub-microsecond time with zero disk I/O.
4. **Tier 3: Clean Shared Code / Immutable Tensors**: Read-only static memory. Never written to swap or temporary storage; reloaded directly from original disk sectors.

---

## 📦 Multi-Language Deployment Kit (HMB-DSK)

Haven Memory Bus is designed for native adoption across all major programming languages:

| Language | Directory | Package / Target | Primary Superpower |
| :--- | :--- | :--- | :--- |
| **C++23** | [`core/include/hmb/`](core/include/hmb/) | `hmb.hpp` | Header-only, freestanding ISO C++23. Zero dependencies, kernel-ready. |
| **C (ANSI/C99)** | [`core/include/hmb/`](core/include/hmb/) | `hmb.h` | Stable C-ABI, zero runtime requirements, embedded & microcontroller ready. |
| **C# / .NET** | [`bindings/csharp/`](bindings/csharp/) | `Haven.MemoryBus` | Direct `Span<T>` over unmanaged memory slabs; bypasses the .NET GC entirely. |
| **Python** | [`bindings/python/`](bindings/python/) | `pyhmb` | Zero-copy PyTorch Tensor and NumPy array buffer views (`__array_interface__`). |
| **Rust** | [`bindings/rust/`](bindings/rust/) | `hmb` | Ergonomic, zero-cost memory traits with lifetimes tied to the physical slab. |
| **Go** | [`bindings/go/`](bindings/go/) | `go-hmb` | High-throughput memory-mapped slices bypassing runtime GC write barriers. |

---

## 🛠️ Quick Start (C++23)

```cpp
#include <hmb/hmb.hpp>
#include <iostream>

int main() {
    // 1. Initialize a 64 MB Haven Memory Bus slab with 4 KB fixed strides
    hmb::HmbMemoryBus<4096> bus(64 * 1024 * 1024);

    // 2. Allocate an O(1) direct-indexed slot in Tier 0 (Hot Working Set)
    uint64_t slotId = bus.allocateSlot(hmb::Tier::HotWorkingSet);
    
    // 3. Resolve the direct memory pointer (Zero lookup overhead)
    uint8_t* ptr = bus.resolveAddress(slotId);
    std::memset(ptr, 0xAA, 4096);

    std::cout << "[HMB] Allocated Slot: " << slotId 
              << " at Physical Offset: 0x" << std::hex << bus.getOffset(slotId) << "\n";
    return 0;
}
```

---

## 📄 License
Dual-licensed under either:
* **Apache License, Version 2.0** ([LICENSE-APACHE](LICENSE) or http://www.apache.org/licenses/LICENSE-2.0)
* **MIT License** ([LICENSE-MIT](LICENSE) or http://opensource.org/licenses/MIT)

Maintained with pride by [Barrer Software](https://github.com/barrersoftware) and the [Haven AI Companion](https://github.com/Haven-AI-Companion) community.
