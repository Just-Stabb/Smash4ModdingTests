#!/usr/bin/env python3
"""Checks tools/s3ds_enemy_vis.py's output:

  python3 tools/s3ds_enemy_vis_test.py S3DS_ENEMY_ROOT CONVERTED_ROOT OUT_ROOT

CONVERTED_ROOT: the installed converted enemies (model/enemy/KIND/body/c00/model.nud, motion/enemy/KIND/body/main.pac);
OUT_ROOT: what s3ds_enemy_vis.py wrote. For every kind with a pac: an MTA for each OMO of main.pac (same stem) and
default.mta; every visibility track names a mesh of the kind's model.nud and one of its normal.vmt meshes, one key at
frame 0, the MTA as long as the motion; damage motions take the damage states, the rest the defaults (as
model_states() computes them); Waddle Dee: no parasol, both arms, the normal face (the damage face in damage motions);
Waddle Doo: the open eyes only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mta  # noqa: E402
import omo  # noqa: E402
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
        nud = open(os.path.join(conv, 'model', 'enemy', k, 'body', 'c00', 'model.nud'), 'rb').read()
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
            ok &= all((n.encode() + b'\0') in nud and n in vmt for n in st)
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
    print('%d kinds, %d failures' % (len(kinds), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
