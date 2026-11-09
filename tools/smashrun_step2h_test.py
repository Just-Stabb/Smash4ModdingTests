#!/usr/bin/env python3
"""Behaviour tests of step 2h's Smash Run kinds (tools/smashrun_walker_cave.py, region H; docs/smash-run-port.md
"Step 2h") on a patched executable, in unicorn with smashrun_walker_test.py's stubbed world (ground / walls /
ledges / search / speed / motion end stubbed, x moved by the AI stick):

  python3 tools/smashrun_step2h_test.py PATCHED.rpx [ENEMY_ROOT]

- the stomp bounce: u_bounce writes the fighter's tread multiplier (status float 0x1000006: CFG BOUNCE, else the
  enemy's work float 0x11 = W+0x44, the param the Enemy's event 6 answers) and zeroes its step count (int
  0x10000006); u_pend writes it again while the fighter is in StepJump (0xB3) and stops once it has left it; the
  game's own StepJump speed (0x02E79938, run natively) then gives y = step_jump_speed_y x the multiplier;
- Big Goomba (dekakuribo): the vtable (slot 45 empty, slot 20 its tread handler, 64-67), initialize, every state's
  3DS transitions, the stomp's HP (25 a stomp: Stepped, then Collapses), its ACMD hitboxes reachable (the hashsets
  are the 3DS table and hold every attack.bin script; ENEMY_ROOT's converted attack.bin holds the readings' boxes).
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_LR  # noqa: E402

check = T.check
OBJ, ACC, POSTURE, EN, INPUT, HEAP = T.OBJ, T.ACC, T.POSTURE, T.EN, T.INPUT, T.HEAP
DMG = HEAP + 0x30000                       # the DamageModule (acc+0x30D4; only its damage is modelled)
FT, TBL, ENTS, FACC, FPOST, FSTAT, FWM, FWMVT, F24, F24VT = (HEAP + 0x34000 + 0x100 * i for i in range(10))
WM_GETF, WM_GETI, WM_FLAG, F24_F4, POWF = 0x02000018, 0x0200001C, 0x02000020, 0x02000024, 0x04ADECB0
NODE_DIRTY, MODEL = 0x02000028, HEAP + 0x30200
PMGR, GLTAB = HEAP + 0x25000, HEAP + 0x26000


class M(T.Machine):
    STUBS = {}
    """smashrun_walker_test's machine plus step 2h's calls: the damage (get_damage / set_current_damage keep
    HP = max - damage in W), the target's position, the fighter's WorkModule reads (the StepJump speed)"""

    def __init__(self, img):
        T.Machine.__init__(self, img)
        self.damage, self.maxhp, self.params = 0.0, 40.0, {}
        self.w32(ACC + 0x30D4, DMG)
        self.w32(W.PARAM_MGR, PMGR)              # the gl entries: every kind / variation -> entry 0, +0x154 30
        self.w32(PMGR + W.GL_BASE, GLTAB)        # (the hit stun frames)
        self.w32(GLTAB + 0x154, 30)
        self.w32(ACC + 0x3118, MODEL)            # the ModelModule: vt+0xC4 (a node changed) stubbed
        self.w32(MODEL, MODEL + 0x10)
        self.w32(MODEL + 0x10 + W.MODEL_NODE_DIRTY, NODE_DIRTY)
        self.w32(MODEL + 0x10 + W.MM_SET_VIS, T.VIS_STUB)     # step 2i: set_visibility(bool)
        self.wf(EN, self.maxhp)
        self.wf(EN + 4, self.maxhp)

    def hook(self, u, addr, size, x):
        r = lambda n: u.reg_read(T.R[n])  # noqa: E731
        c = self.calls
        if addr == W.GET_DAMAGE:
            self.wfr(1, self.damage)
            return self.ret()
        if addr == W.SET_CUR_DAMAGE:
            self.damage = self.fr(1)
            c.append(('set_damage', r(3), round(self.damage, 3)))
            self.wf(EN, self.rf(EN + 4) - self.damage)
            return self.ret()
        if addr == W.GET_TARGET_POS:
            c.append(('target_pos', r(5)))
            self.wf(r(3), self.target_x)
            self.wf(r(3) + 4, getattr(self, 'target_y', 0.0))
            self.wf(r(3) + 8, 0.0)
            return self.ret()
        if addr in M.STUBS:                      # step 2h: the aerial helpers (tested in smashrun_flier_test.py)
            name = M.STUBS[addr]
            if name == 'f_amode':
                c.append(('amode', r(4), round(self.rf(u.reg_read(T.R[1]) + 8), 3),
                          round(self.rf(u.reg_read(T.R[1]) + 0xC), 3)))
            else:
                c.append((name,))
            return self.ret()
        if addr in (W.AER_CTOR, W.DISABLE_HIT, W.DISABLE_TREAD):
            c.append(({W.AER_CTOR: 'aer_ctor', W.DISABLE_HIT: 'disable_hit', W.DISABLE_TREAD: 'disable_tread'}[addr],))
            return self.ret()
        if addr == W.CREATE_THROW:
            sp = r(6)
            c.append(('throw', r(4), r(5), tuple(round(self.rf(sp + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(7) + 4 * i), 3) for i in range(2)), round(self.fr(1), 3), r(8),
                      r(9) - (1 << 32) if r(9) >= 1 << 31 else r(9), r(10) - (1 << 32) if r(10) >= 1 << 31 else r(10)))
            return self.ret(0x5000)
        if addr == NODE_DIRTY:
            c.append(('dirty',))
            return self.ret()
        if addr == W.GET_SPEED:
            self.wf(r(3), getattr(self, 'vx', 0.0))
            self.wf(r(3) + 4, self.vy)
            self.wf(r(3) + 8, 0.0)
            return self.ret()
        if addr == W.SET_NODE_ROT:
            c.append(('node_rot', r(4), round(self.rf(r(5)), 4)))
            return self.ret(1)
        if addr == W.HIT_FACTOR:
            self.wfr(1, 1.5)
            return self.ret()
        if addr == W.REQ_FOLLOW:
            c.append(('follow', r(4), r(5)))
            return self.ret(0x7777)
        if addr == WM_GETF:
            self.wfr(1, self.work.get((r(3), r(4)), self.params.get(r(4), 0.0)))
            return self.ret()
        if addr == WM_GETI:
            return self.ret(self.work.get((r(3), r(4)), 0))
        if addr == WM_FLAG:
            return self.ret(0)
        if addr == F24_F4:
            self.wfr(1, 0.0)
            return self.ret()
        if addr == POWF:
            self.wfr(1, math.pow(self.fr(1), self.fr(2)))
            return self.ret()
        return T.Machine.hook(self, u, addr, size, x)

    def walker(self, cfg, **kw):
        """as create leaves it: the vptr is the kind's own vtable (CFG VT)"""
        T.Machine.walker(self, cfg, **kw)
        self.w32(OBJ + 0xE0, self.r32(cfg + W.CF['VT']))

    def wfr(self, n, v):
        self.uc.reg_write(T.FR[n], struct.unpack('>Q', struct.pack('>d', v))[0])

    def fighter(self, y=20.0, x=0.0, status=0x1D, situation=W.SITU_AIR):
        self.w32(W.FIGHTERS, FT)
        self.w32(FT, TBL)
        self.w32(TBL, ENTS)
        self.w32(TBL + 8, 1)
        self.uc.mem_write(ENTS + 0x1E, bytes([4]))
        self.w32(ENTS + 0xC, FACC)
        self.w32(FACC + 0x18, FPOST)
        self.w32(FACC + 0x20, FSTAT)
        self.w32(FACC + 0x24, F24)
        self.w32(FACC + 0x28, FWM)
        self.w32(FWM, FWMVT)
        for o, a in ((W.WM_SET_FLOAT, T.WM_SETF), (W.WM_SET_INT, T.WM_SETI), (0x44, WM_GETF), (0x84, WM_GETI),
                     (0xE4, WM_FLAG)):
            self.w32(FWMVT + o, a)
        self.w32(F24, F24VT)
        self.w32(F24VT + 0xF4, F24_F4)
        self.w32(FSTAT + W.STATUS_KIND, status)
        self.w32(FSTAT + W.STATUS_SITU, situation)     # step 2r: the stomp needs the fighter in the air (2)
        self.wf(FPOST + 0x10, x)
        self.wf(FPOST + 0x14, y)
        self.params = {}


def spiny(img, fn, D, cfg, byname, world, enter_calls, stomp, vslot):
    """Spiny (togezo 0x4E): the egg (variation 0) and the Spiny (1)"""
    n = 'togezo'
    w = byname[n]
    pv = lambda i: W.P(i)  # noqa: E731
    ok = (vslot(n, 40) == fn['tg_init'] and vslot(n, 45) == fn['tg_atk'] and vslot(n, 66) == fn['tg_66'] and
          vslot(n, 67) == fn['tg_67'] and img.u32(cfg[n] + W.CF['TREAD']) == 0 and
          img.u32(cfg[n] + W.CF['FSTART']) == fn['tgv_start'] and img.u32(cfg[n] + W.CF['F69']) == fn['tg_69'] and
          vslot(n, 60) == fn['tg_60'])
    check(ok, 'togezo: vtable 40 its per-variation initialize, 45 its set_attack_data, 60 its own (step 2i), 66 / 67 by '
          'variation, start (step 2i: tgv_start, the meshes, then tg_start), slot 69 its own; TREAD 0 (never stomped: '
          'its tread area is off)')
    atk = lambda calls: [c[2] for c in calls if c[0] == 'atk_create']  # noqa: E731
    # start: var 1 -> 6 with the body (P2[1], angle 70); var 0 -> 1 with the egg's (P2[0], angle 361)
    res = {}
    for var in (0, 1):
        m = M(img)
        m.walker(cfg[n], state=0, kind=0x4E, var=var)
        m.call(fn['tg_start'], {3: OBJ})
        res[var] = ([c[2] for c in m.calls if c[0] == 'chgi'], atk(m.calls), m.r32(OBJ + W.V(1)),
                    m.r32(OBJ + W.V(2)), [c for c in m.calls if c[0] in ('reverse_lr', 'check_turn')])
    check(res[0][:4] == ([1], [D['tg_egg']], 200, 150) and res[1][:4] == ([6], [D['tg_body']], 200, 150) and
          not res[0][4] and not res[1][4],
          'togezo start: var 0 => 1 (egg fall) with P2[0] (angle 361), var 1 => 6 (fall) with P2[1] (angle 70) as id 0; '
          'the walk / search timers 200 / 150; no turn to a target %s' % res)
    # initialize per variation
    got = {}
    for var in (0, 1):
        m = M(img)
        m.walker(cfg[n], state=0, kind=0x4E, var=var)
        m.call(fn['tg_init'], {3: OBJ})
        got[var] = tuple(round(m.rf(EN + o), 3) for o in (8, 0xC, 0x10, 0x20, 0x24, 0x28, 0x2C, 0x38))
    check(got == {0: (0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4), 1: (0.3, 0.0, 0.3, 0.01, 1.75, 0.01, 1.75, 0.4)},
          'togezo initialize (0x370C0) by variation: W +0x08 / +0x0C / +0x10 / +0x20 / +0x24 / +0x28 / +0x2C / +0x38 '
          '%s' % got)
    # set_attack_data: id 0 is always armed: 4 the egg's dead body (P2[2]), 12 the Spiny's (P2[3]), else the body
    got = {}
    for var, state in ((0, 1), (0, 4), (1, 8), (1, 12), (1, 11)):
        m = M(img)
        m.walker(cfg[n], state=state, kind=0x4E, var=var)
        m.call(fn['tg_atk'], {3: OBJ, 4: state})
        got[(var, state)] = (atk(m.calls), [c[2:4] for c in m.calls if c[0] == 'atk_set'])
    check(got == {(0, 1): ([D['tg_egg']], [(0, 0)]), (0, 4): ([D['tg_eggdead']], [(0, 0)]),
                  (1, 8): ([D['tg_body']], [(0, 0)]), (1, 12): ([D['tg_dead']], [(0, 0)]),
                  (1, 11): ([D['tg_body']], [(0, 0)])},
          'togezo set_attack_data: the spikes (id 0) in every state, the dead bodies in 4 / 12 %s' % got)
    # the egg: 1 falls (Paipo, spinning) -> 2 bounces -> slow on landing -> the hatch (var 1, initialize, the
    # Spiny's body) -> 5 Change -> at its end, nothing behind -> 8 walk
    wo = world(n, 1, var=0)
    wo.m.ground, wo.m.vx, wo.m.target_x = False, 2.0, -300.0
    wo.m.w32(OBJ + W.V(1), 200)
    wo.m.w32(OBJ + W.V(2), 150)
    c1 = enter_calls(wo, 1)
    wo.run(3)
    spins = [c for e in wo.log for c in e[4] if c[0] == 'node_rot']
    wo.m.ground = True
    wo.run(2)
    s1 = wo.states()
    wo.m.vy, wo.m.vx = -1.0, 2.0
    wo.run(3)
    s2 = wo.states()
    wo.m.vy, wo.m.vx = 0.0, 0.2
    wo.run(2)
    var = wo.m.r32(OBJ + 0xC)
    w08 = round(wo.m.rf(EN + 8), 3)
    hatch_atk = [c[2] for e in wo.log for c in e[4] if c[0] == 'atk_create']
    wo.m.motion_end = True
    wo.run(8)
    check(('motion', OBJ, 4, 0.0, 1.0, 1, 0.0) in c1 and len(spins) == 3 and spins[0][1] == 2 and
          spins[2][2] != spins[0][2] and s1 == [1, 2] and s2 == [1, 2] and var == 1 and w08 == 0.3 and
          hatch_atk == [D['tg_body']] and wo.states() == [1, 2, 5, 8],
          'togezo egg: 1 Paipo (node 2 spun every frame: %s) -> on the ground => 2 bounce; landing fast (|v| 2) keeps '
          'bouncing; slow (0.2 < 0.5) -> the hatch (variation 1, initialize: W+8 %.2f, the Spiny\'s spikes) -> 5 '
          'Change -> 8 walk %s' % ([x[2] for x in spins], w08, wo.states()))
    # walk: 200 frames -> 10 the leave (Fall at rate 0, kinetic 15, the leave effect) -> removed after 120
    wo = world(n, 8, var=1)
    wo.m.w32(OBJ + W.V(1), 200)
    wo.m.w32(OBJ + W.V(2), 150)
    wo.run(202)
    lv = [c for e in wo.log for c in e[5] if c[0] in ('kinetic', 'follow', 'motion')]
    wo.run(125)
    check(wo.states() == [8, 10, 13] and ('kinetic', T.EKIN, 15) in lv and ('follow', 0x8000005, 0) in lv,
          'togezo walk: 200 walk frames -> 10 leave (init_common_leave(P6): kinetic 15, effect 0x8000005 on node 0) -> '
          '120 frames -> 13 %s' % wo.states())
    # the search: every 20 frames while the 150-frame search timer runs, a target behind -> 9 (turn) -> => 8
    wo = world(n, 8, var=1)
    wo.m.w32(OBJ + W.V(1), 200)
    wo.m.w32(OBJ + W.V(2), 150)
    wo.m.found, wo.m.target_x = 0, 100.0
    wo.run(25)
    srch = [e[0] for e in wo.log for c in e[4] if c[0] == 'search']
    wo.m.motion_end = True
    wo.run(8)
    wo2 = world(n, 8, var=1)
    wo2.m.w32(OBJ + W.V(1), 200)
    wo2.m.w32(OBJ + W.V(2), 3)
    wo2.m.found, wo2.m.target_x = 0, 100.0
    wo2.run(30)
    check(srch and srch[0] < 20 and wo.states()[:3] == [8, 9, 8] and not any(c[0] == 'search' for e in wo2.log for c in e[4]),
          'togezo walk: search_target(0) every 20 frames of the search timer (first on frame %s), a target behind'
          ' ' % srch[:1] + ' -> 9 Turn -> reverse_lr => 8; '
          'none once the 150-frame search timer has run out %s' % wo.states())
    wo = world(n, 8, var=1)
    wo.m.w32(OBJ + W.V(1), 200)
    wo.m.walls = {2}
    wo.run(2)
    wo2 = world(n, 8, var=1)
    wo2.m.w32(OBJ + W.V(1), 200)
    wo2.m.ground = False
    wo2.run(2)
    check(wo.states() == [8, 9] and wo2.states() == [8, 6], 'togezo walk: a wall -> 9, off the ground -> 6')
    # slot 69: var 1 => 11 (Damage, hit_return_frame frames, flag 0x80), returns 1; in the leave the leave ends
    m = M(img)
    m.walker(cfg[n], state=10, kind=0x4E, var=1)
    m.w32(OBJ + W.V(6), 50)
    m.w32(OBJ + W.V(5), 0x7777)
    m.call(fn['tg_69'], {3: OBJ})
    r3 = m.uc.reg_read(T.R[3])
    got = [c[:3] for c in m.calls if c[0] in ('remove_effect', 'set_correct', 'chgi')]
    check(r3 == 1 and got == [('remove_effect', OBJ, 0x7777), ('set_correct', T.GROUND, 5), ('chgi', OBJ, 11)],
          'togezo slot 69: the running leave ends (its effect removed, set_correct(5)), => 11 stun, returns 1 %s' % got)
    wo = world(n, 11, var=1)
    c = enter_calls(wo, 11)
    stun = wo.m.r32(OBJ + W.V(0))
    flag = wo.m.r32(T.FLAGS) & 0x80
    wo.run(stun + 1)
    check(('motion', OBJ, 1, 0.0, 1.0, 1, 0.0) in c and stun == 45 and flag and wo.states() == [11, 8] and
          not wo.m.r32(T.FLAGS) & 0x80,
          'togezo 11 stun: Damage loop, hit_return_frame() (30 x 1.5 = %d) frames with flag 0x80, then on the ground '
          '-> 8 %s' % (stun, wo.states()))
    m = M(img)
    m.walker(cfg[n], state=1, kind=0x4E, var=0)
    m.call(fn['tg_69'], {3: OBJ})
    check([c[2] for c in m.calls if c[0] == 'chgi'] == [3], 'togezo slot 69 on the egg => 3 (egg stun)')
    # deaths: var 0 -> 4 (bullet, no motion change), var 1 -> 12 (Damage at rate 0, bullet)
    m = M(img)
    m.walker(cfg[n], state=1, kind=0x4E, var=0)
    m.call(vslot(n, 67), {3: OBJ})
    r0 = m.uc.reg_read(T.R[3])
    m.walker(cfg[n], state=1, kind=0x4E, var=1)
    m.call(vslot(n, 67), {3: OBJ})
    r1 = m.uc.reg_read(T.R[3])
    wo = world(n, 4, var=0)
    c = enter_calls(wo, 4)
    check((r0, r1) == (4, 12) and [x[0] for x in c] == ['bullet'],
          'togezo death: var 0 -> 4 (bullet, the Paipo pose kept), var 1 -> 12 %s' % c)
    # never stomped
    _m, got = stomp(n, 8, [(5.0, 0x1D), (-1.0, 0x1D)], 4.0)
    check(not any(got[1]), 'togezo: a fighter falling onto it is not a stomp (TREAD 0) %s' % got)


def paratroopa(img, fn, D, cfg, byname, world, enter_calls, stomp, vslot):
    """Paratroopa / Koopa (patapata 0x03): winged (variations 0 / 1) and walking (2 / 3)"""
    n = 'patapata'
    call = lambda f, var, state=0, **kw: (lambda m: (m.walker(cfg[n], state=state, kind=3, var=var),  # noqa: E731
                                                   m.call(f, {3: OBJ}), m)[2])(M(img))
    rets = {var: [call(vslot(n, k), var).uc.reg_read(T.R[3]) for k in (64, 65, 66, 67)] for var in (0, 1, 2, 3)}
    ok = (vslot(n, 20) == fn['pt_tread'] and img.u32(cfg[n] + W.CF['F69']) == fn['pt_69'] and
          img.u32(cfg[n] + W.CF['TREAD']) == 19 and round(W.struct.unpack('>f', W.struct.pack(
              '>I', img.u32(cfg[n] + W.CF['BOUNCE'])))[0], 3) == 1.0 and
          rets == {0: [2, 1, 1, 8], 1: [2, 1, 1, 8], 2: [12, 10, 10, 20], 3: [12, 10, 10, 20]})
    check(ok, 'patapata: slot 20 its tread handler, 69 the wing loss, slots 64-67 by variation %s, the bounce 1.0 '
          '(the user\'s, as the Green Shell; the 3DS W+0x44 is 0.7)' % rets)
    got = {}
    for var in (0, 2):
        m = call(fn['pt_start'], var)
        got[var] = ([c[0] for c in m.calls if c[0] in ('aer_ctor', 'rhombus')], [c[2] for c in m.calls if c[0] == 'chgi'],
                    m.r32(OBJ + W.V(4)), round(m.rf(EN + 0x44), 3))
    check(got == {0: (['aer_ctor', 'rhombus'], [1], 1, 0.7), 2: (['aer_ctor', 'rhombus'], [10], 1, 0.7)},
          'patapata start: the aerial module, set_rhombus, W+0x44 = f8; winged => 1, walking => 10 %s' % got)
    # winged: 1 -> on the ground => 2 hop (W+0x08 0.6, +0x0C 2.5, kinetic 5) -> airborne, falling, landed -> 2 again;
    # a fighter found by the search (group 0: every 10 frames) -> 5 bite wind-up (uniform (0, -0.5), Bite at 1.5)
    # -> 15 frames -> 6 bite (P2 entry 0) -> the motion's end -> 1 with the 30-frame cool-down
    wo = world(n, 1, var=0)
    wo.m.ground = True
    wo.run(2)
    hop = (round(wo.m.rf(EN + 8), 3), round(wo.m.rf(EN + 0xC), 3))
    wo.m.vy, wo.m.ground = 1.0, False
    wo.run(3)
    wo.m.vy = -1.0
    wo.run(2)
    wo.m.ground = True
    wo.run(2)
    s1 = [e[1] for e in wo.log]
    wo.m.found, wo.m.target_x = 0, -50.0
    wo.m.w32(OBJ + W.V(0), 0)
    wo.m.w32(OBJ + W.V(1), 0)
    wo.m.vy, wo.m.ground = 1.0, False
    wo.run(3)
    am = [c for e in wo.log for c in e[5] if c[0] == 'amode']
    wo.m.found = -1
    wo.run(16)
    s2 = wo.states()
    atk = [c[2] for e in wo.log for c in e[4] + e[5] if c[0] == 'atk_create']
    wo.m.motion_end = True
    wo.oneshot = True
    wo.mframes = 9
    wo.run(2)
    cool = wo.m.r32(OBJ + W.V(1))
    rehop = sum(1 for e in wo.log if e[5] and e[1] == 2 and any(c[0] == 'kinetic' and c[2] == 5 for c in e[5]))
    check(hop == (0.6, 2.5) and rehop >= 2 and am == [('amode', 5, 0.0, -0.5)] and 6 in s2 and
          wo.states() == [1, 2, 5, 6, 1] and cool == 30,
          'patapata winged: 1 => 2 hops (W+8 / +0xC %s), lands -> 2 again; found -> 5 bite wind-up (the aerial '
          'module uniform at (0, -0.5): set_mode_normal without acceleration) -> 15 frames -> 6 bite -> its end -> 1 '
          'with the 30-frame cool-down %s %s' % (hop, wo.states(), (am, cool, rehop)))
    # the stomp on a winged one: => 9 (the wing loss: var 2, effect 0x7030000, NokonokoMode) -> 10; bounce 1.0
    m, got = stomp(n, 2, [(5.0, 0x1D), (-1.0, 0x1D)], sum(W.tread_box(byname[n])[1:]), init=False)
    sf = [c for c in got[1] if c[0] in ('chgi', 'set_float')]
    wo = world(n, 9, var=0)
    c = [x for x in wo.m.calls if x[0] in ('effect', 'motion', 'kinetic', 'clear_speed')]
    var = wo.m.r32(OBJ + 0xC)
    wo.m.motion_end, wo.oneshot, wo.mframes = True, True, 9
    wo.run(2)
    check(sf[0][2] == 9 and sf[1] == ('set_float', T.HEAP + 0x34600, W.F_TREAD_MUL, 1.0) and var == 2 and
          [x[2] for x in c if x[0] == 'effect'] == [0x7030000] and ('motion', OBJ, 17, 0.0, 1.0, 0, 0.0) in c
          and wo.states() == [9, 10],
          'patapata stomped winged => 9: variation 0 -> 2, effect 0x7030000 at the posture, NokonokoMode, -> 10 '
          '(falls, walks on as a Koopa); the fighter\'s multiplier 1.0 %s' % ((sf, var, c, wo.states()),))
    # slot 69 (a hit that does not kill): winged -> walking, returns 0; walking: nothing
    m = call(fn['pt_69'], 1, state=2)
    m2 = call(fn['pt_69'], 3, state=12)
    check(m.r32(OBJ + 0xC) == 3 and m.uc.reg_read(T.R[3]) == 0 and m2.r32(OBJ + 0xC) == 3 and
          not [x for x in m2.calls if x[0] == 'effect'],
          'patapata slot 69: a non-lethal hit takes the wings (var 1 -> 3, returns 0: the damage reaction runs and '
          'comes back to the walking states)')
    # walking: the search (group var + 1) found -> 14 -> 15 the leap (set_kinetic_shoot) -> 16 (P2 entry 1) ->
    # landed -> 17 / 18 -> 12
    wo = world(n, 12, var=2)
    wo.m.found, wo.m.target_x = 0, -40.0
    wo.run(2)
    wo.m.found = -1
    wo.m.motion_end, wo.oneshot, wo.mframes = True, True, 9
    wo.run(2)
    leap = tuple(round(wo.m.rf(EN + o), 3) for o in (0x20, 0x24, 0x28, 0x2C, 0x1C))
    wo.m.motion_end = False
    wo.m.ground = False
    wo.run(3)
    wo.m.ground = True
    wo.run(30)
    wo.m.motion_end, wo.oneshot, wo.mframes = True, True, 9
    wo.run(3)
    atk = [c[2] for e in wo.log for c in e[4] + e[5] if c[0] == 'atk_create']
    check(wo.states()[:4] == [12, 14, 15, 16] and wo.states()[-2:] == [18, 12] and leap == (3.0, 1.0, -1.0, 10.0, 0.075),
          'patapata walking: found -> 14 JumpHold -> 15 the leap (W+0x20..+0x2C %s, +0x1C 0.075) -> 16 (P2 entry 1: 2 %%)'
          ' -> landed -> 17 slide / 18 LandingJumpAttack -> 12 %s' % (leap, wo.states()))
    # stomped as a Koopa => 19 the shell: hit and tread off, damage 0, defeated; at the motion's end on the ground
    # create_item_and_throw(0x94, var 2 -> 1, position + (0, 3 - speed y, 0), the speed, 0, true, -1, -1) -> 23; step
    # 2i: the Wii U's Green Shell (0x46, variation 0) stands in for 0x94, and the model is hidden once it is thrown
    m, got = stomp(n, 12, [(5.0, 0x1D), (-1.0, 0x1D)], sum(W.tread_box(byname[n])[1:]), init=False, var=2)
    wo = world(n, 19, var=2, setup=lambda m: m.w32(OBJ + W.V(4), 1))     # the dead item due (start)
    c = [x[0] for x in wo.m.calls if x[0] in ('disable_hit', 'disable_tread', 'set_damage', 'motion')]
    wo.m.vy = -0.5
    wo.m.motion_end, wo.oneshot, wo.mframes = True, True, 9
    wo.run(2)
    thr = [x for e in wo.log for x in e[4] if x[0] == 'throw']
    vis = [x for e in wo.log for x in e[4] if x[0] == 'visible']
    check([x[2] for x in got[1] if x[0] == 'chgi'] == [19] and c == ['motion', 'disable_hit', 'disable_tread',
                                                                       'set_damage'] and
          wo.m.r32(OBJ + W.DEFEATED) == 1 and len(thr) == 1 and thr[0][:3] == ('throw', 0x46, 0) and
          thr[0][3][1:] == (3.5, 0.0) and thr[0][4:] == ((0.0, -0.5), 0.0, 1, -1, -1) and wo.states() == [19, 23] and
          vis == [('visible', 0)],
          'patapata stomped as a Koopa => 19 shell: disable_hit / disable_tread / set_current_damage(0), defeated; '
          'at its end the shell item thrown from 3 above (step 2i: the Green Shell 0x46, variation 0, for the 3DS\'s '
          '0x94), the model hidden (set_visibility(0), 0x73BC8), -> 23 %s' % ((thr, c, got[1], wo.states(), vis),))
    deaths = {var: call(vslot(n, 67), var).uc.reg_read(T.R[3]) for var in (0, 3)}
    wo = world(n, 20, var=3)
    c = [x for x in wo.enter(20) if x[0] in ('kinetic', 'motion')]
    # step 2q: ShellMode once (the 3DS's change_motion_state(0x12, 0, 10, false, 0), 0x73F80-0x73F98), not looped
    check(deaths == {0: 8, 3: 20} and ('kinetic', T.EKIN, 16) in c and ('motion', OBJ, 18, 0.0, 10.0, 0, 0.0) in c,
          'patapata death: winged -> 8 (BulletMode, bullet), walking -> 20 the spinning shell (kinetic 16, ShellMode '
          'once at 10, P2 entry 2: 17 %%) %s' % c)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    byname = {w['name']: w for w in W.WALKERS}
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    want = {}
    for a in (A.h,):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'region H (0x%08X-0x%08X): the code to 0x%08X is in the executable %s'
          % (W.CAVE_H, W.LIMIT_H, A.h.pc, bad[:4]))

    def rows(name):
        r = {}
        for sid, s in byname[name]['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        return r

    def world(name, state, lr=-1.0, var=0, setup=None):
        w = byname[name]
        m = M(img)
        m.walker(cfg[name], state=state, lr=lr, kind=w['kind'], var=var)
        m.target, m.target_x = 0, 300.0
        m.call(fn['w_init'], {3: OBJ})
        if setup:
            setup(m)
        return T.World(m, w, rows(name), state, cfg[name])

    def vslot(name, k):
        vt = img.u32(cfg[name] + W.CF['VT'])
        return img.u32(vt + 0xC + 8 * k)

    def enter_calls(wo, s):
        return [c for c in wo.enter(s) if c[0] in ('kinetic', 'attach', 'motion', 'quake', 'notify_death', 'bullet')]

    # ---------------------------------------------------------------- the stomp bounce
    def stomp(name, state, frames, box_top, x=0.0, status=0x1D, init=True, var=0):
        w = byname[name]
        m = M(img)
        m.walker(cfg[name], state=state, kind=w['kind'], x=x, var=var)
        m.wf(POSTURE + 0x14, 0.0)
        if init:
            m.call(fn['w_init'], {3: OBJ})
        m.fighter(y=box_top + 10.0, status=status)
        out = []
        for fy, st in frames:
            m.wf(FPOST + 0x14, box_top + fy)
            m.w32(FSTAT + W.STATUS_KIND, st)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            out.append([c for c in m.calls if c[0] in ('chgi', 'msc_status', 'set_float', 'set_int', 'set_damage')])
        return m, out

    def top(name):
        tb = W.tread_box(byname[name])         # step 2n: in the model's scale
        return tb[1] + tb[2]

    fall = [(5.0, 0x1D), (-1.0, 0x1D), (-1.0, 0xB3), (3.0, 0xB3), (6.0, 0xB), (8.0, 0xB)]
    m, got = stomp('kuribo', 3, fall, top('kuribo'))
    mul = m.rf(EN + 0x44)
    sets = [[c for c in g if c[0] in ('set_float', 'set_int')] for g in got]
    check(round(mul, 4) == 0.8 and sets[1] == [('set_float', FWM, W.F_TREAD_MUL, 0.8),
                                               ('set_int', FWM, 0, W.I_STEP_COUNT),
                                               ('set_int', FWM, W.BO_ID_INVALID, W.I_TREAD_TARGET)]
          and ('msc_status', FACC, (3, W.STEP_JUMP, 0)) in got[1] and sets[2] == [('set_float', FWM, W.F_TREAD_MUL, 0.8)]
          and sets[3] == [('set_float', FWM, W.F_TREAD_MUL, 0.8)] and sets[4] == [] and sets[5] == [],
          'bounce: a Goomba stomp writes the fighter\'s tread multiplier float 0x1000006 = its W+0x44 (%.2f, its 3DS '
          'initialize\'s P0 f13), step count int 0x10000006 = 0 and (step 2p) the tread target int 0x10000008 = '
          '0x50000000 with StatusModule(3, 0xB3); again on each update '
          'while the fighter is in 0xB3; not after it has left it (0xB jump) %s' % (mul, sets))
    m, got = stomp('kuribo', 3, [(5.0, 0x1D), (-1.0, 0x1D), (2.0, 0xB), (2.0, 0xB3)], top('kuribo'))
    sets = [[c for c in g if c[0] == 'set_float'] for g in got]
    check(sets[2] == [] and sets[3] == [('set_float', FWM, W.F_TREAD_MUL, 0.8)],
          'bounce: still pending while the fighter has not entered 0xB3 yet (status changes are requests: MSC '
          'StatusModule op 3 stores the kind, 3DS 0x687968) %s' % sets)
    m, got = stomp('tikibuzz', 3, [(5.0, 0x1D), (-1.0, 0x1D)], 11.72 + 1.5)
    tiki = [c for c in got[1] if c[0] == 'set_float']
    check(tiki == [('set_float', FWM, W.F_TREAD_MUL, 0.98)],
          'bounce: Tiki Buzz 0.98 (its initialize\'s W+0x44 = P0 f18) %s' % tiki)
    m, got = stomp('dekakuribo', 3, [(5.0, 0x1D), (-1.0, 0x1D)], top('dekakuribo'))
    dk = [c for c in got[1] if c[0] in ('set_float', 'chgi', 'set_damage')]
    check(dk == [('set_damage', OBJ, 25.0), ('chgi', OBJ, 10, dk[1][3], dk[1][4], dk[1][5]),
                 ('set_float', FWM, W.F_TREAD_MUL, 0.9)] and round(m.rf(EN), 3) == 15.0,
          'Big Goomba stomp (box top %.1f): add_damage(25) -> HP 40 -> 15 => 10 Stepped; bounce 0.9 (W+0x44 = P0 f14)'
          ' %s' % (top('dekakuribo'), dk))

    # the game's StepJump speed with the written multiplier (0x02E79938, natively; its paired-single saves nopped)
    def speed(mult, count=0):
        m = M(img)
        lo_, hi_ = W.STEP_JUMP_SPEED, W.STEP_JUMP_SPEED + 0x340
        for a in range(lo_, hi_, 4):
            if img.u32(a) >> 26 == 4:
                m.uc.mem_write(a, struct.pack('>I', 0x60000000))
        m.fighter()
        m.params = {0x300015F: 2.4, 0x3000160: 1.5, 0x300000D: 0.0, 0x300000E: 0.0, 0x300000F: 1.0, 0x20000B5: 0.8}
        m.work[(FWM, W.F_TREAD_MUL)] = mult
        m.work[(FWM, W.I_STEP_COUNT)] = count
        m.wf(HEAP + 0x3F000, 0.0)
        m.wf(HEAP + 0x3F004, 0.0)
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(W.STEP_JUMP_SPEED, T.DONE, {3: HEAP + 0x3E000, 4: HEAP + 0x3F000, 5: FACC})
        return round(m.rf(HEAP + 0x3F004), 4)
    got = {k: speed(v) for k, v in (('1.0', 1.0), ('Goomba 0.8', 0.8), ('Big Goomba 0.9', 0.9),
                                    ('Tiki Buzz 0.98', 0.98))}
    check(got == {'1.0': 2.4, 'Goomba 0.8': round(2.4 * 0.8, 4), 'Big Goomba 0.9': round(2.4 * 0.9, 4),
                  'Tiki Buzz 0.98': round(2.4 * 0.98, 4)} and speed(0.9, 2) == round(2.4 * 0.9 * 0.8, 4),
          'bounce: the game\'s StepJump speed 0x02E79938 gives y = step_jump_speed_y (2.4 here) x float 0x1000006: %s '
          '(x float 0x20000B5 ^ (count - 1) past one step: the zeroed count keeps it off)' % got)

    # ---------------------------------------------------------------- Big Goomba
    n = 'dekakuribo'
    w = byname[n]
    ok = (vslot(n, 45) == fn['o_nop'] and vslot(n, 20) == fn['dk_tread'] and vslot(n, 41) == fn['f_v41'] and
          img.u32(cfg[n] + W.CF['FSTART']) == fn['w_start'] and
          [img.u32(cfg[n] + W.CF[k]) for k in ('R64', 'R65', 'R66', 'R67', 'DEADMOT', 'TREAD')] == [3, 1, 1, 12, 18, 11])
    check(ok, 'dekakuribo: vtable slot 45 empty (0x869F4: no P2 contact), 20 its tread handler, 41 start; 64-67 '
          '3 / 1 / 1 / 12; death motion 18 (the Damage with its own 12 %% ACMD)')
    m = M(img)
    m.walker(cfg[n], state=0, kind=0x23)
    m.call(fn['w_init'], {3: OBJ})
    en = {o: round(m.rf(EN + o), 3) for o in (8, 0xC, 0x10, 0x14, 0x18, 0x24, 0x28, 0x2C, 0x40, 0x44)}
    check(en == {8: 2.0, 0xC: 1.0, 0x10: 0.0, 0x14: 0.01, 0x18: 10.0, 0x24: 3.0, 0x28: -0.5, 0x2C: 3.5, 0x40: 1.0,
                 0x44: 0.9}, 'dekakuribo initialize (0x8630C): W %s' % en)

    # walk: nothing found -> walks (WalkL at 0.3, kinetic 10); at frame 59 a fighter within 28 -> 4 (3 kinetic-5
    # repeats on the ground) -> 5 (AngryL) -> 200 frames -> 3
    wo = world(n, 3)
    c = enter_calls(wo, 3)
    wo.m.found, wo.m.target_x = -1, 20.0
    wo.run(30)
    s1 = wo.states()
    wo.m.found = 0
    wo.script[58] = lambda w2: setattr(w2.m, 'target_x', w2.m.rf(POSTURE + 0x10) + 20.0)
    wo.run(40)
    k5 = [c for e in wo.log for c in e[4] if c[0] == 'kinetic' and c[2] == 5]
    s2 = wo.states()
    wo.m.found = -1
    wo.run(210)
    check(c[:3] == [('kinetic', T.EKIN, 0xA), ('attach', T.GROUND, 1), ('motion', OBJ, 17, 0.0, 0.3, 1, 0.0)] and
          s1 == [3] and s2 == [3, 4, 5] and len(k5) == 2 and wo.states() == [3, 4, 5, 3],
          'dekakuribo 3 walk (WalkL at 0.3, kinetic 10); the search on frame 60: a fighter at 20 (<= 28) -> 4 '
          '(kinetic 5 again twice) -> 5 Angry -> after 200 frames -> 3: %s' % wo.states())
    # far: -> 6 (the hop back: W+0x20 -0.5, kinetic 5) -> landed, 30 frames -> 7 run -> 200 run frames -> 8 -> 3
    wo = world(n, 3)
    wo.m.found, wo.m.target_x = 0, 100.0
    wo.run(62)
    hop = round(wo.m.rf(EN + 0x20), 3)
    wo.m.found = -1
    wo.m.vy, wo.m.ground = 1.0, False
    wo.script[wo.i + 3] = lambda w2: (setattr(w2.m, 'vy', -1.0), setattr(w2.m, 'ground', True))
    wo.run(40)
    s3 = wo.states()
    wo.run(205)
    s4 = wo.states()
    wo.run(10)
    check(s3 == [3, 6, 7] and hop == -0.5 and s4[:4] == [3, 6, 7, 8] and wo.states() == [3, 6, 7, 8, 3],
          'dekakuribo: a fighter beyond 28 -> 6 run start (W+0x20 = -0.5: a hop back) -> landed and 30 frames -> 7 '
          'Run -> 200 run frames -> 8 brake -> 3: %s' % wo.states())
    wo = world(n, 6, setup=lambda m: setattr(m, 'cliff', True))
    check(round(wo.m.rf(EN + 0x20), 3) == 0.0, 'dekakuribo 6: a ledge behind (check_cliff with -lr) -> no hop back')
    # run: a target behind at the search -> 9 RunTurnL -> reverse_lr, => 7 (the run counter kept); a wall -> 9
    wo = world(n, 7)
    wo.m.found, wo.m.target_x = 0, 50.0                      # lr -1: x 50 is behind
    wo.run(10)
    rev = [c for e in wo.log for c in e[4] if c[0] == 'reverse_lr']
    run_frames = wo.m.r32(OBJ + W.V(1))
    check(wo.states() == [7, 9, 7] and len(rev) == 1 and 0 < run_frames < 10,
          'dekakuribo 7 run: a fighter behind -> 9 run turn -> reverse_lr => 7, the 200-frame count kept (%d) %s'
          % (run_frames, wo.states()))
    wo = world(n, 7)
    wo.m.walls = {2}
    wo.run(3)
    check(wo.states()[:2] == [7, 9], 'dekakuribo 7: a wall ahead -> 9 %s' % wo.states())
    # walk: a wall -> the turn flag: clear_speed_all until WalkL loops (30 / 0.3 = 100 frames), reverse_lr, => 3
    wo = world(n, 3)
    wo.m.walls = {2}
    wo.run(3)
    wo.m.walls = set()
    wo.run(110)
    clr = sum(1 for e in wo.log for c in e[4] if c[0] == 'clear_speed')
    rev = [e[0] for e in wo.log for c in e[4] if c[0] == 'reverse_lr']
    check(rev and 95 <= rev[0] <= 101 and clr >= 90,
          'dekakuribo 3: a wall sets the turn flag: clear_speed_all until WalkL loops, then reverse_lr => 3 (no turn '
          'motion): reversed on frame %s after %d clears' % (rev[:1], clr))
    # landing: quake 3, then walk
    wo = world(n, 1)
    c = enter_calls(wo, 2)
    wo.cur = 2
    wo.m.motion_end = True
    wo.oneshot, wo.mframes = True, 9
    wo.run(2)
    check(('quake', OBJ, 3) in c and wo.states() == [2, 3],
          'dekakuribo 2 landing: Landing, request_quake(3), at its end -> 3 %s' % wo.states())
    # the stomp's second time: 15 -> -10 -> HP 0, => 11 collapses (notify_on_death), its end -> 13 remove
    m = M(img)
    m.walker(cfg[n], state=10, kind=0x23)
    m.damage = 25.0
    m.wf(EN, 15.0)
    m.call(fn['dk_tread'], {3: OBJ})
    chg = [c for c in m.calls if c[0] in ('chgi', 'set_damage')]
    wo = world(n, 11)
    c = enter_calls(wo, 11)
    check(chg[0] == ('set_damage', OBJ, 50.0) and chg[1][2] == 11 and m.rf(EN) == 0.0 and
          ('notify_death', OBJ) in c and ('motion', OBJ, 2, 0.0, 1.0, 0, 0.0) in c,
          'dekakuribo second stomp: damage 50 -> HP 0 => 11 Collapses (notify_on_death) %s' % chg)
    wo = world(n, 10)
    wo.m.motion_end = True
    wo.oneshot, wo.mframes = True, 9
    wo.run(2)
    check(wo.states() == [10, 3], 'dekakuribo 10 Stepped: at its end -> 3 %s' % wo.states())
    # the stomp is skipped while collapsing (TREAD 11) and dying (12)
    _m, got = stomp(n, 11, [(5.0, 0x1D), (-1.0, 0x1D)], top(n))
    _m, got2 = stomp(n, 12, [(5.0, 0x1D), (-1.0, 0x1D)], top(n))
    check(not any(got[1]) and not any(got2[1]), 'dekakuribo: no stomp in 11 (collapsing) or 12 (dying)')
    # the ACMD hitboxes: the motions' scripts are reachable (the hashsets) and hold the readings' boxes
    hs = D['hs_' + n]
    angry = img.u32(hs + 4)
    run = img.u32(hs + 4 * (3 * 14 + 1))
    check(angry == 0xC0C12699 and run == 0x5076A4C0,
          'dekakuribo: AngryL / RunL play the scripts "angry" (0xC0C12699) / 0x5076A4C0 (the 3DS hashset table)')
    if root:
        import acmd
        p = os.path.join(root, 'animcmd', 'enemy', n, 'attack.bin')
        f = acmd.ACMDFile.load(p)
        boxes = {}
        for h in (angry, run, img.u32(hs + 4 * (3 * 17 + 1)), img.u32(hs + 4 * (3 * 18 + 1))):
            boxes[h] = [(c.params[0], c.params[2], c.params[3], c.params[4], c.params[5])
                        for c in f.scripts.get(h, []) if c.name == 'Special_Hitbox']
        boxes = {h: [tuple(v - (1 << 32) if isinstance(v, int) and v >= 1 << 31 else v for v in b) for b in bb]
                 for h, bb in boxes.items()}
        check(boxes[angry] == [(1, 6, 4.0, -30, 100), (2, 5, 4.0, -30, 100)] and
              boxes[run] == [(1, 4, 6.0, 30, 100)] and boxes[img.u32(hs + 4 * (3 * 18 + 1))] == [(0, 2, 12.0, 361, 100)]
              and boxes[img.u32(hs + 4 * (3 * 17 + 1))] == [(0, 4, 0.0, 0, 60)],
              'dekakuribo attack.bin (converted): AngryL ids 1 / 2 at nodes 6 / 5 (4 %%, -30), RunL node 4 (6 %%, 30), '
              'the death Damage node 2 (12 %%, 361), WalkL the 0 %% push box %s' % boxes)

    spiny(img, fn, D, cfg, byname, world, enter_calls, stomp, vslot)
    paratroopa(img, fn, D, cfg, byname, world, enter_calls, stomp, vslot)
    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
