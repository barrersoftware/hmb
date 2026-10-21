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

    # 1. Sync updated files
    sftp = c.open_sftp()
    local_dir = r"C:\Users\admin\source\hmb\kernel\linux"
    with open(f"{local_dir}\\hmb_pagefile.h", "r", encoding="utf-8") as f:
        sftp.open("/home/ubuntu/linux-7.0.0/include/linux/hmb_pagefile.h", "w").write(f.read())
    with open(f"{local_dir}\\hmb_pagefile.c", "r", encoding="utf-8") as f:
        sftp.open("/home/ubuntu/linux-7.0.0/mm/hmb_pagefile.c", "w").write(f.read())
    sftp.close()
    print("[*] Uploaded updated hmb_pagefile.h and hmb_pagefile.c")

    def exec_stream(cmd):
        print(f">>> {cmd}")
        stdin, stdout, stderr = c.exec_command(cmd)
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line, end='', flush=True)
        rc = stdout.channel.recv_exit_status()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if err and '[sudo]' not in err.lower():
            print('ERR:', err)
        return rc

    exec_stream("cd /home/ubuntu/linux-7.0.0 && make -j8 mm/hmb_pagefile.o mm/page_io.o mm/swapfile.o")

    c.close()

if __name__ == "__main__":
    main()
