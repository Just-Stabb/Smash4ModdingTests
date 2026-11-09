#!/usr/bin/env python3
"""Behaviour tests of step 2n (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2n") on a patched
executable, in unicorn (smashrun_step2h_test.py's machine):

  python3 tools/smashrun_step2n_test.py PATCHED.rpx [GL_ENEMY_PARAM]

  GL_ENEMY_PARAM: the Wii U's param/enemy/gl/enemy_param.bin (the kinds' model scale, group 3 entry kind + 1, +0x1C)

- the tread boxes: each stompable kind's CFG TB0-TB2 are its 3DS area 0 ({on, node, w, h, x, y} of its vl group 5:
  half width, centre above the posture / node, half height) in the model's scale, as the 3DS area code scales an area
  by its node's world scale (code.bin 0x3D9278-0x3D92C4); with GL_ENEMY_PARAM the scales are the file's +0x1C;
- the stomp, w_upd run: a fall onto a Big Goomba 8.5 to the side (inside 7 x 1.3, outside the unscaled 7) => 10
  Stepped, 9.5 nothing; onto a Paratroopa 2.8 to the side (3 = 2 x 1.5) => 9 (the wing loss), 3.2 nothing; onto a
  Goomba 8.0 (8.4 = 7 x 1.2) => 8; each crossing the scaled box top (Big Goomba 9.75, Paratroopa 18, Goomba 7.84);
- every write the tests made stayed inside its object (smashrun_walker_test.py's guard) and every run returned.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402

check = T.check
OBJ, INPUT, POSTURE = T.OBJ, T.INPUT, T.POSTURE


def gl_scales(path):
    """{kind number: the gl entry's +0x1C (model scale)} of the Wii U enemy_param.bin (group 3, entry kind + 1)"""
    import fighter_param_vl as V
    _h, toks = V.tokenize(open(path, 'rb').read())
    groups = []
    for t in toks:
        if isinstance(t, tuple):
            groups.append([])
        else:
            groups[-1].append(t)
    g = groups[2]
    n = len(g) // 99
    return {k: g[(k + 1) * n + 7].value for k in range(98)}


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
    f = lambda v: struct.unpack('>f', struct.pack('>I', v))[0]  # noqa: E731

    # ---- the tread boxes in the model's scale
    stomp_kinds = [w for w in W.WALKERS if w.get('tread')]
    got = {w['name']: tuple(round(f(img.u32(cfg[w['name']] + W.CF[k])), 4) for k in ('TB0', 'TB1', 'TB2'))
           for w in stomp_kinds}
    want = {w['name']: tuple(round(v, 4) for v in W.tread_box(w)) for w in stomp_kinds}
    check(got == want and set(got) == set(W.TREAD_SCALE),
          'the stompable kinds\' tread boxes (CFG TB0-TB2: half width, centre, half height) = the 3DS area x the model '
          'scale: %s' % got)
    areas = {}
    for n in ('dekakuribo', 'patapata', 'kuribo', 'tikibuzz'):
        a = W.vl_group(n, 5)[0]                                 # {on, node, w, h, x, y}
        areas[n] = (a[2] / 2.0, a[5], a[3] / 2.0)
    check(areas['dekakuribo'] == byname['dekakuribo']['tbox'] and areas['patapata'] == byname['patapata']['tbox'] and
          (areas['kuribo'][0], areas['kuribo'][2]) == (W.TREAD_BOX[0], W.TREAD_BOX[2]) and
          (areas['tikibuzz'][0], areas['tikibuzz'][2]) == (byname['tikibuzz']['tbox'][0],
                                                           byname['tikibuzz']['tbox'][2]),
          'the unscaled boxes are the vl area 0s ({on, node, w, h, x, y} -> w / 2, y (the Goomba: its node 2 HipN, '
          'bind height 2.53; Tiki Buzz: its live node 3), h / 2): %s' % areas)
    if len(sys.argv) > 2:
        sc = gl_scales(sys.argv[2])
        kinds = {w['name']: w['kind'] for w in stomp_kinds}
        gs = {n: round(sc[k], 4) for n, k in kinds.items()}
        check(gs == {n: round(v, 4) for n, v in W.TREAD_SCALE.items()},
              'TREAD_SCALE is the Wii U gl entries\' model scale (+0x1C, the activation\'s set_scale): %s' % gs)

    # ---- the stomp: w_upd with a fighter falling through the scaled box top, beside the enemy
    def fall(name, dx, state, var=0):
        w = byname[name]
        tb = W.tread_box(w)
        top = tb[1] + tb[2]
        m = H.M(img)
        m.walker(cfg[name], state=state, kind=w['kind'], x=0.0, var=var)
        m.wf(POSTURE + 0x14, 0.0)
        m.call(fn['w_init'], {3: OBJ})
        m.fighter(y=top + 10.0, x=dx)
        out = []
        for fy in (top + 5.0, top + 1.0, top - 1.0):
            m.wf(H.FPOST + 0x14, fy)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            out += [c[2] for c in m.calls if c[0] == 'chgi']
        return top, out
    res = {}
    for name, dx, st, var, want_s in (('dekakuribo', 8.5, 3, 0, [10]), ('dekakuribo', -8.5, 3, 0, [10]),
                                      ('dekakuribo', 9.5, 3, 0, []), ('patapata', 2.8, 2, 0, [9]),
                                      ('patapata', 3.2, 2, 0, []), ('patapata', 2.8, 12, 2, [19]),
                                      ('kuribo', 8.0, 3, 0, [8]), ('kuribo', 8.6, 3, 0, [])):
        top, got = fall(name, dx, st, var)
        res[(name, dx, var)] = (round(top, 3), got)
        check(got == want_s, 'stomp: a fall through %s\'s scaled box top %.2f at dx %g (var %d) -> %s (want %s)'
              % (name, top, dx, var, got, want_s))
    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
