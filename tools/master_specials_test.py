#!/usr/bin/env python3
"""Byleth (master) v8 MSC checks: his compiled master.mscsb run in rolloff_hold_test's MSC interpreter against a small
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
            return 0
        return 0

    def fvar(self, v):
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
    gm.catching = True
    gm.status.clear()
    b.call('master_hi_hit_main')
    moved, n = [], 0
    for n in range(1, 40):
        gm.frame = float(n)
        b.call('master_hi_hit_loop')
        ks = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] == 3]
        if ks:
            vx, vy = i2f(ks[-1][2]), i2f(ks[-1][3])
            gm.x += vx
            gm.y += vy
            moved.append((round(vx, 2), round(vy, 2)))
        gm.calls = [c for c in gm.calls if c[0] != 0x10]
        if b.g('master_phase') == 1:
            gm.frame = 1.0
            b.call('master_hi_hit_loop')            # the next frame stops him
            ks = [a for s, a in gm.calls if s == 0x10 and a and a[0] == 0x11 and a[1] == 3]
            stopped = bool(ks) and i2f(ks[-1][2]) == 0.0 and i2f(ks[-1][3]) == 0.0
            break
    links = [a for s, a in gm.calls if s == 0x2A and a and a[0] == 0x271B]
    sets = [a for s, a in gm.calls if s == 0x16 and a and a[0] == 7 and a[2] == 0x11000005]
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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else compiled()
    failnaught(path)
    up_special(path)
    print('\n%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
