#!/usr/bin/env python3
"""Kirby's Hero copy (fix v8): the sword spells' hitboxes against the blade as the game draws it, frame by frame.

  python3 tools/kirby_hero_sword_hitboxes.py MAIN.pac KIRBY_VBN [--out DIR] [--json FILE] [--before OLD_MSC_PY]
      (the built motion/body/main.pac with the BraveSword17-20 animations, Kirby's body/c00/model.vbn; OLD_MSC_PY:
       an earlier tools/kirby_hero_sword_msc.py, e.g. fix v7's from git, whose hitboxes are drawn grey under these)

For each spell and each cast frame with hitboxes out (tools/kirby_hero_sword_msc.py's events, ground and air): the
blade (Hero's sword model from BLADE[0] to BLADE[1] along the drawn item's +Y, on Sword1's axis (x 0.2023): kirby_hero_sword_anim.fk_lhaven @
ITEM_TO_HAVE, fix v7's drawing rules: the root's translation left out, the item turned -90 about the joint's Z) and
every live hitbox's centre and radius in model space (bone 0x18 hitboxes: LHaveN's matrix x the offset; bone 0:
the offset itself, Kirby's TopN being the model's origin). Prints, per hitbox, its centre's distance from the blade
segment and where along the blade it is (0 = the hilt end, 1 = the tip); --out renders side views (one PNG a spell:
a tile a frame, the blade and the circles, Z right = Kirby's facing, Y up).
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402
import kirby_copy_motions as KM  # noqa: E402
import kirby_hero_sword_anim as A  # noqa: E402
import kirby_hero_sword_msc as SW  # noqa: E402

NAMES = {0x11: 'Flame Slash', 0x12: 'Kacrackle Slash', 0x13: 'Metal Slash', 0x14: 'Hatchet Man'}


def blade(o, sk, f, scale=1.0):
    """(hilt end, tip) of the drawn blade at cast frame f, model space"""
    D = A.fk_lhaven(o, sk, f) @ A.ITEM_TO_HAVE
    x = SW.SWORD1_TO_HAVE * scale                    # the blade's axis (Sword1's X) in the item's (HaveR's) frame
    return ((D @ np.array([x, A.BLADE[0] * scale, 0, 1.0]))[:3], (D @ np.array([x, A.BLADE[1] * scale, 0, 1.0]))[:3])


def seg_dist(p, a, b):
    """(distance from p to segment ab, the parameter 0..1 of its nearest point)"""
    ab = b - a
    t = float(np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * ab))), t


def live(ev, sit):
    """{cast frame: {id: hitbox values}} for frames with hitboxes out (an ID is replaced by a new one of its ID,
    khm_sw_remove clears 5-9)"""
    out, cur = {}, {}
    evs = ev[sit]
    last = max(f for f, k, _v in evs if k in ('hitbox', 'remove'))
    for f in range(0, last + 1):
        for g, k, v in evs:
            if g != f:
                continue
            if k == 'hitbox':
                cur[v[0]] = v
            elif k == 'remove':
                cur = {}
        if cur:
            out[f] = dict(cur)
    return out


def load_generator(path):
    """an earlier kirby_hero_sword_msc.py as a module (its own events(), reading this reference and path.json)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('old_sword_msc', path)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = os.path.join(HERE, 'kirby_hero_sword_msc.py')     # its REF / PATH relative to tools/
    src = open(path).read().replace("os.path.dirname(os.path.abspath(__file__))", repr(HERE))
    exec(compile(src, path, 'exec'), mod.__dict__)
    return mod


def measure(pac_path, vbn, ref=None, gen=SW):
    """{spell: {sit: {frame: {'blade': (a, b), 'hb': [(id, bone, centre, radius, dist, t)]}}}}"""
    pac = dict(omo.pac_read(pac_path))
    sk = KM.s4_skeleton(vbn)
    ev = gen.events(ref or gen.parse())
    res = {}
    for n in sorted(A.SLOT):
        o = omo.Omo(pac[A.NAME % (n - 0x11 + 17) + '.omo'])
        res[n] = {}
        for sit in ('ground', 'air'):
            frames = {}
            for f, hbs in sorted(live(ev[n], sit).items()):
                a, b = blade(o, sk, min(f, o.frames - 1), SW.SCALE)
                J = A.fk_lhaven(o, sk, min(f, o.frames - 1))
                rows = []
                for i, v in sorted(hbs.items()):
                    off = np.array([v[9], v[10], v[11], 1.0])
                    c = (J @ off)[:3] if v[2] == SW.K_SWORD else off[:3]
                    d, t = seg_dist(c, a, b)
                    rows.append((i, v[2], c, float(v[8]), d, t))
                frames[f] = {'blade': (a, b), 'hb': rows}
            res[n][sit] = frames
    return res


def render(res, out_dir, before=None):
    from PIL import Image, ImageDraw
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for n, sits in sorted(res.items()):
        frames = sits['ground']
        T, k = 380, 6.0
        cols = min(4, len(frames))
        rows_ = (len(frames) + cols - 1) // cols
        img = Image.new('RGB', (T * cols, T * rows_ + 30), (250, 250, 250))
        d0 = ImageDraw.Draw(img)
        d0.text((6, 6), '%s (ground): the drawn blade (black, grip end dot) and the hitboxes (red: on the sword bone; '
                'blue: bone 0%s), side view, Z right = facing, 1 unit = %d px; box: the stone'
                % (NAMES[n], '; grey: before' if before else '', k), fill=(0, 0, 0))
        for i, (f, fr) in enumerate(sorted(frames.items())):
            tile = Image.new('RGB', (T, T), (255, 255, 255))
            d = ImageDraw.Draw(tile)
            ox, oy = T * 0.3, T * 0.75

            def px(p):
                return (ox + p[2] * k, oy - p[1] * k)
            d.line([px((0, 0, -20)), px((0, 0, 40))], fill=(170, 170, 170))
            d.rectangle([px((0, 8.1, -5.8)), px((0, 0, 5.8))], outline=(150, 130, 110))
            if before and f in before[n]['ground']:
                for hid, bone, c, r, dist, t in before[n]['ground'][f]['hb']:
                    q = px(c)
                    d.ellipse([q[0] - r * k, q[1] - r * k, q[0] + r * k, q[1] + r * k], outline=(185, 185, 185), width=1)
            a, b = fr['blade']
            d.line([px(a), px(b)], fill=(0, 0, 0), width=3)
            d.ellipse([px(a)[0] - 3, px(a)[1] - 3, px(a)[0] + 3, px(a)[1] + 3], fill=(0, 0, 0))
            for hid, bone, c, r, dist, t in fr['hb']:
                col = (220, 30, 30) if bone == SW.K_SWORD else (40, 80, 220)
                q = px(c)
                d.ellipse([q[0] - r * k, q[1] - r * k, q[0] + r * k, q[1] + r * k], outline=col, width=2)
                d.text((q[0] - 3, q[1] - 5), str(hid - SW.ID_SHIFT), fill=col)
            d.rectangle([0, 0, T - 1, T - 1], outline=(200, 200, 200))
            d.text((4, 4), 'cast frame %d' % f, fill=(0, 0, 0))
            img.paste(tile, ((i % cols) * T, 30 + (i // cols) * T))
        fn = os.path.join(out_dir, 'hitboxes_%d.png' % (n - 0x11 + 17))
        img.save(fn)
        files.append(fn)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pac')
    ap.add_argument('vbn')
    ap.add_argument('--out')
    ap.add_argument('--json')
    ap.add_argument('--before')
    a = ap.parse_args()
    res = measure(a.pac, a.vbn)
    before = measure(a.pac, a.vbn, gen=load_generator(a.before)) if a.before else None
    js = {}
    for n, sits in sorted(res.items()):
        for sit, frames in sits.items():
            for f, fr in sorted(frames.items()):
                for hid, bone, c, r, dist, t in fr['hb']:
                    print('%-16s %-6s f%-3d id %d bone 0x%02x r %4.1f  centre (%6.2f %6.2f %6.2f)  off blade %5.2f  '
                          'along %.2f' % (NAMES[n], sit, f, hid - SW.ID_SHIFT, bone, r, c[0], c[1], c[2], dist, t))
                    js.setdefault('0x%x' % n, {}).setdefault(sit, []).append(
                        {'frame': f, 'id': hid - SW.ID_SHIFT, 'bone': bone, 'r': r, 'centre': [round(float(x), 3) for x in c],
                         'off_blade': round(dist, 3), 'along': round(t, 3)})
    if a.json:
        json.dump(js, open(a.json, 'w'), indent=1)
    if a.out:
        print('\n'.join(render(res, a.out, before)))


if __name__ == '__main__':
    main()
