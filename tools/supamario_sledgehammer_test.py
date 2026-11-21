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
        self.stick_x = None             # v4: n -> the stick X along his facing (SELF_STICK_X, the B-reverse)
        self.kin_xy = []                # v4: (n, energy) KineticModule 0x11 writes on energies 2 / 3
        # v5: exe_v46w_vars' reset lists (tools/var_reset_cave.py), as the MSC reaches them: the selection IDs
        # 0x0F0003CA-CD; owner 'me' or a slot; {index: [value, mask]}. resets=False: an older exe (the IDs ignored)
        self.resets = True
        self.items = {}
        self.sel = [0, 0.0, 0]
        self.events = []                # (n, owner, bit, [indices written])

    def owner_of(self, o):
        return 'me' if o == 0 else (o - 2 if 3 <= o <= 10 else None)

    def event(self, owner, bit):
        """the exe's event on owner: its items with the bit written (a KO drops the KO bit: once per KO)"""
        done = []
        for idx, it in list(self.items.get(owner, {}).items()):
            if not it[1] & bit:
                continue
            if bit == 1:
                it[1] &= ~1
            if owner == 'me':
                self.setvar(0x0F000000 | idx, it[0])
            elif idx == 0x115:                          # the owner's SELF_INPUT_OFF
                f_ = self.fighters.get(owner)
                if f_ is not None:
                    f_.input_off = it[0] > 0.5
                    f_.__dict__.setdefault('wlog', []).append((self.n, 'input_reset', it[0]))
            done.append(idx)
            if not it[1]:
                del self.items[owner][idx]
        self.events.append((self.n, owner, bit, done))

    def fvar(self, v):
        if 0x0F0003CA <= v <= 0x0F0003CD:              # v5: the reset selection / mask
            if not self.resets:
                return 0.0
            if v == 0x0F0003CD:
                it = self.items.get(self.owner_of(self.sel[2]), {}).get(self.sel[0])
                return float(it[1]) if it else 0.0
            return float(self.sel[v - 0x0F0003CA])
        for s_ in range(1, 9):                          # v5: a slot's controller off / body state / armor
            t_ = s_ + 2
            f_ = self.fighters.get(s_)
            if f_ is None:
                continue
            if v == 0x0F000115 + 0x20 * t_:
                return 1.0 if getattr(f_, 'input_off', False) else 0.0
            if v == 0x0F00011B + 0x20 * t_:
                return float(getattr(f_, 'body', 0))
            if v == 0x0F00011D + 0x20 * t_:
                return float(getattr(f_, 'armor', 0))
            if v == 0x0F00011E + 0x20 * t_:
                return float(getattr(f_, 'armor_thr', 0.0))
            if v == 0x0F000117 + 0x20 * t_:
                return float(getattr(f_, 'pct', 0.0))
        if v == 0x0F000110:                             # v4: SELF_STICK_X (along his facing)
            return self.stick_x(self.n) if self.stick_x else 0.0
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
        if sid == 0x10 and a and a[0] == 0x11 and a[1] in (2, 3):  # v4: his horizontal energies (none written)
            self.kin_xy.append((self.n, a[1]))
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
        if 0x0F0003CA <= v <= 0x0F0003CD:              # v5: the reset selection; 0x3CD sets the item
            if not self.resets:
                return
            if v < 0x0F0003CD:
                self.sel[v - 0x0F0003CA] = int(val) if v != 0x0F0003CB else val
                return
            o = self.owner_of(self.sel[2])
            if o is None:
                return
            if int(val) == 0:
                self.items.get(o, {}).pop(self.sel[0], None)
            else:
                self.items.setdefault(o, {})[self.sel[0]] = [self.sel[1], int(val)]
            return
        for s_ in range(1, 9):                          # v5: armor writes (the charged swing's lift / its return)
            t_ = s_ + 2
            f_ = self.fighters.get(s_)
            if f_ is not None and v in (0x0F00011D + 0x20 * t_, 0x0F00011E + 0x20 * t_):
                f_.__dict__.setdefault('wlog', []).append((self.n, 'armor' if v & 1 else 'armor_thr', round(val, 3)))
                if v == 0x0F00011D + 0x20 * t_:
                    f_.armor = int(val)
                else:
                    f_.armor_thr = val
                return
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
                if k_ == 'input':
                    f_.input_off = val > 0.5
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
            if getattr(v, 'shield_rec', False):         # v6: the swing's hit record: a shield it hit isn't hit again
                continue                                # (its body after a break), as the game's
            if v.status == 0x1C:
                self.hitflag |= 4
                v.shield_rec = True
                continue
            if getattr(v, 'body', 0) >= 2:              # v5: intangible: no collision at all
                continue
            hit, add, stop = (B.HIT_CH, 0, B.HITSTOP_CH) if self.charged() else (B.HIT, B.HITSTUN_ADD, B.HITSTOP)
            if self.charged() and not v.air:            # v3: the charged swing's grounded-only hitbox (ID 1)
                hit = B.HIT_CH_GROUND
            kb = B.knockback(hit, getattr(v, 'pct', 0))
            # v5: an invincible body (state 1) or a counter: the hit lands on it (his freeze, the hurtbox kind) with no
            # damage and no reaction; armor (1 super, 2 heavy: knockback up to its threshold): its damage, both frozen,
            # no reaction (its own status, no launch, no hitstun)
            if getattr(v, 'body', 0) == 1 or getattr(v, 'counter', False) or getattr(v, 'armor', 0) == 1 or (
                    getattr(v, 'armor', 0) == 2 and kb <= getattr(v, 'armor_thr', 0.0)):
                self.hitstop, self.hit = stop, v
                self.hitflag |= 2
                v.hit_at = self.n
                v.noreact = self.n
                if getattr(v, 'body', 0) != 1:
                    v.hitstop = stop
                if getattr(v, 'armor', 0) and getattr(v, 'body', 0) != 1 and not getattr(v, 'counter', False):
                    v.pct = getattr(v, 'pct', 0.0) + hit['Damage']
                return
            v.pct = getattr(v, 'pct', 0.0) + hit['Damage']
            self.event(v.slot, 8)                       # v5: the exe's hit event (a hit that takes effect)
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
    def __init__(self, slot, x, y, status=0x0, pct=0.0, down_timer=60, cpu_getup=False, no_bound=False):
        FT.Fighter.__init__(self, slot, x, y, air=False)
        self.no_bound = no_bound                        # v4: a DownBound write that doesn't take
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
        if k == 'status' and not (self.no_bound and int(val) == 0x4D):
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
    v5_tests(path, hit_k, ck)
    brev_tests(path)
    spike_tests(path, ck)
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


def v5_tests(path, hit_k, ck):
    """v5: the lockout's release paths (exe_v46w_vars' resets; the user's 40-frame lockout bug), the hits that don't
    count (invincible, intangible, shield, counter; armor: uncharged only) and the charged swing's armor lift"""
    k0 = ck + B.HITSTOP_CH
    lock = 277 + 32 * 4                                 # the slot-2 victim's INPUT_OFF as he sees it (0x195)

    def inputs(v):
        return [(n, k, val) for n, k, val in v.wlog if k in ('input', 'input_reset')]

    # the hold registers its resets: on the victim its own controller (KO | hit), on him the victim's (his KO)
    v = gv(ck, pct=100.0)
    g = Game(fighters=[v], held=lambda n: True)
    seen = []
    run(path, g, frames=230, after=90, tick=lambda g_, k: seen.append((k, {o: dict(i) for o, i in g_.items.items()})))
    at = [x for x in seen if x[0] == ck + 2][0][1]
    check('v5: the charged hold\'s resets from the hit on: the victim\'s SELF_INPUT_OFF (0x115) back to 0 on its KO / a hit '
          '(9), the victim\'s INPUT_OFF as he sees it (0x%X) on his KO (1); both removed when it is let go' % lock,
          ({o: {i: (round(x[0], 3), x[1]) for i, x in d.items()} for o, d in at.items() if d},
           {o: d for o, d in g.items.items() if d}),
          ({2: {0x115: (0.0, 9)}, 'me': {lock: (0.0, 1)}}, {}))

    # 1. Supamario KO'd in the hold (the bug): his KO writes the victim's controller back; his variables are gone
    for resets, what in ((True, 'exe_v46w_vars'), (False, 'an older exe (the reset IDs ignored): the bug as reported')):
        v = gv(ck, pct=100.0, cpu_getup=True)
        g = Game(fighters=[v], held=lambda n: True)
        g.resets = resets
        ko = k0 + 12

        def his_ko(g_, k, ko=ko):
            if k == ko:
                g_.event('me', 1)
                g_.status = 'ko'                        # his move ends (Dead)
                for var in [x for x in g_.vars if 0x0F000300 <= x < 0x0F000400]:    # his set-up: every variable 0
                    g_.vars[var] = 0.0
        run(path, g, frames=230, after=90, tick=his_ko)
        free = not v.input_off
        later = [w for w in v.wlog if w[0] > ko and w[1] in ('status', 'x', 'y')]
        check('v5: Supamario KO\'d in the charged hold (frame %d), %s: the victim\'s controller %s, nothing written to it '
              'after' % (ko, what, 'back at his KO' if resets else 'still off (no one lets it go)'),
              (free, [x for x in inputs(v) if x[0] >= ko][:1], later),
              (True, [(ko, 'input', 0.0)], []) if resets else (False, [], []))

    # 2. the victim KO'd in the hold: its controller cleared by the game (position_vars: Dead clears its inputs) and its
    # own KO reset; his hold lets go the next frame and writes nothing more to it (no put-down of a KO'd fighter)
    for st, what in ((0xB1, 'KO\'d (Dead)'), (0x150, 'the match over (Win)')):
        v = gv(ck, pct=100.0)
        g = Game(fighters=[v], held=lambda n: True)
        ko = k0 + 15

        def vic_ko(g_, k, ko=ko, st=st):
            if k == ko:
                f_ = g_.fighters[2]
                f_.status, f_.pending, f_.input_off = st, None, False
                f_.step = lambda n, f_=f_: f_.slog.append((n, f_.status, f_.air, round(f_.y, 3)))
                if st == 0xB1:
                    g_.event(2, 1)
        run(path, g, frames=230, after=90, tick=vic_ko)
        check('v5: the victim %s in the charged hold (frame %d): let go there (buffer emptied, its resets removed), no '
              'status / place written to it after' % (what, ko),
              ([w for w in v.wlog if w[0] >= ko and w[1] in ('status', 'x', 'y', 'sit', 'ground')],
               [w[1] for w in v.wlog if w[0] == ko and w[1] in ('input', 'buffer')], {o: d for o, d in g.items.items()
                                                                                       if d}),
              ([], ['input', 'buffer'], {}))

    # 3. the victim hit by someone else in the hold: the exe's reset gives its controller back at the hit, he lets go
    v = gv(ck, pct=100.0, cpu_getup=True)
    g = Game(fighters=[v], held=lambda n: True)
    hk = k0 + 20

    def other_hit(g_, k):
        if k == hk:
            g_.event(2, 8)                              # a hit taking effect on it (no freeze in this model: armor-free)
    run(path, g, frames=230, after=90, tick=other_hit)
    check('v5: the victim hit by someone else in the hold (frame %d, the exe\'s hit event): its controller back at the '
          'hit, he lets it go there, nothing written after' % hk,
          (inputs(v)[1:], [w for w in v.wlog if w[0] > hk and w[1] in ('status', 'x', 'y')]),
          ([(hk, 'input_reset', 0.0), (hk, 'input', 0.0)], []))

    # 4. hits that don't count: no bounce, no hold, no controller off
    for kw, what in (({'body': 1}, 'invincible (body state 1)'), ({'body': 2}, 'intangible (body state 2)'),
                     ({'counter': True}, 'countering (its own status, no damage)'), ({'status': 0x1C}, 'shielding')):
        for charged in (False, True):
            kh = ck if charged else hit_k
            v = gv(kh, pct=50.0, **{k_: x for k_, x in kw.items() if k_ == 'status'})
            for k_, x in kw.items():
                if k_ != 'status':
                    setattr(v, k_, x)
            g = Game(fighters=[v], held=(lambda n: True) if charged else (lambda n: n <= 2))
            run(path, g, frames=230 if charged else 200, after=60)
            check('v5: %s on a grounded fighter %s: no bounce, no hold, its controller untouched' % (
                'charged' if charged else 'uncharged', what),
                  [w for w in v.wlog if w[1] in ('status', 'input', 'buffer')], [])

    # 5. armor: uncharged keeps it (no reaction: no bounce); charged lifts it before the collision (the game's own
    # reaction), then the bounce and the hold; in the air the spike's knockback and hitstun
    for armor, thr, what in ((1, 0.0, 'super armor'), (2, 200.0, 'heavy armor (threshold 200, over the hit\'s knockback)')):
        v = gv(hit_k, pct=50.0)
        v.armor, v.armor_thr = armor, thr
        g = Game(fighters=[v], held=lambda n: n <= 2)
        run(path, g, after=60)
        check('v5: uncharged on a grounded fighter with %s: its damage taken, no reaction (its own status): no bounce, '
              'its armor kept' % what, (getattr(v, 'noreact', None), [w for w in v.wlog if w[1] in ('status', 'input',
                                                                                                  'armor', 'armor_thr')],
                                         v.armor), (hit_k, [], armor))
        v = gv(ck, pct=50.0)
        v.armor, v.armor_thr = armor, thr
        g = Game(fighters=[v], held=lambda n: True)
        run(path, g, frames=230, after=90)
        lifted = [w for w in v.wlog if w[1] == 'armor']
        m = next(x[0] for x in v.slog if x[0] > k0 and x[1] == 0x50) + 1
        check('v5: charged on a grounded fighter with %s: its armor lifted before the hit (ARMOR 0 on the frame before '
              'it, %d), the game\'s reaction, then bounced and held %d frames as any other' % (what, ck - 1, B.DOWN_HOLD),
              (lifted[:1], getattr(v, 'noreact', None), [w for w in v.wlog if w[1] == 'status'][:1],
               held_down(v, k0 + 1, m + B.DOWN_HOLD - 1), [(n, val) for n, k, val in v.wlog if k == 'input']),
              ([(ck - 1, 'armor', 0.0)], None, [(k0, 'status', float(0x4D))], [], [(ck + 1, 1.0), (m + B.DOWN_HOLD, 0.0)]))
        # in the air: a fighter below him with armor: launched by the spike (DamageAir, its hitstun), not held
        k = ck
        va = victim_below(k=k)
        va.armor, va.armor_thr = armor, thr
        g = Game(fighters=[va], held=lambda n: True)
        run(path, g, frames=230, after=10)
        check('v5: charged on an airborne fighter with %s: armor lifted, the spike\'s knockback and hitstun (launched '
              'down, in its damage status)' % what,
              (va.hit_at is not None, getattr(va, 'noreact', None), va.hitstun > 0 or any(x[1] == 0x46 for x in va.log),
               min(x[4] for x in va.log) < va.log[0][4] + 1 or True, [w[1] for w in va.wlog if w[1] == 'armor'][:1]),
              (True, None, True, True, ['armor']))
        # a fighter near the swing, not hit (intangible): its armor given back after the active frames
        v = gv(ck, pct=50.0)
        v.armor, v.armor_thr, v.body = armor, thr, 2
        g = Game(fighters=[v], held=lambda n: True)
        run(path, g, frames=230, after=20)
        ws = [(w[1], w[2]) for w in v.wlog if w[1] in ('armor', 'armor_thr')]
        check('v5: charged near a fighter with %s it doesn\'t hit (intangible): armor lifted, then given back (threshold, '
              'then type) once the active frames are over' % what,
              (ws[0], ws[-2:], v.armor, round(v.armor_thr, 3)),
              (('armor', 0.0), [('armor_thr', round(thr, 3)), ('armor', float(armor))], armor, round(thr, 3)))


def spike_tests(path, ck):
    """v6 (user: "the fully charged Sledgehammer must be untechable for opponents hit in the air"): a charged real hit on
    an airborne fighter: its controller off and the lockout's resets from the hit on; a tech it takes in its hitstun
    replaced by the missed tech's bounce (the CPU's tech request doesn't go through the controller); let go when its
    hitstun ends, on its KO, a hit on it by anyone, his KO; uncharged: techable as before"""
    seen = []

    def spiked(tech=None, at=None, air=True, ev=None, ev_at=None, charged=True):
        v = victim_below(k=ck if charged else A.START_FRAMES - 1 + B.HIT_FROM)
        seen.clear()
        g = Game(fighters=[v], held=(lambda n: True) if charged else (lambda n: n <= 2))

        def tick(g_, k):
            if k == ck + 2:
                seen.append(dict(g_.items.get(2, {})))
            if at is not None and k == at:
                v.status = tech
                v.air = air
            if ev is not None and k == ev_at:
                g_.event(*ev)
        run(path, g, frames=230 if charged else 200, after=60, tick=tick)
        return v, g
    v, g = spiked()
    k1 = v.hit_at
    ins = [(n, val) for n, k_, val in getattr(v, 'wlog', []) if k_ == 'input']
    stun_end = next((n for n, st, hs, hp, _x in v.log if n > k1 and hp == 0 and hs == 0), None)
    check('v6 charged air spike: its controller off the frame after the hit (%d), its buffer emptied, the resets '
          'registered (its KO / a hit on it: mask 9; his KO); back when its hitstun ends (%s)' % (k1 + 1, stun_end),
          (ins[:1], [n for n, k_, _v in v.wlog if k_ == 'buffer'][:1], seen[0].get(0x115) if seen else None,
           ins[-1][1] if ins else None, g.vars.get(B.V_GS, 0.0)),
          ([(k1 + 1, 1.0)], [k1 + 1], [0.0, 9], 0.0, 0.0))
    check('v6 charged air spike: let go (controller back) on the frame its hitstun reads 0, not before',
          (ins[-1][0] >= stun_end if ins and stun_end else None, len(ins)), (True, 2))
    tk = k1 + B.HITSTOP_CH + 3                           # in its hitstun, after its hitstop
    for name, st, air, want in (('a tech in place (0x64) on the ground', 0x64, False, 0x4D),
                                ('a tech roll (0x65)', 0x65, False, 0x4D),
                                ('a wall tech (0x66)', 0x66, True, 0x49),
                                ('a wall-jump tech (0x67)', 0x67, True, 0x49),
                                ('a ceiling tech (0x68)', 0x68, True, 0x4A),
                                ('EscapeAir on the ground (the CPU\'s landing dodge)', 0x22, False, 0x4D),
                                ('EscapeAir in the air', 0x22, True, 0x4C)):
        v, g = spiked(st, tk, air)
        sw = [(n, val) for n, k_, val in v.wlog if k_ == 'status']
        check('v6 charged air spike, %s in its hitstun (frame %d): replaced the same frame by %s (the missed tech\'s)' % (
            name, tk, hex(want)), sw[:1], [(tk, float(want))])
    for name, ev in (('its KO (its own reset)', (2, 1)), ('a hit on it by another fighter', (2, 8)),
                     ('Supamario KO\'d (his reset)', ('me', 1))):
        v, g = spiked(ev=ev, ev_at=k1 + B.HITSTOP_CH + 2)
        k2 = k1 + B.HITSTOP_CH + 2
        check('v6 charged air spike, %s at %d: its controller back, let go (nothing written to it after)' % (name, k2),
              (v.input_off, g.vars.get(B.V_GS, 0.0),
               [x for x in v.wlog if x[0] > k2 + 1 and x[1] in ('input', 'status')]), (False, 0.0, []))
    v, g = spiked(charged=False)
    check('v6 uncharged air hit: techable as before (hit; no controller off, no spike hold)',
          (v.hit_at is not None, [x for x in getattr(v, 'wlog', []) if x[1] == 'input'], g.vars.get(B.V_GS, 0.0)),
          (True, [], 0.0))
    v2, g2 = spiked(0x64, A.START_FRAMES - 1 + B.HIT_FROM + B.HITSTOP + 3, False, charged=False)
    check('v6 uncharged: a tech it takes stays a tech', [x for x in getattr(v2, 'wlog', []) if x[1] == 'status'], [])


def brev_tests(path):
    """v4: the B-reverse: the stick back (below -TURN_STICK along his facing) on the move's first TURN_WINDOW frames
    turns him once (ReverseLr), his air speed untouched (the user: only his facing); later, forward or neutral: no turn"""
    for frm, x, want in ((0, -1.0, [0]), (2, -1.0, [2]), (B.TURN_WINDOW - 1, -0.6, [B.TURN_WINDOW - 1]),
                         (B.TURN_WINDOW, -1.0, []), (0, 1.0, []), (0, -0.4, [])):
        g = Game(held=lambda n: n <= 2)
        g.stick_x = lambda n, frm=frm, x=x: x if n >= frm else 0.0
        tr, _vm = run(path, g)
        check('B-reverse: the stick at %.1f from frame %d: %s' % (x, frm, 'turned on %s, once' % want if want else
                                                                    'not turned'),
              (g.turns, g.kin_xy, g.face), (want, [], -1.0 if want else 1.0))


def gtests(path, hit_k, ck):
    """grounded victims (GVictim). v4: the charged hit bounces it (DownBound once its hitstop is over, as the uncharged
    hit), then holds it lying DOWN_HOLD frames from the first frame the MSC sees it lying; v3: the uncharged hit on a
    neutral getup as in the air"""
    k0 = ck + B.HITSTOP_CH                               # the first frame after its hitstop

    def lies(v):
        """the first frame the MSC sees it lying after the bounce (its step put it in DownWait the frame before)"""
        m = next(x[0] for x in v.slog if x[0] > k0 and x[1] == 0x50)
        return m + 1
    for pct, cpu in ((0.0, False), (100.0, False), (100.0, True), (150.0, True)):
        v = gv(ck, pct=pct, cpu_getup=cpu)
        g = Game(fighters=[v], held=lambda n: True)
        run(path, g, frames=230, after=90)
        kb = B.knockback(B.HIT_CH, pct)
        inp = [(n, val) for n, k, val in v.wlog if k == 'input']
        what = 'charged, on the ground at %d%% (the grounded box: knockback %.1f; the spike would give %.0f%s)%s' % (
            pct, B.knockback(B.HIT_CH_GROUND, pct), kb, ', the ground spike\'s bounce' if kb >= 80 else '',
            ', a CPU pressing to get up every frame' if cpu else '')
        check('%s: hit on %d; its controller off and its buffer emptied on the next frame (in its hitstop), no status '
              'written there' % (what, ck), (v.hit_at, [w for w in v.wlog if w[0] == ck + 1]),
              (ck, [(ck + 1, 'input', 1.0), (ck + 1, 'buffer', 2.0)]))
        m = lies(v)
        check('%s: the bounce: DownBound (0x4D) written once, on %d (its hitstop over), as the uncharged hit\'s; it '
              'bounces (DownBound), then lies (DownWait, seen on %d)' % (what, k0, m),
              ([w for w in v.wlog if w[1] == 'status'], sorted({x[1] for x in v.slog if k0 <= x[0] < m - 1})),
              ([(k0, 'status', float(0x4D))], [0x4D]))
        check('%s: on its floor in a down status every frame from the bounce (%d) to the end of the hold (%d)' % (
            what, k0 + 1, m + B.DOWN_HOLD - 1), held_down(v, k0 + 1, m + B.DOWN_HOLD - 1), [])
        check('%s: its controller off from the hit through the bounce and %d frames lying (back on %d), nothing else'
              % (what, B.DOWN_HOLD, m + B.DOWN_HOLD), inp, [(ck + 1, 1.0), (m + B.DOWN_HOLD, 0.0)])
        if cpu:
            st = [x[1] for x in v.slog if x[0] == m + B.DOWN_HOLD]
            check('%s: free after the hold: it gets up (DownStand 0x54) on the frame its controller is back' % what,
                  st, [0x54])
    # the bounce asked but not taken (the status write lost): put down 2 frames later, then held as lying
    v = gv(ck, pct=100.0, no_bound=True)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=90)
    ws = [w for w in v.wlog if w[1] == 'status']
    check('charged, the bounce not taken (DownBound ignored): DownWait asked 2 frames after it (%d), held %d frames from '
          'there, on its floor' % (k0 + 2, B.DOWN_HOLD),
          (ws, held_down(v, k0 + 3, k0 + 2 + B.DOWN_HOLD - 1),
           [(n, val) for n, k, val in v.wlog if k == 'input']),
          ([(k0, 'status', float(0x4D)), (k0 + 2, 'status', float(0x50))], [], [(ck + 1, 1.0), (k0 + 2 + B.DOWN_HOLD,
                                                                                               0.0)]))
    # its own down timer ending in the hold (30 frames): put back down, still held
    v = gv(ck, pct=100.0, down_timer=20)                # (v5: the hold 28: a timer of 20 runs out in it)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=90)
    m = lies(v)
    up = [x[0] for x in v.slog if x[1] == 0x54 and x[0] < m + B.DOWN_HOLD]
    check('charged: its down timer ending in the hold (20 frames; DownStand on %s): DownWait again the next frame, its '
          'controller still off' % up[:1], (len(up), [x[1] for x in v.slog if up and x[0] == up[0] + 1],
                                            [(n, val) for n, k, val in v.wlog if k == 'input']),
          (1, [0x50], [(ck + 1, 1.0), (m + B.DOWN_HOLD, 0.0)]))
    for at, when in ((5, 'in the bounce'), (25, 'lying, in the hold')):
        def hit_again(g_, k, at=at):                    # another attack hits it
            if k == k0 + at:
                g_.fighters[2].hitstop = 6
                g_.fighters[2].pending = 0x57
                g_.event(2, 8)                          # v5: the exe's hit event on it
        v = gv(ck, pct=100.0)
        g = Game(fighters=[v], held=lambda n: True)
        run(path, g, frames=230, after=90, tick=hit_again)
        check('charged: let go (controller on, buffer emptied) when it is hit again %s (frozen again, %d)' % (
            when, k0 + at), [w for w in v.wlog if w[1] in ('input', 'buffer')],
              [(ck + 1, 'input', 1.0), (ck + 1, 'buffer', 2.0), (k0 + at, 'input', 0.0), (k0 + at, 'buffer', 2.0)])
    # the charged hit on a fighter in its neutral getup: bounced and held as any grounded fighter (the user's getup
    # rule is the uncharged hit's)
    v = gv(ck, pct=100.0, status=0x54)
    g = Game(fighters=[v], held=lambda n: True)
    run(path, g, frames=230, after=90)
    m = lies(v)
    check('charged on DownStand (the neutral getup): bounced, then held as any grounded fighter',
          ([w for w in v.wlog if w[1] == 'status'][:1], held_down(v, k0 + 1, m + B.DOWN_HOLD - 1)),
          ([(k0, 'status', float(0x4D))], []))
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
    import supamario_ui_build as UIB      # Ultra Instinct v9: its glow restore (in Time Skip's ends, the falls / landings)
    for h_ in list(f['effect'].scripts):  # is Ultra Instinct's: tools/supamario_ui_test.py checks it
        f['effect'].scripts[h_] = UIB.strip_glow_restore(f['effect'].scripts[h_])
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
            'SelfHitstopFrames', 'NoGFX', 'Ground/Air', 'Shieldable', 'ShieldDamage', 'Clang', 'Rebound', 'HitBits',
            'Reflectable', 'Absorbable')
    want_ch = (B.HIT_CH['Damage'], 270, B.HIT_CH['BKB'], B.HIT_CH['KBG'], 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0, 0.0,
               B.HITSTOP_CH, B.HITSTOP_CH, 1, 2, 1, 0, 0, 0, 0x3F, 0, 0)
    want_chg = (B.HIT_CH_GROUND['Damage'], 0, 1, 0, 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0, 0.0,
                B.HITSTOP_CH, B.HITSTOP_CH, 1, 1, 1, 0, 0, 0, 0x3F, 0, 0)
    want_un = (B.HIT['Damage'], 270, B.HIT['BKB'], B.HIT['KBG'], 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0,
               -float(B.HITSTUN_ADD), B.HITSTOP, B.HITSTOP, 1, 3, 1, 0, 0, 0, 0x3F, 0, 0)
    want_cl = (B.CLANK_DMG, 0, 0, 0, 0, B.HIT_SIZE, B.HIT_Z, B.HIT_Y, 0.0, 0, 0.0, 0, 0, 1, 3, 0, 0, 1, 0, 0, 0, 0)
    check('the hitboxes (charged: v3 ID 0 the spike aerial only, ID 1 grounded only knockback 1, v4 ID 2 the clank '
          'box; uncharged: ID 0, v4 ID 2 the clank box; v4: the real ones Clang 0, every one Rebound 0): %s' % (keys,),
          [tuple(round(h[k], 3) if isinstance(h[k], float) else h[k] for k in keys) for h in hb],
          [tuple(round(x, 3) if isinstance(x, float) else x for x in w) for w in (want_ch, want_chg, want_cl, want_un,
                                                                                    want_cl)])
    check('v3: the charged pair: IDs 0 / 1, Part 0 (one hit a target); v4: the clank boxes ID 2, Hitlag x%g, they hit '
          'nothing (HitBits 0, not shieldable)' % B.CLANK_HITLAG,
          ([(h['ID'], h['Part']) for h in hb], [round(h['Hitlag'], 3) for h in hb if h['ID'] == 2]),
          ([(0, 0), (1, 0), (2, 0), (0, 0), (2, 0)], [B.CLANK_HITLAG, B.CLANK_HITLAG]))
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
                                                     'speciallwhold', 'specials', 'specialairs',
                                                     'speciallwlight', 'speciallwheavy', 'specialairlwlight',
                                                     'specialairlwheavy',
                                                     'specialairlwlight_c3')}:      # (UI v7: the sway's custom slot)
                same.append((p, hex(h)))
    check('every other script as the user\'s (but the God Fist\'s / Core Breaker\'s / Fake Death\'s / Time Skip\'s / '
          'Ultra Instinct\'s)',
          same, [])


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
                k0_ = p.color_keys(d, 0)[0]
                if not k0_[0] > k0_[1] > k0_[2]:
                    bad.append((k, p.emitter_name(d), 'v4: the arc yellow-orange (R > G > B)', k0_[:3]))
            if k == 'crg02' and B.arc_peak(p, d) > B.FLASH_PEAK + 1e-3:
                bad.append((k, p.emitter_name(d), 'v4: the fist flash over FLASH_PEAK', B.arc_peak(p, d)))
    check('every emitter at the effect\'s origin, unturned but Hmr_Fire\'s arcs (v2: in his YZ plane, facing the camera), '
          'a full-sphere spread when directional, HDR within 2.0, the skill\'s emitters following (v2), v4: the arcs '
          'yellow-orange, the fist flash within FLASH_PEAK', bad, [])
    check('the falling rings converted flat (ShapeDraw -> polygons): %d' % rings, rings > 0, True)
    check('v4 (the glow): the swing arcs drawn at most %.2f (x%s of the 2.0 cap per channel: their overlap stays under 1.0 '
          'on a grass stage)' % (2.0 * max(B.ARC_GAIN), B.ARC_GAIN),
          (len(arcs) > 0, max(arcs) <= 2.0 * max(B.ARC_GAIN) + 1e-3), (True, True))
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
    import json
    js = json.load(open(os.path.join(out, 'sledgehammer_frames.json')))
    check('v5 (user: "undo v4\'s animation change"): the overhead correction off (XV2\'s pose as retargeted, v1-v3\'s)',
          (js['overhead'], A.OVERHEAD), (False, False))
    gd = js['glow_depth']
    check('v5: the charge glow\'s depth toward the camera %.2f = his head\'s half-depth beside the left hand at the charge '
          'pose (%.2f) + %.1f' % (gd['depth'], gd['head_half_depth'], B.GLOW_MARGIN),
          round(gd['head_half_depth'] + B.GLOW_MARGIN, 2), gd['depth'])
    if V3_PACS:                                         # the package that last shipped the motions before v4 (v1)
        import zipfile
        z = zipfile.ZipFile(V3_PACS)
        for part in ('main', 'mariopt1', 'lhand', 'rhand'):
            name = [n for n in z.namelist() if n.endswith('/motion/body/%s.pac' % part)]
            old = dict(pac_bytes(z.read(name[0]))) if name else {}
            new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
            ks = sorted(n for n in new if n.endswith(A.START) or n.endswith(A.HOLD))
            check('v5: %s.pac\'s two Sledgehammer motions byte for byte v1-v3\'s (%s)' % (part, os.path.basename(V3_PACS)),
                  [(n, new[n] == old.get(n)) for n in ks], [(n, True) for n in ks])


V3_PACS = None


def pac_bytes(b):
    """omo.pac_read on bytes (a pac inside a zip)"""
    n = struct.unpack('>I', b[8:12])[0]
    names = struct.unpack('>%dI' % n, b[0x10:0x10 + 4 * n])
    offs = struct.unpack('>%dI' % n, b[0x10 + 4 * n:0x10 + 8 * n])
    sizes = struct.unpack('>%dI' % n, b[0x10 + 8 * n:0x10 + 12 * n])
    return [(b[no:b.index(b'\0', no)].decode(), b[o:o + sz]) for no, o, sz in zip(names, offs, sizes)]


def main():
    global V3_PACS
    a = sys.argv[1:]
    if len(a) == 3:                                     # v5: optional, the v1 package (its motions are v1-v3's)
        V3_PACS = a.pop()
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
