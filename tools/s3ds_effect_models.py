#!/usr/bin/env python3
"""Smash 3DS effect models (an enemy's effect/model/NAME/normal.bch + motion.bch: H3D with the meshes kept in
the .bch) -> Smash 4 effect model folders (model.nud / .nut / .vbn / .omo / .mta / .xmb, as the game's own effect
models and tools/xv2_to_nud.py's), next to the converted .efc: effect/enemy/KIND/model/NAME/.

  python3 tools/s3ds_effect_models.py SRC_ROOT KIND|all OUT
      (tools/s3ds_effects.py runs it for each enemy it converts, and keeps the .efc's references to them)

Mapping:
- skeleton: the .bch bones (under a TopN root unless their root is one already), every bone at the origin
  in the little-endian model.vbn, as the game's effect models; model.omo gives every bone its full local
  transform each frame: the motion.bch's skeletal animation (s3ds_enemy.anim_locals: H3D keys sampled every
  frame 0..end; s3ds_enemy.split_trs, mirrored and zero scales kept exact), else the bind pose.
- meshes (s3ds_model.Bch._geometry: the PICA200 vertex / index buffers): one NUD mesh per .bch object part,
  bound to its bone (bind 8; the 3DS's rigid skinning keeps the vertices in that bone's space, as bind 8 does);
  positions, normals, vertex colours (1.0 -> 127, white without), UV 0 with the 3DS's V turned (V' = 1 - V).
- materials: the effect shader 0xB0201100 (UV transform + vertex colour) as tools/xv2_to_nud.py; blend from the
  H3D fragment operations (source alpha / one minus source alpha -> 5 / 1, source alpha / one (additive) ->
  5 / 2, none -> 0 / 0), its alpha test (-> 0x204, the 3DS reference), culling; NU_effScaleUV /
  NU_effTransUV = its texture coordinator 0 (Ohana3DS: uv * scale - translate, V up; NUD: uv * scale + trans on
  V' = 1 - V: trans = (-tu, 1 - sv + tv)), NU_materialHash.
- textures: the material's texture combiner (6 PICA200 TEV stages: s3ds_model.tev_combine) baked into its
  texture 0 (the only texture the effect materials read; most stages lerp the diffuse / vertex colour against a
  constant colour by the texture and take the alpha from one of its channels, ETC1 having none), with the
  diffuse as the primary colour; a stage's constant is one of the material's colours, so a colour animation
  (diffuse / ambient / constant0) runs the combiner every frame: the most visible frame is baked and the rest
  is NU_effColorGain (the output's colour and alpha over the baked frame's, a frame, in the MTA). PICA200 ->
  RGBA (s3ds_model.decode_texture) -> GX2 BC1 / BC3, power-of-two; ids 0x4F000000 + 0x400 an enemy (its index
  among the Smash Run enemies), then one after the other over its models.
- model.mta: the normal.bch's material animation (colours -> NU_effColorGain as above, coordinator 0
  translate / scale -> NU_effTransUV / NU_effScaleUV, a frame each) and visibility animation (mesh states by
  name); UV rotation and the other colours are left out (counted).
- model.xmb: the game's effect_near layout (xv2_to_nud.effect_xmb).
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import s3ds_enemy as se  # noqa: E402
import s3ds_model as sm  # noqa: E402
from xv2_to_nud import FLAG_BASE, effect_xmb, float_hash, omo_new, omo_node, vbn_le  # noqa: E402

TEX_BASE = 0x4F000000
WRAP = {0: 3, 1: 3, 2: 1, 3: 2}          # H3D wrap (0 clamp, 1 border, 2 repeat, 3 mirror) -> NUD


def eff_uv(scale, trans):
    """3DS coordinator (scale, translate) -> (NU_effScaleUV, NU_effTransUV) [4] each"""
    su, sv = scale
    tu, tv = trans
    return [su, sv, 0.0, 0.0], [-tu, 1.0 - sv + tv, 0.0, 0.0]


SLOTS = ('emission', 'ambient', 'diffuse', 'specular0', 'specular1', 'constant0', 'constant1', 'constant2',
         'constant3', 'constant4', 'constant5', 'blend')
COLOR_PROPS = {9: 'diffuse', 8: 'ambient', 1: 'constant0'}      # H3D material animation colour targets
COLOR_TRACKS = tuple((p, 5) for p in COLOR_PROPS)


def _rgba32(c):
    return sum(int(round(min(max(x, 0.0), 1.0) * 255)) << (8 * j) for j, x in enumerate(c))


def bake_material(mat, textures, tracks=None, frames=1):
    """the material's texture combiner baked into its texture: (RGBA uint8, [NU_effColorGain a frame]).
    The PICA200 combiner (s3ds_model.tev_combine) runs over texture 0's texels with the primary colour = the
    material's diffuse (the vertex colour multiplies in after, as NUD's effect shader does). Each stage's
    constant is one of the material's colours (the slot whose value it holds; an animated one first), so a
    colour animation (TRACKS {(property, segment): components}: diffuse / ambient / constant0) changes the
    stages it feeds: the combiner runs every frame, the most visible frame is baked, and the gain a frame is the
    output's colour (alpha-weighted) and alpha over that frame's, per channel."""
    tracks = tracks or {}
    src = textures.get(mat['textures'][0])
    if src is None:
        src = np.full((8, 8, 4), 255, np.uint8)
    static = {k: np.array(mat.get('colors', {}).get(k, (255, 255, 255, 255)), float) / 255.0 for k in SLOTS}
    if not mat.get('tev'):
        return src, [list(static['diffuse'])]
    anim = {COLOR_PROPS[p]: comps for (p, seg), comps in tracks.items() if (p, seg) in COLOR_TRACKS}
    bind = {}
    for r in sm.TEV_STAGES:
        c = mat['tev'].get(r + 3)
        if c is None:
            continue
        cands = [k for k in SLOTS if _rgba32(static[k]) == c]
        pick = next((k for k in cands if k in anim), None)
        if pick:
            bind[r] = pick

    def run(f, tex):
        col = dict(static)
        for k, comps in anim.items():
            col[k] = np.array([static[k][j] if c is None else sm.sample(c, f) for j, c in enumerate(comps)])
        tev = dict(mat['tev'])
        for r, k in bind.items():
            tev[r + 3] = _rgba32(col[k])
        prim = tuple(np.clip(col['diffuse'], 0, 1))
        return sm.tev_combine(tev, [tex, None, None], primary=prim, lit=prim)
    full = src.astype(np.float64) / 255.0

    def to8(o):
        return (np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8)
    if not anim or frames <= 1:
        return to8(run(0, full)), [[1.0, 1.0, 1.0, 1.0]]
    step = max(1, max(full.shape[:2]) // 32)
    small = full[::step, ::step]
    stats = []
    for f in range(frames):
        o = run(f, small).reshape(-1, 4)
        a = o[:, 3].sum()
        rgb = (o[:, :3] * o[:, 3:]).sum(0) / a if a > 1e-6 else o[:, :3].mean(0)
        stats.append(np.r_[rgb, o[:, 3].mean()])
    stats = np.array(stats)
    ref = int(np.argmax(stats[:, 3] * stats[:, :3].mean(1) + 1e-9 * np.arange(frames)[::-1]))
    base = stats[ref]
    gains = np.where(base > 1e-4, stats / np.maximum(base, 1e-4), 1.0)
    return to8(run(ref, full)), [list(np.clip(g, 0.0, 8.0)) for g in gains]


def material_for(mat, tex_id, name, gain=None):
    bl, at = mat.get('blend', {}), mat.get('alpha_test', {})
    src, dst = (5, 2) if bl.get('on') and bl.get('dst') == 1 else (5, 1) if bl.get('on') else (0, 0)
    cull = {0: 0, 1: 1028, 2: 1029}.get(mat.get('cull', 2), 1029)
    m = nud.Material(FLAG_BASE, src, dst, 0, 0, cull, 0, 0)
    if at.get('on') and at.get('func') in (6, 7):
        m.alpha_func, m.ref_alpha = 0x204, at['ref']
    wrap = [WRAP.get(w & 3, 1) for w in mat['wrap'][0]] if 'wrap' in mat else [1, 1]
    m.textures.append(dict(hash=tex_id, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                           unk=0, unk2=0))
    if gain is None:
        gain = [x / 255.0 for x in mat.get('colors', {}).get('diffuse', (255, 255, 255, 255))]
    co = mat['coords'][0] if 'coords' in mat else dict(scale=(1.0, 1.0), translate=(0.0, 0.0))
    scale = [s or 1.0 for s in co['scale']]
    s4, t4 = eff_uv(scale, co['translate'])
    _bits, val = float_hash(name)
    m.props = [('NU_effRotUV', [0.0, 0.0, 0.0, 0.0]), ('NU_effScaleUV', s4), ('NU_effTransUV', t4),
               ('NU_effColorGain', gain), ('NU_materialHash', [val, 0.0, 0.0, 0.0])]
    return m, dict(gain=gain, scale=scale, trans=list(co['translate']))


def anim_tracks(anim):
    """{material name: {(property, segment): components}}"""
    by_name = {}
    for md in (anim or {}).get('materials', []):
        by_name.setdefault(md['name'], {})[(md['property'], md['segment'])] = md['components']
    return by_name


def material_mta(anim, materials, statics, folder, frames):
    """the normal.bch material animation -> MTA material entries ([], skipped count); the colour gain a frame
    from bake_material (statics[name]['gains'])"""
    out, skipped = [], 0
    for mname, tracks in anim_tracks(anim).items():
        if mname not in statics:
            skipped += len(tracks)
            continue
        st = statics[mname]
        gains, trans, scales = [], [], []
        for f in range(frames):
            def comp(key, j, default):
                t = tracks.get(key)
                v = sm.sample(t[j], f) if t and j < len(t) and t[j] is not None else None
                return default if v is None else v
            gains.append(st['gains'][min(f, len(st['gains']) - 1)])
            sc = [comp((19, 2), j, st['scale'][j]) or 1.0 for j in range(2)]
            tr = [comp((21, 2), j, st['trans'][j]) for j in range(2)]
            s4, t4 = eff_uv(sc, tr)
            scales.append(s4)
            trans.append(t4)
        skipped += sum(1 for k in tracks if k not in COLOR_TRACKS + ((19, 2), (21, 2)))
        props = []
        for pname, vals in (('NU_effColorGain', gains), ('NU_effTransUV', trans), ('NU_effScaleUV', scales)):
            if any(not np.allclose(v, vals[0]) for v in vals):
                props.append(dict(name=pname, values=vals, u2=0))
        if props:
            out.append(dict(name='%s_%s' % (folder, mname), hash=float_hash('%s/%s' % (folder, mname))[0],
                            props=props))
    return out, skipped


def convert_model(mdir, folder, out_dir, tex_id, log=print):
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    model = bch.models()[0]
    bones = model['bones']
    notes = []
    # skeleton: the 3DS bones, under a TopN root unless theirs is one
    top = 0 if bones and bones[0]['name'] == 'TopN' else 1
    vb = ([('TopN', -1, se.bone_hash('TopN'))] if top else []) + \
        [(b['name'], b['parent'] + top if b['parent'] >= 0 else (0 if top else -1), se.bone_hash(b['name']))
         for b in bones]
    assert len({h for _n, _p, h in vb}) == len(vb), 'bone hash collision'
    # materials: each one's combiner baked into its texture (the same results shared)
    textures = {k: v for k, v in bch.textures().items() if not k.endswith('#format')}
    manims, vanims = bch.material_animations(), bch.visibility_animations()
    mframes = max([int(round(x['frames'])) + 1 for x in manims + vanims] + [1])     # frames 0..end
    tracks = anim_tracks(manims[0] if manims else None)
    ids, imgs = {}, []
    mats, statics = {}, {}
    for mt in model['materials']:
        if mt['textures'][0] not in textures:
            notes.append('%s: no texture, white' % mt['name'])
        img, gains = bake_material(mt, textures, tracks.get(mt['name']), mframes)
        key = (img.shape, img.tobytes())
        if key not in ids:
            ids[key] = tex_id + len(imgs)
            imgs.append((ids[key], img))
        mats[mt['name']], statics[mt['name']] = material_for(mt, ids[key], '%s/%s' % (folder, mt['name']),
                                                             gains[0])
        statics[mt['name']]['gains'] = gains
    # meshes
    meshes = []
    for obj in model['objects']:
        if obj['silhouette']:
            continue
        g = obj['geometry']()
        a = g['attrs']
        mat = model['materials'][obj['material']]
        for nodes, _skin, idx in g['parts']:
            if not len(idx):
                continue
            used = np.unique(idx)
            remap = np.full(g['count'], -1, np.int64)
            remap[used] = np.arange(len(used))
            p = nud.Polygon()
            p.pos = a[0][used]
            nrm = a[1][used] if 1 in a else np.tile([0.0, 1.0, 0.0], (len(used), 1))
            p.nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
            col = a[2][used] if 2 in a else np.ones((len(used), 4))
            p.col = np.clip(np.round(col * 127.0), 0, 255)
            uv = a[3][used] if 3 in a else np.zeros((len(used), 2))
            p.uvs = [np.c_[uv[:, 0], 1.0 - uv[:, 1]]]
            p.idx = remap[idx]
            p.materials = [mats[mat['name']].copy()]
            bone = (nodes[0] + top) if nodes else 0
            meshes.append(nud.Mesh(obj['name'], [p], bone=bone, bind=8))
    if not meshes:
        return None, ['no meshes']
    # animation
    mot = os.path.join(mdir, 'motion.bch')
    anims = sm.Bch(open(mot, 'rb').read()).skeletal_animations() if os.path.exists(mot) else []
    frames = int(round(anims[0]['frames'])) + 1 if anims else 1
    o = omo_new(frames)
    f = frames
    if top:
        omo_node(o, vb[0][2], [(0, 0, 0)] * f, [(0, 0, 0, 1)] * f, [(1, 1, 1)] * f)
    locs = se.anim_locals(anims[0], bones, frames) if anims else \
        [np.broadcast_to(se.local_matrix(b['scale'], b['rot'], b['pos']), (1, 4, 4)) for b in bones]
    for b, m in zip(bones, locs):
        t, q, sc = se.split_trs(np.broadcast_to(m, (frames, 4, 4)))
        omo_node(o, se.bone_hash(b['name']), [tuple(x) for x in t], [tuple(x) for x in q], [tuple(x) for x in sc])
    # material / visibility animation
    mta_mats, skipped = (material_mta(manims[0], mats, statics, folder, mframes) if manims else ([], 0))
    vis = []
    if vanims:
        names = [m.name for m in meshes]
        for name in dict.fromkeys(names):
            tr = vanims[0]['tracks'].get(name)
            if tr:
                bits = tr['frames'] or [tr['default']]
                vis.append((name, [(0, bits[0])] + [(i, v) for i, v in enumerate(bits) if i and v != bits[i - 1]]))
    if skipped:
        notes.append('%d material tracks not converted (combiner colours / UV rotation)' % skipped)
    d = os.path.join(out_dir, folder)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'model.nud'), 'wb').write(nud.write(meshes))
    open(os.path.join(d, 'model.nut'), 'wb').write(nut.write_ntwu(
        [(i, 0x33 if (img[..., 3] < 250).any() else 0x31, se._pow2(img)) for i, img in imgs]))
    open(os.path.join(d, 'model.vbn'), 'wb').write(vbn_le(vb))
    open(os.path.join(d, 'model.omo'), 'wb').write(o.encode())
    open(os.path.join(d, 'model.mta'), 'wb').write(
        mta.write(mframes, mta_mats, rate=60, unk=1, vis=vis) if (mta_mats or vis) else b'')
    open(os.path.join(d, 'model.xmb'), 'wb').write(effect_xmb())
    return dict(meshes=len(meshes), bones=len(vb), frames=frames, textures=len(imgs), mta=len(mta_mats),
                vis=len(vis)), notes


def convert_kind(src, kind, out, kinds, log=print):
    """every effect model of enemy KIND -> OUT/effect/enemy/KIND/model/NAME/: {name: summary}"""
    root = os.path.join(src, 'enemy', kind, 'effect', 'model')
    done = {}
    if not os.path.isdir(root):
        return done
    od = os.path.join(out, 'effect', 'enemy', kind, 'model')
    base = TEX_BASE + 0x400 * (kinds.index(kind) if kind in kinds else 0)
    for name in sorted(os.listdir(root)):
        mdir = os.path.join(root, name)
        if not os.path.exists(os.path.join(mdir, 'normal.bch')):
            continue
        summ, notes = convert_model(mdir, name, od, base, log)
        if summ:
            done[name] = summ
            base += summ['textures']
        log('  %-36s %s%s' % (name, summ, ('  (' + '; '.join(notes) + ')') if notes else ''))
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('kind')
    ap.add_argument('out')
    a = ap.parse_args()
    kinds = se.fs_kinds(a.src)
    for k in (kinds if a.kind == 'all' else [a.kind]):
        print(k)
        convert_kind(a.src, k, a.out, kinds)


if __name__ == '__main__':
    main()
