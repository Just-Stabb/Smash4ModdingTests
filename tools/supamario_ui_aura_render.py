#!/usr/bin/env python3
"""Supamario's Ultra Instinct look after the burst (README "Ultra Instinct v4" / v5 / v6): before / after render of the
MSC's aura AS THE GAME RUNS IT, fx_render's Smash 4 side on a sandy background; + the haze's distortion preview
(fx_render doesn't draw the distortion pass: its particles from fx_render.simulate, each a sprite of the emitter's
distortion map (R / G - 0.5) x alpha x size, warping the background); v6: + the glow (Outline_Set's rim inside a
stand-in silhouette, Outline_Shell's band outside it, approximated: no model is drawn).

  python3 tools/supamario_ui_aura_render.py BEFORE_OUT AFTER_OUT OUT.png [--before-mode MODE] [--after-mode MODE]
      (build output dirs of supamario_ui_build.py)

Modes (what the game shows, by how ui_aura renews the aura):
  v5      v1-v5's renewal: the hip / head / feet killed AT ONCE and made again every 30 frames, so no sprite gets past
          29 frames: drawn at 8, 16, 24, 29 frames after a renewal (the faint puffs of the user's v5 clip)
  steady  v6's renewal (the old ones faded, new ones made the same frame: the emission never stops): the seven parts
          (hip, chest, head, feet, hands) at 150-180 frames, the continuous state; with the glow
  preview v4 / v5's own preview (frames 60-81 of one request: a state the v5 game never reached)
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import ptcl
import fx_render as R
import supamario_ui_build as B
from PIL import Image
BG = (0.55, 0.45, 0.32)
HIP, HEAD, CHEST = 6.5, 12.5, 9.0
MODES = {'v5': [8, 16, 24, 29], 'steady': [150, 160, 170, 180], 'preview': [60, 67, 74, 81]}
PPU = 12.0
BODY_RGB = (0.62, 0.62, 0.70)      # the stand-in silhouette (silver-blue clothes / skin: approximated)
SHELL_PX = 5                       # Outline_Shell's 3 px of 1280 x 720 at this canvas's scale (Mario ~180 px tall here,
                                   # ~110 px in a typical battle shot)
RIM_PX = 4
K = 1.0                            # v9: the game's encoding scale on Outline_Shell's colour (--k; the v7 clip: >= 2.2)


def calls(mode):
    s = B.SCALE
    four = [('aura_hip', (0.0, HIP, 0.0), s), ('aura_head', (0.0, HEAD + 0.2 * B.METRE, 0.0), s),
            ('aura_foot', (0.0, 0.6, 1.2), 0.8 * s), ('aura_foot', (0.0, 0.6, -1.2), 0.8 * s)]
    if mode == 'steady':
        return four + [('aura_chest', (0.0, CHEST, 0.0), s), ('aura_hand', (0.0, 6.8, 4.2), 0.65 * s),
                       ('aura_hand', (0.0, 6.8, -4.2), 0.65 * s)]
    return four


def silhouette(c):
    """a stand-in body mask (screen x = Z, y = Y): torso, head, legs, arms as ellipses / capsules"""
    h, w = c.h, c.w
    yy, xx = np.mgrid[0:h, 0:w]
    X = xx / c.ppu + c.x0
    Y = c.y1 - yy / c.ppu
    m = ((X / 3.0) ** 2 + ((Y - 8.0) / 3.4) ** 2) <= 1
    m |= (X ** 2 + (Y - 12.9) ** 2) <= 3.0 ** 2

    def cap(a, b, r):
        a, b = np.array(a), np.array(b)
        d = b - a
        t = (((X - a[0]) * d[0] + (Y - a[1]) * d[1]) / float(d @ d)).clip(0, 1)
        return (X - a[0] - t * d[0]) ** 2 + (Y - a[1] - t * d[1]) ** 2 <= r * r
    for sx in (-1, 1):
        m |= cap((1.5 * sx, 5.0), (1.9 * sx, 0.9), 1.4)
        m |= cap((3.0 * sx, 10.0), (4.2 * sx, 6.8), 1.0)
    return m


def grow(m, n):
    out = m.copy()
    for _ in range(n):
        g = out.copy()
        g[1:] |= out[:-1]
        g[:-1] |= out[1:]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        out = g
    return out


def draw_glow(c):
    """the body (BODY_RGB), Outline_Set's rim (GLOW_RIM: added inside, falling off over RIM_PX from the edge, x Alpha /
    255 / 2 + the Tint over the body) and Outline_Shell's band (GLOW_SHELL: SHELL_PX outside, added x Alpha / 255)"""
    m = silhouette(c)
    rim_rgb = np.array(B.GLOW_RIM_RGB) / 255.0
    body = np.array(BODY_RGB) * (1 - B.GLOW_RIM_TINT / 255.0) + rim_rgb * (B.GLOW_RIM_TINT / 255.0)
    c.rgb[m] = body
    inner = m.copy()
    for k in range(RIM_PX):
        nxt = ~grow(~inner, 1) & m
        ring = inner & ~nxt
        c.rgb[ring] += rim_rgb * min(B.GLOW_RIM_A / 255.0, 4.0) * 0.5 * (1 - k / float(RIM_PX))
        inner = nxt
    band = grow(m, max(1, int(round(SHELL_PX * B.GLOW_SHELL_W / 3.0)))) & ~m
    col = np.minimum(1.0, K * np.array(B.GLOW_SHELL_RGB) / 255.0)
    a = B.GLOW_SHELL_A / 255.0
    if getattr(B, 'GLOW_SHELL_BLEND', 1) == 0:      # v9: drawn over
        c.rgb[band] = c.rgb[band] * (1 - a) + col * a
    else:
        c.rgb[band] += col * a
    return m


def refracts(p, raw):
    """v9: an emitter whose program reads the frame buffer (the fireball's refraction: draws the picture behind it,
    bent; fx_render draws it as colour)"""
    return b'frameBufferTexture' in bytes(p.shader_binary(p.field(raw, 'shader_index')))


def render(out, mode='steady', haze_px=6.0, glow=None):
    global BG
    frames = MODES[mode]
    glow = (mode == 'steady') if glow is None else glow
    R.BG = np.array(BG, float)
    R._s4_programs.clear()
    R._s4_static.clear()
    d = os.path.join(out, 'fighter/supamario/effect/supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    cl = calls(mode)
    sets = {k: p.find_set('PtcSupamarioUi' + [x for x in B.FX if x[0] == k][0][2][:-4]) for k, _x, _s in cl}
    canv = {fr: R.Canvas(-15, 15, -3, 25, PPU) for fr in frames}
    masks = {}
    if glow:
        for fr in frames:
            masks[fr] = draw_glow(canv[fr])
    offs = {fr: np.zeros((canv[fr].h, canv[fr].w, 2)) for fr in frames}
    programs = {}
    for n, (key, xyz, size) in enumerate(cl):
        ems = R.s4_emitters(p, sets[key], programs)
        cm = R.call_matrix(xyz, (0, 0, 0), size)
        for k, em in enumerate(ems):
            sim = R.simulate(em, (0, cm, size, None), frames, seed=n * 10 + k + 1)
            raw = p.sets[sets[key]]['emitters'][k]['data']
            is_haze = ('distortion pass (not drawn)' in getattr(em, 'notes', ()) or em.name == 'UiHaze' or
                       refracts(p, raw))
            for fr in frames:
                if not sim[fr]:
                    continue
                if is_haze:
                    raw = p.sets[sets[key]]['emitters'][k]['data']
                    tex = np.asarray(p.decode_texture(raw, 0)).astype(float) / 255.0
                    th, tw = tex.shape[:2]
                    c = canv[fr]
                    for q in sim[fr]:
                        pos, sz, alpha = q[0], q[3], q[5]
                        s = float(np.mean(sz)) if np.ndim(sz) else float(sz)
                        cx, cy = c.px(pos[2], pos[1])
                        r = max(2, int(s * c.ppu / 2))
                        ys, xs = np.mgrid[-r:r, -r:r]
                        u = ((xs + r) * tw // (2 * r)).clip(0, tw - 1)
                        v = ((ys + r) * th // (2 * r)).clip(0, th - 1)
                        dxy = (tex[v, u, :2] - 0.5) * float(alpha)
                        yy, xx = ys + cy, xs + cx
                        ok = (yy >= 0) & (yy < c.h) & (xx >= 0) & (xx < c.w)
                        offs[fr][yy[ok], xx[ok]] += dxy[ok] * haze_px * 2
                    continue
                m = cm @ R.emitter_matrix(em, fr)
                if em.s4 is not None and R.draw_s4(canv[fr], em, sim[fr], m, float(fr)):
                    continue
                R.draw(canv[fr], em, sim[fr], cm)
    ims = []
    for fr in frames:
        img = np.clip(canv[fr].rgb, 0, 1)
        o = offs[fr]
        if np.abs(o).max() > 0:
            h, w = img.shape[:2]
            yy, xx = np.mgrid[0:h, 0:w]
            sx = (xx + o[..., 0]).round().astype(int).clip(0, w - 1)
            sy = (yy + o[..., 1]).round().astype(int).clip(0, h - 1)
            # the distortion bends the picture behind (here the background's grid + a checker)
            bgc = np.tile(np.array(BG), (h, w, 1))
            chk = (((xx // 12) + (yy // 12)) % 2 == 0)
            bgc[chk] *= 0.85
            warped = bgc[sy, sx]
            keep = np.abs(canv[fr].rgb - np.array(BG)).sum(axis=2, keepdims=True) > 0.02
            if fr in masks:
                keep |= masks[fr][..., None]
            img = np.where(keep, img, warped)
        ims.append((img * 255).astype(np.uint8))
    return np.concatenate(ims, axis=1), offs


def added_light(img, mode):
    """the mean light the aura adds over the background, per frame (the brightness the frames compare by)"""
    a = img.astype(float) / 255.0
    d = np.clip(a - np.array(R.BG), 0, None).sum(axis=2)
    w = img.shape[1] // len(MODES[mode])
    return [round(float(d[:, i * w:(i + 1) * w].mean()), 4) for i in range(len(MODES[mode]))]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('out')
    ap.add_argument('--before-mode', default='v5', choices=sorted(MODES))
    ap.add_argument('--after-mode', default='steady', choices=sorted(MODES))
    ap.add_argument('--bg', help='the background r,g,b (0-1; default the sand %s; e.g. 0.10,0.08,0.22 for a dark stage '
                    'like the user\'s v5 clip)' % (BG,))
    ap.add_argument('--k', type=float, default=1.0, help='v9: the encoding scale on Outline_Shell\'s colour (1 = as '
                    'given; the v7 clip shows >= 2.2)')
    a = ap.parse_args()
    K = a.k
    if a.bg:
        BG = tuple(float(x) for x in a.bg.split(','))
    ia, oa = render(a.before, a.before_mode)
    ib, ob = render(a.after, a.after_mode, glow=False)
    ic, _oc = render(a.after, a.after_mode)
    Image.fromarray(np.concatenate([ia, ib, ic], axis=0)).save(a.out)
    print('rows: before (%s), after (%s, the aura alone), after with the glow' % (a.before_mode, a.after_mode))
    print('added light: before %s, after %s' % (added_light(ia, a.before_mode), added_light(ib, a.after_mode)))
    print('haze offsets max px: before %.1f after %.1f' % (max(np.abs(o).max() for o in oa.values()),
                                                           max(np.abs(o).max() for o in ob.values())))
