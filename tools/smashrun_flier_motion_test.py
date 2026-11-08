#!/usr/bin/env python3
"""Behavioural unicorn test of the Smash Run fliers (Ghos, Tiki Buzz, Furiijio, Propeller Heiho) in a patched
cross_f.rpx: do they MOVE, not only call the right functions.

  python3 tools/smashrun_flier_motion_test.py PATCHED.rpx

tools/smashrun_flier_test.py stubs the aerial module, change_kinetic and the kinetic energies, so it checks call
sequences only; that is how step 2e's fliers, which stayed where they spawned in game, passed it. Here those run as
the game's own code (docs/smash-run-port.md "Step 2g v2"):
- the EnemyKineticModule is built by the game's own ctor 0x02DBD284 (energies at +0x18, energy 0 the enemy energy at
  +0x124, vtable 0x10122F24), at acc+0x30E8 and acc+0x34 (change_kinetic's helpers reach it through acc+0x34);
- the flier's start (vtable slot 41) and its states' enters / updates (the cave's code) with the game's
  EnemyAerialModuleImpl (ctor 0x02DB2C44, setters, update 0x02DB2524), change_kinetic 0x02DBE00C, the energies'
  init 0x02DC3674 / update 0x02DC0084 (KineticModule 0x02C50058), the speed sum 0x02DBE614 (vt+0xAC, mask 0xF) and
  set_rhombus 0x026A65BC (its two shape setters stubbed; the gl entries' shape types as in the Wii U's gl file);
- each frame: the state update, then the kinetic module's energy update, then posture += the summed speed, but only
  while the GroundModule's ground collision is on (+0xDE, set by set_rhombus; its ctor leaves it 0): the game's
  GroundModule update 0x02C35C9C returns at once while it is 0, so the enemy's GroundCollisionObject is never added
  to the collision manager (0x02D61264) and the enemy never moves (step 2e: set_rhombus got the aerial module);
- the aerial target: the fighter at (TX, TY) (EnemyAiModule get_target_pos 0x02DB9CA0 stubbed to it).
Asserts, per kind, that its start turns its ground collision on, that it gets clearly closer to where its behaviour
heads (the fighter for Ghos / Tiki Buzz / Furiijio; the fighter's height, then the patrol bob, for Propeller
Heiho), and that Ghos's speed carries on through its slip-homing re-picks (the 3DS's slip). Results: exe_v16 (step
2e, with the step-2e tools) fails 5 (no ground collision, no movement, the re-pick stop); exe_v19 fails 1 (the
re-pick stop); exe_v20 passes. Other framework calls stay stubbed as in smashrun_flier_test.py (its Machine).
Step 2g v3 (exe_v21): Ghos's re-pick takes the 3DS's sets the right way round (96 % the fast set: 76.2 -> 30.0 units in
240 frames, was 57.9); and the spawn facing, through the game's own initialize_after / set_lr / damage_turn /
reverse_lr: spawned on either side and turned twice by hits, the 3DS-flip kinds keep yaw -90, the others lr x 90.
"""
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_walker_test as T  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_flier_test as FT  # noqa: E402
from smashrun_walker_test import R, OBJ, ACC, POSTURE, check  # noqa: E402

HEAP = T.HEAP
EKM = HEAP + 0x38000            # the EnemyKineticModule (0x4F4 bytes, the game's ctor)
ZBLK = HEAP + 0x39000           # zeroed blocks: acc+0x3120's module, the param block's +0xC words
GMOD, GVT = HEAP + 0x3A000, HEAP + 0x3A100      # a generic module whose every vtable entry returns 0
STUB0 = 0x02000070              # that entry
AI_TPOS = 0x02DB9CA0            # EnemyAiModule::get_target_pos(this, id, &out) (the aerial module's target)
AI_INPUT = 0x02DB96FC           # EnemyAiModule's stick (the energy update reads it)
EKM_CTOR = 0x02DBD284
EN_UPDATE_ALL = 0x02C50058      # KineticModule: every enabled energy's update (r4 -1)
SUM3 = 0x02DBE614               # EnemyKineticModule vt+0xAC: (out, this, mask) the enabled energies' speed
# the game's code this test runs (its Espresso paired-single saves, primary opcode 4, are nopped in Unicorn's copy)
NATIVE = (0x02600000, 0x02E00000)
AER_UPDATE_XY = 0x02DB2524      # EnemyAerialModuleImpl::update(x, y, brake) (step 2g's W.AER_UPDATE_XY)
PASS = {W.AER_CTOR, W.AER_UPDATE, AER_UPDATE_XY, W.AER_SLIP_HOMING, W.AER_SLIP_HOMING_EXT, W.AER_SET_SPEED,
        W.CHANGE_KINETIC, W.SET_RHOMBUS}
# set_rhombus's two shape setters on the GroundCollisionObject (stubbed: the shape itself is not modelled)
SHAPE_RHOMBUS, SHAPE_CIRCLE = 0x02C39A78, 0x02C3CFA0
GROUND_ON = 0xDE                # GroundModule +0xDE: the ground collision is on (set_rhombus sets it; the ctor 0)
GCOLL = HEAP + 0x3C000          # the GroundModule's +0x18 GroundCollisionObject (zeros)
# the gl entries (param/enemy/gl/enemy_param.bin group 3, entry kind + 1, as the game reads them): +0x100 the
# collision shape type (0 rhombus, 1 circle; set_rhombus does nothing for other types), +0x104.. its sizes,
# +0x154 the hit stun frames; the test's gl index per kind
GL = {0x11: (2, 1, (0.0, 0.0, 0.0, 0.0, 8.0, 0.0, 8.0), 30), 0x0F: (3, 1, (0.0, 0.0, 0.0, 0.0, 5.0, 0.0, 5.0), 30),
      0x1A: (4, 0, (12.0, 18.0, 0.0, 9.0, 3.0, 0.0, 10.0), 30),
      0x47: (5, 1, (10.0, 16.0, 0.0, 8.0, 7.0, 0.0, 7.0), 10)}


class Motion(FT.Machine):
    def __init__(self, img):
        FT.Machine.__init__(self, img)
        u = self.uc
        lo, hi = NATIVE
        code = np.frombuffer(bytes(u.mem_read(lo, hi - lo)), dtype='>u4')
        for i in np.where((code >> 26) == 4)[0]:
            u.mem_write(lo + 4 * int(i), struct.pack('>I', 0x60000000))
        u.mem_write(EKM, bytes(0x500))
        u.mem_write(ZBLK, bytes(0x400))
        self.w32(GMOD, GVT)
        for o in range(0, 0x400, 4):
            self.w32(GVT + o, STUB0)
        self.w32(ACC + 0x3120, ZBLK)
        self.w32(ACC + 0x20, GMOD)
        self.w32(ACC + 0x2C, GMOD)
        self.w32(T.ARR + 0xC, ZBLK + 0x100)
        self.w32(ZBLK + 0x100, ZBLK + 0x200)
        self.tpos = (0.0, 0.0)
        self.ai_calls = 0
        # the game's ctor builds the module (energies and their vtables) in place
        self.call(EKM_CTOR, {3: EKM, 4: ACC})
        self.w32(ACC + 0x30E8, EKM)
        self.w32(ACC + 0x34, EKM)
        # the GroundModule: its collision object, ground collision off (as its ctor 0x02C3326C leaves it)
        u.mem_write(GCOLL, bytes(0x300))
        self.w32(T.GROUND + 0x18, GCOLL)
        u.mem_write(T.GROUND + GROUND_ON, b'\0')
        for k, (i, typ, dims, stun) in GL.items():
            self.w32(FT.PMGR + W.GL_INDEX + 4 * (8 * k), i)
            e = FT.GLTAB + i * 0x228
            self.w32(e + 0x100, typ)
            for j, v in enumerate(dims):
                self.wf(e + 0x104 + 4 * j, v)
            self.w32(e + 0x154, stun)

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        if addr in PASS:
            if addr == W.CHANGE_KINETIC:
                self.calls.append(('kinetic', r(3), r(4)))
            elif addr in (W.AER_UPDATE, AER_UPDATE_XY):
                self.calls.append(('aer_update', r(3)))
            elif addr == W.SET_RHOMBUS:
                self.calls.append(('rhombus', r(3)))
            elif addr == W.AER_SLIP_HOMING:
                self.calls.append(('homing', r(3)))
            return                       # the game's own code runs
        if addr in (SHAPE_RHOMBUS, SHAPE_CIRCLE):
            self.calls.append(('shape', addr))
            self.ret()
            return
        if addr == AI_TPOS:
            self.ai_calls += 1
            if r(4) < 0x80000000:
                self.wf(r(5), self.tpos[0])
                self.wf(r(5) + 4, self.tpos[1])
                self.wf(r(5) + 8, 0.0)
            self.ret()
        elif addr == AI_INPUT:
            self.wf(r(4), 0.0)
            self.wf(r(4) + 4, 0.0)
            self.ret()
        elif addr == STUB0:
            self.uc.reg_write(T.FR[1], 0)
            self.ret(0)
        else:
            FT.Machine.hook(self, u, addr, size, _)

    def ground_on(self):
        return self.uc.mem_read(T.GROUND + GROUND_ON, 1)[0] != 0

    def kinetic_step(self):
        """the kinetic module's frame: every enabled energy's update, then posture += the summed speed, but only
        with the ground collision on: the GroundModule's update (vt+0x64, 0x02C35C9C) returns at once while +0xDE is 0,
        so its GroundCollisionObject is never added to the collision manager (0x02D61264), which moves it"""
        self.call(EN_UPDATE_ALL, {3: EKM, 4: 0xFFFFFFFF})
        out = HEAP + 0x3B000
        self.call(SUM3, {3: out, 4: EKM, 5: 0xF})
        vx, vy = self.rf(out), self.rf(out + 4)
        if self.ground_on():
            self.wf(POSTURE + 0x10, self.rf(POSTURE + 0x10) + vx)
            self.wf(POSTURE + 0x14, self.rf(POSTURE + 0x14) + vy)
        return vx, vy

    def e0(self):
        return self.rf(EKM + 0x124), self.rf(EKM + 0x128), self.r32(EKM + 0x124 + 0x44), \
            self.uc.mem_read(EKM + 0x124 + 0x18, 1)[0]


def pos(m):
    return m.rf(POSTURE + 0x10), m.rf(POSTURE + 0x14)


def fly(img, w, D, fn, frames, start=(0.0, 30.0), target=(70.0, 0.0), state=None, setup=None):
    """the kind's start (slot 41) and its states for `frames` frames (smashrun_walker_test.World's rules: a deferred
    change_state takes effect next frame, enter then update); returns (machine, log of (state, x, y, vx, vy))"""
    m = Motion(img)
    cfg = D['cfg_' + w['name']]
    m.flier(cfg, kind=w['kind'])
    m.wf(OBJ + 0x10, 1.0)                   # facing right
    m.wf(POSTURE + 0x60, 1.0)
    m.uc.mem_write(OBJ + W.AER, bytes(0x74))
    m.wf(POSTURE + 0x10, start[0])
    m.wf(POSTURE + 0x14, start[1])
    m.target, m.target_x, m.target_y = 0, target[0], target[1]
    m.tpos = target
    m.found = -1
    m.view = 1
    m.ground, m.ray_hit = False, None       # in the air, no floor below (the ray check misses)
    if setup:
        setup(m)
    vtf = D['vt_' + w['name']] if w.get('vtover') else D['vtf']
    m.calls = []
    m.call(img.u32(vtf + 0xC + 8 * 41), {3: OBJ})
    m.start_calls = list(m.calls)
    rows = {sid: (fn[s[0]], fn[s[1]]) for sid, s in w['states'].items() if s != 'remove'}
    chg = [c for c in m.calls if c[0] in ('chg', 'chgi')]
    cur = chg[-1][2] if chg else (state or w['start'][0])
    pending = cur
    log = []
    for i in range(frames):
        if pending is not None:
            cur, pending = pending, None
            m.calls = []
            m.call(rows[cur][0], {3: OBJ})
        m.calls = []
        m.uc.mem_write(T.INPUT, struct.pack('>ff', 0.0, 0.0))
        m.call(rows[cur][1], {3: OBJ, 4: T.INPUT})
        repick = any(c[0] == 'homing' for c in m.calls)
        for c in m.calls:
            if c[0] == 'chg':
                pending = c[2]
            elif c[0] == 'chgi':
                pending = None
                cur = c[2]
                m.calls = []
                m.call(rows[cur][0], {3: OBJ})
        vx, vy = m.kinetic_step()
        x, y = pos(m)
        log.append((cur, round(x, 2), round(y, 2), round(vx, 3), round(vy, 3), repick))
    return m, log


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


INIT_AFTER = 0x02DB4AC8         # BehaviorImpl::initialize_after (slot 42; fix v3's hook at 0x02DB4B20 calls slot 49)
LINK_EVENT, EVENT_INDEX = 0x02C55B04, 0x026A9748      # set_lr's link event / the listeners' index (stubbed)
POSTURE_SETLR = 0x02000078      # the PostureModule's own set_lr (its vt+0x7C, reverse_lr's first call): lr = f1


class Facing(Motion):
    """step 2g v3: the game's own set_lr 0x026A780C, reverse_lr 0x026A7A20, damage_turn 0x02DB4E84 and initialize_after
    0x02DB4AC8 run as code (their link event / listener calls stubbed; slot 38 is the cave's w_noflip)"""
    RUN = {W.SET_LR, W.REVERSE_LR, W.DAMAGE_TURN, INIT_AFTER}

    def __init__(self, img):
        Motion.__init__(self, img)
        self.w32(POSTURE + 0x78, ACC)
        self.w32(ACC + 0x24, GMOD)
        self.uc.mem_write(HEAP + 0x3D000, bytes(0x100))
        self.w32(ACC + 0x3118, HEAP + 0x3D000)
        self.w32(HEAP + 0x3D000 + 0x80, ACC)
        self.w32(ACC + 0x30F0, T.MOTION)
        self.w32(ACC + 0x30D4, HEAP + 0x3D200)          # the DamageModule: +0x6C +0x2C the hit's lr
        self.uc.mem_write(HEAP + 0x3D200, bytes(0x100))
        self.w32(POSTURE, HEAP + 0x3D400)
        self.w32(HEAP + 0x3D400 + 0x7C, POSTURE_SETLR)

    def hook(self, u, addr, size, _):
        if addr in self.RUN:
            self.calls.append(('run', addr))
            return
        if addr in (LINK_EVENT, EVENT_INDEX):
            self.ret(0xFFFFFFFF)
            return
        if addr == POSTURE_SETLR:
            self.wf(POSTURE + 0x60, self.fr(1))
            self.ret()
            return
        Motion.hook(self, u, addr, size, _)


def facing(img, D, kinds):
    """spawn on both sides (posture lr from the spawner, the Enemy's +0x64 1.0, then initialize_after), then two hits
    from behind (damage_turn -> reverse_lr): the posture yaw (+0x64) after each"""
    out = {}
    for w in kinds:
        vt = D['vt_' + w['name']] if w.get('vtover') else D['vtf' if w.get('flier') else 'vt']
        for lr in (1.0, -1.0):
            m = Facing(img)
            m.flier(D['cfg_' + w['name']], kind=w['kind'], lr=lr) if w.get('flier') else \
                m.walker(D['cfg_' + w['name']], kind=w['kind'], lr=lr)
            m.w32(OBJ + 0xE0, vt)
            m.wf(POSTURE + 0x60, lr)
            m.wf(POSTURE + 0x64, 1.0)                # the Enemy's posture init (0x02D89EF0)
            m.call(INIT_AFTER, {3: OBJ})
            flips = lambda: [c[1] for c in m.calls if c[0] == 'flip']  # noqa: E731
            yaws = [(m.rf(POSTURE + 0x60), m.rf(POSTURE + 0x64), flips()[-1:])]
            for _hit in range(2):
                m.wf(HEAP + 0x3D200 + 0x6C + 0x2C, -m.rf(POSTURE + 0x60))
                n0 = len(flips())
                m.call(W.DAMAGE_TURN, {3: OBJ})
                yaws.append((m.rf(POSTURE + 0x60), m.rf(POSTURE + 0x64), flips()[n0:][-1:]))
            out[(w['name'], lr)] = yaws
    return out


def main():
    img = E.Image(sys.argv[1])
    vt_words = W.read_vt(img)
    A, B, d = W.assemble(vt_words)
    D = d.addr
    T.VT_ADDR[0] = D['vtf']
    fn = dict(A.labels)
    by = {w['name']: w for w in W.FLIERS}

    # the module the game's ctor built: energy 0 at +0x124 registered as energy 0, energy 1 at +0x200
    m = Motion(img)
    check(m.r32(EKM + 0x18) == EKM + 0x124 and m.r32(EKM + 0x28) == EKM + 0x200 and m.r32(EKM + 0x124 + 0x1C) ==
          0x10122F24, 'the EnemyKineticModule (game ctor 0x02DBD288): energy 0 = +0x124 (vtable 0x10122F24), '
          'energy 1 = +0x200')

    # step 2g v3: the spawn facing, through the game's own set_lr / reverse_lr / damage_turn / initialize_after
    allk = {w['name']: w for w in W.WALKERS}
    names = [n for n in ('kuribo', 'heiho', 'waddledee', 'churine', 'ghos', 'tikibuzz', 'furiijio', 'propellerheiho')
             if n in allk]
    fc = facing(img, D, [allk[n] for n in names])
    bad = {}
    for (n, lr), yaws in fc.items():
        k = allk[n]['kind']
        lrs = [lr, -lr, lr]
        # step 2g v6: the kinds with a model.flp keep lr x 90 and the motion flip (MotionModule 0x02C6108C(lr == 1))
        # follows every turn; Churine / Propeller Heiho (no table) keep the yaw hold; the others never flip
        want = [(x, -90.0 if (k in W.YAW_HOLD and x == 1.0) else 90.0 * x,
                 [int(x == 1.0)] if k in W.FLIP_TABLE else []) for x in lrs]
        if yaws != want:
            bad[(n, lr)] = yaws
    check(not bad, 'step 2g v3 / v6: spawned on either side (lr 1 / -1), then turned twice by hits from behind (the '
          'game\'s initialize_after, set_lr, damage_turn, reverse_lr with the cave\'s slots 49 / 50): yaw lr x 90 and '
          'the motion flip set to lr == 1 at every turn for the kinds with a model.flp; yaw -90 at lr 1 for Churine '
          '/ Propeller Heiho (no table); lr x 90 and no flip for the others (%s); wrong: %s'
          % (', '.join(names), bad))

    start, target = (0.0, 30.0), (70.0, 0.0)
    d0 = dist(start, target)
    runs = {}
    for name, n in (('ghos', 240), ('tikibuzz', 120), ('furiijio', 60), ('propellerheiho', 120)):
        if name not in by:                  # an older build (step 2e: Ghos and Tiki Buzz only)
            continue
        st = (0.0, 100.0) if name == 'propellerheiho' else start
        m, log = fly(img, by[name], D, fn, n, st, target)
        runs[name] = (m, log)
        rh = [c for c in m.start_calls if c[0] == 'rhombus']
        check(rh == [('rhombus', OBJ)] and m.ground_on(),
              '%s start: set_rhombus(this) -> GroundModule +0xDE on (its ground collision; without it the game never '
              'moves the enemy) %s, +0xDE %d' % (name, rh, m.ground_on()))
        p = pos(m)
        moved = [e for e in log if e[3] or e[4]]
        states = sorted(set(e[0] for e in log))
        e0 = tuple(round(v, 3) if isinstance(v, float) else v for v in m.e0())
        if name == 'propellerheiho':
            # 4 (height) brings it down to the fighter's height (y 0), then 5 patrols with the cosine bob (both ways)
            ys = [e[2] for e in log]
            check(min(ys) < 10.0 and max(ys[ys.index(min(ys)):]) > min(ys) + 5.0 and len(moved) > n // 2,
                  'propellerheiho: flies down to the fighter\'s height and patrols: y 100 -> min %.1f, then up to '
                  '%.1f, x %.1f; states %s' % (min(ys), max(ys[ys.index(min(ys)):]), p[0], states))
        else:
            # Ghos drifts slowly by its 3DS P7 set 0 (max speed 0.052 x / 0.15 y a frame; set 1, 4 %, dashes)
            need = 5.0 if name == 'ghos' else 10.0
            check(dist(p, target) < d0 - need and len(moved) > n // 2,
                  '%s: flies toward the fighter: (%.1f, %.1f) -> (%.1f, %.1f) in %d frames (target (%.0f, %.0f), '
                  'distance %.1f -> %.1f; %d frames with a speed; states %s; energy 0 (x, y, type, on) %s)' % (
                      name, start[0], start[1], p[0], p[1], n, target[0], target[1], d0, dist(p, target),
                      len(moved), states, e0))
    # Ghos's re-pick (L66BA4, every 20-40 frames) is the 3DS's slip homing: the speed carries on through it (the
    # Wii U's 0x02DB28E4 starts energy 0 at speed 0: the cave puts the speed back)
    if 'ghos' in runs:
        log = runs['ghos'][1]
        rp = [i for i, e in enumerate(log) if e[5] and i > 0]
        drops = [(i, log[i - 1][3:5], log[i][3:5]) for i in rp
                 if math.hypot(*log[i][3:5]) < 0.5 * math.hypot(*log[i - 1][3:5])]
        check(rp and not drops, 'ghos: the speed carries on through each slip-homing re-pick (frames %s; speed '
              'drops %s)' % (rp, drops[:3]))
    print('%d failure(s)' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
