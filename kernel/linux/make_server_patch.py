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

    # 1. Add MAINTAINERS entry on server if not present
    entry = """HAVEN MEMORY BUS (HMB) PAGEFILE ENGINE
M:	Daniel Elliott <ssfdre38@gmail.com>
L:	linux-mm@kvack.org
S:	Maintained
W:	https://github.com/barrersoftware/hmb
F:	include/linux/hmb_pagefile.h
F:	mm/hmb_pagefile.c
"""
    cmd = """
if ! grep -q 'HAVEN MEMORY BUS' /home/ubuntu/linux-7.0.0/MAINTAINERS; then
    sed -i '/^HARDWARE MONITORING/i HAVEN MEMORY BUS (HMB) PAGEFILE ENGINE\\nM:\\tDaniel Elliott <ssfdre38@gmail.com>\\nL:\\tlinux-mm@kvack.org\\nS:\\tMaintained\\nW:\\thttps://github.com/barrersoftware/hmb\\nF:\\tinclude/linux/hmb_pagefile.h\\nF:\\tmm/hmb_pagefile.c\\n' /home/ubuntu/linux-7.0.0/MAINTAINERS
fi
"""
    stdin, stdout, stderr = c.exec_command(cmd)
    stdout.channel.recv_exit_status()

    # 2. Fix page_io.c and swapfile.c headers order
    # Ensure #include <linux/hmb_pagefile.h> is placed after line 30, not before SPDX
    fix_headers = """
sed -i '/#include <linux\\/hmb_pagefile.h>/d' /home/ubuntu/linux-7.0.0/mm/page_io.c
sed -i '/#include <linux\\/mempool.h>/a #include <linux/hmb_pagefile.h>' /home/ubuntu/linux-7.0.0/mm/page_io.c

sed -i '/#include <linux\\/hmb_pagefile.h>/d' /home/ubuntu/linux-7.0.0/mm/swapfile.c
sed -i '/#include <linux\\/zswap.h>/a #include <linux/hmb_pagefile.h>' /home/ubuntu/linux-7.0.0/mm/swapfile.c
"""
    stdin, stdout, stderr = c.exec_command(fix_headers)
    stdout.channel.recv_exit_status()

    # 3. Create a clean git commit in a separate branch or generate patch with diff -u
    gen_cmd = """
cd /home/ubuntu/linux-7.0.0
diff -uN /dev/null include/linux/hmb_pagefile.h > /home/ubuntu/hmb_generated.patch
diff -uN /dev/null mm/hmb_pagefile.c >> /home/ubuntu/hmb_generated.patch
git diff MAINTAINERS mm/Kconfig mm/Makefile mm/page_io.c mm/swapfile.c >> /home/ubuntu/hmb_generated.patch 2>/dev/null || true
perl scripts/checkpatch.pl --no-tree /home/ubuntu/hmb_generated.patch
"""
    stdin, stdout, stderr = c.exec_command(gen_cmd)
    print(stdout.read().decode('utf-8', 'replace'))
    print(stderr.read().decode('utf-8', 'replace'))

    c.close()

if __name__ == "__main__":
    main()
