"""Wii U RPX sections: load, decompress, patch 32-bit words by memory address, move relocations
(reloc:LO-HI=DUMMY), grow the code section (grow:END), raise the text region (textregion:SIZE), and check that
no patched word is still rewritten by a relocation at load time.

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import os
import struct
import sys
import zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SHF_RPL_ZLIB = 134217728
SHT_RPL_CRCS = 2147483651
SHT_RPL_FILEINFO = 2147483652

def load(path):
    d = bytearray(open(path, 'rb').read())
    if d[:4] != b'\x7fELF':
        sys.exit('not an ELF/RPX file')
    shoff, = struct.unpack('>I', d[32:36])
    shentsize, shnum = struct.unpack('>HH', d[46:50])
    secs = [list(struct.unpack('>10I', d[shoff + i * shentsize:shoff + i * shentsize + 40])) for i in range(shnum)]
    return (d, shoff, shentsize, secs)

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
    src, dst = (sys.argv[1], sys.argv[2])
    d, shoff, shentsize, secs = load(src)
    patches = {}
    reloc_moves = []
    grows = []
    text_region = None
    for p in sys.argv[3:]:
        if p.startswith('textregion:'):
            text_region = max(text_region or 0, int(p[11:], 0))
            continue
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
    info_idx = next((i for i, s in enumerate(secs) if s[1] == SHT_RPL_FILEINFO), None)
    if text_region is not None:
        info = section_data(d, secs[info_idx])
        old, = struct.unpack('>I', info[4:8])
        if text_region > old:
            struct.pack_into('>I', info, 4, text_region)
            by_section[info_idx] = (info, [])
            print('text region 0x%X -> 0x%X (ends 0x%08X)' % (old, text_region, 33554432 + text_region))
    if info_idx is not None and grows:
        info = by_section[info_idx][0] if info_idx in by_section else section_data(d, secs[info_idx])
        region_end = 33554432 + struct.unpack('>I', info[4:8])[0]
        assert max(grows) <= region_end, 'grow:0x%08X past the text region (ends 0x%08X): textregion:' % (max(grows), region_end)
    for end in sorted(set(grows))[-1:]:
        idx = max((i for i, s in enumerate(secs) if s[1] == 1 and s[2] & 4 and (0 < s[3] < end)), key=lambda i: secs[i][3])
        data = section_data(d, secs[idx])
        need = end - secs[idx][3]
        if len(data) < need:
            print('grew section %d from %s to %s' % (idx, hex(secs[idx][3] + len(data)), hex(end)))
            data += b'\x00' * (need - len(data))
        cache[idx] = data
        by_section.setdefault(idx, (data, []))
    for addr, value in patches.items():
        idx, data = locate(d, secs, addr, cache)
        by_section.setdefault(idx, (data, []))[1].append((addr, value))
    crc_idx = next((i for i, s in enumerate(secs) if s[1] == SHT_RPL_CRCS))
    crc_off = secs[crc_idx][4]
    for lo, hi, dummy in reloc_moves:
        for idx, sec in enumerate(secs):
            if sec[1] != 4:
                continue
            data = by_section[idx][0] if idx in by_section else section_data(d, sec)
            moved = 0
            for o in range(0, len(data), 12):
                off, = struct.unpack('>I', data[o:o + 4])
                if lo <= off < hi and off not in (dummy, dummy + 2):
                    struct.pack_into('>I', data, o, dummy + (off & 3))
                    moved += 1
            if moved:
                print('moved %d relocations in section %d from [%s, %s) to %s' % (moved, idx, hex(lo), hex(hi), hex(dummy)))
                by_section.setdefault(idx, (data, []))
    clashes = reloc_clashes(d, secs, by_section)
    if clashes:
        sys.exit('patched words the loader still relocates (it would rewrite them at load time; hook another word or move the relocation with reloc:):\n  ' + '\n  '.join(clashes))
    for idx, (data, items) in by_section.items():
        sec = secs[idx]
        for addr, value in items:
            o = addr - sec[3]
            old, = struct.unpack('>I', data[o:o + 4])
            data[o:o + 4] = struct.pack('>I', value)
            if old != value:
                print('patched %s: 0x%X -> 0x%X' % (hex(addr), old, value))
        flags, off, size = (sec[2], sec[4], sec[5])
        if flags & SHF_RPL_ZLIB:
            nxt = [s[4] for s in secs if s[4] > off and s[5]] + ([shoff] if shoff > off else [])
            room = min(nxt) - off if nxt else size
            new = None
            for level in (6, 9, 8, 7, 5, 4, 3, 2, 1):
                comp = struct.pack('>I', len(data)) + zlib.compress(bytes(data), level)
                if len(comp) <= room:
                    new = comp
                    break
            if new is None and (not nxt) and (off + size >= len(d) - 63):
                new = struct.pack('>I', len(data)) + zlib.compress(bytes(data), 9)
                del d[off:]
                d += new
                room = len(new)
                print("section %d rewritten at the file's end (%s)" % (idx, hex(off)))
            if new is None:
                new = struct.pack('>I', len(data)) + zlib.compress(bytes(data), 9)
                d[off:off + room] = b'\x00' * room
                off = len(d) + 63 & ~63
                d += b'\x00' * (off - len(d)) + new
                sec[4] = off
                room = len(new)
                print('section %d moved to file offset %s' % (idx, hex(off)))
            d[off:off + room] = new + b'\x00' * (room - len(new))
            sec[5] = len(new)
            struct.pack_into('>10I', d, shoff + idx * shentsize, *sec)
        else:
            d[off:off + size] = data
        struct.pack_into('>I', d, crc_off + idx * 4, zlib.crc32(bytes(data)) & 4294967295)
    import rpx_compact
    before = len(d)
    d = bytearray(rpx_compact.compact(bytes(d))[0])
    if len(d) != before:
        print('compacted %d -> %d bytes' % (before, len(d)))
    open(dst, 'wb').write(d)
    d2, _s, _e, secs2 = load(dst)
    cache2 = {}
    for addr, value in patches.items():
        got = read_u32(d2, secs2, addr, cache2)
        assert got == value, (hex(addr), got, value)
    for i, s in enumerate(secs2):
        if s[1] == 1 and s[5]:
            crc, = struct.unpack('>I', d2[crc_off + i * 4:crc_off + i * 4 + 4])
            assert crc == zlib.crc32(bytes(section_data(d2, s))) & 4294967295, 'CRC mismatch in section %d' % i
    print('wrote %s (verified)' % dst)
RELOC_NAMES = {1: 'ADDR32', 4: 'ADDR16_LO', 5: 'ADDR16_HI', 6: 'ADDR16_HA', 10: 'REL24', 11: 'REL14'}

def reloc_field(typ, off, val, word):
    if typ == 1:
        return (word, val)
    if typ in (4, 5, 6):
        half = word & 65535 if off & 2 else word >> 16
        return (half, {4: val & 65535, 5: val >> 16, 6: val + 32768 >> 16 & 65535}[typ])
    if typ == 10:
        return (word & 67108860, val - (off & ~3) & 67108860)
    if typ == 11:
        return (word & 65532, val - (off & ~3) & 65532)
    return None

def reloc_clashes(d, secs, by_section):
    out = []
    for ridx, rsec in enumerate(secs):
        if rsec[1] != 4 or rsec[7] not in by_section or (not by_section[rsec[7]][1]):
            continue
        tidx = rsec[7]
        tdata = by_section[tidx][0]
        base = secs[tidx][3]
        changed = {}
        for addr, value in by_section[tidx][1]:
            o = addr - base
            old = struct.unpack('>I', tdata[o:o + 4])[0] if o + 4 <= len(tdata) else 0
            if old != value:
                changed[addr & ~3] = value
        if not changed:
            continue
        rdata = by_section[ridx][0] if ridx in by_section else section_data(d, rsec)
        sym = section_data(d, secs[rsec[6]])
        for o in range(0, len(rdata), 12):
            off, info, add = struct.unpack('>IIi', rdata[o:o + 12])
            w = changed.get(off & ~3)
            if w is None:
                continue
            typ, si = (info & 255, info >> 8)
            sval, = struct.unpack('>I', sym[si * 16 + 4:si * 16 + 8])
            f = reloc_field(typ, off, sval + add & 4294967295, w)
            if sval >= 3221225472 or f is None or f[0] != f[1]:
                out.append('0x%08X = 0x%08X: relocation %s at 0x%08X (symbol 0x%08X + 0x%X) writes %s' % (off & ~3, w, RELOC_NAMES.get(typ, 'type %d' % typ), off, sval, add & 4294967295, "the import's address" if sval >= 3221225472 else '?' if f is None else '0x%X over 0x%X' % (f[1], f[0])))
    return out

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
            return (i, data)
    sys.exit('address %s is not in any loadable section' % hex(addr))

def read_u32(d, secs, addr, cache=None):
    i, data = locate(d, secs, addr, cache)
    o = addr - secs[i][3]
    return struct.unpack('>I', data[o:o + 4])[0]
if __name__ == '__main__':
    main()
