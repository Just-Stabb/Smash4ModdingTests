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
expression faces (FaceN, Ouch, Talk ...), which the eyelid animation switches: they are left as they are (a forced
copy would show every expression's face at once).
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

# ---------------------------------------------------------------- the colours (change them here)
# (main, shading) greys, XV2 HUM.bcs HAIR_ colour 5 and eye_ colour 5 (the fallback until the user sends XV2's own Ultra
# Instinct colour data); SHEEN the faint blue-white tint on both
SILVER = {'hair': (0.80, 0.40), 'iris': (0.80, 0.40)}
SHEEN = (0.96, 0.99, 1.05)

COSTUMES = 8
TEX_BASE = 0x40C10000                # Supamario's own texture ids (fighter_texture_ids.py: kind 0x41), + 0x400 a costume
TEX_HAIR, TEX_IRIS = 0, 1            # + these
MESHES = {'hair': ('Mario_Hair_VIS_O_OBJ', 'Mario_HairUI_VIS_O_OBJ'),
          'nohat': ('Mario_Nohat_VIS_O_OBJ', 'Mario_NohatUI_VIS_O_OBJ'),
          'eye': ('Mario_Eye_VIS_O_OBJ', 'Mario_EyeUI_VIS_O_OBJ')}
PACS = ('material_anime_eyelid.pac', 'material_anime_eyelid_lang.pac')   # the ones with the hair / eye tracks
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
    for fn, retex in (('model.nud', True), ('metal.nud', False)):
        p = os.path.join(src, fn)
        if os.path.exists(p):
            copies = [(a, b, texmap[k] if retex else {}) for k, (a, b) in MESHES.items()]
            open(os.path.join(dst, fn), 'wb').write(nud.clone_meshes(open(p, 'rb').read(), copies))
    tracks = {a: (b, None) for a, b in MESHES.values()}
    added = 0
    for pk in PACS:
        p = os.path.join(src, pk)
        if not os.path.exists(p):
            continue

        def fn(_name, b):
            return mta.add_vis(b, tracks) if b[:4] == b'MTA4' else b
        new = mta.pac_map(open(p, 'rb').read(), fn)
        open(os.path.join(dst, pk), 'wb').write(new)
        added += 1
    return {'hair_id': '0x%08X' % hair_id, 'iris_id': '0x%08X' % iris_id, 'pacs': added,
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
