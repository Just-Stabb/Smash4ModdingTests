#!/usr/bin/env python3
"""Roll-off momentum test: runs the compiled MSC (.mscsb) of fighters through the roll-off's frames in a small
MSC interpreter, with the game's modules stubbed (position, stick, situation, presses, kinetic energy 3, the
air speed cap flag 0x20000044), and checks each against Hero's (fighters/brave/brave.c, the universal roll-off:
CLAUDE.md, docs/universal-mechanics.md "Roll-off momentum").

  python3 tools/rolloff_hold_test.py [--hero BRAVE.mscsb] [--mult NAME=M ...] FILE.mscsb|DIR ...

DIR: every fighter/<name>/script/msc/<name>.mscsb under it. --hero: Hero's built MSC (default: compiled from
fighters/brave/brave.c). --mult: a fighter's rolloff_air_speed_mult() (default 1.0; Luigi 1.1, Pikachu 0.2 are
built in). Exit 1 when a fighter's trace differs from Hero's.

Scenarios, frame by frame (the roll's end, Fall's main / end and the per-frame hook, global14's function, called
as the game calls them): a slide off into Fall with the stick held his way, then an aerial (Fall's end), then the
stick let go; an attack buffered off the edge (no Fall); landing; a hit; the stick let go on a frame attack is
pressed (a stick click's neutral move); moving left; the stick turned the other way. The trace is the flag each
frame. The carried speed x the fighter's multiplier is checked once (Fall's main or, buffered, the hook).
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'mscdec'))
import msc  # noqa: E402

FLAG = 0x20000044
MULTS = {'luigi': 1.1, 'pikachu': 0.2}


def f2i(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def i2f(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0]


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


class Game:
    """the modules the roll-off code reads and writes"""
    def __init__(self):
        self.x = 0.0                # 0x0F000000 self X
        self.stick = 0.0            # 0x0F000260 raw stick X on screen
        self.situation = 0          # StatusModule(1): 0 ground, 2 air
        self.press = set()          # ControlModule(0x2710, n): 0 attack, 1 special pressed this frame
        self.vx, self.vy = 0.0, 0.0  # kinetic energy 3
        self.flag = False           # 0x20000044 (no air speed cap)

    def sys(self, sid, a):
        if sid == 0x17 and len(a) == 2 and a[0] == 0:          # WorkModuleF(0, var)
            return f2i({0x0F000000: self.x, 0x0F000260: self.stick}.get(a[1], 0.0))
        if sid == 0x16:                                        # WorkModule
            if a[0] == 0x13 and a[-1] == FLAG or a[0] == 0x2710 and a[-1] == FLAG:
                self.flag = True
            elif a[0] in (0x14, 0x2711) and a[-1] == FLAG:
                self.flag = False
            elif a[0] == 0x10 and a[-1] == FLAG:
                return int(self.flag)
            return 0
        if sid == 0x18 and a == [1]:                           # StatusModule(1): situation
            return self.situation
        if sid == 0xE and len(a) == 2 and a[0] == 0x2710:      # ControlModule(0x2710, n): pressed
            return int(a[1] in self.press)
        if sid == 0x11 and len(a) == 2 and a[1] == 3:          # KineticModuleF(0xa / 0xb, 3)
            return f2i(self.vx if a[0] == 0xA else self.vy if a[0] == 0xB else 0.0)
        if sid == 0x10 and len(a) == 4 and a[0] == 0x11 and a[1] == 3:   # KineticModule(0x11, 3, x, y)
            self.vx, self.vy = i2f(a[2]), i2f(a[3])
            return 0
        return 0


class VM:
    def __init__(self, path):
        self.m = msc.MscFile()
        self.m.readFromBytes(open(path, 'rb').read(), '<')
        self.at = {s.bounds[0]: s for s in self.m.scripts}
        self.idx = {id(s): i for i, s in enumerate(self.m.scripts)}
        self.g = {}
        self.game = None
        self.steps = 0

    def func(self, i):
        return self.m.scripts[i]

    def call(self, script, args=()):
        cmds = script.cmds
        pos = {c.commandPosition: k for k, c in enumerate(cmds)}
        loc = {}
        st = []
        k = 0
        for n, a in enumerate(args):
            loc[n] = a
        while k < len(cmds):
            self.steps += 1
            if self.steps > 2000000:
                raise RuntimeError('runaway')
            c = cmds[k]
            op, p, push = c.command, c.parameters, c.pushBit
            k += 1
            if op in (0x0, 0x2, 0x32, 0x33) and op != 0x33:
                continue
            if op == 0x33:
                st.pop()
            elif op == 0x3:
                return None
            elif op in (0x6, 0x8):
                return st.pop()
            elif op in (0x7, 0x9):
                return None
            elif op in (0xA, 0xD):
                st.append(p[0] & 0xFFFFFFFF)
            elif op == 0xB:
                st.append((loc if p[0] == 0 else self.g).get(p[1], 0))
            elif op in (0xE, 0xF, 0x10, 0x11, 0x12, 0x16, 0x17, 0x19, 0x1A, 0x1B):
                b, a = s32(st.pop()), s32(st.pop())
                r = {0xE: a + b, 0xF: a - b, 0x10: a * b, 0x11: int(a / b) if b else 0, 0x12: a % b if b else 0,
                     0x16: a & b, 0x17: a | b, 0x19: a ^ b, 0x1A: a << b, 0x1B: a >> b}[op]
                if push:
                    st.append(r & 0xFFFFFFFF)
            elif op in (0x13, 0x18, 0x2B):
                a = s32(st.pop())
                r = {0x13: -a, 0x18: ~a, 0x2B: int(not a)}[op]
                if push:
                    st.append(r & 0xFFFFFFFF)
            elif op in (0x14, 0x15, 0x3F, 0x40):
                d = loc if p[0] == 0 else self.g
                v = d.get(p[1], 0)
                d[p[1]] = (v + (1 if op == 0x14 else -1)) & 0xFFFFFFFF if op in (0x14, 0x15) else \
                    f2i(i2f(v) + (1 if op == 0x3F else -1))
            elif op in (0x1C, 0x41):
                (loc if p[0] == 0 else self.g)[p[1]] = st.pop()
                if push:
                    st.append((loc if p[0] == 0 else self.g)[p[1]])
            elif 0x1D <= op <= 0x24 or 0x42 <= op <= 0x45:
                d = loc if p[0] == 0 else self.g
                v, b = d.get(p[1], 0), st.pop()
                if op >= 0x42:
                    a, bb = i2f(v), i2f(b)
                    d[p[1]] = f2i({0x42: a + bb, 0x43: a - bb, 0x44: a * bb, 0x45: a / bb if bb else 0.0}[op])
                else:
                    a, bb = s32(v), s32(b)
                    d[p[1]] = {0x1D: a + bb, 0x1E: a - bb, 0x1F: a * bb, 0x20: int(a / bb) if bb else 0,
                               0x21: a % bb if bb else 0, 0x22: a & bb, 0x23: a | bb, 0x24: a ^ bb}[op] & 0xFFFFFFFF
            elif 0x25 <= op <= 0x2A:
                b, a = s32(st.pop()), s32(st.pop())
                r = {0x25: a == b, 0x26: a != b, 0x27: a < b, 0x28: a <= b, 0x29: a > b, 0x2A: a >= b}[op]
                if push:
                    st.append(int(r))
            elif 0x46 <= op <= 0x4B:
                b, a = i2f(st.pop()), i2f(st.pop())
                r = {0x46: a == b, 0x47: a != b, 0x48: a < b, 0x49: a <= b, 0x4A: a > b, 0x4B: a >= b}[op]
                if push:
                    st.append(int(r))
            elif 0x3A <= op <= 0x3D:
                b, a = i2f(st.pop()), i2f(st.pop())
                r = {0x3A: a + b, 0x3B: a - b, 0x3C: a * b, 0x3D: a / b if b else 0.0}[op]
                if push:
                    st.append(f2i(r))
            elif op == 0x3E:
                a = i2f(st.pop())
                if push:
                    st.append(f2i(-a))
            elif op in (0x38, 0x39):
                j = len(st) - 1 - p[0]
                st[j] = f2i(float(s32(st[j]))) if op == 0x38 else int(i2f(st[j])) & 0xFFFFFFFF
            elif op == 0x2C:
                for _ in range(p[0]):
                    st.pop()
            elif op == 0x2D:
                a = [st.pop() for _ in range(p[0])][::-1]
                r = self.game.sys(p[1], a)
                if push:
                    st.append((r or 0) & 0xFFFFFFFF)
            elif op == 0x2E:
                c.tryPush = push
            elif op in (0x2F, 0x30, 0x31):
                addr = st.pop()
                a = [st.pop() for _ in range(p[0])][::-1]
                tgt = self.at.get(addr)
                r = self.call(tgt, a) if tgt is not None else 0
                t = next((cmds[j] for j in range(k - 2, -1, -1) if cmds[j].command == 0x2E), None)
                if op == 0x2F and t is not None and t.pushBit:
                    st.append((r or 0) & 0xFFFFFFFF)
            elif op in (0x34, 0x35):
                v = st.pop()
                if (op == 0x34) != bool(v):
                    k = pos[p[0]]
            elif op in (0x4, 0x5, 0x36):
                k = pos[p[0]]
            else:
                raise RuntimeError('op 0x%X not handled' % op)
        return None

    # --- the roll-off's functions
    def hook(self):
        """global14's function (the per-frame hook): the address set into global 14 in the init"""
        for s in self.m.scripts:
            cs = s.cmds
            for j in range(1, len(cs)):
                if cs[j].command == 0x1C and cs[j].parameters[:2] == [1, 14] and cs[j - 1].command in (0xA, 0xD) \
                        and cs[j - 1].parameters[0] in self.at:
                    return self.at[cs[j - 1].parameters[0]]
        raise RuntimeError('no global14 hook')

    def roll_ends(self):
        out = []
        for s in self.m.scripts:
            cs = s.cmds
            for j in range(2, len(cs)):
                if cs[j].command == 0x2D and cs[j].parameters[1] == 0x16 and cs[j - 1].command == 0xA and \
                        cs[j - 1].parameters[0] == FLAG and cs[j - 3].command in (0xA, 0xD) and cs[j - 3].parameters[0] == 0x13:
                    out.append(s)
                    break
        return out


def frame(vm, game, status, situation, x=None, stick=None, press=()):
    vm.g[4] = status
    game.situation = situation
    if x is not None:
        game.x = x
    if stick is not None:
        game.stick = stick
    game.press = set(press)
    vm.call(vm.hook_fn)
    return int(game.flag)


def roll_off(vm, game, nxt, situation=2, speed=2.2):
    """the roll (EscapeF) slides off: its end with the next status, then that status's main"""
    vm.g[4] = 0x20
    vm.g[6] = nxt
    game.situation = situation
    game.vx = speed
    vm.call(vm.roll_end)
    vm.g[5], vm.g[4] = 0x20, nxt
    if nxt == 0xE:
        vm.call(vm.func(501))       # Fall main: rolloff_fall_speed


def scenarios(path, mult=1.0):
    """{scenario: trace}, speed checks"""
    out, problems = {}, []

    def fresh():
        vm = VM(path)
        vm.game = game = Game()
        vm.hook_fn = vm.hook()
        ends = vm.roll_ends()
        if not ends:
            raise RuntimeError('no roll end (WorkModule(0x13, 1, 0x20000044))')
        vm.roll_end = ends[0]
        frame(vm, game, 0x20, 0, x=0.0, stick=1.0)     # the roll's last frame on the ground
        return vm, game

    # A: into Fall, stick held his way (right); an aerial at frame 4 (Fall's end); stick let go at frame 8
    vm, game = fresh()
    roll_off(vm, game, 0xE)
    if abs(game.vx - 2.2 * mult) > 1e-4:
        problems.append('Fall: carried speed %.4f, expected 2.2 x %.2f' % (game.vx, mult))
    tr = []
    for t in range(1, 12):
        if t == 4:
            vm.call(vm.func(535))   # Fall's end -> aerial
        st = 0xE if t < 4 else 0x34
        tr.append(frame(vm, game, st, 2, x=t * 2.0, stick=1.0 if t < 8 else 0.0))
    out['A fall, aerial, let go at 8'] = tr
    # B: an attack buffered off the edge (no Fall)
    vm, game = fresh()
    roll_off(vm, game, 0x34)
    tr = [frame(vm, game, 0x34, 2, x=t * 2.0, stick=1.0) for t in range(1, 5)]
    if abs(game.vx - 2.2 * mult) > 1e-4:
        problems.append('buffered aerial: carried speed %.4f, expected 2.2 x %.2f' % (game.vx, mult))
    tr += [frame(vm, game, 0x34, 2, x=10.0, stick=0.2)]
    out['B buffered aerial, let go'] = tr
    # C: landing with the stick held
    vm, game = fresh()
    roll_off(vm, game, 0xE)
    tr = [frame(vm, game, 0xE, 2, x=t * 2.0, stick=1.0) for t in range(1, 4)]
    tr += [frame(vm, game, 0x16, 0, x=8.0, stick=1.0), frame(vm, game, 0x0, 0, x=8.0, stick=1.0)]
    out['C landing'] = tr
    # D: a hit
    vm, game = fresh()
    roll_off(vm, game, 0xE)
    tr = [frame(vm, game, 0xE, 2, x=t * 2.0, stick=1.0) for t in range(1, 4)]
    tr += [frame(vm, game, 0x48, 2, x=8.0, stick=1.0)]
    out['D hit'] = tr
    # E: let go on a frame attack is pressed (stick click), then really let go
    vm, game = fresh()
    roll_off(vm, game, 0xE)
    tr = [frame(vm, game, 0xE, 2, x=t * 2.0, stick=1.0) for t in range(1, 4)]
    tr += [frame(vm, game, 0x34, 2, x=8.0, stick=0.0, press=(0,)), frame(vm, game, 0x34, 2, x=10.0, stick=0.0)]
    tr += [frame(vm, game, 0x34, 2, x=12.0, stick=0.0, press=(1,))]
    out['E stick click'] = tr
    # F: moving left, stick left, then turned right
    vm, game = fresh()
    game.stick = -1.0
    roll_off(vm, game, 0xE, speed=-2.2)
    tr = [frame(vm, game, 0xE, 2, x=-t * 2.0, stick=-1.0) for t in range(1, 5)]
    tr += [frame(vm, game, 0xE, 2, x=-10.0, stick=0.5)]
    out['F left, turned'] = tr
    # G: a weak stick his way (under 0.3)
    vm, game = fresh()
    roll_off(vm, game, 0xE)
    tr = [frame(vm, game, 0xE, 2, x=t * 2.0, stick=1.0) for t in range(1, 3)]
    tr += [frame(vm, game, 0xE, 2, x=6.0, stick=0.25)]
    out['G stick under 0.3'] = tr
    # H: a roll that ends on the ground: nothing
    vm, game = fresh()
    vm.g[6] = 0x0
    game.situation = 0
    vm.call(vm.roll_end)
    tr = [frame(vm, game, 0x0, 0, x=0.0, stick=1.0) for _ in range(3)]
    out['H ground'] = tr
    return out, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--hero')
    ap.add_argument('--mult', action='append', default=[])
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    mults = dict(MULTS)
    for m in a.mult:
        k, v = m.split('=')
        mults[k] = float(v)
    hero = a.hero
    tmp = None
    if not hero:
        tmp = tempfile.mkdtemp()
        hero = os.path.join(tmp, 'brave.mscsb')
        subprocess.run([sys.executable, os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'),
                        os.path.join(ROOT, 'fighters/brave/brave.c'), '-o', hero], check=True, capture_output=True)
    ref, _ = scenarios(hero)
    if a.v:
        for k, v in ref.items():
            print('Hero %-28s %s' % (k, ''.join(map(str, v))))
    files = []
    for p in a.paths:
        if os.path.isdir(p):
            for d, _ds, fs in sorted(os.walk(p)):
                for f in sorted(fs):
                    if f.endswith('.mscsb') and os.path.basename(d) == 'msc' and f[:-6] == os.path.basename(
                            os.path.dirname(os.path.dirname(d))):
                        files.append(os.path.join(d, f))
        else:
            files.append(p)
    bad = 0
    for path in files:
        name = os.path.basename(path)[:-6]
        try:
            got, problems = scenarios(path, mults.get(name, 1.0))
        except Exception as e:              # noqa: BLE001
            print('%-14s FAIL %s' % (name, e))
            bad += 1
            continue
        diff = [k for k in ref if got[k] != ref[k]]
        if diff or problems:
            bad += 1
            print('%-14s FAIL %s' % (name, '; '.join(['%s: %s (Hero %s)' % (k, ''.join(map(str, got[k])),
                                                                            ''.join(map(str, ref[k]))) for k in diff] + problems)))
        else:
            print('%-14s ok' % name)
    print('%d of %d as Hero\'s' % (len(files) - bad, len(files)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
