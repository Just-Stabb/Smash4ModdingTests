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

Hero copy fix v1: the WorkModule model is the game's (tools/acmd_ext_cave.py nv_code, run in unicorn by
tools/kirby_hero_copy_fix_test.py and tools/new_var_test.py): category-F ids 0x300-0x3BF (VAR_n, timers, New_Var
slots 0x380 + k) are one float per id and object, read 0 until written, kept whether or not a New_Var declared them;
an int op reads the float cut toward 0 and writes the int as a float; 0x3C0-0x3FF read 0 and drop writes (any top
nibble). Before, the stub kept ints and floats in two maps, so an int write read back as a float stayed 0 and a
0x3C0+ write was kept. Also: the silence (MotionAnimcmdModule(0, 0x11, 0, 8), copy_fx_cave.py SILENCE) after every
motion change and every frame of the copy statuses; Kirby's copy voices and Sephiroth's sounds (tools/
kirby_copy_sound.py ids); the marker-less Robin copy's guess from the match's fighters; the A build (no sword
spells).
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
        self.sounds = []
        self.calls, self.removed, self.slow = [], [], []       # v6
        self.hit_now = False
        self.tag = lambda: None
        self.animcmd = []                                      # fix v1: MotionAnimcmdModule(0, set, motion, kind)
        self.nv = {}                                           # category-F user variables / New_Var slots (floats)
        self.stick_x, self.lr = 0.0, 0.0                       # fix v4: ControlModuleF(0), PostureModuleF(0)
        self.posture = []                                      # fix v4: PostureModule calls

    # fix v2: the copy article's spawner as the executable runs it (traced: tools/kirby_robin_book_cave.py). Robin's
    # thunder spawner 0x02F643A4 (the Robin copy's records 2, 6 and 8-12) first calls Robin's tome code 0x02F613B8
    # (owner, 0), which stores 0 into the owner's ints 0x9F / 0xA0 / 0xA1 / 0x90, then reads the custom number: Kirby
    # with a copy his 0x1000009F (copy_custom_cave.py). exe_v45h / v46f (book_fix) skip the tome code for a Kirby whose
    # marker 0x100000A0 is 2 / 3. Din's Fire's spawner (record 7, Sephiroth's fire) reads 0x10000049, no tome code.
    THUNDER_RECORDS = (2, 6, 8, 9, 10, 11, 12)
    book_fix = True

    def spawn(self, article):
        """the custom number the spawner gives the new weapon (its 0x10000005, a signed byte)"""
        if article == 7:
            return self.ints.get(0x10000049, 0)
        if article not in self.THUNDER_RECORDS:
            return None
        if not (self.book_fix and self.ints.get(0x100000A0) in (2, 3)):
            for i in (0x1000009F, 0x100000A0, 0x100000A1, 0x10000090):
                self.ints[i] = 0
        c = self.ints.get(0x1000009F if self.ints.get(0x100000A4, -1) < 0x3A else 0x10000048, 0)
        return ((c & 0xFF) ^ 0x80) - 0x80

    @staticmethod
    def user(ident):
        """the cave's user-variable index for a category-F id 0x300-0x3FF (any top nibble), else None"""
        if (ident >> 24) & 0xF == 0xF and 0x300 <= ident & 0xFFFFFF < 0x400:
            return ident & 0xFFFFFF
        return None

    def nv_get(self, ident):
        i = self.user(ident)
        return self.nv.get(i, 0.0) if i < 0x3C0 else 0.0

    def nv_set(self, ident, v):
        i = self.user(ident)
        if i < 0x3C0:
            self.nv[i] = float(v)

    def sys(self, sid, a):
        f = R.i2f
        if sid == 0x17 and len(a) == 2 and a[0] == 0:          # WorkModuleF(0, var): position variables
            if self.user(a[1]) is not None:
                return R.f2i(self.nv_get(a[1]))
            return R.f2i(self.fvars.get(a[1], 0.0))
        if sid == 0x4B and a and a[0] == 0 and len(a) == 4:    # fix v1: MotionAnimcmdModule(0, set, motion, kind)
            self.animcmd.append((len(self.motions), a[1], a[2], a[3]))
            return 0
        if sid == 0x16:                                         # WorkModule
            if a[0] == 0 and len(a) == 3:                       # WorkModule(0, value, var): set a float variable
                if self.user(a[2]) is not None:
                    self.nv_set(a[2], R.i2f(a[1]))
                    return 0
                self.fvars[a[2]] = R.i2f(a[1])
                return 0
            if a[0] == 0x6:
                if self.user(a[1]) is not None:                 # the cave: the float cut toward 0
                    return int(self.nv_get(a[1])) & 0xFFFFFFFF
                return self.ints.get(a[1], 0)
            if a[0] == 0x7:
                if self.user(a[2]) is not None:
                    v = a[1] - (1 << 32) if a[1] & 0x80000000 else a[1]
                    self.nv_set(a[2], v)
                    return 0
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
        if sid == 0xF and a == [0]:
            return R.f2i(self.stick_x)
        if sid == 0x15 and a == [0]:
            return R.f2i(self.lr)
        if sid == 0x14 and a:
            self.posture.append(list(a))
            if a[0] == 0 and len(a) == 2:
                self.lr = R.i2f(a[1])
            return 0
        if sid == 0x20 and a and a[0] == 0x2710:                # ArticleModule generate
            self.articles.append((a[1], self.frame, self.ints.get(0x10000048), self.ints.get(0x1000009F),
                                  self.ints.get(0x10000049), self.spawn(a[1])))
            return 0
        if sid == 0x10 and len(a) == 3 and a[0] == 0x11 and a[1] == 1:   # KineticModule(0x11, 1, v): speed
            self.speeds.append(R.i2f(a[2]))
            return 0
        if sid == 0x1E and a and a[0] in (0x2710, 0x2714):           # SoundModule play / stop
            self.sounds.append((a[0], a[1]))
            self.calls.append((self.tag(), 'sound' if a[0] == 0x2710 else 'stop', list(a[1:])))
            return 0
        if sid == 0x1C and a and a[0] in (0x2717, 0x2710):
            self.effects.append(a[1])
            if a[0] == 0x2710:
                self.calls.append((self.tag(), 'effect', list(a[1:])))
            return 0
        if sid == 0x1C and a and a[0] in (0x2712, 0x2723):             # v6: EffectModule follow / kill
            self.calls.append((self.tag(), 'follow' if a[0] == 0x2712 else 'kill', list(a[1:])))
            return 0
        if sid == 0x2E and a and a[0] == 0x272C:                     # v6: AttackModule hitbox (Extended_Special_Hitbox)
            self.calls.append((self.tag(), 'hitbox', list(a[1:])))
            return 0
        if sid == 0x2E and a and a[0] == 0x2718:                     # AttackModule remove one
            self.removed.append(a[1])
            return 0
        if sid == 0x2E and a and a[0] == 0x2726:                     # AttackModule hit this frame (kinds)
            return int(self.hit_now and (len(a) < 2 or a[1] & 2 != 0))
        if sid == 0x49:                                               # SlowModule
            self.slow.append(list(a))
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


def slot_table(src):
    """kirby.c's Hero-copy state kept in New_Var slots (crash fix v2): {name: (type, id)}"""
    return {n: (t, int(i, 16)) for n, t, i in re.findall(r'^//\s+(khm_\w+)\s+(int|float)\s+0x([0-9A-Fa-f]{8})\s*$',
                                                         open(src).read(), re.M)}


def kget(r, name):
    """a khm_* value: its New_Var slot (the cave's float, read as the MSC's op reads it), or its global in an older
    build"""
    if name in r.slots:
        t, i = r.slots[name]
        v = r.game.nv_get(i)
        return v if t == 'float' else int(v) & 0xFFFFFFFF
    return r.vm.g.get(r.gi[name], 0)


def kset(r, name, v):
    if name in r.slots:
        t, i = r.slots[name]
        r.game.nv_set(i, v if t == 'float' else (v - (1 << 32) if v & 0x80000000 else v))
    else:
        r.vm.g[r.gi[name]] = v


class Run:
    def __init__(self, path, src, marker, situation=0):
        self.vm = R.VM(path)
        self.slots = slot_table(src)
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
    kset(r, 'khm_spells', spell)
    kset(r, 'khm_cursor', 0)
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
    check('Kamikazee: the crash (article 12) at 20, level 1 (fix v3: no slot; placed.c finds Kirby)', [(x[0], x[2]) for x in g.articles], [(12, 1)])
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
    check('Bounce: 720 frames of reflector', kget(r, 'khm_reflect_t') > 700, True)
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
    check('Zoom: done on landing', kget(r, 'khm_sub'), 0x7f)
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
    # v4: Zoom 2 U (the target: slot 1 at (50, 0); he is at (10, 0) in the air)
    r = Run(path, src, 2, situation=2)
    g = r.game
    r.update()
    g.fvars.update({0x0F000000: 10.0, 0x0F000001: 0.0, 0x0F000020: 10.0, 0x0F000021: 0.0, 0x0F000023: 1.0,
                    0x0F000024: 50.0, 0x0F000025: 0.0, 0x0F000027: 1.0, 0x03000019: 2.0})
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    kset(r, 'khm_spells', 0x17)
    kset(r, 'khm_cursor', 0)
    g.press = {0}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    xs = []
    for _ in range(36):
        r.vm.call(r.fn['khm_update'])
        g.fvars[0x0F000020] = g.fvars[0x0F000000]    # his own slot's variables follow him
        g.fvars[0x0F000021] = g.fvars[0x0F000001]
        xs.append(round(g.fvars[0x0F000000], 3))
    check('Zoom 2 U: target the nearest (slot 1)', kget(r, 'khm_z2_target'), 1)
    check('Zoom 2 U: still before 29, then 9 a frame at the target until within 15 (stops at x 35.x)',
          (xs[29], xs[31] - xs[30] > 8.0, kget(r, 'khm_sub')), (10.0, True, 0x7f))
    check('Zoom 2 U: within 15 of the target\'s feet + 6 at the end', abs(50.0 - xs[-1]) <= 15.0 + 1e-3, True)
    check('Zoom 2 U: intangible while flying', g.fvars.get(0x0F00011B), 2.0)


def menu_tests(path, src):
    """stage 2: Stone (status 0x175) = Hero's Command Selection (kirby.c khm_*)"""
    r = Run(path, src, 2)
    g = r.game
    r.update()
    g.fvars[0x0F000117] = 30.0                  # his damage (Heal)
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    check('menu: opens when the stone starts', kget(r, 'khm_state'), 1)
    check('menu: blocks the stone\'s special while open', r.vm.call(r.fn['khm_blocking']), 1)
    kset(r, 'khm_spells', 0x1 + 0x2 * 0x20 + 0xc * 0x400)   # rows: Heal, Sizz, Oomph
    kset(r, 'khm_rows', kget(r, 'khm_spells'))
    r.vm.call(r.fn['khm_update'])
    check('panel: the gauge int (0x8A) 0x4D50 + MP 100 + after-cost 93 (Heal at the cursor)', hex(g.ints.get(0x1000008A, 0)),
          hex(0x4D500000 + 100 * 0x100 + 93))
    check('panel: the window int (0x8C) shown, Hero\'s magic', (g.ints.get(0x1000008C, 0) >> 16, g.ints.get(0x1000008C, 0) & 4),
          (0x4845, 4))
    check('panel: the rows int (0x8D)', g.ints.get(0x1000008D, 0) & 0xFFFFF, 0x1 + 0x2 * 0x20 + 0xc * 0x400)
    r.vm.g[r.gi['global32']] = R.f2i(-1.0)    # stick down: the cursor to row 1 (Sizz)
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global32']] = 0
    check('menu: stick down moves the cursor', kget(r, 'khm_cursor'), 1)
    r.vm.g[r.gi['global32']] = R.f2i(-1.0)    # the stick came back (the first move waits for it), now down
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global32']] = R.f2i(0.0)
    r.vm.call(r.fn['khm_update'])
    kset(r, 'khm_cursor', 1)
    g.press = {0}                               # attack casts
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('menu: attack casts Sizz (8 MP)', (kget(r, 'khm_state'), kget(r, 'khm_spell'), r.gf('ncp_mp')),
          (2, 2, 92.0))
    for _ in range(8):
        r.vm.call(r.fn['khm_update'])
    check('Sizz: copy article 8, level 0 in the custom slots at frame 6',
          [(x[0], x[2], x[3]) for x in g.articles], [(8, 0, 0)])
    check('Sizz: the custom slots put back', (g.ints[0x10000048], g.ints[0x1000009F]), (7, 11))
    for _ in range(80):
        r.vm.call(r.fn['khm_update'])
    check('menu: shut after the cast (panel window 0)', (kget(r, 'khm_state'), g.ints.get(0x1000008C)), (0, 0))
    # Heal and Oomph
    for row, want in ((0, 'heal'), (2, 'oomph')):
        r.vm.g[r.gi['global4']] = 0
        r.vm.call(r.fn['khm_update'])
        r.vm.g[r.gi['global4']] = 0x175
        r.vm.call(r.fn['khm_update'])
        kset(r, 'khm_spells', 0x1 + 0x2 * 0x20 + 0xc * 0x400)
        kset(r, 'khm_cursor', row)
        g.press = {0}
        r.vm.call(r.fn['khm_update'])
        g.press = set()
        for _ in range(14):
            r.vm.call(r.fn['khm_update'])
        if want == 'heal':
            check('Heal: 11% off his damage at frame 6, 7 MP', (g.fvars.get(0x0F000117), r.gf('ncp_mp')), (19.0, 85.0))
        else:
            check('Oomph: 720 frames, the marker bits 0x80 + 0x20 (not in a special)',
                  (kget(r, 'khm_attack_t') > 700, r.vm.call(r.fn['khm_buff_bits'])), (True, 0xA0))
    # too little MP: greyed, the misfire, no MP spent
    r.setf('ncp_mp', 5.0)
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    kset(r, 'khm_spells', 0x3)
    kset(r, 'khm_cursor', 0)
    g.press = {0}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('Sizzle with 5 MP: greyed, nothing cast, MP kept', (kget(r, 'khm_spell'), r.gf('ncp_mp')), (0, 5.0))
    # shield no longer shuts it (fix v3: it opens again at once; fix_v3_tests)
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    g.press = {3}
    r.vm.call(r.fn['khm_update'])
    g.press = set()
    check('fix v3: shield doesn\'t shut the menu (it opens again at once)', kget(r, 'khm_state'), 1)
    v3_tests(path, src)
    rr = Run(path, src, 3)
    rr.update()
    rr.vm.g[rr.gi['global4']] = 0x175
    rr.vm.call(rr.fn['khm_update'])
    check('Sephiroth copy: no menu, no gauge', (kget(rr, 'khm_state'), rr.game.ints.get(0x1000008A)), (0, 0))


def v6_tests(path, src):
    """v6: the sword spells (17 Flame Slash, 18 Kacrackle Slash, 19 Metal Slash, 20 Hatchet Man): Hero's script
    commands at their frames (tools/kirby_hero_sword_msc.py's events), the held sword's int, the functions"""
    import kirby_hero_sword_msc as SW
    ev = SW.events(SW.parse())
    names = {0x11: 'Flame Slash', 0x12: 'Kacrackle Slash', 0x13: 'Metal Slash', 0x14: 'Hatchet Man'}
    for n in (0x11, 0x12, 0x13, 0x14):
        for sit, situation in (('ground', 0), ('air', 2)):
            r = Run(path, src, 2, situation=situation)
            g = r.game
            r.update()
            g.tag = lambda r=r: kget(r, 'khm_frame') if kget(r, 'khm_state') == 2 else None
            mp0 = r.gf('ncp_mp')
            shown = []

            def each(r):
                shown.append(r.game.ints.get(0x1000008B, 0))
            cast(r, n, ev[n]['end'] + 5, each)
            end = ev[n]['end']

            def norm(lst, bits):
                return [(f, k, [round(R.i2f(x) if bits else float(x), 4) if SW.is_float(k, i) else x
                                for i, x in enumerate(v)]) for f, k, v in lst]
            want = norm([(f, k, v) for f, k, v in ev[n][sit] if k != 'remove'], False)
            got = norm([(f, k, v) for f, k, v in g.calls if f is not None and f < end], True)
            check('%s (%s): Hero\'s %d hitbox / effect / sound commands at their frames, Kirby\'s bones'
                  % (names[n], sit, len(want)), got, want)
            rm = [f for f, k, _v in ev[n][sit] if k == 'remove']
            check('%s (%s): hitboxes 5-9 removed at %s, and at the end' % (names[n], sit, rm),
                  g.removed, [5, 6, 7, 8, 9] * (len(rm) + 1))
            check('%s (%s): the sword int 0x1000008B 1 from the cast to the end (%d), then 0' % (names[n], sit, end),
                  (set(shown[:end]), set(shown[end + 1:])), ({1}, {0}))
            check('%s: its MP (brave_cost)' % names[n], mp0 - r.gf('ncp_mp'), {0x11: 12, 0x12: 11, 0x13: 6, 0x14: 15}[n])
    # the menu's weights, Hocus Pocus's
    r = Run(path, src, 2)
    if not re.search(r'^int khm_sword_on\(\) \{ return 0; \}', open(src).read(), re.M):   # the B build (fix v1)
        check('weights (brave_lw_weight): 0x12 / 0x12 / 0x7 / 0x12',
              [r.vm.call(r.fn['khm_weight'], (n,)) for n in (0x11, 0x12, 0x13, 0x14)], [0x12, 0x12, 0x7, 0x12])
        check('Hocus Pocus: the sword spells 244 each (Ultimate\'s), Zoom 2 U still 0',
              [r.vm.call(r.fn['khm_hp_weight'], (o + 9,)) for o in (0x11, 0x12, 0x13, 0x14, 0x17)], [244] * 4 + [0])
    # Hatchet Man: always critical, the show on the hit; special doesn't end the stone before the cancel frame
    r = Run(path, src, 2)
    g = r.game
    r.update()
    a, b = ev[0x14]['hitbox']
    blocked = []

    def hit_at(r):
        f = kget(r, 'khm_frame')
        r.game.hit_now = f == a + 1
        blocked.append((f, r.vm.call(r.fn['khm_blocking'])))
    cast(r, 0x14, a + 3, hit_at)
    check('Hatchet Man: the crit show on the hit (SlowModule(0, 4, 40), camera in, se_brave_criticalhit)',
          (g.slow, g.fvars.get(0x0F000099), (0x2710, 0x7640112) in g.sounds), ([[0, 4, 40]], 8.0, True))
    for _ in range(45):
        r.vm.call(r.fn['khm_update'])
    check('Hatchet Man: the camera back after 40 frames', g.fvars.get(0x0F000099), 9.0)
    check('Hatchet Man: special held off before the cancel frame (%d)' % ev[0x14]['cancel'],
          all(b for f, b in blocked if f < ev[0x14]['cancel']), True)
    check('Hatchet Man: no x2 crit bit (its damage is Ultimate\'s crit already)', r.vm.call(r.fn['khm_sw_crit_bit']), 0)
    # Metal Slash: metal on the fighter hit; KO on one already metal; nothing on a shield
    for metal, status, want in ((0.0, 0x48, (1.0, None)), (1.0, 0x48, (1.0, 1.0)), (0.0, 28, (None, None))):
        r = Run(path, src, 2)
        g = r.game
        r.update()
        g.fvars[0x0F0000B2] = float(status)
        if metal:
            g.fvars[0x0F000278] = metal
        a, b = ev[0x13]['hitbox']
        cast(r, 0x13, a + 4, lambda r: setattr(r.game, 'hit_now', kget(r, 'khm_frame') == a + 1))
        got = (g.fvars.get(0x0F000278) if not metal else 1.0, g.fvars.get(0x0F00015F))
        check('Metal Slash: target metal %s, status 0x%X -> (metal, KO) %s' % (bool(metal), status, want),
              got if status != 28 else (g.fvars.get(0x0F000278), g.fvars.get(0x0F00015F)), want)
    # Flame Slash: the 1-in-8 crit (the VM's randi gives 0: rolled) -> the marker's x2 bit during the cast
    r = Run(path, src, 2)
    r.update()
    bits = []
    cast(r, 0x11, 8, lambda r: bits.append(r.vm.call(r.fn['khm_sw_crit_bit'])))
    check('Flame Slash crit rolled: the x2 bit 0x10 while its hitboxes are made', set(bits), {0x10})
    # Oomph doesn't boost a sword spell
    kset(r, 'khm_attack_t', 100)
    check('Oomph: no 0x20 during the sword spell (Hero\'s specials)', r.vm.call(r.fn['khm_buff_bits']) & 0x20, 0)
    # the stone ends mid-cast: everything stopped
    r = Run(path, src, 2)
    g = r.game
    r.update()
    cast(r, 0x14, 38)
    r.vm.g[r.gi['global4']] = 0x2
    r.vm.call(r.fn['khm_update'])
    check('stone ended mid-cast: hitboxes removed, the long sound stopped, the sword hidden',
          (g.removed[-5:], (0x2714, 0x76400E2) in g.sounds, g.ints.get(0x1000008B)), ([5, 6, 7, 8, 9], True, 0))


def fix_v1_tests(path, src):
    """Hero copy fix v1: the marker-less Robin copy's guess; the A build's sword spells"""
    def marker(m, kinds):
        r = Run(path, src, m)
        for s_, k in enumerate(kinds):
            r.game.fvars[0x0F0000BD + 8 * s_] = float(k)
        for s_ in range(len(kinds), 8):
            r.game.fvars[0x0F0000BD + 8 * s_] = -1.0
        r.update()
        return r.vm.call(r.fn['newcopy_marker']), r.vm.call(r.fn['newcopy_real_kind'])
    check('guess: no marker, Kirby vs Hero: the Hero copy (and its kind 0x45)', marker(0, [8, 0x45]), (2, 0x45))
    check('guess: no marker, Kirby vs Sephiroth: Sephiroth\'s', marker(0, [8, 0x42]), (3, 0x42))
    check('guess: no marker with a Robin in the match: Robin\'s', marker(0, [8, 0x45, 0x2C]), (0, 0x2C))
    check('guess: no marker with both Hero and Sephiroth: Robin\'s', marker(0, [8, 0x45, 0x42]), (0, 0x2C))
    check('guess: the marker wins (Sephiroth\'s marker, a Hero in the match)', marker(3, [8, 0x45]), (3, 0x42))
    check('guess: Supamario\'s marker 1 isn\'t touched', marker(1, [8, 0x45])[0], 0)
    sword = 0 if re.search(r'^int khm_sword_on\(\) \{ return 0; \}', open(src).read(), re.M) else 1
    r = Run(path, src, 2)
    got = [r.vm.call(r.fn['khm_weight'], [n]) for n in (0x11, 0x12, 0x13, 0x14)] + \
        [r.vm.call(r.fn['khm_hp_weight'], [0x9 + n]) for n in (0x11, 0x12, 0x13, 0x14)]
    check('sword spells %s (khm_sword_on %d: the %s build)' % ('drawn' if sword else 'never drawn', sword,
                                                              'B' if sword else 'A'),
          got, [0x12, 0x12, 0x7, 0x12, 0xf4, 0xf4, 0xf4, 0xf4] if sword else [0] * 8)


def fix_v2_tests(path, src):
    """Hero copy fix v2: the level reaches the article (the spawner's custom number), the marker survives a fire, the
    Stone's projectiles carry their caster"""
    def frizz(book_fix, hold):
        r = Run(path, src, 2)
        r.game.book_fix = book_fix
        r.update()
        r.start()
        for _ in range(8 + hold):
            r.step()
        r.step(press=[1])
        for _ in range(20):
            r.step()
        return r
    r = frizz(False, 20)
    check('fix v2, the old executable modelled (Robin\'s tome code before the read): Frizzle\'s fireball gets custom 0 '
          '(Frizz: the user\'s report) and the marker 0xA0 is lost',
          ([a[5] for a in r.game.articles], r.game.ints.get(0x100000A0)), ([0], 0))
    for hold, level, name in ((5, 0, 'Frizz'), (20, 1, 'Frizzle'), (60, 1, 'Frizzle (60)')):
        r = frizz(True, hold)
        check('fix v2 (exe_v45h / v46f): %s: the fireball\'s custom number %d, the marker kept (2)' % (name, level),
              ([a[5] for a in r.game.articles], r.game.ints.get(0x100000A0)), ([level], 2))
    # Kafrizz: charged to 81 (stored), then cast at once by the next special
    r = Run(path, src, 2)
    r.update()
    r.start()
    for _ in range(8 + 82):
        r.step()
    r.vm.g[r.gi['global4']] = 0
    r.start()
    for _ in range(30):
        r.step()
    check('fix v2: the stored Kafrizz: custom number 2', [a[5] for a in r.game.articles], [2])
    # fix v3: the Stone's projectiles carry the level alone again (fix v2's level + 4 x (slot + 1) drew them invisible)
    for spell, art, level in ((0x2, 8, 0), (0x3, 8, 1), (0x4, 9, 0), (0x5, 9, 1), (0x6, 10, 0), (0x7, 10, 1),
                              (0xe, 11, 0)):
        for slot in (0, 2):
            r = Run(path, src, 2)
            g = r.game
            g.fvars.update({0x0F000000: 30.0, 0x0F000001: 5.0})
            for s_ in range(8):
                g.fvars[0x0F000020 + 4 * s_] = 30.0 if s_ == slot else -50.0 - 10 * s_
                g.fvars[0x0F000021 + 4 * s_] = 5.0 if s_ == slot else 0.0
                g.fvars[0x0F000023 + 4 * s_] = 1.0 if s_ in (slot, 1) else 0.0
            r.update()
            cast(r, spell, 10)
            c = [a[5] for a in g.articles if a[0] == art]
            check('fix v3: spell 0x%X from slot %d: article %d, custom %r = the level %d (0-3: port_check W10)'
                  % (spell, slot, art, c, level), c, [level])
    check('fix v2: Sephiroth\'s fire (Din\'s spawner) as before', Game.THUNDER_RECORDS.count(7), 0)


def fix_v3_tests(path, src):
    """Hero copy fix v3: Acceleration as Hero's (x1.2 animations, the blue glow every frame); the menu cancelled
    opens again; down special in the air with the menu shut drops him as Kirby's own Stone"""
    r = Run(path, src, 2)
    g = r.game
    r.update()
    cast(r, 0x16, 15)
    check('Acceleration: the animation rate 1.2 (0x0F000098)', g.fvars.get(0x0F000098), 1.2000000476837158)
    n = len([e for e in g.effects if e == 0x10000C7])
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    check('Acceleration: the blue glow 0x10000C7 made again every frame on 4 joints',
          len([e for e in g.effects if e == 0x10000C7]) - n, 4)
    check('Acceleration: the stat bit 0x1000 in the marker', (r.vm.call(r.fn['khm_buff_bits']) & 0x1000) != 0, True)
    for _ in range(600):
        r.vm.call(r.fn['khm_update'])
    check('Acceleration over after 600: the rate back to 1.0, the glow off', (g.fvars.get(0x0F000098),
          kget(r, 'khm_accel_t') if 'khm_accel_t' in r.slots else 0), (1.0, 0))
    # the menu: shield / jump reopen it
    r = Run(path, src, 2)
    g = r.game
    r.update()
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    spells = kget(r, 'khm_spells')
    for _ in range(30):
        r.vm.call(r.fn['khm_update'])
    for btn, name in ((3, 'shield'), (2, 'jump')):
        g.press = {btn}
        g.sounds = []
        kset(r, 'khm_spells', 0x1F * 0x8421)    # fix v4: a stand-in draw, to see it drawn again
        r.vm.call(r.fn['khm_update'])
        g.press = set()
        r.vm.call(r.fn['khm_update'])
        check('the menu cancelled with %s: still open (state 1), fix v4: four spells drawn anew (the VM\'s randi 0: '
              'the first draw\'s), its time from 0, the open sound'
              % name, (kget(r, 'khm_state'), kget(r, 'khm_spells'), kget(r, 'khm_frame') <= 2,
                       (0x2710, 0x76400DD) in g.sounds), (1, spells, True, True))
    for _ in range(0x1e0):
        r.vm.call(r.fn['khm_update'])
    check('its 8 seconds up: shut', kget(r, 'khm_state'), 0)

    # Magic Burst / Kamikazee: custom 0-3 (placed.c finds Kirby)
    for mp, want in ((100.0, 0), (70.0, 0), (50.0, 3), (10.0, 3)):
        for slot in (0, 2):
            r = Run(path, src, 2)
            g = r.game
            for s_ in range(8):
                g.fvars[0x0F000020 + 4 * s_] = 30.0 if s_ == slot else -50.0 - 10 * s_
                g.fvars[0x0F000023 + 4 * s_] = 1.0 if s_ in (slot, 1) else 0.0
            g.fvars.update({0x0F000000: 30.0, 0x0F000001: 0.0})
            r.update()
            r.setf('ncp_mp', mp)
            cast(r, 0x8, 25)
            check('Magic Burst with %d MP from slot %d: custom %d (0 full / 3 the x0.2 tier)' % (mp, slot, want),
                  [a[5] for a in g.articles if a[0] == 12], [want])

    def stone(air, state, press=True, down=True, sub=0x7f):
        r = Run(path, src, 2, situation=2 if air else 0)
        r.update()
        r.vm.g[r.gi['global4']] = 0x175
        kset(r, 'khm_state', state)
        kset(r, 'khm_sub', sub)
        r.game.press = {1} if press else set()
        r.vm.g[r.gi['global24']] = 0x8000 if down else 0x1000
        r.game.statuses = []
        got = r.vm.call(r.fn['khm_stone_drop'])
        return r, got
    r, got = stone(True, 0)
    check('down special in the air, the menu shut: down special starts over (0x155), '
          'khm_plain set', (got, r.game.statuses, kget(r, 'khm_plain')), (1, [0x155], 1))
    r.vm.g[r.gi['global4']] = 0x155
    r.vm.call(r.fn['khm_update'])
    r.vm.g[r.gi['global4']] = 0x175
    r.vm.call(r.fn['khm_update'])
    check('...and its hold opens no menu (Kirby\'s own Stone)', kget(r, 'khm_state'), 0)
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['khm_update'])
    check('...until the stone ends (khm_plain cleared)', kget(r, 'khm_plain'), 0)
    for args, name in (((False, 0), 'on the ground'), ((True, 1), 'the menu open'), ((True, 2), 'a spell cast'),
                       ((True, 0, False), 'no special press'), ((True, 0, True, False), 'neutral special'),
                       ((True, 0, True, True, 1), 'Zoom still going')):
        r, got = stone(*args)
        check('no drop: %s' % name, (got, r.game.statuses), (0, []))


def fcall(r, name, default=None):
    """a kirby.c function's value, or `default` when this build has none (fix v4's run on an older MSC)"""
    return r.vm.call(r.fn[name]) if name in r.fn else default


def fix_v4_tests(path, src):
    """Hero copy fix v4: the reopened menu draws anew; Zoom / Zoom 2 U keep him in the stone and stop at a KO (the
    double KO); Kamikazee's KO not after a KO; the cast turns him to the stick held back"""
    # Zoom: the stone's ends held off from the choice to the flight's end, invincible before the launch
    for spell, name in ((0x10, 'Zoom'), (0x17, 'Zoom 2 U')):
        r = Run(path, src, 2)
        g = r.game
        r.update()
        g.fvars.update({0x0F000000: 10.0, 0x0F000001: 0.0, 0x0F000020: 10.0, 0x0F000023: 1.0,
                        0x0F000024: 50.0, 0x0F000027: 1.0})
        cast(r, spell, 10)
        check('%s: before the launch, zooming, the stone\'s special end blocked, invincible (0x0F00011C)' % name,
              (fcall(r, 'khm_zooming'), r.vm.call(r.fn['khm_blocking']), g.fvars.get(0x0F00011C)), (1, 1, 2.0))
        g.statuses = []
        g.press = {1}
        r.vm.call(r.fn['func_2323'])
        g.press = set()
        check('%s: special in the stone\'s hold (0x175) doesn\'t end it (no 0x176)' % name, g.statuses, [])
        g.ints[0x18000000] = 0
        r.vm.call(r.fn['func_2323'])
        check('%s: nor its ground timer' % name, g.statuses, [])
        r.vm.g[r.gi['global24']] = 0x8000
        r.vm.g[r.gi['global18']] = 2
        g.press = {1}
        check('%s: nor the air drop' % name, r.vm.call(r.fn['khm_stone_drop']), 0)
        g.press = set()
        r.vm.g[r.gi['global18']] = 0
        # the double KO: KO'd before the launch (the stone falling past the bottom line), the spell stops there
        r.vm.g[r.gi['global4']] = 0xB1
        g.speeds = []
        n_post = len(g.posture)
        g.fvars[0x0F000000], g.fvars[0x0F000001] = -500.0, -300.0
        for k in range(200):
            if k == 60:
                r.vm.g[r.gi['global4']] = 0xB2      # the respawn
            if k == 120:
                r.vm.g[r.gi['global4']] = 0
            r.vm.call(r.fn['khm_update'])
        check('%s: KO\'d mid-cast (0xB1): the cast over (state 0, sub 0x7F), and through the KO / respawn nothing of '
              'it: no flight speed, his position untouched (the double KO: Zoom went on, put him 120 above a fighter '
              'and pushed him down at 7 a frame)' % name,
              (kget(r, 'khm_state'), kget(r, 'khm_sub'), g.speeds, (g.fvars[0x0F000000], g.fvars[0x0F000001]),
               len(g.posture) - n_post), (0, 0x7f, [], (-500.0, -300.0), 0))
        check('%s: over: the stone\'s ends free again' % name, (fcall(r, 'khm_zooming'),
                                                               r.vm.call(r.fn['khm_blocking'])), (0, 0))
    # Zoom left by another way (not a KO) mid-flight: stopped, the fall put back
    r = Run(path, src, 2)
    g = r.game
    r.update()
    g.fvars.update({0x0F000000: 10.0, 0x0F000020: 10.0, 0x0F000023: 1.0})
    cast(r, 0x10, 35)
    r.vm.g[r.gi['global4']] = 0xE
    r.vm.call(r.fn['khm_update'])
    check('Zoom: out of the stone mid-flight (status 0xE): stopped (sub 0x7F, state 0)', (kget(r, 'khm_sub'), kget(r, 'khm_state')),
          (0x7f, 0))
    # Kamikazee: KO'd before 49: no KO flag after the respawn
    r = Run(path, src, 2)
    g = r.game
    r.update()
    cast(r, 0x9, 25)
    r.vm.g[r.gi['global4']] = 0xB1
    for k in range(60):
        if k == 30:
            r.vm.g[r.gi['global4']] = 0
        r.vm.call(r.fn['khm_update'])
    check('Kamikazee KO\'d at 25 (0xB1): no "causes KO" flag after it (a second KO)', 0x20000043 in g.flags, False)
    # the cast turns him to the stick held back (Hero's brave_lw_loop), not to one held forward or neutral
    for lr, sx, turned in ((1.0, -1.0, True), (1.0, -0.3, False), (1.0, 1.0, False), (-1.0, 1.0, True),
                           (-1.0, 0.0, False)):
        r = Run(path, src, 2)
        g = r.game
        r.update()
        g.lr, g.stick_x = lr, sx
        cast(r, 0x2, 8)
        check('the cast, facing %+d, stick x %+.1f: %s' % (lr, sx, 'turned round (PostureModule(0, %+d), then 2)' % -lr
                                                         if turned else 'his facing kept'),
              [p for p in g.posture if p[0] in (0, 2)], [[0, R.f2i(-lr)], [2]] if turned else [])
        check('...the Sizz made after it (frame 6)', [a[0] for a in g.articles], [8])


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
    check('Hero sounds: the charge n01 (0x76400AA), stopped at the fire, Frizzle\'s n03 (0x76400AD) at 11',
          [x for x in r.game.sounds if x[1] in (0x76400AA, 0x76400AD)],
          [(0x2710, 0x76400AA), (0x2714, 0x76400AA), (0x2710, 0x76400AD)])
    check('fix v1: Hero voices: vc_kirby_copy_brave_01 (0x3F002F) at the hold, stopped at the fire, _03 (0x3F0031) '
          'with Frizzle', [x for x in r.game.sounds if x[1] >> 16 == 0x3F], [(0x2710, 0x3F002F), (0x2714, 0x3F002F),
                                                                           (0x2710, 0x3F0031)])
    check('fix v1: every animcmd call is the silence (set 0x11, kind 8): none of Robin\'s scripts',
          sorted(set(x[1:] for x in r.game.animcmd)), [(0x11, 0, 8)])
    check('fix v1: silenced after every motion change (the change\'s own frame)',
          all(any(c[0] >= k + 1 for c in r.game.animcmd) for k in range(len(r.game.motions))), True)
    n0 = len(r.game.animcmd)
    for _ in range(60):
        r.step()
    check('fix v1: silenced every frame of the status', len(r.game.animcmd) - n0 >= 60, True)
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
    check('fix v1: Sephiroth sounds: the charge n01 (0xA00D5) at 1 and vc_kirby_copy_edge_01 (0x3F0033) at 2, n01 '
          'stopped at the fire, Megaflare n03_01 (0xA00D7) at 2 and edge_03 (0x3F0035) at 12',
          [x for x in r.game.sounds if x[1] >> 16 in (0xA, 0x3F)],
          [(0x2710, 0xA00D5), (0x2710, 0x3F0033), (0x2714, 0xA00D5), (0x2710, 0xA00D7), (0x2710, 0x3F0035)])
    check('fix v1: Sephiroth silenced too', sorted(set(x[1:] for x in r.game.animcmd)), [(0x11, 0, 8)])
    # Sephiroth: Gigaflare in the air
    r = Run(path, src, 3, situation=2)
    r.update()
    r.start(held=[1])
    check('Sephiroth air: the charge slot 0x44D', r.game.motions[:1], [0x44D])
    for _ in range(122):
        r.step(held=[1])
    check('Sephiroth: Gigaflare made by the charge at 120 (level 2)', [(a[0], a[1], a[4]) for a in r.game.articles],
          [(7, 120.0, 2)])
    check('fix v1: Gigaflare: n04_01 (0xA00D8) and vc_kirby_copy_edge_04 (0x3F0036) at 119',
          [x for x in r.game.sounds if x[1] in (0xA00D8, 0x3F0036)], [(0x2710, 0x3F0036), (0x2710, 0xA00D8)])
    r.vm.g[r.gi['global4']] = 0
    r.vm.call(r.fn['newcopy_n_end'])
    check('fix v1: the status\'s end stops the charge sound', r.game.sounds[-1:], [(0x2714, 0xA00D5)])
    fix_v1_tests(path, src)
    fix_v2_tests(path, src)
    fix_v3_tests(path, src)
    fix_v4_tests(path, src)
    menu_tests(path, src)
    if 'khm_sword' in names(src)[0]:
        v6_tests(path, src)
    # the plain Robin copy
    r = Run(path, src, 0)
    check('Robin copy (no marker): newcopy_marker 0', r.vm.call(r.fn['newcopy_marker']), 0)
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
