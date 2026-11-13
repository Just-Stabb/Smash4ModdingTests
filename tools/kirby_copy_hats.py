#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy hats: Ultimate's kirby/model/copy_brave_cap / copy_edge_cap (c00-c07) as Smash 4 hat
models (fighter/kirby/model/bravecap / edgecap/cNN: model.nud, metal.nud, model.nut, model.vbn and the rest of the
template hat's files). fighters/kirby/specials.md "Hero / Sephiroth copies".

  python3 tools/kirby_copy_hats.py ULT_KIRBY_MODEL_DIR S4_KIRBY_MODEL_DIR OUT_MODEL_DIR [--check]

ULT_KIRBY_MODEL_DIR: Ultimate's kirby/model (copy_brave_cap/, copy_edge_cap/, copy_reflet_cap/, body/c00). S4_KIRBY_MODEL_DIR:
Smash 4's fighter/kirby/model (refletcap/c00: the template hat whose vbn / jtb / sb / xmb / nhb / mta are copied;
mariocap/c00: the material template, its metal.nud). OUT_MODEL_DIR gets bravecap/c00-c07 and edgecap/c00-c07.

Placement (Visual fix v1; fighters/kirby/specials.md):
- Smash 4's hats are one bone (TopN) whose bind turn is Kirby's head-frame turn (euler (pi/2, 0, pi/2): local X up,
  shared by HipN ... BustN, NeckN, HeadN, BodyBN), at the origin, so the vertices are offsets in Kirby's world frame
  (Y up, X across, Z forward) from the bone the game puts the hat on. That bone sits at y 5.17 in the bind pose
  (BodyBN, the bone the whole body sphere, eyes and face are bound to; NeckN is at the same place), not at HeadN
  (6.37) as stage 1 assumed: vanilla hats hug Kirby's body sphere (centre y 5.28, radius 4.70) with that origin and
  float with HeadN's: Peach's crown sits on the head (nearest vertex 0.10 inside the sphere) at 5.17 and 0.92 above it
  at 6.37; Fox's ears, Koopa's / Luigi's / Mario's caps, Roy's, Pikachu's, Ganondorf's the same way (`--check` prints
  the table). In game, the Sephiroth hair placed for 6.37 sat 1.2 too low (the user's clip: the head's top bare
  behind the fringe, the side locks down to the floor), and it kept to the body / face while the copy motions turned
  HeadN by up to 179 degrees (Ultimate's Head yaws freely: nothing is skinned to it), so it isn't HeadN.
- Ultimate's two copy hats are in that same frame: copy_edge_cap is skinned to Body / Puff / S_HairB1 in Kirby's
  model space (its skeleton is Kirby's, same bind; Body at (0, 5.17, 0), Y-up axes), so its vertices - (0, 5.17, 0);
  copy_brave_cap has no skeleton and its vertices are already offsets from that point (offset 0): its circlet hugs
  the body sphere there (nearest vertex +0.05, median +0.23, none inside; best fit 5.1-5.2 scanning the anchor
  height) with the gem on the forehead and the sword and shield on the back. Stage 1 put it on Ultimate's Headdress
  joint (9.752: + 3.382 for a 6.37 anchor), which in game left the circlet floating ~1.5-2.9 above the head.
  (Ultimate's other caps, e.g. copy_reflet_cap, are in a Root bone's frame with X up, the same frame as Smash 4's
  hats less the axis turn: `--check` compares the two Robin hoods, which agree to ~0.7.)
- Rigid (one bone): the hair's own swing (S_HairB1, kirby/motion/copy_edge_cap) and the Puff weights aren't kept
  (approximation).
Texture ids: the new fighters' scheme (tools/fighter_texture_ids.py) puts each fighter at 0x40KK0000, KK = 0x80 +
kind; Kirby's copy hats take a block far past those fighters' own articles: Hero's (kind 0x45) 0x40C5F000 and
Sephiroth's (kind 0x42) 0x40C2F000, + 0x80 x NN (Kirby's costume NN: the loader picks cNN by Kirby's costume).
"""
import argparse
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nud  # noqa: E402
import ultimate_fighter as uf  # noqa: E402

HEAD_Y = 6.37          # HeadN / Head (stage 1's assumed anchor; Ultimate's reflet cap frame in --check)
ANCHOR_Y = 5.17        # the hat bone's place: BodyBN / Body (and NeckN)
HATS = {
    # out name: (Ultimate folder, offset to Smash 4's TopN frame, texture id base)
    'bravecap': ('copy_brave_cap', (0.0, 0.0, 0.0), 0x40C5F000),
    'edgecap': ('copy_edge_cap', (0.0, -ANCHOR_Y, 0.0), 0x40C2F000),
}
SPHERE = (np.array([0.0, 5.28, 0.07]), 4.70)    # Kirby's body sphere (Kirby_Bodybig's vertex box)
VANILLA_HATS = ('peachcap', 'foxear', 'koopacap', 'luigicap', 'mariocap', 'roycap', 'pikachucap', 'ganoncap',
                'marthcap', 'refletcap')
TEMPLATE_HAT = 'refletcap'      # Kirby's Robin copy: the copy kind both new copies are granted as
MATERIAL_HAT = 'mariocap'       # an opaque 0x9A011063 (colour, normal, ramp) material and its metal.nud


def hat_polygons(src, off, tex, tmpl):
    parts = uf.mesh_parts(src)
    meshes = []
    for name in sorted(parts):
        for part in parts[name]:
            n = part['n']
            pos = part['pos'] + np.asarray(off)
            nrm = part['nrm'] / (np.linalg.norm(part['nrm'], axis=1, keepdims=True) + 1e-9)
            if part['tan'] is not None:
                tan, sign = part['tan'][:, :3], part['tan'][:, 3:4]
            else:
                tan, sign = np.cross(nrm, [0, 1, 0]), np.ones((n, 1))
            tan = tan - nrm * (tan * nrm).sum(1, keepdims=True)
            tan = tan / (np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9)
            p = nud.Polygon()
            p.pos, p.nrm, p.tan, p.bit = pos, nrm, tan, np.cross(nrm, tan) * sign
            p.bones = np.zeros((n, 4), np.int64)            # TopN, the hat's only bone
            p.weights = np.tile([255, 0, 0, 0], (n, 1))
            p.uvs = [part['uvs']['map1']]
            p.col = np.full((n, 4), uf.WHITE)
            p.idx = part['idx']
            p.materials = [uf.material_for(tex, part['mat'], tmpl, part)]
            meshes.append(nud.Mesh('%s_%d_VIS_O_OBJ' % (part['mat'].material_label, part['sub']), [p], bone=-1, bind=4))
    return meshes


def build(ult, s4, out, log=print):
    tmpl_dir = os.path.join(s4, TEMPLATE_HAT, 'c00')
    mat_dir = os.path.join(s4, MATERIAL_HAT, 'c00')
    tmpl = uf.templates(nud.read(mat_dir + '/model.nud'))
    metal = nud.read(mat_dir + '/metal.nud')
    mm = next(p.materials[0] for m in metal for p in m.polygons if len(p.materials[0].textures) >= 4)
    for hat, (folder, off, tex_base) in HATS.items():
        for c in range(8):
            src = os.path.join(ult, folder, 'c%02d' % c)
            dst = os.path.join(out, hat, 'c%02d' % c)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(tmpl_dir):
                if f not in ('model.nud', 'metal.nud', 'model.nut'):
                    shutil.copy(os.path.join(tmpl_dir, f), os.path.join(dst, f))
            tex = uf.Textures(src, tex_base + 0x80 * c)
            meshes = hat_polygons(src, off, tex, tmpl)
            open(dst + '/model.nud', 'wb').write(nud.write(meshes, top_bone=0))
            metal_tex = tex.add(('metal',), uf.base_texture(mat_dir + '/model.nut', mm.textures[0]['hash']), 256)
            mmeshes = []
            for m in meshes:
                polys = []
                for p in m.polygons:
                    mt = mm.copy()
                    mt.textures[0]['hash'] = metal_tex
                    mt.textures[2]['hash'] = p.materials[0].textures[1]['hash']
                    polys.append(uf._with(p, [mt]))
                mmeshes.append(nud.Mesh(m.name, polys, -1, 4))
            open(dst + '/metal.nud', 'wb').write(nud.write(mmeshes, top_bone=0))
            open(dst + '/model.nut', 'wb').write(tex.nut())
            allpos = np.concatenate([p.pos for m in meshes for p in m.polygons])
            log('%s/c%02d: %d meshes, %d textures (0x%08X..), box %s .. %s' % (
                hat, c, len(meshes), len(tex.images), tex_base + 0x80 * c,
                np.round(allpos.min(0), 2).tolist(), np.round(allpos.max(0), 2).tolist()))


def rigged_positions(path):
    """a rigged .nud's vertex positions (the "vertex add" section: float xyz first)"""
    import zlib
    d = open(path, 'rb').read()
    if d[:2] == b'\x78\x9c':
        d = zlib.decompress(d)
    nrm = {0: 4, 1: 16, 2: 40, 3: 52, 6: 8, 7: 24}
    out = []
    for m in nud.read(path):
        for p in m.polygons:
            if p.vert_size >> 4 == 0:
                out.append(p.pos)
                continue
            stride = 12 + nrm[p.vert_size & 0xF] + {1: 32, 2: 16, 4: 8}[p.vert_size >> 4]
            a = np.frombuffer(d, np.uint8, p.nv * stride, p.vaoff).reshape(p.nv, stride)
            out.append(np.frombuffer(a[:, :12].tobytes(), '>f4').reshape(-1, 3).astype(np.float64))
    return np.concatenate(out)


def check(ult, s4, out=None):
    """where the hat bone is (vanilla hats against Kirby's body sphere), and Ultimate's reflet cap against Smash 4's"""
    import ssbh_data_py as s
    c, r = SPHERE
    print('vanilla hats on an anchor at y = 5.17 (BodyBN) / 6.37 (HeadN): share of vertices inside the body sphere, '
          'nearest vertex to it (- inside)')
    hats = [(h, os.path.join(s4, h, 'c00', 'model.nud')) for h in VANILLA_HATS]
    if out:
        hats += [(h + ' (built)', os.path.join(out, h, 'c00', 'model.nud')) for h in HATS]
    for h, path in hats:
        if not os.path.exists(path):
            continue
        v = rigged_positions(path)
        row = []
        for y in (ANCHOR_Y, HEAD_Y):
            d = np.linalg.norm(v + [0, y, 0] - c, axis=1) - r
            row.append('%.2f: inside %4.1f%%, nearest %+.2f' % (y, 100 * (d < 0).mean(), d.min()))
        print('  %-18s %s' % (h, ' | '.join(row)))
    mesh = s.mesh_data.read_mesh(os.path.join(ult, 'copy_reflet_cap', 'c00', 'model.numshb'))
    u = np.concatenate([np.array(o.positions[0].data, np.float64)[:, :3] for o in mesh.objects])
    w = np.c_[u[:, 2], u[:, 0], u[:, 1]]          # its Root frame (X up, Y forward, Z across) -> Kirby's world axes
    v = rigged_positions(os.path.join(s4, TEMPLATE_HAT, 'c00', 'model.nud'))
    print('Ultimate reflet cap (Root frame):  %s .. %s' % (np.round(w.min(0), 2).tolist(), np.round(w.max(0), 2).tolist()))
    print('Smash 4 refletcap (TopN):          %s .. %s' % (np.round(v.min(0), 2).tolist(), np.round(v.max(0), 2).tolist()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('s4')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.out:
        build(a.ult, a.s4, a.out)
    if a.check:
        check(a.ult, a.s4, a.out)


if __name__ == '__main__':
    main()
