#!/usr/bin/env python3
"""Contact sheet of converted Smash Run effect models (tools/s3ds_effect_models.py), drawn from the written
folders only: model.nud meshes (bind 8: each in its bone's space) posed by model.omo (omo.world, a frame:
the middle one by default), textured from model.nut with the material's UV transform (NU_effRotUV / ScaleUV /
TransUV as the effect vertex program does it: s3ds_preview.nud_uv) and NU_effColorGain, blended as the material
says (additive / alpha / opaque). No lighting, no MTA.

  python3 tools/s3ds_effect_models_preview.py OUT_ROOT SHEET.png [KIND[/NAME]...] [--frame N] [--size 160]
"""
import argparse
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
from s3ds_preview import nud_uv, render  # noqa: E402


def items(d, frame=None):
    meshes = nud.read(os.path.join(d, 'model.nud'))
    bones = omo.vbn_read(os.path.join(d, 'model.vbn'))
    o = omo.Omo(open(os.path.join(d, 'model.omo'), 'rb').read())
    fr = o.frames // 2 if frame is None else min(frame, o.frames - 1)
    w = omo.world(o, bones, fr)
    dn, texs = nut.load(os.path.join(d, 'model.nut'))
    images = {t.tex_id: nut.decode(dn, t) for t in texs}
    out = []
    for m in meshes:
        bm = np.array(w[bones[m.bone][0]]) if 0 <= m.bone < len(bones) else np.eye(4)
        for p in m.polygons:
            mat = p.materials[0]
            props = dict(mat.props)
            gain = np.array(props.get('NU_effColorGain', [1, 1, 1, 1]), float)
            img = images[mat.textures[0]['hash']].astype(np.float64)
            img = np.clip(img * gain[None, None, :], 0, 255).astype(np.uint8)
            uv = nud_uv(p.uvs[0], props)
            pos = (bm @ np.c_[p.pos, np.ones(len(p.pos))].T).T[:, :3]
            tri = np.asarray(p.idx).reshape(-1, 3)
            out.append((pos, uv, np.r_[tri, tri[:, ::-1]], img, (mat.alpha_func, mat.ref_alpha, mat.src, mat.dst),
                        (mat.textures[0]['wrap_s'], mat.textures[0]['wrap_t'])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('sheet')
    ap.add_argument('only', nargs='*')
    ap.add_argument('--frame', type=int, default=None)
    ap.add_argument('--size', type=int, default=160)
    ap.add_argument('--yaw', type=float, default=30)
    ap.add_argument('--cols', type=int, default=8)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    dirs = sorted(glob.glob(os.path.join(a.out, 'effect', 'enemy', '*', 'model', '*')))
    if a.only:
        dirs = [d for d in dirs if any(('%s/model/%s' % tuple(x.split('/')) if '/' in x else '/%s/model/' % x) in d
                                       for x in a.only)]
    tiles = []
    for d in dirs:
        try:
            img = render(items(d, a.frame), a.size, a.yaw)
        except Exception as e:                       # noqa: BLE001 - one bad tile shouldn't stop the sheet
            img = np.zeros((a.size, a.size, 3), np.uint8)
            print('%s: %r' % (d, e))
        im = Image.fromarray(img)
        ImageDraw.Draw(im).text((3, 2), os.path.basename(d).replace('Efffs', ''), fill=(255, 255, 0))
        tiles.append(np.asarray(im))
    rows = []
    for i in range(0, len(tiles), a.cols):
        r = tiles[i:i + a.cols]
        r += [np.zeros_like(tiles[0])] * (a.cols - len(r))
        rows.append(np.concatenate(r, 1))
    Image.fromarray(np.concatenate(rows, 0)).save(a.sheet)
    print('%d tiles -> %s' % (len(tiles), a.sheet))


if __name__ == '__main__':
    main()
