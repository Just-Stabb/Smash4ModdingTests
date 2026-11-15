#!/usr/bin/env python3
"""Tests tools/diag_hitstate_cave.py in a patched executable (unicorn): a call of each HitModule body-state setter
prints one OSReport line with its op, arguments, caller and its caller's caller, then reaches the setter's second
word with the `mflr r0` done and every register as the caller left it (the setter then runs as before); op 0 with
state 0 (the status change reset) prints nothing.

  python3 tools/diag_hitstate_test.py ORIGINAL.rpx [PATCHED.rpx]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_hitstate_cave as D  # noqa: E402
import kind_expand as K  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_MSR, \
    UC_PPC_REG_PC  # noqa: E402

fails = 0
STACK = 0x7F00F000
CALLER2 = 0x02ABCDE4            # the caller's own saved LR (its frame's +4)


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
    words, labels = D.build(orig.w)
    mu = machine(a[1] if len(a) > 1 else a[0])
    if len(a) == 1:
        for x, w in words.items():
            mu.mem_write(x, struct.pack('>I', w))
    else:
        for x, w in words.items():
            check('patched word 0x%08X' % x, struct.unpack('>I', mu.mem_read(x, 4))[0], w)
    calls = []

    def osr(uc, addr, size, _u):
        regs = [uc.reg_read(UC_PPC_REG_3 + i) for i in range(8)]
        fmt = bytes(uc.mem_read(regs[0], 80)).split(b'\0')[0]
        calls.append((fmt, regs[1:]))
        for r in range(3, 13):
            uc.reg_write(UC_PPC_REG_3 + r - 3, 0xDEAD0000 + r)
        uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    mu.hook_add(UC_HOOK_CODE, osr, begin=D.OSREPORT_VENEER, end=D.OSREPORT_VENEER)

    def call(at, v, arg):
        """run from the setter's first word to its second: (registers changed, r0, r1)"""
        mu.reg_write(UC_PPC_REG_1, STACK + 0x100)
        mu.mem_write(STACK + 0x100, struct.pack('>I', STACK + 0x200))
        mu.mem_write(STACK + 0x200 + 4, struct.pack('>I', CALLER2))
        mu.reg_write(UC_PPC_REG_3, 0x30001000)
        mu.reg_write(UC_PPC_REG_3 + 1, v)
        mu.reg_write(UC_PPC_REG_3 + 2, arg)
        for r in range(6, 32):
            mu.reg_write(UC_PPC_REG_3 + r - 3, 0x1000 + r)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        mu.emu_start(at, at + 4, count=100000)
        want = {3: 0x30001000, 4: v, 5: arg}
        want.update({r: 0x1000 + r for r in range(6, 32)})
        bad = [r for r, w in want.items() if mu.reg_read(UC_PPC_REG_3 + r - 3) != w]
        return bad, mu.reg_read(UC_PPC_REG_0), mu.reg_read(UC_PPC_REG_1)

    serial = 0
    for op, at in D.SETTERS:
        for v, arg in ((3, 1), (0, 0)):
            calls.clear()
            bad, r0, sp = call(at, v, arg)
            printed = not (op == 0 and v == 0)
            serial += printed
            check('setter op %d (0x%08X) v=%d: %s, at its second word with r0 = its caller, every register and the '
                  'stack as before' % (op, at, v, 'one line (op, v, a, lr, lr2, module, serial)' if printed else
                                       'no line (the status change reset)'),
                  ([(f, tuple(r[:7])) for f, r in calls], bad, r0, sp),
                  ([(D.FMT.rstrip(b'\0'), (op, v, arg, RET, CALLER2, 0x30001000, serial))] if printed else [],
                   [], RET, STACK + 0x100))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
