#!/usr/bin/env python3
"""Runs tools/monster_roll_cave.py's code in a patched RPX in unicorn, the game functions it calls
replaced by stubs (the base update returns 0x55; the model lookup returns a fake model per folder
name; the scene / visibility calls record what they're asked; the RNG returns a set sequence).

  python3 tools/monster_roll_test.py PATCHED.rpx

Checks: the setup hook resets and goes on to the setup's second instruction; the update returns
the base update's result; for the stage kinds (normal and Omega): the first update rolls the
animals and shows their folder (flags bit 0x80000, scene add / remove, render visibility), hiding
the others; at frame 4200 (slow motion too) the night's monsters are rolled once and shown; at the
cycle's end the animals' folder again; a missing model is skipped; other kinds: nothing. Every
roll of 6000 against the rules in Python (Ultimate's odds), with the resulting frequencies.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monster_roll_cave as C  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_FPR1,  # noqa: E402
                               UC_PPC_REG_MSR)

STAGE = 0x7F004000
MODELS = 0x7F006000        # fake models, 0x200 apart (flags +0x118, handle +0xDC: +0 visible)
REC = 0x7F002000           # +0 rand index, +4 calls to add, +8 remove, +0xC setvis, +0x10 finds
RANDS = 0x7F003000         # the RNG's sequence (words)


def stub(mu, addr, text):
    a = Asm(addr)
    a.asm(text)
    mu.mem_write(addr, b''.join(struct.pack('>I', w) for w in a.words()))


def main():
    mu = machine(sys.argv[1])
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    a, _words, _hooks = C.build()
    stub(mu, C.BASE_UPDATE, 'li r3, 0x55\nblr')
    # find: compare the name's 5th char (h / f / g / n) to pick a model; 'n' -> missing when REC+0x20 set
    stub(mu, C.FIND_MODEL, """
        lis r7, 0x7F00
        lwz r6, 0x2010(r7)
        addi r6, r6, 1
        stw r6, 0x2010(r7)
        lbz r5, 4(r4)
        lis r3, 0x7F00
        ori r3, r3, 0x6000
        cmpwi r5, 0x68
        beq f0
        cmpwi r5, 0x66
        beq f1
        cmpwi r5, 0x67
        beq f2
        lwz r6, 0x2020(r7)
        cmpwi r6, 0
        beq f3
        li r3, 0
        blr
f3:     addi r3, r3, 0x600
        blr
f2:     addi r3, r3, 0x400
        blr
f1:     addi r3, r3, 0x200
f0:     blr""")
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
        for i in range(4):
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
                for i in range(4)]

    data = a.addr('data')

    def roll_model(rs):
        """the cave's rules in Python: (animal folders mask, monster folders mask) from a rand sequence
        (each value taken % n, as 0x024F6BE8 does)"""
        it = iter(rs)
        r = next(it) % 100
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
    # first update: the animals: 45 -> chicken (folder 2)
    models(True)
    rands([45])
    check('update returns the base update', update(), 0x55)
    check('match start: chicken (folder 2) shown, the rest hidden', shown(), [False, False, True, False])
    rands([99] * 10)
    for _ in range(100):
        update()
    check('no roll in the day', (shown(), word(REC)), ([False, False, True, False], 0))
    # to frame 4200: count 50 -> two; picks 10 -> zombie, then 40 of 60 left -> spider (35 skipped)
    rands([50, 10, 40])
    n = 0
    while word(REC) == 0 and n < 10000:
        update(f1=0.5 if n % 2 else 1.0)
        n += 1
    frame = struct.unpack('>f', mu.mem_read(data, 4))[0]
    check('the monsters rolled at frame 4200', abs(frame - C.MONSTER_FRAME) < 1.01, True)
    check('night: zombie + spider shown', shown(), [True, False, True, False])
    rands([0] * 10)
    for _ in range(50):
        update()
    check('rolled once a night', word(REC), 0)
    # to the cycle's end: the animals again, no roll
    n = 0
    while struct.unpack('>f', mu.mem_read(data, 4))[0] >= C.MONSTER_FRAME and n < 10000:
        update()
        n += 1
    check('cycle end: chicken again, no roll', (shown(), word(REC)), ([False, False, True, False], 0))
    # Omega's kind too; a missing model skipped; other kinds nothing
    setw(data + 0xC, 1)
    rands([5])
    update(kind=0x81)
    check('Omega: sheep (folder 0)', shown(), [True, False, False, False])
    setw(REC + 0x20, 1)
    setw(data + 0xC, 1)
    rands([95])
    models(True)
    update()
    check('none (95), a missing enderman skipped', shown()[:3], [False, False, False])
    setw(REC + 0x20, 0)
    setw(data + 0xC, 1)
    before = word(REC + 0x10)
    update(kind=0)
    check('other kind: no lookups, match still new', (word(REC + 0x10), word(data + 0xC)), (before, 1))
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
        same += got == model_night(rs)
        for k in range(4):
            nights[k] += got >> k & 1
        rs = [rng.randrange(1 << 32)]
        rands(rs)
        setw(data + 0xC, 1)
        setw(data, 0)
        update()
        d = word(data + 0x14)
        same += d == roll_model(rs)
        for k in range(4):
            days[k] += d >> k & 1
    check('every roll as the rules in Python (%d)' % (2 * N), same, 2 * N)
    print('   nights with zombie / skeleton / spider / enderman:', ['%.2f' % (x / N) for x in nights])
    print('   matches with sheep / cow / chicken (folders 0 / 1 / 2):', ['%.2f' % (x / N) for x in days[:3]])
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
