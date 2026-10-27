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


def ncc_map(img, tmp, wmask):
    """normalised correlation of tmp (features [th, tw, c], weights wmask) at every offset over img;
    windows with much less energy than the template score low (no 0 / 0 peaks on empty canvas)"""
    t = tmp * wmask[..., None]
    num = _xcorr(img, t)
    e_img = _xcorr((img ** 2).sum(2), wmask)
    e_t = float((t * tmp).sum())
    return num / np.sqrt(np.maximum(e_img, 0.25 * e_t) * max(e_t, 1e-9))


def _peak(m):
    iy, ix = np.unravel_index(np.argmax(m), m.shape)

    def sub(a, b, c):
        d = a - 2 * b + c
        return 0.0 if abs(d) < 1e-12 else 0.5 * (a - c) / d
    fy = sub(m[iy - 1, ix], m[iy, ix], m[iy + 1, ix]) if 0 < iy < m.shape[0] - 1 else 0.0
    fx = sub(m[iy, ix - 1], m[iy, ix], m[iy, ix + 1]) if 0 < ix < m.shape[1] - 1 else 0.0
    return float(m[iy, ix]), iy + fy, ix + fx


class Fit:
    """tmp pixel (x, y) = big pixel (ax * x + bx, ay * y + by); score = normalised correlation"""
    def __init__(self, score, ax, bx, ay, by):
        self.score, self.ax, self.bx, self.ay, self.by = score, ax, bx, ay, by

    def __repr__(self):
        return 'Fit(score %.4f, scale %.4f x %.4f, offset %.1f, %.1f)' % (
            self.score, 1 / self.ax, 1 / self.ay, self.bx, self.by)


def zncc_map(img, tmp, wmask):
    """zero-mean normalised correlation (one channel each, weights wmask): matches shading / edges,
    not brightness, so different renders of a face can line up"""
    img = img.sum(2) if img.ndim == 3 else img
    tmp = tmp.sum(2) if tmp.ndim == 3 else tmp
    sw = float(wmask.sum())
    mt = float((tmp * wmask).sum()) / sw
    t = (tmp - mt) * wmask
    num = _xcorr(img, t)
    s1 = _xcorr(img, wmask)
    s2 = _xcorr(img ** 2, wmask)
    var_i = np.maximum(s2 - s1 ** 2 / sw, 1e-6)
    var_t = float((t * (tmp - mt)).sum())
    return num / np.sqrt(var_i * max(var_t, 1e-9))


def _search(big, T, w, scales, ratios, min_cover, zero_mean=False):
    """big and T at one working resolution; scales: big pixels -> T pixels"""
    best = None
    th, tw = T.shape[:2]
    for s in scales:
        for r in ratios:
            W = max(4, int(round(big.shape[1] * s)))
            H = max(4, int(round(big.shape[0] * s * r)))
            sx, sy = W / big.shape[1], H / big.shape[0]
            I = _feat(resize_f(big, W, H))
            if zero_mean:
                m = zncc_map(I[..., 0], T[..., 0], w)
            else:
                m = ncc_map(I, T, w)
            cover = _xcorr(np.ones((H, W), np.float32), w) / w.sum()
            m = np.where(cover >= min_cover, m, -1)
            sc, py, px = _peak(m)
            ox, oy = px - (tw - 1), py - (th - 1)        # T pixel u = I pixel u + o
            if best is None or sc > best.score:
                best = Fit(sc, 1 / sx, ox / sx, 1 / sy, oy / sy)
    return best


def register(big, tmp, s_lo, s_hi, wmask=None, aniso=(1.0, 1.0), min_cover=0.6, steps=40, max_side=768, zero_mean=False):
    """find where tmp (premultiplied RGBA) appears in big (same art, other size / crop): scale
    (tmp px per big px) in [s_lo, s_hi], vertical / horizontal scale ratio in aniso, translation.
    Coarse to fine: a ~64 px template first, then ~200 px, then full size on a crop of big."""
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
            scales = np.exp(np.linspace(np.log(s_lo), np.log(s_hi), n)) * qx
            ratios = np.exp(np.linspace(np.log(aniso[0]), np.log(aniso[1]), 1 if aniso[0] == aniso[1] else 12)) * qy / qx
            x0 = y0 = 0
            sub = big
        else:
            s0x, s0y = 1 / fit.ax, 1 / fit.ay
            scales = s0x * qx * np.exp(np.linspace(-np.log(span), np.log(span), n))
            r0 = (s0y * qy) / (s0x * qx)
            ratios = [r0] if aniso[0] == aniso[1] else r0 * np.exp(np.linspace(-np.log(span), np.log(span), 5))
            # crop big around the current fit (template's area + a margin)
            mx, my = 0.15 * tw * fit.ax + 8, 0.15 * th * fit.ay + 8
            x0 = int(max(0, np.floor(fit.bx - mx)))
            y0 = int(max(0, np.floor(fit.by - my)))
            x1 = int(min(big.shape[1], np.ceil(fit.bx + tw * fit.ax + mx)))
            y1 = int(min(big.shape[0], np.ceil(fit.by + th * fit.ay + my)))
            sub = big[y0:y1, x0:x1]
        f = _search(sub, T, w, scales, ratios, min_cover, zero_mean)
        # back to full-size template pixels and big pixels
        fit = Fit(f.score, f.ax * qx, f.bx + x0, f.ay * qy, f.by + y0)
    return fit
