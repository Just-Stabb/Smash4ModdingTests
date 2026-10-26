#!/usr/bin/env python3
"""Checks eft_vertex's grafts: the slot-1 / 2 UV clauses' arithmetic against eft's formula (a small
interpreter for the operations they use), the rotation clause's as latte-asm assembles it
(latte_interp), and that latte-asm takes them."""
import math
import os
import random
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eft_vertex  # noqa: E402
from latte_interp import run_clause  # noqa: E402,F401

f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]


def run(lines, gpr, kc):
    """interpret one-operation groups: GPRs gpr {n: [x, y, z, w]} (floats, or ints for the int ops)"""
    def src(s, ints):
        neg = s.startswith('-')
        s = s.lstrip('-')
        m = re.match(r'R(\d+)\.([xyzw])$', s)
        if m:
            v = gpr[int(m.group(1))]['xyzw'.index(m.group(2))]
        elif s.startswith('KC0['):
            m = re.match(r'KC0\[(\d+)\]\.([xyzw])$', s)
            v = kc[int(m.group(1))]['xyzw'.index(m.group(2))]
        elif s.startswith('('):
            h = int(re.match(r'\((0x[0-9A-Fa-f]+)', s).group(1), 16)
            v = h if ints else struct.unpack('<f', struct.pack('<I', h))[0]
        else:
            # (latte-asm reads a bare number as a float: 1 is 0x3F800000)
            v = float(s.rstrip('f'))
            v = struct.unpack('<I', struct.pack('<f', v))[0] if ints else v
        return -v if neg else v
    for l in lines:
        m = re.match(r'([xyzwt]): (\w+)\s+R(\d+)\.([xyzw]), (.*)$', l)
        op, dst, ch = m.group(2), int(m.group(3)), 'xyzw'.index(m.group(4))
        ints = op in ('SETE_INT', 'CNDE_INT')
        a = [src(s.strip(), ints) for s in re.split(r',\s*(?![^()]*\))', m.group(5))]
        v = {'MOV': lambda: a[0], 'ADD': lambda: a[0] + a[1], 'MUL': lambda: a[0] * a[1],
             'MULADD': lambda: a[0] * a[1] + a[2], 'FRACT': lambda: a[0] - math.floor(a[0]),
             'SIN': lambda: math.sin(2 * math.pi * a[0]), 'COS': lambda: math.cos(2 * math.pi * a[0]),
             'FLT_TO_INT': lambda: int(a[0]), 'SETE_INT': lambda: -1 if a[0] == a[1] else 0,
             'RECIP_IEEE': lambda: 1 / a[0],
             'CNDE_INT': lambda: a[1] if a[0] == 0 else a[2]}[op]()
        gpr.setdefault(dst, [0.0] * 4)[ch] = f32(v) if isinstance(v, float) else v
    return gpr


def _common(t, rnd, pm, chan):
    pick = lambda order: rnd['xyz'.index(order[chan])]
    a, b, su, sv, rr = (pick(o) for o in ('xyz', 'yzx', 'xyx', 'yzy', 'zxy'))
    pm0, pm1, pm2, pm3 = pm
    return (t * pm0[0] + pm0[2] + pm1[0] * (1 - 2 * a), t * pm0[1] + pm0[3] + pm1[1] * (1 - 2 * b),
            t * pm1[2] + pm2[0] + pm2[2] * (1 - 2 * su), t * pm1[3] + pm2[1] + pm2[3] * (1 - 2 * sv),
            -(t * pm3[0] + pm3[1] + pm3[2] * (1 - 2 * rr)))


def reference(t, rnd, zw, pm, chan, rep, mesh):
    """eft's slot UV transform from the still UV zw (x repeat). Fitted against vanilla clauses run
    through run_clause: Bayonetta's ring1 (mesh; worst 2.3e-5) and the Bunner smoke quad (9e-6),
    random parameters, repeats 0.5 - 2"""
    shu, shv, scu, scv, ang = _common(t, rnd, pm, chan)
    c, s = math.cos(ang), math.sin(ang)
    if mesh:
        u, v = zw[0] - 0.5, zw[1] - 0.5
        return scu * (c * u - s * v) - shu + 0.5, scv * (c * v + s * u) - shv + 0.5
    x, y = zw[0] / rep[0] - 0.5, 0.5 - zw[1] / rep[1]
    ru, rv = c * x - s * y, c * y + s * x
    return ru * (rep[0] - 1 + scu) + 0.5 * rep[0] - shu, rv * (1 - scv - rep[1]) + 0.5 * rep[1] - shv


def test_uv1():
    rng = random.Random(1)
    fails = 0
    for k in range(400):
        chan, mesh = k % 3, k % 2 == 0
        pm = [[rng.uniform(-2, 2) for _ in range(4)] for _ in range(4)]
        pm[3][3] = float(chan)
        rep = [rng.choice([0.5, 1.0, 2.0]), rng.choice([1.0, 2.0])]
        kc = {6 + i: pm[i] for i in range(4)}
        kc[10] = rep + [1.0, 1.0]
        t, rnd = rng.uniform(0, 60), [rng.random() for _ in range(4)]
        zw = [rng.uniform(0, 2), rng.uniform(0, 2)]
        gpr = {20: [t, 0, 0, 0], 21: rnd, 5: [0.25, 0.75] + zw}
        out = run(eft_vertex.uv1_lines(20, 21, 5, 22, 23, 24, 25, mesh), gpr, kc)[22]
        want = reference(t, rnd, zw, pm, chan, rep, mesh)
        if abs(out[2] - want[0]) > 1e-3 * (1 + abs(want[0])) or abs(out[3] - want[1]) > 1e-3 * (1 + abs(want[1])) \
                or out[:2] != [0.25, 0.75]:
            fails += 1
            print('FAIL uv1', k, mesh, out, want)
    return fails


def test_uv2():
    """slot 2: its still UV from slot 1's (/ repeat 1 x repeat 2), then the transform on shtAnim2"""
    rng = random.Random(2)
    fails = 0
    for k in range(200):
        chan, mesh = k % 3, k % 2 == 0
        pm = [[rng.uniform(-2, 2) for _ in range(4)] for _ in range(4)]
        pm[3][3] = float(chan)
        rep1 = [rng.choice([0.5, 1.0, 2.0]), rng.choice([1.0, 2.0])]
        rep2 = [rng.choice([0.5, 1.0, 3.0]), rng.choice([1.0, 2.0])]
        kc = {11 + i: pm[i] for i in range(4)}
        kc[10], kc[15] = rep1 + [1.0, 1.0], rep2 + [1.0, 1.0]
        t, rnd = rng.uniform(0, 60), [rng.random() for _ in range(4)]
        base = [rng.uniform(0, 1), rng.uniform(0, 1)]
        gpr = {20: [t, 0, 0, 0], 21: rnd, 5: [0.25, 0.75, base[0] * rep1[0], base[1] * rep1[1]]}
        out = run(eft_vertex.uv2_lines(20, 21, 5, 22, 23, 24, 25, 26, mesh), gpr, kc)[22]
        want = reference(t, rnd, [base[0] * rep2[0], base[1] * rep2[1]], pm, chan, rep2, mesh)
        if abs(out[2] - want[0]) > 1e-3 * (1 + abs(want[0])) or abs(out[3] - want[1]) > 1e-3 * (1 + abs(want[1])):
            fails += 1
            print('FAIL uv2', k, mesh, out, want)
    return fails


def _disassembled(lines, kcache, kcache1=None):
    """latte-dis's text of an ALU clause latte-asm made of lines"""
    import subprocess
    import tempfile
    cf, code = eft_vertex._alu(lines, kcache, kcache1)
    w1 = (cf[1] & ~(0x7F << 18)) | ((len(code) // 8 - 1) << 18)
    prog = struct.pack('<II', cf[0] | 2, w1) + struct.pack('<II', 0x0000C000, 0x94200688) + code
    dis = os.path.join(HERE, 'latte_dis', 'latte-dis')
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(prog)
    try:
        text = subprocess.run([dis, f.name, '0', str(len(prog))], capture_output=True, text=True).stdout
    finally:
        os.unlink(f.name)
    return text, len(code)


def rotation(r):
    """eft's mesh rotation, R = Rx Rz Ry (fitted on Little Mac's Final program)"""
    cx, sx, cy, sy, cz, sz = math.cos(r[0]), math.sin(r[0]), math.cos(r[1]), math.sin(r[1]), math.cos(r[2]), math.sin(r[2])
    mul = lambda a, b: [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return mul(mul(rx, rz), ry)


def test_rot():
    """the rotation clause: pos' = S^-1 R S (pos + rotBasis) - rotBasis (rotBasis x / y; z scaled by
    x, or y under uboFlag 0x08000000), so the program's own S (pos' + rotBasis) is R S (pos + rotBasis)"""
    rng = random.Random(4)
    text, _n = _disassembled(eft_vertex.rot_lines(7, 9, 13, 14, 15, 16, 17),
                             (eft_vertex.CB_STATIC, 32, 47), (eft_vertex.CB_STATIC, 0, 15))
    fails = 0
    for k in range(300):
        pos = [rng.uniform(-5, 5) for _ in range(3)]
        scl = [rng.uniform(0.2, 3) for _ in range(3)]
        rot = [rng.uniform(-20, 20) for _ in range(3)]
        rb = [rng.uniform(-2, 2) for _ in range(2)]
        flag = eft_vertex.SCALE_Z_BY_Y if k % 2 else 0
        sz = scl[1] if flag else scl[0]
        cb2 = {0: [flag, 0, 0, 0], 32 + eft_vertex.ROT_BASIS: rb + [0.0, 0.0]}
        gpr = run_clause(text, {7: pos + [1.0], 9: scl + [0.0], 13: rot + [0.0]}, {2: cb2})
        q = [scl[0] * (pos[0] + rb[0]), scl[1] * (pos[1] + rb[1]), sz * pos[2]]
        R = rotation(rot)
        want = [sum(R[i][j] * q[j] for j in range(3)) for i in range(3)]
        got = [scl[0] * (gpr[7][0] + rb[0]), scl[1] * (gpr[7][1] + rb[1]), sz * gpr[7][2]]
        if any(abs(g - w) > 1e-3 * (1 + abs(w)) for g, w in zip(got, want)) or gpr[7][3] != 1.0:
            fails += 1
            print('FAIL rot', k, got, want)
    # a zero scale: the clamped reciprocal, taken back to 0 by the program's x 0 (no inf / nan)
    gpr = run_clause(text, {7: [1.0, 2.0, 3.0, 1.0], 9: [0.0, 0.0, 0.0, 0.0], 13: [0.3, 0.2, 0.1, 0.0]},
                     {2: {0: [0, 0, 0, 0], 36: [0.5, 0.5, 0, 0]}})
    if any(math.isinf(v) or math.isnan(v) for v in gpr[7][:3]):
        fails += 1
        print('FAIL rot at scale 0', gpr[7])
    return fails


def test_assembles():
    """latte-asm takes each variant: its disassembly has each line's operation and destination, in
    one clause of at most 128 slots"""
    fails = 0
    for mesh, lines in [(m, eft_vertex.uv1_lines(20, 21, 5, 22, 23, 24, 25, m)) for m in (True, False)] + \
            [(m, eft_vertex.uv2_lines(20, 21, 5, 22, 23, 24, 25, 26, m)) for m in (True, False)] + \
            [('rot', eft_vertex.rot_lines(7, 9, 13, 14, 15, 16, 17))]:
        text, size = _disassembled(lines, (eft_vertex.CB_STATIC, 0, 15))
        if size > 8 * 128:
            print('FAIL clause size', mesh, size // 8)
            fails += 1
        got = re.findall(r'^\s+(?:\d+\s+)?([xyzwt]): (\w+)\s+(R\d+\.[xyzw])', text, re.M)
        want = [re.match(r'([xyzwt]): (\w+)\s+(R\d+\.[xyzw])', l).groups() for l in lines]
        if got != want:
            print('FAIL assemble', mesh, len(got), len(want), [(g, w) for g, w in zip(got, want) if g != w][:5])
            fails += 1
    return fails


if __name__ == '__main__':
    n = test_uv1() + test_uv2() + test_rot() + test_assembles()
    print('%d failure(s)' % n)
    sys.exit(1 if n else 0)
