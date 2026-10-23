#!/usr/bin/env python3
"""Read / write / disassemble the game's compiled Xtal scripts (ui/script/**/*.xtal).

  python3 tools/xtal.py dis FILE.xtal [OUT.txt]      disassembly (functions, classes, values)
  python3 tools/xtal.py check FILE.xtal              parse + rebuild, must be byte-identical

Xtal (Ishibashi's embeddable script language, Google Code `xtal-language`) serialises a compiled
`Code` object (xtal_serializer.cpp, version 2.0): 'xtal' 02 00 00 00, the bytecode as u16 words,
scope / class / function / except / line-number tables, the once-table size, the source name,
the identifier table and the value table (tagged values), then the breakpoint map.

Instructions (xtal_inst.h, register VM): the opcode is the low byte of the first word; operands
follow at natural alignment in a byte stream laid out over the u16 words (byte 1 = high byte of
word 0, byte 2 = low byte of word 1 ...). address16 operands are relative to the instruction start.
"""
import struct
import sys

# serializer tags
SERIAL_NEW, NAME, REFERENCE, TNULL, TUNDEFINED, TFALSE, TTRUE, TINT32, TINT64, TFLOAT32, TFLOAT64, \
    TSTRING8, TSTRING16, TSTRING32, TID8, TID16, TID32, TARRAY, TMAP, TVALUES = range(20)

SIZES = {'i8': 1, 'u8': 1, 'i16': 2, 'u16': 2, 'address16': 2}

# opcode: (name, [(type, field)]) — trunk xtal_inst.h
INSTS = {
    0: ('Line', []), 1: ('LoadValue', [('i8', 'result'), ('u8', 'value')]),
    2: ('LoadConstant', [('i8', 'result'), ('u16', 'value_number')]),
    3: ('LoadInt1Byte', [('i8', 'result'), ('i8', 'value')]),
    4: ('LoadFloat1Byte', [('i8', 'result'), ('i8', 'value')]),
    5: ('LoadCallee', [('i8', 'result')]), 6: ('LoadThis', [('i8', 'result')]),
    7: ('Copy', [('i8', 'result'), ('i8', 'target')]),
}
for _n, _name in ((8, 'Inc'), (9, 'Dec'), (10, 'Pos'), (11, 'Neg'), (12, 'Com')):
    INSTS[_n] = (_name, [('i8', 'result'), ('i8', 'target'), ('i8', 'stack_base')])
for _n, _name in enumerate(('Add', 'Sub', 'Cat', 'Mul', 'Div', 'Mod', 'And', 'Or', 'Xor', 'Shl', 'Shr', 'Ushr'), 13):
    INSTS[_n] = (_name, [('i8', 'result'), ('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base'), ('u8', 'assign')])
INSTS.update({
    25: ('At', [('i8', 'result'), ('i8', 'target'), ('i8', 'index'), ('i8', 'stack_base')]),
    26: ('SetAt', [('i8', 'target'), ('i8', 'index'), ('i8', 'value'), ('i8', 'stack_base')]),
    27: ('Goto', [('address16', 'address')]),
    28: ('Not', [('i8', 'result'), ('i8', 'target')]),
    29: ('If', [('i8', 'target'), ('address16', 'address_true'), ('address16', 'address_false')]),
    30: ('IfEq', [('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    31: ('IfLt', [('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    32: ('IfRawEq', [('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    33: ('IfIs', [('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    34: ('IfIn', [('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    35: ('IfUndefined', [('i8', 'target'), ('address16', 'address_true'), ('address16', 'address_false')]),
    36: ('IfDebug', [('address16', 'address')]),
    37: ('Push', [('i8', 'target')]), 38: ('Pop', [('i8', 'result')]),
    39: ('AdjustValues', [('u8', 'stack_base'), ('u8', 'result_count'), ('u8', 'need_result_count')]),
    40: ('LocalVariable', [('i8', 'result'), ('u16', 'number'), ('u8', 'depth')]),
    41: ('SetLocalVariable', [('i8', 'target'), ('u16', 'number'), ('u8', 'depth')]),
    42: ('InstanceVariable', [('i8', 'result'), ('u16', 'info_number'), ('u8', 'number')]),
    43: ('SetInstanceVariable', [('i8', 'value'), ('u16', 'info_number'), ('u8', 'number')]),
    44: ('InstanceVariableByName', [('i8', 'result'), ('u16', 'identifier_number')]),
    45: ('SetInstanceVariableByName', [('i8', 'value'), ('u16', 'identifier_number')]),
    46: ('FilelocalVariable', [('i8', 'result'), ('u16', 'value_number')]),
    47: ('SetFilelocalVariable', [('i8', 'value'), ('u16', 'value_number')]),
    48: ('FilelocalVariableByName', [('i8', 'result'), ('u16', 'identifier_number')]),
    49: ('SetFilelocalVariableByName', [('i8', 'value'), ('u16', 'identifier_number')]),
    50: ('Member', [('i8', 'result'), ('i8', 'target'), ('i16', 'primary')]),
    51: ('MemberEx', [('i8', 'result'), ('i8', 'target'), ('i16', 'primary'), ('i8', 'secondary'), ('u8', 'flags')]),
    52: ('Call', [('i8', 'result'), ('u8', 'need_result'), ('i8', 'target'), ('i8', 'stack_base'), ('u8', 'ordered')]),
    53: ('CallEx', [('i8', 'result'), ('u8', 'need_result'), ('i8', 'target'), ('i8', 'self'), ('i8', 'stack_base'),
                    ('u8', 'ordered'), ('u8', 'named'), ('u8', 'flags')]),
    54: ('Send', [('i8', 'result'), ('u8', 'need_result'), ('i8', 'target'), ('i16', 'primary'), ('i8', 'secondary'),
                  ('i8', 'stack_base'), ('u8', 'ordered')]),
    55: ('SendEx', [('i8', 'result'), ('u8', 'need_result'), ('i8', 'target'), ('i16', 'primary'), ('i8', 'secondary'),
                    ('i8', 'stack_base'), ('u8', 'ordered'), ('u8', 'named'), ('u8', 'flags')]),
    56: ('Property', [('i8', 'result'), ('i16', 'primary'), ('i8', 'target'), ('i8', 'stack_base')]),
    57: ('SetProperty', [('i16', 'primary'), ('i8', 'target'), ('i8', 'stack_base')]),
    58: ('ScopeBegin', [('u16', 'info_number')]), 59: ('ScopeEnd', []),
    60: ('Return', [('i8', 'base'), ('u8', 'result_count')]),
    61: ('Yield', [('i8', 'result'), ('u8', 'need_result_count'), ('u8', 'base'), ('i8', 'result_count')]),
    62: ('Exit', []),
    63: ('Range', [('i8', 'result'), ('u8', 'kind'), ('i8', 'lhs'), ('i8', 'rhs'), ('i8', 'stack_base')]),
    64: ('Once', [('i8', 'result'), ('address16', 'address'), ('u16', 'value_number')]),
    65: ('SetOnce', [('i8', 'target'), ('u16', 'value_number')]),
    66: ('MakeArray', [('i8', 'result')]), 67: ('ArrayAppend', [('i8', 'target'), ('i8', 'value')]),
    68: ('MakeMap', [('i8', 'result')]), 69: ('MapInsert', [('i8', 'target'), ('i8', 'key'), ('i8', 'value')]),
    70: ('MapSetDefault', [('i8', 'target'), ('i8', 'value')]),
    71: ('ClassBegin', [('i8', 'mixin_base'), ('u16', 'info_number')]), 72: ('ClassEnd', [('i8', 'result')]),
    73: ('DefineClassMember', [('u16', 'number'), ('u16', 'primary'), ('i8', 'secondary'), ('u8', 'accessibility'),
                               ('i8', 'value')]),
    74: ('DefineMember', [('i8', 'target'), ('i16', 'primary'), ('i8', 'secondary'), ('u8', 'flags'), ('i8', 'value')]),
    75: ('MakeFun', [('i8', 'result'), ('u16', 'info_number'), ('address16', 'address')]),
    76: ('MakeInstanceVariableAccessor', [('i8', 'result'), ('u8', 'type'), ('u8', 'number'), ('u16', 'info_number')]),
    77: ('TryBegin', [('u16', 'info_number')]), 78: ('TryEnd', []),
    79: ('PushGoto', [('address16', 'address')]), 80: ('PopGoto', []), 81: ('Throw', []),
    82: ('Assert', [('i8', 'message')]), 83: ('BreakPoint', []),
})
BY_NAME = {v[0]: k for k, v in INSTS.items()}
LOAD_VALUES = ('null', 'undefined', 'false', 'true')


def layout(ops):
    """[(type, field, byte offset)], size in words"""
    out, off = [], 1
    for t, f in ops:
        s = SIZES[t]
        off = (off + s - 1) & ~(s - 1)
        out.append((t, f, off))
        off += s
    return out, (off + 1) // 2


LAYOUT = {k: layout(v[1]) for k, v in INSTS.items()}


def _bytes(words):
    b = bytearray()
    for w in words:
        b += bytes((w & 0xFF, w >> 8))      # byte 0 = low byte of word 0 (the opcode)
    return b


def decode(code, pc):
    """(opcode, {field: value}, size in words) of the instruction at word pc"""
    op = code[pc] & 0xFF
    if op not in INSTS:
        raise ValueError('bad opcode %d at %d' % (op, pc))
    lay, size = LAYOUT[op]
    b = _bytes(code[pc:pc + size])
    f = {}
    for t, name, off in lay:
        if t in ('i8', 'u8'):
            v = b[off]
            if t == 'i8' and v >= 0x80:
                v -= 0x100
        else:
            v = b[off] | b[off + 1] << 8
            if t != 'u16' and v >= 0x8000:
                v -= 0x10000
        f[name] = v
    return op, f, size


def encode(op, **fields):
    lay, size = LAYOUT[op]
    b = bytearray(size * 2)
    b[0] = op
    for t, name, off in lay:
        v = fields.get(name, 0)
        if t in ('i8', 'u8'):
            b[off] = v & 0xFF
        else:
            b[off] = v & 0xFF
            b[off + 1] = (v >> 8) & 0xFF
    return [b[2 * i] | b[2 * i + 1] << 8 for i in range(size)]


class R:
    def __init__(self, d, o=0):
        self.d, self.o = d, o

    def get(self, fmt):
        v = struct.unpack_from('>' + fmt, self.d, self.o)
        self.o += struct.calcsize('>' + fmt)
        return v[0] if len(v) == 1 else v


class Ref:
    def __init__(self, n):
        self.n = n

    def __repr__(self):
        return 'Ref(%d)' % self.n


class Str(str):
    """a string value (TSTRING8); a subclass so every value is its own object (the serializer's
    references are by object)"""


class Ident(str):
    """an interned string (TID8)"""


class Code:
    SCOPE = 'IBBHHH'

    def __init__(self, data=None):
        if data is not None:
            self.parse(data)

    # values -------------------------------------------------------------------------------------
    def _value(self, r):
        tag = r.get('B')
        if tag == TNULL:
            return None
        if tag == TUNDEFINED:
            return ('undefined',)
        if tag == TFALSE:
            return False
        if tag == TTRUE:
            return True
        if tag == TINT32:
            return r.get('i')
        if tag == TFLOAT32:
            return r.get('f')
        if tag in (TSTRING8, TID8):
            n = r.get('I')
            s = r.d[r.o:r.o + n].decode('latin-1')
            r.o += n
            s = Ident(s) if tag == TID8 else Str(s)
            self._vals.append(s)
            return s
        if tag == REFERENCE:
            return Ref(r.get('I'))
        if tag == TARRAY:
            n = r.get('I')
            a = []
            self._vals.append(a)
            for _ in range(n):
                a.append(self._value(r))
            return a
        if tag == TMAP:
            n = r.get('I')
            m = []
            self._vals.append(m)
            for _ in range(n):
                m.append((self._value(r), self._value(r)))
            return ('map', m)
        if tag == NAME:
            h = [None]
            self._vals.append(h)
            h[0] = self._value(r)
            return ('name', h)
        if tag == TVALUES:
            v = []
            self._vals.append(v)
            v.append(self._value(r))
            v.append(self._value(r))
            return ('values', v)
        raise ValueError('value tag %d at 0x%X' % (tag, r.o - 1))

    def _reg(self, obj):
        self._new[id(obj)] = len(self._keep)
        self._keep.append(obj)

    def _put_value(self, out, v):
        if v is None:
            out += b'\x03'
        elif isinstance(v, tuple) and v == ('undefined',):
            out += b'\x04'
        elif v is False:
            out += b'\x05'
        elif v is True:
            out += b'\x06'
        elif isinstance(v, bool):
            raise ValueError(v)
        elif isinstance(v, int):
            out += struct.pack('>Bi', TINT32, v)
        elif isinstance(v, float):
            out += struct.pack('>Bf', TFLOAT32, v)
        elif isinstance(v, Ref):                # renumbered: the object's index in this write
            out += struct.pack('>BI', REFERENCE, self._new[id(self._vals[v.n])])
        elif isinstance(v, str):
            assert isinstance(v, (Str, Ident)), 'use Str / Ident for new strings'
            e = v.encode('latin-1')
            out += struct.pack('>BI', TID8 if isinstance(v, Ident) else TSTRING8, len(e)) + e
            self._reg(v)
        elif isinstance(v, list):
            out += struct.pack('>BI', TARRAY, len(v))
            self._reg(v)
            for x in v:
                self._put_value(out, x)
        elif isinstance(v, tuple) and v[0] == 'map':
            out += struct.pack('>BI', TMAP, len(v[1]))
            self._reg(v[1])
            for k, x in v[1]:
                self._put_value(out, k)
                self._put_value(out, x)
        elif isinstance(v, tuple) and v[0] == 'name':
            out += bytes((NAME,))
            self._reg(v[1])
            self._put_value(out, v[1][0])
        elif isinstance(v, tuple) and v[0] == 'values':
            out += bytes((TVALUES,))
            self._reg(v[1])
            self._put_value(out, v[1][0])
            self._put_value(out, v[1][1])
        else:
            raise ValueError(repr(v))

    # code object ----------------------------------------------------------------------------------
    def parse(self, d):
        assert d[:6] == b'xtal\x02\x00', d[:8]
        self._vals = [self]                 # the serializer's reference table (the Code itself is 0)
        r = R(d, 8)
        n = r.get('I')
        self.code = list(struct.unpack_from('>%dH' % n, d, r.o))
        r.o += 2 * n
        self.scopes = [r.get(self.SCOPE) for _ in range(r.get('H'))]
        self.classes = [(r.get(self.SCOPE), r.get('HHHB')) for _ in range(r.get('H'))]
        self.funs = [(r.get(self.SCOPE), r.get('HHHBB')) for _ in range(r.get('H'))]
        self.excepts = [r.get('III') for _ in range(r.get('H'))]
        self.lines = [r.get('IH') for _ in range(r.get('H'))]
        self.once = r.get('H')
        self.source = self._value(r)
        self.idents = [self._value(r) for _ in range(r.get('H'))]
        self.values = [self._value(r) for _ in range(r.get('H'))]
        self.breakpoints = self._value(r)
        self.tail = d[r.o:]

    def data(self):
        self._new, self._keep = {}, []
        self._reg(self)
        out = bytearray(b'xtal\x02\x00\x00\x00')
        out += struct.pack('>I', len(self.code)) + struct.pack('>%dH' % len(self.code), *self.code)
        out += struct.pack('>H', len(self.scopes))
        for s in self.scopes:
            out += struct.pack('>' + self.SCOPE, *s)
        out += struct.pack('>H', len(self.classes))
        for s, c in self.classes:
            out += struct.pack('>' + self.SCOPE, *s) + struct.pack('>HHHB', *c)
        out += struct.pack('>H', len(self.funs))
        for s, f in self.funs:
            out += struct.pack('>' + self.SCOPE, *s) + struct.pack('>HHHBB', *f)
        out += struct.pack('>H', len(self.excepts))
        for e in self.excepts:
            out += struct.pack('>III', *e)
        out += struct.pack('>H', len(self.lines))
        for e in self.lines:
            out += struct.pack('>IH', *e)
        out += struct.pack('>H', self.once)
        self._put_value(out, self.source)
        out += struct.pack('>H', len(self.idents))
        for v in self.idents:
            self._put_value(out, v)
        out += struct.pack('>H', len(self.values))
        for v in self.values:
            self._put_value(out, v)
        self._put_value(out, self.breakpoints)
        return bytes(out) + self.tail

    # disassembly --------------------------------------------------------------------------------
    def instructions(self):
        pc = 0
        while pc < len(self.code):
            op, f, size = decode(self.code, pc)
            yield pc, op, f, size
            pc += size

    def resolve(self, v):
        """a value with references to earlier-serialised values replaced by those values"""
        while isinstance(v, Ref):
            v = self._vals[v.n]
        return v

    def ident(self, i):
        return self.resolve(self.idents[i]) if 0 <= i < len(self.idents) else '?%d' % i

    def fmt(self, pc, op, f):
        name = INSTS[op][0]
        parts = []
        for t, k in INSTS[op][1]:
            v = f[k]
            if t == 'address16':
                parts.append('%s=@%d' % (k, pc + v))
            elif k in ('primary', 'identifier_number') or (name == 'DefineClassMember' and k == 'primary'):
                parts.append('%s=%s' % (k, self.ident(v)))
            elif k == 'value_number' and name in ('LoadConstant',):
                parts.append('%s' % short(self.resolve(self.values[v])))
            elif name == 'LoadValue' and k == 'value':
                parts.append(LOAD_VALUES[v] if v < 4 else str(v))
            else:
                parts.append('%s=%d' % (k, v))
        return '%-26s %s' % (name, ' '.join(parts))

    def disassemble(self):
        starts = {}
        for i, (s, f) in enumerate(self.funs):
            starts.setdefault(s[0], []).append('fun %d %s params %d-%d stack %d vars %d' % (
                i, self.ident(f[2]), f[3], f[4], f[0], f[1]))
        for i, (s, c) in enumerate(self.classes):
            starts.setdefault(s[0], []).append('class %d %s' % (i, self.ident(c[2])))
        lines = []
        for pc, op, f, _ in self.instructions():
            for s in starts.get(pc, []):
                lines.append('\n; ---- %s' % s)
            if op == 0:
                continue
            lines.append('%5d  %s' % (pc, self.fmt(pc, op, f)))
        return '\n'.join(lines)


class Block:
    """new bytecode: ins(name, field=value, ...). An address16 field takes a label of the block
    (str), ('T', pc): the original instruction at pc, or code inserted before it, ('I', pc): the
    original instruction at pc itself (after code inserted before it)."""

    def __init__(self):
        self.items, self.labels = [], {}

    def ins(self, name, **fields):
        self.items.append((BY_NAME[name], fields))
        return self

    def label(self, name):
        self.labels[name] = len(self.items)
        return self

    @property
    def size(self):
        return sum(LAYOUT[op][1] for op, _ in self.items)

    def words(self, at, target, instr):
        pcs, pc = [], at
        for op, _ in self.items:
            pcs.append(pc)
            pc += LAYOUT[op][1]
        pcs.append(pc)
        out = []
        for i, (op, fields) in enumerate(self.items):
            f = dict(fields)
            for t, name in INSTS[op][1]:
                if t != 'address16':
                    continue
                v = f[name]
                if isinstance(v, str):
                    a = pcs[self.labels[v]]
                elif v[0] == 'T':
                    a = target(v[1])
                else:
                    a = instr(v[1])
                f[name] = a - pcs[i]
                assert -0x8000 <= f[name] < 0x8000
            out += encode(op, **f)
        return out


def _edit_code(c, edits):
    """edits: [(start, end, Block)] on original pcs: [start, end) replaced by the block (start == end:
    inserted before the instruction at start). Relocates jumps and the pc tables."""
    edits = sorted(edits, key=lambda e: (e[0], e[1]))
    for (s1, e1, _), (s2, _e2, _) in zip(edits, edits[1:]):
        assert e1 <= s2, 'overlapping edits at %d' % s2

    def target(p, lenient=False):
        d = 0
        for s, e, b in edits:
            if s == e:
                if s < p:
                    d += b.size
            elif e <= p:
                d += b.size - (e - s)
            elif s < p < e:
                if not lenient:
                    raise ValueError('a jump into the replaced range %d-%d (%d)' % (s, e, p))
                return target(s)
        return p + d

    def instr(p):
        return target(p) + sum(b.size for s, e, b in edits if s == e == p)
    old = list(c.instructions())
    new, k = [], 0
    pcs = [pc for pc, _, _, _ in old] + [len(c.code)]
    skip_to = -1
    for i, (pc, op, f, size) in enumerate(old + [(len(c.code), None, None, 0)]):
        while k < len(edits) and edits[k][0] == pc:
            s, e, b = edits[k]
            assert len(new) == target(pc), (pc, len(new), target(pc))
            new += b.words(len(new), target, instr)
            if e > s:
                assert e in pcs, 'edit end %d is not an instruction start' % e
                skip_to = e
            k += 1
        if op is None or pc < skip_to:
            continue
        for t, name in INSTS[op][1]:
            if t == 'address16':
                f[name] = target(pc + f[name]) - instr(pc)
                assert -0x8000 <= f[name] < 0x8000, 'jump out of range at %d' % pc
        assert len(new) == instr(pc)
        new += encode(op, **f)
    assert k == len(edits), 'edit past the end'
    c.code = new
    c.scopes = [(target(sc[0]),) + tuple(sc[1:]) for sc in c.scopes]
    c.classes = [((target(sc[0]),) + tuple(sc[1:]), x) for sc, x in c.classes]
    c.funs = [((target(sc[0]),) + tuple(sc[1:]), x) for sc, x in c.funs]
    c.excepts = [tuple(target(p) for p in e) for e in c.excepts]
    c.lines = [(target(p, True), n) for p, n in c.lines]     # a line inside a replaced range: its start
    return target, instr


Code.edit = _edit_code


def _const(c, s):
    """value-table index of string constant s (added if missing)"""
    for i, v in enumerate(c.values):
        if isinstance(c.resolve(v), str) and not isinstance(c.resolve(v), Ident) and c.resolve(v) == s:
            return i
    c.values.append(Str(s))
    return len(c.values) - 1


def _ident(c, s):
    """identifier-table index of s (added if missing)"""
    for i, v in enumerate(c.idents):
        if c.resolve(v) == s:
            return i
    c.idents.append(Ident(s))
    return len(c.idents) - 1


Code.const = _const
Code.ident_index = _ident


class Local(tuple):
    """a local variable register (negative), for table values: ('L', n) = register -n"""


def read_table(c, start, end):
    """the literal table built by the straight-line code [start, end): its last MakeMap / MakeArray
    into a negative register; values: str, int, None / True / False, ('L', n) (a copy of register -n),
    ('call', n, arg) (register -n called with one constant)"""
    regs, result, first = {}, None, None
    for pc, op, f, _ in c.instructions():
        if not start <= pc < end:
            continue
        n = INSTS[op][0]
        if n == 'Line':
            continue
        if n == 'LoadConstant':
            regs[f['result']] = str(c.resolve(c.values[f['value_number']]))
        elif n == 'LoadInt1Byte':
            regs[f['result']] = f['value']
        elif n == 'LoadValue':
            regs[f['result']] = (None, ('undefined',), False, True)[f['value']]
        elif n == 'MakeArray':
            regs[f['result']] = []
            first = f['result'] if first is None else first
        elif n == 'MakeMap':
            regs[f['result']] = {}
            first = f['result'] if first is None else first
        elif n == 'ArrayAppend':
            regs[f['target']].append(regs[f['value']])
        elif n == 'MapInsert':
            regs[f['target']][regs[f['key']]] = regs[f['value']]
        elif n == 'Copy' and f['target'] < 0:
            regs[f['result']] = ('L', -f['target'])
        elif n == 'Call' and f['target'] < 0 and f['ordered'] == 1:
            regs[f['result']] = ('call', -f['target'], regs[f['stack_base']])
        else:
            raise ValueError('not a literal table at %d: %s' % (pc, c.fmt(pc, op, f)))
        if f.get('result', 0) < 0:
            result = f['result']
    result = first if result is None else result
    return result, regs[result]


def gen_table(c, dest, value):
    """a Block building value (as read_table gives) into register dest"""
    b = Block()

    def emit(v, r):
        if isinstance(v, bool) or v is None:
            b.ins('LoadValue', result=r, value={None: 0, False: 2, True: 3}[v])
        elif isinstance(v, int):
            assert -128 <= v < 128
            b.ins('LoadInt1Byte', result=r, value=v)
        elif isinstance(v, str):
            b.ins('LoadConstant', result=r, value_number=c.const(v))
        elif isinstance(v, tuple) and v[0] == 'L':
            b.ins('Copy', result=r, target=-v[1])
        elif isinstance(v, tuple) and v[0] == 'call':
            emit(v[2], r + 1)
            b.ins('Call', result=r, need_result=1, target=-v[1], stack_base=r + 1, ordered=1)
        elif isinstance(v, list):
            b.ins('MakeArray', result=r)
            for x in v:
                emit(x, scratch(r) + 1)
                b.ins('ArrayAppend', target=r, value=scratch(r) + 1)
        elif isinstance(v, dict):
            b.ins('MakeMap', result=r)
            for k, x in v.items():
                emit(k, scratch(r) + 1)
                emit(x, scratch(r) + 2)
                b.ins('MapInsert', target=r, key=scratch(r) + 1, value=scratch(r) + 2)
        else:
            raise ValueError(v)

    def scratch(r):
        return -1 if r < 0 else r
    emit(value, dest)
    return b


def short(v, n=60):
    s = repr(v)
    return s if len(s) <= n else s[:n] + '...'


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    d = open(path, 'rb').read()
    c = Code(d)
    if cmd == 'check':
        same = c.data() == d
        print('identical' if same else 'DIFFERENT (%d vs %d bytes)' % (len(c.data()), len(d)))
        sys.exit(0 if same else 1)
    if cmd == 'dis':
        out = ['; %s' % c.source, '; identifiers:']
        out += ['  %3d %s' % (i, c.resolve(v)) for i, v in enumerate(c.idents)]
        out += ['; values:'] + ['  %3d %s' % (i, short(c.resolve(v), 200)) for i, v in enumerate(c.values)]
        out.append(c.disassemble())
        text = '\n'.join(out) + '\n'
        if len(sys.argv) > 3:
            open(sys.argv[3], 'w').write(text)
        else:
            sys.stdout.write(text)


if __name__ == '__main__':
    main()
