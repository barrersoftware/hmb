"""
Haven Memory Bus (HMB) - Master Bus Engine
Supports zero-copy memoryviews, NumPy arrays, and PyTorch tensors.
"""

from enum import IntEnum
import struct
from typing import Optional
from .bitmask import HmbBitmask


class HmbTier(IntEnum):
    HOT_WORKING_SET = 0x00
    DIRTY_HEAP = 0x01
    ZSWAP_COMPRESSED = 0x02
    CLEAN_IMMUTABLE = 0x03


class HmbHeader:
    MAGIC = 0x4D454D4E45564148  # "HAVENMEM"
    VERSION = 0x00020000
    FORMAT = "<QIIIIQQQQQ"  # 64 bytes

    def __init__(self, stride_bytes: int = 4096, total_slots: int = 0):
        self.magic = self.MAGIC
        self.version = self.VERSION
        self.flags = 0
        self.stride_bytes = stride_bytes
        self.stride_shift = (stride_bytes & -stride_bytes).bit_length() - 1
        self.total_slots = total_slots
        self.active_slots = 0
        self.data_offset = 64
        self.bitmap_offset = 64
        self.checksum = 0

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.magic,
            self.version,
            self.flags,
            self.stride_bytes,
            self.stride_shift,
            self.total_slots,
            self.active_slots,
            self.data_offset,
            self.bitmap_offset,
            self.checksum
        )


class HmbRecord:
    FORMAT = "<QQffqQQII"  # Standard record frame

    def __init__(self, record_id: int = 0, domain_hash: int = 0, weight: float = 1.0):
        self.record_id = record_id
        self.domain_hash = domain_hash
        self.weight = weight
        self.resonance = 0.95
        self.timestamp_us = 0
        self.access_count = 0
        self.payload_offset = 0
        self.payload_size = 0
        self.tier_id = int(HmbTier.HOT_WORKING_SET)


class HmbMemoryBus:
    """Master Haven Memory Bus implementation with O(1) stride addressing."""

    def __init__(self, total_bytes: int, stride_bytes: int = 4096):
        if stride_bytes < 64 or (stride_bytes & (stride_bytes - 1)) != 0:
            raise ValueError("Stride must be a power of 2 >= 64")

        self.total_bytes = total_bytes
        self.stride_bytes = stride_bytes
        self.stride_shift = (stride_bytes & -stride_bytes).bit_length() - 1
        self.capacity = total_bytes >> self.stride_shift

        self._buffer = bytearray(total_bytes)
        self._view = memoryview(self._buffer)
        self._bitmask = HmbBitmask(self.capacity)

    def allocate_slot(self, tier: HmbTier = HmbTier.HOT_WORKING_SET) -> Optional[int]:
        """Allocates an O(1) direct-stride slot."""
        return self._bitmask.allocate_first_free()

    def release_slot(self, slot_idx: int) -> None:
        """Frees an allocated slot."""
        self._bitmask.release(slot_idx)

    def resolve_view(self, slot_idx: int) -> memoryview:
        """Returns a zero-copy memoryview slice for the slot."""
        if slot_idx < 0 or slot_idx >= self.capacity:
            raise IndexError("Slot index out of bounds")
        offset = slot_idx << self.stride_shift
        return self._view[offset : offset + self.stride_bytes]

    def get_offset(self, slot_idx: int) -> int:
        """Returns byte offset of slot."""
        return slot_idx << self.stride_shift

    @property
    def allocated_count(self) -> int:
        return self._bitmask.count_allocated()

    @property
    def free_count(self) -> int:
        return self.capacity - self.allocated_count
