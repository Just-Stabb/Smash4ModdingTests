#!/usr/bin/env python3
"""Runs tools/diag_crumbs_cave.py's hooks in unicorn: the diagnostic executable against the one it was put on.

  python3 tools/diag_crumbs_test.py DIAG.rpx BASE.rpx

For every step: the same machine state (every GPR, CR, XER, CTR, LR, f0-f31, FPSCR set to distinct values, the
step's arguments in fake structs) is run from the hook to where the replaced word goes on (the next word; for a
replaced branch, its target) in both executables. The diagnostic one must end in the same state (LR aside after a
replaced bl, which returns through the stub's `b` back) and the same memory in the fake structs, having called
OSReport (its call site's bl, decoded as the stub does; a Python stub that clobbers every volatile register) once
with the format, the step's tag, the kind and its a / b for a kind that passes the filter, and not at all for one
that doesn't. The first-frames step stops after STEP_MAX crumbs.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_crumbs_cave as D  # noqa: E402
from kind_expand_test import Emu, REGS, STACK  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_CR, UC_PPC_REG_XER, UC_PPC_REG_CTR, UC_PPC_REG_LR, UC_PPC_REG_MSR,  # noqa
                               UC_PPC_REG_FPSCR, UC_PPC_REG_FPR0, UC_PPC_REG_1)
import unicorn.ppc_const as PC  # noqa: E402

FPRS = [getattr(PC, 'UC_PPC_REG_FPR%d' % i) for i in range(32)]
fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


def target(e, at):
    w = e.w(at)
    off = w & 0x3FFFFFC
    if off & 0x2000000:
        off -= 0x4000000
    return at + off


def import_relocs(path):
    """the RPX's relocations against imported symbols (a .fimport_* section's): [(address, type, symbol value, name)]"""
    import rpx_patch as R
    d, _o, _e, secs = R.load(path)
    shstr = R.section_data(d, secs[struct.unpack('>H', bytes(d[0x32:0x34]))[0]])

    def nm(off, tab):
        return bytes(tab[off:tab.index(b'\0', off)]).decode('latin1')
    out = []
    for s in secs:
        if s[1] != 4 or secs[s[7]][3] >= 0x10000000:              # SHT_RELA of .text
            continue
        symsec = secs[s[6]]
        syms, strt = R.section_data(d, symsec), R.section_data(d, secs[symsec[6]])
        data = R.section_data(d, s)
        for o in range(0, len(data), 12):
            off, info, add = struct.unpack('>IIi', data[o:o + 12])
            si = info >> 8
            n, val, _sz, _inf, _oth, shn = struct.unpack('>IIIBBH', syms[16 * si:16 * si + 16])
            if shn < len(secs) and nm(secs[shn][0], shstr).startswith('.fimport'):
                out.append((off, info & 0xFF, (val + add) & 0xFFFFFFFF, nm(n, strt)))
    return out


class M(Emu):
    """the executable as the loader leaves it for these tests: every ADDR16_HA / LO / ADDR32 relocation against an
    import filled in with the import's address (its .fimport section entry), a stub there for OSReport. REL24 calls
    to imports are not resolved (a loader makes them reach a thunk of its own; the crumbs mustn't depend on them)"""
    def __init__(self, path, osreport):
        super().__init__(path)
        self.calls = []
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        try:
            self.mu.mem_map(0xC0000000, 0x10000)
        except Exception:                                        # noqa: BLE001
            pass
        self.imports = {}
        for at, typ, val, name in import_relocs(path):
            self.imports.setdefault(name, val)
            w = self.w(at & ~3)
            if typ == 6:                                         # ADDR16_HA
                self.mu.mem_write(at, struct.pack('>H', ((val + 0x8000) >> 16) & 0xFFFF))
            elif typ == 4:                                       # ADDR16_LO
                self.mu.mem_write(at, struct.pack('>H', val & 0xFFFF))
            elif typ == 1:                                       # ADDR32
                self.setw(at, val)
            del w
        if osreport:
            self.stub(self.imports['OSReport'], self.osreport)

    def osreport(self, e):
        self.calls.append((self.cstr(self.r(3)), self.cstr(self.r(4))) + tuple(self.r(i) for i in range(5, 9)))
        for i in [0] + list(range(3, 13)):                       # clobber what a C function may
            self.mu.reg_write(REGS[i], 0xBAD00000 + i)
        for i in range(14):
            self.mu.reg_write(FPRS[i], 0x7FF8DEAD00000000 + i)
        self.mu.reg_write(UC_PPC_REG_CTR, 0xBADC7)
        self.mu.reg_write(UC_PPC_REG_CR, 0x12345678)

    def state(self):
        s = {'r%d' % i: self.r(i) for i in range(32)}
        s.update(cr=self.mu.reg_read(UC_PPC_REG_CR), xer=self.mu.reg_read(UC_PPC_REG_XER),
                 ctr=self.mu.reg_read(UC_PPC_REG_CTR), lr=self.mu.reg_read(UC_PPC_REG_LR),
                 fpscr=self.mu.reg_read(UC_PPC_REG_FPSCR) & 0xFFFFFFFF)
        s.update({'f%d' % i: self.mu.reg_read(FPRS[i]) for i in range(32)})
        return s


def setup(e, regs, mem):
    """the machine state: every register distinct, then the step's own"""
    for i in range(32):
        e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
    e.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)                 # the stack (Emu's)
    e.mu.reg_write(UC_PPC_REG_CR, 0x24800C42)
    e.mu.reg_write(UC_PPC_REG_XER, 0)                         # XER's CA comes from the prelude (run())
    e.mu.reg_write(UC_PPC_REG_CTR, 0xC7C7C7C7)
    e.mu.reg_write(UC_PPC_REG_LR, 0x4C4C4C4C)
    for i in range(32):
        e.mu.reg_write(FPRS[i], 0x4000000000000000 + (i << 40))
    for a, v in mem.items():
        e.setw(a, v)
    for r, v in regs.items():
        if r == 'ctr':
            e.mu.reg_write(UC_PPC_REG_CTR, v)
        elif r == 'lr':
            e.mu.reg_write(UC_PPC_REG_LR, v)
        else:
            e.mu.reg_write(REGS[r], v)


def run(e, at, stop):
    """from a prelude that sets XER's carry by an instruction (unicorn's XER write doesn't reach its CA), then the
    hook: `li r0, -1; addic r0, r0, 1; lis r0, 0x5A5A; b at`"""
    pre = e.pre
    e.pre += 16                                     # a fresh one each run (unicorn keeps translated code)
    assert e.pre <= D.LIMIT
    e.mu.mem_write(pre, struct.pack('>4I', 0x3800FFFF, 0x30000001, 0x3C005A5A,
                                    (18 << 26) | ((at - (pre + 12)) & 0x3FFFFFC)))
    from unicorn import UC_HOOK_CODE
    h = e.mu.hook_add(UC_HOOK_CODE, lambda mu, a, size, ud: mu.emu_stop(), None, stop, stop)
    try:
        e.mu.emu_start(pre, stop, count=4000)       # (`until` is only seen between translation blocks)
    finally:
        e.mu.hook_del(h)
    pc = e.mu.reg_read(PC.UC_PPC_REG_PC)
    assert pc == stop, 'stopped at 0x%08X, not 0x%08X' % (pc, stop)


def main():
    diag, base = sys.argv[1], sys.argv[2]
    E1, E0 = M(diag, True), M(base, False)
    # the call site the stub decodes: a bl in both
    ha_lo = [(at, typ) for at, typ, _v, nm in import_relocs(diag) if nm == 'OSReport' and typ in (4, 6)]
    check('the veneer\'s lis / addi are OSReport\'s ADDR16_HA / LO relocations',
          sorted(ha_lo), [(D.OSREPORT_VENEER + 10, 6), (D.OSREPORT_VENEER + 14, 4)])
    check('OSReport\'s import address (loader-relocated) stubbed: 0x%08X' % E1.imports['OSReport'],
          E1.imports['OSReport'] >> 24, 0xC0)
    F = E0.alloc(0x1000, b'\0')                                   # fake structs (the same address in both)
    assert E1.alloc(0x1000, b'\0') == F
    for e in (E0, E1):
        e.mu.mem_map(0, 0x1000)                                  # article-pool's null object: lwz r10, 0x24(0)
        e.pre = D.LIMIT - 0x1800                                 # preludes in the unused tail, b reach of every hook
    obj, acc, fs, req, mod, ent = F + 0x100, F + 0x200, F + 0x300, F + 0x400, F + 0x500, F + 0x600
    blr = F + 0xF00                                              # a blr for the module inits' bctrl
    hobj = 0x30000100                                            # a module-init object in the game's heap range
    for e in (E0, E1):
        e.mu.mem_map(0x30000000, 0x1000)
    # step tag -> [(regs, mem, the crumb expected (kind, a, b) or None)]
    cases = {
        'fighter-setup': [({3: fs, 4: 0x44, 5: 0x42}, {}, (0x42, fs, 0x44)), ({5: 0x10}, {}, None)],
        'fighter-resources': [({3: req}, {req + 0x24: 0x42, req + 0x3C: 0x01020304}, (0x42, req, 0x01020304)),
                              ({3: req}, {req + 0x24: 0x10}, None)],
        'effect-folder': [({3: 0x77, 4: 0x45}, {}, (0x45, 0x77, 0)), ({4: 0x10}, {}, None)],
        'weapon-files': [({3: 0x88, 4: 0x199, 5: 1}, {}, (0x199, 1, 0x88)), ({4: 0x22}, {}, None)],
        'effect-bank': [({3: 0x99, 4: 0x42}, {}, (0x42, 0x99, 0)), ({4: 0x2C}, {}, None)],
        'vl-load': [({3: 0x31, 29: 0x29}, {}, (0x42, 0x31, 0x29))],
        'zelda-setup': [({4: fs, 5: 1}, {fs + 4: 0x42}, (0x42, 1, fs)), ({4: fs}, {fs + 4: 0x10}, None)],
        'counter-group': [({31: mod}, {mod + 0x14: 2}, (0x42, 2, mod))],
        'fighter-modules': [({27: fs, 28: 0x42}, {}, (0x42, fs, 0)), ({28: 0x10}, {}, None)],
        'article-pool': [({3: obj, 22: ent, 30: 5}, {ent: 0x199, obj + 0x24: 0x1234}, (0x199, obj, 5)),
                         ({3: obj, 22: ent, 30: 5}, {ent: 0x22, obj + 0x24: 0x1234}, None),
                         ({3: 0, 22: ent, 30: 2}, {ent: 0x80000022}, (0x22, 0, 2))],
        'weapon-modules': [({30: 0x199, 31: obj}, {}, (0x199, obj, 0)), ({30: 0x22}, {}, None)],
        'weapon-params': [({3: 0x55, 4: 0x195, 5: 4}, {}, (0x195, 4, 0x55)), ({4: 0xB6}, {}, None)],
        'art-init24': [({3: obj, 24: 7}, {obj + 4: 0x19C}, (0x19C, 7, obj)), ({3: obj}, {obj + 4: 0x22}, None)],
        'art-init2c': [({25: ent, 24: 6}, {ent + 4: obj, obj + 4: 0x199}, (0x199, 6, obj)),
                       ({25: ent}, {ent + 4: obj, obj + 4: 0x23}, None)],
        'art-init10c': [({25: ent, 31: 0x40}, {ent + 4: obj, obj + 4: 0x19D}, (0x19D, 0x40, obj)),
                        ({25: ent}, {ent + 4: obj, obj + 4: 0x24}, None)],
        'art-done': [({25: ent, 24: 1}, {ent + 4: obj, ent + 8: 3, obj + 4: 0x18C}, (0x18C, 1, obj)),
                     ({25: ent}, {ent + 4: obj, ent + 8: 3, obj + 4: 0x25}, None)],
        'articles-done': [({29: 0x1234, 30: 0x5678}, {}, (0, 0x1234, 0x5678))],
        'acmd-cache': [({3: 0x66, 4: 0x19B}, {}, (0x19B, 0x66, 0)), ({4: 0x26}, {}, None)],
        'module-init': [({30: acc, 'ctr': blr}, {acc: hobj, hobj: 0x00010002, hobj + 4: 0x42}, (0x42, 'off', acc)),
                        ({30: acc, 'ctr': blr}, {acc: hobj, hobj: 0x10010002, hobj + 4: 0x42}, None),
                        ({30: acc, 'ctr': blr}, {acc: hobj, hobj: 0x00010002, hobj + 4: 0x10}, None),
                        ({30: acc, 'ctr': blr}, {acc: 0x50000000}, None),     # boot: not a pointer (v3's crash)
                        ({30: acc, 'ctr': blr}, {acc: 0}, None),
                        ({30: acc, 'ctr': blr}, {acc: obj}, None),            # outside the game's heap
                        ({30: acc, 'ctr': blr}, {acc: hobj + 2}, None)],
    }
    for e in (E0, E1):
        e.setw(blr, 0x4E800020)
    steps = D.all_steps(E0.w)
    check('the steps: v2\'s 13, 6 more, a module init each (%d)' % (len(steps) - 19), len(steps) > 19 + 30, True)
    import re
    for tag, at, _w0, _a, _what in steps:
        w0 = E0.w(at)
        stop = target(E0, at) if w0 >> 26 == 18 else at + 4
        link = (w0 >> 26 == 18 and w0 & 1) or w0 == 0x4E800421
        for k, (regs, mem, want) in enumerate(cases.get(tag, [])):
            if want and want[1] == 'off':
                want = (want[0], int(re.search(r'li r5, (0x[0-9A-F]+)', _a).group(1), 16), want[2])
            if tag == 'article-pool' and regs.get(3) == 0:
                pass                                              # lwz r10, 0x24(r3) on 0: map page 0
            res = []
            for e in (E0, E1):
                e.calls = []
                setup(e, regs, mem)
                run(e, at, stop)
                res.append(e.state())
            s0, s1 = res
            if link:
                lr1 = s1.pop('lr')
                s0.pop('lr')
                check('%s: after the replayed bl, LR at the stub\'s way back (b 0x%08X)' % (tag, at + 4),
                      target(E1, lr1), at + 4)
            diff = {r: (hex(s0[r]), hex(s1[r])) for r in s0 if s0[r] != s1[r]}
            check('%s case %d: every register as the original executable leaves it' % (tag, k), diff, {})
            mem_same = all(E0.w(a) == E1.w(a) for a in mem)
            check('%s case %d: the fake structs untouched' % (tag, k), mem_same, True)
            got = [(c[1], c[2], c[3], c[4]) for c in E1.calls]
            fmt_ok = all(c[0] == 'S4DIAG %s k=%X a=%X b=%X n=%d\n' for c in E1.calls)
            exp = [(tag, want[0], want[1] & 0xFFFFFFFF, want[2] & 0xFFFFFFFF)] if want else []
            check('%s case %d: OSReport %s' % (tag, k, 'once (tag, kind, a, b)' if want else 'not called'),
                  (got, fmt_ok), (exp, True))
    # the first frames: STEP_MAX crumbs in all, kinds below 0x41 never
    tag, at = 'frame', [s[1] for s in steps if s[0] == 'frame'][0]
    n_calls = []
    for k in range(D.STEP_MAX + 3):
        res = []
        for e in (E0, E1):
            e.calls = []
            kind = 0x10 if k == 1 else 0x42
            setup(e, {4: acc}, {acc: obj, obj: 0x1000002A, obj + 4: kind})
            run(e, at, at + 4)
            res.append(e.state())
        diff = {r: (hex(res[0][r]), hex(res[1][r])) for r in res[0] if res[0][r] != res[1][r]}
        if diff:
            check('frame %d: registers kept' % k, diff, {})
        n_calls.append(len(E1.calls))
    check('frame: one crumb a frame for kind 0x42, none for 0x10, %d in all' % D.STEP_MAX,
          (n_calls[1], sum(n_calls), n_calls[-1]), (0, D.STEP_MAX, 0))
    # v4: every allocation-failure assert in TRAP_RANGES is `bl traphook` in the diagnostic executable and still
    # `twu r31, r31` in the base; from a few of them (the animation heap's), the hook logs the assert's address and
    # r3, then reaches its own `twu r31, r31` with every register as at the assert but LR (the bl's)
    sites = D.trap_sites(E0.w)
    _words, labels, _hooks = D.build(E0.w)
    th, tw = labels['traphook'], labels['traptw']
    check('trap: %d asserts in the ranges, each `bl traphook` in the diagnostic one' % len(sites),
          (len(sites) > 100, [hex(x) for x in sites if E1.w(x) != D.branch(x, th, link=True)]), (True, []))
    check('trap: traphook ends in the same assert', E1.w(tw), D.TRAP_WORD)
    for site in [x for x in (0x036B356C, 0x036B89C4, 0x036AFFE0, 0x036C938C) if x in sites] + sites[:1]:
        E1.calls = []
        setup(E1, {3: 0}, {})
        want = E1.state()
        run(E1, site, tw)
        got = E1.state()
        lr = got.pop('lr')
        want.pop('lr')
        diff = {r: (hex(want[r]), hex(got[r])) for r in want if want[r] != got[r]}
        check('trap 0x%08X: registers as at the assert (LR = the bl\'s 0x%08X)' % (site, lr), (diff, lr),
              ({}, site + 4))
        check('trap 0x%08X: OSReport once (trap, 0, the address, r3)' % site,
              [(c[1], c[2], c[3], c[4]) for c in E1.calls], [('trap', 0, site, 0)])
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
