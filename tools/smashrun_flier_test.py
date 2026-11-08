#!/usr/bin/env python3
"""Unicorn test of step 2e's fliers (tools/smashrun_walker_cave.py, region G and the FLIERS kinds) in a patched
cross_f.rpx:

  python3 tools/smashrun_flier_test.py PATCHED.rpx

Runs the cave's code with the framework's calls stubbed (tools/smashrun_walker_test.py's Machine and World, plus
the aerial module, the ground normal, the hit stun factor, sqrtf, BehaviorImpl's notify_on_damage):
- the text region (RPL file info) and region G's words; the factory: new(FL_SIZE), vptr VTF, the CFG;
- VTF: the walkers' vtable but slots 10 / 27 / 41 / 69 (dispatch to the kind's CFG handlers, else BehaviorImpl's);
- per kind: slots 64-67, change_state over its 3DS table, set_attack_data (the vl P2 entries in their states only,
  the entries' words = the 3DS vl's), start, each state's enter / update (the 3DS sequences of docs/smash-run-port.md
  "Step 2e"), the damage / stun / leave / death paths.
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_walker_test as T  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_enemy_cave as E  # noqa: E402
from smashrun_walker_test import R, OBJ, ACC, EN, FLAGS, POSTURE, GROUND, check  # noqa: E402

HEAP = T.HEAP
FEN0, FEN1 = HEAP + 0x24000, HEAP + 0x24100     # the aerial module's energies (fake)
PMGR, GLTAB = HEAP + 0x25000, HEAP + 0x26000      # the param manager, the gl entries
ORIG27 = ORIG4 = None
MODEL, EFFM, DIRTY = HEAP + 0x24400, HEAP + 0x24600, 0x02000020     # fake ModelModule / EffectModule, vt+0xC4 stub
EINIT, FVT = 0x02000010, HEAP + 0x24200      # the aerial energy's init (vt+0x1C), its fake vtable


class Machine(T.Machine):
    def __init__(self, img):
        T.Machine.__init__(self, img)
        self.touch_any, self.normal, self.factor = False, (0.0, 1.0), 1.0
        self.target_y, self.center, self.handle = 0.0, (0.0, 0.0, 0.0), 0x7776
        self.w32(ACC + 0x3118, MODEL)
        self.w32(MODEL, MODEL + 0x40)
        self.w32(MODEL + 0x40 + W.MODEL_NODE_DIRTY, DIRTY)
        self.w32(ACC + 0x30D8, EFFM)
        self.w32(W.PARAM_MGR, PMGR)
        self.w32(PMGR + W.GL_BASE, GLTAB)
        self.w32(PMGR + W.GL_INDEX + 4 * (8 * 0x11), 2)          # ghos, variation 0 -> gl entry 2
        self.w32(GLTAB + 2 * 0x228 + 0x154, 30)

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        c = self.calls
        if addr == W.AER_CTOR:
            c.append(('aer_ctor', r(3), r(4)))
            self.w32(r(3), r(4))
            self.w32(r(3) + 4, FEN0)
            self.w32(r(3) + 8, FEN1)
            self.w32(r(3) + 0xC, 0xFFFFFFFF)
            self.ret()
        elif addr == EINIT:
            c.append(('einit', r(3), r(4), round(self.rf(r(5)), 4), round(self.rf(r(5) + 4), 4), r(7),
                      self.r32(OBJ + W.AER + 0xC)))
            self.ret()
        elif addr == W.AER_UPDATE:
            c.append(('aer_update', r(3)))
            self.ret()
        elif addr in (W.AER_SLIP_HOMING, W.AER_SLIP_HOMING_EXT):
            c.append(('slip_homing' if addr == W.AER_SLIP_HOMING else 'slip_homing_ext', r(3),
                      tuple(round(self.fr(i), 4) for i in range(1, 7))))
            self.ret()
        elif addr == W.AER_SET_SPEED:
            c.append(('set_speed', r(3), round(self.rf(r(4)), 4), round(self.rf(r(4) + 4), 4)))
            self.ret()
        elif addr == W.GROUND_NORMAL:
            c.append(('normal', r(3), r(4)))
            self.ret(struct.unpack('>I', struct.pack('>f', self.normal[0]))[0])
            self.uc.reg_write(R[4], struct.unpack('>I', struct.pack('>f', self.normal[1]))[0])
        elif addr == W.IS_TOUCH and r(4) == 0xFF:
            c.append(('touch', r(3), r(4)))
            self.ret(int(self.touch_any))
        elif addr == W.SET_PASSABLE:
            c.append(('passable', r(3), r(4)))
            self.ret()
        elif addr == W.SQRTF:
            self.uc.reg_write(T.FR[1], struct.unpack('>Q', struct.pack('>d', math.sqrt(self.fr(1))))[0])
            self.ret()
        elif addr == W.HIT_FACTOR:
            c.append(('hit_factor', r(3)))
            self.uc.reg_write(T.FR[1], struct.unpack('>Q', struct.pack('>d', self.factor))[0])
            self.ret()
        elif addr == W.BI_NOTIFY_DMG:
            c.append(('bi_damage', r(3)))
            self.ret()
        elif addr == W.GET_TARGET_POS:
            c.append(('target_pos', r(5)))
            for i, v in enumerate((self.target_x, self.target_y, 0.0)):
                self.wf(r(3) + 4 * i, v)
            self.ret()
        elif addr == W.CENTER_POS:
            c.append(('center_pos', r(4)))
            for i, v in enumerate(self.center):
                self.wf(r(3) + 4 * i, v)
            self.ret()
        elif addr in (W.SET_NODE_ROT, W.SET_NODE_TRANS):
            c.append(('node_rot' if addr == W.SET_NODE_ROT else 'node_trans', r(3), r(4),
                      tuple(round(self.rf(r(5) + 4 * i), 4) for i in range(3)), r(6),
                      r(7) if addr == W.SET_NODE_TRANS else None))
            self.ret(1)
        elif addr == DIRTY:
            c.append(('dirty', r(3)))
            self.ret()
        elif addr in (W.ATK_SET_OFFSET, W.EFF_SET_POS, W.EFF_SET_SCALE):
            c.append(({W.ATK_SET_OFFSET: 'atk_offset', W.EFF_SET_POS: 'eff_pos', W.EFF_SET_SCALE: 'eff_scale'}[addr],
                      r(3), r(4), tuple(round(self.rf(r(5) + 4 * i), 4) for i in range(3))))
            self.ret(1)
        elif addr in (W.SINF, W.COSF, W.ACOSF):
            f = {W.SINF: math.sin, W.COSF: math.cos, W.ACOSF: math.acos}[addr]
            c.append(('libm', addr, self.fr(1)))
            self.uc.reg_write(T.FR[1], struct.unpack('>Q', struct.pack('>d', f(self.fr(1))))[0])
            self.ret()
        elif addr == W.REQ_NODE:
            c.append(('node_effect', r(3), r(4), r(5), tuple(round(self.rf(r(6) + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(7) + 4 * i), 3) for i in range(3)), round(self.fr(1), 3)))
            self.ret()
        elif addr == W.REQ_FOLLOW:
            self.handle += 1
            c.append(('follow', r(3), r(4), r(5), tuple(round(self.rf(r(6) + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(7) + 4 * i), 3) for i in range(3)), round(self.fr(1), 3)))
            self.ret(self.handle)
        elif addr == ORIG4:
            c.append(('bi_skip', r(3)))
            self.ret()
        elif addr == ORIG27:
            c.append(('bi_remove', r(3)))
            self.ret()
        else:
            T.Machine.hook(self, u, addr, size, _)

    def flier(self, cfg, state=0, kind=0x11, lr=0.0):
        self.walker(cfg, state=state, kind=kind, lr=lr)
        self.uc.mem_write(OBJ + W.FL_SIZE, bytes(W.FU_SIZE - W.FL_SIZE))
        self.w32(OBJ + W.AER, ACC)
        self.w32(OBJ + W.AER + 4, FEN0)
        self.w32(OBJ + W.AER + 8, FEN1)
        self.w32(FEN0 + 0x1C, FVT)
        self.w32(FVT + 0x1C, EINIT)

    def speed(self, x, y):
        self.wf(FEN0, x)
        self.wf(FEN0 + 4, y)


def calls(m, *names):
    return [c for c in m.calls if c[0] in names]


def run(m, f, n=1, regs=None):
    out = []
    for _ in range(n):
        m.calls = []
        m.call(f, dict({3: OBJ, 4: T.INPUT}, **(regs or {})))
        out.append(list(m.calls))
    return out


def tikibuzz(img, D, fn, c0, slot, w):
    P0 = W.vl_group('tikibuzz', 0)[0]
    m = Machine(img)
    got = []
    for k in (64, 65, 66, 67, 20):
        m.flier(c0, kind=0x0F, state=3)
        m.calls = []
        m.call(slot(k), {3: OBJ})
        got.append(m.uc.reg_read(R[3]) if k != 20 else [x[2] for x in calls(m, 'chgi')])
    check(got == [3, 3, 3, 2, [10]], 'tikibuzz: slots 64-67 = 3 / 3 / 3 / 2, slot 20 (the 3DS\'s 21, stepped on) => 10 '
          '%s' % got)
    arm = {}
    for sid in range(0, 13):
        m = Machine(img)
        m.flier(c0, kind=0x0F)
        m.call(slot(45), {3: OBJ, 4: sid})
        arm[sid] = [x[2] for x in calls(m, 'atk_create')]
    vl = W.vl_group('tikibuzz', 2)
    words = lambda a: [img.u32(a + 4 * i) for i in range(42)]  # noqa: E731
    want = {s_: [] for s_ in range(13)}
    want.update({5: [D['tiki_dive']], 2: [D['tiki_bullet']]})
    check(arm == want and
          words(D['tiki_dive']) == [W.word(v) for v in vl[0]] and words(D['tiki_bullet']) == [W.word(v) for v in vl[1]],
          'tikibuzz: set_attack_data arms P2 entry 0 (power 2, angle 60, kbg 120, fkb 50, size 4, node 2, y -1) in '
          'state 5 (the dive) and entry 1 (the defeated body) in 2 only; words = the 3DS vl\'s')
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.target, m.target_x = 1, 50.0
    m.wf(POSTURE + 0x60, -1.0)
    m.call(slot(41), {3: OBJ})
    check([x[0] for x in m.calls if x[0] in ('aer_ctor', 'rhombus', 'nearest', 'reverse_lr', 'chg')] ==
          ['aer_ctor', 'rhombus', 'nearest', 'reverse_lr', 'chg'] and calls(m, 'chg')[0][2] == 3,
          'tikibuzz start (0x778A8): the aerial module, set_rhombus, faces the nearest fighter, -> 3')
    # 3 fly
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.wf(POSTURE + 0x14, 40.0)
    m.speed(1.0, 2.0)
    m.call(fn['t_fly_en'], {3: OBJ})
    she = calls(m, 'slip_homing_ext')
    exp = tuple(round(v, 4) for v in (P0[3], P0[4], P0[7], P0[8], P0[5], P0[6]))
    ok = (she == [('slip_homing_ext', OBJ + W.AER, exp)] and calls(m, 'set_speed') == [('set_speed', OBJ + W.AER, 0.0,
                                                                                          0.0)]
          and calls(m, 'motion') == [('motion', OBJ, 11, 0.0, 1.0, 1, 0.0)] and m.r32(OBJ + W.AER + 0x30) == 0 and
          m.rf(OBJ + W.AER + 0x44) == 35.0 and m.rf(OBJ + W.AER + 0x58) == -1.0 and
          m.uc.mem_read(OBJ + W.AER + 0x54, 1) == b'\x01' and m.rf(OBJ + W.Y0) == 40.0)
    check(ok, 'tikibuzz 3 enter (0x78668): passable, Fly loop, set_mode_homing_extend (speed 0, then the Wii U\'s slip '
          'homing extend) with P0 (f3, f4, f7, f8, f5, f6) %s, swing +0x54 1 / +0x58 -1, target fighter 0 at +35' % (
              she,))
    m.found = -1
    log = run(m, fn['t_fly_up'], 61)
    srch = [i for i, c in enumerate(log) if [x for x in c if x[0] == 'search']]
    m2 = Machine(img)
    m2.flier(c0, kind=0x0F)
    m2.found = 0
    m2.w32(OBJ + W.V(0), 30)
    l2 = run(m2, fn['t_fly_up'])
    m3 = Machine(img)
    m3.flier(c0, kind=0x0F)
    m3.w32(OBJ + W.V(0), 899)
    m3.w32(OBJ + W.V(1), 5)
    l3 = run(m3, fn['t_fly_up'], 2)
    check(srch == [0, 30, 60] and all([x for x in c if x[0] == 'aer_update'] for c in log) and
          [x[2] for x in l2[0] if x[0] == 'chg'] == [4] and m2.r32(OBJ + W.V(1)) == 152 and
          [x[2] for c in l3 for x in c if x[0] in ('chg', 'search')] == [9],
          'tikibuzz 3 update (0x77A2C): aerial update; search 0 every 30 frames of V0 (frames %s); found -> 4 with a '
          '152-frame cool-down (no search while it runs); V0 reaches 900 -> 9 (leave)' % srch)
    # 4 hold -> 5 dive -> 6 brake / 7 landed -> 8 -> 3
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_hold_en'], {3: OBJ})
    ei = calls(m, 'einit')
    check(calls(m, 'motion') == [('motion', OBJ, 2, 0.0, 0.75, 0, 0.0)] and ei and ei[0][2:] == (0x17, 0.0, 0.0, ACC,
                                                                                                 0xFFFFFFFF) and
          calls(m, 'kinetic') == [('kinetic', T.EKIN, 11)] and calls(m, 'target_pos') == [('target_pos', 0)],
          'tikibuzz 4 enter (0x780A4): AttackHold at 0.75, set_mode_none (mode -1, energy init 0x17, speed 0), kinetic '
          '11, V6 = fighter 0\'s y')
    m.motion_end = True
    check([x[2] for x in run(m, fn['t_hold_up'])[0] if x[0] == 'chg'] == [5], 'tikibuzz 4 update: at the end -> 5')
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_dive_en'], {3: OBJ})
    ei = calls(m, 'einit')
    check(calls(m, 'motion') == [('motion', OBJ, 0, 0.0, 1.0, 1, 0.0)] and ei and ei[0][2:] == (0x17, 0.0, -6.0, ACC, 5),
          'tikibuzz 5 enter (0x77964): Attack loop, set_mode_uniform((0, -6)) (mode 5, energy 0 speed (0, -6))')
    m.wf(POSTURE + 0x14, 10.0)
    m.wf(OBJ + W.V(6), 0.0)
    m.ground = False
    seq = []
    for f in range(12):
        c = run(m, fn['t_dive_up'])[0]
        seq.append([x[0] + (str(x[2]) if x[0] in ('chg', 'chgi') else '') for x in c if x[0] in ('chg', 'chgi')])
        if f == 3:
            m.wf(POSTURE + 0x14, -1.0)
    m2 = Machine(img)
    m2.flier(c0, kind=0x0F)
    m2.ground = True
    l2 = run(m2, fn['t_dive_up'])
    check([i for i, x in enumerate(seq) if x] == [9, 10, 11] and seq[9] == ['chg6'] and
          [x[2] for x in l2[0] if x[0] == 'chgi'] == [7] and not calls(m2, 'passable') == [],
          'tikibuzz 5 update (0x77CB0): 9 dive frames -> 6; on the ground => 7; at / below V6 passable off')
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.speed(0.5, -3.0)
    m.call(fn['t_brk_en'], {3: OBJ})
    ei = calls(m, 'einit')
    check(ei and ei[0][2:] == (0x17, 0.5, -3.0, ACC, 4) and m.rf(OBJ + W.AER + 0x1C) == round(P0[15], 6) or
          ei and ei[0][2:] == (0x17, 0.5, -3.0, ACC, 4) and abs(m.rf(OBJ + W.AER + 0x1C) - P0[15]) < 1e-6,
          'tikibuzz 6 enter (0x78240): AttackBrake at 0.7, set_mode_braking(0, 0.04) (mode 4, the current speed kept)')
    m.ground, m.vy = False, -1.0
    a = [x[2] for x in run(m, fn['t_brk_up'])[0] if x[0] == 'chg']
    m.vy = 0.0
    b = [x[2] for x in run(m, fn['t_brk_up'])[0] if x[0] == 'chg']
    m.ground, m.motion_end = True, False
    c = run(m, fn['t_brk_up'])[0]
    m.motion_end = True
    d_ = [x[2] for x in run(m, fn['t_brk_up'])[0] if x[0] == 'chg']
    check(a == [] and b == [3] and [x[0] for x in c if x[0] in ('set_speed', 'einit', 'chg')] == ['set_speed', 'einit']
          and d_ == [3], 'tikibuzz 6 update (0x784B4): falling: wait; still / rising -> 3; on the ground: speed 0, '
          'set_mode_none, at the motion\'s end -> 3')
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_land_en'], {3: OBJ})
    n = 0
    while n < 60 and not [x for x in run(m, fn['t_land_up'])[0] if x[0] == 'chg']:
        n += 1
    check(calls(m, 'attach') == [] and n == 45, 'tikibuzz 7 (0x78454): AttackUnguard, request_quake(3), 45 frames -> 8')
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_land_en'], {3: OBJ})
    check(calls(m, 'quake') == [('quake', OBJ, 3)] and calls(m, 'attach') == [('attach', GROUND, 1)],
          'tikibuzz 7 enter: ground on, the camera quake 3')
    # 9 leave, 10 stomped, 11 gone
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_lv_en'], {3: OBJ})
    n = 0
    while n < 300 and not [x for x in run(m, fn['t_lv_up'])[0] if x[0] == 'chg']:
        n += 1
    check(n == 199 and calls(m, 'chg')[0][2] == 12 if calls(m, 'chg') else False,
          'tikibuzz 9 (leave, 0x7781C): Fly, set_correct(0), set_mode_none, 200 frames -> 12 (removed) (%d)' % n)
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.wf(POSTURE + 0x10, 5.0)
    m.call(fn['t_stomp_en'], {3: OBJ})
    ei = calls(m, 'einit')
    fx = calls(m, 'effect')
    check(m.r32(OBJ + W.DEFEATED) == 1 and calls(m, 'notify_death') and ei and ei[0][2:] == (0x17, 0.0, -3.0, ACC, 5)
          and fx and fx[0][2] == 0x70F0000 and calls(m, 'motion') == [('motion', OBJ, 13, 0.0, 1.0, 0, 0.0)],
          'tikibuzz 10 (stomped, 0x77F04): Step, defeated (create_dead_item: the defeat path), hit off, '
          'set_mode_uniform((0, -3)), effect 0x70F0000 at the body %s' % fx)
    m.ground = False
    n = 0
    while n < 100 and not [x for x in run(m, fn['t_stomp_up'])[0] if x[0] == 'chg']:
        n += 1
    m2 = Machine(img)
    m2.flier(c0, kind=0x0F)
    m2.ground = True
    l2 = run(m2, fn['t_stomp_up'])
    check(n == 60 and [x[2] for x in l2[0] if x[0] == 'chg'] == [11],
          'tikibuzz 10 update (0x78388): 60 frames or the ground -> 11 (%d)' % n)
    m = Machine(img)
    m.flier(c0, kind=0x0F)
    m.call(fn['t_gone_en'], {3: OBJ})
    fx = calls(m, 'effect')
    check(calls(m, 'kinetic') == [('kinetic', T.EKIN, 26)] and fx and fx[0][2] == 0x70F0001 and
          [x[2] for x in run(m, fn['t_gone_up'])[0] if x[0] == 'chg'] == [12],
          'tikibuzz 11 (0x77E50): kinetic 26, ground on, effect 0x70F0001, -> 12')
    # the stomp detection (fix v8's, with its tread box: half width 6, centre +11.72, half height 1.5)
    check([img.u32(c0 + W.CF['TB%d' % i]) for i in range(3)] == [W.fword(v) for v in (6.0, 11.72, 1.5)] and
          img.u32(c0 + W.CF['TREAD']) == 10, 'tikibuzz: tread state 10, tread box (6, 11.72, 1.5) (area 0: node 3 '
          'HipN, 12 x 3)')


def main():
    global ORIG27, ORIG4
    img = E.Image(sys.argv[1])
    vt_words = W.read_vt(img)
    A, B, d = W.assemble(vt_words)
    D = d.addr
    T.VT_ADDR[0] = D['vtf']
    fn = dict(A.labels)
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.FLIERS}
    ORIG27 = vt_words[(0xC + 8 * 27) // 4]
    ORIG4 = vt_words[(0xC + 8 * 4) // 4]

    # the text region and region G
    info = [s for s in img.secs if s[1] == 0x80000004][0]
    import rpx_patch
    region = struct.unpack('>I', bytes(rpx_patch.section_data(img.d, info))[4:8])[0]
    check(region == W.TEXT_REGION and img.u32(W.LIMIT_G - 4) == 0,
          'the RPL file info\'s text region 0x%X (code memory to 0x%08X); the text reaches it' % (region,
                                                                                               0x02000000 + region))
    g = A.g
    check(all(img.u32(g.base + 4 * i) == x for i, x in enumerate(g.words())),
          'region G: the fliers\' code 0x%08X-0x%08X' % (g.base, g.pc))

    # the factory, the vtable
    for w in W.FLIERS:
        m = Machine(img)
        m.w32(T.MOD + 4, ACC)
        m.w32(T.MOD + 8, 0)
        m.run(0x02DB94CC, 0x02DB96F8, {3: T.MOD, 4: w['kind'], 5: 0, 6: 0})
        new = calls(m, 'new')
        zero = all(m.r32(OBJ + x) == 0 for x in range(0x16C, W.FL_SIZE, 4))
        vtk = D['vt_' + w['name']] if w.get('vtover') else D['vtf']
        check(new == [('new', w['size'])] and m.r32(OBJ + 0xE0) == vtk and m.r32(OBJ + 0x168) == cfg[w['name']]
              and m.r32(T.MOD + 8) == OBJ and zero,
              'F2: %s 0x%02X -> new(0x%X), vptr %s, its CFG, the counters and aerial space zero' %
              (w['name'], w['kind'], w['size'], 'its own vtable' if w.get('vtover') else 'VTF'))
    vt = [img.u32(D['vt'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    vtf = [img.u32(D['vtf'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    diff = [k for k in range(76) if vt[(0xC + 8 * k) // 4] != vtf[(0xC + 8 * k) // 4]]
    check(diff == [10, 27, 41, 69] and all(vtf[(0xC + 8 * k) // 4] == fn['f_v%d' % k] for k in diff),
          'VTF: the walkers\' vtable but slots 10 / 27 / 41 / 69 (the kinds\' CFG handlers)')
    slot = lambda k: vtf[(0xC + 8 * k) // 4]  # noqa: E731

    # ---- Ghos
    w = [x for x in W.FLIERS if x['name'] == 'ghos'][0]
    c0 = cfg['ghos']
    m = Machine(img)
    got = []
    for k in (64, 65, 66, 67):
        m.flier(c0)
        m.call(slot(k), {3: OBJ})
        got.append(m.uc.reg_read(R[3]))
    check(got == [1, 1, 1, 4], 'ghos: slots 64-67 = the 3DS\'s 1 / 1 / 1 / 4 %s' % got)
    rows = {sid: ((W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE) if s == 'remove' else (fn[s[0]], fn[s[1]]))
            for sid, s in w['states'].items()}
    ok = True
    for sid in range(0, 8):
        m = Machine(img)
        m.flier(c0)
        m.call(slot(73), {3: OBJ, 4: sid})
        eid = sid if sid in rows else 1
        ok &= calls(m, 'chgi') == [('chgi', OBJ, eid, (0xFFFF, rows[eid][1]), (0xFFFF, rows[eid][0]), (0, 0))]
    check(ok, 'ghos: change_state over its table 1 fly, 2 stun, 3 leave, 4 dead, 5 remove (others -> 1)')
    # set_attack_data: P2 entry 1 in state 1, entry 0 in state 4, nothing else
    arm = {}
    for sid in range(0, 7):
        m = Machine(img)
        m.flier(c0)
        m.call(slot(45), {3: OBJ, 4: sid})
        arm[sid] = [x[2] for x in calls(m, 'atk_create')]
    words = lambda a: [img.u32(a + 4 * i) for i in range(42)]  # noqa: E731
    vl = W.vl_group('ghos', 2)
    check(arm == {0: [], 1: [D['ghos_body']], 2: [], 3: [], 4: [D['ghos_bullet']], 5: [], 6: []} and
          words(D['ghos_body']) == [W.word(v) for v in vl[1]] and words(D['ghos_bullet']) == [W.word(v) for v in vl[0]],
          'ghos: set_attack_data arms P2 entry 1 (power 3, angle 361, kbg 50, bkb 50, size 8, node 3) in state 1 '
          '(fly) and entry 0 (kbg 100) in state 4 (dead) only; the words are the 3DS vl\'s')
    # start
    m = Machine(img)
    m.flier(c0)
    m.w32(OBJ + W.AER + 4, 0)
    m.target = 2
    m.wf(POSTURE + 0x60, -1.0)
    m.call(slot(41), {3: OBJ})
    seq = [x[0] for x in m.calls if x[0] in ('aer_ctor', 'rhombus', 'set_lr', 'nearest', 'chg', 'follow')]
    fol = calls(m, 'follow')
    check(seq == ['aer_ctor', 'rhombus', 'set_lr', 'nearest', 'chg', 'follow'] and
          calls(m, 'aer_ctor') == [('aer_ctor', OBJ + W.AER, ACC)] and calls(m, 'set_lr') == [('set_lr', OBJ, 0.0, 1, 1)]
          and calls(m, 'chg')[0][2] == 1 and m.r32(OBJ + W.V(3)) == 2 and m.r32(OBJ + W.V(1)) == 1200 and
          fol == [('follow', OBJ, 0x7110000, 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0)] and
          m.r32(OBJ + W.V(4)) == 0x7777 and m.rf(OBJ + 0x10) == 0.0,
          'ghos start (0x109C0): the aerial module, set_rhombus, set_lr(0, 1, 1), target = nearest, leave timer 1200, '
          '-> 1, body effect 0x7110000 on node 0 %s' % seq)
    # state 1 enter: kinetic 26, a slip-homing set, ground off, passable, FlyHoming loop, the target
    sets = {(round(a[0], 4), round(a[3], 4), round(a[2], 4), round(a[5], 4), round(a[1], 4), round(a[4], 4))
            for a in W.vl_group('ghos', 7)}
    picks = {}
    for i in range(60):
        m = Machine(img)
        m.flier(c0)
        m.w32(OBJ + W.V(3), 3)
        m.w32(D['consts'] + 8, 0x2545F491 + 7919 * i)        # the xorshift state
        m.call(fn['f_g1_en'], {3: OBJ})
        sh = calls(m, 'slip_homing')
        picks[sh[0][2]] = picks.get(sh[0][2], 0) + 1
        ok = (calls(m, 'kinetic') == [('kinetic', T.EKIN, 26)] and calls(m, 'attach') == [('attach', GROUND, 0)] and
              calls(m, 'passable') == [('passable', GROUND, 1)] and len(sh) == 1 and sh[0][2] in sets and
              calls(m, 'motion') == [('motion', OBJ, 1, 0.0, 1.0, 1, 0.0)] and m.r32(OBJ + W.AER + 0x30) == 3 and
              m.uc.mem_read(OBJ + W.AER + 0x2C, 1) == b'\0' and 20 <= m.r32(OBJ + W.V(0)) <= 40)
        if not ok:
            break
    check(ok and set(picks) == sets and max(picks.values()) > 45,
          'ghos 1 enter (0x1091C): kinetic 26, slip homing with a P7 set (96 %% / 4 %%: %s), ground off, passable, '
          'FlyHoming loop, the aerial target = V3, V0 in [20, 40]' % sorted(picks.values()))
    # state 1 update: the aerial update; V0 out -> a new set; V1 out -> 3
    m = Machine(img)
    m.flier(c0, state=1)
    m.w32(OBJ + W.V(0), 2)
    m.w32(OBJ + W.V(1), 3)
    log = []
    for f in range(3):
        m.calls = []
        m.call(fn['f_g1_up'], {3: OBJ, 4: T.INPUT})
        log.append([x[0] for x in m.calls if x[0] in ('aer_update', 'slip_homing', 'chg', 'touch')])
    check(log == [['aer_update', 'touch'], ['aer_update', 'slip_homing', 'touch'], ['aer_update', 'touch', 'chg']]
          and m.r32(OBJ + W.V(1)) == 0, 'ghos 1 update (0x10E24): aerial update, the slip set re-picked when V0 runs '
          'out, the bounce test, -> 3 (leave) when the 1200-frame timer runs out %s' % log)
    # the bounce
    res = []
    for touch, sp, n in ((True, (0.8, 0.0), (-1.0, 0.0)), (True, (0.4, 0.0), (-1.0, 0.0)), (True, (0.2, 0.0),
                                                                                          (-1.0, 0.0)),
                         (False, (0.8, 0.0), (-1.0, 0.0)), (True, (0.5, -0.5), (0.0, 1.0)), (True, (1.6, 0.0),
                                                                                              (-1.0, 0.0))):
        m = Machine(img)
        m.flier(c0, state=1)
        m.touch_any, m.normal = touch, n
        m.speed(*sp)
        m.w32(OBJ + W.V(0), 9)
        m.w32(OBJ + W.V(1), 9)
        m.call(fn['f_g1_up'], {3: OBJ, 4: T.INPUT})
        res.append([x[2:] for x in calls(m, 'set_speed')])
    r1 = 0.6 * (0.5 / 0.64) / math.sqrt(2)
    check(res == [[(-0.6, 0.0)], [(-0.15, 0.0)], [], [], [(round(r1, 4), round(r1, 4))], [(-0.6, 0.0)]],
          'ghos bounce (L1120C): on contact the speed reflected on the ground normal (0x02D64ABC), 0.6 x min(|v|^2 '
          '/ 0.64, 1); below 0.1 nothing %s' % res)
    # stun: enter / update
    m = Machine(img)
    m.flier(c0)
    m.factor = 1.5
    m.w32(FLAGS, 0x1)
    m.call(fn['f_g2_en'], {3: OBJ})
    ok = (calls(m, 'kinetic') == [('kinetic', T.EKIN, 16)] and calls(m, 'attach') == [('attach', GROUND, 0)] and
          calls(m, 'passable') == [('passable', GROUND, 1)] and calls(m, 'motion') == [('motion', OBJ, 0, 0.0, 1.0,
                                                                                         0, 0.0)] and
          m.r32(OBJ + W.V(2)) == 45 and m.r32(FLAGS) == 0x81)
    seq = []
    for f in range(46):
        m.calls = []
        m.call(fn['f_g2_up'], {3: OBJ, 4: T.INPUT})
        if calls(m, 'chg'):
            seq.append((f, calls(m, 'chg')[0][2], m.r32(FLAGS)))
            break
    check(ok and seq == [(44, 1, 0x1)], 'ghos 2 (stun, 0x10AD0 / 0x10EE4): kinetic 16, ground off, passable, '
          'DamageStart, hit_return_frame() = int(gl +0x154 (30) x factor (1.5)) = 45 frames, kinetic flag 0x80 set; '
          'at the end cleared, -> 1 %s' % seq)
    # slot 10 (damage), 69 (stun), 27 (remove)
    m = Machine(img)
    m.flier(c0)
    m.w32(OBJ + W.V(1), 7)
    m.call(slot(10), {3: OBJ})
    check([x[0] for x in m.calls] == ['bi_damage'] and m.r32(OBJ + W.V(1)) == 1200,
          'ghos slot 10 (notify_on_damage 0x11094): BehaviorImpl\'s, then the leave timer back to 1200')
    out = {}
    for leaving in (0, 1):
        m = Machine(img)
        m.flier(c0, state=3 if leaving else 1)
        m.w32(OBJ + W.V(6), 40 if leaving else 0)
        m.w32(OBJ + W.V(5), 0x7777 if leaving else 0)
        m.call(slot(69), {3: OBJ})
        out[leaving] = ([x[:3] for x in m.calls if x[0] in ('remove_effect', 'set_correct', 'chgi')],
                        m.uc.reg_read(R[3]), m.r32(OBJ + W.V(6)), m.r32(OBJ + W.V(5)))
    check(out == {0: ([('chgi', OBJ, 2)], 1, 0, 0),
                  1: ([('remove_effect', OBJ, 0x7777), ('set_correct', GROUND, 5), ('chgi', OBJ, 2)], 1, 0, 0)},
          'ghos slot 69 (0x113A4): a running leave finalised (effect removed, set_correct(5)), => 2, returns 1 %s' % out)
    m = Machine(img)
    m.flier(c0)
    m.w32(OBJ + W.V(4), 0x5555)
    m.call(slot(27), {3: OBJ})
    check([x[:3] for x in m.calls] == [('remove_effect', OBJ, 0x5555), ('bi_remove', OBJ)] and
          m.r32(OBJ + W.V(4)) == 0, 'ghos slot 27 (notify_on_remove, the 3DS\'s 28 0x11140): the body effect removed, '
          'then BehaviorImpl\'s')
    # leave (3 -> 5) and death (4 -> 5)
    m = Machine(img)
    m.flier(c0)
    m.call(fn['f_leave_en'], {3: OBJ})
    fol = calls(m, 'follow')
    ok = (m.r32(OBJ + W.V(6)) == 100 and round(m.rf(EN + 0x30), 4) == -0.02 and m.rf(EN + 0x34) == 30.0 and
          calls(m, 'kinetic') == [('kinetic', T.EKIN, 15)] and calls(m, 'set_correct') == [('set_correct', GROUND, 0)]
          and fol == [('follow', OBJ, 0x8000005, 0, (0.0, 3.0, 0.0), (0.0, 0.0, 0.0), 0.85)])
    n = 0
    while n < 200:
        m.calls = []
        m.call(fn['o_leave_up'], {3: OBJ, 4: T.INPUT})
        n += 1
        if calls(m, 'chg'):
            break
    check(ok and n == 100 and calls(m, 'chg')[0][2] == 5 and calls(m, 'remove_effect'),
          'ghos 3 (leave, 0x10DD0: init_common_leave(P6)): 100 frames, energy +0x30 -0.02 / +0x34 30, kinetic 15, '
          'set_correct(0), effect 0x8000005 at (0, 3, 0) x 0.85; then removed, -> 5 (frames %d)' % n)
    m = Machine(img)
    m.flier(c0)
    m.call(fn['g_dead_en'], {3: OBJ})
    check(calls(m, 'motion') == [('motion', OBJ, 0, 0.0, 0.0, 0, 0.0)] and calls(m, 'bullet') and
          m.r32(OBJ + W.DEFEATED) == 1, 'ghos 4 (dead, 0x10E84): DamageStart at rate 0, bullet(), defeated')
    tikibuzz(img, D, fn, cfg['tikibuzz'], slot, [x for x in W.FLIERS if x['name'] == 'tikibuzz'][0])
    for w in W.FLIERS:
        m = Machine(img)
        m.flier(cfg[w['name']], kind=w['kind'])
        m.call(fn[w['fstart']], {3: OBJ})
        check(calls(m, 'rhombus') == [('rhombus', OBJ)], '%s start: set_rhombus(this) (step 2f: was the aerial '
              'module)' % w['name'])
    import smashrun_furiijio_test
    smashrun_furiijio_test.furiijio(img, D, fn, cfg['furiijio'], vt_words, Machine, calls, run)
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
