using System.Numerics;
using System.Runtime.InteropServices;

namespace Haven.MemoryBus;

public sealed unsafe class HmbBitmask
{
    private ulong* _words;
    private readonly ulong _totalSlots;
    private readonly ulong _wordCount;
    private readonly bool _ownsMemory;

    public ulong TotalSlots => _totalSlots;
    public ulong WordCount => _wordCount;

    public HmbBitmask(ulong totalSlots)
    {
        _totalSlots = totalSlots;
        _wordCount = (totalSlots + 63) / 64;
        _words = (ulong*)NativeMemory.AllocZeroed((nuint)_wordCount, sizeof(ulong));
        _ownsMemory = true;
    }

    public HmbBitmask(ulong* externalWords, ulong totalSlots)
    {
        _words = externalWords;
        _totalSlots = totalSlots;
        _wordCount = (totalSlots + 63) / 64;
        _ownsMemory = false;
    }

    ~HmbBitmask()
    {
        if (_ownsMemory && _words != null)
        {
            NativeMemory.Free(_words);
            _words = null;
        }
    }

    public ulong AllocateFirstFree()
    {
        if (_words == null) return ulong.MaxValue;

        for (ulong w = 0; w < _wordCount; w++)
        {
            ref ulong wordRef = ref _words[w];
            ulong current = Volatile.Read(ref wordRef);

            while (current != ulong.MaxValue)
            {
                ulong inverted = ~current;
                int bit = BitOperations.TrailingZeroCount(inverted);
                ulong targetIdx = (w * 64) + (ulong)bit;
                if (targetIdx >= _totalSlots) return ulong.MaxValue;

                ulong updated = current | (1UL << bit);
                ulong actual = Interlocked.CompareExchange(ref wordRef, updated, current);
                if (actual == current)
                {
                    return targetIdx;
                }
                current = actual;
            }
        }
        return ulong.MaxValue;
    }

    public void Release(ulong slotIndex)
    {
        if (_words == null || slotIndex >= _totalSlots) return;

        ulong wordIdx = slotIndex / 64;
        int bitIdx = (int)(slotIndex % 64);
        ref ulong wordRef = ref _words[wordIdx];

        ulong mask = ~(1UL << bitIdx);
        ulong current = Volatile.Read(ref wordRef);
        while (true)
        {
            ulong updated = current & mask;
            ulong actual = Interlocked.CompareExchange(ref wordRef, updated, current);
            if (actual == current) break;
            current = actual;
        }
    }

    public bool IsAllocated(ulong slotIndex)
    {
        if (_words == null || slotIndex >= _totalSlots) return false;
        ulong wordIdx = slotIndex / 64;
        int bitIdx = (int)(slotIndex % 64);
        return (_words[wordIdx] & (1UL << bitIdx)) != 0;
    }

    public ulong CountAllocated()
    {
        if (_words == null) return 0;
        ulong total = 0;
        for (ulong w = 0; w < _wordCount; w++)
        {
            total += (ulong)BitOperations.PopCount(_words[w]);
        }
        return total;
    }
}
