#!/usr/bin/env python3
"""A stage-select name banner (stagen_10_<Name>.nut) in the game's style: the text's fill in red,
fill + outline + shadow in green (BC5, 1024x256; the game colors the two channels).

  python3 tools/stage_name_banner.py TEMPLATE.nut "New Stage" OUT.nut [--font FILE] [--png PREVIEW.png]

TEMPLATE: any stagen_10_*.nut (format / tiling / texture ID are kept; e.g. stagen_10_BattleField_f).
Layout measured on the game's banners: capitals from y 43 to the baseline at y 197, starting at x 9,
at most ~670 px wide, descenders above ~y 236 (smaller text if needed), outline ~7 px, shadow 5 px down-right; text condensed like the game's font.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut  # noqa: E402

DEFAULT_FONT = '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf'   # closest here to the game's lettering


def banner(text, font_file, condense=0.72):
    size = 400
    font = ImageFont.truetype(font_file, size)
    cap_top = font.getbbox('H')[1]
    baseline = font.getmetrics()[0]
    l, t, r, b = font.getbbox(text)
    big = Image.new('L', (r - l + 40, b + 40), 0)
    ImageDraw.Draw(big).text((20 - l, 0), text, font=font, fill=255)
    cols = np.flatnonzero(np.asarray(big).max(0))
    big = big.crop((cols[0], 0, cols[-1] + 1, big.height))
    s = 154.0 / (baseline - cap_top)             # capitals 43..197
    rows = np.flatnonzero(np.asarray(big).max(1))
    below = rows[-1] + 1 - baseline              # descenders (g, y, p...): keep them above ~y 236
    if below > 0:
        s = min(s, 39.0 / below)
    w = int(big.width * s * condense)
    if w > 670:
        condense *= 670.0 / w
        w = 670
    small = big.resize((w, int(big.height * s)), Image.LANCZOS)
    R = Image.new('L', (1024, 256), 0)
    R.paste(small, (9, int(round(197 - baseline * s))))
    outline = R.filter(ImageFilter.MaxFilter(15))
    shadow = Image.new('L', (1024, 256), 0)
    shadow.paste(outline, (5, 5))
    img = np.zeros((256, 1024, 4), np.uint8)
    img[..., 0] = np.asarray(R)
    img[..., 1] = np.maximum(np.asarray(outline), np.asarray(shadow))
    img[..., 3] = 255
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('template')
    ap.add_argument('text')
    ap.add_argument('out')
    ap.add_argument('--font', default=DEFAULT_FONT)
    ap.add_argument('--png', default=None)
    a = ap.parse_args()
    d, ts = nut.load(a.template)
    t = ts[0]
    assert (t.w, t.h, t.fmt & 0x3F) == (1024, 256, 0x35), 'not a stagen_10 banner'
    img = banner(a.text, a.font)
    open(a.out, 'wb').write(nut.replace(d, t, img))
    if a.png:
        d2, t2 = nut.load(a.out)
        Image.fromarray(nut.decode(d2, t2[0])[..., :3]).save(a.png)


if __name__ == '__main__':
    main()
