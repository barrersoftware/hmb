"""
Haven Memory Bus (HMB) - Python Test & Verification Suite
"""

import sys
import os

# Add bindings/python to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bindings", "python")))

from pyhmb import HmbMemoryBus, HmbTier, HmbHeader

def test_pyhmb():
    print("=======================================================")
    print("  Haven Memory Bus (HMB) - Python Verification Suite")
    print("=======================================================")

    bus = HmbMemoryBus(total_bytes=1024 * 1024, stride_bytes=4096)
    print(f"[pyhmb] Bus Initialized: {bus.total_bytes // 1024} KB, Capacity: {bus.capacity} slots")

    slot0 = bus.allocate_slot(HmbTier.HOT_WORKING_SET)
    slot1 = bus.allocate_slot(HmbTier.HOT_WORKING_SET)
    assert slot0 == 0
    assert slot1 == 1
    print(f"[pyhmb] Allocated Slot 0: {slot0}, Slot 1: {slot1}")

    # Zero-copy memoryview write
    view0 = bus.resolve_view(slot0)
    view0[0:4] = b"HMB!"
    view0[4092:4096] = b"SOV1"
    assert bytes(view0[0:4]) == b"HMB!"
    assert bytes(view0[4092:4096]) == b"SOV1"
    print(f"[pyhmb] Zero-copy memoryview verified: Head={bytes(view0[0:4])}, Tail={bytes(view0[4092:4096])}")

    bus.release_slot(slot0)
    assert bus.allocated_count == 1
    print(f"[pyhmb] Released Slot 0. Allocated: {bus.allocated_count}, Free: {bus.free_count}")

    # Header serialization test
    hdr = HmbHeader(stride_bytes=4096, total_slots=bus.capacity)
    packed = hdr.pack()
    assert len(packed) == 64
    assert packed[0:8] == b"HAVENMEM"[::-1] or packed[0:8] == struct_test_magic()
    print("[pyhmb] Canonical 64-byte Header packed OK.")

    print("=======================================================")
    print("  ALL PYTHON HMB VERIFICATIONS PASSED 100%!")
    print("=======================================================")

def struct_test_magic():
    import struct
    return struct.pack("<Q", HmbHeader.MAGIC)

if __name__ == "__main__":
    test_pyhmb()
