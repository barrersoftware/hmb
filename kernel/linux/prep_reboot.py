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

    # 1. Update /etc/default/grub with panic=10 if not present
    cmd = """
if ! grep -q 'panic=10' /etc/default/grub; then
    sudo sed -i 's/console=ttyS0,115200n8/console=ttyS0,115200n8 panic=10/' /etc/default/grub
    sudo update-grub
fi
"""
    stdin, stdout, stderr = c.exec_command(cmd)
    stdout.channel.recv_exit_status()

    stdin, stdout, stderr = c.exec_command("cat /etc/default/grub; grep 'linux.*7.0.14-hmb' /boot/grub/grub.cfg | head -n 1")
    print("=== Configured Boot Command ===")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
