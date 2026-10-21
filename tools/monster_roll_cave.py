#!/usr/bin/env python3
"""Minecraft World's mobs, spawned as Ultimate's stage code does it (its pickel_world.stdat odds):
the animals' kind each match, the monsters each night. Prints rpx_patch.py args (added after the
standard build's; it takes over the generic stage's update / setup hooks from
stage_script_cave.py, the moving-platform test, which it replaces).

The stage files (tools/minecraft_world.py) have the mobs in four Battlefield model folders
(FOLDERS), each a day animal and a night monster (each scaled to nothing outside its time by its
own animation): dyr_h sheep + zombie, dyr_f cow + skeleton, dyr_g chicken + spider, dyr_n1 the
enderman. Showing a folder by day shows its animal, by night its monster.

StageBaseCafe's update (0x02D1CF9C; Omega's StageBaseEnd update 0x0264CEBC calls it too) calls
the base update with `bl 0x031415C8` at 0x02D1CFDC: that goes to UPDATE, which makes it and then,
for kinds KINDS (stage + 0: NewStage01 and its Omega), adds the frame rate (f1, as the stage's
animations do) to a frame counter over the day / night cycle (CYCLE):
- on the first update (the setup, 0x02D1C65C, which Omega's calls too, flags a new match): rolls
  the match's animals (sheep / chicken / cow 30 / 30 / 30, none 10%) and shows their folder;
- at MONSTER_FRAME (frame_of_monster 4200) each night: rolls how many monsters come (guest
  single / double / triple 20 / 60 / 20) and which (that many different kinds, weighted zombie /
  skeleton / spider / enderman 40 / 35 / 20 / 5), and shows their folders;
- at the cycle's end (the monsters gone, the animals back at frame 0): the animals' folder again.
Rolls: the game's clock-seeded xorshift, 0x024F6BE8(n) = x % n (not the battle RNG).

A model by folder name: 0x03141D2C(stage, name) -> StageModel or 0. Shown / hidden as the game's
own setAllVisible (0x03159750) does it for one model: flags (+0x118) bit 0x80000 set / cleared;
with both 0x80000 and the stage-wide 0x40000 set it's added to the render scene (0x03158994(m, 0))
unless it's already visible (0x032FF668(m + 0xDC)), else removed (0x031589E0(m, 0)) if it is;
then 0x032FF68C(m + 0xDC, both set).

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

KINDS = (0x80, 0x81)            # NewStage01, normal play and Omega
CYCLE = 9000.0                 # minecraft_world.CYCLE
MONSTER_FRAME = 4200.0         # pickel_world.stdat frame_of_monster
FOLDERS = ['dyr_h_BG_more_far0_set', 'dyr_f_BG_far2_set_set', 'dyr_g_bgfar_set', 'dyr_n1_sunset_set']
MONSTER_ODDS = [40, 35, 20, 5]             # zombie, skeleton, spider, enderman: folders 0-3
ANIMAL_ODDS = [(30, 0), (30, 2), (30, 1)]  # sheep (folder 0), chicken (2), cow (1); the rest: none
COUNT_ODDS = [20, 60, 20]                  # one / two / three monsters a night


def build():
    a = Asm(CAVE)
    animal = ''
    run = 0
    for o, folder in ANIMAL_ODDS:
        run += o
        animal += """
        li r4, %d
        cmplwi r3, %d
        blt dset""" % (1 << folder, run)
    a.asm("""
reset:
        lis r12, data@ha
        addi r12, r12, data@l
        li r11, 0
        stw r11, 0(r12)
        li r11, 1
        stw r11, 0xC(r12)
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
        cmpwi r0, %(k0)d
        beq ours
        cmpwi r0, %(k1)d
        bne done
ours:
        lis r29, data@ha
        addi r29, r29, data@l
        lwz r0, 0xC(r29)
        cmpwi r0, 0
        beq counting
        li r0, 0
        stw r0, 0xC(r29)
        stw r0, 0x10(r29)
        bl roll_day
        mr r3, r31
        lwz r4, 0x14(r29)
        bl apply
counting:
        lfs f0, 0(r29)
        fadds f0, f0, f31
        lfs f13, 4(r29)
        fcmpu cr0, f0, f13
        blt nowrap
        fsubs f0, f0, f13
        stfs f0, 0(r29)
        li r0, 0
        stw r0, 0x10(r29)
        mr r3, r31
        lwz r4, 0x14(r29)
        bl apply
        b night
nowrap:
        stfs f0, 0(r29)
night:
        lwz r0, 0x10(r29)
        cmpwi r0, 0
        bne done
        lfs f0, 0(r29)
        lfs f13, 8(r29)
        fcmpu cr0, f0, f13
        blt done
        li r0, 1
        stw r0, 0x10(r29)
        bl roll_night
        mr r3, r31
        lwz r4, 0x18(r29)
        bl apply
done:
        mr r3, r30
        lfd f31, 0x30(r1)
        lmw r26, 0x40(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr
rand:
        lis r12, 0x%(rand_hi)04X
        ori r12, r12, 0x%(rand_lo)04X
        mtctr r12
        bctr
roll_day:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        li r3, 100
        bl rand
        %(animal)s
        li r4, 0
dset:
        stw r4, 0x14(r29)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
roll_night:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        li r3, 100
        bl rand
        li r28, 1
        cmplwi r3, %(c1)d
        blt nset
        li r28, 2
        cmplwi r3, %(c2)d
        blt nset
        li r28, 3
nset:
        li r27, 0
pick:
        li r26, 0
        li r5, 0
tot:
        srw r0, r27, r5
        andi. r0, r0, 1
        bne tskip
        slwi r6, r5, 2
        addi r7, r29, 0x1C
        lwzx r6, r7, r6
        add r26, r26, r6
tskip:
        addi r5, r5, 1
        cmpwi r5, 4
        blt tot
        cmpwi r26, 0
        beq ndone
        mr r3, r26
        bl rand
        li r5, 0
walk:
        srw r0, r27, r5
        andi. r0, r0, 1
        bne wskip
        slwi r6, r5, 2
        addi r7, r29, 0x1C
        lwzx r6, r7, r6
        cmplw r3, r6
        blt take
        subf r3, r6, r3
wskip:
        addi r5, r5, 1
        cmpwi r5, 4
        blt walk
        b ndone
take:
        li r6, 1
        slw r6, r6, r5
        or r27, r27, r6
        addi r28, r28, -1
        cmpwi r28, 0
        bne pick
ndone:
        stw r27, 0x18(r29)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
apply:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r25, 0x14(r1)
        mr r25, r3
        mr r28, r4
        li r27, 0
ap:
        mr r3, r25
        slwi r4, r27, 2
        addi r5, r29, 0x2C
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
        cmpwi r27, 4
        blt ap
        lmw r25, 0x14(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
data:
        .float 0
        .float %(cycle)r
        .float %(mframe)r
        .word 1
        .word 0
        .word 0
        .word 0
""" % dict(first=SETUP_FIRST, setup1=SETUP + 4, base=BASE_UPDATE, k0=KINDS[0], k1=KINDS[1],
           rand_hi=RAND >> 16, rand_lo=RAND & 0xFFFF, animal=animal, c1=COUNT_ODDS[0],
           c2=COUNT_ODDS[0] + COUNT_ODDS[1], find=FIND_MODEL, isvis=IS_VISIBLE, add=SCENE_ADD,
           remove=SCENE_REMOVE, setvis=SET_VISIBLE, cycle=CYCLE, mframe=MONSTER_FRAME))
    # data: +0 counter, +4 cycle, +8 monster frame, +0xC new match, +0x10 tonight rolled, +0x14 the
    # animals' folders, +0x18 tonight's monsters' folders, +0x1C the monsters' weights, +0x2C the
    # folders' names
    for w in MONSTER_ODDS:
        a.asm('.word %d' % w)
    names_at = a.addr('data') + 0x2C + 4 * len(FOLDERS)
    strings, ptrs = b'', []
    for folder in FOLDERS:
        ptrs.append(names_at + len(strings))
        s_ = folder.encode() + b'\0'
        strings += s_ + b'\0' * (-len(s_) % 4)
    for p in ptrs:
        a.asm('.word 0x%08X' % p)
    for i in range(0, len(strings), 4):
        a.asm('.word 0x%08X' % int.from_bytes(strings[i:i + 4], 'big'))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    assert words[(a.addr('data') + 0x2C - CAVE) // 4] == ptrs[0]
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
    sys.stderr.write('mob roll: %d words, data at 0x%08X\n' % (len(words), a.addr('data')))


if __name__ == '__main__':
    main()
