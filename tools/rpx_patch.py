#!/usr/bin/env python3
"""Patches big-endian 32-bit values in a Wii U RPX (e.g. Smash 4's cross_f.rpx).

Usage:
  python3 tools/rpx_patch.py IN.rpx OUT.rpx ADDRESS=VALUE [ADDRESS=VALUE ...]
  python3 tools/rpx_patch.py IN.rpx --read ADDRESS [ADDRESS ...]

Example (Kirby's starmissile max count, 1 -> 3):
  python3 tools/rpx_patch.py cross_f.rpx cross_f_patched.rpx 0x10136C58=3

Addresses are memory addresses (e.g. 0x10136C58 is in .rodata). The section
holding each address is decompressed (RPX zlib sections), patched, recompressed
into the same space, and its CRC in the RPX CRC table is updated, so no other
section moves. The input file is never modified.
"""
import struct
import sys
import zlib

SHF_RPL_ZLIB = 0x08000000
SHT_RPL_CRCS = 0x80000003


def load(path):
    d = bytearray(open(path, 'rb').read())
    if d[:4] != b'\x7fELF':
        sys.exit("not an ELF/RPX file")
    shoff, = struct.unpack('>I', d[0x20:0x24])
    shentsize, shnum = struct.unpack('>HH', d[0x2E:0x32])
    secs = [list(struct.unpack('>10I', d[shoff + i * shentsize:shoff + i * shentsize + 40])) for i in range(shnum)]
    return d, shoff, shentsize, secs


def section_data(d, sec):
    _name, _typ, flags, _addr, off, size = sec[:6]
    raw = bytes(d[off:off + size])
    if flags & SHF_RPL_ZLIB:
        return bytearray(zlib.decompress(raw[4:]))
    return bytearray(raw)


def main():
    if len(sys.argv) >= 3 and sys.argv[2] == '--read':
        d, _shoff, _ent, secs = load(sys.argv[1])
        for a in sys.argv[3:]:
            addr = int(a, 0)
            print(hex(addr), hex(read_u32(d, secs, addr)))
        return
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    d, shoff, shentsize, secs = load(src)
    patches = {}
    for p in sys.argv[3:]:
        a, v = p.split('=')
        patches[int(a, 0)] = int(v, 0)

    by_section = {}
    for addr, value in patches.items():
        idx, data = locate(d, secs, addr)
        by_section.setdefault(idx, (data, []))[1].append((addr, value))

    crc_idx = next(i for i, s in enumerate(secs) if s[1] == SHT_RPL_CRCS)
    crc_off = secs[crc_idx][4]

    for idx, (data, items) in by_section.items():
        sec = secs[idx]
        for addr, value in items:
            o = addr - sec[3]
            old, = struct.unpack('>I', data[o:o + 4])
            data[o:o + 4] = struct.pack('>I', value)
            print("patched %s: 0x%X -> 0x%X" % (hex(addr), old, value))
        flags, off, size = sec[2], sec[4], sec[5]
        if flags & SHF_RPL_ZLIB:
            new = None
            for level in (6, 9, 8, 7, 5, 4, 3, 2, 1):
                comp = struct.pack('>I', len(data)) + zlib.compress(bytes(data), level)
                if len(comp) <= size:
                    new = comp
                    break
            if new is None:
                sys.exit("recompressed section %d doesn't fit in its original space" % idx)
            d[off:off + size] = new + b'\0' * (size - len(new))
            sec[5] = len(new)
            struct.pack_into('>10I', d, shoff + idx * shentsize, *sec)
        else:
            d[off:off + size] = data
        struct.pack_into('>I', d, crc_off + idx * 4, zlib.crc32(bytes(data)) & 0xFFFFFFFF)

    open(dst, 'wb').write(d)

    # verify
    d2, _s, _e, secs2 = load(dst)
    for addr, value in patches.items():
        got = read_u32(d2, secs2, addr)
        assert got == value, (hex(addr), got, value)
    for i, s in enumerate(secs2):
        if s[1] == 1 and s[5]:
            crc, = struct.unpack('>I', d2[crc_off + i * 4:crc_off + i * 4 + 4])
            assert crc == zlib.crc32(bytes(section_data(d2, s))) & 0xFFFFFFFF, "CRC mismatch in section %d" % i
    print("wrote %s (verified)" % dst)


def locate(d, secs, addr):
    for i, s in enumerate(secs):
        if s[1] != 1 or s[3] == 0 or s[5] == 0:
            continue
        data = section_data(d, s)
        if s[3] <= addr < s[3] + len(data):
            return i, data
    sys.exit("address %s is not in any loadable section" % hex(addr))


def read_u32(d, secs, addr):
    i, data = locate(d, secs, addr)
    o = addr - secs[i][3]
    return struct.unpack('>I', data[o:o + 4])[0]


if __name__ == "__main__":
    main()
