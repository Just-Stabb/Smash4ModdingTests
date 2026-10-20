#!/usr/bin/env python3
"""Kirby's copy held model (Marth's sword, ...) shown in more motions. Prints rpx_patch.py args.

  python3 tools/copy_held_cave.py [MOTION ...]      (default: 0x380 0x382 0x384)

Kirby's per-frame copy update (0x02B02534) shows or hides the copy's held model (the RPX's
held-model table 0x1041A8A0: marthsword, ikesword, gamewatchpan, ...; object [fighter+0x28]+0xA8,
vtable +0xA4 visible?, +0x94 set visible) by **status kind** only: 0x181, 0x18F-0x191, 0x1BC-0x1C4
(Marth's Shield Breaker 0x1C1-0x1C4), 0x1FC, 0x202-0x205, 0x20B-0x20E, 0x21F-0x221, 0x229-0x22B,
0x242-0x248 show it (0x02B026B4), any other status hides it (0x02B02730). So no script, motion or
animation could show the sword in Kirby's Strike aerials (their status is the aerial one).

The hook on the hide path (0x02B02730, `lwz r3, 0xA8(r30)`) also takes the show path while
Kirby's motion kind ([accessor+0x44] MotionModule, vtable +0x94) is one of MOTIONS: the Marth
copy's slots 0x380 / 0x382 / 0x384, which only the Marth copy sword aerials play now (Shield
Breaker plays 0x37F / 0x37E / 0x383 there, fighters/kirby/specials.md); the sword's size and place
come from those animations' LHaveN track.

Space: 0x037EE5A0-0x037EE5F0, the end of copy_custom_cave.py's free CAVE_C space (Havok cave; its
code ends at 0x037EE428, copy_fx_cave.py's trampoline is at 0x037EE5F0). The grown code space
(0x04B7xxxx) is too far from the hook for a branch.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x037EE5A0
LIMIT = 0x037EE5F0
HOOK = 0x02B02730          # hide path: lwz r3, 0xA8(r30)
SHOW = 0x02B026B4
MOTIONS = [0x380, 0x382, 0x384]


def build(motions):
    a = Asm(CAVE)
    src = """
held:                                   # r27 module accessor, r30 [fighter+0x28]
        lwz r3, 0x44(r27)               # MotionModule
        lwz r12, 0(r3)
        lwz r12, 0x94(r12)              # motion kind
        mtctr r12
        bctrl
"""
    for m in motions:
        src += "        cmplwi r3, 0x%X\n        beq show\n" % m
    src += """
        lwz r3, 0xA8(r30)               # the hook's own instruction
        b 0x%08X
show:
        b 0x%08X
""" % (HOOK + 4, SHOW)
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'copy held cave too big'
    hook = Asm(HOOK)
    hook.asm('b 0x%08X' % CAVE)
    return words, hook.words()[0]


def main():
    motions = [int(x, 0) for x in sys.argv[1:]] or MOTIONS
    words, hook = build(motions)
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append('0x%08X=0x%08X' % (HOOK, hook))
    print(' '.join(out))


if __name__ == '__main__':
    main()
