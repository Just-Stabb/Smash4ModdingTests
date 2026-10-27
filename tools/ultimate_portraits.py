#!/usr/bin/env python3
"""(draft) Smash 4 portraits for an Ultimate port from Ultimate's UI art."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bntx  # noqa: E402
import nut  # noqa: E402


# ---------------------------------------------------------------- image helpers
def premul(img):
    """RGBA uint8 -> float32 [h, w, 4] premultiplied, 0..1"""
    f = img.astype(np.float32) / 255.0
    f[..., :3] *= f[..., 3:4]
    return f


def unpremul(f):
    a = f[..., 3:4]
    rgb = np.where(a > 1e-4, f[..., :3] / np.maximum(a, 1e-4), 0)
    return np.clip(np.concatenate([rgb, a], 2) * 255 + 0.5, 0, 255).astype(np.uint8)


def resize_f(f, w, h):
    """premultiplied float image resized (Lanczos, channel by channel)"""
    out = [np.asarray(Image.fromarray(f[..., c], 'F').resize((w, h), Image.LANCZOS)) for c in range(f.shape[2])]
    return np.clip(np.stack(out, 2), 0, 1)


def warp(f, ax, bx, ay, by, w, h, quality=True):
    """output (w, h): out(x, y) = f(ax * x + bx, ay * y + by) (premultiplied float, axis-aligned scale +
    offset; outside f = transparent). Downscales are pre-filtered (area) so thin detail doesn't alias."""
    sx, sy = abs(ax), abs(ay)
    if quality and (sx > 1.25 or sy > 1.25):
        kx, ky = max(1, int(sx)), max(1, int(sy))
        H, W = f.shape[0] // ky * ky, f.shape[1] // kx * kx
        f = f[:H, :W].reshape(H // ky, ky, W // kx, kx, -1).mean((1, 3))
        ax, ay = ax / kx, ay / ky
        bx, by = (bx + 0.5) / kx - 0.5, (by + 0.5) / ky - 0.5
    pad = 4
    f = np.pad(f, ((pad, pad), (pad, pad), (0, 0)))
    bx, by = bx + pad, by + pad
    out = [np.asarray(Image.fromarray(f[..., c], 'F').transform(
        (w, h), Image.AFFINE, (ax, 0, bx + 0.5 * ax - 0.5, 0, ay, by + 0.5 * ay - 0.5), Image.BICUBIC))
        for c in range(f.shape[2])]
    return np.clip(np.stack(out, 2), 0, 1)


# ---------------------------------------------------------------- registration
def _feat(f):
    """matching features: luminance (premultiplied) and alpha"""
    lum = f[..., 0] * 0.3 + f[..., 1] * 0.59 + f[..., 2] * 0.11
    return np.stack([lum, f[..., 3]], 2)


def _xcorr(img, tmp):
    """valid-and-partial correlation of tmp over img, by FFT: out[dy, dx] = sum tmp(u) img(u + d),
    d from -(th - 1) .. ih - 1 (index offset th - 1)"""
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


def ncc_map(img, tmp, wmask=None):
    """normalised correlation of tmp (features [th, tw, c]) at every offset over img; wmask
    weights the template's pixels"""
    if wmask is None:
        wmask = np.ones(tmp.shape[:2], np.float32)
    t = tmp * wmask[..., None]
    num = _xcorr(img, t)
    e_img = _xcorr((img ** 2).sum(2), wmask)
    e_t = float((t * tmp).sum())
    return num / np.sqrt(np.maximum(e_img, 1e-6) * max(e_t, 1e-9))


def _peak(m):
    iy, ix = np.unravel_index(np.argmax(m), m.shape)
    def sub(a, b, c):
        d = a - 2 * b + c
        return 0.0 if abs(d) < 1e-12 else 0.5 * (a - c) / d
    fy = sub(m[iy - 1, ix], m[iy, ix], m[iy + 1, ix]) if 0 < iy < m.shape[0] - 1 else 0.0
    fx = sub(m[iy, ix - 1], m[iy, ix], m[iy, ix + 1]) if 0 < ix < m.shape[1] - 1 else 0.0
    return float(m[iy, ix]), iy + fy, ix + fx


def match(big, tmp, scales, wmask=None, min_cover=0.6, sy_ratio=1.0, mode='feat'):
    """where does tmp (premultiplied RGBA) sit in big, at which scale: big resized by s (s * sy_ratio
    vertically) puts tmp's pixel u at u + o. Returns (score, sx, sy, ox, oy) of the best scale:
    tmp pixel (x, y) = big pixel ((x + ox) / sx, (y + oy) / sy)."""
    T = _feat(tmp)
    w = np.ones(tmp.shape[:2], np.float32) if wmask is None else wmask.astype(np.float32)
    best = None
    for s in scales:
        sx, sy = s, s * sy_ratio
        W, H = max(8, int(round(big.shape[1] * sx))), max(8, int(round(big.shape[0] * sy)))
        sx, sy = W / big.shape[1], H / big.shape[0]
        I = _feat(resize_f(big, W, H))
        m = ncc_map(I, T, w)
        cover = _xcorr(np.ones((H, W), np.float32), w) / w.sum()
        m = np.where(cover >= min_cover, m, -1)
        sc, py, px = _peak(m)
        th, tw = tmp.shape[:2]
        r = (sc, sx, sy, px - (tw - 1), py - (th - 1))
        if best is None or r[0] > best[0]:
            best = r
    return best


def match_refine(big, tmp, s0, wmask=None, span=1.12, steps=9, rounds=3, sy_ratio=1.0, **kw):
    """match() around scale s0, narrowing the scale range each round"""
    best = None
    for _ in range(rounds):
        scales = s0 * np.exp(np.linspace(-np.log(span), np.log(span), steps))
        best = match(big, tmp, scales, wmask, sy_ratio=sy_ratio, **kw)
        s0 = best[1]
        span = span ** (2.0 / (steps - 1))
    return best
