#!/usr/bin/env python3
"""Ultra Instinct v1 (Supamario's gimmick) offline checks: the compiled MSC (ui_* through func_82's hook and statuses
0x157 / 0x158's functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built
scripts, motions, effects and sounds.

  python3 -I tools/supamario_ui_test.py BUILD_OUT_DIR TIMESKIP_OUT_DIR SUPAMARIO_DIR

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
import supamario_ui_build as B  # noqa: E402
import supamario_ui_cave as C  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


TIMERS = (C.V_FORM, C.V_DODGE_R, C.V_DODGE_L, B.V_AURA)


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
        self.vx = 0.0
        self.shield = 0

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
        if status_funcs and g.status in (C.ST_UI, C.ST_DODGE) and g.req is None:
            self.call(vm, 'ui_loop' if g.status == C.ST_UI else 'ui_dodge_loop')
        vm.g[18] = 2 if g.air else 0
        if g.req is not None and g.req != g.status:
            self.change(vm, g, g.req)

    def change(self, vm, g, st):
        if g.status == C.ST_UI:
            self.call(vm, 'func_2283')
        elif g.status == C.ST_DODGE:
            self.call(vm, 'func_2284')
        g.status = st
        g.sw, g.flags = {}, set()
        vm.g[18] = 2 if g.air else 0
        if st == C.ST_UI:
            self.call(vm, 'func_2253')
            self.call(vm, 'func_2268')
        elif st == C.ST_DODGE:
            self.call(vm, 'func_2254')
            self.call(vm, 'func_2272')


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
    check('the transformation: status 0x157 asked on the first frame', start, 1)
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
    check('no hitbox (the transformation\'s game script is empty)', True, True)
    r.frame(vm, g)
    aura = [e for e in g.ev('effect', end + 1)]
    check('the aura made right after (4 following requests 0x2717, the three old ones ended first; v3: 0x2717, the '
          'vanilla following request the Kamehameha uses, not v1 / v2\'s 0x2730: the crash fix)',
          sorted((e[2], e[3]) for e in aura),
          sorted([(0x2723, B.fx_id('aura_hip')), (0x2723, B.fx_id('aura_head')), (0x2723, B.fx_id('aura_foot')),
                  (0x2717, B.fx_id('aura_hip')), (0x2717, B.fx_id('aura_head')), (0x2717, B.fx_id('aura_foot')),
                  (0x2717, B.fx_id('aura_foot'))]))
    check('  on HipN / HeadN / LFootJ / RFootJ', sorted(e[4] for e in aura if e[2] == 0x2717),
          sorted([B.BONES['HipN'], B.BONES['HeadN'], B.BONES['LFootJ'], B.BONES['RFootJ']]))
    head_up = round(0.2 * B.METRE, 3)
    check('  their arguments (id, bone, x, y, z, rx, ry, rz, size, flag 0): the head 0.2 m up, the sizes %g / %g' % (
        B.SCALE, round(0.8 * B.SCALE, 3)),
          sorted(tuple(round(float(x), 3) for x in e[5][1:]) for e in aura if e[2] == 0x2717),
          sorted([(B.fx_id('aura_hip'), B.BONES['HipN'], 0, 0, 0, 0, 0, 0, B.SCALE, 0),
                  (B.fx_id('aura_head'), B.BONES['HeadN'], 0, head_up, 0, 0, 0, 0, B.SCALE, 0),
                  (B.fx_id('aura_foot'), B.BONES['LFootJ'], 0, 0, 0, 0, 0, 0, round(0.8 * B.SCALE, 3), 0),
                  (B.fx_id('aura_foot'), B.BONES['RFootJ'], 0, 0, 0, 0, 0, 0, round(0.8 * B.SCALE, 3), 0)]))
    check('  no 0x2730 call left (v1 / v2\'s untested op)', [e for e in g.ev('effect') if e[2] == 0x2730], [])
    for k in range(int(B.AURA_EVERY)):
        r.frame(vm, g)
    again = [e for e in g.ev('effect', end + 2) if e[2] == 0x2717]
    check('  made again after %d frames' % B.AURA_EVERY, len(again), 4)
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


def dodge_run(r, status=0, timer=C.V_DODGE_R, form=2000.0, air=False, frames=30):
    g = Game(status=status, damage=150.0, air=air, x=0.0)
    g.vars[C.V_FORM] = form
    g.vars[B.V_AURA] = 999.0
    g.vars[timer] = 4.0
    vm = r.vm(g)
    xs = []
    for _ in range(frames):
        r.frame(vm, g)
        xs.append((g.status, round(g.vx, 3)))
    return g, vm, xs


def dodge_tests(r):
    for st, name in ((0, 'Wait'), (1, 'Walk'), (2, 'WalkBrake'), (0x11, 'Squat'), (0x12, 'SquatWait'), (0x15, 'SquatRv')):
        g, vm, xs = dodge_run(r, status=st)
        check('dodge: transformed, %s, TIMER_1 (attacker right) -> status 0x158' % name,
              [e[2] for e in g.ev('status')][:1], [C.ST_DODGE])
    g, vm, xs = dodge_run(r)
    start = [e for e in g.ev('status') if e[2] == C.ST_DODGE][0][0]
    check('  its motion 0x241 (SpecialAirLwLight)', [e[2] for e in g.ev('motion')], [B.MOT_DODGE])
    check('  intangible %d frames at its start' % B.DODGE_INV, [e[3] for e in g.ev('set') if e[2] == 0x0F00011B],
          [float(B.DODGE_INV)])
    check('  the signals cleared', (g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]), (0.0, 0.0))
    moving = [v for s, v in xs if s == C.ST_DODGE]   # (the first: the status's frame 0, its init)
    check('  away from the attacker: %g a frame to the left for %d frames, then still' % (B.DODGE_V, B.DODGE_MOVE),
          moving[:B.DODGE_MOVE + 1], [-B.DODGE_V] * B.DODGE_MOVE + [0.0])
    end = [e for e in g.ev('status') if e[2] == 0][0][0]
    check('  Wait at its end (%d frames)' % B.DODGE_N, end - start, B.DODGE_N - 1)
    g, vm, xs = dodge_run(r, timer=C.V_DODGE_L)
    check('dodge: the attacker to his left -> to the right', [v for s, v in xs if s == C.ST_DODGE][0], B.DODGE_V)
    for what, kw in (('not transformed (TIMER_0 0)', dict(form=0.0)),
                     ('in Dash (3)', dict(status=3)), ('in the air (Fall)', dict(status=0xE, air=True)),
                     ('shielding (0x1C)', dict(status=0x1C))):
        g, vm, xs = dodge_run(r, frames=2, **kw)
        check('dodge: %s -> no dodge' % what, [e[2] for e in g.ev('status') if e[2] == C.ST_DODGE], [])
    g, vm, xs = dodge_run(r, status=3, frames=1)
    check('  a signal in Dash is dropped (TIMER_1 / 2 back to 0)', (g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]), (0.0, 0.0))
    g, vm, xs = dodge_run(r, frames=40)
    g.vars[C.V_DODGE_L] = 4.0
    for _ in range(3):
        r.frame(vm, g)
    check('no cooldown: a second signal right after the first dodge dodges again',
          len([e for e in g.ev('status') if e[2] == C.ST_DODGE]), 2)


def reset_tests(r):
    for st, name in ((0xB1, 'Dead'), (0xB2, 'Rebirth'), (0x14F, 'Entry')):
        g = Game(status=st, damage=0.0)
        g.vars.update({C.V_FORM: 2000.0, C.V_DODGE_R: 3.0, C.V_DODGE_L: 2.0})
        vm = r.vm(g)
        r.frame(vm, g)
        check('reset: %s -> TIMER_0-2 0, the aura ended' % name,
              ((g.vars[C.V_FORM], g.vars[C.V_DODGE_R], g.vars[C.V_DODGE_L]),
               sorted(e[3] for e in g.ev('effect') if e[2] == 0x2723)),
              ((0.0, 0.0, 0.0), sorted([B.fx_id('aura_hip'), B.fx_id('aura_head'), B.fx_id('aura_foot')])))
    g = Game(status=0x0, damage=150.0)
    vm = r.vm(g)
    r.frame(vm, g)
    check('after a reset: at 150% in Wait he transforms again (a new stock)', [e[2] for e in g.ev('status')], [C.ST_UI])
    g = Game(status=0x45, damage=150.0)
    g.vars[C.V_FORM] = 1000.0
    vm = r.vm(g)
    r.frame(vm, g)
    check('the transformation\'s status left some other way: transformed (2000)', g.vars[C.V_FORM], 2000.0)


def ss_run(r, rec=None, at=10, frames=60, form=2000.0, air_target=False):
    """the grounded down special (status 0x155's main func_2265, its loop, its end func_2282)"""
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
    cams = [nm(c) for p in f for sname in B.SCRIPT.values() for c in f[p].script(sname) if 'camera' in nm(c).lower()]
    check('no camera command in any Ultra Instinct script (the user)', cams, [])
    check('the transformation / the dodge / Secret Sensation\'s stance: no hitbox (v3: the transformation\'s game script '
          'only the silver swap)',
          [nm(c) for s in ('speciallwlight', 'specialairlwlight', 'specialairlwheavy') for c in f['game'].script(s)],
          ['FRAME'] + ['Mesh_Visibility'] * 5 + ['Script_End', 'Script_End', 'Script_End'])
    eff = [c for c in f['effect'].script('speciallwlight') if 'graphic' in nm(c).lower()]
    check('the transformation\'s effects: start, the aura (7 parts), the burst',
          [c.params[0] for c in eff], [B.fx_id('start')] + [B.fx_id(k) for k in ('aura_hip', 'aura_chest', 'aura_head',
                                                                                'aura_foot', 'aura_foot', 'aura_hand',
                                                                                'aura_hand')] + [B.fx_id('burst')])
    snd = [(nm(c), c.params) for c in f['sound'].script('speciallwlight')]
    check('its sounds: Start at %d (XV2 22), Success at %d (XV2 205)' % (B.SND_START, B.SND_SUCCESS), snd,
          [('FRAME', [float(B.SND_START)]), ('Sound_Effect', [B.SE_IDS['ui_start']]), ('FRAME', [float(B.SND_SUCCESS)]),
           ('Sound_Effect', [B.SE_IDS['ui_success']]), ('Script_End', [])])
    for s in ('speciallwheavy', 'specialairlwlight'):
        check('%s: the vanish sound / effect first' % s,
              ([c.params[0] for c in f['sound'].script(s) if nm(c) == 'Sound_Effect'][:1],
               [c.params[0] for c in f['effect'].script(s) if 'graphic' in nm(c).lower()][:1]),
              ([B.SE_IDS['ui_vanish']], [B.fx_id('vanish')]))
    skip = {acmd.crc(n) for n in B.SCRIPT.values()} | {acmd.crc(n) for n in B.silver_scripts()}
    other = []
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])]:
                other.append((p, hex(h)))
    check('every other script as Time Skip v10\'s build', other, [])
    silver_script_tests(f, b)


def mv(c):
    """a Mesh_Visibility command -> (mesh name, visible, persist)"""
    import mesh_vis_cave as MV
    names = {MV.crc32(n): n for k in B.SILVER_MESHES.values() for n in k}
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
    """v3: the silver hair / eyes swap (Mesh_Visibility) in the game scripts"""
    H, N, E = (B.SILVER_MESHES[k] for k in ('hair', 'nohat', 'eye'))
    on = [(H[0], 0, 1), (N[0], 0, 1), (E[0], 0, 1), (H[1], 1, 1), (E[1], 1, 1)]
    off = sorted((m, 2, 0) for k in (H, N, E) for m in k)
    g = f['game']
    got = [(fr, mv(c)) for fr, c in at_frames(g.script('speciallwlight')) if c.name == 'Mesh_Visibility']
    check('v3: the transformation\'s burst (%d): his hair / full hair / eyes hidden, the silver hair / eyes shown, '
          'Persist 1' % B.FX_BURST_AT, got, [(float(B.FX_BURST_AT), x) for x in on])
    check('v3: the burst is XV2\'s frame 220', B.FX_BURST_AT, 220)
    got = [(fr, mv(c)) for fr, c in at_frames(g.script('speciallwheavy')) if c.name == 'Mesh_Visibility']
    check('v3: the counter (transformed afterwards): the same swap at its white body\'s end (%d)' % B.CNT_END, got,
          [(float(B.CNT_END), x) for x in on])
    w = g.script('wait1')
    names = [c.name for c in w]
    check('v3: Wait1 (no game script before): transformed (TIMER_0 > %g) the swap again, else every override ended' %
          B.UI_TRANSFORMED_OVER, names, ['Float_Var_Compare', 'True'] + ['Mesh_Visibility'] * 5 +
          ['Float_Var_Compare', 'True'] + ['Mesh_Visibility'] * 6 + ['Script_End'])
    if len(w) == 17:
        check('  its conditions: TIMER_0 (0x%X) > / <= %g; the True blocks\' sizes' % (C.V_FORM, B.UI_TRANSFORMED_OVER),
              [(w[0].params, w[1].params), (w[7].params, w[8].params)],
              [([C.V_FORM, 5, B.UI_TRANSFORMED_OVER], [2 + 5 * 5]), ([C.V_FORM, 2, B.UI_TRANSFORMED_OVER], [2 + 6 * 5])])
        check('  the blocks: the swap / the restore', ([mv(c) for c in w[2:7]], sorted(mv(c) for c in w[9:15])), (on, off))
    for e in ('entryl', 'entryr'):
        check('v3: %s: every swap override ended at frame 0 (a new match / stock: his own hair and eyes)' % e,
              sorted((fr, mv(c)) for fr, c in at_frames(g.script(e)) if c.name == 'Mesh_Visibility'),
              [(0.0, x) for x in off])
    for a in ('appealsl', 'appealsr'):
        got = [(fr, c.name, mv(c) if c.name == 'Mesh_Visibility' else c.params) for fr, c in at_frames(g.script(a))
               if c.name != 'Script_End']
        check('v3: %s (the cap off 17-72: Mario_Nohat on, Mario_Hair off): the silver full hair shown 17-72 while '
              'transformed (Persist 0)' % a, got,
              [(17.0, 'Float_Var_Compare', [C.V_FORM, 5, B.UI_TRANSFORMED_OVER]), (17.0, 'True', [7]),
               (17.0, 'Mesh_Visibility', (N[1], 1, 0)), (72.0, 'Mesh_Visibility', (N[1], 2, 0))])
    for p in f:
        for n in B.silver_scripts():
            if p != 'game':
                check('v3: %s %s unchanged' % (p, n), [(c.ident, c.params) for c in f[p].script(n) or []],
                      [(c.ident, c.params) for c in b[p].script(n) or []])
    check('v3: no Mesh_Visibility override ends the whole object (Mesh -1: other moves\' overrides kept)',
          [n for p in f for h, sc in f[p].scripts.items() for c in sc if c.name == 'Mesh_Visibility' and
           c.params[1] == 0xFFFFFFFF], [])


def motion_tests(out, ts_out):
    for part in ('main', 'mariopt1', 'lhand', 'rhand'):
        new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        old = dict(omo.pac_read(os.path.join(ts_out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        diff = sorted(n.split('D03')[-1] for n in new if new[n] != old.get(n))
        check('%s.pac: only the four slots changed' % part, diff, sorted([A.DODGE, A.STRIKE, A.FORM, A.SS]))
        fr = {m: omo.Omo(new[[n for n in new if n.endswith('D03' + m)][0]]).frames for m in A.MOTIONS}
        check('%s.pac: 325 / 349 / 16 / 45 frames' % part, fr, {A.FORM: 325, A.STRIKE: 349, A.DODGE: 16, A.SS: 45})


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
    """v3: the aura's sets turned to the clip's lavender (B.AURA_HUE, saturation x B.AURA_SAT); the others not"""
    import colorsys
    import ptcl
    d = os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    aura = {'PtcSupamarioUi' + x[2][:-4] for x in B.FX if x[0] in B.AURA_SETS}
    hues, sats, other = set(), [], set()
    for i in range(len(p.sets)):
        name = p.set_name(i)
        if not name.startswith('PtcSupamarioUi'):
            continue
        for e in p.sets[i]['emitters']:
            if e['data'] is None:
                continue
            for t in (0, 1):
                for k in p.color_keys(e['data'], t):
                    v = max(k[:3])
                    if v <= 0:
                        continue
                    h, sa, _ = colorsys.rgb_to_hsv(*[c / v for c in k[:3]])
                    if name in aura:
                        if sa > 1e-4:
                            hues.add(round(h * 360))
                        sats.append(sa)
                    elif sa > 0.05:
                        other.add(round(h * 360))
    check('v3: the aura\'s 5 sets (848\'s loops) all lavender: hue %g deg (the clip 281-287)' % B.AURA_HUE, hues,
          {round(B.AURA_HUE)})
    check('  their saturations at most %g (XV2\'s x %g)' % (B.AURA_SAT, B.AURA_SAT), max(sats) <= B.AURA_SAT + 1e-4, True)
    check('  the other UI sets (start, burst, vanish) keep XV2\'s colours (none at %g deg)' % B.AURA_HUE,
          round(B.AURA_HUE) in other, False)
    check('  the tint of a blue (0.45, 0.62, 1.0) -> lavender', tuple(round(x, 3) for x in B.lavender((0.45, 0.62, 1.0))),
          (0.832, 0.643, 1.0))


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
        check('%s model.nud: the meshes as before, then the 3 copies' % c, [m.name for m in new],
              [m.name for m in old] + [M.MESHES[k][1] for k in ('hair', 'nohat', 'eye')])
        same = all(a.name == b.name and a.bone == b.bone and len(a.polygons) == len(b.polygons) and all(
            (pa.idx == pb.idx).all() and (pa.pos is None or (pa.pos == pb.pos).all()) and
            [x.textures for x in pa.materials] == [x.textures for x in pb.materials] and
            [x.props for x in pa.materials] == [x.props for x in pb.materials]
            for pa, pb in zip(a.polygons, b.polygons)) for a, b in zip(old, new))
        check('%s: every existing mesh unchanged (geometry, materials, textures)' % c, same, True)
        hair_id, iris_id = M.tex_ids(nn)
        by = {m.name: m for m in new}
        for k, want in (('hair', {0: hair_id}), ('nohat', {0: hair_id}), ('eye', {0: iris_id, 1: iris_id})):
            a, b = by[M.MESHES[k][0]], by[M.MESHES[k][1]]
            geo = (a.bone, a.bind, len(a.polygons)) == (b.bone, b.bind, len(b.polygons)) and all(
                (pa.idx == pb.idx).all() and (pa.pos == pb.pos).all() and (pa.nrm is None or (pa.nrm == pb.nrm).all())
                and all((u == v).all() for u, v in zip(pa.uvs, pb.uvs)) for pa, pb in zip(a.polygons, b.polygons))
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
        mo, mn = nud.read(os.path.join(src, 'metal.nud')), nud.read(os.path.join(dst, 'metal.nud'))
        mb = {m.name: m for m in mn}
        check('%s metal.nud: the 3 copies with the metal textures (the same mesh list as model.nud)' % c,
              ([m.name for m in mn][len(mo):], [[t['hash'] for t in mb[M.MESHES[k][1]].polygons[0].materials[0].textures]
                                               for k in M.MESHES]),
              ([M.MESHES[k][1] for k in ('hair', 'nohat', 'eye')],
               [[t['hash'] for t in mb[M.MESHES[k][0]].polygons[0].materials[0].textures] for k in M.MESHES]))
        d0, t0 = nut.load(os.path.join(src, 'model.nut'))
        d1, t1 = nut.load(os.path.join(dst, 'model.nut'))
        kept = len(t1) == len(t0) + 2 and all(
            a.tex_id == b.tex_id and d0[a.data_off:a.data_off + a.image_size] == d1[b.data_off:b.data_off + b.image_size]
            and d0[a.mip_off:a.mip_off + a.mip_size * (a.levels > 1)] == d1[b.mip_off:b.mip_off + b.mip_size * (b.levels > 1)]
            and d0[a.gtx:a.gtx + 0x80] == d1[b.gtx:b.gtx + 0x80] for a, b in zip(t0, t1))
        check('%s model.nut: every texture kept byte for byte, 2 added' % c, kept, True)
        lo, hi = T.fighter_range('supamario')
        check('%s: the new ids 0x%08X / 0x%08X, in Supamario\'s own range' % (c, hair_id, iris_id),
              ([t.tex_id for t in t1[-2:]], all(lo <= t.tex_id < hi for t in t1[-2:])), ([hair_id, iris_id], True))
        hair = nut.decode(d1, t1[-2]).reshape(-1, 4).astype(float)
        main, _shade = M.SILVER['hair']
        want = [round(255 * main * x) for x in M.SHEEN]
        check('%s: the silver hair %s (SILVER hair %g x the sheen, BC1 within 4)' % (c, want, main),
              bool((abs(hair[:, :3] - want) <= 4).all()), True)
        src_iris = nut.decode(d0, [t for t in t0 if t.tex_id & 0xFF == M.SRC_TEX['iris']][0])
        iris = nut.decode(d1, t1[-1])
        a = iris[..., 3] > 128
        rgb = iris[a][:, :3].astype(float)
        sat = (rgb.max(1) - rgb.min(1)) / np.maximum(rgb.max(1), 1)
        check('%s: the silver iris: the alpha as Mario\'s (within BC3), grey (saturation under 0.12), its ring up to '
              'SILVER iris %g' % (c, M.SILVER['iris'][0]),
              (int(abs(iris[..., 3].astype(int) - src_iris[..., 3]).max()) <= 8, bool(sat.max() < 0.12),
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
                for v in r0['vis']:
                    want.append((v['name'], v['keys']))
                    for k, (orig, cp) in M.MESHES.items():
                        if v['name'] == orig:
                            want.append((cp, [(0, 0, 0)]))
                            n += 1
                if r0['mats'] != r1['mats'] or [(v['name'], v['keys']) for v in r1['vis']] != want or \
                        x0[:struct.unpack('>I', x0[0x24:0x28])[0]] != x1[:struct.unpack('>I', x1[0x24:0x28])[0]]:
                    bad.append(na)
            check('%s %s: each hair / full hair / eye track followed by its copy\'s, hidden all through (%d added); '
                  'every other byte before the tracks, the materials and the tracks kept' % (c, pk, n), bad, [])
        dm = [e for e in T.pac_entries(open(os.path.join(dst, M.PACS[0]), 'rb').read()) if e[0] == 'default.mta']
        if dm:
            x = open(os.path.join(dst, M.PACS[0]), 'rb').read()[dm[0][1]:dm[0][1] + dm[0][2]]
            vis = {v['name']: v['keys'] for v in mta.read(x)['vis']}
            check('%s: hidden by default (default.mta: the copies off, his own hair / eyes on)' % c,
                  [vis.get(M.MESHES[k][1]) for k in ('hair', 'eye')] + [vis.get(M.MESHES[k][0]) for k in ('hair', 'eye')],
                  [[(0, 0, 0)]] * 2 + [[(0, 1, 0)]] * 2)


def ids_from_json(out):
    import json
    js = json.load(open(os.path.join(out, 'ultrainstinct.json')))
    B.FX_IDS.update({k: int(v, 16) for k, v in js['fx_ids'].items()})
    B.SE_IDS.update({k: int(v, 16) for k, v in js['se_ids'].items()})


def main():
    a = sys.argv[1:]
    if len(a) != 3:
        sys.exit(__doc__)
    out, ts_out, base = a
    ids_from_json(out)
    r = Run(os.path.join(out, 'fighter', 'supamario', 'script', 'msc', 'supamario.mscsb'))
    trigger_tests(r)
    form_tests(r)
    counter_tests(r)
    dodge_tests(r)
    reset_tests(r)
    ss_tests(r)
    script_tests(out, ts_out)
    motion_tests(out, ts_out)
    effect_tests(out, ts_out)
    aura_tests(out, ts_out)
    model_tests(out, base)
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
