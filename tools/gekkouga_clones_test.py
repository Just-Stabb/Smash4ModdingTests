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
        self.line_tests = 0

    def line_test(self):
        """the Line_Test variables: a vertical segment (X0, Y0) -> (X0, Y1) down, the highest floor it meets"""
        self.line_tests += 1
        x, y0, y1 = (self.vars.get(0x0F0003D0 + i, 0.0) for i in (0, 1, 3))
        hit = [fy for x0, x1, fy in self.floors if x0 <= x <= x1 and y1 <= fy <= y0]
        if hit:
            self.vars[0x0F0003D4], self.vars[0x0F0003D7], self.vars[0x0F0003D8] = 1.0, max(hit), 1.0
        else:
            self.vars[0x0F0003D4], self.vars[0x0F0003D7], self.vars[0x0F0003D8] = 0.0, y1, 0.0

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


def frames(m, n, st=0):
    m.vm.g[4] = st
    for _ in range(n):
        m.game.press = set()
        m('gekkouga_frame')


def msc_tests(mscsb, src):
    # ---- the charge: accumulation, kept, threshold
    m = fresh(mscsb, src)
    g = m.game
    check('constants: 300 / 720 / 480 / gap 14 / smash full 60 / growth 1.5',
          (m('gk_lw_full'), m('gk_ability_frames'), m('gk_burnout_frames'), round(i2f(m('gk_gap') & 0xFFFFFFFF), 3),
           m('gk_smash_full'), round(i2f(m('gk_smash_grow') & 0xFFFFFFFF), 3)), (300, 720, 480, 14.0, 60, 1.5))
    r = m('gk_lw_press')
    check('down special, not charged: the stance (status 0x155)', (r, g.status_req), (1, [(0x155, 1)]))
    g.status_req = []
    m('gk_lw_main')
    for _ in range(99):
        m('gk_lw_tick')
    check('100 frames held: charge 100', m.g('gk_lw_charge'), 100)
    pips = [x for x in g.log if x[0] == 'effect' and x[1] == 0x2712]
    check('the bar: 3 pips lit (one a 30 frames), the pip effect 0x1000047 over his head',
          [(x[2], x[5]) for x in pips], [(0x1000047, 25.0)] * 3)
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
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 0: the left clone (article 6) made, VAR_31 = 4747000 + alive 1 + being made (left) 4, its smoke at X - 14',
          (arts, g.vars.get(0x0F00031F), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
          ([('article', 0x2710, 6)], 4747005.0, [36.0]))
    check('v2: the ability hides his name tag (the cursor op BattleObject(0xA, 0))', [x for x in g.log if x[0] == 'cursor'],
          [('cursor', 0)])
    frames(m, 3)
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 3: the right clone (article 7), VAR_31 = 4747000 + 3 + being made (right) 8, its smoke at X + 14',
          (arts[-1], g.vars.get(0x0F00031F), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006][-1]),
          (('article', 0x2710, 7), 4747011.0, 64.0))
    check('flags: tag hidden + clones out (5)', g.vars.get(0x0F000314), 5.0)
    g.motion, g.frame, g.rate = 0x5F, 7.0, 1.0
    frames(m, 2)
    check('v2 channel: left clone X / Y 36 / 10, right 64 / 10, frame 7, rate 1, motion 0x5F, 4747000 + alive 3',
          [g.vars.get(0x0F000318 + i) for i in range(8)], [36.0, 10.0, 64.0, 10.0, 7.0, 1.0, 95.0, 4747003.0])
    check('the capsules: shapes 1 (-14) and 2 (+14) on, 0 / 3 off', g.shapes, {0: 0, 1: 1, 2: 1, 3: 0})
    g.lr = -1.0
    frames(m, 1)
    check('facing left: the same clones are at z +14 / -14 (shapes 2 / 1)', g.shapes, {0: 0, 1: 1, 2: 1, 3: 0})
    g.lr = 1.0
    m.vm.g[4] = 0x74
    m('gekkouga_frame')
    check('on a ledge (0x74, CliffWait): the clones play Wait1 / Fall', g.vars.get(0x0F00031E), 0.0)
    g.situation = 2
    m.vm.g[4] = 0x46
    m('gekkouga_frame')
    check('v2: hit in the air (0x46): standing clones Wait1 (they stay where they are; a falling one plays Fall)',
          g.vars.get(0x0F00031E), 0.0)
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
    # ---- a clone hit: the nearest (dx -12 -> the left one at -14)
    frames(m, 1)
    g.log = []
    g.posture_sets = []
    g.vars[0x0F000315] = 10000.0 - 12.0
    xh, g.rand = g.x, 0.5
    frames(m, 1)
    check('a hit at dx -12: the left clone (-14) gone (article 6 removed), its smoke, the log (0x3F7) at its place, him back',
          ([x for x in g.log if x[0] in ('article', 'battleobject')], g.posture_sets, g.x, m.g('gk_alive'), g.vars.get(0x0F000315)),
          ([('article', 0x2712, 6), ('battleobject', 0x3F7, xh - 14.0, 10.0)], [(xh - 14.0, 10.0), (xh, 10.0)], xh, 2, 0.0))
    check('the capsules: only the right clone\'s (-28: shape 0)', g.shapes, {0: 1, 1: 0, 2: 0, 3: 0})
    check('the channel: alive 2', g.vars.get(0x0F00031F), 4747002.0)
    g.press, g.stick = {1}, (-0.8, -0.8)
    xs = g.x
    frames(m, 10)
    g.press, g.stick = {1}, (-0.8, -0.8)
    m('gekkouga_frame')
    check('swap with the dead left clone: nothing', g.x, xs)
    g.log = []
    g.rand = 0.05
    g.vars[0x0F000315] = 10000.0 + 5.0
    frames(m, 1)
    check('a hit with the right clone the only one: it (0x2712 7), the rare doll (0x3F8: rand 0.05 <= 10%)',
          [x[:3] for x in g.log if x[0] in ('article', 'battleobject')], [('article', 0x2712, 7), ('battleobject', 0x3F8, xs - 28.0)])
    check('no clones: flags tag only (1), the capsules off', (g.vars.get(0x0F000314), g.shapes), (1.0, {0: 0, 1: 0, 2: 0, 3: 0}))
    # ---- the ability's end, the burnout
    left = m.g('gk_ability')
    g.log = []
    frames(m, left)
    check('the ability ran 720 frames in all, then the burnout 480', (m.g('gk_ability'), m.g('gk_burnout')), (0, 480))
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
    m2.setg('gk_s4', 33)
    frames(m2, 1, st=0xB2)
    check('the smash charges survive a KO / respawn', (m2.g('gk_s4'), m2.g('gk_lw_charge')), (33, 120))
    frames(m2, 1, st=0x14F)
    check('the match\'s start (Entry 0x14F): every charge from 0', (m2.g('gk_s4'), m2.g('gk_lw_charge')), (0, 0))

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
    check('30 hold frames: forward smash charge 30 (up / down untouched)', (m.g('gk_s4'), m.g('gk_hi4'), m.g('gk_lw4')), (30, 0, 0))
    g.held = set()
    check('released before full: Wait (no attack), the charge kept', (m('gk_sm_hold_loop', 1), g.status_req, m.g('gk_s4')), (1, [(0, 0)], 30))
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
    check('30 + 40 frames: capped at 60', m.g('gk_s4'), 60)
    check('full while held: ready (flash), Wait, no attack', (m('gk_sm_hold_loop', 1), g.status_req, m.g('gk_s4')), (1, [(0, 0)], 60))
    g.status_req = []
    m.vm.g[4] = 0x2B
    m('gk_sm_start_main', 1)
    check('the next forward smash: automatic (1)', m.g('gk_sm_auto'), 1)
    g.held = set()
    r = m('gk_sm_start_loop', 1)
    check('at the hold point, not even held: the attack (0x2D, keep), ratio 1.0, charged flag, the store used, chain = forward',
          (r, g.status_req, g.vars.get(0x1000000), 0x21000002 in g.flags, m.g('gk_s4'), m.g('gk_chain')),
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
    m.setg('gk_hi4', 25)
    m('gk_sm_start_main', 2)
    check('the chained up smash: automatic (2), its own store untouched', (m.g('gk_sm_auto'), m.g('gk_hi4')), (2, 25))
    r = m('gk_sm_start_loop', 2)
    check('its release: 0x33, chain forward + up, store kept', (g.status_req, m.g('gk_chain'), m.g('gk_hi4')), ([(0x33, 1)], 3, 25))
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
    # down smash out of run: the same start status (0x2E), so the same rules
    m3 = fresh(mscsb, src)
    m3.game.held = {0}
    m3.game.flags.add(0x2100001B)
    m3('gk_sm_start_main', 4)
    m3('gk_sm_start_loop', 4)
    check('a down smash (out of a run too: its start status 0x2E): charges like any', m3.game.status_req, [(0x2F, 1)])


def physics_tests(mscsb, src):
    """v2: the clones' own fall (ledge, a lower floor, max fall speed), a jump with him, a platform drop, a launch, the
    fall off the stage; his hitlag from their hits; the freeze in hitlag"""
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
    check('v2 constants: gravity 0.18, max fall 1.85 (his fighter_param), fall-off 100 frames, snap 3, hitlag min 4',
          (round(i2f(fresh(mscsb, src)('gk_gravity') & 0xFFFFFFFF), 3), round(i2f(fresh(mscsb, src)('gk_max_fall') & 0xFFFFFFFF), 3),
           fresh(mscsb, src)('gk_fall_frames'), round(i2f(fresh(mscsb, src)('gk_snap') & 0xFFFFFFFF), 3),
           fresh(mscsb, src)('gk_hitlag_min')), (0.18, 1.85, 100, 3.0, 4))
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
    check('... only the left clone\'s capsule (the right one is out of formation)', g.shapes, {0: 0, 1: 1, 2: 0, 3: 0})
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
    check('... no capsules, standing: Wait1', (g.shapes, g.vars.get(0x0F00031E)), ({0: 0, 1: 0, 2: 0, 3: 0}, 0.0))
    g.x, g.y, g.situation = 60.0, 10.0, 0
    g.floors = [(-1000.0, 1000.0, 10.0)]
    g.log = []
    frames(m, 1, st=0)
    check('he is back (60, 10): the clones back in formation (46 / 74), a smoke each',
          (cl(m), len([x for x in g.log if x[0] == 'effect' and x[2] == 0x3300006])), ((46.0, 10.0, 74.0, 10.0), 2))
    check('... the capsules back on', g.shapes, {0: 0, 1: 1, 2: 1, 3: 0})
    # ---- off the stage: no floor under them: falling on their own 100 frames -> gone in smoke, no log
    m, g = start(0.0, 10.0, [])
    g.log = []
    frames(m, 94)
    check('nothing under them: the left clone 100 frames falling (made 6 frames before): still there', m.g('gk_alive'), 3)
    frames(m, 1)
    check('its 101st: the left one gone (article 6 removed), its smoke, no Substitution log',
          ([x for x in g.log if x[0] in ('article', 'battleobject')], len([x for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
           m.g('gk_alive')), ([('article', 0x2712, 6)], 1, 2))
    frames(m, 3)
    check('the right one (made 3 frames later) 3 frames later; the ability goes on',
          ([x for x in g.log if x[0] in ('article', 'battleobject')][-1], m.g('gk_alive'), m.g('gk_ability') > 0),
          (('article', 0x2712, 7), 0, True))
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
    g.vars[0x0F000315] = 10000.0 + 14.0
    frames(m, 1)
    check('a hit at a clone place while both clones fell (out of formation: their capsules off): nobody',
          (m.g('gk_alive'), g.shapes), (alive, {0: 0, 1: 0, 2: 0, 3: 0}))
    # ---- a swap to a clone below him: he goes to its X and Y
    m, g = start(0.0, 10.0, [(-30.0, 10.0, 10.0), (10.0, 60.0, -10.0)])
    frames(m, 20)
    x0 = g.x
    g.press, g.stick = {1}, (0.8, -0.8)
    m('gekkouga_frame')
    check('v2 swap with the right clone standing lower (14, -10): him to (14, -10), it to his place (0, 10)',
          (g.x, g.y, m.gf('gk_rx'), m.gf('gk_ry')), (14.0, -10.0, 0.0, 10.0))


def clone_tests(mscsb, src):
    m = MSC(mscsb, src)
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
    shared(2, 6, float(0x5F))
    shared(2, 4, 5.0)
    shared(2, 5, 1.0)
    g.x, g.y, g.lr = 98.0, 0.0, 1.0
    m('cl_frame')
    check('the clone finds him (slot 2, the nearest with the magic), which clone from his "being made" bit (8: the right one)',
          (m.g('cl_slot'), m.g('cl_id')), (2, 2))
    check('v2: its place his MSC\'s (VAR_26 / 27: 114, -6.5: it stands / falls there)', (g.x, g.y), (114.0, -6.5))
    check('v2: its VAR_0 = his slot (the executable\'s hit method gives him its hits\' hitlag)', g.vars.get(0x0F000300), 2.0)
    check('faces his way (-1, then the model turned)', [x for x in g.log if x[0] in ('lr', 'posture')][-2:], [('lr', -1.0), ('posture', 2)])
    check('his motion 0x5F (VAR_30) from his frame 5 at his rate', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 5.0, 1.0)])
    g.log = []
    shared(2, 4, 6.0)
    shared(2, 7, 4747000.0 + 3)
    g.frame = 6.0
    m('cl_frame')
    check('the next frame: the same motion, his rate (no restart); the bit gone, it is still the right one',
          ([x for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'rate'], m.g('cl_id')), ([], [('rate', 1.0)], 2))
    shared(2, 4, 9.0)
    g.frame = 6.5
    g.log = []
    m('cl_frame')
    check('behind him (its own hitlag): back on his frame', [x for x in g.log if x[0] == 'setframe'], [('setframe', 9.0)])
    shared(2, 5, 0.0)
    g.log = []
    m('cl_frame')
    check('v2: his hitlag (rate 0): it freezes', [x for x in g.log if x[0] == 'rate'], [('rate', 0.0)])
    shared(2, 5, 1.0)
    shared(2, 4, 0.0)
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
    shared(2, 6, 0.0)
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
    m3 = MSC(mscsb, src)
    g3 = m3.game
    sh.clear()
    shared(2, 7, 4747000.0 + 1)
    shared(2, 0, 86.0)
    g3.sys = lambda sid, a, f=sysf: f(sid, a)
    m3.game.sys = g.sys
    m3('cl_frame')
    check('v2: no "being made" bit: no id yet (waits)', (m3.g('cl_slot'), m3.g('cl_id')), (0, 0))
    shared(2, 7, 4747000.0 + 1 + 4)
    m3('cl_frame')
    check('v2: ... the left bit (4): the left one, at VAR_24 / 25', (m3.g('cl_slot'), m3.g('cl_id'), g.x), (2, 1, 86.0))


def script_tests(out, user):
    O = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    ug = acmd.ACMDFile.load(os.path.join(user, 'body', 'game.bin'))
    ue = acmd.ACMDFile.load(os.path.join(user, 'body', 'effect.bin'))
    pg = acmd.ACMDFile.load(os.path.join(O, 'body', 'game.bin'))
    pe = acmd.ACMDFile.load(os.path.join(O, 'body', 'effect.bin'))
    smash = {zlib.crc32(n.encode()) for n in GB.SMASH_SCRIPTS}
    bad, n = [], 0
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
                    grow = crc in smash and nm == 'Size' and (c0.name in GB.HITBOXES or kind == 'effect')
                    want = round(float(p0) * 1.5, 4) if grow else p0
                    if grow:
                        n += 1
                    if (abs(float(p1) - float(want)) > 1e-3) if grow else (p1 != p0):
                        bad.append((kind, hex(crc), c0.name, nm, p0, p1))
    check('his smash scripts: every hitbox / effect Size x1.5, nothing else of his changed', (bad[:3], n > 20), ([], True))
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
    check('the clone has his forward smash, his jab, his up air (the loop)',
          all(zlib.crc32(n.encode()) in cg.scripts for n in ('attacks4', 'attack11', 'attackairhi')), True)
    mt0 = open(os.path.join(user, 'body', 'motion.mtable'), 'rb').read()
    mt1 = open(os.path.join(O, 'weapon', 'clone', 'motion.mtable'), 'rb').read()
    check('the clone\'s motion.mtable is his (668 motions)', (mt1 == mt0, len(mt1) // 4), (True, 668))


def package_tests(out, pkg, base, base_diag, v1=None):
    """the package; with v1 (greninja_clones_v1.zip) the package is an update over it: only the files that differ"""
    z = zipfile.ZipFile(pkg)
    names = set(z.namelist())
    z1 = zipfile.ZipFile(v1) if v1 else None
    names1 = set(z1.namelist()) if z1 else set()
    top = {n.split('/')[0] for n in names}
    check('the package\'s top level: README.txt, INSTALL_TO_data, INSTALL_TO_code, TEST_ONLY_INSTALL_TO_code (+ Sm4shCommand)',
          sorted(t for t in top if not t.startswith('Sm4shCommand_v')),
          ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code'])
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
        check('v2 update: none of v1\'s unchanged files again (%d unchanged)' % len(same1), [w for w in same1 if w in names], [])
        check('v2 update: nothing in INSTALL_TO_data but the built files',
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/') and n not in want), [])
        check('v2 update: no Sm4shCommand (no script or slot changed)', [t for t in top if t.startswith('Sm4shCommand_v')], [])
        v2new = ['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/clone/clone.mscsb'] + \
                ['fighter/gekkouga/motion/clone/%s' % f for f in GB.CLONE_MOTION_PACS if f != 'main.pac'] + \
                ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in GB.CLONE_FACE_FILES]
        check('v2: both MSCs, his 5 motion part pacs, the face / rest-of-model files in all 8 colours (%d)' % len(v2new),
              [m for m in v2new if 'INSTALL_TO_data/' + m not in names], [])
    must = ['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
            'fighter/gekkouga/script/animcmd/body/game.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
            'fighter/gekkouga/motion/clone/main.pac', 'fighter/kirby/script/msc/kirby.mscsb'] + \
           ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in GB.CLONE_MODEL_FILES]
    check('the files the mod needs (with v1 under it)', [m for m in must if 'INSTALL_TO_data/' + m not in names | names1], [])
    with tempfile.TemporaryDirectory() as td:
        for nm, b in (('gk', base), ('gkd', base_diag)):
            if not b:
                continue
            p = os.path.join(td, nm + '.rpx')
            import gekkouga_clone_cave as C
            a = C.args(b, nm == 'gkd')
            subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), b, p] + a, check=True, stdout=subprocess.DEVNULL)
            member = ('INSTALL_TO_code' if nm == 'gk' else 'TEST_ONLY_INSTALL_TO_code') + '/cross_f.rpx'
            check('%s is the cave on its base, rebuilt from the script' % member, z.read(member) == open(p, 'rb').read(), True)
            if z1:
                check('%s differs from v1\'s' % member, z.read(member) != z1.read(member), True)
    readme = z.read('README.txt').decode('utf8', 'replace')
    words = ('300', '720', '480', 'swap', 'chain', 'Technical') if not z1 else \
        ('greninja_clones_v1', 'hitlag', 'fall', 'face', 'hand', 'exe_v46z_gk2', 'swap', 'blast')
    check('README.txt mentions every feature (%s)' % ', '.join(words), [w for w in words if w not in readme], [])
    check('no fighter- or game-named wrapper folder', [t for t in top if t.lower() in ('gekkouga', 'greninja', 'fighter', 'data', 'smash4')], [])


def tool_tests(out, base, base_diag, pkg):
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    for f, src in ((os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c')),
                   (os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'msc_stack_check.py'), f, src], capture_output=True, text=True)
        lines = r.stdout.strip().splitlines()
        m = re.search(r'globals: (\d+) of 128', r.stdout)
        check('msc_stack_check %s: 0 stack problems, globals %s <= 128' % (os.path.basename(f), m.group(1) if m else '?'),
              (lines[-2].startswith('0 of') if len(lines) > 1 else False, bool(m) and int(m.group(1)) <= 128), (True, True))
    z = zipfile.ZipFile(pkg)
    with tempfile.TemporaryDirectory() as td:
        for member, b in (('INSTALL_TO_code/cross_f.rpx', base), ('TEST_ONLY_INSTALL_TO_code/cross_f.rpx', base_diag)):
            if not b:
                continue
            p = os.path.join(td, 'x.rpx')
            open(p, 'wb').write(z.read(member))
            r = subprocess.run([sys.executable, os.path.join(HERE, 'import_call_check.py'), b, p], capture_output=True, text=True)
            check('import_call_check %s: 0 direct import calls' % member, r.stdout.strip().splitlines()[-1:], ['0 direct import call(s)'])
            r = subprocess.run([sys.executable, os.path.join(HERE, 'gekkouga_clone_cave_test.py'), b, p] +
                               (['--diag'] if b == base_diag else []), capture_output=True, text=True)
            last = r.stdout.strip().splitlines()[-1:]
            check('the cave\'s unicorn test on %s: %s' % (member, last[0] if last else '?'),
                  bool(last) and last[0].endswith(' 0 failures'), True)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--v1=')]
    v1 = [x[5:] for x in sys.argv[1:] if x.startswith('--v1=')]
    v1 = v1[0] if v1 else None
    out, pkg, user, base = a[0], a[1], a[2], a[3]
    base_diag = a[4] if len(a) > 4 else None
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    msc_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    physics_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    script_tests(out, user)
    package_tests(out, pkg, base, base_diag, v1)
    tool_tests(out, base, base_diag, pkg)
    kirby = open(os.path.join(ROOT, 'fighters', 'kirby', 'kirby.c')).read()
    check('Kirby\'s copy of Greninja (0x30): Technical', 'if (kind == 0x30) { return trait_technical(); } // Greninja' in kirby, True)
    traits = open(os.path.join(ROOT, 'docs', 'character-traits.md')).read()
    check('docs/character-traits.md: Greninja 0x30 Technical', '| Greninja (`gekkouga`) | `0x30` | Technical |' in traits, True)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
