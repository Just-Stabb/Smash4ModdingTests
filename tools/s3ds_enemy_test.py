#!/usr/bin/env python3
"""Checks tools/s3ds_enemy.py on a Smash Run enemy (the Goomba first) against its 3DS files:

- the decoder: a hand-made ETC1 block (differential and individual modes, flip) decodes to the colours the
  ETC1 spec gives; a PICA200 8x8 tile's Z-order.
- every model part (model/PART/cNN): one NUD mesh per non-silhouette .bch object, named as it; the VBN's bones,
  parents and bind pose are the .bch skeleton's; every colour texture decodes back from the NUT within BC1 / BC3
  error of the 3DS texture.
- the motions (every motion folder): every .bch skeletal animation is an OMO in main.pac; every mesh skinned
  (its blended weights) with the written OMO (omo.world, as the game reads it) lands within 0.1 units (scaled
  by model size / the Goomba's 12.4) of the meshes skinned with the 3DS keys, on ~12 frames of every motion
  (Goomba: 0.064 at worst, the feet turned ~180 degrees: OMO rotation type 5 rebuilds w from 16-bit x y z,
  coarse where w is near 0; most frames are under 0.01).
- the visibility: every material_anime .bch is an MTA in material_anime.pac whose mesh states are the 3DS bits.
- the UVs, end to end: every mesh's written UVs through its material's transform as the Wii U vertex programs
  do it (s3ds_preview.nud_uv: NU_colorSamplerUV, or NU_effRotUV / ScaleUV / TransUV for a material whose UV
  rotates, which gets the skinned effect shader) sample where the 3DS's coordinator transform (SPICA's) puts the
  3DS UVs; the model.mta's UV tracks the same a frame against the 3DS's animated scale / rotation / translation.
- the ACMD: big-endian, every command known, the same scripts and parameters as the 3DS file.

  python3 tools/s3ds_enemy_test.py SRC_ROOT [KIND | all]   (SRC_ROOT: a tools/s3ds_unpack.py extract)
"""
import os
import struct
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
import s3ds_enemy as se  # noqa: E402
import s3ds_model as sm  # noqa: E402
from s3ds_preview import nud_uv  # noqa: E402

FAILS = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def decoder_tests():
    # ETC1, individual mode, no flip: left half base (8, 4, 2) * 17, right half (1, 2, 3) * 17, tables 0 / 7,
    # every pixel index 0 (+ the table's small modifier)
    hi = (8 << 28) | (1 << 24) | (4 << 20) | (2 << 16) | (2 << 12) | (3 << 8) | (0 << 5) | (7 << 2)
    blk = sm._etc1_block(hi << 32)
    ok = tuple(blk[0, 0]) == (8 * 17 + 2, 4 * 17 + 2, 2 * 17 + 2)
    ok &= tuple(blk[3, 3]) == (17 + 47, 34 + 47, 51 + 47)
    check(ok, 'ETC1 individual mode: halves, tables, modifier')
    # differential mode, flip (top / bottom halves), base 5-bit (16, 8, 4), delta (-1, 0, +3), pixel (1, 0)
    # (index 4) with msb set: -large modifier of table 1 (17)
    hi = (16 << 27) | (7 << 24) | (8 << 19) | (0 << 16) | (4 << 11) | (3 << 8) | (1 << 5) | (1 << 2) | 2 | 1
    v = (hi << 32) | (1 << (16 + 4)) | (1 << 4)
    blk = sm._etc1_block(v)
    c1 = [(c << 3) | (c >> 2) for c in (16, 8, 4)]
    c2 = [(c << 3) | (c >> 2) for c in (15, 8, 7)]
    check(tuple(blk[0, 1]) == tuple(max(0, x - 17) for x in c1) and tuple(blk[2, 0]) == tuple(min(255, x + 5) for x in c2),
          'ETC1 differential mode, flip, modifier signs')
    # rgba8 tile: pixel p at TILE[p], memory order (first row first)
    data = bytes(b for p in range(64) for b in (255, p, p, p))
    img = sm.decode_texture(data, 8, 8, 0)
    ok = all(tuple(img[sm.TILE[p] // 8, sm.TILE[p] % 8, :3]) == (p, p, p) for p in range(64))
    check(ok, 'PICA200 tile order (Z-order), memory order')


def model_tests(src, kind, out, part='body', c='c00', quiet=False):
    mdir = os.path.join(src, 'enemy', kind, 'model', part, c)
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    mbn = sm.read_mbn(open(os.path.join(mdir, 'normal.mbn'), 'rb').read())
    model = bch.models()[0]
    bones = model['bones']
    tag = '%s/%s/%s' % (kind, part, c)
    od = os.path.join(out, 'model', 'enemy', kind, part, c)
    nd = open(os.path.join(od, 'model.nud'), 'rb').read()
    nmesh = struct.unpack('>h', nd[0xA:0xC])[0]
    want = [o['name'] for o in model['objects'] if not o['silhouette']]
    pstart, psize, vsize, vasize = struct.unpack('>iiii', nd[0x10:0x20])
    sbase = 0x30 + pstart + psize + vsize + vasize
    names = []
    for i in range(nmesh):
        no = struct.unpack('>i', nd[0x30 + 0x30 * i + 32:0x30 + 0x30 * i + 36])[0]
        names.append(nd[sbase + no:nd.index(b'\0', sbase + no)].decode())
    check(nd[:4] == b'NDP3' and names == want, '%s: NUD meshes = the .bch objects (%d)' % (tag, len(names)))
    vb = open(os.path.join(od, 'model.vbn'), 'rb').read()
    n = struct.unpack('<I', vb[8:12])[0]
    ok = n == len(bones)
    for i, b in enumerate(bones):
        name = vb[28 + 76 * i:28 + 76 * i + 64].split(b'\0')[0].decode()
        _t, par, h = struct.unpack('<IiI', vb[28 + 76 * i + 64:28 + 76 * i + 76])
        t = struct.unpack('<9f', vb[28 + 76 * n + 36 * i:28 + 76 * n + 36 * i + 36])
        ok &= name == b['name'] and (par if par != 0x0FFFFFFF else -1) == b['parent'] and h == se.bone_hash(name)
        ok &= np.allclose(t, list(b['pos']) + list(b['rot']) + list(b['scale']), atol=1e-6)
    check(ok, '%s: VBN = the .bch skeleton (%d bones)' % (tag, n))
    check(all(open(os.path.join(od, f), 'rb').read() == open(os.path.join(se.DEFAULTS, f), 'rb').read()
              for f in se.DEFAULT_FILES), '%s: model.sb / .nhb / .xmb (the defaults)' % tag)
    sj = os.path.join(mdir, 'model.jtb')
    if os.path.exists(sj):
        a, b = open(sj, 'rb').read(), open(os.path.join(od, 'model.jtb'), 'rb').read()
        va = struct.unpack('<%dH' % (len(a) // 2), a)
        vb_ = struct.unpack('>%dH' % (len(b) // 2), b) if len(b) == len(a) else None
        check(vb_ == va and va[0] * 2 + 2 == len(a) and all(i < n or i == 0xFFFF for i in va[1:]),
              '%s: model.jtb big-endian, same %d joints, every one a bone' % (tag, va[0]))
    d, texs = nut.load(os.path.join(od, 'model.nut'))
    srcs = {k: v for k, v in bch.textures().items() if not k.endswith('#format')}
    ids = {t.tex_id: t for t in texs}
    worst = 0.0
    used = {model['materials'][o['material']]['textures'][0] for o in model['objects']}
    for k, img in srcs.items():
        if k not in used:
            continue
        # the colour textures were written first, in the .bch's order, after the flat normal map
        best = min((np.abs(nut.decode(d, t)[..., :3].astype(int) - img[..., :3].astype(int)).mean()
                    for t in ids.values() if (t.w, t.h) == (img.shape[1], img.shape[0])), default=99)
        worst = max(worst, best)
    check(worst < 8, '%s: every colour texture in the NUT (worst mean error %.2f / 255)' % (tag, worst))
    return bch, mbn, model


def _coord_t(co, sc=None, rot=None, tr=None):
    sc = [x or 1.0 for x in (sc or co['scale'])]
    return sm.tex_transform(sc, co['rotate'] if rot is None else rot, tr or co['translate'], co['transform'])


def uv_tests(src, kind, out, bch, mbn, model, part='body', c='c00'):
    tag = '%s/%s/%s' % (kind, part, c)
    od = os.path.join(out, 'model', 'enemy', kind, part, c)
    written = nud.read(os.path.join(od, 'model.nud'))
    pairs = [(o, mi) for o, mi in zip(model['objects'], sm.match_objects(model['objects'], mbn)) if not o['silhouette']]
    worst, rot = 0.0, 0
    for (obj, mi), mesh in zip(pairs, written):
        mat = model['materials'][obj['material']]
        a = mbn[mi]['attrs']
        if 3 not in a or 'coords' not in mat:
            continue
        m3 = _coord_t(mat['coords'][0])
        for p, (_bl, idx) in zip(mesh.polygons, mbn[mi]['parts']):
            used = np.unique(idx)
            props = dict(p.materials[0].props)
            rot += p.materials[0].flags == se.ROT_FLAGS
            t3 = (m3 @ np.c_[a[3][used], np.ones(len(used))].T).T
            got = nud_uv(np.asarray(p.uvs[0], float), props)
            worst = max(worst, float(np.abs(got - np.c_[t3[:, 0], 1 - t3[:, 1]]).max(initial=0)))
    check(worst < 4e-3 * 8, '%s: UVs through the shader transform = the 3DS transform (worst %.4f; %d rotating '
          'polygons)' % (tag, worst, rot))
    # the model's own material animation: every frame's UV transform at three points
    path = os.path.join(od, 'model.mta')
    anims = bch.material_animations()
    if not anims or not os.path.exists(path):
        return
    r = mta.read(open(path, 'rb').read())
    by_mat = {m['name']: m for m in model['materials']}
    statics = {}
    for m in written:
        for p in m.polygons:
            props = dict(p.materials[0].props)
            statics.setdefault(struct.unpack('>I', struct.pack('>f', props['NU_materialHash'][0]))[0], props)
    tracks = {}
    for md in anims[0]['materials']:
        tracks.setdefault(md['name'], {})[md['property']] = md['components']
    pts = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    worst, n = 0.0, 0
    for e in r['mats']:
        mat, tr = by_mat.get(e['name']), tracks.get(e['name'], {})
        if mat is None or e['hash'] not in statics:
            continue
        co = mat['coords'][0]
        for f in range(r['frames']):
            def comp(prop, j, default):
                t = tr.get(prop)
                v = sm.sample(t[j], f) if t and j < len(t) and t[j] is not None else None
                return default if v is None else v
            props = dict(statics[e['hash']])
            for q in e['props']:
                props[q['name']] = q['values'][min(f, len(q['values']) - 1)]
            m3 = _coord_t(co, [comp(0x13, j, co['scale'][j]) for j in range(2)], comp(0x14, 0, co['rotate']),
                          [comp(0x15, j, co['translate'][j]) for j in range(2)])
            t3 = (m3 @ np.c_[pts, np.ones(3)].T).T
            # the NUD's UV of a 3DS point is (u, 1 - v)
            got = nud_uv(np.c_[pts[:, 0], 1 - pts[:, 1]], props)
            worst = max(worst, float(np.abs(got - np.c_[t3[:, 0], 1 - t3[:, 1]]).max()))
            n += 1
    check(worst < 1e-3, '%s: model.mta UV tracks = the 3DS animated transform (%d material frames, worst %.5f)'
          % (tag, n, worst))


def motion_tests(src, kind, out, models, mbns, limit=0.1):
    """every motion folder: an OMO per 3DS motion; every mesh skinned (its blended weights) with the written OMO
    = with the 3DS keys, every frame"""
    for mpart, files in se._motion_files(os.path.join(src, 'enemy', kind)).items():
        mp = mpart if mpart in models else 'body' if 'body' in models else next(iter(models))
        model, mbn = models[mp], mbns[mp]
        bones = model['bones']
        vb = omo.vbn_read(os.path.join(out, 'model', 'enemy', kind, mp, 'c00', 'model.vbn'))
        bind = []
        for b in bones:
            m = se.local_matrix(b['scale'], b['rot'], b['pos'])
            bind.append(m if b['parent'] < 0 else bind[b['parent']] @ m)
        inv = [np.linalg.inv(m) for m in bind]
        anims = [a for f in files for a in sm.Bch(open(f, 'rb').read()).skeletal_animations()]
        pac = dict(omo.pac_read(os.path.join(out, 'motion', 'enemy', kind, mpart, 'main.pac')))
        check(sorted(pac) == sorted(a['name'] + '.omo' for a in anims),
              '%s/%s: an OMO per 3DS motion (%d)' % (kind, mpart, len(anims)))
        verts = []
        for me in mbn:
            P = np.c_[me['attrs'][0], np.ones(me['count'])]
            for bl, _idx in me['parts']:
                bi = np.asarray(bl)[np.minimum(me['attrs'][5].astype(int), len(bl) - 1)]
                verts.append((P, bi, me['attrs'][6]))
        worst, where = 0.0, ''
        for a in anims:
            o = omo.Omo(pac[a['name'] + '.omo'])
            loc = se.anim_locals(a, bones, o.frames)
            for fr in range(0, o.frames, max(1, o.frames // 12)):
                w = omo.world(o, vb, fr)
                ref = []
                for i, b in enumerate(bones):
                    ref.append(loc[i][fr] if b['parent'] < 0 else ref[b['parent']] @ loc[i][fr])
                sk_got = [np.array(w[b['name']]) @ inv[i] for i, b in enumerate(bones)]
                sk_ref = [ref[i] @ inv[i] for i in range(len(bones))]
                for P, bi, bw in verts:
                    got = np.zeros((len(P), 3))
                    exp = np.zeros((len(P), 3))
                    for j in range(bi.shape[1]):
                        for b in np.unique(bi[:, j]):
                            sel = bi[:, j] == b
                            got[sel] += bw[sel, j:j + 1] * (sk_got[b] @ P[sel].T).T[:, :3]
                            exp[sel] += bw[sel, j:j + 1] * (sk_ref[b] @ P[sel].T).T[:, :3]
                    e = float(np.abs(got - exp).max()) if len(P) else 0.0
                    if e > worst:
                        worst, where = e, '%s f%d' % (a['name'], fr)
        size = max(float(np.ptp(np.concatenate([m['attrs'][0] for m in mbn]), axis=0).max()), 1.0)
        check(worst < limit * max(1.0, size / 12.4),
              '%s/%s: skinned with the written OMOs = with the 3DS keys (worst %.4f, %s; model %.0f units)'
              % (kind, mpart, worst, where, size))


def vis_tests(src, kind, out):
    base = os.path.join(src, 'enemy', kind, 'model')
    for part in os.listdir(base):
        ma = os.path.join(base, part, 'c00', 'material_anime')
        if not os.path.isdir(ma):
            continue
        for mpart in os.listdir(ma):
            vdir = os.path.join(ma, mpart, 'main')
            pac = dict(omo.pac_read(os.path.join(out, 'motion', 'enemy', kind, mpart, 'material_anime.pac')))
            ok = True
            for fn in os.listdir(vdir):
                for a in sm.Bch(open(os.path.join(vdir, fn), 'rb').read()).visibility_animations():
                    m = mta.read(pac[a['name'] + '.mta'])
                    got = {v['name']: v['keys'][0][1] for v in m['vis']}
                    ok &= all(got.get(k) == t['frames'][0] for k, t in a['tracks'].items() if k in got)
                    ok &= len(got) > 0
            check(ok, '%s/%s: material_anime.pac visibility = the 3DS (%d MTAs)' % (kind, mpart, len(pac)))


def acmd_tests(src, kind, out):
    s = os.path.join(src, 'enemy', kind, 'animcmd')
    if not os.path.isdir(s):
        return
    ok = True
    for fn in os.listdir(s):
        d = open(os.path.join(s, fn), 'rb').read()
        f = acmd.ACMDFile.load(os.path.join(out, 'animcmd', 'enemy', kind, fn))
        n = len(d) // 4
        words = struct.unpack('<%dI' % n, d)
        ok &= len(f.scripts) == words[2]
    check(ok, '%s: ACMD big-endian, every command known, the 3DS script counts' % kind)


def enemy_tests(src, kind, out):
    se.convert(src, kind, out, 0x4E000000, log=lambda *a: None)
    models, mbns = {}, {}
    for part, c, _d in se._model_dirs(os.path.join(src, 'enemy', kind)):
        bch, mbn, model = model_tests(src, kind, out, part, c)
        uv_tests(src, kind, out, bch, mbn, model, part, c)
        if c == 'c00':
            models[part], mbns[part] = model, mbn
    if models:
        motion_tests(src, kind, out, models, mbns)
    vis_tests(src, kind, out)
    acmd_tests(src, kind, out)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else 'kuribo'
    decoder_tests()
    kinds = se.fs_kinds(src) if kind == 'all' else [kind]
    for k in kinds:
        with tempfile.TemporaryDirectory() as out:
            enemy_tests(src, k, out)
    print('%d enemies, %d failures' % (len(kinds), len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
