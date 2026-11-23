#!/usr/bin/env python3
"""Ice detonation v1 (fighters/gekkouga/README.md "Ice detonation v1") previews, offline:

- ice_flash.gif / .png: the armed victim's countdown (his textured model in Wait1 as the stand-in victim, the overlay as
  the fighter shaders draw it: lit x (1 - a) + rgb x a, tools/gekkouga_clone_cave.py ice_flash(), one GIF frame a game
  frame), then the blast (the medium level) going off on it;
- ice_boom.gif / .png: the explosion (his bank's PtcGekkougaIceBoom through tools/fx_render.py: eft's emission and the
  game's own vertex / pixel programs) at three burn amounts, each at the size weapons/firetrail.c gives it (the hitbox's
  radius / ib_fx_ref()), the hitbox drawn as a circle, the stand-in victim at its centre;
- ice_sparkle.gif / .png: the uncharged Water Shuriken's sparkles (PtcGekkougaIceSparkle) round a stand-in shuriken (a
  disc of its hitbox's radius 5), in the shuriken's frame (the particles follow it: follow type 0).

  python3 -I tools/gekkouga_ice_preview.py VANILLA_FIGHTER BUILT_FIGHTER OUT_DIR
  python3 -I tools/gekkouga_ice_preview.py VANILLA_FIGHTER - OUT_DIR --v2     # ice_flash_v2.png only: the flash's yellow
                                                                              # before / after feature ice4 (beetle safety /
                                                                              # radar v2: 80 %), the same frames

VANILLA_FIGHTER: his vanilla fighter/gekkouga (model/body/c00, motion/body/main.pac); BUILT_FIGHTER: the package's
fighter/gekkouga (effect/gekkouga). Side view, no bloom / HDR, the model without its NU_ shaders.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import fx_render as F  # noqa: E402
import gekkouga_clone_cave as C  # noqa: E402
import gekkouga_nair_preview as NP  # noqa: E402
import omo  # noqa: E402
import ptcl  # noqa: E402

BOOM, SPARKLE = 0x3300023, 0x3300024
LEVELS = (5.0, 20.0, 60.0)         # burn amounts b (remaining % + 0.5 a stack): a light burn, half, full


def blast(b):
    """weapons/firetrail.c: (damage, radius, call size) for a burn amount"""
    lvl = min(1.0, max(0.0, b / 40.0))
    r = 8.0 + 14.0 * lvl
    return 5.0 + 13.0 * lvl, r, r / 10.0


def bank(built):
    edir = os.path.join(built, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    programs = {}
    return lambda gid: F.s4_emitters(p, ef.entries[gid & 0xFFFF][1] - 1, programs)


def effect_on(canvases, ems, frames, xyz, size, fr0=0):
    cm = F.call_matrix(xyz, (0.0, 0.0, 0.0), size)
    for j, em in enumerate(ems):
        sim = F.simulate(em, (fr0, cm, size, None), frames, seed=j + 1)
        for fr in frames:
            if sim[fr]:
                if not F.draw_s4(canvases[fr], em, sim[fr], cm @ F.emitter_matrix(em, fr - fr0), float(fr - fr0)):
                    F.draw(canvases[fr], em, sim[fr], cm)


def flash_v2(out, posed):
    """ice_flash_v2.png: the armed victim at the same countdown frames with ice detonation v1 - UI v1's yellow (top) and
    feature ice4's (bottom: 80 %), with swatches"""
    from PIL import Image, ImageDraw
    view, ppu = (-26.0, 26.0, -4.0, 40.0), 8.0
    base = F.Canvas(*view, ppu)
    base.rgb[:] = NP.BG
    NP.draw_model(base, posed)
    body = np.any(np.abs(base.rgb - NP.BG) > 1e-4, axis=2)
    n = C.ice_frames(C.RELEASE)
    rows = []
    for name, feats in (('before (UI v1: %s = RGB %s)', C.RELEASE - {'ice4'}), ('now (ice4: %s = RGB %s, 80 %%)', C.RELEASE)):
        y = C.ice_yellow(feats)
        fl = C.ice_flash(n, y)
        ims = []
        for t in (1, 2, 4, 7, 100, 103):
            col = fl[t - 1]
            rgb = base.rgb.copy()
            rgb[body] = rgb[body] * (1 - col[3]) + np.array(col[:3]) * col[3]
            im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
            ImageDraw.Draw(im).text((5, 4), 'frame %d' % t, fill=(235, 235, 235))
            ims.append(im)
        sw = Image.new('RGB', (90, ims[0].height), tuple(int(round(255 * v)) for v in y))
        rows.append((name % (y, tuple(int(round(255 * v)) for v in y)), ims + [sw]))
    w, h = rows[0][1][0].size
    sh = Image.new('RGB', (6 * (w + 4) + 94, 2 * (h + 22) + 4), (18, 18, 22))
    for k, (lab, ims) in enumerate(rows):
        y0 = k * (h + 22)
        ImageDraw.Draw(sh).text((6, y0 + 5), 'Ice flash yellow ' + lab + '; black, alpha 0.35 / 0.6 / 0.8 and the timing '
                                'unchanged (%d frames); offline render' % n, fill=(220, 220, 220))
        for i, im in enumerate(ims):
            sh.paste(im, (i * (w + 4), y0 + 22))
    sh.save(os.path.join(out, 'ice_flash_v2.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--v2', action='store_true')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    os.makedirs(a.out, exist_ok=True)
    items, bones, bind = NP.model_items(a.vanilla)
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))['FitGekkougaBodyMainA00Wait1.omo'])
    posed = NP.pose(items, bones, bind, o, 0)
    if a.v2:
        flash_v2(a.out, posed)
        return
    fx = bank(a.built)
    # ---- the flashing victim, then the blast
    view, ppu = (-26.0, 26.0, -4.0, 40.0), 8.0
    base = F.Canvas(*view, ppu)
    base.rgb[:] = NP.BG
    NP.draw_model(base, posed)
    body = np.any(np.abs(base.rgb - NP.BG) > 1e-4, axis=2)
    flash = C.ice_flash(C.ice_frames(C.RELEASE))
    _d, r, sz = blast(LEVELS[1])
    boom_frames = list(range(0, 64))
    bc = {}
    for fr in boom_frames:
        c = F.Canvas(*view, ppu)
        c.rgb[:] = base.rgb
        bc[fr] = c
    effect_on(bc, fx(BOOM), boom_frames, (0.0, C.ICE_Y, 0.0), sz)
    gif, sheet_frames = [], []
    for t in range(0, C.ice_frames(C.RELEASE) + 1):
        rgb = base.rgb.copy()
        lab = 'armed, frame %d' % t
        if t >= 1:
            col = flash[t - 1]
            rgb[body] = rgb[body] * (1 - col[3]) + np.array(col[:3]) * col[3]
        else:
            lab = 'the ice hit (burns cleared)'
        im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
        ImageDraw.Draw(im).text((5, 4), lab, fill=(235, 235, 235))
        gif.append(im)
        if t in (1, 2, 4, 7, 31, 33, 52):
            sheet_frames.append(im)
    for fr in boom_frames:
        im = Image.fromarray(bc[fr].image())
        ImageDraw.Draw(im).text((5, 4), 'blast (amount %g: %.1f %%, radius %.1f) + %d' % (LEVELS[1], _d, r, fr),
                                fill=(235, 235, 235))
        gif.append(im)
        if fr in (4, 16, 40, 56):
            sheet_frames.append(im)
    gif[0].save(os.path.join(a.out, 'ice_flash.gif'), save_all=True, append_images=gif[1:], duration=20, loop=0)
    w, h = sheet_frames[0].size
    sh = Image.new('RGB', (len(sheet_frames) * (w + 4), h + 22), (18, 18, 22))
    for i, t in enumerate(sheet_frames):
        sh.paste(t, (i * (w + 4), 22))
    ImageDraw.Draw(sh).text((6, 5), 'Ice detonation v1: the armed victim flashing yellow / black (the burn tint\'s slot) for '
                            '%d frames, then the blast; offline render' % C.ice_frames(C.RELEASE), fill=(220, 220, 220))
    sh.save(os.path.join(a.out, 'ice_flash.png'))
    # ---- the explosion at three burn amounts
    view2, ppu2 = (-45.0, 45.0, -38.0, 60.0), 3.2
    frames = list(range(0, 64))
    cols = []
    for b in LEVELS:
        d, r, sz = blast(b)
        cv = {}
        small = F.Canvas(*view, ppu)
        for fr in frames:
            c = F.Canvas(*view2, ppu2)
            c.rgb[:] = NP.BG
            NP.draw_model(c, posed)
            cv[fr] = c
        effect_on(cv, fx(BOOM), frames, (0.0, C.ICE_Y, 0.0), sz)
        cols.append((b, d, r, sz, cv))
        del small
    gif, sheet = [], []
    for fr in frames:
        tiles = []
        for b, d, r, sz, cv in cols:
            im = Image.fromarray(cv[fr].image())
            dr = ImageDraw.Draw(im)
            c = cv[fr]
            cx, cy, rr = (0.0 - c.x0) * c.ppu, (c.y1 - C.ICE_Y) * c.ppu, r * c.ppu
            if fr < 5:
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255), width=2)
            dr.text((5, 4), 'burn amount %g: %.1f %%, radius %.1f, effect x%.2f' % (b, d, r, sz), fill=(235, 235, 235))
            dr.text((5, 16), 'frame %d%s' % (fr, ' (hitbox on: frames 0 - 4)' if fr < 5 else ''), fill=(210, 210, 210))
            tiles.append(im)
        w, h = tiles[0].size
        im = Image.new('RGB', (3 * (w + 4), h), (18, 18, 22))
        for i, t in enumerate(tiles):
            im.paste(t, (i * (w + 4), 0))
        gif.append(im)
        if fr in (2, 10, 24, 40, 52):
            sheet.append(im)
    gif[0].save(os.path.join(a.out, 'ice_boom.gif'), save_all=True, append_images=gif[1:], duration=33, loop=0)
    w, h = sheet[0].size
    sh = Image.new('RGB', (w, len(sheet) * (h + 4) + 22), (18, 18, 22))
    for i, t in enumerate(sheet):
        sh.paste(t, (0, 22 + i * (h + 4)))
    ImageDraw.Draw(sh).text((6, 5), 'Ice detonation v1: PtcGekkougaIceBoom (Simple_Explosion_15 sped up, the smoke 8x) at '
                            'three burn amounts (frames 2, 10, 24, 40, 52); hitbox circle while on', fill=(220, 220, 220))
    sh.save(os.path.join(a.out, 'ice_boom.png'))
    # ---- the shuriken's sparkles
    view3, ppu3 = (-16.0, 16.0, -14.0, 14.0), 10.0
    frames = list(range(0, 90))
    cv = {}
    for fr in frames:
        c = F.Canvas(*view3, ppu3)
        c.rgb[:] = (0.2, 0.22, 0.28)
        yy, xx = np.mgrid[0:c.rgb.shape[0], 0:c.rgb.shape[1]]
        px, py = (xx / c.ppu + c.x0), (c.y1 - yy / c.ppu)
        disc = px * px + py * py <= 5.0 * 5.0
        c.rgb[disc] = (0.25, 0.55, 0.95)
        cv[fr] = c
    effect_on(cv, fx(SPARKLE), frames, (0.0, 0.0, 0.0), 1.0)
    gif = []
    for fr in frames:
        im = Image.fromarray(cv[fr].image())
        ImageDraw.Draw(im).text((5, 4), 'uncharged Water Shuriken: ice sparkles, frame %d' % fr, fill=(235, 235, 235))
        gif.append(im)
    gif[0].save(os.path.join(a.out, 'ice_sparkle.gif'), save_all=True, append_images=gif[1:], duration=20, loop=0)
    pick = [gif[i] for i in (6, 20, 45, 80)]
    w, h = pick[0].size
    sh = Image.new('RGB', (len(pick) * (w + 4), h + 22), (18, 18, 22))
    for i, t in enumerate(pick):
        sh.paste(t, (i * (w + 4), 22))
    ImageDraw.Draw(sh).text((6, 5), 'PtcGekkougaIceSparkle (the common bank\'s frozen-fighter twinkles) round the shuriken '
                            '(blue disc, its hitbox 5), in its frame', fill=(220, 220, 220))
    sh.save(os.path.join(a.out, 'ice_sparkle.png'))
    print(a.out)


if __name__ == '__main__':
    main()
