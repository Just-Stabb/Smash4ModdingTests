#!/usr/bin/env python3
"""Runs tools/biome_select_cave.py's code in a patched RPX in unicorn: the stage path function
(0x02D1FDA0) for kind 0x80 with fake controllers (the pad slot array filled in), sprintf stubbed
to record its arguments, the time base stubbed (unicorn's mftb is replaced by loads of a fake
time the test sets).

  python3 tools/biome_select_test.py PATCHED.rpx

Checks: each button combination picks its biome's folder; the pick is kept within WINDOW and
redone after; L not held: random, every biome reachable; invalid pads (+0x87 0) and the dummy slot
are ignored; kind 0x81 (Omega) and the game's kinds keep their folders.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import biome_select_cave as C  # noqa: E402
from stage_slot_test import machine, cstr  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4  # noqa: E402

SPRINTF = 0x04ADA3F4
REC = 0x7F002000            # sprintf stub: +0 fmt, +4 arg
BUF = 0x7F003000
TIME = 0x00002100           # fake time base: +0 upper, +4 lower (low memory: lwz rD, TIME(0))
STATUS = 0x7F005000         # fake status objects, 0x100 apart; wrappers at 0x7F008000


def main():
    mu = machine(sys.argv[1])
    a, words, _hooks = C.build()
    # sprintf: record format and argument
    from ppcasm import Asm
    st = Asm(SPRINTF)
    st.asm("""
        lis r7, 0x7F00
        stw r4, 0x2000(r7)
        stw r5, 0x2004(r7)
        blr""")
    mu.mem_write(SPRINTF, b''.join(struct.pack('>I', w) for w in st.words()))
    # the time base reads (mftbu / mftb) -> loads of the fake time
    code = bytearray(mu.mem_read(C.CAVE, 4 * len(words)))
    for i in range(len(words)):
        w = struct.unpack('>I', code[4 * i:4 * i + 4])[0]
        if (w & 0xFC0007FE) == (31 << 26 | 371 << 1):
            rd = (w >> 21) & 31
            off = 0 if ((w >> 11) & 0x3FF) == ((269 & 31) << 5 | 269 >> 5) else 4
            code[4 * i:4 * i + 4] = struct.pack('>I', (32 << 26) | (rd << 21) | (0 << 16) | ((TIME + off) & 0xFFFF))
    mu.mem_write(C.CAVE, bytes(code))
    mu.mem_map(0, 0x10000)
    try:                                    # the slot array is in .bss (not in the file)
        mu.mem_read(C.PADS, 4)
    except Exception:
        mu.mem_map(C.PADS & ~0xFFF, 0x1000)
    fails = 0

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))

    def pads(held, valid=True, slot=9):
        for i in range(26):
            mu.mem_write(C.PADS + 4 * i, struct.pack('>I', 0))
        if held is None:
            return
        w, s = 0x7F008000 + 0x10 * slot, STATUS + 0x100 * slot
        mu.mem_write(w + 8, struct.pack('>I', s))
        mu.mem_write(s, struct.pack('>I', held))
        mu.mem_write(s + 0x87, bytes([1 if valid else 0]))
        mu.mem_write(C.PADS + 4 * slot, struct.pack('>I', w))

    def settime(t):
        mu.mem_write(TIME, struct.pack('>II', t >> 32, t & 0xFFFFFFFF))

    def path(kind=0x80, site=0x0315805C):
        """the path function called from a call site (the setting build 0x0315805C, the prefetch
        0x02AB83A0), as the game does"""
        mu.mem_write(REC, b'\0' * 8)
        mu.reg_write(UC_PPC_REG_3, BUF)
        mu.reg_write(UC_PPC_REG_4, kind)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.emu_start(site, site + 4, count=10000)
        return cstr(mu, struct.unpack('>I', mu.mem_read(REC + 4, 4))[0])

    t = 1 << 40
    step = (C.WINDOW + 5) << 24
    folders = [f for _b, f in C.BIOMES]
    for held, want in ((C.L, 0), (C.L | C.R, 1), (C.L | C.STICK_UP, 2), (C.L | C.STICK_RIGHT, 3),
                       (C.L | C.STICK_DOWN, 4), (C.L | C.STICK_LEFT, 5), (C.L | C.DPAD_UP | C.A, 2),
                       (C.L | C.A, 0), (C.L | C.R | C.STICK_UP, 1)):
        t += step
        settime(t)
        pads(held)
        check('held 0x%X' % held, path(), folders[want])
    t += step
    settime(t)
    pads(C.L | C.R)
    first = path()
    pads(C.L | C.STICK_LEFT)
    settime(t + (2 << 24))
    check('kept within the window', path(), first)
    settime(t + (2 << 24) + step)
    check('picked again after it', path(), folders[5])
    pads(C.L | C.R, valid=False)
    t += 10 * step
    settime(t)
    got = path()
    check('an invalid pad is ignored (random)', got in folders, True)
    for slot in (0, 2, 16):
        t += step
        settime(t)
        pads(C.L | C.STICK_DOWN, slot=slot)
        check('slot %d read' % slot, path(), folders[4])
    seen = set()
    for i in range(400):
        t += step + i * 977
        settime(t)
        pads(None)
        seen.add(path())
    want_last = folders.index(path(site=0x02AB83A0))
    check('the last random pick is kept for the prefetch', folders[want_last] in folders, True)
    check('random reaches every biome', sorted(seen), sorted(folders))
    t += step
    settime(t)
    pads(C.L | C.STICK_UP)
    check('the prefetch reuses the last pick', path(site=0x02AB83A0), folders[want_last])
    check('the setting build then picks', path(), folders[2])
    check('the prefetch reuses it', path(site=0x02AB83A0), folders[2])
    check('Omega (0x81) keeps its folder', path(0x81), 'NewStage01')
    check('Battlefield (0) keeps its folder', path(0), 'BattleField_f')
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
