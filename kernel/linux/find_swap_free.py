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

    stdin, stdout, stderr = c.exec_command("sed -n '1265,1285p' /home/ubuntu/linux-7.0.0/mm/swapfile.c")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
