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

    sftp = c.open_sftp()
    with sftp.open("/home/ubuntu/linux-7.0.0/mm/swapfile.c", "r") as f:
        code = f.read().decode('utf-8')

    # 1. Header include
    if "linux/hmb_pagefile.h" not in code:
        code = "#include <linux/hmb_pagefile.h>\n" + code

    # 2. Hook swap invalidation
    target = "\t\tzswap_invalidate(swp_entry(si->type, offset + i));"
    repl = """\t\tzswap_invalidate(swp_entry(si->type, offset + i));
#ifdef CONFIG_HMB_PAGEFILE
\t\thmb_pagefile_free(swp_entry(si->type, offset + i));
#endif"""
    if "hmb_pagefile_free" not in code:
        assert target in code, "target not found!"
        code = code.replace(target, repl, 1)

    with sftp.open("/home/ubuntu/linux-7.0.0/mm/swapfile.c", "w") as f:
        f.write(code.encode('utf-8'))
    sftp.close()

    print("[*] Successfully patched mm/swapfile.c!")
    stdin, stdout, stderr = c.exec_command("grep -nC 4 'hmb_pagefile' /home/ubuntu/linux-7.0.0/mm/swapfile.c")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
