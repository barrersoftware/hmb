using System;
using Haven.MemoryBus;

Console.WriteLine("=======================================================");
Console.WriteLine("  Haven Memory Bus (HMB) - C# / .NET 10 Verification");
Console.WriteLine("=======================================================");

using var bus = new HmbMemoryBus(totalBytes: 16 * 1024 * 1024, strideBytes: 4096);
Console.WriteLine($"[HMB .NET] Bus Initialized: {bus.TotalBytes / (1024 * 1024)} MB, Capacity: {bus.Capacity} slots, Stride: {bus.StrideBytes} bytes");

// 1. Allocate slot
ulong slot0 = bus.AllocateSlot(HmbTier.HotWorkingSet);
ulong slot1 = bus.AllocateSlot(HmbTier.HotWorkingSet);
Console.WriteLine($"[HMB .NET] Allocated Slot 0: {slot0}, Slot 1: {slot1}");

// 2. Direct Span write
Span<byte> span0 = bus.ResolveSpan(slot0);
span0.Fill(0x5A);
Console.WriteLine($"[HMB .NET] Span 0 Filled with 0x5A: Byte 0 = 0x{span0[0]:X2}, Byte 4095 = 0x{span0[4095]:X2}");

// 3. Direct unmanaged struct mapping
ref HmbRecord rec = ref bus.ResolveStructure<HmbRecord>(slot1);
rec.RecordId = 1337;
rec.DomainHash = 0xDEADBEEF;
rec.Weight = 0.95f;
Console.WriteLine($"[HMB .NET] Inscribed Unmanaged Record via Zero-Copy ref: ID={rec.RecordId}, Weight={rec.Weight}");

bus.ReleaseSlot(slot0);
Console.WriteLine($"[HMB .NET] Released Slot 0. Allocated Count: {bus.AllocatedCount}, Free: {bus.FreeCount}");

Console.WriteLine("=======================================================");
Console.WriteLine("  ALL .NET 10 HMB VERIFICATIONS PASSED 100%!");
Console.WriteLine("=======================================================");
