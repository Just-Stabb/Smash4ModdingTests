#!/usr/bin/env python3
"""Kirby's Hero copy (fix v8 / v10): the sword spells' hitboxes in the world against the blade as the game draws it,
frame by frame, and whether they reach a fighter standing next to the stone.

  python3 tools/kirby_hero_sword_hitboxes.py [--v7 OLD_MSC_PY] [--v8 OLD_MSC_PY] [--out DIR] [--json FILE]
      (OLD_MSC_PY: an earlier tools/kirby_hero_sword_msc.py, e.g. from git: fix v7's 309d064, fix v8's fbe0d83)

Everything comes from reference/kirby_hero_sword_path.json (the swing animations' LHaveN matrices as the game draws
them, lhaven_world, and the drawn sword, item_world: tools/kirby_hero_sword_anim.py) and each generator's events.
Model space: X sideways (depth: + toward the camera on a right-facing fighter), Y up, Z forward (Kirby's facing); a
hitbox's offsets are in its bone's frame, so the same picture holds for both facings, on the ground and in the air.

Where a hitbox is (each generator's own events, a live hitbox kept from its set to Remove_All_Hitboxes):
- bone 0x18 (LHaveN, fix v6-v8): LHaveN's matrix that frame x the offset, under two readings of the game: A, its joints
  as drawn (TransN's translation left out, as fix v7 measured the drawing); B, its joints with TransN's (0, 9, 0) of
  the fix v6-v9 animations (bone 0 and everything under it 9 higher);
- bone 0 (TransN): the offset itself (A) or 9 higher (B) in fix v7's animations; fix v10's animations hold TransN at
  0, so A = B there;
- a capsule (fix v10) from its end X2/Y2/Z2 to its centre.

Reach (--test, and the table it prints): a fighter standing next to the stone in front of it, the core of a medium
body's hurtboxes as a box (X -1.5..1.5: their depth about Kirby's plane; Y 1..11; Z 7.8..13.8: 2 off the stone's 5.8
half-width, 6 wide): a spell reaches it when, on some frame, a hitbox (sphere or capsule) comes within its radius of
the box.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kirby_hero_sword_msc as SW  # noqa: E402

NAMES = {0x11: 'Flame Slash', 0x12: 'Kacrackle Slash', 0x13: 'Metal Slash', 0x14: 'Hatchet Man'}
OPPONENT = (np.array([-1.5, 1.0, 7.8]), np.array([1.5, 11.0, 13.8]))
TRANS_Y = 9.0                          # SpecialLw1's TransN Y, kept in the fix v6-v9 swing animations


def load_generator(path):
    """an earlier kirby_hero_sword_msc.py as a module (its own events(), reading this reference and path.json)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('old_sword_msc_%d' % abs(hash(path)), path)
    mod = importlib.util.module_from_spec(spec)
    src = open(path).read().replace("os.path.dirname(os.path.abspath(__file__))", repr(HERE))
    exec(compile(src, path, 'exec'), mod.__dict__)
    return mod


def path_data():
    p = json.load(open(SW.PATH))
    return {int(k, 16): ([np.array(m) for m in v['lhaven_world']], [np.array(m) for m in v['item_world']])
            for k, v in p['spells'].items()}, p['scale']


def blade(item, scale):
    """(grip end, tip) of the drawn blade: Hero's sword along the item's +Y on Sword1's axis (x 0.2023)"""
    import kirby_hero_sword_anim as A
    x = SW.SWORD1_TO_HAVE * scale
    return ((item @ np.array([x, A.BLADE[0] * scale, 0, 1.0]))[:3], (item @ np.array([x, A.BLADE[1] * scale, 0, 1.0]))[:3])


def world_hitboxes(ev, worlds, transn_y):
    """{frame: [(id, bone, centre, capsule end, radius)]} in model space; transn_y: TransN's translation the game puts
    under its joints for these hitboxes (0: reading A or fix v10's animations; 9: reading B, fix v6-v9's)"""
    out, live = {}, {}
    last = max(f for f, k, _v in ev if k in ('hitbox', 'remove'))
    by = {}
    for f, k, v in ev:
        by.setdefault(f, []).append((k, v))
    up = np.array([0.0, transn_y, 0.0])
    for f in range(last + 1):
        for k, v in by.get(f, []):
            if k == 'hitbox':
                live[v[0]] = v
            elif k == 'remove':
                live = {}
        for i, v in sorted(live.items()):
            off = np.array([v[9], v[10], v[11], 1.0])
            end = np.array([v[40], v[41], v[42], 1.0]) if len(v) > 42 else off
            if v[2] == 0:
                c, e = off[:3] + up, end[:3] + up
            else:
                W = worlds[min(f, len(worlds) - 1)]
                c, e = (W @ off)[:3] + up, (W @ end)[:3] + up
            out.setdefault(f, []).append((i - SW.ID_SHIFT, v[2], c, e, float(v[8])))
    return out


def box_dist(p, lo, hi):
    return float(np.linalg.norm(np.maximum(np.maximum(lo - p, 0.0), p - hi)))


def reach(hbs, box=OPPONENT):
    """[(frame, id, the closest distance less the radius)] where the hitbox reaches the box (<= 0)"""
    lo, hi = box
    out = []
    for f, rows in sorted(hbs.items()):
        for i, _b, c, e, r in rows:
            d = min(box_dist(c + t * (e - c), lo, hi) for t in np.linspace(0.0, 1.0, 21))
            if d <= r:
                out.append((f, i, round(d - r, 2)))
    return out


def render(sets, items, scale, out_dir):
    """per spell: side view (Z right, Y up) and top view (Z right, X up: depth), a column a frame; the drawn blade
    (black), the opponent's box (green), each set's hitboxes in its colour"""
    from PIL import Image, ImageDraw
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for n in sorted(NAMES):
        frames = sorted(set(f for _nm, _c, hb in sets for f in hb[n]))
        T, k = 260, 5.0
        img = Image.new('RGB', (T * len(frames), 2 * T + 44), (250, 250, 250))
        d0 = ImageDraw.Draw(img)
        d0.text((6, 4), '%s (ground and air alike): side view (top row: Z right = facing, Y up) and top view (bottom '
                'row: Z right, X up = depth); black: the drawn blade; green: a fighter next to the stone; %s (joints '
                'as drawn)' % (NAMES[n], ', '.join(nm for nm, _c, _h in sets)), fill=(0, 0, 0))
        d0.text((6, 18), '1 unit = %d px; the stone\'s outline brown; a hitbox: its circle (capsule: both ends and the '
                'line)' % k, fill=(0, 0, 0))
        for j, f in enumerate(frames):
            for row, (ax, lo_, hi_) in enumerate(((1, 0.0, 8.08), (0, -5.8, 5.8))):
                tile = Image.new('RGB', (T, T), (255, 255, 255))
                d = ImageDraw.Draw(tile)
                ox, oy = T * 0.22, T * (0.78 if row == 0 else 0.5)

                def px(p):
                    return (ox + p[2] * k, oy - p[ax] * k)
                d.line([px(np.array([0, 0, -10.0])), px(np.array([0, 0, 40.0]))], fill=(200, 200, 200))
                a, b = px(np.array([lo_, lo_, -5.8])), px(np.array([hi_, hi_, 5.8]))
                d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(150, 120, 90))
                lo, hi = OPPONENT
                a, b = px(lo), px(hi)
                d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(40, 170, 60),
                            width=2)
                ga, gb = blade(items[n][min(f, len(items[n]) - 1)], scale)
                d.line([px(ga), px(gb)], fill=(0, 0, 0), width=3)
                for _nm, col, hb in sets:
                    for _i, _b, c, e, r in hb[n].get(f, []):
                        for q in (px(c), px(e)):
                            d.ellipse([q[0] - r * k, q[1] - r * k, q[0] + r * k, q[1] + r * k], outline=col, width=2)
                        d.line([px(c), px(e)], fill=col, width=1)
                d.rectangle([0, 0, T - 1, T - 1], outline=(200, 200, 200))
                d.text((4, 4), 'cast frame %d, %s' % (f, 'side' if row == 0 else 'top (depth)'), fill=(0, 0, 0))
                img.paste(tile, (j * T, 44 + row * T))
        fn = os.path.join(out_dir, 'hitboxes_%d.png' % (n - 0x11 + 17))
        img.save(fn)
        files.append(fn)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--v7')
    ap.add_argument('--v8')
    ap.add_argument('--out')
    ap.add_argument('--json')
    ap.add_argument('--test', action='store_true', help='fail unless fix v10 (this generator) reaches the fighter in '
                    'every spell, ground and air, with its hitboxes on the drawn blade as seen from the side')
    a = ap.parse_args()
    data, scale = path_data()
    worlds = {n: w for n, (w, _i) in data.items()}
    items = {n: i for n, (_w, i) in data.items()}
    gens = [('v10', SW, ((0.0, 'A = B'),))]
    if a.v8:
        gens.insert(0, ('v8', load_generator(a.v8), ((0.0, 'A'), (TRANS_Y, 'B'))))
    if a.v7:
        gens.insert(0, ('v7', load_generator(a.v7), ((0.0, 'A'), (TRANS_Y, 'B'))))
    table, js, fails = [], {}, []
    hb_sets = {}
    for name, gen, readings in gens:
        ev = gen.events(gen.parse())
        for ty, rd in readings:
            for n in sorted(NAMES):
                for sit in ('ground', 'air'):
                    hb = world_hitboxes(ev[n][sit], worlds[n], ty)
                    if sit == 'ground':
                        hb_sets.setdefault((name, rd), {})[n] = hb
                    rc = reach(hb)
                    depth = max(abs(c[0]) for rows in hb.values() for _i, _b, c, _e, _r in rows)
                    table.append((name, rd, NAMES[n], sit, len(rc) > 0, rc[:4], round(depth, 1)))
                    js.setdefault(name, {}).setdefault(rd, {}).setdefault(NAMES[n], {})[sit] = {
                        'reaches': rc, 'max_depth': depth,
                        'frames': {f: [(i, b, [round(float(x), 2) for x in c], [round(float(x), 2) for x in e], r)
                                       for i, b, c, e, r in rows] for f, rows in hb.items()}}
                    if name == 'v10':
                        if not rc:
                            fails.append((NAMES[n], sit, 'no reach'))
                        off = [(f, i) for f, rows in hb.items() for i, _b, c, _e, _r in rows
                               if abs(c[0]) > 1e-3]
                        if off:
                            fails.append((NAMES[n], sit, 'off the plane', off[:3]))
                        # as seen from the side, each hitbox on the drawn blade's line (Y / Z)
                        far = []
                        for f, rows in hb.items():
                            ga, gb = blade(items[n][min(f, len(items[n]) - 1)], scale)
                            for i, _b, c, _e, _r in rows:
                                p, q, s = c[1:], ga[1:], gb[1:]
                                t = np.clip(np.dot(p - q, s - q) / np.dot(s - q, s - q), 0, 1)
                                if np.linalg.norm(p - (q + t * (s - q))) > 0.05:
                                    far.append((f, i))
                        if far:
                            fails.append((NAMES[n], sit, 'off the blade as seen from the side', far[:3]))
    for row in table:
        print('%-4s %-6s %-16s %-6s reaches %-5s depth up to %5.1f  %s' % (row[0], row[1], row[2], row[3], row[4], row[6],
                                                                           row[5]))
    if a.json:
        json.dump(js, open(a.json, 'w'), indent=1, default=float)
    if a.out:
        cols = {'v7': ('grey', (170, 170, 170)), 'v8': ('orange', (240, 150, 40)), 'v10': ('red', (220, 30, 30))}
        sets = [('%s %s' % (nm, cols[nm][0]), cols[nm][1], hb) for (nm, rd), hb in hb_sets.items() if rd in ('A', 'A = B')]
        print('\n'.join(render(sets, items, scale, a.out)))
    if a.test:
        print('%s fix v10: every spell, ground and air, reaches a fighter next to the stone; every hitbox on Kirby\'s '
              'plane and on the drawn blade as seen from the side%s' % ('ok  ' if not fails else 'FAIL',
                                                                        '' if not fails else ': %r' % fails))
        sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
