#!/usr/bin/env python3
"""Add Hero's Command Selection window to the damage panel (ui/info/dmg), as Ultimate draws it over his
panel (tools/brave_menu_art.py): new sprites placed in each per-player panel clip (sprites 1-4):

  cmdwin_mc                the window (1 frame)
  spell0_mc - spell3_mc    the names, top to bottom: frame n = spell n (1-21), 21 + n = spell n greyed out
                           (not enough MP); labels name_<n> / grey_<n>
  cmdcur0_mc - cmdcur3_mc  the gold pointer by each row (1 frame)
  cmdmp_mc                 the small "MP nn" window: frame n = spell n's cost; labels mp_<n>

with their images on one new texture. The game code (tools/trait_badge_cave.py's menu) shows them on
Hero's panel, picks the frames, and hides them on every other panel.

  python3 tools/dmg_brave_menu.py SRC_DMG_DIR ART_DIR OUT_DIR

SRC_DMG_DIR: the damage panel to add to (the one with the Kirby trait badge, tools/dmg_trait_badge.py);
ART_DIR: tools/brave_menu_art.py's PNGs.
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402
from brave_menu_art import ART_SCALE, LAYOUT, SPELLS  # noqa: E402

SHEET = 1024
TEXTURE_ID = 0x2800FE01                      # unique GIDX (the trait badges' is 0x2800FE00)
ROWS = 4
# panel sprite -> (scale, dx, dy): brave_menu_art.LAYOUT is in the 1-4 player panel's units (sprites 3
# and 4); the others are that panel at 0.8, moved as the trait badge is (tools/dmg_trait_badge.py)
PANELS = {1: (0.8, -21.2, -5.6),              # 5-8 players
          2: (0.8, -49.2, 19.4),              # small panels (dmg_emy layouts)
          3: (1.0, 0.0, 0.0),                 # 1-2 players
          4: (1.0, 0.0, 0.0)}                 # 3-4 players


class Sheet:
    """a shelf packer onto one SHEET x SHEET texture"""
    def __init__(self):
        self.px = np.zeros((SHEET, SHEET, 4), np.uint8)
        self.x = self.y = self.h = 0

    def add(self, img):
        a = np.asarray(img.convert('RGBA'))
        h, w = a.shape[:2]
        if self.x + w > SHEET:
            self.x, self.y, self.h = 0, self.y + self.h + 2, 0
        assert self.y + h <= SHEET, 'menu art does not fit the sheet'
        x, y = self.x, self.y
        self.px[y:y + h, x:x + w] = a
        self.x += w + 2
        self.h = max(self.h, h)
        return x, y, w, h


def build(src, art, out):
    f = flx.read(open(os.path.join(src, 'dmg.flx'), 'rb').read())
    tl = flx.Tlst(open(os.path.join(src, 'texlist.lst'), 'rb').read())
    slot = len(tl.slots)
    tl.slots.append(0)                       # 0 = img-<slot>.nut in the folder
    sh = Sheet()

    def image(label, fn, cx, cy, i=0, n=1):
        x, y, w, h = sh.add(Image.open(os.path.join(art, fn)))
        name = 'inf_dmg_brave_%s' % label
        tl.add(name, slot, x, y, w, h, SHEET, SHEET)
        return f.image_place(name, w, h, cx=cx, cy=cy, slot=i, depth=n - 1 - i)

    n = len(SPELLS)
    names = [('name_%d' % i, 'name_%d.png' % i) for i in range(1, n + 1)] + \
            [('grey_%d' % i, 'name_%d_grey.png' % i) for i in range(1, n + 1)]
    name_sp = f.add_sprite([[image(lb, fn, 0.0, 0.5, i, len(names))] for i, (lb, fn) in enumerate(names)],
                           labels={lb: i for i, (lb, _fn) in enumerate(names)})
    mps = [('mp_%d' % i, 'mp_%d.png' % i) for i in range(1, n + 1)]
    mp_sp = f.add_sprite([[image(lb, fn, 0.5, 0.5, i, n)] for i, (lb, fn) in enumerate(mps)],
                         labels={lb: i for i, (lb, _fn) in enumerate(mps)})
    win_sp = f.add_sprite([[image('window', 'window.png', 0.0, 0.0)]])
    cur_sp = f.add_sprite([[image('cursor', 'cursor.png', 0.5, 0.5)]])

    k = 1.0 / ART_SCALE
    left, top, _w, _h = LAYOUT['window']
    cx, _cw, _ch = LAYOUT['cursor']
    mx, my, _mw, _mh = LAYOUT['mp']
    for panel, (s, dx, dy) in PANELS.items():
        def place(sprite, name, x, y):
            f.insert_place(panel, f.sprite_place(sprite, name, flx.Transform.make(s * x + dx, s * y + dy, s * k)))
        place(win_sp, 'cmdwin_mc', left, top)
        for r, ry in enumerate(LAYOUT['rows']):
            place(name_sp, 'spell%d_mc' % r, LAYOUT['name_x'], ry)
        for r, ry in enumerate(LAYOUT['rows']):
            place(cur_sp, 'cmdcur%d_mc' % r, cx, ry)
        place(mp_sp, 'cmdmp_mc', mx, my)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sh.px)]))
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return name_sp, slot


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    print('menu sprites from 0x%X, texture slot %d' % build(*sys.argv[1:]))
