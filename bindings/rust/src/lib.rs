//! # Haven Memory Bus (HMB) - Rust SDK
//! Standard: HMB Spec 2.0 (64-Bit Sovereign Memory Architecture)

use std::sync::atomic::{AtomicU64, Ordering};

pub const MAGIC: u64 = 0x4D454D4E45564148;
pub const VERSION_20: u32 = 0x00020000;

#[repr(u32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HmbTier {
    HotWorkingSet = 0x00,
    DirtyHeap = 0x01,
    ZSwapCompressed = 0x02,
    CleanImmutable = 0x03,
}

pub struct HmbBitmask {
    words: Vec<AtomicU64>,
    total_slots: u64,
    word_count: usize,
}

impl HmbBitmask {
    pub fn new(total_slots: u64) -> Self {
        let word_count = ((total_slots + 63) / 64) as usize;
        let mut words = Vec::with_capacity(word_count);
        for _ in 0..word_count {
            words.push(AtomicU64::new(0));
        }
        Self {
            words,
            total_slots,
            word_count,
        }
    }

    pub fn allocate_first_free(&self) -> Option<u64> {
        for (w, word) in self.words.iter().enumerate() {
            let mut current = word.load(Ordering::Relaxed);
            while current != u64::MAX {
                let inverted = !current;
                let bit = inverted.trailing_zeros() as u64;
                let slot_idx = (w as u64 * 64) + bit;
                if slot_idx >= self.total_slots {
                    return None;
                }

                let updated = current | (1 << bit);
                match word.compare_exchange_weak(current, updated, Ordering::Acquire, Ordering::Relaxed) {
                    Ok(_) => return Some(slot_idx),
                    Err(actual) => current = actual,
                }
            }
        }
        None
    }

    pub fn release(&self, slot_idx: u64) {
        if slot_idx >= self.total_slots {
            return;
        }
        let w = (slot_idx / 64) as usize;
        let bit = slot_idx % 64;
        let mask = !(1 << bit);
        self.words[w].fetch_and(mask, Ordering::Release);
    }

    pub fn count_allocated(&self) -> u64 {
        self.words.iter().map(|w| w.load(Ordering::Relaxed).count_ones() as u64).sum()
    }
}

pub struct HmbMemoryBus {
    buffer: Vec<u8>,
    stride_bytes: usize,
    stride_shift: u32,
    capacity: u64,
    bitmask: HmbBitmask,
}

impl HmbMemoryBus {
    pub fn new(total_bytes: usize, stride_bytes: usize) -> Result<Self, &'static str> {
        if stride_bytes < 64 || !stride_bytes.is_power_of_two() {
            return Err("Stride must be a power of 2 >= 64");
        }

        let stride_shift = stride_bytes.trailing_zeros();
        let capacity = (total_bytes >> stride_shift) as u64;

        Ok(Self {
            buffer: vec![0u8; total_bytes],
            stride_bytes,
            stride_shift,
            capacity,
            bitmask: HmbBitmask::new(capacity),
        })
    }

    #[inline]
    pub fn allocate_slot(&self, _tier: HmbTier) -> Option<u64> {
        self.bitmask.allocate_first_free()
    }

    #[inline]
    pub fn release_slot(&self, slot_idx: u64) {
        self.bitmask.release(slot_idx);
    }

    #[inline]
    pub fn resolve_slice(&mut self, slot_idx: u64) -> Option<&mut [u8]> {
        if slot_idx >= self.capacity {
            return None;
        }
        let offset = (slot_idx as usize) << self.stride_shift;
        Some(&mut self.buffer[offset..offset + self.stride_bytes])
    }

    #[inline]
    pub fn get_offset(&self, slot_idx: u64) -> u64 {
        slot_idx << self.stride_shift
    }

    pub fn capacity(&self) -> u64 {
        self.capacity
    }

    pub fn allocated_count(&self) -> u64 {
        self.bitmask.count_allocated()
    }
}
