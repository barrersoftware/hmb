"""
Haven Memory Bus (HMB) - 64-Bit Bit Memory Vector Engine
"""

from typing import Optional


class HmbBitmask:
    """Manages slot allocation bitmasks using 64-bit machine words."""

    def __init__(self, total_slots: int):
        self.total_slots = total_slots
        self.word_count = (total_slots + 63) // 64
        self.words = [0] * self.word_count

    def allocate_first_free(self) -> Optional[int]:
        """Finds first clear bit, sets it, and returns slot index."""
        for w in range(self.word_count):
            val = self.words[w]
            if val != 0xFFFFFFFFFFFFFFFF:
                inverted = (~val) & 0xFFFFFFFFFFFFFFFF
                # Find trailing zeros
                bit = (inverted & -inverted).bit_length() - 1
                slot_idx = (w * 64) + bit
                if slot_idx >= self.total_slots:
                    return None
                self.words[w] |= (1 << bit)
                return slot_idx
        return None

    def release(self, slot_idx: int) -> None:
        """Clears bit for given slot index."""
        if slot_idx < 0 or slot_idx >= self.total_slots:
            return
        w = slot_idx // 64
        bit = slot_idx % 64
        self.words[w] &= ~(1 << bit)

    def is_allocated(self, slot_idx: int) -> bool:
        if slot_idx < 0 or slot_idx >= self.total_slots:
            return False
        w = slot_idx // 64
        bit = slot_idx % 64
        return bool(self.words[w] & (1 << bit))

    def count_allocated(self) -> int:
        return sum(bin(w).count("1") for w in self.words)
