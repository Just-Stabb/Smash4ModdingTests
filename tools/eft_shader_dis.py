#!/usr/bin/env python3
"""An Ultimate effect emitter's compiled shader (from the effect file's own BNSH), disassembled.

  python3 tools/eft_shader_dis.py FILE.eff SET EMITTER [vs|ps]        (default ps)

The emitter's shader_index (vfxb.py: shader) picks a BNSH variation: grsc at +0x60 of the BNSH,
variations (0x40 bytes) from +0xC0, each +0x10 the binary program's offset; that holds the code
records' offsets, vertex at +0x08, pixel at +0x28; a record +0x10 the code's offset, +0x1C its size
(offsets from the BNSH). The code is NVN (0x12345678, the SPH 0x30 after it, the instructions from
+0x80), disassembled with tools/maxwell_dis/envydis as tools/nush_dis.py does. In a pixel shader
a[0x80] / a[0x90] are colour 0 / 1 (rgb), a[0x8c] alpha, c9 the emitter's constants.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vfxb  # noqa: E402

ENVYDIS = os.path.join(HERE, 'maxwell_dis', 'envydis')
STAGE = {'vs': 0, 'ps': 4}


def code(d, index, stage):
    """(start, end) of variation index's code for stage (0 vertex, 4 pixel) in the file d"""
    b = d.find(b'BNSH')
    prog = b + struct.unpack_from('<Q', d, b + 0xC0 + 0x40 * index + 0x10)[0]
    rec = b + struct.unpack_from('<Q', d, prog + 8 + 8 * stage)[0]
    off, size = struct.unpack_from('<Q', d, rec + 0x10)[0], struct.unpack_from('<I', d, rec + 0x1C)[0]
    return b + off + 0x80, b + off + size


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    path, set_name, emitter = sys.argv[1:4]
    stage = STAGE[sys.argv[4] if len(sys.argv) == 5 else 'ps']
    d = open(path, 'rb').read()
    eff = vfxb.Eff(path)
    e = [x for x in eff.emitters(eff.sets.index(set_name)) if x['name'] == emitter][0]
    start, end = code(d, e['shader']['shader_index'], stage)
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(d[start:end])
    out = subprocess.run([ENVYDIS, '-m', 'gm107', '-w', '-n', '-i', f.name], capture_output=True, text=True).stdout
    os.unlink(f.name)
    lines = [l for l in out.splitlines() if 'sched' not in l and ' nop ' not in l]
    cut = next((i for i, l in enumerate(lines) if '???' in l), len(lines))   # past the code: data
    print('== %s %s: variation %d, custom shader %d flag %d' % (set_name, emitter, e['shader']['shader_index'],
                                                              e['shader']['custom_shader_index'],
                                                              e['shader']['custom_shader_flag']))
    print('\n'.join(lines[:cut]))


if __name__ == '__main__':
    main()
