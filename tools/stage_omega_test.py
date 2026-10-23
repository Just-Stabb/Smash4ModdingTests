#!/usr/bin/env python3
"""Checks stage_omega_cave.py in a patched RPX, in unicorn.

  python3 tools/stage_omega_test.py PATCHED.rpx ORIGINAL.rpx

- the original words are the expected ones (the RPX the cave was written for), the patched the cave's;
- entry: r4 = 1 (Omega) and `flipped` cleared;
- toggle: `flipped` set only when the state asked for differs, registers passed on to 0x0298C984;
- confirm: isOmega as the game's for ids below 0x38 and 0xC8+; 0 for 0x38-0xC7 until flipped.
"""
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage_omega_cave as C  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_29, UC_PPC_REG_LR)

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def main():
    patched, original = sys.argv[1:3]
    a, patches = C.build()
    om, pm = machine(original), machine(patched)
    check('original words', {k: r32(om, k) for k in C.ORIGINAL}, C.ORIGINAL)
    check('patched words', all(r32(pm, k) == v for k, v in patches.items()), True)
    flag = a.addr('flipped')
    STATE = 0x7F000000                  # where the stubs record what they were given (lis r12, STATE >> 16)

    def run(fn, regs):
        for r, v in regs.items():
            pm.reg_write(r, v)
        pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
        pm.reg_write(UC_PPC_REG_LR, RET)
        pm.emu_start(fn, RET, count=200)

    # entry
    pm.mem_write(flag, struct.pack('>I', 0x01000000))
    run(a.addr('entry'), {UC_PPC_REG_3: 0x1234, UC_PPC_REG_4: 0})
    check('entry: r4 = 1 (Omega)', pm.reg_read(UC_PPC_REG_4), 1)
    check('entry: r3 kept', pm.reg_read(UC_PPC_REG_3), 0x1234)
    check('entry: flipped cleared', pm.mem_read(flag, 1)[0], 0)

    # toggle: stub 0x0298C984 records r3 / r4 / r5
    stub = Asm_words(C.SET_STATE, '''
        lis r12, %d
        stw r3, 0(r12)
        stw r4, 4(r12)
        stw r5, 8(r12)
        blr''' % (STATE >> 16))
    pm.mem_write(C.SET_STATE, stub)
    sw = 0x7F00D000
    pm.mem_write(sw + 8, struct.pack('>I', 1))
    run(a.addr('toggle'), {UC_PPC_REG_3: sw, UC_PPC_REG_4: 1, UC_PPC_REG_5: 1})
    check('toggle, same state: not flipped', pm.mem_read(flag, 1)[0], 0)
    check('toggle passes r3 / r4 / r5 on', struct.unpack('>3I', pm.mem_read(STATE, 12)), (sw, 1, 1))
    run(a.addr('toggle'), {UC_PPC_REG_3: sw, UC_PPC_REG_4: 0, UC_PPC_REG_5: 1})
    check('toggle to normal: flipped', pm.mem_read(flag, 1)[0], 1)
    check('toggle passes the new state on', struct.unpack('>3I', pm.mem_read(STATE, 12)), (sw, 0, 1))

    # confirm: stub isOmega -> the word at STATE + 0x10
    pm.mem_write(C.IS_OMEGA, Asm_words(C.IS_OMEGA, '''
        lis r12, %d
        lwz r3, 0x10(r12)
        blr''' % (STATE >> 16)))

    def confirm(stage, omega, flipped):
        pm.mem_write(STATE + 0x10, struct.pack('>I', omega))
        pm.mem_write(flag, bytes([flipped]))
        run(a.addr('confirm'), {UC_PPC_REG_3: 0x5000, UC_PPC_REG_29: stage})
        return pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_29), pm.reg_read(UC_PPC_REG_1)
    for stage in (0x01, 0x1E, 0x37, 0xC8, 0xFF):
        check('confirm 0x%X Omega switch: Omega' % stage, confirm(stage, 1, 0)[0], 1)
        check('confirm 0x%X normal switch: normal' % stage, confirm(stage, 0, 0)[0], 0)
    for stage in (0x38, 0x39, 0xC7):
        check('confirm new 0x%X, Omega by default: normal' % stage, confirm(stage, 1, 0)[0], 0)
        check('confirm new 0x%X, flipped to Omega: Omega' % stage, confirm(stage, 1, 1)[0], 1)
        check('confirm new 0x%X, flipped to normal: normal' % stage, confirm(stage, 0, 1)[0], 0)
    check('confirm keeps r29 and the stack', confirm(0x38, 1, 0)[1:], (0x38, 0x7F00F000))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


def Asm_words(base, text):
    from ppcasm import Asm
    a = Asm(base)
    a.asm(text)
    return b''.join(struct.pack('>I', w) for w in a.words())


if __name__ == '__main__':
    main()
