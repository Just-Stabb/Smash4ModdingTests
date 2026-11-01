#!/usr/bin/env python3
"""Smash 4's (eft's) vertex programs run on the CPU: a Latte (R600-family) program's latte-dis disassembly
turned into C++, compiled once (build/latte_exec/) and called from numpy.

  vs = VertexProgram(gx2_binary)          # Ptcl.shader_binary(i)
  vs.attributes   [names] in input-GPR order (R1 on)
  vs.blocks       {name: constant buffer}  (viewUniformBlock 1, emitterStaticUniformBlock 2, ...)
  vs.params       {PARAM n: GX2 semantic} (SPI_VS_OUT_ID)
  pos, params = vs.run(attrs [n, len(attributes), 4], cbs {buffer: float32 vec4 array}, vertex_ids)

One vertex at a time, the program's own control flow: R600 predication as a single lane (an active flag,
a stack of saved flags): ALU_PUSH_BEFORE saves the flag and runs its clause, PRED_SET* with
UPDATE_EXEC_MASK sets it for the clause's end; JUMP ADDR(a) [POP_CNT(k)] goes to a, popping k, when the
lane is inactive; ELSE flips it under its parent and jumps (popping) when that leaves it inactive;
ALU_POP_AFTER / ALU_POP2_AFTER / POP restore saved flags. An ALU group reads every source before any of
its writes; PV / PS are the previous group's results; KCACHEn(CBb:lo-hi) maps KCn[i] to buffer b's vec4
lo + i; FETCH ... bN reads buffer N - 128 at the index register's integer (vec4 units). Values are 32-bit
words: float ops on their float view, *_INT / FLT_TO_INT / INT_TO_FLT on the integer one, MUL / MULADD /
DOT4 the non-IEEE kind (0 x anything = 0), SIN / COS taking revolutions (period 1)."""
import ctypes
import hashlib
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eft_vertex  # noqa: E402

CACHE = os.path.join(ROOT, 'build', 'latte_exec')
NCB = 16
CB_VEC4 = 1024           # every constant buffer padded to this many vec4s
NPARAM = 8
CH = 'xyzw'

HEAD = r'''
#include <cstdint>
#include <cstring>
#include <cmath>
#include <cfloat>
typedef union { float f; uint32_t u; int32_t i; } W;
static inline W Wf(float f) { W w; w.f = f; return w; }
static inline W Wu(uint32_t u) { W w; w.u = u; return w; }
static inline W Wi(int32_t i) { W w; w.i = i; return w; }
static inline float mulx(float a, float b) { return (a == 0.0f || b == 0.0f) ? 0.0f : a * b; }
static inline float recip_c(float a) { float r = 1.0f / a; if (std::isinf(r)) r = r > 0 ? FLT_MAX : -FLT_MAX; return r; }
static inline float log_c(float a) { float r = std::log2(a); if (std::isinf(r)) r = r > 0 ? FLT_MAX : -FLT_MAX; return r; }
static inline int32_t f2i(float a) { if (std::isnan(a)) return 0; if (a >= 2147483647.0f) return 2147483647; if (a <= -2147483648.0f) return INT32_MIN; return (int32_t)std::trunc(a); }
static inline uint32_t f2u(float a) { if (std::isnan(a) || a <= 0) return 0; if (a >= 4294967295.0f) return 0xffffffffu; return (uint32_t)std::trunc(a); }
static const float TWO_PI = 6.28318530717958647692f;
'''


def _src(tok):
    """a source operand -> C expression giving a W"""
    neg = tok.startswith('-')
    t = tok[1:] if neg else tok
    ab = t.startswith('|') and t.endswith('|')
    t = t.strip('|')
    m = re.fullmatch(r'\(0x([0-9A-Fa-f]+),\s*[^)]*\)', t)
    if m:
        e = 'Wu(0x%sU)' % m.group(1)
    elif re.fullmatch(r'-?\d+\.\d+f', t):
        e = 'Wf(%s)' % t
    elif re.fullmatch(r'-?\d+', t):
        e = 'Wi(%s)' % t
    else:
        m = re.fullmatch(r'R(\d+)\.([xyzw])', t)
        m2 = re.fullmatch(r'KC([01])\[(\d+)\]\.([xyzw])', t)
        m3 = re.fullmatch(r'PV\d+\.([xyzw])', t)
        m4 = re.fullmatch(r'PS\d+', t)
        if m:
            e = 'R[%s][%d]' % (m.group(1), CH.index(m.group(2)))
        elif m2:
            e = 'KC%s[%d]' % (m2.group(1), 4 * int(m2.group(2)) + CH.index(m2.group(3)))
        elif m3:
            e = 'pv[%d]' % CH.index(m3.group(1))
        elif m4:
            e = 'ps'
        else:
            raise NotImplementedError('operand ' + tok)
    if ab:
        e = 'Wf(std::fabs(%s.f))' % e
    if neg:
        e = 'Wf(-(%s).f)' % e
    return e


FLOAT_BIN = {'ADD': '{a}.f + {b}.f', 'MUL': 'mulx({a}.f, {b}.f)', 'MUL_IEEE': '{a}.f * {b}.f',
             'MAX': 'std::fmax({a}.f, {b}.f)', 'MIN': 'std::fmin({a}.f, {b}.f)',
             'MAX_DX10': 'std::fmax({a}.f, {b}.f)', 'MIN_DX10': 'std::fmin({a}.f, {b}.f)'}
FLOAT_UN = {'FRACT': '{a}.f - std::floor({a}.f)', 'FLOOR': 'std::floor({a}.f)', 'TRUNC': 'std::trunc({a}.f)',
            'RNDNE': 'std::nearbyint({a}.f)', 'RECIP_IEEE': '1.0f / {a}.f', 'RECIP_CLAMPED': 'recip_c({a}.f)',
            'RECIP_FF': 'recip_c({a}.f)', 'RECIPSQRT_IEEE': '1.0f / std::sqrt({a}.f)',
            'RECIPSQRT_CLAMPED': 'recip_c(std::sqrt({a}.f))', 'RECIPSQRT_FF': 'recip_c(std::sqrt({a}.f))',
            'SQRT_IEEE': 'std::sqrt({a}.f)', 'LOG_IEEE': 'std::log2({a}.f)', 'LOG_CLAMPED': 'log_c({a}.f)',
            'EXP_IEEE': 'std::exp2({a}.f)', 'SIN': 'std::sin({a}.f * TWO_PI)', 'COS': 'std::cos({a}.f * TWO_PI)'}
CMP = {'E': '==', 'NE': '!=', 'GT': '>', 'GE': '>='}


def _op(name, a):
    """(C expression giving a W, is_float_result) of one ALU operation on source expressions a"""
    if name in FLOAT_BIN:
        return 'Wf(%s)' % FLOAT_BIN[name].format(a=a[0], b=a[1]), True
    if name in FLOAT_UN:
        return 'Wf(%s)' % FLOAT_UN[name].format(a=a[0]), True
    if name in ('MULADD', 'MULADD_M2', 'MULADD_M4', 'MULADD_D2'):
        k = {'MULADD': '', 'MULADD_M2': ' * 2.0f', 'MULADD_M4': ' * 4.0f', 'MULADD_D2': ' * 0.5f'}[name]
        return 'Wf((mulx(%s.f, %s.f) + %s.f)%s)' % (a[0], a[1], a[2], k), True
    if name == 'MULADD_IEEE':
        return 'Wf(%s.f * %s.f + %s.f)' % tuple(a), True
    if name == 'MOV':
        return a[0], True
    m = re.fullmatch(r'SET(E|NE|GT|GE)(_DX10)?', name)
    if m:
        c = '%s.f %s %s.f' % (a[0], CMP[m.group(1)], a[1])
        return ('Wu((%s) ? 0xffffffffU : 0U)' % c, False) if m.group(2) else ('Wf((%s) ? 1.0f : 0.0f)' % c, True)
    m = re.fullmatch(r'SET(E|NE|GT|GE)_(INT|UINT)', name)
    if m:
        f = 'i' if m.group(2) == 'INT' else 'u'
        return 'Wu((%s.%s %s %s.%s) ? 0xffffffffU : 0U)' % (a[0], f, CMP[m.group(1)], a[1], f), False
    m = re.fullmatch(r'CND(E|GT|GE)(_INT)?', name)
    if m:
        f = 'i' if m.group(2) else 'f'
        z = '0' if m.group(2) else '0.0f'
        return '((%s.%s %s %s) ? %s : %s)' % (a[0], f, CMP[m.group(1)], z, a[1], a[2]), not m.group(2)
    ints = {'AND_INT': '{a}.u & {b}.u', 'OR_INT': '{a}.u | {b}.u', 'XOR_INT': '{a}.u ^ {b}.u',
            'ADD_INT': '{a}.u + {b}.u', 'SUB_INT': '{a}.u - {b}.u', 'LSHL_INT': '{a}.u << ({b}.u & 31)',
            'LSHR_INT': '{a}.u >> ({b}.u & 31)', 'ASHR_INT': '(uint32_t)({a}.i >> ({b}.u & 31))',
            'MAX_INT': '(uint32_t)({a}.i > {b}.i ? {a}.i : {b}.i)', 'MIN_INT': '(uint32_t)({a}.i < {b}.i ? {a}.i : {b}.i)',
            'MAX_UINT': '({a}.u > {b}.u ? {a}.u : {b}.u)', 'MIN_UINT': '({a}.u < {b}.u ? {a}.u : {b}.u)',
            'MULLO_INT': '(uint32_t)({a}.i * {b}.i)', 'MULLO_UINT': '{a}.u * {b}.u'}
    if name in ints:
        return 'Wu(%s)' % ints[name].format(a=a[0], b=a[1] if len(a) > 1 else None), False
    if name == 'NOT_INT':
        return 'Wu(~%s.u)' % a[0], False
    if name == 'FLT_TO_INT':
        return 'Wi(f2i(%s.f))' % a[0], False
    if name == 'FLT_TO_UINT':
        return 'Wu(f2u(%s.f))' % a[0], False
    if name == 'INT_TO_FLT':
        return 'Wf((float)%s.i)' % a[0], True
    if name == 'UINT_TO_FLT':
        return 'Wf((float)%s.u)' % a[0], True
    raise NotImplementedError(name)


def _parse(text):
    """[(cf index, kind, info)] in order, ALU / TEX clauses carrying their instruction lines"""
    cfs, cur = [], None
    for line in text.splitlines():
        m = re.match(r'^(\d{2,3}) (\w+)(:?)\s*(.*)$', line)
        if m:
            cur = [int(m.group(1)), m.group(2), m.group(4), []]
            cfs.append(cur)
            continue
        if line.startswith('END_OF_PROGRAM'):
            break
        if cur is not None and line.strip():
            cur[3].append(line)
    return cfs


def _alu_clause(info, lines):
    """C code of an ALU clause body (runs only while active); returns (code, sets_predicate)"""
    kc = {}
    for m in re.finditer(r'KCACHE(\d)\(CB(\d+):(\d+)-\d+\)', info):
        kc[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
    out = ['const W *KC0 = cb[%d] + 4 * %d;' % kc.get(0, (0, 0)), 'const W *KC1 = cb[%d] + 4 * %d;' % kc.get(1, (0, 0)),
           '(void)KC0; (void)KC1;']
    groups, g = [], None
    for line in lines:
        m = re.match(r'\s*(\d+\s+)?([xyzwt]):\s+(\S+)\s*(.*)$', line)
        if not m:
            continue
        if m.group(1) or g is None:
            g = []
            groups.append(g)
        rest = re.sub(r'\s+(VEC|SCL)_\d{3}\b', '', m.group(4)).strip()
        flags = set()
        for f in ('UPDATE_EXEC_MASK', 'UPDATE_PRED', 'CLAMP', 'WRITE_MASK'):
            if rest.endswith(f) or (' ' + f) in rest:
                flags.add(f)
                rest = rest.replace(f, '').strip()
        args = [x.strip() for x in re.split(r',\s*(?![^()]*\))', rest)] if rest else []
        g.append((m.group(2), m.group(3), args, flags))
    pred = False
    for g in groups:
        body, writes = [], []
        dots = [s for s in g if s[1].split('*')[0].split('/')[0] in ('DOT4', 'DOT4_IEEE')]
        if dots:
            mul = 'mulx' if dots[0][1].startswith('DOT4') and 'IEEE' not in dots[0][1] else ''
            terms = ['%s(%s.f, %s.f)' % (mul, _src(s[2][1]), _src(s[2][2])) if mul else
                     '(%s.f * %s.f)' % (_src(s[2][1]), _src(s[2][2])) for s in dots]
            body.append('W d4 = Wf(%s);' % ' + '.join(terms))
        for slot, opname, args, flags in g:
            if opname == 'NOP':
                continue
            base = re.match(r'([A-Z0-9_]+)', opname).group(1)
            omod = opname[len(base):]
            dst = args[0] if args else '____'
            srcs = [_src(x) for x in args[1:]]
            if base in ('DOT4', 'DOT4_IEEE'):
                e, isf = 'd4', True
            else:
                m = re.fullmatch(r'PRED_SET(E|NE|GT|GE)(_INT|_UINT)?', base)
                if m:
                    f = {'_INT': 'i', '_UINT': 'u'}.get(m.group(2), 'f')
                    cond = '(%s.%s %s %s.%s)' % (srcs[0], f, CMP[m.group(1)], srcs[1], f)
                    body.append('bool pc_%s = %s;' % (slot, cond))
                    if 'UPDATE_EXEC_MASK' in flags or 'UPDATE_PRED' in flags:
                        body.append('pred = pc_%s;' % slot)
                        pred = True
                    e, isf = 'Wf(pc_%s ? 0.0f : 1.0f)' % slot, True
                else:
                    e, isf = _op(base, srcs)
            if omod and isf:
                k = {'*2': '2.0f', '*4': '4.0f', '/2': '0.5f'}[omod]
                e = 'Wf((%s).f * %s)' % (e, k)
            if 'CLAMP' in flags and isf:
                e = 'Wf(std::fmin(std::fmax((%s).f, 0.0f), 1.0f))' % e
            body.append('W r_%s = %s;' % (slot, e))
            if dst != '____':
                md = re.fullmatch(r'R(\d+)\.([xyzw])', dst)
                if not md:
                    raise NotImplementedError('destination ' + dst)
                writes.append('R[%s][%d] = r_%s;' % (md.group(1), CH.index(md.group(2)), slot))
        npv = ['r_%s' % c if any(s[0] == c and s[1] != 'NOP' for s in g) else 'Wu(0)' for c in CH]
        nps = 'r_t' if any(s[0] == 't' and s[1] != 'NOP' for s in g) else 'Wu(0)'
        out.append('{ ' + ' '.join(body) + ' ' + ' '.join(writes) +
                   ' pv[0] = %s; pv[1] = %s; pv[2] = %s; pv[3] = %s; ps = %s; }' % (*npv, nps))
    return '\n'.join(out), pred


def translate(text):
    """C++ source of a vertex program (latte-dis text)"""
    cfs = _parse(text)
    code = []
    for idx, kind, info, lines in cfs:
        code.append('cf%d:' % idx)
        popn = int(re.search(r'POP_CNT\((\d+)\)', info).group(1)) if 'POP_CNT' in info else 0
        addr = int(re.search(r'ADDR\((\d+)\)', info).group(1)) if 'ADDR' in info else None
        if kind == 'CALL_FS' or kind.startswith('MEM_STREAM') or kind == 'NOP':
            continue
        if kind.startswith('ALU'):
            body, pred = _alu_clause(info, lines)
            push = kind == 'ALU_PUSH_BEFORE'
            pops = {'ALU_POP_AFTER': 1, 'ALU_POP2_AFTER': 2}.get(kind, 0)
            code.append('{ bool was = active; bool pred = true; (void)pred;')
            if push:
                code.append('stk[sp++] = was;')
            code.append('if (was) {\n%s\n}' % body)
            if pred:
                code.append('if (was) active = pred;')
            if pops:
                code.append('sp -= %d; active = stk[sp];' % pops)
            code.append('}')
        elif kind == 'TEX':
            code.append('if (active) {')
            for line in lines:
                m = re.match(r'\s*\d+\s+FETCH\s+R(\d+)\.([xyzw01_]{4}),\s+R(\d+)\.([xyzw]),\s+b(\d+).*OFFSET\((\d+)\)', line)
                if not m:
                    if line.strip():
                        raise NotImplementedError(line.strip())
                    continue
                d, sel, ir, ic, buf, off = m.groups()
                code.append('{ const W *f = cb[%d] + 4 * (size_t)(R[%s][%d].u + %d / 16) ;' % (int(buf) - 128, ir, CH.index(ic), int(off)))
                code.append('  if (R[%s][%d].u + %d / 16 >= %d) f = zero4;' % (ir, CH.index(ic), int(off), CB_VEC4))
                for i, c in enumerate(sel):
                    if c in CH:
                        code.append('  R[%s][%d] = f[%d];' % (d, i, CH.index(c)))
                    elif c in '01':
                        code.append('  R[%s][%d] = Wf(%s.0f);' % (d, i, c))
                code.append('}')
            code.append('}')
        elif kind == 'JUMP':
            code.append('if (!active) { %s goto cf%d; }' % ('sp -= %d; active = stk[sp];' % popn if popn else '', addr))
        elif kind == 'ELSE':
            code.append('{ bool parent = sp > 0 ? stk[sp - 1] : true; active = parent && !active;')
            code.append('  if (!active) { %s goto cf%d; } }' % ('sp -= %d; active = stk[sp];' % popn if popn else '', addr))
        elif kind == 'POP':
            code.append('sp -= %d; active = stk[sp];' % popn)
        elif kind in ('EXP', 'EXP_DONE'):
            m = re.match(r'(POS|PARAM)(\d+),\s+R(\d+)\.([xyzw01_]{4})', info)
            if not m:
                raise NotImplementedError(info)
            dst = 'pos' if m.group(1) == 'POS' else 'par + 4 * %d' % int(m.group(2))
            if m.group(1) == 'POS' and m.group(2) != '0':
                continue
            for i, c in enumerate(m.group(4)):
                v = 'R[%s][%d].f' % (m.group(3), CH.index(c)) if c in CH else ('%s.0f' % c if c in '01' else None)
                if v:
                    code.append('(%s)[%d] = %s;' % (dst, i, v))
        else:
            raise NotImplementedError('CF ' + kind)
    labels = {int(x) for x in re.findall(r'goto cf(\d+)', '\n'.join(code))}
    body = '\n'.join(c if not re.fullmatch(r'cf(\d+):', c) or int(c[2:-1]) in labels else '' for c in code)
    return HEAD + r'''
static const W zero4[4] = {};
extern "C" void vs_run(int n, int na, const float *attr, const W *const *cb, const int *vid, float *outpos, float *outpar) {
  static W R[128][4];
  for (int i = 0; i < n; i++) {
    memset(R, 0, sizeof R);
    R[0][0] = Wi(vid[i]);
    for (int k = 0; k < na; k++) for (int c = 0; c < 4; c++) R[k + 1][c] = Wf(attr[((size_t)i * na + k) * 4 + c]);
    bool active = true, stk[64]; int sp = 0; (void)stk; (void)sp;
    W pv[4] = {}, ps = {}; (void)pv; (void)ps;
    float *pos = outpos + 4 * (size_t)i, *par = outpar + (size_t)i * %d * 4;
%s
  }
}
''' % (NPARAM, body)


class VertexProgram:
    def __init__(self, binary):
        b = bytes(binary)
        self.text = eft_vertex.disassemble(b)
        self.attributes = eft_vertex.used_attributes(b)
        h = eft_vertex.vertex_header(b)
        self.blocks = {n: cb for n, cb, _size in h['blocks']}
        self.uniforms = h['uniforms']
        self.reads = eft_vertex.uniform_reads(self.text)      # {(buffer, vec4, component)} its ALU clauses read
        regs = h['regs']
        self.params = {}
        for k in range(NPARAM):
            sem = (regs[4 + k // 4] >> (8 * (k % 4))) & 0xFF
            if sem != 0xFF:
                self.params[k] = sem
        src = translate(self.text)
        key = hashlib.sha1(src.encode()).hexdigest()[:20]
        so = os.path.join(CACHE, 'vs_%s.so' % key)
        if not os.path.exists(so):
            os.makedirs(CACHE, exist_ok=True)
            cpp = so[:-3] + '.cpp'
            open(cpp, 'w').write(src)
            r = subprocess.run(['g++', '-O1', '-w', '-shared', '-fPIC', '-o', so, cpp], capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError('compiling %s: %s' % (cpp, r.stderr[:2000]))
            os.unlink(cpp)
        self.lib = ctypes.CDLL(so)

    def run(self, attrs, cbs, vids=None):
        """attrs [n, len(attributes), 4]; cbs {buffer: float32 / uint32 array (vec4 rows)} ->
        (POS0 [n, 4], PARAMs [n, 8, 4])"""
        attrs = np.ascontiguousarray(attrs, np.float32)
        n = len(attrs)
        keep = []
        arr = (ctypes.c_void_p * NCB)()
        for k in range(NCB):
            a = np.zeros(CB_VEC4 * 4, np.uint32)
            if k in cbs:
                v = np.ascontiguousarray(cbs[k]).view(np.uint32).ravel()
                a[:min(len(v), len(a))] = v[:len(a)]
            keep.append(a)
            arr[k] = a.ctypes.data
        vids = np.ascontiguousarray(np.arange(n) if vids is None else vids, np.int32)
        pos = np.zeros((n, 4), np.float32)
        par = np.zeros((n, NPARAM, 4), np.float32)
        f = self.lib.vs_run
        f.restype = None
        f(ctypes.c_int(n), ctypes.c_int(attrs.shape[1] if attrs.ndim == 3 else 0), attrs.ctypes.data_as(ctypes.c_void_p),
          arr, vids.ctypes.data_as(ctypes.c_void_p), pos.ctypes.data_as(ctypes.c_void_p), par.ctypes.data_as(ctypes.c_void_p))
        return pos, par
