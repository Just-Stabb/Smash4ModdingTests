#!/usr/bin/env python3
"""Behaviour tests of step 2i (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2i") on a patched
executable, in unicorn with smashrun_walker_test.py's stubbed world (the model handle's is_valid /
set_mesh_visibility_by_index and the ModelModule's set_visibility recorded: m.meshes = NUD mesh -> visible):

  python3 tools/smashrun_step2i_test.py PATCHED.rpx [DATA_ROOT]

- the mesh switch tables: each kind's vmt entries -> its NUD meshes (Big Goomba's normal_mh three meshes), the
  H3D default bits; with DATA_ROOT (the package's data/): the shipped model.nud files hold those meshes at those
  indices, none of them drawn as nothing (the restored baselines);
- per kind, the meshes visible in each state, from the 3DS code (Paratroopa winged -> wingless at the wing loss / a
  non-lethal hit; the Spiny egg -> the Spiny at the hatch; the Goombas' faces by motion; Ghos, Tiki Buzz, Waddle
  Dee (parasol by lr and motion), Waddle Doo (the blink cycle, the tear));
- Ghos's per-category immunity is in smashrun_flier_test.py, the shell item and set_visibility(0) in
  smashrun_step2h_test.py.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
import smashrun_flier_test as FT  # noqa: E402

check = T.check
OBJ, ACC, POSTURE, INPUT, MOTION = T.OBJ, T.ACC, T.POSTURE, T.INPUT, T.MOTION


def nud_meshes(path):
    """[(name, all its polygons' indices zero)] in the NUD's order"""
    d = open(path, 'rb').read()
    if d[:2] == b'\x78\x9c':
        d = zlib.decompress(d)
    _, _ver, nmesh, _bs, _be, pstart, psize, vsize, vasize = struct.unpack('>IHhhhiiii', d[4:0x20])
    sb = 0x30 + pstart + psize + vsize + vasize
    out = []
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        no, = struct.unpack('>i', d[o + 32:o + 36])
        npoly, obj = struct.unpack('>hi', d[o + 42:o + 48])
        zero = True
        for j in range(npoly):
            q = obj + j * 0x30
            poff, = struct.unpack('>i', d[q:q + 4])
            nidx, = struct.unpack('>H', d[q + 32:q + 34])
            a = 0x30 + pstart + poff
            zero &= not any(d[a:a + 2 * nidx])
        out.append((d[sb + no:d.index(b'\0', sb + no)].decode('latin1'), zero))
    return out


def vis(m, name):
    """{vmt name: visible} from the recorded NUD meshes (every NUD mesh of an entry must agree; None: never set)"""
    out = {}
    for e in W.VMT[name]:
        vals = {m.meshes.get(i) for i, n in enumerate(W.NUD_MESHES[name]) if n == e}
        out[e.replace('_VIS_O_OBJ', '').replace(name + '_', '').replace('_mh', '')] = \
            vals.pop() if len(vals) == 1 else tuple(vals)
    return out


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
    byname = {w['name']: w for w in W.WALKERS}
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    bad = [hex(A.h.base + 4 * i) for i, x in enumerate(A.h.words()) if img.u32(A.h.base + 4 * i) != x]
    check(not bad, 'region H (0x%08X-0x%08X): the code to 0x%08X is in the executable %s'
          % (W.CAVE_H, W.LIMIT_H, A.h.pc, bad[:4]))

    # ---------------------------------------------------------------- the tables
    res = {}
    for n in W.VMT:
        if n not in byname:
            continue
        a = D['vis_' + n]
        t = [img.u32(a + 4 * i) for i in range(2 + len(W.VMT[n]))]
        idx = [[b for b in struct.pack('>I', x) if b != 0xFF] for x in t[2:]]
        res[n] = (t[0] == len(W.VMT[n]) and img.u32(cfg[n] + W.CF['VIS']) == a and
                  all([W.NUD_MESHES[n][i] for i in ix] == [e] * len(ix) and ix for ix, e in zip(idx, W.VMT[n])) and
                  t[1] == sum(v << i for i, v in enumerate(W.VIS_DEFAULT[n])))
    check(all(res.values()) and len(res) == 9 and
          [b for b in struct.pack('>I', img.u32(D['vis_dekakuribo'] + 8 + 8))] == [2, 3, 4, 0xFF],
          'tables: CFG VIS -> {n, H3D default mask, per vmt entry its NUD meshes} for the 9 ported kinds (step 2j: Pooka\'s too; Pooka\'s '
          'table is built once it is a walker; Big Goomba\'s normal_mh = NUD meshes 2 / 3 / 4) %s' % res)
    if root:
        res = {}
        for n in ('kuribo', 'waddledee', 'waddledoo', 'ghos', 'tikibuzz', 'dekakuribo', 'togezo'):
            p = os.path.join(root, 'model', 'enemy', n, 'body', 'c00', 'model.nud')
            ms = nud_meshes(p) if os.path.exists(p) else []
            res[n] = ([x for x, _z in ms] == list(W.NUD_MESHES[n]), [x for x, z in ms if z])
        check(all(v[0] and not v[1] for v in res.values()),
              'DATA_ROOT: the 7 restored model.nud files hold NUD_MESHES in order and no mesh is drawn as nothing %s'
              % res)

    # ---------------------------------------------------------------- per kind
    def rows(name):
        r = {}
        for sid, s in byname[name]['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        return r

    def machine(name, state=0, lr=-1.0, var=0, flier=False):
        w = byname[name]
        if flier:
            m = FT.Machine(img)
            m.flier(cfg[name], state=state, kind=w['kind'], lr=lr)
            m.w32(OBJ + 0xC, var)
        else:
            m = H.M(img)
            m.walker(cfg[name], state=state, lr=lr, kind=w['kind'], var=var)
        m.target, m.target_x = 0, 300.0
        m.call(fn['w_init'], {3: OBJ})
        return m

    def vslot(name, k):
        return img.u32(img.u32(cfg[name] + W.CF['VT']) + 0xC + 8 * k)

    def start(m, name):
        m.call(img.u32(cfg[name] + W.CF['FSTART']) or vslot(name, 41), {3: OBJ})

    def enter(m, name, s):
        m.call(rows(name)[s][0], {3: OBJ})

    def upd(m, name, s):
        m.call(rows(name)[s][1], {3: OBJ, 4: INPUT})

    # Paratroopa (0x7234C start, 0x726BC slot 20 -> 9 0x72740, 0x73C00 slot 69)
    m = machine('patapata', var=0)
    start(m, 'patapata')
    a = vis(m, 'patapata')
    enter(m, 'patapata', 9)
    b = vis(m, 'patapata')
    m2 = machine('patapata', var=1)
    start(m2, 'patapata')
    m2.calls = []
    m2.call(vslot('patapata', 69), {3: OBJ})
    c = (vis(m2, 'patapata'), m2.r32(OBJ + 0xC))
    m3 = machine('patapata', var=2)
    start(m3, 'patapata')
    check(a == {'wing': 1} and b == {'wing': 0} and c == ({'wing': 0}, 3) and vis(m3, 'patapata') == {'wing': 0},
          'Paratroopa: winged at the start (var 0), the wing gone at the wing loss (state 9\'s enter 0x727BC) and at a '
          'non-lethal hit (slot 69 0x73C3C: var 1 -> 3); a Koopa (var 2) starts wingless (0x724A8) %s'
          % ((a, b, c, vis(m3, 'patapata')),))

    # Spiny (start 0x36CE0, the hatch L622F4, slot 60 0x376A4)
    m = machine('togezo', var=0)
    start(m, 'togezo')
    a = vis(m, 'togezo')
    m.calls = []
    m.call(fn['tg_hatch'], {31: OBJ, 3: OBJ})
    b = (vis(m, 'togezo'), m.r32(OBJ + 0xC), [x for x in m.calls if x[0] == 'node_rot'])
    m2 = machine('togezo', var=1)
    start(m2, 'togezo')
    m3 = machine('togezo', var=0)
    start(m3, 'togezo')
    m3.calls = []
    m3.call(vslot('togezo', 60), {3: OBJ})
    c = (vis(m3, 'togezo'), [x[2] for x in m3.calls if x[0] == 'chgi'])
    m2.calls = []
    m2.call(vslot('togezo', 60), {3: OBJ})
    check(a == {'mh': 0, 'paipo': 1} and b == ({'mh': 1, 'paipo': 0}, 1, [('node_rot', 2, 0.0)]) and
          vis(m2, 'togezo') == {'mh': 1, 'paipo': 0} and c == ({'mh': 1, 'paipo': 0}, [5]) and
          not [x for x in m2.calls if x[0] == 'chgi'],
          'Spiny: the egg drawn as the egg (paipo on, the Spiny off: 0x36D94 / 0x36DA4), var 1 as the Spiny; the hatch '
          '(L622F4): var 1, node 2\'s rotation zeroed, paipo off, the Spiny on; slot 60 on an egg: the hatch => 5, '
          'on a Spiny nothing %s' % ((a, b, vis(m2, 'togezo'), c),))

    # the Goombas: the material animation's meshes by the motion playing (u_vis, every update)
    out = {}
    for name, motions in (('kuribo', ('WalkL', 'Damage', 'Collapses', 'RunL')),
                          ('dekakuribo', ('WalkL', 'DamageStart', 'Stepped', 'AngryL'))):
        m = machine(name, state=3)
        start(m, name)
        got = [vis(m, name)]
        for mot in motions:
            m.w32(MOTION + W.MOT_KIND, [s for s, _f in byname[name]['motions']].index(mot))
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            got.append(vis(m, name))
        out[name] = got
    k_n, k_d = {'damage': 0, 'normal': 1}, {'damage': 1, 'normal': 0}
    d_n, d_d2, d_d = ({'damage2': 0, 'damage': 0, 'normal': 1}, {'damage2': 1, 'damage': 0, 'normal': 0},
                      {'damage2': 0, 'damage': 1, 'normal': 0})
    check(out['kuribo'] == [k_n, k_n, k_d, k_d, k_n] and out['dekakuribo'] == [d_n, d_n, d_d2, d_d, d_n],
          'Goomba / Big Goomba: the normal face at the start (H3D default), then per motion as the 3DS material '
          'animations (the converted material_anime.pac: Damage* / Down* / Collapses the damage face; Big Goomba\'s '
          'Damage / DamageStart / DamageFly damage2, the others and Stepped damage; its three normal_mh meshes '
          'together) %s' % out)

    # Ghos (vmt 0 damage, 1 normal; start 0x109C0, 2 0x10AD0 / 0x10EE4, 4 0x10E84)
    m = machine('ghos', state=1, flier=True)
    start(m, 'ghos')
    a = vis(m, 'ghos')
    enter(m, 'ghos', 2)
    b = vis(m, 'ghos')
    m.w32(OBJ + W.V(2), 2)
    upd(m, 'ghos', 2)
    c = vis(m, 'ghos')
    upd(m, 'ghos', 2)
    e = vis(m, 'ghos')
    enter(m, 'ghos', 4)
    check(a == {'normal': 1, 'damage': 0} and b == {'normal': 0, 'damage': 1} and c == b and
          e == {'normal': 1, 'damage': 0} and vis(m, 'ghos') == {'normal': 0, 'damage': 1},
          'Ghos: start normal; the stun (2) the damage face until its timer runs out, then normal; dead (4) the '
          'damage face %s' % ((a, b, c, e, vis(m, 'ghos')),))

    # Tiki Buzz (0 Damage1, 1 Damage2, 2 Normal)
    m = machine('tikibuzz', state=3, flier=True)
    start(m, 'tikibuzz')
    a = vis(m, 'tikibuzz')
    m.calls = []
    m.call(vslot('tikibuzz', 10), {3: OBJ})
    b = (vis(m, 'tikibuzz'), [x[0] for x in m.calls if x[0] == 'bi_damage'])
    m.call(vslot('tikibuzz', 60), {3: OBJ})
    c = vis(m, 'tikibuzz')
    enter(m, 'tikibuzz', 10)
    e = vis(m, 'tikibuzz')
    enter(m, 'tikibuzz', 3)
    f = vis(m, 'tikibuzz')
    m.calls = []
    enter(m, 'tikibuzz', 11)
    g = [x for x in m.calls if x[0] == 'visible']
    n1, d1, d2 = ({'Damage1': 0, 'Damage2': 0, 'Normal': 1}, {'Damage1': 1, 'Damage2': 0, 'Normal': 0},
                  {'Damage1': 0, 'Damage2': 1, 'Normal': 0})
    check(a == n1 and b == (d1, ['bi_damage']) and c == n1 and e == d2 and f == n1 and g == [('visible', 0)],
          'Tiki Buzz: normal at the start; a hit (slot 10 = the 3DS 11 0x7818C: BehaviorImpl\'s, then Damage1); slot 60 '
          'normal; the stomp (10) Damage2; fly (3) normal; gone (11) the whole model hidden %s'
          % ((a, b, c, e, f, g),))

    # Waddle Dee (wd_show 0x5D04C: var 0 / 1 by lr and motion; 2 / 3 both arms)
    out = {}
    for var, lr, s in ((0, -1.0, 4), (0, 1.0, 4), (0, -1.0, 5), (1, 1.0, 2), (2, -1.0, 4), (3, 1.0, 7)):
        m = machine('waddledee', state=s, lr=lr, var=var)
        start(m, 'waddledee')
        m.wf(POSTURE + 0x60, lr)                 # start faced the target: the case's lr from here
        m.meshes = {}
        enter(m, 'waddledee', s)
        out[(var, lr, s)] = ''.join(k for k, v in zip(('C', 'l', 'L', 'r', 'R', 'd', 'n'), vis(m, 'waddledee').values())
                                    if v)
    m = machine('waddledee', state=4, var=0)
    start(m, 'waddledee')
    m.calls = []
    m.call(vslot('waddledee', 69), {3: OBJ})
    h69 = (m.r32(OBJ + 0xC), ''.join(k for k, v in zip(('C', 'l', 'L', 'r', 'R', 'd', 'n'), vis(m, 'waddledee').values())
                                     if v),
           m.uc.reg_read(T.R[3]))
    m.call(vslot('waddledee', 60), {3: OBJ})
    h60 = vis(m, 'waddledee')
    m.calls = []
    m.call(vslot('waddledee', 71), {3: OBJ})
    h71 = (vis(m, 'waddledee')['damage'], [x[0] for x in m.calls if x[0] == 'notify_death'])
    want = {(0, -1.0, 4): 'lRn', (0, 1.0, 4): 'Lrn', (0, -1.0, 5): 'Lrn', (1, 1.0, 2): 'Cn', (2, -1.0, 4): 'lrn',
            (3, 1.0, 7): 'lr'}
    check(out == want and h69 == (2, 'lrd', 0) and h60['normal'] == 1 and h60['damage'] == 0 and
          h71 == (1, ['notify_death']),
          'Waddle Dee: with a parasol (var 0 / 1) walking left the right parasol and the left arm (lr -1), right the '
          'other two, turning the other way, the parasol fall the centre one; var 2 / 3 both arms, no parasol, the '
          'normal face unless the motion is Damage (dead: as it was); slot 69 drops the parasol (var 0 -> 2) and '
          'shows the damage face, returns 0; slot 60 the normal face; slot 71 the damage face, then notify_on_death '
          '%s' % ((out, h69, h60, h71),))

    # Waddle Doo (slot 55 0x7D8A8 every frame; 56 / 57 / 58)
    m = machine('waddledoo', state=3)
    start(m, 'waddledoo')
    m.w32(OBJ + 4, 3)                            # walking (start went to its first state)
    seq = []
    for _ in range(80):
        m.call(vslot('waddledoo', 55), {3: OBJ})
        v = vis(m, 'waddledoo')
        seq.append('b1' if v['eye_blink1'] else 'b2' if v['eye_blink2'] else 'o' if v['eye_normal'] else '?')
    first = seq[:24]
    wait = seq.index('b1', 24) - 22 if 'b1' in seq[24:] else -1   # the counter's random wait (b1 3 frames in)
    m.w32(OBJ + 4, 6)
    m.call(vslot('waddledoo', 55), {3: OBJ})
    dead = vis(m, 'waddledoo')
    m.w32(OBJ + 4, 1)
    m.call(vslot('waddledoo', 55), {3: OBJ})
    other = vis(m, 'waddledoo')
    s56 = []
    for k in (56, 57, 58):
        m.call(vslot('waddledoo', k), {3: OBJ})
        s56.append(vis(m, 'waddledoo')['tear'])
    want_first = ['o'] * 3 + ['b1'] * 4 + ['b2'] * 4 + ['b1'] * 4 + ['o'] * 4 + ['o'] * 5
    check(first == want_first and 30 <= wait <= 50 and dead == {'eye_blink1': 0, 'eye_blink2': 0, 'eye_normal': 1, 'tear': 1} and
          other == {'eye_blink1': 0, 'eye_blink2': 0, 'eye_normal': 1, 'tear': 0} and s56 == [1, 1, 0],
          'Waddle Doo: walking, a blink starts once the counter runs out, phase = frame / 4: open, blink1, blink2, '
          'blink1, open, then the next wait random_range(30, 50) (%d); dead (the 3DS\'s 10, ours 6): the tear and '
          'open eyes; other states open eyes; slots 56 / 57 the tear, 58 none %s' % (wait, (first, dead, other, s56)))
    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
