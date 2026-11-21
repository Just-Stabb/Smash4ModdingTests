#!/usr/bin/env python3
"""Ultra Instinct v1 (Supamario's gimmick) offline checks: the compiled MSC (ui_* through func_82's hook and statuses
0x157 / 0x158's functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built
scripts, motions, effects and sounds.

  python3 -I tools/supamario_ui_test.py BUILD_OUT_DIR TIMESKIP_OUT_DIR SUPAMARIO_DIR [--exe EXE] [--package ZIP
      [--since PREVIOUS_BUILD_OUT_DIR]]   (v6: --since: the package over the previous one, only the changed files)

BUILD_OUT_DIR: tools/supamario_ui_build.py's OUT_DIR; TIMESKIP_OUT_DIR: the same inputs built by
tools/supamario_timeskip_build.py (the install before this): every other script, motion and effect set is checked
unchanged; SUPAMARIO_DIR: the base fighter folder (v3: the model files the silver hair / eyes are added to). The
native part has its own test (tools/supamario_ui_cave_test.py).

The model of the game (its assumptions): the per-frame hook (func_82, which ends with ui_tick) before the status's loop
every frame; a status change asked (StatusModule 3, through func_16) takes effect on the next frame, when the old
status's end and the new one's pre / main run; the user variables (TIMER_0-3) count down by 1 each frame before the
hook (not below 0); the cave's record (status floats 6-9, flags 0x21000010-12) and its dodge signal (TIMER_1 / 2) are
written by the test where the cave would.
"""
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import omo  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
import supamario_fakedeath_test as FT  # noqa: E402
import supamario_ui_anim as A  # noqa: E402
import supamario_ui_model as M  # noqa: E402
import supamario_ui_build as B  # noqa: E402
import supamario_ui_cave as C  # noqa: E402

PROBLEMS = []


def fbits(x):
    """an MSC argument as the interpreter logs it: a float's bits (ints stay as they are when small)"""
    x = int(x)
    return struct.unpack('>f', struct.pack('>I', x & 0xFFFFFFFF))[0] if abs(x) > 0xFFFFF else float(x)


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


TIMERS = (C.V_FORM, C.V_DODGE_R, C.V_DODGE_L, B.V_AURA, B.V_SS, B.V_SHAPE, B.V_STOP, B.V_SWAY)   # (v5: TIMER_4, status 0x155's mode, counts
                                                                            # down too; ui4: TIMER_5, the shape's marker)


class Game:
    def __init__(self, status=0, damage=0.0, air=False, x=0.0, y=0.0, face=1.0):
        self.status, self.damage, self.air = status, damage, air
        self.x, self.y, self.face = x, y, face
        self.vars = {}
        self.sw = {}                      # status work floats (0x01xxxxxx) and flags (0x21xxxxxx)
        self.flags = set()
        self.req = None                   # the status asked this frame
        self.log = []                     # (frame, what, args)
        self.n = 0
        self.hitlag = 0
        self.motion = None
        self.loop = None                  # the status's loop (v5: 0x155's by its mode)
        self.vx = 0.0
        self.shield = 0
        self.pressed = set()              # v7: buttons pressed this frame (ControlModule(0x2710, button))

    def fvar(self, v):
        if v == 0x0F0000A2:
            return float(self.status)
        if v == 0x0F000117:
            return self.damage
        if v == 0x0F000000:
            return self.x
        if v == 0x0F000001:
            return self.y
        if v == 0x0F000003:
            return self.face
        if v >> 24 == 1:
            return self.sw.get(v, 0.0)
        return self.vars.get(v, 0.0)

    def setvar(self, v, val):
        if v == 0x0F000000:
            self.x = val
        elif v == 0x0F000001:
            self.y = val
        elif v == 0x0F000004:             # move forward (along his facing)
            self.x += val * self.face
        elif v >> 24 == 1:
            self.sw[v] = val
        else:
            self.vars[v] = val
        self.log.append((self.n, 'set', v, round(val, 4)))

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x16:
            if a[0] == 0 and len(a) == 3:
                self.setvar(a[2], f(a[1]))
            elif a[0] == 0x10:
                return int(a[1] in self.flags)
            return 0
        if sid == 0xA and a[0] == 0:
            return R.f2i(math.sqrt(max(0.0, f(a[1]))))
        if sid == 0x18:
            if a[0] == 0x3:
                self.req = a[1]
                self.log.append((self.n, 'status', a[1]))
            elif a[0] == 0x1:
                return 2 if self.air else 0
            elif a[0] == 0x2:
                self.air = a[1] == 2
                self.log.append((self.n, 'situation', a[1]))
            elif a[0] == 0x2713:
                self.log.append((self.n, 'status_data', tuple(a)))
            return 0
        if sid == 0x30 and a == [0x1]:
            return int(self.hitlag > 0)
        if sid == 0x36:
            self.shield = a[3] if len(a) > 3 else 0
            self.log.append((self.n, 'shield', tuple(a)))
            return 0
        if sid == 0x12 and a[0] == 0x1:
            self.motion = a[1]
            self.log.append((self.n, 'motion', a[1]))
            self.log.append((self.n, 'motion_at', a[1], fbits(a[2]) if len(a) > 2 else 0.0))
            self.log.append((self.n, 'motion_rate', a[1], round(fbits(a[3]), 4) if len(a) > 3 else 1.0))
            return 0
        if sid == 0xE and a[0] == 0x2710:               # v7: a button pressed this frame
            return int(a[1] in self.pressed)
        if sid == 0x49:                                 # v7: SlowModule (0 the global slow-motion, 1 its end)
            self.log.append((self.n, 'slow', tuple(a)))
            return 0
        if sid == 0xD:                                  # v7: CameraModule
            self.log.append((self.n, 'camera', tuple(round(fbits(x), 4) if i == 3 else x for i, x in enumerate(a))))
            return 0
        if sid == 0x10 and a[0] == 0x11 and a[1] == 0x3:
            self.vx = f(a[2])
            return 0
        if sid == 0x14 and a[0] == 0x1:
            self.face = -self.face
            self.log.append((self.n, 'turn'))
            return 0
        if sid == 0x1C:
            self.log.append((self.n, 'effect', a[0], a[1], a[2] if len(a) > 2 else None, tuple(a)))
            return 0
        if sid == 0x1E:
            self.log.append((self.n, 'sound', tuple(a)))
            return 0
        return 0

    def ev(self, what, frm=None):
        return [e for e in self.log if e[1] == what and (frm is None or e[0] >= frm)]


class Run:
    def __init__(self, path):
        self.path = path

    def vm(self, g):
        vm = R.VM(self.path)
        vm.game = g
        vm.g[11] = vm.func(17).bounds[0]
        return vm

    def fn(self, vm, name):
        return vm.func(FT.func_index(vm, name))

    def call(self, vm, name, *args):
        return vm.call(self.fn(vm, name), list(args))

    def frame(self, vm, g, status_funcs=True):
        """one frame: the timers, the hook, the status's loop; then a change asked takes effect (end, pre, main)"""
        g.n += 1
        for t in TIMERS:
            if g.vars.get(t, 0.0) > 0.0:
                g.vars[t] = max(0.0, g.vars[t] - 1.0)
        if g.hitlag > 0:
            g.hitlag -= 1
        vm.g[18] = 2 if g.air else 0
        g.req = None
        self.call(vm, 'func_82')
        if status_funcs and g.status == C.ST_UI and g.loop and g.req is None:
            self.call(vm, g.loop)
        vm.g[18] = 2 if g.air else 0
        if g.req is not None and g.req != g.status:
            self.change(vm, g, g.req)

    def change(self, vm, g, st):
        """v5: the transformation / its counter and the dodge are status 0x155 (its end func_2282, pre func_2252, main
        func_2265: each picks the mode from TIMER_4); the loop is the mode's"""
        if g.status == 0x155:
            self.call(vm, 'func_2282')
        g.status = st
        g.sw, g.flags = {}, set()
        g.loop = None
        vm.g[18] = 2 if g.air else 0
        if st == 0x155:
            self.call(vm, 'func_2252')
            self.call(vm, 'func_2265')
            m = g.vars.get(B.V_SS, 0.0)
            g.loop = ('ui_loop' if m > C.MODE_FORM_ON else 'ui_dodge_loop' if m > C.MODE_DODGE_ON else
                      'ui_loop' if m > C.MODE_SWAY_ON else None)       # v8: the spot dodge's rush: ui_loop
            g.log.append((g.n, 'mode', g.loop))


def trigger_tests(r):
    for what, kw, want in (('Wait at 99%', dict(status=0, damage=99.0), None),
                           ('Wait at 100%', dict(status=0, damage=100.0), C.ST_UI),
                           ('Walk at 130%', dict(status=1, damage=130.0), C.ST_UI),
                           ('Dash at 100%', dict(status=3, damage=100.0), C.ST_UI),
                           ('Run at 100%', dict(status=4, damage=100.0), C.ST_UI),
                           ('SquatWait at 100%', dict(status=0x12, damage=100.0), C.ST_UI),
                           ('Squat at 100%', dict(status=0x11, damage=100.0), C.ST_UI),
                           ('Fall in the air at 100%', dict(status=0xE, damage=100.0, air=True), C.ST_UI),
                           ('FallAerial in the air at 100%', dict(status=0xF, damage=100.0, air=True), C.ST_UI),
                           ('tumble (DamageFall 0x4C) at 150%', dict(status=0x4C, damage=150.0, air=True), None),
                           ('hitstun (Damage 0x46) at 150%', dict(status=0x46, damage=150.0, air=True), None),
                           ('shield (Guard 0x1C) at 150%', dict(status=0x1C, damage=150.0), None),
                           ('ledge (CliffCatch 0x73) at 150%', dict(status=0x73, damage=150.0), None),
                           ('landing lag (LandingLight 0x17) at 150%', dict(status=0x17, damage=150.0), None),
                           ('a jab (0x25) at 150%', dict(status=0x25, damage=150.0), None),
                           ('the side special (0x153) at 150%', dict(status=0x153, damage=150.0), None),
                           ('a jump (0xB) at 150%', dict(status=0xB, damage=150.0, air=True), None),
                           ('Fall on the ground situation (0xE, ground)', dict(status=0xE, damage=150.0), None)):
        g = Game(**kw)
        vm = r.vm(g)
        r.frame(vm, g, status_funcs=False)
        check('trigger: %s -> %s' % (what, 'the transformation' if want else 'nothing'),
              [e[2] for e in g.ev('status')], [want] if want else [])
    g = Game(status=0, damage=150.0)
    g.hitlag = 3
    vm = r.vm(g)
    r.frame(vm, g, status_funcs=False)
    check('trigger: Wait at 150% in hitlag -> nothing', g.ev('status'), [])
    g = Game(status=0, damage=150.0)
    g.vars[C.V_FORM] = 2000.0
    vm = r.vm(g)
    r.frame(vm, g, status_funcs=False)
    check('once a stock: transformed, Wait at 150% -> nothing (TIMER_0 kept at 2000)',
          (g.ev('status'), g.vars[C.V_FORM]), ([], 2000.0))


def form_run(r, air=False, counter_at=None, record=None, frames=None):
    g = Game(status=0xE if air else 0, damage=120.0, air=air, x=10.0, y=30.0 if air else 0.0, face=-1.0)
    vm = r.vm(g)
    r.frame(vm, g)
    for k in range(frames or (B.FORM_N + 3)):
        if counter_at is not None and g.status == C.ST_UI and k == counter_at:
            dmg, side, found, tx, ty, cat = record
            g.sw.update({0x01000006: dmg, 0x01000007: side, 0x01000008: tx, 0x01000009: ty})
            g.flags |= {C.FLAG_HIT} | ({C.FLAG_FOUND} if found else set()) | ({C.FLAG_NOTFIGHTER} if cat else set())
        r.frame(vm, g)
        if g.status not in (C.ST_UI,) and k > 2:
            break
    return g, vm


def form_tests(r):
    g, vm = form_run(r)
    start = [e for e in g.log if e[1] == 'status' and e[2] == C.ST_UI][0][0]
    check('the transformation: status 0x155 asked on the first frame (v5; v1-v4 0x157)', start, 1)
    check('  TIMER_4 = %g (the mode) written right before it' % C.MODE_FORM,
          [e[3] for e in g.ev('set') if e[2] == B.V_SS and e[0] == start][:1], [C.MODE_FORM])
    check('  its pre / main took the transformation\'s mode (ui_pre, ui_init, ui_loop)', [e[2] for e in g.ev('mode')][:1],
          ['ui_loop'])
    ren = sorted({e[0] for e in g.ev('set') if e[2] == B.V_SS and e[3] == C.MODE_FORM})
    end0 = [e for e in g.ev('status') if e[2] == 0][0][0]
    check('  the mode renewed every frame of the status (TIMER_4 counts down)', ren == list(range(start, end0 + 1)), True)
    check('  its end (func_2282 -> ui_end) clears the mode', [e[3] for e in g.ev('set') if e[2] == B.V_SS][-1:], [0.0])
    check('its pre: the attack log empty (no staling)', [e[2] for e in g.ev('status_data')][:1],
          [(0x2713, 0, 1, 0, 0, 0, 0, 0, 0x400, 0)])
    check('its motion: 0x231 (SpecialLwLight)', [e[2] for e in g.ev('motion')][:1], [B.MOT_FORM])
    sh = [(e[0] - start, e[2]) for e in g.ev('shield')]
    check('the counter shape on in XV2\'s window only: frames %d-%d (entry 0\'s 30-151), off at the end'
          % (B.CW_ON, B.CW_OFF), (sh[0], sh[1], sh[-1][1]),
          ((B.CW_ON, (0, 2, 0, 1, 1)), (B.CW_OFF, (0, 2, 0, 0, 1)), (0, 2, 0, 0, 1)))
    ints = [e for e in g.ev('set') if e[2] == 0x0F00011B]
    check('intangible (2 frames, renewed) every frame of the %d' % B.FORM_N,
          sorted({e[0] for e in ints}) == list(range(start, start + B.FORM_N)), True)
    end = [e for e in g.ev('status') if e[2] == 0][0][0]
    check('Wait at the end: the status %d frames long (its frames 0-%d)' % (B.FORM_N, B.FORM_N - 1), end - start,
          B.FORM_N - 1)
    check('transformed afterwards (TIMER_0 2000)', g.vars[C.V_FORM], 2000.0)
    check('v7: no camera change and no slow-motion in the transformation (the user)', (g.ev('camera'), g.ev('slow')),
          ([], []))
    check('no hitbox (the transformation\'s game script is empty)', True, True)
    r.frame(vm, g)
    aura = [e for e in g.ev('effect', end + 1)]
    ids = [B.fx_id(k) for k in ('aura_hip', 'aura_head', 'aura_foot', 'aura_chest', 'aura_hand')]
    check('the aura made right after (7 following requests 0x2717: v6 the chest and hands too; the five ids faded first; '
          'v3: 0x2717, the vanilla following request the Kamehameha uses, not v1 / v2\'s 0x2730: the crash fix)',
          sorted((e[2], e[3]) for e in aura),
          sorted([(0x2723, i) for i in ids] +
                 [(0x2717, B.fx_id(k)) for k in ('aura_hip', 'aura_chest', 'aura_head', 'aura_foot', 'aura_foot',
                                                  'aura_hand', 'aura_hand')]))
    check('v6: the renewal FADES the old ones (0x2723 (id, 0, 0): emission stopped, particles live out), never kills '
          'them at once (id, 1, 1: v1-v5, their sprites never got past 29 frames: the user\'s v5 clip)',
          sorted(tuple(e[5][2:4]) for e in aura if e[2] == 0x2723), [(0, 0)] * 5)
    check('  on HipN / BustN / HeadN / LFootJ / RFootJ / RHandN / LHandN', sorted(e[4] for e in aura if e[2] == 0x2717),
          sorted([B.BONES[b] for b in ('HipN', 'BustN', 'HeadN', 'LFootJ', 'RFootJ', 'RHandN', 'LHandN')]))
    head_up = round(0.2 * B.METRE, 3)
    check('  their arguments (id, bone, x, y, z, rx, ry, rz, size, flag 0): the head 0.2 m up, the sizes %g / %g' % (
        B.SCALE, round(0.8 * B.SCALE, 3)),
          sorted((e[5][1], e[5][2]) + tuple(round(fbits(x), 3) for x in e[5][3:10]) + (e[5][10],) for e in aura
                 if e[2] == 0x2717),
          sorted([(B.fx_id('aura_hip'), B.BONES['HipN'], 0, 0, 0, 0, 0, 0, B.SCALE, 0),
                  (B.fx_id('aura_chest'), B.BONES['BustN'], 0, 0, 0, 0, 0, 0, B.SCALE, 0),
                  (B.fx_id('aura_hand'), B.BONES['RHandN'], 0, 0, 0, 0, 0, 0, round(0.65 * B.SCALE, 3), 0),
                  (B.fx_id('aura_hand'), B.BONES['LHandN'], 0, 0, 0, 0, 0, 0, round(0.65 * B.SCALE, 3), 0),
                  (B.fx_id('aura_head'), B.BONES['HeadN'], 0, head_up, 0, 0, 0, 0, B.SCALE, 0),
                  (B.fx_id('aura_foot'), B.BONES['LFootJ'], 0, 0, 0, 0, 0, 0, round(0.8 * B.SCALE, 3), 0),
                  (B.fx_id('aura_foot'), B.BONES['RFootJ'], 0, 0, 0, 0, 0, 0, round(0.8 * B.SCALE, 3), 0)]))
    check('  no 0x2730 call left (v1 / v2\'s untested op)', [e for e in g.ev('effect') if e[2] == 0x2730], [])
    for k in range(int(B.AURA_EVERY) - 1):
        r.frame(vm, g)
    check('v6: nothing ended or made in between (the aura runs on: no renewal before %d frames)' % B.AURA_EVERY,
          [e for e in g.ev('effect') if e[0] > end + 1 and e[2] in (0x2717, 0x2723)], [])
    r.frame(vm, g)
    again = [e for e in g.ev('effect', end + 1 + int(B.AURA_EVERY)) if e[2] == 0x2717]
    check('  made again after %d frames (7), the old ones faded the same frame' % B.AURA_EVERY,
          (len(again), sorted(tuple(e[5][2:4]) for e in g.ev('effect', end + 1 + int(B.AURA_EVERY)) if e[2] == 0x2723)),
          (7, [(0, 0)] * 5))
    g, vm = form_run(r, air=True)
    check('in the air: held still, Fall at the end', ([e[2] for e in g.ev('status')][-1], g.air), (0xE, True))


def counter_tests(r):
    """v2: XV2's rush (BAC 1): he stays, faces the attacker, closes a gap only on frames GAP_FROM-GAP_TO"""
    for what, rec, want_x, turn in (
            ('a fighter in melee range to his right', (10.0, 1.0, True, 17.0, 0.0, 0), 10.0, True),
            ('a fighter 30 to his right (a gap closed to 9 short of it)', (10.0, 1.0, True, 40.0, 0.0, 0), 31.0, True),
            ('a fighter far to his right (the gap closed by at most 6 x 12.6)', (10.0, 1.0, True, 200.0, 0.0, 0),
             10.0 + 6 * B.GAP_V, True),
            ('a fighter to his left in range', (5.0, -1.0, True, 3.0, 0.0, 0), 10.0, False),
            ('nobody found (no 0x21000012)', (7.0, 1.0, False, 0.0, 0.0, 0), 10.0, True)):
        g, vm = form_run(r, counter_at=40, record=rec, frames=B.FORM_N + B.STRIKE_N + 5)
        ms = [e[2] for e in g.ev('motion')]
        check('counter, %s: the counter\'s motion (0x235) after the transformation\'s' % what, ms[:2],
              [B.MOT_FORM, B.MOT_STRIKE])
        at = [e for e in g.ev('motion') if e[2] == B.MOT_STRIKE][0][0]
        check('  at once (the frame the record is read)', at, 42)
        check('  turned to face it' if turn else '  not turned', len(g.ev('turn')), 1 if turn else 0)
        check('  stays where he is but for the gap: X %.1f, Y 0' % want_x, (round(g.x, 3), round(g.y, 3)),
              (round(want_x, 3), 0.0))
        moves = sorted({e[0] - at for e in g.ev('set') if e[2] == 0x0f000004})
        check('  the gap closed only on frames %d-%d' % (B.GAP_FROM, B.GAP_TO), all(B.GAP_FROM <= m <= B.GAP_TO for m in moves),
              True)
        check('  the shape off at once', [e[2] for e in g.ev('shield') if e[0] == at][:1], [(0, 2, 0, 0, 1)])
        check('  transformed from then on (TIMER_0 2000)',
              [e[3] for e in g.ev('set') if e[2] == C.V_FORM and e[0] == at][-1:], [2000.0])
        ints = sorted({e[0] for e in g.ev('set') if e[2] == 0x0F00011B and e[0] >= at})
        end = [e for e in g.ev('status') if e[2] in (0, 0xE)]
        check('  intangible every frame of the counter', ints == list(range(at, end[0][0] + 1)) if end else False, True)
        check('  the end after the counter\'s %d frames' % B.STRIKE_N, end[0][0] - at if end else None, B.STRIKE_N - 1)


def dodge_run(r, status=0, timer=C.V_DODGE_R, form=2000.0, air=False, frames=45, face=1.0, events=None):
    """events: {frame k (0-based, before it runs): callable(g)} (a press, a signal)"""
    g = Game(status=status, damage=150.0, air=air, x=0.0, face=face)
    g.vars[C.V_FORM] = form
    g.vars[B.V_AURA] = 999.0
    g.vars[timer] = 4.0
    vm = r.vm(g)
    xs = []
    for k in range(frames):
        g.pressed = set()
        if events and k in events:
            events[k](g)
        r.frame(vm, g)
        xs.append((g.status, round(g.vx, 3)))
    return g, vm, xs


def press(*buttons):
    return lambda g: g.pressed.update(buttons)


def signal(timer):
    return lambda g: g.vars.update({timer: 4.0})


def dodge_tests(r):
    """v7: XV2's sway (the autododge), its chain and its counter"""
    for st, name in ((0, 'Wait'), (1, 'Walk'), (2, 'WalkBrake'), (0x11, 'Squat'), (0x12, 'SquatWait'), (0x15, 'SquatRv')):
        g, vm, xs = dodge_run(r, status=st)
        check('dodge: transformed, %s, TIMER_1 (attacker right) -> status 0x155 in the dodge\'s mode (v5; v1-v4 0x158)'
              % name, ([e[2] for e in g.ev('status')][:1], [e[2] for e in g.ev('mode')][:1]), ([C.ST_DODGE], ['ui_dodge_loop']))
    g, vm, xs = dodge_run(r)
    start = [e for e in g.ev('status') if e[2] == C.ST_DODGE][0][0]
    check('v7: the sway, the attacker in front (to his right, him facing right): the back sway, motion 0x241 from '
          'frame 0 (CMN.ean #189)', [e[2:] for e in g.ev('motion_at')], [(B.MOT_SWAY_B, 0.0)])
    end = [e for e in g.ev('status') if e[2] == 0][0][0]
    check('  the mode %g (TIMER_4) every frame of it' % C.MODE_DODGE,
          sorted({e[0] for e in g.ev('set') if e[2] == B.V_SS and e[3] == C.MODE_DODGE}) == list(range(start, end + 1)),
          True)
    check('  intangible %d frames at its start (XV2\'s invulnerability 0-13)' % B.SWAY_INV,
          [e[3] for e in g.ev('set') if e[2] == 0x0F00011B], [float(B.SWAY_INV)])
    check('  the signals cleared', (g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]), (0.0, 0.0))
    check('  no travel (XV2\'s Movement none: the animation leans him)', {v for s_, v in xs if s_ == C.ST_DODGE}, {0.0})
    check('  the counter shape kept on through it (the chain): never switched off',
          [e for e in g.ev('shield') if e[2][3] == 0 and start <= e[0] < start + B.SWAY_N], [])
    end = [e for e in g.ev('status') if e[2] == 0][0][0]
    check('  Wait at its end (%d frames)' % B.SWAY_N, end - start, B.SWAY_N - 1)
    g, vm, xs = dodge_run(r, timer=C.V_DODGE_L)
    check('v7: the attacker behind him (to his left, him facing right): the forward sway, motion 0x243 from %d '
          '(CMN.ean #191, the same animation\'s second part)' % B.SWAY_F_AT, [e[2:] for e in g.ev('motion_at')],
          [(B.MOT_SWAY_F, float(B.SWAY_F_AT))])
    g, vm, xs = dodge_run(r, timer=C.V_DODGE_L, face=-1.0)
    check('  facing left, the attacker to his left: in front -> the back sway', [e[2] for e in g.ev('motion_at')],
          [B.MOT_SWAY_B])
    # the chain
    for k, what, want in ((B.SWAY_INV, 'on its first frame after the intangible ones', 2),
                          (B.SWAY_INV - 1, 'on its last intangible frame', 1)):
        g, vm, xs = dodge_run(r, frames=60, events={k: signal(C.V_DODGE_L)})
        sways = [e for e in g.ev('motion_at') if e[2] in (B.MOT_SWAY_B, B.MOT_SWAY_F, B.MOT_SWAY_BR, B.MOT_SWAY_FR)]
        check('v7: chain: a fighter\'s hit on the shape %s (TIMER_2 at sway frame %d) -> %s' % (
            what, k, 'another sway (the forward one: it came from behind; v10: the R one, the next of the alternation), '
            'the same status' if want == 2 else 'nothing (XV2: attacks miss there), the signal dropped'),
              ([e[2:] for e in sways], len([e for e in g.ev('status') if e[2] == C.ST_DODGE])),
              ([(B.MOT_SWAY_B, 0.0), (B.MOT_SWAY_FR, float(B.SWAY_FR_AT))][:want], 1))
        if want == 2:
            st2 = sways[1][0]
            check('  the second sway runs its full %d frames, intangible again' % B.SWAY_N,
                  ([e[0] for e in g.ev('status') if e[2] == 0][0] - st2,
                   [e[3] for e in g.ev('set') if e[2] == 0x0F00011B]), (B.SWAY_N - 1, [float(B.SWAY_INV)] * 2))
    # the counter cancel (v8: the transformation's rush, the user's clip)
    # v10 (the user: "make it only happen from a special button input"; the dodge's rush the short one)
    for k, btn, what, want in ((B.SWAY_CW_ON, 1, 'special on its first counter frame (%d)' % B.SWAY_CW_ON, True),
                               (B.SWAY_CW_OFF, 1, 'special on its last counter frame (%d)' % B.SWAY_CW_OFF, True),
                               (12, 1, 'special mid-sway', True),
                               (B.SWAY_CW_ON - 1, 1, 'special on its frame 0 (before the window)', False),
                               (B.SWAY_CW_OFF + 1, 1, 'special after the window', False),
                               (12, 0, 'attack mid-sway (v7-v9: the counter)', False),
                               (12, 4, 'smash (A+B / C-stick) mid-sway (v7-v9: the counter)', False)):
        g, vm, xs = dodge_run(r, frames=B.STRIKE_S_N + 40, events={k: press(btn)})
        ctr = [e for e in g.ev('motion_at') if e[2] in (B.MOT_STRIKE, B.MOT_STRIKE_S)]
        check('v10: counter cancel: %s -> %s' % (what, 'the SHORT rush (motion 0x236 from %d: SpecialLwHeavy\'s '
                                                  'animation\'s second part)' % B.STRIKE_S_AT if want else 'no counter'),
              [e[2:] for e in ctr], [(B.MOT_STRIKE_S, float(B.STRIKE_S_AT))] if want else [])
        if want and k == 12:
            at = ctr[0][0]
            check('  its mode the transformation\'s (TIMER_4 %g), the shape off at once, the same status (0x155)'
                  % C.MODE_FORM, ([e[3] for e in g.ev('set') if e[2] == B.V_SS and e[0] == at][-1:],
                                  [e[2] for e in g.ev('shield') if e[0] == at][-1:],
                                  len([e for e in g.ev('status') if e[2] == C.ST_UI])),
                  ([C.MODE_FORM], [(0, 2, 0, 0, 1)], 1))
            end = [e for e in g.ev('status') if e[2] == 0]
            ints = sorted({e[0] for e in g.ev('set') if e[2] == 0x0F00011B and e[0] > at})
            check('  intangible every frame of it, Wait after the short rush\'s %d frames (v8-v9: the long %d)'
                  % (B.STRIKE_S_N, B.STRIKE_N), (ints == list(range(at + 1, end[0][0] + 1)) if end else False,
                                                end[0][0] - at if end else None), (True, B.STRIKE_S_N - 1))
            check('  not turned (the attacker in front), no gap closed (no fighter found: the freeze box holds it)',
                  (g.ev('turn'), [e for e in g.ev('set') if e[2] == 0x0f000004]), ([], []))
            check('  its end (func_2282 -> ui_end) clears the mode, transformed afterwards',
                  (g.vars.get(B.V_SS), g.vars.get(C.V_FORM)), (0.0, 2000.0))
    g, vm, xs = dodge_run(r, timer=C.V_DODGE_L, frames=10, events={5: press(1)})
    check('v8: the rush from the forward sway (the attacker behind): turned to face it (v10: the short rush)',
          ([e[2] for e in g.ev('motion_at')][-1:], len(g.ev('turn'))), ([B.MOT_STRIKE_S], 1))
    # v10: the alternation (XV2's four sways: L / R dodge after dodge, the side by the attacker's)
    g, vm, xs = dodge_run(r, frames=B.SWAY_N + 2)
    seq = []
    for timer in (C.V_DODGE_R, C.V_DODGE_L, C.V_DODGE_L, C.V_DODGE_R, C.V_DODGE_R):
        g.vars[timer] = 4.0
        for _ in range(B.SWAY_N + 2):
            r.frame(vm, g)
    seq = [e[2:] for e in g.ev('motion_at')]
    check('v10: successive dodges alternate L / R (TIMER_7): in front, in front, behind, behind, in front, in front -> '
          'B_L (0x241 from 0), B_R (0x242 from %d), F_L (0x243 from %d), F_R (0x244 from %d), B_L, B_R'
          % (B.SWAY_BR_AT, B.SWAY_F_AT, B.SWAY_FR_AT), seq,
          [(B.MOT_SWAY_B, 0.0), (B.MOT_SWAY_BR, float(B.SWAY_BR_AT)), (B.MOT_SWAY_F, float(B.SWAY_F_AT)),
           (B.MOT_SWAY_FR, float(B.SWAY_FR_AT)), (B.MOT_SWAY_B, 0.0), (B.MOT_SWAY_BR, float(B.SWAY_BR_AT))])
    check('  the parity kept in Wait between the dodges (TIMER_7 renewed by ui_tick: > 0.5 after an odd count)',
          g.vars.get(B.V_SWAY, 0.0) > 0.5, False)
    g, vm, xs = dodge_run(r, frames=B.SWAY_N + 2)
    for _ in range(200):
        r.frame(vm, g)
    g.vars[C.V_DODGE_R] = 4.0
    for _ in range(3):
        r.frame(vm, g)
    check('  ... however long between them (200 frames in Wait, then the next: B_R)', [e[2] for e in g.ev('motion_at')],
          [B.MOT_SWAY_B, B.MOT_SWAY_BR])
    for what, kw in (('not transformed (TIMER_0 0)', dict(form=0.0)),
                     ('in Dash (3)', dict(status=3)), ('in the air (Fall)', dict(status=0xE, air=True)),
                     ('shielding (0x1C)', dict(status=0x1C))):
        g, vm, xs = dodge_run(r, frames=2, **kw)
        check('dodge: %s -> no dodge (no 0x155 in the dodge\'s mode)' % what,
              [e[2] for e in g.ev('mode') if e[2] == 'ui_dodge_loop'], [])
    g, vm, xs = dodge_run(r, status=3, frames=1)
    check('  a signal in Dash is dropped (TIMER_1 / 2 back to 0)', (g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]), (0.0, 0.0))
    g, vm, xs = dodge_run(r, frames=45)
    g.vars[C.V_DODGE_L] = 4.0
    for _ in range(3):
        r.frame(vm, g)
    check('no cooldown: a second signal right after the first dodge dodges again',
          len([e for e in g.ev('mode') if e[2] == 'ui_dodge_loop']), 2)


def escape_tests(r):
    """v7: the counter from his spot dodge (EscapeN) while transformed (the user's rule; v8: the rush)"""
    def run(events, form=2000.0, frames=16, status=0x1F):
        g = Game(status=status, damage=150.0)
        g.vars[C.V_FORM] = form
        g.vars[B.V_AURA] = 999.0
        vm = r.vm(g)
        for k in range(frames):
            g.pressed = set()
            if k in events:
                events[k](g)
            r.frame(vm, g)
        return g, vm
    g, vm = run({})
    check('v7: EscapeN while transformed: the counter shape on (an attack on it marks "attacked")',
          [e[2] for e in g.ev('shield')][:1], [(0, 2, 0, 1, 1)])
    for events, what, want in (({2: signal(C.V_DODGE_R), 3: press(0)}, 'attacked, then attack pressed', True),
                               ({2: signal(C.V_DODGE_L), 8: press(1)}, 'attacked, special pressed 6 frames later', True),
                               ({2: signal(C.V_DODGE_R), 4: press(4)}, 'attacked, smash pressed', True),
                               ({3: press(0)}, 'attack pressed, nobody attacked', False),
                               ({2: signal(C.V_DODGE_R)}, 'attacked, nothing pressed', False),
                               ({2: signal(C.V_DODGE_R), 3: press(2)}, 'attacked, jump pressed', False)):
        g, vm = run(events)
        ctr = [e for e in g.ev('motion_at') if e[2] in (B.MOT_STRIKE, B.MOT_STRIKE_S)]
        check('v8: EscapeN, %s -> %s' % (what, 'status 0x155 (asked in the counter\'s mode %g), the rush (v10: the '
                                          'dodge\'s SHORT rush, motion 0x236 from %d; the transformation\'s mode, '
                                          'its loop)' % (C.MODE_COUNTER, B.STRIKE_S_AT) if want else 'no counter'),
              ([e[2] for e in g.ev('status')][:1], [e[3] for e in g.ev('set') if e[2] == B.V_SS][:1],
               [e[2] for e in g.ev('mode')][:1], [e[2:] for e in ctr],
               [e[3] for e in g.ev('set') if e[2] == B.V_SS and ctr and e[0] == ctr[0][0]][-1:]),
              ([C.ST_UI], [C.MODE_COUNTER], ['ui_loop'], [(B.MOT_STRIKE_S, float(B.STRIKE_S_AT))], [C.MODE_FORM])
              if want else ([], [], [], [], []))
        if what.startswith('attacked, nothing'):
            check('  the mark kept through the spot dodge (TIMER_1 renewed to 4)', g.vars.get(C.V_DODGE_R), 4.0)
        if want and 'special' in what:
            check('  turned to face the attacker (to his left)', len(g.ev('turn')), 1)
    g, vm = run({2: signal(C.V_DODGE_R), 3: press(0)}, form=0.0)
    check('v7: EscapeN not transformed: no shape, no counter', (g.ev('shield'), g.ev('status')), ([], []))
    g, vm = run({2: signal(C.V_DODGE_R), 3: press(0)}, status=0x20)
    check('v7: EscapeF (a roll): no shape, no counter', ([e for e in g.ev('shield') if e[2][3] == 1], g.ev('status')),
          ([], []))


def shape_tests(r):
    """ui4: the autododge's counter shape (ui_shape from ui_tick): on while transformed in Wait / Walk / WalkBrake /
    Squat .. SquatRv on the ground (a hit on it is the cave's slot 42: the dodge), off elsewhere, switched only when that
    changes; off at the dodge's start and on a KO"""
    def run(status=0, form=2000.0, air=False, frames=5, hitlag=0):
        g = Game(status=status, damage=150.0, air=air)
        g.vars[C.V_FORM] = form
        g.vars[B.V_AURA] = 999.0
        g.hitlag = hitlag
        vm = r.vm(g)
        for _ in range(frames):
            r.frame(vm, g)
        return g, vm
    for st, name in ((0, 'Wait'), (1, 'Walk'), (2, 'WalkBrake'), (0x11, 'Squat'), (0x12, 'SquatWait'), (0x13, 'SquatF'),
                     (0x14, 'SquatB'), (0x15, 'SquatRv')):
        g, vm = run(status=st)
        check('ui4 / v9: the shape: transformed, %s: on EVERY frame (ShieldModule(0, 2, 0, 1, 1): v4-v8 only on frame 1),'
              ' TIMER_5 renewed' % name, ([(e[0], e[2]) for e in g.ev('shield')], g.vars.get(B.V_SHAPE)),
              ([(n, (0, 2, 0, 1, 1)) for n in range(1, 6)], 3.0))
    for what, kw in (('not transformed (TIMER_0 0)', dict(form=0.0)),
                     ('in Dash (3)', dict(status=3)), ('in Fall (the air)', dict(status=0xE, air=True)),
                     ('shielding (0x1C)', dict(status=0x1C)), ('in a jab (0x25)', dict(status=0x25))):
        g, vm = run(**kw)
        check('ui4: the shape: %s: never switched' % what, g.ev('shield'), [])
    g, vm = run(frames=3)
    g.status = 3
    for _ in range(3):
        r.frame(vm, g)
    check('ui4: the shape: Wait -> Dash: off once on the first Dash frame, TIMER_5 0',
          ([(e[0], e[2]) for e in g.ev('shield')], g.vars.get(B.V_SHAPE)),
          ([(n, (0, 2, 0, 1, 1)) for n in (1, 2, 3)] + [(4, (0, 2, 0, 0, 1))], 0.0))
    g, vm = run(frames=3)
    g.status = 0x155
    g.vars[B.V_SS] = 3.0
    r.frame(vm, g, status_funcs=False)
    check('ui4: the shape: Wait -> 0x155 (Secret Sensation\'s window switches it later): off at once',
          [(e[0], e[2]) for e in g.ev('shield')][3:], [(4, (0, 2, 0, 0, 1))])
    g, vm = run(frames=2)
    g.hitlag = 3
    g.status = 3
    r.frame(vm, g)
    check('ui4: the shape: in hitlag the frame he leaves Wait: off (only Wait-like statuses keep it)',
          [(e[0], e[2]) for e in g.ev('shield')], [(1, (0, 2, 0, 1, 1)), (2, (0, 2, 0, 1, 1)), (3, (0, 2, 0, 0, 1))])
    g, vm = run(frames=2)
    g.hitlag = 3
    r.frame(vm, g)
    g2, vm2 = run(frames=1, hitlag=3)
    check('v9: the shape in hitlag: kept on when on (re-armed), never switched on when off',
          ([e[0] for e in g.ev('shield')][-1:], g2.ev('shield')), ([3], []))
    g, vm = run(frames=2)
    g.vars[C.V_DODGE_R] = 4.0
    for _ in range(3):
        r.frame(vm, g)
    dg = [e[0] for e in g.ev('mode') if e[2] == 'ui_dodge_loop']
    check('ui4: the shape: a signal (slot 42) -> the dodge; v7: the shape kept on through the sway (its chain)',
          ([e for e in g.ev('shield') if e[2][3] != 1], dg[:1]), ([], dg[:1]))
    # v9 (the user's v7 test: "seems to only reactivate after being hit"; the v7 log: a dodge, the next attack on his
    # body, the next dodged): the game can drop the group between frames (its update range M + 0x28 / group + 0x30,
    # zeroed by the module's re-initialisation, the shape's word left at 1). Modelled: the group LIVE only from an ON
    # call to the game's next drop; the drop at every status change and at random frames. v4-v8 (the ON call only when
    # TIMER_5 said off) left it dead from the sway's end until a hit; now live on the next frame every time
    for drops, what in (('status', 'at every status change'), ('every', 'on every frame')):
        g, vm = run(frames=2)
        live, dead_frames = [True], []
        n_shield = [len(g.ev('shield'))]
        last_status = [g.status]

        def step():
            if drops == 'every' or g.status != last_status[0]:
                live[0] = False                      # the game drops the group (after this frame's MSC)
            last_status[0] = g.status
            r.frame(vm, g)
            new_ev = g.ev('shield')[n_shield[0]:]
            n_shield[0] = len(g.ev('shield'))
            for e in new_ev:
                live[0] = e[2][3] == 1
            if g.status in (0, 1, 2) and not live[0]:
                dead_frames.append(g.n)
        g.vars[C.V_DODGE_R] = 4.0
        for _ in range(B.SWAY_N + 12):
            step()
        sways = [e for e in g.ev('mode') if e[2] == 'ui_dodge_loop']
        check('v9: the group dropped by the game %s: after the sway (back in Wait) the shape is live on every Wait frame '
              '(v4-v8: dead until a hit)' % what, (len(sways), g.status, dead_frames), (1, 0, []))
    for st, name in ((0xB1, 'Dead'), (0xB2, 'Rebirth'), (0x14F, 'Entry')):
        g = Game(status=st, damage=0.0)
        g.vars.update({C.V_FORM: 2000.0, B.V_SHAPE: 2.0})
        vm = r.vm(g)
        r.frame(vm, g)
        check('ui4: the shape: %s with it on: off, TIMER_5 0' % name,
              ([e[2] for e in g.ev('shield')], g.vars.get(B.V_SHAPE)), ([(0, 2, 0, 0, 1)], 0.0))


def mode_tests(r):
    """v5: status 0x155's other modes untouched; a stale mode can't leak"""
    g, vm, xs = dodge_run(r, frames=45)
    check('dodge: its end clears the mode (TIMER_4 0)', g.vars.get(B.V_SS), 0.0)
    g = Game(status=0, damage=150.0)
    g.flags.add(0x2000004d)
    vm = r.vm(g)
    r.frame(vm, g, status_funcs=False)
    check('trigger: Wait at 150% with 0x2000004d on (func_79 would turn a special status into 0x83): nothing, no mode',
          (g.ev('status'), g.vars.get(B.V_SS, 0.0)), ([], 0.0))
    g2 = Game(status=0, damage=150.0)
    g2.vars.update({C.V_FORM: 2000.0, C.V_DODGE_R: 4.0})
    g2.flags.add(0x2000004d)
    vm2 = r.vm(g2)
    r.frame(vm2, g2, status_funcs=False)
    check('dodge: with 0x2000004d on: no dodge status, the signal dropped', (g2.ev('status'), g2.vars[C.V_DODGE_R]),
          ([], 0.0))


def reset_tests(r):
    for st, name in ((0xB1, 'Dead'), (0xB2, 'Rebirth'), (0x14F, 'Entry')):
        g = Game(status=st, damage=0.0)
        g.vars.update({C.V_FORM: 2000.0, C.V_DODGE_R: 3.0, C.V_DODGE_L: 2.0})
        vm = r.vm(g)
        r.frame(vm, g)
        check('reset: %s -> TIMER_0-2 0, the aura ended' % name,
              ((g.vars[C.V_FORM], g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]),
               sorted(e[3] for e in g.ev('effect') if e[2] == 0x2723)),
              ((0.0, 0.0, 0.0), sorted([B.fx_id(k) for k in ('aura_hip', 'aura_head', 'aura_foot', 'aura_chest',
                                                              'aura_hand')])))
        check('  ... at once there (0x2723 (id, 1, 1): a KO / respawn takes the particles too)',
              sorted({tuple(e[5][2:4]) for e in g.ev('effect') if e[2] == 0x2723}), [(1, 1)])
    g = Game(status=0x0, damage=150.0)
    vm = r.vm(g)
    r.frame(vm, g)
    check('after a reset: at 150% in Wait he transforms again (a new stock)', ([e[2] for e in g.ev('status')],
          g.vars.get(B.V_SS)), ([C.ST_UI], C.MODE_FORM))
    g = Game(status=0x45, damage=150.0)
    g.vars[C.V_FORM] = 1000.0
    vm = r.vm(g)
    r.frame(vm, g)
    check('the transformation\'s status left some other way: transformed (2000)', g.vars[C.V_FORM], 2000.0)


def ss_run(r, rec=None, at=10, frames=60, form=2000.0, air_target=False, trace=None, stop_at=None):
    """the grounded down special (status 0x155's main func_2265, its loop, its end func_2282); trace: {frame: his X}
    from the counter's read; stop_at: (v10) the slide's frame counter set to this after the read (the fallback)"""
    g = Game(status=0x155, damage=150.0, x=0.0, y=0.0, face=1.0)
    g.vars[C.V_FORM] = form
    g.vars[B.V_AURA] = 999.0
    vm = r.vm(g)
    vm.g[18] = 0
    r.call(vm, 'func_2265')
    zs = []
    for k in range(frames):
        if rec is not None and k == at and g.status == 0x155:
            g.sw.update({0x01000006: 9.0, 0x01000007: rec[0], 0x01000008: rec[1], 0x01000009: rec[2]})
            g.flags |= {C.FLAG_HIT} | ({C.FLAG_FOUND} if rec[3] else set())
        g.n += 1
        for t in TIMERS + (B.V_SS,):
            if g.vars.get(t, 0.0) > 0.0:
                g.vars[t] = max(0.0, g.vars[t] - 1.0)
        vm.g[18] = 2 if g.air else 0
        g.req = None
        r.call(vm, 'func_82')
        if g.status == 0x155:
            r.call(vm, 'ss_loop')
        if stop_at is not None and k == at + 1:
            g.sw[0x0100000C] = float(stop_at)
        if trace is not None and g.ev('motion_at') and B.MOT_ESCAPE_N in [e[2] for e in g.ev('motion_at')]:
            trace[k] = g.x
        zs.append(round(g.vars.get(0x0F000002, 0.0), 3))
        if g.req is not None and g.req != g.status:
            if g.status == 0x155:
                r.call(vm, 'func_2282')
            g.status = g.req
            break
    return g, vm, zs


def ss_tests(r):
    g, vm, zs = ss_run(r, frames=80)
    check('Secret Sensation (transformed, grounded down special): its stance motion 0x245',
          [e[2] for e in g.ev('motion')][:1], [B.MOT_SS])
    sh = [(e[0], e[2]) for e in g.ev('shield')]
    check('  the counter shape on at %d, off at %d (Marth-like)' % (B.SS_ON, B.SS_OFF), sh[:2],
          [(B.SS_ON, (0, 2, 0, 1, 1)), (B.SS_OFF, (0, 2, 0, 0, 1))])
    check('  no counter: Wait after the %d-frame stance' % B.SS_END, (g.status, g.n), (0, B.SS_END - 1))
    g, vm, zs = ss_run(r, form=0.0, frames=1)
    check('  not transformed: the grounded down special is Fake Death (motion 0x229)',
          [e[2] for e in g.ev('motion')][:1], [0x229])
    for what, rec, want in (('a grounded fighter 30 to his right', (1.0, 30.0, 0.0, True), (30.0 + B.SS_BEHIND, B.SS_UP_GROUND)),
                            ('a grounded fighter 25 to his left', (-1.0, -25.0, 0.0, True), (-25.0 - B.SS_BEHIND, B.SS_UP_GROUND)),
                            ('an airborne fighter (30, 20)', (1.0, 30.0, 20.0, True), (30.0 + B.SS_BEHIND_AIR, 20.0 + B.SS_UP_AIR))):
        g, vm, zs = ss_run(r, rec=rec)
        check('Secret Sensation, %s: the spot dodge (0x4B) slide' % what, [e[2] for e in g.ev('motion')][-1:],
              [B.MOT_ESCAPE_N])
        check('  ends behind it, airborne: (%g, %g)' % want, (round(g.x, 3), round(g.y, 3), g.air), want + (True,))
        check('  Fall after %d frames of slide (actionable)' % B.SS_SLIDE_N, g.status, 0xE)
        check('  into the background on the way (Z down to -%g) and back to 0' % B.SS_DEPTH,
              (min(zs) <= -B.SS_DEPTH + 0.05, zs[-1]), (True, 0.0))
        check('  facing it at the end', g.face == -rec[0], True)
        ints = [e for e in g.ev('set') if e[2] == 0x0F00011B]
        check('  intangible every frame of the slide', len(ints) >= B.SS_SLIDE_N, True)
    g, vm, zs = ss_run(r, rec=(1.0, 0.0, 0.0, False), frames=80)
    check('Secret Sensation, nobody to answer (an unowned item): no slide, the stance ends (Wait)',
          (B.MOT_ESCAPE_N in [e[2] for e in g.ev('motion')], g.status), (False, 0))
    check('  v7: no slow-motion, no camera', (g.ev('slow'), g.ev('camera')), ([], []))
    g, vm, zs = ss_run(r, frames=80)
    check('v7: Secret Sensation\'s stance alone (no counter): no slow-motion, no camera', (g.ev('slow'), g.ev('camera')),
          ([], []))
    g, vm, zs = ss_run(r, rec=(1.0, 30.0, 0.0, True), at=10)
    read = [e[0] for e in g.ev('motion') if e[2] == B.MOT_ESCAPE_N][0]
    land = [e[0] for e in g.ev('status') if e[2] == 0xE][0]
    check('v10: no slow-motion any more (v7-v9 SlowModule(0, 3, 48)): the world stop replaces it', g.ev('slow'), [])
    asks = sorted({e[0] for e in g.ev('set') if e[2] == B.V_STOP and e[3] == B.SS_STOP_ASK})
    check('v10: the world stop asked (TIMER_6 = %g) on every frame from the counter\'s read to his Fall (%d frames of '
          'travel + %d held behind the fighter), then 0' % (B.SS_STOP_ASK, B.SS_SLIDE_N, B.SS_ARRIVE),
          (asks == list(range(read, land + 1)) or asks == list(range(read, land)), land - read,
           [e[3] for e in g.ev('set') if e[2] == B.V_STOP][-1:]),
          (True, B.SS_SLIDE_N + B.SS_ARRIVE, [0.0]))
    check('v10: his slide (EscapeN) at his own slow motion, rate %g (the user\'s "3/4")' % B.SS_RATE,
          [e[2:] for e in g.ev('motion_rate') if e[2] == B.MOT_ESCAPE_N], [(B.MOT_ESCAPE_N, B.SS_RATE)])
    # the travel: a hold, then faster and faster
    xs_ = {}
    g2, vm2, zs2 = ss_run(r, rec=(1.0, 30.0, 0.0, True), at=10, frames=10 + 1 + B.SS_SLIDE_N + B.SS_ARRIVE + 4,
                          trace=xs_)
    k0 = min(xs_)
    path = [xs_[k] for k in sorted(xs_)]
    start, end = path[0], 30.0 + B.SS_BEHIND
    frac = [(x - start) / (end - start) for x in path]
    hold = frac[:B.SS_HOLD + 1]
    dash = frac[B.SS_HOLD:B.SS_SLIDE_N + 1]
    steps = [round(b - a, 4) for a, b in zip(dash, dash[1:])]
    check('v10: the hold: over its first %d frames he moves %g of the way, slowing to a stop (DBFZ: the stop)'
          % (B.SS_HOLD, B.SS_HOLD_FRAC), (round(hold[-1], 3), all(b - a >= -1e-6 for a, b in zip(hold, hold[1:])),
                                          hold[-1] - hold[-2] < hold[1] - hold[0]), (B.SS_HOLD_FRAC, True, True))
    check('v10: the dash: the rest over %d frames, every frame faster than the last (DBFZ: it accelerates to the target), '
          'arriving at frame %d' % (B.SS_DASH, B.SS_SLIDE_N),
          (all(b > a for a, b in zip(steps, steps[1:])), round(frac[B.SS_SLIDE_N], 4)), (True, 1.0))
    check('v10: held behind the fighter for %d frames after the arrival (the world still stopped)' % B.SS_ARRIVE,
          {round(x, 3) for x in path[B.SS_SLIDE_N:B.SS_SLIDE_N + B.SS_ARRIVE]}, {round(end, 3)})
    check('v9: both zooms slight (the user: "a slight zoom rather than a close one"; distance = how far: Kirby\'s 4.0 '
          '"slight", 1.4 "much closer"; v7 / v8 1.2 / 1.5): at least %g, the second (on him) the closer'
          % B.SS_CAM_MIN, (min(B.SS_CAM1_D, B.SS_CAM2_D) >= B.SS_CAM_MIN, B.SS_CAM2_D < B.SS_CAM1_D), (True, True))
    check('v10: the camera (v9\'s zooms, timed to the travel): in at the read, closer as the dash starts (frame %d), back '
          'when the world goes on (his Fall), again from its end' % B.SS_HOLD,
          [(e[0] - read, e[2]) for e in g.ev('camera')],
          [(0, (0x2714, B.SS_CAM1_T, 0, B.SS_CAM1_D)), (B.SS_HOLD, (0x2714, B.SS_CAM2_T, 0, B.SS_CAM2_D)),
           (land - read, (0x2718,)), (land - read, (0x2718,))])
    fx = [(e[0] - read, e[2], e[3]) for e in g.ev('effect') if e[0] >= read]
    check('v10: the effects: at the read the stance\'s charge faded (0x2723 (KTN_GKS_Loop, 0, 0)) and KiryokuMax\'s burst '
          '(BoostGKS_End) on him; the vanish lines as the dash starts; the vanish lines and his aura\'s burst '
          '(MGT_HENSIN02) where he lands; the charge faded again at the end',
          fx, [(0, 0x2723, B.fx_id('ss_charge')), (0, 0x2723, B.fx_id('ss_charge_2')), (0, 0x2710, B.fx_id('ss_release')),
               (B.SS_HOLD, 0x2710, B.fx_id('vanish')), (B.SS_SLIDE_N, 0x2710, B.fx_id('vanish')),
               (B.SS_SLIDE_N, 0x2710, B.fx_id('burst')), (land - read, 0x2723, B.fx_id('ss_charge')),
               (land - read, 0x2723, B.fx_id('ss_charge_2'))])
    # a KO mid-slide (its end runs) / the status left without its end (stale) / the fallback
    g, vm, zs = ss_run(r, rec=(1.0, 30.0, 0.0, True), at=10, frames=14)
    r.call(vm, 'func_2282')
    check('v10: Secret Sensation left mid-slide through its end (a KO: Dead\'s change runs it): the world stop\'s asks '
          'ended (TIMER_6 0: the cave lets the world go within its 2-frame lease) and the camera back',
          (g.vars.get(B.V_STOP), [e[2] for e in g.ev('camera')][-1:]), (0.0, [(0x2718,)]))
    g, vm, zs = ss_run(r, rec=(1.0, 30.0, 0.0, True), at=10, frames=14)
    n0 = len(g.ev('camera'))
    g.status = 0x46
    g.loop = None
    r.frame(vm, g)
    check('v7 / v10: left mid-slide WITHOUT its end (TIMER_4 still Secret Sensation\'s outside 0x155): the next frame ends '
          'them (ss_stale: the asks 0, the camera back) and clears TIMER_4',
          ([e[2] for e in g.ev('camera')][n0:], g.vars.get(B.V_STOP), g.vars.get(B.V_SS)), ([(0x2718,)], 0.0, 0.0))
    r.frame(vm, g)
    check('  once only', [e[2] for e in g.ev('camera')][n0:], [(0x2718,)])
    check('v10: the fallback bound covers the travel (%d frames asked at most, the travel and the hold %d)'
          % (B.SS_STOP_MAX, B.SS_SLIDE_N + B.SS_ARRIVE), B.SS_SLIDE_N + B.SS_ARRIVE < B.SS_STOP_MAX, True)
    g, vm, zs = ss_run(r, rec=(1.0, 30.0, 0.0, True), at=10, frames=13, stop_at=B.SS_STOP_MAX + 5)
    check('v10: the fallback: past %d frames of the counter the asks stop (0) even if he hasn\'t arrived'
          % B.SS_STOP_MAX, g.vars.get(B.V_STOP), 0.0)


def script_tests(out, ts_out):
    body = os.path.join(out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    tbody = os.path.join(ts_out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    f = {p: acmd.ACMDFile.load(os.path.join(body, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    b = {p: acmd.ACMDFile.load(os.path.join(tbody, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    nm = lambda c: c.name  # noqa: E731
    g = f['game'].script('speciallwheavy')
    hb = [c for c in g if nm(c).lower() == 'extra_special_hitbox']
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    d = [dict(zip(syn, c.params)) for c in hb]
    check('the counter (XV2\'s BAC 1): the freeze, 14 rush hits, the finisher', len(hb), 16)
    if len(hb) == 16:
        fz, ru, st = d[0], d[1:15], d[15]
        check('  the freeze at 0: ID 1 Part 1, no damage / knockback, the attacker held to the first rush hit (%d), '
              'a 3 m sphere' % B.RUSH_AT[0],
              (fz['ID'], fz['Part'], fz['Damage'], fz['KBG'], fz['BKB'], fz['HitstopFrames'], fz['SelfHitstopFrames'],
               round(fz['Size'], 2)), (1, 1, 0.0, 0, 0, B.RUSH_AT[0], 0, B.FREEZE_SIZE))
        check('  the rush: 14 x %.1f%%, angle 361, KBG 0, BKB 15' % B.RUSH_DMG,
              {(round(x['Damage'], 3), x['Angle'], x['KBG'], x['BKB']) for x in ru}, {(B.RUSH_DMG, 361, 0, 15)})
        check('  the finisher: %.1f%%, angle 35, BKB 80, KBG 75, no clank' % B.FINISH_DMG,
              (st['Damage'], st['Angle'], st['BKB'], st['KBG'], st['Clang']), (B.FINISH_DMG, 35, 80, 75, 0))
    holds = [c.params for c in g if nm(c).lower() == 'hitbox_hold']
    check('  every rush hit held (Hitbox_Hold(0, 2))', holds, [[0, 2]] * 14)
    clears = sum(1 for c in g if nm(c).lower() == 'hit_log_clear')
    check('  the hit log cleared before each rush hit and the finisher (15)', clears, 15)
    frames = [int(c.params[0]) for c in g if nm(c).upper() == 'FRAME']
    want = [1] + [x for f in B.RUSH_AT for x in (f, f + 2)] + [B.STRIKE_AT, B.STRIKE_AT + 3, B.CNT_END]
    check('  frames: freeze off 1, the rush at %s (2 frames each), the finisher %d, the silver swap %d (v3)' % (
        B.RUSH_AT, B.STRIKE_AT, B.CNT_END), frames, want)
    ov = [nm(c) for c in f['effect'].script('speciallwlight') if nm(c) in ('Color_Overlay', 'Terminate_Overlays',
                                                                          'Outline_Shell')]
    check('the transformation\'s white body: Color_Overlay + Outline_Shell at 10, Terminate_Overlays + the shell off at 220',
          ov, ['Color_Overlay', 'Outline_Shell', 'Terminate_Overlays', 'Outline_Shell'])
    glow = [(c.name, c.params) for c in B.glow_on()]
    for sname, at in (('speciallwlight', B.FX_BURST_AT), ('speciallwheavy', B.CNT_END)):
        got = [(fr, c.name, c.params) for fr, c in at_frames(f['effect'].script(sname))
               if c.name in ('Outline_Set', 'Outline_Shell', 'Terminate_Overlays')]
        check('v6: %s: the white body ends at %d into the held glow (Terminate_Overlays, Outline_Set\'s rim %s at %g, '
              'Outline_Shell\'s band %s at %g, %g px, added; Frames 0)' % (
                  sname, at, B.GLOW_RIM_RGB, B.GLOW_RIM_A, B.GLOW_SHELL_RGB, B.GLOW_SHELL_A, B.GLOW_SHELL_W),
              [x for x in got if x[0] == float(at)],
              [(float(at), 'Terminate_Overlays', [])] + [(float(at), n, p_) for n, p_ in glow])
    # v9 (the user's v7 clip: the band white, 4-6 px, the body washed pale): the band drawn OVER (Blend 0: no sum over
    # the parts), thin, and blue-violet for any encoding scale k up to GLOW_SHELL_K_MAX (the clip: k >= 2.2); v6-v8's
    # (150, 135, 255) added at 200 fails it (white from k 1.7); the rim no stronger than its colour at the edge, no tint
    def band(bg, k):
        a = B.GLOW_SHELL_A / 255.0
        col = [min(1.0, k * c / 255.0) for c in B.GLOW_SHELL_RGB]
        if B.GLOW_SHELL_BLEND == 1:
            return [round(255 * min(1.0, bg / 255.0 + a * c)) for c in col]
        return [round(255 * ((1 - a) * bg / 255.0 + a * c)) for c in col]
    bands = [band(bg, k) for bg in (23, 100, 200) for k in (1.0, 2.0, B.GLOW_SHELL_K_MAX)]
    check('v9: the glow held (Frames 0), its band drawn over (Blend 0) and blue-violet over a dark / mid / light stage '
          'for k 1 / 2 / %g (blue >= red >= green, blue over green by 30, never white): %s' % (B.GLOW_SHELL_K_MAX, bands),
          (B.glow_on()[0].params[6], B.glow_on()[1].params[6], B.glow_on()[1].params[10],
           all(b[2] >= b[0] >= b[1] and b[2] - b[1] >= 30 and min(b) < 200 for b in bands)), (0, 0, 0, True))
    check('v9: the band thin (at most 2 px of 1280 x 720; v6-v8 3), the rim at most its colour at the edge (Alpha <= 255; '
          'v6-v8 600) with no tint (v6-v8 18: the body washed)', (B.GLOW_SHELL_W <= 2.0, B.GLOW_RIM_A <= 255.0,
                                                                   B.GLOW_RIM_TINT), (True, True, 0.0))
    # v9: Time Skip's outline ends (Alpha 0) followed by the glow again when transformed; the falls / landings put it on
    for h, cmds in sorted(f['effect'].scripts.items()):
        if h in {acmd.crc(n_) for n_ in list(B.SCRIPT.values()) + list(B.SWAY_SCRIPTS)}:
            continue
        offs = [i for i, c in enumerate(cmds) if c.name == 'Outline_Shell' and c.params[4] == 0.0]
        if not offs:
            continue
        tail = [(c.name, c.params) for c in cmds[offs[-1] + 1:]]
        want = [(c.name, c.params) for c in B.glow_restore()]
        check('v9: effect script 0x%08X ends an Outline_Shell (Time Skip\'s): the glow again after its last command '
              'when transformed (TIMER_0 > %g: glow_on)' % (h, B.UI_TRANSFORMED_OVER),
              [x for x in tail if x[0] in ('Float_Var_Compare', 'True', 'Outline_Set', 'Outline_Shell')][-4:], want)
    for name in B.GLOW_AFTER:
        sc = f['effect'].script(name)
        check('v9: %s\'s effect script puts the glow on at frame 0 when transformed' % name,
              [(c.name, c.params) for c in (sc or [])[:4]], [(c.name, c.params) for c in B.glow_restore()])
    check('v6: the counter\'s effect script plays no aura (the MSC\'s runs from its first frame: it doubled it)',
          [c.params[0] for c in f['effect'].script('speciallwheavy') if 'graphic' in nm(c).lower() and
           c.params[0] in [B.fx_id(k) for k in B.AURA_SETS]], [])
    cams = [nm(c) for p in f for sname in list(B.SCRIPT.values()) + list(B.SWAY_SCRIPTS) for c in f[p].script(sname)
            if 'camera' in nm(c).lower()]
    check('no camera command in any Ultra Instinct script (the user)', cams, [])
    check('the transformation / the dodge / Secret Sensation\'s stance: no hitbox (v4: the transformation\'s game script '
          'only the cap off and the silver look)',
          [nm(c) for s in ('speciallwlight', 'specialairlwlight', 'specialairlwheavy') for c in f['game'].script(s)],
          ['FRAME'] + ['Mesh_Visibility'] * 3 + ['FRAME'] + ['Mesh_Visibility'] * (6 + len(B.OVERLAYS)) +
          ['Script_End', 'Script_End', 'Script_End'])
    eff = [c for c in f['effect'].script('speciallwlight') if 'graphic' in nm(c).lower()]
    check('the transformation\'s effects: start, the aura (7 parts), the burst',
          [c.params[0] for c in eff], [B.fx_id('start')] + [B.fx_id(k) for k in ('aura_hip', 'aura_chest', 'aura_head',
                                                                                'aura_foot', 'aura_foot', 'aura_hand',
                                                                                'aura_hand')] + [B.fx_id('burst')])
    snd = [(nm(c), c.params) for c in f['sound'].script('speciallwlight')]
    check('its sounds: Start at %d (XV2 22), Success at %d (XV2 205)' % (B.SND_START, B.SND_SUCCESS), snd,
          [('FRAME', [float(B.SND_START)]), ('Sound_Effect', [B.SE_IDS['ui_start']]), ('FRAME', [float(B.SND_SUCCESS)]),
           ('Sound_Effect', [B.SE_IDS['ui_success']]), ('Script_End', [])])
    for s in ('speciallwheavy',):
        check('%s: the vanish sound / effect first' % s,
              ([c.params[0] for c in f['sound'].script(s) if nm(c) == 'Sound_Effect'][:1],
               [c.params[0] for c in f['effect'].script(s) if 'graphic' in nm(c).lower()][:1]),
              ([B.SE_IDS['ui_vanish']], [B.fx_id('vanish')]))
    sway_script_tests(f)
    skip = {acmd.crc(n) for n in B.SCRIPT.values()} | {acmd.crc(n) for n in B.silver_scripts()} | \
        {acmd.crc(n) for n in B.SWAY_SCRIPTS}
    other = []
    import copy
    want_eff = copy.deepcopy(b['effect'])
    restored = B.restore_glow(want_eff, skip)       # v9: Time Skip's outline ends / the falls and landings: the glow back
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if p == 'effect':
                s = want_eff.scripts[h]

            def key(c):          # v9: Time Skip's own outline values are its v11's (its test checks them)
                if c.name == 'Outline_Shell':
                    return (c.ident, c.params[4] == 0.0, c.params[6:9])
                return (c.ident, c.params)
            if [key(c) for c in s] != [key(c) for c in (ns or [])]:
                other.append((p, hex(h)))
    check('every other script as Time Skip v10\'s build (v9: but for the glow restored in %d effect scripts)'
          % len(restored), other, [])
    check('v9: the glow restored after Time Skip\'s two outline ends and at the start of the %d falls / landings'
          % len(B.GLOW_AFTER), sorted(w for _h, w in restored), ['end'] * 2 + ['start'] * len(B.GLOW_AFTER))
    silver_script_tests(f, b)


def sway_script_tests(f):
    """v7: the sways' scripts (SpecialAirLwLight's animation: the back sway from 0 (0x241), the forward sway from
    SWAY_F_AT (0x243, specialairlwlight_c3)); v8: no counter script of its own (the rush's)"""
    nm = lambda c: c.name  # noqa: E731
    for sname, at in (('specialairlwlight', 0), ('specialairlwlight_c3', B.SWAY_F_AT)):
        eff = [(fr, c.params[0], round(c.params[8], 2)) for fr, c in at_frames(f['effect'].script(sname))
               if 'graphic' in nm(c).lower()]
        check('v7: %s (a sway from %d): XV2\'s SKI_lineX_S (BTL_CMN 493, 0.35) at its frames 0 and 1 (XV2 1 / 4, in '
              'the x7 part)' % (sname, at), eff,
              [(float(at + k), B.fx_id('sway_line'), round(0.35 * B.SCALE, 2)) for k in B.SWAY_LINE_AT])
        snd = [(fr, c.params[0]) for fr, c in at_frames(f['sound'].script(sname)) if nm(c) == 'Sound_Effect']
        check('  its sound: CAR_BTL_CMN cue 5 (swing_05) at its frame 1 (XV2 7)', snd,
              [(float(at + B.SWAY_SND_AT), B.SE_IDS['ui_sway'])])
        check('  no hitbox, no expression', ([nm(c) for c in f['game'].script(sname)],
                                            [nm(c) for c in f['expression'].script(sname)]),
              (['Script_End'], ['Script_End']))
    check('v8: no script of v7\'s counter (specialairlwlight_c2, CMN.bac 706) written: the slot\'s scripts are Time '
          'Skip v10\'s (the base\'s)', 'specialairlwlight_c2' in B.SWAY_SCRIPTS, False)
    check('v7: the forward sway\'s script\'s first command waits for its start frame (the clock starts there)',
          [(n, f['effect'].script(n)[0].params[0]) for n in ('specialairlwlight_c3',)],
          [('specialairlwlight_c3', float(B.SWAY_F_AT))])


def mv(c):
    """a Mesh_Visibility command -> (mesh name, visible, persist); ui4: the Mesh is the mesh's index (B.MESH_INDEX)"""
    names = {i: n for n, i in B.MESH_INDEX.items()}
    return (names.get(c.params[1], hex(c.params[1])), c.params[2], c.params[3]) if c.params[0] == 0 else None


def at_frames(body):
    """[(frame, command)] of a script without loops (FRAME absolute, WAIT relative)"""
    fr, out = 0.0, []
    for c in body:
        if c.name == 'FRAME':
            fr = float(c.params[0])
        elif c.name == 'WAIT':
            fr += float(c.params[0])
        else:
            out.append((fr, c))
    return out


def silver_script_tests(f, b):
    """v4: the transformed look (Mesh_Visibility Persist 2: each mesh's own set state) in the game scripts: the cap off
    from the transformation's start, the silver full hair / eyes / mustache / eyebrows from the burst, his own look on
    Entry and in Wait1 while not transformed"""
    N, E = (B.SILVER_MESHES[k] for k in ('nohat', 'eye'))
    O = B.OVERLAYS
    hat, hair = M.HAT[0], M.HAIR
    check('v3: the mustache / eyebrow overlays: 3 mustache shapes, 7 eyebrow shapes', (
        sum('Mustache' in o for o in O), sum('Brows' in o for o in O)), (3, 7))
    on = [(hat, 0, 2), (hair, 0, 2), (N[0], 0, 2), (E[0], 0, 2), (N[1], 2, 2), (E[1], 2, 2)] + [(o, 2, 2) for o in O]
    off = [(hat, 2, 2), (hair, 2, 2), (N[0], 2, 2), (E[0], 2, 2), (N[1], 0, 2), (E[1], 0, 2)] + [(o, 0, 2) for o in O]
    hat_off = [(hat, 0, 2), (hair, 0, 2), (N[0], 1, 2)]
    nn = len(O)
    g = f['game']
    got = [(fr, mv(c)) for fr, c in at_frames(g.script('speciallwlight')) if c.name == 'Mesh_Visibility']
    check('v4: the transformation: the cap and sideburns off, his own full hair shown at its start (%d: the gold start, '
          'the white body); at the burst (%d) the silver full hair / eyes / overlays follow their tracks, his own hidden '
          '(Persist 2 every one)' % (B.HAT_OFF_AT, B.FX_BURST_AT), got,
          [(float(B.HAT_OFF_AT), x) for x in hat_off] + [(float(B.FX_BURST_AT), x) for x in on])
    check('v3: the burst is XV2\'s frame 220; v4: the cap off at XV2\'s 10', (B.FX_BURST_AT, B.HAT_OFF_AT), (220, 10))
    got = [(fr, mv(c)) for fr, c in at_frames(g.script('speciallwheavy')) if c.name == 'Mesh_Visibility']
    check('v4: the counter (transformed afterwards): the transformed look at its white body\'s end (%d)' % B.CNT_END, got,
          [(float(B.CNT_END), x) for x in on])
    w = g.script('wait1')
    names = [c.name for c in w]
    k = len(on)
    check('v4: Wait1: transformed (TIMER_0 > %g) the transformed look (v6: + the glow: Outline_Set, Outline_Shell), else '
          'his own' % B.UI_TRANSFORMED_OVER, names,
          ['Float_Var_Compare', 'True'] + ['Mesh_Visibility'] * k + ['Outline_Set', 'Outline_Shell'] +
          ['Float_Var_Compare', 'True'] + ['Mesh_Visibility'] * k + ['Script_End'])
    if len(names) == 7 + 2 * k:
        a = 4 + k
        check('  its conditions: TIMER_0 (0x%X) > / <= %g; the True blocks\' sizes' % (C.V_FORM, B.UI_TRANSFORMED_OVER),
              [(w[0].params, w[1].params), (w[a].params, w[a + 1].params)],
              [([C.V_FORM, 5, B.UI_TRANSFORMED_OVER], [2 + 5 * k + 11 + 12]),
               ([C.V_FORM, 2, B.UI_TRANSFORMED_OVER], [2 + 5 * k])])
        check('v6: Wait1\'s glow = the burst\'s (held: Frames 0)', [(c.name, c.params) for c in w[2 + k:a]],
              [(c.name, c.params) for c in B.glow_on()])
        check('  the blocks: transformed / his own', ([mv(c) for c in w[2:2 + k]], [mv(c) for c in w[a + 2:a + 2 + k]]),
              (on, off))
    for e in ('entryl', 'entryr'):
        check('v4: %s: at frame 0 his own look (Persist 2)' % e,
              [(fr, mv(c)) for fr, c in at_frames(g.script(e)) if c.name == 'Mesh_Visibility'], [(0.0, x) for x in off])
    for a in ('appealsl', 'appealsr'):
        check('v4: %s has no game script (the full hair\'s copy follows its track; the cap stays hidden)' % a,
              g.script(a), b['game'].script(a))
    check('v4: every Mesh_Visibility of the Ultra Instinct scripts is Persist 2 (no override entry)',
          sorted({c.params[3] for n in list(B.SCRIPT.values()) + list(B.silver_scripts()) for c in g.script(n) or []
                  if c.name == 'Mesh_Visibility'}), [2])
    for p in f:
        for n in B.silver_scripts():
            if p != 'game':
                check('v3: %s %s unchanged' % (p, n), [(c.ident, c.params) for c in f[p].script(n) or []],
                      [(c.ident, c.params) for c in b[p].script(n) or []])
    allmv = [c for n in list(B.SCRIPT.values()) + list(B.silver_scripts()) for c in g.script(n) or []
             if c.name == 'Mesh_Visibility']
    check('ui4: every Mesh_Visibility of the Ultra Instinct scripts names its mesh by INDEX (< 256: the game\'s mesh '
          'order, no name walk: v4\'s by-name commands missed every mesh whose name the model loader packs at an '
          'unaligned address), every index one of the build\'s', sorted({c.params[1] < 256 and c.params[1] in
                                                                      set(B.MESH_INDEX.values()) for c in allmv}),
          [True])
    check('v3: no Mesh_Visibility override ends the whole object (Mesh -1: other moves\' overrides kept)',
          [n for p in f for h, sc in f[p].scripts.items() for c in sc if c.name == 'Mesh_Visibility' and
           c.params[1] == 0xFFFFFFFF], [])
    mt = acmd_lookup_tests(f)
    return mt


BASE_DIR = None


def acmd_lookup_tests(f):
    """v4: the game's lookup for each Ultra Instinct slot: the slot -> the motion table's hash -> a script of that hash
    in each file (sorted unsigned: the game's binary search, docs/native-notes.md "Script binding")"""
    import struct as st_
    mtab = os.path.join(BASE_DIR, 'script', 'animcmd', 'body', 'motion.mtable')
    d = open(mtab, 'rb').read()
    ws = st_.unpack('>%dI' % (len(d) // 4), d)
    for slot, name in ((B.MOT_FORM, 'speciallwlight'), (B.MOT_STRIKE, 'speciallwheavy'), (B.MOT_DODGE, 'specialairlwlight'),
                       (B.MOT_SS, 'specialairlwheavy')):
        h = ws[slot]
        check('v4: motion 0x%X -> the motion table\'s hash 0x%08X = crc("%s")' % (slot, h, name), h, acmd.crc(name))
        for p in ('game', 'effect', 'sound', 'expression'):
            hashes = [x for x in f[p].scripts]
            check('  %s.bin: a script of that hash (binary search over the sorted table finds it)' % p,
                  h in hashes and hashes == sorted(hashes), True)
        n_cmd = {p: len([c for c in f[p].script(name) if c.name != 'Script_End']) for p in ('game', 'effect', 'sound')}
        if slot == B.MOT_FORM:
            check('  the transformation\'s game / effect / sound scripts are not empty', all(n_cmd.values()), True)


def motion_tests(out, ts_out):
    for part in ('main', 'mariopt1', 'lhand', 'rhand'):
        new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        old = dict(omo.pac_read(os.path.join(ts_out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        diff = sorted(n.split('D03')[-1] for n in new if new[n] != old.get(n))
        check('%s.pac: only the four slots changed' % part, diff, sorted([A.DODGE, A.STRIKE, A.FORM, A.SS]))
        fr = {m: omo.Omo(new[[n for n in new if n.endswith('D03' + m)][0]]).frames for m in A.MOTIONS}
        check('%s.pac: 325 / 349 / 74 / 45 frames (v7: SpecialAirLwLight the two sways, 37 + 37; v8: no 706 strike)'
              % part, fr, {A.FORM: 325, A.STRIKE: 349, A.DODGE: 74, A.SS: 45})
    src = [(A.source(A.DODGE, f_)[0][0], A.source(A.DODGE, f_)[1], round(A.source(A.DODGE, f_)[2], 2))
           for f_ in (0, 1, 2, 36, 37, 38, 73)]
    check('v7: SpecialAirLwLight\'s frames: the back sway CMN #189 (0 shows XV2 0, 1-36 XV2 7-42: the x7 start), the '
          'forward sway #191 from 37 (v8: nothing after)', src,
          [('sway_b_in', 189, 0.0), ('sway_b', 189, 7.0), ('sway_b', 189, 8.0), ('sway_b', 189, 42.0),
           ('sway_f_in', 191, 0.0), ('sway_f', 191, 7.0), ('sway_f', 191, 42.0)])
    check('v7: the build\'s frames agree with the anim\'s (SWAY_F_AT, SWAY_N)', (B.SWAY_F_AT, B.SWAY_N, 2 * B.SWAY_N),
          (37, 37, A.frames_of(A.DODGE)))


def effect_tests(out, ts_out):
    import ptcl
    d = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario')
    td = os.path.join(ts_out, 'fighter', 'supamario', 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    tp = ptcl.Ptcl(open(os.path.join(td, 'supamario.010d0000.ptcl'), 'rb').read())
    check('the ptcl validates', p.validate(), [])
    n = len(tp.sets)
    check('the earlier sets kept (names)', [p.set_name(i) for i in range(n)], [tp.set_name(i) for i in range(n)])
    check('new sets: PtcSupamarioUi*', sorted(p.set_name(i) for i in range(n, len(p.sets))),
          sorted('PtcSupamarioUi' + x[2][:-4] for x in B.FX))


def aura_tests(out, ts_out):
    """v9 (the user's v7 test: "the aura doesn't have any of its blue or white hue mixed in"): XV2's two colours per
    emitter (EnableSecondaryColor: a white core, a blue / cyan edge; the converter kept one, v3-v8's tint_aura turned all
    to hue 262 with saturation >= 0.45) kept, their hues moved onto the clip's blue .. violet; the other UI sets not"""
    import colorsys
    import ptcl
    d = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    aura = set(B.aura_set_names())
    B.ref_shader(p)
    hues, whites, two, other = [], 0, 0, set()
    for i in range(len(p.sets)):
        name = p.set_name(i)
        if not name.startswith('PtcSupamarioUi'):
            continue
        for e in p.sets[i]['emitters']:
            em = e['data']
            if em is None or p.field(em, 'shader_index') in B.REF_SHADERS:   # v9: the distortion (no colour drawn)
                continue
            k0, k1 = p.color_keys(em, 0)[0][:3], p.color_keys(em, 1)[0][:3]
            if name in aura and struct.unpack_from('>I', em, 0x314)[0] == 2 and k0 != k1:
                two += 1
            for k in (k0, k1):
                v = max(k)
                if v <= 0:
                    continue
                h, sa, _ = colorsys.rgb_to_hsv(*[c / v for c in k])
                if name in aura:
                    if sa < 0.08:
                        whites += 1
                    else:
                        hues.append(h * 360)
                elif sa > 0.05:
                    other.add(round(h * 360))
    blue = [h for h in hues if h < 245]
    violet = [h for h in hues if h > 262]
    check('v9: the aura\'s colours mixed as XV2\'s: white (saturation < 0.08: %d keys), blue (hue < 245: %d), violet '
          '(> 262: %d), all within the map\'s %g-%g; v3-v8: all one hue (262)' % (
              whites, len(blue), len(violet), B.AURA_HUE_MAP[0][1], B.AURA_HUE_MAP[1][1]),
          (whites > 0, len(blue) > 0, len(violet) > 0,
           all(B.AURA_HUE_MAP[0][1] - 0.5 <= h <= B.AURA_HUE_MAP[1][1] + 0.5 for h in hues)), (True, True, True, True))
    check('v9: the two-colour programs (combiner 2) draw XV2\'s two colours: core (colour 0) and edge (colour 1) differ '
          'on at least 6 emitters (XV2: 15 of 19 nodes have a secondary colour)', two >= 6, True)
    check('  the other UI sets (start, burst, vanish) keep XV2\'s colours (none moved into the violet)',
          any(h > 262 for h in other), False)
    check('v9: the hue map: XV2 180 (cyan) -> %g, 240 (blue) -> %g, a white stays white' % (
        B.AURA_HUE_MAP[0][1], B.AURA_HUE_MAP[1][1]),
          (round(B.hue_map(180.0), 3), round(B.hue_map(240.0), 3), tuple(round(c, 3) for c in B.ui_colour((1.0, 1.0, 1.0)))),
          (B.AURA_HUE_MAP[0][1], B.AURA_HUE_MAP[1][1], (1.0, 1.0, 1.0)))


def aura_v5_tests(out, base):
    """v5: the aura's sets smooth (many soft additive sprites); v9: XV2's own refraction emissions (Ref_FOK) as the
    distortion (the fireball's refraction program, XV2's emission), every aura emitter following him"""
    import ptcl
    import eft_vertex
    d = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    q = ptcl.Ptcl(open(os.path.join(base, 'effect', 'supamario', 'supamario.010d0000.ptcl'), 'rb').read())
    fsrc = p.find_set(B.HAZE_SRC[0])
    ref = [e['data'] for e in p.sets[fsrc]['emitters'] if e['data'] is not None and
           p.emitter_name(e['data']) == B.HAZE_SRC[1]][0]
    rsh = p.field(ref, 'shader_index')
    rows, bad, refr, follow, names = [], [], [], [], []
    for name in B.aura_set_names():
        for e in p.sets[p.find_set(name)]['emitters']:
            em = e['data']
            if em is None:
                continue
            names.append(p.emitter_name(em))
            fo = struct.unpack_from('>I', em, 0x310)[0]
            follow.append((name, p.emitter_name(em), fo, fo in eft_vertex.features(
                p.shader_binary(p.field(em, 'shader_index')))['follow']))
            if p.field(em, 'shader_index') == rsh:
                refr.append((name, p.emitter_name(em), em))
                continue
            iv, bl = p.field(em, 'emit_interval'), p.field(em, 'blend_type')
            rows.append((iv, bl))
            if not (1 <= iv <= 7 and bl == 1):
                bad.append((name, p.emitter_name(em), iv, bl))
    check('v5: the aura sets\' %d colour emitters: one particle every 1-7 frames (XV2\'s converted 9-39 / %g), additive '
          '(blend 1)' % (len(rows), B.AURA_DENSITY), bad, [])
    check('v9: every aura emitter follows him (ptcl 0x310 = %d, position only; v1-v8 1: left in the world, the trail) and '
          'its program draws that follow type' % B.AURA_FOLLOW,
          [x for x in follow if x[2] != B.AURA_FOLLOW or not x[3]], [])
    check('v9: the distortion = XV2\'s own refraction emissions (Ref_FOK_L / _R: Aura_LoopFOK\'s and FOK_FootL\'s two '
          'sprite_2_1_*), 4 of them, on the hip and feet sets; no v5-v8 UiHaze',
          (sorted((n, en) for n, en, _e in refr), 'UiHaze' in names),
          (sorted([('PtcSupamarioUiAura_LoopFOK', 'sprite_2_1_1_1'), ('PtcSupamarioUiAura_LoopFOK', 'sprite_2_1_2_1'),
                   ('PtcSupamarioUiFOK_FootL', 'sprite_2_1_2_1_1'), ('PtcSupamarioUiFOK_FootL', 'sprite_2_1_2_1_1_1')]),
           False))
    rk = [o for o in range(0x304, 0x340, 4) if o not in (0x310,)] + list(range(0x830, 0x868, 4)) + [0x324, 0x4BC]
    for n, en, em in refr:
        check('  %s %s: the fireball\'s refraction program (frame buffer read: %s), its two textures, its shader-keyed '
              'words; XV2\'s strength (alpha up %g x %g), its life %d' % (
                  n, en, b'frameBufferTexture' in bytes(p.shader_binary(rsh)), 0.6, B.REF_STRENGTH,
                  p.field(em, 'ptcl_life')),
              ([p.texres(em, k)['native_pos'] for k in (0, 1)], [struct.unpack_from('>I', em, o)[0] for o in rk],
               round(p.field(em, 'alpha_diff21'), 3)),
              ([p.texres(ref, k)['native_pos'] for k in (0, 1)], [struct.unpack_from('>I', ref, o)[0] for o in rk],
               round(0.6 * B.REF_STRENGTH, 3)))
    qs = q.find_set(B.HAZE_SRC[0])
    check('v5: the fireball\'s own set untouched', [bytes(e['data']) for e in p.sets[fsrc]['emitters'] if e['data']],
          [bytes(e['data']) for e in q.sets[qs]['emitters'] if e['data']])
    check('v5: the file still validates', p.validate(), [])


def aura_v6_tests(out):
    """v6 (the user's v5 clip: no aura after the burst): the renewal outlasts the sprites (the MSC fades, never kills at
    once: msc_tests), so at most AURA_GENERATIONS instances a part; the aura's brightness as the game keeps it"""
    import ptcl
    d = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    life = B.aura_life(p)
    check('v6: the renewal (%g frames) at least the aura sprites\' longest life (%d): a faded generation is gone before '
          'the next fade (%d alive a part at most)' % (B.AURA_EVERY, life, B.AURA_GENERATIONS), B.AURA_EVERY >= life, True)
    check('v6: the aura sprites live longer than v1-v5\'s 30-frame kill (the bug: none got past 29 frames)', life > 30, True)
    n = 0
    for key in B.AURA_SETS:
        name = 'PtcSupamarioUi' + [x for x in B.FX if x[0] == key][0][2][:-4]
        n += sum(1 for e in p.sets[p.find_set(name)]['emitters'] if e['data'] is not None) * (2 if key in (
            'aura_foot', 'aura_hand') else 1)
    check('v6: emitters the MSC aura keeps (7 parts) x %d generations: %d (eft\'s pool; the diag logs "Emitter is '
          'Empty." if it runs out)' % (B.AURA_GENERATIONS, n * B.AURA_GENERATIONS), n * B.AURA_GENERATIONS <= 80, True)


def model_tests(out, base):
    """v3: the silver hair / eyes in every costume's model files"""
    import mta
    import nud
    import nut
    import supamario_ui_model as M
    import fighter_texture_ids as T
    for nn in range(M.COSTUMES):
        c = 'c%02d' % nn
        src = os.path.join(base, 'model', 'body', c)
        dst = os.path.join(out, 'fighter', 'supamario', 'model', 'body', c)
        old, new = nud.read(os.path.join(src, 'model.nud')), nud.read(os.path.join(dst, 'model.nud'))
        n0 = len(old)
        ovs = M.overlays(old)
        check('%s model.nud: the meshes as before, then the 2 copies (v4: no sideburn copy) and the %d overlays (c00\'s '
              'names)' % (c, len(ovs)), ([m.name for m in new], [o['name'] for o in ovs]),
              ([m.name for m in old] + [M.MESHES[k][1] for k in ('nohat', 'eye')] + B.OVERLAYS, B.OVERLAYS))
        for fn in ('model.nud', 'metal.nud'):
            if os.path.exists(os.path.join(dst, fn)):
                nm = [m.name for m in nud.read(os.path.join(dst, fn))]
                check('ui4: %s %s: every mesh index the scripts use names its mesh (%d)' % (c, fn, len(B.MESH_INDEX)),
                      [(n, nm[i] if i < len(nm) else None) for n, i in sorted(B.MESH_INDEX.items()) if
                       i >= len(nm) or nm[i] != n], [])
        import moi
        m0 = moi.read(open(os.path.join(src, 'model.moi'), 'rb').read())
        m1 = moi.read(open(os.path.join(dst, 'model.moi'), 'rb').read())
        check('%s model.moi (v4): one table-1 entry per NUD mesh (the invariant every vanilla model keeps; v3: 47 meshes, '
              '34 entries), the old entries kept, each copy\'s at its NUD index with its bone, VIS 1; table 2 the same '
              'plus the copies\' names' % c,
              (len(m1['t1']), m1['t1'][:len(m0['t1'])] == m0['t1'], m1['t2'][:len(m0['t2'])] == m0['t2'],
               [(e['name'], e['index'], e['bone'], e['vis']) for e in m1['t1'][len(m0['t1']):]],
               [(e['name'], e['index']) for e in m1['t2'][len(m0['t2']):]]),
              (len(new), True, True, [(moi.prefix(x.name), i, x.bone & 0xFFFF, 1) for i, x in enumerate(new) if i >= n0],
               [(moi.prefix(x.name), i) for i, x in enumerate(new) if i >= n0]))
        P = M.positions
        same = all(a.name == b.name and a.bone == b.bone and len(a.polygons) == len(b.polygons) and all(
            np.array_equal(pa.idx, pb.idx) and np.array_equal(P(pa), P(pb)) and
            [x.textures for x in pa.materials] == [x.textures for x in pb.materials] and
            [x.props for x in pa.materials] == [x.props for x in pb.materials]
            for pa, pb in zip(a.polygons, b.polygons)) for a, b in zip(old, new))
        check('%s: every existing mesh unchanged (geometry, materials, textures)' % c, same, True)
        hair_id, iris_id = M.tex_ids(nn)
        by = {m.name: m for m in new}
        face_id = M.face_tex_id(nn)
        for k, want in (('nohat', {0: hair_id}), ('eye', {0: iris_id, 1: iris_id})):
            a, b = by[M.MESHES[k][0]], by[M.MESHES[k][1]]
            geo = (a.bone, a.bind, len(a.polygons)) == (b.bone, b.bind, len(b.polygons)) and all(
                np.array_equal(pa.idx, pb.idx) and np.array_equal(P(pa), P(pb)) and
                np.array_equal(M.normals(pa), M.normals(pb)) and all(np.array_equal(u, v) for u, v in zip(pa.uvs, pb.uvs))
                for pa, pb in zip(a.polygons, b.polygons))
            tex = [[t['hash'] for m in p.materials for t in m.textures] for p in b.polygons]
            exp = []
            for j, p in enumerate(a.polygons):
                row = [t['hash'] for m in p.materials for t in m.textures]
                if j in want:
                    row[0] = want[j]          # the first material's colour texture
                exp.append(row)
            props = all([x.props for x in pa.materials] == [x.props for x in pb.materials]
                        for pa, pb in zip(a.polygons, b.polygons))
            check('%s %s: the same geometry / bone / UVs as %s, its materials\' properties (NU_materialHash) kept, '
                  'the silver texture' % (c, M.MESHES[k][1], M.MESHES[k][0]), (geo, props, tex), (True, True, exp))
        bad = []
        for o in ovs:
            a, b = by[o['source']].polygons[o['poly']], by[o['name']]
            pb = b.polygons[0] if len(b.polygons) == 1 else None
            if pb is None:
                bad.append(o['name'])
                continue
            n = M.normals(a) / np.linalg.norm(M.normals(a), axis=1, keepdims=True)
            tri = a.idx.reshape(-1, 3)[o['tris']].reshape(-1)
            ok = (b.bone == by[o['source']].bone and np.array_equal(pb.idx, tri) and
                  np.allclose(P(pb), P(a) + M.PUSH * n, atol=1e-3) and
                  [t['hash'] for t in pb.materials[0].textures][1:] == [t['hash'] for t in a.materials[0].textures][1:]
                  and pb.materials[0].textures[0]['hash'] == face_id and
                  [x.props for x in pb.materials] == [x.props for x in a.materials])
            ys = P(pb)[pb.idx.reshape(-1, 3)][:, :, 1]
            part_ok = (ys > M.BROW_Y - M.PUSH).all() if o['part'] == 'Brows' else (ys <= M.BROW_Y + M.PUSH).any(1).all()
            if not (ok and part_ok):
                bad.append(o['name'])
        check('%s: each overlay = its face\'s mustache / eyebrow triangles (texture ..0B), pushed %g out along the '
              'normals, the face\'s own silver texture (v4), the material otherwise as its source' % (c, M.PUSH), bad, [])
        cover = sorted(m for o in ovs for m in o['members'])
        faces = sorted(m.name for m in old for p in m.polygons if p.materials and
                       (p.materials[0].textures[0]['hash'] & 0xFF) == M.FACE_TEX)
        check('%s: every face with the mustache polygon (%d) in one mustache and one eyebrow overlay' % (c, len(faces)),
              cover, sorted(faces * 2))
        mo, mn = nud.read(os.path.join(src, 'metal.nud')), nud.read(os.path.join(dst, 'metal.nud'))
        mb = {m.name: m for m in mn}
        check('%s metal.nud: the 2 copies with the metal textures (the same mesh list as model.nud)' % c,
              ([m.name for m in mn][len(mo):], [[t['hash'] for t in mb[M.MESHES[k][1]].polygons[0].materials[0].textures]
                                               for k in M.MESHES]),
              ([M.MESHES[k][1] for k in ('nohat', 'eye')] + B.OVERLAYS,
               [[t['hash'] for t in mb[M.MESHES[k][0]].polygons[0].materials[0].textures] for k in M.MESHES]))
        d0, t0 = nut.load(os.path.join(src, 'model.nut'))
        d1, t1 = nut.load(os.path.join(dst, 'model.nut'))
        kept = len(t1) == len(t0) + 3 and all(
            a.tex_id == b.tex_id and d0[a.data_off:a.data_off + a.image_size] == d1[b.data_off:b.data_off + b.image_size]
            and d0[a.mip_off:a.mip_off + a.mip_size * (a.levels > 1)] == d1[b.mip_off:b.mip_off + b.mip_size * (b.levels > 1)]
            and d0[a.gtx:a.gtx + 0x80] == d1[b.gtx:b.gtx + 0x80] for a, b in zip(t0, t1))
        check('%s model.nut: every texture kept byte for byte, 3 added' % c, kept, True)
        lo, hi = T.fighter_range('supamario')
        check('%s: the new ids 0x%08X / 0x%08X / 0x%08X, in Supamario\'s own range' % (c, hair_id, iris_id, face_id),
              ([t.tex_id for t in t1[-3:]], all(lo <= t.tex_id < hi for t in t1[-3:])), ([hair_id, iris_id, face_id], True))
        face = nut.decode(d1, t1[-1])[..., :3].astype(float)
        main, shade = M.SILVER['hair']
        check('%s: the mustache / eyebrows\' silver (v4): darker than v3\'s flat %g (at most %g x the sheen: FACE_TONE %g), '
              'grey (blue >= red), with the strands\' shading (not flat)' % (c, main, main * M.FACE_TONE, M.FACE_TONE),
              (bool(face.max() <= 255 * main * M.FACE_TONE * max(M.SHEEN) + 4), bool((face[..., 2] >= face[..., 0] - 2).all()),
               bool(face.std() > 1.0)), (True, True, True))
        hair = nut.decode(d1, t1[-3]).reshape(-1, 4).astype(float)
        main, _shade = M.SILVER['hair']
        want = [round(255 * main * x) for x in M.SHEEN]
        check('%s: the silver hair %s (SILVER hair %g x the sheen, BC1 within 4)' % (c, want, main),
              bool((abs(hair[:, :3] - want) <= 4).all()), True)
        src_iris = nut.decode(d0, [t for t in t0 if t.tex_id & 0xFF == M.SRC_TEX['iris']][0])
        iris = nut.decode(d1, t1[-2])
        a = iris[..., 3] > 128
        rgb = iris[a][:, :3].astype(float)
        rgb = rgb[rgb.max(1) > 40]                 # the pupil's near-black left out (BC rounding there)
        sat = (rgb.max(1) - rgb.min(1)) / np.maximum(rgb.max(1), 1)
        da = abs(iris[..., 3].astype(int) - src_iris[..., 3])
        check('%s: the silver iris: the alpha as Mario\'s (BC3: mean under 1, edges within 24), grey with the blue-white '
              'sheen only (saturation under 0.25 incl. BC rounding on the dark ring, blue >= red everywhere), its ring '
              'up to SILVER iris %g' % (c, M.SILVER['iris'][0]),
              (bool(da.mean() < 1 and da.max() <= 24), bool(sat.max() < 0.25 and (rgb[:, 2] >= rgb[:, 0]).all()),
               abs(np.percentile(rgb.max(1), 90) / 255 - M.SILVER['iris'][0] * M.SHEEN[2]) < 0.12), (True, True, True))
        for pk in M.PACS:
            pd0, pd1 = open(os.path.join(src, pk), 'rb').read(), open(os.path.join(dst, pk), 'rb').read()
            e0, e1 = T.pac_entries(pd0), T.pac_entries(pd1)
            bad, n = [], 0
            for (na, o, sz), (nb, o2, sz2) in zip(e0, e1):
                x0, x1 = pd0[o:o + sz], pd1[o2:o2 + sz2]
                if na != nb or not na.endswith('.mta'):
                    if na != nb or x0 != x1:
                        bad.append(na)
                    continue
                r0, r1 = mta.read(x0), mta.read(x1)
                want = []
                vis0 = {v['name']: [(f, st) for f, st, _ in v['keys']] for v in r0['vis']}
                hidden = any(k in na for k in M.OVERLAY_HIDDEN)
                for v in r0['vis']:
                    want.append((v['name'], v['keys']))
                    for k, (orig, cp) in M.MESHES.items():
                        if v['name'] == orig:
                            if hidden:
                                kk = [(0, 0, 0)]
                            elif k == 'eye':
                                kk = list(v['keys'])
                            else:
                                last = max(f for f, _s, _x in v['keys'])
                                kk = [(0, 1, 0)] + ([(last, 1, 0)] if last > 0 else [])
                            want.append((cp, kk))
                            n += 1
                want += [(nm, [(f, st, 0) for f, st in k]) for nm, k in M.overlay_tracks(na, vis0, ovs)]
                vo = struct.unpack('>I', x0[0x24:0x28])[0]
                if r0['mats'] != r1['mats'] or [(v['name'], v['keys']) for v in r1['vis']] != want or \
                        x0[:0x20] + x0[0x24:vo] != x1[:0x20] + x1[0x24:vo]:
                    bad.append(na)
            check('%s %s: v4: each full hair / eye track followed by its copy\'s (the eye copy = his eyes\' keys, the full '
                  'hair\'s shown all through; hidden all through in the entry / win / lose / display motions) (%d added); '
                  'every other byte before the tracks, the materials and the tracks kept' % (c, pk, n), bad, [])
        pk = open(os.path.join(dst, M.PACS[0]), 'rb').read()
        tr = {}
        for na, o, sz in T.pac_entries(pk):
            if na.endswith('.mta'):
                tr[na] = {v['name']: [(f, st) for f, st, _ in v['keys']] for v in mta.read(pk[o:o + sz])['vis']}
        ap = tr['FitMarioBodyMainJ01AppealS.mta']
        check('%s: the overlays follow their faces (the side taunt: FaceN\'s mustache / eyebrows as FaceN, Furafura\'s '
              'mustache and Escape\'s eyebrows as Escape, 17-72)' % c,
              [ap.get('Mario_FaceNMustacheUI_VIS_O_OBJ'), ap.get('Mario_FaceNBrowsUI_VIS_O_OBJ'),
               ap.get('Mario_FurafuraMustacheUI_VIS_O_OBJ'), ap.get('Mario_EscapeBrowsUI_VIS_O_OBJ')],
              [ap['Mario_FaceN_VIS_O_OBJ']] * 2 + [ap['Mario_Escape_VIS_O_OBJ']] * 2)
        hid = [na for na in tr if any(k in na for k in M.OVERLAY_HIDDEN) and tr[na] and
               any(tr[na].get(o) != [(0, 0)] for o in B.OVERLAYS)]
        check('%s: the overlays hidden all through the entry / win / lose / display motions' % c, hid, [])
        dm = [e for e in T.pac_entries(pk) if e[0] == 'default.mta']
        if dm:
            x = open(os.path.join(dst, M.PACS[0]), 'rb').read()[dm[0][1]:dm[0][1] + dm[0][2]]
            vis = {v['name']: v['keys'] for v in mta.read(x)['vis']}
            check('%s: v4 default.mta: the eye copy follows his eyes\' track, the full hair\'s copy shown (untransformed '
                  'they are hidden by their set state: Persist 2)' % c,
                  [vis.get(M.MESHES[k][1]) for k in ('nohat', 'eye')],
                  [[(0, 1, 0)] + ([(max(f for f, _s, _x in vis[M.MESHES['nohat'][0]]), 1, 0)]
                                  if max(f for f, _s, _x in vis[M.MESHES['nohat'][0]]) > 0 else []),
                   vis[M.MESHES['eye'][0]]])


# ---------------------------------------------------------------- v5: the game's own script-binding decision (unicorn)
DESC_GETTER = 0x02E4313C          # (mgr, kind) -> the kind's descriptor (+4 its motion info: +0 the motion table)
MOTION_LINK = 0x02C639E0          # MotionModule vt +0x1F4 (this, motion): the entry's flag 0x8 -> the script module's
                                  # +0x2E (vt +0x4C's r7, 0x02C5E5EC): 0x027606C0 then binds the LINKED object's scripts,
                                  # or clears every body agent when there is no link 0 (0x02760750)
PUMP_POS = 0x02F11C0C             # the pump's per-frame placement: status 0x152 / 0x157-0x159 -> 0x02F16864
PUMP_POS_BODY = 0x02F16864
STATUS_CB = 0x02F169D0            # Mario's status-change callback (vtable 0x101393C4 + 0x14): the pump article / flag
                                  # 0x20000078 / [acc + 0xA0] vt +0x1DC / +0x1E4 (0x1A) for 0x152 / 0x157-0x159


def native_tests(exe):
    """the exe's own code: (1) the motion -> link-kind script decision for every UI motion (body scripts kept: 0);
    (2) Mario's status-keyed native code (the pump's placement, the status-change callback) never acts on 0x155, the UI
    statuses since v5, and does on v1-v4's 0x157 / 0x158 (controls)"""
    from kind_expand_test import Emu, REGS  # noqa: F401
    from unicorn.ppc_const import UC_PPC_REG_MSR
    import kind_expand as K
    import outline_shell_cave as OSC
    img = K.Image(exe)
    check('v6: the exe\'s Outline_Shell shows its colour (exe_v46z_outline5\'s hdrRange scaling: the glow\'s blue-violet band '
          'would come out white on exe_v46z_outline4)', OSC.coloured(img.w), True)
    e = Emu(exe)
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # floating point on
    desc = e.call(DESC_GETTER, 0, M_KIND)
    table = e.w(e.w(desc + 4))
    count = e.w(e.w(desc + 4) + 4)
    check('native: kind 0x%X\'s descriptor and motion table found (%d motions)' % (M_KIND, count),
          (e.w(desc), count > 0x249), (M_KIND, True))
    mm = e.alloc(0x40, b'\0')
    e.setw(mm + 0x1C, table)
    e.setw(0x10492CB4, 1)                               # its static default's guard (its init calls an import)
    got = {}
    for mot in (B.MOT_FORM, B.MOT_STRIKE, B.MOT_DODGE, B.MOT_SS, B.MOT_ESCAPE_N, 0x229, 0x239, 0x1BE):
        got[mot] = e.call(MOTION_LINK, mm, mot)
    check('native: the game\'s link-kind decision (0x02C639E0) for SpecialLwLight / Heavy, SpecialAirLwLight / Heavy, '
          'EscapeN, Fake Death\'s / Sledgehammer\'s: 0 (the body\'s own scripts bound); a thrown motion (0x1BE): 1',
          got, {B.MOT_FORM: 0, B.MOT_STRIKE: 0, B.MOT_DODGE: 0, B.MOT_SS: 0, B.MOT_ESCAPE_N: 0, 0x229: 0, 0x239: 0,
                0x1BE: 1})
    # the pump's placement: which statuses reach its body
    hit = []
    e.stub(PUMP_POS_BODY, lambda em: hit.append(1))
    f = e.alloc(0x7400, b'\0')
    stm = e.alloc(0x80, b'\0')
    e.setw(f + 0x7264, stm)
    wpn = e.alloc(0x40, b'\0')
    e.setw(wpn + 0x28, f)
    reach = []
    for st in (0x152, 0x153, 0x154, 0x155, 0x156, 0x157, 0x158, 0x159):
        e.setw(stm + 0x48, st)
        del hit[:]
        e.call(PUMP_POS, 0, wpn)
        if hit:
            reach.append(st)
    check('native: the pump\'s placement (0x02F11C0C) acts in 0x152 / 0x157-0x159, never in 0x155 (the UI statuses, v5)',
          (reach, C.ST_UI in reach, C.ST_DODGE in reach), ([0x152, 0x157, 0x158, 0x159], False, False))
    # the status-change callback
    calls = []

    def fn(name, ret=0):
        a = e.alloc(8, b'\0')
        e.stub(a, lambda em: (calls.append((name, em.r(4))), ret)[1])
        return a

    def vt(entries):
        t = e.alloc(0x400, b'\0')
        for off, a in entries.items():
            e.setw(t + off, a)
        return t
    e.stub(0x02BF2108, lambda em: 0)                     # the handle
    e.stub(0x02BEF604, lambda em: M_KIND)                # its kind (8 = Kirby takes the other status set)
    e.stub(0x02F1124C, lambda em: calls.append(('flag 0x20000078', em.r(4))))
    acc = e.alloc(0x200, b'\0')
    cur = {'st': 0}
    stmod = e.alloc(0x10, b'\0')
    e.setw(stmod, vt({0x8C: fn('status')}))
    e.setw(acc + 0x20, stmod)
    art = e.alloc(0x10, b'\0')
    e.setw(art, vt({0xFC: fn('article exists'), 0x13C: fn('article get'), 0xEC: fn('article remove')}))
    e.setw(acc + 0x4C, art)
    em_ = e.alloc(0x10, b'\0')
    e.setw(em_, vt({0x1DC: fn('0xA0 vt+0x1DC'), 0x1E4: fn('0xA0 vt+0x1E4')}))
    e.setw(acc + 0xA0, em_)
    e.setw(acc, 0x00010012)
    res = {}
    status_fn = e.w(e.w(stmod) + 0x8C)
    for old, new in ((0, 0x155), (0x155, 0), (0x155, 0xE), (0x155, 0x1B), (0x155, 0x155), (0, 0x157), (0x157, 0),
                     (0x158, 0)):
        e.stub(status_fn, lambda em, o=old: (calls.append(('status', 0)), o)[1])
        del calls[:]
        e.call(STATUS_CB, 0, acc, new)
        res[(old, new)] = sorted({c[0] for c in calls} - {'status'})
    check('native: Mario\'s status-change callback (0x02F169D0) does nothing for 0x155 in or out (the UI statuses, v5)',
          [res[k] for k in ((0, 0x155), (0x155, 0), (0x155, 0xE), (0x155, 0x1B), (0x155, 0x155))], [[]] * 5)
    check('  ... and acts on v1-v4\'s 0x157 / 0x158 (leaving them: the pump article removed, effect kind 0x1A, flag '
          '0x20000078; controls)', [bool(res[k]) for k in ((0, 0x157), (0x157, 0), (0x158, 0))], [False, True, True])


M_KIND = 0x41


def ids_from_json(out):
    import json
    js = json.load(open(os.path.join(out, 'ultrainstinct.json')))
    B.FX_IDS.update({k: int(v, 16) for k, v in js['fx_ids'].items()})
    B.SE_IDS.update({k: int(v, 16) for k, v in js['se_ids'].items()})
    B.OVERLAYS[:] = js['silver']['overlays']
    B.MESH_INDEX.clear()
    B.MESH_INDEX.update(js.get('mesh_index', {}))


INSTALL_DIRS = ('fighter', 'sound', 'param')


def package_tests(zpath, out, ts_out):
    """ui4 (v5): the package installs complete over any earlier Ultra Instinct install: every file the build makes that
    differs from Time Skip v10's (or that it lacks) is in INSTALL_TO_data/ byte for byte (v3 / v4 shipped only what they
    changed, and the user's install turned out to hold an older effect.bin / .efc: S4UB found no effect script for
    SpecialAirLwHeavy, which the build's effect.bin has); nothing wrapped in a folder named like a fighter; both
    executables"""
    import zipfile
    z = zipfile.ZipFile(zpath)
    names = set(z.namelist())
    want = []
    for d in INSTALL_DIRS:
        for root, _ds, fs in os.walk(os.path.join(out, d)):
            for fn in fs:
                rel = os.path.relpath(os.path.join(root, fn), out)
                old = os.path.join(ts_out, rel)
                b = open(os.path.join(out, rel), 'rb').read()
                if not os.path.exists(old) or open(old, 'rb').read() != b:
                    want.append((rel, b))
    missing = [r for r, b in want if 'INSTALL_TO_data/' + r not in names]
    differ = [r for r, b in want if 'INSTALL_TO_data/' + r in names and z.read('INSTALL_TO_data/' + r) != b]
    check('package: every file the build changes over Time Skip v10\'s is in INSTALL_TO_data/ (%d files: the scripts, '
          'the .efc / .ptcl, motions, the bank / soundlabeltable, the MSC, the models)' % len(want), (missing, differ),
          ([], []))
    for must in ('script/animcmd/body/effect.bin', 'script/animcmd/body/sound.bin', 'effect/supamario/supamario.010d0000.efc'):
        check('  it ships %s (v3 / v4 did not)' % must, 'INSTALL_TO_data/fighter/supamario/' + must in names, True)
    tops = sorted({n.split('/')[0] for n in names if '/' in n})
    check('package: top folders INSTALL_TO_data, INSTALL_TO_code, TEST_ONLY_INSTALL_TO_code (and the Sm4shCommand '
          'folder); nothing wrapped in a fighter / game folder name',
          [t for t in tops if not (t in ('INSTALL_TO_data', 'INSTALL_TO_code', 'TEST_ONLY_INSTALL_TO_code') or
                                   t.startswith('Sm4shCommand_v'))], [])
    data_tops = sorted({n.split('/')[1] for n in names if n.startswith('INSTALL_TO_data/') and n.count('/') > 1})
    check('  INSTALL_TO_data/ holds the data folders themselves', [t for t in data_tops if t not in INSTALL_DIRS], [])
    check('  both executables and the README', [n for n in ('INSTALL_TO_code/cross_f.rpx',
                                                            'TEST_ONLY_INSTALL_TO_code/cross_f.rpx', 'README.txt')
                                               if n not in names], [])


def package_since_tests(zpath, out, prev_out):
    """v6: a package over the previous one (prev_out: its build output): INSTALL_TO_data/ holds exactly the files the
    build changes since then, byte for byte; nothing wrapped in a fighter / game folder; both executables (the exe
    changed: exe_v46z_ui5) and the README"""
    import zipfile
    z = zipfile.ZipFile(zpath)
    names = set(z.namelist())
    want = {}
    for d in INSTALL_DIRS:
        for root, _ds, fs in os.walk(os.path.join(out, d)):
            for fn in fs:
                rel = os.path.relpath(os.path.join(root, fn), out)
                old = os.path.join(prev_out, rel)
                b = open(os.path.join(out, rel), 'rb').read()
                if not os.path.exists(old) or open(old, 'rb').read() != b:
                    want['INSTALL_TO_data/' + rel] = b
    data = {n for n in names if n.startswith('INSTALL_TO_data/') and not n.endswith('/')}
    check('package (v6): INSTALL_TO_data/ = the %d files changed since the previous build (%s), byte for byte' % (
        len(want), ', '.join(sorted(os.path.basename(n) for n in want))),
          (sorted(data ^ set(want)), [n for n in want if n in data and z.read(n) != want[n]]), ([], []))
    tops = sorted({n.split('/')[0] for n in names if '/' in n})
    check('package: top folders INSTALL_TO_data, INSTALL_TO_code, TEST_ONLY_INSTALL_TO_code (and the Sm4shCommand '
          'folder); nothing wrapped in a fighter / game folder name',
          [t for t in tops if not (t in ('INSTALL_TO_data', 'INSTALL_TO_code', 'TEST_ONLY_INSTALL_TO_code') or
                                   t.startswith('Sm4shCommand_v'))], [])
    data_tops = sorted({n.split('/')[1] for n in names if n.startswith('INSTALL_TO_data/') and n.count('/') > 1})
    check('  INSTALL_TO_data/ holds the data folders themselves', [t for t in data_tops if t not in INSTALL_DIRS], [])
    exes = [n for n in ('INSTALL_TO_code/cross_f.rpx', 'TEST_ONLY_INSTALL_TO_code/cross_f.rpx') if n in names]
    check('  the README; both executables or none (v8: the exe unchanged since the previous package, exe_v46z_ui6)',
          ('README.txt' in names, len(exes) in (0, 2)), (True, True))


def main():
    a = sys.argv[1:]
    exe = None
    if '--exe' in a:
        i = a.index('--exe')
        exe = a[i + 1]
        del a[i:i + 2]
    pkg = None
    if '--package' in a:
        i = a.index('--package')
        pkg = a[i + 1]
        del a[i:i + 2]
    since = None
    if '--since' in a:
        i = a.index('--since')
        since = a[i + 1]
        del a[i:i + 2]
    if len(a) != 3:
        sys.exit(__doc__)
    out, ts_out, base = a
    global BASE_DIR
    BASE_DIR = base
    ids_from_json(out)
    r = Run(os.path.join(out, 'fighter', 'supamario', 'script', 'msc', 'supamario.mscsb'))
    trigger_tests(r)
    form_tests(r)
    counter_tests(r)
    dodge_tests(r)
    escape_tests(r)
    shape_tests(r)
    mode_tests(r)
    reset_tests(r)
    ss_tests(r)
    script_tests(out, ts_out)
    motion_tests(out, ts_out)
    effect_tests(out, ts_out)
    aura_tests(out, ts_out)
    aura_v5_tests(out, base)
    aura_v6_tests(out)
    model_tests(out, base)
    if exe:
        native_tests(exe)
    if pkg and since:
        package_since_tests(pkg, out, since)
    elif pkg:
        package_tests(pkg, out, ts_out)
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
