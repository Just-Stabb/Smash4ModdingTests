#!/usr/bin/env python3
"""exe_v46t_threads: the time commands' per-frame part on every battle scene (fix on exe_v46n-based executables:
exe_v46s -> exe_v46t_threads).

exe_v46n put ts_scene (acmd_ext_cave.py: a new match's clean-up, Time_Scale's extra game steps, the Frames
countdowns of Time_Scale and Stage_Freeze) on ONE call of the battle step 0x029108D0, at 0x0309BE54 (scene C, whose
next callback runs the step's second half 0x0291100C). The game has three scenes that step a battle, each its own
update -> `bl 0x029108D0` (gated by 0x02910164(battle)) and next callback:
  A  update 0x020AFD1C (scene vtable 0x10010598-, its own battle set-up)  bl at 0x020AFE18, next 0x020B02C4
  B  update 0x020E84D4 (from 0x020E6ACC, vtable 0x100124F8-)              bl at 0x020E8504, next 0x020E851C
  C  update 0x0309BE34 (vtable 0x100CE0B0-)                              bl at 0x0309BE54, next 0x0291100C (ts_scene)
The user's training match ran none of C (threads / time test v2: the diag's S4TS line, printed on ts_scene's first
call, never came, while every other diag line did): ts_scene never ran there, so Time_Scale(2+) never sped anything up
and no Frames ran out. This patch puts A's and B's calls through the same work: ts_sitea / ts_siteb = ts_tick, the
extra steps (each the step and that scene's own next callback, as ts_scene does with C's), the frame's own step,
ts_count (ts_scene's own helpers and data, by address). C stays on ts_scene.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/ts_scene_sites_cave.py --rpx IN.rpx)
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04BD4800               # free in ts_code's region (exe_v46n: ts_code ends 0x04BD4564, ts_data 0x04BD5F00)
LIMIT = 0x04BD5F00
BATTLE_UPD = 0x029108D0
SITES = {'a': (0x020AFE18, 0x020B02C4), 'b': (0x020E8504, 0x020E851C)}     # bl BATTLE_UPD, the scene's next callback
SITE_C = 0x0309BE54
TRAMP = 0x037EE550              # 2 x 4 words in the starcopy zero-fill (0x037EE4DC-0x037EE578 zero in exe_v46s): the
                                # sites (0x020A....) can't bl as far as the cave


def bl(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC) | 1


def labels():
    import acmd_ext_cave as C
    a, _w, _h = C.build()
    out = {}
    for p in [a] + [getattr(a, 'part%d' % i) for i in range(2, 10) if hasattr(a, 'part%d' % i)]:
        try:
            out.update(p.labels)
        except Exception:
            pass
    return {k: out[k] for k in ('ts_tick', 'ts_count', 'ts_data', 'ts_scene')}


def build(orig):
    L = labels()
    assert orig(L['ts_tick']) == 0x9421FFE0 and orig(L['ts_count']) == 0x9421FFE0, 'not an exe_v46n-based exe'
    assert orig(SITE_C) == bl(SITE_C, L['ts_scene']), 'scene C not on ts_scene: 0x%08X' % orig(SITE_C)
    for k, (site, _nxt) in SITES.items():
        assert orig(site) == bl(site, BATTLE_UPD), 'site %s 0x%08X: 0x%08X' % (k, site, orig(site))
    a = Asm(CAVE)
    src = ''
    for k, (site, nxt) in SITES.items():
        D = dict(k=k, tick=L['ts_tick'], count=L['ts_count'], tdh=L['ts_data'] >> 16, tdl=L['ts_data'] & 0xFFFF,
                 updh=BATTLE_UPD >> 16, updl=BATTLE_UPD & 0xFFFF, nh=nxt >> 16, nl=nxt & 0xFFFF)
        src += """
# --- ts_site%(k)s(r3 battle): instead of the scene's bl 0x029108D0 -------------------------------------------------
ts_site%(k)s:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        lis r12, 0x%(tick)X@ha
        bl 0x%(tick)08X
        lis r12, 0x%(tdh)X
        ori r12, r12, 0x%(tdl)X
        lwz r30, 0x14(r12)              # extra steps (Time_Scale above 1)
        cmpwi r30, 0
        beq tl_%(k)s
        lwz r12, 0(r31)                 # only while the match runs as normal (not paused, not ending)
        lbz r0, 0x88(r12)
        cmpwi r0, 0
        beq tl_%(k)s
        lbz r0, 0x8C(r12)
        cmpwi r0, 0
        bne tl_%(k)s
        lbz r0, 0x8D(r12)
        cmpwi r0, 0
        bne tl_%(k)s
tm_%(k)s:
        mr r3, r31
        lis r12, 0x%(updh)X
        ori r12, r12, 0x%(updl)X
        mtctr r12
        bctrl
        lis r12, 0x%(nh)X                # the scene's own next callback: the step's second half there
        ori r12, r12, 0x%(nl)X
        mtctr r12
        bctrl
        addi r30, r30, -1
        cmpwi r30, 0
        bne tm_%(k)s
tl_%(k)s:
        mr r3, r31
        lis r12, 0x%(updh)X
        ori r12, r12, 0x%(updl)X
        mtctr r12
        bctrl
        bl 0x%(count)08X
        lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""" % D
    src = src.replace('        lis r12, 0x%X@ha\n' % L['ts_tick'], '')
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    for i, (k, (site, _nxt)) in enumerate(SITES.items()):
        t = TRAMP + 0x10 * i
        dst = a.addr('ts_site' + k)
        tw = [0x3D800000 | (dst >> 16), 0x618C0000 | (dst & 0xFFFF), 0x7D8903A6, 0x4E800420]   # lis/ori r12, mtctr, bctr
        for j, w in enumerate(tw):
            assert orig(t + 4 * j) == 0, 'trampoline word 0x%08X not free' % (t + 4 * j)
            out[t + 4 * j] = w
        out[site] = bl(site, t)
    return out, a.labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46n-based: exe_v46s)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _l = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
