#!/usr/bin/env python3
"""Greninja's round down-special gauge (fighters/gekkouga/README.md "Clones v7"): its art from the user's vector set
(41672.eps "Futuristic user interface elements", its 5250 x 3500 JPG preview), the layer list the damage panel gets
(tools/gekkouga_gauge_flx.py) and the executable drives (tools/gekkouga_clone_cave.py GAUGE_LAYERS), and a preview.

  python3 tools/gekkouga_gauge_art.py extract PREVIEW.jpg OUT_DIR      # the layers' white + alpha textures (256 px)
  python3 tools/gekkouga_gauge_art.py preview ART_DIR OUT.gif SHEET.png  # an animated preview and a contact sheet

Layers (outer to inner): ticks (the preview's row 1 #3), dots (row 1 #5), arcs (row 1 #4), heavy (row 2 #5), each
turning at its own speed (degrees a frame, + clockwise), and the fill: the open arc meter (bottom centre) revealed
clockwise by the value (FILL_STEPS frames 0 % - 100 %). Tint: cyan (charge), blue (the ability), grey (burnout).
"""
import math
import os
import sys

import numpy as np
from PIL import Image

SIZE = 256
# name: (crop box in the 1050 x 700 preview's coordinates (x5 in the 5250 x 3500 JPG), scale in the gauge, degrees / frame,
# alpha 0-100: the panel's colour transform scale)
LAYERS = [('ticks', (310, 10, 455, 160), 1.00, 0.35, 45),
          ('dots', (588, 18, 728, 158), 0.80, -0.8, 60),
          ('arcs', (455, 25, 585, 152), 0.64, 1.5, 70),
          ('heavy', (588, 165, 725, 300), 0.30, -2.4, 55)]
FILL = ('meter', (500, 540, 665, 695), 0.50)
TRACK_ALPHA = 20                      # the fill's empty track (the whole meter, faint)
FILL_STEPS = 11                       # 0 %, 10 %, ... 100 %
TINTS = {1: (0, 190, 240), 2: (60, 110, 255), 3: (150, 150, 150)}   # charge cyan, ability blue, burnout grey


def crop(jpg, box):
    im = np.asarray(Image.open(jpg).convert('RGB')).astype(np.float32)
    x0, y0, x1, y1 = box
    a = np.max(im[y0 * 5:y1 * 5, x0 * 5:x1 * 5, 1:], axis=2) / 255.0
    ys, xs = np.where(a > 0.25)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape
    s = max(h, w)
    sq = np.zeros((s, s), np.float32)
    sq[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = a
    alpha = np.clip((sq - 0.08) / 0.6, 0, 1)
    rgba = np.dstack([np.ones_like(alpha)] * 3 + [alpha])
    return Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').resize((SIZE, SIZE), Image.LANCZOS)


def fill_frame(meter, k):
    """the meter revealed clockwise from 12 o'clock over k / (FILL_STEPS - 1) of the turn"""
    a = np.asarray(meter).copy()
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    ang = (np.degrees(np.arctan2(xx - SIZE / 2 + 0.5, -(yy - SIZE / 2 + 0.5))) + 360) % 360
    a[..., 3] = np.where(ang <= 360.0 * k / (FILL_STEPS - 1) + (0.01 if k else -1), a[..., 3], 0)
    return Image.fromarray(a, 'RGBA')


def extract(jpg, out):
    os.makedirs(out, exist_ok=True)
    for name, box, _s, _v, _a in LAYERS:
        crop(jpg, box).save(os.path.join(out, name + '.png'))
    meter = crop(jpg, FILL[1])
    meter.save(os.path.join(out, 'meter.png'))
    for k in range(FILL_STEPS):
        fill_frame(meter, k).save(os.path.join(out, 'fill_%02d.png' % k))


def compose(art, t, mode, value, px=200):
    """the gauge at frame t, mode 1-3, value 0-100 (the executable's drawing order and speeds)"""
    canvas = Image.new('RGBA', (px, px), (16, 18, 28, 255))
    tint = TINTS[mode]

    def put(img, scale, angle, alpha=100):
        s = max(1, int(px * scale))
        im = img.resize((s, s), Image.LANCZOS).rotate(-angle, resample=Image.BICUBIC)
        a = np.asarray(im).astype(np.float32)
        a[..., 0], a[..., 1], a[..., 2] = tint
        a[..., 3] *= alpha / 100.0
        layer = Image.fromarray(a.astype(np.uint8), 'RGBA')
        canvas.alpha_composite(layer, ((px - s) // 2, (px - s) // 2))
    for name, _b, scale, speed, alpha in LAYERS:
        put(Image.open(os.path.join(art, name + '.png')), scale, speed * t, alpha)
    put(Image.open(os.path.join(art, 'meter.png')), FILL[2], 0, TRACK_ALPHA)
    k = int(round(value / 100.0 * (FILL_STEPS - 1)))
    put(Image.open(os.path.join(art, 'fill_%02d.png' % k)), FILL[2], 0)
    return canvas


def preview(art, gif, sheet):
    frames = []
    seq = [(1, v) for v in range(0, 101, 4)] + [(1, 100)] * 12 + [(2, 100 - v) for v in range(0, 100, 4)] + \
          [(3, 100 - v) for v in range(0, 100, 5)]
    for t, (mode, v) in enumerate(seq):
        frames.append(compose(art, t * 4, mode, v).convert('P', palette=Image.ADAPTIVE))
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=50, loop=0)
    shots = [(1, 0), (1, 30), (1, 60), (1, 100), (2, 50), (3, 50)]
    sh = Image.new('RGBA', (200 * len(shots), 200), (0, 0, 0, 255))
    for i, (mode, v) in enumerate(shots):
        sh.paste(compose(art, 40 * i, mode, v), (200 * i, 0))
    sh.save(sheet)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'extract':
        extract(a[1], a[2])
    elif a and a[0] == 'preview':
        preview(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
