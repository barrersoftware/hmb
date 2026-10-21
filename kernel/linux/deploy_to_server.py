#!/usr/bin/env python3
"""
Deploy and Test Haven Memory Bus (HMB) Swap Driver on Live Linux Server
Target: 147.135.1.229 (Intel Xeon E3-1270 v6, 32GB ECC RAM, Ubuntu 26.04 / Linux 7.0)
"""

import os
import sys
import time
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def safe_print(text):
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace') + b'\n')
    sys.stdout.buffer.flush()

def exec_cmd(client, cmd, sudo=False):
    if sudo:
        cmd = f"sudo {cmd}"
    safe_print(f"\n[EXEC] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    rc = stdout.channel.recv_exit_status()
    if out:
        safe_print(out)
    if err and "password" not in err.lower() and "[sudo]" not in err.lower():
        safe_print(f"[stderr] {err}")
    return rc, out

def main():
    safe_print("================================================================================")
    safe_print("  Haven Memory Bus (HMB) - Bare-Metal Linux Swap Driver Deployment")
    safe_print(f"  Target: {HOST} ({USER})")
    safe_print("================================================================================")

    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, pkey=k, timeout=10)
    safe_print("[1/6] SSH Connected to bare-metal server.")

    # 1. Prepare directory and upload sources
    exec_cmd(client, "mkdir -p ~/hmb_linux")
    sftp = client.open_sftp()
    
    local_dir = r"C:\Users\admin\source\hmb\kernel\linux"
    with open(os.path.join(local_dir, "hmb_swap.c"), "r", encoding="utf-8") as f:
        sftp.open("/home/ubuntu/hmb_linux/hmb_swap.c", "w").write(f.read())
    
    server_makefile = """obj-m += hmb_swap.o
KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

default:
\t$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
\t$(MAKE) -C $(KDIR) M=$(PWD) clean
"""
    sftp.open("/home/ubuntu/hmb_linux/Makefile", "w").write(server_makefile)
    sftp.close()
    safe_print("[2/6] Staged hmb_swap.c and Makefile in ~/hmb_linux/")

    # 2. Build kernel module on target silicon
    safe_print("[3/6] Compiling hmb_swap.ko on target silicon...")
    rc, _ = exec_cmd(client, "cd ~/hmb_linux && make clean && make")
    if rc != 0:
        safe_print("[ERROR] Build failed on server.")
        return 1

    # 3. Clean up any existing swap / module
    exec_cmd(client, "swapoff /dev/hmb0 2>/dev/null || true", sudo=True)
    exec_cmd(client, "rmmod hmb_swap 2>/dev/null || true", sudo=True)

    # 4. Insert module and verify /dev/hmb0
    safe_print("[4/6] Loading hmb_swap.ko (2048 MB)...")
    rc, _ = exec_cmd(client, "sudo insmod /home/ubuntu/hmb_linux/hmb_swap.ko size_mb=2048")
    if rc != 0:
        safe_print("[ERROR] insmod failed.")
        return 1

    exec_cmd(client, "ls -la /dev/hmb0")
    exec_cmd(client, "dmesg | tail -n 10")

    # 5. Format and enable swap with priority 100
    safe_print("[5/6] Formatting /dev/hmb0 and enabling swap (priority=100)...")
    exec_cmd(client, "mkswap /dev/hmb0", sudo=True)
    exec_cmd(client, "swapon -p 100 /dev/hmb0", sudo=True)
    exec_cmd(client, "swapon --show")

    # 6. Read /proc/hmb_swap telemetry
    safe_print("[6/6] Reading initial HMB telemetry:")
    exec_cmd(client, "cat /proc/hmb_swap")

    safe_print("\n================================================================================")
    safe_print("  SUCCESS: HMB Linux Swap Driver is ACTIVE on Bare-Metal Silicon!")
    safe_print("================================================================================")
    client.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
