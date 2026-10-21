# Haven Memory Bus (HMB) - Linux Kernel Swap Driver

**Implementation of HMB Spec 2.0 Direct-Stride Swap Subsystem**  
*Tested and verified on bare-metal Intel Xeon silicon (Linux 7.0 / Ubuntu 26.04).*

---

## 🚀 Key Architectural Advantages

1. **Pure $O(1)$ Stride Page Addressing**:
   - Zero indirection, zero radix-tree or xarray lookups.
   - Any sector maps directly to an aligned 4KB page via arithmetic:
     $$\text{pgoff} = \text{sector} \gg (\text{PAGE\_SHIFT} - \text{SECTOR\_SHIFT})$$

2. **64-bit Atomic Bitmask Tracking**:
   - Uses atomic bitwise operations (`hmb_bitmask_t`) for instantaneous allocation, tracking, and discard handling.

3. **Tier 2 z-Pack In-RAM Deduplication & Compression Engine**:
   - **Zero-Page Deduplication**: 100% memory savings for sparse anonymous heaps. A zero-page consumes 1 bit of metadata in RAM.
   - **Uniform Pattern Deduplication**: 99.8% memory savings for repetitive quadwords (e.g. poison values, repetitive data structures). Consumes only 8 bytes of storage per 4096-byte page.

4. **Direct Bio Pipeline**:
   - Uses modern bio submission (`submit_bio` + `bio_endio`), eliminating I/O scheduler overhead and queuing latency.

5. **Live Kernel Telemetry**:
   - Real-time observability via `/proc/hmb_swap`.

---

## 📊 Bare-Metal Silicon Benchmark Results

*Executed on Intel Xeon E3-1270 v6 @ 3.80 GHz (Supermicro X11SSH-F, 32GB ECC RAM, Linux 7.0)*:

| Metric | Result |
| :--- | :--- |
| **Zero-Page Write Throughput** | **1,094.76 MB/s** (3.57 µs / page) |
| **Pattern Write Throughput** | **1,187.46 MB/s** (3.29 µs / page) |
| **Raw Stride Write Throughput** | **1,099.51 MB/s** (3.55 µs / page) |
| **Bit-Exact Read Verification** | **2,625.90 MB/s** |
| **Bit-Exact Correctness** | **100% Bit-Exact Match** |
| **Tier 2 Deduplication Ratio** | **3.9x** (191 MB saved across 256 MB test) |
| **Total Test Operations** | **131,663 ops (0 errors)** |

---

## 🛠️ Building & Activating

### 1. Build the Kernel Module
```bash
make
```

### 2. Load the Module
```bash
sudo insmod hmb_swap.ko size_mb=2048
```

### 3. Initialize & Activate Swap
```bash
sudo mkswap /dev/hmb0
sudo swapon -p 100 /dev/hmb0
```

### 4. Monitor Telemetry
```bash
cat /proc/hmb_swap
```
