#!/usr/bin/env python3
"""Emulator test (Unicorn) for tools/position_vars_cave.py on a patched cross_f.rpx:
    python3 tools/position_vars_test.py [build/cross_f.rpx]
Fake fighter tables / PostureModules; IDs outside 0x0F0000xx run the game's own WorkModule code."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch as R
from ppcasm import Asm
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import *
RPX = sys.argv[1] if len(sys.argv) > 1 else 'build/cross_f.rpx'
d, _o, _e, SECS = R.load(RPX)
cache = {}
def mem(addr, n):
    i, data = R.locate(d, SECS, addr, cache); base = SECS[i][3]; return bytes(data[addr-base:addr-base+n])

SETPOS = 0x037FF100
fake = Asm(SETPOS); fake.asm('''
 lfs f0,0(r4)
 stfs f0,0x10(r3)
 lfs f0,4(r4)
 stfs f0,0x14(r3)
 lfs f0,8(r4)
 stfs f0,0x18(r3)
 lwz r12,0x70(r3)
 addi r12,r12,1
 stw r12,0x70(r3)
 blr''')
# Stand-ins for the game's MSC module wrappers (ctx +4 = accessor, args {ptr, count}); their state
# lives in the fake accessor: +0x800 + 4 * (ID & 0xFF) WorkModule ints, +0xA00 DamageModuleF(1),
# +0xA04 DamageModule(8), +0xA08 StopModule(1), +0xA0C StopModule(2) frames, +0xA10 / +0xA14 / +0xA18
# ShakeModule frames / intensity / argument count.
FAKES = {
    0x030B2B28: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 lwz r7, 4(r5)
 cmpwi r6, 6
 bne w7
 clrlwi r7, r7, 24
 slwi r7, r7, 2
 add r7, r7, r12
 lwz r3, 0x800(r7)
 blr
w7: lwz r8, 8(r5)
 clrlwi r8, r8, 24
 slwi r8, r8, 2
 add r8, r8, r12
 stw r7, 0x800(r8)
 li r3, 0
 blr""",
    0x030B2FC4: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 0
 beq df0
 lwz r3, 0xA00(r12)
 blr
df0: lwz r3, 0xA4C(r12)
 blr""",                                       # DamageModuleF(1) / (0) damage %
    0x030B2F8C: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 9
 beq dm9
 cmpwi r6, 0xB
 beq dmb
 lwz r3, 0xA04(r12)
 blr
dm9: lfs f0, 4(r5)
 lfs f1, 0xA4C(r12)
 fadds f1, f1, f0
 stfs f1, 0xA4C(r12)
 li r3, 0
 blr
dmb: lwz r8, 0x54(r12)
 lwz r7, 4(r5)
 stw r7, 0x14(r8)
 lwz r9, 8(r5)
 cmpwi r7, 2
 bne dmb3
 stw r9, 0x18(r8)
 li r3, 0
 blr
dmb3: stw r9, 0x1C(r8)
 li r3, 0
 blr""",                                       # DamageModule(8) / (9, add %) / (0xB, armor)
    0x030B2B60: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r7, 4(r5)
 clrlwi r7, r7, 24
 slwi r7, r7, 2
 add r7, r7, r12
 lwz r3, 0x800(r7)
 blr""",                                       # WorkModuleF(0, id): same table as the ints
    0x030B50B8: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 lwz r7, 4(r5)
 cmpwi r6, 2
 bne hm1
 stw r7, 0xA5C(r12)
 li r3, 0
 blr
hm1: stw r7, 0xA60(r12)
 li r3, 0
 blr""",                                       # HitModule(2, frames) intangible / (1, frames, 0)
    0x030B5160: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 2
 beq s2
 lwz r3, 0xA08(r12)
 blr
s2: lwz r7, 4(r5)
 stw r7, 0xA0C(r12)
 li r3, 0
 blr""",
    0x030B2B98: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 3
 beq st3
 cmpwi r6, 1
 beq st1
 cmpwi r6, 2
 beq st2
 lwz r3, 0xA1C(r12)
 blr
st1: lwz r3, 0xA48(r12)
 blr
st2: lwz r7, 4(r5)
 stw r7, 0xA48(r12)
 li r3, 0
 blr
st3: lwz r7, 4(r5)
 stw r7, 0xA1C(r12)
 lwz r7, 8(r5)
 stw r7, 0xA20(r12)
 lwz r7, 4(r4)
 stw r7, 0xA40(r12)
 li r3, 0
 blr""",                                       # StatusModule(0) / (3, status, keep)
    0x030B2A48: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 1
 beq mo1
 lwz r3, 0xA24(r12)
 blr
mo1: lwz r7, 4(r5)
 stw r7, 0xA24(r12)
 lwz r7, 8(r5)
 stw r7, 0xA28(r12)
 lwz r7, 0xC(r5)
 stw r7, 0xA2C(r12)
 li r3, 0
 blr""",                                       # MotionModule(7) / (1, motion, frame, rate)
    0x030B2A80: "lwz r12, 4(r3)\n lwz r3, 0xA30(r12)\n blr",          # MotionModuleF(1)
    0x030B50F0: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r6, 0(r5)
 cmpwi r6, 0x2727
 bne at6
 lwz r3, 0xA34(r12)
 blr
at6: lwz r3, 0xA38(r12)
 blr""",                                       # AttackModule(0x2727) / (0x2726)
    0x030B5C50: """lwz r12, 4(r3)
 lwz r5, 0(r4)
 lwz r7, 8(r5)
 stw r7, 0xA10(r12)
 lwz r7, 0x14(r5)
 stw r7, 0xA14(r12)
 lwz r7, 4(r4)
 stw r7, 0xA18(r12)
 li r3, 0
 blr""",
}
ENTRIES = 0x10400000
VT = 0x10380000
def setup(fighters, count=8):
    """fighters: list of (slot, x, y, z, lr, live)"""
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(0x02000000, 0x20000); mu.mem_write(0x02000020, mem(0x02000020, 0x1FFE0))
    mu.mem_map(0x02F10000, 0x20000); mu.mem_write(0x02F10000, mem(0x02F10000, 0x20000))  # fighters' WorkModule copies
    mu.mem_map(0x037E0000, 0x20000); mu.mem_write(0x037E0000, mem(0x037E0000, 0x20000))
    mu.mem_write(SETPOS, b''.join(struct.pack('>I', w) for w in fake.words()))
    mu.mem_map(0x04B70000, 0x40000); mu.mem_write(0x04B70000, mem(0x04B70000, 0x40000))  # grown .text (combat variables ... acmd_ext_cave.py)
    mu.mem_map(0x030B0000, 0x10000)
    for k, (addr, src) in enumerate(FAKES.items()):    # each in its own space, a branch at the wrapper
        body = 0x030B8000 + 0x100 * k
        f = Asm(body); f.asm(src)
        mu.mem_write(body, b''.join(struct.pack('>I', w) for w in f.words()))
        mu.mem_write(addr, struct.pack('>I', (18 << 26) | ((body - addr) & 0x3FFFFFC)))
    mu.mem_map(0x10300000, 0x200000)
    mu.mem_map(0x10000000, 0x10000); mu.mem_write(0x10000000, mem(0x10000000, 0x10000))
    mu.mem_write(0x1035184C, struct.pack('>I', 0x10360000))
    mu.mem_write(0x10360000, struct.pack('>I', 0x10360100))
    mu.mem_write(0x10360100, struct.pack('>III', ENTRIES, 0, count))
    mu.mem_write(VT + 0x4C, struct.pack('>I', SETPOS))
    objs = {}
    for slot, x, y, z, lr, live in fighters:
        e = ENTRIES + slot * 0x76B0
        acc = 0x10370000 + slot * 0x1000; post = acc + 0x100; wm = acc + 0x400
        mu.mem_write(e + 0x1E, bytes([4 if live else 2]))
        mu.mem_write(e + 0xC, struct.pack('>I', acc))
        mu.mem_write(acc + 0x18, struct.pack('>I', post)); mu.mem_write(acc + 0x28, struct.pack('>I', wm))
        mu.mem_write(post, struct.pack('>I', VT))
        mu.mem_write(post + 0x10, struct.pack('>fff', x, y, z)); mu.mem_write(post + 0x60, struct.pack('>f', lr))
        mu.mem_write(e, struct.pack('>I', slot << 16))          # object ID: fighter, slot
        objs[slot] = (wm, post)
    return mu, objs

RET = 0x037FF000
def call(mu, fn, wm, ident, val=0.0):
    mu.mem_write(RET, struct.pack('>I', 0x60000000))
    mu.reg_write(UC_PPC_REG_3, wm); mu.reg_write(UC_PPC_REG_4, ident)
    mu.reg_write(UC_PPC_REG_5, 0xDEAD)
    mu.reg_write(UC_PPC_REG_FPR1, struct.unpack('>Q', struct.pack('>d', val))[0])
    mu.reg_write(UC_PPC_REG_1, 0x10480000)
    for r in range(14, 32): mu.reg_write(getattr(sys.modules['unicorn.ppc_const'], 'UC_PPC_REG_%d' % r), 0x1000 + r)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(fn, RET)
    for r in range(14, 32):
        assert mu.reg_read(getattr(sys.modules['unicorn.ppc_const'], 'UC_PPC_REG_%d' % r)) == 0x1000 + r, 'r%d clobbered' % r
    assert mu.reg_read(UC_PPC_REG_1) == 0x10480000
    return struct.unpack('>d', struct.pack('>Q', mu.reg_read(UC_PPC_REG_FPR1)))[0]
GET, SET = 0x0200F628, 0x0200F648
def pos(mu, post): return struct.unpack('>fff', mu.mem_read(post + 0x10, 12))
def sets(mu, post): return struct.unpack('>I', mu.mem_read(post + 0x70, 4))[0]

fails = 0
def check(name, got, want):
    global fails
    ok = (abs(got - want) < 1e-3) if not isinstance(want, tuple) else all(abs(a-b) < 1e-3 for a, b in zip(got, want))
    fails += not ok
    print('%-50s got %-28s want %-28s %s' % (name, got, want, 'OK' if ok else 'FAIL'))

F = [(0, 10.0, 5.0, 0.0, 1.0, True), (1, -20.0, 0.0, 1.0, -1.0, True), (2, 13.0, 9.0, 0.0, 1.0, True), (3, 0, 0, 0, 1, False)]
mu, O = setup(F)
wm0, p0 = O[0]; wm1, p1 = O[1]; wm2, p2 = O[2]
check('self X', call(mu, GET, wm0, 0x0F000000), 10)
check('self Y', call(mu, GET, wm0, 0x0F000001), 5)
check('self facing slot1', call(mu, GET, wm1, 0x0F000003), -1)
check('opp X (slot0 -> nearest slot2)', call(mu, GET, wm0, 0x0F000008), 13)
check('opp Y', call(mu, GET, wm0, 0x0F000009), 9)
check('dist', call(mu, GET, wm0, 0x0F00000B), 5)
check('opp rel X fwd (slot0)', call(mu, GET, wm0, 0x0F00000C), 3)
check('opp rel X fwd (slot1 facing left, opp slot0)', call(mu, GET, wm1, 0x0F00000C), -30)
check('self rel Y', call(mu, GET, wm0, 0x0F000011), -4)
check('slot2 X', call(mu, GET, wm0, 0x0F000028), 13)
check('slot1 Z from slot0', call(mu, GET, wm0, 0x0F000026), 1)
check('slot1 facing', call(mu, GET, wm0, 0x0F000027), -1)
check('dead slot3 X', call(mu, GET, wm0, 0x0F00002C), 0)
check('slot beyond', call(mu, GET, wm0, 0x0F00003C), 0)
check('unknown wm self X', call(mu, GET, 0x10399999, 0x0F000000), 0)
check('unknown wm slot0 Y', call(mu, GET, 0x10399999, 0x0F000021), 5)
check('write id read 4', call(mu, GET, wm0, 0x0F000004), 0)
# writes
call(mu, SET, wm0, 0x0F000000, 100.0); check('set self X', pos(mu, p0), (100, 5, 0))
call(mu, SET, wm0, 0x0F000000, 10.0)
call(mu, SET, wm1, 0x0F000004, 3.0); check('move slot1 fwd 3 (facing left)', pos(mu, p1), (-23, 0, 1))
call(mu, SET, wm1, 0x0F000005, 2.0); check('move slot1 up 2', pos(mu, p1), (-23, 2, 1))
call(mu, SET, wm0, 0x0F00000C, 6.0); check('put opp (slot2) 6 in front of slot0', pos(mu, p2), (16, 9, 0))
call(mu, SET, wm0, 0x0F00000D, 0.0); check('put opp Y at self Y', pos(mu, p2), (16, 5, 0))
check('read back opp rel X', call(mu, GET, wm0, 0x0F00000C), 6)
call(mu, SET, wm0, 0x0F000010, -2.0); check('put self 2 behind (fwd) opp', pos(mu, p0), (14, 5, 0))
call(mu, SET, wm0, 0x0F000008, 50.0); check('set opp X', pos(mu, p2), (50, 5, 0))
call(mu, SET, wm0, 0x0F00002A, 7.0); check('set slot2 Z', pos(mu, p2), (50, 5, 7))
n = sets(mu, p2); call(mu, SET, wm0, 0x0F000003, 1.0); call(mu, SET, wm0, 0x0F00000B, 1.0)
check('facing/dist writes ignored (set_pos calls)', sets(mu, p0) + sets(mu, p2) - n, sets(mu, p0))
# fallthrough: other IDs go to the normal paths (need a WM table)
WMX = 0x10390000; mu.mem_write(WMX + 8, struct.pack('>I', WMX + 0x100))
mu.mem_write(WMX + 0x100 + 0x0C, struct.pack('>I', WMX + 0x200))  # cat 3
mu.mem_write(WMX + 0x200 + 4, struct.pack('>I', WMX + 0x300))
mu.mem_write(WMX + 0x300 + 0x16 * 4, struct.pack('>f', 2.5))
mu.mem_write(WMX + 0x100 + 0x3C, struct.pack('>I', WMX + 0x400))  # cat F
mu.mem_write(WMX + 0x400 + 4, struct.pack('>I', WMX + 0x500))
mu.mem_write(WMX + 0x500 + 4 * 0x423, struct.pack(">f", 8.5))
check('stat 0x03000016 normal path', call(mu, GET, WMX, 0x03000016), 2.5)
check('0x0F000423 (index >= 0x400) normal path', call(mu, GET, WMX, 0x0F000423), 8.5)
call(mu, SET, WMX, 0x03000016, 4.0); check('set_float normal path', call(mu, GET, WMX, 0x03000016), 4.0)
call(mu, SET, WMX, 0x0F000423, 1.5); check('set_float cat F index >= 0x400', call(mu, GET, WMX, 0x0F000423), 1.5)
# only self alive
mu, O = setup([(0, 1, 2, 3, 1, True)])
check('no opponent: opp X', call(mu, GET, O[0][0], 0x0F000008), 0)
check('no opponent: dist', call(mu, GET, O[0][0], 0x0F00000B), 0)
call(mu, SET, O[0][0], 0x0F000010, 5.0); check('no opponent: write ignored', pos(mu, O[0][1]), (1, 2, 3))
mu, O = setup([(0, 1, 2, 3, 1, True), (1, 1, 2, 0, 1, True)])
check('same spot: dist 0', call(mu, GET, O[0][0], 0x0F00000B), 0)
mu, O = setup([(0, 0, 0, 0, 1, True), (1, 3000, 4000, 0, 1, True)])
check('far dist', call(mu, GET, O[0][0], 0x0F00000B), 5000)
ADD, SUB, MUL, DIV = 0x0200F73C, 0x0200F764, 0x0200F78C, 0x0200F7B4
mu, O = setup([(0, 10.0, 5.0, 0.0, -1.0, True), (1, 4.0, 1.0, 0.0, 1.0, True)])
w0, p0 = O[0]; w1, p1 = O[1]
call(mu, ADD, w0, 0x0F000000, 2.5); check('add self X', pos(mu, p0), (12.5, 5, 0))
call(mu, SUB, w0, 0x0F000001, 1.0); check('sub self Y', pos(mu, p0), (12.5, 4, 0))
call(mu, MUL, w0, 0x0F000000, 2.0); check('mul self X', pos(mu, p0), (25, 4, 0))
call(mu, DIV, w0, 0x0F000000, 5.0); check('div self X', pos(mu, p0), (5, 4, 0))
call(mu, DIV, w0, 0x0F000000, 0.0); check('div by 0 nothing', pos(mu, p0), (5, 4, 0))
call(mu, ADD, w0, 0x0F000004, 3.0); check('add move fwd (facing left)', pos(mu, p0), (2, 4, 0))
call(mu, ADD, w0, 0x0F00000C, 1.0); check('add opp rel fwd: opp 1 further', pos(mu, p1), (3, 1, 0))
call(mu, ADD, w0, 0x0F000025, 2.0); check('add slot1 Y', pos(mu, p1), (3, 3, 0))
call(mu, ADD, w0, 0x0F000003, 2.0); check('add facing ignored', call(mu, GET, w0, 0x0F000003), -1)
WMX = 0x10390000; mu.mem_write(WMX + 8, struct.pack('>I', WMX + 0x100))
mu.mem_write(WMX + 0x100 + 0x0C, struct.pack('>I', WMX + 0x200))
mu.mem_write(WMX + 0x200 + 4, struct.pack('>I', WMX + 0x300))
mu.mem_write(WMX + 0x300 + 0x10 * 4, struct.pack('>f', 6.0))
call(mu, ADD, WMX, 0x03000010, 1.0); check('normal add', call(mu, GET, WMX, 0x03000010), 7)
call(mu, SUB, WMX, 0x03000010, 3.0); check('normal sub', call(mu, GET, WMX, 0x03000010), 4)
call(mu, MUL, WMX, 0x03000010, 3.0); check('normal mul', call(mu, GET, WMX, 0x03000010), 12)
call(mu, DIV, WMX, 0x03000010, 4.0); check('normal div', call(mu, GET, WMX, 0x03000010), 3)
call(mu, DIV, WMX, 0x03000010, 0.0); check('normal div 0', call(mu, GET, WMX, 0x03000010), 3)
# fighters use their own copies of the WorkModule functions (0x02F1DBE4...): same results through them
FGET, FSET, FADD, FDIV = 0x02F1DBE4, 0x02F1DC04, 0x02F1DCF8, 0x02F1DD70
mu, O = setup([(0, 10.0, 5.0, 0.0, 1.0, True), (1, 13.0, 9.0, 0.0, 1.0, True)])
w0, p0 = O[0]; w1, p1 = O[1]
check('fighter copy: self X', call(mu, FGET, w0, 0x0F000000), 10)
check('fighter copy: opp rel X', call(mu, FGET, w0, 0x0F00000C), 3)
call(mu, FSET, w0, 0x0F00000C, 12.0); check('fighter copy: SET_FLOAT opp 12 in front', pos(mu, p1), (22, 9, 0))
call(mu, FADD, w0, 0x0F000005, 2.0); check('fighter copy: add self Y', pos(mu, p0), (10, 7, 0))
WMX = 0x10390000; mu.mem_write(WMX + 8, struct.pack('>I', WMX + 0x100))
mu.mem_write(WMX + 0x100 + 0x0C, struct.pack('>I', WMX + 0x200))
mu.mem_write(WMX + 0x200 + 4, struct.pack('>I', WMX + 0x300))
mu.mem_write(WMX + 0x300 + 0x10 * 4, struct.pack('>f', 6.0))
check('fighter copy: normal get', call(mu, FGET, WMX, 0x03000010), 6)
call(mu, FSET, WMX, 0x03000010, 9.0); check('fighter copy: normal set', call(mu, FGET, WMX, 0x03000010), 9)
call(mu, FDIV, WMX, 0x03000010, 3.0); check('fighter copy: normal div', call(mu, FGET, WMX, 0x03000010), 3)
# --- hit / status / motion (0x0F0000A0 + 8 * target + quantity) -----------------------------------
def hid(target, q): return 0x0F0000A0 + 8 * target + q
def wf(mu, slot, off, v): mu.mem_write(0x10370000 + slot * 0x1000 + off, struct.pack('>f', v))
def ri(mu, slot, off): return struct.unpack('>i', mu.mem_read(0x10370000 + slot * 0x1000 + off, 4))[0]
def wi(mu, slot, off, v): mu.mem_write(0x10370000 + slot * 0x1000 + off, struct.pack('>i', v))
mu, O = setup([(0, 0.0, 0.0, 0.0, 1.0, True), (1, 30.0, 0.0, 0.0, -1.0, True), (2, 5.0, 2.0, 0.0, 1.0, True)])
w0 = O[0][0]
FGET2, FSET2 = 0x02F1DBE4, 0x02F1DC04
wi(mu, 0, 0xA34, 1); wi(mu, 0, 0xA38, 0)
check('self: attack has connected', call(mu, FGET2, w0, hid(0, 0)), 1)
check('self: connected this frame', call(mu, FGET2, w0, hid(0, 1)), 0)
wi(mu, 2, 0xA34, 0)
check('opp (slot 2): attack has connected', call(mu, FGET2, w0, hid(1, 0)), 0)
check('has connected: writes ignored', (call(mu, FSET2, w0, hid(0, 0), 5.0), ri(mu, 0, 0xA34)), (0, 1))
wi(mu, 2, 0xA1C, 0x45)
check('opp status read', call(mu, FGET2, w0, hid(1, 2)), 0x45)
call(mu, FSET2, w0, hid(1, 2), float(0x59))
check('opp status set (shield break 0x59)', (ri(mu, 2, 0xA1C), ri(mu, 2, 0xA20), ri(mu, 2, 0xA40)), (0x59, 0, 3))
check('  self untouched', ri(mu, 0, 0xA1C), 0)
call(mu, FSET2, w0, hid(4, 2), float(0x1B))
check('slot 2 (target 4) status set', ri(mu, 1, 0xA1C), 0x1B)
wi(mu, 0, 0xA24, 0x211)
check('self motion read', call(mu, FGET2, w0, hid(0, 3)), 0x211)
call(mu, FSET2, w0, hid(1, 3), float(0x7A))
check('opp motion set: kind, frame 0, rate 1', (ri(mu, 2, 0xA24), ri(mu, 2, 0xA28), ri(mu, 2, 0xA2C)), (0x7A, 0, 0x3F800000))
wf(mu, 2, 0xA30, 12.5)
check('opp motion frame read', call(mu, FGET2, w0, hid(1, 4)), 12.5)
check('frame: writes ignored', call(mu, FSET2, w0, hid(1, 4), 3.0), 0)
check('q5-7 read 0', call(mu, FGET2, w0, hid(1, 6)), 0)
check('past the block (0xF8) reads 0', call(mu, FGET2, w0, 0x0F0000F8), 0)
check('combat IDs still work: opp offset Y', call(mu, FGET2, w0, 0x0F00004E), 2)
# --- combat variables (0x0F000040 + 8 * target + quantity) ---------------------------------------
def acc_of(slot): return 0x10370000 + slot * 0x1000
def wint(mu, slot, off, v): mu.mem_write(acc_of(slot) + off, struct.pack('>i', v))
def rint(mu, slot, off): return struct.unpack('>i', mu.mem_read(acc_of(slot) + off, 4))[0]
HS, LA = 0x800 + 0x3E * 4, 0x800 + 0x65 * 4
def cid(target, q): return 0x0F000040 + 8 * target + q
mu, O = setup([(0, 0.0, 0.0, 0.0, 1.0, True), (1, 30.0, 0.0, 0.0, -1.0, True), (2, 5.0, 2.0, 0.0, 1.0, True)])
w0 = O[0][0]
for sl, hs in ((0, 12), (1, 20), (2, 30)): wint(mu, sl, HS, hs)
check('self hitstun left', call(mu, FGET, w0, cid(0, 0)), 12)
check('nearest opp (slot 2) hitstun', call(mu, FGET, w0, cid(1, 0)), 30)
check('slot 2 hitstun (target 4)', call(mu, FGET, w0, cid(4, 0)), 20)
call(mu, FSET, w0, cid(1, 0), 45.0); check('set opp hitstun', rint(mu, 2, HS), 45)
mu.mem_write(acc_of(2) + 0xA00, struct.pack('>f', 33.5))
check('opp hitstun dealt', call(mu, FGET, w0, cid(1, 1)), 33.5)
call(mu, FSET, w0, cid(1, 2), 1.5); check('opp hitstun x1.5 (45 -> 67)', rint(mu, 2, HS), 67)
check('hitstun x reads 0', call(mu, FGET, w0, cid(1, 2)), 0)
wint(mu, 2, 0xA08, 1); check('opp in hitstop', call(mu, FGET, w0, cid(1, 3)), 1)
wint(mu, 2, 0xA04, 9); check('opp hitstop dealt', call(mu, FGET, w0, cid(1, 4)), 9)
call(mu, FSET, w0, cid(1, 3), 7.0)
check('hitstop+shake: frames', rint(mu, 2, 0xA0C), 7); check('hitstop+shake: shake frames', rint(mu, 2, 0xA10), 7)
check('hitstop+shake: intensity 1.0', struct.unpack('>f', mu.mem_read(acc_of(2) + 0xA14, 4))[0], 1.0)
check('hitstop+shake: 6 args', rint(mu, 2, 0xA18), 6)
wint(mu, 2, 0xA10, 0); call(mu, FSET, w0, cid(1, 4), 5.0)
check('hitstop no shake: frames', rint(mu, 2, 0xA0C), 5); check('hitstop no shake: no shake', rint(mu, 2, 0xA10), 0)
call(mu, FADD, w0, cid(0, 0), 3.0); check('ADD to self hitstun (12 -> 15)', rint(mu, 0, HS), 15)
check('opp offset X (fwd)', call(mu, FGET, w0, cid(1, 5)), 5)
check('opp offset Y', call(mu, FGET, w0, cid(1, 6)), 2)
# last fighter hit: hit records of self's AttackModule (slot 1 was hit)
AM, ARR, NODE = acc_of(0) + 0xC00, 0x10398000, 0x10399000
mu.mem_write(acc_of(0) + 0x50, struct.pack('>I', AM))
mu.mem_write(AM + 0x4C, struct.pack('>I', 1)); mu.mem_write(AM + 0x18, struct.pack('>I', 2))
mu.mem_write(AM + 0x14, struct.pack('>I', ARR))
mu.mem_write(ARR + 0x124 + 4, struct.pack('>I', NODE))                 # hitbox 0: one record
mu.mem_write(ARR + 0x174 + 0x128, struct.pack('>I', ARR + 0x174 + 0x124))   # hitbox 1: empty
mu.mem_write(NODE + 0x18, struct.pack('>I', 1 << 16))
check('last hit (record) hitstun', call(mu, FGET, w0, cid(2, 0)), 20)
call(mu, FSET, w0, cid(2, 5), 10.0); check('put last hit 10 in front', pos(mu, O[1][1]), (10, 0, 0))
mu.mem_write(AM + 0x4C, struct.pack('>I', 0))                           # attack over: records off
wint(mu, 1, LA, 3); wint(mu, 2, LA, 0)                                  # slot 2's last attacker = slot 0
check('last hit (fallback) hitstun', call(mu, FGET, w0, cid(2, 0)), 67)
wint(mu, 2, LA, 1)
check('last hit: nobody', call(mu, FGET, w0, cid(2, 0)), 0)
check('index past the end', call(mu, FGET, w0, 0x0F0000A0), 0)
check('position IDs still work: opp X', call(mu, FGET, w0, 0x0F000008), 5)
# hitstun x for the hits of the current move (written before the hit lands)
FSETI = 0x02F1DDCC
def int_table(mu, slot):
    """a WorkModule int table for the fighter in slot (category 0), so set_int's own code works"""
    wm = acc_of(slot) + 0x400; tbl = 0x103A0000 + slot * 0x1000
    mu.mem_write(wm + 8, struct.pack('>I', tbl)); mu.mem_write(tbl, struct.pack('>I', tbl + 0x100))
    mu.mem_write(tbl + 0x100 + 0xC, struct.pack('>I', tbl + 0x200))
    return tbl + 0x200
def seti(mu, slot, value, ident=0x1000003E):
    call(mu, FSETI, acc_of(slot) + 0x400, ident, 0.0)  # r4 is set below
mu, O = setup([(0, 0.0, 0.0, 0.0, 1.0, True), (1, 30.0, 0.0, 0.0, -1.0, True)])
w0, w1 = O[0][0], O[1][0]
ints1 = int_table(mu, 1)
wint(mu, 0, 0xA1C, 0x30)                                 # Kirby's status
AM, ARR, NODE = acc_of(0) + 0xC00, 0x10398000, 0x10399000
mu.mem_write(acc_of(0) + 0x50, struct.pack('>I', AM))
mu.mem_write(AM + 0x4C, struct.pack('>I', 0)); mu.mem_write(AM + 0x18, struct.pack('>I', 1))
mu.mem_write(AM + 0x14, struct.pack('>I', ARR)); mu.mem_write(ARR + 0x128, struct.pack('>I', ARR + 0x124))
call(mu, FSET, w0, cid(2, 2), 10.0)                      # before the hit: no target yet, remembered
def set_int(mu, wm, value, ident):
    mu.mem_write(RET, struct.pack('>I', 0x60000000))
    mu.reg_write(UC_PPC_REG_3, wm); mu.reg_write(UC_PPC_REG_4, value & 0xFFFFFFFF); mu.reg_write(UC_PPC_REG_5, ident)
    mu.reg_write(UC_PPC_REG_1, 0x10480000); mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(FSETI, RET)
def hs1(): return struct.unpack('>i', mu.mem_read(ints1 + 0x3E * 4, 4))[0]
# the hit lands: Kirby's attack records the victim; the victim's MSC sets its hitstun = DamageModuleF(1)
mu.mem_write(AM + 0x4C, struct.pack('>I', 1)); mu.mem_write(ARR + 0x128, struct.pack('>I', NODE))
mu.mem_write(NODE + 0x18, struct.pack('>I', 1 << 16))
mu.mem_write(acc_of(1) + 0xA00, struct.pack('>f', 15.0))
set_int(mu, w1, 15, 0x1000003E); check('hit lands: hitstun 15 x 10', hs1(), 150)
set_int(mu, w1, 20, 0x1000003E); check('later rescale (not the raw hitstun) left alone', hs1(), 20)
set_int(mu, w1, 7, 0x10000040); check('other int IDs untouched', struct.unpack('>i', mu.mem_read(ints1 + 0x40 * 4, 4))[0], 7)
wint(mu, 0, 0xA1C, 0x31)                                 # Kirby is in another move now
set_int(mu, w1, 15, 0x1000003E); check('next move: no multiplier', hs1(), 15)
wint(mu, 0, 0xA1C, 0x30)
set_int(mu, w1, 15, 0x1000003E); check('multiplier was forgotten', hs1(), 15)
wint(mu, 1, HS, 15)                                      # (the stand-in WorkModule's copy of it)
call(mu, FSET, w0, cid(2, 2), 2.0)                       # during the hit: x2 now and for later hits
check('written after the hit: x2 now', rint(mu, 1, HS), 30)
set_int(mu, w1, 15, 0x1000003E); check('and for the next hit of the move', hs1(), 30)
# 0x0F000098: self animation rate multiplier (MotionModule +0xF4 through vtable +0x2FC / +0x304)
MM, MVT, MFN = acc_of(0) + 0xD00, 0x10385000, 0x037FF200
f = Asm(MFN); f.asm('''
 lfs f1, 0xF4(r3)
 blr
 stfs f1, 0xF4(r3)
 blr''')
mu.mem_write(MFN, b''.join(struct.pack('>I', w) for w in f.words()))
mu.mem_write(MVT + 0x2FC, struct.pack('>II', MFN, 0)); mu.mem_write(MVT + 0x304, struct.pack('>I', MFN + 8))
mu.mem_write(MM, struct.pack('>I', MVT)); mu.mem_write(MM + 0xF4, struct.pack('>f', 1.0))
mu.mem_write(acc_of(0) + 0x44, struct.pack('>I', 0))
check('rate x: no MotionModule reads 0', call(mu, FGET, w0, 0x0F000098), 0)
mu.mem_write(acc_of(0) + 0x44, struct.pack('>I', MM))
check('rate x: reads 1.0', call(mu, FGET, w0, 0x0F000098), 1.0)
call(mu, FSET, w0, 0x0F000098, 1.2)
check('rate x: set 1.2', round(struct.unpack('>f', mu.mem_read(MM + 0xF4, 4))[0], 5), 1.2)
check('rate x: other fighter untouched', call(mu, FGET, w1, 0x0F000098), 0)
# --- inputs / state (0x0F000100 + 0x20 * target + q) --------------------------------------------------
def iid(target, q): return 0x0F000100 + 0x20 * target + q
UPDATE = 0x020035FC                      # the game's controller update (hooked)
SRC = 0x103A0000                         # fake pad source: +0x10/+0x14 stick, +0x18 buttons,
SRC_FNS = 0x030B9C00                     # +0x1C/+0x20 triggers, +0x24/+0x28 C-stick
def inp_setup(fighters):
    mu, O = setup(fighters)
    fns = {0x1C: 'blr', 0x24: 'lwz r4, 0x14(r3)\n lwz r3, 0x10(r3)\n blr', 0x34: 'lwz r3, 0x18(r3)\n blr',
           0x3C: 'lwz r4, 0x20(r3)\n lwz r3, 0x1C(r3)\n blr', 0x7C: 'lwz r4, 0x28(r3)\n lwz r3, 0x24(r3)\n blr'}
    mu.mem_write(SRC, struct.pack('>I', SRC + 0x100))
    for k, (off, src) in enumerate(fns.items()):
        f = Asm(SRC_FNS + 0x20 * k); f.asm(src)
        mu.mem_write(SRC_FNS + 0x20 * k, b''.join(struct.pack('>I', w) for w in f.words()))
        mu.mem_write(SRC + 0x100 + off, struct.pack('>I', SRC_FNS + 0x20 * k))
    hm_get = Asm(SRC_FNS + 0x200); hm_get.asm('lwz r3, 4(r3)\n blr')    # HitModule vt +0x10C: state
    mu.mem_write(SRC_FNS + 0x200, b''.join(struct.pack('>I', w) for w in hm_get.words()))
    for slot, *_ in fighters:
        acc = 0x10370000 + slot * 0x1000
        mu.mem_write(acc + 0x24, struct.pack('>I', acc + 0xB00))            # ControlModule
        mu.mem_write(acc + 0xB00 + 0xA0, struct.pack('>I', acc + 0xB10))    # its struct (CM + 0x10)
        mu.mem_write(acc + 0x58, struct.pack('>I', acc + 0xC00))            # HitModule
        mu.mem_write(acc + 0xC00, struct.pack('>I', acc + 0xC80))
        mu.mem_write(acc + 0xC80 + 0x10C, struct.pack('>I', SRC_FNS + 0x200))
        mu.mem_write(acc + 0x54, struct.pack('>I', acc + 0xD00))            # DamageModule
    # the update saves / restores f30 / f31 with Espresso paired-single stores (opcode 4), which
    # Unicorn doesn't run: nops in this copy (only the registers' second halves)
    mu.mem_write(0x02000AE0, struct.pack('>II', 0xFC20082C, 0x4E800020))   # its sqrt: fsqrt f1, f1; blr
    code = mu.mem_read(UPDATE, 0x800)
    for o in range(0, 0x800, 4):
        if code[o] >> 2 == 4:
            mu.mem_write(UPDATE + o, struct.pack('>I', 0x60000000))
    return mu, O
def pad(mu, buttons=0, sx=0.0, sy=0.0, cx=0.0, cy=0.0):
    mu.mem_write(SRC + 0x10, struct.pack('>ffIffff', sx, sy, buttons, 0.0, 0.0, cx, cy))
def update(mu, slot):
    st = 0x10370000 + slot * 0x1000 + 0xB10
    mu.mem_write(RET, struct.pack('>I', 0x60000000))
    mu.reg_write(UC_PPC_REG_3, st); mu.reg_write(UC_PPC_REG_4, SRC); mu.reg_write(UC_PPC_REG_5, 0)
    mu.reg_write(UC_PPC_REG_1, 0x10480000)
    for r in range(14, 32): mu.reg_write(getattr(sys.modules['unicorn.ppc_const'], 'UC_PPC_REG_%d' % r), 0x1000 + r)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(UPDATE, RET)
    for r in range(14, 32):
        assert mu.reg_read(getattr(sys.modules['unicorn.ppc_const'], 'UC_PPC_REG_%d' % r)) == 0x1000 + r, 'r%d clobbered' % r
    assert mu.reg_read(UC_PPC_REG_1) == 0x10480000
def st(mu, slot, off, fmt='>I'):
    return struct.unpack(fmt, mu.mem_read(0x10370000 + slot * 0x1000 + 0xB10 + off, struct.calcsize(fmt)))[0]
mu, O = inp_setup([(0, 0.0, 0.0, 0.0, 1.0, True), (1, 30.0, 0.0, 0.0, -1.0, True)])
w0, w1 = O[0][0], O[1][0]
pad(mu, buttons=0x5, sx=0.5, sy=-0.25)
update(mu, 0)
check('pad read through the hooks: held', st(mu, 0, 0x3C), 0x5)
check('ATTACK held', call(mu, FGET, w0, iid(0, 0)), 1)
check('SPECIAL held', call(mu, FGET, w0, iid(0, 1)), 0)
check('JUMP held', call(mu, FGET, w0, iid(0, 2)), 1)
check('JUMP pressed this frame', call(mu, FGET, w0, iid(0, 10)), 1)
update(mu, 0)
check('JUMP pressed: not on the 2nd frame', call(mu, FGET, w0, iid(0, 10)), 0)
check('STICK_X (facing right)', call(mu, FGET, w0, iid(0, 0x10)), 0.5)
check('STICK_Y', call(mu, FGET, w0, iid(0, 0x11)), -0.25)
pad(mu)
call(mu, FSET, w0, iid(0, 3), 1.0)             # hold shield
update(mu, 0)
check('forced SHIELD held', st(mu, 0, 0x3C), 0x8)
check('forced SHIELD pressed', st(mu, 0, 0x48), 0x8)
update(mu, 0)
check('forced SHIELD still held', st(mu, 0, 0x3C), 0x8)
call(mu, FSET, w0, iid(0, 1), 2.0)             # tap special
update(mu, 0)
check('tap SPECIAL: held this update', st(mu, 0, 0x3C), 0xA)
update(mu, 0)
check('tap SPECIAL: gone next update', st(mu, 0, 0x3C), 0x8)
call(mu, FSET, w0, iid(0, 3), 0.0)
update(mu, 0)
check('SHIELD let go', st(mu, 0, 0x3C), 0)
check('SHIELD released bit', st(mu, 0, 0x4C) & 0x8, 0x8)
call(mu, FSET, w0, iid(0, 6), 1.0)             # side taunt
update(mu, 0)
check('forced side taunt = right d-pad', st(mu, 0, 0x3C), 0x4000)
check('side taunt read', call(mu, FGET, w0, iid(0, 6)), 1)
call(mu, FSET, w0, iid(0, 6), 0.0)
call(mu, FSET, w1, iid(0, 0x10), 0.8)          # slot 1 (facing left): stick 0.8 forward
call(mu, FSET, w1, iid(0, 0x13), 1.0)          # C-stick up
pad(mu, sx=0.3, cx=0.2)
update(mu, 1)
check('forced stick X along the facing (raw)', st(mu, 1, 0, '>f'), -0.8)
check('forced stick: STICK_X reads 0.8', call(mu, FGET, w1, iid(0, 0x10)), 0.8)
check('forced C-stick Y', st(mu, 1, 0x80, '>f'), 1.0)
check('sticks forced flag', call(mu, FGET, w1, iid(0, 0x14)), 1)
check('slot 0 not forced', (update(mu, 0), st(mu, 0, 0, '>f'))[1], 0.3)
call(mu, FSET, w1, iid(0, 0x14), 0.0)          # let go
update(mu, 1)
check('let go: pad stick again', st(mu, 1, 0, '>f'), 0.3)
check('opponent of slot 0 = slot 1: its STICK_X fwd', call(mu, FGET, w0, iid(1, 0x10)), -0.3)
call(mu, FSET, w0, iid(1, 0x15), 1.0)          # turn the opponent's inputs off
pad(mu, buttons=0x1, sx=0.9, cx=0.9)
update(mu, 1)
check('inputs off: no buttons', st(mu, 1, 0x3C), 0)
check('inputs off: no stick', st(mu, 1, 0, '>f'), 0.0)
check('inputs off: no C-stick', st(mu, 1, 0x7C, '>f'), 0.0)
check('inputs off read', call(mu, FGET, w1, iid(0, 0x15)), 1)
call(mu, FSET, w0, iid(1, 2), 1.0)             # ... but forced jump still goes through
update(mu, 1)
check('inputs off + forced JUMP', st(mu, 1, 0x3C), 0x4)
wi(mu, 1, 0xA1C, 0xB1)                         # KO'd: everything forgotten
update(mu, 1)
check('KO clears: pad buttons back', st(mu, 1, 0x3C), 0x1)
check('KO clears: inputs on', call(mu, FGET, w1, iid(0, 0x15)), 0)
wi(mu, 1, 0xA1C, 0)
# state
wi(mu, 0, 0xA48, 2)
check('SITUATION air', call(mu, FGET, w0, iid(0, 0x16)), 2)
call(mu, FSET, w0, iid(0, 0x16), 0.0); check('set SITUATION ground', ri(mu, 0, 0xA48), 0)
wf(mu, 0, 0xA4C, 42.5)
check('DAMAGE', call(mu, FGET, w0, iid(0, 0x17)), 42.5)
call(mu, FSET, w0, iid(0, 0x17), 100.0); check('set DAMAGE 100', call(mu, FGET, w0, iid(0, 0x17)), 100)
call(mu, FADD, w0, iid(0, 0x17), 5.0); check('add DAMAGE 5', call(mu, FGET, w0, iid(0, 0x17)), 105)
wi(mu, 0, 0x804, 1); wi(mu, 0, 0x808, 2)
check('JUMPS_USED', call(mu, FGET, w0, iid(0, 0x18)), 1)
check('JUMPS_MAX', call(mu, FGET, w0, iid(0, 0x19)), 2)
call(mu, FSET, w0, iid(0, 0x18), 0.0); check('give the jump back', ri(mu, 0, 0x804), 0)
wf(mu, 0, 0x80C, 50.0)
check('SHIELD health', call(mu, FGET, w0, iid(0, 0x1A)), 50)
call(mu, FSET, w0, iid(0, 0x1A), 10.0); check('set SHIELD health', call(mu, FGET, w0, iid(0, 0x1A)), 10)
wi(mu, 0, 0xC04, 2)
check('INTANGIBLE body state', call(mu, FGET, w0, iid(0, 0x1B)), 2)
check('INVINCIBLE (state 2): 0', call(mu, FGET, w0, iid(0, 0x1C)), 0)
call(mu, FSET, w0, iid(0, 0x1B), 30.0); check('intangible 30 frames', ri(mu, 0, 0xA5C), 30)
call(mu, FSET, w0, iid(0, 0x1C), 12.0); check('invincible 12 frames', ri(mu, 0, 0xA60), 12)
wi(mu, 0, 0xD14, 3); wf(mu, 0, 0xD1C, 20.0)
check('ARMOR type', call(mu, FGET, w0, iid(0, 0x1D)), 3)
check('ARMOR threshold (damage)', call(mu, FGET, w0, iid(0, 0x1E)), 20)
call(mu, FSET, w0, iid(0, 0x1E), 15.0); call(mu, FSET, w0, iid(0, 0x1D), 2.0)
check('ARMOR set knockback, 15', (ri(mu, 0, 0xD14), struct.unpack('>f', mu.mem_read(0x10370000 + 0xD18, 4))[0]), (2, 15))
check('ARMOR set 1 (super armor)', (call(mu, FSET, w0, iid(0, 0x1D), 1.0), ri(mu, 0, 0xD14))[1], 1)
check('q 0x1F: 0', call(mu, FGET, w0, iid(0, 0x1F)), 0)
def rid(target, n): return 0x0F000260 + 2 * target + n
pad(mu, sx=0.4, cx=-0.6)
update(mu, 1)
check('raw STICK_X (slot 1 facing left): screen +0.4', call(mu, FGET, w1, rid(0, 0)), 0.4)
check('STICK_X along the facing: -0.4', call(mu, FGET, w1, iid(0, 0x10)), -0.4)
check('raw CSTICK_X', call(mu, FGET, w1, rid(0, 1)), -0.6)
check('opponent raw STICK_X', call(mu, FGET, w0, rid(1, 0)), 0.4)
call(mu, FSET, w1, rid(0, 0), 0.9)             # force: 0.9 to the right on screen
update(mu, 1)
check('forced raw X lands raw', st(mu, 1, 0, '>f'), 0.9)
call(mu, FSET, w1, iid(0, 0x14), 0.0)
check('raw past the end: 0', call(mu, FGET, w0, 0x0F000276), 0)
check('slot 3 (empty): 0', call(mu, FGET, w0, iid(6, 0)), 0)
check('target past the end: 0', call(mu, FGET, w0, 0x0F000280), 0)
check('position IDs still fine', call(mu, FGET, w0, 0x0F00000C), 30)
print('FAILS', fails)
sys.exit(1 if fails else 0)
