#!/usr/bin/env python3
"""A reflector for Robin's fighter kind (and Hero, kind 0x45, who shares its per-kind setup): prints
rpx_patch.py args. Hero's Bounce (fighters/brave/brave.c brave_reflect) turns it on.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/brave_reflect_cave.py)

(after trait_badge_cave.py, whose grow covers CAVE.)

Every fighter object has the reflector groups' storage (the constructor 0x02E52960: 20 shapes at
+0x4E90, 5 groups at +0x58A4), but a group only gets a shape from the fighter kind's own setup:
Kirby's (0x02EF57E8, at 0x02EF5A94-0x02EF5B04) and Zelda's give reflector group 3 one, Robin's
(0x02F60194, vtable 0x101417F8) none, so on him ACMD REFLECTOR / SHIELD_ON (and MSC
ShieldModule(0x2717 / 0, 3, ...)) write into an unused slot and nothing reflects. The first instruction
of Robin's setup (lwz r10, 0x28(r4)) branches to CAVE, which does what Kirby's does (the reflector
module R = [fighter + 0x72F8]; REFL_GROUP_INIT(R[8] + 0x9C, R + 0x18, R[0x44], R + 0xC, &params, 3,
R[0x14]) with params {&shape, 1 shape, 1.0 x 4, 0} and the shape all 0 but its byte +0x1E = 2, then
R[0x14] += its result and 0x0200BD8C(R, 0, 0, 3)), then goes on with the setup. The shape itself
(bone, size, place, multipliers) comes from the REFLECTOR command when it's turned on. Research:
the shield disassembly notes in fighters/brave/README.md ("Bounce").
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

HOOK = 0x02F60194               # Robin's per-kind setup: lwz r10, 0x28(r4)
HOOK_WORD = 0x8144_0028
CAVE = 0x04B85600               # trait_badge_cave.py's MENU_LIMIT to its grow's end
LIMIT = 0x04B85800
REFL_GROUP_INIT = 0x02C6F5FC
GROUP_STATE = 0x0200BD8C
REFLECTOR = 0x72F8              # the fighter's reflector module (shield kind 3)
GROUP = 3


def build():
    a = Asm(CAVE)
    a.asm("""
        stwu r1, -0xC0(r1)
        mflr r0
        stw r0, 0xC4(r1)
        stmw r3, 0x48(r1)
        lwz r30, 0x28(r4)           # the fighter
        lwz r31, %(refl)d(r30)      # its reflector module
        cmpwi r31, 0
        beq out
        li r0, 0
        stw r0, 0x8(r1)             # the shape (0x20 bytes at 0x8): all 0
        stw r0, 0xC(r1)
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        stw r0, 0x20(r1)
        sth r0, 0x24(r1)
        li r9, 2
        stb r9, 0x26(r1)
        addi r5, r1, 0x8            # params (0x28): the shapes, their count, 4 multipliers, 0
        stw r5, 0x28(r1)
        li r6, 1
        stw r6, 0x2C(r1)
        lis r9, 0x3F80
        stw r9, 0x30(r1)
        stw r9, 0x34(r1)
        stw r9, 0x38(r1)
        stw r9, 0x3C(r1)
        stb r0, 0x40(r1)
        lwz r7, 8(r31)
        addi r3, r7, 0x9C
        addi r4, r31, 0x18
        lwz r5, 0x44(r31)
        addi r6, r31, 0xC
        addi r7, r1, 0x28
        li r8, %(group)d
        lwz r9, 0x14(r31)
        lis r12, %(init_hi)d
        ori r12, r12, %(init_lo)d
        mtctr r12
        bctrl
        lwz r5, 0x14(r31)
        add r5, r5, r3
        stw r5, 0x14(r31)
        mr r3, r31
        li r4, 0
        li r5, 0
        li r6, %(group)d
        lis r12, %(state_hi)d
        ori r12, r12, %(state_lo)d
        mtctr r12
        bctrl
out:    lmw r3, 0x48(r1)
        lwz r0, 0xC4(r1)
        mtlr r0
        addi r1, r1, 0xC0
        lwz r10, 0x28(r4)           # the replaced instruction
        b 0x%(back)08X
""" % dict(refl=REFLECTOR, group=GROUP, init_hi=REFL_GROUP_INIT >> 16, init_lo=REFL_GROUP_INIT & 0xFFFF,
           state_hi=GROUP_STATE >> 16, state_lo=GROUP_STATE & 0xFFFF, back=HOOK + 4))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, 'cave too long'
    return words


def main():
    words = build()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append('0x%08X=0x%08X' % (HOOK, (18 << 26) | ((CAVE - HOOK) & 0x3FFFFFC)))
    print(' '.join(out))
    sys.stderr.write('brave reflector: %d words\n' % len(words))


if __name__ == '__main__':
    main()
