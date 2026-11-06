#!/usr/bin/env python3
"""Smash 3DS dump unpacking for the Smash Run port (docs/smash-run-port.md).

  python3 tools/s3ds_unpack.py code CODE_BIN OUT          decompress code.bin (ExeFS .code, bottom-up LZ)
  python3 tools/s3ds_unpack.py cros CRO_SARC OUT_DIR      cro.sarc -> OUT_DIR/<module>.cro
  python3 tools/s3ds_unpack.py symbols STATIC_CRS OUT     static.crs exports -> "ADDRESS name" lines, demangled
                                                          (c++filt); addresses as loaded (text at 0x100000:
                                                          code.bin offset = address - 0x100000; odd = Thumb)
  python3 tools/s3ds_unpack.py imports MODULE.cro         a CRO's exported / imported names
  python3 tools/s3ds_unpack.py list ROMFS [PREFIX]          the data archive's files (path, size), the update's
                                                          patch/ over the base
  python3 tools/s3ds_unpack.py extract ROMFS OUT PREFIX...  extract the files under the prefixes to OUT/<path>

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
- dt / ls (RomFS root, the update's in patch/): ls = u32 version, u32 count, {u32 key, u32 dt offset, u32 size};
  a dt chunk = 0xCC padding, then zlib streams. Keys are CRC-32 with a zero start (zlib.crc32(s, 0xFFFFFFFF)) of
  "data<region>/<folder>/packed" (a packaged folder, its trailing / dropped) or "data<region>/<file>" (a file
  packaged on its own); region "" or e.g. "(us_en)" (code.bin 0x1A2A60 builds them).
- The file tree is the "RF" resource (version 5) at key hash("data/resource"... found as the chunk starting with
  "RF"): header +0x18 compressed size, +0x20 names offset + 0x80; zlib; 24-byte entries (dt offset within the
  package, name | extension << 24, compressed, decompressed, timestamp, flags: depth in the low byte, 0x200 folder,
  0x400 package); names at name offset + 4. A name with bit 0x800000 is shortened: control byte b0 (length - 4 in
  bits 0-4, distance bits 8-9 in bits 6-7), b1 (distance bits 0-7): copy that many characters from that far back in
  the names table, then the rest of the string. Extensions: the table at the end of the names (u32 count, offsets).
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


def _rf_from(dt_path, ls_entries):
    """the resource table of a dt (the chunk that decompresses to "RF")"""
    with open(dt_path, 'rb') as f:
        for _k, off, size in ls_entries:
            f.seek(off)
            head = f.read(0x100)
            i = 0
            while i < len(head) and head[i] == 0xCC:
                i += 1
            if head[i:i + 2] == b'RF':
                f.seek(off + i)
                return f.read(size - i)
    raise SystemExit('%s: no RF resource table' % dt_path)


def load_ls(path):
    d = open(path, 'rb').read()
    return [struct.unpack_from('<III', d, 8 + 12 * j) for j in range(struct.unpack_from('<I', d, 4)[0])]


def load_rf(d):
    """[(path, offset in its package, compressed size, decompressed size, flags)] in table order"""
    ress, clen, names_off = (struct.unpack_from('<I', d, o)[0] for o in (0x10, 0x18, 0x20))
    f = zlib.decompress(d[0x80:0x80 + clen])
    names = f[names_off - 0x80:]
    i = names.rindex(b'\x00\x00\x00\x00\x27\x00\x00\x00') - 4    # the extension table: count, offsets
    count = struct.unpack_from('<I', names, i)[0]
    cs = lambda p: names[p:names.index(b'\0', p)]                    # noqa: E731
    ext = [cs(o + 4).decode() if o else '' for o in struct.unpack_from('<%dI' % count, names, i + 4)]

    def name(v):
        p = (v & 0x7FFFFF) + 4
        if v & 0x800000:
            b0, b1 = names[p], names[p + 1]
            s = p - (((b0 >> 6) << 8) | b1)
            return (names[s:s + (b0 & 0x1F) + 4] + cs(p + 2)).decode()
        return cs(p).decode()
    parts, out = [None] * 64, []
    for k in range((names_off - 0x80) // 24):
        off, v, cmp, dec, _ts, fl = struct.unpack_from('<6I', f, 24 * k)
        if (v >> 20) & 0xF == 0xB or not fl & 0xFF:
            continue
        depth, e = fl & 0xFF, (v >> 24) & 0x7F
        parts[depth - 1] = name(v) + (ext[e] if e < len(ext) else '')
        out.append((''.join(parts[:depth]), off, cmp, dec, fl))
    return out


def key(s):
    return zlib.crc32(s.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


class Archive:
    """a RomFS's dt / ls, the update's patch/ dt / ls first"""

    def __init__(self, romfs):
        self.parts = []
        for sub in ('patch', ''):
            ls = os.path.join(romfs, sub, 'ls')
            if os.path.exists(ls):
                ents = load_ls(ls)
                self.parts.append((os.path.join(romfs, sub, 'dt'), {k: (o, s) for k, o, s in ents}, ents))
        self.files = load_rf(_rf_from(self.parts[0][0], self.parts[0][2]))

    def where(self, package):
        k = key('data/%s/packed' % package.rstrip('/') if package.endswith('/') else 'data/' + package)
        for dt, table, _e in self.parts:
            if k in table:
                return dt, table[k][0]
        return None

    def entries(self):
        """(path, compressed, decompressed, package path) of every file"""
        pkg = None
        for path, off, cmp, dec, fl in self.files:
            if fl & 0x400:
                pkg = (path, self.where(path))
            if path.endswith('/') or pkg is None or not path.startswith(pkg[0]):
                continue
            yield path, off, cmp, dec, pkg

    def read(self, off, cmp, dec, pkg):
        if pkg[1] is None:
            return None
        dt, base = pkg[1]
        with open(dt, 'rb') as f:
            f.seek(base + off)
            b = f.read(cmp)
        return zlib.decompress(b) if cmp != dec else b


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
    elif cmd == 'list':
        pre = a[1] if len(a) > 1 else ''
        for path, _off, _cmp, dec, pkg in Archive(a[0]).entries():
            if path.startswith(pre):
                print('%-90s %9d%s' % (path, dec, '' if pkg[1] else '  (not in this dump)'))
    elif cmd == 'extract':
        ar, n = Archive(a[0]), 0
        for path, off, cmp, dec, pkg in ar.entries():
            if any(path.startswith(p) for p in a[2:]):
                data = ar.read(off, cmp, dec, pkg)
                if data is None:
                    continue
                dst = os.path.join(a[1], path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(data)
                n += 1
        print('%d files' % n)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
