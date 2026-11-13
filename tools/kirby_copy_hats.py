#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy hats: Ultimate's kirby/model/copy_brave_cap / copy_edge_cap (c00-c07) as Smash 4 hat
models (fighter/kirby/model/bravecap / edgecap/cNN: model.nud, metal.nud, model.nut, model.vbn and the rest of the
template hat's files). fighters/kirby/specials.md "Hero / Sephiroth copies".

  python3 tools/kirby_copy_hats.py ULT_KIRBY_MODEL_DIR S4_KIRBY_MODEL_DIR OUT_MODEL_DIR [--check]

ULT_KIRBY_MODEL_DIR: Ultimate's kirby/model (copy_brave_cap/, copy_edge_cap/, copy_reflet_cap/, body/c00). S4_KIRBY_MODEL_DIR:
Smash 4's fighter/kirby/model (refletcap/c00: the template hat whose vbn / jtb / sb / xmb / nhb / mta are copied;
mariocap/c00: the material template, its metal.nud). OUT_MODEL_DIR gets bravecap/c00-c07 and edgecap/c00-c07.

Placement (worked out from both games' files):
- Smash 4's hats are one bone (TopN) whose frame is Kirby's world frame (Y up, X across, Z forward) with its origin at
  HeadN (y 6.37 in the bind pose): refletcap's vertices span y -3.58..6.88, x -7.02..7.31, z -7.09..4.55.
- Ultimate's reflet cap is on Kirby's Head bone (bone frame: local X = world up, local Z = across, local Y = forward,
  at y 6.37): placed so, it spans world y 2.91..12.51, x +-6.8, z -6.44..4.57; less HeadN that is y -3.46..6.14,
  z -6.44..4.57: the same box as Smash 4's within ~0.7 (different meshes of the same hood). So the two Head bones
  agree (both skeletons put Head at (0, 6.37, 0) with the same rotation) and a hat goes over as its world position
  less (0, 6.37, 0). `--check` prints that comparison.
- copy_brave_cap has no skeleton: its meshes sit on Kirby's Headdress joint (0, 9.752, 0, unrotated; the only
  Y-up joint near the top of the head; its ring is level there): + (0, 3.382, 0).
- copy_edge_cap is skinned to Kirby's Body / Puff / S_HairB1 in his bind pose (model space): - (0, 6.37, 0). Rigid
  here (one bone): its hair's own swing (S_HairB1, model.nuanmb) isn't kept (approximation).
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

HEAD_Y = 6.37
HEADDRESS_Y = 9.752
HATS = {
    # out name: (Ultimate folder, offset to Smash 4's TopN frame, texture id base)
    'bravecap': ('copy_brave_cap', (0.0, HEADDRESS_Y - HEAD_Y, 0.0), 0x40C5F000),
    'edgecap': ('copy_edge_cap', (0.0, -HEAD_Y, 0.0), 0x40C2F000),
}
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


def check(ult, s4):
    """Ultimate's reflet cap on its Head bone, less HeadN, against Smash 4's refletcap"""
    import ssbh_data_py as s
    mesh = s.mesh_data.read_mesh(os.path.join(ult, 'copy_reflet_cap', 'c00', 'model.numshb'))
    u = np.concatenate([np.array(o.positions[0].data)[:, :3] for o in mesh.objects])
    w = np.c_[u[:, 2], u[:, 0] + HEAD_Y, u[:, 1]] - [0, HEAD_Y, 0]     # Head: local (x, y, z) -> world (z, x + 6.37, y)
    v = np.concatenate([p.pos for m in nud.read(os.path.join(s4, TEMPLATE_HAT, 'c00', 'model.nud')) for p in m.polygons])
    print('Ultimate reflet cap (Head bone, less HeadN): %s .. %s' % (np.round(w.min(0), 2).tolist(), np.round(w.max(0), 2).tolist()))
    print('Smash 4 refletcap (TopN):                    %s .. %s' % (np.round(v.min(0), 2).tolist(), np.round(v.max(0), 2).tolist()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('s4')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        check(a.ult, a.s4)
    if a.out:
        build(a.ult, a.s4, a.out)


if __name__ == '__main__':
    main()
