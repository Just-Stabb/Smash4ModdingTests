#!/usr/bin/env python3
"""Mesh visibility for converted 3DS enemies whose behaviours (not their animations) pick the meshes they show:
writes motion/enemy/KIND/body/material_anime.pac, one MTA a motion (visibility by mesh name, as the converter's
per-motion MTAs and the fighters' material_anime_*.pac) plus default.mta.

  python3 tools/s3ds_enemy_vis.py MOTION_ROOT OUT_ROOT [KIND ...]

MOTION_ROOT holds motion/enemy/KIND/body/main.pac (the converted motions: the MTAs' names and lengths); OUT_ROOT gets
motion/enemy/KIND/body/material_anime.pac. KINDs: the ones in RULES (default: all).

On the 3DS these meshes are listed in the model's normal.vmt and switched by code (Behavior::set_mesh_visibility(vmt
index, bool), the GsbDrawModel's vmt table); the Wii U has no .vmt and draws every mesh, so a converted Waddle Dee
shows its three parasols and both faces. The states below are the 3DS behaviours' (enemy_fs.cro):
- waddledee (normal.vmt: 0 Cparasol, 1 Larm, 2 Lparasol, 3 Rarm, 4 Rparasol, 5 damage, 6 normal): its show
  function 0x5D04C (variations 2 / 3, the ones without a parasol, and every variation once the parasol is
  dropped: 0x5CF90): both arms, no parasol, the normal face (6 on, 5 off); its defeat 0x5CF18 shows the damage face
  (5 on, 6 off). The parasol variations (0 / 1) hold one parasol that follows lr and the motion (0x5D0F0..); here
  none (the walker spawns variation 0; one parasol would need the per-frame code).
- waddledoo (0 eye_blink1, 1 eye_blink2, 2 eye_normal, 3 tear; the body is not in the list): its code switches
  the eyes and the tear per state; here the open eyes (eye_normal), no blink frames, no tear.
- darios (default, shoot): the model's default visibility bit mask 0x1 (default only); shoot is shown by its shot
  code.
Damage motions (Damage*, Down*, Collapses) take the 'damage' states where a kind has them (the damage face, as the
Goomba's own per-motion MTAs do).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mta  # noqa: E402
import omo  # noqa: E402

RULES = {
    'waddledee': {
        'default': {'waddledee_Cparasol_mh_VIS_O_OBJ': 0, 'waddledee_Larm_mh_VIS_O_OBJ': 1,
                    'waddledee_Lparasol_mh_VIS_O_OBJ': 0, 'waddledee_Rarm_mh_VIS_O_OBJ': 1,
                    'waddledee_Rparasol_mh_VIS_O_OBJ': 0, 'waddledee_damage_mh_VIS_O_OBJ': 0,
                    'waddledee_normal_mh_VIS_O_OBJ': 1},
        'damage': {'waddledee_damage_mh_VIS_O_OBJ': 1, 'waddledee_normal_mh_VIS_O_OBJ': 0},
    },
    'waddledoo': {
        'default': {'waddledoo_eye_blink1_mh_VIS_O_OBJ': 0, 'waddledoo_eye_blink2_mh_VIS_O_OBJ': 0,
                    'waddledoo_eye_normal_mh_VIS_O_OBJ': 1, 'waddledoo_tear_mh_VIS_O_OBJ': 0},
    },
    'darios': {
        'default': {'default_VIS_O_OBJ': 1, 'shoot_VIS_O_OBJ': 0},
    },
}
DAMAGE_PREFIXES = ('Damage', 'Down', 'Collapses')


def states(rule, motion):
    s = dict(rule['default'])
    if motion and motion.startswith(DAMAGE_PREFIXES):
        s.update(rule.get('damage', {}))
    return s


def build(kind, main_pac):
    """[(name, MTA bytes)]: one per OMO of main_pac (same stem, .mta) and default.mta"""
    rule = RULES[kind]
    prefix = 'Enm%sBodyMain' % kind.capitalize()
    out = []
    for name, data in omo.pac_read(main_pac):
        if not name.endswith('.omo'):
            continue
        stem = name[:-4]
        motion = stem[len(prefix):] if stem.startswith(prefix) else ''
        frames = max(1, int(omo.Omo(data).frames))
        vis = [(m, [(0, v)]) for m, v in sorted(states(rule, motion).items())]
        out.append((stem + '.mta', mta.write(frames, [], vis=vis)))
    vis = [(m, [(0, v)]) for m, v in sorted(states(rule, '').items())]
    out.append(('default.mta', mta.write(60, [], vis=vis)))
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, out_root = sys.argv[1:3]
    for kind in sys.argv[3:] or sorted(RULES):
        pac = os.path.join(root, 'motion', 'enemy', kind, 'body', 'main.pac')
        entries = build(kind, pac)
        d = os.path.join(out_root, 'motion', 'enemy', kind, 'body')
        os.makedirs(d, exist_ok=True)
        omo.pac_write(os.path.join(d, 'material_anime.pac'), entries)
        print('%s: material_anime.pac, %d MTAs' % (kind, len(entries)))


if __name__ == '__main__':
    main()
