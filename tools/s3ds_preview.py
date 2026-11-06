#!/usr/bin/env python3
"""Contact sheet of converted Smash Run enemies (tools/s3ds_enemy.py), rendered from the written files: the
model's meshes (3DS .mbn geometry and UVs, the objects the .bch shows by default), textured from the written
model.nut (as the NUD samples it: V' = 1 - V), posed with a frame of the written main.pac OMOs (omo.world,
the game's reading). No lighting; alpha-tested / blended materials drawn with their alpha test only.

  python3 tools/s3ds_preview.py SRC_ROOT OUT_ROOT SHEET.png [KIND...] [--frame N] [--size 160]
"""
import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nut  # noqa: E402
import nud  # noqa: E402,F401
import omo  # noqa: E402
import s3ds_enemy as se  # noqa: E402
import s3ds_model as sm  # noqa: E402


def nud_materials(path):
    """[(color texture id, alpha_func, ref, src, dst, props, wrap s, wrap t)] a mesh, in mesh order (reads the
    material header of each mesh's first polygon)"""
    d = open(path, 'rb').read()
    nmesh = struct.unpack('>h', d[0xA:0xC])[0]
    pstart, psize, vsize, vasize = struct.unpack('>iiii', d[0x10:0x20])
    sbase = 0x30 + pstart + psize + vsize + vasize
    out = []
    for i in range(nmesh):
        o = 0x30 + 0x30 * i
        npoly, obj = struct.unpack('>hi', d[o + 42:o + 48])
        q = obj
        mo = struct.unpack('>i', d[q + 16:q + 20])[0]
        m = nud._read_material(d, mo, sbase)
        out.append((m.textures[0]['hash'], m.alpha_func, m.ref_alpha, m.src, m.dst, dict(m.props),
                    m.textures[0]['wrap_s'], m.textures[0]['wrap_t']))
    return out


def nud_uv(uv, props):
    """a NUD mesh's UVs as its shader transforms them (the texas_cross.nsh vertex programs): effect materials
    (NU_effRotUV / ScaleUV / TransUV) rotate about the centre, translate, then scale (V about its top edge);
    body materials (NU_colorSamplerUV) U = s.x (u + t.x), V = s.y (V' + t.y)"""
    if 'NU_effScaleUV' in props:
        r = props.get('NU_effRotUV', [0.0])[0]
        s, t = props['NU_effScaleUV'], props.get('NU_effTransUV', [0.0, 0.0])
        c, n = np.cos(r), np.sin(r)
        a, b = uv[:, 0] - 0.5, uv[:, 1] - 0.5
        ur, vr = c * a + n * b + 0.5, -n * a + c * b + 0.5
        return np.c_[(ur + t[0]) * s[0], 1 - s[1] * (1 - (vr + t[1]))]
    s = props.get('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0])
    return np.c_[s[0] * (uv[:, 0] + s[2]), s[1] * (uv[:, 1] + s[3])]


def _wrap(x, mode):
    if mode == 1:
        return np.mod(x, 1.0)
    if mode == 2:
        x = np.mod(x, 2.0)
        return np.where(x > 1, 2 - x, x)
    return np.clip(x, 0, 1)


def render(items, size, yaw):
    """items: [(positions [n, 3], uvs [n, 2] (NUD), tris, image, (alpha_func, ref, src, dst), wrap)]"""
    allp = np.concatenate([p for p, *_ in items]) if items else np.zeros((1, 3))
    th = np.radians(yaw)
    R = np.array([[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]])
    q = allp @ R.T
    lo, hi = q.min(0), q.max(0)
    span = max(hi[0] - lo[0], hi[1] - lo[1], 1e-3) * 1.1
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    can = np.zeros((size, size, 3), np.float64) + 40
    zb = np.full((size, size), -1e9)
    order = sorted(items, key=lambda it: it[4][2] != 0)          # opaque first
    for pos, uv, tri, img, (af, ref, src, dst), wrap in order:
        qq = pos @ R.T
        sx = ((qq[:, 0] - cx) / span + 0.5) * size
        sy = (0.5 - (qq[:, 1] - cy) / span) * size
        sz = qq[:, 2]
        h, w = img.shape[:2]
        for t in tri:
            x0, y0 = sx[t], sy[t]
            area = (x0[1] - x0[0]) * (y0[2] - y0[0]) - (x0[2] - x0[0]) * (y0[1] - y0[0])
            if area >= 0:
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
            u = w0 * uv[t[0], 0] + w1 * uv[t[1], 0] + w2 * uv[t[2], 0]
            v = w0 * uv[t[0], 1] + w1 * uv[t[1], 1] + w2 * uv[t[2], 1]
            tx = np.clip((_wrap(u, wrap[0]) * w).astype(int), 0, w - 1)
            ty = np.clip((_wrap(v, wrap[1]) * h).astype(int), 0, h - 1)
            yi, xi = (ys - 0.5).astype(int), (xs - 0.5).astype(int)
            texel = img[ty, tx].astype(np.float64)
            a = texel[..., 3] / 255
            sel = ins & (z > zb[yi, xi])
            if af:
                sel &= texel[..., 3] > ref if af == 516 else texel[..., 3] >= ref
            if src:
                if dst == 2:
                    can[yi[sel], xi[sel]] += texel[sel][:, :3] * a[sel][:, None]
                else:
                    can[yi[sel], xi[sel]] = can[yi[sel], xi[sel]] * (1 - a[sel][:, None]) + texel[sel][:, :3] * a[sel][:, None]
                continue
            zb[yi[sel], xi[sel]] = z[sel]
            can[yi[sel], xi[sel]] = texel[sel][:, :3]
    return np.clip(can, 0, 255).astype(np.uint8)


def enemy_items(src, out, kind, part='body', c='c00', motion=None, frame=0):
    d3 = os.path.join(src, 'enemy', kind, 'model', part, c)
    od = os.path.join(out, 'model', 'enemy', kind, part, c)
    bch = sm.Bch(open(os.path.join(d3, 'normal.bch'), 'rb').read())
    mbn = sm.read_mbn(open(os.path.join(d3, 'normal.mbn'), 'rb').read())
    model = bch.models()[0]
    bones = model['bones']
    bind = []
    for b in bones:
        m = se.local_matrix(b['scale'], b['rot'], b['pos'])
        bind.append(m if b['parent'] < 0 else bind[b['parent']] @ m)
    mats = [np.eye(4)] * len(bones)
    if motion:
        pac = os.path.join(out, 'motion', 'enemy', kind, part, 'main.pac')
        if os.path.exists(pac):
            entries = dict(omo.pac_read(pac))
            name = motion if motion in entries else next((n for n in sorted(entries) if motion.lower() in n.lower()),
                                                          sorted(entries)[0] if entries else None)
            if name:
                o = omo.Omo(entries[name])
                w = omo.world(o, omo.vbn_read(os.path.join(od, 'model.vbn')), min(frame, o.frames - 1))
                mats = [np.array(w[b['name']]) @ np.linalg.inv(bind[i]) for i, b in enumerate(bones)]
    dn, texs = nut.load(os.path.join(od, 'model.nut'))
    images = {t.tex_id: nut.decode(dn, t) for t in texs}
    nmats = nud_materials(os.path.join(od, 'model.nud'))
    items = []
    k = 0
    for obj, mi in zip(model['objects'], sm.match_objects(model['objects'], mbn)):
        me = mbn[mi]
        if obj['silhouette']:
            continue
        tid, af, ref, srcf, dstf, suv, ws, wt = nmats[k]
        k += 1
        if not (model['visibility'] >> obj['node']) & 1:
            continue
        a = me['attrs']
        uv = a[3] if 3 in a else np.zeros((me['count'], 2))
        uvn = np.c_[uv[:, 0], 1.0 - uv[:, 1]]
        uvn = nud_uv(uvn, suv)
        P = np.c_[a[0], np.ones(me['count'])]
        for bl, idx in me['parts']:
            bi = a[5].astype(int)
            bw = a[6]
            pos = np.zeros((me['count'], 3))
            for j in range(bi.shape[1]):
                bj = np.asarray(bl)[np.minimum(bi[:, j], len(bl) - 1)]
                for b in np.unique(bj):
                    sel = bj == b
                    pos[sel] += bw[sel, j:j + 1] * (mats[b] @ P[sel].T).T[:, :3]
            tot = bw.sum(1, keepdims=True)
            pos = np.where(tot > 1e-6, pos / np.maximum(tot, 1e-6), a[0])
            items.append((pos, uvn, idx.reshape(-1, 3), images[tid], (af, ref, srcf, dstf), (ws, wt)))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('sheet')
    ap.add_argument('kinds', nargs='*')
    ap.add_argument('--motion', default=None, help='a motion name (or part of one) to pose with')
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--size', type=int, default=160)
    ap.add_argument('--yaw', type=float, default=30)
    ap.add_argument('--cols', type=int, default=10)
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    kinds = a.kinds or sorted(os.listdir(os.path.join(a.out, 'model', 'enemy')))
    tiles = []
    for k in kinds:
        for part in sorted(os.listdir(os.path.join(a.out, 'model', 'enemy', k))):
            try:
                img = render(enemy_items(a.src, a.out, k, part, motion=a.motion, frame=a.frame), a.size, a.yaw)
            except Exception as e:                       # noqa: BLE001 - one bad tile shouldn't stop the sheet
                img = np.zeros((a.size, a.size, 3), np.uint8)
                print('%s/%s: %r' % (k, part, e))
            im = Image.fromarray(img)
            ImageDraw.Draw(im).text((3, 2), k if part == 'body' else '%s/%s' % (k, part), fill=(255, 255, 0))
            tiles.append(np.asarray(im))
    rows = []
    for i in range(0, len(tiles), a.cols):
        r = tiles[i:i + a.cols]
        r += [np.zeros_like(tiles[0])] * (a.cols - len(r))
        rows.append(np.concatenate(r, 1))
    Image.fromarray(np.concatenate(rows, 0)).save(a.sheet)
    print('%d tiles -> %s' % (len(tiles), a.sheet))


if __name__ == '__main__':
    main()
