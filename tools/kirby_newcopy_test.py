#!/usr/bin/env python3
"""Behaviour test of Kirby's Hero / Sephiroth copy neutral specials (fighters/kirby/kirby.c "Hero / Sephiroth copies"):
runs the compiled MSC in tools/rolloff_hold_test.py's interpreter with the modules stubbed, frame by frame, and checks
what the move does (motions, the article made and the ints it reads, statuses, MP).

  python3 tools/kirby_newcopy_test.py KIRBY.mscsb [fighters/kirby/kirby.c]

The game's side, stubbed: WorkModule ints / flags (the copy kind 0x2C, the marker 0x100000A0, the custom slots),
MotionModule (change / swap / frame), ControlModule (pressed / held), StatusModule (situation, status changes),
ArticleModule (the generate, with the slots' values at that moment), EffectModule (ids), the rest 0.
Scenarios: Hero Frizzle (charge 20 frames, press: MP 100 -> 84, slot 0x44A, the fireball (article 6) at frame 11 with
level 1 in 0x10000048 / 0x1000009F, both put back, wait at the end); Hero with 10 MP charging to Kafrizz (stored at 81:
the cancel slot 0x447), then the stored charge casts at once the level he pays for (Frizz, 6 MP); Hero with 3 MP (the
misfire, 0x447); Sephiroth Megaflare (released at 40: slot 0x44A, the fire (article 7) at 13 with 0x10000049 =
1 + 4 x up = 5) and Gigaflare (held: fired by the charge at 120, level 2), in the air (slots + 7); the Robin copy
without the marker still goes to Robin's code.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rolloff_hold_test as R  # noqa: E402

FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


class Game:
    def __init__(self, marker):
        self.ints = {0x100000A4: 0x2C, 0x100000A0: marker, 0x10000048: 7, 0x10000049: 9, 0x1000009F: 11}
        self.flags = {0x2000009A}
        self.motion, self.frame, self.situation = None, 0.0, 0
        self.press, self.held = set(), set()
        self.stick_y = 0.0
        self.motions, self.articles, self.statuses, self.effects = [], [], [], []
        self.fvars = {}
        self.speeds = []

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and len(a) == 2 and a[0] == 0:          # WorkModuleF(0, var): position variables
            return R.f2i(self.fvars.get(a[1], 0.0))
        if sid == 0x16:                                         # WorkModule
            if a[0] == 0 and len(a) == 3:                       # WorkModule(0, value, var): set a float variable
                self.fvars[a[2]] = R.i2f(a[1])
                return 0
            if a[0] == 0x6:
                return self.ints.get(a[1], 0)
            if a[0] == 0x7:
                self.ints[a[2]] = a[1]
                return 0
            if a[0] == 0x10:
                return int(a[1] in self.flags)
            if a[0] == 0x2710:
                self.flags.add(a[1])
            return 0
        if sid == 0x12:                                         # MotionModule
            if a and a[0] == 0x1:
                self.motion, self.frame = a[1], R.i2f(a[2])
                self.motions.append(a[1])
            elif a and a[0] == 0x3:
                self.motion = a[1]
                self.motions.append(('swap', a[1]))
            return 0
        if sid == 0x13 and a == [1]:                            # MotionModuleF(1): frame
            return R.f2i(self.frame)
        if sid == 0x18:
            if a == [1]:
                return self.situation
            if a and a[0] in (0x2710, 0x2711):
                self.statuses.append(a[1])
            return 0
        if sid == 0xE and len(a) == 2:
            if a[0] == 0x2710:
                return int(a[1] in self.press)
            if a[0] == 0x2712:
                return int(a[1] in self.held)
            return 0
        if sid == 0xF and a == [1]:
            return R.f2i(self.stick_y)
        if sid == 0x20 and a and a[0] == 0x2710:                # ArticleModule generate
            self.articles.append((a[1], self.frame, self.ints.get(0x10000048), self.ints.get(0x1000009F),
                                  self.ints.get(0x10000049)))
            return 0
        if sid == 0x10 and len(a) == 3 and a[0] == 0x11 and a[1] == 1:   # KineticModule(0x11, 1, v): speed
            self.speeds.append(R.i2f(a[2]))
            return 0
        if sid == 0x1C and a and a[0] in (0x2717, 0x2710):
            self.effects.append(a[1])
            return 0
        del f
        return 0


def names(src):
    return R_names(src)


def R_names(src):
    s = open(src).read()
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//[^\n]*', '', s)
    funcs = re.findall(r'^(?:int|void|float)\s+(\w+)\s*\([^;{)]*\)\s*\{', s, re.M)
    glob = re.findall(r'^(?:int|float)\s+(\w+)\s*;', s, re.M)
    return funcs, glob


class Run:
    def __init__(self, path, src, marker, situation=0):
        self.vm = R.VM(path)
        funcs, glob = R_names(src)
        self.fn = {n: self.vm.func(i) for i, n in enumerate(funcs)}
        self.gi = {n: i for i, n in enumerate(glob)}
        self.game = Game(marker)
        self.game.situation = situation
        self.vm.game = self.game
        self.vm.g[self.gi['global18']] = situation
        self.vm.g[self.gi['global19']] = situation
        f16, call = self.fn['func_16'], self.vm.call

        def spy(script, args=()):               # func_16 (status change through global11): recorded
            if script is f16:
                self.game.statuses.append(args[0])
                return None
            return call(script, args)
        self.vm.call = spy

    def gf(self, name):
        return R.i2f(self.vm.g.get(self.gi[name], 0))

    def setf(self, name, v):
        self.vm.g[self.gi[name]] = R.f2i(v)

    def update(self):
        self.vm.call(self.fn['newcopy_update'])

    def start(self, held=()):
        self.game.motions, self.game.articles, self.game.statuses = [], [], []
        self.game.held = set(held)                  # the main runs the loop once at once (func_78)
        self.vm.g[self.gi['global4']] = 0x222
        self.vm.call(self.fn['newcopy_n_main'])

    def step(self, press=(), held=(), stick_y=0.0):
        g = self.game
        g.press, g.held, g.stick_y = set(press), set(held), stick_y
        self.vm.g[self.gi['global32']] = R.f2i(stick_y)
        n = len(g.motions)
        self.vm.call(self.fn['ncp_loop'])
        if len(g.motions) == n or isinstance(g.motions[-1], tuple):
            g.frame += 1.0
        return g


def cast(r, spell, frames, f=None):
    """open the menu on the stone, cast `spell` from row 0, run `frames` frames (f(r) after each)"""
    g = r.game
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['khm_spells']] = spell
    r.vm.g[r.gi['khm_cursor']] = 0
    g.press = {0}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    for _ in range(frames):
        r.vm.call(r.fn['khm_update'])
        if f:
            f(r)


def v3_tests(path, src):
    """v3: Kamikazee, Kaclang, Bounce, Hocus Pocus, Zoom, MP from damage dealt"""
    r = Run(path, src, 2)
    g = r.game
    r.update()
    g.fvars.update({0x0F000000: 10.0, 0x0F000001: 0.0, 0x0F000020: 10.0, 0x0F000021: 0.0, 0x0F000023: 1.0,
                    0x0F000024: 50.0, 0x0F000025: 0.0, 0x0F000027: 1.0})    # he is slot 0, a fighter in slot 1
    cast(r, 0x9, 21)
    check('Kamikazee: the crash (article 12) at 20, level 1 + 8 x his slot 0', [(x[0], x[2]) for x in g.articles], [(12, 1)])
    check('Kamikazee: no KO before 49', 0x20000043 in g.flags, False)
    for _ in range(30):
        r.vm.call(r.fn['khm_update'])
    check('Kamikazee: KO flag 0x20000043 at 49', 0x20000043 in g.flags, True)
    r.setf('ncp_mp', 100.0)
    cast(r, 0xa, 25)
    check('Kaclang: metal (SELF_ITEM 1) and invincible from 20', (g.fvars.get(0x0F000099), g.fvars.get(0x0F00011C)), (1.0, 2.0))
    for _ in range(300):
        r.vm.call(r.fn['khm_update'])
    check('Kaclang: metal off (SELF_ITEM 2) after 300', g.fvars.get(0x0F000099), 2.0)
    r.setf('ncp_mp', 100.0)
    cast(r, 0xd, 12)
    check('Bounce: 720 frames of reflector', r.vm.g.get(r.gi['khm_reflect_t']) > 700, True)
    r.setf('ncp_mp', 100.0)
    g.speeds = []
    cast(r, 0x10, 31)
    check('Zoom: up at 9 from frame 29', g.speeds[:1], [9.0])
    for _ in range(40):
        r.vm.call(r.fn['khm_update'])
    check('Zoom: then put 120 above the fighter on the ground (slot 1) and down at 7',
          (g.fvars.get(0x0F000000), g.fvars.get(0x0F000001), g.speeds[-1]), (50.0, 120.0, -7.0))
    r.vm.g[r.gi['global18']] = 0
    r.vm.call(r.fn['khm_update'])
    check('Zoom: done on landing', r.vm.g.get(r.gi['khm_sub']), 0x7f)
    r.setf('ncp_mp', 100.0)
    cast(r, 0xf, 3)
    check('Hocus Pocus (the draw\'s first outcome): giant (SELF_ITEM 3), 4 MP', (g.fvars.get(0x0F000099), r.gf('ncp_mp')),
          (3.0, 96.0))
    r.setf('ncp_mp', 50.0)
    r.vm.g[r.gi['global4']] = 0x2
    r.vm.call(r.fn['khm_update'])
    g.fvars[0x0F000197] = 10.0                 # slot 1's damage + 10 (0x0F000177 + 0x20)
    g.fvars[0x0F0000A0] = 1.0                  # his attack has hit
    r.vm.call(r.fn['khm_update'])
    check('MP from damage dealt: 0.8 x 10', r.gf('ncp_mp'), 58.0)


def menu_tests(path, src):
    """stage 2: Stone (status 0x175) = Hero's Command Selection (kirby.c khm_*)"""
    r = Run(path, src, 2)
    g = r.game
    r.update()
    g.fvars[0x0F000117] = 30.0                  # his damage (Heal)
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    check('menu: opens when the stone starts', r.vm.g.get(r.gi['khm_state']), 1)
    check('menu: blocks the stone\'s special while open', r.vm.call(r.fn['khm_blocking']), 1)
    r.vm.g[r.gi['khm_spells']] = 0x1 + 0x2 * 0x20 + 0xc * 0x400   # rows: Heal, Sizz, Oomph
    r.vm.g[r.gi['khm_rows']] = r.vm.g[r.gi['khm_spells']]
    r.vm.call(r.fn['khm_update'])
    check('panel: the gauge int (0x8A) 0x4D50 + MP 100 + after-cost 93 (Heal at the cursor)', hex(g.ints.get(0x1000008A, 0)),
          hex(0x4D500000 + 100 * 0x100 + 93))
    check('panel: the window int (0x8C) shown, Hero\'s magic', (g.ints.get(0x1000008C, 0) >> 16, g.ints.get(0x1000008C, 0) & 4),
          (0x4845, 4))
    check('panel: the rows int (0x8D)', g.ints.get(0x1000008D, 0) & 0xFFFFF, 0x1 + 0x2 * 0x20 + 0xc * 0x400)
    r.vm.g[r.gi['global32']] = R.f2i(-1.0)    # stick down: the cursor to row 1 (Sizz)
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global32']] = 0
    check('menu: stick down moves the cursor', r.vm.g.get(r.gi['khm_cursor']), 1)
    r.vm.g[r.gi['global32']] = R.f2i(-1.0)    # the stick came back (the first move waits for it), now down
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global32']] = R.f2i(0.0)
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['khm_cursor']] = 1
    g.press = {0}                               # attack casts
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('menu: attack casts Sizz (8 MP)', (r.vm.g.get(r.gi['khm_state']), r.vm.g.get(r.gi['khm_spell']), r.gf('ncp_mp')),
          (2, 2, 92.0))
    for _ in range(8):
        r.vm.call(r.fn['khm_update'])
    check('Sizz: copy article 8, level 0 in the custom slots at frame 6',
          [(x[0], x[2], x[3]) for x in g.articles], [(8, 0, 0)])
    check('Sizz: the custom slots put back', (g.ints[0x10000048], g.ints[0x1000009F]), (7, 11))
    for _ in range(80):
        r.vm.call(r.fn['khm_update'])
    check('menu: shut after the cast (panel window 0)', (r.vm.g.get(r.gi['khm_state']), g.ints.get(0x1000008C)), (0, 0))
    # Heal and Oomph
    for row, want in ((0, 'heal'), (2, 'oomph')):
        r.vm.g[r.gi['global4']] = 0
        r.vm.call(r.fn['khm_update'])
        r.vm.g[r.gi['global4']] = 0x175
        r.vm.call(r.fn['khm_update'])
        r.vm.g[r.gi['khm_spells']] = 0x1 + 0x2 * 0x20 + 0xc * 0x400
        r.vm.g[r.gi['khm_cursor']] = row
        g.press = {0}
        r.vm.call(r.fn['khm_update'])
        g.press = set()
        for _ in range(14):
            r.vm.call(r.fn['khm_update'])
        if want == 'heal':
            check('Heal: 11% off his damage at frame 6, 7 MP', (g.fvars.get(0x0F000117), r.gf('ncp_mp')), (19.0, 85.0))
        else:
            check('Oomph: 720 frames, the marker bits 0x80 + 0x20 (not in a special)',
                  (r.vm.g.get(r.gi['khm_attack_t']) > 700, r.vm.call(r.fn['khm_buff_bits'])), (True, 0xA0))
    # too little MP: greyed, the misfire, no MP spent
    r.setf('ncp_mp', 5.0)
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['khm_spells']] = 0x3
    r.vm.g[r.gi['khm_cursor']] = 0
    g.press = {0}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('Sizzle with 5 MP: greyed, nothing cast, MP kept', (r.vm.g.get(r.gi['khm_spell']), r.gf('ncp_mp')), (0, 5.0))
    # shield shuts it; the stone ending shuts it
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    g.press = {3}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('shield shuts the menu', r.vm.g.get(r.gi['khm_state']), 0)
    v3_tests(path, src)
    rr = Run(path, src, 3)
    rr.update()
    rr.vm.g[rr.gi['global4']] = 0x175
    rr.vm.call(rr.fn['khm_update'])
    check('Sephiroth copy: no menu, no gauge', (rr.vm.g.get(rr.gi['khm_state'], 0), rr.game.ints.get(0x1000008A)), (0, 0))


def main():
    path = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'fighters', 'kirby', 'kirby.c')
    # Hero: Frizzle
    r = Run(path, src, 2)
    r.update()
    check('Hero copy: MP full when the copy is new', r.gf('ncp_mp'), 100.0)
    r.start(held=[1])
    check('Hero: the start slot 0x446', r.game.motions[:1], [0x446])
    for _ in range(8):
        r.step()
    check('Hero: the hold slot 0x44B after the start', r.game.motions[-1], 0x44B)
    for _ in range(20):
        r.step()
    r.step(press=[1])
    check('Hero: Frizzle (20 frames held): slot 0x44A', r.game.motions[-1], 0x44A)
    check('Hero: Frizzle costs 16', r.gf('ncp_mp'), 84.0)
    for _ in range(12):
        r.step()
    check('Hero: the fireball (article 6) at frame 11, level 1 in 0x10000048 / 0x1000009F',
          [(a[0], a[1], a[2], a[3]) for a in r.game.articles], [(6, 11.0, 1, 1)])
    check('Hero: the slots put back', (r.game.ints[0x10000048], r.game.ints[0x1000009F]), (7, 11))
    for _ in range(60):
        r.step()
    check('Hero: wait (status 0) at the end', r.game.statuses[-1:], [0])
    # Hero: 10 MP, charge to Kafrizz (stored), then the stored charge casts what he pays for
    r = Run(path, src, 2)
    r.update()
    r.setf('ncp_mp', 10.0)
    r.start()
    for _ in range(8 + 82):
        r.step()
    check('Hero: Kafrizz charge stored at 81 (the cancel slot 0x447)', (r.game.motions[-1], r.vm.g.get(r.gi['ncp_stored'])),
          (0x447, 81))
    r.vm.g[r.gi['global4']] = 0
    r.start()
    for _ in range(9):
        r.step()
    check('Hero: the stored charge casts Frizz (all 10 MP pay for)', (r.game.motions[-1], r.gf('ncp_mp')), (0x448, 4.0))
    # Hero: 3 MP: the misfire
    r = Run(path, src, 2)
    r.update()
    r.setf('ncp_mp', 3.0)
    r.start()
    for _ in range(10):
        r.step()
    r.step(press=[1])
    check('Hero: too little MP: the misfire (slot 0x447), no fireball', (r.game.motions[-1], r.game.articles), (0x447, []))
    # Sephiroth: Megaflare, up
    r = Run(path, src, 3)
    r.update()
    r.start(held=[1])
    check('Sephiroth: the charge slot 0x446', r.game.motions[:1], [0x446])
    for _ in range(40):
        r.step(held=[1])
    r.step(stick_y=1.0)
    check('Sephiroth: released at 40: Megaflare slot 0x44A', r.game.motions[-1], 0x44A)
    for _ in range(14):
        r.step(stick_y=1.0)
    check('Sephiroth: the fire (article 7) at 13, 0x10000049 = level 1 + 4 x up', [(a[0], a[1], a[4]) for a in r.game.articles],
          [(7, 13.0, 5)])
    check('Sephiroth: 0x10000049 put back', r.game.ints[0x10000049], 9)
    # Sephiroth: Gigaflare in the air
    r = Run(path, src, 3, situation=2)
    r.update()
    r.start(held=[1])
    check('Sephiroth air: the charge slot 0x44D', r.game.motions[:1], [0x44D])
    for _ in range(122):
        r.step(held=[1])
    check('Sephiroth: Gigaflare made by the charge at 120 (level 2)', [(a[0], a[1], a[4]) for a in r.game.articles],
          [(7, 120.0, 2)])
    menu_tests(path, src)
    # the plain Robin copy
    r = Run(path, src, 0)
    check('Robin copy (no marker): newcopy_marker 0', r.vm.call(r.fn['newcopy_marker']), 0)
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
