# Haven Memory Bus (HMB) Linux Swap Driver Makefile
# Compatible with Linux Kernel 6.x and 7.x Kbuild

obj-m += hmb_swap.o

KDIR ?= /mnt/d/linux-7.3
PWD := $(shell pwd)

default:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
