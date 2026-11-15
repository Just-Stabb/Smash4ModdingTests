#!/usr/bin/env python3
"""Tests tools/diag_threads_cave.py (unicorn): with the diag executable, the game's fighter step 0x02E40B90 (as
acmd_ext_test.py's fighter_thread_tests runs it: a fighter whose game script starts a thread, the stack where Cemu
has the game's) prints one S4TH line for each of its first LOG_N steps (r4 the stack slot, r1, the accessor,
old = 0: exe_v46l's check would have skipped it), then none; the thread still runs as without the stub.

  python3 tools/diag_threads_test.py BASE.rpx DIAG.rpx VANILLA_TABLES.rpx
      BASE: exe_v46m (what the diag was built on); DIAG: BASE + diag_godfist_cave + diag_threads_cave;
      VANILLA_TABLES: an executable with the game's command tables (acmd_ext_test.py's ORIGINAL)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_test as T  # noqa: E402
import diag_threads_cave as D  # noqa: E402
import kind_expand as K  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.exit(__doc__)
    words, labels = D.build(K.Image(a[0]).w)
    pm, om = machine(a[1]), machine(a[2])
    for x, w in words.items():
        T.check('patched word 0x%08X' % x, T.r32(pm, x), w)
    calls = []

    def hook(uc, addr, size, _u):
        regs = [uc.reg_read(UC_PPC_REG_3 + i) for i in range(6)]
        fmt = bytes(uc.mem_read(regs[0], 64)).split(b'\0')[0]
        calls.append((fmt, regs[1:]))
        for r in range(3, 13):
            uc.reg_write(UC_PPC_REG_3 + r - 3, 0xDEAD0000 + r)
        uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    pm.hook_add(UC_HOOK_CODE, hook, begin=D.G.OSREPORT_VENEER, end=D.G.OSREPORT_VENEER)
    for lo, hi in ((0x02BEE63C, 0x02BEE9B8), (0x02BE5500, 0x02BE5B00)):      # (acmd_ext_test.py thread_tests)
        for at in range(lo, hi, 4):
            if T.r32(pm, at) >> 26 in (4, 56, 57, 60, 61):
                T.w32(pm, at, 0x60000000)
    cave, _w, _h = T.C.build()
    top = 0x0E00F000
    T.fighter_thread_tests(pm, om, cave, stack_top=top)
    lines = [c for c in calls if c[0].startswith(b'S4TH')]
    T.check('S4TH lines: one for each of the first %d fighter steps, then none' % D.LOG_N, len(lines), D.LOG_N)
    if lines:
        n, r4, r1, acc, old = lines[0][1]
        T.check('S4TH line 1: n 1, r4 the caller\'s stack slot (r1 + 0xC), r1 the caller\'s (0x02E40B90: '
                'stwu r1, -0x20), the accessor, old 0 (exe_v46l would have skipped the threads)',
                (n, r4, r1, acc, old), (1, top - 0x20 + 0xC, top - 0x20, 0x103B0000, 0))
        T.check('S4TH lines numbered 1-%d' % D.LOG_N, [c[1][0] for c in lines], list(range(1, D.LOG_N + 1)))
    print('%d failures' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
