#!/usr/bin/env python3
"""Recoloured trait icons, from the user's art in source/ (pixels, shapes and alpha kept; only the
colours change):

  python3 tools/trait_icons/recolor.py

- shooter.png: source/shooter.png (an orange crosshair with red lines) in purple and black: each
  pixel's place between the orange and the red becomes the same place between purple and black.
- rush.png: source/rush.png (white) in blue.
- technical.png: source/technical.png (white) in black.
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ORANGE, RED = np.array([243, 145, 88.]), np.array([185, 56, 61.])
PURPLE, BLACK = np.array([160, 80, 240.]), np.array([0, 0, 0.])
BLUE = (40, 120, 255)                    # the Rush badge's colour (tools/trait_badge_art.py)


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
