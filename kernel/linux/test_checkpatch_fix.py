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

    # Check if kzalloc_obj exists in slab.h
    stdin, stdout, stderr = c.exec_command("grep -rn 'kzalloc_obj' /home/ubuntu/linux-7.0.0/include/linux/slab.h")
    res = stdout.read().decode().strip()
    print("kzalloc_obj in slab.h:", res if res else "Not found")

    c.close()

if __name__ == "__main__":
    main()
