#!/usr/bin/env python3
"""Supamario's Ultra Instinct v3: the silver hair and eyes. Per costume (model/body/cNN): silver copies of his hair
meshes and eyes in model.nud (metal.nud: the same copies, its own textures), the silver textures added to model.nut,
and the copies' visibility tracks (hidden all through) in the eyelid material animations, so they are hidden until
the transformation's burst shows them (Mesh_Visibility, tools/supamario_ui_build.py).

  python3 -I tools/supamario_ui_model.py SUPAMARIO_DIR OUT_FIGHTER_DIR [--png DIR]

The colours: SILVER (one place). Source: XV2's HUM.bcs (the user's; tools/xv2bcs.py): HAIR_ colour 5 (main 0.8 grey,
shading 0.4) and eye_ colour 5 (0.8 grey). An approximation: Ultra Instinct's own colours are the skill's part set /
power-up data, not sent (the skill's CUS names part set 122, an eye part of eye_ colour 1 = dark grey 0.11, not silver).

Mario's model (every costume the same meshes): Mario_Hair_VIS_O_OBJ (sideburns and back hair under the cap: a flat brown
texture 0x40KK..09 with a strand normal map, and a skin polygon), Mario_Nohat_VIS_O_OBJ (the full hair, shown only in
the side taunt's frames 17-72 with the cap off), Mario_Eye_VIS_O_OBJ (both irises: texture ..07, blue, an alpha oval,
over the white ..06; the material animations move its UVs by NU_materialHash, which the copy keeps, so it looks
around as his own does). The eyebrows and the mustache are one polygon (texture ..0B, near-black) of each of the 17
expression faces (FaceN, Ouch, Talk ...), which the eyelid animation switches (v3, the user: the mustache silver too;
the eyebrows with it, as his hair): OVERLAYS, silver copies of that polygon's mustache / eyebrow triangles, one per
distinct shape (the mustache 3: FaceN's in 10 expressions, Furafura's in 4, Damageflyfront's; the eyebrows 7), pushed
PUSH along the normals over his own, each following its expressions' visibility (the OR of their tracks, per motion;
hidden in the entry / win / lose / display motions) and kept hidden by Mesh_Visibility while he isn't transformed
(tools/supamario_ui_build.py: 10 overrides, from Entry / Wait1, which Rebirth plays), ended at the burst.
"""
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402

# ---------------------------------------------------------------- the colours (change them here: XV2_COLOURS only)
# XV2_COLOURS: the BCS colour entries used, each (group, index, its five RGBA colours as HUM.bcs has them: tools/xv2bcs.py
# colours). APPROXIMATED: the exact Ultra Instinct hair / eye colour indices are XV2's CUS aura table row for the skill's
# CUS aura (1), bcs_hair_color / bcs_eyes_color, which is in the game's executable (XV2 Patcher's CusAuraData), not in
# any file sent (powerup_parameter.pup entry 30 holds only stat multipliers; aura_setting.aur only effect ids; part set
# 122 only an eye part of eye_ colour 1, dark grey 0.11). The fallback: HAIR_ 5 (main 0.8 grey, shading 0.4) and eye_ 5
# (0.8 grey). When the indices are known, put those entries' five colours here.
# How they map onto Smash's textures: HAIR_ colour 1 (the main tone) is the hair / mustache / eyebrows texture's flat
# colour (Mario's own hair texture is flat: the game's lighting shades it); colour 2 (the shading tone) is not baked in
# (it would double the game's shading). eye_ colour 4 (its only one) is the iris ring's bright edge, its dark edge that
# times HAIR_'s shading / main ratio (0.5); the pupil and highlight stay as Mario's (greyed).
XV2_COLOURS = {
    'hair': ('HAIR_', 5, [(0.8, 0.8, 0.8, 1.0), (0.4, 0.4, 0.4, 1.0), (0.4, 0.4, 0.4, 1.0), (0.8, 0.8, 0.8, 1.0),
                          (0.0, 0.0, 0.0, 0.0)]),
    'iris': ('eye_', 5, [(0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0), (0.8, 0.8, 0.8, 1.0),
                         (0.0, 0.0, 0.0, 0.0)]),
}
EXACT = False                        # True once XV2_COLOURS holds the CUS aura row's entries


def _grey(c):
    return sum(c[:3]) / 3.0


_H = XV2_COLOURS['hair'][2]
_E = XV2_COLOURS['iris'][2]
# (main, shading) greys the textures use, from XV2_COLOURS
SILVER = {'hair': (_grey(_H[0]), _grey(_H[1])),
          'iris': (_grey(_E[3]), _grey(_E[3]) * _grey(_H[1]) / max(_grey(_H[0]), 1e-6))}
SHEEN = (0.96, 0.99, 1.05)           # the faint blue-white tint on both (Ultra Instinct's look: the clip's silver)

COSTUMES = 8
TEX_BASE = 0x40C10000                # Supamario's own texture ids (fighter_texture_ids.py: kind 0x41), + 0x400 a costume
TEX_HAIR, TEX_IRIS = 0, 1            # + these
MESHES = {'hair': ('Mario_Hair_VIS_O_OBJ', 'Mario_HairUI_VIS_O_OBJ'),
          'nohat': ('Mario_Nohat_VIS_O_OBJ', 'Mario_NohatUI_VIS_O_OBJ'),
          'eye': ('Mario_Eye_VIS_O_OBJ', 'Mario_EyeUI_VIS_O_OBJ')}
PACS = ('material_anime_eyelid.pac', 'material_anime_eyelid_lang.pac')   # the ones with the hair / eye / face tracks
FACE_TEX = 0x0B                      # the mustache / eyebrows polygon's texture (low byte)
BROW_Y = 11.8                        # its triangles above this (all three vertices): the eyebrows; below: the mustache
SAME = 0.01                          # two shapes the same: no vertex further than this from the other's
PUSH = 0.03                          # the overlays this far out along the normals
OVERLAY_HIDDEN = ('Entry', 'Win', 'Lose', 'display')      # motions (MTA names) with the overlays hidden all through
SRC_TEX = {'hair': 0x09, 'iris': 0x07}       # Mario's texture ids' low byte (0x40KK0000 + 0x400 x NN + this)


def tex_ids(nn):
    return TEX_BASE + 0x400 * nn + TEX_HAIR, TEX_BASE + 0x400 * nn + TEX_IRIS


def _rgb(grey):
    return np.clip(np.array(SHEEN) * grey, 0, 1)


def silver_hair(img):
    """Mario's hair texture (flat brown) -> the silver one: SILVER['hair']'s main grey, its shading where the texture is
    darker than its brightest (none on Mario's flat one), the sheen"""
    main, shade = SILVER['hair']
    v = img[..., :3].astype(float).max(2) / 255.0
    t = v / max(v.max(), 1e-6)
    g = shade + (main - shade) * t
    out = img.copy()
    out[..., :3] = np.round(255 * np.clip(g[..., None] * np.array(SHEEN), 0, 1))
    return out


def silver_iris(img):
    """Mario's iris texture (a blue ring, a dark blue pupil, a white highlight, an alpha oval) -> silver-grey: the ring
    from SILVER['iris']'s shading to its main grey by its brightness, the pupil a dark grey of its own brightness, the
    highlight white, the alpha unchanged"""
    main, shade = SILVER['iris']
    rgb = img[..., :3].astype(float) / 255.0
    v = rgb.max(2)
    s = np.where(v > 0, (v - rgb.min(2)) / np.maximum(v, 1e-6), 0)
    ring = shade + (main - shade) * np.clip((v - 0.5) / 0.3, 0, 1)
    t = np.clip((v - 0.35) / 0.3, 0, 1)
    t = t * t * (3 - 2 * t)
    g = (1 - t) * v * 0.5 + t * ring
    hi = np.clip((0.35 - s) / 0.25, 0, 1) * np.clip((v - 0.7) / 0.2, 0, 1)     # the white highlight kept
    g = g * (1 - hi) + v * hi
    out = img.copy()
    out[..., :3] = np.round(255 * np.clip(g[..., None] * np.array(SHEEN), 0, 1))
    return out


def _hausdorff(a, b):
    if len(a) != len(b):
        return 1e9
    dd = np.sqrt(((a[:, None] - b[None]) ** 2).sum(2))
    return max(dd.min(1).max(), dd.min(0).max())


def positions(p):
    """a polygon's vertex positions (an unrigged one's, or a rigged one's from its vertex add section: some costumes'
    faces are rigged, c04's)"""
    return p.pos if p.pos is not None else getattr(p, 'rpos', None)


def normals(p):
    return p.nrm if p.pos is not None else getattr(p, 'rnrm', None)


def overlays(meshes):
    """[{'name', 'source', 'poly', 'tris', 'members'}] from the model's meshes (nud.read): the mustache / eyebrows
    polygon (texture ..0B) of each face, its triangles split at BROW_Y, one overlay per distinct shape (SAME)"""
    groups = {'Mustache': [], 'Brows': []}
    for m in meshes:
        for j, p in enumerate(m.polygons):
            pos = positions(p)
            if pos is None or not p.materials or (p.materials[0].textures[0]['hash'] & 0xFF) != FACE_TEX:
                continue
            tri = p.idx.reshape(-1, 3)
            brow = (pos[tri][:, :, 1] > BROW_Y).all(1)
            for part, mask in (('Mustache', ~brow), ('Brows', brow)):
                t = np.nonzero(mask)[0]
                pts = pos[np.unique(tri[t])]
                for g in groups[part]:
                    if _hausdorff(g['pts'], pts) < SAME:
                        g['members'].append(m.name)
                        break
                else:
                    groups[part].append(dict(source=m.name, poly=j, tris=[int(x) for x in t], members=[m.name], pts=pts,
                                             part=part))
    out = []
    for part in ('Mustache', 'Brows'):
        for g in groups[part]:
            short = g['source'][len('Mario_'):-len('_VIS_O_OBJ')]
            out.append(dict(name='Mario_%s%sUI_VIS_O_OBJ' % (short, part), source=g['source'], poly=g['poly'],
                            tris=g['tris'], members=g['members'], part=part))
    return out


def or_keys(tracks, last):
    """the OR of step tracks [[(frame, state)]] (each state holds to its next key): [(frame, state)], a key where it
    changes (and at 0)"""
    frames = sorted({f for t in tracks for f, _s in t} | {0})
    out = []
    for f in frames:
        on = 0
        for t in tracks:
            cur = 0
            for kf, st in t:
                if kf <= f:
                    cur = st
            on |= cur
        if not out or out[-1][1] != on:
            out.append((f, on))
    if out[-1][0] != last and any(f == last for t in tracks for f, _s in t):
        out.append((last, out[-1][1]))       # the game's tracks end with a key on the last frame
    return out


def overlay_tracks(mta_name, vis, ovs):
    """[(overlay name, keys)] for one MTA's visibility tracks VIS ({mesh: [(frame, state)]}, last frame LAST)"""
    if not vis:
        return []
    hidden = any(k in mta_name for k in OVERLAY_HIDDEN)
    last = max(f for t in vis.values() for f, _s in t)
    out = []
    for o in ovs:
        have = [vis[m] for m in o['members'] if m in vis]
        if hidden:
            out.append((o['name'], [(0, 0)]))
        elif have:
            out.append((o['name'], or_keys(have, last)))
    return out


def costume(src, dst, nn, png=None):
    """one model folder: SRC (the base's cNN) -> DST (the files changed); returns a report"""
    os.makedirs(dst, exist_ok=True)
    hair_id, iris_id = tex_ids(nn)
    d, texs = nut.load(os.path.join(src, 'model.nut'))
    by = {t.tex_id & 0xFF: t for t in texs if (t.tex_id & 0xFFFFFC00) == 0x40110000 + 0x400 * nn}
    hair = silver_hair(nut.decode(d, by[SRC_TEX['hair']]))
    iris = silver_iris(nut.decode(d, by[SRC_TEX['iris']]))
    raw = open(os.path.join(src, 'model.nut'), 'rb').read()
    out = nut.append_ntwu(raw, [(hair_id, 0x31, hair), (iris_id, 0x33, iris)])
    open(os.path.join(dst, 'model.nut'), 'wb').write(out)
    if png:
        from PIL import Image
        os.makedirs(png, exist_ok=True)
        for name, img, t in (('hair', hair, SRC_TEX['hair']), ('iris', iris, SRC_TEX['iris'])):
            Image.fromarray(nut.decode(d, by[t]), 'RGBA').save(os.path.join(png, 'c%02d_%s_before.png' % (nn, name)))
            Image.fromarray(img, 'RGBA').save(os.path.join(png, 'c%02d_%s_after.png' % (nn, name)))
    texmap = {'hair': {0: {0: hair_id}}, 'nohat': {0: {0: hair_id}}, 'eye': {0: {0: iris_id}, 1: {0: iris_id}}}
    ovs = overlays(nud.read(os.path.join(src, 'model.nud')))
    for fn, retex in (('model.nud', True), ('metal.nud', False)):
        p = os.path.join(src, fn)
        if os.path.exists(p):
            copies = [(a, b, texmap[k] if retex else {}) for k, (a, b) in MESHES.items()]
            copies += [(o['source'], o['name'], {o['poly']: {0: hair_id}} if retex else {},
                        {'polys': [o['poly']], 'tris': {o['poly']: o['tris']}, 'push': PUSH}) for o in ovs]
            open(os.path.join(dst, fn), 'wb').write(nud.clone_meshes(open(p, 'rb').read(), copies))
    tracks = {a: (b, None) for a, b in MESHES.values()}
    added = 0
    for pk in PACS:
        p = os.path.join(src, pk)
        if not os.path.exists(p):
            continue

        def fn(name, b):
            if b[:4] != b'MTA4':
                return b
            vis = {v['name']: [(f, s) for f, s, _ in v['keys']] for v in mta.read(b)['vis']}
            return mta.add_vis(b, tracks, overlay_tracks(name, vis, ovs))
        new = mta.pac_map(open(p, 'rb').read(), fn)
        open(os.path.join(dst, pk), 'wb').write(new)
        added += 1
    return {'hair_id': '0x%08X' % hair_id, 'iris_id': '0x%08X' % iris_id, 'pacs': added,
            'overlays': {o['name']: o['members'] for o in ovs},
            'hair_rgb': [int(x) for x in hair[0, 0, :3]]}


def build(sm_dir, fighter_out, png=None):
    rep = {}
    for nn in range(COSTUMES):
        src = os.path.join(sm_dir, 'model', 'body', 'c%02d' % nn)
        if os.path.isdir(src):
            rep['c%02d' % nn] = costume(src, os.path.join(fighter_out, 'model', 'body', 'c%02d' % nn), nn, png)
    return rep


def main():
    a = sys.argv[1:]
    png = None
    if '--png' in a:
        i = a.index('--png')
        png = a[i + 1]
        del a[i:i + 2]
    if len(a) != 2:
        sys.exit(__doc__)
    for k, v in build(a[0], a[1], png).items():
        print(k, v)


if __name__ == '__main__':
    main()
