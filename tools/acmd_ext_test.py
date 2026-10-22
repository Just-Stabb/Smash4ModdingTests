#!/usr/bin/env python3
"""Tests tools/acmd_ext_cave.py in a patched RPX (unicorn): the game's own ACMD loader / interpreter
code with the new commands.

  python3 tools/acmd_ext_test.py PATCHED.rpx ORIGINAL.rpx

- the hook sites held the expected instructions in the original;
- the CRC lookup 0x02BEE154: every vanilla command gives its old index, the new ones NEW_BASE + k,
  an unknown CRC -1;
- both loader loops (0x02BEE2B4, 0x02BEE3B4) over a script mixing vanilla and new commands: every
  CRC replaced by its index and the step over each command = its size;
- the interpreter's handler read (0x02BEE84C): vanilla indices give the old handlers (r12 kept), new
  ones the cave's;
- hit time: find_copy finds the extras from a copy of the slot's data (the hit info's +0x44); the
  hitstun hook multiplies f28 and keeps the DI x for the victim's WorkModule, which the max DI angle
  read (0x0200011A, through the real get_float with the other caves' hooks) then returns multiplied;
  the victim / attacker hitstop hooks; untagged hits change nothing (and reset the victim's DI x);
- objects: user variables / timers / kinetic type / speed through the real get_float / set_float
  (0x0F000300+, via position_vars_cave.py's hooks and the var_entry gate), the per-frame hook counting
  timers down, the set-up hook forgetting an object, Track_Target steering a weapon (owner skipped,
  instant and 45-degree turns, range) and a fighter (kinetic ops logged by a stub wrapper);
- the Extra handlers (base handler stubbed: steps over its own size like the real ones): the script
  moves over base + extra words, the extras are recorded for the slot (multipliers <= 0 -> 1.0),
  ext_find finds them from the slot's data, not after the slot is rewritten, not when skipped.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import rpx_patch as R  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_19, UC_PPC_REG_20, UC_PPC_REG_27, UC_PPC_REG_FPR1, UC_PPC_REG_FPR28,
                               UC_PPC_REG_7, UC_PPC_REG_0, UC_PPC_REG_12, UC_PPC_REG_28, UC_PPC_REG_29,
                               UC_PPC_REG_30, UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0
CRC_TABLE, COUNT, SIZES, HANDLERS = 0x100FAAB8, 584, 0x100FA198, 0x10350ED8
BUF = 0x7F004000


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def run(mu, start, stop, regs, count=200000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on
    mu.emu_start(start, stop, count=count)


def f2bits(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def hit_tests(pm, om, a, slot, acc):
    """slot: an Extra hitbox's slot (recorded by the handler tests, extras 2.0, 3.0, 0, 1.0, 4, 1.0)"""
    for at, w in C.HIT_ORIG.items():
        check('original word at 0x%08X' % at, r32(om, at), w)
    hi, rec, stack, wm, cats = 0x10376000, 0x10377000, 0x7F00E000, 0x10378000, 0x10379000
    # an Extra hitbox's data in a hit info, extras: hitstun 1.5, hitstop x2, self x1 / 6 frames, DI 0.5
    pm.mem_write(slot + C.TAG_OFF, b'\0\0')
    w32(pm, 0x10373000 + 4, 0x1000)
    ext_vals = [1.5, 2.0, 0, 1.0, 6, 0.5]

    def record(vals):
        w32(pm, 0x10375000, 3)
        nb = C.COMMANDS[0][1] - C.N_EXTRA
        for i, v in enumerate(vals):
            pm.mem_write(0x10375000 + 4 * (nb - 1) + 4 * i, struct.pack('>f' if i in (0, 1, 3, 5) else '>i', v))
        w32(pm, 0x10373000 + 8, -1)
        pm.mem_write(0x10374000 + 8, b'\1')
        run(pm, a.addr(C.COMMANDS[0][2]), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: 0x10373000, UC_PPC_REG_6: 0x10374000,
                                                 UC_PPC_REG_7: 0x10375000})
    record(ext_vals)
    pm.mem_write(hi + 0x44, bytes(pm.mem_read(slot, 0x68)))
    run(pm, a.addr('find_copy'), RET, {UC_PPC_REG_5: hi + 0x44})
    e = pm.reg_read(UC_PPC_REG_5)
    check('find_copy: the copy finds its extras', e != 0, True)
    plain = 0x1037A000
    pm.mem_write(plain + 0x44, bytes(pm.mem_read(slot, 0x68)))
    w32(pm, plain + 0x44 + 0x28, r32(pm, plain + 0x44 + 0x28) + 1)      # another hitbox (FKB differs)
    run(pm, a.addr('find_copy'), RET, {UC_PPC_REG_5: plain + 0x44})
    check('find_copy: other data -> 0', pm.reg_read(UC_PPC_REG_5), 0)

    # victim WorkModule with a category-2 float 0x11A = 18.0 (max DI angle) and a category-3 stat
    w32(pm, acc + 0x28, wm)
    w32(pm, wm + 8, cats)
    for cat, (arr, idx, val) in {2: (0x1037B000, 0x11A, 18.0), 3: (0x1037C000, 0x16, 1.1)}.items():
        w32(pm, cats + cat * 4, cats + 0x100 + cat * 0x10)
        w32(pm, cats + 0x100 + cat * 0x10 + 4, arr)
        pm.mem_write(arr + idx * 4, struct.pack('>f', val))
    w32(pm, cats, 0)                                                    # no category 0 ints (not Kirby)

    def get_float(ident):
        run(pm, 0x02F1DBE4, RET, {UC_PPC_REG_3: wm, UC_PPC_REG_4: ident})
        return round(struct.unpack('>d', struct.pack('>Q', pm.reg_read(UC_PPC_REG_FPR1)))[0], 4)
    check('get_float max DI angle before any hit', get_float(0x0200011A), 18.0)

    def stun(info, kb_hitstun):
        pm.reg_write(UC_PPC_REG_FPR28, f2bits(kb_hitstun))
        run(pm, C.HIT_STUN, C.HIT_STUN + 4, {UC_PPC_REG_27: acc, 28 + UC_PPC_REG_27 - 27: info, 30 + UC_PPC_REG_27 - 27: rec})
        return round(struct.unpack('>f', pm.mem_read(rec + 0x30, 4))[0], 4)
    check('hitstun x1.5 stored (DamageModuleF(1))', stun(hi, 20.0), 30.0)
    check('get_float max DI angle x0.5 after it', get_float(0x0200011A), 9.0)
    check('get_float fighter stat unchanged', get_float(0x03000016), 1.1)
    check('untagged hit: hitstun unchanged', stun(plain, 20.0), 20.0)
    check('untagged hit resets DI x', get_float(0x0200011A), 18.0)

    def vstop(info, frames):
        run(pm, C.HIT_VSTOP, C.HIT_VSTOP + 4, {UC_PPC_REG_20: frames, UC_PPC_REG_19: 2, 28 + UC_PPC_REG_27 - 27: info})
        return pm.reg_read(UC_PPC_REG_20)
    check('victim hitstop x2', vstop(hi, 7), 14)
    check('victim hitstop untagged', vstop(plain, 7), 7)

    def amul(info, frames):
        run(pm, C.HIT_AMUL, C.HIT_AMUL + 4, {UC_PPC_REG_3: frames, 30 + UC_PPC_REG_27 - 27: info})
        return pm.reg_read(UC_PPC_REG_27), pm.reg_read(UC_PPC_REG_3)

    def afix(info, frames):
        w32(pm, stack + 0x10, frames)
        run(pm, C.HIT_AFIX, C.HIT_AFIX + 4, {UC_PPC_REG_1: stack, 30 + UC_PPC_REG_27 - 27: info})
        return pm.reg_read(UC_PPC_REG_27)
    check('self hitstop: x1 before the rate', amul(hi, 7), (7, 7))
    check('self hitstop: 0 computed -> 1 (fixed frames set)', amul(hi, 0), (1, 1))
    check('self hitstop: 6 frames after the rate', afix(hi, 9), 6)
    check('self hitstop untagged', (amul(plain, 7), afix(plain, 9)), ((7, 7), 9))
    record([1.0, 0.5, 20, 3.0, 0, 1.0])
    pm.mem_write(hi + 0x44, bytes(pm.mem_read(slot, 0x68)))
    check('victim hitstop frames 20 replace', vstop(hi, 7), 20)
    check('self hitstop x3', amul(hi, 5), (15, 15))
    check('self hitstop: no fixed frames', afix(hi, 9), 9)


def fcall(mu, fn, wm, ident, val=0.0):
    """get_float / set_float(r3 WorkModule, r4 ID, f1): callee-saved registers must survive"""
    mu.reg_write(UC_PPC_REG_3, wm)
    mu.reg_write(UC_PPC_REG_4, ident)
    mu.reg_write(UC_PPC_REG_FPR1, f2bits(val))
    for r in range(14, 32):
        mu.reg_write(UC_PPC_REG_3 + r - 3, 0x1000 + r)
    run(mu, fn, RET, {UC_PPC_REG_3: wm, UC_PPC_REG_4: ident})
    bad = [r for r in range(14, 32) if mu.reg_read(UC_PPC_REG_3 + r - 3) != 0x1000 + r]
    assert not bad, 'clobbered r%s' % bad
    return round(struct.unpack('>d', struct.pack('>Q', mu.reg_read(UC_PPC_REG_FPR1)))[0], 4)


def obj_tests(pm, om, a):
    from ppcasm import Asm
    for at, w in C.OBJ_ORIG.items():
        check('original word at 0x%08X' % at, r32(om, at), w)
    FGET, FSET = 0x02F1DBE4, 0x02F1DC04
    pm.mem_map(0x7E000000, 0x10000)
    stubs = Asm(0x7E000000)
    stubs.asm("""
set_kind:                       # KineticModule vt +0xEC(km, type)
        stw r4, 0x11C(r3)
        blr
speed_sum:                      # vt +0xA4(km, mask) -> r3 x, r4 y bits
        lwz r4, 0x204(r3)
        lwz r3, 0x200(r3)
        blr
energy:                         # vt +0x54(km, id) -> energy
        addi r3, r3, 0x300
        blr
has_link:                       # LinkModule vt +0x5C
        li r3, 1
        blr
link_id:                        # vt +0x6C -> the owner's object ID
        lis r3, 0x7E00
        lwz r3, 0x1F00(r3)
        blr
wrapper:                        # MSC module wrapper(ctx, {words, n}): log [n, words...] at 0x7E002000+
        lis r11, 0x7E00
        lwz r12, 0x1FF0(r11)
        lwz r10, 4(r4)
        stw r10, 0(r12)
        lwz r9, 0(r4)
wr_l:
        addi r12, r12, 4
        lwz r0, 0(r9)
        stw r0, 0(r12)
        addi r9, r9, 4
        addi r10, r10, -1
        cmpwi r10, 0
        bne wr_l
        addi r12, r12, 4
        stw r12, 0x1FF0(r11)
        blr
""")
    for i, w in enumerate(stubs.words()):
        w32(pm, 0x7E000000 + 4 * i, w)
    # the game's wrappers -> the logging stub
    wa = stubs.addr('wrapper')
    for wrap in (C.KINETIC_W, C.POSTURE_W):                 # lis r12 / ori r12 / mtctr r12 / bctr
        for i, wd in enumerate([0x3D800000 | (wa >> 16), 0x618C0000 | (wa & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, wrap + 4 * i, wd)
    # objects: accessor +0x18 posture, +0x28 WorkModule, +0x34 KineticModule, +0x68 LinkModule
    def obj(base, x, y):
        acc, post, wm, km, lm, vt = base, base + 0x100, base + 0x200, base + 0x400, base + 0x800, base + 0x900
        w32(pm, acc + 0x18, post)
        w32(pm, acc + 0x28, wm)
        w32(pm, acc + 0x34, km)
        w32(pm, acc + 0x68, lm)
        w32(pm, acc + 0x6C, base + 0xA00)                 # owner module: +0x34 current owner's ID
        pm.mem_write(post + 0x10, struct.pack('>ff', x, y))
        pm.mem_write(post + 0x60, struct.pack('>f', 1.0))
        w32(pm, km, vt)
        w32(pm, lm, vt + 0x100)
        for off, lab in ((0xEC, 'set_kind'), (0xA4, 'speed_sum'), (0x54, 'energy')):
            w32(pm, vt + off, stubs.addr(lab))
        w32(pm, vt + 0x100 + 0x5C, stubs.addr('has_link'))
        w32(pm, vt + 0x100 + 0x6C, stubs.addr('link_id'))
        return acc, wm, km
    me, me_wm, me_km = obj(0x10380000, 0.0, 0.0)          # a weapon
    own, own_wm, _ = obj(0x10381000, 0.0, -3.0)          # its owner (nearest, but skipped)
    foe, foe_wm, foe_km = obj(0x10382000, 0.0, 10.0)
    mm = 0x10383000                                       # MotionModule: +4 accessor

    def frame(acc):
        w32(pm, mm + 4, acc)
        regs = {UC_PPC_REG_3 + 31 - 3: mm}
        run(pm, C.FRAME_HOOK, C.FRAME_HOOK + 4, regs)
        check('frame hook keeps r31 / r0 = 1', (pm.reg_read(UC_PPC_REG_3 + 28), pm.reg_read(UC_PPC_REG_0)), (mm, 1)) if acc == me else None
    # fighter table: [[FIGHTERS]] = {entries, ?, count}; entries: owner (ID 0x10000), foe (ID 0x20000)
    tab, ents = 0x10384000, 0x10386000
    w32(pm, C.FIGHTERS, tab)
    w32(pm, tab, tab + 0x10)
    w32(pm, tab + 0x10, ents)
    w32(pm, tab + 0x18, 2)
    pm.mem_write(ents, b'\0' * (2 * C.FIGHTER_ENTRY))
    for k, (ident, acc) in enumerate(((0x10000, own), (0x20000, foe))):
        e = ents + k * C.FIGHTER_ENTRY
        w32(pm, e, ident)
        w32(pm, e + 0xC, acc)
        pm.mem_write(e + 0x1E, b'\4')
    w32(pm, 0x7E001F00, 0x10000)                          # the weapon's owner: entry 0
    w32(pm, me + 0xA00 + 0x34, 0x10000)                   # not reflected: current owner = link 0's

    V = lambda i: 0x0F000300 + i                          # noqa: E731
    check('user var unset -> 0', fcall(pm, FGET, me_wm, V(5)), 0.0)
    fcall(pm, FSET, me_wm, V(5), 7.5)
    check('user var 5 = 7.5', fcall(pm, FGET, me_wm, V(5)), 7.5)
    check('another object: own vars', fcall(pm, FGET, foe_wm, V(5)), 0.0)
    fcall(pm, FSET, foe_wm, V(5), -2.0)
    check('both kept', (fcall(pm, FGET, me_wm, V(5)), fcall(pm, FGET, foe_wm, V(5))), (7.5, -2.0))
    fcall(pm, FSET, me_wm, V(0x21), 3.0)
    frame(me)
    frame(me)
    check('timer 1: 3 -> 1 after 2 frames', fcall(pm, FGET, me_wm, V(0x21)), 1.0)
    for _ in range(4):
        frame(me)
    check('timer stops at 0', fcall(pm, FGET, me_wm, V(0x21)), 0.0)
    check('position IDs still work (self X of a non-fighter = 0)', fcall(pm, FGET, me_wm, 0x0F000000), 0.0)
    w32(pm, me_km + 0x11C, 5)
    check('kinetic type read', fcall(pm, FGET, me_wm, V(0x30)), 5.0)
    fcall(pm, FSET, me_wm, V(0x30), 9.0)
    check('kinetic type set (vt +0xEC)', r32(pm, me_km + 0x11C), 9)
    pm.mem_write(me_km + 0x200, struct.pack('>ff', 1.25, -0.5))
    check('speed X / Y', (fcall(pm, FGET, me_wm, V(0x32)), fcall(pm, FGET, me_wm, V(0x33))), (1.25, -0.5))

    # Track_Target on the weapon: energy 0 at km + 0x300, moving right (1, 0)
    h = a.addr('h_track')
    state, flag, params = 0x10373000, 0x10374000, 0x10375000

    def track(frames, speed, turn, rng, mode):
        pm.mem_write(params, struct.pack('>iff', frames, speed, turn) + struct.pack('>fi', rng, mode))
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        pm.mem_write(flag + 8, b'\1')
        run(pm, h, RET, {UC_PPC_REG_3: me, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000

    def vel(km):
        return tuple(round(x, 3) for x in struct.unpack('>ff', pm.mem_read(km + 0x300, 8)))
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    check('Track_Target: returns 2, steps 6 words', track(3, 2.0, 0.0, 0.0, 0), (2, 24))
    ent = [C.OBJS + C.OBJ_SIZE * k for k in range(C.OBJ_N) if r32(pm, C.OBJS + C.OBJ_SIZE * k) == me_wm]
    check('Track_Target: entry frames / speed / mode', ent and (r32(pm, ent[0] + 8), struct.unpack('>f', pm.mem_read(ent[0] + 0xC, 4))[0], r32(pm, ent[0] + 0x1C)), (3, 2.0, 0))
    frame(me)
    check('weapon: straight at the foe (owner skipped), speed 2', vel(me_km), (0.0, 2.0))
    check('tracking frames left (raw) 2', r32(pm, ent[0] + 8), 2)
    check('tracking frames left 2', fcall(pm, FGET, me_wm, V(0x31)), 2.0)
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 0.0, 45.0, 0.0, 0)
    frame(me)
    check('weapon: turn 45 degrees a frame, keep speed 1', vel(me_km), (0.707, 0.707))
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 0.0, 0.0, 5.0, 0)
    frame(me)
    check('weapon: foe out of range -> unchanged', vel(me_km), (1.0, 0.0))
    track(1, 2.0, 0.0, 0.0, 0)
    frame(me)
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    frame(me)
    check('frames run out -> no more steering', vel(me_km), (1.0, 0.0))
    # reflected by the foe: current owner = the foe; goes back at the original owner (below), not the foe
    w32(pm, me + 0xA00 + 0x34, 0x20000)
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 1.0, 0)                             # range 1: the owner is 3 away, still targeted
    frame(me)
    check('reflected: back at the original owner (any range)', vel(me_km), (0.0, -2.0))
    pm.mem_write(ents + 0x1E, b'\0')                     # original owner not live: not the reflector either
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 0.0, 0)
    frame(me)
    check('reflected, owner gone: the reflector is skipped', vel(me_km), (1.0, 0.0))
    pm.mem_write(ents + 0x1E, b'\4')
    w32(pm, me + 0xA00 + 0x34, 0x10000)                   # reflected back by its owner: normal again
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    frame(me)
    check('reflected back by the owner: at the foe again', vel(me_km), (0.0, 2.0))
    track(5, 2.0, 0.0, 0.0, 0)
    w32(pm, 0x10390000 + 0x28, me_wm)
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 31 - 3: 0x10390000})
    check('set-up hook: r3 = WorkModule', pm.reg_read(UC_PPC_REG_3), me_wm)
    check('set-up hook: object forgotten', (fcall(pm, FGET, me_wm, V(5)), fcall(pm, FGET, me_wm, V(0x31))), (0.0, 0.0))

    # a fighter tracking: the foe (in the table) toward the weapon's owner (entry 0)
    w32(pm, 0x7E001FF0, 0x7E002000)
    pm.mem_write(foe_km + 0x200, struct.pack('>ff', 0.0, 0.0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    pm.mem_write(params, struct.pack('>iff', 3, 1.5, 0.0) + struct.pack('>fi', 0.0, 0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    frame(foe)
    log, p = [], 0x7E002000
    while p < r32(pm, 0x7E001FF0):
        n = r32(pm, p)
        log.append([r32(pm, p + 4 + 4 * i) for i in range(n)])
        p += 4 + 4 * n
    fb = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]      # noqa: E731
    check('fighter: kinetic ops (as Kirby side B), straight down at speed 1.5', log,
          [[0x11, 3, fb(0.0), 0], [0x10, 3, 0, 0], [0xB, 3], [0x11, 1, fb(-1.5)], [0xF, 1, 0], [0x14, 1, fb(1.5)], [0xB, 1]])


def main():
    patched, original = sys.argv[1:3]
    a, words, hooks = C.build()
    om, pm = machine(original), machine(patched)
    want = {C.LOOKUP: [0x3860FFFF], C.SIZE1: [0x546A103A, 0x7C7C292E, 0x7C0A202E],
            C.SIZE2: [0x546B103A, 0x7C7C292E, 0x7D8BF02E], C.FETCH: [0x54E6103A, 0x7C06E82E]}
    for at, ws in want.items():
        check('original words at 0x%08X' % at, [r32(om, at + 4 * i) for i in range(len(ws))], ws)
    check('cave words in place', all(r32(pm, C.CAVE + 4 * i) == w for i, w in enumerate(words)), True)
    check('hooks in place', all(r32(pm, k) == v for k, v in hooks.items()), True)

    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    new = [(zlib.crc32(c[0].encode()) & 0xFFFFFFFF, C.NEW_BASE + k) for k, c in enumerate(C.COMMANDS)]
    check('new CRCs not in the game table', [c for c, _ in new if c in dict(pairs)], [])

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    bad = [hex(c) for c, i in pairs if lookup(pm, c) != i]
    check('vanilla CRCs keep their index (%d)' % COUNT, bad, [])
    check('new CRCs', [lookup(pm, c) for c, _ in new], [i for _, i in new])
    check('unknown CRC', lookup(pm, 0x12345678), 0xFFFFFFFF)
    check('unknown CRC (original)', lookup(om, 0x12345678), 0xFFFFFFFF)

    # a script: Hitbox (25), new 0, FRAME, new 1, Special_Hitbox (42)
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    script = [0xB738EABD, new[0][0], 0x42ACFE7D, new[1][0], 0x14FCC7E4]
    want_idx = [idx[0xB738EABD], new[0][1], idx[0x42ACFE7D], new[1][1], idx[0x14FCC7E4]]
    want_size = [size[want_idx[0]], C.COMMANDS[0][1], size[want_idx[2]], C.COMMANDS[1][1], size[want_idx[4]]]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_29: 0, UC_PPC_REG_30: len(script), UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script), UC_PPC_REG_30: SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, s in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += s
        run(pm, start, stop, regs)
        got = [r32(pm, BUF + 4 * x) for x in offs]
        check('loader %d: indices' % (loop + 1), got, want_idx)
        total = pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4)
        check('loader %d: words stepped' % (loop + 1), total, sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0), mu.reg_read(UC_PPC_REG_12)
    bad = [i for _, i in pairs if fetch(pm, i)[0] != r32(om, HANDLERS + 4 * i)]
    check('vanilla handlers unchanged', bad, [])
    check('r12 kept', fetch(pm, 50)[1], 0x55)
    check('new handlers', [fetch(pm, i)[0] for _, i in new], [a.addr(c[2]) for c in C.COMMANDS])

    # handlers, base handler stubbed (steps over its own size when state +8 == -1, returns 2)
    acc, am, slots, state, flag, params = 0x10370000, 0x10371000, 0x10372000, 0x10373000, 0x10374000, 0x10375000
    for k, (name, csize, label, base) in enumerate(C.COMMANDS[:2]):
        nbase = csize - C.N_EXTRA
        stub = [0x8005_0008, 0x2C00FFFF, 0x40820010, 0x8165_0004, 0x396B0000 | (4 * nbase), 0x91650004,
                0x38600002, 0x4E800020]          # lwz r0,8(r5); cmpwi r0,-1; bne +16; lwz r11,4(r5);
        for i, wd in enumerate(stub):           # addi r11,r11,size; stw r11,4(r5); li r3,2; blr
            w32(pm, base + 4 * i, wd)
        w32(pm, acc + 0x50, am)
        w32(pm, am + 0x40, slots)
        pm.mem_write(slots, bytes(range(256)) * 4 + b'\0' * 0x100)
        sid = 3
        slot = slots + sid * 0x84
        ext = params + 4 * (nbase - 1)

        def go(exe, extras, jump=False):
            w32(pm, params, sid)
            for i, v in enumerate(extras):
                pm.mem_write(ext + 4 * i, struct.pack('>f' if i in (0, 1, 3, 5) else '>i', v))
            w32(pm, state + 4, 0x1000)
            w32(pm, state + 8, 5 if jump else -1)
            pm.mem_write(flag + 8, bytes([exe]))
            run(pm, a.addr(label), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state,
                                         UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
            return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000

        def find(data):
            run(pm, a.addr('ext_find'), RET, {UC_PPC_REG_3: data})
            return pm.reg_read(UC_PPC_REG_3)
        ret, step = go(1, [1.5, 0.0, 12, -2.0, 0, 0.5])
        check('%s: returns 2, steps over %d words' % (name, csize), (ret, step), (2, 4 * csize))
        e = find(slot)
        check('%s: found from the slot data' % name, e != 0 and (e - C.TABLE) % C.ENTRY == 0, True)
        if e:
            vals = struct.unpack('>ffiifif', bytes(pm.mem_read(e + 0x14, 0x1C)))[:6]
            got = struct.unpack('>ffifif', bytes(pm.mem_read(e + 0x14, 0x18)))
            check('%s: extras (x <= 0 -> 1)' % name, got, (1.5, 1.0, 12, 1.0, 0, 0.5))
            check('%s: tag' % name, struct.unpack('>H', pm.mem_read(slot + C.TAG_OFF, 2))[0], C.TAG | ((e - C.TABLE) // C.ENTRY))
        e2 = find(slot)
        go(1, [2.0, 3.0, 0, 1.0, 4, 1.0])
        check('%s: same slot reuses its entry' % name, find(slot), e2)
        check('%s: other slot not found' % name, find(slots + 2 * 0x84), 0)
        w32(pm, slot + 0x24, r32(pm, slot + 0x24) ^ 1)              # a plain hitbox rewrote the slot
        check('%s: not found after the slot changed' % name, find(slot), 0)
        w32(pm, slot + 0x24, r32(pm, slot + 0x24) ^ 1)
        pm.mem_write(slot + C.TAG_OFF, b'\0\0')
        ret, step = go(0, [2.0, 3.0, 0, 1.0, 4, 1.0])
        check('%s: skipped: steps, records nothing' % name, (step, find(slot)), (4 * csize, 0))
        ret, step = go(1, [2.0, 3.0, 0, 1.0, 4, 1.0], jump=True)
        check('%s: jump pending: no step' % name, step, 0)
        check('%s: bad pointer: no crash, nothing' % name, find(0x00001234), 0)

    hit_tests(pm, om, a, slot, acc)
    obj_tests(pm, om, a)
    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
