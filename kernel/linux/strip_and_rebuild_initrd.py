#!/usr/bin/env python3
import paramiko
import time

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    print("=== 1. Stripping unneeded debug symbols from /lib/modules/7.0.14-hmb ===")
    t0 = time.time()
    stdin, stdout, stderr = c.exec_command("sudo find /lib/modules/7.0.14-hmb/ -type f -name '*.ko' -print0 | sudo xargs -0 -n 100 -P 8 strip --strip-unneeded")
    stdout.channel.recv_exit_status()
    print(f"Stripping done in {time.time()-t0:.1f}s")

    print("=== 2. Checking size of /lib/modules/7.0.14-hmb ===")
    stdin, stdout, stderr = c.exec_command("du -sh /lib/modules/7.0.14-hmb")
    print(stdout.read().decode())

    print("=== 3. Regenerating initramfs for 7.0.14-hmb ===")
    t0 = time.time()
    stdin, stdout, stderr = c.exec_command("sudo update-initramfs -u -k 7.0.14-hmb")
    for line in iter(stdout.readline, ""):
        print(line.strip())
    stdout.channel.recv_exit_status()
    print(f"update-initramfs done in {time.time()-t0:.1f}s")

    print("=== 4. Checking /boot space and files ===")
    stdin, stdout, stderr = c.exec_command("df -h /boot; ls -lh /boot")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
