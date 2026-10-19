#!/usr/bin/env python3
"""Emulator test (Unicorn) for tools/kirby_stat_cave.py: get_float on fake WorkModules.
    python3 tools/kirby_stat_test.py"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kirby_stat_cave as K
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import *

fails = 0
WM, TABLE, CONT0, CONT3, INTS, FLOATS = 0x10400000, 0x10400100, 0x10400200, 0x10400300, 0x10401000, 0x10402000
RET = 0x02000000


def check(name, got, want):
    global fails
    ok = abs(got - want) < 1e-5
    fails += not ok
    print("%-44s got %-12r want %-12r %s" % (name, got, want, "OK" if ok else "FAIL"))


def get(marker, stat=0x03000016, value=2.0, count=0x90):
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(0x02000000, 0x2000000)
    mu.mem_map(0x10400000, 0x10000)
    for addr, w in K.words().items():
        mu.mem_write(addr, struct.pack(">I", w))
    mu.mem_write(RET, struct.pack(">I", 0x48000000))
    mu.mem_write(WM + 8, struct.pack(">I", TABLE))
    mu.mem_write(TABLE, struct.pack(">I", CONT0))                     # category 0: instance ints
    mu.mem_write(TABLE + 4, struct.pack(">I", 0x10400400))            # category 1: status (no marker)
    mu.mem_write(TABLE + 12, struct.pack(">I", CONT3))                # category 3: fighter_param
    mu.mem_write(0x10400400 + 4, struct.pack(">I", FLOATS))           # (category 1 floats, for 0x01...)
    mu.mem_write(CONT0 + 8, struct.pack(">II", count | 0x40000000, INTS))
    mu.mem_write(INTS + K.INT_INDEX * 4, struct.pack(">I", marker))
    mu.mem_write(CONT3 + 4, struct.pack(">I", FLOATS))
    mu.mem_write(FLOATS + (stat & 0xFFFFFF) * 4, struct.pack(">f", value))
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.reg_write(UC_PPC_REG_3, WM)
    mu.reg_write(UC_PPC_REG_4, stat)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.emu_start(K.HOOKS[3], RET, count=200)                           # fighters' get_float copy
    return struct.unpack(">d", struct.pack(">Q", mu.reg_read(UC_PPC_REG_FPR1)))[0]


check("Rush Kirby: max air speed 2 x1.25", get(0x4B490001), 2.5)
check("Overdrive: x1.5", get(0x4B490002), 3.0)
check("Rush bit + Strike flag 0x8: still x1.25", get(0x4B490009), 2.5)
check("Strike only (profile 0): unchanged", get(0x4B490008), 2.0)
check("other fighter (no marker): unchanged", get(0x12345671), 2.0)
check("Rush: jump height (0x0E) unchanged", get(0x4B490001, stat=0x0300000E), 2.0)
check("Rush: non-stat float unchanged", get(0x4B490001, stat=0x01000006), 2.0)
check("too few ints: unchanged", get(0x4B490001, count=0x10), 2.0)
print("FAILS", fails)
sys.exit(1 if fails else 0)
