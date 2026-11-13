#!/usr/bin/env python3
"""Behaviour test of Link's arrow lifetime and Samus's / Kirby's Charge Shot charge on a hit: runs the compiled MSC
in the MSC interpreter of tools/rolloff_hold_test.py, with WorkModule / ArticleModule / EffectModule /
BattleObject stubbed, and checks the edited files against the originals.

  python3 tools/link_samus_test.py --arrow ORIG_bowarrow.mscsb NEW_bowarrow.mscsb
                                   --samus ORIG_samus.mscsb NEW_samus.mscsb
                                   [--kirby ORIG_kirby.mscsb NEW_kirby.mscsb]

Arrow (fighters/link/weapons/bowarrow.c): status 0's init (func_63) with the vl life (group 19 entry 0) at 40 / 25 / 11,
then status 1's per-frame function (func_61) until it removes the arrow (BattleObject 9): the new file must last
twice the old one's frames; status 2 (stuck: entry 6, 80) unchanged.
Charge Shot (fighters/samus/samus.c, fighters/kirby/kirby.c): the exit scripts (status table key 6) of the hold and
the two starts, run with a charge stored (0x10000084) for every next status 0 - 0x1FF: the charge must be kept on a
hit (0x45 - 0x4c), and every other next status must do what the original does.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolloff_hold_test as rt  # noqa: E402


def f2i(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


class Game:
    def __init__(self, ints=None, floats=None):
        self.i = dict(ints or {})
        self.f = dict(floats or {})
        self.log = []
        self.removed = False

    def sys(self, sid, a):
        if sid == 0x16:                                   # WorkModule
            op = a[0]
            if op == 0x6:
                return self.i.get(a[1], 0)
            if op == 0x7:
                self.i[a[2]] = a[1]
                return 0
            if op == 0x9:
                self.i[a[1]] = (self.i.get(a[1], 0) + 1) & 0xFFFFFFFF
                return 0
            if op == 0xA:
                self.i[a[1]] = (self.i.get(a[1], 0) - 1) & 0xFFFFFFFF
                return 0
            self.log.append(('WorkModule', tuple(a)))
            return 0
        if sid == 0x17 and a[0] == 0:                     # WorkModuleF(0, var)
            return f2i(self.f.get(a[1], 0.0))
        if sid == 0x1A:                                   # GroundModule(0x2728): still on the ground
            return 1
        if sid == 0x21 and a[0] == 0x9:                   # BattleObject(9): remove
            self.removed = True
        if sid in (0x20, 0x1C, 0x21, 0x1E):               # ArticleModule / EffectModule / BattleObject / Sound
            self.log.append((sid, tuple(a)))
            return 0x77 if sid == 0x1C and a[0] == 0xB else 0
        return 0


def load(path):
    vm = rt.VM(path)
    return vm


def status_table(vm):
    """{(key, status): script} from the sv_set_mem(0x1, key, status, func) calls"""
    out = {}
    for s in vm.m.scripts:
        cs = s.cmds
        for j, c in enumerate(cs):
            if c.command == 0x2D and c.parameters[1] == 0x3 and c.parameters[0] == 4 and j >= 4:
                p = cs[j - 4:j]
                if all(x.command in (0xA, 0xD) for x in p) and p[0].parameters[0] == 1 and p[3].parameters[0] in vm.at:
                    out[(p[1].parameters[0], p[2].parameters[0])] = vm.at[p[3].parameters[0]]
    return out


def arrow_life(path, life, stuck=0x50):
    vm = load(path)
    init = vm.func(63)
    fly = vm.func(61)
    res = []
    for status, per_frame in ((0, fly), (2, vm.func(62))):
        g = Game(ints={0x12000000: life, 0x12000006: stuck})
        vm.game = g
        vm.g = {4: status}
        vm.call(init)
        frames = 0
        while not g.removed and frames < 10000:
            frames += 1
            g.removed = False
            vm.call(per_frame)
        res.append(frames)
    return res


def run_exit(vm, script, nxt, charge, maxc, glow=0x55):
    g = Game(ints={0x10000084: charge, 0x10000083: glow}, floats={0x5000002: float(maxc)})
    vm.game = g
    vm.g = {6: nxt, 5: 0}
    vm.call(script)
    return g.i.get(0x10000084), tuple(g.log)


def check_charge(name, orig, new, statuses):
    vo, vn = load(orig), load(new)
    to, tn = status_table(vo), status_table(vn)
    bad = 0
    for st in statuses:
        so, sn = to.get((6, st)), tn.get((6, st))
        if so is None or sn is None:
            print('%s: no exit script for status 0x%X' % (name, st))
            bad += 1
            continue
        for charge in (30, 112):
            for nxt in range(0x200):
                a = run_exit(vo, so, nxt, charge, 112)
                b = run_exit(vn, sn, nxt, charge, 112)
                if 0x45 <= nxt <= 0x4C:
                    if b[0] != charge:
                        print('%s 0x%X -> 0x%X charge %d: lost (%s)' % (name, st, nxt, charge, b[0]))
                        bad += 1
                    if not any(x[0] == 0x20 and x[1][:2] == (0x2712, 0) for x in b[1]):
                        print('%s 0x%X -> 0x%X: the charging shot (article 0) is not removed' % (name, st, nxt))
                        bad += 1
                elif a != b:
                    print('%s 0x%X -> 0x%X charge %d: differs from the original %s / %s' % (name, st, nxt, charge, a, b))
                    bad += 1
        print('%-6s exit of 0x%X: hit keeps the charge, other next statuses as the original' % (name, st)
              if not bad else '%s exit of 0x%X: FAILED' % (name, st))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arrow', nargs=2)
    ap.add_argument('--samus', nargs=2)
    ap.add_argument('--kirby', nargs=2)
    a = ap.parse_args()
    bad = 0
    if a.arrow:
        for life in (0x28, 0x19, 0xB):
            o, n = arrow_life(a.arrow[0], life), arrow_life(a.arrow[1], life)
            ok = n[0] == 2 * o[0] and n[1] == o[1]
            bad += not ok
            print('arrow life %d: flight %d -> %d frames, stuck %d -> %d  %s' % (life, o[0], n[0], o[1], n[1],
                                                                              'ok' if ok else 'FAIL'))
    if a.samus:   # hold 0x158, ground start 0x157, air start 0x15B
        bad += check_charge('samus', a.samus[0], a.samus[1], (0x158, 0x157, 0x15B))
    if a.kirby:   # Kirby's Samus copy: hold 0x1F1, starts 0x1F0 / 0x1F4
        bad += check_charge('kirby', a.kirby[0], a.kirby[1], (0x1F1, 0x1F0, 0x1F4))
    print('FAILED' if bad else 'all ok')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
