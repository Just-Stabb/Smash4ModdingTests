#!/usr/bin/env python3
"""Hero's articles from any player slot (Kirby's Hero copy fix v4, fighters/kirby/specials.md "Hero copy fix v4"; the
user: "Magic Burst as Hero on a slot other than player 1 doesn't spawn anything"). Runs Hero's compiled MSC
(fighters/brave/brave.c) and the placed articles' (thunder_base.c + placed.c + crash.c / spark.c / tornado.c) in
tools/rolloff_hold_test.py's interpreter, the two joined by the position variables the articles read:

  python3 tools/brave_mark_test.py [OUT_DIR]

- before (the reproduction, from the code as it was, its custom numbers): Magic Burst sent tier + 8 x slot, Kamikazee
  1 + 8 x slot, Woosh level + 4 x slot, Zap level + 4 x the target's slot: past 3 (a copy of Robin's thunder reads
  its base's 4-entry per-custom data past its end: port_check W10) for every slot but P1's, and for P1's Magic Burst
  tiers 4-6 (21-80 MP);
- now every generate's custom number is 0-3 (Magic Burst 0, Kamikazee 1, Woosh / Zap the level), Hero's marker (his
  ARMOR_THRESHOLD, 0x0F00011E) = 9000 + the payload while he makes it, held 3 frames, then his own threshold back;
  a second Zap target waits for the marker and goes out 3 frames later;
- placed.c, for Hero in each slot 0-7 (an opponent Hero without a marker nearer to the article, a stone Kirby out of
  reach): the crash on the casting Hero's slot with the tier (0 / 3-6) or Kamikazee (1), the tornado on his slot,
  the spark on the marked target's slot; Kirby's stone crash (no marker) and the old level + 8 x slot numbers as
  before.
- the move of brave.c's globals 128-134 (brave_lw_released ... brave_lw_burst) into New_Var slots 0x0F0003B6-BC
  (the game keeps 128 globals a file: msc_stack_check / port_check C1): the source with them put back as globals
  (the substitution reversed) and the shipped one, both compiled, run Command Selection (brave_lw_main, then
  brave_lw_loop + brave_frame for 260 frames, the spell cast at 20) for 16 spells: the same calls in the same order,
  the slots' own WorkModule ops aside.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rolloff_hold_test as R  # noqa: E402
from kirby_newcopy_test import R_names  # noqa: E402
from brave_shot_owner_test import build as build_article  # noqa: E402

FAIL = []
BRAVE = os.path.join(ROOT, 'fighters', 'brave', 'brave.c')
MARK = 0x0F00011E


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


class HeroGame:
    """Hero's side: his floats (position variables, New_Var slots: one float an id, int ops cut toward 0), ints,
    the articles he makes (with his marker at that moment)"""
    def __init__(self, slot, fighters):
        self.f = {MARK: 40.0}          # his own threshold before (kept and put back)
        self.ints = {}
        self.slot = slot
        for s, (kind, x, y) in fighters.items():
            self.f[0x0F000020 + 4 * s], self.f[0x0F000021 + 4 * s], self.f[0x0F000023 + 4 * s] = x, y, 1.0
        self.f[0x0F000000], self.f[0x0F000001] = fighters[slot][1], fighters[slot][2]
        self.articles = []

    def sys(self, sid, a):
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.f.get(a[1], 0.0))
        if sid == 0x16:
            if a[0] == 0 and len(a) == 3:
                self.f[a[2]] = R.i2f(a[1])
                return 0
            if a[0] == 0x6:
                if a[1] >> 24 == 0x0F:
                    return int(self.f.get(a[1], 0.0)) & 0xFFFFFFFF
                return self.ints.get(a[1], 0)
            if a[0] == 0x7:
                if a[2] >> 24 == 0x0F:
                    self.f[a[2]] = float(R.s32(a[1]))
                else:
                    self.ints[a[2]] = a[1]
                return 0
            return 0
        if sid == 0x20 and a and a[0] == 0x2710:
            self.articles.append((a[1], R.s32(self.ints.get(0x10000048, 0)), self.f.get(MARK)))
            return 0
        return 0


class ArticleGame:
    """the placed article's side: the custom number, the position variables of the fighters (kind, x, y, status,
    the armour threshold), its own position"""
    def __init__(self, custom, fighters, me):
        self.custom, self.fighters, self.me = custom, fighters, me
        self.placed = None

    def fvar(self, ident):
        i = ident - 0x0F000000
        if 0x20 <= i < 0x40:
            s, q = (i - 0x20) // 4, (i - 0x20) % 4
            f = self.fighters.get(s)
            return (f['x'], f['y'], 0.0, 1.0)[q] if f else 0.0
        if 0xA0 <= i < 0xF8:
            t, q = (i - 0xA0) // 8, (i - 0xA0) % 8
            f = self.fighters.get(t - 3)
            if f and q == 5:
                return float(f['kind'])
            if f and q == 2:
                return float(f.get('status', 0))
            return -1.0 if q == 5 else 0.0
        if 0x160 <= i < 0x260 and (i - 0x100) % 0x20 == 0x1E:
            f = self.fighters.get((i - 0x100) // 0x20 - 3)
            return f.get('mark', 0.0) if f else 0.0
        return 0.0

    def sys(self, sid, a):
        if sid == 0x16 and a and a[0] == 0x6 and a[1] == 0x10000005:
            return self.custom & 0xFFFFFFFF
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.fvar(a[1]))
        if sid == 0x15 and a and a[0] in (1, 2):
            return R.f2i(self.me[a[0] - 1])
        if sid == 0x15 and a == [0]:
            return R.f2i(1.0)
        if sid == 0x14 and a and a[0] == 3:
            self.placed = tuple(round(R.i2f(v), 3) for v in a[1:3])
        return 0


def compile_hero(out):
    path = os.path.join(out, 'brave.mscsb')
    r = R.subprocess.run([sys.executable, os.path.join(HERE, 'msclang', 'msclang.py'), '-x',
                          os.path.join(HERE, 'mscinfo.xml'), BRAVE, '-o', path], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return path


class Hero:
    def __init__(self, path, slot, fighters):
        self.vm = R.VM(path)
        funcs, glob = R_names(BRAVE)
        self.fn = {n: self.vm.func(i) for i, n in enumerate(funcs)}
        self.gi = {n: i for i, n in enumerate(glob)}
        self.game = HeroGame(slot, fighters)
        self.vm.game = self.game

    def g(self, name, v=None):
        if v is not None:
            self.vm.g[self.gi[name]] = v
        return self.vm.g.get(self.gi[name], 0)


def placed(art, custom, fighters, me=(0.0, 10.0)):
    path, funcs, glob = art
    vm = R.VM(path)
    fn = {n: vm.func(i) for i, n in enumerate(funcs)}
    gi = {n: i for i, n in enumerate(glob)}
    vm.game = ArticleGame(custom, fighters, me)
    for name, v in (('pl_levels', 8 if 'crash' in path else 4), ('pl_started', 0), ('pl_mark_kind', 0), ('pl_wait', 0)):
        vm.g[gi[name]] = v
    vm.call(fn['placed_config'])
    vm.call(fn['pl_hit_main'])
    return vm.g.get(gi['pl_slot'], 0), vm.g.get(gi['pl_level'], 0), vm.game.placed


SLOTS = {'brave_lw_released': 0x0F0003B6, 'brave_lw_stick': 0x0F0003B7, 'brave_lw_repeat': 0x0F0003B8,
         'brave_lw_done': 0x0F0003B9, 'brave_lw_sub': 0x0F0003BA, 'brave_lw_t': 0x0F0003BB, 'brave_lw_burst': 0x0F0003BC}


def as_globals(src):
    """brave.c with the moved slots as globals again (the substitution reversed)"""
    for n, i in SLOTS.items():
        h = '0x%08x' % i
        src = src.replace('// %s: New_Var slot' % n, 'int %s; //' % n)
        src = re.sub(r'WorkModule\(0x7, (.*), %s\);' % h, lambda m: '%s = %s;' % (n, m.group(1)), src)
        src = src.replace('WorkModule(0x6, %s)' % h, n)
    return src


class LogGame(HeroGame):
    def __init__(self):
        super().__init__(0, {0: (0x45, 0.0, 0.0)})
        self.log, self.frame, self.press, self.situation = [], 0.0, set(), 0

    def sys(self, sid, a):
        ids = set(SLOTS.values())
        if not ((sid == 0x16 and len(a) >= 2 and ((a[0] == 6 and a[1] in ids) or (a[0] in (7, 0) and a[-1] in ids)))
                or (sid == 0x17 and len(a) == 2 and a[1] in ids)):
            self.log.append((sid, tuple(a)))
        if sid == 0x12 and a and a[0] == 1:
            self.frame = 0.0
            return 0
        if sid == 0x13:
            return R.f2i(self.frame if a == [1] else 0.0)
        if sid == 0x18 and a == [1]:
            return self.situation
        if sid == 0xE and len(a) == 2 and a[0] == 0x2710:
            return int(a[1] in self.press)
        return super().sys(sid, a)


def globals_move(out):
    alt = os.path.join(out, 'brave_globals.c')
    with open(alt, 'w') as f:
        f.write(as_globals(open(BRAVE).read()))
    check('the reversed source has the seven globals back and no slot op left',
          (len(re.findall(r'^int brave_lw_\w+;', open(alt).read(), re.M)), re.findall(r'0x0f0003b[6-9a-c]', open(alt).read())),
          (12, []))
    builds = []
    for src, name in ((alt, 'brave_globals.mscsb'), (BRAVE, 'brave_slots.mscsb')):
        path = os.path.join(out, name)
        r = R.subprocess.run([sys.executable, os.path.join(HERE, 'msclang', 'msclang.py'), '-x',
                              os.path.join(HERE, 'mscinfo.xml'), src, '-o', path], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        builds.append((path, src))
    bad = []
    for spell in (1, 2, 4, 6, 8, 9, 0xa, 0xb, 0xd, 0xe, 0xf, 0x10, 0x13, 0x15, 0x16, 0x17):
        logs = []
        for path, src in builds:
            vm = R.VM(path)
            funcs, glob = R_names(src)
            fn = {n: vm.func(i) for i, n in enumerate(funcs)}
            gi = {n: i for i, n in enumerate(glob)}
            g = LogGame()
            vm.game = g
            vm.g[gi['brave_mp']] = R.f2i(100.0)
            vm.g[gi['global4']] = 0x155
            vm.call(fn['brave_lw_main'])
            vm.g[gi['brave_lw_spells']] = spell
            vm.g[gi['brave_lw_cursor']] = 0
            for k in range(260):
                g.press = {0} if k == 20 else set()
                vm.call(fn['brave_lw_loop'])
                vm.call(fn['brave_frame'])
                g.frame += 1.0
            logs.append(g.log)
        if logs[0] != logs[1] or len(logs[0]) < 1000:
            bad.append(hex(spell))
    check('the globals 128-134 moved to New_Var slots: Command Selection makes the same calls for 16 spells', bad, [])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    # the reproduction: the old numbers past 3
    for art, expr, name in (('0xc', 'brave_burst_motion() + 0x8 * brave_lw_slot()', 'Magic Burst'),
                            ('0xc', '0x1 + 0x8 * brave_lw_slot()', 'Kamikazee'),
                            ('0x8', 'brave_hi_level + 0x4 * s', 'Woosh'), ('0x7', 'brave_s_level + 0x4 * s', 'Zap')):
        check('before: %s sent %s' % (name, expr), expr in [c for a, c in re.findall(
            r'brave_generate\((0x[0-9a-f]+), ([^;]*)\);', R.subprocess.run(
                ['git', '-C', ROOT, 'show', '2cbee77:fighters/brave/brave.c'], capture_output=True, text=True).stdout)
            if a == art], True)
    past = sorted(set(t + 8 * s for t in (0, 3, 4, 5, 6) for s in range(8) if t + 8 * s > 3))
    check('before: Magic Burst\'s custom numbers past 3 (unmade): every slot but P1, and P1\'s tiers 4-6',
          [c for c in past if c < 8], [4, 5, 6])
    path = compile_hero(out)
    src = open(BRAVE).read()
    check('now: no generate carries a slot (port_check W10)', [c for a, c in re.findall(
        r'brave_generate\((0x[0-9a-f]+), ([^;]*)\);', src) if 'slot' in c or '* s' in c], [])
    crash = build_article(out, 'crash', 'placed')
    spark = build_article(out, 'spark', 'placed')
    tornado = build_article(out, 'tornado', 'placed')
    for slot in range(8):
        fighters = {s: (0x45 if s in (slot, (slot + 1) % 8) else 3, 20.0 * s, 0.0) for s in range(8)}
        for mp, tier in ((100, 0), (70, 6), (50, 5), (30, 4), (10, 3)):
            h = Hero(path, slot, fighters)
            h.g('brave_lw_spell', 8)
            h.game.f[0x0F0003BC] = float(mp)        # brave_lw_burst (a New_Var slot since fix v4)
            h.game.f[0x0F0003B9] = 0.0              # brave_lw_done
            h.vm.call(h.fn['brave_lw_cast'], [R.f2i(20.0)])
            gens = h.game.articles
            check('slot %d, Magic Burst with %d MP: article 12, custom 0, marker 9000 + %d' % (slot, mp, tier),
                  [(x[0], x[1], x[2]) for x in gens], [(12, 0, 9000.0 + tier)])
            # the article: the casting Hero marked, an opponent Hero nearer to it unmarked
            fa = {s: {'kind': k, 'x': x, 'y': y} for s, (k, x, y) in fighters.items()}
            fa[slot]['mark'] = 9000.0 + tier
            me = (20.0 * slot + 4.0, 10.0)
            fa[(slot + 1) % 8]['x'] = me[0] + 1.0
            got = placed(crash, 0, fa, me)
            check('slot %d, Magic Burst %d MP: the crash on his slot, motion %d' % (slot, mp, tier), got[:2], (slot, tier))
            for _ in range(3):
                h.vm.call(h.fn['brave_mark_update'])
            check('slot %d: his threshold back after 3 frames, the marker free' % slot,
                  (h.game.f.get(MARK), int(h.game.f.get(0x0F0003BF, 0))), (40.0, 0))
        h = Hero(path, slot, fighters)
        h.g('brave_lw_spell', 9)
        h.game.f[0x0F0003B9] = 0.0
        h.vm.call(h.fn['brave_lw_cast'], [R.f2i(20.0)])
        check('slot %d, Kamikazee: article 12, custom 1, marker 9001' % slot,
              [(x[0], x[1], x[2]) for x in h.game.articles], [(12, 1, 9001.0)])
        fa = {s: {'kind': k, 'x': x, 'y': y} for s, (k, x, y) in fighters.items()}
        fa[slot]['mark'] = 9001.0
        check('slot %d, Kamikazee: the crash on his slot, motion 1' % slot,
              placed(crash, 1, fa, (20.0 * slot + 3.0, 10.0))[:2], (slot, 1))
        # Woosh: tornado on his slot
        fa[slot]['mark'] = 9000.0
        check('slot %d, Woosh level 2: the tornado on his slot' % slot,
              placed(tornado, 2, fa, (20.0 * slot + 3.0, 10.0))[:2], (slot, 2))
        # Zap: the spark on the marked target
        tgt = (slot + 3) % 8
        h = Hero(path, slot, fighters)
        h.g('brave_s_level', 2)
        h.g('brave_s_sparked', 0)
        h.game.f[0x0F0000A0] = 1.0
        for s_ in (tgt, (slot + 5) % 8):        # two bolts hit, the same frame
            h.game.f[0x0F000055] = (20.0 * s_ - 20.0 * slot)
            h.game.f[0x0F000056] = 0.0
            h.game.f[0x0F000003] = 1.0
            h.vm.call(h.fn['brave_s_spark'])
        first = list(h.game.articles)
        for _ in range(3):
            h.vm.call(h.fn['brave_mark_update'])
        check('slot %d, Zap hitting slots %d and %d at once: the first spark at once (custom 2, marker 9000 + %d), '
              'the second when the marker is free (3 frames)' % (slot, tgt, (slot + 5) % 8, tgt),
              (first, h.game.articles[1:]), ([(7, 2, 9000.0 + tgt)], [(7, 2, 9000.0 + (slot + 5) % 8)]))
        fa[slot]['mark'] = 9000.0 + tgt
        check('slot %d, Zap: the spark on the target (slot %d), level 2' % (slot, tgt),
              placed(spark, 2, fa, (20.0 * slot + 3.0, 10.0))[:2], (tgt, 2))
    # unchanged: Kirby's stone crash (no marker), the old level + 8 x slot numbers
    fa = {3: {'kind': 8, 'x': 6.0, 'y': 0.0, 'status': 0x175}, 0: {'kind': 0x45, 'x': 0.5, 'y': 0.0}}
    check('Kirby\'s stone crash (no Hero marked): on the stone Kirby (slot 3), level 3', placed(crash, 3, fa, (0.0, 0.0))[:2],
          (3, 3))
    check('the old number 5 + 8 x 2 still read: slot 2, level 5', placed(crash, 21, fa, (0.0, 0.0))[:2], (2, 5))
    globals_move(out)
    print('%d failure(s)' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
