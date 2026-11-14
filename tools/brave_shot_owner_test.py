#!/usr/bin/env python3
"""Hero's Command Selection projectiles (fighters/brave/weapons/shot.c, Kirby's Hero copy fix v2): the caster from the
custom number. Compiles each shot article's MSC as tools/brave_build.py does (thunder_base.c + shot.c + the article)
and runs its status 0 main (sh_main) in tools/rolloff_hold_test.py's interpreter with the custom number (the weapon's
0x10000005) and the position variables stubbed:

  python3 tools/brave_shot_owner_test.py [OUT_DIR]

- Kirby's Hero copy (fix v3: kirby.c khm_generate sends the level alone, 0 / 1, as fix v2's level + 4 x (slot + 1)
  drew the projectiles invisible): the caster is a Kirby in his stone (0x155 / 0x175 / 0x176) within 30 of the
  article, even with an opponent Hero nearer to it (the old search took that Hero: Whack left him out of its targets
  and rolls, the user's "Whack can't hit an enemy Hero");
- Hero's own (brave.c: the level alone): the search as before (the nearest Hero or Kirby to the article), a stone
  Kirby far from it or a Kirby not in the stone not taken; level + 4 x (slot + 1) still read;
- deathball (Whack): its first frame's target is the opponent nearest to it, never the caster.
- fix v4 (the user: the Stone's spells hit everyone but Hero): cast from the stone, the projectile is put on its
  caster's plane (PostureModule(3, its x, its y, the caster's position-variable Z)); Hero's own casts are left where
  his spawner made them. The failure reproduced from the shapes: the stone pose's hand 5.0 deep (Kirby's
  SpecialLw end pose, LHandN model x -5.0) against each fighter's widest hurtbox (Hero's Ultimate hit_data 2.0;
  vanilla Robin 2.4, Link 2.6, Mario 3.1, Kirby 5.0) and each shot's hitbox radius: before, Sizz / Sizzle reach
  every vanilla body and miss Hero; on the plane, all of them reach Hero.
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brave_build as B  # noqa: E402
import rolloff_hold_test as R  # noqa: E402
from kirby_newcopy_test import R_names  # noqa: E402

FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


class Game:
    def __init__(self, custom, fighters, me=(0.0, 0.0), z=None):
        self.custom = custom
        self.fighters = fighters        # {slot: (kind, x, y[, status])}
        self.me = me
        self.z = z or {}                # {slot: its Z (position variable 0x0F000022 + 4 slot)}
        self.posture = []               # fix v4: PostureModule(3, x, y, z) calls

    def fvar(self, ident):
        i = ident - 0x0F000000
        if 0x20 <= i < 0x40:
            s, q = (i - 0x20) // 4, (i - 0x20) % 4
            if s not in self.fighters:
                return 0.0
            return (self.fighters[s][1], self.fighters[s][2], self.z.get(s, 0.0), 1.0)[q]
        if 0xA0 <= i < 0xF8:
            t, q = (i - 0xA0) // 8, (i - 0xA0) % 8
            if q == 5 and t >= 3:
                return float(self.fighters[t - 3][0]) if t - 3 in self.fighters else -1.0
            if q == 2 and t >= 3 and t - 3 in self.fighters:
                f = self.fighters[t - 3]
                return float(f[3]) if len(f) > 3 else 0.0
        return 0.0

    def sys(self, sid, a):
        if sid == 0x16 and a and a[0] == 0x6 and a[1] == 0x10000005:
            return self.custom & 0xFFFFFFFF
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x15 and a and a[0] in (1, 2):                    # PostureModuleF(1 / 2): its X / Y
            return R.f2i(self.me[a[0] - 1])
        if sid == 0x15 and a == [0]:
            return R.f2i(1.0)
        if sid == 0x14 and a and a[0] == 3:                          # PostureModule(3, x, y, z): set its position
            self.posture.append(tuple(R.i2f(v) for v in a[1:4]))
            return 0
        return 0


def build(out, name, base='shot'):
    w = os.path.join(B.BRAVE, 'weapons')
    srcs = [os.path.join(w, 'thunder_base.c'), os.path.join(w, base + '.c'), os.path.join(w, name + '.c')]
    path = os.path.join(out, name + '.mscsb')
    B.compile_msc(srcs, path)
    text = ''.join(open(s).read() + '\n' for s in srcs)
    with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False) as f:
        f.write(text)
    funcs, glob = R_names(f.name)
    os.unlink(f.name)
    return path, funcs, glob


def run(path, funcs, glob, custom, fighters, me, z=None):
    vm = R.VM(path)
    fn = {n: vm.func(i) for i, n in enumerate(funcs)}
    gi = {n: i for i, n in enumerate(glob)}
    vm.game = Game(custom, fighters, me, z)
    vm.g[gi['global4']] = 0
    vm.call(fn['sh_main'])
    out = {'owner': vm.g.get(gi['sh_owner'], 0), 'level': vm.g.get(gi['sh_level'], 0), 'posture': vm.game.posture}
    if 'sh_tick' in fn and 'dbl_target' in gi:
        vm.g[gi['sh_frame']] = 1
        vm.call(fn['sh_tick'])
        out['target'] = vm.g.get(gi['dbl_target'], 0)
    return out


# fix v4: the shapes behind "the Stone's spells hit everyone but Hero" (fighters/kirby/specials.md "Hero copy fix v4")
STONE_HAND_DEPTH = 5.0          # Kirby's SpecialLw / SpecialAirLw end pose: LHandN at model (-5.0, 10.7, 4.0)
FRIZZ_HAND_DEPTH = 0.9          # the Hero copy's SpecialAirNShoot (Frizz) at its fire frame: LHandN x 0.9
WIDEST_HURTBOX = {'Hero (Ultimate hit_data)': 2.0, 'Robin': 2.4, 'Link': 2.6, 'Mario': 3.1, 'Kirby': 5.0}
SHOT_RADIUS = {'Sizz / Sizzle (flash1 / flash2)': 3.0, 'Frizz (fireball specialn1)': 2.8}


def reaches(depth, radius, hurt):
    """a hitbox `depth` off the plane meets a hurtbox capsule on it (its axis in the plane) when depth < r + R"""
    return depth < radius + hurt


def shape_checks():
    for shot, r in SHOT_RADIUS.items():
        depth = FRIZZ_HAND_DEPTH if shot.startswith('Frizz') else STONE_HAND_DEPTH
        got = {who: reaches(depth, r, h) for who, h in WIDEST_HURTBOX.items()}
        want = {who: True for who in WIDEST_HURTBOX}
        if not shot.startswith('Frizz'):
            want['Hero (Ultimate hit_data)'] = False
        check('fix v4 (the failure, from the shapes): %s %.1f deep reaches %s' % (shot, depth, sorted(k for k, v in want.items() if v)),
              got, want)
        if not shot.startswith('Frizz'):
            check('fix v4: %s on the caster\'s plane reaches every fighter, Hero too' % shot,
                  all(reaches(0.0, r, h) for h in WIDEST_HURTBOX.values()), True)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    shape_checks()
    # Kirby (slot 0) in his stone hold (0x175) 6 from the article; an opponent Hero (slot 1) right at it; another
    # fighter (slot 2) far
    fighters = {0: (8, 6.0, 0.0, 0x175), 1: (0x45, 0.5, 0.0), 2: (0x3, 60.0, 0.0)}
    for name in ('flash', 'explosion', 'deathball', 'sleep'):
        path, funcs, glob = build(out, name)
        for level in (0, 1) if name != 'sleep' else (0,):
            for st in (0x155, 0x175, 0x176):
                f = dict(fighters)
                f[0] = (8, 6.0, 0.0, st)
                got = run(path, funcs, glob, level, f, (2.0, 10.0), {0: 0.25, 1: -3.0})
                check('%s level %d, Kirby (slot 0) in the stone (status 0x%X), an opponent Hero nearer: caster Kirby'
                      % (name, level, st), (got['owner'], got['level']), (0, level))
                check('fix v4: %s level %d from the stone (0x%X): put on Kirby\'s plane (its x / y, his Z 0.25)'
                      % (name, level, st), got['posture'], [(2.0, 10.0, 0.25)])
            f = {5: (8, 6.0, 0.0, 0x175), 1: (0x45, 0.5, 0.0)}
            got = run(path, funcs, glob, level, f, (0.0, 0.0))
            check('%s, the stone Kirby in slot 5: caster 5' % name, got['owner'], 5)
            got = run(path, funcs, glob, level, {0: (0x45, 0.5, 0.0), 1: (8, 40.0, 0.0, 0x175)}, (0.0, 0.0))
            check('%s, Hero\'s own: a stone Kirby 40 away isn\'t taken: the Hero at the article (slot 0)' % name,
                  (got['owner'], got['level']), (0, level))
            check('fix v4: %s, Hero\'s own: left where his spawner made it (no PostureModule(3))' % name, got['posture'], [])
            got = run(path, funcs, glob, level, {0: (0x45, 0.5, 0.0), 1: (8, 3.0, 0.0, 0)}, (0.0, 0.0))
            check('%s, Hero\'s own: a Kirby near it but not in the stone isn\'t taken' % name, got['owner'], 0)
            got = run(path, funcs, glob, level + 4 * 6, {5: (8, 6.0, 0.0), 1: (0x45, 0.5, 0.0)}, (0.0, 0.0))
            check('%s: level + 4 x (slot + 1) still read (custom %d: caster 5, level %d)' % (name, level + 24, level),
                  (got['owner'], got['level']), (5, level))
            if name == 'deathball' and level == 0:
                got = run(path, funcs, glob, 0, fighters, (0.0, 0.0))
                check('Whack from the stone Kirby (slot 0): its target the opponent Hero (slot 1), not Kirby',
                      (got['owner'], got['target']), (0, 1))
                f = dict(fighters)
                f[0] = (8, 6.0, 0.0, 0)
                got = run(path, funcs, glob, 0, f, (0.0, 0.0))
                check('without the stone check (fix v2 and before: the Kirby not in a stone status) the search takes '
                      'the nearer opponent Hero as caster (Whack aims away from him)', (got['owner'], got['target']), (1, 0))
    # placed.c (fix v3): Kirby's crash (level alone) placed on the stone Kirby; Hero's own crash and Zap's spark by
    # the slot in the number
    for name in ('crash', 'spark'):
        path, funcs, glob = build(out, name, 'placed')
        levels = 8 if name == 'crash' else 4
        for c, f, want, what in (
                (0, {3: (8, 6.0, 0.0, 0x175), 0: (0x45, 0.5, 0.0)}, 3 if name == 'crash' else 0,
                 'level 0, a stone Kirby (slot 3) at the article'),
                (3, {3: (8, 6.0, 0.0, 0x176), 0: (0x45, 0.5, 0.0)}, 3 if name == 'crash' else 0,
                 'level 3, the stone Kirby in slot 3'),
                (1 + levels * 2, {3: (8, 6.0, 0.0, 0x175), 2: (0x45, 0.5, 0.0)}, 2, 'the slot in the number (2)'),
                (0, {3: (8, 40.0, 0.0, 0x175), 0: (0x45, 0.5, 0.0)}, 0, 'a stone Kirby 40 away: slot 0'),
                (0, {3: (8, 6.0, 0.0, 0), 0: (0x45, 0.5, 0.0)}, 0, 'a Kirby not in the stone: slot 0')):
            vm = R.VM(path)
            fn = {n: vm.func(i) for i, n in enumerate(funcs)}
            gi = {n: i for i, n in enumerate(glob)}
            vm.game = Game(c, f)
            vm.g[gi['pl_levels']] = levels
            vm.g[gi['pl_started']] = 0
            vm.call(fn['pl_hit_main'])
            check('placed %s: %s: slot %d, level %d' % (name, what, want, c % levels),
                  (vm.g.get(gi['pl_slot'], 0), vm.g.get(gi['pl_level'], 0)), (want, c % levels))
    print('%d failure(s)' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
