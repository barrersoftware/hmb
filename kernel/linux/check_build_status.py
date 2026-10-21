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

    # 1. Compiler processes
    stdin, stdout, stderr = c.exec_command("ps -eo pid,user,%cpu,%mem,comm | grep -E 'make|gcc|cc1|ld' | grep -v grep")
    print("=== Active Compiler Processes ===")
    procs = stdout.read().decode().strip()
    print(procs if procs else "No active compiler processes (Build finished or stopped)")
    print()

    # 2. Recent log
    print("=== Last 30 Lines of Build Log ===")
    stdin, stdout, stderr = c.exec_command("tail -n 30 /home/ubuntu/build_hmb.log")
    print(stdout.read().decode())

    # 3. Kernel image check
    print("=== Kernel Binary Targets ===")
    stdin, stdout, stderr = c.exec_command("ls -lh /home/ubuntu/linux-7.0.0/vmlinux /home/ubuntu/linux-7.0.0/arch/x86/boot/bzImage 2>/dev/null || echo 'Kernel images not yet linked'")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
