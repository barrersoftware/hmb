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

    stdin, stdout, stderr = c.exec_command("grep -E 'MODULES=|COMPRESS=' /etc/initramfs-tools/initramfs.conf")
    print("=== CONF ===")
    print(stdout.read().decode())

    stdin, stdout, stderr = c.exec_command("file /boot/initrd.img-7.0.0-38-generic /boot/initrd.img-7.0.14-hmb")
    print("=== FILE TYPES ===")
    print(stdout.read().decode())

    stdin, stdout, stderr = c.exec_command("ls -lh /boot")
    print("=== BOOT ===")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
