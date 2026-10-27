#!/usr/bin/env python3
"""Runs copy_custom_cave.py's spawner caves (SPAWNERS: every copy spawner reading the owner's custom
slot) in unicorn, from a patched cross_f.rpx: each hook's replaced load of the owner's custom slot
(int 0x10000048) and the cave it branches to, with fake owners: the fighter itself (its own slot),
Kirby without a copy (his own slot) and Kirby with a copy (the copied slot, int 0x1000009F).

  python3 tools/copy_custom_cave_test.py PATCHED.rpx
"""
import os
import struct
import sys

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import UC_PPC_REG_0, UC_PPC_REG_PC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch as R  # noqa: E402
import copy_custom_cave as C  # noqa: E402

DATA = 0x20000000
OWNER, WM, INTS = DATA, DATA + 0x8000, DATA + 0x9000


def reg(n):
    return UC_PPC_REG_0 + n


def run(text, base, hook, dst, ints, owner, kind, own_slot, copy_kind, copy_slot, scratch):
    mu = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    lo = base & ~0xFFF
    mu.mem_map(lo, (base + len(text) - lo + 0xFFF) & ~0xFFF)
    mu.mem_write(base, bytes(text))
    mu.mem_map(DATA, 0x10000)
    mu.mem_write(OWNER + 0x726C, struct.pack('>I', WM))
    mu.mem_write(WM + 0x18, struct.pack('>I', kind))
    mu.mem_write(INTS + 0x120, struct.pack('>i', own_slot))
    mu.mem_write(INTS + 0x290, struct.pack('>i', copy_kind))
    mu.mem_write(INTS + 0x27C, struct.pack('>i', copy_slot))
    mu.reg_write(reg(ints), INTS)
    mu.reg_write(reg(owner), OWNER)
    if dst != ints:
        mu.reg_write(reg(dst), 0x7777)
    # every other register holds a marker: only DST and SCRATCH may change
    keep = {n: 0x5000 + n for n in range(3, 32) if n not in (dst, ints, owner, scratch)}
    for n, v in keep.items():
        mu.reg_write(reg(n), v)
    mu.emu_start(hook, hook + 4, count=64)
    assert mu.reg_read(UC_PPC_REG_PC) == hook + 4
    assert all(mu.reg_read(reg(n)) == v for n, v in keep.items()), 'a register other than DST / SCRATCH changed'
    assert dst == ints or mu.reg_read(reg(ints)) == INTS
    assert mu.reg_read(reg(owner)) == OWNER
    return mu.reg_read(reg(dst))


def main():
    d, _shoff, _ent, secs = R.load(sys.argv[1])
    sec = secs[2]
    base, text = sec[3], R.section_data(d, sec)
    fails = 0
    for hook, dst, ints, owner, scratch, _wkind, name in C.SPAWNERS:
        k = 0x10       # the copied fighter's kind isn't checked, only Kirby (8) and "has a copy" (< 0x3A)
        cases = [
            ('the fighter itself, slot 2', 0x0F, 2, 0x10, 0, 2),       # int 0xA4 means nothing for it
            ('Kirby, no copy, own slot 1', 8, 1, -1, 3, 1),
            ('Kirby with a copy, slot 3', 8, 1, k, 3, 3),
            ('Kirby with a copy, slot 0', 8, 2, k, 0, 0),
        ]
        for what, kind, own, ck, cs, want in cases:
            got = run(text, base, hook, dst, ints, owner, kind, own, ck, cs, scratch)
            ok = got == want
            fails += not ok
            print('%s %08x %-26s %-28s -> %d (want %d)' % ('ok  ' if ok else 'FAIL', hook, name, what, got, want))
    print('%d failure(s)' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
