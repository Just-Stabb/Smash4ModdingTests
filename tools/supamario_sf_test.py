#!/usr/bin/env python3
"""Ultra Instinct v11 checks (run by tools/supamario_ui_test.py, its check / PROBLEMS): Soaring Fist (the transformed
forward smash: supamario.c sf_* in the MSC interpreter, the projectile's MSC weapons/soaringfist.c, its scripts, motion,
model, effects, sounds, XV2's data) and the v11 effect fixes (tools/supamario_ui_fx11.py: the streaks' rotBasis run on
the game's own vertex programs, the aura's flipbooks and spread, the sparkles) and the motion table's slots."""
import math
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
import supamario_sf_build as F  # noqa: E402
import supamario_ui_anim as A  # noqa: E402
import supamario_ui_cave as C  # noqa: E402
import supamario_ui_fx11 as FX11  # noqa: E402
import supamario_ui_test as UT  # noqa: E402

check = UT.check
ST_S4 = 0x2B
ATK = 0x2712
SLOT_X, SLOT_Y, SLOT_F = 0x0F000020, 0x0F000021, 0x0F000023
HITSTUN, STATUS, PUSH = 0x0F000058, 0x0F0000BA, 0x0F0000BF


class Game(UT.Game):
    """his side: the attack button (held), the hold flag, articles, the custom slot, the other fighters' slots"""

    def __init__(self, held=0, flag=True, **kw):
        super().__init__(**kw)
        self.held = held                  # the attack button held through this frame
        self.hold_flag = flag
        self.ints = {0x10000048: 7}
        self.arts = []

    def sys(self, sid, a):
        if sid == 0xE and a[0] == ATK:
            return int(self.n <= self.held)
        if sid == 0x16 and a[0] == 0x10 and a[1] == 0x2100001B:
            return int(self.hold_flag and self.n >= F.HOLD_FLAG_AT)
        if sid == 0x16 and a[0] == 0x6:
            return self.ints.get(a[1], 0)
        if sid == 0x16 and a[0] == 0x7:
            self.ints[a[2]] = a[1]
            self.log.append((self.n, 'int', a[2], a[1]))
            return 0
        if sid == 0x20:
            self.arts.append((self.n, tuple(a), self.ints.get(0x10000048)))
            return 0
        return super().sys(sid, a)


def fidx(vm, name, src='supamario.c'):
    """a function's index: the decompiled func_N are N; ours counted from the file's end"""
    if name.startswith('func_'):
        return int(name[5:])
    s = open(os.path.join(HERE, '..', 'fighters', 'supamario', src)).read()
    names = [m.group(2) for m in re.finditer(r'^(int|void|float|bool)\s+(\w+)\s*\([^;]*$', s, re.M)]
    return len(vm.m.scripts) - 1 - (len(names) - 1 - names.index(name))


def sf_run(r, held=0, flag=True, form=2000.0, air_at=None, frames=None, others=(), status_req_stop=True):
    """status 0x2B's main (func_286) then frame by frame its loop (sf_loop) after the per-frame hook; others: [{slot: (x,
    y, hitstun, status)}] the other fighters, set every frame by a function of the frame (or fixed)"""
    g = Game(held=held, flag=flag, status=ST_S4, damage=50.0)
    g.vars[C.V_FORM] = form
    vm = r.vm(g)
    vm.g[18] = 0
    g.vars[SLOT_X], g.vars[SLOT_Y], g.vars[SLOT_F] = 0.0, 0.0, 1.0      # slot 1: him
    r.call(vm, 'func_286')
    looped = g.motion is not None and g.ev('motion_at') and g.ev('motion_at')[0][2] == F.MOT_START
    for _k in range(frames or 300):
        g.n += 1
        for t in UT.TIMERS:
            if g.vars.get(t, 0.0) > 0.0:
                g.vars[t] = max(0.0, g.vars[t] - 1.0)
        if air_at is not None and g.n >= air_at:
            g.air = True
        for o in others:
            o(g)
        vm.g[18] = 2 if g.air else 0
        g.req = None
        r.call(vm, 'func_82')
        if g.req is not None:
            break
        if looped:
            vm.g[18] = 2 if g.air else 0
            r.call(vm, 'sf_loop')
        if g.req is not None and status_req_stop:
            break
    return g, vm


def msc_tests(r):
    g, vm = sf_run(r, form=0.0, frames=1)
    check('v11: untransformed, the forward smash is Mario\'s: motion 0x5F (AttackS4S) from frame 0, no Soaring Fist',
          [e[2:] for e in g.ev('motion_at')][:1], [(0x5F, 0.0)])
    g, vm = sf_run(r)
    check('v11: transformed: the wind-up, motion 0x%X (specialairlwheavy_c2) from %d (XV2 #0 0-12)' % (
        F.MOT_START, F.START_AT), [e[2:] for e in g.ev('motion_at')][:1], [(F.MOT_START, float(F.START_AT))])
    rel = [e for e in g.ev('motion_at') if e[2] == F.MOT_REL]
    check('  a tap (nothing held): the release at frame %d, motion 0x%X from %d (level 1: XV2 #0 from 12)' % (
        F.HOLD_DECIDE, F.MOT_REL, F.REL_AT[0]), [(e[0], e[3]) for e in rel], [(F.HOLD_DECIDE, float(F.REL_AT[0]))])
    check('  one punch at frame %d (XV2\'s 20): article %d generated, the custom slot %d (level 1, final) then put back' % (
        F.HOLD_DECIDE + F.PUNCH[0], F.ARTICLE, F.code_of(1, 0)),
          ([(n, a[:2], c) for n, a, c in g.arts], g.ints[0x10000048]),
          ([(F.HOLD_DECIDE + F.PUNCH[0], (0x2710, F.ARTICLE), 0)], 7))
    end = [e for e in g.ev('status')]
    check('  Wait at the release\'s end (%d frames: XV2 #0 to 100)' % F.REL_N[0],
          [(e[0], e[2]) for e in end][:1], [(F.HOLD_DECIDE + F.REL_N[0] - 1, 0)])
    check('  no hold, no charge sound', [e for e in g.ev('sound') if e[2][0] == 0x2710 and e[2][1] == F.SND_CHARGE], [])
    # frames charged = the charge's frames up to and with the release's (the button let go on it, or the most)
    for held, lv in ((F.HOLD_DECIDE + 5, 1), (F.HOLD_DECIDE + F.LV2 - 2, 1), (F.HOLD_DECIDE + F.LV2 - 1, 2),
                     (F.HOLD_DECIDE + F.LV3 - 2, 2), (F.HOLD_DECIDE + F.LV3 - 1, 3), (500, 3)):
        g, vm = sf_run(r, held=held)
        hold = [e for e in g.ev('motion_at') if e[2] == F.MOT_START and e[3] == float(F.HOLD_AT)]
        rel = [e for e in g.ev('motion_at') if e[2] == F.MOT_REL]
        frames_held = min(held - F.HOLD_DECIDE + 1, F.HOLD_N)
        r0 = F.HOLD_DECIDE + frames_held
        want_codes = [F.code_of(lv, k) for k in range(lv)]
        check('v11: attack held to frame %d: the charge from %d (motion 0x%X from %d), released at %d (%d held%s): level '
              '%d, motion 0x%X from %d, punches at %s (codes %s)' % (
                  held, F.HOLD_DECIDE, F.MOT_START, F.HOLD_AT, r0, frames_held,
                  ': the most, %d' % F.HOLD_N if frames_held == F.HOLD_N else '', lv, F.MOT_REL, F.REL_AT[lv - 1],
                  [r0 + F.PUNCH[k] for k in range(lv)], want_codes),
              ([e[0] for e in hold], [(e[0], e[3]) for e in rel], [(n, c) for n, _a, c in g.arts]),
              ([F.HOLD_DECIDE], [(r0, float(F.REL_AT[lv - 1]))], [(r0 + F.PUNCH[k], want_codes[k]) for k in range(lv)]))
        if held == 500:
            snd = g.ev('sound')
            check('  the smash charge sound 0x%X on at the charge, off at the release' % F.SND_CHARGE,
                  [(e[0], e[2][0]) for e in snd if e[2][1] == F.SND_CHARGE][:2],
                  [(F.HOLD_DECIDE, 0x2710), (r0, 0x2714)])
            check('  Wait at the level-3 release\'s end (%d frames)' % F.REL_N[2],
                  [e[0] for e in g.ev('status')][:1], [r0 + F.REL_N[2] - 1])
    g, vm = sf_run(r, held=500, flag=False)
    check('v11: no hold flag (0x2100001B, the wind-up\'s game script turns it on at %d as Mario\'s; off: a C-stick smash): '
          'no charge, released at %d' % (F.START_AT + F.HOLD_FLAG_AT, F.HOLD_DECIDE),
          [e[0] for e in g.ev('motion_at') if e[2] == F.MOT_REL], [F.HOLD_DECIDE])
    g, vm = sf_run(r, held=500, air_at=30)
    check('v11: off the ground during it: Fall (0xE), the charge sound off',
          ([e[2] for e in g.ev('status')][:1], [e[2][0] for e in g.ev('sound') if e[2][1] == F.SND_CHARGE][-1:]),
          ([0xE], [0x2714]))
    # sf_end through the status's end (func_347)
    g = Game(status=ST_S4)
    vm = r.vm(g)
    vm.g[4], vm.g[6] = 0x2B, 0
    r.call(vm, 'func_347')
    check('v11: leaving 0x2B (func_347): the charge sound off (sf_end)',
          [e[2][:2] for e in g.ev('sound')], [(0x2714, F.SND_CHARGE)])


def arrive(lv, k, dx):
    d = max(0.0, dx - F.REACH - F.X0)
    fr = d / F.SPEED
    return None if F.MOVE_FROM + fr > F.LIFE[lv - 1] else F.PUNCH[k] + F.MOVE_FROM + fr


def hold_tests(r):
    """sf_hold: an opponent (slot 2) in the punches' lane"""
    held = F.HOLD_DECIDE + F.LV2                       # level 2 (21 frames charged)
    r0 = F.HOLD_DECIDE + F.LV2 + 1
    dx = 30.0

    def opp(y=0.0, hs=lambda g: 20.0, st=0x46, x=dx):
        def f(g):
            g.vars[SLOT_X + 4], g.vars[SLOT_Y + 4], g.vars[SLOT_F + 4] = x, y if not callable(y) else y(g), -1.0
            g.vars[HITSTUN + 8] = hs(g)
            g.vars[STATUS + 8] = float(st)
        return f
    a0, a1 = arrive(2, 0, dx), arrive(2, 1, dx)
    g, vm = sf_run(r, held=held, others=[opp()])
    w = [(e[0], round(e[3], 3)) for e in g.ev('set') if e[2] == HITSTUN + 8]
    first = r0 + math.ceil(a0)
    check('v11 (always connecting): level 2, an opponent %g in front in hitstun: from the first punch\'s arrival (release '
          '%.2f, frame %d) to the final one\'s (%.2f) its hitstun is kept at (frames to the final punch + %g); never before, '
          'never after' % (dx, a0, first, a1, F.HOLD_PAD),
          (w[0][0], all(abs(v - (a1 - (n - r0) + F.HOLD_PAD)) < 1e-3 for n, v in w), w[-1][0] < r0 + a1),
          (first, True, True))
    g, vm = sf_run(r, held=held, others=[opp(y=8.0)])
    ys = [(e[0], round(e[3], 3)) for e in g.ev('set') if e[2] == SLOT_Y + 4]
    ty = F.Y0 - F.MID
    check('  airborne (its feet 8 up): pulled to the lane (its middle on the punches\' line: feet at %g) by %g of the way a '
          'frame (the "windbox")' % (ty, F.PULL), (ys[0][1], ys[0][0]), (round(8.0 + (ty - 8.0) * F.PULL, 3), first))
    g, vm = sf_run(r, held=held, others=[opp(y=0.0)])
    check('  on the ground: not moved (its own knockback pushes it back)', [e for e in g.ev('set') if e[2] == SLOT_Y + 4],
          [])
    g, vm = sf_run(r, held=held, others=[opp(hs=lambda g: 0.0)])
    check('  not in hitstun (missed or shielding): its hitstun untouched', [e for e in g.ev('set') if e[2] == HITSTUN + 8],
          [])
    g, vm = sf_run(r, held=F.HOLD_DECIDE + 5, others=[opp()])
    check('  level 1 (one punch): nothing held', [e for e in g.ev('set') if e[2] in (HITSTUN + 8, SLOT_Y + 4)], [])
    g, vm = sf_run(r, held=held, others=[opp(x=-20.0)])
    check('  an opponent behind him: untouched', [e for e in g.ev('set') if e[2] in (HITSTUN + 8, SLOT_Y + 4)], [])
    g, vm = sf_run(r, held=held, others=[opp(x=200.0)])
    check('  one past the punches\' reach (level 2: %g): untouched' % (F.X0 + F.SPEED * (F.LIFE[1] - F.MOVE_FROM) + F.REACH),
          [e for e in g.ev('set') if e[2] in (HITSTUN + 8, SLOT_Y + 4)], [])
    # level 3: held across both later punches
    held3 = F.HOLD_DECIDE + F.LV3
    r3 = held3 + 1
    b = [arrive(3, k, dx) for k in range(3)]
    g, vm = sf_run(r, held=held3, others=[opp()])
    w = [(e[0], round(e[3], 3)) for e in g.ev('set') if e[2] == HITSTUN + 8]
    want = [(n, round((b[1] if n - r3 < b[1] else b[2]) - (n - r3) + F.HOLD_PAD, 3)) for n, _v in w]
    check('v11: level 3: held to the second punch, then to the third (the final)',
          (w[0][0], w == want, w[-1][0] < r3 + b[2]), (r3 + math.ceil(b[0]), True, True))
    # shields
    g, vm = sf_run(r, held=held, others=[opp(hs=lambda g: 0.0, st=F.ST_GUARD_DAMAGE)])
    p = [(e[0], round(e[3], 3)) for e in g.ev('set') if e[2] == PUSH + 8]
    nf = [(n, v) for n, v in p if n - r0 < a1]
    fi = [(n, v) for n, v in p if n - r0 >= a1]
    check('v11 (shields): a shielding opponent (guard damage) in front: pushed back (its pushback speed, world X: +) as '
          'each punch reaches it: the non-final from %g a frame, the final from %g (further), each fading over %g frames' % (
              F.PUSH_NF, F.PUSH_F, F.PUSH_W),
          (nf[0], round(max(v for _n, v in fi), 3) > round(max(v for _n, v in nf), 3), all(v > 0 for _n, v in p),
           len(nf) <= F.PUSH_W, len(fi) <= F.PUSH_W),
          ((r0 + math.ceil(a0), round(F.PUSH_NF * (1 - (math.ceil(a0) - a0) / F.PUSH_W), 3)), True, True, True, True))
    g, vm = sf_run(r, held=held, others=[opp(hs=lambda g: 0.0, st=F.ST_GUARD_DAMAGE, x=-dx)])
    check('  behind him: not pushed', [e for e in g.ev('set') if e[2] == PUSH + 8], [])


# ---------------------------------------------------------------- the projectile's MSC
class WGame:
    def __init__(self, code, x=50.0, y=10.0, face=1.0, owner=(0.0, 0.0, 1.0), kind=0x41, wall_at=None):
        self.code, self.x, self.y, self.face = code, x, y, face
        self.owner, self.kind, self.wall_at = owner, kind, wall_at
        self.n = 0
        self.log = []

    def fvar(self, v):
        if v == SLOT_X:
            return self.owner[0]
        if v == SLOT_Y:
            return self.owner[1]
        if v == SLOT_F:
            return self.owner[2]
        if v == 0x0F0000BD:
            return float(self.kind)
        return 0.0

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x16 and a[0] == 0x6 and a[1] == 0x10000005:
            return self.code
        if sid == 0x15:
            return R.f2i({0: self.face, 1: self.x, 2: self.y}.get(a[0], 0.0))
        if sid == 0x14 and a[0] == 0x3:
            self.x, self.y = f(a[1]), f(a[2])
            self.log.append((self.n, 'place', round(self.x, 3), round(self.y, 3)))
            return 0
        if sid == 0x10 and a[0] == 0x11:
            self.log.append((self.n, 'speed', round(f(a[2]), 3), round(f(a[3]), 3)))
            return 0
        if sid == 0x12 and a[0] == 0x1:
            self.log.append((self.n, 'motion', a[1], round(f(a[2]), 3)))
            return 0
        if sid == 0x21 and a[0] == 0x9:
            self.log.append((self.n, 'remove'))
            return 0
        if sid == 0x1A and a[0] == 0x2722:
            return int(self.wall_at is not None and self.n >= self.wall_at)
        return 0


def weapon_run(path, code, frames=60, **kw):
    g = WGame(code, **kw)
    vm = R.VM(path)
    vm.game = g
    vm.call(vm.func(fidx(vm, 'sf_setup', 'weapons/soaringfist.c')))
    vm.call(vm.func(fidx(vm, 'sf_main', 'weapons/soaringfist.c')))
    loop = vm.func(fidx(vm, 'sf_loop', 'weapons/soaringfist.c'))
    for _k in range(frames):
        g.n += 1
        vm.call(loop)
        if g.log and g.log[-1][1] == 'remove':
            break
    return g


def weapon_tests(out):
    path = os.path.join(out, 'fighter', 'supamario', 'script', 'msc', 'fireball', 'fireball.mscsb')
    for code in range(6):
        lv, final = code // 2 + 1, code % 2 == 0
        g = weapon_run(path, code)
        speeds = [e[2] for e in g.log if e[1] == 'speed']
        rem = [e[0] for e in g.log if e[1] == 'remove']
        check('v11 projectile (fireball.mscsb), code %d (level %d, %s): placed %g in front of him at his feet + %g, '
              'motion %d, still %d frames then %g a frame along his facing, removed on its frame %d (alive %d frames from its first: XV2\'s BSA life)' % (
                  code, lv, 'final' if final else 'non-final', F.X0, F.Y0, F.motion_of(code), F.MOVE_FROM, F.SPEED,
                  F.LIFE[lv - 1], F.LIFE[lv - 1]),
              ([e[2:] for e in g.log if e[1] == 'place'], [e[2:] for e in g.log if e[1] == 'motion'],
               speeds[:F.MOVE_FROM + 1], set(speeds[F.MOVE_FROM + 1:]), rem),
              ([(F.X0, F.Y0)], [(F.motion_of(code), 0.0)], [0.0] * (F.MOVE_FROM + 1), {F.SPEED}, [F.LIFE[lv - 1]]))
    g = weapon_run(path, 0, owner=(20.0, 5.0, -1.0), face=-1.0)
    check('  facing left (his facing): placed %g to his left, flying left (no tracking: a straight line)' % F.X0,
          ([e[2:] for e in g.log if e[1] == 'place'], {e[2] for e in g.log if e[1] == 'speed'} - {0.0},
           {e[3] for e in g.log if e[1] == 'speed'}),
          ([(20.0 - F.X0, 5.0 + F.Y0)], {-F.SPEED}, {0.0}))
    g = weapon_run(path, 0, kind=0x3)
    check('  no fighter of his kind: left where the game made it', [e for e in g.log if e[1] == 'place'], [])
    g = weapon_run(path, 4, wall_at=10)
    check('  a wall: removed', [e[0] for e in g.log if e[1] == 'remove'], [10])


# ---------------------------------------------------------------- files
def file_tests(out, base, skill_dir):
    import nud
    import omo
    sup = os.path.join(out, 'fighter', 'supamario')
    w = os.path.join(sup, 'script', 'animcmd', 'weapon', 'fireball')
    mt = open(os.path.join(w, 'motion.mtable'), 'rb').read()
    hs = struct.unpack('>%dI' % (len(mt) // 4), mt)
    check('v11: the projectile\'s motion table: slots 0-2 = %s (the final punch, level 2 / 3 non-final)' % (
        list(F.WEAPON_SCRIPTS),), list(hs[:3]), [acmd.crc(n) for n in F.WEAPON_SCRIPTS])
    game = acmd.ACMDFile.load(os.path.join(w, 'game.bin'))
    syn = acmd.INFO[acmd.BY_NAME['extra_special_hitbox']]['syntax']
    for i, n in enumerate(F.WEAPON_SCRIPTS):
        s = [c for c in game.script(n) if c.name != 'Script_End']
        hb = dict(zip(syn, s[1].params))
        want = dict(F.FINAL) if i == 0 else dict(F.NONFINAL, Damage=F.NONFINAL_DMG[i + 1])
        check('v11: %s: frame %d, one Extra_Special_Hitbox: an indirect hit (Direct/Indirect 0), Reflectable 0, '
              'Absorbable 0, Shieldable 1, size %g (XV2\'s 1.2 m), %s' % (
                  n, F.HIT_FROM, F.SIZE, ', '.join('%s %g' % kv for kv in sorted(want.items()))),
              (s[0].name, s[0].params[0], hb['Direct/Indirect'], hb['Reflectable'], hb['Absorbable'], hb['Shieldable'],
               round(hb['Size'], 3), {k: round(hb[k], 3) for k in want}, hb['ShieldDamage'] >= 0, len(s)),
              ('FRAME', float(F.HIT_FROM), 0, 0, 0, 1, F.SIZE, want, True, 2))
    eff = acmd.ACMDFile.load(os.path.join(w, 'effect.bin'))
    ids = UT_IDS.get('sf', {})
    check('v11: each punch\'s effect script: the skill\'s effect 5 (Hkn_Wav, following the shot) at frame 1 on its bone 0',
          {n: [(c.name, c.params[0], c.params[1], c.params[-1]) for c in eff.script(n) if c.name == 'External_Graphic']
           for n in F.WEAPON_SCRIPTS}, {n: [('External_Graphic', ids.get('wav'), 0, 1)] for n in F.WEAPON_SCRIPTS})
    check('v11: the projectile\'s model hidden (nud.hidden of the fireball\'s)',
          open(os.path.join(sup, 'model', 'fireball', 'c00', 'model.nud'), 'rb').read(),
          nud.hidden(os.path.join(base, 'model', 'fireball', 'c00', 'model.nud')))
    still = True
    for _name, data in omo.pac_read(os.path.join(sup, 'motion', 'fireball', 'main.pac')):
        o = omo.Omo(data)
        for n in o.nodes:
            s0 = o.sample(n[1], 0)
            still &= all(np.allclose(np.array(o.sample(n[1], f)[k], float), np.array(s0[k], float), atol=1e-4)
                         for f in (10, 50, o.frames - 1) for k in range(3))
    check('v11: its motion still (the fireball\'s spins its root: the hitbox and the wave would turn with it)', still, True)
    # his body scripts
    mtab = open(os.path.join(base, 'script', 'animcmd', 'body', 'motion.mtable'), 'rb').read()
    ws = struct.unpack('>%dI' % (len(mtab) // 4), mtab)
    check('v11: motion 0x%X / 0x%X -> the motion table\'s hashes crc("%s") / crc("%s")' % (
        F.MOT_START, F.MOT_REL, F.SCRIPT_START, F.SCRIPT_REL), (ws[F.MOT_START], ws[F.MOT_REL]),
          (acmd.crc(F.SCRIPT_START), acmd.crc(F.SCRIPT_REL)))
    body = {p: acmd.ACMDFile.load(os.path.join(sup, 'script', 'animcmd', 'body', p + '.bin'))
            for p in ('game', 'effect', 'sound', 'expression')}
    for p, f in body.items():
        hs_ = list(f.scripts)
        check('  %s.bin: both scripts, the table sorted (the game\'s binary search)' % p,
              (acmd.crc(F.SCRIPT_START) in hs_, acmd.crc(F.SCRIPT_REL) in hs_, hs_ == sorted(hs_)), (True, True, True))

    def at(script, part, name):
        out_, fr = [], 0
        for c in body[part].script(script):
            if c.name == 'FRAME':
                fr = int(c.params[0])
            elif c.name == name:
                out_.append((fr, c.params))
        return out_
    check('v11: the wind-up turns the hold flag 0x2100001B on at %d (Mario\'s AttackS4S frame 6)' % (
        F.START_AT + F.HOLD_FLAG_AT), [(f, p[0]) for f, p in at(F.SCRIPT_START, 'game', 'ON_FLAG')],
          [(F.START_AT + F.HOLD_FLAG_AT, 0x2100001B)])
    se = UT_IDS.get('se', {})
    check('v11: the skill\'s SE cue 0 (Bishi) at the wind-up\'s frame 0, cue 1 (Fire) at every punch (XV2 20 / 40 / 60)',
          ([f for f, p in at(F.SCRIPT_START, 'sound', 'Sound_Effect') if p[0] == se.get('sf_bishi')],
           [f for f, p in at(F.SCRIPT_REL, 'sound', 'Sound_Effect') if p[0] == se.get('sf_fire')]),
          ([F.START_AT], [F.REL_AT[lv - 1] + F.PUNCH[k] for lv in (1, 2, 3) for k in range(lv)]))
    check('v11: the hand burst (the skill\'s effect 0 / 1: Hkn_Fir) at every punch, at his fist\'s place in his frame',
          [f for f, p in at(F.SCRIPT_REL, 'effect', 'Graphic_Effect2') if p[0] == ids.get('fir')],
          [F.REL_AT[lv - 1] + F.PUNCH[k] for lv in (1, 2, 3) for k in range(lv)])
    check('v11: the charge: the smash charge\'s look (START_CHARGE at %d; sparkles every 10 frames to %d)' % (
        F.HOLD_AT, F.HOLD_AT + F.HOLD_N),
          ([f for f, _p in at(F.SCRIPT_START, 'expression', 'START_CHARGE')],
           [f for f, p in at(F.SCRIPT_START, 'effect', 'Graphic_Effect2') if p[0] == 0x1000019]),
          ([F.HOLD_AT], list(range(F.HOLD_AT, F.HOLD_AT + F.HOLD_N, 10))))
    # the motion
    pac = dict(omo.pac_read(os.path.join(sup, 'motion', 'body', 'main.pac')))
    o = omo.Omo([d for n, d in pac.items() if n.endswith('SpecialAirLwHeavy.omo')][0])
    check('v11: SpecialAirLwHeavy\'s animation: Secret Sensation\'s 45 frames, then Soaring Fist\'s wind-up 12, charge '
          '%d, releases %s (XV2 #0 / #1 / #2 from 12, 1:1)' % (F.HOLD_N, F.REL_N),
          (o.frames, F.START_AT, F.HOLD_AT, F.REL_AT), (45 + 12 + F.HOLD_N + sum(F.REL_N), 45, 57, [117, 206, 315]))
    src = [A.source(A.SS, f) for f in (F.HOLD_AT, F.HOLD_AT + 30, F.REL_AT[0], F.REL_AT[1] + 28, F.REL_AT[2] + 48)]
    check('  its sources: the charge XV2 #0 frame 12 held, each release from 12 (XV2 frame 40 of #1, 60 of #2 at the '
          'second / third punch)', [(s[1], round(s[2], 3)) for s in src],
          [(0, 12.0), (0, 12.0), (0, 12.0), (1, 40.0), (2, 60.0)])
    # XV2's data
    bsa = F.sf_bsa(os.path.join(skill_dir, '1510_GKS_HKN.bsa'))
    check('v11: XV2\'s BSA: six shots, lives 15 / 25 / 25 / 35 / 35 / 35, still then 80 m/s from frame 3, a 1.2 m '
          'hitbox from 2, BDM entry = its own, the skill\'s effect 5 at 1; our values from them',
          ([e['life'] for e in bsa], {tuple(e['move']) for e in bsa}, {e['hit'][:3] for e in bsa},
           [e['hit'][3] for e in bsa], {e['effect'] for e in bsa}, F.LIFE, F.SPEED, F.SIZE, F.MOVE_FROM, F.HIT_FROM),
          ([15, 25, 25, 35, 35, 35], {((0, 1, 0.0), (3, 4, 80.0))}, {(2, 15, 1.2), (2, 25, 1.2), (2, 35, 1.2)},
           [(k, k, k) for k in range(6)], {(1, 5, 1510, 5)}, (15, 25, 35), round(80 * 5.04 / 60, 3), round(1.2 * 5.04, 2),
           3, 2))
    import xv2bac
    bac = xv2bac.read_bac(os.path.join(skill_dir, '1510_GKS_HKN.bac'))
    proj = {}
    for e in bac['entries']:
        if e.get('index') in (0, 1, 2):
            proj[e['index']] = [it['start'] for it in e['items'] if it.get('type') == 9]
    check('v11: XV2\'s BAC: the shots at 20 | 20, 40 | 20, 40, 60 (entries 0 / 1 / 2); ours from them',
          (proj, F.PUNCH_XV2), ({0: [20], 1: [20, 40], 2: [20, 40, 60]}, (20, 40, 60)))
    bdm = xv2bac.read_bdm(os.path.join(skill_dir, '1510_GKS_HKN_PLAYER.shot.bdm'))
    check('v11: XV2\'s BDM: the final / uncharged punches (0, 2, 5) launch (type 7, hitstop 10), the others (1, 3, 4) '
          'stagger (type 3, hitstop 7, pushback 0.7 / 0.75): ours FINAL (hitstop %d) / NONFINAL (%d)' % (
              F.FINAL['HitstopFrames'], F.NONFINAL['HitstopFrames']),
          [(b['damage_type'], b['hitstop'][1]) for b in bdm],
          [(7, F.FINAL['HitstopFrames']), (3, F.NONFINAL['HitstopFrames']), (7, 10), (3, 7), (3, 7), (7, 10)])


UT_IDS = {}


# ---------------------------------------------------------------- v11 effect fixes
def fx_tests(out, ts_out):
    import ptcl
    import eft_vertex as V
    import json
    d = json.load(open(os.path.join(out, 'ultrainstinct.json')))
    fx = d['fx']
    p = ptcl.Ptcl(open(os.path.join(out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000.ptcl'),
                       'rb').read())
    q = ptcl.Ptcl(open(os.path.join(ts_out, 'fighter', 'supamario', 'effect', 'supamario', 'supamario.010d0000.ptcl'),
                       'rb').read())

    def emitters(pp, name):
        return [(pp.emitter_name(e['data']), e['data']) for e in pp.sets[pp.find_set(name)]['emitters']
                if e['data'] is not None]
    # 1. the streaks
    basis = {}
    for name in ('PtcSupamarioTsFrt_CrgAura', 'PtcSupamarioTsFrt_CrgAuraH', 'PtcSupamarioUiKTN_GKS_Loop',
                 'PtcSupamarioUiKTN_GKS_Loop_2', 'PtcSupamarioUiBoostGKS_End'):
        for en, em in emitters(p, name):
            if p.field(em, 'particle_type') == 3:
                basis[(name, en)] = round(struct.unpack_from('>2f', em, FX11.ROT_BASIS)[1], 3)
    ts = {k: v for k, v in basis.items() if 'Ts' in k[0]}
    ui = {k: v for k, v in basis.items() if 'Ui' in k[0]}
    check('v11 (the aura far below him): every streak of Time Skip\'s aura (CrgAura / CrgAuraH: XV2 ConeExtrude ribbons) '
          'has rotBasis -0.5 (its quad from the particle back by its length), of Secret Sensation\'s (KTN_GKS_Loop, '
          'BoostGKS_End: VisibleOnSpeed sprites) 0 (centred); v10 -1.34 everywhere (the template\'s): %d / %d streaks' % (
              len(ts), len(ui)), (set(ts.values()), set(ui.values()), len(ts) >= 8, len(ui) >= 10),
          ({FX11.BASIS_CONE}, {FX11.BASIS_CENTRED}, True, True))
    old = {}
    for name in ('PtcSupamarioTsFrt_CrgAura', 'PtcSupamarioTsFrt_CrgAuraH'):
        for en, em in emitters(q, name):
            if q.field(em, 'particle_type') == 3:
                old[(name, en)] = round(struct.unpack_from('>2f', em, FX11.ROT_BASIS)[1], 3)
    check('  Time Skip\'s build had them at -1.34 (the cause)', set(old.values()), {-1.34})
    dim = []
    for name in ('PtcSupamarioTsFrt_CrgAura', 'PtcSupamarioTsFrt_CrgAuraH'):
        qe = dict(emitters(q, name))
        for en, em in emitters(p, name):
            if p.field(em, 'particle_type') == 3:
                for t in (0, 1):
                    dim.append(all(abs(a - b * FX11.TS_DIM) < 1e-4 for k1, k0 in zip(p.color_keys(em, t),
                                                                                    q.color_keys(qe[en], t))
                                   for a, b in zip(k1[:3], k0[:3])))
    check('  Time Skip\'s streaks, on him now, at %g of their colours (the white-area rule: supamario_timeskip_test\'s '
          'ts_e0 at most 1.0 square unit on grass)' % FX11.TS_DIM, (len(dim) >= 16, all(dim)), (True, True))
    # run the game's programs: where the quad's centre sits against its particle, before / after
    import latte_exec
    import eft_static
    import fx_render as FR
    S = FR.to_screen()
    Si = np.linalg.inv(S)
    res = {}
    for name, en in (('PtcSupamarioUiKTN_GKS_Loop', 'wind_1'), ('PtcSupamarioTsFrt_CrgAuraH', 'stripe')):
        for which, pp in (('v11', p), ('v10', q if 'Ts' in name else None)):
            if pp is None:
                continue
            em = dict(emitters(pp, name))[en]
            vs = latte_exec.VertexProgram(bytes(pp.shader_binary(pp.field(em, 'shader_index'))))
            cb2 = np.frombuffer(eft_static.build(bytes(em)), np.float32).copy()
            A_ = np.zeros((4, len(vs.attributes), 4), np.float32)
            per = {'v_inWldPos': (0, 0, 0, 0), 'v_inVec': (0, 0.4, 0, 1), 'v_inScl': (1, 1, 1, 1),
                   'v_inRandom': (0.3, 0.6, 0.2, float(pp.field(em, 'ptcl_life'))), 'v_inRot': (0, 0, 0, 0),
                   'v_inEmtMat0': (1, 0, 0, 0), 'v_inEmtMat1': (0, 1, 0, 0), 'v_inEmtMat2': (0, 0, 1, 0)}
            for k, nm in enumerate(vs.attributes):
                if nm == 'v_inPos':
                    A_[:, k] = FR.EFT_QUAD
                elif nm in per:
                    A_[:, k] = per[nm]
            cb3 = np.zeros(48, np.float32)
            cb3[0:8] = 1.0
            cb3[8:12] = (6.0, 1, 1, 1)
            cb3[12:16] = 1.0
            cb3[16:32] = np.eye(4).ravel()
            cb3[32:48] = np.eye(4).ravel()
            gp, _par = vs.run(A_, {1: FR.s4_view_block(), 2: cb2, 3: cb3}, np.arange(4))
            wpts = [Si @ (gp[i, :3] / gp[i, 3]) for i in range(4)]
            ys = [w_[1] for w_ in wpts]
            part = 0.4 * 5
            res[(en, which)] = (round(min(ys) - part, 2), round(max(ys) - part, 2))
    k = res[('wind_1', 'v11')]
    check('v11: run on the game\'s own vertex program (latte_exec): KTN\'s wind_1 (a VisibleOnSpeed sprite) is drawn '
          'round its particle (%s units from it); v10\'s -1.34 drew it 10.7-21.4 under' % (k,),
          k[0] < 0 < k[1] and abs(k[0] + k[1]) < 1.5, True)
    k1, k0 = res[('stripe', 'v11')], res[('stripe', 'v10')]
    check('  Time Skip\'s stripe (a ConeExtrude ribbon): from its particle back along its way (%s); v10 %s (detached, '
          'behind)' % (k1, k0), (abs(k1[1]) < 0.6, k1[0] < -3.0, k0[1] < -3.0), (True, True, True))
    # 2. the flipbooks
    flip = fx['v11_flipbook']
    ok = [x for x in flip if isinstance(x[2], list)]
    good = True
    for name, en, (nx, ny, cells, per, prog, fv, tw, th) in ok:
        em = dict(emitters(p, name))[en]
        f = V.features(p.shader_binary(p.field(em, 'shader_index')))
        good &= (f['flipbook'][0] and f['gpu_follows'] and p.field(em, 'shader_index') == fv
                 and em[0x4D7] == nx and em[0x4D8] == ny and struct.unpack_from('>I', em, 0x500)[0] == 2
                 and struct.unpack_from('>hh', em, 0x504) == (per, cells)
                 and struct.unpack_from('>2f', em, 0x534) == (1.0, 1.0)
                 and tuple(round(v, 4) for v in struct.unpack_from('>2f', em, 0x508)) == (round(1.0 / nx, 4),
                                                                                       round(1.0 / ny, 4)))
    names = {x[0] for x in ok}
    check('v11 (the aura stiff): %d GPU aura sprites play XV2\'s sprite sheets (the whole sheet, nx x ny cells, mode 2 '
          'loop at XV2\'s frames a cell), on their program\'s flipbook variant still reading the live emitter matrix '
          '(following him), their UV scale 1 / cells, the UV block neutral' % len(ok),
          (good, len(ok) >= 6, {'PtcSupamarioUiAura_LoopFOK', 'PtcSupamarioUiAura_HLoopFOK'} <= names,
           [x for x in flip if not isinstance(x[2], list)]), (True, True, True, []))
    lf = [x for x in ok if x[0] == 'PtcSupamarioUiAura_LoopFOK' and x[1] == 'sprite_1_1'][0][2]
    check('  Aura_LoopFOK\'s sprite_1_1: XV2\'s 8 x 2 sheet, 16 cells every 3 frames', tuple(lf[:4]), (8, 2, 16, 3))
    # 3. the spread
    spread = fx['v11_spread']
    check('v11: the aura sprites scattered by XV2\'s Position_Variance (VerticalDistribution: Aura_LoopFOK 0.3 m -> '
          'radius 2.55, the others 0.1 m -> 0.85)', ({x[2] for x in spread}, len(spread) >= 6), ({2.55, 0.85}, True))
    # 4. the sparkles
    pc = dict(emitters(p, 'PtcSupamarioUiAura_FOKpiace'))
    vals = {en: (tuple(round(v, 3) for v in p.field(em, 'emitter_rotation')), p.field(em, 'volume_type'),
                 tuple(round(v, 3) for v in p.field(em, 'volume_radius')), tuple(p.field(em, 'emit_direction')),
                 round(p.field(em, 'emitter_velocity'), 3), tuple(round(v, 3) for v in p.field(em, 'emitter_translation')))
            for en, em in pc.items()}
    check('v11 (the sparkles): an upright disc round his middle (turned X -90: a circle fill radius %g in his XY plane), '
          'rising %g a frame along his up, no offset (v10: 7 units under his hip)' % (FX11.PIACE_R, FX11.PIACE_RISE),
          set(vals.values()), {((round(-math.pi / 2, 3), 0.0, 0.0), 3, (FX11.PIACE_R, 0.0, FX11.PIACE_R), (0.0, 0.0, 1.0),
                                FX11.PIACE_RISE, (0.0, 0.0, 0.0))})
    check('  %g times bigger' % FX11.PIACE_SIZE, {en: [round(v, 3) for v in p.field(em, 'scale')] for en, em in pc.items()},
          {en: [round(v * FX11.PIACE_SIZE, 3) for v in (0.098 if en == 'sprite' else 0.059,) * 2] for en in pc})
    # the rotation's way: the disc's normal and the rise
    em = pc['sprite']
    m = np.array(p.field(em, 'emitter_matrix'), float).reshape(3, 4)
    check('  its matrix: the volume\'s plane (local XZ) -> his XY (sideways / up), the rise (local +Z) -> his up',
          (np.round(m[:, :3] @ [1, 0, 0], 3).tolist(), np.round(m[:, :3] @ [0, 0, 1], 3).tolist()),
          ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]))


def piace_msc_tests(r):
    """the sparkles' request: TransN at his hip's height"""
    g = UT.Game(status=0, damage=120.0)
    g.vars[C.V_FORM] = 2000.0
    vm = r.vm(g)
    r.call(vm, 'ui_aura')
    ids = UT_IDS.get('aura_piace')
    calls = [e[5] for e in g.ev('effect') if e[2] == 0x2717 and e[3] == ids]
    check('v11: the sparkles\' MSC request: TransN (joint 0, his up the world\'s), %g up (his hip in Wait), size 1.75' %
          FX11.PIACE_Y, [(c[2], UT.fbits(c[4]), UT.fbits(c[9])) for c in calls], [(0, FX11.PIACE_Y, 1.75)])


def native_tests(exe):
    """the exe's motion table gives 0x246 / 0x247 SpecialAirLwHeavy's animation; their scripts are his own (link 0)"""
    from kind_expand_test import Emu
    from unicorn.ppc_const import UC_PPC_REG_MSR
    e = Emu(exe)
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    desc = e.call(UT.DESC_GETTER, 0, UT.M_KIND)
    table = e.w(e.w(desc + 4))
    anim = {m: e.w(table + 8 * m) for m in (0x245, F.MOT_START, F.MOT_REL)}
    check('v11 native: the motion table gives 0x%X / 0x%X SpecialAirLwHeavy\'s animation (0x245\'s)' % (
        F.MOT_START, F.MOT_REL), (anim[F.MOT_START], anim[F.MOT_REL]), (anim[0x245], anim[0x245]))
    mm = e.alloc(0x40, b'\0')
    e.setw(mm + 0x1C, table)
    e.setw(0x10492CB4, 1)
    check('  their scripts bound as his own (link-kind 0)', [e.call(UT.MOTION_LINK, mm, m) for m in (F.MOT_START,
                                                                                                    F.MOT_REL)], [0, 0])


def run(r, out, ts_out, base, skill_dir=None, exe=None):
    import json
    d = json.load(open(os.path.join(out, 'ultrainstinct.json')))
    UT_IDS['se'] = {k: int(v, 16) for k, v in d['se_ids'].items()}
    UT_IDS['sf'] = {k: int(v, 16) for k, v in d.get('sf', {}).get('fx_ids', {}).items()}
    UT_IDS['aura_piace'] = int(d['fx_ids']['aura_piace'], 16)
    msc_tests(r)
    hold_tests(r)
    weapon_tests(out)
    piace_msc_tests(r)
    fx_tests(out, ts_out)
    if skill_dir:
        file_tests(out, base, skill_dir)
    if exe:
        native_tests(exe)
