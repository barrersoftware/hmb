#!/usr/bin/env python3
import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    stdin, stdout, stderr = c.exec_command("uname -a")
    print("=== KERNEL ===\n" + stdout.read().decode('utf-8', 'replace'))

    stdin, stdout, stderr = c.exec_command("swapon --show")
    print("=== SWAP DEVICES ===\n" + stdout.read().decode('utf-8', 'replace'))

    stdin, stdout, stderr = c.exec_command("cat /proc/hmb_swap 2>/dev/null || echo 'No /proc/hmb_swap'")
    print("=== /proc/hmb_swap ===\n" + stdout.read().decode('utf-8', 'replace'))

    stdin, stdout, stderr = c.exec_command("cat /proc/hmb_pagefile 2>/dev/null || echo 'No /proc/hmb_pagefile'")
    print("=== /proc/hmb_pagefile ===\n" + stdout.read().decode('utf-8', 'replace'))

    c.close()

if __name__ == "__main__":
    main()
