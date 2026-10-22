#!/usr/bin/env python3
"""A new series ("mark") for stages: its textures, its ui_mark_db.bin row, its name, and stages set
to it. The executable side (the id -> name table) is tools/series_cave.py.

  python3 tools/add_series.py SYMBOL.png --name minecraft --title Minecraft --id 0x2A \\
      --templates VANILLA_UI --mark-db param/ui/ui_mark_db.bin --stage-db param/ui/ui_stage_db.bin \\
      --stage 0x38 --menu ui/message/menu.msbt --out OUT [--tex-id 0x2803A000]

SYMBOL: a white symbol on black or transparency (Smash Ultimate's series_1_<series>.bntx: tools/bntx.py png).
Writes, under OUT:
- ui/replace/append/mark/mark_00|30|60/mark_NN_<name>.nut: the game's mark sets drawn the way its
  own are (read off Bayonetta's / Smash Bros.'s): 00 (128x128) and 30 (256x256) BC4 (one channel: the
  symbol white, ~0.8 of the side), 60 (256x256) BC3 (the symbol black with a white outline, on
  transparency, ~0.74 with the outline); Bayonetta's files (TEMPLATES/replace/append/mark) as
  templates (format, tiling), new texture ids. mark_70 exists for two series only: not made.
  (append/: the row's flag 1 makes the path builder try ui/replace/append/ first, as the DLC series.)
- param/ui/ui_mark_db.bin: a row {id, 1, order = the last + 1, 0} after the last series row (Bayonetta's
  41: {41, 1, 30, 0}); the order is only sorted (0x030A8608 -> a list), never an index.
- param/ui/ui_stage_db.bin: the stages' series (value [2]) = id.
- ui/message/menu.msbt: Mmen_MarkN_<name> = title (the series' name, as Mmen_MarkN_bayonetta).
Every edited file is re-read and checked: without the change it rebuilds byte for byte.
"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import msbt  # noqa: E402
import nut  # noqa: E402
import s4param  # noqa: E402
from add_stage import texture_ids  # noqa: E402

SETS = {'00': (0.80, 0), '30': (0.80, 0), '60': (0.68, 5)}     # symbol size (of the side), outline px


def symbol_mask(path):
    rgba = np.asarray(Image.open(path).convert('RGBA')).astype(float)
    a = rgba[..., :3].mean(2) * rgba[..., 3] / 255 > 127
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def filled(mask):
    im = Image.fromarray(np.pad(mask, 1).astype(np.uint8) * 255).copy()
    ImageDraw.floodfill(im, (0, 0), 128)
    return np.asarray(im)[1:-1, 1:-1] != 128


def placed(mask, side, size):
    """the mask (float 0-1) scaled to size x side, centred on a side x side canvas"""
    h = round(side * size)
    w = round(mask.shape[1] * h / mask.shape[0])
    if w > h:
        w, h = h, round(mask.shape[0] * h / mask.shape[1])
    im = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((w, h), Image.LANCZOS)) / 255.0
    out = np.zeros((side, side))
    y0, x0 = (side - h) // 2, (side - w) // 2
    out[y0:y0 + h, x0:x0 + w] = im
    return out


def mark_image(mask, side, size, outline):
    img = np.zeros((side, side, 4), np.uint8)
    glyph = placed(mask, side, size)
    if not outline:                         # BC4: the symbol in the one channel (red)
        v = (glyph * 255).round().astype(np.uint8)
        img[..., 0] = img[..., 1] = img[..., 2] = v
        img[..., 3] = 255
        return img
    # BC3: the symbol black, a white outline around it (its outer edge and its holes'), the rest clear
    outer = np.asarray(Image.fromarray((glyph * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(2 * outline + 1))).astype(float) / 255
    outer = np.asarray(Image.fromarray((outer * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))) / 255.0
    white = np.clip(outer - glyph, 0, 1)
    rgb = 255 * white / np.maximum(outer, 1e-6)
    img[..., :3] = rgb.round().clip(0, 255).astype(np.uint8)[..., None]
    img[..., 3] = (outer * 255).round().astype(np.uint8)
    return img


def rows_of(path):
    data = open(path, 'rb').read()
    p = s4param.parse(data)
    assert s4param.build(p) == data, path + ': round trip'
    return data, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbol')
    ap.add_argument('--name', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--id', required=True)
    ap.add_argument('--templates', required=True, help='a ui folder with replace/append/mark/mark_NN/mark_NN_bayonetta.nut')
    ap.add_argument('--mark-db', required=True)
    ap.add_argument('--stage-db')
    ap.add_argument('--stage', action='append', default=[], help='cosmetic id of a stage to set to the series')
    ap.add_argument('--menu')
    ap.add_argument('--tex-id', default='0x2803A000')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    sid, tex = int(a.id, 0), int(a.tex_id, 0)
    mask = symbol_mask(a.symbol)
    log = []

    for s, (size, outline) in SETS.items():
        src = os.path.join(a.templates, 'replace', 'append', 'mark', 'mark_' + s, 'mark_%s_bayonetta.nut' % s)
        d, texs = nut.load(src)
        t = texs[0]
        assert t.w == t.h, (src, t.w, t.h)
        data = bytearray(nut.replace(d, t, mark_image(mask, t.w, size, outline)))
        for off, _old in texture_ids(data):
            struct.pack_into('>I', data, off, tex)
        dst = os.path.join(a.out, 'ui', 'replace', 'append', 'mark', 'mark_' + s, 'mark_%s_%s.nut' % (s, a.name))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bytes(data))
        log.append('%s (%dx%d, format 0x%X, texture 0x%08X)' % (os.path.relpath(dst, a.out), t.w, t.h, t.fmt, tex))
        Image.fromarray(nut.decode(bytes(data), nut.load(dst)[1][0])).save(dst[:-4] + '.png')
        tex += 1

    data, p = rows_of(a.mark_db)
    g = p[0]
    assert g[0] == 'group'
    ids = [e[0][1] for e in g[2]]
    assert sid not in ids, 'id 0x%X has a row already' % sid
    series = [k for k, e in enumerate(g[2]) if e[0][1] < 0x63]
    last = series[-1]
    row = [list(x) for x in g[2][last]]
    row[0][1], row[1][1], row[2][1], row[3][1] = sid, 1, max(e[2][1] for e in g[2]) + 1, 0
    g[2].insert(last + 1, [tuple(x) for x in row])
    g[1] += 1
    out = s4param.build(p)
    chk = s4param.parse(out)
    del chk[0][2][last + 1]
    chk[0][1] -= 1
    assert s4param.build(chk) == data
    dst = os.path.join(a.out, 'param', 'ui', 'ui_mark_db.bin')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    log.append('param/ui/ui_mark_db.bin: row %s at position %d (%d rows)' % ([x[1] for x in row], last + 1, g[1]))

    if a.stage_db and a.stage:
        data, p = rows_of(a.stage_db)
        g = [x for x in p if x[0] == 'group'][0]
        want = {int(x, 0) for x in a.stage}
        done = []
        for e in g[2]:
            if e[0][1] in want:
                t, old = e[2]
                e[2] = (t, sid)
                done.append((e[0][1], old))
        assert {k for k, _ in done} == want, done
        out = s4param.build(p)
        dst = os.path.join(a.out, 'param', 'ui', 'ui_stage_db.bin')
        open(dst, 'wb').write(out)
        log.append('param/ui/ui_stage_db.bin: series of %s -> 0x%X' % (', '.join('0x%X (was %d)' % x for x in done), sid))

    if a.menu:
        data = open(a.menu, 'rb').read()
        m = msbt.Msbt(data)
        assert m.build() == data
        lab = 'Mmen_MarkN_' + a.name
        assert lab not in m.labels
        old = {k: m.text(k) for k in m.labels}
        m.set(lab, a.title)
        out = m.build()
        c = msbt.Msbt(out)
        assert all(c.text(k) == v for k, v in old.items()) and c.text(lab) == a.title
        dst = os.path.join(a.out, 'ui', 'message', 'menu.msbt')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(out)
        log.append('ui/message/menu.msbt: %s = %r' % (lab, a.title))
    print('\n'.join(log))


if __name__ == '__main__':
    main()
