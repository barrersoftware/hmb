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

    print("=== Syncing filesystems and issuing reboot ===")
    stdin, stdout, stderr = c.exec_command("sudo sync && sudo nohup reboot >/dev/null 2>&1 &")
    c.close()
    print("Reboot command dispatched successfully.")

if __name__ == "__main__":
    main()
