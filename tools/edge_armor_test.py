#!/usr/bin/env python3
"""Runs the game's MSC DamageModule armor command and its "no reaction" check in unicorn: the damage-based armor
Sephiroth's held Octaslash sets (fighters/edge/edge.c edge_hi_armor, test 149: `DamageModule(0xb, 3, 3.0f)`, cleared
with `DamageModule(0xb, 0, 0)`).

  python3 tools/edge_armor_test.py [RPX]        (default build/cross_f.rpx: the code is the base game's)

- the MSC handler (DamageModule vt +0x1E4, 0x02C2366C) case 0xB: mode 3 puts its value in the slot's damage threshold
  (f2: mode 2's knockback threshold is f1), slot 0 of the armor container (DamageModule +0x10);
- the check 0x02C24C88(container, 0, f1 knockback, f2 damage) -> 1 "no reaction" (no flinch; the damage is still
  taken): for mode 3 when damage <= the threshold (fcmpu, GT taken out: 3.0 itself is armored), any knockback;
- mode 0 clears it.
docs/native-notes.md "Armor check".
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from unicorn.ppc_const import UC_PPC_REG_FPR1, UC_PPC_REG_FPR2, UC_PPC_REG_MSR  # noqa: E402
from kind_expand_test import Emu  # noqa: E402

HANDLER = 0x02C2366C     # DamageModule vt +0x1E4: the MSC command handler (jump table, 0x14 commands)
CHECK = 0x02C24C88       # the armor container's "no reaction?" (r3 container, r4 0, f1 knockback, f2 damage)
FAILS = []


def check(what, got, want):
    ok = got == want
    print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))
    if not ok:
        FAILS.append(what)


def f2w(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def dbl(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def main():
    rpx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'build', 'cross_f.rpx')
    e = Emu(rpx)
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)    # floating point on
    vt = e.alloc(0x400, b'\0')
    stub = e.alloc(8, b'\0')
    e.mu.mem_write(stub, struct.pack('>II', 0x38600000, 0x4E800020))     # li r3, 0; blr (vt +0x11C)
    for o in range(0, 0x400, 4):
        e.setw(vt + o, stub)
    dm = e.alloc(0x100, b'\0')
    e.setw(dm, vt)
    cont = dm + 0x10
    for s in range(2):                               # empty slots: mode -1 (0x02C24C88 skips them)
        e.setw(cont + 4 + 0x10 * s, 0xFFFFFFFF)

    def msc(*words):
        args = e.alloc(0x40, b'\0')
        for i, w in enumerate(words):
            e.setw(args + 4 * i, w)
        frame = e.alloc(0x10, b'\0')
        e.setw(frame, args)
        e.setw(frame + 4, len(words))
        return e.call(HANDLER, dm, frame)

    def no_reaction(kb, dmg):
        e.mu.reg_write(UC_PPC_REG_FPR1, dbl(kb))
        e.mu.reg_write(UC_PPC_REG_FPR2, dbl(dmg))
        return e.call(CHECK, cont, 0)

    check('no armor: 1% hit reacts', no_reaction(10.0, 1.0), 0)
    msc(0xB, 3, f2w(3.0))
    check('slot 0 mode', e.w(cont + 4), 3)
    check('slot 0 damage threshold', struct.unpack('>f', struct.pack('>I', e.w(cont + 0xC)))[0], 3.0)
    for dmg, want in ((0.14, 1), (2.3, 1), (2.99, 1), (3.0, 1), (3.01, 0), (3.5, 0), (12.0, 0)):
        check('armor 3: %g%% hit (knockback 200) no reaction' % dmg, no_reaction(200.0, dmg), want)
    msc(0xB, 0, 0)
    check('cleared: 1% hit reacts', no_reaction(10.0, 1.0), 0)
    msc(0xB, 2, f2w(50.0))                           # the game's own use (smash charge armor): knockback-based
    check('armor 2 (knockback 50): knockback 40 no reaction', no_reaction(40.0, 30.0), 1)
    check('armor 2 (knockback 50): knockback 60 reacts', no_reaction(60.0, 1.0), 0)
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
