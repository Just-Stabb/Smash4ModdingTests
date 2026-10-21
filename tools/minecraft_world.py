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
EXTRA = {'plains': ['door_plains_butcher_set', 'door_plains_firmer_set', 'vegetables_set'],
         'snowytundra': ['door_snowytundra_butcher_set'],
         'stoneshore': ['ring_stoneshore_water_set']}
ATLAS = 'all_blocks-rgba_c2_add'
TEX_BASE = 0x2000F000               # texture IDs of the port: 0x2000F001... (Battlefield's: 0x2000xxxx below 0x2000F000)
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


# ---------------------------------------------------------------- Ultimate stage data
# Breakable block kinds (pickel_world_breakable_NN.stdat "kind", index into pickel_world.stdat's
# block_info_table) -> bg_b_<model>_set. The files don't name them: worked out from where each kind
# sits in the six biomes (trunks / branches / leaves, the Plains house, the Stone Shore ores), the
# block table's materials and lives, and the models (tools: the block sheet in
# docs/minecraft-world.md). 7 (six "soil" blocks in Taiga) and 33 (two "snow" blocks at the Snowy
# Tundra igloo's ends) are guesses; 10 is the igloo (its 7 x 4 x 7 dome), the white snow block.
KIND_MODEL = {0: 'dirt_01', 1: 'wood_01', 2: 'stone_01', 3: 'iron_ore_01', 4: 'oakleaves_01',
              5: 'grass_block_01', 6: 'grass_block_savanna_01', 7: 'dirt_01', 9: 'hay_bale_01',
              10: 'snow_01', 11: 'cobblestone_01', 12: 'mossy_cobblestone_01',
              13: 'andesite_01', 14: 'diorite_01', 15: 'granite_01', 18: 'oak_pkanks_01',
              21: 'birch_log_01', 22: 'birch_log_02', 23: 'birchleaves_01', 24: 'acacia_log_01',
              25: 'acacia_log_02', 26: 'acacialeaves_01', 27: 'pine_log_01', 28: 'pine_log_02',
              29: 'pineleaves_01', 33: 'blue_ice_01', 35: 'furnace_01'}
# Smash 4 lvd surface kinds (material byte 3; Smash Forge's CollisionMatType) by Ultimate's names
MATERIAL = {'basic': 0, 'rock': 1, 'grass': 2, 'soil': 3, 'wood': 4, 'iron': 5, 'nibuiron': 6,
            'carpet': 7, 'numenume': 8, 'creature': 9, 'asase': 10, 'soft': 11, 'turuturu': 12,
            'snow': 13, 'ice': 14, 'gamewatch': 15, 'oil': 16, 'danbouru': 17, 'cloud': 22, 'brick': 24,
            'sand': 28}


def yaml_loader():
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    def any_tag(loader, _suffix, node):
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node, deep=True)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node, deep=True)
        return loader.construct_scalar(node)
    Loader.add_multi_constructor('!', any_tag)
    return Loader


def ult_lvd(path, yamlvd):
    """an Ultimate .lvd as a dict, through lvd-rs' yamlvd (github.com/ultimate-research/lvd-rs)"""
    import subprocess
    import tempfile
    import yaml
    with tempfile.TemporaryDirectory() as t:
        subprocess.run([yamlvd, path, t + '/x.yml'], check=True, capture_output=True)
        return yaml.load(open(t + '/x.yml'), Loader=yaml_loader())


def els(x):
    return x['elements'] if isinstance(x, dict) and 'elements' in x else x


def ult_prc(path, labels):
    """an Ultimate param file (.stdat / .prc) as plain dicts / lists, through pyprc"""
    import pyprc
    pyprc.hash.load_labels(labels)

    def conv(p):
        if p.type == pyprc.PARAM_TYPE_STRUCT:
            return {str(k): conv(v) for k, v in list(p)}
        if p.type == pyprc.PARAM_TYPE_LIST:
            return [conv(v) for v in list(p)]
        return str(p.value) if p.type == pyprc.PARAM_TYPE_HASH else p.value
    return conv(pyprc.param(path))


def material_code(name):
    return MATERIAL.get(str(name).lower(), 0)


# ---------------------------------------------------------------- blocks
def breakable_blocks(src, index, labels):
    """the biome's breakable blocks: [(kind, x, y, z, flags)] (10-unit cells: x [10x, 10x + 10],
    y [10y, 10y + 10], z [10z - 5, 10z + 5]; flags 1: throughable, under a pass-through floor)"""
    d = ult_prc('%s/normal/param/pickel_world_breakable_%02d.stdat' % (src, index), labels)
    return [(b['kind'], b['x'], b['y'], b['z'], b['flags']) for b in d['blocks']]


def block_parts(src, blocks):
    cube = {}
    out = []
    for kind, x, y, z, _f in blocks:
        model = KIND_MODEL[kind]
        if model not in cube:
            cube[model] = load_parts('%s/normal/model/bg_b_%s_set' % (src, model))
        out += translated(cube[model], np.array([x * 10 + 5.0, y * 10 + 5.0, z * 10.0]))
    return merged(out, 'blocks')


# ---------------------------------------------------------------- collision
def mat_bytes(surface, flags=0):
    m = bytearray(12)
    m[3] = surface
    m[10] = flags
    return m


def ult_collisions(d):
    """[dict(name, through, verts, normals, mats, hang_l/hang_r line sets, cliffs)]"""
    out = []
    for c in els(d['collisions']):
        attrs = els(c['attributes'])
        out.append(dict(
            name=c['base']['meta_info']['name'], through=bool(c['flags']['throughable']),
            verts=[(float(p['x']), float(p['y'])) for p in els(c['vertices'])],
            normals=[(float(p['x']), float(p['y'])) for p in els(c['normals'])],
            mats=[material_code(a['material']) for a in attrs],
            hang_l={i for i, a in enumerate(attrs) if a['flags']['hang_l']},
            hang_r={i for i, a in enumerate(attrs) if a['flags']['hang_r']},
            cliffs=[(float(x['pos']['x']), float(x['pos']['y']), float(x['lr']), int(x['line_index']))
                    for x in els(c.get('cliffs') or [])]))
    return out


def direct_collision(c, k):
    """an Ultimate collision as a Smash 4 one, line for line"""
    mats = [mat_bytes(m, (0x40 if i in c['hang_l'] else 0) | (0x80 if i in c['hang_r'] else 0))
            for i, m in enumerate(c['mats'])]
    name = 'COL_00_Platform%02d_through' % k if c['through'] else 'COL_00_Floor%02d' % k
    col = lvd.collision(name, c['verts'], c['normals'], mats, c['cliffs'], drop_through=c['through'])
    col.subname = name[4:]
    for cl in col.cliffs:
        cl.name = 'CLIFF_%s%s' % (name[4:], 'L' if cl.angle < 0 else 'R')
        cl.subname, cl.start = cl.name[6:], [cl.x, cl.y, 0.0]
    return col


def merged_floors(cols):
    """the pass-through collisions joined where they continue each other (Ultimate cuts them
    into 10-unit pieces, one a block, some drawn right to left): [(verts left to right, material)]"""
    segs = sorted((tuple(sorted((c['verts'][0], c['verts'][-1]))) + (c['mats'][0],) for c in cols),
                  key=lambda s: (s[0][1], s[0][0]))       # left to right, as Battlefield's platforms
    out = []
    for a, b, m in segs:
        if out and out[-1][0][-1] == a and a[1] == b[1] == out[-1][0][0][1] and out[-1][1] == m:
            out[-1][0].append(b)
        else:
            out.append(([a, b], m))
    return out


def inside(poly, x, y):
    n, c = len(poly), False
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            c = not c
    return c


def solid_grid(ground, blocks, block_mats, x0=-140, x1=140, y0=-200, y1=120):
    """10-unit cells in the fighting plane: [row][column] material code + 1 (0 = empty), row 0 at
    y0. The ground's cells are inside its outline (Ultimate's ground line closed along its ends);
    the blocks' cells are those on the plane (z 0), not throughable."""
    nx, ny = (x1 - x0) // 10, (y1 - y0) // 10
    occ = np.zeros((ny, nx), int)
    for j in range(ny):
        for i in range(nx):
            if inside(ground['verts'], x0 + i * 10 + 5, y0 + j * 10 + 5):
                occ[j, i] = -1                  # ground: material from the ground's own lines
    for kind, x, y, z, flags in blocks:
        if z == 0 and not flags:
            i, j = x - x0 // 10, y - y0 // 10
            if 0 <= i < nx and 0 <= j < ny:
                occ[j, i] = block_mats[kind] + 1
    return occ, x0, y0


def ground_line_material(ground, a, b):
    """the material of the ground line holding the edge a-b (Ultimate's lines are 10 units)"""
    for (p, q), m in zip(zip(ground['verts'], ground['verts'][1:]), ground['mats']):
        for e in (a, b):
            if abs((q[0] - p[0]) * (e[1] - p[1]) - (q[1] - p[1]) * (e[0] - p[0])) > 1e-3:
                break
            if not (min(p[0], q[0]) - 1e-3 <= e[0] <= max(p[0], q[0]) + 1e-3 and
                    min(p[1], q[1]) - 1e-3 <= e[1] <= max(p[1], q[1]) + 1e-3):
                break
        else:
            return m
    return MATERIAL['rock']


def outlines(occ, x0, y0, ground):
    """clockwise outlines (y up) of the solid cells, holes dropped: [[(x, y, material of the line
    from this point)]]; points kept where the direction or the material changes"""
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
                    m = occ[j, i] - 1 if occ[j, i] > 0 else ground_line_material(ground, *e)
                    edges[e] = m
    nxt = {}
    for (a, b), m in edges.items():
        nxt.setdefault(a, []).append((b, m))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, cur = [], start
        while True:
            b, m = nxt[cur].pop()
            if not nxt[cur]:
                del nxt[cur]
            loop.append((cur, m))
            if b == start:
                break
            cur = b
        pts = []
        n = len(loop)
        for k in range(n):
            (p, mp), (q, mq), r = loop[k - 1], loop[k], loop[(k + 1) % n][0]
            turn = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
            if turn != 0 or mp != mq:
                pts.append((q[0], q[1], mq))
        area = sum(pts[k - 1][0] * pts[k][1] - pts[k][0] * pts[k - 1][1] for k in range(len(pts))) / 2
        if area < 0:
            loops.append(pts)
    return loops


def grid_collisions(loops):
    """Smash 4 collisions from the outlines (the widest is the island: its outer top corners are
    the ledges, on 5-unit floor lines as Battlefield's)"""
    main = max(loops, key=lambda L: max(p[0] for p in L) - min(p[0] for p in L))
    left, right = min(p[0] for p in main), max(p[0] for p in main)
    left_y = max(p[1] for p in main if p[0] == left)
    right_y = max(p[1] for p in main if p[0] == right)
    cols = []
    for k, loop in enumerate([main] + [L for L in loops if L is not main]):
        is_main = k == 0
        start = min(range(len(loop)), key=lambda i: (loop[i][1], loop[i][0]))
        pts = loop[start:] + loop[:start]
        if is_main:
            out = []
            for i, p in enumerate(pts):
                out.append(p)
                q = pts[(i + 1) % len(pts)]
                if (p[0], p[1]) == (left, left_y) and q[1] == left_y and q[0] - p[0] > 10:
                    out.append((left + 5, left_y, p[2]))
                if (q[0], q[1]) == (right, right_y) and p[1] == right_y and q[0] - p[0] > 10:
                    out.append((right - 5, right_y, p[2]))
            pts = out
        pts = pts + [pts[0]]
        normals, mats, cliffs = [], [], []
        for i in range(len(pts) - 1):
            (ax, ay, m), (bx, by) = pts[i], pts[i + 1][:2]
            ln = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            normals.append((-(by - ay) / ln, (bx - ax) / ln))
            flags = 0
            if is_main and (ax, ay) == (left, left_y) and by == ay:
                flags = 0x40
                cliffs.append((ax, ay, -1, i))
            elif is_main and (bx, by) == (right, right_y) and by == ay:
                flags = 0x80
                cliffs.append((bx, by, 1, i))
            mats.append(mat_bytes(m, flags))
        c = lvd.collision('COL_00_Floor%02d' % (k + 1), [p[:2] for p in pts], normals, mats, cliffs)
        c.subname = '00_Floor%02d' % (k + 1)
        for cl in c.cliffs:
            cl.name = 'CLIFF_00_Floor%02d%s' % (k + 1, 'L' if cl.angle < 0 else 'R')
            cl.subname, cl.start = cl.name[6:], [cl.x, cl.y, 0.0]
        cols.append(c)
    return cols


def point(x, y):
    return [float(x), float(y)]


def build_lvd(base_lvd, d, cols):
    """BASE's lvd (Battlefield's: its entry names, section layout) with Ultimate's lvd d's points
    and regions and the collisions cols"""
    lv = lvd.LVD(base_lvd)
    lv.collisions = cols
    for mine, key in ((lv.spawns, 'start_positions'), (lv.respawns, 'restart_positions')):
        theirs = els(d[key])
        assert len(theirs) == len(mine), key
        for e, t in zip(mine, theirs):
            e.x, e.y = float(t['pos']['x']), float(t['pos']['y'])
    for mine, key in ((lv.camera, 'camera_regions'), (lv.blast, 'death_regions')):
        r = els(d[key])[0]['rect']
        mine[0].left, mine[0].right, mine[0].top, mine[0].bottom = (float(r[k]) for k in ('left', 'right', 'top', 'bottom'))
    paths = [[point(p['x'], p['y']) for p in els(s['path']['points'])]
             for s in els(els(d['item_popups'])[0]['shapes']['shapes'])]
    template = lv.items[0].sections[0]
    lv.items[0].sections = []
    for pts in paths:
        sec = lvd.Shape()
        sec.type, sec.v, sec.points = template.type, list(template.v), pts
        lv.items[0].sections.append(sec)
    kir = [e for e in els(d.get('general_shapes3') or []) if e['base']['meta_info']['name'].endswith('_Kir')]
    for e, t in zip(lv.points, kir):
        e.x, e.y, e.z = float(t['shape']['pos_x']), float(t['shape']['pos_y']), float(t['shape']['pos_z'])
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
        """NTP3 in the forms the game's own NTP3 files use (stage and UI): RGBA8 and DXT5 with one mip,
        DXT1 with a full mip chain; power-of-two sizes. (v1 had RGBA8 / DXT5 with mips and a 36x36
        texture, which no game file has; the stage froze while loading.)"""
        from PIL import Image
        texs = []
        for n in names:
            img = self.image(n)
            h, w = img.shape[:2]
            w2, h2 = min(2048, 1 << (w.bit_length() - 1)), min(2048, 1 << (h.bit_length() - 1))
            if (w2, h2) != (w, h):
                img = np.asarray(Image.fromarray(img).resize((w2, h2), Image.NEAREST if n.startswith('all_blocks')
                                                             else Image.LANCZOS))
            if n.startswith('all_blocks'):
                texs.append((self.ids[n], 14, [img]))
            elif (img[..., 3] < 250).any():
                texs.append((self.ids[n], 2, [img]))
            else:
                texs.append((self.ids[n], 0, nut.mip_chain(img, 1)))
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
def build_form(src, base_dir, out_dir, form, biome, hazards, yamlvd, labels):
    """form 'melee' (one biome) or 'end' (Omega: the battle folder's flat form)"""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(base_dir, out_dir)
    model_dir = out_dir + '/model'
    tex = Textures(src)
    if form == 'melee':
        index = BIOMES.index(biome)
        d = ult_lvd('%s/normal/param/pickel_world_%02d%s.lvd' % (src, index, '' if hazards else '_gimmick_off'), yamlvd)
        ring = load_parts('%s/normal/model/ring_%s_set' % (src, biome))
        blocks = breakable_blocks(src, index, labels) if hazards else []
        plat = []
        if os.path.exists('%s/normal/model/platform_%s_set' % (src, biome)):
            plat = load_parts('%s/normal/model/platform_%s_set' % (src, biome))
        extra = []
        for e in EXTRA.get(biome, []):
            extra += load_parts('%s/normal/model/%s' % (src, e))
        near = ring + (block_parts(src, blocks) if blocks else []) + plat + extra
        far = [p for p in load_parts('%s/normal/model/%s' % (src, FAR[biome])) if p['sub'] == 0]
        sky_src = '%s/normal/model/far_common_set' % src
    else:
        d = ult_lvd('%s/battle/param/pickel_world_end_00.lvd' % src, yamlvd)
        blocks = []
        near = load_parts('%s/battle/model/ring_endbattle_set' % src)
        far = [p for p in load_parts('%s/battle/model/far_plains_set' % src) if p['sub'] == 0]
        sky_src = '%s/battle/model/far_common_set' % src
    sky = [p for p in load_parts(sky_src)
           if p['label'] in ('sfx_sky_color', 'sfx_cloud', 'sfx_cloud_bottom', 'zz_sun', 'zz_sun_core')]

    for name in sorted(os.listdir(model_dir)):
        if os.path.exists('%s/%s/model.mta' % (model_dir, name)):      # material animations
            os.remove('%s/%s/model.mta' % (model_dir, name))
        if name not in (RING_SET, FAR_SET, SKY_SET):
            write_empty('%s/%s' % (model_dir, name))
    for name, parts, kind, is_sky in ((RING_SET, near, 'lit', False), (FAR_SET, far, 'bg', False),
                                      (SKY_SET, sky, 'bg', True)):
        write_set('%s/%s' % (model_dir, name), to_nud(parts, tex, kind, is_sky), tex)

    ucols = ult_collisions(d)
    solid = [c for c in ucols if not c['through']]
    if blocks:
        # the blocks on the fighting plane join the ground (one outline, as Battlefield's)
        info = ult_prc('%s/normal/param/pickel_world.stdat' % src, labels)['block_info_table']
        block_mats = [material_code(b['material']) for b in info]
        assert len(solid) == 1, [c['name'] for c in solid]
        occ, gx0, gy0 = solid_grid(solid[0], blocks, block_mats)
        cols = grid_collisions(outlines(occ, gx0, gy0, solid[0]))
    else:
        cols = [direct_collision(c, k + 1) for k, c in enumerate(solid)]
    floors = merged_floors([c for c in ucols if c['through']])
    for k, (verts, m) in enumerate(floors):
        c = lvd.collision('COL_00_Platform%02d_through' % (k + 1), verts, [(0, 1)] * (len(verts) - 1),
                          [mat_bytes(m)] * (len(verts) - 1), drop_through=True)
        c.subname = '00_Platform%02d_through' % (k + 1)
        cols.append(c)
    for f in os.listdir(out_dir + '/param'):
        if f.endswith('.lvd'):
            data = build_lvd(out_dir + '/param/' + f, d, cols).write()
            open(out_dir + '/param/' + f, 'wb').write(data)
    return cols, blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--biome', default='plains', choices=BIOMES)
    ap.add_argument('--name', default='NewStage01')
    ap.add_argument('--hazards', default='on', choices=('on', 'off'))
    ap.add_argument('--yamlvd', default='yamlvd', help="lvd-rs' yamlvd (reads Ultimate's .lvd)")
    ap.add_argument('--labels', default='ParamLabels.csv', help="ultimate-research/param-labels' ParamLabels.csv")
    a = ap.parse_args()
    for form in ('melee', 'end'):
        cols, blocks = build_form(a.src, '%s/%s/%s' % (a.base, form, a.name), '%s/stage/%s/%s' % (a.out, form, a.name),
                                  form, a.biome, a.hazards == 'on', a.yamlvd, a.labels)
        print('%s: %d collisions (%d drop-through), %d blocks' % (form, len(cols), sum(c.flags[3] for c in cols), len(blocks)))


if __name__ == '__main__':
    main()
