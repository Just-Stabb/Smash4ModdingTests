#!/usr/bin/env python3
"""Tests tools/diag_tick_cave.py (unicorn) in exe_v46u_threads_diag (exe_v46u_threads + diag_godfist_cave +
diag_threads_cave + diag_taunt_time_cave + diag_tick_cave):
- every check of tools/ts_tick_test.py passes with the S4TS hook in place (the tick runs as without it), and S4TS lines
  come on the tick's first call and when slow / extra / stage change;
- S4GE: a Graphic_Effect handler call prints its line (the effect id, EffectModule +0x9F / +0xA0, run, the accessor),
  then runs on as before (here with the module refusing: the handler's own skip path, the stack kept).

  python3 tools/diag_tick_test.py DIAG.rpx V46T.rpx
      V46T: exe_v46t_threads (what exe_v46u_threads was built on: ts_tick_cave.py's labels)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import acmd_ext_test as T  # noqa: E402
import diag_godfist_cave as G  # noqa: E402
import diag_tick_cave as DK  # noqa: E402
import ts_tick_cave as U  # noqa: E402
import ts_tick_test as TT  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_5, UC_PPC_REG_6, UC_PPC_REG_7, \
    UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    import kind_expand as K
    pm = machine(a[0])
    calls = []

    def hook(uc, addr, size, _u):
        regs = [uc.reg_read(UC_PPC_REG_3 + i) for i in range(8)]
        fmt = bytes(uc.mem_read(regs[0], 96)).split(b'\0')[0]
        calls.append((fmt.split(b' ')[0].decode(), regs[1:]))
        for r in range(3, 13):
            uc.reg_write(UC_PPC_REG_3 + r - 3, 0xDEAD0000 + r)
        uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    pm.hook_add(UC_HOOK_CODE, hook, begin=G.OSREPORT_VENEER, end=G.OSREPORT_VENEER)
    ext, _w, _h = C.build()
    _words, lab = U.build(K.Image(a[1]).w)
    f0 = T.fails
    TT.checks(pm, ext, lab)
    T.check('ts_tick_test.py\'s checks: no failures with the S4TS hook in place', T.fails - f0, 0)
    ts = [c[1] for c in calls if c[0] == 'S4TS']
    T.check('S4TS: the first tick prints (n 1); later lines show the slow (slow 1) and the stage (stage 1)',
            (ts[0][1] if ts else None, any(x[2] == 1 for x in ts), any(x[6] == 1 for x in ts)), (1, True, True))
    T.check('S4TS: no line on ticks where nothing changed (fewer lines than ticks)', len(ts) < T.r32(pm, DK.DATA), True)
    # S4GE: Graphic_Effect's handler on an accessor whose EffectModule refuses (vt +0x32C returns 0)
    B = 0x103D0000
    acc, eff, vt, run, params = B, B + 0x400, B + 0x800, B + 0xC00, B + 0xD00
    for x in (acc, eff, vt, run, params):
        pm.mem_write(x, b'\0' * 0x400)
    T.w32(pm, acc + 0xA0, eff)
    T.w32(pm, eff, vt)
    T.w32(pm, vt + 0x32C, 0x02C31610)                       # the game's own vt +0x32C (bytes +0x9F / +0xA0)
    pm.mem_write(eff + 0x9F, b'\1\0')
    pm.mem_write(run + 8, b'\1')
    T.w32(pm, params, 0x100000F)
    T.w32(pm, run + 0x40, 0)
    for at in range(DK.GE_AT, DK.GE_AT + 0x200, 4):          # (the paired-single words unicorn can't run)
        if T.r32(pm, at) >> 26 in (4, 56, 57, 60, 61):
            T.w32(pm, at, 0x60000000)
    n0 = len(calls)
    T.run(pm, DK.GE_AT, RET, {UC_PPC_REG_1: 0x7F00F000, UC_PPC_REG_3: acc, UC_PPC_REG_5: run + 0x40,
                              UC_PPC_REG_6: run, UC_PPC_REG_7: params}, count=200000)
    ge = [c[1] for c in calls[n0:] if c[0] == 'S4GE']
    T.check('S4GE: one line: the effect 0x100000F, +0x9F 1, +0xA0 0, run 1, the accessor; the handler then refuses '
            '(the game\'s gate) and returns, stack kept', (tuple(ge[0][:5]) if ge else None, pm.reg_read(UC_PPC_REG_1)),
            ((0x100000F, 1, 0, 1, acc), 0x7F00F000))
    print('%d failures' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
