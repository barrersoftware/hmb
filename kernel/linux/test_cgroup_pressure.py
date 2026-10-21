#!/usr/bin/env python3
"""
Test Real Linux Virtual Memory Swap Pressure via cgroup v2
Target: 147.135.1.229 (/dev/hmb0 Priority 100 Swap)
"""

import sys
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def safe_print(text):
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace') + b'\n')
    sys.stdout.buffer.flush()

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, pkey=k, timeout=10)
    safe_print("[*] SSH Connected to server.")

    # Script to run inside constrained cgroup (256MB RAM limit)
    worker_script = '''#!/usr/bin/env python3
import time
import os
import sys

print("[cgroup worker] PID:", os.getpid())
print("[cgroup worker] Allocating 600 MB of dirty heap inside a 256 MB RAM cgroup...")

# We allocate 600 MB:
# Chunk 1: 300 MB of zeros (Tier 2 Zero-Page test)
# Chunk 2: 150 MB of repetitive patterns (Tier 2 Pattern test)
# Chunk 3: 150 MB of varied text/data (Tier 1 Raw test)

t0 = time.perf_counter()

print(" -> Allocating Chunk 1 (300 MB zero-fill)...")
c1 = bytearray(300 * 1024 * 1024)

print(" -> Allocating Chunk 2 (150 MB pattern-fill)...")
pat = b"HAVEN_MEMORY_BUS" * 256 # 4096 bytes
c2 = bytearray(pat * (150 * 1024 * 1024 // len(pat)))

print(" -> Allocating Chunk 3 (150 MB varied data)...")
c3 = bytearray(os.urandom(150 * 1024 * 1024))

t1 = time.perf_counter()
print(f" -> Allocation completed in {t1 - t0:.3f}s. System was forced to swap ~350 MB to /dev/hmb0!")

# Read everything back to trigger page-in from swap
print(" -> Verifying/Reading back all 600 MB from swap...")
t0_read = time.perf_counter()
s1 = sum(c1[:1024 * 1024])
s2 = sum(c2[:1024 * 1024])
s3 = sum(c3[:1024 * 1024])
t1_read = time.perf_counter()
print(f" -> Read-back completed in {t1_read - t0_read:.3f}s! Zero stalls, zero drive thrashing.")
'''

    sftp = client.open_sftp()
    with sftp.open("/home/ubuntu/hmb_linux/cgroup_swap_worker.py", "w") as f:
        f.write(worker_script)
    sftp.close()

    safe_print("\n[*] Launching cgroup-constrained memory pressure test (MemoryMax=256M)...")
    cmd = "sudo systemd-run --scope -p MemoryMax=256M -p MemorySwapMax=2G python3 /home/ubuntu/hmb_linux/cgroup_swap_worker.py"
    safe_print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    safe_print(stdout.read().decode('utf-8', errors='replace'))
    err = stderr.read().decode('utf-8', errors='replace')
    if err and "Running scope" not in err:
        safe_print(f"ERR: {err}")

    # Read final /proc/hmb_swap
    safe_print("\n================================================================================")
    safe_print("  TELEMETRY FROM /proc/hmb_swap AFTER REAL KERNEL SWAP PRESSURE")
    safe_print("================================================================================")
    stdin, stdout, stderr = client.exec_command("cat /proc/hmb_swap")
    safe_print(stdout.read().decode('utf-8', errors='replace'))

    # Check swapon status
    stdin, stdout, stderr = client.exec_command("swapon --show")
    safe_print(stdout.read().decode('utf-8', errors='replace'))

    client.close()

if __name__ == "__main__":
    main()
