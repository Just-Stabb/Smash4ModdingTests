#!/usr/bin/env python3
"""Minecraft World's mobs, spawned as Ultimate's stage code does it (its pickel_world.stdat odds):
the animals' kind each match, the monsters each night. Prints rpx_patch.py args (added after the
standard build's; it takes over the generic stage's update / setup hooks from
stage_script_cave.py, the moving-platform test, which it replaces).

The stage files (tools/minecraft_world.py) have each mob kind in a model folder of its own
(FOLDERS; each scaled to nothing outside its time by its own animation): the monsters in four of
Battlefield's (dyr_h zombie, dyr_f skeleton, dyr_g spider, dyr_n1 enderman), the animals (there
day and night, as in Ultimate) in three of the port's own (dyr_p sheep, dyr_q cow, dyr_r chicken).

StageBaseCafe's update (0x02D1CF9C; Omega's StageBaseEnd update 0x0264CEBC calls it too) calls
the base update with `bl 0x031415C8` at 0x02D1CFDC: that goes to UPDATE, which makes it and then,
for kinds KINDS (stage + 0: NewStage01 and its Omega), adds the frame rate (f1, as the stage's
animations do) to a frame counter over the day / night cycle (CYCLE):
- on the first update (the setup, 0x02D1C65C, which Omega's calls too, flags a new match): rolls
  the match's animals (sheep / chicken / cow 30 / 30 / 30, none 10%);
- at MONSTER_FRAME (frame_of_monster 4200) each night: rolls how many monsters come (guest
  single / double / triple 20 / 60 / 20) and which (that many different kinds, weighted zombie /
  skeleton / spider / enderman 40 / 35 / 20 / 5);
- at the cycle's end (the monsters gone): the night's roll cleared.
Every update it shows the folders of the match's animals and, from MONSTER_FRAME to the cycle's
end, the night's monsters, and hides the rest: v17b set them once, at the first update, and the
game showing all of the stage's models as the match starts brought every animal kind back (all
walking the same pen: the user saw them inside each other).
Sounds (tools/minecraft_sound.py's bank; the events tools/minecraft_world.py lists in
minecraft_sound_events.json, by biome and form): the stage's sound object is made by its name
(0x03122E08(X, name, form) -> X + 0x390); NewStage01 matched none, so its name (and its biome
folders') is matched as BattleField_f (NAME hook). Each update plays its biome's events (the biome
cave's pick mod 6; Omega its own table) up to the cycle's frame whose mob's folder is shown, a
variant at random: 0x03125D80(S, handle, (row 1147 << 16) | tone), the handle released after.

Rolls: the game's clock-seeded xorshift, 0x024F6BE8(n) = x % n (not the battle RNG).

A model by folder name: 0x03141D2C(stage, name) -> StageModel or 0. Shown / hidden as the game's
own setAllVisible (0x03159750) does it for one model: flags (+0x118) bit 0x80000 set / cleared;
with both 0x80000 and the stage-wide 0x40000 set it's added to the render scene (0x03158994(m, 0))
unless it's already visible (0x032FF668(m + 0xDC)), else removed (0x031589E0(m, 0)) if it is;
then 0x032FF68C(m + 0xDC, both set).

Space: grown code 0x04B7F400-0x04B84000 (biome_select_cave.py's before it).
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402
import biome_select_cave  # noqa: E402
import minecraft_sound  # noqa: E402

CAVE = 0x04B7F400
LIMIT = 0x04B84000            # grown (the sound event tables: ~6 KB)
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
# sounds (tools/minecraft_sound.py's bank, the events tools/minecraft_world.py --sound-events lists)
EVENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'minecraft_sound_events.json')
SOUND_ROW = minecraft_sound.ROW
PLAY_SE = 0x03125D80           # (stage sound object, handle out (0x30 bytes), sound id): a stage's sound
RELEASE = 0x033EFD88           # (handle, 2): the handle's destructor (not freed)
SOUND_NAME = 0x03122E08        # (X, name, form): makes X+0x390, the stage's sound object, by its name
SOUND_NAME_FIRST = 'stwu r1, -0x28(r1)'
BATTLEFIELD_NAME = 0x10167024  # "BattleField_f" (rodata), the name it's matched to
STAGE_NAME = 'NewStage01'      # its prefix (the biome folders' names too)
TABLES = [(b, 'melee') for b, _f in biome_select_cave.BIOMES[:biome_select_cave.N_BIOMES]] + [('plains', 'end')]
CYCLE = 9000.0                 # minecraft_world.CYCLE
MONSTER_FRAME = 4200.0         # pickel_world.stdat frame_of_monster
# the monsters' folders, then the animals' (minecraft_world.MONSTER_SETS, ANIMAL_SETS)
FOLDERS = ['dyr_h_BG_more_far0_set', 'dyr_f_BG_far2_set_set', 'dyr_g_bgfar_set', 'dyr_n1_sunset_set',
           'dyr_p_animal_sheep_set', 'dyr_q_animal_cow_set', 'dyr_r_animal_chicken_set']
MONSTERS = 4
MONSTER_NAMES = ['zombie', 'skeleton', 'spider', 'enderman']
MONSTER_ODDS = [40, 35, 20, 5]             # zombie, skeleton, spider, enderman: folders 0-3
ANIMAL_ODDS = [(30, 4), (30, 6), (30, 5)]  # sheep (folder 4), chicken (6), cow (5); the rest: none
COUNT_ODDS = [20, 60, 20]                  # one / two / three monsters a night


def words_of(b):
    b += b'\0' * (-len(b) % 4)
    return [int.from_bytes(b[i:i + 4], 'big') for i in range(0, len(b), 4)]


def event_tables(path=None):
    """[bytes] a table each of TABLES: 8-byte events (frame, tone, mob bit or 0xFF, variants, 0),
    ending with frame 0xFFFF"""
    path = path or EVENTS
    events = json.load(open(path)) if os.path.exists(path) else {}
    bits = {'always': 0xFF}
    for k, f in enumerate(FOLDERS):
        bits[f.split('_')[-2] if k >= MONSTERS else MONSTER_NAMES[k]] = k
    out = []
    for biome, form in TABLES:
        b = b''
        for frame, sound, mob in sorted(events.get('%s/%s' % (biome, form), [])):
            tone, variants = minecraft_sound.tone_index(sound)
            b += struct.pack('>HHBBH', frame, tone, bits[mob], variants, 0)
        out.append(b + struct.pack('>HHBBH', 0xFFFF, 0, 0, 0, 0))
    return out


def build():
    pick = biome_select_cave.build()[0].addr('data') + 4
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
        stw r0, -4(r29)
        bl roll_day
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
        stw r0, -4(r29)
        b night
nowrap:
        stfs f0, 0(r29)
night:
        lwz r0, 0x10(r29)
        cmpwi r0, 0
        bne current
        lfs f0, 0(r29)
        lfs f13, 8(r29)
        fcmpu cr0, f0, f13
        blt current
        li r0, 1
        stw r0, 0x10(r29)
        bl roll_night
current:
        lwz r0, 0x10(r29)
        lwz r4, 0x14(r29)
        cmpwi r0, 0
        beq cur
        lwz r4, 0x18(r29)
cur:
        mr r28, r4
        mr r3, r31
        bl apply
        mr r3, r31
        mr r4, r28
        bl sounds
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
        cmpwi r5, %(monsters)d
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
        cmpwi r5, %(monsters)d
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
        lwz r0, 0x14(r29)
        or r27, r27, r0
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
        cmpwi r27, %(folders)d
        blt ap
        lmw r25, 0x14(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
sounds:
        stwu r1, -0x70(r1)
        mflr r0
        stw r0, 0x74(r1)
        stmw r24, 0x50(r1)
        mr r31, r3
        mr r30, r4
        lis r29, data@ha
        addi r29, r29, data@l
        lfs f0, 0(r29)
        fctiwz f0, f0
        stfd f0, 0x48(r1)
        lwz r28, 0x4C(r1)
        lwz r0, 0(r31)
        li r27, %(end_table)d
        cmpwi r0, %(k1)d
        beq tab
        lis r12, 0x%(pick_hi)04X
        ori r12, r12, 0x%(pick_lo)04X
        lwz r27, 0(r12)
        li r0, %(n_biomes)d
        divwu r12, r27, r0
        mullw r12, r12, r0
        subf r27, r12, r27
tab:
        slwi r27, r27, 2
        lis r12, tables@ha
        addi r12, r12, tables@l
        lwzx r26, r12, r27
        lwz r25, -4(r29)
sloop:
        slwi r12, r25, 3
        add r24, r26, r12
        lhz r0, 0(r24)
        cmplw r0, r28
        bgt sout
        addi r25, r25, 1
        lbz r0, 4(r24)
        cmpwi r0, 0xFF
        beq splay
        srw r0, r30, r0
        andi. r0, r0, 1
        beq sloop
splay:
        lbz r3, 5(r24)
        bl rand
        lhz r0, 2(r24)
        add r5, r3, r0
        oris r5, r5, 0x%(row)04X
        lwz r3, 0xFF0(r31)
        cmpwi r3, 0
        beq sloop
        lwz r3, 0(r3)
        cmpwi r3, 0
        beq sloop
        lwz r3, 0x390(r3)
        cmpwi r3, 0
        beq sloop
        addi r4, r1, 0x10
        bl 0x%(play)08X
        addi r3, r1, 0x10
        li r4, 2
        bl 0x%(release)08X
        b sloop
sout:
        stw r25, -4(r29)
        lmw r24, 0x50(r1)
        lwz r0, 0x74(r1)
        mtlr r0
        addi r1, r1, 0x70
        blr
namefix:
        lis r12, sname@ha
        addi r12, r12, sname@l
        addi r12, r12, -1
        addi r11, r4, -1
        li r0, %(name_len)d
        mtctr r0
ncmp:
        lbzu r9, 1(r11)
        lbzu r10, 1(r12)
        cmpw r9, r10
        bne nkeep
        bdnz ncmp
        lis r4, 0x%(bf_hi)04X
        ori r4, r4, 0x%(bf_lo)04X
nkeep:
        %(name_first)s
        b 0x%(name_back)08X
sname:
        %(sname)s
snext:
        .word 0
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
           remove=SCENE_REMOVE, setvis=SET_VISIBLE, cycle=CYCLE, mframe=MONSTER_FRAME,
           monsters=MONSTERS, folders=len(FOLDERS), end_table=len(TABLES) - 1, pick_hi=pick >> 16,
           pick_lo=pick & 0xFFFF, n_biomes=biome_select_cave.N_BIOMES, row=SOUND_ROW, play=PLAY_SE,
           release=RELEASE, name_len=len(STAGE_NAME), bf_hi=BATTLEFIELD_NAME >> 16,
           bf_lo=BATTLEFIELD_NAME & 0xFFFF, name_first=SOUND_NAME_FIRST, name_back=SOUND_NAME + 4,
           sname='\n'.join('.word 0x%08X' % w for w in words_of(STAGE_NAME.encode() + b'\0'))))
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
    tables = event_tables()
    a.asm('tables:')
    at = a.addr('tables') + 4 * len(tables)
    for t in tables:
        a.asm('.word 0x%08X' % at)
        at += len(t)
    for t in tables:
        for w in words_of(t):
            a.asm('.word 0x%08X' % w)
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    assert words[(a.addr('data') + 0x2C - CAVE) // 4] == ptrs[0]
    hook = Asm(UPDATE_HOOK)
    hook.asm('bl 0x%08X' % a.addr('update'))
    setup = Asm(SETUP)
    setup.asm('b 0x%08X' % a.addr('reset'))
    name = Asm(SOUND_NAME)
    name.asm('b 0x%08X' % a.addr('namefix'))
    return a, words, [(UPDATE_HOOK, hook.words()[0]), (SETUP, setup.words()[0]), (SOUND_NAME, name.words()[0])]


def main():
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('mob roll: %d words, data at 0x%08X\n' % (len(words), a.addr('data')))


if __name__ == '__main__':
    main()
