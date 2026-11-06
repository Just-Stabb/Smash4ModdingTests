#!/usr/bin/env python3
"""Contact sheet of converted Smash Run enemy effects (tools/s3ds_effects.py), drawn from the written Wii U
.ptcl by tools/fx_render.py's eft model (stage 1: the CPU's emission, motion, life curves, the written BC4
shape x colour; a side view, 5-unit grid, the emitter set at the origin): a row a set, a column a frame.

  python3 tools/s3ds_effects_preview.py FILE.ptcl SHEET.png [--frames 0,4,8,16,24] [--view -30,30,-20,40]
"""
import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fx_render as fx  # noqa: E402
import ptcl  # noqa: E402


def tiled(tex, p, d, n=128):
    """the texture as the quad shows it: slot 0's UV scale (repeat / cells) and wrap (eft's: 0 mirror, 1
    repeat, 2 clamp; the stage-1 drawing samples the quad's 0-1 UVs straight)"""
    if tex is None:
        return tex
    su, sv = p.field(d, 'tex0_uv_scale')
    word = struct.unpack_from('>I', bytes(d), ptcl.TEXRES + 0x0C)[0]
    wu, wv = (word >> 24) & 0xF, (word >> 28) & 0xF

    def wrap(x, mode):
        if mode == 1:
            return np.mod(x, 1.0)
        if mode == 0:
            x = np.mod(x, 2.0)
            return np.where(x > 1, 2 - x, x)
        return np.clip(x, 0, 1)
    h, w = tex.shape[:2]
    u = wrap((np.arange(n) + 0.5) / n * su, wu)
    v = wrap((np.arange(n) + 0.5) / n * sv, wv)
    return tex[np.clip((v * h).astype(int), 0, h - 1)][:, np.clip((u * w).astype(int), 0, w - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ptcl')
    ap.add_argument('sheet')
    ap.add_argument('--frames', default='0,4,8,16,24')
    ap.add_argument('--view', default='-30,30,-20,40')
    ap.add_argument('--scale', type=float, default=2.5)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    fx.S4_SHADERS = False
    p = ptcl.Ptcl(open(a.ptcl, 'rb').read())
    frames = [int(x) for x in a.frames.split(',')]
    view = [float(x) for x in a.view.split(',')]
    rows = []
    for si in range(len(p.sets)):
        canv = {fr: fx.Canvas(*view, a.scale) for fr in frames}
        datas = [e['data'] for e in p.sets[si]['emitters'] if e['data'] is not None]
        for k, em in enumerate(fx.s4_emitters(p, si)):
            em.tex = tiled(em.tex, p, datas[k])
            sim = fx.simulate(em, (0, np.eye(4), 1.0, None), frames, seed=k + 1)
            for fr in frames:
                fx.draw(canv[fr], em, sim[fr], np.eye(4))
        tiles = [canv[fr].image() for fr in frames]
        row = np.concatenate([np.asarray(t) for t in tiles], 1)
        im = Image.fromarray(row)
        ImageDraw.Draw(im).text((3, 2), p.set_name(si), fill=(255, 255, 0))
        rows.append(np.asarray(im))
    Image.fromarray(np.concatenate(rows, 0)).save(a.sheet)
    print('%d sets -> %s' % (len(rows), a.sheet))


if __name__ == '__main__':
    main()
