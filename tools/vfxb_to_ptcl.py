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
  billboard; 7 primitive as a billboard mesh; a type-3 mesh at rest as type 4; 5 / 6 as type 3,
  as type 4 on a mesh), blend and mesh-ness, plain shaders first, never one reading the screen,
  one that turns its particles (v_inRot) when they turn (a fixed turn no template draws is baked:
  a mesh's into its vertices, a quad's quarter turns into its texture);
- meshes (a primitive id): the VFXB's model (G3PR BFRES, tools/bfres_switch.py; first shape)
  written to the primitive table (Ptcl.add_primitive, once per id);
- texture: the first sampler that isn't an indirect / grade / noise / mask helper, its BNTX channel
  selection applied (tools/vfxb.py images), the flipbook cell its pattern table shows first
  (uv_div; shown_cell), its repeat (0x508), UV set (uv_channel); the sampler's wrap
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
SHAPE_SEL = 0x00000000          # a BC4 shape's channel selectors: R R R R
# eft's colour combiner (shader-keyed; read off the vanilla pixel shaders): 0 colour 0 (alpha from
# the texture's red), 1 colour 0 x texture (alpha from its alpha), 2 colour 1 + (colour 0 - colour 1)
# x texture (alpha from red)
COLOR_MODE = 0x314
# Ultimate custom shader (index, flag bit) whose colour goes out x its alpha shape x 2 (vfxb shader
# custom_shader_index / custom_shader_flag; Sephiroth's ef_edge.eff)
PREMULT_SHADER = (4, 64)
# eft2 vertex transform -> eft particle type (the same numbers: 0 billboard, 1 / 2 plate XY / XZ,
# 3 directional, 4 directional polygon, 8 Y billboard); 7 (primitive) as a billboard mesh. eft2's
# 5 / 6 "stripe" types carry no stripe settings (eft2's history ribbons are emitter plugins,
# EP01-EP04, on other types; 1825 + 289 type-5 / 6 emitters in 31 fighters' files have none), all
# move, and are scaled long (his speed lines 2.5 x 36): quads stretched along their motion, as
# eft's directional type 3. (eft's own stripes are complex emitters with a 0x34-byte history block.)
TYPES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 3, 6: 3, 7: 0, 8: 8}
TEX_MAX = 128           # vanilla effect textures are mostly 64-128 (the bank's size: Bayonetta's is 4.6 MB)
BASE_FIRST = 2          # a template of the base's own beats an imported one this much
# follow type (eft2's numbers: 0 follow the emitter, 1 not, 2 its position only): at emission
# (cross_f.rpx 0x04A5C89C, from the emitter's +0x12C = this) 0 points the particle at the emitter's
# live matrices, else copies them; shader-keyed (no vanilla shader group mixes values)
FOLLOW = 0x310
# slot 0's flipbook (cross_f.rpx 0x04A5A858 / 0x04A5A6AC, the emitter's uniforms; 0x04A54A88 the
# random start cell): 0x4D5 table used, 0x4D7 / 0x4D8 cells across / down, 0x4D9 random start cells,
# 0x4E0 32-byte table, 0x500 mode, 0x504 s16 frames a cell, 0x506 s16 cells (or table entries),
# 0x508 / 0x50C UV scale (1 / cells). The mode sets a shader feature bit (shader-keyed): 1 -> 0x4,
# 4 -> 0x8, 2 -> 0x10, 3 -> 0x20, 5 -> 0x10000000; in that bit order eft2's life-fit / clamp / loop /
# random, as vanilla's numbers agree (1 / 3 / 5 have no frame rate, 2 / 4 do: 4 plays once over the
# life, 2 loops: Bayonetta's bats)
PTN_MODE = 0x500
PTN_FROM_EFT2 = {1: 1, 2: 4, 3: 2, 4: 3}
UV_MODE = 0x510         # slot 0's UV animation (0x4D4 + 0x3C; the block below, docs/ptcl-format.md)
# the alpha an emitter loses a frame while its set fades (Terminate_Graphic_Effect), the emitter and
# its particles ending at 0; it climbs back to 1 otherwise (cross_f.rpx 0x04A64F00 / 0x04A661D8:
# emitter instance +0x58 -= / += this x the frame step)
FADE_ALPHA = 0x82C
# while its set fades, an emitter stops emitting only when this byte is set (0x04A65034: eft2's
# is_fade_emit); with it 0 and FADE_ALPHA 0 it emits on for good (test 37's speed lines)
FADE_EMIT = 0x2F9
# the eft sampler word: U wrap in bits 28-31, V in 24-27, the same codes as eft2's (0 mirror,
# 1 repeat, 2 clamp: vanilla's 2 x 2 repeats, quarter textures mirrored into a star, are all 0x0)
# eft2 texture repeat (tex_anim repeat) -> UV repeat; eft's 0x508 / 0x50C hold repeat / cells
REPEAT = {0: (1, 1), 1: (2, 1), 2: (1, 2), 3: (2, 2)}


# shaders that read the screen behind them (refraction: Zelda's Nayru's Love crystal, test 35's type-4
# templates, drew his sword glows and neutral air as see-through distortion; 56 of 1797 vanilla
# shaders) or texture arrays: never templates
SCREEN_SAMPLERS = (b'frameBufferTexture_CROSS', b'depthBufferTexture_CROSS', b'textureArraySampler')
# a particle's rotation is shader-keyed: the vertex program turns it from this attribute, and a
# shader without it draws every particle unturned (vanilla: all 3165 emitters with a rotation have
# it; down air's flares, turned -90 degrees in Ultimate, lay across the plunge as crosses)
ROTATION_ATTR = b'v_inRot'
# what an emitter's rotation needs of a template: none; a fixed one the converter can bake (a mesh's
# into its vertices, a quad's quarter turns about Z into its texture); one only a turning shader draws
ROT_NONE, ROT_FIXED, ROT_ANIMATED = 0, 1, 2
# eft's directional type (3) comes in two shader kinds: one aligns the particle with its own velocity
# (this attribute; 535 of 1732 vanilla type-3 emitters), the other with its change in world
# position (v_inWldPosDf), which on a following emitter includes the bone's motion. Ultimate aligns
# with the velocity: down smash's speed lines, slow (0.1) on the swinging sword, stood across the
# blade as a 23 x 180 bar (test 46); in Ultimate they lie along it. No emitter byte selects it alone
VELOCITY_ATTR = b'v_inVec'


class Templates:
    """template emitters by (eft particle type, blend 0 / 1 / 2, mesh): simple emitters with one BC4
    texture (slot 0; slots 1 / 2 unused). Among them, in this order: a plain shader (no shader
    parameters: Ike's FS cloud shader, FinIkeCloud FNSmoke with 32 bytes of them, tinted Sephiroth's
    meshes orange), the UV animation the emitter needs (slot 0's mode word 0x510: 1 scroll, 2
    scale, 4 rotate; shader-keyed: 8 of 4291 vanilla shader groups mix values) or more, the follow
    type (FOLLOW; ranked before the UV mode: a glow left behind by the sword shows more), then
    animated colour tracks
    (2 / 2, then 2 / x) and the base's own (no import); others are imported from the corpus
    (Ptcl.import_emitter: their shader, shader parameters and textures copied). Shaders reading the
    screen or texture arrays (SCREEN_SAMPLERS) are left out."""

    def __init__(self, base, corpus):
        self.base, self.files, self.found = base, {}, {}
        for path in [None] + list(corpus):
            p = base if path is None else ptcl.Ptcl(open(path, 'rb').read())
            if path is not None:
                self.files[path] = p
            screen = {}
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
                    si_ = struct.unpack_from('>I', em, 0x844)[0]
                    if si_ not in screen:
                        b = p.shader_binary(si_)
                        screen[si_] = (any(t in b for t in SCREEN_SAMPLERS), ROTATION_ATTR in b, VELOCITY_ATTR in b)
                    if screen[si_][0]:
                        continue
                    traits = (not p.field(em, 'shader_param_size'), struct.unpack_from('>I', em, UV_MODE)[0] & 7,
                              struct.unpack_from('>I', em, FOLLOW)[0], struct.unpack_from('>I', em, PTN_MODE)[0],
                              screen[si_][1], screen[si_][2])
                    self.found.setdefault(key, {})
                    if traits not in self.found[key] or score > self.found[key][traits][0]:
                        self.found[key][traits] = (score, path, si, k)

    def get(self, typ, blend, mesh, uv_mode, follow, ptn, rot, notes):
        """the best template for this particle type / blend / mesh-ness, follow type, flipbook mode
        (eft's, 0 none), rotation (ROT_*) and UV mode bits; another blend (add), then type 0, when
        there's none. A template with another flipbook mode than wanted is never taken when one
        without is there. A rotation the converter can bake (ROT_FIXED) ranks after the UV mode,
        which it can't (only freeze); one it can't, before"""
        def rank(item):
            (plain, mode, fol, pm, turns, by_vel), (score, *_r) = item
            # position-only (2) is rare in vanilla: following fully keeps up with a moving bone too
            # a mesh's UV animation first even so: freezing it bakes the mesh again (his slash arcs'
            # glows: four 240 KB copies), and its starting rotation bakes into the one copy
            return (plain, pm in (ptn, 0), fol == follow, turns or rot != ROT_ANIMATED or mesh,
                    by_vel or typ != 3, follow == 2 and fol == 0, pm == ptn, mode & uv_mode == uv_mode, mode == uv_mode,
                    turns or rot == ROT_NONE, turns == (rot != ROT_NONE), score)
        for key in ((typ, blend, mesh), (typ, 1, mesh), (0, blend, mesh), (0, 1, mesh)):
            if key not in self.found:
                continue
            (plain, mode, fol, pm, turns, by_vel), (_score, path, si, k) = max(self.found[key].items(), key=rank)
            if key != (typ, blend, mesh):
                notes.append('no template (type %d blend %d%s): type %d blend %d' % (
                    typ, blend, ' mesh' if mesh else '', key[0], key[1]))
            if fol != follow:
                notes.append('follow %d: template has %d' % (follow, fol))
            if mode & uv_mode != uv_mode:
                notes.append('UV animation %d: template has %d' % (uv_mode, mode))
            if pm != ptn:
                notes.append('flipbook mode %d: template has %d (one cell shown)' % (ptn, pm))
            if key[0] == 3 and not by_vel:
                notes.append('directional by world motion: template has no v_inVec')
            if rot == ROT_ANIMATED and not turns:
                notes.append('rotation: template has none' + (' (the spin lost)' if mesh else ''))
            if path is None:
                em = self.base.emitter_bytes(si, k)
                struct.pack_into('>II', em, 0x2CC, 0, 0)
                return em, turns
            return self.base.import_emitter(self.files[path], si, k, skip_slots=(0,)), turns
        raise KeyError((typ, blend, mesh))


def mesh(model, uv_channel=0):
    """(pos, nrm, col, uv, idx) of a BFRES model's first shape. Every vanilla primitive has normals
    (825 of them; 106 have no colour): missing ones are +Z; an all-white colour is left out. The UV
    set the texture reads (eft2's uv_channel) comes first"""
    shp = model['shapes'][0]
    a = model['vertex_buffers'][shp['vertex_buffer']]['attrs']
    n = len(a['_p0'])
    uv0 = a.get('_u0', np.zeros((n, 2), np.float32))[:, :2]
    uv1 = a.get('_u1', uv0)[:, :2]
    if uv_channel == 1:
        uv0, uv1 = uv1, uv0
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


def sampler_channel(e, i, img):
    """the channel eft2 takes a sampler's alpha from (combiner tex_alpha_input: 1 red; Ultimate's
    flares are opaque, their round shape in red), 0-1"""
    f = img.astype(np.float32) / 255
    return f[..., 0] if e['combiner']['tex_alpha_input'][i] == 1 else f[..., 3]


def shape_sampler(e, ti, images, notes):
    """(sampler, alpha factor): the sampler that holds the piece's shape when the one main_texture
    picked is a tiling fill. eft2 multiplies its textures (combiner blends 0); his auras / fire /
    smoke (the throws, dash attack, Shadow Flare) put a tiling fire / noise (edges 0.13-0.45) first and
    the shape (edges 0) second or third: drawn from the first alone each was a tinted rectangle up
    to 16 units across (test 47: "lights most of the stage"). The fill is folded in as its mean"""
    cb = e['combiner']
    if any(cb[k] for k in ('tex1_color_blend', 'tex2_color_blend', 'tex1_alpha_blend', 'tex2_alpha_blend')):
        return ti, 1.0
    stats = {}
    for i, s in enumerate(e['sampler']):
        img = images.get(s['texture_id']) if s['texture_id'] != NONE64 else None
        if img is None:
            continue
        c = sampler_channel(e, i, img)
        border = np.concatenate([c[0], c[-1], c[:, 0], c[:, -1]])
        stats[i] = (float(border.mean()), float(c.mean()))
    if ti not in stats or len(stats) < 2 or stats[ti][0] < 0.1:
        return ti, 1.0
    shaped = [i for i, (edge, mean) in stats.items() if edge < 0.05 and mean > 0.01]
    if not shaped:
        return ti, 1.0
    best = shaped[0]
    factor = float(np.prod([mean for i, (edge, mean) in stats.items() if edge >= 0.1]))
    notes.append('shape from sampler %d (sampler %d a fill: x %.2f)' % (best, ti, factor))
    return best, factor


def wrap_uv(t, mode):
    """eft2 / eft wrap codes: 0 mirror, 1 repeat, 2 clamp"""
    if mode == 2:
        return np.clip(t, 0, 1 - 1e-6)
    if mode == 0:
        t = np.mod(t, 2)
        return np.clip(np.where(t > 1, 2 - t, t), 0, 1 - 1e-6)
    return np.mod(t, 1)


def bake_samplers(e, ti, img, ptn, images, names, notes):
    """img (the main sampler's picture: one cell, or the whole sheet of a flipbook) with the
    emitter's other samplers multiplied into the channel its shape is read from, each sampled as
    Ultimate places it on the quad (its repeat, starting scale / shift / turn, wrap; a flipbook's
    first cell): eft2 multiplies its textures (combiner blends 0). Smash 4's templates draw one
    texture, so his fire / aura / smoke (a flipbook or a mask times a tiling noise times a square
    fade) drew as one flat shape; now the product, frozen at its start (the other samplers' scroll
    is lost). Distortion maps ('indirect': they move the picture) are left out. None when nothing
    is multiplied"""
    cb = e['combiner']
    if any(cb[k] for k in ('tex1_color_blend', 'tex2_color_blend', 'tex1_alpha_blend', 'tex2_alpha_blend')):
        return None
    others = [(j, s) for j, s in enumerate(e['sampler']) if j != ti and s['texture_id'] != NONE64
              and s['texture_id'] in images and 'indirect' not in names.get(s['texture_id'], '')]
    if not others:
        return None
    out = img.astype(np.float32).copy()
    am = cb['alpha_process']
    ch = 0 if am in (2, 3) or cb['tex_alpha_input'][ti] == 1 else 3
    nx, ny = ((max(1, int(round(v))) for v in e['static']['tex_scroll'][ti]['uv_div']) if ptn else (1, 1))
    h, w = out.shape[0] // ny, out.shape[1] // nx
    yy, xx = np.mgrid[0:h, 0:w]
    quad = np.stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h], 1).astype(np.float32)
    product = np.ones(h * w, np.float32)
    for j, s in others:
        ts = e['static']['tex_scroll'][j]
        src = first_cell(images[s['texture_id']], ts, shown_cell(e, j))
        c = sampler_channel(e, j, src)
        uv = uv_transform(quad * np.array(REPEAT.get(e['tex_anim'][j]['repeat'], (1, 1)), np.float32),
                          ts['scale'], ts['scroll'], ts['rotation'])
        sh, sw = c.shape
        product *= c[(wrap_uv(uv[:, 1], s['wrap_v']) * sh).astype(int), (wrap_uv(uv[:, 0], s['wrap_u']) * sw).astype(int)]
    product = product.reshape(h, w)
    for cy in range(ny):
        for cx in range(nx):
            out[cy * h:(cy + 1) * h, cx * w:(cx + 1) * w, ch] *= product
    notes.append('samplers %s multiplied in' % ','.join(str(j) for j, _s in others))
    return np.clip(out, 0, 255).astype(np.uint8)


def first_cell(img, scroll, cell=0):
    """a flipbook's cell (row-major, uv_div columns x rows)"""
    nx, ny = (int(round(v)) if v and v >= 1 else 1 for v in scroll['uv_div'])
    h, w = img.shape[:2]
    ch, cw = max(4, h // ny), max(4, w // nx)
    cy, cx = divmod(int(cell) % (nx * ny), nx)
    return img[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw]


def shown_cell(e, ti):
    """the flipbook cell to show (eft's flipbooks aren't converted): the first one Ultimate's
    pattern animation plays (its table's first entry; e.g. neutral air's impact rings start at cell
    1, cell 0 being the full solid shape)"""
    if not e['tex_anim'][ti]['pattern_type']:
        return 0
    tp = e['static']['tex_pat'][ti]
    return tp['table'][0] if tp['num'] else 0


LUMA = np.array([0.299, 0.587, 0.114])


def track(st, col, n):
    """colour track n (0 / 1) over the particle's life [101, 3] and alpha track n [101]"""
    c = keys(st['color%d' % n], st['num_color%d_keys' % n]) if col['color%d_type' % n] == 2 else \
        np.tile(np.array(col['color%d' % n][:3], float), (101, 1))
    a = keys(st['alpha%d' % n], st['num_alpha%d_keys' % n], 1)[:, 0] if col['alpha%d_type' % n] == 2 else \
        np.full(101, float(col['color%d' % n][3]))
    return c, a


def combine(img, e, notes, ti=0, fill=1.0):
    """eft2's combiner on the main texture, folded into what a one-colour eft template draws (a BC4
    shape x the particle colour): (shape [h, w] 0-1, colour [101, 3], alpha [101]).
    Colour modes (combiner color_process): 0 colour 0; 1 colour 0 x texture; 2 colour 0 x texture +
    colour 1 x (1 - texture); 3 colour 0 x texture + colour 1. Each pixel's colour at the tracks' life
    means, weighted by the texture's alpha: their mean is the particle colour, each pixel's
    brightness against it the shape (the hue across the texture is lost, its brightness kept); the
    colour over life is the same mix of the tracks at the texture's mean. Alpha modes (alpha_process):
    0 / 1 texture alpha x alpha 0 (1 erodes the texture by alpha 0: a fade by the ink left), 2 / 3 the
    same with the texture's red, 4 texture alpha x alpha 0 x alpha 1.
    Custom shader 4 with flag 64 (PREMULT_SHADER: his dark fire / aura, read off its Maxwell code in
    the file's BNSH, all 13 of them; flags 32 / 1, his smoke / planes, and the 125 shader_type 2
    emitters without a custom shader don't): the colour is the tracks' mix by the alpha shape, not
    the texture's colour (0: colour 0;
    2: colour 1 + (colour 0 - colour 1) x shape), and goes out x the shape x 2 before blending (which
    multiplies by it again): a mostly faint shape (ef_cmn_fire00) draws dark, his black flames. Then
    the shape is the alpha shape and the 4th value the shape's mean (the colour isn't x 2 yet: the
    template's colour mode decides how the x shape is drawn); else None."""
    st, col, cb, info = e['static'], e['color'], e['combiner'], e['info']
    c0, a0 = track(st, col, 0)
    c1, a1 = track(st, col, 1)
    c0 = c0 * np.array(info['color0'][:3])
    c1 = c1 * np.array(info['color1'][:3])
    f = img.astype(np.float32) / 255
    rgb = f[..., :3]
    am = cb['alpha_process']
    atex = f[..., 0] if am in (2, 3) or cb['tex_alpha_input'][ti] == 1 else f[..., 3]
    cm = cb['color_process']
    m0, m1 = c0.mean(0), c1.mean(0)
    premult = None
    sh = e['shader']
    if (sh['custom_shader_index'], sh['custom_shader_flag'] & PREMULT_SHADER[1]) == PREMULT_SHADER:
        premult = float((atex * atex).sum() / max(float(atex.sum()), 1e-6))
        k = premult if cm in (2, 3) else 1.0
        colour = c0 * k + c1 * ((1 - k) if cm == 2 else 1.0 if cm == 3 else 0.0)
        shape = atex
        notes.append('custom shader: colour by the shape (%.2f), x the shape x 2' % premult)
    else:
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
    alpha = a0 * info['color0'][3] * (a1 * info['color1'][3] if am == 4 else 1.0) * fill
    if am in (1, 3):
        # erosion: each pixel is texture - (1 - alpha), so the faint parts go first and the bright
        # strokes last (the texture can't change over life here): the fade kept is the texture's
        # remaining ink against its full ink
        t = atex[::max(1, atex.shape[0] // 64), ::max(1, atex.shape[1] // 64)].ravel()
        ink = max(float(t.sum()), 1e-6)
        alpha = np.array([np.clip(t - (1 - a), 0, 1).sum() / ink for a in np.clip(alpha, 0, 1)])
        notes.append('alpha erosion: fade by the remaining ink')
    return shape, np.clip(colour, 0, None), np.clip(alpha, 0, 1), premult


def eft_rotation(rot):
    """eft2's emitter rotation (radians, applied Z then Y then X: R = Rx Ry Rz) as eft's angles
    (applied X then Y then Z: R = Rz Ry Rx, Ptcl.set_emitter_srt). eft2's order, from 86 streak
    emitters (types 5 / 6 moving along a designated direction, rotated about 2+ axes) in 31
    fighters' VFXBs: their offset lies across their motion in 53 with Z first (13 with X first),
    along it in 10 (51): layered speed lines side by side, not one behind the other. Sephiroth's
    forward-air lines (90, 0, 90 degrees) ran along their own offset (test 43: "the wrong plane")"""
    a, b, c = (float(v) for v in rot[:3])
    if sum(abs(v) > 1e-6 for v in (a, b, c)) < 2:
        return a, b, c
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    r = (np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
         @ np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]))
    y = math.asin(max(-1.0, min(1.0, -r[2, 0])))
    if abs(r[2, 0]) < 1 - 1e-6:
        x, z = math.atan2(r[2, 1], r[2, 2]), math.atan2(r[1, 0], r[0, 0])
    else:                                                   # gimbal lock: all of it in x
        x, z = math.atan2(-r[1, 2], r[1, 1]), 0.0
    return x, y, z


def crossed_ribbon(pos, nrm, col, uv, idx, notes):
    """a flat ribbon along Y (his sword glows: 25.5 long, 2 wide, ~0 thick) with a copy turned 90
    degrees about Y. Ultimate's directional type keeps such a mesh facing the camera round its Y
    (the glow shows along the blade in every move); held in the sword's frame it went edge-on at
    some rolls (test 47: forward air without a glow). Crossed, one of the two always faces it"""
    span = pos.max(0) - pos.min(0)
    if span[1] <= 0 or min(span[0], span[2]) > 0.1 * span[1] or max(span[0], span[2]) > 0.3 * span[1]:
        return pos, nrm, col, uv, idx
    turn = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], np.float32)
    notes.append('ribbon crossed')
    idx = np.asarray(idx).reshape(-1)
    return (np.concatenate([pos, pos @ turn.T]), np.concatenate([nrm, nrm @ turn.T]),
            None if col is None else np.concatenate([col, col]), np.concatenate([uv, uv]),
            np.concatenate([idx, idx + len(pos)]))


def radial_gradient(shape, notes, n=64):
    """a one-way gradient (Ultimate's ef_cmn_grade00: bright at V 0, gone by V 0.4; the same in every
    column) read outward from the centre. The flare meshes read it so (their UVs polar: V the radius);
    on a quad it was a lit square (the pummel's / down throw's pointlight1: test 49's pink diamond)"""
    if shape.shape[0] < 4 or shape.shape[1] < 4:
        return shape
    for prof, flat in ((shape.mean(1), shape.std(1).max()), (shape.mean(0), shape.std(0).max())):
        if flat < 0.02 and prof.max() - prof.min() > 0.5:
            yy, xx = np.mgrid[0:n, 0:n] + 0.5
            r = np.clip(np.hypot(xx - n / 2, yy - n / 2) / (n / 2), 0, 1)
            if prof[0] < prof[-1]:
                prof = prof[::-1]
            # to 0 at the rim (grade00's dark end is ~0.1: a faint lit square on a bright piece)
            prof = np.clip((prof - prof[-1]) / max(float(prof[0] - prof[-1]), 1e-6), 0, 1) * prof[0]
            notes.append('gradient on a quad: read from the centre')
            return np.interp(r, np.linspace(0, 1, len(prof)), prof).astype(np.float32)
    return shape


def rotation_need(st, is_mesh):
    """ROT_NONE / ROT_FIXED / ROT_ANIMATED for an emitter's particle rotation"""
    init, rand, add = st['rotate_init'][:3], st['rotate_init_rand'][:3], st['rotate_add'][:3]
    if not any(abs(v) > 1e-6 for v in init + rand + add):
        return ROT_NONE
    if any(abs(v) > 1e-6 for v in rand + add):
        return ROT_ANIMATED
    return ROT_FIXED if is_mesh or fixed_quarter_turn(st) else ROT_ANIMATED


def rotation_matrix(rot):
    """eft's particle rotation (radians): Y, then Z, then X (R = Rx Rz Ry, column vectors; a turning
    mesh shader's vertex program builds it from v_inRot so, its x column scaling the position's x:
    the emitter's own order, X Y Z, differs)"""
    a, b, c = rot
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return (np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]) @ np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]])
            @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]))


def fixed_quarter_turn(st):
    """a particle turned a fixed whole number of quarter turns about Z (no other axis, no random or
    spin): that number, 1-3 (counter-clockwise), else None"""
    x, y, z = (float(v) for v in st['rotate_init'][:3])
    if abs(x) > 1e-3 or abs(y) > 1e-3 or any(abs(v) > 1e-6 for v in st['rotate_init_rand'][:3] + st['rotate_add'][:3]):
        return None
    q = z / (math.pi / 2)
    if abs(q - round(q)) > 1e-3:
        return None
    return int(round(q)) % 4 or None


def uv_mode(ts):
    """the UV animation bits (1 scroll, 2 scale, 4 rotate) a sampler's eft2 UV parameters need"""
    if ts is None:
        return 0
    nz = lambda v: any(abs(x) > 1e-6 for x in (v if isinstance(v, list) else [v]))  # noqa: E731
    return (1 if nz(ts['scroll']) or nz(ts['scroll_add']) or nz(ts['scroll_random']) else 0) \
        | (2 if nz([x - 1 for x in ts['scale']]) or nz(ts['scale_add']) or nz(ts['scale_random']) else 0) \
        | (4 if nz(ts['rotation']) or nz(ts['rotation_add']) or nz(ts['rotation_random']) else 0)


# How each game moves a texture (slot 0), from where the clamped, shifted meshes of each game's own
# effects land on their texture over their life (scratch tests: Smash 4's 117 vanilla files, 375
# clamped shifted axes; Ultimate's 31 fighters' VFXBs, 1700): Smash 4 uv x scale + shift (373 of
# 375 partly on the texture), Ultimate uv x scale - shift (1652 of 1700; centred or added forms
# 1183-1277); both turn about the texture's centre (Smash 4 20 of 20 clamped turned ones, Ultimate
# 223 of 224). Ultimate's back-air arc, a disc, only sweeps round as a crescent so. The shifts
# change sign on the way.
def uv_transform(uv, scale, scroll, rotation):
    """eft2's starting UV transform (repeat already applied): uv x scale - shift, turned about the
    texture's centre"""
    c, s = math.cos(rotation), math.sin(rotation)
    q = uv * np.array(scale, np.float32) - np.array(scroll, np.float32) - 0.5
    return (np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], 1) + 0.5).astype(np.float32)


def set_flipbook(em, ptn, ts, tp, rep=(1, 1)):
    """slot 0's flipbook from eft2's pattern animation (PTN_MODE); ptn 0: none (one cell shown,
    first_cell). Cells across / down from eft2's uv_div, the UV scale repeat / cells, its table (eft2's
    num entries of it), frames a cell (frequency) and random start cells (num_random)"""
    struct.pack_into('>I', em, PTN_MODE, ptn)
    if not ptn:
        return
    nx, ny = (max(1, int(round(v))) for v in ts['uv_div'])
    num = int(tp['num']) if tp['num'] else nx * ny
    em[0x4D5] = 1 if tp['num'] else 0
    em[0x4D7], em[0x4D8] = nx, ny
    em[0x4D9] = max(1, int(tp['num_random']))
    em[0x4E0:0x500] = bytes(min(255, max(0, int(v))) for v in tp['table'][:32])
    struct.pack_into('>hh', em, 0x504, max(1, int(round(tp['frequency']))) if ptn in (2, 4) else 0, num)
    struct.pack_into('>2f', em, 0x508, rep[0] / nx, rep[1] / ny)


def set_uv_anim(em, ts):
    """eft2's UV parameters (shift / scale / rotation: initial, random, per frame) -> slot 0's eft
    block: 0x510 mode (bits 1 / 2 / 4; the template's, at least the bits needed), 0x514 scroll a
    frame, 0x51C scroll init, 0x524 scroll random, 0x52C scale a frame, 0x534 scale init, 0x53C
    scale random, 0x544 rotation a frame, 0x548 rotation init, 0x54C rotation random (the vanilla
    corpus: each mode bit set exactly where those values are). Unused ones are left neutral. The
    shifts change sign (eft adds them, eft2 subtracts: above)."""
    if ts is None:
        ts = {'scroll': [0, 0], 'scroll_add': [0, 0], 'scroll_random': [0, 0], 'scale': [1, 1],
              'scale_add': [0, 0], 'scale_random': [0, 0], 'rotation': 0, 'rotation_add': 0, 'rotation_random': 0}
    struct.pack_into('>2f', em, 0x514, *(-v for v in ts['scroll_add']))
    struct.pack_into('>2f', em, 0x51C, *(-v for v in ts['scroll']))
    struct.pack_into('>2f', em, 0x524, *ts['scroll_random'])
    struct.pack_into('>2f', em, 0x52C, *ts['scale_add'])
    struct.pack_into('>2f', em, 0x534, *ts['scale'])
    struct.pack_into('>2f', em, 0x53C, *ts['scale_random'])
    struct.pack_into('>3f', em, 0x544, ts['rotation_add'], ts['rotation'], ts['rotation_random'])


def convert_emitter(p, e, names, images, notes, templates, prims, prim_index):
    pt = e['particle']
    if e['combiner']['shader_type'] == 1:
        # a refraction piece (it bends the picture behind it: back throw's indirect1, the entry's
        # rifrection1): no template reads the screen (SCREEN_SAMPLERS), and drawn plain its
        # normal-map texture is a tinted blob
        notes.append('refraction: skipped')
        return None
    typ = TYPES.get(pt['billboard_type'])
    if typ is None:
        notes.append('billboard type %d: skipped' % pt['billboard_type'])
        return None
    is_mesh = pt['primitive_id'] != NONE64
    if is_mesh and pt['primitive_id'] not in prims:
        notes.append('primitive %d not in the file: skipped' % pt['primitive_id'])
        return None
    vel = e['velocity']
    rest_dir = False
    if is_mesh and typ == 3 and abs(vel['all_direction']) + abs(vel['designated_dir_scale']) < 1e-3:
        # a directional mesh at rest (his sword glows, slash arcs) lies in the emitter's frame in
        # Ultimate; eft's directional type 3 turns it by its (zero) velocity (test 32: the up-air arc
        # lay flat), type 4 keeps the emitter's frame at rest (Zelda's Nayru's Love crystals)
        typ = 4
        rest_dir = True
        notes.append('directional mesh at rest: type 4')
    elif is_mesh and pt['billboard_type'] in (5, 6):
        # a "stripe" mesh (no ribbon data: its shape is the mesh) keeps the emitter's frame: neutral
        # air's rainbow1, a flat 69-unit disc laid level (emitter X 90) and sent off in a random
        # direction, faced its motion as type 3 (test 43-44's purple disc; Ultimate shows none)
        typ = 4
        notes.append('stripe mesh: type 4')
    blend = {0: 'normal', 1: 'add', 2: 'sub'}.get(e['render']['blend_type'], 'add')
    ti, smp = main_texture(e, names)
    fill = 1.0
    if smp:
        ti, fill = shape_sampler(e, ti, images, notes)
        smp = e['sampler'][ti]
    ts = e['static']['tex_scroll'][ti] if smp else None
    uv_quarter = 0
    if ts is not None and pt['primitive_id'] == NONE64 and uv_mode(ts) == 4 and not ts['rotation_add'] \
            and not ts['rotation_random']:
        # a quad's texture turned a fixed number of quarter turns (and nothing else): turned in the
        # image, so no template needs UV rotation (down smash's speed lines, Octaslash's lines)
        q = ts['rotation'] / (math.pi / 2)
        if abs(q - round(q)) < 1e-3:
            uv_quarter = int(round(q)) % 4
            ts = dict(ts, rotation=0.0)
    ptn_want = PTN_FROM_EFT2.get(e['tex_anim'][ti]['pattern_type'], 0) if smp else 0
    if ptn_want and all(int(round(v or 1)) <= 1 for v in e['static']['tex_scroll'][ti]['uv_div']):
        # a one-cell sheet plays nothing; as a flipbook its UV scale (1 / cells) would replace the
        # repeat (forward air's X, a quarter texture repeated 2 x 2 mirrored, drew one quarter from
        # test 39 on: a ">" at the blade tip)
        ptn_want = 0
    tp = e['static']['tex_pat'][ti] if smp else None
    st = e['static']
    # a directional mesh at rest keeps no particle rotation: his slash arcs (all turned Z 180,
    # their glows Y -20 too, spinning) looked right unturned (test 36: back / up air "nearly
    # right") and wrong turned (tests 44 / 45: the arc a whole disc, behind him too). Ultimate's
    # directional basis at rest evidently undoes it (his sword glows, unturned, extend along +Y,
    # so it isn't a plain flip of every such mesh); not derived, only observed
    rot = ROT_NONE if rest_dir else rotation_need(st, is_mesh)
    em, turns = templates.get(typ, BLEND[blend], is_mesh, uv_mode(ts), e['info']['follow_type'], ptn_want, rot, notes)
    # a rotation no template draws: baked (a quad's fixed quarter turns; a mesh's starting rotation)
    baked_rot = rot != ROT_NONE and not turns and (is_mesh or rot == ROT_FIXED)
    quarter = fixed_quarter_turn(st) if baked_rot and not is_mesh else None
    mesh_rot = tuple(float(v) for v in st['rotate_init'][:3]) if baked_rot and is_mesh else None
    if mesh_rot and not any(abs(v) > 1e-6 for v in mesh_rot):
        mesh_rot = None
    ptn = ptn_want if ptn_want and struct.unpack_from('>I', em, PTN_MODE)[0] == ptn_want else 0
    repeat = REPEAT.get(e['tex_anim'][ti]['repeat'], (1, 1)) if smp else (1, 1)
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
            bake = (repeat, tuple(ts['scale']), tuple(ts['scroll']), ts['rotation'])
            repeat = (1, 1)
            notes.append('UV transform baked into the mesh')
        channel = e['tex_anim'][ti]['uv_channel'] if smp else 0
        key = (pt['primitive_id'], s3, bake, channel, mesh_rot, rest_dir)
        if key not in prim_index:
            pos, nrm, col_, uv, idx = mesh(prims[pt['primitive_id']], channel)
            if rest_dir:
                pos, nrm, col_, uv, idx = crossed_ribbon(pos, nrm, col_, uv, idx, notes)
            if bake:
                uv = np.concatenate([uv_transform(uv[:, :2] * np.array(bake[0], np.float32), *bake[1:]),
                                     uv[:, 2:]], 1)
            pos = pos * np.array(s3, np.float32)
            if mesh_rot:
                # as a turning template would (rotation_matrix), the particle's scale first
                r = rotation_matrix(mesh_rot).astype(np.float32)
                pos, nrm = pos @ r.T, nrm @ r.T
                notes.append('rotation baked into the mesh')
            prim_index[key] = p.add_primitive(pos, nrm, col_, uv, idx)
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
        if not ptn:
            img = first_cell(img, e['static']['tex_scroll'][ti], shown_cell(e, ti))
        if not is_mesh:
            baked = bake_samplers(e, ti, img, ptn, images, names, notes)
            if baked is not None:
                img, fill = baked, 1.0
    shape, rgb, alpha, premult = combine(img, e, notes, ti, fill)
    if not is_mesh:
        shape = radial_gradient(shape, notes)
    if uv_quarter:
        # eft2 samples at R(rotation) (uv - 0.5) + 0.5: the picture turns counter-clockwise as shown
        shape = np.ascontiguousarray(np.rot90(shape, uv_quarter))
        notes.append('UV rotation: %d quarter turn(s) baked into the texture' % uv_quarter)
    if quarter:
        # no template turns this quad: a fixed quarter turn goes into the texture (and the scale)
        shape = np.ascontiguousarray(np.rot90(shape, quarter))
        notes.append('rotation: %d quarter turn(s) baked into the texture' % quarter)
    h, w = shape.shape
    # a whole flipbook sheet of 4+ cells a side gets twice the size, cells keeping 64 px
    grid = max(int(round(v)) for v in e['static']['tex_scroll'][ti]['uv_div']) if ptn else 1
    tmax = TEX_MAX * 2 if grid >= 4 else TEX_MAX
    tw, th = pow2(w, hi=tmax), pow2(h, hi=tmax)
    if (tw, th) != (w, h):
        shape = resize(shape[..., None].astype(np.float32), tw, th)[..., 0]
    # smooth textures (glows, gradients) at half size while that changes them by under 1% (the
    # bank's size: test 37's 6.0 MB loaded)
    while min(tw, th) > 16:
        half = resize(shape[..., None].astype(np.float32), tw // 2, th // 2)
        back = resize(half, tw, th)[..., 0]
        if float(np.abs(back - shape).mean()) > 0.01 * max(float(shape.mean()), 0.05):
            break
        shape, tw, th = half[..., 0], tw // 2, th // 2
    r8 = (np.clip(shape, 0, 1) * 255 + 0.5).astype(np.uint8)
    # the shape in every channel (selectors R R R R): most templates' pixel shaders take alpha from
    # red, some from alpha (Koopa's pointlight1 / Pikachu's spark1, picked for the hand / throw auras
    # and back throw's aura2), which with vanilla's R R R 1 drew the whole quad (test 52's colour
    # check: back throw's yellow square, the grab's purple one)
    p.set_texture(em, 0, np.stack([r8, r8, r8, np.full_like(r8, 255)], 2), 0x34, comp_sel=SHAPE_SEL)
    if smp:
        struct.pack_into('>I', em, ptcl.TEXRES + 0x0C, (smp['wrap_u'] & 0xF) << 28 | (smp['wrap_v'] & 0xF) << 24 | 0x100)
    p.set_field(em, 'tex0_uv_scale', [float(v) for v in repeat])
    set_uv_anim(em, ts)
    set_flipbook(em, ptn, e['static']['tex_scroll'][ti] if smp else None, tp, repeat)

    # ---- blend, colour, alpha
    st, col = e['static'], e['color']
    p.set_field(em, 'blend_type', BLEND[blend])
    black1 = False
    if premult is not None:
        # the custom shader's colour x shape x 2: the shape is in every channel (SHAPE_SEL), so a
        # template whose colour mode (COLOR_MODE) takes the texture draws the x shape per pixel
        # (1: colour 0 x texture; 2: colour 1 + (colour 0 - colour 1) x texture, colour 1 black);
        # one that doesn't (0: colour 0) gets the shape's mean
        mode = struct.unpack_from('>I', em, COLOR_MODE)[0]
        rgb = rgb * 2 * (premult if mode == 0 else 1.0)
        black1 = mode == 2
        notes.append('template colour mode %d' % mode)
    cks, secs = color_fit(rgb)
    for track in (0, 1):
        if black1 and track == 1:
            p.set_color_keys(em, track, [(0.0, 0.0, 0.0, 1.0)] * (len(cks) if p.field(em, 'color1_type') == 2 else 1))
        elif p.field(em, 'color%d_type' % track) == 2:
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
    xy = (lambda v: [v[1], v[0]]) if quarter in (1, 3) else (lambda v: list(v))
    p.set_field(em, 'scale', xy([float(b * m) for b, m in zip(base, peak)]))
    p.set_field(em, 'scale_init_ratio', xy([float(v) for v in v0]))
    p.set_field(em, 'scale_diff21', xy([float(v) for v in v1 - v0]))
    p.set_field(em, 'scale_diff32', xy([float(v) for v in v2 - v1]))
    p.set_field(em, 'scale_sections', [int(s1), int(s2)])
    p.set_field(em, 'scale_random', xy([min(1.0, sc['scale_random'][0] / 100), min(1.0, sc['scale_random'][1] / 100)]))

    # ---- rotation
    # (a template that doesn't turn: none, as vanilla's; what could be baked was)
    unturned = rest_dir or (rot != ROT_NONE and not turns)
    p.set_field(em, 'rotation_init', [0.0] * 3 if unturned else [float(v) for v in st['rotate_init'][:3]])
    p.set_field(em, 'rotation_random', [0.0] * 3 if unturned else [float(v) for v in st['rotate_init_rand'][:3]])
    p.set_field(em, 'rotation_velocity', [0.0] * 3 if unturned else [float(v) for v in st['rotate_add']])
    p.set_field(em, 'rotation_velocity_random', [0.0] * 3 if unturned else [float(v) for v in st['rotate_add_rand'][:3]])

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
    p.set_emitter_srt(em, tuple(info['scale']), eft_rotation(info['rotate']), tuple(info['trans']))

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
    # asked (and drops infinite-life particles); eft's FADE_ALPHA is that rate (1 / frames:
    # vanilla's infinite-life glows all have it), 0 lets the particles live out their life (test
    # 33's glow outlived the move; templates carrying 1 cut neutral air's burst at once); emission
    # stops as eft2's is_fade_emit says (always when nothing would end the emitter)
    info = e['info']
    fade = 1.0 / max(1, info['alpha_fade_time']) if info['is_fade_alpha_fade'] or life == FOREVER else 0.0
    if not one and not fade:
        # an endless emitter with no fade never ends once turned off (its instance stays, not
        # emitting); the rate ends it, its particles gone by then (forward air's speed lines)
        fade = 1.0 / max(1, info['alpha_fade_time'] or min(life, 10))
    struct.pack_into('>f', em, FADE_ALPHA, fade)
    em[FADE_EMIT] = 1 if info['is_fade_emit'] or not fade else 0
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


def turn_set(p, si, rot_deg):
    """every emitter of set si turned by an effect's angles (degrees, R = Rz Ry Rx: Smash 4's effect
    turn, cross_f.rpx 0x03373478) on top of its own transform: the effect then needs no angles
    (tools/effect_variants.py)"""
    r = rotation_xyz([math.radians(v) for v in rot_deg])
    for e in p.sets[si]['emitters']:
        em = e['data']
        if em is None:
            continue
        own = rotation_xyz(p.field(em, 'emitter_rotation'))
        m = r @ own
        y = math.asin(max(-1.0, min(1.0, -m[2, 0])))
        if abs(m[2, 0]) < 1 - 1e-6:
            x, z = math.atan2(m[2, 1], m[2, 2]), math.atan2(m[1, 0], m[0, 0])
        else:
            x, z = math.atan2(-m[1, 2], m[1, 1]), 0.0
        t = r @ np.array(p.field(em, 'emitter_translation'), float)
        p.set_emitter_srt(em, tuple(p.field(em, 'emitter_scale')), (x, y, z), tuple(float(v) for v in t))


def rotation_xyz(rot):
    """R = Rz Ry Rx (radians): eft's emitter turn, X first"""
    a, b, c = (float(v) for v in rot)
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return (np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
            @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]))


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
    ap.add_argument('--variants', help='JSON [{"effect", "rot"}] (tools/effect_variants.py scan): a copy of '
                    'each effect\'s set turned by rot (degrees, R = Rz Ry Rx), id "effect@rx,ry,rz"')
    a = ap.parse_args()
    eff = vfxb.Eff(a.eff)
    names, _ = eff.textures()
    images = eff.images()
    base = [f for f in os.listdir(a.base_dir) if f.endswith('.010d0000.ptcl')][0][:-len('.ptcl')]
    p = ptcl.Ptcl(open(os.path.join(a.base_dir, base + '.ptcl'), 'rb').read())
    ef = efc.Efc(open(os.path.join(a.base_dir, base + '.efc'), 'rb').read())
    templates = Templates(p, a.templates)
    prims, prim_index = eff.primitives(), {}
    ids, done, dropped = {}, {}, []
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
            dropped.append(name)
            continue
        if len(made) > MAX_EMITTERS:
            log.append('    %d emitters: the first %d kept' % (len(made), MAX_EMITTERS))
            made = made[:MAX_EMITTERS]
        sname = set_name(a.prefix, eff.sets[si_ult])
        si = p.new_set(sname, [m[0] for m in made], [m[1] for m in made])
        ids[name] = done[si_ult] = (0x300 + a.kind) << 16 | ef.add(si + 1)
        print('%-30s %-28s -> %-28s 0x%07X  %d emitters' % (name, eff.sets[si_ult], sname, ids[name], len(made)))
        print('\n'.join(log))
    if a.variants:
        import effect_variants
        for v in json.load(open(a.variants)):
            if v['effect'] not in ids:
                continue
            entry = ef.entries[ids[v['effect']] & 0xFFFF]          # [flags, set (1-based), ...]
            sname = p.name_at(p.sets[entry[1] - 1]['name_pos']) + 'R%d' % len(ids)
            si = p.clone_set(entry[1] - 1, sname)
            turn_set(p, si, v['rot'])
            key = effect_variants.variant_key(v['effect'], v['rot'])
            ids[key] = (0x300 + a.kind) << 16 | ef.add(si + 1, flags=entry[0])
            print('%-44s -> %-28s 0x%07X' % (key, sname, ids[key]))
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(a.out_dir, base + '.efc'), 'wb').write(ef.build())
    old = json.load(open(a.ids)) if os.path.exists(a.ids) else {}
    old.update({k: '0x%07X' % v for k, v in ids.items()})
    for k in dropped:       # an id from an earlier run would now name another effect's set
        old.pop(k, None)
    json.dump(old, open(a.ids, 'w'), indent=1)
    print('%d effects -> %d sets; %s' % (len(ids), len(set(done.values())), a.ids))


if __name__ == '__main__':
    main()
