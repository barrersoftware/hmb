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

    print("=== 1. Archiving old kernel 34 to /root/old_boot_34 ===")
    stdin, stdout, stderr = c.exec_command("sudo mkdir -p /root/old_boot_34 && sudo mv /boot/*-7.0.0-34* /root/old_boot_34/ 2>/dev/null; df -h /boot")
    print(stdout.read().decode())

    print("=== 2. Generating fresh initrd for 7.0.14-hmb into /tmp first ===")
    t0 = time.time()
    stdin, stdout, stderr = c.exec_command("sudo mkinitramfs -o /tmp/initrd.img-7.0.14-hmb 7.0.14-hmb && ls -lh /tmp/initrd.img-7.0.14-hmb")
    print(stdout.read().decode())
    print(stderr.read().decode())
    print(f"Done in {time.time()-t0:.1f}s")

    print("=== 3. If valid, move into /boot ===")
    stdin, stdout, stderr = c.exec_command("sudo mv /tmp/initrd.img-7.0.14-hmb /boot/initrd.img-7.0.14-hmb && sudo update-grub; df -h /boot")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
