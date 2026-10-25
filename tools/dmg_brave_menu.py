#!/usr/bin/env python3
"""Add Hero's Command Selection window and MP gauge to the damage panel (ui/info/dmg), as Ultimate draws them
over his panel (tools/brave_menu_art.py: Ultimate's own pieces and layout): new sprites placed in each
per-player panel clip (sprites 1-4):

  cmdwin_mc                the window: frames 1-5 opening (5 open), 6-9 closing, 10-13 the one-row window of
                           a cast spell on row 0-3 (wnd_hold_00), 14 open and greyed (the spell at the cursor
                           costs more MP than he has)
  spell0_mc - spell3_mc    the names, top to bottom: frame n = spell n (1-21), 21 + n = spell n greyed out
                           (not enough MP); labels name_<n> / grey_<n>
  cmdcur0_mc - cmdcur3_mc  the pointer by each row: its 16 frames spinning (Ultimate's arrow_00 textures)
  cmdmp_mc                 the small "MP nn" window: frame n = spell n's cost, 21 + n greyed; labels mp_<n>
  mpgauge_mc, mplabel_mc   the MP gauge's pill and its "MP" (1 frame)
  mpblue_mc, mpgreen_mc    the fills: frame v + 1 = v MP (green: the cost of the spell in view), Ultimate's
                           fill textures stretched as its gauge animation does (1 + 1.58 v px)
  mpnum_mc                 the number: frame v + 1 = v

with their images on one new texture. The game code (tools/trait_badge_cave.py's menu) shows them on
Hero's panel, picks the frames, and hides them on every other panel.

  python3 tools/dmg_brave_menu.py SRC_DMG_DIR ART_DIR OUT_DIR

SRC_DMG_DIR: the damage panel to add to (the one with the Kirby trait badge, tools/dmg_trait_badge.py);
ART_DIR: tools/brave_menu_art.py's PNGs and layout.json.
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402
from brave_menu_art import SPELLS  # noqa: E402

SHEET = 1024                                 # wide; 1024 or 2048 high, as the art needs
TEXTURE_ID = 0x2800FE01                      # unique GIDX (the trait badges' is 0x2800FE00)
ROWS = 4
# panel sprite -> (scale, dx, dy): layout.json is in the 1-4 player panel's units (sprites 3
# and 4); the others are that panel at 0.8, moved as the trait badge is (tools/dmg_trait_badge.py)
PANELS = {1: (0.8, -21.2, -5.6),              # 5-8 players
          2: (0.8, -49.2, 19.4),              # small panels (dmg_emy layouts)
          3: (1.0, 0.0, 0.0),                 # 1-2 players
          4: (1.0, 0.0, 0.0)}                 # 3-4 players


class Sheet:
    """a shelf packer onto one SHEET x SHEET texture"""
    def __init__(self, h=SHEET):
        self.px = np.zeros((h, SHEET, 4), np.uint8)
        self.x = self.y = self.h = 0

    def add(self, img):
        a = np.asarray(img.convert('RGBA'))
        h, w = a.shape[:2]
        if self.x + w > SHEET:
            self.x, self.y, self.h = 0, self.y + self.h + 2, 0
        assert self.y + h <= self.px.shape[0], 'menu art does not fit the sheet'
        x, y = self.x, self.y
        self.px[y:y + h, x:x + w] = a
        self.x += w + 2
        self.h = max(self.h, h)
        return x, y, w, h


# the window opening (frames 1-5, 5 = open) and closing (6-9): its height x these, about its middle
WINDOW_OPEN = (0.2, 0.45, 0.7, 0.9, 1.0)
WINDOW_CLOSE = (0.85, 0.6, 0.35, 0.12)
CURSOR_FRAMES = 16


def build(src, art, out):
    f = flx.read(open(os.path.join(src, 'dmg.flx'), 'rb').read())
    tl = flx.Tlst(open(os.path.join(src, 'texlist.lst'), 'rb').read())
    L = json.load(open(os.path.join(art, 'layout.json')))
    slot = len(tl.slots)
    tl.slots.append(0)                       # 0 = img-<slot>.nut in the folder
    sh = Sheet(2 * SHEET)
    size = {}
    pending = []

    def register(label, fn):
        """an image on the sheet (once) -> its symbol name"""
        name = 'inf_dmg_brave_%s' % label
        if name not in size:
            x, y, w, h = sh.add(Image.open(os.path.join(art, fn)))
            pending.append((name, x, y, w, h))
            size[name] = (w, h)
        return name

    def place(name, cx, cy, i=0, n=1, w=None, h=None):
        """an image drawn w x h (its own size by default) with its (cx, cy) fraction at the origin"""
        w0, h0 = size[name]
        return f.image_place(name, w0 if w is None else w, h0 if h is None else h, cx=cx, cy=cy, slot=i,
                             depth=n - 1 - i)

    def sprite(frames, labels=None):
        return f.add_sprite(frames, labels=labels)

    k = L['art_scale']                       # art px a panel unit
    n = len(SPELLS)
    names = [('name_%d' % i, 'name_%d.png' % i) for i in range(1, n + 1)] + \
            [('grey_%d' % i, 'name_%d_grey.png' % i) for i in range(1, n + 1)]
    # the names' images start 2 px left of their text
    name_sp = sprite([[place(register(lb, fn), 2.0 / Image.open(os.path.join(art, fn)).width, 0.5)]
                      for lb, fn in names], {lb: i for i, (lb, _fn) in enumerate(names)})
    mps = [('mp_%d' % i, 'mp_%d.png' % i) for i in range(1, n + 1)] + \
          [('mpgrey_%d' % i, 'mp_%d_grey.png' % i) for i in range(1, n + 1)]
    mp_sp = sprite([[place(register(lb, fn), 0.5, 0.5)] for lb, fn in mps], {lb: i for i, (lb, _fn) in enumerate(mps)})
    # the window (anchored at its top left): opening / closing, its height scaled about its middle; then the
    # one-row window at each row; then greyed
    win = register('window', 'window.png')
    ww, wh = size[win]
    win_frames = []
    for sc in WINDOW_OPEN + WINDOW_CLOSE:
        hs = max(1.0, wh * sc)
        win_frames.append([place(win, 0.0, -(wh - hs) / 2.0 / hs, h=hs)])
    hold = register('hold', 'hold.png')
    _hw, hh = size[hold]
    for top in L['hold_tops']:
        win_frames.append([place(hold, 0.0, -(top - L['window'][1]) * k / hh)])
    win_frames.append([place(register('window_grey', 'window_grey.png'), 0.0, 0.0)])
    win_sp = sprite(win_frames, {'open': len(WINDOW_OPEN) - 1})
    # the pointer: Ultimate's 16 spinning frames
    cur_sp = sprite([[place(register('cursor_%d' % c, 'cursor_%d.png' % c), 0.5, 0.5)] for c in range(CURSOR_FRAMES)])
    # the MP gauge: its pill, the blue / green fills (frame v + 1 = v MP, stretched from the left), the "MP"
    # label, the number (right-aligned digits)
    gauge_sp = sprite([[place(register('gauge', 'gauge.png'), 0.0, 0.5)]])
    label_sp = sprite([[place(register('gauge_label', 'gauge_label.png'), 0.5, 0.5)]])
    w0, w100 = L['fill_w']
    fill_sp = {}
    for c in ('blue', 'green'):
        fill = register('fill_' + c, 'fill_%s.png' % c)
        fill_sp[c] = sprite([[]] + [[place(fill, 0.0, 0.5, w=w0 + (w100 - w0) * v / 100.0)] for v in range(1, 101)])
    digits = [register('digit_%d' % d, 'digit_%d.png' % d) for d in range(10)]
    num_frames = []
    for v in range(101):
        fr, x = [], 0.0
        txt = str(v)
        for j, ch in enumerate(reversed(txt)):
            dn = digits[int(ch)]
            dw, _dh = size[dn]
            x -= dw * 0.78                   # the outlines overlap a little
            fr.append(place(dn, -x / dw, 0.5, j, len(txt)))
        num_frames.append(fr)
    num_sp = sprite(num_frames)

    for panel, (s, dx, dy) in PANELS.items():
        def put(sprite_, name, x, y):
            f.insert_place(panel, f.sprite_place(sprite_, name, flx.Transform.make(s * x + dx, s * y + dy, s / k)))
        gl, gcy, _gw, _gh = L['gauge']
        put(gauge_sp, 'mpgauge_mc', gl, gcy)
        put(fill_sp['green'], 'mpgreen_mc', L['fill_left'], gcy)
        put(fill_sp['blue'], 'mpblue_mc', L['fill_left'], gcy)
        put(label_sp, 'mplabel_mc', *L['gauge_label'])
        put(num_sp, 'mpnum_mc', *L['gauge_num'])
        put(win_sp, 'cmdwin_mc', L['window'][0], L['window'][1])
        for r, ry in enumerate(L['rows']):
            put(name_sp, 'spell%d_mc' % r, L['name_x'], ry)
        for r, ry in enumerate(L['rows']):
            put(cur_sp, 'cmdcur%d_mc' % r, L['cursor_x'], ry)
        put(mp_sp, 'cmdmp_mc', L['mp'][0], L['mp'][1])
    used = sh.y + sh.h
    sheet_h = SHEET if used <= SHEET else 2 * SHEET
    for name, x, y, w, h in pending:
        tl.add(name, slot, x, y, w, h, SHEET, sheet_h)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sh.px[:sheet_h])]))
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return name_sp, slot


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    print('menu sprites from 0x%X, texture slot %d' % build(*sys.argv[1:]))
