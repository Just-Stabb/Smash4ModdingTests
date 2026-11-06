#!/usr/bin/env python3
"""Unicorn test of tools/training_cpu_patch.py: runs the game's own code for the Training menu's "No. of CPUs"
item in a (patched) cross_f.rpx:

  python3 tools/training_cpu_test.py PATCHED.rpx [ORIGINAL.rpx]

The item's set-up (0x0268A500: the value's address, minimum, limit), then left (0x0268A620-0x0268A648) and right
(0x0268A6A8-0x0268A6CC) from every value, on a fake menu object; and the settings reset (0x02687D8C) for the
default. Patched: left 1 -> 0 -> 3 -> 2, right 3 -> 0 -> 1, default 1. With ORIGINAL, the same code there
must give the vanilla 1..3 (the harness reads the game's behaviour, not the patch's idea of it).
"""
import struct
import sys
import os

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch  # noqa: E402

R = {n: getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % n) for n in range(32)}
OBJ = 0x30000000
FAILS = []


def load(path):
    d, _shoff, _ent, secs = rpx_patch.load(path)
    return {s[3]: bytes(rpx_patch.section_data(d, s)) for s in secs if s[1] == 1 and s[3] and s[3] < 0x10000000}


def machine(secs):
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    uc.mem_map(0x02000000, 0x03000000)
    for base, data in secs.items():
        uc.mem_write(base, data)
    uc.mem_map(OBJ, 0x10000)
    return uc


def step(secs, value, start, end):
    """the item's set-up, then the left / right block on `value`; the stored value"""
    uc = machine(secs)
    uc.mem_write(OBJ + 0x118, struct.pack('>i', value))
    uc.reg_write(R[28], OBJ)
    uc.emu_start(0x0268A500, 0x0268A50C)
    assert uc.reg_read(R[31]) == OBJ + 0x118
    uc.emu_start(start, end)
    return struct.unpack('>i', uc.mem_read(OBJ + 0x118, 4))[0]


def left(secs, v):
    return step(secs, v, 0x0268A620, 0x0268A648)


def right(secs, v):
    return step(secs, v, 0x0268A6A8, 0x0268A6CC)


def default(secs):
    uc = machine(secs)
    uc.mem_write(OBJ + 0x110, bytes(0x40))
    uc.reg_write(R[3], OBJ + 0x110)
    uc.emu_start(0x02687D8C, 0x02687DA0)
    return struct.unpack('>i', uc.mem_read(OBJ + 0x118, 4))[0]


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def cycle(secs, lo, hi):
    """every value's left / right as a wrapping range lo..hi"""
    ok = True
    for v in range(lo, hi + 1):
        ok &= left(secs, v) == (v - 1 if v > lo else hi)
        ok &= right(secs, v) == (v + 1 if v < hi else lo)
    return ok


def main():
    patched = load(sys.argv[1])
    check(cycle(patched, 0, 3), 'patched: 0..3, wrapping both ways')
    check([left(patched, 1), left(patched, 0), right(patched, 3), right(patched, 0)] == [0, 3, 0, 1],
          'patched: left 1 -> 0, 0 -> 3; right 3 -> 0, 0 -> 1')
    check(default(patched) == 1, 'patched: the reset still sets 1')
    if len(sys.argv) > 2:
        orig = load(sys.argv[2])
        check(cycle(orig, 1, 3), 'original: 1..3 (the harness reads the game)')
        check(default(orig) == 1, 'original: default 1')
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
