import paramiko
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "147.135.1.229"
USER = "ubuntu"
KEY_PATH = r"C:\Users\admin\.ssh\micant_ci_key"

k = paramiko.RSAKey.from_private_key_file(KEY_PATH)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, 22, USER, pkey=k, timeout=10)

setup_cmd = r"""
cat << 'EOF' > /tmp/madvise_test.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>

#ifndef MADV_PAGEOUT
#define MADV_PAGEOUT 21
#endif

#define ZERO_PAGES    4096 // 16 MB
#define PATTERN_PAGES 4096 // 16 MB
#define TOTAL_PAGES   (ZERO_PAGES + PATTERN_PAGES) // 32 MB

int main() {
    printf("[MADV] Allocating 32MB anonymous memory (16MB zeros + 16MB pattern 0x7E)...\n");
    size_t sz = (size_t)TOTAL_PAGES * 4096;
    char *buf = (char *)mmap(NULL, sz, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buf == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    /* Dirty zero pages so the kernel doesn't elide them */
    for (size_t i = 0; i < (size_t)ZERO_PAGES * 4096; i += 4096) {
        buf[i] = 1;      // dirty the page
        buf[i] = 0;      // restore to 0
    }

    /* Fill second 16MB with repeating pattern */
    memset(buf + ((size_t)ZERO_PAGES * 4096), 0x7E, (size_t)PATTERN_PAGES * 4096);

    printf("[MADV] Triggering MADV_PAGEOUT on full 32MB plane...\n");
    if (madvise(buf, sz, MADV_PAGEOUT) != 0) {
        perror("madvise MADV_PAGEOUT");
    } else {
        printf("[MADV] MADV_PAGEOUT completed.\n");
    }

    usleep(500000);

    printf("\n=== METRICS AFTER 32MB EVICTION (TIER 2 ZERO + PATTERN DEDUP) ===\n");
    system("cat /proc/hmb_pagefile");

    printf("\n[MADV] Reading back full 32MB to trigger page fault recovery...\n");
    long zero_sum = 0;
    for (size_t i = 0; i < (size_t)ZERO_PAGES * 4096; i += 4096) {
        zero_sum += (unsigned char)buf[i];
    }
    long pattern_sum = 0;
    for (size_t i = (size_t)ZERO_PAGES * 4096; i < sz; i += 4096) {
        pattern_sum += (unsigned char)buf[i];
    }
    printf("[MADV] Zero partition checksum: %ld (expected: 0)\n", zero_sum);
    printf("[MADV] Pattern partition checksum: %ld (expected: %ld)\n", pattern_sum, (long)PATTERN_PAGES * 0x7E);

    printf("\n=== METRICS AFTER 32MB RECOVERY (PAGE IN FAULTS) ===\n");
    system("cat /proc/hmb_pagefile");

    munmap(buf, sz);
    return 0;
}
EOF

gcc -static -O2 /tmp/madvise_test.c -o /tmp/madvise_test
cp /tmp/madvise_test /tmp/initramfs_hmb/bin/madvise_test

cd /tmp/initramfs_hmb && find . | cpio -o -H newc | gzip -9 > /home/ubuntu/hmb-aosp-initrd.img
ls -lh /home/ubuntu/hmb-aosp-initrd.img
"""

stdin, stdout, stderr = c.exec_command(setup_cmd)
print("=== Initramfs Setup ===")
print(stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err:
    print("STDERR:", err)

print("=== Booting Android 15 Kernel in QEMU KVM ===")
qemu_cmd = (
    "timeout 30s qemu-system-x86_64 -enable-kvm -cpu host -m 4G -smp 4 "
    "-drive file=/home/ubuntu/swap.img,format=raw,if=virtio "
    "-kernel /home/ubuntu/aosp-kernel-6.6/arch/x86/boot/bzImage "
    "-initrd /home/ubuntu/hmb-aosp-initrd.img "
    "-append 'console=ttyS0 earlycon=uart8250,io,0x3f8 earlyprintk=serial,ttyS0,115200 panic=1' "
    "-nographic -no-reboot"
)

stdin, stdout, stderr = c.exec_command(qemu_cmd)
boot_out = stdout.read().decode('utf-8', 'replace')
print("=== Output ===")
print(boot_out)

c.close()
