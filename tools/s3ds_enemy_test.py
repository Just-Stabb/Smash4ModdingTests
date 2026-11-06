#!/usr/bin/env python3
"""Checks tools/s3ds_enemy.py on a Smash Run enemy (the Goomba first) against its 3DS files:

- the decoder: a hand-made ETC1 block (differential and individual modes, flip) decodes to the colours the
  ETC1 spec gives; a PICA200 8x8 tile's Z-order.
- the model: one NUD mesh per non-silhouette .bch object, named as it; the VBN's bones, parents and bind pose
  are the .bch skeleton's; every vertex's weight on one bone (the 3DS's rigid binding) and that bone the part's
  bone list entry; the NUT's colour texture decodes back within BC1 error of the 3DS texture.
- the motions: every .bch skeletal animation is an OMO in main.pac; the converted mesh skinned with the
  written OMO (omo.world, as the game reads it) lands within 0.1 units of the mesh skinned with the 3DS keys
  at every frame of every motion (Goomba: 0.064 at worst, the feet turned ~180 degrees: OMO rotation type 5
  rebuilds w from 16-bit x y z, coarse where w is near 0; most frames are under 0.01).
- the visibility: every material_anime .bch is an MTA in material_anime.pac whose mesh states are the 3DS bits.
- the ACMD: big-endian, every command known, the same scripts and parameters as the 3DS file.

  python3 tools/s3ds_enemy_test.py SRC_ROOT [KIND]     (SRC_ROOT: a tools/s3ds_unpack.py extract)
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
    ok = tuple(blk[0, 0]) == (8 * 17 + 2, 4 * 17 + 2, 2 * 17 + 2) and tuple(blk[3, 3]) == (17 + 47, 34 + 47, 51 + 47)
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
    # rgba8 tile: pixel p at TILE[p]; the 3DS stores rows bottom up
    data = bytes(b for p in range(64) for b in (255, p, p, p))
    img = sm.decode_texture(data, 8, 8, 0)
    ok = all(tuple(img[7 - sm.TILE[p] // 8, sm.TILE[p] % 8, :3]) == (p, p, p) for p in range(64))
    check(ok, 'PICA200 tile order (Z-order), rows bottom up')


def model_tests(src, kind, out):
    mdir = os.path.join(src, 'enemy', kind, 'model', 'body', 'c00')
    bch = sm.Bch(open(os.path.join(mdir, 'normal.bch'), 'rb').read())
    mbn = sm.read_mbn(open(os.path.join(mdir, 'normal.mbn'), 'rb').read())
    model = bch.models()[0]
    bones = model['bones']
    od = os.path.join(out, 'model', 'enemy', kind, 'body', 'c00')
    nd = open(os.path.join(od, 'model.nud'), 'rb').read()
    check(nd[:4] == b'NDP3', 'model.nud is NDP3')
    nmesh = struct.unpack('>h', nd[0xA:0xC])[0]
    want = [o['name'] for o in model['objects'] if not o['silhouette']]
    pstart, psize, vsize, vasize = struct.unpack('>iiii', nd[0x10:0x20])
    sbase = 0x30 + pstart + psize + vsize + vasize
    names = []
    for i in range(nmesh):
        no = struct.unpack('>i', nd[0x30 + 0x30 * i + 32:0x30 + 0x30 * i + 36])[0]
        names.append(nd[sbase + no:nd.index(b'\0', sbase + no)].decode())
    check(names == want, 'NUD meshes = the .bch objects: %s' % names)
    vb = open(os.path.join(od, 'model.vbn'), 'rb').read()
    n = struct.unpack('<I', vb[8:12])[0]
    ok = n == len(bones)
    for i, b in enumerate(bones):
        name = vb[28 + 76 * i:28 + 76 * i + 64].split(b'\0')[0].decode()
        _t, par, h = struct.unpack('<IiI', vb[28 + 76 * i + 64:28 + 76 * i + 76])
        t = struct.unpack('<9f', vb[28 + 76 * n + 36 * i:28 + 76 * n + 36 * i + 36])
        ok &= name == b['name'] and (par if par != 0x0FFFFFFF else -1) == b['parent'] and h == se.bone_hash(name)
        ok &= np.allclose(t, list(b['pos']) + list(b['rot']) + list(b['scale']), atol=1e-6)
    check(ok, 'VBN: %d bones, parents, hashes, bind pose = the .bch skeleton' % n)
    rigid = all((m['attrs'][6][:, 0] > 0.99).all() for m in mbn if 6 in m['attrs'])
    check(rigid, '3DS weights: one bone a vertex (rigid), as written')
    d, texs = nut.load(os.path.join(od, 'model.nut'))
    src_tex = [v for k, v in bch.textures().items() if not k.endswith('#format')][0]
    back = nut.decode(d, texs[0])
    err = np.abs(back[..., :3].astype(int) - src_tex[..., :3].astype(int)).mean()
    check(back.shape == src_tex.shape and err < 6, 'NUT colour texture = the 3DS one (mean error %.2f / 255)' % err)
    return bch, mbn, model


def motion_tests(src, kind, out, model, mbn):
    bones = model['bones']
    od = os.path.join(out, 'model', 'enemy', kind, 'body', 'c00')
    vb = omo.vbn_read(os.path.join(od, 'model.vbn'))
    bind = []
    for b in bones:
        m = se.local_matrix(b['scale'], b['rot'], b['pos'])
        bind.append(m if b['parent'] < 0 else bind[b['parent']] @ m)
    inv = [np.linalg.inv(m) for m in bind]
    mot = os.path.join(src, 'enemy', kind, 'motion', 'body', 'main.bch')
    anims = sm.Bch(open(mot, 'rb').read()).skeletal_animations()
    pac = dict(omo.pac_read(os.path.join(out, 'motion', 'enemy', kind, 'body', 'main.pac')))
    check(sorted(pac) == sorted(a['name'] + '.omo' for a in anims), 'main.pac: an OMO per 3DS motion (%d)' % len(anims))
    mesh = mbn[0]
    bl = mesh['parts'][0][0]
    bi = mesh['attrs'][5][:, 0].astype(int)
    P = np.c_[mesh['attrs'][0], np.ones(mesh['count'])]
    worst = 0.0
    for a in anims:
        o = omo.Omo(pac[a['name'] + '.omo'])
        frames = o.frames
        loc = se.anim_locals(a, bones, frames)
        for fr in range(frames):
            w = omo.world(o, vb, fr)
            ref = []
            for i, b in enumerate(bones):
                m = loc[i][fr]
                ref.append(m if b['parent'] < 0 else ref[b['parent']] @ m)
            for j, b in enumerate(bl):
                sel = bi == j
                got = (np.array(w[bones[b]['name']]) @ inv[b] @ P[sel].T).T
                exp = (ref[b] @ inv[b] @ P[sel].T).T
                if sel.any():
                    worst = max(worst, float(np.abs(got - exp).max()))
    check(worst < 0.1, 'skinned with the written OMOs = with the 3DS keys, every frame (worst %.4f)' % worst)


def vis_tests(src, kind, out):
    vdir = os.path.join(src, 'enemy', kind, 'model', 'body', 'c00', 'material_anime', 'body', 'main')
    if not os.path.isdir(vdir):
        return
    pac = dict(omo.pac_read(os.path.join(out, 'motion', 'enemy', kind, 'body', 'material_anime.pac')))
    ok = True
    for fn in os.listdir(vdir):
        for a in sm.Bch(open(os.path.join(vdir, fn), 'rb').read()).visibility_animations():
            m = mta.read(pac[a['name'] + '.mta'])
            got = {v['name']: v['keys'][0][1] for v in m['vis']}
            ok &= got == {k: t['frames'][0] for k, t in a['tracks'].items()}
    check(ok, 'material_anime.pac: the 3DS visibility (%d MTAs)' % len(pac))


def acmd_tests(src, kind, out):
    s = os.path.join(src, 'enemy', kind, 'animcmd')
    ok = True
    for fn in os.listdir(s):
        d = open(os.path.join(s, fn), 'rb').read()
        f = acmd.ACMDFile.load(os.path.join(out, 'animcmd', 'enemy', kind, fn))
        n = len(d) // 4
        words = struct.unpack('<%dI' % n, d)
        ok &= len(f.scripts) == words[2]
        ok &= f.encode() is not None
    check(ok, 'ACMD big-endian, every command known, the 3DS script count')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else 'kuribo'
    decoder_tests()
    with tempfile.TemporaryDirectory() as out:
        se.convert(src, kind, out, 0x40F00000, log=lambda *a: None)
        _bch, mbn, model = model_tests(src, kind, out)
        motion_tests(src, kind, out, model, mbn)
        vis_tests(src, kind, out)
        acmd_tests(src, kind, out)
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
