#!/usr/bin/env python3
"""Tests Gravity_Set (tools/acmd_ext_cave.py gs_code, docs/acmd-extra-commands.md "Gravity_Set") in a patched RPX
(unicorn), with the game's own kinetic code.

  python3 tools/gravity_set_test.py PATCHED.rpx BASE.rpx

BASE is the executable it was built on (exe_v41: the hook words held what GS_ORIG says, the GS space was zero). The
fake fighter's gravity energy is made by the game's own constructor (0x02E814B0) and set from its params by the game's
own reset (vt +0x1C, 0x02E818A8, type 0: what every kinetic type change does), and each frame is the game's own
update (vt +0x14, 0x02E8159C, through the patched entry / exit). Its StatusModule is made by the game's own
constructor (0x02E881A8). Stubbed: the fighter's WorkModule (params, flags, its MSC handler: a log, and op 0x2711
turns the flag off), the rates global (1.0), 0x0275FF54 after the update (situation-dependent extras), the fighter
data lookup in the reset (its +0x518 multiplier: 1.0) and two calls of the damage reaction decision's armor path; the
paired-single saves / loads (psq_*, which unicorn can't run) are nops. On PATCHED:
- the words, the command's CRC / index / handler / size;
- without Gravity_Set the speed curve is the game's own (the same as BASE's, frame by frame, and as the model of the
  update: gravity, the max fall speed's brake, the absolute limit);
- Gravity_Set(0.02, 0.6): the curve -0.02 a frame down to -0.6; after every update the energy holds the fighter's own
  acceleration / max fall again (nothing to restore); a reset in between (a kinetic type change) doesn't undo it;
  GRAVITY / MAX_FALL (0x0F000337 / 338, the game's get_float) read what is in effect; Mode 1 multipliers; Mode 2 cuts
  a fast fall to MaxFall at once (without it: the game's gradual brake); Mode 4 turns the fast-fall flag off (without
  it: the game's fast fall); -1 keeps the fighter's own; Accel / MaxFall -1 with Mode 0 turns it off;
- it ends (the fighter's own values in the next update) on: a status change (0x02E88B40, through hk_lgc_chg); a hit
  that takes effect (the game's damage reaction decision 0x02E76BB4 returning 0), at once, before any status change;
  NOT on a hit with no reaction (armor, or knockback under the fighter's threshold); a ledge: situation 1, a cliff
  status or a tether hang as the current or the pending status (whatever path), not Ottotto (0x7B);
- other fighters keep theirs; skipped command: steps only; not a fighter: nothing; 17 fighters: the 17th takes entry 0.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_7, UC_PPC_REG_28, UC_PPC_REG_30, UC_PPC_REG_FPR1, UC_PPC_REG_LR,
                               UC_PPC_REG_MSR)

fails = 0
MEM = 0x7E000000
STUBS, WMVT, PARAMS, FLAGS, LOG, RATES, FDATA = (MEM + o for o in (0, 0x800, 0x900, 0xA00, 0xB00, 0xC00, 0xD00))
ST, CTX, PRM, VEC, REC = (MEM + o for o in (0x2000, 0x2100, 0x2200, 0x2300, 0x2400))
FGET = 0x02F1DBE4                # the fighters' WorkModule get_float (position_vars' hooks -> user_entry)
GRAV_CTOR, GRAV_RESET, GRAV_UPDATE = 0x02E814B0, 0x02E818A8, 0x02E8159C
SM_CTOR = 0x02E881A8
DIDDY = {0x03000018: 0.105, 0x03000019: 1.75, 0x0300001A: 0.016, 0x0300001B: 2.8, 0x03000023: 10.0,
         0x2A: 0.0}              # gravity, max fall, its brake (V acceleration), fast fall, the absolute limit; the
                                 # work float 0x2A the damage reaction compares the knockback with
FF, GROUND_FLAG = 0x21000001, 0x21000000
HITS = ((0, 50.0), (1, 50.0), (0, 3.0))   # (armor, knockback)


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def rf(mu, a):
    return struct.unpack('>f', mu.mem_read(a, 4))[0]


def wf(mu, a, v):
    mu.mem_write(a, struct.pack('>f', v))


def f32(v):
    return struct.unpack('>f', struct.pack('>f', v))[0]


def run(mu, start, stop, regs, count=2000000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(start, stop, count=count)


def prepare(mu):
    """stubs and globals in one machine (BASE or PATCHED)"""
    mu.mem_map(MEM, 0x100000)
    mu.mem_map(0x10471000, 0x10600000 - 0x10471000)    # .bss (the energy constructor reads a zero vector there)
    for lo, hi in ((GRAV_UPDATE, 0x02E81E64), (0x02E76BB4, 0x02E76D94)):     # paired-single saves / loads: nops
        for at in range(lo, hi, 4):
            if r32(mu, at) >> 26 in (4, 56, 57, 60, 61):
                w32(mu, at, 0x60000000)
    w32(mu, 0x0275FF54, 0x4E800020)                   # after the update: blr
    w32(mu, 0x102F6C48, RATES)                         # the rates global: {1.0, 1.0}
    wf(mu, RATES, 1.0)
    wf(mu, RATES + 4, 1.0)
    w32(mu, 0x02E81910, 0x3C600000 | (FDATA >> 16))    # the reset's fighter data lookup -> FDATA (+0x518 = 1.0)
    w32(mu, 0x02E81914, 0x60630000 | (FDATA & 0xFFFF))
    w32(mu, 0x02E81918, 0x60000000)
    wf(mu, FDATA + 0x518, 1.0)
    w32(mu, 0x02E76CBC, 0x60000000)                    # the armor path's two lookups: "not that case" (r3 0)
    w32(mu, 0x02E76CC4, 0x38600000)
    s = Asm(STUBS)
    s.asm("""
getf:                                   # WorkModule vt +0x44: float id -> f1 (PARAMS {id, value}, 0 ends)
        lis r12, 0x%(ph)X
        ori r12, r12, 0x%(pl)X
gf_l:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq gf_z
        cmplw r0, r4
        beq gf_h
        addi r12, r12, 8
        b gf_l
gf_z:
        lis r12, 0x%(rh)X
        ori r12, r12, 0x%(rl)X
        lfs f1, 8(r12)
        blr
gf_h:
        lfs f1, 4(r12)
        blr
flag:                                   # vt +0xE4: flag id -> r3 (FLAGS {id, value})
        lis r12, 0x%(fh)X
        ori r12, r12, 0x%(fl)X
fl_l:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq fl_z
        cmplw r0, r4
        beq fl_h
        addi r12, r12, 8
        b fl_l
fl_z:
        li r3, 0
        blr
fl_h:
        lwz r3, 4(r12)
        blr
geti:                                   # vt +0x84: 0
        li r3, 0
        blr
msc:                                    # vt +0x1CC (MSC handler): log {op, id}; op 0x2711 turns the flag off
        lwz r5, 0(r4)
        lwz r6, 0(r5)
        lwz r7, 4(r5)
        lis r12, 0x%(lh)X
        ori r12, r12, 0x%(ll)X
        lwz r11, 0(r12)
        slwi r10, r11, 3
        add r10, r10, r12
        stw r6, 4(r10)
        stw r7, 8(r10)
        addi r11, r11, 1
        stw r11, 0(r12)
        cmpwi r6, 0x2711
        bne ms_d
        lis r12, 0x%(fh)X
        ori r12, r12, 0x%(fl)X
ms_l:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq ms_d
        cmplw r0, r7
        beq ms_h
        addi r12, r12, 8
        b ms_l
ms_h:
        li r0, 0
        stw r0, 4(r12)
ms_d:
        li r3, 0
        blr
""" % dict(ph=PARAMS >> 16, pl=PARAMS & 0xFFFF, fh=FLAGS >> 16, fl=FLAGS & 0xFFFF, lh=LOG >> 16, ll=LOG & 0xFFFF,
           rh=RATES >> 16, rl=RATES & 0xFFFF))
    for i, w in enumerate(s.words()):
        w32(mu, STUBS + 4 * i, w)
    for off, lab in ((0x44, 'getf'), (0xE4, 'flag'), (0x84, 'geti'), (0x1CC, 'msc')):
        w32(mu, WMVT + off, s.addr(lab))
    for i, (k, v) in enumerate(sorted(DIDDY.items())):
        w32(mu, PARAMS + 8 * i, k)
        wf(mu, PARAMS + 8 * i + 4, v)
    for i, k in enumerate((FF, GROUND_FLAG)):
        w32(mu, FLAGS + 8 * i, k)
        w32(mu, FLAGS + 8 * i + 4, 0)


def set_flag(mu, ident, v):
    for i in range(2):
        if r32(mu, FLAGS + 8 * i) == ident:
            w32(mu, FLAGS + 8 * i + 4, v)


def get_flag(mu, ident):
    return next(r32(mu, FLAGS + 8 * i + 4) for i in range(2) if r32(mu, FLAGS + 8 * i) == ident)


class Fighter:
    """accessor: +0x20 StatusModule (the game's constructor, fighter vtable), +0x28 WorkModule (stub vtable), +0x34
    KineticModule (the fighters' vtable word; its energy 1 at +0x334, made by the game's gravity energy constructor
    and reset)"""
    def __init__(self, mu, base, sm_vt=C.FIGHTER_STATUS_VT):
        self.mu, self.acc = mu, base
        self.sm, self.wm, self.kin = base + 0x100, base + 0x300, base + 0x400
        self.en = self.kin + 0x334
        w32(mu, base + 0x20, self.sm)
        w32(mu, base + 0x28, self.wm)
        w32(mu, base + 0x34, self.kin)
        run(mu, SM_CTOR, RET, {UC_PPC_REG_3: self.sm, UC_PPC_REG_4: base + 0xF00})
        w32(mu, self.sm, sm_vt)
        w32(mu, self.wm, WMVT)
        w32(mu, self.kin, C.FIGHTER_KINETIC_VT)
        run(mu, GRAV_CTOR, RET, {UC_PPC_REG_3: self.en})
        self.reset(0.0)
        self.status(sit=2, kind=0x2C, pending=0x2C)

    def reset(self, vy):
        """the game's own reset, type 0 (a kinetic type change), vertical speed vy"""
        wf(self.mu, VEC, 0.0)
        wf(self.mu, VEC + 4, vy)
        run(self.mu, GRAV_RESET, RET, {UC_PPC_REG_3: self.en, UC_PPC_REG_4: 0, UC_PPC_REG_5: VEC, UC_PPC_REG_6: 0,
                                      UC_PPC_REG_7: self.acc})

    def status(self, sit=None, kind=None, pending=None):
        if sit is not None:
            w32(self.mu, self.sm + 0x84, sit)
        if kind is not None:
            w32(self.mu, self.sm + 0x48, kind)
        if pending is not None:
            w32(self.mu, self.sm + 0x4C, pending)

    def frame(self):
        """one update of the gravity energy (the KineticModule's call: r3 energy, r4 accessor) -> its speed"""
        run(self.mu, GRAV_UPDATE, RET, {UC_PPC_REG_3: self.en, UC_PPC_REG_4: self.acc})
        return round(rf(self.mu, self.en + 4), 4)

    def fields(self):
        return tuple(round(rf(self.mu, self.en + o), 4) for o in (0x24, 0x28))

    def vy(self, v=None):
        if v is not None:
            wf(self.mu, self.en + 4, v)
        return round(rf(self.mu, self.en + 4), 4)

    def entry(self):
        for k in range(C.GS_N):
            e = C.GS + 0x20 * k
            if r32(self.mu, e) == self.acc and self.acc:
                return (r32(self.mu, e + 4) == self.sm, round(rf(self.mu, e + 8), 4), round(rf(self.mu, e + 0xC), 4),
                        r32(self.mu, e + 0x10))
        return None


def model(v, accel, mx, brk=0.016, limit=10.0, n=1):
    """the game's update (0x02E8159C) for the plain case (rates 1, multiplier 1, no flags), n frames -> speeds"""
    out = []
    for _ in range(n):
        a = f32(-accel)
        if f32(v + a) * a > 0:          # falling further: the max fall speed's brake (0x02C54890)
            if mx >= 0 and brk > 0:
                if f32(v + a) < -mx:
                    if mx == 0 or a < brk:
                        a = brk
                    if f32(v + a) > -mx:
                        a = f32(-mx - v)
        v = f32(v + a)
        if v < 0 and abs(v) > limit:
            v = -limit
        out.append(round(v, 4))
    return out


def main():
    patched, base = sys.argv[1:3]
    a, words, hooks = C.build()
    om, pm = machine(base), machine(patched)

    # ---- words
    for at, w in C.GS_ORIG.items():
        check('base: original word at 0x%08X' % at, r32(om, at), w)
        check('patched: 0x%08X -> its hook' % at, r32(pm, at), hooks[at])
    check('base: Gravity_Set space zero', any(r32(om, x) for x in range(C.GS_CODE, C.NV_LIMIT, 4)), False)
    check('code in place', [r32(pm, a.part5[0] + 4 * i) for i in range(len(a.part5[1]))], a.part5[1])
    check('New_Var code (ue_nv: GRAVITY / MAX_FALL go to gs_var) in place',
          [r32(pm, a.part4[0] + 4 * i) for i in range(len(a.part4[1]))], a.part4[1])
    check('Leave_Ground_Cancel code (hk_lgc_chg goes on to gs_chg) in place',
          [r32(pm, a.part3[0] + 4 * i) for i in range(len(a.part3[1]))], a.part3[1])
    crc = zlib.crc32(b'Gravity_Set') & 0xFFFFFFFF
    k = [c[0] for c in C.COMMANDS].index('Gravity_Set')
    run(pm, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
    check('CRC 0x%08X -> index %d' % (crc, C.NEW_BASE + k), pm.reg_read(UC_PPC_REG_3), C.NEW_BASE + k)
    check('handler table: h_gs', r32(pm, a.addr('cmd_handlers') + 4 * k), a.addr('h_gs'))
    check('size 4 words', (C.COMMANDS[k][1], r32(pm, a.addr('cmd_sizes') + 4 * k)), (4, 4))

    for mu in (om, pm):
        prepare(mu)
    f, g = Fighter(pm, MEM + 0x10000), Fighter(pm, MEM + 0x11000)
    fo = Fighter(om, MEM + 0x10000)

    def cmd(who, accel, mx, mode, run_it=True):
        wf(pm, PRM, accel)
        wf(pm, PRM + 4, mx)
        w32(pm, PRM + 8, mode)
        w32(pm, ST + 4, 0x1000)
        w32(pm, ST + 8, -1)
        pm.mem_write(CTX + 8, b'\1' if run_it else b'\0')
        run(pm, a.addr('h_gs'), RET, {UC_PPC_REG_3: who.acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: ST, UC_PPC_REG_6: CTX,
                                        UC_PPC_REG_7: PRM})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, ST + 4) - 0x1000

    def var(who, ident):
        """the game's get_float on the fighter's WorkModule (its {WorkModule, accessor} in the per-frame cache)"""
        w32(pm, C.ACC_CACHE, who.wm)
        w32(pm, C.ACC_CACHE + 4, who.acc)
        pm.reg_write(UC_PPC_REG_FPR1, 0)
        run(pm, FGET, RET, {UC_PPC_REG_3: who.wm, UC_PPC_REG_4: ident})
        return round(struct.unpack('>d', struct.pack('>Q', pm.reg_read(UC_PPC_REG_FPR1)))[0], 4)

    # ---- the game's own curve
    check('reset (type 0) from the params: acceleration -0.105, max fall 1.75', f.fields(), (-0.105, 1.75))
    plain = [f.frame() for _ in range(22)]
    check('no Gravity_Set: the game\'s curve (= BASE\'s, frame by frame)', plain, [fo.frame() for _ in range(22)])
    check('  = the model: -0.105 a frame, held at -1.75', plain, model(0.0, 0.105, 1.75, n=22))
    check('  GRAVITY / MAX_FALL read the fighter\'s own', (var(f, 0x0F000337), var(f, 0x0F000338)), (0.105, 1.75))

    # ---- Gravity_Set(0.02, 0.6)
    f.reset(0.0)
    check('Gravity_Set(0.02, 0.6, 0): returns 2, steps 4 words', cmd(f, 0.02, 0.6, 0), (2, 16))
    check('  entry: the fighter, 0.02, 0.6, mode 0', f.entry(), (True, 0.02, 0.6, 0))
    check('  GRAVITY / MAX_FALL: 0.02 / 0.6', (var(f, 0x0F000337), var(f, 0x0F000338)), (0.02, 0.6))
    floaty, own = [], set()
    for _ in range(36):
        floaty.append(f.frame())
        own.add(f.fields())
    check('  the curve: -0.02 a frame, held at -0.6', floaty, model(0.0, 0.02, 0.6, n=36))
    check('  after every update the energy holds the fighter\'s own values again', own, {(-0.105, 1.75)})
    f.reset(-0.3)                                    # a kinetic type change mid-move: the game's reset
    check('a reset in between (the game\'s, from the params): its own values', f.fields(), (-0.105, 1.75))
    check('  the next updates still use Gravity_Set\'s', [f.frame() for _ in range(3)], model(-0.3, 0.02, 0.6, n=3))
    check('other fighter (no Gravity_Set): its own curve', [g.frame() for _ in range(3)], model(0.0, 0.105, 1.75, n=3))

    cmd(f, 0.5, 0.5, 1)
    f.reset(0.0)
    check('Mode 1 (0.5, 0.5): half gravity, half max fall', [f.frame() for _ in range(20)],
          model(0.0, 0.0525, 0.875, n=20))
    check('  GRAVITY / MAX_FALL: 0.0525 / 0.875', (var(f, 0x0F000337), var(f, 0x0F000338)), (0.0525, 0.875))
    cmd(f, -1.0, 0.6, 0)
    f.reset(0.0)
    check('Accel -1 (its own), MaxFall 0.6', [f.frame() for _ in range(8)], model(0.0, 0.105, 0.6, n=8))
    cmd(f, 0.02, 0.6, 0)
    f.vy(-1.5)
    check('falling at 1.5 with MaxFall 0.6: slows by the brake (0.016) as the game does', f.frame(),
          model(-1.5, 0.02, 0.6)[0])
    cmd(f, 0.02, 0.6, 2)
    f.vy(-1.5)
    check('Mode 2: cut to -0.6 at once', [f.frame() for _ in range(3)], [-0.6, -0.6, -0.6])
    cmd(f, 0.0, 0.6, 0)
    f.vy(-0.3)
    check('Accel 0: the speed stays', [f.frame() for _ in range(3)], [-0.3, -0.3, -0.3])
    cmd(f, 0.02, 0.6, 0)
    set_flag(pm, FF, 1)
    f.vy(-0.5)
    check('fast-fall flag on, Mode 0: the game\'s fast fall (-2.8), flag kept', (f.frame(), get_flag(pm, FF)),
          (-2.8, 1))
    cmd(f, 0.02, 0.6, 4)
    w32(pm, LOG, 0)
    f.vy(-0.5)
    check('Mode 4: the fast-fall flag off (WorkModule(0x2711, 0x21000001)), gravity goes on',
          (f.frame(), get_flag(pm, FF), r32(pm, LOG), r32(pm, LOG + 4), r32(pm, LOG + 8)),
          (model(-0.5, 0.02, 0.6)[0], 0, 1, 0x2711, FF))
    check('skipped: steps only, nothing changed', (cmd(f, 0.1, 1.0, 0, run_it=False), f.entry()),
          ((2, 16), (True, 0.02, 0.6, 4)))
    check('Accel and MaxFall -1, Mode 0: off', (cmd(f, -1.0, -1.0, 0), f.entry()), ((2, 16), None))
    f.reset(0.0)
    check('  its own curve again', [f.frame() for _ in range(4)], model(0.0, 0.105, 1.75, n=4))
    pm.mem_write(MEM + 0x18000, bytes(pm.mem_read(C.FIGHTER_STATUS_VT, 0x200)))
    w = Fighter(pm, MEM + 0x12000, sm_vt=MEM + 0x18000)
    check('not a fighter (another StatusModule class): steps only, no entry', (cmd(w, 0.02, 0.6, 0), w.entry()),
          ((2, 16), None))

    # ---- ends: status change, hit, ledge
    def armed(**st):
        f.status(sit=2, kind=0x2C, pending=0x2C)
        f.status(**st)
        cmd(f, 0.02, 0.6, 0)
        cmd(g, 0.03, 0.7, 0)
        f.reset(0.0)
    armed()
    run(pm, C.LGC_CHG, C.LGC_CHG + 4, {UC_PPC_REG_30: f.sm, UC_PPC_REG_28: 0x0E})
    check('status change (0x02E88B40): +0x4C the new kind, the fighter\'s entry gone, the other\'s kept',
          (r32(pm, f.sm + 0x4C), f.entry(), g.entry()), (0x0E, None, (True, 0.03, 0.7, 0)))
    check('  its own curve from the next update', [f.frame() for _ in range(3)], model(0.0, 0.105, 1.75, n=3))

    def set_threshold(v):
        for mu in (pm, om):
            for i, (kk, _v) in enumerate(sorted(DIDDY.items())):
                if kk == 0x2A:
                    wf(mu, PARAMS + 8 * i + 4, v)

    def hit(armor, kb, who=None):
        """the game's damage reaction decision (0x02E76BB4: r4 accessor, r5 the hit, r6 armor) -> r3"""
        who = who or f
        mu = who.mu
        wf(mu, REC + 0x10, kb)                       # knockback
        mu.mem_write(REC + 0x3D, b'\0')
        mu.mem_write(REC + 0x87, b'\0')
        run(mu, 0x02E76BB4, RET, {UC_PPC_REG_3: 0, UC_PPC_REG_4: who.acc, UC_PPC_REG_5: REC, UC_PPC_REG_6: armor})
        return mu.reg_read(UC_PPC_REG_3)
    armed()
    check('a hit that takes effect (no armor, knockback 50 > 0): reaction (0), entry gone at once',
          (hit(0, 50.0), f.entry(), g.entry() is not None), (0, None, True))
    check('  the very next update (same frame, no status change yet) uses the fighter\'s own',
          f.frame(), model(0.0, 0.105, 1.75)[0])
    armed()
    check('armored hit (armor 1, knockback 50): no reaction (1), Gravity_Set kept', (hit(1, 50.0), f.entry()),
          (1, (True, 0.02, 0.6, 0)))
    set_threshold(5.0)
    check('a hit under the fighter\'s knockback threshold (work float 0x2A = 5, knockback 3): no reaction, kept',
          (hit(0, 3.0), f.entry()), (1, (True, 0.02, 0.6, 0)))
    check('  still floaty', f.frame(), model(0.0, 0.02, 0.6)[0])
    check('the decision itself is the game\'s: the same results as BASE for the same hits',
          [hit(*c) for c in HITS], [hit(*c, who=fo) for c in HITS])
    set_threshold(0.0)

    for what, st, ends in (('situation 1 (on a ledge)', dict(sit=1), True),
                           ('CliffCatch (0x73) pending, still in the air', dict(pending=0x73), True),
                           ('CliffCatchMove (0x72) as the status', dict(kind=0x72), True),
                           ('CliffJumpQuick2 (0x79)', dict(kind=0x79), True),
                           ('AirCatchHit (0xF3, a tether on the ledge)', dict(kind=0xF3), True),
                           ('AirCatchHang (0xF4)', dict(pending=0xF4), True),
                           ('Ottotto (0x7B, teetering, not a ledge grab)', dict(kind=0x7B), False),
                           ('Pass (0x71)', dict(pending=0x71), False)):
        armed(**st)
        v = f.frame()
        check('ledge: %s -> %s' % (what, 'its own values, entry gone' if ends else 'kept'),
              (v, f.entry() is None, g.entry() is not None),
              (model(0.0, 0.105 if ends else 0.02, 1.75 if ends else 0.6)[0], ends, True))
    armed(sit=1)
    check('ledge: GRAVITY reads the fighter\'s own (and ends it)', (var(f, 0x0F000337), f.entry()), (0.105, None))
    f.status(sit=2, kind=0x2C, pending=0x2C)
    check('other IDs: 0x0F000339 reads 0', var(f, 0x0F000339), 0.0)

    # ---- table full
    for kk in range(C.GS_N):
        w32(pm, C.GS + 0x20 * kk, 0)
    many = [Fighter(pm, MEM + 0x20000 + 0x1000 * kk) for kk in range(C.GS_N + 1)]
    for x in many:
        cmd(x, 0.02, 0.6, 0)
    check('16 entries, then the 17th takes entry 0', [r32(pm, C.GS + 0x20 * kk) for kk in range(C.GS_N)],
          [many[16].acc] + [x.acc for x in many[1:16]])

    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
