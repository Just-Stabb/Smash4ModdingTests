#!/usr/bin/env python3
"""Tests tools/ts_scene_sites_cave.py (unicorn, the game's own code around it): the time commands' per-frame part on
the battle scenes A (0x020AFE18) and B (0x020E8504), as acmd_ext_test.py's ts_tests checks scene C's ts_scene. The
scene's own instructions run from the step's call to the next one (A: lwz r3, 0(r29); bl. B: lwz r3, 0(r31); bl);
the battle step and the scene's next callback are stubs that count their calls; the handlers and the game's slow
manager / stage stop are the real ones (fake managers as ts_tests).

  python3 tools/ts_scene_sites_test.py PATCHED.rpx [ORIGINAL.rpx]
      PATCHED: exe_v46t_threads; ORIGINAL (optional): exe_v46s, to show the bug (A / B never count Frames down)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import acmd_ext_test as T  # noqa: E402
import ts_scene_sites_cave as X  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6, \
    UC_PPC_REG_7  # noqa: E402

UC_PPC_REG_29 = UC_PPC_REG_3 + 26
UC_PPC_REG_31 = UC_PPC_REG_3 + 28
f = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]        # noqa: E731


def scenario(pm, a, quiet=False):
    """{site: [(upd, next) per frame ...], stage frames} for the sequence below"""
    B = 0x103C0000
    me, state, ctx, params, mgr, smgr, battle, bstate, slow, slots, cnt = (B + 0x400 * i for i in range(11))
    for i in range(11):
        pm.mem_write(B + 0x400 * i, b'\0' * 0x400)
    stubs = [(C.BATTLE_UPD, 0)] + [(nxt, 4) for _s, nxt in X.SITES.values()]
    for fn, k in stubs:
        st = Asm(fn)
        st.asm("""
        lis r12, 0x%X
        lwz r11, 0x%X(r12)
        addi r11, r11, 1
        stw r11, 0x%X(r12)
        blr""" % (cnt >> 16, (cnt & 0xFFFF) + k, (cnt & 0xFFFF) + k))
        for i, w in enumerate(st.words()):
            T.w32(pm, fn + 4 * i, w)
    T.w32(pm, C.SLOW_MGR, mgr)
    T.w32(pm, C.STAGE_MGR, smgr)
    T.w32(pm, C.BATTLE, battle)
    T.w32(pm, battle, bstate)
    pm.mem_write(bstate + 0x88, b'\1')
    T.w32(pm, smgr, smgr + 0x200)
    T.w32(pm, smgr + 0x200 + 0xC8, 4)
    pm.mem_write(C.TS_DATA, b'\0' * 0x40)

    def cmd(label, words):
        for i, w in enumerate(words):
            T.w32(pm, params + 4 * i, w)
        T.w32(pm, state + 4, 0x1000)
        T.w32(pm, state + 8, -1)
        pm.mem_write(ctx + 8, b'\1')
        T.run(pm, a.addr(label), RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx,
                                       UC_PPC_REG_7: params})

    out = {}
    for k, (site, _nxt) in X.SITES.items():
        pm.mem_write(C.TS_DATA, b'\0' * 0x40)
        reg = UC_PPC_REG_29 if k == 'a' else UC_PPC_REG_31

        def frame():
            T.w32(pm, cnt, 0)
            T.w32(pm, cnt + 4, 0)
            T.run(pm, site - 4, site + 4, {UC_PPC_REG_1: 0x7F00F000, reg: C.BATTLE})
            return T.r32(pm, cnt), T.r32(pm, cnt + 4), pm.reg_read(UC_PPC_REG_1) == 0x7F00F000
        seq = [frame()]
        cmd('h_tscale', [f(2.0), 3])
        seq += [frame(), frame(), frame(), frame()]
        cmd('h_sfreeze', [1, 2])
        st = [pm.mem_read(smgr + 0xD0, 1)[0]]
        frame()
        st.append(pm.mem_read(smgr + 0xD0, 1)[0])
        frame()
        st.append(pm.mem_read(smgr + 0xD0, 1)[0])
        out[k] = (seq, st)
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    ext, _w, _h = C.build()
    got = scenario(machine(a[0]), ext)
    for k, (seq, st) in got.items():
        T.check('scene %s: one step a frame; Time_Scale(2, 3): 2 steps (the extra one with the scene\'s own next '
                'callback) for 3 frames, then 1; stack kept' % k.upper(), seq,
                [(1, 0, True), (2, 1, True), (2, 1, True), (2, 1, True), (1, 0, True)])
        T.check('scene %s: Stage_Freeze(1, 2): stopped, still after 1 frame, going on after its 2nd' % k.upper(), st,
                [1, 1, 0])
    if len(a) > 1:
        old = scenario(machine(a[1]), ext)
        T.check('the original (exe_v46s): scenes A / B never run the extra steps or the Frames countdown (the bug)',
                {k: (s[1], st[2]) for k, (s, st) in old.items()}, {'a': ((1, 0, True), 1), 'b': ((1, 0, True), 1)})
    print('%d failures' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
