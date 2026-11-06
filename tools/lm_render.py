#!/usr/bin/env python3
"""Render a frame of a Lumen menu movie (.lm, with its texlist.lst / img-NNNNN.nut) to PNG, for checking edits
by eye (as tools/flx_render.py does for the HUD movies).

  python3 tools/lm_render.py DIR_OR_LM OUT.png [ROOT_FRAME|LABEL] [--scale S] [--bg RRGGBB] [--boxes]

Read with tools/chara_layout.py: shapes (F022 + F024 graphics: atlas, fill, x y u v vertices, u16 indices; atlas
N = img-0000N.nut), sprites (0x27: frames 0x01 of place 0x04 / remove 0x05, labels 0x2B), texts (0x25: drawn as
grey boxes with their name), transforms F003 (a b c d x y) / positions F103, colours F002 (4 x u16, 256 = 1).
A sprite's display list is played from frame 0 to the frame shown (place mode 1 adds, 2 changes the object at that
depth; remove takes the depth away). A child sprite shows the frame labelled with the nearest ancestor instance
name it has a label for (the menus' buttons do gotoAndStop(_parent._name)), else its first frame. Scripts are not
run. --boxes outlines every named instance with its name.
"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chara_layout as cl  # noqa: E402
import nut  # noqa: E402

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mul(m, n):
    """m after n (both a b c d tx ty: x' = a x + c y + tx, y' = b x + d y + ty)"""
    a, b, c, d, tx, ty = m
    e, f, g, h, ux, uy = n
    return (a * e + c * f, b * e + d * f, a * g + c * h, b * g + d * h, a * ux + c * uy + tx, b * ux + d * uy + ty)


class Movie:
    def __init__(self, path):
        d = path if os.path.isdir(path) else os.path.dirname(path)
        lm_path = path if not os.path.isdir(path) else next(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.lm'))
        self.lm = cl.Lm(open(lm_path, 'rb').read())
        T = self.lm.tags
        self.pos = cl.table(T[self.lm.ti[cl.T_POSITIONS]][1], 2)
        self.xf = cl.table(T[self.lm.ti[cl.T_TRANSFORMS]][1], 6)
        b = T[self.lm.ti[0xF002]][1]
        n = struct.unpack('>I', b[:4])[0]
        self.colors = [np.array(struct.unpack('>4H', b[4 + 8 * i:12 + 8 * i]), float) / 256.0 for i in range(n)]
        self.tex = {}
        for f in os.listdir(d):
            if f.startswith('img-') and f.endswith('.nut'):
                dn, ts = nut.load(os.path.join(d, f))
                im = nut.decode(dn, ts[0]).astype(np.float32) / 255.0
                if ts[0].fmt & 0x3F == 0x35:        # BC5: luminance (R) and alpha (G)
                    im = np.dstack([im[..., 0], im[..., 0], im[..., 0], im[..., 1]])
                elif ts[0].fmt & 0x3F == 0x34:      # BC4: alpha, white
                    im = np.dstack([np.ones_like(im[..., 0])] * 3 + [im[..., 0]])
                self.tex[int(f[4:9])] = im
        self.shapes, self.sprites, self.texts = {}, {}, {}
        i = 0
        while i < len(T):
            t, body = T[i]
            w = cl.words(body)
            if t == 0xF022:
                graphics, j = [], i + 1
                while j < len(T) and T[j][0] == 0xF024:
                    graphics.append(self._graphic(T[j][1]))
                    j += 1
                self.shapes[w[0]] = graphics
                i = j
                continue
            if t == 0x25:
                self.texts[w[0]] = (self.lm.sy[w[2]] if w[2] < len(self.lm.sy) else '', w)
            if t == cl.T_SPRITE:
                frames, labels, j = [], {}, i + 1
                while j < len(T) and T[j][0] not in (cl.T_SPRITE, cl.T_END, 0xF022, 0x25):
                    tt, bb = T[j]
                    ww = cl.words(bb)
                    if tt == cl.T_LABEL:
                        labels[self.lm.sy[ww[0]]] = ww[1]
                    elif tt == cl.T_FRAME:
                        frames.append([T[k] for k in range(j + 1, j + 1 + ww[1])])
                        j += 1 + ww[1]
                        continue
                    elif tt == 0xF105:
                        j += 1 + ww[1]
                        continue
                    j += 1
                self.sprites[w[0]] = (frames, labels)
                i = j
                continue
            i += 1
        self.root = cl.words(T[self.lm.ti[0xF00C]][1])[3]
        cw = cl.words(T[self.lm.ti[0xF00C]][1])
        self.size = tuple(int(v) for v in struct.unpack('>2f', struct.pack('>2I', cw[8], cw[9])))

    def _graphic(self, b):
        atlas = struct.unpack('>I', b[:4])[0]
        fill, nv = struct.unpack('>HH', b[4:8])
        ni = struct.unpack('>I', b[8:12])[0]
        v = np.array(struct.unpack('>%df' % (4 * nv), b[12:12 + 16 * nv]), np.float32).reshape(nv, 4)
        idx = np.array(struct.unpack('>%dH' % ni, b[12 + 16 * nv:12 + 16 * nv + 2 * ni]), int).reshape(-1, 3)
        return atlas, fill, v, idx

    def matrix(self, i):
        if i == cl.NONE:
            return IDENT
        if i & cl.POS_FLAG:
            x, y = self.pos[i & 0xFFFF]
            return (1.0, 0.0, 0.0, 1.0, x, y)
        return tuple(self.xf[i])

    def display(self, cid, frame):
        """{depth: [char, name, matrix, colour mult, colour add]} after playing frames 0..frame of sprite cid"""
        frames, _ = self.sprites[cid]
        dl = {}
        for f in frames[:frame + 1]:
            for t, body in f:
                w = cl.words(body)
                if t == cl.T_PLACE:
                    depth, mode = w[5] >> 16, w[4] >> 16
                    name = self.lm.sy[w[3]] if w[3] else None
                    e = dl.get(depth)
                    if mode == 1 or e is None:
                        e = dl[depth] = [w[0], name, IDENT, None, None]
                    elif w[0] != 0xFFFFFFFF and w[0] != e[0] and mode != 2:
                        e[0] = w[0]
                    if name:
                        e[1] = name
                    if w[7] != cl.NONE or mode == 1:
                        e[2] = self.matrix(w[7])
                    if w[8] != cl.NONE and w[8] < len(self.colors):
                        e[3] = self.colors[w[8]]
                    if w[9] != cl.NONE and w[9] < len(self.colors):
                        e[4] = self.colors[w[9]]
                elif t == 0x05:
                    dl.pop(struct.unpack('>H', bytes(body[4:6]))[0], None)
        return dl

    def draw(self, img, cid, m, mulc, addc, path, frame, boxes):
        if cid in self.shapes:
            for atlas, fill, v, idx in self.shapes[cid]:
                xy = np.c_[v[:, 0] * m[0] + v[:, 1] * m[2] + m[4], v[:, 0] * m[1] + v[:, 1] * m[3] + m[5]]
                for tri in idx:
                    self.raster(img, xy[tri], v[tri, 2:4], self.tex.get(atlas), fill, mulc, addc)
            return
        if cid in self.texts:
            name, _w = self.texts[cid]
            p = [(m[4], m[5])]
            boxes.append(('text', name, p))
            return
        if cid not in self.sprites:
            return
        _frames, labels = self.sprites[cid]
        if frame is None:
            frame = 0
            for anc in reversed(path):
                if anc in labels:
                    frame = labels[anc]
                    break
        for depth in sorted(self.display(cid, frame)):
            c, name, mm, cm, ca = self.display(cid, frame)[depth]
            m2 = mul(m, mm)
            cm2 = mulc * (cm if cm is not None else 1.0)
            ca2 = addc + (ca if ca is not None else 0.0)
            if name and boxes is not None:
                boxes.append(('inst', name, [(m2[4], m2[5])]))
            self.draw(img, c, m2, cm2, ca2, path + ([name] if name else []), None, boxes)

    def raster(self, img, xy, uv, tex, fill, mulc, addc):
        h, w = img.shape[:2]
        x0, y0 = np.floor(xy.min(0)).astype(int)
        x1, y1 = np.ceil(xy.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
        if x0 >= x1 or y0 >= y1:
            return
        ys, xs = np.mgrid[y0:y1, x0:x1] + 0.5
        (ax, ay), (bx, by), (cx, cy) = xy
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            return
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not inside.any():
            return
        if tex is not None and fill != 0:
            u = l1 * uv[0, 0] + l2 * uv[1, 0] + l3 * uv[2, 0]
            v = l1 * uv[0, 1] + l2 * uv[1, 1] + l3 * uv[2, 1]
            th, tw = tex.shape[:2]
            px = np.clip((u * tw).astype(int), 0, tw - 1)
            py = np.clip((v * th).astype(int), 0, th - 1)
            col = tex[py, px]
        else:
            col = np.ones(xs.shape + (4,), np.float32)
        col = np.clip(col * mulc + addc, 0, 1)
        a = col[..., 3:4] * inside[..., None]
        reg = img[y0:y1, x0:x1]
        reg[..., :3] = reg[..., :3] * (1 - a) + col[..., :3] * a
        reg[..., 3:4] = reg[..., 3:4] * (1 - a) + a

    def render(self, frame=0, scale=1.0, bg=(0, 0, 0, 0), show_boxes=False):
        w, h = self.size
        img = np.zeros((h, w, 4), np.float32)
        img[...] = np.array(bg, np.float32) / 255.0
        boxes = []
        if isinstance(frame, str):
            frame = self.sprites[self.root][1][frame]
        self.draw(img, self.root, IDENT, np.ones(4, np.float32), np.zeros(4, np.float32), [], frame, boxes)
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA')
        dr = ImageDraw.Draw(out)
        for kind, name, p in boxes:
            if kind == 'text':
                x, y = p[0]
                dr.rectangle([x - 4, y - 4, x + 4, y + 4], outline=(255, 255, 0, 255))
                dr.text((x + 6, y - 6), name, fill=(255, 255, 0, 255))
            elif show_boxes and name:
                x, y = p[0]
                dr.text((x, y), name, fill=(0, 255, 255, 255))
        if scale != 1.0:
            out = out.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return out


def main():
    args = sys.argv[1:]
    scale, bg, boxes = 1.0, (0, 0, 0, 0), False
    if '--scale' in args:
        i = args.index('--scale')
        scale = float(args[i + 1])
        del args[i:i + 2]
    if '--bg' in args:
        i = args.index('--bg')
        v = int(args[i + 1], 16)
        bg = (v >> 16, v >> 8 & 255, v & 255, 255)
        del args[i:i + 2]
    if '--boxes' in args:
        args.remove('--boxes')
        boxes = True
    if len(args) < 2:
        raise SystemExit(__doc__)
    frame = args[2] if len(args) > 2 else 0
    frame = int(frame) if str(frame).isdigit() else frame
    Movie(args[0]).render(frame, scale, bg, boxes).save(args[1])


if __name__ == '__main__':
    main()
