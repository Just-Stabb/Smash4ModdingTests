#!/usr/bin/env python3
"""Kirby's Hero copy fix v7: how the game draws the swung sword, from the user's fix v6 clip (Flame Slash).

  python3 tools/kirby_hero_sword_clip.py V6_MAIN.pac V7_MAIN.pac KIRBY_VBN [--frames DIR --out DIR]

The user's clip (MedalTV, 2026-11-14 12:43, Cemu, 1296x778, 60 fps) shows the fix v6 sword during Kirby's Flame Slash
from the 100t stone, side on, Kirby facing right (the hit lands on Hero to his right). Five frames (video 1.95 s + 3 ..
+ 7 frames, the sword's first five) were measured by hand on 2x crops of (430, 380)-(830, 620): the pommel end (the
striped hilt) and where the blade's tip is (or enters the floor), as (forward, up) in stone units from the stone's
base centre: 24 px a unit, the stone's centre at x 185, the floor at y 325 (the 100t stone: 11.6 wide, 8.1 tall).

What it shows (and checks):
- The fix v6 animation as fix v6 assumed it is drawn (the root TransN's translation (0, 9, 0) drawn, the item's +Y =
  the blade along LHaveN's +Y) misses the clip: the pommel 6-9 too high, the blade on the wrong axis.
- The same animation with TransN's translation not drawn and the item turned -90 about LHaveN's Z (its +Y along the
  joint's +X: kirby_hero_sword_anim.ITEM_TO_HAVE) matches it: pommel within ~1.3, the blade's direction on screen
  within ~25 degrees (the blade crosses the floor where measured). That is how fix v7 solves the swing.
- A free fit of the blade's axis in LHaveN's frame over the five frames lands on (0.99, -0.14, 0.03): +X.
- The fix v7 animation, drawn the same way, puts the item exactly where Hero's sword is (kirby_hero_sword_anim's own
  check, repeated here at the measured frames).
With --frames (the clip's frames g_03.png ... as extracted: ffmpeg -ss 1.95 -t 0.25 -vf fps=60 g_%02d.png) and --out,
it draws on each frame: red the fix v6 sword as fix v6 assumed, yellow as the game draws it (over the clip's sword),
green fix v7's (Hero's sword).
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402
import kirby_copy_motions as KM  # noqa: E402
import kirby_hero_sword_anim as A  # noqa: E402

# (video frame, cast frame shown): the sword's first visible frame shows cast frame 1 (it is shown from the cast's
# first update; the motion has moved one frame by then)
CLIP = [  # pommel (forward, up), blade end (forward, up)
    ('g_04', 1, (7.3, 6.25), (10.4, 1.04)),
    ('g_05', 2, (8.1, 8.5), (12.3, 1.9)),
    ('g_06', 3, (8.1, 8.1), (12.7, 3.75)),
    ('g_07', 4, (9.4, 7.7), (12.5, 5.6)),
    ('g_08', 5, (11.9, 6.4), (13.3, 1.7)),
]
CROP = (430, 380, 830, 620)
PX, CX, FLOOR = 24.0, 185.0, 325.0
FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


def drawn(o, sk, g, trans_drawn, item_to_have):
    """the item frame as drawn: LHaveN (the root's translation drawn or not) @ the item turn"""
    return A.fk_lhaven(o, sk, g, trans_drawn) @ item_to_have


def ends(m):
    """pommel and tip (forward = model Z, up = Y) of bravesword placed by item frame m"""
    a = m @ np.array([0, A.BLADE[0], 0, 1.0])
    b = m @ np.array([0, A.BLADE[1], 0, 1.0])
    return (a[2], a[1]), (b[2], b[1])


def screen_angle_err(p, t, op, ot):
    """the blade's direction on screen vs the clip's (degrees), the predicted blade clipped at the floor"""
    p, t = np.array(p), np.array(t)
    if t[1] < 0 and p[1] > 0:                                       # the floor hides the rest
        t = p + (t - p) * (p[1] / (p[1] - t[1]))
    v, w = t - p, np.array(ot) - np.array(op)
    c = float(v @ w) / (np.linalg.norm(v) * np.linalg.norm(w) + 1e-9)
    return float(np.degrees(np.arccos(max(-1.0, min(1.0, c)))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('v6_pac')
    ap.add_argument('v7_pac')
    ap.add_argument('vbn')
    ap.add_argument('--frames')
    ap.add_argument('--out')
    a = ap.parse_args()
    sk = KM.s4_skeleton(a.vbn)
    o6 = omo.Omo(dict(omo.pac_read(a.v6_pac))[A.NAME % 17 + '.omo'])
    o7 = omo.Omo(dict(omo.pac_read(a.v7_pac))[A.NAME % 17 + '.omo'])
    ident = np.eye(4)
    rows = {}
    for label, td, k in (('v6 as assumed', True, ident), ('as drawn', False, A.ITEM_TO_HAVE)):
        perr, aerr = [], []
        for _v, g, op, ot in CLIP:
            p, t = ends(drawn(o6, sk, g, td, k))
            perr.append(float(np.hypot(p[0] - op[0], p[1] - op[1])))
            aerr.append(screen_angle_err(p, t, op, ot))
        rows[label] = (max(perr), max(aerr))
        print('%-14s pommel off by %s, blade angle off by %s' % (label, np.round(perr, 2).tolist(), np.round(aerr, 1).tolist()))
    check('fix v6 as fix v6 assumed it drawn: the clip missed (pommel > 5 off or blade > 45 degrees)',
          rows['v6 as assumed'][0] > 5 or rows['v6 as assumed'][1] > 45, True)
    check('fix v6 drawn with TransN\'s translation left out and the item turned -90 about Z: the clip matched (pommel '
          'within 1.5, blade within 30 degrees)', rows['as drawn'][0] < 1.5 and rows['as drawn'][1] < 30, True)
    # the free fit of the blade's axis in LHaveN's frame
    best = None
    for th in np.linspace(0, np.pi, 91):
        for ph in np.linspace(0, 2 * np.pi, 181):
            d = np.array([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)])
            e = 0.0
            for _v, g, op, ot in CLIP:
                v = A.fk_lhaven(o6, sk, g, False)[:3, :3] @ d
                pz, w = np.array([v[2], v[1]]), np.array(ot) - np.array(op)
                e += 1 - float(pz @ w) / (np.linalg.norm(pz) * np.linalg.norm(w) + 1e-9)
            if best is None or e < best[0]:
                best = (e, d)
    check('the blade\'s axis fitted in LHaveN\'s frame (%s, error %.4f) is +X within 10 degrees'
          % (np.round(best[1], 2).tolist(), best[0]), float(best[1] @ [1, 0, 0]) > np.cos(np.radians(10)), True)
    if a.frames and a.out:
        from PIL import Image, ImageDraw
        os.makedirs(a.out, exist_ok=True)
        tiles = []
        for vname, g, _op, _ot in CLIP:
            im = Image.open(os.path.join(a.frames, vname + '.png')).crop(CROP).resize((800, 480))
            d = ImageDraw.Draw(im)

            def px(z, y):
                return (CX + z * PX, FLOOR - y * PX)
            for col, o, td, k in (((255, 60, 60), o6, True, ident), ((255, 230, 0), o6, False, A.ITEM_TO_HAVE),
                                  ((60, 255, 90), o7, False, A.ITEM_TO_HAVE)):
                p, t = ends(drawn(o, sk, g, td, k))
                d.line([px(*p), px(*t)], fill=col, width=3)
                d.ellipse([px(*p)[0] - 5, px(*p)[1] - 5, px(*p)[0] + 5, px(*p)[1] + 5], outline=col, width=2)
            d.text((6, 6), '%s (cast frame %d)  red: v6 as assumed  yellow: v6 as drawn  green: v7' % (vname, g),
                   fill=(255, 255, 255))
            tiles.append(im)
        sheet = Image.new('RGB', (1600, 480 * 3))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 2) * 800, (i // 2) * 480))
        sheet.save(os.path.join(a.out, 'clip_v6_vs_model.png'))
        print(os.path.join(a.out, 'clip_v6_vs_model.png'))
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
