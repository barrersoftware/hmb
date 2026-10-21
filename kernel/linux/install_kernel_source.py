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

    def exec_stream(cmd):
        print(f">>> sudo {cmd}")
        stdin, stdout, stderr = c.exec_command(f"sudo {cmd}")
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

    exec_stream("apt-get install -y linux-source-7.0.0")
    exec_stream("ls -lh /usr/src/")
    c.close()

if __name__ == "__main__":
    main()
