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
   across releases, the 300-frame threshold, the bar's pips), the ability (840 frames: the clones made at 0 / 3 with
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
import gekkouga_clone_cave as CC  # noqa: E402

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
        self.tap_jump = True       # smash tune v1: ControlModule(0x271C): his Tap Jump setting (the game's default on)

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
            if a[0] == 0x271C:
                return int(self.tap_jump)
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
            if a[0] == 0x2728:
                self.log.append(('power', fv(a[1])))          # smash tune v1: the attack's power (func_345)
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
    check('constants: 300 / 840 (usmash spike v2 / trail dim v1: 14 s; 720 before) / 480 / gap 14 / smash full 120 (v3) / hitbox growth 5 (v4)',
          (m('gk_lw_full'), m('gk_ability_frames'), m('gk_burnout_frames'), round(i2f(m('gk_gap') & 0xFFFFFFFF), 3),
           m('gk_smash_full'), round(i2f(m('gk_smash_grow') & 0xFFFFFFFF), 3)), (300, 840, 480, 14.0, 120, 5.0))
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
          (r, g.status_req, m.g('gk_ability'), m.g('gk_lw_charge')), (0, [], 840, 0))
    g.held = set()                        # (clone fix v3: the activating press let go: the kick armed after the lockout)
    g.x = 50.0
    frames(m, 1)
    check('v4: frame 0: the left clone requested (flags + 64: the TEST_ONLY exe logs it before the generate), none made yet',
          ([x for x in g.log if x[0] == 'article'], int(g.vars.get(0x0F000314)) & 0xC0), ([], 0x40))
    frames(m, 1)
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 1: the left clone (article 6) made, VAR_31 = 4747000 + alive 1 + being made (left) 4, its smoke at X - 14',
          (arts, g.vars.get(0x0F00031F), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
          ([('article', 0x2710, 6)], 4747005.0, [36.0]))
    check('v6: the gauge in the ability: mode 2, 839 / 840 left -> 99', g.vars.get(0x0F000313), 2099.0)
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
    check('on a ledge (0x74, CliffWait): tuning v1: the clones act (split: free mode, flags 128; tuning_tests); back in '
          'formation after his ledge (the regroup)', int(g.vars.get(0x0F00031F)) - 4747000 & 0x80, 0x80)
    frames(m, 1)
    frames(m, 80)
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
    g.vars[0x0F0003C9] = 0
    m.vm.g[24] = 0x8000
    m('gekkouga_frame')
    check('aligned kick v1: plain down special (no left / right): no swap, not cleared (the buffer, the special bits: the '
          'game\'s input goes on)', (g.x, g.status_req, g.vars.get(0x0F0003C9), m.vm.g[24] & 0xF000), (x2, [], 0, 0x8000))
    r = m('gk_lw_press')
    check('aligned kick v1: the input sites during the ability: the aligned kick (0x161), no stance', (r, g.status_req),
          (1, [(0x161, 1)]))
    g.status_req = []
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
    check('the channel: alive 2 (aligned kick v1 package: + 256 the effects epoch, flipped at his landing in formation)',
          (int(g.vars.get(0x0F00031F)) - 4747000) & 0xFF, 2)
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
    check('the ability ran 840 frames in all, then the burnout 480', (m.g('gk_ability'), m.g('gk_burnout')), (0, 480))
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
    check('KO (0xB1): the clones removed, no burnout, the channel closed (parabeetle v1: no Parabeetle can be out, no '
          'cooldown: nothing asked for article 10)',
          ([x for x in m2.game.log if x[0] == 'article'], m2.g('gk_ability'), m2.g('gk_burnout'), m2.game.vars.get(0x0F00031F)),
          ([('article', 0x2712, 6), ('article', 0x2712, 7)], 0, 0, 0.0))
    m2.setg('gk_burnout', 100)
    frames(m2, 1, st=0xB2)
    check('respawn (0xB2): the burnout ended', m2.g('gk_burnout'), 0)
    m2.setg('gk_lw_charge', 120)
    frames(m2, 1, st=0xB1)
    check('aligned kick v1 package (the user: "the clone charge gauge should reset when Greninja is KO\'d"): the charge '
          'back to 0 at a KO (v1 - burn tint v1: kept)', m2.g('gk_lw_charge'), 0)
    m2.setg('gk_lw_charge', 120)
    m2.setg('gk_smash', 33)
    frames(m2, 1, st=0xB2)
    check('clone articles v1 package (the user: a KO clears the stored smash charge too; v1 - aligned kick v1: kept): the '
          'smash charge 0 after a KO / respawn, the down special\'s 0', (m2.g('gk_smash'), m2.g('gk_lw_charge')), (0, 0))
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
    check('at the hold point, not even held: the attack (0x2D, keep), charged flag, the store used, chain = forward; '
          'smash tune v1: ratio 0 (was 1.0: the uncharged damage)',
          (r, g.status_req, g.vars.get(0x1000000), 0x21000002 in g.flags, m.g('gk_smash'), m.g('gk_chain')),
          (1, [(0x2D, 1)], 0.0, True, 0, 1))
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
    check('v5: past the 120-frame grace + 3 misses: both dropped, the reason in VAR_23 (101 then 102: heartbeat; clone fix '
          'v3: + 1000 x its place, mod 1000)', (m.g('gk_alive'), int(g.vars.get(0x0F000317)) % 1000), (0, 102))
    v = int(g.vars.get(0x0F000317)) // 1000
    check('clone fix v3: ... its last place in the reason (x 1000: X/10 + 40 + 81 x (Y/10 + 40)): the right clone at '
          '(14, 10) -> X 10, Y 10 (to 10s)', ((v % 81 - 40) * 10, (v // 81 - 40) * 10), (10, 10))
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
          and x[2] == 0x3300006]), int(g.vars.get(0x0F000317)) % 1000, m.g('gk_alive')), ([('article', 0x2712, 6)], 1, 401, 2))
    m, g = start(0.0, 10.0, [(-1000.0, 1000.0, 10.0)])
    frames(m, 10)
    g.beat = 2
    frames(m, 3)
    check('v13: ... standing on the floor when its heartbeat stops: 101 as before', int(g.vars.get(0x0F000317)) % 1000, 101)
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


def ak_setup(mscsb, src):
    """aligned kick v1: him at x 0 on the floor (y 10) with both clones out (x -14 / +14), formation; his kinetics logged
    (KineticModule 0x11: energy 1 his Y speed, 3 his X) and FighterUtil 6 (his rotation)"""
    m = fresh(mscsb, src)
    g = m.game
    g.kin, g.rot = {}, []

    def sysf(sid, a, old=g.sys):
        if sid == 0x10 and a[0] == 0x11:
            g.kin[a[1]] = fv(a[2])
            return 0
        if sid == 0xC and a[0] == 0x6:
            g.rot.append(fv(a[1]))
            return 0
        if sid == 0x12 and a[0] == 0x4:
            g.log.append(('rate', fv(a[1])))
            return 0
        if sid == 0xE and a[0] == 0xA:
            return 0
        return old(sid, a)
    g.sys = sysf
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    g.x, g.y = 0.0, 10.0
    frames(m, 12)
    g.status_req = []
    return m, g


def ak_frame(m, g, st=0x161, held=False, press=(), stick=(0.0, 0.0), cmd=0, atk=False, guard=False):
    """one frame: his per-frame hook (gekkouga_frame), then (in his kick status) its tick, then his kinetics applied"""
    m.vm.g[4] = st
    m.vm.g[24] = cmd
    g.press = set(press)
    g.held = ({1} if held else set()) | ({0} if atk else set()) | ({3} if guard else set())
    g.stick = stick
    g.vars[0x0F00031E] = float(m.g('gk_alive') & g.beat)
    g.kin = {}
    m('gekkouga_frame')
    if st == 0x161:
        m('gk_ak_tick')
        g.x = round(g.x + g.kin.get(3, 0.0), 3)
        g.y = round(g.y + g.kin.get(1, 0.0), 3)
        g.situation = 2 if g.y > 10.001 else 0


def ak_cmd(g, c):
    """clone c's command in the channel (VAR_28 / VAR_29): (kind, start frame, facing left, tilted, paused, seq)"""
    v = int(g.vars.get(0x0F00031B + c, 0.0) + 0.5)
    return (v % 1024, (v // 1024) % 1024, (v >> 20) & 1, (v >> 21) & 1, (v >> 22) & 1, (v >> 23) & 1)


def aligned_kick_tests(mscsb, src):
    """aligned kick v1 (README "Aligned kick v1"): the trigger, the startup (all three still, the clones' delays skipped),
    both variants' trajectories, his higher peak, the swap mid-move (place and momentum), the end in Fall, once an
    airtime, the channel's commands"""
    # ---- the trigger
    m, g = ak_setup(mscsb, src)
    check('aligned kick: clones out in formation at -14 / +14, his Y 10, the mode 0',
          (m.gf('gk_lx'), m.gf('gk_rx'), m.gf('gk_ly'), int(g.vars.get(0x0F000388, 0))), (-14.0, 14.0, 10.0, 0))
    g.press, g.stick = {1}, (-0.8, -0.8)
    m.vm.g[4], m.vm.g[24] = 0, 0x8000
    m('gekkouga_frame')
    check('down special + left: still the silent swap (no status)', (g.status_req, round(g.x, 3)), ([], -14.0))
    m, g = ak_setup(mscsb, src)
    for st, air in ((0, 0), (0xE, 2)):
        g.situation = air
        r = m('gk_lw_press')
        check('down special with no left / right, %s: the aligned kick (his SpecialLwAttack slot 0x161)' %
              ('standing' if not air else 'in the air'), (r, g.status_req), (1, [(0x161, 1)]))
        g.status_req = []
    g.situation = 0
    # ---- the move: its main (the counter's up-diagonal kick, rotated straight up), the startup
    g.log = []
    m.vm.g[4] = 0x161
    m('gk_ak_main')
    check('its main: the kick motion (0x28D) at 5/8 (the startup: 8 frames to its kick frame 5), turned straight up '
          '(FighterUtil 6, 270), the up-diagonal hitboxes\' flag 0x2100001C on, the clones kicking (mode 1, the kick used)',
          ([x for x in g.log if x[0] == 'rate'][:1], g.rot[:1], 0x2100001C in g.flags, int(g.vars.get(0x0F000388)),
           int(g.vars.get(0x0F000389)), int(g.vars.get(0x0F000390, 0))),
          ([('rate', 0.625)], [270.0], True, 1, 1, 12))
    ak_frame(m, g)
    c1, c2 = ak_cmd(g, 1), ak_cmd(g, 2)
    check('the channel: free (flags 128); each clone the kick motion 0x28D paused on the startup\'s frame, tilted along its '
          'flight, facing the centre line (the left one right, the right one left): their delays skipped (aligned)',
          (int(g.vars.get(0x0F00031F)) - 4747000 & 0x80, c1[:5], c2[:5]), (0x80, (0x28D, 0, 0, 1, 1), (0x28D, 0, 1, 1, 1)))
    for _ in range(4):
        ak_frame(m, g)
    check('the startup: frame 5 of 8: his place, the clones\' still; their motion on frame 5 x 5/8 = 3',
          (g.x, g.y, m.gf('gk_lx'), m.gf('gk_ly'), m.gf('gk_rx'), ak_cmd(g, 1)[1]), (0.0, 10.0, -14.0, 10.0, 14.0, 3))
    return m, g


def ak_run(mscsb, src, held, swap_at=None, frames_=60):
    """the whole move from the press, held or tapped; [(his x, y), left (x, y), right (x, y)] each frame"""
    m, g = ak_setup(mscsb, src)
    m('gk_lw_press')
    m.vm.g[4] = 0x161
    m('gk_ak_main')
    g.status_req = []
    track = []
    st = 0x161
    for t in range(1, frames_):
        press, stick = (), (0.0, 0.0)
        if swap_at is not None and t == swap_at:
            press, stick = (1,), (-0.8, -0.8)
        ak_frame(m, g, st=st, held=held and t <= 8, press=press, stick=stick)
        m.vm.g[19], m.vm.g[18] = m.vm.g.get(18, 0), g.situation      # (the system line's situation globals)
        if st == 0x161 and m('gk_ak_loop'):
            st = g.status_req[-1][0]
            m('gk_ak_end')
        track.append(((g.x, g.y), (m.gf('gk_lx'), m.gf('gk_ly')), (m.gf('gk_rx'), m.gf('gk_ry'))))
    return m, g, track


def aligned_kick_more_tests(mscsb, src):
    res = {}
    for held in (False, True):
        m, g, tr = ak_run(mscsb, src, held, frames_=24)
        res[held] = (m, g, tr)
    m, g, tr = res[False]
    hy = [p[0][1] for p in tr]
    ly = [p[1][1] for p in tr]
    lx = [p[1][0] for p in tr]
    rx = [p[2][0] for p in tr]
    check('tapped (special let go before the kick): variant 1; the flights from the kick frame (8): him straight up, 78 in '
          '15 frames (5.2 a frame), x still', (int(g.vars.get(0x0F00038B)), round(hy[7] - hy[6], 3), round(hy[21] - 10.0, 3),
                                                {p[0][0] for p in tr}), (1, 5.2, 78.0, {0.0}))
    check('tapped: the left clone up-right (53 degrees), the right one up-left, 64 along their diagonals: they cross above '
          'him and end 24.5 past the centre line (-14 -> +24.5, +14 -> -24.5), 51.1 up',
          (round(lx[21], 1), round(rx[21], 1), round(ly[21] - 10.0, 1), lx[12] > rx[12]), (24.5, -24.5, 51.1, True))
    check('his peak clearly above theirs (> 20 higher)', round(max(hy) - max(ly), 1) > 20, True)
    m, g, tr = res[True]
    lx = [p[1][0] for p in tr]
    rx = [p[2][0] for p in tr]
    ly = [p[1][1] for p in tr]
    hy = [p[0][1] for p in tr]
    check('held through the startup: variant 2; shorter flights (46.5): they end at the spawn spacing on the other side '
          '(+14 / -14), 37.1 up; his still 78',
          (int(g.vars.get(0x0F00038B)), round(lx[21], 1), round(rx[21], 1), round(ly[21] - 10.0, 1), round(hy[21] - 10.0, 1)),
          (2, 14.0, -14.0, 37.1, 78.0))
    # ---- the end: Fall (not a free fall), split; their fall
    m, g, tr = ak_run(mscsb, src, False, frames_=24)
    check('the move\'s end (23 frames): Fall (0xE, not a free fall 0x10); upright again (FighterUtil 6, 0 at its end)',
          (g.status_req[-1:], g.rot[-1:]), ([(0xE, 0)], [0.0]))
    check('the clones split (mode 2) once both flights are over, in the air, upright (their tilt off)',
          (int(g.vars.get(0x0F000388)), m('gk_bvi', 1, 0), m('gk_bvi', 2, 0), ak_cmd(g, 1)[3], ak_cmd(g, 2)[3]), (2, 10, 10, 0, 0))
    # ---- the swap mid-flight: his path and the clone's exchanged
    m, g, tr = ak_run(mscsb, src, False, swap_at=12, frames_=24)
    hx = [p[0][0] for p in tr]
    lx = [p[1][0] for p in tr]
    check('swap at flight frame 5 (down special + left): he takes the left clone\'s place and its momentum (on up-right: '
          'x grows 2.57 a frame), it takes his (straight up from his old place: x still)',
          (round(hx[12] - hx[11], 2), round(lx[12] - lx[11], 2), round(tr[11][0][0] - tr[10][1][0], 2)),
          (2.57, 0.0, 2.57))
    # ---- once an airtime
    m, g, tr = ak_run(mscsb, src, False, frames_=30)
    g.status_req = []
    m.vm.g[4], g.situation = 0xE, 2
    m('gekkouga_frame')
    r = m('gk_lw_press')
    check('once an airtime: again in the air: nothing', (r, g.status_req), (0, []))
    g.situation = 0
    m.vm.g[4] = 0
    m('gekkouga_frame')
    r = m('gk_lw_press')
    check('... landed: again', (r, g.status_req), (1, [(0x161, 1)]))


def split_tests(mscsb, src):
    """aligned kick v1: split clones mirror his inputs, each in its own situation (README "Aligned kick v1"): aerials by
    its own facing, landing (no regroup), ground walk / dash / run, jab, tilts, smashes (hold, charge, auto release, chain),
    jumps; shield + special: his short call (0x160) and their slow walk / float back, then formation"""
    m, g, tr = ak_run(mscsb, src, True, frames_=24)        # held: they end at +14 / -14 (crossed), in the air
    check('split: after the kick, mode 2, both in the air (action 10)', (int(g.vars.get(0x0F000388)), m('gk_bvi', 1, 0),
                                                                       m('gk_bvi', 2, 0)), (2, 10, 10))
    g.status_req = []
    # an aerial: his forward air command (0x100, him facing right): the left clone (now right of him, facing right as it
    # flew) a forward air, the right one (facing left) a back air
    ak_frame(m, g, st=0xE, cmd=0x100 | 0x1, stick=(0.8, 0.0))
    check('split, in the air: his forward air command: the clone facing his way a forward air (0x69), the one facing '
          'the other way a back air (0x6A), each its own (action 11)',
          (ak_cmd(g, 1)[0], ak_cmd(g, 2)[0], m('gk_bvi', 1, 0), m('gk_bvi', 2, 0)), (0x69, 0x6A, 11, 11))
    for _ in range(200):
        ak_frame(m, g, st=0xE)
        if m('gk_bvi', 1, 0) < 10 and m('gk_bvi', 2, 0) < 10:
            break
    check('split: they land on the floor (y 10) from their aerials: the aerials\' landing lag (forward 15 / back 13, '
          'LandingAirF / B 0x6E / 0x6F), and stay split (no regroup on landing: mode 2)',
          (m.gf('gk_ly'), m.gf('gk_ry'), sorted([ak_cmd(g, 1)[0], ak_cmd(g, 2)[0]]), int(g.vars.get(0x0F000388))),
          (10.0, 10.0, [0x6E, 0x6F], 2))
    for _ in range(16):
        ak_frame(m, g, st=0)
    check('split: after the landing lag: standing (Wait1, action 0)', (ak_cmd(g, 1)[0], m('gk_bvi', 1, 0)), (0, 0))
    # ground: walk, dash -> run, jab, tilt, smash with its hold / release, the stored charge, a chain, a jump
    x0 = m.gf('gk_lx')
    ak_frame(m, g, st=1, stick=(0.5, 0.0))
    check('split, ground: the stick half right: both walk right (WalkMiddle 0xB, 1.43 x 0.5 / 0.75 = 0.953 a frame, facing '
          'right)', (ak_cmd(g, 1)[0], ak_cmd(g, 2)[0], round(m.gf('gk_lx') - x0, 3), ak_cmd(g, 2)[2]), (0xB, 0xB, 0.953, 0))
    ak_frame(m, g, st=3, stick=(-1.0, 0.0))
    k1 = ak_cmd(g, 1)[0]
    for _ in range(10):
        ak_frame(m, g, st=4, stick=(-1.0, 0.0))
    check('split, ground: the stick full left: a dash (0x11, 1.6 a frame, facing left), then the run (0x12, 2.08)',
          (k1, ak_cmd(g, 1)[0], ak_cmd(g, 1)[2], round(m('gk_bv', 1, 6) and fv(m('gk_bv', 1, 6)), 2)), (0x11, 0x12, 1, -2.08))
    for _ in range(40):
        ak_frame(m, g, st=0)
    ak_frame(m, g, st=0x25, cmd=0x1)
    check('split, ground: a jab press: jab 1 (Attack11 0x50) for both', (ak_cmd(g, 1)[0], ak_cmd(g, 2)[0]), (0x50, 0x50))
    for _ in range(6):
        ak_frame(m, g, st=0x25)
    ak_frame(m, g, st=0x25, cmd=0x1)
    check('... pressed again (6 frames in): jab 2 (0x51)', ak_cmd(g, 1)[0], 0x51)
    for _ in range(40):
        ak_frame(m, g, st=0)
    ak_frame(m, g, st=0x29, cmd=0x4 | 0x1)
    check('split, ground: up tilt (0x4): AttackHi3 (0x5C)', ak_cmd(g, 1)[0], 0x5C)
    for _ in range(40):
        ak_frame(m, g, st=0)
    ak_frame(m, g, st=0x2B, cmd=0x10, stick=(1.0, 0.0), atk=True)
    k_start = ak_cmd(g, 1)[0]
    for _ in range(8):
        ak_frame(m, g, st=0x2C, atk=True)
    check('split, ground: a forward smash, attack held: its start (0x5F) to its hold frame (8), then the hold (0x62)',
          (k_start, ak_cmd(g, 1)[0], m('gk_bvi', 1, 0)), (0x5F, 0x62, 4))
    c8 = (ak_cmd(g, 1)[1], m('gk_bvi', 1, 10))
    for _ in range(30):
        ak_frame(m, g, st=0x2C, atk=True)
    check('clone fix v3: the hold\'s command carries its own charge in the start frame\'s place (the clone draws its charge '
          'effects): %s at the hold\'s start, then 30' % (c8,), (c8[0] == c8[1], ak_cmd(g, 1)[1], m('gk_bvi', 1, 10)),
          (True, 30, 30))
    ak_frame(m, g, st=0)
    check('... released before full (31 frames of 120): no attack, Wait1; its charge kept (31)',
          (ak_cmd(g, 1)[0], m('gk_bvi', 1, 10)), (0, 31))
    m('gk_bsi', 1, 10, 120)
    ak_frame(m, g, st=0x2B, cmd=0x20)
    s0 = ak_cmd(g, 1)
    for _ in range(9):
        ak_frame(m, g, st=0x31)
    check('split, ground: with a full stored charge an up smash (0x63) releases at its hold frame on its own: an attack, '
          'the charge used, the chain started (up); clone fix v3: its start motion plays on from 0 (no restart at the hold '
          'frame 9, which skipped his frame-9 swords / fire: same command, same seq)',
          (s0, ak_cmd(g, 1), m('gk_bvi', 1, 0), m('gk_bvi', 1, 10), m('gk_bvi', 1, 11), m('gk_bvi', 1, 0x1) + m('gk_bvi', 1, 3)),
          (s0, s0, 2, 0, 2, 9))
    for _ in range(14):
        ak_frame(m, g, st=0x33)
    ak_frame(m, g, st=0x33, cmd=0x40)
    check('... from its last hitbox\'s end (22) a down smash input chains (its start 0x65, auto)',
          (ak_cmd(g, 1)[0], m('gk_bvi', 1, 13)), (0x65, 4 + 16))
    for _ in range(80):
        ak_frame(m, g, st=0)
    ak_frame(m, g, st=0xA, cmd=0x200000)
    k = ak_cmd(g, 1)[0]
    for _ in range(5):
        ak_frame(m, g, st=0xB)
    check('split, ground: jump: the squat (0x18), then JumpF (0x19) rising (action 10)',
          (k, ak_cmd(g, 1)[0], m('gk_bvi', 1, 0), m.gf('gk_ly') > 10.0), (0x18, 0x19, 10, True))
    for _ in range(120):
        ak_frame(m, g, st=0)
    # the regroup: shield + special while split
    g.status_req = []
    g.x = 0.0
    lx0, rx0 = m.gf('gk_lx'), m.gf('gk_rx')
    m.vm.g[18] = 0                                # (standing: the situation global; usmash spike v2's air clear reads it)
    ak_frame(m, g, st=0x1C, press=(1,), guard=True)
    check('regroup: special pressed with shield held (Guard 0x1C): his short call (0x160), the special eaten',
          (g.status_req, g.vars.get(0x0F0003C9)), ([(0x160, 1)], 32.0))
    g.log = []
    m.vm.g[4], m.vm.g[18] = 0x160, 0
    m('gk_rg_main')
    check('his call: the start of his stance (speciallw 0x271) at 0.4 (its frames 0 - 7.6, before its intangible 8 - 19); '
          'the clones regrouping (mode 3)', ([x for x in g.log if x[0] == 'rate'][:1], int(g.vars.get(0x0F000388))),
          ([('rate', 0.4)], 3))
    xs = []
    for t in range(75):
        ak_frame(m, g, st=0x160 if t < 19 else 0)
        xs.append((m.gf('gk_lx'), m.gf('gk_rx')))
    step = max(abs(b[0] - a[0]) for a, b in zip([(lx0, rx0)] + xs, xs))
    check('regroup: they come back slowly (75 frames, eased: the biggest step %.2f a frame; not a teleport), walking '
          '(WalkMiddle 0xB) on his floor; then formation at -14 / +14 (mode 0)' % step,
          (step < 1.5, abs(xs[37][0] - lx0) < abs(-14.0 - lx0), xs[-1], int(g.vars.get(0x0F000388))),
          (True, True, (-14.0, 14.0), 0))
    ak_frame(m, g, st=0)
    check('regroup: formation again: VAR_28 his motion (kind x 1024 + frame), flags without 128',
          int(g.vars.get(0x0F00031F)) - 4747000 & 0x80, 0)


def usmash_trail_tests(mscsb, src, out, user, ice_clip=None):
    """usmash spike v2 / trail dim v1 (README): up smash's whole strong part a spike; the trails dimmer (the bank: its
    emitters' colour scale); the ice detonation's sound (the bank / table, the cut, his MSC's play / stop, no blast sound),
    the clones' ability 840 frames"""
    import acmd
    import fighter_own_bank as FB
    import gekkouga_clone_cave as C
    import gekkouga_sound as GS
    import minecraft_sound as MS
    import ptcl as P
    import gekkouga_fx as FX
    B = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    gm = acmd.ACMDFile.load(os.path.join(B, 'body', 'game.bin'))
    cg = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'game.bin'))
    ug = acmd.ACMDFile.load(os.path.join(user, 'body', 'game.bin'))
    pv = lambda c, n: c.params[c.info['syntax'].index(n)]   # noqa: E731

    def timeline(sc):
        fr, out_ = 0.0, []
        for c in sc:
            if c.name == 'FRAME':
                fr = float(c.params[0])
            if c.name in GB.HITBOXES:
                out_.append((fr, c))
        return out_
    mine = timeline(gm.scripts[acmd.crc('attackhi4')])
    users = timeline(ug.scripts[acmd.crc('attackhi4')])
    strong = [(f, c) for f, c in mine if GB.USMASH_STRONG[0] <= f < GB.USMASH_STRONG[1]]
    row = lambda c: (int(pv(c, 'ID')), int(pv(c, 'Part')), int(pv(c, 'Bone')), float(pv(c, 'Damage')), int(pv(c, 'Angle')),   # noqa: E731
                     int(pv(c, 'KBG')), int(pv(c, 'FKB')), int(pv(c, 'BKB')))
    bad = [row(c) for f, c in strong if (int(pv(c, 'Angle')), int(pv(c, 'KBG')), int(pv(c, 'FKB')), int(pv(c, 'BKB'))) !=
           (300, 50, 0, 25)]
    kb = lambda pc, d, kbg=50, bkb=25: round(((pc / 10.0 + pc * d / 20.0) * 1.4 + 18) * kbg / 100.0 + bkb, 1)   # noqa: E731
    check('usmash spike v2 (the user: "make all of the strong part of Up smash\'s hitbox do the spike"): the strong part is '
          'every hitbox his AttackHi4 sets at %d (the only setting frame from 15 to 21): the geyser (ID 0, Part 1, 14 %%, '
          'Y 27, off at 19) and the four sword hits (inner 1 / 2, outer 3 / 4, 11 %%, off at 21): frames %d - %d. Each now '
          'angle 300 (down and away, by position), KBG 50, FKB 0, BKB 25 (none with another angle or a bigger knockback); '
          'its damage its own (uncharged): KB at weight 100: geyser %.0f / %.0f / %.0f, swords %.0f / %.0f / %.0f at 0 / '
          '100 / 150 %%' % (GB.USMASH_STRONG[0], GB.USMASH_STRONG[0], GB.USMASH_STRONG[1] - 1, kb(14, 14), kb(114, 14),
                            kb(164, 14), kb(11, 11), kb(111, 11), kb(161, 11)),
          (sorted({f for f, _c in strong}), sorted(row(c) for f, c in strong), bad,
           max(int(pv(c, 'KBG')) for f, c in strong), max(int(pv(c, 'BKB')) for f, c in strong)),
          ([18.0], [(0, 1, 0, 14.0, 300, 50, 0, 25), (1, 1, 0x19, 11.0, 300, 50, 0, 25), (2, 1, 0x18, 11.0, 300, 50, 0, 25),
                    (3, 1, 0x19, 11.0, 300, 50, 0, 25), (4, 1, 0x18, 11.0, 300, 50, 0, 25)], [], 50, 25))
    before = [(f, row(c)) for f, c in mine if f < GB.USMASH_STRONG[0] or f >= GB.USMASH_STRONG[1]]
    ub = [(f, row(c)) for f, c in users if f < GB.USMASH_STRONG[0] or f >= GB.USMASH_STRONG[1]]
    check('usmash spike v2: left as they are (the user\'s script\'s values): the first weak hit (12: ID 0, Part 0, 5 %, angle '
          '366, KBG 120, BKB 30) before the strong part and the late capsule (21: ID 1, 10 %, angle 40, KBG 98, BKB 30) '
          'after it', before, ub)
    cs = timeline(cg.scripts[acmd.crc('attackhi4')])
    check('usmash spike v2: the clones\' copy the same (each strong hitbox 300 / KBG 50 / BKB 25, its damage x1.0; the weak '
          'hit and the late capsule as his)', sorted((f, row(c)[0], row(c)[3:]) for f, c in cs),
          sorted((f, row(c)[0], row(c)[3:]) for f, c in mine))
    sd = sorted((row(c)[0], float(pv(c, 'Damage')), int(pv(c, 'ShieldDamage')),
                 round((float(pv(c, 'Damage')) + int(pv(c, 'ShieldDamage'))) * 1.19 * C.SH_SCALE, 2)) for f, c in strong)
    check('usmash spike v2: shield damage still halved by the exe\'s shalf: it keys on his motion kind (99, up smash: '
          'SH_KINDS %s), not on the hitboxes, and their damage / ShieldDamage fields (0, never negative) are unchanged: '
          'shield HP %s' % (C.SH_KINDS, [x[3] for x in sd]), (99 in C.SH_KINDS, 'shalf' in C.RELEASE, [x[2] for x in sd]),
          (True, True, [0] * 5))
    # the trails
    pp = P.Ptcl(open(os.path.join(out, 'fighter', 'gekkouga', 'effect', 'gekkouga', 'gekkouga.010d0000.ptcl'), 'rb').read())
    si = pp.find_set('PtcGekkougaFireTrail')
    ems = [e['data'] for e in pp.sets[si]['emitters']]
    others = [round(pp.field(e['data'], 'color_scale'), 3) for n_ in ('PtcGekkougaFireBody', 'PtcGekkougaFireTip')
              for e in pp.sets[pp.find_set(n_)]['emitters']]
    lum = FX.TRAIL_BRIGHTNESS * (0.299 * FX.TRAIL_TINT[0] + 0.587 * FX.TRAIL_TINT[1] + 0.114 * FX.TRAIL_TINT[2])
    check('trail dim v1 (the user: "make the smash attack fire trails less bright"): PtcGekkougaFireTrail\'s %d emitters '
          '(both layers) colour scale (0x778) %g (was 1.0) and colour 0 the warm tint %s (was white): drawn colour 0 x the '
          'texture\'s rgb, additive: red x%.2f, green x%.2f, blue x%.2f, luminance x%.2f (55 - 65 %%: the user\'s "less '
          'bright"); the white-hot cores a pale orange, not grey; alpha 1, additive as before; the other fires\' scale 1.0'
          % (len(ems), FX.TRAIL_BRIGHTNESS, FX.TRAIL_TINT, *(FX.TRAIL_BRIGHTNESS * t for t in FX.TRAIL_TINT), lum),
          ([round(pp.field(e, 'color_scale'), 3) for e in ems],
           {tuple(round(x, 3) for x in pp.field(e, 'color0_keys')[:4]) for e in ems},
           {pp.field(e, 'alpha_init') for e in ems}, {pp.field(e, 'blend_type') for e in ems}, set(others),
           0.55 <= lum <= 0.65),
          ([FX.TRAIL_BRIGHTNESS] * len(ems), {tuple(FX.TRAIL_TINT) + (1.0,)}, {1.0}, {1}, {1.0}, True))
    # the sound
    bank = open(os.path.join(out, 'fighter', 'gekkouga', 'sound', 'snd_se_Gekkouga.nus3bank'), 'rb').read()
    _s, tones = MS.tones_of(bank)
    last = MS.parse_entry(tones[-1])
    t_new = FB.Table(open(os.path.join(out, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read())
    row_ = t_new.row_of(2058)
    vol = round(struct.unpack('<f', last[2][12:16])[0], 2)
    check('ice detonation sound: his bank + label 97 snd_se_Gekkouga_IceBoom (0x%08X: row 0x768, the 7th added), TONE %+g dB '
          '(%d tones), the MSC\'s id' % (C.ICE_SND_ID, GS.ICE_SOUND[2], len(tones)),
          (FB.binf(bank), last[1], vol, row_, len(t_new.tones(row_)), t_new.tones(row_)[97] == len(tones) - 1,
           'int gk_is_sound() { return 0x7680061; }' in open(os.path.join(ROOT, 'fighters', 'gekkouga', 'clones.c')).read(),
           C.ICE_SND_ID),
          (('snd_se_Gekkouga', 2058), 'snd_se_Gekkouga_IceBoom', GS.ICE_SOUND[2], 0x768, 98, True, True, 0x07680061))
    if ice_clip:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            w, on, start = GS.ice_cut(ice_clip, tmp)
            pcm = FB.load_audio(w).astype(float) / 32768.0
            o2 = GS.boom_onset(pcm, FB.RATE)
        n_ = round(struct.unpack('<I', last[2][-0x18:-0x14])[0])
        check('ice detonation sound: the clip\'s boom onset (1 ms windows: the rise into its loudest 10 ms) at %.3f s; '
              'with the %d-frame countdown the whole clip fits (its clicks and fuse hiss kept, at its speed and pitch): '
              '%.3f s of silence in front, so its boom comes %.2f frames after its start (the blast lands at %d - %d frames '
              'after the arming); the bank\'s one-shot that long (%d samples)' % (
                  on, C.ICE2_FRAMES, -start, o2 * 60, C.ICE2_FRAMES, C.ICE2_FRAMES + 1, n_),
              (abs(o2 * 60 - C.ICE_SND_LEAD) <= 1.0, start < 0, n_ == len(pcm)), (True, True, True))
    m = MSC(mscsb, src)
    g = m.game
    snd = []
    old = g.sys

    def sysf(sid, a, old=old):
        if sid == 0x1E:
            snd.append((a[0], a[1]))
        return old(sid, a)
    g.sys = sysf
    seen = {}
    for nm, play, stop in (('play', 1.0, 0.0), ('stop', 0.0, 1.0), ('both', 1.0, 1.0), ('none', 0.0, 0.0)):
        snd[:] = []
        g.vars[CC.ICE3_SND_VAR], g.vars[CC.ICE3_SND_VAR + 1] = play * 4.0, stop * 4.0   # parabeetle v2: TIMER_13 / 14
        m('gk_is_tick')
        seen[nm] = (list(snd), g.vars.get(CC.ICE3_SND_VAR), g.vars.get(CC.ICE3_SND_VAR + 1))
    I = 0x07680061
    check('ice detonation sound: his MSC (gk_is_tick, every frame): the executable\'s play request (parabeetle v2: his '
          'TIMER_13, written 4) plays it (SoundModule 0x2710), its stop (TIMER_14, a cancelled countdown) stops it (0x2714), '
          'stop before play, each request cleared',
          seen, {'play': ([(0x2710, I)], 0.0, 0.0), 'stop': ([(0x2714, I)], 0.0, 0.0),
                 'both': ([(0x2714, I), (0x2710, I)], 0.0, 0.0), 'none': ([], 0.0, 0.0)})
    snd[:] = []
    g.vars[CC.ICE3_VAR] = 4.3
    m('gk_ib_tick')
    blast = list(snd)
    snd[:] = []
    m('gk_reset')
    sk = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'skeleton.c')).read()
    check('ice detonation sound: the blast plays no sound now (the skeleton\'s SkBoom 0x07680060 was the old one: replaced, '
          'the user\'s "Replace what the old sound was"); a battle reset (gk_reset) stops the detonation\'s sound; the '
          'skeleton keeps its own explosion sound', (blast, snd, 'int sk_snd_boom() { return 0x7680060; }' in sk),
          ([], [(0x2714, I)], True))
    check('clones: the ability 840 frames (14 s, the user; 720 before), the burnout still 480, the gauge\'s ability drain '
          'over 840 (gk_pct(left, gk_ability_frames()))', (m('gk_ability_frames'), m('gk_burnout_frames')), (840, 480))


def air_regroup_tests(mscsb, src):
    """usmash spike v2 / trail dim v1 (the user: the regroup "work in the air, still by pressing shield and special"; "If
    Greninja is in the middle of airdodging, allow him to cancel into the reform command"): the air press (special with
    shield held from a fall / jump), the air dodge's cancel (special alone, early / mid / late), none with no clones out
    split or in the burnout; the air call's motion, kinetics and intangibility; the clones' regroup to him while he falls;
    a landing mid-call"""
    calls = []

    def fresh():
        m, g, _tr = ak_run(mscsb, src, True, frames_=24)        # split, all in the air
        old = g.sys

        def sysf(sid, a, old=old):
            calls.append((sid, tuple(a)))
            return old(sid, a)
        g.sys = sysf
        g.status_req = []
        m.vm.g[18] = 2
        return m, g
    m, g = fresh()
    got = {}
    for nm, st, press, guard, t in (('Fall, special + shield held', 0xE, (1,), True, 5.0),
                                    ('a jump, special + shield held', 0xB, (1,), True, 5.0),
                                    ('Fall, special without shield', 0xE, (1,), False, 5.0),
                                    ('Fall, shield without special', 0xE, (), True, 5.0),
                                    ('EscapeAir frame 1, special', 0x22, (1,), False, 1.0),
                                    ('EscapeAir frame 15, special', 0x22, (1,), False, 15.0),
                                    ('EscapeAir frame 30, special', 0x22, (1,), False, 30.0),
                                    ('EscapeAir frame 15, special + shield', 0x22, (1,), True, 15.0)):
        g.status_req, g.vars[0x0F0003C9] = [], 0.0
        m.vm.g[9] = f2i(t)
        ak_frame(m, g, st=st, press=press, guard=guard)
        got[nm] = (g.status_req, g.vars.get(0x0F0003C9))
    yes = ([(0x160, 1)], 160.0)
    check('air regroup: in the air special with shield held (a fall, a jump) calls the regroup (0x160) and clears the '
          'specials and the shield / air dodge commands (Buffer_Clear 160: no special, no air dodge from the press); special '
          'alone or shield alone: nothing; in the air dodge (EscapeAir 0x22) special alone cancels it into the call at '
          'its frame 1, 15 and 30 (shield started the dodge), with shield held too', got,
          {'Fall, special + shield held': yes, 'a jump, special + shield held': yes,
           'Fall, special without shield': ([], 0.0), 'Fall, shield without special': ([], 0.0),
           'EscapeAir frame 1, special': yes, 'EscapeAir frame 15, special': yes, 'EscapeAir frame 30, special': yes,
           'EscapeAir frame 15, special + shield': yes})
    none = {}
    for nm in ('formation (no clones split)', 'the burnout', 'the aligned kick'):
        m2, g2 = fresh()
        if nm.startswith('formation'):
            g2.vars[0x0F000388] = 0.0
        elif nm == 'the burnout':
            m2.setg('gk_burnout', 300)
            m2.setg('gk_ability', 0)
        else:
            g2.vars[0x0F000388] = 1.0
        m2.vm.g[9] = f2i(10.0)
        ak_frame(m2, g2, st=0x22, press=(1,), guard=True)
        none[nm] = [r for r in g2.status_req if r[0] == 0x160]
    check('air regroup: none where the ground one is unavailable (the dodge goes on): clones in formation, the burnout, '
          'the aligned kick', none, {k: [] for k in none})
    # the call in the air: motion, kinetics, intangibility
    m, g = fresh()
    x0, y0 = g.x, g.y
    m.vm.g[4] = 0x160
    calls[:] = []
    m('gk_rg_init')
    init = [c for c in calls if c[0] in (0x10, 0x2D)]
    calls[:] = []
    g.log = []
    m('gk_rg_main')
    mo = [(c[1][1], round(fv(c[1][3]), 3)) for c in calls if c[0] == 0x12 and c[1][0] == 1]
    check('air regroup: its init in the air: HitModule(0x2710, 0) (the air dodge\'s intangibility ended), KineticModule(0, '
          '0) (the fall\'s kinetics: his gravity, drift and the speed he had: no stall, no momentum change; the ground one '
          'keeps the stance\'s func_2340); its motion the stance\'s air one (specialairlw 0x289) at 0.4 for 19 frames '
          '(frames 0 - 7.6); the clones regrouping (mode 3)', (init, mo, int(g.vars.get(0x0F000388))),
          ([(0x2D, (0x2710, 0)), (0x10, (0, 0))], [(0x289, 0.4)], 3))
    # the regroup in the air: he falls 1 a frame, they ease to his X -/+ 14 and his Y
    lx0, ly0 = m.gf('gk_lx'), m.gf('gk_ly')
    pts = []
    for t in range(75):
        g.y = round(g.y - 1.0, 3)
        m.vm.g[19], m.vm.g[18] = 2, 2
        ak_frame(m, g, st=0x160 if t < 19 else 0xE)
        pts.append((m.gf('gk_lx'), m.gf('gk_ly'), m.gf('gk_rx'), m.gf('gk_ry'), g.x, g.y))
    step = max(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip([(lx0, ly0)] + pts, pts))
    end = pts[-1]
    check('air regroup: they float back to him while he falls (75 frames eased, the biggest step %.2f; not a teleport), '
          'to his X -/+ 14 and his Y at the end, then formation (mode 0)' % step,
          (step < 4.0, round(end[0] - end[4], 2), round(end[2] - end[4], 2), round(end[1] - end[5], 2),
           round(end[3] - end[5], 2), int(g.vars.get(0x0F000388))), (True, -14.0, 14.0, 0.0, 0.0, 0))
    # landing mid-call
    m, g = fresh()
    m.vm.g[4] = 0x160
    m('gk_rg_init')
    m('gk_rg_main')
    g.status_req = []
    m.vm.g[9] = f2i(6.0)
    m.vm.g[19], m.vm.g[18] = 2, 2
    r_air = m('gk_rg_loop')
    m.vm.g[19], m.vm.g[18] = 2, 0
    r_land = m('gk_rg_loop')
    check('air regroup: landing mid-call (frame 6 of 19) ends it in LandingLight (0x17: a normal landing, no aerial '
          'landing lag); in the air before it, nothing; the clones go on regrouping (mode 3)',
          (r_air, r_land, g.status_req, int(g.vars.get(0x0F000388))), (0, 1, [(0x17, 0)], 3))
    m.vm.g[9] = f2i(19.0)
    m.vm.g[19], m.vm.g[18] = 2, 2
    g.status_req = []
    check('air regroup: its 19 frames over in the air: Fall (0xE, not a special fall)', (m('gk_rg_loop'), g.status_req),
          (1, [(0xE, 0)]))


def bugfix_tests(mscsb, src):
    """aligned kick v1 package (the user's two bugs): a swap / his landing flips the clones' effects epoch; a KO empties the
    down special's charge (gauge 0)"""
    m, g = ak_setup(mscsb, src)
    ep = lambda: (int(g.vars.get(0x0F00031F)) - 4747000) // 256 % 2
    e0 = ep()
    g.situation = 2
    frames(m, 1, 0x34)
    g.situation = 0
    frames(m, 1, 0x18)
    e1 = ep()
    g.press, g.stick = {1}, (-0.8, -0.8)
    m.vm.g[4], m.vm.g[24] = 0x18, 0x8000
    m('gekkouga_frame')
    e2 = ep()
    check('clone effects: his landing in formation (an aerial -> its landing) flips the effects epoch (flags 256), a swap '
          'flips it again (each: the clones fade their following effects)', (e1 != e0, e2 != e1), (True, True))
    m = fresh(mscsb, src)
    g = m.game
    m.setg('gk_lw_charge', 250)
    frames(m, 1)
    g0 = g.vars.get(0x0F000313)
    frames(m, 1, 0xB1)
    frames(m, 3, 0xB2)
    frames(m, 1)
    check('KO: the down special\'s charge (250 of 300: gauge mode 1, 83) back to 0 at the KO: gauge 0 (hidden) after the '
          'respawn; the smash charge kept (as before)', (g0, m.g('gk_lw_charge'), g.vars.get(0x0F000313)),
          (1083.0, 0, 0.0))


def cf3_run(mscsb, src, held_to=0, presses=(), n=40, site_at=()):
    """clone fix v3: the full gauge's down special press activates the ability (frame 0: his hook, then the input site:
    gk_lw_press); then n frames of his hook (gekkouga_frame: gk_input, gk_ability_update) and the input sites. The game's
    command buffer is modelled: a down special press stays for 10 frames unless Buffer_Clear (specials: his var 0x3C9 = 32)
    drops it; while one is live the input site calls gk_lw_press (site_at: frames it asks anyway, as if a press were seen).
    held_to: special held through that frame (the activating press); presses: fresh presses (frame numbers, held 1 frame).
    Returns (the frame of the kick (status 0x161) or None, the input site's answers, slot 60 each frame)"""
    m = fresh(mscsb, src)
    g = m.game
    g.x, g.y = 0.0, 10.0
    m.setg('gk_lw_charge', 300)
    kick, answers, armed = None, [], []
    buf = 0
    for t in range(0, n + 1):
        press = t == 0 or t in presses
        g.press = {1} if press else set()
        g.held = {1} if (press or t <= held_to) else set()
        g.stick = (0.0, -0.8)
        if press:
            buf = 10
            g.vars[0x0F0003C9] = 0
        m.vm.g[4], m.vm.g[24] = 0, 0x8000 if press else 0
        g.vars[0x0F00031E] = float(m.g('gk_alive') & g.beat)
        g.status_req = []
        m('gekkouga_frame')
        if g.vars.get(0x0F0003C9) == 32:
            buf = 0
        if buf > 0 or t in site_at:
            r = m('gk_lw_press')
            answers.append((t, r))
            if g.vars.get(0x0F0003C9) == 32:
                buf = 0
            if (0x161, 1) in g.status_req and kick is None:
                kick = t
                buf = 0
        buf = max(buf - 1, 0)
        armed.append(int(g.vars.get(0x0F000380 + 23, 0)))   # (the kick armed: slot 23 from parabeetle v2)
    return m, g, kick, answers, armed


# freeze fix v1 (clone fixes v3 froze the game at his load: its gekkouga.mscsb had MSC op 0x19, bitXor, from a `^`): the
# opcodes in the game's own Greninja MSCs (gekkouga, its articles) and in clone articles v1's (loaded in game), + 0x1B
# (rightShift: the game's brave.mscsb, the mod's kirby.mscsb, in game for long); a compiled MSC with any other is refused
MSC_GAME_OPS = frozenset((0x2, 0x3, 0x6, 0x7, 0xA, 0xB, 0xD, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x1A, 0x1B,
                          0x1C, 0x1D, 0x1E, 0x23, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30,
                          0x31, 0x34, 0x35, 0x36, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x41, 0x42, 0x43, 0x44, 0x45,
                          0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B))


def msc_ops_tests(out):
    """freeze fix v1: every compiled MSC of the package uses only opcodes the game's own MSCs use"""
    sys.path.insert(0, os.path.join(HERE, 'mscdec'))
    from msc import MscFile
    bad = {}
    for root, _ds, fs in os.walk(os.path.join(out, 'fighter')):
        for f in fs:
            if f.endswith('.mscsb'):
                m = MscFile()
                m.readFromFile(open(os.path.join(root, f), 'rb'))
                ops = {c.command for s in m.scripts for c in s} - MSC_GAME_OPS
                if ops:
                    bad[os.path.relpath(os.path.join(root, f), out)] = sorted(hex(o) for o in ops)
    check('freeze fix v1: every MSC built uses only opcodes the game\'s own MSCs use (v3\'s bitXor 0x19 froze his load)',
          bad, {})


def clone_moves_tests(mscsb, src, cl_mscsb, out):
    """clone moves v1 (README "Clone moves v1"): split clones join his shield / dodges / grab / specials (mirroring: his
    motion, his movement from their own place); a shielding clone blocks hits; dodges' intangible frames; the grab
    hitboxes (hold / pummel / throws from his scripts); the neutral special's charge orb and the run's dust on the clone"""
    import acmd
    m, g, tr = ak_run(mscsb, src, True, frames_=24)
    g.y = 10.0
    for _ in range(80):
        ak_frame(m, g, st=0)
    acts = lambda: (m('gk_bvi', 1, 0), m('gk_bvi', 2, 0))
    check('clone moves: split, both standing (action 0)', (int(g.vars.get(0x0F000388)), acts()), (2, (0, 0)))
    g.motion, g.frame = 0x48, 3.0
    ak_frame(m, g, st=0x1C)
    check('his shield (Guard 0x1C): both clones mirror it (action 6): his motion (Guard 0x48) from his frame 3',
          (acts(), ak_cmd(g, 1)[:2], ak_cmd(g, 2)[:2]), ((6, 6), (0x48, 3), (0x48, 3)))
    g.vars[0x0F000315] = 20000.0 + 1
    ak_frame(m, g, st=0x1C)
    check('... a hit on the left clone while it shields: blocked (it stays; diag VAR_23 711)',
          (m.g('gk_alive'), g.vars.get(0x0F000317)), (3, 711.0))
    g.motion, g.frame = 0, 0.0
    ak_frame(m, g, st=0)
    check('his shield let go: their own control again (Wait, action 0)', (acts(), ak_cmd(g, 1)[0]), ((0, 0), 0))
    x0 = m.gf('gk_lx')
    g.motion = 0x4C
    for _ in range(5):
        g.x += 2.0
        ak_frame(m, g, st=0x20)
    check('his forward roll (EscapeF 0x20, motion 0x4C), him 2 a frame: the clones roll with his movement from their '
          'own place (+10 in 5 frames), on their floor', (ak_cmd(g, 1)[0], round(m.gf('gk_lx') - x0, 3), m.gf('gk_ly')),
          (0x4C, 10.0, 10.0))
    g.motion = 0
    ak_frame(m, g, st=0)
    g.motion = 0x72
    ak_frame(m, g, st=0x35)
    k1 = ak_cmd(g, 1)[0]
    g.motion = 0x76
    ak_frame(m, g, st=0x3B)
    check('his grab (Catch 0x35: motion 0x72), his pummel (CatchAttack 0x3B: 0x76): the clones play them (their scripts\' '
          'catch / pummel hitboxes)', (k1, ak_cmd(g, 1)[0], ak_cmd(g, 2)[0]), (0x72, 0x76, 0x76))
    g.motion = 0
    ak_frame(m, g, st=0)
    g.motion = 0x211
    ak_frame(m, g, st=0x152)
    check('his neutral special (0x152: SpecialNStart 0x211): the clones play it; his shot\'s copies are theirs '
          '(gk_art_clones: both), as his side special\'s skeletons (his stack, one shadow)',
          (ak_cmd(g, 1)[0], m('gk_art_clones')), (0x211, 3))
    g.motion = 0
    ak_frame(m, g, st=0)
    ly0 = m.gf('gk_ly')
    g.motion = 0x25D
    for _ in range(4):
        g.y += 5.0
        ak_frame(m, g, st=0x154)
    check('his up special (0x154: SpecialHiStart 0x25D), him rising 5 a frame: the clones leave the ground with him (action '
          '16) and rise by his movement (+20)', (acts(), round(m.gf('gk_ly') - ly0, 3)), ((16, 16), 20.0))
    g.motion = 0
    for _ in range(60):
        g.y = max(10.0, g.y - 2.0)
        ak_frame(m, g, st=0xE if g.y > 10.0 else 0)
    ak_frame(m, g, st=0x155)
    check('his down special (the charge stance 0x155 / swap / kick): the clones don\'t mirror it', acts()[0] in (6, 16), False)
    ak_frame(m, g, st=0)
    g.vars[0x0F000315] = 20000.0 + 1
    ak_frame(m, g, st=0)
    check('... a hit on a clone not shielding: removed as before (201)', (m.g('gk_alive'), g.vars.get(0x0F000317) % 1000),
          (2, 201.0))
    # ---- the clone article: shield re-arm, dodges, the charge orb, the run's dust
    c = MSC(cl_mscsb, GB.CLONE_MSC)
    cg = c.game

    def cm(kind, f, latch=None):
        c.setg('cl_motion', kind)
        cg.frame = float(f)
        if latch is not None:
            cg.vars[0x0F000304] = latch
        cg.log = []
        c('cl_moves')
        return cg.vars.get(0x0F000304, 0.0)
    lat = [cm(0x48, 5, 1.0 if i == 0 else None) for i in range(13)]
    check('the clone shielding (Guard 0x48) with its hit check latched (a blocked hit): let go after 12 frames (the next '
          'attack is checked)', (lat[10], lat[11]), (1.0, 0.0))
    win = {}
    for k in (0x4B, 0x4C, 0x4D, 0x4E):
        cm(0, 0, 0.0)
        win[k] = [f for f in range(32) if cm(k, f) > 0.5]
        win[k] = (win[k][0], win[k][-1] + 1) if win[k] else None
    cm(0, 0)
    check('the clone\'s dodges: its hit check off (latched) in his vl intangible frames: spot dodge 2 - 17, rolls 4 - 15, '
          'air dodge 2 - 27; on again after', (win, cg.vars.get(0x0F000304)), ({0x4B: (2, 17), 0x4C: (4, 15), 0x4D: (4, 15),
                                                                               0x4E: (2, 27)}, 0.0))
    orbs = []
    for t in range(61):
        cm(0x215, t)
        orbs += [(t, round(x[4], 2)) for x in cg.log if x[0] == 'fxsize' and x[2] == 0x3300003]
    check('the neutral special\'s hold (0x215): his water orb (0x3300003) on its hand (0x7E8) again every 10 frames, '
          'growing 1 -> 1.6 over 60 (the user: "the water shuriken effect doesn\'t appear for clones while charging")',
          orbs, [(t, round(1.0 + 0.6 * t / 60.0, 2)) for t in range(0, 61, 10)])
    cm(0, 0)
    dust = []
    for f in (0.0, 0.5, 1.0, 5.0, 10.0, 14.0, 0.0, 1.0):
        cm(0x12, f)
        dust += [f for x in cg.log if x[0] == 'fxsize' and x[2] == 0x1000019]
    check('the run (0x12): his dust (0x1000019) at its frames 1 and 10, each loop', dust, [1.0, 10.0, 1.0])
    # ---- the grab scripts (the clone's game.bin)
    cgb = acmd.ACMDFile.load(os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon', 'clone', 'game.bin'))
    gb = acmd.ACMDFile.load(os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd', 'body', 'game.bin'))
    val = lambda c_, n: c_.params[c_.info['syntax'].index(n)]
    BOXES = ('Special_Hitbox', 'Extended_Special_Hitbox')
    hb = lambda n: [c_ for c_ in cgb.scripts[acmd.crc(n)] if c_.name in BOXES]
    holds = lambda n: [tuple(c_.params) for c_ in cgb.scripts[acmd.crc(n)] if c_.name == 'Hitbox_Hold']
    catch = hb('catch')
    check('the clone\'s grab (catch): his grab box (frame 11, 2.5, Z 4 - 16) as a hold hitbox: 0 %, 361, BKB 40, not '
          'shieldable, hitlag 0, Hitbox_Hold mode 2',
          [(c_.name, val(c_, 'Size'), val(c_, 'Z'), val(c_, 'Z2'), val(c_, 'Damage'), val(c_, 'Angle'), val(c_, 'BKB'),
            val(c_, 'Shieldable'), val(c_, 'Hitlag')) for c_ in catch] + holds('catch'),
          [('Extended_Special_Hitbox', 2.5, 4.0, 16.0, 0.0, 361, 40, 0, 0.0), (0, 2)])
    cw = hb('catchwait')
    check('CatchWait: the hold at its hand (Z 12, 7) again every 12 frames (rehit), held', [(val(c_, 'Rehit'), val(c_, 'Z'))
                                                                                          for c_ in cw] + holds('catchwait'),
          [(12, 12.0), (0, 2)])
    his_p = next(c_ for c_ in gb.scripts[acmd.crc('catchattack')] if c_.name == 'Special_Hitbox')
    pm = [c_ for c_ in hb('catchattack') if val(c_, 'Damage') > 0]
    check('pummel (CatchAttack): his 2 %% hitbox at his frame 6 (one a press: his pummel status), not shieldable, held',
          [(val(c_, 'Damage'), val(c_, 'Angle'), val(c_, 'KBG'), val(c_, 'FKB'), val(c_, 'Shieldable')) for c_ in pm],
          [(val(his_p, 'Damage'), val(his_p, 'Angle'), val(his_p, 'KBG'), val(his_p, 'FKB'), 0)])
    got, want = {}, {}
    for n in ('throwf', 'throwb', 'throwhi', 'throwlw'):
        sp = next(c_ for c_ in gb.scripts[acmd.crc(n)] if c_.name == 'Throw_Specifier' and int(c_.params[0]) == 0)
        fr = [c_ for c_ in gb.scripts[acmd.crc(n)] if c_.name == 'FRAME'][-1].params[0]
        want[n] = (int(fr), val(sp, 'Damage'), val(sp, 'Angle'), val(sp, 'KBG'), val(sp, 'WBKB'), val(sp, 'BKB'))
        sc = cgb.scripts[acmd.crc(n)]
        t = next(c_ for c_ in sc if c_.name in BOXES and val(c_, 'Damage') > 0)
        fr2 = [c_ for c_ in sc[:sc.index(t)] if c_.name == 'FRAME'][-1].params[0]
        got[n] = (int(fr2), val(t, 'Damage'), val(t, 'Angle'), val(t, 'KBG'), val(t, 'FKB'), val(t, 'BKB'))
    check('throws: at his release frame (Throw_Applier) a hitbox with his throw\'s values (Throw_Specifier kind 0: damage, '
          'angle, KBG, WBKB as FKB, BKB), the hold before it', got, want)


def tuning_tests(mscsb, src, out, user, tr_mscsb):
    """tuning v1 (README "Tuning v1"): forward tilt's teleport gone, neutral air's shield break gone and x1.25, forward
    smash 30 longer (its width the same), the charge-start star at its size, denser trails covered by their hitboxes,
    the clones acting while he hangs on a ledge"""
    import acmd
    B = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    g = acmd.ACMDFile.load(os.path.join(B, 'body', 'game.bin'))
    e = acmd.ACMDFile.load(os.path.join(B, 'body', 'effect.bin'))
    ug = acmd.ACMDFile.load(os.path.join(user, 'body', 'game.bin'))
    ue = acmd.ACMDFile.load(os.path.join(user, 'body', 'effect.bin'))
    cg = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'game.bin'))
    ce = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'effect.bin'))
    v = lambda c, n: c.params[c.info['syntax'].index(n)]
    sf = lambda f, n, var: [c for c in f.scripts[acmd.crc(n)] if c.name == 'SET_FLOAT' and int(c.params[1]) == var]
    check('tuning: forward tilt\'s teleport (his attacks3\'s SET_FLOAT 12 to 0x0F00000C: "put the opponent 12 in front of '
          'self") gone; the rest of the script his', (len(sf(ug, 'attacks3', 0x0F00000C)), len(sf(g, 'attacks3', 0x0F00000C)),
                                                   len(g.scripts[acmd.crc('attacks3')]) + 1 == len(ug.scripts[acmd.crc('attacks3')])),
          (1, 0, True))
    un = ug.scripts[acmd.crc('attackairn')]
    gn = g.scripts[acmd.crc('attackairn')]
    tr = next(c for c in gn if c.name == 'True')
    inner = gn[gn.index(tr) + 1:]
    w = 0
    for c in inner:
        if w >= int(tr.params[0]) - 2:
            break
        w += 1 + len(c.params)
    check('tuning: neutral air\'s shield break (its second hit\'s SET_FLOAT 89 to LASTHIT_STATUS 0x0F0000B2) gone (its '
          'True block one command shorter, its second hit kept); its hitboxes x1.25 (nair / fair v1: its Part 0 hits '
          'sized to the burst, NAIR_STRONG / NAIR_LATE: nair_fair_tests)',
          (len(sf(ug, 'attackairn', 0x0F0000B2)), len(sf(g, 'attackairn', 0x0F0000B2)), w == int(tr.params[0]) - 2,
           [v(c, 'Size') for c in gn if c.name in GB.HITBOXES and int(v(c, 'ID')) == 0]),
          (1, 0, True, [round(v(c, 'Size') * 1.25, 4) for c in un if c.name in GB.HITBOXES] if not hasattr(GB, 'nair_ring')
           else [GB.NAIR_STRONG, GB.NAIR_LATE, GB.NAIR_STRONG]))
    check('... its water burst (0x330000B) and fire ring (0x330001D / 1E) x1.25 (1.45 -> 1.8125)',
          [round(v(c, 'Size'), 4) for c in e.scripts[acmd.crc('attackairn')] if 'Size' in c.info['syntax']], [1.8125, 1.8125])
    hb = {int(v(c, 'ID')): (v(c, 'Y'), v(c, 'Size')) for c in g.scripts[acmd.crc('attacks4')] if c.name in GB.HITBOXES}
    sw = [round(v(c, 'Y'), 3) for c in e.scripts[acmd.crc('attacks4')] if c.name == 'External_Graphic' and c.params[0] == GB.SWORD]
    tip = [v(c, 'Y') for c in e.scripts[acmd.crc('attacks4')] if c.name == 'External_Graphic' and c.params[0] == GB.FIRE_TIP]
    glow = [v(c, 'Y2') for c in e.scripts[acmd.crc('attacks4')] if c.name == 'Sword_Glow']
    check('tuning: forward smash 30 longer, not bigger: a second water sword (the same size 5) from 30 along the blade, its '
          'trail and tip flame at 85 (was 55), a hitbox ID 3 at 62.5 (ID 0\'s size): it reaches 80 from his hand (DK in the '
          'user\'s screenshot: ~72 - 82)', (sw, tip, glow, hb[3], hb[3][1] == hb[0][1], round(-hb[3][0] + hb[3][1], 1)),
          ([0.0, -30.0], [-85.0], [-85.0], (-62.5, hb[0][1]), True, 80.0))
    csw = [c for c in ce.scripts[acmd.crc('attacks4')] if c.name == 'External_Graphic' and c.params[0] == GB.SWORD]
    chb = [c for c in cg.scripts[acmd.crc('attacks4')] if c.name in GB.HITBOXES]
    check('... the clones\' copies the same (2 swords, 4 hitboxes)', (len(csw), len(chb)), (2, 4))
    star = {n: [round(v(c, 'Size'), 3) for c in e.scripts[acmd.crc(n)] if 'Size' in c.info['syntax'] and c.params[0] == GB.SMASH_STAR]
            for n in GB.SMASH_SCRIPTS if acmd.crc(n) in e.scripts}
    rel = [round(v(c, 'Size'), 3) for c in e.scripts[acmd.crc('attacks4')] if c.name == 'Graphic_Effect3']
    check('tuning: the smashes\' charge-start star (0x100000F) at its own size 1 (was x5), his and the clones\'; the '
          'release effects still x5 (forward smash\'s 0.9 -> 4.5)',
          (star, [round(v(c, 'Size'), 3) for n in ('attacks4', 'attackhi4', 'attacklw4') for c in ce.scripts[acmd.crc(n)]
                  if 'Size' in c.info['syntax'] and c.params[0] == GB.SMASH_STAR], rel),
          ({'attacks4': [1.0], 'attackhi4': [1.0], 'attacklw4': [1.0]}, [1.0, 1.0, 1.0], [4.5]))
    # ---- the trails (firetrail.mscsb) and their hitboxes
    t = MSC(tr_mscsb, GB.TRAIL_MSC)
    fl = {}
    for ty in (1, 2, 3):
        t.setg('tr_type', ty)
        n = t('tr_fx_count')
        fl[ty] = [(round(fv(t('tr_fx_dz', k)), 2), round(fv(t('tr_fx_size', k)), 2)) for k in range(n)]
    check('trail lite v1: half the flames over the same lengths: forward 6 flames 8 - 85 (15.4 apart), up 4 (4 and 22 '
          'each side), down 8 (6 - 55 each side, 16.3 apart), sizes 0.85 - 1.15',
          ({k: (len(x), min(z for z, _ in x), max(z for z, _ in x)) for k, x in fl.items()},
           sorted({sz for x in fl.values() for _, sz in x})),
          ({1: (6, 8.0, 85.0), 2: (4, -22.0, 22.0), 3: (8, -55.0, 55.0)}, [0.85, 0.95, 1.05, 1.15]))
    unc = []
    for ty, nm in ((1, 'FireTrailS4'), (2, 'FireTrailHi4'), (3, 'FireTrailLw4')):
        for z, _sz in fl[ty]:
            if not any(abs(z - bz) <= bs for bz, _by, bs in GB.TR_BOXES[nm]):
                unc.append((nm, z))
    check('... every flame inside one of its trail\'s hitboxes (forward 7, up 6, down 8 boxes)',
          (unc, [len(GB.TR_BOXES[n]) for n in GB.TR_SCRIPTS[:3]]), ([], [7, 6, 8]))
    # ---- the ledge: they act
    m = fresh(mscsb, src)
    g_ = m.game
    g_.x, g_.y = 0.0, 10.0
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 14)
    lx0 = m.gf('gk_lx')
    ak_frame(m, g_, st=0x73)
    mode1 = (int(g_.vars.get(0x0F000388)), int(g_.vars.get(0x0F000380 + 39, 0)))   # (the ledge kick: 39 from v2)
    for _ in range(5):
        ak_frame(m, g_, st=0x74, stick=(-0.5, 0.0))
    walked = round(m.gf('gk_lx') - lx0, 3)
    ak_frame(m, g_, st=0x74, cmd=0x1)
    jab = ak_cmd(g_, 1)[0]
    for _ in range(30):
        ak_frame(m, g_, st=0x74)
    ak_frame(m, g_, st=0x75)
    ak_frame(m, g_, st=0)
    mode2 = int(g_.vars.get(0x0F000388))
    for _ in range(80):
        ak_frame(m, g_, st=0)
    check('tuning: he hangs on a ledge (0x73 CliffCatch): the clones in formation go split (mode 2, slot 63 1); his stick '
          '(half left) walks them (WalkMiddle: -0.953 a frame, 5 frames), his attack press a jab (0x50); he gets up: they '
          'regroup (mode 3), then formation at -14 / +14',
          (mode1, walked, jab, mode2, int(g_.vars.get(0x0F000388)), (m.gf('gk_lx'), m.gf('gk_rx'))),
          ((2, 1), round(-0.953 * 5, 3), 0x50, 3, 0, (-14.0, 14.0)))


NAIR_TUNING = (9.375, 12.5)      # tuning v1's neutral air sizes (strong / late)
FAIR_DK = 19.9                    # DK's nearest point from his hand in the user's fair_reach.png (blade 11 = 122 px)


def nair_fair_tests(out, user):
    """nair / fair v1 (README "Neutral air ring v1"; usmash spike v2 / trail dim v1 put the ring back to this, the user's
    request, undoing smash tune v1's windbox): neutral air's strong / late hits sized to the burst, the fire ring's
    weak capsules (Part 1, IDs 1-6) following FIRE_RING's flames outside them, their own hit record kept from frame 14 to
    24; forward air 10 longer with a hitbox ID 2 reaching DK; the clones' copies the same"""
    import math
    import acmd
    import gekkouga_fx as FX
    import gekkouga_clone_cave as C
    B = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    g = acmd.ACMDFile.load(os.path.join(B, 'body', 'game.bin'))
    e = acmd.ACMDFile.load(os.path.join(B, 'body', 'effect.bin'))
    cg = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'game.bin'))
    ce = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'effect.bin'))
    v = lambda c, n: c.params[c.info['syntax'].index(n)]
    gn = g.scripts[acmd.crc('attackairn')]
    # the timeline: (frame, command)
    tl, fr = [], 0.0
    for c in gn:
        if c.name == 'FRAME':
            fr = max(fr, float(c.params[0]))
        elif c.name == 'WAIT':
            fr += float(c.params[0])
        tl.append((fr, c))
    hb = [(f, c) for f, c in tl if c.name in GB.HITBOXES]
    p0 = [(f, int(v(c, 'ID')), float(v(c, 'Damage')), round(float(v(c, 'Size')), 3)) for f, c in hb if int(v(c, 'Part')) == 0]
    check('nair ring v1: neutral air\'s Part 0 hits (ID 0): strong 11 %% at 12 (and the connected re-hit at 17) %.1f, late '
          '6 %% at 14 %.1f (tuning v1 %.3f / %.1f): the burst as drawn (its solid disc / its edge)' % (
              GB.NAIR_STRONG, GB.NAIR_LATE, NAIR_TUNING[0], NAIR_TUNING[1]),
          (p0, GB.NAIR_STRONG > NAIR_TUNING[0] * 1.2, GB.NAIR_LATE > NAIR_TUNING[1]),
          ([(12.0, 0, 11.0, GB.NAIR_STRONG), (14.0, 0, 6.0, GB.NAIR_LATE), (17.0, 0, 11.0, GB.NAIR_STRONG)], True, True))
    ring = [(f, c) for f, c in hb if int(v(c, 'Part')) != 0]
    frames = sorted({f for f, _c in ring})
    check('nair ring v1: the ring\'s hitboxes: Extended_Hitbox capsules, Part 1, IDs 1-6 on joint 0, set at 14 / 16 / 18 / '
          '20 / 22 (6 each), all gone at 24 (Remove_All_Hitboxes), the Part 0 hit removed alone at 19 (Remove_Hitbox 0)',
          ({c.name for _f, c in ring}, {int(v(c, 'Part')) for _f, c in ring}, sorted({int(v(c, 'ID')) for _f, c in ring}),
           {int(v(c, 'Bone')) for _f, c in ring}, frames, [sum(1 for f, _c in ring if f == x) for x in frames],
           [(f, c.name, list(c.params)) for f, c in tl if c.name in ('Remove_Hitbox', 'Remove_All_Hitboxes')]),
          ({'Extended_Hitbox'}, {1}, [1, 2, 3, 4, 5, 6], {0}, [14.0, 16.0, 18.0, 20.0, 22.0], [6] * 5,
           [(19.0, 'Remove_Hitbox', [0]), (24.0, 'Remove_All_Hitboxes', [])]))
    vals = {(float(v(c, 'Damage')), int(v(c, 'Angle')), int(v(c, 'KBG')), int(v(c, 'FKB')), int(v(c, 'BKB')), int(v(c, 'Effect')),
             int(v(c, 'ShieldDamage')), int(v(c, 'SFXType')), float(v(c, 'Hitlag'))) for _f, c in ring}
    check('nair ring v1: the ring\'s hits weak: 2.5 %, angle 60 (the burst\'s), KBG 25, FKB 0, BKB 25, fire (element 5, '
          'burn sound 8), no shield damage, half hitlag; no shield break anywhere in neutral air (no LASTHIT_STATUS)',
          (vals, [c for c in gn if c.name == 'SET_FLOAT']), ({(2.5, 60, 25, 0, 25, 5, 0, 8, 0.5)}, []))
    # ---- the ring's geometry against FIRE_RING (its own formula here, not GB.ring_radius)
    fx = next(c for c in e.scripts[acmd.crc('attackairn')] if c.name == 'EFFECT_FOLLOW_FLIP')
    efr = 0.0
    for c in e.scripts[acmd.crc('attackairn')]:
        if c.name == 'FRAME':
            efr = float(c.params[0])
        if c is fx:
            break
    size, cy = float(v(fx, 'Size')), float(v(fx, 'Y'))
    R = FX.FIRE_RING

    def flames(f):                       # the flames' centres' radius at frame f (t: frames since the call less one)
        t = max(0, f - efr - 1)
        return size * (R['r0'] + R['v'] * (1 - R['air'] ** t) / (1 - R['air']))
    geo, bad = [], []
    for f in frames:
        cs = sorted((c for ff, c in ring if ff == f), key=lambda c: int(v(c, 'ID')))
        pts = [((float(v(c, 'Z')), float(v(c, 'Y')) - cy), (float(v(c, 'Z2')), float(v(c, 'Y2')) - cy)) for c in cs]
        rv = [math.hypot(*p) for a_ in pts for p in a_]
        sz = {round(float(v(c, 'Size')), 3) for c in cs}
        closed = all(math.hypot(pts[k][1][0] - pts[(k + 1) % 6][0][0], pts[k][1][1] - pts[(k + 1) % 6][0][1]) < 0.01
                     for k in range(6))
        ang = sorted(round(math.degrees(math.atan2(p[0][1], p[0][0])) % 360) for p in pts)
        r, s_ = sum(rv) / len(rv), sz.pop() if len(sz) == 1 else None
        mid = r * math.cos(math.radians(30))
        tips = flames(f + 1) + GB.NAIR_RING_TIP
        inner, outer = ((r - s_) + (mid - s_)) / 2, ((r + s_) + (mid + s_)) / 2
        geo.append((f, round(flames(f + 1), 2), round(tips, 2), round(r, 2), s_))
        want_in = GB.NAIR_LATE if (tips - GB.NAIR_LATE) / 2 >= GB.NAIR_RING_MIN else (GB.NAIR_LATE + tips) / 2 - GB.NAIR_RING_MIN
        if not (max(rv) - min(rv) < 0.01 and closed and ang == [0, 60, 120, 180, 240, 300] and
                abs(outer - max(tips, (GB.NAIR_LATE + tips) / 2 + GB.NAIR_RING_MIN)) < 0.05 and abs(inner - want_in) < 0.05
                and r - s_ >= GB.NAIR_LATE and flames(f + 1) < outer):
            bad.append((f, round(inner, 2), round(outer, 2), round(tips, 2), closed, ang))
    check('nair ring v1: each set a closed hexagon of 6 capsules (corners at 0, 60 ... 300 degrees, one radius) round the '
          'burst / ring\'s centre (joint 0, Y %.1f); its band from the burst boxes\' edge (%.1f, its mean inner edge) to the '
          'ring\'s flame tips at the next frame (FIRE_RING r0 %.1f + v %.1f (1 - air %.1f^t) / (1 - air), x %.4f, + %.1f: its '
          'mean outer edge), its corners outside the burst boxes; moving out with the flames (frame, flames, tips, corner '
          'radius, capsule size): %s' % (cy, GB.NAIR_LATE, R['r0'], R['v'], R['air'], size, GB.NAIR_RING_TIP, geo),
          (bad, [x[3] for x in geo] == sorted(x[3] for x in geo) and geo[0][3] < geo[-1][3]), ([], True))
    check('nair ring v1: the ring boxes follow the effect\'s timing: the burst / ring called at %d (FIRE_RING life %d: its '
          'flames gone by %d), the boxes from the strong hit\'s end (14, the late hit) to 24, within the flames\' life' % (
              efr, R['life'], efr + R['life']),
          (efr == GB.NAIR_FX_FRAME, frames[0], max(f for f, c in tl if c.name == 'Remove_All_Hitboxes') <= efr + R['life'],
           size == GB.NAIR_FX_SIZE, cy == GB.NAIR_FX_Y), (True, 14.0, True, True, True))
    # ---- the hit records: set_attack (0x02C08848) returns at once (the record kept) when the ID is out on the same Part,
    # and clears the Part's record when an ID not out (or moved from another Part) is set on it
    live, clears, keeps, shared = {}, [], 0, set()
    for f, c in tl:
        if c.name in GB.HITBOXES:
            hid, part = int(v(c, 'ID')), int(v(c, 'Part'))
            if live.get(hid) == part:
                keeps += part == 1
            else:
                clears.append((f, part, hid))
            live[hid] = part
        elif c.name == 'Remove_Hitbox':
            live.pop(int(c.params[0]), None)
        elif c.name == 'Remove_All_Hitboxes':
            live = {}
    for f, c in hb:
        shared.add((int(v(c, 'ID')), int(v(c, 'Part'))))
    check('nair ring v1: the strong / late hits and the ring don\'t share a hit record: their own Parts (0 / 1) and IDs (0 / '
          '1-6); Part 1\'s record is cleared only when the ring is first set (frame 14, before it can hit), every later set '
          'moves IDs still out on Part 1 (24 sets: the record kept: one ring hit an opponent); the clone\'s AttackModule '
          '(a weapon: IDs 0-6, Parts 0-1) holds them',
          (sorted({p for _i, p in shared}), sorted({i for i, p in shared if p == 0}), sorted({i for i, p in shared if p == 1}),
           [x for x in clears if x[1] == 1], keeps, max(i for i, _p in shared) <= 6 and max(p for _i, p in shared) <= 1),
          ([0, 1], [0], [1, 2, 3, 4, 5, 6], [(14.0, 1, k) for k in range(1, 7)], 24, True))
    check('nair ring v1: the ring\'s hits burn (neutral air\'s row, motion 104: 0.25 %% / 15 f / 180 f) with no exe change: '
          'burn_scan takes every Part\'s hit log (entries 0 - %d, AttackModule +0x18 the highest Part in use + 1: 2) and the '
          'release marks each new record (feature mark), so a Part 1 record after a Part 0 one is new' % (C.BURN_ENTS - 1),
          ((104, 0.25, 15, 180) in C.BURN_MOVES, C.BURN_ENTS >= 2, 'mark' in C.RELEASE), (True, True, True))
    # ---- forward air
    gf = g.scripts[acmd.crc('attackairf')]
    hf = {int(v(c, 'ID')): c for c in gf if c.name in GB.HITBOXES}
    same = [n for n in hf[0].info['syntax'] if n not in ('ID', 'Y') and v(hf[0], n) != v(hf[2], n)]
    reach = round(-float(v(hf[2], 'Y')) + float(v(hf[2], 'Size')), 2)
    res = {int(c.params[0]): round(float(v(c, 'Y')), 2) for c in gf if c.name == 'ATK_RESERVE'}
    check('fair reach: forward air\'s hitbox ID 2 = ID 0 (14 %%, size 5.4) %.0f further along the blade (Y -17, its '
          'ATK_RESERVE too): reach %.1f from the hand (was 12.4); DK\'s nearest point in the user\'s screenshot %.1f '
          '(the blade 11 as the ruler): at least 2 to spare' % (GB.FAIR_EXTRA, reach, FAIR_DK),
          (sorted(hf), same, round(float(v(hf[2], 'Y')), 2), res, reach >= FAIR_DK + 2),
          ([0, 1, 2], [], -17.0, {0: -7.0, 1: 0.0, 2: -17.0}, True))
    ef = e.scripts[acmd.crc('attackairf')]
    calls = sorted((int(c.params[0]), round(float(v(c, 'Y')), 2), round(float(v(c, 'Size')), 2)) for c in ef
                   if c.name == 'External_Graphic')
    glow = [round(float(v(c, 'Y2')), 2) for c in ef if c.name == 'Sword_Glow']
    check('fair reach: longer, not bigger: a second water sword (0x%X, size 1) and its FireBlade flames (0x%X) at Y -10 '
          '(the blade 11 -> 21), the trail (Sword_Glow) to -21' % (GB.SWORD, GB.FIRE_BLADE), (calls, glow),
          (sorted([(GB.SWORD, 0.0, 1.0), (GB.SWORD, -10.0, 1.0), (GB.FIRE_BLADE, 0.0, 1.0), (GB.FIRE_BLADE, -10.0, 1.0)]),
           [-21.0]))
    # ---- the clones' copies
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone', 'c00')
    bm = GB.bone_map(open(os.path.join(mdl, 'model.jtb'), 'rb').read(), os.path.join(mdl, 'model.vbn'))
    diff = []
    for nm in ('attackairn', 'attackairf'):
        mine = [c for c in g.scripts[acmd.crc(nm)] if c.name in GB.HITBOXES]
        theirs = [c for c in cg.scripts[acmd.crc(nm)] if c.name in GB.HITBOXES]
        if len(mine) != len(theirs):
            diff.append((nm, len(mine), len(theirs)))
            continue
        for a_, b_ in zip(mine, theirs):
            p = list(a_.params)
            p[a_.info['syntax'].index('Bone')] = bm(int(v(a_, 'Bone')))
            if a_.ident != b_.ident or p != list(b_.params):
                diff.append((nm, int(v(a_, 'ID'))))
    cef = sorted((int(c.params[0]), round(float(v(c, 'Y')), 2)) for c in ce.scripts[acmd.crc('attackairf')]
                 if c.name == 'External_Graphic')
    check('nair ring v1 / fair reach: the clones\' copies the same (their scripts are his: neutral air\'s 33 hitbox sets, '
          'forward air\'s 3 hitboxes, bones as the article\'s; its second sword and flames)',
          (diff, len([c for c in cg.scripts[acmd.crc('attackairn')] if c.name in GB.HITBOXES]), cef),
          ([], 33, sorted([(GB.SWORD, 0.0), (GB.SWORD, -10.0), (GB.FIRE_BLADE, 0.0), (GB.FIRE_BLADE, -10.0)])))


FP_SLOT = 2                       # the fighter hit: player slot 3 (fighter table entry 2)


def fp_setup(mscsb, src):
    """smash tune v1: him in forward smash (0x2D) on the floor (y 10) at x 0 facing right, his own slot (0) at his place"""
    m = fresh(mscsb, src)
    g = m.game
    m.vm.g[4], m.vm.g[18], m.vm.g[24] = 0x2D, 0, 0
    g.x, g.y, g.lr, g.frame = 0.0, 10.0, 1.0, 14.0
    return m, g


def fp_frame(m, g, tx, hit=2, hitlag=0, ty=10.0, cmd=0):
    """one frame of his forward smash's loop (gk_chain_try): the fighter in slot FP_SLOT at (tx, ty), target 12 (this attack's
    hit) its offset from him when `hit` (AttackModule 0x2727 kinds: 2 a hurtbox, 4 a shield), his hitlag"""
    V = g.vars
    V[0x0F000020], V[0x0F000021] = g.x, g.y
    V[0x0F000020 + 4 * FP_SLOT], V[0x0F000021 + 4 * FP_SLOT] = tx, ty
    V[0x0F0002CD], V[0x0F0002CE] = ((tx - g.x) * g.lr, ty - g.y) if hit else (0.0, 0.0)
    g.atk_hit = hit
    g.hitlag = hitlag
    m.vm.g[24] = cmd
    return m('gk_chain_try', 1)


def fp_trace(m, g, tx0=60.0, v0=2.5, decay=0.9, lag=6, n=40, hit=2):
    """the hit at frame 13 (his and its hitlag `lag` frames), then the fighter sliding away at v0 slowing x decay a frame:
    [(frame, his x, its x)]"""
    tr, tx, v = [], tx0, v0
    for t in range(n):
        if t >= lag:
            tx, v = round(tx + v, 3), v * decay
        fp_frame(m, g, tx, hit=hit, hitlag=1 if t < lag else 0)
        tr.append((13 + t, round(g.x, 3), round(tx, 3)))
    return tr


def smash_tune_tests(mscsb, src, out, user):
    """smash tune v1 (README "Smash tune v1"): forward smash's pursuit (MSC, run here), the smashes' uncharged damage (the
    charge ratio 0: the attack's power 1.0; the clones' copies x1.0), up smash's inner sword hits a weak diagonal spike,
    the smashes' shield damage x0.5 (exe feature shalf: its unicorn test in gekkouga_clone_cave_test; here the numbers),
    the clones' jumps by his Tap Jump setting, the burn rows unchanged"""
    import gekkouga_clone_cave as C
    # ---- 1. forward smash pursuit
    m, g = fp_setup(mscsb, src)
    tr = fp_trace(m, g)
    xs = [x for _f, x, _t in tr]
    steps = [round(b - a, 3) for a, b in zip([0.0] + xs, xs)]
    gaps = [round(t - x, 2) for _f, x, t in tr]
    lag = 6
    moving = [s_ for s_ in steps[lag:] if s_ > 0]
    check('smash tune v1, pursuit: nothing during his hitlag (frames 13 - 18: the hit found, target 12\'s place matched to '
          'slot 3); then a burst (4, 8 a frame: gk_fp_acc 4) at its top speed 8 while far, slowing smoothly (each step '
          'smaller) as he closes in; never past the stop point (the gap >= 12), ending 12 - 13.5 short of the sliding '
          'fighter; trace (frame, his x, its x): %s' % (tr[::3],),
          (steps[:lag], steps[lag:lag + 3], all(b <= a + 1e-6 for a, b in zip(moving[2:], moving[3:])),
           min(gaps) >= 12.0 - 1e-3, 12.0 <= gaps[-1] <= 13.5, R.s32(m.g('gk_fp_slot'))),
          ([0.0] * lag, [4.0, 8.0, 8.0], True, True, True, -1))
    PRE = os.environ.get('GK_PURSUIT_TRACE')
    if PRE:
        open(PRE, 'w').write('\n'.join('%d %.3f %.3f' % x for x in tr) + '\n')
    m, g = fp_setup(mscsb, src)
    for t in range(40):
        fp_frame(m, g, 50.0, hit=4 if t == 0 else 4, hitlag=1 if t < 4 else 0)
    check('pursuit on a shield (kind 4): the same run, to 12 short of the shielding fighter (at 50: he ends at 37.8 - 38)',
          37.8 <= g.x <= 38.0, True)
    m, g = fp_setup(mscsb, src)
    for t in range(30):
        fp_frame(m, g, 50.0, hit=0)
    check('no hit / shield yet (AttackModule 0x2727 kinds 6 off): he stays', (g.x, m.g('gk_fp_slot')), (0.0, 0))
    m, g = fp_setup(mscsb, src)
    for t in range(30):
        fp_frame(m, g, -40.0, hit=2, hitlag=1 if t < 3 else 0)
    check('the fighter behind him (x -40, he faces right): he stays (never backwards, never through it)', g.x, 0.0)
    m, g = fp_setup(mscsb, src)
    g.lr = -1.0
    for t in range(40):
        fp_frame(m, g, -50.0, hit=2, hitlag=1 if t < 3 else 0)
    check('facing left, the fighter at -50: he runs left to -37.8 - -38', -38.0 <= g.x <= -37.8, True)
    m, g = fp_setup(mscsb, src)
    g.floors = [(-100.0, 30.0, 10.0)]                # the stage's edge at 30
    for t in range(40):
        fp_frame(m, g, 70.0, hit=2, hitlag=1 if t < 3 else 0)
    check('a ledge at 30 (the fighter at 70, off the stage): he stops at the ledge (1 short of it: gk_fp_edge, on the floor) '
          'and the pursuit ends', (28.8 <= g.x <= 29.0, g.y, R.s32(m.g('gk_fp_slot'))), (True, 10.0, -1))
    m, g = fp_setup(mscsb, src)
    g.walls = [(25.0, 0.0, 100.0)]
    for t in range(40):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    check('a wall at 25: he stops 3 short of it (22) and the pursuit ends', (round(g.x, 2), R.s32(m.g('gk_fp_slot'))),
          (22.0, -1))
    m, g = fp_setup(mscsb, src)
    g.floors = [(-100.0, 20.0, 10.0), (20.0, 200.0, 14.0)]   # a step up of 4 at 20
    for t in range(40):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    check('a step up of 4 at x 20 on his way: he goes on along the floor (y 14 there) to 47.8 - 48', (47.8 <= g.x <= 48.0, g.y),
          (True, 14.0))
    m, g = fp_setup(mscsb, src)
    for t in range(6):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    x6 = g.x
    g.vars[0x0F0000A2 + 8 * (FP_SLOT + 3)] = 0xB1
    fp_frame(m, g, 60.0)
    check('the fighter KO\'d (status 0xB1): over, he stops', (g.x == x6, R.s32(m.g('gk_fp_slot'))), (True, -1))
    m, g = fp_setup(mscsb, src)
    for t in range(6):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    m.vm.g[18] = 2
    x6 = g.x
    fp_frame(m, g, 60.0)
    check('in the air (situation 2): over, no move', (g.x == x6, R.s32(m.g('gk_fp_slot'))), (True, -1))
    m, g = fp_setup(mscsb, src)
    for t in range(60):
        fp_frame(m, g, 400.0, hit=2, hitlag=1 if t < 3 else 0)
    check('the longest pursuit: %d frames after his hitlag (the fighter far: %d x 8 - 4 = he moves %d at most)' % (
        m('gk_fp_frames'), m('gk_fp_frames'), m('gk_fp_frames') * 8 - 4), (round(g.x, 2), R.s32(m.g('gk_fp_slot'))),
          (m('gk_fp_frames') * 8.0 - 4.0, -1))
    # the chain: an up smash input during the burst (frame 16+: forward smash's last hitbox's end)
    m, g = fp_setup(mscsb, src)
    for t in range(5):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    g.frame = 16.0
    g.status_req = []
    r = fp_frame(m, g, 60.0, cmd=0x20)
    check('during the burst an up smash input chains (gk_chain_try: its start 0x31, auto): the pursuit ends (gk_fp_end) '
          'and the chain works', (r, g.status_req, m.g('gk_fp_slot'), m.g('gk_chain_req')), (1, [(0x31, 1)], 0, 0x2))
    m, g = fp_setup(mscsb, src)
    for t in range(6):
        fp_frame(m, g, 60.0, hit=2, hitlag=1 if t < 3 else 0)
    frames(m, 1, st=0)
    check('he leaves forward smash (Wait): gekkouga_frame ends the pursuit', (m.g('gk_fp_slot'), m.g('gk_fp_t')), (0, 0))
    m, g = fp_setup(mscsb, src)
    m.vm.g[4] = 0x33
    for t in range(10):
        m.vm.g[4] = 0x33
        g.atk_hit = 2
        m('gk_chain_try', 2)
    check('up smash (0x33) / down smash hitting: no pursuit (forward smash only)', (g.x, m.g('gk_fp_slot')), (0.0, 0))
    # ---- 2. uncharged damage: the release's ratio, func_345's power (1 + (0x0200003E - 1) x ratio)
    pw = []
    for store, auto in ((120, 1), (0, 2)):
        m = fresh(mscsb, src)
        g = m.game
        g.vars[0x200003E], g.vars[0x26] = 1.4, 0.0
        m.setg('gk_smash', store)
        m.setg('gk_sm_auto', auto)
        m.vm.g[4] = 0x2B
        m('gk_sm_release', 1)
        m.vm.g[4] = 0x2D
        g.log = []
        m('func_345')
        pw.append((g.vars.get(0x1000000), 0x21000002 in g.flags, [x for x in g.log if x[0] == 'power']))
    g.vars[0x1000000] = 1.0
    g.log = []
    m('func_345')
    old = [x for x in g.log if x[0] == 'power']
    check('uncharged: a full stored charge (120) and a chain (0) both release with the charge ratio 0, charged flag on: '
          'the attack\'s power (func_345, AttackModule 0x2728) 1.0, the uncharged damage (ratio 1.0, before: 1.4)',
          (pw, old), ([(0.0, True, [('power', 1.0)])] * 2, [('power', 1.4)]))
    rows = {k: (d, i, f) for k, d, i, f in C.BURN_MOVES}
    src_c = open(os.path.join(HERE, 'gekkouga_clone_cave.py')).read()
    check('uncharged: the burn is unchanged at every charge: its rows are keyed by the move\'s motion kind (burn_scan reads '
          'the attacker\'s motion kind, never the hit\'s damage): forward / up / down smash 0.4 %% every 6 f for 240 f '
          '= %.0f %% (shielded %.1f %%), as before' % (C.burn_total(C.BURN_MOVES[0]), C.burn_total(C.BURN_MOVES[0], True)),
          ([rows[k] for k in (95, 99, 101)], 'lwz r0, %(mm_kind)d(r12)        # its motion kind' in src_c),
          ([(0.4, 6, 240)] * 3, True))
    # ---- 3. up smash's spike, 4. shield damage (the scripts)
    B = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd')
    gm = acmd.ACMDFile.load(os.path.join(B, 'body', 'game.bin'))
    cg = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'clone', 'game.bin'))
    pv = lambda c, n: c.params[c.info['syntax'].index(n)]
    tl, fr = [], 0.0
    for c in gm.scripts[acmd.crc('attackhi4')]:
        if c.name == 'FRAME':
            fr = float(c.params[0])
        tl.append((fr, c))
    at18 = sorted((int(pv(c, 'ID')), int(pv(c, 'Bone')), float(pv(c, 'Y')), float(pv(c, 'Size')), float(pv(c, 'Damage')),
                   int(pv(c, 'Angle')), int(pv(c, 'KBG')), int(pv(c, 'BKB')), int(pv(c, 'FKB'))) for f, c in tl
                  if f == 18.0 and c.name in GB.HITBOXES)
    res = sorted((int(c.params[0]), int(pv(c, 'Bone')), float(pv(c, 'Y'))) for f, c in tl if c.name == 'ATK_RESERVE' and f == 15.0)
    later = [(f, c.name, int(c.params[0])) for f, c in tl if f > 18 and c.name in GB.HITBOXES + ('Remove_Hitbox',)]
    kb = lambda pc, d=11.0, kbg=50, bkb=25: round(((pc / 10.0 + pc * d / 20.0) * 1.0 * 1.4 + 18) * kbg / 100.0 + bkb, 1)
    check('up smash spike: at 18 the geyser (ID 0) and both swords; the inner hits (at the hands: Y 0, size 17.5, nearer '
          'his body) now IDs 1 / 2 (the lower IDs: they win where the outer ones overlap them) at %d degrees (down and away, '
          'by position: behind him down and back), KBG %d / BKB %d (weak: KB %.0f at 0 %%, %.0f at 100 %%, %.0f at 150 %% on '
          'weight 100; tumble from 80), 11 %% (the uncharged damage); the outer ones IDs 3 / 4 as before (44, KBG 100, BKB '
          '30; usmash spike v2: they and the geyser spike too: usmash_trail_tests); their reserves renumbered; the geyser off '
          'at 19; at 21 the body capsule (ID 1) and IDs 2 - 4 removed as before' % (
              GB.USMASH_SPIKE['Angle'], GB.USMASH_SPIKE['KBG'], GB.USMASH_SPIKE['BKB'], kb(11), kb(111), kb(161)),
          (at18, res, later),
          ([(0, 0, 27.0, 30.0, 14.0, 300, 50, 25, 0), (1, 0x19, 0.0, 17.5, 11.0, 300, 50, 25, 0),   # (usmash spike v2:
            (2, 0x18, 0.0, 17.5, 11.0, 300, 50, 25, 0), (3, 0x19, -20.0, 23.5, 11.0, 300, 50, 25, 0),   # the geyser and the
            (4, 0x18, -20.0, 23.5, 11.0, 300, 50, 25, 0)],                                            # outer hits too)
           [(0, 0, 27.0), (1, 0x19, 0.0), (2, 0x18, 0.0), (3, 0x19, -4.0), (4, 0x18, -4.0)],
           [(19.0, 'Remove_Hitbox', 0), (21.0, 'Extended_Hitbox', 1), (21.0, 'Remove_Hitbox', 2),
            (21.0, 'Remove_Hitbox', 3), (21.0, 'Remove_Hitbox', 4)]))
    ch = [c for c in cg.scripts[acmd.crc('attackhi4')] if c.name in GB.HITBOXES]
    mine = [c for c in gm.scripts[acmd.crc('attackhi4')] if c.name in GB.HITBOXES]
    check('up smash spike: the clones\' copy the same (IDs, angle 300, KBG 50, BKB 25, 11 %: x1.0), bones the article\'s',
          [(int(pv(a, 'ID')), int(pv(a, 'Angle')), int(pv(a, 'KBG')), int(pv(a, 'BKB')), float(pv(a, 'Damage'))) for a in ch],
          [(int(pv(a, 'ID')), int(pv(a, 'Angle')), int(pv(a, 'KBG')), int(pv(a, 'BKB')), float(pv(a, 'Damage'))) for a in mine])
    table, neg = [], []
    for nm in ('attacks4', 'attackhi4', 'attacklw4'):
        for f, c in [(0, c) for c in gm.scripts[acmd.crc(nm)] if c.name in GB.HITBOXES]:
            d, sd = float(pv(c, 'Damage')), int(pv(c, 'ShieldDamage'))
            neg += [sd] if sd < 0 else []
            table.append((nm, int(pv(c, 'ID')), d, round((d * 1.4 + sd) * 1.19, 2), round((d + sd) * 1.19, 2),
                          round((d + sd) * 1.19 * C.SH_SCALE, 2)))
    check('shield damage x0.5 (exe feature shalf: the shield hit\'s pending damage halved before the 1.19 multiplier for a '
          'Greninja\'s attack in motion 95 / 99 / 101 or with the trail\'s Type): per hitbox (move, ID, damage, shield '
          'damage before this package (x1.4 charge), uncharged, now): %s; every ShieldDamage field 0 (never negative)'
          % table, (neg, all(abs(t[5] - t[4] / 2) < 0.01 for t in table), 'shalf' in C.RELEASE, C.SH_KINDS,
                     sorted(k for k, _d, _i, _f in C.BURN_MOVES if k < 0x100 and _d == 0.4), C.SH_SCALE),
          ([], True, True, (95, 99, 101), [95, 99, 101], 0.5))
    tg = acmd.ACMDFile.load(os.path.join(B, 'weapon', 'firetrail', 'game.bin'))
    types = {}
    for fn, ff in (('body', gm), ('clone', cg), ('firetrail', tg)):
        for crc, sc in ff.scripts.items():
            for c in sc:
                if c.name in GB.HITBOXES and int(pv(c, 'Type')) == C.SH_TYPE:
                    types[fn] = types.get(fn, 0) + 1
    sk = os.path.join(B, 'weapon', 'skeleton', 'game.bin')
    if os.path.exists(sk):
        for crc, sc in acmd.ACMDFile.load(sk).scripts.items():
            types['skeleton'] = types.get('skeleton', 0) + sum(1 for c in sc if c.name in GB.HITBOXES and
                                                                 int(pv(c, 'Type')) == C.SH_TYPE)
    check('shield damage x0.5: the fire trails\' hitboxes (0.1 %%: their shield damage 0.119 -> 0.06) carry Type 0x%X '
          '(Water: unused in Smash 4), and only they do (his, the clones\', the skeleton\'s none): the exe\'s marker'
          % C.SH_TYPE, (types.get('firetrail', 0) > 0, types.get('body', 0), types.get('clone', 0), types.get('skeleton', 0),
                        GB.TR_HIT['Type']), (True, 0, 0, 0, C.SH_TYPE))
    # ---- 5. the clones' jumps and his Tap Jump setting
    got = {}
    for tap in (False, True):
        for cmd in (0x100000, 0x200000):
            m, g, _tr = ak_run(mscsb, src, True, frames_=24)
            for _ in range(200):
                ak_frame(m, g, st=0xE)
                if m('gk_bvi', 1, 0) < 10 and m('gk_bvi', 2, 0) < 10:
                    break
            for _ in range(20):
                ak_frame(m, g, st=0)
            g.tap_jump = tap
            ak_frame(m, g, st=0x28 if cmd == 0x100000 else 0xA, cmd=cmd, stick=(0.0, 0.9) if cmd == 0x100000 else (0, 0))
            got[(tap, cmd)] = (ak_cmd(g, 1)[0], m('gk_bvi', 1, 0))
    check('clones and Tap Jump (ControlModule 0x271C: his input frame\'s 0x8000, the game\'s own stick-jump check): split '
          'clones on the ground, his stick flicked up (command 0x100000, an up tilt: the game makes the bit whatever the '
          'setting): Tap Jump off: no jump (they stay, action 0); on: the squat (0x18, action 1); the jump button '
          '(0x200000): the squat either way', got,
          {(False, 0x100000): (0, 0), (False, 0x200000): (0x18, 1), (True, 0x100000): (0x18, 1), (True, 0x200000): (0x18, 1)})
    vys = {}
    for tap in (False, True):
        for held, sy in ((False, 0.9), (True, 0.0), (False, 0.0)):
            m = fresh(mscsb, src)
            g = m.game
            g.tap_jump = tap
            g.held = {2} if held else set()
            m('gk_jump', 1, f2i(0.0), f2i(sy))
            vys[(tap, held, sy)] = m.gf('gk_lvy')
    check('clones and Tap Jump: the squat\'s end: a full jump (4.07) with the jump button held, or the stick up (0.9) only '
          'with Tap Jump on; else the short hop (2.82)', vys,
          {(False, False, 0.9): 2.82, (False, True, 0.0): 4.07, (False, False, 0.0): 2.82,
           (True, False, 0.9): 4.07, (True, True, 0.0): 4.07, (True, False, 0.0): 2.82})
    air = {}
    for tap in (False, True):
        m, g, _tr = ak_run(mscsb, src, True, frames_=24)
        g.tap_jump = tap
        n0 = m('gk_bvi', 1, 9)
        ak_frame(m, g, st=0xE, cmd=0x100000, stick=(0.0, 0.9))
        air[tap] = (n0, m('gk_bvi', 1, 9), ak_cmd(g, 1)[0] == 0x1B)
    check('clones and Tap Jump: in the air (after the kick), his stick flicked up: their double jump (JumpAerialF 0x1B) only '
          'with Tap Jump on', air, {False: (0, 0, False), True: (0, 1, True)})
    src_c = open(src).read()
    check('clones and Tap Jump: the clones\' jumps all go through gk_jump_cmd (no bare command 0x300000 test left); the '
          'other settings they mirror come with his command bits (A+B smash, Stick Smash off: applied to the inputs before '
          'the game builds them)', ('cmd & 0x300000' in src_c, src_c.count('gk_jump_cmd(cmd)')), (False, 2))


def ib_kb(damage, percent, weight=100.0, kbg=None, bkb=None):
    """Smash 4's knockback (the community sheet's formula, no staleness / rage): the victim at `percent` before the hit"""
    import gekkouga_build as _gb  # noqa: F401
    kbg = 80 if kbg is None else kbg
    bkb = 50 if bkb is None else bkb
    p = percent + damage
    return ((p / 10.0 + p * damage / 20.0) * 200.0 / (weight + 100.0) * 1.4 + 18.0) * kbg / 100.0 + bkb


def ice_tests(mscsb, src, tr_mscsb, out, user):
    """ice detonation v1 (README "Ice detonation v1"): his MSC's side (gk_ib_tick: the executable's blast request made into
    article 9 with the explosion's sound, a retry, its lapse, a reset), the fire trail's blast mode (the hitbox's damage /
    size by the burn amount, angle / knockback / facing / element, its explosion effect sized with it, its end; a trail
    with no burn context gone at once), the shuriken's uncharged ice and sparkles, the explosion's ids and sizes"""
    import gekkouga_clone_cave as C
    V = C.ICE3_VAR                                # parabeetle v2: his New_Var 60 - 63 (v1 / v2: 48 - 51)
    # ---- his side
    m = fresh(mscsb, src)
    g = m.game

    def sysf(sid, a, old=g.sys):
        if sid == 0x1E:
            g.log.append(('sound', a[0], a[1]))
            return 1
        return old(sid, a)
    g.sys = sysf
    frames(m, 2, 0)
    arts = lambda: [x for x in g.log if x[0] in ('article', 'sound')]   # noqa: E731
    g.log = []
    frames(m, 3, 0)
    check('ice: no blast request: no article', arts(), [])
    g.vars[V], g.vars[V + 1], g.vars[V + 2], g.vars[V + 3] = 4.25, 30.0, 21.0, -1.0
    got = []
    for _ in range(8):
        g.log = []
        frames(m, 1, 0x2D)
        got.append(arts())
    check('ice: the executable\'s blast request (his gk_vi(60) = 4.25): article 9 made at once (usmash spike v2 / trail dim '
          'v1: no sound of its own: the skeleton\'s 0x%X gone, the detonation\'s own sound plays from the arming), again 3 '
          'frames later (not claimed yet), then nothing; dropped after %d frames' % (0x7680060, 6),
          (got, g.vars.get(V)),
          ([[('article', 0x2710, 9)], [], [], [('article', 0x2710, 9)], [], [], [], []], 0.0))
    g.vars[V] = 4.5
    g.log = []
    frames(m, 1, 0xB1)
    g.vars[V] = 0.0                               # the executable's claim takes it
    frames(m, 2, 0xB1)
    g.vars[V] = 4.1
    g.log = []
    frames(m, 1, 0)
    check('ice: claimed (his request 0 again): the next request starts over (made at once, in any status: KO\'d too)', arts(),
          [('article', 0x2710, 9)])
    m('gk_reset')
    check('ice: a reset (gk_reset): the request gone', (g.vars.get(V), m.g('gk_ib_t')), (0.0, 0))
    check('ice: his MSC reads the request the executable writes (gk_vi(60) = 0x%08X = ICE3_VAR, the release\'s)' % V,
          ('WorkModuleF(0, 0x%08x)' % V in open(os.path.join(ROOT, 'fighters', 'gekkouga', 'clones.c')).read(),
           0x0F000380 + 60, C.ice_vars(C.RELEASE)[0]), (True, V, V))
    # ---- the blast (firetrail.c)
    t = MSC(tr_mscsb, GB.TRAIL_MSC)

    def make():
        mm = MSC(tr_mscsb, GB.TRAIL_MSC)
        gg = mm.game

        def sysf2(sid, a, old=gg.sys):
            if sid == 0x12 and a[0] == 0x1:
                gg.log.append(('motion', a[1]))
                return 0
            if sid == 0x14 and a[0] == 0:
                gg.log.append(('lr', fv(a[1])))
                return 0
            if sid == 0x21 and a[0] == 0x9:
                gg.log.append(('remove',))
                return 0
            if sid == 0x2E:
                gg.log.append(('attack', a[0]) + tuple(a[1:]))
                return 0
            if sid == 0x1C:
                gg.log.append(('fx', a[0]) + tuple(a[1:]))
                return 0
            return old(sid, a)
        gg.sys = sysf2
        return mm, gg
    syn = ['ID', 'Part', 'Bone', 'Damage', 'Angle', 'KBG', 'FKB', 'BKB', 'Size', 'X', 'Y', 'Z', 'Effect', 'Trip', 'Hitlag',
           'SDI', 'Clang', 'Rebound', 'ShieldDamage', 'SFXLevel', 'SFXType', 'Ground/Air', 'Direct/Indirect', 'Type',
           'HitBits', 'Unk41', 'CollisionPart', 'NoScale', 'Shieldable', 'Reflectable', 'Absorbable', 'Rehit',
           'IgnoreInvuln', 'HitAllStates', 'FacingRestrict', 'NoGrabRelease', 'TeamDamage', 'DisableHitlag', 'NoGFX',
           'Flinchless', 'X2', 'Y2', 'Z2']
    floats = {'Damage', 'Size', 'X', 'Y', 'Z', 'Trip', 'Hitlag', 'SDI', 'X2', 'Y2', 'Z2'}
    import acmd as _a
    by = {v['name']: k for k, v in _a.INFO.items()}
    check('ice: the blast\'s AttackModule 0x272C arguments are Extended_Special_Hitbox\'s, in order',
          _a.INFO[by['Extended_Special_Hitbox']]['syntax'], syn)
    lv = []
    for b, way in ((5.0, 1.0), (20.0, -1.0), (60.0, 1.0)):
        mm, gg = make()
        gg.vars.update({0x0F000300: 3.0, 0x0F000301: 4.0 + b / 100.0, 0x0F000302: 30.0, 0x0F000303: 21.0,
                        0x0F000304: way, 0x0F000305: 0.0})
        mm('tr_frame')
        hb = [x for x in gg.log if x[0] == 'attack' and x[1] == 0x272C]
        h = dict(zip(syn, hb[0][2:])) if hb else {}
        h = {k: round(fv(v), 3) if k in floats else v for k, v in h.items()}
        fx = [x for x in gg.log if x[0] == 'fx' and x[1] == 0x3]
        L = min(1.0, b / 40.0)
        lv.append((b, L, h.get('Damage'), h.get('Size')))
        check('ice blast, burn amount %g (level %.3f), way %+d: facing %+d (its model turned), at (30, 21), motion 3 '
              '(FireTrailIceBoom); one hitbox %.2f %% size %.2f (5 + 13 L / 8 + 14 L), angle 60, KBG 80, BKB 50, flame, '
              'explosion sound, forward (FacingRestrict 3), shieldable, no extra shield damage, no clank; its explosion '
              '(0x3300023) there at size %.3f (the hitbox / 10)' % (b, L, way, way, 5 + 13 * L, 8 + 14 * L, (8 + 14 * L) / 10),
              ([x for x in gg.log if x[0] in ('lr', 'motion')], gg.posture_sets[:1], len(hb),
               [h.get(k) for k in ('ID', 'Part', 'Bone', 'Damage', 'Size', 'Angle', 'KBG', 'FKB', 'BKB', 'Effect', 'SFXType',
                                   'SFXLevel', 'FacingRestrict', 'Shieldable', 'ShieldDamage', 'Clang', 'Rebound',
                                   'Ground/Air', 'HitBits', 'Hitlag', 'X', 'Y', 'Z')],
               [(x[2], round(fv(x[3]), 2), round(fv(x[4]), 2), round(fv(x[9]), 3)) for x in fx]),
              ([('lr', way), ('motion', 3)], [(30.0, 21.0)], 1,
               [0, 0, 0, round(5 + 13 * L, 3), round(8 + 14 * L, 3), 60, 80, 0, 50, 5, 0xB, 2, 3, 1, 0, 0, 0, 3, 0x3F, 1.0,
                0.0, 0.0, 0.0],
               [(0x3300023, 30.0, 21.0, round((8 + 14 * L) / 10, 3))]))
        gg.log = []
        for _ in range(4):
            mm('tr_frame')
        off = [x for x in gg.log if x[0] == 'attack']
        gg.log = []
        for _ in range(64):
            mm('tr_frame')
        rem1 = [x for x in gg.log if x[0] == 'remove']
        mm('tr_frame')
        rem2 = [x for x in gg.log if x[0] == 'remove']
        check('ice blast (amount %g): its hitbox off at frame 5 (AttackModule 0x2719: one hit each), it stays put, gone at '
              'frame 70' % b, (off, rem1, rem2, gg.posture_sets[-1]), ([('attack', 0x2719)], [], [('remove',)], (30.0, 21.0)))
    check('ice blast: the scaling (amount b = remaining burn + 0.5 a stack; L = b / 40, at most 1): 5 -> L 0.125 6.6 %% / '
          'size 9.75; 20 -> 0.5 11.5 %% / 15; 60 -> 1 18 %% / 22', [(b, round(L, 3), d, s_) for b, L, d, s_ in lv],
          [(5.0, 0.125, 6.625, 9.75), (20.0, 0.5, 11.5, 15.0), (60.0, 1.0, 18.0, 22.0)])
    kbs = [(d, round(ib_kb(d, p)), p) for d in (5.0, 11.5, 18.0) for p in (0, 60, 120)]
    check('ice blast knockback (KBG 80, BKB 50; weight 100, no rage / staleness): at 0 / 60 / 120 %%: weak blast (5 %%) '
          '%d / %d / %d, half (11.5 %%) %d / %d / %d, full (18 %%) %d / %d / %d' % tuple(k for _d, k, _p in kbs),
          [k for _d, k, _p in kbs], [round(ib_kb(d, p)) for d in (5.0, 11.5, 18.0) for p in (0, 60, 120)])
    mm, gg = make()
    gg.vars.update({0x0F000300: 3.0, 0x0F000301: 1.0, 0x0F000302: 0.0, 0x0F000303: 0.0, 0x0F000304: 1.0, 0x0F000305: 0.0})
    mm('tr_frame')
    check('ice detonation v1: a fire trail claimed with no burn context (a 7th / 8th in article 9\'s list): gone at once, '
          'nothing drawn (at most 6 burning trails, as before)',
          [x for x in gg.log if x[0] in ('remove', 'fx', 'motion')], [('remove',)])
    check('ice blast: the effect ids: the explosion 0x3300023, the shuriken\'s sparkles 0x3300024 (his bank\'s entries 0x23 / '
          '0x24, after the burn tiers\': gekkouga_fx_test checks them against the bank)', (t('ib_fx'), GB.ICE_SPARKLE),
          (0x3300023, 0x3300024))
    # ---- the shuriken
    sd = os.path.join(user, 'weapon', 'shuriken')
    od = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon', 'shuriken')
    vg, ve = acmd.ACMDFile.load(os.path.join(sd, 'game.bin')), acmd.ACMDFile.load(os.path.join(sd, 'effect.bin'))
    pg, pe = acmd.ACMDFile.load(os.path.join(od, 'game.bin')), acmd.ACMDFile.load(os.path.join(od, 'effect.bin'))
    shot = acmd.crc('Shot')
    s = pg.scripts[shot]
    names = [c.name for c in s]
    check('ice: the shuriken\'s Shot: Float_Var_Compare(5, <, 0.1) (its charge float 5, the one its sound script splits at '
          '0.5) True: IDs 0 / 1 + ATK_LERP, Else: vanilla\'s, Script_End',
          (names, list(s[0].params[:2]), round(s[0].params[2], 3)),
          (['Float_Var_Compare', 'True', 'Special_Hitbox', 'Special_Hitbox', 'ATK_LERP', 'Else', 'Special_Hitbox',
            'Special_Hitbox', 'ATK_LERP', 'Script_End'], [5, 4], 0.1))
    pos, at = [], 0
    for c in s:
        pos.append(at)
        at += 1 + len(c.params)
    check('ice: ... the True / Else jumps land on the Else branch / the end',
          (pos[1] + s[1].params[0], pos[5] + s[5].params[0]), (pos[6], pos[9]))
    van = vg.scripts[shot]
    diff = []
    for a, b_ in zip(s[2:4], van[:2]):
        da, db = dict(zip(a.info['syntax'], a.params)), dict(zip(b_.info['syntax'], b_.params))
        diff.append(sorted((k, db[k], da[k]) for k in da if da[k] != db[k]))
    check('ice: the uncharged hitboxes = vanilla\'s but Effect 2 -> 4 (ice) and the hit sound 3 -> 0x1C (ice); the charged '
          'branch is vanilla\'s exactly', (diff, [(c.name, c.params) for c in s[6:9]] == [(c.name, c.params) for c in van[:3]]),
          ([[('Effect', 2, 4), ('SFXType', 3, 0x1C)]] * 2, True))
    check('ice: every other shuriken script as vanilla (MaxShot 0xF744D20D, the charged max shot, included)',
          sorted(k for k in set(vg.scripts) | set(pg.scripts) if k != shot and
                 [(c.name, c.params) for c in vg.scripts.get(k, [])] != [(c.name, c.params) for c in pg.scripts.get(k, [])]),
          [])
    e_ = pe.scripts.get(shot, [])
    eg = dict(zip(e_[2].info['syntax'], e_[2].params)) if len(e_) > 2 else {}
    check('ice: its effect script (vanilla: empty): the same compare, True: External_Graphic PtcGekkougaIceSparkle (0x%X) '
          'following its joint 0, size 1, for its flight (Terminate 1)' % GB.ICE_SPARKLE,
          ([c.name for c in e_], list(e_[0].params[:2]) if e_ else None, e_[1].params[0] if len(e_) > 1 else None,
           [eg.get(k) for k in ('Graphic', 'Bone', 'X', 'Y', 'Z', 'Size', 'Terminate')], len(ve.scripts),
           sorted(pe.scripts) == [shot]),
          (['Float_Var_Compare', 'True', 'External_Graphic', 'Script_End'], [5, 4], 13,
           [GB.ICE_SPARKLE, 0, 0.0, 0.0, 0.0, 1.0, 1], 0, True))
    kb0 = ((3.0 / 10 + 3.0 * 3.0 / 20) * 1.4 + 18) * 0.85 + 10
    p52 = next(p for p in range(0, 300) if ((((p + 3) / 10 + (p + 3) * 3.0 / 20) * 1.4 + 18) * 0.85 + 10) > 52.5)
    check('ice: the uncharged shot\'s knockback (3 %%, KBG 85, BKB 10, weight 100): %.1f at 0 %%, over 52.5 (a freeze, 12 x 3 = '
          '36 frames) from %d %%: under that only the ice hit effect' % (kb0, p52), (round(kb0, 1), p52), (26.2, 89))
    names_txt = open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand', 'ModAnimNames.txt')).read()
    check('ice: FireTrailIceBoom in ModAnimNames.txt (-> its carrier\'s animation)',
          '\nFireTrailIceBoom -> firetrail/FitPacmanFirehydrantMainD03SpecialLw.omo' in names_txt, True)


def invuln_tests(mscsb, src, out, vanilla_vl):
    """round gauge v1.1 package (the user: "please remove the invulnerability from the charge"): his vl's stance motions
    without their intangible window (the fighter update's, docs/native-notes.md), every other byte his; the stance's MSC
    keeps his body state normal every frame and never sets intangibility or a shield"""
    v = open(os.path.join(out, 'param', 'fighter', 'fighter_param_vl_gekkouga.bin'), 'rb').read()
    v0 = open(vanilla_vl, 'rb').read()
    diff = [i for i in range(len(v0)) if v[i] != v0[i]] if len(v) == len(v0) else None
    r = subprocess.run([sys.executable, os.path.join(HERE, 'fighter_param_vl.py'), 'dump', os.path.join(
        out, 'param', 'fighter', 'fighter_param_vl_gekkouga.bin'), '--kind', 'gekkouga', '--only', 'm0', '--no-labels'],
        capture_output=True, text=True).stdout
    win = {}
    for ln in r.splitlines():
        mm = re.match(r'm0\[(\d+)\]\.([34])\s+u8\s+(\d+)', ln)
        if mm:
            win.setdefault(int(mm.group(1)), [0, 0])[int(mm.group(2)) - 3] = int(mm.group(3))
    check('charge invulnerability: his vl\'s SpecialLw / SpecialAirLw (0x271 / 0x289) intangible window 0 / 0 (was 8 - 19: '
          'the charge holds the motion at 14, so from frame 8 on he was intangible for the whole charge); 4 bytes changed, '
          'the rest his vanilla file', (win.get(0x271), win.get(0x289), len(diff) if diff is not None else 'size'),
          ([0, 0], [0, 0], 4))
    m = fresh(mscsb, src)
    g = m.game
    calls = []

    def sysf(sid, a, old=g.sys):
        if sid in (0x2D, 0x36):
            calls.append((sid, tuple(a)))
            return 0
        return old(sid, a)
    g.sys = sysf
    g.held = {1}
    m.vm.g[4] = 0x155
    m('gk_lw_main')
    n = 0
    for t in range(40):
        m.vm.g[18], m.vm.g[19] = 0, 0
        if m('gk_lw_loop'):
            break
        m('gk_lw_tick')
        n += 1
    check('charge invulnerability: the stance (main + %d frames of its loop, held): his body state set normal (HitModule(0, '
          '0)) at its start and every frame, never intangible / invincible, no shield (ShieldModule) on' % n,
          (calls.count((0x2D, (0, 0))), [c for c in calls if c != (0x2D, (0, 0))]), (n + 1 + (1 if n < 40 else 0), []))


def clonefix_v3_tests(mscsb, src):
    """clone fix v3 (the user: "make it so the use of down special just activates the clones. Please disable clone kick for
    the first 10 frames of clones existing. Right now if down special is pressed with max gauge, it activates the kick")"""
    m, g, kick, answers, armed = cf3_run(mscsb, src, held_to=0, n=3)
    check('clone fix v3: the full gauge\'s press activates the ability and is used up there: the input site answers 0 (no '
          'status), the specials\' buffer cleared (Buffer_Clear: 32), the kick locked (slot 60: 0), clones on the way',
          (answers[:1], kick, m.g('gk_ability') > 0, armed[:2], m('gk_vi', 60)), ([(0, 0)], None, True, [0, 0], 0))
    m, g, kick, answers, armed = cf3_run(mscsb, src, held_to=30, n=40, site_at=range(31))
    check('activation with the button held 30 frames (the input site asking on every held frame, as if the held press '
          'counted): no kick; every answer 0; the kick armed only after the release (frame 31)',
          (kick, {r for _t, r in answers}, armed.index(1) if 1 in armed else None), (None, {0}, 31))
    m, g, kick, answers, armed = cf3_run(mscsb, src, held_to=30, presses=(36,), n=40)
    check('... then a fresh press (frame 36): the kick', kick, 36)
    m, g, kick, answers, armed = cf3_run(mscsb, src, presses=(5,), n=30)
    check('a press at frame 5 of the ability (in the lockout): no kick, then or later (his hook drops it: it never reaches '
          'the input site, not buffered past the lockout)', (kick, [t for t, r in answers]), (None, [0]))
    m, g, kick, answers, armed = cf3_run(mscsb, src, presses=(5,), n=30, site_at=range(5, 11))
    check('... nor if it reached the input site on frames 5 - 10 (its answers 0; the kick armed at frame 11\'s update: '
          'the clones\' first 10 frames, the left one made on frame 2)',
          (kick, {r for t, r in answers if t > 0}, armed.index(1)), (None, {0}, 11))
    m, g, kick, answers, armed = cf3_run(mscsb, src, presses=(11,), n=30)
    check('a press at frame 11 (the lockout\'s last frame): no kick', kick, None)
    m, g, kick, answers, armed = cf3_run(mscsb, src, presses=(12,), n=30)
    check('a fresh press at frame 12: the kick (his SpecialLwAttack slot 0x161) that frame', kick, 12)
    m, g, kick, answers, armed = cf3_run(mscsb, src, presses=(20,), n=30)
    check('... and later (frame 20): the kick', kick, 20)
    g.press, g.stick, g.held = {1}, (-0.8, -0.8), {1}
    m, g, kick, answers, armed = cf3_run(mscsb, src, n=3)
    x0 = g.x
    g.press, g.held, g.stick = {1}, {1}, (-0.8, -0.8)
    m.vm.g[4], m.vm.g[24] = 0, 0x8000
    g.status_req = []
    m('gekkouga_frame')
    check('the swaps aren\'t locked: down special + left at frame 4 still swaps (his place to the left clone\'s)',
          (g.status_req, round(g.x - x0, 3) != 0), ([], True))
    # ---- reasons
    m = fresh(mscsb, src)
    g = m.game
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 20)
    frames(m, 1, 0xB1)
    check('clone fix v3 diag: ended by his KO status: VAR_23 500 (300 only for the timer)', g.vars.get(0x0F000317), 500.0)
    m = fresh(mscsb, src)
    g = m.game
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 20)
    g.vars[0x0F00030E] = float((int(g.vars.get(0x0F00030E, 0)) + 1) & 7)
    frames(m, 1)
    check('... ended by a battle reset (the clear-all count): 600', (g.vars.get(0x0F000317), m.g('gk_alive')), (600.0, 0))
    m = fresh(mscsb, src)
    g = m.game
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 840)
    check('... the timer\'s end: 302 as before', (g.vars.get(0x0F000317), m.g('gk_alive')), (302.0, 0))


def clone_free_tests(mscsb, src):
    """aligned kick v1: the clone article in free mode (his flags 128): its own commanded motion (VAR_28 / VAR_29), facing,
    tilt, the startup's pause, restarts by seq; back to his motion after; the effects epoch"""
    m = MSC(mscsb, src)
    g = m.game
    sh = {}
    g.calls2 = []

    def sysf(sid, a, old=g.sys):
        if sid == 0x17 and a[0] == 0 and a[1] in sh:
            return f2i(sh[a[1]])
        if sid == 0x17 and a[0] == 0 and 0x0F000020 <= a[1] < 0x0F000040:
            return f2i({0x0F000024: 0.0, 0x0F000025: 0.0, 0x0F000027: 1.0}.get(a[1], 0.0))
        if sid == 0x12 and a[0] in (0x1, 0x4, 0x2713):
            g.calls2.append(('motion', a[0]) + ((a[1], fv(a[2]), fv(a[3])) if a[0] == 0x1 else (fv(a[1]),)))
            return 0
        if sid == 0x14 and a[0] in (0, 0x4):
            g.calls2.append(('posture', a[0]) + tuple(fv(x) for x in a[1:]))
            if a[0] == 0:
                g.lr = fv(a[1])
            return 0
        if sid == 0x1C and a[0] == 0x2D:
            g.calls2.append(('fade',))
            return 0
        return old(sid, a)
    g.sys = sysf
    base = 0x0F000348                                      # slot 2's shared VAR_24 - 31

    def chan(flags, c1, c2=0):
        sh[base + 7] = 4747000.0 + flags
        sh[base + 4] = float(c1)
        sh[base + 5] = float(c2)
        sh[base + 0], sh[base + 1], sh[base + 2], sh[base + 3] = -14.0, 10.0, 14.0, 10.0
    chan(3 + 4, 0, 1.0)
    g.x, g.y, g.lr = -14.0, 10.0, 1.0
    m('cl_frame')
    check('free: the clone found him (slot 2, the left one)', (m.g('cl_slot'), m.g('cl_id')), (2, 1))
    g.calls2 = []
    cmd = 0x28D + 1024 * 2 + (1 << 21) + (1 << 22)        # the kick, frame 2, tilted, paused, facing right
    chan(3 + 128, cmd)
    m('cl_frame')
    check('free (flags 128): its command: the kick motion 0x28D from frame 2 held (rate 0), tilted back 53 degrees (its '
          'kick along its flight up toward the centre line)',
          [c for c in g.calls2 if c[0] != 'fade'], [('posture', 4, -53.0, 0.0, 0.0), ('motion', 1, 0x28D, 2.0, 0.0)])
    g.calls2 = []
    cmd2 = 0x28D + 1024 * 3 + (1 << 21) + (1 << 22)
    chan(3 + 128, cmd2)
    m('cl_frame')
    check('... paused on the startup\'s next frame: set there (0x2713), held', g.calls2, [('motion', 4, 0.0), ('motion', 0x2713, 3.0)])
    g.calls2 = []
    chan(3 + 128, 0x69 + (1 << 20) + (1 << 23))
    m('cl_frame')
    check('a new command (forward air, facing left, upright, seq 1): turned, upright, its motion from 0 at rate 1, its old '
          'move\'s following effects faded', g.calls2,
          [('posture', 0, -1.0), ('posture', 4, 0.0, 0.0, 0.0), ('fade',), ('motion', 1, 0x69, 0.0, 1.0)])
    g.calls2 = []
    chan(3 + 128, 0x69 + (1 << 20))
    m('cl_frame')
    check('the same kind, its seq flipped (a restart: jab 1 again, an aerial again): from its frame again',
          g.calls2, [('motion', 1, 0x69, 0.0, 1.0)])
    g.calls2 = []
    chan(3 + 128 + 64, 0x69 + (1 << 20))
    m('cl_frame')
    check('he is frozen (flags 64): its rate 0 where it is', g.calls2, [('motion', 4, 0.0)])
    g.calls2 = []
    chan(3 + 256, 0x5F * 1024 + 4, 1.0)
    m('cl_frame')
    check('back in formation (no 128), the effects epoch flipped (256): its effects faded; upright; his motion (the channel\'s '
          'kind x 1024 + frame) from its frame', [c for c in g.calls2 if c[0] in ('fade', 'motion') or c[1] == 4][:4],
          [('fade',), ('posture', 4, 0.0, 0.0, 0.0), ('fade',), ('motion', 1, 0x5F, 4.0, 1.0)])
    # ---- clone fix v3 (the user: "after using the clone kick and landing, clones don't have some of their effects show
    # (ex. smash attack charging/release)"): a split clone's hold draws its own charge effects
    def fx(op=None):
        return [(x[1], x[2], x[3], round(x[4], 3)) for x in g.log if x[0] == 'fxsize'] + \
            [('kill', x[2]) for x in g.log if x[0] == 'effect' and x[1] == 0x2723]
    g.log, g.calls2 = [], []
    chan(3 + 128, 0x62 + 1024 * 30 + (1 << 23))               # forward smash's hold, its charge 30
    m('cl_frame')
    check('clone fix v3: split, a forward smash hold (0x62) with its charge 30: the hold motion from 0 (not from 30), its '
          'old move\'s effects faded; its charge effects as his: dust (0x1000019, root, 1), sparkle at the sword (0x1000010, '
          'its hand 0x7E8, 1), the water sword made again at the charge\'s size (1 + 4 x 30 / 120 = 2)',
          ([c for c in g.calls2 if c[0] in ('fade', 'motion')][-2:], sorted(fx(), key=str)),
          ([('fade',), ('motion', 1, 0x62, 0.0, 1.0)],
           sorted([(0x2710, 0x1000019, 0, 1.0), (0x2712, 0x1000010, 0x7E8, 1.0), (0x2712, 0x3300007, 0x7E8, 2.0),
                   ('kill', 0x3300007)], key=str)))
    seen = []
    for v in (31, 32, 35, 35, 40):
        g.log = []
        chan(3 + 128, 0x62 + 1024 * v + (1 << 23))
        m('cl_frame')
        seen.append((v, sorted(fx(), key=str)))
    check('... its charge growing: every 5 the dust and sparkle, every 10 the sword at the new size (40: 2.333); nothing '
          'while it doesn\'t change (35 twice: frozen) or between',
          seen, [(31, []), (32, []), (35, sorted([(0x2710, 0x1000019, 0, 1.0), (0x2712, 0x1000010, 0x7E8, 1.0)], key=str)),
                 (35, []), (40, sorted([(0x2710, 0x1000019, 0, 1.0), (0x2712, 0x1000010, 0x7E8, 1.0),
                                        (0x2712, 0x3300007, 0x7E8, 2.333), ('kill', 0x3300007)], key=str))])
    for kind, t, spark in ((0x64, 'up', (0x2710, 0x1000010, 0, 1.0)), (0x67, 'down', (0x2710, 0x1000010, 0, 1.0))):
        g.log = []
        chan(3 + 128, kind + 1024 * 120 + (1 << 20))
        m('cl_frame')
        check('... %s smash\'s hold (0x%X), full: the sparkle over it / at its feet (root), the sword at 5' % (t, kind),
              (spark in fx(), (0x2712, 0x3300007, 0x7E8, 5.0) in fx()), (True, True))
    g.log, g.calls2 = [], []
    chan(3 + 128, 0x5F + (1 << 23))
    m('cl_frame')
    check('... any other motion (the release: forward smash 0x5F from 0): no charge effects of its own (its effect script\'s)',
          ([c for c in g.calls2 if c[0] == 'motion'], fx()), ([('motion', 1, 0x5F, 0.0, 1.0)], []))


def kick_data_tests(out, user):
    """aligned kick v1: the clone's counter kick scripts (both motions): his up-diagonal branch's hitboxes (13 %, 60 degrees,
    bone 4 as the article's), frames 5 - 20; its effects his False branches'; his own scripts unchanged"""
    import acmd
    ow = os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon', 'clone')
    cg = acmd.ACMDFile.load(os.path.join(ow, 'game.bin'))
    ce = acmd.ACMDFile.load(os.path.join(ow, 'effect.bin'))
    hg = acmd.ACMDFile.load(os.path.join(user, 'body', 'game.bin'))
    mdl = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone', 'c00')
    bm = GB.bone_map(open(os.path.join(mdl, 'model.jtb'), 'rb').read(), os.path.join(mdl, 'model.vbn'))
    want = [dict(zip(c.info['syntax'], c.params)) for c in GB.kick_branch(hg.scripts[acmd.crc('speciallwattack')], 0x2100001C)]
    for n in GB.KICK_SCRIPTS:
        sc = cg.scripts.get(acmd.crc(n), [])
        hbs = [dict(zip(c.info['syntax'], c.params)) for c in sc if c.name == 'Hitbox']
        frames_ = [float(c.params[0]) for c in sc if c.name == 'FRAME']
        check('aligned kick: the clone\'s %s: his up-diagonal kick (flag 0x2100001C\'s branch: %s %%, %s degrees, sizes %s), '
              'bone 4 as the article\'s (0x%X), on at 5, off at 20' % (n, [w['Damage'] for w in want], [w['Angle'] for w in want],
                                                                        [w['Size'] for w in want], bm(4)),
              ([(h['Damage'], h['Angle'], h['KBG'], h['BKB'], h['Size'], h['X'], h['Bone']) for h in hbs], frames_,
               [c.name for c in sc][-2:]),
              ([(w['Damage'], w['Angle'], w['KBG'], w['BKB'], w['Size'], w['X'], bm(4)) for w in want], [5.0, 20.0],
               ['Remove_All_Hitboxes', 'Script_End']))
        ef = [c.name for c in ce.scripts.get(acmd.crc(n), [])]
        check('aligned kick: its effects: his kick\'s (frame 2 Graphic_Effect2, frame 3 Graphic_Effect4: his flags off)',
              ef, ['FRAME', 'Graphic_Effect2', 'FRAME', 'Graphic_Effect4', 'Script_End'])
    bg = acmd.ACMDFile.load(os.path.join(out, 'fighter', 'gekkouga', 'script', 'animcmd', 'body', 'game.bin'))
    check('aligned kick: his own kick scripts unchanged (the 0x2100001C branch on him: his MSC sets the flag)',
          [acmd.fmt_script(bg.scripts[acmd.crc(n)]) == acmd.fmt_script(hg.scripts[acmd.crc(n)]) for n in GB.KICK_SCRIPTS],
          [True, True])


def clone_articles_tests(mscsb, src, sk_mscsb, sh_mscsb, cl_mscsb):
    """clone articles v1 (README "Clone articles v1"): his skeleton request then the clones' (one a frame, stacked levels),
    their seating (skeleton.mscsb), his shot's shuriken copies (gekkouga.mscsb) and their claim / move (shuriken.mscsb),
    the clones' hitboxes cleared on every new motion (clone.mscsb), the KO's resets (the user)"""
    # ---- his side: the skeleton queue
    m, g = ak_setup(mscsb, src)
    g.log = []
    m('gk_sk_spawn', f2i(36.0), f2i(10.0))
    req = [(g.vars.get(0x0F00030F), g.vars.get(0x0F000311), [x for x in g.log if x[0] == 'article'])]
    for _ in range(2):
        g.vars[0x0F00030F] = 0.0                     # claimed (the executable clears his VAR_15)
        g.log = []
        frames(m, 1)
        req.append((g.vars.get(0x0F00030F), g.vars.get(0x0F000311), [x for x in g.log if x[0] == 'article']))
    g.vars[0x0F00030F] = 0.0
    g.log = []
    frames(m, 1)
    check('clone articles: his side special\'s skeleton (VAR_15 1: level 0, at its place), then each frame after the last '
          'was claimed the clones\' (VAR_15 2 / 3: levels 1 / 2, Y + 24 / + 48), article 8 each; then nothing',
          req + [[x for x in g.log if x[0] == 'article']],
          [(1.0, 10.0, [('article', 0x2710, 8)]), (2.0, 34.0, [('article', 0x2710, 8)]), (3.0, 58.0, [('article', 0x2710, 8)]), []])
    m2, g2 = ak_setup(mscsb, src)
    m2.setg('gk_alive', 2)
    m2('gk_sk_spawn', f2i(36.0), f2i(10.0))
    g2.vars[0x0F00030F] = 0.0
    frames(m2, 1)
    lv1 = g2.vars.get(0x0F00030F)
    g2.vars[0x0F00030F] = 0.0
    g2.log = []
    frames(m2, 1)
    check('... one clone out (the right one): its skeleton level 1, nothing more', (lv1, [x for x in g2.log if x[0] == 'article']),
          (2.0, []))
    m3, g3 = ak_setup(mscsb, src)
    frames(m3, 1)
    m3('gk_sk_spawn', f2i(36.0), f2i(10.0))
    frames(m3, 6)
    check('... not claimed in time (5 frames): the queue dropped', m3('gk_vi', 15), 0)
    # ---- his side: the shuriken copies
    m, g = ak_setup(mscsb, src)
    g.log = []
    m('gk_sh_copies')
    frames(m, 1)
    fl = (int(g.vars.get(0x0F00031F)) - 4747000) // 512 % 4
    frames(m, 3)
    fl2 = (int(g.vars.get(0x0F00031F)) - 4747000) // 512 % 4
    check('clone articles: his shot: one shuriken generated and shot per clone out (article 0: 0x2710 then 0x2719, twice); the '
          'channel\'s flags 512 + 1024 (copies waiting) for 3 frames, then cleared',
          ([x for x in g.log if x[0] == 'article'], fl, fl2),
          ([('article', 0x2710, 0), ('article', 0x2719, 0), ('article', 0x2710, 0), ('article', 0x2719, 0)], 3, 0))
    # ---- the KO (the user: the stored smash charge too)
    m, g = ak_setup(mscsb, src)
    m.setg('gk_smash', 90)
    m.setg('gk_chain_req', 2)
    m('gk_bsi', 1, 10, 60)
    frames(m, 1, 0xB1)
    check('KO: the stored smash charge 0 (the user; until now kept across stocks), a chain asked for 0, the split clones\' '
          'charges 0', (m.g('gk_smash'), m.g('gk_chain_req'), m('gk_bvi', 1, 10)), (0, 0, 0))
    # ---- the skeleton's seat (skeleton.mscsb)
    k = MSC(sk_mscsb, GB.SKELETON_MSC)
    kg = k.game
    kg.floors = [(-1000.0, 1000.0, 10.0)]
    kg.vars.update({0x0F000300: 3.0, 0x0F000301: 36.0, 0x0F000302: 34.0, 0x0F000303: 1.0, 0x0F000314: 1.0})
    places = []
    for t in range(6):
        kg.vars.update({0x0F000311: 1.0, 0x0F000312: 36.0 + 0.58 * t, 0x0F000313: 10.0, 0x0F000315: float(t % 10)})
        k('sk_frame')
        places.append((round(kg.x, 2), round(kg.y, 2)))
    check('the stacked skeleton (level 1): sits on the one below (its x, its y + 24) while it runs',
          places[1:], [(round(36.0 + 0.58 * t, 2), 34.0) for t in range(1, 6)])
    ys = []
    for t in range(6, 40):
        kg.vars.update({0x0F000311: 1.0, 0x0F000315: 5.0})   # its counter stale: past the blast zone
        k('sk_frame')
        ys.append(kg.y)
    check('... the one below stale 2 frames (gone without a word): it falls (his gravity) and lands on the floor, then runs',
          (ys[0], ys[2] < ys[1], ys[-1]), (34.0, True, 10.0))
    # ---- the shuriken copies (shuriken.mscsb)
    def shur(beat, wait):
        sm = MSC(sh_mscsb, GB.SHURIKEN_MSC)
        sg = sm.game
        sh = {0x0F000348 + 7: 4747003.0 + 512 * wait, 0x0F000348 + 6: float(beat), 0x0F000348 + 0: -14.0,
              0x0F000348 + 1: 10.0, 0x0F000348 + 2: 14.0, 0x0F000348 + 3: 12.0}

        def sysf(sid, a, old=sg.sys):
            if sid == 0x17 and a[0] == 0 and a[1] in sh:
                return f2i(sh[a[1]])
            if sid == 0x17 and a[0] == 0 and 0x0F000024 <= a[1] <= 0x0F000027:
                return f2i({0x0F000024: 0.0, 0x0F000025: 10.0}.get(a[1], 0.0))
            if sid == 0x16 and a[0] == 0 and a[2] in sh:
                sh[a[2]] = fv(a[1])
                return 0
            return old(sid, a)
        sg.sys = sysf
        sg.x, sg.y = 3.0, 18.0
        return sm, sg, sh
    sm, sg, sh = shur(3, 3)
    sm.vm.g[4] = 0
    sm('sh_frame')
    sm2, sg2, sh2 = shur(sh[0x0F000348 + 6], 3)
    sm2.vm.g[4] = 0
    sm2('sh_frame')
    sm.vm.g[4] = 2
    sm('sh_frame')
    p1 = (sg.x, sg.y)
    sm('sh_frame')
    check('a copy in its first frame claims the first clone waiting (the left one: claim bit 64 in his VAR_30), the next '
          'copy the other (128); shot (status 2) it moves once by its clone\'s place minus his (-14 - 0, 10 - 10)',
          (sm.g('sh_clone'), sm2.g('sh_clone'), sh2[0x0F000348 + 6], p1, (sg.x, sg.y)), (1, 2, 3.0 + 64 + 128, (-11.0, 18.0), (-11.0, 18.0)))
    sm3, sg3, sh3 = shur(0, 0)
    for _ in range(3):
        sm3('sh_frame')
    sm3.vm.g[4] = 2
    sm3('sh_frame')
    check('his own shuriken (no copy waiting): not a copy, not moved', (sm3.g('sh_clone'), sg3.x, sg3.y), (0, 3.0, 18.0))
    # ---- clone fix v3 (the user: "articles spawned from clones spawn from the main body"): the clone's live place, held
    sm4, sg4, sh4 = shur(0, 1)
    sh4[0x0F000348 + 0], sh4[0x0F000348 + 1] = -37.0, 25.0     # the left clone away from its formation place (-14, 10)
    sg4.x, sg4.y = 8.0, 18.0                                   # the shot at his hand (him at 0, 10)
    sm4.vm.g[4] = 0
    sm4('sh_frame')
    sm4.vm.g[4] = 2
    sm4('sh_frame')
    p0 = (sg4.x, sg4.y)
    check('clone fix v3: a copy for a clone standing away from its formation place (-37, 25): set at the clone\'s live place '
          '+ his hand\'s offset (8, 8): (-29, 33); reported (VAR_30 + 256 x (clone 1, first set, its place - the clone\'s '
          '(8, 8) -> 24 / 24))', (p0, sh4[0x0F000348 + 6]), ((-29.0, 33.0), 64.0 + 256 * (1 + 8 * (24 + 41 * 24))))
    sg4.x += 3.0
    sm4('sh_frame')
    check('... flying on its own path (3 a frame): left alone', (sg4.x, sg4.y), (-26.0, 33.0))
    sg4.x, sg4.y = 14.0, 18.0                                  # the game put it back on his path (his hand + 2 frames)
    sm4('sh_frame')
    check('... the game re-placing it on his path the next frame: put back on the clone\'s (+ the same offset)',
          (sg4.x, sg4.y), (-23.0, 33.0))
    sh4[0x0F000348 + 6] = 64.0                                 # (his MSC took the first report)
    sg4.x += 3.0
    sm4('sh_frame')
    check('... its report (set again: kind 2, its place - the clone\'s (14, 8)) the next frame (one at a time); still on '
          'the clone\'s path', (sh4[0x0F000348 + 6], sg4.x), (64.0 + 256 * (5 + 8 * (27 + 41 * 24)), -20.0))
    for _ in range(10):
        sg4.x, sg4.y = 50.0, 18.0
        sm4('sh_frame')
    check('... only in its first %d frames after the move (then it is the game\'s)' % 8, (sg4.x, sg4.y), (50.0, 18.0))
    m = fresh(mscsb, src)
    g = m.game
    g.vars[0x0F00031E] = 64.0 + 256 * (5 + 8 * (27 + 41 * 24))
    f0 = int(g.vars.get(0x0F000314, 0)) >> 20 & 1
    m.vm.g[4] = 0
    m('gekkouga_frame')
    v = int(g.vars.get(0x0F000317))
    check('his MSC: a copy\'s report -> his VAR_23 (the S4GF line: 701 / 702 first set, 801 / 802 set again, + 1000 x its '
          'place - the clone\'s in 2s: X/2 + 20 + 41 x (Y/2 + 20)), the report taken off VAR_30, the flags\' 1048576 bit flipped '
          '(a line)', (v % 1000, ((v // 1000 % 41 - 20) * 2, (v // 1000 // 41 - 20) * 2), g.vars.get(0x0F00031E),
                       int(g.vars.get(0x0F000314)) >> 20 & 1 != f0), (801, (14, 8), 64.0, True))
    # ---- the clone's hitboxes cleared on a new motion (the user: the kick's hitboxes never cleared)
    c = MSC(cl_mscsb, GB.CLONE_MSC)
    cg = c.game
    atk = []

    def sysc(sid, a, old=cg.sys):
        if sid == 0x2E:
            atk.append(a[0])
        return old(sid, a)
    cg.sys = sysc
    c.setg('cl_motion', 0x28D)
    c('cl_move_end', 0x24)
    c('cl_move_end', 0x24)
    check('the clone: every new motion (the kick -> Fall) and every restart clears its hitboxes first (AttackModule 0x2719: '
          'its kick\'s FRAME 20 is past its 20-frame motion; a landing / cancel / command never reaches a Remove)',
          atk, [0x2719, 0x2719])


GAUGE_SRC = None                          # round gauge v1: the user's ui/info/dmg (--gauge-src=), the art's JPG (--gauge-jpg=)
GAUGE_JPG = None


def gauge_tests(z, v11=False, inst=None):
    """round gauge v1 (README "Round gauge v1"): the package's ui/info/dmg rebuilt from the user's folder and the art,
    the gauge clip in panel sprites 1 - 4 with the names the executable looks for, the texture a new slot after the
    highest (135), every existing texlist entry / reference as it was, no overlap with the trait badge"""
    import flx
    import gekkouga_gauge_art as GA
    import gekkouga_gauge_flx as GF
    import gekkouga_clone_cave as C
    import dmg_trait_badge as TB
    pre = 'INSTALL_TO_data/ui/info/dmg/'
    zr, zn = z.read, set(z.namelist())

    class _Z:                              # round gauge v1.1: the files it doesn't ship from the installed packages
        @staticmethod
        def read(n):
            return zr(n) if n in zn else inst.read(n)
    if inst is not None:
        z = _Z()
    with tempfile.TemporaryDirectory() as td:
        art, out = os.path.join(td, 'art'), os.path.join(td, 'out')
        GA.extract(GAUGE_JPG, art)
        info = GF.build(GAUGE_SRC, art, out, v11=v11)
        same = [n for n in ('dmg.flx', 'texlist.lst', 'img-00135.nut') if z.read(pre + n) != open(os.path.join(out, n), 'rb').read()]
    check('round gauge: the package\'s dmg.flx / texlist.lst / img-00135.nut rebuilt byte for byte from the user\'s folder '
          '(the update\'s) and 41672\'s art (tools/gekkouga_gauge_art.py extract, tools/gekkouga_gauge_flx.py)', same, [])
    t0 = flx.Tlst(open(os.path.join(GAUGE_SRC, 'texlist.lst'), 'rb').read())
    t1 = flx.Tlst(z.read(pre + 'texlist.lst'))
    check('round gauge: the texture a new slot after the highest (135: img-00135.nut), its 16 cells added; the existing %d '
          'entries and %d slots as they were' % (len(t0.entries), len(t0.slots)),
          (info['texture_slot'], len(t1.slots), t1.slots[:len(t0.slots)] == t0.slots,
           [vars(e) for e in t1.entries[:len(t0.entries)]] == [vars(e) for e in t0.entries], len(t1.entries) - len(t0.entries)),
          (135, 136, True, True, 16))
    d = z.read(pre + 'img-00135.nut')
    i = d.find(b'GIDX')
    check('round gauge: img-00135.nut: NTWU, its own GIDX 0x2800FE30 (the trait badge\'s 0x2800FE00 / FE01 kept)',
          (d[:4], d[i + 8:i + 12].hex()), (b'NTWU', '2800fe30'))
    f0 = flx.read(open(os.path.join(GAUGE_SRC, 'dmg.flx'), 'rb').read())
    f1 = flx.read(z.read(pre + 'dmg.flx'))
    names = {}
    for panel in (1, 2, 3, 4):
        k = f1.frame_key(panel, 0)
        names[panel] = [f1.instance_name(f1.places[pi]) for pi in k.places if f1.instance_name(f1.places[pi]) == 'gkgauge_mc']
    g = info['gauge']
    kid = [f1.instance_name(f1.places[pi]) for pi in f1.frame_key(g, 0).places]
    check('round gauge: "gkgauge_mc" in panel sprites 1 - 4; in it the rings and the fill as the executable names them '
          '(GAUGE_NAMES), the fill 11 frames',
          (names, sorted(n for n in kid if n), f1.sprites[info['fill']].nframes),
          ({p_: ['gkgauge_mc'] for p_ in (1, 2, 3, 4)}, sorted(C.GAUGE_NAMES[1:]), GA.FILL_STEPS))
    check('round gauge: every sprite / place / image of the user\'s file kept (the gauge\'s appended)',
          (len(f1.sprites) - len(f0.sprites) > 0, f1.images[:len(f0.images)] == f0.images,
           [vars(x) for x in f1.sprites[5:len(f0.sprites)]] == [vars(x) for x in f0.sprites[5:]]), (True, True, True))
    if v11:
        em = GF.emblem_places(f0)
        got, bad_depth = {}, []
        for panel in (1, 2, 3, 4):
            k = f1.frame_key(panel, 0)
            ps = [f1.places[pi] for pi in k.places]
            gp = next(p_ for p_ in ps if f1.instance_name(p_) == 'gkgauge_mc')
            mk = next(p_ for p_ in ps if f1.instance_name(p_) == 'mark_mc')
            m = f1.transforms[gp.xform].matrix()
            got[panel] = (round(m[4], 3), round(m[5], 3), round(m[0], 4), f1.colors[gp.color].mul[0])
            ds = [p_.depth for p_ in ps]
            if len(set(ds)) != len(ds) or gp.depth != mk.depth + 1 or \
                    min(p_.depth for p_ in ps if p_.depth > mk.depth and p_ is not gp) != gp.depth + 1:
                bad_depth.append(panel)
        check('round gauge v1.1 (the user: "far too small ... about the size of the fighter emblem (pokeball), slightly '
              'smaller"): centred on each panel\'s emblem (mark_mc), its cell 0.87 of the emblem (254 px x its scale); '
              'hidden by default (alpha 0: the user: "appearing on fighters other than Greninja"; the executable shows it '
              'on his panel)', got, {p_: (x, y, s_, 0) for p_, (x, y, s_, _d) in em.items()})
        check('... drawn right above the emblem and under every other part of the panel (the percent, the portrait: their '
              'depths one up), every depth in a panel its own', bad_depth, [])
        return
    over = []
    for panel, (x, y, sc) in GF.PLACES.items():
        bx, by, bs = TB.PLACES[panel]
        r = GF.GAUGE_PX * sc / 2
        if abs(x - bx) < TB.BADGE_W * bs / 2 + r and abs(y - by) < TB.BADGE_H * bs / 2 + r:
            over.append(panel)
    check('round gauge: in Little Mac\'s KO meter band, right of the trait badge, not over it (v7\'s places sat on the CPU '
          'level and the badge)', over, [])


def tilt_chain_tests(mscsb, src):
    """tilt chain v1 (README "Tilt chain v1"): a jab (0x25) or a tilt (0x28 / 0x29 / 0x2A) that hits an opponent
    (AttackModule 0x2727 kind 2; a shield doesn't count; a clone's hit does) can be cancelled from the frame after the hit,
    on the ground, into a tilt not used in this chain (the game's tilt input; a smash input left to the game); the rapid
    jab (0x26) not part of it; anything but a jab / tilt ends it"""
    m = fresh(mscsb, src)
    g = m.game
    body = open(src).read()
    spans = {}
    for fn in ('func_263', 'func_275', 'func_278', 'func_281', 'func_270', 'func_277', 'func_279', 'func_282', 'func_336'):
        a, b, c = GB.func_span(body, fn)
        spans[fn] = body[a:c]
    check('tilt chain: the jab / forward / up / down tilt mains start it (4 / 1 / 2 / 3) before their loops are set',
          [spans[f].count('gk_tc_start(0x%X);' % k) == 1 and spans[f].index('gk_tc_start') < spans[f].index('func_78(')
           for f, k in (('func_263', 4), ('func_275', 1), ('func_278', 2), ('func_281', 3))], [True] * 4)
    check('tilt chain: their loops try it first; the rapid jab (Attack100 0x26, func_336) has none',
          ([spans[f].index('gk_tc_try()') < spans[f].index('CancelModule(0x2713)') for f in ('func_270', 'func_277', 'func_279',
                                                                                              'func_282')],
           'gk_tc' in spans['func_336']), ([True] * 4, False))

    def start(st, k):
        m.vm.g[4] = st
        g.log = []
        m('gk_tc_start', k)

    def tick(hit=0, cmd=0, air=0):
        g.atk_hit = hit
        m.vm.g[18] = air
        m.vm.g[24] = cmd
        g.status_req = []
        return m('gk_tc_try'), list(g.status_req)

    start(0x25, 4)
    check('a jab starts a chain: nothing used (a jab isn\'t a tilt use), kind 4, its hits since it started cleared',
          (m.g('gk_tc_used'), m.g('gk_tc_kind'), m.g('gk_tc_hit'), [x for x in g.log if x[0] == 'atk_clear']),
          (0, 4, 0, [('atk_clear',)]))
    check('a whiff: a tilt input (forward) does nothing, 5 frames', [tick(0, 0x2) for _ in range(5)], [(0, [])] * 5)
    check('shielded (kind 4 only): no window', [tick(4, 0x2) for _ in range(3)], [(0, [])] * 3)
    check('the hit (kind 2) on this frame: no cancel yet (from the next frame)', (tick(2, 0x2), m.g('gk_tc_hit')), ((0, []), 1))
    g.hitlag = 3
    check('... the next frame in hitlag: still none', tick(2, 0x2), (0, []))
    g.hitlag = 0
    check('... a smash input (forward smash 0x10 with the tilt bit): left to the game', tick(2, 0x12), (0, []))
    check('... no tilt input (jab 0x1): none', tick(2, 0x1), (0, []))
    check('... in the air (situation 2): none', tick(2, 0x2, air=2), (0, []))
    check('... a forward tilt: AttackS3 (0x28) as a chain', (tick(2, 0x2), m.g('gk_tc_req')), ((1, [(0x28, 1)]), 1))
    start(0x28, 1)
    check('the forward tilt\'s start: the chain kept (used forward: 2), kind 1, its hit from 0',
          (m.g('gk_tc_used'), m.g('gk_tc_kind'), m.g('gk_tc_hit'), m.g('gk_tc_req')), (2, 1, 0, 0))
    check('... no hit yet: no chain (even with the input)', tick(0, 0x4), (0, []))
    tick(2, 0)
    check('... hit: forward again refused; up + forward bits: up first (as func_43); down accepted',
          (tick(2, 0x2), tick(2, 0x6)), ((0, []), (1, [(0x29, 1)])))
    start(0x29, 2)
    tick(2, 0)
    check('the up tilt hits: forward / up refused, down: AttackLw3 (0x2A)', (tick(2, 0x2), tick(2, 0x4), tick(2, 0x8)),
          ((0, []), (0, []), (1, [(0x2A, 1)])))
    start(0x2A, 3)
    check('forward, up, down: all three in the chain (2 + 4 + 8)', m.g('gk_tc_used'), 14)
    tick(2, 0)
    check('... the down tilt hits: no tilt left', [tick(2, c) for c in (0x2, 0x4, 0x8)], [(0, [])] * 3)
    m.setg('gk_tc_hit', 2)
    m.vm.g[4] = 0x2A
    m.game.vars[0x0F00031E] = 0.0
    m('gekkouga_frame')
    d = int(g.vars.get(0x0F000314, 0.0))
    check('diag (his VAR_20): 2097152 on, the move (3 x 256), hit seen (2048), window open (4096), used 14 x 8192; under '
          '2^24 (VAR_20 is a float: its low flag bits stay exact)',
          (d >> 21 & 1, d >> 8 & 7, d >> 11 & 1, d >> 12 & 1, d >> 13 & 0xFF, d < 1 << 24), (1, 3, 1, 1, 14, True))
    frames(m, 1, st=0x1)
    check('walking (any status but a jab / tilt): the chain ends', (m.g('gk_tc_used'), m.g('gk_tc_kind'), m.g('gk_tc_hit'),
                                                                   m.g('gk_tc_req')), (0, 0, 0, 0))
    start(0x2A, 3)
    check('... the next tilt (down) a new chain: only itself used', m.g('gk_tc_used'), 8)
    for st, what in ((0x1B, 'a jump'), (0x1D, 'a shield'), (0x4A, 'being hit'), (0x153, 'a special'), (0x2B, 'a smash'),
                     (0x34, 'an aerial'), (0x26, 'the rapid jab')):
        start(0x28, 1)
        tick(2, 0)
        m.setg('gk_tc_req', 1)
        frames(m, 1, st=st)
        start(0x29, 2)
        check('%s (0x%X) ends it, even with a chain cancel asked: the next tilt a new chain' % (what, st), m.g('gk_tc_used'), 4)
    m2 = fresh(mscsb, src)
    m2.vm.g[4] = 0x26
    m2.game.atk_hit = 2
    m2.game.status_req = []
    m2.vm.g[24] = 0x2
    check('the rapid jab (0x26): no chain kind set, its try does nothing', (m2('gk_tc_try'), m2.game.status_req), (0, []))
    # a clone's copy of the move landing (the exe's VAR_22) opens the window too
    start(0x28, 1)
    tick(0, 0)
    g.vars[0x0F000316] = 1.0
    m('gk_clone_hitlag')
    check('a clone\'s hit (his VAR_22) during his forward tilt: hit seen, VAR_22 cleared', (m.g('gk_tc_hit'),
          g.vars.get(0x0F000316)), (1, 0.0))
    g.hitlag = 0
    check('... the next frame: a chain (up tilt)', tick(0, 0x4), (1, [(0x29, 1)]))
    m.vm.g[4] = 0x1
    m.setg('gk_tc_hit', 0)
    g.vars[0x0F000316] = 1.0
    m('gk_clone_hitlag')
    check('... a clone\'s hit while he walks: nothing', m.g('gk_tc_hit'), 0)


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
    import acmd as _acmd
    kick = {_acmd.crc(n) for n in GB.KICK_SCRIPTS} if hasattr(GB, 'KICK_SCRIPTS') else set()
    for crc, cmds in ce.scripts.items():
        if crc in kick:                  # aligned kick v1: the counter kick's False branches (clone_kick; aligned_kick_tests)
            continue
        if crc not in pe.scripts:
            bad.append((hex(crc), 'not his'))
            continue
        if req(cmds) != req([c for c in GB.flatten(GB.effect_jump(pe, crc)) if mappable(c)]):
            bad.append(hex(crc))
    check('clone fixes v1: every clone effect script (%d) requests his own effects in his order (the joints remapped; '
          'a request on a joint past his model.jtb tables left out)' %
          len(ce.scripts), bad, [])
    check('clone fixes v1: at least the motions his scripts give effects without loops / calls (%d)' % len(ce.scripts),
          len(ce.scripts) >= 90, True)
    jumps = [crc for crc in ce.scripts if [c.name for c in pe.scripts.get(crc, []) if c.name != 'Script_End'] == ['JUMP']]
    named = sorted(n for n in ('jumpaerialback', 'landingairf', 'landingairb', 'landingairhi', 'landingairlw')
                   if _acmd.crc(n) in jumps)
    check('clone fix v3: his effect scripts that only JUMP to another (his double jumps, his aerials\' landings: their dust; '
          '15) copied from their target: the clones\' (in formation and split) as his', (len(jumps), named),
          (15, ['jumpaerialback', 'landingairb', 'landingairf', 'landingairhi', 'landingairlw']))

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


def skeleton_v16_tests(mscsb, src):
    """skeleton v1.6: the shadow's fixed distance (gk_ss_shadow: his instance float 0x35 to gk_sk_dist() by SpecialS
    frame 20, the skeleton at 21) and no side special while a skeleton of his runs (gk_ss_allowed in func_2379)"""
    D = 36.0
    for start, what in ((9.2, 'a tap (2 + 6 x 1.2)'), (2.0, 'the hold\'s first frame'), (30.8, 'a hold cut short'),
                        (36.0, 'a full hold (the executable\'s cap)')):
        m = fresh(mscsb, src)
        g = m.game
        g.ints.update({0x16000006: 12, 0x16000007: 10, 0x10000085: 0, 0x11000002: 0})
        g.vars.update({0x31: 80.0, 0x32: 12.5, 0x35: start})
        g.situation = 0
        ds, spawn = [], None
        for f in range(1, 22):
            g.log = []
            m('func_2291')
            ds.append(round(g.vars[0x35], 3))
            if g.vars.get(0x0F00030F) and spawn is None:
                spawn = f
        steps = [round(b - a, 3) for a, b in zip([start] + ds, ds)]
        check('skeleton v1.6: %s (0x35 = %.1f): the shadow goes on evenly to %.0f by SpecialS frame 20, stays, never past; '
              'the skeleton at 21 (from the shadow\'s place 0x31 / 0x32)' % (what, start, D),
              (ds[19], ds[20], max(ds) <= D, all(x >= -1e-3 for x in steps), max(steps) - min(steps[:20]) < 1e-2 or start == D,
               spawn), (D, D, True, True, True, 21))
    check('skeleton v1.6: gk_sk_dist() 36 = tools/gekkouga_clone_cave.py SK_DIST (the hold\'s cap in the executable)',
          (round(i2f(fresh(mscsb, src)('gk_sk_dist') & 0xFFFFFFFF), 3), CC.SK_DIST), (36.0, 36.0))

    def press_side(m, st):
        g = m.game
        g.flags.discard(0x2000007C)
        m.vm.g[24] = 0x2000                   # global24: side special pressed
        m.vm.g[4] = st
        m('func_2379')
        m.vm.g[24] = 0
        return 0x2000007C in g.flags
    for sit, st, where in ((0, 0, 'on the ground (Wait)'), (2, 0x1A, 'in the air (Fall)')):
        m = fresh(mscsb, src)
        g = m.game
        g.situation = sit
        g.beat = 0
        frames(m, 2, st)
        free = press_side(m, st)
        g.vars[0x0F00031E] = 4.0              # a skeleton runs: bit 4 in his VAR_30
        m.vm.g[4] = st
        m('gekkouga_frame')
        alive1 = press_side(m, st)
        blocked = []
        for _ in range(100):
            g.vars[0x0F00031E] = 4.0
            m('gekkouga_frame')
            blocked.append(press_side(m, st))
        g.vars[0x0F00031E] = 0.0             # exploded: no heartbeat
        m('gekkouga_frame')
        one = press_side(m, st)
        g.vars[0x0F00031E] = 0.0
        m('gekkouga_frame')
        two = press_side(m, st)
        g.vars[0x0F00031E] = 0.0
        m('gekkouga_frame')
        three = press_side(m, st)
        check('skeleton v1.6 %s: side special starts (0x2000007C) with no skeleton; blocked from its first heartbeat '
              'and while it runs (100 frames); free again 2 frames after its last (gk_sk_beat_miss)' % where,
              (free, alive1, any(blocked), one, two, three), (True, False, False, False, True, True))
    # the request in flight (made, not yet claimed): blocked too; other specials untouched
    m = fresh(mscsb, src)
    g = m.game
    g.beat = 0
    m.setg('gk_sk_req_t', 3)
    check('skeleton v1.6: a skeleton asked for and not claimed yet (gk_sk_req_t): side special blocked',
          press_side(m, 0), False)
    m = fresh(mscsb, src)
    g = m.game
    g.vars[0x0F00031E] = 4.0
    m('gekkouga_frame')
    m.vm.g[24] = 0x4000                       # up special pressed while a skeleton runs
    g.flags.discard(0x2000007C)
    m('func_2379')
    m.vm.g[24] = 0
    body = open(src).read()
    a, b, c = GB.func_span(body, 'func_2379')
    check('skeleton v1.6: up special pressed while a skeleton runs: no side special hold; func_2379\'s only change is its '
          'side special condition (the other specials\' lines as before)',
          (0x2000007C in g.flags, body[a:c].count('gk_'), 'global24 & 0x2000 && gk_ss_allowed()' in body[a:c]), (False, 1, True))


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
    spd = fv(m('sk_speed'))
    check('skeleton v1.7: its speed 0.58 a frame (the user: "slightly slower"; v1 - v1.6 0.7)', spd, 0.58)
    check('skeleton run: 2 steps %g left (%g, 10)' % (spd, 40 - 2 * spd), (g.x, g.y), (round(40 - 2 * spd, 3), 10.0))
    run(m, 8)
    check('skeleton run: 10 frames: %g units (%g, 10), straight on' % (10 * spd, 40 - 10 * spd), (round(g.x, 2), g.y),
          (round(40 - 10 * spd, 2), 10.0))
    m, g = make(walls=[(30.0, 0.0, 50.0)])
    claim(g)
    run(m, 30)
    wall_x = next(round(40 - spd * k, 1) for k in range(100) if 40 - spd * k < 30 + 2 + spd)
    check('skeleton run: a wall (x 30) stops it short (its test reaches 2 past its step), it stays there running',
          (round(g.x, 1), g.y), (wall_x, 10.0))
    # off a ledge: running right from 95 on a floor that ends at 100, a lower floor at -20 from 100 on
    m, g = make(floors=[(-1000.0, 100.0, 10.0), (100.0, 1000.0, -20.0)])
    claim(g, 95.0, 10.0, 1.0)
    run(m, 9)
    check('skeleton v1.2: way +1: the body as shot (PtcGekkougaSkeletonR 0x3300016), once',
          [x[:3] for x in g.log if x[0] == 'effect' and x[1] == 0x2717], [('effect', 0x2717, 0x3300016)])
    check('skeleton ledge: it doesn\'t stop at the ledge (x 95 -> %g in 9 frames), off it it falls' % round(95 + 9 * spd, 1),
          (round(g.x, 1), g.y < 10.0), (round(95 + 9 * spd, 1), True))
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
    beats = []
    for _ in range(179):
        g.vars[0x0F000356] = 1.0                      # his slot 3's VAR_30: a clone's bit; he clears it every frame
        run(m, 1)
        beats.append(g.vars.get(0x0F000356))
    check('skeleton v1.6: running, its heartbeat: bit 4 added to its owner\'s (slot 3) VAR_30 (SLOTn_SHARED_6) every frame, '
          'the clones\' bits kept', set(beats), {5.0})
    check('skeleton: 179 frames: still running (phase 1, no explosion)', (g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'motion'][-1]),
          (1.0, ('motion', 0, 0.0, 1.0)))
    g.log = []
    run(m, 1)
    check('skeleton explosion at 180: phase 2 (VAR_5: its collision removed, its hits burn), its body ended (both facings\' '
          'sets, 0x2723), v1.2: the explosion flipbook (0x3300019) at its feet (x, y: its base on the ground)',
          (g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'motion'], [x[:3] for x in g.log if x[0] == 'effect' and x[1] == 0x2723],
           [x[:5] for x in g.log if x[0] == 'effect' and x[1] != 0x2723]),
          (2.0, [], [('effect', 0x2723, 0x3300016), ('effect', 0x2723, 0x3300017)],
           [('effect', 3, 0x3300019, round(40.0 - spd * 179, 3), 10.0)]))
    g.log = []
    run(m, 1)
    check('skeleton explosion: the next frame (its scale back to 1) the explode motion (1: its hitbox), its body hidden',
          ([x for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'visible']), ([('motion', 1, 0.0, 1.0)], [('visible', 0)]))
    atk = []

    def sys_atk(sid, a, old=g.sys):
        if sid == 0x2E:
            atk.append((g.t_boom, a[0]))
        return old(sid, a)
    g.sys = sys_atk
    g.t_boom = 2
    g.log = []
    run(m, 1)
    rate = [x for x in g.log if x[0] == 'rate']
    g.vars[0x0F000356] = 0.0
    for t in range(3, m('sk_boom_frames') - 1):
        g.t_boom = t
        run(m, 1)
    check('skeleton v1.7: the explode motion held the frame after (rate 0: its 30 / 48 frames would loop it, its script '
          'again); its hitbox off (AttackModule 0x2719, its records kept) %d frames after it was set, nothing else' %
          m('sk_boom_hit_frames'), (rate, atk, m('sk_boom_hit_frames') == GB.SK_BOOM_FRAMES),
          ([('rate', 0.0)], [(1 + m('sk_boom_hit_frames'), 0x2719)], True))
    check('skeleton v1.6: exploded (phase 2): no heartbeat (his side special is free again; not at its removal, '
          'sk_boom_frames later)', g.vars.get(0x0F000356), 0.0)
    x0 = g.x
    run(m, 1)
    check('skeleton explosion: it stays put; removed %d frames after (BattleObject 9; v1.5: 40 -> 120, its sound\'s '
          'length)' % m('sk_boom_frames'),
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
    run(m, m('sk_smoke_frames') - 1)
    check('skeleton smoke: removed %d frames after (v1.5: 3 -> 36, its death sound\'s length)' % m('sk_smoke_frames'),
          [x for x in g.log if x[0] == 'remove'], [])
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


def skeleton_sound_tests(mscsb, src, out=None):
    """skeleton v1.5's sounds (its MSC): a random one of the two spawn sounds at its start; while it runs its voices, one
    of two at random, the first 10 - 40 frames in, each next from 30 before the last one's end to 60 after; at its end
    (explosion / 0 HP) its voices stopped, then the explosion's / death's sound; the ids its bank / table give them"""
    import gekkouga_sound as GS
    picks = []

    def make(seq):
        m = MSC(mscsb, src)
        g = m.game
        it = iter(seq)

        def sysf(sid, a, old=g.sys):
            if sid == 0x9:                         # randi(lo, hi): the scripted picks (lo + n, under hi)
                v = next(it, 0)
                picks.append((a[0], a[1], v))
                return a[0] + min(v, a[1] - a[0] - 1)
            if sid == 0x1E:
                g.log.append(('snd', a[0], a[1]))
                return 0
            if sid == 0x21 and a[0] == 0x9:
                g.log.append(('remove',))
                return 0
            return old(sid, a)
        g.sys = sysf
        g.vars.update({0x0F000300: 3.0, 0x0F000301: 40.0, 0x0F000302: 10.0, 0x0F000303: 1.0})
        return m, g
    ids = {n: m_ for n, m_ in (('spawn1', 'sk_snd_spawn1'), ('spawn2', 'sk_snd_spawn2'), ('voice1', 'sk_snd_voice1'),
                                ('voice2', 'sk_snd_voice2'), ('death', 'sk_snd_death'), ('boom', 'sk_snd_boom'))}
    m, g = make([1, 5, 0, 0, 1, 90])               # spawn: the 2nd; first voice in 10 + 5; voice1, gap -30 + 0; voice2 ...
    sid = {k: m(v) & 0xFFFFFFFF for k, v in ids.items()}
    if out:
        exp = {k: (0x0768 << 16) | (91 + i) for i, k in enumerate(('spawn1', 'spawn2', 'voice1', 'voice2', 'death', 'boom'))}
        check('skeleton v1.5 sounds: the MSC\'s ids are the bank / table\'s (row 0x768, labels 91 - 96: '
              'tools/gekkouga_sound.py SOUNDS in order)', sid, exp)
    plays = []
    for t in range(160):
        g.log = []
        m('sk_frame')
        plays += [(t, x[2]) for x in g.log if x[0] == 'snd' and x[1] == 0x2710]
    inv = {v: k for k, v in sid.items()}
    seq = [(t, inv.get(i & 0xFFFFFFFF)) for t, i in plays]
    l1, l2 = m('sk_vc_len1'), m('sk_vc_len2')
    check('skeleton v1.5 sounds: its start plays the picked spawn sound (randi 0 / 2 -> the 2nd); its first voice the '
          '15th frame (10 + 5, its start frame the 1st), voice1, the next %d after (its %d frames - 30), voice2' % (l1 - 30, l1),
          seq[:3], [(0, 'spawn2'), (14, 'voice1'), (14 + l1 - 30, 'voice2')])
    check('skeleton v1.7 sounds: every play noted for the TEST_ONLY exe\'s S4SN (VAR_13 the count, VAR_14 the last label, '
          'VAR_15 the answer)', [g.vars.get(0x0F00030D), g.vars.get(0x0F00030E), g.vars.get(0x0F00030F)],
          [float(len(plays)), float(plays[-1][1] & 0xFFFF), 0.0])
    m2, g2 = make([0, 30, 1, 90] + [0, 0] * 20)
    sid2 = {k: m2(v) & 0xFFFFFFFF for k, v in ids.items()}
    inv2 = {v: k for k, v in sid2.items()}
    plays, stops = [], []
    for t in range(180):
        g2.log = []
        m2('sk_frame')
        plays += [(t, inv2.get(x[2] & 0xFFFFFFFF)) for x in g2.log if x[0] == 'snd' and x[1] == 0x2710]
        stops += [(t, inv2.get(x[2] & 0xFFFFFFFF)) for x in g2.log if x[0] == 'snd' and x[1] == 0x2714]
    vt = [t for t, k in plays if k in ('voice1', 'voice2')]
    check('skeleton v1.5 sounds: the 1st spawn sound on a 0 pick; the first voice the 40th frame (10 + 30); then voice2 (a 1 pick) '
          'and the next %d + 60 after it (the latest a gap allows); explosion at 180: the voices stopped then the '
          'explosion\'s sound' % l2,
          (plays[0], vt[:2], vt[1] - vt[0] if len(vt) > 1 else None, stops, plays[-1]),
          ((0, 'spawn1'), [39, 39 + l2 + 60] if 39 + l2 + 60 < 180 else [39], (l2 + 60) if 39 + l2 + 60 < 180 else None,
           [(179, 'voice1'), (179, 'voice2')], (179, 'boom')))
    # 0 HP: the voices stopped, the death sound; nothing after it
    m3, g3 = make([0, 0] + [0] * 40)
    sid3 = {k: m3(v) & 0xFFFFFFFF for k, v in ids.items()}
    inv3 = {v: k for k, v in sid3.items()}
    for _ in range(20):
        m3('sk_frame')
    g3.vars[0x0F000304] = 30.0                    # its VAR_4: 30 damage (25 HP)
    g3.log = []
    m3('sk_frame')
    end = [(x[1], inv3.get(x[2] & 0xFFFFFFFF)) for x in g3.log if x[0] == 'snd']
    g3.log = []
    for _ in range(m3('sk_smoke_frames') + 5):
        m3('sk_frame')
    check('skeleton v1.5 sounds: at 0 HP its voices stopped (0x2714 both), the death sound; no voice after it; removed %d '
          'frames later (its sound played out)' % m3('sk_smoke_frames'),
          (end, [x for x in g3.log if x[0] == 'snd'], [x for x in g3.log if x[0] == 'remove'][:1]),
          ([(0x2714, 'voice1'), (0x2714, 'voice2'), (0x2710, 'death')], [], [('remove',)]))
    gaps = (m('sk_vc_gap'), m('sk_vc_gap') + m('sk_vc_gap_rand') - 1, m('sk_vc_first'), m('sk_vc_first') + m('sk_vc_first_rand') - 1)
    check('skeleton v1.5 sounds: the gap to the next voice -30 ... +60 frames after the last one\'s end (overlap at most 0.5 s), '
          'the first voice 10 - 40 frames in', gaps, (-30, 60, 10, 40))

FX_PKG = None                             # skeleton v1.7: the flipbooks' folder (--fx=...), for the explosion's orange
ICE_CLIP = None                           # usmash spike v2 / trail dim v1: the ice detonation's clip (--ice-clip=), for the cut


def boom_orange(folder):
    """skeleton v1.7: explosion_simple_24's orange pixels a cell (R > 0.45, saturation > 0.35, R > B + 0.25, alpha > 0.3)"""
    import json as _json
    import numpy as np
    from PIL import Image
    d = _json.load(open(os.path.join(folder, 'explosion_simple_24.json')))
    im = np.asarray(Image.open(os.path.join(folder, 'explosion_simple_24_atlas.png')).convert('RGBA')).astype(float) / 255
    nx = d['columns']
    cw, ch = d['cell_size']
    out = []
    for i in range(d['frames']):
        c, r = i % nx, i // nx
        cell = im[int(round(r * ch)):int(round(r * ch + ch)), int(round(c * cw)):int(round(c * cw + cw))]
        R, G, B, A = (cell[..., k] for k in range(4))
        mx, mn = np.maximum(np.maximum(R, G), B), np.minimum(np.minimum(R, G), B)
        sat = (mx - mn) / (mx + 1e-6)
        out.append(int(((A > 0.3) & (R > 0.45) & (sat > 0.35) & (R > B + 0.25)).sum()))
    return out


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
    ex = game.script('SkeletonExplode')
    check('skeleton explosion: one hitbox, 15 %, 50 degrees, KBG 50 / BKB 40, size 27 at its middle (bone 0, Y 14; v1 - v1.4: '
          '22), flame, launched from its middle (FacingRestrict 5), one hit an opponent (Rehit 0); v1.5: shield damage +40 '
          '(55 against a fresh shield\'s 50: it breaks); skeleton v1.7: set at the explode motion\'s frame 0, no WAIT / '
          'Remove (its MSC holds the motion and ends the hitbox: v1 - v1.6 WAIT 4)',
          (len(boom), [round(hb.get(k, -1), 3) for k in ('Damage', 'Angle', 'KBG', 'BKB', 'Size', 'Y', 'Effect', 'FacingRestrict', 'Bone',
                                                          'ShieldDamage', 'Rehit')],
           [c.name for c in ex[1:]]),
          (1, [15.0, 50, 50, 40, 27.0, 14.0, 5, 5, 0, 40, 0], ['Script_End']))
    if FX_PKG:
        import json as _json
        k = _json.load(open(os.path.join(FX_PKG, 'explosion_simple_24', 'explosion_simple_24.json')))['frames_per_cell_at_60fps']
        oc = boom_orange(os.path.join(FX_PKG, 'explosion_simple_24'))
        peak = max(oc)
        last2 = max(i for i, v in enumerate(oc) if v >= 0.02 * peak)
        gone = min(i for i, v in enumerate(oc) if i > oc.index(peak) and v == 0)
        end = 1 + GB.SK_BOOM_FRAMES            # the effect's frame (the hitbox starts a frame after it)
        check('skeleton v1.7: the explosion\'s hitbox ends (effect frame %d) inside the last cell with orange >= 2 %% of its '
              'peak (cell %d: frames %d - %d), before it is all gone (cell %d, frame %d)' % (
                  end, last2, last2 * k, last2 * k + k - 1, gone, gone * k),
              (last2 * k <= end < (last2 + 1) * k, end < gone * k), (True, True))
    p = 145.0
    kb = ((p / 10 + p * 15 / 20) * 200 / 200 * 1.4 + 18) * 0.5 + 40
    check('skeleton explosion: Smash 4\'s knockback on Mario (weight 100) at 130 %% (+ 15): %.1f (a mid-stage KO ~130-140)' % kb,
          130 <= kb <= 140, True)
    check('skeleton v1.5: the explosion\'s hitstun x %g (Extra_Special_Hitbox HitstunMul; the other extras 0: unchanged)' %
          GB.SK_BOOM_HITSTUN, (boom[0].name if boom else None, round(hb.get('HitstunMul', 0), 4),
                               [hb.get(k) for k in ('HitstopMul', 'HitstopFrames', 'SelfHitstopMul', 'SelfHitstopFrames', 'DIMul')]),
          ('Extra_Special_Hitbox', round(GB.SK_BOOM_HITSTUN, 4), [0.0, 0, 0.0, 0, 0.0]))
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
    check('skeleton v1.7 contact: SkeletonRun puts its body capsule (joint 0, radius 3.5, Y 3.5 - 20.5: x +- 3.5, y 0 - 24) '
          'on once (each loop of its motion), rehit rate 3 (a touch every 3 frames; v1.5 / v1.6: on 2 / off 1); no '
          'knockback (KBG / FKB / BKB 0), no hitlag, no flinch, 0.1 %, fire',
          ([c.name for c in run], [t.get(k) for k in ('Bone', 'Size', 'Y', 'Y2', 'KBG', 'FKB', 'BKB', 'DisableHitlag', 'Flinchless',
                                                      'Effect', 'Rehit')], round(t.get('Damage', 0), 3)),
          (['Extended_Special_Hitbox', 'Script_End'], [0, 3.5, 3.5, 20.5, 0, 0, 0, 1, 1, 5, 3], 0.1))
    tog = os.path.join(out, 'TEST_ONLY_DATA', 'skeleton_toggle', 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon',
                       'skeleton', 'game.bin')
    if os.path.exists(tog):
        tg = acmd.ACMDFile.load(tog)
        fr, on = 0.0, []
        for c in tg.script('SkeletonRun'):
            if c.name == 'FRAME':
                fr = float(c.params[0])
            elif c.name == 'Extended_Special_Hitbox':
                on.append(fr)
            elif c.name == 'Remove_All_Hitboxes':
                on.append(-fr)
        starts = [x for x in on if x >= 0]
        check('skeleton v1.7 TEST_ONLY_DATA skeleton_toggle: v1.6\'s contact (on at 0, 3 ... 45, off 2 frames later), '
              'v1.7\'s explosion', (starts[:3], len(starts), all(-on[2 * k + 1] == starts[k] + 2 for k in range(len(starts))),
                                    acmd.fmt_script(tg.script('SkeletonExplode')) == acmd.fmt_script(ex)),
              ([0.0, 3.0, 6.0], 16, True, True))
    check('skeleton scripts: smoke without a hitbox; effect / sound empty', [c.name for c in game.script('SkeletonSmoke')],
          ['Script_End'])
    lv = lvd.LVD(os.path.join(fg, 'model', 'skeleton', 'c00', 'skeleton.lvd'))
    c = lv.collisions[0]
    check('skeleton.lvd: one collision, the 4 vertices the executable moves (v1.5: x +- 3.5, y 2 / 24: its body), a wall each side and a '
          'floor on top (normals out), the hydrant\'s flags',
          (len(lv.collisions), [tuple(round(x, 2) for x in v) for v in c.verts], [tuple(n) for n in c.normals], c.flags),
          (1, [tuple(v) for v in C.sk_verts(C.RELEASE)], [(-1.0, 0.0), (0.0, 1.0), (1.0, 0.0), (0.0, -1.0)][:len(c.verts) - 1],
           [0, 1, 0, 0]))
    check('tuning v1 (the user: "make it so skeletons have solid collision from the bottom"): the box closed: 5 vertices, '
          'the last line its bottom (3.5 -> -3.5 at y 2: a ceiling, normal down: solid from below); not drop-through (flag 4 '
          '0: the top a solid floor); the executable moves all 5 (sk_verts with skbot)',
          ([tuple(v) for v in c.verts[3:]], tuple(c.normals[-1]), c.flags[3], len(C.sk_verts(C.RELEASE))),
          ([(3.5, 2.0), (-3.5, 2.0)], (0.0, -1.0), 0, 5))
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
    g.vars.update({0x0F000300: 3.0, 0x0F000301: 1.0, 0x0F000302: 40.0, 0x0F000303: 10.0, 0x0F000304: -1.0, 0x0F000305: 1.0})
    run(m, 1)
    check('trail start (forward smash at (40, 10), way -1): facing -1 (its model turned: PostureModule 0, 2), there, its '
          'effects unhooked from its hidden model (0x26 (0), 0x1C (1)), motion 0 held (rate 0: its hitboxes), the first flame '
          '8 ahead (fire trail fix v1: on joint 0\'s local Z, forward in its turned frame: X 0, Y 0, Z 8; tuning v1: 8, '
          'size 0.85)',
          ([x for x in g.log if x[0] in ('lr', 'motion')], g.posture_sets[:1], [x for x in g.log if x[0] == 'fx'],
           [x for x in g.log if x[0] == 'visible' and x[1] != 0]),
          ([('lr', -1.0), ('motion', 0, 0.0, 0.0)], [(40.0, 10.0)],
           [('fx', 0x26, 0), ('fx', 0x1C, 1), ('fx', 0x2717, 0x330001C, 0, 0.0, 0.0, 8.0)], []))
    g.log = []
    run(m, 5)
    check('trail: a flame a frame along its way (local Z 23.4 ... 85, X / Y 0: on the ground ahead; trail lite v1: 15.4 '
          'apart, 6 in all)',
          [tuple(round(v, 2) for v in x[4:7]) for x in g.log if x[0] == 'fx'],
          [(0.0, 0.0, round(8.0 + 15.4 * k, 2)) for k in range(1, 6)])
    g.log = []
    run(m, 158)
    check('trail: frames 7 - 164: no more flames (trail lite v1: all 6 made by frame 6), then nothing; it stays put',
          ([x[6] for x in g.log if x[0] == 'fx'], [x for x in g.log if x[0] == 'remove'], g.posture_sets[-1]),
          ([], [], (40.0, 10.0)))
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
            (1, [round(8.0 + 15.4 * k, 2) for k in range(6)]),       # (trail lite v1: half of tuning v1's, same lengths)
            (2, [(4.0 + 18.0 * (k // 2)) * (1 - 2 * (k % 2)) for k in range(4)]),
            (3, [round((6.0 + 49.0 / 3.0 * (k // 2)) * (1 - 2 * (k % 2)), 2) for k in range(8)])) for w in (1.0, -1.0)]:
        m, g = make()
        g.vars.update({0x0F000300: 3.0, 0x0F000301: float(typ), 0x0F000302: 0.0, 0x0F000303: 0.0, 0x0F000304: way, 0x0F000305: 1.0})
        run(m, 20)
        check('fire trail fix v1: %s smash facing %s: motion %d, its flames on the ground (Y 0) along its way (local Z: '
              'X 0, never into the screen) %s; its model turned by its way (the same Z either way)' % (
                  ('forward', 'up', 'down')[typ - 1], 'right' if way > 0 else 'left', typ - 1,
                  'ahead' if typ == 1 else 'each side alternately (up smash: under its geyser, 6 / 14: an interpretation)'),
              ([x[1] for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'lr'][:1],
               [tuple(round(v, 2) for v in x[4:7]) for x in g.log if x[0] == 'fx' and x[1] == 0x2717]),
              ([typ - 1], [('lr', way)], [(0.0, 0.0, z) for z in want]))


def trail_data_tests(out):
    """burn v2: the fire trail's built files"""
    fg = os.path.join(out, 'fighter', 'gekkouga')
    ow = os.path.join(fg, 'script', 'animcmd', 'weapon', 'firetrail')
    mt = open(os.path.join(ow, 'motion.mtable'), 'rb').read()
    check('trail scripts: motion.mtable = FireTrailS4 / FireTrailHi4 / FireTrailLw4 (its motion kinds 0 / 1 / 2; ice '
          'detonation v1: + FireTrailIceBoom, 3)',
          list(struct.unpack('>%dI' % (len(mt) // 4), mt)), [acmd.crc(n) for n in GB.TR_SCRIPTS])
    game = acmd.ACMDFile.load(os.path.join(ow, 'game.bin'))
    rows = []
    for n in GB.TR_SCRIPTS[:3]:
        sc = game.script(n)
        hb = [dict(zip(c.info['syntax'], c.params)) for c in sc if c.name == 'Special_Hitbox']
        rows.append((n, [(h['ID'], h['Bone'], round(h['Z'], 2), round(h['Y'], 2), round(h['Size'], 2)) for h in hb],
                     sorted({(round(h['Damage'], 2), h['KBG'], h['FKB'], h['BKB'], h['Rehit'], h['DisableHitlag'], h['NoGFX'],
                              h['Flinchless'], round(h['Hitlag'], 2), h['Ground/Air'], h['Shieldable']) for h in hb}),
                     [c.name for c in sc][-1]))
    check('trail hitboxes (bone 0, from frame 0, never removed): along each smash\'s path, 0.1 %, no knockback (KBG / FKB / '
          'BKB 0), re-hit every 35 frames, no hitlag, no hit effect, no flinch, ground and air, shieldable', rows,
          [(n, [(i, 0, z, y, sz) for i, (z, y, sz) in enumerate(GB.TR_BOXES[n])],
            [(0.1, 0, 0, 0, 35, 1, 1, 1, 0.0, 3, 1)], 'Script_End') for n in GB.TR_SCRIPTS[:3]])
    check('ice detonation v1: FireTrailIceBoom\'s game script empty (the blast\'s hitbox is its MSC\'s: ib_start)',
          [c.name for c in game.script('FireTrailIceBoom')], ['Script_End'])
    check('trail scripts: effect / sound empty (its MSC makes the fire)',
          [[c.name for c in acmd.ACMDFile.load(os.path.join(ow, f)).script(n)] for f in ('effect.bin', 'sound.bin')
           for n in GB.TR_SCRIPTS], [['Script_End']] * (2 * len(GB.TR_SCRIPTS)))
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
              ([(GB.FIRE_RING, GB.FIRE_RING_L, 0, 8.5, 0.0, round(1.45 * getattr(GB, 'NAIR_SCALE', 1.0), 2))],
               ['EFFECT_FOLLOW_FLIP']))       # (tuning v1: x1.25)
        check('burn v2: a flame (0x%X) at each water sword\'s tip (its hand joint, Y -11 x its size: -55 in the smashes), '
              'ended with the sword' % GB.FIRE_TIP, tips,
              [('AttackS4', [(25, -55.0 - getattr(GB, 'FSMASH_EXTRA', 0.0), 0.0, 2.0)], 1), ('AttackHi4', [(25, -55.0, 0.0, 2.0), (24, -55.0, 0.0, 2.0)], 1),
               ('AttackLw4', [(25, -55.0, 0.0, 2.0), (24, -55.0, 0.0, 2.0)], 1), ('AttackAirF', [], 0),
               ('AttackAirN', [], 0)])
        blade = [(int(c.params[1]), round(float(c.params[2]), 2), round(float(c.params[3]), 2), round(float(c.params[8]), 2))
                 for c in pe.script('AttackAirF') if c.name == 'External_Graphic' and int(c.params[0]) == GB.FIRE_BLADE]
        check('skeleton v1.3 package: forward air\'s flames along its water sword (0x%X, burn v2\'s tip flame gone): at the '
              'sword\'s joint (25) and size (1), made and ended with it' % GB.FIRE_BLADE,
              (blade, [c.name for c in pe.script('AttackAirF') if c.params and isinstance(c.params[0], int) and
                       int(c.params[0]) in (GB.FIRE_BLADE, GB.SWORD)]),
              ([(25, 0.0, 0.0, 1.0)] + ([(25, 0.0, -GB.FAIR_EXTRA, 1.0)] if hasattr(GB, 'FAIR_EXTRA') else []),
               ['External_Graphic'] * (4 if hasattr(GB, 'FAIR_EXTRA') else 2) + ['Terminate_Graphic_Effect'] * 2))
        # (nair / fair v1: a second blade's flames and sword from FAIR_EXTRA along it)
        check('burn v2: ... and his effect scripts otherwise unchanged (the flames taken out again: the True blocks\' '
              'offsets back)', GB.strip_fire_tips(pe), 12 if hasattr(GB, 'FAIR_EXTRA') else 11)
    smash = {zlib.crc32(n.encode()) for n in GB.SMASH_SCRIPTS}
    hold = {zlib.crc32(n.encode()) for n in GB.HOLD_SCRIPTS}
    bad, n, got = [], 0, {}
    if hasattr(GB, 'usmash_spike'):               # smash tune v1: up smash's inner hits renumbered / a spike (its own
        ug = acmd.ACMDFile({k: [acmd.Command(c.ident, list(c.params)) for c in sc] for k, sc in ug.scripts.items()})
        GB.usmash_spike(ug)                       # checks: smash_tune_tests): his script with it, the rest as before
    for f0, f1, kind in ((ug, pg, 'game'), (ue, pe, 'effect')):
        check('%s.bin: the same scripts' % kind, sorted(f0.scripts), sorted(f1.scripts))
        tuned = {zlib.crc32(x.encode()) for x in ('attacks3', 'attackairn', 'attacks4') + (
            ('attackairf',) if hasattr(GB, 'fair_reach') else ())} if hasattr(GB, 'tune') else set()   # (nair / fair v1's
        # forward air: nair_fair_tests)
        for crc in f0.scripts:
            if crc in tuned:
                continue                  # (tuning v1: tuning_tests)
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
                    elif crc in smash and kind == 'effect' and nm == 'Size' and \
                            int(c0.params[0]) == getattr(GB, 'SMASH_STAR', -1):
                        k = 1.0               # (tuning v1: the charge-start star at its size)
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
    kick = {acmd.crc(n) for n in getattr(GB, 'KICK_SCRIPTS', ())}
    grab = {acmd.crc(n) for n in GB.GRAB_SCRIPTS + GB.THROW_SCRIPTS + ('catchwait', 'catchattack')} \
        if hasattr(GB, 'GRAB_SCRIPTS') else set()
    for crc, s in cg.scripts.items():
        if crc in kick or crc in grab:
            continue                      # aligned kick v1: one branch of his kick (kick_data_tests); clone moves v1: the
        o = pg.scripts[crc]               # grabs (clone_moves_tests)
        hb0 = [c for c in o if c.name in GB.HITBOXES]
        hb1 = [c for c in s if c.name in GB.HITBOXES]
        same = len(hb0) == len(hb1)
        for c0, c1 in zip(hb0, hb1):
            for nm in c0.info['syntax']:
                i = c0.info['syntax'].index(nm)
                if nm == 'Bone':
                    same &= (c1.params[i] == 0) == (c0.params[i] == 0) and (c1.params[i] == 0 or c1.params[i] >= 0x7D0)
                elif nm == 'Damage':
                    same &= abs(float(c1.params[i]) - float(c0.params[i]) * (GB.CHARGE_DAMAGE if crc in smash else 1.0)) < 1e-3
                else:
                    same &= c0.params[i] == c1.params[i]
        bad_cmds = [c.name for c in s if c.name not in GB.CLONE_GAME | GB.FLOW | GB.FLOW_KEEP_SAFE]
        ok.append(same and not bad_cmds)
    check('the clone\'s game scripts (%d): his hitboxes (bones the article\'s joints, his smashes\' damage x%.1f: smash '
          'tune v1 1.0, the uncharged damage, as his; x1.4 before), only hitbox / timing commands' % (
              len(cg.scripts), GB.CHARGE_DAMAGE), all(ok) and len(cg.scripts) >= 35 and GB.CHARGE_DAMAGE == 1.0, True)
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
    lh = 23 if GB.CLONE_JOINT_FIX.get(25) == 'LHaveN' else 24
    check('v4: ... its trails 5x long (Y2 -55) on its sword joints (0x7D0 + 24: his joint 24 RHaveN; clone fixes v2: his '
          'joint 25, ThrowN by model.jtb, on the clone\'s %s, 0x7D0 + %d; v1.5: the right hand, confirmed in game)' % (
              GB.CLONE_JOINT_FIX.get(25), lh),
          sorted({(int(c.params[c.info['syntax'].index('Bone2')]), round(float(c.params[c.info['syntax'].index('Y2')]), 2))
                  for c in sw}), sorted({(0x7D0 + lh, -55.0), (0x7D0 + 24, -55.0)} |
                                        ({(0x7D0 + lh, -55.0 - GB.FSMASH_EXTRA)} if hasattr(GB, 'FSMASH_EXTRA') else set())))
    j25 = sorted({(n, c.name, int(c.params[c.info['syntax'].index('Bone')])) for n in ('attackairf', 'attackhi4', 'specialnhold')
                  for c in ce.scripts.get(zlib.crc32(n.encode()), []) if 'Bone' in c.info['syntax'] and
                  c.name in ('External_Graphic', 'Graphic_Effect2')})
    check('clone fixes v2 (the user: the clones\' forward air sword / trail hang down): his joint-25 effects (the water sword, '
          'its flames, the smashes\' second sword) on the clone\'s %s (0x7D0 + %d), not its still ThrowN (0x7D0 + 25)%s' % (
              GB.CLONE_JOINT_FIX.get(25), lh, ' (v1.5: the right hand, the user: "HaveR fixed the sword")' if lh == 24 else ''),
          sorted({b_ for _n, _c, b_ in j25 if b_ >= 0x7D0}), sorted({0x7D0 + lh, 0x7D0 + 24}))
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
    if len(earlier) == 33:   # burn tint v1: the exes only
        want_top = ['INSTALL_TO_code', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (37, 38):   # round gauge v1: the damage panel's files; clone fix v3: his MSC
        want_top = ['INSTALL_TO_data', 'README.txt']
    if len(earlier) in (42, 44, 45, 46, 47, 48):   # parabeetle v2: the exes (ice3, ccol) and his / the beetle's MSC; parabeetle v1: the exes (pbeetle), data (+ Sm4shCommand); usmash spike v2 / trail dim v1: the exes (ice2, bgrav) and data; ice detonation v1: the exes, data (+ Sm4shCommand); tuning v1: the exes (the gauge's ready state, the skeleton's bottom) and data; smash
        # tune v1: the exes (the half shield damage) and data
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (41, 43):   # clone moves v1, nair / fair v1: data only
        want_top = ['INSTALL_TO_data', 'README.txt']
    if len(earlier) == 40:   # round gauge v1.1: the panel file and the exes
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 39:   # freeze fix v1: his MSC, v3's files reverted one at a time (test)
        want_top = ['INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA']
    if len(earlier) == 36:   # clone articles v1: the exes and the MSCs
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) == 35:   # aligned kick v1: data only
        want_top = ['INSTALL_TO_data', 'README.txt']
    if len(earlier) == 34:   # skeleton v1.7: the exes, the skeleton's data and his bank, test data
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_DATA', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (20, 21, 26, 30, 31):   # skeleton v1.2 / burn v2 / skeleton v1.3 / v1.5 / v1.6: the exes, the data, test exes
        want_top = ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code']
    if len(earlier) in (23, 24, 25, 27, 28, 32):   # burn v2.2 / v2.3 / aerial chain v1 / clone fixes v1 / trail fix / tilt
        # chain v1: data only
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
        again = {'INSTALL_TO_data/fighter/gekkouga/model/skeleton/c00/skeleton.lvd'} if len(earlier) == 29 else \
            {'INSTALL_TO_data/sound/config/soundlabeltable.bin'} if len(earlier) == 30 else set()   # skeleton v1.4: the box skeleton.lvd again on purpose (it
        # replaces skeleton v1.1's TEST_ONLY floor-only one the user had installed)
        check('update: none of the installed unchanged files again (%d unchanged)%s' % (len(same1), ', but skeleton.lvd' if again
              else ''), [w for w in same1 if w in names and w not in again], [])
        check('update: nothing in INSTALL_TO_data but the built files%s' % (' (and round gauge v1\'s ui/info/dmg: gauge_tests)'
                                                                          if len(earlier) in (37, 40) else ''),
              sorted(n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/') and n not in want and
                     n not in again and not (len(earlier) in (37, 40) and n.startswith('INSTALL_TO_data/ui/info/dmg/')) and
                     not (len(earlier) == 40 and n == 'INSTALL_TO_data/param/fighter/fighter_param_vl_gekkouga.bin') and
                     not (len(earlier) == 46 and n == 'INSTALL_TO_data/sound/config/soundlabeltable.bin')), [])
        if len(earlier) == 46:
            check('usmash spike v2 / trail dim v1: INSTALL_TO_data/sound/config/soundlabeltable.bin the built one (his row + '
                  'label 97: the ice detonation\'s sound), new over what the earlier packages install',
                  (z.read('INSTALL_TO_data/sound/config/soundlabeltable.bin') ==
                   open(os.path.join(out, 'sound', 'config', 'soundlabeltable.bin'), 'rb').read(),
                   z.read('INSTALL_TO_data/sound/config/soundlabeltable.bin') !=
                   z1.read('INSTALL_TO_data/sound/config/soundlabeltable.bin')), (True, True))
        if len(earlier) in (18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
                            43, 48):
            check('update: no Sm4shCommand (no script or slot changed)', [t for t in top if t.startswith('Sm4shCommand_v')], [])
        elif len(earlier) == 47:
            check('parabeetle v1: Sm4shCommand v1.7.30 (ParabeetleWait / Rise / Ridden in ModAnimNames.txt, with -> lines)',
                  ([t for t in top if t.startswith('Sm4shCommand_v')],
                   z.read('Sm4shCommand_v1.7.30/ModAnimNames.txt') == open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand',
                                                                                         'ModAnimNames.txt'), 'rb').read()),
                  (['Sm4shCommand_v1.7.30'], True))
            mn = open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand', 'ModAnimNames.txt')).read()
            check('parabeetle v1: ModAnimNames.txt names its 3 scripts, each with a -> line to its own animation '
                  '(parabeetle/FitGekkougaParabeetleMain*.omo: the Hitbox Viewer plays them)',
                  [n for n, f in zip(GB.PB_SCRIPTS, CC.PB_MOTIONS) if '%s -> parabeetle/%s.omo' % (n, f) not in mn], [])
        elif len(earlier) == 45:
            check('ice detonation v1: Sm4shCommand v1.7.29 (FireTrailIceBoom in ModAnimNames.txt)',
                  ([t for t in top if t.startswith('Sm4shCommand_v')],
                   z.read('Sm4shCommand_v1.7.29/ModAnimNames.txt') == open(os.path.join(HERE, 'Sm4shCommand', 'SM4SHCommand',
                                                                                         'ModAnimNames.txt'), 'rb').read()),
                  (['Sm4shCommand_v1.7.29'], True))
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
    if z1 and len(earlier) == 37:
        check('round gauge v1: INSTALL_TO_data: ui/info/dmg\'s dmg.flx, texlist.lst and the new img-00135.nut (the other '
              'images as they are); the exe is clone articles v1\'s',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['ui/info/dmg/dmg.flx', 'ui/info/dmg/img-00135.nut', 'ui/info/dmg/texlist.lst'])
        if GAUGE_SRC and GAUGE_JPG:
            gauge_tests(z)
    if z1 and len(earlier) == 48:
        check('parabeetle v2: INSTALL_TO_data: his MSC (the snap, the stick\'s direction, the slot map, the clone\'s costume '
              'flag) and the Parabeetle\'s MSC (the hold, the path, the wings); INSTALL_TO_code exe_v46z_gkb18; TEST_ONLY '
              'A_release; no Sm4shCommand (no script or slot added)',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/parabeetle/parabeetle.mscsb'],
               ['A_release']))
    if z1 and len(earlier) == 47:
        check('parabeetle v1: INSTALL_TO_data: his MSC (the up special\'s end, the cooldown, the clones\' beetles) and the '
              'Parabeetle\'s files (model + parabeetle.lvd, motion, scripts, MSC); INSTALL_TO_code exe_v46z_gkb17; TEST_ONLY '
              'A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (sorted(['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/parabeetle/parabeetle.mscsb',
                       'fighter/gekkouga/motion/parabeetle/main.pac'] +
                      ['fighter/gekkouga/model/parabeetle/c00/' + f for f in (
                          'model.nud', 'model.nut', 'model.vbn', 'model.jtb', 'model.sb', 'model.nhb', 'model.xmb', 'model.flp',
                          'parabeetle.lvd')] +
                      ['fighter/gekkouga/script/animcmd/weapon/parabeetle/' + f for f in (
                          'game.bin', 'effect.bin', 'sound.bin', 'motion.mtable')]), ['A_release']))
    if z1 and len(earlier) == 45:
        check('ice detonation v1: INSTALL_TO_data: his MSC (the blast request), his bank (the explosion, the sparkles), the '
              'fire trail\'s MSC (the blast mode) and scripts (its 4th slot), the shuriken\'s game / effect scripts; '
              'INSTALL_TO_code exe_v46z_gkb15; TEST_ONLY A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (sorted('fighter/gekkouga/' + x for x in (
                  'effect/gekkouga/gekkouga.010d0000.efc', 'effect/gekkouga/gekkouga.010d0000.ptcl',
                  'script/animcmd/weapon/firetrail/effect.bin', 'script/animcmd/weapon/firetrail/game.bin',
                  'script/animcmd/weapon/firetrail/motion.mtable', 'script/animcmd/weapon/firetrail/sound.bin',
                  'script/animcmd/weapon/shuriken/effect.bin', 'script/animcmd/weapon/shuriken/game.bin',
                  'script/msc/firetrail/firetrail.mscsb', 'script/msc/gekkouga.mscsb')), ['A_release']))
    if z1 and len(earlier) == 44:
        check('smash tune v1: INSTALL_TO_data: his MSC (the pursuit, the uncharged ratio, the clones\' Tap Jump), his and the '
              'clone\'s game scripts (up smash\'s spike, the windbox ring, the clones\' x1.0), the fire trail\'s hitboxes (the '
              'shield marker); INSTALL_TO_code exe_v46z_gkb14; TEST_ONLY A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (sorted('fighter/gekkouga/' + x for x in (
                  'script/animcmd/body/game.bin', 'script/animcmd/weapon/clone/game.bin',
                  'script/animcmd/weapon/firetrail/game.bin', 'script/msc/gekkouga.mscsb')), ['A_release']))
    if z1 and len(earlier) == 43:
        check('nair / fair v1: INSTALL_TO_data: his and the clone\'s game / effect scripts (neutral air\'s sizes and ring, '
              'forward air\'s reach), trail lite v1\'s bank (the wider trail flames) and fire trail MSC; no exe (tuning '
              'v1\'s)', sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and
                                not n.endswith('/')),
              sorted('fighter/gekkouga/' + x for x in (
                  'effect/gekkouga/gekkouga.010d0000.ptcl', 'script/animcmd/body/effect.bin', 'script/animcmd/body/game.bin',
                  'script/animcmd/weapon/clone/effect.bin', 'script/animcmd/weapon/clone/game.bin',
                  'script/msc/firetrail/firetrail.mscsb')))
    if z1 and len(earlier) == 42:
        check('tuning v1: INSTALL_TO_data: his scripts (game / effect: forward smash, neutral air, forward tilt, the star), '
              'the clone\'s copies, his MSC (the ledge), the fire trail\'s hitboxes and MSC, his effect bank (the trails\' '
              'flames), the skeleton\'s collision (its bottom); INSTALL_TO_code exe_v46z_gkb13; TEST_ONLY A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (sorted('fighter/gekkouga/' + x for x in (
                  'effect/gekkouga/gekkouga.010d0000.ptcl', 'model/skeleton/c00/skeleton.lvd', 'script/animcmd/body/effect.bin',
                  'script/animcmd/body/game.bin', 'script/animcmd/weapon/clone/effect.bin', 'script/animcmd/weapon/clone/game.bin',
                  'script/animcmd/weapon/firetrail/game.bin', 'script/msc/firetrail/firetrail.mscsb',
                  'script/msc/gekkouga.mscsb')), ['A_release']))
    if z1 and len(earlier) == 41:
        check('clone moves v1: INSTALL_TO_data: his MSC (the mirroring, the shield\'s block), the clone\'s MSC (dodges, the '
              'shield\'s re-arm, the charge orb, the run\'s dust) and game scripts (grab / pummel / throws); the exe is '
              'round gauge v1.1\'s', sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/')
                                             and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/weapon/clone/game.bin', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
               'fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 40:
        check('round gauge v1.1: INSTALL_TO_data: ui/info/dmg\'s dmg.flx (texlist / img-00135 as v1), his MSC and his vl '
              '(the charge\'s invulnerability removed); INSTALL_TO_code: exe_v46z_gkb12 (feature gauge2: the charge cyan, '
              'the diag\'s S4GB line with the clip found); TEST_ONLY: A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (['fighter/gekkouga/script/msc/gekkouga.mscsb', 'param/fighter/fighter_param_vl_gekkouga.bin',
                'ui/info/dmg/dmg.flx'], ['A_release']))
        check('... its vl: the build\'s (tools/gekkouga_build.py vl)', z.read('INSTALL_TO_data/param/fighter/fighter_param_vl_gekkouga.bin')
              == open(os.path.join(out, 'param', 'fighter', 'fighter_param_vl_gekkouga.bin'), 'rb').read(), True)
        if GAUGE_SRC and GAUGE_JPG:
            gauge_tests(z, v11=True, inst=z1)
    if z1 and len(earlier) == 39:
        check('freeze fix v1: INSTALL_TO_data: his MSC only (no bitXor); TEST_ONLY_DATA: each of clone fixes v3\'s files as '
              'clone articles v1 had it',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted(n[len('TEST_ONLY_DATA/'):] for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/'))),
              (['fighter/gekkouga/script/msc/gekkouga.mscsb'],
               ['revert_1_gekkouga_msc/fighter/gekkouga/script/msc/gekkouga.mscsb',
                'revert_2_clone_effect/fighter/gekkouga/script/animcmd/weapon/clone/effect.bin',
                'revert_3_clone_msc/fighter/gekkouga/script/msc/clone/clone.mscsb',
                'revert_4_shuriken_msc/fighter/gekkouga/script/msc/shuriken/shuriken.mscsb']))
        ca = Installed(earlier[:next(i for i, e in enumerate(earlier) if 'clone_articles' in e) + 1])
        check('... each revert is clone articles v1\'s file byte for byte',
              [n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/') and
               z.read(n) != ca.read('INSTALL_TO_data/' + n.split('/', 2)[2])], [])
    if z1 and len(earlier) == 38:
        check('clone fix v3: INSTALL_TO_data: his MSC (the activating press used up, the kick\'s lockout, the removal reasons, '
              'the copies\' reports, the split holds\' charge), his shuriken\'s (the copies held on their clone\'s place), the '
              'clone\'s MSC (its split holds\' charge effects) and effect scripts (the JUMP-only ones); the exe is clone '
              'articles v1\'s', sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/weapon/clone/effect.bin', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
               'fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/shuriken/shuriken.mscsb'])
    if z1 and len(earlier) == 36:
        check('clone articles v1: INSTALL_TO_data: his MSC (the clones\' skeletons / shuriken copies, the KO\'s smash charge), '
              'the clone\'s (its hitboxes cleared on a new motion), the skeleton\'s (its seat), his shuriken\'s (new: the '
              'copies\' claim and move); TEST_ONLY: A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (['fighter/gekkouga/script/msc/clone/clone.mscsb', 'fighter/gekkouga/script/msc/gekkouga.mscsb',
                'fighter/gekkouga/script/msc/shuriken/shuriken.mscsb', 'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb'],
               ['A_release']))
    if z1 and len(earlier) == 35:
        check('aligned kick v1: INSTALL_TO_data: his MSC (the kick, split clones, the regroup, the effects epoch, the charge '
              'reset at a KO), the clone\'s MSC (free mode, the epoch) and scripts (the kick); the exe is skeleton v1.7\'s',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/animcmd/weapon/clone/effect.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
               'fighter/gekkouga/script/msc/clone/clone.mscsb', 'fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 34:
        check('skeleton v1.7: INSTALL_TO_data: the skeleton\'s game.bin (the explosion\'s window, the contact hitbox with '
              'rehit 3) and MSC (0.58 a frame, the explosion held / ended, its sounds noted), his effect bank (the run '
              'flipbook slowed as much); TEST_ONLY_DATA skeleton_toggle (v1.6\'s contact) and sound_via_greninja (his MSC '
              '= tilt chain v1\'s + the spawn sound from him); TEST_ONLY: A_release',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted(n for n in names if n.startswith('TEST_ONLY_DATA/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl',
                'fighter/gekkouga/script/animcmd/weapon/skeleton/game.bin',
                'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb'],
               ['TEST_ONLY_DATA/skeleton_toggle/fighter/gekkouga/script/animcmd/weapon/skeleton/game.bin',
                'TEST_ONLY_DATA/sound_via_greninja/fighter/gekkouga/script/msc/gekkouga.mscsb'], ['A_release']))
        snd = z.read('TEST_ONLY_DATA/sound_via_greninja/fighter/gekkouga/script/msc/gekkouga.mscsb')
        inst = z1.read('INSTALL_TO_data/fighter/gekkouga/script/msc/gekkouga.mscsb')
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'g.c')
            repo = ROOT if os.path.exists(os.path.join(ROOT, '.git')) else os.environ.get('GK_REPO', ROOT)
            subprocess.run(['git', '-C', repo, 'show', 'bc7e3ea:fighters/gekkouga/gekkouga.c'], stdout=open(src, 'w'), check=True)
            o1, o2 = os.path.join(td, 'a.mscsb'), os.path.join(td, 'b.mscsb')
            GB.compile_msc(src, o1)
            open(src + '2.c', 'w').write(GB.sound_test_msc(open(src).read()))
            GB.compile_msc(src + '2.c', o2)
            check('skeleton v1.7 sound_via_greninja: his installed MSC (tilt chain v1\'s) rebuilt from git bc7e3ea byte for '
                  'byte; the test MSC is it + one line (SoundModule 0x2710 0x0768005B in gk_sk_spawn)',
                  (open(o1, 'rb').read() == inst, open(o2, 'rb').read() == snd), (True, True))
    if z1 and len(earlier) == 32:
        check('tilt chain v1: INSTALL_TO_data: his MSC only (the exe is skeleton v1.6\'s)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/script/msc/gekkouga.mscsb'])
    if z1 and len(earlier) == 31:
        check('skeleton v1.6: INSTALL_TO_data: his MSC (the shadow carried on to 36, no side special while a skeleton runs) '
              'and the skeleton\'s MSC (its heartbeat); TEST_ONLY: A_release only (no G_pose: the user)',
              (sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
               sorted({n.split('/')[1] for n in names if n.startswith('TEST_ONLY_INSTALL_TO_code/') and n.count('/') > 1})),
              (['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb'],
               ['A_release']))
    if z1 and len(earlier) == 30:
        check('skeleton v1.5: INSTALL_TO_data: his effect bank (the skeleton\'s body shifted onto its place, the explosion '
              'x 1.23), the body-sized skeleton.lvd, the skeleton\'s game.bin (its contact hitbox, the explosion\'s hitstun / '
              'size / shield damage) and MSC (its sounds), the clone\'s game / effect.bin (joint 25 on the right hand: '
              'confirmed in game), his se bank (+ 6 sounds) and the soundlabeltable (his row + 6 labels)',
              sorted(n[len('INSTALL_TO_data/'):] for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')),
              ['fighter/gekkouga/effect/gekkouga/gekkouga.010d0000.ptcl', 'fighter/gekkouga/model/skeleton/c00/skeleton.lvd',
               'fighter/gekkouga/script/animcmd/weapon/clone/effect.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
               'fighter/gekkouga/script/animcmd/weapon/skeleton/game.bin', 'fighter/gekkouga/script/msc/skeleton/skeleton.mscsb',
               'fighter/gekkouga/sound/snd_se_Gekkouga.nus3bank', 'sound/config/soundlabeltable.bin'])
        import fighter_own_bank as FB
        import minecraft_sound as MS
        import gekkouga_sound as GS
        bank = z.read('INSTALL_TO_data/fighter/gekkouga/sound/snd_se_Gekkouga.nus3bank')
        _s, tones = MS.tones_of(bank)
        new = [MS.parse_entry(e) for e in tones[-len(GS.SOUNDS):]]
        frames = [round(struct.unpack('<I', r[-0x18:-0x14])[0] * 60 / 48000) for _h, _n, r in new]
        t_new = FB.Table(z.read('INSTALL_TO_data/sound/config/soundlabeltable.bin'))
        t_old = FB.Table(open(os.path.join(out, 'TEST_ONLY_STB_BASE'), 'rb').read()) if os.path.exists(
            os.path.join(out, 'TEST_ONLY_STB_BASE')) else None
        row = t_new.row_of(2058)
        others = None if t_old is None else [i for i in range(len(t_old.rows)) if i != row and
                                             t_old.tones(i) != t_new.tones(i)]
        check('skeleton v1.5 sounds: his bank (BINF snd_se_Gekkouga 2058, kept) + 6 one-shots snd_se_Gekkouga_<label> '
              '(%s); his row 0x768 = his 91 labels + their tones (labels 91 - 96); no other row changed; the voices\' '
              'lengths the MSC\'s (80 / 231 frames)' % ', '.join(l for l, _f, _v in GS.SOUNDS),
              (FB.binf(bank), len(tones), [n for _h, n, _r in new], row, t_new.tones(row)[91:], others,
               frames[2:4]),
              (('snd_se_Gekkouga', 2058), 110, ['snd_se_Gekkouga_' + l for l, _f, _v in GS.SOUNDS], 0x768,
               list(range(104, 110)), [] if t_old is not None else None, [80, 231]))
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
                                                               len(earlier) in (26, 27, 28, 29), len(earlier) == 30,
                                                               len(earlier) in (31, 32), len(earlier) == 33,
                                                               len(earlier) in (34, 35), len(earlier) in (36, 37, 38, 39),
                                                               len(earlier) in (40, 41), len(earlier) in (42, 43),
                                                               len(earlier) == 44, len(earlier) == 45, len(earlier) == 46)):
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
         'E_sway', 'S4GR', 'S4GH', '401', 'confirmed', 'TEST_ONLY_DATA/sway') if len(earlier) not in tuple(range(17, 49)) else \
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
        ('greninja_skeleton_v1_4', 'exe_v46z_gkb7', 'body', '3.5', '24', 'contact', '70', '3.5%', 'every 3 frames', 'spawn', 'death', 'explosion', 'soundlabeltable', 'nus3bank', '27', 'shield damage',
         'shield', '1.6', 'hitstun', 'right hand', 'skeleton_box.png', 'unconfirmed', 'A_release') if len(earlier) == 30 else \
        ('greninja_skeleton_v1_5', 'exe_v46z_gkb8', '36', 'shadow', 'tap', 'hold', '9.2', 'alive', 'explo', 'side special',
         'air', 'A_release', 'G_pose', 'unconfirmed') if len(earlier) == 31 else \
        ('greninja_skeleton_v1_6', 'jab', 'tilt', 'rapid', 'hit', 'shield', 'once', 'clone', 'smash', 'S4GF', '2097152',
         'unconfirmed', 'exe_v46z_gkb8') if len(earlier) == 32 else \
        ('greninja_tilt_chain_v1', 'exe_v46z_gkb9', 'orange', 'hot red', 'outline', 'tier', 'fade', 'KO', 'reset',
         'Supamario', 'burn_tint.png', 'A_release', 'unconfirmed') if len(earlier) == 33 else \
        ('greninja_burn_tint_v1', 'exe_v46z_gkb10', 'explosion', 'orange', '102', 'once', 'contact', 'rehit', '3', '20',
         'hit record', 'skeleton_toggle', 'SoundModule', 'null', 'S4SN', 'sound_via_greninja', '0.58', 'flipbook',
         'A_release', 'unconfirmed') if len(earlier) == 34 else \
        ('greninja_skeleton_v1_7', 'down special', 'left', 'right', 'straight up', 'held', 'tapped', '64', '46.5', '78',
         'swap', 'Fall', 'once', 'split', 'mirror', 'aerial', 'smash', 'jump', 'landing', 'shield', 'regroup', 'stance',
         'effect', 'KO', 'charge', 'smash charge', 'unconfirmed') if len(earlier) == 35 else \
        ('greninja_aligned_kick_v1', 'exe_v46z_gkb11', 'skeleton', 'stack', '24', 'level', 'falls', 'shuriken', 'charge',
         'Hydro Pump', 'native', 'side special', 'hitbox', 'kick', 'smash charge', 'KO', 'A_release', 'unconfirmed') \
        if len(earlier) == 36 else \
        ('greninja_clone_articles_v1', 'round', 'gauge', 'img-00135', 'texlist', 'KO meter', 'badge', 'ring', 'fill',
         'cyan', 'blue', 'grey', 'preview', 'unconfirmed') if len(earlier) == 37 else \
        ('greninja_clone_articles_v1', 'round gauge', 'exe_v46z_gkb11', 'activates', '10 frames', 'fresh press', 'held',
         'kick', 'shuriken', 'clone\'s place', 'S4GF', 'gen=', '500', '600', '701', '801', 'charging', 'landing', 'double jump',
         'unconfirmed') if len(earlier) == 38 else \
        ('greninja_clonefix_v3', 'froze', 'bitXor', '0x19', 'revert_1_gekkouga_msc', 'revert_2_clone_effect',
         'revert_3_clone_msc', 'revert_4_shuriken_msc', 'exe_v46z_gkb11', 'unconfirmed') if len(earlier) == 39 else \
        ('greninja_freeze_fix_v1', 'emblem', '0.87', 'hidden', 'Greninja', 'cyan', 'exe_v46z_gkb12', 'S4GB', 'clip',
         'preview', 'invulnerab', 'intangible', '8 - 19', 'fighter_param_vl_gekkouga', 'unconfirmed') if len(earlier) == 40 else \
        ('greninja_round_gauge_v1_1', 'shield', 'dodge', 'grab', 'pummel', 'throw', 'neutral special', 'side special',
         'up special', 'down special', 'ledge', 'dust', 'water shuriken', 'Hitbox_Hold', 'unconfirmed') if len(earlier) == 41 else \
        ('greninja_clone_moves_v1', 'exe_v46z_gkb13', 'forward smash', 'Donkey Kong', 'fire trail', 'neutral air', 'shield break',
         '25%', 'forward tilt', 'teleport', 'READY', 'ledge', 'skeleton', 'bottom', 'star', 'S4SB', 'unconfirmed') if len(earlier) == 42 else \
        ('greninja_tuning_v1', 'exe_v46z_gkb13', 'neutral air', 'Part 1', 'Part 0', 'hexagon', '2.5 %', 'angle 60', 'burn',
         'forward air', 'Donkey Kong', '22.4', '19.9', 'clones', 'trail', 'nair_ring_hitboxes.png', 'fair_reach_tuning.png',
         'knockback', 'unconfirmed') if len(earlier) == 43 else \
        ('greninja_nair_fair_v1', 'exe_v46z_gkb14', 'pursuit', 'shield', 'ledge', 'chain', '12', 'uncharged', 'burn',
         'x1.4', 'knockback', 'spike', 'angle 300', 'inner', 'lower hitbox ID', '1.19', '8.3', 'Tap Jump', 'A+B',
         'windbox', 'F.L.U.D.D.', 'no hitlag', 'fsmash_pursuit.png', 'unconfirmed') if len(earlier) == 44 else \
        ('greninja_smash_tune_v1', 'exe_v46z_gkb15', 'ice', 'burn', '52', 'yellow', 'black', '60', 'KBG 80', 'BKB 50',
         'smoke', '8x', 'Water Shuriken', 'uncharged', 'sparkle', 'S4IA', 'S4IB', 'S4IC', 'shield', 'ice_boom.gif',
         'ice_flash.gif', 'ice_sparkle.gif', 'Sm4shCommand_v1.7.29', 'confirmed in game') if len(earlier) == 45 else \
        ('greninja_ice_detonation_v1', 'exe_v46z_gkb16', 'spike', '300', 'KBG 50', 'BKB 25', 'geyser', 'trail', '0.65',
         'neutral air', 'nair_fair_v1', 'IceBoom', '156', 'creeper', 'S4ID', 'S4IF', 'S4BG', '840', 'gravity', 'air dodge',
         'LandingLight', 'trail_dim.png', 'confirmed in game') if len(earlier) == 46 else \
        ('greninja_usmash_trail_v1', 'exe_v46z_gkb17', 'Parabeetle', 'stance', '450', '7.5', 'cooldown', 'special fall',
         'boost', '21', 'jet', 'Fall', 'drop', 'down', 'carr', 'swoop', '0.75', '0.4', '240', 'wait', 'rise', 'ridden',
         'clone', '1.25', 'parabeetle.lvd', 'S4PB', 'S4PC', 'S4PF', 'Sm4shCommand_v1.7.30', 'parabeetle_model.png',
         'parabeetle_anims.gif', 'confirmed in game') if len(earlier) == 47 else \
        ('greninja_parabeetle_v1', 'exe_v46z_gkb18', 'costume', 'c00', 'c07', 'snap', 'Wait', 'drop', 'vertical', '0.7',
         '144', '3.5', 'neutral', 'left', 'right', 'down', 'wings', 'loop', 'slot', 'TIMER', 'Outline_Set', 'Outline_Shell',
         'S4IF', 'S4CK', 'S4BR', 'parabeetle_path.png', 'parabeetle_wings.gif', 'confirmed in game') if len(earlier) == 48 else \
        ('greninja_skeleton_v1', 'exe_v46z_gk14', 'tongue', 'water', 'A_release', 'E_sway', 'S4TP', 'S4GQ', 'S4GR',
         'TEST_ONLY_DATA/sway', 'TEST_ONLY_DATA/rigid', 'crash', '+0x10', 'unconfirmed', 'S4SD', 'S4SE', 'S4SG',
         'skeleton_floor_only', 'collision') if len(earlier) == 18 else \
        ('greninja_clones_v14', 'exe_v46z_gk15', 'confirmed in game: native swing (v14 E_sway)', 'tongue', 'water',
         'A_release', 'G_pose', 'TEST_ONLY_DATA/rigid', 'skeleton_floor_only', 'S4SD', 'unconfirmed') if len(earlier) == 19 else \
        ('greninja_burn_v1_2', 'exe_v46z_gks1', 'Running Skeleton', '25', '180', '0.7', 'ledge', 'smoke', 'explo', '36',
         '6.3', 'S4SS', 'S4SH', 'S4SX', 'S4SC', 'S4SF', 'hydrant', 'placeholder', 'Sm4shCommand_v1.7.27', 'unconfirmed')
    check('README.txt mentions every feature (%s)' % ', '.join(words), [w for w in words if w not in readme], [])
    check('no fighter- or game-named wrapper folder', [t for t in top if t.lower() in ('gekkouga', 'greninja', 'fighter', 'data', 'smash4')], [])


def exe_members(base, base_diag, v4, skeleton=False, v14=False, v15=False, sk12=False, b2=False, gkb5=False, gkb6=False,
                gkb7=False, gkb8=False, gkb9=False, gkb10=False, gkb11=False, gkb12=False, gkb13=False, gkb14=False,
                gkb15=False, gkb16=False, gkb17=False):
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
        drop |= {'skdist'} if sk12 or b2 or gkb5 or gkb6 or gkb7 else set()      # (skeleton v1.6's gkb8)
        drop |= {'btint'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 else set()   # (burn tint v1's gkb9)
        drop |= {'mark', 'sksnd'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 else set()   # (skeleton v1.7's gkb10)
        drop |= {'cart'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 else set()   # (clone articles v1's gkb11)
        drop |= {'gauge2'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 else set()   # (round
        # gauge v1.1's gkb12)
        drop |= {'gready', 'skbot'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 \
            else set()   # (tuning v1's gkb13)
        drop |= {'shalf'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 or gkb13 \
            else set()   # (smash tune v1's gkb14)
        drop |= {'ice'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 or gkb13 or gkb14 \
            else set()   # (ice detonation v1's gkb15)
        drop |= {'ice2', 'bgrav'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 or gkb13 \
            or gkb14 or gkb15 else set()   # (usmash spike v2 / trail dim v1's gkb16)
        drop |= {'pbeetle'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 or gkb13 \
            or gkb14 or gkb15 or gkb16 else set()   # (parabeetle v1's gkb17)
        drop |= {'ice3', 'ccol'} if sk12 or b2 or gkb5 or gkb6 or gkb7 or gkb8 or gkb9 or gkb10 or gkb11 or gkb12 or gkb13 \
            or gkb14 or gkb15 or gkb16 or gkb17 else set()   # (parabeetle v2's gkb18)
        variants = C.VARIANTS if not (sk12 or b2 or gkb5 or gkb6 or gkb7) else \
            C.VARIANTS + (('G_pose', (C.RELEASE - {'sway'}) | {'pose'}),)       # (up to v1.5: + G_pose)
        return [('INSTALL_TO_code/cross_f.rpx', base, False, C.RELEASE - drop)] + \
            [('TEST_ONLY_INSTALL_TO_code/%s/cross_f.rpx' % n, base_diag, True, f - drop) for n, f in variants]
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
                   (os.path.join(msc, 'firetrail', 'firetrail.mscsb'), GB.TRAIL_MSC),
                   (os.path.join(msc, 'shuriken', 'shuriken.mscsb'), getattr(GB, 'SHURIKEN_MSC', '')),
                   (os.path.join(msc, 'parabeetle', 'parabeetle.mscsb'), getattr(GB, 'PARABEETLE_MSC', ''))):
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
                                                len(earlier) in (22, 23, 24, 25), len(earlier) in (26, 27, 28, 29),
                                                len(earlier) == 30, len(earlier) in (31, 32), len(earlier) == 33,
                                                len(earlier) in (34, 35), len(earlier) in (36, 37, 38, 39),
                                                len(earlier) in (40, 41), len(earlier) in (42, 43), len(earlier) == 44,
                                                len(earlier) == 45, len(earlier) == 46, len(earlier) == 47):
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


def pb_his_setup(mscsb, src, situation=2, lr=1.0):
    """parabeetle v1: his MSC with the calls the up special's end makes logged (Kinetic, Ground, Model, the situation)"""
    import math
    m = fresh(mscsb, src)
    g = m.game
    g.lr = lr
    g.situation = situation
    m.vm.g[18] = 0 if situation == 0 else 2

    def sysf(sid, a, old=g.sys):
        if sid == 0x10:
            g.log.append(('kinetic', a[0], a[1]) + tuple(fv(x) for x in a[2:3]))
            return 0
        if sid == 0x1A:
            g.log.append(('ground', a[0], a[1]))
            return 0
        if sid == 0x27:
            g.log.append(('model', a[0], a[1]) + tuple(fv(x) for x in a[2:5]))
            return 0
        if sid == 0x18 and a[0] == 0x2:
            g.log.append(('situation', a[1]))
            return 0
        if sid == 0xA and a[0] == 0:                     # parabeetle v2: MathF(0, x): sqrt; (1, a, b): atan2(a, b)
            return f2i(math.sqrt(max(fv(a[1]), 0.0)))
        if sid == 0xA and a[0] == 0x1:
            return f2i(math.atan2(fv(a[1]), fv(a[2])))
        return old(sid, a)
    g.sys = sysf
    return m, g


def parabeetle_side_tests(mscsb, src):
    """parabeetle v1 (README "Parabeetle v1"): his up special's stance end (gk_pb_end: MSC_EDITS func_2303), the request
    and the clones' queue (gk_pb_tick), the cooldown, the boost, the KO / reset, the ride heartbeat and the clones' ride"""
    REQ, BOOST = CC.GK_VAR_PBREQ, 0x0F00030D
    c = open(src).read()
    a, b, e_ = GB.func_span(c, 'func_2303')
    body = c[b:e_]
    check('parabeetle: his stance\'s loop (SpecialHi 0x154, func_2303) ends in gk_pb_end at its motion\'s end; no jet '
          '(SpecialHiJet 0x15D) anywhere in it (so no water article, effect or sound)',
          ('if (MotionModule(0x2712))\n    {\n        gk_pb_end();' in body, '0x15d' in body), (True, False))
    m, g = pb_his_setup(mscsb, src)
    check('parabeetle constants: cooldown 450 (7.5 s), article 10, request life 5, boost 2.75; v2: the ground lift 9.5, '
          'the snap 12 frames (his TIMER_12)',
          (m('gk_pb_cooldown'), m('gk_pb_article'), m('gk_pb_req_frames'), fv(m('gk_pb_boost')), fv(m('gk_pb_lift')),
           m('gk_pb_snap_frames')), (450, 10, 5, 2.75, 9.5, 12))
    grav = 0.18
    full = 3.7 * 10 + 3.7 * 0.9 * 10 + (3.7 * 0.9 * 0.7) ** 2 / (2 * grav)
    boost = 2.75 ** 2 / (2 * grav)
    check('parabeetle: the boost rises %.1f units (2.75^2 / (2 x 0.18)), about a quarter of a straight-up Hydro Pump (%.1f: '
          'two jets 3.7 / 3.33 a frame x 10 frames, the end\'s 0.7 x speed under his gravity)' % (boost, full),
          0.2 <= boost / full <= 0.3, True)
    # ---- off cooldown, in the air, facing right
    m('gk_pb_end')
    check('parabeetle: off cooldown, in the air: Fall (0xE: actionable), not the jet; his stance\'s lean undone '
          '(ModelModule(1, 2, 0, 0, 0)); a Parabeetle asked for (his VAR_12 = +1: his own, neutral: straight up toward his '
          'facing, right) and made (ArticleModule(0x2710, 10)); v2: held still (his gravity energy 0) for the snap (his '
          'TIMER_12 = 12), no hop',
          (g.status_req, [x for x in g.log if x[0] == 'model'], g.vars.get(REQ), [x for x in g.log if x[0] == 'article'],
           g.vars.get(BOOST, 0.0), [x for x in g.log if x[0] in ('kinetic', 'situation', 'ground')],
           g.vars.get(0x0F00032C)),
          ([(0xE, 0)], [('model', 1, 2, 0.0, 0.0, 0.0)], 1.0, [('article', 0x2710, 10)], 0.0,
           [('kinetic', 0x11, 1, 0.0), ('kinetic', 0xB, 1)], 12.0))
    check('parabeetle: the cooldown 450 from the spawn, the request up 5 frames', (m.g('gk_pb_cd'), m.g('gk_pb_req_t')),
          (450, 5))
    # ---- on the ground, facing left
    m, g = pb_his_setup(mscsb, src, situation=0, lr=-1.0)
    y0 = g.y
    m('gk_pb_end')
    check('parabeetle: on the ground (facing left): his VAR_12 = -5 (left, his own, + 4 grounded), Fall; v2: no hop: in '
          'the air by the game\'s own switch (func_102: KineticModule(0, 0), situation air, GroundModule(0x2710, 5)), put '
          '9.5 up (set_pos: its line will be at his feet, its swoop\'s lowest over the floor), held still, the snap pending',
          (g.vars.get(REQ), g.status_req, [x for x in g.log if x[0] in ('kinetic', 'situation', 'ground')],
           g.vars.get(BOOST, 0.0), round(g.y - y0, 3), g.vars.get(0x0F00032C)),
          (-5.0, [(0xE, 0)], [('kinetic', 0, 0), ('situation', 2), ('ground', 0x2710, 5), ('kinetic', 0x11, 1, 0.0),
                              ('kinetic', 0xB, 1)], 0.0, 9.5, 12.0))
    # ---- on cooldown
    m, g = pb_his_setup(mscsb, src)
    g.vars[0x0700000B], g.vars[0x0700000E] = 0.6, 32.0
    m.setg('gk_pb_cd', 300)
    m('gk_pb_end')
    check('parabeetle: on cooldown (in the air): SpecialFall (0x10), no Parabeetle (no request, no ArticleModule), up at '
          '2.75 (KineticModule 0x11, VAR_13 for his next frame), vanilla\'s special fall set-up (func_2329: landing lag '
          '0x0700000E 32, air speed 0x0700000B 0.6, flag 0x20000003), a puff at his feet (the cue); the cooldown runs on',
          (g.status_req, g.vars.get(REQ, 0.0), [x for x in g.log if x[0] == 'article'],
           [x for x in g.log if x[0] == 'kinetic'], g.vars.get(BOOST), (g.vars.get(0x0), g.vars.get(0x1)),
           0x20000003 in g.flags, [x[:2] for x in g.log if x[0] == 'effect'], m.g('gk_pb_cd')),
          ([(0x10, 0)], 0.0, [], [('kinetic', 0x11, 1, 2.75), ('kinetic', 0xB, 1)], 2.75, (32.0, 0.6), True,
           [('effect', 0x3)], 300))
    m2 = fresh(mscsb, src)
    m2.game.x, m2.game.y = 5.0, 7.0
    m2('gk_puff_at', f2i(5.0), f2i(7.0))
    check('parabeetle: the cooldown cue is his clones\' smoke puff (gk_puff_at) at his feet', [x[:2] for x in g.log if
          x[0] == 'effect'] == [x[:2] for x in m2.game.log if x[0] == 'effect'], True)
    m, g = pb_his_setup(mscsb, src, situation=0)
    m.setg('gk_pb_cd', 1)
    m('gk_pb_end')
    check('parabeetle: on cooldown on the ground: off the ground (situation air), up at 2.75, SpecialFall',
          (g.status_req, [x for x in g.log if x[0] in ('kinetic', 'situation', 'ground')]),
          ([(0x10, 0)], [('situation', 2), ('ground', 0x2710, 5), ('kinetic', 0x11, 1, 2.75), ('kinetic', 0xB, 1)]))
    # ---- the tick: the boost again on his first frame in SpecialFall / Fall, the cooldown down to 0
    m, g = pb_his_setup(mscsb, src)
    g.vars[BOOST] = 2.75
    m.vm.g[4] = 0x154
    m('gk_pb_tick')
    check('parabeetle tick: still in the stance (0x154): the boost waits', ([x for x in g.log if x[0] == 'kinetic'],
                                                                           g.vars.get(BOOST)), ([], 2.75))
    m.vm.g[4] = 0x10
    m('gk_pb_tick')
    check('parabeetle tick: his first frame in SpecialFall: up at 2.75 again (KineticModule 0x11 / 0xB), VAR_13 0',
          ([x for x in g.log if x[0] == 'kinetic'], g.vars.get(BOOST)), ([('kinetic', 0x11, 1, 2.75), ('kinetic', 0xB, 1)],
                                                                         0.0))
    g.vars[BOOST] = 2.4
    m.vm.g[4] = 0x1B
    g.log = []
    m('gk_pb_tick')
    check('parabeetle tick: out of the stance some other way (not Fall / SpecialFall): the pending boost dropped, not given',
          ([x for x in g.log if x[0] == 'kinetic'], g.vars.get(BOOST)), ([], 0.0))
    m.setg('gk_pb_cd', 450)
    for _ in range(449):
        m('gk_pb_tick')
    cd1 = m.g('gk_pb_cd')
    m('gk_pb_tick')
    check('parabeetle tick: the cooldown counts down a frame at a time: 1 left after 449, 0 at 450 (7.5 s)',
          (cd1, m.g('gk_pb_cd')), (1, 0))
    m('gk_pb_tick')
    check('parabeetle tick: ... and stays 0', m.g('gk_pb_cd'), 0)
    # ---- the clones' Parabeetles (two clones in formation), one a frame after his is claimed
    m, g = pb_his_setup(mscsb, src, lr=-1.0)
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 3)
    m('gk_pb_end')
    seq = [g.vars.get(REQ)]
    m('gk_pb_tick')
    seq.append(g.vars.get(REQ))
    g.vars[REQ] = 0.0                                     # the executable's claim (his beetle)
    m('gk_pb_tick')
    seq.append(g.vars.get(REQ))
    g.vars[REQ] = 0.0                                     # the left clone's claimed
    m('gk_pb_tick')
    seq.append(g.vars.get(REQ))
    g.vars[REQ] = 0.0
    m('gk_pb_tick')
    seq.append(g.vars.get(REQ))
    check('parabeetle clones (clone articles: both in formation): his request -1, kept while not claimed; claimed -> the '
          'left clone\'s (-2) the next frame, then the right one\'s (-3), then nothing; each made (ArticleModule 0x2710, '
          '10 x 3); one cooldown',
          (seq, [x for x in g.log if x[0] == 'article'], m.g('gk_pb_cd')),
          ([-1.0, -1.0, -2.0, -3.0, 0.0], [('article', 0x2710, 10)] * 3, 446))
    m, g = pb_his_setup(mscsb, src, situation=0)
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 2)
    m('gk_pb_end')
    g.vars[REQ] = 0.0
    m('gk_pb_tick')
    check('parabeetle clones: on the ground the clone\'s too (+4): only the right clone out: +7', g.vars.get(REQ), 7.0)
    m, g = pb_his_setup(mscsb, src)
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 3)
    m.setg('gk_lfall', 10)                                # the left clone falling on its own: not in formation
    m('gk_pb_end')
    g.vars[REQ] = 0.0
    m('gk_pb_tick')
    check('parabeetle clones: a clone falling on its own (not copying him) gets none: only the right one\'s (+3)',
          g.vars.get(REQ), 3.0)
    m, g = pb_his_setup(mscsb, src)
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 3)
    m.setg('gk_pb_cd', 100)
    m('gk_pb_end')
    m('gk_pb_tick')
    check('parabeetle clones: on cooldown: no beetle for them either (they mirror his boost)',
          (g.vars.get(REQ, 0.0), [x for x in g.log if x[0] == 'article'], g.status_req), (0.0, [], [(0x10, 0)]))
    # ---- not claimed: dropped
    m, g = pb_his_setup(mscsb, src)
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 3)
    m('gk_pb_end')
    for _ in range(5):
        m('gk_pb_tick')
    check('parabeetle: a request not claimed in 5 frames (no room: 3 out) dropped, and the clones\' with it',
          (g.vars.get(REQ), m.g('gk_pb_q'), m.g('gk_pb_req_t'), [x for x in g.log if x[0] == 'article']),
          (0.0, 0, 0, [('article', 0x2710, 10)]))
    # ---- KO / reset
    m, g = pb_his_setup(mscsb, src)
    m.setg('gk_pb_cd', 200)
    g.vars[REQ] = 1.0
    frames(m, 1, st=0xB1)
    check('parabeetle: his KO (Dead 0xB1): his beetles removed (ArticleModule(0x2712, 10)), the cooldown 0, no request',
          ([x for x in g.log if x[0] == 'article'], m.g('gk_pb_cd'), g.vars.get(REQ)), ([('article', 0x2712, 10)], 0, 0.0))
    m, g = pb_his_setup(mscsb, src)
    frames(m, 3, st=0xB1)
    check('parabeetle: KO frames with no cooldown (none can be out: it lives 270 frames, the cooldown 450): nothing '
          'asked of the ArticleModule', [x for x in g.log if x[0] == 'article'], [])
    m, g = pb_his_setup(mscsb, src)
    m.setg('gk_pb_cd', 200)
    m('gk_reset')
    check('parabeetle: a training reset / restart (gk_reset): removed, cooldown 0',
          ([x for x in g.log if x[0] == 'article' and x[2] == 10], m.g('gk_pb_cd')), ([('article', 0x2712, 10)], 0))
    # ---- the ride heartbeat (bit 8 of his VAR_30, his own beetle's)
    m, g = pb_his_setup(mscsb, src)
    g.vars[0x0F00031E] = 8.0 + 1.0 + 256.0
    m('gk_pb_heartbeat')
    r1 = (m.g('gk_pb_ride'), g.vars.get(0x0F00031E))
    m('gk_pb_heartbeat')
    r2 = m.g('gk_pb_ride')
    m('gk_pb_heartbeat')
    check('parabeetle heartbeat: bit 8 in his VAR_30 (his own beetle carries him): taken out (the other bits kept), 2 frames '
          'of ride; then 1, 0', (r1, r2, m.g('gk_pb_ride')), ((2, 257.0), 1, 0))
    # ---- the clones ride theirs: while he stands on his beetle (situation ground, the heartbeat) they copy his rise
    def start(ride):
        m = fresh_nodelay(mscsb, src)
        g = m.game
        g.x, g.y = 0.0, 10.0
        m.setg('gk_lw_charge', 300)
        m('gk_lw_press')
        frames(m, 6)
        g.floors = [(-1000.0, 1000.0, -60.0)]             # the stage far below: the beetles aren't stage floors here
        g.situation = 0
        m.vm.g[18] = 0
        ys = []
        for k in range(6):
            g.y = round(10.0 + 0.4 * (k + 1), 3)
            g.press = set()
            g.vars[0x0F00031E] = float((m.g('gk_alive') & g.beat) | (8 if ride else 0))
            m.vm.g[4] = 0
            m('gekkouga_frame')
            ys.append((m.gf('gk_ly'), m.gf('gk_ry')))
        return ys
    ys = start(True)
    check('parabeetle clones ride: he stands on his rising beetle (0.4 a frame; ground, its heartbeat): the clones copy his '
          'vertical movement (on theirs, made under them, rising as his): 10.4 ... 12.4',
          ys[1:], [(round(10.0 + 0.4 * (k + 1), 3),) * 2 for k in range(1, 6)])
    ys0 = start(False)
    check('parabeetle clones ride: the same without the heartbeat (on a floor the clones can\'t see): they fall with their '
          'gravity (the line test\'s floors; theirs are the beetles\' lines in game)', ys0[-1][0] < 10.0, True)



def parabeetle_v2_tests(mscsb, src, out):
    """parabeetle v2 (README "Parabeetle v2"): the stick's direction (neutral / left / right / up-left / up-right / down /
    down-right), the snap (in the air and on the ground; dropped by an action; the clones copy him meanwhile), the slot
    map (no two users of one New_Var slot or TIMER), the clones' costumes (c00 - c07 their own)"""
    import math
    REQ = CC.GK_VAR_PBREQ
    SNAP = 0x0F00032C
    # ---- the direction: the stance's own unit vector (0x1000006 / 7, as vanilla's jet reads it) -> the request's code
    cases = (('neutral (no stick: vanilla (0, 1))', (0.0, 1.0), 1.0, +1.0), ('straight up', (0.0, 1.0), -1.0, -1.0),
             ('right', (1.0, 0.0), -1.0, +(1 + 8 * 90)), ('left', (-1.0, 0.0), 1.0, -(1 + 8 * 90)),
             ('up-right', (0.7071, 0.7071), 1.0, +(1 + 8 * 45)), ('up-left', (-0.7071, 0.7071), 1.0, -(1 + 8 * 45)),
             ('down (clamped: neutral)', (0.0, -1.0), 1.0, +1.0), ('down-right (clamped: right)', (0.7071, -0.7071), 1.0,
                                                                     +(1 + 8 * 90)),
             ('down-left, facing right (clamped: left)', (-0.7071, -0.7071), 1.0, -(1 + 8 * 90)),
             ('a little right of up (0.1: straight up, toward his facing left)', (0.1, 0.995), -1.0, -1.0),
             ('up-right 22 degrees', (0.3746, 0.9272), 1.0, +(1 + 8 * 22)))
    got = {}
    for nm, (dx, dy), lr, _w in cases:
        m, g = pb_his_setup(mscsb, src, lr=lr)
        g.vars[0x1000006], g.vars[0x1000007] = dx, dy
        m('gk_pb_end')
        got[nm] = g.vars.get(REQ)
    check('parabeetle v2 direction: the request\'s code = its travel side x (1 + 8 x the stick\'s angle from straight up): '
          'neutral / up toward his facing; left / right 90; the up-diagonals 45; down clamped to level (straight down '
          'neutral, a down-diagonal its side)', got, {nm: float(w) for nm, _d, _l, w in cases})
    for nm, want in (('right', 0.17), ('up-right', 0.17), ('up-right 22 degrees', 0.05 + 0.12 * 22 / 45), ('neutral', 0.05)):
        k = next(c for c in got if c.startswith(nm))
        q = int(abs(got[k])) // 8
        check('parabeetle v2 direction: %s -> angle %d -> sideways %.4f a frame (pb_ref_h)' % (nm, q, pb_ref_h(q)),
              round(pb_ref_h(q), 4), round(want, 4))
    # ---- the clones' beetles: the same direction (they copy his up special)
    m, g = pb_his_setup(mscsb, src, lr=1.0)
    g.vars[0x1000006], g.vars[0x1000007] = -1.0, 0.0
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 3)
    m('gk_pb_end')
    seq = [g.vars.get(REQ)]
    for _ in range(2):
        g.vars[REQ] = 0.0
        m('gk_pb_tick')
        seq.append(g.vars.get(REQ))
    check('parabeetle v2 direction: his clones\' beetles go his way too (left held: -721 his, -722 / -723 theirs)', seq,
          [-721.0, -722.0, -723.0])
    m, g = pb_his_setup(mscsb, src, situation=0, lr=1.0)
    g.vars[0x1000006], g.vars[0x1000007] = 0.7071, 0.7071
    m.setg('gk_ability', 300)
    m.setg('gk_alive', 2)
    m('gk_pb_end')
    g.vars[REQ] = 0.0
    m('gk_pb_tick')
    check('parabeetle v2 direction: on the ground, up-right: the right clone\'s +(3 + 4 + 8 x 45) = +367', g.vars.get(REQ),
          367.0)
    # ---- the snap
    m, g = pb_his_setup(mscsb, src)
    m('gk_pb_end')
    m.vm.g[4] = 0xE
    g.log = []
    m('gk_pb_tick')
    held = [x for x in g.log if x[0] == 'kinetic']
    g.vars[0x0F00031E] = 16.0 + 1.0                       # his beetle: its line made under his feet (+ a clone's bit)
    g.status_req = []
    g.log = []
    m('gk_pb_heartbeat')
    check('parabeetle v2 snap (in the air): held still each frame in Fall while pending (gravity energy 0); his beetle\'s '
          'report (bit 16 of VAR_30): taken out (the clone\'s bit kept), on it by the game\'s own ground switch (func_101: '
          'KineticModule(0, 6), situation ground, GroundModule(0x2710, 1): the line under his feet), Wait (0: '
          'actionable); the snap done (TIMER_12 0), his clones ride (gk_pb_ride 2)',
          (held, g.vars.get(0x0F00031E), [x for x in g.log if x[0] in ('kinetic', 'situation', 'ground')], g.status_req,
           g.vars.get(SNAP), m.g('gk_pb_ride')),
          ([('kinetic', 0x11, 1, 0.0), ('kinetic', 0xB, 1)], 1.0,
           [('kinetic', 0, 6), ('situation', 0), ('ground', 0x2710, 1)], [(0, 0)], 0.0, 2))
    m, g = pb_his_setup(mscsb, src, situation=0)
    y0 = g.y
    m('gk_pb_end')
    m.vm.g[4] = 0xE
    m.vm.g[18] = 2
    g.vars[0x0F00031E] = 16.0
    g.status_req = []
    g.log = []
    m('gk_pb_heartbeat')
    check('parabeetle v2 snap (on the ground): put 9.5 up onto its line, then the same landing on it (Wait, ground)',
          (round(g.y - y0, 3), [x for x in g.log if x[0] in ('situation', 'ground')], g.status_req),
          (9.5, [('situation', 0), ('ground', 0x2710, 1)], [(0, 0)]))
    m, g = pb_his_setup(mscsb, src)
    m('gk_pb_end')
    m.vm.g[4] = 0x19                                      # he jumped before its line was made
    m('gk_pb_tick')
    g.vars[0x0F00031E] = 16.0
    g.status_req = []
    m('gk_pb_heartbeat')
    check('parabeetle v2 snap: an action first (a jump: not Fall): the snap dropped (TIMER_12 0); the late report changes '
          'nothing (no Wait)', (g.vars.get(SNAP), g.status_req), (0.0, []))
    m, g = pb_his_setup(mscsb, src)
    m.setgf('gk_pb_cd', 0)
    m('gk_pb_end')
    m('gk_pb_clear')
    check('parabeetle v2 snap: a KO / reset (gk_pb_clear): the snap dropped', g.vars.get(SNAP), 0.0)
    # the clones keep still with him while the snap is pending (they copy his vertical movement: his is 0)
    m = fresh_nodelay(mscsb, src)
    g = m.game
    g.x, g.y = 0.0, 40.0
    m.setg('gk_lw_charge', 300)
    m('gk_lw_press')
    frames(m, 6)
    g.floors = [(-1000.0, 1000.0, -60.0)]
    g.situation = 2
    m.vm.g[18] = 2
    g.vars[SNAP] = 10.0
    ys = []
    for k in range(4):
        g.press = set()
        g.vars[0x0F00031E] = float(m.g('gk_alive') & g.beat)
        m.vm.g[4] = 0xE
        m('gekkouga_frame')
        ys.append((m.gf('gk_ly'), m.gf('gk_ry')))
    check('parabeetle v2 snap: the clones in the air while his snap is pending copy his (still) height: they stay where '
          'they are, over their beetles (%s every frame; they would fall on their own)' % (ys[0],), ys[1:], [ys[0]] * 3)
    # ---- the slot map: no two features on one New_Var slot / TIMER (his MSC and the executable)
    c = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'clones.c')).read()
    code = re.sub(r'//[^\n]*', '', c)
    users = {}

    def use(slot, who):
        users.setdefault(slot, set()).add(who)
    funcs = [(mm.start(), mm.group(1)) for mm in re.finditer(r'^(?:int|void|float) (\w+)\(', code, re.M)]

    def fn_at(pos):
        return max((f for f in funcs if f[0] <= pos), default=(0, '?'))[1]
    for mm in re.finditer(r'gk_s?vi\((0x[0-9a-f]+|\d+)[,)]', code):
        use(int(mm.group(1), 0), 'vi:' + fn_at(mm.start()))
    for mm in re.finditer(r'gk_b(?:s|v|vi|si)\(([^,()]+), (0x[0-9a-f]+|\d+)', code):
        b, k = mm.group(1).strip(), int(mm.group(2), 0)
        for bb in ([int(b, 0)] if re.match(r'^(0x[0-9a-f]+|\d+)$', b) else [1, 2]):
            use(16 * bb + k, 'body%d' % bb)
    for mm in re.finditer(r'gk_dg(?:_set)?\(', code):
        use(48, 'diag flags')
    for mm in re.finditer(r'0x0f0003([89ab][0-9a-f])', code):
        use(int(mm.group(1), 16) - 0x80, 'id:' + fn_at(mm.start()))
    for mm in re.finditer(r'0x0f00032([0-9a-f])', code):
        use(('TIMER', int(mm.group(1), 16)), fn_at(mm.start()))
    for i in range(4):
        use(CC.ICE3_VAR - 0x0F000380 + i, 'exe: the ice request')
    use(('TIMER', CC.ICE3_SND_VAR - 0x0F000320), 'exe: the ice sound play')
    use(('TIMER', CC.ICE3_SND_VAR + 1 - 0x0F000320), 'exe: the ice sound stop')
    use(('TIMER', CC.CC_VAR - 0x0F000320), 'exe: the clone\'s costume')
    groups = {'ice': ('gk_ib_tick', 'gk_reset', 'gk_ice', 'gk_is_tick', 'exe: the ice'), 'body': ('body',),
              'snap': ('gk_pb_', 'gk_physics'), 'clone costume': ('gk_spawn', 'exe: the clone'), 'diag flags': ('diag flags', 'gk_dg')}

    def group(who):
        w = who.split(':', 1)[-1] if who.startswith(('vi:', 'id:')) else who
        for gname, pre in groups.items():
            if any(w.startswith(p_) for p_ in pre):
                return gname
        return 'own:' + w
    def clashes(us):
        out_ = {}
        for slot, who in us.items():
            gs = {group(w) for w in who}
            if len(gs) > 1 and gs & {'body', 'ice', 'snap', 'diag flags', 'clone costume'}:
                out_[slot] = sorted(who)
        return out_
    clash = clashes(users)
    v1 = {k: set(v) for k, v in users.items()}
    for i in range(4):
        v1.setdefault(CC.ICE_VAR - 0x0F000380 + i, set()).add('exe: the ice request (v1)')
    for i in range(2):
        v1.setdefault(CC.ICE_SND_VAR - 0x0F000380 + i, set()).add('exe: the ice sound (v1)')
    check('parabeetle v2 slot map: the check finds v1\'s clash (the ice request / sound at 48 - 53 on his body\'s 49 - 56; '
          '48 now the diag flags\')', sorted(k for k in clashes(v1) if isinstance(k, int)), [48, 49, 50, 51, 52, 53])
    check('parabeetle v2 slot map: no New_Var slot / TIMER used by two features (his body\'s 49 - 56, the clones\' 16 - 47 '
          'but k 7, the ice request 60 - 63 (the executable\'s ICE3_VAR), its sound TIMER_13 / 14, the clone\'s costume '
          'TIMER_15, the snap TIMER_12, the diag flags 48); v1\'s clash (the ice request in 48 - 53 on body 3\'s 49 - 56) '
          'gone', clash, {})
    check('parabeetle v2 slot map: the executable\'s request / sound slots (ICE3_VAR 0x%08X, ICE3_SND_VAR 0x%08X) are the '
          'release\'s, his MSC reads them' % (CC.ICE3_VAR, CC.ICE3_SND_VAR),
          (CC.ice_vars(CC.RELEASE), '0x%08x' % CC.ICE3_VAR in c, '0x%08x' % CC.ICE3_SND_VAR in c,
           '0x%08x' % (CC.ICE3_SND_VAR + 1) in c, '0x%08x' % CC.CC_VAR in c, '0x0f0003b0' in c, '0x0f0003b4' in c),
          ((CC.ICE3_VAR, CC.ICE3_SND_VAR), True, True, True, True, False, False))
    nv = sorted(k for k in users if isinstance(k, int))
    check('parabeetle v2 slot map: every New_Var slot in 0 - 63 (%d used)' % len(nv), (nv[0] >= 0, nv[-1] <= 63), (True, True))
    # ---- the clones' costumes: model/clone/c00 - c07 each his body's own (the game picks the owner's: the exe's ccol)
    import nut
    md = os.path.join(out, 'fighter', 'gekkouga', 'model', 'clone')
    ids = {}
    for k in range(8):
        _d, ts = nut.load(os.path.join(md, 'c%02d' % k, 'model.nut'))
        ids[k] = sorted({t.tex_id & 0xFFFFFC00 for t in ts})
    check('parabeetle v2 costumes: the clone\'s model/clone/c00 - c07 each carry their own costume\'s textures (0x4030 0000 + '
          '0x400 x costume: his body\'s c0X ids), so the owner\'s costume picked by the game shows', ids,
          {k: [0x40300000 + 0x400 * k] for k in range(8)})


PB_SRC_DIR = None


def pb_make(mscsb, src, code=1.0, slot=3, his=(40.0, 50.0), shared=None, line_made=True, loop=False):
    """parabeetle v1 / v2: its MSC (parabeetle.mscsb) on a stub game: motion kinds / frames (v2: the motion module plays a
    motion once and holds its last frame, as the game does: loop=False), facing, removal, cos / sin; its owner in `slot`
    at `his`; VAR_6 1 (the executable made its line) unless line_made is False"""
    import math
    m = MSC(mscsb, src)
    g = m.game
    g.x, g.y = 0.0, 0.0
    g.kind_at = 0
    g.restarts = 0
    g.loop = loop

    def sysf(sid, a, old=g.sys):
        if sid == 0x12 and a[0] == 0x1:
            if a[1] == g.motion and g.kind_at > 0:
                g.restarts += 1
            g.log.append(('motion', a[1]))
            g.motion, g.kind_at = a[1], 0
            g.frame = 0.0
            return 0
        if sid == 0x14 and a[0] == 0:
            g.log.append(('lr', fv(a[1])))
            g.lr = fv(a[1])
            return 0
        if sid == 0x21 and a[0] == 0x9:
            g.log.append(('remove',))
            return 0
        if sid == 0xA and a[0] in (0x4, 0x5):
            x = i2f(a[1])
            return f2i(math.cos(x) if a[0] == 0x4 else math.sin(x))
        return old(sid, a)
    g.sys = sysf
    if code is not None:
        g.vars[0x0F000300] = float(slot)
        g.vars[0x0F000301] = float(code)
    if line_made:
        g.vars[0x0F000306] = 1.0
    g.vars[0x0F000020 + 4 * (slot - 1)] = his[0]
    g.vars[0x0F000021 + 4 * (slot - 1)] = his[1]
    g.vars[0x0F0000A0 + 8 * (slot + 2) + 5] = float(CC.GK_KIND)
    for k, v in (shared or {}).items():
        g.vars[0x0F000340 + 8 * (slot - 1) + k] = v
    return m, g


PB_LEN = {0: 80, 1: 80, 2: 7}


def pb_run(m, n=1):
    """n frames of the beetle: its MSC's frame, then its motion one frame on (held on its last frame: no loop of its own)"""
    g = m.game
    for _ in range(n):
        m('pb_frame')
        g.kind_at += 1
        ln = PB_LEN.get(g.motion, 80)
        g.frame = float(g.kind_at % ln if g.loop else min(g.kind_at, ln - 1))


def pb_ref_curve(t):
    """(Python reference) parabeetle v2's height over its start at flight frame t"""
    import math
    d, df, v, e = 6.0, 16, 0.7, 20
    if t <= df:
        return -d * (1 - math.cos(math.pi * t / df)) / 2
    u = t - df
    return -d + (v * u * u / (2 * e) if u <= e else v * e / 2 + v * (u - e))


def pb_ref_h(q):
    """(Python reference) parabeetle v2's sideways speed for the stick's angle q from straight up"""
    return 0.17 if q >= 45 else 0.05 + 0.12 * q / 45.0


def parabeetle_tests(mscsb, src):
    """parabeetle v1 / v2: its MSC (parabeetle.mscsb): the claim's start (his / a clone's place), v2's hold at its rider's
    feet (the snap) and the line's report, its path (the swoop, the rise; sideways by the stick), its bob, the riders
    (fighters, his clones) and the motions, the heartbeat, the leaving, the removals"""
    import gekkouga_clone_cave as C
    make = lambda *a_, **k_: pb_make(mscsb, src, *a_, **k_)   # noqa: E731
    run = pb_run

    def line(m):
        return round(m.game.y + fv(m('pb_top')), 3)
    m, g = make(code=None)
    run(m, 30)
    check('parabeetle: nobody claimed it: it waits hidden (VisibilityModule 0), nothing else ...',
          sorted(set(x for x in g.log)), [('visible', 0)])
    run(m, 1)
    check('parabeetle: ... and after 30 frames removes itself', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    B0 = 0.007 + 0.7598 - 0.0388 + 0.1015              # its bob at the wait motion's frame 0 (pb_bob's fit)
    m, g = make(line_made=False)
    run(m)
    check('parabeetle constants: line 10.6 over its place (PB_TOP), half length 10 (PB_HALF: 20 wide), the executable\'s',
          (fv(m('pb_top')), fv(m('pb_half'))), (C.PB_TOP, C.PB_HALF))
    check('parabeetle v2 start (code +1: his, neutral toward his facing, right; him at (40, 50) in the air): its line at his '
          'feet exactly (50: the snap; v1 0.3 under), at his X, held (no step); the wait motion (0), facing right, shown; '
          'its phase 1 (VAR_5: the executable makes its line); an arrival puff',
          (line(m), round(g.x, 3), m.g('pb_t'), [x for x in g.log if x[0] in ('lr', 'motion', 'visible')],
           g.vars.get(0x0F000305), [x[:3] for x in g.log if x[0] == 'effect']),
          (50.0, 40.0, 0, [('motion', 0), ('lr', 1.0), ('visible', 1)], 1.0, [('effect', 0x3, 0x1000021)]))
    # ---- v2: the hold (the snap): at its rider's feet until its line is made, the line reported, then it flies
    BEAT = 0x0F000340 + 8 * 2 + 6                        # his VAR_30 (slot 3)
    trk = []
    for k in range(3):
        g.vars[0x0F000028], g.vars[0x0F000029] = 40.0 + 0.5 * k, 50.0 - 0.2 * k   # (he drifts / sinks a little)
        run(m)
        trk.append((round(g.x, 2), line(m), m.g('pb_t')))
    check('parabeetle v2 hold: its line not made yet (VAR_6 0): it stays under his feet (its line at them, following him), '
          'not flying, his VAR_30 untouched', (trk, g.vars.get(BEAT, 0.0)),
          ([(40.0, 50.0, 0), (40.5, 49.8, 0), (41.0, 49.6, 0)], 0.0))
    g.vars[0x0F000306] = 1.0                              # the executable: its line made
    g.vars[BEAT] = 1.0                                   # (a clone's heartbeat bit there)
    rep = []
    for k in range(4):
        run(m)
        rep.append((m.g('pb_t'), g.vars.get(BEAT)))
        g.vars[BEAT] = 1.0
    check('parabeetle v2 hold: its line made: bit 16 in his VAR_30 each frame until it flies (the others kept: 17; he lands '
          'on it: clones.c gk_pb_heartbeat), flying from the 3rd frame (2 after the first report); then him on it: bit 8 '
          '(the ride heartbeat: 9)', rep, [(0, 17.0), (0, 17.0), (1, 17.0), (2, 9.0)])
    m, g = make(line_made=False)
    run(m, 12)
    t12 = m.g('pb_t')
    run(m)
    check('parabeetle v2 hold: its line never made: held 12 frames at most, then it flies anyway', (t12, m.g('pb_t')), (0, 1))
    m, g = make(code=2.0, shared={0: -14.0, 1: 30.0, 2: 14.0, 3: 31.0, 6: 0.0})
    run(m, 2)
    check('parabeetle v2 hold: a clone\'s beetle (code +2: the left clone\'s, his VAR_24 / 25 (-14, 30)): its line at that '
          'clone\'s feet; his VAR_30 not touched (only his own beetle lands him)',
          (round(m.gf('pb_x0'), 2), line(m), m.g('pb_which'), g.vars.get(BEAT, 0.0)), (-14.0, 30.0, 2, 0.0))
    m, g = make(code=-7.0, shared={0: -14.0, 1: 30.0, 2: 14.0, 3: 31.0})
    run(m)
    check('parabeetle v2 start (code -7: the right clone\'s, on the ground, its travel side left): at (14, 31): its line at '
          'its feet (it was lifted with him), facing left', (round(m.gf('pb_x0'), 2), line(m), m.g('pb_which'),
                                                             m.g('pb_ground'), [x for x in g.log if x[0] == 'lr']),
          (14.0, 31.0, 3, 1, [('lr', -1.0)]))
    # ---- the path (v2): mostly up, sideways by the stick
    paths = {}
    for nm, code, q, side in (('neutral (toward his facing, right)', 1.0, 0, 1), ('right', 1.0 + 8 * 90, 90, 1),
                              ('up-right (45)', 1.0 + 8 * 45, 45, 1), ('up-left (45)', -(1.0 + 8 * 45), 45, -1),
                              ('left', -(1.0 + 8 * 90), 90, -1), ('up-right (22)', 1.0 + 8 * 22, 22, 1)):
        m, g = make(code=code)
        run(m, 2)                                         # (held: its report)
        g.vars[0x0F000029] = 500.0                        # (he jumps away: nobody on it)
        st = []
        for t in range(1, 241):
            run(m)
            st.append((m.g('pb_t'), m.gf('pb_x'), m.gf('pb_y'), g.motion, g.vars.get(0x0F000305)))
        x0, y0 = m.gf('pb_x0'), m.gf('pb_y0')
        xs = [round(p[1] - x0, 3) for p in st[:239]]
        ys = [round(p[2] - y0, 3) for p in st[:239]]
        h = side * pb_ref_h(q)
        ex = max(abs(xs[t - 1] - h * t) for t in range(1, 240))
        ey = max(abs(ys[t - 1] - pb_ref_curve(t)) for t in range(1, 240))
        paths[nm] = (xs, ys, st, ex, ey, h)
    for nm, (xs, ys, st, ex, ey, h) in paths.items():
        check('parabeetle v2 path, %s: sideways %.4f a frame (%.1f by frame 239), the swoop then the rise (pb_curve: max '
              'errors x %.4f, y %.4f)' % (nm, h, xs[-1], ex, ey), (ex < 0.01, ey < 0.01), (True, True))
    xs, ys, st, ex, ey, h = paths['right']
    rise = ys[-1]
    check('parabeetle v2 path: the swoop down 6 over 16 frames (lowest -6 at 16), then up to 0.7 a frame over 20, steady: '
          '+%.1f at frame 239 (v1: +74)' % rise, (round(min(ys), 3), ys.index(min(ys)) + 1, round(rise, 1)),
          (-6.0, 16, round(-6 + 0.7 * 10 + 0.7 * (223 - 20), 1)))
    ratios = {nm: round(p[1][-1] / max(abs(p[0][-1]), 1e-6), 2) for nm, p in paths.items()}
    check('parabeetle v2 path: far more vertical than horizontal: the rise / the sideways travel over its life: %s (a side '
          'or up-diagonal held: 3 - 4; neutral / straight up: mostly vertical, about 12; never under 3)' % ratios,
          (3.0 <= ratios['right'] <= 4.0, 3.0 <= ratios['up-left (45)'] <= 4.0, 3.0 <= ratios['left'] <= 4.0,
           ratios['neutral (toward his facing, right)'] >= 10.0, min(ratios.values()) >= 3.0), (True,) * 5)
    check('parabeetle v2 path: left held goes left, right right, neutral toward his facing (right), the up-diagonals their way',
          (paths['left'][0][-1] < -30, paths['right'][0][-1] > 30, 5 < paths['neutral (toward his facing, right)'][0][-1] < 15,
           paths['up-left (45)'][0][-1] < -30, paths['up-right (45)'][0][-1] > 30), (True,) * 5)
    check('parabeetle motions with nobody on it: wait (0) through the swoop, rise (1) once it rises (flight frame 17 on)',
          ([p[3] for p in st[:16]] == [0] * 16, [p[3] for p in st[16:239]] == [1] * 223), (True, True))
    check('parabeetle: flying 239 frames (phase 1), leaving at 240 (VAR_5 2: the executable removes its line)',
          ([p[4] for p in st[:239]] == [1.0] * 239, st[239][4]), (True, 2.0))
    m, g = make(code=-(1.0 + 8 * 90))
    run(m, 2)
    g.vars[0x0F000029] = 500.0
    run(m, 240)
    lx, ly = g.x, g.y
    run(m, 29)
    check('parabeetle leaving (left held): flies off its way and up (x %+.1f, y %+.1f in 29 frames), still there ...' % (
          g.x - lx, g.y - ly), (g.x - lx < -15, g.y - ly > 60, [x for x in g.log if x[0] == 'remove']), (True, True, []))
    run(m, 1)
    check('parabeetle leaving: ... removed 30 frames after', [x for x in g.log if x[0] == 'remove'], [('remove',)])
    # ---- the wings (v2: the motion module holds a motion's last frame; its MSC restarts wait / rise there)
    wing = {}
    for nm, ride_at in (('nobody on it', None), ('ridden from flight frame 5', 5)):
        m, g = make()
        frames_, kinds = [], []
        n = 0
        while not [x for x in g.log if x[0] == 'remove'] and n < 400:
            if ride_at is not None:
                on = m.g('pb_t') >= ride_at
                g.vars[0x0F000028], g.vars[0x0F000029] = (m.gf('pb_x'), line(m)) if on else (500.0, 500.0)
                if m.g('pb_t') >= 239:
                    g.vars[0x0F000029] = 500.0
            run(m)
            n += 1
            frames_.append(g.frame)
            kinds.append(g.motion)
        stuck = [i for i in range(1, len(frames_)) if frames_[i] == frames_[i - 1] and kinds[i] == kinds[i - 1]]
        wing[nm] = (n, stuck, g.restarts, m.g('pb_loops'), sorted(set(kinds)))
    for nm, (n, stuck, rs, loops, kinds) in wing.items():
        check('parabeetle v2 wings (%s): its motion moves on every one of its %d frames (hold, flight, leaving: never held '
              'on a frame; v1 held rise\'s last frame from 80 frames into the climb); wait / rise restarted at their end %d '
              'times (pb_loops %d); motions %s' % (nm, n, rs, loops, kinds), (stuck, n > 265, loops >= 2), ([], True, True))
    check('parabeetle v2 wings: ridden plays its 7 frames once (the press), then rise loops', wing['ridden from flight frame 5'][4],
          [0, 1, 2])
    # ---- the bob: the article bobs by its root's motion, so its line stays on the shell
    held = PB_HELD or {}
    if held:
        errs = []
        for kind, name in enumerate(C.PB_MOTIONS):
            h = held[name]
            m2, g2 = make()
            run(m2)
            m2.setg('pb_kind', kind)
            for f in range(len(h) if kind != 2 else 7):
                g2.frame = float(f)
                errs.append((kind, f, abs(fv(m2('pb_bob')) - h[f])))
        worst = max(errs, key=lambda e: e[2])
        check('parabeetle bob: its MSC\'s pb_bob = the root Y taken out of each motion (tools/chr0_to_omo.py hold) on every '
              'frame of wait (80), rise (80), ridden (7): worst %.3f (motion %d frame %d)' % (worst[2], worst[0], worst[1]),
              worst[2] <= 0.1, True)
    # ---- riders
    m, g = make()
    run(m, 3)
    g.vars[0x0F000029] = 500.0
    run(m, 2)
    px = m.gf('pb_x')
    top = line(m)
    slot1 = (0x0F000020, 0x0F000021, 0x0F0000A0 + 8 * 3 + 5, 0x0F0000A0 + 8 * 3 + 2)
    g.vars[slot1[2]] = 0x10                               # slot 1: a fighter (kind 0x10)
    g.vars[slot1[0]], g.vars[slot1[1]] = px + 5.0, top + 30.0
    g.log = []
    run(m)
    check('parabeetle riders: a fighter 30 over it: nothing on it (wait)', (m.g('pb_rode'), g.motion), (0, 0))
    ms = []
    for k in range(10):
        g.vars[slot1[0]], g.vars[slot1[1]] = m.gf('pb_x') + 5.0, line(m)
        run(m)
        ms.append(g.motion)
    check('parabeetle riders: a fighter lands on it (its feet on the line, 5 from its middle): on it from its 2nd frame '
          'there (one passing through the line\'s band is in it a frame at most), ridden (2: the user\'s ridden.chr0, the '
          'press) for its frames 0 - 5 (v2: its 7th, the rest pose, is rise\'s first: no frame held), then rise (1) while it '
          'carries (VAR_8 1)', (ms, g.vars.get(0x0F000308)), ([0] + [2] * 6 + [1] * 3, 1.0))
    m3, g3 = make()
    run(m3, 3)
    g3.vars[0x0F000029] = 500.0
    run(m3, 3)
    g3.vars[slot1[2]] = 0x10
    hits = []
    for k in range(4):
        g3.vars[slot1[0]], g3.vars[slot1[1]] = m3.gf('pb_x'), line(m3) + 1.2 - 1.8 * k   # falling 1.8 a frame through it
        run(m3)
        hits.append(m3.g('pb_rode'))
    check('parabeetle riders: one falling through its line\'s band (1.8 a frame) isn\'t on it', hits, [0, 0, 0, 0])
    check('parabeetle riders: not its owner: no ride heartbeat (bit 8) in his VAR_30 (bit 16: its line\'s report while held)',
          int(g.vars.get(0x0F000356, 0.0)) & 8, 0)
    g.vars[slot1[1]] = line(m) + 40.0
    ms, ts = [], []
    for k in range(4):
        run(m)
        ms.append(g.motion)
        ts.append(m.g('pb_t'))
    check('parabeetle riders: it jumps off: ridden for 2 more frames (a frame or two off the line), then wait in its swoop / '
          'rise after it', ms, [1, 1] + [0 if t <= 16 else 1 for t in ts[2:]])
    g.vars[slot1[0]], g.vars[slot1[1]] = m.gf('pb_x') + 13.5, line(m)
    run(m, 2)
    check('parabeetle riders: past its end (its line +- 10, + 1.5): not on it', m.g('pb_rode'), 0)
    for k in range(2):
        g.vars[slot1[0]], g.vars[slot1[1]] = m.gf('pb_x') - 11.3, line(m) - 0.8   # (11.25 from it after its 0.05 step)
        run(m)
    check('parabeetle riders: 11.25 from its middle, 0.8 under the line: on it (the line\'s ends + 1.5, 1 under)', m.g('pb_rode') > 0,
          True)
    g.vars[slot1[1]] = 500.0
    run(m, 4)
    g.vars[slot1[2]] = -1.0
    g.vars[slot1[0]], g.vars[slot1[1]] = m.gf('pb_x'), line(m)
    run(m)
    check('parabeetle riders: an empty slot (kind -1) at its place: nobody', m.g('pb_rode'), 0)
    g.vars[0x0F000028], g.vars[0x0F000029] = m.gf('pb_x') - 2.0, line(m) + 0.5
    run(m)
    g.vars[0x0F000028], g.vars[0x0F000029] = m.gf('pb_x') - 2.0, line(m) + 0.5
    g.vars[0x0F000356] = 1.0                              # the clones' heartbeat bits already there
    run(m)
    check('parabeetle riders: its owner (slot 3) on it: bit 8 added to his VAR_30 (the clones\' bit 1 kept: 9), ridden',
          (g.vars.get(0x0F000356), g.motion), (9.0, 2))
    m, g = make(shared={0: 0.0, 1: 0.0, 7: 4747001.0})
    run(m, 3)
    g.vars[0x0F000029] = 500.0
    run(m, 2)
    for k in range(2):
        g.vars[0x0F000350], g.vars[0x0F000351] = m.gf('pb_x') + 1.0, line(m)
        run(m)
    check('parabeetle riders: his clone (alive: his VAR_31 4747000 + 1) on it: ridden', (m.g('pb_rode') > 0, g.motion),
          (True, 2))
    g.vars[0x0F000357] = 4747002.0
    run(m, 4)
    check('parabeetle riders: ... that clone gone (flags 2: only the other one alive): not ridden', m.g('pb_rode'), 0)
    # ---- its owner KO'd; hitlag
    m, g = make()
    run(m, 10)
    g.vars[0x0F0000A0 + 8 * 5 + 2] = float(0xB1)
    run(m)
    check('parabeetle: its owner KO\'d (his status Dead 0xB1): its line removed (VAR_5 2) and it removes itself',
          (g.vars.get(0x0F000305), [x for x in g.log if x[0] == 'remove']), (2.0, [('remove',)]))
    m, g = make()
    run(m, 10)
    t0, x0_ = m.g('pb_t'), g.x
    g.hitlag = 3
    run(m, 3)
    check('parabeetle: in hitlag (StopModule 1) it holds (no step)', (m.g('pb_t'), g.x), (t0, x0_))


def parabeetle_data_tests(out):
    """parabeetle v1: its files (the converters' output) against the user's source (when --pb-src is given) and the
    executable's constants"""
    import math
    import numpy as np
    import lvd
    import nud
    import nut
    import omo
    import mdl0_to_nud as M
    import chr0_to_omo as CH
    import s3ds_enemy as se
    import gekkouga_clone_cave as C
    F = os.path.join(out, 'fighter', 'gekkouga')
    md = os.path.join(F, 'model', 'parabeetle', 'c00')
    files = sorted(os.listdir(md))
    check('parabeetle model: model.nud / .nut / .vbn / .jtb / .sb / .nhb / .xmb / .flp and parabeetle.lvd',
          files, sorted(['model.nud', 'model.nut', 'model.vbn', 'model.jtb', 'model.sb', 'model.nhb', 'model.xmb',
                         'model.flp', 'parabeetle.lvd']))
    vb = omo.vbn_read(os.path.join(md, 'model.vbn'))
    check('parabeetle skeleton: TransN (the added root) + the source\'s 6 bones in order, parents kept',
          [(n, p) for n, p, _h in vb], [('TransN', 0x0FFFFFFF), ('skl_root', 0), ('face', 1), ('wing_L_1', 1), ('wing_L_2', 3),
                                        ('wing_R_1', 1), ('wing_R_2', 5)])
    jt = open(os.path.join(md, 'model.jtb'), 'rb').read()
    check('parabeetle model.jtb: one table, joint i = bone i (7)', struct.unpack('>8H', jt), (7, 0, 1, 2, 3, 4, 5, 6))
    for f in se.DEFAULT_FILES:
        check('parabeetle %s: reference/enemy_model_defaults\' (without sb / nhb the bone getter crashes, without xmb black)'
              % f, open(os.path.join(md, f), 'rb').read() == open(os.path.join(se.DEFAULTS, f), 'rb').read(), True)
    ms = nud.read(os.path.join(md, 'model.nud'))
    dn, texs = nut.load(os.path.join(md, 'model.nut'))
    check('parabeetle NUD: 2 meshes (the shell 46 vertices / 80 triangles, the body 253 / 394: the source\'s 80 / 394 faces),'
          ' rigged, the fighter body shader 0x9A011063, culled back',
          [(x.name, sum(p.nv for p in x.polygons), sum(len(p.idx) // 3 for p in x.polygons), x.polygons[0].vert_size >> 4 != 0,
            hex(x.polygons[0].materials[0].flags), x.polygons[0].materials[0].cull) for x in ms],
          [('polygon0', 46, 80, True, '0x9a011063', 1029), ('polygon1', 253, 394, True, '0x9a011063', 1029)])
    tid = sorted(t.tex_id for t in texs)
    check('parabeetle NUT: 3 textures in his range (0x4030A000: the flat normal map, the baked shell, met_pata)',
          [hex(t) for t in tid], ['0x4030a000', '0x4030a001', '0x4030a002'])
    ims = {t.tex_id: nut.decode(dn, t) for t in texs}
    check('parabeetle NUT: the shell 32 x 32 (the env map\'s), met_pata 64 x 128', (ims[0x4030A001].shape[:2],
                                                                                   ims[0x4030A002].shape[:2]),
          ((32, 32), (128, 64)))
    pac = dict(omo.pac_read(os.path.join(F, 'motion', 'parabeetle', 'main.pac')))
    check('parabeetle main.pac: its 3 animations, the names the executable\'s motion info hashes (PB_MOTIONS)',
          sorted(pac), sorted(n + '.omo' for n in C.PB_MOTIONS))
    check('parabeetle OMOs: wait 80 frames, rise 80, ridden 7 (the CHR0s\' frame counts); 7 nodes each',
          [(omo.Omo(pac[n + '.omo']).frames, len(omo.Omo(pac[n + '.omo']).nodes)) for n in C.PB_MOTIONS],
          [(80, 7), (80, 7), (7, 7)])
    w = os.path.join(F, 'script', 'animcmd', 'weapon', 'parabeetle')
    mt = open(os.path.join(w, 'motion.mtable'), 'rb').read()
    check('parabeetle motion.mtable: ParabeetleWait / Rise / Ridden (motion kinds 0 / 1 / 2)',
          list(struct.unpack('>3I', mt)), [acmd.crc(n) for n in GB.PB_SCRIPTS])
    for f in ('game.bin', 'effect.bin', 'sound.bin'):
        a = acmd.ACMDFile.load(os.path.join(w, f))
        check('parabeetle %s: its 3 scripts empty (no hitbox: it isn\'t hurt and hurts nobody; no effect, no sound)' % f,
              sorted((h, [c.name for c in sc]) for h, sc in a.scripts.items()),
              sorted((acmd.crc(n), ['Script_End']) for n in GB.PB_SCRIPTS))
    lv = lvd.LVD(os.path.join(md, 'parabeetle.lvd'))
    c = lv.collisions[0]
    check('parabeetle.lvd: one collision, drop-through (flag 4: the ground maker makes its line passable, 0x2000), the '
          'hydrant\'s other flags; one floor line x -10 -> +10 at y 10.6 (= the executable\'s PB_VERTS: they ship '
          'together), normal up, no ledges',
          (len(lv.collisions), c.flags, [tuple(round(x, 3) for x in v) for v in c.verts], c.normals, c.cliffs),
          (1, [0, 1, 0, 1], [tuple(v) for v in C.PB_VERTS], [[0.0, 1.0]], []))
    msc = MSC(os.path.join(F, 'script', 'msc', 'parabeetle', 'parabeetle.mscsb'), GB.PARABEETLE_MSC)
    check('parabeetle MSC: its line height / half length = the executable\'s PB_TOP / PB_HALF',
          (fv(msc('pb_top')), fv(msc('pb_half'))), (C.PB_TOP, C.PB_HALF))
    if not PB_SRC_DIR:
        return
    src = os.path.join(PB_SRC_DIR, GB.PB_MDL0)
    model = M.parse(src)
    check('mdl0_to_nud: the source parsed: MDL0 v11, 6 bones, 2 objects (80 + 394 triangles = the headers\' face counts), 2 '
          'materials, the draw list',
          (model['version'], len(model['bones']), [len(o['tris']) for o in model['objects']],
           [o['nfaces'] for o in model['objects']], len(model['materials']), len(model['draw'])),
          (11, 6, [80, 394], [80, 394], 2, 2))
    check('mdl0_to_nud: each bone\'s SRT (Rz Ry Rx) gives its stored bind matrix (max error < 1e-3)',
          max(float(np.abs(b['world'][:3] - b['bind']).max()) for b in model['bones']) < 1e-3, True)
    S_ = C.PB_SCALE
    import nud_preview
    items, bones_, bw = nud_preview.load(md)
    worst = 0.0
    for i, b in enumerate(model['bones']):
        want_ = b['world'].copy()
        want_[:3, 3] *= S_
        worst = max(worst, float(np.abs(bw[i + 1][:3] - want_[:3]).max()))
    check('mdl0_to_nud: the VBN\'s bind pose = the source\'s (translations x %g; TransN identity): max error %.4f' % (S_, worst),
          worst < 2e-3, True)
    for oi, it in enumerate(items):
        ov = M.object_vertices(model, model['objects'][oi])
        a1 = np.unique(np.round(ov['pos'] * S_, 2), axis=0)
        a2 = np.unique(np.round(it['pos'], 2), axis=0)
        check('mdl0_to_nud: %s\'s vertices = the source\'s (world, x %g; welded corners: %d -> %d)' % (
              it['name'], S_, len(ov['pos']), len(it['pos'])),
              (len(a1), bool(np.allclose(a1, a2, atol=0.011)) if len(a1) == len(a2) else False), (len(a2), True))
    uv1 = model['arrays']['uv'][1][1]
    it = items[1]
    check('mdl0_to_nud: the body\'s UVs = the source\'s UV set 1 (range %s - %s, mirrored wrap: NUD 2)' % (
          np.round(uv1.min(0), 3).tolist(), np.round(uv1.max(0), 3).tolist()),
          (np.allclose(it['uv'].min(0), uv1.min(0), atol=2e-3), np.allclose(it['uv'].max(0), uv1.max(0), atol=2e-3),
           it['wrap']), (True, True, (2, 2)))
    it = items[0]
    nv = it['nrm'] @ M.VIEW_RIGHT.T
    want_uv = M.sphere_uv(nv)
    check('mdl0_to_nud: the shell\'s UVs are its sphere-map coordinates (GX EnvCamera: 0.5 + 0.5 nx, 0.5 - 0.5 ny of the '
          'normal seen from the side, facing right), in 0 - 1, clamped',
          (bool(np.allclose(it['uv'], want_uv, atol=2e-3)), float(it['uv'].min()) >= 0, float(it['uv'].max()) <= 1,
           it['wrap']), (True, True, True, (3, 3)))
    from PIL import Image
    red = np.asarray(Image.open(os.path.join(PB_SRC_DIR, 'met_pata_shell.png')).convert('RGBA'))[..., :3].reshape(-1, 3).mean(0)
    env = np.asarray(Image.open(os.path.join(PB_SRC_DIR, 'met_pata_shell_env.png')).convert('RGBA')).astype(float)
    mats = {x['name']: x for x in model['materials']}
    k = mats['mat_met_pata_shell']['regs']['C1'][3]
    want_t = np.clip(red[None, None, :] + k * env[..., :3], 0, 255)
    got_t = ims[0x4030A001][..., :3].astype(float)
    err = float(np.abs(want_t - got_t).mean())
    check('mdl0_to_nud: the shell\'s texture = its flat red (153, 28, 2) + %.3f x met_pata_shell_env (its TEV: C1 alpha '
          '175 / 255; GX2 BC1, mean error %.1f / 255)' % (k, err), err < 6.0, True)
    check('mdl0_to_nud: the source\'s materials are opaque (blend off, alpha compare always): no alpha (its PNGs are '
          'opaque too)', [(x['blend'] & 1, (x['alpha_compare'] >> 16) & 0x3F) for x in model['materials']],
          [(0, 0x3F), (0, 0x3F)])
    # the OMOs against the CHR0s, every frame of every bone
    worst = {}
    for name, ch in zip(C.PB_MOTIONS, GB.PB_CHR0):
        anim = CH.parse(os.path.join(PB_SRC_DIR, ch + '.chr0'))
        o = omo.Omo(pac[name + '.omo'])
        wr, wt = 0.0, 0.0
        for f in range(o.frames):
            for b in model['bones']:
                ab = anim['bones'].get(b['name'])
                sc, rot, tr = CH.local_at(ab, b, f) if ab else (b['scale'], b['rot'], b['pos'])
                tr = np.asarray(tr) * S_
                if b['name'] == GB.PB_ROOT:
                    tr = tr.copy()
                    tr[1] = 0.0
                pos, q, s_ = o.sample(se.bone_hash(b['name']), f)
                R1 = M.euler_xyz(rot)
                R2 = np.array(omo.qmat(q))[:3, :3]
                ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R1.T @ R2) - 1) / 2))))
                wr = max(wr, ang)
                wt = max(wt, float(np.abs(np.asarray(pos) - tr).max()))
        worst[name] = (round(wr, 2), round(wt, 3))
    check('chr0_to_omo: every frame / bone of each OMO = its CHR0 (Hermite / linear keys, x 1.25; the root\'s Y held 0): '
          'worst rotation / translation error %s' % worst,
          all(r <= 0.5 and t <= 0.02 for r, t in worst.values()), True)
    global PB_HELD
    PB_HELD = {}
    for name, ch in zip(C.PB_MOTIONS, GB.PB_CHR0):
        anim = CH.parse(os.path.join(PB_SRC_DIR, ch + '.chr0'))
        _b, _f, _l, held = CH.to_omo(anim, model, S_, None, {GB.PB_ROOT: 1})
        PB_HELD[name] = held[GB.PB_ROOT]


PB_HELD = None


def main():
    global FX_PKG, GAUGE_SRC, GAUGE_JPG
    FX_PKG = next((x[5:] for x in sys.argv[1:] if x.startswith('--fx=')), None)
    GAUGE_SRC = next((x[12:] for x in sys.argv[1:] if x.startswith('--gauge-src=')), None)
    GAUGE_JPG = next((x[12:] for x in sys.argv[1:] if x.startswith('--gauge-jpg=')), None)
    global GAUGE_VL
    GAUGE_VL = next((x[5:] for x in sys.argv[1:] if x.startswith('--vl=')), None)
    global ICE_CLIP, PB_SRC_DIR
    ICE_CLIP = next((x[11:] for x in sys.argv[1:] if x.startswith('--ice-clip=')), None)
    PB_SRC_DIR = next((x[9:] for x in sys.argv[1:] if x.startswith('--pb-src=')), None)
    a = [x for x in sys.argv[1:] if not x.startswith('--v') and not x.startswith('--fx=') and not x.startswith('--gauge-')
         and not x.startswith('--ice-clip=') and not x.startswith('--pb-src=')]
    earlier = [x[len('--v%s=' % k):] for k in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '91', '10', '11', '12', '13', 'b1',
                                               'b11', 'b12', 's1', '14', '15', 's12', 'b2', 'b21', 'b22', 'b23', 'ac', 's13', 'cf', 'ft', 's14', 's15', 's16', 'tc', 'bt', 's17', 'ak', 'ca', 'rg', 'cf3', 'ff', 'rg11', 'cm', 'tu', 'nr', 'st', 'id', 'ut', 'pb') for x in sys.argv[1:]
               if x.startswith('--v%s=' % k)]
    v1 = None
    out, pkg, user, base = a[0], a[1], a[2], a[3]
    base_diag = a[4] if len(a) > 4 else None
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    msc_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    physics_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    aerial_chain_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    tilt_chain_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    delay_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_delay_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    clone_fx_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC, out)
    ground_move_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out)
    if os.path.exists(os.path.join(msc, 'skeleton', 'skeleton.mscsb')):
        skeleton_side_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        skeleton_v16_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        skeleton_tests(os.path.join(msc, 'skeleton', 'skeleton.mscsb'), GB.SKELETON_MSC)
        skeleton_data_tests(out)
    if os.path.exists(os.path.join(msc, 'firetrail', 'firetrail.mscsb')):
        trail_side_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        firetrail_tests(os.path.join(msc, 'firetrail', 'firetrail.mscsb'), GB.TRAIL_MSC)
        trail_data_tests(out)
    script_tests(out, user)
    msc_ops_tests(out)
    if os.path.exists(os.path.join(msc, 'parabeetle', 'parabeetle.mscsb')):
        parabeetle_data_tests(out)
        parabeetle_side_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        parabeetle_tests(os.path.join(msc, 'parabeetle', 'parabeetle.mscsb'), GB.PARABEETLE_MSC)
    if len(earlier) >= 48:
        parabeetle_v2_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out)
    if len(earlier) >= 46:
        usmash_trail_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out,
                           user, ICE_CLIP)
        air_regroup_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    if len(earlier) >= 45:
        ice_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'),
                  os.path.join(msc, 'firetrail', 'firetrail.mscsb'), out, user)
    if len(earlier) >= 44:
        smash_tune_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out,
                         user)
    if len(earlier) >= 43:
        nair_fair_tests(out, user)
    if len(earlier) >= 42:
        tuning_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out, user,
                     os.path.join(msc, 'firetrail', 'firetrail.mscsb'))
    if len(earlier) >= 41:
        clone_moves_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'),
                          os.path.join(msc, 'clone', 'clone.mscsb'), out)
    if len(earlier) >= 40:
        invuln_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), out,
                     GAUGE_VL)
    if len(earlier) >= 38:
        clonefix_v3_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    if len(earlier) >= 36:
        clone_articles_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'),
                             os.path.join(msc, 'skeleton', 'skeleton.mscsb'), os.path.join(msc, 'shuriken', 'shuriken.mscsb'),
                             os.path.join(msc, 'clone', 'clone.mscsb'))
    if len(earlier) >= 35:
        aligned_kick_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        aligned_kick_more_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        split_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        bugfix_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
        clone_free_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
        kick_data_tests(out, user)
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
