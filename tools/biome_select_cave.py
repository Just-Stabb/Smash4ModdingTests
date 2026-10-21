#!/usr/bin/env python3
"""Minecraft World's biome on NewStage01: picked when the stage loads, by the buttons held, or at
random (as Ultimate picks one). Prints rpx_patch.py args (added after the standard build's).

Each biome is its own stage folder (stage/melee/<FOLDER>, built by tools/minecraft_world.py
--biome ...). The stage-kind path function (0x02D1FDA0: sprintf(out, "stage/melee/%s", name)) loads
the kind's name at 0x02D1FDD8 (`lwzx r5, r10, r8`, r8 = kind x 8); that word branches to PICK,
which for kind KIND (NewStage01, normal play) swaps in the biome's folder name. The kind's name
itself is unchanged (it also names the stage's music group), and so is Omega (kind 0x81, always
plains as in Ultimate's battle form).

The buttons: every controller's held word, ORed (the pad manager's static slot array 0x1057581C:
26 wrappers, +8 their status: +0 held buttons in the game's own layout, +0x87 valid this frame;
slot 0 the GamePad, 2-8 Wii Remotes / Pro, 9-16 the GameCube adapter; polled every frame, also
while loading). L held picks the biome (BUTTONS); otherwise one at random (the time base).

The path is built where a match's stage setting is made (0x0315800C, returning to SETTING_RET; it
is cached there and the loader uses that copy) and for an optional prefetch of the folder
(0x02AB82B0, LR 0x02AB83A4) whose order to it is unknown: only the setting build picks, any other
caller gets the last pick (a prefetch of another biome only wastes the prefetch). A setting can be
built more than once a match, so a pick is kept while setting builds come within WINDOW of each
other (the time base's upper word and the top byte of its lower: units of 2^24 ticks, ~0.27 s
at 62.15 MHz): a new match after a pause picks again.

Space: grown code 0x04B7F000-0x04B80000 (within `b` reach of the hook). The pick and the time are
words in it (writable in Cemu, as stage_script_cave.py's counter).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B7F000
LIMIT = 0x04B80000
HOOK = 0x02D1FDD8               # lwzx r5, r10, r8 (the kind's name) in the path function
HOOK_WORD = 0x7CAA402E
BACK = HOOK + 4
KIND = 0x80                     # NewStage01, normal play
SETTING_RET = 0x03158060        # the stage setting's build (bl at 0x0315805C), the call that picks
PADS = 0x1057581C               # the pad manager's slot array (26 wrappers)
SLOTS = 17                      # 0 GamePad, (1 a dummy), 2-8 Wii Remotes / Pro, 9-16 GameCube
WINDOW = 20                     # ~5.4 s

L, R, A = 0x1000, 0x2000, 0x10
STICK_LEFT, STICK_RIGHT, STICK_DOWN, STICK_UP = 0x80000, 0x100000, 0x200000, 0x400000
DPAD_LEFT, DPAD_RIGHT, DPAD_DOWN, DPAD_UP = 0x1, 0x2, 0x4, 0x8

# the biomes' folders, in the order the buttons pick them (index 0: L alone)
BIOMES = [('plains', 'NewStage01'), ('birchforest', 'NewStage01_forest'), ('savanna', 'NewStage01_savanna'),
          ('taiga', 'NewStage01_taiga'), ('snowytundra', 'NewStage01_tundra'), ('stoneshore', 'NewStage01_shore')]
# with L held: (buttons, biome index), the first that's held wins
BUTTONS = [(R, 1), (STICK_UP | DPAD_UP, 2), (STICK_RIGHT | DPAD_RIGHT, 3), (STICK_DOWN | DPAD_DOWN, 4),
           (STICK_LEFT | DPAD_LEFT, 5)]


def build():
    a = Asm(CAVE)
    tests = ''.join("""
        lis r0, 0x%04X
        ori r0, r0, 0x%04X
        and. r0, r11, r0
        li r9, %d
        bne chosen""" % (m >> 16, m & 0xFFFF, i) for m, i in BUTTONS)
    a.asm("""
pick:
        lwzx r5, r10, r8
        cmplwi r8, %(kind8)d
        bne back
        lis r12, data@ha
        addi r12, r12, data@l
        lwz r9, 4(r12)
        mflr r0
        lis r6, 0x%(ret_hi)04X
        ori r6, r6, 0x%(ret_lo)04X
        cmplw r0, r6
        bne use
        mftbu r6
        mftb r7
        slwi r6, r6, 8
        srwi r0, r7, 24
        or r6, r6, r0
        lwz r0, 0(r12)
        stw r6, 0(r12)
        subf r0, r0, r6
        cmplwi r0, %(window)d
        blt use
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
        andi. r0, r11, %(l)d
        beq random
        %(tests)s
        li r9, 0
        b chosen
random:
        mftb r7
        srwi r7, r7, 4
        li r0, %(n)d
        divwu r8, r7, r0
        mullw r8, r8, r0
        subf r9, r8, r7
chosen:
        stw r9, 4(r12)
use:
        slwi r9, r9, 2
        addi r7, r12, 8
        lwzx r5, r7, r9
back:
        b 0x%(back)08X
data:
        .word 0
        .word 0
""" % dict(kind8=KIND * 8, window=WINDOW, pads_hi=PADS >> 16, pads_lo=PADS & 0xFFFF, slots=SLOTS, l=L,
           tests=tests, n=len(BIOMES), back=BACK, ret_hi=SETTING_RET >> 16, ret_lo=SETTING_RET & 0xFFFF))
    names_at = a.addr('data') + 8 + 4 * len(BIOMES)
    strings, ptrs = b'', []
    for _biome, folder in BIOMES:
        ptrs.append(names_at + len(strings))
        s = folder.encode() + b'\0'
        strings += s + b'\0' * (-len(s) % 4)
    for p in ptrs:
        a.asm('.word 0x%08X' % p)
    for i in range(0, len(strings), 4):
        a.asm('.word 0x%08X' % int.from_bytes(strings[i:i + 4], 'big'))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    hook = Asm(HOOK)
    hook.asm('b 0x%08X' % a.addr('pick'))
    return a, words, [(HOOK, hook.words()[0])]


def main():
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('biome select: %d words, pick / time at 0x%08X\n' % (len(words), a.addr('data')))


if __name__ == '__main__':
    main()
