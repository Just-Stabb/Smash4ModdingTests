#!/usr/bin/env python3
"""Kirby's trait badges for the damage panel (docs/character-traits.md): a dark plate with the
trait's colour, its icon and its name, one PNG a trait.

  python3 tools/trait_badge_art.py OUT_DIR [--size 256x64] [--sheet sheet.png]

Writes OUT_DIR/trait_<name>.png (RGBA, transparent around the plate) for Normal, Rush, Shooter,
Strike, Juggernaut and Technical, in the order of the trait numbers (1-6) Kirby's MSC writes to his
marker int's bits 8-11. Drawn at 4x and scaled down. Replace any PNG with your own art of the same
size to change a badge.
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
SS = 4                                  # supersampling
# (name, plate accent colour, icon)
TRAITS = [('Normal', (200, 205, 215), 'star'), ('Rush', (255, 176, 32), 'chevrons'),
          ('Shooter', (64, 200, 255), 'crosshair'), ('Strike', (255, 72, 64), 'burst'),
          ('Juggernaut', (176, 120, 255), 'shield'), ('Technical', (80, 224, 120), 'gear')]
PLATE = (24, 28, 44, 235)
TEXT = (255, 255, 255, 255)
OUTLINE = (12, 14, 24, 255)


def star(cx, cy, r, points=5, inner=0.45, turn=-90):
    pts = []
    for i in range(points * 2):
        a = math.radians(turn + i * 180 / points)
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def icon(d, kind, cx, cy, r, colour):
    white = (255, 255, 255, 255)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour + (255,), outline=OUTLINE, width=SS * 2)
    g = r * 0.62
    if kind == 'star':
        d.polygon(star(cx, cy + g * 0.06, g), fill=white)
    elif kind == 'chevrons':
        for off in (-g * 0.42, g * 0.3):
            x = cx + off
            d.polygon([(x - g * 0.35, cy - g * 0.75), (x + g * 0.15, cy - g * 0.75), (x + g * 0.6, cy),
                       (x + g * 0.15, cy + g * 0.75), (x - g * 0.35, cy + g * 0.75), (x + g * 0.1, cy)], fill=white)
    elif kind == 'crosshair':
        w = SS * 3
        d.ellipse((cx - g * 0.7, cy - g * 0.7, cx + g * 0.7, cy + g * 0.7), outline=white, width=w)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line((cx + dx * g * 0.35, cy + dy * g * 0.35, cx + dx * g, cy + dy * g), fill=white, width=w)
        d.ellipse((cx - g * 0.14, cy - g * 0.14, cx + g * 0.14, cy + g * 0.14), fill=white)
    elif kind == 'burst':
        d.polygon(star(cx, cy, g, points=8, inner=0.5, turn=-90 + 22.5 / 2), fill=white)
    elif kind == 'shield':
        d.polygon([(cx - g * 0.75, cy - g * 0.8), (cx + g * 0.75, cy - g * 0.8), (cx + g * 0.75, cy - g * 0.1),
                   (cx, cy + g * 0.9), (cx - g * 0.75, cy - g * 0.1)], fill=white)
        d.polygon([(cx - g * 0.12, cy - g * 0.55), (cx + g * 0.12, cy - g * 0.55), (cx + g * 0.12, cy + g * 0.45),
                   (cx, cy + g * 0.6), (cx - g * 0.12, cy + g * 0.45)], fill=colour + (255,))
    elif kind == 'gear':
        teeth = 8
        pts = []
        for i in range(teeth * 4):
            a = math.radians(i * 360 / (teeth * 4))
            rr = g if (i % 4) in (1, 2) else g * 0.72
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=white)
        d.ellipse((cx - g * 0.3, cy - g * 0.3, cx + g * 0.3, cy + g * 0.3), fill=colour + (255,))


def badge(name, colour, kind, size):
    w, h = size[0] * SS, size[1] * SS
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = SS * 2
    d.rounded_rectangle((pad, pad, w - pad, h - pad), radius=(h - 2 * pad) // 2, fill=PLATE,
                        outline=colour + (255,), width=SS * 3)
    r = (h - 2 * pad) * 0.42
    cx = pad + (h - 2 * pad) / 2
    icon(d, kind, cx, h / 2, r, colour)
    text = name.upper()
    left, right = cx + r + SS * 6, w - pad - SS * 10
    fs = int((h - 2 * pad) * 0.5)
    font = ImageFont.truetype(FONT, fs)
    while font.getlength(text) > right - left and fs > 8:
        fs -= SS
        font = ImageFont.truetype(FONT, fs)
    tw = font.getlength(text)
    x = left + (right - left - tw) / 2
    box = font.getbbox(text)
    y = h / 2 - (box[1] + box[3]) / 2
    d.text((x, y), text, font=font, fill=TEXT, stroke_width=SS * 2, stroke_fill=OUTLINE)
    return img.resize(size, Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--size', default='256x64')
    ap.add_argument('--sheet', help='also a preview of every badge, one under the other')
    a = ap.parse_args()
    size = tuple(int(x) for x in a.size.split('x'))
    os.makedirs(a.out, exist_ok=True)
    imgs = []
    for name, colour, kind in TRAITS:
        img = badge(name, colour, kind, size)
        img.save(os.path.join(a.out, 'trait_%s.png' % name.lower()))
        imgs.append(img)
    if a.sheet:
        sheet = Image.new('RGBA', (size[0] + 16, (size[1] + 8) * len(imgs) + 8), (90, 110, 140, 255))
        for i, img in enumerate(imgs):
            sheet.alpha_composite(img, (8, 8 + i * (size[1] + 8)))
        sheet.save(a.sheet)


if __name__ == '__main__':
    main()
