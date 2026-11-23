#!/usr/bin/env python3
"""A sword trail texture pair drawn as the game draws a Sword_Glow trail, on a sword swing: for comparing trail textures
(e.g. a new one against a fighter's vanilla pair) before a game test.

  python3 -I tools/trail_preview.py OUT.png LABEL=TEX1.nut,TEX2.nut[,SHADER] [LABEL=...] [--blur 8] [--y1 0.1 --y2 14]
      [--frames 3,5,7] [--bg 40,44,52]

TEX2 '-': no second texture (Texture2=0).
One row per pair, one column per frame of the swing (--frames: frames after the trail starts). The swing: a blade
from Y1 to Y2 on a joint 9 units from the shoulder, swung from overhead (110 degrees) down past the front (-35
degrees) in 9 frames with an ease-out (a forward tilt's arc, facing right; Corrin's Sword_Glow points are (0, 0.1, 0) /
(0, 14, 0) on her sword joint 0x19). The trail (docs/native-notes.md "Sword trails" / "The trail shaders", the game's
textured trail 0x032F84D0, as Sm4shCommand's Hitbox Viewer FxRaster.TrailTri): the blade's two points this frame and
the BlurLength frames before, 4 steps between each two; U = 1 - t along it (t 0 at the blade, 1 at the tail end), V
across the blade; vertex alpha (1 - t); shader 1: rgb = (t0.rgb t0.a + t1.rgb t1.a) va, a = t0.a va; shader 2: rgb =
(t0.rgb t0.a (1 - t1.a) + t1.rgb t1.a) va, a = t1.a va; premultiplied over the background (ONE / INV_SRC_ALPHA), as
the viewer does. The blade itself is a thin grey line. No bloom / HDR (the game's frame is lit and tone-mapped).
"""
import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nut  # noqa: E402

W, H, SCALE = 260, 220, 6.0         # pixels a panel, pixels per unit
PIVOT = (95.0, 150.0)               # the shoulder on the panel (pixels)


def texture(path):
    if path == '-':                     # no texture (Texture2=0): samples as 0
        return np.zeros((4, 4, 4), np.float32)
    d = open(path, 'rb').read()
    if d[:4] == b'NTP3' or (d[:2] == b'\x78\x9c' and nut.zlib.decompress(d)[:4] == b'NTP3'):
        img = nut.read_ntp3(d)[0][2]
    else:
        dd, texs = nut.load_bytes(d)
        img = nut.decode(dd, texs[0])
    return img.astype(np.float32) / 255.0


def sample(tex, u, v):
    """bilinear, clamped"""
    h, w = tex.shape[:2]
    x = np.clip(u, 0, 1) * (w - 1)
    y = np.clip(v, 0, 1) * (h - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) + tex[y1, x0] * (1 - fx) * fy
            + tex[y1, x1] * fx * fy)


def angle(f):
    """the arm's angle (degrees) at swing frame f (0-9, held after)"""
    s = min(max(f / 9.0, 0), 1)
    return 110 - 145 * (1 - (1 - s) ** 2)


def blade(f, y1, y2):
    """the blade's two points (pixels) at swing frame f"""
    a = math.radians(angle(f))
    d = (math.cos(a), -math.sin(a))
    base = (PIVOT[0] + 9 * SCALE * d[0], PIVOT[1] + 9 * SCALE * d[1])
    return [(base[0] + y * SCALE * d[0], base[1] + y * SCALE * d[1]) for y in (y1, y2)]


def tri(img, P, UV, TT, t0, t1, shader):
    (ax, ay), (bx, by), (cx, cy) = P
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if abs(area) < 1e-6:
        return
    x0, x1 = max(0, int(math.floor(min(ax, bx, cx)))), min(W - 1, int(math.ceil(max(ax, bx, cx))))
    y0, y1 = max(0, int(math.floor(min(ay, by, cy)))), min(H - 1, int(math.ceil(max(ay, by, cy))))
    if x0 > x1 or y0 > y1:
        return
    px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area
    w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area
    w2 = 1 - w0 - w1
    m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not m.any():
        return
    U = w0 * UV[0][0] + w1 * UV[1][0] + w2 * UV[2][0]
    V = w0 * UV[0][1] + w1 * UV[1][1] + w2 * UV[2][1]
    T = w0 * TT[0] + w1 * TT[1] + w2 * TT[2]
    s0, s1 = sample(t0, U, V), sample(t1, U, V)
    va = np.clip(1 - T, 0, 1)[..., None]
    if shader == 2:
        rgb = (s0[..., :3] * s0[..., 3:] * (1 - s1[..., 3:]) + s1[..., :3] * s1[..., 3:]) * va
        a = s1[..., 3:] * va
    else:
        rgb = (s0[..., :3] * s0[..., 3:] + s1[..., :3] * s1[..., 3:]) * va
        a = s0[..., 3:] * va
    a = np.minimum(a, 1)
    reg = img[y0:y1 + 1, x0:x1 + 1]
    out = reg * (1 - a) + rgb
    reg[m] = out[m]


def panel(t0, t1, shader, frame, blur, y1, y2, bg):
    img = np.ones((H, W, 3), np.float32) * np.array(bg, np.float32) / 255.0
    frames = [frame - k for k in range(blur + 1) if frame - k >= 0]
    pts = []
    for k in range(len(frames) - 1):
        for s in range(4 + (1 if k + 2 == len(frames) else 0)):
            pts.append(blade(frames[k] + (frames[k + 1] - frames[k]) * s / 4.0, y1, y2))
    n = len(pts)
    for i in range(n - 1):
        ti, tj = i / (n - 1.0), (i + 1) / (n - 1.0)
        a0, a1 = pts[i]
        b0, b1 = pts[i + 1]
        for P, UV, TT in (((a0, b0, b1), ((1 - ti, 0), (1 - tj, 0), (1 - tj, 1)), (ti, tj, tj)),
                          ((a0, b1, a1), ((1 - ti, 0), (1 - tj, 1), (1 - ti, 1)), (ti, tj, ti))):
            tri(img, P, UV, TT, t0, t1, shader)
    (bx0, by0), (bx1, by1) = blade(frame, y1 - 1, y2)
    for s in np.linspace(0, 1, 200):                # the blade
        x, y = int(bx0 + (bx1 - bx0) * s), int(by0 + (by1 - by0) * s)
        if 0 <= x < W and 0 <= y < H:
            img[max(0, y - 1):y + 1, max(0, x - 1):x + 1] = 0.75
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out')
    p.add_argument('pairs', nargs='+', help='LABEL=TEX1.nut,TEX2.nut[,SHADER]')
    p.add_argument('--blur', type=int, default=8)
    p.add_argument('--y1', type=float, default=0.1)
    p.add_argument('--y2', type=float, default=14.0)
    p.add_argument('--frames', default='3,5,7')
    p.add_argument('--bg', default='40,44,52')
    a = p.parse_args()
    from PIL import Image, ImageDraw
    frames = [int(x) for x in a.frames.split(',')]
    bg = [int(x) for x in a.bg.split(',')]
    rows = []
    for spec in a.pairs:
        label, files = spec.rsplit('=', 1)      # (a label may hold '=')
        parts = files.split(',')
        t0, t1 = texture(parts[0]), texture(parts[1])
        shader = int(parts[2]) if len(parts) > 2 else 1
        row = np.concatenate([panel(t0, t1, shader, f, a.blur, a.y1, a.y2, bg) for f in frames], 1)
        im = Image.fromarray((np.clip(row, 0, 1) * 255).astype(np.uint8))
        ImageDraw.Draw(im).text((6, 4), label, fill=(235, 235, 235))
        rows.append(np.asarray(im))
    Image.fromarray(np.concatenate(rows, 0)).save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
