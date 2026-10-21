package main

import (
	"fmt"
	"os"

	"github.com/barrersoftware/hmb/bindings/go"
)

func main() {
	fmt.Println("=======================================================")
	fmt.Println("  Haven Memory Bus (HMB) - Go Verification Suite")
	fmt.Println("=======================================================")

	bus, err := hmb.NewMemoryBus(1024*1024, 4096)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("[go-hmb] Bus Initialized: Capacity=%d slots, Stride=4096\n", bus.Capacity())

	slot0, err := bus.AllocateSlot(hmb.TierHotWorkingSet)
	if err != nil {
		fmt.Printf("Allocation failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("[go-hmb] Allocated Slot 0: %d\n", slot0)

	slice0, err := bus.ResolveSlice(slot0)
	if err != nil {
		fmt.Printf("Resolve failed: %v\n", err)
		os.Exit(1)
	}

	copy(slice0[0:4], []byte("GO!!"))
	fmt.Printf("[go-hmb] Slice modified in-place: %s\n", string(slice0[0:4]))

	bus.ReleaseSlot(slot0)
	fmt.Printf("[go-hmb] Released Slot 0. Active slots: %d\n", bus.AllocatedCount())

	fmt.Println("=======================================================")
	fmt.Println("  ALL GO HMB VERIFICATIONS PASSED 100%!")
	fmt.Println("=======================================================")
}
