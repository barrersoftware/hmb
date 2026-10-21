/**
 * ============================================================================
 * Haven Memory Bus (HMB) - C Reference Implementation (hmb_core.c)
 * Standard: HMB Spec 2.0
 * ============================================================================
 */

#include "hmb/hmb.h"
#include <string.h>

/**
 * @brief Initialize a canonical 64-byte HMB header.
 */
void hmb_init_header(
    HmbHeader* hdr,
    uint32_t stride_bytes,
    uint64_t total_slots,
    uint64_t data_offset,
    uint64_t bitmap_offset
) {
    if (!hdr) return;
    memset(hdr, 0, sizeof(HmbHeader));

    hdr->magic = HMB_MAGIC_UINT64;
    hdr->version = HMB_VERSION_2_0;
    hdr->flags = 0;
    hdr->stride_bytes = stride_bytes;

    /* Compute shift exponent */
    uint32_t shift = 0;
    uint32_t temp = stride_bytes;
    while (temp > 1) {
        temp >>= 1;
        shift++;
    }
    hdr->stride_shift = shift;
    hdr->total_slots = total_slots;
    hdr->active_slots = 0;
    hdr->data_offset = data_offset;
    hdr->bitmap_offset = bitmap_offset;
    hdr->checksum = 0;
}

/**
 * @brief Verify header validity.
 */
bool hmb_verify_header(const HmbHeader* hdr) {
    if (!hdr) return false;
    if (hdr->magic != HMB_MAGIC_UINT64) return false;
    if (hdr->version != HMB_VERSION_2_0) return false;
    if (hdr->stride_bytes == 0 || (hdr->stride_bytes & (hdr->stride_bytes - 1)) != 0) return false;
    return true;
}
