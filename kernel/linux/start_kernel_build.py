#!/usr/bin/env python3
"""
Start Background Compilation of Linux 7.0.0 with In-Tree HMB
Target: 147.135.1.229 (/home/ubuntu/linux-7.0.0)
"""

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

    # 1. Clean up trusted keys so Ubuntu signing certs don't cause build stops
    cmds = [
        "cd /home/ubuntu/linux-7.0.0 && scripts/config --set-str SYSTEM_TRUSTED_KEYS ''",
        "cd /home/ubuntu/linux-7.0.0 && scripts/config --set-str SYSTEM_REVOCATION_KEYS ''",
        "cd /home/ubuntu/linux-7.0.0 && scripts/config --set-str LOCALVERSION '-hmb'",
        "cd /home/ubuntu/linux-7.0.0 && scripts/config --enable CONFIG_HMB_PAGEFILE",
        "cd /home/ubuntu/linux-7.0.0 && make olddefconfig"
    ]
    for cmd in cmds:
        stdin, stdout, stderr = c.exec_command(cmd)
        stdout.channel.recv_exit_status()

    # 2. Verify config
    stdin, stdout, stderr = c.exec_command("grep -E 'CONFIG_HMB_PAGEFILE|CONFIG_LOCALVERSION' /home/ubuntu/linux-7.0.0/.config")
    print("[*] Configured Parameters:\n" + stdout.read().decode())

    # 3. Launch background compilation with nohup
    build_cmd = "cd /home/ubuntu/linux-7.0.0 && nohup make -j8 bzImage modules > /home/ubuntu/build_hmb.log 2>&1 &"
    print(f"[*] Launching background build: {build_cmd}")
    stdin, stdout, stderr = c.exec_command(build_cmd)
    stdout.channel.recv_exit_status()

    # 4. Check that build process is running
    import time
    time.sleep(2)
    stdin, stdout, stderr = c.exec_command("ps aux | grep -E 'make.*bzImage|gcc|cc1' | grep -v grep")
    print("[*] Running Build Processes:\n" + stdout.read().decode())

    stdin, stdout, stderr = c.exec_command("tail -n 15 /home/ubuntu/build_hmb.log")
    print("[*] Initial Log Output:\n" + stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
