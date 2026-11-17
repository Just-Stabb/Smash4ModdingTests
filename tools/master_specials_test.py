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
v10 (README "Status: v10"):
 9. the wall latch keeps the sword (no func_127 into 0x15B), holds the fall (gravity 0, energy 1 suspended), reels
    his hand (5.5 / 20.5) to the point; the wall jump turns away, clings 13 frames, then 2.6 / 0.9 on gravity / air
    control with the fall back;
10. the catch without a capture: the tip on a fighter's body two frames running in 20 - 26 (not intangible, not far)
    -> 0x15B with VAR_11 (the overtake's hitbox), its 3 %, a hitstop each frame; reeled in, held to the throw's frame;
11. the ledge box per frame (12 - 14 the normal one, 15 - 16 the tether box);
12. Aymr's landings by frame (INHERIT_1, Landing2 before the hop, the air motion from the hop to the hit's end,
    INHERIT_2, Landing1) and the hop at 53.
v11: the reel moves him by the self-move position variables (0x0F000004 / 5), energy 3 kept 0; the wall jump's jump
     from 0x15C's main entered again; the catch without a capture leaves its 3 % to SpecialAirHiHit's hit.
v12: the reel ends with the target's throw point 7.8 ahead / 14.2 above him (not under a grounded target's feet), the
     overtake puts him on that point (its waist read, else feet + 10) through 11; the catch's effects at the target and
     the wall latch's at the point met (MSC, not FOOT_EFFECT), the cling's at 6; point-blank catches (the blade) and the
     tip pull of a fighter overlapping him.
v13: 0x15B holds every energy and puts him by position: exactly still through the stop's motion frames, then one
     straight path of equal steps (<= 4.1) to the reel's end; master_wire_wind2 stopped at the reel, killed on a cut-short
     exit and by the sweep.
v16: Aymr's turn: the model (update_rot_y_lr, PostureModule(2)) turns as SpecialLw resumes after the turn motion
     (its script's Reverse_Direction flips the facing only), at the frame it left, ground and air; not without a turn.
v17: the reel at master_build's MASTER_HI_REWIND (5.0) a frame and the pull motions at the same rate (master_whip.REWIND);
     SpecialAirHiHit's script removes the tether's whip at 0 and makes a fresh one with the hit motion at 1 (never the
     tether's whip moved into an anchored motion); the base's whip out of the side taunt / Win1 (and only there);
     the rapid jab's holding hits at HOLD_ANGLE (ultimate_acmd.hold_angle), nothing else; the jab chain's
     fighter_param values from Ultimate's (ultimate_stats: 86 presses 5, 81 / 82 28, 262 1).
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
import master_build as _MB  # noqa: E402
REWIND = float(_MB.CONSTS['MASTER_HI_REWIND'].rstrip('f'))    # v17: 5.0 (Ultimate's rewind_speed 4.1)
SRC = os.path.join(ROOT, 'fighters', 'master', 'master.c')
HOLD1, HOLD2, BOWFLARE2 = 0x347004E, 0x347004F, 0x3470051
CAPTURE = 0xBD


# v18: vl group 7 (x, y, w, h along his facing from his position, world units): 0 the normal ledge box (Ultimate's
# cliff_hang_data[0]: ultimate_vl_shapes.ledge_box), 2 the tether box (cliff_hang_data[3], master's AIR_LASSO), 3 the
# ZSS's (kept), 4 the box his air up special starts with (cliff_hang_data[1], the common AIR_LASSO):
# ultimate_vl_shapes.tether_box
BOXES = {0: (0.0, 7.5, 16.0, 18.5), 2: (-44.0, 20.0, 88.0, 65.0), 3: (-15.0, 10.0, 65.0, 80.0), 4: (-5.0, -35.0, 80.0, 120.0)}


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
        self.lasso = False         # v10: flag 0x2100000D on
        self.step = [0.0, 0.0]     # v11: self moves (forward, up) since the last take()
        self.placed = []           # v12: (x, y) before each write of his X / Y (0x0F000000 / 1), and after
        self.fx = []               # v12: EffectModule(0x2710, id, bone, x, y, ...) requests: (id, world x, world y)
        self.rot = 1.0             # v16: the model's facing (PostureModule +0x64 / 90: update_rot_y_lr sets it to lr)
        self.stick_x = 0.0         # v16: ControlModuleF(0), the stick's X on screen
        self.ledge = None          # v18: a ledge (world x, y, its hang direction: GroundModuleF(7))
        self.box = None            # v18: the vl group 7 entry GroundModule(0x2712, n) chose last

    def take(self):
        """the self moves since the last call (applied as they were written): (forward, up)"""
        f, u = self.step
        self.step = [0.0, 0.0]
        return f, u

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
        if sid == 0x16 and a == [0x2712, 0x2100000D]:           # v10: AIR_LASSO_FLAG_CHECK (the aircatch script's)
            return int(self.lasso)
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
            if a[2] in (0x0F000004, 0x0F000005):         # v11: the self moves (forward / up), position_vars_cave
                self.step[a[2] - 0x0F000004] += i2f(a[1])
                if a[2] == 0x0F000004:
                    self.x += i2f(a[1]) * self.lr
                else:
                    self.y += i2f(a[1])
            if a[2] in (0x0F000000, 0x0F000001):         # v12: set his X / Y
                before = (self.x, self.y)
                if a[2] == 0x0F000000:
                    self.x = i2f(a[1])
                else:
                    self.y = i2f(a[1])
                self.placed.append((before, (self.x, self.y)))
            if 0x0F000020 <= a[2] < 0x0F000040 and (a[2] - 0x0F000020) % 4 < 2:    # v12: a slot's X / Y set
                sl, q = divmod(a[2] - 0x0F000020, 4)
                if sl in self.slots:
                    self.slots[sl]['xy'[q]] = i2f(a[1])
            if a[2] == 0x0F0003D4:
                self.line_test(i2f(a[1]))
            return 0
        if sid == 0x1C and a and a[0] == 0x2710:             # v12: EffectModule(0x2710, id, bone 0, x (fwd), y, ...)
            self.fx.append((a[1], self.x + i2f(a[3]) * self.lr, self.y + i2f(a[4])))
            return 0
        if sid == 0x14 and a in ([1], [2]):                 # PostureModule(1): reverse_lr (then 2: its rotation)
            if a == [1]:
                self.lr = -self.lr
            else:
                self.rot = self.lr                       # v16: update_rot_y_lr (vt+0xC4): the model turns
            return 0
        if sid == 0xF and a == [0]:                          # v16: ControlModuleF(0): the stick's X
            return f2i(self.stick_x)
        if sid == 0x1A and a and a[0] == 0x2712:             # v18: GroundModule(0x2712, n): the ledge box used
            self.box = a[1]
            return 0
        if sid == 0x1A and a in ([0x2724], [0x2725]):        # v18: is_status_cliff / can_entry_cliff (func_99)
            return int(self.ledge_in_box())
        if sid == 0x1B and a == [7]:                         # v18: GroundModuleF(7): the ledge's hang direction
            return f2i(self.ledge[2] if self.ledge else 0.0)
        if sid == 0x1B and a == [1]:                         # v18: GroundModuleF(1): the ledge's x
            return f2i(self.ledge[0] if self.ledge else 0.0)
        if sid == 0x1B and a == [2]:                         # v19: GroundModuleF(2): the ledge's y (master_hi_reach)
            return f2i(self.ledge[1] if self.ledge else 0.0)
        return 0

    def ledge_in_box(self):
        """v18: a ledge (x, y, hang dir) inside vl group 7's entry self.box (x, y, w, h along the facing, from his
        position: ultimate_vl_shapes.tether_box), the boxes as BOXES holds them"""
        if not self.ledge or self.box not in BOXES:
            return False
        bx, by, bw, bh = BOXES[self.box]
        fx = (self.ledge[0] - self.x) * self.lr
        fy = self.ledge[1] - self.y
        return bx <= fx <= bx + bw and by <= fy <= by + bh

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
        if 0x0F000290 <= v < 0x0F0002BC and (v - 0x0F000290) % 4 == 2:   # v12: a joint's Y (the slot's 'waist')
            f = self.slots.get((v - 0x0F000290) // 4 - 3)
            return f['y'] + f['waist'] if f and 'waist' in f else 0.0
        if 0x0F000100 <= v < 0x0F000260:
            t, q = divmod(v - 0x0F000100, 0x20)
            f = self.slots.get(t - 3)
            if f and q == 0x16:
                return 2.0 if f['air'] else 0.0
            if f and q == 0x17:
                return f['damage']
            if f and q == 0x1B:
                return f.get('intangible', 0.0)
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


def run_hit(b, gm, stop_at=None, n=60, clock=None):
    """v13: 0x15B from its main (motion frame 0), its loop on frames 1, 2, ...: [(frame, phase, x, y)] after each, until
    phase 1 (the overtake) or a status change (stop_at). v14 clock(f) -> (motion frame, in hitstop) for loop f (a frozen
    motion, a hitlag)"""
    gm.frame = 0.0
    if clock:
        gm.frame, hs = clock(0)
        gm.vars[0x0F000043] = 1.0 if hs else 0.0
    b.call('master_hi_hit_main')
    out = [(0, 0, gm.x, gm.y)]
    for f in range(1, n):
        gm.frame = float(f)
        if clock:
            gm.frame, hs = clock(f)
            gm.vars[0x0F000043] = 1.0 if hs else 0.0
        b.call('master_hi_hit_loop')
        out.append((f, b.g('master_phase'), gm.x, gm.y))
        if b.g('master_phase') == 1 or (stop_at is not None and stop_at in gm.status):
            break
    return out


def reel_ok(path, start, end, stop):
    """held exactly at start through the stop's frames, then steady REWIND steps on the line to end (the last shorter)"""
    held = [p for p in path if p[0] < stop]
    moving = [p for p in path if p[0] >= stop]
    if any(abs(p[2] - start[0]) > 1e-3 or abs(p[3] - start[1]) > 1e-3 for p in held) or not moving:
        return False, 'held %s' % held[:3]
    pts = [start] + [(p[2], p[3]) for p in moving]
    steps = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:])]
    d = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    n = max(1, -(-d // REWIND))
    ok = len(steps) >= 1 and all(abs(x - d / n) < 0.01 for x in steps) and d / n <= REWIND + 1e-4
    return ok, 'steps %s, d %.2f' % ([round(x, 2) for x in steps], d)


def sword_len_check(what, gm, start, held, mode):
    """v15: VAR_16 = 10 x mode + v, v the PULL_LENGTHS entry nearest his hand's (Ultimate's hit pose: 6.2 / 18.5 from
    his root, held at start) distance to what the tip holds"""
    import master_whip as MW
    hand = (start[0] + 6.2 * gm.lr, start[1] + 18.5)
    d = ((held[0] - hand[0]) ** 2 + (held[1] - hand[1]) ** 2) ** 0.5
    v = min(range(len(MW.PULL_LENGTHS)), key=lambda k: (abs(MW.PULL_LENGTHS[k] - d), k))
    got = gm.vars.get(0x0F000310)
    check('v15 %s: VAR_16 = %d (10 x VAR_15 %d + the blade %g nearest the distance %.1f from his hand)'
          % (what, 10 * mode + v, mode, MW.PULL_LENGTHS[v], d), got == float(10 * mode + v), str(got))


def script_run(script, vars_):
    """[(frame, command name, params)] a flat ACMD script with Float_Var_Compare / True blocks executes (== / != / >=)"""
    import operator
    ops = {0: operator.eq, 1: operator.ne, 2: operator.le, 3: operator.ge, 4: operator.lt, 5: operator.gt}
    out, frame, i, skip_to = [], 0.0, 0, None
    words = [1 + len(c.params) for c in script]
    while i < len(script):
        c = script[i]
        if c.name == 'FRAME':
            frame = float(c.params[0])
        elif c.name == 'Float_Var_Compare':
            ok = ops[int(c.params[1])](vars_.get(c.params[0], 0.0), float(c.params[2]))
            t = script[i + 1]
            assert t.name == 'True'
            if not ok:
                n, j = int(t.params[0]) - words[i + 1], i + 2      # the block's words after the True
                while n > 0:
                    n -= words[j]
                    j += 1
                i = j
                continue
            i += 2
            continue
        elif c.name not in ('True', 'END'):
            out.append((frame, c.name, list(c.params)))
        i += 1
    return out


def v15_scripts():
    """v15: SpecialAirHiHit's game script by VAR_15 / VAR_16; the overtake's; the slots the executable must have"""
    import master_build as M
    import master_whip as MW
    sc = M.hi_hit_script()
    arts = lambda r: [(f, n, p) for f, n, p in r if 'Article' in n or n == 'GENERATE_ARTICLE']   # noqa: E731
    for mode, stop in sorted(M.HI_STOP.items()):
        for v in range(len(MW.PULL_LENGTHS)):
            r = arts(script_run(sc, {0x0F00030F: float(mode), 0x0F000310: float(10 * mode + v)}))
            # v17: the tether's whip removed at 0, a fresh one made at 1 with the hit motion (v15 / v16: status 0)
            want = [(0.0, 'Remove_Article', [2]), (1.0, 'GENERATE_ARTICLE', [2]),
                    (1.0, 'Set_Anchored_Article_Action', [2, MW.HIT_SLOT(v)]),
                    (float(stop), 'Set_Anchored_Article_Action', [2, MW.PULL_SLOT(v)])]
            check('v17 SpecialAirHiHit\'s script, VAR_15 %d, blade %g: the tether\'s whip removed at 0, a new one with '
                  'the hit motion at 1, its pull at %d' % (mode, MW.PULL_LENGTHS[v], stop), r == want, str(r))
            check('v17 SpecialAirHiHit\'s script, VAR_15 %d, blade %g: no status change of the whip (port_check S29)' %
                  (mode, MW.PULL_LENGTHS[v]), not [x for x in r if x[1].startswith('Set_Remote')], str(r))
    r = arts(script_run(sc, {0x0F00030F: 0.0, 0x0F000310: -1.0}))
    check('v15 SpecialAirHiHit\'s script, the floor / ceiling stop: her reverse at once, nothing else', r ==
          [(0.0, 'Set_Remote_Article_Action2', [2, 3])], str(r))
    import ultimate_acmd as U
    ovt = [U.cmd('FRAME', 12.0), U.cmd('Remove_Article', 2)]
    M.overtake_sword(U, ovt)
    M.overtake_sword(U, ovt)
    r = arts(script_run(ovt, {}))
    check('v15 the overtake plays the sword\'s overtake motion at 0 (once), removed at 12',
          r == [(0.0, 'Set_Anchored_Article_Action', [2, MW.OVT_SLOT]), (12.0, 'Remove_Article', [2])], str(r))
    used = sorted({MW.OVT_SLOT} | {MW.HIT_SLOT(v) for v in range(6)} | {MW.PULL_SLOT(v) for v in range(6)})
    check('v15 the new slots: past her 60, multiples of 4, within the grown motion info (%d), one name each' %
          MW.MOTION_COUNT, used[0] == 60 and all(x % 4 == 0 and x + 3 < MW.MOTION_COUNT for x in used)
          and sorted(MW.NEW_NAMES) == used and len(set(MW.ALL_NAMES.values())) == len(MW.ALL_NAMES), str(used))


def v17_static():
    """v17: the reel's rate in the MSC and the pull motions; the hit slots' start; the base's whip stripped; the rapid
    jab's holding angle; the jab chain's stats"""
    import master_build as M
    import master_whip as MW
    import ultimate_acmd as U
    import acmd
    check('v17 the reel: MASTER_HI_REWIND %g = master_whip.REWIND %g (the pull motions shrink the blade as fast)' %
          (REWIND, MW.REWIND), REWIND == MW.REWIND == 5.0)
    check('v17 the hit slots start on the body\'s frame %d (the fresh whip\'s frame), the pulls on its pose frame' %
          MW.HIT_GEN, all(MW.SLOTS[MW.HIT_SLOT(v)]['start'] == MW.HIT_GEN == 1 and
                          MW.SLOTS[MW.PULL_SLOT(v)]['start'] == MW.HIT_POSE_FRAME for v in range(len(MW.PULL_LENGTHS))))
    for v, l0 in enumerate(MW.PULL_LENGTHS):
        n = next(t for t in range(100) if l0 - MW.REWIND * t <= MW.PULL_MIN)
        check('v17 pull from %g: the blade reaches the overtake\'s %g in %d frames at %g (within PULL_FRAMES %d)' %
              (l0, MW.PULL_MIN, n, MW.REWIND, MW.PULL_FRAMES), n <= MW.PULL_FRAMES)
    check('v17 the up smash slot 4 starts where its body script plays it (FRAME 8)',
          MW.SLOTS[4]['start'] == 8 and MW.SLOTS[4]['tl'][0][:3] == (8, 'c04attackhi4', 8))

    class G:
        scripts = {}
    G.scripts = {acmd.crc('appealsr'): [U.cmd('GENERATE_ARTICLE', 2), U.cmd('Set_Anchored_Article_Action', 2, 40),
                                        U.cmd('FRAME', 81.0), U.cmd('Remove_Article', 2), acmd.Command(acmd.END)],
                 acmd.crc('win1'): [U.cmd('GENERATE_ARTICLE', 2), U.cmd('Set_Anchored_Article_Action', 2, 48),
                                    acmd.Command(acmd.END)],
                 acmd.crc('attackhi4'): [U.cmd('GENERATE_ARTICLE', 2), U.cmd('Set_Anchored_Article_Action', 2, 20),
                                         acmd.Command(acmd.END)],
                 acmd.crc('specialn'): [U.cmd('GENERATE_ARTICLE', 0), acmd.Command(acmd.END)]}
    left = MW.strip_base_whip(G, {'attackhi4', 'aircatch'})
    check('v17 the base\'s whip stripped from the side taunt and Win1 only (not a planned move, not another article)',
          left == ['appealsr', 'win1'] and len(G.scripts[acmd.crc('attackhi4')]) == 3
          and len(G.scripts[acmd.crc('specialn')]) == 2
          and [c.name for c in G.scripts[acmd.crc('appealsr')]] == ['FRAME', 'Script_End'], str(left))
    cases = [((361, 10, 0, 12, 'ATTACK_SETOFF_KIND_OFF', 0.4), U.HOLD_ANGLE),
             ((361, 10, 0, 10, 'ATTACK_SETOFF_KIND_OFF', 0.4), U.HOLD_ANGLE),
             ((361, 10, 0, 12, 'ATTACK_SETOFF_KIND_ON', 0.4), 361), ((361, 162, 0, 60, 'ATTACK_SETOFF_KIND_OFF', 3.5), 361),
             ((361, 20, 0, 0, 'ATTACK_SETOFF_KIND_OFF', 0.0), 361), ((54, 10, 0, 12, 'ATTACK_SETOFF_KIND_OFF', 0.4), 54),
             ((368, 10, 0, 12, 'ATTACK_SETOFF_KIND_OFF', 0.4), 366)]
    mode = U.HOLD_MODE
    U.HOLD_MODE = 'angle'
    got = [U.hold_angle(*a) for a, _w in cases]
    U.HOLD_MODE = mode
    check('v17 the holding angle (--hold-angle): the rapid jab\'s 361 / setoff off / small knockback -> %d; not with '
          'setoff on, a big knockback, no damage, another angle; 368 -> 366 as before' % U.HOLD_ANGLE,
          got == [w for _a, w in cases], str(got))
    # rapid_setoff v1 (the default): Ultimate's angle kept, Hitbox_Hold(ID, 1) after the holding hit, none after others
    got = [U.hold_angle(*a) for a, _w in cases]
    held = [U.holding(*a) for a, _w in cases]
    check('rapid_setoff v1: the default keeps Ultimate\'s angle (361; 368 -> 366) and marks only the holding hits',
          (U.HOLD_MODE, got, held) == ('hold', [361, 361, 361, 361, 361, 54, 366], [True, True] + [False] * 5),
          str((U.HOLD_MODE, got, held)))
    try:                                # the translation of Ultimate's Attack100 itself (the port's dump)
        import port_sources
        d = port_sources.load().dump('master')
        body = U.functions(open(os.path.join(d, 'master', 'Attack100.txt')).read())['game_attack100']
    except Exception:                   # noqa: BLE001
        body = None
    if body is not None:
        cmds = U.Translator({}).script(body)
        hits = [(c.params[0], c.params[4]) for c in cmds if c.name.endswith('Special_Hitbox')]
        after = [cmds[i + 1].name == 'Hitbox_Hold' and cmds[i + 1].params == [c.params[0], 1]
                 for i, c in enumerate(cmds) if c.name.endswith('Special_Hitbox')]
        check('rapid_setoff v1: Attack100 translated: its 12 loop hits (6 x IDs 0 / 1) at 361, each followed by '
              'Hitbox_Hold(ID, 1)', (len(hits), set(a for _i, a in hits), all(after)) == (12, {361}, True),
              str((hits, after)))
    try:
        import port_sources
        import ultimate_stats as US
        src = port_sources.load()
        e = US.entry(src.find('ult_common', 'param/fighter_param.prc'), src.get('labels'), 'master')
        v = US.values(e)
        got = {k: v[k][0] for k in (81, 82, 86, 262, 263, 264)}
        check('v17 the jab chain from Ultimate\'s: 86 presses 5 (attack_100_enable_cnt 4 + 1), 81 / 82 28, 262 1 (hit), '
              '263 3, 264 1', got == {81: 28.0, 82: 28.0, 86: 5, 262: 1, 263: 3, 264: 1}, str(got))
    except Exception as ex:                         # no Ultimate files on this machine
        print('  (v17 stats not checked: %s)' % ex)


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
    start = (gm.x, gm.y)
    hp = run_hit(b, gm)
    sword_len_check('a fighter (its throw point (20, 100))', gm, start, (20.0, 100.0), 2)
    reel_end = gm.placed[-2][0]                     # where the reel's last step put him (the overtake then moves him)
    gm.frame = 1.0
    b.call('master_hi_hit_loop')                    # the overtake's next frame: still on the throw point
    stopped = (gm.x, gm.y) == (hp[-1][2], hp[-1][3])
    links = [a for s, a in gm.calls if s == 0x2A and a and a[0] == 0x271B]
    sets = [a for s, a in gm.calls if s == 0x16 and a and a[0] == 7 and a[2] == 0x11000005]
    ok, why = reel_ok(hp[:-1] + [(hp[-1][0], 0, reel_end[0], reel_end[1])], start, (20.0 - 7.8, 100.0 - 14.2), 19)
    check('v13 SpecialAirHiHit: held exactly still for hit_stop_frame_fighter (motion frames 0 - 18), then reeled along '
          'one straight path at a steady speed (<= REWIND) until the caught fighter\'s throw point (its feet + '
          '10: no waist read) is 7.8 ahead / 14.2 above him (Ultimate\'s hit pose -> overtake), then put on that point '
          '(v12: the overtake, his root on its throw joint) and kept there', ok and stopped and reel_end
          and abs(reel_end[0] - (20.0 - 7.8)) < 0.01 and abs(reel_end[1] - (100.0 - 14.2)) < 0.01
          and abs(gm.x - 20.0) < 0.01 and abs(gm.y - 100.0) < 0.01,
          '%s, reel end %s, at (%.2f, %.2f)' % (why, reel_end, gm.x, gm.y))
    susp = sorted({a[1] for s, a in gm.calls if s == 0x10 and len(a) == 2 and a[0] == 0x2717})
    # v14: the stop can't freeze: a motion that stands at 14 (v13's 15-frame motion), a hitlag at the start
    for what, clock, want in (
            ('the motion standing at 14 (v13 in game: frozen for good)', lambda f: (float(min(f, 14)), False), 19),
            ('6 frames of his own hitstop first (the motion at 0.04 a frame)',
             lambda f: ((0.04 * f, True) if f < 6 else (f - 6 + 0.24, False)), 25)):
        b2, g2 = setup(22.0, near)
        b2.call('master_hi_air_loop')
        g2.catching = True
        hp2 = run_hit(b2, g2, clock=clock)
        first = next((p[0] for p in hp2 if (p[2], p[3]) != (hp2[0][2], hp2[0][3])), None)
        check('v14 the stop, %s: ends, the reel starts on loop %s (want %d) and reaches the overtake' % (what, first, want),
              first == want and b2.g('master_phase') == 1, str(hp2[-3:]))
    check('v13 SpecialAirHiHit holds every energy (0x2717 on 0 - 3): only his written position moves him',
          susp == [0, 1, 2, 3], str(susp))
    wind_off = [a for s, a in gm.calls if s == 0x1C and a and a[0] == 0x2723 and a[1] == 0x3470073]
    check('v13 master_wire_wind2 (endless) stopped once as the reel starts (EffectModule 0x2723, 0, 0: its particles '
          'fade)', wind_off == [[0x2723, 0x3470073, 0, 0]], str(wind_off))
    cat = [(hex(i), round(x, 1), round(y, 1)) for i, x, y in gm.fx]
    check('v12 the catch\'s effects (master_wire_catch 0x347006E, master_wire_wind2 0x3470073) at the caught fighter\'s '
          'throw point (20, 100), from MSC (not the effect script\'s ground-only FOOT_EFFECT)',
          cat[:2] == [('0x347006e', 20.0, 100.0), ('0x3470073', 20.0, 100.0)], str(cat))
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
    check('v13 0x15B cut short: master_wire_wind2 killed with its particles, the energies resumed (0x2718 on 0 - 3)',
          [0x2723, 0x3470073, 1, 1] in [a for s, a in gm.calls if s == 0x1C]
          and sorted({a[1] for s, a in gm.calls if s == 0x10 and len(a) == 2 and a[0] == 0x2718}) == [0, 1, 2, 3])
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_fx_sweep', 0x15B, 0x45)
    check('v13 the status sweep leaving 0x15B kills master_wire_wind2', [0x2723, 0x3470073, 1, 1] in
          [a for s, a in gm.calls if s == 0x1C])


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
    start = (gm.x, gm.y)
    hp = run_hit(b, gm, stop_at=0x15C)
    check('v9 latched: VAR_15 = 1 (the sword stays 12 frames)', gm.vars.get(0x0F00030F) == 1.0)
    sword_len_check('a wall (the point met)', gm, start, (tx, ty), 1)
    ok, why = reel_ok(hp, start, (tx - 5.5, ty - 20.5), 12)
    check('v9 latched: still 12 frames (hit_stop_frame_wall; v13 held exactly, on the motion\'s frame), reeled on one '
          'path until his hand (v10: the line test\'s start, 5.5 ahead) is at the point, then the wall jump',
          ok and 0x15C in gm.status and abs(gm.x + 5.5 - tx) < 0.01 and abs(gm.y + 20.5 - ty) < 0.01,
          '%s, at (%.2f, %.2f), point (%.2f, %.2f), statuses %s' % (why, gm.x, gm.y, tx, ty, [hex(x) for x in gm.status]))
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
    gm.frame = 0.0
    b.call('master_hi_hit_main')
    gm.frame = 14.0                                 # v14: its own end (Ultimate's last frame; the motion is 60 now)
    b.call('master_hi_hit_loop')
    check('v15 stopped: VAR_16 -1 (no hit / pull motion: her reverse at once)', gm.vars.get(0x0F000310) == -1.0,
          str(gm.vars.get(0x0F000310)))
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


def kin(gm, op, energy):
    return [a for s, a in gm.calls if s == 0x10 and a and a[0] == op and len(a) > 1 and a[1] == energy]


def v10(path):
    """v10 (README "Status: v10")"""
    def setup(frame, lr=1.0):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 2)
        b.g('global19', 2)
        b.g('master_wall_jumps', 0)
        gm.frame, gm.lr = frame, lr
        return b, gm
    # 1. the wall latch: the sword kept, no fall, the wall jump turns away, clings 13 frames, then jumps
    b, gm = setup(19.0)
    gm.wall_x = 14.0
    b.call('master_hi_air_loop')
    b.g('global6', 0x15B)
    b.call('master_hi_air_end')
    check('v10 the latch (0xF1 -> 0x15B) keeps the sword: no func_127 (its ArticleModule 0x2712 remove)',
          not [a for s, a in gm.calls if s == 0x20 and a and a[0] == 0x2712])
    b.g('global6', 0x0)
    gm.calls.clear()
    b.call('master_hi_air_end')
    check('v10 leaving 0xF1 for anything else still removes it', bool([a for s, a in gm.calls if s == 0x20 and a and a[0] == 0x2712]))
    gm.calls.clear()
    gm.status.clear()
    gm.fx.clear()
    b.call('master_hi_hit_main')
    latch = (b.g('master_tx'), b.g('master_ty'))
    check('v12 the latch: the sword\'s hit effects (master_wire_catch, master_wire_wind2) on the point the tip met',
          [(i, round(x, 2), round(y, 2)) for i, x, y in gm.fx] == [(0x347006E, round(i2f(latch[0]), 2), round(i2f(latch[1]), 2)),
                                                                 (0x3470073, round(i2f(latch[0]), 2), round(i2f(latch[1]), 2))],
          str(gm.fx))
    check('v10 SpecialAirHiHit: gravity speed 0 and its energy suspended (0x2717, 1)',
          kin(gm, 0x11, 1) and i2f(kin(gm, 0x11, 1)[-1][2]) == 0.0 and kin(gm, 0x2717, 1), str(kin(gm, 0x11, 1)))
    for n in range(60):
        b.call('master_hi_hit_loop')
        gm.take()
        gm.calls = [c for c in gm.calls if c[0] != 0x10]
        if 0x15C in gm.status:
            break
    check('v10 at the wall: 0x15B -> 0x15C latched', 0x15C in gm.status and b.g('master_hi_latched') == 1)
    b.g('global6', 0x15C)
    gm.calls.clear()
    b.call('master_hi_hit_end')
    check('v10 0x15B -> 0x15C keeps the fall off (no 0x2718)', not kin(gm, 0x2718, 1))
    gm.calls.clear()
    lr0 = gm.lr
    gm.frame = 0.0
    gm.fx.clear()
    b.call('master_hi_wall_main')
    turned = [a for s, a in gm.calls if s == 0x14 and a == [0x2710]]
    check('v10 the wall jump turns away from the wall (reverse_lr) and holds the fall', bool(turned) and kin(gm, 0x2717, 1),
          'calls %s' % [a for s, a in gm.calls if s == 0x14])
    jumped = None
    cling_fx = (0, list(gm.fx)) if gm.fx else None
    for n in range(1, 20):
        gm.calls.clear()
        gm.frame = float(n - 1)
        b.call('master_hi_wall_loop')
        if gm.fx and cling_fx is None:
            cling_fx = (n - 1, list(gm.fx))
        if kin(gm, 0x11, 1) and jumped is None:
            jumped = n
            jy = i2f(kin(gm, 0x11, 1)[-1][2])
            jx = kin(gm, 0x11, 2)
            fell = kin(gm, 0x2718, 1)
    check('v10 the cling: 13 frames (wall_jump_stop_frame), then 2.6 up on the gravity energy and 0.9 on air control, '
          'the fall back (0x2718)', jumped == 13 and abs(jy - 2.6) < 1e-5 and jx and abs(abs(i2f(jx[-1][2])) - 0.9) < 1e-5
          and fell, 'jumped at %s' % jumped)
    check('v12 the cling\'s effect (Ultimate\'s REQ_EFFECT at 6: sys_cling; the common ledge catch flash 0x100001E) once, '
          'at frame 6, on the point the sword met', cling_fx and cling_fx[0] == 6 and len(cling_fx[1]) == 1
          and cling_fx[1][0][0] == 0x100001E and abs(cling_fx[1][0][1] - i2f(latch[0])) < 0.01
          and abs(cling_fx[1][0][2] - i2f(latch[1])) < 0.01 and len(gm.fx) == 1, str(cling_fx))
    check('v11 the jump: 0x15C entered again (its main sets the speeds), flagged', 0x15C in gm.status
          and b.g('master_hi_wj_jump') == 1, str([hex(x) for x in gm.status]))
    gm.calls.clear()
    jumps0 = b.g('master_wall_jumps')
    b.call('master_hi_wall_end')
    b.call('master_hi_wall_main')
    check('v11 the re-entered main: the jump (gravity 2.6, air control 0.9), no turn, no extra wall jump counted, the '
          'motion kept at its frame', kin(gm, 0x11, 1) and abs(i2f(kin(gm, 0x11, 1)[-1][2]) - 2.6) < 1e-5
          and not [a for s, a in gm.calls if s == 0x14 and a == [0x2710]] and b.g('master_wall_jumps') == jumps0
          and [a for s, a in gm.calls if s == 0x12 and a and a[0] == 3], str(kin(gm, 0x11, 1)))
    # 2. the catch without a capture
    def tipped(frame, dx=0.0, dy=0.0, intangible=False):
        b, gm = setup(frame)
        tx = b.call('master_tip_x', int(frame - 18.0))
        ty = b.call('master_tip_y', int(frame - 18.0))
        gm.slots[1] = dict(x=i2f(tx) + dx, y=gm.y + i2f(ty) - 10.0 + dy, status=0x46, air=True, damage=20.0)
        if intangible:
            gm.slots[1]['intangible'] = 2.0
        return b, gm
    b, gm = tipped(21.0)
    b.call('master_hi_air_loop')
    first = 0x15B in gm.status
    gm.frame = 22.0
    gm.slots[1]['x'] = i2f(b.call('master_tip_x', 4))
    gm.slots[1]['y'] = gm.y + i2f(b.call('master_tip_y', 4)) - 10.0
    b.call('master_hi_air_loop')
    check('v10 no capture: the tip on a fighter two frames running -> caught (0x15B), not on the first (the grab box\'s)',
          not first and 0x15B in gm.status and b.g('master_target') == 1)
    check('v10 held without a capture: VAR_11 = 2 (CATCH: an air target), a hitstop each frame; v11 its 3 % left to '
          'the hit in SpecialAirHiHit\'s script (not added here)',
          gm.vars.get(0x0F00030B) == 2.0 and gm.vars.get(0x0F000100 + 0x20 * 4 + 0x17) is None
          and gm.vars.get(0x0F00005C + 8) == 3.0, str((gm.vars.get(0x0F00030B), gm.vars.get(0x0F00005C + 8))))
    # the hold, the reel, the overtake's hitbox frame
    gm.status.clear()
    gm.calls.clear()
    b.call('master_hi_hit_main')
    for n in range(60):
        b.call('master_hi_hit_loop')
        gm.take()
        gm.calls = [c for c in gm.calls if c[0] != 0x10] if b.g('master_phase') == 0 else gm.calls
        if b.g('master_phase') == 1:
            break
    gm.calls.clear()
    gm.frame = 5.0
    b.call('master_hi_hit_loop')
    kept = [a for s, a in gm.calls if s == 0x16 and len(a) == 3 and a[2] == 0x0F000024]
    gm.calls.clear()
    gm.frame = 11.0
    b.call('master_hi_hit_loop')
    at11 = (not kin(gm, 0x2718, 1), [a for s, a in gm.calls if s == 0x16 and len(a) == 3 and a[2] == 0x0F000001])
    gm.calls.clear()
    gm.frame = 12.0
    b.call('master_hi_hit_loop')
    check('v10 held without a capture: reeled in (phase 1), still held at the overtake\'s frame 5, let go at 11 (its '
          'hitbox frame); v12 he stays on it through 11 (no fall), the fall back at 12', b.g('master_phase') == 1 and kept
          and at11[0] and at11[1] and kin(gm, 0x2718, 1) and b.g('master_target') & 0xFFFFFFFF == 0xFFFFFFFF,
          'kept %s, frame 11 %s' % (kept, at11))
    for what, kw in (('20 away', dict(dx=20.0)), ('intangible', dict(intangible=True)), ('shielding', dict(status=0x1C))):
        b, gm = tipped(21.0, **{k: v for k, v in kw.items() if k != 'status'})
        if 'status' in kw:
            gm.slots[1]['status'] = kw['status']
        b.call('master_hi_air_loop')
        gm.frame = 22.0
        b.call('master_hi_air_loop')
        check('v10 no capture, a fighter %s: not caught' % what, 0x15B not in gm.status)
    b, gm = tipped(30.0)
    b.call('master_hi_air_loop')
    b.call('master_hi_air_loop')
    check('v10 after the window (30): not caught', 0x15B not in gm.status)
    # v12: point-blank (the blade, not only the tip: Ultimate's sword stops on what it meets), behind him not
    for what, dx, dy, want in (('at his hand (8 ahead, 6 up: the blade)', 8.0, 6.0, True), ('10 behind him', -10.0, 0.0, False)):
        b, gm = setup(21.0)
        gm.slots[1] = dict(x=gm.x + dx, y=gm.y + dy, status=0x46, air=True, damage=20.0)
        b.call('master_hi_air_loop')
        gm.frame = 22.0
        b.call('master_hi_air_loop')
        check('v12 no capture, a fighter %s: caught %s' % (what, 'yes' if want else 'no'), (0x15B in gm.status) == want)
    # v12: the tip's pulls (17 / 19) carry a fighter overlapping him (in hitstun) toward the catch point
    b, gm = setup(17.0)
    b.g('global4', 0xF1)
    gm.slots[1] = dict(x=gm.x - 2.0, y=gm.y + 4.0, status=0x46, air=True, damage=20.0)
    gm.vars[0x0F000058 + 8 * 1] = 12.0
    real_fvar = gm.fvar
    gm.fvar = lambda v: 12.0 if v == 0x0F000058 + 8 else real_fvar(v)
    b.call('master_vt_specialhi')
    check('v12 the tip\'s pull at 17 takes a fighter 2 behind his front (in hitstun) toward (16, 32) by 21',
          abs(gm.slots[1]['x'] - (-2.0 + (16.0 + 2.0) / 4.0)) < 0.01 and abs(gm.slots[1]['y'] - (54.0 + (82.0 - 54.0) / 4.0)) < 0.01,
          str(gm.slots[1]))
    # v12: the overtake's point from the caught fighter's waist (its joint read), a fighter on the ground: not reeled
    # under its feet
    for air, waist, want_end, want_on in ((True, 9.0, (30.0 - 7.8, 59.0 - 14.2), (30.0, 59.0)),
                                          (False, 9.0, (30.0 - 7.8, 50.0), (30.0, 59.0))):
        b, gm = setup(22.0)
        gm.y = 20.0
        gm.slots[1] = dict(x=30.0, y=50.0, status=0x46, air=air, damage=20.0, waist=waist)
        b.g('master_target', 1)
        b.g('master_soft', 1)
        b.g('master_tx', 30.0)
        b.g('master_ty', 50.0)
        run_hit(b, gm)
        end = gm.placed[-2][0]
        check('v12 the caught fighter %s, its waist 9 up: reeled to %s, then on (%g, %g)' % (
            'in the air' if air else 'on the ground', tuple(round(v, 1) for v in want_end), *want_on),
            end and abs(end[0] - want_end[0]) < 0.01 and abs(end[1] - want_end[1]) < 0.01
            and abs(gm.x - want_on[0]) < 0.01 and abs(gm.y - want_on[1]) < 0.01, 'end %s, on (%g, %g)' % (end, gm.x, gm.y))
    # 3. the ledge boxes by frame
    # (v18: before 15 the box Ultimate's init selects, the common AIR_LASSO (entry 4), not v10's normal box, entry 0)
    for f, box in ((12.0, 4), (13.0, 4), (14.0, 4), (15.0, 2), (16.0, 2)):
        b, gm = setup(f)
        gm.lasso = True
        b.call('master_hi_air_loop')
        sel = [a for s, a in gm.calls if s == 0x1A and a and a[0] == 0x2712]
        check('v18 the ledge box at frame %g: entry %d' % (f, box), (not sel and box is None) or (sel and sel[-1][1] == box),
              str(sel))
    # 4. Aymr's landings: (frame, landed?) -> what
    for f, want, what in ((40.0, 'ground', 'INHERIT_LANDING_1: the ground motion'), (52.0, 0x259, 'before the hop: Landing2'),
                          (56.0, 'air', 'after the hop (53): the air motion goes on'),
                          (62.0, 'air', 'FORBID_LANDING (60 - 65): the air motion and its hit'),
                          (70.0, 'ground', 'INHERIT_LANDING_2: the ground motion'), (120.0, 0x255, 'Landing1')):
        b, gm = setup(f)
        b.g('global4', 0x155)
        b.g('master_phase', 0)
        b.g('global19', 2)
        b.g('global18', 0)
        gm.situation = 0
        b.call('master_lw_loop')
        sets = [a[1] for s, a in gm.calls if s == 0x12 and a and a[0] in (1, 3) and len(a) > 1]
        got = 'air' if not sets else ('ground' if sets[-1] == 0x241 else sets[-1])
        check('v10 Aymr landing at %g (%s)' % (f, what), got == want, 'motions %s' % [hex(x) for x in sets])
    b, gm = setup(53.0)
    b.g('global4', 0x155)
    b.g('master_phase', 0)
    b.call('master_lw_loop')
    b.call('master_lw_loop')
    hops = kin(gm, 0x11, 1)
    check('v10 Aymr in the air at 53: the hop (gravity y + 1), once', len(hops) == 1 and i2f(hops[0][2]) == 1.0, str(hops))


def v16(path):
    """v16 (README "Status: v16"): Aymr's turn. SpecialLwTurn's game script turns him at its frame 8 with Reverse_Direction,
    which flips the facing only (the model test: gm.lr); the model turns (gm.rot) when the MSC calls update_rot_y_lr
    (PostureModule(0x2)) as the move resumes after the turn motion, at the frame it left, in both situations; never
    without the turn"""
    for air in (False, True):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        sit = 2 if air else 0
        b.g('global18', sit)
        b.g('global19', sit)
        b.g('global4', 0x155)
        gm.situation = sit
        b.g('master_phase', 0)
        b.g('master_flag', 0)
        gm.frame, gm.lr, gm.rot = 20.0, 1.0, 1.0
        gm.stick_x = -1.0                                # the stick back (he faces right)
        b.call('master_lw_loop')
        want_turn = 0x247 if air else 0x243
        sets = [a for s, a in gm.calls if s == 0x12 and a and a[0] == 1]
        check('v16 Aymr %s: the stick back at 20 -> the turn motion 0x%X' % ('air' if air else 'ground', want_turn),
              b.g('master_phase') == 4 and sets and sets[-1][1] == want_turn, str(sets))
        gm.stick_x = 0.0
        rots = []
        for f in range(1, 12):                           # the turn motion (12 frames); its script's Reverse_Direction at 8
            gm.frame = float(f)
            if f == 8:
                gm.lr = -gm.lr
            gm.end = f == 11
            gm.calls.clear()
            b.call('master_lw_loop')
            rots.append(gm.rot)
        sets = [a for s, a in gm.calls if s == 0x12 and a and a[0] == 1]
        back = 0x245 if air else 0x241
        check('v16 Aymr %s: the model faces the old way through the turn motion (its own 180), then turns as the move '
              'resumes (update_rot_y_lr)' % ('air' if air else 'ground'),
              rots[:-1] == [1.0] * 10 and rots[-1] == -1.0 and gm.lr == -1.0, 'rot %s lr %s' % (rots, gm.lr))
        check('v16 Aymr %s: the move resumes at the frame it left (20)' % ('air' if air else 'ground'),
              b.g('master_phase') == 0 and sets and sets[-1][1] == back and i2f(sets[-1][2]) == 20.0,
              str(sets))
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.g('global18', 0)
    b.g('global19', 0)
    b.g('global4', 0x155)
    gm.situation = 0
    b.g('master_phase', 0)
    b.g('master_flag', 0)
    gm.frame, gm.stick_x = 20.0, 1.0
    b.call('master_lw_loop')
    check('v16 Aymr: no turn (and no model turn) with the stick forward',
          b.g('master_phase') == 0 and not [a for s, a in gm.calls if s == 0x14 and a == [2]])


def v18(path):
    """v18 (README "Status: v18"): the up special's ledge boxes and the ledge before the wall; Aymr's armor every frame"""
    def setup(frame, lr=1.0):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 2)
        b.g('global19', 2)
        b.g('master_wall_jumps', 0)
        gm.frame, gm.lr = frame, lr
        return b, gm
    # 1. the air up special's main selects Ultimate's init box (the common AIR_LASSO, entry 3) before the loop
    b, gm = setup(0.0)
    b.call('master_hi_air_main')
    sel = [a[1] for s, a in gm.calls if s == 0x1A and a and a[0] == 0x2712]
    check('v18 the air up special starts with the box Ultimate\'s init selects (entry 4)', sel and sel[-1] == 4, str(sel))
    # 2. the clip's attempt (user v17, clip 75dbb69e frames 186 - 191): the ledge 16 ahead, 43 up during the check window
    for f, ledge, want, what in ((12.0, (16.0, 43.0), True, 'the clip\'s ledge (16 ahead, 43 up) at 12'),
                                 (13.0, (60.0, 70.0), True, 'a ledge 60 ahead, 70 up at 13 (the common AIR_LASSO reach)'),
                                 (13.0, (16.0, -20.0), True, 'a ledge 16 ahead, 20 below at 13'),
                                 (13.0, (90.0, 40.0), False, 'a ledge 90 ahead at 13 (past 75)'),
                                 (15.0, (16.0, 43.0), True, 'the clip\'s ledge at 15 (the tether box)'),
                                 (15.0, (60.0, 70.0), False, 'a ledge 60 ahead at 15 (the tether box: 44)')):
        b, gm = setup(f)
        gm.lasso = True
        gm.ledge = (gm.x + ledge[0], gm.y + ledge[1], -1.0)
        b.call('master_hi_air_loop')
        check('v18 up special: %s -> the ledge (0xF2) %s' % (what, 'yes' if want else 'no'), (0xF2 in gm.status) == want,
              'statuses %s, box %s' % ([hex(s) for s in gm.status], gm.box))
    # v17's box at 13 (entry 0) would have missed the clip's ledge
    gm = Game()
    gm.box, gm.ledge = 0, (16.0, gm.y + 43.0, -1.0)
    check('v18 (v17\'s entry 0 at 12 - 14 misses the clip\'s ledge)', not gm.ledge_in_box())
    # 3. a wall and a ledge both in reach: the ledge (the wall under its corner is not latched); no ledge: the latch
    for ledge, want in (((14.0, 62.0), 0xF2), (None, 0x15B)):
        b, gm = setup(19.0)
        gm.wall_x = 14.0
        gm.box = 2                                       # selected from 15 on and kept
        gm.ledge = (gm.x + ledge[0], gm.y + ledge[1], -1.0) if ledge else None
        b.call('master_hi_air_loop')
        check('v18 the tip meets a wall at 19 %s -> %s' % ('under a catchable ledge' if ledge else 'with no ledge',
              'the ledge (0xF2), no latch' if want == 0xF2 else 'the latch (0x15B)'),
              want in gm.status and (0x15B not in gm.status if want == 0xF2 else True),
              'statuses %s' % [hex(s) for s in gm.status])
    # a ledge behind the wall's side but not catchable (its hang direction the wrong way) -> the latch
    b, gm = setup(19.0)
    gm.wall_x, gm.box = 14.0, 2
    gm.ledge = (gm.x + 14.0, gm.y + 62.0, 1.0)
    b.call('master_hi_air_loop')
    check('v18 a ledge in the box facing away (not catchable) -> the wall latch', 0x15B in gm.status and 0xF2 not in gm.status,
          str([hex(s) for s in gm.status]))
    # 4. Aymr's armor every frame of 34 - 63 (mode 3, 30), off at 64, both situations; through a turn past 34; ends
    for air in (False, True):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        sit = 2 if air else 0
        b.g('global18', sit)
        b.g('global19', sit)
        b.g('global4', 0x155)
        gm.situation = sit
        b.call('master_lw_main')
        on, off = [], []
        for f in range(0, 64 if not air else 100):
            gm.frame = float(f)
            gm.calls.clear()
            b.call('master_lw_loop')
            for s, a in gm.calls:
                if s == 0x24 and a and a[0] == 0xB:
                    (on if a[1] == 3 and abs(i2f(a[2]) - 30.0) < 1e-4 else off).append(f)
        want_on = list(range(34, 64))
        check('v18 Aymr %s: armor (damage-based, 30) put on every frame 34 - 63' % ('air' if air else 'ground'),
              sorted(set(on)) == want_on, 'on %s' % on)
        check('v18 Aymr %s: the armor taken off when the window ends, not before 34' % ('air' if air else 'ground'),
              (64 in off or air is False) and not [f for f in off if f < 34], 'off %s' % off)
    # a turn at 38 (in the window) keeps the armor through the turn motion; a turn at 20 has none in it, then on past 34
    for turn_at, want_turn_armor in ((38.0, True), (20.0, False)):
        b, gm = Byleth(path), Game()
        b.vm.game = gm
        b.g('global18', 0)
        b.g('global19', 0)
        b.g('global4', 0x155)
        gm.situation = 0
        b.call('master_lw_main')
        b.g('master_flag', 0)
        gm.frame, gm.stick_x = turn_at, -1.0
        b.call('master_lw_loop')
        gm.stick_x = 0.0
        armored = []
        for f in range(1, 12):
            gm.frame = float(f)
            gm.end = f == 11
            gm.calls.clear()
            b.call('master_lw_loop')
            armored.append(any(s == 0x24 and a[:2] == [0xB, 3] for s, a in gm.calls))
        check('v18 Aymr turned at %g: armor %s through the turn motion' % (turn_at, 'kept' if want_turn_armor else 'not on'),
              all(armored[:-1]) if want_turn_armor else not any(armored[:-1]), str(armored))
    b, gm = Byleth(path), Game()
    b.vm.game = gm
    b.call('master_lw_end')
    check('v18 Aymr: the status end takes the armor off', [a[:2] for s, a in gm.calls if s == 0x24] == [[0xB, 0]])
    v18_rapid()


def v18_rapid():
    """v18: the rapid-jab loop as ultimate_acmd translates Ultimate's Attack100 (HOLD_WAVE_CLEAR) and master_build.rapid_v18
    makes the installed one: 6 waves a loop at Ultimate's frames 2 / 5 / ... / 17, each Hit_Log_Clear(0) first, its two
    hits (IDs 0 / 1, Part 0, 0.4 %, 361) with Hitbox_Hold(ID, 1) and Ultimate's hitlag (2) as fixed hitstop frames on both
    sides, removed the next frame (Ultimate's 1-frame hits); the hitlag rule; port_check S30 on both"""
    import acmd
    import ultimate_acmd as U
    import master_build as MB
    check('v18 ult_hitlag: the rapid jab\'s 0.4 % x 0.4 -> 2 frames; a 3 % hit x 1 -> 7', U.ult_hitlag(0.4, 0.4) == 2
          and U.ult_hitlag(3.0, 1.0) == 7)
    try:
        import port_sources
        dump = os.path.join(port_sources.load().dump('master'), 'master', 'Attack100.txt')
        body = U.functions(open(dump).read())['game_attack100']
    except Exception as e:             # noqa: BLE001
        check('v18 rapid jab: Ultimate\'s Attack100 dump found', False, str(e))
        return

    def waves(cmds):
        out, frame, cur = [], None, None
        for k, c in enumerate(cmds):
            if c.name == 'FRAME':
                frame = float(c.params[0])
            if c.name == 'Hit_Log_Clear':
                cur = dict(frame=frame, clear=c.params[0], hits=[], removed=None)
                out.append(cur)
            if c.name in ('Extra_Special_Hitbox',) and cur is not None:
                d = dict(zip(c.info['syntax'], c.params))
                held = k + 1 < len(cmds) and cmds[k + 1].name == 'Hitbox_Hold' and cmds[k + 1].params == [d['ID'], 1]
                cur['hits'].append((d['ID'], d['Part'], round(d['Damage'], 3), d['Angle'], d['HitstopFrames'],
                                    d['SelfHitstopFrames'], round(d['HitstunMul'], 3), held))
            if c.name == 'WAIT' and cur is not None and cur['removed'] is None:
                cur['removed'] = c.params[0]
        return out
    want = [dict(frame=f, clear=0, hits=[(0, 0, 0.4, 361, 2, 2, -3.0, True), (1, 0, 0.4, 361, 2, 2, -3.0, True)], removed=1)
            for f in (2.0, 5.0, 8.0, 11.0, 14.0, 17.0)]
    tr = U.Translator({})
    got = waves(tr.script(body))
    check('v18 translator: Attack100 -> 6 waves (2 - 17), each Hit_Log_Clear(0) then IDs 0 / 1 held, hitstop 2 / 2, '
          '+3 hitstun, removed after 1 frame', got == want, str(got[:2]))
    S = os.environ.get('BYLETH_GAME_BIN')
    if S and os.path.exists(S):
        g = acmd.ACMDFile.load(S)
        check('v18 the installed attack100 (BYLETH_GAME_BIN) has the same waves', waves(g.scripts[acmd.crc('attack100')])
              == want, str(waves(g.scripts[acmd.crc('attack100')])[:2]))
        check('v18 rapid_v18 is idempotent on it', MB.rapid_v18(g) == [])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else compiled()
    failnaught(path)
    up_special(path)
    v9(path)
    v10(path)
    v15_scripts()
    v16(path)
    v17_static()
    v18(path)
    print('\n%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
