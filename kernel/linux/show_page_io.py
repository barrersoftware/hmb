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

    print("=== STORE PATH (lines 265-300) ===")
    stdin, stdout, stderr = c.exec_command("sed -n '265,300p' /home/ubuntu/linux-7.0.0/mm/page_io.c")
    print(stdout.read().decode())

    print("=== LOAD PATH (lines 625-660) ===")
    stdin, stdout, stderr = c.exec_command("sed -n '625,660p' /home/ubuntu/linux-7.0.0/mm/page_io.c")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
