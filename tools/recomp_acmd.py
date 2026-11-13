#!/usr/bin/env python3
"""An ssbu-recomp dump's animcmd (ACMD) functions read back as script lines: frame / wait and every sv_animcmd call
with its arguments, decoded from the L2CValues pushed on the lua stack.

  python3 tools/recomp_acmd.py DUMP_DIR [FUNC ...] [--names NAME ...] [--find NAME ...]

DUMP_DIR: lua2cpp_<name>/ (c_*.c, imports.c; the user's lua2cpp_decomp.zip). FUNC: u_ function addresses (hex).
--names: extra hash40 names to recognise (effect, bone, sound names); the Ultimate fighter's own bone names and
the effect / sound names in fighters/*/<name>_effects.json are added by the caller as needed. --find NAME: list
the functions that build those hash40s (an effect name finds its effect scripts).

What it can and can't read: integers, hash40s (named when the name is known, else hex) and floats an fmov can
encode (1.0, 8.5, -0.5 ...) are in the code; other floats are loaded from the NRO's .rodata, which the dump does
not have: they print as `?f(+offset)` (the literal's offset from its page; the same offset is the same value
within one function). Branches (is_excute, conditions) are followed linearly: every call in the function is
listed in code order, with the frame waits between them.
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import zlib

STUB = re.compile(r'void (f_[0-9a-f]+)\(Ctx \*c\) \{ nro_import\(c, &\w+, (\d+)\); \}')
BODY = re.compile(r'void u_([0-9a-f]+)\(Ctx \*c, uint64_t rp\) \{')
SET64 = re.compile(r'^c->x\[(\d+)\] = \(uint64_t\)\((0x[0-9a-f]+|\d+)ULL\);')
SET32 = re.compile(r'^c->x\[(\d+)\] = \(uint32_t\)\((?:0U \| )?(0x[0-9a-f]+ULL|0U)\);')
MOVK = re.compile(r'^c->x\[(\d+)\] = \(uint64_t\)\(\(c->x\[(\d+)\] & ~(0x[0-9a-f]+)ULL\) \| (0x[0-9a-f]+)ULL\);')
COPY = re.compile(r'^c->x\[(\d+)\] = \(uint64_t\)\(0ULL \| c->x\[(\d+)\]\);')
SLOT = re.compile(r'^c->x\[(\d+)\] = \(uint64_t\)\(c->x\[(29|31)\] ([-+]) (\d+)ULL\);')
FIMM = re.compile(r'float t = fnan32\(\(float\)([-0-9.e+]+)\); vzero\(&c->v\[(\d+)\]\)')
FLIT = re.compile(r'uint64_t a = c->x\[\d+\] \+ (\d+)ULL; c->v\[(\d+)\] = rdv\(a, 4\);')
CALL = re.compile(r'(f_[0-9a-f]+)\(c\);')
NEG32 = re.compile(r'^c->x\[(\d+)\] = \(uint32_t\)\((?:0U \| )?~\(?(0x[0-9a-f]+)ULL\)?\);')


def hash40(s):
    return zlib.crc32(s.encode()) | (len(s) << 32)


def load(dump):
    syms = []
    for line in open(os.path.join(dump, 'imports.c')):
        m = re.match(r'\s*\{ "([^"]*)",', line)
        if m:
            syms.append(m.group(1))
    stubs, bodies = {}, {}
    for f in sorted(glob.glob(os.path.join(dump, 'c_*.c'))):
        cur = None
        for line in open(f):
            m = STUB.search(line)
            if m:
                stubs[m.group(1)] = syms[int(m.group(2))]
                continue
            m = BODY.match(line)
            if m:
                cur = m.group(1)
                bodies[cur] = []
                continue
            if cur is not None:
                if line.startswith('}'):
                    cur = None
                else:
                    bodies[cur].append(line)
    return stubs, bodies


def demangle(names):
    try:
        out = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True).stdout.splitlines()
        return dict(zip(names, out)) if len(out) == len(names) else {n: n for n in names}
    except OSError:
        return {n: n for n in names}


def decode(lines, stubs, dm, names):
    x, v, slots, stack, out = {}, {}, {}, [], []

    def show(val):
        if isinstance(val, tuple) and val[0] == 'h':
            return names.get(val[1], '0x%x' % val[1])
        if isinstance(val, tuple) and val[0] == 'f':
            return val[1]
        return str(val)
    for line in lines:
        code = re.sub(r'^(L_[0-9a-f]+:\s*)', '', line.strip())
        m = SET64.match(code)
        if m:
            x[m.group(1)] = int(m.group(2), 0)
            continue
        m = SET32.match(code)
        if m:
            x[m.group(1)] = 0 if m.group(2) == '0U' else int(m.group(2)[:-3], 16)
            continue
        m = NEG32.match(code)
        if m:
            x[m.group(1)] = (~int(m.group(2), 16)) & 0xFFFFFFFF
            continue
        m = MOVK.match(code)
        if m and m.group(1) == m.group(2) and isinstance(x.get(m.group(1)), int):
            x[m.group(1)] = (x[m.group(1)] & ~int(m.group(3), 16)) | int(m.group(4), 16)
            continue
        m = COPY.match(code)
        if m:
            x[m.group(1)] = x.get(m.group(2))
            continue
        m = SLOT.match(code)
        if m:
            x[m.group(1)] = ('slot', (m.group(2), m.group(3), int(m.group(4))))
            continue
        m = FIMM.search(code)
        if m:
            v[m.group(2)] = ('f', '%g' % float(m.group(1)))
            continue
        m = FLIT.search(code)
        if m:
            v[m.group(2)] = ('f', '?f(+%d)' % int(m.group(1)))
            continue
        m = CALL.search(code)
        if not m or m.group(1) not in stubs:
            continue
        sym = stubs[m.group(1)]
        name = dm.get(sym, sym)
        if 'L2CValue::L2CValue' in name or sym.startswith('_ZN3lib8L2CValueC1'):
            s = x.get('0')
            val = None
            if sym.endswith('Ef'):
                val = v.get('0', ('f', '?'))
            elif sym.endswith('EN3phx6Hash40E'):
                h = x.get('1')
                val = ('h', h & 0xFFFFFFFFFF) if isinstance(h, int) else '?h'
            elif sym.endswith(('Ei', 'Ej', 'El', 'Em')):
                h = x.get('1')
                if isinstance(h, int):
                    h &= 0xFFFFFFFF
                    val = h - (1 << 32) if h & 0x80000000 else h
                else:
                    val = '?i'
            elif sym.endswith('Eb'):
                h = x.get('1')
                val = ('true' if h else 'false') if isinstance(h, int) else '?b'
            if isinstance(s, tuple) and s[0] == 'slot':
                slots[s[1]] = val
            continue
        if 'clear_lua_stack' in name:
            stack = []
            continue
        if 'push_lua_stack' in name:
            s = x.get('1')
            stack.append(slots.get(s[1], '?') if isinstance(s, tuple) and s[0] == 'slot' else '?')
            continue
        if 'sv_animcmd::' in name:
            fn = name.split('sv_animcmd::')[1].split('(')[0]
            if fn in ('is_excute',):
                continue
            out.append('%s(%s)' % (fn, ', '.join(show(a) for a in stack)))
            stack = []
        elif name.startswith(('app::lua_bind', 'app::')) and '::' in name:
            out.append('  [%s]' % name.split('(')[0])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dump')
    ap.add_argument('funcs', nargs='*')
    ap.add_argument('--names', nargs='*', default=[])
    ap.add_argument('--find', nargs='*', default=[])
    a = ap.parse_args()
    stubs, bodies = load(a.dump)
    dm = demangle(sorted(set(stubs.values())))
    names = {hash40(n): n for n in a.names + a.find}
    if a.find:
        want = {hash40(n) & 0xFFFFFFFF: n for n in a.find}
        for f, lines in sorted(bodies.items()):
            got = set()
            for val in [x for x in decode(lines, stubs, dm, names)]:
                for n in a.find:
                    if n in val:
                        got.add(n)
            if got:
                print(f, sorted(got))
        del want
    for f in a.funcs:
        print('== u_%s' % f)
        for line in decode(bodies[f], stubs, dm, names):
            print('  ' + line)


if __name__ == '__main__':
    main()
