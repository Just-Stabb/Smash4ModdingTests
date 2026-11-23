#!/usr/bin/env python3
"""Greninja's round gauge in the damage panel (ui/info/dmg): a new clip "gkgauge_mc" in each per-player panel clip
(panel sprites 1-4, as tools/dmg_trait_badge.py's trait_mc) made of the layers of tools/gekkouga_gauge_art.py: four
rings ("gk_ticks_mc", "gk_dots_mc", "gk_arcs_mc", "gk_heavy_mc": one frame each, the executable turns them every
frame), the fill's faint track and the fill ("gk_fill_mc": 11 frames, 0 % - 100 %, the executable picks the frame),
on one new 1024 x 1024 texture (16 cells of 256 px). Tinted per mode by the executable (tools/gekkouga_clone_cave.py
"gk_panel"); without this clip in the panel the executable falls back to Little Mac's KO meter.

  python3 tools/gekkouga_gauge_flx.py SRC_DMG_DIR ART_DIR OUT_DIR

SRC_DMG_DIR: the user's data/ui/info/dmg (dmg.flx, texlist.lst, img-*.nut: with the trait badge if it is installed);
ART_DIR: tools/gekkouga_gauge_art.py extract's output.
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402
import gekkouga_gauge_art as A  # noqa: E402

CELL = 256
SHEET = 1024
TEXTURE_ID = 0x2800FE30                      # unique GIDX (the trait badge has 0x2800FE00)
GAUGE_PX = 256                               # the gauge's size in the clip (scaled by PLACES)
# panel sprite -> (x, y, scale) of gkgauge_mc. Round gauge v1 (rendered on the user's dmg.flx, tools/flx_render.py): the
# Clones v7 places (left of the trait badge) sat on the CPU level ("Lv.") and the badge's star; now in Little Mac's KO
# meter band (the meter is hidden while the gauge shows), right of the trait badge (dmg_trait_badge.PLACES: its right edge
# + the gauge's radius (its outer ticks: the whole 256 px cell) + 2 - 3)
PLACES = {1: (72, -52, 0.16), 2: (38, -27, 0.12), 3: (122, -58, 0.24), 4: (122, -58, 0.24)}
# round gauge v1.1 (the user, in game: "far too small. It should be about the size of the fighter emblem (pokeball),
# slightly smaller. Also it's appearing on fighters other than Greninja"): centred on each panel's series emblem
# (mark_mc: a 254 px quad x its scale), its whole cell GAUGE_EMBLEM of the emblem's size, drawn just above the emblem
# (under the portrait, the percent and the rest: the depths above it moved up one), and hidden (alpha 0) until the
# executable shows it on a Greninja panel (gk_panel: visibility and the mode's colour, alpha 100)
GAUGE_EMBLEM = 0.87
EMBLEM_PX = 254


def emblem_places(f):
    """panel sprite -> (x, y, scale) of the gauge on its mark_mc, and mark_mc's depth"""
    out = {}
    for panel in (1, 2, 3, 4):
        k = f.frame_key(panel, 0)
        pl = next(f.places[pi] for pi in k.places if f.instance_name(f.places[pi]) == 'mark_mc')
        t = f.transforms[pl.xform]
        m = t.matrix()
        x, y = m[4], m[5]
        sc = (m[0] ** 2 + m[1] ** 2) ** 0.5
        out[panel] = (round(x, 3), round(y, 3), round(GAUGE_EMBLEM * EMBLEM_PX * sc / GAUGE_PX, 4), pl.depth)
    return out


def raise_above(f, sprites, depth):
    """every place of these sprites' keyframes deeper than depth one up (each place once); the places must be theirs only"""
    mine = set()
    for sp in sprites:
        s_ = f.sprites[sp]
        for k in f.keys[s_.key0:s_.key0 + s_.nkeys]:
            mine.update(k.places)
    others = set()
    for i, s_ in enumerate(f.sprites):
        if i not in sprites:
            for k in f.keys[s_.key0:s_.key0 + s_.nkeys]:
                others.update(k.places)
    assert not (mine & others), 'panel places shared with other sprites'
    for pi in mine:
        if f.places[pi].depth > depth:
            f.places[pi].depth += 1


def cells(art):
    """the 16 cell images: 4 rings (alpha baked per layer), the track, 11 fill frames"""
    out = []
    for name, _box, _scale, _speed, alpha in A.LAYERS:
        im = np.asarray(Image.open(os.path.join(art, name + '.png')).convert('RGBA')).copy()
        im[..., 3] = (im[..., 3].astype(np.float32) * alpha / 100.0).astype(np.uint8)
        out.append(('gk_' + name, im))
    tr = np.asarray(Image.open(os.path.join(art, 'meter.png')).convert('RGBA')).copy()
    tr[..., 3] = (tr[..., 3].astype(np.float32) * A.TRACK_ALPHA / 100.0).astype(np.uint8)
    out.append(('gk_track', tr))
    for k in range(A.FILL_STEPS):
        out.append(('gk_fill_%02d' % k, np.asarray(Image.open(os.path.join(art, 'fill_%02d.png' % k)).convert('RGBA'))))
    assert len(out) == (SHEET // CELL) ** 2
    return out


def build(src, art, out, v11=True, preview=False):
    """v11: round gauge v1.1 (on the emblem, hidden until shown); False: v1. preview: the gauge drawn visible (alpha 100),
    for flx_render only"""
    f = flx.read(open(os.path.join(src, 'dmg.flx'), 'rb').read())
    tl = flx.Tlst(open(os.path.join(src, 'texlist.lst'), 'rb').read())
    slot = len(tl.slots)
    tl.slots.append(0)
    sheet = np.zeros((SHEET, SHEET, 4), np.uint8)
    names = []
    for i, (name, im) in enumerate(cells(art)):
        x, y = (i % 4) * CELL, (i // 4) * CELL
        sheet[y:y + CELL, x:x + CELL] = im
        name = 'inf_dmg_%s' % name
        tl.add(name, slot, x, y, CELL, CELL, SHEET, SHEET)
        names.append(name)

    def one(name, px):
        return f.add_sprite([[f.image_place(name, px, px)]])
    rings = [one(names[i], int(GAUGE_PX * A.LAYERS[i][2])) for i in range(4)]
    fill_px = int(GAUGE_PX * A.FILL[2])
    track = one(names[4], fill_px)
    fill = f.add_sprite([[f.image_place(names[5 + k], fill_px, fill_px)] for k in range(A.FILL_STEPS)],
                        labels={'f%d' % k: k for k in range(A.FILL_STEPS)})
    parts = [f.sprite_place(sp, 'gk_%s_mc' % A.LAYERS[i][0], slot=i, depth=10 - i) for i, sp in enumerate(rings)]
    parts.append(f.sprite_place(track, None, slot=4, depth=5))
    parts.append(f.sprite_place(fill, 'gk_fill_mc', slot=5, depth=4))
    gauge = f.add_sprite([parts])
    if not v11:
        for panel, (x, y, s) in PLACES.items():
            f.insert_place(panel, f.sprite_place(gauge, 'gkgauge_mc', flx.Transform.make(x, y, s)))
    else:
        em = emblem_places(f)
        depths = {d for _x, _y, _s, d in em.values()}
        assert len(depths) == 1, depths
        d = depths.pop()
        raise_above(f, (1, 2, 3, 4), d)
        col = flx.Color((100 if preview else 0, 100, 100, 100), (0, 0, 0, 0))
        for panel, (x, y, s, _d) in em.items():
            pl = f.sprite_place(gauge, 'gkgauge_mc', flx.Transform.make(x, y, s), color=col, slot=f.sprites[panel].nslots,
                                depth=d + 1)
            f.insert_place(panel, pl)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sheet)]))
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return dict(gauge=gauge, rings=rings, track=track, fill=fill, texture_slot=slot)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    print(build(*sys.argv[1:]))
