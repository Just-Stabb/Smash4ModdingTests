#!/usr/bin/env python3
"""Patches big-endian 32-bit values in a Wii U RPX (e.g. Smash 4's cross_f.rpx).

Usage:
  python3 tools/rpx_patch.py IN.rpx OUT.rpx ADDRESS=VALUE [ADDRESS=VALUE ...]
  python3 tools/rpx_patch.py IN.rpx --read ADDRESS [ADDRESS ...]

Example (Kirby's starmissile max count, 1 -> 3):
  python3 tools/rpx_patch.py cross_f.rpx cross_f_patched.rpx 0x10136C58=3

Relocations: an argument `reloc:LO-HI=DUMMY` moves every relocation whose target address is in
[LO, HI) to DUMMY (halfword relocations to DUMMY+2), so the loader doesn't rewrite code put
there (e.g. a code cave in a dead function: its relocations would otherwise patch the new code
at load time). DUMMY must be a dead word.

`grow:END` extends the code section below END with zeros up to END (room for new code after the
game's own; END must stay below the text region's end in the RPL file info). A section that no
longer fits in its place in the file is moved to the end of the file.

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
    reloc_moves = []
    grows = []
    for p in sys.argv[3:]:
        if p.startswith('grow:'):
            grows.append(int(p[5:], 0))
            continue
        if p.startswith('reloc:'):
            rng, dummy = p[6:].split('=')
            lo, hi = rng.split('-')
            reloc_moves.append((int(lo, 0), int(hi, 0), int(dummy, 0)))
            continue
        a, v = p.split('=')
        patches[int(a, 0)] = int(v, 0)

    by_section = {}
    cache = {}
    for end in sorted(set(grows))[-1:]:     # several grow: (one per cave script): the largest
        # the code section that ends below END grows (zero-filled) up to it; the loader maps the
        # whole text region (textRegionSize in the file info), so this stays inside allocated code
        # memory as long as END is below the region's end
        idx = max((i for i, s in enumerate(secs) if s[1] == 1 and s[2] & 4 and 0 < s[3] < end),
                  key=lambda i: secs[i][3])
        data = section_data(d, secs[idx])
        need = end - secs[idx][3]
        if len(data) < need:
            print("grew section %d from %s to %s" % (idx, hex(secs[idx][3] + len(data)), hex(end)))
            data += b'\0' * (need - len(data))
        cache[idx] = data
        by_section.setdefault(idx, (data, []))
    for addr, value in patches.items():
        idx, data = locate(d, secs, addr, cache)
        by_section.setdefault(idx, (data, []))[1].append((addr, value))

    crc_idx = next(i for i, s in enumerate(secs) if s[1] == SHT_RPL_CRCS)
    crc_off = secs[crc_idx][4]

    for lo, hi, dummy in reloc_moves:
        for idx, sec in enumerate(secs):
            if sec[1] != 4:  # SHT_RELA
                continue
            # the copy an earlier reloc: argument already changed, if any (each one used to start
            # from the file's data again, so only the first argument's moves were kept)
            data = by_section[idx][0] if idx in by_section else section_data(d, sec)
            moved = 0
            for o in range(0, len(data), 12):
                off, = struct.unpack('>I', data[o:o + 4])
                if lo <= off < hi and off not in (dummy, dummy + 2):
                    struct.pack_into('>I', data, o, dummy + (off & 3))
                    moved += 1
            if moved:
                print("moved %d relocations in section %d from [%s, %s) to %s"
                      % (moved, idx, hex(lo), hex(hi), hex(dummy)))
                by_section.setdefault(idx, (data, []))

    for idx, (data, items) in by_section.items():
        sec = secs[idx]
        for addr, value in items:
            o = addr - sec[3]
            old, = struct.unpack('>I', data[o:o + 4])
            data[o:o + 4] = struct.pack('>I', value)
            if old != value:
                print("patched %s: 0x%X -> 0x%X" % (hex(addr), old, value))
        flags, off, size = sec[2], sec[4], sec[5]
        if flags & SHF_RPL_ZLIB:
            # Room = up to the next section's data (the original space; an earlier patch may have
            # shrunk the recorded size and zero-padded the rest), never into the header table.
            nxt = [s[4] for s in secs if s[4] > off and s[5]] + ([shoff] if shoff > off else [])
            room = min(nxt) - off if nxt else size
            new = None
            for level in (6, 9, 8, 7, 5, 4, 3, 2, 1):
                comp = struct.pack('>I', len(data)) + zlib.compress(bytes(data), level)
                if len(comp) <= room:
                    new = comp
                    break
            if new is None:
                # doesn't fit any more (a grown section): move it to the end of the file
                new = struct.pack('>I', len(data)) + zlib.compress(bytes(data), 9)
                d[off:off + room] = b'\0' * room
                off = (len(d) + 63) & ~63
                d += b'\0' * (off - len(d)) + new
                sec[4] = off
                room = len(new)
                print("section %d moved to file offset %s" % (idx, hex(off)))
            d[off:off + room] = new + b'\0' * (room - len(new))
            sec[5] = len(new)
            struct.pack_into('>10I', d, shoff + idx * shentsize, *sec)
        else:
            d[off:off + size] = data
        struct.pack_into('>I', d, crc_off + idx * 4, zlib.crc32(bytes(data)) & 0xFFFFFFFF)

    open(dst, 'wb').write(d)

    # verify
    d2, _s, _e, secs2 = load(dst)
    cache2 = {}
    for addr, value in patches.items():
        got = read_u32(d2, secs2, addr, cache2)
        assert got == value, (hex(addr), got, value)
    for i, s in enumerate(secs2):
        if s[1] == 1 and s[5]:
            crc, = struct.unpack('>I', d2[crc_off + i * 4:crc_off + i * 4 + 4])
            assert crc == zlib.crc32(bytes(section_data(d2, s))) & 0xFFFFFFFF, "CRC mismatch in section %d" % i
    print("wrote %s (verified)" % dst)


def locate(d, secs, addr, cache=None):
    for i, s in enumerate(secs):
        if s[1] != 1 or s[3] == 0 or s[5] == 0:
            continue
        if cache is not None and i in cache:
            data = cache[i]
        else:
            data = section_data(d, s)
            if cache is not None:
                cache[i] = data
        if s[3] <= addr < s[3] + len(data):
            return i, data
    sys.exit("address %s is not in any loadable section" % hex(addr))


def read_u32(d, secs, addr, cache=None):
    i, data = locate(d, secs, addr, cache)
    o = addr - secs[i][3]
    return struct.unpack('>I', data[o:o + 4])[0]


if __name__ == "__main__":
    main()
