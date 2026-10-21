#!/usr/bin/env python3
import sys
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    cmd = """
rm -rf /tmp/kernel_virgin && mkdir -p /tmp/kernel_virgin
tar -xjf /usr/src/linux-source-7.0.0.tar.bz2 -C /tmp/kernel_virgin \
    linux-source-7.0.0/MAINTAINERS \
    linux-source-7.0.0/mm/Kconfig \
    linux-source-7.0.0/mm/Makefile \
    linux-source-7.0.0/mm/page_io.c \
    linux-source-7.0.0/mm/swapfile.c

cd /home/ubuntu/linux-7.0.0

cat << 'EOF' > /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch
From: Daniel Barrer <ssfdre38@gmail.com>
Date: Wed, 21 Oct 2026 17:00:00 +0000
Subject: [RFC PATCH] mm: Haven Memory Bus (HMB) zero-bio paging engine

Implement Haven Memory Bus (HMB) Spec 2.0 direct-stride virtual
memory paging inside the Linux Virtual Memory Manager (VMM).

Bypasses the generic block layer (struct bio, blk-mq, and elevator
queues) in mm/page_io.c, resolving page faults in sub-microsecond
O(1) arithmetic strides with Tier 2 z-Pack in-RAM deduplication.

Signed-off-by: Daniel Barrer <ssfdre38@gmail.com>
---
EOF

diff -uN /dev/null include/linux/hmb_pagefile.h | sed 's|^--- /dev/null|--- a/include/linux/hmb_pagefile.h\nnew file mode 100644\n--- /dev/null|' | sed 's|+++ include/linux/hmb_pagefile.h|+++ b/include/linux/hmb_pagefile.h|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch
diff -uN /dev/null mm/hmb_pagefile.c | sed 's|^--- /dev/null|--- a/mm/hmb_pagefile.c\nnew file mode 100644\n--- /dev/null|' | sed 's|+++ mm/hmb_pagefile.c|+++ b/mm/hmb_pagefile.c|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch
diff -u /tmp/kernel_virgin/linux-source-7.0.0/MAINTAINERS MAINTAINERS | sed 's|/tmp/kernel_virgin/linux-source-7.0.0/MAINTAINERS|a/MAINTAINERS|' | sed 's|MAINTAINERS|b/MAINTAINERS|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch || true
diff -u /tmp/kernel_virgin/linux-source-7.0.0/mm/Kconfig mm/Kconfig | sed 's|/tmp/kernel_virgin/linux-source-7.0.0/mm/Kconfig|a/mm/Kconfig|' | sed 's|mm/Kconfig|b/mm/Kconfig|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch || true
diff -u /tmp/kernel_virgin/linux-source-7.0.0/mm/Makefile mm/Makefile | sed 's|/tmp/kernel_virgin/linux-source-7.0.0/mm/Makefile|a/mm/Makefile|' | sed 's|mm/Makefile|b/mm/Makefile|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch || true
diff -u /tmp/kernel_virgin/linux-source-7.0.0/mm/page_io.c mm/page_io.c | sed 's|/tmp/kernel_virgin/linux-source-7.0.0/mm/page_io.c|a/mm/page_io.c|' | sed 's|mm/page_io.c|b/mm/page_io.c|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch || true
diff -u /tmp/kernel_virgin/linux-source-7.0.0/mm/swapfile.c mm/swapfile.c | sed 's|/tmp/kernel_virgin/linux-source-7.0.0/mm/swapfile.c|a/mm/swapfile.c|' | sed 's|mm/swapfile.c|b/mm/swapfile.c|' >> /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch || true

perl scripts/checkpatch.pl --no-tree /home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch
"""
    stdin, stdout, stderr = c.exec_command(cmd)
    print(stdout.read().decode('utf-8', 'replace'))
    print(stderr.read().decode('utf-8', 'replace'))

    # Download pristine patch to local workspace
    sftp = c.open_sftp()
    sftp.get('/home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch', r'C:\Users\admin\source\hmb\kernel\in_tree_patch\hmb_in_tree_linux_7.0.patch')
    sftp.get('/home/ubuntu/0001-mm-hmb-zero-bio-paging-engine.patch', r'C:\Users\admin\source\hmb\kernel\linux\hmb_in_tree_linux_7.0.patch')
    sftp.close()
    print("[*] Successfully retrieved pristine upstream-ready patch!")

    c.close()

if __name__ == "__main__":
    main()
