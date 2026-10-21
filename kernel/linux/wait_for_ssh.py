#!/usr/bin/env python3
import time
import socket
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    print(f"Waiting for {HOST}:22 to come back online...")
    t0 = time.time()
    online = False
    
    # Wait for server to drop first if it's still shutting down
    time.sleep(5)
    
    while time.time() - t0 < 180:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((HOST, 22))
            s.close()
            online = True
            break
        except Exception:
            time.sleep(2)

    if not online:
        print("Timeout waiting for port 22.")
        return 1

    print(f"Port 22 is OPEN after {time.time()-t0:.1f}s! Authenticating...")
    time.sleep(2)

    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    print("\n================ BARE-METAL BOOT VERIFICATION ================")
    stdin, stdout, stderr = c.exec_command("uname -a")
    print("UNAME:", stdout.read().decode().strip())

    stdin, stdout, stderr = c.exec_command("cat /proc/cmdline")
    print("CMDLINE:", stdout.read().decode().strip())

    stdin, stdout, stderr = c.exec_command("dmesg | grep -i hmb || echo 'No HMB in dmesg'")
    print("DMESG HMB:\n", stdout.read().decode().strip())

    stdin, stdout, stderr = c.exec_command("swapon --show; cat /proc/swaps")
    print("SWAP TOPOLOGY:\n", stdout.read().decode().strip())

    c.close()
    return 0

if __name__ == "__main__":
    main()
