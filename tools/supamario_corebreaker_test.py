#!/usr/bin/env python3
"""Core Breaker (Supamario's up special) offline checks: the compiled MSC (cb_* through the SpecialHi status
functions, in rolloff_hold_test's MSC interpreter) driving a small physics model of the game, the built scripts,
motion and effects.

  python3 -I tools/supamario_corebreaker_test.py BUILD_OUT_DIR MODEL_VBN

BUILD_OUT_DIR: tools/supamario_corebreaker_build.py's OUT_DIR (fighter/supamario, corebreaker_fx.json,
corebreaker_frames.json).

The model of the game (the assumptions, as the README's "Core Breaker" lists them): energy 1 (gravity) moves him
up / down by its speed, its acceleration added each frame and its limit clamping a fall; energy 3 moves him along
world X; KineticModule(0, t) resets them to his own (gravity -0.09, max fall 1.5, X kept); on the ground type 6 a
friction of 0.08 a frame; he lands when he reaches the floor's height over the stage (x within it) moving down;
the motion advances by its rate (MotionModule(4)); a status change (StatusModule 3) ends the run; the game script's
catch is modelled (cb 2 -> 3 and the slot) when the victim is within reach of his fist on a dive frame; the victim's
place follows the offsets the MSC writes.

Checks: the rise's height and armor, the hover (still, no armor, the B-reverse), the dive's speed and angle, its
armor and air cap, the light homing (only ahead / below, within its cone, its turn rate and limit), a miss landing on
the stage (the long landing lag, Wait), a dive off the stage (no lower than his start: FallSpecial), an air start,
a catch on the stage (the hold at his fist, the controller off, the drive, the crash, the hand-off to gf_tick's
put-down, Wait), a catch off the stage (the explosion, the victim let go: stage collision back, controller on,
FallSpecial), the status cut mid-hold (let go), an earlier God Fist victim let go at the catch; the scripts' damage
(26% each way), the explosion's KO knockback; TransN 0 in the motion; the effects' facing rule (the God Fist's).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import omo  # noqa: E402
import ptcl  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
import supamario_corebreaker_build as B  # noqa: E402
import supamario_godfist_build as GB  # noqa: E402
import xv2_smash_fx as FX  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


def near(a, b, tol):
    return abs(a - b) <= tol


GRAVITY, MAX_FALL, FRICTION = 0.09, 1.5, 0.08
FUNC_MAIN, FUNC_LOOP, FUNC_END = 2287, 2288, 2289


class Game:
    """his physics, the motion, the variables, the victim (player slot 2)"""

    def __init__(self, x=0.0, y=0.0, face=1.0, stage=(-80.0, 80.0), floor=0.0, victim=None):
        self.x, self.y, self.face = x, y, face
        self.stage, self.floor = stage, floor
        self.vx, self.vy, self.acc, self.lim = 0.0, 0.0, 0.0, 30.0
        self.kin = None
        self.air = not (stage[0] <= x <= stage[1] and abs(y - floor) < 1e-6)
        self.frame, self.rate = 0.0, 1.0
        self.status = None
        self.vars = {}
        self.flags = set()
        self.flag_log = []              # (frame, flag, on)
        self.armor = []                 # (frame, on)
        self.sounds = []                # (frame, 'play' / 'stop', id)
        self.stick_back = None          # the game frame the stick is held back from
        self.victim = victim            # {'x', 'y', 'off': (fwd, up) or None, 'ground', 'input', 'status', ...}
        self.n = 0                      # game frames run

    def fvar(self, v):
        if v in self.vars:
            return self.vars[v]
        if v == 0x0F000000:
            return self.x
        if v == 0x0F000001:
            return self.y
        if v == 0x0F000003:
            return self.face
        if v == 0x0F000110:                         # his stick X along his facing
            return -1.0 if self.stick_back is not None and self.n >= self.stick_back else 0.0
        vi = self.victim
        if vi is not None:
            if v in (0x0F000024, 0x0F000025):
                return (vi['x'], vi['y'])[v - 0x0F000024]
            if v == 0x0F000027:
                return vi.get('facing', -1.0)
            if v == 0x0F0000A2 + 8 * 4:
                return float(vi.get('status', 0x47))
        return 0.0

    def setvar(self, v, val):
        vi = self.victim
        t = 4                                       # slot 2: target 4
        if vi is not None:
            if v == 0x0F000045 + 8 * t:
                vi['offx'] = val
                vi['x'] = self.x + val * self.face
                return
            if v == 0x0F000046 + 8 * t:
                vi['y'] = self.y + val
                return
            if v == 0x0F0000A6 + 8 * t:
                vi['ground'] = val
                return
            if v == 0x0F000115 + 0x20 * t:
                vi['input'] = val
                return
            if v in (0x0F000040 + 8 * t, 0x0F000044 + 8 * t):
                vi.setdefault('held', []).append(self.n)
                return
        self.vars[v] = val

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x16:
            if a[0] == 0 and len(a) == 3:
                self.setvar(a[2], f(a[1]))
            elif a[0] == 6 and len(a) == 2:
                if a[1] == 0x11000002:
                    return 0x221
                if a[1] == 0x11000003:
                    return 0x225
                return int(self.fvar(a[1]))
            elif a[0] == 0x2710 and len(a) == 2:
                self.flags.add(a[1])
                self.flag_log.append((self.n, a[1], 1))
            elif a[0] == 0x2711 and len(a) == 2:
                self.flags.discard(a[1])
                self.flag_log.append((self.n, a[1], 0))
            return 0
        if sid == 0x10:                             # KineticModule
            op = a[0]
            if op == 0:
                self.kin = a[1]
                if a[1] == 0:
                    self.acc, self.lim = -GRAVITY, MAX_FALL
                elif a[1] == 6:
                    self.vy = 0.0
            elif op == 0x11 and a[1] == 3:
                self.vx = f(a[2])
            elif op == 0x11 and a[1] == 1:
                self.vy = f(a[2])
            elif op == 0x11 and a[1] == 2:
                pass
            elif op == 0xF and a[1] == 1:
                self.acc = f(a[2])
            elif op == 0x14 and a[1] == 1:
                self.lim = f(a[2])
            return 0
        if sid == 0x12:                             # MotionModule
            if a[0] == 0x4:
                self.rate = f(a[1])
            if a[0] == 0x2712:
                return 0
            return 0
        if sid == 0x13 and a == [0x1]:
            return R.f2i(self.frame)
        if sid == 0x18:                             # StatusModule
            if a[0] == 0x2:
                self.air = a[1] == 2
            if a[0] == 0x3:
                self.status = a[1]
            if a[0] == 0x1:
                return 2 if self.air else 0
            return 0
        if sid == 0x14 and a and a[0] == 0x271C:     # PostureModule: turn
            self.face = -self.face
            return 0
        if sid == 0x24 and a and a[0] == 0xB:       # DamageModule armor
            self.armor.append((self.n, a[1]))
            return 0
        if sid == 0x1E:                             # SoundModule
            self.sounds.append((self.n, {0x2710: 'play', 0x2714: 'stop'}.get(a[0], a[0]), a[1] if len(a) > 1 else None))
            return 0
        if sid == 0xA:                              # MathF
            op = a[0]
            if op == 1:
                return R.f2i(math.atan2(f(a[1]), f(a[2])))
            if op == 4:
                return R.f2i(math.cos(f(a[1])))
            if op == 5:
                return R.f2i(math.sin(f(a[1])))
            if op == 0:
                return R.f2i(math.sqrt(max(0.0, f(a[1]))))
        return 0

    def physics(self):
        if self.air:
            self.vy += self.acc
            if self.vy < -self.lim:
                self.vy = -self.lim
            self.x += self.vx
            ny = self.y + self.vy
            if self.vy < 0 and self.stage[0] <= self.x <= self.stage[1] and ny <= self.floor <= self.y:
                ny = self.floor
                self.air = False
                self.vy = 0.0
            self.y = ny
        else:
            self.x += self.vx
            self.vx = self.vx - FRICTION * (1 if self.vx > 0 else -1) if abs(self.vx) > FRICTION else 0.0
        self.frame += self.rate


def vm_for(path, g):
    vm = R.VM(path)
    vm.game = g
    vm.g[11] = vm.func(17).bounds[0]
    vm.g[18] = 2 if g.air else 0
    return vm


def run(path, g, frames=420, catch_at=None, cut_at=None, victim_reach=None):
    """the status from its main (func_2287) frame by frame; catch_at: the game frame the game script's catch is
    modelled at (cb 2 -> 3), victim_reach: catch when the victim is within this of his fist instead; cut_at: the status
    cut (func_2289) then. Returns the per-frame trace [(n, frame, x, y, cb_ph var, air)]"""
    vm = vm_for(path, g)
    vm.call(vm.func(FUNC_MAIN))
    trace = []
    for n in range(frames):
        g.n = n
        vm.g[18] = 2 if g.air else 0
        cbv = g.vars.get(B.CB_VAR, 0.0)
        if cbv == 2.0 and g.victim is not None:
            fx = g.x + 6.3 * g.face
            fy = g.y + 3.1
            reach = victim_reach is not None and math.hypot(g.victim['x'] - fx, g.victim['y'] + 5 - fy) < victim_reach
            if (catch_at is not None and n >= catch_at) or reach:
                g.vars[B.CB_VAR] = 3.0
                g.vars[B.CB_V_SLOT] = 2.0
        if cut_at is not None and n == cut_at:
            vm.call(vm.func(FUNC_END))
            g.status = 'cut'
        if g.status is None:
            vm.call(vm.func(FUNC_LOOP))
        vs = dict(g.victim) if g.victim is not None else None
        trace.append((n, g.frame, g.x, g.y, g.vars.get(B.CB_VAR, 0.0), g.air, vs))
        if g.status is not None:
            if g.status != 'cut':
                vm.call(vm.func(FUNC_END))
            break
        g.physics()
    return trace


def armor_at(g, n):
    on = 0
    for f, v in g.armor:
        if f <= n:
            on = v
    return on


def msc_tests(path):
    # 1. from the ground, a miss landing back on the stage (no victim)
    g = Game()
    tr = run(path, g)

    lift = next(t for t in tr if t[3] > 0.01)
    check('ground: still to the lift-off (%d), up from it' % B.RISE_FROM, int(lift[1]), B.RISE_FROM + 1)
    hover = next(t for t in tr if t[4] == 1.0)
    check('the rise: %.1f up at the hover (RISE_HEIGHT %.1f, within 3)' % (hover[3], B.anim.RISE_HEIGHT),
          near(hover[3], B.anim.RISE_HEIGHT, 3.0), True)
    hn = hover[0]
    still = [t for t in tr if t[4] == 1.0]
    check('the hover: still (%d frames)' % len(still), max(abs(t[3] - still[0][3]) + abs(t[2] - still[0][2])
                                                         for t in still) < 0.01, True)
    check('the hover: %d frames' % (B.DIVE_FROM - B.HOVER_FROM), len(still), B.DIVE_FROM - B.HOVER_FROM)
    check('armor: on through the rise, off for the hover, on for the dive',
          (armor_at(g, 0), armor_at(g, hn - 1), armor_at(g, hn), armor_at(g, hn + 10),
           armor_at(g, still[-1][0] + 2)), (1, 1, 0, 0, 1))
    dive = [t for t in tr if t[4] == 2.0]
    d0, d1 = dive[1], dive[2]
    ang = math.degrees(math.atan2(-(d1[3] - d0[3]), (d1[2] - d0[2])))
    spd = math.hypot(d1[3] - d0[3], d1[2] - d0[2])
    check('the dive: %.1f a frame (%.2f) at %.1f degrees (%.0f)' % (spd, B.DIVE_V, ang, B.DIVE_DEG),
          (near(spd, B.DIVE_V, 0.05), near(ang, B.DIVE_DEG, 0.2)), (True, True))
    cap = [(n, on) for n, fl_, on in g.flag_log if fl_ == 0x20000044]
    check('the dive: the air speed cap lifted from its first frame (flag 0x20000044), back at the landing',
          (cap[0][1], cap[0][0] == dive[0][0], cap[-1][1]), (1, True, 0))
    land = next(t for t in tr if t[4] == 5.0)
    check('the miss lands on the stage: the landing (cb 5), the motion to %d' % B.LAND,
          (land[5], any(t[1] == B.LAND for t in tr)), (False, True))
    lag = tr[-1][0] - land[0]
    check('the miss: Wait after its long landing lag (%d frames, ~%d)' % (lag, B.LAND_LAG),
          (g.status, near(lag, B.LAND_LAG, 3)), (0, True))
    check('the Rush sound stopped at the landing', any(s[1] == 'stop' and s[2] == B.SE_IDS['cb_rush']
                                                       and s[0] == land[0] for s in g.sounds), True)
    check('no armor left, the air cap back', (armor_at(g, 10 ** 6), 0x20000044 in g.flags), (0, False))
    # 2. off the stage (no ground): the dive stops at his start height -> FallSpecial
    g = Game(x=0.0, y=-30.0, stage=(1000.0, 1001.0))
    tr = run(path, g)
    low = min(t[3] for t in tr)
    check('off the stage: FallSpecial (0x10), never below his start - %.0f (lowest %.1f)' % (B.FLOOR_MARGIN, low),
          (g.status, low >= -30.0 - B.FLOOR_MARGIN - B.DIVE_V), (0x10, True))
    check('off the stage: no armor left, air cap back', (armor_at(g, 10 ** 6), 0x20000044 in g.flags), (0, False))
    # 3. the B-reverse in the hover
    g = Game(stage=(-1000.0, 1000.0))
    g.stick_back = B.HOVER_FROM + 5
    tr = run(path, g)
    dive = [t for t in tr if t[4] == 2.0]
    check('the hover: the stick back turns him (the dive goes the other way)', dive[2][2] < dive[1][2], True)
    # 4. light homing: a fighter ahead and below, a little off the line
    for name, vx, vy, want in (('ahead / below, 6 degrees steeper', 30.0, -40.0, 'steeper'),
                               ('above him', 30.0, 120.0, 'none'), ('behind him', -30.0, -10.0, 'none'),
                               ('far below the line (out of the cone)', 2.0, -45.0, 'none')):
        g = Game(stage=(-1000.0, 1000.0), victim={'x': vx, 'y': vy, 'status': 0})
        tr = []
        vm = vm_for(path, g)
        vm.call(vm.func(FUNC_MAIN))
        angs = []
        for n in range(B.DIVE_FROM + 12):
            g.n = n
            vm.g[18] = 2 if g.air else 0
            if g.vars.get(B.CB_VAR) == 2.0 and g.victim:
                # place it on a line steeper than the dive, relative to him (it moves with him)
                if want == 'steeper' or name.startswith('far'):
                    d = 30.0
                    a = math.radians(B.DIVE_DEG + (6.0 if want == 'steeper' else 40.0))
                    g.victim['x'] = g.x + d * math.cos(a)
                    g.victim['y'] = g.y - d * math.sin(a)
                elif name == 'above him':
                    g.victim['x'], g.victim['y'] = g.x + 30.0, g.y + 10.0
                else:
                    g.victim['x'], g.victim['y'] = g.x - 30.0, g.y - 10.0
            vm.call(vm.func(FUNC_LOOP))
            if g.vars.get(B.CB_VAR) == 2.0:
                angs.append(math.degrees(math.atan2(-g.vy, g.vx * g.face)))
            g.physics()
        if want == 'steeper':
            steps = [b - a for a, b in zip(angs, angs[1:])]
            check('homing (%s): steeper, at most %.1f a frame, at most %.0f off' % (name, B.HOME_TURN, B.HOME_MAX),
                  (angs[-1] > B.DIVE_DEG + 1, max(steps) <= B.HOME_TURN + 1e-3,
                   max(angs) <= B.DIVE_DEG + B.HOME_MAX + 1e-3), (True, True, True))
        else:
            check('homing (%s): none' % name, max(abs(x - B.DIVE_DEG) for x in angs) < 1e-3, True)
    # 5. a catch on the stage: the hold, the drive, the crash, the hand-off, Wait
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    tr = run(path, g, catch_at=B.DIVE_FROM + 4)
    phases = []
    for t in tr:
        if not phases or phases[-1] != t[4]:
            phases.append(t[4])
    check('catch on the stage: the phases', phases, [0.0, 1.0, 2.0, 3.0, 4.0, 6.0])
    hold = [t for t in tr if t[4] == 3.0]
    mid = hold[len(hold) // 2][6]
    check('the hold: the victim at his fist (offsets %.0f, %.0f), its controller off, no stage collision'
          % (B.HOLD_X, B.HOLD_Y), (mid.get('offx'), round(mid['y'] - hold[len(hold) // 2][3], 3), mid.get('input'),
                                   mid.get('ground')), (B.HOLD_X, B.HOLD_Y, 1.0, 0.0))
    check('the hold and the drive: the victim held every frame (hitstun / hitstop)',
          all(t[0] in t[6].get('held', []) for t in tr if t[4] in (3.0, 4.0)), True)
    check('the hold: he goes up %.0f' % B.HOLD_RISE, near(max(t[3] for t in hold) - hold[0][3], B.HOLD_RISE, 1.0),
          True)
    drive = [t for t in tr if t[4] == 4.0]
    da = math.degrees(math.atan2(-(drive[2][3] - drive[1][3]), drive[2][2] - drive[1][2]))
    check('the drive: down %.0f degrees' % B.DRIVE_DEG, near(da, B.DRIVE_DEG, 0.3), True)
    check('the crash: on the ground, Wait at the end (%d)' % B.CRASH_END, (tr[-1][5], g.status), (False, 0))
    check('the hand-off: gf_tick put-down (gf_phase 5), its slot and lock, %d frames' % B.FALL_WAIT,
          (g.vars.get(GB.V_PHASE), g.vars.get(GB.V_SLOT), g.vars.get(GB.V_LOCK), g.vars.get(GB.V_CNT)),
          (5.0, 2.0, 2.0, B.FALL_WAIT))
    check('the crash: the victim on the floor in front of him before the hand-off', near(v['y'], 0.0, 0.01), True)
    check('the crash: the explosion and Hit sounds; Down at the hand-off',
          all(any(s[1] == 'play' and s[2] == i for s in g.sounds) for i in (B.SE_IDS['cb_explosion'], B.GF_DOWN_SE)),
          True)
    # 6. a catch off the stage: the explosion in the air, the victim let go, FallSpecial
    v = {'x': 30.0, 'y': -40.0, 'status': 0x47}
    g = Game(x=0.0, y=0.0, stage=(-1000.0, -900.0), victim=v)
    g.air = True
    tr = run(path, g, catch_at=B.DIVE_FROM + 4)
    phases = []
    for t in tr:
        if not phases or phases[-1] != t[4]:
            phases.append(t[4])
    check('catch off the stage: the phases (explosion in the air)', phases, [0.0, 1.0, 2.0, 3.0, 4.0, 7.0])
    check('off the stage: the victim let go (stage collision 5, controller on), FallSpecial',
          (v.get('ground'), v.get('input'), g.status), (5.0, 0.0, 0x10))
    rel = [t for t in tr if t[4] == 7.0]
    check('off the stage: he stays where the explosion is (no fall in it)',
          max(abs(t[3] - rel[0][3]) for t in rel) < 0.01, True)
    # 7. cut mid-hold (hit, grabbed): the victim let go at once
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    tr = run(path, g, catch_at=B.DIVE_FROM + 4, cut_at=B.DIVE_FROM + 20)
    check('cut mid-hold: the victim let go (stage collision 5, controller on), no armor',
          (v.get('ground'), v.get('input'), armor_at(g, 10 ** 6)), (5.0, 0.0, 0))
    # 8. an earlier God Fist victim (another slot, held down) is let go at the catch
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    g.vars[GB.V_PHASE] = 2.0
    g.vars[GB.V_SLOT] = 3.0
    g.vars[GB.V_LOCK] = 3.0
    run(path, g, catch_at=B.DIVE_FROM + 4, frames=B.DIVE_FROM + 8)
    check('an earlier God Fist victim (slot 3) let go at the catch (gf_release: its controller on, phase 0)',
          (g.vars.get(0x0F000115 + 0x20 * 5), g.vars.get(GB.V_PHASE)), (0.0, 0.0))


def ko_estimate():
    """Smash 4's knockback for the explosion (CRASH_DMG): KB = ((p/10 + p d/20) 200/(w+100) 1.4 + 18) KBG/100 + BKB,
    p the percent after the hit, w the weight (Mario 98); ~120 off the stage near the ledge KOs on a mid-size stage"""
    kb = B.EXPLOSION_KB
    out = []
    for start in range(0, 200, 5):
        p = start + B.CATCH_DMG + B.BURN_HITS * B.BURN_DMG + B.CRASH_DMG
        k = ((p / 10.0 + p * B.CRASH_DMG / 20.0) * 200.0 / 198.0 * 1.4 + 18.0) * kb['KBG'] / 100.0 + kb['BKB']
        out.append((start, round(k, 1)))
    return out


def script_tests(fdir):
    f = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'game.bin'))
    s = f.script('specialhi')
    hits = [c for c in s if c.ident == acmd.BY_NAME['extra_special_hitbox']]
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    dmg = [c.params[syn.index('Damage')] for c in hits]
    catch = max(d for d in dmg if d <= B.CATCH_DMG + 1e-6 and d >= B.CATCH_DMG - 1e-6)
    burn = [d for d in dmg if abs(d - B.BURN_DMG) < 1e-6]
    big = [d for d in dmg if abs(d - B.CRASH_DMG) < 1e-6]
    check('damage: catch %g + %d x %g + crash / explosion %g = 26 (both endings)' % (
        B.CATCH_DMG, len(burn), B.BURN_DMG, B.CRASH_DMG), (catch + sum(burn) + B.CRASH_DMG, len(big)), (26.0, 2))
    air = f.script('specialairhi')
    check('specialairhi: the same script', [(c.ident, c.params) for c in air], [(c.ident, c.params) for c in s])
    est = ko_estimate()
    first = next(st for st, k in est if k >= 120)
    print('     the explosion\'s knockback (Mario-weight, %% before the move -> KB): %s; KB 120 from %d%%' % (
        ', '.join('%d%%: %g' % e for e in est[::4]), first))


def motion_tests(fdir, vbn):
    bones = omo.vbn_read(vbn)
    trans = [h for n, _p, h in bones if n == 'TransN'][0]
    ents = dict(omo.pac_read(os.path.join(fdir, 'motion', 'body', 'main.pac')))
    hi = [ents[n] for n in ents if n.endswith('SpecialHi.omo') and 'Air' not in n][0]
    air = [ents[n] for n in ents if n.endswith('SpecialAirHi.omo')][0]
    o = omo.Omo(hi)
    check('motion: SpecialHi = SpecialAirHi, %d frames, TransN 0 on every frame (the MSC sets his speeds)'
          % (B.AIRREL_END + 1), (hi == air, o.frames, all(max(abs(x) for x in o.sample(trans, f)[0]) < 1e-6
                                                          for f in range(o.frames))), (True, B.AIRREL_END + 1, True))


def effect_tests(out_dir, fdir):
    doc = json.load(open(os.path.join(out_dir, 'corebreaker_fx.json')))
    calls = []
    for e in doc['effects']:
        for pt in e['parts']:
            if 'bone' in pt:
                calls.append({'name': '%d %s' % (e['bac_effect'], pt['xv2']), 'bone': pt['bone'],
                              'offset': pt['offset'], 'rot': pt['rot']})
    check('effects: every call facing-safe (the God Fist\'s rule)', FX.facing_check(calls), [])
    p = ptcl.Ptcl(open(os.path.join(fdir, 'effect', 'supamario', 'supamario.010d0000.ptcl'), 'rb').read())
    sets = [p.find_set(s['set']) for v in doc['sets'].values() for s in v]
    check('effects: every converted emitter facing-safe', FX.facing_emitters(p, sets), [])
    over = []
    for si in sets:
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None or p.field(d, 'alpha_init') <= 0 or p.field(d, 'blend_type') == FX.BLEND_SUB:
                continue
            pk = max(max(k[:3]) for t in (0, 1) for k in p.color_keys(d, t)) * p.field(d, 'color_scale')
            if pk > FX.HDR_CAP + 1e-3:
                over.append((si, round(pk, 2)))
    check('effects: nothing drawn past the HDR cap (%.1f)' % FX.HDR_CAP, over, [])
    gf = [i for i in range(len(p.sets)) if p.set_name(i).startswith('PtcSupamarioGf')]
    check('effects: the God Fist\'s sets still there', len(gf) > 0, True)
    # v2 (user, v1's clip: "Up special's charging effect seems to be played incorrectly"): the orb's own animation
    # in its frames on screen, its colours (not black), the mirrored quarter glows whole (no square)
    import mta
    orb = os.path.join(fdir, 'effect', 'supamario', 'model', doc['models']['Cor_Crg.emo']['folder'])
    oo = omo.Omo(open(os.path.join(orb, 'model.omo'), 'rb').read())
    m = mta.read(open(os.path.join(orb, 'model.mta'), 'rb').read())
    gains = {e['name'].split('_', 1)[1]: [v for pr in e['props'] if pr['name'] == 'NU_effColorGain'
                                          for v in pr['values']] for e in m['mats']}
    check('the charge orb: its animation in %d frames (on screen %d-%d), every material coloured (v1: core_a / '
          'core_b2 black)' % (B.ORB_FRAMES, B.ORB_ON, B.FLARE_FROM),
          (oo.frames, m['frames'], all(max(v[:3]) > 0.3 for g in gains.values() for v in g)),
          (B.ORB_FRAMES, B.ORB_FRAMES, True))
    quarter = []
    for v in doc['sets'].get('Cor_Crg_End_01.emp', []):
        si = p.find_set(v['set'])
        for k, em in enumerate(p.sets[si]['emitters']):
            d = em['data']
            if d is None or k >= len(v['emitters']) or v['emitters'][k] not in ('ptcl01', 'ptcl01_1', 'pitcl_01_st',
                                                                              'pitcl_01_st_1'):
                continue
            t = np.asarray(p.decode_texture(d, 0), dtype=np.float32)[..., 0]
            h, w = t.shape
            if not (t[h // 2, w // 2] > 200 and max(t[0, 0], t[0, -1], t[-1, 0], t[-1, -1]) < 40):
                quarter.append(v['emitters'][k])
    check('the charge end flash: ptcl01 a whole round glow (XV2 mirrors its quarter x2 x2; v1: a square)', quarter, [])
    e = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'effect.bin')).script('specialhi')
    eid = int(doc['models']['Cor_Crg.emo']['id'], 16)
    at, f_ = {}, 0
    for c in e:
        if c.ident == acmd.BY_NAME['frame']:
            f_ = int(c.params[0])
        if c.params and c.params[0] == eid:
            at.setdefault(acmd.INFO[c.ident]['name'], f_)
    check('the charge orb: on at %d, off at the flare (%d)' % (B.ORB_ON, B.FLARE_FROM),
          (at.get('External_Graphic'), at.get('Terminate_Graphic_Effect')), (B.ORB_ON, B.FLARE_FROM))
    bad = []
    syn = acmd.INFO[acmd.BY_NAME['external_graphic']]['syntax']
    for c in e:
        if c.ident == acmd.BY_NAME['external_graphic']:
            d = dict(zip(syn, c.params))
            if d['X'] != 0.0 or d['XRot'] != 0.0 or d['YRot'] not in (0.0, 180.0) or d['ZRot'] != 0.0 or \
                    (d['Bone'] != 0 and (d['Y'] != 0.0 or d['Z'] != 0.0)):
                bad.append(d)
    check('effect script: every External_Graphic facing-safe (bone 0: up / forward only; body bones: nothing)',
          bad, [])


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    out_dir, vbn = a
    fdir = os.path.join(out_dir, 'fighter', 'supamario')
    msc_tests(os.path.join(fdir, 'script', 'msc', 'supamario.mscsb'))
    script_tests(fdir)
    motion_tests(fdir, vbn)
    effect_tests(out_dir, fdir)
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
