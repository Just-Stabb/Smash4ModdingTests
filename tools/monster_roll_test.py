#!/usr/bin/env python3
"""Runs tools/monster_roll_cave.py's code in a patched RPX in unicorn, the game functions it calls
replaced by stubs (the base update returns 0x55; the model lookup returns a fake model per folder
name; the scene / visibility calls record what they're asked; the RNG returns a set sequence).

  python3 tools/monster_roll_test.py PATCHED.rpx

Checks: the setup hook resets and goes on to the setup's second instruction; the update returns
the base update's result; for the stage kinds (normal and Omega): the first update rolls the
animals and shows their folder (flags bit 0x80000, scene add / remove, render visibility), hiding
the others, and hides them again after the game shows them all; at frame 4200 (slow motion too)
the night's monsters are rolled once and shown with the animals; at the cycle's end the animals
alone again; a missing model is skipped; other kinds: nothing. Sounds (a small event table of
the test's own, EVENTS): the biome's table played up to the frame, only shown mobs', a random
variant, on the stage's sound object with a stack handle released after; another biome's (a
hazards-off pick); Omega's; again after the cycle wraps; nothing without a sound object; the
sound object's name hook (NewStage01* -> BattleField_f). The breakable blocks (EVENTS' three): a
gimmick each block on the plane at the first update (sphere at its cell's centre, BLOCK_RADIUS, its
life), damage taken off its life with the material's hit sound, at 0 its hurtbox removed, the break
sound, its collision link switched off, nothing more after; a block behind the plane broken with its
column's plane block; the lives × LIFE_RATE by the number of live fighters (5 / 4 / 2 / 8); none on a
hazards-off pick or on Omega. The game's own ground switch (0x0315EDD8, unstubbed, on a fake link
list of two grounds): 1 takes them out (+0x72 0, +0x163 0), 0 puts them back (+0x72 1, +0x163 1);
the cave passes 1. Every roll of 6000 against the rules in
Python (Ultimate's odds), with the resulting frequencies.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monster_roll_cave as C  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR,  # noqa: E402
                               UC_PPC_REG_FPR1, UC_PPC_REG_MSR)

STAGE = 0x7F004000
MODELS = 0x7F006000        # fake models, 0x200 apart (flags +0x118, handle +0xDC: +0 visible)
REC = 0x7F002000           # +0 rand index, +4 calls to add, +8 remove, +0xC setvis, +0x10 finds
RANDS = 0x7F003000         # the RNG's sequence (words)
FOLDER_CHARS = ''.join(f[4] for f in C.FOLDERS)
N_FOLDERS = len(C.FOLDERS)
SHEEP, COW, CHICKEN = (C.FOLDERS.index('dyr_%s' % c) for c in ('p_animal_sheep_set', 'q_animal_cow_set',
                                                                'r_animal_chicken_set'))


def biome_pick(a):
    """the biome cave's pick word, as the mob cave reads it"""
    return C.biome_select_cave.build()[0].addr('data') + 4


def stub(mu, addr, text):
    a = Asm(addr)
    a.asm(text)
    mu.mem_write(addr, b''.join(struct.pack('>I', w) for w in a.words()))


# sounds: a small event table of our own (written over the cave: its tables are the build's)
EVENTS = {'plains/melee': [[5, 'door_open', 'always'], [10, 'cow_vo', 'cow'], [12, 'zombi_vo', 'zombie'],
                           [20, 'sheep_vo', 'sheep']],
          'birchforest/melee': [[7, 'door_close', 'always']],
          'plains/end': [[3, 'enderman_portal', 'enderman'], [4, 'villager_vo', 'always']],
          'blocks/plains': [dict(x=-55.0, y=15.0, z=0.0, life=12.0, sound='grass', link=True, leader=0),
                            dict(x=5.0, y=5.0, z=-10.0, life=18.0, sound='wood', link=False, leader=2),
                            dict(x=5.0, y=5.0, z=0.0, life=24.0, sound='stone', link=True, leader=2)]}
GIMS = 0x7F00A000          # fake gimmick wrappers, 0x40 apart: +0 the damage the stub returns, +4 removed
BREC = 0x7F00B000          # +0 creates, +4 activates, +8 ground calls, +0xC its list, +0x10 on/off, +0x20 shapes
LINKS = 0x7F00B800         # the ground list the link lookup returns for 'b00' / 'b02'
SOUND_X = 0x7F002300       # stage + 0xFF0 -> SOUND_X; *SOUND_X = SOUND_X + 0x10 (X); X + 0x390 = S
SOUND_S = 0x7F002800
PLAYS = 0x7F002600         # the sound ids played (REC + 0x30 counts them, + 0x34 the releases)
FRAMES = 0x7F00C000        # the crack frames set: +0 count, then (model, frame, apply) 12 bytes each (64, wrapping)


def main():
    mu = machine(sys.argv[1])
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    import json
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(EVENTS, f)
    C.EVENTS = f.name
    a, words, _hooks = C.build()
    os.unlink(f.name)
    mu.mem_write(C.CAVE, b''.join(struct.pack('>I', w) for w in words))
    stub(mu, C.PLAY_SE, """
        lis r7, 0x7F00
        lwz r6, 0x2030(r7)
        slwi r8, r6, 2
        ori r9, r7, 0x2600
        stwx r5, r9, r8
        addi r6, r6, 1
        stw r6, 0x2030(r7)
        stw r3, 0x2038(r7)
        subf r8, r1, r4
        stw r8, 0x203C(r7)
        blr""")
    stub(mu, C.RELEASE, 'lis r7, 0x7F00\nlwz r6, 0x2034(r7)\naddi r6, r6, 1\nstw r6, 0x2034(r7)\nstw r4, 0x2040(r7)\nblr')
    # gimmicks: create -> the next fake wrapper (args checked: 0, 0, 2, 1), shape -> copied to BREC+0x20
    # + 0x28 n, activate counted, damage -> f1 = w+0, remove -> w+4 = 1
    stub(mu, C.GIM_CREATE, """
        lis r7, 0x7F00
        ori r7, r7, 0xB000
        lwz r8, 0(r7)
        addi r9, r8, 1
        stw r9, 0(r7)
        cmpwi r3, 0
        bne bad
        cmpwi r4, 0
        bne bad
        cmpwi r5, 2
        bne bad
        cmpwi r6, 1
        bne bad
        slwi r8, r8, 6
        lis r3, 0x7F00
        ori r3, r3, 0xA000
        add r3, r3, r8
        blr
bad:    li r3, 0
        blr""")
    stub(mu, C.GIM_SHAPE, """
        lis r7, 0x7F00
        ori r7, r7, 0xB000
        subf r8, r7, r7
        lis r9, 0x7F00
        ori r9, r9, 0xA000
        subf r8, r9, r3
        srwi r8, r8, 6
        mulli r8, r8, 0x28
        addi r9, r7, 0x20
        add r9, r9, r8
        li r10, 10
        mtctr r10
        addi r5, r5, -4
        addi r9, r9, -4
cp:     lwzu r11, 4(r5)
        stwu r11, 4(r9)
        bdnz cp
        li r3, 0
        blr""")
    stub(mu, C.GIM_ACTIVATE, 'lis r7, 0x7F00\nori r7, r7, 0xB000\nlwz r6, 4(r7)\naddi r6, r6, 1\nstw r6, 4(r7)\nblr')
    stub(mu, C.GIM_DAMAGE, 'lfs f1, 0(r3)\nblr')
    stub(mu, C.GIM_REMOVE, 'li r6, 1\nstw r6, 4(r3)\nblr')
    # the link lookup: 'b00' / 'b02' -> LINKS (anything else 0); the ground switch recorded
    stub(mu, C.LINK_FIND, """
        lbz r5, 0(r4)
        cmpwi r5, 0x62
        bne no
        lbz r5, 1(r4)
        cmpwi r5, 0x30
        bne no
        lbz r5, 2(r4)
        cmpwi r5, 0x30
        beq yes
        cmpwi r5, 0x32
        beq yes
no:     li r3, 0
        blr
yes:    lis r3, 0x7F00
        ori r3, r3, 0xB800
        blr""")
    stub(mu, C.GROUNDS_OFF, """
        lis r7, 0x7F00
        ori r7, r7, 0xB000
        lwz r6, 8(r7)
        addi r6, r6, 1
        stw r6, 8(r7)
        stw r3, 0xC(r7)
        stw r4, 0x10(r7)
        blr""")
    stub(mu, C.BASE_UPDATE, 'li r3, 0x55\nblr')
    # regeneration: set world matrix -> MATS (+0 count, then the model and 12 floats, 0x34 each, 16
    # kept), the gimmick's battle object back -> BREC + 0x14 counted, + 0x18 its wrapper
    stub(mu, C.SET_MATRIX, """
        lis r7, 0x7F00
        ori r7, r7, 0xD000
        lwz r6, 0(r7)
        andi. r5, r6, 15
        mulli r5, r5, 0x34
        add r5, r5, r7
        stw r3, 4(r5)
        li r8, 12
        mtctr r8
        addi r4, r4, -4
        addi r5, r5, 4
mcopy:  lwzu r8, 4(r4)
        stwu r8, 4(r5)
        bdnz mcopy
        addi r6, r6, 1
        stw r6, 0(r7)
        blr""")
    stub(mu, C.GIM_RESTORE, """
        lis r7, 0x7F00
        ori r7, r7, 0xB000
        lwz r6, 0x14(r7)
        addi r6, r6, 1
        stw r6, 0x14(r7)
        stw r3, 0x18(r7)
        blr""")
    stub(mu, C.SET_MOTION_FRAME, """
        lis r7, 0x7F00
        ori r7, r7, 0xC000
        lwz r6, 0(r7)
        andi. r5, r6, 63
        mulli r5, r5, 12
        add r5, r5, r7
        stw r3, 4(r5)
        stfs f1, 8(r5)
        stw r4, 12(r5)
        addi r6, r6, 1
        stw r6, 0(r7)
        blr""")
    # find: the name's 5th char's place in FOLDER_CHARS picks a model (0x200 apart); the enderman's
    # ('n') missing while REC+0x20 is set
    mu.mem_write(REC + 0x100, (FOLDER_CHARS + 'b').encode() + b'\0')     # 'b': the blocks' (one fake model)
    stub(mu, C.FIND_MODEL, """
        lis r7, 0x7F00
        lwz r6, 0x2010(r7)
        addi r6, r6, 1
        stw r6, 0x2010(r7)
        lbz r5, 4(r4)
        cmpwi r5, 0x6E
        bne look
        lwz r6, 0x2020(r7)
        cmpwi r6, 0
        beq look
        li r3, 0
        blr
look:   ori r6, r7, 0x20FF
        lis r3, 0x7F00
        ori r3, r3, 0x5E00
next:   addi r3, r3, 0x200
        lbzu r8, 1(r6)
        cmpwi r8, 0
        beq miss
        cmpw r8, r5
        bne next
        blr
miss:   li r3, 0
        blr""")
    stub(mu, C.RAND, """
        lis r7, 0x7F00
        lwz r6, 0x2000(r7)
        addi r5, r6, 1
        stw r5, 0x2000(r7)
        slwi r6, r6, 2
        ori r7, r7, 0x3000
        lwzx r6, r7, r6
        divwu r5, r6, r3
        mullw r5, r5, r3
        subf r3, r5, r6
        blr""")
    stub(mu, C.IS_VISIBLE, 'lwz r3, 0(r3)\nblr')
    stub(mu, C.SET_VISIBLE, """
        stw r4, 0(r3)
        lis r7, 0x7F00
        lwz r6, 0x200C(r7)
        addi r6, r6, 1
        stw r6, 0x200C(r7)
        blr""")
    stub(mu, C.SCENE_ADD, 'lis r7, 0x7F00\nlwz r6, 0x2004(r7)\naddi r6, r6, 1\nstw r6, 0x2004(r7)\nblr')
    stub(mu, C.SCENE_REMOVE, 'lis r7, 0x7F00\nlwz r6, 0x2008(r7)\naddi r6, r6, 1\nstw r6, 0x2008(r7)\nblr')
    fails = 0

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))

    def word(addr):
        return struct.unpack('>I', mu.mem_read(addr, 4))[0]

    def setw(addr, v):
        mu.mem_write(addr, struct.pack('>I', v))

    def models(visible):
        for i in range(N_FOLDERS):
            m = MODELS + 0x200 * i
            setw(m + 0x118, 0x020C0000 | (0x80000 if visible else 0))
            setw(m + 0xDC, 1 if visible else 0)

    def rands(seq):
        setw(REC, 0)
        for i, v in enumerate(seq):
            setw(RANDS + 4 * i, v)

    def update(kind=C.KINDS[0], f1=1.0):
        setw(STAGE, kind)
        mu.reg_write(UC_PPC_REG_3, STAGE)
        mu.reg_write(UC_PPC_REG_FPR1, struct.unpack('>Q', struct.pack('>d', f1))[0])
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(a.addr('update'), RET, count=100000)
        return mu.reg_read(UC_PPC_REG_3)

    def shown():
        return [bool(word(MODELS + 0x200 * i + 0x118) & 0x80000) and word(MODELS + 0x200 * i + 0xDC) == 1
                for i in range(N_FOLDERS)]

    def only(*folders):
        return [i in folders for i in range(N_FOLDERS)]

    data = a.addr('data')

    def roll_model(rs):
        """the cave's rules in Python: (animal folders mask, monster folders mask) from a rand sequence
        (each value taken % n, as 0x024F6BE8 does)"""
        it = iter(rs)
        r = next(it) % sum(o for o, _f in C.ANIMAL_ODDS)
        run, day = 0, 0
        for o, f in C.ANIMAL_ODDS:
            run += o
            if r < run:
                day = 1 << f
                break
        return day
    # setup hook
    setw(data, 0x3F800000)
    setw(data + 0xC, 0)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.emu_start(a.addr('reset'), C.SETUP + 4, count=100)
    check('setup: counter 0, new match', (word(data), word(data + 0xC)), (0, 1))
    check('setup: its first instruction made (stwu)', mu.reg_read(UC_PPC_REG_1), 0x7F00F000 - 0x298)
    # first update: the animals: 45 -> chicken (savanna: no sound events in EVENTS)
    setw(biome_pick(a), 2)
    models(True)
    rands([45])
    check('update returns the base update', update(), 0x55)
    check('match start: chicken shown, the rest hidden', shown(), only(CHICKEN))
    rands([99] * 10)
    for _ in range(100):
        update()
    check('no roll in the day', (shown(), word(REC)), (only(CHICKEN), 0))
    models(True)                # the game showing all of the stage's models
    update()
    check('the next update hides them again', shown(), only(CHICKEN))
    # to frame 4200: count 50 -> two; picks 10 -> zombie, then 40 of 60 left -> spider (35 skipped)
    rands([50, 10, 40])
    n = 0
    while word(REC) == 0 and n < 10000:
        update(f1=0.5 if n % 2 else 1.0)
        n += 1
    frame = struct.unpack('>f', mu.mem_read(data, 4))[0]
    check('the monsters rolled at frame 4200', abs(frame - C.MONSTER_FRAME) < 1.01, True)
    check('night: zombie + spider shown, the chicken still there', shown(), only(0, 2, CHICKEN))
    rands([0] * 10)
    for _ in range(50):
        update()
    check('rolled once a night', word(REC), 0)
    # to the cycle's end: the animals again, no roll
    n = 0
    while struct.unpack('>f', mu.mem_read(data, 4))[0] >= C.MONSTER_FRAME and n < 10000:
        update()
        n += 1
    check('cycle end: the chicken alone again, no roll', (shown(), word(REC)), (only(CHICKEN), 0))
    # Omega's kind too; a missing model skipped; other kinds nothing
    setw(data + 0xC, 1)
    rands([5])
    update(kind=0x81)
    check('Omega: sheep', shown(), only(SHEEP))
    setw(REC + 0x20, 1)
    setw(data + 0xC, 1)
    rands([95])
    models(True)
    update()
    check('95 (of 90): sheep again; a missing enderman skipped', shown()[:3] + shown()[4:],
          [i == SHEEP for i in range(N_FOLDERS) if i != 3])
    setw(REC + 0x20, 0)
    setw(data + 0xC, 1)
    before = word(REC + 0x10)
    update(kind=0)
    check('other kind: no lookups, match still new', (word(REC + 0x10), word(data + 0xC)), (before, 1))
    # sounds
    pick = biome_pick(a)
    setw(STAGE + 0xFF0, SOUND_X)
    setw(SOUND_X, SOUND_X + 0x10)
    setw(SOUND_X + 0x10 + 0x390, SOUND_S)

    def plays():
        n = word(REC + 0x30)
        return [word(PLAYS + 4 * i) for i in range(n)]

    def match(kind, biome, animal_roll, rs, frames):
        setw(pick, biome)
        setw(REC + 0x30, 0)
        setw(REC + 0x34, 0)
        setw(data + 0xC, 1)
        setw(data, 0)
        rands([animal_roll] + rs)
        models(True)
        for _ in range(frames):
            update(kind=kind)
        return plays()
    row = C.SOUND_ROW << 16
    tone = C.minecraft_sound.tone_index
    got = match(C.KINDS[0], 0, 75, [0, 4, 0], 31)
    check('plains, cow: the door at 5, the cow (variant 4) at 10; no zombie, no sheep',
          got, [row | tone('door_open')[0], row | tone('cow_vo')[0] + 4])
    check('played on the stage sound object, a handle on the stack, released (2) each',
          (word(REC + 0x38), word(REC + 0x3C) > 0, word(REC + 0x34), word(REC + 0x40)), (SOUND_S, True, 2, 2))
    got = match(C.KINDS[0], 1 + C.biome_select_cave.N_BIOMES, 5, [0, 0], 31)
    check('birch forest (hazards off pick): its own table', got, [row | tone('door_close')[0]])
    got = match(C.KINDS[1], 0, 75, [2, 0], 10)
    check('Omega: its table; the enderman not out by day', got, [row | tone('villager_vo')[0] + 2])
    setw(data, struct.unpack('>I', struct.pack('>f', C.CYCLE - 3))[0])
    setw(data + 0x10, 1)
    setw(REC + 0x30, 0)
    rands([0] * 10)
    for _ in range(10):
        update(kind=C.KINDS[1])
    check('the cycle wrapped: from its start again', plays(), [row | tone('villager_vo')[0]])
    setw(STAGE + 0xFF0, 0)
    got = match(C.KINDS[0], 0, 75, [0] * 10, 31)
    check('no sound object: nothing played', got, [])
    # the sound object's name: NewStage01 (and its biome folders) made Battlefield's
    for name, want in (('NewStage01', C.BATTLEFIELD_NAME), ('NewStage01_forest', C.BATTLEFIELD_NAME),
                       ('BattleField_f', REC + 0x400), ('NewStage0', REC + 0x400)):
        mu.mem_write(REC + 0x400, name.encode() + b'\0')
        mu.reg_write(UC_PPC_REG_4, REC + 0x400)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.emu_start(a.addr('namefix'), C.SOUND_NAME + 4, count=200)
        check('name %r -> %s' % (name, 'BattleField_f' if want == C.BATTLEFIELD_NAME else 'itself'),
              (mu.reg_read(UC_PPC_REG_4), mu.reg_read(UC_PPC_REG_1)), (want, 0x7F00F000 - 0x28))
    # the breakable blocks (EVENTS' three on plains)
    setw(STAGE + 0xFF0, SOUND_X)
    mu.mem_write(BREC, b'\0' * 0x100)
    mu.mem_write(GIMS, b'\0' * 0x100)

    def wf(addr):
        return struct.unpack('>f', mu.mem_read(addr, 4))[0]

    def damage(i, d):
        mu.mem_write(GIMS + 0x40 * i, struct.pack('>f', d))

    def frames():
        """the crack frames set since the last call: [(model, frame, apply)]"""
        n = word(FRAMES)
        setw(FRAMES, 0)
        return [(word(FRAMES + 4 + 12 * k) - block_model, round(wf(FRAMES + 8 + 12 * k), 3), word(FRAMES + 12 + 12 * k))
                for k in range(min(n, 64))]
    for i in range(3):
        damage(i, 0.0)
    block_model = MODELS + 0x200 * N_FOLDERS
    setw(block_model + 0x118, 0x020C0000 | 0x80000)
    setw(block_model + 0xDC, 1)
    all_plays = plays
    tone = C.minecraft_sound.tone_index
    got = match(C.KINDS[0], 0, 75, [0] * 10, 2)
    shapes = [tuple(round(wf(BREC + 0x20 + 0x28 * i + 4 * k), 2) for k in (0, 1, 2, 6)) + (word(BREC + 0x20 + 0x28 * i + 0x20),)
              for i in range(2)]
    check('blocks: a gimmick each plane block, made and activated once', (word(BREC), word(BREC + 4)), (2, 2))
    check('their spheres (x, y, z, radius, kind 0)', shapes,
          [(-55.0, 15.0, 0.0, C.BLOCK_RADIUS, 0), (5.0, 5.0, 0.0, C.BLOCK_RADIUS, 0)])
    bhp, bstate = a.addr('bhp'), a.addr('bstate')
    first_block = tone('block_dmg_soil')[0]

    def plays():                                   # the blocks' only (the plains table's door at 5 too)
        return [p for p in all_plays() if p & 0xFFFF >= first_block]
    check('their lives (12 / 24; the wood block behind follows the stone one)',
          ([wf(bhp + 4 * i) for i in (0, 2)], [word(bstate + 4 * i) for i in range(3)]), ([12.0, 24.0], [0, 2, 0]))
    bmax = a.addr('bmax')
    check('their full lives kept (bmax)', [wf(bmax + 4 * i) for i in (0, 2)], [12.0, 24.0])
    frames()
    update()
    check('cracks: every intact block held at state 0 (no crack: frame %d), the pose applied' % (C.CRACK_STEP // 2),
          frames(), [(0, C.CRACK_STEP // 2, 1)] * 3)
    setw(REC + 0x30, 0)
    rands([3] * 10)
    damage(0, 5.0)
    update()
    damage(0, 0.0)
    check('no fighters yet: lives unscaled; 5 damage: life 7, the grass hit sound', (wf(bhp), plays()),
          (7.0, [row | tone('block_dmg_grass')[0] + 3]))
    mid = C.CRACK_STEP // 2
    # 5 of 12: stage floor(10 x 5 / 12) = 4 -> state 5
    check('5 / 12 damage: the grass block at stage 4 (state 5), the others still uncracked',
          frames(), [(0, 5 * C.CRACK_STEP + mid, 1), (0, mid, 1), (0, mid, 1)])
    update()
    check('no hit the next update: held at the same stage', [f[1] for f in frames()], [5 * C.CRACK_STEP + mid, mid, mid])
    setw(REC + 0x30, 0)
    damage(0, 8.0)
    update()
    damage(0, 0.0)
    check('8 more: broken (hurtbox removed, the grass break sound)', (word(GIMS + 4), plays()),
          (1, [row | tone('block_break_grass')[0] + 3]))
    check('its collision link switched off (0x0315EDD8(list, 1))', (word(BREC + 8), word(BREC + 0xC), word(BREC + 0x10)), (1, LINKS, 1))
    check('its model hidden', (bool(word(block_model + 0x118) & 0x80000), word(block_model + 0xDC)), (False, 0))
    check('the wood block still there', word(bstate + 4), 2)
    frames()
    damage(1, 23.9)
    update()
    damage(1, 0.0)
    check('23.9 / 24 on the stone block: stage 9 (state 10); the wood block behind (before it in the table) an update later',
          frames(), [(0, mid, 1), (0, 10 * C.CRACK_STEP + mid, 1)])
    update()
    check('  then both at stage 9; none for the broken grass block', frames(),
          [(0, 10 * C.CRACK_STEP + mid, 1), (0, 10 * C.CRACK_STEP + mid, 1)])
    setw(REC + 0x30, 0)
    damage(1, 30.0)
    update()
    damage(1, 0.0)
    frames()
    update()
    check('broken (the wood block behind gone with it): no crack frames set any more', frames(), [])
    check('the stone block broken (its link off), the wood block behind it with it',
          (word(GIMS + 0x44), word(BREC + 8), [word(bstate + 4 * i) for i in range(3)], plays()),
          (1, 2, [1, 1, 1], [row | tone('block_break_stone')[0] + 3]))
    setw(REC + 0x30, 0)
    update()
    check('broken blocks: no more damage read, nothing played', plays(), [])
    # regeneration at the new day: order stone (its plane block, row 0) -> wood behind it -> grass (row 1)
    table = 0x7E000000                             # a fake fighter table (8 entries of 0x76B0)
    mu.mem_map(table, 0x50000)
    rg = a.addr('rgdata')
    MATS = 0x7F00D000

    def mats():
        n = word(MATS)
        setw(MATS, 0)
        return [(word(MATS + 4 + 0x34 * k) - block_model, [round(wf(MATS + 8 + 0x34 * k + 4 * j), 3) for j in range(12)])
                for k in range(min(n, 16))]

    def fighter_at(x, y):                          # one live fighter (accessor -> posture at x, y), or none
        setw(0x1035184C, table + 0x100)
        setw(table + 0x100, table + 0x200)
        setw(table + 0x200, table + 0x1000)
        setw(table + 0x208, 1)
        mu.mem_write(table + 0x1000 + 0x1E, bytes([5 if x is not None else 0]))
        setw(table + 0x1000 + 0xC, table + 0x40000)
        setw(table + 0x40000 + 0x18, table + 0x40100)
        mu.mem_write(table + 0x40100 + 0x10, struct.pack('>ff', x or 0.0, y or 0.0))

    def scale_mat(s_, c):
        f = lambda v: round(struct.unpack('>f', struct.pack('>f', v))[0], 3)     # float32, as the cave
        s_ = f(s_)
        return [s_, 0, 0, f(c[0] * (1 - s_)), 0, s_, 0, f(c[1] * (1 - s_)), 0, 0, s_, f(c[2] * (1 - s_))]

    def near(got, want):
        return all(len(g[1]) == len(w[1]) and all(abs(x - y) < 0.002 for x, y in zip(g[1], w[1])) and g[0] == w[0]
                   for g, w in zip(got, want)) and len(got) == len(want)
    fighter_at(-55.0, 12.0)                        # standing in the grass block's cell (x -60..-50, y 10..20)
    breaks = [tone('block_break_%s' % m)[0] for m in ('stone', 'wood', 'grass')]
    mats()
    setw(REC + 0x30, 0)
    setw(BREC + 8, 0)
    setw(data, struct.unpack('>I', struct.pack('>f', C.CYCLE - 0.5))[0])
    adds = word(REC + 4)
    update()                                       # the cycle wraps: a new day
    st = [word(bstate + 4 * i) for i in range(3)]
    check('new day: regenerating; the stone block first (state 3), the break sound, its collision on, its hurtbox back',
          (word(rg + 4), st, [p & 0xFFFF for p in plays()], (word(BREC + 8), word(BREC + 0x10)),
           (word(BREC + 0x14), word(BREC + 0x18) - GIMS)),
          (1, [1, 1, 3], [breaks[0] + 3], (1, 0), (1, 0x40)))
    check('  its life full again, its model added to the scene (the test\'s blocks share one model: the broken'
          ' ones hide it again), grown from %.2f about its centre (5, 5, 0)' % C.REGEN_SCALE0,
          (wf(bhp + 8), word(REC + 4) - adds, mats()), (24.0, 1, [(0, scale_mat(C.REGEN_SCALE0, (5, 5, 0)))]))
    grown, wood = [], None                         # wood: (updates after the stone's start, its state then)
    for n in range(max(C.REGEN_FADE, C.REGEN_GAP)):
        if n + 1 == C.REGEN_GAP:
            setw(REC + 0x30, 0)                    # the sounds of the update the wood block should start on
        if n < C.REGEN_FADE:
            damage(2, 50.0)                        # unbreakable while regenerating
        update()
        if n < C.REGEN_FADE:
            grown.append(mats())
        if n + 1 == C.REGEN_FADE:
            damage(2, 0.0)
            stone = ([word(bstate + 4 * i) for i in (0, 2)], wf(bhp + 8))
        if wood is None and word(bstate + 4) != 1:
            wood = (n + 1, [word(bstate + 4 * i) for i in range(3)], [p & 0xFFFF for p in plays()], word(BREC + 0x14))
    s1 = round(C.REGEN_SCALE0 + (1 - C.REGEN_SCALE0) / C.REGEN_FADE, 3)
    check('  grows a step each update (%.3f, ...), full size (identity) after %d' % (s1, C.REGEN_FADE),
          (near(grown[0][:1], [(0, scale_mat(s1, (5, 5, 0)))]), near(grown[-1][:1], [(0, scale_mat(1.0, (5, 5, 0)))])),
          (True, True))
    check('  then intact (state 0), the 50-damage hits ignored', stone, ([1, 0], 24.0))
    check('  the wood block (behind it) %d updates after it (state 3, its break sound, no hurtbox or collision of its own)'
          % C.REGEN_GAP, wood, (C.REGEN_GAP, [1, 3, 0], [breaks[1] + 3], 1))
    for n in range(C.REGEN_GAP + 20):
        update()
    check('the grass block waits while a fighter is in its cell', (word(bstate), word(rg + 4)), (1, 1))
    check('  the wood block grown and intact (state 2, behind its plane block)', word(bstate + 4), 2)
    fighter_at(-30.0, 0.0)                         # moved away
    update()
    check('  comes back once the fighter is out of it', word(bstate), 3)
    for n in range(C.REGEN_FADE):
        update()
    check('all back: regeneration over, every block intact', (word(rg + 4), [word(bstate + 4 * i) for i in range(3)]),
          (0, [0, 2, 0]))
    setw(REC + 0x30, 0)
    damage(0, 5.0)
    update()
    damage(0, 0.0)
    check('  breakable again (5 damage on the grass block)', round(wf(bhp), 3), 7.0)
    setw(0x1035184C, 0)
    frames()
    mats()
    # the lives × Ultimate's rate by the number of live fighters, once there are any
    for n, rate in ((5, 1.4), (4, 1.3), (2, 1.0), (8, 1.5)):
        setw(0x1035184C, table + 0x100)
        setw(table + 0x100, table + 0x200)
        setw(table + 0x200, table + 0x1000)
        setw(table + 0x208, 8)
        for i in range(8):
            mu.mem_write(table + 0x1000 + C.FIGHTER_ENTRY * i + 0x1E, bytes([5 if i < n else 0]))
        match(C.KINDS[0], 0, 75, [0] * 10, 2)
        update()
        check('%d fighters: lives × %.1f' % (n, rate), [round(wf(bhp + 4 * i), 3) for i in (0, 2)],
              [round(12 * rate, 3), round(24 * rate, 3)])
        check('  full lives × %.1f too, so no crack' % rate,
              ([round(wf(bmax + 4 * i), 3) for i in (0, 2)], sorted(set(f[1] for f in frames()))),
              ([round(12 * rate, 3), round(24 * rate, 3)], [C.CRACK_STEP // 2]))
    setw(0x1035184C, 0)
    mu.mem_write(BREC, b'\0' * 0x10)
    match(C.KINDS[0], C.biome_select_cave.N_BIOMES, 75, [0] * 10, 3)
    check('a hazards-off pick: no blocks', word(BREC), 0)
    match(C.KINDS[1], 0, 75, [0] * 10, 3)
    check('Omega: no blocks', word(BREC), 0)
    setw(pick, 2)                                  # (savanna: no blocks in EVENTS) for the statistics
    # statistics: 6000 nights / matches with a uniform RNG, against the rules in Python
    import random
    rng = random.Random(2)

    def model_night(rs):
        it = iter(rs)
        r = next(it) % 100
        count = 1 if r < C.COUNT_ODDS[0] else 2 if r < C.COUNT_ODDS[0] + C.COUNT_ODDS[1] else 3
        picked = 0
        for _ in range(count):
            left = [k for k in range(4) if not picked >> k & 1]
            total = sum(C.MONSTER_ODDS[k] for k in left)
            r = next(it) % total
            for k in left:
                if r < C.MONSTER_ODDS[k]:
                    picked |= 1 << k
                    break
                r -= C.MONSTER_ODDS[k]
        return picked
    same, nights, days = 0, [0] * 4, [0] * 4
    N = 3000
    for _ in range(N):
        rs = [rng.randrange(1 << 32) for _ in range(4)]
        rands(rs)
        setw(data + 0xC, 0)
        setw(data + 0x10, 0)
        setw(data, struct.unpack('>I', struct.pack('>f', C.MONSTER_FRAME - 0.5))[0])
        models(True)
        update()
        got = word(data + 0x18)
        same += got == model_night(rs) | word(data + 0x14)
        for k in range(4):
            nights[k] += got >> k & 1
        rs = [rng.randrange(1 << 32)]
        rands(rs)
        setw(data + 0xC, 1)
        setw(data, 0)
        update()
        d = word(data + 0x14)
        same += d == roll_model(rs)
        for k, f in enumerate((SHEEP, COW, CHICKEN)):
            days[k] += d >> f & 1
    check('every roll as the rules in Python (%d)' % (2 * N), same, 2 * N)
    print('   nights with zombie / skeleton / spider / enderman:', ['%.2f' % (x / N) for x in nights])
    print('   matches with sheep / cow / chicken:', ['%.2f' % (x / N) for x in days[:3]])
    real_switch(sys.argv[1], check)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


def real_switch(path, check):
    """the game's 0x0315EDD8 itself on a fake link ground list (the collision manager's
    0x02D4BDD0 / 0x02D4BCF8-family calls and the ground's own 0x02D417B8 stubbed): which value takes
    the grounds out of play. A ground (the list's element) has its line set at +0 (+0x72 1 live,
    as 0x02D5ABA8 makes it; +0x38 / +0x34 sub-lists empty, +0x10 none); check counts the failures"""
    mu = machine(path)
    mu.mem_map(0x7E000000, 0x10000)
    stub(mu, 0x02D4BDD0, 'blr')
    stub(mu, 0x02D4BCF8, 'blr')
    stub(mu, 0x02D417B8, 'blr')
    lst, vec, grounds, lines = 0x7E000000, 0x7E000100, 0x7E001000, 0x7E004000
    for k in range(2):
        g, ln = grounds + 0x400 * k, lines + 0x200 * k
        mu.mem_write(vec + 4 * k, struct.pack('>I', g))
        mu.mem_write(g, struct.pack('>I', ln))
        mu.mem_write(ln + 0x72, b'\1')
        mu.mem_write(g + 0x163, b'\1')
    mu.mem_write(lst + 4, struct.pack('>II', vec, vec + 8))

    def switch(v):
        mu.reg_write(UC_PPC_REG_3, lst)
        mu.reg_write(UC_PPC_REG_4, v)
        mu.reg_write(UC_PPC_REG_1, 0x7E00F000)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(C.GROUNDS_OFF, RET, count=100000)
        return [(mu.mem_read(lines + 0x200 * k + 0x72, 1)[0], mu.mem_read(grounds + 0x400 * k + 0x163, 1)[0])
                for k in range(2)]
    for what, v, want in (('1: both grounds out (+0x72 0, +0x163 0)', 1, [(0, 0)] * 2),
                          ('0: both back (+0x72 1, +0x163 1)', 0, [(1, 1)] * 2),
                          ('0 again: stay on', 0, [(1, 1)] * 2)):
        check('the game\'s ground switch, ' + what, switch(v), want)


if __name__ == '__main__':
    main()
