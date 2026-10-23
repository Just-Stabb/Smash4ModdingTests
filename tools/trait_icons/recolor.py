#!/usr/bin/env python3
"""Recoloured trait icons, from the user's art in source/ (pixels, shapes and alpha kept; only the
colours change):

  python3 tools/trait_icons/recolor.py

- shooter.png: source/shooter.png (an orange crosshair with red lines) in purple and black: each
  pixel's place between the orange and the red becomes the same place between purple and black.
- rush.png: source/rush.png (white) in blue.
- technical.png: source/technical.png (white) in black.

Each then gets a white outline like Strike's and Juggernaut's (about 3.5% of the icon's width), on a
canvas grown to fit it (the small sources are scaled up to 512 px first, their edges sharpened, so the outline is smooth).
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ORANGE, RED = np.array([243, 145, 88.]), np.array([185, 56, 61.])
PURPLE, BLACK = np.array([160, 80, 240.]), np.array([0, 0, 0.])
BLUE = (40, 120, 255)                    # the Rush badge's colour (tools/trait_badge_art.py)
OUTLINE = 0.035                          # white outline width / icon width
SIZE = 512                               # working size of the icon (its longer side)


def outline(path):
    """the icon at path, scaled to SIZE, on a white outline (its shape grown by a disc), saved over it"""
    img = Image.open(path).convert('RGBA')
    k = SIZE / max(img.size)
    img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    r = round(OUTLINE * SIZE)
    pad = r + 2
    canvas = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(img, (pad, pad))
    if k > 2:                                  # a small source: its edges smear when scaled up; sharpen them
        px = np.asarray(canvas).astype(np.float32)
        px[..., 3] = np.clip((px[..., 3] - 128) * k / 2 + 128, 0, 255)
        canvas = Image.fromarray(px.round().astype(np.uint8))
    alpha = np.asarray(canvas)[..., 3].astype(np.float32)
    grown = alpha.copy()
    h, w = alpha.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = (dx * dx + dy * dy) ** 0.5
            if d > r + 0.5:
                continue
            edge = min(1.0, r + 0.5 - d)       # soft rim: the last half pixel fades
            shifted = np.zeros_like(alpha)
            shifted[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
                alpha[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
            np.maximum(grown, shifted * edge, out=grown)
    white = np.zeros((h, w, 4), np.uint8)
    white[..., :3] = 255
    white[..., 3] = grown.round().astype(np.uint8)
    out = Image.fromarray(white)
    out.alpha_composite(canvas)
    out.save(path)


def two_tone(src, dst, a_from, b_from, a_to, b_to):
    img = np.asarray(Image.open(os.path.join(HERE, src)).convert('RGBA')).astype(float)
    d = b_from - a_from
    t = np.clip(((img[..., :3] - a_from) @ d) / (d @ d), 0, 1)[..., None]
    img[..., :3] = a_to + t * (b_to - a_to)
    Image.fromarray(img.round().astype(np.uint8)).save(os.path.join(HERE, dst))


def fill(src, dst, colour):
    img = np.asarray(Image.open(os.path.join(HERE, src)).convert('RGBA')).copy()
    img[..., :3] = colour
    Image.fromarray(img).save(os.path.join(HERE, dst))


if __name__ == '__main__':
    two_tone('source/shooter.png', 'shooter.png', ORANGE, RED, PURPLE, BLACK)
    fill('source/rush.png', 'rush.png', BLUE)
    fill('source/technical.png', 'technical.png', (0, 0, 0))
    for name in ('shooter', 'rush', 'technical'):
        outline(os.path.join(HERE, name + '.png'))
