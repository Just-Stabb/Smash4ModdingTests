#!/usr/bin/env python3
"""The Running Skeleton's collision box against its body (skeleton v1.5, fighters/gekkouga/README.md "Skeleton v1.5"):
his bank's PtcGekkougaSkeletonR (as the skeleton calls it: following its joint 0, facing right: local +Z ahead = screen
right) drawn by tools/fx_render.py at a few frames, with the box outlines: v1.5's body box (tools/gekkouga_clone_cave.py
SK_BODY: x +- 3.5, the walls from 2, the top 24) in green, v1 - v1.4's (x +- 6, top 28) dashed grey.

  python3 -I tools/gekkouga_skeleton_box_preview.py BUILT_FIGHTER OUT_PNG [--frames 0,14,28,42,56,70]
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import fx_render as F  # noqa: E402
import gekkouga_clone_cave as C  # noqa: E402
import ptcl  # noqa: E402

VIEW = (-22.0, 22.0, -4.0, 36.0)
PPU = 8.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--frames', default='0,14,28,42,56,70')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    frames = [int(x) for x in a.frames.split(',')]
    edir = os.path.join(a.built, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    ems = F.s4_emitters(p, ef.entries[0x16][1] - 1, {})
    tiles = []
    new = C.sk_verts(C.RELEASE)
    old = C.sk_verts(C.RELEASE - {'skbody'})
    for fr in frames:
        c = F.Canvas(*VIEW, PPU)
        c.rgb[:] = np.array([0.12, 0.12, 0.15])
        cm = F.call_matrix((0, 0, 0), (0, 0, 0), 1.0)
        for j, em in enumerate(ems):
            sim = F.simulate(em, (0, cm, 1.0, None), [fr], seed=j + 1)
            if sim[fr] and not F.draw_s4(c, em, sim[fr], cm @ F.emitter_matrix(em, fr), float(fr)):
                F.draw(c, em, sim[fr], cm)
        im = Image.fromarray(c.image())
        d = ImageDraw.Draw(im)
        px = lambda x, y: ((x - VIEW[0]) * PPU, (VIEW[3] - y) * PPU)   # noqa: E731
        for verts, col, dash in ((old, (150, 150, 150), True), (new, (60, 230, 90), False)):
            pts = [px(x, y) for x, y in ((verts[0][0], 0.0),) + tuple(verts) + ((verts[3][0], 0.0),)]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if dash:
                    n = int(max(abs(x1 - x0), abs(y1 - y0)) / 6) + 1
                    for k in range(0, n, 2):
                        d.line([(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n),
                                (x0 + (x1 - x0) * (k + 1) / n, y0 + (y1 - y0) * (k + 1) / n)], fill=col, width=2)
                else:
                    d.line([(x0, y0), (x1, y1)], fill=col, width=2)
        d.line([px(VIEW[0], 0), px(VIEW[1], 0)], fill=(90, 90, 110), width=1)
        d.text((6, 4), 'frame %d' % fr, fill=(230, 230, 230))
        tiles.append(im)
    w, h = tiles[0].size
    sheet = Image.new('RGB', (len(tiles) * (w + 4), h + 22), (18, 18, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * (w + 4), 22))
    ImageDraw.Draw(sheet).text((6, 5), 'Running Skeleton: v1.5 body box (green: x +- %g, top %g) vs v1 - v1.4 (grey: x +- %g, '
                               'top %g); facing right, offline render' % (new[2][0], new[2][1], old[2][0], old[2][1]),
                               fill=(220, 220, 220))
    sheet.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
