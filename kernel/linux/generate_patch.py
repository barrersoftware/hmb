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

    # Generate git diff or diff
    cmd = """cd /home/ubuntu/linux-7.0.0 && git status >/dev/null 2>&1 || (git init >/dev/null && git add -N include/linux/hmb_pagefile.h mm/hmb_pagefile.c mm/page_io.c mm/swapfile.c mm/Makefile mm/Kconfig)
cd /home/ubuntu/linux-7.0.0 && git diff include/linux/hmb_pagefile.h mm/hmb_pagefile.c mm/page_io.c mm/swapfile.c mm/Makefile mm/Kconfig
"""
    stdin, stdout, stderr = c.exec_command(cmd)
    patch_content = stdout.read().decode('utf-8')

    with open(r"C:\Users\admin\source\hmb\kernel\linux\linux-7.0.0-hmb-pagefile.patch", "w", encoding="utf-8") as f:
        f.write(patch_content)
    print(f"[*] Saved linux-7.0.0-hmb-pagefile.patch ({len(patch_content)} bytes)")

    c.close()

if __name__ == "__main__":
    main()
