#!/usr/bin/env python3
"""Unicorn test of tools/smashrun_field_cave.py in a patched cross_f.rpx:

  python3 tools/smashrun_field_test.py [--set NAME | --minions] PATCHED.rpx   (the set the rpx was built with:
                                                                  walkers (default), smashrun (2a), minions)

Runs the four hooked sites with the game's code around them, the calls out of the caves stubbed:
- A (0x02D9E2DC, inside "make an EnemyManager?"): stage kinds 3 / 0x82 / 0x94 / 0x95 -> yes (0x02D9E2E4), 0x10 /
  0x81 / 0x96 -> no (0x02D9E2FC).
- B (0x02D99FF8): category 1 stays 1 off the Smash Run stages; on them mgr+0x5EC and r31 become 2.
- C (0x02D9A568): the accessor set-up is called with the caller's r3 / r4; on a Smash Run stage then
  0x02DAE314(mgr+0x28, k) for the set's REQUESTS (walkers: 0x12 0x1D 0x30 0x0E 0x57 0x01 0x0B 0x13 0x19 0x1F;
  smashrun: the first five; minions 0x57-0x5A); off them nothing more; r31 and the stack kept.
- D (0x02D9B6F8, the manager's update): every frame ends in 0x02D9B1A8(mgr); on a Smash Run stage a spawn every
  INTERVAL frames: the set's kinds in turn, then the first again (walkers 0x12 0x01 0x1D 0x0B 0x30 0x13 0x0E 0x19
  0x1F; smashrun 0x12 0x1D 0x30 0x0E; minions 0x57 0x58 0x59 0x5A), with the set's placements (2 floaters, 1 the
  rest), DX left / right of the player in turn facing him, y + DY, +8 = 1.0, the rest 0; none while MAX_ALIVE live,
  none off the Smash Run stages, none without a player.
"""
import struct
import sys
import os

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_PC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch  # noqa: E402
import smashrun_field_cave as F  # noqa: E402

R = {n: getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % n) for n in range(32)}
MGR, FM, FE, STACK = 0x30000000, 0x30010000, 0x30020000, 0x31000000
FAILS = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


class Machine:
    def __init__(self, secs):
        uc = self.uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(0x02000000, 0x03000000)
        uc.mem_map(0x10000000, 0x00800000)
        for base, data in secs.items():
            uc.mem_write(base, data)
        uc.mem_map(MGR, 0x40000)
        uc.mem_map(STACK - 0x10000, 0x20000)
        self.calls = []
        self.player = (10.0, 20.0, 0.0)
        uc.hook_add(UC_HOOK_CODE, self.hook)

    def ret(self, r3=None):
        if r3 is not None:
            self.uc.reg_write(R[3], r3)
        self.uc.reg_write(UC_PPC_REG_PC, self.uc.reg_read(UC_PPC_REG_LR))

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        if addr == F.ACCESSOR_SETUP:
            self.calls.append(('setup', r(3), r(4)))
            self.ret()
        elif addr == F.REQUEST:
            self.calls.append(('request', r(3), r(4)))
            self.ret()
        elif addr == F.UPDATE_REST:
            self.calls.append(('rest', r(3)))
            self.ret()
        elif addr == F.POS_HANDLE:
            self.calls.append(('handle', r(3), r(5)))
            u.mem_write(r(4), struct.pack('>II', 0x1234, 0x5678))
            self.ret()
        elif addr == F.HANDLE_NULL:
            self.ret(0)
        elif addr == F.HANDLE_POS:
            u.mem_write(r(3), struct.pack('>3f', *self.player))
            self.ret()
        elif addr == F.SPAWN:
            p = bytes(u.mem_read(r(4), 0x3C))
            self.calls.append(('spawn', r(3), p))
            self.ret(1)

    def stage(self, kind):
        self.uc.mem_write(F.STAGE_KIND, struct.pack('>I', kind))

    def run(self, start, stop, regs):
        for k, v in regs.items():
            self.uc.reg_write(R[k], v)
        self.uc.reg_write(R[1], STACK)
        from unicorn.ppc_const import UC_PPC_REG_MSR
        self.uc.reg_write(UC_PPC_REG_MSR, self.uc.reg_read(UC_PPC_REG_MSR) | 0x2000)    # FP available
        self.uc.emu_start(start, stop, count=5000)


def load(path):
    d, _shoff, _ent, secs = rpx_patch.load(path)
    out = {}
    for s in secs:
        if s[1] == 1 and s[3] and (0x02000000 <= s[3] < 0x05000000 or 0x10000000 <= s[3] < 0x10800000):
            out[s[3]] = bytes(rpx_patch.section_data(d, s))
    return out


def main():
    if '--minions' in sys.argv:
        sys.argv.remove('--minions')
        F.configure('minions')
    if '--set' in sys.argv:
        i = sys.argv.index('--set')
        F.configure(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    print('set %s' % F.ENEMIES)
    secs = load(sys.argv[1])
    # A
    res = {}
    for kind in (3, 0x82, 0x94, 0x95, 0x10, 0x81, 0x96):
        m = Machine(secs)
        stops = []
        m.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, _: (stops.append(a), u.emu_stop())
                      if a in (0x02D9E2E4, 0x02D9E2FC) else None)
        m.run(F.SITE_A, 0x02D9E300, {0: kind})
        res[kind] = stops[0] == 0x02D9E2E4
    check(res == {3: True, 0x82: True, 0x94: True, 0x95: True, 0x10: False, 0x81: False, 0x96: False},
          'A: manager for 3 and 0x82-0x95 only %s' % {hex(k): v for k, v in res.items()})
    # B
    out = {}
    for kind in (0x10, 0x94):
        m = Machine(secs)
        m.stage(kind)
        m.run(F.SITE_B, F.SITE_B + 4, {3: MGR, 31: 1})
        out[kind] = (struct.unpack('>I', m.uc.mem_read(MGR + 0x5EC, 4))[0], m.uc.reg_read(R[31]))
    check(out == {0x10: (1, 1), 0x94: (2, 2)}, 'B: category sm on Smash Run stages only %s' % out)
    # C
    for kind, want in ((0x94, list(F.REQUESTS)), (0x10, [])):
        m = Machine(secs)
        m.stage(kind)
        m.run(F.SITE_C, F.SITE_C + 4, {3: 0x10AB0000, 4: 2, 31: MGR})
        setup = [c for c in m.calls if c[0] == 'setup']
        reqs = [c for c in m.calls if c[0] == 'request']
        check(setup == [('setup', 0x10AB0000, 2)] and [c[2] for c in reqs] == want and
              all(c[1] == MGR + 0x28 for c in reqs) and m.uc.reg_read(R[31]) == MGR and m.uc.reg_read(R[1]) == STACK,
              'C (stage 0x%X): set-up, then requests %s' % (kind, [hex(k) for k in want]))
    # D
    m = Machine(secs)
    m.stage(0x94)
    m.uc.mem_write(F.FIGHTER_MGR, struct.pack('>I', FM))
    m.uc.mem_write(FM + 0x24, struct.pack('>I', FE))
    m.uc.mem_write(FE + 0x14E9, b'\x07')
    spawns, rests = [], 0
    n = len(F.SPAWNS) + 1               # one round, then the first kind again
    for frame in range(F.INTERVAL * n):
        m.calls = []
        m.run(F.SITE_D, F.SITE_D + 4, {3: MGR, 31: MGR})
        rests += sum(1 for c in m.calls if c == ('rest', MGR))
        for c in m.calls:
            if c[0] == 'spawn':
                spawns.append((frame, c))
        if any(c[0] == 'handle' and c[2] != 7 for c in m.calls):
            check(False, 'D: handle call passes the entry byte +0x14E9')
    check(rests == F.INTERVAL * n and m.uc.reg_read(R[31]) == MGR and m.uc.reg_read(R[1]) == STACK,
          'D: every frame ends in 0x02D9B1A8(mgr); r31 / stack kept')
    check([f for f, _ in spawns] == [F.INTERVAL * i - 1 for i in range(1, n + 1)], 'D: a spawn every %d frames %s'
          % (F.INTERVAL, [f for f, _ in spawns]))
    kinds, modes, xs, ys, faces, rest_ok = [], [], [], [], [], True
    for _f, (_t, mgr, p) in spawns:
        v = struct.unpack('>II f fff f B3x i fffi fi I', p[:0x3C]) if False else None
        kind, var = struct.unpack('>II', p[0:8])
        one, x, y, z, face = struct.unpack('>5f', p[8:0x1C])
        mode = struct.unpack('>i', p[0x20:0x24])[0]
        kinds.append(kind)
        modes.append(mode)
        xs.append(round(x - m.player[0], 3))
        ys.append(round(y - m.player[1], 3))
        faces.append(face)
        rest_ok &= mgr == MGR and var == 0 and one == 1.0 and z == 0.0 and p[0x1C:0x20] == bytes(4) and \
            p[0x24:0x3C] == bytes(0x18)
        del v
    want_modes = [2 if k in (0x12, 0x1D, 0x57, 0x58) else 1 for k in F.KINDS]
    check(kinds == list(F.KINDS) + [F.KINDS[0]] and modes == [m for _k, m in F.SPAWNS] + [F.SPAWNS[0][1]] and
          modes[:-1] == want_modes,
          'D: kinds %s (then the first again), placement %s' % ([hex(k) for k in kinds], modes))
    check(xs == [F.DX if i % 2 == 0 else -F.DX for i in range(n)] and ys == [F.DY] * n and
          faces == [-1.0 if i % 2 == 0 else 1.0 for i in range(n)],
          'D: x %s from the player, y +%s, facing %s' % (xs, F.DY, faces))
    check(rest_ok, 'D: variation 0, +8 = 1.0, z 0, the rest 0')
    # limits
    m2 = Machine(secs)
    m2.stage(0x94)
    m2.uc.mem_write(F.FIGHTER_MGR, struct.pack('>I', FM))
    m2.uc.mem_write(FM + 0x24, struct.pack('>I', FE))
    m2.uc.mem_write(MGR + 0x52A + 2 * F.KINDS[2], struct.pack('>H', F.MAX_ALIVE))
    n = 0
    for frame in range(F.INTERVAL * 2):
        m2.calls = []
        m2.run(F.SITE_D, F.SITE_D + 4, {3: MGR, 31: MGR})
        n += sum(1 for c in m2.calls if c[0] == 'spawn')
    check(n == 0, 'D: none while %d live' % F.MAX_ALIVE)
    for kind, fm, label in ((0x10, FM, 'off the Smash Run stages'), (0x94, 0, 'without a fighter manager')):
        m3 = Machine(secs)
        m3.stage(kind)
        m3.uc.mem_write(F.FIGHTER_MGR, struct.pack('>I', fm))
        if fm:
            m3.uc.mem_write(FM + 0x24, struct.pack('>I', FE))
        n = rest = 0
        for frame in range(F.INTERVAL * 2):
            m3.calls = []
            m3.run(F.SITE_D, F.SITE_D + 4, {3: MGR, 31: MGR})
            n += sum(1 for c in m3.calls if c[0] == 'spawn')
            rest += sum(1 for c in m3.calls if c[0] == 'rest')
        check(n == 0 and rest == F.INTERVAL * 2, 'D: none %s, the update still runs' % label)
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
