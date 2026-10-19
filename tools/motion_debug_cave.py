#!/usr/bin/env python3
"""DEBUG ONLY: what a copy motion's animation record looks like. Prints rpx_patch.py args, added
after the standard build's (it uses the free words after tools/copy_fx_cave.py's cave).

MotionModule 0x02C5D4EC(this, motion) returns the animation for a motion (from change motion
0x02C5D730): v1 (record = [this+0x1C] + motion * 8) showed those records only hold a face (material
animation) key. The body animation comes from 0x02C5D5C0: S = [this+0x18], group lists
[S+0x10] (list, count), entries [S+8] + i*8 = (per-motion array, part bit), animation =
array[motion]. v2 stores, for every motion above 0x30A (Kirby's copy motions), the debug words:
  +0x00 calls  +0x04 motion  +0x08 S  +0x0C group 0 count  +0x10 its first entry
  +0x14 entry part  +0x18 entry array  +0x1C &array[motion]  +0x20 array[motion]
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
        stw r4, 4(r11)
        lwz r12, 0x18(r3)               # S
        stw r12, 8(r11)
        cmpwi r12, 0
        beq mdbg_out
        lwz r10, 0x10(r12)              # group lists
        lwz r9, 0(r10)                  # group 0 list
        lwz r10, 4(r10)                 # its count
        stw r10, 0xC(r11)
        lwz r9, 0(r9)                   # first entry index
        stw r9, 0x10(r11)
        lwz r10, 8(r12)                 # entries
        slwi r9, r9, 3
        add r10, r10, r9
        lwz r9, 4(r10)                  # part
        stw r9, 0x14(r11)
        lwz r10, 0(r10)                 # per-motion array
        stw r10, 0x18(r11)
        cmpwi r10, 0
        beq mdbg_out
        slwi r9, r4, 2
        add r10, r10, r9                # its slot for this motion
        stw r10, 0x1C(r11)
        lwz r9, 0(r10)
        stw r9, 0x20(r11)
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
