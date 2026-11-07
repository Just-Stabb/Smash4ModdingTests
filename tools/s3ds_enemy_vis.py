#!/usr/bin/env python3
"""Mesh visibility for the converted 3DS enemies that switch meshes by code: writes
motion/enemy/KIND/body/material_anime.pac, one MTA a motion (visibility by mesh name, as the converter's per-motion
MTAs and the fighters' material_anime_*.pac do) plus default.mta.

  python3 tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT MOTION_ROOT OUT_ROOT [KIND ...]     write the pacs
  python3 tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT --list                              the states, per kind
  python3 tools/s3ds_enemy_vis.py S3DS_ENEMY_ROOT --nud CONVERTED_ROOT OUT_ROOT [KIND ...]
        the baseline: model/enemy/KIND/body/c00/model.nud with every mesh hidden by default drawn as nothing

The material_anime.pac files turned out to do nothing in game (Cemu, fix v3: Waddle Doo's eye pieces and the
Goomba's two faces stayed; the Goomba's converted per-motion face pac never ran either): the Wii U does not play
motion/enemy/.../material_anime.pac for enemies. The baseline that works without it (--nud): the NUD itself, each
default-hidden mesh's polygons with their indices zeroed (nud.hidden's way: the mesh, its materials and bones stay,
nothing is drawn), so an enemy shows only its 3DS default meshes; the damage faces / blinks stay hidden for good.
Kinds: every vmt kind above, plus the ones whose converted material_anime.pac carries a visibility default
(default.mta: kuribo, dekakuribo, keronpa: their damage faces).

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


def hide_meshes(nud_bytes, names):
    """the NUD with the polygons of the meshes NAMES drawn as nothing (indices zeroed); (bytes, names hidden)"""
    import struct
    import zlib
    d = bytearray(nud_bytes)
    packed = d[:2] == b'\x78\x9c'
    if packed:
        d = bytearray(zlib.decompress(d))
    assert d[:4] == b'NDP3', d[:4]
    _, _ver, nmesh, _bs, _be, pstart, psize, vsize, vasize = struct.unpack('>IHhhhiiii', d[4:0x20])
    str_base = 0x30 + pstart + psize + vsize + vasize
    done = []
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        name_off, = struct.unpack('>i', d[o + 32:o + 36])
        name = d[str_base + name_off:d.index(b'\0', str_base + name_off)].decode('latin1')
        if name not in names:
            continue
        npoly, obj = struct.unpack('>hi', d[o + 42:o + 48])
        for j in range(npoly):
            q = obj + j * 0x30
            poff, = struct.unpack('>i', d[q:q + 4])
            nidx, = struct.unpack('>H', d[q + 32:q + 34])
            a = 0x30 + pstart + poff
            d[a:a + 2 * nidx] = bytes(2 * nidx)
        done.append(name)
    out = bytes(d)
    return (zlib.compress(out) if packed else out), done


def pac_defaults(conv, kind):
    """{mesh: 0/1} of the converted material_anime.pac's default.mta (the 3DS default material animation), or {}"""
    p = os.path.join(conv, 'motion', 'enemy', kind, 'body', 'material_anime.pac')
    if not os.path.exists(p):
        return {}
    for name, data in omo.pac_read(p):
        if name == 'default.mta':
            return {v['name']: v['keys'][0][1] for v in mta.read(data)['vis'] if v['keys']}
    return {}


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
    if len(sys.argv) >= 5 and sys.argv[2] == '--nud':
        root, conv, out_root = sys.argv[1], sys.argv[3], sys.argv[4]
        names = sys.argv[5:] or sorted(set(kinds(root)) | {'kuribo', 'dekakuribo', 'keronpa'})
        for kind in names:
            hide = {n for n, v in pac_defaults(conv, kind).items() if not v}
            if os.path.exists(os.path.join(root, kind, 'model', 'body', 'c00', 'normal.vmt')):
                _vmt, default, _dmg = model_states(kind, os.path.join(root, kind, 'model', 'body', 'c00'))
                hide |= {n for n, v in default.items() if not v}
            src = os.path.join(conv, 'model', 'enemy', kind, 'body', 'c00', 'model.nud')
            if not hide or not os.path.exists(src):
                print('%s: %s' % (kind, 'nothing hidden by default' if hide == set() else 'no %s' % src))
                continue
            b, done = hide_meshes(open(src, 'rb').read(), hide)
            d = os.path.join(out_root, 'model', 'enemy', kind, 'body', 'c00')
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'model.nud'), 'wb').write(b)
            print('%s: model.nud, hidden %s%s' % (kind, ' '.join(short(kind, n) for n in sorted(done)),
                                                 '' if set(done) == hide else ' (not in the NUD: %s)'
                                                 % sorted(hide - set(done))))
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
