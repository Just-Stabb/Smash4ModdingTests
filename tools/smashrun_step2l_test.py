#!/usr/bin/env python3
"""Behaviour tests of step 2l (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2l") on a patched
executable, in unicorn (smashrun_step2k_test.py's machine), every expected value from the 3DS code / files:

  python3 tools/smashrun_step2l_test.py PATCHED.rpx FS_DIR [ENEMY_SRC [SM_DIR]]

  FS_DIR: the converted 3DS param/enemy/fs (the kinds' enemy_param_vl_<kind>.bin);
  ENEMY_SRC: the 3DS enemy/ folder (s3ds_unpack extract: enemy/<kind>/model/body/c00/normal.bch, model.jtb) for the
  hurtboxes' node -> bone check.

- Waddle Doo: the hit effect's handle in its own field (DO_FX, the 3DS +0x1A0): a hit no longer sets the landing's
  hop flag V8, so the landing (2, g_landt_up) still turns to a target behind it;
- every walker / flier kind's own param object (slot[K] on a Smash Run stage): its P3 (hurtboxes) / P4 (ground box) /
  P5 (areas) equal the kind's vl groups 3 / 4 / 5 word for word, the other members their 3DS offsets; with ENEMY_SRC
  each hurtbox's node is a bone of the kind's skeleton through its model.jtb (as the converter writes them);
- Waddle Dee's parasol: the drop (slots 69 / 71: var 0 / 1 -> + 2, generate_article(0, false), once), the article set
  {0xAD, 1, wd_para_cb} written by the T hook, the spawner's activate param (3DS 0x7C778), and the Wii U's own parasol
  init (weapon kind 0xAD, 0x0319F3FC = the 3DS's 0xADF64) run on the Dee's param object;
- Lethinium: mczakoplasmawisp's state 2 update through pw2_up (no Fortress-only forced level-2 attack for kind
  0x12); with SM_DIR (the Wii U param/enemy/sm) its remapped param file's +0x134 word = the 3DS search_interval(1).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
import smashrun_step2k_test as K2  # noqa: E402
import smashrun_twin_params as TP  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402

check = T.check
OBJ, ACC, POSTURE, GROUND, HEAP = T.OBJ, T.ACC, T.POSTURE, T.GROUND, T.HEAP
ACCW, MDL, WX, VTB = HEAP + 0x30000, HEAP + 0x32000, HEAP + 0x32100, HEAP + 0x32400
M1, M2, M3 = HEAP + 0x32200, HEAP + 0x32210, HEAP + 0x32220


def fl(w):
    return struct.unpack('>f', struct.pack('>I', w))[0]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    fsdir = sys.argv[2]
    src = sys.argv[3] if len(sys.argv) > 3 else None
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    H.M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    want = {A.h.base + 4 * i: x for i, x in enumerate(A.h.words())}
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'region H: the step 2l code to 0x%08X is in the executable %s' % (A.h.pc, bad[:4]))
    byname = {w['name']: w for w in W.WALKERS}
    cfgs = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    vslot = lambda n, k: img.u32(img.u32(cfgs[n] + W.CF['VT']) + 0xC + 8 * k)  # noqa: E731

    def kworld(n, state, lr=-1.0, setup=None, var=0):
        w = byname[n]
        m = K2.K(img)
        m.walker(cfgs[n], state=state, lr=lr, kind=w['kind'], var=var)
        m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x40))
        if setup:
            setup(m)
        rows = {sid: ((W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE) if s_ == 'remove' else
                      tuple(x if isinstance(x, int) else fn[x] for x in s_)) for sid, s_ in w['states'].items()}
        return T.World(m, w, rows, state, cfgs[n])

    calls = lambda wo, k: [c for e in wo.log for c in e[4] if c[0] == k]  # noqa: E731

    # ==== 1. Waddle Doo: the hit effect's handle (3DS +0x1A0) in DO_FX, not in V8 (the landing's hop flag)
    check(W.DO_FX == 0x1C8 and W.DO_FX + 4 <= img.u32(cfgs['waddledoo'] + W.CF['SIZE']) and
          W.DO_FX not in (W.DO_SC, W.DO_CD, W.DO_TK, W.DO_IX, W.DO_ANG, W.DO_AIR) and W.DO_FX >= W.OBJ_SIZE,
          'waddledoo: DO_FX 0x1C8, inside its 0x1D0 object, after the walker\'s fields and the beam\'s DO_*')
    res = {}
    for case in ('hit', 'none', 'hop'):
        def setup(m, case=case):
            m.target, m.target_x = 0, 300.0            # behind it (lr -1)
            m.w32(OBJ + W.V(8), 1 if case == 'hop' else 0)
        wo = kworld('waddledoo', 2, setup=setup)
        if case == 'hit':
            wo.m.calls = []
            wo.m.call(vslot('waddledoo', 69), {3: OBJ})
            hit = (wo.m.r32(OBJ + W.V(8)), wo.m.r32(OBJ + W.DO_FX))
        wo.run(7)
        res[case] = [c[2] for c in calls(wo, 'chg')]
    check(hit == (0, 0x5556) and res['hit'] == [4] and res['none'] == [4] and res['hop'][:1] == [3],
          'waddledoo: a hit (slot 69) keeps its effect handle in DO_FX (V8 stays 0), so the landing (2) still turns to '
          'a target behind it (=> 4) as without a hit; only a hop\'s landing (V8 = 1) walks on (=> 3): %s %s' % (hit, res))
    m = K2.K(img)
    m.walker(cfgs['waddledoo'], state=3, kind=0x19)
    m.w32(OBJ + W.DO_FX, 0x1111)
    m.w32(OBJ + W.V(8), 0)
    m.call(vslot('waddledoo', 69), {3: OBJ})
    rm = [c for c in m.calls if c[0] == 'remove_effect']
    check(rm == [('remove_effect', OBJ, 0x1111)] and m.r32(OBJ + W.DO_FX) == 0x5556 and m.r32(OBJ + W.V(8)) == 0,
          'waddledoo slot 69 (0x7E0E0): the previous effect (DO_FX) removed, the new handle in DO_FX %s' % rm)

    # ==== 2. every kind's own param object
    m = K2.K(img)
    m.stage(0x94)
    m.w32(E.PARAM_MGR, T.PM)
    m.uc.mem_write(T.PM + W.SLOTS, struct.pack('>97I', *[0x50000000 + i for i in range(0x61)]))
    m.w32(T.MGR + 0x5EC, 2)
    m.run(E.SITE_S, W.SITE_S + 4, {3: 0, 28: T.MGR, 31: 7})
    slots = {w['name']: m.r32(T.PM + W.SLOTS + 4 * w['kind']) for w in W.WALKERS}
    check(all(slots[n] == D[W.param_label(n)] for n in slots) and len(set(slots.values())) == len(slots) and
          m.r32(T.PM + W.SLOTS + 4 * W.SLOT_DONOR) == 0x50000000 + W.SLOT_DONOR,
          'S2 on a Smash Run stage: slot[K] = the kind\'s own object for all %d walker / flier kinds (none borrows '
          'mczakozima\'s slot 0x5A any more; slot 0x5A untouched)' % len(slots))
    bad, hurt, ground = [], {}, {}
    for w in W.WALKERS:
        n = w['name']
        o = D[W.param_label(n)]
        u = lambda a: img.u32(a)  # noqa: E731
        vl = open(os.path.join(fsdir, 'enemy_param_vl_%s.bin' % n), 'rb').read()
        g = TP.groups(vl)
        for i in (3, 4, 5):
            cnt, toks = g[i]                   # (a group's tokens run on into a struct that follows it)
            base = o + 0x14 * i
            esz = u(base + 4)
            words = [u(u(base + 0xC) + 4 * j) for j in range(esz * cnt // 4)]
            exp = [W.word(t.value) for t in toks][:len(words)]
            if (u(base + 8), words) != (cnt, exp) or esz != {3: 48, 4: 40, 5: 24}[i]:
                bad.append((n, i, (u(base + 4), u(base + 8)), cnt))
            if i == 3:
                hurt[n] = [(round(fl(words[12 * e + 6]), 2), words[12 * e + 7]) for e in range(cnt)]
            if i == 4:
                ground[n] = [round(fl(x), 2) if j != 5 else x for j, x in enumerate(words[:10])]
        # the other members (structs / words) at their 3DS offsets
        for mb in W.param_members(n):
            if mb['type'] == 'struct':
                got = [u(o + mb['offset'] + 4 * j) for j in range(len(mb['values'][0]))]
                if got != [W.word(v) for v in mb['values'][0]]:
                    bad.append((n, hex(mb['offset'])))
    check(not bad, 'every kind\'s param object: P3 (hurtboxes) / P4 (ground box) / P5 (areas) = its vl groups 3 / 4 / 5 '
          '(elem size, count, every word), the structs at their 3DS offsets %s' % bad[:4])
    print('      hurtboxes (radius, node):', hurt)
    print('      ground boxes:', {k: v[:5] + [v[9]] for k, v in ground.items()})
    check(hurt['kuribo'] == [(8.0, 4)] and hurt['waddledoo'] == [(9.0, 3)] and hurt['pooka'] == [(18.0, 4)] and
          ground['whitebear'][9] == 50.0 and ground['dekakuribo'][1:4] == [24.0, -27.0, 40.0],
          'spot values: Goomba hurtbox r 8 at node 4, Waddle Doo r 9 node 3, Pooka r 18 node 4; White Bear ground box '
          'height 50, Big Goomba (24, -27, 40)')
    if src:
        import s3ds_model as sm
        nodes, badn = {}, []
        for w in W.WALKERS:
            n = w['name']
            d0 = os.path.join(src, n, 'model', 'body', 'c00')
            bones = sm.Bch(open(os.path.join(d0, 'normal.bch'), 'rb').read()).models()[0]['bones']
            jt = open(os.path.join(d0, 'model.jtb'), 'rb').read()
            v = struct.unpack('<%dH' % (len(jt) // 2), jt)
            assert v[0] * 2 + 2 == len(jt)
            out = []
            for _r, node in hurt[n]:          # node n = the table's word n (word 0 its count): 0 = none (the root)
                if node == 0:
                    out.append((0, bones[0]['name']))
                elif node >= len(v) or v[node] >= len(bones):
                    badn.append((n, node))
                else:
                    out.append((node, bones[v[node]]['name']))
            nodes[n] = out
        print('      hurtbox node -> bone:', nodes)
        body = {'kuribo': 'HeadN', 'churine': 'HeadN', 'pooka': 'BodyN', 'ghos': 'RotN', 'togezo': 'RotN',
                'propellerheiho': 'TransN'}
        check(not badn and all(nodes[n] and nodes[n][0][1] == body.get(n, 'HipN') for n in nodes),
              'every hurtbox node is a bone of its kind\'s skeleton through model.jtb (node n = the table\'s u16 word n, '
              'word 0 its count; the converter keeps the .bch bone order and writes the table byte-swapped): the body '
              'centres (HipN, the Goomba / Churine HeadN, Pooka BodyN, Ghos / Spiny RotN; Propeller Heiho node 0, the '
              'root); the parasol spawner\'s node 9 the Dee\'s LRParasolN %s %s'
              % (badn, ''))
        d0 = os.path.join(src, 'waddledee', 'model', 'body', 'c00')
        bd = sm.Bch(open(os.path.join(d0, 'normal.bch'), 'rb').read()).models()[0]['bones']
        jd = struct.unpack('<10H', open(os.path.join(d0, 'model.jtb'), 'rb').read())
        check(bd[jd[9]]['name'] == 'LRParasolN', 'the parasol spawner\'s node 9 (0x7C79C) is the Dee\'s LRParasolN')

    # ==== 3. Waddle Dee's parasol
    art = D['art_dee']
    arts = [img.u32(art + 4 * i) for i in range(6)]
    check(arts == [art + 8, 1, 0xAD, 1, fn['wd_para_cb'], 0],
          'waddledee: article set {0xAD parasol, max 1, wd_para_cb} (3DS enemy_article_data_set_waddledee 0x111C08: '
          '{173, 1, 0x7C778}) %s' % arts)
    m = K2.K(img)
    m.stage(0x94)
    m.w32(T.MGR + 0x5EC, 2)
    m.run(E.SITE_T, W.SITE_T + 8, {31: T.MGR, 0: 2})
    check(m.r32(W.ART_SETS + 4 * 0x13) == art and m.r32(W.ART_SETS + 4 * 0x19) == D['art_doo'],
          'battle load on a Smash Run stage: article set[0x13] = the Dee\'s (the parasol), [0x19] the Doo\'s')
    drop = {}
    for var in (0, 1, 2, 3):
        for slot in (69, 71):
            m = K2.K(img)
            m.walker(cfgs['waddledee'], state=4, kind=0x13, var=var)
            m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x40))
            m.call(vslot('waddledee', slot), {3: OBJ, 4: 0})
            g1 = [c[1:] for c in m.calls if c[0] == 'gen_art']
            v1 = m.r32(OBJ + 0xC)
            m.calls = []
            m.call(vslot('waddledee', slot), {3: OBJ, 4: 0})
            g2 = [c[1:] for c in m.calls if c[0] == 'gen_art']
            drop[(var, slot)] = (g1, v1, g2)
    ok = all(drop[(v, s)] == (([(OBJ, 0, 0)], v + 2, []) if v < 2 else ([], v, [])) for v in range(4) for s in (69, 71))
    check(ok, 'waddledee drop (0x5CF90, slots 69 / 71): var 0 / 1 -> + 2 and generate_article(0, false) (0x5CFBC) once; '
          'var 2 / 3 (no parasol) nothing %s' % drop)
    m = K2.K(img)
    m.wf(POSTURE + 0x10, 100.0)
    m.wf(POSTURE + 0x14, 10.0)
    m.node_off = (1.0, 7.0)
    m.wf(GROUND + 0x88, 2.5)
    m.w32(ACC, 0x1234)
    res = {}
    for lr in (1.0, -1.0):
        m.calls = []
        m.wf(POSTURE + 0x60, lr)
        m.call(fn['wd_para_cb'], {3: 0xA471C1E, 4: ACC})
        a_, p, pa = m.captured
        u = lambda o: struct.unpack('>I', p[o:o + 4])[0]  # noqa: E731
        f = lambda o: round(struct.unpack('>f', p[o:o + 4])[0], 3)  # noqa: E731
        node = [c[2] for c in m.calls if c[0] == 'node_gpos']
        frees = [c[1:] for c in m.calls if c[0] == 'free']
        res[lr] = (a_, node, (f(4), f(8), f(0xC), f(0x10), f(0x68)), (u(0x1C), u(0x20), u(0x28), u(0x2C), u(0x58)),
                   (p[0x60], p[0x6C]), frees == [(pa + 0x48, 2), (pa + 0x3C, 2)], m.uc.reg_read(T.R[3]))
    check(all(res[lr] == (0xA471C1E, [9], (101.0, 17.0, 2.5, lr, -lr), (0, 0x1234, 3, 120, 4), (0, 0), True, 0)
              for lr in (1.0, -1.0)),
          'waddledee parasol spawner (3DS 0x7C778): node 9\'s position, z the ground\'s +0x88; lr, -lr at +0x68, the '
          'owner\'s id, team, life PSb0 f0 120, +0x58 4; util_activate, the members freed, returns 0 %s' % res)
    # the Wii U's own parasol init (weapon kind 0xAD, specializer slot 6 0x0319F3FC = 3DS 0xADF64) on the Dee's object
    wdee = D['prm_waddledee']
    for lr in (1.0, -1.0):
        m = K2.K(img)
        for a in range(0x0319F3FC, 0x0319F578, 4):
            if img.u32(a) >> 26 in (4, 56, 57, 60, 61):
                m.w32(a, 0x60000000)
        m.w32(W.PARAM_MGR, T.PM)
        m.w32(T.PM + 0x60 + 4 * 0x13, wdee)
        m.uc.mem_write(VTB, b''.join(struct.pack('>I', K2.STUB + 4 * 0x31) for _ in range(0x100)))
        m.uc.mem_write(VTB + 0x400, b''.join(struct.pack('>I', K2.STUB + 4 * 0x32) for _ in range(0x40)))
        m.w32(VTB + 0x400 + 0x6C, K2.STUB + 4 * 0x30)
        for k in range(K2.NSTUB):
            m.w32(K2.VTS + 4 * k, K2.STUB + 4 * k)
        m.w32(M1, VTB)
        m.w32(M2, K2.VTS)
        m.w32(M3, VTB + 0x400)
        m.w32(K2.WPN + 0x28, ACCW)
        m.w32(ACCW + 0x2C, M1)
        m.w32(ACCW + 0x34, M2)
        m.w32(ACCW + 0x84, M3)
        m.w32(ACCW + 0x1A98, MDL)
        m.wf(MDL + 0x5C, 1.0)                     # the model's scale = PSb0 f5 1.0 already (no re-scale)
        m.w32(ACCW + 0x1A90, WX)
        m.w32(WX + 8, WX + 0x10)
        m.w32(WX + 0x10, WX + 0x20)
        m.w32(WX + 0x20 + 0xC, WX + 0x40)
        m.uc.mem_write(K2.EBUF, bytes(0x40))
        m.wf(K2.PRM + 0x68, -lr)
        m.call(0x0319F3FC, {3: 0, 4: K2.WPN, 5: K2.PRM})
        e = [round(m.rf(K2.EBUF + o), 3) for o in (0, 4, 8, 0x24, 0x2C, 0x30)]
        sh = [c[3:6] for c in m.calls if c[0] == 'stub' and c[1] == 0x30]
        check(e == [-lr * 1.0, 0.0, 0.0, 0.02, 2.0, 0.01] and sh == [(0, 1, 0)] and m.r32(WX + 0x40 + 0x1C) == 16,
              'the Wii U\'s parasol init (0x0319F3FC) on the Dee\'s object, lr %d: speed x PSb0 f1 1.0 x (-lr) %s, its '
              '+0x24 / +0x2C / +0x30 PSb0 f3 / f4 / f2 (0.02, 2.0, 0.01), ShieldModule set_status(0, 1, 0), +0x1C '
              'P+0x88 16 (as the 3DS 0xADF64)' % (lr, e))

    # ==== 4. Lethinium (plasmawisp 0x12) on mczakoplasmawisp's AI: no forced level-2 attack (the 3DS 0x88E68 has none)
    pw = fn['pw2_up']
    res = {}
    for kind, level in ((0x12, 2), (0x12, 3), (0x12, 1), (0x57, 2)):
        m = K2.K(img)
        m.uc.mem_write(OBJ, bytes(0x210))
        m.w32(OBJ + 8, kind)
        m.w32(OBJ + 0x1EC, level)
        m.w32(OBJ + 0x1E4, 5)
        m.run(pw, W.PW_UP2, {3: OBJ, 4: 0x4444})
        res[(kind, level)] = (m.r32(OBJ + 0x1E4), m.uc.reg_read(T.R[3]), m.uc.reg_read(T.R[4]))
    check(img.u32(W.PW_ROW2_UP) == pw and
          res == {(0x12, 2): (0x7FFFFFFF, OBJ, 0x4444), (0x12, 3): (0x7FFFFFFF, OBJ, 0x4444),
                  (0x12, 1): (5, OBJ, 0x4444), (0x57, 2): (5, OBJ, 0x4444)},
          'Lethinium: mczakoplasmawisp\'s state 2 update word (0x102FE778) -> pw2_up: kind 0x12 at level >= 2 keeps '
          '+0x1E4 at 0x7FFFFFFF (the Fortress-only forced level-2 attack never comes; 0x026D0C48, the 3DS path, runs), '
          'then the game\'s update 0x026D09A4 (this, r4 kept); level < 2 and the twin 0x57 untouched %s' % res)
    if len(sys.argv) > 4:
        sm = sys.argv[4]
        f3 = open(os.path.join(fsdir, 'enemy_param_vl_plasmawisp.bin'), 'rb').read()
        fu = open(os.path.join(sm, 'enemy_param_vl_mczakoplasmawisp.bin'), 'rb').read()
        data, _ch = TP.remap('plasmawisp', f3, fu)
        g, g3, gu = TP.groups(data), TP.groups(f3), TP.groups(fu)
        check(g[5][1][59].value == g3[1][1][8].value == 5 and gu[5][1][59].value == 90 and
              [t.value for t in g[5][1][53:59]] == [t.value for t in gu[5][1][53:59]],
              'Lethinium\'s param file: the Wii U-only word at object +0x134 (G5 word 59, the twin\'s 90: the search '
              'cool-down its level-2 attack sets, 0x026D0EA0) = the 3DS\'s search_interval(1) %s (G1 word 8), which the '
              '3DS leaves in +0x1E0 there; the other Wii U-only words kept' % g[5][1][59].value)
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
