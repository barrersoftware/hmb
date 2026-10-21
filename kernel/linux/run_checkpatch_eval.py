#!/usr/bin/env python3
import sys
import paramiko

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    # 1. Upload clean file
    sftp = c.open_sftp()
    sftp.put(r"C:\Users\admin\source\hmb\kernel\linux\hmb_pagefile.c", "/home/ubuntu/linux-7.0.0/mm/hmb_pagefile.c")
    sftp.close()

    # 2. Run checkpatch.pl
    stdin, stdout, stderr = c.exec_command("cd /home/ubuntu/linux-7.0.0 && perl scripts/checkpatch.pl --no-tree -f mm/hmb_pagefile.c")
    print(stdout.read().decode('utf-8', 'replace'))
    print(stderr.read().decode('utf-8', 'replace'))

    c.close()

if __name__ == "__main__":
    main()
