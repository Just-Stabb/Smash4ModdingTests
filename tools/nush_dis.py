#!/usr/bin/env python3
"""Ultimate shader binaries (render/shader/bin/*.nushdb, 'HBSS' / 'RDHS'): a named program's Maxwell
code disassembled.

  python3 tools/nush_dis.py NAME FILE.nushdb [FILE ...]       e.g. 0x4f000065PS nusampleshaderlist.*.nushdb

Layout (read off nusampleshaderlist.N.nushdb): each program is its name (C string), a record, its NVN
code (header word 0x12345678; the shader program header, SPH, 0x30 after it, 0x50 bytes: word 0 type
and version, e.g. 0x00065462 a pixel shader; the code right after it, in groups of four 64-bit words,
the first the scheduling word), then the names of the uniforms / attributes it can use. The code runs
up to EXIT and the branch-to-self after it. Disassembled with tools/maxwell_dis/envydis (envytools,
`-m gm107`; tools/maxwell_dis/build.sh). In the output a[0x80 + 0x10 n] is attribute n's x (vertex
input / pixel varying), cN[off] constant buffer N at byte off.
"""
import os
import struct
import subprocess
import sys
import tempfile

ENVYDIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maxwell_dis', 'envydis')
NVN_MAGIC = struct.pack('<I', 0x12345678)
EXIT_LOOP = bytes.fromhex('0f0007ffff0f40e2')   # BRA to itself, after EXIT


def program(d, name):
    """(sph offset, code start, code end) of program NAME, or None"""
    i = d.find(name.encode() + b'\0')
    if i < 0:
        return None
    sph = d.find(NVN_MAGIC, i) + 0x30
    code = sph + 0x50
    end = d.find(EXIT_LOOP, code)
    end = (end + 8 + 31) // 32 * 32 if end > 0 else code + 0x1000
    return sph, code, end


def main():
    name = sys.argv[1]
    for path in sys.argv[2:]:
        d = open(path, 'rb').read()
        p = program(d, name)
        if p is None:
            continue
        sph, code, end = p
        print('== %s in %s: SPH 0x%X, code 0x%X-0x%X' % (name, os.path.basename(path), sph, code, end))
        print('SPH: ' + ' '.join('%08x' % w for w in struct.unpack_from('<20I', d, sph)))
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(d[code:end])
        out = subprocess.run([ENVYDIS, '-m', 'gm107', '-w', '-n', '-i', f.name], capture_output=True, text=True).stdout
        os.unlink(f.name)
        lines = [l for l in out.splitlines() if 'sched' not in l and ' nop ' not in l]
        cut = next((i for i, l in enumerate(lines) if '???' in l), len(lines))   # past the code: data
        print('\n'.join(lines[:cut]))


if __name__ == '__main__':
    main()
