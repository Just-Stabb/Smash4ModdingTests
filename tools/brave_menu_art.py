#!/usr/bin/env python3
"""Hero's Command Selection window for the damage panel (fighters/brave/README.md), drawn after Ultimate's
(the international version, as on SmashWiki's Hero_MP_Comparison.png): a translucent black window with
rounded corners and a dark brown frame over the left of the panel, the four spell names in white, the gold
pointer by the chosen one, and a small window "MP nn" (the chosen spell's cost) at its bottom right.

  python3 tools/brave_menu_art.py OUT_DIR [--font FONT.ttf]

Writes OUT_DIR/window.png, cursor.png, name_<n>.png / name_<n>_grey.png (the 21 spells, n in the
order of Ultimate's commands, param_special_lw_command_data: SPELLS; grey: not enough MP) and
mp_<n>.png, all at ART_SCALE x the panel's units (LAYOUT: the 1-4 player panel's; tools/dmg_brave_menu.py
places them). Drawn at 4x and scaled down. The font: give the Wii U's shared font, FOT-Rodin (Cemu's
resources/sharedFonts/CafeStd.ttf), Ultimate's UI font family; without it Inter Medium stands in.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# the Wii U's shared font (FOT-Rodin, as Cemu's resources/sharedFonts/CafeStd.ttf; not in the repository):
# --font; without it a close stand-in
FONT = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
SS = 4
ART_SCALE = 1.25
# (name, MP cost: param_special_lw_command_data sp; Magic Burst uses all of it)
SPELLS = [('Heal', 7), ('Sizz', 8), ('Sizzle', 20), ('Bang', 9), ('Kaboom', 37), ('Whack', 10),
          ('Thwack', 30), ('Magic Burst', None), ('Kamikazee', 1), ('Kaclang', 6), ('Acceleratle', 13),
          ('Oomph', 16), ('Bounce', 14), ('Snooze', 16), ('Hocus Pocus', 4), ('Zoom', 8),
          ('Flame Slash', 12), ('Kacrackle Slash', 11), ('Metal Slash', 6), ('Hatchet Man', 15),
          ('Psyche Up', 14)]
# the 1-4 player panel's units (sprite 3 / 4; x right, y down; the panel is about x -230..200,
# y -100..95): Ultimate's proportions (its window 410 x 243 over a panel ~520 wide)
LAYOUT = dict(window=(-228, -100, 288, 172),     # left, top, w, h
              name_x=-194, rows=(-71.6, -32.8, 6.1, 45.2), name_h=32, name_w=256,
              cursor=(-224.5, 50, 24),           # centre x, w, h
              mp=(122, 44, 114, 56))             # centre x, y, w, h
WINDOW_FILL = (6, 4, 2, 132)
FRAME_OUT = (22, 10, 6, 255)
FRAME = (70, 36, 24, 255)
FRAME_IN = (26, 12, 8, 230)
WHITE = (255, 255, 255, 255)
GREY = (120, 120, 120, 255)


def font(path, px):
    return ImageFont.truetype(path, int(px))


def panel_window(w, h, radius):
    """a translucent black window, rounded, with Ultimate's dark brown frame (an outer dark line, the
    brown band, a dark inner line)"""
    W, H, r = w * SS, h * SS, radius * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = int(0.9 * SS)
    d.rounded_rectangle([o, o, W - 1 - o, H - 1 - o], r, fill=WINDOW_FILL, outline=FRAME_OUT, width=int(3.4 * SS))
    b = int(2.9 * SS)
    d.rounded_rectangle([o + b, o + b, W - 1 - o - b, H - 1 - o - b], r - b, outline=FRAME, width=int(2.8 * SS))
    b2 = b + int(2.8 * SS)
    d.rounded_rectangle([o + b2, o + b2, W - 1 - o - b2, H - 1 - o - b2], r - b2, outline=FRAME_IN, width=int(0.8 * SS))
    return im.resize((w, h), Image.LANCZOS)


def window(scale):
    _l, _t, w, h = LAYOUT['window']
    return panel_window(round(w * scale), round(h * scale), 9 * scale)


def mp_box(cost, path, scale):
    _x, _y, w, h = LAYOUT['mp']
    w, h = round(w * scale), round(h * scale)
    im = panel_window(w, h, 8 * scale).resize((w * SS, h * SS), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    big = font(path, h * SS * 0.56)
    small = font(path, h * SS * 0.40)
    num = 'ALL' if cost is None else str(cost)
    gap = h * SS * 0.16
    ws, wn = d.textlength('MP', font=small), d.textlength(num, font=big)
    x = (w * SS - ws - gap - wn) / 2
    y = h * SS * 0.53
    st = int(h * SS * 0.05)
    d.text((x, y), 'MP', font=small, fill=WHITE, anchor='lm', stroke_width=st, stroke_fill=(20, 10, 8, 255))
    d.text((x + ws + gap, y), num, font=big, fill=WHITE, anchor='lm', stroke_width=st, stroke_fill=(20, 10, 8, 255))
    return im.resize((w, h), Image.LANCZOS)


def name(text, colour, path, scale):
    """the spell's name, left aligned and vertically centred, with a soft dark shadow"""
    w, h = round(LAYOUT['name_w'] * scale), round(LAYOUT['name_h'] * scale)
    W, H = w * SS, h * SS
    f = font(path, H * 0.72)
    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(txt).text((SS * 2, H * 0.5), text, font=f, fill=colour, anchor='lm', stroke_width=int(SS * 0.15),
                             stroke_fill=colour)
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((SS * 2 + SS, H * 0.5 + SS), text, font=f, fill=(0, 0, 0, 170), anchor='lm',
                                stroke_width=SS, stroke_fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(SS * 0.8))
    shadow.alpha_composite(txt)
    return shadow.resize((w, h), Image.LANCZOS)


def cursor(scale):
    """Dragon Quest's gold pointer: two round knobs and a tapered blade, pointing right"""
    _x, w, h = LAYOUT['cursor']
    w, h = round(w * scale), round(h * scale)
    W, H = w * SS, h * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = H / 2
    dark, mid, light, hi = (92, 52, 8, 255), (196, 128, 24, 255), (240, 190, 60, 255), (255, 240, 170, 255)

    def ball(cx, r):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dark)
        r2 = r * 0.84
        d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=mid)
        d.ellipse([cx - r2 * 0.75, cy - r2 * 0.8, cx + r2 * 0.45, cy + r2 * 0.25], fill=light)
        d.ellipse([cx - r2 * 0.45, cy - r2 * 0.6, cx - r2 * 0.05, cy - r2 * 0.25], fill=hi)
    r1 = H * 0.34
    ball(W * 0.15, r1)
    ball(W * 0.33, r1 * 1.1)
    x0, x1 = W * 0.40, W * 0.97
    t = H * 0.20
    d.polygon([(x0, cy - t), (x0 + (x1 - x0) * 0.55, cy - t * 0.85), (x1, cy), (x0 + (x1 - x0) * 0.55, cy + t * 0.85),
               (x0, cy + t)], fill=dark)
    t2 = t * 0.7
    d.polygon([(x0 + SS, cy - t2), (x0 + (x1 - x0) * 0.55, cy - t2 * 0.85), (x1 - SS * 2, cy),
               (x0 + (x1 - x0) * 0.55, cy + t2 * 0.85), (x0 + SS, cy + t2)], fill=light)
    d.polygon([(x0 + SS, cy - t2), (x1 - SS * 2, cy), (x0 + SS, cy)], fill=hi)
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shadow.putalpha(im.getchannel('A').point(lambda v: v * 3 // 5))
    shadow = shadow.filter(ImageFilter.GaussianBlur(SS))
    base = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    base.alpha_composite(shadow, (SS, SS))
    base.alpha_composite(im)
    return base.resize((w, h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--font', default=FONT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    s = ART_SCALE
    window(s).save(os.path.join(a.out, 'window.png'))
    cursor(s).save(os.path.join(a.out, 'cursor.png'))
    for i, (nm, cost) in enumerate(SPELLS, 1):
        name(nm, WHITE, a.font, s).save(os.path.join(a.out, 'name_%d.png' % i))
        name(nm, GREY, a.font, s).save(os.path.join(a.out, 'name_%d_grey.png' % i))
        mp_box(cost, a.font, s).save(os.path.join(a.out, 'mp_%d.png' % i))
    print('%d spells -> %s' % (len(SPELLS), a.out))


if __name__ == '__main__':
    main()
