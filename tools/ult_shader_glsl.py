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
HEADER = 0x50                    # the Maxwell program header (SPH) before the instructions


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


def glsl(path, set_name, emitter, stage='vs'):
    """(GLSL text, summary line) of the emitter's vertex or pixel program"""
    d = open(path, 'rb').read()
    eff = vfxb.Eff(path)
    if set_name not in eff.sets:
        raise SystemExit('%s: no set %s' % (path, set_name))
    em = [x for x in eff.emitters(eff.sets.index(set_name)) if x['name'] == emitter]
    if not em:
        raise SystemExit('%s: no emitter %s' % (set_name, emitter))
    start, end = eft_shader_dis.code(d, em[0]['shader']['shader_index'], eft_shader_dis.STAGE[stage])
    with tempfile.NamedTemporaryFile(suffix='.sph', delete=False) as f:
        f.write(d[start - HEADER:end])
    try:
        r = subprocess.run([build(), f.name, '0' if stage == 'vs' else '1'], capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    if r.returncode:
        raise SystemExit('translation failed: ' + r.stderr.strip())
    return r.stdout, '// %s %s %s: variation %d; %s' % (set_name, emitter, stage, em[0]['shader']['shader_index'],
                                                        r.stderr.strip())


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
