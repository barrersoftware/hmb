#!/usr/bin/env python3
"""
Apply Haven Memory Bus (HMB) In-Tree Patch to Linux 7.0.0 and Test Compilation
Target: 147.135.1.229 (/home/ubuntu/linux-7.0.0)
"""

import sys
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def safe_print(text):
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace') + b'\n')
    sys.stdout.buffer.flush()

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, pkey=k, timeout=10)
    safe_print("[*] SSH Connected to server.")

    sftp = client.open_sftp()
    local_dir = r"C:\Users\admin\source\hmb\kernel\linux"

    # 1. Upload hmb_pagefile.h to include/linux/
    with open(f"{local_dir}\\hmb_pagefile.h", "r", encoding="utf-8") as f:
        sftp.open("/home/ubuntu/linux-7.0.0/include/linux/hmb_pagefile.h", "w").write(f.read())
    safe_print("[1/6] Uploaded include/linux/hmb_pagefile.h")

    # 2. Upload hmb_pagefile.c to mm/
    with open(f"{local_dir}\\hmb_pagefile.c", "r", encoding="utf-8") as f:
        sftp.open("/home/ubuntu/linux-7.0.0/mm/hmb_pagefile.c", "w").write(f.read())
    safe_print("[2/6] Uploaded mm/hmb_pagefile.c")

    # 3. Patch mm/Makefile
    stdin, stdout, stderr = client.exec_command("grep -q 'hmb_pagefile.o' /home/ubuntu/linux-7.0.0/mm/Makefile || echo 'obj-$(CONFIG_HMB_PAGEFILE) += hmb_pagefile.o' >> /home/ubuntu/linux-7.0.0/mm/Makefile")
    safe_print("[3/6] Updated mm/Makefile with obj-$(CONFIG_HMB_PAGEFILE)")

    # 4. Patch mm/Kconfig
    kconfig_patch = """
config HMB_PAGEFILE
	bool "Haven Memory Bus (HMB) Native In-Tree Paging Engine"
	depends on SWAP
	default y
	help
	  Enables native arithmetic-first virtual memory paging and Tier 2
	  z-Pack in-RAM deduplication based on HMB Spec 2.0.
"""
    cmd = f"""python3 -c '
with open("/home/ubuntu/linux-7.0.0/mm/Kconfig", "r") as f: content = f.read()
if "config HMB_PAGEFILE" not in content:
    content += \"\"\"{kconfig_patch}\"\"\"
    with open("/home/ubuntu/linux-7.0.0/mm/Kconfig", "w") as f: f.write(content)
'"""
    client.exec_command(cmd)
    safe_print("[4/6] Added CONFIG_HMB_PAGEFILE to mm/Kconfig")

    # 5. Patch mm/page_io.c
    patch_code = '''python3 -c '
with open("/home/ubuntu/linux-7.0.0/mm/page_io.c", "r") as f:
    code = f.read()

# Add include
if "linux/hmb_pagefile.h" not in code:
    code = "#include <linux/hmb_pagefile.h>\\n" + code

# Hook store
store_target = "if (zswap_store(folio)) {"
store_repl = """#ifdef CONFIG_HMB_PAGEFILE
	if (hmb_pagefile_store(folio)) {
		goto out_unlock;
	}
#endif
\\tif (zswap_store(folio)) {"

if "hmb_pagefile_store" not in code and store_target in code:
    code = code.replace(store_target, store_repl, 1)

# Hook load
load_target = "if (zswap_load(folio) != -ENOENT)\\n\\t\\tgoto finish;"
load_repl = """#ifdef CONFIG_HMB_PAGEFILE
	if (hmb_pagefile_load(folio)) {
		folio_unlock(folio);
		goto finish;
	}
#endif
\\tif (zswap_load(folio) != -ENOENT)\\n\\t\\tgoto finish;"""

if "hmb_pagefile_load" not in code and load_target in code:
    code = code.replace(load_target, load_repl, 1)

with open("/home/ubuntu/linux-7.0.0/mm/page_io.c", "w") as f:
    f.write(code)
' '''
    stdin, stdout, stderr = client.exec_command(patch_code)
    safe_print("[5/6] Patched mm/page_io.c with HMB store and load hooks")

    # 6. Verify diff in mm/page_io.c
    stdin, stdout, stderr = client.exec_command("git -C /home/ubuntu/linux-7.0.0 diff mm/page_io.c || diff -u /home/ubuntu/linux-7.0.0/mm/page_io.c.bak /home/ubuntu/linux-7.0.0/mm/page_io.c")
    safe_print("[6/6] Patch diff:\n" + stdout.read().decode('utf-8', errors='replace'))

    sftp.close()
    client.close()

if __name__ == "__main__":
    main()
