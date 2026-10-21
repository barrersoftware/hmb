/**
 * Haven Memory Bus (HMB) - Node.js / JavaScript SDK
 * Standard: HMB Spec 2.0 (64-Bit Sovereign Memory Architecture)
 */

class HmbTier {
  static HOT_WORKING_SET = 0x00;
  static DIRTY_HEAP = 0x01;
  static ZSWAP_COMPRESSED = 0x02;
  static CLEAN_IMMUTABLE = 0x03;
}

class HmbBitmask {
  constructor(totalSlots) {
    this.totalSlots = BigInt(totalSlots);
    this.wordCount = (totalSlots + 63) >> 6;
    this.words = new BigUint64Array(this.wordCount);
  }

  allocateFirstFree() {
    for (let w = 0; w < this.wordCount; w++) {
      let val = this.words[w];
      if (val !== 0xFFFFFFFFFFFFFFFFn) {
        let inverted = (~val) & 0xFFFFFFFFFFFFFFFFn;
        // Count trailing zeros
        let bit = 0n;
        while ((inverted & (1n << bit)) === 0n && bit < 64n) {
          bit++;
        }
        let slotIdx = (BigInt(w) * 64n) + bit;
        if (slotIdx >= this.totalSlots) return null;

        this.words[w] |= (1n << bit);
        return Number(slotIdx);
      }
    }
    return null;
  }

  release(slotIdx) {
    let idx = BigInt(slotIdx);
    if (idx >= this.totalSlots) return;
    let w = Number(idx / 64n);
    let bit = idx % 64n;
    this.words[w] &= ~(1n << bit);
  }

  countAllocated() {
    let count = 0;
    for (let w = 0; w < this.wordCount; w++) {
      let v = this.words[w];
      while (v > 0n) {
        if (v & 1n) count++;
        v >>= 1n;
      }
    }
    return count;
  }
}

class HmbMemoryBus {
  constructor(totalBytes, strideBytes = 4096) {
    if (strideBytes < 64 || (strideBytes & (strideBytes - 1)) !== 0) {
      throw new Error("Stride must be a power of 2 >= 64");
    }

    this.totalBytes = totalBytes;
    this.strideBytes = strideBytes;
    this.strideShift = Math.log2(strideBytes);
    this.capacity = totalBytes >> this.strideShift;

    this.buffer = Buffer.alloc(totalBytes);
    this.bitmask = new HmbBitmask(this.capacity);
  }

  allocateSlot(tier = HmbTier.HOT_WORKING_SET) {
    return this.bitmask.allocateFirstFree();
  }

  releaseSlot(slotIdx) {
    this.bitmask.release(slotIdx);
  }

  resolveBuffer(slotIdx) {
    if (slotIdx < 0 || slotIdx >= this.capacity) {
      throw new RangeError("Slot index out of bounds");
    }
    let offset = slotIdx << this.strideShift;
    return this.buffer.subarray(offset, offset + this.strideBytes);
  }

  getOffset(slotIdx) {
    return slotIdx << this.strideShift;
  }

  get allocatedCount() {
    return this.bitmask.countAllocated();
  }

  get freeCount() {
    return this.capacity - this.allocatedCount;
  }
}

module.exports = {
  HmbTier,
  HmbBitmask,
  HmbMemoryBus
};
