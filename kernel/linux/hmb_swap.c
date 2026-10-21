// SPDX-License-Identifier: GPL-2.0
/*
 * Haven Memory Bus (HMB) - Linux Swap Block Driver
 * Implementation of HMB Spec 2.0 Direct-Stride Swap Subsystem
 *
 * Copyright (C) 2026 Daniel Elliott / Barrer Software Org.
 *
 * Key Architecture:
 * - O(1) Stride-Based Page Indexing: zero indirection, zero radix lookup.
 * - Lock-Free 64-bit Atomic Bitmasks for Slot Allocation & Deduplication.
 * - Tier 2 z-Pack In-RAM Compression Engine:
 *     * Instant Zero-Page Deduplication (100% RAM savings for anonymous heaps).
 *     * 64-bit Uniform Pattern Deduplication (99.8% RAM savings).
 * - Modern Bio Submission with Direct bio_endio() Completion.
 * - Live Kernel Telemetry via /proc/hmb_swap.
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/major.h>
#include <linux/blkdev.h>
#include <linux/bio.h>
#include <linux/highmem.h>
#include <linux/mutex.h>
#include <linux/pagemap.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/version.h>

#define DRV_NAME "hmb_swap"
#define HMB_DEFAULT_SIZE_MB 2048

static int size_mb = HMB_DEFAULT_SIZE_MB;
module_param(size_mb, int, 0444);
MODULE_PARM_DESC(size_mb, "Size of HMB Swap block device in Megabytes (default: 2048)");

static bool zpack_enable = true;
module_param(zpack_enable, bool, 0644);
MODULE_PARM_DESC(zpack_enable, "Enable Tier 2 z-Pack zero/pattern deduplication (default: Y)");

struct hmb_stats {
	atomic64_t reads;
	atomic64_t writes;
	atomic64_t discards;
	atomic64_t zpack_zero_hits;
	atomic64_t zpack_pattern_hits;
	atomic64_t raw_pages;
	atomic64_t bytes_saved;
};

struct hmb_device {
	int major;
	struct gendisk *disk;
	sector_t capacity_sectors;
	unsigned long total_pages;

	/* Atomic Bitmasks (HMB 64-bit Bitmask Engine) */
	unsigned long *allocated_bitmap;
	unsigned long *zero_bitmap;
	unsigned long *pattern_bitmap;

	/* Tier 2 Pattern Storage */
	u64 *patterns;

	/* Backing Raw Pages (Tier 1 uncompressed fallback) */
	struct page **raw_pages;
	spinlock_t lock;

	struct hmb_stats stats;
};

static struct hmb_device *g_hmb_dev;
static struct proc_dir_entry *g_proc_entry;

/*
 * Check if a 4KB memory buffer is 100% uniform 64-bit repeating value.
 * Returns true if uniform, storing the 64-bit value in *out_val.
 */
static inline bool hmb_is_uniform_quadword(const void *kaddr, u64 *out_val)
{
	const u64 *words = (const u64 *)kaddr;
	u64 first = words[0];
	int i;

	for (i = 1; i < (PAGE_SIZE / sizeof(u64)); i++) {
		if (words[i] != first)
			return false;
	}
	*out_val = first;
	return true;
}

/*
 * Process Discard (REQ_OP_DISCARD): Free memory immediately
 */
static void hmb_do_discard(struct hmb_device *hmb, sector_t sector, unsigned int len)
{
	unsigned long pgoff = sector >> PAGE_SECTORS_SHIFT;
	unsigned long nr_pages = len >> PAGE_SHIFT;
	unsigned long i;
	struct page *p = NULL;

	for (i = 0; i < nr_pages && (pgoff + i) < hmb->total_pages; i++) {
		unsigned long idx = pgoff + i;

		clear_bit(idx, hmb->zero_bitmap);
		clear_bit(idx, hmb->pattern_bitmap);

		if (test_and_clear_bit(idx, hmb->allocated_bitmap)) {
			spin_lock(&hmb->lock);
			p = hmb->raw_pages[idx];
			hmb->raw_pages[idx] = NULL;
			spin_unlock(&hmb->lock);

			if (p)
				__free_page(p);
		}
		atomic64_inc(&hmb->stats.discards);
	}
}

/*
 * Read Data: Direct O(1) lookup + Tier 2 z-Pack decompression
 */
static void hmb_read_segment(struct hmb_device *hmb, sector_t sector, void *dst, unsigned int len)
{
	unsigned long pgoff = sector >> PAGE_SECTORS_SHIFT;
	unsigned int offset = (sector & (PAGE_SECTORS - 1)) << 9;
	struct page *p = NULL;

	if (unlikely(pgoff >= hmb->total_pages)) {
		memset(dst, 0, len);
		return;
	}

	/* Tier 2 z-Pack: Zero-Page Hit */
	if (test_bit(pgoff, hmb->zero_bitmap)) {
		memset(dst, 0, len);
		atomic64_inc(&hmb->stats.reads);
		return;
	}

	/* Tier 2 z-Pack: Uniform Pattern Hit */
	if (test_bit(pgoff, hmb->pattern_bitmap)) {
		u64 val = hmb->patterns[pgoff];
		if (offset == 0 && len == PAGE_SIZE) {
			memset64(dst, val, PAGE_SIZE / sizeof(u64));
		} else {
			u8 temp[sizeof(u64)];
			unsigned int copied = 0;
			memcpy(temp, &val, sizeof(u64));
			while (copied < len) {
				unsigned int chunk = min_t(unsigned int, len - copied, sizeof(u64));
				memcpy((u8 *)dst + copied, temp, chunk);
				copied += chunk;
			}
		}
		atomic64_inc(&hmb->stats.reads);
		return;
	}

	/* Tier 1: Raw Page */
	spin_lock(&hmb->lock);
	p = hmb->raw_pages[pgoff];
	if (p)
		get_page(p);
	spin_unlock(&hmb->lock);

	if (p) {
		memcpy_from_page(dst, p, offset, len);
		put_page(p);
	} else {
		memset(dst, 0, len);
	}

	atomic64_inc(&hmb->stats.reads);
}

/*
 * Write Data: Tier 2 z-Pack inline analysis + Direct O(1) storage
 */
static void hmb_write_segment(struct hmb_device *hmb, sector_t sector, const void *src, unsigned int len)
{
	unsigned long pgoff = sector >> PAGE_SECTORS_SHIFT;
	unsigned int offset = (sector & (PAGE_SECTORS - 1)) << 9;
	struct page *p = NULL;
	struct page *old_p = NULL;
	u64 val = 0;

	if (unlikely(pgoff >= hmb->total_pages))
		return;

	/* Full page write: Analyze for Tier 2 z-Pack Compression */
	if (zpack_enable && offset == 0 && len == PAGE_SIZE) {
		if (hmb_is_uniform_quadword(src, &val)) {
			if (val == 0) {
				/* 100% Zero Page: 1 bit metadata only */
				set_bit(pgoff, hmb->zero_bitmap);
				clear_bit(pgoff, hmb->pattern_bitmap);
				clear_bit(pgoff, hmb->allocated_bitmap);

				spin_lock(&hmb->lock);
				old_p = hmb->raw_pages[pgoff];
				hmb->raw_pages[pgoff] = NULL;
				spin_unlock(&hmb->lock);

				if (old_p)
					__free_page(old_p);

				atomic64_inc(&hmb->stats.zpack_zero_hits);
				atomic64_add(PAGE_SIZE, &hmb->stats.bytes_saved);
				atomic64_inc(&hmb->stats.writes);
				return;
			} else {
				/* Repeating Quadword: 8 bytes metadata */
				hmb->patterns[pgoff] = val;
				set_bit(pgoff, hmb->pattern_bitmap);
				clear_bit(pgoff, hmb->zero_bitmap);
				clear_bit(pgoff, hmb->allocated_bitmap);

				spin_lock(&hmb->lock);
				old_p = hmb->raw_pages[pgoff];
				hmb->raw_pages[pgoff] = NULL;
				spin_unlock(&hmb->lock);

				if (old_p)
					__free_page(old_p);

				atomic64_inc(&hmb->stats.zpack_pattern_hits);
				atomic64_add(PAGE_SIZE - sizeof(u64), &hmb->stats.bytes_saved);
				atomic64_inc(&hmb->stats.writes);
				return;
			}
		}
	}

	/* Incompressible or partial write: Back by raw page */
	spin_lock(&hmb->lock);
	p = hmb->raw_pages[pgoff];
	if (!p) {
		spin_unlock(&hmb->lock);
		p = alloc_page(GFP_NOIO | __GFP_ZERO | __GFP_HIGHMEM);
		if (!p)
			return;

		spin_lock(&hmb->lock);
		if (!hmb->raw_pages[pgoff]) {
			hmb->raw_pages[pgoff] = p;
		} else {
			__free_page(p);
			p = hmb->raw_pages[pgoff];
		}
	}
	get_page(p);
	spin_unlock(&hmb->lock);

	clear_bit(pgoff, hmb->zero_bitmap);
	clear_bit(pgoff, hmb->pattern_bitmap);
	set_bit(pgoff, hmb->allocated_bitmap);

	memcpy_to_page(p, offset, src, len);
	put_page(p);

	atomic64_inc(&hmb->stats.raw_pages);
	atomic64_inc(&hmb->stats.writes);
}

/*
 * Bio Submission Entry Point: Fast synchronous processing
 */
static void hmb_submit_bio(struct bio *bio)
{
	struct hmb_device *hmb = bio->bi_bdev->bd_disk->private_data;
	struct bvec_iter iter;
	struct bio_vec bvec;

	if (unlikely(op_is_discard(bio->bi_opf))) {
		hmb_do_discard(hmb, bio->bi_iter.bi_sector, bio->bi_iter.bi_size);
		bio_endio(bio);
		return;
	}

	bio_for_each_segment(bvec, bio, iter) {
		void *kaddr = bvec_kmap_local(&bvec);

		if (bio_data_dir(bio) == WRITE)
			hmb_write_segment(hmb, iter.bi_sector, kaddr, bvec.bv_len);
		else
			hmb_read_segment(hmb, iter.bi_sector, kaddr, bvec.bv_len);

		kunmap_local(kaddr);
	}

	bio_endio(bio);
}

static const struct block_device_operations hmb_fops = {
	.owner = THIS_MODULE,
	.submit_bio = hmb_submit_bio,
};

/*
 * /proc/hmb_swap Telemetry Output
 */
static int hmb_proc_show(struct seq_file *m, void *v)
{
	struct hmb_device *hmb = g_hmb_dev;
	u64 reads = atomic64_read(&hmb->stats.reads);
	u64 writes = atomic64_read(&hmb->stats.writes);
	u64 discards = atomic64_read(&hmb->stats.discards);
	u64 zero_hits = atomic64_read(&hmb->stats.zpack_zero_hits);
	u64 pat_hits = atomic64_read(&hmb->stats.zpack_pattern_hits);
	u64 raw_pages = atomic64_read(&hmb->stats.raw_pages);
	u64 bytes_saved = atomic64_read(&hmb->stats.bytes_saved);
	u64 total_ops = reads + writes;
	u64 total_comp = zero_hits + pat_hits;
	u64 total_stored = total_comp + raw_pages;

	seq_puts(m, "================================================================================\n");
	seq_puts(m, "  HAVEN MEMORY BUS (HMB) — LINUX KERNEL SWAP SUBSYSTEM (Spec 2.0)\n");
	seq_printf(m, "  Device Node: /dev/%s | Stride: %lu bytes (64-bit aligned)\n",
		   hmb->disk->disk_name, PAGE_SIZE);
	seq_puts(m, "================================================================================\n");
	seq_printf(m, "Capacity:                %d MB (%lu swap pages)\n",
		   size_mb, hmb->total_pages);
	seq_printf(m, "Direct O(1) Reads:       %llu ops\n", reads);
	seq_printf(m, "Direct O(1) Writes:      %llu ops\n", writes);
	seq_printf(m, "Atomic Discards/Trims:   %llu ops\n", discards);
	seq_printf(m, "Total I/O Operations:    %llu\n", total_ops);
	seq_puts(m, "--------------------------------------------------------------------------------\n");
	seq_puts(m, "[Tier 2 z-Pack In-RAM Deduplication & Compression Engine]\n");
	seq_printf(m, "  Zero-Page Deduplication: %llu pages (100.0%% compression)\n", zero_hits);
	seq_printf(m, "  Uniform Pattern Hits:    %llu pages (99.8%% compression)\n", pat_hits);
	seq_printf(m, "  Raw Stride Allocations:  %llu pages\n", raw_pages);
	seq_printf(m, "  Physical RAM Saved:      %llu MB (%llu KB)\n",
		   bytes_saved >> 20, bytes_saved >> 10);
	if (total_stored > 0) {
		u64 ratio_x10 = (total_stored * 10) / (raw_pages ? raw_pages : 1);
		seq_printf(m, "  Effective Compression:   %llu.%llux Ratio\n",
			   ratio_x10 / 10, ratio_x10 % 10);
	} else {
		seq_puts(m, "  Effective Compression:   1.0x Ratio (Idle)\n");
	}
	seq_puts(m, "================================================================================\n");
	return 0;
}

static int hmb_proc_open(struct inode *inode, struct file *file)
{
	return single_open(file, hmb_proc_show, NULL);
}

static const struct proc_ops hmb_proc_fops = {
	.proc_open = hmb_proc_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int __init hmb_swap_init(void)
{
	int err = 0;
	struct hmb_device *hmb;
	unsigned long bitmap_bytes;
	struct queue_limits lim = {
		.logical_block_size = 512,
		.physical_block_size = PAGE_SIZE,
		.max_hw_sectors = PAGE_SECTORS * 64, /* 64-page clusters */
		.max_sectors = PAGE_SECTORS * 64,
		.max_hw_discard_sectors = UINT_MAX,
		.max_discard_segments = 1,
		.discard_granularity = PAGE_SIZE,
		.features = BLK_FEAT_SYNCHRONOUS | BLK_FEAT_NOWAIT,
	};

	pr_info(DRV_NAME ": Initializing Haven Memory Bus (HMB) Swap Driver (Size: %d MB)\n", size_mb);

	hmb = kzalloc(sizeof(*hmb), GFP_KERNEL);
	if (!hmb)
		return -ENOMEM;

	hmb->capacity_sectors = ((sector_t)size_mb * 1024 * 1024) >> 9;
	hmb->total_pages = size_mb * (1024 * 1024 / PAGE_SIZE);
	spin_lock_init(&hmb->lock);

	bitmap_bytes = BITS_TO_LONGS(hmb->total_pages) * sizeof(unsigned long);

	hmb->allocated_bitmap = vzalloc(bitmap_bytes);
	hmb->zero_bitmap = vzalloc(bitmap_bytes);
	hmb->pattern_bitmap = vzalloc(bitmap_bytes);
	hmb->patterns = vzalloc(hmb->total_pages * sizeof(u64));
	hmb->raw_pages = vzalloc(hmb->total_pages * sizeof(struct page *));

	if (!hmb->allocated_bitmap || !hmb->zero_bitmap ||
	    !hmb->pattern_bitmap || !hmb->patterns || !hmb->raw_pages) {
		err = -ENOMEM;
		goto out_free_mem;
	}

	hmb->major = register_blkdev(0, "hmb");
	if (hmb->major < 0) {
		err = hmb->major;
		goto out_free_mem;
	}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 9, 0)
	hmb->disk = blk_alloc_disk(&lim, NUMA_NO_NODE);
#else
	hmb->disk = blk_alloc_disk(NUMA_NO_NODE);
#endif
	if (IS_ERR(hmb->disk)) {
		err = PTR_ERR(hmb->disk);
		goto out_unregister_blkdev;
	}

	hmb->disk->major = hmb->major;
	hmb->disk->first_minor = 0;
	hmb->disk->minors = 1;
	hmb->disk->fops = &hmb_fops;
	hmb->disk->private_data = hmb;
	strscpy(hmb->disk->disk_name, "hmb0", DISK_NAME_LEN);
	set_capacity(hmb->disk, hmb->capacity_sectors);

	err = add_disk(hmb->disk);
	if (err)
		goto out_cleanup_disk;

	g_proc_entry = proc_create("hmb_swap", 0444, NULL, &hmb_proc_fops);
	g_hmb_dev = hmb;

	pr_info(DRV_NAME ": /dev/hmb0 ready (%d MB, %lu pages). /proc/hmb_swap online.\n",
		size_mb, hmb->total_pages);
	return 0;

out_cleanup_disk:
	put_disk(hmb->disk);
out_unregister_blkdev:
	unregister_blkdev(hmb->major, "hmb");
out_free_mem:
	vfree(hmb->raw_pages);
	vfree(hmb->patterns);
	vfree(hmb->pattern_bitmap);
	vfree(hmb->zero_bitmap);
	vfree(hmb->allocated_bitmap);
	kfree(hmb);
	return err;
}

static void __exit hmb_swap_exit(void)
{
	struct hmb_device *hmb = g_hmb_dev;
	unsigned long i;

	if (g_proc_entry)
		proc_remove(g_proc_entry);

	if (hmb) {
		del_gendisk(hmb->disk);
		put_disk(hmb->disk);
		unregister_blkdev(hmb->major, "hmb");

		/* Free raw allocated pages */
		for (i = 0; i < hmb->total_pages; i++) {
			if (hmb->raw_pages[i])
				__free_page(hmb->raw_pages[i]);
		}

		vfree(hmb->raw_pages);
		vfree(hmb->patterns);
		vfree(hmb->pattern_bitmap);
		vfree(hmb->zero_bitmap);
		vfree(hmb->allocated_bitmap);
		kfree(hmb);
	}

	pr_info(DRV_NAME ": Haven Memory Bus (HMB) swap driver unloaded cleanly.\n");
}

module_init(hmb_swap_init);
module_exit(hmb_swap_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Daniel Elliott <ssfdre38@gmail.com>");
MODULE_DESCRIPTION("Haven Memory Bus (HMB) Direct-Stride Swap Block Driver");
MODULE_VERSION("2.0.0");
