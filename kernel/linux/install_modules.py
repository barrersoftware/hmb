#!/usr/bin/env python3
import sys
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

    print("=== Running sudo make -j8 modules_install ===")
    t0 = time.time()
    stdin, stdout, stderr = c.exec_command("cd /home/ubuntu/linux-7.0.0 && sudo make -j8 modules_install", get_pty=True)
    # Stream output
    for line in iter(stdout.readline, ""):
        if "INSTALL" in line or "DEPMOD" in line or "error" in line.lower():
            print(line.strip())
    exit_status = stdout.channel.recv_exit_status()
    print(f"modules_install exit code: {exit_status} in {time.time()-t0:.1f}s")

    c.close()

if __name__ == "__main__":
    main()
