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


class M(Emu):
    def __init__(self, path, osreport):
        super().__init__(path)
        self.calls = []
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        if osreport:
            self.stub(target(self, D.OSREPORT_SITE), self.osreport)

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
    check('OSReport\'s call site is a bl (REL24 to the import)', E1.w(D.OSREPORT_SITE) >> 26 == 18 and E1.w(D.OSREPORT_SITE) & 1, 1)
    F = E0.alloc(0x1000, b'\0')                                   # fake structs (the same address in both)
    assert E1.alloc(0x1000, b'\0') == F
    for e in (E0, E1):
        e.mu.mem_map(0, 0x1000)                                  # article-pool's null object: lwz r10, 0x24(0)
        e.pre = D.LIMIT - 0x800                                  # preludes in the unused tail, b reach of every hook
    obj, acc, fs, req, mod, ent = F + 0x100, F + 0x200, F + 0x300, F + 0x400, F + 0x500, F + 0x600
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
    }
    tags = [s[0] for s in D.STEPS]
    for tag, at, _w0, _a, _what in D.STEPS:
        i = tags.index(tag)
        w0 = E0.w(at)
        stop = target(E0, at) if w0 >> 26 == 18 else at + 4
        link = w0 >> 26 == 18 and w0 & 1
        for k, (regs, mem, want) in enumerate(cases.get(tag, [])):
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
    tag, at = 'frame', [s[1] for s in D.STEPS if s[0] == 'frame'][0]
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
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
