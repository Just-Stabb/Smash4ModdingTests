#!/usr/bin/env python3
"""Smash 4 portraits (ui/replace/chr) for an Ultimate port, from Ultimate's own UI art, framed as
Smash 4 frames the base fighter's.

  python3 tools/ultimate_portraits.py --ult-ui ULT_UI --s4-chr S4_CHR --templates TEMPLATES
          --ult brave --ult-base reflet --ui-name Hero --s4-base Reflet --out OUT
          [--extra-out DIR] [--contact PNG] [--sets chr_00,chr_13,...] [--costumes 1-8] [--fits FITS.json]
          [--cross SCALE,X,Y] [--stock-whole] [--stock-icon]
          [--name-text TEXT]

ULT_UI     Ultimate's ui folder, or a zip holding it (ui/replace[_patch]/chara/chara_N/chara_N_<name>_CC.bntx)
S4_CHR     the Smash 4 UI the game shows, its ui/replace/chr folder (the base's <set>/<set>_<Base>_NN.nut;
           every fighter's chrn_* name plates, for the lettering)
TEMPLATES  the new fighter's portraits as tools/add_fighter.py made them (the base's art with the new
           texture ids): a folder of <set>/<set>_<UiName>_NN.nut, or ZIP:PREFIX for one inside a zip
           (new ids for --extra-out skip every id of the zip's / the enclosing ui folder's .nut files).
           Each output keeps its template's format, size, tiling and GIDX id; only the picture changes.
OUT        gets ui/replace/chr/<set>/<set>_<UiName>_NN.nut for every template file.
--extra-out  also the costumes the base has no file for (Robin's chr_10 / chr_70 / chr_90 are _01 / _02
           only: the game picks them by Robin's two variants), each with a new texture id after the
           fighter's others (add_fighter.py's block 0x28010000 + 0x100 * (id - 59), id from extra_kinds.json).
--fits     cache of the image fits (JSON; read when present, written after). The log lists every fit.

Framing. Each Smash 4 picture of a fighter is one render, cropped and scaled: chr_00, chr_10, chr_11,
chr_12 (squeezed 8:1), chr_13, chr_70 and stock_90 are all crops of chr_90's render. Ultimate's chara_0,
chara_1 and chara_7 are crops of chara_3, and chara_5 is the same render whole (~1/5.5 its size). So,
by image matching (normalised cross-correlation over scale and offset):
  F_set  Smash 4 base <set>_01 -> base chr_90_01            (same art)
  C      Ultimate base chara_0 c00 -> Smash 4 base chr_90_01 (different art: zero-mean correlation of
         the face; the one approximate link)
  G_k    new fighter chara_0 cK -> its chara_3 cK, chara_3 -> chara_5 (same art)
and a pixel of the new <set>_NN is the new fighter's chara_3 c(NN-1) at G_k(C^-1(F_set(pixel)))
(chara_5, upscaled, where chara_3 is cut off): the face lands where the base's face is, at the base's
face size, as Ultimate frames both fighters' chara_N around their faces.

Per kind of set (the parts measured on the base's own pictures):
  plain  chr_11, chr_12, chr_13, chr_70, chr_90: the render; cut where the base's is cut (Robin's chr_12
         stops at row 258 though the render goes on).
  hex    chr_00, chr_10: the base's frame (inside = the convex hull of where the base's picture shows its
         background or its render unchanged; the ring = the rest, kept as it is) with the new render
         inside, over the base's background refitted as a smooth surface (chr_10's dark gradient;
         chr_00's is clear).
  stock  stock_90: the head (chara_4's cut: chara_4 is the head of the same render), down to the bottom
         of the face frame, with the base's outline and drop shadow refitted (outer = max(dilate(head,
         r1), k * shift(dilate(head, r2)))). The face goes where the base's face is; the scale is the
         face frame's unless the head would leave the base head's box (+3 px), then smaller (Smash 4
         fits each stock icon's head to the icon; Hero's hair and the other heroes' helmets are bigger).
         --stock-whole, where chara_4 isn't a cut of chara_3's render (Squirtle's upper body, turned):
         chara_4 whole, fitted into the base head's box.
  plate  chrn_11 / chrn_12 / chrn_40: the name in the game's lettering: glyphs cut from the other
         fighters' plates (SHEIK, BOWSER, ROBIN, DUCK HUNT...), long names' condensing undone, letter
         spacing from the same pair on a plate where there is one, outline / shadow refitted on the
         base's plate. A name needs every letter on some plate (big and small-cap forms for chrn_12 /
         chrn_40).
Alpha: Ultimate's chara_0-4 / 6 / 7 are premultiplied, chara_5 straight (detected per picture); Smash
4's portraits are straight alpha, black where clear. Costumes: Ultimate cCC = Smash 4 _(CC+1). A
chara_5 shared by costumes (Hero: one per hero, c00-c03) is recoloured for the others (c04-c07) with
a colour map learnt from the two costumes' chara_3 (the same render, pixel for pixel).
"""
import argparse
import json
import os
import re
import struct
import sys
import zipfile
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bntx  # noqa: E402
import nut  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_TEXTURE_IDS = 0x28010000          # as tools/add_fighter.py: + 0x100 * (character id - 59)
REF_SET = 'chr_90'

# set -> (kind, registration options)
SETS = {
    'chr_00': ('hex', {}),
    'chr_10': ('hex', {}),
    'chr_11': ('plain', {}),
    'chr_12': ('plain', {'aniso': (1.5, 12.0)}),
    'chr_13': ('plain', {}),
    'chr_70': ('plain', {}),
    'chr_90': ('plain', {}),
    'stock_90': ('stock', {}),
    'chrn_11': ('plate', {}),
    'chrn_12': ('plate', {}),
    'chrn_40': ('plate', {}),
}

# the Smash 4 (English) names on the chrn_* plates, as the small-caps plates write them (a capital is
# a big letter); a plate of a name not here, or whose letters touch, gives no glyphs
PLATE_TEXT = {
    'Mario': 'Mario', 'Luigi': 'Luigi', 'Peach': 'Peach', 'Koopa': 'Bowser', 'Yoshi': 'Yoshi',
    'Wario': 'Wario', 'Donkey': 'Donkey Kong', 'Diddy': 'Diddy Kong', 'Link': 'Link', 'Zelda': 'Zelda',
    'Sheik': 'Sheik', 'Ganon': 'Ganondorf', 'Toonlink': 'Toon Link', 'Samus': 'Samus',
    'Szerosuit': 'Zero Suit Samus', 'Pit': 'Pit', 'Palutena': 'Palutena', 'Marth': 'Marth', 'Ike': 'Ike',
    'Reflet': 'Robin', 'Duckhunt': 'Duck Hunt', 'Kirby': 'Kirby', 'Dedede': 'King Dedede',
    'Metaknight': 'Meta Knight', 'Littlemac': 'Little Mac', 'Fox': 'Fox', 'Falco': 'Falco',
    'Pikachu': 'Pikachu', 'Lizardon': 'Charizard', 'Lucario': 'Lucario', 'Purin': 'Jigglypuff',
    'Gekkouga': 'Greninja', 'Ness': 'Ness', 'Captain': 'Captain Falcon', 'Murabito': 'Villager',
    'Pikmin': 'Olimar', 'Shulk': 'Shulk', 'Pitb': 'Dark Pit', 'Lucina': 'Lucina', 'Sonic': 'Sonic',
    'Rockman': 'Mega Man', 'Wiifit': 'Wii Fit Trainer', 'Pacman': 'Pac-Man', 'Drmario': 'Dr. Mario',
}
PLATE_TEXT_VARIANT = {'Pikmin_05': 'Alph', 'KoopaJr_01': 'Bowser Jr.', 'KoopaJr_02': 'Larry',
                      'KoopaJr_03': 'Roy', 'KoopaJr_04': 'Wendy', 'KoopaJr_05': 'Iggy',
                      'KoopaJr_06': 'Morton', 'KoopaJr_07': 'Lemmy', 'KoopaJr_08': 'Ludwig'}


# ================================================================ image helpers
def to_float(img, premultiplied=False):
    """RGBA uint8 -> premultiplied float32, 0..1"""
    f = img.astype(np.float32) / 255.0
    if premultiplied:
        f[..., :3] = np.minimum(f[..., :3], f[..., 3:4])
    else:
        f[..., :3] *= f[..., 3:4]
    return f


def to_straight(f):
    """premultiplied float -> straight RGBA uint8, black where clear (as Smash 4's portraits)"""
    a = f[..., 3:4]
    rgb = np.where(a > 1.0 / 512, f[..., :3] / np.maximum(a, 1e-6), 0)
    out = np.clip(np.concatenate([rgb, a], 2) * 255 + 0.5, 0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    return out


def is_premultiplied(img):
    """in premultiplied art a faint pixel is never brighter than its alpha (BC7 noise aside)"""
    a = img[..., 3].astype(np.float32)
    m = (a > 13) & (a < 100)
    if m.sum() < 50:
        return False
    r = img[..., :3].max(2)[m] / a[m]
    return float((r > 1.05).mean()) < 0.2


def resize_f(f, w, h):
    out = [np.asarray(Image.fromarray(np.ascontiguousarray(f[..., c]), 'F').resize((w, h), Image.LANCZOS))
           for c in range(f.shape[2])]
    return np.clip(np.stack(out, 2), 0, 1)


def warp(f, ax, bx, ay, by, w, h):
    """[h, w] picture with out[y, x] = f at pixel (ax * x + bx, ay * y + by) (premultiplied float;
    clear outside f). Big reductions are area-averaged first, so fine detail doesn't alias."""
    kx, ky = max(1, int(abs(ax) / 1.5)), max(1, int(abs(ay) / 1.5))
    if kx > 1 or ky > 1:
        H, W = f.shape[0] // ky * ky, f.shape[1] // kx * kx
        f = f[:H, :W].reshape(H // ky, ky, W // kx, kx, -1).mean((1, 3))
        ax, ay = ax / kx, ay / ky
        bx, by = (bx + 0.5) / kx - 0.5, (by + 0.5) / ky - 0.5
    pad = 4
    f = np.pad(f, ((pad, pad), (pad, pad), (0, 0)))
    bx, by = bx + pad, by + pad
    # PIL maps an output pixel's centre (x + 0.5) to an input position (pixel i's centre at i + 0.5)
    coef = (ax, 0, bx + 0.5 - 0.5 * ax, 0, ay, by + 0.5 - 0.5 * ay)
    out = [np.asarray(Image.fromarray(np.ascontiguousarray(f[..., c]), 'F').transform(
        (w, h), Image.AFFINE, coef, Image.BICUBIC)) for c in range(f.shape[2])]
    return np.clip(np.stack(out, 2), 0, 1)


def over(a, b):
    """premultiplied a over b"""
    return a + b * (1 - a[..., 3:4])


def erode(mask, px):
    im = Image.fromarray((mask > 0.5).astype(np.uint8) * 255)
    return np.asarray(im.filter(ImageFilter.MinFilter(2 * px + 1))) > 127 if px > 0 else np.asarray(im) > 127


def shift(a, dx, dy):
    """a moved by whole pixels (dx, dy), zeros shifted in"""
    dx, dy = int(dx), int(dy)
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    if abs(dx) >= w or abs(dy) >= h:
        return out
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = a[ys, xs]
    return out


def dist_field(f, R):
    """soft distance to a 0..1 mask: min over offsets |o| <= R + 1 of |o| + 1 - f(x - o) (0 inside)"""
    d = np.where(f > 0, 1 - f, 1e6).astype(np.float32)
    R1 = int(np.ceil(R)) + 1
    for dy in range(-R1, R1 + 1):
        for dx in range(-R1, R1 + 1):
            r = (dx * dx + dy * dy) ** 0.5
            if 0 < r <= R1:
                s = shift(f, dx, dy)
                np.minimum(d, np.where(s > 0, r + 1 - s, 1e6), out=d)
    return d


def dilated(f, d, r):
    """the mask grown by r px (soft edge), from its dist_field d"""
    return f.copy() if r <= 0 else np.maximum(f, np.clip(r + 1 - d, 0, 1))


def convex_mask(points, w, h, ss=4):
    """soft (supersampled) mask of the convex hull of points [(x, y)] (pixel-corner coordinates)"""
    pts = sorted(set(map(tuple, points)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    im = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in hull], fill=255)
    return np.asarray(im.resize((w, h), Image.BOX)).astype(np.float32) / 255.0, hull


def mask_points(mask):
    """the corners of each row's leftmost and rightmost pixel of a boolean mask"""
    pts = []
    for y in np.flatnonzero(mask.any(1)):
        xs = np.flatnonzero(mask[y])
        for x in (xs[0], xs[-1] + 1):
            pts += [(int(x), int(y)), (int(x), int(y) + 1)]
    return pts


# ================================================================ registration
def _feat(f):
    lum = f[..., 0] * 0.3 + f[..., 1] * 0.59 + f[..., 2] * 0.11
    return np.stack([lum, f[..., 3]], 2)


def _xcorr(img, tmp):
    """out[dy + th - 1, dx + tw - 1] = sum over u of tmp(u) img(u + d), every partial overlap (FFT)"""
    ih, iw = img.shape[:2]
    th, tw = tmp.shape[:2]
    H, W = ih + th - 1, iw + tw - 1
    FH, FW = 1 << (H - 1).bit_length(), 1 << (W - 1).bit_length()
    fi = np.fft.rfft2(img, (FH, FW), axes=(0, 1))
    ft = np.fft.rfft2(tmp[::-1, ::-1], (FH, FW), axes=(0, 1))
    r = np.fft.irfft2(fi * ft, (FH, FW), axes=(0, 1))
    if r.ndim == 3:
        r = r.sum(2)
    return r[:H, :W]


def ncc_map(img, tmp, w):
    """normalised correlation, no mean removed (same art; alpha is a feature); windows with much
    less energy than the template score low"""
    t = tmp * w[..., None]
    num = _xcorr(img, t)
    e_img = _xcorr((img ** 2).sum(2), w)
    e_t = float((t * tmp).sum())
    return num / np.sqrt(np.maximum(e_img, 0.25 * e_t) * max(e_t, 1e-9))


def zncc_map(img, tmp, w):
    """zero-mean normalised correlation of luminance (shading, edges): lines up different renders"""
    sw = float(w.sum())
    mt = float((tmp * w).sum()) / sw
    t = (tmp - mt) * w
    num = _xcorr(img, t)
    s1 = _xcorr(img, w)
    s2 = _xcorr(img ** 2, w)
    var_i = s2 - s1 ** 2 / sw
    var_t = float((t * (tmp - mt)).sum())
    return num / np.sqrt(np.maximum(var_i, 0.05 * var_t) * max(var_t, 1e-9))


def _peak(m):
    iy, ix = np.unravel_index(np.argmax(m), m.shape)

    def sub(a, b, c):
        d = a - 2 * b + c
        return 0.0 if abs(d) < 1e-12 else max(-0.5, min(0.5, 0.5 * (a - c) / d))
    fy = sub(m[iy - 1, ix], m[iy, ix], m[iy + 1, ix]) if 0 < iy < m.shape[0] - 1 else 0.0
    fx = sub(m[iy, ix - 1], m[iy, ix], m[iy, ix + 1]) if 0 < ix < m.shape[1] - 1 else 0.0
    return float(m[iy, ix]), iy + fy, ix + fx


class Fit:
    """pixel (x, y) of one picture is pixel (ax * x + bx, ay * y + by) of another; score = correlation"""
    def __init__(self, score, ax, bx, ay, by):
        self.score, self.ax, self.bx, self.ay, self.by = float(score), float(ax), float(bx), float(ay), float(by)

    def then(self, g):
        """this, then g"""
        return Fit(min(self.score, g.score), g.ax * self.ax, g.ax * self.bx + g.bx, g.ay * self.ay, g.ay * self.by + g.by)

    def inv(self):
        return Fit(self.score, 1 / self.ax, -self.bx / self.ax, 1 / self.ay, -self.by / self.ay)

    def tolist(self):
        return [self.score, self.ax, self.bx, self.ay, self.by]

    def __repr__(self):
        return 'score %.4f, scale %.4f x %.4f, offset (%.1f, %.1f)' % (self.score, self.ax, self.ay, self.bx, self.by)


def _pyramid(big):
    """big and its halvings (area mean), for fast resizing to small sizes"""
    out = [big]
    while min(out[-1].shape[:2]) >= 64:
        f = out[-1]
        H, W = f.shape[0] // 2 * 2, f.shape[1] // 2 * 2
        out.append(f[:H, :W].reshape(H // 2, 2, W // 2, 2, -1).mean((1, 3)))
    return out


def _search(big, T, w, scales, ratios, min_cover, zero_mean, smax=None):
    best = None
    th, tw = T.shape[:2]
    pyr = _pyramid(big)
    for s in scales:
        for r in ratios:
            if smax is not None and s * r > smax:
                continue
            W = max(4, int(round(big.shape[1] * s)))
            H = max(4, int(round(big.shape[0] * s * r)))
            sx, sy = W / big.shape[1], H / big.shape[0]
            src = big
            for lev in pyr[1:]:
                if lev.shape[1] >= 2 * W and lev.shape[0] >= 2 * H:
                    src = lev
            I = _feat(resize_f(src, W, H))
            m = zncc_map(I[..., 0], T[..., 0], w) if zero_mean else ncc_map(I, T, w)
            cover = _xcorr(np.ones((H, W), np.float32), w) / w.sum()
            m = np.where(cover >= min_cover, m, -1)
            sc, py, px = _peak(m)
            ox, oy = px - (tw - 1), py - (th - 1)        # T pixel u = (resized big) pixel u + o
            if best is None or sc > best.score:
                best = Fit(sc, 1 / sx, (ox + 0.5) / sx - 0.5, 1 / sy, (oy + 0.5) / sy - 0.5)
    return best


def register(big, tmp, s_lo, s_hi, wmask=None, aniso=(1.0, 1.0), min_cover=0.6, steps=48, max_side=768,
             zero_mean=False):
    """where tmp (premultiplied RGBA) is in big: Fit tmp pixel -> big pixel, big pixels per tmp pixel
    in [s_lo, s_hi] (horizontally; vertical / horizontal in aniso). Coarse (a ~64 px template) to fine
    (up to max_side, on a crop of big)."""
    w0 = np.ones(tmp.shape[:2], np.float32) if wmask is None else wmask.astype(np.float32)
    th, tw = tmp.shape[:2]
    fit = None
    for side, span, n in ((64, None, steps), (200, 1.06, 7), (max_side, 1.015, 5)):
        q = min(1.0, max(float(side) / max(th, tw), 0.4 * side / min(th, tw)))   # thin templates keep detail
        qw, qh = max(4, int(round(tw * q))), max(4, int(round(th * q)))
        T = _feat(resize_f(tmp, qw, qh))
        w = np.asarray(Image.fromarray(w0, 'F').resize((qw, qh), Image.BILINEAR))
        qx, qy = qw / tw, qh / th
        if fit is None:
            scales = np.exp(np.linspace(np.log(1.0 / s_hi), np.log(1.0 / s_lo), n)) * qx
            ratios = [1.0] if aniso[0] == aniso[1] else np.exp(np.linspace(np.log(aniso[0]), np.log(aniso[1]), 12))
            ratios = [r * qy / qx for r in ratios]
            x0 = y0 = 0
            sub = big
        else:
            s0x, s0y = 1 / fit.ax, 1 / fit.ay
            scales = s0x * qx * np.exp(np.linspace(-np.log(span), np.log(span), n))
            r0 = (s0y * qy) / (s0x * qx)
            ratios = [r0] if aniso[0] == aniso[1] else list(r0 * np.exp(np.linspace(-np.log(span), np.log(span), 5)))
            mx, my = 0.15 * tw * fit.ax + 8, 0.15 * th * fit.ay + 8
            x0 = int(max(0, np.floor(fit.bx - mx)))
            y0 = int(max(0, np.floor(fit.by - my)))
            x1 = int(min(big.shape[1], np.ceil(fit.bx + tw * fit.ax + mx)))
            y1 = int(min(big.shape[0], np.ceil(fit.by + th * fit.ay + my)))
            sub = big[y0:y1, x0:x1]
        f = _search(sub, T, w, scales, ratios, min_cover, zero_mean, smax=qy / s_lo if fit is None else None)
        # template pixel u (full size) = (u + 0.5) q - 0.5 at this resolution
        fit = Fit(f.score, f.ax * qx, f.bx + f.ax * (0.5 * qx - 0.5) + x0, f.ay * qy, f.by + f.ay * (0.5 * qy - 0.5) + y0)
    return fit


def register_best(big, tmp, s_lo, s_hi, **kw):
    """register() with and without the mean removed; the better score"""
    a = register(big, tmp, s_lo, s_hi, **kw)
    b = register(big, tmp, s_lo, s_hi, zero_mean=True, **kw)
    return a if a.score >= b.score else b


def cached(cache, key, fn):
    if key in cache:
        return Fit(*cache[key])
    f = fn()
    cache[key] = f.tolist()
    return f


# ================================================================ inputs
class UltUI:
    """Ultimate's ui folder or a zip of it"""
    def __init__(self, path):
        self.zip = zipfile.ZipFile(path) if zipfile.is_zipfile(path) else None
        self.root = path
        self.names = set(self.zip.namelist()) if self.zip else None
        self._memo = {}

    def _path(self, rel):
        for pre in ('', 'ui/'):
            if self.zip is not None:
                if pre + rel in self.names:
                    return pre + rel
            elif os.path.exists(os.path.join(self.root, pre, rel)):
                return os.path.join(self.root, pre, rel)
        return None

    def _find(self, n, name, c):
        for d in ('replace_patch', 'replace'):
            p = self._path('%s/chara/chara_%d/chara_%d_%s_%02d.bntx' % (d, n, n, name, c))
            if p:
                return p
        return None

    def has(self, n, name, c):
        return self._find(n, name, c) is not None

    def chara(self, n, name, c):
        """chara_N_<name>_CC (replace_patch first) as premultiplied float, None when missing"""
        key = (n, name, c)
        if key not in self._memo:
            p = self._find(n, name, c)
            if p is None:
                self._memo[key] = None
            else:
                data = self.zip.read(p) if self.zip is not None else open(p, 'rb').read()
                img = bntx._brti(data, data.index(b'BRTI'))
                self._memo[key] = to_float(img, is_premultiplied(img))
        return self._memo[key]


def read_nut(data):
    return zlib.decompress(data) if data[:2] == b'\x78\x9c' else data


def load_nut_bytes(data):
    data = read_nut(data)
    assert data[:4] == b'NTWU', data[:4]
    texs, hp = [], 0x10
    for _ in range(nut.be16(data, 6)):
        t = nut.Tex(data, hp)
        texs.append(t)
        hp += t.header_size
    return data, texs


def texture_ids(data):
    out = []
    i = data.find(b'GIDX')
    while i >= 0:
        out.append((i + 8, struct.unpack('>I', data[i + 8:i + 12])[0]))
        i = data.find(b'GIDX', i + 4)
    return out


class Templates:
    """the new fighter's present portrait files (a folder, or zip:prefix)"""
    def __init__(self, spec):
        self.files = {}
        self.everything = []       # every .nut of the build (its texture ids are taken)
        zp = spec.split(':', 1)[0]
        if ':' in spec and os.path.isfile(zp) and zipfile.is_zipfile(zp):
            z = zipfile.ZipFile(zp)
            pre = spec.split(':', 1)[1].rstrip('/') + '/'
            for n in z.namelist():
                if n.endswith('.nut'):
                    self.everything.append(lambda n=n: z.read(n))
                    if n.startswith(pre):
                        self.files[n[len(pre):]] = (lambda n=n: z.read(n))
        else:
            for root, _d, fs in os.walk(spec):
                for f in fs:
                    if f.endswith('.nut'):
                        p = os.path.join(root, f)
                        self.files[os.path.relpath(p, spec).replace(os.sep, '/')] = (lambda p=p: open(p, 'rb').read())
            top = os.path.abspath(spec)            # the build's ui folder (or the templates' own)
            while os.path.basename(top) != 'ui' and os.path.dirname(top) != top:
                top = os.path.dirname(top)
            top = top if os.path.basename(top) == 'ui' else spec
            for root, _d, fs in os.walk(top):
                self.everything += [(lambda p=os.path.join(root, f): open(p, 'rb').read()) for f in fs if f.endswith('.nut')]

    def get(self, st, ui, nn):
        f = self.files.get('%s/%s_%s_%02d.nut' % (st, st, ui, nn))
        return f() if f else None

    def ids(self):
        """the texture ids every .nut of the build uses"""
        out = set()
        for f in self.everything or list(self.files.values()):
            out.update(t for _, t in texture_ids(read_nut(f())))
        return out


def load_s4(path):
    d, texs = load_nut_bytes(open(path, 'rb').read())
    return nut.decode(d, texs[0])


# ================================================================ the Ultimate side
# Smash 4's portrait renders are brighter than Ultimate's (shadows and midtones lifted; colour strength,
# max - min of a pixel's channels, about the same): the median, over 39 fighters in both games (Ultimate
# chara_3 c00 vs Smash 4 chr_90 _01, opaque pixels), of their luminance at each quantile (2 - 98 %),
# Ultimate -> Smash 4. Applied to the luminance (tone())
TONE_ULT = [0.0, 0.036, 0.072, 0.103, 0.144, 0.193, 0.252, 0.309, 0.401, 0.48, 0.563, 0.719, 0.91, 1.0]
TONE_S4 = [0.03, 0.184, 0.252, 0.302, 0.357, 0.395, 0.436, 0.51, 0.582, 0.655, 0.737, 0.823, 0.948, 1.0]
TONE = [True]


def tone(f):
    """premultiplied art toned as Smash 4's renders (TONE_*)"""
    if not TONE[0]:
        return f
    a = f[..., 3:4]
    rgb = np.where(a > 1e-4, f[..., :3] / np.maximum(a, 1e-4), 0)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    lum2 = np.interp(lum, TONE_ULT, TONE_S4).astype(np.float32)
    # chroma scaled by sqrt(L' / L): kept as is (+ (L' - L)) greys the lifted darks (his hair), scaled with
    # the luminance over-saturates them
    k = np.sqrt(np.clip(lum2 / np.maximum(lum, 1e-3), 1.0, 4.0))[..., None]
    rgb = np.clip(lum2[..., None] + (rgb - lum[..., None]) * k, 0, 1)
    return np.concatenate([rgb * a, a], -1).astype(np.float32)


class Fighter:
    """one Ultimate costume's art: chara_3, chara_5 (the whole render) under it, the face frame chara_0"""
    def __init__(self, ult, name, c, cache, log):
        self.name, self.c = name, c
        self.c3, self.c0, self.c4 = ult.chara(3, name, c), ult.chara(0, name, c), ult.chara(4, name, c)
        self.c2 = ult.chara(2, name, c)         # Ultimate's stock icon (--stock-icon)
        if self.c3 is None or self.c0 is None:
            raise SystemExit('no chara_3 / chara_0 for %s c%02d' % (name, c))
        key = '%s_c%02d' % (name, c)
        self.f0 = cached(cache, key + '/chara_0_in_chara_3', lambda: register(self.c3, self.c0, 1.0, 12.0))
        log.append('%s: chara_0 in chara_3: %s' % (key, self.f0))
        self.c5, self.f5 = None, None
        n5 = [k for k in range(8) if ult.has(5, name, k)]
        if n5:
            k5 = c if c in n5 else n5[c % len(n5)]
            c5 = ult.chara(5, name, k5)
            # chara_3, reduced, inside chara_5 (chara_5 holds all of it)
            q = min(1.0, 700.0 / max(self.c3.shape[:2]))
            sw, sh = max(4, int(round(self.c3.shape[1] * q))), max(4, int(round(self.c3.shape[0] * q)))
            fq = cached(cache, '%s/chara_3_in_chara_5_c%02d' % (key, k5),
                        lambda: register(c5, resize_f(self.c3, sw, sh), 0.05, 2.0, min_cover=0.3))
            qx, qy = sw / self.c3.shape[1], sh / self.c3.shape[0]
            self.f5 = Fit(fq.score, fq.ax * qx, fq.bx + fq.ax * (0.5 * qx - 0.5), fq.ay * qy, fq.by + fq.ay * (0.5 * qy - 0.5))
            log.append('%s: chara_3 in chara_5 c%02d: %s' % (key, k5, self.f5))
            if k5 != c:
                src3 = ult.chara(3, name, k5)
                if src3 is not None and src3.shape == self.c3.shape:
                    c5 = recolour(c5, src3, self.c3)
                    log.append('%s: chara_5 c%02d recoloured with the colours of chara_3 c%02d -> c%02d' % (key, k5, k5, c))
                else:
                    log.append('%s: chara_5 c%02d used as it is (no chara_3 of the same render to recolour by)' % (key, k5))
            self.c5 = c5

    def render(self, to3, w, h):
        """the art of a (w, h) picture whose pixel p is chara_3 pixel to3(p)"""
        a3 = warp(self.c3, to3.ax, to3.bx, to3.ay, to3.by, w, h)
        if self.c5 is None:
            return tone(a3)
        to5 = to3.then(self.f5)
        a5 = warp(self.c5, to5.ax, to5.bx, to5.ay, to5.by, w, h)
        # chara_3 inside its own rectangle (feathered inward a few output pixels), chara_5 outside
        H3, W3 = self.c3.shape[:2]
        fy, fx = 3.0 * max(1.0, abs(to3.ay)), 3.0 * max(1.0, abs(to3.ax))
        ys = np.arange(h) * to3.ay + to3.by
        xs = np.arange(w) * to3.ax + to3.bx
        wy = np.clip(np.minimum(ys + 0.5, H3 - 0.5 - ys) / fy, 0, 1)
        wx = np.clip(np.minimum(xs + 0.5, W3 - 0.5 - xs) / fx, 0, 1)
        wgt = (wy[:, None] * wx[None, :])[..., None].astype(np.float32)
        return tone(a3 * wgt + a5 * (1 - wgt))


def recolour(c5, src3, dst3, bins=24):
    """c5 (costume src's art) in costume dst's colours: each colour bin of src (from the two costumes'
    chara_3, the same render) -> the mean colour change of its pixels; empty bins take the nearest"""
    def straight(f):
        a = f[..., 3:4]
        return np.where(a > 0.02, f[..., :3] / np.maximum(a, 1e-6), 0)
    m = (src3[..., 3] > 0.9) & (dst3[..., 3] > 0.9)
    s, d = straight(src3)[m], straight(dst3)[m]
    idx = np.clip((s * bins).astype(int), 0, bins - 1)
    flat = (idx[:, 0] * bins + idx[:, 1]) * bins + idx[:, 2]
    n = np.bincount(flat, minlength=bins ** 3)
    delta = np.stack([np.bincount(flat, (d - s)[:, k], bins ** 3) for k in range(3)], 1)
    ok = n > 3
    lut = np.zeros((bins ** 3, 3), np.float32)
    lut[ok] = delta[ok] / n[ok, None]
    g = np.stack(np.meshgrid(np.arange(bins), np.arange(bins), np.arange(bins), indexing='ij'), -1).reshape(-1, 3)
    filled, empty = np.flatnonzero(ok), np.flatnonzero(~ok)
    for chunk in np.array_split(empty, max(1, len(empty) // 1024)):
        if len(chunk):
            dist = ((g[chunk, None, :] - g[None, filled, :]) ** 2).sum(2)
            lut[chunk] = lut[filled[dist.argmin(1)]]
    a = c5[..., 3:4]
    col = straight(c5)
    ci = np.clip((col * bins).astype(int), 0, bins - 1)
    out = np.clip(col + lut[(ci[..., 0] * bins + ci[..., 1]) * bins + ci[..., 2]], 0, 1)
    return np.concatenate([out * a, a], 2).astype(np.float32)


# ================================================================ the Smash 4 side
class SetRef:
    """a set's base picture (_01), its fit into the base's chr_90, and where it is cut"""
    def __init__(self, st, kind, opts, img, ref90, cache, log):
        self.st, self.kind = st, kind
        self.O = to_float(img)
        self.h, self.w = img.shape[:2]
        if st == REF_SET:
            self.F = Fit(1.0, 1, 0, 1, 0)
        else:
            wm = None
            if kind in ('hex', 'stock'):     # leave the frame / outline out of the match
                wm = erode(self.O[..., 3] > 0.5, max(2, int(round(0.05 * min(self.w, self.h))))).astype(np.float32)
            cover = 0.95 if kind in ('hex', 'stock') else 0.5
            # match on the picture's content (and a margin), not its empty parts
            ys, xs = np.nonzero(self.O[..., 3] > 0.05)
            mx, my = max(2, (xs.max() - xs.min()) // 10), max(2, (ys.max() - ys.min()) // 10)
            x0, y0 = max(0, xs.min() - mx), max(0, ys.min() - my)
            x1, y1 = min(self.w, xs.max() + 1 + mx), min(self.h, ys.max() + 1 + my)
            box = self.O[y0:y1, x0:x1]
            wb = None if wm is None else wm[y0:y1, x0:x1]

            def fit_in_box():
                f = register_best(ref90, box, 0.8, 60.0, wmask=wb, aniso=opts.get('aniso', (1.0, 1.0)), min_cover=cover)
                return Fit(f.score, f.ax, f.bx - f.ax * x0, f.ay, f.by - f.ay * y0)
            self.F = cached(cache, 's4/%s_in_%s' % (st, REF_SET), fit_in_box)
        log.append('Smash 4 %s_01 in %s_01: %s' % (st, REF_SET, self.F))
        F = self.F
        self.P = warp(ref90, F.ax, F.bx, F.ay, F.by, self.w, self.h)       # the base's render, predicted
        self.V = warp(np.ones(ref90.shape[:2] + (1,), np.float32), F.ax, F.bx, F.ay, F.by, self.w, self.h)[..., 0] > 0.99
        if kind == 'plain':
            seen = (self.P[..., 3] > 0.5) & self.V & (self.O[..., 3] > 0.5)
            if seen.sum() > 100:
                log.append('%s: the base picture vs its render through the fit: mean difference %.4f' % (
                    st, float(np.abs(self.O - self.P).max(2)[seen].mean())))
        self.window = self._window() if kind == 'plain' else [0, 0, self.w, self.h]

    def _window(self):
        """[x0, y0, x1, y1]: where the base's picture stops although its render goes on"""
        a, p = self.O[..., 3] > 0.05, (self.P[..., 3] > 0.5) & self.V
        x0, y0, x1, y1 = 0, 0, self.w, self.h
        if a.any():
            rows, cols = np.flatnonzero(a.any(1)), np.flatnonzero(a.any(0))
            if rows[-1] < self.h - 3 and p[rows[-1] + 3:].sum() > 20:
                y1 = rows[-1] + 1
            if rows[0] > 2 and p[:rows[0] - 2].sum() > 20:
                y0 = rows[0]
            if cols[-1] < self.w - 3 and p[:, cols[-1] + 3:].sum() > 20:
                x1 = cols[-1] + 1
            if cols[0] > 2 and p[:, :cols[0] - 2].sum() > 20:
                x0 = cols[0]
        return [int(x0), int(y0), int(x1), int(y1)]

    def window_mask(self):
        x0, y0, x1, y1 = self.window
        m = np.zeros((self.h, self.w, 1), np.float32)
        m[y0:y1, x0:x1] = 1
        return m


def hexagon(cx, cy, a, b):
    """pointy-top hexagon: half-width a, half-height b"""
    return [(cx, cy - b), (cx + a, cy - b / 2), (cx + a, cy + b / 2), (cx, cy + b), (cx - a, cy + b / 2), (cx - a, cy - b / 2)]


def fit_hexagon(cand, ring_px):
    """(cx, cy, a, b) maximising candidates inside - 4 x ring pixels inside (coordinate descent)"""
    yc, xc = np.nonzero(cand)
    yr, xr = np.nonzero(ring_px)
    pc = np.stack([xc + 0.5, yc + 0.5], 1)
    pr = np.stack([xr + 0.5, yr + 0.5], 1)

    def inside(pts, h):
        cx, cy, a, b = h
        x, y = np.abs(pts[:, 0] - cx), np.abs(pts[:, 1] - cy)
        return (x <= a) & (y <= b - x * b / (2 * a))

    def score(h):
        return int(inside(pc, h).sum()) - 4 * int(inside(pr, h).sum())
    h = [float(pc[:, 0].mean()), float(pc[:, 1].mean()), float(np.ptp(pc[:, 0])) / 2, float(np.ptp(pc[:, 1])) / 2]
    for step in (4, 2, 1, 0.5, 0.25):
        for _ in range(20):
            moved = False
            for i in range(4):
                for dv in (-step, step):
                    t = list(h)
                    t[i] += dv
                    if score(t) > score(h):
                        h, moved = t, True
            if not moved:
                break
    return hexagon(*h)


def frame_hex(ref, log):
    """inside = convex hull of where the base's picture shows its background (not opaque) or its render
    unchanged; ring = the rest of the base's picture; background = a smooth surface (cubic in x, y)
    fitted where it shows (inside, the render not there)"""
    O, P, V = ref.O, ref.P, ref.V
    a = O[..., 3]
    core = erode(a > 0.5, 2)
    cand = (core & (a < 0.95)) | ((P[..., 3] > 0.95) & (np.abs(O - P).max(2) < 0.08) & V & core)
    # the inside: the hexagon (pointy top, vertical sides) holding the most of those and none of the
    # pixels that are surely ring (dark and opaque where the render isn't)
    L = O[..., :3].max(2)
    ring_px = core & (a > 0.95) & (L < 0.12) & ((P[..., 3] < 0.5) | (np.abs(O - P).max(2) > 0.25) | ~V)
    hull = fit_hexagon(cand, ring_px)
    inner, hull = convex_mask(hull, ref.w, ref.h)
    inside = inner > 0.999
    known = inside & V & (P[..., 3] < 0.02)
    ys, xs = np.mgrid[0:ref.h, 0:ref.w].astype(np.float64)
    xs, ys = xs / ref.w - 0.5, ys / ref.h - 0.5
    basis = np.stack([np.ones_like(xs), xs, ys, xs * xs, xs * ys, ys * ys, xs ** 3, xs * xs * ys, xs * ys * ys, ys ** 3], -1)
    bg = np.zeros_like(O)
    if known.sum() > 50:
        A = basis[known]
        for c in range(4):
            coef = np.linalg.lstsq(A, O[..., c][known].astype(np.float64), rcond=None)[0]
            bg[..., c] = basis @ coef
        bg = np.clip(bg, 0, 1)
        bg[..., :3] = np.minimum(bg[..., :3], bg[..., 3:4])
        rms = float(np.sqrt(((bg - O)[known] ** 2).mean()))
        log.append('%s: frame inside %d px (hexagon %s), background fitted on %d px: rms %.3f, alpha %.2f-%.2f' % (
            ref.st, int(inside.sum()), [(round(x, 1), round(y, 1)) for x, y in hull], int(known.sum()), rms,
            float(bg[..., 3][inside].min()), float(bg[..., 3][inside].max())))
    return inner[..., None], O * (1 - inner[..., None]), bg


# ---------------------------------------------------------------- outline / shadow styles
def fill_holes(a):
    """a 0..1 mask with its enclosed holes (below 0.5, not reaching the border) filled"""
    bg = a < 0.5
    reach = np.zeros_like(bg)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = bg[0], bg[-1], bg[:, 0], bg[:, -1]
    while True:
        grown = reach.copy()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grown |= shift(reach, dx, dy)
        grown &= bg
        if (grown == reach).all():
            break
        reach = grown
    return np.where(bg & ~reach, 1.0, a).astype(np.float32)


def style_apply(fill, p):
    """max(dilate(fill, r1), k * shift(dilate(fill, r2), dx, dy)), its holes filled if p[5]"""
    r1, r2, dx, dy, k = p[:5]
    d = dist_field(fill, max(r1, r2))
    out = np.maximum(dilated(fill, d, r1), k * shift(dilated(fill, d, r2), dx, dy))
    return fill_holes(out) if len(p) > 5 and p[5] else out


def style_fit(fill, outer, rmax=10, dmax=10, fix_r1=None):
    """the style (r1, r2, dx, dy, k) making outer from fill: coordinate descent on the mean |error|
    from a few starts, on the part of the picture around the shapes"""
    ys, xs = np.nonzero((fill > 0.05) | (outer > 0.05))
    m = rmax + dmax + 2
    y0, y1 = max(0, ys.min() - m), min(fill.shape[0], ys.max() + 1 + m)
    x0, x1 = max(0, xs.min() - m), min(fill.shape[1], xs.max() + 1 + m)
    fill, outer = fill[y0:y1, x0:x1], outer[y0:y1, x0:x1]
    rs = [x * 0.5 for x in range(0, 2 * rmax + 1)]
    d = dist_field(fill, rmax)
    dil = {r: dilated(fill, d, r) for r in rs}
    memo = {}

    def err(p):
        key = tuple(p)
        if key not in memo:
            r1, r2, dx, dy, k = p
            memo[key] = float(np.abs(np.maximum(dil[r1], k * shift(dil[r2], dx, dy)) - outer).mean())
        return memo[key]
    choices = [rs if fix_r1 is None else [fix_r1], rs, list(range(-2, dmax + 1)), list(range(-2, dmax + 1)),
               [x / 20.0 for x in range(1, 21)]]
    best = None
    q = rmax / 10.0
    for r1 in ([fix_r1] if fix_r1 is not None else [1.0 * q, 3.0 * q, 6.0 * q]):
        for r2 in (1.0 * q, 4.0 * q, 8.0 * q):
            for dxy in ((2, 2), (4, 5), (6, 10)):
                for k in (0.3, 0.6, 1.0):
                    p = [min(rs, key=lambda v: abs(v - r1)), min(rs, key=lambda v: abs(v - r2)), dxy[0], dxy[1], k]
                    for _ in range(5):
                        old = list(p)
                        for i, vals in enumerate(choices):
                            p[i] = min(vals, key=lambda v: err(p[:i] + [v] + p[i + 1:]))
                        if p == old:
                            break
                    if best is None or err(p) < err(best):
                        best = list(p)
    # some styles fill the letters' enclosed counters (chrn_12), some don't (chrn_11's G)
    r1, r2, dx, dy, k = best
    filled = fill_holes(np.maximum(dil[r1], k * shift(dil[r2], dx, dy)))
    e_holes = float(np.abs(filled - outer).mean())
    return (best + [1], e_holes) if e_holes < err(best) else (best + [0], err(best))


def stock_parts(ref, log):
    """the base's stock icon: its head (where it is the render) and the outline / shadow style"""
    O, P = ref.O, ref.P
    head = ((np.abs(O - P).max(2) < 0.1) & (O[..., 3] > 0.9) & ref.V)
    im = Image.fromarray(head.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    head = np.asarray(im).astype(np.float32) / 255
    p, e = style_fit(head, O[..., 3], rmax=6, dmax=6)
    ring = (O[..., 3] > 0.9) & (head < 0.1)
    col = np.median(O[..., :3][ring] / np.maximum(O[..., 3:4][ring], 1e-6), 0) if ring.any() else np.zeros(3)
    log.append('stock_90: outline r %.1f, shadow r %.1f at (%d, %d) x %.2f, colour %s (mean error %.3f)' % (
        p[0], p[1], p[2], p[3], p[4], tuple(int(round(c * 255)) for c in col), e))
    return p, col.astype(np.float32), box_of(head)


def head_cut(fighter, cache, key, log):
    """the new fighter's head as chara_4 cuts it (chara_4 is the head of the same render with a shadow
    added; the head = the part that matches the render): (chara_4 -> chara_3 fit, mask in chara_4's
    pixels, the head's box in chara_3's pixels)"""
    c4 = fighter.c4
    if c4 is None:
        return None
    f4 = cached(cache, key + '/chara_4_in_chara_3', lambda: register_best(fighter.c3, c4, 1.0, 12.0, min_cover=0.8))
    log.append('%s: chara_4 in chara_3: %s' % (key, f4))
    pred = warp(fighter.c3, f4.ax, f4.bx, f4.ay, f4.by, c4.shape[1], c4.shape[0])
    m = ((np.abs(pred - c4).max(2) < 0.12) & (c4[..., 3] > 0.5)).astype(np.uint8) * 255
    m = Image.fromarray(m).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(3))
    m = np.asarray(m).astype(np.float32)[..., None] / 255
    ys, xs = np.nonzero(m[..., 0] > 0.5)
    box = (f4.ax * xs.min() + f4.bx, f4.ay * ys.min() + f4.by, f4.ax * (xs.max() + 1) + f4.bx, f4.ay * (ys.max() + 1) + f4.by)
    return f4, m, box


def box_of(mask):
    ys, xs = np.nonzero(mask > 0.5)
    return (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))


# ---------------------------------------------------------------- name plates
def plate_layers(img, bc5):
    """a plate's fill (0..1) and layers: BC5 = R (fill, its shadow at a low level) and G (fill + outline
    + shadow); RGBA = white-ish fill on a dark outline / shadow, alpha"""
    f = img.astype(np.float32) / 255
    if bc5:
        R, G = f[..., 0], f[..., 1]
        sh = (G > 0.5) & (R < 0.5) & (R > 0.02)
        k = float(np.median(R[sh])) if sh.any() else 0.0
        fill = np.clip((R - k) / (1 - k), 0, 1) * (R > k + 0.04)
        return fill, {'R': R, 'G': G}
    a = f[..., 3]
    L = f[..., :3].mean(2)
    dk = (a > 0.95) & (L < 0.3)
    dark = float(np.median(L[dk])) if dk.any() else 0.1
    fill = np.clip((L - dark) / (0.92 - dark), 0, 1) * (a > 0.5)
    return fill, {'A': a, 'RGB': f[..., :3]}


def components(mask):
    """connected components (8-neighbour) of a boolean mask: label array, count"""
    lab = np.zeros(mask.shape, np.int32)
    h, w = mask.shape
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n += 1
        lab[y0, x0] = n
        stack = [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for yy in (y - 1, y, y + 1):
                for xx in (x - 1, x, x + 1):
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
    return lab, n


def segment(fill, n):
    """a plate's glyphs, left to right: [(x0, x1, soft mask [h, x1 - x0], core x0, core x1)] (core: fill
    over half); None unless there are n
    (letters are separate shapes, some only above a higher fill level; the rest of the fill goes to the
    nearest)"""
    for th in (0.35, 0.5, 0.65, 0.8):          # touching letters part at a higher level
        lab, k = components(fill > th)
        sizes = np.bincount(lab.ravel(), minlength=k + 1)
        keep = [i for i in range(1, k + 1) if sizes[i] >= 8]
        if len(keep) == n:
            break
    else:
        return None
    grown = np.where(np.isin(lab, keep), lab, 0)
    for _ in range(4):
        g = grown.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = shift(grown, dx, dy)
            g = np.where((g == 0) & (sh > 0) & (fill > 0), sh, g)
        grown = g
    out = []
    for i in keep:
        m = grown == i
        xs = np.flatnonzero(m.any(0))
        x0, x1 = int(xs[0]), int(xs[-1]) + 1
        core = np.flatnonzero((m & (fill > 0.5)).any(0))
        out.append((x0, x1, np.where(m[:, x0:x1], fill[:, x0:x1], 0).astype(np.float32), int(core[0]), int(core[-1]) + 1))
    out.sort(key=lambda r: r[0] + r[1])
    return out


def glyph_q(cond, gm, ui, img, cl, cr):
    """an O glyph with a Q's tail: a stroke of the O's own thickness from inside its lower right to its
    bottom right corner, in the letter's colour row by row"""
    gm, img = gm.copy(), img.copy()
    ys, xs = np.flatnonzero(gm.max(1) > 0.5), np.flatnonzero(gm.max(0) > 0.5)
    t, bt, l, r = ys[0], ys[-1], xs[0], xs[-1]
    mid = gm[(t + bt) // 2] > 0.5
    th = max(2.0, float(np.argmin(mid[l:]) if not mid[l:].all() else 2))      # the left stroke's width
    p0 = np.array([l + 0.58 * (r - l), t + 0.62 * (bt - t)])
    p1 = np.array([r + 0.5, bt + 0.5])
    yy, xx = np.mgrid[0:gm.shape[0], 0:gm.shape[1]].astype(np.float64)
    q = np.stack([xx, yy], -1) - p0
    d = p1 - p0
    u = np.clip((q @ d) / (d @ d), 0, 1)
    dist = np.linalg.norm(q - u[..., None] * d, axis=-1)
    cov = np.clip(th / 2 + 0.5 - dist, 0, 1).astype(np.float32)
    cov[bt + 1:] = 0                    # on the baseline: the glyph checks hold the letters to it
    cov[:, r + 2:] = 0
    rows = {}
    for y in range(gm.shape[0]):
        on = gm[y] > 0.5
        if on.any():
            rows[y] = img[y][on].mean(0)
    new = (cov > 0) & (gm < 0.5)
    for y, x in zip(*np.nonzero(new)):
        ny = min(rows, key=lambda k: abs(k - y))
        img[y, x] = np.round(rows[ny]).astype(img.dtype)
    return (cond, np.maximum(gm, cov), ui, img, cl, cr)


class GlyphLib:
    """the letters of one plate set (chrn_11: capitals; chrn_12 / chrn_40: big + small capitals)"""
    def __init__(self, st, s4chr, log):
        self.st = st
        self.small_caps = st != 'chrn_11'
        self.glyphs = {}      # (char, big) -> [(condense, fill crop, ui, colour crop)]
        self.pairs = {}       # (c1, big1, c2, big2) -> [gap at natural width]
        self.plates = []      # (text centre, drawn width, condense, ui)
        d = os.path.join(s4chr, st)
        raw = []
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r'%s_(\w+?)_(\d\d)\.nut$' % st, f)
            if not m:
                continue
            ui, nn = m.group(1), m.group(2)
            text = PLATE_TEXT_VARIANT.get('%s_%s' % (ui, nn)) or (PLATE_TEXT.get(ui) if nn == '01' else None)
            if not text:
                continue
            dd, texs = load_nut_bytes(open(os.path.join(d, f), 'rb').read())
            self.bc5 = (texs[0].fmt & 0x3F) == 0x35
            img = nut.decode(dd, texs[0])
            fill, _ = plate_layers(img, self.bc5)
            chars = [c for c in text if c != ' ']
            runs = segment(fill, len(chars))
            if runs is not None:
                raw.append((ui, text, chars, runs, fill, img))
        # every glyph sits on the common baseline, small capitals at their common height: a plate with
        # a glyph off that (two-line names, a letter cut wrong: Ike's "e" took part of the "k" and
        # came out 5 px too tall) gives nothing
        ext = {}
        for ui, text, chars, runs, fill, img in raw:
            for (_x0, _x1, gm, _c0, _c1), big in zip(runs, self.bigs(text)):
                ys = np.flatnonzero(gm.max(1) > 0.5)
                ext.setdefault(big, []).append((ys[0], ys[-1] + 1))
        line = {b: (float(np.median([e[0] for e in v])), float(np.median([e[1] for e in v]))) for b, v in ext.items()}
        tol = max(2.0, 0.07 * (line[False][1] - line[False][0])) if False in line else 2.0   # ~2 px on chrn_12
        kept, dropped = [], []
        for r in raw:
            ui, text, chars, runs, fill, img = r
            ok = True
            for (_x0, _x1, gm, _c0, _c1), big in zip(runs, self.bigs(text)):
                ys = np.flatnonzero(gm.max(1) > 0.5)
                # (big letters' height varies from plate to plate, 36-46 px on chrn_12: bottoms only)
                ok &= abs(ys[-1] + 1 - line[big][1]) <= tol and (big or abs(ys[0] - line[big][0]) <= tol)
            (kept if ok else dropped).append(r)
        raw = kept
        self.line = line
        widths = {}
        for ui, text, chars, runs, fill, img in raw:
            for c, (_x0, _x1, _m, c0, c1), big in zip(chars, runs, self.bigs(text)):
                widths.setdefault((c.upper(), big), []).append(c1 - c0)
        nat = {k: float(np.percentile(v, 80)) for k, v in widths.items()}
        for ui, text, chars, runs, fill, img in raw:
            bigs = self.bigs(text)
            ratios = [(c1 - c0) / nat[(c.upper(), b)] for c, (_x0, _x1, _m, c0, c1), b in zip(chars, runs, bigs) if len(widths[(c.upper(), b)]) > 1]
            cond = float(np.median(ratios)) if ratios else 1.0
            cond = 1.0 if cond > 0.97 else cond
            lo, hi = min(r[3] for r in runs), max(r[4] for r in runs)
            self.plates.append(((lo + hi) / 2.0, hi - lo, cond, ui))
            for i, (c, (x0, x1, gm, c0, c1), b) in enumerate(zip(chars, runs, bigs)):
                self.glyphs.setdefault((c.upper(), b), []).append((cond, gm, ui, img[:, x0:x1], c0 - x0, c1 - x0))
                if i + 1 < len(chars) and not self.space_after(text, i):
                    self.pairs.setdefault((c.upper(), b, chars[i + 1].upper(), bigs[i + 1]), []).append((runs[i + 1][3] - c1) / cond)
        # no Smash 4 name has a Q (Squirtle's): the O with a tail across its lower right
        for b in (True, False):
            if ('O', b) in self.glyphs and ('Q', b) not in self.glyphs:
                self.glyphs[('Q', b)] = [glyph_q(*g) for g in self.glyphs[('O', b)]]
                nat[('Q', b)] = nat[('O', b)]
                log.append('%s: Q (%s) made from the O (%s)' % (st, 'big' if b else 'small',
                                                              ', '.join(g[2] for g in self.glyphs[('O', b)])))
        self.nat = nat
        log.append('%s: glyphs from %d plates (%s); left out, a glyph off the line: %s; %s' % (
            st, len(raw), ', '.join(r[0] for r in raw), ', '.join(r[0] for r in dropped) or 'none',
            '; '.join('%s letters rows %.0f-%.0f' % ('big' if b else 'small', t, bt) for b, (t, bt) in sorted(line.items()))))

    def bigs(self, text):
        return [(not self.small_caps) or c.isupper() or not c.isalpha() for c in text if c != ' ']

    @staticmethod
    def space_after(text, i):
        j = -1
        for k, c in enumerate(text):
            if c != ' ':
                j += 1
                if j == i:
                    return k + 1 < len(text) and text[k + 1] == ' '
        return False

    def compose(self, text, h, w, log):
        """fill and glyph colours of text laid out as the plates are (centred where theirs are)"""
        chars = [c for c in text if c != ' ']
        bigs = self.bigs(text)
        pieces = []
        for c, b in zip(chars, bigs):
            opts = self.glyphs.get((c.upper(), b))
            if not opts:
                raise SystemExit('%s: no plate has the letter %r (%s)' % (self.st, c, 'big' if b else 'small'))
            # the least condensed; of those, the one nearest the letter's usual width
            cond, fill, ui, img, cl, cr = max(opts, key=lambda o: (o[0], -abs((o[5] - o[4]) / o[0] - self.nat[(c.upper(), b)])))
            if cond < 1.0:
                nw = max(1, int(round(fill.shape[1] / cond)))
                cl, cr = cl * nw / fill.shape[1], cr * nw / fill.shape[1]
                fill = np.asarray(Image.fromarray(fill.astype(np.float32), 'F').resize((nw, h), Image.LANCZOS))
                img = np.asarray(Image.fromarray(img).resize((nw, h), Image.LANCZOS))
            pieces.append((fill, img, ui, cond, cl, cr))
        by_class = {}
        for (c1, b1, c2, b2), v in self.pairs.items():
            by_class.setdefault((b1, b2), []).extend(v)
        gaps = []
        for i in range(len(chars) - 1):
            k = (chars[i].upper(), bigs[i], chars[i + 1].upper(), bigs[i + 1])
            own = k in self.pairs
            if own:
                g = float(np.median(self.pairs[k]))
            else:       # the left letter's spacing after anything and the right one's before anything
                left = [x for kk, v in self.pairs.items() if kk[:2] == k[:2] and kk[3] == k[3] for x in v]
                right = [x for kk, v in self.pairs.items() if kk[2:] == k[2:] and kk[1] == k[1] for x in v]
                est = [float(np.median(v)) for v in (left, right) if v]
                g = float(np.mean(est)) if est else float(np.median(by_class.get((bigs[i], bigs[i + 1]), [2.0])))
            if self.space_after(text, i):
                g += 0.08 * h
            gaps.append((g, own))
        total = sum(p[5] - p[4] for p in pieces) + sum(g for g, _ in gaps)
        natural = [p for p in self.plates if p[2] == 1.0]
        centre = float(np.median([p[0] for p in natural])) if natural else w / 2.0
        max_w = max(p[1] for p in self.plates)
        cond = min(1.0, max_w / total)
        fillc = np.zeros((h, w), np.float32)
        colc = np.zeros((h, w, 4), np.float32)
        x = centre - total * cond / 2
        used = []
        for i, (fill, img, ui, c0, cl, cr) in enumerate(pieces):
            nw = max(1, int(round(fill.shape[1] * cond)))
            if nw != fill.shape[1]:
                cl, cr = cl * nw / fill.shape[1], cr * nw / fill.shape[1]
                fill = np.asarray(Image.fromarray(fill.astype(np.float32), 'F').resize((nw, h), Image.LANCZOS))
                img = np.asarray(Image.fromarray(img).resize((nw, h), Image.LANCZOS))
            xi = int(round(x - cl))
            x0, x1 = max(0, xi), min(w, xi + nw)
            sel = np.clip(fill[:, x0 - xi:x1 - xi], 0, 1)
            fillc[:, x0:x1] = np.maximum(fillc[:, x0:x1], sel)
            colc[:, x0:x1] = colc[:, x0:x1] * (1 - sel[..., None]) + img[:, x0 - xi:x1 - xi].astype(np.float32) / 255 * sel[..., None]
            ys = np.flatnonzero(fill.max(1) > 0.5)
            used.append('%s (%s, rows %d-%d) from %s%s' % (chars[i], 'big' if bigs[i] else 'small', ys[0], ys[-1] + 1, ui,
                                               '' if c0 == 1.0 else ', its plate condensed x%.2f, undone' % c0))
            x += (cr - cl) + (gaps[i][0] * cond if i < len(gaps) else 0)
        log.append('%s: %r: %s; spacing: %s; %.0f px wide at x %.0f%s' % (
            self.st, text, '; '.join(used),
            ', '.join('%s%s %s' % (chars[i], chars[i + 1], 'as on a plate' if g[1] else 'estimated') for i, g in enumerate(gaps)),
            total * cond, centre, '' if cond == 1.0 else ' (condensed x%.2f to fit)' % cond))
        return fillc, colc


def make_plate(st, ref_img, lib, text, log):
    """the plate for text, in the base plate's style (fitted on the base's own plate)"""
    h, w = ref_img.shape[:2]
    fill_r, layers = plate_layers(ref_img, lib.bc5)
    fill, col = lib.compose(text, h, w, log)
    out = np.zeros((h, w, 4), np.float32)
    if lib.bc5:
        pg, eg = style_fit(fill_r, layers['G'], rmax=12, dmax=12)
        pr, er = style_fit(fill_r, layers['R'], rmax=12, dmax=12, fix_r1=0.0)
        log.append('%s: G = fill grown %.1f + shadow (grown %.1f) at (%d, %d) x %.2f (mean error %.3f); R = fill + shadow '
                   '(grown %.1f) at (%d, %d) x %.2f (mean error %.3f)' % (st, pg[0], pg[1], pg[2], pg[3], pg[4], eg,
                                                                         pr[1], pr[2], pr[3], pr[4], er))
        out[..., 0] = style_apply(fill, pr)
        out[..., 1] = style_apply(fill, pg)
        out[..., 3] = 1
    else:
        pa, ea = style_fit(fill_r, layers['A'], rmax=10, dmax=10)
        a = layers['A']
        dark = np.median(layers['RGB'][(a > 0.95) & (fill_r < 0.05)], 0)
        log.append('%s: alpha = fill grown %.1f + shadow (grown %.1f) at (%d, %d) x %.2f%s (mean error %.3f), dark %s' % (
            st, pa[0], pa[1], pa[2], pa[3], pa[4], ', counters filled' if pa[5] else '', ea, tuple(int(round(c * 255)) for c in dark)))
        f3 = fill[..., None]
        out[..., :3] = col[..., :3] * f3 + dark * (1 - f3)
        out[..., 3] = style_apply(fill, pa)
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)


# ================================================================ contact sheet
def contact_sheet(items, path, old_name, new_name, base_ult, H=200):
    """per set: the old picture (the base's Smash 4 art), the base's Ultimate art through the same
    framing (how well the cross-game fit lines up), the new picture; on a checkerboard (BC5 plates:
    red / green channels)"""
    def view(img, bc5):
        img = img.astype(np.float32) / 255
        if bc5:
            rgb = np.stack([img[..., 0], img[..., 1], np.zeros_like(img[..., 0])], 2)
            al = np.ones(img.shape[:2] + (1,), np.float32)
        else:
            rgb, al = img[..., :3], img[..., 3:4]
        h, w = img.shape[:2]
        chk = (np.indices((h, w)).sum(0) // max(4, h // 16)) % 2
        bg = np.where(chk[..., None] == 1, 0.78, 0.55)
        return Image.fromarray(((rgb * al + bg * (1 - al)) * 255).astype(np.uint8))
    rows = []
    for st, old, check, new, bc5 in items:
        ims = [view(old, bc5), None if check is None else view(check, bc5), view(new, bc5)]
        if st == 'chr_12':          # at its shown aspect (the 8:1 squeeze undone)
            ims = [None if im is None else im.resize((im.width * 8, im.height)) for im in ims]
        s = min(H / ims[0].height, 520.0 / ims[0].width)
        size = (max(1, int(ims[0].width * s)), max(1, int(ims[0].height * s)))
        rows.append((st, [None if im is None else im.resize(size, Image.LANCZOS) for im in ims]))
    col = max(r[1][0].width for r in rows) + 16
    W = 90 + 3 * col
    sheet = Image.new('RGB', (W, sum(r[1][0].height + 12 for r in rows) + 30), (32, 32, 36))
    d = ImageDraw.Draw(sheet)
    for k, label in enumerate(('old: %s (%s\'s Smash 4 art)' % (new_name, old_name),
                               'fit check: %s\'s Ultimate art, same framing' % base_ult,
                               'new: %s (Ultimate art)' % new_name)):
        d.text((90 + k * col, 8), label, fill=(255, 255, 255))
    y = 28
    for st, ims in rows:
        d.text((8, y + ims[0].height // 2 - 6), st + '_01', fill=(255, 255, 255))
        for k, im in enumerate(ims):
            if im is not None:
                sheet.paste(im, (90 + k * col, y))
        y += ims[0].height + 12
    sheet.save(path)


# ================================================================ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ult-ui', required=True)
    ap.add_argument('--s4-chr', required=True)
    ap.add_argument('--templates', required=True)
    ap.add_argument('--ult', required=True, help="the port's Ultimate name (brave)")
    ap.add_argument('--ult-base', required=True, help="the base fighter's Ultimate name (reflet)")
    ap.add_argument('--ui-name', required=True, help="the port's Smash 4 UI name (Hero)")
    ap.add_argument('--s4-base', required=True, help="the base's Smash 4 UI name (Reflet)")
    ap.add_argument('--name-text', help='the name on the plates (default: the UI name)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--extra-out')
    ap.add_argument('--contact')
    ap.add_argument('--sets')
    ap.add_argument('--costumes', default='1-8')
    ap.add_argument('--fits')
    ap.add_argument('--stock-icon', action='store_true', help="stock_90: Ultimate's own stock icon (chara_2), fitted "
                    "into the base head's box (the default for ports: tools/ultimate_port.py)")
    ap.add_argument('--stock-whole', action='store_true', help="stock_90: the port's chara_4 whole, fitted into "
                    "the base head's box (where chara_4 isn't the head of chara_3's render)")
    ap.add_argument('--cross', help='SCALE,X,Y: C (the base\'s chara_0 c00 pixel -> its Smash 4 chr_90_01 pixel) '
                    'set by hand instead of matched (Mario: the poses differ; from eyes, nose and cap emblem)')
    ap.add_argument('--no-tone', action='store_true', help="Ultimate's art as it is (not brightened as Smash 4's "
                    'renders: TONE_*)')
    a = ap.parse_args()
    TONE[0] = not a.no_tone

    log = []
    cache = json.load(open(a.fits)) if a.fits and os.path.exists(a.fits) else {}
    ult = UltUI(a.ult_ui)
    tpl = Templates(a.templates)
    sets = [x for x in a.sets.split(',') if x] if a.sets else list(SETS)
    lo, hi = (int(x) for x in a.costumes.split('-'))
    text = a.name_text or a.ui_name

    def base_file(st, nn=1):
        return os.path.join(a.s4_chr, st, '%s_%s_%02d.nut' % (st, a.s4_base, nn))

    ref90 = to_float(load_s4(base_file(REF_SET)))
    base = Fighter(ult, a.ult_base, 0, cache, log)
    # C: the base's Ultimate face frame (chara_0 c00) in its Smash 4 chr_90 (different art)
    if a.cross:         # set by hand (landmarks), where the two games' arts differ too much to match
        sc, bx, by = (float(v) for v in a.cross.split(','))
        C = Fit(0.0, sc, bx, sc, by)
    else:
        C = cached(cache, 'cross/%s_chara_0_in_%s' % (a.ult_base, REF_SET),
                   lambda: register(ref90, base.c0, 1.0, 6.0, zero_mean=True, min_cover=0.9))
    log.append('CROSS-GAME: Ultimate %s chara_0 c00 in Smash 4 %s %s_01: %s' % (a.ult_base, a.s4_base, REF_SET, C))

    fighters = {}

    def fighter(c):
        if c not in fighters:
            fighters[c] = Fighter(ult, a.ult, c, cache, log)
        return fighters[c]

    ids = {'next': None, 'used': None}

    def new_id():
        if ids['used'] is None:
            kinds = json.load(open(os.path.join(HERE, 'extra_kinds.json')))['kinds']
            cid = next(k['ui']['id'] for k in kinds if k.get('ui', {}).get('name') == a.ui_name)
            ids['next'], ids['used'] = NEW_TEXTURE_IDS + 0x100 * (cid - 59), tpl.ids()
        while ids['next'] in ids['used']:
            ids['next'] += 1
        ids['used'].add(ids['next'])
        return ids['next']

    contact = []
    for st in sets:
        kind, opts = SETS[st]
        if not os.path.exists(base_file(st)):
            log.append('%s: the base has no %s; skipped' % (st, base_file(st)))
            continue
        base_img = load_s4(base_file(st))
        if kind == 'plate':
            lib = GlyphLib(st, a.s4_chr, log)
            plate = make_plate(st, base_img, lib, text, log)
            nns = [1]
        else:
            ref = SetRef(st, kind, opts, base_img, ref90, cache, log)
            if ref.window != [0, 0, ref.w, ref.h]:
                log.append('%s: the base picture is cut to %s; so is the new one' % (st, ref.window))
            if kind == 'hex':
                inner, ring, bg = frame_hex(ref, log)
            elif kind == 'stock':
                stock_style, stock_col, stock_box = stock_parts(ref, log)
            nns = range(lo, hi + 1)

        def frame(f, key, nn):
            """the set's picture of costume f (premultiplied)"""
            # set pixel -> base chr_90 -> base face frame = this fighter's face frame (chara_0) -> chara_3
            to3 = ref.F.then(C.inv()).then(f.f0)
            if kind == 'plain':
                return f.render(to3, ref.w, ref.h) * ref.window_mask()
            if kind == 'hex':
                return ring + over(f.render(to3, ref.w, ref.h), bg) * inner
            # stock: the face where the base's face is (the face frame, as everywhere), but small enough
            # that the head (chara_4's cut, down to the bottom of the face frame chara_0) stays inside the
            # base head's box (+3 px): Smash 4 fits each icon's head to the icon
            if a.stock_icon and key.startswith(a.ult + '_') and f.c2 is not None:
                # Ultimate's own stock icon (chara_2: the finished icon, outline and all), whole, its box
                # fitted into the base head's box (+3 px), centred; no Smash 4 outline over its own.
                # Squirtle's chara_4 cut (--stock-whole) was his select-screen art shrunk (user)
                c2 = f.c2
                x0, y0, x1, y1 = box_of(c2[..., 3])
                ux0, uy0 = max(1.0, stock_box[0] - 3), max(1.0, stock_box[1] - 3)
                ux1, uy1 = min(ref.w - 1.0, stock_box[2] + 3), min(ref.h - 1.0, stock_box[3] + 3)
                sc = max((x1 - x0) / (ux1 - ux0), (y1 - y0) / (uy1 - uy0))
                bx = (x0 + x1) / 2 - sc * (ux0 + ux1) / 2
                by = (y0 + y1) / 2 - sc * (uy0 + uy1) / 2
                log.append('%s_%02d (%s): chara_2 (Ultimate\'s stock icon), %.2f px a pixel' % (st, nn, key, sc))
                return tone(warp(c2, sc, bx, sc, by, ref.w, ref.h))
            cut = head_cut(f, cache, key, log)
            if cut is None:
                head = f.render(to3, ref.w, ref.h)
            elif a.stock_whole and key.startswith(a.ult + '_'):
                # chara_4 isn't a cut of chara_3's render (Squirtle's: his upper body, turned): the icon
                # art as it is, its box fitted into the base head's box (+3 px), centred
                c4 = f.c4
                x0, y0, x1, y1 = box_of(c4[..., 3])
                ux0, uy0 = max(2.0, stock_box[0] - 3), max(2.0, stock_box[1] - 3)
                ux1, uy1 = min(ref.w - 2.0, stock_box[2] + 3), min(ref.h - 2.0, stock_box[3] + 2)
                sc = max((x1 - x0) / (ux1 - ux0), (y1 - y0) / (uy1 - uy0))      # chara_4 px a pixel
                bx = (x0 + x1) / 2 - sc * (ux0 + ux1) / 2
                by = (y0 + y1) / 2 - sc * (uy0 + uy1) / 2
                log.append('%s_%02d (%s): chara_4 whole (its fit in chara_3: %.2f), %.2f px a pixel' % (
                    st, nn, key, cut[0].score, sc))
                head = tone(warp(c4, sc, bx, sc, by, ref.w, ref.h))
            else:
                f4, m4, hbox = cut
                fc = ref.F.then(C.inv())                       # stock px -> face frame px
                pcx, pcy = (63.5 - fc.bx) / fc.ax, (63.5 - fc.by) / fc.ay
                qcx, qcy = f.f0.ax * 63.5 + f.f0.bx, f.f0.ay * 63.5 + f.f0.by
                bottom = min(hbox[3], f.f0.ay * 128 + f.f0.by)
                ux0, uy0 = max(2.0, stock_box[0] - 3), max(2.0, stock_box[1] - 3)
                ux1, uy1 = min(ref.w - 2.0, stock_box[2] + 3), min(ref.h - 2.0, stock_box[3] + 2)
                sc = max([to3.ax] + [num / den for num, den in (
                    (qcx - hbox[0], pcx - ux0), (hbox[2] - qcx, ux1 - pcx), (qcy - hbox[1], pcy - uy0),
                    (bottom - qcy, uy1 - pcy)) if num > 0 and den > 0])
                to3 = Fit(1.0, sc, qcx - sc * pcx, sc, qcy - sc * pcy)
                ycut = pcy + (bottom - qcy) / sc
                log.append('%s_%02d (%s): face at (%.1f, %.1f), %.2f chara_3 px a pixel (face frame: %.2f), cut at y %.1f' % (
                    st, nn, key, pcx, pcy, sc, ref.F.then(C.inv()).then(f.f0).ax, ycut))
                to4 = to3.then(f4.inv())
                hm = warp(m4, to4.ax, to4.bx, to4.ay, to4.by, ref.w, ref.h)
                chin = np.clip((ycut + 1 - (np.arange(ref.h) + 0.5)) / 2.0, 0, 1)
                head = f.render(to3, ref.w, ref.h) * hm * chin[:, None, None]
            outer = style_apply(head[..., 3], stock_style)
            return over(head, np.concatenate([stock_col * outer[..., None], outer[..., None]], 2))

        for nn in nns:
            data, out_root = tpl.get(st, a.ui_name, nn), a.out
            if data is None:
                t1 = tpl.get(st, a.ui_name, 1)
                if not a.extra_out or t1 is None:
                    continue
                data = bytearray(read_nut(t1))
                tid = new_id()
                for off, _ in texture_ids(data):
                    struct.pack_into('>I', data, off, tid)
                data, out_root = bytes(data), a.extra_out
            d, texs = load_nut_bytes(data)
            t = texs[0]
            if kind == 'plate':
                img = plate
            else:
                img = to_straight(frame(fighter(nn - 1), '%s_c%02d' % (a.ult, nn - 1), nn))
            if (img.shape[1], img.shape[0]) != (t.w, t.h):
                img = np.asarray(Image.fromarray(img).resize((t.w, t.h), Image.LANCZOS))
            new = nut.replace(d, t, np.ascontiguousarray(img))
            dst = os.path.join(out_root, 'ui', 'replace', 'chr', st, '%s_%s_%02d.nut' % (st, a.ui_name, nn))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(new)
            log.append('wrote %s (texture 0x%08X, %dx%d, format 0x%X)' % (dst, t.tex_id, t.w, t.h, t.fmt))
            if nn == 1:
                d2, t2 = load_nut_bytes(new)
                # the fit check: the base's own Ultimate art through the same framing
                check = None if kind == 'plate' else to_straight(frame(base, '%s_c00' % a.ult_base, 1))
                contact.append((st, nut.decode(d, t), check, nut.decode(d2, t2[0]), (t.fmt & 0x3F) == 0x35))
        if a.fits:
            json.dump(cache, open(a.fits, 'w'), indent=1)
    if a.contact and contact:
        contact_sheet(contact, a.contact, a.s4_base, a.ui_name, a.ult_base)
    print('\n'.join(log))


if __name__ == '__main__':
    main()
