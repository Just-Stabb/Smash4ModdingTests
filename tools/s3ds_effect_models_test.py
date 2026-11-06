#!/usr/bin/env python3
"""Checks tools/s3ds_effect_models.py (run through tools/s3ds_effects.py) on every Smash Run enemy's effect
models, reading back the written folders with the repo's readers: model.nud has a mesh per non-empty .bch
object part, its positions / UVs (V' = 1 - V) / vertex colours the .bch vertex buffer's, bound (bind 8) to the
part's bone, material blend / alpha test / colour gain / UV transform from the H3D material, the model.nut
texture the material's combiner baked over its texture (the combiner itself checked against hand-worked
stages first), ids unique over every enemy; model.vbn's bones the .bch's (+ TopN); model.omo's world matrices
the .bch bind pose / motion.bch animation (first, middle, last frame); model.mta re-writes identical, its
materials NUD material hashes, its visibility tracks NUD meshes; model.xmb parses; the written .efc names
only converted folders and keeps every 3DS reference that has one.

  python3 tools/s3ds_effect_models_test.py SRC_ROOT OUT_ROOT [KIND...]
      OUT_ROOT: a tools/s3ds_effects.py SRC_ROOT all OUT_ROOT VANILLA run
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import efc  # noqa: E402
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
import s3ds_effect_models as em  # noqa: E402
import s3ds_effects as sfx  # noqa: E402
import s3ds_enemy as se  # noqa: E402
import s3ds_model as sm  # noqa: E402
import xmb  # noqa: E402
from s3ds_preview import nud_uv  # noqa: E402

FAILS = []


def check(cond, what):
    if not cond:
        print('FAIL  ' + what)
        FAILS.append(what)
    return cond


def model_checks(tag, mdir, d, all_ids):
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    model = bch.models()[0]
    bones = model['bones']
    top = 0 if bones and bones[0]['name'] == 'TopN' else 1
    meshes = nud.read(os.path.join(d, 'model.nud'))
    # meshes, in object / part order
    want = []
    for obj in model['objects']:
        if obj['silhouette']:
            continue
        g = obj['geometry']()
        for nodes, _skin, idx in g['parts']:
            if len(idx):
                want.append((obj, g, nodes, idx))
    if not check(len(meshes) == len(want), '%s: %d meshes != %d parts' % (tag, len(meshes), len(want))):
        return
    nd, texs = nut.load(os.path.join(d, 'model.nut'))
    ids = {t.tex_id for t in texs}
    decoded = {t.tex_id: nut.decode(nd, t) for t in texs}
    textures = {k: v for k, v in bch.textures().items() if not k.endswith('#format')}
    manims = bch.material_animations()
    mframes = max([int(round(x['frames'])) + 1 for x in manims + bch.visibility_animations()] + [1])
    tracks = em.anim_tracks(manims[0] if manims else None)
    for t in texs:
        check(t.tex_id not in all_ids, '%s: texture id 0x%08X used twice' % (tag, t.tex_id))
        all_ids.add(t.tex_id)
        check(decoded[t.tex_id] is not None, '%s: texture 0x%08X decodes' % (tag, t.tex_id))
    want_gains = {}
    for m, (obj, g, nodes, idx) in zip(meshes, want):
        mt = '%s/%s' % (tag, obj['name'])
        a = g['attrs']
        used = np.unique(idx)
        p = m.polygons[0]
        check(m.name == obj['name'] and m.bind == 8 and m.bone == ((nodes[0] + top) if nodes else 0),
              '%s: name / bind / bone' % mt)
        check(p.pos.shape == (len(used), 3) and np.allclose(p.pos, a[0][used], atol=1e-4), '%s: positions' % mt)
        check(len(p.idx) == len(idx) and np.array_equal(used[np.asarray(p.idx)], idx), '%s: triangles' % mt)
        if 3 in a:
            uv = np.c_[a[3][used, 0], 1.0 - a[3][used, 1]]
            check(np.allclose(p.uvs[0], uv, atol=2e-3, rtol=1e-3), '%s: UVs (half floats)' % mt)
        if 2 in a:
            check(np.allclose(p.col, np.clip(np.round(a[2][used] * 127), 0, 255), atol=1), '%s: colours' % mt)
        mat = model['materials'][obj['material']]
        img, gains = em.bake_material(mat, textures, tracks.get(mat['name']), mframes)
        wm, st = em.material_for(mat, 0, 'x', gains[0])
        want_gains[mat['name']] = gains
        got = p.materials[0]
        check((got.src, got.dst, got.alpha_func, got.ref_alpha) == (wm.src, wm.dst, wm.alpha_func, wm.ref_alpha),
              '%s: blend / alpha test' % mt)
        props = dict(got.props)
        check(np.allclose(props['NU_effColorGain'], st['gain'], atol=1e-5), '%s: colour gain' % mt)
        if 3 in a and 'coords' in mat:
            # end to end: the written UVs through the effect vertex program's transform (s3ds_preview.nud_uv)
            # sample where the 3DS's coordinator transform (SPICA's) puts the 3DS UVs (V' = 1 - v')
            co = mat['coords'][0]
            m3 = sm.tex_transform([x or 1.0 for x in co['scale']], co['rotate'], co['translate'], co['transform'])
            t3 = (m3 @ np.c_[a[3][used], np.ones(len(used))].T).T
            got_uv = nud_uv(np.asarray(p.uvs[0], float), props)
            check(np.allclose(got_uv, np.c_[t3[:, 0], 1 - t3[:, 1]], atol=4e-3, rtol=1e-3),
                  '%s: UV transform (rotation / scale / translation)' % mt)
        if check(all(t['hash'] in ids for t in got.textures), '%s: texture in the nut' % mt):
            back = decoded[got.textures[0]['hash']]
            if back.shape == img.shape:                     # (not resized to a power of two)
                err = np.abs(back.astype(float) - img).mean()
                check(err < 8, '%s: texture != the baked combiner (BC1 / BC3) (mean error %.1f)' % (mt, err))
    # skeleton and animation
    vb = omo.vbn_read(os.path.join(d, 'model.vbn'))
    check([n for n, _p, _h in vb] == (['TopN'] if top else []) + [b['name'] for b in bones], '%s: vbn bones' % tag)
    od = open(os.path.join(d, 'model.omo'), 'rb').read()
    o = omo.Omo(od)
    check(o.encode() == od, '%s: omo re-encodes' % tag)
    mot = os.path.join(mdir, 'motion.bch')
    anims = sm.Bch(open(mot, 'rb').read()).skeletal_animations() if os.path.exists(mot) else []
    frames = int(round(anims[0]['frames'])) + 1 if anims else 1
    check(o.frames == frames, '%s: omo frames %d != %d' % (tag, o.frames, frames))
    locs = se.anim_locals(anims[0], bones, frames) if anims else \
        [np.broadcast_to(se.local_matrix(b['scale'], b['rot'], b['pos']), (1, 4, 4)) for b in bones]
    worst = 0.0
    for fr in sorted({0, frames // 2, frames - 1}):
        w = omo.world(o, vb, fr)
        ref = []
        for i, b in enumerate(bones):
            lm = locs[i][min(fr, len(locs[i]) - 1)]
            ref.append(lm if b['parent'] < 0 else ref[b['parent']] @ lm)
            worst = max(worst, np.abs(np.array(w[b['name']]) - ref[-1]).max() / max(1.0, np.abs(ref[-1]).max()))
    check(worst < 1e-3, '%s: omo world matrices off by %.4g' % (tag, worst))
    # material / visibility animation
    md = open(os.path.join(d, 'model.mta'), 'rb').read()
    if md:
        r = mta.read(md)
        hashes = {struct.unpack('>I', struct.pack('>f', dict(mm.props)['NU_materialHash'][0]))[0]
                  for m in meshes for pp in m.polygons for mm in pp.materials}
        check(all(e['hash'] in hashes for e in r['mats']), '%s: mta materials are NUD material hashes' % tag)
        names = {m.name for m in meshes}
        check(all(v['name'] in names for v in r['vis']), '%s: mta visibility tracks are meshes' % tag)
        again = mta.write(r['frames'], [dict(name=e['name'], hash=e['hash'], props=[
            dict(name=q['name'], values=q['values'], u1=q['u1'], u2=q['u2'], type=q['type']) for q in e['props']])
            for e in r['mats']], rate=r['rate'], unk=r['unk'],
            vis=[(v['name'], [(k[0], k[1]) for k in v['keys']]) for v in r['vis']])
        check(again == md, '%s: mta re-writes identical' % tag)
        folder = os.path.basename(d)
        for e in r['mats']:
            rv = next((q['values'] for q in e['props'] if q['name'] == 'NU_effRotUV'), None)
            tr = tracks.get(e['name'][len(folder) + 1:], {})
            if (20, 0) in tr:
                want = [sm.sample(tr[(20, 0)][0], f) for f in range(r['frames'])]
                check(rv is not None and np.allclose([v[0] for v in rv], want, atol=1e-5),
                      '%s: %s UV rotation track' % (tag, e['name']))
            gv = next((q['values'] for q in e['props'] if q['name'] == 'NU_effColorGain'), None)
            wg = want_gains.get(e['name'][len(folder) + 1:])
            if gv is not None and check(wg is not None, '%s: mta material %s' % (tag, e['name'])):
                check(np.allclose(gv, [wg[min(f, len(wg) - 1)] for f in range(len(gv))], atol=1e-5),
                      '%s: %s colour gain track != the combiner a frame' % (tag, e['name']))
    check(xmb.parse(open(os.path.join(d, 'model.xmb'), 'rb').read()) is not None, '%s: xmb' % tag)


def tev_checks():
    """s3ds_model.tev_combine against stages worked by hand"""
    rng = np.random.default_rng(0)
    tex = rng.random((4, 4, 4))
    prim = (0.9, 0.8, 0.7, 0.6)
    # StarmanBeam's stage 0: RGB interpolate(primary, constant, texture), alpha modulate(primary, texture.G)
    tev = {0xC0: 0x0E3003E0, 0xC1: 0x20000, 0xC2: 0x10004, 0xC3: 0xFF0046AA, 0xC4: 0}
    for r in sm.TEV_STAGES[1:]:
        tev[r], tev[r + 2] = 0x0E1F0E1F, 0                   # pass the previous on
    out = sm.tev_combine(tev, [tex, None, None], primary=prim)
    c = np.array([0xAA, 0x46, 0x00]) / 255.0
    want_rgb = np.array(prim[:3]) * tex[..., :3] + c * (1 - tex[..., :3])
    want_a = prim[3] * tex[..., 1]
    check(np.allclose(out[..., :3], np.clip(want_rgb, 0, 1)) and np.allclose(out[..., 3], want_a), 'tev: interpolate')
    # stage 0 writes the buffer, stage 1 replaces with the constant, stage 2 adds the buffer (x2 scale)
    tev = {0xE0: 0x1100, 0xFD: 0, 0xC0: 0x00030003, 0xC1: 0, 0xC2: 0,
           0xC8: 0x000E000E, 0xC9: 0, 0xCA: 0, 0xCB: 0x40404040,
           0xD0: 0x00DF00DF, 0xD1: 0, 0xD2: 0x20002, 0xD4: 0x10001}
    for r in sm.TEV_STAGES[3:]:
        tev[r], tev[r + 2] = 0x0E1F0E1F, 0
    out = sm.tev_combine(tev, [tex, None, None])
    check(np.allclose(out, np.clip(2 * (0x40 / 255.0 + tex), 0, 1)), 'tev: combiner buffer + scale')


def popperam_check(src):
    """EfffsPopperamBikkuri: its one stage is RGB = constant x primary, alpha = constant, the constant the
    material's ambient slot (static alpha 0), which property 8 animates (G, B, A; R absent: static): the baked
    frame is opaque, and the gain a frame is the track's value (8 bits) over the baked frame's (1 where absent)"""
    mdir = os.path.join(src, 'enemy', 'popperam', 'effect', 'model', 'EfffsPopperamBikkuri')
    if not os.path.exists(mdir):
        return
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    mat = bch.models()[0]['materials'][0]
    a = bch.material_animations()[0]
    tr = em.anim_tracks(a)[mat['name']]
    frames = int(round(a['frames'])) + 1
    img, gains = em.bake_material(mat, {}, tr, frames)
    comps = tr[(8, 5)]
    vals = np.array([[1.0 if c is None else sm.sample(c, f) for c in comps] for f in range(frames)])
    vals = np.round(np.clip(vals, 0, 1) * 255) / 255                    # the GPU's 8-bit constant
    ref = int(np.argmax(vals[:, 3]))                       # the first fully visible frame
    check(img[..., 3].min() == 255, 'popperam: baked opaque')
    check(np.allclose(gains, vals / vals[ref], atol=2e-3), 'popperam: gains = the track over the baked frame')


def main():
    src, out = sys.argv[1], sys.argv[2]
    tev_checks()
    popperam_check(src)
    kinds = sys.argv[3:] or se.fs_kinds(src)
    all_ids = set()
    n_models = n_kinds = 0
    for k in kinds:
        root = os.path.join(src, 'enemy', k, 'effect', 'model')
        od = os.path.join(out, 'effect', 'enemy', k)
        have = set()
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                d = os.path.join(od, 'model', name)
                if not os.path.exists(os.path.join(root, name, 'normal.bch')):
                    continue
                if check(os.path.exists(os.path.join(d, 'model.nud')), '%s/%s: converted' % (k, name)):
                    model_checks('%s/%s' % (k, name), os.path.join(root, name), d, all_ids)
                    have.add(name)
                    n_models += 1
        fe = os.path.join(src, 'enemy', k, 'effect', '%s.03030000.efc' % k)
        we = os.path.join(od, '%s.010d0000.efc' % k)
        if os.path.exists(fe) and os.path.exists(we):
            n_kinds += 1
            entries, models, _m, _n = sfx.read_efc(open(fe, 'rb').read())
            w = efc.Efc(open(we, 'rb').read())
            check(set(w.models) <= have, '%s: efc names a model not converted' % k)
            for e3, ew in zip(entries, w.entries):
                name = models[e3[2] - 1] if e3[2] else None
                got = w.models[ew[2] - 1] if ew[2] else None
                check(got == (name if name in have else None), '%s: efc entry 0x%X model %s != %s' % (
                    k, e3[0], got, name))
    print('%d kinds, %d models, %d textures, %d failures' % (n_kinds, n_models, len(all_ids), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
