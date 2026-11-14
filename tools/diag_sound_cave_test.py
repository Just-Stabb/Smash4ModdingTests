#!/usr/bin/env python3
"""Runs tools/diag_sound_cave.py's hooks in unicorn on the patched executable, against the unpatched one.

  python3 tools/diag_sound_cave_test.py PATCHED.rpx ORIGINAL.rpx

- every hook site: the patched word is a `b` to the cave, every other word of the executable outside the cave is
  unchanged, the cave sits in space that was zero;
- each step run from its hook (its log line wanted or not): the line's tag and values (OSReport veneer stubbed),
  and every register the hooked code can see afterwards (r0, r3-r31, CR, CTR, XER, LR, f0-f13) equal to running the
  replaced word alone on the unpatched executable from the same state;
- the set-up step through its real call (0x02762180 -> bl 0x03121D68 at 0x02762190: logged) and the same callee
  from another caller (no line);
- the caps: the 'ok' lines stop after OK_EACH a player, a step's lines after its cap.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diag_sound_cave as D  # noqa: E402
import kind_expand as K  # noqa: E402
from kind_expand_test import Emu, REGS, check  # noqa: E402
import kind_expand_test as KT  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_CR, UC_PPC_REG_CTR, UC_PPC_REG_LR, UC_PPC_REG_MSR,  # noqa: E402
                               UC_PPC_REG_PC, UC_PPC_REG_XER)  # noqa: F401

FREGS = [getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_FPR%d' % i) for i in range(32)]
MOD = KT.STRUCTS + 0x10000      # a SoundModule
SLOTOBJ = KT.STRUCTS + 0x20000  # a bank slot (0x033EDABC's r29)
PROBE = KT.STRUCTS + 0x30000   # a 2-word probe (mfxer)
BANKS = {MOD + 0x18: 2051, MOD + 0x24: 6059, MOD + 0x30: -1}


class Run:
    def __init__(self, path):
        self.E = Emu(path)
        mu = self.E.mu
        mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        self.lines = []

        def report(E):
            fmt = E.cstr(E.r(3))
            tag = E.cstr(E.r(4))
            vals = [E.r(i) for i in range(5, 11)]
            self.lines.append((fmt, tag) + tuple(vals))
        self.E.stub(D.OSREPORT_VENEER, report)
        self.E.stub(D.BANK_ID, lambda E: BANKS.get(E.r(3), 0x7777))
        self.E.stub(0x03121CE8, lambda E: None)     # the player call the set-up hook sits in front of

    def state(self, regs):
        mu = self.E.mu
        for n in range(32):
            mu.reg_write(REGS[n], regs.get(n, 0x1000 + 0x11 * n))
        mu.reg_write(UC_PPC_REG_1, KT.STACK + 0xF0000)
        mu.reg_write(UC_PPC_REG_CR, regs.get('cr', 0x24828000))
        mu.reg_write(UC_PPC_REG_CTR, regs.get('ctr', 0x0CC00CC0))
        mu.reg_write(UC_PPC_REG_XER, regs.get('xer', 0x20000000))
        mu.reg_write(UC_PPC_REG_LR, regs.get('lr', 0x0BADC0DE))
        for n in range(14):
            mu.reg_write(FREGS[n], 0x3FF0000000000000 + n)

    def xer(self):
        """XER as the code reads it (mfxer: unicorn keeps SO / OV / CA apart from the XER its API reads)"""
        mu = self.E.mu
        r5 = mu.reg_read(REGS[5])
        mu.mem_write(PROBE, struct.pack('>II', 0x7CA102A6, 0x48000000))      # mfxer r5; b .
        mu.emu_start(PROBE, PROBE + 4, count=10)
        v = mu.reg_read(REGS[5])
        mu.reg_write(REGS[5], r5)
        return v

    def snap(self):
        mu = self.E.mu
        s = {n: mu.reg_read(REGS[n]) for n in range(32) if n != 2}
        s.update(cr=mu.reg_read(UC_PPC_REG_CR), ctr=mu.reg_read(UC_PPC_REG_CTR), lr=mu.reg_read(UC_PPC_REG_LR),
                 pc=mu.reg_read(UC_PPC_REG_PC))
        s['xer'] = self.xer()
        s.update({'f%d' % n: mu.reg_read(FREGS[n]) for n in range(14)})
        return s

    def step(self, at, regs, until=None):
        self.state(regs)
        self.E.mu.emu_start(at, until or at + 4, count=200000)
        return self.snap()


def main():
    patched, original = sys.argv[1], sys.argv[2]
    P, O = K.Image(patched), K.Image(original)
    words, labels, hooks = D.build()
    print('# words')
    check('every hook is a b to its stub', sorted((hex(a), P.w(a)) for a in hooks),
          sorted((hex(a), D.branch(a, labels['hook%d' % i])) for i, (_t, a, *_r) in enumerate(D.STEPS)))
    check('the cave holds the built words', [hex(D.CAVE + 4 * i) for i, w in enumerate(words)
                                             if P.w(D.CAVE + 4 * i) != w], [])
    check('the cave was zero before', [hex(x) for x in range(D.CAVE, D.CAVE + 4 * len(words), 4) if O.w(x)], [])
    diff = []
    for base, data in O.mem:
        pd = P.blob(base, len(data))
        for o in range(0, len(data) - 3, 4):
            a = base + o
            if data[o:o + 4] != pd[o:o + 4] and not (D.CAVE <= a < D.LIMIT) and a not in hooks:
                diff.append(hex(a))
    check('no other word changed', diff[:5], [])

    print('# each step from its hook')
    R, Ro = Run(patched), Run(original)
    for E in (R.E, Ro.E):
        E.mu.mem_write(MOD, b'\0' * 0x800)
        E.setw(MOD + 0x8, 0x45)
        E.setw(MOD + 0xC, 1)
        E.setw(MOD + 0x5E4, 3)
        E.setw(MOD + 0x10, MOD + 0x400)          # the player pointer the set-up's callee reads
        E.mu.mem_write(SLOTOBJ, b'\0' * 0x40)
        E.setw(SLOTOBJ, 0x12)
        E.setw(SLOTOBJ + 0x1C, 0x5ABC0000)
    sid, bank = 0x7640028, 2051
    cases = [
        # (step tag, registers, the line wanted or None)
        ('setup', {3: MOD + 0x10, 30: MOD, 'lr': D.SETUP_RET}, ('setup', 1, 0x45, 2051, 6059, -1, 3)),
        ('setup', {3: MOD + 0x10, 30: MOD, 'lr': 0x0288A680}, None),
        ('bankfail', {3: 0x80000005, 29: SLOTOBJ, 31: 0}, ('bankfail', -1, -1, 0x80000005, 0, 0x5ABC0000, 0x12)),
        ('bankfail', {3: 0, 29: SLOTOBJ, 31: 0x41000000}, None),
        ('gated', {0: 0, 30: MOD, 23: sid}, ('gated', 1, 0x45, sid, 0, 0, 0)),
        ('gated', {0: 1, 30: MOD, 23: sid}, None),
        ('nobank', {3: 0, 30: MOD, 23: sid, 26: bank, 27: MOD + 0x18}, ('nobank', 1, 0x45, sid, bank, 0x18, 0)),
        ('nobank', {3: 1, 30: MOD, 23: sid, 26: bank, 27: MOD + 0x18}, None),
        ('filtered', {3: 1, 30: MOD, 23: sid, 28: 2}, ('filtered', 1, 0x45, sid, 2, 0, 0)),
        ('filtered', {3: 0, 30: MOD, 23: sid, 28: 2}, None),
        ('ok', {30: MOD, 23: sid, 26: bank, 27: MOD + 0x24}, ('ok', 1, 0x45, sid, bank, 0x24, 0)),
    ]
    idx = {s[0]: i for i, s in enumerate(D.STEPS)}
    m32 = 0xFFFFFFFF
    for tag, regs, want in cases:
        i = idx[tag]
        at = D.STEPS[i][1]
        n0 = len(R.lines)
        if tag == 'setup':
            regs = dict(regs)
        got = R.step(at, regs)
        ref = Ro.step(at, regs)
        line = R.lines[n0:]
        w = [] if want is None else [(D.FORMAT[:-1].decode(), want[0]) + tuple(v & m32 for v in want[1:])]
        check('%s %s: the line' % (tag, 'logged' if want else 'not logged'), line, w)
        bad = [(k, hex(got[k]), hex(ref[k])) for k in ref if got[k] != ref[k]]
        check('%s: every register as the replaced word alone leaves it' % tag, bad, [])

    print('# the set-up through its real call, the other callers not logged')
    n0 = len(R.lines)
    R.step(0x02762180, {30: MOD, 7: 0}, until=0x02762194)
    check('0x02762180 -> 0x02762194 (bl 0x03121D68 hooked): one setup line',
          [l[1:] for l in R.lines[n0:]], [('setup', 1, 0x45, 2051, 6059, m32, 3)])
    check('  the player call reached with r3 = [module + 0x10]', R.E.mu.reg_read(REGS[3]), MOD + 0x400)

    print('# caps')
    n0 = len(R.lines)
    for k in range(10):
        R.step(D.STEPS[idx['ok']][1], {30: MOD, 23: sid + k, 26: bank, 27: MOD + 0x18})
    check('ok: %d lines a player' % D.OK_EACH, len(R.lines) - n0, D.OK_EACH - 1)   # one taken above
    R.E.setw(MOD + 0xC, 2)
    n0 = len(R.lines)
    for k in range(10):
        R.step(D.STEPS[idx['ok']][1], {30: MOD, 23: sid + k, 26: bank, 27: MOD + 0x18})
    check('ok: another player has his own %d' % D.OK_EACH, len(R.lines) - n0, D.OK_EACH)
    cap = D.STEPS[idx['gated']][3]
    n0 = len(R.lines)
    for k in range(cap + 10):
        R.step(D.STEPS[idx['gated']][1], {0: 0, 30: MOD, 23: sid})
    check('gated: at most %d lines' % cap, len(R.lines) - n0, cap - 1)        # one taken above
    print('FAILED %d' % KT.fails if KT.fails else 'all passed')
    sys.exit(1 if KT.fails else 0)


if __name__ == '__main__':
    main()
