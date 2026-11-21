#!/usr/bin/env python3
"""How many polygon parts' Outline_Shell bands cover each band pixel (the cave draws the inverted hull once per polygon
part: with Blend 1 the layers add). Supamario Ultra Instinct v9's check that the white band was not the layering
(README "Ultra Instinct v9" 1): the meshes he draws transformed in Wait, bind pose, side view (the battle camera looks
along his side).

  python3 tools/outline_shell_layers.py MODEL.nud PX_PER_UNIT WIDTH_PX
      (the v7 clip: Supamario ~6.7 px a unit, the band 3 px)
"""
import sys, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import nud
from PIL import Image, ImageDraw
path, PX, WIDTH = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
VIS = ('Mario_FaceN_VIS_O_OBJ', 'Mario_FaceNMClose_VIS_O_OBJ', 'Gamemodel', 'Mario_NohatUI_VIS_O_OBJ',
       'Mario_EyeUI_VIS_O_OBJ', 'Mario_FaceNMustacheUI_VIS_O_OBJ', 'Mario_FaceNBrowsUI_VIS_O_OBJ')
ms = [m for m in nud.read(path) if m.name in VIS]
parts = []
for m in ms:
    for p in m.polygons:
        idx = p.idx
        if p.strip == 0x40:
            tri = idx.reshape(-1, 3)
        else:
            t = []
            for k in range(len(idx) - 2):
                a, b, c = idx[k:k + 3]
                if 0xFFFF in (a, b, c) or len({a, b, c}) < 3:
                    continue
                t.append((a, b, c) if k % 2 == 0 else (b, a, c))
            tri = np.array(t)
        pos = p.pos if p.pos is not None else getattr(p, "rpos", None)
        if pos is None or len(tri) == 0:
            continue
        parts.append((m.name, pos, tri))
allp = np.concatenate([p for _n, p, _t in parts])
# side view: screen x = model z (his facing), screen y = -model y
zmin, zmax, ymin, ymax = allp[:, 2].min(), allp[:, 2].max(), allp[:, 1].min(), allp[:, 1].max()
pad = 10
W = int((zmax - zmin) * PX) + 2 * pad
H = int((ymax - ymin) * PX) + 2 * pad
masks = []
for name, pos, tri in parts:
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    sx = (pos[:, 2] - zmin) * PX + pad
    sy = (ymax - pos[:, 1]) * PX + pad
    for a, b, c in tri:
        d.polygon([(sx[a], sy[a]), (sx[b], sy[b]), (sx[c], sy[c])], fill=1)
    masks.append(np.array(im, bool))
def dil(mk, r):
    out = mk.copy()
    R = int(np.ceil(r))
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(mk, dy, 0), dx, 1)
    return out
union = np.any(masks, 0)
band = dil(union, WIDTH) & ~union
cnt = np.zeros((H, W), int)
for mk in masks:
    dm = dil(mk, WIDTH)
    cnt += dm
c = cnt[band]
print('parts drawn', len(masks), 'band pixels', band.sum())
for n in range(1, 8):
    print('  covered by %d part(s): %.1f%%' % (n, 100.0 * (c == n).sum() / len(c)))
print('  by more than 7: %.1f%%' % (100.0 * (c > 7).sum() / len(c)))
print('mean layers %.2f' % c.mean())
