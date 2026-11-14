#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy hats: Ultimate's kirby/model/copy_brave_cap / copy_edge_cap (c00-c07) as Smash 4 hat
models (fighter/kirby/model/bravecap / edgecap/cNN: model.nud, metal.nud, model.nut, model.vbn and the rest of the
template hat's files). fighters/kirby/specials.md "Hero / Sephiroth copies".

  python3 tools/kirby_copy_hats.py ULT_KIRBY_MODEL_DIR S4_KIRBY_MODEL_DIR OUT_MODEL_DIR [--check]

ULT_KIRBY_MODEL_DIR: Ultimate's kirby/model (copy_brave_cap/, copy_edge_cap/, copy_reflet_cap/, body/c00). S4_KIRBY_MODEL_DIR:
Smash 4's fighter/kirby/model (refletcap/c00: the template hat whose vbn / jtb / sb / xmb / nhb / mta are copied;
mariocap/c00: the material template, its metal.nud). OUT_MODEL_DIR gets bravecap/c00-c07 and edgecap/c00-c07.

Placement (Visual fix v1; fighters/kirby/specials.md):
- Smash 4's hats are one bone (TopN) whose bind turn is Kirby's head-frame turn (euler (pi/2, 0, pi/2): local X up,
  shared by HipN ... BustN, NeckN, HeadN, BodyBN), at the origin, so the vertices are offsets in Kirby's world frame
  (Y up, X across, Z forward) from the bone the game puts the hat on. That bone sits at y 5.17 in the bind pose
  (BodyBN, the bone the whole body sphere, eyes and face are bound to; NeckN is at the same place), not at HeadN
  (6.37) as stage 1 assumed: vanilla hats hug Kirby's body sphere (centre y 5.28, radius 4.70) with that origin and
  float with HeadN's: Peach's crown sits on the head (nearest vertex 0.10 inside the sphere) at 5.17 and 0.92 above it
  at 6.37; Fox's ears, Koopa's / Luigi's / Mario's caps, Roy's, Pikachu's, Ganondorf's the same way (`--check` prints
  the table). In game, the Sephiroth hair placed for 6.37 sat 1.2 too low (the user's clip: the head's top bare
  behind the fringe, the side locks down to the floor), and it kept to the body / face while the copy motions turned
  HeadN by up to 179 degrees (Ultimate's Head yaws freely: nothing is skinned to it), so it isn't HeadN.
- Ultimate's two copy hats are in that same frame: copy_edge_cap is skinned to Body / Puff / S_HairB1 in Kirby's
  model space (its skeleton is Kirby's, same bind; Body at (0, 5.17, 0), Y-up axes), so its vertices - (0, 5.17, 0);
  copy_brave_cap has no skeleton and its vertices are already offsets from that point (offset 0): its circlet hugs
  the body sphere there (nearest vertex +0.05, median +0.23, none inside; best fit 5.1-5.2 scanning the anchor
  height) with the gem on the forehead and the sword and shield on the back. Stage 1 put it on Ultimate's Headdress
  joint (9.752: + 3.382 for a 6.37 anchor), which in game left the circlet floating ~1.5-2.9 above the head.
  (Ultimate's other caps, e.g. copy_reflet_cap, are in a Root bone's frame with X up, the same frame as Smash 4's
  hats less the axis turn: `--check` compares the two Robin hoods, which agree to ~0.7.)
- Swing (Visual fix v2): the edge hat's back hair swings with Smash 4's own physics (SWING below); the Puff
  weights stay on TopN. Ultimate's keyframed hair of the neutral-special motions (kirby/motion/copy_edge_cap
  d00special*.nuanmb, where swingblend.prc turns the swing off) isn't played: Kirby's copy hats get no motion pack
  (the copy resource tables, 0x1041A6D0 body motions, 0x1041A7B8 hats, 0x1041A8A0 and two more held items, have no
  hat-motion table; Yoshi's motion/yoshicap is presumably the Yoshi copy's own code's). Hero's hat has no skeleton
  in Ultimate: rigid.
Texture ids: the new fighters' scheme (tools/fighter_texture_ids.py) puts each fighter at 0x40KK0000, KK = 0x80 +
kind; Kirby's copy hats take a block far past those fighters' own articles: Hero's (kind 0x45) 0x40C5F000 and
Sephiroth's (kind 0x42) 0x40C2F000, + 0x80 x NN (Kirby's costume NN: the loader picks cNN by Kirby's costume).
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

HEAD_Y = 6.37          # HeadN / Head (stage 1's assumed anchor; Ultimate's reflet cap frame in --check)
ANCHOR_Y = 5.17        # the hat bone's place: BodyBN / Body (and NeckN)
HATS = {
    # out name: (Ultimate folder, offset to Smash 4's TopN frame, texture id base)
    'bravecap': ('copy_brave_cap', (0.0, 0.0, 0.0), 0x40C5F000),
    'edgecap': ('copy_edge_cap', (0.0, -ANCHOR_Y, 0.0), 0x40C2F000),
}
SPHERE = (np.array([0.0, 5.28, 0.07]), 4.70)    # Kirby's body sphere (Kirby_Bodybig's vertex box)
VANILLA_HATS = ('peachcap', 'foxear', 'koopacap', 'luigicap', 'mariocap', 'roycap', 'pikachucap', 'ganoncap',
                'marthcap', 'refletcap')
TEMPLATE_HAT = 'refletcap'      # Kirby's Robin copy: the copy kind both new copies are granted as
MATERIAL_HAT = 'mariocap'       # an opaque 0x9A011063 (colour, normal, ramp) material and its metal.nud

# Swing (Visual fix v2): Smash 4's own hair physics. A hat's model.vbn may have swing bones (type 3, named
# SWG_..__swing, children of the root) with vertices skinned to them, and its model.sb (' BWS' 5.1, little-endian, a
# u32 count, 140-byte entries: Smash Forge's SB.SBEntry) gives each one's physics by bone hash. Vanilla Kirby hats do:
# marthcap (3 hair bones), linkcap (3, the hat's tail), ikecap (2 x 3, the bandana), szerosuithair (5, the ponytail),
# 22 hats / parts in all. Ultimate's copy_edge_cap swings one bone, S_HairB1 (the back hair, 1341 vertices, the
# strand below y ~6.9), to S_HairB2_null 5 below (swing.prc 'hairb': z -20..50, y -20..20 degrees, no collision).
SWING = dict(
    ult_bone='S_HairB1', ult_tip='S_HairB2_null',
    name='SWG_HairB1N__swing',
    # entry template: Zero Suit Samus's ponytail root (szerosuithair c00, SWG_Pony01N__swing): a strand hanging from
    # the back of Kirby's head, its bone axes as S_HairB1's (X along the strand, Z across); Marth's hair bones carry
    # the same physics words (800, 5, 3, 100, 0, 1). Its angle limits become Ultimate's, its length S_HairB1's.
    template=('szerosuithair', 'SWG_Pony01N__swing'),
    ry=(-20.0, 20.0), rz=(-20.0, 50.0),
)
SB_NONE = 3449071621            # 0xCD94A505: an unused collision-bone slot in every vanilla entry


def swing_share(part, bone):
    """per-vertex weight of the Ultimate bone (0 when the part isn't skinned to it)"""
    w = np.zeros(part['n'])
    for b, ws in part['infl']:
        if b == bone:
            for v, x in ws:
                w[v] += x
    return np.clip(w, 0.0, 1.0)


def hat_polygons(src, off, tex, tmpl, swing_bone=None):
    """the hat's polygons; with swing_bone, vertices skinned to it go to the hat's bone 1 (the swing bone) by
    their weight, the rest (Body, Puff) to bone 0 (TopN)"""
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
            p.bones = np.zeros((n, 4), np.int64)            # TopN
            p.weights = np.tile([255, 0, 0, 0], (n, 1))
            if swing_bone:
                ws = np.round(swing_share(part, swing_bone) * 255).astype(np.int64)
                p.bones[:, 1] = 1
                p.weights[:, 0], p.weights[:, 1] = 255 - ws, ws
                # main weight first, as the game's fighters (and an index with no weight repeats the first)
                swap = ws > 127
                p.bones[swap] = [1, 0, 0, 0]
                p.weights[swap] = np.c_[ws[swap], 255 - ws[swap], np.zeros((swap.sum(), 2), np.int64)]
                p.bones = np.where(p.weights == 0, p.bones[:, :1], p.bones)
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
            swing = hat == 'edgecap'
            if swing:
                vbn, sb = swing_skeleton(os.path.join(src, 'model.nusktb'), tmpl_dir + '/model.vbn', s4, off)
                open(dst + '/model.vbn', 'wb').write(vbn)
                open(dst + '/model.sb', 'wb').write(sb)
            meshes = hat_polygons(src, off, tex, tmpl, SWING['ult_bone'] if swing else None)
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


def euler_of(r):
    """model.vbn's rotation (rx, ry, rz) for R = Rz Ry Rx"""
    ry = -np.arcsin(np.clip(r[2, 0], -1, 1))
    return np.arctan2(r[2, 1], r[2, 2]), ry, np.arctan2(r[1, 0], r[0, 0])


def matrix_of(t, rot, scl=(1, 1, 1)):
    rx, ry, rz = rot
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    m = np.eye(4)
    m[:3, :3] = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
                 @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])) * np.asarray(scl)
    m[:3, 3] = t
    return m


def vbn_read_le(path):
    """[(name, type, parent or -1, hash, (t, r, s))] of a little-endian ' NBV' hat skeleton"""
    d = open(path, 'rb').read()
    assert d[:4] == b' NBV', path
    n = struct.unpack('<I', d[8:12])[0]
    base = 28 + 76 * n
    out = []
    for i in range(n):
        o = 28 + 76 * i
        t, par, h = struct.unpack('<IiI', d[o + 64:o + 76])
        v = struct.unpack('<9f', d[base + 36 * i:base + 36 * i + 36])
        name = d[o:o + 64].split(b'\0')[0].decode()
        out.append((name, t, par if par != 0x0FFFFFFF else -1, h, (v[:3], v[3:6], v[6:])))
    return out


def vbn_write_le(bones):
    """little-endian ' NBV' 2.1 as Kirby's hats: the header counts the bones of each type (0-3)"""
    counts = [sum(1 for b in bones if b[1] == k) for k in range(4)]
    out = struct.pack('<4sHHI4I', b' NBV', 2, 1, len(bones), *counts)
    for name, typ, par, h, _trs in bones:
        out += name.encode().ljust(64, b'\0') + struct.pack('<IiI', typ, 0x0FFFFFFF if par < 0 else par, h)
    for _n, _t, _p, _h, (t, r, sc) in bones:
        out += struct.pack('<9f', *t, *r, *sc)
    return out


def sb_read(path):
    d = open(path, 'rb').read()
    assert d[:4] == b' BWS', path
    n = struct.unpack('<I', d[8:12])[0]
    return d[:8], [bytearray(d[12 + 140 * k:12 + 140 * (k + 1)]) for k in range(n)]


def sb_write(head, entries):
    return head + struct.pack('<I', len(entries)) + b''.join(bytes(e) for e in entries)


def swing_skeleton(ult_skel, tmpl_vbn, s4, off):
    """the edge hat's model.vbn (the template's TopN + the swing bone at S_HairB1's bind, in the hat's frame:
    Kirby's model space + off, axes kept) and model.sb (one entry: SWING's template with Ultimate's limits)"""
    import ssbh_data_py as ssbh
    sk = ssbh.skel_data.read_skel(ult_skel)
    by = {b.name: b for b in sk.bones}
    world = np.array(sk.calculate_world_transform(by[SWING['ult_bone']])).T
    tip = np.array(sk.calculate_world_transform(by[SWING['ult_tip']])).T
    length = float(np.linalg.norm(tip[:3, 3] - world[:3, 3]))
    top = vbn_read_le(tmpl_vbn)
    assert len(top) == 1, tmpl_vbn
    tname, ttype, _tp, thash, ttrs = top[0]
    top_bind = matrix_of(*ttrs)
    swing_model = world.copy()
    swing_model[:3, 3] += np.asarray(off)
    local = np.linalg.inv(top_bind) @ swing_model
    r = local[:3, :3]
    assert np.allclose(r @ r.T, np.eye(3), atol=1e-5)
    h = zlib.crc32(SWING['name'].encode()) & 0xFFFFFFFF
    bones = [(tname, ttype, -1, thash, ttrs),
             (SWING['name'], 3, 0, h, (tuple(local[:3, 3]), euler_of(r), (1.0, 1.0, 1.0)))]
    head, entries = sb_read(os.path.join(s4, SWING['template'][0], 'c00', 'model.sb'))
    want = {b[3]: b[0] for b in vbn_read_le(os.path.join(s4, SWING['template'][0], 'c00', 'model.vbn'))}
    e = next(x for x in entries if want.get(struct.unpack('<I', x[:4])[0]) == SWING['template'][1])
    e[0:4] = struct.pack('<I', h)
    e[36:44] = struct.pack('<2f', *SWING['ry'])        # words 9-10: ry1, ry2
    e[44:52] = struct.pack('<2f', *SWING['rz'])        # words 11-12: rz1, rz2
    e[120:124] = struct.pack('<f', length)            # word 30 (Smash Forge unks2[5]): the bone's length
    assert struct.unpack('<8I', e[52:84]) == (SB_NONE,) * 8, 'no collision bones'
    return vbn_write_le(bones), sb_write(head, [e])


def rigged_positions(path):
    """a rigged .nud's vertex positions (the "vertex add" section: float xyz first)"""
    import zlib
    d = open(path, 'rb').read()
    if d[:2] == b'\x78\x9c':
        d = zlib.decompress(d)
    nrm = {0: 4, 1: 16, 2: 40, 3: 52, 6: 8, 7: 24}
    out = []
    for m in nud.read(path):
        for p in m.polygons:
            if p.vert_size >> 4 == 0:
                out.append(p.pos)
                continue
            stride = 12 + nrm[p.vert_size & 0xF] + {1: 32, 2: 16, 4: 8}[p.vert_size >> 4]
            a = np.frombuffer(d, np.uint8, p.nv * stride, p.vaoff).reshape(p.nv, stride)
            out.append(np.frombuffer(a[:, :12].tobytes(), '>f4').reshape(-1, 3).astype(np.float64))
    return np.concatenate(out)


def check_swing(s4, out):
    """the built edge hats' swing set-up, laid out as the vanilla swing hats' (marthcap, szerosuithair ...)"""
    for c in range(8):
        d = os.path.join(out, 'edgecap', 'c%02d' % c)
        bones = vbn_read_le(d + '/model.vbn')
        head, entries = sb_read(d + '/model.sb')
        hashes = [struct.unpack('<I', e[:4])[0] for e in entries]
        assert [b[1] for b in bones] == [0, 3] and bones[1][2] == 0 and hashes == [bones[1][3]], d
        assert head == sb_read(os.path.join(s4, SWING['template'][0], 'c00', 'model.sb'))[0], 'sb header'
        nb = open(d + '/model.nud', 'rb').read()
        assert struct.unpack('>hh', nb[12:16]) == (0, 1), 'nud bone range'
    e = entries[0]
    f = struct.unpack('<35f', bytes(e))
    print('edgecap c00-c07: TopN + %s (type 3, %s), model.sb 1 entry: limits ry %s rz %s, length %.2f' % (
        bones[1][0], ' '.join('%.3f' % x for x in bones[1][4][0]), f[9:11], f[11:13], f[30]))


def check(ult, s4, out=None):
    """where the hat bone is (vanilla hats against Kirby's body sphere), and Ultimate's reflet cap against Smash 4's"""
    import ssbh_data_py as s
    if out:
        check_swing(s4, out)
    c, r = SPHERE
    print('vanilla hats on an anchor at y = 5.17 (BodyBN) / 6.37 (HeadN): share of vertices inside the body sphere, '
          'nearest vertex to it (- inside)')
    hats = [(h, os.path.join(s4, h, 'c00', 'model.nud')) for h in VANILLA_HATS]
    if out:
        hats += [(h + ' (built)', os.path.join(out, h, 'c00', 'model.nud')) for h in HATS]
    for h, path in hats:
        if not os.path.exists(path):
            continue
        v = rigged_positions(path)
        row = []
        for y in (ANCHOR_Y, HEAD_Y):
            d = np.linalg.norm(v + [0, y, 0] - c, axis=1) - r
            row.append('%.2f: inside %4.1f%%, nearest %+.2f' % (y, 100 * (d < 0).mean(), d.min()))
        print('  %-18s %s' % (h, ' | '.join(row)))
    mesh = s.mesh_data.read_mesh(os.path.join(ult, 'copy_reflet_cap', 'c00', 'model.numshb'))
    u = np.concatenate([np.array(o.positions[0].data, np.float64)[:, :3] for o in mesh.objects])
    w = np.c_[u[:, 2], u[:, 0], u[:, 1]]          # its Root frame (X up, Y forward, Z across) -> Kirby's world axes
    v = rigged_positions(os.path.join(s4, TEMPLATE_HAT, 'c00', 'model.nud'))
    for label, x in (('Ultimate reflet cap (Root frame):', w), ('Smash 4 refletcap (TopN):', v)):
        print('%-35s %s .. %s' % (label, np.round(x.min(0), 2).tolist(), np.round(x.max(0), 2).tolist()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('s4')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.out:
        build(a.ult, a.s4, a.out)
    if a.check:
        check(a.ult, a.s4, a.out)


if __name__ == '__main__':
    main()
