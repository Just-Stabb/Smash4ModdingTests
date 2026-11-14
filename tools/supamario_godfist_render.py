#!/usr/bin/env python3
"""Stick-figure renders of a fighter motion (side view: +Z forward to the right; front view), for checking
poses offline (the Super God Fist animation, tools/supamario_godfist_anim.py).

  python3 tools/supamario_godfist_render.py MOTION.pac NAME.omo MODEL.vbn OUT.png FRAME [FRAME ...]

Left bones blue, right bones red, the rest black; the head a circle; fingers / face / helper bones left out.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402

SKIP = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky', 'Face', 'HLP', 'Have', 'Finger')


def panel(o, bones, fr, label, size=220, scale=10.0):
    from PIL import Image, ImageDraw
    w = omo.world(o, bones, fr)
    im = Image.new('RGB', (size * 2, size + 16), (245, 245, 245))
    d = ImageDraw.Draw(im)
    for view in (0, 1):
        ox = view * size

        def pt(m):
            x, y, z = m[0][3], m[1][3], m[2][3]
            return ox + size / 2 + (z if view == 0 else x) * scale / 1.6 - (60 if view == 0 else 0), size - 10 - y * scale / 1.6
        d.line([(ox, size - 10), (ox + size, size - 10)], fill=(180, 180, 180))
        for n, p, _h in bones:
            if p < 0 or p >= len(bones) or any(k in n for k in SKIP) or n in ('ThrowN', 'RotN', 'HipN'):
                continue
            c = {'L': (40, 90, 230), 'R': (220, 50, 40)}[n[0]] if n[0] in 'LR' and n[1].isupper() else (30, 30, 30)
            d.line([pt(w[bones[p][0]]), pt(w[n])], fill=c, width=3)
        hx, hy = pt(w['HeadN'])
        d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], outline=(0, 0, 0))
    d.text((4, size), label, fill=(0, 0, 0))
    return im


def sheet(o, bones, out, frames, cols=4):
    from PIL import Image
    ims = [panel(o, bones, f, 'frame %d / %d' % (f, o.frames)) for f in frames]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    s = Image.new('RGB', (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(ims):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    s.save(out)


def main():
    a = sys.argv[1:]
    if len(a) < 5:
        sys.exit(__doc__)
    e = dict(omo.pac_read(a[0]))
    sheet(omo.Omo(e[a[1]]), omo.vbn_read(a[2]), a[3], [int(x) for x in a[4:]])


if __name__ == '__main__':
    main()
