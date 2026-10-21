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

    def exec_stream(cmd, sudo=False):
        full_cmd = f"sudo {cmd}" if sudo else cmd
        print(f">>> {full_cmd}")
        stdin, stdout, stderr = c.exec_command(full_cmd)
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

    exec_stream("apt-get install -y lbzip2", sudo=True)
    exec_stream("mkdir -p /home/ubuntu/linux-7.0.0 && tar --use-compress-program=lbzip2 -xf /usr/src/linux-source-7.0.0/linux-source-7.0.0.tar.bz2 -C /home/ubuntu/linux-7.0.0 --strip-components=1")
    exec_stream("ls -la /home/ubuntu/linux-7.0.0 | head -n 20")
    c.close()

if __name__ == "__main__":
    main()
