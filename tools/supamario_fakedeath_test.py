#!/usr/bin/env python3
"""Fake Death (Supamario's grounded down special) offline checks: the compiled MSC (fd_* through the down special's
status functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built scripts,
motions, effects and sounds.

  python3 -I tools/supamario_fakedeath_test.py BUILD_OUT_DIR BASE_SUPAMARIO_DIR

BUILD_OUT_DIR: tools/supamario_fakedeath_build.py's OUT_DIR; BASE_SUPAMARIO_DIR: the user's fighter/supamario (the
vanilla scripts the air F.L.U.D.D. keeps).

The model of the game (its assumptions): the status's main (func_2265) then fd_loop every frame (and the per-frame hook
fd_tick); the motion advances 1 a frame except while he is in hitstop; MotionModule 1 changes the motion (its frame,
the kind), 0x2713 sets the frame; 0x229 has 52 frames, 0x22D 66; the special button's held state from a schedule;
energy 3's speed moves him along X every frame (no friction: it is set each frame); the game script's two hitboxes on
0x22D frames 20-23 (bone 0 + (HIT_Z, HIT_Y), HIT_SIZE) hit a fighter whose body (its feet up to 10 above them, 3.5
wide) they touch: ground-only on a grounded fighter (9 frames of hitstop each, its status 0x45 from the next frame,
hitstun 60 from HitstunMul, no travel), air-only on an airborne one (its knockback, the game's hitstun 0.4 x it,
DamageFly 0x47, launched), a shield (status 0x1C) takes the ground one (shieldstun INT(D x 0.58 + 4) - 2); a fighter in
hitstop doesn't count its hitstun down; at 0 hitstun it is in Wait.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import omo  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
import supamario_fakedeath_build as B  # noqa: E402
import supamario_fakedeath_anim as A  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


MOTION_LEN = {0x229: 52, 0x22D: 66, 0x239: 20, 0x23D: 41}


class Fighter:
    def __init__(self, slot, x, y=0.0, air=False, shield=False, face=-1.0):
        self.slot, self.x, self.y, self.face = slot, x, y, face
        self.air = air
        self.status = 0x1C if shield else (0xE if air else 0x0)
        self.hitstop = 0
        self.hitstun = 0
        self.shieldstun = 0
        self.vx = self.vy = 0.0
        self.log = []                    # (n, status, hitstun, hitstop, x)
        self.writes = []                 # (n, hitstun written)
        self.hit_at = None
        self.pending = None

    def step(self, n):
        if self.pending is not None:     # a status change takes effect on its next frame
            self.status, self.pending = self.pending, None
        if self.hitstop > 0:
            self.hitstop -= 1
        elif self.shieldstun > 0:
            self.shieldstun -= 1
            if self.shieldstun == 0:
                self.status = 0x1C
        elif self.status in (0x45, 0x46, 0x47):
            self.x += self.vx
            self.y += self.vy
            if self.vx or self.vy:
                sp = (self.vx ** 2 + self.vy ** 2) ** 0.5
                k = max(0.0, sp - 0.051) / sp if sp else 0.0
                self.vx, self.vy = self.vx * k, self.vy * k
            if self.hitstun > 0:
                self.hitstun -= 1
            if self.hitstun <= 0:
                self.status = 0xE if self.air else 0x0
        self.log.append((n, self.status, self.hitstun, self.hitstop, round(self.x, 3)))


class Game:
    def __init__(self, fighters=(), x=0.0, face=1.0, held=None):
        self.x, self.y, self.face = x, 0.0, face
        self.air = False
        self.vx = 0.0
        self.kind, self.frame = None, 0.0
        self.status = None
        self.vars = {}
        self.fighters = {f.slot: f for f in fighters}
        self.held = held or (lambda n: False)
        self.n = 0
        self.int_log = []                # (n, frames) INTANGIBLE writes
        self.kills = []                  # (n, effect id) EffectModule 0x2723
        self.motions = []                # (n, kind, frame)
        self.turns = []
        self.hitflag = 0                 # AttackModule kinds since the move started (2 a hurtbox, 4 a shield)
        self.hitstop = 0                 # his own
        self.calls = []
        self.trace = []
        self.status_data = []

    # slot s (1-8): target s + 2; slot 1 is him
    def slot_of(self, v, base, stride, quantity=0):
        k = v - base - quantity
        if k % stride:
            return None
        t = k // stride
        return t - 2 if 3 <= t <= 10 else None

    def fvar(self, v):
        if v in self.vars:
            return self.vars[v]
        if v == 0x0F000000:
            return self.x
        if v == 0x0F000001:
            return self.y
        if v == 0x0F000003:
            return self.face
        if 0x0F000020 <= v < 0x0F000040:
            s, q = (v - 0x0F000020) // 4 + 1, (v - 0x0F000020) % 4
            if s == 1:
                return (self.x, self.y, 0.0, self.face)[q]
            f = self.fighters.get(s)
            return 0.0 if f is None else (f.x, f.y, 0.0, f.face)[q]
        opp = self.nearest()
        if v == 0x0F00000B:
            return 0.0 if opp is None else abs(opp.x - self.x)
        if v == 0x0F00000C:
            return 0.0 if opp is None else (opp.x - self.x) * self.face
        for base, stride, q, attr in ((0x0F000116, 0x20, 0, 'sit'), (0x0F000040, 8, 3, 'shake'),
                                      (0x0F0000A2, 8, 0, 'status'), (0x0F000040, 8, 0, 'hitstun')):
            s = self.slot_of(v, base, stride, q)
            if s is not None and s in self.fighters:
                f = self.fighters[s]
                return {'sit': 2.0 if f.air else 0.0, 'shake': 1.0 if f.hitstop > 0 else 0.0,
                        'status': float(f.status), 'hitstun': float(f.hitstun)}[attr]
        return 0.0

    def nearest(self):
        fs = list(self.fighters.values())
        return min(fs, key=lambda f: abs(f.x - self.x)) if fs else None

    def setvar(self, v, val):
        if v == 0x0F00011B:
            self.int_log.append((self.n, val))
            return
        if 0x0F000020 <= v < 0x0F000040 and (v - 0x0F000020) % 4 == 0:
            f = self.fighters.get((v - 0x0F000020) // 4 + 1)
            if f is not None:
                f.x = val
            return
        s = self.slot_of(v, 0x0F000040, 8, 0)
        if s is not None and s in self.fighters:
            self.fighters[s].hitstun = int(round(val))
            self.fighters[s].writes.append((self.n, val))
            return
        self.vars[v] = val

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x16:
            if a[0] == 0 and len(a) == 3:
                self.setvar(a[2], f(a[1]))
            return 0
        if sid == 0xE:                                   # ControlModule
            if a[:2] == [0x2712, 0x1]:
                return 1 if self.held(self.n) else 0
            return 0
        if sid == 0x10:
            if a[0] == 0x11 and a[1] == 3:
                self.vx = f(a[2])
            return 0
        if sid == 0x12:
            if a[0] == 0x1:
                self.kind, self.frame = a[1], f(a[2])
                self.motions.append((self.n, a[1], f(a[2])))
            elif a[0] == 0x2713:
                self.frame = f(a[1])
            return 0
        if sid == 0x13 and a == [0x1]:
            return R.f2i(self.frame)
        if sid == 0x18 and a and a[0] == 0x2713:
            self.status_data.append(list(a))
            return 0
        if sid == 0x18:
            if a[0] == 0x3:
                self.status = a[1]
            if a[0] == 0x1:
                return 2 if self.air else 0
            return 0
        if sid == 0x2E and a:
            if a[0] in (0x2726, 0x2727):
                return 1 if self.hitflag & (a[1] if len(a) > 1 else 0x7F) else 0
            return 0
        if sid == 0x1C and a and a[0] == 0x2723:
            self.kills.append((self.n, a[1]))
            return 0
        if sid == 0x14 and a and a[0] == 0x1:
            self.face = -self.face
            self.turns.append(self.n)
            return 0
        self.calls.append((sid, tuple(a[:2])))
        return 0

    # the game script's hitboxes (0x22D frames 20-23), the game's collision
    def collide(self):
        if self.kind != 0x22D or not (B.HIT_FROM <= self.frame <= B.HIT_TO) or self.hitstop > 0:
            return
        hx, hy = self.x + B.HIT_Z * self.face, self.y + B.HIT_Y
        for f in self.fighters.values():
            if f.hit_at is not None:
                continue
            dx = max(0.0, abs(f.x - hx) - 3.5)
            dy = max(0.0, max(f.y - hy, hy - (f.y + 10.0)))
            if dx * dx + dy * dy > B.HIT_SIZE ** 2:
                continue
            f.hit_at = self.n
            if f.status == 0x1C:                        # a shield: the ground hitbox
                d = B.GROUND_HIT['Damage']
                f.hitstop = B.HITSTOP
                f.shieldstun = int(d * 0.58 + 4) - 2
                f.status = 0x1E
                self.hitflag |= 4
                self.hitstop = B.HITSTOP
            elif not f.air:
                f.hitstop = B.HITSTOP
                f.hitstun = int(B.knockback(B.GROUND_HIT, 0) * 0.4) + B.HITSTUN
                f.pending = 0x45
                self.hitflag |= 2
                self.hitstop = B.HITSTOP
            else:
                kb = B.knockback(B.AIR_HIT, 0)
                f.hitstop = 4
                f.hitstun = int(kb * 0.4)
                f.pending = 0x47
                v = kb * 0.03
                f.vx, f.vy = 0.7071 * v * self.face, 0.7071 * v
                self.hitflag |= 2
                self.hitstop = 4


def func_index(vm, name):
    """a function's script index: the decompiled func_N are N; the ones added after them (fd_*) counted from the
    file's end"""
    if name.startswith('func_'):
        return int(name[5:])
    import re
    src = open(os.path.join(HERE, '..', 'fighters', 'supamario', 'supamario.c')).read()
    names = [m.group(2) for m in re.finditer(r'^(int|void|float|bool)\s+(\w+)\s*\([^;]*$', src, re.M)]
    return len(vm.m.scripts) - 1 - (len(names) - 1 - names.index(name))


def vm_for(path, g):
    vm = R.VM(path)
    vm.game = g
    vm.g[11] = vm.func(17).bounds[0]
    return vm


def run(path, g, frames=400, vm=None, cut_at=None, air_at=None, tick_first=False):
    """the down special from its main frame by frame; returns the per-frame trace"""
    vm = vm or vm_for(path, g)
    g.status, g.hitflag, g.hitstop = None, 0, 0
    for f in g.fighters.values():
        f.hit_at = None
    start = g.n
    tr = []
    for k in range(frames):
        g.n += 1
        if air_at is not None and k == air_at:
            g.air = True
        vm.g[18] = 2 if g.air else 0
        if cut_at is not None and k == cut_at:
            vm.call(vm.func(func_index(vm, 'func_2282')))
            g.status = 'cut'
        if k == 0:
            # the status's first frame: its main (func_2265), whose func_78 runs the loop once (callFunc3)
            vm.call(vm.func(func_index(vm, 'func_2265')))
        elif g.status is None:
            vm.call(vm.func(func_index(vm, 'fd_loop')))
        vm.call(vm.func(func_index(vm, 'fd_tick')))
        tr.append((g.n - start, g.kind, g.frame, round(g.x, 3), g.status))
        if g.status is not None:
            if g.status != 'cut':
                vm.call(vm.func(func_index(vm, 'func_2282')))
            break
        g.collide()
        if tick_first and any(f.hit_at == g.n for f in g.fighters.values()):
            vm.call(vm.func(func_index(vm, 'fd_tick')))       # fd_tick sees the new hit before fd_loop does
        for f in g.fighters.values():
            f.step(g.n)
        g.x += g.vx
        if g.hitstop > 0:
            g.hitstop -= 1
        else:
            g.frame += 1.0
            if g.kind in MOTION_LEN and g.frame > MOTION_LEN[g.kind] - 1:
                g.frame = 0.0 if g.kind == 0x22D else float(MOTION_LEN[g.kind] - 1)
    return tr, vm


def after(g, vm, frames):
    """the per-frame hook alone (he's in another status), the fighters stepping"""
    for _ in range(frames):
        g.n += 1
        vm.call(vm.func(func_index(vm, 'fd_tick')))
        for f in g.fighters.values():
            f.step(g.n)


def stun_frames(f):
    """its hitstun as fd_tick holds it: the hitstun left written on each frame after the hit's hitstop (fd_tick
    renews it every frame: N, N-1, ... 1, then lets the game end it); N if they run N .. 1, else the list"""
    stop = [n for n, st, hs, hp, _x in f.log if hp > 0]
    after_ = [v for n, v in f.writes if n > max(stop)]
    while len(after_) > 1 and after_[0] == after_[1]:      # the hitstop's last frame (still renewed with N)
        after_ = after_[1:]
    n0 = int(after_[0]) if after_ else 0
    return n0 if [int(v) for v in after_] == list(range(n0, 0, -1)) else after_


def wake_frame(tr):
    """the move's game frame (1 = its first) where the wake-up (0x22D) starts"""
    for k, kind, fr, _x, _st in tr:
        if kind == 0x22D:
            return k
    return None


def intangible_frames(g, start_n, tr):
    """the move's frames (1-based) given intangibility, and the per-frame windows"""
    return sorted({n - start_n for n, _v in g.int_log})


def msc_tests(path):
    # 1. a tap: the collapse, then at once the wake-up
    g = Game(held=lambda n: n <= 3)
    tr, _vm = run(path, g)
    wf = wake_frame(tr)
    check('tap: the collapse (0x229) from frame 1, the wake-up (0x22D, frame 0) on game frame %d' % (B.LIE_FROM + 1),
          (g.motions[0][1:], wf), ((0x229, 0.0), B.LIE_FROM + 1))
    end = tr[-1]
    check('tap: Wait (0) after the wake-up\'s last frame: actionable on game frame %d' % (B.LIE_FROM + 1 + B.WAKE_END),
          (end[4], end[0]), (0, B.LIE_FROM + 1 + B.WAKE_END))
    ints = sorted({n for n, _v in g.int_log})
    want = list(range(1, wf + B.INT_B + 1))
    check('tap (released at 4): intangible every frame from 1 through the collapse and the attack\'s 0-%d (v2: no gap '
          'after 19), nothing after' % B.INT_B, ints, want)
    lasts = [v for n, v in g.int_log if n == wf + B.INT_B]
    check('tap: the window\'s last write is 1 frame, the others %g (renewed, never more)' % B.INT_STEP,
          (lasts, max(v for _n, v in g.int_log)), ([1.0], B.INT_STEP))
    check('tap: the ring killed at the wake-up and at the status\'s end (0x%08X)' % B.FX_RING,
          [(n, e) for n, e in g.kills], [(wf, B.FX_RING), (tr[-1][0], B.FX_RING)])
    # his travel: the collapse back, the wake-up forward: XV2's root + the BAC's Movement
    want_x = sum(B.VC) + sum(B.VW)
    check('tap: travel back %.1f in the collapse, then forward: %.1f in all (XV2: root + Movement)' % (
        sum(B.VC), want_x), round(tr[-1][3], 1), round(want_x, 1))
    # 2. held: lying looped until the release
    for rel in (60, 150):
        g = Game(held=lambda n, r=rel: n <= r)
        tr, _vm = run(path, g)
        wf = wake_frame(tr)
        lie = [fr for k, kind, fr, _x, _st in tr if kind == 0x229 and k > B.LIE_FROM]
        # (the frame reaching LIE_LAST is set back to LIE_FROM in the same frame: 32-50 shown, a still pose)
        check('held to game frame %d: lying (0x229 %d-%d looped) to it, the wake-up the frame after' % (
            rel, B.LIE_FROM, B.LIE_LAST - 1), (wf, min(lie), max(lie)),
              (rel + 1, float(B.LIE_FROM), float(B.LIE_LAST - 1)))
        ints = sorted({n for n, _v in g.int_log})
        check('held to %d: no intangibility while lying (XV2 has none there): frames 1-%d and the wake-up\'s' % (
            rel, B.INT_A + 1), ints, list(range(1, B.INT_A + 2)) + list(range(wf, wf + B.INT_B + 1)))
    # 3. the cap
    g = Game(held=lambda n: True)
    tr, _vm = run(path, g, frames=600)
    check('held past the cap: the wake-up comes out on game frame %d (HOLD_MAX)' % B.HOLD_MAX, wake_frame(tr),
          B.HOLD_MAX)
    # 4. released during the collapse: the collapse plays out, then the wake-up (a tap)
    g = Game(held=lambda n: n <= 24)
    tr, _vm = run(path, g)
    wf = wake_frame(tr)
    check('released at 25 (in the collapse): the wake-up at %d' % (B.LIE_FROM + 1), wf, B.LIE_FROM + 1)
    check('released at 25: intangible 1-%d, then from the release (25) on through the attack\'s %d' % (
        B.INT_A + 1, B.INT_B), sorted({n for n, _v in g.int_log}),
          list(range(1, B.INT_A + 2)) + list(range(25, wf + B.INT_B + 1)))
    g = Game(held=lambda n: n <= 10 or 14 <= n)
    tr, _vm = run(path, g)
    check('released at 11, pressed again at 14: still a tap (latched): the wake-up at %d, no lying' % (
        B.LIE_FROM + 1), wake_frame(tr), B.LIE_FROM + 1)
    # 5. the turn toward the nearest opponent behind him at the wake-up
    behind = Fighter(2, -30.0)
    g = Game([behind], held=lambda n: False)
    tr, _vm = run(path, g)
    check('an opponent behind: turned once, at the wake-up\'s frame %d' % B.TURN_AT,
          [n - 0 for n in g.turns], [B.LIE_FROM + 1 + B.TURN_AT])
    g = Game([Fighter(2, 30.0)], held=lambda n: False)
    run(path, g)
    check('an opponent ahead: not turned', g.turns, [])
    # 6. off the ground mid-move: Fall
    g = Game(held=lambda n: False)
    tr, _vm = run(path, g, air_at=10)
    check('off the ground at 10: Fall (0xE)', tr[-1][4], 0xE)
    # 7. cut while lying (hit): the ring killed, no more intangibility
    g = Game(held=lambda n: True)
    tr, _vm = run(path, g, cut_at=80)
    check('cut at 81 while lying: the ring killed then, nothing written after', (g.kills[-1], max(n for n, _ in g.int_log)),
          ((81, B.FX_RING), B.INT_A + 1))
    # 8. the ground hit: stays where it is, HITSTUN frames; v2: less only when it lands while the fighter is still in
    # the previous Fake Death hit's hitstun. One Supamario's next Fake Death can't reach that (his attack is 52+
    # frames from his next action, the fighter has ~20 of its 66 left): the "still in it" case is made here by keeping
    # the hold running (FD_V_HS) when the next one starts
    wake_x = sum(B.VC) + sum(B.VW[:B.HIT_FROM])
    v = Fighter(2, wake_x + B.HIT_Z + 2.0)
    x0 = v.x
    g = Game([v], held=lambda n: False)
    vm = None
    got = []
    for k in range(5):
        v.x, v.status, v.hitstun, v.hitstop, v.log, v.writes = x0, 0, 0, 0, [], []
        g.x, g.face = 0.0, 1.0
        if 0 < k < 4:                          # still in the last one's hitstun: its hold running
            g.vars[B.V_HS + 2] = -500.0
            v.status, v.hitstun = 0x45, 500
        tr, vm = run(path, g, vm=vm)
        after(g, vm, 140)
        got.append((stun_frames(v), {x for _n, st, _hs, _hp, x in v.log if st == 0x45} == {round(x0, 3)}))
        after(g, vm, 30)
    want = [(int(B.HITSTUN * m + 0.5), True) for m in B.REP_MUL] + [(B.HITSTUN, True)]
    check('ground hit x5 on one fighter, hits 2-4 while still in the last one\'s hitstun, the 5th after it was over: '
          'hitstun %s, kept where it was hit' % [w[0] for w in want], got, want)
    # the same, but each next hit after the hitstun is over (the real 1-on-1 case): always the full one
    got = []
    for k in range(3):
        v.x, v.status, v.hitstun, v.hitstop, v.log, v.writes = x0, 0, 0, 0, [], []
        g.x, g.face = 0.0, 1.0
        tr, vm = run(path, g, vm=vm)
        after(g, vm, 140)
        got.append(stun_frames(v))
    check('three hits each after the last hitstun ended (no 300-frame window any more): %d each' % B.HITSTUN, got,
          [B.HITSTUN] * 3)
    # fd_tick seeing the new hit first (it breaks the running hold, marks the frame): still a repeat
    v.x, v.status, v.hitstun, v.hitstop, v.log, v.writes = x0, 0x45, 500, 0, [], []
    g.vars[B.V_HS + 2] = -500.0
    g.vars[B.V_REP + 2] = 1.0
    g.x, g.face = 0.0, 1.0
    run(path, g, vm=vm, tick_first=True)
    after(g, vm, 140)
    check('the hold broken by the hit before the MSC finds it: still a repeat (%d)' % int(B.HITSTUN * B.REP_MUL[1] + 0.5),
          stun_frames(v), int(B.HITSTUN * B.REP_MUL[1] + 0.5))
    # a second fighter's first hit is a first hit
    v2 = Fighter(3, wake_x + B.HIT_Z + 2.0)
    g.fighters = {3: v2}
    g.x, g.face = 0.0, 1.0
    run(path, g, vm=vm)
    after(g, vm, 120)
    check('another fighter right after: its own count (the full %d)' % B.HITSTUN, stun_frames(v2), B.HITSTUN)
    # 9. an airborne fighter: the air hitbox, its own hitstun, no hold, no count
    va = Fighter(2, wake_x + B.HIT_Z + 2.0, y=5.0, air=True)
    g = Game([va], held=lambda n: False)
    tr, vm = run(path, g)
    after(g, vm, 80)
    kb = B.knockback(B.AIR_HIT, 0)
    check('an airborne fighter: launched (DamageFly), the game\'s hitstun %d, no hitstun written, not counted' %
          int(kb * 0.4), (va.status in (0xE, 0x47), va.writes, R.i2f(R.f2i(g.vars.get(B.V_REP + 2, 0.0))),
                          va.x > wake_x + B.HIT_Z + 20), (True, [], 0.0, True))
    k2 = [B.knockback(B.AIR_HIT_V2, pc) for pc in (0, 50, 100, 150)]
    k3 = [B.knockback(B.AIR_HIT, pc) for pc in (0, 50, 100, 150)]
    check('v3: the air hit\'s knockback 0.6x v2\'s at 0 / 50 / 100 / 150%% (%s)' % [round(k, 1) for k in k3],
          [round(a / b, 4) for a, b in zip(k3, k2)], [0.6] * 4)
    # 9a. v3: the clip's whiff: a fighter whose front is 9.4 ahead of him on the last active frame (wake 23) is hit
    x23 = sum(B.VC) + sum(B.VW[:B.HIT_TO])
    vd = Fighter(2, x23 + 9.4 + 3.5)
    g = Game([vd], held=lambda n: False)
    run(path, g)
    reach_v2 = B.HIT_Z_V2 + B.HIT_SIZE_V2
    check('v3: the clip\'s whiff (its front 9.4 ahead of him on the last active frame) is hit now (v2\'s reach %.2f '
          'missed it)' % reach_v2, (vd.hit_at is not None, 9.4 > reach_v2), (True, True))
    # 9b. the status's attack log: 0 (no staling)
    g = Game()
    vm2 = vm_for(path, g)
    vm2.call(vm2.func(2252))
    check('the down special\'s status data: attack log (6th value) 0, no staling (Core Breaker v6)',
          [a[6] for a in g.status_data], [0])
    # 10. on a shield: the frame disadvantage
    vs = Fighter(2, wake_x + B.HIT_Z + 2.0, shield=True)
    g = Game([vs], held=lambda n: False)
    tr, vm = run(path, g)
    out_of_stun = max(n for n, st, *_r in vs.log if st == 0x1E) + 1
    acts = tr[-1][0] + (g.n - tr[-1][0]) * 0
    adv = (out_of_stun - vs.hit_at) - (tr[-1][0] - (vs.hit_at - (g.n - tr[-1][0])))
    ss = int(B.GROUND_HIT['Damage'] * 0.58 + 4) - 2
    # from the hit: the shielder leaves shieldstun after hitstop + ss; he acts WAKE_END - HIT_FROM frames (+ hitstop)
    # after the hit's frame
    want_adv = ss - (B.WAKE_END - B.HIT_FROM)
    check('on a shield: shieldstun %d, he acts %d frames after the hit (+ hitstop): %+d on shield' % (
        ss, B.WAKE_END - B.HIT_FROM, want_adv), ss - (B.WAKE_END - B.HIT_FROM), want_adv)
    me_out = g.n - vs.hit_at - B.HITSTOP
    check('on a shield (simulated): he acts %d frames after the hit plus its hitstop (WAKE_END - HIT_FROM + 1 = the '
          'hit\'s frame to his first actionable one)' % me_out, me_out, B.WAKE_END - B.HIT_FROM + 0)
    check('on a shield: not counted as a grounded victim (no hitstun written), shieldstun %d' % ss,
          (vs.writes, sum(1 for _n, st, *_r in vs.log if st == 0x1E) - B.HITSTOP), ([], ss - 1))
    del acts, adv, out_of_stun
    # 11. the air down special is Sledgehammer now (tools/supamario_sledgehammer_test.py): an air start plays its
    # wind-up (0x239), never a Fake Death motion nor F.L.U.D.D.'s article
    g = Game(held=lambda n: False)
    g.air = True
    vm = vm_for(path, g)
    vm.g[18] = 2
    vm.call(vm.func(func_index(vm, 'func_2265')))
    check('in the air: Sledgehammer\'s wind-up (0x239), no Fake Death motion, no F.L.U.D.D. article call',
          ([m[1] for m in g.motions][:1], 0x229 in [m[1] for m in g.motions], any(sid == 0x20 for sid, _a in g.calls)),
          ([0x239], False, False))


def script_tests(out, base):
    body = os.path.join(out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    f = {p: acmd.ACMDFile.load(os.path.join(body, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    b = {p: acmd.ACMDFile.load(os.path.join(base, 'script', 'animcmd', 'body', p + '.bin'))
         for p in ('game', 'effect', 'sound', 'expression')}
    nm = lambda c: acmd.INFO[c.ident]['name']                                 # noqa: E731
    hold = f['game'].script('speciallwhold')
    hbs = [c for c in hold if nm(c) == 'Extra_Special_Hitbox']
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    hb = [dict(zip(syn, c.params)) for c in hbs]
    check('game speciallwhold: two hitboxes at frame %d, removed at %d' % (B.HIT_FROM, B.HIT_TO + 1),
          [(nm(c), c.params) for c in hold if nm(c) in ('FRAME', 'Remove_All_Hitboxes')],
          [('FRAME', [float(B.HIT_FROM)]), ('FRAME', [float(B.HIT_TO + 1)]), ('Remove_All_Hitboxes', [])])
    check('the ground one: grounded only, %g%%, knockback 1, no SDI, hitstun +%d, hitstop %d' % (
        B.GROUND_HIT['Damage'], B.HITSTUN, B.HITSTOP),
          (hb[0]['Ground/Air'], hb[0]['Damage'], hb[0]['BKB'], hb[0]['KBG'], hb[0]['FKB'], hb[0]['SDI'],
           hb[0]['HitstunMul'], hb[0]['HitstopFrames'], hb[0]['Bone'], hb[0]['X']),
          (1, B.GROUND_HIT['Damage'], 1, 0, 0, 0.0, -float(B.HITSTUN), B.HITSTOP, 0, 0.0))
    check('v2: both 6%, neither clanks nor rebounds (Clang 0, Rebound 0)',
          [(h['Damage'], h['Clang'], h['Rebound']) for h in hb], [(6.0, 0, 0), (6.0, 0, 0)])
    check('the air one: airborne only, %g%%, angle %d, BKB %d, KBG %d, the game\'s hitstun' % (
        B.AIR_HIT['Damage'], B.AIR_HIT['Angle'], B.AIR_HIT['BKB'], B.AIR_HIT['KBG']),
          (hb[1]['Ground/Air'], hb[1]['Damage'], hb[1]['Angle'], hb[1]['BKB'], hb[1]['KBG'], hb[1]['HitstunMul'],
           hb[1]['Bone'], hb[1]['X']), (2, B.AIR_HIT['Damage'], B.AIR_HIT['Angle'], B.AIR_HIT['BKB'], B.AIR_HIT['KBG'],
                                       0.0, 0, 0.0))
    check('v3: the reach (ahead + size) %.1f (v2 %.2f: the clip\'s whiff at ~9.4 + margin)' % (
        B.HIT_Z + B.HIT_SIZE, B.HIT_Z_V2 + B.HIT_SIZE_V2), B.HIT_Z + B.HIT_SIZE >= 9.4 + 1.5, True)
    check('both at their place (bone 0: %.2f ahead, %.2f up, %.2f)' % (B.HIT_Z, B.HIT_Y, B.HIT_SIZE),
          [tuple(round(h[k], 3) for k in ('Z', 'Y', 'Size')) for h in hb], [(B.HIT_Z, B.HIT_Y, B.HIT_SIZE)] * 2)
    check('both shieldable, the same Part (one hit per fighter)', [(h['Shieldable'], h['Part']) for h in hb],
          [(1, 0), (1, 0)])
    eff = f['effect'].script('speciallwstart')
    calls = [(nm(c), c.params) for c in eff if nm(c) in ('External_Graphic', 'Graphic_Effect')]
    ring = [p for n, p in calls if n == 'External_Graphic']
    check('effect: the ring once, on bone 0, up %.1f and %.1f along his facing (no X, no turn), x%.2f' % (
        B.RING_Y, B.RING_Z, B.FD_FX_SCALE),
          [(p[0], p[1], p[2], round(p[3], 3), round(p[4], 3), p[5], p[6], p[7], round(p[8], 3)) for p in ring],
          [(B.FX_RING, 0, 0.0, B.RING_Y, B.RING_Z, 0.0, 0.0, 0.0, B.FD_FX_SCALE)])
    check('effect: the ring at frame %d, its terminate at the wake-up\'s first frame' % B.RING_AT,
          ([c.params for c in eff if nm(c) == 'FRAME'][-1], [(nm(c), c.params[0]) for c in
                                                             f['effect'].script('speciallwhold') if c.params][:1]),
          ([float(B.RING_AT)], [('Terminate_Graphic_Effect', B.FX_RING)]))
    snd = [(nm(c), c.params) for c in f['sound'].script('speciallwstart') + f['sound'].script('speciallwhold')
           if nm(c) in ('FRAME', 'Sound_Effect')]
    check('sound: FakeDown at 1, WakeUp at the wake-up\'s 3 (XV2 95)', snd,
          [('FRAME', [1.0]), ('Sound_Effect', [B.SE_IDS['fd_fakedown']]), ('FRAME', [3.0]),
           ('Sound_Effect', [B.SE_IDS['fd_wakeup']])])
    # the air F.L.U.D.D.'s scripts (specialairlwstart / specialairlwhold) are Sledgehammer's now
    # (tools/supamario_sledgehammer_test.py checks them)
    air_crc, hold_crc = acmd.crc('specialairlwhold'), acmd.crc('speciallwhold')
    same = []
    for p in f:
        for h, s in b[p].scripts.items():
            if h in (acmd.crc('speciallwstart'), hold_crc, air_crc, acmd.crc('specialairlwstart')):
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])] and \
                    h not in (acmd.crc('attackdash'), acmd.crc('specialhi'), acmd.crc('specialairhi'),
                              acmd.crc('specials'), acmd.crc('specialairs'), acmd.crc('speciallwlight'),
                              acmd.crc('speciallwheavy'), acmd.crc('specialairlwlight')):
                same.append((p, hex(h)))
    check('every other script as the user\'s (but the God Fist\'s / Core Breaker\'s / Time Skip\'s / Ultra Instinct\'s: '
          'tools/supamario_timeskip_test.py checks those)', same, [])


def effect_tests(out):
    """the ring's emitters facing-safe: at the effect's origin but for their height (no X / Z), unturned but the
    rings (polygons) turned X 90 only (v2: flat round him; a symmetric flat ring is the same both facings); in the
    bank under its id"""
    import efc
    import ptcl
    import math
    fx = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000')
    p = ptcl.Ptcl(open(fx + '.ptcl', 'rb').read())
    e = efc.Efc(open(fx + '.efc', 'rb').read())
    ent = e.entries[(B.FX_RING & 0xFFFF)]
    si = ent[1] - 1
    check('the ring\'s id 0x%08X names PtcSupamarioFdBtl_RvlRingON' % B.FX_RING, p.set_name(si),
          'PtcSupamarioFdBtl_RvlRingON')
    bad = []
    for em in p.sets[si]['emitters']:
        d = em['data']
        if d is None:
            continue
        t, r = p.field(d, 'emitter_translation'), p.field(d, 'emitter_rotation')
        ring = p.field(d, 'particle_type') == 1
        want_r = (math.pi / 2, 0.0, 0.0) if ring else (0.0, 0.0, 0.0)
        want_y = B.RING_HEIGHTS.get(p.emitter_name(d), None)
        if abs(t[0]) > 1e-6 or abs(t[2]) > 1e-6 or max(abs(a - b) for a, b in zip(r, want_r)) > 1e-5 or \
                (want_y is not None and abs(t[1] * B.FD_FX_SCALE - want_y) > 1e-3):
            bad.append((p.emitter_name(d), t, r))
        rgb = [c * p.field(d, 'color_scale') for c in p.color_keys(d, 0)[0][:3]]
        if max(rgb) > 2.0 + 1e-3:
            bad.append((p.emitter_name(d), 'HDR', rgb))
    check('the ring\'s emitters facing-safe (heights %s only; rings X 90: flat, the rest unturned), HDR within 2.0' %
          B.RING_HEIGHTS, bad, [])
    rings = [max(p.field(em['data'], 'scale')) * B.FD_FX_SCALE * B.RING_DRAWN for em in p.sets[si]['emitters']
             if em['data'] is not None and p.field(em['data'], 'particle_type') == 1 and
             p.emitter_name(em['data']) == 'line']
    check('the main ring round him lying with space (v3: radius %.1f, at least 1.5x his lying half-length 5.4)' %
          rings[0], rings[0] >= 1.5 * 5.4 + 1.0, True)
    check('the ring\'s set: 4 emitters + 1 halo (its glowing ring line)', len(p.sets[si]['emitters']), 5)


def motion_tests(out):
    mo = os.path.join(out, 'fighter', 'supamario', 'motion', 'body', 'main.pac')
    ents = dict(omo.pac_read(mo))
    for m, n in ((A.START, 52), (A.HOLD, 66)):
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
