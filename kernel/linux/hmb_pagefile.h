/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Haven Memory Bus (HMB) - Native In-Tree Paging Engine
 * Implementation of HMB Spec 2.0 for Linux Kernel 7.0 VMM
 *
 * Copyright (C) 2026 Daniel Barrer / Barrer Software Org.
 */

#ifndef _LINUX_HMB_PAGEFILE_H
#define _LINUX_HMB_PAGEFILE_H

#include <linux/types.h>
#include <linux/mm_types.h>
#include <linux/swap.h>

#ifdef CONFIG_HMB_PAGEFILE

bool hmb_pagefile_store(struct folio *folio);
bool hmb_pagefile_load(struct folio *folio);
void hmb_pagefile_free(swp_entry_t entry);
int hmb_pagefile_init(void);

#else /* !CONFIG_HMB_PAGEFILE */

static inline bool hmb_pagefile_store(struct folio *folio) { return false; }
static inline bool hmb_pagefile_load(struct folio *folio) { return false; }
static inline void hmb_pagefile_free(swp_entry_t entry) {}
static inline int hmb_pagefile_init(void) { return 0; }

#endif /* CONFIG_HMB_PAGEFILE */

#endif /* _LINUX_HMB_PAGEFILE_H */
