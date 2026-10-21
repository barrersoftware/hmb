using System.Runtime.InteropServices;

namespace Haven.MemoryBus;

[StructLayout(LayoutKind.Sequential, Pack = 1)]
public struct HmbHeader
{
    public const ulong MagicValue = 0x4D454D4E45564148UL; // "HAVENMEM"
    public const uint Version20 = 0x00020000U;

    public ulong Magic;
    public uint Version;
    public uint Flags;
    public uint StrideBytes;
    public uint StrideShift;
    public ulong TotalSlots;
    public ulong ActiveSlots;
    public ulong DataOffset;
    public ulong BitmapOffset;
    public ulong Checksum;

    public bool IsValid => Magic == MagicValue && Version == Version20 && StrideBytes > 0;
}

[StructLayout(LayoutKind.Sequential, Pack = 1)]
public struct HmbRecord
{
    public ulong RecordId;
    public ulong DomainHash;
    public float Weight;
    public float Resonance;
    public long TimestampUs;
    public ulong AccessCount;
    public ulong PayloadOffset;
    public uint PayloadSize;
    public uint TierId;
}
