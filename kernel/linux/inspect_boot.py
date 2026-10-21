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

    print("=== EFIBOOTMGR ===")
    stdin, stdout, stderr = c.exec_command("sudo efibootmgr -v")
    print(stdout.read().decode())

    print("=== CURRENT KERNEL & PROC ===")
    stdin, stdout, stderr = c.exec_command("uname -a; cat /proc/cmdline")
    print(stdout.read().decode())

    print("=== GRUB ENTRIES ===")
    stdin, stdout, stderr = c.exec_command("grep -E \"menuentry '\" /boot/grub/grub.cfg")
    print(stdout.read().decode())

    print("=== BOOT DIRECTORY ===")
    stdin, stdout, stderr = c.exec_command("ls -lh /boot")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
