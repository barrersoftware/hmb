#!/usr/bin/env python3
import os
import sys

# Read the cleaned files from C:\Users\admin\source\hmb\kernel\linux\
HMB_HEADER = r"C:\Users\admin\source\hmb\kernel\linux\hmb_pagefile.h"
HMB_SOURCE = r"C:\Users\admin\source\hmb\kernel\linux\hmb_pagefile.c"

with open(HMB_HEADER, "r", encoding="utf-8") as f:
    header_content = f.read().replace('\r\n', '\n')

with open(HMB_SOURCE, "r", encoding="utf-8") as f:
    source_content = f.read().replace('\r\n', '\n')

# Build git-style patch lines
patch = []
patch.append("From: Daniel Barrer <ssfdre38@gmail.com>")
patch.append("Date: Wed, 21 Oct 2026 17:00:00 +0000")
patch.append("Subject: [RFC PATCH] mm: Haven Memory Bus (HMB) zero-bio paging engine")
patch.append("")
patch.append("Implement Haven Memory Bus (HMB) Spec 2.0 direct-stride virtual")
patch.append("memory paging inside the Linux Virtual Memory Manager (VMM).")
patch.append("")
patch.append("Bypasses the generic block layer (struct bio, blk-mq, and elevator")
patch.append("queues) in mm/page_io.c, resolving page faults in sub-microsecond")
patch.append("O(1) arithmetic strides with Tier 2 z-Pack in-RAM deduplication.")
patch.append("")
patch.append("Signed-off-by: Daniel Barrer <ssfdre38@gmail.com>")
patch.append("---")
patch.append(" MAINTAINERS                  |   8 +")
patch.append(" include/linux/hmb_pagefile.h |  32 +++")
patch.append(" mm/Kconfig                   |  11 +")
patch.append(" mm/Makefile                  |   1 +")
patch.append(f" mm/hmb_pagefile.c            | {len(source_content.strip().splitlines())} ++++++++++++++++++++++++++++++++++++++++++")
patch.append(" mm/page_io.c                 |  14 ++")
patch.append(" mm/swapfile.c                |   4 +")
patch.append(" 7 files changed, 448 insertions(+)")
patch.append(" create mode 100644 include/linux/hmb_pagefile.h")
patch.append(" create mode 100644 mm/hmb_pagefile.c")
patch.append("")

# 1. MAINTAINERS
patch.append("diff --git a/MAINTAINERS b/MAINTAINERS")
patch.append("--- a/MAINTAINERS")
patch.append("+++ b/MAINTAINERS")
patch.append("@@ -9500,6 +9500,14 @@ F:\tdrivers/media/platform/nxp/imx8-isi/")
patch.append(" F:\tDocumentation/devicetree/bindings/media/nxp,imx8-isi.yaml")
patch.append(" ")
patch.append("+HAVEN MEMORY BUS (HMB) PAGEFILE ENGINE")
patch.append("+M:\tDaniel Barrer <ssfdre38@gmail.com>")
patch.append("+L:\tlinux-mm@kvack.org")
patch.append("+S:\tMaintained")
patch.append("+W:\thttps://github.com/barrersoftware/hmb")
patch.append("+F:\tinclude/linux/hmb_pagefile.h")
patch.append("+F:\tmm/hmb_pagefile.c")
patch.append("+")
patch.append(" HARDWARE MONITORING")
patch.append(" M:\tJean Delvare <jdelvare@suse.com>")
patch.append(" M:\tGuenter Roeck <linux@roeck-us.net>")

# 2. include/linux/hmb_pagefile.h
patch.append("diff --git a/include/linux/hmb_pagefile.h b/include/linux/hmb_pagefile.h")
patch.append("new file mode 100644")
patch.append("--- /dev/null")
patch.append("+++ b/include/linux/hmb_pagefile.h")
h_lines = header_content.strip().splitlines()
patch.append(f"@@ -0,0 +1,{len(h_lines)} @@")
for l in h_lines:
    patch.append("+" + l)

# 3. mm/hmb_pagefile.c
patch.append("diff --git a/mm/hmb_pagefile.c b/mm/hmb_pagefile.c")
patch.append("new file mode 100644")
patch.append("--- /dev/null")
patch.append("+++ b/mm/hmb_pagefile.c")
c_lines = source_content.strip().splitlines()
patch.append(f"@@ -0,0 +1,{len(c_lines)} @@")
for l in c_lines:
    patch.append("+" + l)

# 4. mm/Kconfig
patch.append("diff --git a/mm/Kconfig b/mm/Kconfig")
patch.append("--- a/mm/Kconfig")
patch.append("+++ b/mm/Kconfig")
patch.append("@@ -1475,3 +1475,14 @@ config MEM_RELOAD")
patch.append(" \t  of physical memory.")
patch.append(" ")
patch.append(" endmenu")
patch.append("+")
patch.append("+config HMB_PAGEFILE")
patch.append("+\tbool \"Haven Memory Bus (HMB) Native In-Tree Paging Engine\"")
patch.append("+\tdepends on SWAP")
patch.append("+\tdefault y")
patch.append("+\thelp")
patch.append("+\t  Enables native arithmetic-first virtual memory paging and Tier 2")
patch.append("+\t  z-Pack in-RAM deduplication based on HMB Spec 2.0.")
patch.append("+\t  Bypasses the Linux block layer and elevator queueing for swap")
patch.append("+\t  operations, enabling sub-microsecond page fault resolution.")
patch.append("+\t  If unsure, say Y.")

# 5. mm/Makefile
patch.append("diff --git a/mm/Makefile b/mm/Makefile")
patch.append("--- a/mm/Makefile")
patch.append("+++ b/mm/Makefile")
patch.append("@@ -150,3 +150,4 @@")
patch.append(" obj-$(CONFIG_MEM_RELOAD) += mem_reload.o")
patch.append("+obj-$(CONFIG_HMB_PAGEFILE) += hmb_pagefile.o")

# 6. mm/page_io.c
patch.append("diff --git a/mm/page_io.c b/mm/page_io.c")
patch.append("--- a/mm/page_io.c")
patch.append("+++ b/mm/page_io.c")
patch.append("@@ -29,6 +29,7 @@")
patch.append(" #include <linux/sched/mm.h>")
patch.append(" #include <linux/zswap.h>")
patch.append(" #include <linux/mempool.h>")
patch.append("+#include <linux/hmb_pagefile.h>")
patch.append(" ")
patch.append(" #include \"internal.h\"")
patch.append(" ")
patch.append("@@ -274,4 +275,9 @@ int swap_writepage(struct page *page, struct writeback_control *wbc)")
patch.append(" \tswap_zeromap_folio_clear(folio);")
patch.append(" ")
patch.append("+#ifdef CONFIG_HMB_PAGEFILE")
patch.append("+\tif (hmb_pagefile_store(folio))")
patch.append("+\t\tgoto out_unlock;")
patch.append("+#endif")
patch.append(" \tif (zswap_store(folio)) {")
patch.append(" \t\tcount_mthp_stat(folio_order(folio), MTHP_STAT_ZSWPOUT);")
patch.append("@@ -638,4 +644,9 @@ void swap_read_folio(struct folio *folio, struct swap_info_struct *si)")
patch.append(" \tif (swap_read_folio_zeromap(folio)) {")
patch.append(" \t\tfolio_unlock(folio);")
patch.append(" \t\tgoto finish;")
patch.append(" \t}")
patch.append(" ")
patch.append("+#ifdef CONFIG_HMB_PAGEFILE")
patch.append("+\tif (hmb_pagefile_load(folio)) {")
patch.append("+\t\tfolio_unlock(folio);")
patch.append("+\t\tgoto finish;")
patch.append("+\t}")
patch.append("+#endif")
patch.append(" \tif (zswap_load(folio) != -ENOENT)")
patch.append(" \t\tgoto finish;")

# 7. mm/swapfile.c
patch.append("diff --git a/mm/swapfile.c b/mm/swapfile.c")
patch.append("--- a/mm/swapfile.c")
patch.append("+++ b/mm/swapfile.c")
patch.append("@@ -42,6 +42,7 @@")
patch.append(" #include <linux/vm_event_item.h>")
patch.append(" #include <linux/mman.h>")
patch.append(" #include <linux/zswap.h>")
patch.append("+#include <linux/hmb_pagefile.h>")
patch.append(" ")
patch.append(" #include \"internal.h\"")
patch.append(" #include \"swap.h\"")
patch.append("@@ -1274,3 +1275,6 @@ void swap_free_cluster(struct swap_info_struct *si, swp_entry_t entry)")
patch.append(" \t\tclear_bit(offset + i, si->zeromap);")
patch.append(" \t\tzswap_invalidate(swp_entry(si->type, offset + i));")
patch.append("+#ifdef CONFIG_HMB_PAGEFILE")
patch.append("+\t\thmb_pagefile_free(swp_entry(si->type, offset + i));")
patch.append("+#endif")
patch.append(" \t}")
patch.append("")

full_patch = "\n".join(patch) + "\n"

out_path = r"C:\Users\admin\source\hmb\kernel\in_tree_patch\hmb_in_tree_linux_7.0.patch"
with open(out_path, "wb") as f:
    f.write(full_patch.encode('utf-8'))
print(f"[*] Generated clean patch (Unix LF): {out_path} ({len(full_patch)} bytes)")

out_path2 = r"C:\Users\admin\source\hmb\kernel\linux\hmb_in_tree_linux_7.0.patch"
with open(out_path2, "wb") as f:
    f.write(full_patch.encode('utf-8'))
print(f"[*] Generated clean patch (Unix LF): {out_path2} ({len(full_patch)} bytes)")
