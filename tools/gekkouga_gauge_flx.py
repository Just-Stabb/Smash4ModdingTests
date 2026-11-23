#!/usr/bin/env python3
"""Greninja's round gauge in the damage panel (ui/info/dmg): a new clip "gkgauge_mc" in each per-player panel clip
(panel sprites 1-4, as tools/dmg_trait_badge.py's trait_mc) made of the layers of tools/gekkouga_gauge_art.py: four
rings ("gk_ticks_mc", "gk_dots_mc", "gk_arcs_mc", "gk_heavy_mc": one frame each, the executable turns them every
frame), the fill's faint track and the fill ("gk_fill_mc": 11 frames, 0 % - 100 %, the executable picks the frame),
on one new 1024 x 1024 texture (16 cells of 256 px). Tinted per mode by the executable (tools/gekkouga_clone_cave.py
"gk_panel"); without this clip in the panel the executable falls back to Little Mac's KO meter.

  python3 tools/gekkouga_gauge_flx.py SRC_DMG_DIR ART_DIR OUT_DIR [UI_ART_DIR]

UI_ART_DIR (UI radar / waveform v1): tools/gekkouga_ui_art.py extract's output: the radar ("gkradar_mc": "gk_rring_mc",
"gk_rbeetle_mc", "gk_rsweep_mc") right of the portrait and the waveform ("gkwave_mc", 60 frames) under it, on the next
texture slot (136, GIDX 0x2800FE31).

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
import gekkouga_ui_art as U  # noqa: E402

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


# UI radar / waveform v1 (fighters/gekkouga/README.md "UI radar / waveform v1"; the user: "a UI element slightly to the right
# of the Greninja's character icon ... the radar ... a parabeetle image layered into it" and "a small waveform element that
# ... tracks smash attack charge ... under Greninja's character icon"): two clips in panel sprites 1 - 4 on one new 1024 x
# 1024 texture (the radar's 3 layers in row 0's 256 px cells; the waveform's 60 frames in 256 x 48 cells below), placed by
# the portrait (face_bg_mc: the hexagon, FACE_W x FACE_H x its scale), hidden (alpha 0) until the executable's gk_ui shows
# them on a Greninja panel
UI_TEXTURE_ID = 0x2800FE31                   # (the gauge's 0x2800FE30, the trait badge's 0x2800FE00 / 01)
UI_NAMES = ('gkradar_mc', 'gk_rring_mc', 'gk_rbeetle_mc', 'gk_rsweep_mc', 'gkwave_mc')   # the executable's (UI_GAUGE_NAMES)
FACE_W, FACE_H = 116.0, 122.0                # the portrait hexagon (inf_dmg_f_back) at its place's scale 1
RADAR_FACE = 0.48                            # the radar's diameter: this x the hexagon's height (panel 3: 58.6; the round
                                             # gauge 144, the stock icons' row 37, the percent's digits 96)
RADAR_GAP = 2.0                              # its left edge this far right of the hexagon's right side
RADAR_UP = 0.43                              # its centre this x the hexagon's height above the hexagon's centre: in the
                                             # notch over the hexagon's upper-right edge, above the percent's top
RADAR_V2 = 2.0                               # beetle safety / radar v2 (the user: "double the size of the parabeetle
                                             # radar and move it very slightly upwards"): RADAR_FACE x this across (panel
                                             # 3: 117.2), about v1's centre (its left edge then over the hexagon's upper-
                                             # right corner, under the percent digits' top-left) ...
RADAR_RAISE = 4.0                            # ... raised this far (x the panel's scale: panel 3 4.0, panels 1 / 2 2.9 / 2.3)
WAVE_FACE = 0.86                             # the waveform's width: this x the hexagon's width (panel 3: 99.8 x 18.7)
WAVE_GAP = 2.0                               # its top this far under the hexagon's bottom point
WAVE_ROW = 256                               # the waveform's cells start under the radar's row


def ui_places(f, radar=2):
    """panel sprite -> {'radar': (x, y, scale), 'wave': (x, y, scale)} from its face_bg_mc (the hexagon). radar 1: UI v1's
    radar (RADAR_FACE of the hexagon's height, its left edge RADAR_GAP right of the hexagon); 2 (beetle safety / radar v2):
    RADAR_V2 x that size about v1's centre, RADAR_RAISE higher"""
    out = {}
    for panel in (1, 2, 3, 4):
        k = f.frame_key(panel, 0)
        pl = next(f.places[pi] for pi in k.places if f.instance_name(f.places[pi]) == 'face_bg_mc')
        m = f.transforms[pl.xform].matrix()
        fx, fy = m[4], m[5]
        fs = (m[0] ** 2 + m[1] ** 2) ** 0.5
        d = RADAR_FACE * FACE_H * fs
        rx = fx + FACE_W / 2 * fs + RADAR_GAP * fs + d / 2
        ry = fy - RADAR_UP * FACE_H * fs
        if radar == 2:
            d *= RADAR_V2
            ry -= RADAR_RAISE * fs
        ww = WAVE_FACE * FACE_W * fs
        wh = ww * U.WAVE_H / U.WAVE_W
        wy = fy + FACE_H / 2 * fs + WAVE_GAP * fs + wh / 2
        out[panel] = {'radar': (round(rx, 3), round(ry, 3), round(d / U.RSIZE, 4)),
                      'wave': (round(fx, 3), round(wy, 3), round(ww / U.WAVE_W, 4))}
    return out


def depth_of(f, panel, name):
    k = f.frame_key(panel, 0)
    return next(f.places[pi].depth for pi in k.places if f.instance_name(f.places[pi]) == name)


def ui_sheet(ui):
    """the 1024 x 1024 texture and its cells [(name, x, y, w, h)]"""
    L = U.load(ui)
    sheet = np.zeros((SHEET, SHEET, 4), np.uint8)
    cells_ = []
    for i, n in enumerate(U.LAYERS):
        sheet[0:U.RSIZE, i * U.RSIZE:(i + 1) * U.RSIZE] = L[n]
        cells_.append(('inf_dmg_gk_r%s' % n, i * U.RSIZE, 0, U.RSIZE, U.RSIZE))
    per_row = SHEET // U.WAVE_W
    for i, im in enumerate(L['wave']):
        x, y = (i % per_row) * U.WAVE_W, WAVE_ROW + (i // per_row) * U.WAVE_H
        assert y + U.WAVE_H <= SHEET
        sheet[y:y + U.WAVE_H, x:x + U.WAVE_W] = im
        cells_.append(('inf_dmg_gk_wave_%02d' % i, x, y, U.WAVE_W, U.WAVE_H))
    return sheet, cells_


def add_ui(f, tl, ui, preview=False, rv=2):
    """the radar and waveform clips (UI_NAMES) on a new texture slot: returns (slot, sheet, info). rv: ui_places' radar"""
    slot = len(tl.slots)
    tl.slots.append(0)
    sheet, cells_ = ui_sheet(ui)
    for name, x, y, w, h in cells_:
        tl.add(name, slot, x, y, w, h, SHEET, SHEET)
    layer = {n: f.add_sprite([[f.image_place('inf_dmg_gk_r%s' % n, U.RSIZE, U.RSIZE)]]) for n in U.LAYERS}
    parts = [f.sprite_place(layer[n], 'gk_r%s_mc' % n, slot=i, depth=i) for i, n in enumerate(U.LAYERS)]
    radar = f.add_sprite([parts])
    wave = f.add_sprite([[f.image_place('inf_dmg_gk_wave_%02d' % i, U.WAVE_W, U.WAVE_H)] for i in range(U.WAVE_FRAMES)],
                        labels={'w%02d' % i: i for i in range(U.WAVE_FRAMES)})
    places = ui_places(f, rv)
    col = flx.Color((100 if preview else 0, 100, 100, 100), (0, 0, 0, 0))
    for name, sprite, above in (('radar', radar, 'lv_mc'), ('wave', wave, 'name_col_mc')):
        ds = {depth_of(f, panel, above) for panel in (1, 2, 3, 4)}
        assert len(ds) == 1, ds
        d = ds.pop()
        raise_above(f, (1, 2, 3, 4), d)
        for panel in (1, 2, 3, 4):
            x, y, sc = places[panel][name]
            pl = f.sprite_place(sprite, 'gk%s_mc' % name, flx.Transform.make(x, y, sc), color=col,
                                slot=f.sprites[panel].nslots, depth=d + 1)
            f.insert_place(panel, pl)
    return slot, sheet, dict(radar=radar, layers=layer, wave=wave, places=places)


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


def build(src, art, out, v11=True, preview=False, ui=None, radar=2):
    """v11: round gauge v1.1 (on the emblem, hidden until shown); False: v1. preview: the gauge drawn visible (alpha 100),
    for flx_render only. ui: UI radar / waveform v1's art (tools/gekkouga_ui_art.py extract): its clips on the next slot.
    radar: 1 UI v1's radar place / size, 2 beetle safety / radar v2's (ui_places)"""
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
    uinfo = None
    if ui:
        uslot, usheet, uinfo = add_ui(f, tl, ui, preview, radar)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(src):
        if fn.endswith('.nut'):
            shutil.copy(os.path.join(src, fn), out)
    open(os.path.join(out, 'img-%05d.nut' % slot), 'wb').write(nut.write_ntwu([(TEXTURE_ID, 0x33, sheet)]))
    if ui:
        open(os.path.join(out, 'img-%05d.nut' % uslot), 'wb').write(nut.write_ntwu([(UI_TEXTURE_ID, 0x33, usheet)]))
        uinfo['texture_slot'] = uslot
    open(os.path.join(out, 'texlist.lst'), 'wb').write(tl.build())
    open(os.path.join(out, 'dmg.flx'), 'wb').write(flx.write(f))
    return dict(gauge=gauge, rings=rings, track=track, fill=fill, texture_slot=slot, ui=uinfo)


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    print(build(*sys.argv[1:4], ui=sys.argv[4] if len(sys.argv) == 5 else None))
