#!/usr/bin/env python3
"""Greninja's neutral air as it looks with burn v2 (fighters/gekkouga/README.md "Burn v2"): his model posed in
AttackAirN with his effect script's effects drawn by tools/fx_render.py (the game's own vertex / pixel programs on
eft's uniform blocks: the water burst 0x330000B and the two new flames 0x330001B), a contact sheet and a GIF.

  python3 -I tools/gekkouga_nair_preview.py VANILLA_FIGHTER BUILT_FIGHTER OUT_DIR [--frames 9,11,13,16,20,24]

VANILLA_FIGHTER: his vanilla fighter/gekkouga (model/body/c00, motion/body/main.pac); BUILT_FIGHTER: the package's
fighter/gekkouga (effect/gekkouga, script/animcmd/body/effect.bin). Writes OUT_DIR/nair.png and nair.gif.

The model: model.nud's meshes (the default eyes; the other expression meshes and the burn-face mesh hidden), linear
blend skinned from model.vbn's rest pose to the motion's frame (tools/omo.py world: the game's reading), its colour
texture (model.nut) with a plain lambert light and a little ambient: no NU_ shaders (specular, rim, AO, normal maps),
no swing bones (the tongue / water drops at their animation's keys only). The effects: fx_render's Smash 4 side
(emission, motion, flipbooks and colours through the programs), drawn over the model without a depth test against
it; the burst's refraction emitter (ring3_rif, a distortion pass) isn't drawn. Camera: the side view, facing right,
no pitch, no bloom / HDR.
"""
import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import fbx_anim as FA  # noqa: E402
import fx_render as F  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
import ptcl  # noqa: E402

MOTION = 'FitGekkougaBodyMainC05AttackAirN.omo'
SHOW = ('Gamemodel', 'Gekkouga_Eye_VIS_O_OBJ')
BG = np.array([0.07, 0.07, 0.09])
VIEW = (-24.0, 24.0, -6.0, 30.0)
PPU = 8.0
LIGHT = np.array([-0.45, 0.6, 0.65])


def rigged_weights(p):
    """(bone ids [n, 4], weights [n, 4]) of a rigged polygon (its vertex add section's tail)"""
    vs = p.vert_size
    st = nud._vertex_add_stride(vs)
    nb = st - {1: 32, 2: 16, 4: 8}[vs >> 4]
    d = DATA[0]
    a = np.frombuffer(d, np.uint8, p.nv * st, p.vaoff).reshape(p.nv, st)
    t = a[:, nb:]
    if vs >> 4 == 4:
        return t[:, :4].astype(int), t[:, 4:8].astype(np.float64) / 255.0
    if vs >> 4 == 2:
        return t[:, :8].copy().view('>u2').astype(int), t[:, 8:16].copy().view('>f2').astype(np.float64)
    return t[:, :16].copy().view('>u4').astype(int), t[:, 16:32].copy().view('>f4').astype(np.float64)


DATA = [None]


def model_items(vdir):
    mdir = os.path.join(vdir, 'model', 'body', 'c00')
    path = os.path.join(mdir, 'model.nud')
    DATA[0] = open(path, 'rb').read()
    meshes = nud.read(path)
    dn, texs = nut.load(os.path.join(mdir, 'model.nut'))
    images = {t.tex_id: nut.decode(dn, t) for t in texs}
    bones = omo.vbn_read(os.path.join(mdir, 'model.vbn'))
    rest = FA.vbn_rest(os.path.join(mdir, 'model.vbn'))
    bind = []
    for n, par, _h in bones:
        bind.append(rest[n] if not 0 <= par < len(bones) else bind[par] @ rest[n])
    items = []
    for m in meshes:
        if m.name not in SHOW:
            continue
        for p in m.polygons:
            if not p.materials or p.materials[0].src:          # opaque body only (the blended overlays left out)
                continue
            tid = p.materials[0].textures[0]['hash']
            if p.pos is None:
                pos, nrm = p.rpos, p.rnrm
                bi, bw = rigged_weights(p)
            else:
                pos, nrm = p.pos, p.nrm if p.nrm is not None else np.zeros_like(p.pos)
                bi = np.full((len(pos), 1), m.bone)
                bw = np.ones((len(pos), 1))
            idx = p.idx
            if p.strip:
                tri = []
                for k in range(len(idx) - 2):
                    a, b, c = idx[k], idx[k + 1], idx[k + 2]
                    if 0xFFFF in (a, b, c) or a == b or b == c or a == c:
                        continue
                    tri.append((a, b, c) if k % 2 == 0 else (b, a, c))
                tri = np.array(tri)
            else:
                tri = idx.reshape(-1, 3)
            uv = p.uvs[0] if p.uvs else np.zeros((len(pos), 2))
            items.append(dict(pos=pos, nrm=nrm, bi=bi, bw=bw, tri=tri, uv=uv, img=images.get(tid)))
    return items, bones, bind


def pose(items, bones, bind, o, fr):
    w = omo.world(o, bones, fr)
    skin = [np.array(w[n]) @ np.linalg.inv(bind[i]) for i, (n, _p, _h) in enumerate(bones)]
    out = []
    for it in items:
        P = np.c_[it['pos'], np.ones(len(it['pos']))]
        Nn = np.c_[it['nrm'], np.zeros(len(it['pos']))]
        pos = np.zeros((len(P), 3))
        nrm = np.zeros((len(P), 3))
        tot = it['bw'].sum(1)
        for j in range(it['bi'].shape[1]):
            for b in np.unique(it['bi'][:, j]):
                sel = it['bi'][:, j] == b
                if not 0 <= b < len(skin):
                    continue
                pos[sel] += it['bw'][sel, j:j + 1] * (skin[b] @ P[sel].T).T[:, :3]
                nrm[sel] += it['bw'][sel, j:j + 1] * (skin[b] @ Nn[sel].T).T[:, :3]
        t = np.maximum(tot, 1e-6)[:, None]
        out.append(dict(it, pos=pos / t, nrm=nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)))
    return out


def draw_model(c, posed):
    """onto fx_render's canvas (screen x = his Z, y = Y; depth -X): textured, lambert, z-buffered"""
    zb = np.full((c.h, c.w), -1e9)
    L = LIGHT / np.linalg.norm(LIGHT)
    for it in posed:
        p = it['pos']
        sx = (p[:, 2] - c.x0) * c.ppu
        sy = (c.y1 - p[:, 1]) * c.ppu
        sz = -p[:, 0]
        img = it['img']
        h, w = img.shape[:2]
        shade = 0.35 + 0.75 * np.clip(it['nrm'] @ L, 0, 1)
        for t in it['tri']:
            x0, y0 = sx[t], sy[t]
            area = (x0[1] - x0[0]) * (y0[2] - y0[0]) - (x0[2] - x0[0]) * (y0[1] - y0[0])
            if abs(area) < 1e-9:
                continue
            lx, hx = int(max(0, x0.min())), int(min(c.w - 1, x0.max()) + 1)
            ly, hy = int(max(0, y0.min())), int(min(c.h - 1, y0.max()) + 1)
            if hx <= lx or hy <= ly:
                continue
            ys, xs = np.mgrid[ly:hy, lx:hx] + 0.5
            w0 = ((x0[1] - xs) * (y0[2] - ys) - (x0[2] - xs) * (y0[1] - ys)) / area
            w1 = ((x0[2] - xs) * (y0[0] - ys) - (x0[0] - xs) * (y0[2] - ys)) / area
            w2 = 1 - w0 - w1
            ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            z = w0 * sz[t[0]] + w1 * sz[t[1]] + w2 * sz[t[2]]
            u = w0 * it['uv'][t[0], 0] + w1 * it['uv'][t[1], 0] + w2 * it['uv'][t[2], 0]
            v = w0 * it['uv'][t[0], 1] + w1 * it['uv'][t[1], 1] + w2 * it['uv'][t[2], 1]
            sh = w0 * shade[t[0]] + w1 * shade[t[1]] + w2 * shade[t[2]]
            yi, xi = (ys - 0.5).astype(int), (xs - 0.5).astype(int)
            sel = ins & (z > zb[yi, xi])
            if not sel.any():
                continue
            tx = np.clip((np.mod(u, 1.0) * w).astype(int), 0, w - 1)
            ty = np.clip((np.mod(v, 1.0) * h).astype(int), 0, h - 1)
            texel = img[ty, tx].astype(np.float64) / 255.0
            zb[yi[sel], xi[sel]] = z[sel]
            c.rgb[yi[sel], xi[sel]] = texel[sel][:, :3] * sh[sel][:, None]


def effects(bdir):
    edir = os.path.join(bdir, 'effect', 'gekkouga')
    p = ptcl.Ptcl(open(os.path.join(edir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ef = EFC.Efc(open(os.path.join(edir, 'gekkouga.010d0000.efc'), 'rb').read())
    calls = F.s4_calls(os.path.join(bdir, 'script', 'animcmd', 'body', 'effect.bin'), 'AttackAirN')
    s4, programs = {}, {}
    for _f, gid, *_r in calls:
        i = int(gid) & 0xFFFF
        if int(gid) not in s4:
            s4[int(gid)] = F.s4_emitters(p, ef.entries[i][1] - 1, programs)
    return calls, s4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vanilla')
    ap.add_argument('built')
    ap.add_argument('out')
    ap.add_argument('--frames', default='9,11,13,15,18,22')
    a = ap.parse_args()
    from PIL import Image, ImageDraw
    frames = [int(x) for x in a.frames.split(',')]
    items, bones, bind = model_items(a.vanilla)
    o = omo.Omo(dict(omo.pac_read(os.path.join(a.vanilla, 'motion', 'body', 'main.pac')))[MOTION])
    calls, s4 = effects(a.built)
    allf = list(range(min(frames), max(frames) + 1))
    gif_frames = list(range(6, 30))
    want = sorted(set(frames) | set(gif_frames))
    canv = {}
    for fr in want:
        c = F.Canvas(*VIEW, PPU)
        c.rgb[:] = BG
        draw_model(c, pose(items, bones, bind, o, min(fr, o.frames - 1)))
        canv[fr] = c
    for k, (fr0, gid, bone, xyz, rot, size, off) in enumerate(calls):
        cm = F.call_matrix(xyz, rot, size)
        for j, em in enumerate(s4[int(gid)]):
            sim = F.simulate(em, (fr0, cm, size, off), want, seed=10 * k + j + 1)
            for fr in want:
                if sim[fr]:
                    if not F.draw_s4(canv[fr], em, sim[fr], cm @ F.emitter_matrix(em, fr - fr0), float(fr - fr0)):
                        F.draw(canv[fr], em, sim[fr], cm)
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
    ImageDraw.Draw(sheet).text((6, 5), 'Greninja neutral air (burn v2): water burst 0x330000B + flames 0x330001B (Z +- 10, '
                               'Y 8.5) from frame 11, ended at 24; offline render (see notes)', fill=(220, 220, 220))
    sheet.save(os.path.join(a.out, 'nair.png'))
    gif = [Image.fromarray(canv[fr].image()).convert('P', palette=Image.ADAPTIVE) for fr in gif_frames]
    gif[0].save(os.path.join(a.out, 'nair.gif'), save_all=True, append_images=gif[1:], duration=50, loop=0)
    print(os.path.join(a.out, 'nair.png'))


if __name__ == '__main__':
    main()
