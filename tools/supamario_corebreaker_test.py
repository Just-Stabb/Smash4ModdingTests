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
the stage (the long landing lag, Wait), v3's endless dive (off the stage it goes on, the motion's loop looped; a
landing far below his start; a wall ahead -> FallSpecial), an air start, a catch of a victim on the ground (v3: the
hold on the ground, the crash), of one in the air over the stage (the hold at his fist, the controller off, the drive,
the crash; the victim let go the frame before the crash's KO hit, Wait), a catch off the stage (the explosion, the
victim let go: stage collision back, controller on, FallSpecial), the status cut mid-hold (let go), an earlier God
Fist victim let go at the catch; the scripts' damage (26% on every path), the dive's catch-check loop, the crash's and
the explosion's KO knockback; TransN 0 in the motion; the effects' facing rule (the God Fist's).
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
import supamario_corebreaker_fx as CF  # noqa: E402
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

    def __init__(self, x=0.0, y=0.0, face=1.0, stage=(-80.0, 80.0), floor=0.0, victim=None, wall=None):
        self.x, self.y, self.face = x, y, face
        self.wall = wall                # (x, top): a wall at x from below up to top (v3: the dive stops at it)
        self.touch = 0                  # GroundModule(0x2722)'s side touched this frame: 2 left / 4 right wall
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
        self.n = 0                      # game frames run (the logs' clock)
        self.t = 0
        self.self_status = None         # his status as the variables read it (cb_reset_tick's test)
        self.frame_sets = []            # (n, frame) MotionModule(0x2713)
        self.used_log = []
        self.status_data = []
        self.stick_world = None
        self.turns = []
        self.inv_log = []               # (n, frames) the self INVINCIBLE writes
        self.dmg_log = []               # (n, %) his own DAMAGE writes (v6)
        self.vx2 = 0.0                  # energy 2 (the stick's air control: his air momentum), world X
        self.hit = False                # v4: his attack has hit the victim (AttackModule 0x2726 / 0x2727)
        self.cleared = []               # AttackModule(0x2719): his hitboxes cleared

    def fvar(self, v):
        if v in self.vars:
            return self.vars[v]
        if v == 0x0F000000:
            return self.x
        if v == 0x0F000001:
            return self.y
        if v == 0x0F000003:
            return self.face
        if v == 0x0F0000A2:
            return float(self.self_status if self.self_status is not None else 0x154)
        if v == 0x0F000110 and self.stick_world is not None:      # v4: a stick held (world X), along his facing
            return self.stick_world * self.face
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
            if v in (0x0F0000B2, ) and self.hit:         # v4: target 2 (the last fighter hit): the victim
                return float(vi.get('status', 0x47))
            if v == 0x0F00015B and self.hit:
                return float(vi.get('body', 0))
            if v in (0x0F000157, 0x0F000197) and (self.hit or v == 0x0F000197):
                return float(vi.get('dmg', 10.0))
            if v in (0x0F0000B5, 0x0F0000C5) and (self.hit or v == 0x0F0000C5):
                return float(vi.get('kind', 4.0))
            if v == 0x0F000116 + 0x20 * 4:              # its SITUATION (v3): 0 ground, 2 air
                if self.hit and 'sit_after_hit' in vi:  # v5: launched by the hit before the catch reads it
                    return float(vi['sit_after_hit'])
                if 'sit' in vi:
                    return float(vi['sit'])
                on = self.stage[0] <= vi['x'] <= self.stage[1] and abs(vi['y'] - self.floor) < 1e-6
                return 0.0 if on else 2.0
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
            if v == 0x0F0000A2 + 8 * t:
                vi['status'] = int(val)
                vi.setdefault('status_log', []).append(int(val))
                return
            if v in (0x0F000040 + 8 * t, 0x0F000044 + 8 * t):
                vi.setdefault('held', []).append(self.n)
                return
        if v == 0x0F00011C:
            self.inv_log.append((self.n, val))
        if v == 0x0F000117:
            self.dmg_log.append((self.n, val))
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
                self.vx2 = f(a[2])
            elif op == 0xF and a[1] == 1:
                self.acc = f(a[2])
            elif op == 0x14 and a[1] == 1:
                self.lim = f(a[2])
            return 0
        if sid == 0x12:                             # MotionModule
            if a[0] == 0x4:
                self.rate = f(a[1])
            if a[0] == 0x2713:                      # its frame set (v3: the dive's loop)
                self.frame = f(a[1])
                self.frame_sets.append((self.n, f(a[1])))
            if a[0] == 0x2712:
                return 0
            return 0
        if sid == 0x13 and a == [0x1]:
            return R.f2i(self.frame)
        if sid == 0x18 and a and a[0] == 0x2713:   # v6: the status data (its attack log: the 6th value)
            self.status_data.append(list(a[1:]))
            return 0
        if sid == 0x18:                             # StatusModule
            if a[0] == 0x2:
                self.air = a[1] == 2
            if a[0] == 0x3:
                self.status = a[1]
            if a[0] == 0x1:
                return 2 if self.air else 0
            return 0
        if sid == 0x11 and len(a) == 2 and a[0] in (0xA, 0xB):   # KineticModuleF(0xa / 0xb, energy): its x / y
            return R.f2i({(0xA, 1): 0.0, (0xB, 1): self.vy, (0xA, 2): self.vx2, (0xB, 2): 0.0,
                          (0xA, 3): self.vx, (0xB, 3): 0.0}.get((a[0], a[1]), 0.0))
        if sid == 0x2E and a:                        # AttackModule (v4: the dive's catch in the MSC)
            if a[0] == 0x2724:
                self.hit = False
            elif a[0] in (0x2726, 0x2727):
                return 1 if self.hit and (len(a) < 2 or a[1] & 2) else 0
            elif a[0] == 0x2719:
                self.cleared.append(self.n)
            return 0
        if sid == 0x1A and a and a[0] == 0x2722:     # GroundModule: touching (1 ceiling, 2 / 4 left / right wall)
            return 1 if a[1] == self.touch else 0
        if sid == 0x14 and a and a[0] == 0x1:        # PostureModule: ReverseLr (v4's B-reverse)
            self.face = -self.face
            self.turns.append(self.n)
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
        self.touch = 0
        if self.air:
            self.vy += self.acc
            if self.vy < -self.lim:
                self.vy = -self.lim
            nx = self.x + self.vx + self.vx2
            if self.wall is not None and self.vx != 0.0 and self.y < self.wall[1] and \
                    (self.x - self.wall[0]) * (nx - self.wall[0]) <= 0.0:
                nx = self.wall[0] - (0.01 if self.vx > 0 else -0.01)
                self.touch = 4 if self.vx > 0 else 2
            self.x = nx
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


def func_index(vm, name):
    """a function's script index in the compiled MSC (they are numbered in the order supamario.c defines them)"""
    import re
    src = open(os.path.join(HERE, '..', 'fighters', 'supamario', 'supamario.c')).read()
    names = [m.group(2) for m in re.finditer(r'^(int|void|float|bool)\s+(\w+)\s*\([^;]*$', src, re.M)]
    return len(vm.m.scripts) - 1 - (len(names) - 1 - names.index(name))


def run(path, g, frames=420, catch_at=None, cut_at=None, victim_reach=None, press=None, detect=False, tick=False,
        hit_at_dive=False, victim_move=None):
    """the status from its main (func_2287) frame by frame; catch_at: the game frame of this run the game script's
    dive catch is modelled at (cb 2 -> 3), victim_reach: catch when the victim is within this of his fist instead;
    detect: the hover's detection box catches (cb 1 -> 3) when the victim is within DETECT_SIZE + 2 of his middle on
    the hover's first frames; press: {frame of this run: global24 bits}; cut_at: the status cut (func_2289) then.
    Returns the per-frame trace [(n, motion frame, x, y, cb var, air, victim)]"""
    g.frame, g.rate, g.status = 0.0, 1.0, None
    vm = vm_for(path, g)
    vm.g[24] = 0
    vm.call(vm.func(FUNC_MAIN))
    trace = []
    for n in range(frames):
        g.n = g.t
        g.t += 1
        vm.g[18] = 2 if g.air else 0
        vm.g[24] = (press or {}).get(n, 0)
        cbv = g.vars.get(B.CB_VAR, 0.0)
        if cbv == 2.0 and g.victim is not None:
            fx = g.x + 6.3 * g.face
            fy = g.y + 3.1
            reach = victim_reach is not None and math.hypot(g.victim['x'] - fx, g.victim['y'] + 5 - fy) < victim_reach
            if (catch_at is not None and n >= catch_at) or reach:
                g.hit = True                    # v4: the hit; the MSC's cb_dive_catch does the rest
        if detect and cbv == 1.0 and g.victim is not None and B.HOVER_FROM <= g.frame <= B.HOVER_FROM + 3:
            mx, my = g.x + B.DETECT_AT[0] * g.face, g.y + B.DETECT_AT[1]
            if math.hypot(g.victim['x'] - mx, g.victim['y'] + 5 - my) < B.DETECT_SIZE + 2.0:
                g.vars[B.CB_VAR] = 3.0
                g.vars[B.CB_V_SLOT] = 2.0
        if victim_move is not None and g.victim is not None and not g.hit:
            victim_move(g, g.victim)            # v6: the victim moving before the hit (a jump)
        if hit_at_dive and g.frame >= B.DIVE_FROM - 1e-6 and cbv == 1.0:
            g.hit = True                        # v5: point-blank: his dive hitboxes connect on its first frame
        if cut_at is not None and n == cut_at:
            vm.call(vm.func(FUNC_END))
            g.status = 'cut'
        if tick:
            # the per-frame hook's cb_reset_tick (func_82), his status as the variable reads it: the status before
            # (Wait) on the up special's first frame (v4's ground reset bug)
            g.self_status = 0 if n == 0 else 0x154
            vm.call(vm.func(func_index(vm, 'cb_reset_tick')))
            g.used_log.append((n, g.vars.get(B.CB_USED, 0.0), g.air))
        if g.status is None:
            vm.call(vm.func(FUNC_LOOP))
        vs = dict(g.victim) if g.victim is not None else None
        trace.append((n, g.frame, g.x, g.y, g.vars.get(B.CB_VAR, 0.0), g.air, vs, g.n))
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


def phases_of(tr):
    out = []
    for t in tr:
        if not out or out[-1] != t[4]:
            out.append(t[4])
    return out


def both(path, g, **kw):
    """the rise (v4: to its held top, still in the air), then up special again: the hover / dive"""
    r1 = run(path, g, frames=B.HOVER_FROM + 3)
    r2 = run(path, g, **kw)
    return r1, r2


def msc_tests(path):
    used = lambda g: g.vars.get(B.CB_USED, 0.0)      # noqa: E731
    # 1. the rise alone, from the ground: up ~55, armor, Fall at its end (not FallSpecial), the rise used
    g = Game()
    tr = run(path, g)
    lift = next(t for t in tr if t[3] > 0.01)
    check('the rise: still to the lift-off (%d), up from it' % B.RISE_FROM, int(lift[1]), B.RISE_FROM + 1)
    top = max(t[3] for t in tr)
    check('the rise: %.1f up (RISE_HEIGHT %.1f, within 3)' % (top, B.anim.RISE_HEIGHT),
          near(top, B.anim.RISE_HEIGHT, 3.0), True)
    # v5 (user: v4's leap "never transitions to fall and keeps its pose until landing"): the whole rise animation,
    # then Fall at its last frame (actionable before it: v4)
    check('the rise: its whole animation, Fall (0xE) at its last frame (%d, never the hover\'s %d), in the air, the '
          'rise still used' % (B.HOVER_FROM - 1, B.HOVER_FROM),
          (g.status, max(t[1] for t in tr), tr[-1][1], tr[-1][5], used(g)),
          (0xE, float(B.HOVER_FROM - 1), float(B.HOVER_FROM - 1), True, 1.0))
    top = next(t for t in tr if t[1] >= B.HOVER_FROM - 1 - 1e-6)
    check('the rise: no armor at all (v4; v1-v3: super armor to its top)',
          [armor_at(g, t[7]) for t in tr if t[7] <= top[7]] == [0] * len([t for t in tr if t[7] <= top[7]]), True)
    check('the rise: from frame %d the fall\'s kinetic type (drift), its own forward speed off' % B.RISE_CANCEL,
          (g.kin, g.vx), (0, 0.0))
    # 2. up special again (from the held top): the hover / dive; a miss landing on the stage
    g = Game()
    run(path, g, frames=B.HOVER_FROM + 3)
    tr = run(path, g)
    check('up special again: the hover / dive (cb_used 2), the motion to the hover (%d)' % B.HOVER_FROM,
          (used(g), any(t[1] == B.HOVER_FROM for t in tr)), (2.0, True))
    check('the hover / dive: its phases (hover, dive, landing)', [p for p in phases_of(tr)], [1.0, 2.0, 5.0])
    still = [t for t in tr if t[4] == 1.0 and t[1] >= B.HOVER_FROM]
    check('the hover: still, %d frames, no armor' % (B.DIVE_FROM - B.HOVER_FROM),
          (max(abs(t[3] - still[0][3]) + abs(t[2] - still[0][2]) for t in still) < 0.01, len(still),
           armor_at(g, still[3][7])), (True, B.DIVE_FROM - B.HOVER_FROM, 0))
    dive = [t for t in tr if t[4] == 2.0]
    d0, d1 = dive[1], dive[2]
    ang = math.degrees(math.atan2(-(d1[3] - d0[3]), (d1[2] - d0[2])))
    spd = math.hypot(d1[3] - d0[3], d1[2] - d0[2])
    check('the dive: %.1f a frame (%.2f) at %.1f degrees (%.0f), armor' % (spd, B.DIVE_V, ang, B.DIVE_DEG),
          (near(spd, B.DIVE_V, 0.05), near(ang, B.DIVE_DEG, 0.2), armor_at(g, dive[2][7])), (True, True, 1))
    land = next(t for t in tr if t[4] == 5.0)
    lag = tr[-1][0] - land[0]
    check('the miss: Wait after its long landing lag (%d frames, ~%d)' % (lag, B.LAND_LAG),
          (g.status, near(lag, B.LAND_LAG, 3)), (0, True))
    check('no armor left, the air cap back', (armor_at(g, 10 ** 6), 0x20000044 in g.flags), (0, False))
    # 3. once per airtime: cb_can_up (the up special's hook, global26) and the resets (cb_reset_tick)
    vm = vm_for(path, g)
    can = vm.func(func_index(vm, 'cb_can_up'))
    tick = vm.func(func_index(vm, 'cb_reset_tick'))
    out = []
    for u, air in ((0.0, True), (1.0, True), (2.0, True), (2.0, False)):
        g.vars[B.CB_USED] = u
        vm.g[18] = 2 if air else 0
        out.append(vm.call(can))
    check('up special allowed: nothing used / the rise used (air), both used (air) no, on the ground yes', out,
          [1, 1, 0, 1])
    vm.call(vm.func(2249))
    check('the up special hook (global26) is cb_can_up', vm.g.get(26), can.bounds[0])
    resets = []
    for name, sit, st in (('landing', 0, 0x0), ('a ledge', 1, 0x74), ('a hit', 2, 0x46), ('a tumble', 2, 0x4C),
                          ('grabbed', 2, 0x3F), ('thrown', 2, 0x44), ('KO', 2, 0xB1), ('respawn', 2, 0xB2),
                          ('falling (no reset)', 2, 0xE), ('in the move (no reset)', 2, 0x154),
                          ('in the move on the ground (no reset)', 0, 0x154),      # v3 compared it as an int
                          ('an aerial (no reset)', 2, 0x34)):
        g.vars[B.CB_USED] = 2.0
        g.vars[B.CB_AIR] = 1.0                       # in the air since the use
        g.self_status = st
        vm.g[18] = sit
        vm.call(tick)
        resets.append((name, used(g)))
    g.vars[B.CB_USED], g.vars[B.CB_AIR], g.self_status, vm.g[18] = 1.0, 0.0, 0x0, 0
    vm.call(tick)
    resets.append(('on the ground, never in the air since (no reset)', used(g)))
    check('the uses reset on landing, a ledge, a hit, a grab, a KO; not while falling / attacking / in the move, nor '
          'on the ground before he has left it (v4)',
          resets, [(n, 0.0 if '(no reset)' not in n else (1.0 if 'never' in n else 2.0)) for n, _u in resets])
    g.self_status = None
    # 3a. v6 (user: "if Supamario is hit during or after the leap part of Core Breaker (without doing the dive yet) he
    # does the dive next time he uses up special"): with only the rise used, a hit (0x45-0x4C) keeps it; grabbed /
    # thrown (0x3F-0x44) still resets
    out = []
    for name, sit, st, u in (('rise used, hit', 2, 0x46, 1.0), ('rise used, tumbling', 2, 0x4C, 1.0),
                             ('rise used, hit on the ground (no landing yet)', 0, 0x45, 1.0),
                             ('rise used, grabbed', 2, 0x3F, 1.0), ('rise used, thrown', 2, 0x44, 1.0),
                             ('dive used, hit', 2, 0x46, 2.0)):
        g.vars[B.CB_USED], g.vars[B.CB_AIR], g.self_status, vm.g[18] = u, 0.0 if sit == 0 else 1.0, st, sit
        vm.call(tick)
        out.append((name, used(g)))
    check('a hit keeps the rise\'s use (the next up special: the hover / dive); grabbed / thrown resets; a hit after '
          'the dive resets', out, [('rise used, hit', 1.0), ('rise used, tumbling', 1.0),
                                   ('rise used, hit on the ground (no landing yet)', 1.0), ('rise used, grabbed', 0.0),
                                   ('rise used, thrown', 0.0), ('dive used, hit', 0.0)])
    g.self_status = None

    def seq(events):
        """the rise, then events [(status, situation)] through the per-frame reset, then up special: its first phase"""
        g_ = Game(stage=(-200.0, 200.0))
        run(path, g_)
        vm_ = vm_for(path, g_)
        tk = vm_.func(func_index(vm_, 'cb_reset_tick'))
        for st_, sit_ in [(0xE, 2)] + events:           # falling first (in the air since the use)
            if st_ == 'dive':
                run(path, g_, frames=B.DIVE_FROM - B.HOVER_FROM + 5)
                continue
            g_.self_status, vm_.g[18] = st_, sit_
            vm_.call(tk)
        g_.self_status = None
        if events and events[-1][1] == 0:
            g_.air, g_.y = False, 0.0
        u_ = used(g_)
        tr_ = run(path, g_, frames=8)
        return (u_, phases_of(tr_)[0])
    check('rise -> hit -> up special: the hover / dive (1); rise -> hit -> landing -> up special: the rise (0); dive '
          '-> hit out of it -> up special: the rise; rise -> ledge -> up special: the rise',
          [seq([(0x46, 2)]), seq([(0x46, 2), (0x45, 0)]), seq([('dive', 2), (0x46, 2)]), seq([(0x74, 1), (0xE, 2)])],
          [(1.0, 1.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)])
    # 3d. v6 (user: "make all of Core Breaker's hitboxes unaffected by staling"): the up special status's attack log
    # (StatusModule 0x2713's 6th value) empty, on both custom move IDs (vanilla: 0x1422 / 0 for custom 2)
    out = []
    for cid in (0, 1, 2):
        g = Game()
        g.vars[0x1000004a] = float(cid)
        vm = vm_for(path, g)
        vm.call(vm.func(2286))
        out.append(g.status_data[-1][5] if g.status_data else None)
    check('the up special status logs no attack (its 6th status-data value 0, every custom ID): no staling',
          out, [0, 0, 0])
    # 3c. v6 (user: "make sure that getting hit during/after the rise only consumes it after the vertical speed begins
    # being added"): the rise is used at its lift-off (frame RISE_FROM): cut in the crouch, the next up special is the
    # rise again; cut after the lift-off and hit, the next is the hover / dive
    out = []
    for name, cut in (('hit in the crouch (frame 3)', 3), ('hit after the lift-off (frame %d)' % (B.RISE_FROM + 3),
                                                            B.RISE_FROM + 3)):
        g = Game(x=0.0, y=40.0, stage=(1000.0, 1001.0))
        run(path, g, cut_at=cut, frames=cut + 2)
        vm = vm_for(path, g)
        g.self_status, vm.g[18] = 0x46, 2
        vm.call(vm.func(func_index(vm, 'cb_reset_tick')))
        g.self_status = None
        u = used(g)
        tr = run(path, g, frames=8)
        out.append((name, u, phases_of(tr)[0]))
    check('the rise used only from its lift-off: a hit in the crouch -> the rise again; after it -> the hover / dive',
          out, [('hit in the crouch (frame 3)', 0.0, 0.0), ('hit after the lift-off (frame %d)' % (B.RISE_FROM + 3),
                                                             1.0, 1.0)])
    # 3b. v4 (user: "The first press of up special on the ground should consume its one rising use"): a ground up
    # special with the per-frame reset running and his status read as the one before on its first frame: the rise
    # stays used; up special again: the hover / dive; a third does nothing in the air; the landing gives it back
    g = Game()
    r1 = run(path, g, tick=True)
    first = min(u for n, u, _a in g.used_log if n > B.RISE_FROM)      # v6: used from the lift-off
    tr = run(path, g, tick=True, frames=B.DIVE_FROM - B.HOVER_FROM + 15)
    vm = vm_for(path, g)
    vm.g[18] = 2
    third = vm.call(vm.func(func_index(vm, 'cb_can_up')))
    check('a ground up special: the rise used from its lift-off on (no reset on the ground before he leaves it), the '
          'second (from Fall) the hover / dive (cb_used 2), a third refused in the air',
          (first, phases_of(r1), phases_of(tr)[:2], used(g), third), (1.0, [0.0], [1.0, 2.0], 2.0, 0))
    g = Game()
    run(path, g, tick=True)
    run(path, g, tick=True)
    g.self_status = 0x0
    vm = vm_for(path, g)
    vm.g[18] = 0
    vm.call(vm.func(func_index(vm, 'cb_reset_tick')))
    check('... and the landing (Wait on the ground after being in the air) gives it back', used(g), 0.0)
    # 4. the rise's cancel: nothing before RISE_CANCEL; after it (v4: the air actions of Fall too) each one, in the
    # rise and in its held top
    for name, bits, want in (('an aerial', 0x1, 0x34), ('neutral special', 0x1000, 0x152),
                             ('side special', 0x2000, 0x153), ('down special', 0x8000, 0x155),
                             ('an air dodge', 0x400000, 0x22), ('a double jump', 0x200000, 0xD)):
        g = Game()
        g.vars[0x10000002] = 2.0                        # his jumps (one used: the ground jump, none here)
        run(path, g, press={B.RISE_CANCEL - 2: bits})
        early = g.status
        out = []
        for at in (B.RISE_CANCEL + 1, B.HOVER_FROM - 3):
            g = Game()
            g.vars[0x10000002] = 2.0
            tr = run(path, g, press={at: bits})
            out.append((g.status, tr[-1][0] == at))
        check('the rise: %s acts from frame %d to its end (not before: it goes on to Fall)'
              % (name, B.RISE_CANCEL), (early, out), (0xE, [(want, True), (want, True)]))
    g = Game()
    tr = run(path, g, press={B.RISE_CANCEL + 1: 0x4000})
    check('the rise: up special again in it goes to the hover / dive in place (cb_used 2, the motion to %d)'
          % B.HOVER_FROM, (used(g), any(t[1] == B.HOVER_FROM for t in tr), phases_of(tr)), (2.0, True, [0.0, 1.0, 2.0,
                                                                                                   5.0]))
    # 4b. v4 (user: "make the up special leap B-reversable/change facing direction based on direction held at the start
    # of the move"): the stick back in its first frames turns him, in the air his momentum with him; forward / neutral
    # nothing; both facings, ground and air
    out, want = [], []
    for air in (False, True):
        for face in (1.0, -1.0):
            for stick in ('back', 'forward', 'neutral'):
                g = Game(x=0.0, y=40.0 if air else 0.0, face=face,
                         stage=(1000.0, 1001.0) if air else (-200.0, 200.0))
                g.vx2 = 1.0 * face if air else 0.0                      # moving forward in the air
                g.stick_world = {'back': -face, 'forward': face, 'neutral': 0.0}[stick]
                tr = run(path, g, frames=B.RISE_FROM + 3)
                g.stick_world = None
                flip = stick == 'back'
                out.append((air, face, stick, g.face, len(g.turns), round(g.vx2, 3)))
                want.append((air, face, stick, -face if flip else face, 1 if flip else 0,
                             round((-1.0 if flip else 1.0) * face, 3) if air else 0.0))
    check('the rise\'s B-reverse: the stick back in its first %d frames turns him once (ground and air, both facings), '
          'his air momentum turned with him; forward / neutral: nothing' % B.TURN_WINDOW, out, want)
    g = Game()
    g.stick_back = B.TURN_WINDOW + 1
    run(path, g, frames=B.RISE_FROM + 3)
    check('the rise\'s B-reverse: not after its first %d frames' % B.TURN_WINDOW, (g.face, len(g.turns)), (1.0, 0))
    # 5. the hover's detection box: a fighter at his middle -> straight to the catch (no hover / dive)
    v = {'x': 1.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    r1 = run(path, g, frames=B.HOVER_FROM + 3)
    v['x'], v['y'] = g.x + B.DETECT_AT[0] * g.face, g.y + B.DETECT_AT[1] - 5.0
    tr = run(path, g, detect=True)
    check('the detection box catches: the hold, the drive, the crash (no hover, no dive)', phases_of(tr),
          [1.0, 3.0, 4.0, 6.0])
    check('the detection box: caught on the hover\'s first frames', min(t[1] for t in tr if t[4] == 3.0) <=
          B.HOVER_FROM + 3, True)
    v = {'x': 60.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    run(path, g, frames=B.HOVER_FROM + 3)
    tr = run(path, g, detect=True)
    check('the detection box misses (nobody at his middle): the hover, then the dive', phases_of(tr)[:2], [1.0, 2.0])
    # 5b. (user: "The detection box for Core Breaker should be able to hit a downed opponent"): lying fighters (DownWait,
    # DownBound) and a God Fist victim held down by gf_tick are caught, out of the down status into Damage
    for name, st, gf in (('DownWait', 0x50, False), ('DownBound', 0x4D, False), ('a God Fist victim held down', 0x50,
                                                                                   True)):
        # (lying on the ground, a platform at his middle's height: the hold on the ground, v3)
        v = {'x': 1.0, 'y': 0.0, 'status': st, 'sit': 0}
        g = Game(stage=(-200.0, 200.0), victim=v)
        run(path, g, frames=B.HOVER_FROM + 3)
        v['x'], v['y'] = g.x + B.DETECT_AT[0] * g.face, g.y + B.DETECT_AT[1] - 5.0
        if gf:
            g.vars[GB.V_PHASE], g.vars[GB.V_SLOT], g.vars[GB.V_LOCK] = 2.0, 2.0, 2.0
        tr = run(path, g, detect=True)
        hold = [t for t in tr if t[4] == 8.0]
        check('the detection box catches %s: the hold on the ground (into Damage 0x%X), its controller off, no stage '
              'collision%s' % (name, B.HOLD_STATUS, ', gf_tick stops holding it' if gf else ''),
              (phases_of(tr)[:2], v.get('status_log', [None])[0], hold[2][6].get('input'), hold[2][6].get('ground'))
              + ((g.vars.get(GB.V_PHASE), ) if gf else ()),
              ([1.0, 8.0], B.HOLD_STATUS, 1.0, 0.0) + ((0.0, ) if gf else ()))
    # 6. v3 (user: "make the Core Breaker dive continue until either landing or something (unless KOd)"): off the
    # stage (no ground) the dive goes on: no frame limit, no floor, the motion's dive loop looped, the same speed
    g = Game(x=0.0, y=-30.0, stage=(1000.0, 1001.0))
    r1, tr = both(path, g, frames=400)
    dive = [t for t in tr if t[4] == 2.0]
    steps = [math.hypot(b[2] - a[2], b[3] - a[3]) for a, b in zip(dive[1:], dive[2:])]
    check('off the stage: still diving after %d frames (%.0f down: past any bottom blast zone), at %.2f a frame, '
          'armor on, the air cap lifted' % (len(dive), dive[0][3] - dive[-1][3], B.DIVE_V),
          (g.status, len(dive) >= 330, dive[0][3] - dive[-1][3] > 1500.0, all(near(x, B.DIVE_V, 0.01) for x in steps),
           armor_at(g, dive[-1][7]), 0x20000044 in g.flags), (None, True, True, True, 1, True))
    fr = [t[1] for t in dive[1:]]
    check('the endless dive: the motion stays in the dive (%d-%d), looped back by %d (%d times)'
          % (B.DIVE_FROM, B.DIVE_LAST, B.DIVE_LOOP, len(g.frame_sets)),
          (min(fr) >= B.DIVE_FROM, max(fr) <= B.DIVE_LAST + 1e-6, len(g.frame_sets) >= 10,
           all(near(b - a, -B.DIVE_LOOP, 1e-3) for a, b in [(B.DIVE_LAST, f) for _n, f in g.frame_sets])),
          (True, True, True, True))
    # 6b. landing far below the height he started at: the dive goes on to it (v2 stopped it at the rise's start)
    g = Game(x=0.0, y=0.0, stage=(-1000.0, 1000.0), floor=-400.0)
    r1, tr = both(path, g)
    land = next(t for t in tr if t[4] == 5.0)
    check('landing 400 below the rise\'s start: the dive goes on to it, the miss\'s landing, Wait',
          (phases_of(tr), round(land[3], 3), g.status), ([1.0, 2.0, 5.0], -400.0, 0))
    # 6c. a wall ahead: the dive stops there (FallSpecial, no speed into the wall)
    g = Game(x=0.0, y=0.0, stage=(1000.0, 1001.0), wall=(60.0, 1000.0))
    r1, tr = both(path, g)
    check('a wall ahead: the dive stops at it, FallSpecial (0x10), still against it, no armor, the air cap back',
          (g.status, max(t[2] for t in tr) <= 60.0, g.vx, armor_at(g, 10 ** 6), 0x20000044 in g.flags),
          (0x10, True, 0.0, 0, False))
    g = Game(x=0.0, y=0.0, face=-1.0, stage=(1000.0, 1001.0), wall=(60.0, 1000.0))
    r1, tr = both(path, g)
    check('a wall behind him (facing away): no stop (still diving)', (g.status, phases_of(tr)), (None, [1.0, 2.0]))
    # 7. the B-reverse in the hover
    g = Game(stage=(-1000.0, 1000.0))
    run(path, g, frames=B.HOVER_FROM + 3)
    g.stick_back = g.t + 5
    tr = run(path, g)
    dive = [t for t in tr if t[4] == 2.0]
    check('the hover: the stick back turns him (the dive goes the other way)', dive[2][2] < dive[1][2], True)
    # 8. light homing (the second up special's dive)
    for name, want in (('ahead / below, 6 degrees steeper', 'steeper'), ('above him', 'none'), ('behind him', 'none'),
                       ('far below the line (out of the cone)', 'none')):
        g = Game(stage=(-1000.0, 1000.0), victim={'x': 30.0, 'y': -40.0, 'status': 0})
        run(path, g, frames=B.HOVER_FROM + 3)
        g.frame, g.rate, g.status = 0.0, 1.0, None
        vm = vm_for(path, g)
        vm.g[24] = 0
        vm.call(vm.func(FUNC_MAIN))
        angs = []
        for n in range(B.DIVE_FROM + 12):
            g.n = g.t
            g.t += 1
            vm.g[18] = 2 if g.air else 0
            if g.vars.get(B.CB_VAR) == 2.0:
                if want == 'steeper' or name.startswith('far'):
                    a = math.radians(B.DIVE_DEG + (6.0 if want == 'steeper' else 40.0))
                    g.victim['x'], g.victim['y'] = g.x + 30.0 * math.cos(a) * g.face, g.y - 30.0 * math.sin(a)
                elif name == 'above him':
                    g.victim['x'], g.victim['y'] = g.x + 30.0 * g.face, g.y + 10.0
                else:
                    g.victim['x'], g.victim['y'] = g.x - 30.0 * g.face, g.y - 10.0
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
    # 9. v3 (user: "if a grounded opponent is hit by Core Breaker, Supamario and the opponent should do the grounded
    # part of the animation instead of being dragged up"): a victim on the ground: the hold on the ground, the crash
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    r1, tr = both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4)
    check('a grounded victim: the hold on the ground, then the crash (no lift, no drive)', phases_of(tr),
          [1.0, 2.0, 8.0, 6.0])
    hg = [t for t in tr if t[4] == 8.0]
    late = hg[len(hg) // 2]
    check('the hold on the ground: he comes down and lands, the victim on the ground at his fist (%.0f ahead), its '
          'controller off, no stage collision, held every frame, the motion through hold_gnd (%d-%d)'
          % (B.HOLD_X, B.HOLDG, B.HOLDG_END),
          (late[5], round(late[3], 3), late[6].get('offx'), round(late[6]['y'], 3), late[6].get('input'),
           late[6].get('ground'), all(t[7] in t[6].get('held', []) for t in hg[1:]),
           min(t[1] for t in hg[1:]) >= B.HOLDG, max(t[1] for t in hg) <= B.HOLDG_END + 1e-6),
          (False, 0.0, B.HOLD_X, 0.0, 1.0, 0.0, True, True, True))
    check('the hold on the ground: never above where it started (no lift)', max(t[3] for t in hg) <= hg[0][3] + 1e-6,
          True)
    crash = [t for t in tr if t[4] == 6.0]
    rel = next(t for t in crash if t[6].get('ground') == 5.0)
    check('the crash: the victim let go (stage collision 5, controller on) at the crash\'s first frame (%d, the '
          'explosion hit the next), no gf_tick put-down; Wait at the end'
          % B.CRASH, (int(round(rel[1])), rel[6].get('input'), g.vars.get(GB.V_PHASE, 0.0), tr[-1][5], g.status),
          (B.CRASH, 0.0, 0.0, False, 0))
    check('the crash: the explosion sound',
          any(s_[1] == 'play' and s_[2] == B.SE_IDS['cb_explosion'] for s_ in g.sounds), True)
    # 9a. v4 (user: "The catch doesn't happen anymore on the dive unless the point-blank detection box is hit"): the
    # dive itself catches a fighter standing in its way, far from the detection box (the MSC: the hit, its slot)
    def on_path(extra=None):
        v = dict({'x': 0.0, 'y': 0.0, 'status': 0x47}, **(extra or {}))
        g = Game(stage=(-200.0, 200.0), victim=v)
        run(path, g, frames=B.HOVER_FROM + 3)
        v['x'] = g.x + g.face * (g.y / math.tan(math.radians(B.DIVE_DEG)) - 2.0)
        far = math.hypot(v['x'] - (g.x + B.DETECT_AT[0] * g.face), v['y'] + 5.0 - (g.y + B.DETECT_AT[1]))
        return g, v, far, run(path, g, victim_reach=B.HB['catch'][1] + 4.0)
    g, v, far, tr = on_path()
    dv = [t for t in tr if t[4] == 2.0]
    check('the dive catches a fighter standing in its way (%d frames into it, far from the detection box): its slot '
          '(2), the hitboxes cleared, invincible %d frames, the hold on the ground, the crash' % (len(dv), B.INVINCIBLE),
          (len(dv) > 3 and far > 30.0, g.vars.get(B.CB_V_SLOT), len(g.cleared) > 0, g.inv_log[0][1],
           phases_of(tr)), (True, 2.0, True, float(B.INVINCIBLE), [1.0, 2.0, 8.0, 6.0]))
    # v4 (user: "make it so that there's no armor during the leap or hover, and the dive has armor instead of
    # invincibility"; then "He should keep invincibility during the hold only"): the hover nothing, the dive super armor
    # and not invincible, the hold invincible (written at the catch, not before), no armor there
    arm = {ph: sorted({armor_at(g, t[7]) for t in tr if t[4] == ph}) for ph in (1.0, 2.0, 8.0, 6.0)}
    check('armor / invincibility: the hover none, the dive super armor (invincibility only written at the catch), the '
          'hold / crash invincible without armor', (arm, [v_ for _n, v_ in g.inv_log] == [float(B.INVINCIBLE), 0.0] and g.inv_log[0][0] > dv[0][7]),
          ({1.0: [0], 2.0: [1], 8.0: [0], 6.0: [0]}, True))
    for name, extra in (('lying down (DownWait)', {'status': 0x50}), ('invincible', {'body': 1})):
        g, v, far, tr = on_path(extra)
        check('the dive refuses a fighter %s: no catch, the hitboxes gone, it dives on and lands' % name,
              (phases_of(tr), len(g.cleared) > 0), ([1.0, 2.0, 5.0], True))
    # 9c. v5 (user: "There are cases where it will hit an opponent but they won't be put in the hold"): point-blank,
    # the dive's hitboxes connect on its very first frame (v4 reset the hit flag in the MSC after that hit): caught
    v = {'x': 0.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    run(path, g, frames=B.HOVER_FROM + 3)
    v['x'], v['y'] = g.x + 6.3 * g.face, g.y - 2.0
    tr = run(path, g, hit_at_dive=True)
    check('point-blank: a hit on the dive\'s first frame catches (v4: no hold)', (phases_of(tr)[:3],
                                                                                   g.vars.get(B.CB_V_SLOT)),
          ([1.0, 2.0, 3.0], 2.0))
    # 9d. v5 (user: "When catching an opponent on the ground, the move plays the animation as if it was in the air"):
    # a fighter standing on the ground whose situation already reads the air when the catch is read: the hold on the
    # ground (the frame before the hit decides), as the detection box's catch
    g, v, far, tr = on_path({'sit_after_hit': 2})
    check('a fighter on the ground, airborne by the time the catch is read: the hold on the ground, the crash',
          phases_of(tr), [1.0, 2.0, 8.0, 6.0])
    # 9e. v5 (user: "Sometimes after finishing the move, Supamario will keep the grey invincibility flashing"): the
    # hold's invincibility ends with the move, every way it ends
    ends = []
    g, v, far, tr = on_path()
    ends.append(('the crash (Wait)', g.status, [x for _n, x in g.inv_log][-1:]))
    v = {'x': 30.0, 'y': -40.0, 'status': 0x47}
    g = Game(x=0.0, y=0.0, stage=(-1000.0, -900.0), victim=v)
    g.air = True
    both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4)
    ends.append(('the explosion in the air (FallSpecial)', g.status, [x for _n, x in g.inv_log][-1:]))
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4, cut_at=B.DIVE_FROM - B.HOVER_FROM + 20)
    ends.append(('cut mid-hold', g.status, [x for _n, x in g.inv_log][-1:]))
    g = Game()
    run(path, g)
    ends.append(('no catch (the rise alone: nothing set, nothing cleared)', g.status, g.inv_log))
    check('the hold\'s invincibility cleared (INVINCIBLE 0) at every end; nothing written without a catch', ends,
          [('the crash (Wait)', 0, [0.0]), ('the explosion in the air (FallSpecial)', 0x10, [0.0]),
           ('cut mid-hold', 'cut', [0.0]), ('no catch (the rise alone: nothing set, nothing cleared)', 0xE, [])])
    # 9f. v6 (user: "Hitting the dive on a grounded/near ground opponent should work the same, using the same final hit
    # and leaving Supamario in the grounded finisher animation"; the clip: a dive catch on Donkey Kong standing took
    # the hold on the ground, then the weaker air explosion: he stopped just above the floor and never landed)
    def dive_at(h, jump=None, extra=None):
        """a victim in the dive's line at height h (its feet); jump: (height, from the dive's frame) it jumps to"""
        v = dict({'x': 0.0, 'y': 0.0, 'status': 0x47}, **(extra or {}))
        g = Game(stage=(-300.0, 300.0), victim=v)
        run(path, g, frames=B.HOVER_FROM + 3)
        a = math.radians(B.DIVE_DEG)
        hh = jump[0] if jump else h
        t = (g.y - hh - 1.9) / math.sin(a)
        v['x'] = g.x + g.face * (t * math.cos(a) + 6.3)
        v['y'] = h

        def move(g_, v_):
            if jump and g_.frame >= B.DIVE_FROM - 1e-6:
                v_['y'] = jump[0]
        tr = run(path, g, victim_reach=8.0, victim_move=move)
        return g, v, tr
    crash_frames = lambda tr: [t[1] for t in tr if t[4] == 6.0 and t[1] >= B.CRASH - 1e-6]      # noqa: E731
    # the point-blank catch (the detection box, a fighter in the air at his middle): the air hold, the drive, the crash
    v = {'x': 1.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    run(path, g, frames=B.HOVER_FROM + 3)
    v['x'], v['y'] = g.x + B.DETECT_AT[0] * g.face, g.y + B.DETECT_AT[1] - 5.0
    pb = run(path, g, detect=True)
    pb_end = (pb[-1][4], g.status, pb[-1][5])
    out = []
    for name, h, jump, extra, want in (
            ('standing', 0.0, None, None, [1.0, 2.0, 8.0, 6.0]),
            ('standing, its height read 0.5 above the floor (v5 never landed)', 0.5, None, {'sit': 0},
             [1.0, 2.0, 8.0, 6.0]),
            ('just jumped, 10 up', 0.0, (10.0,), None, [1.0, 2.0, 8.0, 6.0]),
            ('jumped high, 40 up', 0.0, (40.0,), None, [1.0, 2.0, 3.0, 4.0, 6.0])):
        g, v, tr = dive_at(h, jump, extra)
        hold = [t for t in tr if t[4] == 8.0]
        out.append((name, phases_of(tr), (tr[-1][4], g.status, tr[-1][5]) == pb_end,
                    crash_frames(tr) == crash_frames(pb), (not hold[-1][5]) if hold else None,
                    round(hold[-1][6]['y'], 3) if hold else None))
    check('dive catches: standing and near the ground (<= %.0f above where it stood) take the hold on the ground, he '
          'lands, the victim on its ground, then the crash with the point-blank catch\'s final hit and end pose (the '
          'crash phase, its frames, Wait on the ground); high: the air hold, the drive, the same crash'
          % B.NEAR_GROUND, out,
          [('standing', [1.0, 2.0, 8.0, 6.0], True, True, True, 0.0),
           ('standing, its height read 0.5 above the floor (v5 never landed)', [1.0, 2.0, 8.0, 6.0], True, True, True,
            0.5),
           ('just jumped, 10 up', [1.0, 2.0, 8.0, 6.0], True, True, True, 0.0),
           ('jumped high, 40 up', [1.0, 2.0, 3.0, 4.0, 6.0], True, True, None, None)])
    # 9g. v6 (user: "make Supamario take 7% in damage during the hold multihits for all versions of Core Breaker"): his
    # percent +1.75 on each burn hit's frame, +7 in all, on every catch path
    paths = []
    g, v, tr = dive_at(0.0)
    paths.append(('the dive, a standing fighter (the hold on the ground)', g, tr, 8.0, B.HOLDG))
    g, v, tr = dive_at(0.0, (40.0,))
    paths.append(('the dive, a high one (the air hold, the drive, the crash)', g, tr, 3.0, B.HOLD))
    v = {'x': 30.0, 'y': -40.0, 'status': 0x47}
    g = Game(x=0.0, y=0.0, stage=(-1000.0, -900.0), victim=v)
    g.air = True
    r1, tr = both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4)
    paths.append(('off the stage (the explosion in the air)', g, tr, 3.0, B.HOLD))
    v = {'x': 1.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    run(path, g, frames=B.HOVER_FROM + 3)
    v['x'], v['y'] = g.x + B.DETECT_AT[0] * g.face, g.y + B.DETECT_AT[1] - 5.0
    tr = run(path, g, detect=True)
    paths.append(('the point-blank catch', g, tr, 3.0, B.HOLD))
    out, want = [], []
    for name, g, tr, ph, seg in paths:
        at = {t[7]: t[1] for t in tr}
        steps = [(round(at.get(n_, -1) - seg), round(val, 3)) for n_, val in g.dmg_log]
        out.append((name, steps))
        want.append((name, [(f - B.HOLD, round(B.BURN_SELF * (k + 1), 3)) for k, f in enumerate(B.BURN_AT)]))
    check('his own %.2f%% on each burn hit\'s frame (+%g in all), every catch path' % (B.BURN_SELF,
                                                                                    B.BURN_SELF * B.BURN_HITS),
          out, want)
    # 9b. a victim in the air over the stage: the hold, the lift, the drive, the crash
    v = {'x': 30.0, 'y': 20.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    r1, tr = both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4)
    check('an airborne victim on the stage: the phases (the hold, the drive, the crash)', phases_of(tr),
          [1.0, 2.0, 3.0, 4.0, 6.0])
    hold = [t for t in tr if t[4] == 3.0]
    mid = hold[len(hold) // 2][6]
    check('the hold: the victim at his fist (offsets %.0f, %.0f), its controller off, no stage collision'
          % (B.HOLD_X, B.HOLD_Y), (mid.get('offx'), round(mid['y'] - hold[len(hold) // 2][3], 3), mid.get('input'),
                                   mid.get('ground')), (B.HOLD_X, B.HOLD_Y, 1.0, 0.0))
    check('the hold and the drive: the victim held every frame',
          all(t[7] in t[6].get('held', []) for t in tr if t[4] in (3.0, 4.0)), True)
    check('the hold: he goes up %.0f' % B.HOLD_RISE, near(max(t[3] for t in hold) - hold[0][3], B.HOLD_RISE, 1.0),
          True)
    drive = [t for t in tr if t[4] == 4.0]
    da = math.degrees(math.atan2(-(drive[2][3] - drive[1][3]), drive[2][2] - drive[1][2]))
    check('the drive: down %.0f degrees' % B.DRIVE_DEG, near(da, B.DRIVE_DEG, 0.3), True)
    crash = [t for t in tr if t[4] == 6.0]
    rel = next(t for t in crash if t[6].get('ground') == 5.0)
    check('the crash (after the drive): on the ground, the victim let go at its first frame (%d), no put-down, Wait'
          % B.CRASH, (tr[-1][5], int(round(rel[1])), rel[6].get('input'), g.vars.get(GB.V_PHASE, 0.0), g.status),
          (False, B.CRASH, 0.0, 0.0, 0))
    # 10. a catch off the stage: the explosion in the air, the victim let go, FallSpecial
    v = {'x': 30.0, 'y': -40.0, 'status': 0x47}
    g = Game(x=0.0, y=0.0, stage=(-1000.0, -900.0), victim=v)
    g.air = True
    r1, tr = both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4)
    check('catch off the stage: the phases (explosion in the air)', phases_of(tr), [1.0, 2.0, 3.0, 4.0, 7.0])
    check('off the stage: the victim let go (stage collision 5, controller on), FallSpecial',
          (v.get('ground'), v.get('input'), g.status), (5.0, 0.0, 0x10))
    rel = [t for t in tr if t[4] == 7.0]
    check('off the stage: he stays where the explosion is', max(abs(t[3] - rel[0][3]) for t in rel) < 0.01, True)
    # 11. cut mid-hold: the victim let go at once
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    both(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4, cut_at=B.DIVE_FROM - B.HOVER_FROM + 20)
    check('cut mid-hold: the victim let go (stage collision 5, controller on), no armor',
          (v.get('ground'), v.get('input'), armor_at(g, 10 ** 6)), (5.0, 0.0, 0))
    # 12. an earlier God Fist victim (another slot, held down) is let go at the catch
    v = {'x': 30.0, 'y': 0.0, 'status': 0x47}
    g = Game(stage=(-200.0, 200.0), victim=v)
    run(path, g, frames=B.HOVER_FROM + 3)
    g.vars[GB.V_PHASE] = 2.0
    g.vars[GB.V_SLOT] = 3.0
    g.vars[GB.V_LOCK] = 3.0
    run(path, g, catch_at=B.DIVE_FROM - B.HOVER_FROM + 4, frames=B.DIVE_FROM - B.HOVER_FROM + 8)
    check('an earlier God Fist victim (slot 3) let go at the catch (its controller on, gf_phase 0)',
          (g.vars.get(0x0F000115 + 0x20 * 5), g.vars.get(GB.V_PHASE)), (0.0, 0.0))
    # 13. an air start: the rise, Fall
    g = Game(x=0.0, y=40.0, stage=(1000.0, 1001.0))
    tr = run(path, g, frames=200)
    check('an air start: the rise, Fall at its last frame, the rise used',
          (g.status, max(t[1] for t in tr), used(g)), (0xE, float(B.HOVER_FROM - 1), 1.0))


def ko_estimate(kb=None):
    """Smash 4's knockback for the explosion (CRASH_DMG): KB = ((p/10 + p d/20) 200/(w+100) 1.4 + 18) KBG/100 + BKB,
    p the percent after the hit, w the weight (Mario 98); ~120 off the stage near the ledge KOs on a mid-size stage"""
    kb = kb or B.EXPLOSION_KB
    out = []
    for start in range(0, 200, 5):
        p = start + B.CATCH_DMG + B.BURN_HITS * B.BURN_DMG + B.CRASH_DMG
        k = ((p / 10.0 + p * B.CRASH_DMG / 20.0) * 200.0 / 198.0 * 1.4 + 18.0) * kb['KBG'] / 100.0 + kb['BKB']
        out.append((start, round(k, 1)))
    return out


def ko_percent(kb, x0=9.0, side=240.0, top=200.0, grav=0.087, max_fall=1.5):
    """a rough KO percent (before the move) for a Mario-weight victim at x0 from a Final Destination-size stage's
    middle: launched at KB x 0.03 a frame along the angle, that speed less 0.051 a frame, its own gravity on top, KO
    past the side (240) or top (200) blast zone; no DI, no rage (an estimate, not the game)"""
    for start, k in ko_estimate(kb) + [(s, None) for s in range(200, 400, 5)]:
        if k is None:
            p = start + B.CATCH_DMG + B.BURN_HITS * B.BURN_DMG + B.CRASH_DMG
            k = ((p / 10.0 + p * B.CRASH_DMG / 20.0) * 200.0 / 198.0 * 1.4 + 18.0) * kb['KBG'] / 100.0 + kb['BKB']
        sp, a = k * 0.03, math.radians(kb['Angle'])
        x, y, vg = x0, 0.0, 0.0
        for _f in range(300):
            vg = max(vg - grav, -max_fall)
            x += sp * math.cos(a)
            y += sp * math.sin(a) + vg
            sp = max(0.0, sp - 0.051)
            if x > side or y > top:
                return start
    return None


def script_tests(fdir):
    f = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'game.bin'))
    s = f.script('specialhi')
    hits = [c for c in s if c.ident == acmd.BY_NAME['extra_special_hitbox']]
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    dmg = [c.params[syn.index('Damage')] for c in hits]
    catch = max(d for d in dmg if d <= B.CATCH_DMG + 1e-6 and d >= B.CATCH_DMG - 1e-6)
    big = [d for d in dmg if abs(d - B.CRASH_DMG) < 1e-6]
    # the burn hits by the frame they come out at: the hold (grab_hold) and v3's hold on the ground (hold_gnd)
    at, burn_at = 0.0, []
    for c in s:
        if c.ident == acmd.BY_NAME['frame']:
            at = c.params[0]
        if c.ident == acmd.BY_NAME['extra_special_hitbox'] and abs(c.params[syn.index('Damage')] - B.BURN_DMG) < 1e-6:
            burn_at.append(at)
    air = [f for f in burn_at if B.HOLD <= f <= B.HOLD_END]
    gnd = [f for f in burn_at if B.HOLDG <= f <= B.HOLDG_END]
    check('damage: catch %g + %d x %g + crash / explosion %g = 26, the same burn hits in the hold and the hold on the '
          'ground' % (B.CATCH_DMG, B.BURN_HITS, B.BURN_DMG, B.CRASH_DMG),
          (catch + len(air) * B.BURN_DMG + B.CRASH_DMG, catch + len(gnd) * B.BURN_DMG + B.CRASH_DMG, len(big),
           [f - B.HOLD for f in air] == [f - B.HOLDG for f in gnd], len(burn_at)), (26.0, 26.0, 2, True, 2 * B.BURN_HITS))
    # v4: the dive's catch is the MSC's: no Hit_Check or loop in the dive's frames; the hit flag and the Part 0 record
    # cleared before its hitboxes
    at, in_dive, order = 0.0, [], []
    for c in s:
        if c.ident == acmd.BY_NAME['frame']:
            at = c.params[0]
        nm = acmd.INFO[c.ident]['name']
        if B.DIVE_FROM < at < B.LAND:
            in_dive.append(nm)
        if at == B.DIVE_FROM and nm in ('Hit_Reset', 'Hit_Log_Clear', 'Extra_Special_Hitbox'):
            order.append(nm)
    check('the dive: no game-script catch checks (the MSC\'s cb_dive_catch); Hit_Reset, Hit_Log_Clear(0), then its '
          'hitboxes', (in_dive, order), ([], ['Hit_Reset', 'Hit_Log_Clear', 'Extra_Special_Hitbox',
                                             'Extra_Special_Hitbox']))
    # v5 (user: "Up special's leap has a hitbox and it persists until cancelled": v4 held the rise's pose and the game
    # script, on its own frame count, reached the dive's catch / body boxes at 60 with cb 0): every hitbox, and every
    # hover / dive effect call, inside a cb guard that cb 0 fails
    def unguarded(script, idents):
        out, stack, w = [], [], 0
        cmp_ = None
        for c in script:
            stack = [b for b in stack if b[0] > w]
            nm = acmd.INFO[c.ident]['name']
            if nm == 'Float_Var_Compare':
                cmp_ = c.params
            if nm == 'True':
                stack.append((w + c.params[0], cmp_))
            if c.ident in idents:
                ok0 = all(not (cm and cm[0] == B.CB_VAR) or
                          {0: 0.0 == cm[2], 1: 0.0 != cm[2], 2: 0.0 <= cm[2], 3: 0.0 >= cm[2]}.get(cm[1], True)
                          for _e, cm in stack)
                if ok0:
                    out.append((nm, w))
            w += acmd.INFO[c.ident]['size']
        return out
    eff = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'effect.bin')).script('specialhi')
    check('no hitbox the rise (cb 0) can reach, whatever frame the script gets to (v4: the dive\'s 3% catch / body '
          'boxes in the held rise)', unguarded(s, {acmd.BY_NAME['extra_special_hitbox']}), [])
    ext = [c for c in eff if c.ident == acmd.BY_NAME['external_graphic']]
    check('no Core Breaker (XV2) effect the rise (cb 0) can reach', (len(ext) > 10, unguarded(
        eff, {acmd.BY_NAME['external_graphic']})), (True, []))
    burns = [c for c in hits if abs(c.params[syn.index('Damage')] - B.BURN_DMG) < 1e-6]
    el = lambda c, n: c.params[syn.index(n)]      # noqa: E731
    check('the burn hits (both holds) the coin\'s (user: "make the catch multihits of the dive use the coin hit '
          'effect"): Element 6, SFX Coin 1 (4), level 1, as vanilla Super Jump Punch',
          sorted({(el(c, 'Effect'), el(c, 'SFXType'), el(c, 'SFXLevel')) for c in burns}), [(6, 4, 1)])
    crash = [c for c in hits if abs(c.params[syn.index('Size')] - B.HB['crash'][1]) < 1e-3][0]
    ex = [c for c in hits if abs(c.params[syn.index('Size')] - B.HB['explosion'][1]) < 1e-3][0]
    kbs = lambda c: tuple(c.params[syn.index(n)] for n in ('Angle', 'KBG', 'BKB'))      # noqa: E731
    check('the crash on the stage launches (v3): angle %d, KBG %d, BKB %d, at least the explosion in the air\'s'
          % kbs(crash), (kbs(crash), all(a >= b for a, b in zip(kbs(crash)[1:], kbs(ex)[1:])),
                         40 <= kbs(crash)[0] <= 45), ((B.CRASH_KB['Angle'], B.CRASH_KB['KBG'], B.CRASH_KB['BKB']),
                                                       True, True))
    szs = sorted({round(c.params[syn.index('Size')], 2) for c in hits})
    want = sorted({B.HB[k][1] for k in B.HB})
    check('hitbox sizes (v3: scaled with their effects; the detection box and the body box not): %s' % (
        ', '.join('%s %g -> %g' % (k, a, b) for k, (a, b) in B.HB.items())), szs, want)
    det = [c for c in hits if abs(c.params[syn.index('Size')] - B.DETECT_SIZE) < 1e-6]
    check('the detection box hits fighters lying down (Ground/Air 3, no bit 31)',
          [c.params[syn.index('Ground/Air')] for c in det], [3])
    air = f.script('specialairhi')
    check('specialairhi: the same script', [(c.ident, c.params) for c in air], [(c.ident, c.params) for c in s])
    for name, kb in (('the explosion in the air', B.EXPLOSION_KB), ('the crash on the stage', B.CRASH_KB)):
        est = ko_estimate(kb)
        print('     %s\'s knockback (Mario-weight, %% before the move -> KB): %s; KO from mid-stage (rough) at ~%s%%' % (
            name, ', '.join('%d%%: %g' % e for e in est[::4]), ko_percent(kb)))


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
    # v3: the orb a closed shell round him (front and back), every effect at x1.75 (no halving)
    import nud
    zs = np.concatenate([np.asarray(pp.pos)[:, 2] for mm in nud.read(os.path.join(orb, 'model.nud'))
                         for pp in mm.polygons])
    check('the charge orb: a closed shell (v2: flat discs)', (zs.min() < -1.0, zs.max() > 1.0), (True, True))
    syn_e = acmd.INFO[acmd.BY_NAME['external_graphic']]['syntax']
    orb_id = int(doc['models']['Cor_Crg.emo']['id'], 16)
    sizes = [dict(zip(syn_e, c.params))['Size'] for c in acmd.ACMDFile.load(os.path.join(
        fdir, 'script', 'animcmd', 'body', 'effect.bin')).script('specialhi') if c.ident == acmd.BY_NAME[
        'external_graphic'] and c.params[0] == orb_id]
    check('every effect at Core Breaker\'s x%.2f (above the God Fist\'s %.2f), v4: all but the aura x%.1f over it: the '
          'orb\'s call %.2f (XV2 2.8 x %.2f x %.1f)' % (CF.CB_FX_SCALE, FX.SIZE, B.FX_MUL, sizes[0], CF.CB_FX_SCALE,
                                                        B.FX_MUL),
          (sorted(B.SIZE_MUL), set(B.SIZE_MUL.values()), B.CMN_MUL, round(sizes[0], 3), CF.CB_FX_SCALE > FX.SIZE),
          ([0, 1, 2, 3, 7], {B.FX_MUL}, 1.0, round(2.8 * CF.CB_FX_SCALE * B.FX_MUL, 3), True))
    # v5 (user: "The ending effects (aside from the explosion) are far too large"): the hit / hit loop, the miss blast,
    # the flare and the common dust / clouds / smoke / sparks at v3's size; the explosion and the dive's at v4's
    syn_e2 = acmd.INFO[acmd.BY_NAME['graphic_effect']]['syntax']
    eff = acmd.ACMDFile.load(os.path.join(fdir, 'script', 'animcmd', 'body', 'effect.bin')).script('specialhi')
    by_id = {}
    for e in doc['effects']:
        for pt in e['parts']:
            for st in pt.get('ptcl') or []:
                by_id.setdefault(int(st['id'], 16), set()).add((e['bac_effect'], round(pt['size'], 4)))
    bad = []
    for c in eff:
        if c.ident == acmd.BY_NAME['external_graphic']:
            d = dict(zip(syn_e, c.params))
            for eid, sz in by_id.get(d['Graphic'] if 'Graphic' in d else c.params[0], ()):
                want_sz = sz * B.SIZE_MUL.get(eid, 1.0)
                if eid in (8, 9, 12) and abs(d['Size'] - sz) > 1e-3 and abs(d['Size'] - want_sz) > 1e-3:
                    bad.append((eid, d['Size'], sz))
        if c.ident == acmd.BY_NAME['graphic_effect']:
            d = dict(zip(syn_e2, c.params))
            if d['Size'] > 1.25:
                bad.append(('common', d['Size']))
    check('v5: the ending effects (the hit and its loop, the miss blast, the flare, the common clouds / smoke / '
          'sparks) at v3\'s sizes; the explosion at v4\'s', bad, [])
    calls = []
    for e in doc['effects']:
        for pt in e['parts']:
            if 'size' in pt:
                calls.append(abs(pt['size'] - pt['xv2_scale'] * CF.CB_FX_SCALE) < 1e-3)
    check('every placement at CB_FX_SCALE', all(calls), True)
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
