#!/usr/bin/env python3
"""An ssbu-recomp fighter dump's function, annotated for reading: imported calls named (demangled), the
lua2cpp const table's reads marked CONST[offset], hash40s rebuilt and named, calls into other dump
functions marked with what they read (recomp_hashes), float bit patterns shown as floats.

  python3 tools/recomp_annotate.py DUMP_DIR FUNC [FUNC ...] [--vl VL_PRC --labels CSV] [--regs DUMP_DIR]
  python3 tools/recomp_annotate.py DUMP_DIR --status          the status table (sv_set_status_func calls)

DUMP_DIR: ssbu-recomp's output for one fighter (lua2cpp_<name>/: c_*.c, imports.c, table.c; the user's
lua2cpp_decomp.zip, gen_nro_eh_o2/). Each function is `f_<addr>` (a wrapper) and `u_<addr>` (the body,
one C line per AArch64 instruction). Imported functions are PLT stubs `f_<addr>` calling
nro_import(c, &mod, N): N indexes imports.c's dynamic symbols.

The const table: lua2cpp code reads every lua constant (status kinds, flags, work ids, kinetic types...)
as rd32(table + offset), the table being the imported `L2CAgentGeneratedBase::const_value_table__`
(lua2cpp_common's, filled at run time: its values aren't in the dump), its address loaded from the GOT.
The GOT's contents aren't in the dump either, so the table register is found by its use: a register
loaded from a GOT slot (rd64 of 0x<got> + n) that is then read with rd32 at many offsets. CONST[o] is
the same constant wherever it appears (in status code and in the animcmd functions, whose smashline
sources name them: compare to get names).

--status: every sv_set_status_func call with its status const, condition const and function address.
"""
import argparse
import glob
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STUB = re.compile(r'void (f_[0-9a-f]+)\(Ctx \*c\) \{ nro_import\(c, &\w+, (\d+)\); \}')
BODY = re.compile(r'void u_([0-9a-f]+)\(Ctx \*c, uint64_t rp\) \{')
CALL = re.compile(r'(f_[0-9a-f]+)\(c\);')
SETX = re.compile(r'c->x\[(\d+)\] = \(uint64_t\)\((0x[0-9a-f]+)ULL\);')
GOTLD = re.compile(r'uint64_t a = c->x\[(\d+)\] \+ (\d+)ULL; c->x\[(\d+)\] = \(uint64_t\)\(rd64\(a\)\);')
RD32 = re.compile(r'uint64_t a = c->x\[(\d+)\] \+ (\d+)ULL; c->x\[(\d+)\] = \(uint64_t\)\(rd32\(a\)\);')
MOVZ = re.compile(r'c->x\[(\d+)\] = \(uint64_t\)\((0x[0-9a-f]+)ULL\);')
MOVK = re.compile(r'c->x\[(\d+)\] = \(uint64_t\)\(\(c->x\[(\d+)\] & ~(0x[0-9a-f]+)ULL\) \| (0x[0-9a-f]+)ULL\);')
FLOATBITS = re.compile(r'0x([0-9a-f]{8})U(?:LL)?\b')


def demangle(names):
    try:
        out = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True).stdout.splitlines()
        return out if len(out) == len(names) else names
    except OSError:
        return names


class Dump:
    def __init__(self, path):
        self.path = path
        self.files = sorted(glob.glob(os.path.join(path, 'c_*.c')))
        raw = []
        for line in open(os.path.join(path, 'imports.c'), errors='replace'):
            m = re.match(r'\s*\{ "([^"]*)",', line)
            if m:
                raw.append(m.group(1))
        self.imports = demangle(raw)
        self.stubs = {}
        self.bodies = {}
        for f in self.files:
            text = open(f, errors='replace').read()
            for m in STUB.finditer(text):
                self.stubs[m.group(1)] = short(self.imports[int(m.group(2))])
            for m in BODY.finditer(text):
                self.bodies[m.group(1)] = (f, m.start())

    def body(self, addr):
        f, i = self.bodies[addr]
        text = open(f, errors='replace').read()
        return text[i:text.find('\n}\n', i) + 2]


def short(name):
    """app::lua_bind::WorkModule__on_flag_impl(...) -> WorkModule::on_flag"""
    n = re.sub(r'\(.*$', '', name)
    n = n.replace('app::lua_bind::', '').replace('_impl', '').replace('__', '::')
    return n


def annotate(d, addr, hashes=None, regs_named=None):
    text = d.body(addr)
    got_regs = {}           # register -> 'GOT+n' loaded from the GOT page
    page_regs = {}          # register -> GOT page address
    table_regs = set()
    regs = {}
    out = []
    lines = text.splitlines()
    # first pass: registers loaded from a GOT slot and read with rd32 at 3+ offsets are the const table
    reads = {}
    for line in lines:
        m = SETX.search(line)
        if m and int(m.group(2), 16) >> 24 == 0x7204:
            page_regs[m.group(1)] = int(m.group(2), 16)
        m = GOTLD.search(line)
        if m and m.group(1) in page_regs:
            got_regs[m.group(3)] = page_regs[m.group(1)] + int(m.group(2))
        m = RD32.search(line)
        if m and m.group(1) in got_regs:
            reads.setdefault(got_regs[m.group(1)], set()).add(int(m.group(2)))
    table_slots = {s for s, offs in reads.items() if len(offs) >= 1}
    page_regs, got_regs = {}, {}
    for line in lines:
        note = []
        m = SETX.search(line)
        if m and int(m.group(2), 16) >> 24 == 0x7204:
            page_regs[m.group(1)] = int(m.group(2), 16)
        m = GOTLD.search(line)
        if m and m.group(1) in page_regs:
            got_regs[m.group(3)] = page_regs[m.group(1)] + int(m.group(2))
        m = RD32.search(line)
        if m and got_regs.get(m.group(1)) in table_slots:
            note.append('CONST[%d]' % int(m.group(2)))
        m = MOVZ.search(line)
        if m:
            regs[m.group(1)] = int(m.group(2), 16)
        m = MOVK.search(line)
        if m and m.group(1) == m.group(2) and m.group(1) in regs:
            v = (regs[m.group(1)] & ~int(m.group(3), 16)) | int(m.group(4), 16)
            regs[m.group(1)] = v
            if regs_named and v in regs_named:
                note.append('hash40 %s' % regs_named[v])
            elif v >> 32 and v < 1 << 40:
                note.append('hash40 0x%x' % v)
        for c in CALL.findall(line):
            if c in d.stubs:
                note.append(d.stubs[c])
            elif hashes and c in hashes:
                note.append('%s [%s]' % (c, hashes[c][:120]))
        for h in FLOATBITS.findall(line):
            v = int(h, 16)
            if 0x3a000000 <= v <= 0x48000000 or 0xba000000 <= v <= 0xc8000000:
                note.append('%gf' % struct.unpack('<f', struct.pack('<I', v))[0])
        line = re.sub(r'^L_[0-9a-f]+: ', lambda mm: mm.group(0)[2:], line)
        out.append(line + ('    // ' + '; '.join(note) if note else ''))
    return '\n'.join(out)


def status_table(d):
    """(status const offset, condition const offset, function) per sv_set_status_func call"""
    want = [k for k, v in d.stubs.items() if 'sv_set_status_func' in v]
    rows = []
    for addr in d.bodies:
        text = d.body(addr)
        if not any(w + '(c)' in text for w in want):
            continue
        last = {}
        regs = {}
        for line in text.splitlines():
            m = RD32.search(line)
            if m:
                last[m.group(3)] = int(m.group(2))
            m = SETX.search(line)
            if m:
                regs[m.group(1)] = int(m.group(2), 16)
            m = re.search(r'c->x\[(\d+)\] = \(uint64_t\)\(c->x\[(\d+)\] \+ (\d+)ULL\);', line)
            if m and m.group(2) in regs and m.group(1) == m.group(2):
                regs[m.group(1)] += int(m.group(3))
            m = re.search(r'f_720404af80\(c\);', line)            # L2CValue(int): remember the order
            if m:
                last.setdefault('_ints', []).append(last.get('1'))
            if any(w + '(c)' in line for w in want):
                ints = last.get('_ints', [])
                rows.append((ints[-2] if len(ints) > 1 else None, ints[-1] if ints else None,
                             'f_%x' % regs['3'] if '3' in regs else '?', addr))
                last['_ints'] = []
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump')
    ap.add_argument('funcs', nargs='*')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--hashes', help="recomp_hashes.py's output, to mark calls with what they read")
    ap.add_argument('--vl')
    ap.add_argument('--labels')
    a = ap.parse_args()
    d = Dump(a.dump)
    if a.status:
        for s, cond, fn, where in status_table(d):
            print('status CONST[%s] cond CONST[%s] -> %s   (registered in u_%s)' % (s, cond, fn, where))
        return
    hashes = {}
    if a.hashes:
        for line in open(a.hashes):
            if line.startswith('f_') and ':' in line:
                k, v = line.split(':', 1)
                hashes[k] = v.strip()
    named = {}
    if a.vl and a.labels:
        import recomp_hashes as R
        import ultimate_acmd as U
        names = R.label_names(a.vl, a.labels)
        for line in open(a.labels, errors='replace'):
            p = line.strip().split(',', 1)
            if len(p) == 2:
                names.add(p[1])
        named = {U.hash40(n): n for n in names if n}
    for f in a.funcs:
        print(annotate(d, f.replace('f_', '').replace('u_', ''), hashes, named))
        print()


if __name__ == '__main__':
    main()
