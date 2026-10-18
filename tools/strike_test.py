#!/usr/bin/env python3
"""Emulator test (Unicorn) for tools/strike_cave.py: runs the cave's two hooks on fake objects.
    python3 tools/strike_test.py"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strike_cave as S
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import *

a, words = S.assemble()
fails = 0


def check(name, got, want):
    global fails
    ok = abs(got - want) < 1e-4 if isinstance(want, float) else got == want
    fails += not ok
    print("%-48s got %-14r want %-14r %s" % (name, got, want, "OK" if ok else "FAIL"))


def fresh():
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(0x04B70000, 0x10000)
    mu.mem_write(S.CAVE, b"".join(struct.pack(">I", w) for w in words))
    mu.mem_map(0x02C00000, 0x40000)
    mu.mem_map(0x10100000, 0x10000)
    mu.mem_write(0x10105D98, struct.pack(">f", 0.0))
    mu.mem_map(0x10400000, 0x100000)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    return mu


def fighter(mu, base, kind_id, marker):
    """object at base: +0 ID, +0xC accessor; accessor +0x28 WorkModule with int 0x8E = marker"""
    acc, wm, tbl, cat1, ints = base + 0x100, base + 0x200, base + 0x300, base + 0x400, base + 0x500
    mu.mem_write(base, struct.pack(">I", kind_id))
    mu.mem_write(base + 0xC, struct.pack(">I", acc))
    mu.mem_write(acc + 0x28, struct.pack(">I", wm))
    mu.mem_write(wm + 8, struct.pack(">I", tbl))
    mu.mem_write(tbl + 4, struct.pack(">I", cat1))
    mu.mem_write(cat1 + 8, struct.pack(">I", 0xC0))
    mu.mem_write(cat1 + 0xC, struct.pack(">I", ints))
    mu.mem_write(ints + 0x8E * 4, struct.pack(">I", marker))
    return acc


def run_atk(mu, obj, damage, hitlag):
    am, slot = 0x10480000, 0x10481000
    mu.mem_write(am, struct.pack(">I", 0x1234))
    mu.mem_write(am + 4, struct.pack(">I", obj))
    mu.mem_write(slot + 0x18, struct.pack(">f", damage))
    mu.mem_write(slot + 0x34, struct.pack(">f", hitlag))
    mu.reg_write(UC_PPC_REG_26, slot)
    mu.reg_write(UC_PPC_REG_28, am)
    mu.emu_start(a.labels["strike_atk"], S.HOOK_ATK + 4)
    check("  (set_attack's own lwz r8, 0(r28))", mu.reg_read(UC_PPC_REG_8), 0x1234)
    return (struct.unpack(">f", mu.mem_read(slot + 0x18, 4))[0], struct.unpack(">f", mu.mem_read(slot + 0x34, 4))[0])


def run_hs(mu, acc, side, damage, mult=1.0, kb=1.0):
    hit = 0x10490000
    mu.mem_write(hit + 0xC, struct.pack(">f", damage))
    mu.mem_write(hit + 0x10, struct.pack(">f", kb))
    for r, v in ((3, 0x777), (4, acc), (5, hit), (6, side), (1, 0x104F0000)):
        mu.reg_write(getattr(sys.modules["unicorn.ppc_const"], "UC_PPC_REG_%d" % r), v)
    mu.reg_write(UC_PPC_REG_FPR1, struct.unpack(">Q", struct.pack(">d", mult))[0])
    mu.reg_write(UC_PPC_REG_LR, 0x02C30000)
    stops = {S.CALC_HITLAG: "calc", S.HOOK_HS + 4: "orig", 0x02C30000: "ret"}
    for addr in stops:
        mu.mem_write(addr, struct.pack(">I", 0x48000000))     # b . (stop points)
    mu.emu_start(a.labels["strike_hs"], 0, count=200)
    pc = mu.reg_read(UC_PPC_REG_PC)
    f = lambda n: struct.unpack(">d", struct.pack(">Q", mu.reg_read(getattr(sys.modules["unicorn.ppc_const"], "UC_PPC_REG_FPR%d" % n))))[0]
    return stops.get(pc, hex(pc)), f(1), f(2), mu.reg_read(UC_PPC_REG_4), mu.reg_read(UC_PPC_REG_5), mu.reg_read(UC_PPC_REG_6), mu.reg_read(UC_PPC_REG_11)


STRIKE, RUSH, NONE = 0x4B490008, 0x4B490001, 0x4B490000
# --- hitboxes ---
mu = fresh()
kirby = 0x10400000
fighter(mu, kirby, 0x00000003, STRIKE)
d, h = run_atk(mu, kirby, 10.0, 1.0)
check("Strike Kirby hitbox: damage 10 -> 11.5", d, 11.5)
check("Strike Kirby hitbox: hitlag mult 1 -> 1.2", h, 1.2)
d, h = run_atk(mu, kirby, 4.0, 1.5)
check("Strike: 4 dmg / 1.5 hitlag -> 4.6 / 1.8", (round(d, 4), round(h, 4)), (4.6, 1.8))
fighter(mu, kirby, 0x00000003, RUSH)
check("Rush Kirby: unchanged", run_atk(mu, kirby, 10.0, 1.0), (10.0, 1.0))
fighter(mu, kirby, 0x00000003, 0x4B49000A)            # Strike bit + stat profile 2
check("Strike bit with a stat profile: scaled", tuple(round(x, 4) for x in run_atk(mu, kirby, 10.0, 1.0)), (11.5, 1.2))
fighter(mu, kirby, 0x00000003, 0x12340008)
check("other fighter (no KI marker): unchanged", run_atk(mu, kirby, 10.0, 1.0), (10.0, 1.0))
fighter(mu, kirby, 0x10000003, STRIKE)               # a weapon (ID category 1) with the marker
check("weapon / projectile: unchanged", run_atk(mu, kirby, 10.0, 1.0), (10.0, 1.0))
check("no owner (0): unchanged", run_atk(mu, 0, 10.0, 1.0), (10.0, 1.0))
check("bad owner pointer: unchanged", run_atk(mu, 0x02000001, 10.0, 1.0), (10.0, 1.0))
# --- hitstop ---
mu = fresh()
acc = fighter(mu, kirby, 3, STRIKE)
r = run_hs(mu, acc, 1, 11.5, 1.0)
check("Strike Kirby attacker: goes to calc_hitlag", r[0], "calc")
check("  damage 11.5 -> 10 (x bias)", round(r[1], 3), 10.0)
check("  mult 1 -> 1/1.2", round(r[2], 5), round(1 / 1.2, 5))
check("  r4 = hit + 0x44, r5 = side 1, r6 = 1", (r[3], r[4], r[5]), (0x10490044, 1, 1))
check("  damage x bias stays >= the original", r[1] >= 10.0, True)
r = run_hs(mu, acc, 0, 11.5, 1.0)
check("Strike Kirby as victim: original path", (r[0], r[6]), ("orig", 0x10490000))
r = run_hs(mu, acc, 1, 11.5, 1.0, kb=0.0)
check("Strike attacker, no-hitstop hit: returns 0", (r[0], mu.reg_read(UC_PPC_REG_3)), ("ret", 0))
acc = fighter(mu, kirby, 3, RUSH)
r = run_hs(mu, acc, 1, 11.5, 1.0)
check("Rush Kirby attacker: original path", r[0], "orig")
r = run_hs(mu, 0x02000000, 1, 11.5, 1.0)
check("bad accessor: original path", r[0], "orig")
# the frames: Strike Kirby's own hitstop = the game's formula with the original damage
for dmg in (1.0, 3.0, 7.0, 10.0, 13.0, 20.0, 26.0):
    scaled = struct.unpack(">f", struct.pack(">f", dmg * 1.15))[0]
    mult = struct.unpack(">f", struct.pack(">f", 1.2))[0]
    acc = fighter(mu, kirby, 3, STRIKE)
    r = run_hs(mu, acc, 1, scaled, 1.0)
    f = lambda x: struct.unpack(">f", struct.pack(">f", x))[0]
    own = int(min(f(f(r[1] * f(0.3846154)) + 5) * f(r[2] * mult), 30))
    check("self hitstop, %g dmg: vanilla frames" % dmg, own, int(min((dmg * 0.3846154 + 5), 30)))
# --- critical hits (marker bit 0x10, set by the MSC during a smash attack that rolled a crit) ---
CRIT = STRIKE | 0x10
mu = fresh()
fighter(mu, kirby, 3, CRIT)
check("crit hitbox: damage 10 -> 23", tuple(round(x, 4) for x in run_atk(mu, kirby, 10.0, 1.0)), (23.0, 2.4))
fighter(mu, kirby, 3, 0x4B490010)
check("crit bit without Strike: unchanged", run_atk(mu, kirby, 10.0, 1.0), (10.0, 1.0))
for dmg in (3.0, 10.0, 14.0, 18.0):
    scaled = struct.unpack(">f", struct.pack(">f", struct.unpack(">f", struct.pack(">f", dmg * 1.15))[0] * 2))[0]
    mult = struct.unpack(">f", struct.pack(">f", struct.unpack(">f", struct.pack(">f", 1.2))[0] * 2))[0]
    acc = fighter(mu, kirby, 3, CRIT)
    r = run_hs(mu, acc, 1, scaled, 1.0)
    f = lambda x: struct.unpack(">f", struct.pack(">f", x))[0]
    own = int(min(f(f(r[1] * f(0.3846154)) + 5) * f(r[2] * mult), 30))
    check("crit self hitstop, %g dmg: 2x the normal" % dmg, own, int(min((dmg * 0.3846154 + 5) * 2, 30)))


# --- throws ---
def run_throw(mu, obj, damage):
    am, sp = 0x10480000, 0x104E0000
    mu.mem_write(am, struct.pack(">I", 0x5678))
    mu.mem_write(am + 4, struct.pack(">I", obj))
    mu.mem_write(sp + 0x78, struct.pack(">f", damage))
    mu.reg_write(UC_PPC_REG_30, am)
    mu.reg_write(UC_PPC_REG_1, sp)
    mu.reg_write(UC_PPC_REG_4, 0x44)
    mu.reg_write(UC_PPC_REG_5, 0x55)
    mu.emu_start(a.labels["strike_throw"], S.HOOK_THROW + 4)
    check("  (handler's own lwz r12, 0(r30); r4 / r5 kept)", (mu.reg_read(UC_PPC_REG_12), mu.reg_read(UC_PPC_REG_4), mu.reg_read(UC_PPC_REG_5)), (0x5678, 0x44, 0x55))
    return round(struct.unpack(">f", mu.mem_read(sp + 0x78, 4))[0], 4)


mu = fresh()
fighter(mu, kirby, 3, STRIKE)
check("Strike Kirby throw: 10 -> 11.5", run_throw(mu, kirby, 10.0), 11.5)
fighter(mu, kirby, 3, CRIT)
check("throw during a crit: x1.15 only", run_throw(mu, kirby, 8.0), 9.2)
fighter(mu, kirby, 3, RUSH)
check("Rush Kirby throw: unchanged", run_throw(mu, kirby, 10.0), 10.0)
fighter(mu, kirby, 0x10000003, STRIKE)
check("weapon throw data: unchanged", run_throw(mu, kirby, 10.0), 10.0)
check("bad owner: unchanged", run_throw(mu, 0x7, 10.0), 10.0)
print("FAILS", fails)
sys.exit(1 if fails else 0)
