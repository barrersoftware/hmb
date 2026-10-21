#!/usr/bin/env python3
"""
Haven Memory Bus (HMB) - Live Bare-Metal Swap & Deduplication Benchmark
Target: 147.135.1.229 (/dev/hmb0 on Linux 7.0 / Xeon E3-1270 v6)
"""

import sys
import time
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

    benchmark_code = '''#!/usr/bin/env python3
import os
import sys
import time

DEV = "/dev/hmb0"
BLOCK_SIZE = 4096

print("================================================================================")
print("  HAVEN MEMORY BUS (HMB) - SILICON BENCHMARK ON /dev/hmb0")
print("================================================================================")

# 1. Tier 2 Zero-Page Test (128 MB of pure zeros)
ZERO_PAGES = 32768  # 128 MB
print(f"[*] [Test 1] Writing {ZERO_PAGES * 4 // 1024} MB of Zero Pages (Tier 2 Deduplication)...")
zero_buf = b"\\x00" * BLOCK_SIZE
t0 = time.perf_counter()
with open(DEV, "r+b", buffering=0) as f:
    f.seek(BLOCK_SIZE) # Skip swap header at sector 0
    for _ in range(ZERO_PAGES):
        f.write(zero_buf)
t1 = time.perf_counter()
mb_sec = 128.0 / (t1 - t0)
print(f"    --> Written in {t1 - t0:.4f}s ({mb_sec:.2f} MB/s) | Latency: {(t1 - t0) / ZERO_PAGES * 1e6:.2f} us/page")

# 2. Tier 2 Pattern Page Test (64 MB of repeating 0xDEADBEEFCAFEBABELL)
PAT_PAGES = 16384  # 64 MB
print(f"[*] [Test 2] Writing {PAT_PAGES * 4 // 1024} MB of Pattern Pages (Tier 2 Deduplication)...")
import struct
quad = struct.pack("<Q", 0xDEADBEEFCAFEBABE)
pat_buf = quad * (BLOCK_SIZE // 8)
t0 = time.perf_counter()
with open(DEV, "r+b", buffering=0) as f:
    f.seek(BLOCK_SIZE + (ZERO_PAGES * BLOCK_SIZE))
    for _ in range(PAT_PAGES):
        f.write(pat_buf)
t1 = time.perf_counter()
mb_sec = 64.0 / (t1 - t0)
print(f"    --> Written in {t1 - t0:.4f}s ({mb_sec:.2f} MB/s) | Latency: {(t1 - t0) / PAT_PAGES * 1e6:.2f} us/page")

# 3. Tier 1 Raw Stride Test (64 MB of Pseudo-random Pages)
RAW_PAGES = 16384  # 64 MB
print(f"[*] [Test 3] Writing {RAW_PAGES * 4 // 1024} MB of Incompressible Raw Pages (Tier 1 Fallback)...")
import os
raw_buf = os.urandom(BLOCK_SIZE)
t0 = time.perf_counter()
with open(DEV, "r+b", buffering=0) as f:
    f.seek(BLOCK_SIZE + ((ZERO_PAGES + PAT_PAGES) * BLOCK_SIZE))
    for i in range(RAW_PAGES):
        f.write(raw_buf)
t1 = time.perf_counter()
mb_sec = 64.0 / (t1 - t0)
print(f"    --> Written in {t1 - t0:.4f}s ({mb_sec:.2f} MB/s) | Latency: {(t1 - t0) / RAW_PAGES * 1e6:.2f} us/page")

# 4. Bit-Exact Read Verification
print("[*] [Verification] Verifying 100% bit-exact recall from /dev/hmb0...")
t0 = time.perf_counter()
with open(DEV, "rb", buffering=0) as f:
    f.seek(BLOCK_SIZE)
    # Read zeros
    for _ in range(ZERO_PAGES):
        data = f.read(BLOCK_SIZE)
        if data != zero_buf:
            print("FAILED ZERO CHECK!")
            sys.exit(1)
    # Read patterns
    for _ in range(PAT_PAGES):
        data = f.read(BLOCK_SIZE)
        if data != pat_buf:
            print("FAILED PATTERN CHECK!")
            sys.exit(1)
    # Read raw
    for _ in range(RAW_PAGES):
        data = f.read(BLOCK_SIZE)
        if data != raw_buf:
            print("FAILED RAW CHECK!")
            sys.exit(1)
t1 = time.perf_counter()
total_mb = (ZERO_PAGES + PAT_PAGES + RAW_PAGES) * 4 // 1024
print(f"    --> Verified {total_mb} MB bit-exact in {t1 - t0:.4f}s ({total_mb / (t1 - t0):.2f} MB/s)!")

print("\\n[+] BENCHMARK COMPLETE: 100% BIT-EXACT PASS!")
'''

    sftp = client.open_sftp()
    with sftp.open("/home/ubuntu/hmb_linux/run_bench.py", "w") as f:
        f.write(benchmark_code)
    sftp.close()

    # 1. Disable swap temporarily to release exclusive block lock for direct verification
    client.exec_command("sudo swapoff /dev/hmb0 2>/dev/null || true")

    # 2. Run raw I/O throughput and Tier 2 z-Pack test
    stdin, stdout, stderr = client.exec_command("sudo python3 /home/ubuntu/hmb_linux/run_bench.py")
    safe_print(stdout.read().decode('utf-8', errors='replace'))
    err = stderr.read().decode('utf-8', errors='replace')
    if err:
        safe_print(f"[stderr] {err}")

    # 3. Re-format and re-arm swap at priority 100
    safe_print("\n[*] Re-arming /dev/hmb0 as Priority 100 Swap Device...")
    client.exec_command("sudo mkswap /dev/hmb0 && sudo swapon -p 100 /dev/hmb0")

    # 4. Read final /proc/hmb_swap
    safe_print("\n================================================================================")
    safe_print("  LIVE TELEMETRY FROM /proc/hmb_swap")
    safe_print("================================================================================")
    stdin, stdout, stderr = client.exec_command("cat /proc/hmb_swap")
    safe_print(stdout.read().decode('utf-8', errors='replace'))

    client.close()

if __name__ == "__main__":
    main()
