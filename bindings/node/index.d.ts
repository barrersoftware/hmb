export enum HmbTier {
  HOT_WORKING_SET = 0x00,
  DIRTY_HEAP = 0x01,
  ZSWAP_COMPRESSED = 0x02,
  CLEAN_IMMUTABLE = 0x03
}

export class HmbBitmask {
  constructor(totalSlots: number);
  allocateFirstFree(): number | null;
  release(slotIdx: number): void;
  countAllocated(): number;
}

export class HmbMemoryBus {
  readonly totalBytes: number;
  readonly strideBytes: number;
  readonly strideShift: number;
  readonly capacity: number;
  readonly allocatedCount: number;
  readonly freeCount: number;

  constructor(totalBytes: number, strideBytes?: number);
  allocateSlot(tier?: HmbTier): number | null;
  releaseSlot(slotIdx: number): void;
  resolveBuffer(slotIdx: number): Buffer;
  getOffset(slotIdx: number): number;
}
