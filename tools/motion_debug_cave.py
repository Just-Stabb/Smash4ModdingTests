#!/usr/bin/env python3
"""DEBUG ONLY: what a copy motion's animation record looks like. Prints rpx_patch.py args, added
after the standard build's (it uses the free words after tools/copy_fx_cave.py's cave).

MotionModule 0x02C5D4EC(this, motion) returns the animation for a motion (from change motion
0x02C5D730): record = [this+0x1C] + motion * 8 (u32 animation, u16, u16 flags); flag 0x8 =
borrowed from the module at accessor +0x68 (vtable +0x204, motion + [this+0x100]); otherwise the
record's own word. The hook at its first instruction stores, for every motion above 0x30A (Kirby's
copy motions), the debug words (DBG, printed by main):
  +0x00 calls  +0x04 this  +0x08 motion  +0x0C [this+0x1C] (record table)
  +0x10 record word 0  +0x14 record word 1 (u16, u16 flags)  +0x18 [this+0x100]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402

CAVE = 0x04B78F50
LIMIT = 0x04B79000
HOOK = 0x02C5D4EC           # mflr r0

SOURCE = """
mdbg:
        cmpwi r4, 0x30A
        ble mdbg_out
        lis r11, dbg@ha
        addi r11, r11, dbg@l
        lwz r12, 0(r11)
        addi r12, r12, 1
        stw r12, 0(r11)
        stw r3, 4(r11)
        stw r4, 8(r11)
        lwz r12, 0x1C(r3)
        stw r12, 0xC(r11)
        lwz r9, 0x100(r3)
        stw r9, 0x18(r11)
        cmpwi r12, 0
        beq mdbg_out
        slwi r10, r4, 3
        add r10, r12, r10
        lwz r9, 0(r10)
        stw r9, 0x10(r11)
        lwz r9, 4(r10)
        stw r9, 0x14(r11)
mdbg_out:
        mflr r0
        b %(BACK)s
dbg:
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
"""


def assemble():
    a = Asm(CAVE)
    a.asm(SOURCE % dict(BACK="0x%08X" % (HOOK + 4)))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, "motion debug cave too big: %d words" % len(words)
    return a, words


def main():
    a, words = assemble()
    out = ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    off = CAVE - HOOK
    assert off < 0x2000000
    out.append("0x%08X=0x%08X" % (HOOK, (18 << 26) | (off & 0x3FFFFFC)))
    print(" ".join(out))
    sys.stderr.write("debug words at 0x%08X\n" % a.labels["dbg"])


if __name__ == "__main__":
    main()
