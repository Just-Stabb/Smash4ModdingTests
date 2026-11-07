#!/usr/bin/env python3
"""Sephiroth's held forward air, the extending sword as articles (fighters/edge/snake_fair.md, test 82): the models of
the two article kinds (tools/extra_kinds.json: `snake` 0x199, `snaketip` 0x19A, both copies of Zelda's light arrow),
written into OUT/fighter/edge/model/<article>/c00 - c07.

  - snake (a straight run, up to 12 at once): bones TopN (root), HaveN, EndN, BaseN (all children of TopN, identity
    binds). One ring-to-ring slice of the blade, its near ring on BaseN and its far ring on EndN, both at z = 0 in the
    bind. Nothing is on HaveN: the light arrow's kind (flag 0x10, held) draws HaveN on its owner, so test 84's near
    rings and point (on HaveN) were drawn at Sephiroth's feet; BaseN follows the article
    (nothing on the root, as vanilla weapon models: the light arrow's NUD bone range is 2 - 2):
    it draws nothing until the run's MSC moves EndN out along +Z to the run's length (ModelModule 7 on joint 0x7D2:
    vanilla weapons name their joints 0x7D0 + bone, Mario's pump), then it spans TopN -> EndN.
  - snaketip (the point, one): the blade's point on BaseN, its real length along +Z.

Both lie along +Z, as weapon models do (Pit's arrow turns with PostureModule(0x2717, -pitch, 90, 0)), drawn twice, the
second copy turned 90 degrees about the blade, so they look the same width turned any way (tools/snake_sword.py). Their
material is the sword's own (his body's model.nud, the sword's mesh slot), its two textures copied into the article's
model.nut under ids of their own (each article its block: tools/fighter_texture_ids.py article_id; until
fighters_texid_fix_v1 0x40EBF000 + k, shared with every port's ids). model.sb / .nhb / .mta / .xmb are the light arrow's.

  python3 tools/edge_snake_articles.py ULT_MODEL_DIR BODY_MODEL_DIR ARROW_MODEL_DIR OUT_FIGHTER_DIR
    ULT_MODEL_DIR: Ultimate's fighter/edge/model/body/c00; BODY_MODEL_DIR: his built Smash 4 body c00 (model.nud /
    model.nut); ARROW_MODEL_DIR: Zelda's fighter/zelda/model/lightingbowarrow/c00
"""
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nud  # noqa: E402
import nut  # noqa: E402
import snake_sword  # noqa: E402
import fighter_texture_ids as TX  # noqa: E402

SWORD_SLOT = 'skirt_VIS_O_OBJ16'           # his body model's mesh slot holding the sword (ultimate_fighter MESH_SLOTS)
# the articles' texture ids: each article's block in Sephiroth's range (reference/port_bases.json "_texture_ids"), + k
# for the sword's textures copied in (were 0x40EBF000 + k, F100 / F101: fighters_texid_fix_v1)
TEX_IDS = {a: TX.article_id('edge', a) for a in ('snake', 'snaketip')}
BONES = ['TopN', 'HaveN', 'EndN', 'BaseN']
BASE = 3                                    # BaseN: the near ring and the point
END_JOINT = 0x7D2                           # EndN for ModelModule (0x7D0 + bone index)
ARTICLES = ('snake', 'snaketip')
WHITE = 0x7F
COLOURS = 8                                 # his costumes c00 - c07


def vbn(names):
    """little-endian model.vbn as his body's: the first bone the root, the rest its children, identity binds"""
    n = len(names)
    out = struct.pack('<4sHHI4I', b' NBV', 2, 1, n, n, 0, 0, 0)
    for i, name in enumerate(names):
        out += name.encode()[:63].ljust(64, b'\0') + struct.pack('<IiI', 0, 0x0FFFFFFF if i == 0 else 0,
                                                                  __import__('zlib').crc32(name.encode()) & 0xFFFFFFFF)
    for _ in names:
        out += struct.pack('<9f', 0, 0, 0, 0, 0, 0, 1, 1, 1)
    return out


def jtb(n):
    """the light arrow's layout: a count, then the bone of each joint"""
    return struct.pack('>H', n) + struct.pack('>%dH' % n, *range(n))


def polygon(q, bones, material):
    """a rigged nud.Polygon from a snake_sword piece (pos / nrm / tan, map1) with a bone per vertex"""
    n = q['n']
    nrm = q['nrm'] / (np.linalg.norm(q['nrm'], axis=1, keepdims=True) + 1e-9)
    tan = q['tan'][:, :3] if q['tan'] is not None else np.cross(nrm, [0, 1, 0])
    sign = q['tan'][:, 3:4] if q['tan'] is not None else np.ones((n, 1))
    tan = tan - nrm * (tan * nrm).sum(1, keepdims=True)
    tan = tan / (np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9)
    p = nud.Polygon()
    p.pos, p.nrm, p.tan, p.bit = q['pos'], nrm, tan, np.cross(nrm, tan) * sign
    idx = np.zeros((n, 4), np.int64)
    idx[:, 0] = bones
    wt = np.zeros((n, 4), np.int64)
    wt[:, 0] = 255
    p.bones, p.weights = idx, wt
    p.uvs = [q['uvs']['map1']]
    p.col = np.full((n, 4), WHITE)
    p.idx = q['idx']
    p.materials = [material]
    return p


def sword_material(body_dir):
    m = next(m for m in nud.read(os.path.join(body_dir, 'model.nud')) if m.name == SWORD_SLOT)
    return m.polygons[0].materials[0].copy()


def textures(body_dir, material, first):
    """the material's own textures (his body's .nut) copied under FIRST + k, the material pointed at them"""
    _d, texs = nut.load(os.path.join(body_dir, 'model.nut'))
    raw = open(os.path.join(body_dir, 'model.nut'), 'rb').read()
    by_id = {t.tex_id: t for t in texs}
    out, k = [], 0
    for t in material.textures:
        src = by_id.get(t['hash'])
        if src is None:                     # a common one (0x10080000: the game's own)
            continue
        img = nut.decode(raw, src)
        new = first + k
        k += 1
        t['hash'] = new
        out.append((new, 0x33 if (img[..., 3] < 250).any() else 0x31, img))
    return nut.write_ntwu(out)


def build(ult_dir, body_dir, arrow_dir, out_fighter):
    import ultimate_fighter as U
    part = U.mesh_parts(ult_dir)[snake_sword.SPEC['meshes'][0]][0]
    run, tip, info = snake_sword.article_pieces(part)
    mat = sword_material(body_dir)
    mats = {a: mat.copy() for a in ARTICLES}
    texs = {a: textures(body_dir, mats[a], TEX_IDS[a]) for a in ARTICLES}
    # the run: the far ring (z 1) on EndN, laid at z 0 in the bind
    far = run['pos'][:, 2] > 0.5
    run_pos = run['pos'].copy()
    run_pos[:, 2] = 0.0
    run_bind = dict(run, pos=run_pos)
    models = {
        'snake': [nud.Mesh('snake', [polygon(run_bind, np.where(far, 2, BASE), mats['snake'])], bone=-1, bind=4)],
        'snaketip': [nud.Mesh('snaketip', [polygon(tip, np.full(tip['n'], BASE, np.int64), mats['snaketip'])], bone=-1, bind=4)],
    }
    # every colour (c00 - c07): the light arrow's kind takes its model in the owner's colour (its flag 0x10, read by
    # the weapon's model set-up 0x02B62F88), and Sephiroth's costumes are c00 - c07
    for name, meshes in models.items():
        for c in range(COLOURS):
            d = os.path.join(out_fighter, 'model', name, 'c%02d' % c)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'model.nud'), 'wb').write(nud.write(meshes))
            open(os.path.join(d, 'model.vbn'), 'wb').write(vbn(BONES))
            open(os.path.join(d, 'model.jtb'), 'wb').write(jtb(len(BONES)))
            open(os.path.join(d, 'model.nut'), 'wb').write(texs[name])
            for f in ('model.sb', 'model.nhb', 'model.mta', 'model.xmb'):
                shutil.copy(os.path.join(arrow_dir, f), os.path.join(d, f))
    return 'snake articles: run %d vertices (far ring %d), point %d vertices %.2f long; %d textures from %s' % (
        run['n'], int(far.sum()), tip['n'], info['tip_len'], len(mat.textures), body_dir)


# ---- Sephiroth's up special trail (tests 123 / 124, fighters/edge/weapons/trail.c from tools/edge_trail_msc.py): one
# article draws a stretch of the path, up to TRAIL_POINTS points: bones TopN, HaveN (nothing on it: the light arrow's
# kind draws HaveN on its owner), P0 - P15 (identity binds at the origin; the MSC moves joint 0x7D2 + k to point k).
# Between consecutive points two ribbons in the screen plane, one with its width along the model's Y (world up), one
# along its Z (world X, as the article faces +1), so a piece shows at any angle (narrowest, 0.7 of the width, at 45).
# Test 123 had one 8-long piece per article, 40 of them: the game crashed loading him (the article pool, holder +0x120
# list empty at 0x02C0337C: too many instances). The material is the light arrow's glow (its second: additive, blend
# 1 / 1), the texture a purple profile across the line made here
TRAIL_TEX = TX.article_id('edge', 'trail')      # the line; + 1 the fill's texture in the trail's .nut (were 0x40EBF100 / F101)
TRAIL_FILL_TEX = TRAIL_TEX + 1
TRAIL_HALF = 0.6                            # half the line's width
TRAIL_RGB = (150, 70, 255)                  # purple
TRAIL_POINTS = 16


def trail_textures():
    """the line's texture and the fill's, in one .nut (test 126: the trail draws its shapes' fill)"""
    return nut.write_ntwu([_trail_img(), _fill_img(TRAIL_FILL_TEX)])


def trail_texture():
    return nut.write_ntwu([_trail_img()])


def _trail_img():
    w, h = 32, 8
    u = (np.arange(w) + 0.5) / w * 2.0 - 1.0              # -1 .. 1 across the line
    core = np.clip(1.0 - np.abs(u), 0.0, 1.0) ** 1.6
    hot = np.clip(1.0 - np.abs(u) * 3.0, 0.0, 1.0) ** 2    # a whiter middle
    img = np.zeros((h, w, 4), np.uint8)
    for c in range(3):
        img[:, :, c] = np.clip(TRAIL_RGB[c] * core + 255 * 0.55 * hot, 0, 255).astype(np.uint8)[None, :]
    img[:, :, 3] = (255 * core).astype(np.uint8)[None, :]
    return (TRAIL_TEX, 0x1A, img)


def trail_bones():
    """TopN, HaveN, C (the fill's middle), W0 - W15 (the fill's points), A0 / B0 ... A14 / B14 (the line's pieces' ends,
    tools/edge_trail_msc.py's bones)"""
    names = ['TopN', 'HaveN', 'C'] + ['W%d' % k for k in range(TRAIL_POINTS)]
    for k in range(TRAIL_POINTS - 1):
        names += ['A%d' % k, 'B%d' % k]
    return names


def _glow_material(arrow_dir, tex):
    mat = nud.read(os.path.join(arrow_dir, 'model.nud'))[0].polygons[1].materials[0].copy()
    assert mat.src == 1 and mat.dst == 1, (mat.src, mat.dst)
    mat.textures = mat.textures[:1]
    mat.textures[0]['hash'] = tex
    mat.textures[0]['wrap_s'] = 3
    mat.cull = 0                             # both sides
    return mat


def _polygon(pos, uv, bones, idx, mat):
    n = len(pos)
    p = nud.Polygon()
    p.pos = np.array(pos, float)
    p.nrm = np.tile([1.0, 0.0, 0.0], (n, 1))
    p.tan = np.tile([0.0, 1.0, 0.0], (n, 1))
    p.bit = np.cross(p.nrm, p.tan)
    b = np.zeros((n, 4), np.int64)
    b[:, 0] = bones
    w = np.zeros((n, 4), np.int64)
    w[:, 0] = 255
    p.bones, p.weights = b, w
    p.uvs = [np.array(uv, float)]
    p.col = np.full((n, 4), WHITE)
    p.idx = np.array(idx, np.int64)
    p.materials = [mat]
    return p


def trail_mesh(arrow_dir):
    """the line: piece k two ribbons (width along the model's Y, and Z) between A_k and B_k; the fill: wedges C - W_k -
    W_k+1 (the fill texture, u 0 at the middle, 1 at the line)"""
    a_bone = 3 + TRAIL_POINTS
    pos, uv, bones, idx = [], [], [], []
    for k in range(TRAIL_POINTS - 1):
        for axis in (1, 2):
            v0 = len(pos)
            for end in (0, 1):
                for side in (-1, 1):
                    q = [0.0, 0.0, 0.0]
                    q[axis] = side * TRAIL_HALF
                    pos.append(q)
                    uv.append([(side + 1) * 0.5, float(end)])
                    bones.append(a_bone + 2 * k + end)
            idx += [v0, v0 + 1, v0 + 2, v0 + 1, v0 + 3, v0 + 2]
    line = _polygon(pos, uv, bones, idx, _glow_material(arrow_dir, TRAIL_TEX))
    pos, uv, bones, idx = [], [], [], []
    for k in range(TRAIL_POINTS - 1):
        v0 = len(pos)
        for b, u in ((2, 0.0), (3 + k, 1.0), (4 + k, 1.0)):
            pos.append([0.0, 0.0, 0.0])
            uv.append([u, 0.5])
            bones.append(b)
        idx += [v0, v0 + 1, v0 + 2]
    fill = _polygon(pos, uv, bones, idx, _glow_material(arrow_dir, TRAIL_FILL_TEX))
    return [nud.Mesh('trail', [line], bone=-1, bind=4), nud.Mesh('trailfill', [fill], bone=-1, bind=4)]


def build_trail(arrow_dir, out_fighter):
    meshes = trail_mesh(arrow_dir)
    tex = trail_textures()
    names = trail_bones()
    for c in range(COLOURS):
        d = os.path.join(out_fighter, 'model', 'trail', 'c%02d' % c)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'model.nud'), 'wb').write(nud.write(meshes))
        open(os.path.join(d, 'model.vbn'), 'wb').write(vbn(names))
        open(os.path.join(d, 'model.jtb'), 'wb').write(jtb(len(names)))
        open(os.path.join(d, 'model.nut'), 'wb').write(tex)
        for f in ('model.sb', 'model.nhb', 'model.mta', 'model.xmb'):
            shutil.copy(os.path.join(arrow_dir, f), os.path.join(d, f))
    return 'trail article: %d points (%d bones), ribbons %.1f wide, the light arrow\'s glow material, purple %s' % (
        TRAIL_POINTS, len(names), TRAIL_HALF * 2, TRAIL_RGB)


# ---- the closed-shape fill (test 125, fighters/edge/weapons/fill.c from tools/edge_fill_msc.py): a purple disc, bones
# TopN, HaveN, C (its middle, 0x7D2) and R0 - R15 (the rim, 0x7D3 + k, moved out to the radius by the MSC; all at the
# origin in the bind, so it draws nothing until then), a fan of triangles C - R_k - R_k+1 in the model's Y / Z plane
# (the screen: facing 1). The light arrow's glow material (additive) with a radial purple texture (u: middle 0 to rim
# 1): faint inside, bright at the rim
FILL_TEX = TX.article_id('edge', 'fill')        # the fill article's (was 0x40EBF101, the trail's too)
FILL_RIM = 16


def fill_texture():
    return nut.write_ntwu([_fill_img(FILL_TEX)])


def _fill_img(tex_id):
    w, h = 64, 8
    u = (np.arange(w) + 0.5) / w
    inner = 0.72 + 0.13 * u                  # near solid (test 132, the user: "shapes look part empty"; 0.30 - 0.55)
    rim = np.exp(-((u - 0.93) / 0.06) ** 2)
    val = np.clip(inner + rim, 0.0, 1.0)
    val[u > 0.985] *= 0.3                    # soft outer edge
    img = np.zeros((h, w, 4), np.uint8)
    for c in range(3):
        img[:, :, c] = np.clip(TRAIL_RGB[c] * val + 255 * 0.45 * rim, 0, 255).astype(np.uint8)[None, :]
    img[:, :, 3] = (255 * val).astype(np.uint8)[None, :]
    return (tex_id, 0x1A, img)


def fill_bones():
    """test 126: the fill is the shape's hitbox only (the trail draws the shape): TopN, HaveN, J0 - J4 (the spheres)"""
    return ['TopN', 'HaveN'] + ['J%d' % k for k in range(5)]


def fill_mesh(arrow_dir):
    """nothing to see: one triangle with no area on J0 (a model it must have)"""
    return [nud.Mesh('fill', [_polygon([[0.0, 0.0, 0.0]] * 3, [[0.0, 0.5]] * 3, [2, 2, 2], [0, 1, 2],
                                       _glow_material(arrow_dir, FILL_TEX))], bone=-1, bind=4)]


def build_fill(arrow_dir, out_fighter):
    meshes = fill_mesh(arrow_dir)
    tex = fill_texture()
    names = fill_bones()
    for c in range(COLOURS):
        d = os.path.join(out_fighter, 'model', 'fill', 'c%02d' % c)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'model.nud'), 'wb').write(nud.write(meshes))
        open(os.path.join(d, 'model.vbn'), 'wb').write(vbn(names))
        open(os.path.join(d, 'model.jtb'), 'wb').write(jtb(len(names)))
        open(os.path.join(d, 'model.nut'), 'wb').write(tex)
        for f in ('model.sb', 'model.nhb', 'model.mta', 'model.xmb'):
            shutil.copy(os.path.join(arrow_dir, f), os.path.join(d, f))
    return 'fill article: the shape\'s hitbox, %d bones (nothing drawn)' % len(names)


if __name__ == '__main__':
    print(build(*sys.argv[1:5]))
