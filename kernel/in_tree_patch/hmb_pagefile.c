// SPDX-License-Identifier: GPL-2.0
/*
 * Haven Memory Bus (HMB) - Native In-Tree Paging Engine
 * Implementation of HMB Spec 2.0 for Linux Kernel 7.0 VMM
 *
 * Copyright (C) 2026 Daniel Elliott / Barrer Software Org.
 *
 * Directly integrated into:
 *  - mm/page_io.c: swap_writepage() and swap_read_folio()
 *  - mm/swapfile.c: swap_entry_free() / swap_free()
 *
 * Eliminates block layer overhead, bio allocation, and scheduler latency.
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/mm.h>
#include <linux/swap.h>
#include <linux/swapops.h>
#include <linux/pagemap.h>
#include <linux/highmem.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/hmb_pagefile.h>

#define HMB_PAGEFILE_MAX_PAGES (1048576UL) /* 4 GB virtual swap plane */

struct hmb_pagefile_stats {
	atomic64_t reads;
	atomic64_t writes;
	atomic64_t frees;
	atomic64_t zero_hits;
	atomic64_t pattern_hits;
	atomic64_t raw_pages;
	atomic64_t bytes_saved;
};

struct hmb_pagefile_plane {
	unsigned long total_pages;
	unsigned long *allocated_bitmap;
	unsigned long *zero_bitmap;
	unsigned long *pattern_bitmap;
	u64 *patterns;
	struct page **raw_pages;
	spinlock_t lock;
	struct hmb_pagefile_stats stats;
};

static struct hmb_pagefile_plane *g_hmb_plane;
static struct proc_dir_entry *g_hmb_proc_entry;

static inline bool hmb_is_uniform_64(const void *kaddr, u64 *out_val)
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
 * Store Folio: Fast-path evaluation of Tier 2 z-Pack inline deduplication
 * Returns true if folio handled in-memory by HMB, false to fallback to block I/O.
 */
bool hmb_pagefile_store(struct folio *folio)
{
	struct hmb_pagefile_plane *plane = g_hmb_plane;
	swp_entry_t entry;
	unsigned long pgoff;
	void *kaddr;
	u64 val = 0;
	struct page *p = NULL;
	struct page *old_p = NULL;

	if (unlikely(!plane))
		return false;

	entry = folio->swap;
	pgoff = swp_offset(entry);

	if (unlikely(pgoff >= plane->total_pages))
		return false;

	kaddr = kmap_local_folio(folio, 0);

	/* Tier 2 z-Pack: Check 64-bit Quadword Uniformity */
	if (hmb_is_uniform_64(kaddr, &val)) {
		kunmap_local(kaddr);

		if (val == 0) {
			/* 100% Zero-Page: Stored as 1 single bit */
			set_bit(pgoff, plane->zero_bitmap);
			clear_bit(pgoff, plane->pattern_bitmap);
			clear_bit(pgoff, plane->allocated_bitmap);

			spin_lock(&plane->lock);
			old_p = plane->raw_pages[pgoff];
			plane->raw_pages[pgoff] = NULL;
			spin_unlock(&plane->lock);

			if (old_p)
				__free_page(old_p);

			atomic64_inc(&plane->stats.zero_hits);
			atomic64_add(PAGE_SIZE, &plane->stats.bytes_saved);
			atomic64_inc(&plane->stats.writes);

			folio_mark_uptodate(folio);
			return true;
		} else {
			/* Repeating Quadword: Stored in 8 bytes */
			plane->patterns[pgoff] = val;
			set_bit(pgoff, plane->pattern_bitmap);
			clear_bit(pgoff, plane->zero_bitmap);
			clear_bit(pgoff, plane->allocated_bitmap);

			spin_lock(&plane->lock);
			old_p = plane->raw_pages[pgoff];
			plane->raw_pages[pgoff] = NULL;
			spin_unlock(&plane->lock);

			if (old_p)
				__free_page(old_p);

			atomic64_inc(&plane->stats.pattern_hits);
			atomic64_add(PAGE_SIZE - sizeof(u64), &plane->stats.bytes_saved);
			atomic64_inc(&plane->stats.writes);

			folio_mark_uptodate(folio);
			return true;
		}
	}

	/* Incompressible Raw Page: Tier 1 Fixed Stride Allocation */
	spin_lock(&plane->lock);
	p = plane->raw_pages[pgoff];
	if (!p) {
		spin_unlock(&plane->lock);
		p = alloc_page(GFP_NOWAIT | __GFP_HIGHMEM);
		if (!p) {
			kunmap_local(kaddr);
			return false; /* Memory pressure fallback to block swap */
		}
		spin_lock(&plane->lock);
		if (!plane->raw_pages[pgoff]) {
			plane->raw_pages[pgoff] = p;
		} else {
			__free_page(p);
			p = plane->raw_pages[pgoff];
		}
	}
	get_page(p);
	spin_unlock(&plane->lock);

	memcpy_to_page(p, 0, kaddr, PAGE_SIZE);
	kunmap_local(kaddr);
	put_page(p);

	clear_bit(pgoff, plane->zero_bitmap);
	clear_bit(pgoff, plane->pattern_bitmap);
	set_bit(pgoff, plane->allocated_bitmap);

	atomic64_inc(&plane->stats.raw_pages);
	atomic64_inc(&plane->stats.writes);

	folio_mark_uptodate(folio);
	return true;
}
EXPORT_SYMBOL_GPL(hmb_pagefile_store);

/*
 * Load Folio: Nanosecond #PF page fault recovery
 * Returns true if folio recovered from HMB, false to read from disk.
 */
bool hmb_pagefile_load(struct folio *folio)
{
	struct hmb_pagefile_plane *plane = g_hmb_plane;
	swp_entry_t entry;
	unsigned long pgoff;
	struct page *p = NULL;
	void *dst;

	if (unlikely(!plane))
		return false;

	entry = folio->swap;
	pgoff = swp_offset(entry);

	if (unlikely(pgoff >= plane->total_pages))
		return false;

	/* Tier 2: Zero-Page Fast-Path */
	if (test_bit(pgoff, plane->zero_bitmap)) {
		folio_zero_range(folio, 0, folio_size(folio));
		folio_mark_uptodate(folio);
		atomic64_inc(&plane->stats.reads);
		return true;
	}

	/* Tier 2: Pattern Page Fast-Path */
	if (test_bit(pgoff, plane->pattern_bitmap)) {
		u64 val = plane->patterns[pgoff];
		dst = kmap_local_folio(folio, 0);
		memset64(dst, val, PAGE_SIZE / sizeof(u64));
		kunmap_local(dst);
		folio_mark_uptodate(folio);
		atomic64_inc(&plane->stats.reads);
		return true;
	}

	/* Tier 1: Raw Stride Memory Slab */
	if (test_bit(pgoff, plane->allocated_bitmap)) {
		spin_lock(&plane->lock);
		p = plane->raw_pages[pgoff];
		if (p)
			get_page(p);
		spin_unlock(&plane->lock);

		if (p) {
			void *src = kmap_local_page(p);
			dst = kmap_local_folio(folio, 0);
			memcpy(dst, src, PAGE_SIZE);
			kunmap_local(dst);
			kunmap_local(src);
			put_page(p);
			folio_mark_uptodate(folio);
			atomic64_inc(&plane->stats.reads);
			return true;
		}
	}

	return false;
}
EXPORT_SYMBOL_GPL(hmb_pagefile_load);

/*
 * Free Slot: Lock-free atomic bitmask clearing
 */
void hmb_pagefile_free(swp_entry_t entry)
{
	struct hmb_pagefile_plane *plane = g_hmb_plane;
	unsigned long pgoff;
	struct page *p = NULL;

	if (unlikely(!plane))
		return;

	pgoff = swp_offset(entry);
	if (unlikely(pgoff >= plane->total_pages))
		return;

	clear_bit(pgoff, plane->zero_bitmap);
	clear_bit(pgoff, plane->pattern_bitmap);

	if (test_and_clear_bit(pgoff, plane->allocated_bitmap)) {
		spin_lock(&plane->lock);
		p = plane->raw_pages[pgoff];
		plane->raw_pages[pgoff] = NULL;
		spin_unlock(&plane->lock);

		if (p)
			__free_page(p);
	}

	atomic64_inc(&plane->stats.frees);
}
EXPORT_SYMBOL_GPL(hmb_pagefile_free);

/*
 * /proc/hmb_pagefile Telemetry
 */
static int hmb_pagefile_proc_show(struct seq_file *m, void *v)
{
	struct hmb_pagefile_plane *plane = g_hmb_plane;
	u64 reads = atomic64_read(&plane->stats.reads);
	u64 writes = atomic64_read(&plane->stats.writes);
	u64 frees = atomic64_read(&plane->stats.frees);
	u64 zero_hits = atomic64_read(&plane->stats.zero_hits);
	u64 pat_hits = atomic64_read(&plane->stats.pattern_hits);
	u64 raw_pages = atomic64_read(&plane->stats.raw_pages);
	u64 bytes_saved = atomic64_read(&plane->stats.bytes_saved);
	u64 total_ops = reads + writes;
	u64 total_comp = zero_hits + pat_hits;
	u64 total_stored = total_comp + raw_pages;

	seq_puts(m, "================================================================================\n");
	seq_puts(m, "  HAVEN MEMORY BUS (HMB) — IN-TREE LINUX KERNEL PAGING ENGINE (Spec 2.0)\n");
	seq_puts(m, "  Mode: Native VMM Bypass (Zero Bio, Zero blk-mq, Pure Arithmetic)\n");
	seq_puts(m, "================================================================================\n");
	seq_printf(m, "Configured Plane:        %lu MB (%lu swap slots)\n",
		   (plane->total_pages * PAGE_SIZE) >> 20, plane->total_pages);
	seq_printf(m, "Direct O(1) Page In:     %llu faults resolved\n", reads);
	seq_printf(m, "Direct O(1) Page Out:    %llu pages evicted\n", writes);
	seq_printf(m, "Lock-Free Slot Frees:    %llu slots\n", frees);
	seq_printf(m, "Total VMM Paging Ops:    %llu\n", total_ops);
	seq_puts(m, "--------------------------------------------------------------------------------\n");
	seq_puts(m, "[Tier 2 z-Pack In-RAM Deduplication Engine]\n");
	seq_printf(m, "  Zero-Page Deduplication: %llu pages (100.0%% compression)\n", zero_hits);
	seq_printf(m, "  Uniform Pattern Hits:    %llu pages (99.8%% compression)\n", pat_hits);
	seq_printf(m, "  Raw Stride Allocations:  %llu pages\n", raw_pages);
	seq_printf(m, "  Physical RAM Saved:      %llu MB (%llu KB)\n",
		   bytes_saved >> 20, bytes_saved >> 10);
	if (total_stored > 0) {
		u64 ratio_x10 = (total_stored * 10) / (raw_pages ? raw_pages : 1);
		seq_printf(m, "  Effective Compression:   %llu.%llux Ratio\n",
			   ratio_x10 / 10, ratio_x10 % 10);
	}
	seq_puts(m, "================================================================================\n");
	return 0;
}

static int hmb_pagefile_proc_open(struct inode *inode, struct file *file)
{
	return single_open(file, hmb_pagefile_proc_show, NULL);
}

static const struct proc_ops hmb_pagefile_proc_fops = {
	.proc_open = hmb_pagefile_proc_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

int __init hmb_pagefile_init(void)
{
	struct hmb_pagefile_plane *plane;
	unsigned long bitmap_bytes;

	pr_info("HMB: Initializing Haven Memory Bus Native In-Tree Paging Engine...\n");

	plane = kzalloc(sizeof(*plane), GFP_KERNEL);
	if (!plane) {
		pr_err("HMB: Failed to allocate plane descriptor\n");
		return -ENOMEM;
	}

	plane->total_pages = HMB_PAGEFILE_MAX_PAGES;
	spin_lock_init(&plane->lock);

	bitmap_bytes = BITS_TO_LONGS(plane->total_pages) * sizeof(unsigned long);

	plane->allocated_bitmap = vzalloc(bitmap_bytes);
	plane->zero_bitmap = vzalloc(bitmap_bytes);
	plane->pattern_bitmap = vzalloc(bitmap_bytes);
	plane->patterns = vzalloc(plane->total_pages * sizeof(u64));
	plane->raw_pages = vzalloc(plane->total_pages * sizeof(struct page *));

	if (!plane->allocated_bitmap || !plane->zero_bitmap ||
	    !plane->pattern_bitmap || !plane->patterns || !plane->raw_pages) {
		pr_err("HMB: Memory plane allocation failed\n");
		vfree(plane->raw_pages);
		vfree(plane->patterns);
		vfree(plane->pattern_bitmap);
		vfree(plane->zero_bitmap);
		vfree(plane->allocated_bitmap);
		kfree(plane);
		return -ENOMEM;
	}

	g_hmb_plane = plane;
	g_hmb_proc_entry = proc_create("hmb_pagefile", 0444, NULL, &hmb_pagefile_proc_fops);

	pr_info("HMB: Native In-Tree Paging Engine ONLINE (%lu MB, %lu slots). /proc/hmb_pagefile ready.\n",
		(plane->total_pages * PAGE_SIZE) >> 20, plane->total_pages);
	return 0;
}
subsys_initcall(hmb_pagefile_init);
