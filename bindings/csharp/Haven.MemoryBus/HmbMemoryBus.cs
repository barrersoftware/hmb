using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace Haven.MemoryBus;

public sealed unsafe class HmbMemoryBus : IDisposable
{
    private byte* _baseMemory;
    private readonly ulong _totalBytes;
    private readonly uint _strideBytes;
    private readonly uint _strideShift;
    private readonly ulong _capacity;
    private readonly HmbBitmask _bitmask;
    private readonly bool _ownsMemory;
    private bool _disposed;

    public ulong TotalBytes => _totalBytes;
    public uint StrideBytes => _strideBytes;
    public uint StrideShift => _strideShift;
    public ulong Capacity => _capacity;
    public ulong AllocatedCount => _bitmask.CountAllocated();
    public ulong FreeCount => _capacity > AllocatedCount ? _capacity - AllocatedCount : 0;

    public HmbMemoryBus(ulong totalBytes, uint strideBytes = 4096)
    {
        if (strideBytes < 64 || (strideBytes & (strideBytes - 1)) != 0)
            throw new ArgumentException("Stride must be a power of 2 >= 64", nameof(strideBytes));

        _totalBytes = totalBytes;
        _strideBytes = strideBytes;
        _strideShift = (uint)System.Numerics.BitOperations.TrailingZeroCount(strideBytes);
        _capacity = totalBytes >> (int)_strideShift;

        _baseMemory = (byte*)NativeMemory.AllocZeroed((nuint)totalBytes);
        _ownsMemory = true;
        _bitmask = new HmbBitmask(_capacity);
    }

    public HmbMemoryBus(byte* externalBase, ulong totalBytes, uint strideBytes = 4096, ulong* externalBitmap = null)
    {
        if (strideBytes < 64 || (strideBytes & (strideBytes - 1)) != 0)
            throw new ArgumentException("Stride must be a power of 2 >= 64", nameof(strideBytes));

        _baseMemory = externalBase;
        _totalBytes = totalBytes;
        _strideBytes = strideBytes;
        _strideShift = (uint)System.Numerics.BitOperations.TrailingZeroCount(strideBytes);
        _capacity = totalBytes >> (int)_strideShift;
        _ownsMemory = false;

        _bitmask = externalBitmap != null
            ? new HmbBitmask(externalBitmap, _capacity)
            : new HmbBitmask(_capacity);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ulong AllocateSlot(HmbTier tier = HmbTier.HotWorkingSet)
    {
        return _bitmask.AllocateFirstFree();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public void ReleaseSlot(ulong slotIndex)
    {
        _bitmask.Release(slotIndex);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public byte* ResolvePointer(ulong slotIndex)
    {
        if (slotIndex >= _capacity || _baseMemory == null) return null;
        return _baseMemory + (slotIndex << (int)_strideShift);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public Span<byte> ResolveSpan(ulong slotIndex)
    {
        byte* ptr = ResolvePointer(slotIndex);
        if (ptr == null) return Span<byte>.Empty;
        return new Span<byte>(ptr, (int)_strideBytes);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ref T ResolveStructure<T>(ulong slotIndex) where T : unmanaged
    {
        byte* ptr = ResolvePointer(slotIndex);
        if (ptr == null || sizeof(T) > _strideBytes)
            throw new InvalidOperationException("Invalid slot or type exceeds stride size");
        return ref Unsafe.AsRef<T>(ptr);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public ulong GetOffset(ulong slotIndex)
    {
        return slotIndex << (int)_strideShift;
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            if (_ownsMemory && _baseMemory != null)
            {
                NativeMemory.Free(_baseMemory);
                _baseMemory = null;
            }
            _disposed = true;
        }
    }
}
