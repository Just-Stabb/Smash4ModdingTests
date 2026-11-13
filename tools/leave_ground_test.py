#!/usr/bin/env python3
"""Tests Leave_Ground_Cancel (tools/acmd_ext_cave.py, docs/acmd-extra-commands.md) in a patched RPX (unicorn).

  python3 tools/leave_ground_test.py PATCHED.rpx BASE.rpx

BASE is the executable it was built on: before Leave_Ground_Cancel (exe_v38: the hook words held what LGC_ORIG says,
the trampolines and the table / code space were zero), or an earlier build of it (exe_v39 / v40: the hooks branch to
the trampolines / the code). The fake fighters' StatusModules are made by the game's own constructor (0x02E881A8), so
its +4 is what the game has there (not the accessor: exe_v39 read the accessor there, the edge-slide bug). On PATCHED:
- the CRC lookup (0x02BEE154) gives Leave_Ground_Cancel its index, the handler table its handler;
- the command (h_lgc, as the interpreter calls it): Enabled 0 / 2 / 1 set / change / clear the fighter's entry, and
  on the ground give an edge-stopping move (ground correction 2) correction 1 / back its own through GroundModule
  (0x2710); a move that slides off edges anyway (1) gets no call; a skipped command only steps; a non-fighter
  (another StatusModule vtable) gets nothing;
- the situation read, through the fighters' own MSC StatusModule handler (0x02E882AC -> 0x0200D6D8 op 1): in the
  air through it, KineticModule(0, 0) + GroundModule(0x2710, 5) once, the kinetic type kept; landed, that type and
  the move's correction back; an air status (correction 5) and a fighter with no entry: nothing; the situation
  itself returned unchanged;
- the status request, through the same handler (op 3, `StatusModule(3, 0xE, 0)` = the status loops' Fall): dropped
  (StatusModule +0x54 and +0x96 untouched) while in the air through it with the motion going (MotionModule(0x2712)
  stubbed) and the cancel window shut (the game's own fighter CancelModule handler 0x02E6FCFC, byte +0x10); stored
  as normal when the motion has ended, the cancel window is open, the leave-ground cancel is on, the request isn't
  Fall, the fighter is on the ground, or has no entry;
- a status change (0x02E88B40 in 0x02E88B28): +0x4C written as before and the fighter's entry cleared, the others
  kept;
- the table: 16 fighters fill it, the 17th / 18th take entries 0 / 1 in turn.
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
                               UC_PPC_REG_7, UC_PPC_REG_28, UC_PPC_REG_30, UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0
CRC_TABLE, HANDLERS = 0x100FAAB8, 0x10350ED8
MEM = 0x7E000000                 # fake objects (mapped here)
STUB = MEM                       # stub module handler
LOG = MEM + 0x9000               # +0 count, then {module, op, arg} records
ARGS = MEM + 0xA000              # MSC args: {words, count} at +0, words at +0x10
ST, CTX, PRM = MEM + 0xB000, MEM + 0xB100, MEM + 0xB200
SM_CTOR = 0x02E881A8             # the fighters' StatusModule constructor (r3 this, r4 the fighter)


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def run(mu, start, stop, regs, count=500000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(start, stop, count=count)


class Fighter:
    """a fake fighter: accessor with StatusModule (the real fighter vtable), Kinetic / Ground / Motion modules (stub
    handlers that log), CancelModule (the real fighter CancelModule vtable)"""
    def __init__(self, mu, base, sm_vt=C.FIGHTER_STATUS_VT):
        self.mu, self.acc = mu, base
        self.sm, self.kin, self.gnd, self.mot, self.can = (base + 0x200 * k for k in range(1, 6))
        vt = base + 0xE00                # one stub vtable serves the three stubbed modules
        for off in (0x114, 0x4BC, 0x2D4):
            w32(mu, vt + off, STUB)
        for k, m in ((0x20, self.sm), (0x34, self.kin), (0x2C, self.gnd), (0x44, self.mot), (0x94, self.can)):
            w32(mu, base + k, m)
        for m in (self.kin, self.gnd, self.mot):
            w32(mu, m, vt)
        # the StatusModule made by the game's own constructor (0x02E881A8: base 0x0200D588, +0x9C = its fighter, the
        # fighter vtable): its +4 is an embedded list (first word 8), not the accessor (exe_v39's hooks read it as one)
        run(mu, SM_CTOR, RET, {UC_PPC_REG_3: self.sm, UC_PPC_REG_4: base + 0xF00})
        w32(mu, self.sm, sm_vt)
        w32(mu, self.can, 0x1012B0C4)    # fighter CancelModule vtable (vt +0x4C = 0x02E6FCFC)
        w32(mu, self.can + 4, base)
        self.set(sit=0, correct=2, kinetic=0xF, ended=0, cancel=0)

    def set(self, sit=None, correct=None, kinetic=None, ended=None, cancel=None):
        mu = self.mu
        if sit is not None:
            w32(mu, self.sm + 0x84, sit)
        if correct is not None:
            w32(mu, self.sm + 0x78, correct)
        if kinetic is not None:
            w32(mu, self.kin + 0x11C, kinetic)
        if ended is not None:
            w32(mu, self.mot + 0x10, ended)
        if cancel is not None:
            mu.mem_write(self.can + 0x10, bytes([cancel]))

    def entry(self):
        for k in range(C.LGC_N):
            e = C.LGC + 0x10 * k
            if r32(self.mu, e) == self.sm:
                return r32(self.mu, e + 4), r32(self.mu, e + 8)
        return None


def log(mu):
    n = r32(mu, LOG)
    return [struct.unpack('>3I', mu.mem_read(LOG + 4 + 12 * k, 12)) for k in range(n)]


def main():
    patched, base = sys.argv[1:3]
    a, words, hooks = C.build()
    om, pm = machine(base), machine(patched)

    # ---- words (BASE: the executable before Leave_Ground_Cancel, or an earlier build of it: exe_v39 / v40)
    def b_to(mu, at):
        w = r32(mu, at)
        if w >> 26 != 18 or w & 3:
            return None
        off = w & 0x3FFFFFC
        return at + (off - 0x4000000 if off & 0x2000000 else off)
    earlier = r32(om, C.LGC_CHG) != C.LGC_ORIG[C.LGC_CHG]
    for at, w in C.LGC_ORIG.items():
        if not earlier:
            check('base: original word at 0x%08X' % at, r32(om, at), w)
        else:
            want = C.LGC_TRAMP.get(at)
            got = b_to(om, at)
            check('base (an earlier Leave_Ground_Cancel build): 0x%08X branches to its %s' % (
                at, 'trampoline' if want else 'code'), got == want if want else C.LGC_CODE <= (got or 0) < C.OBJS, True)
    for at in C.LGC_TRAMP.values():
        if not earlier:
            check('base: trampoline 0x%08X was zero' % at, r32(om, at), 0)
        else:
            check('base: trampoline 0x%08X goes to the code' % at, C.LGC_CODE <= (b_to(om, at) or 0) < C.OBJS, True)
    if not earlier:
        check('base: table and code space zero', any(r32(om, x) for x in range(C.LGC, C.OBJS, 4)), False)
    check('code in place', [r32(pm, a.part3[0] + 4 * i) for i in range(len(a.part3[1]))], a.part3[1])
    for at in list(C.LGC_ORIG) + list(C.LGC_TRAMP.values()):
        check('hook word at 0x%08X' % at, r32(pm, at), hooks[at])
    for at, t in C.LGC_TRAMP.items():
        off = r32(pm, t) & 0x3FFFFFC
        dest = t + (off - 0x4000000 if off & 0x2000000 else off)
        check('0x%08X -> trampoline -> %s' % (at, 'hk_lgc_sit' if at == C.LGC_SIT else 'hk_lgc_req'), dest,
              a.addr('hk_lgc_sit' if at == C.LGC_SIT else 'hk_lgc_req'))

    crc = zlib.crc32(b'Leave_Ground_Cancel') & 0xFFFFFFFF
    k = [c[0] for c in C.COMMANDS].index('Leave_Ground_Cancel')
    run(pm, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
    check('CRC 0x%08X -> index %d' % (crc, C.NEW_BASE + k), pm.reg_read(UC_PPC_REG_3), C.NEW_BASE + k)
    check('handler table: h_lgc', r32(pm, a.addr('cmd_handlers') + 4 * k), a.addr('h_lgc'))
    check('size 2 words', C.COMMANDS[k][1], 2)

    # ---- fakes
    pm.mem_map(MEM, 0x100000)
    stub = Asm(STUB)
    stub.asm("""
        lwz r5, 0(r4)
        lis r12, 0x%X
        ori r12, r12, 0x%X
        lwz r11, 0(r12)
        mulli r10, r11, 12
        add r10, r10, r12
        stw r3, 4(r10)
        lwz r0, 0(r5)
        stw r0, 8(r10)
        lwz r0, 4(r5)
        stw r0, 12(r10)
        addi r11, r11, 1
        stw r11, 0(r12)
        lwz r3, 0x10(r3)
        blr
""" % (LOG >> 16, LOG & 0xFFFF))
    for i, w in enumerate(stub.words()):
        w32(pm, STUB + 4 * i, w)
    f = Fighter(pm, MEM + 0x10000)
    g = Fighter(pm, MEM + 0x20000)
    pm.mem_write(MEM + 0x8000, bytes(pm.mem_read(C.FIGHTER_STATUS_VT, 0x200)))
    w = Fighter(pm, MEM + 0x30000, sm_vt=MEM + 0x8000)    # another StatusModule class (the same methods)

    def cmd(who, enabled, run_it=True):
        w32(pm, LOG, 0)
        w32(pm, PRM, enabled)
        w32(pm, ST + 4, 0x1000)
        w32(pm, ST + 8, -1)
        pm.mem_write(CTX + 8, b'\1' if run_it else b'\0')
        run(pm, a.addr('h_lgc'), RET, {UC_PPC_REG_3: who.acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: ST,
                                         UC_PPC_REG_6: CTX, UC_PPC_REG_7: PRM})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, ST + 4) - 0x1000, log(pm)

    def msc(who, *ws):
        """the fighters' own MSC StatusModule handler: StatusModule(ws...)"""
        w32(pm, LOG, 0)
        for i, v in enumerate(ws):
            w32(pm, ARGS + 0x10 + 4 * i, v)
        w32(pm, ARGS, ARGS + 0x10)
        w32(pm, ARGS + 4, len(ws))
        run(pm, 0x02E882AC, RET, {UC_PPC_REG_3: who.sm, UC_PPC_REG_4: ARGS})
        return pm.reg_read(UC_PPC_REG_3), log(pm)

    G, K = f.gnd, f.kin
    check('the game-built StatusModule: +4 holds 8 (an embedded list), +0x9C its fighter, not the accessor',
          (r32(pm, f.sm + 4), r32(pm, f.sm + 0x9C)), (8, f.acc + 0xF00))
    # ---- the command
    check('Enabled 0 on the ground, edge-stopping move (2): returns 2, steps 2 words, GroundModule(0x2710, 1)',
          cmd(f, 0), (2, 8, [(G, 0x2710, 1)]))
    check('  entry: state 1 (off)', f.entry(), (1, 0))
    check('Enabled 2: GroundModule(0x2710, 2) (its own: edges stop it)', cmd(f, 2)[2], [(G, 0x2710, 2)])
    check('  entry: state 5 (off, edges kept)', f.entry(), (5, 0))
    check('Enabled 1: GroundModule(0x2710, 2), state 0 (on)', (cmd(f, 1)[2], f.entry()), ([(G, 0x2710, 2)], (0, 0)))
    check('skipped: steps only, nothing changed', (cmd(f, 0, run_it=False), f.entry()), ((2, 8, []), (0, 0)))
    check('not a fighter: steps only, no entry', (cmd(w, 0), w.entry()), ((2, 8, []), None))
    g.set(correct=1)
    check('a move that slides off edges (1): no GroundModule call, state 1', (cmd(g, 0)[2], g.entry()), ([], (1, 0)))

    # ---- situation reads (the MSC main's global18 = StatusModule(1))
    f.set(sit=0, correct=2, kinetic=0xF)
    cmd(f, 0)
    check('on the ground: situation 0, no calls', msc(f, 1), (0, []))
    f.set(sit=2)
    check('left the ground: situation 2, KineticModule(0, 0), GroundModule(0x2710, 5)', msc(f, 1),
          (2, [(K, 0, 0), (G, 0x2710, 5)]))
    check('  entry: state 3, kinetic type 0xF kept', f.entry(), (3, 0xF))
    check('in the air again: no calls', msc(f, 1), (2, []))
    f.set(sit=0)
    check('landed: KineticModule(0, 0xF), GroundModule(0x2710, 1) (still off: slides off edges)', msc(f, 1),
          (0, [(K, 0, 0xF), (G, 0x2710, 1)]))
    check('  entry: state 1', f.entry(), (1, 0xF))
    cmd(f, 2)
    f.set(sit=2, kinetic=6)
    msc(f, 1)
    cmd(f, 1)                                        # back on in the air
    check('  back on in the air: state 2', f.entry(), (2, 6))
    f.set(sit=0)
    check('  landed: KineticModule(0, 6), GroundModule(0x2710, 2) (its own)', msc(f, 1)[1],
          [(K, 0, 6), (G, 0x2710, 2)])
    g.set(sit=2, correct=5)
    cmd(g, 0)
    check('an air status (correction 5) off in the air: nothing', (msc(g, 1), g.entry()), ((2, []), (1, 0)))
    check('no entry (not a fighter): situation only', msc(w, 1), (0, []))

    # ---- the Fall request (op 3), through the fighters' handler
    def request(who, kind, **kw):
        who.set(**kw)
        w32(pm, who.sm + 0x54, -1)
        pm.mem_write(who.sm + 0x96, b'\x77')
        r, calls = msc(who, 3, kind, 0)
        return r32(pm, who.sm + 0x54), pm.mem_read(who.sm + 0x96, 1)[0], [c[1] for c in calls]
    f.set(sit=0, correct=2, kinetic=0xF, ended=0, cancel=0)
    cmd(f, 0)
    f.set(sit=2)
    msc(f, 1)                                        # in the air through it: state 3
    check('Fall asked in the air, motion going, cancel shut: dropped (+0x54, +0x96 untouched)',
          request(f, 0xE), (0xFFFFFFFF, 0x77, [0x2712]))
    check('motion ended: Fall stored', request(f, 0xE, ended=1)[:2], (0xE, 0))
    check('cancel window open (byte +0x10): Fall stored', request(f, 0xE, ended=0, cancel=1)[:2], (0xE, 0))
    check('another request (Wait 0): stored', request(f, 0, cancel=0)[:2], (0, 0))
    cmd(f, 1)
    check('back on: Fall stored', request(f, 0xE)[:2], (0xE, 0))
    cmd(f, 0)
    check('off again, still marked in the air: dropped', request(f, 0xE)[:2], (0xFFFFFFFF, 0x77))
    f.set(sit=0)
    check('on the ground: Fall stored', request(f, 0xE)[:2], (0xE, 0))
    check('no entry: stored', request(w, 0xE, sit=2)[:2], (0xE, 0))
    g2 = Fighter(pm, MEM + 0x40000)
    cmd(g2, 0)
    check('off, on the ground through it but the situation says air (not marked yet): stored',
          request(g2, 0xE, sit=2)[:2], (0xE, 0))

    # ---- status change
    f.set(sit=2)
    msc(f, 1)
    before = g.entry()
    run(pm, C.LGC_CHG, C.LGC_CHG + 4, {UC_PPC_REG_30: f.sm, UC_PPC_REG_28: 0x27})
    check('status change: +0x4C = the new kind, entry gone, the other fighter\'s kept',
          (r32(pm, f.sm + 0x4C), f.entry(), g.entry()), (0x27, None, before))
    check('  then a Fall request is stored', request(f, 0xE, sit=2)[:2], (0xE, 0))

    # ---- table full
    for k in range(C.LGC_N):
        w32(pm, C.LGC + 0x10 * k, 0)
    w32(pm, C.LGC + C.LGC_N * 0x10, 0)
    many = [Fighter(pm, MEM + 0x50000 + 0x1000 * k) for k in range(C.LGC_N + 2)]
    for x in many:
        cmd(x, 0)
    check('16 entries, then the 17th / 18th take entries 0 / 1',
          [r32(pm, C.LGC + 0x10 * k) for k in range(C.LGC_N)],
          [many[16].sm, many[17].sm] + [x.sm for x in many[2:16]])

    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
