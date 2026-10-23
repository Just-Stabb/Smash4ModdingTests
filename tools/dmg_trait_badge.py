#!/usr/bin/env python3
"""Add the Kirby trait badge to the damage panel (ui/info/dmg): a new sprite (index 0x5F in the vanilla
dmg.flx) with one frame per trait image and no frame actions, placed as "trait_mc" in each per-player
panel clip (sprites 1-4, the dmg_k instances), and its images on a new texture img-00133.nut.

  python3 tools/dmg_trait_badge.py SRC_DMG_DIR BADGE_DIR OUT_DIR

BADGE_DIR holds trait_<name>.png (256x64) for the TRAITS below; frame i = TRAITS[i] (labels are the
trait names too). The game code picks the frame (goto frame + stop) and shows / hides the clip.
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402

TRAITS = ['normal', 'rush', 'shooter', 'strike', 'juggernaut', 'technical', 'barrage']
BADGE_W, BADGE_H, ROW = 256, 64, 72          # badges stacked in a 256x512 texture, 72 px apart
TEXTURE_ID = 0x2800FE00                      # unique GIDX (game UI uses 0x28000000-0x28006395)
# panel sprite -> (x, y, scale) of trait_mc: above the damage percent, right of the CPU level,
# in the band Little Mac's KO gauge (ko_mc) uses
PLACES = {1: (-2, -52, 0.4),                 # 5-8 players
          2: (-30, -27, 0.4),                # small panels (dmg_emy layouts)
          3: (24, -58, 0.5),                 # 1-2 players
          4: (24, -58, 0.5)}                 # 3-4 players


def build(src, badges, out):
    f = flx.read(open(os.path.join(src, 'dmg.flx'), 'rb').read())
    tl = flx.Tlst(open(os.path.join(src, 'texlist.lst'), 'rb').read())
    slot = len(tl.slots)
    tl.slots.append(0)                       # 0 = img-<slot>.nut in the folder
    sheet = np.zeros((512, BADGE_W, 4), np.uint8)
    frames = []
    for i, t in enumerate(TRAITS):
        img = np.asarray(Image.open(os.path.join(badges, 'trait_%s.png' % t)).convert('RGBA')
                         .resize((BADGE_W, BADGE_H), Image.LANCZOS))
        sheet[ROW * i:ROW * i + BADGE_H] = img
        name = 'inf_dmg_trait_%s' % t
        tl.add(name, slot, 0, ROW * i, BADGE_W, BADGE_H, BADGE_W, 512)
        frames.append([f.image_place(name, BADGE_W, BADGE_H, slot=i, depth=len(TRAITS) - 1 - i)])
    sprite = f.add_sprite(frames, labels={t: i for i, t in enumerate(TRAITS)})
    for panel, (x, y, s) in PLACES.items():
        f.insert_place(panel, f.sprite_place(sprite, 'trait_mc', flx.Transform.make(x, y, s)))
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sheet)]))
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return sprite


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    print('trait sprite 0x%X' % build(*sys.argv[1:]))
