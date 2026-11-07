#!/usr/bin/env python3
"""Smash 3DS Smash Run enemies -> Smash 4 (Wii U) enemy files, in the Wii U's own enemy layout (the paths
cross_f.rpx builds: `model/enemy/%s/%s/c%02d/`, `motion/enemy/%s/%s/`, `animcmd/enemy/%s/`,
`sound/se/snd_se_enemy_%s.nus3bank`, `param/enemy/fs`):

  model/enemy/KIND/PART/cNN/model.nud, model.nut, model.vbn, model.jtb [, model.mta]
      every model part (body, and shots / missiles / hammers / parasols...): the .mbn meshes (one NUD mesh per
      .bch object, named as the object) rigged to the .bch skeleton (bind pose, blended weights kept),
      textures (PICA200 -> RGBA -> GX2 BC1 / BC3, power-of-two) plus a flat normal map, Smash 4's fighter
      body shader (0x9A011063: colour, normal, the game's shared ramp 0x10080000) with the 3DS material's
      blending, alpha test, culling, wrap and UV transform. model.mta: the model's own material animation (UV
      scrolls) and visibility timeline (the retro sprite enemies' flipbooks). The 3DS's normal.vmt (its list of
      the meshes visibility drives) is not written: the Wii U has no .vmt (not in its resource table, so
      Sm4shExplorer skips it; nothing in cross_f.rpx names it) and model.mta carries the visibility.
      model.jtb: the 3DS joint table (u16 count, count u16 bone indices) byte-swapped: the Wii U's model loader
      (0x0330466C, file slot 1) reads it big-endian with plain lhz (0x0335E8EC) into the model handle's +0xC;
      without it that pointer is null and the enemies' center_node (0x026A7C70) crashes at the first spawn.
      The 3DS model.flp (mirror table, copied as is by the loader) is not written yet.
  motion/enemy/KIND/PART/main.pac
      the motion .bch's skeletal animations (motion/PART/main.bch or main/*.bch), one OMO each (name.omo),
      sampled every frame 0..end (H3D keys, linear / hermite / step, Euler XYZ rotations as quaternions). The
      bones keep the 3DS axes (scripts' offsets are in them), so a bone turned ~180 degrees (the Goomba's feet)
      loses a little precision in OMO rotation type 5 (w rebuilt from 16-bit x y z): 0.064 units at worst on
      the Goomba, 0.27 on Mahva (198 units).
  motion/enemy/KIND/PART/material_anime.pac
      the material_anime .bch visibility / material animations, one MTA a motion (mesh visibility by name), so
      a motion can show the damage face.
  animcmd/enemy/KIND/*.bin
      the 3DS ACMD byte-swapped to the Wii U's big-endian (checked: every command one tools/acmd.py knows).
  sound/se/snd_se_enemy_KIND.nus3bank, param/enemy/fs/enemy_param_vl_KIND.bin
      copied: the 3DS bank is already the Wii U's layout (NUS3 chunks, little-endian TONE, IDSP audio) and the
      vl params the same typed big-endian format.
  Not converted (yet): the enemies' particle effects (effect/: 3DS .ptcl SPBD / .efc, effect models, trails).

  python3 tools/s3ds_enemy.py SRC_ROOT KIND|all OUT [--tex-id 0x4E000000]
      SRC_ROOT: a tools/s3ds_unpack.py extract (holds enemy/ and param/enemy/fs/). "all": every Smash Run
      enemy (a param/enemy/fs vl file), texture IDs 0x4E000000 + 0x1000 an enemy + 0x100 a model part.
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
import acmd  # noqa: E402
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
import s3ds_model as sm  # noqa: E402
from ultimate_fighter import _mat_quat, _node, euler_mat, float_hash  # noqa: E402

WHITE = 127                         # NUD vertex colour 1.0
RAMP = 0x10080000                   # the game's shared fighter ramp (every 0x9A011063 body material's third)
OMO_HEAD = struct.pack('>HHIH', 1, 3, 0x091E100C, 0)       # Smash Forge OMO.cs's header words
# Smash 4's skinned fighter body material (Zelda's body, as tools/ultimate_fighter.py templates it): colour,
# normal, ramp; a neutral rim and specular
BODY_FLAGS = 0x9A011063
BODY_PROPS = [('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0]), ('NU_lightMapColorOffset', [0.0, 0.0, 0.0, 0.0]),
              ('NU_specularParams', [0.0, 2.95, 0.0, 0.0]), ('NU_fresnelParams', [0.64, 0.0, 0.0, 1.0]),
              ('NU_fresnelColor', [0.32, 0.32, 0.32, 1.0]), ('NU_specularColor', [0.1, 0.1, 0.1, 2.0]),
              ('NU_aoMinGain', [0.222, 0.222, 0.222, 0.3]), ('NU_blinkColor', [0.0, 0.0, 0.0, 0.0]),
              ('NU_alphaBlendParams', [0.0, 0.0, 0.0, 0.0]), ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])]


# a material whose UV rotates (no body shader rotates UVs): Smash 4's skinned effect shader (Captain Falcon's
# EffCaptainFalconPunch "..._eff_skin" mesh), whose vertex program has NU_effRotUV (s3ds_model.nud_eff_uv)
ROT_FLAGS = 0xB0241100
ROT_PROPS = [('NU_effRotUV', [0.0, 0.0, 0.0, 0.0]), ('NU_effScaleUV', [1.0, 1.0, 0.0, 0.0]),
             ('NU_effTransUV', [0.0, 0.0, 0.0, 0.0]), ('NU_effColorGain', [1.0, 1.0, 1.0, 1.0]),
             ('NU_angleFadeParams', [0.0, 1.0, 0.0, 0.0]), ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])]


def rotating_materials(*anims):
    """names of the materials a material animation rotates the UVs of (H3D property 20: coordinator 0)"""
    return {md['name'] for a in anims if a for md in a['materials'] if md['property'] == 20}


def bone_hash(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


# ---------------------------------------------------------------- skeleton
def local_matrix(scale, rot, pos):
    m = np.eye(4)
    m[:3, :3] = euler_mat(*rot) @ np.diag(scale)
    m[:3, 3] = pos
    return m


def jtb_bytes(data, nbones):
    """the 3DS model.jtb (little-endian u16 count + count u16 bone indices) as the Wii U reads it: big-endian
    (0x0335E8EC: size == 2 * count + 2 -> one table; else two counts and their tables). Every index must be a
    bone of the converted skeleton (the VBN keeps the .bch's bone order) or 0xFFFF (no bone)."""
    n = len(data) // 2
    v = struct.unpack('<%dH' % n, data[:2 * n])
    if v[0] * 2 + 2 == len(data):
        idx = v[1:]
    else:
        assert (v[0] + v[1]) * 2 + 4 == len(data), 'model.jtb: unknown layout (%d bytes)' % len(data)
        idx = v[2:]
    assert all(i < nbones or i == 0xFFFF for i in idx), 'model.jtb: index out of the skeleton (%d bones): %s' % (nbones, idx)
    return struct.pack('>%dH' % n, *v)


def vbn_bytes(bones):
    """little-endian model.vbn as the game's fighters' (' NBV', 2, 1), every bone type 0; the 3DS bind pose
    as it is (both games: R = Rz Ry Rx, radians)"""
    n = len(bones)
    out = struct.pack('<4sHHI4I', b' NBV', 2, 1, n, n, 0, 0, 0)
    for b in bones:
        out += b['name'].encode()[:63].ljust(64, b'\0') + struct.pack(
            '<IiI', 0, 0x0FFFFFFF if b['parent'] < 0 else b['parent'], bone_hash(b['name']))
    for b in bones:
        out += struct.pack('<9f', *b['pos'], *b['rot'], *b['scale'])
    return out


# ---------------------------------------------------------------- model
def tangents(pos, nrm, uv, tri):
    """per-vertex tangent / bitangent from the UVs (Lengyel), orthogonalised against the normal"""
    tan = np.zeros_like(pos)
    bit = np.zeros_like(pos)
    for a, b, c in tri:
        e1, e2 = pos[b] - pos[a], pos[c] - pos[a]
        d1, d2 = uv[b] - uv[a], uv[c] - uv[a]
        r = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(r) < 1e-12:
            continue
        t = (e1 * d2[1] - e2 * d1[1]) / r
        s = (e2 * d1[0] - e1 * d2[0]) / r
        for v in (a, b, c):
            tan[v] += t
            bit[v] += s
    out_t, out_b = np.zeros_like(pos), np.zeros_like(pos)
    for i in range(len(pos)):
        n = nrm[i]
        t = tan[i] - n * np.dot(n, tan[i])
        if np.linalg.norm(t) < 1e-8:
            t = np.cross(n, [0.0, 1.0, 0.0] if abs(n[1]) < 0.9 else [1.0, 0.0, 0.0])
        t /= np.linalg.norm(t)
        b = np.cross(n, t)
        if np.dot(b, bit[i]) < 0:
            b = -b
        out_t[i], out_b[i] = t, b
    return out_t, out_b


def body_material(mat, color_id, normal_id, wrap, rotating=False):
    """Smash 4's skinned body material for a 3DS material: its blending (H3D fragment operations: source alpha /
    one minus source alpha -> NUD 1 / 1; source alpha / one, additive -> 1 / 2; anything else blended -> 1 / 1),
    alpha test (greater -> 516, greater or equal -> 518, the 3DS reference), culling (back -> 1029, front ->
    1028, none -> 0) and texture transform (NU_colorSamplerUV, see sampler_uv). ROTATING (its UV rotates, or is
    turned): the skinned effect material (ROT_FLAGS, unlit) with the transform as NU_effRotUV / ScaleUV /
    TransUV"""
    if rotating or abs(mat.get('coords', [{}])[0].get('rotate', 0.0)) > 1e-6:
        return rot_material(mat, color_id, wrap)
    bl, at = mat.get('blend', {}), mat.get('alpha_test', {})
    src = dst = 0
    if bl.get('on'):
        src, dst = (1, 2) if bl['dst'] == 1 else (1, 1)
    af = ref = 0
    if at.get('on') and at['func'] in (6, 7):
        af, ref = (516 if at['func'] == 6 else 518), at['ref']
    cull = {0: 0, 1: 1028, 2: 1029}.get(mat.get('cull', 2), 1029)
    m = nud.Material(BODY_FLAGS, src, dst, af, ref, cull)
    for tid in (color_id, normal_id, RAMP):
        m.textures.append(dict(hash=tid, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                               unk=0, unk2=0))
    m.textures[2]['wrap_s'] = m.textures[2]['wrap_t'] = 3
    _bits, val = float_hash(mat['name'])
    uv = sampler_uv(mat['coords'][0]) if 'coords' in mat else [1.0, 1.0, 0.0, 0.0]
    m.props = [(n, [val, 0.0, 0.0, 0.0] if n == 'NU_materialHash' else uv if n == 'NU_colorSamplerUV' else list(v))
               for n, v in BODY_PROPS]
    return m


def sampler_uv(coord, translate=None, scale=None):
    """3DS texture coordinator (scale, translate) -> NUD NU_colorSamplerUV for the NUD's V' = 1 - V
    (s3ds_model.nud_sampler_uv: H3D's Maya transform, SPICA's, translates then scales; the body vertex programs
    do U = s.x (u + t.x), V = s.y (V' + t.y)): s = the 3DS scale, t = (-tu, (1 - sv) / sv + tv). Rotation
    can't be expressed: a rotating material is a rot_material."""
    return sm.nud_sampler_uv(scale or coord['scale'], translate or coord['translate'], coord.get('transform', 0))


def eff_uv_flat(coord, scale=None, rot=None, translate=None):
    """the coordinator (or its animated values) as NU_effRotUV, NU_effScaleUV, NU_effTransUV"""
    sc = [x or 1.0 for x in (scale or coord['scale'])]
    return sm.nud_eff_uv(sc, coord.get('rotate', 0.0) if rot is None else rot,
                         translate or coord['translate'], coord.get('transform', 0))


def rot_material(mat, color_id, wrap):
    """the skinned effect material (ROT_FLAGS) for a 3DS material with a rotating UV: colour texture only,
    its blending (alpha -> 5 / 1, additive -> 5 / 2), alpha test, culling, the UV transform"""
    bl, at = mat.get('blend', {}), mat.get('alpha_test', {})
    src, dst = ((5, 2) if bl['dst'] == 1 else (5, 1)) if bl.get('on') else (0, 0)
    af = ref = 0
    if at.get('on') and at['func'] in (6, 7):
        af, ref = (516 if at['func'] == 6 else 518), at['ref']
    cull = {0: 0, 1: 1028, 2: 1029}.get(mat.get('cull', 2), 1029)
    m = nud.Material(ROT_FLAGS, src, dst, af, ref, cull)
    m.textures.append(dict(hash=color_id, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                           unk=0, unk2=0))
    r4, s4, t4 = eff_uv_flat(mat['coords'][0]) if 'coords' in mat else ([0.0] * 4, [1.0, 1.0, 0.0, 0.0],
                                                                         [0.0] * 4)
    _bits, val = float_hash(mat['name'])
    m.props = [(n, {'NU_effRotUV': r4, 'NU_effScaleUV': s4, 'NU_effTransUV': t4,
                    'NU_materialHash': [val, 0.0, 0.0, 0.0]}.get(n, list(v))) for n, v in ROT_PROPS]
    return m


# H3D wrap (0 clamp to edge, 1 border, 2 repeat, 3 mirror) -> NUD (1 repeat, 2 mirror, 3 clamp)
PICA_WRAP = {0: 3, 1: 3, 2: 1, 3: 2}


def _resized(img, w, h):
    from PIL import Image
    if img.shape[:2] == (h, w):
        return img
    return np.asarray(Image.fromarray(img, 'RGBA').resize((w, h), Image.BILINEAR))


def build_model(bch, mbn, tex_id, log=print, rotating=None):
    """-> (model.nud, model.nut, model.vbn, model) bytes. Texture unit 0 is the colour (units 1 / 2 are the 3DS
    shader's reflection / specular maps, left out), except a unit-1 texture named *alpha*: a mask, put into the
    colour's alpha. A material without a texture gets a flat one of its diffuse colour."""
    model = bch.models()[0]
    bones = model['bones']
    textures = {k: v for k, v in bch.textures().items() if not k.endswith('#format')}
    assert len(model['objects']) == len(mbn), (len(model['objects']), len(mbn))
    if rotating is None:
        rotating = rotating_materials(*bch.material_animations())
    model['rotating'] = set(rotating)
    ids, images = {}, []

    def tex(key, img):
        if key not in ids:
            ids[key] = tex_id + len(images)
            images.append((ids[key], img))
        return ids[key]
    flat = tex('#flat', np.full((64, 64, 4), (128, 128, 255, 255), np.uint8))
    meshes = []
    for obj, mi in zip(model['objects'], sm.match_objects(model['objects'], mbn)):
        me = mbn[mi]
        if obj['silhouette']:
            log('  skip silhouette object %s' % obj['name'])
            continue
        mat = model['materials'][obj['material']]
        wrap = (1, 1)
        if 'wrap' in mat:
            wrap = tuple(PICA_WRAP[x & 3] for x in mat['wrap'][0])
        t0, t1 = mat['textures'][0], mat['textures'][1]
        if t0 in textures:
            img = textures[t0]
            if t1 in textures and 'alpha' in t1.lower():
                mask = _resized(textures[t1], img.shape[1], img.shape[0])
                img = img.copy()
                img[..., 3] = np.minimum(img[..., 3], mask[..., 0])
                color = tex((t0, t1), img)
            else:
                color = tex(t0, img)
        else:
            dc = mat.get('colors', {}).get('diffuse', (255, 255, 255, 255))
            color = tex(('#solid', dc), np.full((8, 8, 4), dc, np.uint8))
            log('  material %s: no texture %r, its diffuse colour %s' % (mat['name'], t0, dc))
        a = me['attrs']
        polys = []
        for bone_list, idx in me['parts']:
            used = np.unique(idx)
            remap = np.full(me['count'], -1, np.int64)
            remap[used] = np.arange(len(used))
            p = nud.Polygon()
            p.pos = a[0][used]
            nrm = a[1][used] if 1 in a else np.tile([0.0, 1.0, 0.0], (len(used), 1))
            p.nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
            uv = a[3][used] if 3 in a else np.zeros((len(used), 2))
            p.uvs = [np.c_[uv[:, 0], 1.0 - uv[:, 1]]]        # the 3DS's V counts up from the bottom
            p.col = np.full((len(used), 4), WHITE)
            p.idx = remap[idx]
            tri = p.idx.reshape(-1, 3)
            p.tan, p.bit = tangents(p.pos, p.nrm, p.uvs[0], tri)
            n = len(used)
            if 5 in a:
                bi = a[5][used].astype(np.int64)
                bw = a[6][used] if 6 in a else np.c_[np.ones(n), np.zeros((n, bi.shape[1] - 1))]
            else:
                bi, bw = np.zeros((n, 1), np.int64), np.ones((n, 1))
            p.bones = np.zeros((n, 4), np.int64)
            for j in range(bi.shape[1]):
                p.bones[:, j] = np.asarray(bone_list)[np.minimum(bi[:, j], len(bone_list) - 1)]
            w = np.zeros((n, 4))
            w[:, :bw.shape[1]] = bw
            w /= np.maximum(w.sum(1, keepdims=True), 1e-8)
            q = np.floor(w * 255).astype(np.int64)
            q[:, 0] += 255 - q.sum(1)
            p.weights = q
            p.bones[q == 0] = p.bones[:, :1].repeat(4, 1)[q == 0]
            p.materials = [body_material(mat, color, flat, wrap, mat['name'] in rotating)]
            polys.append(p)
        m = nud.Mesh(obj['name'], polys, -1, 4)
        meshes.append(m)
        if polys and polys[0].materials[0].flags == ROT_FLAGS:
            log('  mesh %s: material %s rotates its UV: skinned effect shader 0x%08X' % (
                obj['name'], mat['name'], ROT_FLAGS))
        log('  mesh %-24s %5d vertices, %5d triangles' % (
            obj['name'], sum(len(p.pos) for p in polys), sum(len(p.idx) // 3 for p in polys)))
    nud_b = nud.write(meshes, top_bone=len(bones) - 1)
    nut_b = nut.write_ntwu([(i, 0x33 if (img[..., 3] < 250).any() else 0x31, _pow2(img)) for i, img in images])
    return nud_b, nut_b, vbn_bytes(bones), model


def _pow2(img):
    """GX2 textures here: power-of-two sides, at least 8"""
    h, w = img.shape[:2]
    p = [max(8, 1 << (x - 1).bit_length()) for x in (w, h)]
    return _resized(img, p[0], p[1]) if (p[0], p[1]) != (w, h) else img


# ---------------------------------------------------------------- motions
def anim_locals(anim, bones, frames):
    """per bone [frames, 4, 4] local matrices"""
    by_name = {b['name']: b for b in anim['bones']}
    out = []
    for b in bones:
        a = by_name.get(b['name'])
        mats = np.empty((frames, 4, 4))
        for f in range(frames):
            scale, rot, pos = list(b['scale']), list(b['rot']), list(b['pos'])
            if a is not None and a['type'] == 4:
                for (kind, axis), g in a['tracks'].items():
                    v = sm.sample(g, f)
                    {'scale': scale, 'rot': rot, 'pos': pos}[kind][axis] = v
                mats[f] = local_matrix(scale, rot, pos)
            elif a is not None and a['type'] == 7:
                m = local_matrix(scale, rot, pos)
                if 'quat' in a:
                    q = _track_at(a['quat'], f)
                    x, y, z, w = q
                    m[:3, :3] = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                                          [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
                if 'scale' in a:
                    m[:3, :3] = m[:3, :3] @ np.diag(_track_at(a['scale'], f))
                if 'pos' in a:
                    m[:3, 3] = _track_at(a['pos'], f)
                mats[f] = m
            elif a is not None and a['type'] == 9:
                mt = a['matrices'][min(f, len(a['matrices']) - 1)]
                mats[f] = np.vstack([mt, [0, 0, 0, 1]])
            else:
                mats[f] = local_matrix(scale, rot, pos)
        out.append(mats)
    return out


def _track_at(t, f):
    vals = t['values']
    i = int(min(max(f - t.get('start', 0), 0), len(vals) - 1))
    return vals[i]


def split_trs(m):
    """[frames, 4, 4] local matrices (R x diag(scale) + translation) -> (translations, quaternions, scales),
    exact also for a mirrored (negative) scale and a zero one (the 3DS effects squash axes to 0): a zero
    column takes its rotation axis from the others, a negative determinant goes on the smallest axis"""
    m = np.asarray(m, float)
    t = m[:, :3, 3]
    sc = np.linalg.norm(m[:, :3, :3], axis=1)
    rots = np.empty((len(m), 3, 3))
    for f in range(len(m)):
        r = m[f, :3, :3].copy()
        live = sc[f] > 1e-8
        for j in range(3):
            r[:, j] = r[:, j] / sc[f, j] if live[j] else 0.0
        dead = [j for j in range(3) if not live[j]]
        if len(dead) == 3:
            r = np.eye(3)
        elif len(dead) == 2:
            j = next(j for j in range(3) if live[j])
            a = np.eye(3)[np.argmin(np.abs(r[:, j]))]
            k1, k2 = (j + 1) % 3, (j + 2) % 3
            r[:, k1] = np.cross(r[:, j], a)
            r[:, k1] /= np.linalg.norm(r[:, k1])
            r[:, k2] = np.cross(r[:, j], r[:, k1])
        elif len(dead) == 1:
            k = dead[0]
            r[:, k] = np.cross(r[:, (k + 1) % 3], r[:, (k + 2) % 3])
            r[:, k] /= max(np.linalg.norm(r[:, k]), 1e-12)
        if np.linalg.det(r) < 0:
            k = int(np.argmin(sc[f]))
            r[:, k] = -r[:, k]
            sc[f, k] = -sc[f, k]
        rots[f] = r
    return t, _mat_quat(rots), sc


def omo_from(anim, bones):
    frames = int(round(anim['frames'])) + 1          # keys sit on frames 0..end, both ends kept
    o = omo.Omo(b'OMO ' + OMO_HEAD + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
    for b, m in zip(bones, anim_locals(anim, bones, frames)):
        t, q, sc = split_trs(m)
        # keep consecutive quaternions in one hemisphere (_node then makes w >= 0 for the xyz encoding)
        _node(o, bone_hash(b['name']), t, q, sc)
    return o.encode(), frames


def anim_mta(vis=None, mats=None, model=None, mesh_names=(), rotating=()):
    """a visibility animation and / or a material animation (H3D) -> MTA bytes. Visibility: mesh states by
    name. Material: texture coordinator 0's translate / scale (UV scrolls, the common case) as
    NU_colorSamplerUV a frame, by the material's NU_materialHash; for a ROTATING material (a rot_material)
    translate / scale / rotation as NU_effTransUV / ScaleUV / RotUV; the other animated properties (combiner
    constant colours, coordinators 1 / 2) are counted, not converted."""
    frames = max(1, int(round(max(a['frames'] for a in (vis, mats) if a))))
    vlist = []
    if vis:
        for name in mesh_names:
            tr = vis['tracks'].get(name)
            if tr is None:
                continue
            bits = tr['frames'] or [tr['default']]
            keys = [(0, bits[0])] + [(f, v) for f, v in enumerate(bits) if f and v != bits[f - 1]]
            vlist.append((name, keys))
    mlist, skipped = [], 0
    if mats and model:
        by_name = {m['name']: m for m in model['materials']}
        for md in mats['materials']:
            mat = by_name.get(md['name'])
            if mat is None or md['property'] not in (0x13, 0x14, 0x15) or \
                    (md['property'] == 0x14 and md['name'] not in rotating):
                skipped += 1
                continue
            entry = next((e for e in mlist if e['name'] == md['name']), None)
            if entry is None:
                entry = dict(name=md['name'], hash=float_hash(md['name'])[0], tracks={})
                mlist.append(entry)
            entry['tracks'][md['property']] = md['components']
        for e in mlist:
            c = model and by_name[e['name']]['coords'][0]
            rot = e['name'] in rotating
            vals, rots, trans = [], [], []
            for f in range(frames):
                def comp(prop, j, default):
                    t = e['tracks'].get(prop)
                    v = sm.sample(t[j], f) if t and j < len(t) and t[j] is not None else None
                    return default if v is None else v
                sc = (comp(0x13, 0, c['scale'][0]), comp(0x13, 1, c['scale'][1]))
                tr = (comp(0x15, 0, c['translate'][0]), comp(0x15, 1, c['translate'][1]))
                if rot:
                    r4, s4, t4 = eff_uv_flat(c, sc, comp(0x14, 0, c.get('rotate', 0.0)), tr)
                    rots.append(r4)
                    vals.append(s4)
                    trans.append(t4)
                else:
                    vals.append(sampler_uv(c, tr, sc))
            if rot:
                e['props'] = [dict(name=n, values=v) for n, v in (('NU_effRotUV', rots), ('NU_effScaleUV', vals),
                                                                  ('NU_effTransUV', trans))
                              if any(not np.allclose(x, v[0]) for x in v)]
            else:
                e['props'] = [dict(name='NU_colorSamplerUV', values=vals)]
        mlist = [e for e in mlist if e.get('props')]
    out = mta.write(frames, [dict(name=e['name'], hash=e['hash'], props=e['props']) for e in mlist], vis=vlist)
    return out, skipped


def vis_mta(anim, mesh_names):
    return anim_mta(vis=anim, mesh_names=mesh_names)[0]


# ---------------------------------------------------------------- ACMD
def acmd_be(d):
    """3DS (little-endian) ACMD -> Wii U (big-endian): every field is a 32-bit word (header, script table,
    command CRCs, parameters; Goto offsets are in words), so each word after the magic is byte-swapped"""
    assert d[:4] == b'ACMD' and len(d) % 4 == 0
    if d[4] == 0:
        return d                                    # already big-endian
    n = len(d) // 4
    return b'ACMD' + struct.pack('>%dI' % (n - 1), *struct.unpack('<%dI' % n, d)[1:])


# ---------------------------------------------------------------- driver
def _model_dirs(base):
    """[(part, 'cNN', dir)] of an enemy's models"""
    out = []
    mroot = os.path.join(base, 'model')
    for part in sorted(os.listdir(mroot)) if os.path.isdir(mroot) else []:
        for c in sorted(os.listdir(os.path.join(mroot, part))):
            d = os.path.join(mroot, part, c)
            if os.path.exists(os.path.join(d, 'normal.mbn')):
                out.append((part, c, d))
    return out


def _motion_files(base):
    """{part: [motion .bch]}: motion/PART/main.bch, or motion/PART/main/*.bch (one motion a file)"""
    out = {}
    mroot = os.path.join(base, 'motion')
    for part in sorted(os.listdir(mroot)) if os.path.isdir(mroot) else []:
        one = os.path.join(mroot, part, 'main.bch')
        many = os.path.join(mroot, part, 'main')
        if os.path.exists(one):
            out[part] = [one]
        elif os.path.isdir(many):
            out[part] = [os.path.join(many, f) for f in sorted(os.listdir(many)) if f.endswith('.bch')]
    return out


def convert(src, kind, out, tex_id, log=print):
    """every model part (model/PART/cNN), motion folder, material / visibility animation, ACMD, the sound bank
    and the vl params of enemy KIND. Returns {part: model} (c00 models) and a summary dict."""
    base = os.path.join(src, 'enemy', kind)
    summary = dict(kind=kind, models=[], motions=0, mtas=0, skipped_mat_props=0, acmd=[], sound=False, params=False)
    models = {}
    for pi, (part, c, d) in enumerate(_model_dirs(base)):
        bch = sm.Bch(open(os.path.join(d, 'normal.bch'), 'rb').read())
        mbn = sm.read_mbn(open(os.path.join(d, 'normal.mbn'), 'rb').read())
        log('model %s/%s/%s' % (kind, part, c))
        nud_b, nut_b, vbn_b, model = build_model(bch, mbn, tex_id + 0x100 * pi, log)
        od = os.path.join(out, 'model', 'enemy', kind, part, c)
        os.makedirs(od, exist_ok=True)
        for n, b in (('model.nud', nud_b), ('model.nut', nut_b), ('model.vbn', vbn_b)):
            open(os.path.join(od, n), 'wb').write(b)
        if os.path.exists(os.path.join(d, 'model.jtb')):
            open(os.path.join(od, 'model.jtb'), 'wb').write(
                jtb_bytes(open(os.path.join(d, 'model.jtb'), 'rb').read(), len(model['bones'])))
        manims, vanims = bch.material_animations(), bch.visibility_animations()
        if manims or vanims:
            # the model's own (always running) material / visibility animation: model.mta, as stages' /
            # fighters' models. The retro sprite enemies (cucco, flyingman, shiroiobake) keep their flipbooks
            # here: one long visibility timeline of sprite meshes
            meshes = [o['name'] for o in model['objects'] if not o['silhouette']]
            b, skipped = anim_mta(vanims[0] if vanims else None, manims[0] if manims else None, model, meshes,
                                  model['rotating'])
            open(os.path.join(od, 'model.mta'), 'wb').write(b)
            summary['skipped_mat_props'] += skipped
            log('  model.mta (%s)' % ', '.join('%s %s %d frames' % (k, a[0]['name'], a[0]['frames'])
                                                for k, a in (('material', manims), ('visibility', vanims)) if a))
        if c == 'c00':
            models[part] = model
        summary['models'].append('%s/%s: %d meshes, %d bones, %d textures' % (
            part, c, len(model['objects']), len(model['bones']), len(model['materials'])))
        # per-motion visibility / material animations: model/PART/cNN/material_anime/MPART/main/*.bch
        ma = os.path.join(d, 'material_anime')
        if c == 'c00' and os.path.isdir(ma):
            for mpart in sorted(os.listdir(ma)):
                adir = os.path.join(ma, mpart, 'main')
                entries = []
                for fn in sorted(os.listdir(adir)) if os.path.isdir(adir) else []:
                    ab = sm.Bch(open(os.path.join(adir, fn), 'rb').read())
                    vis = {a['name']: a for a in ab.visibility_animations()}
                    mats = {a['name']: a for a in ab.material_animations()}
                    for name in sorted(set(vis) | set(mats)):
                        b, skipped = anim_mta(vis.get(name), mats.get(name), model,
                                              [o['name'] for o in model['objects'] if not o['silhouette']],
                                              model['rotating'])
                        entries.append((name + '.mta', b))
                        summary['skipped_mat_props'] += skipped
                if entries:
                    md = os.path.join(out, 'motion', 'enemy', kind, mpart)
                    os.makedirs(md, exist_ok=True)
                    omo.pac_write(os.path.join(md, 'material_anime.pac'), entries)
                    summary['mtas'] += len(entries)
                    log('  %s/material_anime.pac: %d MTAs' % (mpart, len(entries)))
    for mpart, files in _motion_files(base).items():
        model = models.get(mpart) or models.get('body') or next(iter(models.values()), None)
        if model is None:
            log('  motion %s: no model for its skeleton, skipped' % mpart)
            continue
        entries = []
        for fn in files:
            for a in sm.Bch(open(fn, 'rb').read()).skeletal_animations():
                b, frames = omo_from(a, model['bones'])
                entries.append((a['name'] + '.omo', b))
        if entries:
            md = os.path.join(out, 'motion', 'enemy', kind, mpart)
            os.makedirs(md, exist_ok=True)
            omo.pac_write(os.path.join(md, 'main.pac'), entries)
            summary['motions'] += len(entries)
            log('  motion %s/main.pac: %d OMOs' % (mpart, len(entries)))
    s = os.path.join(base, 'animcmd')
    if os.path.isdir(s):
        dst = os.path.join(out, 'animcmd', 'enemy', kind)
        os.makedirs(dst, exist_ok=True)
        for fn in sorted(os.listdir(s)):
            b = acmd_be(open(os.path.join(s, fn), 'rb').read())
            open(os.path.join(dst, fn), 'wb').write(b)
            f = acmd.ACMDFile.load(os.path.join(dst, fn))       # every command one the Wii U knows
            summary['acmd'].append('%s %d' % (fn, len(f.scripts)))
            log('  animcmd %s: %d scripts, %d commands' % (fn, len(f.scripts), sum(map(len, f.scripts.values()))))
    snd = os.path.join(base, 'snd_se_enemy_%s.nus3bank' % kind)
    if os.path.exists(snd):
        os.makedirs(os.path.join(out, 'sound', 'se'), exist_ok=True)
        shutil.copy(snd, os.path.join(out, 'sound', 'se'))
        summary['sound'] = True
    prm = os.path.join(src, 'param', 'enemy', 'fs', 'enemy_param_vl_%s.bin' % kind)
    if os.path.exists(prm):
        os.makedirs(os.path.join(out, 'param', 'enemy', 'fs'), exist_ok=True)
        shutil.copy(prm, os.path.join(out, 'param', 'enemy', 'fs'))
        summary['params'] = True
    return models, summary


def fs_kinds(src):
    """the Smash Run enemies: the ones with a param/enemy/fs vl file and an enemy folder"""
    pd = os.path.join(src, 'param', 'enemy', 'fs')
    ks = [f[len('enemy_param_vl_'):-4] for f in os.listdir(pd) if f.startswith('enemy_param_vl_')]
    return sorted(k for k in ks if os.path.isdir(os.path.join(src, 'enemy', k)))


def tex_base(kind, kinds):
    """texture IDs: 0x4E000000 + 0x1000 an enemy (its index among the Smash Run enemies, sorted) + 0x100 a
    model part"""
    return 0x4E000000 + 0x1000 * kinds.index(kind)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('kind', help='an enemy, or "all" (every Smash Run enemy: a param/enemy/fs vl file)')
    ap.add_argument('out')
    ap.add_argument('--tex-id', type=lambda s: int(s, 0), default=None)
    a = ap.parse_args()
    kinds = fs_kinds(a.src)
    todo = kinds if a.kind == 'all' else [a.kind]
    failed = []
    for k in todo:
        try:
            convert(a.src, k, a.out, a.tex_id if a.tex_id is not None else tex_base(k, kinds if k in kinds else [k]))
        except Exception as e:                          # noqa: BLE001 - report every enemy, then fail
            failed.append((k, repr(e)))
            print('FAILED %s: %r' % (k, e))
    if failed:
        sys.exit('%d failed: %s' % (len(failed), ', '.join(k for k, _ in failed)))


if __name__ == '__main__':
    main()
