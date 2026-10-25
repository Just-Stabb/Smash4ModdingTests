#!/usr/bin/env python3
"""Hero's Command Selection rows for the damage panel (fighters/brave/README.md): one plate a spell, in the
style of Dragon Quest's command windows (a dark window, a white frame, the name and the MP cost), plain
and highlighted (the cursor's row: a gold frame and the cursor triangle).

  python3 tools/brave_menu_art.py OUT_DIR [--font FONT.otf] [--size 256x40]

Writes OUT_DIR/spell_<n>.png and OUT_DIR/spell_<n>_sel.png (RGBA) for the 21 spells, n = 1-21 in the
order of Ultimate's commands (param_special_lw_command_data, SPELLS): the frame numbers
tools/dmg_brave_menu.py gives them (n plain, 21 + n highlighted). Drawn at 4x and scaled down.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
SS = 4
# (name, MP cost: param_special_lw_command_data sp; Magic Burst uses all of it)
SPELLS = [('Heal', 7), ('Sizz', 8), ('Sizzle', 20), ('Bang', 9), ('Kaboom', 37), ('Whack', 10),
          ('Thwack', 30), ('Magic Burst', None), ('Kamikazee', 1), ('Kaclang', 6), ('Acceleratle', 13),
          ('Oomph', 16), ('Bounce', 14), ('Snooze', 16), ('Hocus Pocus', 4), ('Zoom', 8),
          ('Flame Slash', 12), ('Kacrackle Slash', 11), ('Metal Slash', 6), ('Hatchet Man', 15),
          ('Psyche Up', 14)]
WINDOW = (12, 16, 38, 230)
FRAME = (240, 240, 240, 255)
GOLD = (255, 214, 80, 255)
TEXT = (255, 255, 255, 255)
SEL_TEXT = (255, 236, 150, 255)
COST = (190, 200, 230, 255)


def plate(name, cost, sel, size, font_path):
    w, h = size[0] * SS, size[1] * SS
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r, b = 5 * SS, 2 * SS
    d.rounded_rectangle([b, b, w - 1 - b, h - 1 - b], r, fill=WINDOW, outline=GOLD if sel else FRAME,
                        width=(3 if sel else 2) * SS)
    th = int(h * 0.5)
    left = int(h * 0.62)
    if sel:                                         # the cursor
        cy, s = h // 2, int(h * 0.17)
        x0 = int(h * 0.2)
        d.polygon([(x0, cy - s), (x0 + int(s * 1.5), cy), (x0, cy + s)], fill=GOLD)
    cost_txt = 'ALL' if cost is None else str(cost)
    cf = ImageFont.truetype(font_path, int(th * 0.8))
    cw = d.textlength(cost_txt, font=cf)
    right = w - int(h * 0.3)
    room = right - cw - int(h * 0.35) - left
    size_px = th
    while size_px > 8 and d.textlength(name, font=ImageFont.truetype(font_path, size_px)) > room:
        size_px -= 2
    f = ImageFont.truetype(font_path, size_px)
    d.text((left, h // 2), name, font=f, fill=SEL_TEXT if sel else TEXT, anchor='lm')
    d.text((right, h // 2), cost_txt, font=cf, fill=COST, anchor='rm')
    return im.resize(size, Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--font', default=FONT)
    ap.add_argument('--size', default='256x40')
    a = ap.parse_args()
    size = tuple(int(v) for v in a.size.split('x'))
    os.makedirs(a.out, exist_ok=True)
    for i, (name, cost) in enumerate(SPELLS, 1):
        plate(name, cost, False, size, a.font).save(os.path.join(a.out, 'spell_%d.png' % i))
        plate(name, cost, True, size, a.font).save(os.path.join(a.out, 'spell_%d_sel.png' % i))
    print('%d spells -> %s' % (len(SPELLS), a.out))


if __name__ == '__main__':
    main()
