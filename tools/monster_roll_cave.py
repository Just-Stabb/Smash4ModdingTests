#!/usr/bin/env python3
"""Minecraft World's night monsters rolled each match and each night, as Ultimate rolls them.
Prints rpx_patch.py args (added after the standard build's; it takes over the generic stage's
update / setup hooks from stage_script_cave.py, the moving-platform test, which it replaces).

The stage files have each monster in its own model folder (MONSTERS: tools/minecraft_world.py's
MONSTER_SETS), animated every night. StageBaseCafe's update (0x02D1CF9C) calls the base update with
`bl 0x031415C8` at 0x02D1CFDC: that call goes to UPDATE, which makes it and then, for kind KIND
(stage + 0), adds the frame rate (f1, as the stage's animations do) to a frame counter wrapping
at CYCLE (the day / night cycle); on the first update and at each wrap (dawn's end: the monsters
are gone by then and come back at 4200) it rolls DRAWS spawns with Ultimate's odds
(pickel_world.stdat: zombie / skeleton / spider / enderman 40 / 35 / 20 / 5; the game's
clock-seeded xorshift, 0x024F6BE8(n) = x % n, not the battle RNG) and shows the monsters rolled,
hides the others. The setup (0x02D1C65C) starts at RESET: counter 0, a roll due.

A model by folder name: 0x03141D2C(stage, name) -> StageModel or 0. Shown / hidden as the game's
own setAllVisible (0x03159750) does it for one model: flags (+0x118) bit 0x80000 set / cleared;
with both 0x80000 and the stage-wide 0x40000 set it's added to the render scene (0x03158994(m, 0))
unless it's already visible (0x032FF668(m + 0xDC)), else removed (0x031589E0(m, 0)) if it is;
then 0x032FF68C(m + 0xDC, both set).

Omega (StageBaseEnd, another class) isn't hooked: its monsters all come every night.

Space: grown code 0x04B7F400-0x04B80000 (biome_select_cave.py's before it).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B7F400
LIMIT = 0x04B80000
UPDATE_HOOK = 0x02D1CFDC       # bl 0x031415C8 in StageBaseCafe's update 0x02D1CF9C
BASE_UPDATE = 0x031415C8
SETUP = 0x02D1C65C             # StageBaseCafe setup (vtable +0x1C)
SETUP_FIRST = 'stwu r1, -0x298(r1)'
FIND_MODEL = 0x03141D2C        # (stage, folder name) -> StageModel* or 0
SCENE_ADD = 0x03158994        # (m, 0)
SCENE_REMOVE = 0x031589E0      # (m, 0)
IS_VISIBLE = 0x032FF668        # (m + 0xDC) -> bool
SET_VISIBLE = 0x032FF68C       # (m + 0xDC, bool)
RAND = 0x024F6BE8              # (n) -> x % n, the clock-seeded xorshift (instance 1); beyond bl reach: bctrl

KIND = 0x80                    # NewStage01, normal play
CYCLE = 9000.0                 # minecraft_world.CYCLE
DRAWS = 3                      # spawns a night (each a roll of the odds; a monster rolled again
                               # shows once: zombie ~78% of nights, enderman ~14%)
# (folder, odds in %): minecraft_world.MONSTER_SETS, pickel_world.stdat's odds
MONSTERS = [('dyr_h_BG_more_far0_set', 40), ('dyr_f_BG_far2_set_set', 35), ('dyr_g_bgfar_set', 20),
            ('dyr_n1_sunset_set', 5)]
assert sum(o for _f, o in MONSTERS) == 100


def build():
    a = Asm(CAVE)
    a.asm("""
reset:
        lis r12, data@ha
        addi r12, r12, data@l
        li r11, 0
        stw r11, 0(r12)
        li r11, 1
        stw r11, 8(r12)
        %(first)s
        b 0x%(setup1)08X
update:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r26, 0x40(r1)
        stfd f31, 0x30(r1)
        mr r31, r3
        fmr f31, f1
        bl 0x%(base)08X
        mr r30, r3
        lwz r0, 0(r31)
        cmpwi r0, %(kind)d
        bne done
        lis r29, data@ha
        addi r29, r29, data@l
        lfs f0, 0(r29)
        fadds f0, f0, f31
        lfs f13, 4(r29)
        fcmpu cr0, f0, f13
        blt keep
        fsubs f0, f0, f13
        li r0, 1
        stw r0, 8(r29)
keep:
        stfs f0, 0(r29)
        lwz r0, 8(r29)
        cmpwi r0, 0
        beq done
        li r0, 0
        stw r0, 8(r29)
        li r28, 0
        li r27, %(draws)d
draw:
        li r3, 100
        lis r12, 0x%(rand_hi)04X
        ori r12, r12, 0x%(rand_lo)04X
        mtctr r12
        bctrl
        addi r4, r29, 12
        li r5, 0
odds:
        slwi r6, r5, 2
        lwzx r6, r4, r6
        cmplw r3, r6
        blt got
        addi r5, r5, 1
        cmpwi r5, %(last)d
        blt odds
got:
        li r6, 1
        slw r6, r6, r5
        or r28, r28, r6
        addi r27, r27, -1
        cmpwi r27, 0
        bne draw
        stw r28, 0x1C(r29)
        li r27, 0
apply:
        mr r3, r31
        slwi r4, r27, 2
        addi r5, r29, 0x20
        lwzx r4, r5, r4
        bl 0x%(find)08X
        mr. r26, r3
        beq nextm
        srw r0, r28, r27
        andi. r0, r0, 1
        lwz r5, 0x118(r26)
        lis r6, 8
        andc r5, r5, r6
        beq flag
        or r5, r5, r6
flag:
        stw r5, 0x118(r26)
        srwi r5, r5, 18
        andi. r5, r5, 3
        cmpwi r5, 3
        bne off
        addi r3, r26, 0xDC
        bl 0x%(isvis)08X
        cmpwi r3, 0
        bne setv
        mr r3, r26
        li r4, 0
        bl 0x%(add)08X
        b setv
off:
        addi r3, r26, 0xDC
        bl 0x%(isvis)08X
        cmpwi r3, 0
        beq setv
        mr r3, r26
        li r4, 0
        bl 0x%(remove)08X
setv:
        lwz r5, 0x118(r26)
        srwi r5, r5, 18
        andi. r5, r5, 3
        li r4, 0
        cmpwi r5, 3
        bne sv
        li r4, 1
sv:
        addi r3, r26, 0xDC
        bl 0x%(setvis)08X
nextm:
        addi r27, r27, 1
        cmpwi r27, %(n)d
        blt apply
done:
        mr r3, r30
        lfd f31, 0x30(r1)
        lmw r26, 0x40(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr
data:
        .float 0
        .float %(cycle)r
        .word 1
""" % dict(first=SETUP_FIRST, setup1=SETUP + 4, base=BASE_UPDATE, kind=KIND, draws=DRAWS, rand_hi=RAND >> 16, rand_lo=RAND & 0xFFFF,
           last=len(MONSTERS) - 1, find=FIND_MODEL, isvis=IS_VISIBLE, add=SCENE_ADD, remove=SCENE_REMOVE,
           setvis=SET_VISIBLE, n=len(MONSTERS), cycle=CYCLE))
    # data +12: the odds' running sums (4 words), +0x1C the last roll's mask, +0x20 the names' pointers
    cum, run = [], 0
    for _f, o in MONSTERS:
        run += o
        cum.append(run)
    for c in cum:
        a.asm('.word %d' % c)
    a.asm('.word 0')
    names_at = a.addr('data') + 0x20 + 4 * len(MONSTERS)
    strings, ptrs = b'', []
    for folder, _o in MONSTERS:
        ptrs.append(names_at + len(strings))
        s = folder.encode() + b'\0'
        strings += s + b'\0' * (-len(s) % 4)
    for p in ptrs:
        a.asm('.word 0x%08X' % p)
    for i in range(0, len(strings), 4):
        a.asm('.word 0x%08X' % int.from_bytes(strings[i:i + 4], 'big'))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    assert words[(a.addr('data') + 0x20 - CAVE) // 4] == ptrs[0]
    hook = Asm(UPDATE_HOOK)
    hook.asm('bl 0x%08X' % a.addr('update'))
    setup = Asm(SETUP)
    setup.asm('b 0x%08X' % a.addr('reset'))
    return a, words, [(UPDATE_HOOK, hook.words()[0]), (SETUP, setup.words()[0])]


def main():
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('monster roll: %d words, counter / roll at 0x%08X\n' % (len(words), a.addr('data')))


if __name__ == '__main__':
    main()
