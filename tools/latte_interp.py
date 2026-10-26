#!/usr/bin/env python3
"""A small interpreter for Latte (R600-family) ALU clauses as latte-dis prints them: what an eft
vertex program works out, for checking grafts against vanilla code (tools/eft_vertex.py,
tools/eft_vertex_test.py). Floats are Python floats rounded to f32 per write; integer ops keep
32-bit patterns. Control flow is the caller's: clauses() splits a program's disassembly by CF
instruction."""
import math
import re
import struct

f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]


def _bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0] if isinstance(v, float) else v & 0xFFFFFFFF


def _flt(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0] if isinstance(v, int) else v


INT_OPS = {'AND_INT', 'OR_INT', 'XOR_INT', 'NOT_INT', 'SETE_INT', 'SETNE_INT', 'SETGT_INT', 'SETGE_INT',
           'SETGT_UINT', 'SETGE_UINT', 'CNDE_INT', 'CNDGT_INT', 'CNDGE_INT', 'ADD_INT', 'SUB_INT', 'MAX_INT',
           'MIN_INT', 'MULLO_INT', 'INT_TO_FLT', 'UINT_TO_FLT', 'LSHL_INT', 'LSHR_INT', 'ASHR_INT', 'MOV'}
_s32 = lambda v: struct.unpack('<i', struct.pack('<I', v & 0xFFFFFFFF))[0]


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
                       'MIN': lambda: min(a[0], a[1]), 'FRACT': lambda: a[0] - math.floor(a[0]) if math.isfinite(a[0]) else 0.0,
                       'TRUNC': lambda: float(math.trunc(a[0])) if math.isfinite(a[0]) else a[0],
                       'FLOOR': lambda: float(math.floor(a[0])) if math.isfinite(a[0]) else a[0],
                       'SIN': lambda: math.sin(2 * math.pi * a[0]), 'COS': lambda: math.cos(2 * math.pi * a[0]),
                       'RECIP_IEEE': lambda: (1 / a[0]) if a[0] else float('inf'),
                       'RECIP_CLAMPED': lambda: (1 / a[0]) if a[0] else 3.4028234663852886e38,
                       'RECIPSQRT_IEEE': lambda: 1 / math.sqrt(a[0]) if a[0] > 0 else float('inf'),
                       'FLT_TO_INT': lambda: int(math.trunc(a[0])) & 0xFFFFFFFF if math.isfinite(a[0]) else 0,
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
                       'SETNE': lambda: 1.0 if a[0] != a[1] else 0.0,
                       'SETNE_DX10': lambda: 0xFFFFFFFF if a[0] != a[1] else 0,
                       'SETGT_INT': lambda: 0xFFFFFFFF if _s32(a[0]) > _s32(a[1]) else 0,
                       'SETGE_INT': lambda: 0xFFFFFFFF if _s32(a[0]) >= _s32(a[1]) else 0,
                       'SETGT_UINT': lambda: 0xFFFFFFFF if a[0] > a[1] else 0,
                       'SETGE_UINT': lambda: 0xFFFFFFFF if a[0] >= a[1] else 0,
                       'CNDGE_INT': lambda: a[1] if _s32(a[0]) >= 0 else a[2],
                       'SUB_INT': lambda: (a[0] - a[1]) & 0xFFFFFFFF,
                       'MAX_INT': lambda: a[0] if _s32(a[0]) >= _s32(a[1]) else a[1],
                       'MIN_INT': lambda: a[0] if _s32(a[0]) <= _s32(a[1]) else a[1],
                       'MULLO_INT': lambda: (a[0] * a[1]) & 0xFFFFFFFF,
                       'XOR_INT': lambda: a[0] ^ a[1], 'NOT_INT': lambda: a[0] ^ 0xFFFFFFFF,
                       'LSHL_INT': lambda: (a[0] << (a[1] & 31)) & 0xFFFFFFFF, 'LSHR_INT': lambda: a[0] >> (a[1] & 31),
                       'ASHR_INT': lambda: (_s32(a[0]) >> (a[1] & 31)) & 0xFFFFFFFF,
                       'UINT_TO_FLT': lambda: float(a[0]),
                       'FLT_TO_UINT': lambda: int(math.trunc(a[0])) & 0xFFFFFFFF if math.isfinite(a[0]) and a[0] > 0 else 0,
                       'MAX_DX10': lambda: max(a[0], a[1]), 'MIN_DX10': lambda: min(a[0], a[1]),
                       'CEIL': lambda: float(math.ceil(a[0])) if math.isfinite(a[0]) else a[0],
                       'RNDNE': lambda: float(round(a[0])) if math.isfinite(a[0]) else a[0],
                       'SQRT_IEEE': lambda: math.sqrt(a[0]) if a[0] >= 0 else float('nan'),
                       'EXP_IEEE': lambda: 2.0 ** min(a[0], 128.0),
                       'LOG_IEEE': lambda: math.log2(a[0]) if a[0] > 0 else float('-inf'),
                       'LOG_CLAMPED': lambda: math.log2(a[0]) if a[0] > 0 else -3.4028234663852886e38,
                       'RECIP_FF': lambda: (1 / a[0]) if a[0] else 0.0,
                       'RECIPSQRT_CLAMPED': lambda: 1 / math.sqrt(a[0]) if a[0] > 0 else 3.4028234663852886e38,
                       'RECIPSQRT_FF': lambda: 1 / math.sqrt(a[0]) if a[0] > 0 else 0.0,
                       }[op]() if not op.startswith('PRED_') else 0      # (predicates: the caller's control flow)
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


def clauses(text):
    """[(CF index, its header line, its text)] of a disassembled program"""
    out = []
    for l in text.splitlines():
        m = re.match(r'^(\d+) (.*)$', l)
        if m:
            out.append([int(m.group(1)), m.group(2), [l]])
        elif out:
            out[-1][2].append(l)
    return [(i, h, '\n'.join(t)) for i, h, t in out]
