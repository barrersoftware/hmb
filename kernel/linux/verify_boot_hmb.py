#!/usr/bin/env python3
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    print("=== 1. UNAME ===")
    stdin, stdout, stderr = c.exec_command("uname -a")
    print(stdout.read().decode())

    print("=== 2. DMESG HMB LOGS ===")
    stdin, stdout, stderr = c.exec_command("sudo dmesg | grep -iE 'hmb|haven|pagefile'")
    print(stdout.read().decode())

    print("=== 3. /proc/hmb_pagefile ===")
    stdin, stdout, stderr = c.exec_command("cat /proc/hmb_pagefile")
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out if out else f"ERR: {err}")

    print("=== 4. /proc/hmb_swap ===")
    stdin, stdout, stderr = c.exec_command("cat /proc/hmb_swap")
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out if out else f"ERR: {err}")

    print("=== 5. Systemd hmb-swap status ===")
    stdin, stdout, stderr = c.exec_command("systemctl status hmb-swap.service --no-pager")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
