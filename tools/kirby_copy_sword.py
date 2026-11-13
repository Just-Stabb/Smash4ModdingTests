#!/usr/bin/env python3
"""Kirby's Hero copy: Hero's sword as Kirby's held model (fighter/kirby/model/bravesword/cNN: model.nud, metal.nud,
model.nut, model.vbn and the one-bone model's side files), shown on the stone while a sword spell is cast.
fighters/kirby/specials.md "v6".

  python3 tools/kirby_copy_sword.py ULT_BRAVE_BODY_DIR TEMPLATE_DIR OUT_MODEL_DIR [--costume NN]

ULT_BRAVE_BODY_DIR: Ultimate's brave/model/body (cNN with model.numshb / numdlb / numatb / nusktb and the textures:
the user's brave.zip). TEMPLATE_DIR: a one-bone Kirby copy model folder (the Hero copy hat, fighter/kirby/model/
bravecap/c00 from kirby_hero_sephiroth_copy_v1: tools/kirby_copy_hats.py's output, itself from Smash 4's refletcap /
mariocap): its material (0x9A011063: colour, normal, ramp), its metal.nud material and metal texture, and its
model.jtb / sb / xmb / nhb / mta. OUT_MODEL_DIR gets bravesword/c00-c07 (every Kirby costume the same sword: Hero cNN
with --costume, default 00, Eleven's; Kirby's costume picks the folder, not the copied Hero's).

How it sits (worked out from the files):
- Ultimate's sword (brave_sword_VIS_O_OBJShape, material met_brave11_001) is single-bound to Hero's Sword1 bone: its
  vertices are in Sword1's frame, the blade along +X (x -2.1 .. 12.1), the flat in X-Z (y +-0.4, z +-1.8).
- Sword1 and HaveR are both children of HandR; in HaveR's frame Sword1's +X is HaveR's +Y and its origin is at
  (0.202, 0, 0) (the skeleton's local transforms, nusktb rows: Ultimate's item convention, an item's long axis
  along the Have bone's +Y). Smash 4's Hero (tools/ultimate_fighter.py --have Shield,Sword1) plays Sword1 as RHaveN,
  so his scripts' sword hitboxes (bone 0x19, X 4 / 9 along the blade, Z -2.5) are in Sword1's frame too.
- Kirby's copy held model is his article 26 ("simple", weapon kind 0x11) on Kirby's LHaveN; the game puts the
  model's root on that bone (the Marth copy's marthsword: its HaveN's bind rotation turns its +Z blade onto LHaveN's
  +Y, tools/kirby_marth_sword.py). Here the root (HaveN) has no rotation and the vertices are given in LHaveN's own
  frame: Hero's sword as held in HaveR (Sword1's frame -> HaveR's), the blade along +Y, so the hitboxes on Kirby's
  LHaveN (script bone 0x18) are Hero's (x, y, z) -> (0.202 - y, x, z) (fighters/kirby/kirby.c khm_sw_*).
  Kirby's LHaveN is taken to be oriented as Ultimate's HaveL / HaveR (Kirby's two skeletons share the bind pose,
  tools/kirby_copy_motions.py); the edge's side (z) is not checked in game.
- Size: Hero's (the hitboxes are Hero's sizes and offsets).
Texture ids: Hero's block (kind 0x45: 0x40C50000), past his articles and below the copy hats' 0x40C5F000:
0x40C5E000 + 0x80 x NN (Kirby's costume NN).
"""
import argparse
import os
import shutil
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nud  # noqa: E402
import ultimate_fighter as uf  # noqa: E402

TEX_BASE = 0x40C5E000
MESH = 'brave_sword_VIS_O_OBJShape'
SIDE_FILES = ('model.jtb', 'model.sb', 'model.xmb', 'model.nhb', 'model.mta')


def sword_to_have(skel_path):
    """4x4 (column vectors) taking Sword1-frame points to HaveR-frame points"""
    import ssbh_data_py as s
    sk = s.skel_data.read_skel(skel_path)
    by = {b.name: b for b in sk.bones}

    def local(n):
        return np.array(by[n].transform, dtype=np.float64).T      # nusktb rows (row vectors) -> column form
    assert sk.bones[by['Sword1'].parent_index].name == sk.bones[by['HaveR'].parent_index].name == 'HandR'
    return np.linalg.inv(local('HaveR')) @ local('Sword1')


def vbn_one_bone(name):
    """little-endian model.vbn (' NBV' 2.1, as the copy hats'): one bone at the origin, unrotated, scale 1"""
    out = struct.pack('<4sHHI4I', b' NBV', 2, 1, 1, 1, 0, 0, 0)
    out += name.encode().ljust(64, b'\0') + struct.pack('<IiI', 0, 0x0FFFFFFF, zlib.crc32(name.encode()) & 0xFFFFFFFF)
    out += struct.pack('<9f', 0, 0, 0, 0, 0, 0, 1, 1, 1)
    return out


def sword_meshes(src, m, tex, tmpl):
    parts = uf.mesh_parts(src)[MESH]
    rot = m[:3, :3]
    meshes = []
    for part in parts:
        n = part['n']
        assert not part['infl'] and part['parent'] == 'Sword1', 'the sword is single-bound to Sword1'
        pos = (np.c_[part['pos'], np.ones(n)] @ m.T)[:, :3]
        nrm = part['nrm'] @ rot.T
        nrm = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
        if part['tan'] is not None:
            tan, sign = part['tan'][:, :3] @ rot.T, part['tan'][:, 3:4]
        else:
            tan, sign = np.cross(nrm, [0, 1, 0]), np.ones((n, 1))
        tan = tan - nrm * (tan * nrm).sum(1, keepdims=True)
        tan = tan / (np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9)
        p = nud.Polygon()
        p.pos, p.nrm, p.tan, p.bit = pos, nrm, tan, np.cross(nrm, tan) * sign
        p.bones = np.zeros((n, 4), np.int64)            # HaveN, the model's only bone
        p.weights = np.tile([255, 0, 0, 0], (n, 1))
        p.uvs = [part['uvs']['map1']]
        p.col = np.full((n, 4), uf.WHITE)
        p.idx = part['idx']
        p.materials = [uf.material_for(tex, part['mat'], tmpl, part)]
        meshes.append(nud.Mesh('bravesword_%d_VIS_O_OBJ' % part['sub'], [p], bone=-1, bind=4))
    return meshes


def build(ult, template, out, costume=0, log=print):
    src = os.path.join(ult, 'c%02d' % costume)
    m = sword_to_have(os.path.join(src, 'model.nusktb'))
    tmpl = uf.templates(nud.read(os.path.join(template, 'model.nud')))
    metal = nud.read(os.path.join(template, 'metal.nud'))
    mm = next(p.materials[0] for mesh in metal for p in mesh.polygons if len(p.materials[0].textures) >= 4)
    metal_img = uf.base_texture(os.path.join(template, 'model.nut'), mm.textures[0]['hash'])
    for c in range(8):
        dst = os.path.join(out, 'bravesword', 'c%02d' % c)
        os.makedirs(dst, exist_ok=True)
        for f in SIDE_FILES:
            shutil.copy(os.path.join(template, f), os.path.join(dst, f))
        open(os.path.join(dst, 'model.vbn'), 'wb').write(vbn_one_bone('HaveN'))
        tex = uf.Textures(src, TEX_BASE + 0x80 * c)
        meshes = sword_meshes(src, m, tex, tmpl)
        open(os.path.join(dst, 'model.nud'), 'wb').write(nud.write(meshes, top_bone=0))
        metal_tex = tex.add(('metal',), metal_img, 256)
        mmeshes = []
        for mesh in meshes:
            polys = []
            for p in mesh.polygons:
                mt = mm.copy()
                mt.textures[0]['hash'] = metal_tex
                mt.textures[2]['hash'] = p.materials[0].textures[1]['hash']
                polys.append(uf._with(p, [mt]))
            mmeshes.append(nud.Mesh(mesh.name, polys, -1, 4))
        open(os.path.join(dst, 'metal.nud'), 'wb').write(nud.write(mmeshes, top_bone=0))
        open(os.path.join(dst, 'model.nut'), 'wb').write(tex.nut())
        allpos = np.concatenate([p.pos for mesh in meshes for p in mesh.polygons])
        log('bravesword/c%02d: %d meshes, %d textures (0x%08X..), box %s .. %s' % (
            c, len(meshes), len(tex.images), TEX_BASE + 0x80 * c,
            np.round(allpos.min(0), 2).tolist(), np.round(allpos.max(0), 2).tolist()))
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('template')
    ap.add_argument('out')
    ap.add_argument('--costume', type=int, default=0)
    a = ap.parse_args()
    m = build(a.ult, a.template, a.out, a.costume)
    print('Sword1 -> HaveR:\n%s' % np.round(m, 4))


if __name__ == '__main__':
    main()
