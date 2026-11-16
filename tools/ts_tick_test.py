#!/usr/bin/env python3
"""Tests tools/ts_tick_cave.py (exe_v46u_threads; unicorn, the game's own slow manager / stage stop and the command
handlers, as acmd_ext_test.py's ts_tests):
- tsu_frame (the battle object world's first phase, 0x02BF2544's call of the frame state fill): the fill's result
  kept; Time_Scale(0.5, 3) / Stage_Freeze(1, 2) end after their Frames of it; nothing counted while `busy`;
- tsu_clear (the slow manager's clear-all 0x02FB3498, run for real): our request gone with the others, Time_Scale and
  Stage_Freeze off, the function's own work done;
- tsu_seq (0x02FF4DF8, the battle sequence's frame; its body stubbed past the hooked word to count calls): 1 call
  normally, 1 + extra under Time_Scale(2 / 3) (`busy` on all but the last), 1 when r4 isn't 0;
- the scenes A / B / C (their own instructions; the battle step stubbed to count, then run the world phase's hooked
  call): Time_Scale(2, 3) two steps (the extra one with that scene's second half) for 3 frames then one, counted once
  a frame; Stage_Freeze(1, 2) lets go after 2.

  python3 tools/ts_tick_test.py PATCHED.rpx ORIGINAL.rpx
      PATCHED: exe_v46u_threads; ORIGINAL: exe_v46t_threads (what it was built on: its labels)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import acmd_ext_test as T  # noqa: E402
import ts_scene_sites_cave as X  # noqa: E402
import ts_tick_cave as U  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6, \
    UC_PPC_REG_7  # noqa: E402

UC_PPC_REG_29 = UC_PPC_REG_3 + 26
UC_PPC_REG_31 = UC_PPC_REG_3 + 28
f = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]        # noqa: E731


def put(pm, at, src):
    st = Asm(at)
    st.asm(src)
    for i, w in enumerate(st.words()):
        T.w32(pm, at + 4 * i, w)


def setup(pm):
    B = 0x103C0000
    r = {n: B + 0x400 * i for i, n in enumerate(('me', 'state', 'ctx', 'params', 'mgr', 'smgr', 'battle', 'bstate',
                                                   'cnt'))}
    for v in r.values():
        pm.mem_write(v, b'\0' * 0x400)
    T.w32(pm, C.SLOW_MGR, r['mgr'])
    T.w32(pm, C.STAGE_MGR, r['smgr'])
    T.w32(pm, C.BATTLE, r['battle'])
    T.w32(pm, r['battle'], r['bstate'])
    pm.mem_write(r['bstate'] + 0x88, b'\1')
    T.w32(pm, r['smgr'], r['smgr'] + 0x200)
    T.w32(pm, r['smgr'] + 0x200 + 0xC8, 4)
    pm.mem_write(C.TS_DATA, b'\0' * 0x40)
    return r


def cmd(pm, a, r, label, words):
    for i, w in enumerate(words):
        T.w32(pm, r['params'] + 4 * i, w)
    T.w32(pm, r['state'] + 4, 0x1000)
    T.w32(pm, r['state'] + 8, -1)
    pm.mem_write(r['ctx'] + 8, b'\1')
    T.run(pm, a.addr(label), RET, {UC_PPC_REG_3: r['me'], UC_PPC_REG_4: 0, UC_PPC_REG_5: r['state'],
                                   UC_PPC_REG_6: r['ctx'], UC_PPC_REG_7: r['params']})


def requests(pm, r):
    return {k: pm.mem_read(r['mgr'] + 0x10 + 2 * k + 1, 1)[0] for k in range(16)
            if pm.mem_read(r['mgr'] + 0x10 + 2 * k, 1)[0]}


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    ext, _w, _h = C.build()
    import kind_expand as K
    _words, lab = U.build(K.Image(a[1]).w)
    checks(machine(a[0]), ext, lab)
    print('%d failures' % T.fails)
    sys.exit(1 if T.fails else 0)


def checks(pm, ext, lab):
    """every check above on machine pm (diag tests pass one with OSReport hooked)"""
    tsu = {k: lab[k] for k in lab if k.startswith('tsu_')}
    r = setup(pm)
    put(pm, U.FRAME_FN, 'li r3, 7\nblr')                    # the frame state fill: returns 7
    stage = lambda: pm.mem_read(r['smgr'] + 0xD0, 1)[0]     # noqa: E731

    def frame():                                            # 0x02BF2544's lines: lis r3; lwz r3; bl (tsu_frame)
        T.run(pm, U.FRAME_AT - 8, U.FRAME_AT + 4, {UC_PPC_REG_1: 0x7F00F000})
        return pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_1) == 0x7F00F000
    cmd(pm, ext, r, 'h_tscale', [f(0.5), 3])
    seen = [requests(pm, r)]
    out = []
    for _ in range(3):
        out.append(frame())
        seen.append(requests(pm, r))
    T.check('tsu_frame: the fill\'s result back (7), stack kept', set(out), {(7, True)})
    T.check('tsu_frame: Time_Scale(0.5, 3): our slow request (rate 2) for 3 frames of the world phase, then freed',
            seen, [{0: 2}, {0: 2}, {0: 2}, {}])
    cmd(pm, ext, r, 'h_sfreeze', [1, 2])
    st = [stage()]
    frame()
    st.append(stage())
    frame()
    st.append(stage())
    T.check('tsu_frame: Stage_Freeze(1, 2): stopped, still after 1 frame, going on after the 2nd', st, [1, 1, 0])
    cmd(pm, ext, r, 'h_tscale', [f(0.5), 2])
    T.w32(pm, C.TS_DATA + U.BUSY, 1)
    frame()
    frame()
    frame()
    T.check('tsu_frame: nothing counted while a speed-up\'s extra step runs (busy)', requests(pm, r), {0: 2})
    T.w32(pm, C.TS_DATA + U.BUSY, 0)
    # tsu_clear: the game's own clear-all
    cmd(pm, ext, r, 'h_tscale', [f(0.5), 0])
    cmd(pm, ext, r, 'h_sfreeze', [1, 0])
    pm.mem_write(r['mgr'] + 0x10 + 2 * 3, b'\1\4')          # the game's own request too
    before = (requests(pm, r), stage())
    T.run(pm, U.CLEAR_AT, RET, {UC_PPC_REG_1: 0x7F00F000, UC_PPC_REG_3: r['mgr']})
    td = struct.unpack('>9I', bytes(pm.mem_read(C.TS_DATA, 0x24)))
    T.check('tsu_clear (the slow manager\'s clear-all, e.g. a training reset): every request gone (ours and the '
            'game\'s), our state off (slow, frames, extra), the stage going on; stack kept',
            (before, requests(pm, r), stage(), td[1], td[4], td[5], td[6], pm.reg_read(UC_PPC_REG_1)),
            (({0: 2, 3: 4}, 1), {}, 0, 0, 0, 0, 0, 0x7F00F000))
    T.check('tsu_clear: the clear-all\'s own dirty byte (+0x30) set as before', pm.mem_read(r['mgr'] + 0x30, 1)[0], 1)
    # tsu_seq: the sequence's frame; past its hooked first word, a stub counts the calls and records busy
    put(pm, U.SEQ_AT + 4, """
        addi r1, r1, 0x38
        lis r12, 0x%X
        lwz r11, 0x%X(r12)
        addi r11, r11, 1
        stw r11, 0x%X(r12)
        lis r10, 0x%X
        lwz r9, 0x%X(r10)
        slwi r11, r11, 2
        add r12, r12, r11
        stw r9, 0x%X(r12)
        blr""" % (r['cnt'] >> 16, r['cnt'] & 0xFFFF, r['cnt'] & 0xFFFF, C.TS_DATA >> 16, (C.TS_DATA & 0xFFFF) + U.BUSY,
                  (r['cnt'] & 0xFFFF) + 0x20))

    def seq(r4=0):
        pm.mem_write(r['cnt'], b'\0' * 0x80)
        T.run(pm, U.SEQ_AT, RET, {UC_PPC_REG_1: 0x7F00F000, UC_PPC_REG_3: 0x10390000, UC_PPC_REG_4: r4})
        n = T.r32(pm, r['cnt'])
        return n, [T.r32(pm, r['cnt'] + 0x24 + 4 * i) for i in range(n)], pm.reg_read(UC_PPC_REG_1) == 0x7F00F000
    pm.mem_write(C.TS_DATA, b'\0' * 0x40)
    s0 = seq()
    cmd(pm, ext, r, 'h_tscale', [f(3.0), 0])
    s1 = seq()
    s2 = seq(1)
    cmd(pm, ext, r, 'h_tscale', [f(1.0), 0])
    s3 = seq()
    T.check('tsu_seq: 1 run normally; Time_Scale(3): 3 runs, busy on the first 2; r4 1: 1 run; Time_Scale(1): 1 '
            'run; the stack kept', (s0, s1, s2, s3), ((1, [0], True), (3, [1, 1, 0], True), (1, [0], True),
                                                        (1, [0], True)))
    # the scenes A / B / C: the battle step stubbed: count, then the world phase's hooked call (tsu_frame)
    put(pm, C.BATTLE_UPD, """
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        lis r12, 0x%X
        lwz r11, 0x%X(r12)
        addi r11, r11, 1
        stw r11, 0x%X(r12)
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        bctrl
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr""" % (r['cnt'] >> 16, r['cnt'] & 0xFFFF, r['cnt'] & 0xFFFF, tsu['tsu_frame'] >> 16,
                                           tsu['tsu_frame'] & 0xFFFF))
    for nxt, _arg in U.SCENES.values():
        put(pm, nxt, """
        lis r12, 0x%X
        lwz r11, 0x%X(r12)
        addi r11, r11, 1
        stw r11, 0x%X(r12)
        blr""" % (r['cnt'] >> 16, (r['cnt'] & 0xFFFF) + 4, (r['cnt'] & 0xFFFF) + 4))
    put(pm, U.BATTLE_PLAY, 'li r3, 1\nblr')
    sites = {'a': (X.SITES['a'][0], UC_PPC_REG_29), 'b': (X.SITES['b'][0], UC_PPC_REG_31),
             'c': (X.SITE_C, UC_PPC_REG_3 + 28)}
    for k, (site, reg) in sites.items():
        pm.mem_write(C.TS_DATA, b'\0' * 0x40)
        regs = {UC_PPC_REG_1: 0x7F00F000, reg: C.BATTLE}

        def sframe():
            pm.mem_write(r['cnt'], b'\0' * 8)
            if k == 'c':                                    # C: lwz r3, 0(r31) at 0x0309BE48 (lis / lwz r3 before)
                T.run(pm, site - 0x10, site + 4, {UC_PPC_REG_1: 0x7F00F000})
            else:
                T.run(pm, site - 4, site + 4, regs)
            return T.r32(pm, r['cnt']), T.r32(pm, r['cnt'] + 4), pm.reg_read(UC_PPC_REG_1) == 0x7F00F000
        seq_ = [sframe()]
        cmd(pm, ext, r, 'h_tscale', [f(2.0), 3])
        seq_ += [sframe(), sframe(), sframe(), sframe()]
        cmd(pm, ext, r, 'h_sfreeze', [1, 2])
        st = [stage()]
        sframe()
        st.append(stage())
        sframe()
        st.append(stage())
        T.check('scene %s: 1 step a frame; Time_Scale(2, 3): 2 (the extra one with the scene\'s own second half) for '
                '3 frames, counted once a frame, then 1; Stage_Freeze(1, 2) lets go after 2; stack kept' % k.upper(),
                (seq_, st), ([(1, 0, True), (2, 1, True), (2, 1, True), (2, 1, True), (1, 0, True)], [1, 1, 0]))


if __name__ == '__main__':
    main()
