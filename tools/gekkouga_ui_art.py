#!/usr/bin/env python3
"""Greninja's panel radar and smash-charge waveform (fighters/gekkouga/README.md "UI radar / waveform v1"): the art
from the user's radar.webp (650 x 650: a green radar) and parabeetle_icon.webp (268 x 163 RGBA), the layer / frame lists
the damage panel gets (tools/gekkouga_gauge_flx.py build(ui=...)) and the executable drives (tools/gekkouga_clone_cave.py
gk_ui), previews and mock-ups.

  python3 tools/gekkouga_ui_art.py extract RADAR.webp BEETLE.webp OUT_DIR    # the radar's 3 layers + the 60 wave frames
  python3 tools/gekkouga_ui_art.py preview ART_DIR OUT_DIR [INGAME.png]      # radar_ready / radar_cooldown / waveform
                                                                              # gifs (+ the mock-up over a screenshot)

The radar (256 x 256 each, centred, drawn ring -> beetle -> sweep):
- ring (static): the source's bright ring, its thin inner ring, the 4 inner rings, the 12 spokes and the 36 inner ticks,
  REBUILT at the source's measured radii / colours (its centre (325.8, 325.7); radii 47 / 95 / 142.5 / 191.5 inner,
  228.5 thin, 237.5 - 245.5 bright) with the line widths raised for the panel's size; the grid, the dark backdrop (and its
  map), the compass numbers and the outer ticks (r 256 - 272) left out: transparent outside the ring and between lines;
- sweep (turned by the executable about its centre, + clockwise as the source's): the source's wedge rebuilt: its
  leading edge at 12 o'clock, the trail counter-clockwise behind it fading as (1 - t / 180)^1.5 (measured: 1.0 / 0.61 /
  0.35 / 0.15 at 10 / 50 / 90 / 130 degrees), green (0, 230, 0) brighter outward, inside the thin ring;
- beetle: the icon centred, its farthest opaque pixel inside the third inner ring (r 135 of the source's 142.5), tinted
  28 % toward the radar's green with faint scanlines, alpha 0.9 (it reads as a blip on the screen; the sweep passes over
  it).

The waveform (256 x 48 cells): WAVE_LEVELS amplitudes x WAVE_PHASES phases of a tapered two-harmonic wave in white (the
executable tints it the round gauge's water blue), then RAINBOW_FRAMES pre-coloured frames at full amplitude: the hue
along the wave and moving with it, a white-hot core and a wide rainbow glow.
"""
import colorsys
import math
import os
import sys

import numpy as np
from PIL import Image

RSIZE = 256                       # the radar's cells
SS = 4                            # supersampling
SRC_CENTRE = (325.78, 325.72)     # radar.webp's centre (a circle fit to the bright ring)
SRC_RING = (237.5, 245.5)         # its bright ring (inner, outer edge), colour (68, 255, 1)
SRC_THIN = 228.5                  # its thin ring, (65, 205, 45)
SRC_INNER = (47.0, 95.0, 142.5, 191.5)   # its inner rings
SRC_TICKS = (216.0, 227.0)        # its inner ticks (every 10 degrees)
SCALE = 121.0 / SRC_RING[1]       # source px -> cell px (the bright ring's outer edge at 121: 7 px for its glow)
RING_RGB = (68, 255, 1)
THIN_RGB = (65, 205, 45)
LINE_RGB = (40, 205, 40)
SWEEP_RGB = (20, 235, 20)
EDGE_RGB = (150, 255, 150)
SWEEP_ALPHA = 0.72
SWEEP_TRAIL = 180.0               # degrees behind the leading edge to nothing
BEETLE_R = 135.0                  # the beetle's farthest opaque pixel (source px)
BEETLE_TINT = 0.28
BEETLE_ALPHA = 0.9
LAYERS = ('ring', 'beetle', 'sweep')   # bottom first (the executable's GK names: gk_rring_mc ... )

WAVE_W, WAVE_H = 256, 48
WAVE_LEVELS = 6                   # amplitude levels below full (charge x 6 / 120)
WAVE_PHASES = 6                   # phases a level (1/6 of a wavelength each)
RAINBOW_FRAMES = 24               # full: phase 1/6 a frame (4 wavelengths a loop), hue 15 degrees a frame
WAVE_CYCLES = 3.0                 # wavelengths across
WAVE_AMP = (1.5, 16.0)            # level 0 / the top level's amplitude (px of the 48)
RAINBOW_AMP = 17.0
WAVE_FRAMES = WAVE_LEVELS * WAVE_PHASES + RAINBOW_FRAMES
CALM_TINT = (25, 90, 100)         # the executable's calm colour (percent), the round gauge's charge cyan


def _down(a):
    """(H*SS, W*SS[, C]) -> box-filtered (H, W[, C])"""
    h, w = a.shape[0] // SS, a.shape[1] // SS
    return a.reshape(h, SS, w, SS, *a.shape[2:]).mean(axis=(1, 3))


def _down_rgba(d):
    """a supersampled straight-alpha RGBA box-filtered through premultiplied colour"""
    pm = d.copy()
    pm[..., :3] *= pm[..., 3:]
    pm = _down(pm)
    a = pm[..., 3:]
    pm[..., :3] = np.where(a > 0, pm[..., :3] / np.maximum(a, 1e-6), 0)
    return pm


def _polar(n):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    c = n / 2.0
    dx, dy = xx + 0.5 - c, yy + 0.5 - c
    r = np.hypot(dx, dy)
    ang = (np.degrees(np.arctan2(dx, -dy)) + 360.0) % 360.0     # clockwise from 12 o'clock
    return r, ang


def _band(r, r0, r1):
    """coverage of r0 <= r <= r1 (antialiased by the supersampling)"""
    return ((r >= r0) & (r <= r1)).astype(np.float32)


def _over(dst, rgb, a):
    """straight-alpha 'over' of a colour with coverage a onto dst (RGBA float 0-1)"""
    rgb = np.asarray(rgb, np.float32) / 255.0
    da = dst[..., 3]
    oa = a + da * (1 - a)
    for k in range(3):
        dst[..., k] = np.where(oa > 0, (rgb[k] * a + dst[..., k] * da * (1 - a)) / np.maximum(oa, 1e-6), dst[..., k])
    dst[..., 3] = oa


def _blur(a, sigma):
    """separable gaussian"""
    k = int(math.ceil(3 * sigma))
    x = np.arange(-k, k + 1, dtype=np.float32)
    g = np.exp(-x * x / (2 * sigma * sigma))
    g /= g.sum()
    p = np.pad(a, [(k, k), (k, k)] + [(0, 0)] * (a.ndim - 2), mode='constant')
    p = np.apply_along_axis(lambda v: np.convolve(v, g, mode='valid'), 0, p)
    p = np.apply_along_axis(lambda v: np.convolve(v, g, mode='valid'), 1, p)
    return p


def _to_img(d):
    """RGBA float 0-1 -> uint8, the colour of see-through pixels bled from their neighbours (no dark fringes)"""
    out = np.clip(d * 255.0 + 0.5, 0, 255).astype(np.uint8)
    a = d[..., 3]
    if (a > 0).any():
        w = _blur(a, 3.0)[..., None]
        bled = _blur(d[..., :3] * a[..., None], 3.0) / np.maximum(w, 1e-6)
        rgb = np.where(a[..., None] > 0.02, d[..., :3], bled)
        out[..., :3] = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return out


def radar_ring():
    n = RSIZE * SS
    r, ang = _polar(n)
    r = r / SS                                       # cell px
    s = SCALE
    d = np.zeros((n, n, 4), np.float32)
    # the spokes (every 30 degrees, centre to the thin ring) and the 36 inner ticks (every 10 degrees)
    dist = np.abs(((ang + 15.0) % 30.0) - 15.0) * math.pi / 180.0 * r      # px from the nearest spoke
    _over(d, LINE_RGB, ((dist <= 0.8) & (r <= SRC_THIN * s)).astype(np.float32) * 0.5)
    tdist = np.abs(((ang + 5.0) % 10.0) - 5.0) * math.pi / 180.0 * r
    _over(d, LINE_RGB, ((tdist <= 0.8) & (r >= SRC_TICKS[0] * s) & (r <= SRC_TICKS[1] * s)).astype(np.float32) * 0.55)
    for rc in SRC_INNER:
        _over(d, LINE_RGB, _band(r, rc * s - 0.9, rc * s + 0.9) * 0.7)
    _over(d, THIN_RGB, _band(r, SRC_THIN * s - 0.8, SRC_THIN * s + 0.8) * 0.92)
    d = _down_rgba(d)
    # the bright ring and its glow (at cell resolution after the line work: the glow blurred from it)
    core = _down(_band(r, SRC_RING[0] * s, SRC_RING[1] * s))
    glow = np.clip(_blur(core, 2.2) * 0.75, 0, 1)
    _over(d, RING_RGB, glow * (1 - core))
    _over(d, RING_RGB, core)
    return _to_img(d)


def radar_sweep():
    n = RSIZE * SS
    r, ang = _polar(n)
    r = r / SS
    rmax = SRC_THIN * SCALE - 0.8
    t = (360.0 - ang) % 360.0                       # degrees behind the leading edge (12 o'clock), counter-clockwise
    f = np.clip(1.0 - t / SWEEP_TRAIL, 0, 1) ** 1.5
    a = SWEEP_ALPHA * f * (0.78 + 0.22 * r / rmax) * (r <= rmax)
    d = np.zeros((n, n, 4), np.float32)
    _over(d, SWEEP_RGB, a.astype(np.float32))
    edge = (np.minimum(t, 360.0 - t) * math.pi / 180.0 * r <= 0.9) & (r <= rmax) & (t < 90)
    _over(d, EDGE_RGB, edge.astype(np.float32) * 0.95)
    return _to_img(_down_rgba(d))


def radar_beetle(icon):
    im = np.asarray(Image.open(icon).convert('RGBA')).astype(np.float32) / 255.0
    a = im[..., 3]
    ys, xs = np.where(a > 0.1)
    im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = im.shape[:2]
    a = im[..., 3]
    yy, xx = np.mgrid[0:h, 0:w]
    far = np.hypot(xx + 0.5 - w / 2.0, yy + 0.5 - h / 2.0)[a > 0.1].max()
    k = BEETLE_R * SCALE / far                      # its farthest opaque pixel on the radius
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    pm = im.copy()
    pm[..., :3] *= pm[..., 3:]                       # premultiplied for the resize
    sm = np.asarray(Image.fromarray((pm * 255).astype(np.uint8), 'RGBA').resize((nw, nh), Image.LANCZOS)).astype(np.float32) / 255.0
    al = sm[..., 3]
    rgb = np.where(al[..., None] > 0, sm[..., :3] / np.maximum(al[..., None], 1e-6), 0)
    lum = (0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2])[..., None]
    green = lum * np.array(RING_RGB, np.float32) / 255.0 * 1.15
    rgb = np.clip(rgb * (1 - BEETLE_TINT) + green * BEETLE_TINT, 0, 1)
    scan = np.where((np.arange(nh) % 3) == 2, 0.8, 1.0).astype(np.float32)[:, None]
    al = np.clip(al * BEETLE_ALPHA * scan, 0, 1)
    d = np.zeros((RSIZE, RSIZE, 4), np.float32)
    x0, y0 = (RSIZE - nw) // 2, (RSIZE - nh) // 2
    d[y0:y0 + nh, x0:x0 + nw, :3] = rgb
    d[y0:y0 + nh, x0:x0 + nw, 3] = al
    return _to_img(d)


def wave_y(u, amp, phase, harm=0.3):
    """the wave's height (px, + down) at u 0-1 across, taper sin(pi u)^0.8"""
    env = np.clip(np.sin(np.pi * np.clip(u, 0, 1)), 0, 1) ** 0.8
    v = np.sin(2 * np.pi * (WAVE_CYCLES * u - phase)) * (1 - harm) + \
        np.sin(2 * np.pi * (2 * WAVE_CYCLES * u - 2 * phase) + 0.9) * harm
    return amp * env * v


def _wave_dist(amp, phase, harm):
    """per (supersampled) pixel: the distance in cell px to the wave's line, and u"""
    h, w = WAVE_H * SS, WAVE_W * SS
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx + 0.5) / SS
    y = (yy + 0.5) / SS
    x0, x1 = 8.0, WAVE_W - 8.0
    u = (x - x0) / (x1 - x0)
    wy = WAVE_H / 2.0 + wave_y(u, amp, phase, harm)
    du = 1e-3
    slope = (wave_y(u + du, amp, phase, harm) - wave_y(u - du, amp, phase, harm)) / (2 * du * (x1 - x0))
    dist = np.abs(y - wy) / np.sqrt(1 + slope * slope)
    inside = (u >= 0) & (u <= 1)
    return np.where(inside, dist, 99.0), u, y


def wave_frame(level=None, phase=0.0, rainbow=None):
    """a white frame (level 0 - WAVE_LEVELS - 1) or a rainbow one (rainbow = the frame 0 - RAINBOW_FRAMES - 1)"""
    if rainbow is None:
        amp = WAVE_AMP[0] + (WAVE_AMP[1] - WAVE_AMP[0]) * level / (WAVE_LEVELS - 1)
        dist, u, y = _wave_dist(amp, phase, 0.3)
        core = _down((dist <= 2.1).astype(np.float32))
        track = _down(((np.abs(y - WAVE_H / 2.0) <= 0.5) & (u >= 0) & (u <= 1)).astype(np.float32)) * 0.2
        glow = np.clip(_blur(core, 3.0) * 1.1, 0, 1) * 0.55
        d = np.zeros((WAVE_H, WAVE_W, 4), np.float32)
        _over(d, (255, 255, 255), track)
        _over(d, (255, 255, 255), glow * (1 - core))
        _over(d, (255, 255, 255), core)
        return _to_img(d)
    k = rainbow
    phase = (k / float(WAVE_PHASES)) % 1.0
    dist, u, _y = _wave_dist(RAINBOW_AMP, phase, 0.38)
    core = _down((dist <= 2.4).astype(np.float32))
    uu = _down(np.clip(u, 0, 1))
    hue = ((uu * 360.0 - 15.0 * k) % 360.0) / 360.0
    rgb = np.zeros((WAVE_H, WAVE_W, 3), np.float32)
    for i in range(WAVE_H):
        for j in range(WAVE_W):
            rgb[i, j] = colorsys.hsv_to_rgb(float(hue[i, j]), 0.85, 1.0)
    glow = np.clip(_blur(core, 4.0) * 1.6, 0, 1) * 0.85
    d = np.zeros((WAVE_H, WAVE_W, 4), np.float32)
    d[..., :3] = rgb
    d[..., 3] = glow * (1 - core)
    core_rgb = rgb * 0.6 + 0.4
    a = core
    oa = a + d[..., 3] * (1 - a)
    d[..., :3] = (core_rgb * a[..., None] + d[..., :3] * (d[..., 3] * (1 - a))[..., None]) / np.maximum(oa, 1e-6)[..., None]
    d[..., 3] = oa
    return _to_img(d)


def wave_frames():
    out = []
    for lv in range(WAVE_LEVELS):
        for p in range(WAVE_PHASES):
            out.append(wave_frame(lv, p / float(WAVE_PHASES)))
    for k in range(RAINBOW_FRAMES):
        out.append(wave_frame(rainbow=k))
    return out


def wave_index(charge, t, slow_shift=3):
    """the executable's frame (0-based) for a charge 0 - 120 at its frame count t (gk_ui)"""
    if charge >= 120:
        return WAVE_LEVELS * WAVE_PHASES + t % RAINBOW_FRAMES
    lv = charge * WAVE_LEVELS // 120
    return lv * WAVE_PHASES + (t >> slow_shift) % WAVE_PHASES


def extract(radar, icon, out):
    os.makedirs(out, exist_ok=True)
    Image.fromarray(radar_ring(), 'RGBA').save(os.path.join(out, 'radar_ring.png'))
    Image.fromarray(radar_sweep(), 'RGBA').save(os.path.join(out, 'radar_sweep.png'))
    Image.fromarray(radar_beetle(icon), 'RGBA').save(os.path.join(out, 'radar_beetle.png'))
    for i, fr in enumerate(wave_frames()):
        Image.fromarray(fr, 'RGBA').save(os.path.join(out, 'wave_%02d.png' % i))


def load(art):
    """{name: RGBA uint8}: radar_ring / radar_beetle / radar_sweep, wave_00 ..."""
    out = {n: np.asarray(Image.open(os.path.join(art, 'radar_%s.png' % n)).convert('RGBA')) for n in LAYERS}
    out['wave'] = [np.asarray(Image.open(os.path.join(art, 'wave_%02d.png' % i)).convert('RGBA'))
                   for i in range(WAVE_FRAMES)]
    return out


def _put(canvas, img, cx, cy, size, angle=0.0, mul=(100, 100, 100, 100)):
    """img (RGBA uint8) scaled to size (w, h) px, turned clockwise by angle, its colour x mul (percent), centred at cx, cy"""
    im = Image.fromarray(img, 'RGBA')
    w, h = max(1, int(round(size[0]))), max(1, int(round(size[1])))
    im = im.resize((w, h), Image.LANCZOS)
    if angle:
        im = im.rotate(-angle, resample=Image.BICUBIC, expand=False)
    a = np.asarray(im).astype(np.float32)
    for k, m in enumerate((mul[1], mul[2], mul[3], mul[0])):
        a[..., k] *= m / 100.0
    canvas.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'),
                           (int(round(cx - w / 2.0)), int(round(cy - h / 2.0))))


def compose_radar(L, angle, beetle, px=160, bg=(14, 18, 26, 255)):
    c = Image.new('RGBA', (px, px), bg)
    _put(c, L['ring'], px / 2, px / 2, (px, px))
    if beetle:
        _put(c, L['beetle'], px / 2, px / 2, (px, px))
    _put(c, L['sweep'], px / 2, px / 2, (px, px), angle)
    return c


def compose_wave(L, charge, t, scale=1.0, bg=(14, 18, 26, 255)):
    c = Image.new('RGBA', (int(WAVE_W * scale), int(WAVE_H * scale)), bg)
    i = wave_index(charge, t)
    mul = (100, 100, 100, 100) if charge >= 120 else (100,) + CALM_TINT
    _put(c, L['wave'][i], c.width / 2, c.height / 2, (WAVE_W * scale, WAVE_H * scale), mul=mul)
    return c


def _gif(frames, path, ms):
    pal = [f.convert('RGB').quantize(colors=255, method=Image.Quantize.MEDIANCUT) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=False)


def preview(art, out, speed=3.6, cd_div=4, ingame=None, place=None):
    """radar_ready.gif (speed degrees a frame, the beetle shown), radar_cooldown.gif (speed / cd_div, no beetle),
    waveform_charging.gif (0 -> 119 over 2 s, then held), waveform_full.gif (full: rainbow, a frame a frame)"""
    L = load(art)
    os.makedirs(out, exist_ok=True)
    fr = [compose_radar(L, (speed * t) % 360, True) for t in range(0, int(360 / speed), 2)]
    _gif(fr, os.path.join(out, 'radar_ready.gif'), 33)
    slow = speed / cd_div
    fr = [compose_radar(L, (slow * t) % 360, False) for t in range(0, int(360 / slow), 8)]
    _gif(fr, os.path.join(out, 'radar_cooldown.gif'), 33)
    fr = [compose_wave(L, min(119, t), t, 2.0) for t in range(0, 240, 2)]
    _gif(fr, os.path.join(out, 'waveform_charging.gif'), 33)
    fr = [compose_wave(L, 120, t, 2.0) for t in range(48)]
    _gif(fr, os.path.join(out, 'waveform_full.gif'), 17)


# the user's in-game screenshot (round_gauge_ingame.webp, 1434 x 322: Greninja's panel at the left, 2 players: panel
# sprite 3): panel units -> its pixels, measured on the portrait hexagons (Donkey Kong's 205 x 225 px for the 116 x 122
# hexagon: 1.8 px a unit; Greninja's hexagon's right side at x 172, its top point at y 50)
SHOT_SCALE = 1.8
SHOT_ORIGIN = (172.0 + 46.0 * 1.8, 50.0 + 58.0 * 1.8)     # where panel (0, 0) lands
SHOT_PAD = 40                                            # dark columns added at the left (the shot cuts the hexagon)


def shot_xy(x, y):
    return SHOT_PAD + SHOT_ORIGIN[0] + x * SHOT_SCALE, SHOT_ORIGIN[1] + y * SHOT_SCALE


def mockup_shot(art, shot, places, angle=40.0, beetle=True, charge=70, t=0):
    """the radar and the waveform drawn over the screenshot at panel sprite 3's places (places: gekkouga_gauge_flx
    ui_places()[3]); returns the left 640 px"""
    L = load(art)
    im = Image.open(shot).convert('RGBA')
    c = Image.new('RGBA', (im.width + SHOT_PAD, im.height), (20, 20, 24, 255))
    c.alpha_composite(im, (SHOT_PAD, 0))
    x, y, sc = places['radar']
    px, py = shot_xy(x, y)
    size = RSIZE * sc * SHOT_SCALE
    _put(c, L['ring'], px, py, (size, size))
    if beetle:
        _put(c, L['beetle'], px, py, (size, size))
    _put(c, L['sweep'], px, py, (size, size), angle)
    x, y, sc = places['wave']
    px, py = shot_xy(x, y)
    i = wave_index(charge, t)
    mul = (100, 100, 100, 100) if charge >= 120 else (100,) + CALM_TINT
    _put(c, L['wave'][i], px, py, (WAVE_W * sc * SHOT_SCALE, WAVE_H * sc * SHOT_SCALE), mul=mul)
    return c.crop((0, 0, 640, c.height))


# beetle safety / radar v2: the user's in-game screenshot of the v1 panel (radar_ingame.png, 233 x 161: Greninja's 1 - 4
# player panel): units -> pixels measured on its v1 radar (the bright ring's outer edge, 121 / 256 of the radar's 58.6 units:
# 36.5 px across, centred at (100.0, 48.5): 0.66 px a unit)
SHOT2_RADAR = (100.0, 48.5)       # the v1 radar's centre in the shot (px)
SHOT2_RING = 36.5                 # its bright ring's outer diameter (px)


def _fill_disc(a, cx, cy, r, keep):
    """the pixels in the disc (cx, cy, r) not in keep painted from their surroundings (repeated 4-neighbour averaging)"""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    hole = ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r) & ~keep
    out = a.astype(np.float32).copy()
    out[hole] = 0
    known = ~hole
    for _ in range(400):
        acc = np.zeros_like(out)
        n = np.zeros(out.shape[:2], np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(out, dy, 0), dx, 1)
            kn = np.roll(np.roll(known, dy, 0), dx, 1)
            acc += sh * kn[..., None]
            n += kn
        upd = hole & (n > 0)
        out[upd] = acc[upd] / n[upd][:, None]
        known = known | upd
    return np.clip(out, 0, 255).astype(np.uint8)


def digits_mask(a):
    """the percent digits in the shot (white / grey fill, low saturation, bright) and their black outline (2 px round them):
    the panel draws them over the radar"""
    f = a[..., :3].astype(int)
    sat = f.max(axis=2) - f.min(axis=2)
    m = (f.mean(axis=2) > 125) & (sat < 40)
    m[:, :95] = False                              # (the portrait's highlights left of the digits)
    out = m.copy()
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def mockup_v2(art, shot, place1, place2, angle=40.0, beetle=True, charge=70, t=0, k=4):
    """the radar at its v2 place (place2) drawn over the user's in-game shot of the v1 panel (its v1 radar at place1 painted
    out), under the percent digits as the panel draws it; the waveform as v1. k: upscale. -> image"""
    L = load(art)
    im = np.asarray(Image.open(shot).convert('RGBA'))
    s = SHOT2_RING / (RSIZE * place1['radar'][2] * 242.0 / 256.0)     # px a unit
    x1, y1, sc1 = place1['radar']
    dig = digits_mask(im)
    clean = _fill_disc(im, SHOT2_RADAR[0], SHOT2_RADAR[1], SHOT2_RING / 2 + 2.5, dig)
    base = Image.fromarray(clean, 'RGBA').resize((im.shape[1] * k, im.shape[0] * k), Image.BICUBIC)
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    x2, y2, sc2 = place2['radar']
    cx = (SHOT2_RADAR[0] + (x2 - x1) * s) * k
    cy = (SHOT2_RADAR[1] + (y2 - y1) * s) * k
    size = RSIZE * sc2 * s * k
    _put(layer, L['ring'], cx, cy, (size, size))
    if beetle:
        _put(layer, L['beetle'], cx, cy, (size, size))
    _put(layer, L['sweep'], cx, cy, (size, size), angle)
    over = np.asarray(Image.fromarray(dig.astype(np.uint8) * 255).resize(base.size, Image.BILINEAR)).astype(np.float32) / 255
    la = np.asarray(layer).astype(np.float32)
    la[..., 3] *= 1.0 - over                       # under the digits
    out = base.copy()
    out.alpha_composite(Image.fromarray(la.astype(np.uint8), 'RGBA'))
    return out, dict(scale=s, centre=(cx / k, cy / k), diameter_px=size / k)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'extract' and len(a) == 4:
        extract(a[1], a[2], a[3])
    elif a and a[0] == 'preview' and len(a) >= 3:
        preview(a[1], a[2])
    else:
        sys.exit(__doc__)
