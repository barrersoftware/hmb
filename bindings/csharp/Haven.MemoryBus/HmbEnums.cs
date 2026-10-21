namespace Haven.MemoryBus;

public enum HmbTier : uint
{
    HotWorkingSet = 0x00,
    DirtyHeap = 0x01,
    ZSwapCompressed = 0x02,
    CleanImmutable = 0x03
}
