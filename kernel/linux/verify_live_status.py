#!/usr/bin/env python3
import sys
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, USER, pkey=k, timeout=10)

    cmds = [
        ("1. Running Linux Kernel Version", "uname -a"),
        ("2. Loaded Kernel Modules (lsmod | grep hmb)", "lsmod | grep hmb"),
        ("3. Kernel Module File in Driver Directory", "ls -la /lib/modules/7.0.0-38-generic/kernel/drivers/block/hmb_swap.ko"),
        ("4. Module Info (modinfo hmb_swap)", "modinfo hmb_swap"),
        ("5. Active Swap Partitions & Priority (swapon --show)", "swapon --show"),
        ("6. Block Device Node in /dev (ls -la /dev/hmb0)", "ls -la /dev/hmb0"),
        ("7. Systemd Service Status (systemctl status hmb-swap.service)", "systemctl status hmb-swap.service --no-pager"),
        ("8. Boot Autoload Configuration", "cat /etc/modules-load.d/hmb.conf && cat /etc/modprobe.d/hmb_swap.conf"),
        ("9. Live Kernel Telemetry (/proc/hmb_swap)", "cat /proc/hmb_swap")
    ]

    for title, cmd in cmds:
        print(f"=== {title} ===")
        stdin, stdout, stderr = c.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        if out:
            print(out)
        print()

    c.close()

if __name__ == "__main__":
    main()
