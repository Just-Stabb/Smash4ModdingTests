#!/usr/bin/env python3
"""Smash 4 shader files (shader/*.nsh: 'NSP3') dumped: each shader's GX2 programs disassembled.

  python3 tools/nsh_dump.py FILE.nsh [SHADER_ID ...]      (ids as 0x4F000001; default: all)

Layout (read off shader/effect_trail.nsh): 'NSP3', u32 file size, u32, then one record a shader:
u32 shader id (e.g. 0x4F000001: trail shader 1), u32 program count (2: vertex + pixel), offsets, u32
the record's size (to the next record); the record's programs follow it as standard GX2 .gsh files
('Gfx2' header, then 'BLK{' blocks: type 3 / 6 / 8 the vertex / pixel / geometry header with the
uniform, sampler and attribute names, 5 / 7 / 9 its program, 1 the end). Programs are disassembled
with tools/latte_dis/latte-dis (decaf-emu's Latte disassembler; tools/latte_dis/build.sh builds it).
"""
import os
import re
import struct
import subprocess
import sys

LATTE_DIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'latte_dis', 'latte-dis')
BLOCKS = {1: 'end', 2: 'padding', 3: 'vertex header', 5: 'vertex program', 6: 'pixel header',
          7: 'pixel program', 8: 'geometry header', 9: 'geometry program', 10: 'geometry copy program'}


def records(d):
    """[(shader id, offset)]: the records are at 0x20 and each record's last word before zeros is
    its size (to the next one)"""
    out, o = [], 0x20
    while o + 8 <= len(d):
        sid, n = struct.unpack_from('>II', d, o)
        if sid >> 24 != 0x4F or n == 0 or n > 8:
            break
        out.append((sid, o))
        words = struct.unpack_from('>%dI' % (2 + n * 2 + 1), d, o)
        o += words[-1]
    return out


def programs(d, start, end):
    """GX2 files in [start, end): [(offset, [(block type, data offset, size)])]"""
    out = []
    for m in re.finditer(b'Gfx2', d[start:end]):
        g = start + m.start()
        o = g + struct.unpack_from('>I', d, g + 4)[0]
        blocks = []
        while o + 0x20 <= len(d) and d[o:o + 4] == b'BLK{':
            head, _major, _minor, typ, size = struct.unpack_from('>5I', d, o + 4)
            blocks.append((typ, o + head, size))
            if typ == 1:
                break
            o += head + size
        out.append((g, blocks))
    return out


def main():
    path = sys.argv[1]
    want = {int(a, 0) for a in sys.argv[2:]}
    d = open(path, 'rb').read()
    assert d[:4] == b'NSP3', d[:4]
    recs = records(d)
    for i, (sid, o) in enumerate(recs):
        if want and sid not in want:
            continue
        end = recs[i + 1][1] if i + 1 < len(recs) else len(d)
        print('==== shader 0x%08X (record at 0x%X)' % (sid, o))
        for g, blocks in programs(d, o, end):
            for typ, data, size in blocks:
                if typ in (3, 6, 8):
                    names = sorted({m.group().decode() for m in
                                    re.finditer(rb'[A-Za-z_][A-Za-z0-9_\[\]]{2,}', d[data:data + size])} - {'BLK'})
                    print('-- %s (0x%X): %s' % (BLOCKS[typ], data, ' '.join(names)))
                elif typ in (5, 7, 9, 10):
                    print('-- %s (0x%X, 0x%X bytes)' % (BLOCKS[typ], data, size))
                    r = subprocess.run([LATTE_DIS, path, hex(data), hex(size)], capture_output=True, text=True)
                    print('\n'.join(l for l in (r.stdout or r.stderr).splitlines() if l.strip()))


if __name__ == '__main__':
    main()
