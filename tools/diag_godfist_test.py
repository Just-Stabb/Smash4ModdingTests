#!/usr/bin/env python3
"""Tests tools/diag_godfist_cave.py in a patched executable (unicorn): the game's own WorkModule set_float (the
fighters' copy, 0x02F1DC04, through position_vars_cave.py's hook, var_entry, acmd_ext_cave.py's user_entry and hv_var)
with a diag ID calls the OSReport veneer once with the line's arguments, every register a C caller keeps is kept,
and reads / other IDs never call it.

  python3 tools/diag_godfist_test.py ORIGINAL.rpx [PATCHED.rpx]
      (without PATCHED: the patch is applied in memory)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_godfist_cave as D  # noqa: E402
import kind_expand as K  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_FPR1, UC_PPC_REG_LR, \
    UC_PPC_REG_MSR, UC_PPC_REG_PC  # noqa: E402

fails = 0
FSET, FGET = 0x02F1DC04, 0x02F1DBE4
WM = 0x30000000


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    orig = K.Image(a[0])
    words, labels, (hvv_zero, ue_zero) = D.build(orig.w)
    mu = machine(a[1] if len(a) > 1 else a[0])
    if len(a) == 1:
        for x, w in words.items():
            mu.mem_write(x, struct.pack('>I', w))
    else:
        for x, w in words.items():
            check('patched word 0x%08X' % x, struct.unpack('>I', mu.mem_read(x, 4))[0], w)
    check('hvv_zero (0x%08X) was `b ue_zero` (0x%08X)' % (hvv_zero, ue_zero), (orig.w(hvv_zero) >> 26), 18)
    mu.mem_map(WM, 0x10000)
    calls = []

    def hook(uc, addr, size, _u):
        if addr == D.OSREPORT_VENEER:
            regs = [uc.reg_read(UC_PPC_REG_3 + i) for i in range(5)]
            fmt = bytes(uc.mem_read(regs[0], 64)).split(b'\0')[0]
            calls.append((fmt, [r if r < 0x80000000 else r - (1 << 32) for r in regs[1:]]))
            for r in range(3, 13):                  # a C callee may clobber the volatile ones
                uc.reg_write(UC_PPC_REG_3 + r - 3, 0xDEAD0000 + r)
            uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    mu.hook_add(UC_HOOK_CODE, hook, begin=D.OSREPORT_VENEER, end=D.OSREPORT_VENEER)

    def fcall(fn, ident, val):
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_3, WM)
        mu.reg_write(UC_PPC_REG_4, ident)
        mu.reg_write(UC_PPC_REG_FPR1, struct.unpack('>Q', struct.pack('>d', val))[0])
        for r in range(14, 32):
            mu.reg_write(UC_PPC_REG_3 + r - 3, 0x1000 + r)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        mu.emu_start(fn, RET, count=100000)
        bad = [r for r in range(14, 32) if mu.reg_read(UC_PPC_REG_3 + r - 3) != 0x1000 + r]
        return bad, mu.reg_read(UC_PPC_REG_1)

    for k, val, line in ((3, -57.22, (3, -57, -5721)), (0, 2.0, (0, 2, 200)), (15, 141.0, (15, 141, 14100))):
        calls.clear()
        bad, sp = fcall(FSET, 0x0F0003F0 + k, val)
        check("set 0x0F0003%02X = %g: one OSReport line %r (c: x 100 in single precision, cut toward 0)" % (0xF0 + k, val, line),
              [(f, tuple(r[:3])) for f, r in calls], [(D.FMT.rstrip(b'\0'), line)])
        check('... callee-saved registers and the stack kept', (bad, sp), ([], 0x7F00F000))
    check('the serial counts the lines', [r[3] for _f, r in calls], [3])
    for what, fn, ident in (('a read of a diag ID', FGET, 0x0F0003F3), ('a write of 0x0F0003D0', FSET, 0x0F0003D0),
                            ('a write of a New_Var slot', FSET, 0x0F0003B0)):
        calls.clear()
        bad, sp = fcall(fn, ident, 5.0)
        check('%s: no line, registers kept' % what, (calls, bad, sp), ([], [], 0x7F00F000))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
