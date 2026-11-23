#!/usr/bin/env python3
"""The smashes' fire trails as fire trail fix v1 places them (fighters/gekkouga/README.md "Fire trail fix v1"): his
bank's PtcGekkougaFireTrail (0x330001C) at each flame's offset on the trail's joint 0 (local Z: along its way; the
trail turned by its way as a fighter: +Z forward, so facing right +Z is screen right), drawn by tools/fx_render.py beside
a grey stand-in of him (Wait1) at the trail's place; one row a smash (forward / up / down), facing right.

  python3 -I tools/gekkouga_trail_preview.py VANILLA_FIGHTER BUILT_FIGHTER OUT_PNG [--frame 40]
"""
import argparse
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import fx_render as F  # noqa: E402
import gekkouga_nair_preview as NP  # noqa: E402
import omo  # noqa: E402
import ptcl  # noqa: E402

VIEW = (-95.0, 95.0, -4.0, 30.0)     # (tuning v1: forward smash's trail to 85)
ROOT = os.path.dirname(HERE)


def offsets():
    """(smash, [local Z]) from fighters/gekkouga/weapons/firetrail.c (tr_fx_count / tr_fx_dz / tr_fx_dx)"""
    out = []
    for t, name in ((1, 'forward'), (2, 'up'), (3, 'down')):
        if t == 1:                       # tuning v1's denser trails
            zs = [8.0 + 7.0 * k for k in range(12)]
        elif t == 2:
            zs = [(4.0 + 6.0 * (k // 2)) * (1 if k % 2 == 0 else -1) for k in range(8)]
        else:
            zs = [(6.0 + 7.0 * (k // 2)) * (1 if k % 2 == 0 else -1) for k in range(16)]
        out.append((name, zs))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--frame', type=int, default=40)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    src = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'firetrail.c')).read()
    assert 'return 4.0f + 6.0f * (float)(k / 2);' in src and 'return 8.0f + 7.0f * (float)k;' in src and \
        'return 6.0f + 7.0f * (float)(k / 2);' in src and 'return 0.85f + 0.1f * (float)((k * 3) % 4);' in src
    gid = int(re.search(r'int tr_fx\(\) \{ return (0x[0-9a-f]+); \}', src).group(1), 16)
    items, bones, bind = NP.model_items(a.vanilla)
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))['FitGekkougaBodyMainA00Wait1.omo'])
    posed = NP.pose(items, bones, bind, o, 0)
    for it in posed:
        it['img'] = np.full((2, 2, 4), 110, np.uint8)
    edir = os.path.join(a.built, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    ems = F.s4_emitters(p, ef.entries[gid & 0xFFFF][1] - 1, {})
    tiles = []
    for name, zs in offsets():
        c = F.Canvas(*VIEW, NP.PPU)
        c.rgb[:] = NP.BG
        NP.draw_model(c, posed)
        for k, z in enumerate(zs):
            cm = F.call_matrix((0.0, 0.0, z), (0, 0, 0), 0.85 + 0.1 * ((k * 3) % 4))
            for j, em in enumerate(ems):
                sim = F.simulate(em, (k, cm, 1.0, None), [a.frame], seed=7 * k + j + 1)
                if sim[a.frame] and not F.draw_s4(c, em, sim[a.frame], cm @ F.emitter_matrix(em, a.frame - k),
                                                  float(a.frame - k)):
                    F.draw(c, em, sim[a.frame], cm)
        im = Image.fromarray(c.image())
        ImageDraw.Draw(im).text((6, 4), '%s smash trail (local Z %s), facing right' % (name, ', '.join('%g' % z for z in zs)),
                                fill=(235, 235, 235))
        tiles.append(im)
    w, h = tiles[0].size
    sheet = Image.new('RGB', (w, 3 * (h + 4) + 22), (18, 18, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (0, 22 + i * (h + 4)))
    ImageDraw.Draw(sheet).text((6, 5), 'Greninja smash fire trails (tuning v1): 0x%X on the ground along X; offline '
                               'render, his grey stand-in at the trail\'s place' % gid, fill=(220, 220, 220))
    sheet.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
