#!/usr/bin/env python3
"""Step 2g: Propeller Heiho's checks (tools/smashrun_walker_cave.py, FLIERS 'propellerheiho'; docs/smash-run-port.md,
"Step 2g"). Run by tools/smashrun_flier_test.py (its Machine, with the item / ray / camera / random stubs):

  python3 tools/smashrun_flier_test.py PATCHED.rpx

Checks its vtable (slots 10 / 27 / 41 / 55 / 59 / 69), slots 64-67, change_state over its 3DS table, set_attack_data
(P2 entry 0 in 3 only), its CFG P words (the 3DS P0 row), start (the item picked: the three kinds' chances, created,
held: create_item + have(0x50000000, 0, -1, 0, 0) + the id), the hold (slot 59: warp to HipN + (0, -10, 0)), the swap
and the drop (slot 55), the drop on damage (slot 10), the removal (slot 27), set_mode_normal / set_max_speed, every
state's enter / update against the 3DS sequences (enemy_fs.cro addresses in the messages).
"""
import math
import struct

import smashrun_walker_cave as W
import smashrun_walker_test as T
from smashrun_walker_test import OBJ, ACC, POSTURE, R, check

NONE = 0x50000000


def propellerheiho(img, D, fn, c0, vtw, Machine, calls, run):
    import smashrun_flier_test as FT
    w = [x for x in W.FLIERS if x['name'] == 'propellerheiho'][0]
    vk = [img.u32(D['vt_propellerheiho'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    vtf = [img.u32(D['vtf'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    diff = sorted(k for k in range(76) if vk[(0xC + 8 * k) // 4] != vtf[(0xC + 8 * k) // 4])
    check(diff == [55, 59] and vk[(0xC + 8 * 55) // 4] == fn['f_ph_55'] and vk[(0xC + 8 * 59) // 4] == fn['f_ph_59'],
          'propellerheiho: its vtable = VTF but slots 55 (after the state update) and 59 (every frame) %s' % diff)
    check([img.u32(c0 + W.CF[k]) for k in ('FSTART', 'FDMG', 'F69', 'F27')] ==
          [fn['f_ph_start'], fn['f_ph_dmg'], fn['f_ph_69'], fn['f_ph_rm']],
          'propellerheiho: CFG handlers start 0x99010, damage (slot 10 = 3DS 11, 0x9A330), slot 69 0x9AA1C, '
          'remove (slot 27)')
    slot = lambda k: vk[(0xC + 8 * k) // 4]  # noqa: E731
    P = lambda i: img.u32(c0 + W.P(i))  # noqa: E731
    Pf = lambda i: struct.unpack('>f', struct.pack('>I', P(i)))[0]  # noqa: E731
    p0 = W.vl_group('propellerheiho', 0)[0]
    check([P(i) for i in range(33)] == [W.word(v) for v in p0] and Pf(7) == -10.0 and P(8) == 60 and
          Pf(9) == 10.0 and Pf(10) == 20.0 and P(26) == 100 and Pf(25) == 10.0 and P(24) == 180,
          'propellerheiho: CFG P0-32 = the 3DS P0 row (P@0x1C -10 item y, 0x20 60 swap, 0x24 / 0x28 10 / 20 %%, '
          '0x60 180, 0x64 10 %%, 0x68 100)')
    m = Machine(img)
    got = []
    for k in (64, 65, 66, 67):
        m.flier(c0, kind=0x47)
        m.call(slot(k), {3: OBJ})
        got.append(m.uc.reg_read(R[3]))
    check(got == [4, 4, 4, 3], 'propellerheiho: slots 64-67 = the 3DS\'s 4 / 4 / 4 / 3 %s' % got)
    tab = img.u32(c0 + W.CF['TAB']) + 0x18
    ok = True
    for sid in range(1, 9):
        row = [img.u32(tab + 0x18 * (sid - 1) + 4 * i) for i in range(6)]
        s = w['states'][sid]
        want = ([0xFFFF, W.ZIMA_REMOVE_ENTER, 0xFFFF, W.ZIMA_REMOVE_UPDATE, 0, 0] if s == 'remove' else
                [0xFFFF, fn[s[0]], 0xFFFF, fn[s[1]], 0, 0])
        ok = ok and row == want
    check(ok, 'propellerheiho: its table 1 turn, 2 fly away, 3 dead, 4 height, 5 patrol, 6 brake, 7 stun, 8 remove '
          '(0x111278)')
    arm = {}
    for sid in range(0, 9):
        m = Machine(img)
        m.flier(c0, kind=0x47)
        m.call(slot(45), {3: OBJ, 4: sid})
        arm[sid] = [x[2] for x in calls(m, 'atk_create')]
    vl = W.vl_group('propellerheiho', 2)
    want = {sid: [] for sid in range(9)}
    want[3] = [D['ph_bullet']]
    words = [img.u32(D['ph_bullet'] + 4 * i) for i in range(len(vl[0]))]
    check(arm == want and words == [W.word(v) for v in vl[0]],
          'propellerheiho: set_attack_data arms P2 entry 0 in 3 only (power 2, angle 361, kbg 100, bkb 50, size 2, '
          'node 2): no contact hitbox while it flies')

    def mk(state=0, lr=1.0, x=0.0, y=0.0):
        m = Machine(img)
        m.flier(c0, state=state, kind=0x47, lr=lr)
        m.wf(POSTURE + 0x10, x)
        m.wf(POSTURE + 0x14, y)
        m.w32(OBJ + W.PH_I, NONE)
        return m

    def held(m, kind=0x0E):
        """an item held (as ph_pick leaves it)"""
        n = len(m.items)
        it = FT.ITEMS + 0x40 * n
        m.w32(it, 0x1000 + n)
        m.w32(it + 4, kind)
        m.w32(it + 0x24, FT.IVT)
        m.items[0x1000 + n] = it
        m.w32(OBJ + W.PH_I, 0x1000 + n)
        return it

    aer = OBJ + W.AER

    def amode():
        return (m.r32(aer + 0xC),) + tuple(round(m.rf(aer + o), 4) for o in range(0x10, 0x28, 4)) + \
            (round(m.rf(FT.FEN0 + 0x38), 4), round(m.rf(FT.FEN0 + 0x3C), 4), m.r32(FT.FEN0 + 0x18) >> 24,
             m.r32(FT.FEN1 + 0x18) >> 24)

    # start
    m = mk(lr=-1.0, x=5.0, y=7.0)
    m.target, m.target_x = 2, 50.0
    m.success = [1]
    m.call(fn['f_ph_start'], {3: OBJ})
    ci = calls(m, 'create_item')
    hv = calls(m, 'item_have')
    check(calls(m, 'aer_ctor') == [('aer_ctor', aer, ACC)] and calls(m, 'rhombus') == [('rhombus', OBJ)] and
          calls(m, 'reverse_lr') and m.rf(OBJ + 0x10) == 1.0 and
          ci == [('create_item', OBJ, 0x21, 0, (5.0, 7.0, 0.0), (0.0, 0.0, 0.0), 1)] and
          hv == [('item_have', FT.ITEMS, NONE, 0, 0xFFFFFFFF, 0, 0)] and calls(m, 'item_id') and
          m.r32(OBJ + W.PH_I) == 0x1000 and m.r32(OBJ + W.PH_S) == 60 and m.r32(OBJ + W.PH_DT) == 100 and
          m.r32(OBJ + W.PH_X) == 0 and [x[2] for x in calls(m, 'chg')] == [4] and
          [x[1] for x in calls(m, 'success')] == [10.0],
          'propellerheiho start (0x99010): aerial module, set_rhombus, +0x10 = lr (-1), turned to the nearest (1), the item '
          '(0x5A6F0): success_by_percent(10) -> customizeitem 0x21: create_item(0x21, 0, posture, 0, 1) + have('
          '0x50000000, 0, -1, 0, 0) (= create_item_and_have 0x7B4104) -> its id; swap 60, drop 100, -> 4')
    m = mk()
    m.success = [0, 1]
    m.call(fn['f_ph_start'], {3: OBJ})
    k1 = [(x[2], x[3]) for x in calls(m, 'create_item')]
    sp = [x[1] for x in calls(m, 'success')]
    kinds, vars_ = set(), set()
    for seed in range(1, 60):
        m = mk()
        m.w32(D['consts'] + 8, seed * 0x9E3779B1 & 0xFFFFFFFF)
        m.call(fn['f_ph_start'], {3: OBJ})
        for x in calls(m, 'create_item'):
            kinds.add(x[2])
            vars_.add(x[3])
    check(k1 == [(0x1D, 0)] and sp == [10.0, 20.0] and kinds == {0x0E} and min(vars_) >= 0 and max(vars_) <= 28 and
          len(vars_) > 15,
          'propellerheiho item: else success_by_percent(20) -> goldbag 0x1D; else tabemono 0x0E, variation '
          'random(0, 28) (%d seen)' % len(vars_))
    m = mk()
    m.create_fail = True
    m.call(fn['f_ph_start'], {3: OBJ})
    check(m.r32(OBJ + W.PH_I) == NONE and not calls(m, 'item_have'),
          'propellerheiho item: create_item fails -> none held (0x50000000)')

    # slot 59: the hold
    m = mk(state=4)
    it = held(m)
    m.node3 = (11.0, 31.0, 4.0)
    m.call(slot(59), {3: OBJ})
    check(calls(m, 'node_gpos') == [('node_gpos', FT.MODEL, 3, 1)] and
          calls(m, 'warp') == [('warp', it, (11.0, 21.0, 0.0))],
          'propellerheiho slot 59 (0x9A224, every frame): the held item warped to node 3 (HipN)\'s global position '
          '+ (0, P7 -10, 0), z 0 (Item::warp)')
    m.w32(OBJ + W.PH_X, 1)
    m.calls = []
    m.call(slot(59), {3: OBJ})
    m2 = mk(state=4)
    m2.call(slot(59), {3: OBJ})
    check(not calls(m, 'warp') and not calls(m2, 'warp'), 'propellerheiho slot 59: dropped or none held: no warp')

    # slot 55: the swap and the drop
    m = mk(state=4)
    it = held(m)
    m.w32(OBJ + W.PH_S, 1)
    m.node3 = (0.0, 30.0, 0.0)
    m.success = [0, 0]
    m.call(slot(55), {3: OBJ})
    eff = calls(m, 'effect')
    new = calls(m, 'create_item')
    check(calls(m, 'item_remove') == [('item_remove', it, 0)] and new and m.r32(OBJ + W.PH_I) == 0x1001 and
          m.r32(OBJ + W.PH_S) == 60 and eff and eff[0][2] == 0x100001C and eff[0][3] == (0.0, 25.0, 5.0),
          'propellerheiho slot 55 (0x99E24) in 4: the swap timer at 0 -> the item removed (vt slot 81), a new one '
          'picked (0x5A6F0), swap 60, effect 0x100001C at the item ((0, 5, 5) for tabemono) %s' % (eff,))
    m = mk(state=5)
    held(m, kind=0x1D)
    m.w32(OBJ + W.PH_S, 1)
    m.success = [0, 1]
    m.call(slot(55), {3: OBJ})
    eff = calls(m, 'effect')
    check(eff and eff[0][3] == (-5.0, 15.0, 0.0), 'propellerheiho slot 55 in 5: the swap effect at (-5, 5, 0) from '
          'the item (goldbag) %s' % (eff,))
    m = mk(state=4)
    it = held(m, kind=0x21)
    m.w32(OBJ + W.PH_S, 5)
    m.w32(OBJ + W.PH_DT, 1)
    m.success = [1]
    m.call(slot(55), {3: OBJ})
    check(m.r32(OBJ + W.PH_S) == 4 and calls(m, 'success') == [('success', 10.0)] and
          calls(m, 'fall') == [('fall', it, 1.0, (0.0, 0.0, 0.0))] and m.r32(OBJ + W.PH_I) == NONE and
          m.r32(OBJ + W.PH_X) == 1 and [x[2] for x in calls(m, 'chg')] == [5],
          'propellerheiho slot 55: else the drop timer at 0 and success_by_percent(P25 10) -> Item::fall(1, ZERO), '
          'none held, dropped, -> 5')
    m = mk(state=5)
    it = held(m)
    m.w32(OBJ + W.PH_S, 5)
    m.w32(OBJ + W.PH_DT, 1)
    m.success = [1]
    m.call(slot(55), {3: OBJ})
    f1 = calls(m, 'fall')
    m2 = mk(state=5)
    held(m2)
    m2.w32(OBJ + W.PH_S, 5)
    m2.w32(OBJ + W.PH_DT, 1)
    m2.call(slot(55), {3: OBJ})
    check(f1 == [('fall', it, 0.0, (0.0, 0.0, 0.0))] and m.r32(OBJ + W.PH_T) == 60 and not calls(m, 'chg') and
          not calls(m2, 'fall') and m2.r32(OBJ + W.PH_DT) == 180,
          'propellerheiho slot 55: tabemono falls with 0; in 5 PH_T = P32 60 (no change); a failed roll -> drop timer '
          'P24 180')
    got = []
    for st_, x_ in ((3, 0), (7, 0), (4, 1)):
        m = mk(state=st_)
        held(m)
        m.w32(OBJ + W.PH_X, x_)
        m.w32(OBJ + W.PH_S, 1)
        m.call(slot(55), {3: OBJ})
        got.append(bool(calls(m, 'create_item')) or m.r32(OBJ + W.PH_S) != 1)
    check(got == [False] * 3, 'propellerheiho slot 55: nothing outside 4 / 5 or once dropped %s' % got)

    # slot 10: a held item falls on any damage; 69; 27
    m = mk(state=5)
    it = held(m, kind=0x1D)
    m.call(fn['f_ph_dmg'], {3: OBJ})
    seq = [x[0] for x in m.calls if x[0] in ('bi_damage', 'fall')]
    m2 = mk(state=5)
    held(m2)
    m2.w32(OBJ + W.PH_X, 1)
    m2.call(fn['f_ph_dmg'], {3: OBJ})
    check(seq == ['bi_damage', 'fall'] and calls(m, 'fall')[0][1:3] == (it, 1.0) and m.r32(OBJ + W.PH_X) == 1 and
          m.r32(OBJ + W.PH_I) == NONE and not calls(m2, 'fall') and calls(m2, 'bi_damage'),
          'propellerheiho slot 10 (notify_on_damage 0x9A330): BehaviorImpl\'s, then a held item falls (the killing '
          'blow too: the item drops on defeat), dropped')
    m = mk(state=5)
    m.call(fn['f_ph_69'], {3: OBJ})
    check([x[2] for x in calls(m, 'chgi')] == [7] and m.uc.reg_read(R[3]) == 1,
          'propellerheiho slot 69 (0x9AA1C): => 7 (stun), returns 1')
    m = mk(state=2)
    it = held(m)
    m.call(fn['f_ph_rm'], {3: OBJ, 4: 3})
    seq = [x for x in m.calls if x[0] in ('item_remove', 'bi_remove')]
    check(seq == [('item_remove', it, 0), ('bi_remove', OBJ)] and m.r32(OBJ + W.PH_I) == NONE,
          'propellerheiho slot 27 (the dtors 0x9AC10 / 0x9AC74): a held item removed (vt slot 81), then '
          'BehaviorImpl\'s')

    # 1 turn
    m = mk(state=1)
    m.call(fn['ph1_en'], {3: OBJ})
    check(amode() == (0, 0.0, 0.0, 0.1, 0.1, 10.0, 10.0, 10.0, 10.0, 1, 0) and calls(m, 'einit') and
          calls(m, 'einit')[0][2] == 0x17 and calls(m, 'motion') == [('motion', OBJ, 2, 0.0, 1.0, 0, 0.0)] and
          ('attach', T.GROUND, 0) in calls(m, 'attach') and calls(m, 'passable'),
          'propellerheiho 1 enter (0x99598): set_mode_normal(0, 0, 0.1, 0.1, 10, 10) (0x5F5A9C: mode 0, energy 0 '
          'init 0x17, on; energy 1 off; max 10 / 10), ground off, passable, TurnAir once %s' % (amode(),))
    (c,) = run(m, fn['ph1_up'])
    check([x for x in c if x[0] == 'aer_update_xy'] == [('aer_update_xy', aer, 0.0, 0.0, 0)],
          'propellerheiho 1 update (0x99D64): update(0, 0, 0)')
    m.motion_end = True
    (c,) = run(m, fn['ph1_up'])
    check([x[0] for x in c if x[0] in ('reverse_lr', 'chgi')] == ['reverse_lr', 'chgi'] and
          [x[2] for x in c if x[0] == 'chgi'] == [4] and m.r32(OBJ + W.PH_R) == 1,
          'propellerheiho 1: at the end reverse_lr(1, 1), turned = 1, => 4')

    # 2 fly away
    m = mk(state=2)
    m.call(fn['ph2_en'], {3: OBJ})
    check(amode() == (0, 0.0, 0.05, 0.0, 0.0, 0.0, 4.0, 0.0, 4.0, 1, 0) and m.rf(OBJ + W.PH_D) == 1.0 and
          m.r32(OBJ + W.PH_B) == 0 and calls(m, 'set_speed') == [('set_speed', aer, 0.0, 0.0)] and
          calls(m, 'set_correct') == [('set_correct', T.GROUND, 0)] and
          calls(m, 'motion') == [('motion', OBJ, 3, 0.0, 2.0, 1, 0.0)] and m.r32(OBJ + W.PH_F) == 300,
          'propellerheiho 2 enter (0x99440): set_mode_normal(0, P28 0.05, 0, 0, 10, 10), set_max_speed(0, P29 4), '
          'dir 1, brake 0, speed (0, P27 0), set_correct(0), Vertical loop at P31 2, 300 frames %s' % (amode(),))
    (c,) = run(m, fn['ph2_up'])
    check([x for x in c if x[0] == 'aer_update_xy'] == [('aer_update_xy', aer, 0.0, 1.0, 0)] and
          calls(m, 'in_view') and m.r32(OBJ + W.PH_F) == 299,
          'propellerheiho 2 update (0x99CC4): in view -> update(0, 1, 0)')
    m.view = 0
    (c,) = run(m, fn['ph2_up'])
    m.view = 1
    m.w32(OBJ + W.PH_F, 1)
    (c2,) = run(m, fn['ph2_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [8] and [x[2] for x in c2 if x[0] == 'chg'] == [8] and
          not calls(m, 'in_view'),
          'propellerheiho 2: out of view (is_in_view_area 0x9EA804 = CameraModule is_clip_in(1)) or 300 frames -> 8 '
          '(removed)')

    # 3 dead
    m = mk(state=3)
    m.call(fn['ph3_en'], {3: OBJ})
    check(calls(m, 'kinetic') == [('kinetic', T.EKIN, 23)] and ('attach', T.GROUND, 0) in calls(m, 'attach') and
          calls(m, 'passable') == [('passable', T.GROUND, 0)] and calls(m, 'bullet') and
          m.r32(OBJ + W.DEFEATED) == 1,
          'propellerheiho 3 enter (0x99624): kinetic 23, ground off, passable off, bullet() (P2 entry 0), defeated')
    m.w32(T.FLAGS, 8)
    (c,) = run(m, fn['ph3_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [8], 'propellerheiho 3 update (0x9A2F8): kinetic flag 8 -> 8')

    # 4 height
    m = mk(state=4, y=10.0)
    m.target, m.target_y = 1, 50.0
    m.call(fn['ph4_en'], {3: OBJ})
    check(amode() == (0, 0.0, 0.0, 0.0, 0.0, 10.0, 10.0, 10.0, 10.0, 1, 0) and m.r32(OBJ + W.PH_T) == 120 and
          m.rf(OBJ + W.PH_D) == 1.0 and calls(m, 'set_speed') == [('set_speed', aer, 0.0, 1.0)] and
          calls(m, 'motion') == [('motion', OBJ, 3, 0.0, 1.0, 1, 0.0)] and not calls(m, 'chg'),
          'propellerheiho 4 enter (0x9A578): set_mode_normal(0 x 4, 10, 10), Vertical loop, 120 frames, the target '
          'above -> dir 1, speed (0, P12 1 x dir)')
    m2 = mk(state=4, y=60.0)
    m2.target, m2.target_y = 1, 50.0
    m2.call(fn['ph4_en'], {3: OBJ})
    m3 = mk(state=4, y=51.0)
    m3.target, m3.target_y = 1, 50.0
    m3.call(fn['ph4_en'], {3: OBJ})
    m4 = mk(state=4)
    m4.target = 0xFFFFFFFF
    m4.call(fn['ph4_en'], {3: OBJ})
    check(m2.rf(OBJ + W.PH_D) == -1.0 and calls(m2, 'set_speed')[0][3] == -1.0 and
          [x[2] for x in calls(m3, 'chg')] == [5] and calls(m4, 'set_speed') == [('set_speed', aer, 0.0, 0.0)],
          'propellerheiho 4 enter: below -> dir -1; within P14 3 -> 5; no target -> speed (0, 0)')
    m.ground = False
    (c,) = run(m, fn['ph4_up'])
    check([x for x in c if x[0] == 'aer_update_xy'] == [('aer_update_xy', aer, 0.0, 1.0, 0)] and
          not [x for x in c if x[0] == 'ray'] and m.r32(OBJ + W.PH_T) == 119,
          'propellerheiho 4 update (0x9A6F8): rising, the target far: update(0, dir, brake)')
    m.target_y = 12.0
    (c,) = run(m, fn['ph4_up'])
    m.target_x = 50.0
    m.wf(POSTURE + 0x60, -1.0)
    (c2,) = run(m, fn['ph4_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [5] and [x[2] for x in c2 if x[0] == 'chg'] == [1],
          'propellerheiho 4: at the target\'s height (y > ty - 3 rising): the nearest on the facing side -> 5, '
          'else -> 1 (turn; get_lr_to_nearest_target 0x9EB178)')
    m = mk(state=4, y=30.0)
    m.ground = False
    m.target, m.target_y = 1, -100.0
    m.wf(OBJ + W.PH_D, -1.0)
    m.w32(OBJ + W.PH_T, 50)
    m.ray_hit = 20.0
    (c,) = run(m, fn['ph4_up'])
    ray = [x for x in c if x[0] == 'ray']
    check(ray == [('ray', T.GROUND, (0.0, 30.0), (0.0, -50.0), 1)] and m.rf(OBJ + W.PH_D) == 1.0 and
          [x[2] for x in c if x[0] == 'chg'] == [5],
          'propellerheiho 4: descending, get_height_from_ground (0x7B4C68: ray_check(pos, (0, -50), 1) -> y - hit '
          '10) below 5 - P7 = 15 -> dir 1, -> 5 %s' % (ray,))
    m.ray_hit = None
    m.wf(OBJ + W.PH_D, -1.0)
    (c,) = run(m, fn['ph4_up'])
    check([x for x in c if x[0] == 'aer_update_xy'] == [('aer_update_xy', aer, 0.0, -1.0, 0)],
          'propellerheiho 4: no ground within 50 -> keeps descending')
    m.w32(OBJ + W.PH_T, 1)
    m.w32(OBJ + W.PH_R, 1)
    (c,) = run(m, fn['ph4_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [5], 'propellerheiho 4: 120 frames, already turned -> 5')

    # 5 patrol
    m = mk(state=5, y=40.0, lr=1.0)
    m.call(fn['ph5_en'], {3: OBJ})
    pt = m.r32(OBJ + W.PH_T)
    check(amode()[0] == 0 and m.r32(OBJ + W.PH_A) == 0 and m.r32(OBJ + W.PH_B) == 1 and m.rf(OBJ + W.PH_Y) == 40.0
          and calls(m, 'motion') == [('motion', OBJ, 1, 0.0, 0.5, 1, 0.0)] and 150 <= pt <= 450 and
          m.r32(OBJ + W.PH_DT) == 180,
          'propellerheiho 5 enter (0x991D4): set_mode_normal, bob 0, brake 1, Move loop at P23 0.5, random(150, '
          '450) frames (%d), drop timer 180' % pt)
    m2 = mk(state=5)
    m2.w32(OBJ + W.PH_X, 1)
    m2.call(fn['ph5_en'], {3: OBJ})
    check(m2.r32(OBJ + W.PH_T) == 60, 'propellerheiho 5 enter: dropped -> P32 60 frames')
    m.ground = False
    (c,) = run(m, fn['ph5_up'])
    vy = math.cos(3 * math.pi / 180) * 100 * 3.6 / 360
    ss = [x for x in c if x[0] == 'set_speed']
    up = [x for x in c if x[0] == 'aer_update_xy']
    check(m.r32(OBJ + W.PH_A) == 3 and ss and ss[0][2] == 0.5 and abs(ss[0][3] - vy) < 1e-3 and
          up == [('aer_update_xy', aer, 1.0, 1.0, 0)],
          'propellerheiho 5 update (0x99848): the bob angle += 360 / P17 (3), speed (P15 0.5 x move x, cos x P16 x '
          '3.6 / 360), dir = vy >= 0, update(move x, dir, 0) %s' % (ss,))
    m.w32(OBJ + W.PH_A, 357)
    run(m, fn['ph5_up'])
    check(m.r32(OBJ + W.PH_A) == 0, 'propellerheiho 5: the angle wraps at 360 (int(357 + 3.6) = 360 -> 0)')
    m.w32(OBJ + W.PH_A, 150)
    m.ground = True
    m.speed(0.0, -0.5)
    (c,) = run(m, fn['ph5_up'])
    ray = [x for x in c if x[0] == 'ray']
    check(m.r32(OBJ + W.PH_A) == 270 and m.rf(OBJ + W.PH_Y) == -10.0 and m.rf(OBJ + W.PH_D) == 0.0 and
          ray == [('ray', T.GROUND, (0.0, 40.0), (0.0, -50.0), 0)],
          'propellerheiho 5: sinking (vy < 0: height_from_ground(0) checked) on the ground with cos < 0 -> angle '
          '270, y ref = y - P16 / 2; dir = (vy >= 0) = 0 %s' % (ray,))
    m.ground = False
    m.walls = {1}
    m.speed(0.0, 0.5)
    m.w32(OBJ + W.PH_A, 10)
    (c,) = run(m, fn['ph5_up'])
    check(m.r32(OBJ + W.PH_A) == 90 and m.rf(OBJ + W.PH_Y) == 90.0 and m.rf(OBJ + W.PH_D) == 1.0,
          'propellerheiho 5: a ceiling while cos > 0 -> angle 90, y ref = y + P16 / 2')
    m.walls = set()
    m.wall = 1
    (c,) = run(m, fn['ph5_up'])
    m.wall = 0
    check([x[2] for x in c if x[0] == 'chg'] == [1], 'propellerheiho 5: check_wall -> 1 (turn)')
    m.w32(OBJ + W.PH_T, 1)
    m.target, m.target_y = 1, 200.0
    (c,) = run(m, fn['ph5_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [4] and m.r32(OBJ + W.PH_R) == 0,
          'propellerheiho 5: time up, the nearest more than P11 60 away in y -> 4, turned 0')
    m.w32(OBJ + W.PH_T, 1)
    m.target_y = 30.0
    (c,) = run(m, fn['ph5_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [6] and 150 <= m.r32(OBJ + W.PH_T) <= 450,
          'propellerheiho 5: time up, the nearest close in y -> random(150, 450), -> 6 (brake)')
    m.w32(OBJ + W.PH_T, 1)
    m.w32(OBJ + W.PH_X, 1)
    (c,) = run(m, fn['ph5_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [2], 'propellerheiho 5: time up after the drop -> 2 (fly away)')

    # 6 brake
    m = mk(state=6)
    m.vx, m.vy = 2.0, 0.05
    m.call(fn['ph6_en'], {3: OBJ})
    check(amode()[:7] == (0, 0.0, 0.0, 1.0, 0.05, 10.0, 10.0) and
          calls(m, 'set_speed') == [('set_speed', aer, 2.0, 0.05)] and m.r32(OBJ + W.PH_B) == 1 and
          calls(m, 'motion') == [('motion', OBJ, 1, 0.0, 1.0, 1, 0.0)],
          'propellerheiho 6 enter (0x9934C): set_mode_normal(0, 0, P21 x |vx| / max(|vy|, 0.1), P21, 10, 10), the '
          'speed kept, brake 1, Move loop %s' % (amode(),))
    (c,) = run(m, fn['ph6_up'])
    check([x for x in c if x[0] == 'aer_update_xy'] == [('aer_update_xy', aer, 1.0, 0.0, 1)],
          'propellerheiho 6 update (0x99BD0): moving -> update(move x, dir, 1)')
    m.vx, m.vy = 0.05, 0.0
    m.success = [1]
    (c,) = run(m, fn['ph6_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [2] and [x[1] for x in c if x[0] == 'success'] == [100.0],
          'propellerheiho 6: stopped (|v|^2 < 0.01), success_by_percent(P22 100) -> 2 (fly away)')
    m.target, m.target_x = 1, 50.0
    (c,) = run(m, fn['ph6_up'])
    m.target_x = -50.0
    (c2,) = run(m, fn['ph6_up'])
    check([x[2] for x in c if x[0] == 'chg'] == [4] and [x[2] for x in c2 if x[0] == 'chg'] == [1],
          'propellerheiho 6: a failed roll -> the nearest on the facing side => 4, else => 1')

    # 7 stun
    m = mk(state=7)
    m.w32(FT.PMGR + W.GL_INDEX + 4 * (8 * 0x47), 2)          # its gl entry: the test's (+0x154 30)
    m.call(fn['ph7_en'], {3: OBJ})
    seq = [x[0] for x in m.calls if x[0] in ('motion', 'kinetic', 'attach', 'damage_turn', 'hit_factor')]
    check(seq == ['motion', 'kinetic', 'attach', 'damage_turn', 'hit_factor'] and
          calls(m, 'motion') == [('motion', OBJ, 0, 0.0, 1.0, 0, 0.0)] and
          calls(m, 'kinetic') == [('kinetic', T.EKIN, 16)] and m.r32(OBJ + W.PH_T) == 30 and
          m.r32(T.FLAGS) & 0x80,
          'propellerheiho 7 enter (0x99148): Damage once, kinetic 16, ground off, damage_turn() (0x7B0814 = Wii U '
          '0x02DB4E84), hit_return_frame(), kinetic flag 0x80')
    m.ground = False
    (c,) = run(m, fn['ph7_up'])
    check(m.r32(OBJ + W.PH_T) == 29 and not [x for x in c if x[0] == 'chgi'] and not calls(m, 'clear_speed'),
          'propellerheiho 7 update (0x99674): counting, move(ai)')
    m.ground = True
    m.w32(OBJ + W.PH_T, 0)
    (c,) = run(m, fn['ph7_up'])
    check([x[0] for x in c if x[0] in ('clear_speed', 'chgi')] == ['clear_speed', 'chgi'] and
          [x[2] for x in c if x[0] == 'chgi'] == [4] and not (m.r32(T.FLAGS) & 0x80),
          'propellerheiho 7: on the ground clear_speed_all; below 0 -> flag 0x80 off, => 4')
