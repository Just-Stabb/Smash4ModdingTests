#!/usr/bin/env python3
"""Greninja's Parabeetle (fighters/gekkouga/README.md "Parabeetle v1"): previews of the converted model and motions,
rendered from the written files (tools/nud_preview.py: model.nud / .nut / .vbn and main.pac) with its collision line.

  python3 tools/gekkouga_parabeetle_preview.py FIGHTER_DIR SRC_DIR OUT_DIR
      FIGHTER_DIR: the built fighter/gekkouga; SRC_DIR: the user's Parabeetle files (the CHR0s: the root's bob, which the
      article itself does in game, put back here as weapons/parabeetle.c pb_bob does)
      -> OUT_DIR/parabeetle_model.png: facing right (as the game turns an article facing right), front, facing left,
         three quarters, from above; its collision line (green: x +- 10 at y 10.6) on the side views; Greninja's size
         (a grey 12 x 30 box: his clones' boxes) beside it
      -> OUT_DIR/parabeetle_anims.gif: wait (80 frames), rise (80), ridden (7, twice), facing right, its line moving with
         it (the bob), 30 fps
      -> OUT_DIR/parabeetle_path.png: its path (weapons/parabeetle.c: forward 0.75 a frame, the swoop, the rise; the
         ground start), 240 frames
  python3 tools/gekkouga_parabeetle_preview.py --v2 FIGHTER_DIR SRC_DIR OUT_DIR   (parabeetle v2, README "Parabeetle v2")
      its compiled MSC (FIGHTER_DIR/script/msc/parabeetle/parabeetle.mscsb) run as the game would (a motion played once
      and held on its last frame; the clones test's pb_make / pb_run):
      -> OUT_DIR/parabeetle_path.png: its line's path for each stick direction (neutral, up-right / up-left 22 and 45
         degrees, right / left; down is clamped: neutral / its side), the hold, the 240 frames, the leaving; 1 unit = 1
         pixel x 2, the rise / sideways ratios
      -> OUT_DIR/parabeetle_wings.gif: the beetle over its whole life (hold, swoop, rise, leaving; ridden from flight
         nobody on it once it flies; ridden is the tests') posed by the motion / frame its MSC plays each frame, every 2nd frame; and parabeetle_wings.png: the
         motion frame against the life frame (v1's held from 80 frames into the rise; v2's never)
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nud_preview as N  # noqa: E402
import omo  # noqa: E402


def held_bob(src_dir):
    import chr0_to_omo as CH
    import mdl0_to_nud as M
    import gekkouga_build as GB
    import gekkouga_clone_cave as C
    model = M.parse(os.path.join(src_dir, GB.PB_MDL0))
    out = {}
    for name, ch in zip(C.PB_MOTIONS, GB.PB_CHR0):
        anim = CH.parse(os.path.join(src_dir, ch + '.chr0'))
        _b, _f, _l, held = CH.to_omo(anim, model, C.PB_SCALE, None, {GB.PB_ROOT: 1})
        out[name] = held[GB.PB_ROOT]
    return out


def shifted(posed, dy):
    return [dict(it, pos=it['pos'] + np.array([0.0, dy, 0.0])) for it in posed]


def turned(posed, yaw, pitch=0.0):
    th, a = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    R = Rx @ Ry
    return [dict(it, pos=it['pos'] @ R.T, nrm=it['nrm'] @ R.T) for it in posed]


def box(img, view, size, x0, x1, y0, y1, colour=(120, 120, 130)):
    cx, cy, span = view
    sx = lambda x: int(((x - cx) / span + 0.5) * size)   # noqa: E731
    sy = lambda y: int((0.5 - (y - cy) / span) * size)   # noqa: E731
    a, b, c, d = sx(x0), sx(x1), sy(y1), sy(y0)
    for x in range(max(0, a), min(size, b + 1)):
        for y in (c, d):
            if 0 <= y < size:
                img[y, x] = colour
    for y in range(max(0, c), min(size, d + 1)):
        for x in (a, b):
            if 0 <= x < size:
                img[y, x] = colour
    return img


def main():
    from PIL import Image
    import gekkouga_clone_cave as C
    fighter, src, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    md = os.path.join(fighter, 'model', 'parabeetle', 'c00')
    items, bones, bind = N.load(md)
    pac = dict(omo.pac_read(os.path.join(fighter, 'motion', 'parabeetle', 'main.pac')))
    bob = held_bob(src)
    size = 300
    view = (0.0, 13.0, 62.0)
    wait = omo.Omo(pac[C.PB_MOTIONS[0] + '.omo'])
    ps = shifted(N.pose(items, bones, bind, wait, 0), bob[C.PB_MOTIONS[0]][0])
    top = C.PB_TOP + bob[C.PB_MOTIONS[0]][0]
    tiles = []
    for yaw, pitch, label, line in ((90, 0, 'facing right', True), (0, 0, 'front', False), (-90, 0, 'facing left', True),
                                    (45, 15, 'three quarters', False), (90, 70, 'from above', False)):
        t = N.draw(turned(ps, yaw, pitch), size, view, 0.0, floor=(top, -C.PB_HALF, C.PB_HALF) if line else None)
        if yaw == 90 and pitch == 0:
            t = box(t.copy(), view, size, -6.0, 6.0, top, top + 30.0)       # Greninja's size standing on it
        tiles.append(N.label(t, label))
    sheet = np.concatenate(tiles, 1)
    cap = np.zeros((26, sheet.shape[1], 3), np.uint8) + 30
    sh = ps[0]['pos']
    al = np.concatenate([it['pos'] for it in ps])
    cap = N.label(cap, 'Parabeetle x %.2f: shell %.1f long (%.1f with its head), %.1f across the wings; its line (green) x +- %.0f '
                  'at y %.1f (+ its bob, %.2f at frame 0); grey: Greninja-sized (12 x 30) standing on it' % (
                      C.PB_SCALE, np.ptp(sh[:, 2]), np.ptp(al[:, 2]), np.ptp(al[:, 0]), C.PB_HALF, C.PB_TOP,
                      bob[C.PB_MOTIONS[0]][0]))
    Image.fromarray(np.concatenate([sheet, cap], 0)).save(os.path.join(out, 'parabeetle_model.png'))
    frames = []
    for name, reps in zip(C.PB_MOTIONS, (1, 1, 2)):
        o = omo.Omo(pac[name + '.omo'])
        for _r in range(reps):
            for f in range(o.frames):
                dy = bob[name][f]
                p = turned(shifted(N.pose(items, bones, bind, o, f), dy), 90)
                img = N.draw(p, 260, (0.0, 8.0, 50.0), 0.0, floor=(C.PB_TOP + dy, -C.PB_HALF, C.PB_HALF))
                frames.append(Image.fromarray(N.label(img, '%s %d / %d' % (name[len('FitGekkougaParabeetleMain'):], f,
                                                                           o.frames))))
    frames[0].save(os.path.join(out, 'parabeetle_anims.gif'), save_all=True, append_images=frames[1:], duration=33, loop=0)
    # the path (weapons/parabeetle.c pb_curve), air and ground starts
    W, H = 720, 300
    img = np.zeros((H, W, 3), np.uint8) + 30
    xs = lambda x: int(20 + x * (W - 40) / 190.0)   # noqa: E731
    ys = lambda y: int(H - 30 - (y + 12) * (H - 60) / 100.0)   # noqa: E731

    def curve(t):
        if t <= 20:
            return -8 * (1 - math.cos(math.pi * t / 20)) / 2
        u = t - 20
        return -8 + (0.4 * u * u / 60 if u <= 30 else 6 + 0.4 * (u - 30))
    for y0, col in ((0.0, (90, 230, 120)), (11.5, (230, 190, 90))):
        for t in range(241):
            x, y = xs(0.75 * t), ys(y0 + curve(t))
            if 0 <= x < W and 0 <= y < H:
                img[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = col
    for yv in (0.0,):
        img[ys(yv), :] = (90, 90, 100)
    img = N.label(img, 'its line: in the air from his feet (green), on the ground from 11.5 over them (gold): forward 0.75 '
                       'a frame, down 8 in 20 frames, then up to 0.4 a frame; 240 frames (180 forward, +74)')
    Image.fromarray(img).save(os.path.join(out, 'parabeetle_path.png'))
    print(os.path.join(out, 'parabeetle_model.png'), os.path.join(out, 'parabeetle_anims.gif'),
          os.path.join(out, 'parabeetle_path.png'), len(frames), 'frames')


def v2(fighter, src, out):
    from PIL import Image
    import gekkouga_clone_cave as C
    sys.argv = [sys.argv[0]]
    import gekkouga_clones_test as T
    import gekkouga_build as GB
    mscsb = os.path.join(fighter, 'script', 'msc', 'parabeetle', 'parabeetle.mscsb')
    os.makedirs(out, exist_ok=True)
    # ---- the paths
    W, H, k = 560, 720, 2.0
    img = np.zeros((H, W, 3), np.uint8) + 30
    ox, oy = W // 2, H - 70
    img[oy, :] = (80, 80, 90)
    img[:, ox] = (60, 60, 70)
    cols = {'neutral (toward his facing: right)': (90, 230, 120), 'up-right 22': (120, 200, 255),
            'up-right 45 / right': (255, 200, 90), 'up-left 22': (200, 120, 255), 'up-left 45 / left': (255, 110, 110)}
    lines = []
    for nm, code in (('neutral (toward his facing: right)', 1.0), ('up-right 22', 1.0 + 8 * 22),
                     ('up-right 45 / right', 1.0 + 8 * 90), ('up-left 22', -(1.0 + 8 * 22)), ('up-left 45 / left', -(1.0 + 8 * 90))):
        m, g = T.pb_make(mscsb, GB.PARABEETLE_MSC, code=code, his=(0.0, 0.0))
        T.pb_run(m, 2)
        g.vars[0x0F000029] = 500.0
        pts = []
        while not [x for x in g.log if x[0] == 'remove'] and len(pts) < 400:
            T.pb_run(m)
            pts.append((m.gf('pb_x'), m.gf('pb_y') + C.PB_TOP - m.gf('pb_y0') - C.PB_TOP, m.g('pb_phase')))
        for i, (x, y, ph) in enumerate(pts):
            px, py = int(ox + x * k), int(oy - y * k)
            if 0 <= px < W and 0 <= py < H:
                c = cols[nm] if ph == 1 else tuple(v // 2 for v in cols[nm])
                img[max(0, py - 1):py + 2, max(0, px - 1):px + 2] = c
                if i % 60 == 59 and ph == 1:
                    img[max(0, py - 4):py + 5, max(0, px - 4):px + 5] = c
        fl = [p for p in pts if p[2] == 1]
        lines.append('%s: %+.0f sideways, %+.0f up (x %.1f)' % (nm, fl[-1][0], fl[-1][1], fl[-1][1] / max(abs(fl[-1][0]), 1e-6)))
    img = N.label(img, 'v2 path: its line from his feet, x 2 px a unit; squares each 1 s; dim: leaving')
    caps = []
    for t in lines + ['swoop 6 down over 16 frames, then up to 0.7 a frame over 20; down held: clamped level']:
        c = np.zeros((22, W, 3), np.uint8) + 30
        caps.append(N.label(c, t))
    Image.fromarray(np.concatenate([img] + caps, 0)).save(os.path.join(out, 'parabeetle_path.png'))
    # ---- the wings over its life
    md = os.path.join(fighter, 'model', 'parabeetle', 'c00')
    items, bones, bind = N.load(md)
    pac = dict(omo.pac_read(os.path.join(fighter, 'motion', 'parabeetle', 'main.pac')))
    oms = {i: omo.Omo(pac[n + '.omo']) for i, n in enumerate(C.PB_MOTIONS)}
    bob = held_bob(src)
    m, g = T.pb_make(mscsb, GB.PARABEETLE_MSC, his=(0.0, 0.0))
    life, gif = [], []
    n = 0
    while not [x for x in g.log if x[0] == 'remove'] and n < 400:
        if m.g('pb_t') > 0:
            g.vars[0x0F000028], g.vars[0x0F000029] = 500.0, 500.0   # (he jumps off once it flies: nobody on it)
        mo, fr = g.motion, int(g.frame)               # (what it shows this frame)
        T.pb_run(m)
        life.append((n, mo, fr))
        if n % 2 == 0:
            o = oms[mo]
            f = min(fr, o.frames - 1)
            dy = bob[C.PB_MOTIONS[mo]][f]
            p = turned(shifted(N.pose(items, bones, bind, o, f), dy), 90)
            im = N.draw(p, 200, (0.0, 8.0, 50.0), 0.0, floor=(C.PB_TOP + dy, -C.PB_HALF, C.PB_HALF))
            gif.append(Image.fromarray(N.label(im, 'life %d: %s %d' % (n, ('wait', 'rise', 'ridden')[mo], f))))
        n += 1
    gif[0].save(os.path.join(out, 'parabeetle_wings.gif'), save_all=True, append_images=gif[1:], duration=33, loop=0)
    Wg, Hg = 2 * len(life) + 40, 200
    pl = np.zeros((Hg, Wg, 3), np.uint8) + 30
    for i, mo, fr in life:
        x, y = 20 + 2 * i, Hg - 20 - int(fr * 2)
        pl[max(0, y - 1):y + 2, x:x + 2] = ((90, 230, 120), (255, 200, 90), (255, 110, 110))[mo]
    pl = N.label(pl, 'v2: motion frame (up) over its %d frames of life: wait green, rise gold - never held (v1: rise held from 80 in)' % len(life))
    Image.fromarray(pl).save(os.path.join(out, 'parabeetle_wings.png'))
    print(os.path.join(out, 'parabeetle_path.png'), os.path.join(out, 'parabeetle_wings.gif'),
          os.path.join(out, 'parabeetle_wings.png'), len(gif), 'frames')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--v2']:
        v2(*sys.argv[2:5])
    else:
        main()
