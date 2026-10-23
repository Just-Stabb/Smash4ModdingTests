#!/usr/bin/env python3
"""A stage-select game logo (stagel_10_<Name>.nut) from a white symbol on black or transparency (e.g. Smash
Ultimate's series symbols, ui/replace_patch/series/series_1/series_1_<series>.bntx: tools/bntx.py png).

  python3 tools/stage_series_logo.py SYMBOL.png TEMPLATE.nut OUT.nut [--png PREVIEW.png]
  python3 tools/stage_series_logo.py --two-channel LOGO.png TEMPLATE.nut OUT.nut [--png PREVIEW.png]

--two-channel: LOGO is already drawn the game's way (red the picture, green the alpha), e.g. Smash
Ultimate's stage logos (ui/replace_patch/stage/stage_0/stage_0_<stage>.bntx: the "MINECRAFT" logo,
tools/bntx.py png). It's cropped to its silhouette and scaled to fit WIDE x HEIGHT (the game's wide
logos, Metroid / Pikmin / Pac-Land: ~215 px across), centred.

The game's logos (stagel_10_*: BC5, 256x128) are drawn as two channels, read off its own (Battlefield's
"Super Smash Bros. for Wii U", Mega Man, Fire Emblem): red a grayscale picture of the logo (white
fill, black outline, white around it), green its silhouette with a soft edge (the alpha). Here the
symbol's strokes are the white fill, what they enclose (a cube's faces) dark, with a black outline.
TEMPLATE: any stagel_10_*.nut (format / tiling / texture ID are kept).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nut  # noqa: E402

W, H = 256, 128
HEIGHT = 112            # the symbol's height on the logo (the game's logos fill ~100-120 rows)
OUTLINE = 4             # px of black outline around the symbol (the game's logos: ~3-6)
GLOW = 2.0              # the silhouette's soft edge (Gaussian radius)
FACE = 40               # red inside the symbol's enclosed parts (dark)
WIDE = 216              # --two-channel: the most a logo spans across (the game's: x 17-238)


def filled(mask):
    """the mask with what it encloses filled (flood from outside)"""
    im = Image.fromarray(np.pad(mask, 1).astype(np.uint8) * 255).copy()     # (fromarray shares the array)
    ImageDraw.floodfill(im, (0, 0), 128)
    return (np.asarray(im)[1:-1, 1:-1] != 128)


def logo(symbol):
    rgba = np.asarray(symbol.convert('RGBA')).astype(float)
    a = rgba[..., :3].mean(2) * rgba[..., 3] / 255 > 127      # white strokes (on black or transparency)
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sil = filled(a)
    h = HEIGHT - 2 * OUTLINE
    w = max(1, round(a.shape[1] * h / a.shape[0]))
    fill = np.asarray(Image.fromarray(a.astype(np.uint8) * 255).resize((w, h), Image.LANCZOS)) / 255.0
    inside = np.asarray(Image.fromarray(sil.astype(np.uint8) * 255).resize((w, h), Image.LANCZOS)) / 255.0
    canvas_f, canvas_s = np.zeros((H, W)), np.zeros((H, W))
    y0, x0 = (H - h) // 2, (W - w) // 2
    canvas_f[y0:y0 + h, x0:x0 + w] = fill
    canvas_s[y0:y0 + h, x0:x0 + w] = inside
    outer = np.asarray(Image.fromarray((canvas_s * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(2 * OUTLINE + 1))) / 255.0
    # red: white around, black outline band, dark faces, white strokes
    red = 255 * (1 - outer) + FACE * (canvas_s - canvas_f).clip(0, 1) + 255 * canvas_f
    green = np.asarray(Image.fromarray((outer * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(GLOW)))
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0] = red.clip(0, 255).round().astype(np.uint8)
    out[..., 1] = green
    out[..., 3] = 255
    return out


def fit(logo_img):
    """a two-channel logo (red picture, green alpha) cropped to its silhouette, scaled into W x H"""
    a = np.asarray(logo_img.convert('RGBA')).astype(float)
    ys, xs = np.nonzero(a[..., 1] > 8)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    scale = min(WIDE / a.shape[1], HEIGHT / a.shape[0])
    w, h = max(1, round(a.shape[1] * scale)), max(1, round(a.shape[0] * scale))

    def sized(ch):
        return np.asarray(Image.fromarray(ch.clip(0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS))
    red, green = np.full((H, W), 255, np.uint8), np.zeros((H, W), np.uint8)
    y0, x0 = (H - h) // 2, (W - w) // 2
    red[y0:y0 + h, x0:x0 + w] = sized(a[..., 0])
    green[y0:y0 + h, x0:x0 + w] = sized(a[..., 1])
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 3] = red, green, 255
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbol')
    ap.add_argument('template')
    ap.add_argument('out')
    ap.add_argument('--png')
    ap.add_argument('--two-channel', action='store_true')
    a = ap.parse_args()
    img = fit(Image.open(a.symbol)) if a.two_channel else logo(Image.open(a.symbol))
    d, texs = nut.load(a.template)
    t = texs[0]
    assert (t.w, t.h) == (W, H), (t.w, t.h)
    open(a.out, 'wb').write(nut.replace(d, t, img))
    if a.png:
        # as shown: the red picture over a mid gray by the green alpha
        g = img[..., 1:2] / 255.0
        Image.fromarray((img[..., :1].repeat(3, 2) * g + 90 * (1 - g)).astype(np.uint8)).save(a.png)


if __name__ == '__main__':
    main()
