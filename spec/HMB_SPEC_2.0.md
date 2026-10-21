# Haven Memory Bus (HMB) Standard Specification
## Version 2.0 (64-Bit Sovereign Memory Architecture)

**Status:** Official Standard  
**Author:** Barrer Software & Haven AI Systems Architecture Group  
**Target Environments:** Freestanding Kernels, AI Inference Accelerators, High-Throughput Runtimes  

---

### 1. Abstract
The Haven Memory Bus (HMB) specification defines a deterministic, zero-copy, direct-indexed binary memory protocol designed to bridge asymmetric memory tiers (e.g., CPU DRAM, NVMe Flash, GPU VRAM, CXL fabrics). By replacing dynamic tree-based memory management with fixed-stride arithmetic and 64-bit bit-vector control masks, HMB achieves pure $O(1)$ memory mapping, eliminate cache pollution, and provides native hardware acceleration for clustered DMA transfers.

---

### 2. Design Principles
1. **Zero Indirection**: No pointer chasing, no B-trees, no filesystem extent tables. Every memory location is calculated strictly as a function of its index and fixed stride.
2. **Fixed-Stride Homogeneity**: Memory is allocated in homogeneous slabs with power-of-two strides (e.g., 64 B cacheline, 512 B sector, 4096 B page, 65536 B cluster).
3. **64-Bit Word Alignment**: All headers, records, and control bitmaps are strictly 64-bit aligned, allowing atomic operations (`lock bts`, `lock btr`) and single-cycle bit-scans (`tzcnt`, `popcnt`).
4. **4-Tier Partitioning**: Physical memory is organized into four distinct operational tiers matching real-world access patterns: Hot Working Set, Sequential Dirty Heap, Bit-Packed z-Store, and Immutable Clean Code/Tensors.
5. **Freestanding Portability**: The core specification requires zero OS runtime dependencies, making it directly embeddable into Ring 0 microkernels, bare-metal firmware, or userland high-performance engines.

---

### 3. Mathematical Foundations

#### 3.1 Direct Stride Formula
Let:
* $B$ be the base physical or virtual address of the memory slab ($B \equiv 0 \pmod{64}$).
* $S$ be the fixed stride size in bytes ($S = 2^k, k \ge 6$).
* $i$ be the zero-based slot index ($0 \le i < N$).

The memory location $A(i)$ is given by:
$$A(i) = B + (i \cdot S) = B + (i \ll k)$$

In x86-64 assembly, for $S = 4096$ ($k = 12$):
```assembly
movq  %rdi, %rax       ; rax = index i
shlq  $12, %rax        ; rax = i * 4096
addq  %rsi, %rax       ; rax = Base B + (i * 4096)
```

#### 3.2 Backward PFN / Slot Resolution
Given any arbitrary memory pointer $P$ within the slab range $[B, B + N \cdot S)$:
$$i = \frac{P - B}{S} = (P - B) \gg k$$
This operation executes in a single cycle without division.

---

### 4. Memory Control Plane (Bit Memory System)

Memory allocation state is governed by an array of 64-bit words:
$$W_w = \text{Bitmask}[w], \quad w = \lfloor i / 64 \rfloor$$
The state of slot $i$ is represented by bit $b = i \pmod{64}$ within word $W_w$.

#### 4.1 Lock-Free Allocation (Atomic Search-and-Set)
1. Fetch 64-bit word $W_w$.
2. Check if $W_w \ne \text{0xFFFFFFFFFFFFFFFF}$.
3. Find lowest zero bit using trailing zero count:
   $$b = \text{tzcnt}(\sim W_w)$$
4. Atomically test-and-set bit $b$ using `lock bts`. If successful, slot index $i = (w \cdot 64) + b$ is allocated.

#### 4.2 Lock-Free Deallocation
Atomically clear bit $b$ using `lock btr`.

---

### 5. The 4-Tier Partition Standard

| Tier ID | Tier Name | Typical Stride | DMA / Access Policy |
| :---: | :--- | :---: | :--- |
| **0x00** | **Tier 0: Hot Working Set** | 4 KB / 64 KB | Clustered prefetch bursts. Single fault fetches contiguous cluster of $2^m$ slots. |
| **0x01** | **Tier 1: Dirty Heap** | 4 KB | Sequential streaming flush. Swept in contiguous PFN runs along disk LBA strides. |
| **0x02** | **Tier 2: Bit-Packed z-Store** | Variable | In-memory bit-compressed cache tier. Decompresses in CPU registers in $< 1\,\mu\text{s}$. |
| **0x03** | **Tier 3: Clean Immutable** | 4 KB / 2 MB | Read-only static code/tensors. Never written to swap; reloaded directly from source. |

---

### 6. Wire & Serialization Format

Every persistent HMB file or memory-mapped slab begins with the **Canonical 64-Byte HMB Header**:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Magic: "HAVENMEM"                       |
|                      (0x484156454E4D454D)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Version (0x00020000)   |       Tier / Feature Flags    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Stride Size (Bytes)     |      Stride Shift Exponent (k)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Total Slot Capacity                     |
|                            (uint64_t)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Active Allocated Slots                   |
|                            (uint64_t)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Data Slab Byte Offset                    |
|                            (uint64_t)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Bitmap Control Offset                    |
|                            (uint64_t)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     CRC-64 / Blake3 Checksum                  |
|                            (uint64_t)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
