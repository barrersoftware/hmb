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

    stdin, stdout, stderr = c.exec_command("sed -n '270,285p' /home/ubuntu/linux-7.0.0/mm/page_io.c")
    print("LINES 270-285:\n" + repr(stdout.read().decode()))

    stdin, stdout, stderr = c.exec_command("sed -n '630,645p' /home/ubuntu/linux-7.0.0/mm/page_io.c")
    print("LINES 630-645:\n" + repr(stdout.read().decode()))

    stdin, stdout, stderr = c.exec_command("grep -n 'CONFIG_HMB_PAGEFILE' /home/ubuntu/linux-7.0.0/mm/Makefile")
    print(stdout.read().decode())

    stdin, stdout, stderr = c.exec_command("grep -n 'HMB_PAGEFILE' /home/ubuntu/linux-7.0.0/mm/Kconfig")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
