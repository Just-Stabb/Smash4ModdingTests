#!/usr/bin/env python3
"""Supamario's Ultra Instinct aura (README "Ultra Instinct v4", v5's aura): before / after render of the MSC's aura (hip, head, both feet: as ui_aura places them), fx_render's
Smash 4 side on a sandy background; + the haze's distortion preview (fx_render doesn't draw the distortion pass:
its particles from fx_render.simulate, each a sprite of the emitter's distortion map (R / G - 0.5) x alpha x size,
warping the background)

  python3 tools/supamario_ui_aura_render.py BEFORE_OUT AFTER_OUT OUT.png   (build output dirs of supamario_ui_build.py)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import ptcl, efc
import fx_render as R
import supamario_ui_build as B
from PIL import Image
BG = (0.55, 0.45, 0.32)
FRAMES = [60, 67, 74, 81]
HIP, HEAD = 6.5, 12.5


def ids(out):
    import json
    return json.load(open(os.path.join(out, 'supamario_ui.json')))['fx_ids'] if os.path.exists(os.path.join(out, 'supamario_ui.json')) else None


def render(out, haze_px=6.0):
    R.BG = np.array(BG, float)
    R._s4_programs.clear(); R._s4_static.clear()
    d = os.path.join(out, 'fighter/supamario/effect/supamario')
    p = ptcl.Ptcl(open(os.path.join(d, 'supamario.010d0000.ptcl'), 'rb').read())
    sets = {k: p.find_set('PtcSupamarioUi' + [x for x in B.FX if x[0] == k][0][2][:-4]) for k in ('aura_hip', 'aura_head', 'aura_foot')}
    calls = [('aura_hip', (0.0, HIP, 0.0), B.SCALE), ('aura_head', (0.0, HEAD + 0.2 * B.METRE, 0.0), B.SCALE),
             ('aura_foot', (0.0, 0.6, 1.2), 0.8 * B.SCALE), ('aura_foot', (0.0, 0.6, -1.2), 0.8 * B.SCALE)]
    canv = {fr: R.Canvas(-15, 15, -3, 25, 12.0) for fr in FRAMES}
    offs = {fr: np.zeros((canv[fr].h, canv[fr].w, 2)) for fr in FRAMES}
    programs = {}
    for n, (key, xyz, size) in enumerate(calls):
        ems = R.s4_emitters(p, sets[key], programs)
        cm = R.call_matrix(xyz, (0, 0, 0), size)
        for k, em in enumerate(ems):
            sim = R.simulate(em, (0, cm, size, None), FRAMES, seed=n * 10 + k + 1)
            is_haze = 'distortion pass (not drawn)' in getattr(em, 'notes', ()) or em.name == 'UiHaze'
            for fr in FRAMES:
                if not sim[fr]:
                    continue
                if is_haze:
                    tex = None
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
                        u = ((xs + r) * tw // (2 * r)).clip(0, tw - 1); v = ((ys + r) * th // (2 * r)).clip(0, th - 1)
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
    for fr in FRAMES:
        img = np.clip(canv[fr].rgb, 0, 1)
        o = offs[fr]
        if np.abs(o).max() > 0:
            h, w = img.shape[:2]
            yy, xx = np.mgrid[0:h, 0:w]
            sx = (xx + o[..., 0]).round().astype(int).clip(0, w - 1); sy = (yy + o[..., 1]).round().astype(int).clip(0, h - 1)
            # the distortion bends the picture behind (here the background's grid + a checker)
            bgc = np.tile(np.array(BG), (h, w, 1)); chk = (((xx // 12) + (yy // 12)) % 2 == 0)
            bgc[chk] *= 0.85
            warped = bgc[sy, sx]
            img = np.where(np.abs(canv[fr].rgb - np.array(BG)).sum(axis=2, keepdims=True) > 0.02, img, warped)
        ims.append((img * 255).astype(np.uint8))
    return np.concatenate(ims, axis=1), offs


if __name__ == '__main__':
    a, oa = render(sys.argv[1])
    b, ob = render(sys.argv[2])
    sheet = np.concatenate([a, b], axis=0)
    Image.fromarray(sheet).save(sys.argv[3])
    print('haze offsets max px: before %.1f after %.1f' % (max(np.abs(o).max() for o in oa.values()), max(np.abs(o).max() for o in ob.values())))
