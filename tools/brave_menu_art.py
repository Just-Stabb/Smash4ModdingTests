#!/usr/bin/env python3
"""Hero's Command Selection window and MP gauge for the damage panel (fighters/brave/README.md), from
Ultimate's own: its battle HUD layout (ui/layout/info/info_melee/info_melee/layout.arc: the part
p4_info_melee_lct_brave, its textures in timg/__Combined.bntx) gives the pieces and where they go.

  python3 tools/brave_menu_art.py LAYOUT_ARC OUT_DIR [--font FONT.ttf]

Writes OUT_DIR/ (tools/dmg_brave_menu.py puts them on the panel):
  window.png, window_grey.png  wnd_open_00 (p4_rep_info_melee_lct_brave_wind_00), grey: its white x 60/255
                               (wnd_color_gray_out: the spell at the cursor costs more MP than he has)
  hold.png                     wnd_hold_00 (wind_01): the cast spell's row alone (view_wnd_hold_0K)
  cursor_<k>.png               arrow_00's 16 textures (p4_info_brave_cursor_*) in the order
                               loop_anim_arrow shows them (15 down to 0, 2 frames each)
  name_<n>.png / name_<n>_grey.png   the 21 spells' names (SPELLS, Ultimate's command order), white /
                               x 107/255 (txt_gray_out), as set_txt_00 (FOT-Rodin, its size 22.08 x 33.12)
  mp_<n>.png / mp_<n>_grey.png the cost window (wnd_cost_00: wind_02) with "MP" and spell n's cost as
                               txt_cost_mp / set_txt_cost_mp place them (bottom aligned); grey as above
  gauge.png                    the gauge's pill: bg_gauge_00 then frame_gauge_00 (windows of one frame
                               texture, mp_gauge_00 / 03, mirrored on the right, its last column between)
  fill_blue.png, fill_green.png  gauge_00 / gauge_01 (mp_gauge_04 / 05), stretched to 1 + 1.58 x MP px
                               (guage_00 / 01: 1 at 0, 159 at 100)
  gauge_label.png, digit_<d>.png  stxt_mp ("MP") and set_txt_mp's digits
  layout.json                  where they go, in the 1-4 player panel's units (x right, y down): Ultimate's
                               pane positions (y up, px) with the window's top left at WINDOW_AT and
                               UNIT units a px (the earlier drawn window's place and size)
The images are at Ultimate's pixel size (art_scale px a unit). The font: the Wii U's shared font,
FOT-Rodin as Ultimate's (Cemu's resources/sharedFonts/CafeStd.ttf; not in the repository); without it
Inter Medium stands in.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bntx  # noqa: E402
import sarc  # noqa: E402

FONT = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
SS = 4
# (name, MP cost: param_special_lw_command_data sp; Magic Burst uses all of it)
SPELLS = [('Heal', 7), ('Sizz', 8), ('Sizzle', 20), ('Bang', 9), ('Kaboom', 37), ('Whack', 10),
          ('Thwack', 30), ('Magic Burst', None), ('Kamikazee', 1), ('Kaclang', 6), ('Acceleratle', 13),
          ('Oomph', 16), ('Bounce', 14), ('Snooze', 16), ('Hocus Pocus', 4), ('Zoom', 8),
          ('Flame Slash', 12), ('Kacrackle Slash', 11), ('Metal Slash', 6), ('Hatchet Man', 15),
          ('Psyche Up', 14)]
TEX = 'p4_info_melee_lct_brave_%s^u'
# p4_info_melee_lct_brave.bflyt's panes (px, y up, from the part's origin)
WINDOW = (47, -13, 278, 168)                    # wnd_open_00: centre, size
HOLD_H = 64                                     # wnd_hold_00
ROWS = (42, 5, -31, -67)                        # set_parts_cmd_00-03 (select_00-03 put the arrow there)
NAME_X = 13 - 68                                # set_txt_00 (left origin) in its part
ARROW_X = -84                                   # nul_arrow_00 (arrow_00: 50 x 50)
COST = (174, -67, 116, 64)                      # wnd_cost_00
COST_NUM = (190 + 35 / 2.0, -67 - 20)           # set_txt_cost_mp: right, bottom (its 35 x 40 box)
COST_LABEL = (157 - 38 / 2.0, -65 - 20)         # txt_cost_mp: left, bottom (38 x 40)
COST_NUM_H, COST_LABEL_H = 36.92, 31.03
GAUGE = (-8, 83, 172, 32)                       # null_gauge: bg_gauge_00 / frame_gauge_00
FILL = (-8 - 80, 20, 1.0, 159.0)                # gauge_00 / 01: left, height, width at 0 / 100 MP
GAUGE_NUM = (-8 + 73, 83 + 13)                  # set_txt_mp: right, centre
GAUGE_LABEL = (-8 - 54, 83 + 10)                # stxt_mp: centre
GAUGE_NUM_H, GAUGE_LABEL_H = 41.73, 31.03
NAME_H = 33.12
GREY_TEXT = 107.23 / 255                        # txt_gray_out / wnd_color_gray_out (the text)
GREY_WINDOW = 59.898 / 255                      # wnd_color_gray_out (the windows' white)
# the panel: the window's top left and the units a px
WINDOW_AT = (-228, -100)
UNIT = 288 / 278.0
WHITE = (255, 255, 255, 255)


def units(x, y):
    """Ultimate px (y up) -> the panel's units (y down)"""
    left, top = WINDOW[0] - WINDOW[2] / 2.0, WINDOW[1] + WINDOW[3] / 2.0
    return WINDOW_AT[0] + (x - left) * UNIT, WINDOW_AT[1] + (top - y) * UNIT


def textures(arc):
    files = sarc.read(open(arc, 'rb').read())
    return {n: Image.fromarray(px, 'RGBA') for n, px in bntx.read_all(files['timg/__Combined.bntx']).items()}


def tint(im, k):
    """a material's white colour x k (black stays black)"""
    r, g, b, a = im.split()
    r, g, b = (c.point(lambda v: int(v * k + 0.5)) for c in (r, g, b))
    return Image.merge('RGBA', (r, g, b, a))


def font_for(path, line_h):
    """the font sized so that its line (ascent + descent) is line_h px, as a text pane's font size"""
    f = ImageFont.truetype(path, 100)
    a, d = f.getmetrics()
    return ImageFont.truetype(path, max(1, int(round(100.0 * line_h * SS / (a + d)))))


def text(s, path, line_h, colour, outline=None, shadow=False):
    """s in one line, its line box line_h high (plus the outline / shadow's margins)"""
    f = font_for(path, line_h)
    st = int(outline * SS) if outline else 0
    d0 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    w = int(d0.textlength(s, font=f)) + 2 * st + 4 * SS
    a, dsc = f.getmetrics()
    h = a + dsc + 2 * st + 2 * SS
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((st + 3 * SS, st + 2 * SS), s, font=f, fill=(0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(SS * 0.8)))
    ImageDraw.Draw(im).text((st + 2 * SS, st + SS), s, font=f, fill=colour, stroke_width=st,
                            stroke_fill=(16, 16, 20, 255))
    return im.resize((max(1, w // SS), max(1, h // SS)), Image.LANCZOS)


def window_of_frame(tex, w, h):
    """a window pane of one frame texture (its top left corner): the texture on the left, mirrored on the
    right, its last column stretched between (the pill-shaped gauge: the texture is the full height)"""
    cw = tex.width
    t = tex.resize((cw, h), Image.LANCZOS) if tex.height != h else tex
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    im.alpha_composite(t, (0, 0))
    im.alpha_composite(t.transpose(Image.FLIP_LEFT_RIGHT), (w - cw, 0))
    im.alpha_composite(t.crop((cw - 1, 0, cw, h)).resize((w - 2 * cw, h)), (cw, 0))
    return im


def cost_window(base, cost, path, colour):
    im = base.copy()
    left, top = COST[0] - COST[2] / 2.0, COST[1] + COST[3] / 2.0
    num = text('ALL' if cost is None else str(cost), path, COST_NUM_H, colour)
    lab = text('MP', path, COST_LABEL_H, colour)
    # bottom aligned: the line boxes' bottoms where the panes put them
    im.alpha_composite(num, (int(round(COST_NUM[0] - left - num.width + 2)), int(round(top - COST_NUM[1] - num.height))))
    im.alpha_composite(lab, (int(round(COST_LABEL[0] - left - 2)), int(round(top - COST_LABEL[1] - lab.height))))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('layout_arc', help="Ultimate's ui/layout/info/info_melee/info_melee/layout.arc")
    ap.add_argument('out')
    ap.add_argument('--font', default=FONT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tx = textures(a.layout_arc)

    def save(im, name):
        im.save(os.path.join(a.out, name))
    wnd = tx['p4_rep_info_melee_lct_brave_wind_00^u']
    save(wnd, 'window.png')
    save(tint(wnd, GREY_WINDOW), 'window_grey.png')
    save(tx['p4_rep_info_melee_lct_brave_wind_01^u'], 'hold.png')
    for k in range(16):
        save(tx['p4_info_brave_cursor_%02d^u' % (15 - k)], 'cursor_%d.png' % k)
    grey = tuple(int(255 * GREY_TEXT + 0.5) for _ in range(3)) + (255,)
    cost = tx['p4_rep_info_melee_lct_brave_wind_02^u']
    for i, (nm, c) in enumerate(SPELLS, 1):
        save(text(nm, a.font, NAME_H, WHITE, shadow=True), 'name_%d.png' % i)
        save(text(nm, a.font, NAME_H, grey, shadow=True), 'name_%d_grey.png' % i)
        save(cost_window(cost, c, a.font, WHITE), 'mp_%d.png' % i)
        save(cost_window(tint(cost, GREY_WINDOW), c, a.font, grey), 'mp_%d_grey.png' % i)
    gx, gy, gw, gh = GAUGE
    pill = window_of_frame(tx[TEX % 'mp_gauge_00'], gw, gh)
    pill.alpha_composite(window_of_frame(tx[TEX % 'mp_gauge_03'], gw, gh))
    save(pill, 'gauge.png')
    save(tx[TEX % 'mp_gauge_04'], 'fill_blue.png')
    save(tx[TEX % 'mp_gauge_05'], 'fill_green.png')
    save(text('MP', a.font, GAUGE_LABEL_H, WHITE, outline=2.2), 'gauge_label.png')
    for dg in range(10):
        save(text(str(dg), a.font, GAUGE_NUM_H, WHITE, outline=2.6), 'digit_%d.png' % dg)
    wl, wt = units(WINDOW[0] - WINDOW[2] / 2.0, WINDOW[1] + WINDOW[3] / 2.0)
    layout = dict(
        art_scale=1.0 / UNIT,
        window=[wl, wt, WINDOW[2] * UNIT, WINDOW[3] * UNIT],
        hold_tops=[units(0, r + HOLD_H / 2.0)[1] for r in ROWS],
        name_x=units(NAME_X, 0)[0], rows=[units(0, r)[1] for r in ROWS],
        cursor_x=units(ARROW_X, 0)[0],
        mp=list(units(COST[0], COST[1])) + [COST[2] * UNIT, COST[3] * UNIT],
        gauge=[units(gx - gw / 2.0, 0)[0], units(0, gy)[1], gw * UNIT, gh * UNIT],
        fill_left=units(FILL[0], 0)[0], fill_w=[FILL[2], FILL[3]],
        gauge_label=list(units(*GAUGE_LABEL)), gauge_num=list(units(*GAUGE_NUM)))
    json.dump(layout, open(os.path.join(a.out, 'layout.json'), 'w'), indent=1)
    print('%d spells -> %s' % (len(SPELLS), a.out))


if __name__ == '__main__':
    main()
