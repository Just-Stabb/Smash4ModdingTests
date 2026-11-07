#!/usr/bin/env python3
"""Unicorn test of tools/smashrun_walker_cave.py in a patched cross_f.rpx:

  python3 tools/smashrun_walker_test.py [--keep-flip] PATCHED.rpx [ENEMY_ROOT]

ENEMY_ROOT (optional): the installed converted enemies (motion/enemy/<name>/body/main.pac, animcmd/enemy/<name>/):
then every set entry must be an OMO of K's pac and every script of K's animcmd files a hash of K's script hashsets.

Runs the cave's code and the game's around it, the framework's calls stubbed (modules are fake objects):
- the hook words, and 0x04B86800-0x04B88000 holding only the cave's code and data (zeros after);
- the factory 0x02DB94CC: each walker kind -> operator new(OBJ_SIZE), the Behavior ctor (obj, acc, K, variation),
  module+8 = obj with vptr VT, +0xE4.. BehaviorImpl's init (0 but +0xE8/+0xEC common_state_func, +0x120 1,
  +0x15C -1), +0x168 its CFG, +0xA8 its hashsets (or 0), +0xB0..+0xD0 its nine damage labels; 2a's kinds and the
  twins / bosses still call their own create, other kinds none;
- the vtable: BehaviorImpl's slots but the overrides; change_state (72 / 73 -> 0x026A3A44 / 0x026A3AD4 with the
  state's {update, enter, exit} PMFs; unknown ids -> FALL);
- each state's enter: change_kinetic / set_attach_ground / change_motion_state with the kind's indices, rate, loop;
  bullet() in DEAD;
- initialize: the kind's kinetic energy words, the kinetic vt+0xFC(0x20000004) for Kuribo / Shy Guy only;
  start: set_rhombus, +0x10 = posture lr, faces a target behind (reverse_lr(1, 1)), change_state(FALL);
  set_attack_data: clear_all, then in WALK / TURN the kind's contact attack (create_attack_data, set_attack);
- a walk in a small world (real check_wall; check_turn_to_target as the game's, ground, cliff stubbed): it
  walks (AI stick = lr), turns to a target behind it (TURN, the Turn motion, reverse_lr at its end, WALK), walks
  to it, turns at a wall and at a ledge, falls off the ground and lands (FALL, LANDING, WALK);
- T2 / S2: on a Smash Run stage the motion data set table points the walker kinds at their sets (2a's four still
  at theirs), get_motion_data_set returns them, and their param slots = mczakozima's; off them nothing changes;
- the sets: K's 3DS order, crc32(stem, 0xFFFFFFFF), flags; the hashsets crc32(name(.init / .exit));
- fix v3: the walker's slot 38 and the twins' (zima / plasmawisp / darios vtable words) return 0 for kinds < 0x50
  (1 for the minions; --keep-flip: unchanged); initialize_after 0x02DB4AC8 calls set_lr(posture lr, 1, 1) for kinds
  < 0x50; notify_on_remove 0x02DB40E4 sends a kind < 0x50's type 0 to the defeat path 0x02DB3AB0.
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
KVT, ARRP, ARR, EN, INPUT, PM, MGR = (HEAP + 0x21000 + 0x100 * i for i in range(7))
KICK = 0x02000004               # the kinetic vt+0xFC target (a stub address)
DONE = 0x02000000               # return address of a run
CREATES = {0x50: 0x02DD0438, 0x51: 0x02DC7414, 0x52: 0x026B7344, 0x53: 0x026C2E9C, 0x54: 0x026BE944,
           0x55: 0x026BB3E8, 0x56: 0x026C5F80, 0x57: 0x026CF4DC, 0x58: 0x026CBA64, 0x59: 0x026D1DFC,
           0x5A: 0x026D6834, 0x5B: 0x02DDB82C, 0x5E: 0x026E24EC, 0x5F: 0x026D80A0, 0x60: 0x026DB864}
GET_TARGET_POS = 0x026A690C
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
                uc.mem_write(base, data)
        uc.mem_map(HEAP, 0x40000)
        uc.mem_map(STACK - 0x10000, 0x20000)
        uc.mem_write(DONE, struct.pack('>II', 0x48000000, 0x48000000))      # b . (stop addresses)
        self.calls = []
        self.ground, self.walls, self.cliff, self.motion_end = True, set(), False, False
        self.target, self.target_x = 0, 0.0
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
        elif addr == W.CHANGE_MOTION:
            c.append(('motion', r(3), r(4), round(self.fr(1), 4), round(self.fr(2), 4), r(5), round(self.fr(3), 4)))
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
        elif addr == GET_TARGET_POS:
            c.append(('target_pos', r(5)))
            self.wf(r(3), self.target_x)
            self.wf(r(3) + 4, 0.0)
            self.wf(r(3) + 8, 0.0)
            self.ret()
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

    def walker(self, cfg, state=0, lr=-1.0, x=0.0):
        """a walker object (as create leaves it) with the fake modules"""
        self.uc.mem_write(OBJ, bytes(W.OBJ_SIZE))
        self.w32(OBJ, ACC)
        self.w32(OBJ + 4, state)
        self.w32(OBJ + 0x168, cfg)
        self.w32(OBJ + 0xE0, self.vt)
        self.wf(OBJ + 0x10, lr)
        self.wf(POSTURE + 0x10, x)
        self.wf(POSTURE + 0x60, lr)


def main():
    if '--keep-flip' in sys.argv:            # the variant built with smashrun_walker_cave.py --keep-flip
        sys.argv.remove('--keep-flip')
        W.KEEP_FLIP = True
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    vt_words = W.read_vt(img)
    a, words, d = W.assemble(vt_words)
    D = d.addr
    VT_ADDR[0] = D['vt']
    cfg = {w['kind']: D['cfg_' + w['name']] for w in W.WALKERS}
    fn = {k: a.addr(k) for k in a.labels}

    # hooks and space
    check(img.u32(W.SITE_F) == W.branch(W.SITE_F, fn['cave_f']) and
          img.u32(W.SITE_T) == W.branch(W.SITE_T, fn['cave_t']) and
          img.u32(W.SITE_S) == W.branch(W.SITE_S, fn['cave_s']), 'hooks: F2 / T2 / S2 branch to the cave')
    want = {W.CAVE + 4 * i: x for i, x in enumerate(words)}
    want.update({d.base + 4 * i: x for i, x in enumerate(d.words)})
    bad = [hex(x) for x in range(W.CAVE, W.LIMIT, 4) if img.u32(x) != want.get(x, 0)]
    check(not bad, 'space 0x%08X-0x%08X: the code (to 0x%08X), its data (0x%08X-0x%08X), zeros after %s'
          % (W.CAVE, W.LIMIT, W.CAVE + 4 * len(words), d.base, d.base + 4 * len(d.words), bad[:4]))
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
    over = {12: W.ZIMA_CAPTURE_MOTION, 38: W.ZIMA_ONE if W.KEEP_FLIP else fn['w_noflip'], 40: fn['w_init'], 41: fn['w_start'], 45: fn['w_atk'],
            64: 0x026D7CA0, 65: 0x026D7CA8, 66: 0x026D7CB0, 67: 0x026D7CB8, 72: fn['w_chg'], 73: fn['w_chgi'],
            74: fn['w_chg'], 75: fn['w_chgi']}
    ok = vt[:3] == vt_words[:3] and all(slots[k] == over.get(k, bi.get(k)) for k in range(76))
    ok &= all(vt[(0x8 + 8 * k) // 4] == 0 for k in range(76))
    check(ok, 'VT: BehaviorImpl\'s 74 slots (dtor 0x%08X, update 0x%08X kept) with 12 38 40 41 45 64-67 72-75 '
          'overridden' % (slots[0], slots[3]))
    zima_ret = {}
    for k in (64, 65, 66, 67):
        m = Machine(img)
        m.call(slots[k], {3: OBJ})
        zima_ret[k] = m.uc.reg_read(R[3])
    m = Machine(img)
    m.call(slots[38], {3: OBJ})
    flip = 1 if W.KEEP_FLIP else 0
    check(zima_ret == {64: W.ST_WALK, 65: W.ST_FALL, 66: W.ST_FALL, 67: W.ST_DEAD} and m.uc.reg_read(R[3]) == flip,
          'VT: after damage on the ground WALK, in the air / default FALL, death DEAD; slot 38 (flip the motion '
          'with lr) %d' % flip)

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
        m.walker(cfg[1], lr=-1.0)
        m.w32(OBJ + 8, k)
        m.calls = []
        m.call(0x02DB4AC8, {3: OBJ})
        got[k] = [c for c in m.calls if c[0] in ('set_lr', 'flip')]
    flip_call = [] if not W.KEEP_FLIP else None
    ok = all(got[k][-1:] == [('set_lr', OBJ, -1.0, 1, 1)] for k in (0x01, 0x12)) and \
        all(not [c for c in got[k] if c[0] == 'set_lr'] for k in (0x57, 0x60))
    check(ok, 'fix v3: initialize_after calls set_lr(posture lr, 1, 1) for kinds < 0x50 only %s' % got)
    del flip_call
    got = {}
    for k, t in ((0x01, 0), (0x12, 0), (0x01, 5), (0x01, 1), (0x57, 0), (0x01, 3)):
        m = Machine(img)
        m.walker(cfg[1])
        m.w32(OBJ + 8, k)
        m.calls = []
        m.call(W.SITE_DEATH, {3: OBJ, 4: t})
        got[(k, t)] = [c[0] for c in m.calls if c[0] in ('defeat_fx', 'vanish_fx')]
    check(got == {(0x01, 0): ['defeat_fx'], (0x12, 0): ['defeat_fx'], (0x01, 5): [], (0x01, 1): [],
                  (0x57, 0): ['vanish_fx'], (0x01, 3): ['defeat_fx']},
          'fix v3: notify_on_remove: a kind < 0x50 removed by its behaviour (type 0) takes the defeat effect path '
          '0x02DB3AB0 (type 3); the minions keep type 0; other types unchanged %s' % got)

    # change_state
    st = {W.ST_FALL: (fn['fall_enter'], fn['fall_update']), W.ST_LANDING: (fn['land_enter'], fn['land_update']),
          W.ST_WALK: (fn['walk_enter'], fn['walk_update']), W.ST_TURN: (fn['turn_enter'], fn['turn_update']),
          W.ST_DEAD: (fn['dead_enter'], W.ZIMA_DEAD_UPDATE), W.ST_REMOVE: (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)}
    for slot, kind in ((72, 'chg'), (73, 'chgi')):
        got = {}
        for sid in (1, 2, 3, 4, 6, 7, 0, 5, 8, 99, -1):
            m = Machine(img)
            m.walker(cfg[1])
            m.call(slots[slot], {3: OBJ, 4: sid})
            c = [x for x in m.calls if x[0] in ('chg', 'chgi')]
            got[sid] = c
        ok = True
        for sid, c in got.items():
            eid = sid if sid in st else W.ST_FALL
            en, up = st[eid]
            ok &= c == [(kind, OBJ, eid, (0xFFFF, up), (0xFFFF, en), (0, 0))]
        check(ok, 'change_state slot %d -> 0x%08X(this, id, &update, &enter, &exit) for 1 2 3 4 6 7; 0 5 8 99 -1 -> '
              'FALL' % (slot, W.CHG_BASE if slot == 72 else W.CHG_INT))

    # enters
    for w in W.WALKERS:
        k, c0 = w['kind'], cfg[w['kind']]
        idx = lambda s: W.index(w, s)  # noqa: E731
        res = {}
        for name in ('fall_enter', 'land_enter', 'walk_enter', 'turn_enter', 'dead_enter'):
            m = Machine(img)
            m.walker(c0)
            m.w32(OBJ + 0x16C, 77)
            m.call(fn[name], {3: OBJ})
            res[name] = [x[2:] if x[0] in ('kinetic', 'attach') else x[1:] for x in m.calls]
            if name == 'walk_enter':
                res['counter'] = m.r32(OBJ + 0x16C)
        rate = round(w['walk_rate'], 4)
        exp = {'fall_enter': [(8,), (0,), (OBJ, idx(w['fall']), 0.0, 1.0, 1, 0.0)],
               'land_enter': [(0,), (1,), (OBJ, idx(w['landing']), 0.0, 1.0, 0, 0.0)],
               'walk_enter': [(w['walk_kinetic'],), (1,), (OBJ, idx(w['walk']), 0.0, rate, 1, 0.0)],
               'turn_enter': [(0,), (1,), (OBJ, idx(w['turn']), 0.0, 1.0, 0, 0.0)],
               'dead_enter': [(OBJ, idx(w['dead']), 0.0, 0.0, 0, 0.0), (OBJ,)], 'counter': 0}
        check(res == exp, 'enters %s: FALL %s, LANDING %s, WALK %s (kinetic 0x%X, rate %s), TURN %s, DEAD %s + bullet'
              % (w['name'], w['fall'], w['landing'], w['walk'], w['walk_kinetic'], w['walk_rate'], w['turn'],
                 w['dead']))
    # a turn with no Turn motion (none of the five; the code path): reverse at once
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
        m = Machine(img)
        m.walker(c0, lr=-1.0, x=0.0)
        m.target, m.target_x = 0, 50.0
        m.wf(OBJ + 0x14, 9.0)
        m.call(fn['w_start'], {3: OBJ})
        seq = [x[0] for x in m.calls]
        chg = [x for x in m.calls if x[0] == 'chg']
        check(seq[:1] == ['rhombus'] and 'reverse_lr' in seq and chg and chg[-1][2] == W.ST_FALL and
              m.rf(OBJ + 0x10) == 1.0 and m.rf(OBJ + 0x14) == 0.0 and m.r32(OBJ + 0x16C) == 0,
              'start %s: set_rhombus, +0x10 = lr, turns to the target behind, change_state(FALL) %s' % (w['name'], seq))
        atk = d.addr['kuribo_bump'] if w['attack'] is W.KURIBO_BUMP else d.addr['heiho_bump']
        res = {}
        for sid in (W.ST_WALK, W.ST_TURN, W.ST_FALL, W.ST_LANDING, W.ST_DEAD):
            m = Machine(img)
            m.walker(c0)
            m.call(fn['w_atk'], {3: OBJ, 4: sid})
            res[sid] = (m.calls, m.r32(OBJ + 0x84), m.r32(OBJ + 0x88))
        e = [img.u32(atk + 4 * i) for i in range(42)]
        on = [('atk_clear', ATKM), ('atk_create', OBJ, atk), ('atk_set', ATKM, e[1], e[2], OBJ + 0x1C)]
        ok = all(res[s] == (on, e[1], e[2]) for s in (W.ST_WALK, W.ST_TURN))
        ok &= all(res[s][0] == [('atk_clear', ATKM)] for s in (W.ST_FALL, W.ST_LANDING, W.ST_DEAD))
        ok &= e == [(struct.unpack('>I', struct.pack('>f', v))[0] if isinstance(v, float) else v & 0xFFFFFFFF)
                    for v in w['attack']]
        check(ok, 'set_attack_data %s: clear_all; in WALK / TURN its contact attack (%s, node %d, power %d, angle %d)'
              % (w['name'], 'own' if w['attack'] is not W.HEIHO_BUMP or k == 0x0B else 'Shy Guy\'s',
                 w['attack'][3], w['attack'][4], w['attack'][5]))

    # a walk in a small world (Kuribo and Waddle Dee)
    for w in (W.WALKERS[0], W.WALKERS[2]):
        m = Machine(img)
        m.walker(cfg[w['kind']], state=W.ST_WALK, lr=-1.0, x=0.0)
        m.target, m.target_x = 0, 300.0
        log = []
        cur, pending = W.ST_WALK, None
        m.call(st[W.ST_WALK][0], {3: OBJ})
        turn_frames = 0
        script = {}            # frame -> world change

        def frame(i):
            nonlocal cur, pending, turn_frames
            if i in script:
                script[i](m)
            m.calls = []
            if pending is not None:
                m.call(st[pending][0], {3: OBJ})
                cur, pending = pending, None
            m.motion_end = cur in (W.ST_TURN, W.ST_LANDING) and turn_frames >= 5     # the one-shot motions end
            turn_frames = turn_frames + 1 if cur in (W.ST_TURN, W.ST_LANDING) else 0
            m.uc.mem_write(INPUT, struct.pack('>ff', 7.0, 7.0))
            m.call(st[cur][1], {3: OBJ, 4: INPUT})
            stick = struct.unpack('>ff', m.uc.mem_read(INPUT, 8))
            x = m.rf(POSTURE + 0x10) + 2.0 * stick[0]
            m.wf(POSTURE + 0x10, x)
            ch = [c for c in m.calls if c[0] == 'chg']
            if ch:
                pending = ch[-1][2]
            log.append((i, cur, round(x, 1), stick, [c[0] for c in m.calls if c[0] in ('reverse_lr', 'chg')]))

        for i in range(0, 60):
            frame(i)
        states = [s for _i, s, _x, _st, _c in log]
        xs = [x for _i, _s, x, _st, _c in log]
        first_turn = states.index(W.ST_TURN) if W.ST_TURN in states else -1
        walk_after = states.index(W.ST_WALK, first_turn) if first_turn >= 0 else -1
        revs = [i for i, _s, _x, _st, c in log if 'reverse_lr' in c]
        check(log[0][3] == (-1.0, 0.0) and xs[5] < 0 and 0 < first_turn <= W.TARGET_INTERVAL + 1 and
              revs and revs[0] > first_turn and walk_after > revs[0] and log[walk_after][3] == (1.0, 0.0) and
              xs[-1] > xs[walk_after] and all(st == (0.0, 0.0) for _i, s, _x, st, _c in log if s == W.ST_TURN),
              '%s walks left (stick %s), turns to the target behind it on frame %d (TURN, reverse_lr at the '
              'motion\'s end, frame %s), walks right to it (x %s -> %s)' % (w['name'], log[0][3], first_turn,
                                                                            revs[:1], xs[walk_after], xs[-1]))
        # a wall ahead (right), then a ledge, then no ground
        m.target = -1
        n0 = len(log)
        script[60] = lambda mm: mm.walls.add(4)
        script[62] = lambda mm: mm.walls.clear()
        for i in range(60, 90):
            frame(i)
        s2 = [s for _i, s, _x, _st, _c in log[n0:]]
        wall_turn = s2.index(W.ST_TURN) if W.ST_TURN in s2 else -1
        st_after = [st for _i, s, _x, st, _c in log[n0 + wall_turn:] if s == W.ST_WALK][:1]
        check(wall_turn in (1, 2) and st_after == [(-1.0, 0.0)], '%s turns at a wall ahead (TURN on frame +%d), '
              'walks away %s' % (w['name'], wall_turn, st_after))
        n0 = len(log)
        script[90] = lambda mm: setattr(mm, 'cliff', True)
        script[91] = lambda mm: setattr(mm, 'cliff', False)
        for i in range(90, 120):
            frame(i)
        s3 = [s for _i, s, _x, _st, _c in log[n0:]]
        cliffs = [c for c in m.calls if c[0] == 'cliff']
        st_after = [st for _i, s, _x, st, _c in log[n0 + 2:] if s == W.ST_WALK][:1]
        check(W.ST_TURN in s3[:3] and st_after == [(1.0, 0.0)], '%s turns at a ledge ahead (check_cliff_lr with '
              'the posture lr), walks away %s' % (w['name'], st_after))
        del cliffs
        n0 = len(log)
        script[120] = lambda mm: setattr(mm, 'ground', False)
        script[125] = lambda mm: setattr(mm, 'ground', True)
        for i in range(120, 135):
            frame(i)
        s4 = [s for _i, s, _x, _st, _c in log[n0:]]
        seen = [s for j, s in enumerate(s4) if j == 0 or s != s4[j - 1]]
        check(seen[:4] == [W.ST_WALK, W.ST_FALL, W.ST_LANDING, W.ST_WALK] or
              (W.index(w, w['landing']) < 0 and seen[:3] == [W.ST_WALK, W.ST_FALL, W.ST_WALK]),
              '%s falls off the ground and lands: %s' % (w['name'], seen))

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
