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
import mta  # noqa: E402
import xmb  # noqa: E402

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
# Draw order (model.xmb drawing_order; Battlefield's go far to near: sky 0, moon 2, sun 4,
# background 5-9, near objects 12-18; blended models drawn in that order, ties by distance). The
# sky folder (dome, sun, Ultimate's haze ring) and the panorama were both 0 in v10 test 3, and
# the user saw the sky drawn over the panorama depending on the camera. The panorama's own haze
# layer gets a folder of its own, drawn after it (stc_b_shadow_gareki_set: no .mta).
FAR_ORDER = '2'
FOG_SET, FOG_ORDER = 'stc_b_shadow_gareki_set', '3'
GAMMA = 2.2                         # Ultimate's material colors are linear; Smash 4's vertex colors not
# (Ultimate's haze ring, fog_near, left out in v12: with the panorama solid it showed as a lighter
# band of sky over the hills, user)
SKY_LABELS = ('sfx_sky_color', 'sfx_cloud', 'sfx_cloud_bottom', 'zz_sun', 'zz_sun_core')

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
# (dyr_d_mid_front01_set: a plain one-bone Battlefield object. v9 used dyr_change_160_2_O_OBJ_O_HIR_set
# and froze, with its own skeleton or Battlefield's (user, v10 tests 1-2): that folder is Battlefield's
# 160-mesh building whose windows light up at night, likely by mesh, and ours had 8 meshes.)
TORCH_SET = 'dyr_d_mid_front01_set'
TORCH_ROW_END = 6
TORCH_LOOP = 300                    # frames; the flicker periods and the smoke's life divide it, it divides CYCLE
SMOKE_LIFE, SMOKE_RISE, SMOKE_SHRINK = 60, 7.0, 0.7
# each torch its own rhythm (v13 had every flame on the same two periods and every puff on the
# same life, only their phases apart: the user saw them all move in step, Ultimate's don't):
# periods and lives drawn from divisors of TORCH_LOOP, so the loop still closes
FLICKER_PERIODS = (20, 25, 30, 50, 60)
FLICKER2_PERIODS = (10, 12, 15)
SMOKE_LIVES = (50, 60, 75, 100)
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
# The island is drawn unlit (v11), its shading baked into the vertex colors: lit by the stage
# (0xA4001041, which has no fog parameters of its own) it came out washed out in game (user's
# screenshot: hay's blue channel ~0 -> ~100, grey stone beige), the stage's light and haze added
# on top. Minecraft-style face shading from Ultimate's sun (travel direction as ISLAND_LIGHTS'):
# BAKE_AMBIENT + BAKE_SUN x the face's share of it (top 1.22, front 0.95, sides 0.86 / 0.75,
# bottom 0.75), times Ultimate's corner shading (colorSet1, AO_KEEP).
BAKE_SUN_DIR = np.array([-0.204, -0.903, -0.379])
# (v11: 0.6 + 0.42, top 0.98 ... bottom 0.6, "a bit too dark", user; v12 x1.25)
BAKE_AMBIENT, BAKE_SUN = 0.75, 0.52
# Ultimate grades the finished picture through the stage's LUT (lut/color_grading_lut.nutexb,
# 16^3: near the identity, saturation +0.07 on the blocks' colors); v12 puts every texture through
# it (an approximation: Ultimate grades the lit result), with GRADE_SATURATION more on top
# (v11 next to Ultimate in the user's screenshots: the hay's and the background's colors weaker)
GRADE_SATURATION = 1.1
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


# Minecraft's corner shading for the breakable blocks: Ultimate's island mesh has it in colorSet1,
# its breakable blocks don't (Ultimate shades them at run time, ao_depth_table 200 / 128 / 64 / 0),
# so ours were lighter than the island around them (user). A face corner's level counts the solid
# cells beside it on the face's open side (Minecraft's smooth lighting: two sides, or the sides and
# the corner); the colorSet1 a level, as the island mesh has them (medians of its vertices by level,
# computed the same way): 3 (open) 0.5, 2 0.31, 1 0.18, 0 0.15
AO_LEVELS = (0.15, 0.18, 0.31, 0.5)


def _cell(p):
    """the 10-unit cell of a point (breakable_blocks' cells: x and y from 10 n, z centred on 10 n)"""
    return int(np.floor(p[0] / 10 + 1e-6)), int(np.floor(p[1] / 10 + 1e-6)), int(np.round(p[2] / 10))


def solid_cells(parts):
    """the cells behind the parts' axis-aligned faces (the island is made of 10-unit blocks)"""
    out = set()
    for p in parts:
        if p['nrm'] is None:
            continue
        for t in p['idx'].reshape(-1, 3):
            n = p['nrm'][t].mean(0)
            a = np.argmax(np.abs(n))
            if abs(n[a]) < 0.95:
                continue
            d = np.zeros(3)
            d[a] = np.sign(n[a])
            out.add(_cell(p['pos'][t].mean(0) - d * 2.5))
    return out


def block_ao(p, solid):
    """the part with colorSet1 from its face corners' levels (AO_LEVELS)"""
    col = np.full((len(p['pos']), 4), 0.502) if p['col'] is None else p['col'].copy()
    for t in p['idx'].reshape(-1, 3):
        n = p['nrm'][t].mean(0)
        a = np.argmax(np.abs(n))
        if abs(n[a]) < 0.95:
            continue
        c = p['pos'][t].mean(0)
        d = np.zeros(3, int)
        d[a] = int(np.sign(n[a]))
        layer = np.array(_cell(c + d * 2.5))
        ax = [i for i in range(3) if i != a]
        for v in t:
            t1 = np.zeros(3, int)
            t2 = np.zeros(3, int)
            t1[ax[0]] = 1 if p['pos'][v][ax[0]] > c[ax[0]] else -1
            t2[ax[1]] = 1 if p['pos'][v][ax[1]] > c[ax[1]] else -1
            s1, s2 = tuple(layer + t1) in solid, tuple(layer + t2) in solid
            corner = tuple(layer + t1 + t2) in solid
            col[v, :3] = AO_LEVELS[0 if s1 and s2 else 3 - (s1 + s2 + corner)]
    return dict(p, col=col)


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
def pixel_art(name):
    """textures drawn 4x larger with nearest pixels, so each source pixel is one 4x4 BC block
    (exact) and stays sharp under linear filtering: the block atlases and the mobs' skins
    (pickel_guestg_col, pickel_plains_col, ...: 128 pixels, faces of a few; at their own size BC
    and filtering lost the sheep's eyes and the villagers' faces in game, user)"""
    return name.startswith('all_blocks') or name.startswith('pickel_') and not name.startswith('pickel_world')


# Ultimate's textures drawn with One / OneMinusSourceAlpha (color already times alpha): the panoramas
PREMULTIPLIED = {'far_%s_day_low_col' % k for k in 'abcdef'}


def premultiply(img):
    out = img.astype(np.float64)
    out[..., :3] *= out[..., 3:] / 255
    return np.round(out).astype(np.uint8)


def unpremultiply(img):
    out = img.astype(np.float64)
    a = out[..., 3:] / 255
    out[..., :3] = np.where(a > 0, out[..., :3] / np.maximum(a, 1e-6), 0)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def bleed(img, steps=4):
    """the color of the texels with any alpha spread into the fully transparent ones next to
    them, a texel a step: filtering mixes those in at the edges, and Ultimate's have them white
    (the grass's white outline in game, user)"""
    rgb = img[..., :3].astype(np.float64)
    have = img[..., 3] > 0
    if have.all() or not have.any():
        return img
    for _ in range(steps):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(have.shape)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            m = np.roll(have, (dy, dx), (0, 1))
            acc += np.roll(rgb, (dy, dx), (0, 1)) * m[..., None]
            cnt += m
        grow = ~have & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        have = have | grow
    out = img.copy()
    out[..., :3] = np.round(rgb).astype(np.uint8)
    out[..., 3] = img[..., 3]
    return out


def graded(img, lut):
    """RGBA through Ultimate's grading LUT, then GRADE_SATURATION (about the pixel's grey)"""
    out = img.copy()
    rgb = nutexb.apply_lut(lut, img[..., :3]).astype(np.float64)
    grey = rgb.mean(-1, keepdims=True)
    out[..., :3] = np.clip(np.round(grey + (rgb - grey) * GRADE_SATURATION), 0, 255).astype(np.uint8)
    return out


class Textures:
    def __init__(self, src, lut=None):
        self.src = src
        self.lut = lut                      # Ultimate's grading LUT (nutexb.lut3d) or None
        self.premultiplied_out = set()      # textures written with color x alpha (for blend one / 1 - alpha)
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
        if '#' in name:                     # 'NAME#k': slice k of SPLIT, with the overlap, unscaled (split_wide)
            base, k = name.split('#')
            img = nutexb.decode(nutexb.Nutexb(self.files[base]))
            w = img.shape[1]
            lo, hi = split_range(int(k))
            img = img[:, int(round(lo * w)):int(round(hi * w))]
            out = np.zeros((SLICE, SLICE, 4), np.uint8)
            h, sw = img.shape[:2]
            out[:h, :sw] = img
            out[h:, :sw] = img[-1]              # the edges repeated: filtering at them stays solid
            out[:, sw:] = out[:, sw - 1:sw]
            return out
        return nutexb.decode(nutexb.Nutexb(self.files[name]))

    def nut(self, names):
        """NTWU, one mip, as Battlefield's single-mip textures: BC1 (opaque) or BC3, power-of-two
        sizes 64-2048; pixel art (see pixel_art) 4x larger with nearest pixels."""
        from PIL import Image
        texs = []
        for n in names:
            img = self.image(n)
            h, w = img.shape[:2]
            if pixel_art(n):
                # at least 4x, up to a power of two, nearest: no source pixel dropped (the crops'
                # 164 x 72 went 4x to 656 and then down to 512, losing columns)
                w2, h2 = (min(2048, 1 << (4 * v - 1).bit_length()) for v in (w, h))
            else:
                w2, h2 = (min(2048, max(64, 1 << (v.bit_length() - 1))) for v in (w, h))
            alpha = (img[..., 3] < 255).any()
            if alpha and not n.split('#')[0] in PREMULTIPLIED:
                img = premultiply(img)
            if (w2, h2) != (w, h):
                img = np.asarray(Image.fromarray(img).resize((w2, h2), Image.NEAREST if pixel_art(n) else Image.LANCZOS))
            if alpha:
                img = unpremultiply(img)
            if self.lut is not None:
                img = graded(img, self.lut)
            if alpha:
                img = bleed(img)
            if n in self.premultiplied_out:
                img = premultiply(img)
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


# Bone-bound materials as Battlefield's own (flags, blend, alpha test, culling, properties, sampler):
# v9 / v10 tests 1, 2 and 5 froze with the torches' unlit 0xA2001001 alpha-tested / blended on
# bones, which no Battlefield model has. Flames: dyr_g_bgfar_set's (0xA3C01081, blend 1 / 2:
# source alpha, one, so additive); smoke: dyr_f_BG_far2_set_set's (0xA4011001, blend 5 / 1: source
# alpha, one minus source alpha (Smash Forge's NudEnums), so plain alpha blending; the smoke's
# texture is written premultiplied all the same, which only darkens its thin edges), its fog
# strengths 0. Glow (the sun and the moon): the flames' shader, which fades with its gain's alpha
# (Battlefield's moon), alpha-blended (5 / 1) as Ultimate's (colour x alpha over the sky). All with
# an alpha test (greater than 0) as Battlefield's blended materials: without it a flame's whole quad
# wrote depth, hiding the torch light (torch_light, drawn after) behind it, a dark square that grew
# with the flame (user).
BF_FLAME = (0xA3C01081, 1, 2, 516, 0, 1029,
            [('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0]), ('NU_finalColorGain', [1.0, 1.0, 1.0, 1.0]),
             ('NU_diffuseColor', [1.0, 1.0, 1.0, 1.0]), ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])], 3)
BF_SMOKE = (0xA4011001, 5, 1, 516, 0, 1029,
            [('NU_colorSamplerUV', [1.0, 1.0, 0.0, 0.0]), ('NU_fresnelParams', [1.0, 1.0, 0.0, 1.0]),
             ('NU_fresnelColor', [0.0, 0.0, 0.0, 0.0]), ('NU_fogParams', [300.0, 9000.0, 0.0, 0.0]),
             ('NU_diffuseColor', [1.0, 1.0, 1.0, 0.0]), ('NU_fogColor', [0.43, 0.712, 0.994, 0.0]),
             ('NU_materialHash', [0.0, 0.0, 0.0, 0.0])], 1)
BF_GLOW = (BF_FLAME[0], 5, 1) + BF_FLAME[3:]
# the stars: the flames' material, their texture repeated (UVs 0-4 and -3-1; the flames' clamp
# drew their edge texels as long streaks, user)
BF_STARS = BF_FLAME[:7] + (1,)


def bf_material(spec, tex_id):
    flags, src, dst, af, ref, cull, props, wrap = spec
    m = nud.Material(flags, src, dst, af, ref, cull)
    m.textures.append(dict(hash=tex_id, map_mode=0, wrap_s=wrap, wrap_t=wrap, min_f=3, mag_f=2, mip=6, unk=0, unk2=0))
    m.props = [(n, list(v)) for n, v in props]
    return m


def two_sided(idx):
    """a triangle list and its reverse (both faces drawn with back-face culling)"""
    t = np.asarray(idx).reshape(-1, 3)
    return np.concatenate([t, t[:, ::-1]]).reshape(-1)


def split_range(k):
    lo, hi = k / SPLIT - SPLIT_OVERLAP, (k + 1) / SPLIT + SPLIT_OVERLAP
    return max(lo, 0.0), min(hi, 1.0)


SLICE = 2048                        # a panorama slice's texture (its source pixels unscaled in its corner)


def split_wide(parts, size):
    """each part as SPLIT parts by its triangles' u (centroid), on the slices of its texture
    (Textures 'NAME#k'): the panorama at 2 x 1800 source pixels across instead of 2048. size: the
    texture's (w, h). v12 scaled each slice to 2048 x 2048 (the user saw the skyline's cutout
    edge ragged, stray pixels over it); v13c keeps its pixels as they are, in the slice texture's
    top left corner (UVs scaled to it)"""
    w, h = size
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
            sw = int(round(hi * w)) - int(round(lo * w))
            uv[:, 0] = (uv[:, 0] - lo) / (hi - lo) * sw / SLICE
            uv[:, 1] *= h / SLICE
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
    pano = [p for p in parts if p['sub'] == 0]
    t = nutexb.Nutexb('%s/%s.nutexb' % (setdir, pano[0]['textures'][0]))
    return split_wide(pano, (t.w, t.h)), fog


def to_nud(parts, tex, kind, sky=False, cutout=False):
    """kind 'lit' (the island: unlit with baked shading, see BAKE_SUN_DIR) or 'bg' (unlit as
    Ultimate's); cutout: alpha-tested even where Ultimate blends (the panorama, so it's drawn with
    the solid models and hides the sky and clouds behind it)"""
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
            if p['nrm'] is not None:
                n = p['nrm'] / (np.linalg.norm(p['nrm'], axis=1, keepdims=True) + 1e-9)
                col[:, :3] *= (BAKE_AMBIENT + BAKE_SUN * np.clip(-n @ BAKE_SUN_DIR, 0, None))[:, None]
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
        blend = p['blend'] and not atlas and not cutout
        if kind == 'bg':
            # the backdrop and sky: Ultimate's are unlit (lighting baked in their textures)
            setup = UNLIT_BLEND if blend else UNLIT if sky else UNLIT_CUTOUT
        elif p['emissive']:
            setup = UNLIT_BLEND if blend else UNLIT_CUTOUT
        else:
            setup = UNLIT_BLEND if blend else UNLIT_CUTOUT if atlas else UNLIT
        if cull == 0 and setup not in CULLABLE:
            poly.idx = two_sided(poly.idx)
        poly.materials = [material(setup, tid, cull)]
        if len(poly.pos) >= 0x10000:
            raise ValueError('%s: %d vertices' % (p['name'], len(poly.pos)))
        meshes.append(nud.Mesh('%s_%d' % (p['name'], p['sub']), [poly]))
    return meshes


def write_set(outdir, meshes, tex, curves=None):
    """the folder's model.nud / .nut; with curves ({kind: [CYCLE + 1, 4]}), each mesh with a `gain`
    kind gets that kind's NU_materialHash and the folder a model.mta animating its
    NU_finalColorGain (any other model.mta removed)"""
    os.makedirs(outdir, exist_ok=True)
    kinds = []
    for m in meshes if curves else ():
        k = getattr(m, 'gain', None)
        if k not in curves:
            continue
        h = struct.unpack('>f', struct.pack('>I', gain_hash(k)))[0]
        for p in m.polygons:
            for mat in p.materials:
                mat.props = [(n, [h, 0.0, 0.0, 0.0] if n == 'NU_materialHash' else v) for n, v in mat.props]
                if GAIN_FLAGS and mat.flags == 0xA2001001 and not (ISLAND_FLAGS and k == 'island'
                                                                   and outdir.endswith(RING_SET)):
                    mat.flags = GAIN_FLAGS
                if not any(n == 'NU_finalColorGain' for n, _v in mat.props):
                    # as every material Battlefield animates on a bone has it (v15b: without it the
                    # doors on their bones seemed to stay at full day brightness at night, user)
                    mat.props.insert(1, ('NU_finalColorGain', [1.0, 1.0, 1.0, 1.0]))
        if k not in kinds:
            kinds.append(k)
    if os.path.exists(outdir + '/model.mta'):
        os.remove(outdir + '/model.mta')
    if kinds:
        open(outdir + '/model.mta', 'wb').write(mta.write(CYCLE + 1, [
            dict(name='mcw_%s' % k, hash=gain_hash(k), props=[dict(name='NU_finalColorGain', values=curves[k].tolist())])
            for k in kinds]))
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


def cloud_motion(src, form, bone, frames=CLOUD_PERIOD + 1):
    """[frames] world offsets of a cloud bone from its rest pose, from Ultimate's sky animation
    (CLOUD_PERIOD + 1, or CYCLE + 1: its whole length, two of its loops; the last frame is the first
    again, so the animation loops)"""
    import ssbh_data_py as s
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    skel = s.skel_data.read_skel(d + '/model/far_common_set/model.nusktb')
    world = _world(skel)
    b = [x for x in skel.bones if x.name == bone][0]
    rest = np.array(b.transform, dtype=np.float64)[3, :3]
    parent = world[skel.bones[b.parent_index].name][:3, :3]
    anim = s.anim_data.read_anim(d + '/motion/far_common_set/far_common_set_00.nuanmb')
    track = [n for g in anim.groups for n in g.nodes if n.name == bone][0].tracks[0].values
    offs = [(np.array(track[f].translation) - rest) @ parent for f in range(frames)]
    assert np.abs(offs[-1] - offs[0]).max() < 1, (bone, offs[0], offs[-1])
    return offs


def write_clouds(model_dir, anim_dir, parts, tex, src, form, moving=True, curves=None):
    """moving=False: the layers unbound, where Ultimate's animation starts (the folder's bone and
    animation as for moving ones, but no mesh follows them)"""
    for bone, folder in CLOUD_SETS.items():
        layer = [p for p in parts if p['bone'] == bone]
        meshes = to_nud(layer, tex, 'bg', True)
        for m in meshes:
            m.gain = 'cloud'
            if moving:
                m.bind, m.bone = 8, 0
        write_set('%s/%s' % (model_dir, folder), meshes, tex, curves)
        h = omo.vbn_read('%s/%s/model.vbn' % (model_dir, folder))[0][2]
        path = '%s/%s/%s.omo' % (anim_dir, folder, folder)
        o = omo.Omo(open(path, 'rb').read())
        pos = [tuple(float(x) for x in v) for v in cloud_motion(src, form, bone, CYCLE + 1 if curves else CLOUD_PERIOD + 1)]
        o.frames = len(pos)
        o.nodes = []
        omo.set_node(o, h, pos, [(0.0, 0.0, 0.0, 1.0)] * len(pos), [(1.0, 1.0, 1.0)] * len(pos))
        open(path, 'wb').write(o.encode())


def torch_points(src, labels, row):
    t = ult_prc('%s/normal/param/pickel_world_visual.stdat' % src, labels)['torch_info_table'][row]
    return [np.array([t['x%d' % i], t['y%d' % i], t['z%d' % i]]) for i in range(t['count'])]


# the torches' light at night (Ultimate's point lights; our island is unlit): the island's faces
# within TORCH_LIGHT_RANGE of a torch drawn again, added (Battlefield's unbound 0xA3C01081, blend
# 5 / 2: source alpha, one), their texture times a warm light in the vertex colours (per corner,
# as Minecraft's smooth lighting: a quarter from everywhere, the rest by how much the face looks
# at the torch), the curve 'torchlight' fading it in as the island darkens
TORCH_LIGHT_RANGE, TORCH_LIGHT, TORCH_LIGHT_MAX = 45.0, 1.8, 0.8     # the most: 1.6 blew out Omega's lamp post (four torches on it, user)
TORCH_LIGHT_COLOR = (1.0, 0.7, 0.4)
DOOR_LIGHT_MAX = 0.35               # the doors' corners are next to their torches: at the cap, far too bright (user)
TORCH_LIGHT_LIFT = 0.05             # the copy this far out along its normals, in front of the island


def torch_light(meshes, points, cap=None):
    """additive copies of meshes' triangles lit by the torches at points, each with gain 'torchlight';
    cap: the most light (TORCH_LIGHT_MAX)"""
    out = []
    pts = np.array(points, dtype=np.float64)
    for m in meshes:
        polys = []
        for p in m.polygons:
            if p.nrm is None:
                continue
            n = p.nrm / (np.linalg.norm(p.nrm, axis=1, keepdims=True) + 1e-9)
            light = np.zeros(len(p.pos))
            for t in pts:
                v = t - p.pos
                d = np.linalg.norm(v, axis=1) + 1e-9
                face = np.clip(np.einsum('ij,ij->i', n, v) / d, 0, 1)
                light += TORCH_LIGHT * np.clip(1 - d / TORCH_LIGHT_RANGE, 0, 1) ** 2 * (0.25 + 0.75 * face)
            light = np.minimum(light, cap or TORCH_LIGHT_MAX)
            tri = np.asarray(p.idx).reshape(-1, 3)
            tri = tri[light[tri].max(1) > 0.02]
            if not len(tri):
                continue
            keep, idx = np.unique(tri, return_inverse=True)
            q = nud.Polygon()
            q.pos = p.pos[keep] + n[keep] * TORCH_LIGHT_LIFT
            q.nrm = p.nrm[keep]
            q.uvs = [uv[keep] for uv in p.uvs]
            q.col = np.c_[np.round(light[keep, None] * np.array(TORCH_LIGHT_COLOR) * 128), np.full(len(keep), 128)]
            q.idx = idx.reshape(-1)
            q.materials = [added(p.materials[0])]
            polys.append(q)
        if polys:
            lit = nud.Mesh(m.name + '_torchlight', polys, bone=m.bone, bind=m.bind)
            lit.gain = 'torchlight'
            out.append(lit)
    return out


def added(mat):
    """mat's texture, drawn added (Battlefield's 0xA3C01081, blend 5 / 2, bound or not)"""
    m = nud.Material(BF_FLAME[0], 5, 2, 516, 0, mat.cull)
    m.textures = [dict(t) for t in mat.textures]
    m.props = [(n, list(v)) for n, v in BF_FLAME[6]]
    return m


# the backdrop's own lights at night: Ultimate's night panorama has torch-lit patches and lava
# glowing (user), which our night panorama (the day one darkened, see daynight_curves) lacks.
# What the night texture has over the darkened day one, softened to PANO_GLOW_SIZE, drawn added
# over the panorama's triangles it reaches, faded in with Ultimate's day / night blend ('pano_glow')
PANO_GLOW_SIZE = (1024, 512)
PANO_GLOW_MIN = 6                   # the least texel (0-255) a triangle must reach to be drawn again


def pano_glow(setdir, tex):
    """the panorama's glow parts (texture 'pano_glow')"""
    from PIL import Image, ImageFilter
    parts = [p for p in load_parts(setdir) if p['sub'] == 0]
    path = '%s/%s.nutexb' % (setdir, parts[0]['textures'][0])
    a = nutexb.decode(nutexb.Nutexb(path)).astype(np.float64)
    b = nutexb.decode(nutexb.Nutexb(path.replace('_day_', '_night_'))).astype(np.float64)
    m = a[..., 3] > 250
    k = b[m][:, :3].mean(0) / a[m][:, :3].mean(0)
    glow = np.clip(b[..., :3] - a[..., :3] * k, 0, 255) * m[..., None]
    small = Image.fromarray(np.round(glow).astype(np.uint8)).resize(PANO_GLOW_SIZE, Image.BOX)
    img = np.dstack([np.asarray(small), np.full(PANO_GLOW_SIZE[::-1], 255, np.uint8)])
    tex.extra['pano_glow'] = img
    reach = np.asarray(small.convert('L').filter(ImageFilter.MaxFilter(9)))
    h, w = reach.shape
    out = []
    for p in parts:
        tri = p['idx'].reshape(-1, 3)
        uv = p['uv'][tri]                                   # [t, 3, 2]
        pts = np.concatenate([uv, uv.mean(1, keepdims=True)], 1)
        x = np.clip((pts[..., 0] * w).astype(int), 0, w - 1)
        y = np.clip((pts[..., 1] * h).astype(int), 0, h - 1)
        sel = tri[reach[y, x].max(1) >= PANO_GLOW_MIN]
        if not len(sel):
            continue
        used, idx = np.unique(sel, return_inverse=True)
        out.append(dict(p, pos=p['pos'][used] * 0.995, nrm=None if p['nrm'] is None else p['nrm'][used],
                        col=np.full((len(used), 4), 0.502), uv=p['uv'][used], idx=idx.reshape(-1),
                        textures=['pano_glow'], emissive=False, blend=False, sub=200))
    return out


def torch_meshes(points, tex, effect, animated=True):
    """the torches' flames (and, animated, smoke) as meshes. animated: each on its own bone
    (bind 8, bone n; made skeleton [(name, parent)], bone 0 the root) with its motion
    {bone: (sprite centre, scale a frame, offset a frame)}, Battlefield's bone-bound materials
    (BF_FLAME, BF_SMOKE); still: flames only, unbound, the island's alpha-tested unlit setup"""
    import bntx
    sprites = bntx.read_all(open(effect, 'rb').read())
    tex.extra['torch_flame'] = sprites['ef_pickelworld_fire00']
    smoke = sprites['ef_pickelworld_smoke00'][:, :32]                    # the sheet's first (largest) puff
    smoke = smoke.repeat(2, 0).repeat(2, 1).astype(np.float64)
    if animated:                            # grey and opacity in the texture, written premultiplied for BF_SMOKE
        smoke[..., 3] *= SMOKE_ALPHA
        smoke[..., :3] *= SMOKE_GREY
        tex.premultiplied_out.add('torch_smoke')
    tex.extra['torch_smoke'] = np.round(smoke).astype(np.uint8)
    bones = [('torch_root', -1)]
    meshes = []
    motion = {}
    frames = np.arange(TORCH_LOOP + 1)

    def quad(c, size, tname, col, setup, name, spec=None):
        h = size / 2
        poly = nud.Polygon()
        poly.pos = c + np.array([[-h, -h, 0], [h, -h, 0], [h, h, 0], [-h, h, 0]])
        poly.nrm = np.tile([0.0, 0.0, 1.0], (4, 1))
        poly.col = np.tile(np.round(np.array(col) * 127), (4, 1))
        poly.uvs = [np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float64)]
        poly.idx = two_sided([0, 1, 2, 0, 2, 3])
        poly.materials = [bf_material(spec, tex.id(tname)) if animated else material(setup, tex.id(tname))]
        if animated:
            bones.append((name, 0))
            meshes.append(nud.Mesh(name, [poly], bone=len(bones) - 1, bind=8))
        else:
            meshes.append(nud.Mesh(name, [poly]))
        meshes[-1].gain = 'island' if 'smoke' in name else None     # the flames keep their light

    for i, c in enumerate(points):
        rng = np.random.default_rng(i)
        flame = c + np.array([0.0, FLAME_SIZE * 0.3, 0.5])
        quad(flame, FLAME_SIZE, 'torch_flame', [1, 1, 1, 1], UNLIT_CUTOUT, 'torch%d_flame' % i, BF_FLAME)
        if not animated:
            continue
        ph = rng.uniform(0, 2 * np.pi, 2)
        p1, p2 = rng.choice(FLICKER_PERIODS), rng.choice(FLICKER2_PERIODS)
        a1, a2 = rng.uniform(0.05, 0.1), rng.uniform(0.03, 0.06)
        s = 1 + a1 * np.sin(2 * np.pi * frames / p1 + ph[0]) + a2 * np.sin(2 * np.pi * frames / p2 + ph[1])
        motion[bones[-1][0]] = (flame, s, np.zeros((len(frames), 3)))
        life = int(rng.choice(SMOKE_LIVES))
        start = int(rng.integers(life))
        rise_to = SMOKE_RISE * rng.uniform(0.8, 1.2)
        for k in range(2):
            base = c + np.array([0.0, FLAME_SIZE * 0.6, 0.4])
            quad(base, SMOKE_SIZE, 'torch_smoke', [1, 1, 1, 1], UNLIT_BLEND, 'torch%d_smoke%d' % (i, k), BF_SMOKE)
            u = ((frames + start + k * life // 2) % life) / life
            rise = np.zeros((len(frames), 3))
            rise[:, 1] = rise_to * u
            motion[bones[-1][0]] = (base, 1 - SMOKE_SHRINK * u, rise)
    return meshes, bones, motion


def torch_tracks(bones, motion, frames):
    """the torches' {bone: (positions, None, scales)} over frames (their TORCH_LOOP repeated)"""
    out = {}
    f = np.arange(frames) % TORCH_LOOP
    for name, _p in bones[1:]:
        c, sc, up = motion[name]
        sc = np.asarray(sc, dtype=np.float64)[f]
        t = c[None, :] * (1 - sc[:, None]) + np.asarray(up)[f]       # scale about the sprite's centre
        out[name] = (t, None, np.repeat(sc[:, None], 3, 1))
    return out


def write_rig(model_dir, anim_dir, folder, meshes, bones, tracks, frames, tex, curves=None):
    """a dyr_ folder with a made skeleton: meshes (bind 8, bone n), bones [(name, parent)] (bone 0
    a still root), tracks {bone: (positions [F, 3], quaternions [F, 4] x y z w or None, scales
    [F, 3] or None)} over frames; NUD header 0x0E = the highest bone (nud.write)"""
    import zlib
    bones = [(n, p, zlib.crc32(n.encode())) for n, p in bones]
    write_set('%s/%s' % (model_dir, folder), meshes, tex, curves)
    open('%s/%s/model.vbn' % (model_dir, folder), 'wb').write(omo.vbn_write(bones))
    path = '%s/%s/%s.omo' % (anim_dir, folder, folder)
    o = omo.Omo(open(path, 'rb').read())
    o.frames = frames
    o.nodes = []
    omo.set_node(o, bones[0][2], [(0.0, 0.0, 0.0)] * frames, [(0.0, 0.0, 0.0, 1.0)] * frames, [(1.0, 1.0, 1.0)] * frames)
    for name, _p, h in bones[1:]:
        pos, rot, scl = tracks[name]
        omo.set_node(o, h, [tuple(map(float, v)) for v in pos],
                     [tuple(map(float, q)) for q in rot] if rot is not None else [(0.0, 0.0, 0.0, 1.0)] * frames,
                     [tuple(map(float, v)) for v in scl] if scl is not None else [(1.0, 1.0, 1.0)] * frames)
    open(path, 'wb').write(o.encode())


# Ultimate's mobs and villagers (model/ch_pickel_*_set: rigid parts, each vertex on one bone;
# motion/ch_pickel_*_set: the stage's own paths, in stage coordinates on the Hip bone, so the models
# stay at the origin). Each part becomes a mesh on a bone of a made skeleton, its animation the
# part's motion from its bind pose: A_f x B^-1 (column vectors, as omo.trs). Day only (the night's
# monsters and the villagers' meeting / return / sleep, which take them indoors, left out).
VILLAGERS = {'plains': ('plains_farmer', 'plains_butcher'),
             'snowytundra': ('snowytundra_farmer', 'snowytundra_butcher')}
# their day and night over Ultimate's cycle (CYCLE, 9000 frames): free1, work and free2 from and
# back to their spot (1200 frames each), to the meeting at dusk (600), home (1200), sleep indoors
# (3600: still inside until it walks back out to the spot at dawn); with the torches (TORCH_LOOP
# divides CYCLE) in TORCH_SET. Without the cycle (--daynight off): the day part looped (7200).
VILLAGER_DAY = ('free1', 'work', 'free2', 'free3', 'work', 'free4')
VILLAGER_CYCLE = (('free1', 1200), ('work', 1200), ('free2', 1200), ('meeting', 600), ('return', 1200),
                  ('sleep', 3600))
VILLAGER_FRAMES = 1200
# animals: two of a kind (Ultimate picks sheep / chicken / cow 30 / 30 / 30), playing wait1 and
# wait2 (4200 frames each, start = end), in their own folder; with the cycle, gone from Ultimate's
# frame_of_monster (4200, when its monsters come) to the end of the night (scaled to nothing)
ANIMAL_SET = 'dyr_e_mid_left01_set'
ANIMAL_FRAMES = 4200
# Omega (the battle folder's ring_endbattle_set): its motions are the normal form's, but its island
# is narrower and has only the butcher's house (the middle one). The farmer's spot is a block above
# its ground and his house isn't there (he floated, user), so he and his door are left out; the
# animals' pen walked off its edge, so they're moved by END_ANIMAL_SHIFT (blocks of 10), the least
# shift that keeps every frame of all three animals' paths on its ground
END_VILLAGERS = ('plains_butcher',)
END_ANIMAL_SHIFT = (10.0, 0.0, 20.0)


def mob_parts(setdir):
    """load_parts split by bone: [(bone name, part)]"""
    import ssbh_data_py as s
    mesh = s.mesh_data.read_mesh(setdir + '/model.numshb')
    out = []
    for p, o in zip(load_parts(setdir), mesh.objects):
        vb = np.full(len(p['pos']), -1)
        names = []
        for bi in o.bone_influences:
            names.append(bi.bone_name)
            for vw in bi.vertex_weights:
                if vw.vertex_weight > 0.5:
                    vb[vw.vertex_index] = len(names) - 1
        tri = p['idx'].reshape(-1, 3)
        tb = vb[tri]
        assert (tb >= 0).all() and (tb == tb[:, :1]).all(), 'not rigid: ' + setdir
        for k, name in enumerate(names):
            t = tri[tb[:, 0] == k]
            if not len(t):
                continue
            used, idx = np.unique(t.reshape(-1), return_inverse=True)
            q = dict(p, pos=p['pos'][used], nrm=None if p['nrm'] is None else p['nrm'][used],
                     col=None if p['col'] is None else p['col'][used], uv=p['uv'][used], idx=idx)
            out.append((name, q))
    return out


def mob_motion(setdir, anim_paths, frames, bones):
    """{bone: (positions, quaternions, scales)} over frames: the anims' frames one after another"""
    import ssbh_data_py as s
    skel = s.skel_data.read_skel(setdir + '/model.nusktb')
    bind = {k: np.linalg.inv(m.T) for k, m in _world(skel).items()}
    rest = {b.name: np.array(b.transform, dtype=np.float64).T for b in skel.bones}
    seq = []
    for path, n in anim_paths:              # n: a frame count from 0, or the frames to take
        a = s.anim_data.read_anim(path)
        nodes = {x.name: x.tracks[0].values for g in a.groups if g.group_type.name == 'Transform' for x in g.nodes}
        seq += [(nodes, f) for f in (range(n) if isinstance(n, int) else n)]
    assert len(seq) >= frames
    out = {b: ([], [], []) for b in bones}
    for nodes, f in seq[:frames]:
        world = {}
        for b in skel.bones:
            v = nodes.get(b.name)
            if v is not None:
                v = v[min(f, len(v) - 1)]
                local = np.array(omo.trs(v.translation, v.rotation, v.scale), dtype=np.float64)
            else:
                local = rest[b.name]
            if b.parent_index is not None and b.parent_index >= 0:
                local = world[skel.bones[b.parent_index].name] @ local
            world[b.name] = local
        for b in bones:
            m = world[b] @ bind[b]
            p, q, sc = omo.decompose(m.tolist())
            out[b][0].append(p)
            out[b][1].append(q)
            out[b][2].append(sc)
    return {b: tuple(np.array(x) for x in v) for b, v in out.items()}


def mob_rig(src, form, kinds, tex, frames, prefix):
    """kinds [(model set, [(anim path, frames)])] -> meshes, bones, tracks (bones after a root)"""
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    meshes, bones, tracks = [], [('%s_root' % prefix, -1)], {}
    for i, (setname, anims) in enumerate(kinds):
        setdir = '%s/model/%s' % (d, setname)
        parts = mob_parts(setdir)
        names = sorted({b for b, _ in parts})
        motion = mob_motion(setdir, anims, frames, names)
        index = {}
        for b in names:
            bones.append(('%s%d_%s' % (prefix, i, b), 0))
            index[b] = len(bones) - 1
            tracks[bones[-1][0]] = motion[b]
        for b, part in parts:
            for m in to_nud([part], tex, 'lit'):
                m.name = '%s%d_%s' % (prefix, i, b)
                m.bind, m.bone = 8, index[b]
                m.gain = 'island'
                meshes.append(m)
    return meshes, bones, tracks


# the houses' doors (door_*_set: one bone each, Ultimate's open / close animations swing it 90
# degrees in 4 frames): on the villagers' skeleton, open while a villager is within DOOR_REACH of
# it (going in to sleep, coming out at dawn), DOOR_EARLY frames before and after; without them
# the villagers walked through the shut doors (user)
DOOR_REACH, DOOR_EARLY, DOOR_SWING = 8.0, 12, 4


def door_sets(src, form, biome):
    """the biome's door model sets (Omega: the butcher's, END_VILLAGERS)"""
    if form == 'melee':
        return [e for e in EXTRA.get(biome, []) if e.startswith('door_')]
    return ['door_%s_set' % v for v in END_VILLAGERS]


def villager_paths(villagers):
    """[[frames, 3]] each villager's Hip position (stage coordinates) over its animations"""
    import ssbh_data_py as s
    out = []
    for _set, anims in villagers:
        seq = []
        for path, n in anims:
            a = s.anim_data.read_anim(path)
            hip = [x for g in a.groups for x in g.nodes if x.name == 'Hip'][0].tracks[0].values
            seq += [hip[min(f, len(hip) - 1)].translation for f in (range(n) if isinstance(n, int) else n)]
        out.append(np.array(seq))
    return out


def atlas_rows(parts, tex, name):
    """parts on the block atlas moved to its rows they use (whole 16-pixel tiles), a texture of
    their own (name): the atlas in each folder that draws them is 4 MB"""
    img = tex.image(ATLAS)
    h = img.shape[0]
    v = np.concatenate([p['uv'][:, 1] for p in parts])
    lo, hi = int(np.floor(v.min() * h / 16)) * 16, int(np.ceil(v.max() * h / 16)) * 16
    tex.extra[name] = img[lo:hi].copy()
    out = []
    for p in parts:
        q = dict(p)
        q['uv'] = np.c_[p['uv'][:, 0], (p['uv'][:, 1] * h - lo) / (hi - lo)]
        q['textures'] = [name] + list(p['textures'][1:])
        out.append(q)
    return out


def door_rig(src, form, doors, paths, tex, frames):
    """meshes, bones, tracks: each door on its own bone, swung by the villagers' paths"""
    import ssbh_data_py as s
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    meshes, bones, tracks = [], [('door_root', -1)], {}
    for setname in doors:
        setdir = '%s/model/%s' % (d, setname)
        parts = load_parts(setdir)
        skel = s.skel_data.read_skel(setdir + '/model.nusktb')
        world = {k: m.T for k, m in _world(skel).items()}
        bone = parts[0]['bone']
        b = [x for x in skel.bones if x.name == bone][0]
        parent = world[skel.bones[b.parent_index].name] if b.parent_index is not None and b.parent_index >= 0 else np.eye(4)
        rest_p, _rq, rest_s = omo.decompose(np.array(b.transform, dtype=np.float64).T.tolist())

        def last(motion):
            a = s.anim_data.read_anim('%s/motion/%s/pickel_door_%s.nuanmb' % (d, setname, motion))
            return np.array([x for g in a.groups for x in g.nodes if x.name == bone][0].tracks[0].values[-1].rotation)
        shut, wide = last('close'), last('open')
        if np.dot(shut, wide) < 0:
            wide = -wide
        centre = np.concatenate([p['pos'] for p in parts]).mean(0)[[0, 2]]
        near = np.zeros(frames, bool)
        for path in paths:
            close = np.linalg.norm(path[:frames, [0, 2]] - centre, axis=1) < DOOR_REACH
            for f in np.where(close)[0]:
                near[max(0, f - DOOR_EARLY):f + DOOR_EARLY + 1] = True
        t = np.zeros(frames)                # 0 shut, 1 open, DOOR_SWING frames between
        for f in range(1, frames):
            t[f] = min(1.0, t[f - 1] + 1 / DOOR_SWING) if near[f] else max(0.0, t[f - 1] - 1 / DOOR_SWING)
        t[0] = t[-1] = 0.0
        bind_inv = np.linalg.inv(world[bone])
        pos, rot, scl = [], [], []
        for w in t:
            q = (1 - w) * shut + w * wide
            q /= np.linalg.norm(q)
            m = parent @ np.array(omo.trs(rest_p, q, rest_s)) @ bind_inv
            p_, q_, s_ = omo.decompose(m.tolist())
            pos.append(p_)
            rot.append(q_)
            scl.append(s_)
        bones.append(('door_%s' % setname, 0))
        tracks[bones[-1][0]] = tuple(np.array(x) for x in (pos, rot, scl))
        for m in to_nud(atlas_rows(parts, tex, 'all_blocks_doors'), tex, 'lit'):
            m.bind, m.bone = 8, len(bones) - 1
            m.gain = 'island'
            meshes.append(m)
    return meshes, bones, tracks


def mob_kinds(src, form, biome, animal, daynight=True):
    """(villagers, animals): [(model set, [(anim path, frames)])] for the biome (Omega: plains', END_VILLAGERS)"""
    d = '%s/%s/motion' % (src, 'normal' if form == 'melee' else 'battle')
    b = biome if form == 'melee' else 'plains'
    villagers = []
    for v in VILLAGERS.get(b, ()) if form == 'melee' else END_VILLAGERS:
        path = '%s/ch_pickel_%s_set/pickel_%s_%%s.nuanmb' % (d, v, v)
        if daynight:
            anims = [(path % a, n) for a, n in VILLAGER_CYCLE]
        else:
            anims = [(path % a, VILLAGER_FRAMES) for a in VILLAGER_DAY]
        anims.append((anims[0][0], 1))                      # the loop's last frame = its first
        villagers.append(('ch_pickel_%s_set' % v, anims))
    animals = []
    if animal:
        for w in ('wait1', 'wait2'):
            path = '%s/ch_pickel_%s_set/pickel_%s_%s_%s.nuanmb' % (d, animal, b, animal, w)
            if os.path.exists(path):
                anims = [(path, ANIMAL_FRAMES + 1)]
                if daynight:                # away for the night (animal_tracks hides them), then back
                    anims.append((path, [0] * (CYCLE - ANIMAL_FRAMES)))
                animals.append(('ch_pickel_%s_set' % animal, anims))
    return villagers, animals


# ---------------------------------------------------------------- day and night
# Ultimate's cycle at its full length (pickel_world.stdat frame_of_night 6000; its far_common_set,
# far_<biome>_set and render/light/light00_set animations: 9000 frames, day at 0, sunset ~4500,
# night ~6000, dawn ~8250). Smash 4 has no lights on our unlit models, so each material's colour
# follows a curve: an MTA (model.mta) animating NU_finalColorGain, which Battlefield animates on
# its own (lit, unlit and additive) shaders, on materials found by their NU_materialHash (one
# hash a kind of curve, GAIN_KINDS).
CYCLE = 9000
GAIN_KINDS = ('island', 'pano', 'fog', 'sky', 'cloud', 'sun', 'stars', 'sun_core', 'torchlight', 'pano_glow')
NIGHT_FLOOR = 0.5                   # the island's least gain (Ultimate's stage light 2.4 by day, 0.3 at night: 0.39, darker
                                    # than Ultimate's night island, whose ambient light stays: user's comparison)
SKY_RIG = 'dyr_m_SKY_DOME_set'      # the sun, the moon and the stars on their turning bones
PANO_MEAN = 0.55                    # the panoramas' mean texel value, about
RIG_LABELS = {'zz_sun': 'sun', 'zz_sun_core': 'sun_core', 'zz_moon': 'stars', 'sun_stars': 'stars'}
GLOW_LABELS = ('zz_sun', 'zz_sun_core', 'zz_moon')     # alpha-blended (BF_GLOW); the stars added
# the moon's glow: Ultimate's is its texture's grey-blue halo, lifted by the bloom; Smash 4's
# bloom doesn't reach a colour that dim, so the halo is drawn paler and stronger, and the moon past
# white (MOON_BRIGHT, in its vertex colours: 2 the most) for the bloom to glow around it, as it
# does around the sun (v15: still no light from it, user)
MOON_GLOW, MOON_GLOW_ALPHA, MOON_BRIGHT = (205, 218, 255), 1.6, 1.8
# the stars: their vertex colours (0.34, alpha 0.49) under Ultimate's CustomVector8 1.5 and HDR
# bloom; here they came out at 0.17 at most, not seen in game (user). Drawn at that 1.5, alpha 1
STARS_BRIGHT = 1.5
GAIN_FLAGS = None                   # a test: these flags instead of 0xA2001001 on materials with a curve
# fighters' shadows: Smash 4 draws them on materials with flag 0x40 (Smash Forge's NudEnums
# TextureFlag.Shadow); our unlit 0xA3C01081 (0x81: glow, diffuse) has none, so no shadows (user).
# Battlefield's own platform (stc_c_Ring_set) is 0xA4001041, lit. A test: the island on it
ISLAND_FLAGS = None
# light.bin (the fighters' lights; their records every 3 frames): Battlefield's own records for the
# same time of day (its cycle: night 1950-2400 and 0-100, dawn 200-500, day 800-1100, sunset
# 1300-1800), as (our frame, its record, counted on past 2400)
LIGHT_PHASES = ((0, 950), (3000, 1100), (3750, 1300), (4500, 1600), (5250, 1950), (7500, 2501),
                (8250, 2851), (9000, 3351))


def gain_hash(kind):
    """the NU_materialHash bits of a curve's materials (a plain float: 4096 + its index)"""
    return struct.unpack('>I', struct.pack('>f', 4096.0 + GAIN_KINDS.index(kind)))[0]


def _ult_track(path, node, param):
    """[frames, k] values of a material / light animation's track"""
    import ssbh_data_py as s
    a = s.anim_data.read_anim(path)
    n = [x for g in a.groups for x in g.nodes if x.name == node][0]
    v = [t for t in n.tracks if t.name == param][0].values
    return np.array([x if isinstance(x, list) else [x] for x in v], dtype=np.float64)


def daynight_curves(src, form, far_set):
    """{kind: NU_finalColorGain [CYCLE + 1, 4]} from Ultimate's animations"""
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    u = np.arange(CYCLE + 1)
    common = '%s/motion/far_common_set/far_common_set_00.nuanmb' % d
    light = '%s/normal/render/light/light00_set.nuanmb' % src

    def at(t):
        return t[np.minimum(u, len(t) - 1)]

    def ratio(node, path=common, param='CustomVector8'):
        # Ultimate's colours are linear, our vertex colours gamma-encoded (to_nud): the ratio too
        t = at(_ult_track(path, node, param))
        g = np.ones((len(u), 4))
        g[:, :3] = np.clip(t[:, :3] / t[:1, :3], 0, None) ** (1 / GAMMA)
        return g
    out = {}
    inten = np.clip(at(_ult_track(light, 'LightStg0', 'CustomFloat0'))[:, 0] / 2.4, NIGHT_FLOOR ** GAMMA, 1)
    col = at(_ult_track(light, 'LightStg0', 'CustomVector0'))[:, :3]
    col = (col / col.max(1, keepdims=True)) ** (1 / GAMMA)
    out['island'] = np.c_[inten[:, None] ** (1 / GAMMA) * col, np.ones(len(u))]
    isl = out['island'][:, :3].mean(1)
    dark = np.clip((isl.max() - isl) / (isl.max() - isl.min()), 0, 1)
    out['torchlight'] = np.c_[np.repeat(dark[:, None], 3, 1), np.ones(len(u))]
    out['sky'] = ratio('sfx_sky_color')
    out['cloud'] = ratio('sfx_cloud')
    # the sun's glow: Ultimate's colour, faded out with it once set (in Ultimate a black glow
    # below the horizon); its core white all day (Ultimate's doesn't change), fading with it
    sun = at(_ult_track(common, 'zz_sun', 'CustomVector8'))[:, :3]
    fade = np.clip(2 * (sun / sun[:1]).max(1), 0, 1)
    out['sun'] = ratio('zz_sun')
    out['sun'][:, 3] = fade
    out['sun_core'] = np.c_[np.ones((len(u), 3)), fade]
    stars = at(_ult_track(common, 'sun_stars', 'CustomVector8'))[:, 3]
    out['stars'] = np.c_[np.ones((len(u), 3)), stars]
    # the panorama: Ultimate blends its day and night textures (CustomVector20.w); here the day one
    # times the night one's colour over the day one's (per channel), warmed at sunset as the island
    far = '%s/motion/%s/%s_00.nuanmb' % (d, far_set, far_set)
    if not os.path.exists(far):
        far = '%s/normal/motion/far_plains_set/far_plains_set_00.nuanmb' % src
    import ssbh_data_py as s
    # its material's node: sfx_far_A_long (plains), sfx_far_E_long (snowy tundra), sfx_far_C, ...
    names = {x.name for g in s.anim_data.read_anim(far).groups for x in g.nodes}
    pano_node = [n for n in names if n.startswith('sfx_far_') and not n.endswith('_fog')][0]
    fog_node = [n for n in names if n.startswith('sfx_far_') and n.endswith('_fog')][0]
    night = at(_ult_track(far, pano_node, 'CustomVector20'))[:, 3]
    out['pano_glow'] = np.c_[np.repeat(night[:, None], 3, 1), np.ones(len(u))]
    day_tex = glob.glob('%s/normal/model/%s/far_*_day_low_col.nutexb' % (src, far_set))[0]
    a = nutexb.decode(nutexb.Nutexb(day_tex)).astype(np.float64)
    b = nutexb.decode(nutexb.Nutexb(day_tex.replace('_day_', '_night_'))).astype(np.float64)
    m = a[..., 3] > 250
    k = b[m][:, :3].mean(0) / a[m][:, :3].mean(0)
    warm = 0.6 + 0.4 * col              # col: the stage light's colour (gamma-encoded, max 1)
    base = ((1 - night)[:, None] + night[:, None] * k) * warm
    # and its haze (CustomVector19: colour, .w how much; reddish at sunset, near black late at
    # night) as a gain towards that colour over the texture's mean (PANO_MEAN)
    haze = at(_ult_track(far, pano_node, 'CustomVector19'))
    w = haze[:, 3:4]
    out['pano'] = np.c_[base * (1 - w) + w * np.clip(haze[:, :3], 0, None) ** (1 / GAMMA) / PANO_MEAN, np.ones(len(u))]
    fog = ratio(fog_node, far)
    fog[:, 3] = np.clip(fog[:, :3].mean(1), 0, 1)       # the haze fades out with its colour
    out['fog'] = fog
    return out


def chr_light(src):
    """Ultimate's fighter light (light00_set LightChr: intensity 4.6 by day, 1.8 at night, white,
    warm at night) over CYCLE: [CYCLE + 1] its brightness over midday's (gamma-encoded, as the
    island's), [CYCLE + 1, 3] its colour (max 1)"""
    light = '%s/normal/render/light/light00_set.nuanmb' % src
    n = CYCLE + 1
    inten = _ult_track(light, 'LightChr', 'CustomFloat0')[:, 0]
    col = _ult_track(light, 'LightChr', 'CustomVector0')[:, :3]
    f = np.minimum(np.arange(n), len(inten) - 1)
    g = np.minimum(np.arange(n), len(col) - 1)
    return (inten[f] / inten[0]) ** (1 / GAMMA), col[g] / col[g].max(1, keepdims=True)


def cycle_light(path, phases=LIGHT_PHASES, fighter=None):
    """Battlefield's light.bin over CYCLE: a record every 3 frames (3001), each Battlefield's for the
    same time of day (phases), and the five colour tracks likewise. fighter (chr_light's): the fighters'
    light (each record's first block) and the colour tracks instead Battlefield's midday (DAY_FRAME)
    ones dimmed and tinted by it: Battlefield's night lit them with a strong blue light (user)"""
    d = open(path, 'rb').read()
    magic, ver, n, step, rec = struct.unpack('>4sIIII', d[:20])
    assert magic == b'LIGH' and ver == 5 and step == 3
    tracks = struct.unpack('>5I', d[0x14:0x28])
    size = (len(d) - rec) // n
    count = CYCLE // step + 1
    f = np.arange(count) * step
    src = np.round(np.interp(f, *zip(*phases))).astype(int) % n
    pad = -3 * count % 4
    out = bytearray(b'LIGH' + struct.pack('>III', ver, count, step))
    start = 0x28 + 5 * (3 * count + pad)
    out += struct.pack('>I', start) + struct.pack('>5I', *[0x28 + i * (3 * count + pad) for i in range(5)])
    if fighter is not None:
        bright, col = fighter[0][f], fighter[1][f]
    for o in tracks:
        if fighter is None:
            out += b''.join(d[o + 3 * r:o + 3 * r + 3] for r in src) + b'\0' * pad
        else:
            day = np.frombuffer(d[o + 3 * DAY_FRAME:o + 3 * DAY_FRAME + 3], np.uint8).astype(np.float64)
            rgb = np.clip(np.round(day * bright[:, None] * col), 0, 255).astype(np.uint8)
            out += rgb.tobytes() + b'\0' * pad
    assert len(out) == start
    recs = [bytearray(d[rec + size * r:rec + size * (r + 1)]) for r in src]
    if fighter is not None:
        import colorsys
        day = bytes(d[rec + size * DAY_FRAME:rec + size * DAY_FRAME + 116])
        on, *v, _h, _s, val = struct.unpack('>i6f', day[:28])
        for i, r in enumerate(recs):
            h, sat, _v = colorsys.rgb_to_hsv(*col[i])
            r[:116] = day
            r[:28] = struct.pack('>i6f', on, *v, h * 360, sat, val * bright[i])
    out += b''.join(bytes(r) for r in recs)
    return bytes(out)


def sky_rig(src, form, tex):
    """the sun, the moon and the stars (far_common_set, each mesh on one bone) on a made skeleton,
    turning as Ultimate's (sunmoon_rotateAxis, stars_RotateAxis) over CYCLE; the sun and the moon
    alpha-blended (BF_GLOW), the stars added (BF_STARS)"""
    d = '%s/%s' % (src, 'normal' if form == 'melee' else 'battle')
    setdir = '%s/model/far_common_set' % d
    parts = [p for p in load_parts(setdir) if p['label'] in RIG_LABELS]
    moon = [p for p in parts if p['label'] == 'zz_moon']
    if moon:                                # its half of the shared sun / moon texture: a paler glow
        name = moon[0]['textures'][0]
        img = tex.image(name).copy()
        w = img.shape[1]
        half = img[:, int(moon[0]['uv'][:, 0].min() * w):int(np.ceil(moon[0]['uv'][:, 0].max() * w))]
        halo = half[..., 3] < 250
        half[halo, :3] = MOON_GLOW
        half[halo, 3] = np.clip(np.round(half[halo, 3] * MOON_GLOW_ALPHA), 0, 255)
        tex.extra[name] = img
    names = sorted({p['bone'] for p in parts})
    motion = mob_motion(setdir, [('%s/motion/far_common_set/far_common_set_00.nuanmb' % d, list(range(CYCLE + 1)))],
                        CYCLE + 1, names)
    meshes, bones, tracks, index = [], [('sky_root', -1)], {}, {}
    for b in names:
        bones.append(('sky_%s' % b, 0))
        index[b] = len(bones) - 1
        tracks[bones[-1][0]] = motion[b]
    for p in parts:
        for m in to_nud([p], tex, 'bg'):
            for poly in m.polygons:
                poly.materials = [bf_material(BF_GLOW if p['label'] in GLOW_LABELS else BF_STARS,
                                              poly.materials[0].textures[0]['hash'])]
                if p['label'] == 'zz_moon':
                    poly.col[:, :3] = round(128 * MOON_BRIGHT)
                elif p['label'] == 'sun_stars':
                    poly.col[:, :3] = round(128 * STARS_BRIGHT)
                    poly.col[:, 3] = 128
            m.bind, m.bone = 8, index[p['bone']]
            m.gain = RIG_LABELS[p['label']]
            meshes.append(m)
    return meshes, bones, tracks


# ---------------------------------------------------------------- stage
def tiny_nut(path):
    """a hidden folder's textures at 64x64, same IDs (its materials and material animations still
    find them; the model is never drawn): Battlefield's full-size ones were 14.5 MB of the stage's
    memory. Files that aren't single-mip-able 2D NTWU (Omega's NTP3, a cube map) stay as they are."""
    try:
        d, ts = nut.load(path)
    except AssertionError:
        return open(path, 'rb').read()
    if any(t.dim != 1 or t.depth != 1 or t.tex_id is None for t in ts):
        return d
    blank = np.zeros((64, 64, 4), np.uint8)
    return nut.write_ntwu([(t.tex_id, t.fmt if t.fmt in nut.NTWU_CODE else 0x33, blank) for t in ts])


def build_form(src, base_dir, out_dir, form, biome, hazards, yamlvd, labels, effect=None, torches='animated',
               clouds='moving', animal='sheep', daynight=True):
    """form 'melee' (one biome) or 'end' (Omega: the battle folder's flat form). torches (need
    effect): 'animated' (TORCH_SET), 'still' (flames in the island's model) or 'off'; clouds:
    'moving' or 'still'; animal: 'sheep', 'cow', 'chicken' or None; daynight: Ultimate's day / night
    cycle (CYCLE), or held at midday"""
    if torches == 'off':
        effect = None
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(base_dir, out_dir)
    model_dir = out_dir + '/model'
    lut = nutexb.lut3d(nutexb.Nutexb('%s/%s/lut/color_grading_lut.nutexb' % (src, 'normal' if form == 'melee' else 'battle')))
    tex = Textures(src, lut)
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
            if not (e.startswith('door_') and daynight and VILLAGERS.get(biome)):     # those: door_rig
                extra += load_parts('%s/normal/model/%s' % (src, e))
        bparts = block_parts(src, blocks) if blocks else []
        if bparts:
            solid = solid_cells(ring + plat) | {(x, y, z) for _k, x, y, z, _f in blocks}
            bparts = [block_ao(p, solid) for p in bparts]
        near = ring + bparts + plat + extra
        far_dir = '%s/normal/model/%s' % (src, FAR[biome])
        far, far_fog = far_parts(far_dir)
        sky_src = '%s/normal/model/far_common_set' % src
    else:
        d = ult_lvd('%s/battle/param/pickel_world_end_00.lvd' % src, yamlvd)
        blocks = []
        near = load_parts('%s/battle/model/ring_endbattle_set' % src)
        if not daynight:                    # with it: door_rig
            near += [p for e in door_sets(src, form, biome) for p in load_parts('%s/battle/model/%s' % (src, e))]
        far_dir = '%s/battle/model/far_plains_set' % src
        far, far_fog = far_parts(far_dir)
        sky_src = '%s/battle/model/far_common_set' % src
    sky = [p for p in load_parts(sky_src) if p['label'] in SKY_LABELS]

    cloud_parts = [p for p in sky if p['bone'] in CLOUD_SETS]
    sky = [p for p in sky if p['bone'] not in CLOUD_SETS and not (daynight and p['label'] in RIG_LABELS)]
    villagers, animals = mob_kinds(src, form, biome, animal, daynight)
    rig = villagers or (effect and torches == 'animated')
    curves = daynight_curves(src, form, FAR[biome] if form == 'melee' else 'far_plains_set') if daynight else None
    for name in sorted(os.listdir(model_dir)):
        if (name in (RING_SET, FAR_SET, SKY_SET, FOG_SET) or name in CLOUD_SETS.values() or name == TORCH_SET and rig
                or name == ANIMAL_SET and animals or name == SKY_RIG and daynight):
            assert name == SKY_RIG or not os.path.exists('%s/%s/model.mta' % (model_dir, name)), name
        else:
            path = '%s/%s/model.nud' % (model_dir, name)
            data = nud.hidden(path)
            open(path, 'wb').write(data)
            path = '%s/%s/model.nut' % (model_dir, name)
            if os.path.exists(path):
                data = tiny_nut(path)
                open(path, 'wb').write(data)
    torch, torch_bones, torch_motion, points = [], [('torch_root', -1)], {}, []
    if effect:
        row = BIOMES.index(biome) if form == 'melee' else TORCH_ROW_END
        points = torch_points(src, labels, row)
        torch, torch_bones, torch_motion = torch_meshes(points, tex, effect, torches == 'animated')
    for name, parts, kind, is_sky in ((RING_SET, near, 'lit', False), (FAR_SET, far, 'bg', False),
                                      (FOG_SET, far_fog, 'bg', False), (SKY_SET, sky, 'bg', True)):
        meshes = to_nud(parts, tex, kind, is_sky, cutout=name == FAR_SET)
        for m, part in zip(meshes, [q for q in parts if q['textures'] and q['uv'] is not None]):
            m.gain = {RING_SET: 'island', FAR_SET: 'pano', FOG_SET: 'fog'}.get(name) or (
                'sun' if part['label'].startswith('zz_sun') else 'sky')
        if name == RING_SET and ISLAND_FLAGS:
            for m in meshes:
                for poly in m.polygons:
                    for mat in poly.materials:
                        mat.flags = ISLAND_FLAGS
        if name == RING_SET and torches == 'still':
            meshes += torch                 # unbound, the island's alpha-tested unlit setup
        if name == RING_SET and curves and points:
            meshes += torch_light(meshes, points)
        if name == FAR_SET and curves:
            for m in to_nud(pano_glow(far_dir, tex), tex, 'bg'):
                for poly in m.polygons:
                    poly.materials = [added(poly.materials[0])]
                m.gain = 'pano_glow'
                meshes.append(m)
        write_set('%s/%s' % (model_dir, name), meshes, tex, curves)
    for name, changes in ((FAR_SET, {'drawing_order': {'number': FAR_ORDER}}),
                          (FOG_SET, {'drawing_order': {'number': FOG_ORDER}, 'draw_range': {'number': '2'}})):
        path = '%s/%s/model.xmb' % (model_dir, name)
        data = xmb.edit(open(path, 'rb').read(), changes)
        open(path, 'wb').write(data)
    write_clouds(model_dir, out_dir + '/animation', cloud_parts, tex, src, form, clouds == 'moving', curves)
    anim_dir = out_dir + '/animation'
    if daynight:
        m, b, t = sky_rig(src, form, tex)
        write_rig(model_dir, anim_dir, SKY_RIG, m, b, t, CYCLE + 1, tex, curves)
    if rig:
        # torches (their own bones) and villagers in TORCH_SET, one skeleton, one animation
        frames = ((CYCLE if daynight else VILLAGER_FRAMES * len(VILLAGER_DAY)) + 1 if villagers
                  else TORCH_LOOP + 1)
        meshes, bones = [], [('rig_root', -1)]
        tracks = {}
        if effect and torches == 'animated':
            meshes += torch
            bones += torch_bones[1:]
            tracks.update(torch_tracks(torch_bones, torch_motion, frames))
        if villagers:
            m, b, t = mob_rig(src, form, villagers, tex, frames, 'villager')
            if daynight:
                dm, db, dt = door_rig(src, form, door_sets(src, form, biome), villager_paths(villagers), tex, frames)
                if points:                  # the torches' light on them too (user)
                    dm += torch_light(dm, points, DOOR_LIGHT_MAX)
                for mesh in dm:
                    mesh.bone += len(b) - 1
                m, b = m + dm, b + db[1:]
                t.update(dt)
            for mesh in m:                  # its bones come after the torches'
                mesh.bone += len(bones) - 1
            meshes += m
            bones += [(n, 0) for n, _p in b[1:]]
            tracks.update(t)
        write_rig(model_dir, anim_dir, TORCH_SET, meshes, bones, tracks, frames, tex, curves)
    if animals:
        frames = (CYCLE if daynight else ANIMAL_FRAMES) + 1
        m, b, t = mob_rig(src, form, animals, tex, frames, 'animal')
        for name, (pos, rot, scl) in t.items():
            scl[ANIMAL_FRAMES + 1:frames - 1] = 0.0         # away for the night
            if form != 'melee':
                pos += END_ANIMAL_SHIFT
        write_rig(model_dir, anim_dir, ANIMAL_SET, m, b, t, frames, tex, curves)

    light = out_dir + '/animation/light.bin'
    data = cycle_light(light, fighter=chr_light(src)) if daynight else still_light(light)
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
    ap.add_argument('--torches', default='animated', choices=('animated', 'still', 'off'),
                    help="animated (default; v12 test A2 in game), still (flames in the island's model) or off")
    ap.add_argument('--clouds', default='moving', choices=('moving', 'still'))
    ap.add_argument('--daynight', default='on', choices=('on', 'off'), help="Ultimate's day / night cycle, or midday")
    ap.add_argument('--gain-shader', choices=('a2', 'a3c'), default='a3c',
                    help="a test: the curves on our unlit 0xA2001001 or on Battlefield's 0xA3C01081")
    ap.add_argument('--island-shader', choices=('unlit', 'shadow'), default='unlit',
                    help="a test: the island on Battlefield's platform shader 0xA4001041 (fighters' shadows)")
    ap.add_argument('--animal', default='sheep', choices=('sheep', 'cow', 'chicken', 'none'),
                    help="the two animals in the pen (Ultimate picks one of the three each time)")
    a = ap.parse_args()
    global GAIN_FLAGS, ISLAND_FLAGS
    GAIN_FLAGS = 0xA3C01081 if a.gain_shader == 'a3c' else None
    ISLAND_FLAGS = 0xA4001041 if a.island_shader == 'shadow' else None
    for form in ('melee', 'end'):
        cols, blocks = build_form(a.src, '%s/%s/%s' % (a.base, form, a.name), '%s/stage/%s/%s' % (a.out, form, a.name),
                                  form, a.biome, a.hazards == 'on', a.yamlvd, a.labels, a.effect, a.torches, a.clouds,
                                  None if a.animal == 'none' else a.animal, a.daynight == 'on')
        print('%s: %d collisions (%d drop-through), %d blocks' % (form, len(cols), sum(c.flags[3] for c in cols), len(blocks)))


if __name__ == '__main__':
    main()
