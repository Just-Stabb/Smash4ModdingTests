#!/usr/bin/env python3
"""Runs tools/trait_badge_cave.py's code in a patched RPX in unicorn: the damage panel's per-frame
update (through its vtable entry, as the UI manager calls it) with a fake panel, fake fighters and
stubbed flx runtime calls.

  python3 tools/trait_badge_test.py PATCHED.rpx

Checks: the vtable entry is the cave; the original update runs once with the panel, its return
value kept; Kirby with a trait: the badge shown at the trait's frame, the panel's alpha copied, the
goto only when the trait changes; Kirby without a copy, another fighter, a wrong marker: hidden;
an empty slot or a panel clip without trait_mc: untouched; the name interned once.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trait_badge_cave as C  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR  # noqa: E402
from ppcasm import Asm  # noqa: E402

P = 0x7E000000                  # the panel (8 slots of 0x30C0 from +0xC0)
FM = 0x7E100000                 # fighter manager; entries' FE at FM + 0x1000 + 0x2000 * e
OBJS = 0x7E200000               # battle objects (0x100 each) and their accessor / WorkModule / ints
CLIPS = 0x7E300000              # panel clips (0x100 each): +0 the element find returns (0 = none)
ELEMS = 0x7E400000              # elements (0x100 each)
REC = 0x7F001000                # stub records: +0 update calls, +4 its r3, +8 intern calls,
                                # +0xC goto calls, +0x10 last goto (elem), +0x14 last goto frame,
ATOM = 0x7F002000               # the interned name
RETVAL = 0x1234ABCD


def stub(mu, addr, src):
    a = Asm(addr)
    a.asm(src)
    mu.mem_write(addr, b''.join(struct.pack('>I', w) for w in a.words()))


def main():
    mu = machine(sys.argv[1])
    mu.mem_map(0x7E000000, 0x500000)
    fails = 0

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))

    def w32(a, v):
        mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))

    def r32(a):
        return struct.unpack('>I', mu.mem_read(a, 4))[0]

    # stubs: the original update counts its calls and returns RETVAL; intern returns ATOM; find
    # returns the clip's +0; goto sets +0x3C to frame - 1 and records
    stub(mu, C.UPDATE, """
        lis r7, 0x7F00
        lwz r6, 0x1000(r7)
        addi r6, r6, 1
        stw r6, 0x1000(r7)
        stw r3, 0x1004(r7)
        lis r3, 0x%04X
        ori r3, r3, 0x%04X
        blr""" % (RETVAL >> 16, RETVAL & 0xFFFF))
    stub(mu, C.INTERN, """
        lis r7, 0x7F00
        lwz r6, 0x1008(r7)
        addi r6, r6, 1
        stw r6, 0x1008(r7)
        lis r3, 0x7F00
        ori r3, r3, 0x2000
        blr""")
    stub(mu, C.FIND_CHILD, """
        lwz r5, 0(r4)
        lis r6, 0x7F00
        ori r6, r6, 0x2000
        cmpw r5, r6
        bne none
        lwz r3, 0(r3)
        blr
none:   li r3, 0
        blr""")
    # the game's own visible / alpha setters (they store +0xE8 bit 0x4000 / +0x74, then tail-call
    # 0x03402B24, stubbed); visible calls counted by element
    stub(mu, 0x03402B24, 'blr')
    vis_calls = {}
    mu.hook_add(UC_HOOK_CODE, lambda m, addr, size, ud: vis_calls.__setitem__(
        m.reg_read(UC_PPC_REG_3), vis_calls.get(m.reg_read(UC_PPC_REG_3), 0) + 1), begin=C.SET_VISIBLE, end=C.SET_VISIBLE)
    stub(mu, C.GOTO_FRAME, """
        addi r5, r4, -1
        sth r5, 0x3C(r3)
        li r5, 0
        sth r5, 0x9C(r3)
        lis r7, 0x7F00
        lwz r6, 0x100C(r7)
        addi r6, r6, 1
        stw r6, 0x100C(r7)
        stw r3, 0x1010(r7)
        stw r4, 0x1014(r7)
        blr""")

    check('vtable +0x3C is the cave', r32(C.VTABLE_UPDATE), C.CAVE)

    w32(C.ATOM_POOL, 0x7F003000)                # the game's string pool (set at boot)
    # FM (pointer at FIGHTER_MANAGER): count 8, FE for entries 0-7
    w32(C.FIGHTER_MANAGER, FM)
    w32(FM + 0x18, 8)

    def fighter(entry, kind, marker):
        fe = FM + 0x1000 + 0x2000 * entry
        w32(FM + 0x24 + 4 * entry, fe)
        w32(fe + 0xDB4, 1)
        mu.mem_write(fe + 0x14E9, b'\0')
        obj = OBJS + 0x1000 * entry
        w32(fe + 0xDC0, obj)
        w32(obj + 4, kind)
        acc, wm, cat, cat0, ints = obj + 0x100, obj + 0x200, obj + 0x300, obj + 0x400, obj + 0x500
        w32(obj + 0xC, acc)
        w32(acc + 0x28, wm)
        w32(wm + 8, cat)
        w32(cat, cat0)
        w32(cat0 + 8, 0x200)
        w32(cat0 + 0xC, ints)
        w32(ints + 4 * 0x8E, marker)

    def slot(i, entry, kind, elem=True, empty=False):
        s = P + 0xC0 + C.SLOT_SIZE * i
        mu.mem_write(s, struct.pack('>h', entry))
        mu.mem_write(s + 8, struct.pack('>h', 2 if empty else 0))
        mu.mem_write(s + 0xA, struct.pack('>b', kind))
        clip, e, sib = CLIPS + 0x100 * i, ELEMS + 0x100 * i, ELEMS + 0x80000 + 0x100 * i
        w32(s + 0x5C, clip)
        w32(clip, e if elem else 0)
        w32(s + 0x60, sib)
        mu.mem_write(sib + 0x74, bytes([0x40 + i]))
        mu.mem_write(e, b'\0' * 0x100)
        w32(e + 0xE8, 0x4000)                   # visible, as placed
        return e

    KI = 0x4B490000
    elems = [slot(0, 0, 8), slot(1, 1, 8), slot(2, 2, 1), slot(3, 3, 8, empty=True),
             slot(4, 4, 8, elem=False), slot(5, 5, 8), slot(6, 6, 8), slot(7, 7, 8)]
    fighter(0, 8, KI | 2 << 8 | 1)              # Rush (stat profile 1)
    fighter(1, 8, KI)                           # no copy
    fighter(2, 1, KI | 3 << 8)                  # Mario (even with a marker)
    fighter(3, 8, KI | 4 << 8)
    fighter(4, 8, KI | 4 << 8)
    fighter(5, 8, KI | 6 << 8)                  # Technical
    fighter(6, 8, 0x12340400)                   # no magic
    fighter(7, 8, KI | 8 << 8 | 0x18)           # trait 8: none such

    def update():
        mu.reg_write(UC_PPC_REG_3, P)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(r32(C.VTABLE_UPDATE), RET, count=200000)
        return mu.reg_read(UC_PPC_REG_3)

    def state(e):
        return (bool(r32(e + 0xE8) & 0x4000), struct.unpack('>H', mu.mem_read(e + 0x3C, 2))[0] + 1,
                vis_calls.get(e, 0), mu.mem_read(e + 0x74, 1)[0])

    got = update()
    check('the original update ran once with the panel, its value returned',
          (r32(REC), r32(REC + 4), got), (1, P, RETVAL))
    check('Kirby, Rush: shown at frame 2, the panel alpha (0x40)', state(elems[0]), (True, 2, 1, 0x40))
    check('stopped there', struct.unpack('>H', mu.mem_read(elems[0] + 0x9C, 2))[0], 1)
    check('Kirby without a copy: hidden', state(elems[1])[0], False)
    check('Mario: hidden', state(elems[2])[0], False)
    check('an empty slot: untouched', state(elems[3]), (True, 1, 0, 0))
    check('a clip without trait_mc: untouched', state(elems[4]), (True, 1, 0, 0))
    check('Kirby, Technical: frame 6', state(elems[5])[:2], (True, 6))
    check('no KI marker: hidden', state(elems[6])[0], False)
    check('trait 8 (none such): hidden', state(elems[7])[0], False)
    gotos = r32(REC + 0xC)
    update()
    check('the same traits next frame: no goto', r32(REC + 0xC), gotos)
    check('the name interned once', r32(REC + 8), 1)
    fighter(0, 8, KI | 4 << 8 | 0x8)            # Rush -> Strike
    update()
    check('Rush -> Strike: one goto, frame 4', (r32(REC + 0xC) - gotos, state(elems[0])[:2]), (1, (True, 4)))
    fighter(5, 8, KI | 7 << 8)                  # Technical -> Barrage (the last trait)
    update()
    check('Technical -> Barrage: frame 7', state(elems[5])[:2], (True, 7))
    fighter(0, 8, KI)
    update()
    check('the copy lost: hidden', state(elems[0])[0], False)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
