#!/usr/bin/env python3
"""Behaviour tests of Smash Run step 2o (docs/smash-run-port.md "Step 2o") on a patched executable, in unicorn:

  python3 tools/smashrun_step2o_test.py PATCHED.rpx [SM_DIR FS3DS_DIR [MOTION_ROOT]]

SM_DIR: the Wii U param/enemy/sm (the twins' files); FS3DS_DIR: the converted 3DS param/enemy/fs (step 2a's files, the
3DS layout); MOTION_ROOT: a data root with motion/enemy/patapata/body/main.pac (the motions' real lengths; without
it the lengths are the 3DS's, read once: Bite 66, Fall 17, JumpHold 35, LandingJumpAttack 61, Landing 21).

- the spawn crash (the user's code_diag log: the last lines a Big Goomba's five mesh switches, then nothing; the
  code_diag_novis build did not crash there): every kind's start (vtable slot 41) run with a live ModelModule (the
  mesh calls succeed, as in game; smashrun_walker_test.py's machine has none, so h_vis returned before touching r3)
  passes `this` to set_rhombus (0x026A65BC: lwz r9, 8(r3)); h_vis / h_vset / h_vdef return the behaviour in r3;
- the Paratroopa's bite cadence (3DS 0x72860 / 0x72D3C / 0x72F08: the search when +0x1DC <= 0 AND the cool-down
  +0x1E8 <= 0, the cool-down 30 set at the bite's end, both counted down in the hop state only): with a target
  always in the search box, the hop states between two bites are 31 (30 counting, then the search), the searches
  without a target 10 frames apart; the Koopa's leap (0x73898: the counters every walk frame, the landing attack's
  cool-down 20): 21 walk frames between leaps;
- the twins' param objects (k2_twins's check): the game's own ctor + generic loader (0x033B4770) run natively on the
  Wii U sm files, the files tools/smashrun_twin_params.py writes (the package's) and step 2a's 3DS-layout files: the
  loader's +8 byte is 1 for the first two, 0 for the 3DS layout; Lethinium's 3DS-layout object has its attacks (G2,
  +0x30 = 4: step 2k took it) and no G6-G8 (+0x19C = 0: the cannon shot's init 0x02AE050C faults at 0x02AE06B4).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_PC, UC_PPC_REG_MSR, UC_PPC_REG_1, UC_PPC_REG_2  # noqa: E402

check = T.check
OBJ, INPUT = T.OBJ, T.INPUT
BITE_LENS = {'Bite': 66, 'Fall': 17, 'JumpHold': 35, 'LandingJumpAttack': 61, 'Landing': 21, 'JumpAttack': 40,
             'TurnPatapata': 31, 'TurnNokonoko': 21, 'Fly': 81, 'Walk': 41}


# ---------------------------------------------------------------- the twins' params: the game's own parser
class Parser:
    """the twin's ctor (this 0: allocates) and its parser (the generic loader 0x033B4770) run natively: operator
    new / the pool allocator / free stubbed, the resource handle's data = the file, the OS imports return 0"""
    HEAP, STACK, BUF, DONE = 0x20000000, 0x30000000, 0x31000000, 0x32000000
    ALLOC = (0x03374530, 0x03375FB8)           # aligned alloc (size r3), the pool alloc (pool r3, size r4)
    STUBS = {0x032D6F24: 'hcopy', 0x032D4600: 'hfree', 0x032D7880: 'lock', 0x032D8B9C: 'data', 0x032D9060: 'size',
             0x032D8E08: 'unlock', 0x032D4614: 'err', 0x03374548: 'free', 0x033760C4: 'pfree', 0x032D4200: 'hfree2'}
    MEMCPY, MEMSET = 0x04B811C0, 0x04B811D0

    def __init__(self, img):
        self.mem = img.mem

    def run(self, data, t):
        uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(0x02000000, 0x03000000)
        uc.mem_map(0x10000000, 0x01000000)
        for b, d in self.mem:
            if 0x02000000 <= b < 0x05000000:
                uc.mem_write(b, d[:0x05000000 - b])
            elif 0x10000000 <= b < 0x11000000:
                uc.mem_write(b, d[:0x11000000 - b])
        for a, n in ((self.HEAP, 0x400000), (self.STACK - 0x20000, 0x40000), (self.BUF, 0x10000), (self.DONE, 0x1000)):
            uc.mem_map(a, n)
        uc.mem_write(self.DONE, struct.pack('>I', 0x48000000))
        uc.mem_write(self.BUF, data)
        st = {'hp': self.HEAP + 0x100, 'calls': []}
        R = T.R

        def ret(r3=None):
            if r3 is not None:
                uc.reg_write(R[3], r3 & 0xFFFFFFFF)
            uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))

        def hook(u, addr, size, _):
            if addr in self.ALLOC:
                n = u.reg_read(R[3] if addr == self.ALLOC[0] else R[4])
                a = (st['hp'] + 0x3F) & ~0x3F
                st['hp'] = a + n + 0x40
                u.mem_write(a, bytes(n))
                return ret(a)
            if addr == self.MEMCPY:
                d_, s_, n = (u.reg_read(R[i]) for i in (3, 4, 5))
                u.mem_write(d_, bytes(u.mem_read(s_, n)))
                return ret(d_)
            if addr == self.MEMSET:
                d_, v, n = (u.reg_read(R[i]) for i in (3, 4, 5))
                u.mem_write(d_, bytes([v & 0xFF]) * n)
                return ret(d_)
            if 0x04B80000 <= addr < 0x04B82000:
                st['calls'].append('import')
                return ret(0)
            if addr in self.STUBS:
                nm = self.STUBS[addr]
                st['calls'].append(nm)
                if nm == 'hcopy':
                    u.mem_write(u.reg_read(R[3]), struct.pack('>I', 1))
                    return ret(u.reg_read(R[3]))
                return ret(self.BUF if nm == 'data' else len(data) if nm == 'size' else 0)

        uc.hook_add(UC_HOOK_CODE, hook)

        def call(f, *args):
            for i, a in enumerate(args):
                uc.reg_write(R[3 + i], a)
            uc.reg_write(UC_PPC_REG_1, self.STACK)
            uc.reg_write(UC_PPC_REG_2, 0x10008000)
            uc.reg_write(UC_PPC_REG_MSR, uc.reg_read(UC_PPC_REG_MSR) | 0x2000)
            uc.reg_write(UC_PPC_REG_LR, self.DONE)
            uc.emu_start(f, self.DONE, count=5000000)
            return uc.reg_read(R[3])

        uc.mem_write(self.HEAP + 0x40, bytes(4))
        obj = call(W.TWIN_CTOR[t], 0, self.HEAP + 0x40)
        uc.mem_write(self.HEAP + 0x80, struct.pack('>I', 1))
        call(W.TWIN_PARSE[t], self.HEAP + 0x80, obj)
        rd = lambda a: struct.unpack('>I', uc.mem_read(a, 4))[0]  # noqa: E731
        vecs = []
        for off in range(0, 0x800, 4):            # the object's vectors: {handler, element size, count, data, flag}
            h = rd(obj + off)
            if 0x026B0000 <= h < 0x026C0000 and 0 < rd(obj + off + 4) < 0x400 and rd(obj + off + 0x10) >> 24 < 2:
                vecs.append((off, rd(obj + off + 8), rd(obj + off + 0xC)))
        return dict(ok=bytes(uc.mem_read(obj + W.TWIN_LOADER[t] + 8, 1))[0], vecs=vecs, attacks=rd(obj + 0x30),
                    calls=st['calls'], rd=lambda o: rd(obj + o))


def twin_params(img, sm_dir, fs3_dir):
    import smashrun_twin_params as TP
    P = Parser(img)
    for t, k in W.TWIN_K:
        w = img.u32(W.TWIN_PARSE[t] + 8)                 # addi r3, r12, LOADER
        check(img.u32(W.TWIN_PARSE[t]) == 0x7C8C2378 and w >> 16 == 0x386C and w & 0xFFFF == W.TWIN_LOADER[t] and
              img.u32(W.TWIN_PARSE[t] + 12) >> 26 == 18,
              'twin 0x%X: its parser hands the object\'s loader member +0x%X to 0x033B4770' % (t, W.TWIN_LOADER[t]))
    for t, k in W.TWIN_K:
        twin = dict(W.TWIN_K)[t]
        twin_file = {'plasmawisp': 'mczakoplasmawisp', 'darios': 'mczakodarios', 'stalfos': 'mczakostalfos',
                     'zima': 'mczakozima'}[k]
        sm = open(os.path.join(sm_dir, 'enemy_param_vl_%s.bin' % twin_file), 'rb').read()
        f3 = open(os.path.join(fs3_dir, 'enemy_param_vl_%s.bin' % k), 'rb').read()
        ours, _ch = TP.remap(k, f3, sm)
        a, b, c = P.run(sm, t), P.run(ours, t), P.run(f3, t)
        full = [(o, n) for o, n, _p in a['vecs']]
        check(a['ok'] == 1 and b['ok'] == 1 and [(o, n) for o, n, _p in b['vecs']] == full and
              all(p for _o, _n, p in b['vecs']) and 'err' not in b['calls'] and c['ok'] == 0 and 'err' in c['calls'],
              '%s (%s): the Wii U file and the package\'s file parse clean (loader +8 = 1, vectors %s, every one '
              'filled); step 2a\'s 3DS-layout file is a parse error (+8 = 0: k2_twins now refuses it) %s'
              % (k, twin, full, [(hex(o), n) for o, n, _p in c['vecs']]))
        if t == 0x57:
            check(c['attacks'] == 4 and c['rd'](0x19C) == 0 and c['rd'](0x174) == 0 and b['rd'](0x19C) != 0 and
                  b['attacks'] == 4,
                  'plasmawisp: the 3DS-layout object has its 4 attacks (+0x30: step 2k\'s only check passed it) but '
                  'no G7 / G8 elements (+0x174 / +0x19C = 0: the laser\'s and the cannon shot\'s data; 0x02AE0634 '
                  'loads +0x19C, 0x02AE06B4 faults on it, the user\'s crash); the package\'s file has them')


# ---------------------------------------------------------------- the spawn: set_rhombus gets `this`
class LiveModel(H.M):
    """step 2h's machine with the mesh calls succeeding (the model handle valid, set_mesh_visibility_by_index 1)"""


def spawn(img, fn, D, cfg, byname):
    bad, seen = [], {}
    for w in W.WALKERS:
        n = w['name']
        vt = img.u32(cfg[n] + W.CF['VT'])
        start = img.u32(vt + 0xC + 8 * 41)
        for var in (0, 1, 2) if n in ('patapata', 'waddledee', 'togezo') else (0,):
            m = LiveModel(img)
            m.walker(cfg[n], state=0, kind=w['kind'], var=var)
            m.target, m.target_x = 0, 50.0
            m.call(fn['w_init'], {3: OBJ})
            m.calls = []
            try:
                m.call(start, {3: OBJ, 4: INPUT})
            except Exception as e:  # noqa: BLE001
                seen[(n, var)] = ('error', str(e))
                continue
            rh = [c for c in m.calls if c[0] == 'rhombus']
            meshes = sum(1 for c in m.calls if c[0] == 'mesh')
            seen[(n, var)] = (len(rh), meshes)
            if any(c[1] != OBJ for c in rh):
                bad.append((n, var, [hex(c[1]) for c in rh]))
    # Pooka's start needs step 2j's ray / position stubs: its machine (a live model too)
    import smashrun_step2j_test as J
    m = J.PM(img)
    m.pooka(cfg['pooka'], state=0)
    m.target_x = 50.0
    m.calls = []
    m.call(fn['pk_start'], {3: OBJ, 4: INPUT})
    rh = [c for c in m.calls if c[0] == 'rhombus']
    seen[('pooka', 0)] = (len(rh), sum(1 for c in m.calls if c[0] == 'mesh'))
    if any(c[1] != OBJ for c in rh):
        bad.append(('pooka', 0, [hex(c[1]) for c in rh]))
    print('  start runs not in this machine: %s' % {k: v for k, v in seen.items() if v[0] == 'error'})
    vis_kinds = sorted({n for (n, _v), (_r, ms) in seen.items() if ms and _r != 'error'})
    ran = {k: v for k, v in seen.items() if v[0] != 'error'}
    print('  set_rhombus calls per start: %s' % sorted({(k[0], v[0]) for k, v in ran.items()}))
    check(not bad and all(r >= 1 for (n, _v), (r, _m) in ran.items() if n not in ('furiijio', 'propellerheiho')) and
          {'kuribo', 'dekakuribo', 'waddledee', 'waddledoo'} <= set(vis_kinds),
          'spawn with a live model: every kind\'s start (slot 41) switches its meshes (%s) and passes this to '
          'set_rhombus (step 2i\'s w_start passed h_vdef\'s r3 = 1: set_rhombus read address 9, the crash at the '
          'first Big Goomba / Goomba / Waddle Dee / Waddle Doo spawn) %s' % (', '.join(vis_kinds), bad))
    got = {}
    for n in ('dekakuribo', 'ghos', 'pooka', 'waddledoo'):
        m = LiveModel(img)
        m.walker(cfg[n], state=0, kind=byname[n]['kind'])
        for lab, regs in (('h_vdef', {3: OBJ}), ('h_vset', {3: OBJ, 4: 1, 5: 0xFF}), ('h_vis', {3: OBJ, 4: 0, 5: 1})):
            m.calls = []
            m.call(fn[lab], regs)
            got[(n, lab)] = (m.uc.reg_read(T.R[3]) == OBJ, sum(1 for c in m.calls if c[0] == 'mesh'))
    check(all(ok and ms for ok, ms in got.values()),
          'h_vdef / h_vset / h_vis switch meshes and return r3 = the behaviour given %s' % got)


# ---------------------------------------------------------------- the Paratroopa's / Koopa's attack cadence
class Sim(T.World):
    """T.World with the motions' real lengths (frames / rate) and a hop / fall physics by state and frames in it"""

    def __init__(self, m, w, rows, state, cfg, lens, phys):
        self.lens, self.phys, self.mlen, self.since = lens, phys, 5, 0
        T.World.__init__(self, m, w, rows, state, cfg)

    def enter(self, s):
        self.since = 0
        return T.World.enter(self, s)

    def track(self, calls):
        for c in calls:
            if c[0] == 'motion':
                self.mframes, self.oneshot = 0, not c[5]
                stem = self.w['motions'][c[2]][0]
                rate = c[4] if c[4] > 0 else 1.0
                self.mlen = max(1, int(-(-self.lens.get(stem, 30) // rate)))

    def frame(self):
        m = self.m
        en = []
        if self.pending is not None:
            en = self.enter(self.pending)
            self.pending = None
        self.phys(self, self.since)
        m.motion_end = self.oneshot and self.mframes >= self.mlen
        self.mframes += 1
        m.calls = []
        m.uc.mem_write(INPUT, struct.pack('>ff', 7.0, 7.0))
        m.call(self.rows[self.cur][1], {3: OBJ, 4: INPUT})
        calls = list(m.calls)
        self.track(calls)
        for c in calls:
            if c[0] == 'chg':
                self.pending = c[2]
        ints = [c for c in calls if c[0] == 'chgi']
        st = self.cur
        self.since += 1
        if ints:
            self.pending = None
            en = self.enter(ints[-1][2])
        self.log.append((self.i, st, 0.0, None, calls, en))
        self.i += 1


def cadence(img, fn, cfg, byname, rows, lens):
    n = 'patapata'
    w = byname[n]

    def hop_phys(sim, k):
        m, s = sim.m, sim.cur
        if s == 2:
            m.ground, m.vy = k >= 20, (1.0 if k < 10 else -1.0)
        elif s == 1:
            m.ground, m.vy = k >= 3, -1.0
        elif s in (5, 6, 7):
            m.ground, m.vy = False, -0.5
        else:
            m.ground, m.vy = True, 0.0

    def make(var, state, found):
        m = H.M(img)
        m.walker(cfg[n], state=state, kind=w['kind'], var=var)
        m.call(fn['w_init'], {3: OBJ})
        m.found, m.target, m.target_x = found, 0, 5.0
        return Sim(m, w, rows(n), state, cfg[n], lens, hop_phys)

    # a target always in the box: bite, the cool-down (30) counted in the hop state only, the search, bite again
    sim = make(0, 2, 0)
    sim.run(400)
    sts = [e[1] for e in sim.log]
    bites = [i for i in range(1, len(sts)) if sts[i] == 5 and sts[i - 1] != 5]
    gaps = []
    for a, b in zip(bites, bites[1:]):
        last7 = max(i for i in range(a, b) if sts[i] in (6, 7))
        gaps.append(sum(1 for i in range(last7, b) if sts[i] == 2))
    seq = []
    for s in sts[bites[0]:bites[1] + 1]:
        if not seq or seq[-1] != s:
            seq.append(s)
    check(len(bites) >= 3 and set(gaps) == {31} and seq == [5, 6, 7, 1, 2, 5],
          'Paratroopa, a target always found: bite (5 wind-up 15, 6 bite 9, 7 to Bite\'s end at 1.5) -> 1 -> 2 hops '
          '-> the next bite after 31 hop frames each time (the 3DS: +0x1E8 = 30 at the bite\'s end, -1 a hop frame, '
          'the search at +0x1DC <= 0 and +0x1E8 <= 0); step 2n searched once V0 | V1 went negative: 12 '
          '%s, %d bites in 400 frames' % (gaps, len(bites)))
    # no target: the search every 10 hop frames (group 0's interval), not every frame
    sim = make(0, 2, -1)
    sim.run(120)
    frames = [e[0] for e in sim.log for c in e[4] if c[0] == 'search' and c[3][2:4] == (42.5, 50.0)]
    d = [b - a for a, b in zip(frames, frames[1:])]
    check(len(frames) >= 8 and set(d) == {10}, 'Paratroopa, no target: a search every 10 hop frames %s' % d)

    # the Koopa: found -> 14 JumpHold -> 15 the leap -> 16 -> (ground) 18 the landing attack -> 12 walk; the next leap
    # after 21 walk frames (the 3DS 0x73898: the cool-down +0x1E8 = 20 from 16's landing, -1 every walk frame)
    def koopa_phys(sim, k):
        m, s = sim.m, sim.cur
        if s in (15, 16):
            m.ground, m.vy = k >= 15, (1.0 if k < 8 else -1.0)
        else:
            m.ground, m.vy = True, 0.0

    m = H.M(img)
    m.walker(cfg[n], state=12, kind=w['kind'], var=2)
    m.call(fn['w_init'], {3: OBJ})
    m.found, m.target, m.target_x = 0, 0, 5.0
    sim = Sim(m, w, rows(n), 12, cfg[n], lens, koopa_phys)
    sim.run(500)
    sts = [e[1] for e in sim.log]
    leaps = [i for i in range(1, len(sts)) if sts[i] == 14 and sts[i - 1] != 14]
    walks = [sum(1 for i in range(a, b) if sts[i] == 12) for a, b in zip(leaps, leaps[1:])]
    check(len(leaps) >= 3 and set(walks) == {21} and 18 in sts,
          'Koopa, a target always found: leap -> landing attack (cool-down 20) -> 21 walk frames -> the next leap '
          '(step 2n: V0 negative from the leap let the search through at once: 1) %s' % walks)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    H.M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    byname = {w['name']: w for w in W.WALKERS}
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    want = {}
    for a in (A, _B, A.h):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'regions A / B / H: the code is in the executable %s' % bad[:4])

    def rows(name):
        r = {}
        for sid, s in byname[name]['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        return r

    lens = dict(BITE_LENS)
    if len(sys.argv) > 4:
        import omo
        pac = os.path.join(sys.argv[4], 'motion', 'enemy', 'patapata', 'body', 'main.pac')
        for nm, data in omo.pac_read(pac):
            lens[nm.replace('EnmPatapataBodyMain', '').replace('.omo', '')] = omo.Omo(data).frames
    spawn(img, fn, D, cfg, byname)
    cadence(img, fn, cfg, byname, rows, lens)
    if len(sys.argv) > 3:
        twin_params(img, sys.argv[2], sys.argv[3])
    print('%d failures' % len(T.FAILS))


if __name__ == '__main__':
    main()
