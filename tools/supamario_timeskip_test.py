#!/usr/bin/env python3
"""Time Skip (Supamario's side special) offline checks: the compiled MSC (ts_* through the side special's status
functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built scripts, motions,
effects and sounds.

  python3 -I tools/supamario_timeskip_test.py BUILD_OUT_DIR SLEDGEHAMMER_OUT_DIR

BUILD_OUT_DIR: tools/supamario_timeskip_build.py's OUT_DIR; SLEDGEHAMMER_OUT_DIR: the same inputs built by
tools/supamario_sledgehammer_build.py (the install before this move): every other script, motion, effect set and
sound of it is checked unchanged.

The model of the game (its assumptions):
- the status's main (func_2259) on its first frame, then ts_loop every frame (also in his hitstop); func_2280 at a
  status change (func_16); func_82's hooks every frame (sh_tick: the slots' status / damage records; ts_tick);
- each frame: his motion (rate 1; SpecialS stops at its last frame, SpecialAirS too) and the scripts' clock advance
  unless he is frozen in a hitstop; a motion change (MotionModule 1) restarts the clock at its start frame; holding the
  frame (MotionModule 0x2713) doesn't stop the clock (Core Breaker v4); then the scripts (the box at the clock's
  frame), the MSC, the collision;
- his speed: energy 3 (world X, KineticModule 0x11) moves him each frame he isn't frozen, on the ground (kinetic type 6)
  and in the air only while it is on (v2: KineticModule 0xB 3 since the last KineticModule(0, 0): FALL leaves it off, as
  the game: the Cape's air code turns it on itself); energy 2 (the air drift, world X) in the air; in the air energy 1's
  speed plus its acceleration (gravity 0.09 when on), a fall at most 1.5; a floor ends the air (the situation changes);
  v2: his position writes (0x0F000004 forward, 0x0F000005 up) move him at once; a floor only up to `edge` (along his
  facing) on the ground: past it he is in the air (ground correction 1: slides off);
- the connect box (bone 0 + (HIT_Z, HIT_Y), HIT_SIZE) hits a fighter whose body (its feet to 10 above, 3.5 wide) it
  touches, once a fighter (its Part 0 record): a shield (0x1C) sets the shield bit only; intangible (body >= 2): no
  contact; invincible (1) or countering: the hurtbox bit, no damage, no reaction; armor: its damage, no reaction;
  else 2%, both frozen CATCH_FREEZE, Damage (0x45 / 0x46). The strike (on SpecialAirS from STRIKE to STRIKE + 1) on
  the held victim: 14%, both frozen STRIKE_FREEZE, launched at 10 degrees (knockback x 0.03 a frame), DamageFly
  (0x47). Target 12's offsets read the fighter last hit.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import omo  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
import supamario_fakedeath_test as FT  # noqa: E402
import supamario_sledgehammer_test as SHT  # noqa: E402
import supamario_timeskip_anim as A  # noqa: E402
import supamario_timeskip_build as B  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


def near(name, got, want, tol):
    check('%s (%.2f, want %.2f +- %g)' % (name, got, want, tol), abs(got - want) <= tol, True)


LEN = {0x219: 96, 0x21D: 81}
GRAVITY, MAX_FALL = 0.09, 1.5
SIDE = 0x2000


class V(FT.Fighter):
    def __init__(self, slot, x, y=0.0, air=False, shield=False, face=-1.0, **kw):
        FT.Fighter.__init__(self, slot, x, y, air, shield, face)
        self.pct = 0.0
        self.input_off = False
        self.ground = []
        self.w = 3.5                 # its body's half width (v2: 1.5 for a slim hurtbox, the point-blank cases)
        for k, v in kw.items():
            setattr(self, k, v)


class Game(SHT.Game):
    def __init__(self, fighters=(), held=None, air=False, y=0.0, stick_x=None, floor=None, edge=None, boxes=(0, 1)):
        SHT.Game.__init__(self, fighters=fighters, held=held, y=y)
        self.air = air
        self.floor = floor if floor is not None else (None if air else y)
        self.edge = edge             # v2: the floor ends this far along his facing (None: no end)
        self.boxes = boxes           # v2: the detection boxes the script makes (v1: (0,))
        self.e3 = not air            # v2: energy 3 on (the ground's kinetic type; off in FALL until KineticModule 0xB 3)
        self.vx2 = 0.0               # v2: energy 2 (the air drift)
        self.pdx = self.pdy = 0.0    # v2: this frame's position writes (world)
        self.moves = []              # v2: (n, forward, up) position writes
        self.correct = []            # v2: (n, GroundModule 0x2710 value)
        self.sit_fn = None           # v2: n -> a situation to report (a ledge: 1)
        self.acc = 0.0 if not air else -GRAVITY
        self.vx = 0.0
        self.stick_x = stick_x
        self.clock = 0.0
        self.fired = set()
        self.box = None              # 'catch' / 'strike'
        self.inv = []                # (n, frames) INVINCIBLE writes
        self.holds = []              # (n, slot offset x) the hold's writes
        self.removed = []            # n of AttackModule 0x2719
        self.statuses = []
        self.vlim = MAX_FALL         # energy 1's limit (KineticModule 0x14)
        self.vlims = []
        self.vel = []                # (n, vx, vy) each frame he moves

    def fvar(self, v):
        if v == 0x0F000043:
            return 1.0 if self.hitstop > 0 else 0.0
        if v == 0x0F0000A2:
            return float(B.ST_SIDE) if self.status is None else float(self.status if self.status != 'cut' else 0)
        return SHT.Game.fvar(self, v)

    def setvar(self, v, val):
        if v == 0x0F00011C:
            self.inv.append((self.n, val))
            return
        if v == 0x0F000004:                             # v2: move self forward
            self.x += self.face * val
            self.pdx += self.face * val
            self.moves.append((self.n, round(val, 4), 0.0))
            return
        if v == 0x0F000005:                             # v2: move self up
            self.y += val
            self.pdy += val
            self.moves.append((self.n, 0.0, round(val, 4)))
            return
        for s_ in range(1, 9):
            t_ = s_ + 2
            f_ = self.fighters.get(s_)
            if f_ is None:
                continue
            if v == 0x0F000045 + 8 * t_:
                f_.x = self.x + self.face * val
                self.holds.append((self.n, s_, round(val, 3)))
                return
            if v == 0x0F000046 + 8 * t_:
                f_.y = self.y + val
                return
            if v == 0x0F000044 + 8 * t_:
                f_.hitstop = max(f_.hitstop, int(val))
                return
            if v == 0x0F0000A6 + 8 * t_:
                f_.ground.append((self.n, val))
                return
            if v == 0x0F0000A7 + 8 * t_ and val >= 1000.0:     # a held shieldstun (cb_shield_tick / ts_shield)
                f_.shieldstun = int(val - 1000.0)
                f_.__dict__.setdefault('pushes', []).append((self.n, int(val - 1000.0)))
                return
        SHT.Game.setvar(self, v, val)

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0xA:                                  # MathF (sqrt)
            if a[0] == 0:
                return R.f2i(math.sqrt(max(0.0, f(a[1]))))
            return 0
        if sid == 0x10 and a and a[0] == 0x14 and a[1] == 1:
            self.vlim = f(a[2])
            self.vlims.append((self.n, round(self.vlim, 4)))
            return 0
        if sid == 0x18 and a and a[0] == 0x2:           # the situation set (func_20)
            self.air = a[1] == 2
            return 0
        if sid == 0x10 and a and a[0] == 0x11 and a[1] == 3:
            self.vx = f(a[2])
            return 0
        if sid == 0x10 and a and a[0] == 0x11 and a[1] == 2:
            self.vx2 = f(a[2])
            return 0
        if sid == 0x10 and a and a[0] == 0xB and len(a) == 2 and a[1] == 3:
            self.e3 = True
            return 0
        if sid == 0x10 and a and a[0] == 0 and len(a) == 2:   # a kinetic type: 0 FALL (energy 3 off), 6 ground
            self.e3 = a[1] != 0
            if a[1] == 0:
                self.acc = -GRAVITY
            return 0
        if sid == 0x1A and a and a[0] == 0x2710:          # v2: GroundModule's correction
            self.correct.append((self.n, a[1]))
            return 0
        if sid == 0x12 and a and a[0] == 0x1:
            self.kind, self.frame = a[1], f(a[2])
            self.motions.append((self.n, a[1], f(a[2])))
            self.clock = f(a[2])
            self.fired = set()
            self.rate = 1.0
            return 0
        if sid == 0x12 and a and a[0] == 0x2713:
            self.frame = f(a[1])
            self.motions.append((self.n, 'set', f(a[1])))
            return 0
        if sid == 0x12 and a == [0x2712]:
            return 1 if self.kind in LEN and self.frame >= LEN[self.kind] - 1 else 0
        if sid == 0x2E and a and a[0] == 0x2724:
            self.hitflag = 0
            return 0
        if sid == 0x2E and a and a[0] == 0x2719:
            self.box = None
            self.removed.append(self.n)
            return 0
        if sid == 0x18 and a and a[0] == 0x3:
            self.status = a[1]
            self.statuses.append((self.n, a[1]))
            return 0
        return SHT.Game.sys(self, sid, a)

    def scripts(self):
        """the game scripts at the clock's frame (once each per motion)"""
        if self.kind == 0x219 and self.clock >= B.HIT_FROM - 1e-6 and 'catch' not in self.fired:
            self.fired.add('catch')
            if self.vars.get(B.V_PH, 0.0) > 2.5:
                self.box = 'catch'
        if self.kind == 0x21D and self.clock >= B.STRIKE - 1e-6 and 'strike' not in self.fired:
            self.fired.add('strike')
            self.box = 'strike'
        if self.kind == 0x21D and self.clock >= B.STRIKE + 2 - 1e-6 and 'off' not in self.fired:
            self.fired.add('off')
            self.box = None

    def collide(self):
        if self.box is None or self.hitstop > 0:
            return
        if self.box == 'catch':
            spheres = [(self.x + self.face * z, self.y + y, r) for i, (z, y, r) in
                       enumerate(((B.HIT_Z, B.HIT_Y, B.HIT_SIZE), (B.HIT2_Z, B.HIT2_Y, B.HIT2_SIZE))) if i in self.boxes]
        else:
            spheres = [(self.x + self.face * B.STRIKE_Z, self.y + B.STRIKE_Y, B.STRIKE_SIZE)]
        for v in self.fighters.values():
            if getattr(v, 'rec', None) == self.box:
                continue

            def touch(hx, hy, r):
                dx = max(0.0, abs(v.x - hx) - getattr(v, 'w', 3.5))
                dy = max(0.0, max(v.y - hy, hy - (v.y + 10.0)))
                return dx * dx + dy * dy <= r * r
            if not any(touch(*sp) for sp in spheres):
                continue
            if getattr(v, 'body', 0) >= 2:
                continue
            v.rec = self.box
            unblock = self.box == 'strike' and self.vars.get(B.V_CHG, 0.0) > B.FULL
            if v.status in (0x1C, 0x1E) and not unblock:
                self.hitflag |= 4
                self.hit = v
                stop = B.CATCH_FREEZE if self.box == 'catch' else B.STRIKE_FREEZE
                v.hitstop, self.hitstop = stop, stop
                v.shield_hits = getattr(v, 'shield_hits', []) + [(self.n, self.box)]
                if self.box == 'strike':
                    v.status = 0x1E
                return
            self.hit = v
            self.hitflag |= 2
            v.hit_at = self.n
            hit, stop = (B.CATCH, B.CATCH_FREEZE) if self.box == 'catch' else (B.STRIKE_HIT, B.STRIKE_FREEZE)
            if self.box == 'strike' and unblock and self.vars.get(B.V_SHV, 0.0) > 0.5:
                hit = dict(hit, Damage=hit['Damage'] + B.SH_BONUS)
            if getattr(v, 'body', 0) == 1 or getattr(v, 'counter', False):
                self.hitstop = stop
                return
            v.pct += hit['Damage']
            v.hitstop = stop
            self.hitstop = stop
            if getattr(v, 'armor', 0):
                return
            kb = B.knockback(hit, v.pct)
            v.hitstun = int(kb * 0.4)
            if self.box == 'catch':
                v.pending = 0x57 if 0x4D <= v.status <= 0x53 else (0x46 if v.air else 0x45)   # lying: DownDamage
            else:
                a = math.radians(hit['Angle'])
                v.vx, v.vy = kb * 0.03 * math.cos(a) * self.face, kb * 0.03 * math.sin(a)
                v.pending = 0x47
                v.air = True
                v.launch = kb
            return

    def on_floor(self):
        return self.floor is not None and (self.edge is None or (self.x - 0.0) * self.face <= self.edge)

    def physics(self):
        pdx, pdy = self.pdx, self.pdy
        self.pdx = self.pdy = 0.0
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        ex = (self.vx if (self.e3 or not self.air) else 0.0) + (self.vx2 if self.air else 0.0)
        self.x += ex
        if not self.air and not self.on_floor():        # v2: slid off the edge (correction 1)
            self.air = True
            self.vy = 0.0
        if self.air:
            self.vy += self.acc
            if self.vy < -self.vlim:
                self.vy = -self.vlim
            self.y += self.vy
            self.vel.append((self.n, (ex + pdx) * self.face, self.vy + pdy))
            if self.on_floor() and self.y <= self.floor:
                self.y, self.air, self.vy = self.floor, False, 0.0
                self.e3 = True
                self.event('me', 2)                     # the landing's variable reset
        else:
            self.vel.append((self.n, (ex + pdx) * self.face, pdy))
        self.frame += self.rate
        self.clock += self.rate
        if self.kind in LEN and self.frame > LEN[self.kind] - 1:
            self.frame = float(LEN[self.kind] - 1)


def fn(vm, name):
    return vm.func(FT.func_index(vm, name))


def run(path, g, frames=260, cut_at=None, after=0, tick=None):
    vm = FT.vm_for(path, g)
    tr = []
    prev_sit = 2 if g.air else 0
    end = None
    for k in range(frames + after):
        g.n = k
        if end is not None:
            vm.g[18] = 2 if g.air else 0
            if tick:
                tick(g, k)
            if g.sit_fn and g.sit_fn(k) is not None:
                vm.g[18] = g.sit_fn(k)
            vm.call(fn(vm, 'sh_tick'))
            vm.call(fn(vm, 'cb_shield_tick'))
            vm.call(fn(vm, 'ts_tick'))
            for v in g.fighters.values():
                v.step(k)
            g.physics()
            continue
        if g.status is None and k > 0 and vm.g[18] == 2 and not g.air:
            pass
        sit = 2 if g.air else 0
        vm.g[18], vm.g[19] = sit, prev_sit
        prev_sit = sit
        if tick:
            tick(g, k)
        if g.sit_fn and g.sit_fn(k) is not None:
            vm.g[18] = g.sit_fn(k)
        g.scripts()
        if cut_at is not None and k == cut_at:
            g.status = 'cut'
        elif k == 0:
            vm.call(fn(vm, 'func_2259'))
        else:
            vm.call(fn(vm, 'ts_loop'))
        tr.append((k, g.kind, round(g.frame, 3), round(g.x, 3), round(g.y, 3), g.status,
                   g.vars.get(B.V_PH, 0.0)))
        vm.call(fn(vm, 'sh_tick'))
        vm.call(fn(vm, 'cb_shield_tick'))
        vm.call(fn(vm, 'ts_tick'))
        if g.status is not None:
            vm.call(fn(vm, 'func_2280'))
            g.box = None
            end = k
            if not after:
                break
            continue
        g.collide()
        for v in g.fighters.values():
            v.step(k)
        g.physics()
    return tr, vm


def first(tr, pred):
    return next((t for t in tr if pred(t)), None)


def ph_at(tr, k):
    return tr[k][6]


def speeds(g, a, b):
    """his speed's size on game frames a..b (the frames he moved)"""
    return [round(math.hypot(vx, vy), 3) for n, vx, vy in g.vel if a <= n <= b]


def msc_tests(path, root):
    mf, mn = B.MOVE_FROM, B.MOVE_N
    # 1. a tap on the ground: the dash and the stop, no victim
    g = Game()
    tr, vm = run(path, g)
    end = tr[-1]
    check('ground tap: SpecialS from frame 0, never restarted (no charge held)', [m for m in g.motions if m[1] != 'set'],
          [(0, 0x219, 0.0)])
    check('ground tap: the dash at frame %d (phase 3), the stop (4) at %d, Wait (0) at %d' % (
        B.WIND_END, mf + mn, B.DASH_END), (ph_at(tr, B.WIND_END), ph_at(tr, mf + mn), end[0], end[5]),
          (3.0, 4.0, B.DASH_END, 0))
    check('ground tap: the detection box out at %d (the script, phase 3), taken off at %d (2 before the moving part '
          'ends)' % (B.HIT_FROM, mf + mn - 2), ('catch' in g.fired, g.removed[0] if g.removed else None),
          (True, mf + mn - 2))
    sp = speeds(g, mf, mf + mn - 1)
    ease = [round(B.VMIN + (B.VSTOP - B.VMIN) * (k - (mn - B.MOVE_EASE - 1)) / B.MOVE_EASE, 3)
            for k in range(mn - B.MOVE_EASE, mn)]
    check('ground tap: the moving part %d-%d at %.2f a frame (uncharged), eased to %.2f over its last %d frames' % (
        mf, mf + mn - 1, B.VMIN, B.VSTOP, B.MOVE_EASE), sp, [B.VMIN] * (mn - B.MOVE_EASE) + ease)
    near('ground tap: his travel (the wind-up\'s step, the moving part, the stop\'s slide)', end[3], B.travel(0, root), 0.3)
    check('ground tap: Hazure (the whiff) once, at the moving part\'s end (%d)' % (mf + mn),
          [(n, s_) for n, w, s_ in g.sounds if w == 'play'], [(mf + mn, B.SE_IDS['ts_hazure'])])
    check('ground tap: no invincibility, the air use not taken', (g.inv, g.vars.get(B.V_USED, 0.0)), ([], 0.0))
    fwd = sorted({n for n, a_, u_ in g.moves if a_ > 0 and mf <= n < mf + mn})
    check('v2 ground tap: the travel is his position (one forward write a moving frame), his energy 3 held at 0, the '
          'ground correction 1 (slides off edges) every frame', (fwd == list(range(mf, mf + mn)), round(g.vx, 6),
                                                                  sorted({c for _n, c in g.correct})), (True, 0.0, [1]))
    sp_ground = sp
    # 2. in the air: no gravity, Fall at the moving part's end, the use taken, the gravity eased back in
    g = Game(air=True, y=200.0, floor=-1e4)
    tr, vm = run(path, g, after=40)
    k_end = max(t[0] for t in tr if t[5] is None) + 1
    check('air tap: Fall (0xE, not FallSpecial) at the moving part\'s end (%d)' % (mf + mn),
          (tr[-1][0], g.statuses[:1]), (mf + mn, [(mf + mn, 0xE)]))
    check('air tap: his height kept through the move (no gravity, no drift)',
          max(abs(t[4] - 200.0) for t in tr if t[0] < k_end), 0.0)
    near('air tap: his travel (no stop: Fall)', tr[-1][3], B.travel(0, root, True), 0.3)
    check('v2 (user: "Doesn\'t move anywhere in the air"): the air dash moves exactly as the ground one (the moving '
          'part\'s speeds frame by frame)', speeds(g, mf, mf + mn - 1), sp_ground)
    near('v2 air tap: Fall carries the miss\'s last speed (%.2f, energy 2: the air drift)' % B.VSTOP, abs(g.vx2), B.VSTOP,
         0.01)
    accs = [a for n, a in g.acc_log if n > k_end]
    want = [round(-GRAVITY * min(1.0, n / B.EASE_FRAMES), 4) for n in range(1, int(B.EASE_FRAMES) + 1)]
    check('air tap: his gravity eased back in over %d frames (-%.4f a frame more each frame), then his own' % (
        B.EASE_FRAMES, GRAVITY / B.EASE_FRAMES), accs[:len(want) + 1], [round(x, 4) for x in want] + [-GRAVITY])
    check('air tap: the air use taken, its variable reset (KO | landing | ledge | hit -> 0) on him; a second refused',
          (g.vars.get(B.V_USED), g.items.get('me', {}).get(B.USED_INDEX), ),
          (1.0, [0.0, 15]))
    g2 = Game(air=True, y=200.0, floor=0.0)
    tr2, vm2 = run(path, g2, frames=5)
    vm2.g[18] = 2
    check('  ts_can_side in the air after the use: 0', vm2.call(fn(vm2, 'ts_can_side')), 0)
    g2.event('me', 2)
    check('  a landing (the exe\'s reset, bit 2): the use back (VAR_26 0), ts_can_side 1',
          (g2.vars.get(B.V_USED), vm2.call(fn(vm2, 'ts_can_side'))), (0.0, 1))
    g2.vars[B.V_USED] = 1.0
    g2.event('me', 8)
    check('  a hit (bit 8): back too', g2.vars.get(B.V_USED), 0.0)
    # 3. a fast fall after an aim down: the fall limit lowered by FALL_EASE a frame
    v = V(2, 60.0, y=150.0, air=True)
    g = Game(fighters=[v], air=True, y=200.0, floor=0.0, held=lambda n: True)
    v.x = 1e4                                           # out of reach until the dash: then put below-ahead (tracked)

    def dive(g_, k):
        if k == B.WIND_END + B.CHARGE + 2:
            v.x, v.y = g_.x + 20.0, g_.y - 42.0         # 64.5 degrees down, 46.5 away: tracked
        if k == B.WIND_END + B.CHARGE + 8:
            v.x = 1e4                                   # gone: the last aim kept
    tr, vm = run(path, g, frames=300, after=60, tick=dive)
    lims = [x for n, x in g.vlims if n > g.statuses[0][0]] if g.statuses else []
    falls = [x for x in lims if x > MAX_FALL + 1e-3]
    steps = sorted({round(a - b, 3) for a, b in zip(falls, falls[1:])})
    vy_end = [vy for n, vx, vy in g.vel if n == g.statuses[0][0] - 1][0]
    print('     the dive: falling %.3f a frame at the move\'s end; the limit after it %s' % (vy_end, lims[:8]))
    check('fully charged dive (tracked down 64.5 degrees): Fall faster than his max fall (%.2f), the limit lowered %.2f a '
          'frame to it' % (-vy_end, B.FALL_EASE), (-vy_end > MAX_FALL + 0.1, steps, lims[len(falls)] if len(lims) >
                                                    len(falls) else None), (True, [B.FALL_EASE], MAX_FALL))
    # 4. charges: 20 frames (half), full
    for held, v_ in ((20, B.speed(20)), (B.CHARGE + 5, B.VMAX)):
        g = Game(held=lambda n, h=held: n < B.WIND_END + h)
        tr, vm = run(path, g, frames=400)
        c = min(held, B.CHARGE)
        t0 = B.WIND_END + c
        r0 = [m for m in g.motions if m[1] != 'set'][-1][0]       # the restart
        sp = speeds(g, r0 - B.WIND_END + mf, r0 - B.WIND_END + mf + mn - B.MOVE_EASE - 1)
        check('charge %d: restarted at %d (the scripts\' clock), the moving part at %.2f (%s), Wait at %d' % (
            held, t0 - (0 if c < B.CHARGE else 1), v_, 'full' if c >= B.CHARGE else 'half', B.DASH_END + c - (c >= B.CHARGE)),
              ([m for m in g.motions if m[1] != 'set'][-1][:2], set(sp), tr[-1][0]),
              ((t0 - (0 if c < B.CHARGE else 1), 0x219), {round(v_, 3)}, B.DASH_END + c - (c >= B.CHARGE)))
        near('charge %d: his travel' % held, tr[-1][3], B.travel(c, root), 0.3)
    # 5. caught
    caught_tests(path, air=False)
    caught_tests(path, air=True)
    shield_tests(path)
    # 6. refusals; armor beaten (the user: "shieldable but beats armor")
    for name, kw, catches in (('invincible', dict(body=1), False), ('countering', dict(counter=True), False),
                              ('intangible', dict(body=2), False), ('super armor', dict(armor=1), True),
                              ('heavy armor', dict(armor=2, armor_thr=500.0), True),
                              ('lying (DownWait)', dict(status=0x50), True)):
        v = V(2, 30.0, **{k: x for k, x in kw.items() if k != 'status'})
        if 'status' in kw:
            v.status = kw['status']
        g = Game(fighters=[v])
        tr, vm = run(path, g)
        got = any(t[1] == 0x21D for t in tr)
        check('%s fighter ahead: %s' % (name, 'caught' if catches else 'not caught, the dash goes on to its end'),
              (got, tr[-1][5] if not catches else None), (catches, 0 if not catches else None))
        if 'armor' in name:
            ck_ = first(tr, lambda t: t[1] == 0x21D)[0]
            check('  its armor lifted on the box\'s frame of contact, before the collision (ARMOR 0), not given back',
                  [w for w in v.wlog if w[1] == 'armor'], [(ck_ - 1, 'armor', 0.0)])
        if name.startswith('lying'):
            check('lying: put into the hold\'s Damage (0x46) at the catch', [w for w in v.wlog if w[1] == 'status'][:1],
                  [(first(tr, lambda t: t[1] == 0x21D)[0], 'status', 70.0)])
    v = V(2, -40.0, armor=1, armor_thr=0.0)             # behind him
    g = Game(fighters=[v])
    tr, vm = run(path, g)
    check('an armored fighter the box never touches keeps its armor', [w for w in v.__dict__.get('wlog', [])
                                                                       if w[1] == 'armor'], [])
    # an invincible fighter in front, another behind it: the second is caught
    v1, v2 = V(2, 20.0, body=1), V(3, 50.0)
    g = Game(fighters=[v1, v2])
    tr, vm = run(path, g)
    check('an invincible fighter, then another: the second caught (slot 3)', g.vars.get(B.V_SLOT), -1.0)
    check('  (its hold written on slot 3 only)', sorted({s_ for _n, s_, _x in g.holds}), [3])
    tracking_tests(path)
    # 8. B-reverse
    for kk, want in ((0, 1), (3, 1), (4, 0)):
        g = Game(stick_x=lambda n, kk=kk: -1.0 if n == kk else 0.0)
        run(path, g, frames=10)
        check('B-reverse: the stick back on frame %d turns him %d time(s); his speed not turned' % (kk, want),
              len(g.turns), want)
    g = Game(stick_x=lambda n: -0.4)
    run(path, g, frames=10)
    check('B-reverse: a weak stick back (0.4) doesn\'t', len(g.turns), 0)
    # 9. cut in the hold / the victim KO'd
    ck = B.HIT_FROM + 1 + 4                             # the catch (k 34: the box hits on 33 at 30 ahead)
    v = V(2, 30.0)
    g = Game(fighters=[v])
    tr, vm = run(path, g, frames=200)
    ck = first(tr, lambda t: t[1] == 0x21D)[0]
    v = V(2, 30.0)
    g = Game(fighters=[v])
    tr, vm = run(path, g, cut_at=ck + 5)
    check('cut 5 frames into the hold: the victim let go (controller and stage collision back)',
          (v.input_off, v.ground[-1][1] if v.ground else None), (False, 5.0))
    v = V(2, 30.0)
    g = Game(fighters=[v])

    def ko_tick(g_, k):
        if k == ck + 4:
            v.status = 0xB1
    tr, vm = run(path, g, tick=ko_tick)
    check('the victim KO\'d in the hold: let go, nothing held after', (v.input_off, max(n for n, _s, _x in g.holds)),
          (False, ck + 3))


def shield_tests(path):
    for charged in (False, True):
        v = V(2, 30.0, shield=True, shield_hp=50.0)
        g = Game(fighters=[v], held=(lambda n: True) if charged else None)
        tr, vm = run(path, g, frames=300, after=60)
        tag = 'fully charged' if charged else 'uncharged'
        c = first(tr, lambda t: t[1] == 0x21D)
        check('%s, a shielding fighter: the time stop all the same (caught shielding, TS_V_SHV 1)' % tag,
              (c is not None, g.vars.get(B.V_SHV)), (True, 1.0))
        if c is None:
            continue
        check('  kept where it is (no hold offset), frozen and its controller off until the punch, its stage collision '
              'never touched', ([x for _n, s_, x in g.holds if s_ == 2], v.ground), ([], []))
        hk = [h for h in v.shield_hits if h[1] == 'strike'] if hasattr(v, 'shield_hits') else []
        if not charged:
            sk = hk[0][0] if hk else None
            want_hp = round(50.0 + B.STRIKE_HIT['Damage'] * 1.19 - 50.0 * B.SH_TAKE, 3)
            check('  uncharged: the punch on the shield; its shield %.0f%% of the max less than before the hit '
                  '(%.2f with the model\'s untouched 50), %d frames of shieldstun held' % (
                      100 * B.SH_TAKE, want_hp, B.SH_STUN),
                  (sk is not None, [w[2] for w in v.wlog if w[1] == 'shield_hp'], v.pushes[0][1] if
                   getattr(v, 'pushes', None) else None), (True, [want_hp], B.SH_STUN))
            mine = g.statuses[0][0] if g.statuses else None
            free = first([(n, st, hs, hp) for n, st, hs, hp, _x in v.log if n > sk], lambda t: t[1] == 0x1C and t[3] == 0)
            adv = (free[0] - mine) if (free and mine) else None
            print('     shield: punch on %s, he acts on %s (connect frame %d), the shielder on %s: %+d' % (
                sk, mine, B.SH_IASA, free and free[0], adv if adv is not None else 0))
            check('  uncharged: he acts at the connect\'s frame %d, the shielder later: at an advantage (the model: +9; '
                  'by the held count +%d)' % (B.SH_IASA, B.SH_STUN - (B.SH_IASA - B.STRIKE) + 1), (g.statuses[0][1], adv),
                  (0, 9))
        else:
            check('  fully charged: the punch through the shield (unblockable): %g%% (16 + %g) to the body, launched' % (
                B.STRIKE_HIT['Damage'] + B.SH_BONUS, B.SH_BONUS), (hk, round(v.pct, 3),
                                                                   getattr(v, 'launch', 0) > 80),
                  ([], B.STRIKE_HIT['Damage'] + B.SH_BONUS, True))


def caught_tests(path, air):
    y = 40.0 if air else 0.0
    v = V(2, 30.0, y=y, air=air)
    by = V(3, -60.0, y=y, air=air)                      # a bystander behind him
    g = Game(fighters=[v, by], air=air, y=y)
    tr, vm = run(path, g, frames=200)
    tag = 'air' if air else 'ground'
    c = first(tr, lambda t: t[1] == 0x21D)
    check('%s catch: the connect motion (SpecialAirS from 0) on a real hit, slot 2' % tag,
          (c is not None, [m for m in g.motions if m[1] == 0x21D][:1] == [(c[0], 0x21D, 0.0)] if c else None),
          (True, True))
    if c is None:
        return
    ck = c[0] - 1                                       # the detection box hit the frame before the catch
    held = [x for n, s_, x in g.holds if s_ == 2]
    hk = sorted({n for n, s_, x in g.holds if s_ == 2})
    check('%s: held %.2f in front every frame from the catch to the punch\'s frame' % (tag, B.HOLD_X),
          (set(held), hk[0], hk[-1]), ({B.HOLD_X}, ck + 1, ck + B.CATCH_FREEZE + B.STRIKE - 1))
    check('%s: the victim\'s controller off from the catch, back at the punch (and its stage collision)' % tag,
          ([w[0] for w in v.wlog if w[1] == 'input'][:1], [w[2] for w in v.wlog if w[1] == 'input'][-1],
           v.ground[-1][1]), ([ck + 1], 0.0, 5.0))
    sk = ck + B.CATCH_FREEZE + B.STRIKE
    by_stop = sorted({n for n, st, hs, hp, _x in by.log if hp > 0})
    check('%s: the time stop: the bystander frozen (a hitstop renewed every frame) from the catch to the punch\'s frame, '
          'free after' % tag, (by_stop[0] if by_stop else None, by_stop[-1] if by_stop else None, len(by_stop)),
          (ck + 1, sk - 1, sk - 1 - ck))
    check('%s: punched at %d: 2 + 16 = 18%%, launched (DamageFly), XV2\'s hit look the next frame (v2: Time Skip\'s own '
          'Btl_HitLOD / Btl_HitL x2 sets / the sweat) and Hit_TmLck once' % (tag, sk),
          (round(v.pct, 3), v.hit_at, [(n, i) for n, i, _x, _y, _s in g.fx if i != B.FX_TRAIL_ID],
           [(n, s_) for n, w, s_ in g.sounds if w == 'play']),
          (18.0, sk, [(sk + 1, B.FX_LOD_ID), (sk + 1, B.FX_IDS['hitl']), (sk + 1, B.FX_IDS['hitl_2']),
                      (sk + 1, B.SH_FX['sweat'])], [(sk + 1, B.SE_IDS['ts_hit'])]))
    sizes = [s_ for _n, i_, _x, _y, s_ in g.fx if i_ != B.FX_TRAIL_ID]
    check('%s: the hit look\'s sizes (x%.2f the EEPK\'s 1.5 / 0.8 / 2.0)' % (tag, B.FX_SCALE), sizes,
          [round(B.EEPK_SCALE[e] * B.FX_SCALE, 3) for e in ('Btl_HitLOD.emp', 'Btl_HitL.emp', 'Btl_HitL.emp',
                                                             'Btl_Sweat00.emp')])
    inv = sorted({n for n, _v in g.inv})
    fz = sk + B.STRIKE_FREEZE
    check('%s: invincible from the catch through the punch\'s freeze (renewed by 2, 1 on the first frame after)' % tag,
          (inv[0], inv[-1], [val for n, val in g.inv if n == inv[-1]]), (ck + 1, fz + 1, [1.0]))
    end = tr[-1]
    check('%s: the connect ends at its last frame (%d), %s' % (tag, B.CONNECT_END, 'Fall' if air else 'Wait'),
          (end[0], end[5]), (fz + B.CONNECT_END - B.STRIKE, 0xE if air else 0))
    if air:
        accs = [a for n, a in g.acc_log if n > fz]
        check('air: held in place through the hold and the freeze; then his gravity eased in (-%.4f a frame more)' % (
            GRAVITY / B.EASE_FRAMES), (max(abs(t[4] - c[4]) for t in tr if c[0] <= t[0] <= fz), accs[:3]),
              (0.0, [round(-GRAVITY * k / B.EASE_FRAMES, 4) for k in (1, 2, 3)]))


def script_tests(out, sh_out):
    body = os.path.join(out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    sbody = os.path.join(sh_out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    nm = lambda c: acmd.INFO[c.ident]['name']                                 # noqa: E731
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    f = {p: acmd.ACMDFile.load(os.path.join(body, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    b = {p: acmd.ACMDFile.load(os.path.join(sbody, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    dash, conn = f['game'].script('specials'), f['game'].script('specialairs')
    keys = ('ID', 'Part', 'Damage', 'Angle', 'BKB', 'KBG', 'Size', 'Z', 'Y', 'HitstopFrames', 'SelfHitstopFrames',
            'SDI', 'Clang', 'Rebound', 'NoGFX', 'Ground/Air', 'Shieldable')
    hb = lambda s: [tuple(round(x, 3) if isinstance(x, float) else x for x in (dict(zip(syn, c.params))[k] for k in keys))  # noqa
                    for c in s if nm(c) == 'Extra_Special_Hitbox']
    check('specials: the connect box at %d in the dash only (TS_V_PH > 2.5): %s' % (B.HIT_FROM, (keys,)),
          ([c.params for c in dash if nm(c) in ('FRAME', 'Float_Var_Compare')], hb(dash)),
          ([[float(B.HIT_FROM)], [B.V_PH, 5, 2.5]],
           [(0, 0, 2.0, 0, 1, 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, B.CATCH_FREEZE, B.CATCH_FREEZE, 0.0, 0, 0, 0, 3, 1)]))
    check('specialairs: the stopped time (Stage_Freeze on at 0, %d frames at most; off at the punch %d), the punch\'s '
          'Part 1 record cleared, off at %d; the three punches (uncharged shieldable 16; fully charged unblockable, 22 on a '
          'fighter caught shielding, 16 else)' % (B.STAGE_FREEZE_SAFETY, B.STRIKE, B.STRIKE + 2),
          ([(nm(c), c.params) for c in conn if nm(c) in ('FRAME', 'Hit_Log_Clear', 'Remove_All_Hitboxes', 'Stage_Freeze',
                                                         'Float_Var_Compare')], hb(conn)),
          ([('Stage_Freeze', [1, B.STAGE_FREEZE_SAFETY]), ('FRAME', [float(B.STRIKE)]), ('Stage_Freeze', [0, 0]),
            ('Hit_Log_Clear', [1]), ('Float_Var_Compare', [B.V_CHG, 4, B.FULL]), ('Float_Var_Compare', [B.V_CHG, 5, B.FULL]),
            ('Float_Var_Compare', [B.V_SHV, 5, 0.5]), ('Float_Var_Compare', [B.V_SHV, 4, 0.5]),
            ('FRAME', [float(B.STRIKE + 2)]), ('Remove_All_Hitboxes', [])],
           [(0, 1, 16.0, 10, 70, 70, B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE, 0.0, 0, 0,
             1, 3, 1), (0, 1, 22.0, 10, 70, 70, B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE,
                        0.0, 0, 0, 1, 3, 0),
            (0, 1, 16.0, 10, 70, 70, B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE, 0.0, 0, 0,
             1, 3, 0)]))
    snd = [(nm(c), c.params) for s in ('specials', 'specialairs') for c in f['sound'].script(s)
           if nm(c) in ('FRAME', 'Sound_Effect', 'Float_Var_Compare')]
    check('sounds: Basa at 6 (wind-up only), Dash at %d (dash only); TimeStop at 0, PumchiFuri at 8, CharaAway at %d' % (
        B.SND['dash'], B.SND['away']), snd,
          [('FRAME', [6.0]), ('Float_Var_Compare', [B.V_PH, 4, 1.5]), ('Sound_Effect', [B.SE_IDS['ts_basa']]),
           ('FRAME', [float(B.SND['dash'])]), ('Float_Var_Compare', [B.V_PH, 5, 2.5]),
           ('Sound_Effect', [B.SE_IDS['ts_dash']]), ('Sound_Effect', [B.SE_IDS['ts_timestop']]), ('FRAME', [8.0]),
           ('Sound_Effect', [B.SE_IDS['ts_punch']]), ('FRAME', [float(B.SND['away'])]),
           ('Sound_Effect', [B.SE_IDS['ts_away']])])
    eff = [(nm(c), c.params[:2]) for c in f['effect'].script('specials') if nm(c) == 'Graphic_Effect']
    check('effect: Smash\'s dash cloud at the dash on the ground (XV2\'s stage dust)', eff, [('Graphic_Effect',
                                                                                          [B.FX_DUST, 0])])
    gen = [nm(c) for p in f for s in ('specials', 'specialairs') for c in f[p].script(s)
           if 'article' in nm(c).lower() or 'reflect' in nm(c).lower()]
    check('no Cape left (no article, no reflector) in the side special\'s scripts', gen, [])
    other = []
    skip = {acmd.crc(n) for n in B.SCRIPT_NAMES}
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])]:
                other.append((p, hex(h)))
    check('every other script as Sledgehammer v5\'s build', other, [])


def effect_tests(out, sh_out):
    import efc
    import ptcl
    fx = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000')
    sfx = os.path.join(sh_out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000')
    p, e = ptcl.Ptcl(open(fx + '.ptcl', 'rb').read()), efc.Efc(open(fx + '.efc', 'rb').read())
    q, qe = ptcl.Ptcl(open(sfx + '.ptcl', 'rb').read()), efc.Efc(open(sfx + '.efc', 'rb').read())
    sis = {k: e.entries[i & 0xFFFF][1] - 1 for k, i in B.FX_IDS.items()}
    check('Btl_HitL at %s (the converter\'s two sets)' % ', '.join('0x%08X' % i for i in B.FX_IDS.values()),
          {k: p.set_name(si) for k, si in sis.items()},
          {'hitl': 'PtcSupamarioTsBtl_HitL', 'hitl_2': 'PtcSupamarioTsBtl_HitL_2'})
    check('Sledgehammer\'s sets and efc entries unchanged (the same %d sets first, %d entries)' % (len(q.sets),
                                                                                                   len(qe.entries)),
          ([p.set_name(i) for i in range(len(q.sets))] == [q.set_name(i) for i in range(len(q.sets))],
           e.entries[:len(qe.entries)] == qe.entries,
           [p.set_name(e.entries[i & 0xFFFF][1] - 1) for i in B.SH_FX.values()]),
          (True, True, ['PtcSupamarioShBtl_HitLOD', 'PtcSupamarioShBtl_Sweat00']))
    bad, n_em = [], 0
    for si in sis.values():
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            n_em += 1
            t, r = p.field(d, 'emitter_translation'), p.field(d, 'emitter_rotation')
            if max(abs(v) for v in t) > 1e-6 or max(abs(v) for v in r) > 1e-6:
                bad.append((p.emitter_name(d), t, r))
            rgb = [c * p.field(d, 'color_scale') for c in p.color_keys(d, 0)[0][:3]]
            if max(rgb) > 2.0 + 1e-3:
                bad.append((p.emitter_name(d), 'HDR', rgb))
    check('Btl_HitL\'s emitters unturned at its origin (facing-safe), HDR within 2.0', bad, [])
    import json
    rep = json.load(open(os.path.join(out, 'timeskip.json')))['fx']
    conv = sum(len(v['emitters']) for v in rep['sets'].values())
    check('its fake-glow halos (HALO_ALPHA %g) in its own sets: %d (no room for %s)' % (
        rep['halos'].get('alpha', 0), rep['halos'].get('glowing', 0), rep['halos'].get('no_room')),
          n_em - conv, rep['halos'].get('glowing', 0))


def motion_tests(out, sh_out):
    for part in ('main', 'mariopt1', 'lhand', 'rhand'):
        new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        old = dict(omo.pac_read(os.path.join(sh_out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        diff = sorted(n for n in new if new[n] != old.get(n))
        check('%s.pac: only SpecialS / SpecialAirS changed (both)' % part, sorted(n.split('D01')[-1] for n in diff),
              ['SpecialAirS.omo', 'SpecialS.omo'])
        if part == 'main':
            fr = {m: omo.Omo(new[[n for n in new if n.endswith('D01' + m)][0]]).frames for m in A.MOTIONS}
            check('SpecialS 96 frames, SpecialAirS 81', fr, {A.DASH: 96, A.CONNECT: 81})


def sound_tests(out):
    import fighter_own_bank as fb
    t = fb.Table(open(os.path.join(out, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    row = t.tones(0xCB1)
    ids = [(0xCB1 << 16) | i for i in range(len(row))]
    check('the seven tones\' sound ids in row 3249', all(v in ids for v in B.SE_IDS.values()), True)


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    import json
    root = json.load(open(os.path.join(a[0], 'timeskip.json')))['root_speed']
    import supamario_fakedeath_build as FD
    for p_ in (0, 50, 100):
        print('     knockback from %d%%: Time Skip %.1f, Sledgehammer charged %.1f, Core Breaker crash %.1f' % (
            p_, B.knockback(B.STRIKE_HIT, p_ + B.CATCH['Damage']), FD.knockback(SHT.B.HIT_CH, p_),
            FD.knockback(dict(Damage=17.0, Angle=42, KBG=75, FKB=0, BKB=45), p_)))
    path = os.path.join(a[0], 'fighter', 'supamario', 'script', 'msc', 'supamario.mscsb')
    msc_tests(path, root)
    script_tests(a[0], a[1])
    effect_tests(a[0], a[1])
    motion_tests(a[0], a[1])
    sound_tests(a[0])
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
