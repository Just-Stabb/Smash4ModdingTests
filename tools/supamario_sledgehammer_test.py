#!/usr/bin/env python3
"""Sledgehammer (Supamario's air down special) offline checks: the compiled MSC (sh_* through the down special's
status functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built scripts,
motions, effects and sounds.

  python3 -I tools/supamario_sledgehammer_test.py BUILD_OUT_DIR BASE_SUPAMARIO_DIR

BUILD_OUT_DIR: tools/supamario_sledgehammer_build.py's OUT_DIR; BASE_SUPAMARIO_DIR: the user's fighter/supamario.

The model of the game (its assumptions): the status's main (func_2265) on its first frame, then sh_loop every frame
(also in his hitstop); func_2282 at a status change; the motion advances by its rate (MotionModule 4) except in his
hitstop; 0x239 has 13 frames (it stops at its last), 0x23D 65 (it loops); his gravity energy: its speed (KineticModule
0x11 on energy 1) plus its acceleration (0xF; -0.09 his own) each frame, a fall clamped at 1.5 while it has one; the
special button's held state and global24's presses from a schedule; the game script's hitbox (bone 0 + (HIT_Z,
HIT_Y), HIT_SIZE; uncharged frames 16-19, charged 15-18, sh_chg read when it comes out) hits a fighter whose body (its
feet to 10 above, 3.5 wide) it touches: both frozen the hit's hitstop, the fighter launched straight down at its
knockback x 0.03 (decaying 0.051 a frame), its hitstun 0.4 x it (+ the hitbox's added frames), DamageAir; a shield
(status 0x1C) only sets the shield bit. Target 12's offset variables (ATKHIT_OFFSET_X / _Y) read the hit fighter
once it is hit.
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
import supamario_sledgehammer_build as B  # noqa: E402
import supamario_sledgehammer_anim as A  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


GRAVITY, MAX_FALL = 0.09, 1.5
FF, FF_SPEED, FF_STICK, FF_WINDOW = 0x21000001, 2.4, -0.66, 4      # v2: the fast fall (flag, speed, stick, flick age)
LEN = {0x239: A.START_FRAMES, 0x23D: A.HOLD_FRAMES}
UP, SIDE, NEUTRAL, DOWN = 0x4000, 0x2000, 0x1000, 0x8000
MOTION_FRAMES = {0x3A: 16, 0x2D: 31}    # v2: LandingLight / LandingFallSpecial (his main.pac)


class Game(FT.Game):
    def __init__(self, fighters=(), held=None, press=None, y=100.0, vy=0.0):
        FT.Game.__init__(self, fighters=fighters, held=held)
        self.air = True
        self.y, self.vy = y, vy
        self.acc = -GRAVITY
        self.rate = 1.0
        self.press = press or {}
        self.sounds = []                # (n, 'play' / 'stop', id)
        self.fx = []                    # (n, id, x, y, size) EffectModule 3 (world)
        self.acc_log = []               # (n, acceleration) KineticModule 0xF energy 1
        self.vy_log = []                # (n, speed) KineticModule 0x11 energy 1
        self.rates = []                 # (n, rate)
        self.hit = None                 # the fighter his attack hit
        self.floor = None               # a floor's height under him (landing)
        self.flags = set()              # v2: WorkModule flags (0x21000001: fast falling)
        self.stick = None               # v2: n -> (stick Y, frames since its flick) for func_77's globals 32 / 47
        self.ff_log = []                # v2: (n, on) the fast-fall flag's changes

    def fvar(self, v):
        if v in (0x20000c2, 0x20000ca, 0x20000cb):      # v2: the common shield params (max, damage x, + base)
            return {0x20000c2: 50.0, 0x20000ca: 1.19, 0x20000cb: 0.0}[v]
        for s_ in range(1, 9):
            t_ = s_ + 2
            f_ = self.fighters.get(s_)
            if f_ is not None and v == 0x0F00011A + 0x20 * t_:
                return getattr(f_, 'shield_hp', 50.0)
        if v in (0x0F0002CD, 0x0F0002CE):              # Target 12 (ATKHIT_OFFSET_X / _Y): the fighter hit, if any
            if self.hit is None:
                return 0.0
            return (self.hit.x - self.x) * self.face if v == 0x0F0002CD else self.hit.y - self.y
        if v == 0x0F000002:
            return 0.0
        if v == 0x3000018:                              # his fighter_param Gravity
            return GRAVITY
        if v == 0x3000019:
            return MAX_FALL
        if v == 0x300001b:                              # v2: his fast-fall speed (Mario's 2.4)
            return FF_SPEED
        if v == 0x2000046:                              # v2: the stick's fast-fall threshold
            return FF_STICK
        return FT.Game.fvar(self, v)

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x16 and a and a[0] in (0x2710, 0x2711) and len(a) == 2:      # v2: flags on / off
            if a[1] == FF and ((a[0] == 0x2710) != (FF in self.flags)):
                self.ff_log.append((self.n, a[0] == 0x2710))
            (self.flags.add if a[0] == 0x2710 else self.flags.discard)(a[1])
            return 0
        if sid == 0x16 and a and a[0] == 0x10 and len(a) == 2:
            return 1 if a[1] in self.flags else 0
        if sid == 0x16 and a and a[0] == 0x6 and len(a) == 2 and a[1] == 0x12000047:
            return FF_WINDOW
        if sid == 0x11 and len(a) == 2 and a[1] == 1 and a[0] in (0x1, 0xB):      # his gravity energy's speed
            return R.f2i(self.vy)
        if sid == 0x10 and a and a[0] in (0x4, 0x5) and len(a) == 2 and a[1] == 2:
            return 1 if a[0] == 0x4 else 0                                       # energy 2 (air control) on
        if sid == 0x10 and a and a[0] == 0xF and a[1] == 1:
            self.acc = f(a[2])
            self.acc_log.append((self.n, round(self.acc, 4)))
            return 0
        if sid == 0x10 and a and a[0] == 0x11 and a[1] == 1:
            self.vy = f(a[2])
            self.vy_log.append((self.n, round(self.vy, 4)))
            return 0
        if sid == 0x10 and a and a[0] == 0:
            if a[1] == 0:
                self.acc = -GRAVITY
            return 0
        if sid == 0x12 and a and a[0] == 0x4:
            self.rate = f(a[1])
            self.rates.append((self.n, round(self.rate, 4)))
            return 0
        if sid == 0x12 and a and a[0] == 0x1:
            self.rate = f(a[3]) if len(a) > 3 else 1.0
        if sid == 0x12 and a and a[0] == 0x0 and len(a) == 2:                    # a motion's length
            return MOTION_FRAMES.get(a[1], 1)
        if sid == 0x1E:
            self.sounds.append((self.n, {0x2710: 'play', 0x2714: 'stop'}.get(a[0], a[0]), a[1] if len(a) > 1 else None))
            return 0
        if sid == 0x1C and a and a[0] == 0x3:
            self.fx.append((self.n, a[1], round(f(a[2]), 3), round(f(a[3]), 3), round(f(a[8]), 3)))
            return 0
        return FT.Game.sys(self, sid, a)

    def setvar(self, v, val):
        if v == 0x0F0003C9:                             # v3: BUFFER_CLEAR (a slot's buffer emptied)
            f_ = self.fighters.get(int(val))
            if f_ is not None:
                f_.__dict__.setdefault('wlog', []).append((self.n, 'buffer', round(val, 3)))
            return
        for s_ in range(1, 9):
            f_ = self.fighters.get(s_)
            if isinstance(f_, GVictim):                 # v3: the grounded victim model's own writes
                t_ = s_ + 2
                k_ = {0x0F0000A2 + 8 * t_: 'status', 0x0F000115 + 0x20 * t_: 'input', 0x0F000116 + 0x20 * t_: 'sit',
                      0x0F0000A6 + 8 * t_: 'ground', 0x0f000020 + 4 * (s_ - 1): 'x',
                      0x0f000021 + 4 * (s_ - 1): 'y'}.get(v)
                if k_ is not None:
                    f_.write(self.n, k_, val)
                    return
        for s_ in range(1, 9):                          # v2: a slot's status / input / shield / push writes
            t_ = s_ + 2
            f_ = self.fighters.get(s_)
            if f_ is None:
                continue
            k_ = {0x0F0000A2 + 8 * t_: 'status', 0x0F000115 + 0x20 * t_: 'input', 0x0F00011A + 0x20 * t_: 'shield_hp',
                  0x0F0000A7 + 8 * t_: 'push'}.get(v)
            if k_ is not None:
                f_.__dict__.setdefault('wlog', []).append((self.n, k_, round(val, 3)))
                if k_ == 'status':
                    f_.status = int(val)
                elif k_ == 'shield_hp':
                    f_.shield_hp = val
                return
        FT.Game.setvar(self, v, val)

    def charged(self):
        return self.vars.get(B.V_CHG, 0.0) >= B.CHARGE_FRAMES - 0.5

    def collide(self):
        """the game script's hitbox, the game's collision"""
        if self.kind != 0x23D or self.hitstop > 0 or self.hit is not None:
            return
        lo, hi = (B.HIT_FROM_CH, B.HIT_TO_CH) if self.charged() else (B.HIT_FROM, B.HIT_TO)
        if not (lo <= self.frame < hi):
            return
        hx, hy = self.x + B.HIT_Z * self.face, self.y + B.HIT_Y
        for v in self.fighters.values():
            dx = max(0.0, abs(v.x - hx) - 3.5)
            dy = max(0.0, max(v.y - hy, hy - (v.y + 10.0)))
            if dx * dx + dy * dy > B.HIT_SIZE ** 2:
                continue
            if v.status == 0x1C:
                self.hitflag |= 4
                continue
            hit, add, stop = (B.HIT_CH, 0, B.HITSTOP_CH) if self.charged() else (B.HIT, B.HITSTUN_ADD, B.HITSTOP)
            if self.charged() and not v.air:            # v3: the charged swing's grounded-only hitbox (ID 1)
                hit = B.HIT_CH_GROUND
            kb = B.knockback(hit, getattr(v, 'pct', 0))
            if isinstance(v, GVictim):                  # v3: the grounded victim model
                v.hit(self.n, kb, int(kb * 0.4) + add, stop)
                self.hitstop = stop
                self.hit = v
                self.hitflag |= 2
                return
            v.hitstop, self.hitstop = stop, stop
            v.hitstun = int(kb * 0.4) + add
            v.vx, v.vy = 0.0, -kb * 0.03
            v.pending = 0x46
            v.hit_at = self.n
            self.hit = v
            self.hitflag |= 2
            return

    def physics(self):
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        if FF in self.flags:                            # v2: the gravity energy's fast fall
            self.vy = -FF_SPEED
        else:
            self.vy += self.acc
            if self.acc != 0.0 and self.vy < -MAX_FALL:
                self.vy = -MAX_FALL
        self.y += self.vy
        if self.floor is not None and self.y <= self.floor:
            self.y, self.air = self.floor, False
        self.frame += self.rate
        if self.kind in LEN and self.frame > LEN[self.kind] - 1 + 1e-6:
            self.frame = self.frame - LEN[self.kind] if self.kind == 0x23D else float(LEN[self.kind] - 1)


class GVictim(FT.Fighter):
    """v3: a fighter on the ground, the game's side as far as the MSC sees it (the model's assumptions; the worst case
    where the game isn't known):
    - a hit (Sledgehammer's 270): frozen its hitstop; its damage status asked (taking effect next frame): lying
      (0x4D-0x53) and knockback under 80 DownDamage (0x57), else under 80 Damage on the ground (0x45), 80 or more the
      ground spike's bounce (DamageFly 0x47, launched up at knockback x 0.8 x 0.03 a frame). The launch speed is kept
      through any status (a status change isn't assumed to clear it), less 0.051 a frame, gravity 0.09 in the air;
      landing ends it (a DamageFly landing: DownBound)
    - a status write takes effect on its next frame (docs/position-variables.md), over its own pending one; a position
      or SITUATION write at once
    - DownWait (0x50): in the air -> Fall (func_963); a getup press (cpu_getup: a CPU's, which the controller-off
      stops, as the God Fist's in game) or its timer (down_timer frames) -> DownStand; DownBound (0x4D) -> DownWait
      after 10 frames; DownStand / DownStandFb / DownStandAttack -> Wait after 30; Damage / DamageFly -> Wait / Fall at
      the end of their hitstun; DownDamage -> DownWait after 12
    """
    def __init__(self, slot, x, y, status=0x0, pct=0.0, down_timer=60, cpu_getup=False):
        FT.Fighter.__init__(self, slot, x, y, air=False)
        self.floor = y
        self.status = status
        self.pct = pct
        self.down_timer, self.cpu_getup = down_timer, cpu_getup
        self.timer = down_timer
        self.age = 0                                    # frames in its status
        self.input_off = False
        self.kvy = 0.0
        self.wlog = []
        self.slog = []                                  # (n, status, air, y) after each step

    def write(self, n, k, val):
        self.wlog.append((n, k, round(val, 3)))
        if k == 'status':
            self.pending = int(val)
        elif k == 'input':
            self.input_off = val > 0.5
        elif k == 'sit':
            self.air = val > 1.5
        elif k == 'x':
            self.x = val
        elif k == 'y':
            self.y = val

    def hit(self, n, kb, hitstun, stop):
        self.hit_at = n
        self.hitstop, self.hitstun = stop, hitstun
        lying = 0x4D <= self.status <= 0x53
        if kb < 80.0:
            self.pending = 0x57 if lying else 0x45
            self.kvy = 0.0
        else:
            self.pending = 0x47
            self.kvy = kb * 0.8 * 0.03

    def set_status(self, st):
        if st != self.status:
            self.status, self.age = st, 0
            if st == 0x50:
                self.timer = self.down_timer

    def step(self, n):
        if self.pending is not None:
            self.set_status(self.pending)
            self.pending = None
        if self.hitstop > 0:
            self.hitstop -= 1
            self.slog.append((n, self.status, self.air, round(self.y, 3)))
            return
        self.age += 1
        if self.kvy or self.air:                        # the launch, whatever its status
            self.air = True
            self.y += self.kvy
            sp = abs(self.kvy)
            self.kvy = (self.kvy / sp) * max(0.0, sp - 0.051) if sp else 0.0
            self.kvy -= 0.09
            if self.y <= self.floor:
                self.y, self.kvy, self.air = self.floor, 0.0, False
                if self.status in (0x47, 0x4C):
                    self.set_status(0x4D)               # an un-teched tumble landing
        st = self.status
        if st == 0x50:
            if self.air:
                self.set_status(0xE)
            else:
                self.timer -= 1
                if (self.cpu_getup and not self.input_off) or self.timer <= 0:
                    self.set_status(0x54)
        elif st == 0x4D and self.age >= 10:
            self.set_status(0x50)
        elif st in (0x54, 0x55, 0x56) and self.age >= 30:
            self.set_status(0x0)
        elif st == 0x57 and self.age >= 12:
            self.set_status(0x50)
        elif st in (0x45, 0x46, 0x47):
            self.hitstun -= 1
            if self.hitstun <= 0:
                self.set_status(0xE if self.air else 0x0)
        self.slog.append((n, self.status, self.air, round(self.y, 3)))


def fn(vm, name):
    return vm.func(FT.func_index(vm, name))


def run(path, g, frames=200, cut_at=None, after=0, tick=None):
    """the air down special from its main; the trace [(k, kind, frame, y, vy, status)] (k 0 = the first frame);
    after: frames of the per-frame hooks (sh_tick, cb_shield_tick) and the fighters after the status ends (v2);
    tick(g, k): the test's own changes before each frame's hooks"""
    vm = FT.vm_for(path, g)
    tr = []
    end = None
    for k in range(frames + after):
        if end is not None:
            if k > end + after:
                break
            g.n = k
            if tick:
                tick(g, k)
            vm.call(fn(vm, 'sh_tick'))
            vm.call(fn(vm, 'cb_shield_tick'))
            for v in g.fighters.values():
                v.step(k)
            continue
        if k >= frames:
            break
        g.n = k
        vm.g[18] = 2 if g.air else 0
        vm.g[24] = g.press.get(k, 0)
        if g.stick is not None:                         # v2: func_77's stick Y / flick age
            sy, age = g.stick(k)
            vm.g[32], vm.g[47] = R.f2i(sy), age
        else:
            vm.g[32], vm.g[47] = R.f2i(0.0), 0xFE
        if cut_at is not None and k == cut_at:
            vm.call(fn(vm, 'func_2282'))
            g.status = 'cut'
        elif k == 0:
            vm.call(fn(vm, 'func_2265'))
        elif g.status is None:
            vm.call(fn(vm, 'sh_loop'))
        tr.append((k, g.kind, round(g.frame, 3), round(g.y, 3), round(g.vy, 3), g.status,
                   round(g.fighters[2].y, 3) if 2 in g.fighters else None))
        if tick:
            tick(g, k)
        vm.call(fn(vm, 'sh_tick'))                      # v2: func_82's hooks, every frame
        vm.call(fn(vm, 'cb_shield_tick'))
        if g.status is not None:
            if g.status != 'cut':
                vm.call(fn(vm, 'func_2282'))
            if not after:
                break
            end = k
            continue
        g.collide()
        for v in g.fighters.values():
            v.step(k)
            if v.status in (0x45, 0x46, 0x47) or v.hitstop:
                pass
        g.physics()
    return tr, vm


def first(tr, pred):
    return next((t for t in tr if pred(t)), None)


def fall_y(y0, k):
    """his height after k frames of his own fall from rest at y0 (the model's physics)"""
    y, v = y0, 0.0
    for _ in range(k):
        v = max(-MAX_FALL, v - GRAVITY)
        y += v
    return y


def victim_below(y=100.0, dy=-6.0, dx=4.0, k=None):
    """an airborne fighter (slot 2) below and ahead of him (k: where he will be on game frame k: it waits there)"""
    v = FT.Fighter(2, dx, (fall_y(y, k) if k is not None else y) + dy, air=True)
    return v


def msc_tests(path):
    swing_k = A.START_FRAMES - 1                       # 12: the game frame (k) the swing starts on a tap
    # 1. a tap: the wind-up 0-12, the swing from k 12, Fall after its last frame; the charge SE at 12, no charge
    g = Game(held=lambda n: n <= 2)
    tr, _vm = run(path, g)
    check('tap: 0x239 from frame 0, then 0x23D (frame 0) on game frame %d' % swing_k,
          [(n, m, fr) for n, m, fr in g.motions], [(0, 0x239, 0.0), (swing_k, 0x23D, 0.0)])
    check('tap: uncharged (sh_chg 0), Fall (0xE) on game frame %d (the swing\'s %d frames)' % (
        swing_k + A.HOLD_FRAMES, A.HOLD_FRAMES), (g.vars.get(B.V_CHG), tr[-1][5], tr[-1][0]),
          (0.0, 0xE, swing_k + A.HOLD_FRAMES))
    check('tap: XV2\'s Charge SE (cue 0, BAC 6) at the charge pose, stopped only at the status\'s end',
          [(n, w) for n, w, i in g.sounds if i == B.SE_IDS['sh_charge']], [(swing_k, 'play'), (tr[-1][0], 'stop')])
    check('tap: his own gravity the whole move (no 0 acceleration, no speed written), the end puts it back',
          (sorted({a for _n, a in g.acc_log}), g.vy_log), ([-GRAVITY], []))
    want_y = 100.0
    v = 0.0
    for _ in range(40):
        v = max(-MAX_FALL, v - GRAVITY)
        want_y += v
    check('tap: he falls as with no move (40 frames: %.2f)' % want_y, round(tr[40][3], 2), round(want_y, 2))
    check('tap: the swing at its own speed (rate 1 every frame: no hit, uncharged)',
          sorted({r for n, r in g.rates}), [1.0])
    # 2. a full charge: held at the charge pose CHARGE_FRAMES frames, then the charged swing
    g = Game(held=lambda n: True)
    tr, _vm = run(path, g)
    sk = swing_k + B.CHARGE_FRAMES - 1
    check('held: the pose (0x239 frame %d) held, the charged swing on game frame %d (%d frames charged)' % (
        A.START_FRAMES - 1, sk, B.CHARGE_FRAMES), ([(n, m) for n, m, _f in g.motions], g.vars.get(B.V_CHG)),
          ([(0, 0x239), (sk, 0x23D)], float(B.CHARGE_FRAMES)))
    check('held: the pose frame on every charging frame', sorted({fr for k, m, fr, *_r in tr if m == 0x239 and
                                                                  swing_k <= k < sk}), [float(A.START_FRAMES - 1)])
    check('held: the Charge SE from the pose, stopped when it is charged (XV2: entry 0 ends)',
          [(n, w) for n, w, i in g.sounds if i == B.SE_IDS['sh_charge']][:2], [(swing_k, 'play'), (sk, 'stop')])
    rates = sorted({r for _n, r in g.rates})
    check('held: a charged whiff slows BAC 22-26 (x%.3f: entry 2\'s 0.23 / 0.3)' % (0.23 / 0.3),
          rates, sorted({1.0, round(0.23 / 0.3, 4)}))
    # 3. released during the charge: uncharged (XV2: entry 0)
    g = Game(held=lambda n: n < swing_k + 10)
    tr, _vm = run(path, g)
    check('released after 10 charging frames: uncharged (sh_chg 0), the swing at once',
          ([(n, m) for n, m, _f in g.motions], g.vars.get(B.V_CHG)), ([(0, 0x239), (swing_k + 10, 0x23D)], 0.0))
    # 4. an uncharged hit on a fighter below: XV2's hit effect at the contact point, Hit_L, the follow, the rates,
    # the special cancel from the on-hit window (not the down special)
    hit_k = swing_k + B.HIT_FROM
    vy0 = fall_y(100.0, hit_k) - 6.0
    v = victim_below(k=hit_k)
    presses = {hit_k + 2: UP, hit_k + B.HITSTOP + 8: DOWN}
    g = Game(fighters=[v], held=lambda n: n <= 2, press=presses)
    tr, _vm = run(path, g, frames=200)
    check('uncharged hit on game frame %d (swing %d)' % (hit_k, B.HIT_FROM), v.hit_at, hit_k)
    fx = [(n, i) for n, i, *_r in g.fx]
    check('the hit (the next frame, in its hitstop): BTL_CMN 0\'s three sets once (HitLOD, HitS, the sweat)',
          sorted(fx), sorted([(hit_k + 1, B.FX_IDS[k]) for k in ('hitlod', 'hits', 'sweat')]))
    me = [t for t in tr if t[0] == hit_k + 1][0]
    hx, hy = B.HIT_Z, me[3] + B.HIT_Y
    cx, cy = (hx + 4.0) / 2, (hy + vy0 + B.VICTIM_MID) / 2
    got = {i: (x, y, s_) for _n, i, x, y, s_ in g.fx}
    check('the hit effects halfway between the hitbox\'s centre and the fighter\'s middle, XV2\'s sizes x%.2f' %
          B.SH_FX_SCALE, (got.get(B.FX_IDS['hitlod']), got.get(B.FX_IDS['hits']), got.get(B.FX_IDS['sweat'])),
          ((round(cx, 3), round(cy, 3), round(1.5 * B.SH_FX_SCALE, 3)),
           (round(cx, 3), round(cy, 3), round(0.8 * B.SH_FX_SCALE, 3)),
           (4.0, round(vy0 + B.VICTIM_HEAD, 3), round(1.0 * B.SH_FX_SCALE, 3))))
    check('the hit: Hit_L (BDM #0\'s cue 52), the Charge SE stopped (entry 3)',
          [(n, w, i) for n, w, i in g.sounds if n == hit_k + 1], [(hit_k + 1, 'stop', B.SE_IDS['sh_charge']),
                                                                   (hit_k + 1, 'play', B.SND_HIT)])
    check('the follow: his gravity 0 from the hit', g.acc_log[:1], [(hit_k + 1, 0.0)])
    st = [t[5] for t in tr]
    check('an up special pressed 2 frames after the hit (before the on-hit window), a down special in it: nothing',
          (0x154 in st, 0x155 in st), (False, False))
    # the follow: his speed each frame = the fighter's Y change (frozen in the hitstop: 0)
    g2 = Game(fighters=[victim_below(k=hit_k)], held=lambda n: n <= 2)
    tr2, _vm = run(path, g2, frames=200)
    check('follow: his vertical speed written from the frame after the hit, the fighter in slot 2 followed',
          (g2.vy_log[:1], sorted({n for n, _v in g2.vy_log}) == list(range(hit_k + 1, g2.vy_log[-1][0] + 1))),
          ([(hit_k + 1, 0.0)], True))
    gap = [round(t[3] - t[6], 2) for t in tr2 if hit_k <= t[0] <= g2.vy_log[-1][0]]
    fall = max(abs(a_ - b_) for (a_, b_) in zip([t[6] for t in tr2], [t[6] for t in tr2][1:]))
    check('follow: he keeps his height over the fighter (gap %.2f .. %.2f) within its fastest frame (%.2f) while it '
          'falls %.1f' % (min(gap), max(gap), fall, gap and (tr2[hit_k][6] - tr2[g2.vy_log[-1][0]][6])),
          max(gap) - min(gap) <= fall + 1e-6, True)
    vv = g2.fighters[2]
    over = min(n for n, st_, hs, hp, _x in vv.log if n > hit_k and hs <= 0 and hp <= 0)
    back = [n for n, a_ in g2.acc_log if a_ < 0]
    check('follow: his own gravity back on the frame after its hitstun ran out (game frame %d)' % (over + 1),
          back[:1], [over + 1])
    rates = sorted({r for _n, r in g2.rates})
    check('hit: the swing at entry 3\'s speed (BAC 22-26 x3.333, 26-32 x2, 32-37 x1, 37-44 x0.5)', rates,
          sorted({1.0, round(1 / 0.3, 4), 2.0, 0.5}))
    k_end = [t for t in tr2 if t[5] is not None][0][0]
    check('hit: the move ends %d frames after the hit\'s hitstop (XV2 entry 3: BAC 16 -> 44 = 40 frames)' % (
        k_end - hit_k - B.HITSTOP), k_end - hit_k - B.HITSTOP, 40)
    # the cancel on the on-hit window's first frame (and not the frame before)
    kw = first(tr2, lambda t: t[1] == 0x23D and t[2] >= B.CANCEL_HIT - 0.01)[0]
    check('on-hit window: swing frame %.2f (BAC 26) on game frame %d = %d after the hit\'s hitstop (XV2: 10)' % (
        B.CANCEL_HIT, kw, kw - hit_k - B.HITSTOP), kw - hit_k - B.HITSTOP, 10)
    for when, what in ((UP, 0x154), (SIDE, 0x153), (NEUTRAL, 0x152), (DOWN, None)):
        gc = Game(fighters=[victim_below(k=hit_k)], held=lambda n: n <= 2, press={kw: when, kw - 1: when})
        trc, _vm = run(path, gc, frames=200)
        check('on-hit window (game frame %d): %s -> %s, the frame before: nothing' % (
            kw, {UP: 'up', SIDE: 'side', NEUTRAL: 'neutral', DOWN: 'down'}[when],
            hex(what) if what else 'nothing (never the down special)'), (trc[-1][0], trc[-1][5]),
              (kw, what) if what else (k_end, 0xE))
    # 5. a charged hit: Hit_LL, no follow, the cancel kept
    ck = swing_k + B.CHARGE_FRAMES - 1 + B.HIT_FROM_CH
    g = Game(fighters=[victim_below(k=ck)], held=lambda n: True)
    tr, _vm = run(path, g, frames=220)
    check('charged hit on game frame %d (swing %d)' % (ck, B.HIT_FROM_CH), g.fighters[2].hit_at, ck)
    check('charged hit: Hit_LL (BDM #1\'s cue 53), the three hit effects, no follow (his gravity untouched)',
          ([(w, i) for n, w, i in g.sounds if n == ck + 1 and w == 'play'], len(g.fx), g.vy_log,
           sorted({a_ for _n, a_ in g.acc_log})), ([('play', B.SND_HIT_CH)], 3, [], [-GRAVITY]))
    kw = first(tr, lambda t: t[1] == 0x23D and t[2] >= B.CANCEL_HIT - 0.01)[0]
    gc = Game(fighters=[victim_below(k=ck)], held=lambda n: True, press={kw: UP})
    trc, _vm = run(path, gc, frames=220)
    check('charged hit: the on-hit cancel kept (up special at game frame %d)' % kw, (trc[-1][0], trc[-1][5]),
          (kw, 0x154))
    # 6. a whiff: no special before IASA, every action from it
    kia = first(run(path, Game(held=lambda n: n <= 2))[0], lambda t: t[1] == 0x23D and t[2] >= B.IASA - 0.01)[0]
    g = Game(held=lambda n: n <= 2, press={k: UP for k in range(swing_k + 30, kia)})
    tr, _vm = run(path, g)
    check('whiff: up special held from swing 30 to before IASA (BAC 37, swing %.2f, game frame %d): nothing' % (
        B.IASA, kia), (tr[-1][5], tr[-1][0]), (0xE, swing_k + A.HOLD_FRAMES))
    g = Game(held=lambda n: n <= 2, press={kia: UP})
    tr, _vm = run(path, g)
    check('whiff: up special at IASA -> 0x154', (tr[-1][0], tr[-1][5]), (kia, 0x154))
    g = Game(held=lambda n: n <= 2, press={kia: DOWN})
    tr, _vm = run(path, g)
    check('whiff: the down special again at IASA -> 0x155 (allowed once free)', (tr[-1][0], tr[-1][5]),
          (kia, 0x155))
    # 7. landing (v2): before IASA LandingFallSpecial, 10 frames, his light landing's animation fitted to them; after it a
    # normal landing
    g = Game(held=lambda n: n <= 2, y=6.0)
    g.floor = 0.0
    tr, _vm = run(path, g)
    check('a landing before IASA: LandingFallSpecial (0x19), %d frames (work float 0)' % B.LAND_LAG,
          (tr[-1][5], g.vars.get(0)), (0x19, float(B.LAND_LAG)))
    g = Game(fighters=[victim_below(y=200.0, k=hit_k)], held=lambda n: n <= 2, y=200.0)
    g.floor = fall_y(200.0, hit_k) - 15.0
    tr, _vm = run(path, g, frames=300)
    check('a landing after a hit, before IASA: the same %d frames' % B.LAND_LAG,
          (tr[-1][5], g.vars.get(0), g.fighters[2].hit_at is not None), (0x19, float(B.LAND_LAG), True))
    g = Game(held=lambda n: True, y=8.0)
    g.floor = 0.0
    tr, _vm = run(path, g)
    check('a landing while charging: the same %d frames' % B.LAND_LAG, (tr[-1][5], g.vars.get(0)),
          (0x19, float(B.LAND_LAG)))
    for prev, mot in ((0x155, 0x3A), (0x154, 0x2D)):
        g = Game()
        vm = FT.vm_for(path, g)
        g.vars[0] = float(B.LAND_LAG)
        vm.g[4], vm.g[5] = 0x19, prev
        vm.call(fn(vm, 'func_586'))
        want_rate = round(MOTION_FRAMES[mot] / float(B.LAND_LAG), 3)
        check('LandingFallSpecial entered from 0x%X: motion 0x%X at rate %.2f (%d frames over %d)' % (
            prev, mot, want_rate, MOTION_FRAMES[mot], B.LAND_LAG),
              [(m, round(g.rate, 3)) for _n, m, _f in g.motions], [(mot, want_rate)])
    g = Game(held=lambda n: n <= 2, y=300.0)
    tr, vm = run(path, g, frames=kia + 2)
    g.air = False
    vm.g[18] = 0
    vm.call(fn(vm, 'sh_loop'))
    check('a landing past IASA: a normal landing (0x16)', g.status, 0x16)
    # 8. the status cut while charging: the Charge SE stopped, the charge glow killed, the state cleared
    g = Game(held=lambda n: True)
    tr, _vm = run(path, g, cut_at=swing_k + 5)
    check('cut while charging: Charge SE stopped, Hmr_Crg killed (0x%08X), sh 0, his gravity back' % B.FX_IDS['crg'],
          ([(w, i) for n, w, i in g.sounds if n == swing_k + 5], [e for _n, e in g.kills], g.vars.get(B.V_SH),
           g.acc_log[-1][1]), ([('stop', B.SE_IDS['sh_charge'])], [B.FX_IDS['crg']], 0.0, -GRAVITY))
    # 9. a shield: no hit effect, no cancel, no follow
    v = FT.Fighter(2, 4.0, fall_y(100.0, hit_k) - 6.0, air=True, shield=True)
    g = Game(fighters=[v], held=lambda n: n <= 2, press={k: UP for k in range(swing_k + 36, swing_k + 50)})
    tr, _vm = run(path, g)
    check('a shield: no effect, no follow, no on-hit cancel (Fall at the end)',
          (g.fx, g.vy_log, g.hitflag, tr[-1][5]), ([], [], 4, 0xE))
    # 11. v2: fast fall (the game's own check, func_553): a flick made in the move, while falling
    def stick_from(k0):
        return lambda k: (-1.0, k - k0) if k >= k0 else (0.0, 0xFE)
    g = Game(held=lambda n: n <= 2)
    g.stick = stick_from(20)
    tr, _vm = run(path, g)
    check('fast fall: a down flick on game frame 20 (falling): the flag on 20, his fall at his fast-fall speed after',
          (g.ff_log[:1], tr[22][4]), ([(20, True)], -FF_SPEED))
    g = Game(held=lambda n: n <= 2)
    g.stick = stick_from(0)                            # the down special's own down input, held
    tr, _vm = run(path, g)
    check('fast fall: the stick down from the move\'s first frame (its input): never a fast fall', g.ff_log, [])
    g = Game(held=lambda n: True)
    g.stick = stick_from(swing_k + 10)
    tr, _vm = run(path, g)
    check('fast fall while charging (game frame %d)' % (swing_k + 10), g.ff_log[:1], [(swing_k + 10, True)])
    g = Game(held=lambda n: n <= 2, vy=-FF_SPEED)
    g.flags.add(FF)
    tr, _vm = run(path, g, frames=3)
    check('fast fall carried in: ended at the start, his fall at most his max fall (%.1f)' % MAX_FALL,
          (g.ff_log[:1], tr[0][4] >= -MAX_FALL - 0.1), ([(0, False)], True))
    gf = Game(fighters=[victim_below(k=hit_k)], held=lambda n: n <= 2)
    gf.stick = stick_from(hit_k + B.HITSTOP + 4)
    trf, _vm = run(path, gf, frames=200)
    fol_end = gf.vy_log[-1][0]
    check('fast fall during the uncharged follow: ignored while it runs (flicked at %d; the follow to %d), its speed the '
          'victim\'s' % (hit_k + B.HITSTOP + 4, fol_end), [n for n, on in gf.ff_log if on and n <= fol_end], [])
    gf = Game(fighters=[victim_below(k=hit_k)], held=lambda n: n <= 2)
    gf.stick = stick_from(fol_end + 2)
    trf, _vm = run(path, gf, frames=200)
    check('fast fall after the follow ended (flicked at %d): on' % (fol_end + 2), gf.ff_log[:1], [(fol_end + 2, True)])
    for sh, want in ((1.0, True), (0.0, False)):
        g = Game()
        vm = FT.vm_for(path, g)
        g.flags.add(FF)
        g.vars[B.V_SH] = sh
        vm.g[6], vm.g[50] = 0x155, R.f2i(1.0)
        vm.call(fn(vm, 'func_81'))
        check('func_81 (a special cancels a fresh fast fall): %s' % ('kept while Sledgehammer runs' if want else
                                                                   'cancelled as before outside it'),
              FF in g.flags, want)
    # 12. v2: a grounded victim: uncharged DownBound (a low bounce, no tech) once its hitstop is over; charged lying 40
    # frames (input off, put back down, let go when hit)
    def grounded(k_hit):
        return FT.Fighter(2, 4.0, fall_y(100.0, k_hit) - 4.0, air=False)
    g = Game(fighters=[grounded(hit_k)], held=lambda n: n <= 2)
    tr, _vm = run(path, g, after=20)
    v = g.fighters[2]
    check('grounded, uncharged: hit on %d; DownBound (0x4D) written once, on the first frame after its %d frames of hitstop; no '
          'input change' % (hit_k, B.HITSTOP), (v.hit_at, [w for w in v.wlog if w[1] in ('status', 'input')]),
          (hit_k, [(hit_k + B.HITSTOP, 'status', float(0x4D))]))
    ck = swing_k + B.CHARGE_FRAMES - 1 + B.HIT_FROM_CH
    gtests(path, hit_k, ck)
    # 13. v2: shields: uncharged 24% of the max shield and 8 frames held; charged 80% and 30; a break
    for chg, take, stun, kk in ((False, B.SHIELD_TAKE, B.SHIELD_STUN, hit_k), (True, B.SHIELD_TAKE_CH, B.SHIELD_STUN_CH, ck)):
        v = FT.Fighter(2, 4.0, fall_y(100.0, kk) - 6.0, air=True, shield=True)
        g = Game(fighters=[v], held=(lambda n: True) if chg else (lambda n: n <= 2))
        tr, _vm = run(path, g, frames=230)
        dmg = (B.HIT_CH if chg else B.HIT)['Damage']
        hp = round(50.0 + dmg * 1.19 - 50.0 * take, 3)
        check('shield, %s: its health %.2f (50 + the hit\'s %g x 1.19 back, less %d%% of 50), PUSH 1000 + %d' % (
            'charged' if chg else 'uncharged', hp, dmg, take * 100, stun),
              [x[1:] for x in v.wlog], [('shield_hp', hp), ('push', 1000.0 + stun)])
    v = FT.Fighter(2, 4.0, fall_y(100.0, ck) - 6.0, air=True, shield=True)
    v.shield_hp = 10.0
    g = Game(fighters=[v], held=lambda n: True)
    tr, _vm = run(path, g, frames=230)
    check('shield, charged, 10 health left: a shield break (0x59)', [x[1:] for x in v.wlog], [('status', float(0x59))])
    # 10. on the ground the down special stays Fake Death
    g = Game(held=lambda n: False)
    g.air = False
    vm = FT.vm_for(path, g)
    vm.g[18] = 0
    vm.call(fn(vm, 'func_2265'))
    check('on the ground: Fake Death (0x229), not Sledgehammer', [m[1] for m in g.motions][:1], [0x229])


def gv(k_hit, **kw):
    """a GVictim (slot 2) on the ground where the hitbox reaches on game frame k_hit (4 below his feet)"""
    return GVictim(2, 4.0, fall_y(100.0, k_hit) - 4.0, **kw)


def held_down(v, k0, k1):
    """the frames k0..k1 the victim isn't lying on its floor (a down status 0x4D-0x53, on the ground, at its floor)"""
    return [x for x in v.slog if k0 <= x[0] <= k1 and not (0x4D <= x[1] <= 0x53 and not x[2] and
                                                             abs(x[3] - v.floor) < 1e-3)]


def gtests(path, hit_k, ck):
    """v3: grounded victims (GVictim): the charged hit lying straight down (the user's item 2), the uncharged hit on a
    neutral getup as in the air (item 3)"""
    k0 = ck + B.HITSTOP_CH                               # the first frame after its hitstop
    for pct, cpu in ((0.0, False), (100.0, False), (100.0, True), (150.0, True)):
        v = gv(ck, pct=pct, cpu_getup=cpu)
        g = Game(fighters=[v], held=lambda n: True)
        run(path, g, frames=230, after=80)
        kb = B.knockback(B.HIT_CH, pct)
        inp = [(n, val) for n, k, val in v.wlog if k == 'input']
        what = 'charged, on the ground at %d%% (knockback %.0f: %s)%s' % (
            pct, kb, 'the ground spike\'s bounce, DamageFly' if kb >= 80 else 'Damage on the ground',
            ', a CPU pressing to get up every frame' if cpu else '')
        check('%s: hit on %d; DownWait (0x50) asked in its hitstop (the next frame), its controller off and its buffer '
              'emptied there' % (what, ck), (v.hit_at, [w for w in v.wlog if w[0] == ck + 1 and
                                                         w[1] in ('status', 'input', 'buffer')]),
              (ck, [(ck + 1, 'input', 1.0), (ck + 1, 'buffer', 2.0), (ck + 1, 'status', float(0x50))]))
        check('%s: lying on its floor (a down status, on the ground) every frame from %d to the end of the hold (%d), '
              'never bounced' % (what, ck + 2, k0 + B.DOWN_HOLD - 1), held_down(v, ck + 2, k0 + B.DOWN_HOLD - 1), [])
        check('%s: its controller back after %d frames held (on %d), nothing else' % (what, B.DOWN_HOLD,
                                                                                     k0 + B.DOWN_HOLD),
              inp, [(ck + 1, 1.0), (k0 + B.DOWN_HOLD, 0.0)])
        if cpu:
            st = [x[1] for x in v.slog if x[0] == k0 + B.DOWN_HOLD + 1]
            check('%s: free after the hold: it gets up (DownStand 0x54) on its next frame' % what, st, [0x54])
    # its own down timer ending in the hold (20 frames): put back down, still held
    v = gv(ck, pct=100.0, down_timer=20)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=80)
    up = [x[0] for x in v.slog if x[1] == 0x54 and x[0] < k0 + B.DOWN_HOLD]
    check('charged: its down timer ending in the hold (20 frames; DownStand on %s): DownWait again the next frame, its '
          'controller still off' % up[:1], (len(up), [x[1] for x in v.slog if up and x[0] == up[0] + 1],
                                            [(n, val) for n, k, val in v.wlog if k == 'input']),
          (1, [0x50], [(ck + 1, 1.0), (k0 + B.DOWN_HOLD, 0.0)]))

    def hit_again(g_, k):                               # another attack hits it 15 frames into the hold
        if k == k0 + 15:
            g_.fighters[2].hitstop = 6
            g_.fighters[2].pending = 0x57
    v = gv(ck, pct=100.0)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=80, tick=hit_again)
    check('charged: let go (controller on, buffer emptied) when it is hit again in the hold (frozen again)',
          [w for w in v.wlog if w[1] in ('input', 'buffer')],
          [(ck + 1, 'input', 1.0), (ck + 1, 'buffer', 2.0), (k0 + 15, 'input', 0.0), (k0 + 15, 'buffer', 2.0)])
    # the charged hit on a fighter in its neutral getup: still put down (the user's getup rule is the uncharged hit's)
    v = gv(ck, pct=100.0, status=0x54)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=80)
    check('charged on DownStand (the neutral getup): put down as any grounded fighter',
          held_down(v, ck + 2, k0 + B.DOWN_HOLD - 1), [])
    # the uncharged hit (item 3; the user: the neutral getup only): DownStand -> as in the air (no DownBound, nothing
    # written); standing, lying (DownWait), the roll getup, the getup attack -> the bounce (DownBound after its
    # hitstop) as before
    for st, bounce in ((0x54, False), (0x0, True), (0x50, True), (0x55, True), (0x56, True)):
        v = gv(hit_k, status=st)
        g = Game(fighters=[v], held=lambda n: n <= 2)
        seen = []

        def show(g_, k, seen=seen):
            if k == hit_k + 1:
                seen.append(g_.fighters[2].status)
        run(path, g, after=30, tick=show)
        w = [x for x in v.wlog if x[1] in ('status', 'input')]
        check('uncharged on a fighter on the ground in 0x%X (%s; the MSC sees 0x%X on the hit\'s frame): %s' % (
            st, {0x54: 'DownStand, the neutral getup', 0x0: 'Wait', 0x50: 'DownWait, lying',
                 0x55: 'DownStandFb, the roll getup', 0x56: 'DownStandAttack, the getup attack'}[st],
            seen[0] if seen else -1,
            'DownBound after its hitstop' if bounce else 'no bounce: the hit as in the air (nothing written; its status '
                                                         'before the freeze, sh_rec)'),
              (v.hit_at, w), (hit_k, [(hit_k + B.HITSTOP, 'status', float(0x4D))] if bounce else []))


def script_tests(out, base):
    body = os.path.join(out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    f = {p: acmd.ACMDFile.load(os.path.join(body, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    b = {p: acmd.ACMDFile.load(os.path.join(base, 'script', 'animcmd', 'body', p + '.bin'))
         for p in ('game', 'effect', 'sound', 'expression')}
    nm = lambda c: acmd.INFO[c.ident]['name']                                 # noqa: E731
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    hold = f['game'].script('specialairlwhold')
    hb = [dict(zip(syn, c.params)) for c in hold if nm(c) == 'Extra_Special_Hitbox']
    check('game specialairlwhold: frames %d / %d / %d / %d, the charged hitbox then the uncharged one' % (
        B.HIT_FROM_CH, B.HIT_FROM, B.HIT_TO_CH, B.HIT_TO),
          [c.params[0] for c in hold if nm(c) == 'FRAME'], [float(x) for x in (B.HIT_FROM_CH, B.HIT_FROM, B.HIT_TO_CH,
                                                                                B.HIT_TO)])
    keys = ('Damage', 'Angle', 'BKB', 'KBG', 'FKB', 'Size', 'Z', 'Y', 'X', 'Bone', 'HitstunMul', 'HitstopFrames',
            'SelfHitstopFrames', 'NoGFX', 'Ground/Air', 'Shieldable', 'ShieldDamage')
    want_ch = (B.HIT_CH['Damage'], 270, B.HIT_CH['BKB'], B.HIT_CH['KBG'], 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0, 0.0,
               B.HITSTOP_CH, B.HITSTOP_CH, 1, 2, 1, 0)
    want_chg = (B.HIT_CH_GROUND['Damage'], 0, 1, 0, 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0, 0.0,
                B.HITSTOP_CH, B.HITSTOP_CH, 1, 1, 1, 0)
    want_un = (B.HIT['Damage'], 270, B.HIT['BKB'], B.HIT['KBG'], 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0,
               -float(B.HITSTUN_ADD), B.HITSTOP, B.HITSTOP, 1, 3, 1, 0)
    check('the hitboxes (charged: v3 ID 0 the spike aerial only, ID 1 grounded only knockback 1; uncharged): %s' % (keys,),
          [tuple(round(h[k], 3) if isinstance(h[k], float) else h[k] for k in keys) for h in hb],
          [tuple(round(x, 3) if isinstance(x, float) else x for x in w) for w in (want_ch, want_chg, want_un)])
    check('v3: the charged pair: IDs 0 / 1, Part 0 (one hit a target)', [(h['ID'], h['Part']) for h in hb[:2]],
          [(0, 0), (1, 0)])
    conds = [(c.params[0], c.params[1], c.params[2]) for c in hold if nm(c) == 'Float_Var_Compare']
    check('each read sh_chg (>= %d charged / < %d not)' % (B.CHARGE_FRAMES, B.CHARGE_FRAMES), conds,
          [(B.V_CHG, 3, float(B.CHARGE_FRAMES)), (B.V_CHG, 4, float(B.CHARGE_FRAMES)),
           (B.V_CHG, 3, float(B.CHARGE_FRAMES))])
    names = sorted(n for _c, n in f['game'].new_vars())
    check('New_Vars sh / sh_chg / sh_vic declared (object scope, slots 0x3E / 0x3F / 0x2F)',
          sorted({(n, c.params[0] - 0x0F000380 if c.params[0] >= 0x0F000380 else c.params[0], c.params[3])
                  for c, n in f['game'].new_vars() if n.startswith('sh')}),
          sorted({('sh', 0x3E, 0), ('sh_chg', 0x3F, 0), ('sh_vic', 0x2F, 0)}) if names else [])
    eff_s, eff_h = f['effect'].script('specialairlwstart'), f['effect'].script('specialairlwhold')
    calls = [(nm(c), c.params[0], c.params[1]) + ((round(c.params[3], 2), round(c.params[4], 2),
                                                   round(c.params[8], 3)) if len(c.params) > 8 else (0, 0, 0))
             for c in eff_s + eff_h if nm(c) in ('External_Graphic', 'Terminate_Graphic_Effect')]
    print('     effect calls:', [(n, hex(i), b_, y, z, s) for n, i, b_, y, z, s in calls])
    ids = B.FX_IDS
    check('effect: Hmr_Crg on LHandN at %d; off at %d (uncharged) / %d (charged); at %d Hmr_Fire_L + Hmr_Crg02 '
          '(charged) / Hmr_Fire, on bone 0 up only' % (B.FX_AT['crg_on'], B.FX_AT['crg_off'], B.FX_AT['crg_off_ch'],
                                                      B.FX_AT['fire']),
          [(n, i, b_) for n, i, b_, _y, _z, _s in calls],
          [('External_Graphic', ids['crg'], B.LHAND), ('Terminate_Graphic_Effect', ids['crg'], 1),
           ('External_Graphic', ids['fire_l'], 0), ('External_Graphic', ids['crg02'], B.LHAND),
           ('External_Graphic', ids['fire'], 0), ('Terminate_Graphic_Effect', ids['crg'], 1)])
    snd = [(nm(c), c.params) for c in f['sound'].script('specialairlwstart') + f['sound'].script('specialairlwhold')
           if nm(c) in ('FRAME', 'Sound_Effect')]
    check('sound: swing_42 at 2 (BAC 1), Furi at the swing\'s %d (BAC 9)' % B.SND_AT['furi'], snd,
          [('FRAME', [2.0]), ('Sound_Effect', [B.SE_IDS['sh_swing']]), ('FRAME', [float(B.SND_AT['furi'])]),
           ('Sound_Effect', [B.SE_IDS['sh_furi']])])
    same = []
    skip = {acmd.crc(n) for n in ('specialairlwstart', 'specialairlwhold')}
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])] and \
                    h not in {acmd.crc(n) for n in ('attackdash', 'specialhi', 'specialairhi', 'speciallwstart',
                                                     'speciallwhold')}:
                same.append((p, hex(h)))
    check('every other script as the user\'s (but the God Fist\'s / Core Breaker\'s / Fake Death\'s)', same, [])


def effect_tests(out):
    import efc
    import ptcl
    fx = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000')
    p = ptcl.Ptcl(open(fx + '.ptcl', 'rb').read())
    e = efc.Efc(open(fx + '.efc', 'rb').read())
    names = {k: p.set_name(e.entries[i & 0xFFFF][1] - 1) for k, i in B.FX_IDS.items()}
    want = {k: 'PtcSupamarioSh' + emp[:-4] for emp, k in B.EMP_KEY.items()}
    check('the seven effect ids name their sets', names, want)
    bad, halos, rings, arcs = [], 0, 0, []
    for k, i in B.FX_IDS.items():
        si = e.entries[i & 0xFFFF][1] - 1
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None:
                continue
            t, r = p.field(d, 'emitter_translation'), p.field(d, 'emitter_rotation')
            ring = p.field(d, 'particle_type') == 1
            flat = ring and k in ('fire', 'fire_l')
            if k in ('crg', 'crg02', 'fire', 'fire_l') and struct.unpack_from('>I', bytes(d), 0x310)[0] != 0:
                bad.append((k, p.emitter_name(d), 'not following (0x310)'))
            rings += flat
            want_r = tuple(B.arc_turn()) if flat else (0.0, 0.0, 0.0)
            if flat and p.field(d, 'rotation_velocity')[2] >= 0:
                bad.append((k, p.emitter_name(d), 'v2: the arc must spin the swing\'s way (negative)'))
            if max(abs(v) for v in t) > 1e-6 or max(abs(a - b_) for a, b_ in zip(r, want_r)) > 1e-5:
                bad.append((k, p.emitter_name(d), t, r))
            if (p.field(d, 'particle_type') in (1, 3) or p.field(d, 'emitter_velocity') or
                    p.field(d, 'figure_velocity')) and p.field(d, 'dispersion_angle') < 180.0 - 1e-3:
                bad.append((k, p.emitter_name(d), 'spread', p.field(d, 'dispersion_angle')))
            rgb = [c * p.field(d, 'color_scale') for c in p.color_keys(d, 0)[0][:3]]
            if max(rgb) > 2.0 + 1e-3:
                bad.append((k, p.emitter_name(d), 'HDR', rgb))
            if flat and p.field(d, 'alpha_init') > 0.05:
                arcs.append(round(B.arc_peak(p, d), 3))
    check('every emitter at the effect\'s origin, unturned but Hmr_Fire\'s arcs (v2: in his YZ plane, facing the camera), '
          'a full-sphere spread when directional, HDR within 2.0, the skill\'s emitters following (v2)', bad, [])
    check('the falling rings converted flat (ShapeDraw -> polygons): %d' % rings, rings > 0, True)
    check('v3 (the glow): the swing arcs drawn at most %.2f (x%g of the 2.0 cap: two overlapping stay under the bloom)'
          % (2.0 * B.ARC_GAIN, B.ARC_GAIN), (len(arcs) > 0, max(arcs) <= 2.0 * B.ARC_GAIN + 1e-3), (True, True))
    import json
    rep = json.load(open(os.path.join(out, 'sledgehammer_fx.json')))
    for k, i in B.FX_IDS.items():
        si = e.entries[i & 0xFFFF][1] - 1
        halos += len(p.sets[si]['emitters']) - len(rep['sets'][{v: q for q, v in B.EMP_KEY.items()}[k]]['emitters'])
    check('the fake-glow halos (HALO_ALPHA %g) in their own sets: %d (the glowing emitters with room; no companion '
          'sets)' % (rep['halos']['alpha'], halos), halos, rep['halos']['glowing'])


def motion_tests(out):
    mo = os.path.join(out, 'fighter', 'supamario', 'motion', 'body', 'main.pac')
    ents = dict(omo.pac_read(mo))
    for m, n in ((A.START, A.START_FRAMES), (A.HOLD, A.HOLD_FRAMES)):
        o = omo.Omo(ents['FitMarioBodyMainD03' + m])
        check('%s: %d frames' % (m, n), o.frames, n)


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    path = os.path.join(a[0], 'fighter', 'supamario', 'script', 'msc', 'supamario.mscsb')
    msc_tests(path)
    script_tests(a[0], a[1])
    effect_tests(a[0])
    motion_tests(a[0])
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
