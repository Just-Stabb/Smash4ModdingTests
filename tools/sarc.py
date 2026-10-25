#!/usr/bin/env python3
"""SARC archives (Smash Ultimate's ui/layout/.../layout.arc: the layouts, animations and textures of a
UI screen): list or extract.

  python3 tools/sarc.py list FILE.arc
  python3 tools/sarc.py extract FILE.arc OUTDIR

SARC: "SARC" header (+4 its size, +6 the byte order mark, +0xC the data's offset), then SFAT (+6 the
node count, 16 bytes a node from +0xC: name hash, attributes (0x01xxxxxx: name offset / 4 in SFNT),
data start, data end) and SFNT (the names, from +8).
"""
import os
import struct
import sys


def read(d):
    """{name: bytes}"""
    assert d[:4] == b'SARC', 'not a SARC'
    e = '<' if d[6:8] == b'\xff\xfe' else '>'
    hdr, = struct.unpack(e + 'H', d[4:6])
    data, = struct.unpack(e + 'I', d[0xC:0x10])
    n, = struct.unpack(e + 'H', d[hdr + 6:hdr + 8])
    nodes = [struct.unpack(e + 'IIII', d[hdr + 12 + 16 * i:hdr + 28 + 16 * i]) for i in range(n)]
    names = hdr + 12 + 16 * n + 8
    out = {}
    for _h, attr, s, t in nodes:
        no = names + (attr & 0xFFFFFF) * 4
        out[d[no:d.index(b'\0', no)].decode()] = d[data + s:data + t]
    return out


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('list', 'extract'):
        sys.exit(__doc__)
    files = read(open(sys.argv[2], 'rb').read())
    for name, b in sorted(files.items()):
        if sys.argv[1] == 'list':
            print('%8d %s' % (len(b), name))
        else:
            p = os.path.join(sys.argv[3], name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(b)


if __name__ == '__main__':
    main()
