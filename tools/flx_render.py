#!/usr/bin/env python3
"""Render a frame of a Smash 4 HUD movie (tools/flx.py) to PNG, with its textures (texlist.lst +
img-NNNNN.nut in the same folder), for checking edits by eye.

  python3 tools/flx_render.py DIR_OR_FLX OUT.png [SPRITE[:FRAME]] [PATH=FRAME ...] [--scale S] [--bg RRGGBB]

SPRITE defaults to 0 (the root, drawn on the stage); other sprites are cropped to their bounds.
FRAME is a number or a label. Children play from the frame they appear on and stop at the first
frame with an action (the samples' actions look like stop(); their bodies are not in the file);
PATH=FRAME forces one (FRAME '-' hides it): PATH is an instance name ('ko_mc'), the end of a path
('dmg_1/ko_mc'; * wildcards, e.g. 'col_1/*' for all of col_1's descendants that have the label)
or '#SPRITE'. --bg RRGGBB fills the background (default transparent).
Images on run-time textures (fighter portraits, stock icons, rendered text) are grey boxes.
Blend 9 is drawn additive.
"""
import fnmatch
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flx  # noqa: E402
import nut  # noqa: E402


def _mul(m, n):
    """affine m after n, both (a, b, c, d, tx, ty)"""
    a, b, c, d, tx, ty = m
    a2, b2, c2, d2, tx2, ty2 = n
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2,
            a * tx2 + c * ty2 + tx, b * tx2 + d * ty2 + ty)


def _ctx(parent, col):
    """colour transforms as RGBA (mul 0-1, add 0-255); parent applied after col"""
    m = np.array([col.mul[1], col.mul[2], col.mul[3], col.mul[0]], np.float32) / 100.0
    a = np.array([col.add[1], col.add[2], col.add[3], col.add[0]], np.float32)
    pm, pa = parent
    return m * pm, a * pm + pa


IDENT_CT = (np.ones(4, np.float32), np.zeros(4, np.float32))


class Movie:
    def __init__(self, path):
        if os.path.isdir(path):
            path = os.path.join(path, [n for n in os.listdir(path) if n.endswith('.flx')][0])
        self.dir = os.path.dirname(path)
        self.f = flx.read(open(path, 'rb').read())
        tl = os.path.join(self.dir, 'texlist.lst')
        self.tlst = flx.Tlst(open(tl, 'rb').read()) if os.path.exists(tl) else flx.Tlst()
        self._tex, self._img = {}, {}

    def texture(self, slot):
        if slot not in self._tex:
            p = os.path.join(self.dir, 'img-%05d.nut' % slot)
            img = None
            if os.path.exists(p):
                d, texs = nut.load(p)
                t = texs[0]
                img = nut.decode(d, t).astype(np.float32)
                fmt = t.fmt & 0x3F
                if fmt == 0x35:      # BC5: luminance, alpha
                    img = np.stack([img[..., 0]] * 3 + [img[..., 1]], -1)
                elif fmt == 0x34:    # BC4: alpha only
                    img = np.stack([np.full_like(img[..., 0], 255)] * 3 + [img[..., 0]], -1)
            self._tex[slot] = img
        return self._tex[slot]

    def image(self, idx):
        """RGBA float array of image symbol idx (grey box when its texture is not a file)"""
        if idx not in self._img:
            e = self.tlst.find(self.f.images[idx])
            tex = self.texture(e.tex) if e else None
            if tex is None:
                w, h = (e.w, e.h) if e else (32, 32)
                img = np.zeros((max(h, 1), max(w, 1), 4), np.float32)
                img[...] = (128, 128, 128, 110)
                img[:2], img[-2:], img[:, :2], img[:, -2:] = 200, 200, 200, 200
            else:
                th, tw = tex.shape[:2]
                x0, y0 = int(round(e.u0 * tw)), int(round(e.v0 * th))
                x1, y1 = int(round(e.u1 * tw)), int(round(e.v1 * th))
                img = tex[y0:y1, x0:x1]
            self._img[idx] = img
        return self._img[idx]

    # ---- display list traversal
    def _child_frame(self, parent, pframe, place, path, over):
        """frame of a child instance (None = hidden)"""
        f = self.f
        sp = f.sprites[place.char]
        labels = f.sprite_labels(place.char)
        for k, v in over.items():
            if k == '#%d' % place.char or fnmatch.fnmatchcase(path, k) or fnmatch.fnmatchcase(path, '*/' + k):
                if v == '-':
                    return None
                if isinstance(v, int) or v in labels:
                    return labels[v] if isinstance(v, str) else v
        # frames since this instance (same slot, same sprite) appeared in the parent
        ps = f.sprites[parent]
        start = pframe
        while start > 0:
            k = f.keys[ps.key0 + f.frames[ps.frame0 + start - 1]]
            if not any(f.places[i].slot == place.slot and f.places[i].char == place.char for i in k.places):
                break
            start -= 1
        fr = 0
        for _ in range(pframe - start):
            if f.keys[sp.key0 + f.frames[sp.frame0 + fr]].action != flx.NONE16 or fr + 1 >= sp.nframes:
                break
            fr += 1
        return fr

    def ops(self, sprite=0, frame=0, over=None, m=(1, 0, 0, 1, 0, 0), ct=IDENT_CT, blend=0, path='',
            depth=0):
        """[(image index, matrix image px -> out, colour transform, blend)] bottom first"""
        f, over = self.f, over or {}
        if isinstance(frame, str):
            frame = f.sprite_labels(sprite)[frame]
        out = []
        if depth > 32:
            return out
        for pi in reversed(f.frame_key(sprite, frame).places):
            p = f.places[pi]
            if p.kind in (flx.KIND_IMAGE, flx.KIND_TEXT):
                r = f.infos[p.info]
                if p.kind == flx.KIND_TEXT:
                    t = f.texts[p.char]
                    fmt = f.formats[t.fmt]
                    nm = f.strings[fmt.text]
                    if nm not in f.images:
                        continue
                    idx = f.images.index(nm)
                else:
                    idx = p.char
                img = self.image(idx)
                ih, iw = img.shape[:2]
                out.append((idx, _mul(m, (r.w / iw, 0, 0, r.h / ih, r.x, r.y)), ct, blend))
            else:
                name = f.instance_name(p) or '#%d' % p.char
                cpath = (path + '/' if path else '') + name
                cm = _mul(m, f.transforms[p.xform].matrix()) if p.xform != flx.NONE16 else m
                cc = _ctx(ct, f.colors[p.color]) if p.color != flx.NONE16 else ct
                cf = self._child_frame(sprite, frame, p, cpath, over)
                if cf is None:
                    continue
                out += self.ops(p.char, cf, over, cm, cc, p.blend or blend, cpath, depth + 1)
        return out

    def render(self, sprite=0, frame=0, over=None, scale=1.0, background=(0, 0, 0, 0)):
        ops = self.ops(sprite, frame, over)
        if sprite == 0:
            x0, y0, x1, y1 = 0, 0, self.f.width, self.f.height
        else:
            pts = []
            for idx, m, ct, bl in ops:
                ih, iw = self.image(idx).shape[:2]
                for u, v in ((0, 0), (iw, 0), (0, ih), (iw, ih)):
                    pts.append((m[0] * u + m[2] * v + m[4], m[1] * u + m[3] * v + m[5]))
            if not pts:
                pts = [(0, 0)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            x0, y0, x1, y1 = min(xs) - 4, min(ys) - 4, max(xs) + 4, max(ys) + 4
        W, H = max(1, int(math.ceil((x1 - x0) * scale))), max(1, int(math.ceil((y1 - y0) * scale)))
        canvas = np.zeros((H, W, 4), np.float32)
        canvas[...] = background
        canvas[..., :3] *= canvas[..., 3:] / 255.0          # premultiplied
        view = (scale, 0, 0, scale, -x0 * scale, -y0 * scale)
        for idx, m, ct, bl in ops:
            self._draw(canvas, self.image(idx), _mul(view, m), ct, bl)
        a = canvas[..., 3:]
        rgb = np.where(a > 0, canvas[..., :3] * 255.0 / np.maximum(a, 1e-6), 0)
        return Image.fromarray(np.clip(np.concatenate([rgb, a], -1), 0, 255).astype(np.uint8), 'RGBA')

    @staticmethod
    def _draw(canvas, img, m, ct, blend):
        H, W = canvas.shape[:2]
        ih, iw = img.shape[:2]
        corners = [(m[0] * u + m[2] * v + m[4], m[1] * u + m[3] * v + m[5]) for u, v in
                   ((0, 0), (iw, 0), (0, ih), (iw, ih))]
        bx0 = max(0, int(math.floor(min(c[0] for c in corners))))
        by0 = max(0, int(math.floor(min(c[1] for c in corners))))
        bx1 = min(W, int(math.ceil(max(c[0] for c in corners))))
        by1 = min(H, int(math.ceil(max(c[1] for c in corners))))
        det = m[0] * m[3] - m[1] * m[2]
        if bx1 <= bx0 or by1 <= by0 or abs(det) < 1e-9:
            return
        ia, ib, ic, id_ = m[3] / det, -m[1] / det, -m[2] / det, m[0] / det
        # output pixel centre -> image coords
        ys, xs = np.mgrid[by0:by1, bx0:bx1].astype(np.float32) + 0.5
        dx, dy = xs - m[4], ys - m[5]
        u = ia * dx + ic * dy - 0.5
        v = ib * dx + id_ * dy - 0.5
        inside = (u > -1) & (u < iw) & (v > -1) & (v < ih)
        u0 = np.floor(u).astype(np.int32)
        v0 = np.floor(v).astype(np.int32)
        fu, fv = (u - u0)[..., None], (v - v0)[..., None]

        def tap(x, y):
            ok = (x >= 0) & (x < iw) & (y >= 0) & (y < ih)
            px = img[np.clip(y, 0, ih - 1), np.clip(x, 0, iw - 1)]
            return px * ok[..., None]
        src = (tap(u0, v0) * (1 - fu) * (1 - fv) + tap(u0 + 1, v0) * fu * (1 - fv) +
               tap(u0, v0 + 1) * (1 - fu) * fv + tap(u0 + 1, v0 + 1) * fu * fv)
        src = np.clip(src * ct[0] + ct[1] * (src[..., 3:] > 0), 0, 255) * inside[..., None]
        a = src[..., 3:] / 255.0
        dst = canvas[by0:by1, bx0:bx1]
        if blend == 9:
            dst[..., :3] += src[..., :3] * a
        else:
            dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
            dst[..., 3:] = src[..., 3:] + dst[..., 3:] * (1 - a)
        np.clip(dst, 0, 255, out=dst)


def main():
    args = [a for a in sys.argv[1:]]
    scale = 1.0
    if '--scale' in args:
        i = args.index('--scale')
        scale = float(args[i + 1])
        del args[i:i + 2]
    bg = (0, 0, 0, 0)
    if '--bg' in args:
        i = args.index('--bg')
        v = int(args[i + 1], 16)
        bg = (v >> 16, v >> 8 & 255, v & 255, 255)
        del args[i:i + 2]
    if len(args) < 2:
        print(__doc__)
        return
    mv = Movie(args[0])
    sprite, frame = 0, 0
    over = {}
    for a in args[2:]:
        if '=' in a:
            k, v = a.split('=', 1)
            over[k] = int(v) if v.isdigit() else v
        else:
            s, _, fr = a.partition(':')
            sprite = int(s)
            frame = int(fr) if fr.isdigit() else (fr or 0)
    mv.render(sprite, frame, over, scale, bg).save(args[1])


if __name__ == '__main__':
    main()
