#!/usr/bin/env python3
"""Smash Ultimate's Minecraft World (stage/pickel_world) as a Smash 4 stage slot (NewStage01).

  python3 tools/minecraft_world.py SRC BASE OUT [--biome plains] [--name NewStage01]

SRC   Ultimate's stage/pickel_world folder (normal/ and battle/ with their model/ folders)
BASE  the slot's current stage folders: BASE/melee/NAME and BASE/end/NAME (a Battlefield copy)
OUT   writes OUT/stage/melee/NAME and OUT/stage/end/NAME: BASE's folders with the models,
      textures and collision replaced

What it builds (the Ultimate stage has no collision or stage code in the files, so both are made
here from the models):
- melee (normal play): one biome's ring (the island: terrain, the village / trees / house, the
  under-side), its "breakable" blocks placed where the stage puts them (the ink-able top faces
  ink_<biome>block_set has, one per block, give their cells; the kind of block isn't in the files:
  grass / dirt-like by biome), the biome's platforms, doors and (Plains) the farm, the far
  backdrop (day texture) and the sky (dome, clouds, sun).
- end (Omega): the battle folder's ring_end_l_set (the flat form), same backdrop and sky.
- collision: the solid cells of the ring and the blocks in the fighting plane (z = 0, 10-unit
  block grid), as outlines (ledges at the outer top corners of the main island), the platforms as
  drop-through lines; spawns / respawns / camera / blast zones / item areas from the layout.

Models go into Battlefield's model folders (stc_c_Ring_set: everything using the block atlas,
stc_k_BG_most_far2: the backdrop, stc_o_BG_clouds_set: the sky); every other model folder gets an
empty model (one zero-size triangle, a transparent 4x4 texture; melee's stc_a_surinuke_set is
Battlefield's pass-through platforms, so it's emptied too). Materials are Battlefield's: 0xA4001041
(stage ground: lit, vertex colors, shadows) with an alpha test for the block atlas' cut-outs,
0xA2000001 (its background plane) for the sky and backdrop. Textures are NTP3 .nut (nut.py).
"""
import argparse
import glob
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lvd  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import nutexb  # noqa: E402

BIOMES = ['plains', 'birchforest', 'savanna', 'taiga', 'snowytundra', 'stoneshore']
FAR = {'plains': 'far_plains_set', 'birchforest': 'far_birchforest_set', 'savanna': 'far_savanna_set',
       'taiga': 'far_taiga_set', 'snowytundra': 'far_snowytundra_set', 'stoneshore': 'far_stoneshore_set'}
# blocks: (top block, block under another); bg_b_<kind>_01_set
BLOCKS = {'plains': ('grass_block', 'dirt'), 'birchforest': ('grass_block', 'dirt'),
          'savanna': ('grass_block_savanna', 'dirt'), 'taiga': ('grass_block', 'dirt'),
          'snowytundra': ('grass_block_tundra', 'dirt'), 'stoneshore': ('stone', 'stone')}
EXTRA = {'plains': ['door_plains_butcher_set', 'door_plains_firmer_set', 'vegetables_set'],
         'snowytundra': ['door_snowytundra_butcher_set'],
         'stoneshore': ['ring_stoneshore_water_set']}
# surface kind of the collision (lvd material byte 3): soil, rock
SURFACE = {'plains': 3, 'birchforest': 3, 'savanna': 3, 'taiga': 3, 'snowytundra': 0x0D, 'stoneshore': 1}

ATLAS = 'all_blocks-rgba_c2_add'
TEX_BASE = 0x204D0000               # texture IDs of the port: 0x204D0001...
LIT, BG = 0xA4001041, 0xA2000001
CULL = {'Back': 1029, 'Front': 1028, 'Disabled': 0}
SKY_TOP, SKY_HORIZON = np.array([0.47, 0.65, 1.0]), np.array([0.75, 0.85, 1.0])
CLOUD_ALPHA = 0.7                   # the cloud layer, seen from under it, would hide most of the sky

RING_SET, FAR_SET, SKY_SET = 'stc_c_Ring_set', 'stc_k_BG_most_far2', 'stc_o_BG_clouds_set'
EMPTY_TEX = TEX_BASE + 0xFFFF


# ---------------------------------------------------------------- Ultimate models
def _world(skel):
    """bone name -> world matrix (row vectors: p' = p @ M)"""
    out = {}
    for b in skel.bones:
        m = np.array(b.transform, dtype=np.float64)
        if b.parent_index is not None and b.parent_index >= 0:
            m = m @ out[skel.bones[b.parent_index].name]
        out[b.name] = m
    return out


def load_parts(setdir):
    """the set's meshes as dicts (world positions, normals, colors, uv, triangles, material info)"""
    import ssbh_data_py as s
    mesh = s.mesh_data.read_mesh(setdir + '/model.numshb')
    modl = s.modl_data.read_modl(setdir + '/model.numdlb')
    matl = {e.material_label: e for e in s.matl_data.read_matl(setdir + '/model.numatb').entries}
    world = {}
    if os.path.exists(setdir + '/model.nusktb'):
        world = _world(s.skel_data.read_skel(setdir + '/model.nusktb'))
    parts = []
    for o in mesh.objects:
        label = [e.material_label for e in modl.entries
                 if e.mesh_object_name == o.name and e.mesh_object_subindex == o.subindex][0]
        mat = matl[label]
        pos = np.array(o.positions[0].data, dtype=np.float64)[:, :3]
        nrm = np.array(o.normals[0].data, dtype=np.float64)[:, :3] if o.normals else None
        m = world.get(o.parent_bone_name)
        if m is not None:
            pos = np.c_[pos, np.ones(len(pos))] @ m
            pos = pos[:, :3]
            if nrm is not None:
                nrm = nrm @ m[:3, :3]
                nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        parts.append(dict(
            name=o.name, sub=o.subindex, pos=pos, nrm=nrm, label=label, shader=mat.shader_label,
            # colorSet1 is the vertex color (0.5 = 1.0); the others are shader inputs (the
            # backdrops' colorSet5 is a constant 0.33)
            col=next((np.array(c.data, dtype=np.float64) for c in o.color_sets if c.name == 'colorSet1'), None),
            uv=np.array(o.texture_coordinates[0].data, dtype=np.float64)[:, :2] if o.texture_coordinates else None,
            idx=np.array(o.vertex_indices, dtype=np.int64),
            textures=[t.data.lower() for t in mat.textures if not t.data.startswith('#')],
            blend=any(b.data.destination_color.name != 'Zero' for b in mat.blend_states),
            cull=CULL.get(mat.rasterizer_states[0].data.cull_mode.name, 1029) if mat.rasterizer_states else 1029))
    return parts


def translated(parts, offset):
    return [dict(p, pos=p['pos'] + offset) for p in parts]


def merged(parts, name):
    """parts with the same material as one part"""
    out = {}
    for p in parts:
        key = (p['label'], tuple(p['textures']), p['blend'], p['cull'])
        if key not in out:
            out[key] = dict(p, name=name, sub=len(out), pos=[], nrm=[], col=[], uv=[], idx=[], n=0)
        m = out[key]
        m['idx'].append(p['idx'] + m['n'])
        m['n'] += len(p['pos'])
        for k in ('pos', 'nrm', 'col', 'uv'):
            m[k].append(p[k])
    for m in out.values():
        for k in ('pos', 'nrm', 'col', 'uv', 'idx'):
            m[k] = np.concatenate(m[k])
    return list(out.values())


# ---------------------------------------------------------------- layout
def block_cells(src, biome):
    """{(column, row): (z_min, z_max)} of the biome's blocks, from ink_<biome>block_set"""
    import ssbh_data_py as s
    path = '%s/normal/model/ink_%sblock_set/model.numshb' % (src, biome)
    cells = {}
    for o in s.mesh_data.read_mesh(path).objects:
        p = np.array(o.positions[0].data)[:, :3]
        lo, hi = p.min(0), p.max(0)
        col, row = int(round(lo[0] / 10)), int(round(hi[1] / 10)) - 1
        cells[(col, row)] = (int(round(lo[2] / 10)) * 10, int(round(hi[2] / 10)) * 10)
    return cells


def block_parts(src, biome, cells):
    top_kind, fill_kind = BLOCKS[biome]
    cube = {}
    out = []
    for (c, r), (z0, z1) in sorted(cells.items()):
        kind = fill_kind if (c, r + 1) in cells else top_kind
        if kind not in cube:
            cube[kind] = load_parts('%s/normal/model/bg_b_%s_01_set' % (src, kind))
        for z in range(z0, z1, 10):
            out += translated(cube[kind], np.array([c * 10 + 5, r * 10 + 5, z + 5.0]))
    return merged(out, 'blocks_%s' % biome)


def solid_grid(tris_list, cells, x0=-140, x1=140, y0=-200, y1=120):
    """occupancy of 10-unit cells in the plane z = 0 ([row][column], row 0 at y0): parity of the
    faces facing +-x the cell-center rows cross, plus the block cells"""
    nx, ny = (x1 - x0) // 10, (y1 - y0) // 10
    occ = np.zeros((ny, nx), bool)
    T = np.concatenate(tris_list)
    xs = T[:, :, 0]
    F = T[(np.ptp(xs, 1) < 1e-3) & (T[:, :, 2].min(1) < 0) & (T[:, :, 2].max(1) > 0)]
    a, b, c = F[:, 0, 1:], F[:, 1, 1:], F[:, 2, 1:]
    v0, v1 = b - a, c - a
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1)
    for j in range(ny):
        v2 = np.array([y0 + j * 10 + 5.0, 0.0]) - a
        u = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        v = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        hit = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
        hx = np.unique(np.round(F[hit, 0, 0], 2))
        for i in range(nx):
            occ[j, i] = (hx < x0 + i * 10 + 5).sum() % 2 == 1
    for (cc, r), (z0, z1) in cells.items():
        if z0 < 0 < z1 or z0 <= 0 <= z1:
            i, j = cc - x0 // 10, r - y0 // 10
            if 0 <= i < nx and 0 <= j < ny:
                occ[j, i] = True
    return occ, x0, y0


def outlines(occ, x0, y0):
    """clockwise outlines (y up) of the solid regions, holes dropped: [[(x, y), ...]] closed"""
    ny, nx = occ.shape
    edges = {}
    for j in range(ny):
        for i in range(nx):
            if not occ[j, i]:
                continue
            X, Y = x0 + i * 10, y0 + j * 10
            for e in (((X, Y + 10), (X + 10, Y + 10)), ((X + 10, Y + 10), (X + 10, Y)),
                      ((X + 10, Y), (X, Y)), ((X, Y), (X, Y + 10))):
                if (e[1], e[0]) in edges:
                    del edges[(e[1], e[0])]
                else:
                    edges[e] = True
    nxt = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        while True:
            b = nxt[cur].pop()
            if not nxt[cur]:
                del nxt[cur]
            if b == start:
                break
            loop.append(b)
            cur = b
        # merge collinear points
        pts = []
        n = len(loop)
        for k in range(n):
            p, q, r = loop[k - 1], loop[k], loop[(k + 1) % n]
            if (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]) != 0:
                pts.append(q)
        area = sum(pts[k - 1][0] * pts[k][1] - pts[k][0] * pts[k - 1][1] for k in range(len(pts))) / 2
        if area < 0:                    # clockwise: an outer outline
            loops.append(pts)
    return loops


def platform_tops(parts):
    """drop-through platforms: the up-facing faces crossing z = 0, as (x0, x1, y)"""
    segs = []
    for p in parts:
        T = p['pos'][p['idx'].reshape(-1, 3)]
        flat = np.ptp(T[:, :, 1], 1) < 1e-3
        up = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])[:, 1] > 0
        cross = (T[:, :, 2].min(1) <= 0) & (T[:, :, 2].max(1) >= 0)
        for t in T[flat & up & cross]:
            segs.append((round(t[:, 0].min(), 1), round(t[:, 0].max(), 1), round(t[0, 1], 1)))
    by_y = {}
    for a, b, y in segs:
        by_y.setdefault(y, []).append((a, b))
    out = []
    for y in sorted(by_y):
        iv = sorted(by_y[y])
        cur = list(iv[0])
        for a, b in iv[1:]:
            if a <= cur[1] + 0.1:
                cur[1] = max(cur[1], b)
            else:
                out.append((cur[0], cur[1], y))
                cur = [a, b]
        out.append((cur[0], cur[1], y))
    # drop faces under another face of the same platform (keep the top of each)
    keep = []
    for a, b, y in out:
        if not any(aa <= a + 0.1 and bb >= b - 0.1 and yy > y and yy - y < 6 for aa, bb, yy in out):
            keep.append((a, b, y))
    return keep


# ---------------------------------------------------------------- collision
def mat_bytes(surface, flags=0):
    m = bytearray(12)
    m[3] = surface
    m[10] = flags
    return m


def build_lvd(base_lvd, loops, platforms, surface):
    lv = lvd.LVD(base_lvd)
    template = lv.collisions[0]
    main = max(loops, key=lambda L: max(p[0] for p in L) - min(p[0] for p in L))
    left, right = min(p[0] for p in main), max(p[0] for p in main)
    # the ledges: the outer top corners, where the outer walls meet the floor
    left_y = max(p[1] for p in main if p[0] == left)
    right_y = max(p[1] for p in main if p[0] == right)
    cols = []
    for k, loop in enumerate([main] + [L for L in loops if L is not main]):
        is_main = k == 0
        cliffs = []
        # start at the bottom-left so the outline reads as Battlefield's
        start = min(range(len(loop)), key=lambda i: (loop[i][1], loop[i][0]))
        pts = loop[start:] + loop[:start]
        if is_main:
            # split the floor lines at the ledges 5 units in, as Battlefield does
            out = []
            for i, p in enumerate(pts):
                out.append(p)
                q = pts[(i + 1) % len(pts)]
                if p == (left, left_y) and q[1] == left_y and q[0] - p[0] > 10:
                    out.append((left + 5, left_y))
                if q == (right, right_y) and p[1] == right_y and q[0] - p[0] > 10:
                    out.append((right - 5, right_y))
            pts = out
        pts = pts + [pts[0]]
        normals, mats = [], []
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            ln = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            n = (-(by - ay) / ln, (bx - ax) / ln)
            flags = 0
            if is_main and (ax, ay) == (left, left_y) and by == ay:
                flags = 0x40
                cliffs.append((ax, ay, -1, i))
            elif is_main and (bx, by) == (right, right_y) and by == ay:
                flags = 0x80
                cliffs.append((bx, by, 1, i))
            normals.append(n)
            mats.append(mat_bytes(surface, flags))
        c = lvd.collision('COL_00_Floor%02d' % (k + 1), pts, normals, mats, cliffs)
        c.subname = '00_Floor%02d' % (k + 1)
        for cl in c.cliffs:
            cl.name = 'CLIFF_00_Floor%02d%s' % (k + 1, 'L' if cl.angle < 0 else 'R')
        c.unk3 = template.unk3
        cols.append(c)
    for k, (a, b, y) in enumerate(platforms):
        c = lvd.collision('COL_00_Platform%02d_through' % (k + 1), [(a, y), (b, y)], [(0, 1)],
                          [mat_bytes(4)], drop_through=True)
        c.subname = '00_Platform%02d_through' % (k + 1)
        cols.append(c)
    lv.collisions = cols
    return lv, main


def floor_height(loops, platforms, x):
    """the highest floor at x (outline lines facing up, platforms)"""
    best = None
    for L in loops:
        P = L + [L[0]]
        for (ax, ay), (bx, by) in zip(P, P[1:]):
            if ay == by and bx > ax and ax <= x <= bx and (best is None or ay > best):
                best = ay
    for a, b, y in platforms:
        if a <= x <= b and (best is None or y > best):
            best = y
    return best


def place_points(lv, loops, platforms, main, blast_margin):
    xs = [p[0] for p in main]
    left, right = min(xs), max(xs)
    mid = (left + right) / 2
    half = (right - left) / 2
    ground = floor_height([main], [], left + 1)

    def flat(x):
        """the island's floor at x if it's flat 5 units either side"""
        y = [floor_height([main], [], x + d) for d in (-5, 0, 5)]
        return y[0] if y[0] is not None and y[0] == y[1] == y[2] else None

    cand = [float(x) for x in np.arange(left + 15, right - 14, 5.0) if flat(x) is not None]
    # players 1 / 2: a mirrored pair at least 20% of the half width from the middle, nearest 35%
    # (on the ground level if there is one), else the spots nearest -35% / +35%
    pairs = [d for d in range(5, int(half) - 10, 5) if mid - d in cand and mid + d in cand]
    pairs.sort(key=lambda d: (d < 0.2 * half, flat(mid - d) != ground or flat(mid + d) != ground,
                              abs(d - 0.35 * half)))
    if pairs:
        chosen = [mid - pairs[0], mid + pairs[0]]
    else:
        chosen = [min((x for x in cand if x < mid), key=lambda x: abs(x - mid + 0.35 * half), default=cand[0]),
                  min((x for x in cand if x > mid), key=lambda x: abs(x - mid - 0.35 * half), default=cand[-1])]
    while len(chosen) < len(lv.spawns):
        chosen.append(max(cand, key=lambda x: min(abs(x - y) for y in chosen)))
    for s, x in zip(lv.spawns, chosen):
        s.x, s.y = round(x, 1), flat(x)
    highest = max(floor_height(loops, platforms, x + 5.0) or ground for x in range(int(left), int(right), 10))
    re_x = [0, 0.36, -0.36, 0.72, -0.18, 0.18, -0.54, 0.54]
    for s, f in zip(lv.respawns, re_x):
        s.x = round(f * half * 0.9 + mid, 1)
        s.y = highest + (50 if abs(f) in (0, 0.36, 0.72) else 78)
    cam = lv.camera[0]
    cam.left, cam.right = left - 90, right + 90
    cam.top, cam.bottom = max(130.0, highest + 110), -80.0
    bl = lv.blast[0]
    bl.left, bl.right = left - blast_margin, right + blast_margin
    bl.top, bl.bottom = max(192.0, highest + 170), -140.0
    for it in lv.items:
        it.sections = it.sections[:1]
        it.sections[0].points = [[left + 20, highest + 60], [right - 20, highest + 60]]
    return lv


# ---------------------------------------------------------------- NUD / NUT
class Textures:
    def __init__(self, src):
        self.src = src
        self.ids = {}
        self.order = []
        self.files = {os.path.basename(f)[:-7].lower(): f
                      for f in glob.glob(src + '/*/model/*/*.nutexb') + glob.glob(src + '/*/render/*.nutexb')}

    def id(self, name):
        if name not in self.ids:
            self.ids[name] = TEX_BASE + 1 + len(self.ids)
            self.order.append(name)
        return self.ids[name]

    def image(self, name):
        if name == 'default_white':
            return np.full((8, 8, 4), 255, np.uint8)
        return nutexb.decode(nutexb.Nutexb(self.files[name]))

    def nut(self, names):
        from PIL import Image
        texs = []
        for n in names:
            img = self.image(n)
            if n.startswith('all_blocks'):
                texs.append((self.ids[n], 14, nut.mip_chain(img, 32)))
                continue
            h, w = img.shape[:2]
            if w > 2048 or h > 2048:
                k = 2048 / max(w, h)
                img = np.asarray(Image.fromarray(img).resize((int(w * k) // 4 * 4, int(h * k) // 4 * 4), Image.LANCZOS))
            fmt = 2 if (img[..., 3] < 250).any() else 0
            texs.append((self.ids[n], fmt, nut.mip_chain(img, 4)))
        return nut.write_ntp3(texs)


def material(kind, tex_id, nearest, blend, cull, alpha_test):
    m = nud.Material(LIT if kind == 'lit' else BG, 1 if blend else 0, 1 if blend else 0,
                     518 if alpha_test else 0, 128 if alpha_test else 0, cull)
    m.textures.append(dict(hash=tex_id, map_mode=0, wrap_s=1, wrap_t=1, min_f=3 if nearest else 0,
                           mag_f=1 if nearest else 2, mip=6, unk=0, unk2=7936))
    m.props = [('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0]), ('NU_diffuseColor', [1.0, 1.0, 1.0, 1.0]),
               ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])]
    return m


def to_nud(parts, tex, kind, sky=False):
    meshes = []
    for p in parts:
        if not p['textures'] or p['uv'] is None:
            continue
        tname = p['textures'][0]
        if tname.startswith('all_blocks-rgba_c2_add') and tname not in ('all_blocks-rgba_c2_add_vegetables',):
            tname = ATLAS
        tid = tex.id(tname)
        poly = nud.Polygon()
        poly.pos, poly.nrm, poly.uvs = p['pos'], p['nrm'], [p['uv']]
        col = p['col'] if p['col'] is not None else np.full((len(p['pos']), 4), 0.502)
        col = np.clip(np.round(col * 253), 0, 255)
        if sky:
            # Ultimate tints the sky in its shader; a day gradient instead
            d = p['pos'] / (np.linalg.norm(p['pos'], axis=1, keepdims=True) + 1e-9)
            t = np.clip(d[:, 1:2] * 3, 0, 1)
            if p['label'] == 'sfx_sky_color':
                col[:, :3] *= (SKY_HORIZON * (1 - t) + SKY_TOP * t) * 2
            elif p['label'].startswith('sfx_cloud'):
                col[:, 3] = 127 * CLOUD_ALPHA
            col = np.clip(col, 0, 255)
        poly.col = col
        poly.idx = p['idx']
        atlas = tname.startswith('all_blocks')
        cloud = sky and p['label'].startswith('sfx_cloud')
        poly.materials = [material(kind, tid, atlas, p['blend'] and not atlas or cloud, p['cull'],
                                   atlas or kind == 'bg' and not sky)]
        if len(poly.pos) >= 0x10000:
            raise ValueError('%s: %d vertices' % (p['name'], len(poly.pos)))
        meshes.append(nud.Mesh('%s_%d' % (p['name'], p['sub']), [poly]))
    return meshes


def write_empty(outdir):
    poly = nud.Polygon()
    poly.pos = np.zeros((3, 3))
    poly.nrm = np.tile([0.0, 1.0, 0.0], (3, 1))
    poly.col = np.full((3, 4), 127.0)
    poly.uvs = [np.zeros((3, 2))]
    poly.idx = np.array([0, 1, 2])
    poly.materials = [material('bg', EMPTY_TEX, False, False, 0, True)]
    mesh = nud.Mesh('empty', [poly])
    mesh.sphere = [0.0, 0.0, 0.0, 1.0]
    open(outdir + '/model.nud', 'wb').write(nud.write([mesh]))
    open(outdir + '/model.nut', 'wb').write(nut.write_ntp3([(EMPTY_TEX, 14, [np.zeros((4, 4, 4), np.uint8)])]))


def write_set(outdir, meshes, tex):
    os.makedirs(outdir, exist_ok=True)
    used = []
    for m in meshes:
        for p in m.polygons:
            for mat in p.materials:
                for t in mat.textures:
                    n = tex.order[t['hash'] - TEX_BASE - 1]
                    if n not in used:
                        used.append(n)
    open(outdir + '/model.nud', 'wb').write(nud.write(meshes))
    open(outdir + '/model.nut', 'wb').write(tex.nut(used))


# ---------------------------------------------------------------- stage
def build_form(src, base_dir, out_dir, form, biome):
    """form 'melee' (the biome) or 'end' (the flat form)"""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(base_dir, out_dir)
    model_dir = out_dir + '/model'
    tex = Textures(src)
    cells = {}
    if form == 'melee':
        ring = load_parts('%s/normal/model/ring_%s_set' % (src, biome))
        cells = block_cells(src, biome)
        blocks = block_parts(src, biome, cells)
        plat = []
        if os.path.exists('%s/normal/model/platform_%s_set' % (src, biome)):
            plat = load_parts('%s/normal/model/platform_%s_set' % (src, biome))
        extra = []
        for e in EXTRA.get(biome, []):
            extra += load_parts('%s/normal/model/%s' % (src, e))
        near = ring + blocks + plat + extra
        solid_tris = [p['pos'][p['idx'].reshape(-1, 3)] for p in ring if p['sub'] in (1, 2)]
        far = [p for p in load_parts('%s/normal/model/%s' % (src, FAR[biome])) if p['sub'] == 0]
        sky_src = '%s/normal/model/far_common_set' % src
    else:
        ring = load_parts('%s/battle/model/ring_end_l_set' % src)
        plat = []
        near = ring
        solid_tris = [p['pos'][p['idx'].reshape(-1, 3)] for p in ring if p['sub'] in (1, 2)]
        far = [p for p in load_parts('%s/battle/model/far_plains_set' % src) if p['sub'] == 0]
        sky_src = '%s/battle/model/far_common_set' % src
    sky = [p for p in load_parts(sky_src)
           if p['label'] in ('sfx_sky_color', 'sfx_cloud', 'sfx_cloud_bottom', 'zz_sun', 'zz_sun_core')]

    for d in sorted(os.listdir(model_dir)):
        if os.path.exists('%s/%s/model.mta' % (model_dir, d)):      # material animations
            os.remove('%s/%s/model.mta' % (model_dir, d))
        if d not in (RING_SET, FAR_SET, SKY_SET):
            write_empty('%s/%s' % (model_dir, d))
    for d, parts, kind, is_sky in ((RING_SET, near, 'lit', False), (FAR_SET, far, 'bg', False),
                                   (SKY_SET, sky, 'bg', True)):
        write_set('%s/%s' % (model_dir, d), to_nud(parts, tex, kind, is_sky), tex)

    occ, gx0, gy0 = solid_grid(solid_tris, cells)
    loops = outlines(occ, gx0, gy0)
    platforms = platform_tops(plat)
    lvds = [f for f in os.listdir(out_dir + '/param') if f.endswith('.lvd')]
    for f in lvds:
        lv, main = build_lvd(out_dir + '/param/' + f, loops, platforms, SURFACE[biome if form == 'melee' else 'plains'])
        place_points(lv, loops, platforms, main, 165)
        open(out_dir + '/param/' + f, 'wb').write(lv.write())
    return loops, platforms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--biome', default='plains', choices=BIOMES)
    ap.add_argument('--name', default='NewStage01')
    a = ap.parse_args()
    for form in ('melee', 'end'):
        loops, platforms = build_form(a.src, '%s/%s/%s' % (a.base, form, a.name), '%s/stage/%s/%s' % (a.out, form, a.name),
                                      form, a.biome)
        print('%s: %d outlines, %d platforms' % (form, len(loops), len(platforms)))


if __name__ == '__main__':
    main()
