#!/usr/bin/env python3
"""Behaviour tests of step 2k (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2k") on a patched
executable, in unicorn (smashrun_step2j_test.py's machine), every expected value from the 3DS code:

  python3 tools/smashrun_step2k_test.py PATCHED.rpx [ENEMY_ROOT [FS_DIR SM_DIR]]

- Waddle Doo's beam: the search (walk / fall / jump: search_interval(1) 20, the cool-down, search_target(1) 60 x 70
  at (30, 20)), 10 the charge, 11 the fan (7 shots, 3 frames apart, 30 -> -120 degrees x lr through
  generate_article_angle), the cool-down 150, the leave timer reset; the article's spawner (the activate param); the
  article set and the param object the Wii U's own beam (weapon kind 0xAF) reads, and that beam's init itself run on
  them (speed, attack, effect);
- Churine: the search, 8 the attack hop, 9 the powder (the follow effect, its rate, its end, the cool-down), slot 69,
  the dead enter, the start's first-frame attack; with ENEMY_ROOT its converted attack.bin's sleep hitboxes;
- the twins: k2_twins (new objects from the kinds' files, the slots, the previous ones deleted, a missing / empty
  file ignored); with FS_DIR / SM_DIR the remapped files (tools/smashrun_twin_params.py) keep the twins' layout and
  carry the 3DS values the audit listed;
- the White Bear's weakness (attribute 5 hits x2).
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
import smashrun_step2j_test as J  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402

check = T.check
OBJ, ACC, POSTURE, EN, GROUND, HEAP = T.OBJ, T.ACC, T.POSTURE, T.EN, T.GROUND, T.HEAP
TEAMO, TVT, ACC_EFF = HEAP + 0x3D000, HEAP + 0x3D100, HEAP + 0x3D200
STUB = 0x02000080                   # generic stubs: STUB + 4 k (blr), recorded
MODS, VTS, EBUF, WPN, PRM = (HEAP + 0x3E000 + 0x200 * i for i in range(5))
NSTUB = 0x40


class K(J.PM):
    def __init__(self, img):
        J.PM.__init__(self, img)
        self.exist, self.captured, self.objs, self.files = 1, None, [], set()
        self.uc.mem_write(STUB, b'\x4E\x80\x00\x20' * NSTUB)
        self.w32(ACC + W.ACC_TEAM, TEAMO)
        self.w32(TEAMO + 4, TVT)
        self.w32(TVT + 0x14, STUB)
        self.w32(ACC + 0x30D8, ACC_EFF)          # the EffectModule (set_rate_last's this)

    def hook(self, u, addr, size, x):
        r = lambda n: u.reg_read(T.R[n])  # noqa: E731
        c = self.calls
        if STUB <= addr < STUB + 4 * NSTUB:
            k = (addr - STUB) // 4
            c.append(('stub', k, r(3), r(4), r(5), r(6), round(self.fr(1), 4)))
            if k == 0x54 // 4 and r(6):                # set_attack's AttackData (the beam's init)
                self.adata = bytes(self.uc.mem_read(r(6), 0x60))
            if k == 0:
                return self.ret(3)                   # the team
            if k == 0x54 // 4:
                return self.ret(EBUF)                # the energy getter (the beam's init)
            return self.ret()
        if addr == W.REQ_FOLLOW:
            c.append(('follow', r(3), r(4), r(5), tuple(round(self.rf(r(6) + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(7) + 4 * i), 3) for i in range(3)), round(self.fr(1), 3)))
            return self.ret(0x7777)
        if addr == W.GEN_ART_ANGLE:
            c.append(('gen', r(3), r(4), round(self.fr(1), 3), r(5)))
            return self.ret()
        if addr == W.EFF_EXIST:
            c.append(('exist', r(3)))
            return self.ret(self.exist)
        if addr == W.EFF_RATE_LAST:
            c.append(('rate_last', r(3), round(self.fr(1), 3)))
            return self.ret()
        if addr == W.ACT_PARAM:
            self.uc.mem_write(r(3), bytes(0xA8))
            return self.ret()
        if addr == W.UTIL_ACTIVATE:
            self.captured = (r(3), bytes(self.uc.mem_read(r(4), 0xA8)), r(4))
            return self.ret()
        if addr == W.ACT_PARAM_FREE:
            c.append(('free', r(3), r(4)))
            return self.ret()
        if addr == W.BI_NOTIFY_DMG:
            c.append(('notify_damage', r(3)))
            return self.ret()
        if addr == W.BI_SLOT31:
            c.append(('slot31', r(3), r(4)))
            return self.ret()
        # k2_twins' resource / param calls
        if addr in (W.RES_DIR, W.RES_DIR2, W.RES_FREE, W.RES_NEW):
            c.append((hex(addr), r(3), r(4)))
            if addr == W.RES_NEW:
                self.w32(r(3), 0)
            return self.ret(r(3))
        if addr == W.RES_JOIN:
            name = bytes(self.uc.mem_read(r(5), 40)).split(b'\0')[0].decode()
            self.w32(r(4), 0xF11E if name in self.files else 0)
            c.append(('join', name))
            return self.ret()
        if addr in W.TWIN_CTOR.values():
            o = HEAP + 0x38000 + 0x400 * len(self.objs)
            self.objs.append(o)
            self.uc.mem_write(o, bytes(0x200))
            c.append(('ctor', addr, r(3), o))
            return self.ret(o)
        if addr in W.TWIN_PARSE.values():
            c.append(('parse', addr, r(4)))
            self.w32(r(4) + 0x30, 0 if getattr(self, 'empty', False) else 2)
            return self.ret()
        if addr in W.TWIN_DTOR.values():
            c.append(('dtor', addr, r(3), r(4)))
            return self.ret()
        return J.PM.hook(self, u, addr, size, x)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    H.M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    want = {A.h.base + 4 * i: x for i, x in enumerate(A.h.words())}
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'region H: the step 2k code to 0x%08X is in the executable %s' % (A.h.pc, bad[:4]))
    byname = {w['name']: w for w in W.WALKERS}
    cfgs = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}

    def kworld(n, state, lr=-1.0, setup=None):
        w = byname[n]
        m = K(img)
        m.walker(cfgs[n], state=state, lr=lr, kind=w['kind'])
        m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x40))
        m.target, m.target_x = 0, 300.0
        if setup:
            setup(m)
        rows = {sid: ((W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE) if s_ == 'remove' else
                      tuple(x if isinstance(x, int) else fn[x] for x in s_)) for sid, s_ in w['states'].items()}
        return T.World(m, w, rows, state, cfgs[n])

    calls = lambda wo, k: [c for e in wo.log for c in e[4] if c[0] == k]  # noqa: E731

    # ==== Waddle Doo
    w = byname['waddledoo']
    cf = lambda n, k: img.u32(cfgs[n] + W.CF[k])  # noqa: E731
    check(cf('waddledoo', 'SIZE') == 0x1D0 and w['states'][10] == ('do_ch_en', 'do_ch_up') and
          w['states'][11][:2] == ('se_waddledoo_11', 'do_bm_up') and W.SE_ORIG[('waddledoo', 11)] == 'do_bm_en' and w['states'][1][1] == 'do_fall_up',
          'waddledoo: object 0x1D0 (DO_* after the walker\'s 0x1B0), states 10 / 11 the 3DS\'s 7 / 8, 1 its own fall')

    def doo(state, lr=-1.0, cd=0, sc=0, found=0, ground=True):
        def setup(m):
            m.w32(OBJ + W.V(4), 0xFFFFFC18)          # the random hop held back (smashrun_step2j_test.py)
            m.w32(OBJ + W.V(7), 100)
            m.w32(OBJ + W.DO_CD, cd & 0xFFFFFFFF)
            m.w32(OBJ + W.DO_SC, sc)
            m.found, m.ground = found, ground
        return kworld('waddledoo', state, lr, setup)

    # walk: the beam's search every 21st frame (+0x16C > 20), the cool-down counting down only then (0x7D5D0..)
    wo = doo(3, cd=2)
    wo.run(23)
    s = [(e[0], c) for e in wo.log for c in e[4] if c[0] == 'search']
    chg = [(e[0], c[2]) for e in wo.log for c in e[4] if c[0] == 'chg']
    check(s[:1] == [(22, ('search', 2, OBJ + 0x10, (30.0, 20.0, 60.0, 70.0, 0.0)))] and chg[:1] == [(22, 10)] and
          wo.m.r32(OBJ + W.V(7)) == 600 and wo.m.r32(OBJ + W.DO_SC) == 0 and
          wo.m.r32(OBJ + W.DO_CD) == 0xFFFFFFFF,
          'waddledoo walk: frames 21 / 22 count the cool-down (2) down, frame 23 search_target(1) (60 x 70 at (30, 20)) '
          'finds -> the leave timer back to 600 (0x7D62C), => 10 (the 3DS 7) %s %s' % (s[:1], chg[:1]))
    wo = doo(3, found=-1)
    wo.run(21)
    s = [c for c in calls(wo, 'search')]
    check([c[3][2] for c in s] == [60.0] and wo.m.r32(OBJ + W.V(7)) == 79 and wo.cur == 3,
          'waddledoo walk: not found (frame 21) -> no change, the leave timer not reset, the walk goes on %s' % s)
    # fall (0x7D21C): in the air the search sets +0x19D (DO_AIR); on the ground => 2 at once (no speed test)
    wo = doo(1, sc=20, ground=False)
    wo.run(1)
    air = wo.m.r32(OBJ + W.DO_AIR)
    wo2 = doo(1, sc=20, ground=True)
    wo2.m.vy = 3.0
    wo2.run(1)
    check(air == 1 and [c[2] for c in calls(wo, 'chg')] == [10] and [c[2] for c in calls(wo2, 'chgi')] == [2],
          'waddledoo fall: the beam\'s search in the air (+0x19D = 1) => 10; on the ground => 2 (rising or not)')
    wo = doo(9, sc=20, ground=False)
    wo.m.vy = 2.0
    wo.run(1)
    check(wo.m.r32(OBJ + W.DO_AIR) == 1 and [c[2] for c in calls(wo, 'chg')] == [10],
          'waddledoo jump (the 3DS 6, 0x7D350): not landed -> the beam\'s search in the air => 10')
    # 10 the charge (0x7DD40 / 0x7DEEC)
    wo = doo(10)
    en = [c for c in wo.log[0][5]] if wo.log else []
    en = wo.enter(10)
    k10 = [c[2] for c in en if c[0] in ('kinetic', 'attach')]
    mot = [c for c in en if c[0] == 'motion']
    wo2 = doo(10, ground=False, setup=None) if False else doo(10, ground=False)
    wo2.m.w32(OBJ + W.DO_AIR, 1)
    en2 = wo2.enter(10)
    wo2.m.ground = True
    wo2.run(1)
    land = [c[2] for c in wo2.log[0][4] if c[0] in ('kinetic', 'attach')]
    wo.run(7)
    check(k10 == [0, 1] and mot == [('motion', OBJ, 1, 0.0, 1.0, 0, 0.0)] and
          not [c for c in en2 if c[0] in ('kinetic', 'attach')] and land == [0, 1] and
          wo2.m.r32(OBJ + W.DO_AIR) == 0 and 11 in wo.states(),
          'waddledoo 10 (the 3DS 7): on the ground kinetic 0 / ground on, BeamShotHold at PS8c f3 1.0 (once); charged '
          'in the air: no kinetic change until it lands (then 0 / ground on, +0x19D off); the end => 11 %s' % wo.states())
    # 11 the fan (0x7D060 / 0x7DB04): BeamShot at 4.0, cool-down 150; a shot every 3 frames: 30 - 25 n x lr
    for lr in (1.0, -1.0):
        wo = doo(11, lr=lr)
        en = wo.enter(11)
        wo.run(25)
        g = [(e[0], c[3]) for e in wo.log for c in e[4] if c[0] == 'gen']
        exp = [(3 * n, (30.0 - 25.0 * n) * lr) for n in range(7)]
        args = {(c[1], c[2], c[4]) for e in wo.log for c in e[4] if c[0] == 'gen'}
        check(g == exp and args == {(OBJ, 0, 0)} and ('motion', OBJ, 0, 0.0, 4.0, 0, 0.0) in en and
              wo.m.r32(OBJ + W.DO_CD) == 150 and wo.states()[-1] == 3,
              'waddledoo 11 (the 3DS 8) lr %d: BeamShot at PS8c f4 4.0, the cool-down 150; generate_article_angle(0, '
              'a, false) on frames %s, a = %s; all shot and the motion\'s end => 3'
              % (lr, [x[0] for x in g], [x[1] for x in g]))
    # the article's spawner (3DS 0x7DDB0): the activate param
    m = K(img)
    m.wf(POSTURE + 0x10, 100.0)
    m.wf(POSTURE + 0x14, 10.0)
    m.wf(POSTURE + 0x60, -1.0)
    m.node_off = (1.0, 7.0)
    m.wf(GROUND + 0x88, 2.5)
    m.wf(EN + 0x54, -45.0)
    m.w32(ACC, 0x1234)
    m.call(fn['do_beam_cb'], {3: 0xA471C1E, 4: ACC})
    art, p, pa = m.captured
    u = lambda o: struct.unpack('>I', p[o:o + 4])[0]  # noqa: E731
    f = lambda o: round(struct.unpack('>f', p[o:o + 4])[0], 3)  # noqa: E731
    node = [c for c in m.calls if c[0] == 'node_gpos']
    frees = [c[1:] for c in m.calls if c[0] == 'free']
    check(art == 0xA471C1E and node and node[0][2] == 3 and (f(4), f(8), f(0xC), f(0x10)) == (92.0, 17.75, 2.5, -1.0)
          and (u(0x1C), u(0x20), u(0x28), u(0x2C), u(0x58), f(0x68), p[0x60], p[0x6C]) ==
          (0, 0x1234, 3, 8, 4, -45.0, 0, 0) and frees == [(pa + 0x48, 2), (pa + 0x3C, 2)] and m.uc.reg_read(T.R[3]) == 0,
          'waddledoo beam spawner (3DS 0x7DDB0): node 3 + (PS8c f6 9 x lr, f7 0.75), z the ground\'s +0x88; lr, the '
          'owner\'s id, team, life PSc4 f0 8, +0x58 4, the angle (AI +0x54); util_activate, the members freed, returns '
          '0: pos (%s, %s, %s)' % (f(4), f(8), f(0xC)))
    # the article set and the param object
    art = D['art_doo']
    arts = [img.u32(art + 4 * i) for i in range(6)]
    wdp = D['wdp']
    pw = lambda o: img.u32(wdp + o)  # noqa: E731
    pf = lambda o: struct.unpack('>f', struct.pack('>I', img.u32(wdp + o)))[0]  # noqa: E731
    p7 = [img.u32(pw(0xDC) + 4 * i) for i in range(9)]
    check(arts == [art + 8, 1, 0xAF, 5, fn['do_beam_cb'], 0] and (pw(0xC4), pf(0xC8), pf(0xCC)) == (8, 4.0, 0.5) and
          (pf(0xA4), pf(0xA8)) == (9.0, 0.75) and p7 == [0, 0, 0, 2, 361, 100, 100, 0, 1] and pw(0xD8) == 1 and
          pw(0x6C) == 2 and pw(0x70) and pw(0x5C) and pw(0x30) == 1,
          'waddledoo: article set {0xAF beam, max 5, the spawner} (3DS {175, 5, 0x7DDB0}); param object (the 3DS '
          'layout): PSc4 {8, 4.0, 0.5}, PS8c f6 / f7 9 / 0.75, P7[0] power 2, angle 361, kbg 100, fixed 100, bkb 0, '
          'size 1; the common groups (area table 2 entries, P4, the bullet attack)')
    # the T / S hooks write them on a Smash Run stage
    m = K(img)
    m.stage(0x94)
    m.w32(T.MGR + 0x5EC, 2)
    m.run(E.SITE_T, W.SITE_T + 8, {31: T.MGR, 0: 2})
    t_ok = m.r32(W.ART_SETS + 4 * 0x19) == art
    m = K(img)
    m.stage(0x94)
    m.w32(E.PARAM_MGR, T.PM)
    m.w32(T.MGR + 0x5EC, 2)
    m.run(E.SITE_S, W.SITE_S + 4, {3: 0, 28: T.MGR, 31: 7})
    check(t_ok and m.r32(T.PM + W.SLOTS + 4 * 0x19) == wdp,
          'battle load on a Smash Run stage: article set[0x19] = the Doo\'s; param slot[0x19] = its object')
    # the Wii U's own beam (weapon kind 0xAF, init 0x0319FE98) run on that object: speed PSc4 f1 4 along the angle,
    # the attack from P7[0], the effect 0x7190000 at PSc4 f2 0.5
    m = K(img)
    for a in range(0x0319FE98, 0x031A026C, 4):           # its paired-single saves / loads (not run by unicorn)
        if img.u32(a) >> 26 in (4, 56, 57, 60, 61):
            m.w32(a, 0x60000000)
    m.w32(W.PARAM_MGR, T.PM)
    m.w32(T.PM + 0xC4, wdp)
    m.w32(WPN + 0x28, MODS)
    for i, off in enumerate((0x34, 0x50, 0xA0)):
        m.w32(MODS + off, MODS + 0x100 + 0x10 * i)
        m.w32(MODS + 0x100 + 0x10 * i, VTS)
    for k in range(NSTUB):
        m.w32(VTS + 4 * k, STUB + 4 * k)
    m.uc.mem_write(EBUF, bytes(0x40))
    m.wf(PRM + 0x68, -45.0)
    m.call(0x0319FE98, {3: 0, 4: WPN, 5: PRM})
    e = [round(m.rf(EBUF + 4 * i), 3) for i in range(3)]
    st = [c for c in m.calls if c[0] == 'stub']
    eff = [c for c in st if c[1] == 0x64 // 4]
    sa = [c for c in st if c[1] == 0x54 // 4 and c[2] == MODS + 0x110]
    exp = [round(-4.0 * math.sin(math.radians(-45.0)), 3), round(4.0 * math.cos(math.radians(-45.0)), 3)]
    adw = struct.unpack('>24I', getattr(m, 'adata', bytes(0x60)))
    adf = [round(struct.unpack('>f', struct.pack('>I', x))[0], 3) for x in adw]
    ad = [adf[6], adf[7]]                       # the AttackData's power / size floats (as the 3DS's sp+0x18 / +0x1C)
    print('      AttackData words', [hex(x) for x in adw[:16]])
    check(e[:2] == exp and eff and eff[0][3] == 0x7190000 and eff[0][6] == 0.5 and ad == [2.0, 1.0] and
          sa and sa[0][3:5] == (0, 0) and adw[8] == 361 and adw[9:12] == (100, 100, 0),
          'the Wii U\'s beam init (0x0319FE98) on the Doo\'s object: speed %s (4 x (-sin, cos) of -45), effect '
          '0x7190000 x0.5, set_attack(0, 0, data: power %s, size %s)' % (e[:2], ad[:1], ad[1:]) + ' %s' % st)

    # ==== Churine
    ch = byname['churine']
    check(ch['states'][8] == ('ch_hop_en', 'ch_hop_up') and ch['states'][9] == ('ch_pw_en', 'ch_pw_up') and
          [round(x, 3) for x in ch['P']] == [1.0, 10.0, 40, 0.0, 5.0, 1.0, 1.4, 210, 90.0, -90.0],
          'churine: states 8 / 9 the 3DS\'s 6 / 7; P0 f9 1, 10, f12 40, f7 / f8 (0, 5), f11 1, f10 1.4, f13 210')

    def chw(state, lr=1.0, found=-1, v=None):
        def setup(m):
            m.found = found
            for i, x in (v or {}).items():
                m.w32(OBJ + W.V(i), x & 0xFFFFFFFF)
        return kworld('churine', state, lr, setup)

    wo = chw(3, found=0)
    wo.m.target_x = 400.0
    wo.run(1)
    s1 = calls(wo, 'search')
    c1 = [c[2] for c in calls(wo, 'chg')]
    wo = chw(3, found=0, v={2: 0})
    wo.m.target_x = -400.0
    wo.run(1)
    c2 = ([c[2] for c in calls(wo, 'chg')], wo.m.r32(OBJ + W.V(2)))
    wo = chw(3, found=-1)
    wo.run(4)
    s3 = [e[0] for e in wo.log for c in e[4] if c[0] == 'search']
    wo = chw(3, found=0, v={1: 3})
    wo.run(3)
    s4 = [e[0] for e in wo.log for c in e[4] if c[0] == 'search']
    wo = chw(3, found=-1, v={3: 1})
    wo.run(2)
    c5 = [c[2] for c in calls(wo, 'chg')]
    check(s1 == [('search', 2, OBJ + 0x10, (5.0, 5.0, 100.0, 35.0, 0.0))] and c1 == [8] and c2 == ([5], 1) and
          s3 == [0, 3] and s4 == [2] and c5 == [8] and wo.m.r32(OBJ + W.V(3)) == 0,
          'churine walk (0x3D76C): search_target(0) (100 x 35 at (5, 5)) found ahead => 8 (the 3DS 6), behind -> +0x170 '
          '=> 5; not found: again after search_interval(0) 3 (frames %s); a cool-down 3 holds it (searched on frame %s); '
          'the first-frame flag => 8 once' % (s3, s4))
    wo = chw(5, v={2: 1})
    wo.m.motion_end = True
    wo.oneshot, wo.mframes = True, 9
    wo.run(1)
    check([c[2] for c in calls(wo, 'chgi')] == [8] and wo.m.r32(OBJ + W.V(2)) == 0,
          'churine 5 turn (0x3D660): at the end reverse_lr, a target pending => 8 (interrupt), +0x170 = 0')
    wo = chw(8)
    en = wo.enter(8)
    e8 = tuple(round(wo.m.rf(EN + o), 3) for o in (0x20, 0x24, 0x28, 0x2C, 0x1C))
    wo.m.ground, wo.m.vy = False, 2.0
    wo.run(1)
    stick = wo.log[0][3]
    wo.m.ground, wo.m.vy = True, -1.0
    wo.run(1)
    check(('clear_speed', OBJ) in en and e8 == (0.0, 1.0, 10.0, 10.0, 0.0) and ('kinetic', T.EKIN, 5) in en and
          ('attach', T.GROUND, 0) in en and ('motion', OBJ, 7, 0.0, 1.0, 0, 0.0) in en and stick == (1.0, 1.0) and
          [c[2] for c in calls(wo, 'chgi')] == [9],
          'churine 8 (the 3DS 6, 0x3DBF0 / 0x3DD14): clear_speed_all, W+0x20 0 / +0x24 1 / +0x28 10 / +0x2C 10 / +0x1C '
          '0 %s, kinetic 5, ground off, Jump; the stick (lr, 1); landed => 9' % (e8,))
    for lr in (1.0, -1.0):
        wo = chw(9, lr=lr)
        en = wo.enter(9)
        wo.run(45)
        fol = [(e[0], c) for e in wo.log for c in e[4] if c[0] == 'follow']
        rate = calls(wo, 'rate_last')
        check(('kinetic', T.EKIN, 0) in en and ('clear_speed', OBJ) in en and ('attach', T.GROUND, 1) in en and
              ('motion', OBJ, 9, 0.0, 1.0, 0, 0.0) in en and
              fol == [(39, ('follow', OBJ, 0x71F0000, 1, (0.0, 5.0, 0.0), (90.0 - 90.0 * lr, -90.0, 0.0), 1.0))] and
              rate == [('rate_last', ACC_EFF, 1.4)] and wo.m.r32(OBJ + W.V(5)) == 0x7777,
              'churine 9 (the 3DS 7, 0x3D3B4 / 0x3D970) lr %d: kinetic 0, clear_speed_all, ground on, SleepPowder; on '
              'its 40th frame the follow effect 0x71F0000 at node 1 (0, 5, 0), rot (90 - 90 lr, -90, 0), x1, rate 1.4'
              % lr + ' %s %s %s' % (fol, rate, [c for c in en if c[0] in ('kinetic', 'motion', 'attach', 'clear_speed')]))
    wo.m.exist = 0
    wo.run(1)
    check([c[2] for c in calls(wo, 'chg')] == [5] and wo.m.r32(OBJ + W.V(5)) == 0 and wo.m.r32(OBJ + W.V(1)) == 210,
          'churine 9: the effect gone (is_exist 0) => 5, the cool-down 210 (P0 f13)')
    wo = chw(9, v={5: 0x7777})
    wo.m.ground = False
    wo.run(1)
    rm = calls(wo, 'remove_effect')
    m = K(img)
    m.walker(cfgs['churine'], state=9, kind=0x1F)
    m.w32(OBJ + W.V(5), 0x7777)
    vt = img.u32(cfgs['churine'] + W.CF['VT'])
    m.call(img.u32(vt + 0xC + 8 * 69), {3: OBJ})
    r69 = ([c for c in m.calls if c[0] == 'remove_effect'], m.uc.reg_read(T.R[3]), m.r32(OBJ + W.V(5)))
    m = K(img)
    m.walker(cfgs['churine'], state=6, kind=0x1F)
    m.w32(OBJ + W.V(5), 0x7777)
    m.call(fn['ch_dead_en'], {3: OBJ})
    dead = [c[0] for c in m.calls if c[0] in ('remove_effect', 'bullet')]
    m = K(img)
    m.walker(cfgs['churine'], state=0, kind=0x1F)
    m.call(img.u32(vt + 0xC + 8 * 41), {3: OBJ})
    check([c[2] for c in calls(wo, 'chg')] == [1] and rm == [('remove_effect', OBJ, 0x7777)] and
          r69 == ([('remove_effect', OBJ, 0x7777)], 0, 0) and dead == ['remove_effect', 'bullet'] and
          m.r32(OBJ + W.V(3)) == 1,
          'churine: off the ground in 9 the effect removed => 1; slot 69 in 9 removes it, returns 0 (0x3DDE8); the dead '
          'enter removes it (0x3D36C); the start sets the first-frame flag (+0x171, 0x3D064)')
    if root:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import acmd as AC
        f = AC.ACMDFile.load(os.path.join(root, 'animcmd', 'enemy', 'churine', 'attack.bin'))
        sc = f.script('sleeppowder')
        hb = [(c.params[0], c.params[3], c.params[4], c.params[5], c.params[8], c.params[12]) for c in sc
              if AC.INFO.get(c.ident, {}).get('name') == 'Special_Hitbox']
        hs = img.u32(D['hs_churine'] + 4 * (3 * 9 + 1))
        check(hb == [(1, 1.0, 0x169, 7, 8.0, 9), (2, 1.0, 0x169, 3, 25.0, 9)] and hs == 0xAAFC4289,
              'churine attack.bin sleeppowder: the 3DS\'s hitboxes (id 1 kbg 7 size 8, id 2 kbg 3 size 25, angle 361, '
              '1 %%, effect 9 = sleep), run by its SleepPowder motion (hashset 0x%08X) %s' % (hs, hb))

    # ==== the twins' params
    def k2(files, prev=None, empty=False):
        m = K(img)
        m.files, m.empty = set(files), empty
        m.w32(W.PARAM_MGR, T.PM)
        m.uc.mem_write(T.PM + W.SLOTS, struct.pack('>97I', *[0x50000000 + i for i in range(0x61)]))
        if prev:
            for i, o in enumerate(prev):
                m.w32(D['k2_objs'] + 4 * i, o)
        else:
            m.uc.mem_write(D['k2_objs'], bytes(16))
        m.call(fn['k2_twins'], {})
        return m, [m.r32(T.PM + W.SLOTS + 4 * k) for k in range(0x61)], [m.r32(D['k2_objs'] + 4 * i) for i in range(4)]
    m, sl, objs = k2(['enemy_param_vl_%s.bin' % k for _t, k in W.TWIN_K])
    exp = [0x50000000 + i for i in range(0x61)]
    for i, (t, k) in enumerate(W.TWIN_K):
        exp[W.KIND_OF[k]] = objs[i]
        if t != 0x5A:
            exp[t] = objs[i]
    parses = [(c[1], c[2]) for c in m.calls if c[0] == 'parse']
    ctors = [c[1:3] for c in m.calls if c[0] == 'ctor']
    check(sl == exp and all(objs) and parses == [(W.TWIN_PARSE[t], objs[i]) for i, (t, _k) in enumerate(W.TWIN_K)] and
          ctors == [(W.TWIN_CTOR[t], 0) for t, _k in W.TWIN_K] and
          [c[1] for c in m.calls if c[0] == 'join'] == ['enemy_param_vl_%s.bin' % k for _t, k in W.TWIN_K],
          'k2_twins: each kind\'s file (param/enemy/fs) parsed into a new object of its twin\'s class (ctor(0), the '
          'twin\'s parser): slot[K] = it, slot[twin] too but for zima (the walkers\' donor)')
    m2, sl2, objs2 = k2(['enemy_param_vl_zima.bin'], prev=objs)
    dt = [(c[1], c[2], c[3]) for c in m2.calls if c[0] == 'dtor']
    exp2 = [0x50000000 + i for i in range(0x61)]
    exp2[0x0E] = objs2[3]
    m3, sl3, objs3 = k2([])
    m4, sl4, objs4 = k2(['enemy_param_vl_darios.bin'], empty=True)
    dt4 = [c for c in m4.calls if c[0] == 'dtor']
    check(dt == [(W.TWIN_DTOR[t], objs[i], 1) for i, (t, _k) in enumerate(W.TWIN_K)] and sl2 == exp2 and
          objs2[:3] == [0, 0, 0] and sl3 == [0x50000000 + i for i in range(0x61)] and objs3 == [0] * 4 and
          sl4 == sl3 and objs4 == [0] * 4 and len(dt4) == 1 and dt4[0][3] == 1,
          'k2_twins: the previous battle\'s objects deleted first (dtor(obj, 1)); a missing file leaves the slots as '
          'they are; an object that parsed no attacks is deleted and not used')
    if len(sys.argv) > 4:
        import fighter_param_vl as V
        import smashrun_twin_params as TP
        fs, sm = sys.argv[3], sys.argv[4]
        vals = {}
        for kind, twin in TP.TWINS:
            f3 = open(os.path.join(fs, 'enemy_param_vl_%s.bin' % kind), 'rb').read()
            fu = open(os.path.join(sm, 'enemy_param_vl_%s.bin' % twin), 'rb').read()
            data, _ch = TP.remap(kind, f3, fu)
            vals[kind] = [[t.value for t in g[1]] for g in TP.groups(data)]
            sig = lambda b: [x[1] if isinstance(x, tuple) else x.t for x in V.tokenize(b)[1]]  # noqa: E731
            assert sig(data) == sig(fu)
        pw, da, zi, sf = vals['plasmawisp'], vals['darios'], vals['zima'], vals['stalfos']
        check((pw[7][3], pw[7][7], pw[8][3], pw[8][7], pw[1][2], pw[1][8:11]) == (3, 50, 9, 150, 200.0, [5, 140.0, 20.0])
              and (da[0][6], da[6][5], da[6][9], da[6][46], da[6][50]) == (90, 367, 6, 5, 60) and
              (zi[2][4], zi[2][8], zi[4][9]) == (4, 70, 15.0) and (sf[4][9], sf[6][6]) == (20.0, 3.0),
              'the remapped files: the twins\' layouts (token types / groups equal), the 3DS values: Lethinium laser 3 %% '
              '/ bkb 50, cannon 9 / 150, search 200 / (5, 140, 20); Darios charge 90, beam angle 367, size 6, 5 %% / bkb '
              '60; Zima contact 4 %% / bkb 70, G4 15; Stalfos G4 20, G6 3.0')

    # ==== White Bear (set_weak_param(5, 2.0))
    wb = byname['whitebear']
    vt = img.u32(cfgs['whitebear'] + W.CF['VT'])
    s31 = img.u32(vt + 0xC + 8 * 31)
    s10 = img.u32(vt + 0xC + 8 * 10)
    res = {}
    for attr in (5, 3):
        m = K(img)
        m.walker(cfgs['whitebear'], state=3, kind=0x40)
        m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x40))
        hit, ad = HEAP + 0x3F000, HEAP + 0x3F100
        m.w32(hit + 0x14, ad)
        m.uc.mem_write(ad + 0x40, bytes([0, 0, 0, attr]))
        m.wf(OBJ + W.WB_D, 10.0)
        m.call(s31, {3: OBJ, 4: hit})
        flag = m.r32(OBJ + W.WB_W)
        m.damage = 15.0
        m.call(s10, {3: OBJ})
        res[attr] = (flag, [c for c in m.calls if c[0] in ('slot31', 'set_damage', 'notify_damage')],
                     round(m.rf(OBJ + W.WB_D), 3))
    check(res[5] == (1, [('slot31', OBJ, HEAP + 0x3F000), ('set_damage', OBJ, 20.0), ('notify_damage', OBJ)], 20.0) and
          res[3] == (0, [('slot31', OBJ, HEAP + 0x3F000), ('notify_damage', OBJ)], 15.0) and
          wb['P'][15:17] == (5, 2.0),
          'white bear: an attribute-5 hit (AttackData +0x43) takes its damage x2 (10 -> 15 becomes 20 through '
          'set_current_damage, before BehaviorImpl\'s notify_on_damage); other hits as they are %s' % res)
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
