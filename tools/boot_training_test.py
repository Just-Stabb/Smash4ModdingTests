#!/usr/bin/env python3
"""Unicorn test of tools/boot_training_cave.py in a patched cross_f.rpx:

  python3 tools/boot_training_test.py PATCHED.rpx

Runs the two hooked name loads of the root controller's set-up (0x02C87650 and 0x02C87660, each
until the next instruction) with fake pad slots: nothing held, L held on the GamePad / a Pro
controller / a GameCube controller, other buttons only, L on a slot whose status isn't valid this
frame. Checks the names they give (r3 / r5), that the menu mode is set to 0xB (the stub at
0x02C840CC records its argument) only with L, and that r29 / r30 / r31 and the stack are kept.
"""
import struct
import sys

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_PC, UC_PPC_REG_LR

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch  # noqa: E402
import boot_training_cave as B  # noqa: E402

REG = {n: getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % n) for n in range(32)}
FAKE = 0x30000000                     # fake pad wrappers / statuses
STACK = 0x31000000


def load(path):
    d, _shoff, _ent, secs = rpx_patch.load(path)
    out = {}
    for s in secs:
        if s[1] == 1 and s[3] and s[3] < 0x20000000:
            out[s[3]] = bytes(rpx_patch.section_data(d, s))
    return out


def run(secs, pads):
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    uc.mem_map(0x02000000, 0x03000000)               # code (the grown space too)
    uc.mem_map(0x10000000, 0x00800000)               # data, bss (the pad slots)
    for base, data in secs.items():
        uc.mem_write(base, data)
    uc.mem_map(FAKE, 0x100000)
    uc.mem_map(STACK - 0x10000, 0x20000)
    # pad slots: [slot] = (held, valid) or None
    for slot in range(26):
        uc.mem_write(B.PADS + 4 * slot, struct.pack('>I', 0))
    for slot, (held, valid) in pads.items():
        w = FAKE + 0x100 * slot
        st = FAKE + 0x8000 + 0x100 * slot
        uc.mem_write(B.PADS + 4 * slot, struct.pack('>I', w))
        uc.mem_write(w + 8, struct.pack('>I', st))
        uc.mem_write(st, struct.pack('>I', held))
        uc.mem_write(st + 0x87, bytes([1 if valid else 0]))
    modes = []
    uc.mem_write(B.SET_MODE, struct.pack('>I', 0x4E800020))       # stub: blr

    def hook(u, addr, size, _):
        if addr == B.SET_MODE:
            modes.append(u.reg_read(REG[3]))
            for r in range(3, 13):                                   # a call may change any volatile register
                u.reg_write(REG[r], 0xDEAD0000 + r)
    uc.hook_add(UC_HOOK_CODE, hook)
    keep = {29: 0x1011DEAD, 30: 0x22220000, 31: 0x33330000}
    for r, v in keep.items():
        uc.reg_write(REG[r], v)
    uc.reg_write(REG[1], STACK)
    uc.reg_write(UC_PPC_REG_LR, 0x0BADBAD0)
    uc.emu_start(B.NAME_SITE, B.NAME_SITE + 4)
    r3 = uc.reg_read(REG[3])
    uc.reg_write(REG[3], 0x12345678)
    uc.emu_start(B.NAME2_SITE, B.NAME2_SITE + 4)
    r5 = uc.reg_read(REG[5])
    kept = all(uc.reg_read(REG[r]) == v for r, v in keep.items()) and uc.reg_read(REG[1]) == STACK \
        and uc.reg_read(REG[3]) == 0x12345678
    return r3, r5, modes, kept


def main():
    secs = load(sys.argv[1])
    cases = [
        ('nothing held', {0: (0, True), 2: (0, True)}, False),
        ('L on the GamePad', {0: (B.L, True)}, True),
        ('L on a Pro controller (slot 2)', {0: (0, True), 2: (B.L | 0x10, True)}, True),
        ('L on a GameCube controller (slot 12)', {12: (B.L, True)}, True),
        ('other buttons only (R, A, ZL)', {0: (0x2000 | 0x10 | 0x4000, True)}, False),
        ('L on a slot not valid this frame', {3: (B.L, False)}, False),
        ('L on the dummy slot 1', {1: (B.L, True)}, False),
        ('no pads at all', {}, False),
    ]
    fails = 0
    for name, pads, want in cases:
        r3, r5, modes, kept = run(secs, pads)
        exp = B.TRAINING if want else B.TITLE
        ok = r3 == exp and r5 == exp and modes == ([B.TRAINING_MODE] if want else []) and kept
        fails += not ok
        print('%s %-40s r3 0x%08X r5 0x%08X modes %s kept %s' % ('ok  ' if ok else 'FAIL', name, r3, r5, modes, kept))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
