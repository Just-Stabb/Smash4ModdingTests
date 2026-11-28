#!/usr/bin/env python3
"""The random pools of a patched executable, in unicorn (the tool's replaced refill / count / remove / pick and the
game's own stage refill and helper loops; the database, availability and player calls stubbed: position i = id i,
every fighter / stage available, Miis 1-3 left out as the game's Mii check does).

  python3 tools/sm4shclonetool/tests/random_select_test.py PATCHED.rpx [PICKS]

Checks:
- refill: the new pool (7 words, ids 0-223) holds the game's fighters 4-58 and every clone with "random", not the
  ones set to false; +0x98-+0xA3 mirror ids 0-95; nothing else written (the stage pools +0xA4 on, the object, the
  tool's other data);
- a cycle: pick, then remove the picked id, until 7 are left: every enabled id exactly once, none disabled; then the
  count function refills (under 8 left) and the pool is full again;
- PICKS picks from the full pool: every enabled id picked, none other, a chi-square test of uniformity;
- a player's pick leaves out the ids the other players have (7 or more left);
- remove(id) for every id 0-0xFF: exactly that bit for ids below the scan count (and its mirror bit), else nothing;
- the fighter helper 0x0301CAE8's loop with a 200-entry database writes only its 12 bytes (the 96 clamp) and sets
  no clone's bit (1.4);
- the stage refill 0x02FFB76C: the stage clones with "random" in pool +0xA4, the ones set to false not, nothing
  written past its 16 bytes.
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import random_select as RS  # noqa: E402
from sm4shclonetool.rpx import Rpx  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn import ppc_const as P  # noqa: E402

RET = 0x01000000
OBJ, PLAYERS, LOCAL, STACK = 0x7E000000, 0x7E010000, 0x7E020000, 0x7F00F000
FAILS = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)), flush=True)
    if not ok:
        FAILS.append(what)


def R(n):
    return getattr(P, 'UC_PPC_REG_%d' % n)


class M:
    def __init__(self, path, n_ids, n_stages):
        x = Rpx(path)
        self.mu = mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        spans = []
        for addr, blob in x.memory().items():
            spans.append([addr & ~0xFFF, (addr + len(blob) + 0xFFF) & ~0xFFF, addr, blob])
        bss = [s for s in x.secs if s[1] == 8 and s[3]]
        for s in bss:
            spans.append([s[3] & ~0xFFF, (s[3] + s[5] + 0xFFF) & ~0xFFF, None, None])
        spans.sort()
        merged = []
        for lo, hi, _a, _b in spans:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            mu.mem_map(lo, hi - lo)
        for _l, _h, addr, blob in spans:
            if blob:
                mu.mem_write(addr, blob)
        mu.mem_map(RET, 0x1000)
        mu.mem_map(0x7E000000, 0x2000000)
        self.n_ids, self.n_stages = n_ids, n_stages
        self.special_from = 59 + n_ids
        self.writes = []
        self.wh = None
        st = {
            0x0309FB24: lambda: self.pos_id(self.r(4)),
            0x0301BA44: lambda: 1 if 1 <= self.r(3) < 200 else 0,
            0x0293C40C: lambda: 1,
            0x030A04C0: lambda: 1 if self.r(4) in (1, 2, 3) else 0,
            0x030A0EFC: lambda: 0, 0x030A0F1C: lambda: 4, 0x020013BC: lambda: 0,
            0x0300174C: lambda: OBJ, 0x0300266C: lambda: 0, 0x02868080: lambda: PLAYERS,
            0x0309FB18: lambda: 200,
            0x0301CCB4: lambda: (mu.mem_write(self.r(3), b'\0' * 16), self.r(3))[1],
            0x030A89CC: lambda: self.r(4) if self.r(4) < 0x38 + self.n_stages else 0xFF,
            0x0301BA8C: lambda: 1, 0x02948858: lambda: 1, 0x030A9B24: lambda: 0,
        }
        for a, f in st.items():
            mu.hook_add(UC_HOOK_CODE, lambda uc, addr, size, ud, f=f: self.ret(f()), begin=a, end=a)
        mu.mem_write(0x105759C0 + 0x10, struct.pack('>4I', 0x12345678, 0x9ABCDEF1, 0x0F1E2D3C, 0x55AA33CC))

    def watch(self, on):
        if on and self.wh is None:
            self.writes = []
            self.wh = self.mu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, a, size, v, ud: self.writes.append((a, size)))
        elif not on and self.wh is not None:
            self.mu.hook_del(self.wh)
            self.wh = None

    def r(self, n):
        return self.mu.reg_read(R(n))

    def ret(self, v):
        self.mu.reg_write(R(3), (v or 0) & 0xFFFFFFFF)
        self.mu.reg_write(P.UC_PPC_REG_PC, self.mu.reg_read(P.UC_PPC_REG_LR))

    def pos_id(self, i):
        return i if i < self.special_from else 200 + (i - self.special_from)

    def call(self, fn, *args, count=2000000):
        for i, v in enumerate(args):
            self.mu.reg_write(R(3 + i), v & 0xFFFFFFFF)
        self.mu.reg_write(R(1), STACK)
        self.mu.reg_write(P.UC_PPC_REG_LR, RET)
        self.mu.emu_start(fn, RET, count=count)
        return self.r(3)

    def words(self, a, n):
        return struct.unpack('>%dI' % n, bytes(self.mu.mem_read(a, 4 * n)))


def ids_of(words):
    return {32 * w + b for w in range(len(words)) for b in range(32) if words[w] >> b & 1}


def main():
    path = sys.argv[1]
    picks = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    base, rec = X.find_marker(Rpx(path))
    reg = rec['registry']
    fighters, stages = reg['fighters'], reg['stages']
    lay = X.layout(base, reg)
    cave = lay['random'][0]
    tab = cave
    n = RS.scan_count(len(fighters))
    m = M(path, len(fighters), len(stages))
    m.mu.mem_write(OBJ, b'\x5A' * 0x200)
    m.mu.mem_write(OBJ + 0x98, b'\0' * 12)
    for i in range(8):                                  # no other players
        m.mu.mem_write(PLAYERS + 0x80 * i + 0x1E, b'\x01\xFF')
    enabled = set(range(4, 59)) | {f['ui_id'] for f in fighters if f.get('random', True)}
    off = {f['ui_id'] for f in fighters if f.get('random', True) is False}
    data_lo, data_hi = cave, cave + 32 * RS.SLOTS
    m.watch(True)
    m.call(RS.REFILL, OBJ)
    slot = m.words(tab, 8 * RS.SLOTS)
    k = next(i for i in range(RS.SLOTS) if slot[8 * i] == OBJ)
    pool = slot[8 * k + 1:8 * k + 8]
    check('%d fighter clones: the refill scans ids 0-%d; the pool holds the game\'s fighters and the %d clones in '
          'random, not the %d set to false' % (len(fighters), n - 1, len(enabled) - 55, len(off)),
          sorted(ids_of(pool)), sorted(enabled))
    check('+0x98-+0xA3 mirror ids 0-95', m.words(OBJ + 0x98, 3), pool[:3])
    stray = [(a, s) for a, s in m.writes if not (STACK - 0x1000 <= a < STACK + 8 or data_lo <= a < data_hi or
                                               OBJ + 0x98 <= a < OBJ + 0xA4)]
    check('the refill writes only the stack, its pool slot and +0x98-+0xA3 (stage pools +0xA4 on untouched)',
          stray[:4], [])
    # a cycle
    got = []
    m.watch(False)
    m.watch(True)
    while len(ids_of(m.words(tab + 32 * k + 4, 7))) > 7 and len(got) < 300:
        i = m.call(RS.PICK, 0xFFFFFFFF)
        got.append(i)
        m.call(RS.REMOVE, OBJ, i)
    check('a cycle: pick + remove until 7 left: %d picks, every enabled id once, none disabled' % len(got),
          (len(got) == len(set(got)), set(got) <= enabled, len(got)), (True, True, len(enabled) - 7))
    stray = [(a, s) for a, s in m.writes if not (STACK - 0x1000 <= a < STACK + 8 or data_lo <= a < data_hi or
                                               OBJ + 0x98 <= a < OBJ + 0xA4 or 0x105759C0 <= a < 0x105759E0 or a == 0x10492894)]
    check('picks and removes write only the stack, the pool, its mirror and the random number state', stray[:4], [])
    m.watch(False)
    m.call(0x02FFC4A8, OBJ)
    check('the count function refills under 8 left (the pool is full again)',
          sorted(ids_of(m.words(tab + 32 * k + 4, 7))), sorted(enabled))
    # uniformity
    hist = collections.Counter(m.call(RS.PICK, 0xFFFFFFFF) for _ in range(picks))
    mean = picks / len(enabled)
    check('%d picks from the full pool: only enabled ids, every one picked' % picks,
          (set(hist) <= enabled, set(hist) == enabled), (True, True))
    lo, hi = min(hist.values()), max(hist.values())
    chi2 = sum((hist.get(i, 0) - mean) ** 2 / mean for i in enabled)
    df = len(enabled) - 1
    check('uniform: chi-square %.1f for %d degrees of freedom (bound %.1f; counts %d-%d, mean %.1f)'
          % (chi2, df, df + 5 * (2 * df) ** 0.5, lo, hi, mean), chi2 < df + 5 * (2 * df) ** 0.5, True)
    # a player's pick leaves out the others' ids
    others = [5, 59, max(enabled)]
    for i, cid in enumerate(others, 1):
        m.mu.mem_write(PLAYERS + 0x80 * i + 0x1E, bytes([0, cid]))
    res = {m.call(RS.PICK, 0) for _ in range(300)}
    check('player 0\'s pick leaves out the ids of players 1-3 %s' % others, sorted(res & set(others)), [])
    # remove for every id
    bad = []
    full = struct.pack('>7I', *([0xFFFFFFFF] * 7))
    for i in range(0x100):
        m.mu.mem_write(tab + 32 * k + 4, full)
        m.mu.mem_write(OBJ + 0x98, b'\xFF' * 12)
        m.call(RS.REMOVE, OBJ, i)
        cl = set(range(224)) - ids_of(m.words(tab + 32 * k + 4, 7))
        mir = set(range(96)) - ids_of(m.words(OBJ + 0x98, 3))
        want = {i} if i < n and i != 0xFF else set()
        if cl != want or mir != {x for x in want if x < 96}:
            bad.append((i, sorted(cl), sorted(mir)))
    check('remove(id), ids 0-0xFF: exactly that bit below %d (and its mirror below 96), nothing for the rest' % n,
          bad[:3], [])
    # the fighter helper's loop with 200 database entries
    m.watch(True)
    m.mu.reg_write(R(31), LOCAL)
    m.mu.reg_write(R(30), 0)
    m.mu.mem_write(LOCAL - 0x10, b'\0' * 0x40)
    m.mu.reg_write(R(3), 200)
    m.mu.reg_write(R(1), STACK)
    m.mu.emu_start(0x0301CB40, 0x0301CB98, count=200000)
    outside = [(a, s) for a, s in m.writes if not (LOCAL <= a < LOCAL + 12)]
    check('the available-fighters helper 0x0301CAE8 with 200 entries: its loop writes only its 12 bytes',
          outside[:4], [])
    got = ids_of(m.words(LOCAL, 3))
    clones = set(range(59, 59 + len(fighters)))
    check('the helper (1.4): no clone id in its set (the online session\'s announced fighters; %d clones), the '
          'game\'s available ids below 59 still in it' % len(fighters), (sorted(got & clones), len(got - clones) > 0),
          ([], True))
    # stage refill A
    m.watch(False)
    m.watch(True)
    m.mu.mem_write(OBJ + 0xA4, b'\0' * 16)
    m.call(0x02FFB76C, OBJ, 1)
    st = ids_of(m.words(OBJ + 0xA4, 4))
    want = set(range(1, 0x38)) | {s['cosmetic'] for s in stages if s.get('random', True)}
    check('stage pool +0xA4 (%d stage clones, %d set to false): the game\'s stage ids and the clones in random'
          % (len(stages), sum(1 for s in stages if s.get('random', True) is False)),
          sorted(st), sorted(x for x in want if x < 0x63))
    stray = [(a, s) for a, s in m.writes if not (STACK - 0x1000 <= a < STACK + 8 or OBJ + 0xA4 <= a < OBJ + 0xB4)]
    check('the stage refill writes only the stack and its 16 bytes', stray[:4], [])
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
