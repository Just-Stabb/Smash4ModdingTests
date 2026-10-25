#!/usr/bin/env python3
"""Add Hero's Command Selection menu to the damage panel (ui/info/dmg): a new sprite (the spell row) with
one frame per spell plate (frames 1-21 the spells plain, 22-42 highlighted: the cursor's row; labels
spell_<n> / sel_<n>, no frame actions), placed four times, as "spell0_mc" (top) ... "spell3_mc", in each
per-player panel clip (sprites 1-4), and its plates on a new texture.

  python3 tools/dmg_brave_menu.py SRC_DMG_DIR ART_DIR OUT_DIR

SRC_DMG_DIR: the damage panel to add to (the one with the Kirby trait badge, tools/dmg_trait_badge.py);
ART_DIR: tools/brave_menu_art.py's spell_<n>.png / spell_<n>_sel.png (256 x 40). The game code
(tools/trait_badge_cave.py's menu) shows the rows of Hero's panel, picks their frames and hides them on
every other panel.
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402
from brave_menu_art import SPELLS  # noqa: E402

W, H = 256, 40
SHEET_W, SHEET_H = 512, 1024                 # 2 columns of 25 rows: 42 plates
TEXTURE_ID = 0x2800FE01                      # unique GIDX (the trait badges' is 0x2800FE00)
ROWS = 4
# panel sprite -> (x, y of the bottom row's centre, scale): rows stacked up from above the panel's top
# edge (over the damage percent and the trait badge's band), one plate + 1 px apart
PLACES = {1: (-2, -84, 0.45),                # 5-8 players
          2: (-30, -50, 0.4),                # small panels (dmg_emy layouts)
          3: (24, -112, 0.6),                # 1-2 players
          4: (24, -112, 0.6)}                # 3-4 players


def build(src, art, out):
    f = flx.read(open(os.path.join(src, 'dmg.flx'), 'rb').read())
    tl = flx.Tlst(open(os.path.join(src, 'texlist.lst'), 'rb').read())
    slot = len(tl.slots)
    tl.slots.append(0)                       # 0 = img-<slot>.nut in the folder
    sheet = np.zeros((SHEET_H, SHEET_W, 4), np.uint8)
    frames, labels = [], {}
    plates = [('spell_%d' % n, 'spell_%d.png' % n) for n in range(1, len(SPELLS) + 1)] + \
             [('sel_%d' % n, 'spell_%d_sel.png' % n) for n in range(1, len(SPELLS) + 1)]
    for i, (label, fn) in enumerate(plates):
        img = np.asarray(Image.open(os.path.join(art, fn)).convert('RGBA').resize((W, H), Image.LANCZOS))
        x, y = W * (i % 2), H * (i // 2)
        sheet[y:y + H, x:x + W] = img
        name = 'inf_dmg_brave_%s' % label
        tl.add(name, slot, x, y, W, H, SHEET_W, SHEET_H)
        frames.append([f.image_place(name, W, H, slot=i, depth=len(plates) - 1 - i)])
        labels[label] = i
    sprite = f.add_sprite(frames, labels=labels)
    for panel, (x, y, s) in PLACES.items():
        step = H * s + 1
        for k in range(ROWS):
            f.insert_place(panel, f.sprite_place(sprite, 'spell%d_mc' % k,
                                                 flx.Transform.make(x, y - step * (ROWS - 1 - k), s)))
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sheet)]))
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return sprite, slot


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    print('spell row sprite 0x%X, texture slot %d' % build(*sys.argv[1:]))
