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
    total0, anim0 = X.lis_value(E0.w(P.ARENA_TOTAL)), X.lis_value(E0.w(P.ANIM_GETTER))
    check('the base is exe_v11\'s heap sizes (total 0x36600000, animation 46 MiB)', (total0, anim0),
          (0x36600000, 0x2E00000))
    slack0 = total0 - sum(X.lis_value(E0.w(g)) for g in GETTERS)
    ext_total = total0 + X.ANIM_EXT - anim0
    for name, free, want_total, want_anim in (('normal MEM2', NORMAL_FREE, total0, anim0),
                                              ('just below the threshold', X.THRESHOLD - 0x1000, total0, anim0),
                                              ('at the threshold', X.THRESHOLD, ext_total, X.ANIM_EXT),
                                              ('the pack\'s MEM2', EXT_FREE, ext_total, X.ANIM_EXT),
                                              ('normal again (a fresh boot)', NORMAL_FREE, total0, anim0)):
        if name.startswith('normal'):
            E1.setw(X.build(total0, anim0)[1]['flag'], 0)        # a boot starts with the cave's zero
        r1 = call(E1, X.HOOK_TOTAL, {29: free})
        r0 = call(E0, X.HOOK_TOTAL, {29: free})
        check('%s (free 0x%08X): arena total 0x%08X' % (name, free, want_total), r1[3], want_total)
        check('%s: registers but r3 / r11 / r12 as the base leaves them' % name,
              [i for i in range(32) if i not in (3, 11, 12) and r1[i] != r0[i]], [])
        for at in X.HOOK_ANIM:
            a1, a0 = call(E1, at, {}), call(E0, at, {})
            check('%s: animation heap at 0x%08X = 0x%08X' % (name, at, want_anim), a1[3], want_anim)
            check('%s: 0x%08X, registers but r3 / r11 / r12 as the base' % (name, at),
                  [i for i in range(32) if i not in (3, 11, 12) and a1[i] != a0[i]], [])
        blocks = sum(X.lis_value(E0.w(g)) for g in GETTERS) - anim0 + want_anim
        check('%s: the arena\'s slack = the base\'s (0x%X)' % (name, slack0), r1[3] - blocks, slack0)
    check('with the pack, the default heap grows (0x%X -> 0x%X)' % (NORMAL_FREE - total0, EXT_FREE - ext_total),
          EXT_FREE - ext_total > 4 * (NORMAL_FREE - total0), True)
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
