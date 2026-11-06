#!/usr/bin/env python3
"""Smash 3DS dump unpacking for the Smash Run port (docs/smash-run-port.md).

  python3 tools/s3ds_unpack.py code CODE_BIN OUT          decompress code.bin (ExeFS .code, bottom-up LZ)
  python3 tools/s3ds_unpack.py cros CRO_SARC OUT_DIR      cro.sarc -> OUT_DIR/<module>.cro
  python3 tools/s3ds_unpack.py symbols STATIC_CRS OUT     static.crs exports -> "ADDRESS name" lines, demangled
                                                          (c++filt); addresses as loaded (text at 0x100000:
                                                          code.bin offset = address - 0x100000; odd = Thumb)
  python3 tools/s3ds_unpack.py imports MODULE.cro         a CRO's exported / imported names

Formats:
- code.bin: 3DS bottom LZ. Footer: u32 (header size << 24 | compressed size), u32 extra size; decompressed from
  the end backwards; a flag byte (MSB first), a set bit = a 2-byte back-reference (length 3 + high 4 bits,
  distance 3 + low 12 bits), else a literal.
- cro.sarc: not Nintendo's SARC: "SARC", u32 count, "CRC\\0", then {u32 hash, u32 offset, u32 size, u32 compressed
  size} each; zlib-compressed CROs.
- CRO / CRS: header from 0x80 ("CRO0"); +0xC0 module name {offset, size}; +0xC8 segments {offset, size, type} x n;
  +0xD0 named exports {u32 name offset, u32 segment index | offset << 4}; +0xE0 export strings; +0x118 import strings.
  static.crs is the main executable's (code size 0): its exports are code.bin's names.
  The update's code.bin goes with the update's static.crs / cro.sarc (the base game's don't fit it).
"""
import os
import struct
import subprocess
import sys
import zlib


def blz_decompress(data):
    top_bottom, extra = struct.unpack('<II', data[-8:])
    enc_len, hdr_len = top_bottom & 0xFFFFFF, top_bottom >> 24
    out = bytearray(data) + bytearray(extra)
    src, dst, end = len(data) - hdr_len, len(out), len(data) - enc_len
    while src > end:
        src -= 1
        flags = out[src]
        for _ in range(8):
            if src <= end:
                break
            if flags & 0x80:
                src -= 2
                v = out[src + 1] << 8 | out[src]
                n, disp = (v >> 12) + 3, (v & 0xFFF) + 3
                for _ in range(n):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = out[src]
            flags = (flags << 1) & 0xFF
    assert dst == src, 'bottom LZ: ended at %d / %d' % (dst, src)
    return bytes(out)


def cros(sarc):
    d = open(sarc, 'rb').read()
    assert d[:4] == b'SARC' and d[8:12] == b'CRC\0', 'not Smash 3DS\'s cro.sarc'
    for i in range(struct.unpack_from('<I', d, 4)[0]):
        _h, off, _size, csize = struct.unpack_from('<IIII', d, 0x10 + 16 * i)
        x = zlib.decompress(d[off:off + csize])
        no, ns = struct.unpack_from('<II', x, 0xC0)
        yield x[no:no + ns].split(b'\0')[0].decode(), x


def table(x, at):
    return struct.unpack_from('<II', x, at)


def strings(x, at):
    o, n = table(x, at)
    return [s.decode('latin1') for s in x[o:o + n].split(b'\0') if s]


def exports(x):
    so, sn = table(x, 0xC8)
    segs = [struct.unpack_from('<III', x, so + 12 * i) for i in range(sn)]
    eo, en = table(x, 0xD0)
    out = []
    for i in range(en):
        no, v = struct.unpack_from('<II', x, eo + 8 * i)
        out.append((segs[v & 0xF][0] + (v >> 4), x[no:x.index(b'\0', no)].decode('latin1')))
    return sorted(out)


def demangle(names):
    try:
        return subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True,
                              check=True).stdout.split('\n')[:len(names)]
    except (OSError, subprocess.CalledProcessError):
        return list(names)


def main():
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'code':
        out = blz_decompress(open(a[0], 'rb').read())
        open(a[1], 'wb').write(out)
        print('%d bytes' % len(out))
    elif cmd == 'cros':
        os.makedirs(a[1], exist_ok=True)
        n = 0
        for name, x in cros(a[0]):
            open(os.path.join(a[1], name + '.cro'), 'wb').write(x)
            n += 1
        print('%d modules' % n)
    elif cmd == 'symbols':
        syms = exports(open(a[0], 'rb').read())
        with open(a[1], 'w') as f:
            for (addr, _n), d in zip(syms, demangle([n for _, n in syms])):
                f.write('%08X %s\n' % (addr, d))
        print('%d symbols' % len(syms))
    elif cmd == 'imports':
        x = open(a[0], 'rb').read()
        for title, names in (('exports', strings(x, 0xE0)), ('imports', strings(x, 0x118))):
            print('== %s (%d)' % (title, len(names)))
            for d in demangle(names):
                print('  ' + d)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
