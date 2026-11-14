#!/usr/bin/env python3
"""A picture of the Super God Fist's scripted victim motion (tools/supamario_godfist_build.py: the hold's lean,
then flight_frame 1 .. GF_FLIGHT): a standing stick figure (Mario's Wait1 frame 0) placed at each frame's feet
offset and turned by its Rotation_Set X about its feet, side view (Supamario to the left, facing right; the victim
facing him), every Nth frame, one panel each (the label gives its distance in front of him).

  python3 tools/supamario_godfist_flight_render.py MAIN.pac MODEL.vbn OUT.png [EVERY]
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import supamario_godfist_build as B  # noqa: E402
from supamario_godfist_render import SKIP  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.exit(__doc__)
    from PIL import Image, ImageDraw
    every = int(a[3]) if len(a) > 3 else 2
    bones = omo.vbn_read(a[1])
    o = omo.Omo(dict(omo.pac_read(a[0]))['FitMarioBodyMainA00Wait1.omo'])
    w = omo.world(o, bones, 0)
    pts = {n: (w[n][2][3], w[n][1][3]) for n, _p, _h in bones}     # (z forward, y up) of the standing pose
    n_hold = B.STRIKE - B.JUMP_TO
    frames = [(B.HOLD_X, 0.0, -B.hold_lean(k, n_hold), 'hold') for k in range(n_hold)]
    frames += [B.flight_frame(k) + ('flight',) for k in range(1, B.GF_FLIGHT + 1)]
    sel = [k for k in range(len(frames)) if k % every == 0 or k == len(frames) - 1]
    cols, pw, ph, sc = 6, 220, 150, 9.0
    rows = (len(sel) + cols - 1) // cols
    im = Image.new('RGB', (cols * pw, rows * ph), (250, 250, 250))
    d = ImageDraw.Draw(im)
    for c, i in enumerate(sel):
        x, y, rx, kind = frames[i]
        ox, oy = (c % cols) * pw, (c // cols) * ph
        gy = oy + ph - 22
        d.line([(ox, gy), (ox + pw, gy)], fill=(150, 150, 150))
        r = math.radians(rx)
        col = (60, 90, 220) if kind == 'hold' else (210, 70, 40)

        def pt(n, r=r, y=y, ox=ox, gy=gy):
            # its forward is -x on screen (it faces him); Rotation_Set X = r tilts its up axis toward its forward:
            # forward -> (-cos r, -sin r), up -> (-sin r, cos r), about its feet
            fz, fy = pts[n]
            px = -fz * math.cos(r) - fy * math.sin(r)
            py = -fz * math.sin(r) + fy * math.cos(r)
            return ox + pw / 2 + px * sc, gy - (y + py) * sc
        for n, p, _h in bones:
            if p < 0 or p >= len(bones) or any(k in n for k in SKIP) or n in ('ThrowN', 'RotN', 'HipN', 'TransN'):
                continue
            d.line([pt(bones[p][0]), pt(n)], fill=col, width=2)
        hx, hy = pt('HeadN')
        d.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], outline=(0, 0, 0))
        lab = ('hold %d' % i) if kind == 'hold' else ('flight %d' % (i - n_hold + 1))
        d.text((ox + 4, gy + 4), '%s: x %.0f, X rot %.0f' % (lab, x, rx), fill=(0, 0, 0))
    im.save(a[2])


if __name__ == '__main__':
    main()
