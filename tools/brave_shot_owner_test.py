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
    def __init__(self, custom, fighters, me=(0.0, 0.0)):
        self.custom = custom
        self.fighters = fighters        # {slot: (kind, x, y[, status])}
        self.me = me

    def fvar(self, ident):
        i = ident - 0x0F000000
        if 0x20 <= i < 0x40:
            s, q = (i - 0x20) // 4, (i - 0x20) % 4
            if s not in self.fighters:
                return 0.0
            return (self.fighters[s][1], self.fighters[s][2], 0.0, 1.0)[q]
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


def run(path, funcs, glob, custom, fighters, me):
    vm = R.VM(path)
    fn = {n: vm.func(i) for i, n in enumerate(funcs)}
    gi = {n: i for i, n in enumerate(glob)}
    vm.game = Game(custom, fighters, me)
    vm.g[gi['global4']] = 0
    vm.call(fn['sh_main'])
    out = {'owner': vm.g.get(gi['sh_owner'], 0), 'level': vm.g.get(gi['sh_level'], 0)}
    if 'sh_tick' in fn and 'dbl_target' in gi:
        vm.g[gi['sh_frame']] = 1
        vm.call(fn['sh_tick'])
        out['target'] = vm.g.get(gi['dbl_target'], 0)
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    # Kirby (slot 0) in his stone hold (0x175) 6 from the article; an opponent Hero (slot 1) right at it; another
    # fighter (slot 2) far
    fighters = {0: (8, 6.0, 0.0, 0x175), 1: (0x45, 0.5, 0.0), 2: (0x3, 60.0, 0.0)}
    for name in ('flash', 'explosion', 'deathball', 'sleep'):
        path, funcs, glob = build(out, name)
        for level in (0, 1) if name != 'sleep' else (0,):
            for st in (0x155, 0x175, 0x176):
                f = dict(fighters)
                f[0] = (8, 6.0, 0.0, st)
                got = run(path, funcs, glob, level, f, (0.0, 0.0))
                check('%s level %d, Kirby (slot 0) in the stone (status 0x%X), an opponent Hero nearer: caster Kirby'
                      % (name, level, st), (got['owner'], got['level']), (0, level))
            f = {5: (8, 6.0, 0.0, 0x175), 1: (0x45, 0.5, 0.0)}
            got = run(path, funcs, glob, level, f, (0.0, 0.0))
            check('%s, the stone Kirby in slot 5: caster 5' % name, got['owner'], 5)
            got = run(path, funcs, glob, level, {0: (0x45, 0.5, 0.0), 1: (8, 40.0, 0.0, 0x175)}, (0.0, 0.0))
            check('%s, Hero\'s own: a stone Kirby 40 away isn\'t taken: the Hero at the article (slot 0)' % name,
                  (got['owner'], got['level']), (0, level))
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
