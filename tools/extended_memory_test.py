#!/usr/bin/env python3
"""Test tools/extended_memory.py: its executable run in unicorn against its base (exe_v11), and its graphic pack's
rules.txt against Cemu's [RAM] rules.

  python3 tools/extended_memory_test.py PATCHED.rpx BASE.rpx

Checks: at the arena set-up's getter call (0x03374F38, r29 = MEM2's free bytes) the patched executable returns the
base's total for a normal MEM2 (as Cemu reports it without the pack, ~1007 MiB) and below THRESHOLD, and the total
+ (ANIM_EXT - the base's animation size) from THRESHOLD up; the animation getter calls (0x03326310 / 0x03326320)
then return the base's size, or ANIM_EXT after an extended set-up; the arena's slack (its total minus the getters'
blocks) is the base's in both; the default heap with the pack is larger than without; every other register as the
base leaves it at the call's return (but r11 / r12, volatile); the pack's mapping: MEM2's base, 0x1000-aligned,
past the default end, below the overlay arena (0xA0000000, the next MMU range) and 0x80000000, version >= 6.
"""
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extended_memory as X  # noqa: E402
import effect_heap_patch as P  # noqa: E402
from kind_expand_test import Emu, REGS, STACK  # noqa: E402
import unicorn.ppc_const as PC  # noqa: E402

fails = 0
NORMAL_FREE = 1056546712 - 0x10      # the user's Cemu log: MEM_ARENA_2 freeBytes=1056546712 (~1007 MiB)
EXT_FREE = NORMAL_FREE + (X.MEM2_END - 0x50000000)
GETTERS = (0x02010AF0, 0x02010AF8, 0x02010B00, 0x02010B08, 0x02010B10, 0x02010B18, 0x02010B20)


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def call(e, at, regs):
    """run the bl at `at` (and what it calls) to its return at + 4: the registers after"""
    for i in range(32):
        e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
    e.mu.reg_write(REGS[1], STACK + 0xF0000)
    for r, v in regs.items():
        e.mu.reg_write(REGS[r], v)
    e.mu.reg_write(PC.UC_PPC_REG_LR, 0x4C4C4C4C)
    e.mu.emu_start(at, at + 4, count=200)
    check('0x%08X returns to 0x%08X' % (at, at + 4), e.mu.reg_read(PC.UC_PPC_REG_PC), at + 4)
    return [e.mu.reg_read(REGS[i]) for i in range(32)]


def main():
    new, old = sys.argv[1:3]
    E1, E0 = Emu(new), Emu(old)
    total0, bases = X.base_sizes(E0)
    check('the base is exe_v11\'s heap sizes (total 0x36600000; animation 46, effect 60, resource 444 MiB)',
          (total0, bases), (0x36600000, {'animation': 0x2E00000, 'effect': 0x3C00000, 'resource': 0x1BC00000}))
    slack0 = total0 - sum(X.lis_value(E0.w(g)) for g in GETTERS)
    ext_total = X.ext_total(total0, bases)
    exts = {n: e for n, _g, _c, e in X.POOLS}
    flag = X.build(total0, bases)[1]['flag']
    for name, free, extended in (('normal MEM2', NORMAL_FREE, False),
                                 ('just below the threshold', X.THRESHOLD - 0x1000, False),
                                 ('at the threshold', X.THRESHOLD, True),
                                 ('the pack\'s MEM2', EXT_FREE, True),
                                 ('normal again (a fresh boot)', NORMAL_FREE, False)):
        if name.startswith('normal'):
            E1.setw(flag, 0)                                     # a boot starts with the cave's zero
        want_total = ext_total if extended else total0
        r1 = call(E1, X.HOOK_TOTAL, {29: free})
        r0 = call(E0, X.HOOK_TOTAL, {29: free})
        check('%s (free 0x%08X): arena total 0x%08X' % (name, free, want_total), r1[3], want_total)
        check('%s: registers but r3 / r11 / r12 as the base leaves them' % name,
              [i for i in range(32) if i not in (3, 11, 12) and r1[i] != r0[i]], [])
        sizes = {}
        for pool, _g, calls, ext in X.POOLS:
            want = ext if extended else bases[pool]
            sizes[pool] = want
            for at in calls:
                a1, a0 = call(E1, at, {}), call(E0, at, {})
                check('%s: %s heap at 0x%08X = 0x%08X' % (name, pool, at, want), a1[3], want)
                check('%s: 0x%08X, registers but r3 / r11 / r12 as the base' % (name, at),
                      [i for i in range(32) if i not in (3, 11, 12) and a1[i] != a0[i]], [])
        blocks = sum(X.lis_value(E0.w(g)) for g in GETTERS) + sum(sizes[p] - bases[p] for p in sizes)
        check('%s: the arena\'s slack = the base\'s (0x%X)' % (name, slack0), r1[3] - blocks, slack0)
    check('pools with the pack: animation 160, effect 128, resource 704 MiB',
          {p: e >> 20 for p, e in exts.items()}, {'animation': 160, 'effect': 128, 'resource': 704})
    d0, d1 = NORMAL_FREE - total0, EXT_FREE - ext_total
    check('with the pack, the default heap grows (0x%X -> 0x%X, >= 3x)' % (d0, d1), d1 >= 3 * d0, True)
    import kind_expand as K
    img, found = K.Image(old), []
    getters = {g for _n, g, _c, _e in X.POOLS}
    for at in range(0x02000000, 0x04B80000, 4):
        try:
            w = img.w(at)
        except KeyError:                    # gaps between sections
            continue
        if w >> 26 == 18 and w & 3 == 1:
            off = w & 0x3FFFFFC
            if (at + off - (0x4000000 if off & 0x2000000 else 0)) in getters:
                found.append(at)
    check('every getter call is hooked (the base\'s callers of the three getters)',
          sorted(at for _n, g, calls, _e in X.POOLS for at in calls), found)
    # the 1 GiB cap skipped (the base: ble 0x03374EF4 over the 1 GiB tail allocation; patched: b there)
    check('the 1 GiB cap: base 0x%08X is ble +0x24' % X.CAP_SITE, E0.w(X.CAP_SITE), X.CAP_WORD)
    check('the 1 GiB cap: patched to b +0x24 (the same target, always)', E1.w(X.CAP_SITE), X.CAP_SKIP)
    check('the cap\'s target keeps r29 (0x03374EF4 is past `mr r29, r3`)', (E0.w(0x03374EF0), E0.w(0x03374EF4)),
          (0x7C7D1B78, 0x7FE3FB78))
    # the pack
    with tempfile.TemporaryDirectory() as d:
        X.write_pack(d)
        txt = open(os.path.join(d, 'rules.txt')).read()
    m = re.search(r'^\[RAM\]\s*\nmapping0 = 0x([0-9A-F]{8})-0x([0-9A-F]{8})', txt, re.M)
    v = re.search(r'^version = (\d+)', txt, re.M)
    check('rules.txt: [RAM] mapping0 and version', bool(m and v), True)
    lo, hi = int(m.group(1), 16), int(m.group(2), 16)
    check('mapping0 starts at MEM2\'s base (Cemu matches the range by its base)', lo, 0x10000000)
    check('mapping0: aligned to 0x1000, past 0x50000000, below the overlay arena 0xA0000000 and 0x80000000',
          (lo & 0xFFF, hi & 0xFFF, hi > 0x50000000, hi <= 0x80000000), (0, 0, True, True))
    check('version >= 6 ([RAM] needs it)', int(v.group(1)) >= 6, True)
    check('title ids: Smash 4 Wii U US / EU / JP', re.search(r'^titleIds = (.*)$', txt, re.M).group(1),
          '0005000010144F00,0005000010145000,0005000010110E00')
    check('the extended RAM reaches the threshold: free with the pack 0x%08X >= 0x%08X' % (EXT_FREE, X.THRESHOLD),
          EXT_FREE >= X.THRESHOLD, True)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
