#!/usr/bin/env python3
"""A Latte (R600-family) pixel program run over many pixels at once (numpy), from its latte-dis
disassembly: what Smash 4 draws for a converted effect part, for tools/fx_render.py (stage 2).

  prog = Program(shader_binary)            # a GX2 vertex + pixel binary (Ptcl.shader_binary)
  rgba = prog.run(inputs, consts, sample)  # inputs {semantic: [4, n]}, consts {index: (4,)},
                                           # sample(slot, u [n], v [n]) -> [4, n]

The inputs are the program's interpolated attributes by GX2 semantic (the pixel header's input
controls, eft_pixel.INPUT_CNTL: 0 colour 0, 1 colour 1, 6 a mesh's vertex colour, 9 / 10 the UVs);
consts the kcache banks' vec4s (KC0 [i] as consts[i], KC1 [i] as consts[('KC1', i)]) (CB9 [8] u_nwHdrRange on eft's programs, CB4 [0] on the distortion
pass's). An ALU group reads before it writes; PV<n> / PS<n> are group n's vector / trans results.
Ops: MOV, MUL(_IEEE), ADD, MULADD(_IEEE), MAX, MIN, DOT4(_IEEE), RECIP(_IEEE), RECIPSQRT(_IEEE),
SQRT(_IEEE), FRACT, FLOOR, SETGT / SETGE / SETE / SETNE, CNDGT / CNDGE / CNDE, KILLGT / KILLGE (a
mask: killed pixels come out with alpha 0); others raise NotImplementedError (the caller falls back).
"""
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eft_pixel  # noqa: E402

CH = 'xyzw'


def disassemble(binary):
    return [ln for ln in eft_pixel.disassemble(bytes(binary)).splitlines() if ln.strip()]


def semantics(binary):
    """the pixel program's inputs in register order: [GX2 semantic]"""
    w = eft_pixel.header_words(bytes(binary), eft_pixel.PS_HEADER)
    n = w[eft_pixel.NUM_INPUTS]
    return [w[eft_pixel.INPUT_CNTL + i] & 0xFF for i in range(n)]


def _lit(tok):
    m = re.fullmatch(r'\(0x[0-9A-Fa-f]+,\s*(-?[\d.eE+-]+)\)', tok)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r'(-?\d+(?:\.\d+)?)f', tok)
    if m:
        return float(m.group(1))
    return None


class Program:
    def __init__(self, binary):
        self.lines = disassemble(binary)
        self.sems = semantics(binary)
        self.ops = self._parse()

    def _parse(self):
        ops = []                 # ('alu', [(slot, op, dst, srcs, clamp)]) / ('tex', ...) / ('out', reg)
        group = None
        for line in self.lines:
            m = re.match(r'\s*(\d+\s+)?([xyzwt]):\s+(\w+)\s+(.*)', line)
            if m:
                if m.group(1) or group is None:
                    group = []
                    # PV<n> / PS<n> name the group by latte-dis's instruction counter (TEX ones count)
                    ops.append(('alu', group, int(m.group(1)) if m.group(1) else None))
                text = re.sub(r'\s+(VEC|SCL)_\d{3}\b', '', m.group(4).rstrip())
                clamp = text.endswith('CLAMP')
                text = re.sub(r'\s+CLAMP$', '', text)
                args = [a.strip() for a in re.split(r',\s*(?![^()]*\))', text)]
                group.append((m.group(2), m.group(3), args[0], args[1:], clamp))
                continue
            group = None
            m = re.match(r'\s*\d+\s+SAMPLE\w*\s+(R\d+)\.([xyzw01_]{4}),\s+(R\d+)\.([xyzw01_]{4}),\s+t(\d+),\s+s(\d+)', line)
            if m:
                ops.append(('tex', m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))))
                continue
            if 'SAMPLE' in line or 'FETCH' in line:
                raise NotImplementedError(line.strip())
            m = re.match(r'\s*\d+\s+EXP_DONE: PIX0, (R\d+)\.xyzw', line)
            if m:
                ops.append(('out', m.group(1)))
        return ops

    def run(self, inputs, consts, sample):
        n = len(next(iter(inputs.values()))[0]) if inputs else 1
        regs = {}
        for i, sem in enumerate(self.sems):
            regs['R%d' % i] = np.array(inputs.get(sem, np.ones((4, n))), dtype=np.float64).reshape(4, n).copy()
        get = lambda r: regs.setdefault(r, np.zeros((4, n)))    # noqa: E731
        pv, ps = {}, {}
        killed = np.zeros(n, bool)

        def src(tok, gi):
            neg = tok.startswith('-')
            tok = tok[1:] if neg else tok
            ab = tok.startswith('|') and tok.endswith('|')
            tok = tok.strip('|')
            v = _lit(tok)
            if v is None:
                m = re.fullmatch(r'(R\d+|KC([01])\[(\d+)\]|PV(\d+))\.([xyzw])', tok)
                m2 = re.fullmatch(r'PS(\d+)', tok)
                if m2:
                    v = ps[int(m2.group(1))]
                elif not m:
                    raise NotImplementedError('operand ' + tok)
                elif m.group(2) is not None:      # KC0[i] (consts[i]), KC1[i] (consts[('KC1', i)])
                    key = int(m.group(3)) if m.group(2) == '0' else ('KC1', int(m.group(3)))
                    v = float(np.asarray(consts.get(key, (0, 0, 0, 0)))[CH.index(m.group(5))])
                elif m.group(4) is not None:
                    v = pv[int(m.group(4))][CH.index(m.group(5))]
                else:
                    v = get(m.group(1))[CH.index(m.group(5))]
            v = np.abs(v) if ab else v
            return -v if neg else v
        gi = 0
        out = None
        for op in self.ops:
            if op[0] == 'tex':
                _k, dst, dsel, sreg, ssel, slot = op
                s = get(sreg)
                coord = [s[CH.index(c)] if c in CH else np.full(n, float(c == '1')) for c in ssel]
                t = np.asarray(sample(slot, coord[0], coord[1]), dtype=np.float64).reshape(4, n)
                d = get(dst)
                new = d.copy()
                for i, c in enumerate(dsel):
                    if c in CH:
                        new[i] = t[CH.index(c)]
                    elif c in '01':
                        new[i] = float(c)
                regs[dst] = new
                continue
            if op[0] == 'out':
                out = get(op[1]).copy()
                continue
            group = op[1]
            gi = op[2] if op[2] is not None else gi + 1
            results, writes = {}, []
            dots = [g for g in group if g[1].startswith('DOT4')]
            dot = None
            if dots:
                dot = sum(src(g[3][0], gi) * src(g[3][1], gi) for g in dots)
            for slot, name, dst, srcs, clamp in group:
                a = [src(x, gi) for x in srcs]
                base = name.replace('_IEEE', '').replace('_DX10', '').replace('_INT', '')
                if base.startswith('DOT4'):
                    v = dot
                elif base == 'MOV':
                    v = a[0]
                elif base == 'MUL':
                    v = a[0] * a[1]
                elif base == 'ADD':
                    v = a[0] + a[1]
                elif base in ('MULADD', 'MULADD_M2', 'MULADD_D2'):
                    v = a[0] * a[1] + a[2]
                elif base == 'MAX':
                    v = np.maximum(a[0], a[1])
                elif base == 'MIN':
                    v = np.minimum(a[0], a[1])
                elif base == 'RECIP':
                    v = 1.0 / np.where(np.abs(a[0]) < 1e-30, 1e-30, a[0])
                elif base == 'RECIPSQRT':
                    v = 1.0 / np.sqrt(np.maximum(np.abs(a[0]), 1e-30))
                elif base == 'SQRT':
                    v = np.sqrt(np.maximum(a[0], 0))
                elif base == 'FRACT':
                    v = a[0] - np.floor(a[0])
                elif base == 'RNDNE':
                    v = np.round(a[0])
                elif base == 'TRUNC':
                    v = np.trunc(a[0])
                elif base == 'FLOOR':
                    v = np.floor(a[0])
                elif base in ('SETGT', 'SETGE', 'SETE', 'SETNE'):
                    f = {'SETGT': np.greater, 'SETGE': np.greater_equal, 'SETE': np.equal, 'SETNE': np.not_equal}[base]
                    v = f(a[0], a[1]).astype(np.float64)
                elif base in ('CNDGT', 'CNDGE', 'CNDE'):
                    f = {'CNDGT': np.greater, 'CNDGE': np.greater_equal, 'CNDE': np.equal}[base]
                    v = np.where(f(a[0], 0), a[1], a[2])
                elif base in ('KILLGT', 'KILLGE'):
                    f = np.greater if base == 'KILLGT' else np.greater_equal
                    killed |= np.broadcast_to(f(a[0], a[1]), (n,))
                    v = np.zeros(n)
                else:
                    raise NotImplementedError(name)
                v = np.broadcast_to(np.asarray(v, dtype=np.float64), (n,)).copy()
                if clamp:
                    v = np.clip(v, 0, 1)
                results[slot] = v
                if dst != '____':
                    r, c = dst.split('.')
                    writes.append((r, CH.index(c), v))
            for r, c, v in writes:
                get(r)[c] = v
            pv[gi] = [results.get(c, np.zeros(n)) for c in CH]
            ps[gi] = results.get('t', np.zeros(n))
        if out is None:
            raise NotImplementedError('no EXP_DONE')
        out[3] = np.where(killed, 0.0, out[3])
        return out
