# Haven Memory Bus (HMB) - Native In-Tree Linux Kernel Patch

**Architecture: In-Tree Virtual Memory Manager (VMM) Direct Paging Engine**  
*Target: Linux Kernel 7.0.x / 7.x series*

---

## ⚡ Overview

This patch directly embeds **Haven Memory Bus (HMB) Spec 2.0** into the core Linux Virtual Memory Manager (`mm/`):
- Completely bypasses `struct bio` allocation, `blk-mq` request queues, and device I/O schedulers.
- Page eviction (`__swap_writepage`) evaluates folios directly with HMB Tier 2 z-Pack inline deduplication:
  - **Zero-pages**: Stored as 1 bit in an atomic 64-bit word (`$100\%$ RAM savings, 0 byte payload`).
  - **Quadword patterns**: Stored in 8 bytes (`$99.8\%$ RAM savings`).
  - **Incompressible memory**: Placed into fixed-stride 64-bit aligned memory slabs at pure $O(1)$ arithmetic.
- Fault resolution (`do_swap_page` -> `swap_read_folio`):
  - Solves page faults in nanoseconds directly in the fault handler without thread blocking or disk waits.
- Slot invalidation (`swap_entry_free`):
  - Atomically clears bitmasks with zero lock contention across CPU cores.

---

## 🛠️ Applying the Patch

### 1. Apply Unified Diff to Kernel Source Tree
```bash
cd /usr/src/linux-7.0.0
patch -p1 < hmb_in_tree_linux_7.0.patch
```

### 2. Enable in Kernel Configuration
```bash
# Enable in .config:
CONFIG_HMB_PAGEFILE=y

# Or via menuconfig:
# Memory Management options --->
#   [*] Haven Memory Bus (HMB) Native In-Tree Paging Engine
make olddefconfig
```

### 3. Compile the Kernel
```bash
make -j$(nproc) bzImage modules
sudo make modules_install
sudo make install
```

---

## 📊 Live Observability

The in-tree engine exposes direct kernel VMM paging telemetry via:
```bash
cat /proc/hmb_pagefile
```
