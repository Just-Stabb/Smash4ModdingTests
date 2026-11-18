#!/usr/bin/env python3
"""Ultra Instinct v1 (Supamario's gimmick) offline checks: the compiled MSC (ui_* through func_82's hook and statuses
0x157 / 0x158's functions, in rolloff_hold_test's MSC interpreter) driving a small model of the game, and the built
scripts, motions, effects and sounds.

  python3 -I tools/supamario_ui_test.py BUILD_OUT_DIR TIMESKIP_OUT_DIR

BUILD_OUT_DIR: tools/supamario_ui_build.py's OUT_DIR; TIMESKIP_OUT_DIR: the same inputs built by
tools/supamario_timeskip_build.py (the install before this): every other script, motion and effect set is checked
unchanged. The native part has its own test (tools/supamario_ui_cave_test.py).

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
            self.log.append((self.n, 'effect', a[0], a[1], a[2] if len(a) > 2 else None))
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
    sh = [e[2] for e in g.ev('shield')]
    check('the counter shape on at the start, off at the end (ShieldModule(0, 2, 0, on, 1))',
          (sh[0], sh[-1]), ((0, 2, 0, 1, 1), (0, 2, 0, 0, 1)))
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
    check('the aura made right after (4 following requests 0x2730, the three old ones ended first)',
          sorted((e[2], e[3]) for e in aura),
          sorted([(0x2723, B.fx_id('aura_hip')), (0x2723, B.fx_id('aura_head')), (0x2723, B.fx_id('aura_foot')),
                  (0x2730, B.fx_id('aura_hip')), (0x2730, B.fx_id('aura_head')), (0x2730, B.fx_id('aura_foot')),
                  (0x2730, B.fx_id('aura_foot'))]))
    check('  on HipN / HeadN / LFootJ / RFootJ', sorted(e[4] for e in aura if e[2] == 0x2730),
          sorted([B.BONES['HipN'], B.BONES['HeadN'], B.BONES['LFootJ'], B.BONES['RFootJ']]))
    for k in range(int(B.AURA_EVERY)):
        r.frame(vm, g)
    again = [e for e in g.ev('effect', end + 2) if e[2] == 0x2730]
    check('  made again after %d frames' % B.AURA_EVERY, len(again), 4)
    g, vm = form_run(r, air=True)
    check('in the air: held still, Fall at the end', ([e[2] for e in g.ev('status')][-1], g.air), (0xE, True))


def counter_tests(r):
    for what, rec, air, want_x, want_y, want_dmg, turn in (
            ('a fighter on the ground to his right, 10%', (10.0, 1.0, True, 40.0, 0.0, 0), False, 40.0 - B.GAP, 0.0,
             12.0, True),
            ('a fighter to his left, 5% (8 at least)', (5.0, -1.0, True, -20.0, 0.0, 0), False, -20.0 + B.GAP, 0.0,
             8.0, False),
            ('a projectile, its owner high up to the right', (20.0, 1.0, True, 60.0, 25.0, 1), False, 60.0 - B.GAP,
             25.0, 24.0, True),
            ('a projectile with no owner found', (7.0, 1.0, False, 0.0, 0.0, 1), False, 10.0, 0.0, 8.4, True)):
        g, vm = form_run(r, air=air, counter_at=20, record=rec, frames=B.FORM_N + B.STRIKE_N + 5)
        ms = [e[2] for e in g.ev('motion')]
        check('counter, %s: the strike\'s motion (0x235) after the transformation\'s' % what, ms[:2],
              [B.MOT_FORM, B.MOT_STRIKE])
        at = [e for e in g.ev('motion') if e[2] == B.MOT_STRIKE][0][0]
        check('  at once (the frame the record is read)', at, 22)
        check('  its damage %.1f (status float 0x0100000A)' % want_dmg,
              [e[3] for e in g.ev('set') if e[2] == B.F_DMG and e[3] > 0][:1], [round(want_dmg, 4)])
        check('  turned to face it' if turn else '  not turned', len(g.ev('turn')), 1 if turn else 0)
        check('  placed at X %.1f, Y %.1f' % (want_x, want_y), (round(g.x, 3), round(g.y, 3)), (want_x, want_y))
        check('  the shape off at once', [e[2] for e in g.ev('shield') if e[0] == at][:1], [(0, 2, 0, 0, 1)])
        check('  transformed from then on (TIMER_0 2000)',
              [e[3] for e in g.ev('set') if e[2] == C.V_FORM and e[0] == at][-1:], [2000.0])
        check('  the vanish effect where he was', [e[3] for e in g.ev('effect') if e[0] == at and e[2] == 0x2710][:1],
              [B.fx_id('vanish')])
        ints = sorted({e[0] for e in g.ev('set') if e[2] == 0x0F00011B and e[0] >= at})
        check('  intangible through the strike (to its frame %d)' % B.STRIKE_SAFE,
              ints[-1] - at if ints else None, B.STRIKE_SAFE)
        if want_y > 0:
            check('  in the air (the target off the ground)', g.air, True)
        end = [e for e in g.ev('status') if e[2] in (0, 0xE)]
        check('  the end after the strike\'s %d frames' % B.STRIKE_N, end[0][0] - at if end else None, B.STRIKE_N - 1)


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


def script_tests(out, ts_out):
    body = os.path.join(out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    tbody = os.path.join(ts_out, 'fighter', 'supamario', 'script', 'animcmd', 'body')
    f = {p: acmd.ACMDFile.load(os.path.join(body, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    b = {p: acmd.ACMDFile.load(os.path.join(tbody, p + '.bin')) for p in ('game', 'effect', 'sound', 'expression')}
    nm = lambda c: c.name  # noqa: E731
    g = f['game'].script('speciallwheavy')
    hb = [c for c in g if nm(c).lower() == 'extra_special_hitbox']
    check('the strike: one Extra hitbox', len(hb), 1)
    if hb:
        syn = acmd.INFO[hb[0].ident]['syntax']
        d = dict(zip(syn, hb[0].params))
        check('  its Damage the variable 0x0100000A (1.2x the hit, 8 at least: the MSC)',
              struct.unpack('>I', struct.pack('>f', d['Damage']))[0], B.F_DMG)
        check('  angle 35, BKB 80, KBG 75, no clank', (d['Angle'], d['BKB'], d['KBG'], d['Clang']), (35, 80, 75, 0))
    frames = [c.params[0] for c in g if nm(c).upper() == 'FRAME']
    check('  out at %d, removed at %d' % (B.STRIKE_AT, B.STRIKE_AT + 3), frames, [float(B.STRIKE_AT), float(B.STRIKE_AT + 3)])
    check('the transformation / the dodge: no hitbox',
          [nm(c) for s in ('speciallwlight', 'specialairlwlight') for c in f['game'].script(s)], ['Script_End', 'Script_End'])
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
        check('%s: the vanish sound / effect at 0' % s,
              ([c.params[0] for c in f['sound'].script(s) if nm(c) == 'Sound_Effect'],
               [c.params[0] for c in f['effect'].script(s) if 'graphic' in nm(c).lower()]),
              ([B.SE_IDS['ui_vanish']], [B.fx_id('vanish')]))
    skip = {acmd.crc(n) for n in B.SCRIPT.values()}
    other = []
    for p in f:
        for h, s in b[p].scripts.items():
            if h in skip:
                continue
            ns = f[p].scripts.get(h)
            if [(c.ident, c.params) for c in s] != [(c.ident, c.params) for c in (ns or [])]:
                other.append((p, hex(h)))
    check('every other script as Time Skip v10\'s build', other, [])


def motion_tests(out, ts_out):
    for part in ('main', 'mariopt1', 'lhand', 'rhand'):
        new = dict(omo.pac_read(os.path.join(out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        old = dict(omo.pac_read(os.path.join(ts_out, 'fighter', 'supamario', 'motion', 'body', part + '.pac')))
        diff = sorted(n.split('D03')[-1] for n in new if new[n] != old.get(n))
        check('%s.pac: only the three slots changed' % part, diff,
              sorted([A.DODGE, A.STRIKE, A.FORM]))
        fr = {m: omo.Omo(new[[n for n in new if n.endswith('D03' + m)][0]]).frames for m in A.MOTIONS}
        check('%s.pac: 60 / 58 / 16 frames' % part, fr, {A.FORM: 60, A.STRIKE: 58, A.DODGE: 16})


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


def ids_from_json(out):
    import json
    js = json.load(open(os.path.join(out, 'ultrainstinct.json')))
    B.FX_IDS.update({k: int(v, 16) for k, v in js['fx_ids'].items()})
    B.SE_IDS.update({k: int(v, 16) for k, v in js['se_ids'].items()})


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    out, ts_out = a
    ids_from_json(out)
    r = Run(os.path.join(out, 'fighter', 'supamario', 'script', 'msc', 'supamario.mscsb'))
    trigger_tests(r)
    form_tests(r)
    counter_tests(r)
    dodge_tests(r)
    reset_tests(r)
    script_tests(out, ts_out)
    motion_tests(out, ts_out)
    effect_tests(out, ts_out)
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
