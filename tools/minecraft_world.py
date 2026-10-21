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

Models go into Battlefield's model folders that have no material animation (model.mta):
stc_c_Ring_set (everything using the block atlas), stc_k_BG_most_far2 (the backdrop) and
stc_BG_most_far2_1_set (the sky; its own model.xmb: draw range 2, as Battlefield's sky dome: the
clouds' range 4 clipped it). Every other folder keeps Battlefield's files with the model's indices zeroed
(nud.hidden: nothing drawn, its .mta / skeleton still match it). Only what Battlefield's own
models have: its shaders (material flags, with its vertex layout), NTWU textures as its single-mip
ones (nut.write_ntwu). The first builds (NTP3 textures, an empty model in every folder, other
material flags) froze the game while loading the models. The island is lit by the stage's lights,
held at Battlefield's midday (still_light); the backdrop and sky are unlit, as Ultimate's.
"""
import argparse
import glob
import os
import shutil
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lvd  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import nutexb  # noqa: E402
import omo  # noqa: E402

BIOMES = ['plains', 'birchforest', 'savanna', 'taiga', 'snowytundra', 'stoneshore']
FAR = {'plains': 'far_plains_set', 'birchforest': 'far_birchforest_set', 'savanna': 'far_savanna_set',
       'taiga': 'far_taiga_set', 'snowytundra': 'far_snowytundra_set', 'stoneshore': 'far_stoneshore_set'}
EXTRA = {'plains': ['door_plains_butcher_set', 'door_plains_firmer_set', 'vegetables_set'],
         'snowytundra': ['door_snowytundra_butcher_set'],
         'stoneshore': ['ring_stoneshore_water_set']}
ATLAS = 'all_blocks-rgba_c2_add'
TEX_BASE = 0x2000F000               # texture IDs of the port: 0x2000F001... (Battlefield's: 0x2000xxxx below 0x2000F000)
CULL = {'Back': 1029, 'Front': 1028, 'Disabled': 0}
# the panorama's fog layer: its texture is white with alpha 0 at the top rows, 1 at the bottom, and
# its UVs put the bottom rows on the near ground, the top near the horizon, which as read would
# hide the hills near the island and clear them at the horizon; Ultimate shows the opposite (clear
# near, hazy far: the user's screenshots), so the ramp is read the other way up, at this strength
FAR_FOG_ALPHA = 0.8
GAMMA = 2.2                         # Ultimate's material colors are linear; Smash 4's vertex colors not
SKY_LABELS = ('sfx_sky_color', 'sfx_cloud', 'sfx_cloud_bottom', 'zz_sun', 'zz_sun_core', 'fog_near')

RING_SET, FAR_SET, SKY_SET = 'stc_c_Ring_set', 'stc_k_BG_most_far2', 'stc_BG_most_far2_1_set'
# the cloud layers (far_common_set's bones cloud_model0-2, moved by its animation) each in a
# Battlefield dyr_ folder with one bone, draw range 2 and no material animation, bound to the
# bone, with an animation of the layer's motion (as moving_platform_test.py's platform, which the
# stage plays): Ultimate's frames 0 to CLOUD_PERIOD (each layer slides 10.8 a frame and jumps
# back every 2250 frames; the middle one half a period out of step, so all repeat after 4500)
CLOUD_SETS = {'cloud_model0': 'dyr_i_BG_more_far1_set', 'cloud_model1': 'dyr_j_BG_most_far0_set',
              'cloud_model2': 'dyr_l_BG_more_far2_set'}
CLOUD_PERIOD = 4500
# torches: Ultimate puts its flame / smoke effect (ef_pickel_world.eff's P_PickelWorldFire) at
# pickel_world_visual.stdat's torch_info_table points (row = biome; 6 = the battle / Omega island).
# Smash 4 can't take Ultimate's effects (other format, compiled Switch shaders), so: the effect's
# own sprites (its BNTX: ef_pickelworld_fire00, smoke00) on quads, each on a bone of a made
# skeleton in a dyr_ folder (all bones at the origin, as Battlefield's), animated: the flame
# flickering, two smoke puffs a torch rising and shrinking, out of step
TORCH_SET = 'dyr_change_160_2_O_OBJ_O_HIR_set'
TORCH_ROW_END = 6
TORCH_LOOP = 240                    # frames; the flicker periods and the smoke's life divide it
SMOKE_LIFE, SMOKE_RISE, SMOKE_SHRINK = 60, 7.0, 0.7
FLAME_SIZE, SMOKE_SIZE = 3.0, 2.5
SMOKE_GREY, SMOKE_ALPHA = 0.45, 0.8
SKY_GRADIENT = 'sky_gradient'       # a made texture: the day sky from the top (v 0) to the horizon
SPLIT = 2                           # the panorama (3200x1600) in this many 2048x2048 textures,
SPLIT_OVERLAP = 0.0625              # overlapping by its widest triangle (u)
# Ultimate's colorSet1 on the ring and blocks is Minecraft's corner shading (0.5 = none) and is
# kept at this fraction; shaders SFX_PBS_52... (doors, crops) get values near 0 there that they
# can't use as color (they look lit in Ultimate), so those are 0.5
AO_KEEP = 0.5
DAY_FRAME = 945                     # Battlefield's light.bin: its most neutral midday frame
# NAME_stprm.bin (typed values: a type byte, then the value): Battlefield's normal camera is
# value 6 fov 30, 7 / 8 distance 83 / 1000, 9 vertical angle -5, 10 look-down angle -15 (Ultimate's
# pickel_world's stageparam: 30, 83 / 1000, -5, -22): Ultimate's, where the fields match.
CAMERA = {6: 30.0, 7: 83.0, 8: 1000.0, 9: -5.0, 10: -22.0}
ISLAND_LIGHT_SET = 4                # stc_c_Ring_set's model.xmb light set
# the island's light set, from Ultimate's (render/light/light00_set.nuanmb, frame 0 = day): its
# stage light is white from (0.20, 0.90, 0.38) (travel direction below, as light.bin's); Ultimate's
# ambient (spherical harmonics) becomes a sky light from above, a fill from the camera and the 4th
# (off, no direction: Battlefield's ambient color). (enabled, direction, hue, saturation, value)
ISLAND_LIGHTS = [(1, (-0.204, -0.903, -0.379), 0.0, 0.0, 0.75),
                 (1, (0.0, -1.0, 0.0), 210.0, 0.1, 0.15),
                 (1, (0.0, -0.259, -0.966), 0.0, 0.0, 0.4),
                 (0, (0.0, 0.0, 0.0), 0.0, 0.0, 0.45)]


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
            bone=o.parent_bone_name,
            # colorSet1 is the vertex color (0.5 = 1.0); the others are shader inputs (the
            # backdrops' colorSet5 is a constant 0.33)
            col=next((np.array(c.data, dtype=np.float64) for c in o.color_sets if c.name == 'colorSet1'), None),
            uv=np.array(o.texture_coordinates[0].data, dtype=np.float64)[:, :2] if o.texture_coordinates else None,
            idx=np.array(o.vertex_indices, dtype=np.int64),
            textures=[t.data.lower() for t in mat.textures if not t.data.startswith('#')],
            # Ultimate's emission shaders (a Texture5): color = texture x CustomVector3 x CustomVector8
            # x colorSet1 x 2, unlit (render/shader/nuc2effectlibrary.nufxlb's programs)
            emissive=any(str(t.param_id).split('.')[-1].startswith('Texture5') for t in mat.textures),
            vec={str(v.param_id).split('.')[-1].split(':')[0]: np.array(v.data, dtype=np.float64) for v in mat.vectors},
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
        self.sky = np.ones((256, 3))
        self.extra = {}                     # made textures: name -> RGBA
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
        if name in self.extra:
            return self.extra[name]
        if name == SKY_GRADIENT:
            img = np.empty((256, 64, 4), np.uint8)
            img[..., :3] = np.round(np.clip(self.sky, 0, 1) * 255)[:, None, :]
            img[..., 3] = 255
            return img
        if '#' in name:                     # 'NAME#k': slice k of SPLIT, with the overlap, 2048x2048
            from PIL import Image
            base, k = name.split('#')
            img = nutexb.decode(nutexb.Nutexb(self.files[base]))
            w = img.shape[1]
            lo, hi = split_range(int(k))
            img = img[:, int(round(lo * w)):int(round(hi * w))]
            return np.asarray(Image.fromarray(img).resize((2048, 2048), Image.LANCZOS))
        return nutexb.decode(nutexb.Nutexb(self.files[name]))

    def nut(self, names):
        """NTWU, one mip, as Battlefield's single-mip textures: BC1 (opaque) or BC3, power-of-two
        sizes 64-2048. The block atlases are pixel art: 4x larger with nearest pixels, so each
        source pixel is one 4x4 block (exact in BC) and the game's linear filtering keeps it sharp."""
        from PIL import Image
        texs = []
        for n in names:
            img = self.image(n)
            if n.startswith('all_blocks'):
                img = img.repeat(4, 0).repeat(4, 1)
            h, w = img.shape[:2]
            w2, h2 = (min(2048, max(64, 1 << (v.bit_length() - 1))) for v in (w, h))
            if (w2, h2) != (w, h):
                img = np.asarray(Image.fromarray(img).resize((w2, h2), Image.NEAREST if n.startswith('all_blocks')
                                                             else Image.LANCZOS))
            fmt = 0x1A if n == SKY_GRADIENT else 0x31 if (img[..., 3] >= 250).all() else 0x33    # RGBA8: no banding
            texs.append((self.ids[n], fmt, img))
        return nut.write_ntwu(texs)


# material setups (flags, source / destination blend, alpha test, culling). The flags pick the
# shader: only flags Battlefield's melee models have, with the vertex layout they have them with.
# Blending and the alpha test are GPU states, not shaders (the unlit ones below add them to
# Battlefield's unlit 0xA2001001).
OPAQUE = (0xA4001041, 0, 0, 0, 0, 1029)             # stc_c_Ring_set (lit by the stage's lights)
CUTOUT = (0xA4011001, 0, 0, 518, 128, 1029)         # stc_b_shadow_gareki_set (also with culling 0)
BLEND = (0xA4001041, 1, 1, 0, 0, 1029)              # stc_s_ring_kusa_set
UNLIT = (0xA2001001, 0, 0, 0, 0, 1029)              # stc_a_surinuke_set (texture x vertex color)
UNLIT_CUTOUT = (0xA2001001, 0, 0, 518, 128, 1029)
UNLIT_BLEND = (0xA2001001, 1, 1, 0, 0, 1029)
CULLABLE = (CUTOUT, UNLIT_CUTOUT)                   # take Ultimate's culling; the others cull back faces


# a material's own fog (as Battlefield's far models have; without it the stage's default fog turns
# everything white by a few thousand units): NU_fogParams = start, end, strength at start / end
NO_FOG = ([0.0, 0.0, 0.0, 0.0], [36000.0, 42300.0, 0.0, 0.0])


def material(setup, tex_id, cull=1029, fog=NO_FOG):
    flags, src, dst, af, ref, c = setup
    m = nud.Material(flags, src, dst, af, ref, cull if setup in CULLABLE else c)
    m.textures.append(dict(hash=tex_id, map_mode=0, wrap_s=1, wrap_t=1, min_f=3, mag_f=2, mip=6, unk=0, unk2=0))
    m.props = [('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0]), ('NU_fogParams', list(fog[1])),
               ('NU_fogColor', list(fog[0])), ('NU_diffuseColor', [1.0, 1.0, 1.0, 1.0]),
               ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])]
    return m


def two_sided(idx):
    """a triangle list and its reverse (both faces drawn with back-face culling)"""
    t = np.asarray(idx).reshape(-1, 3)
    return np.concatenate([t, t[:, ::-1]]).reshape(-1)


def split_range(k):
    lo, hi = k / SPLIT - SPLIT_OVERLAP, (k + 1) / SPLIT + SPLIT_OVERLAP
    return max(lo, 0.0), min(hi, 1.0)


def split_wide(parts):
    """each part as SPLIT parts by its triangles' u (centroid), on the slices of its texture
    (Textures 'NAME#k'): the panorama at 2 x 1800 source pixels across instead of 2048"""
    out = []
    for p in parts:
        tri = p['idx'].reshape(-1, 3)
        cu = p['uv'][tri, 0].mean(1)
        for k in range(SPLIT):
            sel = tri[(cu >= k / SPLIT) & ((cu < (k + 1) / SPLIT) | (k == SPLIT - 1))]
            if not len(sel):
                continue
            used, idx = np.unique(sel, return_inverse=True)
            lo, hi = split_range(k)
            uv = p['uv'][used].copy()
            assert uv[:, 0].min() >= lo - 1e-6 and uv[:, 0].max() <= hi + 1e-6
            uv[:, 0] = (uv[:, 0] - lo) / (hi - lo)
            q = dict(p, pos=p['pos'][used], nrm=None if p['nrm'] is None else p['nrm'][used],
                     col=None if p['col'] is None else p['col'][used], uv=uv, idx=idx.reshape(-1),
                     textures=['%s#%d' % (p['textures'][0], k)] + p['textures'][1:], sub=100 * (p['sub'] + 1) + k)
            out.append(q)
    return out


def far_parts(setdir):
    """the panorama (split, see split_wide) and its fog layer (Ultimate's distance haze: a blended
    texture in front of it; 1% nearer, as it's drawn over the panorama there)"""
    parts = load_parts(setdir)
    fog = [dict(p, pos=p['pos'] * 0.99, uv=np.c_[p['uv'][:, 0], 1 - p['uv'][:, 1]],
                col=np.tile([0.5, 0.5, 0.5, 0.5 * FAR_FOG_ALPHA], (len(p['pos']), 1)))
           for p in parts if p['sub'] == 1]
    return split_wide([p for p in parts if p['sub'] == 0]) + fog


def to_nud(parts, tex, kind, sky=False):
    meshes = []
    for p in parts:
        if not p['textures'] or p['uv'] is None:
            continue
        tname = p['textures'][0]
        if tname.startswith('all_blocks-rgba_c2_add') and tname not in ('all_blocks-rgba_c2_add_vegetables',):
            tname = ATLAS
        uv = p['uv']
        col = p['col'].copy() if p['col'] is not None else np.full((len(p['pos']), 4), 0.502)
        if p['emissive']:
            # emission (the sky, the island's glowing blocks): Ultimate's color, as vertex colors
            tint = p['vec'].get('CustomVector3', np.ones(4))[:3] * p['vec'].get('CustomVector8', np.ones(4))[:3]
            col[:, :3] = (tint * col[:, :3] * 2) ** (1 / GAMMA) / 2
        elif kind == 'lit':
            if p['shader'].startswith('SFX_PBS_52'):
                # toon shaders (Texture11 a ToonGradationMap): colorSet1 drives their lighting, not color
                col[:, :3] = 0.5
            else:
                col[:, :3] = np.where(col[:, :3] < 0.5, 0.5 - (0.5 - col[:, :3]) * AO_KEEP, col[:, :3])
        col = np.clip(np.round(col * 253), 0, 255)
        if sky and p['label'] == 'sfx_sky_color':
            # the dome's color by elevation in a texture (vertex colors at 1.0), in case the unlit
            # shader doesn't take vertex colors
            d = p['pos'] / (np.linalg.norm(p['pos'], axis=1, keepdims=True) + 1e-9)
            t = np.clip(d[:, 1], 0, 1)
            rows = np.round((1 - t) * 255).astype(int)
            sky_rgb = np.zeros((256, 3))
            for c in range(3):
                n = np.bincount(rows, minlength=256)
                v = np.bincount(rows, col[:, c] / 127, minlength=256)
                have = n > 0
                sky_rgb[:, c] = np.interp(np.arange(256), np.where(have)[0], v[have] / n[have])
            tex.sky = sky_rgb
            tname = SKY_GRADIENT
            uv = np.c_[np.full(len(t), 0.5), 1 - t]
            col[:, :3] = 127
        tid = tex.id(tname)
        poly = nud.Polygon()
        poly.pos, poly.nrm, poly.uvs = p['pos'], p['nrm'], [uv]
        poly.col = col
        poly.idx = p['idx']
        atlas = tname.startswith('all_blocks')
        cull = 1029 if p['cull'] == 1029 else 0
        blend = p['blend'] and not atlas
        if kind == 'bg':
            # the backdrop and sky: Ultimate's are unlit (lighting baked in their textures)
            setup = UNLIT_BLEND if blend else UNLIT if sky else UNLIT_CUTOUT
        elif p['emissive']:
            setup = UNLIT_BLEND if blend else UNLIT_CUTOUT
        else:
            setup = BLEND if blend else CUTOUT if atlas else OPAQUE
        if cull == 0 and setup not in CULLABLE:
            poly.idx = two_sided(poly.idx)
        poly.materials = [material(setup, tid, cull)]
        if len(poly.pos) >= 0x10000:
            raise ValueError('%s: %d vertices' % (p['name'], len(poly.pos)))
        meshes.append(nud.Mesh('%s_%d' % (p['name'], p['sub']), [poly]))
    return meshes


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


def still_light(path, frame=DAY_FRAME):
    """Battlefield's animation/light.bin (its day / night cycle: night at frame 0, midday around
    945, sunset around 1400) with every frame set to `frame`'s, so the stage stays at midday, and
    the island's light set replaced by ISLAND_LIGHTS.
    Layout: 'LIGH', version, frame count, ?, the per-frame records' offset; five RGB tracks (3 bytes
    a frame) from the offsets at 0x14; then one fixed-size record a frame. Only values change."""
    d = bytearray(open(path, 'rb').read())
    magic, _, n, _, rec = struct.unpack('>4sIIII', d[:20])
    assert magic == b'LIGH'
    size = (len(d) - rec) // n
    assert rec + size * n == len(d)
    for o in struct.unpack('>5I', d[0x14:0x28]):
        d[o:o + 3 * n] = d[o + 3 * frame:o + 3 * frame + 3] * n
    r = bytearray(d[rec + size * frame:rec + size * (frame + 1)])
    # a record: a 116-byte block for the characters, then one a light set: 4 lights of 28 bytes
    # (enabled, direction, hue, saturation, value) and 4 more bytes
    o = 116 * (1 + ISLAND_LIGHT_SET)
    assert struct.unpack('>i', r[o:o + 4])[0] == 1
    for k, (on, v, h, sat, val) in enumerate(ISLAND_LIGHTS):
        r[o + 28 * k:o + 28 * k + 28] = struct.pack('>i6f', on, *v, h, sat, val)
    d[rec:] = bytes(r) * n
    return bytes(d)


def stage_params(path, values=CAMERA):
    """a Smash 4 typed param file (ff ff 00 00 header) with float values (by index) replaced"""
    d = bytearray(open(path, 'rb').read())
    assert d[:2] == b'\xff\xff'
    sizes = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4, 0x20: 4}
    o, i = 8, 0
    while o < len(d):
        t = d[o]
        if t == 8:
            n = 4 + struct.unpack('>I', d[o + 1:o + 5])[0]
        else:
            n = sizes[t]
        if i in values:
            assert t == 7, (i, t)
            d[o + 1:o + 5] = struct.pack('>f', values[i])
        o += 1 + n
        i += 1
    return bytes(d)


def cloud_motion(src, form, bone):
    """[CLOUD_PERIOD + 1] world offsets of a cloud bone from its rest pose, from Ultimate's sky
    animation (the last frame is the first again, so the animation loops)"""
    import ssbh_data_py as s
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    skel = s.skel_data.read_skel(d + '/model/far_common_set/model.nusktb')
    world = _world(skel)
    b = [x for x in skel.bones if x.name == bone][0]
    rest = np.array(b.transform, dtype=np.float64)[3, :3]
    parent = world[skel.bones[b.parent_index].name][:3, :3]
    anim = s.anim_data.read_anim(d + '/motion/far_common_set/far_common_set_00.nuanmb')
    track = [n for g in anim.groups for n in g.nodes if n.name == bone][0].tracks[0].values
    offs = [(np.array(track[f].translation) - rest) @ parent for f in range(CLOUD_PERIOD + 1)]
    assert np.abs(offs[-1] - offs[0]).max() < 1, (bone, offs[0], offs[-1])
    return offs


def write_clouds(model_dir, anim_dir, parts, tex, src, form):
    for bone, folder in CLOUD_SETS.items():
        layer = [p for p in parts if p['bone'] == bone]
        meshes = to_nud(layer, tex, 'bg', True)
        for m in meshes:
            m.bind, m.bone = 8, 0
        write_set('%s/%s' % (model_dir, folder), meshes, tex)
        h = omo.vbn_read('%s/%s/model.vbn' % (model_dir, folder))[0][2]
        path = '%s/%s/%s.omo' % (anim_dir, folder, folder)
        o = omo.Omo(open(path, 'rb').read())
        pos = [tuple(float(x) for x in v) for v in cloud_motion(src, form, bone)]
        o.frames = len(pos)
        o.nodes = []
        omo.set_node(o, h, pos, [(0.0, 0.0, 0.0, 1.0)] * len(pos), [(1.0, 1.0, 1.0)] * len(pos))
        open(path, 'wb').write(o.encode())


def torch_points(src, labels, row):
    t = ult_prc('%s/normal/param/pickel_world_visual.stdat' % src, labels)['torch_info_table'][row]
    return [np.array([t['x%d' % i], t['y%d' % i], t['z%d' % i]]) for i in range(t['count'])]


def write_torches(model_dir, anim_dir, points, tex, effect):
    """the torches' flames and smoke (see TORCH_SET) into the folder: model, skeleton, animation"""
    import zlib
    import bntx
    sprites = bntx.read_all(open(effect, 'rb').read())
    tex.extra['torch_flame'] = sprites['ef_pickelworld_fire00']
    smoke = sprites['ef_pickelworld_smoke00'][:, :32]                    # the sheet's first (largest) puff
    tex.extra['torch_smoke'] = smoke.repeat(2, 0).repeat(2, 1)
    bones = [('torch_root', -1)]
    meshes = []
    pos = {}
    frames = np.arange(TORCH_LOOP + 1)

    def quad(c, size, tname, col, setup, name):
        h = size / 2
        poly = nud.Polygon()
        poly.pos = c + np.array([[-h, -h, 0], [h, -h, 0], [h, h, 0], [-h, h, 0]])
        poly.nrm = np.tile([0.0, 0.0, 1.0], (4, 1))
        poly.col = np.tile(np.round(np.array(col) * 127), (4, 1))
        poly.uvs = [np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float64)]
        poly.idx = two_sided([0, 1, 2, 0, 2, 3])
        poly.materials = [material(setup, tex.id(tname))]
        bones.append((name, 0))
        meshes.append(nud.Mesh(name, [poly], bone=len(bones) - 1, bind=8))

    for i, c in enumerate(points):
        rng = np.random.default_rng(i)
        flame = c + np.array([0.0, FLAME_SIZE * 0.3, 0.5])
        quad(flame, FLAME_SIZE, 'torch_flame', [1, 1, 1, 1], UNLIT_CUTOUT, 'torch%d_flame' % i)
        ph = rng.uniform(0, 2 * np.pi, 2)
        s = 1 + 0.08 * np.sin(2 * np.pi * frames / 20 + ph[0]) + 0.05 * np.sin(2 * np.pi * frames / 12 + ph[1])
        pos[bones[-1][0]] = (flame, s, np.zeros((len(frames), 3)))
        start = int(rng.integers(SMOKE_LIFE))
        for k in range(2):
            base = c + np.array([0.0, FLAME_SIZE * 0.6, 0.4])
            quad(base, SMOKE_SIZE, 'torch_smoke', [SMOKE_GREY] * 3 + [SMOKE_ALPHA], UNLIT_BLEND, 'torch%d_smoke%d' % (i, k))
            u = ((frames + start + k * SMOKE_LIFE // 2) % SMOKE_LIFE) / SMOKE_LIFE
            rise = np.zeros((len(frames), 3))
            rise[:, 1] = SMOKE_RISE * u
            pos[bones[-1][0]] = (base, 1 - SMOKE_SHRINK * u, rise)
    bones = [(n, p, zlib.crc32(n.encode())) for n, p in bones]
    folder = '%s/%s' % (model_dir, TORCH_SET)
    write_set(folder, meshes, tex)
    open(folder + '/model.vbn', 'wb').write(omo.vbn_write(bones))
    path = '%s/%s/%s.omo' % (anim_dir, TORCH_SET, TORCH_SET)
    o = omo.Omo(open(path, 'rb').read())
    o.frames = len(frames)
    o.nodes = []
    for name, _p, h in bones[1:]:
        c, sc, up = pos[name]
        sc = np.asarray(sc, dtype=np.float64)
        t = c[None, :] * (1 - sc[:, None]) + up              # scale about the sprite's centre
        omo.set_node(o, h, [tuple(map(float, v)) for v in t], [(0.0, 0.0, 0.0, 1.0)] * len(frames),
                     [(float(x), float(x), float(x)) for x in sc])
    open(path, 'wb').write(o.encode())


# ---------------------------------------------------------------- stage
def build_form(src, base_dir, out_dir, form, biome, hazards, yamlvd, labels, effect=None):
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
        far = far_parts('%s/normal/model/%s' % (src, FAR[biome]))
        sky_src = '%s/normal/model/far_common_set' % src
    else:
        d = ult_lvd('%s/battle/param/pickel_world_end_00.lvd' % src, yamlvd)
        blocks = []
        near = load_parts('%s/battle/model/ring_endbattle_set' % src)
        far = far_parts('%s/battle/model/far_plains_set' % src)
        sky_src = '%s/battle/model/far_common_set' % src
    sky = [p for p in load_parts(sky_src) if p['label'] in SKY_LABELS]

    clouds = [p for p in sky if p['bone'] in CLOUD_SETS]
    sky = [p for p in sky if p['bone'] not in CLOUD_SETS]
    for name in sorted(os.listdir(model_dir)):
        if name in (RING_SET, FAR_SET, SKY_SET) or name in CLOUD_SETS.values() or effect and name == TORCH_SET:
            assert not os.path.exists('%s/%s/model.mta' % (model_dir, name)), name
        else:
            path = '%s/%s/model.nud' % (model_dir, name)
            data = nud.hidden(path)
            open(path, 'wb').write(data)
    for name, parts, kind, is_sky in ((RING_SET, near, 'lit', False), (FAR_SET, far, 'bg', False),
                                      (SKY_SET, sky, 'bg', True)):
        write_set('%s/%s' % (model_dir, name), to_nud(parts, tex, kind, is_sky), tex)
    write_clouds(model_dir, out_dir + '/animation', clouds, tex, src, form)
    if effect:
        row = BIOMES.index(biome) if form == 'melee' else TORCH_ROW_END
        write_torches(model_dir, out_dir + '/animation', torch_points(src, labels, row), tex, effect)

    light = out_dir + '/animation/light.bin'
    data = still_light(light)
    open(light, 'wb').write(data)
    prm = glob.glob(out_dir + '/param/*_stprm.bin')[0]
    data = stage_params(prm)
    open(prm, 'wb').write(data)

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
    ap.add_argument('--effect', help="Ultimate's effect/stage/pickel_world/ef_pickel_world.eff (torch flames / smoke)")
    a = ap.parse_args()
    for form in ('melee', 'end'):
        cols, blocks = build_form(a.src, '%s/%s/%s' % (a.base, form, a.name), '%s/stage/%s/%s' % (a.out, form, a.name),
                                  form, a.biome, a.hazards == 'on', a.yamlvd, a.labels, a.effect)
        print('%s: %d collisions (%d drop-through), %d blocks' % (form, len(cols), sum(c.flags[3] for c in cols), len(blocks)))


if __name__ == '__main__':
    main()
