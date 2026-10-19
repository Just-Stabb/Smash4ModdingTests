#!/usr/bin/env python3
"""Emulator test (Unicorn) for tools/copy_fx_cave.py: the +0x6C hook with stub game functions.
    python3 tools/copy_fx_test.py"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy_fx_cave as C
from ppcasm import Asm
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import *

a, words = C.assemble()
fails = 0
LOG = 0x10400000          # stub calls append (function id, r3, r4, r5, r6) here; [LOG - 4] = count
MGR = 0x10300000
THIS = 0x10500000
RET = 0x02000000
SET_TABLE, BIND, FSYNC = 0x02E424D8, 0x02BEE560, 0x02BEE950   # stubbed: the cave must not call them


def check(name, got, want):
    global fails
    ok = got == want
    fails += not ok
    print("%-48s got %-30r want %-30r %s" % (name, got, want, "OK" if ok else "FAIL"))


def stub(addr, fid, ret):
    """log (fid, r3-r6), return ret in r3"""
    s = Asm(addr)
    s.asm("""
        lis r11, 0x1040
        lwz r12, -4(r11)
        mulli r0, r12, 20
        add r11, r11, r0
        li r0, %d
        stw r0, 0(r11)
        stw r3, 4(r11)
        stw r4, 8(r11)
        stw r5, 0xC(r11)
        stw r6, 0x10(r11)
        lis r11, 0x1040
        addi r12, r12, 1
        stw r12, -4(r11)
        lis r3, %s
        ori r3, r3, %s
        blr""" % (fid, hex(ret >> 16), hex(ret & 0xFFFF)))
    return b"".join(struct.pack(">I", w) for w in s.words())


def fresh(script=0x5C00, tables=(0x7AB1E0, 0x7AB1E1, 0x7AB1E2, 0x7AB1E3), no_sync=0):
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(0x02000000, 0x01000000)
    mu.mem_map(0x03000000, 0x01000000)
    mu.mem_map(0x04B70000, 0x10000)
    mu.mem_map(0x10200000, 0x400000)
    mu.mem_write(C.CAVE, b"".join(struct.pack(">I", w) for w in words))
    mu.mem_write(C.TRAMP, b"".join(struct.pack(">I", w) for w in C.trampoline(a.labels["copy_fx"])))
    off = C.TRAMP - C.HOOK
    mu.mem_write(C.HOOK, struct.pack(">I", (18 << 26) | (off & 0x3FFFFFC)))
    mu.mem_write(C.HOOK + 4, struct.pack(">I", 0x48000000))          # b . (the original's rest)
    mu.mem_write(C.SCRIPT_OF, stub(C.SCRIPT_OF, 1, script))
    # the set table stub returns tables[set] (set in r5)
    s = Asm(SET_TABLE)
    s.asm("""
        lis r11, 0x1030
        slwi r12, r5, 2
        addi r12, r12, 0x100
        lwzx r12, r11, r12
        mtctr r12
        bctr""")
    mu.mem_write(SET_TABLE, b"".join(struct.pack(">I", w) for w in s.words()))
    mu.mem_write(0x02F00000, stub(0x02F00000, 2, 0))                      # logs, then returns...
    for i, t in enumerate(tables):                                        # ...the table: one stub each
        addr = 0x02F00100 + 0x100 * i
        mu.mem_write(addr, stub(addr, 2, t))
        mu.mem_write(MGR + 0x100 + 4 * i, struct.pack(">I", addr))
    mu.mem_write(BIND, stub(BIND, 3, 0))
    mu.mem_write(FSYNC, stub(FSYNC, 4, 0))
    mu.mem_write(THIS + 0x1C, struct.pack(">I", 0x47C))                 # pending motion (late update)
    mu.mem_write(THIS + 0x20, struct.pack(">ff", 5.0, 1.0))             # frame, rate
    mu.mem_write(THIS + 0x2C, bytes([0, no_sync]))
    mu.mem_write(0x102FF68C, struct.pack(">I", MGR))
    mu.mem_write(THIS + 4, struct.pack(">I", 0xACC))
    mu.mem_write(THIS + 0x18, struct.pack(">I", 8))                     # own kind (Kirby)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    return mu


def call(mu, set_, motion, kind):
    for r, v in ((1, 0x104F0000), (3, THIS), (4, set_), (5, motion), (6, kind)):
        mu.reg_write(getattr(sys.modules["unicorn.ppc_const"], "UC_PPC_REG_%d" % r), v)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.mem_write(RET, struct.pack(">I", 0x48000000))
    mu.emu_start(C.HOOK, 0, count=400)
    n = struct.unpack(">I", mu.mem_read(LOG - 4, 4))[0]
    log = [struct.unpack(">5I", mu.mem_read(LOG + 20 * i, 20)) for i in range(n)]
    return mu.reg_read(UC_PPC_REG_PC), log


dbg = lambda mu, k: struct.unpack(">I", mu.mem_read(a.labels["dbg"] + 4 * k, 4))[0]

mu = fresh()
pc, log = call(mu, 0, 0x212, 0xF)
check("set 0: goes on to +0x6C (r0 = LR)", (pc, mu.reg_read(UC_PPC_REG_0), mu.reg_read(UC_PPC_REG_4), log), (C.HOOK + 4, RET, 0, []))
check("  +0x6C calls counted", (dbg(mu, 0), dbg(mu, 1)), (1, 0))

mu = fresh()
pc, log = call(mu, C.BIND_ALL, 0x212, 0xF)
check("bind all: returns to the caller", pc, RET)
check("  only the script lookup (mgr, kind, motion)", [l[:4] for l in log], [(1, MGR, 0xF, 0x212)])
check("  late bind override: +0x28 kind, +0x2E on", (struct.unpack(">I", mu.mem_read(THIS + 0x28, 4))[0], mu.mem_read(THIS + 0x2E, 1)[0]), (0xF, 1))
check("  pending motion +0x1C = the custom", struct.unpack(">I", mu.mem_read(THIS + 0x1C, 4))[0], 0x212)
check("  +0x2C / +0x2D (frame set's flags) untouched", tuple(mu.mem_read(THIS + 0x2C, 2)), (0, 0))
check("  set kinds untouched (late bind stores them)", struct.unpack(">III", mu.mem_read(THIS + 0xC, 12)), (0, 0, 0))
check("  debug: calls, bind-all, motion, kind, script", tuple(dbg(mu, k) for k in range(5)), (1, 1, 0x212, 0xF, 0x5C00))
pc, log = call(mu, C.BIND_ALL, 0x212, 0xF)
check("  counts past 1", (dbg(mu, 0), dbg(mu, 1)), (2, 2))

mu = fresh()
call(mu, C.BIND_ALL, 0x212, -1 & 0xFFFFFFFF)
check("kind -1: own kind (+0x18)", (dbg(mu, 3), struct.unpack(">I", mu.mem_read(THIS + 0x28, 4))[0]), (8, 8))

mu = fresh(script=0)
pc, log = call(mu, C.BIND_ALL, 0x999, 0xF)
check("no script: nothing changed", (pc, struct.unpack(">I", mu.mem_read(THIS + 0x1C, 4))[0], mu.mem_read(THIS + 0x2E, 1)[0]), (RET, 0x47C, 0))
print("FAILS", fails)
sys.exit(1 if fails else 0)
