#!/usr/bin/env python3
"""Byleth v10 (master.c master_hold_gravity): unicorn on an executable (python3 tools/kinetic_suspend_test.py EXE.rpx): kinetic_module_impl's MSC op handler 0x02C510C4 on exe_v46w_vars_line: ops 0x2717 / 0x2718 on energy 1
set / clear the energy's +0x19 (the update skips an energy with +0x19 set: docs/native-notes.md 0x02C50058)"""
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from stage_slot_test import machine, RET
from unicorn.ppc_const import *
EXE = sys.argv[1] if len(sys.argv) > 1 else 'exe_v46w_vars_line.rpx'
mu = machine(EXE)
# paired-single saves / restores of f29 - f31 (opcode 4) in the function: unicorn's PPC32 has no paired singles; as nops
for a in range(0x02C510C4, 0x02C534B0, 4):
    if struct.unpack('>I', mu.mem_read(a, 4))[0] >> 26 == 4:
        mu.mem_write(a, struct.pack('>I', 0x60000000))
mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on
M, A, E = 0x7F000000, 0x7F001000, 0x7F002000
w = lambda a, v: mu.mem_write(a, struct.pack('>I', v))
for i in range(4):
    w(M + 0x18 + 0x10 * i, E + 0x100 * i)
w(M + 0xC, 4)
def op(code, idx):
    w(A, A + 0x10); w(A + 4, 2); w(A + 0x10, code); w(A + 0x14, idx)   # {args, count 2}
    mu.reg_write(UC_PPC_REG_3, M); mu.reg_write(UC_PPC_REG_4, A)
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000); mu.reg_write(UC_PPC_REG_LR, RET)
    mu.emu_start(0x02C510C4, RET, count=100000)
    return [mu.mem_read(E + 0x100 * i + 0x18, 2) for i in range(4)]
r = op(0x2717, 1); ok1 = r[1][1] == 1 and all(r[i][1] == 0 for i in (0, 2, 3))
r = op(0x2718, 1); ok2 = r[1][1] == 0
print('ok  ' if ok1 else 'FAIL', 'KineticModule(0x2717, 1): energy 1 +0x19 = 1 (suspended), the others untouched')
print('ok  ' if ok2 else 'FAIL', 'KineticModule(0x2718, 1): energy 1 +0x19 = 0 (resumed)')
