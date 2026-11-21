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
        self.tints = []              # v3: (n, 'on' / 'off', slot) a screen tint from the MSC (EffectModule op 0 / 1)
        self.e2_log = []             # v3: (n, speed) energy 2 writes
        self.e2_on = []              # v3: (n, on) energy 2 turned on / off
        self.stick_y = None          # v3: n -> the stick's Y (SELF_STICK_Y)
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
        self.fx_rot = []             # v4: (n, id, rotation Y) EffectModule 3's turn
        self.t12_empty = False       # v4: Target 12 reads nothing (the hit's first frame, the user's point-blank clip)
        self.script_lead = 0         # v5: the game script's events this many frames before the MSC's motion frame (an
                                     # ACMD FRAME N run as the motion reaches N - 1: the user's v4 point-blank clip)

    def fvar(self, v):
        if v == 0x0F000111:
            return self.stick_y(self.n) if self.stick_y else 0.0
        if self.t12_empty and v in (0x0F0002CD, 0x0F0002CE):
            return 0.0
        for s_, f_ in self.fighters.items():         # v4: a victim whose freeze isn't seen on the frame after the hit
            if v == 0x0F000043 + 8 * (s_ + 2) and getattr(f_, 'stop_lag', False) and \
                    getattr(f_, 'hit_at', None) == self.n - 1:
                return 0.0
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
        if sid == 0xA:                                  # MathF (0 sqrt; v3: 1 atan2(y, x), 4 cos, 5 sin)
            if a[0] == 0:
                return R.f2i(math.sqrt(max(0.0, f(a[1]))))
            if a[0] == 1:
                return R.f2i(math.atan2(f(a[1]), f(a[2])))
            if a[0] == 4:
                return R.f2i(math.cos(f(a[1])))
            if a[0] == 5:
                return R.f2i(math.sin(f(a[1])))
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
            self.e2_log.append((self.n, round(self.vx2, 4)))
            return 0
        if sid == 0x10 and a and a[0] in (0xB, 0xC) and len(a) == 2 and a[1] == 2:   # v3: energy 2 on / off
            self.e2_on.append((self.n, a[0] == 0xB))
            return 0
        if sid == 0x10 and a and a[0] == 0xB and len(a) == 2 and a[1] == 3:
            self.e3 = True
            return 0
        if sid == 0x10 and a and a[0] == 0 and len(a) == 2:   # a kinetic type: 0 FALL (energy 3 off), 6 ground
            self.e3 = a[1] != 0
            if a[1] == 0:
                self.acc = -GRAVITY
            return 0
        if sid == 0x1C and a and a[0] == 3 and len(a) > 8:    # v4: EffectModule 3's turn (Y)
            self.fx_rot.append((self.n, a[1], round(f(a[6]), 4)))
        if sid == 0x1C and a and a[0] == 0 and len(a) == 9:   # v3: Screen_Tint (EffectModule op 0)
            self.tints.append((self.n, 'on', a[1]))
            return 0
        if sid == 0x1C and a and a[0] == 1 and len(a) == 3:   # v3: End_Screen_Tint (op 1)
            self.tints.append((self.n, 'off', a[1]))
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
        if self.kind == 0x219 and self.clock >= B.HIT_FROM - self.script_lead - 1e-6 and 'catch' not in self.fired:
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
            if getattr(v, 'armor_at', None) is not None and self.n >= v.armor_at:
                v.armor = 1             # v4: armor its own status put on after his MSC (the user's point-blank clip)

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
            if v.status in (0x1C, 0x1E) and getattr(v, 'poke', False) and self.box == 'catch':
                self.hit = v                            # v3: a shield poke: its hurtbox hit, still shielding
                self.hitflag |= 2
                v.pct += B.CATCH['Damage']
                v.hitstop, self.hitstop = B.CATCH_FREEZE, B.CATCH_FREEZE
                return
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


def run(path, g, frames=260, cut_at=None, after=0, tick=None, cut_status='cut', tick_first=False):
    """tick_first (v4): func_82's hooks (sh_tick: Sledgehammer's slot records; ts_tick) before the status's main, not
    after (the game's order isn't known: the user's point-blank clip fits this one)"""
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
        if tick_first:
            vm.call(fn(vm, 'sh_tick'))
            vm.call(fn(vm, 'cb_shield_tick'))
            vm.call(fn(vm, 'ts_tick'))
        if cut_at is not None and k == cut_at:
            g.status = cut_status
        elif k == 0:
            vm.call(fn(vm, 'func_2259'))
        else:
            vm.call(fn(vm, 'ts_loop'))
        tr.append((k, g.kind, round(g.frame, 3), round(g.x, 3), round(g.y, 3), g.status,
                   g.vars.get(B.V_PH, 0.0)))
        if not tick_first:
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
    check('ground tap: the moving part %d-%d at %.2f a frame (uncharged; eased to %.2f over its last %d frames when '
          'faster)' % (mf, mf + mn - 1, B.VMIN, B.VSTOP, B.MOVE_EASE), [round(x, 2) for x in sp],
          [round(x, 2) for x in B.move_speeds(0)])
    near('ground tap: his travel (the wind-up\'s step, the moving part, the stop\'s slide)', end[3], B.travel(0, root), 0.3)
    check('ground tap: Hazure (the whiff) once, at the moving part\'s end (%d)' % (mf + mn),
          [(n, s_) for n, w, s_ in g.sounds if w == 'play'], [(mf + mn, B.SE_IDS['ts_hazure'])])
    check('ground tap: no invincibility, the air use not taken', (g.inv, g.vars.get(B.V_USED, 0.0)), ([], 0.0))
    fwd = sorted({n for n, a_, u_ in g.moves if a_ > 0 and mf <= n < mf + mn})
    check('v2 ground tap: the travel is his position (one forward write a moving frame), his energy 3 held at 0, the '
          'ground correction 1 (slides off edges) every frame', (fwd == list(range(mf, mf + mn)), round(g.vx, 6),
                                                                  sorted({c for _n, c in g.correct})), (True, 0.0, [1]))
    sp_ground = sp
    # 2. in the air: no gravity, v3 the stop (the motion's end lag) as on the ground, then Fall; the use taken, the gravity
    # eased back in
    g = Game(air=True, y=200.0, floor=-1e4)
    tr, vm = run(path, g, after=60)
    k_end = max(t[0] for t in tr if t[5] is None) + 1
    check('v3 air tap (user: "the air whiff snaps to its end"): the stop (phase 4) from %d, Fall (0xE, not FallSpecial) at '
          'the motion\'s end (%d), as Wait on the ground' % (mf + mn, B.DASH_END),
          (ph_at(tr, mf + mn), tr[-1][0], g.statuses[:1]), (4.0, B.DASH_END, [(B.DASH_END, 0xE)]))
    check('air tap: his height kept through the move (no gravity, no drift)',
          max(abs(t[4] - 200.0) for t in tr if t[0] < k_end), 0.0)
    near('v3 (user: "the grounded one moves at the same speed as the air one"): the air travel = the ground\'s (%.1f)' %
         end[3], tr[-1][3], end[3], 0.01)
    check('v2 (user: "Doesn\'t move anywhere in the air"): the air dash moves exactly as the ground one (the moving '
          'part\'s speeds frame by frame)', speeds(g, mf, mf + mn - 1), sp_ground)
    fall_at = g.statuses[0][0]
    check('v3 air tap: Fall from the stop: no speed handed on (energy 2 / 1 set to 0 at the change)',
          ([x for n, x in g.e2_log if n == fall_at][-1:], [x for n, x in g.vy_log if n == fall_at][-1:]), ([0.0], [0.0]))
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
    # 3. a faster fall than his max (a hit's launch in Fall right after the move): the limit lowered by FALL_EASE a frame
    g = Game(air=True, y=400.0, floor=-1e4)

    def fast(g_, k):
        if k == B.DASH_END + 2:
            g_.vy = -2.2
    tr, vm = run(path, g, frames=300, after=40, tick=fast)
    lims = [x for n, x in g.vlims if n > B.DASH_END + 2]
    falls = [x for x in lims if x > MAX_FALL + 1e-3]
    steps = sorted({round(a - b, 3) for a, b in zip(falls, falls[1:])})
    check('v3 a fall faster than his max after the move: the limit lowered %.3f a frame to it (v2 0.05)' % B.FALL_EASE,
          (steps, lims[len(falls)] if len(lims) > len(falls) else None), ([B.FALL_EASE], MAX_FALL))
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
    edge_tests(path, root)
    pointblank_tests(path)
    reset_tests(path)
    exit_tests(path)
    aura_tests(path)
    lag_tests(path)
    landanim_tests(path)
    v3_tests(path)


def tracking_tests(path):
    """7. tracking (the user): the nearest opponent in front within 80, up to 65 degrees up or down, on the ground and in the
    air alike (v2: no ground rule); the direction only (never turned, the speed unchanged). Placed on the moving part's
    first frame (feet to feet) and gone the next: that frame's aim and travel"""
    mf = B.MOVE_FROM
    for name, dx, dy, air, want_air in (
            ('45 degrees up, 50 away (air)', 35.0, 35.0, True, True),
            ('64 degrees up, 60 away (air)', 26.0, 54.0, True, True),
            ('70 degrees up (air): past 65, not tracked', 15.0, 41.0, True, True),
            ('behind (air): not tracked', -30.0, 20.0, True, True),
            ('85 away (air): past 80, not tracked', 70.0, 48.0, True, True),
            ('45 degrees down (air)', 35.0, -35.0, True, True),
            ('64 degrees down (air)', 30.0, -61.0, True, True),
            ('70 away, 30 degrees up (air): tracked (past the God Fist\'s 55)', 60.6, 35.0, True, True),
            ('level ahead on the ground (stays on it)', 40.0, 0.0, False, False),
            ('v2: an airborne opponent 45 degrees up from the ground: tracked, he leaves the ground', 40.0, 40.0, False,
             True),
            ('v2: 60 degrees up from the ground: tracked, lifted off', 25.0, 43.3, False, True),
            ('v2: below-ahead from the ground (off the stage): aimed down, the floor keeps him up while on it', 40.0,
             -30.0, False, False)):
        y0 = 100.0
        v = V(3, 1e4, y=y0, air=True)
        g = Game(fighters=[v], air=air, y=y0, floor=None if air else y0)
        aims = {}

        def put(g_, k, dx=dx, dy=dy):
            if k == mf:
                v.x, v.y = g_.x + dx, g_.y + dy         # feet to feet, placed on the moving part's first frame
            if k == mf + 1:
                v.x = 1e4
        tr, vm = run(path, g, frames=mf + 6, tick=put)
        sn = g.vars.get(B.V_AIM, 0.0)
        ang = math.degrees(math.atan2(dy, dx)) if dx > 0 else 999.0
        want = ang if (math.hypot(dx, dy) < B.TRACK_RANGE and abs(ang) <= B.TRACK_DEG) else 0.0
        vx, vy = [(vx, vy) for n, vx, vy in g.vel if n == mf][0]
        moved = math.degrees(math.atan2(vy, vx))
        if not air and want < 0:                        # on the floor: its downward part taken by the floor
            wmove, wspeed = 0.0, round(B.VMIN * math.cos(math.radians(want)), 3)
        else:
            wmove, wspeed = want, B.VMIN
        check('tracking %s: aimed %.0f degrees (moved %.0f at %.2f), never turned, %s' % (
            name, want, wmove, wspeed, 'in the air' if want_air else 'on the ground'),
            (round(math.degrees(math.asin(max(-1.0, min(1.0, sn)))), 1), round(moved, 1),
             round(math.hypot(vx, vy), 3), g.turns, g.air),
            (round(want, 1), round(wmove, 1), wspeed, [], want_air))
    # v2: the offstage opponent: the aim down kept while on the floor, then down at full speed past the edge
    v = V(3, 40.0, y=-30.0, air=True)
    g = Game(fighters=[v], y=0.0, edge=12.0)
    tr, vm = run(path, g, frames=mf + 20)
    off = first(tr, lambda t: t[0] >= mf and t[4] < -0.01)
    vel = [(n, round(math.hypot(a, b), 3), round(math.degrees(math.atan2(b, a)), 1)) for n, a, b in g.vel
           if off and n >= off[0] and n < mf + 12]
    ang = round(math.degrees(math.atan2(-30.0, 40.0)), 1)
    check('v2: an opponent below past the edge: level on the floor to the edge (12), then down along the aim at the full '
          'speed, the move going on in the air (no Fall)', (off is not None, sorted({x for _n, x, _a in vel}),
                                                            g.statuses), (True, [B.VMIN], []))
    print('     past the edge: the aim %s (opponent at %.1f degrees, re-aimed as he goes)' % (
        sorted({a_ for _n, _x, a_ in vel})[:3], ang))
    # v2 (user: "the exact same tracking rules as Super God Fist"): Time Skip's picker isn't the God Fist's
    src = open(os.path.join(HERE, '..', 'fighters', 'supamario', 'supamario.c')).read()
    body = src[src.index('void ts_track(float k)'):]
    body = body[:body.index('\n}\n')]
    import supamario_godfist_build as GB
    check('v2: ts_track is Time Skip\'s own (no gf_* call, no ground rule), its range / angle (%g / %g) not the God '
          'Fist\'s (%g / %g)' % (B.TRACK_RANGE, B.TRACK_DEG, GB.TRACK_RANGE, GB.TRACK_ANGLE),
          ('gf_' in body, 'global18' in body, B.TRACK_RANGE != GB.TRACK_RANGE, B.TRACK_DEG != GB.TRACK_ANGLE),
          (False, False, True, True))


def edge_tests(path, root):
    """v2 (user: "Can't leave edges"): the ground dash runs off the edge and goes on in the air at its speed"""
    mf, mn = B.MOVE_FROM, B.MOVE_N
    g0 = Game()
    run(path, g0)
    g = Game(edge=40.0, floor=0.0)
    tr, vm = run(path, g, after=30)
    off = first(tr, lambda t: t[3] > 40.0)
    check('v2 edge: off the edge at x 40 in the moving part, the side special goes on (phase 3, SpecialS), no Fall '
          'until the motion\'s end (%d, v3: after the stop), then Fall' % B.DASH_END,
          (off is not None and off[0] < mf + mn, [t[6] for t in tr if off and off[0] <= t[0] < mf + mn and
                                                  t[5] is None][:1], g.statuses[:1]), (True, [3.0], [(B.DASH_END, 0xE)]))
    check('v2 edge: the moving part\'s speeds on and off the edge the same as on flat ground, no height lost while the '
          'move goes on', (speeds(g, mf, mf + mn - 1) == speeds(g0, mf, mf + mn - 1),
                           max(abs(t[4]) for t in tr if t[0] < mf + mn and t[5] is None)), (True, 0.0))
    check('v2 edge: air kinetics once off (correction 5), the air use taken', ([c for _n, c in g.correct][-1:],
                                                                                 g.vars.get(B.V_USED)), ([5], 1.0))


def pointblank_tests(path):
    """v2 (user: "The 2% detection hit won't activate the punch on opponents touching Supamario at point blank")"""
    for x0, tag in ((0.5, 'on top of him (0.5 ahead)'), (-1.0, 'overlapping his back half (1 behind)'),
                    (3.0, 'touching his front (3 ahead)')):
        res = []
        for boxes in ((0,), (0, 1)):
            v = V(2, x0)
            v.w = 1.5
            g = Game(fighters=[v], boxes=boxes)
            tr, vm = run(path, g)
            res.append(any(t[1] == 0x21D for t in tr))
        check('v2 point blank, a slim fighter %s: v1\'s box alone %s; with the point-blank box (ID 1) caught' % (
            tag, 'misses' if not res[0] else 'catches'), res[1], True)
        print('     (v1\'s box alone: %s)' % ('caught' if res[0] else 'missed'))
    v = V(2, 0.5, air=True, y=0.0)
    v.w = 1.5
    g = Game(fighters=[v], air=True, y=0.0, floor=-1e4)
    tr, vm = run(path, g)
    c = first(tr, lambda t: t[1] == 0x21D)
    check('v2 point blank in the air: caught (the connect), the slim fighter held (slot 2)',
          (c is not None, sorted({s_ for _n, s_, _x in g.holds})), (True, [2]))
    # v4 (the user's v3 clip c64f2a99, frames 40-80: a CPU Donkey Kong touching him; it starts an attack as the box comes
    # out (frame 67), takes the 2% at 68 without flinching, the dash goes on through it: no freeze, no punch). Each of
    # the game's possible orders that give that sequence, on v3's catch and v4's
    cases = (('armor its own attack put on that frame (after his MSC: armor_lift can\'t see it)',
              dict(armor_at=B.HIT_FROM, status=0x30), {}),
             ('its freeze not seen on the hit\'s first frame, func_82 (the records) before the status, Target 12 empty',
              dict(stop_lag=True), dict(tick_first=True, t12=True)),
             ('both, and Target 12 empty', dict(armor_at=B.HIT_FROM, status=0x30, stop_lag=True),
              dict(tick_first=True, t12=True)))
    cases = cases + (('v5: the box made a frame before the MSC reads its frame (the user\'s v4 clip aaf3050c: hit on the '
                      'box\'s first frame, at once)', {}, dict(lead=1)),
                     ('v5: that and func_82 first, Target 12 empty, the freeze not seen at once', dict(stop_lag=True),
                      dict(lead=1, tick_first=True, t12=True)))
    for name, vk, gk in cases:
        v = V(2, 1.0, **vk)
        by = V(3, -60.0)
        g = Game(fighters=[v, by])
        g.t12_empty = gk.get('t12', False)
        g.script_lead = gk.get('lead', 0)
        tr, vm = run(path, g, frames=200, tick_first=gk.get('tick_first', False))
        c = first(tr, lambda t: t[1] == 0x21D)
        ck = c[0] - 1 if c else None
        check('v4 point blank (the user\'s clip), %s: the 2%% lands (%s), caught (the connect), held, the hold\'s hitstun '
              'status (0x46: its attack ended), the bystander frozen, punched (18%%)' % (name, v.hit_at),
              (c is not None, sorted({s_ for _n, s_, _x in g.holds}),
               [st_ for n_, st_, _hs, _hp, _x in v.log if c and n_ == c[0]][:1] in ([0x45], [0x46]),
               any(hp > 0 for _n, _st, _hs, hp, _x in by.log), round(v.pct, 3)),
              (True, [2], True, True, 18.0))


def reset_tests(path):
    """v2 (user: "Never resets after being used in the air"): the use (VAR_26) back to 0 from the MSC (ts_reset) on each
    event, with the exe's resets off (the model's older exe: the selection IDs ignored)"""
    events = (('landing', None, None, True), ('ledge (CliffCatch, situation 1)', 0x73, 1, False),
              ('hit (Damage)', 0x45, None, False), ('hit (DamageFlyRoll)', 0x4A, None, False),
              ('grabbed (CapturePulled)', 0x3F, None, False), ('KO (Dead)', 0xB1, None, False),
              ('respawn (Rebirth)', 0xB2, None, False))
    mf, mn = B.MOVE_FROM, B.MOVE_N
    for name, st, sit, land in events:
        g = Game(air=True, y=60.0, floor=0.0 if land else -1e4)
        g.resets = False
        at = mf + mn + 10
        seen = {}

        def tick(g_, k, st=st, sit=sit):
            if k == at - 1:
                seen['before'] = g_.vars.get(B.V_USED)
            if st is not None and k == at:
                g_.status = st
                if sit is not None:
                    g_.sit_fn = lambda n, s_=sit: s_
        tr, vm = run(path, g, frames=300, after=120, tick=tick)
        check('v2 reset (the MSC, the exe\'s resets off): %s -> the air use back (VAR_26 1 -> 0)' % name,
              (seen.get('before'), g.vars.get(B.V_USED)), (1.0, 0.0))
    g = Game(air=True, y=200.0, floor=-1e4)
    g.resets = False
    tr, vm = run(path, g, frames=300, after=40)
    check('v2 reset: still taken while he stays in the air (Fall, no event)', g.vars.get(B.V_USED), 1.0)
    vm.g[18] = 2
    check('  ... and refused (ts_can_side 0)', vm.call(fn(vm, 'ts_can_side')), 0)
    g = Game(air=True, y=200.0, floor=-1e4)
    g.resets = False
    seen = {}

    def tick2(g_, k):
        if k == 3:
            seen['ph'] = g_.vars.get(B.V_PH)
            g_.status = 0x4C                              # a stale status read in the move's first frames
    tr, vm = run(path, g, frames=6, tick=tick2)
    check('v2 reset: not while he is in the move (a stale damage status in its first frames keeps the use taken)',
          g.vars.get(B.V_USED), 1.0)


def brightness_tests(out):
    """v2 (user: "Does a massive white flash when it hits an opponent"): tools/supamario_fx_glow.py on a grass stage and a
    grey one: the punch's look against v1's (the shared Btl_HitLOD) and the user's earlier tolerance (Sledgehammer v5's
    arcs, 1.0 / 3.6 square units over 1.0 on grass); the purple lines and the shards"""
    import supamario_fx_glow as G
    res = {}
    for bg_name, bg in (('grass', (0.5, 0.65, 0.3)), ('grey', (0.5, 0.5, 0.5))):
        r = G.measure(out, ('ts_hit', 'ts_hit_v1', 'ts_e11', 'ts_e0'), None, bg)
        res[bg_name] = r
        h, h1 = r['ts_hit'], r['ts_hit_v1']
        e0, e1 = h['frames'][0][4], h1['frames'][0][4]
        print('     %s: ts_hit frame 0 energy %.1f (v1 %.1f), most over 1.0 in a frame %.1f (v1 %.1f), brightest frame %s' % (
            bg_name, e0, e1, h['max_over_1'], h1['max_over_1'], h['brightest']))
        for k in ('ts_e11', 'ts_e0'):
            moved = max(abs(f_[4]) for f_ in r[k]['frames'])
            print('     %s: %s most over 1.0 %.1f, most white %.1f, the most it changes the picture (|energy|) %.1f' % (
                bg_name, k, r[k]['max_over_1'], r[k]['max_white'], moved))
        check('v2 %s: the punch\'s look at most 1.0 square unit over 1.0 in any frame (Sledgehammer v5\'s uncharged arcs; '
              'v1 %.1f), its first frame (the freeze\'s) at most a third of v1\'s energy, still vibrant (energy 8+ at its '
              'brightest)' % (bg_name, h1['max_over_1']),
              (h['max_over_1'] <= 1.0, e0 <= e1 / 3.0, h['brightest'][4] >= 8.0), (True, True, True))
        for k, lo in (('ts_e11', 20.0), ('ts_e0', 3.0)):
            o1 = 1e9    # v5 (user): the punch's burst limited by its white, not its purple; v6: effect 0 too (violet)
            check('v5 %s: %s (XV2\'s skill effect) %s, at most 1.0 square unit white in any frame, visible (it changes the '
                  'picture by %g+)' % (bg_name, k, 'purple past 1.0 allowed (%.1f square units: it blooms purple)' %
                                       r[k]['max_over_1'], lo),
                  (r[k]['max_over_1'] <= o1, r[k]['max_white'] <= 1.0, max(abs(f_[4]) for f_ in r[k]['frames']) >= lo),
                  (True, True, True))
        # v7: the outline is Outline_Set (his own rim, no effect): nothing of it in the bank to measure (v6's rings went)
        # the wash: alpha-blended white at most WASH_A + the flash: the picture lifted toward white, never past it
        a = 1 - (1 - B.WASH_A) * (1 - B.WASH_FLASH)
        lifted = [round(c * (1 - a) + w * a, 3) for c, w in zip(bg, B.WASH_RGB)]
        check('v6 %s: the wash at its brightest (alpha %.2f) lifts the picture to %s: under 1.0 (no white blow-out, no '
              'bloom)' % (bg_name, a, lifted), max(lifted) < 1.0, True)
        lifted = [round(c * (1 - B.FADE_A) + w * B.FADE_A, 3) for c, w in zip(bg, B.WASH_RGB)]
        check('v7 %s: the white fade quad (the white negative\'s cut) at its brightest (alpha %.2f) lifts the picture to %s: '
              'under 1.0, its contrast %.2f (positive: never the flat grey of a part-negative)' % (
                  bg_name, B.FADE_A, lifted, 1 - B.FADE_A), (max(lifted) < 1.0, 1 - B.FADE_A > 0.2), (True, True))
    return res


def exit_tests(path):
    """v3 (the known v2 bug): the time stop's look (the camera's darkening and glass: the connect's effect script), the
    stage and the frozen fighters let go on every exit before the punch; nothing taken off on the normal path"""
    look = (B.FX_DARK_ID, B.FX_GLASS_ID) if B.CAMERA_FX else (B.FX_GLASS_ID,)
    v = V(2, 30.0)
    by = V(3, -60.0)
    g = Game(fighters=[v, by])
    tr, vm = run(path, g, frames=200)
    ck = first(tr, lambda t: t[1] == 0x21D)[0]
    sk = ck - 1 + B.CATCH_FREEZE + B.STRIKE
    slot = B.TINT[0]
    want_t = [] if B.CAMERA_FX else [(ck, 'on', slot), (sk, 'off', slot)]
    check('v3 normal (%s): %s, nothing killed (the glass plays out)' % (
        'camera build' if B.CAMERA_FX else 'default build',
        'the darkening the script\'s camera effect' if B.CAMERA_FX else
        'the MSC\'s screen tint on at the catch (%d), off at the punch (%d, %d frames out), once each; v5: the glass the '
        'script\'s (on the screen), none from the MSC' % (ck, sk, B.TINT_OUT)),
          (g.tints, [k_ for k_ in g.kills if k_[1] in look and k_[0] < tr[-1][0]],
           [n for n, i, _x, _y, _s in g.fx if i == B.FX_GLASS_ID]), (want_t, [], []))
    check('v6 / v7 normal: the move\'s end (ts_end) ends the white fade quad, the wash and the glass (ts_fx_off)',
          sorted({i for n, i in g.kills if n == tr[-1][0]} & {B.FX_FADE_ID, B.FX_WASH_ID, B.FX_GLASS_ID}),
          sorted({B.FX_FADE_ID, B.FX_WASH_ID, B.FX_GLASS_ID}))
    for name, st in (('cut (a status change)', 'cut'), ('Supamario hit (Damage)', 0x45), ('Supamario KO\'d (Dead)', 0xB1),
                     ('the match ending (Win)', 0x14F)):
        v = V(2, 30.0)
        by = V(3, -60.0)
        g = Game(fighters=[v, by])
        cut = ck + 5
        tr, vm = run(path, g, cut_at=cut, after=12, cut_status=st)
        froze = sorted({n for n, st_, hs, hp, _x in by.log if hp > 0})
        check('v3 exit before the punch, %s at %d: the darkening (End_Screen_Tint / its camera effect) and the glass '
              'taken off at once, the victim let go (controller, stage collision), the others no longer frozen (none '
              'renewed after the cut: free within 2 frames), the air drift back on' % (name, cut),
              (g.tints, sorted(set(k_ for k_ in g.kills if k_[1] in look)), v.input_off,
               v.ground[-1][1] if v.ground else None, max(froze) <= cut + 2 if froze else None, g.e2_on[-1:]),
              ([] if B.CAMERA_FX else [(ck, 'on', slot), (cut, 'off', slot)], sorted((cut, i) for i in look), False,
               5.0, True, [(cut, True)]))
        check('  v6 / v7: ... and the white fade quad / the wash ended there too (ts_fx_off)',
              sorted({i for n, i in g.kills if n == cut} & {B.FX_FADE_ID, B.FX_WASH_ID}),
              sorted({B.FX_FADE_ID, B.FX_WASH_ID}))
    v = V(2, 30.0)
    g = Game(fighters=[v])

    def esc(g_, k):
        if k == ck + 4:
            v.status = 0xB1
    tr, vm = run(path, g, tick=esc)
    check('v3 the victim escapes (KO\'d in the hold): let go, the move goes on to its end, nothing killed, the darkening '
          'still to the punch', (v.input_off, [k_ for k_ in g.kills if k_[1] in look and k_[0] < tr[-1][0]], tr[-1][5],
                                 g.tints), (False, [], 0, want_t))
    g = Game()
    tr, vm = run(path, g)
    check('v3 a miss: no darkening, no glass, nothing killed', (g.tints, [k_ for k_ in g.kills if k_[1] in look and
                                                                         k_[0] < tr[-1][0]],
                                                               [i for _n, i, _x, _y, _s in g.fx if i == B.FX_GLASS_ID]),
          ([], [], []))


def v3_tests(path):
    """v3: the charge's drift, the punch without drift, the shield poke, the first-frame retry, soft tracking"""
    mf = B.MOVE_FROM
    # charge drift (only while the charge is held)
    for air in (False, True):
        y0 = 100.0
        g = Game(held=lambda n: n < B.WIND_END + 20, air=air, y=y0, floor=None if air else y0,
                 stick_x=lambda n: 1.0 if n >= B.WIND_END else 0.0)
        g.stick_y = lambda n: 1.0 if n >= B.WIND_END else 0.0
        tr, vm = run(path, g, frames=80)
        drift = [(n, a_, u_) for n, a_, u_ in g.moves if B.WIND_END < n < B.WIND_END + 19]
        fw = sorted({a_ for _n, a_, _u in drift if a_})
        up = sorted({u_ for _n, _a, u_ in drift if u_})
        check('v4 charge drift (%s; user: "left / right only"): the stick held forward and up while charging: %.2f a '
              'frame forward, nothing up' % ('air' if air else 'ground', B.DRIFT), (fw, up), ([round(B.DRIFT, 4)], []))
    g = Game(stick_x=lambda n: 1.0)
    g.stick_y = lambda n: 1.0
    tr, vm = run(path, g, frames=mf + 10)
    gs = Game()
    trs, vms = run(path, gs, frames=mf + 10)
    check('v3 no drift outside the charge (a tap with the stick held: the same travel as without)',
          round(tr[-1][3], 4), round(trs[-1][3], 4))
    # no drift in the punch (air)
    v = V(2, 30.0, y=40.0, air=True)
    g = Game(fighters=[v], air=True, y=40.0)
    tr, vm = run(path, g, frames=200)
    ck = first(tr, lambda t: t[1] == 0x21D)[0]
    sk = ck - 1 + B.CATCH_FREEZE + B.STRIKE
    after = [x for n, x in g.e2_log if n > sk + B.STRIKE_FREEZE]
    check('v3 air punch: the air drift off at the catch, held at 0 every frame after the freeze, back on at Fall',
          (g.e2_on[:1], set(after), g.e2_on[-1:]), ([(ck, False)], {0.0}, [(g.statuses[0][0], True)]))
    # shield poke: its body reached past a small shield
    for charged in (False, True):
        v = V(2, 30.0, shield=True, shield_hp=50.0)
        v.poke = True
        g = Game(fighters=[v], held=(lambda n: True) if charged else None)
        tr, vm = run(path, g, frames=300, after=60)
        check('v3 shield poke (%s): a body hit on a shielding fighter is the shield case: caught shielding (TS_V_SHV 1)'
              % ('fully charged' if charged else 'uncharged'), (first(tr, lambda t: t[1] == 0x21D) is not None,
                                                                 g.vars.get(B.V_SHV)), (True, 1.0))
    # soft tracking after the strong frames
    v = V(3, 1e4, y=100.0, air=True)
    g = Game(fighters=[v], air=True, y=100.0)

    def put(g_, k):
        if k == mf + B.TRACK_STRONG + 1:
            v.x, v.y = g_.x + 30.0, g_.y + 30.0       # 45 degrees up, placed after the strong frames
    aims = []

    def rec(g_, k):
        put(g_, k)
        aims.append((k, g_.vars.get(B.V_AIM, 0.0)))
    tr, vm = run(path, g, frames=mf + 12, tick=rec)
    ang = [round(math.degrees(math.asin(max(-1, min(1, a_)))), 2) for k, a_ in aims if k > mf + B.TRACK_STRONG + 1]
    steps = sorted({round(b_ - a_, 2) for a_, b_ in zip(ang, ang[1:])})
    check('v3 tracking: after its first %d frames (strong: straight at the target) it turns at most %.1f degrees a frame '
          'toward a target appearing then (45 degrees up)' % (B.TRACK_STRONG, B.TRACK_SOFT), steps, [B.TRACK_SOFT])
    v = V(3, 1e4, y=100.0, air=True)
    g = Game(fighters=[v], air=True, y=100.0)

    def put2(g_, k):
        if k == mf:
            v.x, v.y = g_.x + 30.0, g_.y + 30.0
    tr, vm = run(path, g, frames=mf + 3, tick=put2)
    check('v3 tracking: strong at release (the first moving frame aimed straight at a target 45 degrees up)',
          round(math.degrees(math.asin(g.vars.get(B.V_AIM, 0.0))), 1), 45.0)


def aura_tests(path):
    """v4: XV2's skill effect 0 (1350_HIK_FRT.eepk: the world parts as one set at his ground point, turned to his facing)
    at the move's start (ts_init: XV2's frame 0), left behind as he dashes, again every AURA_EVERY frames of a held
    charge"""
    for face in (1.0, -1.0):
        g = Game()
        g.face = face
        tr, vm = run(path, g)
        au = [(n, x, y) for n, i, x, y, _s in g.fx if i == B.FX_AURA_ID]
        rot = [r for n, i, r in g.fx_rot if i == B.FX_AURA_ID]
        check('v4 effect 0 (facing %s): once at the move\'s frame 0 (XV2\'s BAC 0), at his ground point, x%.2f, turned to '
              'his facing (Y %s)' % ('right' if face > 0 else 'left', B.AURA_SIZE, '0' if face > 0 else 'pi'),
              ([(n, round(y, 2)) for n, _x, y in au], rot, [s_ for _n, i, _x, _y, s_ in g.fx if i == B.FX_AURA_ID]),
              ([(0, 0.0)], [0.0 if face > 0 else round(math.pi, 4)], [round(B.AURA_SIZE, 3)]))
        check('  ... he dashes on from there: %.1f units past it by the move\'s end' % abs(tr[-1][3] - au[0][1]),
              abs(tr[-1][3] - au[0][1]) > 50.0, True)
    g = Game(held=lambda n: n < B.WIND_END + B.CHARGE + 5)
    tr, vm = run(path, g, frames=400)
    au = [n for n, i, _x, _y, _s in g.fx if i == B.FX_AURA_ID]
    check('v4 effect 0 in a full charge: at 0, then every %d charge frames (as the last one\'s 40-frame emission ends: '
          'one at a time); v6: none as the dash starts (v4 / v5 played one more there)' % B.AURA_EVERY,
          au, [0] + [B.WIND_END + k for k in range(B.AURA_EVERY - 1, B.CHARGE - 1, B.AURA_EVERY)])


def lag_tests(path):
    """v5 (user: "high landing lag after using Time Skip if it ended in the air, similarly to how Bayonetta ... even after
    doing other moves"): his next landing after an air end is LandingFallSpecial LAND_LAG frames long, whatever he did in
    the air before it; nothing after a ground end; cleared by a hit, a ledge, a special-fall landing"""
    def after(air, events):
        g = Game(air=air, y=200.0 if air else 0.0, floor=-1e4 if air else 0.0)
        end = []

        def tick(g_, k):
            if not end and g_.status is not None:
                end.append(k)
            if end:
                ev = events.get(k - end[0])
                if ev is not None:
                    g_.status, land = ev
                    if land:
                        g_.air = False
        tr, vm = run(path, g, after=30, tick=tick)
        k0 = end[0] if end else None
        return [(n - k0, st) for n, st in g.statuses if k0 is not None and n > k0], g.vars.get(0), g.vars.get(B.V_RETRY)
    for name, air, ev, want in (
            ('ended in the air, then a landing (Landing 0x16)', True, {5: (0x16, True)}, [(5, 0x19)]),
            ('ended in the air, an air dodge, an aerial, then its landing (0x18)', True,
             {2: (0x22, False), 4: (0x35, False), 8: (0x18, True)}, [(8, 0x19)]),
            ('ended in the air, a light landing (0x17)', True, {3: (0x17, True)}, [(3, 0x19)]),
            ('ended on the ground, then a landing (0x16)', False, {5: (0x16, True)}, []),
            ('ended in the air, hit (Damage 0x45), then a landing', True, {2: (0x45, False), 6: (0x16, True)},
             []),
            ('ended in the air, a ledge (CliffCatch 0x72), then a landing', True, {2: (0x72, False), 6: (0x16, True)},
             []),
            ('ended in the air, a special-fall landing (0x19: its own), then a landing', True,
             {3: (0x19, True), 8: (0x16, True)}, [])):
        st, lag, flag = after(air, ev)
        got = (st, lag if any(x[1] == 0x19 for x in st) else None, flag)
        # v6: a lag landing keeps its mark (LAG_ANIM) into LandingFallSpecial: func_586 clears it (landanim_tests)
        check('v5 landing lag, %s: %s' % (name, 'LandingFallSpecial %d frames (work float 0) at that landing, the mark '
                                          'cleared' % B.LAND_LAG if (0x19 in [x[1] for x in want]) else 'nothing'),
              got, (want, float(B.LAND_LAG) if any(x[1] == 0x19 for x in want) else None,
                    B.LAG_ANIM if any(x[1] == 0x19 for x in want) else 0.0))


def landanim_tests(path):
    """v6 (user: "use Mario's normal landing lag animation after Time Skip falls from the air"): the air end's landing is
    still LandingFallSpecial LAND_LAG frames, its mark (TS_V_RETRY = LAG_ANIM) kept into the status, and func_586 (the
    landing statuses' start) plays LandingHeavy (0x3B) over the lag (rate: its length / LAND_LAG) and clears the mark;
    any other LandingFallSpecial (the up special's: 0x2D) and Sledgehammer's (LandingLight 0x3A) unchanged"""
    LENS = {B.MOT_LANDING_HEAVY: 31, 0x2D: 40, 0x3A: 16}

    class G(Game):
        def sys(self, sid, a):
            if sid == 0x12 and a and a[0] == 0 and len(a) == 2:
                return LENS.get(a[1], 20)
            if sid == 0x12 and a and a[0] == 0x1:
                self.__dict__.setdefault('rates', []).append((a[1], round(R.i2f(a[3]), 4) if len(a) > 3 else None))
            return Game.sys(self, sid, a)
    g = G(air=True, y=200.0, floor=-1e4)
    end = []

    def tick(g_, k):
        if not end and g_.status is not None:
            end.append(k)
        if end and k - end[0] == 5:
            g_.status, g_.air = 0x16, False
    tr, vm = run(path, g, after=20, tick=tick)
    mark = g.vars.get(B.V_RETRY)
    g.rates = []
    vm.g[4], vm.g[5] = 0x19, 0x16
    vm.call(fn(vm, 'func_586'))
    check('v6 landing after an air end: LandingFallSpecial %d frames, the mark %g kept into it; its start (func_586) plays '
          'LandingHeavy (0x%X) at its length / %d (31 frames -> %.4f), the mark cleared' % (
              B.LAND_LAG, B.LAG_ANIM, B.MOT_LANDING_HEAVY, B.LAND_LAG, 31.0 / B.LAND_LAG),
          ([st for _n, st in g.statuses][-1:], g.vars.get(0), mark, g.rates, g.vars.get(B.V_RETRY)),
          ([0x19], float(B.LAND_LAG), B.LAG_ANIM, [(B.MOT_LANDING_HEAVY, round(31.0 / B.LAND_LAG, 4))], 0.0))
    for name, g5, want in (('the up special\'s special fall landing', 0x1B, (0x2D, round(40.0 / 20.0, 4))),
                           ('Sledgehammer\'s landing (from 0x155)', 0x155, (0x3A, round(16.0 / 20.0, 4)))):
        g.rates = []
        g.vars[0] = 20.0
        vm.g[4], vm.g[5] = 0x19, g5
        vm.call(fn(vm, 'func_586'))
        check('v6: %s (no mark) unchanged: %s' % (name, want), g.rates, [want])


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
          (round(v.pct, 3), v.hit_at, [(n, i) for n, i, _x, _y, _s in g.fx
                                       if i not in tuple(B.FX_E11_IDS.values()) + (B.FX_AURA_ID, B.FX_GLASS_ID)],
           [(n, s_) for n, w, s_ in g.sounds if w == 'play']),
          (18.0, sk, [(sk + 1, B.FX_LOD_ID), (sk + 1, B.FX_IDS['hitl']), (sk + 1, B.FX_IDS['hitl_2']),
                      (sk + 1, B.SH_FX['sweat'])], [(sk + 1, B.SE_IDS['ts_hit'])]))
    at = tr[sk + 1]
    e11 = [(n, i_, round(x_ - at[3], 2), round(y_ - at[4], 2), s_) for n, i_, x_, y_, s_ in g.fx
           if i_ in B.FX_E11_IDS.values()]
    check('v4 %s: XV2\'s skill effect 11 with the hit look (its 4 sets: %s), at his right fist (%.2f ahead, %.2f up), '
          'x%.2f, turned to his facing' % (tag, ', '.join('0x%08X' % i for i in B.FX_E11_IDS.values()), B.E11_AT[0],
                                           B.E11_AT[1], B.E11_SIZE),
          (e11, [r for n, i_, r in g.fx_rot if i_ in B.FX_E11_IDS.values()]),
          ([(sk + 1, i, B.E11_AT[0], B.E11_AT[1], round(B.E11_SIZE, 3)) for i in B.FX_E11_IDS.values()], [0.0] * 4))
    sizes = [s_ for _n, i_, _x, _y, s_ in g.fx if i_ in (B.FX_LOD_ID, B.FX_IDS['hitl'], B.FX_IDS['hitl_2'], B.SH_FX['sweat'])]
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


def timed(script):
    """a script's commands with their FRAME (absolute frames; waits added)"""
    at, out = 0.0, []
    for c in script:
        n_ = acmd.INFO[c.ident]['name'] if c.ident in acmd.INFO else hex(c.ident)
        if n_ == 'FRAME':
            at = c.params[0]
        elif n_ == 'WAIT':
            at += c.params[0]
        else:
            out.append((int(at), n_, list(c.params)))
    return out


def outline_sim(events, n):
    """outline_cave's tick (Python): events {effect frame: [Outline_Set params]} -> the weight w each frame 0..n-1 (the
    commands of a frame, then that frame's tick): a command with Alpha > 0 fades in from where it is (FadeIn 0: full at
    once), held Frames once full (0: no count), then out over FadeOut (0: off at once); Alpha 0 fades out over its FadeOut"""
    ph, w, left, rin, rout, ws = 0, 0.0, 0, 0.0, 0.0, []
    for t in range(n):
        for prm in events.get(t, []):
            alpha, frames, fin, fout = prm[4], prm[6], prm[7], prm[8]
            if alpha > 0:
                rout = 1.0 / fout if fout > 0 else 0.0
                left = max(frames, 0)
                if fin > 0:
                    rin, ph = 1.0 / fin, 1
                else:
                    w, ph = 1.0, 2
            elif ph:
                rout = 1.0 / fout if fout > 0 else 0.0
                ph = 3 if rout else 0
                w = w if rout else 0.0
        if ph == 1:
            w += rin
            if w >= 1.0:
                w, ph = 1.0, 2
        elif ph == 2 and left:
            left -= 1
            if not left:
                ph = 3 if rout else 0
                w = w if rout else 0.0
        elif ph == 3:
            w -= rout
            if w <= 0:
                w, ph = 0.0, 0
        ws.append(round(w, 3) if ph else 0.0)
    return ws


def outline_tests(f):
    """v7: the outline is Outline_Set (exe_v46z_outline): XV2's BPE 85 from the charge's start (OL_ON) through the dash,
    renewed every OL_KEEP frames, off at the whiff's OL_OFF or at once at the punch; checked as commands and through
    outline_cave's tick (outline_sim) on the effect frames of a whiff, a held charge (the script's clock running, and
    stopped), a catch at every frame of the box (+ its freeze and the retries) and a cut at any frame"""
    dash, conn = timed(f['effect'].script('specials')), timed(f['effect'].script('specialairs'))
    # v8: the expected commands come from the build's outline_on / outline_off (the outline's one place); the values
    # are checked against OL_* once, here, for Outline_Set
    olname = acmd.INFO[acmd.BY_NAME[B.OUTLINE_CMD]]['name']
    ol = {sc: [(t, p_) for t, n_, p_ in b_ if n_ == olname] for sc, b_ in (('dash', dash), ('connect', conn))}
    pon, poff = (lambda: list(B.outline_on(B.OL_HOLD)[0].params)), (lambda f_: list(B.outline_off(f_)[0].params))   # noqa: E731
    if olname == 'Outline_Set':
        check('v7 / v8 the outline\'s two commands (outline_on / outline_off): Outline_Set on him, OL_RGB at OL_ALPHA, '
              'Tint 0, held OL_HOLD, in OL_IN, out OL_CUT_OUT, Flash 0; its end Alpha 0', (pon(), poff(B.OL_OUT)),
              ([0, B.OL_RGB[0], B.OL_RGB[1], B.OL_RGB[2], B.OL_ALPHA, 0.0, B.OL_HOLD, B.OL_IN, B.OL_CUT_OUT, 0],
               [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, B.OL_OUT, 0]))
    elif olname == 'Outline_Shell':
        check('v9 / v10 the outline\'s two commands: Outline_Shell on him, OL_SH_RGB at OL_SH_ALPHA, OL_WIDTH px, held '
              'OL_HOLD, in OL_IN, out OL_CUT_OUT, Flash 0, Blend OL_BLEND (a glow); its end Alpha 0', (pon(), poff(B.OL_OUT)),
              ([0, B.OL_SH_RGB[0], B.OL_SH_RGB[1], B.OL_SH_RGB[2], B.OL_SH_ALPHA, B.OL_WIDTH, B.OL_HOLD, B.OL_IN, B.OL_CUT_OUT,
                0, B.OL_BLEND], [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, B.OL_OUT, 0, 0]))
    want_d = [(t, pon()) for t in range(B.OL_ON, B.OL_OFF, B.OL_KEEP)] + [(B.OL_OFF, poff(B.OL_OUT))]
    pin = lambda: list(B.outline_on(B.OL_HOLD, True)[0].params)     # noqa: E731
    want_c = [(t, pin()) for t in range(0, B.STRIKE, B.OL_KEEP)] + [(B.STRIKE, poff(B.OL_PUNCH_OUT))]
    if olname == 'Outline_Shell' and B.INVERT_FX:
        import screen_invert_cave as SI
        st = B.INV_STOP
        A = SI.filter_matrix(1.0, st[1], st[5], st[6], st[7:10])
        a = B.OL_INV_ALPHA / 255.0
        sa = B.OL_SH_ALPHA / 255.0
        # v11: drawn over (Blend 0), for any encoding scale k up to OL_SH_K_MAX (the v7 clip: k >= 2.2; v10's added
        # light colour clipped to white at k >= ~1.3: this check fails on v10's values)
        def over(bg, k):
            return [round(255 * ((1 - sa) * bg / 255.0 + sa * min(1.0, k * c / 255.0))) for c in B.OL_SH_RGB]
        if B.OL_BLEND == 1:
            grey = [[round(255 * min(1.0, 100 / 255.0 + sa * min(1.0, k * c / 255.0))) for c in B.OL_SH_RGB]
                    for k in (1.0, 2.0, B.OL_SH_K_MAX)]
        else:
            grey = [over(100, k) for k in (1.0, 2.0, B.OL_SH_K_MAX)] + [over(20, k) for k in (1.0, 2.0, B.OL_SH_K_MAX)]
        check('v11 the dash\'s band over a mid grey (100) and a dark stage (20), encoding scale k 1 / 2 / %g: blue, '
              'never white (blue - red >= 40 every time): %s' % (B.OL_SH_K_MAX, grey),
              (B.OL_BLEND, all(g[2] - g[0] >= 40 for g in grey)), (0, True))

        def seen(bg):        # the band over a background pixel bg (0-1), then the stop's filter
            px = [a * B.OL_INV_RGB[i] / 255.0 + (1 - a) * bg[i] for i in range(3)]
            return [round(255 * min(1.0, max(0.0, sum(A[i][j] * px[j] for j in range(3)) + A[i][3]))) for i in range(3)]
        dark, light = seen([0.1, 0.1, 0.1]), seen([0.8, 0.8, 0.8])
        bg_dark_stage = [round(255 * (0.8 - 0.8 * 0.1) + c) for c in st[7:10]]     # a dark stage's pixel in the negative
        check('v10 the connect\'s outline (under the stop\'s negative): OL_INV_RGB (white) drawn over (Blend 0) at '
              'OL_INV_ALPHA, the rest as the dash\'s; through INV_STOP it comes out dark navy (%s / %s over a dark / a '
              'light background), against a dark stage\'s negative of ~%s: at least 120 darker' % (dark, light,
                                                                                                    bg_dark_stage),
              (pin()[1:4], pin()[4], pin()[10], pin()[5:10] == pon()[5:10], max(dark + light) <= 90,
               min(b - d for b, d in zip(bg_dark_stage, dark)) >= 120),
              (list(B.OL_INV_RGB), B.OL_INV_ALPHA, B.OL_INV_BLEND, True, True, True))
    check('v7 outline (the dash): Outline_Set on him (Target 0) from the charge\'s start %d (XV2\'s BPE 85 at BAC 20), '
          'white-blue %s at Alpha %g, edge only (Tint 0), steady (Flash 0), in over %d, renewed every %d frames (each held '
          '%d, then out over %d), off at %d (BAC 100) over %d' % (
              B.OL_ON, B.OL_RGB, B.OL_ALPHA, B.OL_IN, B.OL_KEEP, B.OL_HOLD, B.OL_CUT_OUT, B.OL_OFF, B.OL_OUT),
          ol['dash'], want_d)
    check('v7 outline (the connect): renewed from its 0 every %d frames, off at once at the punch %d (BPE 85 off at '
          'entry 4\'s 16); nothing after it' % (B.OL_KEEP, B.STRIKE), ol['connect'], want_c)
    check('v7: no ring effect left (v6\'s External_Graphic / Terminate_Graphic_Effect of 0x0341006A, now the wash\'s id) '
          'in either script, no PtcSupamarioTsOutline', [x for x in dash + conn if x[1] in ('External_Graphic',
                                                                                         'Terminate_Graphic_Effect')
                                                    and x[2][0] == 0x0341006A], [])

    def evs(pairs):
        d = {}
        for e_, p_ in pairs:
            d.setdefault(e_, []).append(p_)
        return d
    if olname not in ('Outline_Set', 'Outline_Shell'):     # (v9: Outline_Shell's tick is Outline_Set's, same params)
        print('     outline: %s: outline_sim (Outline_Set\'s tick) not run' % olname)
        return
    D = [(t, p_) for t, p_ in ol['dash']]
    C = [(t, p_) for t, p_ in ol['connect']]
    full = lambda ws, a, b_: all(x == 1.0 for x in ws[a:b_])     # noqa: E731
    # the whiff: effect frame = script frame
    ws = outline_sim(evs(D), 120)
    check('v7 outline (whiff, sim): off before %d, full from %d (in over %d) to the off at %d, gone by %d' % (
        B.OL_ON, B.OL_ON + B.OL_IN, B.OL_IN, B.OL_OFF, B.OL_OFF + B.OL_OUT),
          (max(ws[:B.OL_ON]), full(ws, B.OL_ON + B.OL_IN - 1, B.OL_OFF), max(ws[B.OL_OFF + B.OL_OUT - 1:])),
          (0.0, True, 0.0))
    # a full charge: the clock running on through the hold (the model's: Core Breaker v4's finding)
    for name, hold_clock in (('the script\'s clock running on', True),):
        ev, e_ = [], 0
        for s_ in range(0, B.OL_ON + B.CHARGE + 1) if hold_clock else range(0, B.OL_ON + 1):
            ev += [(e_, p_) for t, p_ in D if t == s_]
            e_ += 1
        if not hold_clock:
            e_ += B.CHARGE
        rs = e_
        for s_ in range(B.OL_ON, B.OL_OFF + 1):       # the restart at WIND_END: its frame's commands again
            ev += [(e_, p_) for t, p_ in D if t == s_]
            e_ += 1
        ws = outline_sim(evs(ev), e_ + 20)
        off = rs + B.OL_OFF - B.OL_ON
        check('v7 outline (a %d-frame charge, %s, sim): full from %d through the restart (%d) to the off (%d), gone %d '
              'later' % (B.CHARGE, name, B.OL_ON + B.OL_IN, rs, off, B.OL_OUT),
              (full(ws, B.OL_ON + B.OL_IN - 1, off), max(ws[off + B.OL_OUT - 1:])), (True, 0.0))
    # a catch at each frame of the box: the dash's commands to it, the freeze + retries, then the connect's
    bad = []
    for ck in range(B.HIT_FROM, B.HIT_LAST + int(B.HIT_LATE) + 1):
        for gap in (B.CATCH_FREEZE, B.CATCH_FREEZE + B.RETRY_N):
            ev = [(t, p_) for t, p_ in D if t <= ck]
            c0 = ck + gap + 1
            ev += [(c0 + t, p_) for t, p_ in C]
            ws = outline_sim(evs(ev), c0 + B.STRIKE + B.STRIKE_FREEZE + 10)
            if not (full(ws, B.OL_ON + B.OL_IN - 1, c0 + B.STRIKE) and max(ws[c0 + B.STRIKE:]) == 0.0):
                bad.append((ck, gap))
    check('v7 outline (a catch at every frame %d-%d of the box, %d / %d frames before the connect starts, sim): full '
          'without a dip to the punch, off at once there' % (B.HIT_FROM, B.HIT_LAST + int(B.HIT_LATE), B.CATCH_FREEZE,
                                                             B.CATCH_FREEZE + B.RETRY_N), bad, [])
    # a cut: the scripts stop at any frame (no more renewals): gone within OL_IN + OL_HOLD + OL_CUT_OUT
    worst = 0
    allev = D + [(B.OL_OFF + 10 + t, p_) for t, p_ in C]
    for cut in range(B.OL_ON, B.OL_OFF + 10 + B.STRIKE):
        ws = outline_sim(evs([(t, p_) for t, p_ in allev if t < cut]), cut + 80)
        last = max([k for k in range(len(ws)) if ws[k] > 0] or [cut])
        worst = max(worst, last - cut + 1)
    check('v7 outline (the move cut at any frame, sim: a hit, a ledge, any status change; the MSC can\'t send it): '
          'gone within %d frames (OL_IN + OL_HOLD + OL_CUT_OUT: its hold counts once it is full)' % (
              B.OL_IN + B.OL_HOLD + B.OL_CUT_OUT), worst <= B.OL_IN + B.OL_HOLD + B.OL_CUT_OUT, True)
    print('     outline: gone at most %d frames after a cut' % worst)


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
    check('specials: the connect box at %d in the dash only (TS_V_PH > 2.5), v2 with the point-blank box (ID 1, Part 0, '
          'at his middle): %s' % (B.HIT_FROM, (keys,)),
          ([c.params for c in dash if nm(c) in ('FRAME', 'Float_Var_Compare')], hb(dash)),
          ([[float(B.HIT_FROM)], [B.V_PH, 5, 2.5]],
           [(0, 0, 2.0, 0, 1, 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, B.CATCH_FREEZE, B.CATCH_FREEZE, 0.0, 0, 0, 0, 3, 1),
            (1, 0, 2.0, 0, 1, 0, B.HIT2_SIZE, B.HIT2_Z, B.HIT2_Y, B.CATCH_FREEZE, B.CATCH_FREEZE, 0.0, 0, 0, 0, 3, 1)]))
    r_ = B.HIT2_SIZE
    check('v2: the point-blank box covers his body from behind his centre to XV2\'s box (%.2f to %.2f ahead, no gap)' % (
        B.HIT2_Z - r_, B.HIT2_Z + r_), (B.HIT2_Z - r_ < 0.0, B.HIT2_Z + r_ >= B.HIT_Z - B.HIT_SIZE), (True, True))
    check('specialairs: the stopped time (v3: Stage_Freeze(1, %d) renewed every frame by a %d-pass loop, so a cut lets '
          'the stage go; off at the punch %d), no Screen_Tint in the scripts (the MSC\'s now), the punch\'s Part 1 record '
          'cleared, off at %d; the three punches (uncharged shieldable 16; fully charged unblockable, 22 on a fighter caught '
          'shielding, 16 else; v3: BKB %d, KBG %d)' % (B.STAGE_FREEZE_RENEW, B.STRIKE, B.STRIKE, B.STRIKE + 2,
                                                  B.STRIKE_HIT['BKB'], B.STRIKE_HIT['KBG']),
          ([(nm(c), c.params) for c in conn if nm(c) in ('FRAME', 'Hit_Log_Clear', 'Remove_All_Hitboxes', 'Stage_Freeze',
                                                         'Float_Var_Compare', 'Set_Loop', 'Goto', 'WAIT',
                                                         'Screen_Tint', 'End_Screen_Tint')], hb(conn)),
          ([('Set_Loop', [B.STRIKE]), ('Stage_Freeze', [1, B.STAGE_FREEZE_RENEW]), ('WAIT', [1.0]), ('Goto', [-5 & 0xFFFFFFFF]),
            ('FRAME', [float(B.STRIKE)]), ('Stage_Freeze', [0, 0]),
            ('Hit_Log_Clear', [1]), ('Float_Var_Compare', [B.V_CHG, 4, B.FULL]), ('Float_Var_Compare', [B.V_CHG, 5, B.FULL]),
            ('Float_Var_Compare', [B.V_SHV, 5, 0.5]), ('Float_Var_Compare', [B.V_SHV, 4, 0.5]),
            ('FRAME', [float(B.STRIKE + 2)]), ('Remove_All_Hitboxes', [])],
           [(0, 1, 16.0, 10, B.STRIKE_HIT['BKB'], B.STRIKE_HIT['KBG'], B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE, 0.0, 0, 0,
             1, 3, 1), (0, 1, 22.0, 10, B.STRIKE_HIT['BKB'], B.STRIKE_HIT['KBG'], B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE,
                        0.0, 0, 0, 1, 3, 0),
            (0, 1, 16.0, 10, B.STRIKE_HIT['BKB'], B.STRIKE_HIT['KBG'], B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE, 0.0, 0, 0,
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
    ext = [(nm(c), [round(x, 3) if isinstance(x, float) else x for x in c.params]) for c in f['effect'].script('specials')
           if nm(c) == 'External_Graphic' and c.params[0] == B.FX_E0H_ID]
    check('v4: effect 0\'s following part (Frt_CrgAuraH x%.1f) at frame 0 on the left elbow (bone %d), no offset / turn, '
          'the bone\'s place only (last word 0)' % (B.E0_FOLLOW[2], B.E0_FOLLOW[1]), ext,
          [('External_Graphic', [B.FX_E0H_ID, B.E0_FOLLOW[1], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                 round(B.E0_FOLLOW[2] * B.AURA_SIZE, 3), 0])])
    lt = {sc: [(nm(c), [round(x, 2) if isinstance(x, float) else x for x in c.params]) for c in f['effect'].script(sc)
               if nm(c) in ('Flash_Light_Effect', 'Change_Flash_Light_Color', 'Color_Overlay', 'Change_Overlay',
                            'Terminate_Overlays')] for sc in ('specials', 'specialairs')}
    check('v6: no body overlay / light at all (v4 / v5\'s FLASH tinted his whole body; in the user\'s v5 clip d8c96e8e it '
          'ran on to opaque white while the charge held the frame)', lt, {'specials': [], 'specialairs': []})
    outline_tests(f)
    print('     note: Stage_Freeze(1, ...) is the stage-only freeze with no flash from exe_v46z_camfx3 on (camera_effects_v3 /'
          ' v4); on exe_v46y_hold its On 1 also turned the scene white (the user\'s v3 clip ca068f15, 70-88)')
    cam = [(nm(c), [round(x, 4) if isinstance(x, float) else x for x in c.params]) for c in f['effect'].script('specialairs')
           if nm(c) in ('Effect_Camera', 'FRAME') or nm(c) == 'Terminate_Graphic_Effect' and c.params[0] == B.FX_GLASS_ID]
    check('v5 / v6: the glass (its shards) on the screen (Effect_Camera Mode 1, %g half heights a unit, Z %g, unslowed) '
          'from the connect\'s frame 0; v6: the white wash at the punch (%d: Mode 1, Z %g, size %g, unslowed, its own '
          'fade: INVERT_FX off; v7 INVERT_FX: the white fade quad at the punch + %d instead), the glass ended %d frames '
          'later (its shards breaking apart past the punch); the darkening on the camera only in the camera build '
          '(CAMERA_FX %s)' % (B.GLASS_SCREEN_SIZE, B.GLASS_SCREEN_Z, B.STRIKE, B.WASH_Z, B.WASH_SIZE, B.INV_END,
                              B.GLASS_BREAK, B.CAMERA_FX),
          [c for c in cam if c[0] != 'FRAME' or c[1][0] in (float(B.STRIKE), float(B.STRIKE + B.GLASS_BREAK))],
          ([('Effect_Camera', [B.FX_DARK_ID, 0.0, 0.0, B.DARK_Z, 0.0, 0.0, 0.0, B.DARK_SIZE, 1, B.STRIKE, 1])]
           if B.CAMERA_FX and not B.INVERT_FX else []) +
          [('Effect_Camera', [B.FX_GLASS_ID, 0.0, 0.0, B.GLASS_SCREEN_Z, 0.0, 0.0, 0.0, B.GLASS_SCREEN_SIZE, 1, 0, 1]),
           ('FRAME', [float(B.STRIKE)])] +
          ([('Effect_Camera', [B.FX_FADE_ID, 0.0, 0.0, B.WASH_Z, 0.0, 0.0, 0.0, B.WASH_SIZE, 1, 0, 1])] if B.INVERT_FX else
           [('Effect_Camera', [B.FX_WASH_ID, 0.0, 0.0, B.WASH_Z, 0.0, 0.0, 0.0, B.WASH_SIZE, 1, 0, 1])]) +
          [('FRAME', [float(B.STRIKE + B.GLASS_BREAK)]), ('Terminate_Graphic_Effect', [B.FX_GLASS_ID, 1, 1])])
    rr = lambda xs: [round(x, 3) if isinstance(x, float) else x for x in xs]     # noqa: E731
    inv = [(nm(c), rr(c.params)) for c in f['effect'].script('specialairs')
           if nm(c) in ('Screen_Invert',) or nm(c) == 'FRAME' and c.params[0] in (float(B.STRIKE),
                                                                                float(B.STRIKE + B.INV_END))]
    allinv = [c for p_ in f for s_ in ('specials', 'specialairs') for c in f[p_].script(s_) if nm(c) == 'Screen_Invert']
    check('v6 / v7 INVERT_FX %s: Screen_Invert (exe_v46z_inv) the stop\'s dark blue-grey negative at the connect\'s 0 '
          '(held %d, then its own end), the white negative at the punch (held %d at most), ended by the script at the '
          'punch + %d; only there' % (B.INVERT_FX, B.INV_STOP[2], B.INV_WHITE[2], B.INV_END),
          (inv, len(allinv)),
          (([('Screen_Invert', rr(B.INV_STOP)), ('FRAME', [float(B.STRIKE)]), ('Screen_Invert', rr(B.INV_WHITE)),
             ('FRAME', [float(B.STRIKE + B.INV_END)]), ('Screen_Invert', rr(B.INV_OFF))], 3) if B.INVERT_FX else
           ([('FRAME', [float(B.STRIKE)])], 0)))
    check('v7 (the user\'s Screen_Invert test: part strengths are grey): every Screen_Invert straight on / off (FadeIn / '
          'FadeOut 0), full strength', ({(c.params[1], c.params[3], c.params[4]) for c in allinv if c.params[0] == 1},
                                         {c.params[4] for c in allinv if c.params[0] == 0}),
          ({(1.0, 0, 0)}, {0}) if B.INVERT_FX else (set(), set()))
    seq = [(nm(c), c.params[0]) for c in f['effect'].script('specialairs') if nm(c) in ('Effect_Camera', 'Screen_Invert')]
    k_off = next((k for k, x in enumerate(seq) if x == ('Screen_Invert', 0)), None)
    check('v7: the white negative ends under the white fade quad: the quad started just before it, in the same frame',
          seq[k_off - 1] if k_off else None, ('Effect_Camera', B.FX_FADE_ID) if B.INVERT_FX else None)
    # the white negative's end (Python reference: screen_invert's f(x) on a grey picture): the contrast it shows each
    # frame, v6's 14-frame fade (through flat grey) against v7's cut under the quad
    br = B.INV_WHITE[6]
    v6c = [round(1 - w_ * (1 + br * 1.0), 2) for w_ in [1 - (k + 1) / 14.0 for k in range(14)]]
    flat6 = sum(1 for c_ in v6c if abs(c_) < 0.3)
    v7c = [round(1 - B.FADE_A * max(0.0, 1 - k / float(B.FADE_N)), 2) for k in range(B.FADE_N)]
    check('v7: after the white negative the picture\'s contrast only rises (%.2f -> 1) under the quad; v6\'s fade out '
          'over 14 had %d frames near flat grey (|contrast| < 0.3), v7 none' % (v7c[0], flat6),
          (all(b_ >= a_ for a_, b_ in zip(v7c, v7c[1:])), sum(1 for c_ in v7c if abs(c_) < 0.3), flat6 >= 4),
          (True, 0, True))
    gen = [nm(c) for p in f for s in ('specials', 'specialairs') for c in f[p].script(s)
           if 'article' in nm(c).lower() or 'reflect' in nm(c).lower()]
    check('no Cape left (no article, no reflector) in the side special\'s scripts', gen, [])
    other = []
    skip = {acmd.crc(n) for n in B.SCRIPT_NAMES}
    # Ultra Instinct's (later: tools/supamario_ui_test.py checks them): F.L.U.D.D.'s shoot slots
    skip |= {acmd.crc(n) for n in ('speciallwlight', 'speciallwheavy', 'specialairlwlight', 'specialairlwheavy',
                                   'specialairlwlight_c3')}    # (v7: the sway's custom slot)
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])]:
                other.append((p, hex(h)))
    check('every other script as Sledgehammer v5\'s build', other, [])


def effect_tests(out, sh_out):
    import json
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
    # v2 (item 9, user: "Sledgehammer seems less bright than before"): every set before Time Skip's (Sledgehammer's, the
    # God Fist's, Core Breaker's, Fake Death's, the Kamehameha's...) byte for byte as the Sledgehammer build's: each
    # emitter's bytes, its textures (decoded), the shaders, the efc entries
    diff = []
    for si in range(len(q.sets)):
        for k, em in enumerate(q.sets[si]['emitters']):
            if em['data'] is None:
                continue
            if p.emitter_bytes(si, k) != q.emitter_bytes(si, k):
                diff.append((q.set_name(si), k, 'bytes'))
                continue
            for slot in range(3):
                try:
                    a_, b_ = p.decode_texture(p.sets[si]['emitters'][k]['data'], slot), q.decode_texture(em['data'], slot)
                except Exception:
                    a_ = b_ = None
                if (a_ is None) != (b_ is None) or (a_ is not None and a_.tobytes() != b_.tobytes()):
                    diff.append((q.set_name(si), k, 'texture %d' % slot))
    sh_ = [i for i in range(q.shader_count()) if q.shader_binary(i) != p.shader_binary(i) or
           q.shader_entry(i) != p.shader_entry(i)]
    check('v2: every earlier set (Sledgehammer\'s %d, the God Fist\'s, Core Breaker\'s, Fake Death\'s, ...: %d sets) byte '
          'for byte as the Sledgehammer build\'s (emitters, textures), its shaders, its efc entries' % (
              sum(1 for i in range(len(q.sets)) if 'PtcSupamarioSh' in q.set_name(i)), len(q.sets)),
          (diff[:5], sh_[:5], e.entries[:len(qe.entries)] == qe.entries), ([], [], True))
    lod_si = e.entries[B.FX_LOD_ID & 0xFFFF][1] - 1
    shl = e.entries[B.SH_FX['hitlod'] & 0xFFFF][1] - 1
    import supamario_sledgehammer_build as SB
    pk = [(p.emitter_name(em['data']), round(SB.arc_peak(p, em['data']), 3)) for em in p.sets[lod_si]['emitters']
          if em['data'] is not None]
    pk_sh = [(q.emitter_name(em['data']), round(SB.arc_peak(q, em['data']), 3)) for em in q.sets[shl]['emitters']
             if em['data'] is not None]
    check('v2: Time Skip\'s own Btl_HitLOD (0x%08X, a copy of Sledgehammer\'s), its flash disc capped (%g), the rest by '
          'LOD_CAP; Sledgehammer\'s own unchanged' % (B.FX_LOD_ID, dict(B.LOD_CAP)['flash']),
          (p.set_name(lod_si), [n for n, _v in pk] == [n for n, _v in pk_sh],
           all(v_ <= dict(B.LOD_CAP)['flash'] + 1e-3 for n, v_ in pk if n.startswith('flash'))),
          ('PtcSupamarioTsBtl_HitLOD', True, True))
    # v4: XV2's skill effects 11 and 0 (1350_HIK_FRT.eepk)
    rep4 = json.load(open(os.path.join(out, 'timeskip.json')))['fx']
    sis = {k: e.entries[i & 0xFFFF][1] - 1 for k, i in B.FX_E11_IDS.items()}
    ds = {k: [em['data'] for em in p.sets[si]['emitters'] if em['data'] is not None] for k, si in sis.items()}
    names = [p.emitter_name(d) for k in ('hit', 'hit_2') for d in ds[k]]
    pk = {p.emitter_name(d): round(SB.arc_peak(p, d), 3) for k in ('hit', 'hit_2') for d in ds[k]}
    capped = all(pk[n] <= next(c for pre, c in B.E11_CAP if n.startswith(pre)) + 1e-3 for n in pk
                 if any(n.startswith(pre) for pre, _c in B.E11_CAP))
    check('v4: effect 11 (Frt_Hit.emp: %d emissions, every one converted) in %s / %s, its halos (HALO_ALPHA) in %s / %s; '
          'world-placed (follow none), each capped by E11_CAP' % (
              len(names), *('0x%08X' % B.FX_E11_IDS[k] for k in ('hit', 'hit_2', 'hit_h', 'hit_2h'))),
          ({k: p.set_name(si) for k, si in sis.items()}, len(names), rep4['e11']['skipped'],
           {bytes(d[0x310:0x314]).hex() for k in ds for d in ds[k]}, capped),
          ({'hit': 'PtcSupamarioTsFrt_Hit', 'hit_2': 'PtcSupamarioTsFrt_Hit_2', 'hit_h': 'PtcSupamarioTsFrt_HitH',
            'hit_2h': 'PtcSupamarioTsFrt_Hit_2H'}, 31, [], {'00000001'}, True))
    import numpy as np
    import xv2_to_ptcl as X
    fwd = []
    for d in ds['hit']:
        if p.emitter_name(d).startswith('line_add') and p.field(d, 'volume_type') == 0:
            m = X.euler_matrix([float(np.degrees(v_)) for v_ in p.field(d, 'emitter_rotation')])
            fwd.append([round(float(x_), 3) for x_ in m @ np.array(p.field(d, 'emit_direction'), float)])
    check('v4: effect 11 turned so the hand\'s +Z (the punch: its speed lines run from the fist forward, the clip) is the '
          'set\'s +X: the speed lines emitted toward -X (Smash draws a streak back along its motion, Line_Hit\'s line '
          'ahead of the fist)', fwd, [[-1.0, 0.0, 0.0]] * len(fwd))
    si = e.entries[B.FX_AURA_ID & 0xFFFF][1] - 1
    dw = [em['data'] for em in p.sets[si]['emitters'] if em['data'] is not None]
    hip, foot = rep4['aura']['emitters'][:3:2]
    tr_ = {p.emitter_name(d): [round(x_, 2) for x_ in p.field(d, 'emitter_translation')] for d in dw}
    check('v4: effect 0\'s world parts (Frt_CrgAura at b_C_Pelvis 0.3 m down and at b_R_Foot, Frt_CrgAuraB at b_C_Pelvis: '
          '0x%08X): ConeExtrude stripes as streaks (type 3), rising, follow none; v6: lavender (blue > red > green) at %g '
          '(v4 / v5: 0.32, CrgAuraB pale cyan); + their halos; the foot\'s part behind (SpecialS frame 0: RFootJ behind '
          'TransN)' % (B.FX_AURA_ID, B.E0_CAP6),
          (p.set_name(si), [p.emitter_name(d) for d in dw][:3], {p.field(d, 'particle_type') for d in dw},
           {tuple(p.field(d, 'emit_direction')) for d in dw}, {bytes(d[0x310:0x314]).hex() for d in dw},
           all((abs(SB.arc_peak(p, d) - B.E0_CAP6) < 1e-3 if p.field(d, 'blend_type') == 1 else
                p.field(d, 'alpha_diff21') <= B.E0_B_ALPHA + 1e-3 and min(p.color_keys(d, 0)[0][:3]) > 0.4) and
               p.color_keys(d, 0)[0][2] > p.color_keys(d, 0)[0][0] > p.color_keys(d, 0)[0][1] for d in dw[:3]),
           len(dw), tr_[foot][0] < 0.0),
          ('PtcSupamarioTsFrt_CrgAura', ['CrgAura_HipN', 'CrgAuraB_HipN', 'CrgAura_RFootJ'], {3}, {(0.0, 1.0, 0.0)},
           {'00000001'}, True, 6, True))
    si = e.entries[B.FX_E0H_ID & 0xFFFF][1] - 1
    dh = [em['data'] for em in p.sets[si]['emitters'] if em['data'] is not None]
    check('v4: effect 0\'s following part (Frt_CrgAuraH, 0x%08X): its streak + halo, following (follow 0: XV2\'s '
          'PositionUpdate)' % B.FX_E0H_ID,
          (p.set_name(si), len(dh), {bytes(d[0x310:0x314]).hex() for d in dh}),
          ('PtcSupamarioTsFrt_CrgAuraH', 2, {'00000000'}))
    gi = e.entries[B.FX_GLASS_ID & 0xFFFF]
    mdir = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario', 'model', 'EffSupamarioTsDmgGrs2')
    import nut
    nd_, tx_ = nut.load(os.path.join(mdir, 'model.nut'))
    img_ = nut.decode(nd_, tx_[0]).astype(float) / 255.0
    lum = img_[..., 3] if B.INVERT_FX else img_[..., :3].max(axis=2)     # v6 INVERT_FX: drawn pre-inverted, black
    if B.INVERT_FX:
        import nud as nud_
        check('v6 INVERT_FX: the glass drawn pre-inverted (Screen_Invert turns it negative): alpha-blended (src 5 / dst 1), '
              'black, the cracks / panes in the alpha',
              ({(mt.src, mt.dst) for m in nud_.read(os.path.join(mdir, 'model.nud')) for pg in m.polygons
                for mt in pg.materials}, float(img_[..., :3].max())), ({(5, 1)}, 0.0))
    gl_ = json.load(open(os.path.join(out, 'timeskip.json')))['fx']['glass']
    sh_ = gl_.get('sheens') or [0.0]
    check('v5 / v6: the glass clear: its texture the shards\' outlines (%d lines) in light blue-white (blue >= red), no '
          'yellow (v2-v4: the refraction map drawn as colour); v6: each of the %d shards\' panes its own faint sheen '
          '(%.2f-%.2f: see-through, additive; the texture\'s mean under 0.2), the cracks bright' % (
              gl_['cracks'], len(sh_), min(sh_), max(sh_)),
          (bool((img_[..., 2] >= img_[..., 0] - 0.02).all()), float(lum.mean()) < 0.2, float(lum.max()) > 0.8,
           len(sh_) > 20, max(sh_) - min(sh_) > 0.08, max(sh_) <= B.GLASS_SHEEN[1] + 1e-6),
          (True, True, True, True, True, True))
    # v8 (the user's v7 clip 869ac5f5, 156-171: a white square ~64% of the screen wide, turning, after the punch)
    for nm_, fid, size_ in (('fade', B.FX_FADE_ID, B.WASH_SIZE), ('wash', B.FX_WASH_ID, B.WASH_SIZE),
                            ('dark', B.FX_DARK_ID, B.DARK_SIZE)):
        si = e.entries[fid & 0xFFFF][1] - 1
        for d in [em['data'] for em in p.sets[si]['emitters'] if em['data'] is not None]:
            rot = [p.field(d, k) for k in ('rotation_init', 'rotation_random', 'rotation_velocity',
                                           'rotation_velocity_random')]
            sc = p.field(d, 'scale')
            wide = min(sc) * size_ / 2.0
            check('v8 the %s quad (0x%08X, %s) fills the screen and doesn\'t turn: no rotation of any kind (init, random, '
                  'velocity, random velocity), scale %g (%.2f screen heights at Mode 1 Size %g: over a 16:9 screen\'s '
                  '1.78), no scale / key animation, follow 0, a billboard' % (
                      nm_, fid, p.set_name(si), B.QUAD_W, wide, size_),
                  (all(x == 0.0 for r in rot for x in r), wide > 1.9, list(p.field(d, 'scale_diff21')),
                   list(p.field(d, 'scale_diff32')), p.field(d, 'keyanim_size'), bytes(d[0x310:0x314]).hex(),
                   p.field(d, 'particle_type'), p.field(d, 'camera_offset')),
                  (True, True, [0.0, 0.0], [0.0, 0.0], 0, '00000000', 0, 0.0))
    check('v7: no outline ring set left in the bank (v6\'s PtcSupamarioTsOutline: the outline is Outline_Set)',
          [p.set_name(i) for i in range(len(p.sets)) if p.set_name(i) == 'PtcSupamarioTsOutline'], [])
    for key, fid in (('fade', B.FX_FADE_ID), ('wash', B.FX_WASH_ID)):
        si = e.entries[fid & 0xFFFF][1] - 1
        ds = [em['data'] for em in p.sets[si]['emitters'] if em['data'] is not None]
        if key == 'fade':
            d = ds[0]
            check('v7 the white fade quad (0x%08X): one alpha-blended white quad, %d real frames, alpha %g straight down to '
                  '0 (no fade in)' % (fid, B.FADE_N, B.FADE_A),
                  (p.set_name(si), len(ds), p.field(d, 'blend_type'), p.field(d, 'ptcl_life'),
                   [round(p.field(d, k), 3) for k in ('alpha_init', 'alpha_diff21', 'alpha_diff32', 'alpha_section1',
                                                       'alpha_section2')]),
                  ('PtcSupamarioTsFade', 1, 0, B.FADE_N, [B.FADE_A, 0.0, -B.FADE_A, 0.0, 0.0]))
        else:
            got = [(p.field(d, 'blend_type'), p.field(d, 'ptcl_life'), round(p.field(d, 'alpha_diff21'), 3),
                    round(p.field(d, 'alpha_section1') * p.field(d, 'ptcl_life'), 2),
                    round((1 - p.field(d, 'alpha_section2')) * p.field(d, 'ptcl_life'), 2)) for d in ds]
            check('v6 the wash (0x%08X): alpha-blended white quads: the wash %g in %d, held, out over %d of %d real frames; '
                  'the punch\'s flash %g out over %d' % (fid, B.WASH_A, B.WASH_IN, B.WASH_OUT, B.WASH_LIFE, B.WASH_FLASH,
                                                         B.WASH_FLASH_N - 1),
                  (p.set_name(si), got), ('PtcSupamarioTsWash', [(0, B.WASH_LIFE, B.WASH_A, float(B.WASH_IN),
                                                                 float(B.WASH_OUT)),
                                                                (0, B.WASH_FLASH_N, B.WASH_FLASH, 1.0,
                                                                 float(B.WASH_FLASH_N - 1))]))
    check('v2: the glass (BTL_CMN 108, HIT_DmgGrs2) a model entry (0x%08X), its folder with model / texture / '
          'animation / material animation' % B.FX_GLASS_ID,
          (gi[1], sorted(f for f in os.listdir(mdir)) if os.path.isdir(mdir) else None),
          (0, ['model.mta', 'model.nud', 'model.nut', 'model.omo', 'model.vbn', 'model.xmb']))
    rep = json.load(open(os.path.join(out, 'timeskip.json')))['fx']
    conv = sum(len(v['emitters']) for v in rep['sets'].values())
    check('its fake-glow halos (HALO_ALPHA %g) in its own sets: %d (no room for %s)' % (
        rep['halos'].get('alpha', 0), rep['halos'].get('glowing', 0), rep['halos'].get('no_room')),
          n_em - conv, rep['halos'].get('glowing', 0))


def motion_tests(out, sh_out):
    for part in ('main', 'mariopt1', 'lhand', 'rhand'):
        new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        old = dict(omo.pac_read(os.path.join(sh_out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        diff = sorted(n for n in new if new[n] != old.get(n) and not any(  # Ultra Instinct's (later: its own test)
            n.endswith('D03' + m) for m in ('SpecialLwLight.omo', 'SpecialLwHeavy.omo', 'SpecialAirLwLight.omo',
                                    'SpecialAirLwHeavy.omo')))
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
    tracking_tests(path)
    script_tests(a[0], a[1])
    effect_tests(a[0], a[1])
    brightness_tests(a[0])
    motion_tests(a[0], a[1])
    sound_tests(a[0])
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
