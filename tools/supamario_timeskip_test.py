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
- his speed: energy 3 (world X, KineticModule 0x11) moves him each frame he isn't frozen; in the air energy 1's speed
  plus its acceleration (gravity 0.09 when on), a fall at most 1.5; a floor ends the air (the situation changes);
- the connect box (bone 0 + (HIT_Z, HIT_Y), HIT_SIZE) hits a fighter whose body (its feet to 10 above, 3.5 wide) it
  touches, once a fighter (its Part 0 record): a shield (0x1C) sets the shield bit only; intangible (body >= 2): no
  contact; invincible (1) or countering: the hurtbox bit, no damage, no reaction; armor: its damage, no reaction;
  else 2%, both frozen CATCH_FREEZE, Damage (0x45 / 0x46). The strike (on SpecialAirS from STRIKE to STRIKE + 1) on
  the held victim: 14%, both frozen STRIKE_FREEZE, launched at 10 degrees (knockback x 0.03 a frame), DamageFly
  (0x47). Target 12's offsets read the fighter last hit.
"""
import math
import os
import struct
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
        for k, v in kw.items():
            setattr(self, k, v)


class Game(SHT.Game):
    def __init__(self, fighters=(), held=None, air=False, y=0.0, stick_x=None, floor=None):
        SHT.Game.__init__(self, fighters=fighters, held=held, y=y)
        self.air = air
        self.floor = floor if floor is not None else (None if air else y)
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

    def fvar(self, v):
        if v == 0x0F000043:
            return 1.0 if self.hitstop > 0 else 0.0
        if v == 0x0F0000A2:
            return float(B.ST_SIDE) if self.status is None else 0.0
        return SHT.Game.fvar(self, v)

    def setvar(self, v, val):
        if v == 0x0F00011C:
            self.inv.append((self.n, val))
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
        SHT.Game.setvar(self, v, val)

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x10 and a and a[0] == 0x11 and a[1] == 3:
            self.vx = f(a[2])
            return 0
        if sid == 0x10 and a and a[0] == 0x11 and a[1] == 2:
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
            hx, hy, r = self.x + self.face * B.HIT_Z, self.y + B.HIT_Y, B.HIT_SIZE
        else:
            hx, hy, r = self.x + self.face * B.STRIKE_Z, self.y + B.STRIKE_Y, B.STRIKE_SIZE
        for v in self.fighters.values():
            if getattr(v, 'rec', None) == self.box:
                continue
            dx = max(0.0, abs(v.x - hx) - 3.5)
            dy = max(0.0, max(v.y - hy, hy - (v.y + 10.0)))
            if dx * dx + dy * dy > r * r:
                continue
            if getattr(v, 'body', 0) >= 2:
                continue
            v.rec = self.box
            if v.status == 0x1C:
                self.hitflag |= 4
                continue
            self.hit = v
            self.hitflag |= 2
            v.hit_at = self.n
            hit, stop = (B.CATCH, B.CATCH_FREEZE) if self.box == 'catch' else (B.STRIKE_HIT, B.STRIKE_FREEZE)
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
            return

    def physics(self):
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        self.x += self.vx
        if self.air:
            self.vy += self.acc
            if self.acc != 0.0 and self.vy < -MAX_FALL:
                self.vy = -MAX_FALL
            self.y += self.vy
            if self.floor is not None and self.y <= self.floor:
                self.y, self.air, self.vy = self.floor, False, 0.0
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
            vm.call(fn(vm, 'sh_tick'))
            vm.call(fn(vm, 'ts_tick'))
            for v in g.fighters.values():
                v.step(k)
            g.physics()
            continue
        sit = 2 if g.air else 0
        vm.g[18], vm.g[19] = sit, prev_sit
        prev_sit = sit
        if tick:
            tick(g, k)
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


def msc_tests(path, root):
    want_un, want_ch = B.travel(False, root), B.travel(True, root)
    # 1. a tap on the ground: the dash and the stop, no victim
    g = Game()
    tr, vm = run(path, g)
    end = tr[-1]
    check('ground tap: SpecialS from frame 0, never restarted (no charge held)', [m for m in g.motions if m[1] != 'set'],
          [(0, 0x219, 0.0)])
    check('ground tap: the dash at frame %d (phase 3), the stop (4) at %d, Wait (0) at %d' % (
        B.WIND_END, B.MOVE_FROM + B.MOVE_N, B.DASH_END),
          (ph_at(tr, B.WIND_END), ph_at(tr, B.MOVE_FROM + B.MOVE_N), end[0], end[5]), (3.0, 4.0, B.DASH_END, 0))
    check('ground tap: the connect box out at %d (the script, phase 3), taken off at %d (2 before the movement ends)' % (
        B.HIT_FROM, B.MOVE_FROM + B.MOVE_N - 2), ('catch' in g.fired, g.removed[0] if g.removed else None),
          (True, B.MOVE_FROM + B.MOVE_N - 2))
    near('ground tap: his travel = the root\'s + XV2\'s Movement (29 frames of 3.53 less 0.015 a frame)', end[3], want_un,
         0.6)
    check('ground tap: Hazure (the whiff) once, at the movement\'s end (%d)' % (B.MOVE_FROM + B.MOVE_N),
          [(n, s) for n, w, s in g.sounds if w == 'play'], [(B.MOVE_FROM + B.MOVE_N, B.SE_IDS['ts_hazure'])])
    check('ground tap: no invincibility, the air use not taken', (g.inv, g.vars.get(B.V_USED, 0.0)), ([], 0.0))
    # 2. in the air: no gravity through the dash, Fall at the movement's end, the use taken
    g = Game(air=True, y=50.0)
    tr, vm = run(path, g)
    end = tr[-1]
    check('air tap: Fall (0xE, not FallSpecial) at the movement\'s end (%d)' % (B.MOVE_FROM + B.MOVE_N),
          (end[0], end[5]), (B.MOVE_FROM + B.MOVE_N, 0xE))
    check('air tap: his height kept through the dash (no gravity, no drift)', max(abs(t[4] - 50.0) for t in tr) < 1e-3,
          True)
    want_air = round(B.travel(False) + sum(root[:B.MOVE_FROM + B.MOVE_N]), 1)
    near('air tap: the root\'s travel to the movement\'s end + the Movement (no stop: Fall there)', end[3], want_air,
         0.6)
    check('air tap: his gravity back at the end, the air use taken; ts_can_side refuses a second in the air',
          (round(g.acc, 4), g.vars.get(B.V_USED), vm.call(fn(vm, 'ts_can_side'))), (-GRAVITY, 1.0, 0))
    vm.g[18] = 0
    vm.call(fn(vm, 'ts_tick'))
    check('air tap: landed (out of the move): the use back', (g.vars.get(B.V_USED), vm.call(fn(vm, 'ts_can_side'))),
          (0.0, 1))
    # 3. a short charge (10 frames): the motion restarted at the charge's frame, the uncharged dash
    g = Game(held=lambda n: n < B.WIND_END + 10)
    tr, vm = run(path, g)
    check('short charge: held at %d, restarted there at %d (the scripts\' clock), uncharged' % (
        B.WIND_END, B.WIND_END + 10), ([m for m in g.motions if m[1] != 'set'], g.vars.get(B.V_CHG)),
          ([(0, 0x219, 0.0), (B.WIND_END + 10, 0x219, float(B.WIND_END))], 0.0))
    near('short charge: the uncharged travel', tr[-1][3], want_un, 0.6)
    check('short charge: the box from the restart\'s frame %d (%d after it)' % (
        B.HIT_FROM, B.HIT_FROM - B.WIND_END), first(tr, lambda t: t[1] == 0x219 and 'catch' in g.fired) is not None and
        g.removed[0], B.WIND_END + 10 + B.MOVE_FROM + B.MOVE_N - 2 - B.WIND_END)
    # 4. a full charge: the long dash (the pose looped twice)
    g = Game(held=lambda n: True)
    tr, vm = run(path, g, frames=400)
    loops = [n for n, m, fr in g.motions if m == 'set' and fr == float(B.LOOP_FROM)]
    t0 = B.WIND_END + B.CHARGE
    check('full charge: the charged dash after %d frames held (restart at %d), the pose looped back to %d twice' % (
        B.CHARGE, t0, B.LOOP_FROM), (g.vars.get(B.V_CHG, 0.0) >= B.CHARGE - 0.5,
                                     [m for m in g.motions if m[1] != 'set'][-1], len(loops)),
          (True, (t0 - 1, 0x219, float(B.WIND_END)), 2))
    s0 = t0 - 1 - B.WIND_END
    check('full charge: the box off at movement frame %d, the stop at %d, Wait at %d' % (
        B.MOVE_N_CH - 2, s0 + B.MOVE_FROM + B.MOVE_N_CH, s0 + B.DASH_END + 2 * B.LOOP_LEN),
          (g.removed[0], first(tr, lambda t: t[6] == 4.0)[0], tr[-1][0], tr[-1][5]),
          (s0 + B.MOVE_FROM + B.MOVE_N_CH - 2, s0 + B.MOVE_FROM + B.MOVE_N_CH, s0 + B.DASH_END + 2 * B.LOOP_LEN, 0))
    near('full charge: the charged travel (79 movement frames)', tr[-1][3], want_ch, 0.6)
    # 5. a fighter ahead on the ground: caught, held, struck, launched
    caught_tests(path, air=False)
    caught_tests(path, air=True)
    # 6. refusals
    for name, kw, catches in (('shielding', dict(shield=True), False), ('invincible', dict(body=1), False),
                              ('countering', dict(counter=True), False), ('super armor', dict(armor=1), False),
                              ('heavy armor', dict(armor=2, armor_thr=50.0), False), ('intangible', dict(body=2), False),
                              ('lying (DownWait)', dict(status=0x50), True)):
        v = V(2, 30.0, **{k: x for k, x in kw.items() if k != 'status'})
        if 'status' in kw:
            v.status = kw['status']
        g = Game(fighters=[v])
        tr, vm = run(path, g)
        got = any(t[1] == 0x21D for t in tr)
        check('%s fighter ahead: %s' % (name, 'caught' if catches else 'not caught, the dash goes on to its end'),
              (got, tr[-1][5] if not catches else None, [w for w in v.__dict__.get('wlog', []) if w[1] == 'input'] == []
               if not catches else True), (catches, 0 if not catches else None, True))
        if name.startswith('lying'):
            check('lying: put into the hold\'s Damage (0x46) at the catch', [w for w in v.wlog if w[1] == 'status'][:1],
                  [(first(tr, lambda t: t[1] == 0x21D)[0], 'status', 70.0)])
    # an invincible fighter in front, another behind it: the second is caught
    v1, v2 = V(2, 20.0, body=1), V(3, 50.0)
    g = Game(fighters=[v1, v2])
    tr, vm = run(path, g)
    check('an invincible fighter, then another: the second caught (slot 3)', g.vars.get(B.V_SLOT), -1.0)
    check('  (its hold written on slot 3 only)', sorted({s for _n, s, _x in g.holds}), [3])
    # 7. B-reverse
    for kk, want in ((0, 1), (3, 1), (4, 0)):
        g = Game(stick_x=lambda n, kk=kk: -1.0 if n == kk else 0.0)
        run(path, g, frames=10)
        check('B-reverse: the stick back on frame %d turns him %d time(s); his speed not turned' % (kk, want),
              len(g.turns), want)
    g = Game(stick_x=lambda n: -0.4)
    run(path, g, frames=10)
    check('B-reverse: a weak stick back (0.4) doesn\'t', len(g.turns), 0)
    # 8. cut in the hold / the victim KO'd
    v = V(2, 30.0)
    g = Game(fighters=[v])
    catch_k = [None]

    def cut_tick(g_, k):
        if catch_k[0] is None and g_.kind == 0x21D:
            catch_k[0] = k
    tr, vm = run(path, g, frames=200, tick=cut_tick, cut_at=None)
    ck = catch_k[0]
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


def caught_tests(path, air):
    y = 40.0 if air else 0.0
    v = V(2, 30.0, y=y, air=air)
    g = Game(fighters=[v], air=air, y=y)
    tr, vm = run(path, g, frames=200)
    tag = 'air' if air else 'ground'
    c = first(tr, lambda t: t[1] == 0x21D)
    check('%s catch: the connect motion (SpecialAirS from 0) on a real hit, slot 2' % tag,
          (c is not None, [m for m in g.motions if m[1] == 0x21D][:1] == [(c[0], 0x21D, 0.0)] if c else None),
          (True, True))
    if c is None:
        return
    ck = c[0] - 1                                       # the connect box hit the frame before the catch
    held = [x for n, s, x in g.holds if s == 2]
    hk = sorted({n for n, s, x in g.holds if s == 2})
    check('%s: held %.2f in front every frame from the catch to the strike\'s frame' % (tag, B.HOLD_X),
          (set(held), hk[0], hk[-1]), ({B.HOLD_X}, ck + 1, ck + B.CATCH_FREEZE + B.STRIKE - 1))
    check('%s: the victim\'s controller off from the catch, back at the strike (and its stage collision)' % tag,
          ([w[0] for w in v.wlog if w[1] == 'input'][:1], [w[2] for w in v.wlog if w[1] == 'input'][-1],
           v.ground[-1][1]), ([ck + 1], 0.0, 5.0))
    sk = ck + B.CATCH_FREEZE + B.STRIKE
    check('%s: struck at %d: 2 + 14%%, launched (DamageFly), XV2\'s hit look the next frame (Btl_HitLOD / Btl_HitL / the '
          'sweat) and Hit_TmLck once' % (tag, sk),
          (round(v.pct, 3), v.hit_at, [(n, i) for n, i, _x, _y, _s in g.fx],
           [(n, s) for n, w, s in g.sounds if w == 'play']),
          (16.0, sk, [(sk + 1, B.SH_FX['hitlod']), (sk + 1, B.FX_IDS['hitl']), (sk + 1, B.FX_IDS['hitl_2']),
                      (sk + 1, B.SH_FX['sweat'])],
           [(sk + 1, B.SE_IDS['ts_hit'])]))
    sizes = [s for _n, _i, _x, _y, s in g.fx]
    check('%s: the hit look\'s sizes (x%.2f the EEPK\'s 1.5 / 0.8 / 2.0)' % (tag, B.FX_SCALE), sizes,
          [round(B.EEPK_SCALE[e] * B.FX_SCALE, 3) for e in ('Btl_HitLOD.emp', 'Btl_HitL.emp', 'Btl_HitL.emp',
                                                             'Btl_Sweat00.emp')])
    inv = sorted({n for n, _v in g.inv})
    fz = sk + B.STRIKE_FREEZE
    check('%s: invincible from the catch through the strike\'s freeze (renewed by 2, 1 on the first frame after)' % tag,
          (inv[0], inv[-1], [val for n, val in g.inv if n == inv[-1]]), (ck + 1, fz, [1.0]))
    end = tr[-1]
    check('%s: the connect ends at its last frame (%d), %s' % (tag, B.CONNECT_END, 'Fall' if air else 'Wait'),
          (end[0], end[5]), (fz + B.CONNECT_END - B.STRIKE, 0xE if air else 0))
    if air:
        check('air: held in place through the hold and the freeze, his gravity from the motion\'s next frame',
              (max(abs(t[4] - y) for t in tr if t[0] <= fz), round(g.acc, 4)), (0.0, -GRAVITY))


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
    check('specialairs: the strike at %d (its Part 1 record cleared first), off at %d' % (B.STRIKE, B.STRIKE + 2),
          ([(nm(c), c.params) for c in conn if nm(c) in ('FRAME', 'Hit_Log_Clear', 'Remove_All_Hitboxes')], hb(conn)),
          ([('FRAME', [float(B.STRIKE)]), ('Hit_Log_Clear', [1]), ('FRAME', [float(B.STRIKE + 2)]),
            ('Remove_All_Hitboxes', [])],
           [(0, 1, 14.0, 10, 60, 75, B.STRIKE_SIZE, B.STRIKE_Z, B.STRIKE_Y, B.STRIKE_FREEZE, B.STRIKE_FREEZE, 0.0, 0, 0,
             1, 3, 1)]))
    snd = [(nm(c), c.params) for s in ('specials', 'specialairs') for c in f['sound'].script(s)
           if nm(c) in ('FRAME', 'Sound_Effect', 'Float_Var_Compare')]
    check('sounds: Basa at 6 (wind-up only), Dash at %d (dash only); TimeStop at 0, PumchiFuri at 8, CharaAway at %d' % (
        B.MOVE_FROM, B.SND['away']), snd,
          [('FRAME', [6.0]), ('Float_Var_Compare', [B.V_PH, 4, 1.5]), ('Sound_Effect', [B.SE_IDS['ts_basa']]),
           ('FRAME', [float(B.MOVE_FROM)]), ('Float_Var_Compare', [B.V_PH, 5, 2.5]),
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
