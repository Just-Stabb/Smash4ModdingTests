#!/usr/bin/env python3
"""Greninja's clones / smash charges mod (fighters/gekkouga/README.md "Clones v1"): the tests.

  python3 tools/gekkouga_clones_test.py OUT PACKAGE.zip USER_ANIMCMD BASE.rpx [BASE_DIAG.rpx]

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
4. the package: every file, the exe (cross_f.rpx = exe_v46z_gk1 built from BASE, its diag), README, no fighter-named
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

    def sys(self, sid, a):
        if sid == 0x16:                                       # WorkModule
            op = a[0]
            if op == 0:
                self.vars[a[2]] = fv(a[1])
                return 0
            if op == 2:
                if a[2] == 0x0F000000:
                    self.x = round(self.x + fv(a[1]), 3)
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
        if sid == 0x30:                                       # StopModule(1): not in hitlag
            return 0
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
    check('frame 0: the left clone (article 6) made, VAR_30 = 1, its smoke at X - 14',
          (arts, g.vars.get(0x0F00031E), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006]),
          ([('article', 0x2710, 6)], 1.0, [36.0]))
    frames(m, 3)
    arts = [x for x in g.log if x[0] == 'article']
    check('frame 3: the right clone (article 7), VAR_30 = 2, its smoke at X + 14',
          (arts[-1], g.vars.get(0x0F00031E), [x[3] for x in g.log if x[0] == 'effect' and x[2] == 0x3300006][-1]),
          (('article', 0x2710, 7), 2.0, 64.0))
    check('flags: tag hidden + clones out (5)', g.vars.get(0x0F000314), 5.0)
    g.motion, g.frame, g.rate = 0x5F, 7.0, 1.0
    frames(m, 1)
    check('the channel: offsets -14 / 14, alive 3, motion 0x5F frame 7 rate 1, magic 4747',
          [g.vars.get(0x0F000318 + i) for i in range(8)], [-14.0, 14.0, 3.0, 95.0, 7.0, 1.0, 2.0, 4747.0])
    check('the capsules: shapes 1 (-14) and 2 (+14) on, 0 / 3 off', g.shapes, {0: 0, 1: 1, 2: 1, 3: 0})
    g.lr = -1.0
    frames(m, 1)
    check('facing left: the same clones are at z +14 / -14 (shapes 2 / 1)', g.shapes, {0: 0, 1: 1, 2: 1, 3: 0})
    g.lr = 1.0
    m.vm.g[4] = 0x74
    m('gekkouga_frame')
    check('on a ledge (0x74, CliffWait): the clones play Wait1 / Fall', g.vars.get(0x0F00031B), 0.0)
    g.situation = 2
    m.vm.g[4] = 0x46
    m('gekkouga_frame')
    check('hit in the air (0x46): Fall (0x24)', g.vars.get(0x0F00031B), 36.0)
    g.situation = 0
    # ---- swaps
    x0 = g.x
    g.press, g.stick = {1}, (-0.8, -0.8)
    m.vm.g[4] = 0
    m.vm.g[24] = 0x8000
    m('gekkouga_frame')
    check('down special + left: swapped with the left clone (him -14), Buffer_Clear specials (32), the frame\'s special bits off',
          (round(g.x - x0, 3), m.gf('gk_off_l'), m.gf('gk_off_r'), g.vars.get(0x0F0003C9), m.vm.g[24] & 0xF000, g.status_req),
          (-14.0, 14.0, 28.0, 32.0, 0, []))
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
    check('the channel: alive 2', g.vars.get(0x0F00031A), 2.0)
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
    # two Greninjas with clones: slot 2 at x 100, slot 5 at x -40 (both with the magic); the clone made at 98
    for s, x in ((2, 100.0), (5, -40.0)):
        shared(s, 7, 4747.0)
        slotpos(s, x, 0.0, -1.0)
    shared(2, 6, 2.0)
    shared(2, 0, -14.0)
    shared(2, 1, 14.0)
    shared(2, 2, 3.0)
    shared(2, 3, float(0x5F))
    shared(2, 4, 5.0)
    shared(2, 5, 1.0)
    g.x, g.y, g.lr = 98.0, 0.0, 1.0
    m('cl_frame')
    check('the clone finds him (slot 2, the nearest with the magic), its id from his VAR_30 (2)', (m.g('cl_slot'), m.g('cl_id')), (2, 2))
    check('its place: his X + its offset (114), his Y', (g.x, g.y), (114.0, 0.0))
    check('faces his way (-1, then the model turned)', [x for x in g.log if x[0] in ('lr', 'posture')][-2:], [('lr', -1.0), ('posture', 2)])
    check('his motion 0x5F from his frame 5 at his rate', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 5.0, 1.0)])
    g.log = []
    shared(2, 4, 6.0)
    g.frame = 6.0
    m('cl_frame')
    check('the next frame: the same motion, his rate (no restart)', ([x for x in g.log if x[0] == 'motion'], [x for x in g.log if x[0] == 'rate']),
          ([], [('rate', 1.0)]))
    shared(2, 4, 9.0)
    g.frame = 6.5
    g.log = []
    m('cl_frame')
    check('behind him (its own hitlag): back on his frame', [x for x in g.log if x[0] == 'setframe'], [('setframe', 9.0)])
    shared(2, 4, 0.0)
    g.log = []
    m('cl_frame')
    check('his frame went back (a restart): the motion again from his frame', [x for x in g.log if x[0] == 'motion'], [('motion', 0x5F, 0.0, 1.0)])
    shared(2, 3, 0.0)
    g.log = []
    m('cl_frame')
    check('a new motion (Wait1)', [x for x in g.log if x[0] == 'motion'], [('motion', 0, 0.0, 1.0)])
    shared(2, 2, 1.0)
    g.log = []
    m('cl_frame')
    check('not alive (alive 1: it is 2): hidden', [x for x in g.log if x[0] == 'visible'], [('visible', 0)])
    shared(2, 2, 3.0)
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


def package_tests(out, pkg, base, base_diag):
    z = zipfile.ZipFile(pkg)
    names = set(z.namelist())
    top = {n.split('/')[0] for n in names}
    check('the package\'s top level: README.txt, INSTALL_TO_data, INSTALL_TO_code, TEST_ONLY_INSTALL_TO_code (+ Sm4shCommand)',
          sorted(t for t in top if not t.startswith('Sm4shCommand_v')),
          ['INSTALL_TO_code', 'INSTALL_TO_data', 'README.txt', 'TEST_ONLY_INSTALL_TO_code'])
    want = []
    for root, _ds, fs in os.walk(os.path.join(out, 'fighter')):
        for f in fs:
            want.append('INSTALL_TO_data/' + os.path.relpath(os.path.join(root, f), out))
    check('every built file in INSTALL_TO_data (%d)' % len(want), sorted(w for w in want if w not in names), [])
    same = [w for w in want if z.read(w) != open(os.path.join(out, w[len('INSTALL_TO_data/'):]), 'rb').read()]
    check('... byte for byte', same, [])
    must = ['fighter/gekkouga/script/msc/gekkouga.mscsb', 'fighter/gekkouga/script/msc/clone/clone.mscsb',
            'fighter/gekkouga/script/animcmd/body/game.bin', 'fighter/gekkouga/script/animcmd/weapon/clone/game.bin',
            'fighter/gekkouga/motion/clone/main.pac', 'fighter/kirby/script/msc/kirby.mscsb'] + \
           ['fighter/gekkouga/model/clone/c%02d/%s' % (c, f) for c in range(8) for f in GB.CLONE_MODEL_FILES]
    check('the files the mod needs', [m for m in must if 'INSTALL_TO_data/' + m not in names], [])
    with tempfile.TemporaryDirectory() as td:
        for nm, b in (('gk1', base), ('gk1d', base_diag)):
            if not b:
                continue
            p = os.path.join(td, nm + '.rpx')
            import gekkouga_clone_cave as C
            a = C.args(b, nm == 'gk1d')
            subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), b, p] + a, check=True, stdout=subprocess.DEVNULL)
            member = ('INSTALL_TO_code' if nm == 'gk1' else 'TEST_ONLY_INSTALL_TO_code') + '/cross_f.rpx'
            check('%s is the cave on its base, rebuilt from the script' % member, z.read(member) == open(p, 'rb').read(), True)
    check('README.txt mentions every feature', all(w in z.read('README.txt').decode('utf8', 'replace')
                                                   for w in ('300', '720', '480', 'swap', 'chain', 'Technical')), True)
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
    a = sys.argv[1:]
    out, pkg, user, base = a[0], a[1], a[2], a[3]
    base_diag = a[4] if len(a) > 4 else None
    msc = os.path.join(out, 'fighter', 'gekkouga', 'script', 'msc')
    msc_tests(os.path.join(msc, 'gekkouga.mscsb'), os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'))
    clone_tests(os.path.join(msc, 'clone', 'clone.mscsb'), GB.CLONE_MSC)
    script_tests(out, user)
    package_tests(out, pkg, base, base_diag)
    tool_tests(out, base, base_diag, pkg)
    kirby = open(os.path.join(ROOT, 'fighters', 'kirby', 'kirby.c')).read()
    check('Kirby\'s copy of Greninja (0x30): Technical', 'if (kind == 0x30) { return trait_technical(); } // Greninja' in kirby, True)
    traits = open(os.path.join(ROOT, 'docs', 'character-traits.md')).read()
    check('docs/character-traits.md: Greninja 0x30 Technical', '| Greninja (`gekkouga`) | `0x30` | Technical |' in traits, True)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
