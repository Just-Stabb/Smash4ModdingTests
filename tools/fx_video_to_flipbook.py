#!/usr/bin/env python3
"""Stock effect footage -> a game flipbook: a transparent, tightly cropped, looping (or one-shot) texture atlas
for an eft .ptcl emitter (docs/ptcl-format.md: slot 0 flipbook 0x4D5-0x50C), with a sidecar and previews.

  python3 -I tools/fx_video_to_flipbook.py CLIP OUT_DIR --name NAME --matte luma|alpha|chroma
          [--oneshot] [--range A:B] [--cells MIN:MAX] [--fpc K] [--max-side 1024] [--max-area 1048576] ...
  python3 -I tools/fx_video_to_flipbook.py --batch jobs.json [--only NAME,...] [--overview sheet.png]

jobs.json: {"out": DIR, "jobs": [{"input": PATH, "name": NAME, "matte": ..., <any option below, "-" -> "_">}]}.
Each job writes OUT/NAME/: NAME_atlas.png, NAME.json (sidecar), NAME.webp (animated, alpha),
NAME.webm (VP9 + alpha), NAME_checker.gif (over a checker, quick look), and OUT/_qa/NAME_*.png (the atlas
over checker / grey, the loop seam) for checking the matte. Nothing is written into the input's folder;
run it with `python3 -I` on downloaded footage. Needs ffmpeg (libvpx-vp9, libwebp), numpy, Pillow.

1. Matte (every frame -> premultiplied RGBA, float):
   luma    fire / sparks on black: c = (rgb - black) / (1 - black) x gain, alpha = max(c.r, c.g, c.b),
           premultiplied colour = c. The atlas stores c / alpha (straight), so colour x alpha is the footage
           itself: it composites the same with normal alpha blending (eft "Normal": src x a + dst x (1 - a))
           as with additive blending that takes the source alpha (eft "Add": src x a + dst); additive is
           what the footage was shot for (bright fire glows, black adds nothing). --black: the noise floor
           cut (default 0.02), --gain: > 1 thickens the alpha (default 1).
   alpha   footage with its own alpha (ProRes 4444 ...): --premultiplied (default on; --straight if not).
   chroma  green (or --key blue) screen: a clean plate of the screen is estimated per pixel (its median
           over frames where a pixel is screen, smoothed and filled where never seen), then a colour-
           difference key: alpha = 1 - (G - max(R, B)) / (plate's G - max(R, B)). A semi-transparent dark
           smoke keeps the fraction of the screen it lets through (smoke stays smoke). The colour is unmixed
           (pixel - (1 - alpha) x plate) / alpha, so the screen's green leaves the edges and the smoke, then
           despilled (G <= max(R, B)). Alpha is then levelled: --key-lo (default: the screen's own noise,
           its 99.5th percentile of alpha where nothing ever passes) to --key-hi (0.92) -> 0..1: soft edges kept, noise gone.
2. Range: the visible frames (alpha mass >= --vis of the peak, default 0.02). --oneshot: kept from the first
   visible frame to the last (no loop). Loop (default): searched inside the sustained part (alpha mass >=
   --sustain x the steady level (5-frame mean), default 0.8; or --range A:B, source frames, B inclusive): every start a and
   length L (L from --cells) scored by how alike the frames around the seam are (--xfade X frames before
   frame a+L against the X before a, mean L1 on a small blurred copy, relative to the clip's own median
   frame-to-frame change: 1.0 = the seam looks like an ordinary frame step), longer loops slightly
   preferred (--prefer-long). The loop's last X frames (default 6) are crossfaded (premultiplied) toward
   the X frames before a, weights 1/X .. X/X: frame L-1 is frame a-1 itself and leads into frame 0 (= a)
   as in the footage.
3. --track (x, xy): runners crossing the frame are shifted so the opaque body's centroid (alpha >= 0.6) stays
   at its mean over the loop (smoothed over 5 frames); reported as drift when not used.
4. Crop: the union of every kept frame's alpha (box-filtered 5 px, > --crop-thr, default 0.03) plus --margin
   (default 3 % of the larger side, at least 4 px). Where the effect runs off the footage (smoke trailing out
   of frame) that side fades out over --edge-feather (8 % of the crop, smoothstep) instead of ending in
   a hard line (--bottom-cut-ok: not the bottom, for fire standing on it); the sidecar lists them.
5. Cells and timing: the game runs at 60; eft plays a cell every K frames (0x504 frames a cell, integer).
   K defaults to the slowest that does not drop below the source's rate (30 fps -> 2: 30 fps; 24 -> 3: 20 fps);
   --fpc K forces it. A loop of L source frames becomes N = round(L x 60 / (fps x K)) cells (sampled by
   nearest frame; 30 / 29.97 fps sources at K = 2: every frame, N = L); a one-shot gets ceil(kept x 60 /
   (fps x K)) cells, K raised until N <= --cells max (one more when that turns an uneven step such as
   1.5 source frames a cell into a whole one: 30 fps at K = 3 -> 4).
6. Atlas: power-of-two W x H (<= --max-side, W x H <= --max-area), a grid of nx x ny >= N cells (one partial
   row at most), chosen for the largest frame (never above the source's own resolution), then the
   smallest texture. Each frame is box-filtered (premultiplied) into its cell, centred, 2 px clear of the
   cell's edge (cells may fall on fractional pixels: UVs are i / nx). Stored straight (unpremultiplied),
   colour bled out into the clear pixels so filtering / BC3 never pull black or green into an edge.
7. Sidecar NAME.json: columns, rows, frames, fps, frames_per_cell_at_60fps, loop / one-shot, kept range,
   loop seam score, crop in source pixels, alpha mode and blend hint, VRAM (RGBA8 / BC3), and the ptcl
   fields to set (flipbook mode 2 loop / 4 clamp, cells across / down, frames a cell, cells).
   tools/ptcl.py takes the atlas as is: Ptcl.set_texture(em, 0, rgba, 0x33) (BC3) with
   vfxb_to_ptcl.set_flipbook(em, mode, {'uv_div': [nx, ny]}, {'num': 0, 'num_random': 1, 'table': [0] * 32,
   'frequency': K}) and 0x506 = N (tools/supamario_ui_fx11.aura_flipbook does the same for its sprites).
"""
import argparse
import json
import math
import os
import subprocess
import warnings
from fractions import Fraction

import numpy as np
from PIL import Image, ImageDraw

GUTTER = 2


# ------------------------------------------------------------------------------------------------ decode
def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height,r_frame_rate,pix_fmt,color_space,color_range', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)['streams'][0]
    return {'w': int(s['width']), 'h': int(s['height']), 'fps': Fraction(s['r_frame_rate']),
            'pix_fmt': s.get('pix_fmt', ''), 'space': s.get('color_space', 'unknown'),
            'range': s.get('color_range', 'unknown')}


def decode(path, info, w, h, alpha):
    """every frame scaled to w x h (area filter), RGB(A) uint8 [T, h, w, C]; untagged video read as BT.709
    limited range (HD footage's norm; ffmpeg's untagged default would be BT.601)"""
    space = info['space'] if info['space'] in ('bt709', 'bt470bg', 'smpte170m', 'bt2020nc') else 'bt709'
    space = {'bt470bg': 'bt601', 'smpte170m': 'bt601', 'bt2020nc': 'bt2020'}.get(space, space)
    rng = 'full' if info['range'] in ('pc', 'jpeg') else 'tv'
    c = 4 if alpha else 3
    vf = f'scale={w}:{h}:flags=area:in_color_matrix={space}:in_range={rng}:out_range=full'
    p = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', path, '-vf', vf, '-f', 'rawvideo',
                        '-pix_fmt', 'rgba' if alpha else 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, c)


# ------------------------------------------------------------------------------------------------ helpers
def box(a, r, axes=(0, 1)):
    """box mean of radius r over the given axes (edge-clamped), any trailing channels"""
    if r <= 0:
        return a
    a = np.asarray(a, np.float32)
    for ax in axes:
        n = a.shape[ax]
        pad = [(0, 0)] * a.ndim
        pad[ax] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode='edge'), axis=ax, dtype=np.float64)
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax)
        lo = np.take(c, np.arange(0, n), axis=ax)
        a = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return a


def shrink(a, f):
    """block mean by an integer factor (frames [T, H, W, C] or one frame [H, W, C])"""
    if f <= 1:
        return a.astype(np.float32)
    *lead, h, w, c = a.shape
    h2, w2 = h // f, w // f
    a = a[..., :h2 * f, :w2 * f, :].astype(np.float32)
    return a.reshape(*lead, h2, f, w2, f, c).mean(axis=(-4, -2))


# ------------------------------------------------------------------------------------------------ mattes
class Matte:
    """frame (uint8 [H, W, C]) -> premultiplied RGBA float32 [H, W, 4]"""

    def __init__(self, opt, frames):
        self.o = opt
        self.kind = opt.matte
        if self.kind == 'chroma':
            self.plate_full = self.clean_plate(frames)
            self.plates = {}
            self.lo = None

    # chroma ------------------------------------------------------------------------------------------
    def _diff(self, rgb):
        if self.o.key == 'blue':
            return rgb[..., 2] - np.maximum(rgb[..., 0], rgb[..., 1])
        return rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])

    def clean_plate(self, frames):
        """the screen's own colour per pixel: the median of the frames where the pixel reads as screen (its
        colour difference >= 60 % of the clip's typical screen), smoothed (normalised box); pixels never
        seen as screen take their neighbourhood's (or the global screen colour)"""
        idx = np.linspace(0, len(frames) - 1, min(24, len(frames))).round().astype(int)
        sub = frames[idx].astype(np.float32) / 255
        d = self._diff(sub)
        typical = np.percentile(d, 90)
        scr = d >= 0.6 * typical
        vals = np.where(scr[..., None], sub, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)      # pixels never screen: filled below
            plate = np.nanmedian(vals, axis=0)
        valid = np.isfinite(plate[..., 0])
        glob = np.median(sub[scr], axis=0)
        plate = np.where(valid[..., None], plate, 0).astype(np.float32)
        r = max(2, max(plate.shape[:2]) // 60)
        wsum = box(valid.astype(np.float32)[..., None], r)
        filled = box(plate * valid[..., None], r) / np.maximum(wsum, 1e-6)
        plate = np.where(valid[..., None], plate, filled)
        plate = np.where(wsum > 1e-3, plate, glob)
        # a second, wider pass for large holes (the subject's own place)
        r2 = max(4, max(plate.shape[:2]) // 12)
        ok = (wsum > 1e-3) | valid[..., None]
        w2 = box(ok.astype(np.float32), r2)
        far = box(np.where(ok, plate, 0), r2) / np.maximum(w2, 1e-6)
        plate = np.where(ok, plate, np.where(w2 > 1e-3, far, glob))
        plate = box(plate, max(1, r // 2))
        self.screen_rgb = glob
        return plate.astype(np.float32)

    def plate_for(self, shape):
        h, w = shape[:2]
        if (h, w) not in self.plates:
            ph, pw = self.plate_full.shape[:2]
            if (h, w) == (ph, pw):
                self.plates[(h, w)] = self.plate_full
            else:
                ch = [np.asarray(Image.fromarray(self.plate_full[..., i]).resize((w, h), Image.Resampling.BILINEAR))
                      for i in range(3)]
                self.plates[(h, w)] = np.stack(ch, -1).astype(np.float32)
        return self.plates[(h, w)]

    def chroma(self, rgb, levels=True):
        plate = self.plate_for(rgb.shape)
        dp = np.maximum(self._diff(plate), 1e-3)
        a_raw = np.clip(1 - self._diff(rgb) / dp, 0, 1)
        prem = np.clip(rgb - (1 - a_raw[..., None]) * plate, 0, None)
        col = prem / np.maximum(a_raw[..., None], 1e-3)
        if self.o.key == 'blue':
            col[..., 2] = np.minimum(col[..., 2], np.maximum(col[..., 0], col[..., 1]))
        else:
            col[..., 1] = np.minimum(col[..., 1], np.maximum(col[..., 0], col[..., 2]))
        col = np.clip(col, 0, 1)
        if not levels:
            return a_raw
        a = np.clip((a_raw - self.lo) / max(1e-3, self.o.key_hi - self.lo), 0, 1)
        return np.concatenate([col * a[..., None], a[..., None]], -1)

    def calibrate(self, small_frames):
        """--key-lo by default: the screen's own noise, the 99.5th percentile of the raw alpha over the pixels
        the subject and its faintest smoke never reach (raw alpha < 0.1 in every sampled frame)"""
        if self.kind != 'chroma':
            return
        if self.o.key_lo is not None:
            self.lo = self.o.key_lo
            return
        idx = np.linspace(0, len(small_frames) - 1, min(24, len(small_frames))).round().astype(int)
        A = np.stack([self.chroma(small_frames[i][..., :3], levels=False) for i in idx])
        never = A.max(0) < 0.1
        v = A[:, never]
        self.lo = float(np.clip(np.percentile(v, 99.5) if v.size else 0.05, 0.01, 0.2))

    # all ----------------------------------------------------------------------------------------------
    def __call__(self, frame):
        f = frame.astype(np.float32) / 255.0 if frame.dtype == np.uint8 else np.asarray(frame, np.float32)
        if self.kind == 'luma':
            b = self.o.black
            c = np.clip((f[..., :3] - b) / (1 - b) * self.o.gain, 0, 1)
            return np.concatenate([c, c.max(-1, keepdims=True)], -1)
        if self.kind == 'alpha':
            a = f[..., 3:4]
            rgb = f[..., :3] if self.o.premultiplied else f[..., :3] * a
            return np.concatenate([np.clip(rgb, 0, 1), a], -1)
        return self.chroma(f[..., :3])


# ------------------------------------------------------------------------------------------------ analysis
def features(prem_small):
    """a blurred small copy for frame-to-frame comparison"""
    return box(prem_small, 1).reshape(len(prem_small), -1)


def dist_matrix(feat):
    t = len(feat)
    d = np.zeros((t, t), np.float32)
    for i in range(t):
        d[i] = np.abs(feat - feat[i]).mean(1)
    return d


def choose_fpc(fps, opt):
    if opt.fpc:
        return opt.fpc
    return max(1, math.ceil(60 / float(fps) - 0.01))          # 29.97 fps -> 2


def find_loop(D, lo, hi, Lmin, Lmax, X, prefer_long):
    """best (a, L): frames a .. a+L-1 kept, frames a-X .. a-1 crossfaded in; lo / hi the usable source
    frames (inclusive). Cost: mean over j in [-X, 0] of D[a+L+j, a+j] (frame a+L itself must exist)"""
    best = None
    for L in range(Lmin, Lmax + 1):
        for a in range(lo + X, hi - L + 1):
            js = np.arange(-X, 1)
            cost = float(D[a + L + js, a + js].mean())
            score = cost * (1 + prefer_long * (Lmax - L) / max(1, Lmax - Lmin))
            if best is None or score < best[0]:
                best = (score, cost, a, L)
    return best


# ------------------------------------------------------------------------------------------------ atlas
def pick_layout(n, bw, bh, native, opt):
    """(W, H, nx, ny, scale): power-of-two atlas, grid >= n with one partial row at most, the largest frame
    (capped at the source's resolution: native = source px per working px), then the smallest atlas"""
    sides = [s for s in (128, 256, 512, 1024, 2048, 4096) if s <= opt.max_side]
    best = None
    for W in sides:
        for H in sides:
            if W * H > opt.max_area:
                continue
            for nx in range(1, min(n, 255) + 1):
                ny = math.ceil(n / nx)
                if ny > 255 or nx * ny - n >= nx:
                    continue
                cw, ch = W / nx, H / ny
                s = min((cw - 2 * GUTTER - 1) / bw, (ch - 2 * GUTTER - 1) / bh)
                if s <= 0:
                    continue
                eff = min(s, native)
                key = (round(eff, 4), -W * H, -(nx * ny - n), -abs(math.log(W / H)))
                if best is None or key > best[0]:
                    best = (key, (W, H, nx, ny, min(s, native)))
    if best is None:
        raise SystemExit('no atlas layout fits: raise --max-side / --max-area or lower --cells')
    return best[1]


def resize_prem(prem, w, h):
    """premultiplied RGBA float -> w x h, box filter per channel (area average, no ringing)"""
    out = []
    for i in range(4):
        im = Image.fromarray(np.ascontiguousarray(prem[..., i], dtype=np.float32), mode='F')
        filt = Image.Resampling.BOX if (w < prem.shape[1] and h < prem.shape[0]) else Image.Resampling.BICUBIC
        out.append(np.asarray(im.resize((w, h), filt)))
    return np.clip(np.stack(out, -1), 0, 1)


def to_straight(prem):
    """premultiplied float RGBA -> straight uint8 RGBA, colour bled into the clear pixels (normalised box
    blurs, widening) so filtering / BC3 / mips never pull black into an edge"""
    a8 = np.round(np.clip(prem[..., 3], 0, 1) * 255).astype(np.uint8)
    a = a8.astype(np.float32) / 255
    col = np.clip(prem[..., :3] / np.maximum(a[..., None], 1 / 255), 0, 1)
    have = a8 > 0
    weight = a.copy()
    fill = np.zeros_like(col)
    got = np.zeros(a.shape, bool)
    for r in (1, 2, 4, 8, 16, 32):
        ws = box(weight[..., None], r)
        cs = box(prem[..., :3] * (a8 > 0)[..., None], r)
        f = cs / np.maximum(ws, 1e-6)
        new = (~got) & (ws[..., 0] > 1e-4)
        fill[new] = f[new]
        got |= new
    col = np.where(have[..., None], col, np.clip(fill, 0, 1))
    return np.concatenate([np.round(col * 255).astype(np.uint8), a8[..., None]], -1)


def checker(w, h, s=8, c0=(102, 102, 102), c1=(153, 153, 153)):
    yy, xx = np.mgrid[0:h, 0:w]
    m = ((yy // s + xx // s) % 2).astype(bool)
    img = np.empty((h, w, 3), np.uint8)
    img[~m] = c0
    img[m] = c1
    return img


def over(rgba8, bg):
    a = rgba8[..., 3:4].astype(np.float32) / 255
    return np.round(rgba8[..., :3] * a + bg * (1 - a)).astype(np.uint8)


# ------------------------------------------------------------------------------------------------ job
def run_job(opt):
    info = probe(opt.input)
    fps = info['fps']
    W0, H0 = info['w'], info['h']
    sc = min(1.0, opt.decode_max / max(W0, H0))
    w, h = int(W0 * sc) // 2 * 2, int(H0 * sc) // 2 * 2
    native = W0 / w                                 # source px per working px
    alpha_in = opt.matte == 'alpha'
    frames = decode(opt.input, info, w, h, alpha_in)
    T = len(frames)
    matte = Matte(opt, frames)
    f = max(1, round(max(w, h) / 160))
    small_raw = shrink(frames, f) / 255.0
    matte.calibrate(small_raw)
    small = np.stack([matte(x) for x in small_raw])
    mass = small[..., 3].sum((1, 2))
    peak = float(mass.max()) or 1.0
    vis = np.nonzero(mass >= opt.vis * peak)[0]
    first, last = int(vis[0]), int(vis[-1])
    K = choose_fpc(fps, opt)
    cmin, cmax = opt.cells
    X = opt.xfade
    feat = features(small)
    D = dist_matrix(feat)
    step_d = float(np.median(np.diag(D, 1)[first:last])) if last > first else 1.0
    loop = None
    if opt.oneshot:
        lo, hi = (opt.range if opt.range else (first, last))
        kept = hi - lo + 1
        cands = []
        for k in range(K, K * 4 + 1):
            step = float(fps) * k / 60
            n = math.ceil(kept / step)
            if n <= cmax:
                cands.append((k, step, n))
        if not cands:
            raise SystemExit(f'{opt.name}: {kept} frames do not fit {cmax} cells')
        k, step, n = cands[0]                        # the fastest that fits; a whole frame step one K
        nxt = [c for c in cands if c[0] == k + 1 and abs(c[1] - round(c[1])) < 0.02]   # slower if
        if not opt.fpc and step > 1.01 and abs(step - round(step)) > 0.02 and nxt:      # it ends a
            k, step, n = nxt[0]                                                         # judder
        K = k
        src_idx = [min(hi, lo + int(round(i * step))) for i in range(n)]
        seq_src = list(range(lo, hi + 1))
    else:
        if opt.range:
            lo, hi = opt.range
        else:
            tail = mass[first + (last - first) // 2: last + 1]
            steady = float(np.median(tail))
            ok = box(mass[:, None], 2, axes=(0,))[:, 0] >= opt.sustain * steady
            runs, t = [], first                      # the longest sustained run (the latest on a tie)
            while t <= last:
                if ok[t]:
                    u = t
                    while u + 1 <= last and ok[u + 1]:
                        u += 1
                    runs.append((u - t, t, u))
                    t = u + 1
                else:
                    t += 1
            _n, lo, hi = max(runs) if runs else (0, first, last)
        step = float(fps) * K / 60
        Lmin = max(X + 2, math.ceil(cmin * step - 1e-6))
        Lmax = min(int(cmax * step + 1e-6), hi - lo - X)
        if Lmax < Lmin:
            raise SystemExit(f'{opt.name}: sustained range {lo}-{hi} too short for {cmin} cells + {X} crossfade')
        score, cost, a, L = find_loop(D, lo, hi, Lmin, Lmax, X, opt.prefer_long)
        n = int(round(L / step))
        loop = {'start_frame': a, 'length_frames': L, 'crossfade_frames': X,
                'seam_cost_vs_median_frame_step': round(cost / max(step_d, 1e-9), 3),
                'search_range': [lo, hi]}
        src_idx = [a + int(round(i * L / n)) % L for i in range(n)]
        lo, hi = a, a + L - 1
        kept = L
        seq_src = list(range(a, a + L))
    # tracking ---------------------------------------------------------------------------------------
    shifts = {}
    span = sorted(set(seq_src) | ({i - L for i in seq_src[-X:]} if loop else set()))
    cxs, cys = [], []
    for i in span:
        body = (small[i, ..., 3] >= 0.6).astype(np.float32)
        s = body.sum()
        yy, xx = np.mgrid[0:body.shape[0], 0:body.shape[1]]
        cxs.append((body * xx).sum() / s * f if s else np.nan)
        cys.append((body * yy).sum() / s * f if s else np.nan)
    cxs, cys = np.array(cxs), np.array(cys)
    drift = {'x_px_source': round(float((np.nanmax(cxs) - np.nanmin(cxs)) * native), 1) if np.isfinite(cxs).any() else 0,
             'y_px_source': round(float((np.nanmax(cys) - np.nanmin(cys)) * native), 1) if np.isfinite(cys).any() else 0}
    if opt.track:
        def smooth(v):
            v = np.where(np.isfinite(v), v, np.nanmean(v))
            return box(v[:, None], 2, axes=(0,))[:, 0]
        sx, sy = smooth(cxs), smooth(cys)
        for j, i in enumerate(span):
            dx = int(round(sx.mean() - sx[j])) if 'x' in opt.track else 0
            dy = int(round(sy.mean() - sy[j])) if 'y' in opt.track else 0
            shifts[i] = (dx, dy)
    # full-resolution frames -------------------------------------------------------------------------
    cache = {}

    def full(i):
        if i not in cache:
            p = matte(frames[i])
            dx, dy = shifts.get(i, (0, 0))
            if dx or dy:
                q = np.zeros_like(p)
                ys = slice(max(0, dy), h + min(0, dy)), slice(max(0, -dy), h - max(0, dy))
                xs = slice(max(0, dx), w + min(0, dx)), slice(max(0, -dx), w - max(0, dx))
                q[ys[0], xs[0]] = p[ys[1], xs[1]]
                p = q
            cache[i] = p.astype(np.float16)
        return cache[i].astype(np.float32)

    def out_frame(c):
        """cell c's premultiplied frame (full res)"""
        i = src_idx[c]
        p = full(i)
        if loop:
            pos = i - loop['start_frame']
            j = pos - (loop['length_frames'] - X)
            if j >= 0:
                wgt = (j + 1) / X               # the last frame is frame a-1 itself
                p = (1 - wgt) * p + wgt * full(i - loop['length_frames'])
        return p

    outs = [out_frame(c).astype(np.float16) for c in range(n)]
    cache.clear()
    frames = None
    # crop -------------------------------------------------------------------------------------------
    amax = np.zeros((h, w), np.float32)
    for o in outs:
        np.maximum(amax, o[..., 3], out=amax)
    m = box(amax[..., None], 2)[..., 0] > opt.crop_thr
    ys, xs = np.nonzero(m.any(1))[0], np.nonzero(m.any(0))[0]
    y0, y1, x0, x1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
    mg = max(4, int(round(opt.margin * max(x1 - x0, y1 - y0))))
    x0, y0, x1, y1 = max(0, x0 - mg), max(0, y0 - mg), min(w, x1 + mg), min(h, y1 + mg)
    bw, bh = x1 - x0, y1 - y0
    # the effect running off the footage's edge (smoke trailing out of frame): fade it out toward that side
    # instead of a hard cut at the cell's edge
    cut = {'left': bool(m[:, :2].any()), 'right': bool(m[:, -2:].any()),
           'top': bool(m[:2].any()), 'bottom': bool(m[-2:].any())}
    if opt.bottom_cut_ok:
        cut['bottom'] = False
    ramp = np.ones((bh, bw), np.float32)
    if opt.edge_feather > 0 and any(cut.values()):
        fwid, fhei = max(2, int(opt.edge_feather * bw)), max(2, int(opt.edge_feather * bh))
        rx, ry = np.ones(bw, np.float32), np.ones(bh, np.float32)
        ss = lambda n: (lambda t: t * t * (3 - 2 * t))(np.linspace(0, 1, n, dtype=np.float32))
        if cut['left']:
            rx[:fwid] *= ss(fwid)
        if cut['right']:
            rx[-fwid:] *= ss(fwid)[::-1]
        if cut['top']:
            ry[:fhei] *= ss(fhei)
        if cut['bottom']:
            ry[-fhei:] *= ss(fhei)[::-1]
        ramp = ry[:, None] * rx[None, :]
    W, H, nx, ny, s = pick_layout(n, bw, bh, native, opt)
    fw, fh = max(1, int(round(bw * s))), max(1, int(round(bh * s)))
    atlas = np.zeros((H, W, 4), np.float32)
    cells = []
    cw, ch = W / nx, H / ny
    for c, o in enumerate(outs):
        r = resize_prem(o[y0:y1, x0:x1].astype(np.float32) * ramp[..., None], fw, fh)
        cx, cy = c % nx, c // nx
        px, py = int(math.floor(cx * cw + (cw - fw) / 2)), int(math.floor(cy * ch + (ch - fh) / 2))
        atlas[py:py + fh, px:px + fw] = r
        cells.append(r)
    del outs
    atlas8 = to_straight(atlas)
    # outputs ----------------------------------------------------------------------------------------
    od = os.path.join(opt.out, opt.name)
    qa = os.path.join(opt.out, '_qa')
    os.makedirs(od, exist_ok=True)
    os.makedirs(qa, exist_ok=True)
    Image.fromarray(atlas8, 'RGBA').save(os.path.join(od, f'{opt.name}_atlas.png'), optimize=True)
    cell8 = [to_straight(r) for r in cells]
    play_fps = 60 / K
    write_previews(od, opt.name, cell8, K, bool(loop))
    write_qa(qa, opt.name, atlas8, cell8, nx, bool(loop))
    fpsf = float(fps)
    src_dur = kept / fpsf
    out_dur = n * K / 60
    side = {
        'name': opt.name,
        'source': os.path.basename(opt.input),
        'source_size': [W0, H0], 'source_fps': round(fpsf, 3), 'source_frames': T,
        'playback': 'loop' if loop else 'one-shot',
        'kept_range': {'first_frame': int(lo), 'last_frame': int(hi), 'start_s': round(lo / fpsf, 3),
                       'end_s': round((hi + 1) / fpsf, 3), 'frames': int(kept)},
        'loop': loop,
        'frames': n, 'columns': nx, 'rows': ny,
        'atlas_size': [W, H], 'cell_size': [round(cw, 3), round(ch, 3)],
        'frame_size_in_cell': [fw, fh],
        'frame_offset_in_cell': 'centred (floor((cell - frame) / 2) from the cell origin i * W / columns)',
        'fps': round(play_fps, 3), 'frames_per_cell_at_60fps': K,
        'duration_s': round(out_dur, 4), 'source_duration_s': round(src_dur, 4),
        'speed_vs_source_pct': round(100 * src_dur / out_dur, 2),
        'crop_in_source_px': [round(x0 * native), round(y0 * native), round(x1 * native), round(y1 * native)],
        'source_px_per_atlas_px': round(native / s, 3),
        'alpha_mode': ALPHA_MODE[opt.matte],
        'blend_hint': BLEND_HINT[opt.matte],
        'matte': {'kind': opt.matte, **({'black': opt.black, 'gain': opt.gain} if opt.matte == 'luma' else {}),
                  **({'premultiplied_source': opt.premultiplied} if opt.matte == 'alpha' else {}),
                  **({'key': opt.key, 'key_lo': round(matte.lo, 4), 'key_hi': opt.key_hi,
                      'screen_rgb': [round(float(v), 3) for v in matte.screen_rgb]} if opt.matte == 'chroma' else {})},
        'edges_faded': [k for k, v in cut.items() if v and opt.edge_feather > 0],
        'subject_drift': drift, 'tracked': opt.track or None,
        'vram_bytes': {'rgba8': W * H * 4, 'bc3': W * H},
        'ptcl': {'flipbook_mode_0x500': 2 if loop else 4, 'cells_across_0x4D7': nx, 'cells_down_0x4D8': ny,
                 'frames_a_cell_0x504': K, 'cells_0x506': n, 'uv_scale_0x508': [1 / nx, 1 / ny],
                 'pattern_table_0x4D5': 0, 'texture': 'RGBA -> BC3 (GX2 0x33), Ptcl.set_texture'},
        'files': {'atlas': f'{opt.name}_atlas.png', 'webp': f'{opt.name}.webp', 'webm': f'{opt.name}.webm',
                  'gif': f'{opt.name}_checker.gif'},
    }
    with open(os.path.join(od, f'{opt.name}.json'), 'w') as fh_:
        json.dump(side, fh_, indent=1)
    print(f"{opt.name}: {side['playback']} src {lo}-{hi} ({kept} f) -> {n} cells {nx}x{ny} on {W}x{H} "
          f"cell {fw}x{fh} @ {play_fps:.2f} fps (K={K}); crop {side['crop_in_source_px']}; "
          f"{'seam ' + str(loop['seam_cost_vs_median_frame_step']) if loop else ''} drift {drift}"
          + (f" key_lo {matte.lo:.3f}" if opt.matte == 'chroma' else ''))
    return side


ALPHA_MODE = {
    'luma': 'straight (unpremultiplied) RGBA; alpha = max(R, G, B) of the black-levelled footage, colour = '
            'footage / alpha, so colour x alpha = the footage over black',
    'alpha': 'straight (unpremultiplied) RGBA from the source\'s own (premultiplied) alpha',
    'chroma': 'straight (unpremultiplied) RGBA; colour-difference key with the screen unmixed out and despilled',
}
BLEND_HINT = {
    'luma': 'additive (eft Add: src x alpha + dst) as shot; normal alpha blending gives the same picture over '
            'black and a less glowing one over bright backgrounds',
    'alpha': 'normal alpha blending (dark smoke must darken); the fire part could take a separate additive copy',
    'chroma': 'normal alpha blending (the dark smoke must darken what is behind it)',
}


def write_previews(od, name, cells, K, loop):
    h = max(c.shape[0] for c in cells)
    w = max(c.shape[1] for c in cells)
    ms = 1000 * K / 60
    ims = [Image.fromarray(c, 'RGBA') for c in cells]
    dur = [int(round(ms))] * len(ims)
    if not loop:
        dur[-1] += 400                               # one-shot: a pause before the preview restarts
    ims[0].save(os.path.join(od, f'{name}.webp'), save_all=True, append_images=ims[1:], duration=dur, loop=0,
                quality=88, alpha_quality=100, method=4, lossless=False)
    bg = checker(w, h)
    gif = [Image.fromarray(over(c, bg)).convert('P', palette=Image.Palette.ADAPTIVE, colors=255) for c in cells]
    gif[0].save(os.path.join(od, f'{name}_checker.gif'), save_all=True, append_images=gif[1:],
                duration=dur, loop=0, disposal=1, optimize=False)
    ew, eh = w + (w & 1), h + (h & 1)
    reps = max(1, math.ceil(6.0 / (len(cells) * K / 60))) if loop else 1
    raw = b''.join(np.pad(c, ((0, eh - c.shape[0]), (0, ew - c.shape[1]), (0, 0))).tobytes() for c in cells) * reps
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{ew}x{eh}',
                    '-framerate', f'{60}/{K}', '-i', '-', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p',
                    '-b:v', '0', '-crf', '28', '-auto-alt-ref', '0', '-row-mt', '1',
                    os.path.join(od, f'{name}.webm')], input=raw, check=True)


def write_qa(qa, name, atlas8, cells, nx, loop):
    H, W = atlas8.shape[:2]
    grey = np.full((H, W, 3), 128, np.uint8)
    add = np.clip(atlas8[..., :3] * (atlas8[..., 3:4] / 255.0) + 64, 0, 255).astype(np.uint8)
    sheet = np.concatenate([over(atlas8, checker(W, H, 16)), over(atlas8, grey), add], 1)   # normal x2, additive
    Image.fromarray(sheet).save(os.path.join(qa, f'{name}_atlas_qa.png'))
    if loop and len(cells) >= 8:
        seq = cells[-4:] + cells[:4]                 # the loop's last four cells, then its first four
        h = max(c.shape[0] for c in seq)
        strip = np.concatenate([over(c, np.full((h, c.shape[1], 3), 128, np.uint8)) for c in seq], 1)
        Image.fromarray(strip).save(os.path.join(qa, f'{name}_seam_qa.png'))


def cell_frames(atlas8, side):
    """the frames back out of an atlas, by its sidecar"""
    W, H = side['atlas_size']
    nx, ny = side['columns'], side['rows']
    fw, fh = side['frame_size_in_cell']
    cw, ch = W / nx, H / ny
    out = []
    for c in range(side['frames']):
        px = int(math.floor((c % nx) * cw + (cw - fw) / 2))
        py = int(math.floor((c // nx) * ch + (ch - fh) / 2))
        out.append(atlas8[py:py + fh, px:px + fw])
    return out


def overview(out_dir, sides, path, per=5, tile=180):
    """one row per effect: `per` frames spread over it, over a checker, with its stats"""
    label_w = 300
    rows = []
    for side in sides:
        atlas8 = np.asarray(Image.open(os.path.join(out_dir, side['name'], side['files']['atlas'])).convert('RGBA'))
        fr = cell_frames(atlas8, side)
        pick = np.linspace(0, len(fr) - 1, per).round().astype(int)
        row = Image.new('RGB', (label_w + per * (tile + 8), tile + 8), (32, 32, 32))
        d = ImageDraw.Draw(row)
        txt = [side['name'], f"{side['playback']}, {side['frames']} frames @ {side['fps']:g} fps",
               f"{side['columns']}x{side['rows']} on {side['atlas_size'][0]}x{side['atlas_size'][1]}",
               f"cell {side['frame_size_in_cell'][0]}x{side['frame_size_in_cell'][1]}, {side['matte']['kind']} matte",
               f"src frames {side['kept_range']['first_frame']}-{side['kept_range']['last_frame']}"
               + (f", seam {side['loop']['seam_cost_vs_median_frame_step']}" if side['loop'] else '')]
        for i, t in enumerate(txt):
            d.text((8, 8 + 16 * i), t, fill=(230, 230, 230) if i else (255, 200, 90))
        for j, k in enumerate(pick):
            f = fr[k]
            sc = min(tile / f.shape[1], tile / f.shape[0])
            im = Image.fromarray(f, 'RGBA').resize((max(1, int(f.shape[1] * sc)), max(1, int(f.shape[0] * sc))),
                                                  Image.Resampling.LANCZOS)
            bg = Image.fromarray(checker(tile, tile, 10))
            bg.paste(im, ((tile - im.width) // 2, (tile - im.height) // 2), im)
            row.paste(bg, (label_w + j * (tile + 8), 4))
            d.text((label_w + j * (tile + 8) + 4, 6), f'#{k}', fill=(255, 255, 255))
        rows.append(row)
    sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), (32, 32, 32))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(path)


# ------------------------------------------------------------------------------------------------ cli
def parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('input', nargs='?')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--batch')
    ap.add_argument('--only')
    ap.add_argument('--overview', help='with --batch: a contact sheet of every job (PNG path)')
    ap.add_argument('--name')
    ap.add_argument('--matte', choices=('luma', 'alpha', 'chroma'), default='luma')
    ap.add_argument('--oneshot', action='store_true')
    ap.add_argument('--range', type=lambda s: tuple(int(v) for v in s.split(':')))
    ap.add_argument('--cells', type=lambda s: tuple(int(v) for v in s.split(':')), default=(32, 64))
    ap.add_argument('--fpc', type=int, default=0, help='frames a cell at 60 fps (default from the source fps)')
    ap.add_argument('--xfade', type=int, default=6)
    ap.add_argument('--prefer-long', type=float, default=0.25)
    ap.add_argument('--vis', type=float, default=0.02)
    ap.add_argument('--sustain', type=float, default=0.8)
    ap.add_argument('--track', choices=('x', 'y', 'xy'))
    ap.add_argument('--crop-thr', type=float, default=0.03)
    ap.add_argument('--margin', type=float, default=0.03)
    ap.add_argument('--edge-feather', type=float, default=0.08,
                    help='fade width (of the crop) on sides where the effect runs off the footage')
    ap.add_argument('--bottom-cut-ok', action='store_true', help='no fade at the bottom (fire standing on it)')
    ap.add_argument('--max-side', type=int, default=1024)
    ap.add_argument('--max-area', type=int, default=1024 * 1024)
    ap.add_argument('--decode-max', type=int, default=1280, help='working resolution (longer side)')
    ap.add_argument('--black', type=float, default=0.02)
    ap.add_argument('--gain', type=float, default=1.0)
    ap.add_argument('--straight', dest='premultiplied', action='store_false')
    ap.add_argument('--key', choices=('green', 'blue'), default='green')
    ap.add_argument('--key-lo', type=float)
    ap.add_argument('--key-hi', type=float, default=0.92)
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    if args.batch:
        with open(args.batch) as fh:
            spec = json.load(fh)
        only = set(args.only.split(',')) if args.only else None
        results = []
        for job in spec['jobs']:
            if only and job['name'] not in only:
                continue
            argl = [job['input'], spec['out']]
            for k, v in job.items():
                if k == 'input':
                    continue
                flag = '--' + k.replace('_', '-')
                if v is True:
                    argl.append(flag)
                elif v is False or v is None:
                    continue
                elif isinstance(v, (list, tuple)):
                    argl += [flag, ':'.join(str(x) for x in v)]
                else:
                    argl += [flag, str(v)]
            results.append(run_job(ap.parse_args(argl)))
        if args.overview:
            sides = []
            for job in spec['jobs']:
                with open(os.path.join(spec['out'], job['name'], job['name'] + '.json')) as fh:
                    sides.append(json.load(fh))
            overview(spec['out'], sides, args.overview)
        return results
    if not (args.input and args.out and args.name):
        ap.error('CLIP OUT_DIR --name NAME (or --batch jobs.json)')
    return [run_job(args)]


if __name__ == '__main__':
    main()
