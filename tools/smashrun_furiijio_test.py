#!/usr/bin/env python3
"""Step 2f: Furiijio's checks (tools/smashrun_walker_cave.py, FLIERS 'furiijio'; docs/smash-run-port.md, "Step 2f").
Run by tools/smashrun_flier_test.py (its Machine, with the node / attack-offset / effect / libm stubs):

  python3 tools/smashrun_flier_test.py PATCHED.rpx

Checks its vtable (slots 4 / 10 / 41 / 61 / 62), slots 64-67, change_state over its 3DS table (with the beam states'
exits), set_attack_data (P2 entry 0 in 4, 1 in 7, 2 in 9 only), start, every state's enter / update against the 3DS
sequences (enemy_fs.cro addresses in the messages), the beam's growth / hitbox offset / effects, the aim angle
(calc_angle 0x7B01D8 and the effect offset of 0x67364), the leave, the dead state and the damage / skip slots.
"""
import math
import struct

import smashrun_walker_cave as W
import smashrun_walker_test as T
from smashrun_walker_test import OBJ, ACC, POSTURE, R, check

ATKM = T.ATKM


def calc_angle(dx, dy):
    """the 3DS Behavior::calc_angle (0x7B01D8) in doubles"""
    n = math.hypot(dx, dy)
    x, y = (dx / n, dy / n) if n else (dx, dy)
    a = math.acos(max(-1.0, min(1.0, y)))
    b = math.acos(max(-1.0, min(1.0, x)))
    return a * 180.0 * (-1.0 / math.pi if b < math.pi / 2 else 1.0 / math.pi)


def furiijio(img, D, fn, c0, vtw, Machine, calls, run):
    w = [x for x in W.FLIERS if x['name'] == 'furiijio'][0]
    vt = D['vt_furiijio']
    vk = [img.u32(vt + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    vtf = [img.u32(D['vtf'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    diff = sorted(k for k in range(76) if vk[(0xC + 8 * k) // 4] != vtf[(0xC + 8 * k) // 4])
    check(diff == [4, 61, 62] and vk[(0xC + 8 * 4) // 4] == fn['f_fu_skip'] and
          vk[(0xC + 8 * 61) // 4] == vk[(0xC + 8 * 62) // 4] == fn['f_fu_kin'],
          'furiijio: its vtable = VTF but slots 4 (update_on_skip, the 3DS\'s 5), 61, 62 %s' % diff)
    slot = lambda k: vk[(0xC + 8 * k) // 4]  # noqa: E731
    V = W.V
    P = lambda i: img.u32(c0 + W.P(i))  # noqa: E731
    Pf = lambda i: struct.unpack('>f', struct.pack('>I', P(i)))[0]  # noqa: E731
    m = Machine(img)
    got = []
    for k in (64, 65, 66, 67):
        m.flier(c0, kind=0x1A)
        m.call(slot(k), {3: OBJ})
        got.append(m.uc.reg_read(R[3]))
    check(got == [1, 1, 1, 9], 'furiijio: slots 64-67 = the 3DS\'s 1 / 1 / 1 / 9 %s' % got)
    tab = img.u32(c0 + W.CF['TAB']) + 0x18
    ok = True
    for sid in range(1, 11):
        row = [img.u32(tab + 0x18 * (sid - 1) + 4 * i) for i in range(6)]
        s = w['states'][sid]
        want = ([0xFFFF, W.ZIMA_REMOVE_ENTER, 0xFFFF, W.ZIMA_REMOVE_UPDATE, 0, 0] if s == 'remove' else
                [0xFFFF, fn[s[0]], 0xFFFF, fn[s[1]]] + ([0xFFFF, fn[s[2]]] if len(s) > 2 else [0, 0]))
        ok = ok and row == want
    check(ok, 'furiijio: its table 1 fly, 2 / 5 charge, 3 / 6 aim, 4 / 7 beam (with their exits), 8 leave, 9 dead, '
          '10 remove (0x10D168)')
    arm = {}
    for sid in range(0, 11):
        m = Machine(img)
        m.flier(c0, kind=0x1A)
        m.call(slot(45), {3: OBJ, 4: sid})
        arm[sid] = [x[2] for x in calls(m, 'atk_create')]
    vl = W.vl_group('furiijio', 2)
    want = {sid: [] for sid in range(11)}
    want[4], want[7], want[9] = [D['fu_beam0']], [D['fu_beam1']], [D['fu_bullet']]
    words = [[img.u32(D[k] + 4 * i) for i in range(len(vl[0]))] for k in ('fu_beam0', 'fu_beam1', 'fu_bullet')]
    check(arm == want and words == [[W.word(v) for v in e] for e in vl],
          'furiijio: set_attack_data arms P2 entry 0 in 4 (power 4, angle 361, kbg 100, fkb 100, size 2, node 3), '
          'entry 1 in 7 (the same, +0x7C 140), entry 2 in 9 (power 3, kbg 100, bkb 50, size 3, node 2), nothing else')

    # start
    m = Machine(img)
    m.flier(c0, kind=0x1A, lr=1.0)
    m.target, m.target_x = 2, -50.0
    m.call(fn['f_fu_start'], {3: OBJ})
    aer = OBJ + W.AER
    check(calls(m, 'aer_ctor') == [('aer_ctor', aer, ACC)] and calls(m, 'rhombus') == [('rhombus', OBJ)] and
          m.r32(OBJ + V(2)) == 900 and m.r32(OBJ + V(3)) == 2 and calls(m, 'reverse_lr') and
          m.r32(aer + 0x30) == 2 and m.rf(aer + 0x44) == 25.0 and [x[2] for x in calls(m, 'chg')] == [1],
          'furiijio start (0x6BE88): aerial module, set_rhombus, V2 = 900, target = nearest (turned to it), aerial '
          'target at (0, 25, 0), -> 1')

    # 1 fly
    m = Machine(img)
    m.flier(c0, kind=0x1A, state=1)
    m.call(fn['fu1_en'], {3: OBJ})
    sh = calls(m, 'slip_homing')
    mot = calls(m, 'motion')
    check(calls(m, 'set_speed') and sh and sh[0][2] == tuple(round(Pf(i), 4) for i in range(6)) and
          mot == [('motion', OBJ, 9, 0.0, 1.0, 1, 0.0)] and m.r32(OBJ + V(0)) == 50 and calls(m, 'passable') and
          ('attach', T.GROUND, 0) in calls(m, 'attach'),
          'furiijio 1 enter (0x6BF78): set_mode_homing(P0 row: 0.1, 0.05, 0.015, 0.025, 1.2, 1) (speed 0, then mode 2), '
          'passable, ground off, Move (loop), V0 = search interval 50 %s' % (sh,))
    m.w32(OBJ + V(3), 0xFFFFFFFF)
    m.target = 0xFFFFFFFF
    (c,) = run(m, fn['fu1_up'])
    check(not [x for x in c if x[0] == 'aer_update'], 'furiijio 1 update: no target, none near -> the frame ends')
    m.target = 1
    m.w32(OBJ + V(0), 5)
    m.w32(OBJ + V(2), 2)
    (c,) = run(m, fn['fu1_up'])
    check(m.r32(OBJ + V(3)) == 1 and m.r32(aer + 0x30) == 1 and [x for x in c if x[0] == 'aer_update'] and
          m.r32(OBJ + V(2)) == 1 and not [x for x in c if x[0] == 'search'],
          'furiijio 1 update (0x6C0E8): the nearest fighter becomes the (aerial) target, aerial update, V2 counts')
    (c,) = run(m, fn['fu1_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [8], 'furiijio 1: V2 runs out -> 8 (leave)')
    seen = set()
    for seed in range(1, 40):
        m.w32(D['consts'] + 8, seed * 0x9E3779B1 & 0xFFFFFFFF)
        m.w32(OBJ + V(0), 0)
        m.w32(OBJ + V(1), 0)
        m.w32(OBJ + V(2), 500)
        m.found = 3
        (c,) = run(m, fn['fu1_up'])
        nxt = [x[2] for x in c if x[0] == 'chg']
        seen.update(nxt)
        if not (m.r32(OBJ + V(3)) == 3 and m.r32(OBJ + V(2)) == 900 and m.r32(OBJ + V(0)) == 50 and
                len(nxt) == 1 and [x[1] for x in c if x[0] == 'search'] == [2]):
            seen.add('bad')
    m.w32(OBJ + V(0), 0)
    m.w32(OBJ + V(1), 5)
    (c,) = run(m, fn['fu1_up'])
    check(seen == {2, 5} and not [x for x in c if x[0] == 'search'],
          'furiijio 1: V0 and the cool-down V1 below 0 -> search_target(0) (type 2); found -> V3, V2 = 900, '
          'random(0, 2) < 1 -> 5 (sweep) else 2; no search while V1 runs %s' % sorted(map(str, seen)))

    # 2 charge
    m = Machine(img)
    m.flier(c0, kind=0x1A, state=2, lr=-1.0)
    m.wf(POSTURE + 0x10, 10.0)
    m.wf(POSTURE + 0x14, 20.0)
    m.center = (12.0, 27.0, 0.5)
    m.call(fn['fu2_en'], {3: OBJ})
    e0 = calls(m, 'effect0')
    check(e0 and e0[0][2] == 0x71A0000 and e0[0][3] == (12.0, 27.0, 0.5) and
          [m.rf(OBJ + W.FU_C + 4 * i) for i in range(3)] == [2.0, 7.0, 0.5] and m.r32(OBJ + V(4)) == 22 and
          calls(m, 'motion') == [('motion', OBJ, 8, 0.0, 1.0, 1, 0.0)] and calls(m, 'set_speed'),
          'furiijio 2 enter (0x6D0F0): speed 0, IceBeamShotHold (loop), FU_C = center_pos - posture, effect '
          '0x71A0000 there x 1, V4 = 22 %s' % (e0,))
    outs = []
    for _ in range(24):
        (c,) = run(m, fn['fu2_up'])
        outs.append([x[2] for x in c if x[0] == 'chg'])
    check(outs[:22] == [[]] * 22 and outs[22] == [3], 'furiijio 2 update (0x6D924): V4 below 0 -> 3 (23rd frame)')
    m.call(fn['fu5_en'], {3: OBJ})
    e0 = calls(m, 'effect0')
    check(e0 and e0[-1][2] == 0x71A0001 and m.r32(OBJ + V(4)) == 34, 'furiijio 5 enter (0x6D4F0): the same with '
          'effect 0x71A0001, V4 = 34')

    # 3 aim
    for (tx, ty) in ((60.0, 40.0), (-30.0, -5.0), (12.0, 80.0)):
        m.target_x, m.target_y = tx, ty
        m.w32(OBJ + V(3), 1)
        m.wf(OBJ + V(8), 77.0)
        m.calls = []
        m.call(fn['fu3_en'], {3: OBJ})
        a = calc_angle(tx - 12.0, ty - 27.0)
        ry = m.rf(OBJ + W.FU_ROT + 4)
        rot = calls(m, 'node_rot')
        tr = calls(m, 'node_trans')
        ne = calls(m, 'node_effect')
        b = -ry * math.pi / 180
        ok = (abs(ry - a * -1.0) < 1e-3 and m.rf(OBJ + W.FU_ROT) == 0.0 and m.rf(OBJ + W.FU_ROT + 8) == 90.0 and
              rot and rot[0][2] == 3 and abs(rot[0][3][1] - ry * math.pi / 180) < 1e-3 and
              abs(rot[0][3][2] - math.pi / 2) < 1e-3 and abs(rot[0][3][0]) < 1e-6 and rot[0][4] == 0 and
              tr and tr[0][2:] == (3, (12.0, 27.0, 0.5), 1, 0) and len(calls(m, 'dirty')) == 2 and
              ne and ne[0][2:4] == (0x71A0005, 2) and abs(ne[0][4][0] - 10 * math.sin(b)) < 1e-3 and
              abs(ne[0][4][1] - 10 * math.cos(b)) < 1e-3 and ne[0][5] == (0.0, 0.0, round(-ry, 3)) and
              ne[0][6] == 1.5 and m.r32(OBJ + V(4)) == 25 and m.rf(OBJ + V(8)) == 0.0)
        check(ok, 'furiijio 3 enter (0x6D224) target (%g, %g): angle %.2f (calc_angle x lr), BeamN (node 3) turned '
              '(0, a, 90) deg (the 3DS angles; step 2j: the beam models bones billboard themselves) and placed at the posture + FU_C, effect 0x71A0005 on node 2 at (10 sin b, 10 cos b) '
              'rot (0, 0, lr a) x 1.5, V4 = 25, beam length 0 %s %s' % (tx, ty, ry, rot, ne))
    # step 2g v5: the beam's world turn. Both games build a node's matrix as Rz Ry Rx (3DS Matrix34::set_rotate_xyz
    # 0x87D298, Wii U 0x033730A0, read off their code); the model root is the yaw (Ry(-90): the flip kinds' camera
    # view). The 3DS beam models' planes (XY, the beam along X) are Y-axial billboards there; the port turns them to
    # the camera with x = 90: the beam keeps its direction (X) and its planes face the camera (Z along the view), where
    # the 3DS angles (0, a, 90) left Y along the view (edge-on). The user's step 2g v4 log (the beam body's record
    # +0x80: rows (-1.338, 0, 0.677), (-0.677, 0, -1.338), (0, -1.5, 0), scale 1.5) is exactly the old turn at
    # a = -116.8: the model check is checked against it too.
    def rz_ry_rx(x, y, z):
        cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
        return [[cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
                [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
                [-sy, sx * cy, cx * cy]]

    def mul(p, q):
        return [[sum(p[i][k] * q[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    yaw = rz_ry_rx(0.0, -math.pi / 2, 0.0)
    wm = {}
    for ry_ in (-116.8, -30.0, 45.0, 170.0):
        new = mul(yaw, rz_ry_rx(math.pi / 2, math.radians(ry_), math.pi / 2))
        old = mul(yaw, rz_ry_rx(0.0, math.radians(ry_), math.pi / 2))
        col = lambda M, j: [round(M[i][j], 3) for i in range(3)]  # noqa: E731
        wm[ry_] = (col(new, 0) == col(old, 0) and abs(col(new, 0)[2]) < 1e-3 and abs(abs(col(new, 2)[2]) - 1) < 1e-3
                   and abs(abs(col(old, 1)[2]) - 1) < 1e-3)
    log_rows = [[-1.338, 0.0, 0.677], [-0.677, 0.0, -1.338], [0.0, -1.5, 0.0]]
    old = mul(yaw, rz_ry_rx(0.0, math.radians(-116.8), math.pi / 2))
    fits = all(abs(1.5 * old[i][j] - log_rows[i][j]) < 0.01 for i in range(3) for j in range(3))
    import s3ds_effect_models as em
    check(all(wm.values()) and fits and not em.BILLBOARD_IN_CODE,
          'furiijio beam (step 2j): BeamN keeps the 3DS angles (0, a, 90), which reproduce the user\'s logged beam matrix '
          '(a -116.8, scale 1.5): %s; the planes face the camera through the effect models\' _BILLBOARDYAXIS_ bones '
          '(BILLBOARD_IN_CODE empty), no longer by the step 2g v5 turn (90, a, 90) (its maths for a %s kept as the '
          'record)' % (fits, sorted(wm)))
    outs = []
    for _ in range(27):
        (c,) = run(m, fn['fu3_up'])
        outs.append([x[2] for x in c if x[0] == 'chg'])
    check(outs[:25] == [[]] * 25 and outs[25] == [4] and m.r32(OBJ + V(1)) == 150,
          'furiijio 3 update (0x6D948): BeamN kept; V4 below 0 (26th frame) -> V1 = 150 (the cool-down), -> 4')

    # 4 beam
    m.calls = []
    m.call(fn['fu4_en'], {3: OBJ})
    fol = calls(m, 'follow')
    check([(x[2], x[3]) for x in fol] == [(0x71A0002, 2), (0x71A0004, 3), (0x71A0003, 3)] and
          [m.r32(OBJ + W.FU_E + 4 * i) for i in range(3)] == [0x7777, 0x7778, 0x7779] and
          calls(m, 'motion') == [('motion', OBJ, 7, 0.0, 1.0, 1, 0.0)] and m.r32(OBJ + V(4)) == 60 and
          calls(m, 'node_rot'),
          'furiijio 4 enter (0x6C258): IceBeamShot (loop), V4 = 60, BeamN set, follow effects 0x71A0002 (node 2), '
          '0x71A0004 / 0x71A0003 (node 3) kept')
    lens, outs = [], []
    for _ in range(62):
        (c,) = run(m, fn['fu4_up'])
        outs.append([x[2] for x in c if x[0] == 'chg'])
        lens.append((m.rf(OBJ + V(8)), [x[3] for x in c if x[0] == 'atk_offset'],
                     [x[2:] for x in c if x[0] in ('eff_scale', 'eff_pos')]))
    L1, off1, eff1 = lens[0]
    check(L1 == 4.5 and off1 == [(21.75, 0.0, 0.0)] and eff1 == [(0x7778, (0.225, 1.0, 1.0)), (0x7779, (4.5, 0.0, 0.0))]
          and lens[50][0] == 200.0 and lens[50][1] == [(315.0, 0.0, 0.0)] and outs[:60] == [[]] * 60 and
          outs[60] == [1],
          'furiijio 4 update (0x6CB80): the length +4.5 a frame up to 200; the hitbox (set_offset(0)) at (L x 1.5 + '
          '15, 0, 0), effect 0x71A0004 scaled (L x 0.05, 1, 1), 0x71A0003 at (L, 0, 0); V4 below 0 -> 1 %s' %
          (lens[0],))
    m.calls = []
    m.call(fn['fu_bexit'], {3: OBJ})
    check([x[2] for x in calls(m, 'remove_effect')] == [0x7777, 0x7778, 0x7779] and
          [m.r32(OBJ + W.FU_E + 4 * i) for i in range(3)] == [0, 0, 0],
          'furiijio 4 / 7 exit (0x6D094 / 0x6D494): the three effects removed')

    # 6 / 7 sweep
    sweeps = set()
    for seed in range(1, 12):
        m.w32(D['consts'] + 8, seed * 0x9E3779B1 & 0xFFFFFFFF)
        m.target_x, m.target_y = 60.0, 40.0
        m.call(fn['fu6_en'], {3: OBJ})
        lr = -1.0
        a = calc_angle(60.0 - 12.0, 40.0 - 27.0) * lr
        st, ry = m.rf(OBJ + V(7)), m.rf(OBJ + W.FU_ROT + 4)
        rate = 180.0 / 140
        if abs(st + rate * lr) < 1e-5 and abs(ry - (a + 90 * lr)) < 1e-3:
            sweeps.add('right')
        elif abs(st - rate * lr) < 1e-5 and abs(ry - (a - 90 * lr)) < 1e-3:
            sweeps.add('left')
        else:
            sweeps.add('bad %g %g' % (st, ry))
    check(sweeps == {'left', 'right'} and m.r32(OBJ + V(4)) == 25,
          'furiijio 6 enter (0x6D624): step 180 / 140 x lr, random(0, 1) < 1: the step negated and the start a lr + '
          '90 lr, else a lr - 90 lr; then as 3 %s' % sorted(sweeps))
    m.call(fn['fu7_en'], {3: OBJ})
    r0 = m.rf(OBJ + W.FU_ROT + 4)
    st = m.rf(OBJ + V(7))
    outs = []
    for _ in range(141):
        (c,) = run(m, fn['fu7_up'])
        outs.append([x[2] for x in c if x[0] == 'chg'])
    check(m.r32(OBJ + V(4)) == 0xFFFFFFFF and outs[140] == [1] and outs[:140] == [[]] * 140 and
          abs(m.rf(OBJ + W.FU_ROT + 4) - (r0 + 140 * st)) < 1e-2 and m.rf(OBJ + V(8)) == 200.0,
          'furiijio 7 (0x6C980 / 0x6CE24): 140 frames, the angle stepping 180 degrees, the beam as in 4, -> 1')

    # 8 leave, 9 dead
    m = Machine(img)
    m.flier(c0, kind=0x1A, state=8)
    m.call(fn['fu8_en'], {3: OBJ})
    check(calls(m, 'motion') == [('motion', OBJ, 7, 0.0, 0.0, 0, 0.0)] and m.r32(OBJ + V(6)) == 200 and
          calls(m, 'follow') and calls(m, 'follow')[0][2:4] == (0x8000005, 0) and calls(m, 'follow')[0][4] ==
          (0.0, 5.0, 0.0) and [x[2] for x in calls(m, 'kinetic')] == [15],
          'furiijio 8 (leave, 0x6C058): IceBeamShot at rate 0, init_common_leave(P6: 200 frames, effect 0x8000005 '
          'at (0, 5, 0) x 1, kinetic 15)')
    m = Machine(img)
    m.flier(c0, kind=0x1A, state=9)
    m.call(fn['fu9_en'], {3: OBJ})
    check(m.r32(OBJ + W.AER + 0xC) == 0xFFFFFFFF and calls(m, 'motion') == [('motion', OBJ, 2, 0.0, 0.0, 0, 0.0)]
          and calls(m, 'bullet') and m.r32(OBJ + W.DEFEATED) == 1,
          'furiijio 9 (dead, 0x6C0AC): set_mode_none, DamageStart at rate 0, bullet(), defeated')

    # slots
    m = Machine(img)
    m.flier(c0, kind=0x1A, state=1)
    m.w32(OBJ + V(2), 3)
    m.call(slot(10), {3: OBJ})
    check(m.r32(OBJ + V(2)) == 900 and calls(m, 'bi_damage'),
          'furiijio slot 10 (notify_on_damage, the 3DS\'s 11 0x6CB64): V2 = 900, then BehaviorImpl\'s')
    m.calls = []
    m.call(slot(61), {3: OBJ})
    m.call(slot(62), {3: OBJ})
    check([x[2] for x in calls(m, 'kinetic')] == [26, 26], 'furiijio slots 61 / 62 (0x6D910 / 0x6DC58): kinetic 26')
    got = {}
    for sid in (1, 3, 4, 7):
        m.flier(c0, kind=0x1A, state=sid)
        m.calls = []
        m.call(slot(4), {3: OBJ})
        got[sid] = [x[0] for x in m.calls if x[0] in ('bi_skip', 'node_rot', 'atk_offset')]
    check(got == {1: ['bi_skip'], 3: ['bi_skip', 'node_rot'], 4: ['bi_skip', 'node_rot', 'atk_offset'],
                  7: ['bi_skip', 'atk_offset', 'node_rot']},
          'furiijio slot 4 (update_on_skip, 0x6C438): BehaviorImpl\'s, then BeamN / the beam set up again %s' % got)
