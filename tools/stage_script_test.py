#!/usr/bin/env python3
"""Runs tools/stage_script_cave.py's code in a patched RPX in unicorn, with the game functions it
calls replaced by stubs that record their arguments.

  python3 tools/stage_script_test.py PATCHED.rpx

Checks: the setup hook zeroes the counter and goes on to the setup's second instruction; the
update hook calls the base update and returns its result; for the stage kind, every frame asks for
the link by name and moves it to motion(t) (t = frames so far, f1 = 1, and 0.5 for slow motion);
for another kind, nothing.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_script_cave as C  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine, cstr  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_PC,  # noqa: E402
                               UC_PPC_REG_FPR1, UC_PPC_REG_MSR)

STAGE = 0x7F004000
REC = 0x7F002000          # stub records: +0 x, +4 y, +8 rotation, +0xC name ptr, +0x10 stage, +0x14 calls


def stub(mu, addr, text):
    a = Asm(addr)
    a.asm(text)
    mu.mem_write(addr, b''.join(struct.pack('>I', w) for w in a.words()))


def f2i(f):
    return struct.unpack('>Q', struct.pack('>d', f))[0]


def main():
    mu = machine(sys.argv[1])
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)   # FP available
    a, _words, _hooks = C.build()
    stub(mu, C.BASE_UPDATE, 'li r3, 0x55\nblr')
    stub(mu, C.LINK_GROUNDS, """
        lis r7, 0x7F00
        stw r4, 0x200C(r7)
        stw r3, 0x2010(r7)
        lis r3, 0x7F00
        ori r3, r3, 0x3000
        blr""")
    stub(mu, C.MOVE_GROUNDS, """
        lis r7, 0x7F00
        lwz r5, 0(r4)
        lwz r6, 4(r4)
        stw r5, 0x2000(r7)
        stw r6, 0x2004(r7)
        stfs f1, 0x2008(r7)
        lwz r5, 0x2014(r7)
        addi r5, r5, 1
        stw r5, 0x2014(r7)
        blr""")
    fails = 0

    def check(what, ok, detail=''):
        nonlocal fails
        fails += not ok
        print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, ' ' + detail if detail else ''))

    data = a.addr('data')
    # setup hook
    mu.mem_write(data, struct.pack('>f', 123.0))
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.emu_start(C.SETUP, C.SETUP + 4, count=100)
    sp = mu.reg_read(UC_PPC_REG_1)
    check('setup hook: counter zeroed, stack frame made, back at the setup',
          struct.unpack('>f', mu.mem_read(data, 4))[0] == 0.0 and sp == 0x7F00F000 - 0x298 and
          mu.reg_read(UC_PPC_REG_PC) == C.SETUP + 4)

    def frame(kind, rate):
        mu.mem_write(STAGE + C.KIND_AT, struct.pack('>I', kind))
        mu.mem_write(STAGE + 0xCC, struct.pack('>I', 0))      # the manager's slot, not the kind
        mu.reg_write(UC_PPC_REG_3, STAGE)
        mu.reg_write(UC_PPC_REG_FPR1, f2i(rate))
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.emu_start(C.UPDATE_HOOK, C.UPDATE_HOOK + 4, count=2000)   # the hook bl returns here
        return mu.reg_read(UC_PPC_REG_3), mu.reg_read(UC_PPC_REG_1)

    mu.mem_write(REC, b'\0' * 0x20)
    worst, t = 0.0, 0.0
    ok_ret = True
    for i in range(600):
        rate = 0.5 if 300 <= i < 340 else 1.0
        t += rate
        r3, sp = frame(C.KIND, rate)
        ok_ret &= r3 == 0x55 and sp == 0x7F00F000
        x, y, rot = struct.unpack('>3f', mu.mem_read(REC, 12))
        wx, wy = C.motion(t)
        worst = max(worst, abs(x - wx), abs(y - wy))
        ok_ret &= rot == 0.0
    calls = struct.unpack('>I', mu.mem_read(REC + 0x14, 4))[0]
    check('base update called, its result returned, stack restored, rotation 0', ok_ret)
    check('the link moved every frame (600 frames)', calls == 600, '(%d)' % calls)
    check('link name / stage passed', cstr(mu, struct.unpack('>I', mu.mem_read(REC + 0xC, 4))[0]) == C.LINK and
          struct.unpack('>I', mu.mem_read(REC + 0x10, 4))[0] == STAGE)
    check('offsets follow motion(t), slow motion included', worst < 1e-3, '(worst error %.6f)' % worst)
    frame(C.KIND + 1, 1.0)
    check('another stage kind: nothing moved', struct.unpack('>I', mu.mem_read(REC + 0x14, 4))[0] == 600)
    print('FAILED %d' % fails if fails else 'all ok')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
