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
  timers down, the set-up hook forgetting an object, the shared variables (0x0F000340 + 8 * slot + k = that
  slot's fighter's VAR_24 + k, from a weapon and from fighters, through every WorkModule class; empty / not
  live slots and bad fighter tables read 0 and write nothing), Track_Target steering a weapon (owner skipped,
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
                               UC_PPC_REG_19, UC_PPC_REG_20, UC_PPC_REG_27, UC_PPC_REG_26, UC_PPC_REG_10, UC_PPC_REG_FPR1, UC_PPC_REG_FPR28,
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
    for v, want, what in ((-2.0, 22.0, 'HitstunMul -2: 2 frames more'), (0.0, 20.0, 'HitstunMul 0: x1')):
        record([v] + ext_vals[1:])
        pm.mem_write(hi + 0x44, bytes(pm.mem_read(slot, 0x68)))
        check(what, stun(hi, 20.0), want)
    record(ext_vals)
    pm.mem_write(hi + 0x44, bytes(pm.mem_read(slot, 0x68)))

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


def shared_tests(pm, me_wm, own_wm, foe_wm, ents):
    """0x0F000340 + 8*s + k: fighter table entry s's VAR_(24 + k). Entry 0 = own_wm, entry 1 = foe_wm (count
    2); me_wm (a weapon) is in no entry."""
    import position_vars_cave as P
    FGET, FSET = 0x02F1DBE4, 0x02F1DC04
    V = lambda i: 0x0F000300 + i                          # noqa: E731
    S = lambda s, k: 0x0F000340 + 8 * s + k               # noqa: E731

    def entries(wm):
        return sum(1 for k in range(C.OBJ_N) if r32(pm, C.OBJS + C.OBJ_SIZE * k) == wm)

    def objs():
        return bytes(pm.mem_read(C.OBJS, C.OBJ_N * C.OBJ_SIZE))
    check('shared: the owner (entry 0) has no state yet', entries(own_wm), 0)
    check('shared: read with no state -> 0', fcall(pm, FGET, me_wm, S(0, 2)), 0.0)
    check('shared: a read creates nothing', entries(own_wm), 0)
    fcall(pm, FSET, me_wm, S(0, 2), 9.0)
    check('shared: a write creates the slot fighter\'s entry', entries(own_wm), 1)
    check('shared: weapon writes slot 1 var 2 -> the fighter\'s own VAR_26', fcall(pm, FGET, own_wm, V(26)), 9.0)
    fcall(pm, FSET, me_wm, S(1, 3), 4.5)
    check('shared: weapon writes slot 2 var 3 -> the foe\'s own VAR_27', fcall(pm, FGET, foe_wm, V(27)), 4.5)
    fcall(pm, FSET, foe_wm, V(27), -1.25)
    check('shared: the foe sets its VAR_27 -> the weapon reads slot 2 var 3', fcall(pm, FGET, me_wm, S(1, 3)), -1.25)
    check('shared: the foe reads its own slot', fcall(pm, FGET, foe_wm, S(1, 3)), -1.25)
    fcall(pm, FSET, foe_wm, S(0, 7), 2.0)
    check('shared: fighter writes another fighter\'s (owner VAR_31)', fcall(pm, FGET, own_wm, V(31)), 2.0)
    for k in range(8):
        fcall(pm, FSET, me_wm, S(1, k), k + 0.5)
    check('shared: k 0-7 = VAR_24-31', [fcall(pm, FGET, foe_wm, V(24 + k)) for k in range(8)],
          [k + 0.5 for k in range(8)])
    check('shared: the foe\'s VAR_5 / VAR_23 untouched', (fcall(pm, FGET, foe_wm, V(5)), fcall(pm, FGET, foe_wm, V(23))),
          (-2.0, 0.0))
    check('shared: the weapon\'s own VAR_5 / VAR_27 untouched', (fcall(pm, FGET, me_wm, V(5)), fcall(pm, FGET, me_wm, V(27))),
          (7.5, 0.0))
    check('shared: get_float of every WorkModule class', [fcall(pm, cls[0], me_wm, S(1, 3)) for cls in P.CLASSES],
          [3.5] * len(P.CLASSES))
    for n, cls in enumerate(P.CLASSES):
        fcall(pm, cls[1], me_wm, S(1, 6), 10.0 + n)
        check('shared: set_float of WorkModule class %d' % n, fcall(pm, FGET, foe_wm, V(30)), 10.0 + n)
    fcall(pm, 0x02F1DCF8, me_wm, S(1, 0), 2.0)            # add_float / sub_float (SUB_FLOAT_2): read + write
    fcall(pm, 0x02F1DD20, me_wm, S(1, 0), 0.25)
    check('shared: add 2 / sub 0.25 -> the foe\'s VAR_24 0.5 + 1.75', fcall(pm, FGET, foe_wm, V(24)), 2.25)
    before = objs()
    check('shared: empty slots 3-8 read 0', [fcall(pm, FGET, me_wm, S(s, 1)) for s in range(2, 8)], [0.0] * 6)
    for s in range(2, 8):
        fcall(pm, FSET, me_wm, S(s, 1), 5.0)
    check('shared: writes to empty slots change nothing', objs() == before, True)
    pm.mem_write(ents + C.FIGHTER_ENTRY + 0x1E, b'\3')    # the foe's entry not live
    check('shared: not live -> 0', fcall(pm, FGET, me_wm, S(1, 3)), 0.0)
    fcall(pm, FSET, me_wm, S(1, 3), 99.0)
    check('shared: write to a not live slot changes nothing', objs() == before, True)
    pm.mem_write(ents + C.FIGHTER_ENTRY + 0x1E, b'\4')
    check('shared: live again: the value kept', fcall(pm, FGET, foe_wm, V(27)), 3.5)
    tab = r32(pm, C.FIGHTERS)
    for bad in (0, 0x10384002):                           # no fighter table / a misaligned one
        w32(pm, C.FIGHTERS, bad)
        r = fcall(pm, FGET, me_wm, S(1, 3))
        fcall(pm, FSET, me_wm, S(1, 3), 99.0)
        check('shared: fighter table 0x%X -> 0, no write' % bad, (r, objs() == before), (0.0, True))
    w32(pm, C.FIGHTERS, tab)
    for ident in (0x337, 0x33F, 0x3C0, 0x3FF):           # (0x380-0x3BF: New_Var's, tools/new_var_test.py)
        fcall(pm, FSET, me_wm, 0x0F000000 + ident, 5.0)
        check('ID 0x0F000%03X: reads 0, a write changes nothing' % ident,
              (fcall(pm, FGET, me_wm, 0x0F000000 + ident), objs() == before), (0.0, True))


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
fwrapper:                       # KineticModuleF wrapper: f1 = the float at 0x7E001FE0 (energy 1's Y speed)
        lis r11, 0x7E00
        lfs f1, 0x1FE0(r11)
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
    for wrap, to in ((C.KINETIC_W, wa), (C.POSTURE_W, wa), (C.KINETIC_FW, stubs.addr('fwrapper'))):
        for i, wd in enumerate([0x3D800000 | (to >> 16), 0x618C0000 | (to & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, wrap + 4 * i, wd)       # lis r12 / ori r12 / mtctr r12 / bctr
    # objects: accessor +0x18 posture, +0x28 WorkModule, +0x34 KineticModule, +0x68 LinkModule
    def obj(base, x, y):
        acc, post, wm, km, lm, vt = base, base + 0x100, base + 0x200, base + 0x400, base + 0x800, base + 0x900
        w32(pm, acc + 0x18, post)
        w32(pm, acc + 0x28, wm)
        w32(pm, acc + 0x34, km)
        w32(pm, acc + 0x68, lm)
        w32(pm, acc + 0x6C, base + 0xA00)                 # owner module: +0x34 current owner's ID
        for off in (8, 0x18, 0x28):                       # team / hurt team / attack team ids: none
            w32(pm, base + 0xA00 + off, -1)
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
    shared_tests(pm, me_wm, own_wm, foe_wm, ents)

    # Track_Target on the weapon: energy 0 at km + 0x300, moving right (1, 0)
    h = a.addr('h_track')
    state, flag, params = 0x10373000, 0x10374000, 0x10375000

    def track(frames, speed, turn, rng, mode, owner=0, mates=0):
        pm.mem_write(params, struct.pack('>iff', frames, speed, turn) + struct.pack('>fiii', rng, mode, owner, mates))
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        pm.mem_write(flag + 8, b'\1')
        run(pm, h, RET, {UC_PPC_REG_3: me, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000

    def vel(km):
        return tuple(round(x, 3) for x in struct.unpack('>ff', pm.mem_read(km + 0x300, 8)))
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    check('Track_Target: returns 2, steps 8 words', track(3, 2.0, 0.0, 0.0, 0), (2, 32))
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
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 0.0, 0, owner=1)
    frame(me)
    check('TargetOwner=1: the owner (nearest) is a target', vel(me_km), (0.0, -2.0))
    # teams: the weapon's attack team 2 = the foe's hurt team 2 -> a teammate (team attack off): skipped
    w32(pm, me + 0xA00 + 0x28, 2)
    w32(pm, foe + 0xA00 + 0x18, 2)
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 0.0, 0)
    frame(me)
    check('teammate (attack team = its hurt team): skipped', vel(me_km), (1.0, 0.0))
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 0.0, 0, mates=1)
    frame(me)
    check('TargetTeammates=1: targeted', vel(me_km), (0.0, 2.0))
    w32(pm, foe + 0xA00 + 0x18, 5)                        # hurt team differs (e.g. team attack on): a target
    pm.mem_write(me_km + 0x300, struct.pack('>ff', 1.0, 0.0))
    track(3, 2.0, 0.0, 0.0, 0)
    frame(me)
    check('hurt team differs: targeted', vel(me_km), (0.0, 2.0))
    w32(pm, foe + 0xA00 + 8, 3)
    frame(foe)                                            # (its accessor is known once it has stepped)
    check('team variables: team / hurt / attack', (fcall(pm, FGET, foe_wm, V(0x34)), fcall(pm, FGET, foe_wm, V(0x35)),
          fcall(pm, FGET, me_wm, V(0x36))), (3.0, 5.0, 2.0))
    w32(pm, me + 0xA00 + 0x28, -1)
    w32(pm, foe + 0xA00 + 0x18, -1)
    track(5, 2.0, 0.0, 0.0, 0)
    w32(pm, 0x10390000 + 0x28, me_wm)
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 31 - 3: 0x10390000})
    check('set-up hook: r3 = WorkModule', pm.reg_read(UC_PPC_REG_3), me_wm)
    check('set-up hook: object forgotten', (fcall(pm, FGET, me_wm, V(5)), fcall(pm, FGET, me_wm, V(0x31))), (0.0, 0.0))

    # a fighter tracking: the foe (in the table) toward the weapon's owner (entry 0)
    w32(pm, 0x7E001FF0, 0x7E002000)
    pm.mem_write(foe_km + 0x200, struct.pack('>ff', 0.0, 0.0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    pm.mem_write(params, struct.pack('>iff', 3, 1.5, 0.0) + struct.pack('>fiii', 0.0, 0, 0, 0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    frame(foe)
    log, p = [], 0x7E002000
    while p < r32(pm, 0x7E001FF0):
        n = r32(pm, p)
        log.append([r32(pm, p + 4 + 4 * i) for i in range(n)])
        p += 4 + 4 * n
    fb = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]      # noqa: E731
    check('fighter: kinetic ops, straight down at speed 1.5 (gravity and its limit left alone)', log,
          [[0x11, 3, fb(0.0), 0], [0x10, 3, 0, 0], [0xB, 3], [0x11, 1, fb(-1.5)], [0xB, 1]])

    # Mode 4: no gravity. The gravity energy's Y speed set each frame gets back what gravity took
    # since the last frame (KineticModuleF(0xB, 1) now vs what was set), 0..1
    def ops():
        log, p = [], 0x7E002000
        while p < r32(pm, 0x7E001FF0):
            n = r32(pm, p)
            log.append([r32(pm, p + 4 + 4 * i) for i in range(n)])
            p += 4 + 4 * n
        return log

    def vy_set(now):
        w32(pm, 0x7E001FF0, 0x7E002000)
        pm.mem_write(0x7E001FE0, struct.pack('>f', now))
        frame(foe)
        ys = [o for o in ops() if o[:2] == [0x11, 1]]
        return round(struct.unpack('>f', struct.pack('>I', ys[0][2]))[0], 4) if ys else None
    pm.mem_write(params, struct.pack('>iff', -1, 1.5, 0.0) + struct.pack('>fiii', 0.0, 4, 0, 0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    check('no gravity, first frame: the speed as is', vy_set(0.0), -1.5)
    check('no gravity: gravity took 0.1 -> set 0.1 more', vy_set(-1.6), -1.4)
    check('no gravity: steady (took 0.1 again)', vy_set(-1.5), -1.4)
    check('no gravity: a reset speed (landing) puts back at most 1', vy_set(-9.0), -0.5)
    check('no gravity: speed gained (not lost) -> nothing put back', vy_set(5.0), -1.5)
    check('no gravity: no gravity / limit ops', [o for o in ops() if o[0] in (0xF, 0x14)], [])
    pm.mem_write(params, struct.pack('>iff', 0, 0.0, 0.0) + struct.pack('>fiii', 0.0, 0, 0, 0))
    run(pm, h, RET, {UC_PPC_REG_3: foe, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    check('Track_Target(0) stops it: no more ops', vy_set(-1.0), None)


def thread_tests(pm, om, a):
    """Thread_Start / Thread_Stop with the game's own interpreter (0x02BEE950 -> 0x02BEE63C): a loaded script
    (command words = indices) Thread_Start(15, 7, flags){ FRAME(2); Track_Target(3, 2, 0, 0, 0, 0, 0) } Script_End"""
    from unicorn.ppc_const import UC_PPC_REG_PC
    idx = {r32(om, CRC_TABLE + 8 * i): r32(om, CRC_TABLE + 8 * i + 4) for i in range(COUNT)}
    new = {c[0]: C.NEW_BASE + k for k, c in enumerate(C.COMMANDS)}
    me = 0x10380000                                        # the weapon from obj_tests (WorkModule +0x200)
    me_wm = me + 0x200
    script, state, ctx, table = 0x10391000, 0x10392000, 0x10392100, 0x10392200
    f = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]        # noqa: E731

    def load(flags):
        words = [new['Thread_Start'], 15, 7, flags, idx[0x42ACFE7D], f(2.0),
                 new['Track_Target'], 3, f(2.0), 0, 0, 0, 0, 0, idx[0x5766F889], idx[0x5766F889]]
        for i, w in enumerate(words):
            w32(pm, script + 4 * i, w)

    def start(flags=0, exe=1):
        load(flags)
        w32(pm, state + 4, script)
        w32(pm, state + 8, -1)
        pm.mem_write(ctx + 8, bytes([exe]))
        run(pm, a.addr('h_thread'), RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: table, UC_PPC_REG_5: state,
                                          UC_PPC_REG_6: ctx, UC_PPC_REG_7: script + 4})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - script

    def slots():
        return [(k, r32(pm, C.THREADS + C.THREAD_SIZE * k + 8)) for k in range(C.THREAD_N)
                if r32(pm, C.THREADS + C.THREAD_SIZE * k) == me]

    def entry_frames():
        e = [C.OBJS + C.OBJ_SIZE * k for k in range(C.OBJ_N) if r32(pm, C.OBJS + C.OBJ_SIZE * k) == me_wm]
        return r32(pm, e[0] + 8) if e else None
    holder = 0x10393000
    w32(pm, holder, me)

    def step(k=1):                                         # the weapon step entry, as the game calls it
        regs = {UC_PPC_REG_3 + i: 0x2000 + i for i in range(5, 29)}
        regs[UC_PPC_REG_3] = 0x1234
        regs[UC_PPC_REG_4] = holder
        run(pm, C.STEP_HOOKS[k], C.STEP_HOOKS[k] + 4, regs)
        kept = all(pm.reg_read(UC_PPC_REG_3 + i) == 0x2000 + i for i in range(5, 29))
        return kept and pm.reg_read(UC_PPC_REG_3) == 0x1234 and pm.reg_read(UC_PPC_REG_4) == holder \
            and pm.reg_read(UC_PPC_REG_1) == 0x7F00F000 - 0x38
    # the interpreter saves / restores f29-f31's paired-single halves (Gekko psq_st / psq_l, primary
    # opcodes 4 / 56 / 57 / 60 / 61): unicorn can't run them, nop them here (the float values are kept)
    nopped = 0
    for lo, hi in ((0x02BEE63C, 0x02BEE9B8), (0x02BE5500, 0x02BE5B00)):
        for at in range(lo, hi, 4):
            if r32(pm, at) >> 26 in (4, 56, 57, 60, 61):
                w32(pm, at, 0x60000000)
                nopped += 1
    w32(pm, me + 0x48, 0)                                  # no StopModule: not in hitlag
    check('Thread_Start: returns 2, the script jumps over the block (15 words)', start(), (2, 60))
    check('thread registered (ID 7)', [i for _, i in slots()], [7])
    k = slots()[0][0]
    check('thread state starts at the block', r32(pm, C.THREADS + C.THREAD_SIZE * k + 0x14), script + 16)
    track_before = entry_frames()
    check('step hook keeps registers / stack', step(), True)
    check('frame 1: FRAME(2) still waiting', (entry_frames(), [i for _, i in slots()]), (track_before, [7]))
    step()
    step()
    check('Track_Target ran by frame 3 (frames 3, then 2 after the frame hook would count)', entry_frames(), 3)
    for _ in range(3):
        step()
    check('the block\'s Script_End ends the thread', slots(), [])
    start()
    run(pm, a.addr('h_thread_stop'), RET, {UC_PPC_REG_3: me, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx,
                                           UC_PPC_REG_7: holder + 0x10})
    w32(pm, holder + 0x10, 7)
    w32(pm, state + 8, -1)
    run(pm, a.addr('h_thread_stop'), RET, {UC_PPC_REG_3: me, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx,
                                           UC_PPC_REG_7: holder + 0x10})
    check('Thread_Stop(7) stops it', slots(), [])
    start()
    start()
    check('starting the same ID again restarts it (one thread)', len(slots()), 1)
    w32(pm, 0x10390000 + 0x28, me_wm)
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 31 - 3: me})
    check('object set-up drops its threads', slots(), [])
    stop = 0x10394000
    w32(pm, me + 0x48, stop)
    pm.mem_write(stop + 0x10, b'\1')                       # in hitlag
    start()
    k = slots()[0][0]
    fr = lambda: struct.unpack('>f', pm.mem_read(C.THREADS + C.THREAD_SIZE * k + 0x10 + 0x18, 4))[0]   # noqa: E731
    step()
    step()
    check('hitlag: the thread waits', (len(slots()), fr()), (1, 0.0))
    start(flags=1)
    step()
    step()
    check('Flags 1: runs during hitlag', fr() > 0.0, True)
    pm.mem_write(stop + 0x10, b'\0')
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 31 - 3: me})
    check('fast-forward (not executed): still jumps over the block', start(exe=0), (2, 60))
    check('fast-forward: no thread started', slots(), [])


def input_tests(pm, a):
    """Input_Compare / Input_Get / Input_Set / Hit_Reset with stubbed WorkModule (get: f1 = (ID & 0xFFFF) / 16,
    set: logs ID and f1), ControlModule wrapper (1 for one (op, button) pair) and AttackModule wrapper (logs)"""
    from ppcasm import Asm
    B = 0x7D000000
    pm.mem_map(B, 0x10000)
    st = Asm(B)
    st.asm("""
get:                            # WorkModule vt +0x44(wm, id) -> f1 = (id & 0xFFFF) / 16
        lis r11, 0x7D00
        clrlwi r4, r4, 16
        stw r4, 0x1104(r11)
        lis r0, 0x4330
        stw r0, 0x1100(r11)
        lfd f1, 0x1100(r11)
        lfd f0, 0x1108(r11)
        fsub f1, f1, f0
        lfs f0, 0x1110(r11)
        fmul f1, f1, f0
        frsp f1, f1
        blr
set:                            # vt +0x4C(wm, id, f1): log id, f1, count
        lis r11, 0x7D00
        stw r4, 0x1000(r11)
        stfs f1, 0x1004(r11)
        lwz r12, 0x1008(r11)
        addi r12, r12, 1
        stw r12, 0x1008(r11)
        blr
control:                        # ControlModule wrapper(ctx, {words, n}) -> 1 when (op, button) = the pair at 0x1010
        lis r11, 0x7D00
        lwz r9, 0(r4)
        lwz r10, 0(r9)
        lwz r12, 0x1010(r11)
        li r3, 0
        cmpw r10, r12
        bnelr
        lwz r10, 4(r9)
        lwz r12, 0x1014(r11)
        cmpw r10, r12
        bnelr
        li r3, 1
        blr
attack:                         # AttackModule wrapper: log the op and n, count
        lis r11, 0x7D00
        lwz r9, 0(r4)
        lwz r10, 0(r9)
        stw r10, 0x1020(r11)
        lwz r10, 4(r4)
        stw r10, 0x1024(r11)
        lwz r12, 0x1028(r11)
        addi r12, r12, 1
        stw r12, 0x1028(r11)
        blr
""")
    for i, w in enumerate(st.words()):
        w32(pm, B + 4 * i, w)
    pm.mem_write(B + 0x1108, struct.pack('>Qf', f2bits(2.0 ** 52), 1 / 16))
    for wrap, to in ((C.CONTROL_W, st.addr('control')), (C.ATTACK_W, st.addr('attack'))):
        for i, wd in enumerate([0x3D800000 | (to >> 16), 0x618C0000 | (to & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, wrap + 4 * i, wd)
    acc, wm, vt = B + 0x2000, B + 0x2100, B + 0x2200
    w32(pm, acc + 0x28, wm)
    w32(pm, wm, vt)
    w32(pm, vt + 0x44, st.addr('get'))
    w32(pm, vt + 0x4C, st.addr('set'))
    state, ctx, prm = B + 0x3000, B + 0x3100, B + 0x3200

    def go(name, params, exe=1, pair=(0, -1)):
        w32(pm, B + 0x1010, pair[0])
        w32(pm, B + 0x1014, pair[1])
        for k in (0x1000, 0x1004, 0x1008, 0x1020, 0x1024, 0x1028):
            w32(pm, B + k, 0)
        for i, v in enumerate(params):
            pm.mem_write(prm + 4 * i, struct.pack('>f' if isinstance(v, float) else '>i', v))
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        w32(pm, state + 0xC, 0x55)
        pm.mem_write(ctx + 8, bytes([exe]))
        lab = dict((c[0], c[2]) for c in C.COMMANDS)[name]
        run(pm, a.addr(lab), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx, UC_PPC_REG_7: prm})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000, r32(pm, state + 0xC)

    def logged():
        return r32(pm, B + 0x1008), r32(pm, B + 0x1000), round(struct.unpack('>f', pm.mem_read(B + 0x1004, 4))[0], 4)

    check('Input_Compare jump held (ControlModule(0x2712, 2)): true, steps 5 words',
          go('Input_Compare', [0, 2, 0, 1.0], pair=(0x2712, 2)), (2, 20, 1))
    check('Input_Compare jump held, ControlModule says no: false', go('Input_Compare', [0, 2, 0, 1.0], pair=(0x2712, 3))[2], 0)
    check('Input_Compare jump pressed (0x2710, 2)', go('Input_Compare', [0, 10, 0, 1.0], pair=(0x2710, 2))[2], 1)
    check('Input_Compare jump pressed: held only -> false', go('Input_Compare', [0, 10, 0, 1.0], pair=(0x2712, 2))[2], 0)
    check('Input_Compare grab -> MSC button 9', go('Input_Compare', [0, 4, 0, 1.0], pair=(0x2712, 9))[2], 1)
    check('Input_Compare taunt up -> d-pad up 5', go('Input_Compare', [0, 5, 0, 1.0], pair=(0x2712, 5))[2], 1)
    check('Input_Compare taunt side: d-pad left 7', go('Input_Compare', [0, 6, 0, 1.0], pair=(0x2712, 7))[2], 1)
    check('Input_Compare taunt side: d-pad right 8', go('Input_Compare', [0, 6, 0, 1.0], pair=(0x2712, 8))[2], 1)
    check('Input_Compare taunt down -> d-pad down 6', go('Input_Compare', [0, 7, 0, 1.0], pair=(0x2712, 6))[2], 1)
    check('Input_Compare button != 1 when not held', go('Input_Compare', [0, 1, 1, 1.0])[2], 1)
    # stick (variable 0x0F000110 -> stub 0x110 / 16 = 17): 17 > 16.5 and not < 16.5
    check('Input_Compare stick X via the variable: >', go('Input_Compare', [0, 0x10, 5, 16.5])[2], 1)
    check('Input_Compare stick X via the variable: <', go('Input_Compare', [0, 0x10, 4, 16.5])[2], 0)
    check('Input_Compare opponent attack held: the variable 0x0F000120 (== 18)', go('Input_Compare', [1, 0, 0, 18.0])[2], 1)
    check('Input_Compare bad method: false', go('Input_Compare', [0, 0x10, 9, 0.0])[2], 0)
    check('Input_Compare target 11: reads 0', go('Input_Compare', [11, 0x10, 0, 0.0])[2], 1)
    ret, step, _ = go('Input_Compare', [0, 2, 0, 1.0])
    w32(pm, state + 8, 0)
    check('Input_Compare steps 5 words', step, 20)

    go('Input_Get', [1, 0x11, 0x0F000300])
    check('Input_Get opponent stick Y (0x0F000131) -> VAR_0', logged(), (1, 0x0F000300, round(0x131 / 16, 4)))
    go('Input_Get', [2, 0x21, 0x0F000301])
    check('Input_Get last hit raw C-stick X (0x0F000265)', logged(), (1, 0x0F000301, round(0x265 / 16, 4)))
    go('Input_Get', [0, 1, 0x0F000302], pair=(0x2712, 1))
    check('Input_Get self special held -> 1.0', logged(), (1, 0x0F000302, 1.0))
    check('Input_Get skipped: steps 4 words, no write', (go('Input_Get', [0, 1, 0x0F000302], exe=0)[1], logged()[0]), (16, 0))

    check('Input_Set steps 4 words', go('Input_Set', [3, 2, 2.0])[1], 16)
    check('Input_Set slot 1 jump tap -> 0x0F000162 = 2', logged(), (1, 0x0F000162, 2.0))
    go('Input_Set', [0, 0x20, -0.75])
    check('Input_Set self raw stick X -> 0x0F000260', logged(), (1, 0x0F000260, -0.75))
    go('Input_Set', [10, 0x15, 1.0])
    check('Input_Set slot 8 inputs off -> 0x0F000255', logged(), (1, 0x0F000255, 1.0))
    go('Input_Set', [0, 0x22, 1.0])
    check('Input_Set input 0x22: nothing', logged()[0], 0)
    go('Input_Set', [11, 0, 1.0])
    check('Input_Set target 11: nothing', logged()[0], 0)
    go('Input_Set', [0, 2, 1.0], exe=0)
    check('Input_Set skipped: nothing', logged()[0], 0)

    ret, step, _ = go('Hit_Reset', [])
    check('Hit_Reset: AttackModule(0x2724) once, steps 1 word',
          (r32(pm, B + 0x1028), r32(pm, B + 0x1020), r32(pm, B + 0x1024), ret, step), (1, 0x2724, 1, 2, 4))
    go('Hit_Reset', [], exe=0)
    check('Hit_Reset skipped: nothing', r32(pm, B + 0x1028), 0)

    # Hit_Log_Clear: AttackModule (acc +0x50) with 2 groups at +0x14; the game's clears stubbed (log r3 r4 r5)
    hl = Asm(B + 0x4000)
    hl.asm("""
one:                            # 0x02C10660(group, list, r5): log the call (up to 2)
        lis r11, 0x7D00
        lwz r12, 0x1040(r11)
        slwi r10, r12, 4
        add r10, r10, r11
        stw r3, 0x1044(r10)
        stw r4, 0x1048(r10)
        stw r5, 0x104C(r10)
        addi r12, r12, 1
        stw r12, 0x1040(r11)
        blr
all:                            # 0x02C0ECDC(AttackModule + 8): log it
        lis r11, 0x7D00
        stw r3, 0x1070(r11)
        blr
""")
    for i, w in enumerate(hl.words()):
        w32(pm, B + 0x4000 + 4 * i, w)
    for fn, to in ((C.HIT_CLEAR_LIST, hl.addr('one')), (C.HIT_CLEAR_ALL, hl.addr('all'))):
        for i, wd in enumerate([0x3D800000 | (to >> 16), 0x618C0000 | (to & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, fn + 4 * i, wd)
    am, grp = B + 0x5000, B + 0x6000
    w32(pm, acc + 0x50, am)
    w32(pm, am + 0x10, 2)
    w32(pm, am + 0x14, grp)
    w32(pm, grp + 0x130, grp + 0x124)               # group 0: its current list is the +0x124 one
    w32(pm, grp + 0x174 + 0x130, grp + 0x174 + 0x12C)   # group 1: another one current

    def hlog(part, exe=1):
        for k in range(0x1040, 0x1074, 4):
            w32(pm, B + k, 0)
        ret, step, _ = go('Hit_Log_Clear', [part], exe=exe)
        calls = [tuple(r32(pm, B + 0x1044 + 16 * i + 4 * j) for j in range(3)) for i in range(r32(pm, B + 0x1040))]
        return ret, step, calls, r32(pm, B + 0x1070)

    check('Hit_Log_Clear(0): its current list (+0x124) once, steps 2 words',
          hlog(0), (2, 8, [(grp, grp + 0x124, 0)], 0))
    check('Hit_Log_Clear(1): the current list (+0x12C), then +0x124',
          hlog(1)[2], [(grp + 0x174, grp + 0x174 + 0x12C, 0), (grp + 0x174, grp + 0x174 + 0x124, 0)])
    check('Hit_Log_Clear(2) with 2 parts: nothing', hlog(2)[2:], ([], 0))
    check('Hit_Log_Clear(-1): every part (0x02C0ECDC(AttackModule + 8))', hlog(-1)[2:], ([], am + 8))
    check('Hit_Log_Clear skipped: nothing, steps 2 words', hlog(0, exe=0)[1:], (8, [], 0))
    w32(pm, acc + 0x50, 0)
    check('Hit_Log_Clear, no AttackModule: nothing', hlog(0)[2:], ([], 0))


def new_cmd_tests(pm, a):
    """the new commands (Hit_Check ... Animation_Rate_Set) with stubbed MSC module wrappers (each logs its
    accessor and words, returns the word at LOG + 0xFF8), a stubbed WorkModule (get: ACC IDs give fake targets'
    accessors, other IDs (id & 0xFFFF) / 16; set: logs), an AttackModule whose vt +0x2C4 / +0x2BC give 4 / 2 and a
    fighter table"""
    from ppcasm import Asm
    B, LOG, M = 0x7D200000, 0x7D300000, 0x61000000
    for base, n in ((B, 0x10000), (LOG, 0x10000), (M, 0x100000)):
        pm.mem_map(base, n)
    wraps = [C.POSTURE_W, C.POSTURE_FW, C.MOTION_W, C.MOTION_FW, C.WORK_W]
    st = Asm(B)
    st.asm(''.join("""
w%d:
        li r10, %d
        b common""" % (i, i) for i in range(len(wraps))) + """
common:                         # log {wrapper, accessor, n, words[0..3]}; return [LOG + 0xFF8]
        lis r11, 0x7D30
        lwz r12, 0xFFC(r11)
        mulli r9, r12, 0x20
        add r9, r9, r11
        stw r10, 0(r9)
        lwz r0, 4(r3)
        stw r0, 4(r9)
        lwz r8, 0(r4)
        lwz r7, 4(r4)
        stw r7, 8(r9)
        lwz r0, 0(r8)
        stw r0, 0xC(r9)
        lwz r0, 4(r8)
        stw r0, 0x10(r9)
        lwz r0, 8(r8)
        stw r0, 0x14(r9)
        lwz r0, 0xC(r8)
        stw r0, 0x18(r9)
        addi r12, r12, 1
        stw r12, 0xFFC(r11)
        lwz r3, 0xFF8(r11)
        blr
get:                            # WorkModule vt +0x44: ACC 0x0F0002BC + t -> M + 0x1000 t (as float bits)
        clrlwi r4, r4, 16
        addi r5, r4, -0x2BC
        cmplwi r5, 11
        bge get_q
        slwi r5, r5, 12
        addis r5, r5, 0x6100
        lis r11, 0x7D30
        stw r5, 0xF00(r11)
        lfs f1, 0xF00(r11)
        blr
get_q:                          # (id & 0xFFFF) / 16
        lis r11, 0x7D30
        stw r4, 0xF04(r11)
        lis r0, 0x4330
        stw r0, 0xF00(r11)
        lfd f1, 0xF00(r11)
        lfd f0, 0xF08(r11)
        fsub f1, f1, f0
        lfs f0, 0xF10(r11)
        fmul f1, f1, f0
        frsp f1, f1
        blr
set:                            # vt +0x4C: log {id, f1} at LOG + 0x800 + 8 k
        lis r11, 0x7D30
        lwz r12, 0xF14(r11)
        slwi r9, r12, 3
        add r9, r9, r11
        stw r4, 0x800(r9)
        stfs f1, 0x804(r9)
        addi r12, r12, 1
        stw r12, 0xF14(r11)
        blr
am_all:
        li r3, 4
        blr
am_now:
        li r3, 2
        blr
""")
    for i, w in enumerate(st.words()):
        w32(pm, B + 4 * i, w)
    pm.mem_write(LOG + 0xF08, struct.pack('>Qf', f2bits(2.0 ** 52), 1 / 16))
    for k, wrap in enumerate(wraps):
        to = st.addr('w%d' % k)
        for i, wd in enumerate([0x3D800000 | (to >> 16), 0x618C0000 | (to & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, wrap + 4 * i, wd)
    me, wm, am = M + 0x20000, M + 0x30000, M + 0x40000
    for acc in [me] + [M + 0x1000 * t for t in range(11)]:
        w32(pm, acc + 0x28, wm)
        w32(pm, acc + 0x50, am)
    w32(pm, wm, wm + 0x100)
    w32(pm, wm + 0x100 + 0x44, st.addr('get'))
    w32(pm, wm + 0x100 + 0x4C, st.addr('set'))
    w32(pm, am, am + 0x100)
    w32(pm, am + 0x100 + 0x2C4, st.addr('am_all'))
    w32(pm, am + 0x100 + 0x2BC, st.addr('am_now'))
    # fighter table: entry 2 (player slot 3) is target 5's accessor
    tab, ents = M + 0x50000, M + 0x60000
    w32(pm, C.FIGHTERS, tab)
    w32(pm, tab, tab + 0x10)
    w32(pm, tab + 0x10, ents)
    w32(pm, tab + 0x18, 8)
    pm.mem_write(ents + 2 * C.FIGHTER_ENTRY + 0x1E, b'\4')
    w32(pm, ents + 2 * C.FIGHTER_ENTRY + 0xC, M + 0x5000)
    state, ctx, prm = M + 0x70000, M + 0x71000, M + 0x72000
    fb = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]       # noqa: E731

    def cmd(name, *params, ret=0):
        size = dict((c[0], c[1]) for c in C.COMMANDS)[name]
        assert len(params) == size - 1, name
        for i, v in enumerate(params):
            w32(pm, prm + 4 * i, fb(v) if isinstance(v, float) else v)
        w32(pm, LOG + 0xFFC, 0)
        w32(pm, LOG + 0xF14, 0)
        w32(pm, LOG + 0xFF8, ret)
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        w32(pm, state + 0xC, 0x55)
        pm.mem_write(ctx + 8, b'\1')
        label = [c[2] for c in C.COMMANDS if c[0] == name][0]
        run(pm, a.addr(label), RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx,
                                     UC_PPC_REG_7: prm})
        calls = [struct.unpack('>7I', pm.mem_read(LOG + 0x20 * k, 0x1C)) for k in range(r32(pm, LOG + 0xFFC))]
        sets = [(r32(pm, LOG + 0x800 + 8 * k), round(struct.unpack('>f', pm.mem_read(LOG + 0x804 + 8 * k, 4))[0], 4))
                for k in range(r32(pm, LOG + 0xF14))]
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000, calls, sets, r32(pm, state + 0xC)
    PW, PF, MW, MF, WK = range(5)
    r, step, calls, sets, _c = cmd('Rotation_Set', 0, 10.0, 20.0, 30.0)
    check('Rotation_Set: returns 2, steps 5 words', (r, step), (2, 20))
    check('Rotation_Set: PostureModule(4, x, y, z) on itself',
          [c[:7] for c in calls], [(PW, me, 4, 4, fb(10.0), fb(20.0), fb(30.0))])
    r, step, calls, sets, _c = cmd('Rotation_Get', 3, 1, 0x0F000300, ret=fb(45.0))
    check('Rotation_Get (slot 1 = target 3): PostureModuleF(5) on that fighter, VAR_0 = 45',
          ([c[:4] for c in calls], sets), ([(PF, M + 0x3000, 1, 5)], [(0x0F000300, 45.0)]))
    r, step, calls, sets, _c = cmd('Rotation_Get', 11, 2, 0x0F000301, ret=2)
    check('Target 11 (last attacker: its int 0x10000065 = 2 -> slot 3 -> target 5)',
          [c[:4] for c in calls], [(WK, me, 2, 6), (PF, M + 0x5000, 1, 6)])
    r, step, calls, sets, cond = cmd('Hit_Check', 0, 0, 2)
    check('Hit_Check(since start, hurtbox) with a shield hit (4): False', cond, 0)
    check('Hit_Check(since start, shield): True', cmd('Hit_Check', 0, 0, 4)[4], 1)
    check('Hit_Check(since start, anything (0)): True', cmd('Hit_Check', 0, 0, 0)[4], 1)
    check('Hit_Check(this frame, hurtbox) with a hurtbox hit (2): True; steps 4 words', cmd('Hit_Check', 0, 1, 2)[4:] +
          (cmd('Hit_Check', 0, 1, 6)[1],), (1, 16))
    check('Hit_Check(target 12: none): False', cmd('Hit_Check', 12, 0, 0)[4], 0)
    check('Hit_Get(since start): VAR_0 = 4 (shield)', cmd('Hit_Get', 0, 0, 0x0F000300)[3], [(0x0F000300, 4.0)])
    _r, _s, calls, _st, _c = cmd('Motion_Set', 0, 0x50, 5.0, 0.0)
    check('Motion_Set(0x50, 5, 0): MotionModule(1, 0x50, 5.0, 1.0)', [c[:7] for c in calls],
          [(MW, me, 4, 1, 0x50, fb(5.0), fb(1.0))])
    _r, _s, calls, _st, _c = cmd('Motion_Set', 0, -1, 7.0, 2.0)
    check('Motion_Set(-1, 7, 2): MotionModule(0x2713, 7.0), MotionModule(4, 2.0)', [c[:5] for c in calls],
          [(MW, me, 2, 0x2713, fb(7.0)), (MW, me, 2, 4, fb(2.0))])
    _r, _s, calls, _st, _c = cmd('Motion_Set', 0, -1, -1.0, 0.0)
    check('Motion_Set(-1, -1, 0): nothing', calls, [])
    _r, _s, calls, sets, _c = cmd('Motion_Get', 0, 0, 0x0F000302, ret=0x59)
    check('Motion_Get(kind): MotionModule(7) -> 89', ([c[:4] for c in calls], sets), ([(MW, me, 1, 7)], [(0x0F000302, 89.0)]))
    _r, _s, calls, sets, _c = cmd('Motion_Get', 0, 2, 0x0F000302, ret=fb(1.5))
    check('Motion_Get(rate): MotionModuleF(9)', ([c[:4] for c in calls], sets), ([(MF, me, 1, 9)], [(0x0F000302, 1.5)]))
    _r, _s, calls, sets, _c = cmd('Position_Set', 0, 2.0, 3.0, 4.0, 1, ret=fb(-1.0))
    check('Position_Set(relative): facing -1, at (-1, -1, -1) + (2 fwd, 3, 4) -> PostureModule(3, -3, 2, 3)',
          calls[-1][:7], (PW, me, 4, 3, fb(-3.0), fb(2.0), fb(3.0)))
    _r, _s, calls, sets, _c = cmd('Position_Set', 0, 2.0, 3.0, 4.0, 0)
    check('Position_Set(absolute): PostureModule(3, 2, 3, 4)', [c[:7] for c in calls], [(PW, me, 4, 3, fb(2.0), fb(3.0), fb(4.0))])
    _r, _s, calls, sets, _c = cmd('Position_Get', 0, 3, 0x0F000300, ret=fb(-1.0))
    check('Position_Get(facing): PostureModuleF(0)', ([c[:4] for c in calls], sets), ([(PF, me, 1, 0)], [(0x0F000300, -1.0)]))
    check('Status_Set(slot 1, 0x59): STATUS of target 3 (0x0F0000BA) = 89', cmd('Status_Set', 3, 0x59)[3],
          [(0x0F0000BA, 89.0)])
    check('Status_Get(self): 0x0F0000A2 read into VAR_1', cmd('Status_Get', 0, 0x0F000301)[3], [(0x0F000301, 0xA2 / 16)])
    check('Damage_Get(nearest opponent): 0x0F000137', cmd('Damage_Get', 1, 0x0F000301)[3], [(0x0F000301, 0x137 / 16)])
    check('Damage_Set(self, 50%)', cmd('Damage_Set', 0, 50.0)[3], [(0x0F000117, 50.0)])
    check('Hitstun_Get(last fighter hit, dealt): 0x0F000051', cmd('Hitstun_Get', 2, 1, 0x0F000300)[3], [(0x0F000300, 0x51 / 16)])
    check('Hitstop_Set(self, 8, shake) / (no shake)', (cmd('Hitstop_Set', 0, 8, 1)[3], cmd('Hitstop_Set', 0, 8, 0)[3]),
          ([(0x0F000043, 8.0)], [(0x0F000044, 8.0)]))
    check('Body_State_Set(slot 2: intangible / invincible 30)', (cmd('Body_State_Set', 4, 0, 30)[3],
                                                                 cmd('Body_State_Set', 4, 1, 30)[3]),
          ([(0x0F00019B, 30.0)], [(0x0F00019C, 30.0)]))
    check('Armor_Set(self, 2, 40): threshold, then type', cmd('Armor_Set', 0, 2, 40.0)[3],
          [(0x0F00011E, 40.0), (0x0F00011D, 2.0)])
    check('Item_State_Set(last fighter hit, metal)', cmd('Item_State_Set', 2, 1)[3], [(0x0F000278, 1.0)])
    check('Stage_Collision_Set(self, 0)', cmd('Stage_Collision_Set', 0, 0)[3], [(0x0F0000A6, 0.0)])
    check('Joint_Position_Get(slot 1, joint 11): the joint, then X / Y / Z', cmd('Joint_Position_Get', 3, 11, 0x0F000300,
                                                                                 0x0F000301, 0x0F000302)[3],
          [(0x0F00029C, 11.0), (0x0F000300, 0x29D / 16), (0x0F000301, 0x29E / 16), (0x0F000302, 0x29F / 16)])
    check('Animation_Rate_Set(1.25)', cmd('Animation_Rate_Set', 1.25)[3], [(0x0F000098, 1.25)])
    check('Last_Hit_Get(1: last attacker, int 2 -> slot 3)', cmd('Last_Hit_Get', 1, 0x0F000300, ret=2)[3], [(0x0F000300, 3.0)])
    check('Target_Slot_Get(target 5 = table entry 2): 3', cmd('Target_Slot_Get', 5, 0x0F000300)[3], [(0x0F000300, 3.0)])
    check('Target_Slot_Get(target 6, not in the table): 0', cmd('Target_Slot_Get', 6, 0x0F000300)[3], [(0x0F000300, 0.0)])
    check('Status_Set(target 11, int 9 = no slot): nothing', cmd('Status_Set', 11, 0x59, ret=9)[3], [])
    pm.mem_write(ctx + 8, b'\0')
    w32(pm, state + 4, 0x1000)
    w32(pm, LOG + 0xFFC, 0)
    run(pm, a.addr('h_rset'), RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: ctx,
                                    UC_PPC_REG_7: prm})
    check('skipped (fast-forward): steps only', (r32(pm, state + 4) - 0x1000, r32(pm, LOG + 0xFFC)), (20, 0))


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
        w32(pm, am + 0x3C, 10)                                      # slots (fighters: 10)
        pm.mem_write(slots, bytes(range(256)) * 4 + b'\0' * 0x400)
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
        old_copy = bytes(pm.mem_read(slot, 0x68))                  # a hit of this hitbox still being handled
        go(1, [2.0, 3.0, 0, 1.0, 4, 1.0])
        e3 = find(slot)
        check('%s: the same ID again: a new entry (the old one kept)' % name, (e3 != 0, e3 != e2), (True, True))
        pm.mem_write(0x1037F000, old_copy)
        run(pm, a.addr('find_copy'), RET, {UC_PPC_REG_5: 0x1037F000})
        e_old = pm.reg_read(UC_PPC_REG_5)
        check('%s: the earlier hit (its copy) still finds its own extras, not the new ones' % name,
              (e_old, struct.unpack('>f', pm.mem_read(e_old + 0x14, 4))[0] if e_old else None), (e2, 1.5))
        w32(pm, params, 9)                                          # ID 9 (fighters have 10): recorded too
        pm.mem_write(slots + 9 * 0x84 + C.TAG_OFF, b'\0\0')
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        pm.mem_write(flag + 8, b'\1')
        run(pm, a.addr(label), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: flag,
                                     UC_PPC_REG_7: params})
        check('%s: ID 9 recorded (IDs up to the module\'s count, not 7)' % name, find(slots + 9 * 0x84) != 0, True)
        w32(pm, params, 10)
        pm.mem_write(slots + 10 * 0x84 + C.TAG_OFF, b'\0\0')
        w32(pm, state + 4, 0x1000)
        run(pm, a.addr(label), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: flag,
                                     UC_PPC_REG_7: params})
        check('%s: ID 10 (past the count): nothing recorded' % name, struct.unpack('>H', pm.mem_read(
            slots + 10 * 0x84 + C.TAG_OFF, 2))[0], 0)
        w32(pm, params, sid)
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

    # every hitbox set (AttackModule vt +0x54, 0x02C086A8) clears the slot's tag after copying the data
    check('slot set hook: original word', r32(om, C.SLOT_SET), 0x815C0014)
    pm.mem_write(slot + C.TAG_OFF, struct.pack('>H', C.TAG | 5))
    w32(pm, 0x10380000 + 0x14, 0x10381000)
    run(pm, C.SLOT_SET, C.SLOT_SET + 8, {UC_PPC_REG_26: slot, UC_PPC_REG_28: 0x10380000})
    check('hitbox set: the slot\'s tag cleared, the game\'s load done', (struct.unpack('>H', pm.mem_read(
        slot + C.TAG_OFF, 2))[0], pm.reg_read(UC_PPC_REG_10)), (0, 0x10381000))
    hit_tests(pm, om, a, slot, acc)
    d = [r32(pm, C.DBG + 4 * i) for i in range(17)]
    check('debug: Extra commands run / tagged, last ID', (d[15] > 0, d[0] > 0, d[16]), (True, True, 3))
    check('debug: victim hitstop calls / found, attacker calls / found, hitstun calls / found',
          tuple(x > 0 for x in (d[1], d[2], d[5], d[6], d[13], d[14])), (True,) * 6)
    check('debug: last victim hitstop before / after (frames 20 replace 7)', (d[3], d[4]), (7, 20))
    obj_tests(pm, om, a)
    thread_tests(pm, om, a)
    input_tests(pm, a)
    new_cmd_tests(pm, a)
    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
