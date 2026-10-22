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
  the match's animals (sheep / chicken / cow 30 / 30 / 30: always one kind);
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
# the breakable blocks (v18; tools/minecraft_world.py's BREAKABLE, its table 'blocks/<biome>' in the
# events file): a stage gimmick each (as Luigi's Mansion's pillars: research in
# docs/minecraft-world.md), its own model folder and, on the fighting plane, collision link
GIM_CREATE = 0x03133A8C        # (0, kind 0, flags 2 (damage shapes), groups 1) -> gimmick wrapper
GIM_SHAPE = 0x03133FF0         # (w, group, &shape (0x28 bytes), 0): a hurt shape
GIM_ACTIVATE = 0x03133E4C      # (w, 0)
GIM_DAMAGE = 0x0313408C        # (w, group) -> f1 the damage it took this frame
GIM_REMOVE = 0x03133DFC        # (w): its battle object (the hurtbox) removed
LINK_FIND = 0x03142954         # (stage, short name) -> the link's ground list or 0
GROUNDS_OFF = 0x0315EDD8       # (ground list, 1 off / 0 on): 1 -> 0x02D5D870 per ground (+0x72 = 0,
                               # out of the collision manager's lists), 0 -> 0x02D5D6E0 (+0x72 = 1, as
                               # a new ground, 0x02D5ABA8); v18b passed 0, which left them on
BLOCK_RADIUS = 7.5             # minecraft_world.BLOCK_RADIUS
# Ultimate's block_life_rate_table (pickel_world.stdat): the blocks' lives × this by the number of
# fighters (1-8; SmashWiki: 1-3 ×1, 4 ×1.3, 5-6 ×1.4, 7-8 ×1.5), counted (live entries of the fighter
# table, as tools/position_vars_cave.py) at the first update that has fighters
LIFE_RATE = [1.0, 1.0, 1.0, 1.3, 1.4, 1.4, 1.5, 1.5]
FIGHTERS = 0x1035184C          # [[FIGHTERS] + 0]: +0 entries (0x76B0 each, live: byte +0x1E >= 4), +8 count
FIGHTER_ENTRY = 0x76B0
MAX_BLOCKS = 99                # names stc_blkNN_set / bNN
BLOCK_NAME, BLOCK_LINK = 'dyr_blk00_set', 'b00'
# cracks (v18f): each block folder (minecraft_world.BLOCK_SET, a dyr_ folder: the stage plays its motion)
# has its crack overlay's 10 stages on bones shown only in their window of CRACK_STEP frames (state 0:
# no crack, s + 1: stage s); every update the cave holds each intact block at its state's middle frame
# with the draw model's set-motion-frame (Manifold's set_motion_current_frame: 0x031593FC(m, f1, apply):
# the motion player at m + 0xF4, 0x0330A5F8 its frame; the model's own update 0x03158E24 advances it by
# f1 x m+0xF8, which can't leave the window). Stage = floor(10 x damage / life) (Minecraft's), a follower
# its column leader's.
SET_MOTION_FRAME = 0x031593FC  # (m, f1 frame, r4 apply the pose now)
CRACK_STEP = 10                # minecraft_world.CRACK_STEP
CRACK_STAGES = 10
CYCLE = 9000.0                 # minecraft_world.CYCLE
MONSTER_FRAME = 4200.0         # pickel_world.stdat frame_of_monster
# the monsters' folders, then the animals' (minecraft_world.MONSTER_SETS, ANIMAL_SETS)
FOLDERS = ['dyr_h_BG_more_far0_set', 'dyr_f_BG_far2_set_set', 'dyr_g_bgfar_set', 'dyr_n1_sunset_set',
           'dyr_p_animal_sheep_set', 'dyr_q_animal_cow_set', 'dyr_r_animal_chicken_set']
MONSTERS = 4
MONSTER_NAMES = ['zombie', 'skeleton', 'spider', 'enderman']
MONSTER_ODDS = [40, 35, 20, 5]             # zombie, skeleton, spider, enderman: folders 0-3
# sheep (folder 4), chicken (6), cow (5): weights (v17c rolled of 100, the last 10 none: matches
# without animals, which the user doesn't see in Ultimate)
ANIMAL_ODDS = [(30, 4), (30, 6), (30, 5)]
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


def block_tables(path=None):
    """([bytes] a table each biome (TABLES' melee ones): count, then 8 bytes a block: cell x, y, z
    (signed), life, material (minecraft_sound.BLOCK_MATERIALS), has a link, the index of its column's
    plane block (its own if on the plane), 0), the materials'
    sounds (8 bytes each: hit tone, variants, 0, broken tone, variants, 0)"""
    events = json.load(open(path or EVENTS)) if os.path.exists(path or EVENTS) else {}
    out = []
    for biome, form in TABLES[:-1]:
        blocks = events.get('blocks/%s' % biome, [])
        assert len(blocks) <= MAX_BLOCKS
        b = struct.pack('>I', len(blocks))
        for i, k in enumerate(blocks):
            x, y, z = int((k['x'] - 5) // 10), int((k['y'] - 5) // 10), int(round(k['z'] / 10))
            b += struct.pack('>bbbBBBBB', x, y, z, int(round(k['life'])),
                         minecraft_sound.BLOCK_MATERIALS.index(k['sound']), int(k['link']), k.get('leader', i), 0)
        out.append(b)
    mats = b''
    for m in minecraft_sound.BLOCK_MATERIALS:
        hit = minecraft_sound.tone_index('block_dmg_%s' % m)
        broken = minecraft_sound.tone_index('block_break_%s' % m)
        mats += struct.pack('>HBBHBB', hit[0], hit[1], 0, broken[0], broken[1], 0)
    return out, mats


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
        lis r12, bdata@ha
        stw r0, bdata@l(r12)
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
        mr r3, r31
        bl blocks
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
        li r3, %(animal_total)d
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
        mr r3, r31
        lhz r4, 2(r24)
        lbz r5, 5(r24)
        bl playsnd
        b sloop
sout:
        stw r25, -4(r29)
        lmw r24, 0x50(r1)
        lwz r0, 0x74(r1)
        mtlr r0
        addi r1, r1, 0x70
        blr
blocks:
        stwu r1, -0x80(r1)
        mflr r0
        stw r0, 0x84(r1)
        stmw r22, 0x50(r1)
        mr r31, r3
        lis r29, bdata@ha
        addi r29, r29, bdata@l
        lwz r0, 0(r29)
        cmpwi r0, 0
        bne brun
        li r0, 1
        stw r0, 0(r29)
        li r0, 0
        stw r0, 4(r29)
        stw r0, 12(r29)
        lwz r0, 0(r31)
        cmpwi r0, %(k0)d
        bne bout
        lis r12, 0x%(pick_hi)04X
        ori r12, r12, 0x%(pick_lo)04X
        lwz r27, 0(r12)
        cmplwi r27, %(n_biomes)d
        bge bout
        slwi r27, r27, 2
        lis r12, btables@ha
        addi r12, r12, btables@l
        lwzx r30, r12, r27
        lwz r27, 0(r30)
        addi r30, r30, 4
        stw r27, 4(r29)
        stw r30, 8(r29)
        li r28, 0
binit:
        cmpw r28, r27
        bge bout
        slwi r26, r28, 2
        slwi r12, r28, 3
        add r25, r30, r12
        li r0, 0
        lis r12, bwrap@ha
        addi r12, r12, bwrap@l
        stwx r0, r12, r26
        lbz r11, 6(r25)
        cmpw r11, r28
        beq bleader
        li r0, 2
        lis r12, bstate@ha
        addi r12, r12, bstate@l
        stwx r0, r12, r26
        b bmodel
bleader:
        li r0, 0
        lis r12, bstate@ha
        addi r12, r12, bstate@l
        stwx r0, r12, r26
        li r3, 0
        li r4, 0
        li r5, 2
        li r6, 1
        bl 0x%(gim_create)08X
        lis r12, bwrap@ha
        addi r12, r12, bwrap@l
        stwx r3, r12, r26
        mr. r24, r3
        bne bshape
        li r0, 1
        lis r12, bstate@ha
        addi r12, r12, bstate@l
        stwx r0, r12, r26
        b bmodel
bshape:
        lis r12, 0x4330
        stw r12, 0x40(r1)
        lis r12, bconst@ha
        addi r12, r12, bconst@l
        lfd f13, 0(r12)
        lfs f12, 8(r12)
        lfs f11, 12(r12)
        lbz r11, 0(r25)
        extsb r11, r11
        mulli r11, r11, 10
        addi r11, r11, 5
        xoris r11, r11, 0x8000
        stw r11, 0x44(r1)
        lfd f0, 0x40(r1)
        fsub f0, f0, f13
        frsp f0, f0
        stfs f0, 0x10(r1)
        lbz r11, 1(r25)
        extsb r11, r11
        mulli r11, r11, 10
        addi r11, r11, 5
        xoris r11, r11, 0x8000
        stw r11, 0x44(r1)
        lfd f0, 0x40(r1)
        fsub f0, f0, f13
        frsp f0, f0
        stfs f0, 0x14(r1)
        lbz r11, 2(r25)
        extsb r11, r11
        mulli r11, r11, 10
        xoris r11, r11, 0x8000
        stw r11, 0x44(r1)
        lfd f0, 0x40(r1)
        fsub f0, f0, f13
        frsp f0, f0
        stfs f0, 0x18(r1)
        stfs f11, 0x1C(r1)
        stfs f11, 0x20(r1)
        stfs f11, 0x24(r1)
        stfs f12, 0x28(r1)
        li r0, 0
        stw r0, 0x2C(r1)
        stw r0, 0x30(r1)
        stw r0, 0x34(r1)
        mr r3, r24
        li r4, 0
        addi r5, r1, 0x10
        li r6, 0
        bl 0x%(gim_shape)08X
        mr r3, r24
        li r4, 0
        bl 0x%(gim_activate)08X
        lis r12, 0x4330
        stw r12, 0x40(r1)
        lbz r0, 3(r25)
        stw r0, 0x44(r1)
        lis r12, bconst@ha
        addi r12, r12, bconst@l
        lfd f13, 16(r12)
        lfd f0, 0x40(r1)
        fsub f0, f0, f13
        frsp f0, f0
        lis r12, bhp@ha
        addi r12, r12, bhp@l
        add r12, r12, r26
        stfs f0, 0(r12)
        lis r12, bmax@ha
        addi r12, r12, bmax@l
        add r12, r12, r26
        stfs f0, 0(r12)
bmodel:
        mr r3, r28
        bl bnames
        mr r3, r31
        lis r4, bname@ha
        addi r4, r4, bname@l
        bl 0x%(find)08X
        lis r12, bmodels@ha
        addi r12, r12, bmodels@l
        stwx r3, r12, r26
        addi r28, r28, 1
        b binit
brun:
        lwz r27, 4(r29)
        lwz r30, 8(r29)
        lwz r0, 12(r29)
        cmpwi r0, 0
        bne bcounted
        lis r12, 0x%(fighters_hi)04X
        lwz r12, 0x%(fighters_lo)04X(r12)
        cmpwi r12, 0
        beq bcounted
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq bcounted
        lwz r11, 8(r12)
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq bcounted
        li r10, 0
        li r9, 0
bcount:
        cmpw r9, r11
        bge bcounts
        lbz r0, 0x1E(r12)
        cmplwi r0, 4
        blt bcskip
        addi r10, r10, 1
bcskip:
        addi r12, r12, %(entry)d
        addi r9, r9, 1
        b bcount
bcounts:
        cmpwi r10, 0
        beq bcounted
        cmpwi r10, 8
        ble bcmax
        li r10, 8
bcmax:
        li r0, 1
        stw r0, 12(r29)
        addi r10, r10, -1
        slwi r10, r10, 2
        lis r12, brate@ha
        addi r12, r12, brate@l
        lfsx f12, r12, r10
        lis r12, bhp@ha
        addi r12, r12, bhp@l
        lis r11, bmax@ha
        addi r11, r11, bmax@l
        li r9, 0
bcmul:
        cmpw r9, r27
        bge bcounted
        slwi r10, r9, 2
        lfsx f0, r12, r10
        fmuls f0, f0, f12
        stfsx f0, r12, r10
        lfsx f0, r11, r10
        fmuls f0, f0, f12
        stfsx f0, r11, r10
        addi r9, r9, 1
        b bcmul
bcounted:
        li r28, 0
bloop:
        cmpw r28, r27
        bge bout
        slwi r26, r28, 2
        slwi r12, r28, 3
        add r25, r30, r12
        lis r12, bstate@ha
        addi r12, r12, bstate@l
        lwzx r0, r12, r26
        cmpwi r0, 1
        beq bhide
        cmpwi r0, 2
        bne bintact
        lbz r11, 6(r25)
        slwi r11, r11, 2
        lwzx r0, r12, r11
        cmpwi r0, 1
        bne bfollow
        li r0, 1
        stwx r0, r12, r26
        b bhide
bintact:
        lis r12, bwrap@ha
        addi r12, r12, bwrap@l
        lwzx r3, r12, r26
        li r4, 0
        bl 0x%(gim_damage)08X
        lis r12, bconst@ha
        addi r12, r12, bconst@l
        lfs f13, 12(r12)
        fcmpu cr0, f1, f13
        ble bkeep
        lis r12, bhp@ha
        addi r12, r12, bhp@l
        add r24, r12, r26
        lfs f0, 0(r24)
        fsubs f0, f0, f1
        stfs f0, 0(r24)
        lbz r0, 4(r25)
        slwi r0, r0, 3
        lis r12, bmats@ha
        addi r12, r12, bmats@l
        add r23, r12, r0
        fcmpu cr0, f0, f13
        ble bbreak
        mr r3, r31
        lhz r4, 0(r23)
        lbz r5, 2(r23)
        bl playsnd
        b bkeep
bbreak:
        li r0, 1
        lis r12, bstate@ha
        addi r12, r12, bstate@l
        stwx r0, r12, r26
        lis r12, bwrap@ha
        addi r12, r12, bwrap@l
        lwzx r3, r12, r26
        bl 0x%(gim_remove)08X
        mr r3, r31
        lhz r4, 4(r23)
        lbz r5, 6(r23)
        bl playsnd
        lbz r0, 5(r25)
        cmpwi r0, 0
        beq bhide
        mr r3, r28
        bl bnames
        mr r3, r31
        lis r4, blink@ha
        addi r4, r4, blink@l
        bl 0x%(link_find)08X
        cmpwi r3, 0
        beq bhide
        li r4, 1
        bl 0x%(grounds_off)08X
bhide:
        lis r12, bmodels@ha
        addi r12, r12, bmodels@l
        lwzx r22, r12, r26
        cmpwi r22, 0
        beq bnext
        lwz r5, 0x118(r22)
        lis r6, 8
        andc r5, r5, r6
        stw r5, 0x118(r22)
        addi r3, r22, 0xDC
        bl 0x%(isvis)08X
        cmpwi r3, 0
        beq bvis
        mr r3, r22
        li r4, 0
        bl 0x%(remove)08X
bvis:
        addi r3, r22, 0xDC
        li r4, 0
        bl 0x%(setvis)08X
        b bnext
bfollow:
        mr r3, r28
        lbz r4, 6(r25)
        bl bcrack
        b bnext
bkeep:
        mr r3, r28
        mr r4, r28
        bl bcrack
bnext:
        addi r28, r28, 1
        b bloop
bout:
        lmw r22, 0x50(r1)
        lwz r0, 0x84(r1)
        mtlr r0
        addi r1, r1, 0x80
        blr
bcrack:                                 # r3 block, r4 its column's leader: hold the block's crack state
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        slwi r3, r3, 2
        lis r12, bmodels@ha
        addi r12, r12, bmodels@l
        lwzx r3, r12, r3
        cmpwi r3, 0
        beq cout
        slwi r4, r4, 2
        lis r12, bhp@ha
        addi r12, r12, bhp@l
        lfsx f1, r12, r4
        lis r12, bmax@ha
        addi r12, r12, bmax@l
        lfsx f2, r12, r4
        li r5, 0
        lis r12, bconst@ha
        addi r12, r12, bconst@l
        lfs f3, 12(r12)
        fcmpu cr0, f2, f3
        ble cset
        fcmpu cr0, f1, f2
        bge cset
        fsubs f3, f2, f1
        fdivs f3, f3, f2
        lfs f4, 24(r12)
        fmuls f3, f3, f4
        fctiwz f3, f3
        stfd f3, 0x10(r1)
        lwz r5, 0x14(r1)
        cmpwi r5, 0
        bge cmin
        li r5, 0
cmin:
        cmpwi r5, %(stages)d
        blt cmax
        li r5, %(stages1)d
cmax:
        addi r5, r5, 1
cset:
        mulli r5, r5, %(step)d
        addi r5, r5, %(half)d
        lis r0, 0x4330
        stw r0, 0x10(r1)
        stw r5, 0x14(r1)
        lfd f1, 0x10(r1)
        lfd f0, 16(r12)
        fsub f1, f1, f0
        frsp f1, f1
        li r4, 1
        bl 0x%(set_frame)08X
cout:
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
bnames:
        li r0, 10
        divwu r11, r3, r0
        mullw r12, r11, r0
        subf r12, r12, r3
        addi r11, r11, 0x30
        addi r12, r12, 0x30
        lis r10, bname@ha
        addi r10, r10, bname@l
        stb r11, %(name_tens)d(r10)
        stb r12, %(name_ones)d(r10)
        lis r10, blink@ha
        addi r10, r10, blink@l
        stb r11, 1(r10)
        stb r12, 2(r10)
        blr
playsnd:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r30, 0x50(r1)
        mr r31, r3
        mr r30, r4
        mr r3, r5
        bl rand
        add r30, r30, r3
        oris r30, r30, 0x%(row)04X
        lwz r3, 0xFF0(r31)
        cmpwi r3, 0
        beq pout
        lwz r3, 0(r3)
        cmpwi r3, 0
        beq pout
        lwz r3, 0x390(r3)
        cmpwi r3, 0
        beq pout
        mr r5, r30
        addi r4, r1, 0x10
        bl 0x%(play)08X
        addi r3, r1, 0x10
        li r4, 2
        bl 0x%(release)08X
pout:
        lmw r30, 0x50(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
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
           remove=SCENE_REMOVE, setvis=SET_VISIBLE, cycle=CYCLE, mframe=MONSTER_FRAME, fighters_hi=(FIGHTERS + 0x8000) >> 16,
           fighters_lo=FIGHTERS & 0xFFFF, entry=FIGHTER_ENTRY, gim_create=GIM_CREATE, gim_shape=GIM_SHAPE,
           gim_activate=GIM_ACTIVATE, gim_damage=GIM_DAMAGE, gim_remove=GIM_REMOVE, link_find=LINK_FIND,
           grounds_off=GROUNDS_OFF, set_frame=SET_MOTION_FRAME, step=CRACK_STEP, half=CRACK_STEP // 2,
           stages=CRACK_STAGES, stages1=CRACK_STAGES - 1, name_tens=BLOCK_NAME.index('00'), name_ones=BLOCK_NAME.index('00') + 1,
           monsters=MONSTERS, folders=len(FOLDERS), animal_total=sum(o for o, _f in ANIMAL_ODDS), end_table=len(TABLES) - 1, pick_hi=pick >> 16,
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
    # the blocks: constants (2^52 + 2^31 and 2^52 for int -> float, the radius, 0, the stages), a table a biome,
    # the materials' sounds, names and the match's state
    while a.pc % 8:
        a.asm('.word 0')
    a.asm('bconst:')
    for w in (0x43300000, 0x80000000, struct.unpack('>I', struct.pack('>f', BLOCK_RADIUS))[0], 0,
              0x43300000, 0, struct.unpack('>I', struct.pack('>f', float(CRACK_STAGES)))[0], 0):
        a.asm('.word 0x%08X' % w)
    btables, bmats = block_tables()
    a.asm('btables:')
    at = a.addr('btables') + 4 * len(btables)
    for t in btables:
        a.asm('.word 0x%08X' % at)
        at += len(t)
    for t in btables:
        for w in words_of(t):
            a.asm('.word 0x%08X' % w)
    a.asm('bmats:')
    for w in words_of(bmats):
        a.asm('.word 0x%08X' % w)
    a.asm('bname:')
    for w in words_of(BLOCK_NAME.encode() + b'\0'):
        a.asm('.word 0x%08X' % w)
    a.asm('blink:')
    for w in words_of(BLOCK_LINK.encode() + b'\0'):
        a.asm('.word 0x%08X' % w)
    a.asm('brate:')
    for r in LIFE_RATE:
        a.asm('.word 0x%08X' % struct.unpack('>I', struct.pack('>f', r))[0])
    a.asm('bdata:')
    a.asm('.word 0\n.word 0\n.word 0\n.word 0')
    for label in ('bwrap', 'bhp', 'bstate', 'bmodels', 'bmax'):
        a.asm(label + ':')
        for _ in range(MAX_BLOCKS):
            a.asm('.word 0')
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
