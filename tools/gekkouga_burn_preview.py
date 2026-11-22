#!/usr/bin/env python3
"""The burning fighter's fire by tier (skeleton v1.3 package, fighters/gekkouga/README.md "Skeleton v1.3"): his bank's
PtcGekkougaFireBody1 / FireBody / FireBody3 / FireBody4 (tools/gekkouga_clone_cave.py BFX_TIER_IDS) drawn by
tools/fx_render.py as the exe calls them (following the victim's joint 0, size 1), over a fighter silhouette (Greninja's
model in Wait1, flat grey: the stand-in victim), each at a few frames after it starts; a sheet, one column a tier.

  python3 -I tools/gekkouga_burn_preview.py VANILLA_FIGHTER BUILT_FIGHTER OUT_PNG [--frames 20,45]
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
import gekkouga_nair_preview as NP  # noqa: E402
import omo  # noqa: E402
import ptcl  # noqa: E402

VIEW = (-22.0, 22.0, -4.0, 62.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--frames', default='20,45')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    frames = [int(x) for x in a.frames.split(',')]
    items, bones, bind = NP.model_items(a.vanilla)
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))['FitGekkougaBodyMainA00Wait1.omo'])
    posed = NP.pose(items, bones, bind, o, 0)
    for it in posed:
        it['img'] = np.full((2, 2, 4), 110, np.uint8)            # flat grey: a silhouette
    edir = os.path.join(a.built, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    programs = {}
    rows = []
    for fr in frames:
        tiles = []
        for tier in range(1, 5):
            gid = C.BFX_TIER_IDS[tier]
            ems = F.s4_emitters(p, ef.entries[gid & 0xFFFF][1] - 1, programs)
            c = F.Canvas(*VIEW, NP.PPU)
            c.rgb[:] = NP.BG
            NP.draw_model(c, posed)
            cm = F.call_matrix((0, 0, 0), (0, 0, 0), 1.0)
            for j, em in enumerate(ems):
                sim = F.simulate(em, (0, cm, 1.0, None), [fr], seed=j + 1)
                if sim[fr] and not F.draw_s4(c, em, sim[fr], cm @ F.emitter_matrix(em, fr), float(fr)):
                    F.draw(c, em, sim[fr], cm)
            im = Image.fromarray(c.image())
            ImageDraw.Draw(im).text((6, 4), 'tier %d (0x%X), frame %d' % (tier, gid, fr), fill=(235, 235, 235))
            tiles.append(im)
        rows.append(tiles)
    w, h = rows[0][0].size
    sheet = Image.new('RGB', (4 * w + 12, len(rows) * (h + 4) + 22), (18, 18, 22))
    for r, tiles in enumerate(rows):
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * (w + 4), 22 + r * (h + 4)))
    rules = ', '.join('tier %d: %d+ burns / %g %% left / %g %%/s' % r for r in C.BFX_TIERS)
    ImageDraw.Draw(sheet).text((6, 5), 'Burn tiers (the strongest met; 1 with any burn): ' + rules + '; offline render',
                               fill=(220, 220, 220))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
