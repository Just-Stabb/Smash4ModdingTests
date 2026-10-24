#!/usr/bin/env python3
"""Ultimate fighter effects (ef_<name>.eff, VFXB: tools/vfxb.py) -> Smash 4 emitter sets added to a
fighter's ptcl (one set per Ultimate emitter set), its .efc entries, and an ids file for
tools/ultimate_acmd.py --effects.

  python3 tools/vfxb_to_ptcl.py EFF BASE_DIR OUT_DIR KIND IDS.json [EFFECT ...] [--prefix PtcEdge]
                                [--templates VANILLA.ptcl ...]

BASE_DIR: the base fighter's effect folder (<base>.010d0000.ptcl / .efc, e.g. Zelda's: the new
fighter's bank is a copy of it, the base's specials still use its sets). OUT_DIR gets
<name>.010d0000.ptcl / .efc (named after BASE_DIR's files: rename for the fighter); KIND: the
fighter kind (ids 0x3KKnnnn). EFFECT: Ultimate effect names (default: all).

Mapping (eft2 v22 -> eft 0x42), per emitter, from a template emitter, as tools/xv2_to_ptcl.py:
- template: Templates (the base's own or one imported from --templates files) of the eft particle
  type (eft2's numbers: 0 billboard, 1 / 2 plate XY / XZ, 3 directional, 4 directional polygon, 8 Y
  billboard; 7 primitive as a billboard mesh; a type-3 mesh at rest as type 4), blend and mesh-ness,
  plain shaders first. Stripes (5 / 6) are skipped;
- meshes (a primitive id): the VFXB's model (G3PR BFRES, tools/bfres_switch.py; first shape)
  written to the primitive table (Ptcl.add_primitive, once per id);
- texture: the first sampler that isn't an indirect / grade / noise / mask helper, its BNTX channel
  selection applied (tools/vfxb.py images), the first flipbook cell (uv_div); the sampler's wrap
  per axis; its UV shift / scale / rotation (initial, random, a frame) into slot 0's UV block
  (set_uv_anim; baked into a mesh's UVs when the template can't animate them);
- colour / alpha: eft2's combiner (colour modes 0-3: colour 0, x texture, + colour 1 x (1 -
  texture), + colour 1; alpha modes 0-4) folded into a BC4 shape and one particle colour (combine):
  each pixel's brightness kept, the hue averaged; the 3-key colour and alpha fits; colour scale;
- meshes: the particle's 3D scale baked into the mesh, the emitter's scale 1 (x the animation);
- scale: the particle scale x the scale keys (3-key fit), random % -> fraction;
- life (+ random % -> frames; infinite -> 0x7FFFFFFF, emitted once), emission (start, duration when one-time, else
  forever, interval, rate), velocity (all-direction -> figure velocity, designated direction x
  scale -> emitter velocity / direction, diffusion angle, random %), gravity (scale x direction),
  air resistance, volume (same 0-14 shape list; radius x form scale), rotation (init / random /
  add, radians), the emitter transform (translate / rotate / scale); the fade when turned off
  (0x82C: 1 / alpha fade time; infinite life fades too);
- not converted: pattern (flipbook) animation, the second colour track and multi-texture
  combiners, alpha / scale fades at the end, emitter animations (EAA0 / EAA1 ...), child emitters.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import efc  # noqa: E402
import ptcl  # noqa: E402
import vfxb  # noqa: E402
from xv2_to_ptcl import (BLEND, FOREVER, MAX_EMITTERS, MAX_LIVE, buffer_count, color_fit,  # noqa: E402
                         pow2, resize, sanitize, three_key)

NONE64 = 2 ** 64 - 1
# eft2 vertex transform -> eft particle type (the same numbers: 0 billboard, 1 / 2 plate XY / XZ,
# 3 directional, 4 directional polygon, 8 Y billboard); 7 (primitive) as a billboard mesh; 5 / 6
# (stripes) have no eft counterpart here
TYPES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 7: 0, 8: 8}
TEX_MAX = 128           # vanilla effect textures are mostly 64-128 (the bank's size: Bayonetta's is 4.6 MB)
BASE_FIRST = 2          # a template of the base's own beats an imported one this much
UV_MODE = 0x510         # slot 0's UV animation (0x4D4 + 0x3C; the block below, docs/ptcl-format.md)
FOLLOW = 0x2F9
FADE_ALPHA = 0x82C      # alpha lost a frame once the set is turned off (1 / frames); 0 lives on
# eft2 sampler wrap (0 mirror, 1 repeat, 2 clamp) -> GX2 (0 repeat, 1 mirror, 2 clamp); the eft
# sampler word: U wrap in bits 28-31, V in 24-27 (clamped vanilla textures: 0x22000100)
WRAP = {0: 1, 1: 0, 2: 2}


class Templates:
    """template emitters by (eft particle type, blend 0 / 1 / 2, mesh): simple emitters with one BC4
    texture (slot 0; slots 1 / 2 unused). Among them, in this order: a plain shader (no shader
    parameters: Ike's FS cloud shader, FinIkeCloud FNSmoke with 32 bytes of them, tinted Sephiroth's
    meshes orange), the UV animation the emitter needs (slot 0's mode word 0x510: 1 scroll, 2
    scale, 4 rotate; shader-keyed: 8 of 4291 vanilla shader groups mix values) or more, the follow
    byte 0x2F9 wanted (0 on 86% of vanilla's infinite-life glows, 1 on 88% of the rest: taken as
    particles following the emitter; also shader-keyed: 41 groups mix), then animated colour tracks
    (2 / 2, then 2 / x) and the base's own (no import); others are imported from the corpus
    (Ptcl.import_emitter: their shader, shader parameters and textures copied)"""

    def __init__(self, base, corpus):
        self.base, self.files, self.found = base, {}, {}
        for path in [None] + list(corpus):
            p = base if path is None else ptcl.Ptcl(open(path, 'rb').read())
            if path is not None:
                self.files[path] = p
            for si, s in enumerate(p.sets):
                for k, x in enumerate(s['emitters']):
                    em = x['data']
                    if em is None or len(em) != ptcl.SIMPLE_SIZE:
                        continue
                    t = [p.texres(em, j) for j in range(3)]
                    if t[0]['native_format'] != 9 or t[1]['native_size'] or t[2]['native_size']:
                        continue
                    key = (p.field(em, 'particle_type'), p.field(em, 'blend_type'), p.field(em, 'primitive_index') >= 0)
                    c = (p.field(em, 'color0_type'), p.field(em, 'color1_type'))
                    score = (2 if c == (2, 2) else 1 if c[0] == 2 else 0) + (BASE_FIRST if path is None else 0) \
                        - (1 if p.field(em, 'keyanim_size') else 0)
                    traits = (not p.field(em, 'shader_param_size'), struct.unpack_from('>I', em, UV_MODE)[0] & 7,
                              em[FOLLOW] == 0)
                    self.found.setdefault(key, {})
                    if traits not in self.found[key] or score > self.found[key][traits][0]:
                        self.found[key][traits] = (score, path, si, k)

    def get(self, typ, blend, mesh, uv_mode, follow, notes):
        """the best template for this particle type / blend / mesh-ness, UV mode bits and follow;
        another blend (add), then type 0, when there's none"""
        def rank(item):
            (plain, mode, fol), (score, *_r) = item
            return (plain, mode & uv_mode == uv_mode, fol == follow, mode == uv_mode, score)
        for key in ((typ, blend, mesh), (typ, 1, mesh), (0, blend, mesh), (0, 1, mesh)):
            if key not in self.found:
                continue
            (plain, mode, fol), (_score, path, si, k) = max(self.found[key].items(), key=rank)
            if key != (typ, blend, mesh):
                notes.append('no template (type %d blend %d%s): type %d blend %d' % (
                    typ, blend, ' mesh' if mesh else '', key[0], key[1]))
            if mode & uv_mode != uv_mode:
                notes.append('UV animation %d: template has %d' % (uv_mode, mode))
            if fol != follow:
                notes.append('template follow byte %d' % (0 if fol else 1))
            if path is None:
                em = self.base.emitter_bytes(si, k)
                struct.pack_into('>II', em, 0x2CC, 0, 0)
                return em
            return self.base.import_emitter(self.files[path], si, k, skip_slots=(0,))
        raise KeyError((typ, blend, mesh))


def mesh(model):
    """(pos, nrm, col, uv, idx) of a BFRES model's first shape. Every vanilla primitive has normals
    (825 of them; 106 have no colour): missing ones are +Z; an all-white colour is left out"""
    shp = model['shapes'][0]
    a = model['vertex_buffers'][shp['vertex_buffer']]['attrs']
    n = len(a['_p0'])
    uv0 = a.get('_u0', np.zeros((n, 2), np.float32))[:, :2]
    uv1 = a.get('_u1', uv0)[:, :2]
    nrm = a['_n0'][:, :3] if '_n0' in a else np.tile(np.array([0, 0, 1], np.float32), (n, 1))
    col = a['_c0'][:, :4] if '_c0' in a else None
    if col is not None and col.min() >= 0.99:
        col = None
    return (a['_p0'][:, :3], nrm, col, np.concatenate([uv0, uv1], 1), shp['meshes'][0]['indices'])


HELPER_TEXTURES = ('indirect', 'grade', 'noise', 'mask')


def keys(table, n, comps=3):
    """an eft2 key table (8 x (x, y, z, time 0-1)) -> [101, comps] samples over the particle's life"""
    k = np.array(table['keys'], float).reshape(8, 4)[:max(1, n)]
    t = np.linspace(0, 1, 101)
    return np.stack([np.interp(t, k[:, 3], k[:, c]) for c in range(comps)], 1)


def main_texture(e, names):
    smp = [(i, s) for i, s in enumerate(e['sampler']) if s['texture_id'] != NONE64]
    for i, s in smp:
        if not any(h in names.get(s['texture_id'], '') for h in HELPER_TEXTURES):
            return i, s
    return smp[0] if smp else (None, None)


def first_cell(img, scroll):
    nx, ny = (int(round(v)) if v and v >= 1 else 1 for v in scroll['uv_div'])
    h, w = img.shape[:2]
    return img[:max(4, h // ny), :max(4, w // nx)]


LUMA = np.array([0.299, 0.587, 0.114])


def track(st, col, n):
    """colour track n (0 / 1) over the particle's life [101, 3] and alpha track n [101]"""
    c = keys(st['color%d' % n], st['num_color%d_keys' % n]) if col['color%d_type' % n] == 2 else \
        np.tile(np.array(col['color%d' % n][:3], float), (101, 1))
    a = keys(st['alpha%d' % n], st['num_alpha%d_keys' % n], 1)[:, 0] if col['alpha%d_type' % n] == 2 else \
        np.full(101, float(col['color%d' % n][3]))
    return c, a


def combine(img, e, notes):
    """eft2's combiner on the main texture, folded into what a one-colour eft template draws (a BC4
    shape x the particle colour): (shape [h, w] 0-1, colour [101, 3], alpha [101]).
    Colour modes (combiner color_process): 0 colour 0; 1 colour 0 x texture; 2 colour 0 x texture +
    colour 1 x (1 - texture); 3 colour 0 x texture + colour 1. Each pixel's colour at the tracks' life
    means, weighted by the texture's alpha: their mean is the particle colour, each pixel's
    brightness against it the shape (the hue across the texture is lost, its brightness kept); the
    colour over life is the same mix of the tracks at the texture's mean. Alpha modes (alpha_process):
    0 / 1 texture alpha x alpha 0 (1 erodes the texture by alpha 0: a fade by the ink left), 2 / 3 the
    same with the texture's red, 4 texture alpha x alpha 0 x alpha 1."""
    st, col, cb, info = e['static'], e['color'], e['combiner'], e['info']
    c0, a0 = track(st, col, 0)
    c1, a1 = track(st, col, 1)
    c0 = c0 * np.array(info['color0'][:3])
    c1 = c1 * np.array(info['color1'][:3])
    f = img.astype(np.float32) / 255
    rgb = f[..., :3]
    am = cb['alpha_process']
    atex = f[..., 0] if am in (2, 3) else f[..., 3]
    cm = cb['color_process']
    m0, m1 = c0.mean(0), c1.mean(0)
    if cm == 0:
        pix = np.broadcast_to(m0, rgb.shape)
    elif cm == 1:
        pix = rgb * m0
    elif cm == 2:
        pix = rgb * m0 + (1 - rgb) * m1
    else:
        pix = rgb * m0 + m1
    w = atex[..., None]
    wsum = max(float(w.sum()), 1e-6)
    tm = (rgb * w).reshape(-1, 3).sum(0) / wsum                     # the texture's mean (per channel)
    cmean = (pix * w).reshape(-1, 3).sum(0) / wsum
    lc = max(float(cmean @ LUMA), 1e-4)
    shape = atex * (pix @ LUMA) / lc
    peak = max(float(shape.max()), 1e-4)
    shape = shape / peak
    if cm == 0:
        colour = c0
    elif cm == 1:
        colour = c0 * tm
    elif cm == 2:
        colour = c0 * tm + c1 * (1 - tm)
    else:
        colour = c0 * tm + c1
    colour = colour * peak * float(cmean @ LUMA > 0)
    alpha = a0 * info['color0'][3] * (a1 * info['color1'][3] if am == 4 else 1.0)
    if am in (1, 3):
        # erosion: each pixel is texture - (1 - alpha), so the faint parts go first and the bright
        # strokes last (the texture can't change over life here): the fade kept is the texture's
        # remaining ink against its full ink
        t = atex[::max(1, atex.shape[0] // 64), ::max(1, atex.shape[1] // 64)].ravel()
        ink = max(float(t.sum()), 1e-6)
        alpha = np.array([np.clip(t - (1 - a), 0, 1).sum() / ink for a in np.clip(alpha, 0, 1)])
        notes.append('alpha erosion: fade by the remaining ink')
    return shape, np.clip(colour, 0, None), np.clip(alpha, 0, 1)


def uv_mode(ts):
    """the UV animation bits (1 scroll, 2 scale, 4 rotate) a sampler's eft2 UV parameters need"""
    if ts is None:
        return 0
    nz = lambda v: any(abs(x) > 1e-6 for x in (v if isinstance(v, list) else [v]))  # noqa: E731
    return (1 if nz(ts['scroll']) or nz(ts['scroll_add']) or nz(ts['scroll_random']) else 0) \
        | (2 if nz([x - 1 for x in ts['scale']]) or nz(ts['scale_add']) or nz(ts['scale_random']) else 0) \
        | (4 if nz(ts['rotation']) or nz(ts['rotation_add']) or nz(ts['rotation_random']) else 0)


def uv_transform(uv, scale, scroll, rotation):
    """eft2's starting UV transform: scaled and turned about the texture's centre, then shifted"""
    c, s = math.cos(rotation), math.sin(rotation)
    q = (uv - 0.5) * np.array(scale, np.float32)
    return (np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], 1) + 0.5
            + np.array(scroll, np.float32)).astype(np.float32)


def set_uv_anim(em, ts):
    """eft2's UV parameters (shift / scale / rotation: initial, random, per frame) -> slot 0's eft
    block: 0x510 mode (bits 1 / 2 / 4; the template's, at least the bits needed), 0x514 scroll a
    frame, 0x51C scroll init, 0x524 scroll random, 0x52C scale a frame, 0x534 scale init, 0x53C
    scale random, 0x544 rotation a frame, 0x548 rotation init, 0x54C rotation random (the vanilla
    corpus: each mode bit set exactly where those values are). Unused ones are left neutral."""
    if ts is None:
        ts = {'scroll': [0, 0], 'scroll_add': [0, 0], 'scroll_random': [0, 0], 'scale': [1, 1],
              'scale_add': [0, 0], 'scale_random': [0, 0], 'rotation': 0, 'rotation_add': 0, 'rotation_random': 0}
    struct.pack_into('>2f', em, 0x514, *ts['scroll_add'])
    struct.pack_into('>2f', em, 0x51C, *ts['scroll'])
    struct.pack_into('>2f', em, 0x524, *ts['scroll_random'])
    struct.pack_into('>2f', em, 0x52C, *ts['scale_add'])
    struct.pack_into('>2f', em, 0x534, *ts['scale'])
    struct.pack_into('>2f', em, 0x53C, *ts['scale_random'])
    struct.pack_into('>3f', em, 0x544, ts['rotation_add'], ts['rotation'], ts['rotation_random'])


def convert_emitter(p, e, names, images, notes, templates, prims, prim_index):
    pt = e['particle']
    typ = TYPES.get(pt['billboard_type'])
    if typ is None:
        notes.append('billboard type %d (stripe): skipped' % pt['billboard_type'])
        return None
    is_mesh = pt['primitive_id'] != NONE64
    if is_mesh and pt['primitive_id'] not in prims:
        notes.append('primitive %d not in the file: skipped' % pt['primitive_id'])
        return None
    vel = e['velocity']
    if is_mesh and typ == 3 and abs(vel['all_direction']) + abs(vel['designated_dir_scale']) < 1e-3:
        # a directional mesh at rest (his sword glows, slash arcs) lies in the emitter's frame in
        # Ultimate; eft's directional type 3 turns it by its (zero) velocity (test 32: the up-air arc
        # lay flat), type 4 keeps the emitter's frame at rest (Zelda's Nayru's Love crystals)
        typ = 4
        notes.append('directional mesh at rest: type 4')
    blend = {0: 'normal', 1: 'add', 2: 'sub'}.get(e['render']['blend_type'], 'add')
    ti, smp = main_texture(e, names)
    ts = e['static']['tex_scroll'][ti] if smp else None
    em = templates.get(typ, BLEND[blend], is_mesh, uv_mode(ts), e['info']['follow_type'] == 0, notes)
    if is_mesh:
        # eft's particle scale has two axes (vanilla 3D meshes, e.g. Zelda's smash arc, are built at
        # size with scale 1): an uneven 3D scale goes into the mesh (one primitive per mesh and
        # scale) and the emitter scales by 1 (x its scale animation); an even one stays the
        # particle's (the mesh shared)
        s3 = tuple(round(float(v), 4) for v in e['scale']['scale'])
        is_mesh = 'even' if max(s3) - min(s3) < 1e-3 else True
        if is_mesh == 'even':
            s3 = (1.0, 1.0, 1.0)
        # a template without the UV animation needed: the starting UV transform goes into the mesh's
        # UVs (the shift / scale / rotation over life is lost)
        need = uv_mode(ts)
        bake = None
        if struct.unpack_from('>I', em, UV_MODE)[0] & need != need:
            bake = (tuple(ts['scale']), tuple(ts['scroll']), ts['rotation'])
            notes.append('UV transform baked into the mesh')
        key = (pt['primitive_id'], s3, bake)
        if key not in prim_index:
            pos, nrm, col_, uv, idx = mesh(prims[pt['primitive_id']])
            if bake:
                uv = np.concatenate([uv_transform(uv[:, :2], *bake), uv[:, 2:]], 1)
            prim_index[key] = p.add_primitive(pos * np.array(s3, np.float32), nrm, col_, uv, idx)
        struct.pack_into('>i', em, 0x2DC, prim_index[key])
        if bake:
            ts = None
    # the blend is shader-keyed: the template's (the same unless none had this one)
    blend = {0: 'normal', 1: 'add', 2: 'sub'}[p.field(em, 'blend_type')]

    # ---- texture
    img = images.get(smp['texture_id']) if smp else None
    if img is None:
        img = np.full((16, 16, 4), 255, np.uint8)
        notes.append('no texture: white')
    else:
        img = first_cell(img, e['static']['tex_scroll'][ti])
    shape, rgb, alpha = combine(img, e, notes)
    h, w = shape.shape
    tw, th = pow2(w, hi=TEX_MAX), pow2(h, hi=TEX_MAX)
    if (tw, th) != (w, h):
        shape = resize(shape[..., None].astype(np.float32), tw, th)[..., 0]
    r8 = (np.clip(shape, 0, 1) * 255 + 0.5).astype(np.uint8)
    p.set_texture(em, 0, np.stack([r8, r8, r8, np.full_like(r8, 255)], 2), 0x34)
    if smp:
        struct.pack_into('>I', em, ptcl.TEXRES + 0x0C,
                         WRAP.get(smp['wrap_u'], 0) << 28 | WRAP.get(smp['wrap_v'], 0) << 24 | 0x100)
    p.set_field(em, 'tex0_uv_scale', [1.0, 1.0])
    set_uv_anim(em, ts)

    # ---- blend, colour, alpha
    st, col = e['static'], e['color']
    p.set_field(em, 'blend_type', BLEND[blend])
    cks, secs = color_fit(rgb)
    for track in (0, 1):
        if p.field(em, 'color%d_type' % track) == 2:
            p.set_color_keys(em, track, [(*map(float, c), 1.0) for c in cks])
        else:
            p.set_color_keys(em, track, [(*map(float, rgb.mean(0)), 1.0)])
    p.set_field(em, 'color_section1', [secs[0]] * 2)
    p.set_field(em, 'color_section2', [secs[1]] * 2)
    p.set_field(em, 'color_section3', [secs[2]] * 2)
    p.set_field(em, 'color_repeat', [1, 1])
    p.set_field(em, 'color_scale', float(st['color_scale'] or 1.0))
    a0, a1, a2, s1, s2 = (float(np.squeeze(v)) for v in three_key(alpha))
    p.set_field(em, 'alpha_init', a0)
    p.set_field(em, 'alpha_diff21', a1 - a0)
    p.set_field(em, 'alpha_diff32', a2 - a1)
    p.set_field(em, 'alpha_section1', s1 / 100)
    p.set_field(em, 'alpha_section2', s2 / 100)

    # ---- scale
    sc = e['scale']
    curve = keys(st['scale_anim'], st['num_scale_keys'], 2)
    base = np.ones(2) if is_mesh is True else np.array([max(sc['scale'][0], 1e-4), max(sc['scale'][1], 1e-4)])
    peak = np.maximum(curve.max(0), 1e-4)
    v0, v1, v2, s1, s2 = three_key(curve / peak)
    p.set_field(em, 'scale', [float(b * m) for b, m in zip(base, peak)])
    p.set_field(em, 'scale_init_ratio', [float(v) for v in v0])
    p.set_field(em, 'scale_diff21', [float(v) for v in v1 - v0])
    p.set_field(em, 'scale_diff32', [float(v) for v in v2 - v1])
    p.set_field(em, 'scale_sections', [int(s1), int(s2)])
    p.set_field(em, 'scale_random', [min(1.0, sc['scale_random'][0] / 100), min(1.0, sc['scale_random'][1] / 100)])

    # ---- rotation
    p.set_field(em, 'rotation_init', [float(v) for v in st['rotate_init'][:3]])
    p.set_field(em, 'rotation_random', [float(v) for v in st['rotate_init_rand'][:3]])
    p.set_field(em, 'rotation_velocity', [float(v) for v in st['rotate_add']])
    p.set_field(em, 'rotation_velocity_random', [float(v) for v in st['rotate_add_rand'][:3]])

    # ---- shape and motion
    sh, vel, ems = e['shape'], e['velocity'], e['emission']
    vt = sh['volume_type'] if sh['volume_type'] <= 14 else 0
    p.set_field(em, 'volume_type', vt)
    p.set_field(em, 'volume_radius', [float(r * f) for r, f in zip(sh['volume_radius'], sh['volume_form_scale'])])
    p.set_field(em, 'figure_velocity', float(vel['all_direction']))
    d = np.array(vel['designated_dir'], float)
    n = np.linalg.norm(d)
    p.set_field(em, 'emit_direction', [float(v) for v in (d / n if n else np.array([0.0, 1.0, 0.0]))])
    p.set_field(em, 'emitter_velocity', float(vel['designated_dir_scale']))
    p.set_field(em, 'dispersion_angle', float(vel['diffusion_dir_angle']))
    p.set_field(em, 'init_velocity_random', min(1.0, vel['vel_random'] / 100))
    p.set_field(em, 'gravity', [float(ems['gravity_scale'] * g) for g in ems['gravity_dir']])
    p.set_field(em, 'air_resistance', float(st['air_res']))
    info = e['info']
    p.set_emitter_srt(em, tuple(info['scale']), tuple(info['rotate']), tuple(info['trans']))

    # ---- timing
    one = bool(ems['one_time'])
    if pt['infinite_life'] and not one:
        # a particle that lives until the effect ends (a held glow): emitted once (eft sizes the
        # buffer from life x rate / interval, unbounded for an endless emitter)
        one, ems = True, dict(ems, duration=1)
        notes.append('infinite life: emitted once')
    p.set_field(em, 'start_frame', int(ems['start']))
    p.set_field(em, 'end_frame', max(1, int(ems['duration'])) if one else FOREVER)
    p.set_field(em, 'one_time', 1 if one else 0)
    p.set_field(em, 'emit_start', 0)
    p.set_field(em, 'emit_interval', int(ems['interval']))
    p.set_field(em, 'emit_rate', float(max(ems['rate'], 0.01)))
    life = FOREVER if pt['infinite_life'] else max(1, int(pt['life']))
    p.set_field(em, 'ptcl_life', life)
    # turned off (Terminate_Graphic_Effect): eft2 fades the alpha over alpha_fade_time frames when
    # asked (and drops infinite-life particles); eft's 0x82C is that rate (1 / frames: vanilla's
    # infinite-life glows all have it), 0 lets them live on (test 33's glow outlived the move, and
    # templates carrying 1 cut neutral air's burst the frame it was turned off)
    info = e['info']
    fade = 1.0 / max(1, info['alpha_fade_time']) if info['is_fade_alpha_fade'] or life == FOREVER else 0.0
    struct.pack_into('>f', em, FADE_ALPHA, fade)
    p.set_field(em, 'ptcl_life_random', 0 if life == FOREVER else int(pt['life'] * pt['life_random'] / 100))
    if p.field(em, 'keyanim_size'):
        p.set_field(em, 'keyanim_size', 0)
    if e['children']:
        notes.append('%d child emitters not converted' % len(e['children']))
    if e['subsections']:
        notes.append('not converted: ' + ', '.join(sorted(e['subsections'])))
    n = buffer_count(p, em)
    if n > 4 * MAX_LIVE:
        # fewer particles a burst (eft sizes the emitter's buffer from it; vanilla stays far below)
        p.set_field(em, 'emit_rate', max(1.0, p.field(em, 'emit_rate') * 4 * MAX_LIVE / n))
        notes.append('buffer %d: rate lowered' % n)
    notes += sanitize(p, em)
    return em


def set_name(prefix, ult):
    return prefix + ult[len('P_Edge'):] if ult.startswith('P_Edge') else prefix + ult.replace('P_', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('eff')
    ap.add_argument('base_dir')
    ap.add_argument('out_dir')
    ap.add_argument('kind', type=lambda v: int(v, 0))
    ap.add_argument('ids')
    ap.add_argument('effects', nargs='*')
    ap.add_argument('--prefix', default='PtcEdge')
    ap.add_argument('--templates', nargs='*', default=[],
                    help='vanilla .ptcl files to take template emitters from (the base\'s own first)')
    a = ap.parse_args()
    eff = vfxb.Eff(a.eff)
    names, _ = eff.textures()
    images = eff.images()
    base = [f for f in os.listdir(a.base_dir) if f.endswith('.010d0000.ptcl')][0][:-len('.ptcl')]
    p = ptcl.Ptcl(open(os.path.join(a.base_dir, base + '.ptcl'), 'rb').read())
    ef = efc.Efc(open(os.path.join(a.base_dir, base + '.efc'), 'rb').read())
    templates = Templates(p, a.templates)
    prims, prim_index = eff.primitives(), {}
    ids, done = {}, {}
    for name in (a.effects or sorted(eff.effects)):
        si_ult = eff.effects[name]
        if si_ult in done:
            ids[name] = done[si_ult]
            continue
        made, log = [], []
        for e in eff.emitters(si_ult):
            notes = []
            em = convert_emitter(p, e, names, images, notes, templates, prims, prim_index)
            if em is not None:
                made.append((em, e['name']))
            log.append('    %-24s %s' % (e['name'], '; '.join(dict.fromkeys(notes))))
        if not made:
            print('%-30s %s: nothing convertible' % (name, eff.sets[si_ult]))
            print('\n'.join(log))
            continue
        if len(made) > MAX_EMITTERS:
            log.append('    %d emitters: the first %d kept' % (len(made), MAX_EMITTERS))
            made = made[:MAX_EMITTERS]
        sname = set_name(a.prefix, eff.sets[si_ult])
        si = p.new_set(sname, [m[0] for m in made], [m[1] for m in made])
        ids[name] = done[si_ult] = (0x300 + a.kind) << 16 | ef.add(si + 1)
        print('%-30s %-28s -> %-28s 0x%07X  %d emitters' % (name, eff.sets[si_ult], sname, ids[name], len(made)))
        print('\n'.join(log))
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(a.out_dir, base + '.efc'), 'wb').write(ef.build())
    old = json.load(open(a.ids)) if os.path.exists(a.ids) else {}
    old.update({k: '0x%07X' % v for k, v in ids.items()})
    json.dump(old, open(a.ids, 'w'), indent=1)
    print('%d effects -> %d sets; %s' % (len(ids), len(set(done.values())), a.ids))


if __name__ == '__main__':
    main()
