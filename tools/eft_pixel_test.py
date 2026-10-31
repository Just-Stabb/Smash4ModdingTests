#!/usr/bin/env python3
"""Checks tools/eft_pixel.py: each program variant assembled, disassembled back from its bytes and run
(a small Latte interpreter, after tools/trail_shader_test.py's) against eft2's combiner on random
inputs; and, given a ptcl (a converted bank), every own shader there: its pixel program one of
these, its vertex program and header the template's.

  python3 tools/eft_pixel_test.py [BANK.ptcl]
"""
import itertools
import os
import random
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eft_pixel as E  # noqa: E402
from trail_shader_test import lit  # noqa: E402

FAILS = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        FAILS.append(what)


def disasm(prog):
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(prog)
    try:
        out = subprocess.run([os.path.join(HERE, 'latte_dis', 'latte-dis'), f.name, '0', str(len(prog))],
                             capture_output=True, text=True).stdout
    finally:
        os.unlink(f.name)
    return [ln for ln in out.splitlines() if ln.strip()]


def run(lines, regs, kc0, tex):
    """runs a disassembled program; an ALU group reads before it writes (Latte's PV semantics aside:
    these programs don't use PV)"""
    ch = 'xyzw'
    get = lambda r: regs.setdefault(r, [0.0] * 4)  # noqa: E731

    def src(tok):
        neg = tok.startswith('-')
        tok = tok[1:] if neg else tok
        if tok.startswith('(') and tok.endswith(')') and '0x' in tok:
            v = lit(tok)
        else:
            v = lit(tok)
            if v is None:
                m = re.fullmatch(r'(R\d+|KC0\[(\d+)\])\.([xyzw])', tok)
                assert m, tok
                v = kc0[int(m.group(2))][ch.index(m.group(3))] if m.group(2) else get(m.group(1))[ch.index(m.group(3))]
        return -v if neg else v
    group, out = [], None

    def flush():
        writes = []
        for dst, op, s, clamp in group:
            v = {'MOV': lambda: s[0], 'MUL': lambda: s[0] * s[1], 'ADD': lambda: s[0] + s[1],
                 'MULADD': lambda: s[0] * s[1] + s[2]}[op]()
            writes.append((dst, min(max(v, 0.0), 1.0) if clamp else v))
        for dst, v in writes:
            r, c = dst.split('.')
            get(r)[ch.index(c)] = v
        group.clear()
    for line in lines:
        m = re.match(r'\s*(\d+\s+)?([xyzwt]):\s+(\w+)\s+(.*)', line)
        if m:
            if m.group(1):
                flush()
            text = m.group(4)
            clamp = text.rstrip().endswith('CLAMP')
            text = re.sub(r'\s+CLAMP$', '', text.rstrip())
            args = [a.strip() for a in re.split(r',\s*(?![^()]*\))', text)]
            group.append((args[0], m.group(3), [src(a) for a in args[1:]], clamp))
            continue
        flush()
        m = re.match(r'\s*\d+\s+SAMPLE\s+(R\d+)\.xyzw,\s+(R\d+)\.(xy|zw)0[xz],\s+t(\d),\s+s(\d)', line)
        if m:
            assert m.group(4) == m.group(5), line
            r = get(m.group(2))
            u, v = (r[0], r[1]) if m.group(3) == 'xy' else (r[2], r[3])
            regs[m.group(1)] = list(tex(u, v, int(m.group(4))))
            continue
        m = re.match(r'\s*\d+\s+EXP_DONE: PIX0, (R\d+)\.xyzw', line)
        if m:
            out = list(get(m.group(1)))
    return out


def expected(cm, am, gain, c0, c1, t, vc, hdr, t1=None, blend=(0, 0), dissolve=None, premult=False, additive=False):
    if dissolve is not None:
        # (width, threshold): texture grey in .x, the mask in .y
        width, thr = dissolve
        ramp = min(max((t[1] - thr) / width, 0.0), 1.0)
        out = expected(cm, am, gain, c0, c1, [t[0], t[0], t[0], t[3]], vc, hdr)
        return out[:3] + [out[3] * ramp]
    if t1 is not None:
        t = [(a + b) if blend[k == 3] else a * b for k, (a, b) in enumerate(zip(t, t1))]
    c0_, c1_, t_ = c0[:3], c1[:3], t[:3]
    if cm == 0:
        rgb = c0_
    elif cm == 1:
        rgb = [a * b for a, b in zip(c0_, t_)]
    elif cm == 2:
        rgb = [b + (a - b) * x for a, b, x in zip(c0_, c1_, t_)]
    else:
        rgb = [a * x + b for a, b, x in zip(c0_, c1_, t_)]
    if am == 4:
        a = min(max(min(max((t[3] - c0[3]) * 4, 0.0), 1.0) * gain, 0.0), 1.0)
    else:
        a = (t[3] + c0[3] - 1) if am == 1 else c0[3] * t[3]
        a *= gain
    if vc is not None:
        rgb = [x * y for x, y in zip(rgb, vc[:3])]
        a *= vc[3]
    a = min(max(a, 0.0), 1.0)
    # additive (premultiplied): alpha out 0, so ONE / INV_SRC_ALPHA adds
    return [(min(max(x, 0.0), 1.0) * hdr[0] + hdr[3]) * (a if premult else 1.0) for x in rgb] + [
        0.0 if premult and additive else a]


LAYOUTS = {
    'quad (0, 1, 9)': {'regs': 3, 'c0': 0, 'c1': 1, 'vc': None, 'uv': (2, 'xy'), 'sems': [0, 1, 9]},
    'mesh (0, 1, 6, 10)': {'regs': 4, 'c0': 0, 'c1': 1, 'vc': 2, 'uv': (3, 'zw'), 'sems': [0, 1, 6, 10]},
    'mesh without colour 1 (0, 6, 10), colour 1 constant': {'regs': 3, 'c0': 0, 'c1': None, 'vc': 1, 'uv': (2, 'xy'),
                                                            'sems': [0, 6, 10]},
}
TWO = {
    'quad, two textures (0, 1, 9): t0 .xy, t1 .zw': {'regs': 3, 'c0': 0, 'c1': 1, 'vc': None, 'uv': (2, 'xy'),
                                                    'uv1': (2, 'zw'), 'sems': [0, 1, 9]},
    'mesh, two textures (0, 1, 6, 10)': {'regs': 4, 'c0': 0, 'c1': 1, 'vc': 2, 'uv': (3, 'xy'), 'uv1': (3, 'zw'),
                                         'sems': [0, 1, 6, 10]},
}
C1_CONST = (0.37, 0.0, 1.25)


def test_variants():
    rnd = random.Random(1)
    for name, lay in LAYOUTS.items():
        for cm in range(4):
            for am, gain, (premult, additive) in itertools.product((0, 1, 4), (1.0, 4.0, 0.6),
                                                                   ((False, False), (True, False), (True, True))):
                c1k = C1_CONST if lay['c1'] is None else None
                prog, gprs = E.program(lay, cm, am, gain, c1k, premult=premult, additive=additive)
                lines = disasm(prog)
                worst = 0.0
                for _ in range(40):
                    c0 = [rnd.uniform(0, 1.5) for _ in range(3)] + [rnd.uniform(0, 1)]
                    c1 = [rnd.uniform(0, 1.5) for _ in range(4)]
                    vc = [rnd.uniform(0, 1) for _ in range(4)] if lay['vc'] is not None else None
                    texel = [rnd.uniform(0, 1) for _ in range(4)]
                    uv = [rnd.uniform(0, 1) for _ in range(4)]
                    hdr = [rnd.uniform(0.5, 2), 0, 0, rnd.uniform(0, 0.1)]
                    if c1k:
                        c1 = list(c1k) + [0.0]
                    regs = {'R%d' % lay['c0']: list(c0), 'R%d' % lay['uv'][0]: list(uv)}
                    if not c1k:
                        regs['R%d' % lay['c1']] = list(c1)
                    if vc is not None:
                        regs['R%d' % lay['vc']] = list(vc)
                    seen = []

                    def tex(u, v, k=0):
                        seen.append((u, v))
                        return texel
                    got = run(lines, regs, {8: hdr}, tex)
                    want = expected(cm, am, gain, c0, c1, texel, vc, hdr, premult=premult, additive=additive)
                    k = (0, 1) if lay['uv'][1] == 'xy' else (2, 3)
                    if seen != [(uv[k[0]], uv[k[1]])]:
                        worst = float('inf')
                    worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
                check(worst < 1e-5 and gprs == lay['regs'] + 2,
                      '%s colour %d alpha %d x %g%s: max error %.2g (%d GPRs)' % (
                          name, cm, am, gain, (', premultiplied, added' if additive else ', premultiplied')
                          if premult else '', worst, gprs))


def test_two():
    """two-texture layouts: each texture sampled from its own coordinates, combined per blend"""
    rnd = random.Random(2)
    for name, lay in TWO.items():
        for cm in range(4):
            for am in (0, 1):
                for blend in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    prog, gprs = E.program(lay, cm, am, 2.0, None, blend)
                    lines = disasm(prog)
                    worst = 0.0
                    for _ in range(30):
                        c0 = [rnd.uniform(0, 1.5) for _ in range(3)] + [rnd.uniform(0, 1)]
                        c1 = [rnd.uniform(0, 1.5) for _ in range(4)]
                        vc = [rnd.uniform(0, 1) for _ in range(4)] if lay['vc'] is not None else None
                        texels = [[rnd.uniform(0, 1) for _ in range(4)] for _ in range(2)]
                        uv = [rnd.uniform(0, 1) for _ in range(4)]
                        hdr = [rnd.uniform(0.5, 2), 0, 0, rnd.uniform(0, 0.1)]
                        regs = {'R%d' % lay['c0']: list(c0), 'R%d' % lay['c1']: list(c1), 'R%d' % lay['uv'][0]: list(uv)}
                        if vc is not None:
                            regs['R%d' % lay['vc']] = list(vc)
                        seen = []

                        def tex(u, v, k):
                            seen.append((k, u, v))
                            return texels[k]
                        got = run(lines, regs, {8: hdr}, tex)
                        want = expected(cm, am, 2.0, c0, c1, texels[0], vc, hdr, texels[1], blend)
                        if sorted(seen) != [(0, uv[0], uv[1]), (1, uv[2], uv[3])]:
                            worst = float('inf')
                        worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
                    check(worst < 1e-5 and gprs == lay['regs'] + 3,
                          '%s colour %d alpha %d blend %s: max error %.2g (%d GPRs)' % (name, cm, am, blend, worst, gprs))


C0_CONST = (0.9, 0.25, 1.5)


def test_dissolve():
    """Ultimate's custom shader 8: alpha x clamp((mask - threshold) / width), the threshold colour 1's
    red (colour 1 constant) or colour 0's (colour 0's rgb constant, its alpha the register's)"""
    rnd = random.Random(3)
    for (name, lay), by in [(x, b) for x in list(LAYOUTS.items())[:2] for b in (1, 0)]:
        for cm in range(4):
            for am in (0, 1):
                for width in (0.05, 0.3):
                    prog, gprs = E.program(lay, cm, am, 2.0, C1_CONST if by else None, (0, 0), width,
                                           None if by else C0_CONST)
                    lines = disasm(prog)
                    worst = 0.0
                    for _ in range(40):
                        c0 = [rnd.uniform(0, 1.5) for _ in range(3)] + [rnd.uniform(0, 1)]
                        thr = rnd.uniform(0, 1)
                        vc = [rnd.uniform(0, 1) for _ in range(4)] if lay['vc'] is not None else None
                        g = rnd.uniform(0, 1)
                        texel = [g, rnd.uniform(0, 1), g, rnd.uniform(0, 1)]
                        uv = [rnd.uniform(0, 1) for _ in range(4)]
                        hdr = [rnd.uniform(0.5, 2), 0, 0, rnd.uniform(0, 0.1)]
                        c1 = [rnd.uniform(0, 1.5) for _ in range(3)] + [0.9]
                        if by:
                            regs = {'R%d' % lay['c0']: list(c0), 'R%d' % lay['c1']: [thr, 0.7, 0.2, 0.9]}
                            c0w, c1w = c0, list(C1_CONST) + [0.0]
                        else:
                            regs = {'R%d' % lay['c0']: [thr, 0.4, 0.1, c0[3]], 'R%d' % lay['c1']: list(c1)}
                            c0w, c1w = list(C0_CONST) + [c0[3]], c1
                        regs['R%d' % lay['uv'][0]] = list(uv)
                        if vc is not None:
                            regs['R%d' % lay['vc']] = list(vc)
                        got = run(lines, regs, {8: hdr}, lambda u, v, k=0: texel)
                        want = expected(cm, am, 2.0, c0w, c1w, texel, vc, hdr, dissolve=(width, thr))
                        worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
                    check(worst < 1e-5 and gprs == lay['regs'] + 3,
                          '%s colour %d alpha %d dissolve %g by colour %d: max error %.2g (%d GPRs)' % (
                              name, cm, am, width, by, worst, gprs))


def test_distort():
    """Ultimate's shader_type 2: texture 1 sampled first, texture 0 at uv + (2 t1.x - 1, 2 t1.w - 1) x
    (sx, sy), texture 1 not blended in; a three-texture layout's texture 2 still is"""
    rnd = random.Random(4)
    three = dict(list(TWO.values())[0], regs=4, uv2=(3, 'xy'), sems=[0, 1, 9, 11])
    for name, lay in list(TWO.items()) + [('quad, three textures (0, 1, 9, 11)', three)]:
        for cm in range(4):
            for am in (0, 1):
                for warp in ((0.05, 0.06), (0.0, 0.55)):
                    blend2 = (1, 0) if 'uv2' in lay else (0, 0)
                    prog, gprs = E.program(lay, cm, am, 2.0, None, (0, 0), None, None, blend2, False, warp)
                    lines = disasm(prog)
                    worst = 0.0
                    for _ in range(30):
                        c0 = [rnd.uniform(0, 1.5) for _ in range(3)] + [rnd.uniform(0, 1)]
                        c1 = [rnd.uniform(0, 1.5) for _ in range(4)]
                        vc = [rnd.uniform(0, 1) for _ in range(4)] if lay['vc'] is not None else None
                        texels = [[rnd.uniform(0, 1) for _ in range(4)] for _ in range(3)]
                        uv = [rnd.uniform(0, 1) for _ in range(4)]
                        uv2 = [rnd.uniform(0, 1) for _ in range(4)]
                        hdr = [rnd.uniform(0.5, 2), 0, 0, rnd.uniform(0, 0.1)]
                        regs = {'R%d' % lay['c0']: list(c0), 'R%d' % lay['c1']: list(c1), 'R%d' % lay['uv'][0]: list(uv)}
                        if 'uv2' in lay:
                            regs['R%d' % lay['uv2'][0]] = list(uv2)
                        if vc is not None:
                            regs['R%d' % lay['vc']] = list(vc)
                        seen = []

                        def tex(u, v, k):
                            seen.append((k, u, v))
                            return texels[k]
                        got = run(lines, regs, {8: hdr}, tex)
                        moved = (uv[0] + (2 * texels[1][0] - 1) * warp[0], uv[1] + (2 * texels[1][3] - 1) * warp[1])
                        want = expected(cm, am, 2.0, c0, c1, texels[0], vc, hdr,
                                        texels[2] if 'uv2' in lay else None, blend2)
                        order = [(1, uv[2], uv[3]), (0,) + moved] + ([(2, uv2[0], uv2[1])] if 'uv2' in lay else [])
                        if len(seen) != len(order) or any(a[0] != b[0] or max(abs(x - y) for x, y in zip(a[1:], b[1:])) > 1e-5
                                                          for a, b in zip(seen, order)):
                            worst = float('inf')
                        worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
                    check(worst < 1e-5 and gprs == lay['regs'] + (4 if 'uv2' in lay else 3),
                          '%s colour %d alpha %d distort %s: max error %.2g (%d GPRs)' % (name, cm, am, warp, worst, gprs))


def test_bank(path):
    """every shader in the bank whose pixel program is one of ours (rebuilt from its layout, colour /
    alpha mode and gain literal: the same bytes)"""
    import ptcl
    p = ptcl.Ptcl(open(path, 'rb').read())
    own = other = 0
    for i in range(p.shader_count()):
        b = bytes(p.shader_binary(i))
        lay = E.layout_of(b)
        if lay is None:
            other += 1
            continue
        prog = [b[o:o + s] for t, _h, o, s in E.gsh_blocks(b, 0) if t == E.PS_PROGRAM][0]
        gains = {1.0} | {struct.unpack('>f', struct.pack('>I', int(m, 16)))[0]
                         for m in re.findall(r'MUL\s+R\d+\.w, R\d+\.w, \((0x[0-9A-F]+)', '\n'.join(disasm(prog)))}
        blends = ((0, 0), (1, 0), (0, 1), (1, 1)) if 'uv1' in lay else ((0, 0),)
        if any(E.program(lay, cm, am, g, None, bl)[0] == prog for cm in range(4) for am in (0, 1) for g in gains
               for bl in blends):
            own += 1
        else:
            other += 1
    check(own > 0, '%s: %d own pixel programs, %d other shaders' % (os.path.basename(path), own, other))
    check(not p.validate(), 'validates')


if __name__ == '__main__':
    test_variants()
    test_two()
    test_dissolve()
    test_distort()
    if len(sys.argv) > 1:
        test_bank(sys.argv[1])
    print('%d failure(s)' % len(FAILS))
    sys.exit(1 if FAILS else 0)
