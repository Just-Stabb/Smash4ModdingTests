#!/usr/bin/env python3
"""Checks tools/s3ds_enemy_vis.py's output:

  python3 tools/s3ds_enemy_vis_test.py S3DS_ENEMY_ROOT CONVERTED_ROOT OUT_ROOT [NUD_OUT]

CONVERTED_ROOT: the installed converted enemies (model/enemy/KIND/body/c00/model.nud, motion/enemy/KIND/body/main.pac);
OUT_ROOT: what s3ds_enemy_vis.py wrote. For every kind with a pac: an MTA for each OMO of main.pac (same stem) and
default.mta; every visibility track names a mesh of the kind's model.nud and one of its normal.vmt meshes, one key at
frame 0, the MTA as long as the motion; damage motions take the damage states, the rest the defaults (as
model_states() computes them); Waddle Dee: no parasol, both arms, the normal face (the damage face in damage motions);
Waddle Doo: the open eyes only.
NUD_OUT (what --nud wrote): each model.nud the same size as the converted one, the default-hidden meshes' polygons
all-zero indices, every other mesh's indices and the rest of the file unchanged; Waddle Dee's parasols / damage face,
Waddle Doo's blinks / tear, the Goomba's damage face hidden.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mta  # noqa: E402
import omo  # noqa: E402
import nud  # noqa: E402
import s3ds_enemy_vis as V  # noqa: E402

FAILS = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def main():
    root, conv, out = sys.argv[1:4]
    kinds = sorted(os.listdir(os.path.join(out, 'motion', 'enemy')))
    for k in kinds:
        vmt, default, damage = V.model_states(k, os.path.join(root, k, 'model', 'body', 'c00'))
        nudb = open(os.path.join(conv, 'model', 'enemy', k, 'body', 'c00', 'model.nud'), 'rb').read()
        omos = {n[:-4]: omo.Omo(d).frames for n, d in omo.pac_read(os.path.join(conv, 'motion', 'enemy', k, 'body',
                                                                                 'main.pac')) if n.endswith('.omo')}
        got = dict(omo.pac_read(os.path.join(out, 'motion', 'enemy', k, 'body', 'material_anime.pac')))
        ok = set(got) == {s + '.mta' for s in omos} | {'default.mta'}
        prefix = 'Enm%sBodyMain' % k.capitalize()
        for name, d in got.items():
            m = mta.read(d)
            st = {v['name']: v['keys'] for v in m['vis']}
            stem = name[:-4]
            motion = stem[len(prefix):] if stem.startswith(prefix) else ''
            want = damage if motion.startswith(V.DAMAGE_PREFIXES) else default
            ok &= all((n.encode() + b'\0') in nudb and n in vmt for n in st)
            ok &= {n: ks[0][1] for n, ks in st.items()} == want and all(len(ks) == 1 and ks[0][0] == 0
                                                                            for ks in st.values())
            ok &= not m['mats'] and (name == 'default.mta' or m['frames'] == max(1, int(omos[stem])))
        check(ok, '%s: %d MTAs (every motion + default), tracks on its vmt / NUD meshes, damage states in %s'
              % (k, len(got), '/'.join(V.DAMAGE_PREFIXES)))
    if 'waddledee' in kinds:
        _v, d, g = V.model_states('waddledee', os.path.join(root, 'waddledee', 'model', 'body', 'c00'))
        sd = {V.short('waddledee', n): v for n, v in d.items()}
        sg = {V.short('waddledee', n): v for n, v in g.items()}
        check(sd == {'Cparasol': 0, 'Larm': 1, 'Lparasol': 0, 'Rarm': 1, 'Rparasol': 0, 'damage': 0, 'normal': 1} and
              sg == dict(sd, damage=1, normal=0), 'waddledee: no parasol, both arms, normal face; damage face in '
              'damage motions')
    if 'waddledoo' in kinds:
        _v, d, g = V.model_states('waddledoo', os.path.join(root, 'waddledoo', 'model', 'body', 'c00'))
        sd = {V.short('waddledoo', n): v for n, v in d.items()}
        check(sd == {'eye_blink1': 0, 'eye_blink2': 0, 'eye_normal': 1, 'tear': 0} and g == d,
              'waddledoo: the open eyes only, in every motion')
    if len(sys.argv) > 4:
        nout = sys.argv[4]
        nk = sorted(os.listdir(os.path.join(nout, 'model', 'enemy')))
        hidden_all = {}
        for k in nk:
            src = os.path.join(conv, 'model', 'enemy', k, 'body', 'c00', 'model.nud')
            dst = os.path.join(nout, 'model', 'enemy', k, 'body', 'c00', 'model.nud')
            hide = {n for n, v in V.pac_defaults(conv, k).items() if not v}
            if os.path.exists(os.path.join(root, k, 'model', 'body', 'c00', 'normal.vmt')):
                hide |= {n for n, v in V.model_states(k, os.path.join(root, k, 'model', 'body', 'c00'))[1].items()
                         if not v}
            a, b = nud.read(src), nud.read(dst)
            ok = os.path.getsize(src) == os.path.getsize(dst) and [m.name for m in a] == [m.name for m in b]
            da, db = open(src, 'rb').read(), open(dst, 'rb').read()
            diff = [i for i in range(len(da)) if da[i] != db[i]]
            idx_ranges = set()
            for ma, mb in zip(a, b):
                for pa, pb in zip(ma.polygons, mb.polygons):
                    if ma.name in hide:
                        ok &= not pb.idx.any()
                    else:
                        ok &= (pa.idx == pb.idx).all()
            hidden_all[k] = sorted({m.name for m in b if m.polygons and all(not p.idx.any() for p in m.polygons)})
            ok &= set(hidden_all[k]) == hide
            check(ok and len(diff) > 0, '%s: model.nud hides %s, the rest unchanged (%d bytes differ)'
                  % (k, [V.short(k, n) for n in hidden_all[k]], len(diff)))
            del idx_ranges
        want = {'darios': {'shoot'}, 'pooka': {'body_damage', 'eye_damage'}}
        check(all({V.short(k, n) for n in hidden_all.get(k, [])} == w for k, w in want.items()) and
              not set(nk) & set(V.CODE_SWITCHED),
              'NUDs: Darios no shot mesh, Pooka no damage meshes; none for the kinds the code switches (step 2i: %s)'
              % ', '.join(V.CODE_SWITCHED))
    print('%d kinds, %d failures' % (len(kinds), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
