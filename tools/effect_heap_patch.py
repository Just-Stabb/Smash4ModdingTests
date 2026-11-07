#!/usr/bin/env python3
"""A bigger effect heap: every effect bank in a match (both fighters', final smashes', the stage's, the common
and item effects) is loaded into ONE eft heap of 44 MiB; a bank's cost there is its shader programs (each shader
entry gets its own copy, ~17 KB each for Ultimate-converted ones), ~0x900 per shader entry and 0xA00 per emitter.
Sephiroth's tests 61 / 62 (680 / 714 shaders, ~13.5 MB of it) ran it out at match load: eft's loader writes
through the NULL of a failed allocation (0x04A6CEA4: crash). Test bank of 670 shaders loaded, 682 crashed
(the user's bisect: not the file size, sets or emitters).

  python3 tools/effect_heap_patch.py --rpx BASE.rpx       check the base's words (vanilla, or this patch's)
  (tools/edge_specials_build.py --rpx applies args())

The patch (two immediates, not relocated): the effect heap's size getter 0x02010B08 `lis r3, 0x2C0` (44 MiB) ->
0x3C0 (60 MiB), and 16 MiB taken from the file resource heap's getter 0x02010AF8 `lis r3, 0x1CC0` (460 MiB) ->
0x1BC0 (444 MiB), so MEM_ARENA_2's budget (0x02010AE8, 0x34E00000: the sum of its blocks; an overflow isn't
caught, the blocks would overlap) is unchanged. Only 0x033FA2E4 / 0x033FA39C call the effect heap's getter;
nothing else is sized from it. Source: the heap reads (eft's loader 0x04A6CD18 -> 0x04A6CE40 shader count,
0x6E8-byte shader objects, program copies 0x04A594B8 / 0x04A59618 / 0x04A59778; the manager's heap at
0x032F1648, created 0x032EF824), docs/native-notes.md "Effect heap".

Since multi-instance bugs v3 (exe_v11), also the animation heap: the 22 MiB heap behind 0x036C9350 (its allocator
at [0x1057DBD8], made at 0x03326328 from the arena block of getter 0x02010B18 `lis r3, 0x160`, mutex [0x104470F4])
holds every model instance's motion objects (0x0332637C: 0x340 each) and per-bone arrays (0x036B34A0 / 0x036B32C4
bones x 64, 0x036B8040 x 16 and x 0x88, 0x036AA2FC x 0xA0 ...); a failed allocation there ends in `li r3, 0; twu r31,
r31` (an assert: Cemu's debugger parks the thread, the game hangs at load with no crash log). Two Sephiroths (41
model-bearing article instances each, 24 trails of 49 bones) hung at the second's 31st (exe_diag_v3b: his 17th
trail's model / motion set-up, 0x02B62F14, never returned). The patch: that getter + ANIM_GROW_MIB, taken from the
default heap (MEM2 left after MEM_ARENA_2: the arena's total 0x02010AE8 `lis r3, 0x34E0` + the same, read once at
0x03374F38; Cemu's MEM2 ~1007 MiB, so the default heap goes ~162 -> ~138 MiB), not from another arena block.
Only 0x03326310 / 0x03326320 call the getter (the block's bump allocation and the heap made over it).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EFFECT_GETTER, RESOURCE_GETTER = 0x02010B08, 0x02010AF8
ANIM_GETTER, ARENA_TOTAL = 0x02010B18, 0x02010AE8
ORIGINAL = {EFFECT_GETTER: 0x3C6002C0, RESOURCE_GETTER: 0x3C601CC0,        # lis r3, 0x2C0 / lis r3, 0x1CC0
            ANIM_GETTER: 0x3C600160, ARENA_TOTAL: 0x3C6034E0}               # lis r3, 0x160 / lis r3, 0x34E0
GROW_MIB = 16
ANIM_GROW_MIB = 24


def patches():
    return {EFFECT_GETTER: ORIGINAL[EFFECT_GETTER] + GROW_MIB * 0x10,           # 0x2C0 -> 0x3C0 (units of 64 KiB)
            RESOURCE_GETTER: ORIGINAL[RESOURCE_GETTER] - GROW_MIB * 0x10}       # 0x1CC0 -> 0x1BC0


def anim_patches():
    """the animation heap 22 -> 46 MiB, the MEM_ARENA_2 total grown by the same (the default heap gives it)"""
    return {ANIM_GETTER: ORIGINAL[ANIM_GETTER] + ANIM_GROW_MIB * 0x10,          # 0x160 -> 0x2E0 (units of 64 KiB)
            ARENA_TOTAL: ORIGINAL[ARENA_TOTAL] + ANIM_GROW_MIB * 0x10}          # 0x34E0 -> 0x3660


def all_patches():
    return {**patches(), **anim_patches()}


def check_base(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    p = all_patches()
    bad = ['0x%08X: 0x%08X' % (a, img.w(a)) for a, w in ORIGINAL.items() if img.w(a) not in (w, p[a])]
    if bad:
        raise SystemExit('effect_heap_patch: unexpected words in %s: %s' % (rpx, ', '.join(bad)))


def args():
    return ['0x%08X=0x%08X' % (a, w) for a, w in sorted(all_patches().items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx')
    a = ap.parse_args()
    if a.rpx:
        check_base(a.rpx)
        print('ok:', ' '.join(args()))
    else:
        print(' '.join(args()))


if __name__ == '__main__':
    main()
