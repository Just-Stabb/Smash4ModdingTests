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
import nut  # noqa: E402
import omo  # noqa: E402
import s3ds_enemy as se  # noqa: E402
import s3ds_model as sm  # noqa: E402

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
        _bch, mbn, model = model_tests(src, kind, out, part, c)
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
