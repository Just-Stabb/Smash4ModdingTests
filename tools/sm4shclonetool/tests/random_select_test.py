#!/usr/bin/env python3
"""The character select's random pool on a patched executable, in unicorn: the refill 0x02FFB610 (the game's own
code, its database / availability calls stubbed: position i = id i, every fighter available, Miis 1-3 left out as
the game's Mii check does), then the remove 0x02FFC5BC for every id 0-0xFF.

  python3 tools/sm4shclonetool/tests/random_select_test.py PATCHED.rpx

Checks: the pool (+0x98, 96 bits) holds every game fighter and every clone with "random" (ids < 96), not the
clones set to false nor any id >= 96; nothing is written past the 12 bytes (+0xA4 on stays as it was) nor below
(+0x94); the function returns with its saved registers; remove clears exactly the bit of each id below the scan
count and touches nothing for the others.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import random_select as RS  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

RET = 0x01000000
OBJ = 0x7E000000
FAILS = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    if not ok:
        FAILS.append(what)


def machine(path):
    x = Rpx(path)
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    spans = []
    for addr, blob in x.memory().items():
        lo, hi = addr & ~0xFFF, (addr + len(blob) + 0xFFF) & ~0xFFF
        spans.append((lo, hi, addr, blob))
    spans.sort()
    merged = []
    for lo, hi, _a, _b in spans:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    for lo, hi in merged:
        mu.mem_map(lo, hi - lo)
    for _lo, _hi, addr, blob in spans:
        mu.mem_write(addr, blob)
    mu.mem_map(RET, 0x1000)
    mu.mem_map(0x7E000000, 0x2000000)
    return mu


def run_refill(path, n_clones, special_from):
    mu = machine(path)
    stubs = {}

    def ret(v):
        mu.reg_write(UC_PPC_REG_3, v & 0xFFFFFFFF)
        mu.reg_write(UC_PPC_REG_PC, mu.reg_read(UC_PPC_REG_LR))

    def pos_id(i):
        return i if i < special_from else 200 + (i - special_from)
    stubs[0x0301CAE8] = lambda: (mu.mem_write(mu.reg_read(UC_PPC_REG_3), b'\0' * 12), ret(mu.reg_read(UC_PPC_REG_3)))
    stubs[0x0309FB24] = lambda: ret(pos_id(mu.reg_read(UC_PPC_REG_4)))
    stubs[0x0301BA44] = lambda: ret(1 if 1 <= mu.reg_read(UC_PPC_REG_3) < 200 else 0)
    stubs[0x0293C40C] = lambda: ret(1)
    stubs[0x030A04C0] = lambda: ret(1 if mu.reg_read(UC_PPC_REG_4) in (1, 2, 3) else 0)
    stubs[0x030A0EFC] = lambda: ret(0)
    scanned = []

    def hook(uc, addr, size, ud):
        if addr in stubs:
            if addr == 0x0309FB24:
                scanned.append(mu.reg_read(UC_PPC_REG_4))
            stubs[addr]()
    mu.hook_add(UC_HOOK_CODE, hook)
    mu.mem_write(OBJ, b'\x5A' * 0x200)
    mu.reg_write(UC_PPC_REG_3, OBJ)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    mu.reg_write(UC_PPC_REG_LR, RET)
    for r in range(23, 32):                      # the saved registers come back
        mu.reg_write(getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % r), 0x1000 + r)
    mu.emu_start(0x02FFB610, RET, count=200000)
    regs = [mu.reg_read(getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % r))
            for r in range(23, 32)]
    pool = struct.unpack('>3I', bytes(mu.mem_read(OBJ + 0x98, 12)))
    return mu, pool, bytes(mu.mem_read(OBJ, 0x98)), bytes(mu.mem_read(OBJ + 0xA4, 0x100)), regs, scanned


def ids_of(pool):
    return {32 * w + b for w in range(3) for b in range(32) if pool[w] >> b & 1}


def main():
    path = sys.argv[1]
    base, rec = X.find_marker(Rpx(path))
    fighters = rec['registry']['fighters']
    n = len(fighters)
    special_from = 59 + n
    count = RS.scan_count(n)
    _mu, pool, below, above, regs, scanned = run_refill(path, n, special_from)
    want = set(range(4, 59)) | {f['ui_id'] for f in fighters if f['ui_id'] < 96 and f.get('random', True)}
    want = {i for i in want if i < count}
    check('%d clones: the refill scans %d entries (positions 0-%d)' % (n, count, count - 1), scanned,
          list(range(count)))
    got = ids_of(pool)
    check('the pool: the game\'s fighters 4-58 and the clones in random (%d), no Mii, no id >= 96'
          % len([i for i in want if i >= 59]), sorted(got), sorted(want))
    off = [f['ui_id'] for f in fighters if f.get('random', True) is False]
    check('clones set to "random": false are not in it (%s)' % off, sorted(got & set(off)), [])
    check('nothing written before +0x98', below, b'\x5A' * 0x98)
    check('nothing written past the 12 bytes (+0xA4 on)', above, b'\x5A' * 0x100)
    check('the function returns with r23-r31 restored', regs, [0x1000 + r for r in range(23, 32)])
    # remove: every id
    mu = machine(path)
    mu.mem_write(OBJ, b'\x5A' * 0x200)
    full = b'\xFF' * 12
    bad = []
    for i in range(0, 0x100):
        mu.mem_write(OBJ + 0x98, full)
        mu.reg_write(UC_PPC_REG_3, OBJ)
        mu.reg_write(UC_PPC_REG_4, i)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(0x02FFC5BC, RET, count=100)
        p = struct.unpack('>3I', bytes(mu.mem_read(OBJ + 0x98, 12)))
        cleared = set(range(96)) - ids_of(p)
        if cleared != ({i} if i < count and i != 0xFF else set()):
            bad.append((i, sorted(cleared)))
        if bytes(mu.mem_read(OBJ + 0xA4, 0x100)) != b'\x5A' * 0x100 or bytes(mu.mem_read(OBJ, 0x98)) != b'\x5A' * 0x98:
            bad.append((i, 'outside'))
    check('remove(id): clears exactly bit id for ids < %d, nothing else and nothing for the rest' % count, bad[:5], [])
    # the count loop's bound
    x = Rpx(path)
    check('the count of picks left covers the same %d bits' % count, x.r32(RS.COUNT_LOOP),
          RS.one(RS.COUNT_LOOP, 'li r11, %d' % count))
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
