#!/usr/bin/env python3
"""Byleth (master) v8 / v9 MSC checks: his compiled master.mscsb run in rolloff_hold_test's MSC interpreter against a small
model of the game (fighters/master/README.md "Status: v8").

  python3 -I tools/master_specials_test.py [MASTER.mscsb]     (default: compiled now from fighters/master/master.c)

The model (its assumptions): the status functions are called as the game does (main, then the loop each frame;
the end at a status change); a status change is func_16 -> global11 (func_79: StatusModule(3, status)), recorded;
the motion frame and its end, the special button, the situation and the slots' position variables (positions, status,
situation, damage: tools/position_vars_cave.py's ids) are the test's; CatchModule(0x2712) is "holding someone".
Checked:
 1. Failnaught's charge effects (master_bow_hold1 / hold2, master_bowflare2) are killed, particles too
    (EffectModule(0x2723, id, 1, 1)), at the shot, at the shield cancel, at the status's end and by the status sweep
    leaving 0x152 (user v7: the glow "continues into other actions if the special button is held");
 2. the sweep doesn't kill an effect the new status started on its first frame (the bow glow entering 0x152);
    Aymr's following rocks are killed when SpecialLwHit is left before its frame 60 detaches them;
 3. the up special's catch: a fighter in the capture status 0xBD near him during frames 20 - 26 -> SpecialAirHiHit
    (0x15B), Ultimate's TARGET_AIR / TARGET_HI_DAMAGE into VAR_12 / VAR_13; none outside those frames or far away;
 4. 0x15B pulls him to it, then the overtake sends the thrown link event (0xB, ThrownF 0x7C) and the throw work int
    0x11000005, once; its end lets go of a fighter it still holds only when it wasn't thrown.
v9 (README "Status: v9"):
 5. the catch adds Ultimate's catching hit's 3 % to the caught fighter; 0x15B holds hit_stop_frame_fighter (19) before
    the rewind;
 6. the stage line test (LINE_* variables, tools/line_test_cave.py; the model answers it with one wall / ceiling): the
    tip meeting a wall during 17 - 26 -> 0x15B latched (VAR_15 1): 12 frames' stop, the rewind to the point (his hand
    there), then the wall jump 0x15C; a ceiling or no wall jumps left -> stopped (VAR_15 0), no pull, Fall at the end;
    nothing met -> no change; the test asked with Ultimate's points (from the hand to the next frame's tip);
 7. the turn rules: TURN_CHECK at 8 turns him once with the stick back (no momentum flip); the B-reverse in the first
    frames turns him and flips his air momentum; nothing with the stick forward;
 8. Aymr's critical: the move's first hit in a 1-on-1 with a KO-strength hitstun slows the game (SlowModule 4, 40)
    and zooms (ITEM 8, then 9 after 40 frames); not with three fighters or a weak hit.
"""
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.append(HERE)
sys.path.append(os.path.join(HERE, 'mscdec'))
import rolloff_hold_test as R  # noqa: E402

PROBLEMS = []
SRC = os.path.join(ROOT, 'fighters', 'master', 'master.c')
HOLD1, HOLD2, BOWFLARE2 = 0x347004E, 0x347004F, 0x3470051
CAPTURE = 0xBD


def check(name, ok, detail=''):
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, (': ' + detail) if detail and not ok else ''))
    if not ok:
        PROBLEMS.append(name)


def f2i(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def i2f(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0]


class Game:
    def __init__(self):
        self.frame = 0.0
        self.end = False
        self.special = True
        self.shield = False
        self.motion = 0
        self.situation = 2
        self.x, self.y, self.lr = 0.0, 50.0, 1.0
        self.slots = {}            # slot: dict(x, y, status, air, damage)
        self.catching = False
        self.calls = []            # (sys, args)
        self.status = []           # status changes asked
        self.vars = {}             # float variables written
        self.stick = 0.0           # STICK_X along the facing
        self.hit_now = 0.0         # SELF_HIT_NOW
        self.wall_x = None         # v9: a wall at this world x (its normal facing him) ...
        self.ceil_y = None         # ... or a ceiling at this world y, for the line test
        self.line_asks = []        # (x0, y0, x1, y1, mode) of each line test

    def sys(self, sid, a):
        self.calls.append((sid, list(a)))
        if sid == 0x13 and a == [1]:                         # MotionModuleF(1): the frame
            return f2i(self.frame)
        if sid == 0x12 and a == [0x2712]:                    # MotionModule(0x2712): the motion's end
            return int(self.end)
        if sid == 0x12 and a == [7]:                         # MotionModule(7): the motion kind
            return self.motion
        if sid == 0xE and a == [0x2712, 1]:                  # ControlModule(0x2712, 1): special held
            return int(self.special)
        if sid == 0xE and a == [0x2712, 3]:                  # ControlModule(0x2712, 3): shield held
            return int(self.shield)
        if sid == 0x18 and a == [1]:
            return self.situation
        if sid == 0x18 and a and a[0] == 3:                  # StatusModule(3, status, ..): the change (func_79)
            self.status.append(a[1])
            return 0
        if sid == 0x15:                                      # PostureModuleF
            return f2i({0: self.lr, 1: self.x, 2: self.y}.get(a[0], 0.0))
        if sid == 0x3B and a == [0x2712]:
            return int(self.catching)
        if sid == 0x2A and a == [1, 0]:                      # LinkModule(1, 0): the linked object
            return 0x1234
        if sid == 0x17 and len(a) == 2 and a[0] == 0:        # WorkModuleF(0, var)
            return f2i(self.fvar(a[1]))
        if sid == 0x16 and len(a) == 3 and a[0] == 0:        # WorkModule(0, value, var): a float set
            self.vars[a[2]] = i2f(a[1])
            if a[2] == 0x0F0003D4:
                self.line_test(i2f(a[1]))
            return 0
        if sid == 0x14 and a in ([1], [2]):                 # PostureModule(1): reverse_lr (then 2: its rotation)
            if a == [1]:
                self.lr = -self.lr
            return 0
        return 0

    def line_test(self, mode):
        """tools/line_test_cave.py's LINE_* answer (Space 0: X along his facing from his position), one wall / ceiling"""
        x0, y0, x1, y1 = (self.vars.get(0x0F0003D0 + i, 0.0) for i in range(4))
        self.line_asks.append((x0, y0, x1, y1, mode))
        wx0, wy0 = self.x + self.lr * x0, self.y + y0
        wx1, wy1 = self.x + self.lr * x1, self.y + y1
        hit = None
        if self.wall_x is not None and wx1 != wx0:
            t = (self.wall_x - wx0) / (wx1 - wx0)
            if 0 <= t <= 1:
                hit = (t, self.wall_x, wy0 + t * (wy1 - wy0), -1.0 if (wx1 - wx0) * self.lr > 0 else 1.0, 0.0, 2.0)
        if hit is None and self.ceil_y is not None and wy1 != wy0:
            t = (self.ceil_y - wy0) / (wy1 - wy0)
            if 0 <= t <= 1:
                hit = (t, wx0 + t * (wx1 - wx0), self.ceil_y, 0.0, -1.0, 3.0)
        if hit is None:
            out = [0.0, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, x1, y1, 0.0, 0.0, 0.0]
        else:
            t, hx, hy, nx, ny, kind = hit
            out = [1.0, t * ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, (hx - self.x) * self.lr, hy - self.y, kind, nx, ny]
        for i, v in enumerate(out):
            self.vars[0x0F0003D4 + i] = v

    def fvar(self, v):
        if v == 0x0F000110:
            return self.stick
        if v == 0x0F0000A1:
            return self.hit_now
        if 0x0F000020 <= v < 0x0F000040:
            s, q = divmod(v - 0x0F000020, 4)
            f = self.slots.get(s)
            return 0.0 if not f else [f['x'], f['y'], 0.0, 1.0][q]
        if 0x0F0000A0 <= v < 0x0F0000F8:
            t, q = divmod(v - 0x0F0000A0, 8)
            f = self.slots.get(t - 3)
            return float(f['status']) if f and q == 2 else 0.0
        if 0x0F000100 <= v < 0x0F000260:
            t, q = divmod(v - 0x0F000100, 0x20)
            f = self.slots.get(t - 3)
            if f and q == 0x16:
                return 2.0 if f['air'] else 0.0
            if f and q == 0x17:
                return f['damage']
            return 0.0
        return self.vars.get(v, 0.0)

    def kills(self):
        return [(a[1], a[2], a[3]) for s, a in self.calls if s == 0x1C and a and a[0] == 0x2723]


class Byleth:
    def __init__(self, path):
        self.vm = R.VM(path)
        src = open(SRC).read()
        self.names = [m.group(2) for m in re.finditer(
            r'^(int|void|float|bool)\s+(\w+)\s*\([^;\n]*\)\s*(\{.*\})?\s*(//.*)?$', src, re.M)]
        assert len(self.names) == len(self.vm.m.scripts), (len(self.names), len(self.vm.m.scripts))
        gl = [m.group(2) for m in re.finditer(r'^(int|float)\s+(\w+)\s*(=[^;]*)?;', src, re.M)]
        self.gidx = {n: i for i, n in enumerate(gl)}
        self.vm.g[11] = self.vm.func(self.names.index('func_79')).bounds[0]

    def g(self, name, value=None):
        i = self.gidx[name]
        if value is not None:
            self.vm.g[i] = value & 0xFFFFFFFF if isinstance(value, int) else f2i(value)
        return self.vm.g.get(i, 0)

    def call(self, name, *args):
        return self.vm.call(self.vm.func(self.names.index(name)), args)


def compiled():
    import master_build as M
    out = os.path.join(tempfile.mkdtemp(), 'master.mscsb')
    M.compile_msc(SRC, out)
    return out


def failnaught(path):
    for shot_at, what in ((60.0, 'the shot (special let go at 60)'), (None, 'the shield cancel')):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 0)
        b.g('global19', 0)
        gm.situation = 0
        b.call('master_n_main')
        for f in range(1, 100):
            gm.frame = float(f)
            if shot_at is not None and f == shot_at:
                gm.special = False
            if shot_at is None and f == 40:
                gm.shield = True
            b.call('master_n_loop')
            if b.g('master_phase') >= 2:
                break
        k = gm.kills()
        want = {HOLD1, HOLD2} | ({BOWFLARE2} if shot_at is None else set())
        got = {i for i, kp, im in k if kp == 1 and im == 1}
        check('Failnaught: %s kills %s with their particles' % (what, sorted(hex(x) for x in want)), want <= got,
              'kills %s' % [tuple(map(hex, x)) for x in k])
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_n_end')
    got = {i for i, kp, im in gm.kills() if kp == 1 and im == 1}
    check('Failnaught: its status end kills hold1 / hold2 / the bow glow', {HOLD1, HOLD2, BOWFLARE2} <= got)
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_fx_sweep', 0x152, 0x0)
    got = {i for i, kp, im in gm.kills()}
    check('the status sweep leaving Failnaught (0x152 -> Wait) kills its glows', {HOLD1, HOLD2, BOWFLARE2} <= got)
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_fx_sweep', 0x0, 0x152)
    got = {i for i, kp, im in gm.kills()}
    check('the sweep entering Failnaught (Wait -> 0x152) leaves the bow glow it just started', BOWFLARE2 not in got)
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_fx_sweep', 0x25, 0x26)
    check('the sweep entering the rapid jab leaves its lines (master_atk_100)', 0x3470027 not in {i for i, _a, _b in gm.kills()})
    for frame, want in ((30.0, True), (70.0, False)):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        gm.motion, gm.frame = 0x242, frame
        b.call('master_lw_end')
        check('Aymr cut short in SpecialLwHit at %g: its following rocks (master_axe_rock) %s' % (
            frame, 'killed' if want else 'left (detached at 60)'), (0x3470039 in {i for i, _a, _b in gm.kills()}) == want)


def up_special(path):
    def setup(frame, slot=None):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 2)
        b.g('global19', 2)
        b.g('master_wall_jumps', 0)
        gm.frame = frame
        if slot:
            gm.slots[1] = slot
        return b, gm
    near = dict(x=20.0, y=90.0, status=CAPTURE, air=True, damage=30.0)
    for frame, slot, want, what in (
            (22.0, near, True, 'a fighter in 0xBD at frame 22, 52 away'),
            (12.0, near, False, 'the same at frame 12 (before ENABLE_CATCH)'),
            (30.0, near, False, 'at frame 30 (after the catch)'),
            (22.0, dict(near, status=0x45), False, 'a fighter only hit (DamageAir) at 22'),
            (22.0, dict(near, x=400.0), False, 'a fighter in 0xBD 400 away')):
        b, gm = setup(frame, slot)
        b.call('master_hi_air_loop')
        check('up special: %s -> SpecialAirHiHit %s' % (what, 'yes' if want else 'no'), (0x15B in gm.status) == want,
              'statuses %s' % [hex(s) for s in gm.status])
    for air, dmg, v12, v13 in ((True, 30.0, 1.0, 0.0), (True, 80.0, 1.0, 1.0), (False, 80.0, 0.0, 1.0)):
        b, gm = setup(22.0, dict(near, air=air, damage=dmg))
        b.call('master_hi_air_loop')
        got = (gm.vars.get(0x0F00030C), gm.vars.get(0x0F00030D))
        check('up special: the caught fighter %s at %g %% -> VAR_12 / VAR_13 = %g / %g (the overtake\'s THROW / CATCH / '
              'THROW_MEWTWO)' % ('in the air' if air else 'on the ground', dmg, v12, v13), got == (v12, v13), str(got))
    # the pull and the throw
    b, gm = setup(22.0, near)
    b.call('master_hi_air_loop')
    dvar = 0x0F000100 + 0x20 * (1 + 3) + 0x17
    check('v9 the catch adds the catching hit\'s 3 %% (30 -> 33)', gm.vars.get(dvar) == 33.0, str(gm.vars.get(dvar)))
    gm.catching = True
    gm.status.clear()
    b.call('master_hi_hit_main')
    moved, n, held = [], 0, 0
    for n in range(1, 40):
        gm.frame = float(n)
        b.call('master_hi_hit_loop')
        ks = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] == 3]
        if ks:
            vx, vy = i2f(ks[-1][2]), i2f(ks[-1][3])
            gm.x += vx
            gm.y += vy
            if vx or vy:
                moved.append((round(vx, 2), round(vy, 2)))
            elif not moved:
                held = n
        gm.calls = [c for c in gm.calls if c[0] != 0x10]
        if b.g('master_phase') == 1:
            gm.frame = 1.0
            b.call('master_hi_hit_loop')            # the next frame stops him
            ks = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] == 3]
            stopped = bool(ks) and i2f(ks[-1][2]) == 0.0 and i2f(ks[-1][3]) == 0.0
            break
    links = [a for s, a in gm.calls if s == 0x2A and a and a[0] == 0x271B]
    sets = [a for s, a in gm.calls if s == 0x16 and a and a[0] == 7 and a[2] == 0x11000005]
    # (the status's first frame is the main's: its loop runs there too, so 18 loops + it)
    check('v9 SpecialAirHiHit: still for hit_stop_frame_fighter (19 frames) before the rewind', held + 1 == 19, 'held %d' % held)
    check('SpecialAirHiHit: pulled at rewind_speed 4.1 a frame to the caught fighter (his hand 8 short), then stopped',
          moved and stopped and abs((moved[0][0] ** 2 + moved[0][1] ** 2) ** 0.5 - 4.1) < 0.01 and abs(gm.x - (20.0 - 8.0)) < 0.01
          and abs(gm.y - 90.0) < 0.01, 'steps %s, at (%.2f, %.2f) after %d frames' % (moved[:3], gm.x, gm.y, n))
    check('the overtake: the thrown link event (0xB, ThrownF 0x7C, the throw work ints) once',
          len(links) == 1 and links[0][:3] == [0x271B, 0xB, 0x7C] and len(sets) == 1 and sets[0][1] == 0x1234,
          'links %s, sets %s' % (links, sets))
    gm.calls.clear()
    gm.catching = False                     # Throw_Applier (its game script, frame 11) ended the hold
    b.g('global6', 0xE)
    b.call('master_hi_hit_end')
    check('0x15B\'s end after the throw: no extra let go', not [a for s, a in gm.calls if s == 0x3B and a == [0x2711]])
    b, gm = setup(22.0, near)
    b.call('master_hi_air_loop')
    gm.catching = True
    b.call('master_hi_hit_main')
    b.g('global6', 0x45)
    b.call('master_hi_hit_end')
    check('0x15B cut short (a hit) while holding: let go (CatchModule 0x2711)',
          [a for s, a in gm.calls if s == 0x3B and a == [0x2711]] != [])


def v9(path):
    def setup(frame, x=0.0, lr=1.0):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 2)
        b.g('global19', 2)
        b.g('master_wall_jumps', 0)
        b.g('master_hi_turned', 1)
        b.g('master_hi_brev', 1)
        b.g('master_hi_wall', 0)
        gm.frame, gm.x, gm.lr = frame, x, lr
        return b, gm
    # 6. the line test
    b, gm = setup(19.0)
    gm.wall_x = 14.0
    b.call('master_hi_air_loop')
    ask = gm.line_asks[-1] if gm.line_asks else None
    check('v9 line test asked from his hand (5.5, 20.5) to the next frame\'s tip (frame 20: 15.3, 45.3), mode 2',
          ask is not None and all(abs(p - q) < 1e-4 for p, q in zip(ask, (5.5, 20.5, 15.3, 45.3, 2.0))), str(ask))
    check('v9 the tip meets a wall at frame 19 -> SpecialAirHiHit, latched', 0x15B in gm.status and b.g('master_hi_wall') == 1,
          'statuses %s, wall %d' % ([hex(x) for x in gm.status], b.g('master_hi_wall')))
    tx, ty = i2f(b.g('master_tx')), i2f(b.g('master_ty'))
    gm.status.clear()
    b.call('master_hi_hit_main')
    check('v9 latched: VAR_15 = 1 (the sword stays 12 frames)', gm.vars.get(0x0F00030F) == 1.0)
    held, moved, n = 0, 0, 0
    for n in range(1, 60):
        gm.calls.clear()
        b.call('master_hi_hit_loop')
        ks = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] == 3]
        if ks:
            vx, vy = i2f(ks[-1][2]), i2f(ks[-1][3])
            if vx or vy:
                moved += 1
                gm.x += vx * gm.lr
                gm.y += vy
            elif not moved:
                held = n
        if 0x15C in gm.status:
            break
    check('v9 latched: still 12 frames (hit_stop_frame_wall), pulled until his hand is at the point, then the wall jump',
          held + 1 == 12 and 0x15C in gm.status and abs(gm.x + 8.0 - tx) < 0.01 and abs(gm.y + 20.5 - ty) < 0.01,
          'held %d, moved %d, at (%.2f, %.2f), point (%.2f, %.2f), statuses %s' % (held, moved, gm.x, gm.y, tx, ty,
                                                                                  [hex(x) for x in gm.status]))
    b, gm = setup(22.0, lr=-1.0)
    gm.wall_x = -15.0
    b.call('master_hi_air_loop')
    check('v9 facing left: the wall 15 to his left met', 0x15B in gm.status and b.g('master_hi_wall') == 1)
    b, gm = setup(23.0)
    gm.ceil_y = 50.0 + 40.0
    b.call('master_hi_air_loop')
    check('v9 a ceiling 40 above at frame 23 -> SpecialAirHiHit, stopped (no latch)',
          0x15B in gm.status and b.g('master_hi_wall') == 2)
    gm.status.clear()
    b.call('master_hi_hit_main')
    gm.end = True
    b.call('master_hi_hit_loop')
    check('v9 stopped: VAR_15 0 (the sword back at once), Fall at the motion\'s end, no overtake',
          gm.vars.get(0x0F00030F) == 0.0 and gm.status == [0xE], str([hex(x) for x in gm.status]))
    b, gm = setup(19.0)
    gm.wall_x = 14.0
    b.g('master_wall_jumps', 3)
    b.call('master_hi_air_loop')
    check('v9 no wall hits left (wall_hit_max 3): stopped, not latched', b.g('master_hi_wall') == 2)
    b, gm = setup(19.0)
    gm.wall_x = 400.0
    b.call('master_hi_air_loop')
    check('v9 nothing met -> no change', 0x15B not in gm.status and b.g('master_hi_wall') == 0)
    b, gm = setup(14.0)
    gm.wall_x = 14.0
    b.call('master_hi_air_loop')
    check('v9 no test before 17 (the sword out)', not gm.line_asks)
    b, gm = setup(19.0)
    b.g('global18', 0)
    gm.wall_x = 14.0
    b.call('master_hi_loop')
    check('v9 the ground up special latches too', 0x15B in gm.status and b.g('master_hi_wall') == 1)
    # 7. the turn rules
    for f, stick, want, what in ((8.0, -0.5, -1.0, 'TURN_CHECK (frame 8), stick back'),
                                 (8.0, 0.5, 1.0, 'TURN_CHECK, stick forward'),
                                 (8.0, -0.2, 1.0, 'TURN_CHECK, stick back under 0.3')):
        b, gm = setup(f)
        b.g('master_hi_turned', 0)
        gm.stick = stick
        b.call('master_hi_air_loop')
        flips = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] in (2, 3)]
        check('v9 %s -> facing %g, momentum kept' % (what, want), gm.lr == want and not flips, 'lr %g' % gm.lr)
    b, gm = setup(9.0)
    b.g('master_hi_turned', 0)
    gm.stick = -0.5
    b.call('master_hi_air_loop')
    gm.lr = -gm.lr if False else gm.lr
    b.call('master_hi_air_loop')
    check('v9 TURN_CHECK once (two loops with the stick back: one turn)', gm.lr == -1.0)
    b, gm = setup(1.0)
    b.g('master_hi_brev', 0)
    gm.stick = -0.6
    b.call('master_hi_air_loop')
    flips = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] in (2, 3)]
    check('v9 B-reverse at frame 1 in the air: turned, energies 2 / 3 x flipped', gm.lr == -1.0 and len(flips) == 2,
          'lr %g, flips %d' % (gm.lr, len(flips)))
    b, gm = setup(5.0)
    b.g('master_hi_brev', 0)
    gm.stick = -0.6
    b.call('master_hi_air_loop')
    check('v9 no B-reverse after its window (frame 5)', gm.lr == 1.0)
    # 8. Aymr's critical
    for slots, hitstun, want, what in ((2, 60.0, True, 'a 1-on-1, hitstun 60'), (3, 60.0, False, 'three fighters'),
                                       (2, 30.0, False, 'a weak hit (hitstun 30)')):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global4', 0x155)
        for k in range(slots):
            gm.slots[k] = dict(x=0.0, y=0.0, status=0, air=False, damage=0.0)
        gm.vars[0x0F0002C9] = hitstun
        gm.hit_now = 1.0
        b.call('master_lw_crit')
        slow = [a for s, a in gm.calls if s == 0x49]
        cam = gm.vars.get(0x0F000099)
        ok = (slow == [[0, 4, 40]] and cam == 8.0) if want else (not slow and cam is None)
        if want:
            gm.hit_now = 0.0
            for _ in range(40):
                b.call('master_lw_crit')
            ok = ok and gm.vars.get(0x0F000099) == 9.0 and len([a for s, a in gm.calls if s == 0x49]) == 1
        check('v9 Aymr\'s critical: %s -> %s' % (what, 'slowed and zoomed, back after 40' if want else 'nothing'), ok,
              'slow %s, cam %s' % (slow, gm.vars.get(0x0F000099)))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else compiled()
    failnaught(path)
    up_special(path)
    v9(path)
    print('\n%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
