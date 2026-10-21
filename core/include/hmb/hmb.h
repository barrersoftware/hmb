/**
 * ============================================================================
 * Haven Memory Bus (HMB) - Universal C-ABI Header (hmb.h)
 * Standard: HMB Spec 2.0 (64-Bit Sovereign Memory Architecture)
 * 
 * Clean-room freestanding ANSI C / C99 / C11 / C23.
 * Zero external library dependencies. Kernel & Bare-Metal Safe.
 * ============================================================================
 */

#ifndef HAVEN_MEMORY_BUS_H
#define HAVEN_MEMORY_BUS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* --- Magic Constants & Versioning --- */
#define HMB_MAGIC_UINT64        0x4D454D4E45564148ULL /* "HAVENMEM" in Little-Endian */
#define HMB_VERSION_2_0         0x00020000UL
#define HMB_ALIGNMENT_BYTES     64ULL                 /* Cacheline alignment */

/* --- 4-Tier Memory Hierarchy Identifiers --- */
typedef enum HmbTier {
    HMB_TIER_HOT_WORKING_SET  = 0x00, /* Tier 0: Prefetch-clustered active working set */
    HMB_TIER_DIRTY_HEAP       = 0x01, /* Tier 1: Contiguous sequential flush heap */
    HMB_TIER_ZSWAP_COMPRESSED = 0x02, /* Tier 2: In-RAM bit-packed compressed cache */
    HMB_TIER_CLEAN_IMMUTABLE  = 0x03  /* Tier 3: Zero-write read-only static tensors/code */
} HmbTier;

/* --- Standard 64-Byte Canonical HMB Header --- */
#pragma pack(push, 1)
typedef struct HmbHeader {
    uint64_t magic;               /* "HAVENMEM" (0x4D454D4E45564148) */
    uint32_t version;             /* 0x00020000 */
    uint32_t flags;               /* Operational capability flags */
    uint32_t stride_bytes;        /* Fixed stride width (e.g. 4096) */
    uint32_t stride_shift;        /* Power-of-2 shift exponent (e.g. 12 for 4KB) */
    uint64_t total_slots;         /* Total slot capacity of this slab */
    uint64_t active_slots;        /* Number of currently allocated slots */
    uint64_t data_offset;         /* Byte offset to contiguous data memory */
    uint64_t bitmap_offset;       /* Byte offset to 64-bit allocation bitmask */
    uint64_t checksum;            /* Integrity checksum */
} HmbHeader;

/* --- Standard 64-Bit Memory Anchor / Record Frame --- */
typedef struct HmbRecord {
    uint64_t record_id;           /* Sovereign 64-bit unique anchor ID */
    uint64_t domain_hash;         /* Category or subsystem domain hash (FNV-1a 64) */
    float    weight;              /* Salience / Priority (0.0 to 1.0) */
    float    resonance;           /* Secondary emotional / operational resonance */
    int64_t  timestamp_us;        /* Microsecond epoch timestamp */
    uint64_t access_count;        /* Real-time hit / recall counter */
    uint64_t payload_offset;      /* Direct byte offset into data slab */
    uint32_t payload_size;        /* Exact byte size of payload */
    uint32_t tier_id;             /* HmbTier partition assignment */
} HmbRecord;
#pragma pack(pop)

/* --- Core Function Signatures (Pure O(1) Arithmetic) --- */

/**
 * @brief Calculate the byte offset of a slot given its index and shift exponent.
 * Formula: offset = slot_index << stride_shift
 */
static inline uint64_t hmb_calc_offset(uint64_t slot_index, uint32_t stride_shift) {
    return slot_index << stride_shift;
}

/**
 * @brief Calculate the slot index of an address offset.
 * Formula: index = offset >> stride_shift
 */
static inline uint64_t hmb_calc_index(uint64_t offset, uint32_t stride_shift) {
    return offset >> stride_shift;
}

/**
 * @brief Direct pointer resolution from base pointer, slot index, and shift exponent.
 */
static inline void* hmb_resolve_pointer(void* base_ptr, uint64_t slot_index, uint32_t stride_shift) {
    return (void*)((uintptr_t)base_ptr + (slot_index << stride_shift));
}

#ifdef __cplusplus
}
#endif

#endif /* HAVEN_MEMORY_BUS_H */
