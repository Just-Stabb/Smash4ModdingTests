#!/usr/bin/env python3
"""Greninja's forward air with the skeleton v1.3 package's blade flames (fighters/gekkouga/README.md "Skeleton v1.3"):
his model posed in AttackAirF and his effect script's effects drawn by tools/fx_render.py, each following its joint (the
water sword 0x3300007 and the flames 0x3300022 on hand joint 25: the joint's world matrix from the motion every frame),
a contact sheet and a GIF. As tools/gekkouga_nair_preview.py (its model drawing, its notes), plus the joints.

  python3 -I tools/gekkouga_fair_preview.py VANILLA_FIGHTER BUILT_FIGHTER OUT_DIR [--frames 2,8,13,16,19,23] [--name fair]
      [--axes]   (also print joint 25's local X / Y / Z as seen on screen at each frame: where the blade's edge is)
      [--hand RHaveN]   the bone drawn for joint 25 (default RHaveN: model.jtb table 0 gives joint 25 = ThrowN, which
                        AttackAirF holds still at his origin (its track constant): not where the game draws the sword;
                        the hand that sweeps in front in the motion stands in. Unresolved: README "Skeleton v1.3")
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import fx_render as F  # noqa: E402
import gekkouga_nair_preview as NP  # noqa: E402
import omo  # noqa: E402
import port_check  # noqa: E402
import ptcl  # noqa: E402

MOTION = 'FitGekkougaBodyMainC05AttackAirF.omo'
VIEW = (-30.0, 34.0, -24.0, 30.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--frames', default='2,8,13,16,19,23')
    ap.add_argument('--name', default='fair')
    ap.add_argument('--axes', action='store_true')
    ap.add_argument('--hand', default='RHaveN')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    frames = [int(x) for x in a.frames.split(',')]
    items, bones, bind = NP.model_items(a.vanilla)
    mdir = os.path.join(a.vanilla, 'model', 'body', 'c00')
    t0, _t1 = port_check.jtb(open(os.path.join(mdir, 'model.jtb'), 'rb').read())
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))[MOTION])
    edir = os.path.join(a.built, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    calls = F.s4_calls(os.path.join(a.built, 'script', 'animcmd', 'body', 'effect.bin'), 'AttackAirF')
    s4, programs = {}, {}
    for _f, gid, *_r in calls:
        if (int(gid) >> 16) not in (0x330, 0x100):
            continue
        if int(gid) not in s4 and int(gid) >> 16 == 0x330:
            s4[int(gid)] = F.s4_emitters(p, ef.entries[int(gid) & 0xFFFF][1] - 1, programs)
    gif_frames = list(range(1, 26))
    want = sorted(set(frames) | set(gif_frames))
    worlds = {fr: omo.world(o, bones, min(fr, o.frames - 1)) for fr in want}

    def joint(j, fr):
        if j == 0:
            return np.eye(4)
        return np.array(worlds[fr][a.hand if j == 25 else bones[t0[j]][0]])
    canv = {}
    for fr in want:
        c = F.Canvas(*VIEW, NP.PPU)
        c.rgb[:] = NP.BG
        NP.draw_model(c, NP.pose(items, bones, bind, o, min(fr, o.frames - 1)))
        canv[fr] = c
    if a.axes:
        for fr in frames:
            m = joint(25, fr)
            print('frame %d joint 25: origin (z %.1f, y %.1f); on screen (z, y): X %s Y %s Z %s' % (
                fr, m[2, 3], m[1, 3], np.round(m[[2, 1], 0], 2), np.round(m[[2, 1], 1], 2), np.round(m[[2, 1], 2], 2)))
    for k, (fr0, gid, bone, xyz, rot, size, off) in enumerate(calls):
        if int(gid) not in s4:
            continue
        cm = F.call_matrix(xyz, rot, size)
        for j, em in enumerate(s4[int(gid)]):
            for fr in want:                        # following its joint: played with that frame's joint matrix (its
                jm = joint(int(bone), fr) @ cm     # particles still: on the emitter's live matrix, follow type 0)
                sim = F.simulate(em, (fr0, jm, size, off), [fr], seed=10 * k + j + 1)
                if sim[fr]:
                    if not F.draw_s4(canv[fr], em, sim[fr], jm @ F.emitter_matrix(em, fr - fr0), float(fr - fr0)):
                        F.draw(canv[fr], em, sim[fr], jm)
    os.makedirs(a.out, exist_ok=True)
    tiles = []
    for fr in frames:
        im = Image.fromarray(canv[fr].image())
        ImageDraw.Draw(im).text((6, 4), 'frame %d' % fr, fill=(230, 230, 230))
        tiles.append(im)
    w, h = tiles[0].size
    sheet = Image.new('RGB', (w * len(tiles) + 4 * (len(tiles) - 1), h + 22), (18, 18, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * (w + 4), 22))
    ImageDraw.Draw(sheet).text((6, 5), 'Greninja forward air: ' + ', '.join('0x%X at frame %d' % (int(c[1]), c[0]) for c in calls
                                                                      if int(c[1]) in s4)
                               + '; offline render (see tools/gekkouga_nair_preview.py notes)', fill=(220, 220, 220))
    sheet.save(os.path.join(a.out, a.name + '.png'))
    gif = [Image.fromarray(canv[fr].image()).convert('P', palette=Image.ADAPTIVE) for fr in gif_frames]
    gif[0].save(os.path.join(a.out, a.name + '.gif'), save_all=True, append_images=gif[1:], duration=60, loop=0)
    print(os.path.join(a.out, a.name + '.png'))


if __name__ == '__main__':
    main()
