#!/usr/bin/env python3
"""Ultimate's effect vertex programs lowered to Latte (the Wii U GPU's instruction set): the universal shader
path's phase 1 (docs/eft-universal-shader-scope.md).

  text = lower(glsl, consts, attrib_names={location: name}, mode='identity' | 'eft', zratio)   # latte-asm (.vsh)
  gsh = assemble(text)                                                        # GX2 vertex shader (.gsh)

The input is the register-level GLSL tools/ult_shader_glsl.py makes of a BNSH vertex program: Maxwell
registers rN (uint), predicates pN, condition flags, F() / U() bit casts, one operation a statement, and a
jump dispatcher (`for (;;) switch (pc)`) whose jumps all go forward. The lowering is statement by statement:

- every scalar (rN, pN, cz / cs, the outputs) gets a GPR component; the attributes are fetched into R1.. in
  location order; R0.x is the vertex id
- one ALU operation a group (the vector unit of its destination channel, or the transcendental unit), groups
  cut into ALU clauses of at most 120 slots, each locking the two constant buffers c8 / c10 map to
- control flow is if-converted: a block's active mask (0 / ~0) is the OR of its incoming edges (a jump's
  mask is the active mask and its condition); a return clears lanes from it. Writes are guarded (CNDE_INT)
  only where needed: outputs while some lane may have left, registers inside a region a pending jump skips
- constant buffers other than c8 / c10 (c9 static emitter data, c1 the program's immediates, c12, c13, c16)
  are baked: their reads become literals, and every operation on literals is folded with the ALU's own
  semantics, so a branch on baked data is decided here and its dead side never emitted
- c9's one dynamic read (a 16-byte-strided table at a constant byte offset) is a select chain

Float operations are the IEEE kinds (MUL_IEEE, MULADD_IEEE: not the DX9 0 x anything = 0), sin / cos are
range-reduced into turns for SIN / COS."""
import math
import os
import re
import struct
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, 'latte_dis', 'latte-asm')
CH = 'xyzw'
ONES = 0xFFFFFFFF
CLAUSE_SLOTS = 120
TABLE_ENTRIES = 8           # c9's dynamic table read: 16-byte entries tried

TRANS_ONLY = {'EXP_IEEE', 'LOG_CLAMPED', 'LOG_IEEE', 'RECIP_CLAMPED', 'RECIP_FF', 'RECIP_IEEE', 'RECIPSQRT_CLAMPED',
              'RECIPSQRT_FF', 'RECIPSQRT_IEEE', 'SQRT_IEEE', 'FLT_TO_INT', 'INT_TO_FLT', 'UINT_TO_FLT', 'SIN', 'COS',
              'MULLO_INT', 'MULLO_UINT', 'FLT_TO_UINT'}
FLOAT_IN = {'ADD', 'MUL_IEEE', 'MULADD_IEEE', 'MIN_DX10', 'MAX_DX10', 'FLOOR', 'TRUNC', 'FRACT', 'RECIP_IEEE',
            'RECIPSQRT_IEEE', 'SQRT_IEEE', 'EXP_IEEE', 'LOG_IEEE', 'SIN', 'COS', 'FLT_TO_INT', 'FLT_TO_UINT',
            'SETE_DX10', 'SETNE_DX10', 'SETGT_DX10', 'SETGE_DX10', 'MOV'}


# ------------------------------------------------------------------ 32-bit words
def f32(u):
    return struct.unpack('<f', struct.pack('<I', u & ONES))[0]


def u32(f):
    try:
        return struct.unpack('<I', struct.pack('<f', f))[0]
    except OverflowError:
        return 0x7F800000 if f > 0 else 0xFF800000


def s32(u):
    u &= ONES
    return u - (1 << 32) if u & 0x80000000 else u


def _f2i(f):
    if f != f:
        return 0
    if f >= 2147483647.0:
        return 0x7FFFFFFF
    if f <= -2147483648.0:
        return 0x80000000
    return int(f) & ONES


def _f2u(f):
    if f != f or f <= 0:
        return 0
    if f >= 4294967295.0:
        return ONES
    return int(f)


def _fop(fn, *a):
    try:
        return u32(fn(*a))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def fold(name, v):
    """the ALU operation on 32-bit words (sources already with their modifiers), or None"""
    F = [f32(x) for x in v]
    b = lambda c: ONES if c else 0
    if name == 'MOV':
        return v[0]
    if name == 'ADD':
        return u32(F[0] + F[1])
    if name == 'MUL_IEEE':
        return u32(F[0] * F[1])
    if name == 'MULADD_IEEE':
        return u32(f32(u32(F[0] * F[1])) + F[2])
    if name in ('MIN_DX10', 'MAX_DX10'):
        a, c = F
        if a != a:
            return v[1]
        if c != c:
            return v[0]
        return u32(min(a, c) if name == 'MIN_DX10' else max(a, c))
    if name == 'FLOOR':
        return _fop(math.floor, F[0]) if math.isfinite(F[0]) else v[0]
    if name == 'TRUNC':
        return _fop(math.trunc, F[0]) if math.isfinite(F[0]) else v[0]
    if name == 'FRACT':
        return _fop(lambda x: x - math.floor(x), F[0]) if math.isfinite(F[0]) else None
    if name == 'RECIP_IEEE':
        return u32(math.copysign(math.inf, F[0])) if F[0] == 0 else _fop(lambda x: 1.0 / x, F[0])
    if name == 'SQRT_IEEE':
        return _fop(math.sqrt, F[0]) if F[0] >= 0 else 0x7FC00000
    if name == 'RECIPSQRT_IEEE':
        return None
    if name == 'SETE_DX10':
        return b(F[0] == F[1])
    if name == 'SETNE_DX10':
        return b(F[0] != F[1])
    if name == 'SETGT_DX10':
        return b(F[0] > F[1])
    if name == 'SETGE_DX10':
        return b(F[0] >= F[1])
    if name == 'SETE_INT':
        return b(v[0] == v[1])
    if name == 'SETNE_INT':
        return b(v[0] != v[1])
    if name == 'SETGT_INT':
        return b(s32(v[0]) > s32(v[1]))
    if name == 'SETGE_INT':
        return b(s32(v[0]) >= s32(v[1]))
    if name == 'SETGT_UINT':
        return b(v[0] > v[1])
    if name == 'SETGE_UINT':
        return b(v[0] >= v[1])
    if name == 'CNDE_INT':
        return v[1] if v[0] == 0 else v[2]
    if name == 'AND_INT':
        return v[0] & v[1]
    if name == 'OR_INT':
        return v[0] | v[1]
    if name == 'XOR_INT':
        return v[0] ^ v[1]
    if name == 'NOT_INT':
        return ~v[0] & ONES
    if name == 'ADD_INT':
        return (v[0] + v[1]) & ONES
    if name == 'SUB_INT':
        return (v[0] - v[1]) & ONES
    if name in ('MULLO_UINT', 'MULLO_INT'):
        return (v[0] * v[1]) & ONES
    if name == 'LSHL_INT':
        return (v[0] << (v[1] & 31)) & ONES
    if name == 'LSHR_INT':
        return v[0] >> (v[1] & 31)
    if name == 'ASHR_INT':
        return (s32(v[0]) >> (v[1] & 31)) & ONES
    if name == 'MAX_INT':
        return v[0] if s32(v[0]) > s32(v[1]) else v[1]
    if name == 'MIN_INT':
        return v[0] if s32(v[0]) < s32(v[1]) else v[1]
    if name == 'MAX_UINT':
        return max(v[0], v[1])
    if name == 'MIN_UINT':
        return min(v[0], v[1])
    if name == 'FLT_TO_INT':
        return _f2i(F[0])
    if name == 'FLT_TO_UINT':
        return _f2u(F[0])
    if name == 'INT_TO_FLT':
        return u32(float(s32(v[0])))
    if name == 'UINT_TO_FLT':
        return u32(float(v[0]))
    return None          # EXP / LOG / SIN / COS: left to the GPU


# ------------------------------------------------------------------ operands
class Opd:
    """a source: kind 'lit' (v a word), 'reg' (v a slot), 'kc' (v (buffer, word)); neg / abs float modifiers"""
    __slots__ = ('kind', 'v', 'neg', 'abs')

    def __init__(self, kind, v, neg=False, ab=False):
        self.kind, self.v, self.neg, self.abs = kind, v, neg, ab

    def plain(self):
        return not self.neg and not self.abs

    def key(self):
        return (self.kind, self.v, self.neg, self.abs)

    def word(self):
        """a literal's word with its modifiers applied"""
        w = self.v
        if self.abs:
            w &= 0x7FFFFFFF
        if self.neg:
            w ^= 0x80000000
        return w

    def negated(self):
        if self.kind == 'lit':
            return Opd('lit', self.word() ^ 0x80000000)
        return Opd(self.kind, self.v, not self.neg, self.abs)

    def absolute(self):
        if self.kind == 'lit':
            return Opd('lit', self.word() & 0x7FFFFFFF)
        return Opd(self.kind, self.v, False, True)


def L(w):
    return Opd('lit', w & ONES)


# ------------------------------------------------------------------ parsing
_TOK = re.compile(r'(0x[0-9a-fA-F]+u?|\d+\.\d+(?:e[+-]?\d+)?f?|\d+u?)|([A-Za-z_]\w*)|'
                  r'(<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&|^~!<>=?:;,(){}\[\].])')


def tokenize(s):
    out, i = [], 0
    while True:
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            return out
        m = _TOK.match(s, i)
        if not m:
            raise SyntaxError('at: ' + s[i:i + 40])
        i = m.end()
        if m.group(1):
            out.append(('num', m.group(1)))
        elif m.group(2):
            out.append(('id', m.group(2)))
        else:
            out.append(('op', m.group(3)))


BIN = {'||': 2, '&&': 3, '|': 4, '^': 5, '&': 6, '==': 7, '!=': 7, '<': 8, '<=': 8, '>': 8, '>=': 8,
       '<<': 9, '>>': 9, '+': 10, '-': 10, '*': 11, '/': 11, '%': 11}
TYPES = ('float', 'uint', 'int', 'bool')


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        return self.t[self.i + k] if self.i + k < len(self.t) else ('eof', None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise SyntaxError('expected %r, got %r near %r' % (val, tok, self.t[max(0, self.i - 8):self.i + 4]))
        self.i += 1
        return tok

    def stmts(self, stop):
        out = []
        while self.peek()[1] not in stop and self.peek()[0] != 'eof':
            out.append(self.stmt())
        return out

    def stmt(self):
        k, v = self.peek()
        if v == '{':
            self.take()
            body = self.stmts(('}',))
            self.take('}')
            return ('block', body)
        if v == ';':
            self.take()
            return ('block', [])
        if v == 'if':
            self.take()
            self.take('(')
            c = self.expr()
            self.take(')')
            s = self.stmt()
            if self.peek()[1] == 'else':
                self.take()
                return ('ifelse', c, s, self.stmt())
            return ('if', c, s)
        if v == 'case':
            self.take()
            n = self.take()[1]
            self.take(':')
            return ('label', int(n.rstrip('u')))
        if v == 'default':
            self.take()
            self.take(':')
            return ('default',)
        if v == 'return':
            self.take()
            self.take(';')
            return ('return',)
        if v == 'pc' and self.peek(1)[1] == '=':
            self.take()
            self.take('=')
            n = int(self.take()[1].rstrip('u'))
            self.take(';')
            self.take('continue')
            self.take(';')
            return ('goto', n)
        if v in TYPES and self.peek(1)[0] == 'id':
            self.take()
            decls = []
            while True:
                name = self.take()[1]
                self.take('=')
                decls.append((name, self.expr()))
                if self.peek()[1] == ',':
                    self.take()
                    continue
                break
            self.take(';')
            return ('decl', v, decls)
        lhs = self.unary()
        self.take('=')
        e = self.expr()
        self.take(';')
        return ('assign', lhs, e)

    def expr(self, prec=0):
        a = self.unary()
        while True:
            k, v = self.peek()
            if v == '?' and prec <= 1:
                self.take()
                b = self.expr(1)
                self.take(':')
                c = self.expr(1)
                a = ('tern', a, b, c)
                continue
            if k == 'op' and v in BIN and BIN[v] > prec:
                self.take()
                a = ('bin', v, a, self.expr(BIN[v]))
                continue
            return a

    def unary(self):
        k, v = self.peek()
        if v in ('-', '!', '~'):
            self.take()
            return ('un', v, self.unary())
        return self.postfix()

    def postfix(self):
        k, v = self.take()
        if k == 'num':
            node = ('num', v)
        elif k == 'id':
            if self.peek()[1] == '(':
                self.take()
                args = []
                while self.peek()[1] != ')':
                    args.append(self.expr())
                    if self.peek()[1] == ',':
                        self.take()
                self.take(')')
                node = ('call', v, args)
            else:
                node = ('id', v)
        elif v == '(':
            node = self.expr()
            self.take(')')
        else:
            raise SyntaxError('unexpected %r' % (v,))
        while self.peek()[1] in ('[', '.'):
            if self.take()[1] == '[':
                node = ('index', node, self.expr())
                self.take(']')
            else:
                node = ('member', node, self.take()[1])
        return node


def parse_program(glsl):
    """(inputs {location: name}, outputs [location], buffers used, statements)"""
    ins, outs = {}, []
    for m in re.finditer(r'layout\(location = (\d+)\) (in|out) vec4 (\w+);', glsl):
        if m.group(2) == 'in':
            ins[int(m.group(1))] = m.group(3)
        else:
            outs.append(int(m.group(1)))
    i = glsl.index('switch (pc) {') + len('switch (pc) {')
    j = glsl.index('default:', i)
    return ins, outs, Parser(tokenize(glsl[i:j])).stmts(())


# ------------------------------------------------------------------ eft's particle streams
def _v(name):
    return [(name, c) for c in range(4)]


# Ultimate's attribute components from eft's CPU-particle streams (cross_f 0x04A637E4's record, phase 0:
# docs/fx-render-eft2.md): a (stream, component), 'birth' (time - v_inWldPos.w, the age eft keeps), 'scale_z'
# (v_inScl.x x the emitter's z / x ratio: eft's streams have x and y only), or None (0)
EFT_ATTRIBUTES = {
    'sysPosAttr': _v('v_inPos'),
    'sysTexCoordAttr': _v('v_inTexCoord'),
    'sysVertexColor0Attr': _v('v_inColor'),
    'sysLocalPosAttr': [('v_inWldPos', 0), ('v_inWldPos', 1), ('v_inWldPos', 2), ('v_inRandom', 3)],   # w life
    'sysLocalVecAttr': [('v_inVec', 0), ('v_inVec', 1), ('v_inVec', 2), 'birth'],
    'sysLocalDiffAttr': _v('v_inWldPosDf'),
    'sysScaleAttr': [('v_inScl', 0), ('v_inScl', 1), 'scale_z', ('v_inScl', 3)],
    'sysRandomAttr': [('v_inRandom', 0), ('v_inRandom', 1), ('v_inRandom', 2), ('v_inVec', 3)],    # w: eft's
    'sysInitRotateAttr': _v('v_inRot'),                                                             # own random
    'sysEmtMat0Attr': _v('v_inEmtMat0'),
    'sysEmtMat1Attr': _v('v_inEmtMat1'),
    'sysEmtMat2Attr': _v('v_inEmtMat2'),
}


def _spec_streams(spec):
    if isinstance(spec, tuple):
        return [spec[0]]
    return {'birth': ['v_inWldPos'], 'scale_z': ['v_inScl']}.get(spec, [])


# ------------------------------------------------------------------ lowering
class Lowering:
    def __init__(self, glsl, consts, attrib_names=None, mode='identity', zratio=1.0, table_entries=TABLE_ENTRIES):
        """consts {buffer: words} the baked buffers; attrib_names {location: Ultimate attribute name} (the
        program's reflection); mode 'identity' (c8 / c10 as constant buffers 1 / 3 word for word, the attributes
        as Ultimate names them) or 'eft' (eft's own blocks and particle streams: EFT_ATTRIBUTES, eft_cb);
        zratio the emitter's z / x particle scale (eft's streams carry x and y only)"""
        self.consts = {k: list(v) for k, v in consts.items()}
        self.cbmap = {8: 1, 10: 3}
        self.mode, self.zratio = mode, zratio
        self.table_entries = table_entries
        self.ins, self.outs, self.body = parse_program(glsl)
        self.attrib_names = {loc: (attrib_names or {}).get(loc, 'in_attr%d' % loc) for loc in self.ins}
        if mode == 'eft':
            need = []
            for loc in sorted(self.ins):
                for spec in EFT_ATTRIBUTES.get(self.attrib_names[loc], [None] * 4):
                    for nm in _spec_streams(spec):
                        if nm not in need:
                            need.append(nm)
            self.hw_attrs = need
        else:
            self.hw_attrs = [self.attrib_names[loc] for loc in sorted(self.ins)]
        self.hw_gpr = {nm: 1 + k for k, nm in enumerate(self.hw_attrs)}
        self.derived = {}
        self.code = []              # (op, dst slot, [Opd])
        self.nvars = 0
        self.vars = {}              # name -> named slot index
        self.ntemp = self.maxtemp = 0
        self.known = {}             # name -> literal word (the GPR holds it too)
        self.act = L(ONES)
        self.pending = {}           # label -> {'lits': [word], 'acc': name or None, 'known': [dict]}
        self.dead = False
        self.locals, self.local_ast, self.eqcache = {}, {}, {}
        self.region_act, self.region_ret = L(ONES), False
        # outputs first, each a whole GPR
        self.vec = {}
        for name in ['gl_Position'] + ['out_attr%d' % k for k in sorted(self.outs)]:
            self.vec[name] = self.nvars
            self.nvars += 4

    # ---- slots: ('h', n) hardware (n = 4 gpr + channel), ('n', i) named, ('t', i) temp
    def var(self, name):
        if name not in self.vars:
            self.vars[name] = self.nvars
            self.nvars += 1
        return ('n', self.vars[name])

    def temp(self):
        self.ntemp += 1
        self.maxtemp = max(self.maxtemp, self.ntemp)
        return ('t', self.ntemp - 1)

    # ---- emission
    def emit(self, op, srcs, dst=None):
        """dst = op(srcs): folded when every source is a literal; returns the result as a source"""
        srcs = [s if isinstance(s, Opd) else L(s) for s in srcs]
        if op == 'NOT_INT':                 # latte-asm's grammar takes it with two sources: ~x = x ^ ~0
            op, srcs = 'XOR_INT', [srcs[0], L(ONES)]
        if all(s.kind == 'lit' for s in srcs):
            w = fold(op, [s.word() for s in srcs])
            if w is not None:
                if dst is not None:
                    self.code.append(('MOV', dst, [L(w)]))
                    return Opd('reg', dst)
                return L(w)
        simple = self.simplify(op, srcs)
        if simple is not None:
            if dst is None:
                return simple
            return self.move(simple, dst)
        if op not in FLOAT_IN:
            srcs = [self.plain(s) for s in srcs]
        if dst is None:
            dst = self.temp()
        self.code.append((op, dst, srcs))
        return Opd('reg', dst)

    def simplify(self, op, s):
        lit = [x.word() if x.kind == 'lit' else None for x in s]
        if op == 'AND_INT':
            if ONES in lit:
                return s[1 - lit.index(ONES)]
            if 0 in lit:
                return L(0)
            if s[0].key() == s[1].key():
                return s[0]
        if op == 'OR_INT':
            if 0 in lit:
                return s[1 - lit.index(0)]
            if ONES in lit:
                return L(ONES)
        if op in ('ADD_INT', 'XOR_INT') and lit[1] == 0:
            return s[0]
        if op == 'ADD_INT' and lit[0] == 0:
            return s[1]
        if op == 'SUB_INT' and lit[1] == 0:
            return s[0]
        if op == 'CNDE_INT':
            if lit[0] is not None:
                return s[1] if lit[0] == 0 else s[2]
            if s[1].key() == s[2].key():
                return s[1]
        return None

    def plain(self, s):
        """a source without float modifiers (integer operations take none)"""
        if s.kind == 'lit' or s.plain():
            return s
        return self.emit('MOV', [s])

    def move(self, s, dst):
        if s.kind == 'reg' and s.v == dst and s.plain():
            return s
        self.code.append(('MOV', dst, [s]))
        return Opd('reg', dst)

    # ---- values of names
    def read(self, name):
        if name in self.locals:
            return self.locals[name]
        if name == 'rz':
            return (L(0), 'uint')
        typ = 'bool' if re.fullmatch(r'p\d+|cz|cs|ccf|cov', name) else 'uint'
        if name in self.known:
            return (L(self.known[name]), typ)
        return (Opd('reg', self.var(name)), typ)

    # ---- types
    def conv(self, val, to):
        o, t = val
        if t == to or (t in ('int', 'uint') and to in ('int', 'uint')):
            return o
        if to == 'float':
            if t == 'int':
                return self.emit('INT_TO_FLT', [o])
            if t == 'uint':
                return self.emit('UINT_TO_FLT', [o])
            if t == 'bool':
                return self.emit('CNDE_INT', [o, L(0), L(0x3F800000)])
        if to in ('int', 'uint'):
            if t == 'float':
                return self.emit('FLT_TO_INT' if to == 'int' else 'FLT_TO_UINT', [o])
            if t == 'bool':
                return self.emit('AND_INT', [o, L(1)])
        if to == 'bool':
            if t == 'float':
                return self.emit('SETNE_DX10', [o, L(0)])
            return self.emit('SETNE_INT', [o, L(0)])
        raise NotImplementedError('%s -> %s' % (t, to))

    # ---- expressions -> (Opd, type)
    def ex(self, n):
        k = n[0]
        if k == 'num':
            t = n[1]
            if t.startswith('0x'):
                return (L(int(t.rstrip('u'), 16)), 'uint' if t.endswith('u') else 'int')
            if '.' in t:
                return (L(u32(float(t.rstrip('f')))), 'float')
            return (L(int(t.rstrip('u'))), 'uint' if t.endswith('u') else 'int')
        if k == 'id':
            name = n[1]
            if name in ('true', 'false'):
                return (L(ONES if name == 'true' else 0), 'bool')
            if name == 'gl_VertexID':
                return (Opd('reg', ('h', 0)), 'int')
            return self.read(name)
        if k == 'index':
            base, idx = n[1], n[2]
            if base[0] == 'id' and re.fullmatch(r'in_attr\d+', base[1]):
                c = self.lit(self.ex(idx)[0])
                return (self.attr(int(base[1][7:]), c), 'float')
            if base[0] == 'id' and re.fullmatch(r'c\d+', base[1]):
                return (self.cbread(int(base[1][1:]), idx), 'uint')
            if base[0] == 'id' and base[1] in self.vec:
                c = self.lit(self.ex(idx)[0])
                return (Opd('reg', ('n', self.vec[base[1]] + c)), 'float')
            raise NotImplementedError('index ' + repr(n))
        if k == 'un':
            o, t = self.ex(n[2])
            if n[1] == '-':
                if t == 'float':
                    return (o.negated(), 'float')
                return (self.emit('SUB_INT', [L(0), o]), t)
            if n[1] == '!':
                return (self.emit('NOT_INT', [self.conv((o, t), 'bool')]), 'bool')
            if n[1] == '~':
                return (self.emit('NOT_INT', [o]), t)
        if k == 'tern':
            c = n[1]
            neg = c[0] == 'un' and c[1] == '!'
            co = self.conv(self.ex(c[2] if neg else c), 'bool')
            if co.kind == 'lit':
                return self.ex(n[2] if (co.v != 0) != neg else n[3])
            a, b = self.ex(n[2]), self.ex(n[3])
            t = self.arith_type(a[1], b[1])
            a, b = self.conv(a, t), self.conv(b, t)
            # CNDE_INT c, x, y = c == 0 ? x : y
            return (self.emit('CNDE_INT', [co, a, b] if neg else [co, b, a]), t)
        if k == 'bin':
            return self.binop(n[1], n[2], n[3])
        if k == 'call':
            return self.call(n[1], n[2])
        raise NotImplementedError(repr(n))

    @staticmethod
    def arith_type(a, b):
        if 'float' in (a, b):
            return 'float'
        if 'uint' in (a, b):
            return 'uint'
        if a == b == 'bool':
            return 'bool'
        return 'int'

    def lit(self, o):
        if o.kind != 'lit':
            raise NotImplementedError('a dynamic index')
        return o.word()

    def binop(self, op, an, bn):
        if op in ('&&', '||'):
            a = self.conv(self.ex(an), 'bool')
            b = self.conv(self.ex(bn), 'bool')
            return (self.emit('AND_INT' if op == '&&' else 'OR_INT', [a, b]), 'bool')
        a, b = self.ex(an), self.ex(bn)
        t = self.arith_type(a[1], b[1])
        if t == 'bool':
            t = 'int'
        x, y = self.conv(a, t), self.conv(b, t)
        if op in ('==', '!=', '<', '<=', '>', '>='):
            if t == 'float':
                name = {'==': 'SETE_DX10', '!=': 'SETNE_DX10', '<': 'SETGT_DX10', '<=': 'SETGE_DX10',
                        '>': 'SETGT_DX10', '>=': 'SETGE_DX10'}[op]
            else:
                sfx = '_INT' if t == 'int' else '_UINT'
                name = {'==': 'SETE_INT', '!=': 'SETNE_INT', '<': 'SETGT' + sfx, '<=': 'SETGE' + sfx,
                        '>': 'SETGT' + sfx, '>=': 'SETGE' + sfx}[op]
            if op in ('<', '<='):
                x, y = y, x
            return (self.emit(name, [x, y]), 'bool')
        if t == 'float':
            if op == '+':
                return (self.emit('ADD', [x, y]), t)
            if op == '-':
                return (self.emit('ADD', [x, y.negated()]), t)
            if op == '*':
                return (self.emit('MUL_IEEE', [x, y]), t)
            if op == '/':
                if x.kind == 'lit' and x.word() == 0x3F800000:
                    return (self.emit('RECIP_IEEE', [y]), t)
                return (self.emit('MUL_IEEE', [x, self.emit('RECIP_IEEE', [y])]), t)
            raise NotImplementedError('float ' + op)
        name = {'+': 'ADD_INT', '-': 'SUB_INT', '*': 'MULLO_UINT', '&': 'AND_INT', '|': 'OR_INT', '^': 'XOR_INT',
                '<<': 'LSHL_INT', '>>': 'ASHR_INT' if t == 'int' else 'LSHR_INT'}.get(op)
        if name is None:
            raise NotImplementedError('int ' + op)
        return (self.emit(name, [x, y]), t)

    def call(self, fn, args):
        if fn == 'F':
            return (self.ex(args[0])[0], 'float')
        if fn == 'U':
            return (self.ex(args[0])[0], 'uint')
        if fn in ('float', 'int', 'uint', 'bool'):
            a = self.ex(args[0])
            if fn in ('int', 'uint') and a[1] in ('int', 'uint'):
                return (a[0], fn)
            return (self.conv(a, fn), fn)
        if fn == 'fma':
            a, b, c = (self.conv(self.ex(x), 'float') for x in args)
            return (self.emit('MULADD_IEEE', [a, b, c]), 'float')
        un = {'floor': 'FLOOR', 'trunc': 'TRUNC', 'sqrt': 'SQRT_IEEE', 'inversesqrt': 'RECIPSQRT_IEEE',
              'exp2': 'EXP_IEEE', 'log2': 'LOG_IEEE'}
        if fn in un:
            return (self.emit(un[fn], [self.conv(self.ex(args[0]), 'float')]), 'float')
        if fn in ('sin', 'cos'):
            x = self.conv(self.ex(args[0]), 'float')
            # turns, reduced to [-0.5, 0.5): SIN / COS take turns
            t = self.emit('MULADD_IEEE', [x, L(u32(1 / (2 * math.pi))), L(0x3F000000)])
            t = self.emit('ADD', [self.emit('FRACT', [t]), L(0xBF000000)])
            return (self.emit('SIN' if fn == 'sin' else 'COS', [t]), 'float')
        if fn == 'isnan':
            x = self.conv(self.ex(args[0]), 'float')
            return (self.emit('SETNE_DX10', [x, x]), 'bool')
        if fn == 'abs':
            o, t = self.ex(args[0])
            if t == 'float':
                return (o.absolute(), t)
            return (self.emit('MAX_INT', [o, self.emit('SUB_INT', [L(0), o])]), t)
        if fn in ('min', 'max'):
            a, b = self.ex(args[0]), self.ex(args[1])
            t = self.arith_type(a[1], b[1])
            name = {'float': '_DX10', 'int': '_INT', 'uint': '_UINT'}[t]
            return (self.emit(fn.upper() + name, [self.conv(a, t), self.conv(b, t)]), t)
        if fn == 'clamp':
            x, lo, hi = (self.conv(self.ex(a), 'float') for a in args)
            return (self.emit('MIN_DX10', [self.emit('MAX_DX10', [x, lo]), hi]), 'float')
        if fn == 'bitfieldExtract':
            o, t = self.ex(args[0])
            off, bits = self.lit(self.ex(args[1])[0]), self.lit(self.ex(args[2])[0])
            if bits == 0:
                return (L(0), t)
            if t == 'int':
                v = self.emit('LSHL_INT', [o, L(32 - off - bits)]) if off + bits < 32 else o
                return (self.emit('ASHR_INT', [v, L(32 - bits)]), t)
            v = self.emit('LSHR_INT', [o, L(off)]) if off else o
            return (self.emit('AND_INT', [v, L((1 << bits) - 1)]) if off + bits < 32 else v, t)
        if fn == 'mx_f2i':
            inner = args[0]
            if inner[0] == 'call' and inner[1] == 'trunc':
                inner = inner[2][0]          # FLT_TO_INT / UINT truncate
            x = self.conv(self.ex(inner), 'float')
            kind = self.lit(self.ex(args[1])[0])
            if kind == 0:
                return (self.emit('FLT_TO_UINT', [x]), 'uint')
            if kind == 1:
                return (self.emit('FLT_TO_INT', [x]), 'uint')
            lo, hi = (0.0, 65535.0) if kind == 2 else (-32768.0, 32767.0)
            x = self.emit('MIN_DX10', [self.emit('MAX_DX10', [x, L(u32(lo))]), L(u32(hi))])
            return (self.emit('FLT_TO_INT', [x]), 'uint')
        raise NotImplementedError('function ' + fn)

    # ---- constant buffers
    def hw(self, name, c):
        return Opd('reg', ('h', 4 * self.hw_gpr[name] + c))

    def once(self, key, make):
        """a value made from inputs / blocks only (the same in every lane and branch): computed at its first
        use into its own register, unguarded (every emitted operation runs), and reused after"""
        if key not in self.derived:
            self.derived[key] = self.store(make(), self.var('d_%s' % key))
        return self.derived[key]

    def attr(self, loc, c):
        """component c of Ultimate's attribute at location loc"""
        name = self.attrib_names[loc]
        if self.mode != 'eft':
            return self.hw(name, c)
        spec = EFT_ATTRIBUTES.get(name, [None] * 4)[c]
        if spec is None:
            return L(0)
        if isinstance(spec, tuple):
            return self.hw(*spec)
        if spec == 'birth':           # time - age: c10[8] - birth is then the age eft keeps (v_inWldPos.w)
            return self.once('birth', lambda: self.emit('ADD', [Opd('kc', (3, 8)), self.hw('v_inWldPos', 3).negated()]))
        if spec == 'scale_z':
            return self.once('scale_z', lambda: self.emit('MUL_IEEE', [self.hw('v_inScl', 0), L(u32(self.zratio))]))
        raise NotImplementedError(spec)

    def cbread(self, cb, idx):
        if cb in self.cbmap:
            w = self.lit(self.ex(idx)[0])
            if self.mode == 'eft':
                return self.eft_cb(cb, w)
            return Opd('kc', (self.cbmap[cb], w))
        o = self.ex(idx)[0]
        data = self.consts.get(cb, [])
        if o.kind == 'lit':
            w = o.word()
            return L(data[w] if w < len(data) else 0)
        return self.table_read(cb, idx, data)

    def eft_cb(self, cb, w):
        """c8 / c10 word w from eft's viewUniformBlock (CB1) / emitterDynamicUniformBlock (CB3): the same row-major
        layout (vm 0, pm 16, vpm 32, bm 48, eye vector 64, eye position 68; colours 0 / 4, emp0 8 (time, .., step),
        emm 16, emmrt 32), except Ultimate's view parameters c8[72-75] (near, far, near x far, far - near), which
        eft keeps at vp 80 (near, far)"""
        if cb == 8 and 72 <= w < 76:
            near, far = Opd('kc', (1, 80)), Opd('kc', (1, 81))
            if w == 72:
                return near
            if w == 73:
                return far
            if w == 74:
                return self.once('nf', lambda: self.emit('MUL_IEEE', [near, far]))
            return self.once('fmn', lambda: self.emit('ADD', [far, near.negated()]))
        return Opd('kc', (self.cbmap[cb], w))

    def table_read(self, cb, idx, data):
        """c9[(X + K) >> 2 (+ j)] with X a multiple of 16 below 16 x TABLE_ENTRIES: a select chain"""
        j = 0
        if idx[0] == 'bin' and idx[1] == '+':
            j = self.lit(self.ex(idx[3])[0])
            idx = idx[2]
        if not (idx[0] == 'bin' and idx[1] == '>>' and idx[2][0] == 'id' and idx[2][1] in self.local_ast):
            raise NotImplementedError('a dynamic constant read ' + repr(idx))
        ad = self.local_ast[idx[2][1]]
        if not (ad[0] == 'bin' and ad[1] == '+'):
            raise NotImplementedError('a dynamic constant read ' + repr(ad))
        x = self.ex(ad[2])[0]
        base = self.lit(self.ex(ad[3])[0])
        word = lambda m: (base + 16 * m) // 4 + j
        get = lambda w: data[w] if w < len(data) else 0
        res = L(get(word(0)))
        for m in range(1, self.table_entries):
            key = (x.key(), m)
            if key not in self.eqcache:
                self.eqcache[key] = self.emit('SETE_INT', [x, L(16 * m)])
            res = self.emit('CNDE_INT', [self.eqcache[key], res, L(get(word(m)))])
        return res

    # ---- statements
    def full(self):
        """no pending jump skips this point: every live lane runs it"""
        return not self.pending

    def write(self, name, val, cond):
        """a named register / predicate / flag written under cond"""
        if name == 'rz':
            return
        if name == 'pc':
            raise NotImplementedError('pc')
        for ln, (o, t) in list(self.locals.items()):
            if o.kind == 'reg' and o.v == self.var(name):
                self.locals[ln] = (self.emit('MOV', [o]), t)
        slot = self.var(name)
        guard = cond if self.full() else self.emit('AND_INT', [cond, self.act])
        old = self.known.get(name)
        if guard.kind == 'lit' and guard.v == 0:
            return
        if guard.kind == 'lit':
            self.store(val, slot)
            if val.kind == 'lit':
                self.known[name] = val.word()
            else:
                self.known.pop(name, None)
            return
        oldo = L(old) if old is not None else Opd('reg', slot)
        self.emit('CNDE_INT', [guard, oldo, self.plain(val)], dst=slot)
        if not (val.kind == 'lit' and old is not None and val.word() == old):
            self.known.pop(name, None)

    def store(self, val, slot):
        """val into a named slot (retargeting the operation that just made it, when it made a temporary)"""
        if val.kind == 'reg' and val.v[0] == 't' and val.plain() and self.code and self.code[-1][1] == val.v:
            op, _d, s = self.code[-1]
            self.code[-1] = (op, slot, s)
            new = Opd('reg', slot)
            for ln, (o, t) in list(self.locals.items()):
                if o.kind == 'reg' and o.v == val.v:
                    self.locals[ln] = (Opd('reg', slot, o.neg, o.abs), t)
            self.eqcache = {k: v for k, v in self.eqcache.items() if v.v != val.v}
            return new
        return self.move(val, slot)

    def write_out(self, vec, c, val, cond):
        slot = ('n', self.vec[vec] + c)
        guard = self.emit('AND_INT', [cond, self.act])
        if guard.kind == 'lit' and guard.v == 0:
            return
        if guard.kind == 'lit':
            self.store(val, slot)
        else:
            self.emit('CNDE_INT', [guard, Opd('reg', slot), self.plain(val)], dst=slot)

    def jump(self, label, cond):
        mask = self.emit('AND_INT', [self.act, cond])
        if mask.kind == 'lit' and mask.v == 0:
            return
        if self.full():
            # a region starts: every lane active here meets again where no jump is pending, unless one returns
            self.region_act = self.act if self.act.kind == 'lit' else self.move(self.act, self.var('ract'))
            self.region_ret = False
        p = self.pending.setdefault(label, {'lits': [], 'acc': None, 'known': []})
        p['known'].append(dict(self.known))
        if mask.kind == 'lit':
            p['lits'].append(mask.v)
        elif p['acc'] is None:
            p['acc'] = 'in%d' % label
            mask = self.store(mask, self.var(p['acc']))
        else:
            acc = Opd('reg', self.var(p['acc']))
            self.emit('OR_INT', [acc, mask], dst=self.var(p['acc']))
        self.set_act(self.emit('XOR_INT', [self.act, mask]))

    def ret(self, cond):
        c = self.emit('AND_INT', [self.act, cond])
        if c.kind == 'lit' and c.v == 0:
            return
        if not self.full():
            self.region_ret = True
        self.set_act(self.emit('XOR_INT', [self.act, c]))

    def set_act(self, o):
        if o.kind == 'lit':
            self.act = o
            self.dead = o.v == 0
        else:
            self.act = self.store(o, self.var('act'))
            self.dead = False

    def label(self, n):
        p = self.pending.pop(n, None)
        states = ([dict(self.known)] if not self.dead else []) + (p['known'] if p else [])
        if not states:
            self.dead = True
            return
        known = states[0]
        for s in states[1:]:
            known = {k: v for k, v in known.items() if s.get(k) == v}
        self.known = known
        if p and not self.pending and not self.region_ret:
            self.set_act(self.region_act)          # the region closed with no lane gone: as it began
            return
        parts = [self.act] if not self.dead else []
        if p:
            parts += [L(w) for w in p['lits']]
            if p['acc']:
                parts.append(Opd('reg', self.var(p['acc'])))
        act = parts[0]
        for q in parts[1:]:
            act = self.emit('OR_INT', [act, q])
        self.set_act(act)

    def stmt(self, s, cond):
        k = s[0]
        if k == 'label':
            self.label(s[1])
            return
        if self.dead:
            return
        if k == 'block':
            for x in s[1]:
                self.stmt(x, cond)
                if self.dead:
                    return
        elif k == 'if':
            c = self.conv(self.ex(s[1]), 'bool')
            c = self.emit('AND_INT', [cond, c])
            if not (c.kind == 'lit' and c.v == 0):
                self.stmt(s[2], c)
        elif k == 'goto':
            self.jump(s[1], cond)
        elif k == 'return':
            self.ret(cond)
        elif k == 'decl':
            for name, e in s[2]:
                self.local_ast[name] = e
                self.locals[name] = (self.conv(self.ex(e), s[1]), s[1])
        elif k == 'assign':
            lhs = s[1]
            if lhs[0] == 'id' and lhs[1] in self.locals:
                t = self.locals[lhs[1]][1]
                self.locals[lhs[1]] = (self.conv(self.ex(s[2]), t), t)
                self.local_ast[lhs[1]] = s[2]
            elif lhs[0] == 'id':
                name = lhs[1]
                t = 'bool' if re.fullmatch(r'p\d+|cz|cs|ccf|cov', name) else 'uint'
                self.write(name, self.conv(self.ex(s[2]), t), cond)
            elif lhs[0] == 'index' and lhs[1][0] == 'id' and lhs[1][1] in self.vec:
                c = self.lit(self.ex(lhs[2])[0])
                self.write_out(lhs[1][1], c, self.conv(self.ex(s[2]), 'float'), cond)
            else:
                raise NotImplementedError('assignment to ' + repr(lhs))
        elif k == 'default':
            self.dead = True
        else:
            raise NotImplementedError(k)

    def run(self):
        # every register / predicate the program reads starts 0 (the GLSL's initialisers); outputs (0, 0, 0, 1)
        names = sorted(set(re.findall(r'\b(r\d+|p\d+|cz|cs|ccf|cov)\b', repr(self.body))) - {'rz'})
        for n in names:
            self.var(n)
            self.known[n] = 0
        self.init_names = names
        for s in self.body:
            self.ntemp = 0
            self.locals, self.local_ast, self.eqcache = {}, {}, {}
            self.stmt(s, L(ONES))
        return self

    # ---- text
    def text(self, cbnames=None):
        nin = len(self.hw_attrs)
        named0 = 4 * (1 + nin)                   # first named slot (whole GPRs after the inputs)
        temp0 = named0 + ((self.nvars + 3) // 4) * 4
        ngpr = (temp0 + self.maxtemp + 3) // 4

        def sl(s):
            kind, i = s
            n = i if kind == 'h' else named0 + i if kind == 'n' else temp0 + i
            return 'R%d.%s' % (n // 4, CH[n % 4]), n % 4

        banks = {cb: k for k, cb in enumerate(sorted(set(self.cbmap.values())))}

        def src(o):
            if o.kind == 'lit':
                t = '0x%08X' % o.v
            elif o.kind == 'reg':
                t = sl(o.v)[0]
            else:
                cb, w = o.v
                t = 'KC%d[%d].%s' % (banks[cb], w // 4, CH[w % 4])
            if o.abs:
                t = '|%s|' % t
            if o.neg:
                t = '-' + t
            return t

        groups = []
        # initial values: outputs (0, 0, 0, 1), registers 0
        for name, base in self.vec.items():
            for c in range(4):
                groups.append(('MOV', ('n', base + c), [L(0x3F800000 if c == 3 else 0)]))
        for n in self.init_names:
            groups.append(('MOV', ('n', self.vars[n]), [L(0)]))
        groups += self.code
        lines, cf = [], []
        hdr = ['; $MODE = "UniformBlock"']
        for k, nm in enumerate(self.hw_attrs):
            hdr += ['; $ATTRIB_VARS[%d].name = "%s"' % (k, nm), '; $ATTRIB_VARS[%d].type = "vec4"' % k,
                    '; $ATTRIB_VARS[%d].location = %d' % (k, k)]
        # eft's own names and sizes (a vanilla program's header): the CPU binds the blocks by name
        blocks = cbnames or {1: ('viewUniformBlock', 352), 3: ('emitterDynamicUniformBlock', 192)}
        for k, (cb, (nm, size)) in enumerate(sorted(blocks.items())):
            hdr += ['; $UNIFORM_BLOCKS[%d].name = "%s"' % (k, nm), '; $UNIFORM_BLOCKS[%d].offset = %d' % (k, cb),
                    '; $UNIFORM_BLOCKS[%d].size = %d' % (k, size)]
        params = sorted(self.outs)
        hdr += ['; $NUM_SPI_VS_OUT_ID = %d' % max(1, (len(params) + 3) // 4)]
        for k, loc in enumerate(params):
            hdr.append('; $SPI_VS_OUT_ID[%d].SEMANTIC_%d = %d' % (k // 4, k % 4, loc))
        hdr += ['; $SPI_VS_OUT_CONFIG.VS_EXPORT_COUNT = %d' % max(0, len(params) - 1)]
        cf.append('CALL_FS NO_BARRIER')
        kc = ' '.join('KCACHE%d(CB%d:0-31)' % (k, cb) for cb, k in sorted(banks.items(), key=lambda x: x[1]))
        clause, slots, gno = [], 0, 0
        for op, dst, srcs in groups:
            nlit = len({s.v for s in srcs if s.kind == 'lit'})
            need = 1 + (nlit + 1) // 2
            if slots + need > CLAUSE_SLOTS:
                cf.append(('ALU', clause))
                clause, slots = [], 0
            d, ch = sl(dst)
            unit = 't' if op in TRANS_ONLY else CH[ch]
            clause.append('  %d %s: %s %s, %s' % (gno, unit, op, d, ', '.join(src(s) for s in srcs)))
            gno += 1
            slots += need
        if clause:
            cf.append(('ALU', clause))
        pos = sl(('n', self.vec['gl_Position']))[0].split('.')[0]
        cf.append('EXP_DONE: POS0, %s.xyzw' % pos)
        for k, loc in enumerate(params):
            r = sl(('n', self.vec['out_attr%d' % loc]))[0].split('.')[0]
            cf.append('%s: PARAM%d, %s.xyzw NO_BARRIER' % ('EXP_DONE' if k == len(params) - 1 else 'EXP', k, r))
        for k, c in enumerate(cf):
            if isinstance(c, tuple):
                lines.append('%02d ALU: %s' % (k, kc))
                lines += c[1]
            else:
                lines.append('%02d %s' % (k, c))
        lines.append('END_OF_PROGRAM')
        self.ngpr = ngpr
        return '\n'.join(hdr) + '\n\n' + '\n'.join(lines) + '\n'


def lower(glsl, consts, attrib_names=None, mode='identity', zratio=1.0):
    """latte-asm source of a translated Ultimate vertex program; consts {buffer: words} for the baked buffers"""
    return Lowering(glsl, consts, attrib_names, mode, zratio).run().text()


def assemble(text):
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, 'a.vsh'), os.path.join(d, 'a.gsh')
        open(src, 'w').write(text)
        r = subprocess.run([ASM, 'assemble', '--vsh', src, out], capture_output=True, text=True)
        if r.returncode or not os.path.exists(out) or r.stdout.strip() or r.stderr.strip():
            raise RuntimeError('latte-asm: ' + (r.stdout + r.stderr).strip()[:2000])
        return open(out, 'rb').read()
