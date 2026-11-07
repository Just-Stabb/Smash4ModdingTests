#!/usr/bin/env python3
"""Unicorn test of tools/smashrun_walker_cave.py in a patched cross_f.rpx:

  python3 tools/smashrun_walker_test.py [--keep-flip] PATCHED.rpx [ENEMY_ROOT]

ENEMY_ROOT (optional): the installed converted enemies (motion/enemy/<name>/body/main.pac, animcmd/enemy/<name>/):
then every set entry must be an OMO of K's pac and every script of K's animcmd files a hash of K's script hashsets.

Runs the cave's code and the game's around it, the framework's calls stubbed (modules are fake objects):
- the hook words; the three spaces holding only the cave's code and data (zeros after);
- the factory 0x02DB94CC: each walker kind -> operator new(OBJ_SIZE), the Behavior ctor (obj, acc, K, variation),
  module+8 = obj with vptr VT, BehaviorImpl's init, +0x168 its CFG, its hashsets and nine damage labels; 2a's kinds
  and the twins / bosses still call their own create, other kinds none;
- the vtable (BehaviorImpl's but the overrides), slots 64-67 the kind's 3DS states, slot 38 0;
- fix v3 (the twins' slot 38, initialize_after's set_lr, notify_on_remove's type);
- change_state per kind: its 3DS state table (unknown / empty ids -> 1);
- initialize (the kind's energy words, the kick), start (face the target, the first state: Waddle Dee 2 for
  variations 0 / 1), set_attack_data (the kind's attacks only in their states: the contact attack in the Kuribo's
  5 and the Shy Guy's 9, the bullet attack in each death state, nothing else);
- each kind's behaviour in a small world (ground / walls / ledges / the target's search / the speed's y / the
  motion's end stubbed, x moved by the AI stick): the 3DS state sequences of README (Fix v5);
- T2 / S2, the sets and hashsets.
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

pc = __import__('unicorn.ppc_const', fromlist=['x'])
R = {n: getattr(pc, 'UC_PPC_REG_%d' % n) for n in range(32)}
FR = {n: getattr(pc, 'UC_PPC_REG_FPR%d' % n) for n in range(32)}
HEAP, STACK = 0x30000000, 0x31000000
OBJ, ACC, MOD = HEAP + 0x1000, HEAP + 0x10000, HEAP + 0x200
ATKM, GROUND, EKIN, MOTION, KIN, POSTURE = (HEAP + 0x20000 + 0x100 * i for i in range(6))
KVT, ARRP, ARR, EN, INPUT, PM, MGR, FLAGS = (HEAP + 0x21000 + 0x100 * i for i in range(8))
KICK = 0x02000004               # the kinetic vt+0xFC target (a stub address)
DONE = 0x02000000               # return address of a run
CREATES = {0x50: 0x02DD0438, 0x51: 0x02DC7414, 0x52: 0x026B7344, 0x53: 0x026C2E9C, 0x54: 0x026BE944,
           0x55: 0x026BB3E8, 0x56: 0x026C5F80, 0x57: 0x026CF4DC, 0x58: 0x026CBA64, 0x59: 0x026D1DFC,
           0x5A: 0x026D6834, 0x5B: 0x02DDB82C, 0x5E: 0x026E24EC, 0x5F: 0x026D80A0, 0x60: 0x026DB864}
REVERSE_LR = 0x026A7A20
SET_LR = 0x026A780C
FAILS = []
VT_ADDR = [0]


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def f2d(v):
    return struct.unpack('>d', struct.pack('>Q', v))[0]


class Machine:
    def __init__(self, img):
        uc = self.uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(0x02000000, 0x03000000)
        uc.mem_map(0x10000000, 0x00800000)
        for base, data in img.mem:
            if 0x02000000 <= base < 0x05000000 or 0x10000000 <= base < 0x10800000:
                uc.mem_write(base, data[:max(0, min(len(data), 0x05000000 - base))]
                             if base < 0x05000000 else data)
        uc.mem_map(HEAP, 0x40000)
        uc.mem_map(STACK - 0x10000, 0x20000)
        uc.mem_write(DONE, struct.pack('>II', 0x48000000, 0x48000000))      # b . (stop addresses)
        self.calls = []
        self.ground, self.walls, self.cliff, self.motion_end = True, set(), False, False
        self.target, self.target_x = 0, 0.0
        self.found, self.vy, self.stopped = -1, 0.0, True
        self.creates = dict((v, k) for k, v in CREATES.items())
        self.vt = VT_ADDR[0]
        uc.hook_add(UC_HOOK_CODE, self.hook)
        # fake modules
        w = self.w32
        w(ACC + 0x30C8, ATKM)
        w(ACC + 0x30DC, GROUND)
        w(ACC + 0x30E8, EKIN)
        w(ACC + 0x30F0, MOTION)
        w(ACC + 0x3130, KIN)
        w(ACC + 0x311C, POSTURE)
        w(KIN, KVT)
        w(KVT + 0xFC, KICK)
        w(KIN + 8, ARRP)
        w(ARRP, ARR)
        w(ARR + 4, EN)
        w(ARR + 0x14, FLAGS)

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))

    def r32(self, a):
        return struct.unpack('>I', self.uc.mem_read(a, 4))[0]

    def wf(self, a, v):
        self.uc.mem_write(a, struct.pack('>f', v))

    def rf(self, a):
        return struct.unpack('>f', self.uc.mem_read(a, 4))[0]

    def ret(self, r3=None):
        if r3 is not None:
            self.uc.reg_write(R[3], r3 & 0xFFFFFFFF)
        self.uc.reg_write(UC_PPC_REG_PC, self.uc.reg_read(UC_PPC_REG_LR))

    def fr(self, n):
        return f2d(self.uc.reg_read(FR[n]))

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        c = self.calls
        if addr in self.creates:
            c.append(('create', addr, r(3), r(4), r(5)))
            self.ret(0x7000 + r(4))
        elif addr == W.OPNEW:
            c.append(('new', r(3)))
            self.uc.mem_write(OBJ, b'\xCC' * W.OBJ_SIZE)
            self.ret(OBJ)
        elif addr == W.BEH_CTOR:
            c.append(('ctor', r(3), r(4), r(5), r(6)))
            self.w32(r(3), r(4))
            self.w32(r(3) + 4, 0)
            self.w32(r(3) + 8, r(5))
            self.w32(r(3) + 0xC, r(6))
            self.w32(r(3) + 0xE0, 0x1234)
            self.ret(r(3))
        elif addr == W.CHANGE_KINETIC:
            c.append(('kinetic', r(3), r(4)))
            self.ret()
        elif addr == W.SET_ATTACH_GROUND:
            c.append(('attach', r(3), r(4)))
            self.ret()
        elif addr == W.SET_MOTION_LABEL:
            self.w32(r(3) + 0xA8, r(5))
            self.ret()
        elif addr == W.SET_DAMAGE_LABEL:
            for i, x in enumerate((r(4), r(5), r(6), r(7), r(8), r(9), r(10))):
                self.w32(r(3) + 0xB0 + 4 * i, x)
            sp = r(1)
            self.w32(r(3) + 0xCC, self.r32(sp + 8))
            self.w32(r(3) + 0xD0, self.r32(sp + 0xC))
            self.ret()
        elif addr == W.CHANGE_MOTION:
            c.append(('motion', r(3), r(4), round(self.fr(1), 4), round(self.fr(2), 4), r(5), round(self.fr(3), 4)))
            self.ret()
        elif addr == W.NOTIFY_DEATH:
            c.append(('notify_death', r(3)))
            self.ret()
        elif addr == W.BULLET:
            c.append(('bullet', r(3)))
            self.ret()
        elif addr == W.IS_TOUCH:
            c.append(('touch', r(3), r(4)))
            self.ret(int(self.ground) if r(4) == 8 else int(r(4) in self.walls))
        elif addr == W.MOTION_IS_END:
            c.append(('is_end', r(3)))
            self.ret(int(self.motion_end))
        elif addr == W.NEAREST:
            c.append(('nearest', r(3)))
            self.ret(self.target)
        elif addr == W.CHECK_TURN:
            # check_turn_to_target (its prologue saves f31 with a paired-single store Unicorn can't run): the game's
            # test, 0x026A69C0-0x026A6A14: dx = target x - posture x; dx < -f1 and lr != -1, or dx > f1 and lr != 1
            c.append(('check_turn', r(4), self.fr(1)))
            if r(4) >= 0x80000000:
                self.ret(0)
            else:
                dx = self.target_x - self.rf(POSTURE + 0x10)
                lr = self.rf(POSTURE + 0x60)
                self.ret(int((dx < -self.fr(1) and lr != -1.0) or (dx > self.fr(1) and lr != 1.0)))
        elif addr == W.GET_TARGET_POS:
            c.append(('target_pos', r(5)))
            self.wf(r(3), self.target_x)
            self.wf(r(3) + 4, 0.0)
            self.wf(r(3) + 8, 0.0)
            self.ret()
        elif addr == W.SEARCH:
            c.append(('search', r(4), r(5), tuple(round(self.fr(i), 3) for i in range(1, 6))))
            self.ret(self.found)
        elif addr == W.GET_SPEED:
            self.wf(r(3), 0.0)
            self.wf(r(3) + 4, self.vy)
            self.wf(r(3) + 8, 0.0)
            self.ret()
        elif addr == W.CLEAR_SPEED:
            c.append(('clear_speed', r(3)))
            self.ret()
        elif addr == W.IS_STOPPED:
            self.ret(int(self.stopped))
        elif addr == W.CHECK_CLIFF_LR:
            c.append(('cliff', r(3), self.fr(1)))
            self.ret(int(self.cliff))
        elif addr == W.SET_RHOMBUS:
            c.append(('rhombus', r(3)))
            self.ret()
        elif addr == SET_LR:
            c.append(('set_lr', r(3), self.fr(1), r(4), r(5)))
            self.ret()
        elif addr == 0x02C6108C:
            c.append(('flip', r(4)))
            self.ret()
        elif addr in (0x02C367C4, 0x02DB49F8, 0x02DB3518):
            self.ret()
        elif addr == 0x02DB3AB0:
            c.append(('defeat_fx', r(3)))
            self.ret()
        elif addr == 0x02DB3574:
            c.append(('vanish_fx', r(3)))
            self.ret()
        elif addr == REVERSE_LR:
            c.append(('reverse_lr', r(3), r(4), r(5)))
            lr = -self.rf(POSTURE + 0x60)
            self.wf(POSTURE + 0x60, lr)
            if r(5):
                self.wf(r(3) + 0x10, lr)
            self.ret()
        elif addr in (W.CHG_BASE, W.CHG_INT):
            pm = lambda p: (self.r32(p), self.r32(p + 4))  # noqa: E731
            c.append(('chg' if addr == W.CHG_BASE else 'chgi', r(3), r(4), pm(r(5)), pm(r(6)), pm(r(7))))
            self.w32(r(3) + 4, r(4))
            self.ret()
        elif addr == W.ATK_CLEAR:
            c.append(('atk_clear', r(3)))
            self.ret()
        elif addr == W.ATK_CREATE:
            c.append(('atk_create', r(3), r(4)))
            self.ret()
        elif addr == W.ATK_SET:
            c.append(('atk_set', r(3), r(4), r(5), r(6)))
            self.ret()
        elif addr == KICK:
            c.append(('kick', r(3), r(4)))
            self.ret()
        elif addr == E.PARAM_LOAD:
            c.append(('load', r(3)))
            self.ret(0x1234)

    def stage(self, kind):
        self.w32(F.STAGE_KIND, kind)

    def run(self, start, stop, regs, fregs=None):
        for k, v in regs.items():
            self.uc.reg_write(R[k], v & 0xFFFFFFFF)
        for k, v in (fregs or {}).items():
            self.uc.reg_write(FR[k], struct.unpack('>Q', struct.pack('>d', v))[0])
        self.uc.reg_write(R[1], STACK)
        self.uc.reg_write(UC_PPC_REG_MSR, self.uc.reg_read(UC_PPC_REG_MSR) | 0x2000)
        self.uc.emu_start(start, stop, count=50000)

    def call(self, fn, regs, fregs=None):
        self.uc.reg_write(UC_PPC_REG_LR, DONE)
        self.run(fn, DONE, regs, fregs)

    def walker(self, cfg, state=0, lr=-1.0, x=0.0, kind=0, var=0):
        """a walker object (as create leaves it) with the fake modules"""
        self.uc.mem_write(OBJ, bytes(W.OBJ_SIZE))
        self.w32(OBJ, ACC)
        self.w32(OBJ + 4, state)
        self.w32(OBJ + 8, kind)
        self.w32(OBJ + 0xC, var)
        self.w32(OBJ + 0x168, cfg)
        self.w32(OBJ + 0xE0, self.vt)
        self.wf(OBJ + 0x10, lr)
        self.wf(POSTURE + 0x10, x)
        self.wf(POSTURE + 0x14, 0.0)
        self.wf(POSTURE + 0x60, lr)


class World:
    """frames of one walker: the deferred change_state takes effect next frame (enter, then update), the interrupt
    one at once (its enter now); a one-shot motion ends 5 frames after it starts; x += 2 * the AI stick"""

    def __init__(self, m, w, rows, state, cfg):
        self.m, self.w, self.rows, self.cfg = m, w, rows, cfg
        self.cur, self.pending, self.mframes, self.oneshot = state, None, 0, False
        self.log, self.script, self.i = [], {}, 0
        self.enter(state)

    def enter(self, s):
        m = self.m
        m.calls = []
        self.cur = s
        if self.rows[s][0] == W.ZIMA_REMOVE_ENTER:          # the game's remove state: not run here
            return []
        m.call(self.rows[s][0], {3: OBJ})
        self.track(m.calls)
        return m.calls

    def track(self, calls):
        for c in calls:
            if c[0] == 'motion':
                self.mframes, self.oneshot = 0, not c[5]

    def frame(self):
        m = self.m
        if self.i in self.script:
            self.script[self.i](self)
        en = []
        if self.pending is not None:
            en = self.enter(self.pending)
            self.pending = None
        m.motion_end = self.oneshot and self.mframes >= 5
        self.mframes += 1
        m.calls = []
        m.uc.mem_write(INPUT, struct.pack('>ff', 7.0, 7.0))
        m.call(self.rows[self.cur][1], {3: OBJ, 4: INPUT})
        calls = list(m.calls)
        self.track(calls)
        stick = struct.unpack('>ff', m.uc.mem_read(INPUT, 8))
        x = m.rf(POSTURE + 0x10) + (2.0 * stick[0] if stick[0] != 7.0 else 0.0)
        m.wf(POSTURE + 0x10, x)
        for c in calls:
            if c[0] == 'chg':
                self.pending = c[2]
        ints = [c for c in calls if c[0] == 'chgi']
        st = self.cur
        if ints:
            self.pending = None
            en = self.enter(ints[-1][2])
        self.log.append((self.i, st, round(x, 1), stick, calls, en))
        self.i += 1

    def run(self, n):
        for _ in range(n):
            self.frame()

    def states(self, since=0):
        out = []
        for e in self.log[since:]:
            if not out or out[-1] != e[1]:
                out.append(e[1])
        return out


def main():
    if '--keep-flip' in sys.argv:            # the variant built with smashrun_walker_cave.py --keep-flip
        sys.argv.remove('--keep-flip')
        W.KEEP_FLIP = True
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    vt_words = W.read_vt(img)
    A, B, d = W.assemble(vt_words)
    D = d.addr
    VT_ADDR[0] = D['vt']
    cfg = {w['kind']: D['cfg_' + w['name']] for w in W.WALKERS}
    fn = dict(A.labels)
    byname = {w['name']: w for w in W.WALKERS}

    # hooks and space
    check(all(img.u32(s) == W.branch(s, fn[f]) for s, f in ((W.SITE_F, 'cave_f'), (W.SITE_T, 'cave_t'),
                                                            (W.SITE_S, 'cave_s'), (W.SITE_ROT, 'cave_rot'),
                                                            (W.SITE_DEATH, 'cave_death'))),
          'hooks: F2 / T2 / S2 / initialize_after / notify_on_remove branch to the cave')
    want = {}
    for a in (A, B, A.area):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    for base, words in d.chunks:
        want.update({base + 4 * i: x for i, x in enumerate(words)})
    bad = [hex(x) for lo, hi in W.REGIONS for x in range(lo, hi, 4) if img.u32(x) != want.get(x, 0)]
    check(not bad, 'space %s: the code (A to 0x%08X, B to 0x%08X, C to 0x%08X), the data, zeros after %s'
          % (', '.join('0x%08X-0x%08X' % r for r in W.REGIONS), A.pc, B.pc, A.area.pc, bad[:4]))
    check(all(img.u32(s_) == W.branch(s_, fn['area_%d' % i]) for i, (s_, _w, _d, _b, _k, _x) in
              enumerate(W.AREA_SITES)), 'fix v7: the three area-table sites (0x02D89898 0x02D8A24C 0x02D8FB98) '
          'branch to the cave')
    cave_f_2a = E.assemble(E.build_sets(img))[0].addr('cave_f')
    check(img.u32(E.SITE_F) == W.branch(E.SITE_F, cave_f_2a),
          'step 2a\'s factory hook still in place (0x%08X)' % E.SITE_F)

    # the factory
    for w in W.WALKERS:
        k = w['kind']
        m = Machine(img)
        m.w32(MOD + 4, ACC)
        m.w32(MOD + 8, 0)
        m.run(0x02DB94CC, 0x02DB96F8, {3: MOD, 4: k, 5: 0, 6: 2})
        o = OBJ
        init = [m.r32(o + x) for x in range(0xE4, W.OBJ_SIZE, 4)]
        exp = []
        for x in range(0xE4, W.OBJ_SIZE, 4):
            v = 0
            if x == 0xE8:
                v = img.u32(W.COMMON_PMF)
            elif x == 0xEC:
                v = img.u32(W.COMMON_PMF + 4)
            elif x == 0x120:
                v = 0x01000000
            elif x == 0x15C:
                v = 0xFFFFFFFF
            elif x == 0x168:
                v = cfg[k]
            exp.append(v)
        calls = [c for c in m.calls if c[0] in ('new', 'ctor', 'create')]
        labels = [m.r32(o + 0xB0 + 4 * i) for i in range(9)]
        check(calls == [('new', W.OBJ_SIZE), ('ctor', OBJ, ACC, k, 2)] and m.r32(MOD + 8) == OBJ and
              m.r32(o + 0xE0) == D['vt'] and init == exp and m.r32(o + 0xA8) == D.get('hs_' + w['name'], 0) and
              labels == W.damage_labels(w) and m.r32(o + 8) == k,
              'F2: %s 0x%02X -> new(0x%X), ctor(acc, K, var), module+8, vptr VT, BehaviorImpl init, CFG, '
              'hashsets 0x%X, damage labels %s' % (w['name'], k, W.OBJ_SIZE, m.r32(o + 0xA8), labels))
    res = {}
    for k in [0x30, 0x0E, 0x12, 0x1D, 0x57, 0x5A, 0x50, 0x60, 0x00, 0x02, 0x2F, 0x4F, 0x61]:
        m = Machine(img)
        m.w32(MOD + 4, ACC)
        m.w32(MOD + 8, 0)
        m.run(0x02DB94CC, 0x02DB96F8, {3: MOD, 4: k, 5: 0, 6: 0})
        res[k] = ([c[1:] for c in m.calls if c[0] in ('create', 'new')], m.r32(MOD + 8))
    twins = {p[1]: p[3] for p in E.PAIRS}
    ok = all(res[k] == ([(twins[k], ACC, k, 0)], 0x7000 + k) for k in twins)
    ok &= all(res[k] == ([(CREATES[k], ACC, k, 0)], 0x7000 + k) for k in (0x57, 0x5A, 0x50, 0x60))
    ok &= all(res[k] == ([], 0) for k in (0x00, 0x02, 0x2F, 0x4F, 0x61))
    check(ok, 'F2: 2a\'s kinds call their twins\' create, 0x50-0x60 their own, 0x00 0x02 0x2F 0x4F 0x61 none')

    # the vtable
    vt = [img.u32(D['vt'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    slots = {k: vt[(0xC + 8 * k) // 4] for k in range(76)}
    bi = {k: vt_words[(0xC + 8 * k) // 4] for k in range(74)}
    over = {12: W.ZIMA_CAPTURE_MOTION, 38: W.ZIMA_ONE if W.KEEP_FLIP else fn['w_noflip'], 40: fn['w_init'],
            41: fn['w_start'], 45: fn['w_atk'], 20: fn['w_tread'], 64: fn['w_r64'], 65: fn['w_r65'], 66: fn['w_r66'],
            67: fn['w_r67'], 72: fn['w_chg'], 73: fn['w_chgi'], 74: fn['w_chg'], 75: fn['w_chgi']}
    ok = vt[:3] == vt_words[:3] and all(slots[k] == over.get(k, bi.get(k)) for k in range(76))
    ok &= all(vt[(0x8 + 8 * k) // 4] == 0 for k in range(76))
    check(ok, 'VT: BehaviorImpl\'s 74 slots (dtor 0x%08X, update 0x%08X kept) with 12 38 40 41 45 64-67 72-75 '
          'overridden' % (slots[0], slots[3]))
    for w in W.WALKERS:
        m = Machine(img)
        m.walker(cfg[w['kind']], state=3, kind=w['kind'])
        m.call(slots[20], {3: OBJ, 4: 0x11, 5: 0})
        c = [x for x in m.calls if x[0] in ('chg', 'chgi')]
        t = w.get('tread', 0)
        check(c == ([('chgi', OBJ, t, (0xFFFF, fn[w['states'][t][1]]), (0xFFFF, fn[w['states'][t][0]]), (0, 0))]
                    if t else []) and len(m.calls) == len(c),
              'VT %s: slot 20 (the 3DS\'s 21, stepped on) %s' % (w['name'], '=> %d (collapses)' % t if t else
                                                                  'does nothing (BehaviorImpl\'s nop, as on the 3DS)'))
    for w in W.WALKERS:
        got = []
        for k in (64, 65, 66, 67):
            m = Machine(img)
            m.walker(cfg[w['kind']])
            m.call(slots[k], {3: OBJ})
            got.append(m.uc.reg_read(R[3]))
        check(tuple(got) == w['rets'], 'VT %s: slots 64-67 (after damage on the ground / in the air / default, '
              'death) = the 3DS\'s %s' % (w['name'], got))
    m = Machine(img)
    m.call(slots[38], {3: OBJ})
    flip = 1 if W.KEEP_FLIP else 0
    check(m.uc.reg_read(R[3]) == flip, 'VT: slot 38 (flip the motion with lr) %d' % flip)

    # fix v3: the twins' slot 38, initialize_after's set_lr, notify_on_remove's type
    res = {}
    for word, orig in W.TWIN_FLIP:
        f = img.u32(word)
        for k in (0x12, 0x0E, 0x1D, 0x57, 0x5A, 0x58):
            m = Machine(img)
            m.w32(OBJ + 8, k)
            m.call(f, {3: OBJ})
            res[(word, k)] = m.uc.reg_read(R[3])
        res[word] = f
    if W.KEEP_FLIP:
        ok = all(res[w] == o for w, o in W.TWIN_FLIP)
    else:
        ok = all(res[w] == fn['twin_flip'] for w, _o in W.TWIN_FLIP)
        ok &= all(res[(w, k)] == (1 if k >= 0x50 else 0) for w, _o in W.TWIN_FLIP for k in (0x12, 0x0E, 0x1D, 0x57,
                                                                                           0x5A, 0x58))
    check(ok, 'fix v3: the twins\' slot 38 (zima / plasmawisp / darios vtables) %s'
          % ('kept (variant)' if W.KEEP_FLIP else '-> 0 for kinds < 0x50, 1 for the Fortress minions'))
    got = {}
    for k in (0x01, 0x12, 0x57, 0x60):
        m = Machine(img)
        m.walker(cfg[1], lr=-1.0, kind=k)
        m.calls = []
        m.call(0x02DB4AC8, {3: OBJ})
        got[k] = [c for c in m.calls if c[0] in ('set_lr', 'flip')]
    ok = all(got[k][-1:] == [('set_lr', OBJ, -1.0, 1, 1)] for k in (0x01, 0x12)) and \
        all(not [c for c in got[k] if c[0] == 'set_lr'] for k in (0x57, 0x60))
    check(ok, 'fix v3: initialize_after calls set_lr(posture lr, 1, 1) for kinds < 0x50 only %s' % got)
    got = {}
    for k, t in ((0x01, 0), (0x12, 0), (0x01, 5), (0x01, 1), (0x57, 0), (0x01, 3)):
        m = Machine(img)
        m.walker(cfg[1], kind=k)
        m.calls = []
        m.call(W.SITE_DEATH, {3: OBJ, 4: t})
        got[(k, t)] = [c[0] for c in m.calls if c[0] in ('defeat_fx', 'vanish_fx')]
    check(got == {(0x01, 0): ['defeat_fx'], (0x12, 0): ['defeat_fx'], (0x01, 5): [], (0x01, 1): [],
                  (0x57, 0): ['vanish_fx'], (0x01, 3): ['defeat_fx']},
          'fix v3: notify_on_remove: a kind < 0x50 removed by its behaviour (type 0) takes the defeat effect path '
          '0x02DB3AB0 (type 3); the minions keep type 0; other types unchanged %s' % got)

    # change_state: the kind's table
    rows = {}
    for w in W.WALKERS:
        r = {}
        for sid, s in w['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        rows[w['name']] = r
        for slot, kind in ((72, 'chg'), (73, 'chgi')):
            ok = True
            for sid in list(range(0, W.nstates(w) + 2)) + [99, -1]:
                m = Machine(img)
                m.walker(cfg[w['kind']])
                m.call(slots[slot], {3: OBJ, 4: sid})
                c = [x for x in m.calls if x[0] in ('chg', 'chgi')]
                eid = sid if sid in r else 1
                en, up = r[eid]
                ok &= c == [(kind, OBJ, eid, (0xFFFF, up), (0xFFFF, en), (0, 0))]
            check(ok, 'change_state %s slot %d -> 0x%08X(this, id, &update, &enter, &exit): states %s, others -> 1'
                  % (w['name'], slot, W.CHG_BASE if slot == 72 else W.CHG_INT, sorted(r)))

    # initialize / start / set_attack_data
    for w in W.WALKERS:
        k, c0 = w['kind'], cfg[w['kind']]
        m = Machine(img)
        m.walker(c0)
        m.call(fn['w_init'], {3: OBJ})
        got = {o: round(m.rf(EN + o), 6) for o in range(0, 0x80, 4) if m.r32(EN + o)}
        exp = {o: round(v, 6) for o, v in w['energy'].items() if v}
        kicks = [x for x in m.calls if x[0] == 'kick']
        check(got == exp and kicks == ([('kick', KIN, 0x20000004)] if w['kick'] else []),
              'initialize %s: kinetic energy %s%s' % (w['name'], {hex(o): v for o, v in got.items()},
                                                      ', vt+0xFC(0x20000004)' if w['kick'] else ''))
        for var in (0, 2):
            m = Machine(img)
            m.walker(c0, lr=-1.0, x=0.0, var=var)
            m.target, m.target_x = 0, 50.0
            m.wf(OBJ + 0x14, 9.0)
            m.w32(W.V(3) + OBJ, 5)
            m.call(fn['w_start'], {3: OBJ})
            seq = [x[0] for x in m.calls]
            chg = [x for x in m.calls if x[0] == 'chg']
            first = w['start'][1] if var <= 1 else w['start'][0]
            check(seq[:1] == ['rhombus'] and 'reverse_lr' in seq and chg and chg[-1][2] == first and
                  m.rf(OBJ + 0x10) == 1.0 and m.rf(OBJ + 0x14) == 0.0 and m.r32(OBJ + W.V(3)) == 0,
                  'start %s (variation %d): set_rhombus, +0x10 = lr, turns to the target behind, change_state(%d)'
                  % (w['name'], var, first))
        atks = {}
        for st, a in w['attacks']:
            atks.setdefault(st, []).append(D[a])
        ok = True
        for sid in range(0, W.nstates(w) + 1):
            m = Machine(img)
            m.walker(c0)
            m.call(fn['w_atk'], {3: OBJ, 4: sid})
            exp = [('atk_clear', ATKM)]
            for e in atks.get(sid, []):
                ent = [img.u32(e + 4 * i) for i in range(42)]
                exp += [('atk_create', OBJ, e), ('atk_set', ATKM, ent[1], ent[2], OBJ + 0x1C)]
            ok &= m.calls == exp
        for st, a in w['attacks']:
            ok &= [img.u32(D[a] + 4 * i) for i in range(42)] == [W.word(v) for v in W.ATTACKS[a]]
        check(ok, 'set_attack_data %s: clear_all; the 3DS vl attacks only in their states %s'
              % (w['name'], {st: a for st, a in w['attacks']}))

    def air(wo, n=3):
        wo.m.vy, wo.m.ground = 1.0, False
        wo.script[wo.i + n] = lambda w2: (setattr(w2.m, 'vy', -1.0), setattr(w2.m, 'ground', True))

    def world(name, state, lr=-1.0, var=0, setup=None):
        w = byname[name]
        m = Machine(img)
        m.walker(cfg[w['kind']], state=state, lr=lr, kind=w['kind'], var=var)
        m.target, m.target_x = 0, 300.0
        if setup:
            setup(m)
        return World(m, w, rows[name], state, cfg[w['kind']])

    def enters(name):
        """each state's enter: (kinetic, attach, (motion index, rate, loop)) as the 3DS's"""
        out = {}
        for sid, (en, _up) in rows[name].items():
            if en == W.ZIMA_REMOVE_ENTER:
                continue
            m = Machine(img)
            m.walker(cfg[byname[name]['kind']], kind=byname[name]['kind'])
            m.call(en, {3: OBJ})
            k = [c[2] for c in m.calls if c[0] == 'kinetic']
            a = [c[2] for c in m.calls if c[0] == 'attach']
            mo = [(c[2], c[4], c[5]) for c in m.calls if c[0] == 'motion']
            out[sid] = (k[0] if k else None, a[0] if a else None, mo[0] if mo else None,
                        'bullet' if [c for c in m.calls if c[0] == 'bullet'] else '')
        return out

    # ---- fix v7: the area tables (area 0 = the tread area) per kind, the slot's for the other kinds
    ZT = HEAP + 0x30000
    for i, (site, _w, dst, base, kreg, shifted) in enumerate(W.AREA_SITES):
        got = {}
        for k in (0x01, 0x0B, 0x13, 0x19, 0x1F, 0x12, 0x5A, 0x30):
            m = Machine(img)
            m.uc.reg_write(R[dst], 0)
            m.run(fn['area_%d' % i], site + 4, {base: ZT - 0x70 + 0x70 * 0 + 0, kreg: k * 4 if shifted else k,
                                                  31: OBJ})
            got[k] = m.uc.reg_read(R[dst])
        m.w32(ZT, 0)
        exp = {k: (D['ar_' + byname_k['name']] if byname_k else 0) for k, byname_k in
               ((k, next((w for w in W.WALKERS if w['kind'] == k), None)) for k in got)}
        exp = {k: (v if v else m.r32(ZT)) for k, v in exp.items()}
        check(got == exp, 'fix v7: area site 0x%08X: a walker kind gets its own table, others the slot\'s +0x70 %s'
              % (site, {hex(k): hex(v) for k, v in got.items()}))
    for w in W.WALKERS:
        t = [img.u32(D['ar_' + w['name']] + 4 * j) for j in range(12)]
        check(t == [W.word(v) for e in w['areas'] for v in e], 'fix v7: %s area table %s (tread area %s)'
              % (w['name'], w['areas'], 'on' if w['areas'][0][0] else 'off, as on the 3DS'))
    # the game's area set-up 0x02D89860 for a Goomba: the tread area from its table (zima's slot: tread off)
    EN_OBJ = HEAP + 0x8000
    for k, want in ((0x01, (0xE, 2, 14.0, 8.0)), (0x5A, (0xE, 0, 12.0, 12.0))):
        m = Machine(img)
        m.uc.mem_write(EN_OBJ, bytes(0x3500))
        m.w32(EN_OBJ + 4, k)
        m.w32(EN_OBJ + 0x30F0, HEAP + 0x200)
        m.w32(W.PARAM_MGR, PM)
        m.w32(PM + 0x60 + 4 * k, HEAP + 0x30100)
        m.w32(HEAP + 0x30100 + 0x70, HEAP + 0x30200)
        for j, v in enumerate((0, 0, 12.0, 12.0, 0.0, 0.0, 1, 3, 8.0, 8.0, 0.0, 0.0)):
            m.uc.mem_write(HEAP + 0x30200 + 4 * j, struct.pack('>f', v) if isinstance(v, float) else
                           struct.pack('>I', v))
        sets = []

        def add_area(uc, addr, size, _u, mm=m, out=sets):
            if addr == 0x02BFEA2C:
                out.append(mm.r32(mm.uc.reg_read(R[4])))
                mm.ret()
        m.uc.hook_add(UC_HOOK_CODE, add_area, begin=0x02BFEA2C, end=0x02BFEA2C)
        m.call(0x02D89860, {3: EN_OBJ})
        e0 = EN_OBJ + 0x348C
        got = (m.uc.mem_read(e0 + 1, 1)[0], m.r32(e0 + 0xC), round(m.rf(e0 + 0x18), 3), round(m.rf(e0 + 0x1C), 3))
        check(sets == [e0] and got == want, 'fix v7: the game\'s area set-up (0x02D89860) for kind 0x%02X: '
              'area 0 (kind, node, size) %s' % (k, got))

    # ---- Kuribo
    I = lambda n, s: W.index(byname[n], s)  # noqa: E731,E741
    got = enters('kuribo')
    exp = {1: (8, 0, (I('kuribo', 'Fall'), 1.0, 1), ''), 2: (0, 1, (I('kuribo', 'Landing'), 1.0, 0), ''),
           3: (0xA, 1, (15, 0.6, 1), ''), 4: (5, 0, (12, 1.0, 1), ''), 5: (0xA, 1, (13, 1.0, 1), ''),
           6: (2, 1, (11, 1.0, 0), ''), 7: (2, 1, (14, 1.0, 0), ''), 8: (0, 1, (0, 1.0, 0), ''),
           9: (None, None, (1, 0.0, 0), 'bullet')}
    check(got == exp, 'kuribo enters (kinetic, ground, (motion, rate, loop)) as the 3DS\'s: %s' % got)
    # walk: the search on its first frame finds a target in front -> notice (no turn); the hop (E+0x20 = -0.4)
    wd = world('kuribo', 3, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, -50.0
    m.wf(EN + 0x20, 9.0)
    wd.run(1)
    s0 = wd.log[0]
    srch = [c for c in s0[4] if c[0] == 'search']
    ok = srch == [('search', 2, OBJ + 0x10, (10.0, 10.0, 100.0, 40.0, 0.0))] and wd.cur == 4 and \
        not [c for c in s0[4] if c[0] == 'reverse_lr'] and round(m.rf(EN + 0x20), 4) == -0.4
    # in the air (rising, then falling), lands (ground on), 30 frames after entering -> run
    m.found = -1
    m.vy, m.ground = 1.0, False
    wd.script[4] = lambda wo: setattr(wo.m, 'vy', -1.0)
    wd.script[8] = lambda wo: setattr(wo.m, 'ground', True)
    wd.run(40)
    st = wd.states()
    att = [i for i, s, _x, _st, c, _e in wd.log if s == 4 and [x for x in c if x[0] == 'attach' and x[2] == 1]]
    run_at = [i for i, s, _x, _st, _c, _e in wd.log if s == 5][:1]
    ok &= st[:3] == [3, 4, 5] and att and att[0] == 8 and run_at == [33]
    check(ok, 'kuribo: walking, search_target(search 0 {2, 100, ...}) on its first frame finds a target ahead -> '
          'notice (=> 4, no turn), the hop back (E+0x20 = -0.4, kinetic 5), ground on when it lands (frame %s), '
          'the run 30 frames after (frame %s) %s' % (att[:1], run_at, st))
    # run: input (lr, 0); every 60 run frames search 1; a target behind -> run turn -> => 5; 110 frames -> brake
    n0 = len(wd.log)
    m.found, m.target_x = 0, 300.0
    wd.run(60)
    st = wd.states(n0)
    srch = [c for e in wd.log[n0:] for c in e[4] if c[0] == 'search']
    turn_i = [e[0] for e in wd.log[n0:] if e[1] == 7][:1]
    revs = [e[0] for e in wd.log[n0:] if [c for c in e[4] if c[0] == 'reverse_lr']]
    ok = st[:3] == [5, 7, 5] and srch and srch[0][1:] == (2, OBJ + 0x10, (0.0, 10.0, 150.0, 60.0, 0.0)) and revs \
        and m.rf(OBJ + 0x10) == 1.0 and wd.log[n0][3] == (-1.0, 0.0)
    check(ok, 'kuribo: running (stick (-1, 0)), search_target(search 1 {2, 60, ...}) finds the target behind -> '
          'run turn 7 (frame %s), reverse_lr at its end (frame %s) => run 5 again %s' % (turn_i, revs[:1], st))
    m.found = -1
    n0 = len(wd.log)
    wd.run(80)
    st = wd.states(n0)
    runs = [e for e in wd.log if e[1] == 5]
    ok = st[-2:] == [6, 3] or st[-3:-1] == [6, 3]
    brk = [e[0] for e in wd.log[n0:] if e[1] == 6][:1]
    check(ok and len(runs) >= 100, 'kuribo: after 110 run frames the brake 6 (frame %s), at its end the walk 3 %s'
          % (brk, st))
    # walk: a wall ahead -> reverse_lr, walk again; a ledge: variation 0 walks on, variation 1 turns
    wd = world('kuribo', 3, lr=1.0)
    m = wd.m
    m.walls = {4}
    wd.run(2)
    ok = bool([c for c in wd.log[0][4] if c[0] == 'reverse_lr']) and \
        [c for c in wd.log[0][4] if c[0] == 'chg'][-1][2] == 3
    m.walls = set()
    wd2 = world('kuribo', 3, lr=1.0, var=0)
    wd2.m.cliff = True
    wd2.run(3)
    wd3 = world('kuribo', 3, lr=1.0, var=1)
    wd3.m.cliff = True
    wd3.run(1)
    ok &= not [c for e in wd2.log for c in e[4] if c[0] == 'reverse_lr'] and \
        bool([c for c in wd3.log[0][4] if c[0] == 'reverse_lr'])
    wd4 = world('kuribo', 3, lr=1.0)
    wd4.m.ground = False
    wd4.run(2)
    ok &= wd4.cur == 1
    check(ok, 'kuribo: a wall ahead -> reverse_lr, walk again; at a ledge variation 0 walks on, variation 1 '
          'turns; off the ground -> fall 1')
    # fall -> landing -> walk
    wd = world('kuribo', 1)
    wd.m.ground = False
    wd.script[3] = lambda wo: setattr(wo.m, 'ground', True)
    wd.run(12)
    check(wd.states()[:3] == [1, 2, 3], 'kuribo: fall 1, on the ground => landing 2, at its end -> walk 3 %s'
          % wd.states())
    # stomp: stepped on while walking => 8 (Collapses, notify_on_death), at its end -> 10; no attack armed in 8
    wd = world('kuribo', 3)
    wd.run(3)
    m = wd.m
    m.calls = []
    m.call(slots[20], {3: OBJ, 4: 0x11})
    en = [c for c in m.calls if c[0] == 'chgi']
    wd.enter(8)
    col = [c[0] for c in m.calls]
    wd.run(8)
    atk = []
    mm = Machine(img)
    mm.walker(cfg[1])
    mm.call(fn['w_atk'], {3: OBJ, 4: 8})
    atk = mm.calls
    check(en and en[0][2] == 8 and 'notify_death' in col and wd.states() == [3, 8, 10] and
          atk == [('atk_clear', ATKM)], 'kuribo: stepped on (slot 20) => collapses 8 (kinetic 0, Collapses, '
          'notify_on_death %s), at its end -> remove 10 %s; no attack in 8' % (col, wd.states()))
    # dead: kinetic flag 8 => remove
    wd = world('kuribo', 9)
    wd.run(2)
    wd.m.w32(FLAGS, 8)
    wd.run(1)
    check(wd.cur == 10, 'kuribo: dead 9 (Damage, bullet()), kinetic flag 8 => remove 10')

    # ---- Shy Guy
    got = enters('heiho')
    exp = {1: (8, 0, (8, 1.0, 1), ''), 2: (0, 1, (9, 1.0, 0), ''), 3: (2, 1, (15, 1.0, 0), ''),
           4: (1, 1, (16, 1.0, 1), ''), 5: (0, 1, (14, 1.0, 0), ''), 6: (5, 0, (16, 1.0, 1), ''),
           7: (5, 0, (12, 1.0, 1), ''), 8: (0, 1, (12, 1.0, 1), ''), 9: (3, 1, (10, 1.0, 1), ''),
           10: (0, 1, (13, 1.0, 0), ''), 12: (2, 1, (11, 1.0, 0), ''), 13: (2, 1, (13, 0.7, 0), ''),
           14: (21, 0, (8, 1.0, 1), ''), 15: (None, None, (3, 0.0, 0), 'bullet')}
    check(got == exp, 'heiho enters (kinetic, ground, (motion, rate, loop)) as the 3DS\'s: %s' % got)
    # walk energy row, kick, the walk timer -> wait (Wait twice) -> walk
    wd = world('heiho', 4, lr=-1.0)
    m = wd.m
    walk_en = {o: round(m.rf(EN + o), 4) for o in (8, 0x10, 0x14, 0x20, 0x24, 0x28, 0x2C)}
    t = m.r32(OBJ + W.V(1))
    wd.run(t + 40)
    st = wd.states()
    ok = walk_en == {8: 0.3, 0x10: 0.3, 0x14: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5} and 60 <= t <= 120
    ok &= st[:3] == [4, 3, 4] or st[:2] == [4, 3]
    waits = [c for e in wd.log for c in e[4] if c[0] == 'motion' and c[2] == 15]
    check(ok and len(waits) == 1, 'heiho: walk (energy %s, kick), %d frames -> wait 3 (Wait, again once), -> walk '
          '4 %s' % (walk_en, t, st))
    # search -> notice (two hops in place) -> hold -> run (the run row) -> brake -> settle -> walk
    wd = world('heiho', 4, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    wd.run(31)
    air(wd)
    wd.run(1)
    ok = wd.cur == 7 and bool([c for e in wd.log for c in e[4] if c[0] == 'reverse_lr'])
    srch = [c for e in wd.log for c in e[4] if c[0] == 'search'][:1]
    ntc = {o: round(m.rf(EN + o), 4) for o in (0x1C, 0x20, 0x24, 0x28, 0x2C)}
    ok &= ntc == {0x1C: 0.0, 0x20: 0.0, 0x24: 2.0, 0x28: 0.0, 0x2C: 2.0}
    m.found = -1
    hops = []
    for _ in range(14):
        wd.frame()
        h = [c for c in wd.log[-1][4] if c[0] == 'kinetic' and c[2] == 5]
        if h:
            air(wd)
        hops += h
    ok &= wd.cur in (8, 9) and len(hops) == 1
    n0 = len(wd.log)
    wd.run(3)
    run_en = {o: round(m.rf(EN + o), 4) for o in (8, 0x10, 0x14, 0x20, 0x24, 0x28, 0x2C)}
    ok &= wd.cur == 9 and 60 <= m.r32(OBJ + W.V(2)) <= 80 and \
        run_en == {8: 0.8, 0x10: 0.8, 0x14: 0.0075, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5}
    check(ok, 'heiho: walking, search_target(search 0) %s finds the target behind: reverse_lr, -> notice 7 '
          '(set_kinetic_jump(0, 2.0): E %s), a second hop on landing, => hold 8, -> run 9 (the run row %s, 80 '
          'frames)' % (srch, ntc, run_en))
    n0 = len(wd.log)
    wd.run(100)
    st = wd.states(n0)
    ok = st[:3] == [9, 12, 14]
    m.w32(FLAGS, 1)
    wd.run(3)
    check(ok and wd.cur == 4, 'heiho: after 80 run frames the brake 12, at its end (stopped) the settle 14 (kinetic '
          '21), kinetic flag 1 -> walk 4 %s' % wd.states(n0))
    # run: a target behind -> run turn 13 => run; a wall -> wall run turn 10 => run
    wd = world('heiho', 9, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    wd.run(40)
    st = wd.states()
    ok = st[:3] == [9, 13, 9]
    m.found = -1
    m.walls = {2, 4}
    n0 = len(wd.log)
    wd.run(2)
    m.walls = set()
    wd.run(10)
    ok &= wd.states(n0)[:3] == [9, 10, 9]
    check(ok, 'heiho: running, the target behind (search 1) -> run turn 13 (RunTurn at 0.7) => run; a wall -> '
          'wall run turn 10 => run %s %s' % (st, wd.states(n0)))
    # walk: a wall -> hop 6; landing on the same height => turn 5 => walk; higher, no wall => landing 2
    for dy, want in ((0.0, [4, 6, 5, 4]), (8.0, [4, 6, 2])):
        wd = world('heiho', 4, lr=1.0)
        m = wd.m
        m.walls = {4}
        wd.run(1)
        m.walls = set()
        air(wd)
        wd.script[wd.i + 2] = lambda wo, dy=dy: wo.m.wf(POSTURE + 0x14, dy)
        wd.run(14)
        check(wd.states()[:len(want)] == want, 'heiho: a wall -> wall hop 6 (kinetic 5, Walk); landed %s => %s %s'
              % ('on the same height' if not dy else '%g higher' % dy, want[2:], wd.states()))

    # ---- Waddle Dee
    got = enters('waddledee')
    exp = {1: (8, 0, (8, 1.0, 1), ''), 2: (8, 0, (11, 1.0, 1), ''), 3: (0, 1, (10, 1.0, 0), ''),
           4: (1, 1, (13, 1.2, 1), ''), 5: (0, 1, (12, 1.0, 0), ''), 6: (5, 0, (9, 1.0, 0), ''),
           7: (None, None, (0, 0.0, 0), 'bullet')}
    check(got == exp, 'waddledee enters as the 3DS\'s (the parasol fall: kinetic 8 with ParasolFall): %s' % got)
    wd = world('waddledee', 4, lr=-1.0)
    m = wd.m
    wd.run(300)
    jumps = [e[0] for e in wd.log if e[1] == 6]
    stamp = [e[0] for e in wd.log if e[1] == 4]
    ok = not [c for e in wd.log for c in e[4] if c[0] == 'search']
    ok &= all(not [c for c in e[4] if c[0] in ('atk_create',)] for e in wd.log)
    check(ok and len(stamp) > 250, 'waddledee: walks (no search: it never chases)%s' %
          (', jumps on frames %s' % jumps[:3] if jumps else ''))
    for var, want in ((0, [4, 6, 2]), (2, [4, 6, 1])):
        wd = world('waddledee', 4, lr=-1.0, var=var)
        m = wd.m
        m.walls = {2}
        jumped = False
        for _ in range(40):
            wd.frame()
            if wd.cur == 6 and not jumped:
                jumped = True
                m.walls = set()
                m.vy, m.ground = 1.0, False
                wd.script[wd.i + 2] = lambda wo: setattr(wo.m, 'vy', -1.0)
                wd.script[wd.i + 4] = lambda wo: setattr(wo.m, 'ground', True)
            if wd.cur == 5:
                m.walls = set()
        st = wd.states()
        ok = st[:3] == want or (st[:2] == [4, 5] and 4 in st[2:])
        check(ok, 'waddledee (variation %d): a wall -> 50 %% jump 6 (else turn 5); from the apex %s; lands 3 -> 4 %s'
              % (var, 'the parasol fall 2' if var <= 1 else 'the fall 1', st))
    wd = world('waddledee', 4, lr=-1.0, var=0)
    wd.m.ground = False
    wd.run(1)
    wd3 = world('waddledee', 4, lr=-1.0, var=2)
    wd3.m.ground = False
    wd3.run(1)
    check(wd.pending == 2 and wd3.pending == 1, 'waddledee: off the ground -> 2 (variations 0 / 1) / 1')

    # ---- Waddle Doo
    got = enters('waddledoo')
    exp = {1: (8, 0, (10, 1.0, 1), ''), 2: (0, 1, (12, 1.0, 0), ''), 3: (1, 1, (14, 1.0, 1), ''),
           4: (0, 1, (13, 1.0, 0), ''), 5: (5, 0, (11, 1.0, 0), ''), 10: (None, None, (2, 0.0, 0), 'bullet')}
    check(got == exp, 'waddledoo enters as the 3DS\'s: %s' % got)
    wd = world('waddledoo', 3, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    wd.run(70)
    st = wd.states()
    srch = [c for e in wd.log for c in e[4] if c[0] == 'search'][:1]
    ok = st[:3] == [3, 4, 3] and srch == [('search', 2, OBJ + 0x10, (0.0, 0.0, 200.0, 200.0, 0.0))]
    check(ok, 'waddledoo: walks, every 60 frames search_target(search 0) finds the target behind -> turn 4 => walk '
          '%s' % st)
    wd = world('waddledoo', 3, lr=1.0)
    m = wd.m
    m.walls = {4}
    wd.run(1)
    m.walls = set()
    air(wd)
    wd.run(14)
    check(wd.states()[:4] == [3, 5, 4, 3], 'waddledoo: a wall -> jump 5; landed on the same height => turn 4 => '
          'walk %s' % wd.states())

    # ---- Churine
    got = enters('churine')
    exp = {1: (8, 0, (12, 1.0, 1), ''), 2: (0, 1, (8, 1.0, 0), ''), 3: (1, 1, (11, 1.0, 1), ''),
           4: (5, 0, (7, 1.0, 1), ''), 5: (0, 1, (10, 1.0, 0), ''), 8: (None, None, (2, 0.0, 0), 'bullet')}
    check(got == exp, 'churine enters as the 3DS\'s: %s' % got)
    wd = world('churine', 3, lr=1.0)
    m = wd.m
    m.target = -1
    m.walls = {4}
    wd.run(1)
    m.walls = set()
    air(wd)
    wd.script[wd.i + 2] = lambda wo: wo.m.wf(POSTURE + 0x14, 30.0)
    wd.run(14)
    st = wd.states()
    m.cliff = True
    n0 = len(wd.log)
    wd.run(2)
    check(st[:4] == [3, 4, 2, 3] and wd.states(n0)[:2] == [3, 5], 'churine: a wall -> jump 4 (initialize first); '
          'landed 30 higher, no wall => landing 2 (no look back) -> walk 3; a ledge -> turn 5 %s %s'
          % (st, wd.states(n0)))
    # no kind searches for a contact attack in its walk: set_attack_data is per state (above)

    # T2 / S2
    t1 = [img.u32(W.MOTION_SETS + 4 * k) for k in range(0x61)]
    sets2a = E.build_sets(img)
    for stage in (0x94, 0x10):
        m = Machine(img)
        m.stage(stage)
        m.w32(MGR + 0x5EC, 2)
        m.run(E.SITE_T, W.SITE_T + 8, {31: MGR, 0: 0})
        got = [m.r32(W.MOTION_SETS + 4 * k) for k in range(0x61)]
        exp = list(t1)
        if stage == 0x94:
            for name, k, _t, _c in E.PAIRS:
                exp[k] = sets2a[name][0]
            for w in W.WALKERS:
                exp[w['kind']] = D['set_' + w['name']]
        ok = got == exp and m.uc.reg_read(R[0]) == 2 and m.uc.reg_read(UC_PPC_REG_PC) == W.SITE_T + 8
        if stage == 0x94:
            r = []
            for k in W.KINDS:
                m.uc.reg_write(UC_PPC_REG_LR, DONE)
                m.run(0x02DC6D68, DONE, {3: k})
                r.append(m.uc.reg_read(R[3]))
            ok &= r == [D['set_' + w['name']] for w in W.WALKERS]
        check(ok, 'T2 (stage 0x%X): %s' % (stage, 'the walkers\' sets (2a\'s four kept), get_motion_data_set returns '
                                            'them' if stage == 0x94 else 'the table unchanged'))
    for stage, pm in ((0x94, PM), (0x10, PM), (0x94, 0)):
        m = Machine(img)
        m.stage(stage)
        m.w32(E.PARAM_MGR, pm)
        m.uc.mem_write(PM + W.SLOTS, struct.pack('>97I', *[0x50000000 + i for i in range(0x61)]))
        m.w32(MGR + 0x5EC, 2)
        before = [m.r32(PM + W.SLOTS + 4 * k) for k in range(0x61)]
        m.run(E.SITE_S, W.SITE_S + 4, {3: 0x10AB0000, 28: MGR, 31: 7})
        after = [m.r32(PM + W.SLOTS + 4 * k) for k in range(0x61)]
        exp = list(before)
        if stage == 0x94 and pm:
            for _n, k, twin, _c in E.PAIRS:
                exp[k] = before[twin]
            for k in W.KINDS:
                exp[k] = before[W.SLOT_DONOR]
        check(after == exp and m.uc.reg_read(R[3]) == 0x1234 and m.uc.reg_read(R[0]) == 2 and
              m.uc.reg_read(R[1]) == STACK and m.uc.reg_read(R[28]) == MGR,
              'S2 (stage 0x%X%s): %s' % (stage, '' if pm else ', no param manager',
                                         'slot[K] = slot[0x5A] for the walkers (2a\'s kept), r3 = the load\'s'
                                         if stage == 0x94 and pm else 'no slot changed'))

    # the sets
    pac_stems = {}
    if root:
        import omo
        for w in W.WALKERS:
            pac = os.path.join(root, 'motion', 'enemy', w['name'], 'body', 'main.pac')
            pac_stems[w['name']] = [n[:-4] for n, _d in omo.pac_read(pac) if n.endswith('.omo')]
    for w in W.WALKERS:
        n, s = w['name'], D['set_' + w['name']]
        ms = w['motions']
        head = [img.u32(s + 4 * i) for i in range(6)]
        ents = [(img.u32(s + 0x18 + 8 * i), img.u32(s + 0x1C + 8 * i)) for i in range(len(ms))]
        ok = head == [s + 0x18, len(ms), 0, 0, 0, 0] and ents == [(zlib.crc32(W.stem(n, sfx).encode(), 0xFFFFFFFF), f)
                                                                 for sfx, f in ms]
        hs = D.get('hs_' + n)
        if hs:
            ok &= [img.u32(hs + 4 * i) for i in range(3 * len(ms))] == \
                [zlib.crc32((sfx.lower() + x).encode()) for sfx, _f in ms for x in ('.init', '', '.exit')]
        check(ok, 'set %s (0x%08X): %d entries, K\'s 3DS order, crc32(stem, 0xFFFFFFFF), flags%s'
              % (n, s, len(ms), '; hashsets 0x%08X' % hs if hs else '; no hashsets (none on the 3DS)'))
        if root:
            have = {zlib.crc32(x.encode(), 0xFFFFFFFF) for x in pac_stems[n]}
            missing = [W.stem(n, sfx) for (sfx, _f), (h, _f2) in zip(ms, ents) if h not in have]
            check(not missing, 'set %s: every entry is an OMO of %s/body/main.pac (%d) %s'
                  % (n, n, len(pac_stems[n]), missing))
            hashes = {img.u32(hs + 4 * i) for i in range(3 * len(ms))} if hs else set()
            for f in ('attack', 'effect', 'sound'):
                p = os.path.join(root, 'animcmd', 'enemy', n, f + '.bin')
                if os.path.exists(p):
                    dd = open(p, 'rb').read()
                    cnt = struct.unpack('>I', dd[8:12])[0]
                    scr = [struct.unpack('>I', dd[0x10 + 8 * i:0x14 + 8 * i])[0] for i in range(cnt)]
                    out = [hex(h) for h in scr if h not in hashes]
                    check(not out, 'set %s: %s.bin\'s %d scripts are in its hashsets %s' % (n, f, cnt, out))
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
