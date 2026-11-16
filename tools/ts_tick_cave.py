#!/usr/bin/env python3
"""exe_v46u_threads: the time commands' per-frame tick where every battle mode runs it (fix on exe_v46t_threads).

The user's training test on exe_v46t_threads (threads / time test v2, log 0a921016): every new command ran (S4TC), but
not one S4TS line came from any of the three battle-step call sites tools/ts_scene_sites_cave.py had put ts_scene's work
on: training steps its battle another way. Time_Scale(0.5) never ended, Stage_Freeze never let go (not even after a
training reset), because nothing counted their Frames down.

What every battle mode does run (read off the code): the fighters (0x02E40B90, the user's S4TH lines) are stepped by
the battle object world's phases, and the first of them, 0x02BF2544 ([0x102F6C30]: the frame state fill 0x02BFB97C,
then the objects), is called by exactly three functions, the battle steps 0x029108D0 (scenes A / B / C), 0x02913310 and
0x02FF4DF8 (the per-frame virtual of 24 battle sequence classes, vtables 0x100A1A44 ... 0x1014E67C). So:
- tsu_frame (bl at 0x02BF2568, instead of the frame state fill, which it calls first): once a battle step, the Frames
  countdown (ts_count) unless a speed-up's extra step is running (ts_data +0x30, `busy`);
- tsu_clear (b at 0x02FB3498, the global slow manager's "clear every request", which the battle sequence's own
  start / restart / end virtuals 0x02FF1F18, 0x02FF5E7C, 0x02FF8D64 and the battle set-up 0x029104D0 call): our
  slow request is gone with the others, so Time_Scale is off (nothing freed twice), and a Stage_Freeze lets go;
- the scenes' wrappers (C at 0x0309BE54, A / B through ts_scene_sites_cave.py's trampolines) now tsu_scenec / a / b:
  ts_tick, the extra steps with `busy` set (each the step and that scene's own second half), the frame's own step;
  the countdown is tsu_frame's (ts_scene / ts_sitea / ts_siteb counted it themselves: twice now otherwise);
- tsu_seq (b at 0x02FF4DF8's first word): a speed-up (Time_Scale above 1) there too: with extra steps to run and
  r4 0 (its normal path), the sequence's frame runs 1 + extra times, `busy` on all but the last.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/ts_tick_cave.py --rpx IN.rpx)
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import ts_scene_sites_cave as X  # noqa: E402

CAVE = 0x04BD4A00               # after ts_scene_sites_cave.py's ts_sitea / ts_siteb (0x04BD4800-0x04BD4970)
LIMIT = 0x04BD5F00
FRAME_AT, FRAME_FN = 0x02BF2568, 0x02BFB97C        # in 0x02BF2544: bl the frame state fill
CLEAR_AT = 0x02FB3498                               # li r10, 0x10 (the slow manager's clear-all)
CLEAR_WORD = 0x39400010
SEQ_AT = 0x02FF4DF8                                 # stwu r1, -0x38(r1) (the battle sequence's frame)
SEQ_WORD = 0x9421FFC8
BATTLE_UPD = 0x029108D0
BATTLE_POST, BATTLE_PLAY = 0x0291100C, 0x0334CCE8
SCENES = {'a': (0x020B02C4, False), 'b': (0x020E851C, False), 'c': (BATTLE_POST, True)}   # next callback, (battle) arg
BUSY = 0x30                     # ts_data +0x30: a speed-up's extra step is running


def bl(src, dst, link=True):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, '0x%08X -> 0x%08X' % (src, dst)
    return (18 << 26) | (off & 0x3FFFFFC) | (1 if link else 0)


def labels():
    import acmd_ext_cave as C
    a, _w, _h = C.build()
    out = {}
    for p in [a] + [getattr(a, 'part%d' % i) for i in range(2, 10) if hasattr(a, 'part%d' % i)]:
        try:
            out.update(p.labels)
        except Exception:
            pass
    return {k: out[k] for k in ('ts_tick', 'ts_count', 'ts_time_off', 'ts_stage_off', 'ts_data', 'ts_scene')}


def build(orig):
    L = labels()
    assert orig(FRAME_AT) == bl(FRAME_AT, FRAME_FN), 'frame hook 0x%08X: 0x%08X' % (FRAME_AT, orig(FRAME_AT))
    assert orig(CLEAR_AT) == CLEAR_WORD, 'clear hook 0x%08X: 0x%08X' % (CLEAR_AT, orig(CLEAR_AT))
    assert orig(SEQ_AT) == SEQ_WORD, 'sequence hook 0x%08X: 0x%08X' % (SEQ_AT, orig(SEQ_AT))
    assert orig(X.SITE_C) == bl(X.SITE_C, L['ts_scene']), 'scene C 0x%08X: 0x%08X' % (X.SITE_C, orig(X.SITE_C))
    for i in range(2):                      # ts_scene_sites_cave.py's trampolines (exe_v46t_threads)
        t = X.TRAMP + 0x10 * i
        assert orig(t) >> 16 == 0x3D80 and orig(t + 8) == 0x7D8903A6, 'not exe_v46t_threads: trampoline 0x%08X' % t
    D = dict(tick=L['ts_tick'], count=L['ts_count'], toff=L['ts_time_off'], soff=L['ts_stage_off'],
             tdh=L['ts_data'] >> 16, tdl=L['ts_data'] & 0xFFFF, busy=BUSY, ffn=FRAME_FN,
             clear_back=CLEAR_AT + 4, seq_back=SEQ_AT + 4,
             updh=BATTLE_UPD >> 16, updl=BATTLE_UPD & 0xFFFF, play=BATTLE_PLAY)
    src = """
# --- tsu_frame(r3 the frame state): bl from 0x02BF2568 (0x02BF2544, the battle object world's first phase) -----------
tsu_frame:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        bl 0x%(ffn)08X                  # the frame state fill, as before
        stw r3, 0x10(r1)
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        lwz r0, %(busy)d(r12)
        cmpwi r0, 0
        bne tf_out
        bl 0x%(count)08X                # one of the Frames gone
tf_out:
        lwz r3, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- tsu_clear(r3 the slow manager): b from 0x02FB3498 (clear every request) ----------------------------------------
tsu_clear:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r3, 0x10(r1)
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        li r0, 0
        stw r0, 4(r12)                  # our request goes with the others: nothing to free
        bl 0x%(toff)08X                 # Time_Scale off (frames, extra steps)
        bl 0x%(soff)08X                 # Stage_Freeze off (its stage manager, if still the same)
        lwz r3, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        li r10, 0x10
        b 0x%(clear_back)08X

# --- tsu_seq(r3, r4): b from 0x02FF4DF8 (the battle sequence's frame) -----------------------------------------------
tsu_seq:
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        lwz r0, 0x14(r12)
        cmpwi r0, 0
        beq seq_orig
        lwz r0, %(busy)d(r12)
        cmpwi r0, 0
        bne seq_orig
        cmpwi r4, 0
        bne seq_orig
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r29, 0x14(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        mr r30, r3
        mr r31, r4
        lwz r29, 0x14(r12)
        li r0, 1
        stw r0, %(busy)d(r12)
seq_more:
        mr r3, r30
        mr r4, r31
        bl seq_orig
        addi r29, r29, -1
        cmpwi r29, 0
        bgt seq_more
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        li r0, 0
        stw r0, %(busy)d(r12)
        mr r3, r30
        mr r4, r31
        bl seq_orig
        lwz r29, 0x14(r1)
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
seq_orig:
        stwu r1, -0x38(r1)
        b 0x%(seq_back)08X
""" % D
    for k, (nxt, arg) in SCENES.items():
        E = dict(D, k=k, nh=nxt >> 16, nl=nxt & 0xFFFF)
        src += """
# --- tsu_scene%(k)s(r3 battle): instead of the scene's bl 0x029108D0 ------------------------------------------------
tsu_scene%(k)s:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        bl 0x%(tick)08X                 # a new match / one not running: everything off
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        lwz r30, 0x14(r12)              # extra steps (Time_Scale above 1)
        cmpwi r30, 0
        beq sl_%(k)s
        lwz r11, 0(r31)                 # only while the match runs as normal (not paused, not ending)
        lbz r0, 0x88(r11)
        cmpwi r0, 0
        beq sl_%(k)s
        lbz r0, 0x8C(r11)
        cmpwi r0, 0
        bne sl_%(k)s
        lbz r0, 0x8D(r11)
        cmpwi r0, 0
        bne sl_%(k)s
""" % E + ("""        bl 0x%(play)08X
        cmpwi r3, 0
        beq sl_%(k)s
""" % E if arg else "") + """        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        li r0, 1
        stw r0, %(busy)d(r12)
sm_%(k)s:
        mr r3, r31
        lis r12, 0x%(updh)X
        ori r12, r12, 0x%(updl)X
        mtctr r12
        bctrl
        mr r3, r31
        lis r12, 0x%(nh)X                # that scene's own second half
        ori r12, r12, 0x%(nl)X
        mtctr r12
        bctrl
        addi r30, r30, -1
        cmpwi r30, 0
        bgt sm_%(k)s
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        li r0, 0
        stw r0, %(busy)d(r12)
sl_%(k)s:
        mr r3, r31
        lis r12, 0x%(updh)X              # the frame's own step (its tsu_frame counts the frame)
        ori r12, r12, 0x%(updl)X
        mtctr r12
        bctrl
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""" % E
    a = Asm(CAVE)
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[FRAME_AT] = bl(FRAME_AT, a.addr('tsu_frame'))
    out[CLEAR_AT] = bl(CLEAR_AT, a.addr('tsu_clear'), link=False)
    out[SEQ_AT] = bl(SEQ_AT, a.addr('tsu_seq'), link=False)
    out[X.SITE_C] = bl(X.SITE_C, a.addr('tsu_scenec'))
    for i, k in enumerate(('a', 'b')):
        t = X.TRAMP + 0x10 * i
        dst = a.addr('tsu_scene' + k)
        out[t] = 0x3D800000 | (dst >> 16)
        out[t + 4] = 0x618C0000 | (dst & 0xFFFF)
    return out, a.labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46t_threads)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _l = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
