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
    with sftp.open("/home/ubuntu/linux-7.0.0/mm/page_io.c", "r") as f:
        code = f.read().decode('utf-8')

    # 1. Header include
    if "linux/hmb_pagefile.h" not in code:
        code = "#include <linux/hmb_pagefile.h>\n" + code

    # 2. Hook store
    store_target = "\tif (zswap_store(folio)) {"
    store_repl = """#ifdef CONFIG_HMB_PAGEFILE
\tif (hmb_pagefile_store(folio)) {
\t\tgoto out_unlock;
\t}
#endif
\tif (zswap_store(folio)) {"""
    if "hmb_pagefile_store" not in code:
        assert store_target in code, "store_target not found!"
        code = code.replace(store_target, store_repl, 1)

    # 3. Hook load
    load_target = "\tif (zswap_load(folio) != -ENOENT)\n\t\tgoto finish;"
    load_repl = """#ifdef CONFIG_HMB_PAGEFILE
\tif (hmb_pagefile_load(folio)) {
\t\tfolio_unlock(folio);
\t\tgoto finish;
\t}
#endif
\tif (zswap_load(folio) != -ENOENT)\n\t\tgoto finish;"""
    if "hmb_pagefile_load" not in code:
        assert load_target in code, "load_target not found!"
        code = code.replace(load_target, load_repl, 1)

    with sftp.open("/home/ubuntu/linux-7.0.0/mm/page_io.c", "w") as f:
        f.write(code.encode('utf-8'))
    sftp.close()

    print("[*] Successfully patched mm/page_io.c!")
    stdin, stdout, stderr = c.exec_command("grep -nC 4 'hmb_pagefile' /home/ubuntu/linux-7.0.0/mm/page_io.c")
    print(stdout.read().decode())

    c.close()

if __name__ == "__main__":
    main()
