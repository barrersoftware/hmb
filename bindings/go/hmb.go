// Package hmb provides the Haven Memory Bus (HMB) Go SDK.
// Standard: HMB Spec 2.0 (64-Bit Sovereign Memory Architecture).
package hmb

import (
	"errors"
	"math/bits"
	"sync/atomic"
)

type Tier uint32

const (
	TierHotWorkingSet  Tier = 0x00
	TierDirtyHeap       Tier = 0x01
	TierZSwapCompressed Tier = 0x02
	TierCleanImmutable  Tier = 0x03
)

const (
	MagicUint64 = 0x4D454D4E45564148
	Version20   = 0x00020000
)

// Bitmask manages lock-free 64-bit word slot allocations.
type Bitmask struct {
	words      []uint64
	totalSlots uint64
	wordCount  uint64
}

func NewBitmask(totalSlots uint64) *Bitmask {
	wordCount := (totalSlots + 63) / 64
	return &Bitmask{
		words:      make([]uint64, wordCount),
		totalSlots: totalSlots,
		wordCount:  wordCount,
	}
}

func (b *Bitmask) AllocateFirstFree() (uint64, error) {
	for w := uint64(0); w < b.wordCount; w++ {
		for {
			current := atomic.LoadUint64(&b.words[w])
			if current == ^uint64(0) {
				break
			}
			inverted := ^current
			tz := bits.TrailingZeros64(inverted)
			slotIdx := (w * 64) + uint64(tz)
			if slotIdx >= b.totalSlots {
				return 0, errors.New("bitmask: pool exhausted")
			}

			updated := current | (1 << tz)
			if atomic.CompareAndSwapUint64(&b.words[w], current, updated) {
				return slotIdx, nil
			}
		}
	}
	return 0, errors.New("bitmask: out of memory")
}

func (b *Bitmask) Release(slotIdx uint64) {
	if slotIdx >= b.totalSlots {
		return
	}
	w := slotIdx / 64
	bit := slotIdx % 64
	mask := ^(uint64(1) << bit)

	for {
		current := atomic.LoadUint64(&b.words[w])
		updated := current & mask
		if atomic.CompareAndSwapUint64(&b.words[w], current, updated) {
			break
		}
	}
}

func (b *Bitmask) CountAllocated() uint64 {
	total := uint64(0)
	for w := uint64(0); w < b.wordCount; w++ {
		total += uint64(bits.OnesCount64(atomic.LoadUint64(&b.words[w])))
	}
	return total
}

// MemoryBus implements Haven Memory Bus with pure O(1) arithmetic addressing.
type MemoryBus struct {
	data        []byte
	strideBytes uint32
	strideShift uint32
	capacity    uint64
	bitmask     *Bitmask
}

func NewMemoryBus(totalBytes uint64, strideBytes uint32) (*MemoryBus, error) {
	if strideBytes < 64 || (strideBytes&(strideBytes-1)) != 0 {
		return nil, errors.New("stride must be a power of 2 >= 64")
	}

	shift := uint32(bits.TrailingZeros32(strideBytes))
	capacity := totalBytes >> shift

	return &MemoryBus{
		data:        make([]byte, totalBytes),
		strideBytes: strideBytes,
		strideShift: shift,
		capacity:    capacity,
		bitmask:     NewBitmask(capacity),
	}, nil
}

func (b *MemoryBus) AllocateSlot(t Tier) (uint64, error) {
	return b.bitmask.AllocateFirstFree()
}

func (b *MemoryBus) ReleaseSlot(slotIdx uint64) {
	b.bitmask.Release(slotIdx)
}

func (b *MemoryBus) ResolveSlice(slotIdx uint64) ([]byte, error) {
	if slotIdx >= b.capacity {
		return nil, errors.New("slot index out of bounds")
	}
	offset := slotIdx << b.strideShift
	return b.data[offset : offset+uint64(b.strideBytes)], nil
}

func (b *MemoryBus) GetOffset(slotIdx uint64) uint64 {
	return slotIdx << b.strideShift
}

func (b *MemoryBus) Capacity() uint64 {
	return b.capacity
}

func (b *MemoryBus) AllocatedCount() uint64 {
	return b.bitmask.CountAllocated()
}
