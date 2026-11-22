#!/usr/bin/env python3
"""Burn tint v1 (fighters/gekkouga/README.md "Burn tint v1"): a burning fighter's colour overlay and faint red outline by
its fire's tier (tools/gekkouga_clone_cave.py BTINT_TINT / BTINT_SHELL), on Greninja's textured model in Wait1 (the
stand-in victim): the overlay as the fighter shaders draw it (lit x (1 - a) + rgb x a), the outline as a band of its
width round the silhouette (outline_shell_cave.py: pixels of a 1280 x 720 picture, here scaled to a fighter ~150 px tall
in it), drawn behind the body at its alpha. One column a tier, plus tier 4 halfway through the fade. Offline: the fire
itself is gekkouga_burn_preview.py's.

  python3 -I tools/gekkouga_tint_preview.py VANILLA_FIGHTER OUT_PNG
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fx_render as F  # noqa: E402
import gekkouga_clone_cave as C  # noqa: E402
import gekkouga_nair_preview as NP  # noqa: E402
import omo  # noqa: E402

VIEW = (-16.0, 16.0, -3.0, 26.0)
GAME_PX_PER_UNIT = 150.0 / 22.0     # a ~22-unit fighter ~150 px tall in a 1280 x 720 picture (the outline's unit)


def dilate(mask, r):
    out = mask.copy()
    ri = int(np.ceil(r))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('out')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    items, bones, bind = NP.model_items(a.vanilla)
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))['FitGekkougaBodyMainA00Wait1.omo'])
    posed = NP.pose(items, bones, bind, o, 0)
    ppu = 12.0
    base = F.Canvas(*VIEW, ppu)
    base.rgb[:] = NP.BG
    NP.draw_model(base, posed)
    body = np.any(np.abs(base.rgb - NP.BG) > 1e-4, axis=2)
    scale = ppu / GAME_PX_PER_UNIT
    cols = [(t, C.BTINT_FADE, 'tier %d' % t) for t in (1, 2, 3, 4)] + [(4, C.BTINT_FADE // 2, 'tier 4, fading (7/15)')]
    tiles = []
    for tier, fade, label in cols:
        tint, sh = C.btint_ref(tier, fade)
        rgb = base.rgb.copy()
        band = dilate(body, max(1.0, sh[4] * scale)) & ~body
        rgb[band] = rgb[band] * (1 - sh[3]) + np.array(sh[:3]) * sh[3]
        rgb[body] = rgb[body] * (1 - tint[3]) + np.array(tint[:3]) * tint[3]
        im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)[::1])
        d = ImageDraw.Draw(im)
        d.text((5, 4), label, fill=(235, 235, 235))
        d.text((5, 16), 'tint %.2f %.2f %.2f a %.2f' % tint, fill=(200, 200, 200))
        d.text((5, 28), 'outline a %.2f, %.2f px' % (sh[3], sh[4]), fill=(200, 200, 200))
        tiles.append(im)
    plain = Image.fromarray((np.clip(base.rgb, 0, 1) * 255).astype(np.uint8))
    ImageDraw.Draw(plain).text((5, 4), 'no burn', fill=(235, 235, 235))
    tiles.insert(0, plain)
    w, h = tiles[0].size
    sheet = Image.new('RGB', (len(tiles) * (w + 4), h + 26), (18, 18, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * (w + 4), 22))
    ImageDraw.Draw(sheet).text((6, 5), 'Burn tint v1: overlay (ColorBlendModule slot %d) + faint red outline by tier; '
                               'offline render, outline width approximate' % C.BTINT_SLOT, fill=(220, 220, 220))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
