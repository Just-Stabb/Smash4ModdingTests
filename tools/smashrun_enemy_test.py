#!/usr/bin/env python3
"""Unicorn test of tools/smashrun_enemy_cave.py in a patched cross_f.rpx:

  python3 tools/smashrun_enemy_test.py PATCHED.rpx [ENEMY_ROOT]

ENEMY_ROOT (optional): the installed converted enemies (a folder holding motion/enemy/<name>/body/main.pac and
animcmd/enemy/<name>/, e.g. smashrun_enemies_v1b's smashrun_enemies/): then every set entry must name an OMO in K's
pac and every script of K's attack.bin / effect.bin a hash in K's set.

Runs the game's code around the hooks, the calls out of them stubbed:
- F, the factory 0x02DB94CC(module, kind, _, variation): stalfos 0x30 / zima 0x0E / plasmawisp 0x12 / darios 0x1D
  call their twin's create (0x026D1DFC / 0x026D6834 / 0x026CF4DC / 0x026CBA64) with (module+4, K, variation) and
  module+8 = its result; the twins 0x57-0x5A still call their own create with their own kind; kinds 0x00 / 0x2F /
  0x31 / 0x4F / 0x5C / 0x61 call none and leave module+8 = 0.
- T (0x02D9A468): on a Smash Run stage motion set table[K] -> K's set, article table[K] = article table[twin], the
  rest of both tables untouched, r0 = mgr+0x5EC; get_motion_data_set(K) / 0x02DC6D88(K) then return them; off the
  Smash Run stages nothing changes.
- The sets: the twin's count, flags, hashsets and zero words; each entry the CRC (zlib.crc32(stem, 0xFFFFFFFF)) of
  K's animation whose twin name has the twin's hash at that index.
- S (0x02D9A614): 0x02DC67C0 is called with the caller's r3; on a Smash Run stage then slot[K] = slot[twin] in the
  param manager (*(0x102F6C00) + 0x60), the other slots untouched, r3 = the call's result, stack kept; off them
  or without a manager nothing changes.
- The hook words, and 0x04B85800-0x04B88000 holding only the cave's code and sets (zeros elsewhere; with
  tools/smashrun_walker_cave.py applied, 0x04B86800-0x04B88000 is its space, checked by smashrun_walker_test.py).
"""
import os
import struct
import sys
import zlib

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_PC, UC_PPC_REG_MSR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_field_cave as F  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402

R = {n: getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % n) for n in range(32)}
MGR, PM, MOD, ACC, STACK = 0x30000000, 0x30010000, 0x30020000, 0x30030000, 0x31000000
CREATES = {0x50: 0x02DD0438, 0x51: 0x02DC7414, 0x52: 0x026B7344, 0x53: 0x026C2E9C, 0x54: 0x026BE944,
           0x55: 0x026BB3E8, 0x56: 0x026C5F80, 0x57: 0x026CF4DC, 0x58: 0x026CBA64, 0x59: 0x026D1DFC,
           0x5A: 0x026D6834, 0x5B: 0x02DDB82C, 0x5E: 0x026E24EC, 0x5F: 0x026D80A0, 0x60: 0x026DB864}
FAILS = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def u32s(uc, addr, n):
    return list(struct.unpack('>%dI' % n, uc.mem_read(addr, 4 * n)))


class Machine:
    def __init__(self, img):
        uc = self.uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(0x02000000, 0x03000000)
        uc.mem_map(0x10000000, 0x00800000)
        for base, data in img.mem:
            if 0x02000000 <= base < 0x05000000 or 0x10000000 <= base < 0x10800000:
                uc.mem_write(base, data)
        uc.mem_map(MGR, 0x40000)
        uc.mem_map(STACK - 0x10000, 0x20000)
        self.calls = []
        self.slots = {}
        uc.hook_add(UC_HOOK_CODE, self.hook)

    def ret(self, r3=None):
        if r3 is not None:
            self.uc.reg_write(R[3], r3)
        self.uc.reg_write(UC_PPC_REG_PC, self.uc.reg_read(UC_PPC_REG_LR))

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        if addr in CREATES.values():
            self.calls.append(('create', addr, r(3), r(4), r(5)))
            self.ret(0x7000 + r(4))
        elif addr == E.PARAM_LOAD:
            self.calls.append(('load', r(3)))
            for k, v in self.slots.items():
                u.mem_write(PM + E.SLOTS + 4 * k, struct.pack('>I', v))
            self.ret(0x1234)

    def stage(self, kind):
        self.uc.mem_write(F.STAGE_KIND, struct.pack('>I', kind))

    def run(self, start, stop, regs):
        for k, v in regs.items():
            self.uc.reg_write(R[k], v)
        self.uc.reg_write(R[1], STACK)
        self.uc.reg_write(UC_PPC_REG_MSR, self.uc.reg_read(UC_PPC_REG_MSR) | 0x2000)
        self.uc.emu_start(start, stop, count=20000)


def main():
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    sets = E.build_sets(img)
    a, words = E.assemble(sets)
    pairs = {k: (name, twin, create) for name, k, twin, create in E.PAIRS}

    # hook words and the space
    check(img.u32(E.SITE_F) == E.branch(E.SITE_F, a.addr('cave_f')) and
          img.u32(E.SITE_T) == E.branch(E.SITE_T, a.addr('cave_t')) and
          img.u32(E.SITE_S) == E.branch(E.SITE_S, a.addr('cave_s'), True), 'hooks: F / T / S branch to the caves')
    want = {E.CAVE + 4 * i: w for i, w in enumerate(words)}
    for addr, ws, _st in sets.values():
        want.update({addr + 4 * i: w for i, w in enumerate(ws)})
    end = E.CLEAR[1]
    w = img.u32(W.SITE_F)
    if w >> 26 == 18 and W.CAVE <= W.branch_target(W.SITE_F, w) < W.LIMIT:
        end = W.CAVE            # step 2b's walker cave from here (smashrun_walker_test.py)
    bad = [hex(x) for x in range(E.CLEAR[0], end, 4) if img.u32(x) != want.get(x, 0)]
    check(not bad, 'space 0x%08X-0x%08X: the cave, its sets, zeros elsewhere %s' % (E.CLEAR[0], end, bad[:4]))

    # F
    res = {}
    for kind in [k for k in pairs] + [0x57, 0x58, 0x59, 0x5A, 0x50, 0x5B, 0x60] + [0x00, 0x2F, 0x31, 0x4F, 0x5C, 0x61]:
        m = Machine(img)
        m.uc.mem_write(MOD, struct.pack('>III', 0, ACC, 0))
        m.run(0x02DB94CC, 0x02DB96F8, {3: MOD, 4: kind, 5: 0, 6: 3})
        res[kind] = ([c[1:] for c in m.calls], struct.unpack('>I', m.uc.mem_read(MOD + 8, 4))[0])
    for k, (name, twin, create) in pairs.items():
        check(res[k] == ([(create, ACC, k, 3)], 0x7000 + k),
              'F: %s 0x%X -> 0x%08X(acc, 0x%X, 3) at module+8 %s' % (name, k, create, k, res[k]))
    ok = all(res[k] == ([(CREATES[k], ACC, k, 3)], 0x7000 + k) for k in (0x57, 0x58, 0x59, 0x5A, 0x50, 0x5B, 0x60))
    check(ok, 'F: the twins and the bosses keep their own create and kind')
    ok = all(res[k] == ([], 0) for k in (0x00, 0x2F, 0x31, 0x4F, 0x5C, 0x61))
    check(ok, 'F: other kinds get no behaviour (0x00 0x2F 0x31 0x4F 0x5C 0x61)')

    # T
    t1 = [img.u32(E.MOTION_SETS + 4 * k) for k in range(0x61)]
    t2 = [img.u32(E.ARTICLE_SETS + 4 * k) for k in range(0x61)]
    for stage in (0x94, 0x82, 0x10):
        m = Machine(img)
        m.stage(stage)
        m.uc.mem_write(MGR + 0x5EC, struct.pack('>I', 2))
        m.run(E.SITE_T, E.SITE_T + 4, {31: MGR, 0: 0})
        n1, n2 = u32s(m.uc, E.MOTION_SETS, 0x61), u32s(m.uc, E.ARTICLE_SETS, 0x61)
        w1, w2 = list(t1), list(t2)
        if stage != 0x10:
            for k, (name, twin, _c) in pairs.items():
                w1[k] = sets[name][0]
                w2[k] = t2[twin]
        check(n1 == w1 and n2 == w2 and m.uc.reg_read(R[0]) == 2 and m.uc.reg_read(R[31]) == MGR,
              'T (stage 0x%X): %s, r0 = mgr+0x5EC' % (stage, 'K -> its set / its twin\'s articles, the rest kept'
                                                     if stage != 0x10 else 'tables unchanged'))
        if stage == 0x94:
            got = {}
            for k in pairs:
                m.uc.reg_write(UC_PPC_REG_LR, 0x02000000)
                m.run(0x02DC6D68, 0x02000000, {3: k})
                g1 = m.uc.reg_read(R[3])
                m.uc.reg_write(UC_PPC_REG_LR, 0x02000000)
                m.run(0x02DC6D88, 0x02000000, {3: k})
                got[k] = (g1, m.uc.reg_read(R[3]))
            check(all(got[k] == (sets[pairs[k][0]][0], t2[pairs[k][1]]) for k in pairs),
                  'T: get_motion_data_set(K) / 0x02DC6D88(K) return K\'s set / the twin\'s articles')
    check(t2[0x57] != t2[0x12] and t2[0x58] == t2[0x1D], 'T: Plasma Wisp gets the twin\'s articles (0x%08X; default '
          '0x%08X); the others\' are the default' % (t2[0x57], t2[0x12]))

    # the sets
    pac_stems = {}
    if root:
        import omo
        for name, _k, _t, _c in E.PAIRS:
            pac = os.path.join(root, 'motion', 'enemy', name, 'body', 'main.pac')
            pac_stems[name] = [n[:-4] for n, _d in omo.pac_read(pac) if n.endswith('.omo')]
    for name, k, twin, _c in E.PAIRS:
        addr, ws, stems = sets[name]
        tw = img.u32(E.MOTION_SETS + 4 * twin)
        n = img.u32(tw + 4)
        mine = [img.u32(addr + 4 * i) for i in range(6)]
        hs_ok = all(img.u32(addr + 0x18 + 4 * i) == img.u32(tw + 0x18 + 4 * i) for i in range(3 * n))
        te, me = img.u32(tw), img.u32(addr)
        ent_ok = True
        for i in range(n):
            th, tf = img.u32(te + 8 * i), img.u32(te + 8 * i + 4)
            mh, mf = img.u32(me + 8 * i), img.u32(me + 8 * i + 4)
            st = stems[i]
            sfx = st[len('Enm%sBodyMain' % name.capitalize()):]
            ent_ok &= mf == tf and mh == zlib.crc32(st.encode(), 0xFFFFFFFF) and \
                th == zlib.crc32(E.stem(name, sfx, True).encode(), 0xFFFFFFFF)
        check(mine == [addr + 0x18 + 12 * n, n, 0, 0, 0, 0] and hs_ok and ent_ok,
              'set %s (0x%08X): %d entries in the twin\'s order, K\'s animations, the twin\'s flags / hashsets'
              % (name, addr, n))
        if root:
            have = {zlib.crc32(s.encode(), 0xFFFFFFFF) for s in pac_stems[name]}
            missing = [stems[i] for i in range(n) if img.u32(me + 8 * i) not in have]
            check(not missing, 'set %s: every entry is an OMO of %s/body/main.pac %s' % (name, name, missing))
            hs = {img.u32(addr + 0x18 + 4 * i) for i in range(3 * n)}
            for f in ('attack', 'effect', 'sound'):
                p = os.path.join(root, 'animcmd', 'enemy', name, f + '.bin')
                if os.path.exists(p):
                    d = open(p, 'rb').read()
                    cnt = struct.unpack('>I', d[8:12])[0]
                    scr = [struct.unpack('>I', d[0x10 + 8 * i:0x14 + 8 * i])[0] for i in range(cnt)]
                    out = [hex(h) for h in scr if h not in hs]
                    check(not out, 'set %s: %s.bin\'s %d scripts are in the hashsets %s' % (name, f, cnt, out))

    # S
    twin_vals = {twin: 0x40000000 + twin for _n, _k, twin, _c in E.PAIRS}
    for stage, pm, label in ((0x94, PM, 'on a Smash Run stage'), (0x10, PM, 'off them'),
                             (0x94, 0, 'without a param manager')):
        m = Machine(img)
        m.stage(stage)
        m.uc.mem_write(E.PARAM_MGR, struct.pack('>I', pm))
        m.uc.mem_write(PM + E.SLOTS, struct.pack('>97I', *[0x50000000 + i for i in range(0x61)]))
        for k in pairs:
            m.uc.mem_write(PM + E.SLOTS + 4 * k, bytes(4))
        m.slots = twin_vals
        before = u32s(m.uc, PM + E.SLOTS, 0x61)
        m.run(E.SITE_S, E.SITE_S + 4, {3: 0x10AB0000, 31: 7})
        after = u32s(m.uc, PM + E.SLOTS, 0x61)
        want = list(before)
        for k, v in twin_vals.items():
            want[k] = v
        if stage != 0x10 and pm:
            for k, (_n, twin, _c) in pairs.items():
                want[k] = twin_vals[twin]
        check(m.calls == [('load', 0x10AB0000)] and after == want and m.uc.reg_read(R[3]) == 0x1234 and
              m.uc.reg_read(R[1]) == STACK and m.uc.reg_read(R[31]) == 7,
              'S (%s): the param load, then %s' % (label, 'slot[K] = slot[twin]' if stage != 0x10 and pm
                                                   else 'no slot changed'))
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
