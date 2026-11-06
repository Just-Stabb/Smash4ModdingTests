#!/usr/bin/env python3
"""Checks tools/s3ds_stage.py's builds (every AREA / AREA_open folder under OUT) against the 3DS files and the
slot's Battlefield copy, reading the written files back with the repo's readers:

- only forms Battlefield's loaded models have (docs/minecraft-world.md, "Freeze"): our meshes unbound (bind 0,
  bone -1), every material Battlefield's unlit 0xA2001001 with blending none / alpha / additive and the alpha
  test 518 or none, under 65536 vertices a polygon; textures NTWU, one mip, power-of-two 64-2048, BC1 / BC3, ids
  from 0x2000F001 (one id an image, shared by the folders using it); every Battlefield model folder hidden (all
  its indices 0); no file of the base missing.
- geometry, end to end: every mesh's positions the 3DS .mbn's (a rigid part placed by its bone's bind
  pose; a copy at each of s3ds_stage.placements: the climb's tower segments, MainField's moving floors); its
  UVs through the body shader's transform
  (s3ds_preview.nud_uv, NU_colorSamplerUV) where the 3DS's coordinator transform (SPICA's) puts the 3DS UVs.
- collision: the 3DS .lvds' collisions (vertices, normals, materials, pass-through flags) in order (the open
  build without the enclosing loops), no bone links; 8 spawns, each on a floor line (or the 3DS's own spawn);
  8 respawns, the camera bounds and the item paths inside the blast zones.
- the stprm camera values (indices 6-10) the 3DS stage's.

  python3 tools/s3ds_stage_test.py SRC_ROOT BASE OUT
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lvd  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import s3ds_model as sm  # noqa: E402
import s3ds_stage as st  # noqa: E402
from s3ds_enemy import local_matrix  # noqa: E402
from s3ds_preview import nud_uv  # noqa: E402

FAILS = []


def check(cond, what):
    if not cond:
        print('FAIL  ' + what)
        FAILS.append(what)
    return cond


def model_checks(src, area, od, all_ids):
    folders = sorted(glob.glob(os.path.join(od, 'model', 'stc_sr_*')))
    names = ['stc_sr_%s_set' % n for n in st.area_models(src, area)]
    check(set(os.path.basename(f) for f in folders) <= set(names), '%s: model folders' % area)
    worst_pos = worst_uv = 0.0
    n_mesh = 0
    for folder in folders:
        name = os.path.basename(folder)[len('stc_sr_'):-len('_set')]
        tag = '%s/%s' % (area, name)
        dn, texs = nut.load(os.path.join(folder, 'model.nut'))
        ids = {t.tex_id for t in texs}
        for t in texs:
            check(t.tex_id >= st.TEX_BASE + 1, '%s: texture id 0x%08X' % (tag, t.tex_id))
            check((t.w & (t.w - 1)) == 0 and (t.h & (t.h - 1)) == 0 and 64 <= min(t.w, t.h) and max(t.w, t.h) <= 2048,
                  '%s: texture 0x%08X size %dx%d' % (tag, t.tex_id, t.w, t.h))
            check(t.fmt in (0x31, 0x33), '%s: texture 0x%08X format 0x%X' % (tag, t.tex_id, t.fmt))
            check(nut.decode(dn, t) is not None, '%s: texture 0x%08X decodes' % (tag, t.tex_id))
        all_ids.setdefault(name, ids)
        written = nud.read(os.path.join(folder, 'model.nud'))
        mdir = os.path.join(src, 'stage', 'field_smash', area, 'model', name)
        bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
        model = bch.models()[0]
        mbn = sm.read_mbn(open(os.path.join(mdir, 'normal.mbn'), 'rb').read())
        offsets = st.placements(src, area, name)
        world = []
        for b in model['bones']:
            lm = local_matrix(b['scale'], b['rot'], b['pos'])
            world.append(lm if b['parent'] < 0 else world[b['parent']] @ lm)
        want = []
        for obj, mi in zip(model['objects'], sm.match_objects(model['objects'], mbn)):
            if obj['silhouette'] or not (model['visibility'] >> obj['node']) & 1:
                continue
            for bl, idx in mbn[mi]['parts']:
                if len(idx):
                    for off in offsets:
                        want.append((obj, mbn[mi], idx, bl, off))
        if not check(len(written) == len(want), '%s: %d meshes != %d parts' % (tag, len(written), len(want))):
            continue
        for m, (obj, me, idx, bl, off) in zip(written, want):
            p = m.polygons[0]
            mat = p.materials[0]
            check(m.bind == 0 and m.bone == -1, '%s/%s: unbound' % (tag, m.name))
            check(mat.flags == st.UNLIT and (mat.src, mat.dst) in ((0, 0), (1, 1), (1, 2)) and
                  mat.alpha_func in (0, 518), '%s/%s: material form 0x%08X %d/%d %d' % (
                      tag, m.name, mat.flags, mat.src, mat.dst, mat.alpha_func))
            check(all(t['hash'] in ids for t in mat.textures), '%s/%s: texture in the nut' % (tag, m.name))
            check(p.nv < 0x10000, '%s/%s: vertices' % (tag, m.name))
            a = me['attrs']
            used = np.unique(idx)
            # rigged polygons aren't read back (positions in the vertex add section): ours are all unrigged.
            # A rigid part (no weights) is in its bone's space: its bind pose places it; then the placement
            pos = a[0][used].astype(float)
            if 6 not in a and len(bl) and world:
                bi = a[5][used, 0].astype(int) if 5 in a else np.zeros(len(used), int)
                bo = np.asarray(bl)[np.minimum(bi, len(bl) - 1)]
                for b in np.unique(bo):
                    sel = bo == b
                    pos[sel] = pos[sel] @ world[b][:3, :3].T + world[b][:3, 3]
            pos[:, :2] += off
            worst_pos = max(worst_pos, float(np.abs(p.pos - pos).max()))
            mat3 = model['materials'][obj['material']]
            if 3 in a and 'coords' in mat3:
                co = mat3['coords'][0]
                m3 = sm.tex_transform([x or 1.0 for x in co['scale']], 0.0, co['translate'], co['transform'])
                t3 = (m3 @ np.c_[a[3][used], np.ones(len(used))].T).T
                got = nud_uv(np.asarray(p.uvs[0], float), dict(mat.props))
                worst_uv = max(worst_uv, float((np.abs(got - np.c_[t3[:, 0], 1 - t3[:, 1]]) /
                                                np.maximum(1, np.abs(t3))).max()))
            n_mesh += 1
    check(worst_pos < 1e-2, '%s: positions = the .mbn (worst %.4g)' % (area, worst_pos))
    check(worst_uv < 4e-3, '%s: UVs through the shader = the 3DS transform (worst %.4g)' % (area, worst_uv))
    return n_mesh


def lvd_checks(src, area, od, open_room):
    lv = lvd.LVD(glob.glob(os.path.join(od, 'param', '*.lvd'))[0])
    srcs = [lvd.LVD(p) for p in sorted(glob.glob(os.path.join(src, 'stage', 'field_smash', area, 'param', '*.lvd')))]
    want = [c for f in srcs for c in f.collisions if not (open_room and st.enclosing(c))]
    ok = len(want) == len(lv.collisions)
    for a, b in zip(want, lv.collisions):
        ok &= np.allclose(a.verts, b.verts) and np.allclose(a.normals, b.normals) and \
            [bytes(m) for m in a.mats] == [bytes(m) for m in b.mats] and a.flags == b.flags and b.bone == ''
    check(ok, '%s: collisions = the 3DS ones (%d)' % (area, len(want)))
    check(len(lv.spawns) == 8 and len(lv.respawns) == 8, '%s: 8 spawns / respawns' % area)
    fl = st.floors(lv.collisions)
    own = {(s.x, s.y) for f in srcs for s in f.spawns}
    for s in lv.spawns:
        fy = st.floor_at(fl, s.x, s.y)
        check((s.x, s.y) in own or (fy is not None and abs(fy - s.y) < 0.5),
              '%s: spawn %s (%.1f, %.1f) on a floor' % (area, s.name, s.x, s.y))
    b, c = lv.blast[0], lv.camera[0]
    check(b.left <= c.left and c.right <= b.right and c.bottom >= b.bottom and c.top <= b.top,
          '%s: camera bounds inside the blast zones' % area)
    for r in lv.respawns:
        check(b.left < r.x < b.right and b.bottom < r.y < b.top, '%s: respawn %s inside' % (area, r.name))
    for sec in lv.items[0].sections:
        for x, y in sec.points:
            check(b.left < x < b.right and b.bottom < y < b.top, '%s: item path inside' % area)


def param_checks(src, area, od):
    s3 = glob.glob(os.path.join(src, 'stage', 'field_smash', area, 'param', '*_stprm.bin'))
    if not s3:
        return
    got, want = st.read_params(glob.glob(os.path.join(od, 'param', '*_stprm.bin'))[0]), st.read_params(s3[0])
    check(all(abs(got[k] - want[k]) < 1e-5 for k in st.CAMERA_KEYS), '%s: stprm camera values' % area)


def base_checks(base, od, area):
    files = {os.path.relpath(os.path.join(r, f), base) for r, _d, fs in os.walk(base) for f in fs}
    have = {os.path.relpath(os.path.join(r, f), od) for r, _d, fs in os.walk(od) for f in fs}
    check(files <= have, '%s: every base file present (%d missing)' % (area, len(files - have)))
    for f in glob.glob(os.path.join(base, 'model', '*', 'model.nud')):
        rel = os.path.relpath(f, base)
        m = nud.read(os.path.join(od, rel))
        check(all(not np.asarray(p.idx).any() for x in m for p in x.polygons), '%s: %s hidden' % (area, rel))


def main():
    src, base, out = sys.argv[1:4]
    n_builds = n_mesh = 0
    for area in st.AREAS:
        for open_room in (False, True):
            od = os.path.join(out, area + ('_open' if open_room else ''), 'stage', 'melee', 'NewStage01')
            if not os.path.isdir(od):
                continue
            n_builds += 1
            n_mesh += model_checks(src, area, od, {})
            lvd_checks(src, area, od, open_room)
            param_checks(src, area, od)
            base_checks(base, od, area)
    print('%d builds, %d meshes, %d failures' % (n_builds, n_mesh, len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
