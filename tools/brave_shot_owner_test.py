#!/usr/bin/env python3
"""Hero's Command Selection projectiles (fighters/brave/weapons/shot.c, Kirby's Hero copy fix v2): the caster from the
custom number. Compiles each shot article's MSC as tools/brave_build.py does (thunder_base.c + shot.c + the article)
and runs its status 0 main (sh_main) in tools/rolloff_hold_test.py's interpreter with the custom number (the weapon's
0x10000005) and the position variables stubbed:

  python3 tools/brave_shot_owner_test.py [OUT_DIR]

- Hero's own (brave.c: the level alone, 0 / 1): the caster from the search (the nearest Hero or Kirby to the article),
  as before;
- Kirby's Hero copy (kirby.c khm_generate: level + 4 x (his slot + 1)): the level and the caster from the number, even
  with an opponent Hero nearer to the article than he is (the search would have taken that Hero: Whack left him out of
  its targets and rolls, the user's "Whack can't hit an enemy Hero");
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
        self.fighters = fighters        # {slot: (kind, x, y)}
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


def build(out, name):
    w = os.path.join(B.BRAVE, 'weapons')
    srcs = [os.path.join(w, 'thunder_base.c'), os.path.join(w, 'shot.c'), os.path.join(w, name + '.c')]
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
    # an opponent Hero (slot 1) right at the article, Kirby (slot 0) 6 away, another fighter (slot 2) far
    fighters = {0: (8, 6.0, 0.0), 1: (0x45, 0.5, 0.0), 2: (0x3, 60.0, 0.0)}
    for name in ('flash', 'explosion', 'deathball', 'sleep'):
        path, funcs, glob = build(out, name)
        for level in (0, 1) if name != 'sleep' else (0,):
            got = run(path, funcs, glob, level + 4 * (0 + 1), fighters, (0.0, 0.0))
            check('%s, Kirby (slot 0) casts level %d (custom %d): caster slot 0, level %d'
                  % (name, level, level + 4, level), (got['owner'], got['level']), (0, level))
            got = run(path, funcs, glob, level + 4 * (5 + 1), {5: (8, 6.0, 0.0), 1: (0x45, 0.5, 0.0)}, (0.0, 0.0))
            check('%s, Kirby in slot 5 (custom %d): caster 5' % (name, level + 24), (got['owner'], got['level']),
                  (5, level))
            got = run(path, funcs, glob, level, {0: (0x45, 0.5, 0.0), 1: (8, 40.0, 0.0)}, (0.0, 0.0))
            check('%s, Hero\'s own (custom %d = the level): the search, the Hero at the article (slot 0)'
                  % (name, level), (got['owner'], got['level']), (0, level))
            if name == 'deathball' and level == 0:
                got = run(path, funcs, glob, 4, fighters, (0.0, 0.0))
                check('Whack from Kirby (slot 0): its target the opponent Hero (slot 1), not Kirby', got['target'], 1)
                got = run(path, funcs, glob, 0, fighters, (0.0, 0.0))
                check('the old coding (level only) with the opponent Hero nearer: the search takes the Hero as caster '
                      '(the bug: Whack aims away from him)', (got['owner'], got['target']), (1, 0))
    print('%d failure(s)' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
