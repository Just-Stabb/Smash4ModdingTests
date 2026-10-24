#!/usr/bin/env python3
"""Hold L while the game starts to go straight to Training (its character select), skipping the
opening, the title screen and the menus. Prints rpx_patch.py args (added after the standard build's).

The root sequence controller (method 0x02C841E4, vtable entry 0x1010E10C) sets itself up once, after
the boot scenes: it maps every mode's sequence scene to a menu state ("SingleTrainingSeqCtrlScene" ->
0x13, ...) and ends by starting "TitleSequenceScene":

  0x02C87650  addi r3, r29, -0x24E0      ; "TitleSequenceScene" (0x1010DB20)
  0x02C87654  bl 0x020FF398              ; its id
  0x02C87658  lwz r4, 0(r30)
  0x02C8765C  mr r6, r3
  0x02C87660  addi r5, r29, -0x24E0      ; the name again
  0x02C87664  addi r3, r30, 8
  0x02C87668  bl 0x033FD77C              ; start it

The two name loads become `bl` into the cave. The first reads every controller's held buttons (the
pad manager's slot array, as biome_select_cave.py does); with L held it does what the main menu's
Training entry does (launch case 0x5F of 0x02C881D4: the menu mode 0xB through 0x02C840CC, then
"SingleTrainingSeqCtrlScene") and returns that name instead; the second returns the same pick.
Leaving Training goes back through the controller as from the menu's Training.

Space: 0x04B84A00-0x04B85000 (zeros after stage_omega_cave.py's 0x04B84900). The first version sat
at 0x04B85000, on kind_expand.py's old space, and crashed the game at boot on Cemu (Cemu asserted on
an HLE call at 0x04B85170, in the old space's stale words, just before the first hook; the same
executable without the shortcut booted). The old space (0x04B85000-0x04B877C4: kind_expand's tables
from when it had one kind there; nothing refers to it any more) is now cleared to zeros too.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B84A00
LIMIT = 0x04B85000
OLD_SPACE = (0x04B85000, 0x04B877C4)   # kind_expand.py's first space: stale words, cleared
NAME_SITE = 0x02C87650          # addi r3, r29, -0x24E0
NAME_SITE_WORD = 0x387DDB20
NAME2_SITE = 0x02C87660         # addi r5, r29, -0x24E0
NAME2_SITE_WORD = 0x38BDDB20
TITLE = 0x1010DB20              # "TitleSequenceScene"
TRAINING = 0x1010DF04           # "SingleTrainingSeqCtrlScene"
SET_MODE = 0x02C840CC           # the menu mode (the Training launch passes 0xB)
TRAINING_MODE = 0xB
PADS = 0x1057581C               # the pad manager's slot array
SLOTS = 17                      # 0 GamePad, (1 a dummy), 2-8 Wii Remotes / Pro, 9-16 GameCube
L = 0x1000                      # L (the GameCube controller's left trigger too), the game's layout


def build():
    a = Asm(CAVE)
    a.asm("""
pick:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lis r10, 0x%(pads_hi)04X
        ori r10, r10, 0x%(pads_lo)04X
        li r11, 0
        li r8, 0
loop:
        cmpwi r8, 1
        beq next
        slwi r0, r8, 2
        lwzx r7, r10, r0
        cmpwi r7, 0
        beq next
        lwz r7, 8(r7)
        cmpwi r7, 0
        beq next
        lbz r0, 0x87(r7)
        cmpwi r0, 0
        beq next
        lwz r0, 0(r7)
        or r11, r11, r0
next:
        addi r8, r8, 1
        cmplwi r8, %(slots)d
        blt loop
        lis r3, 0x%(title_hi)04X
        ori r3, r3, 0x%(title_lo)04X
        andi. r0, r11, %(l)d
        beq done
        li r3, %(mode)d
        bl 0x%(set_mode)08X
        lis r3, 0x%(train_hi)04X
        ori r3, r3, 0x%(train_lo)04X
done:
        lis r12, sel@ha
        stw r3, sel@l(r12)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
again:
        lis r5, sel@ha
        lwz r5, sel@l(r5)
        blr
sel:
        .word 0x%(title)08X
""" % dict(pads_hi=PADS >> 16, pads_lo=PADS & 0xFFFF, slots=SLOTS, l=L, mode=TRAINING_MODE, set_mode=SET_MODE,
           title=TITLE, title_hi=TITLE >> 16, title_lo=TITLE & 0xFFFF, train_hi=TRAINING >> 16,
           train_lo=TRAINING & 0xFFFF))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    hooks = []
    for site, label in ((NAME_SITE, 'pick'), (NAME2_SITE, 'again')):
        h = Asm(site)
        h.asm('bl 0x%08X' % a.addr(label))
        hooks.append((site, h.words()[0]))
    return a, words, hooks


def main():
    a, words, hooks = build()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x00000000' % a for a in range(OLD_SPACE[0], OLD_SPACE[1], 4)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('boot training: %d words at 0x%08X, pick at 0x%08X\n' % (len(words), CAVE, a.addr('sel')))


if __name__ == '__main__':
    main()
