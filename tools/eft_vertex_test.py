#!/usr/bin/env python3
"""Checks eft_vertex's grafts: the slot-1 UV clause's arithmetic against eft's formula (a small
interpreter for the operations it uses), and that latte-asm takes it."""
import math
import os
import random
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eft_vertex  # noqa: E402

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


def _bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0] if isinstance(v, float) else v & 0xFFFFFFFF


def _flt(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0] if isinstance(v, int) else v


INT_OPS = {'AND_INT', 'OR_INT', 'SETE_INT', 'SETNE_INT', 'SETGT_INT', 'SETGE_INT', 'CNDE_INT', 'CNDGT_INT',
           'CNDGE_INT', 'ADD_INT', 'INT_TO_FLT', 'LSHL_INT', 'LSHR_INT', 'MOV'}


def run_clause(text, gpr, cbs):
    """interpret a disassembled ALU clause (latte-dis text: VLIW groups, PV / PS, literals, KCACHE):
    gpr {n: [4 values]} (floats or 32-bit ints, kept as bits where an int op wrote them), cbs
    {cb: {vec4: [4 floats or ints]}}"""
    kc = {}
    m = re.search(r'KCACHE0\(CB(\d+):(\d+)-\d+\)', text)
    if m:
        kc[0] = (int(m.group(1)), int(m.group(2)))
    m = re.search(r'KCACHE1\(CB(\d+):(\d+)-\d+\)', text)
    if m:
        kc[1] = (int(m.group(1)), int(m.group(2)))
    pv, ps = [0.0] * 4, 0.0
    groups, cur = [], None
    for l in text.splitlines():
        m = re.match(r'^\s+(?:(\d+)\s+)?([xyzwt]): (\S+)\s+(.*)$', l)
        if not m:
            continue
        if m.group(1) is not None:
            cur = []
            groups.append(cur)
        cur.append((m.group(2), m.group(3), m.group(4)))
    for g in groups:
        writes, npv, nps = [], list(pv), ps
        for slot, op, rest in g:
            rest = re.sub(r'\s+(SCL_\d+|VEC_\d+|UPDATE_EXEC_MASK|UPDATE_PRED|CLAMP)', '', rest)
            args = [a.strip() for a in re.split(r',\s*(?![^()]*\))', rest)]
            dst, srcs = args[0], args[1:]
            omod = 1.0
            mo = re.match(r'(\w+)([*/])(\d)', op)
            if mo:
                op, omod = mo.group(1), (float(mo.group(3)) if mo.group(2) == '*' else 1 / float(mo.group(3)))
            def val(s):
                neg = s.startswith('-')
                s = s.lstrip('-')
                ab = s.startswith('|')
                s = s.strip('|')
                if s.startswith('('):
                    v = int(re.match(r'\((0x[0-9A-Fa-f]+)', s).group(1), 16)
                elif re.match(r'R\d+\.[xyzw]$', s):
                    r, c = s[1:].split('.')
                    v = gpr.get(int(r), [0.0] * 4)['xyzw'.index(c)]
                elif s.startswith('PV'):
                    v = pv['xyzw'.index(s[-1])]
                elif s.startswith('PS'):
                    v = ps
                elif s.startswith('KC'):
                    mk = re.match(r'KC(\d)\[(\d+)\]\.([xyzw])', s)
                    cb, base = kc[int(mk.group(1))]
                    v = cbs[cb].get(base + int(mk.group(2)), [0.0] * 4)['xyzw'.index(mk.group(3))]
                elif s.endswith('f'):
                    v = float(s[:-1])
                else:
                    v = int(s)
                if op in INT_OPS - {'MOV', 'INT_TO_FLT'}:
                    v = _bits(v)
                    return (-v) & 0xFFFFFFFF if neg else v
                v = _flt(v) if op != 'MOV' else v
                if ab:
                    v = abs(v)
                return -v if neg and isinstance(v, float) else (v ^ 0x80000000 if neg else v)
            a = [val(s) for s in srcs]
            if op == 'DOT4' or op == 'DOT4_IEEE':
                res = ('dot', a[0] * a[1])
            else:
                res = {'MOV': lambda: a[0], 'ADD': lambda: a[0] + a[1], 'MUL': lambda: a[0] * a[1],
                       'MUL_IEEE': lambda: a[0] * a[1], 'MULADD': lambda: a[0] * a[1] + a[2],
                       'MULADD_IEEE': lambda: a[0] * a[1] + a[2], 'MAX': lambda: max(a[0], a[1]),
                       'MIN': lambda: min(a[0], a[1]), 'FRACT': lambda: a[0] - math.floor(a[0]),
                       'TRUNC': lambda: float(math.trunc(a[0])), 'FLOOR': lambda: float(math.floor(a[0])),
                       'SIN': lambda: math.sin(2 * math.pi * a[0]), 'COS': lambda: math.cos(2 * math.pi * a[0]),
                       'RECIP_IEEE': lambda: (1 / a[0]) if a[0] else float('inf'),
                       'RECIPSQRT_IEEE': lambda: 1 / math.sqrt(a[0]) if a[0] > 0 else float('inf'),
                       'FLT_TO_INT': lambda: int(math.trunc(a[0])) & 0xFFFFFFFF,
                       'INT_TO_FLT': lambda: float(struct.unpack('<i', struct.pack('<I', _bits(a[0])))[0]),
                       'SETE_INT': lambda: 0xFFFFFFFF if a[0] == a[1] else 0,
                       'SETNE_INT': lambda: 0xFFFFFFFF if a[0] != a[1] else 0,
                       'AND_INT': lambda: a[0] & a[1], 'OR_INT': lambda: a[0] | a[1],
                       'ADD_INT': lambda: (a[0] + a[1]) & 0xFFFFFFFF,
                       'CNDE_INT': lambda: a[1] if a[0] == 0 else a[2],
                       'CNDGT_INT': lambda: a[1] if struct.unpack('<i', struct.pack('<I', a[0]))[0] > 0 else a[2],
                       'CNDE': lambda: a[1] if a[0] == 0.0 else a[2],
                       'CNDGT': lambda: a[1] if a[0] > 0.0 else a[2],
                       'CNDGE': lambda: a[1] if a[0] >= 0.0 else a[2],
                       'SETGT': lambda: 1.0 if a[0] > a[1] else 0.0, 'SETGE': lambda: 1.0 if a[0] >= a[1] else 0.0,
                       'SETE': lambda: 1.0 if a[0] == a[1] else 0.0,
                       'SETGT_DX10': lambda: 0xFFFFFFFF if a[0] > a[1] else 0,
                       'SETGE_DX10': lambda: 0xFFFFFFFF if a[0] >= a[1] else 0,
                       'SETE_DX10': lambda: 0xFFFFFFFF if a[0] == a[1] else 0,
                       'PRED_SETGT': lambda: 0.0, 'PRED_SETE_INT': lambda: 0, 'PRED_SETNE_INT': lambda: 0,
                       }[op]()
                if isinstance(res, float):
                    res *= omod
            writes.append((slot, dst, res))
        dots = [r[1] for _s, _d, r in writes if isinstance(r, tuple)]
        for slot, dst, res in writes:
            if isinstance(res, tuple):
                res = sum(dots) * 1.0
            if slot == 't':
                nps = res
            else:
                npv['xyzw'.index(slot)] = res
            if dst != '____':
                r, c = dst[1:].split('.')
                gpr.setdefault(int(r), [0.0] * 4)['xyzw'.index(c)] = res
        pv, ps = npv, nps
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


def test_assembles():
    """latte-asm takes each variant: its disassembly has each line's operation and destination, in
    one clause of at most 128 slots"""
    import subprocess
    import tempfile
    fails = 0
    for mesh in (True, False):
        lines = eft_vertex.uv1_lines(20, 21, 5, 22, 23, 24, 25, mesh)
        cf, code = eft_vertex._alu(lines, (eft_vertex.CB_STATIC, 0, 15))
        if len(code) > 8 * 128:
            print('FAIL clause size', mesh, len(code) // 8)
            fails += 1
        w1 = (cf[1] & ~(0x7F << 18)) | ((len(code) // 8 - 1) << 18)
        prog = struct.pack('<II', cf[0] | 2, w1) + struct.pack('<II', 0x0000C000, 0x94200688) + code
        dis = os.path.join(HERE, 'latte_dis', 'latte-dis')
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(prog)
        try:
            text = subprocess.run([dis, f.name, '0', str(len(prog))], capture_output=True, text=True).stdout
        finally:
            os.unlink(f.name)
        got = re.findall(r'^\s+(?:\d+\s+)?([xyzwt]): (\w+)\s+(R\d+\.[xyzw])', text, re.M)
        want = [re.match(r'([xyzwt]): (\w+)\s+(R\d+\.[xyzw])', l).groups() for l in lines]
        if got != want:
            print('FAIL assemble', mesh, len(got), len(want), [(g, w) for g, w in zip(got, want) if g != w][:5])
            fails += 1
    return fails


if __name__ == '__main__':
    n = test_uv1() + test_assembles()
    print('%d failure(s)' % n)
    sys.exit(1 if n else 0)
