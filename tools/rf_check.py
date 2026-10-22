#!/usr/bin/env python3
"""Smash 4's resource table (content/patch/resource, as Sm4shExplorer builds it): list entries and
find the ones the game can't read.

  python3 tools/rf_check.py RESOURCE [--list PREFIX] [--packed PATH=PACKED_FILE ...]

Format (Sm4shExplorer's RFManager writer): "RF" header (0x80 bytes: +0x10 entries' size + 0x18,
+0x18 compressed size, +0x1C decompressed size, +0x20 names offset + 0x80, +0x24 names size), then
zlib: 24-byte entries from +0x18 (offset in package, name offset | extension << 24, compressed
size, decompressed size, timestamp, flags: depth in the low byte, 0x200 folder, 0x400 package (a
file's own, or a folder packed as one), 0x800, 0x1000, 0x4000 externally patched), then the names
(at name offset + 4) and the extension table (Utils.GetExtensionTable).

Checks: a file flagged as a package of its own (0x400) inside a packaged folder (the game crashed
reading such a folder's package: docs/kind-expansion.md, Supamario's chr_10 icon); with --packed, each
file of that package against the package file (its offset, sizes, data).
"""
import struct
import sys
import zlib

EXT = ['', '.bin', '.nuf', '.nut', '.efc', '.ptcl', '.mta', '.nud', '.omo', '.vbn', '.xmb',
       '.xmta', '.jtb', '.nhb', '.sb', '.pac', '.flp', '.ik', '.moi', '.sbwl', '.mtable', '.mscsb',
       '.nus3bank', '.sqb', '.vat', '.mir', '.cms', '.lvd', '.mfp', '.exi', '.obt', '.gya', '.h',
       '.log', '.mtmp', '.nhbxml', '.sa', '.tdb', '.xmbxml', '.hkt', '.HKX', '.mbm', '.gsh',
       '.xtal', '.nsh', '.rsm', '.vew', '.fbb', '.mmb', '.mpb', '.csb', '.nus3conf', '.nus3conf3d',
       '.mtb', '.spt', '.fnv', '.svt', '.local', '.brf', '.tex', '.texatlas', '.fgb', '.flx',
       '.lst', '.tinf', '.lm', '.msb', '.msbt', '.txt', '.tga']


def load(path):
    d = open(path, 'rb').read()
    assert d[:2] == b'RF', 'not a resource file'
    ress, clen, names_off = (struct.unpack_from('<I', d, o)[0] for o in (0x10, 0x18, 0x20))
    f = zlib.decompress(d[0x80:0x80 + clen])
    names = f[names_off - 0x80:]
    out, parts = [], [None] * 64
    for i in range((ress - 0x18) // 24):
        off, nm, cmp, dec, _ts, fl = struct.unpack_from('<6I', f, 0x18 + 24 * i)
        no, ext = nm & 0xFFFFFF, nm >> 24
        name = names[4 + no:names.index(b'\0', 4 + no)].decode('ascii', 'replace') + (EXT[ext] if ext < len(EXT) else '.?%d' % ext)
        depth = fl & 0xFF
        parts[depth - 1] = name
        out.append(dict(path=''.join(parts[:depth]), off=off, cmp=cmp, dec=dec, fl=fl))
    return out


def main():
    a = sys.argv[1:]
    ents = load(a[0])
    by = {e['path']: e for e in ents}

    def package_of(path):
        bits = path.rstrip('/').split('/')
        for k in range(len(bits) - 1, 0, -1):
            q = '/'.join(bits[:k]) + '/'
            if q in by and by[q]['fl'] & 0x400:
                return q
        return None
    if '--list' in a:
        pre = a[a.index('--list') + 1]
        for e in ents:
            if e['path'].startswith(pre):
                print('%-70s off %-8x cmp %-8d dec %-8d flags %x' % (e['path'], e['off'], e['cmp'], e['dec'], e['fl']))
    bad = [e for e in ents if not e['path'].endswith('/') and e['fl'] & 0x400 and package_of(e['path'])]
    for e in bad:
        print('LOOSE IN PACKAGE %s (package %s): offset %x, flags %x' % (e['path'], package_of(e['path']), e['off'], e['fl']))
    for spec in [a[i + 1] for i, x in enumerate(a) if x == '--packed']:
        pkg, fn = spec.split('=', 1)
        data = open(fn, 'rb').read()
        top = by[pkg]
        print('%s: package %d bytes, the table says %d' % (pkg, len(data), top['cmp']))
        for e in ents:
            if e['path'].startswith(pkg) and e['path'] != pkg and not e['path'].endswith('/'):
                blob = data[e['off']:e['off'] + e['cmp']]
                try:
                    n = len(zlib.decompress(blob)) if blob[:2] == b'\x78\x9c' else len(blob)
                except zlib.error as x:
                    n = 'zlib error %s' % x
                if n != e['dec']:
                    print('  BAD %s: offset %x cmp %d: data gives %s, the table %d' % (e['path'], e['off'], e['cmp'], n, e['dec']))
    print('%d entries, %d loose files in packages' % (len(ents), len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
