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
    0x030B2FC4: "lwz r12, 4(r3)\n lwz r3, 0xA00(r12)\n blr",
    0x030B2F8C: "lwz r12, 4(r3)\n lwz r3, 0xA04(r12)\n blr",
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
    mu.mem_map(0x04B70000, 0x10000); mu.mem_write(0x04B70000, mem(0x04B70000, 0x9000))  # combat variables (grown .text)
    mu.mem_map(0x030B0000, 0x10000)
    for addr, src in FAKES.items():
        f = Asm(addr); f.asm(src)
        mu.mem_write(addr, b''.join(struct.pack('>I', w) for w in f.words()))
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
mu.mem_write(WMX + 0x500 + 4 * 0x123, struct.pack('>f', 8.5))
check('stat 0x03000016 normal path', call(mu, GET, WMX, 0x03000016), 2.5)
check('0x0F000123 (index >= 0x100) normal path', call(mu, GET, WMX, 0x0F000123), 8.5)
call(mu, SET, WMX, 0x03000016, 4.0); check('set_float normal path', call(mu, GET, WMX, 0x03000016), 4.0)
call(mu, SET, WMX, 0x0F000123, 1.5); check('set_float cat F index >= 0x100', call(mu, GET, WMX, 0x0F000123), 1.5)
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
print('FAILS', fails)
sys.exit(1 if fails else 0)
