#!/usr/bin/env python3
"""Renders a Smash 4 model folder (model.nud / model.nut / model.vbn, as the repo's readers read them) posed by an OMO
of a main.pac: a software rasterizer (textured with each material's colour texture and wrap, back faces culled as the
material says, a z-buffer, a Lambert light so the shape reads). Used to check converted models (tools/mdl0_to_nud.py,
tools/chr0_to_omo.py).

  python3 tools/nud_preview.py MODEL_DIR OUT.png [--pac main.pac --anim NAME[:FRAME]] [--yaw DEG] [--size 320]
  python3 tools/nud_preview.py MODEL_DIR OUT.gif --pac main.pac --anim NAME [--anim NAME ...] [--yaw DEG]
      a GIF of each animation in turn, every frame (labels in the corner)

The view: X right, Y up, looking along -Z (Smash 4's side camera); --yaw turns the model about Y first (90: a model
facing +Z seen facing right, as the game turns an article facing right).
"""
import argparse
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402

LIGHT = np.array([-0.4, 0.65, 0.65])
BG = (46, 48, 58)


def vbn_bind(path):
    """[(name, parent, hash)], [world bind 4x4]"""
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    bones = omo.vbn_read(path)
    off = 28 + 76 * n
    bind = []
    for i, (name, par, _h) in enumerate(bones):
        v = struct.unpack(e + '9f', d[off + 36 * i:off + 36 * i + 36])
        x, y, z = v[3:6]
        rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
        ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
        rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
        m = np.eye(4)
        m[:3, :3] = rz @ ry @ rx @ np.diag(v[6:9])
        m[:3, 3] = v[0:3]
        bind.append(m if not 0 <= par < len(bones) else bind[par] @ m)
    return bones, bind


def load(model_dir):
    path = os.path.join(model_dir, 'model.nud')
    data = open(path, 'rb').read()
    meshes = nud.read(path)
    dn, texs = nut.load(os.path.join(model_dir, 'model.nut'))
    images = {t.tex_id: nut.decode(dn, t) for t in texs}
    bones, bind = vbn_bind(os.path.join(model_dir, 'model.vbn'))
    items = []
    for m in meshes:
        for p in m.polygons:
            mat = p.materials[0]
            t0 = mat.textures[0]
            if p.pos is None:
                pos, nrm = p.rpos, p.rnrm
                vs = p.vert_size
                st = nud._vertex_add_stride(vs)
                nb = st - {1: 32, 2: 16, 4: 8}[vs >> 4]
                a = np.frombuffer(data, np.uint8, p.nv * st, p.vaoff).reshape(p.nv, st)[:, nb:]
                bi, bw = a[:, :4].astype(int), a[:, 4:8].astype(np.float64) / 255.0
            else:
                pos, nrm = p.pos, p.nrm if p.nrm is not None else np.tile([0.0, 1.0, 0.0], (len(p.pos), 1))
                bi, bw = np.full((len(pos), 1), max(m.bone, 0)), np.ones((len(pos), 1))
            items.append(dict(name=m.name, pos=pos, nrm=nrm, bi=bi, bw=bw, tri=p.idx.reshape(-1, 3),
                              uv=p.uvs[0] if p.uvs else np.zeros((len(pos), 2)), img=images[t0['hash']],
                              wrap=(t0['wrap_s'], t0['wrap_t']), cull=mat.cull))
    return items, bones, bind


def pose(items, bones, bind, o=None, fr=0):
    if o is None:
        skin = [np.eye(4) for _ in bones]
    else:
        w = omo.world(o, bones, fr)
        skin = [np.array(w[n]) @ np.linalg.inv(bind[i]) for i, (n, _p, _h) in enumerate(bones)]
    out = []
    for it in items:
        P = np.c_[it['pos'], np.ones(len(it['pos']))]
        Nn = np.c_[it['nrm'], np.zeros(len(it['pos']))]
        pos = np.zeros((len(P), 3))
        nrm = np.zeros((len(P), 3))
        for j in range(it['bi'].shape[1]):
            for b in np.unique(it['bi'][:, j]):
                sel = it['bi'][:, j] == b
                pos[sel] += it['bw'][sel, j:j + 1] * (skin[b] @ P[sel].T).T[:, :3]
                nrm[sel] += it['bw'][sel, j:j + 1] * (skin[b] @ Nn[sel].T).T[:, :3]
        t = np.maximum(it['bw'].sum(1), 1e-6)[:, None]
        out.append(dict(it, pos=pos / t, nrm=nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)))
    return out


def _wrap(x, mode):
    if mode == 1:
        return np.mod(x, 1.0)
    if mode == 2:
        x = np.mod(x, 2.0)
        return np.where(x > 1, 2 - x, x)
    return np.clip(x, 0, 1)


def draw(posed, size, view, yaw=0.0, floor=None):
    """view: (centre x, centre y, span) in units; floor: a y to draw a line at (the platform)"""
    can = np.zeros((size, size, 3)) + np.array(BG, float)
    zb = np.full((size, size), -1e9)
    th = math.radians(yaw)
    R = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    L = LIGHT / np.linalg.norm(LIGHT)
    cx, cy, span = view
    for it in posed:
        p = it['pos'] @ R.T
        n = it['nrm'] @ R.T
        sx = ((p[:, 0] - cx) / span + 0.5) * size
        sy = (0.5 - (p[:, 1] - cy) / span) * size
        sz = p[:, 2]
        img = it['img']
        h, w = img.shape[:2]
        shade = 0.45 + 0.65 * np.clip(n @ L, 0, 1)
        for t in it['tri']:
            x0, y0 = sx[t], sy[t]
            area = (x0[1] - x0[0]) * (y0[2] - y0[0]) - (x0[2] - x0[0]) * (y0[1] - y0[0])
            if abs(area) < 1e-9:
                continue
            # NUD triangles are counter-clockwise from the front; on this y-down screen that is a negative area
            if it['cull'] == 1029 and area > 0 or it['cull'] == 1028 and area < 0:
                continue
            lx, hx = int(max(0, x0.min())), int(min(size - 1, x0.max()) + 1)
            ly, hy = int(max(0, y0.min())), int(min(size - 1, y0.max()) + 1)
            if hx <= lx or hy <= ly:
                continue
            ys, xs = np.mgrid[ly:hy, lx:hx] + 0.5
            w0 = ((x0[1] - xs) * (y0[2] - ys) - (x0[2] - xs) * (y0[1] - ys)) / area
            w1 = ((x0[2] - xs) * (y0[0] - ys) - (x0[0] - xs) * (y0[2] - ys)) / area
            w2 = 1 - w0 - w1
            ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            z = w0 * sz[t[0]] + w1 * sz[t[1]] + w2 * sz[t[2]]
            yi, xi = (ys - 0.5).astype(int), (xs - 0.5).astype(int)
            sel = ins & (z > zb[yi, xi])
            if not sel.any():
                continue
            u = w0 * it['uv'][t[0], 0] + w1 * it['uv'][t[1], 0] + w2 * it['uv'][t[2], 0]
            v = w0 * it['uv'][t[0], 1] + w1 * it['uv'][t[1], 1] + w2 * it['uv'][t[2], 1]
            sh = w0 * shade[t[0]] + w1 * shade[t[1]] + w2 * shade[t[2]]
            tx = np.clip((_wrap(u, it['wrap'][0]) * w).astype(int), 0, w - 1)
            ty = np.clip((_wrap(v, it['wrap'][1]) * h).astype(int), 0, h - 1)
            texel = img[ty, tx].astype(np.float64)
            zb[yi[sel], xi[sel]] = z[sel]
            can[yi[sel], xi[sel]] = texel[sel][:, :3] * sh[sel][:, None]
    if floor is not None:
        fy = int((0.5 - (floor[0] - cy) / span) * size)
        x0 = int(((floor[1] - cx) / span + 0.5) * size)
        x1 = int(((floor[2] - cx) / span + 0.5) * size)
        if 0 <= fy < size:
            can[fy, max(0, x0):min(size, x1 + 1)] = (90, 230, 120)
    return np.clip(can, 0, 255).astype(np.uint8)


def label(img, text):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img)
    ImageDraw.Draw(im).text((4, 3), text, fill=(235, 235, 235))
    return np.asarray(im)


def fit(posed, yaw, pad=1.15):
    th = math.radians(yaw)
    R = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    q = np.concatenate([it['pos'] for it in posed]) @ R.T
    lo, hi = q.min(0), q.max(0)
    return ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, max(hi[0] - lo[0], hi[1] - lo[1]) * pad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model_dir')
    ap.add_argument('out')
    ap.add_argument('--pac')
    ap.add_argument('--anim', action='append', default=[])
    ap.add_argument('--yaw', type=float, default=0.0)
    ap.add_argument('--size', type=int, default=320)
    ap.add_argument('--span', type=float, default=None)
    a = ap.parse_args()
    items, bones, bind = load(a.model_dir)
    entries = dict(omo.pac_read(a.pac)) if a.pac else {}
    from PIL import Image
    if a.out.endswith('.gif'):
        frames = []
        view = None
        for an in a.anim:
            o = omo.Omo(entries[an if an.endswith('.omo') else an + '.omo'])
            for f in range(o.frames):
                ps = pose(items, bones, bind, o, f)
                view = view or fit(ps, a.yaw, 1.4)
                if a.span:
                    view = (view[0], view[1], a.span)
                frames.append(Image.fromarray(label(draw(ps, a.size, view, a.yaw), '%s %d' % (an, f))))
        frames[0].save(a.out, save_all=True, append_images=frames[1:], duration=33, loop=0)
        return
    if a.anim:
        an, _, fr = a.anim[0].partition(':')
        o = omo.Omo(entries[an if an.endswith('.omo') else an + '.omo'])
        ps = pose(items, bones, bind, o, int(fr or 0))
    else:
        ps = pose(items, bones, bind)
    view = fit(ps, a.yaw)
    Image.fromarray(draw(ps, a.size, view, a.yaw)).save(a.out)


if __name__ == '__main__':
    main()
