#!/usr/bin/env python3
"""Runs tools/brave_reflect_cave.py's code in a patched RPX in unicorn: Robin's per-kind setup entered
with a fake fighter, the group set-up calls stubbed.

  python3 tools/brave_reflect_test.py PATCHED.rpx

Checks: the setup's first word branches to the cave; REFL_GROUP_INIT gets Kirby's arguments (the
module's fields, group 3, its first free shape) and a parameter block of one zeroed shape (byte +0x1E
= 2) and multipliers 1.0; the module's shape count grows by its result; 0x0200BD8C(R, 0, 0, 3); the
setup goes on at its second word with r4 / r10 / the stack as they were; no reflector module: nothing
called.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brave_reflect_cave as C  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_4, UC_PPC_REG_10, UC_PPC_REG_31  # noqa: E402

ACC = 0x7F001000                # the setup's r4 (+0x28 the fighter)
FIGHTER = 0x7F002000
MOD = 0x7F00A000                # the reflector module
REC = 0x7F00C000                # stub records


def main():
    mu = machine(sys.argv[1])
    fails = 0

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print('%s %s: %r%s' % ('ok  ' if ok else 'FAIL', what, got, '' if ok else ' (want %r)' % (want,)))

    def w32(a, v):
        mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))

    def r32(a):
        return struct.unpack('>I', mu.mem_read(a, 4))[0]

    def stub(addr, src):
        a = Asm(addr)
        a.asm(src)
        mu.mem_write(addr, b''.join(struct.pack('>I', x) for x in a.words()))

    # REFL_GROUP_INIT records r3-r9 and a copy of the parameter block and its shape, returns 1
    stub(C.REFL_GROUP_INIT, """
        lis r12, 0x7F00
        ori r12, r12, 0xC000
        stw r3, 0(r12)
        stw r4, 4(r12)
        stw r5, 8(r12)
        stw r6, 0xC(r12)
        stw r7, 0x10(r12)
        stw r8, 0x14(r12)
        stw r9, 0x18(r12)
        lwz r10, 0(r7)
        stw r10, 0x1C(r12)
        lwz r10, 4(r7)
        stw r10, 0x20(r12)
        lwz r10, 8(r7)
        stw r10, 0x24(r12)
        lwz r10, 0x14(r7)
        stw r10, 0x28(r12)
        lwz r10, 0(r7)
        lwz r11, 0x1C(r10)
        stw r11, 0x2C(r12)
        lwz r11, 0(r10)
        stw r11, 0x30(r12)
        lwz r11, 0x18(r10)
        stw r11, 0x34(r12)
        lwz r11, 0x40(r12)
        addi r11, r11, 1
        stw r11, 0x40(r12)
        li r3, 1
        li r10, 0x55                # clobbered (the cave restores the setup's own)
        blr""")
    stub(C.GROUP_STATE, """
        lis r12, 0x7F00
        ori r12, r12, 0xC000
        stw r3, 0x50(r12)
        stw r4, 0x54(r12)
        stw r5, 0x58(r12)
        stw r6, 0x5C(r12)
        lwz r11, 0x44(r12)
        addi r11, r11, 1
        stw r11, 0x44(r12)
        blr""")
    check('the setup branches to the cave', r32(C.HOOK), (18 << 26) | ((C.CAVE - C.HOOK) & 0x3FFFFFC))

    def run(module):
        mu.mem_write(REC, b'\0' * 0x100)
        w32(ACC + 0x28, FIGHTER)
        w32(FIGHTER + C.REFLECTOR, module)
        w32(MOD + 8, 0x7F00B000)
        w32(MOD + 0x14, 4)                      # 4 shapes used already
        w32(MOD + 0x44, 0x12345678)
        mu.reg_write(UC_PPC_REG_4, ACC)
        mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
        mu.reg_write(UC_PPC_REG_31, 0x31313131)
        mu.reg_write(UC_PPC_REG_10, 0)
        # reached the setup's second word: stop
        mu.emu_start(C.HOOK, C.HOOK + 4, count=2000)
        return mu.reg_read(UC_PPC_REG_4), mu.reg_read(UC_PPC_REG_10), mu.reg_read(UC_PPC_REG_1), \
            mu.reg_read(UC_PPC_REG_31)

    regs = run(MOD)
    rec = [r32(REC + 4 * i) for i in range(0x18)]
    check('back at the setup: r4, r10 = [r4 + 0x28] (the replaced load), r1, r31 kept', regs,
          (ACC, FIGHTER, 0x7F00F000, 0x31313131))
    check('REFL_GROUP_INIT once, 0x0200BD8C once', (rec[0x10], rec[0x11]), (1, 1))
    check('its arguments: R[8] + 0x9C, R + 0x18, R[0x44], R + 0xC, group 3, first shape 4',
          [rec[0], rec[1], rec[2], rec[3], rec[5], rec[6]], [0x7F00B09C, MOD + 0x18, 0x12345678, MOD + 0xC, 3, 4])
    check('params: 1 shape, multipliers 1.0', (rec[8], rec[9], rec[10]), (1, 0x3F800000, 0x3F800000))
    check('the shape: its +0x1C half 0 and +0x1E byte 2, the floats 0', (rec[0xB], rec[0xC], rec[0xD]),
          (0x00000200, 0, 0))
    check('the shapes used: 4 + 1', r32(MOD + 0x14), 5)
    check('0x0200BD8C(R, 0, 0, 3)', rec[0x14:0x18], [MOD, 0, 0, 3])
    run(0)
    check('no reflector module: nothing called', (r32(REC + 0x40), r32(REC + 0x44)), (0, 0))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
