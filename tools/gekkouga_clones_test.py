#!/usr/bin/env python3
"""Greninja's clones / smash charges mod (fighters/gekkouga/README.md "Clones v1"): the tests.

  python3 tools/gekkouga_clones_test.py OUT PACKAGE.zip USER_ANIMCMD BASE.rpx [BASE_DIAG.rpx] [--v1=V1.zip]

v2 (README "Clones v2"): with --v1 the package is the update over greninja_clones_v1.zip (only the files that differ
from it, plus README.txt); the clones' own fall / landing, the jump with him, a launch, the fall off the stage, his
hitlag from their hits and the freeze, their hand / face files.

OUT: tools/gekkouga_build.py all's output folder (fighter/gekkouga, fighter/kirby); PACKAGE.zip: the package;
USER_ANIMCMD: his script/animcmd the package's body scripts were made from (the user's); BASE.rpx: the executable the
package's cross_f.rpx was built on (exe_v46z_ui10; its _diag for TEST_ONLY's).

1. MSC logic: the compiled gekkouga.mscsb run in a small MSC interpreter (tools/rolloff_hold_test.py's VM) with the
   game's modules stubbed, function by function as the game calls them: the down special charge (accumulation, kept
   across releases, the 300-frame threshold, the bar's pips), the ability (720 frames: the clones made at 0 / 3 with
   their ids, the channel, the name tag / clone flags, their removal), the burnout (480: grey every frame, the slow
   flag, the down special blocked), the swaps (offsets, his move, a dead clone, the cooldown), a clone hit (the
   nearest one, its log at its place, his place back, the capsules), a KO ending it, the smash charge store (kept,
   released early = no attack, full = ready, auto release with the hold's exit values), the chains (windows, each
   smash once, the end of a chain);
2. the clone article's MSC (clone.mscsb): finding him, its id, its place, facing and motion, hidden when not alive;
3. the scripts: his smashes' hitbox / effect sizes x1.5, nothing else of his changed, the clone's scripts (his hitbox
   scripts, bones as the article's joints, his smashes' damage x1.4), its motion.mtable his;
4. the package: every file, the exe (cross_f.rpx = exe_v46z_gk2 (v1: gk1) built from BASE, its diag), README, no fighter-named
   wrapper folder, Kirby's MSC with Greninja's trait;
5. msc_stack_check (stack, globals <= 128) on both MSCs, import_call_check (0) on both executables, the cave's
   unicorn test (tools/gekkouga_clone_cave_test.py).
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rolloff_hold_test as R  # noqa: E402
import msc_stack_check  # noqa: E402
import acmd  # noqa: E402
import gekkouga_build as GB  # noqa: E402

fails = 0
checks = 0


def check(what, got, want):
    global fails, checks
    checks += 1
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


f2i, i2f = R.f2i, R.i2f


def fv(v):
    return round(i2f(v), 3)


class Game:
    """the modules his MSC uses, stubbed"""

    def __init__(self):
        self.vars = {}             # float variables (0x0F......), status floats
        self.ints = {}
        self.flags = set()
        self.x, self.y, self.z, self.lr = 0.0, 10.0, 0.0, 1.0
        self.situation = 0
        self.press = set()         # ControlModule(0x2710, n): pressed this frame
        self.held = set()          # ControlModule(0x2712, n): held
        self.stick = (0.0, 0.0)
        self.motion, self.frame, self.rate = 0, 0.0, 1.0
        self.rand = 0.5
        self.status_req = []
        self.log = []
        self.shapes = {}
        self.posture_sets = []
        self.hitlag = 0            # StopModule(1)
        self.floors = [(-1000.0, 1000.0, 10.0)]   # the stage's floors (x0, x1, y): his line test (LINE_* variables)
        self.walls = []            # (x, y0, y1)
        self.ceilings = []         # (x0, x1, y)
        self.beat = 3              # v3: the clones' heartbeat bits their MSCs write into his VAR_30 each frame
        self.line_tests = 0
        self.air_kind = 0          # aerial chain v1: ControlModule(0x10): the air attack the input asks for (1 n - 5 d)
        self.atk_hit = 0           # AttackModule(0x2727, kinds): what his attack hit since it started (2 hurtbox, 4 shield)

    def line_test(self):
        """the Line_Test variables: a vertical segment (X0, Y0) -> (X0, Y1) meets the nearest floor (going down) or
        ceiling (going up); a horizontal one (Y0 = Y1) the nearest wall"""
        self.line_tests += 1
        x, y0, x1_, y1 = (self.vars.get(0x0F0003D0 + i, 0.0) for i in (0, 1, 2, 3))
        V = self.vars
        hit = None
        if abs(x1_ - x) < 1e-6:
            if y1 <= y0:
                fl = [fy for a, b, fy in self.floors if a <= x <= b and y1 <= fy <= y0]
                if fl:
                    hit = (x, max(fl), 1.0)
            else:
                cl = [cy for a, b, cy in self.ceilings if a <= x <= b and y0 <= cy <= y1]
                if cl:
                    hit = (x, min(cl), 3.0)
        else:
            lo, hi = min(x, x1_), max(x, x1_)
            wl = [wx for wx, a, b in self.walls if lo <= wx <= hi and a <= y0 <= b]
            if wl:
                hit = (min(wl, key=lambda w: abs(w - x)), y0, 2.0)
        if hit:
            V[0x0F0003D4], V[0x0F0003D6], V[0x0F0003D7], V[0x0F0003D8] = 1.0, hit[0], hit[1], hit[2]
        else:
            V[0x0F0003D4], V[0x0F0003D6], V[0x0F0003D7], V[0x0F0003D8] = 0.0, x1_, y1, 0.0

    def sys(self, sid, a):
        if sid == 0x16:                                       # WorkModule
            op = a[0]
            if op == 0:
                self.vars[a[2]] = fv(a[1])
                if a[2] == 0x0F0003D4:
                    self.line_test()
                return 0
            if op == 2:
                if a[2] == 0x0F000000:
                    self.x = round(self.x + fv(a[1]), 3)
                if a[2] == 0x0F000001:
                    self.y = round(self.y + fv(a[1]), 3)
                return 0
            if op == 0x6:
                return self.ints.get(a[1], 0)
            if op == 0x7:
                self.ints[a[2]] = a[1]
                return 0
            if op in (0x9, 0xA):
                self.ints[a[1]] = self.ints.get(a[1], 0) + (1 if op == 0x9 else -1)
                return 0
            if op == 0x10:
                return int(a[1] in self.flags)
            if op == 0x2710:
                self.flags.add(a[1])
                return 0
            if op == 0x2711:
                self.flags.discard(a[1])
                return 0
            return 1
        if sid == 0x17:                                       # WorkModuleF(0, id)
            if a[1] == 0x8000003:
                return f2i(10.0)
            return f2i(self.vars.get(a[1], 0.0))
        if sid == 0xE:                                        # ControlModule
            if a[0] == 0x10:
                return self.air_kind
            if a[0] == 0x2710:
                return int(a[1] in self.press)
            if a[0] == 0x2712:
                return int(a[1] in self.held)
            return 0
        if sid == 0xF:                                        # ControlModuleF(0 / 1): the stick
            return f2i(self.stick[a[0]] if a[0] in (0, 1) else 0.0)
        if sid == 0x15:                                       # PostureModuleF
            return f2i({0: self.lr, 1: self.x, 2: self.y, 3: self.z}.get(a[0], 0.0))
        if sid == 0x14:                                       # PostureModule
            if a[0] == 0x3:
                self.x, self.y, self.z = fv(a[1]), fv(a[2]), fv(a[3])
                self.posture_sets.append((self.x, self.y))
            elif a[0] == 0x1:
                self.lr = -self.lr
            self.log.append(('posture', a[0]))
            return 0
        if sid == 0x12:                                       # MotionModule
            if a[0] == 0x7:
                return self.motion
            if a[0] == 0x4:
                self.log.append(('rate', fv(a[1])))
            return 0
        if sid == 0x13:                                       # MotionModuleF
            return f2i({0x1: self.frame, 0xA: self.rate}.get(a[0], 0.0))
        if sid == 0x18:                                       # StatusModule
            if a[0] == 0x1:
                return self.situation
            if a[0] == 0x3:
                self.status_req.append((a[1], a[2]))
            return 0
        if sid == 0xA:                                        # MathF(6): random 0-1
            return f2i(self.rand)
        if sid == 0x20:                                       # ArticleModule
            self.log.append(('article', a[0], a[1]))
            return 0
        if sid == 0x21:                                       # BattleObject
            if a[0] == 0xA:
                self.log.append(('cursor', a[1]))             # the player cursor (name tag) shown / hidden
                return 0
            self.log.append(('battleobject', a[0], self.x, self.y))
            return 0
        if sid == 0x36:                                       # ShieldModule(0, 2, shape, on, 1)
            if a[0] == 0 and a[1] == 2 and a[4] == 1:
                self.shapes[a[2]] = a[3]
            return 0
        if sid == 0x1C:                                       # EffectModule
            self.log.append(('effect', a[0], a[1]) + tuple(fv(x) for x in a[2:6]))
            if a[0] in (0x2710, 0x2712) and len(a) > 9:
                self.log.append(('fxsize', a[0], a[1], a[2], fv(a[9])))   # op, id, bone, size
            return 0
        if sid == 0x42:                                       # ColorBlendModule
            self.log.append(('colour', a[0]) + tuple(fv(x) if i < 4 and a[0] == 0x2711 else x
                                                     for i, x in enumerate(a[1:])))
            return 0
        if sid == 0x30:                                       # StopModule(1): in hitlag; (2, n): hitlag n
            if a[0] == 0x2:
                self.log.append(('hitlag', a[1]))
                self.hitlag = a[1]
                return 0
            return int(self.hitlag > 0)
        if sid == 0x39:
            self.log.append(('visible', a[1]))
            return 0
        if sid == 0x2E:                                       # AttackModule
            if a[0] == 0x2727:
                return int(self.atk_hit & a[1] != 0)
            if a[0] == 0x2724:
                self.log.append(('atk_clear',))
                self.atk_hit = 0
            return 0
        return 0


class MSC:
    """a compiled MSC and its source: functions by name, named globals by name"""

    def __init__(self, mscsb, source):
        self.vm = R.VM(mscsb)
        src = open(source).read()
        names = msc_stack_check.function_names([source])
        assert len(names) == len(self.vm.m.scripts), (len(names), len(self.vm.m.scripts))
        self.fn = {n: self.vm.m.scripts[i] for i, n in enumerate(names)}
        self.addr = {n: self.vm.m.scripts[i].bounds[0] for i, n in enumerate(names)}
        body = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
        body = re.sub(r'//[^\n]*', '', body)
        gl = re.findall(r'^(?:int|float)\s+(\w+)\s*;', body, re.M)
        self.gidx = {n: i for i, n in enumerate(gl)}
        self.game = Game()
        self.vm.game = self.game

    def __call__(self, name, *args):
        r = self.vm.call(self.fn[name], [a & 0xFFFFFFFF for a in args])
        return R.s32(r) if r is not None else None

    def g(self, name):
        return self.vm.g.get(self.gidx[name], 0)

    def gf(self, name):
        return round(i2f(self.g(name)), 3)

    def setg(self, name, v):
        self.vm.g[self.gidx[name]] = v & 0xFFFFFFFF

    def setgf(self, name, v):
        self.vm.g[self.gidx[name]] = f2i(v)


def fresh(mscsb, src):
    m = MSC(mscsb, src)
    m.vm.g[11] = m.addr['func_17']          # func_16 -> func_17 -> StatusModule(3, status, keep)
    m.vm.g[14] = 0
    return m


def stub_fn(m, name, value):
    """one of the MSC's functions answering `value` (e.g. the clone delay's gk_delay / cl_delay at 0: the tests written
    before it, of the physics / playback it delays)"""
    orig, tgt = m.vm.call, m.fn[name]

    def call(script, args=()):
        return value if script is tgt else orig(script, args)
    m.vm.call = call
    return m


def fresh_nodelay(mscsb, src):
    return stub_fn(fresh(mscsb, src), 'gk_delay', 0)


def frames(m, n, st=0):
    m.vm.g[4] = st
    for _ in range(n):
        m.game.press = set()
        m.game.vars[0x0F00031E] = float(m.g('gk_alive') & m.game.beat)   # the clones' MSCs: their heartbeat bits
        m('gekkouga_frame')


def msc_tests(mscsb, src):
    # ---- the charge: accumulation, kept, threshold
    m = fresh(mscsb, src)
    g = m.game
    check('constants: 300 / 720 / 480 / gap 14 / smash full 120 (v3) / hitbox growth 5 (v4)',
          (m('gk_lw_full'), m('gk_ability_frames'), m('gk_burnout_frames'), round(i2f(m('gk_gap') & 0xFFFFFFFF), 3),
           m('gk_smash_full'), round(i2f(m('gk_smash_grow') & 0xFFFFFFFF), 3)), (300, 720, 480, 14.0, 120, 5.0))
    r = m('gk_lw_press')
    check('down special, not charged: the stance (status 0x155)', (r, g.status_req), (1, [(0x155, 1)]))
    g.status_req = []
    m('gk_lw_main')
    for _ in range(99):
        m('gk_lw_tick')
    check('100 frames held: charge 100', m.g('gk_lw_charge'), 100)
    pips = [x for x in g.log if x[0] == 'effect' and x[2] == 0x1000047]
    check('v6: no pips over his head any more (the gauge is on his damage panel)', pips, [])
    m('gekkouga_frame')
    check('v6: the panel gauge (his VAR_19): charge mode 1, 100 / 300 frames -> 1000 + 33', g.vars.get(0x0F000313), 1033.0)
    g.held = {1}
    g.frame = 20.0
    r = m('gk_lw_loop')
    check('held, at the stance frame: held there (rate 0), no exit', (r, g.status_req, g.log[-1]), (0, [], ('rate', 0.0)))
    g.held = set()
    r = m('gk_lw_loop')
    check('released: out of the stance (Wait), the charge kept', (r, g.status_req, m.g('gk_lw_charge')), (1, [(0, 0)], 100))
    g.status_req = []
    m('gk_lw_press')
    m('gk_lw_main')
    for _ in range(198):
        m('gk_lw_tick')
    check('the next press: from 100 (main + 198 ticks: 299)', m.g('gk_lw_charge'), 299)
    g.held = {1}
    check('299: not ready (still held)', m('gk_lw_loop'), 0)
    m('gk_lw_tick')
    check('300: full', m.g('gk_lw_charge'), 300)
    m('gk_lw_tick')
    check('kept at 300', m.g('gk_lw_charge'), 300)
    g.status_req = []
    g.log = []
    r = m('gk_lw_loop')
    check('full: the stance ends (ready flash 0x1000069)', (r, g.status_req, [x[2] for x in g.log if x[0] == 'effect']),
          (1, [(0, 0)], [0x1000069, 0x1000047]))
    pips = [x for x in m.game.log if x[0] == 'effect' and x[1] == 0x2723]
    check('the bar killed at the end', [(x[2]) for x in pips], [0x1000047])
    # ---- the ability
    g.status_req = []
    g.log = []
    r = m('gk_lw_press')
    check('ready: the press starts the ability (no status), the charge used',
          (r, g.status_req, m.g('gk_ability'), m.g('gk_lw_charge')), (0, [], 720, 0))
    g.x = 50.0
    frames(m, 1)
    check('v4: frame 0: the left clone requested (flags + 64: the TEST_ONLY exe logs it before the generate), none made yet',
          ([x for x in g.log if x[0] == 'article'], int(g.vars.get(0x0F000314)) & 0xC0), ([], 0x40))
    frames(m, 1)
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 1: the left clone (article 6) made, VAR_31 = 4747000 + alive 1 + being made (left) 4, its smoke at X - 14',
          (arts, g.vars.get(0x0F00031F), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
          ([('article', 0x2710, 6)], 4747005.0, [36.0]))
    check('v6: the gauge in the ability: mode 2, 719 / 720 left -> 99', g.vars.get(0x0F000313), 2099.0)
    check('v2: the ability hides his name tag (the cursor op BattleObject(0xA, 0))', [x for x in g.log if x[0] == 'cursor'],
          [('cursor', 0)])
    frames(m, 3)
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 4: the right clone (article 7), VAR_31 = 4747000 + 3 + being made (right) 8, its smoke at X + 14',
          (arts[-1], g.vars.get(0x0F00031F), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006][-1]),
          (('article', 0x2710, 7), 4747011.0, 64.0))
    check('flags: tag hidden (1) + v3 diag clones out (16 + 32)', g.vars.get(0x0F000314), 49.0)
    g.motion, g.frame, g.rate = 0x5F, 7.0, 1.0
    frames(m, 3)
    check('v3 channel: left clone X / Y 36 / 10, right 64 / 10, motion 0x5F x 1024 + frame 7, rate 1, the heartbeat '
          'cleared (0), 4747000 + alive 3', [g.vars.get(0x0F000318 + i) for i in range(8)],
          [36.0, 10.0, 64.0, 10.0, 95.0 * 1024 + 7.0, 1.0, 0.0, 4747003.0])
    check('v3: no shield capsules (the clones have their own hurtboxes): shapes 0-3 off', g.shapes, {0: 0, 1: 0, 2: 0, 3: 0})
    check('v3: flags: bit 4 ("clones out": his shield shapes report) no longer set; 1 + 16 + 32',
          g.vars.get(0x0F000314), 49.0)
    g.lr = -1.0
    frames(m, 1)
    check('facing left: still no capsules', g.shapes, {0: 0, 1: 0, 2: 0, 3: 0})
    g.lr = 1.0
    m.vm.g[4] = 0x74
    m('gekkouga_frame')
    check('on a ledge (0x74, CliffWait): the clones play Wait1 / Fall', g.vars.get(0x0F00031C) // 1024, 0.0)
    g.situation = 2
    m.vm.g[4] = 0x46
    m('gekkouga_frame')
    check('v2: hit in the air (0x46): standing clones Wait1 (they stay where they are; a falling one plays Fall)',
          g.vars.get(0x0F00031C) // 1024, 0.0)
    g.situation = 0
    frames(m, 1)
    # ---- swaps
    x0 = g.x
    g.press, g.stick = {1}, (-0.8, -0.8)
    m.vm.g[4] = 0
    m.vm.g[24] = 0x8000
    m('gekkouga_frame')
    check('down special + left: swapped with the left clone (him -14), Buffer_Clear specials (32), the frame\'s special bits off',
          (round(g.x - x0, 3), m.gf('gk_off_l'), m.gf('gk_off_r'), g.vars.get(0x0F0003C9), m.vm.g[24] & 0xF000, g.status_req),
          (-14.0, 14.0, 28.0, 32.0, 0, []))
    check('v2: ... the clone now at his old place (X, Y), the other one where it stood',
          (m.gf('gk_lx'), m.gf('gk_ly'), m.gf('gk_rx'), m.gf('gk_ry'), g.y), (x0, 10.0, x0 + 14.0, 10.0, 10.0))
    x1 = g.x
    m('gekkouga_frame')
    check('the cooldown: the same press again does nothing', g.x, x1)
    frames(m, 10)
    g.press, g.stick = {1}, (0.8, -0.8)
    m('gekkouga_frame')
    check('down special + right: swapped with the right clone (him +28), offsets -14 / -28',
          (round(g.x - x1, 3), m.gf('gk_off_l'), m.gf('gk_off_r')), (28.0, -14.0, -28.0))
    frames(m, 10)
    g.press, g.stick = {1}, (0.0, -1.0)
    x2 = g.x
    m('gekkouga_frame')
    check('plain down special: nothing (no swap, no stance)', (g.x, g.status_req), (x2, []))
    r = m('gk_lw_press')
    check('the input sites during the ability: no stance', (r, g.status_req), (0, []))
    g.press, g.stick = {1}, (0.0, 1.0)
    m.vm.g[24] = 0x4000
    m('gekkouga_frame')
    check('up special during the ability: left alone', m.vm.g[24] & 0x4000, 0x4000)
    # ---- v3: a clone's own hurtbox hit (the executable: VAR_21 = 20000 + its id): exactly that clone
    frames(m, 1)
    g.log = []
    g.vars[0x0F000315] = 10000.0 - 12.0
    frames(m, 1)
    check('v1 / v2\'s shield-capsule report (10000 + dx): ignored now, cleared', (m.g('gk_alive'), g.vars.get(0x0F000315)), (3, 0.0))
    g.log = []
    g.posture_sets = []
    g.vars[0x0F000315] = 20000.0 + 1.0
    xh, g.rand = g.x, 0.5
    frames(m, 1)
    check('v3: a hit on the left clone\'s hurtbox (20001): it is gone (article 6 removed), its smoke, the log (0x3F7) at its place, him back',
          ([x for x in g.log if x[0] in ('article', 'battleobject')], g.posture_sets, g.x, m.g('gk_alive'), g.vars.get(0x0F000315)),
          ([('article', 0x2712, 6), ('battleobject', 0x3F7, xh - 14.0, 10.0)], [(xh - 14.0, 10.0), (xh, 10.0)], xh, 2, 0.0))
    check('the channel: alive 2', g.vars.get(0x0F00031F), 4747002.0)
    g.press, g.stick = {1}, (-0.8, -0.8)
    xs = g.x
    frames(m, 10)
    g.press, g.stick = {1}, (-0.8, -0.8)
    m('gekkouga_frame')
    check('swap with the dead left clone: nothing', g.x, xs)
    g.log = []
    g.rand = 0.05
    g.vars[0x0F000315] = 20000.0 + 2.0
    frames(m, 1)
    check('a hit with the right clone the only one: it (0x2712 7), the rare doll (0x3F8: rand 0.05 <= 10%)',
          [x[:3] for x in g.log if x[0] in ('article', 'battleobject')], [('article', 0x2712, 7), ('battleobject', 0x3F8, xs - 28.0)])
    check('no clones: flags tag only (1), the capsules off', (g.vars.get(0x0F000314), g.shapes), (1.0, {0: 0, 1: 0, 2: 0, 3: 0}))
    # ---- the ability's end, the burnout
    left = m.g('gk_ability')
    g.log = []
    frames(m, left)
    check('the ability ran 720 frames in all, then the burnout 480', (m.g('gk_ability'), m.g('gk_burnout')), (0, 480))
    check('v6: the gauge in the burnout: mode 3, 480 / 480 left -> 99 (100 is only the charge\'s "ready")', g.vars.get(0x0F000313), 3099.0)
    check('its end: the channel closed (magic 0), flags 2 (slow)', (g.vars.get(0x0F00031F), g.vars.get(0x0F000314)), (0.0, 2.0))
    cur = [x for x in g.log if x[0] == 'cursor']
    check('v2: the name tag hidden again every 60 frames during it, shown at its end (BattleObject(0xA, 1))',
          (len(cur) >= 10, cur[-1], all(c == ('cursor', 0) for c in cur[:-1])), (True, ('cursor', 1), True))
    g.log = []
    frames(m, 1)
    grey = [x for x in g.log if x[0] == 'colour']
    check('burnout: the grey overlay every frame (0x2711 110 110 110 170, priority 0x65)', grey,
          [('colour', 0x2711, 110.0, 110.0, 110.0, 170.0), ('colour', 0x271A, 0x65)])
    g.press, g.stick = {1}, (0.0, -1.0)
    m.vm.g[24] = 0x8000
    g.vars[0x0F0003C9] = 0
    m('gekkouga_frame')
    check('burnout: down special cleared from the buffer, no stance', (g.vars.get(0x0F0003C9), m('gk_lw_press'), g.status_req),
          (32.0, 0, []))
    m.setg('gk_lw_charge', 300)
    check('burnout: even charged, no ability', (m('gk_lw_press'), m.g('gk_ability')), (0, 0))
    m.setg('gk_lw_charge', 0)
    g.log = []
    frames(m, 478)
    check('480 frames: over, the overlay off (alpha 0, FLASH_OFF), flags 0', (m.g('gk_burnout'), [x for x in g.log if x[0] == 'colour'][-2:], g.vars.get(0x0F000314)),
          (0, [('colour', 0x2711, 0.0, 0.0, 0.0, 0.0), ('colour', 0x2713)], 0.0))
    # ---- a KO ends the ability (no burnout) and the burnout
    m2 = fresh(mscsb, src)
    m2.setg('gk_lw_charge', 300)
    m2('gk_lw_press')
    frames(m2, 5)
    m2.game.log = []
    frames(m2, 1, st=0xB1)
    check('KO (0xB1): the clones removed, no burnout, the channel closed',
          ([x for x in m2.game.log if x[0] == 'article'], m2.g('gk_ability'), m2.g('gk_burnout'), m2.game.vars.get(0x0F00031F)),
          ([('article', 0x2712, 6), ('article', 0x2712, 7)], 0, 0, 0.0))
    m2.setg('gk_burnout', 100)
    frames(m2, 1, st=0xB2)
    check('respawn (0xB2): the burnout ended', m2.g('gk_burnout'), 0)
    m2.setg('gk_lw_charge', 120)
    frames(m2, 1, st=0xB1)
    check('the charge survives a KO', m2.g('gk_lw_charge'), 120)
    m2.setg('gk_smash', 33)
    frames(m2, 1, st=0xB2)
    check('the smash charges survive a KO / respawn', (m2.g('gk_smash'), m2.g('gk_lw_charge')), (33, 120))
    frames(m2, 1, st=0x14F)
    check('the match\'s start (Entry 0x14F): every charge from 0', (m2.g('gk_smash'), m2.g('gk_lw_charge')), (0, 0))

    # ---- smash attacks
    m = fresh(mscsb, src)
    g = m.game
    m('gk_sm_start_main', 1)
    check('forward smash, nothing stored: not automatic', m.g('gk_sm_auto'), 0)
    g.held = {0}
    check('before the hold point (flag 0x2100001B off): nothing', (m('gk_sm_start_loop', 1), g.status_req), (0, []))
    g.flags.add(0x2100001B)
    check('at the hold point, attack held: the hold (0x2C)', (m('gk_sm_start_loop', 1), g.status_req), (1, [(0x2C, 1)]))
    g.status_req = []
    m.vm.g[4] = 0x2C
    for _ in range(30):
        m('gk_sm_hold_tick')
    check('30 hold frames: the (shared, v3) charge 30', m.g('gk_smash'), 30)
    g.held = set()
    check('released before full: Wait (no attack), the charge kept', (m('gk_sm_hold_loop', 1), g.status_req, m.g('gk_smash')), (1, [(0, 0)], 30))
    g.status_req = []
    g.held = set()
    m('gk_sm_start_main', 1)
    check('a tap (released before the hold point): no attack', (m('gk_sm_start_loop', 1), g.status_req), (1, [(0, 0)]))
    g.status_req = []
    g.held = {0}
    m('gk_sm_start_main', 1)
    m('gk_sm_start_loop', 1)
    g.status_req = []
    for _ in range(40):
        m('gk_sm_hold_tick')
    check('v3: 30 + 40 frames: 70 (full is 120 now): not full, still holding', (m.g('gk_smash'), m('gk_sm_hold_loop', 1), g.status_req), (70, 0, []))
    for _ in range(60):
        m('gk_sm_hold_tick')
    check('70 + 60 frames: capped at 120', m.g('gk_smash'), 120)
    check('full while held: ready (flash), Wait, no attack', (m('gk_sm_hold_loop', 1), g.status_req, m.g('gk_smash')), (1, [(0, 0)], 120))
    g.status_req = []
    m.vm.g[4] = 0x2B
    m('gk_sm_start_main', 1)
    check('the next forward smash: automatic (1)', m.g('gk_sm_auto'), 1)
    g.held = set()
    r = m('gk_sm_start_loop', 1)
    check('at the hold point, not even held: the attack (0x2D, keep), ratio 1.0, charged flag, the store used, chain = forward',
          (r, g.status_req, g.vars.get(0x1000000), 0x21000002 in g.flags, m.g('gk_smash'), m.g('gk_chain')),
          (1, [(0x2D, 1)], 1.0, True, 0, 1))
    g.status_req = []
    m.vm.g[4] = 0x2D
    g.frame = 15.0
    m.vm.g[24] = 0x20
    check('frame 15 of the forward smash: no chain yet (window 16)', (m('gk_chain_try', 1), g.status_req), (0, []))
    g.frame = 16.0
    m.vm.g[24] = 0x10
    check('forward smash again: refused (used in the chain)', (m('gk_chain_try', 1), g.status_req), (0, []))
    m.vm.g[24] = 0x20
    check('frame 16, up smash: chained (0x31)', (m('gk_chain_try', 1), g.status_req, m.g('gk_chain_req')), (1, [(0x31, 1)], 2))
    g.status_req = []
    m.vm.g[4] = 0x31
    m('gekkouga_frame')
    check('the chain goes on through the start status', m.g('gk_chain'), 1)
    m.setg('gk_smash', 25)
    m('gk_sm_start_main', 2)
    check('the chained up smash: automatic (2), the store untouched', (m.g('gk_sm_auto'), m.g('gk_smash')), (2, 25))
    r = m('gk_sm_start_loop', 2)
    check('its release: 0x33, chain forward + up, store kept', (g.status_req, m.g('gk_chain'), m.g('gk_smash')), ([(0x33, 1)], 3, 25))
    g.status_req = []
    m.vm.g[4] = 0x33
    g.frame = 21.0
    m.vm.g[24] = 0x40
    check('up smash frame 21: no chain (window 22)', m('gk_chain_try', 2), 0)
    g.frame = 22.0
    check('frame 22, down smash: chained (0x2E)', (m('gk_chain_try', 2), g.status_req), (1, [(0x2E, 1)]))
    g.status_req = []
    m.vm.g[4] = 0x2E
    m('gk_sm_start_main', 4)
    m('gk_sm_start_loop', 4)
    check('down smash released: all three used (7)', (g.status_req, m.g('gk_chain')), ([(0x30, 1)], 7))
    g.status_req = []
    m.vm.g[4] = 0x30
    g.frame = 30.0
    for b in (0x10, 0x20, 0x40):
        m.vm.g[24] = b
        check('all three used: no more chains (input 0x%X)' % b, m('gk_chain_try', 4), 0)
    m.vm.g[24] = 0
    frames(m, 1, st=0)
    check('back to Wait: the chain ends', m.g('gk_chain'), 0)
    m.vm.g[4] = 0x2D
    g.situation = 2
    check('no chain in the air', m('gk_chain_try', 1), 0)
    g.situation = 0
    m.vm.g[4] = 0x2D
    m.setg('gk_chain', 1)
    g.frame = 17.0
    m.vm.g[24] = 0x10
    g.lr = 1.0
    g.stick = (-0.9, 0.0)
    m.setg('gk_chain', 2)
    m('gk_chain_try', 1)
    check('a forward smash chained the other way: turned first (PostureModule 1, 2)',
          [x for x in g.log if x[0] == 'posture'][-2:], [('posture', 1), ('posture', 2)])
    # ---- v3: one charge for all three; the hold's effects grow with it
    m4 = fresh(mscsb, src)
    g4 = m4.game
    g4.held = {0}
    g4.flags.add(0x2100001B)
    m4('gk_sm_start_main', 1)
    m4('gk_sm_start_loop', 1)
    m4.vm.g[4] = 0x2C
    for _ in range(50):
        m4('gk_sm_hold_tick')
    g4.held = set()
    m4('gk_sm_hold_loop', 1)
    g4.held = {0}
    m4.vm.g[4] = 0x2E
    m4('gk_sm_start_main', 4)
    m4('gk_sm_start_loop', 4)
    m4.vm.g[4] = 0x2F
    g4.log = []
    m4('gk_sm_hold_tick')
    fx = [x for x in g4.log if x[0] == 'effect']
    check('v3: a forward smash held 50, then a down smash: the same store (51 after its first frame)', m4.g('gk_smash'), 51)
    check('v3: the resumed hold\'s first frame: its effects at once: sparkle, flash (over his feet), the sword killed and '
          'made again on both hands (25, 24)', [(x[1], x[2]) for x in fx],
          [(0x2710, 0x1000019), (0x2710, 0x1000010), (0x2723, 0x3300007), (0x2712, 0x3300007), (0x2712, 0x3300007)])
    check('... the sword at the kept charge\'s size: 1 + 4 x 50 / 120 = 2.667 (aerial chain v1 package: the dust and sparkle '
          'at their vanilla 1)', [x[4] for x in g4.log if x[0] == 'fxsize'], [1.0, 1.0, 2.667, 2.667])
    g4.log = []
    for _ in range(69):
        m4('gk_sm_hold_tick')
    sizes = [x[4] for x in g4.log if x[0] == 'fxsize' and x[2] == 0x3300007]
    check('v3: the sword made again every 10 frames (60 - 110, both hands: 12), growing (its last: 1 + 4 x 110 / 120 = 4.667)',
          (len(sizes), sizes[-1], sizes == sorted(sizes)), (12, 4.667, True))
    check('v3: 120: full -> ready, Wait; the next up smash releases at once', (m4('gk_sm_hold_loop', 4), m4.g('gk_smash')), (1, 120))
    m4('gk_sm_start_main', 2)
    check('... automatic (1: the stored full charge)', m4.g('gk_sm_auto'), 1)
    m4.game.status_req = []
    m4('gk_sm_start_loop', 2)
    check('... released (0x33): the shared store emptied (the chain carries the full charge)', (m4.game.status_req, m4.g('gk_smash')), ([(0x33, 1)], 0))
    check('v3 effect size curve: 1 at 0, 3 at 60, 5 at 120 (linear)',
          [round(i2f(m4('gk_sm_size', v) & 0xFFFFFFFF), 3) for v in (0, 30, 60, 120)], [1.0, 2.0, 3.0, 5.0])
    # down smash out of run: the same start status (0x2E), so the same rules
    m3 = fresh(mscsb, src)
    m3.game.held = {0}
    m3.game.flags.add(0x2100001B)
    m3('gk_sm_start_main', 4)
    m3('gk_sm_start_loop', 4)
    check('a down smash (out of a run too: its start status 0x2E): charges like any', m3.game.status_req, [(0x2F, 1)])


def physics_tests(mscsb, src):
    """v2: the clones' own fall (ledge, a lower floor, max fall speed), a jump with him, a platform drop, a launch, the
    fall off the stage; his hitlag from their hits; the freeze in hitlag (the physics at delay 0: gk_delay stubbed; the
    clone delay's own tests: delay_tests)"""
    fresh = fresh_nodelay
    def start(x=0.0, y=10.0, floors=None):
        m = fresh(mscsb, src)
        g = m.game
        g.x, g.y = x, y
        if floors is not None:
            g.floors = floors
        m.setg('gk_lw_charge', 300)
        m('gk_lw_press')
        frames(m, 6)
        return m, g

    def cl(m):
        return (m.gf('gk_lx'), m.gf('gk_ly'), m.gf('gk_rx'), m.gf('gk_ry'))

    def flags(g):
        return int(g.vars.get(0x0F00031F, 0.0) - 4747000.0)
    check('v3 constants: gravity 0.18, max fall 1.85 (his fighter_param), fall-off fallback 300 frames, snap 2, hitlag min 4',
          (round(i2f(fresh(mscsb, src)('gk_gravity') & 0xFFFFFFFF), 3), round(i2f(fresh(mscsb, src)('gk_max_fall') & 0xFFFFFFFF), 3),
           fresh(mscsb, src)('gk_fall_frames'), round(i2f(fresh(mscsb, src)('gk_snap') & 0xFFFFFFFF), 3),
           fresh(mscsb, src)('gk_hitlag_min')), (0.18, 1.85, 300, 2.0, 4))
    # ---- a ledge: the stage ends at x 20 (a lower floor at -20 from 20 to 100)
    m, g = start(10.0, 10.0, [(-60.0, 20.0, 10.0), (20.0, 100.0, -20.0)])
    check('made: left at (-4, 10), right at (24, 10) (both on the floor: the right one at the edge\'s far side, its '
          'first frames)', (m.gf('gk_lx'), m.gf('gk_ly'), m.gf('gk_rx')), (-4.0, 10.0, 24.0))
    m.setgf('gk_ry', 10.0)
    m.setgf('gk_rvy', 0.0)
    m.setg('gk_rfall', 0)
    frames(m, 10)
    check('off the ledge: the right clone falls with his gravity (10 frames: 10 - 0.18 x 55 = 0.1), the left one stays on '
          'the floor', (m.gf('gk_ly'), round(m.gf('gk_ry'), 2)), (10.0, 0.1))
    check('... it plays Fall (flags 16 / 32: right 32), alive 3', flags(g) & 0x3F, 0x23)
    vmin = 0.0
    for _ in range(40):
        frames(m, 1)
        vmin = min(vmin, m.gf('gk_rvy'))
        if m.gf('gk_ry') <= -20.0 and m.gf('gk_rvy') == 0.0:
            break
    check('... its speed capped at his max fall speed (1.85), it lands on the lower floor (-20): stands, speed 0',
          (vmin, m.gf('gk_ry'), m.gf('gk_rvy')), (-1.85, -20.0, 0.0))
    frames(m, 3)
    check('... landed: no Fall flag, it plays his motion; its X still his X + 14', (flags(g) & 0x30, m.gf('gk_rx')), (0, 24.0))
    g.x = 12.0
    frames(m, 1)
    check('he walks: both clones\' X follow him (-2 / 26), their heights their own (10 / -20)', cl(m), (-2.0, 10.0, 26.0, -20.0))
    # ---- a jump with him: they copy his vertical movement from where they stand; then land on their floors
    g.situation = 2
    ys = []
    for y in (14.0, 17.0, 19.0, 15.0, 10.0):
        g.y = y
        frames(m, 1, st=0x1B)
        ys.append((m.gf('gk_ly'), m.gf('gk_ry')))
    check('he jumps (14, 17, 19, 15, 10): the left clone with him, the right one the same rise / fall from -20',
          ys, [(14.0, -16.0), (17.0, -13.0), (19.0, -11.0), (15.0, -15.0), (10.0, -20.0)])
    g.situation = 0
    frames(m, 5)
    check('he lands: both stand (10 / -20, speed 0)', (m.gf('gk_ly'), m.gf('gk_ry'), m.gf('gk_lvy'), m.gf('gk_rvy')), (10.0, -20.0, 0.0, 0.0))
    # ---- a jump onto a platform: the clones over nothing fall back down
    m, g = start(0.0, 10.0, [(-100.0, 100.0, 10.0), (-5.0, 5.0, 25.0)])
    g.situation = 2
    for y in (16.0, 21.0, 25.0, 27.0, 26.0):
        g.y = y
        frames(m, 1, st=0x1B)
    g.y, g.situation = 25.0, 0
    frames(m, 1)
    check('he jumps onto a platform (25): the clones went up with him (to 26)', (m.gf('gk_ly') > 24.0, m.gf('gk_ry') > 24.0), (True, True))
    frames(m, 20)
    check('... he stands on it, they (at -14 / 14, past its ends) fall back to the floor (10)', (m.gf('gk_ly'), m.gf('gk_ry')), (10.0, 10.0))
    # ---- a platform drop: all on a platform (30), he drops through it: they follow, not stopped by the platform
    m, g = start(0.0, 30.0, [(-100.0, 100.0, 30.0), (-1000.0, 1000.0, -50.0)])
    g.situation = 2
    for y in (29.5, 28.0, 26.0):
        g.y = y
        frames(m, 1, st=0x1D)
    check('he drops through the platform (30 -> 26): the clones follow (26)', (m.gf('gk_ly'), m.gf('gk_ry')), (26.0, 26.0))
    # ---- a launch: they stay (X too) and fall where they are; back in formation (smoke) when he is back
    m, g = start(0.0, 10.0, [(-30.0, 30.0, 10.0)])
    g.situation = 2
    for i in range(5):
        g.x, g.y = 10.0 * (i + 1), 10.0 + 6.0 * (i + 1)
        frames(m, 1, st=0x46)
    check('he is launched (x 50, y 40): the clones stay where they were, on the floor (-14 / 14, 10)', cl(m), (-14.0, 10.0, 14.0, 10.0))
    check('... standing: Wait1', g.vars.get(0x0F00031C) // 1024, 0.0)
    g.x, g.y, g.situation = 60.0, 10.0, 0
    g.floors = [(-1000.0, 1000.0, 10.0)]
    g.log = []
    frames(m, 1, st=0)
    check('he is back (60, 10): the clones back in formation (46 / 74), a smoke each',
          (cl(m), len([x for x in g.log if x[0] == 'effect' and x[2] == 0x3300006])), ((46.0, 10.0, 74.0, 10.0), 2))
    # ---- v3: the blast zone: the game removes a weapon past it without its MSC; its heartbeat stops
    m, g = start(0.0, 10.0, [])
    g.log = []
    frames(m, 4)
    g.beat = 2                                # the left clone's MSC no longer runs (removed by the game)
    frames(m, 2)
    check('v3 blast zone: the left clone\'s heartbeat (his VAR_30 bit 1) missing 2 frames: still counted', m.g('gk_alive'), 3)
    frames(m, 1)
    check('... 3 frames: gone (no log), the right one (its heartbeat on) stays',
          ([x[:3] for x in g.log if x[0] in ('article', 'battleobject')], m.g('gk_alive')), ([('article', 0x2712, 6)], 2))
    m, g = start(0.0, 10.0, [])
    g.beat = 0
    frames(m, 1)
    check('v3: just made (6 frames of grace: its MSC finds him first): no heartbeat yet is fine', m.g('gk_alive'), 3)
    g.beat = 3
    # ---- v5: a clone whose script never reports (never seen) is kept 120 frames, then dropped (reason 101 / 102 logged)
    m = fresh(mscsb, src)
    g = m.game
    g.beat = 0
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 100)
    check('v5: never-seen clones (their script not running) kept past v4\'s 9 frames (100 frames)', m.g('gk_alive'), 3)
    check('v6: ... only the clone made last (the right one: 8) flagged "being made" (v5 flagged both, and both clones '
          'took id 1 in game)', int(g.vars.get(0x0F00031F) - 4747000) & 0xC, 0x8)
    frames(m, 30)
    check('v5: past the 120-frame grace + 3 misses: both dropped, the reason in VAR_23 (101 then 102: heartbeat)',
          (m.g('gk_alive'), g.vars.get(0x0F000317)), (0, 102.0))
    m = fresh(mscsb, src)
    g = m.game
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 8)
    check('v5: seen clones: "being made" cleared', int(g.vars.get(0x0F00031F) - 4747000) & 0xC, 0)
    g.vars[0x0F000315] = 20000.0 + 2.0
    frames(m, 1)
    check('v5: a hit on the right clone: VAR_23 = 202', g.vars.get(0x0F000317), 202.0)
    # ---- the fallback: falling on their own 300 frames (no blast zone removal seen) -> gone in smoke, no log
    m, g = start(0.0, 10.0, [])
    g.log = []
    frames(m, 295)
    check('v3 fallback: nothing under them, the left clone 300 frames falling: still there', m.g('gk_alive'), 3)
    frames(m, 1)
    check('its 301st: the left one gone (article 6 removed), its smoke, no Substitution log',
          ([x for x in g.log if x[0] in ('article', 'battleobject')], len([x for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
           m.g('gk_alive')), ([('article', 0x2712, 6)], 1, 2))
    frames(m, 3)
    check('the right one (made 3 frames later) 3 frames later; the ability goes on',
          ([x for x in g.log if x[0] in ('article', 'battleobject')][-1], m.g('gk_alive'), m.g('gk_ability') > 0),
          (('article', 0x2712, 7), 0, True))
    # ---- v13: a clone falling on its own whose heartbeat stops (the game removed it past the blast zone: the user's
    # v12 E_sway "fell off of the edge", logged 101): 400 + id, its smoke
    m, g = start(0.0, 10.0, [])
    frames(m, 10)
    g.log = []
    g.beat = 2
    frames(m, 3)
    check('v13: the left clone falling (10 frames) and its heartbeat gone 3 frames: removed with its smoke, reason 401 '
          '(fell off), not 101', ([x[:3] for x in g.log if x[0] == 'article'], len([x for x in g.log if x[0] == 'effect'
          and x[2] == 0x3300006]), g.vars.get(0x0F000317), m.g('gk_alive')), ([('article', 0x2712, 6)], 1, 401.0, 2))
    m, g = start(0.0, 10.0, [(-1000.0, 1000.0, 10.0)])
    frames(m, 10)
    g.beat = 2
    frames(m, 3)
    check('v13: ... standing on the floor when its heartbeat stops: 101 as before', g.vars.get(0x0F000317), 101.0)
    # ---- v3: walls: a clone stops against one (its offset gives way), and goes back to its offset when free
    m, g = start(0.0, 10.0, [(-1000.0, 1000.0, 10.0)])
    g.walls = [(20.0, 0.0, 40.0)]
    for x in (2.0, 4.0, 6.0, 8.0, 10.0):
        g.x = x
        frames(m, 1)
    check('v3 wall at x 20: he walks to 10, the right clone (offset 14) stops against it (20 - 3), the left one follows (-4)',
          (m.gf('gk_rx'), m.gf('gk_lx'), m.gf('gk_off_r')), (17.0, -4.0, 14.0))
    g.x = -2.0
    frames(m, 1)
    check('... he walks back (-2): the right clone at its offset again (12)', m.gf('gk_rx'), 12.0)
    g.x = 10.0
    for _ in range(2):
        frames(m, 1)
    x0 = g.x
    g.press, g.stick = {1}, (0.8, -0.8)
    m('gekkouga_frame')
    check('v3 swap with the right clone held by the wall (17): him to 17, it to his place (10), the left one stays (-4)',
          (g.x, m.gf('gk_rx'), m.gf('gk_lx'), m.gf('gk_off_r'), m.gf('gk_off_l')), (17.0, 10.0, -4.0, -7.0, -21.0))
    m, g = start(0.0, 10.0, [(-1000.0, 1000.0, 10.0)])
    g.walls = [(-20.0, 0.0, 40.0)]
    g.x = -10.0
    frames(m, 1)
    check('v3: a wall on the left (-20): the left clone held at -17', m.gf('gk_lx'), -17.0)
    g.walls = [(30.0, 30.0, 60.0)]
    g.x = 20.0
    frames(m, 1)
    check('v3: a wall above its test height (30 - 60) doesn\'t stop it (34)', m.gf('gk_rx'), 34.0)
    # ---- v3: ceilings: a clone jumping with him stops under one
    m, g = start(0.0, 10.0, [(-1000.0, 1000.0, 10.0)])
    g.ceilings = [(10.0, 20.0, 35.0)]
    g.situation = 2
    for y in (15.0, 20.0, 25.0, 30.0):
        g.y = y
        frames(m, 1, st=0x1B)
    check('v3 ceiling at 35 over the right clone (x 14): he rises to 30, it stops at 35 - 15 = 20; the left one rises with him',
          (m.gf('gk_ry'), m.gf('gk_ly')), (20.0, 30.0))
    for y in (27.0, 22.0, 15.0, 10.0):
        g.y = y
        frames(m, 1, st=0x1B)
    g.situation = 0
    frames(m, 6)
    check('... both come back down to the floor (10)', (m.gf('gk_ry'), m.gf('gk_ly')), (10.0, 10.0))
    # ---- v3: slopes / steps: standing, it follows the floor under its new X, up or down
    m, g = start(0.0, 10.0, [(-1000.0, 15.0, 10.0), (15.0, 1000.0, 14.0)])
    frames(m, 1)
    check('v3: the right clone at x 14 on the floor 10', m.gf('gk_ry'), 10.0)
    g.x = 4.0
    frames(m, 1)
    check('v3: a step up of 4 (x 18 on the floor 14; reach 2 + 1.4 x 4 = 7.6): it steps up', m.gf('gk_ry'), 14.0)
    g.x = 0.0
    frames(m, 1)
    check('v3: and down again (no fall)', (m.gf('gk_ry'), m.g('gk_rfall')), (10.0, 0))
    m, g = start(0.0, 10.0, [(-1000.0, 15.0, 10.0), (15.0, 1000.0, 40.0)])
    g.walls = [(15.0, 10.0, 40.0)]
    g.x = 4.0
    frames(m, 1)
    check('v3: a cliff face (a wall, 30 high) is not a step: it stays against it on its floor', (m.gf('gk_rx'), m.gf('gk_ry')), (12.0, 10.0))
    # ---- a clone's hit lands: his hitlag (the biggest victim's), once; the freeze
    m, g = start(0.0, 10.0, [(-10.0, 10.0, 10.0)])
    g.vars[0x0F000043 + 8 * 4] = 1.0          # slot 2 in hitstop, 9 frames
    g.vars[0x0F000044 + 8 * 4] = 9.0
    g.vars[0x0F000043 + 8 * 7] = 1.0          # slot 5 in hitstop, 12
    g.vars[0x0F000044 + 8 * 7] = 12.0
    g.vars[0x0F000044 + 8 * 8] = 20.0         # slot 6: its last hit's 20, not in hitstop now
    g.vars[0x0F000316] = 1.0
    g.log = []
    ry0 = m.gf('gk_ry')
    frames(m, 1)
    check('a clone\'s hit landed (VAR_22 = 1, the executable): his hitlag = the biggest hitstop running (12), VAR_22 cleared',
          ([x for x in g.log if x[0] == 'hitlag'], g.vars.get(0x0F000316)), ([('hitlag', 12)], 0.0))
    check('... the channel\'s rate 0 (the clones freeze with him), the falling clone frozen (its Y as it was)',
          (g.vars.get(0x0F00031D), m.gf('gk_ry')), (0.0, ry0))
    g.vars[0x0F000316] = 1.0
    g.log = []
    frames(m, 1)
    check('another clone hit (the other clone, or the same frame\'s second) while in hitlag: no more hitlag (not stacked), cleared',
          ([x for x in g.log if x[0] == 'hitlag'], g.vars.get(0x0F000316)), ([], 0.0))
    g.hitlag = 0
    for k in (4, 7):
        g.vars[0x0F000043 + 8 * k] = 0.0
    g.vars[0x0F000316] = 1.0
    g.log = []
    frames(m, 1)
    check('no victim in hitstop found (a shield, ...): the minimum (4)', [x for x in g.log if x[0] == 'hitlag'], [('hitlag', 4)])
    g.hitlag = 0
    frames(m, 2)
    check('out of hitlag: the falling clone falls again, his rate back', (m.gf('gk_ry') < ry0, g.vars.get(0x0F00031D)), (True, 1.0))
    # ---- the clone hit's log where the clone stands (falling: its own Y)
    m.setgf('gk_ry', -20.0)
    m.setgf('gk_ly', -20.0)
    alive = m.g('gk_alive')
    g.vars[0x0F000315] = 20000.0 + 2.0
    g.log = []
    frames(m, 1)
    check('v3: a hit on the right clone 30 below him (its own hurtbox, anywhere): it is gone, the log at its place',
          (m.g('gk_alive'), [x[:4] for x in g.log if x[0] == 'battleobject']), (alive & 1, [('battleobject', 0x3F7, m.gf('gk_rx'), -20.0)]))
    # ---- a swap to a clone below him: he goes to its X and Y
    m, g = start(0.0, 10.0, [(-30.0, 10.0, 10.0), (10.0, 60.0, -10.0)])
    frames(m, 20)
    x0 = g.x
    g.press, g.stick = {1}, (0.8, -0.8)
    m('gekkouga_frame')
    check('v2 swap with the right clone standing lower (14, -10): him to (14, -10), it to his place (0, 10)',
          (g.x, g.y, m.gf('gk_rx'), m.gf('gk_ry')), (14.0, -10.0, 0.0, 10.0))


def clone_tests(mscsb, src):
    m = stub_fn(MSC(mscsb, src), 'cl_delay', 0)     # the playback at delay 0 (the delay: clone_delay_tests)
    g = m.game
    sh = {}

    def shared(slot, k, v):
        sh[0x0F000340 + 8 * (slot - 1) + k] = v

    pos = {}

    def slotpos(slot, x, y, lr):
        pos[0x0F000020 + 4 * (slot - 1)] = x
        pos[0x0F000020 + 4 * (slot - 1) + 1] = y
        pos[0x0F000020 + 4 * (slot - 1) + 3] = lr

    def sysf(sid, a, old=g.sys):
        if sid == 0x17 and a[0] == 0:
            if a[1] in sh:
                return f2i(sh[a[1]])
            if a[1] in pos:
                return f2i(pos[a[1]])
        if sid == 0x12 and a[0] == 0x1:
            g.log.append(('motion', a[1], fv(a[2]), fv(a[3])))
            return 0
        if sid == 0x12 and a[0] == 0x2713:
            g.log.append(('setframe', fv(a[1])))
            return 0
        if sid == 0x14 and a[0] == 0:
            g.log.append(('lr', fv(a[1])))
            g.lr = fv(a[1])
            return 0
        return old(sid, a)
    g.sys = sysf
    # two Greninjas with clones: slot 2 at x 100, slot 5 at x -40 (both with the magic 4747000 + flags); the clone
    # made at 98, slot 2's right clone being made (flags 3 + 8)
    for s_, x in ((2, 100.0), (5, -40.0)):
        shared(s_, 7, 4747000.0 + 3 + 8)
        slotpos(s_, x, 0.0, -1.0)
    shared(2, 0, 86.0)
    shared(2, 1, 0.0)
    shared(2, 2, 114.0)
    shared(2, 3, -6.5)
    shared(2, 6, 0.0)
    shared(2, 4, 97280 + 5.0)
    shared(2, 5, 1.0)
    g.x, g.y, g.lr = 98.0, 0.0, 1.0
    m('cl_frame')
    check('the clone finds him (slot 2, the nearest with the magic), which clone from his "being made" bit (8: the right one)',
          (m.g('cl_slot'), m.g('cl_id')), (2, 2))
    check('v2: its place his MSC\'s (VAR_26 / 27: 114, -6.5: it stands / falls there)', (g.x, g.y), (114.0, -6.5))
    check('v2: its VAR_0 = his slot (the executable\'s hit method gives him its hits\' hitlag)', g.vars.get(0x0F000300), 2.0)
    check('v3: its VAR_1 = which clone (2: the executable reports its hurtbox\'s hits with it)', g.vars.get(0x0F000301), 2.0)
    check('v3: its heartbeat: bit 2 written into his VAR_30 (SLOT2_SHARED_6)', g.vars.get(0x0F000340 + 8 + 6), 2.0)
    check('faces his way (-1, then the model turned)', [x for x in g.log if x[0] in ('lr', 'posture')][-2:], [('lr', -1.0), ('posture', 2)])
    check('his motion 0x5F (VAR_28 = kind x 1024 + frame) from his frame 5 at his rate', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 5.0, 1.0)])
    g.log = []
    shared(2, 4, 97280 + 6.0)
    shared(2, 7, 4747000.0 + 3)
    g.frame = 6.0
    m('cl_frame')
    check('the next frame: the same motion, his rate (no restart); the bit gone, it is still the right one',
          ([x for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'rate'], m.g('cl_id')), ([], [('rate', 1.0)], 2))
    shared(2, 4, 97280 + 9.0)
    g.frame = 6.5
    g.log = []
    m('cl_frame')
    check('behind him (its own hitlag): back on his frame', [x for x in g.log if x[0] == 'setframe'], [('setframe', 9.0)])
    shared(2, 5, 0.0)
    g.log = []
    m('cl_frame')
    check('v2: his hitlag (rate 0): it freezes', [x for x in g.log if x[0] == 'rate'], [('rate', 0.0)])
    shared(2, 5, 1.0)
    shared(2, 4, 97280 + 0.0)
    g.log = []
    m('cl_frame')
    check('his frame went back (a restart): the motion again from his frame', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 0.0, 1.0)])
    shared(2, 7, 4747000.0 + 3 + 0x20)
    g.log = []
    m('cl_frame')
    check('v2: falling on its own (flag 32, the right one): Fall (0x24) from 0, its own loop',
          [x for x in g.log if x[0] == 'motion'], [('motion', 0x24, 0.0, 1.0)])
    g.log = []
    m('cl_frame')
    check('... next frame: no restart', [x for x in g.log if x[0] == 'motion'], [])
    shared(2, 7, 4747000.0 + 3 + 0x10)
    g.log = []
    m('cl_frame')
    check('... the other clone\'s fall flag (16): not this one, his motion again', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 0.0, 1.0)])
    shared(2, 4, 0.0)
    g.log = []
    m('cl_frame')
    check('a new motion (Wait1)', [x for x in g.log if x[0] == 'motion'], [('motion', 0, 0.0, 1.0)])
    shared(2, 7, 4747000.0 + 1)
    g.log = []
    m('cl_frame')
    check('not alive (alive 1: it is 2): hidden', [x for x in g.log if x[0] == 'visible'], [('visible', 0)])
    shared(2, 7, 4747000.0 + 3)
    g.log = []
    m('cl_frame')
    check('alive again: shown', [x for x in g.log if x[0] == 'visible'], [('visible', 1)])
    shared(2, 7, 0.0)
    g.log = []
    m('cl_frame')
    check('his channel closed: hidden', [x for x in g.log if x[0] == 'visible'], [('visible', 0)])
    m2 = MSC(mscsb, src)
    m2.game.sys = lambda sid, a: 0
    m2('cl_frame')
    check('nobody with the magic: not found, hidden', m2.g('cl_slot'), 0)
    # v2: made before his channel says which (no "being made" bit yet): it waits (hidden), then takes it
    m3 = stub_fn(MSC(mscsb, src), 'cl_delay', 0)
    g3 = m3.game
    sh.clear()
    shared(2, 7, 4747000.0 + 1)
    shared(2, 0, 86.0)
    g3.sys = lambda sid, a, f=sysf: f(sid, a)
    m3.game.sys = g.sys
    g.log = []
    m3('cl_frame')
    check('v2: no "being made" bit: no id yet (waits)', (m3.g('cl_slot'), m3.g('cl_id')), (0, 0))
    check('v8: ... hidden while it waits', [x for x in g.log if x[0] == 'visible'], [('visible', 0)])
    shared(2, 7, 4747000.0 + 1 + 4)
    g.log = []
    m3('cl_frame')
    check('v2: ... the left bit (4): the left one, at VAR_24 / 25', (m3.g('cl_slot'), m3.g('cl_id'), g.x), (2, 1, 86.0))
    check('v8: ... and shown again (v1 - v7 never showed a clone that had waited: the invisible clones)',
          [x for x in g.log if x[0] == 'visible'], [('visible', 1)])
    g.log = []
    for _ in range(3):
        m3('cl_frame')
    check('v8: ... once (no VisibilityModule call while nothing changes)', [x for x in g.log if x[0] == 'visible'], [])


def aerial_chain_tests(mscsb, src):
    """aerial chain v1 (README "Aerial chain v1"): an aerial that hits an opponent (AttackModule 0x2727 kind 2; a shield
    doesn't count; a clone's hit does) can be cancelled from the frame after the hit into a different aerial (the game's
    air attack input, ControlModule 0x10); each once a chain; anything but an aerial (landing) ends it; then the smash
    charge's dust / sparkle at size 1 at every charge level"""
    m = fresh(mscsb, src)
    g = m.game
    body = open(src).read()
    f82 = body[body.index('void func_2382()'):body.index('void func_2384()')]
    check('aerial chain: the aerial status (0x34) start notes the aerial after func_314 picked its motion; its loop tries '
          'a chain first after func_56\'s own interrupts', (f82.index('func_314();') < f82.index('gk_ac_start();'),
          f82.index('if (func_56())') < f82.index('if (gk_ac_try())') < f82.index('StopModule(0x1) == 0')), (True, True))
    names = {0x68: 1, 0x69: 2, 0x6A: 3, 0x6B: 4, 0x6C: 5}

    def start(motion):
        m.vm.g[4] = 0x34
        g.ints[0x11000002] = motion
        g.log = []
        m('gk_ac_start')

    def tick(hit=0, kind=0, cmd=0x1, air=2):
        """one frame of the aerial's loop: what its attack hit so far, the input's air attack"""
        g.atk_hit = hit
        g.air_kind = kind
        m.vm.g[18] = air
        m.vm.g[24] = cmd
        g.status_req = []
        return m('gk_ac_try'), list(g.status_req)

    start(0x69)
    check('a forward air starts a chain: used {forward} (bit 1 << 2), kind 2, its hits since it started cleared',
          (m.g('gk_ac_used'), m.g('gk_ac_kind'), m.g('gk_ac_hit'), [x for x in g.log if x[0] == 'atk_clear']), (4, 2, 0, [('atk_clear',)]))
    check('a whiff: an aerial input (neutral) does nothing, 5 frames', [tick(0, 1) for _ in range(5)], [(0, [])] * 5)
    check('shielded (kind 4 only): no window', [tick(4, 1) for _ in range(3)], [(0, [])] * 3)
    check('the hit (kind 2) on this frame: no cancel yet (from the next frame)', (tick(2, 1), m.g('gk_ac_hit')), ((0, []), 1))
    g.hitlag = 3
    check('... the next frame in hitlag: still none', tick(2, 1), (0, []))
    g.hitlag = 0
    check('... out of hitlag, the same aerial again (forward, used): refused', tick(2, 2), (0, []))
    check('... no attack input (command bit 1 off): none', tick(2, 1, cmd=0), (0, []))
    check('... on the ground (situation 0): none', tick(2, 1, air=0), (0, []))
    check('... a neutral air: cancelled into the aerial status again (0x34) as a chain', (tick(2, 1), m.g('gk_ac_req')), ((1, [(0x34, 1)]), 1))
    start(0x68)
    check('the neutral air\'s start: the chain kept (used forward + neutral: 4 + 2), its hit from 0', (m.g('gk_ac_used'), m.g('gk_ac_kind'),
          m.g('gk_ac_hit'), m.g('gk_ac_req')), (6, 1, 0, 0))
    check('... no hit yet: no chain (even with the input)', tick(0, 3), (0, []))
    tick(2, 0)
    check('... hit: forward / neutral (and 0: func_311\'s neutral) refused, back accepted', (tick(2, 2), tick(2, 1), tick(2, 0), tick(2, 3)),
          ((0, []), (0, []), (0, []), (1, [(0x34, 1)])))
    start(0x6A)
    tick(2, 0)
    tick(2, 4)
    start(0x6B)
    tick(2, 0)
    tick(2, 5)
    start(0x6C)
    check('forward, neutral, back, up, down: all five in the chain (2 + 4 + 8 + 16 + 32)', m.g('gk_ac_used'), 62)
    tick(2, 0)
    check('... the down air hits: no aerial left (every input refused)', [tick(2, k) for k in range(0, 6)], [(0, [])] * 6)
    g.ints[0x11000002] = 0x6C
    m.setg('gk_ac_hit', 2)
    m.vm.g[4] = 0x34
    m.game.vars[0x0F00031E] = 0.0
    m('gekkouga_frame')
    d = int(g.vars.get(0x0F000314, 0.0))
    check('diag (his VAR_20 from 256): the aerial (5 x 256), hit seen (2048), window open (4096), used 62 x 8192',
          (d >> 8 & 7, d >> 11 & 1, d >> 12 & 1, d >> 13), (5, 1, 1, 62))
    frames(m, 1, st=0x17)
    check('landing (any status but 0x34): the chain ends', (m.g('gk_ac_used'), m.g('gk_ac_kind'), m.g('gk_ac_hit'), m.g('gk_ac_req')), (0, 0, 0, 0))
    start(0x6C)
    check('... the next aerial (down) a new chain: only itself used', m.g('gk_ac_used'), 32)
    tick(2, 0)
    m.setg('gk_ac_req', 1)
    frames(m, 1, st=0x1B)
    start(0x6B)
    check('a jump (not an aerial) ends it too, even with a chain cancel asked: the next aerial a new chain', m.g('gk_ac_used'), 16)
    # a clone's copy of the aerial landing (the exe's VAR_22) opens the window too
    start(0x6A)
    tick(0, 0)
    g.vars[0x0F000316] = 1.0
    m('gk_clone_hitlag')
    check('a clone\'s hit (his VAR_22) during his aerial: hit seen, VAR_22 cleared', (m.g('gk_ac_hit'), g.vars.get(0x0F000316)), (1, 0.0))
    g.hitlag = 0
    check('... the next frame: a chain (neutral)', tick(0, 1), (1, [(0x34, 1)]))
    m.vm.g[4] = 0x2C
    m.setg('gk_ac_hit', 0)
    g.vars[0x0F000316] = 1.0
    m('gk_clone_hitlag')
    check('... a clone\'s hit while he is not in an aerial: nothing', m.g('gk_ac_hit'), 0)
    check('the hit kinds read: 2 (a hurtbox; 4 a shield not counted)', m('gk_ac_hit_kinds'), 2)
    # ---- the smash charge's dust / sparkle at size 1 at every charge level; the water sword still the charge's size
    bad = []
    for t in (0x1, 0x2, 0x4):
        for v in range(0, 121, 10):
            g.log = []
            m('gk_sm_fx', t, v, 1)
            sz = [(x[2], x[4]) for x in g.log if x[0] == 'fxsize']
            want_sw = round(i2f(m('gk_sm_size', v) & 0xFFFFFFFF), 3)
            ds = [z for i_, z in sz if i_ in (0x1000019, 0x1000010)]
            sw = [z for i_, z in sz if i_ == 0x3300007]
            if ds != [1.0, 1.0] or not sw or any(z != want_sw for z in sw):
                bad.append((t, v, sz))
    check('smash charge (forward / up / down, charge 0 - 120 every 10): the dust (0x1000019) and sparkle (0x1000010) at '
          'size 1, the water sword at the charge\'s (1 - 5)', bad, [])


def delay_tests(mscsb, src):
    """clone delay (README "Clone delay"): his side: each clone's place follows his X / vertical movement from gk_delay(id)
    of his frames back (left 1, right 2); its first frames his place now (held); a swap / a return to formation starts the
    history over; his hitlag frames are no frames"""
    def start(x=0.0, y=10.0, floors=None):
        m = fresh(mscsb, src)
        g = m.game
        g.x, g.y = x, y
        if floors is not None:
            g.floors = floors
        m.setg('gk_lw_charge', 300)
        m('gk_lw_press')
        return m, g
    m, g = start()
    check('clone delay: the left clone 1 frame, the right one 2', (m('gk_delay', 1), m('gk_delay', 2)), (1, 2))
    seen = []
    for t in range(12):
        g.x = 2.0 * t
        frames(m, 1)
        seen.append((g.x, m.gf('gk_lx') + 14.0 if m.g('gk_alive') & 1 else None, m.gf('gk_rx') - 14.0 if m.g('gk_alive') & 2 else None))
    check('he walks 2 a frame from the start (the clones made on its 2nd / 5th frame): each clone\'s X - its offset: made at '
          'his X then, held for its delay, then his X 1 (left) / 2 (right) frames back',
          seen, [(0.0, None, None), (2.0, 2.0, None), (4.0, 2.0, None), (6.0, 4.0, None), (8.0, 6.0, 8.0), (10.0, 8.0, 8.0),
                 (12.0, 10.0, 8.0), (14.0, 12.0, 10.0), (16.0, 14.0, 12.0), (18.0, 16.0, 14.0), (20.0, 18.0, 16.0),
                 (22.0, 20.0, 18.0)])
    # his jump: the clones copy his vertical movement 1 / 2 frames late
    m, g = start()
    frames(m, 10)
    g.situation = 2
    ys = []
    for y in (14.0, 17.0, 19.0, 15.0, 10.0, 10.0, 10.0):
        g.y = y
        frames(m, 1, st=0x1B)
        ys.append((m.gf('gk_ly'), m.gf('gk_ry')))
    check('he jumps (14, 17, 19, 15, 10): the left clone 1 frame late, the right one 2',
          ys, [(10.0, 10.0), (14.0, 10.0), (17.0, 14.0), (19.0, 17.0), (15.0, 19.0), (10.0, 15.0), (10.0, 10.0)])
    g.situation = 0
    # his hitlag: no history: they freeze and go on in step
    m, g = start()
    frames(m, 10)
    for t in range(3):
        g.x = 2.0 * (t + 1)
        frames(m, 1)
    g.hitlag = 5
    for _ in range(3):
        frames(m, 1)
    fr = (m.gf('gk_lx') + 14.0, m.gf('gk_rx') - 14.0)
    fl = int(g.vars.get(0x0F00031F) - 4747000.0)
    g.hitlag = 0
    out = []
    for t in range(3):
        g.x = 8.0 + 2.0 * t
        frames(m, 1)
        out.append((m.gf('gk_lx') + 14.0, m.gf('gk_rx') - 14.0))
    check('he walks 2, 4, 6, then 3 frames of hitlag: the clones stay at 4 / 2 (frozen); then 8, 10, 12: 6 / 4, 8 / 6, '
          '10 / 8 (his frozen frames skipped)', (fr, out), ((4.0, 2.0), [(6.0, 4.0), (8.0, 6.0), (10.0, 8.0)]))
    check('... the channel\'s flag 64 while he was frozen (their playback pauses), off after',
          (fl & 0x40, int(g.vars.get(0x0F00031F) - 4747000.0) & 0x40), (0x40, 0))
    # a swap: the history starts over (his old places would put the clones off by the swap's move)
    m, g = start()
    frames(m, 10)
    for t in range(4):
        g.x = 2.0 * (t + 1)
        frames(m, 1)
    lx0 = m.gf('gk_lx')
    g.press, g.stick = {1}, (0.8, -0.8)
    m('gekkouga_frame')
    sw = (g.x, m.gf('gk_rx'), m.gf('gk_lx'), m.g('gk_hn'))
    check('swap with the right clone (at 4 + 14 = 18: 2 frames late) while he is at 8: him to 18, it to his place (8), '
          'the left one at his place + its offset (8 - 14: the history started over, his place now), 1 frame of history each',
          sw, (18.0, 8.0, -6.0, 1 + 4))
    check('... (the left one was at %g: 6 - 14)' % lx0, lx0, -8.0)
    out = []
    for t in range(3):
        g.x = 18.0 + 2.0 * (t + 1)
        frames(m, 1)
        out.append((m.gf('gk_lx'), m.gf('gk_rx')))
    check('... he walks on (20, 22, 24): the left one (offset -24) 1 frame late from 18, the right one (offset -10) held at '
          '8 for 2 frames, then 2 late', out, [(-6.0, 8.0), (-4.0, 8.0), (-2.0, 10.0)])
    # back in formation after a launch: the history starts over (his place now)
    m, g = start(0.0, 10.0, [(-30.0, 30.0, 10.0)])
    frames(m, 10)
    g.situation = 2
    for i in range(3):
        g.x, g.y = 10.0 * (i + 1), 10.0 + 6.0 * (i + 1)
        frames(m, 1, st=0x46)
    g.x, g.y, g.situation = 60.0, 10.0, 0
    g.floors = [(-1000.0, 1000.0, 10.0)]
    frames(m, 1, st=0)
    check('back in formation after a launch (60): at his place now (46 / 74), not his launch\'s places',
          (m.gf('gk_lx'), m.gf('gk_rx'), m.g('gk_hn')), (46.0, 74.0, 1 + 4))

def clone_delay_tests(mscsb, src):
    """clone delay, the clone's side (weapons/clone.c): it plays his channel's motion / frame / rate / facing from
    cl_delay() of his frames back (left 1, right 2); at first his state now, held while its history fills; his frozen
    frames (flag 64) kept out of it, its rate 0 then"""
    def make(cid):
        m = MSC(mscsb, src)
        g = m.game
        sh, pos = {}, {}

        def sysf(sid, a, old=g.sys):
            if sid == 0x17 and a[0] == 0:
                if a[1] in sh:
                    return f2i(sh[a[1]])
                if a[1] in pos:
                    return f2i(pos[a[1]])
            if sid == 0x12 and a[0] == 0x1:
                g.log.append(('motion', a[1], fv(a[2]), fv(a[3])))
                return 0
            if sid == 0x12 and a[0] == 0x2713:
                g.log.append(('setframe', fv(a[1])))
                return 0
            if sid == 0x14 and a[0] == 0:
                g.log.append(('lr', fv(a[1])))
                g.lr = fv(a[1])
                return 0
            return old(sid, a)
        g.sys = sysf
        base = 0x0F000340 + 8

        def feed(kind, frame=0.0, rate=1.0, lr=1.0, flags=3):
            sh[base + 4] = kind * 1024 + frame
            sh[base + 5] = rate
            sh[base + 7] = 4747000.0 + flags
            pos[0x0F000020 + 4] = 100.0
            pos[0x0F000020 + 4 + 3] = lr
            g.log = []
            m('cl_frame')
            return [x for x in g.log if x[0] in ('motion', 'rate', 'lr')]
        sh[base + 0], sh[base + 2] = 86.0, 114.0
        g.x, g.y, g.lr = 98.0, 0.0, 1.0
        feed(0x10, flags=3 + 4 * cid)                 # found, its id from the "being made" bit
        return m, g, feed

    m, g, feed = make(1)
    check('clone delay: cl_delay = its id (the left clone 1, the right one 2)', (m.g('cl_id'), m('cl_delay')), (1, 1))
    m, g, feed = make(2)
    check('... (the right one: 2)', (m.g('cl_id'), m('cl_delay')), (2, 2))
    for cid in (1, 2):
        m, g, feed = make(cid)
        played = [0x10]                               # its first frame: his motion now
        for k in (0x11, 0x12, 0x13, 0x14, 0x15):
            played.append(([x[1] for x in feed(k) if x[0] == 'motion'] or ['-'])[0])
        want = [0x10, '-', 0x11, 0x12, 0x13, 0x14] if cid == 1 else [0x10, '-', '-', 0x11, 0x12, 0x13]
        check('the %s clone: his motions 0x10 (its first frame: now), 0x11 ... 0x15 one a frame: it plays %s (- none new: '
              'held while its history fills), then %d frame%s late' % ('left' if cid == 1 else 'right', ' '.join(
                  x if x == '-' else '0x%X' % x for x in want), cid, 's' if cid > 1 else ''), played, want)
    m, g, feed = make(2)
    for f in (1.0, 2.0, 3.0):
        feed(0x10, f, 1.0)
    got = []
    for f, lr in ((4.0, -1.0), (5.0, -1.0), (6.0, -1.0)):
        got.append([x for x in feed(0x10, f, 1.0, lr) if x[0] in ('lr',)])
    check('the right clone: his facing (turned at his frame 4) 2 frames late', got, [[], [], [('lr', -1.0)]])
    # his frozen frames: no history, rate 0
    m, g, feed = make(1)
    feed(0x20, 0.0)
    feed(0x20, 1.0)
    fz = [feed(0x21, 0.0, 0.0, flags=3 + 64) for _ in range(3)]
    check('he is frozen (flag 64; his rate 0, a new motion that frame): the left clone pauses where it is (rate 0, '
          'still 0x20), nothing kept', fz, [[('rate', 0.0)]] * 3)
    out = [feed(0x22, 0.0) for _ in range(2)]
    check('... unfrozen (0x22): his frozen frame never played: 0x20 at rate 1, then 0x22',
          out, [[('rate', 1.0)], [('motion', 0x22, 0.0, 1.0)]])
    m, g, feed = make(2)
    feed(0x30, 0.0)
    feed(0x31, 0.0, flags=1)
    check('not alive (its bit gone): hidden, its history dropped (alive again: his motion now)',
          [x[1] for x in feed(0x32, 0.0) if x[0] == 'motion'], [0x32])

def clone_fx_tests(mscsb, src, out):
    """clone fixes v1: the clone ends its following effects (EffectModule 0x2D (0): a fade) on a new motion kind, not on a
    restart; its effect.bin has every motion's effects his has (conditions' True branches), up air's twist and the grabs'"""
    m = stub_fn(MSC(mscsb, src), 'cl_delay', 0)
    g = m.game
    sh, pos = {}, {}

    def sysf(sid, a, old=g.sys):
        if sid == 0x17 and a[0] == 0:
            if a[1] in sh:
                return f2i(sh[a[1]])
            if a[1] in pos:
                return f2i(pos[a[1]])
        if sid == 0x12 and a[0] == 0x1:
            g.log.append(('motion', a[1]))
            return 0
        if sid == 0x1C:
            g.log.append(('fx', a[0]) + tuple(a[1:2]))
            return 0
        return old(sid, a)
    g.sys = sysf
    base = 0x0F000340 + 8
    sh[base + 0], sh[base + 2] = 86.0, 114.0
    g.x, g.y = 98.0, 0.0

    def feed(kind, frame, flags=3):
        sh[base + 4] = kind * 1024 + frame
        sh[base + 5] = 1.0
        sh[base + 7] = 4747000.0 + flags
        pos[0x0F000020 + 4 + 3] = 1.0
        g.log = []
        m('cl_frame')
        return [x for x in g.log if x[0] in ('motion', 'fx')]
    feed(0x62, 0.0, 3 + 8)                         # made during his up smash hold (0x62)
    seq = []
    for k, f in ((0x62, 1.0), (0x62, 2.0), (0x63, 0.0), (0x63, 1.0), (0x63, 0.0), (0x1B, 0.0), (0x1B, 1.0)):
        seq.append(feed(k, f))
    check('clone fixes v1: the clone in his smash hold (0x62), then his up smash (0x63), its restart, a jump (0x1B): its '
          'following effects ended (EffectModule 0x2D (0): a fade) before each new move, not on a restart or within a move',
          seq, [[], [], [('fx', 0x2D, 0), ('motion', 0x63)], [], [('motion', 0x63)], [('fx', 0x2D, 0), ('motion', 0x1B)], []])
    g.log = []
    feed(0x1B, 2.0, 3 + 0x20)
    check('clone fixes v1: ... falling on its own (Fall): ended too', [x for x in g.log if x[0] in ('motion', 'fx')],
          [('fx', 0x2D, 0), ('motion', 0x24)])
    # its effect.bin
    O = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    pe = acmd.ACMDFile.load(os.path.join(O, 'body', 'effect.bin'))
    ce = acmd.ACMDFile.load(os.path.join(O, 'weapon', 'clone', 'effect.bin'))
    req = lambda cmds: [(c.name, int(c.params[0])) for c in cmds if c.name in GB.CLONE_EFFECT and   # noqa: E731
                        c.name not in ('FRAME', 'WAIT', 'Script_End')]
    names = ('attackairhi', 'catch', 'catchdash', 'catchturn', 'attackairlw', 'attackairf', 'attackairb', 'attackhi4')
    got = {n: req(ce.scripts.get(zlib.crc32(n.encode()), [])) for n in names}
    want = {n: req(GB.flatten(pe.scripts[zlib.crc32(n.encode())])) for n in names}
    check('clone fixes v1: the clone\'s effect scripts request his effects (up air\'s twist Graphic_Effect5 0x1000023, the '
          'grabs\' 0x3300015, his conditions\' True branches): %s' % ', '.join(names), got, want)
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone', 'c00')
    bm = GB.bone_map(open(os.path.join(mdl, 'model.jtb'), 'rb').read(), os.path.join(mdl, 'model.vbn'))

    def mappable(c):
        try:
            for nm in ('Bone', 'Bone1', 'Bone2', 'Bone3'):
                if nm in c.info['syntax']:
                    bm(int(c.params[c.info['syntax'].index(nm)]))
            return True
        except (IndexError, AssertionError):
            return False
    bad = []
    for crc, cmds in ce.scripts.items():
        if crc not in pe.scripts:
            bad.append((hex(crc), 'not his'))
            continue
        if req(cmds) != req([c for c in GB.flatten(pe.scripts[crc]) if mappable(c)]):
            bad.append(hex(crc))
    check('clone fixes v1: every clone effect script (%d) requests his own effects in his order (the joints remapped; '
          'a request on a joint past his model.jtb tables left out)' %
          len(ce.scripts), bad, [])
    check('clone fixes v1: at least the motions his scripts give effects without loops / calls (%d)' % len(ce.scripts),
          len(ce.scripts) >= 90, True)

def ground_move_tests(mscsb, src, out):
    """clone fixes v2 (the user: the clones "follow grounded movement incorrectly", "clip back to a set position
    constantly"): his walk / dash / run / turnaround / dash-turn / skid at his own speeds (fighter_param: walk 1.43, dash
    1.6, run 2.08): each clone at his X 1 / 2 frames back + its offset (world: the left one always left), never a jump
    over 1.5x his top speed; the cause was the clone's motions' TransN movement (its model ran ahead and snapped back):
    the clone's main.pac has none; the diag line"""
    import omo as O
    m = fresh(mscsb, src)
    g = m.game
    g.x, g.y = 0.0, 10.0
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 10)
    xs, lr = [], []
    v, x = 0.0, 0.0
    plan = ([1.43] * 20 + [1.6] * 10 + [2.08] * 30 + [1.2, 0.6, 0.0, -0.6, -1.2] + [-1.6] * 8 + [-2.08] * 20 +
            [-1.5, -1.0, -0.5, 0.0] + [1.6] * 5 + [-1.6] * 5 + [2.08] * 10 + [1.4, 0.8, 0.3, 0.0])   # walk, dash, run,
    for v in plan:                        # turnaround, run back, skid, dash-turn twice, run, skid
        x += v
        g.x = round(x, 3)
        g.lr = 1.0 if v >= 0 else -1.0
        frames(m, 1)
        xs.append((g.x, m.gf('gk_lx'), m.gf('gk_rx')))
    hist = [p[0] for p in xs]
    bad = []
    for t in range(3, len(xs)):
        want = (round(hist[t - 1] - 14.0, 2), round(hist[t - 2] + 14.0, 2))
        got = (round(xs[t][1], 2), round(xs[t][2], 2))
        if abs(got[0] - want[0]) > 0.01 or abs(got[1] - want[1]) > 0.01:
            bad.append((t, got, want))
    jumps = [t for t in range(1, len(xs)) if max(abs(xs[t][1] - xs[t - 1][1]), abs(xs[t][2] - xs[t - 1][2])) > 1.5 * 2.08]
    check('clone fixes v2: walk, dash, run, turnaround, run back, skid, two dash-turns, run, skid (%d frames, his speeds): '
          'the left clone at his X 1 frame back - 14, the right one 2 back + 14 (world sides: his facing changes nothing), '
          'no jump over 1.5 x 2.08' % len(plan), (bad[:3], jumps[:3]), ([], []))
    check('clone fixes v2 diag: every 10 grounded frames his VAR_23 = reasons x 10000 + (left X - target + 50) x 100 + (right '
          '+ 50) (here: no override; the left 1 frame late, the right 2), flags bit 1048576 toggling',
          (int(g.vars.get(0x0F000317)) // 10000, int(g.vars.get(0x0F000314)) >> 20 in (0, 1)), (0, True))
    # the clone's motions: no TransN sideways movement
    d = dict(O.pac_read(os.path.join(out, 'fighter', 'gekkouga', 'motion', 'clone', 'main.pac')))
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone', 'c00')
    bones = O.vbn_read(os.path.join(mdl, 'model.vbn'))
    h = bones[0][2]
    moving = []
    for name, data in d.items():
        o = O.Omo(data)
        for fr in range(o.frames):
            s_ = o.sample(h, fr)
            if s_ and (abs(s_[0][0]) > 1e-3 or abs(s_[0][2]) > 1e-3):
                moving.append(name)
                break
    walk = O.Omo(d['FitGekkougaBodyMainA01WalkMiddle.omo'])
    check('clone fixes v2: the clone\'s %d motions: TransN never moves sideways (his WalkMiddle / Run / AttackDash carry '
          'it 22 / 33 / 25.5: the clone\'s model ran ahead of its place and snapped back each loop); WalkMiddle\'s TransN '
          'still, its other bones moving' % len(d),
          (moving[:3], [round(c, 2) for c in walk.sample(h, 25)[0]],
           walk.sample(bones[2][2], 0) != walk.sample(bones[2][2], 25)), ([], [0.0, 0.0, 0.0], True))

def skeleton_side_tests(mscsb, src):
    """skeleton v1: his side special (SpecialS 0x153's per-frame: gk_ss_tick, in place of func_2291), the request's
    lapse, the reset on the executable's clear-all count (his VAR_14)"""
    m = fresh(mscsb, src)
    g = m.game
    g.ints.update({0x16000006: 12, 0x16000007: 10, 0x10000085: 0, 0x11000002: 0})
    g.vars.update({0x31: 80.0, 0x32: 12.5})
    g.lr = -1.0
    g.situation = 0
    seen = []
    for f in range(1, 23):
        g.log, g.status_req = [], []
        m('func_2291')
        if g.log or g.status_req or g.vars.get(0x0F00030F):
            seen.append(f)
            if f == 21:
                got = (list(g.log), list(g.status_req))
    check('skeleton v1: Shadow Sneak: nothing for the start-up (12) and the shadow\'s time (10): no vanish (no '
          'VisibilityModule / HitModule), no teleport; at frame 21 (where vanilla\'s func_2291 teleports him) the skeleton',
          seen[:1], [21])
    check('skeleton v1: ... his VAR_15 = 1 (asked), VAR_16 / 17 = the shadow\'s place (80, 12.5), VAR_18 his facing (-1)',
          [g.vars.get(v) for v in (0x0F00030F, 0x0F000310, 0x0F000311, 0x0F000312)], [1.0, 80.0, 12.5, -1.0])
    check('skeleton v1: ... article 8 made (ArticleModule 0x2710), then he ends the move in place: Wait (on the ground)',
          ([x for x in got[0] if x[0] == 'article'], got[1], g.posture_sets), ([('article', 0x2710, 8)], [(0, 0)], []))
    g.ints.update({0x10000085: 0, 0x11000002: 0})
    g.situation = 2
    m.vm.g[18] = 2
    for _ in range(21):
        g.status_req = []
        m('func_2291')
    check('skeleton v1: in the air: Fall (0xE) at the end', g.status_req, [(0xE, 0)])
    # the request lapses after 5 frames (one out already: none was made, the executable never claims it)
    g.situation = 0
    m.vm.g[18] = 0
    g.vars[0x0F00030E] = 0.0
    frames(m, 4)
    a = g.vars.get(0x0F00030F)
    frames(m, 1)
    check('skeleton v1: the request stays 5 frames for the executable\'s claim, then lapses (VAR_15 0)',
          (a, g.vars.get(0x0F00030F)), (1.0, 0.0))
    # a reset of the battle: his VAR_14 (the clear-all count & 7) changes
    m.setg('gk_smash', 60)
    m.setg('gk_lw_charge', 200)
    frames(m, 1)
    check('skeleton v1: VAR_14 unchanged: his charges kept', (m.g('gk_smash'), m.g('gk_lw_charge')), (60, 200))
    g.vars[0x0F00030E] = 1.0
    frames(m, 1)
    check('skeleton v1: VAR_14 changed (a training reset / restart): the smash store and the down special charge 0',
          (m.g('gk_smash'), m.g('gk_lw_charge')), (0, 0))
    m2 = fresh(mscsb, src)
    m2.game.vars[0x0F00030E] = 5.0
    m2.setg('gk_smash', 60)
    frames(m2, 1)
    check('skeleton v1: the first count he sees is only stored (not a reset)', (m2.g('gk_smash'), m2.g('gk_gen')), (60, 5))
    m2.game.vars[0x0F00030E] = 0.0
    frames(m2, 1)
    check('skeleton v1: ... a change back to 0 is a reset too', m2.g('gk_smash'), 0)


def skeleton_tests(mscsb, src):
    """skeleton v1: the Running Skeleton's MSC (skeleton.mscsb)"""

    def make(floors=((-1000.0, 1000.0, 10.0),), walls=()):
        m = MSC(mscsb, src)
        g = m.game
        g.floors = list(floors)
        g.walls = list(walls)
        g.x, g.y = 0.0, 0.0

        def sysf(sid, a, old=g.sys):
            if sid == 0x12 and a[0] == 0x1:
                g.log.append(('motion', a[1], fv(a[2]), fv(a[3])))
                return 0
            if sid == 0x14 and a[0] == 0:
                g.log.append(('lr', fv(a[1])))
                g.lr = fv(a[1])
                return 0
            if sid == 0x21 and a[0] == 0x9:
                g.log.append(('remove',))
                return 0
            return old(sid, a)
        g.sys = sysf
        return m, g

    def claim(g, x=40.0, y=10.0, d=-1.0):
        g.vars.update({0x0F000300: 3.0, 0x0F000301: x, 0x0F000302: y, 0x0F000303: d})

    def run(m, n):
        for _ in range(n):
            m('sk_frame')
    m, g = make()
    run(m, 30)
    check('skeleton: nobody claimed it: it waits (hidden, nothing else) ...', [x for x in g.log if x[0] != 'visible'], [])
    run(m, 1)
    check('skeleton: ... and after 30 frames it removes itself (BattleObject 9)', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    m, g = make()
    claim(g)
    run(m, 1)
    check('skeleton start: at its VAR_1 / 2 (40, 10: on the floor), facing its VAR_3 (-1, the model turned), the run '
          'motion (0), its phase 1 (VAR_5); the carrier model hidden',
          ([x for x in g.log if x[0] in ('lr', 'motion')], g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'visible']),
          ([('lr', -1.0), ('motion', 0, 0.0, 1.0)], 1.0, [('visible', 0)]))
    check('skeleton v1.2: its effects unhooked from its (hidden) model\'s visibility (EffectModule 0x26 (0), 0x1C (1)), then '
          'its body the flipbook following it (op 0x2717: PtcGekkougaSkeletonL 0x3300017 for way -1, joint 0, no offset)',
          [x[:3] for x in g.log if x[0] == 'effect'], [('effect', 0x26, 0), ('effect', 0x1C, 1), ('effect', 0x2717, 0x3300017)])
    g.log = []
    run(m, 1)
    check('skeleton v1.2: running, the carrier model (the hydrant) stays hidden (v1 / v1.1: shown x 2 as its stand-in body)',
          [x for x in g.log if x[0] == 'visible' and x[1] != 0], [])
    check('skeleton run: 2 steps 0.7 left (38.6, 10)', (g.x, g.y), (38.6, 10.0))
    run(m, 8)
    check('skeleton run: 10 frames: 7 units (33, 10), straight on', (round(g.x, 2), g.y), (33.0, 10.0))
    m, g = make(walls=[(30.0, 0.0, 50.0)])
    claim(g)
    run(m, 30)
    check('skeleton run: a wall (x 30) stops it short (its test reaches 2 past its step), it stays there running',
          (round(g.x, 1), g.y), (32.3, 10.0))
    # off a ledge: running right from 95 on a floor that ends at 100, a lower floor at -20 from 100 on
    m, g = make(floors=[(-1000.0, 100.0, 10.0), (100.0, 1000.0, -20.0)])
    claim(g, 95.0, 10.0, 1.0)
    run(m, 8)
    check('skeleton v1.2: way +1: the body as shot (PtcGekkougaSkeletonR 0x3300016), once',
          [x[:3] for x in g.log if x[0] == 'effect' and x[1] == 0x2717], [('effect', 0x2717, 0x3300016)])
    check('skeleton ledge: it doesn\'t stop at the ledge (x 95 -> 100.6), off it it falls', (round(g.x, 1), g.y < 10.0), (100.6, True))
    ys = []
    for _ in range(30):
        run(m, 1)
        ys.append(g.y)
    dys = [round(b - a, 3) for a, b in zip([g.posture_sets[-31][1]] + ys, ys)]
    check('skeleton fall: his gravity 0.18 a frame up to his max fall 1.85, then lands on the floor below (-20)',
          (dys[:3], min(dys), ys[-1]), ([-0.36, -0.54, -0.72], -1.85, -20.0))
    # the explosion at 180 frames
    m, g = make()
    claim(g)
    run(m, 179)
    check('skeleton: 179 frames: still running (phase 1, no explosion)', (g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'motion'][-1]),
          (1.0, ('motion', 0, 0.0, 1.0)))
    g.log = []
    run(m, 1)
    check('skeleton explosion at 180: phase 2 (VAR_5: its collision removed, its hits burn), its body ended (both facings\' '
          'sets, 0x2723), v1.2: the explosion flipbook (0x3300019) at its feet (x, y: its base on the ground)',
          (g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'motion'], [x[:3] for x in g.log if x[0] == 'effect' and x[1] == 0x2723],
           [x[:5] for x in g.log if x[0] == 'effect' and x[1] != 0x2723]),
          (2.0, [], [('effect', 0x2723, 0x3300016), ('effect', 0x2723, 0x3300017)],
           [('effect', 3, 0x3300019, round(40.0 - 0.7 * 179, 3), 10.0)]))
    g.log = []
    run(m, 1)
    check('skeleton explosion: the next frame (its scale back to 1) the explode motion (1: its hitbox), its body hidden',
          ([x for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'visible']), ([('motion', 1, 0.0, 1.0)], [('visible', 0)]))
    x0 = g.x
    run(m, 38)
    check('skeleton explosion: it stays put; removed 40 frames after (BattleObject 9)',
          (g.x == x0, [x for x in g.log if x[0] == 'remove']), (True, []))
    run(m, 1)
    check('skeleton explosion: ... removed', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    # mid-air: off a ledge, exploding in the air
    m, g = make(floors=[(-1000.0, 50.0, 10.0)])
    claim(g, 45.0, 10.0, 1.0)
    run(m, 180)
    check('skeleton explosion in the air (it ran off at 50 and fell): still at 180, where it is', (g.vars.get(0x0F000305), g.y < 0),
          (2.0, True))
    # hits / HP
    m, g = make()
    claim(g)
    run(m, 5)
    g.vars.update({0x0F000309: 1.0, 0x0F000307: 50.0, 0x0F000308: 20.0, 0x0F000304: 9.0})
    g.log = []
    run(m, 1)
    check('skeleton hit (the executable: VAR_9 1, at VAR_7 / 8): v1.2: the impact sparks flipbook (0x3300018) there; 9 of 25: '
          'still running',
          ([x[:5] for x in g.log if x[0] == 'effect'], g.vars.get(0x0F000305)), ([('effect', 3, 0x3300018, 50.0, 20.0)], 1.0))
    g.log = []
    run(m, 1)
    check('skeleton hit: no new hit: no spark', [x for x in g.log if x[0] == 'effect'], [])
    g.vars.update({0x0F000309: 3.0, 0x0F000304: 25.0})
    g.log = []
    x0, y0 = g.x, g.y
    run(m, 1)
    check('skeleton at 0 HP (25 damage): smoked: phase 3, the smoke at its middle, motion 2 (no hitbox), no explosion',
          (g.vars.get(0x0F000305), [x[:5] for x in g.log if x[0] == 'effect' and x[1] != 0x2723],
           [x[:3] for x in g.log if x[0] == 'effect' and x[1] == 0x2723], [x for x in g.log if x[0] == 'motion']),
          (3.0, [('effect', 3, 0x3300018, 50.0, 20.0), ('effect', 3, 0x1000021, round(x0, 3), round(y0 + 14.0, 3))],
           [('effect', 0x2723, 0x3300016), ('effect', 0x2723, 0x3300017)], [('motion', 2, 0.0, 1.0)]))
    run(m, 2)
    check('skeleton smoke: removed 3 frames after', [x for x in g.log if x[0] == 'remove'], [])
    run(m, 1)
    check('skeleton smoke: ... removed', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    run(m, 200)
    check('skeleton smoke: never explodes after', [x for x in g.log if x[0] == 'motion' and x[1] == 1], [])
    # hitlag: it doesn't move
    m, g = make()
    claim(g)
    run(m, 1)
    x0 = g.x
    g.hitlag = 3
    run(m, 3)
    check('skeleton in hitlag: it doesn\'t move', g.x, x0)


def skeleton_data_tests(out):
    """skeleton v1: its built files: the explosion's hitbox, the scripts' names, its collision, its carrier"""
    import acmd
    import lvd
    import gekkouga_clone_cave as C
    fg = os.path.join(out, 'fighter', 'gekkouga')
    ow = os.path.join(fg, 'script', 'animcmd', 'weapon', 'skeleton')
    mt = open(os.path.join(ow, 'motion.mtable'), 'rb').read()
    check('skeleton scripts: motion.mtable = SkeletonRun / SkeletonExplode / SkeletonSmoke (its motion kinds 0 / 1 / 2)',
          list(struct.unpack('>3I', mt)), [acmd.crc(n) for n in GB.SK_SCRIPTS])
    game = acmd.ACMDFile.load(os.path.join(ow, 'game.bin'))
    boom = [c for c in game.script('SkeletonExplode') if c.name in ('Special_Hitbox', 'Extra_Special_Hitbox')]
    syn = boom[0].info['syntax'] if boom else []
    hb = dict(zip(syn, boom[0].params)) if boom else {}
    check('skeleton explosion: one hitbox, 15 %, 50 degrees, KBG 50 / BKB 40, size 22 at its middle (bone 0, Y 14), flame, '
          'launched from its middle (FacingRestrict 5), then off after 4 frames',
          (len(boom), [round(hb.get(k, -1), 3) for k in ('Damage', 'Angle', 'KBG', 'BKB', 'Size', 'Y', 'Effect', 'FacingRestrict', 'Bone')],
           [c.name for c in game.script('SkeletonExplode')][1:3]),
          (1, [15.0, 50, 50, 40, 22.0, 14.0, 5, 5, 0], ['WAIT', 'Remove_All_Hitboxes']))
    p = 145.0
    kb = ((p / 10 + p * 15 / 20) * 200 / 200 * 1.4 + 18) * 0.5 + 40
    check('skeleton explosion: Smash 4\'s knockback on Mario (weight 100) at 130 %% (+ 15): %.1f (a mid-stage KO ~130-140)' % kb,
          130 <= kb <= 140, True)
    check('skeleton v1.5: the explosion\'s hitstun x %g (Extra_Special_Hitbox HitstunMul; the other extras 0: unchanged)' %
          GB.SK_BOOM_HITSTUN, (boom[0].name if boom else None, hb.get('HitstunMul'),
                               [hb.get(k) for k in ('HitstopMul', 'HitstopFrames', 'SelfHitstopMul', 'SelfHitstopFrames', 'DIMul')]),
          ('Extra_Special_Hitbox', GB.SK_BOOM_HITSTUN, [0.0, 0, 0.0, 0, 0.0]))
    run = game.script('SkeletonRun')
    fr, on, t = 0.0, [], {}
    for c in run:
        if c.name == 'FRAME':
            fr = float(c.params[0])
        elif c.name == 'Extended_Special_Hitbox':
            on.append(fr)
            t = dict(zip(c.info['syntax'], c.params))
        elif c.name == 'Remove_All_Hitboxes':
            on.append(-fr)
    starts = [x for x in on if x >= 0]
    check('skeleton v1.5 contact: SkeletonRun puts its body capsule (joint 0, radius 3.5, Y 3.5 - 20.5: x +- 3.5, y 0 - 24) '
          'on at frames 0, 3, 6 ... 45 and off 2 frames later (a touch every 3 frames, as up air\'s multi-hit); no '
          'knockback (KBG / FKB / BKB 0), no hitlag, no flinch, 0.1 %%, fire',
          (starts[:3], len(starts), all(-on[2 * k + 1] == starts[k] + 2 for k in range(len(starts))),
           [t.get(k) for k in ('Bone', 'Size', 'Y', 'Y2', 'KBG', 'FKB', 'BKB', 'DisableHitlag', 'Flinchless', 'Effect')],
           round(t.get('Damage', 0), 3)),
          ([0.0, 3.0, 6.0], 16, True, [0, 3.5, 3.5, 20.5, 0, 0, 0, 1, 1, 5], 0.1))
    check('skeleton scripts: smoke without a hitbox; effect / sound empty', [c.name for c in game.script('SkeletonSmoke')],
          ['Script_End'])
    lv = lvd.LVD(os.path.join(fg, 'model', 'skeleton', 'c00', 'skeleton.lvd'))
    c = lv.collisions[0]
    check('skeleton.lvd: one collision, the 4 vertices the executable moves (v1.5: x +- 3.5, y 2 / 24: its body), a wall each side and a '
          'floor on top (normals out), the hydrant\'s flags',
          (len(lv.collisions), [tuple(round(x, 2) for x in v) for v in c.verts], [tuple(n) for n in c.normals], c.flags),
          (1, [tuple(v) for v in C.sk_verts(C.RELEASE)], [(-1.0, 0.0), (0.0, 1.0), (1.0, 0.0)], [0, 1, 0, 0]))
    check('skeleton: its main.pac and carrier model files are present (Pac-Man\'s hydrant\'s)',
          [f for f in GB.SK_CARRIER if not os.path.exists(os.path.join(fg, 'model', 'skeleton', 'c00', f))] +
          [f for f in ('main.pac',) if not os.path.exists(os.path.join(fg, 'motion', 'skeleton', f))], [])
    names = open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand', 'ModAnimNames.txt')).read()
    check('skeleton: its script names in ModAnimNames.txt (with -> lines for the Hitbox Viewer)',
          [n for n in GB.SK_SCRIPTS if '\n%s -> skeleton/' % n not in names], [])


def trail_side_tests(mscsb, src):
    """burn v2: his smashes ask for their fire trails at the main hit (gk_trail_tick, from gk_chain_try every frame of
    the attack statuses): his place and each standing clone's, the requests' lapse"""
    m = fresh(mscsb, src)
    g = m.game
    g.situation = 0
    m.vm.g[18] = 0
    m.vm.g[4] = 0x2D
    g.x, g.y, g.lr = 30.0, 10.0, -1.0
    arts = lambda: [x for x in g.log if x[0] == 'article']    # noqa: E731
    got = []
    for fr in (11, 12):
        g.frame, g.log = float(fr), []
        m('gk_chain_try', 1)
        got.append(arts())
    check('burn v2: forward smash frames 11 / 12: no trail yet (its hit at 13)', got, [[], []])
    g.frame, g.log = 13.0, []
    m('gk_chain_try', 1)
    check('burn v2: frame 13: his request 0 (VAR_0 type 1, VAR_1 / 2 his place, VAR_3 his facing) and article 9 made',
          ([g.vars.get(0x0F000300 + i) for i in range(4)], arts()), ([1.0, 30.0, 10.0, -1.0], [('article', 0x2710, 9)]))
    g.frame, g.log = 14.0, []
    m('gk_chain_try', 1)
    check('burn v2: frame 14: not again', arts(), [])
    frames(m, 4, 0x2D)
    check('burn v2: the request kept 5 frames for the executable\'s claims ...', g.vars.get(0x0F000300), 1.0)
    frames(m, 1, 0x2D)
    check('burn v2: ... then lapses (not claimed: six trails out already)', g.vars.get(0x0F000300), 0.0)
    # the clones: down smash with both out, the right one falling on its own (no trail for it)
    frames(m, 1, 0)
    m.setg('gk_alive', 3)
    m.setgf('gk_lx', 16.0)
    m.setgf('gk_ly', 10.0)
    m.setgf('gk_rx', 44.0)
    m.setgf('gk_ry', 10.0)
    m.vm.g[4] = 0x30
    g.frame, g.log = 16.0, []
    m('gk_chain_try', 4)
    check('burn v2: down smash (type 3) at 16 with both clones out: his request and the left clone\'s (16, 10), the right '
          'one\'s (44, 10): three, three trails made',
          ([g.vars.get(0x0F000300 + i) for i in range(12)], arts()),
          ([3.0, 30.0, 10.0, -1.0, 3.0, 16.0, 10.0, -1.0, 3.0, 44.0, 10.0, -1.0], [('article', 0x2710, 9)] * 3))
    frames(m, 1, 0)
    for i in range(12):
        g.vars[0x0F000300 + i] = 0.0
    m.setg('gk_rfall', 5)
    m.vm.g[4] = 0x33
    g.frame, g.log = 18.0, []
    m('gk_chain_try', 2)
    check('burn v2: up smash (type 2) at 18, the right clone falling on its own: his and the left clone\'s only',
          ([g.vars.get(0x0F000300 + i) for i in (0, 4, 8)], len(arts())), ([2.0, 2.0, 0.0], 2))
    frames(m, 1, 0)
    m.vm.g[18] = 2
    m.vm.g[4] = 0x2D
    g.frame, g.log = 13.0, []
    m('gk_chain_try', 1)
    check('burn v2: in the air: no trail', arts(), [])


def firetrail_tests(mscsb, src):
    """burn v2: the fire trail's MSC (firetrail.mscsb)"""

    def make():
        m = MSC(mscsb, src)
        g = m.game

        def sysf(sid, a, old=g.sys):
            if sid == 0x12 and a[0] == 0x1:
                g.log.append(('motion', a[1], fv(a[2]), fv(a[3])))
                return 0
            if sid == 0x14 and a[0] == 0:
                g.log.append(('lr', fv(a[1])))
                return 0
            if sid == 0x21 and a[0] == 0x9:
                g.log.append(('remove',))
                return 0
            if sid == 0x1C:
                g.log.append(('fx', a[0]) + tuple(a[1:3]) + tuple(round(fv(x), 2) for x in a[3:6]) if a[0] == 0x2717
                             else ('fx',) + tuple(a))
                return 0
            return old(sid, a)
        g.sys = sysf
        return m, g

    def run(m, n):
        for _ in range(n):
            m('tr_frame')
    m, g = make()
    run(m, 30)
    check('trail: nobody claimed it: it waits (hidden) ...', [x for x in g.log if x[0] not in ('visible',)], [])
    run(m, 1)
    check('trail: ... and after 30 frames it removes itself', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    m, g = make()
    g.vars.update({0x0F000300: 3.0, 0x0F000301: 1.0, 0x0F000302: 40.0, 0x0F000303: 10.0, 0x0F000304: -1.0})
    run(m, 1)
    check('trail start (forward smash at (40, 10), way -1): facing -1 (its model turned: PostureModule 0, 2), there, its '
          'effects unhooked from its hidden model (0x26 (0), 0x1C (1)), motion 0 held (rate 0: its hitboxes), the first flame '
          '10 ahead (fire trail fix v1: on joint 0\'s local Z, forward in its turned frame: X 0, Y 0, Z 10)',
          ([x for x in g.log if x[0] in ('lr', 'motion')], g.posture_sets[:1], [x for x in g.log if x[0] == 'fx'],
           [x for x in g.log if x[0] == 'visible' and x[1] != 0]),
          ([('lr', -1.0), ('motion', 0, 0.0, 0.0)], [(40.0, 10.0)],
           [('fx', 0x26, 0), ('fx', 0x1C, 1), ('fx', 0x2717, 0x330001C, 0, 0.0, 0.0, 10.0)], []))
    g.log = []
    run(m, 5)
    check('trail: a flame a frame along its way (local Z 18 ... 42, X / Y 0: on the ground ahead), five in all',
          [x[4:7] for x in g.log if x[0] == 'fx'], [(0.0, 0.0, 18.0), (0.0, 0.0, 26.0), (0.0, 0.0, 34.0), (0.0, 0.0, 42.0)])
    g.log = []
    run(m, 158)
    check('trail: frames 7 - 164: nothing more; it stays put', ([x for x in g.log if x[0] in ('fx', 'remove')], g.posture_sets[-1]),
          ([], (40.0, 10.0)))
    g.log = []
    run(m, 1)
    check('trail: frame 165: its fire fades (0x2723 (id, 0, 0): its set\'s 15-frame fade)', [x for x in g.log if x[0] == 'fx'],
          [('fx', 0x2723, 0x330001C, 0, 0)])
    g.log = []
    run(m, 14)
    check('trail: ... still there until 179', [x for x in g.log if x[0] in ('fx', 'remove')], [])
    run(m, 1)
    check('trail: frame 180 (3 s): its fire ended, removed', [x for x in g.log if x[0] in ('fx', 'remove')],
          [('fx', 0x2723, 0x330001C, 1, 1), ('remove',)])
    for typ, way, want in [(t, w, ws) for t, ws in (
            (1, [10.0, 18.0, 26.0, 34.0, 42.0]),
            (2, [6.0, -6.0, 14.0, -14.0]),
            (3, [10.0, -10.0, 19.0, -19.0, 28.0, -28.0, 37.0, -37.0])) for w in (1.0, -1.0)]:
        m, g = make()
        g.vars.update({0x0F000300: 3.0, 0x0F000301: float(typ), 0x0F000302: 0.0, 0x0F000303: 0.0, 0x0F000304: way})
        run(m, 12)
        check('fire trail fix v1: %s smash facing %s: motion %d, its flames on the ground (Y 0) along its way (local Z: '
              'X 0, never into the screen) %s; its model turned by its way (the same Z either way)' % (
                  ('forward', 'up', 'down')[typ - 1], 'right' if way > 0 else 'left', typ - 1,
                  'ahead' if typ == 1 else 'each side alternately (up smash: under its geyser, 6 / 14: an interpretation)'),
              ([x[1] for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'lr'][:1],
               [x[4:7] for x in g.log if x[0] == 'fx' and x[1] == 0x2717]),
              ([typ - 1], [('lr', way)], [(0.0, 0.0, z) for z in want]))


def trail_data_tests(out):
    """burn v2: the fire trail's built files"""
    fg = os.path.join(out, 'fighter', 'gekkouga')
    ow = os.path.join(fg, 'script', 'animcmd', 'weapon', 'firetrail')
    mt = open(os.path.join(ow, 'motion.mtable'), 'rb').read()
    check('trail scripts: motion.mtable = FireTrailS4 / FireTrailHi4 / FireTrailLw4 (its motion kinds 0 / 1 / 2)',
          list(struct.unpack('>3I', mt)), [acmd.crc(n) for n in GB.TR_SCRIPTS])
    game = acmd.ACMDFile.load(os.path.join(ow, 'game.bin'))
    rows = []
    for n in GB.TR_SCRIPTS:
        sc = game.script(n)
        hb = [dict(zip(c.info['syntax'], c.params)) for c in sc if c.name == 'Special_Hitbox']
        rows.append((n, [(h['ID'], h['Bone'], round(h['Z'], 2), round(h['Y'], 2), round(h['Size'], 2)) for h in hb],
                     sorted({(round(h['Damage'], 2), h['KBG'], h['FKB'], h['BKB'], h['Rehit'], h['DisableHitlag'], h['NoGFX'],
                              h['Flinchless'], round(h['Hitlag'], 2), h['Ground/Air'], h['Shieldable']) for h in hb}),
                     [c.name for c in sc][-1]))
    check('trail hitboxes (bone 0, from frame 0, never removed): along each smash\'s path, 0.1 %, no knockback (KBG / FKB / '
          'BKB 0), re-hit every 35 frames, no hitlag, no hit effect, no flinch, ground and air, shieldable', rows,
          [(n, [(i, 0, z, y, sz) for i, (z, y, sz) in enumerate(GB.TR_BOXES[n])],
            [(0.1, 0, 0, 0, 35, 1, 1, 1, 0.0, 3, 1)], 'Script_End') for n in GB.TR_SCRIPTS])
    check('trail scripts: effect / sound empty (its MSC makes the fire)',
          [[c.name for c in acmd.ACMDFile.load(os.path.join(ow, f)).script(n)] for f in ('effect.bin', 'sound.bin')
           for n in GB.TR_SCRIPTS], [['Script_End']] * 6)
    check('trail: its main.pac and carrier model files are present (Pac-Man\'s hydrant\'s), its MSC',
          [f for f in GB.SK_CARRIER if not os.path.exists(os.path.join(fg, 'model', 'firetrail', 'c00', f))] +
          [f for f in (os.path.join('motion', 'firetrail', 'main.pac'), os.path.join('script', 'msc', 'firetrail', 'firetrail.mscsb'))
           if not os.path.exists(os.path.join(fg, f))], [])
    names = open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand', 'ModAnimNames.txt')).read()
    check('trail: its script names in ModAnimNames.txt (with -> lines for the Hitbox Viewer)',
          [n for n in GB.TR_SCRIPTS if '\n%s -> firetrail/' % n not in names], [])


def script_tests(out, user):
    O = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    ug = acmd.ACMDFile.load(os.path.join(user, 'body', 'game.bin'))
    ue = acmd.ACMDFile.load(os.path.join(user, 'body', 'effect.bin'))
    pg = acmd.ACMDFile.load(os.path.join(O, 'body', 'game.bin'))
    pe = acmd.ACMDFile.load(os.path.join(O, 'body', 'effect.bin'))
    import rolloff_acmd as RA
    mom = {nm: [(f, float(c.params[0])) for f, c in RA.timeline(pg.script(nm)) if c.ident == RA.MOM]
           for nm in GB.ROLLOFF_SCRIPTS}
    check('skeleton v1.3 package: his rolls\' roll-off speed (the user: 2.5; his game.bin had none, so the MSC\'s kinetic '
          'type 0x6 rolls never moved): cleared at 0, cleared then +-2.5 at 5, cleared at 27 (the back roll -2.5)',
          mom, {'EscapeF': [(0.0, 0.0), (5.0, 0.0), (5.0, 2.5), (27.0, 0.0)],
                'EscapeB': [(0.0, 0.0), (5.0, 0.0), (5.0, -2.5), (27.0, 0.0)]})
    msrc = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c')).read()
    check('skeleton v1.3 package: his MSC\'s roll-off air multiplier 1.24, the ground cap lifted (KineticModule(0x15, 3, -1, '
          '-1) on the roll frames: universal_mechanics --ground-uncapped)',
          ('float rolloff_air_speed_mult() { return 1.24f; }' in msrc,
           'KineticModule(0x15, 0x3, -1.0f, -1.0f); // no ground speed limit on the roll\'s speed (user: gekkouga)' in msrc),
          (True, True))
    GB.add_rolloff(ug)                    # (the rest compared against his own with the roll-off added)
    tips = [(nm, [(int(c.params[1]), round(float(c.params[3]), 2), round(float(c.params[4]), 2), round(float(c.params[8]), 2))
                  for c in pe.script(nm) if c.name == 'External_Graphic' and int(c.params[0]) == GB.FIRE_TIP],
             len([c for c in pe.script(nm) if c.name == 'Terminate_Graphic_Effect' and int(c.params[0]) == GB.FIRE_TIP]))
            for nm in ('AttackS4', 'AttackHi4', 'AttackLw4', 'AttackAirF', 'AttackAirN')]
    if GB.FIRE_TIPS:
        ring = [(int(c.params[0]), int(c.params[1]), int(c.params[2]), round(float(c.params[4]), 2),
                 round(float(c.params[5]), 2), round(float(c.params[9]), 2)) for c in pe.script('AttackAirN')
                if c.name == 'EFFECT_FOLLOW_FLIP' and int(c.params[0]) == GB.FIRE_RING]
        check('burn v2.2 / v2.3: neutral air\'s water burst wrapped in fire: its ring (0x%X, facing left 0x%X: '
              'EFFECT_FOLLOW_FLIP) with it, on its call (joint 0, Y 8.5, size 1.45), played out (no Terminate); burn v2\'s '
              'two side flames gone' % (GB.FIRE_RING, GB.FIRE_RING_L),
              (ring, [c.name for c in pe.script('AttackAirN') if c.params and isinstance(c.params[0], int) and
                      int(c.params[0]) in (GB.FIRE_RING, GB.FIRE_TIP)]),
              ([(GB.FIRE_RING, GB.FIRE_RING_L, 0, 8.5, 0.0, 1.45)], ['EFFECT_FOLLOW_FLIP']))
        check('burn v2: a flame (0x%X) at each water sword\'s tip (its hand joint, Y -11 x its size: -55 in the smashes), '
              'ended with the sword' % GB.FIRE_TIP, tips,
              [('AttackS4', [(25, -55.0, 0.0, 2.0)], 1), ('AttackHi4', [(25, -55.0, 0.0, 2.0), (24, -55.0, 0.0, 2.0)], 1),
               ('AttackLw4', [(25, -55.0, 0.0, 2.0), (24, -55.0, 0.0, 2.0)], 1), ('AttackAirF', [], 0),
               ('AttackAirN', [], 0)])
        blade = [(int(c.params[1]), round(float(c.params[2]), 2), round(float(c.params[3]), 2), round(float(c.params[8]), 2))
                 for c in pe.script('AttackAirF') if c.name == 'External_Graphic' and int(c.params[0]) == GB.FIRE_BLADE]
        check('skeleton v1.3 package: forward air\'s flames along its water sword (0x%X, burn v2\'s tip flame gone): at the '
              'sword\'s joint (25) and size (1), made and ended with it' % GB.FIRE_BLADE,
              (blade, [c.name for c in pe.script('AttackAirF') if c.params and isinstance(c.params[0], int) and
                       int(c.params[0]) in (GB.FIRE_BLADE, GB.SWORD)]),
              ([(25, 0.0, 0.0, 1.0)], ['External_Graphic', 'External_Graphic', 'Terminate_Graphic_Effect',
                                       'Terminate_Graphic_Effect']))
        check('burn v2: ... and his effect scripts otherwise unchanged (the flames taken out again: the True blocks\' '
              'offsets back)', GB.strip_fire_tips(pe), 11)
    smash = {zlib.crc32(n.encode()) for n in GB.SMASH_SCRIPTS}
    hold = {zlib.crc32(n.encode()) for n in GB.HOLD_SCRIPTS}
    bad, n, got = [], 0, {}
    for f0, f1, kind in ((ug, pg, 'game'), (ue, pe, 'effect')):
        check('%s.bin: the same scripts' % kind, sorted(f0.scripts), sorted(f1.scripts))
        for crc in f0.scripts:
            a, b = f0.scripts[crc], f1.scripts[crc]
            for c0, c1 in zip(a, b):
                if c0.ident != c1.ident:
                    bad.append((kind, hex(crc), 'ident'))
                    continue
                for i, (p0, p1) in enumerate(zip(c0.params, c1.params)):
                    nm = c0.info['syntax'][i] if i < len(c0.info['syntax']) else ''
                    k = None
                    if crc in smash and nm == 'Size' and c0.name in GB.HITBOXES and kind == 'game':
                        k = 5.0
                    elif (crc in smash and kind == 'game' and c0.name in GB.HITBOXES and nm in ('X', 'Y', 'Z', 'X2', 'Y2', 'Z2')
                          and int(c0.params[c0.info['syntax'].index('Bone')]) in GB.SWORD_BONES):
                        k = 5.0
                    elif crc in smash and kind == 'effect' and (nm == 'Size' or (c0.name == 'Sword_Glow' and nm in
                                                                                 ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'))):
                        k = 5.0
                    elif crc in hold and kind == 'effect' and nm == 'Size' and c0.name in GB.HOLD_EFFECTS:
                        k = 0.0
                    if k is not None:
                        n += 1
                        got[(kind, k)] = got.get((kind, k), 0) + 1
                    if (abs(float(p1) - float(p0) * k) > 1e-3) if k is not None else (p1 != p0):
                        bad.append((kind, hex(crc), c0.name, nm, p0, p1))
    check('v3: the shipped body scripts the smashes play (attacks4 / attackhi4 / attacklw4, motions 0x5F / 0x63 / 0x65): '
          'v4: hitbox Size x5 and the water-sword bones\' (24 / 25) hitbox offsets x5 (game), every effect Size and trail point x5 (effect); their holds\' (0x62 / 0x64 / 0x67) effects '
          'size 0 (his MSC draws them by the charge); nothing else of his changed',
          (bad[:3], got.get(('game', 5.0), 0) >= 30, got.get(('effect', 5.0), 0) >= 20, got.get(('effect', 0.0), 0)),
          ([], True, True, 11))
    mt = open(os.path.join(user, 'body', 'motion.mtable'), 'rb').read()
    mth = [struct.unpack_from('>I', mt, 4 * i)[0] for i in range(len(mt) // 4)]
    check('v3: those scripts are the smash motions\' (the motion table: attacks4 0x5F, attacks4hold 0x62, attackhi4 0x63, '
          'attackhi4hold 0x64, attacklw4 0x65, attacklw4hold 0x67)',
          [mth[k] for k in (0x5F, 0x62, 0x63, 0x64, 0x65, 0x67)],
          [zlib.crc32(x.encode()) for x in ('attacks4', 'attacks4hold', 'attackhi4', 'attackhi4hold', 'attacklw4', 'attacklw4hold')])
    cg = acmd.ACMDFile.load(os.path.join(O, 'weapon', 'clone', 'game.bin'))
    ok = []
    for crc, s in cg.scripts.items():
        o = pg.scripts[crc]
        hb0 = [c for c in o if c.name in GB.HITBOXES]
        hb1 = [c for c in s if c.name in GB.HITBOXES]
        same = len(hb0) == len(hb1)
        for c0, c1 in zip(hb0, hb1):
            for nm in c0.info['syntax']:
                i = c0.info['syntax'].index(nm)
                if nm == 'Bone':
                    same &= (c1.params[i] == 0) == (c0.params[i] == 0) and (c1.params[i] == 0 or c1.params[i] >= 0x7D0)
                elif nm == 'Damage':
                    same &= abs(float(c1.params[i]) - float(c0.params[i]) * (1.4 if crc in smash else 1.0)) < 1e-3
                else:
                    same &= c0.params[i] == c1.params[i]
        bad_cmds = [c.name for c in s if c.name not in GB.CLONE_GAME | GB.FLOW | GB.FLOW_KEEP_SAFE]
        ok.append(same and not bad_cmds)
    check('the clone\'s game scripts (%d): his hitboxes (bones the article\'s joints, his smashes\' damage x1.4), only '
          'hitbox / timing commands' % len(cg.scripts), all(ok) and len(cg.scripts) >= 35, True)
    ce = acmd.ACMDFile.load(os.path.join(O, 'weapon', 'clone', 'effect.bin'))
    sizes = []
    for nm in GB.SMASH_SCRIPTS:
        for c in ce.scripts.get(zlib.crc32(nm.encode()), []):
            if 'Size' in c.info['syntax'] and c.name != 'Sword_Glow' and int(c.params[0]) != GB.FIRE_TIP:
                sizes.append(float(c.params[c.info['syntax'].index('Size')]))
    his = []
    for nm in GB.SMASH_SCRIPTS:
        for c in GB.flatten(pe.scripts.get(zlib.crc32(nm.encode()), [])):
            if c.name in GB.CLONE_EFFECT and 'Size' in c.info['syntax'] and c.name != 'Sword_Glow' and \
                    int(c.params[0]) != GB.FIRE_TIP:
                his.append(float(c.params[c.info['syntax'].index('Size')]))
    check('v4: the clone has his smash effects too (their True branches), at his sizes (x5: the water sword / flash 5.0; '
          'clone fixes v1: every effect request of them)', (len(sizes) >= 8, sizes == his, 5.0 in sizes), (True, True, True))
    sw = [c for nm in GB.SMASH_SCRIPTS for c in ce.scripts.get(zlib.crc32(nm.encode()), []) if c.name == 'Sword_Glow']
    check('v4: ... its trails 5x long (Y2 -55) on its sword joints (0x7D0 + 24: his joint 24 RHaveN; clone fixes v2: his '
          'joint 25, ThrowN by model.jtb, on the clone\'s LHaveN, 0x7D0 + 23)',
          sorted({(int(c.params[c.info['syntax'].index('Bone2')]), round(float(c.params[c.info['syntax'].index('Y2')]), 2))
                  for c in sw}), [(0x7D0 + 23, -55.0), (0x7D0 + 24, -55.0)])
    j25 = sorted({(n, c.name, int(c.params[c.info['syntax'].index('Bone')])) for n in ('attackairf', 'attackhi4', 'specialnhold')
                  for c in ce.scripts.get(zlib.crc32(n.encode()), []) if 'Bone' in c.info['syntax'] and
                  c.name in ('External_Graphic', 'Graphic_Effect2')})
    check('clone fixes v2 (the user: the clones\' forward air sword / trail hang down): his joint-25 effects (the water sword, '
          'its flames, the smashes\' second sword) on the clone\'s left hand (0x7D0 + 23), not its still ThrowN (0x7D0 + 25); '
          'TEST_ONLY_DATA clone_sword_rhave / clone_sword_thrown the alternatives',
          sorted({b_ for _n, _c, b_ in j25 if b_ >= 0x7D0}), [0x7D0 + 23, 0x7D0 + 24])
    check('the clone has his forward smash, his jab, his up air (the loop)',
          all(zlib.crc32(n.encode()) in cg.scripts for n in ('attacks4', 'attack11', 'attackairhi')), True)
    mt0 = open(os.path.join(user, 'body', 'motion.mtable'), 'rb').read()
    mt1 = open(os.path.join(O, 'weapon', 'clone', 'motion.mtable'), 'rb').read()
    check('the clone\'s motion.mtable is his (668 motions)', (mt1 == mt0, len(mt1) // 4), (True, 668))


class Installed:
    """the earlier packages installed in order (a later one's file replaces an earlier one's)"""

    def __init__(self, paths):
        self.zs = [zipfile.ZipFile(p) for p in paths]

    def namelist(self):
        return sorted(set(n for z in self.zs for n in z.namelist()))

    def read(self, n):
        for z in reversed(self.zs):
            if n in z.namelist():
                return z.read(n)
        raise KeyError(n)


def sb_parse(sb, bones):
    """the model library's swing parser's checks (0x036B8040), in Python: ' BWS' (LE, swapped to 'SWB '), version
    0x10005 (0x8C-byte entries from +0xC), the count at +8; each entry's bone looked up by hash (0x036B0318: a miss is
    skipped, 0x036B8474) -> (count, [found bone names], [missed hashes])"""
    assert sb[:4] == b' BWS', sb[:4]
    ver = struct.unpack('<I', sb[4:8])[0]
    assert ver == 0x10005, hex(ver)
    n = struct.unpack('<I', sb[8:12])[0]
    assert len(sb) == 12 + 0x8C * n, (len(sb), n)
    names = {h: nm for nm, _p, h in bones}
    found, missed = [], []
    for i in range(n):
        h = struct.unpack('<I', sb[12 + 0x8C * i:16 + 0x8C * i])[0]
        (found.append(names[h]) if h in names else missed.append(h))
    return n, found, missed


def model_tests(out, earlier):
    """v11: the clone's model / motions. The release: the merged main.pac (v10's), v9.1's model.nud (every vertex on a
    bone main.pac keys: the tongue visible, on the clone, rigid) and his own model.sb (v10's unswung one made the tongue
    vanish); TEST_ONLY_DATA/sway: his own model.nud + model.sb, for the E_sway exe"""
    import omo as O
    if len(earlier) < 11:
        return
    v8 = Installed(earlier[:8])
    v91 = zipfile.ZipFile(earlier[9])
    v10 = zipfile.ZipFile(earlier[10])
    oc = 'fighter/gekkouga/motion/clone/'
    mot = os.path.join(out, oc)
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone')
    td_root = os.path.join(out, 'TEST_ONLY_DATA')
    if len(earlier) < 29:
        check("v11: the release's main.pac is v10's (merged; loaded in v9.1 and v10)",
              open(os.path.join(mot, 'main.pac'), 'rb').read() == v10.read('INSTALL_TO_data/' + oc + 'main.pac'), True)
    else:
        with tempfile.TemporaryDirectory() as td_:
            pp = os.path.join(td_, 'main.pac')
            open(pp, 'wb').write(v10.read('INSTALL_TO_data/' + oc + 'main.pac'))
            old = O.pac_read(pp)
        new = O.pac_read(os.path.join(mot, 'main.pac'))
        h0 = O.vbn_read(os.path.join(mdl, 'c00', 'model.vbn'))[0][2]
        bad, still = [], 0
        for (n0, d0), (n1, d1) in zip(old, new):
            m0 = O.Omo(d0)
            still += GB.root_still(m0, h0)
            if n0 != n1 or m0.encode() != d1:
                bad.append(n0)
        check("v11 / skeleton v1.4: the release's main.pac is v10's (merged) with TransN kept still sideways (%d motions: "
              "clone fixes v2's root_still), every motion otherwise byte for byte" % still,
              (len(old) == len(new), bad[:3], still > 20), (True, [], True))
    bad = []
    for c in range(8):
        rel = 'fighter/gekkouga/model/clone/c%02d/' % c
        cd = os.path.join(mdl, 'c%02d' % c)
        b = O.vbn_read(os.path.join(cd, 'model.vbn'))
        nud = open(os.path.join(cd, 'model.nud'), 'rb').read()
        sb = open(os.path.join(cd, 'model.sb'), 'rb').read()
        rigid = nud if GB.CLONE_RELEASE == 'rigid' else open(os.path.join(td_root, 'rigid', rel + 'model.nud'), 'rb').read()
        if rigid != v91.read('INSTALL_TO_data/' + rel + 'model.nud'):
            bad.append(('nud not v9.1', c))
        if GB.CLONE_RELEASE == 'own' and nud != v8.read('INSTALL_TO_data/' + rel + 'model.nud'):
            bad.append(('v15: the release nud not his own', c))
        if sb != v8.read('INSTALL_TO_data/' + rel + 'model.sb'):
            bad.append(('sb not his', c))
        n, found, missed = sb_parse(sb, b)
        if n != 13 or missed:
            bad.append(('sb parse', c, n, missed))
        if open(os.path.join(td_root, 'sway', rel + 'model.nud'), 'rb').read() != v8.read('INSTALL_TO_data/' + rel + 'model.nud'):
            bad.append(('sway nud', c))
        if open(os.path.join(td_root, 'sway', rel + 'model.sb'), 'rb').read() != sb:
            bad.append(('sway sb', c))
    check('v11 / v15: c00-c07: the rigid model.nud = v9.1\'s (v15: TEST_ONLY_DATA/rigid; the release his own: native swing), '
          'model.sb = his own (13 entries, all found); TEST_ONLY_DATA/sway = his own model.nud + model.sb', bad, [])


def package_tests(out, pkg, base, base_diag, v1=None, earlier=()):
    """the package; with earlier packages (v1, v2: --v1 / --v2) it is an update over them: only the files that differ
    from what they install"""
    z = zipfile.ZipFile(pkg)
    names = set(z.namelist())
    earlier = list(earlier) or ([v1] if v1 else [])
    z1 = Installed(earlier) if earlier else None
    names1 = set(z1.namelist()) if z1 else set()
    newest = os.path.basename(earlier[-1]).replace('.zip', '') if earlier else None
    top = {n.split('/')[0] for n in names}
    exe_too = True
    want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 6:
        want_top.remove('INSTALL_TO_data')        # v7: executables only
    if len(earlier) == 9:
        want_top = ['INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA']   # v9.1: data only (v9's exes stay)
    if len(earlier) == 10:
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 11:   # v11: the release exe is v10's (not shipped)
        want_top = ['INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 19:   # v15: the release exe and data, test exes and data
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (20, 21, 26):   # skeleton v1.2 / burn v2 / skeleton v1.3: the exes, the data, test exes
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (23, 24, 25, 27, 28):   # burn v2.2 / v2.3 / aerial chain v1 / clone fixes v1 / trail fix: data only
        want_top = ['INSTALL_TO_data', 'README.txt']
    if len(earlier) == 29:   # skeleton v1.4: data, the clone joint test data and the TEST_ONLY exes (S4SV); the release
        want_top = ['INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']   # exe is v1.3's
    if len(earlier) == 22:   # burn v2.1: the exes only (the floor is the exe's)
        want_top = ['INSTALL_TO_code', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 18:   # v14: exes and test data only
        want_top = ['INSTALL_TO_code', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 12:   # v12: TEST_ONLY exes only (the release and the data are v11's)
        want_top = ['README.txt', 'TEST_ONLY_INSTALL_TO_code']
    check('the package\'s top level: %s (+ Sm4shCommand)' % ', '.join(want_top),
          sorted(t for t in top if not t.startswith('Sm4shCommand_v')), want_top)
    want, same1 = [], []
    for root, _ds, fs in os.walk(os.path.join(out, 'fighter')):
        for f in fs:
            w = 'INSTALL_TO_data/' + os.path.relpath(os.path.join(root, f), out)
            if z1 and w in names1 and z1.read(w) == open(os.path.join(out, w[len('INSTALL_TO_data/'):]), 'rb').read():
                same1.append(w)
            else:
                want.append(w)
    check('every built file that isn\'t already in v1 as it is: in INSTALL_TO_data (%d)' % len(want),
          sorted(w for w in want if w not in names), [])
    same = [w for w in want if z.read(w) != open(os.path.join(out, w[len('INSTALL_TO_data/'):]), 'rb').read()]
    check('... byte for byte', same, [])
    if z1:
        again = {'INSTALL_TO_data/fighter/gekkouga/model/skeleton/c00/skeleton.lvd'} if len(earlier) == 29 else set()   # skeleton v1.4: the box skeleton.lvd again on purpose (it
        # replaces skeleton v1.1's TEST_ONLY floor-only one the user had installed)
        check('update: none of the installed unchanged files again (%d unchanged)%s' % (len(same1), ', but skeleton.lvd' if again
              else ''), [w for w in same1 if w in names and w not in again], [])
        check('update: nothing in INSTALL_TO_data but the built files',
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/') and n not in want and
                     n not in again), [])
        if len(earlier) in (18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29):
            check('update: no Sm4shCommand (no script or slot changed)', [t for t in top if t.startswith('Sm4shCommand_v')], [])
        elif len(earlier) == 21:
            check('burn v2: Sm4shCommand v1.7.28 (the fire trail\'s three script names in ModAnimNames.txt)',
                  ([t for t in top if t.startswith('Sm4shCommand_v')],
                   z.read('Sm4shCommand_v1.7.28/ModAnimNames.txt') == open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand',
                                                                                         'ModAnimNames.txt'), 'rb').read()),
                  (['Sm4shCommand_v1.7.28'], True))
        elif len(earlier) == 17:
            check('skeleton v1: Sm4shCommand v1.7.27 (its three script names in ModAnimNames.txt)',
                  ([t for t in top if t.startswith('Sm4shCommand_v')],
                   z.read('Sm4shCommand_v1.7.27/ModAnimNames.txt') == open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand',
                                                                                         'ModAnimNames.txt'), 'rb').read()),
                  (['Sm4shCommand_v1.7.27'], True))
        else:
            check('update: no Sm4shCommand (no script or slot changed)', [t for t in top if t.startswith('Sm4shCommand_v')], [])
    if z1 and len(earlier) == 1:
        v2new = ['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/clone/clone.mscsb'] + \
                ['fighter/gekkouga/motion/clone/%s' % f for f in GB.CLONE_MOTION_PACS if f != 'main.pac'] + \
                ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in GB.CLONE_FACE_FILES]
        check('v2: both MSCs, his 5 motion part pacs, the face / rest-of-model files in all 8 colours (%d)' % len(v2new),
              [m for m in v2new if 'INSTALL_TO_data/' + m not in names], [])
    if z1 and len(earlier) == 17:
        check('skeleton v1: INSTALL_TO_data: his MSC, the skeleton\'s MSC, scripts, motion and model (with skeleton.lvd)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb',
                      'fighter/gekkouga/motion/skeleton/main.pac', 'fighter/gekkouga/model/skeleton/c00/skeleton.lvd'] +
                     ['fighter/gekkouga/script/animcmd/weapon/skeleton/%s' % f for f in ('game.bin', 'effect.bin', 'sound.bin',
                                                                                         'motion.mtable')] +
                     ['fighter/gekkouga/model/skeleton/c00/%s' % f for f in GB.SK_CARRIER]))
    if z1 and len(earlier) == 19:
        check('v15: INSTALL_TO_data: c00-c07 model.nud only (his own: the tongue / water on their swing bones)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted('fighter/gekkouga/model/clone/c%02d/model.nud' % c for c in range(8)))
        check('v15: ... = v14\'s TEST_ONLY_DATA/sway model.nud (what the user ran E_sway with)',
              [c for c in range(8) if z.read('INSTALL_TO_data/fighter/gekkouga/model/clone/c%02d/model.nud' % c) !=
               z1.read('TEST_ONLY_DATA/sway/fighter/gekkouga/model/clone/c%02d/model.nud' % c)], [])
        tdo = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        want_td = sorted(['TEST_ONLY_DATA/rigid/fighter/gekkouga/model/clone/c%02d/model.nud' % c for c in range(8)] +
                         ['TEST_ONLY_DATA/skeleton_floor_only/fighter/gekkouga/model/skeleton/c00/skeleton.lvd'])
        check('v15: TEST_ONLY_DATA: rigid (the stiff tongue: the fallback), skeleton_floor_only', tdo, want_td)
        check('v15: ... each as built and rigid = v14\'s', ([n for n in want_td if z.read(n) != open(os.path.join(out, n), 'rb').read()],
              [c for c in range(8) if z.read('TEST_ONLY_DATA/rigid/fighter/gekkouga/model/clone/c%02d/model.nud' % c) !=
               z1.read('TEST_ONLY_DATA/rigid/fighter/gekkouga/model/clone/c%02d/model.nud' % c)]), ([], []))
    if z1 and len(earlier) == 20:
        check('skeleton v1.2: INSTALL_TO_data: his effect bank (.ptcl / .efc: the flipbooks) and the skeleton\'s MSC',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.efc', 'fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl',
               'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb'])
    if z1 and len(earlier) in (23, 24):
        check('burn v2.2 / v2.3: INSTALL_TO_data: his effect bank (+ the ring of flames) and his body / the clone\'s effect.bin '
              '(neutral air\'s ring in place of v2\'s two flames)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.efc',
                      'fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl',
                      'fighter/gekkouga/script/animcmd/body/effect.bin',
                      'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin']))
    if z1 and len(earlier) == 25:
        check('aerial chain v1: INSTALL_TO_data: his MSC (the aerial chain, the charge\'s dust / sparkle at size 1, the clones\' '
              'places delayed) and the clone\'s MSC (its playback delayed)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/clone/clone.mscsb', 'fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 29:
        check('skeleton v1.4: INSTALL_TO_data: the box skeleton.lvd (walls + top), the clone\'s main.pac (no TransN movement), '
              'the trail\'s game.bin (up smash\'s hitboxes on its flames), his MSC (the clone diag)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/model/skeleton/c00/skeleton.lvd', 'fighter/gekkouga/motion/clone/main.pac',
               'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
               'fighter/gekkouga/script/animcmd/weapon/firetrail/game.bin', 'fighter/gekkouga/script/msc/gekkouga.mscsb'])
        td = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        check('skeleton v1.4: TEST_ONLY_DATA: the clone\'s game / effect.bin with his joint 25 on its right hand '
              '(clone_sword_rhave) or ThrowN as before (clone_sword_thrown), byte for byte as built',
              [(n, z.read(n) == open(os.path.join(out, n), 'rb').read()) for n in td],
              [('TEST_ONLY_DATA/%s/fighter/gekkouga/script/animcmd/weapon/clone/%s' % (t, f), True)
               for t in ('clone_sword_rhave', 'clone_sword_thrown') for f in ('effect.bin', 'game.bin')])
        import lvd as LV
        with tempfile.TemporaryDirectory() as td_:
            lp = os.path.join(td_, 'skeleton.lvd')
            open(lp, 'wb').write(z.read('INSTALL_TO_data/fighter/gekkouga/model/skeleton/c00/skeleton.lvd'))
            c = LV.LVD(lp).collisions[0]
        check('skeleton v1.4: skeleton.lvd: one collision, 4 vertices up the left side, across the top, down the right (x +- 6, '
              'y 2 / 28), normals out of the solid (left wall -X, the top +Y, right wall +X: each the line\'s direction '
              'turned counter-clockwise, as the hydrant\'s floor), no drop-through',
              ([list(map(float, v)) for v in c.verts], [list(map(float, n)) for n in c.normals], len(c.mats)),
              ([[-6.0, 2.0], [-6.0, 28.0], [6.0, 28.0], [6.0, 2.0]], [[-1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], 3))
    if z1 and len(earlier) == 28:
        check('fire trail fix v1: INSTALL_TO_data: the trail\'s MSC (its flames along X) and his effect bank (the fires\' soft '
              'bases)', sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl', 'fighter/gekkouga/script/msc/firetrail/firetrail.mscsb'])
    if z1 and len(earlier) == 27:
        check('clone fixes v1: INSTALL_TO_data: the clone\'s MSC (its effects ended on a new move) and effect.bin (every '
              'motion\'s effect requests)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/weapon/clone/effect.bin', 'fighter/gekkouga/script/msc/clone/clone.mscsb'])
    if z1 and len(earlier) == 26:
        check('skeleton v1.3: INSTALL_TO_data: his effect bank (the runs born on time, the burn tiers\' fires, forward air\'s '
              'blade flames), his body game.bin (the rolls\' roll-off speed) and effect.bin (forward air), the clone\'s '
              'effect.bin (forward air), his MSC (roll-off air x 1.24, uncapped)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.efc',
                      'fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl',
                      'fighter/gekkouga/script/animcmd/body/effect.bin', 'fighter/gekkouga/script/animcmd/body/game.bin',
                      'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin',
                      'fighter/gekkouga/script/msc/gekkouga.mscsb']))
    if z1 and len(earlier) == 22:
        check('burn v2.1: no INSTALL_TO_data (the 1 %% floor is the exe\'s shielded damage table)',
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')), [])
    if z1 and len(earlier) == 21:
        check('burn v2: INSTALL_TO_data: his MSC, his body and the clone\'s effect.bin (the flames at his water\'s ends), his '
              'effect bank (the fire sets), the fire trail\'s files (model / motion / scripts / MSC)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/animcmd/body/effect.bin',
                      'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin',
                      'fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.efc',
                      'fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl',
                      'fighter/gekkouga/script/msc/firetrail/firetrail.mscsb', 'fighter/gekkouga/motion/firetrail/main.pac'] +
                     ['fighter/gekkouga/script/animcmd/weapon/firetrail/%s' % f for f in ('game.bin', 'effect.bin', 'sound.bin',
                                                                                          'motion.mtable')] +
                     ['fighter/gekkouga/model/firetrail/c00/%s' % f for f in GB.SK_CARRIER]))
    if z1 and len(earlier) == 18:
        check('v14: no INSTALL_TO_data (the rigid-tongue release data stays)',
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')), [])
        tdo = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        want_td = sorted(['TEST_ONLY_DATA/sway/fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8)
                          for f in ('model.nud', 'model.sb')] +
                         ['TEST_ONLY_DATA/rigid/fighter/gekkouga/model/clone/c%02d/model.nud' % c for c in range(8)] +
                         ['TEST_ONLY_DATA/skeleton_floor_only/fighter/gekkouga/model/skeleton/c00/skeleton.lvd'])
        check('v14: TEST_ONLY_DATA: sway (his own model.nud / model.sb: the tongue on its own bones) and rigid (the release\'s '
              'model.nud back)', tdo, want_td)
        check('v14: ... each as built', [n for n in want_td if z.read(n) != open(os.path.join(out, n), 'rb').read()], [])
        check('v14: rigid = the installed release model.nud',
              [c for c in range(8) if z.read('TEST_ONLY_DATA/rigid/fighter/gekkouga/model/clone/c%02d/model.nud' % c) !=
               z1.read('INSTALL_TO_data/fighter/gekkouga/model/clone/c%02d/model.nud' % c)], [])
    if z1 and len(earlier) == 13:
        check('v13: INSTALL_TO_data: his MSC only (a fallen clone\'s heartbeat loss reported 401 / 402)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 11:
        check("v11: INSTALL_TO_data: c00-c07 model.nud (v9.1's) / model.sb (his own)",
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted('fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in ('model.nud', 'model.sb')))
        tdo = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        want_td = sorted('TEST_ONLY_DATA/sway/fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8)
                         for f in ('model.nud', 'model.sb'))
        check('v11: TEST_ONLY_DATA: sway (his own model.nud / model.sb)', tdo, want_td)
        check('v11: ... each as built', [n for n in want_td if z.read(n) != open(os.path.join(out, n), 'rb').read()], [])
    if z1 and len(earlier) == 10:
        check("v10: INSTALL_TO_data: the merged main.pac, c00-c07 model.nud (own bones) / model.sb (tongue unswung)",
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/motion/clone/main.pac'] +
                     ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in ('model.nud', 'model.sb')]))
        tdo = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        want_td = sorted(['TEST_ONLY_DATA/v91_rigid/fighter/gekkouga/motion/clone/main.pac'] +
                         ['TEST_ONLY_DATA/%s/fighter/gekkouga/model/clone/c%02d/%s' % (d, c, f) for c in range(8)
                          for d, f in (('v91_rigid', 'model.nud'), ('v91_rigid', 'model.sb'), ('original_model_sb', 'model.sb'))])
        check('v10: TEST_ONLY_DATA: the v9.1 set (v91_rigid), his original model.sb', tdo, want_td)
        check('v10: ... each as built', [n for n in want_td if z.read(n) != open(os.path.join(out, n), 'rb').read()], [])
    if z1 and len(earlier) == 9:
        check("v9.1: INSTALL_TO_data: his own main.pac / model.sb back (v8's), c00-c07 model.nud rebound to main.pac's bones",
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/motion/clone/main.pac'] +
                     ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in ('model.nud', 'model.sb')]))
        tdo = sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))
        want_td = sorted(['TEST_ONLY_DATA/merged_main_pac/fighter/gekkouga/motion/clone/main.pac'] +
                         ['TEST_ONLY_DATA/%s/fighter/gekkouga/model/clone/c%02d/%s' % (d, c, f) for c in range(8)
                          for d, f in (('empty_model_sb', 'model.sb'), ('original_model_nud', 'model.nud'))])
        check('v9.1: TEST_ONLY_DATA: v9\'s merged main.pac, v9\'s empty model.sb, the original model.nud',
              tdo, want_td)
        check('v9.1: ... each as built', [n for n in want_td if n in names and
                                          z.read(n) != open(os.path.join(out, n), 'rb').read()], [])
    if z1 and len(earlier) == 8:
        check("v9: INSTALL_TO_data: the clone's main.pac (full-body motions) and c00-c07 model.nud / model.sb",
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              sorted(['fighter/gekkouga/motion/clone/main.pac'] +
                     ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in ('model.nud', 'model.sb')]))
    if z1 and len(earlier) == 7:
        check('v8: INSTALL_TO_data: the clone\'s MSC only (its visibility: shown again after waiting for its id)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/clone/clone.mscsb'])
    if z1 and len(earlier) == 6:
        check('v7: no INSTALL_TO_data (no data file changed: the fixes are the executable\'s)',
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')), [])
    if z1 and len(earlier) == 5:
        check('v6: INSTALL_TO_data: his MSC only (the "being made" bit for the last-made clone only)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 4:
        check('v5: INSTALL_TO_data: his MSC only (the clones\' heartbeat grace, removal reasons, the request frame)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 3:
        check('v4: INSTALL_TO_data: his body game.bin (hitboxes x5), the clone\'s game / effect.bin, his MSC',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/body/game.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin',
               'fighter/gekkouga/script/animcmd/weapon/clone/game.bin', 'fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 2:
        check('v3: INSTALL_TO_data is both MSCs and his body effect.bin (the smash effects x5; the rest is v1 / v2\'s)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/body/effect.bin', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
               'fighter/gekkouga/script/msc/gekkouga.mscsb'])
    must = ['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
            'fighter/gekkouga/script/animcmd/body/game.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
            'fighter/gekkouga/motion/clone/main.pac', 'fighter/kirby/script/msc/kirby.mscsb'] + \
           ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in GB.CLONE_MODEL_FILES]
    check('the files the mod needs (with the earlier packages under it)', [m for m in must if 'INSTALL_TO_data/' + m not in names | names1], [])
    with tempfile.TemporaryDirectory() as td:
        import gekkouga_clone_cave as C
        for i, (member, b, dg, feats) in enumerate(exe_members(base, base_diag, len(earlier) >= 3, len(earlier) == 17,
                                                               len(earlier) == 18, len(earlier) >= 19, len(earlier) in (19, 20),
                                                               len(earlier) == 21, len(earlier) in (22, 23, 24, 25),
                                                               len(earlier) in (26, 27, 28, 29))):
            if not b:
                continue
            p = os.path.join(td, '%d.rpx' % i)
            a = C.args(b, dg, feats)
            subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), b, p] + a, check=True, stdout=subprocess.DEVNULL)
            if member not in names and z1 and len(earlier) >= 8:
                check('v9: %s: none in this package; the installed one (%s) is the cave rebuilt from the script (features %s)'
                      % (member, newest, ','.join(sorted(feats)) or 'safe'), z1.read(member) == open(p, 'rb').read(), True)
                continue
            check('%s is the cave on its base (features %s), rebuilt from the script' % (member, ','.join(sorted(feats)) or 'safe'),
                  z.read(member) == open(p, 'rb').read(), True)
            if z1 and member in names1:
                check('%s differs from %s\'s' % (member, newest), z.read(member) != z1.read(member), True)
    readme = z.read('README.txt').decode('utf8', 'replace')
    words = ('300', '720', '480', 'swap', 'chain', 'Technical') if not z1 else \
        ('greninja_clones_v1', 'hitlag', 'fall', 'face', 'hand', 'exe_v46z_gk2', 'swap', 'blast') if len(earlier) == 1 else \
        ('greninja_clones_v2', 'hurtbox', 'wall', 'ceiling', 'slope', 'blast zone', 'hitlag', 'exe_v46z_gk3', 'swap', '120',
         '5x', 'S4GF', 'S4GC', 'S4GU', 'Final Smash') if len(earlier) == 2 else \
        ('greninja_clones_v3', 'hitbox', '5x', 'sword', 'offset', 'clone', 'exe_v46z_gk4', 'Hitbox Viewer', 'A_safe',
         'B_template', 'C_hurt', 'D_full', 'S4GP', 'GX2R', 'crash') if len(earlier) == 3 else \
        ('greninja_clones_v4', 'exe_v46z_gk5', 'A_safe', 'B_attack', 'C_hurt', 'D_parts', 'S4GV', 'gen=', 'heartbeat',
         'moon', 'pump') if len(earlier) == 4 else \
        ('greninja_clones_v5', 'exe_v46z_gk6', 'black', 'id=1', 'S4GX', 'A_safe', 'B_attack', 'C_hurt', 'D_parts',
         'damage panel', 'Little Mac', 'S4GB', 'grey') if len(earlier) == 5 else \
        ('greninja_clones_v6', 'exe_v46z_gk7', 'scale', 'S4GZ', 'S4GW', 'name tag', '0-100', 'A_safe', 'B_attack', 'round',
         'data/ui/info/dmg') if len(earlier) == 6 else \
        ('greninja_clones_v7', 'exe_v46z_gk8', 'clone.mscsb', 'VisibilityModule', 'S4GM', 'S4GN', 'A_safe', 'E_bstart',
         'bunshin', 'black', 'object id') if len(earlier) == 7 else \
        ('greninja_clones_v8', 'exe_v46z_gk9', 'main.pac', 'model.nud', 'model.sb', 'tongue', 'water', 'swing',
         'A_attack', 'C_hurt', 'D_parts', 'name tag', '0x100FCC00', 'S4GK', 'S4GO', 'confirmed') if len(earlier) == 8 else \
        ('greninja_clones_v9', 'freeze', 'model.sb', 'main.pac', 'model.nud', 'TEST_ONLY_DATA', 'merged_main_pac',
         'empty_model_sb', 'original_model_nud', 'exe_v46z_gk9', 'confirmed') if len(earlier) == 9 else         ('greninja_clones_v9_1', 'exe_v46z_gk10', 'tongue', 'model.sb', 'main.pac', 'model.nud', 'TEST_ONLY_DATA',
         'v91_rigid', 'original_model_sb', 'A_attack', 'C_hurt', 'D_parts', 'name tag', '0x2B75', 'S4GU', 'S4GO',
         'sway', 'confirmed') if len(earlier) == 10 else         ('greninja_clones_v10', 'exe_v46z_gk11', 'tongue', 'model.sb', 'model.nud', 'TEST_ONLY_DATA', 'E_sway', 'sway',
         'S4GQ', 'S4GY', 'S4GO', 'C_hurt', 'name tag', 'confirmed') if len(earlier) == 11 else \
        ('greninja_clones_v11', 'exe_v46z_gk12', 'F_hitcheck', 'E_sway', 'S4GH', 'S4GR', 'crash', 'TEST_ONLY_DATA/sway',
         'Lyn', 'Ghirahim', 'confirmed') if len(earlier) == 12 else \
        ('greninja_clones_v12', 'exe_v46z_gk13', 'hit check', 'projectile', 'item', 'hitlag', 'A_release', 'D_parts',
         'E_sway', 'S4GR', 'S4GH', '401', 'confirmed', 'TEST_ONLY_DATA/sway') if len(earlier) not in (17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29) else \
        ('greninja_clones_v15', 'exe_v46z_gks2', 'collision', '0x02AC2EF0', 'S4CD', 'flipbook', '28', '44', 'mirror',
         'impact', 'explosion', 'smoke', 'A_release', 'G_pose', 'unconfirmed', '32 cells', 'hydrant') if len(earlier) == 20 else \
        ('greninja_skeleton_v1_2', 'exe_v46z_gkb4', 'fire', 'trail', '0.25', '15', '180', '3 %', '35', 'shield', 'tip',
         'sword', 'neutral air', 'up smash', 'clone', 'S4BF', 'S4TR', 'Sm4shCommand_v1.7.28', 'A_release', 'G_pose',
         'unconfirmed', 'knockback') if len(earlier) == 21 else \
        ('greninja_burn_v2', 'exe_v46z_gkb5', '1 %', '2.8', '0.945', '0.525', '6.3', '16', '5.4', '36', 'shield',
         'lower', 'A_release', 'G_pose', 'unconfirmed') if len(earlier) == 22 else \
        ('greninja_burn_v2_1', 'neutral air', 'ring', '15', 'flames', 'edge', '1.45', 'clone', 'preview', 'unconfirmed',
         'exe_v46z_gkb5') if len(earlier) == 23 else \
        ('greninja_burn_v2_2', 'neutral air', 'ring', '15', 'outward', 'fire_small_4', 'fire_small_5', 'fire_torch_012',
         'fire_torch_026', 'fire_ground_10', 'facing left', 'jitter', 'clone', 'preview', 'unconfirmed', 'exe_v46z_gkb5') \
        if len(earlier) == 24 else \
        ('greninja_burn_v2_3', 'aerial', 'chain', 'hit', 'shield', 'once', 'land', 'clone', 'dust', 'sparkle', 'size 1',
         'sword', '1 frame', '2 frames', 'hitlag', 'swap', 'S4GF', 'unconfirmed', 'exe_v46z_gkb5') if len(earlier) == 25 else \
        ('greninja_aerialchain_v1', 'exe_v46z_gkb6', 'blink', 'collision', 'tier', 'stack', 'forward air', 'blade', 'roll',
         '2.5', '1.24', 'A_release', 'G_pose', 'S4SD', 'unconfirmed', 'burn_tiers.png', 'fair.png') if len(earlier) == 26 else \
        ('greninja_skeleton_v1_3', 'up air', 'grab', 'down air', 'smash', 'charge', 'shuriken', 'forward air', 'back air',
         'walk', 'unconfirmed', 'exe_v46z_gkb6') if len(earlier) == 27 else \
        ('greninja_clonefix_v1', 'axis', 'down smash', 'up smash', 'forward smash', 'interpretation', 'bottom', 'trails.png',
         'unconfirmed', 'exe_v46z_gkb6') if len(earlier) == 28 else \
        ('greninja_firetrail_fix_v1', 'skeleton.lvd', 'floor-only', 'walls', 'S4SV', 'A_release', 'TransN', 'snap', 'S4GF',
         'gen=', 'up smash', 'unconfirmed', 'exe_v46z_gkb6') if len(earlier) == 29 else \
        ('greninja_skeleton_v1', 'exe_v46z_gk14', 'tongue', 'water', 'A_release', 'E_sway', 'S4TP', 'S4GQ', 'S4GR',
         'TEST_ONLY_DATA/sway', 'TEST_ONLY_DATA/rigid', 'crash', '+0x10', 'unconfirmed', 'S4SD', 'S4SE', 'S4SG',
         'skeleton_floor_only', 'collision') if len(earlier) == 18 else \
        ('greninja_clones_v14', 'exe_v46z_gk15', 'confirmed in game: native swing (v14 E_sway)', 'tongue', 'water',
         'A_release', 'G_pose', 'TEST_ONLY_DATA/rigid', 'skeleton_floor_only', 'S4SD', 'unconfirmed') if len(earlier) == 19 else \
        ('greninja_burn_v1_2', 'exe_v46z_gks1', 'Running Skeleton', '25', '180', '0.7', 'ledge', 'smoke', 'explo', '36',
         '6.3', 'S4SS', 'S4SH', 'S4SX', 'S4SC', 'S4SF', 'hydrant', 'placeholder', 'Sm4shCommand_v1.7.27', 'unconfirmed')
    check('README.txt mentions every feature (%s)' % ', '.join(words), [w for w in words if w not in readme], [])
    check('no fighter- or game-named wrapper folder', [t for t in top if t.lower() in ('gekkouga', 'greninja', 'fighter', 'data', 'smash4')], [])


def exe_members(base, base_diag, v4, skeleton=False, v14=False, v15=False, sk12=False, b2=False, gkb5=False, gkb6=False):
    """(member, base, diag, features): v4+ ships the safe release exe and a TEST_ONLY exe per variant; skeleton v1 the
    release and TEST_ONLY A_release (as the burn packages)"""
    import gekkouga_clone_cave as C
    sk1 = frozenset(('attack', 'hitcheck', 'burn', 'skeleton'))
    if skeleton:
        return [('INSTALL_TO_code/cross_f.rpx', base, False, sk1),
                ('TEST_ONLY_INSTALL_TO_code/A_release/cross_f.rpx', base_diag, True, sk1)]
    if v14:     # (v14's sets: its release had the pose copy; its exes are v14's code, v15's code differs in nothing)
        return [('INSTALL_TO_code/cross_f.rpx', base, False, sk1 | {'pose'}),
                ('TEST_ONLY_INSTALL_TO_code/A_release/cross_f.rpx', base_diag, True, sk1 | {'pose'}),
                ('TEST_ONLY_INSTALL_TO_code/E_sway/cross_f.rpx', base_diag, True, sk1 | {'sway'})]
    if v15:     # (v15 and skeleton v1.2 (sk12): RELEASE without burn v2's burn2; burn v2 on: RELEASE)
        drop = {'burn2', 'floor1'} if sk12 else {'floor1'} if b2 else set()
        drop |= {'tiers', 'gmupd'} if sk12 or b2 or gkb5 else set()   # (skeleton v1.3's exe_v46z_gkb6 adds them)
        drop |= {'skbody', 'sktouch'} if sk12 or b2 or gkb5 or gkb6 else set()   # (skeleton v1.5's gkb7)
        return [('INSTALL_TO_code/cross_f.rpx', base, False, C.RELEASE - drop)] + \
            [('TEST_ONLY_INSTALL_TO_code/%s/cross_f.rpx' % n, base_diag, True, f - drop) for n, f in C.VARIANTS]
    if not v4:
        return [('INSTALL_TO_code/cross_f.rpx', base, False, C.FEATURES), ('TEST_ONLY_INSTALL_TO_code/cross_f.rpx', base_diag, True, C.FEATURES)]
    return [('INSTALL_TO_code/cross_f.rpx', base, False, C.RELEASE)] + \
        [('TEST_ONLY_INSTALL_TO_code/%s/cross_f.rpx' % n, base_diag, True, f) for n, f in C.VARIANTS]


def tool_tests(out, base, base_diag, pkg, v4=False, earlier=()):
    import gekkouga_clone_cave as C
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone', 'c00')
    bm = GB.bone_map(open(os.path.join(mdl, 'model.jtb'), 'rb').read(), os.path.join(mdl, 'model.vbn'))
    check('v3: the clone hurtboxes\' bones are his hurtbox joints as the article\'s (gekkouga_build.bone_map, model.jtb)',
          [C.WEAPON_JOINT + h[7] for h in C.HURTBOXES], [bm(h[7]) for h in C.HURTBOXES])
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    for f, src in ((os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c')),
                   (os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC),
                   (os.path.join(msc, 'skeleton', 'skeleton.mscsb'), GB.SKELETON_MSC),
                   (os.path.join(msc, 'firetrail', 'firetrail.mscsb'), GB.TRAIL_MSC)):
        if not os.path.exists(f):
            continue
        r = subprocess.run([sys.executable, os.path.join(HERE, 'msc_stack_check.py'), f, src], capture_output=True, text=True)
        lines = r.stdout.strip().splitlines()
        m = re.search(r'globals: (\d+) of 128', r.stdout)
        check('msc_stack_check %s: 0 stack problems, globals %s <= 128' % (os.path.basename(f), m.group(1) if m else '?'),
              (lines[-2].startswith('0 of') if len(lines) > 1 else False, bool(m) and int(m.group(1)) <= 128), (True, True))
    z = zipfile.ZipFile(pkg)
    with tempfile.TemporaryDirectory() as td:
        for member, b, dg, feats in exe_members(base, base_diag, v4, len(earlier) == 17, len(earlier) == 18,
                                                len(earlier) >= 19, len(earlier) in (19, 20), len(earlier) == 21,
                                                len(earlier) in (22, 23, 24, 25), len(earlier) in (26, 27, 28, 29)):
            if not b:
                continue
            p = os.path.join(td, 'x.rpx')
            if member not in z.namelist():
                if not earlier:
                    continue
                open(p, 'wb').write(Installed(earlier).read(member))   # v9: data only: the installed v8 exe
            else:
                open(p, 'wb').write(z.read(member))
            r = subprocess.run([sys.executable, os.path.join(HERE, 'import_call_check.py'), b, p], capture_output=True, text=True)
            check('import_call_check %s: 0 direct import calls' % member, r.stdout.strip().splitlines()[-1:], ['0 direct import call(s)'])
            r = subprocess.run([sys.executable, os.path.join(HERE, 'gekkouga_clone_cave_test.py'), b, p,
                                '--features=' + ','.join(sorted(feats))] + (['--diag'] if dg else []), capture_output=True, text=True)
            last = r.stdout.strip().splitlines()[-1:]
            check('the cave\'s unicorn test on %s: %s' % (member, last[0] if last else '?'),
                  bool(last) and last[0].endswith(' 0 failures'), True)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--v')]
    earlier = [x[len('--v%s=' % k):] for k in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '91', '10', '11', '12', '13', 'b1',
                                               'b11', 'b12', 's1', '14', '15', 's12', 'b2', 'b21', 'b22', 'b23', 'ac', 's13', 'cf', 'ft') for x in sys.argv[1:]
               if x.startswith('--v%s=' % k)]
    v1 = None
    out, pkg, user, base = a[0], a[1], a[2], a[3]
    base_diag = a[4] if len(a) > 4 else None
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    msc_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    physics_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    aerial_chain_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    delay_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_delay_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    clone_fx_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC, out)
    ground_move_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out)
    if os.path.exists(os.path.join(msc, 'skeleton', 'skeleton.mscsb')):
        skeleton_side_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        skeleton_tests(os.path.join(msc, 'skeleton', 'skeleton.mscsb'), GB.SKELETON_MSC)
        skeleton_data_tests(out)
    if os.path.exists(os.path.join(msc, 'firetrail', 'firetrail.mscsb')):
        trail_side_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        firetrail_tests(os.path.join(msc, 'firetrail', 'firetrail.mscsb'), GB.TRAIL_MSC)
        trail_data_tests(out)
    script_tests(out, user)
    package_tests(out, pkg, base, base_diag, v1, earlier)
    model_tests(out, earlier)
    tool_tests(out, base, base_diag, pkg, len(earlier) >= 3, earlier)
    kirby = open(os.path.join(ROOT, 'fighters', 'kirby', 'kirby.c')).read()
    check('Kirby\'s copy of Greninja (0x30): Technical', 'if (kind == 0x30) { return trait_technical(); } // Greninja' in kirby, True)
    traits = open(os.path.join(ROOT, 'docs', 'character-traits.md')).read()
    check('docs/character-traits.md: Greninja 0x30 Technical', '| Greninja (`gekkouga`) | `0x30` | Technical |' in traits, True)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
