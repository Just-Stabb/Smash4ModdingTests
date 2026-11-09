#!/usr/bin/env python3
"""Behaviour tests of step 2j (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2j") on a patched
executable, in unicorn with smashrun_walker_test.py's stubbed world (smashrun_step2h_test.py's machine plus the
ray checks, the motion frame, the trig functions):

  python3 tools/smashrun_step2j_test.py PATCHED.rpx

- Pooka (pooka 0x20, every value from its 3DS code, hand_read.json pooka port_step2j): the vtable and CFG; the walk's
  search -> 5 back-off (40 frames, the stick reversed) -> 6 lunge (P2 entry 0: 2 %, angle 20, bkb 50, size 5, node
  4) ending at the first hit (or a wall) with the 3DS bounce, -> 7 slide -> 3; the walk's ghost / drop check; the
  inflate by damage (slot 69 -> 10 at or below 85 % HP), the balloon frame following the HP lost, the deflate (HP back
  to 90 %); the pop at 0 HP (15 frames, 11: the burst P2 entry 1, effect 0x7200001 at node 3 x3, the model hidden,
  the dead item and quake 3 on its first frame, removed after the sound's 28 frames); the ghost (start inside a wall ->
  8: kinetic 26, set_correct(0), disable_hit, the goggles effect, the model hidden; flies 0.5 a frame toward the
  fighter; out of the walls: set_correct(5), enable_hit, the meshes back, the effect removed, -> 1);
- the audit fixes (smashrun_walker_cave.py "Step 2j" fixes).
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402

check = T.check
OBJ, ACC, POSTURE, EN, INPUT, HEAP, MOTION = T.OBJ, T.ACC, T.POSTURE, T.EN, T.INPUT, T.HEAP, T.MOTION
E0 = HEAP + 0x3C000                  # energy 0 (the aerial module's +4)
GCO = HEAP + 0x3C800                 # the GroundCollisionObject (GroundModule +0x18)
END = 120.0                          # Damageballoon's frames


class PM(H.M):
    """step2h's machine plus Pooka's calls: ray_check (self.rays(from, dir, bool) -> hit point or None), the
    motion frame (set_frame / end_frame), the trig functions, the hit / effect / dead item calls"""

    def __init__(self, img):
        H.M.__init__(self, img)
        self.rays = lambda f, d, b: None
        self.center = (0.0, 0.0)
        self.w32(T.GROUND + 0x18, GCO)
        self.wf(H.GLTAB + 0x120, 0.25)
        self.normal = (1.0, 0.0)

    def hook(self, u, addr, size, x):
        r = lambda n: u.reg_read(T.R[n])  # noqa: E731
        c = self.calls
        if addr == W.RAY_CHECK:
            f = (self.rf(r(4)), self.rf(r(4) + 4))
            d = (self.rf(r(5)), self.rf(r(5) + 4))
            hit = self.rays(f, d, r(7))
            c.append(('ray', tuple(round(v, 2) for v in f), tuple(round(v, 2) for v in d), r(7), hit))
            if hit:
                self.wf(r(6), hit[0])
                self.wf(r(6) + 4, hit[1])
            return self.ret(1 if hit else 0)
        if addr == W.CENTER_POS:
            self.wf(r(3), self.rf(POSTURE + 0x10) + self.center[0])
            self.wf(r(3) + 4, self.rf(POSTURE + 0x14) + self.center[1])
            self.wf(r(3) + 8, 0.0)
            return self.ret()
        if addr in (W.SQRTF, W.ACOSF, W.COSF, W.SINF):
            f = {W.SQRTF: math.sqrt, W.ACOSF: math.acos, W.COSF: math.cos, W.SINF: math.sin}[addr]
            self.wfr(1, f(self.fr(1)))
            return self.ret()
        if addr == W.SET_FRAME:
            c.append(('set_frame', round(self.fr(1), 3)))
            self.wf(MOTION + W.MOT_FRAME, self.fr(1))
            return self.ret()
        if addr == W.END_FRAME:
            return self.ret(int(END))
        if addr == W.GROUND_NORMAL:
            u.reg_write(T.R[4], struct.unpack('>I', struct.pack('>f', self.normal[1]))[0])
            return self.ret(struct.unpack('>I', struct.pack('>f', self.normal[0]))[0])
        if addr in (W.ENABLE_HIT, W.ZIMA_CAPTURE_MOTION, W.ATK_CLEAR):
            c.append(({W.ENABLE_HIT: 'enable_hit', W.ZIMA_CAPTURE_MOTION: 'capture_motion',
                       W.ATK_CLEAR: 'atk_clear'}[addr],))
            return self.ret()
        if addr == W.REQ_NODE:
            c.append(('effect_node', r(4), r(5), round(self.fr(1), 3)))
            return self.ret()
        if addr == W.CREATE_DEAD_ITEM:
            c.append(('dead_item', r(4), r(5), round(self.fr(1), 3), round(self.fr(2), 3)))
            return self.ret()
        if addr == W.SET_PASSABLE:
            c.append(('passable', r(4)))
            return self.ret()
        if addr == W.AER_UPDATE_XY:
            c.append(('aer_upd', round(self.fr(1), 3), round(self.fr(2), 3), r(4)))
            return self.ret()
        if addr == W.IN_VIEW:
            c.append(('in_view',))
            return self.ret(getattr(self, 'in_view', 1))
        if addr == W.CHECK_CLIFF_DIST:
            c.append(('cliff_dist', round(self.fr(1), 3), round(self.fr(2), 3)))
            return self.ret(int(self.cliff))
        return H.M.hook(self, u, addr, size, x)

    def pooka(self, cfg, state=0, lr=-1.0, x=0.0, hp=10.0):
        self.walker(cfg, state=state, lr=lr, kind=0x20, x=x)
        self.uc.mem_write(OBJ + W.FL_SIZE, bytes(W.PK_SIZE - W.FL_SIZE))
        self.uc.mem_write(E0, bytes(0x40))
        self.w32(OBJ + W.AER + 4, E0)
        self.wf(EN, hp)
        self.wf(EN + 4, 10.0)
        self.maxhp, self.damage = 10.0, 10.0 - hp
        self.wf(OBJ + W.V(6), 8.5)
        self.w32(OBJ + W.V(5), 0xFFFFFFFF)
        self.w32(OBJ + W.PK + 4, 1)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    H.M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    want = {A.h.base + 4 * i: x for i, x in enumerate(A.h.words())}
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'region H: the step 2j code to 0x%08X is in the executable %s' % (A.h.pc, bad[:4]))
    byname = {w['name']: w for w in W.WALKERS}
    n = 'pooka'
    w = byname[n]
    cfg = D['cfg_pooka']
    vslot = lambda k: img.u32(img.u32(cfg + W.CF['VT']) + 0xC + 8 * k)  # noqa: E731
    cf = lambda k: img.u32(cfg + W.CF[k])  # noqa: E731
    rows = {sid: ((W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE) if s == 'remove' else tuple(fn[x] for x in s))
            for sid, s in w['states'].items()}

    def world(state, lr=-1.0, hp=10.0, setup=None):
        m = PM(img)
        m.pooka(cfg, state=state, lr=lr, hp=hp)
        m.target, m.target_x = 0, 300.0
        m.call(fn['w_init'], {3: OBJ})
        if setup:
            setup(m)
        return T.World(m, w, rows, state, cfg)

    # ---- the vtable and the CFG
    atk = [img.u32(D['atk_pooka'] + 4 * i) for i in range(5)]
    lunge = [img.u32(D['pk_lunge'] + 4 * i) for i in range(10)]
    pop = [img.u32(D['pk_pop'] + 4 * i) for i in range(10)]
    check(all(vslot(k) == fn[f] for k, f in w['vtover'].items()) and cf('F69') == fn['pk_69'] and
          cf('FSTART') == fn['pk_start'] and cf('TREAD') == 0 and cf('SIZE') == W.PK_SIZE and
          [cf(k) for k in ('R64', 'R65', 'R66', 'R67')] == [3, 1, 1, 10] and
          atk == [6, D['pk_lunge'], 11, D['pk_pop'], 0xFFFFFFFF] and
          lunge[:10] == [6, 0, 0, 4, 2, 20, 100, 0, 50, 5] and pop[:10] == [11, 0, 0, 4, 6, 70, 100, 60, 0, 30],
          'pooka: vtable 6 (hit) / 12 / 16 / 51 / 56 / 60 / 70 its own, slot 69 / start its own, never stomped (TREAD '
          '0), slots 64-67 3 / 1 / 1 / 10, size 0x%X; set_attack_data: 6 the lunge (2 %%, angle 20, kbg 100, bkb 50, '
          'size 5, node 4), 11 the pop (6 %%, angle 70, kbg 100, fixed 60, size 30, node 4)' % W.PK_SIZE)
    m = PM(img)
    m.pooka(cfg, state=0)
    m.call(fn['w_init'], {3: OBJ})
    ini = tuple(round(m.rf(EN + o), 3) for o in (0x10, 8, 0x14))
    check(ini == (0.04, 0.15, 0.01), 'pooka initialize (0x222BC): W+0x10 / +0x08 / +0x14 = %s' % (ini,))

    # ---- the walk: search found -> 5 back-off (Attackhold 1.5, stick reversed, 40 frames) -> 6 lunge
    wo = world(3)
    wo.m.found = 0
    wo.run(16)
    wo.m.ground = False
    s5 = wo.states()
    en5 = [c for e in wo.log for c in e[5] if c[0] in ('motion', 'kinetic')]
    sticks = [e[3][0] for e in wo.log if e[1] == 5]
    wo.m.found = -1
    wo.run(40)
    en6 = [c for e in wo.log for c in e[5] if c[0] in ('motion', 'kinetic')]
    w6 = tuple(round(wo.m.rf(EN + o), 3) for o in (0x20, 0x24, 0x28, 0x2C, 0x1C, 0x3C))
    back = sum(1 for e in wo.log if e[1] == 5)
    check(s5 == [3, 5] and ('motion', OBJ, 1, 0.0, 1.5, 0, 0.0) in en5 and sticks and sticks[0] == 1.0 and
          wo.states() == [3, 5, 6] and back == 40 and ('kinetic', T.EKIN, 5) in en6 and
          ('motion', OBJ, 0, 0.0, 0.1, 1, 0.0) in en6 and w6 == (2.0, 1.0, 10.0, 10.0, 0.0, 0.25),
          'pooka walk: search_target(0) found -> 5 back-off (Attackhold at 1.5, the stick reversed: %s) for 40 frames '
          '(%d) -> 6 lunge: W+0x20 / +0x24 / +0x28 / +0x2C / +0x1C / +0x3C %s (the gl gravity 0.25), kinetic 5, Attack '
          'at 0.1 (loop) %s' % (sticks[:1], back, w6, wo.states()))
    # the lunge's bounce: a hit (slot 6) while moving (1, -0.5) with the fighter ahead: reflected (-1, -0.5), angle
    # -153.4 -> clamp(-73.4, 50, 90) = 50; speed 0.5 x |v| = 0.559: W+0x20 = lr x cos 50 x 0.559, +0x24 = sin 50 x 0.559,
    # the hitbox cleared; a wall: the ground normal
    res = {}
    for case in ('hit', 'wall', 'none'):
        wo = world(6, lr=1.0)
        m = wo.m
        m.vx, m.vy, m.target_x = 1.0, -0.5, 20.0
        m.ground = False
        if case == 'hit':
            m.call(vslot(6), {3: OBJ, 4: 0x1234})
        if case == 'wall':
            m.walls, m.normal = {4, 2}, (-1.0, 0.0)
        wo.run(1)
        cl = wo.log[0][4]
        if os.environ.get('PKDBG') and case == 'wall':
            print('wall', [c for c in cl if c[0] in ('touch', 'ray')])
        res[case] = (round(m.rf(EN + 0x20), 3), round(m.rf(EN + 0x24), 3), ('atk_clear',) in cl,
                     m.r32(OBJ + W.V(5)), m.r32(OBJ + W.PK + 8))
    sp = 0.5 * math.hypot(1.0, 0.5)
    exp = (round(math.cos(math.radians(50)) * sp, 3), round(math.sin(math.radians(50)) * sp, 3), True, 0xFFFFFFFF, 0)
    check(res['hit'] == exp and res['wall'] == exp and res['none'][2] is False,
          'pooka lunge: the first hit (slot 6 stores the object, 0x23670) or a wall bounces it (reflect, the angle '
          'clamped 50-90, speed x 0.5) and clears the hitbox (AttackModule clear_all): %s, expected %s; no hit no '
          'clear' % (res, exp))
    wo = world(6, lr=1.0)
    wo.m.vy, wo.m.ground = 0.0, True
    wo.run(1)
    st7 = wo.cur
    e0 = (round(wo.m.rf(E0), 3), round(wo.m.rf(E0 + 4), 3))
    wo.m.wf(E0, 0.25)
    wo.run(1)
    v1 = round(wo.m.rf(E0), 3)
    wo.run(3)
    check(st7 == 7 and v1 == 0.15 and wo.states() == [6, 7, 3],
          'pooka: the lunge landing (speed y <= 0 on the ground) => 7 slide (kinetic 26, energy 0 kept %s): x eased by '
          '0.1 a frame (0.25 -> %s), |x| < 0.1 on the ground -> 3 %s' % (e0, v1, wo.states()))

    # ---- the walk's ghost / drop check (every 10 frames or at a wall): the fighter within 200, the ray (every
    # collision) blocked within 15 and short of it; the ray without the passable floors blocked as near -> 8, not
    # blocked and the fighter below -> 9
    def gchk(rays, tx, ty):
        m = PM(img)
        m.pooka(cfg, state=3)
        m.target_x, m.target_y = tx, ty
        m.rays = rays
        m.call(fn['pk_gchk'], {3: OBJ, 31: OBJ, 30: cfg})
        return m.uc.reg_read(T.R[3])
    wall = lambda f, d, b: (f[0] + 10.0, f[1])  # noqa: E731
    floor = lambda f, d, b: (f[0], f[1] - 5.0) if b else None  # noqa: E731
    got = (gchk(wall, 100.0, 0.0), gchk(floor, 3.0, -60.0), gchk(floor, 60.0, -60.0), gchk(wall, 250.0, 0.0),
           gchk(lambda f, d, b: (f[0] + 20.0, f[1]), 100.0, 0.0))
    check(got == (8, 9, 0, 0, 0),
          'pooka ghost check (0x22528): a wall 10 ahead -> 8 ghost; a passable floor and the fighter 60 below -> 9 drop; '
          'the fighter 45 degrees away -> none; out of range (250) -> none; the wall 20 away (> 15) -> none %s' % (got,))
    wo = world(9)
    wo.run(11)
    check(wo.states() == [9, 1], 'pooka 9 drop: 10 frames -> 1 %s' % wo.states())

    # ---- inflate by damage: slot 69 at or below 85 % -> 10 and 1 (no reaction); above -> 0
    out = {}
    for hp in (8.0, 9.0):
        m = PM(img)
        m.pooka(cfg, state=3, hp=hp)
        m.call(fn['pk_69'], {3: OBJ})
        out[hp] = (m.uc.reg_read(T.R[3]), [c[2] for c in m.calls if c[0] == 'chgi'])
    check(out == {8.0: (1, [10]), 9.0: (0, [])},
          'pooka slot 69 (0x23A48): HP 8 (<= 85 %% of 10) => 10, returns 1; HP 9 returns 0 %s' % out)
    # the balloon: HP 5 -> pct 41.2 % of 120 frames; the frame moves 1/15 of the way a frame for 15 frames; held 100;
    # deflating 0.3 a frame with the HP; at frame 0 HP 9 (90 %) -> 1
    wo = world(3, hp=5.0)
    m = wo.m
    m.wf(DMGX := H.DMG + 0x78, 3.0)
    en10 = wo.enter(10)
    w10 = tuple(round(m.rf(EN + o), 4) for o in (0x20, 0x24, 0x1C, 0x3C))
    m.ground, m.vy = False, 1.0
    wo.run(15)
    f15 = round(m.rf(MOTION + W.MOT_FRAME), 2)
    wo.run(101)
    defl = m.r32(OBJ + W.PK)
    wo.run(5)
    hp5 = round(m.rf(EN), 3)
    fr5 = round(m.rf(MOTION + W.MOT_FRAME), 2)
    wo.run(200)
    check(('motion', OBJ, 2, 0.0, 0.0, 0, 0.0) in en10 and w10 == (-1.5, 0.3029, 0.025, 0.015) and
          10 < f15 <= 0.42 * END and defl == 1 and fr5 < f15 and abs(hp5 - (8.5 - fr5 / END * 8.5)) < 0.01 and
          wo.states() == [10, 1] and round(m.rf(EN), 3) == 9.0,
          'pooka balloon (10): Damageballoon at rate 0, W+0x20 / +0x24 / +0x1C / +0x3C %s (x 3 halved, lr -1; y 0.45 x '
          '(1 - 5 / 8.5) + 0.2 x 5 / 8.5); the frame follows the HP lost (%.2f after 15 frames), held 100, then '
          'deflating (frame %.2f, HP %.3f climbing with it), frame 0: HP 90 %% -> 1 %s'
          % (w10, f15, fr5, hp5, wo.states()))
    # the pop: dead (W flags 2) -> 15 frames -> => 11: kinetic -1, every mesh off and hidden, effect 0x7200001 at
    # node 3 x3, the burst armed (P2 entry 1); its first frame the dead item and quake 3; removed after 28 frames
    wo = world(3, hp=0.0)
    m = wo.m
    m.w32(T.FLAGS, 2)
    wo.enter(10)
    wo.run(15)
    s11 = wo.cur
    dft = m.r32(OBJ + W.DEFEATED)
    pe = [c for e in wo.log for c in e[5]]
    wo.run(30)
    pu = [c for e in wo.log for c in e[4]]
    fr = [e[0] for e in wo.log if e[1] == 11]
    check(s11 == 11 and dft == 1 and ('kinetic', T.EKIN, 0xFFFFFFFF) in pe and ('effect_node', 0x7200001, 3, 3.0) in pe and
          ('visible', 0) in pe and not any(c[0] == 'mesh' and c[2] for c in pe) and
          ('dead_item', 0, 0, 1.0, 0.0) in pu and ('quake', OBJ, 3) in pu and wo.states() == [10, 11, 12] and
          len(fr) == 28,
          'pooka pop: dead -> 15 balloon frames => 11 (kinetic -1, the model hidden, effect 0x7200001 at node 3 x3), '
          'its first frame create_dead_item(1, 0) and request_quake(3), removed (12) after %d frames %s'
          % (len(fr), wo.states()))

    # ---- the ghost: start inside a wall (the ray to the fighter clear, the one back blocked) -> 8
    m = PM(img)
    m.pooka(cfg, state=0)
    m.target_x = 50.0
    m.rays = lambda f, d, b: (f[0] - 5.0, f[1]) if d[0] < 0 else None
    m.call(fn['pk_start'], {3: OBJ, 4: INPUT})
    st = [c[2] for c in m.calls if c[0] == 'chgi']
    m2 = PM(img)
    m2.pooka(cfg, state=0)
    m2.call(fn['pk_start'], {3: OBJ, 4: INPUT})
    check(st == [8] and [c[2] for c in m2.calls if c[0] == 'chgi'] == [1] and round(m.rf(OBJ + W.V(6)), 2) == 8.5,
          'pooka start (0x21064): inside a wall -> 8 ghost, else -> 1; the threshold 85 %% of the HP %s' % st)
    blocked = [True]
    wo = world(8, setup=lambda mm: setattr(mm, 'target_x', 100.0))
    m = wo.m
    m.rays = lambda f, d, b: (f[0] + 0.5 * d[0], f[1]) if blocked[0] else None
    en8 = wo.enter(8)
    wo.run(1)
    fly = (round(m.rf(E0), 3), round(m.rf(E0 + 4), 3), m.uc.mem_read(E0 + 0x18, 1)[0])
    wo.run(31)
    blocked[0] = False
    wo.run(30)
    out8 = [c for e in wo.log for c in e[4]]
    check(('kinetic', T.EKIN, 26) in en8 and ('set_correct', T.GROUND, 0) in en8 and ('disable_hit',) in en8 and
          any(c[0] == 'follow' and c[1] == 0x7200000 and c[2] == 1 for c in en8) and ('visible', 0) in en8 and
          fly == (0.5, 0.0, 1) and ('set_correct', T.GROUND, 5) in out8 and ('enable_hit',) in out8 and
          ('remove_effect', OBJ, 0x7777) in out8 and ('visible', 1) in out8 and wo.states() == [8, 1] and
          m.r32(OBJ + W.V(4)) == 1,
          'pooka ghost (8): kinetic 26, set_correct(0), disable_hit, the goggles effect 0x7200000 on node 1, the model '
          'hidden; flies toward the fighter at 0.5 (energy 0 %s), re-aimed every 30 frames; the rays clear: set_correct'
          '(5), enable_hit, the model shown, the effect removed -> 1 with a search at once %s' % (fly, wo.states()))
    fixes(img, fn, D, byname)
    if os.environ.get('PKDBG'):
        print('vt', [(k, hex(vslot(k)), hex(fn[f])) for k, f in w['vtover'].items()], hex(cf('F69')), hex(cf('FSTART')),
              cf('TREAD'), hex(cf('SIZE')), [cf(k) for k in ('R64', 'R65', 'R66', 'R67')], atk, lunge, pop)
        print('pop', s11, len(fr), m.r32(OBJ + W.DEFEATED), [c for c in pe if c[0] in ('kinetic', 'effect_node', 'visible', 'mesh')],
              [c for c in pu if c[0] in ('dead_item', 'quake')])
        print('back', s5, en5, sticks[:3], back, en6)
        print('en8', [c for c in en8 if c[0] in ('kinetic', 'set_correct', 'disable_hit', 'follow', 'visible')],
              [c for c in out8 if c[0] in ('set_correct', 'enable_hit', 'remove_effect', 'visible')])
    T.FAILS and sys.exit('%d FAILED' % len(T.FAILS))
    print('all checks passed')


def xorshift_seed(want_le):
    """an xorshift32 state whose next h_rand(1, 100) is <= 50 (want_le) or > 50"""
    for st in range(1, 1000):
        x = st
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        v = 1 + x % 100
        if (v <= 50) == want_le:
            return st
    raise AssertionError


def fixes(img, fn, D, byname):
    """step 2j: the audit's fixes (each from its 3DS address)"""
    cfgs = {n: D['cfg_' + n] for n in byname}
    vslot = lambda n, k: img.u32(img.u32(cfgs[n] + W.CF['VT']) + 0xC + 8 * k)  # noqa: E731

    def kworld(n, state, lr=-1.0, var=0):
        w = byname[n]
        m = PM(img)
        m.walker(cfgs[n], state=state, lr=lr, kind=w['kind'], var=var)
        m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x10))
        m.w32(OBJ + W.AER + 4, E0)
        m.target, m.target_x = 0, 300.0
        m.call(fn['w_init'], {3: OBJ})
        rows = {sid: ((W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE) if s_ == 'remove' else
                      tuple(x if isinstance(x, int) else fn[x] for x in s_)) for sid, s_ in w['states'].items()}
        return T.World(m, w, rows, state, cfgs[n])

    # Waddle Doo slot 69 (0x7E0E0): the old hit effect removed, effect 0x7190001 at center_pos x1 -> V8, the leave
    # timer back to 600 (0x7E12C), returns 0
    m = PM(img)
    m.walker(cfgs['waddledoo'], state=3, kind=0x19)
    m.w32(OBJ + W.V(8), 0x1111)
    m.w32(OBJ + W.V(7), 12)
    m.call(vslot('waddledoo', 69), {3: OBJ})
    got = ([c for c in m.calls if c[0] in ('remove_effect', 'effect0')], m.r32(OBJ + W.V(8)), m.r32(OBJ + W.V(7)),
           m.uc.reg_read(T.R[3]))
    check(got == ([('remove_effect', OBJ, 0x1111), ('effect0', OBJ, 0x7190001, (0.0, 0.0, 0.0), 1.0)], 0x5556, 600, 0),
          'waddledoo slot 69 (0x7E0E0): the old hit effect removed, effect 0x7190001 at center_pos x1, the leave timer '
          'back to 600 (0x7E12C), returns 0 %s' % (got,))
    # the random hop (0x7D568): every 61st walk frame a 50 %% chance -> 9 (the 3DS's 6)
    out = {}
    for le in (True, False):
        wo = kworld('waddledoo', 3)
        wo.m.w32(OBJ + W.V(7), 600)
        wo.m.w32(OBJ + W.V(4), 60)
        wo.m.w32(D['consts'] + 8, xorshift_seed(le))
        wo.run(1)
        out[le] = ([c[2] for c in wo.log[0][4] if c[0] == 'chg'], wo.m.r32(OBJ + W.V(4)))
    wo = kworld('waddledoo', 3)
    wo.m.w32(OBJ + W.V(7), 600)
    wo.run(3)
    cnt = wo.m.r32(OBJ + W.V(4))
    check(out == {True: ([9], 0), False: ([], 0)} and cnt == 3,
          'waddledoo walk: the hop counter (+0x170) counts the walk frames (%d); past PS8c f1 (60) it restarts and '
          'random_range(1, 100) <= 50 -> 9 (the 3DS state 6) %s' % (cnt, out))
    wo = kworld('waddledoo', 9)
    en9 = [c for c in wo.log[:0]] or wo.enter(9)
    wo.m.ground, wo.m.vy = False, -1.0
    wo.run(2)
    fall = [c for e in wo.log for c in e[4] if c[0] == 'motion']
    wo.m.ground = True
    wo.run(1)
    check(('motion', OBJ, 11, 0.0, 1.0, 0, 0.0) in en9 and ('kinetic', T.EKIN, 5) in en9 and
          fall[:1] == [('motion', OBJ, 10, 0.0, 1.0, 1, 0.0)] and len(fall) == 1 and wo.cur == 3,
          'waddledoo 9 (the 3DS 6, 0x7CE10 / 0x7D2CC): kinetic 5, Jump; falling: Fall (no restart); landed => 3 %s'
          % wo.states())
    wo = kworld('waddledoo', 5)
    wo.m.ground, wo.m.vy = False, -1.0
    wo.run(1)
    check(any(c[:3] == ('motion', OBJ, 10) for c in wo.log[0][4]) and
          struct.unpack('>f', struct.pack('>I', img.u32(cfgs['waddledoo'] + W.CF['HOPTHR'])))[0] == 0.5 and
          struct.unpack('>f', struct.pack('>I', img.u32(cfgs['heiho'] + W.CF['HOPTHR'])))[0] == 0.5,
          'waddledoo 5 wall hop: Fall when falling (0x7D6F0); the hop landing threshold 0.5 for Waddle Doo (0x7D77C) '
          'and Shy Guy (0x1B5B8)')
    # Shy Guy slot 69 (0x1BF70): the run timer (+0x174) = 0, returns 0
    m = PM(img)
    m.walker(cfgs['heiho'], state=9, kind=0x0B)
    m.w32(OBJ + W.V(2), 50)
    m.call(vslot('heiho', 69), {3: OBJ})
    check(m.r32(OBJ + W.V(2)) == 0 and m.uc.reg_read(T.R[3]) == 0,
          'heiho slot 69 (0x1BF70): the run timer reset, returns 0')
    # Waddle Dee 2 (0x7C6BC / 0x7C8E0): the aerial module at (x, -0.2), ParasolFall; update(stick x, -1, true)
    wo = kworld('waddledee', 4)
    wo.m.vx = 1.5
    e2 = wo.enter(2)
    wo.m.ground = False
    wo.run(1)
    u2 = [c for c in wo.log[0][4] if c[0] == 'aer_upd']
    wo.m.ground = True
    wo.run(1)
    check(img.u32(cfgs['waddledee'] + W.CF['SIZE']) == W.FL_SIZE and ('amode', 5, 1.5, -0.2) in e2 and
          ('motion', OBJ, 11, 0.0, 1.0, 1, 0.0) in e2 and not any(c[0] == 'kinetic' for c in e2) and
          u2 == [('aer_upd', -1.0, -1.0, 1)] and wo.cur == 3,
          'waddledee 2 parasol fall: a flier-sized object; the aerial module at (x, -P0 f5 0.2) (uniform: the Wii U '
          'module has no mode 0), ParasolFall; the aerial update(stick x, -1, true); landed => 3 %s %s' % (e2[:3], u2))
    # Goomba 4 notice (0x33314): check_cliff_distance_lr(-0.4 x (1.6 / g + 2) x -2, -lr): a ledge behind -> no hop back
    res = {}
    for cl in (False, True):
        m = PM(img)
        m.walker(cfgs['kuribo'], state=3, kind=0x01, lr=-1.0)
        m.call(fn['w_init'], {3: OBJ})
        m.cliff = cl
        m.call(fn['kc_ntc_en'], {3: OBJ})
        res[cl] = ([c for c in m.calls if c[0] == 'cliff_dist'], round(m.rf(EN + 0x20), 3))
    dist = round(-0.4 * (1.6 / 0.25 + 2.0) * -2.0, 3)
    check(res == {False: ([('cliff_dist', dist, 1.0)], -0.4), True: ([('cliff_dist', dist, 1.0)], 0.0)},
          'kuribo 4 notice: check_cliff_distance_lr(%.3f, -lr) (Wii U 0x026A6CF4): no ledge behind -> W+0x20 -0.4, a '
          'ledge -> 0 %s' % (dist, res))
    # Goomba 8 collapses (0x32A08): create_dead_item(1, 10, 0, 0) on its frame 1
    wo = kworld('kuribo', 3)
    wo.enter(8)
    wo.run(3)
    di = [(e[0], c) for e in wo.log for c in e[4] if c[0] == 'dead_item']
    check(di == [(1, ('dead_item', 0, 0, 1.0, 10.0))],
          'kuribo 8 collapses: create_dead_item(1, 10) on the state frame 1 (0x32A08), not at the removal %s' % di)
    # White Bear 6 end: is_in_view_area -> 7, else -> 3
    out = {}
    for v in (1, 0):
        wo = kworld('whitebear', 6)
        wo.m.in_view = v
        wo.m.motion_end = True
        wo.oneshot, wo.mframes = True, 9
        wo.run(1)
        out[v] = [c[2] for c in wo.log[0][4] if c[0] == 'chg']
    check(out == {1: [7], 0: [3]}, 'whitebear 6 quake hold end: in view (IN_VIEW 0x026A96BC = 3DS 0x9EA804) -> 7, '
          'else -> 3 %s' % out)


if __name__ == '__main__':
    main()
