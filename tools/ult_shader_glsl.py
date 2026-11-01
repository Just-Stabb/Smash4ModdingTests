#!/usr/bin/env python3
"""An Ultimate effect emitter's compiled shader as GLSL, through OpenSmash-Ultimate's Maxwell translator.

  python3 tools/ult_shader_glsl.py FILE.eff SET EMITTER [vs|ps] [--out FILE.glsl]
  python3 tools/ult_shader_glsl.py PORT SET EMITTER [vs|ps]      (PORT: fighters/PORT/port.json's effect file)

The program is found as tools/eft_shader_dis.py finds it (the emitter's shader_index picks a BNSH
variation); its 0x50-byte program header and instructions go to ssbu-recomp's runtime/mx_translate.c
(port_sources.json key `opensmash`, or $OPENSMASH), built once into build/mx_glsl with
tools/opensmash/mx_glsl_main.c. The result is register-level GLSL (r0.., predicates, F() / U() bit casts),
the same semantics OpenSmash runs the game with.

What the inputs are (eft2, read from these programs and main.bin; docs/fx-render-eft2.md):
  c9          the emitter's data as stored in the effect file: c9 byte k = EMTR binary byte k (vfxb.EMITTER:
              STATIC from 0x50, e.g. scale_anim keys at 0x600 = c9[384..391], rotate_regist c9[459])
  c10         per-emitter values set each frame (c10[8]: the emitter's time)
  c8          the view block
  attributes  the particle arrays (vfx_trace.py): 3 position (w life), 4 velocity (w birth time),
              5 scale, 6 random, 8 / 9 / 10 the emitter matrix at birth (rows)
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eft_shader_dis  # noqa: E402
import port_sources  # noqa: E402
import vfxb  # noqa: E402

BIN = os.path.join(ROOT, 'build', 'mx_glsl')
MAIN = os.path.join(HERE, 'opensmash', 'mx_glsl_main.c')


def recomp():
    r = os.environ.get('OPENSMASH') or (port_sources.load().roots('opensmash') or [None])[0]
    if not r or not os.path.exists(os.path.join(r, 'runtime', 'mx_translate.c')):
        raise SystemExit('no OpenSmash-Ultimate checkout (port_sources.json "opensmash" or $OPENSMASH): '
                         'its runtime/mx_translate.c is the translator')
    return r


def build():
    """build/mx_glsl, rebuilt when the translator or the driver is newer"""
    rt = os.path.join(recomp(), 'runtime')
    srcs = [MAIN, os.path.join(rt, 'mx_translate.c')]
    deps = srcs + [os.path.join(rt, f) for f in ('mx_translate.h', 'mx_ops.h')]
    if os.path.exists(BIN) and all(os.path.getmtime(BIN) >= os.path.getmtime(p) for p in deps if os.path.exists(p)):
        return BIN
    os.makedirs(os.path.dirname(BIN), exist_ok=True)
    subprocess.run(['cc', '-O1', '-w', '-I', rt, *srcs, '-lm', '-o', BIN], check=True)
    return BIN


def program(d, index, stage):
    """(code: the program header + instructions, cdata: constant buffer 1) of BNSH variation index's
    stage ('vs' / 'ps'). The code record (eft_shader_dis.code): +0x08 NVN's control section (0x850 bytes:
    +0x6F8 the code's length, +0x6FC / +0x700 the immediates' size / offset, as ssbu-recomp's mxtest.c
    reads it), +0x10 the code section (a 0x30-byte header, the 0x50-byte SPH, the instructions; the
    immediates further on), +0x18 its size"""
    b = d.find(b'BNSH')
    prog = b + struct.unpack_from('<Q', d, b + 0xC0 + 0x40 * index + 0x10)[0]
    rec = b + struct.unpack_from('<Q', d, prog + 8 + 8 * eft_shader_dis.STAGE[stage])[0]
    ctl = b + struct.unpack_from('<Q', d, rec + 0x08)[0]
    data = b + struct.unpack_from('<Q', d, rec + 0x10)[0]
    code_len, c_size, c_off = struct.unpack_from('<3I', d, ctl + 0x6F8)
    return d[data + 0x30:data + 0x30 + code_len], d[data + c_off:data + c_off + c_size]


def emitter_data(path, set_name, emitter):
    eff = vfxb.Eff(path)
    if set_name not in eff.sets:
        raise SystemExit('%s: no set %s' % (path, set_name))
    em = [x for x in eff.emitters(eff.sets.index(set_name)) if x['name'] == emitter]
    if not em:
        raise SystemExit('%s: no emitter %s' % (set_name, emitter))
    return em[0]


def translate(code, cdata, stage):
    """GLSL text and the translator's summary line"""
    with tempfile.TemporaryDirectory() as t:
        open(os.path.join(t, 'code'), 'wb').write(code)
        open(os.path.join(t, 'cdata'), 'wb').write(cdata)
        r = subprocess.run([build(), os.path.join(t, 'code'), '0' if stage == 'vs' else '1']
                           + ([os.path.join(t, 'cdata')] if cdata else []), capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('translation failed: ' + r.stderr.strip())
    return r.stdout, r.stderr.strip()


def glsl(path, set_name, emitter, stage='vs'):
    """(GLSL text, summary line) of the emitter's vertex or pixel program"""
    em = emitter_data(path, set_name, emitter)
    code, cdata = program(open(path, 'rb').read(), em['shader']['shader_index'], stage)
    text, summary = translate(code, cdata, stage)
    return text, '// %s %s %s: variation %d; %s' % (set_name, emitter, stage, em['shader']['shader_index'], summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('eff', help='an .eff file, or a port name')
    ap.add_argument('set')
    ap.add_argument('emitter')
    ap.add_argument('stage', nargs='?', default='vs', choices=('vs', 'ps'))
    ap.add_argument('--out')
    a = ap.parse_args()
    path = a.eff if os.path.exists(a.eff) else port_sources.load().eff(a.eff)
    text, head = glsl(path, a.set, a.emitter, a.stage)
    text = head + '\n' + text
    if a.out:
        open(a.out, 'w').write(text)
        print(head)
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
