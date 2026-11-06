#!/usr/bin/env python3
"""Smash 3DS Smash Run enemy -> Smash 4 (Wii U) enemy files, in the Wii U's own enemy layout (the paths
cross_f.rpx builds: `model/enemy/%s/body/c00/`, `motion/enemy/%s/body/`, `animcmd/enemy/%s/`,
`sound/se/snd_se_enemy_%s.nus3bank`, `param/enemy/fs`):

  model/enemy/KIND/body/c00/model.nud, model.nut, model.vbn
      the .mbn meshes (one NUD mesh per .bch object, named as the object: the Goomba's normal_mh / damage_mh
      faces) rigged to the .bch skeleton (bones, bind pose, rigid weights kept), textures (PICA200 -> RGBA ->
      GX2 BC1 / BC3) plus a flat normal map, Smash 4's fighter body shader (0x9A011063: colour, normal, the
      game's shared ramp 0x10080000).
  motion/enemy/KIND/body/main.pac
      the motion .bch's skeletal animations, one OMO each (name.omo), sampled every frame 0..end (H3D keys,
      linear / hermite / step, Euler XYZ rotations as quaternions). The bones keep the 3DS axes (scripts'
      offsets are in them), so a bone turned ~180 degrees (the Goomba's feet) loses a little precision in
      OMO rotation type 5 (w rebuilt from 16-bit x y z): 0.064 units at worst on the Goomba.
  motion/enemy/KIND/body/material_anime.pac
      the material_anime .bch visibility animations, one MTA each (mesh visibility by name), so a motion can
      show the damage face.
  animcmd/enemy/KIND/*.bin
      the 3DS ACMD byte-swapped to the Wii U's big-endian (checked: every command one tools/acmd.py knows).
  sound/se/snd_se_enemy_KIND.nus3bank, param/enemy/fs/enemy_param_vl_KIND.bin
      copied: the 3DS bank is already the Wii U's layout (NUS3 chunks, little-endian TONE, IDSP audio) and the
      vl params the same typed big-endian format.

  python3 tools/s3ds_enemy.py SRC_ROOT KIND OUT [--tex-id 0x40F00000]
      SRC_ROOT: a tools/s3ds_unpack.py extract (holds enemy/KIND/ and param/enemy/fs/).
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


def bone_hash(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


# ---------------------------------------------------------------- skeleton
def local_matrix(scale, rot, pos):
    m = np.eye(4)
    m[:3, :3] = euler_mat(*rot) @ np.diag(scale)
    m[:3, 3] = pos
    return m


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


def body_material(name, color_id, normal_id, wrap):
    m = nud.Material(BODY_FLAGS, 0, 0, 0, 0, 1029)
    for tid in (color_id, normal_id, RAMP):
        m.textures.append(dict(hash=tid, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                               unk=0, unk2=0))
    m.textures[2]['wrap_s'] = m.textures[2]['wrap_t'] = 3
    _bits, val = float_hash(name)
    m.props = [(n, [val, 0.0, 0.0, 0.0] if n == 'NU_materialHash' else list(v)) for n, v in BODY_PROPS]
    return m


# H3D wrap (0 clamp to edge, 1 border, 2 repeat, 3 mirror) -> NUD (1 repeat, 2 mirror, 3 clamp)
PICA_WRAP = {0: 3, 1: 3, 2: 1, 3: 2}


def build_model(bch, mbn, tex_id, log=print):
    """-> (model.nud, model.nut, model.vbn) bytes"""
    model = bch.models()[0]
    bones = model['bones']
    textures = bch.textures()
    ids, images = {}, []
    for name, img in textures.items():
        if name.endswith('#format'):
            continue
        ids[name] = tex_id + len(images)
        images.append((ids[name], img))
    flat = tex_id + len(images)
    images.append((flat, np.full((64, 64, 4), (128, 128, 255, 255), np.uint8)))
    meshes = []
    for k, (obj, me) in enumerate(zip(model['objects'], mbn)):
        if obj['silhouette']:
            log('  skip silhouette object %s' % obj['name'])
            continue
        mat = model['materials'][obj['material']]
        wrap = (1, 1)
        if 'wrap' in mat:
            wrap = tuple(PICA_WRAP[x & 3] for x in mat['wrap'][0])
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
            p.weights = np.zeros((n, 4), np.int64)
            for j in range(bi.shape[1]):
                p.bones[:, j] = np.asarray(bone_list)[bi[:, j]]
            w = np.zeros((n, 4))
            w[:, :bw.shape[1]] = bw
            w /= np.maximum(w.sum(1, keepdims=True), 1e-8)
            q = np.floor(w * 255).astype(np.int64)
            q[:, 0] += 255 - q.sum(1)
            p.weights = q
            p.bones[q == 0] = p.bones[:, :1].repeat(4, 1)[q == 0]
            tex = mat['textures'][0]
            p.materials = [body_material(mat['name'], ids[tex], flat, wrap)]
            polys.append(p)
        m = nud.Mesh(obj['name'], polys, -1, 4)
        meshes.append(m)
        log('  mesh %-12s %d vertices, %d triangles, bones %s' % (
            obj['name'], sum(len(p.pos) for p in polys), sum(len(p.idx) // 3 for p in polys),
            sorted({bones[b]['name'] for p in polys for b in np.unique(p.bones)})))
    nud_b = nud.write(meshes, top_bone=len(bones) - 1)
    nut_b = nut.write_ntwu([(i, 0x33 if (img[..., 3] < 250).any() else 0x31, img) for i, img in images])
    return nud_b, nut_b, vbn_bytes(bones), model


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


def omo_from(anim, bones):
    frames = int(round(anim['frames'])) + 1          # keys sit on frames 0..end, both ends kept
    o = omo.Omo(b'OMO ' + OMO_HEAD + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
    for b, m in zip(bones, anim_locals(anim, bones, frames)):
        t = m[:, :3, 3]
        sc = np.linalg.norm(m[:, :3, :3], axis=1)
        q = _mat_quat(m[:, :3, :3] / sc[:, None, :])
        # keep consecutive quaternions in one hemisphere (_node then makes w >= 0 for the xyz encoding)
        _node(o, bone_hash(b['name']), t, q, sc)
    return o.encode(), frames


def vis_mta(anim, mesh_names):
    frames = max(1, int(round(anim['frames'])))
    vis = []
    for name in mesh_names:
        tr = anim['tracks'].get(name)
        if tr is None:
            continue
        bits = tr['frames'] or [tr['default']]
        keys = [(0, bits[0])] + [(f, v) for f, v in enumerate(bits) if f and v != bits[f - 1]]
        vis.append((name, keys))
    return mta.write(frames, [], vis=vis)


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
def convert(src, kind, out, tex_id, log=print):
    base = os.path.join(src, 'enemy', kind)
    mdir = os.path.join(base, 'model', 'body', 'c00')
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    mbn = sm.read_mbn(open(os.path.join(mdir, 'normal.mbn'), 'rb').read())
    log('model %s' % kind)
    nud_b, nut_b, vbn_b, model = build_model(bch, mbn, tex_id, log)
    od = os.path.join(out, 'model', 'enemy', kind, 'body', 'c00')
    os.makedirs(od, exist_ok=True)
    for n, b in (('model.nud', nud_b), ('model.nut', nut_b), ('model.vbn', vbn_b)):
        open(os.path.join(od, n), 'wb').write(b)
    bones = model['bones']
    md = os.path.join(out, 'motion', 'enemy', kind, 'body')
    os.makedirs(md, exist_ok=True)
    mot = os.path.join(base, 'motion', 'body', 'main.bch')
    entries = []
    if os.path.exists(mot):
        for a in sm.Bch(open(mot, 'rb').read()).skeletal_animations():
            b, frames = omo_from(a, bones)
            entries.append((a['name'] + '.omo', b))
            log('  motion %-34s %3d frames' % (a['name'], frames))
        omo.pac_write(os.path.join(md, 'main.pac'), entries)
    vdir = os.path.join(mdir, 'material_anime', 'body', 'main')
    mesh_names = [o['name'] for o in model['objects'] if not o['silhouette']]
    vis = []
    if os.path.isdir(vdir):
        for fn in sorted(os.listdir(vdir)):
            for a in sm.Bch(open(os.path.join(vdir, fn), 'rb').read()).visibility_animations():
                vis.append((a['name'] + '.mta', vis_mta(a, mesh_names)))
        if vis:
            omo.pac_write(os.path.join(md, 'material_anime.pac'), vis)
            log('  visibility: %d MTAs (%s)' % (len(vis), ', '.join(n for n, _ in vis)))
    s = os.path.join(base, 'animcmd')
    if os.path.isdir(s):
        dst = os.path.join(out, 'animcmd', 'enemy', kind)
        os.makedirs(dst, exist_ok=True)
        for fn in sorted(os.listdir(s)):
            b = acmd_be(open(os.path.join(s, fn), 'rb').read())
            open(os.path.join(dst, fn), 'wb').write(b)
            f = acmd.ACMDFile.load(os.path.join(dst, fn))       # every command one the Wii U knows
            log('  animcmd %s: %d scripts, %d commands' % (fn, len(f.scripts), sum(map(len, f.scripts.values()))))
    snd = os.path.join(base, 'snd_se_enemy_%s.nus3bank' % kind)
    if os.path.exists(snd):
        os.makedirs(os.path.join(out, 'sound', 'se'), exist_ok=True)
        shutil.copy(snd, os.path.join(out, 'sound', 'se'))
    prm = os.path.join(src, 'param', 'enemy', 'fs', 'enemy_param_vl_%s.bin' % kind)
    if os.path.exists(prm):
        os.makedirs(os.path.join(out, 'param', 'enemy', 'fs'), exist_ok=True)
        shutil.copy(prm, os.path.join(out, 'param', 'enemy', 'fs'))
    return model


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('kind')
    ap.add_argument('out')
    ap.add_argument('--tex-id', type=lambda s: int(s, 0), default=0x40F00000)
    a = ap.parse_args()
    convert(a.src, a.kind, a.out, a.tex_id)


if __name__ == '__main__':
    main()
