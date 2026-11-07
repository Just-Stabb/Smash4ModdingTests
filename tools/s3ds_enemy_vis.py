#!/usr/bin/env python3
"""Mesh visibility for the converted 3DS enemies that switch meshes by code: writes
motion/enemy/KIND/body/material_anime.pac, one MTA a motion (visibility by mesh name, as the converter's per-motion
MTAs and the fighters' material_anime_*.pac do) plus default.mta.

  python3 tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT MOTION_ROOT OUT_ROOT [KIND ...]     write the pacs
  python3 tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT --list                              the states, per kind

S3DS_ENEMY_ROOT: the 3DS dump's enemy folders (KIND/model/body/c00/normal.bch + normal.vmt); MOTION_ROOT holds the
converted motion/enemy/KIND/body/main.pac (the MTAs' names and lengths); OUT_ROOT gets
motion/enemy/KIND/body/material_anime.pac. KINDs: default every kind with a normal.vmt (the Wii U's own enemy kinds,
WIIU_KINDS, left out: they keep their Wii U files).

Why: on the 3DS the meshes listed in a model's normal.vmt are switched by code (Behavior::set_mesh_visibility(vmt
index, bool) -> the GsbDrawModel's vmt table; 39 enemies have one). The Wii U has no .vmt and draws every mesh: a
converted Waddle Dee shows its three parasols and both faces, a Waddle Doo every eye state at once. None of these
meshes is driven by a 3DS visibility animation (the material_anime .bch files have no tracks for them), and none of
these kinds has a converted material_anime.pac, so nothing is merged.

States (default = every motion but the damage ones):
- start from the model's own default visibility (the H3D model's visibility bit mask, one bit an object);
- hidden by default whatever the mask says: the damage meshes (name with "damage"), blinks, tears, the closed / wide
  open eyes (monoeye), and the alternatives a behaviour picks one of (ALT: keep the first);
- vmt names that are no object of the model (koshinigami's three) are left out;
- damage motions (Damage*, Down*, Collapses): the damage meshes shown (only the first of numbered ones), the "normal"
  ones hidden (the Goomba's own per-motion MTAs do the same with its damage / normal face);
- RULES: per kind, from the 3DS behaviour (enemy_fs.cro):
  waddledee (vmt 0 Cparasol, 1 Larm, 2 Lparasol, 3 Rarm, 4 Rparasol, 5 damage, 6 normal): its show function 0x5D04C
  for the variations without a parasol (2 / 3, and every variation once it is dropped, 0x5CF90): both arms, no
  parasol, normal face; its defeat 0x5CF18 shows the damage face. The parasol variations (0 / 1) hold one parasol
  that follows lr and the motion (0x5D0F0..): here none (that needs the per-frame code).
  waddledoo (0 eye_blink1, 1 eye_blink2, 2 eye_normal, 3 tear): open eyes, no blink frames, no tear.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mta  # noqa: E402
import omo  # noqa: E402

WIIU_KINDS = ('crazyhand', 'masterhand', 'mcanimal', 'mcblade', 'mcgiant', 'yellowdevil')
HIDE = ('damage', 'blink', 'tear', 'eye_close', 'wideopen')
# alternatives a behaviour shows one of: (kind, regex of the family); the first (sorted) stays
ALT = {
    'bonkers': (r'Lhand_\d', r'Rhand_\d'),
    'shinigami': (r'Face_[ab]',),
    'darknut': (r'sword_[ab]',),
}
RULES = {
    'waddledee': {'Cparasol': 0, 'Larm': 1, 'Lparasol': 0, 'Rarm': 1, 'Rparasol': 0, 'damage': 0, 'normal': 1},
    'waddledoo': {'eye_blink1': 0, 'eye_blink2': 0, 'eye_normal': 1, 'tear': 0},
}
DAMAGE_PREFIXES = ('Damage', 'Down', 'Collapses')


def short(kind, name):
    s = name
    for p in (kind + '_',):
        if s.startswith(p):
            s = s[len(p):]
    return s.replace('_VIS_O_OBJ', '').replace('_mh', '')


def model_states(kind, model_dir):
    """(vmt mesh names, {mesh: default 0/1}, {mesh: damage 0/1})"""
    import s3ds_model as M
    vmt = [x.decode('latin1') for x in open(os.path.join(model_dir, 'normal.vmt'), 'rb').read()[2:].split(b'\0')
           if x]
    m = M.Bch(open(os.path.join(model_dir, 'normal.bch'), 'rb').read()).models()[0]
    objs, bits = m['object_names'], m['visibility']
    vmt = [n for n in vmt if n in objs]          # koshinigami's vmt names meshes its model doesn't have
    default = {}
    for n in vmt:
        v = (bits >> objs.index(n)) & 1 if n in objs else 1
        low = short(kind, n).lower()
        if any(h in low for h in HIDE):
            v = 0
        default[n] = v
    for fam in ALT.get(kind, ()):
        members = sorted(n for n in vmt if re.fullmatch(fam, short(kind, n)))
        for i, n in enumerate(members):
            default[n] = 1 if i == 0 else 0
    if kind in RULES:
        for n in vmt:
            if short(kind, n) in RULES[kind]:
                default[n] = RULES[kind][short(kind, n)]
    damage = dict(default)
    dmg = sorted(n for n in vmt if 'damage' in short(kind, n).lower())
    if dmg:
        numbered = [n for n in dmg if re.search(r'\d$', short(kind, n))]
        for n in dmg:
            damage[n] = 0 if (numbered and n != numbered[0] and n in numbered) else 1
        for n in vmt:
            if 'normal' in short(kind, n).lower():
                damage[n] = 0
    return vmt, default, damage


def build(kind, main_pac, default, damage):
    """[(name, MTA bytes)]: one per OMO of main_pac (same stem, .mta) and default.mta"""
    prefix = 'Enm%sBodyMain' % kind.capitalize()
    out = []
    for name, data in omo.pac_read(main_pac):
        if not name.endswith('.omo'):
            continue
        stem = name[:-4]
        motion = stem[len(prefix):] if stem.startswith(prefix) else ''
        st = damage if motion.startswith(DAMAGE_PREFIXES) else default
        frames = max(1, int(omo.Omo(data).frames))
        out.append((stem + '.mta', mta.write(frames, [], vis=[(m, [(0, v)]) for m, v in sorted(st.items())])))
    out.append(('default.mta', mta.write(60, [], vis=[(m, [(0, v)]) for m, v in sorted(default.items())])))
    return out


def kinds(root):
    out = []
    for k in sorted(os.listdir(root)):
        if k not in WIIU_KINDS and os.path.exists(os.path.join(root, k, 'model', 'body', 'c00', 'normal.vmt')):
            out.append(k)
    return out


def main():
    if len(sys.argv) >= 3 and sys.argv[2] == '--list':
        root = sys.argv[1]
        for k in kinds(root):
            vmt, d, g = model_states(k, os.path.join(root, k, 'model', 'body', 'c00'))
            print('%-12s default %s' % (k, ' '.join('%s%s' % ('+' if d[n] else '-', short(k, n)) for n in vmt)))
            if g != d:
                print('%-12s damage  %s' % ('', ' '.join('%s%s' % ('+' if g[n] else '-', short(k, n)) for n in vmt)))
        return
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    root, mroot, out_root = sys.argv[1:4]
    for kind in sys.argv[4:] or kinds(root):
        vmt, default, damage = model_states(kind, os.path.join(root, kind, 'model', 'body', 'c00'))
        if not vmt:
            print('%s: no vmt mesh in the model, skipped' % kind)
            continue
        pac = os.path.join(mroot, 'motion', 'enemy', kind, 'body', 'main.pac')
        if not os.path.exists(pac):
            print('%s: no %s, skipped' % (kind, pac))
            continue
        entries = build(kind, pac, default, damage)
        d = os.path.join(out_root, 'motion', 'enemy', kind, 'body')
        os.makedirs(d, exist_ok=True)
        omo.pac_write(os.path.join(d, 'material_anime.pac'), entries)
        print('%s: material_anime.pac, %d MTAs' % (kind, len(entries)))


if __name__ == '__main__':
    main()
