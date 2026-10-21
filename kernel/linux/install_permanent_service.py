#!/usr/bin/env python3
"""
Install Haven Memory Bus (HMB) Swap as a Permanent System Service on Ubuntu
Target: 147.135.1.229
"""

import sys
import paramiko

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

def safe_print(text):
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace') + b'\n')
    sys.stdout.buffer.flush()

def exec_cmd(client, cmd, sudo=True):
    if sudo:
        cmd = f"sudo {cmd}"
    safe_print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        safe_print(out)
    if err and "password" not in err.lower() and "[sudo]" not in err.lower():
        safe_print(f"ERR: {err}")
    return stdout.channel.recv_exit_status(), out

def main():
    k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, pkey=k, timeout=10)
    safe_print("[*] SSH Connected to server.")

    # 1. Copy module to kernel drivers directory
    exec_cmd(client, "mkdir -p /lib/modules/7.0.0-38-generic/kernel/drivers/block/")
    exec_cmd(client, "cp /home/ubuntu/hmb_linux/hmb_swap.ko /lib/modules/7.0.0-38-generic/kernel/drivers/block/")
    exec_cmd(client, "depmod -a")

    # 2. Configure modprobe options (4GB HMB swap)
    exec_cmd(client, "sh -c 'echo \"options hmb_swap size_mb=4096 zpack_enable=1\" > /etc/modprobe.d/hmb_swap.conf'")
    exec_cmd(client, "sh -c 'echo hmb_swap > /etc/modules-load.d/hmb.conf'")

    # 3. Create systemd service
    service_def = """[Unit]
Description=Haven Memory Bus (HMB) High-Speed Swap Subsystem
After=local-fs.target
Before=swap.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/sbin/modprobe hmb_swap
ExecStart=/bin/sh -c 'mkswap /dev/hmb0 && swapon -p 100 /dev/hmb0'
ExecStop=/bin/sh -c 'swapoff /dev/hmb0 2>/dev/null || true'

[Install]
WantedBy=multi-user.target
"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/hmb-swap.service", "w") as f:
        f.write(service_def)
    sftp.close()

    exec_cmd(client, "mv /tmp/hmb-swap.service /etc/systemd/system/hmb-swap.service")
    exec_cmd(client, "systemctl daemon-reload")
    exec_cmd(client, "systemctl enable hmb-swap.service")

    # 4. Restart service to verify 4GB allocation
    safe_print("\n[*] Activating persistent 4GB HMB Swap Service...")
    exec_cmd(client, "swapoff /dev/hmb0 2>/dev/null || true")
    exec_cmd(client, "rmmod hmb_swap 2>/dev/null || true")
    exec_cmd(client, "systemctl restart hmb-swap.service")
    exec_cmd(client, "systemctl status hmb-swap.service --no-pager")

    # 5. Check live swap and telemetry
    safe_print("\n================================================================================")
    safe_print("  VERIFYING LIVE SWAP SUBSYSTEM")
    safe_print("================================================================================")
    exec_cmd(client, "swapon --show")
    exec_cmd(client, "cat /proc/hmb_swap")

    client.close()

if __name__ == "__main__":
    main()
