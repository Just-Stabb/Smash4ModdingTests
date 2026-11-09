#!/usr/bin/env python3
"""Smash 3DS particle effects (.ptcl SPBD v0x33 + .efc EFCC) -> Smash 4 Wii U ones (.ptcl EFTF v0x42 + .efc
EFCF), for the Smash Run enemies (effect/enemy/KIND/, the path cross_f.rpx builds).

  python3 tools/s3ds_effects.py SRC_ROOT KIND|all OUT VANILLA_DIR [--base FILE.ptcl] [--no-models]
      (all: the Smash Run enemies; the effect models go next to the .efc, tools/s3ds_effect_models.py)
      SRC_ROOT: a tools/s3ds_unpack.py extract (enemy/KIND/effect/KIND.03030000.ptcl / .efc);
      VANILLA_DIR: vanilla Wii U ptcl files (their emitters are the templates: tools/vfxb_to_ptcl.py's
      Templates, BC4-shape templates only).
  python3 tools/s3ds_effects.py dump FILE.ptcl       the 3DS file's sets and emitters, fields read as below

The 3DS format is the same NintendoWare eft as the Wii U's (CTR port, little endian): the same file header
(+ the same tables), set records (0x1C), emitter tables (8-byte entries here), emitters with the name at
+0x38 and the same field order, but 2 texture slots of 0x7C bytes (not 3 of 0xD8), 3 colour keys (not 8)
and some fields packed in bytes. The emitter layout (SPBD_FIELDS below) was worked out on the 2,112 3DS
emitters of the enemies' and fighters' files: from their values, and by pairing the 147 fighter emitters
both games share unchanged (same names, same life / rate / scale / speeds ...) word by word and byte by
byte (docs/smash-run-port.md). A simple emitter is 0x548 bytes (plus padding); type 1 (complex) adds a
header with fields / fluctuation / stripe / child blocks (not converted: the emitter is converted as a
simple one, listed).

Each emitter is converted onto a vanilla template emitter (vfxb_to_ptcl.Templates: by particle type, blend,
follow type, flipbook, UV animation and rotation needs), then the 3DS fields written over it; the texture
(PICA200: ETC1 / ETC1A4 / L / LA / RGB(A)... decoded by tools/s3ds_model.py) folded into the templates' BC4
shape + a tint (texture_shape: the alpha-weighted mean colour, folded into the colour tracks for the colour
mode drawn, tinted_keys); ETC1 and the other formats without alpha: the shape is the colour's level (alpha
and colour alike, as the 3DS draws them and Smash 4's BC4 textures). The 3DS colour combiner (0x194) is the
Wii U's colour mode: a template drawing another gets an own pixel program (tools/eft_pixel.py). Step 2n: each
emitter's own PICA200 TEV set-up (its MATC block, matc_regs) says which texture channel the alpha comes from;
where the colour and that alpha differ from the one shape, the texture is two channels (BC5: R the colour's level,
G the alpha) under an own pixel program. Not converted: key animations (emitter curves), primitives (3DS mesh
particles: drawn as billboards; Furiijio's are unit quads), the complex blocks. The effect models (effect/model/NAME/*.bch)
are converted by tools/s3ds_effect_models.py into effect/enemy/KIND/model/NAME/; the .efc keeps the
references to the ones converted.
"""
import argparse
import glob
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eft_pixel  # noqa: E402
import ptcl  # noqa: E402
import s3ds_model as sm  # noqa: E402
import vfxb_to_ptcl as vt  # noqa: E402
from xv2_to_ptcl import FOREVER, MAX_EMITTERS, pow2, resize, sanitize, shape_texture  # noqa: E402

SIMPLE = 0x548
TEX_SLOTS3, TEXRES3 = (0x40, 0xBC), 0x7C
# 3DS texture formats (TexRes +0x6C; Switch Toolbox's PTCL_3DS SurfaceFormat) -> s3ds_model.FORMATS index
SURFACE = {18: 13, 19: 12, 20: 6, 21: 10, 22: 11, 23: 7, 24: 8, 25: 9, 26: 5, 27: 2, 28: 4, 29: 0, 30: 1, 31: 3}
NO_ALPHA = {12, 6, 10, 7, 1, 3}               # ETC1, HILO8, L4, L8, RGB8, RGB565: alpha from the shape
SHAPE_SEL = vt.SHAPE_SEL
BC4 = 0x34
BC5, TWO_SEL = 0x35, 0x00000001               # step 2n: two channels, rgb <- R (the colour), a <- G (the alpha)
COMBINER = 0x194                              # 3DS colour combiner: the Wii U's colour modes (0x314)
# step 2n: every 3DS emitter's own PICA200 fragment set-up. Header words 16 / 17 (+0x40 / +0x44) are the MATC table
# (offset, size: furiijio 0x6C50, 0x948), 0x18C-byte blocks 'MATC', 2 words, then a PICA command list (TEV stages
# 0xC0.. 0xFC, 0xE0 buffer, 0x100-0x107 blending / alpha test / depth, 0x80-0x8E texture 0); the emitter's +0x158 is
# its block's offset (furiijio: BG 0, snow 0x18C, cool_airA 0x318, tubu 0x4A4, flare 0x630, sign_center 0x7BC; the
# texture size in each block's 0x82 is its emitter's). TEV stage 0 takes the colour from texture 0's rgb and the
# alpha from ONE channel of it, per emitter (furiijio: cool_airA and sign_center its alpha, BG / snow / tubu / flare
# its red); stage 1 multiplies the vertex (particle) colour and alpha in, stage 2+ add / blend colour 1 (the
# combiner 0x194). (The table was read as mesh primitives up to effects v3: those are at header words 11 / 12, three
# unit quads for furiijio.)
MATC_PTR = 0x158
TEV_SRC = {0: 'prim', 1: 'frag', 2: 'frag2', 3: 'tex0', 4: 'tex1', 5: 'tex2', 6: 'tex3', 0xD: 'buf', 0xE: 'const',
           0xF: 'prev'}
TEV_ALPHA_OP = {0: 'a', 1: '1-a', 2: 'r', 3: '1-r', 4: 'g', 5: '1-g', 6: 'b', 7: '1-b'}


def matc_regs(blk, off):
    """{PICA register: value} of the MATC block at OFF of the table BLK (None: no block there). Commands are
    {param, header (register, mask, extra count << 20, consecutive << 31)} + the extra params, padded to 8 bytes"""
    if off < 0 or off + 12 > len(blk) or blk[off:off + 4] != b'MATC':
        return None
    p, regs = off + 12, {}
    while p + 8 <= len(blk) and blk[p:p + 4] != b'MATC':
        param, hdr = struct.unpack_from('<2I', blk, p)
        reg, extra, cons = hdr & 0xFFFF, (hdr >> 20) & 0xFF, hdr >> 31
        if reg > 0x2FF or p + 8 + 4 * extra > len(blk):
            break
        vals = [param] + list(struct.unpack_from('<%dI' % extra, blk, p + 8))
        for i, v in enumerate(vals):
            regs[reg + (i if cons else 0)] = v
        p += 8 + 4 * extra + (4 if extra % 2 else 0)
    return regs


def matc_alpha_channel(regs):
    """the texture channel TEV stage 0 takes the alpha from ('a', 'r', 'g', 'b'), or None when stage 0's alpha
    isn't texture 0 straight (another source, an inverted operand, a stage 0 that doesn't pass A on)"""
    if not regs or 0xC0 not in regs:
        return None
    src, opr, cmb = regs.get(0xC0, 0), regs.get(0xC1, 0), regs.get(0xC2, 0)
    if TEV_SRC.get((src >> 16) & 0xF) != 'tex0' or (cmb >> 16) & 0xF != 0:     # alpha: A = tex0 (replace)
        return None
    op = TEV_ALPHA_OP.get((opr >> 12) & 0x7)
    return op if op in ('a', 'r', 'g', 'b') else None


def texture_shape(img, fmt):
    """(shape [h, w] 0..1, tint rgb) of a 3DS texture for the BC4-shape templates (shape replicated: the
    template draws its colour from colour 0 / 1 by it and its alpha as it). A format without alpha (ETC1, L8,
    RGB565...): the 3DS draws the colour's level as the alpha too, so the shape is that level (the colour's
    projection on the tint), once: alpha = max(rgb) and then x the projection drew level^2 (Furiijio's mist
    at a quarter where the 3DS has a half; the vanilla Wii U copies of the fighters' ETC1 textures hold the
    level: 104 of 134 matched texture pairs). With alpha: alpha x the projection (xv2_to_ptcl.shape_texture)"""
    rgba = img.astype(np.float32) / 255.0
    if fmt not in NO_ALPHA:
        return shape_texture(rgba)
    rgba[..., 3] = rgba[..., :3].max(-1)                  # the weights of the tint
    _s, tint = shape_texture(rgba)
    return np.clip(rgba[..., :3] @ tint / float(tint @ tint), 0, 1), tint


def texture_channels(img, fmt, chan):
    """step 2n: (colour level [h, w], alpha [h, w], tint rgb) of a 3DS texture drawn as its MATC's TEV stage 0 does:
    the colour its rgb (the level along the tint, alpha NOT folded in) and the alpha its channel CHAN ('a': the
    alpha, 0 or 1 for a format without one as PICA200 reads it: 1; 'r' / 'g' / 'b': that colour channel). The
    tint is texture_shape's (alpha-weighted mean colour), so tinted_keys folds it the same way"""
    rgba = img.astype(np.float32) / 255.0
    _s, tint = texture_shape(img, fmt)
    t = np.asarray(tint, np.float32)
    level = np.clip(rgba[..., :3] @ t / max(float(t @ t), 1e-6), 0, 1)
    if chan == 'a':
        alpha = np.ones(rgba.shape[:2], np.float32) if fmt in NO_ALPHA else rgba[..., 3]
    else:
        alpha = rgba[..., 'rgb'.index(chan)]
    return level, alpha, tint


def tinted_keys(mode, keys0, keys1, tint):
    """the colour 0 / 1 keys that draw the 3DS colour of combiner MODE with the texture's tint folded into
    them (the shape carries the level only): 0 colour 0 (no texture colour); 1 colour 0 x texture; 2
    colour 1 + (colour 0 - colour 1) x texture -> colour 0' = colour 1 + (colour 0 - colour 1) x tint,
    colour 1 as is (exact); 3 colour 0 x texture + colour 1 -> colour 0 x tint, colour 1 as is. Colour 1
    was x tint too up to effects v3: Furiijio's mist (colour 1 deep blue) drew a darker blue than the 3DS"""
    t = np.asarray(tint, float)
    if mode == 0:
        k0 = [np.asarray(k, float) for k in keys0]
    elif mode == 2:
        k0 = [np.asarray(keys1[min(i, len(keys1) - 1)], float) +
              (np.asarray(k, float) - np.asarray(keys1[min(i, len(keys1) - 1)], float)) * t
              for i, k in enumerate(keys0)]
    else:
        k0 = [np.asarray(k, float) * t for k in keys0]
    return [tuple(float(c) for c in k) for k in k0], [tuple(float(c) for c in k) for k in keys1]

# (3DS offset, struct format (little endian), Wii U field name or offset, note). Offsets read off the corpus
# (see the module doc): the matches with the shared emitters' Wii U fields given as e.g. 0.99 (share of pairs)
SPBD_FIELDS = [
    (0x038, 'I', 'name_pos', 'into the name table'),
    (0x14C, 'i', 'primitive_index', '-1 none (0.95)'),
    (0x17D, 'B', 0x2F9, 'stop emitting while the set fades (0.97)'),
    (0x184, '3B', 0x2FC, 'random rotation direction x y z (1.00)'),
    (0x190, 'I', 'follow', '0 follow, 1 none, 2 position (Wii U 0x310, 0.95)'),
    (0x194, 'I', 'combiner', 'colour combiner (Wii U 0x314, 0.90): 1 colour 0 x texture, '
                             '2 colour 1 + (0 - 1) x texture'),
    (0x1A8, '12f', None, 'emitter matrix (Wii U 0x3A8)'),
    (0x1D8, '12f', 'emitter_matrix', '(0.95)'),
    (0x208, '3f', 'emitter_scale', ''),
    (0x214, '3f', 'emitter_rotation', 'radians (0.94)'),
    (0x220, '3f', 'emitter_translation', '(0.98)'),
    (0x244, 'I', 'blend_type', '0 alpha, 1 add, 2 subtract (0.99; names *add* 75 / 78 1, *alpha* 57 / 59 0)'),
    (0x250, 'I', 'volume_type', 'NintendoWare\'s 0-14 shapes'),
    (0x254, '3f', 'volume_radius', ''),
    (0x260, 'I', 'volume_sweep_start', 'u32 angle (2^32 a turn) -> radians'),
    (0x264, 'I', 'volume_sweep_param', 'u32 angle -> radians'),
    (0x26C, 'f', 0x360, 'the same distribution as Wii U 0x360 (1 / 0.5 / 0.2)'),
    (0x270, 'f', 0x364, 'pi (Wii U 0x364, 1.00)'),
    (0x284, '3f', 0x378, 'shape scale (0.99): what key animations scale'),
    (0x290, '4f', 0x384, 'emitter colour 0'),
    (0x2A0, '4f', 0x394, 'emitter colour 1'),
    (0x2B0, 'f', 0x3A4, 'emitter alpha'),
    (0x2B4, 'f', 0x494, '(0.97)'),
    (0x2B8, 'f', 0x498, '(0.97)'),
    (0x2C4, 'f', 'emit_rate', '(0.82)'),
    (0x2C8, 'i', 'emit_start', '(0.88)'),
    (0x2CC, 'i', 'end_frame', '0x7FFFFFFF forever (0.95)'),
    (0x2D0, 'i', 'emit_interval', ''),
    (0x2D4, 'i', 'emit_interval_random', '(0.90)'),
    (0x2D8, 'f', 'figure_velocity', ''),
    (0x2DC, 'f', 'emitter_velocity', 'directional speed (0.84)'),
    (0x2E0, 'f', 'init_velocity_random', '(0.92)'),
    (0x2E4, '3f', 'emit_direction', ''),
    (0x2F0, 'f', 'dispersion_angle', 'degrees'),
    (0x2F4, '3f', 'spread_vec', ''),
    (0x300, 'f', 'air_resistance', '(0.93)'),
    (0x304, '3f', 'gravity', ''),
    (0x31C, 'i', 'ptcl_life', '(0.90)'),
    (0x320, 'i', 'ptcl_life_random', '(0.74)'),
    (0x324, 'I', 0x4B8, '0 / 1 / 2 (Wii U 0x4B8, 0.95)'),
    (0x328, 'I', 'particle_type', '0 billboard, 1 / 2 plates, 3 directional, 4 directional polygon, 5 / 6 '
                                  'stripes, 8 Y billboard (0.92; *line* emitters 3)'),
    (0x32C, '2f', 0x4C4, 'rotBasis (1.00)'),
    (0x334, 'f', 'camera_offset', '(0.78)'),
    # texture slot 0's UV block (slot 1's at 0x3B0, the same layout)
    (0x338, 'B', None, 'flipbook animated (with frames a cell > 0)'),
    (0x33B, 'B', 0x4D8, 'cells down'),
    (0x33C, 'B', 0x4D7, 'cells across'),
    (0x33D, 'B', 0x4D9, 'random start cells (0.92)'),
    (0x340, 'h', 0x504, 'frames a cell'),
    (0x342, 'h', 0x506, 'pattern table entries'),
    (0x344, '32B', 0x4E0, 'pattern table'),
    (0x364, 'I', None, 'repeat: 0 1x1, 1 2x1, 2 1x2, 3 2x2 (in the UV scale already; vfxb_to_ptcl.REPEAT)'),
    (0x368, '2f', 'tex0_uv_scale', 'repeat / cells'),
    (0x370, 'I', 0x510, 'UV animation mode bits (0.96)'),
    (0x374, '2f', 0x514, 'UV scroll a frame (V negated: the 3DS\'s V runs up)'),
    (0x37C, '2f', 0x51C, 'UV scroll initial'),
    (0x384, '2f', 0x524, 'UV scroll random'),
    (0x38C, '2f', 0x52C, 'UV scale a frame'),
    (0x394, '2f', 0x534, 'UV scale initial'),
    (0x39C, '2f', 0x53C, 'UV scale random'),
    (0x3A4, 'f', 0x544, 'UV rotation a frame (negated)'),
    (0x3A8, 'f', 0x548, 'UV rotation initial (negated)'),
    (0x3AC, 'f', 0x54C, 'UV rotation random'),
    (0x428, 'I', 'color0_type', '0 constant, 1 random, 2 keys (1.00)'),
    (0x42C, 'I', 'color1_type', '(0.88)'),
    (0x430, '12f', None, 'colour 0: 3 keys rgba'),
    (0x460, '12f', None, 'colour 1: 3 keys rgba'),
    (0x490, '2i', 'color_section1', 'colour 0 / 1 (% of life)'),
    (0x498, '2i', 'color_section2', ''),
    (0x4A0, '2i', 'color_section3', ''),
    (0x4A8, '2i', 'color_repeat', ''),
    (0x4B8, 'f', 'color_scale', ''),
    (0x4BC, 'f', 'alpha_init', ''),
    (0x4C0, 'f', 'alpha_diff21', '(0.88)'),
    (0x4C4, 'f', 'alpha_diff32', ''),
    (0x4C8, 'i', 'alpha_section1', '% of life (Wii U: a fraction)'),
    (0x4CC, 'i', 'alpha_section2', ''),
    (0x4D8, '2i', 'scale_sections', '(0.95)'),
    (0x4E0, 'f', 'scale_random', 'one value (Wii U x and y, 0.95)'),
    (0x4E4, '2f', 'scale', ''),
    (0x4EC, '2f', 'scale_init_ratio', ''),
    (0x4F4, '2f', 'scale_diff21', '(0.93)'),
    (0x4FC, '2f', 'scale_diff32', '(0.95)'),
    (0x508, '3f', 'rotation_init', '(0.94)'),
    (0x514, '3f', 'rotation_random', '(0.99)'),
    (0x520, '3f', 'rotation_velocity', '(1.00)'),
    (0x52C, '3f', 'rotation_velocity_random', '(0.98)'),
    (0x538, 'f', 'rotation_attenuation', '(0.96)'),
    (0x53C, 'f', 0x82C, 'fade rate'),
]


def field(d, off, fmt):
    v = struct.unpack_from('<' + fmt, d, off)
    return v if len(v) > 1 else v[0]


# ---------------------------------------------------------------- reading
def read_spbd(data):
    """-> dict(sets=[dict(name, emitters=[dict(name, data, textures=[RGBA or None, ...], formats)])])"""
    d = data
    assert d[:4] == b'SPBD', d[:4]
    h = struct.unpack_from('<20I', d, 0)
    names, tex_pos = h[4], h[5]
    matc = d[h[16]:h[16] + h[17]] if h[17] and h[16] + h[17] <= len(d) else b''

    def nm(o):
        return d[names + o:d.index(b'\0', names + o)].decode('latin1')
    starts, sets = set(), []
    for i in range(h[2]):
        w = struct.unpack_from('<7I', d, 0x48 + 0x1C * i)
        ems = [struct.unpack_from('<I', d, w[5] + 8 * k)[0] for k in range(w[4])]
        starts.update(ems)
        sets.append((nm(w[2]), ems))
    order = sorted(starts) + [names]
    out = []
    for sname, ems in sets:
        es = []
        for e in ems:
            end = order[order.index(e) + 1]
            em = d[e:end]
            texs, fmts = [], []
            for slot in TEX_SLOTS3:
                w_, h_ = struct.unpack_from('<2H', em, slot)
                fmt, size, pos = struct.unpack_from('<3I', em, slot + 0x6C)
                if not (w_ and h_ and size) or fmt not in SURFACE:
                    texs.append(None)
                    fmts.append(fmt)
                    continue
                f = SURFACE[fmt]
                raw = d[tex_pos + pos:tex_pos + pos + sm.tex_size(w_, h_, f)]
                texs.append(sm.decode_texture(raw, w_, h_, f))
                fmts.append(f)
            es.append(dict(name=nm(struct.unpack_from('<I', em, 0x38)[0]), data=em, textures=texs, formats=fmts,
                           wrap=em[TEX_SLOTS3[0] + 0x10], complex=struct.unpack_from('<I', em, 0)[0] == 1,
                           matc=matc_regs(matc, struct.unpack_from('<I', em, MATC_PTR)[0]) if matc else None))
        out.append(dict(name=sname, emitters=es))
    return dict(sets=out)


def read_efc(data):
    """3DS EFCC: 'EFCC', u32 version (6 / 7), u16 entries, u16 models, u16 mesh records, u16 0, then 16-byte
    entries (u32 flags, u32 set (1-based), u32 model (1-based), u16 first mesh record, u16 count), the mesh
    records (u16, u16), the model folder names and the mesh names: the Wii U's EFCF (tools/efc.py) little
    endian, with a u32 version in place of its u16 variant / version"""
    assert data[:4] == b'EFCC', data[:4]
    _v, n, m, x = struct.unpack_from('<IHHH', data, 4)
    entries = [list(struct.unpack_from('<IIIHH', data, 0x10 + 0x10 * i)) for i in range(n)]
    o = 0x10 + 0x10 * n
    meshes = [list(struct.unpack_from('<HH', data, o + 4 * i)) for i in range(x)]
    o += 4 * x
    names = []
    for _ in range(m + x):
        e = data.index(b'\0', o)
        names.append(data[o:e].decode('ascii'))
        o = e + 1
    return entries, names[:m], meshes, names[m:]


def write_efc(entries, models=(), meshes=(), mesh_names=(), have=()):
    """Wii U EFCF (version 7). Effect models are kept only when their folder was converted (names in HAVE:
    effect/enemy/KIND/model/NAME, tools/s3ds_effect_models.py); an entry pointing at a model that isn't there
    would have the game load a missing folder, so those references are dropped and the list renumbered"""
    keep = [m for m in models if m in set(have)]
    new = {i + 1: keep.index(m) + 1 for i, m in enumerate(models) if m in keep}
    entries = [[f, s, new.get(m, 0), a if m in new else 0, b if m in new else 0] for f, s, m, a, b in entries]
    if not keep:
        meshes, mesh_names = [], []
    out = b'EFCF' + struct.pack('>HHHHHH', 0, 7, len(entries), len(keep), len(meshes), 0)
    out += b''.join(struct.pack('>IIIHH', *e) for e in entries)
    out += b''.join(struct.pack('>HH', *mm) for mm in meshes)
    out += b''.join(x.encode('ascii') + b'\0' for x in list(keep) + list(mesh_names))
    return out


# ---------------------------------------------------------------- converting
def u32_angle(v):
    return v / 2.0 ** 32 * 2 * math.pi


def convert_emitter(p, templates, e, notes):
    d = e['data']
    g = {}
    for off, fmt, name, _note in SPBD_FIELDS:
        g[off] = field(d, off, fmt)
    typ = g[0x328]
    typ = {5: 3, 6: 3, 7: 0}.get(typ, typ)
    blend = g[0x244] if g[0x244] in (0, 1, 2) else 0
    follow = g[0x190] if g[0x190] in (0, 1, 2) else 1
    uv_mode = g[0x370] & 7
    animated_ptn = d[0x338] and g[0x340] > 0
    ptn = 2 if animated_ptn else 0
    rot = vt.ROT_NONE
    if any(abs(x) > 1e-6 for x in g[0x520] + g[0x52C]):
        rot = vt.ROT_ANIMATED
    elif any(abs(x) > 1e-6 for x in g[0x508] + g[0x514]):
        rot = vt.ROT_ANIMATED
    if g[0x14C] >= 0:
        notes.append('primitive (a 3DS mesh particle, a unit quad for Furiijio\'s): drawn as a billboard')
    if e['complex']:
        notes.append('complex blocks (fields / child / stripe) not converted')
    em, _turns, _swapped = templates.get(typ, blend, False, uv_mode, follow, ptn, rot, notes)
    em = bytearray(em)

    # ---- texture: slot 0, folded into a BC4 shape + tint
    img = e['textures'][0]
    if img is None:
        img = np.full((16, 16, 4), 255, np.uint8)
        notes.append('no texture: white')
    shape, tint = texture_shape(img, e['formats'][0])
    h, w = shape.shape
    tw, th = pow2(w, hi=256), pow2(h, hi=256)
    # step 2n: the emitter's own TEV stage 0 (its MATC block): the colour from the texture's rgb, the alpha from one
    # channel. Where those differ from the one shape (alpha x level, or the level), two channels: BC5, rgb <- R the
    # colour's level, a <- G the alpha channel, drawn by an own pixel program (alpha mode 0: colour 0 alpha x t.a).
    # Up to effects v3 the colour was x the alpha too (Furiijio's cool_air: alpha 0.33 x a bright cyan texture drew
    # a deep blue, as the sky)
    chan = matc_alpha_channel(e.get('matc'))
    two = None
    if chan is not None:
        level, alpha, _t = texture_channels(img, e['formats'][0], chan)
        if np.abs(level - shape).mean() > 0.02 or np.abs(alpha - shape).mean() > 0.02:
            two = (level, alpha)

    def shape_tex(s):
        if (tw, th) != (w, h):
            s = resize(s[..., None].astype(np.float32), tw, th)[..., 0]
        return (np.clip(s, 0, 1) * 255 + 0.5).astype(np.uint8)
    if two is not None:
        lv8, al8 = shape_tex(two[0]), shape_tex(two[1])
        p.set_texture(em, 0, np.stack([lv8, al8, np.zeros_like(lv8), np.full_like(lv8, 255)], 2), BC5,
                      comp_sel=TWO_SEL)
    else:
        r8 = shape_tex(shape)
        p.set_texture(em, 0, np.stack([r8, r8, r8, r8], 2), BC4, comp_sel=SHAPE_SEL)
    wu, wv = e['wrap'] & 0xF, e['wrap'] >> 4
    samp = struct.unpack_from('>I', em, ptcl.TEXRES + 0x0C)[0] & 0x00FFFFFF
    struct.pack_into('>I', em, ptcl.TEXRES + 0x0C, samp | (min(wu, 2) << 24) | (min(wv, 2) << 28))

    # ---- named fields
    for off, fmt, name, _note in SPBD_FIELDS:
        if not isinstance(name, str) or name in ('name_pos', 'primitive_index', 'follow', 'combiner',
                                                 'volume_sweep_start', 'volume_sweep_param', 'alpha_section1',
                                                 'alpha_section2', 'scale_random', 'emitter_matrix',
                                                 'emitter_scale', 'emitter_rotation', 'emitter_translation',
                                                 'color0_type', 'color1_type'):
            continue
        v = g[off]
        p.set_field(em, name, list(v) if isinstance(v, tuple) else v)
    for off, fmt, wo, _note in SPBD_FIELDS:
        if isinstance(wo, int):
            v = g[off]
            vals = v if isinstance(v, tuple) else (v,)
            for j, x in enumerate(vals):
                c = fmt[-1]
                size = {'f': 4, 'I': 4, 'i': 4, 'h': 2, 'B': 1}[c]
                struct.pack_into('>' + c, em, wo + size * j, x)
    p.set_field(em, 'volume_sweep_start', u32_angle(g[0x260]))
    p.set_field(em, 'volume_sweep_param', u32_angle(g[0x264]))
    # a first section of -127 (689 3DS emitters: no first section; the paired Wii U fighter emitters have 0 there,
    # 86 + 37 + 20 + ... of them) is 0: a negative one made eft's emission take the key's step backwards (cross_f
    # 0x04A5D964: the start value init - diff21 / section)
    p.set_field(em, 'alpha_section1', max(g[0x4C8], 0) / 100.0)
    p.set_field(em, 'alpha_section2', max(g[0x4CC], 0) / 100.0)
    p.set_field(em, 'scale_sections', [max(v, 0) for v in g[0x4D8]])
    p.set_field(em, 'scale_random', [g[0x4E0], g[0x4E0]])
    p.set_emitter_srt(em, g[0x208], g[0x214], g[0x220])
    struct.pack_into('>I', em, vt.FOLLOW, follow)
    p.set_field(em, 'start_frame', 0)
    end = g[0x2CC]
    p.set_field(em, 'end_frame', FOREVER if end >= FOREVER else max(1, end))
    p.set_field(em, 'one_time', 0 if end >= FOREVER else 1)
    p.set_field(em, 'display_side', 0)
    # the 3DS's V runs up: V scroll and the UV rotation the other way
    for wo in (0x518, 0x520, 0x528):
        struct.pack_into('>f', em, wo, -struct.unpack_from('>f', em, wo)[0])
    for wo in (0x544, 0x548):
        struct.pack_into('>f', em, wo, -struct.unpack_from('>f', em, wo)[0])
    # flipbook: the 3DS's random start cells / animated table
    em[0x4D5] = 1 if animated_ptn else 0
    struct.pack_into('>I', em, vt.PTN_MODE, ptn)
    if not animated_ptn:
        struct.pack_into('>hh', em, 0x504, 0, 0)

    # ---- colour mode: the 3DS combiner (the Wii U's colour modes, 0x314: 551 of 581 paired fighter emitters
    # with 2 have 2, 47 of 58 with 1 have 1, 7 of 14 with 3 have 3). A template drawing another mode gets an
    # own pixel program (tools/eft_pixel.py) of the 3DS mode: up to effects v3 every emitter drew its
    # template's (mostly 2, colour 1 + (colour 0 - colour 1) x texture), Furiijio's mist (3: colour 0 x
    # texture + colour 1) a deep blue, invisible on a blue sky
    mode = struct.unpack_from('>I', em, vt.COLOR_MODE)[0]
    want = g[COMBINER]
    c1_rgb = [float(c) * g[0x4B8] for c in g[0x460][:3]]
    if (want in (0, 1, 2, 3) and want != mode) or two is not None:
        target = want if want in (0, 1, 2, 3) else mode
        si = eft_pixel.own_shader(p, p.field(em, 'shader_index'), target, 0, 1.0, c1_const=c1_rgb,
                                  additive=blend == 1)
        if si is None:
            notes.append('colour mode %d drawn as the template\'s %d (no own program for its layout)' % (want, mode))
            if two is not None:             # the template's program reads one channel: the one shape again
                notes.append('texture alpha / colour in one shape (no own program for its layout)')
                r8 = shape_tex(shape)
                p.set_texture(em, 0, np.stack([r8, r8, r8, r8], 2), BC4, comp_sel=SHAPE_SEL)
                two = None
        else:
            struct.pack_into('>I', em, 0x844, si)
            struct.pack_into('>I', em, vt.COLOR_MODE, target)
            mode = target

    # ---- colours: the 3 keys, the texture's tint folded in for the colour mode drawn (tinted_keys)
    keys = [[tuple(g[off][4 * k:4 * k + 3]) for k in range(3)] for off in (0x430, 0x460)]
    k0, k1 = tinted_keys(mode, keys[0], keys[1], tint)
    for track, ks, toff in ((0, k0, 0x428), (1, k1, 0x42C)):
        ks = [(*k, 1.0) for k in ks]
        typ_c = g[toff]
        if typ_c == 2:
            p.set_color_keys(em, track, ks, 2)
        elif typ_c == 1:
            p.set_color_keys(em, track, ks, 1)
        else:
            p.set_color_keys(em, track, ks[:1], 0)
    if p.field(em, 'keyanim_size'):
        p.set_field(em, 'keyanim_size', 0)
    notes += sanitize(p, em)
    return em


def convert_file(src_ptcl, src_efc, templates, base_path, log=print, models_have=()):
    """-> (ptcl bytes, efc bytes, set names); MODELS_HAVE: the effect model folders converted next to it"""
    s3 = read_spbd(open(src_ptcl, 'rb').read())
    p = ptcl.Ptcl(open(base_path, 'rb').read())
    templates.base = p
    nbase = len(p.sets)
    made = []
    for s in s3['sets']:
        ems, names = [], []
        for e in s['emitters'][:MAX_EMITTERS]:
            notes = []
            ems.append(convert_emitter(p, templates, e, notes))
            names.append(e['name'])
            if notes:
                log('    %s / %s: %s' % (s['name'], e['name'], '; '.join(sorted(set(notes)))))
        p.new_set(s['name'], ems, names)
        made.append(s['name'])
    p.sets = p.sets[nbase:]
    p.drop_unused_shaders(0)
    p.drop_unused_textures()
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    efc_b, dropped = write_efc([]), []
    if src_efc and os.path.exists(src_efc):
        entries, models, meshes, mesh_names = read_efc(open(src_efc, 'rb').read())
        dropped = sorted({models[e[2] - 1] for e in entries if e[2]} - set(models_have))
        efc_b = write_efc(entries, models, meshes, mesh_names, models_have)
        if dropped:
            log('    efc: effect models left out (no converted folder): %s' % ', '.join(dropped))
    return out, efc_b, made


def main():
    if len(sys.argv) > 2 and sys.argv[1] == 'dump':
        s3 = read_spbd(open(sys.argv[2], 'rb').read())
        for s in s3['sets']:
            print(s['name'])
            for e in s['emitters']:
                d = e['data']
                print('   %-24s type %d blend %d follow %d life %d rate %g end %d scale %s tex %s' % (
                    e['name'], field(d, 0x328, 'I'), field(d, 0x244, 'I'), field(d, 0x190, 'I'),
                    field(d, 0x31C, 'i'), field(d, 0x2C4, 'f'), field(d, 0x2CC, 'i'),
                    '%.3gx%.3g' % field(d, 0x4E4, '2f'),
                    'x'.join(map(str, e['textures'][0].shape[:2])) if e['textures'][0] is not None else '-'))
        return
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('kind')
    ap.add_argument('out')
    ap.add_argument('vanilla')
    ap.add_argument('--base', default=None)
    ap.add_argument('--no-models', action='store_true', help='leave the effect models (and the efc references) out')
    a = ap.parse_args()
    vt.EXACT = vt.TWO_TEXTURES = vt.GRAFT = vt.UNIVERSAL = False
    corpus = sorted(glob.glob(os.path.join(a.vanilla, '**', '*.ptcl'), recursive=True))
    base = a.base or min(corpus, key=os.path.getsize)
    templates = vt.Templates(ptcl.Ptcl(open(base, 'rb').read()), corpus)
    import s3ds_enemy
    import s3ds_effect_models
    fs = s3ds_enemy.fs_kinds(a.src)
    kinds = fs if a.kind == 'all' else [a.kind]     # all: the Smash Run enemies
    for k in kinds:
        f = os.path.join(a.src, 'enemy', k, 'effect', '%s.03030000.ptcl' % k)
        fe = f.replace('.ptcl', '.efc')
        if not os.path.exists(f) and not os.path.exists(fe):
            continue
        print(k)
        have = [] if a.no_models else s3ds_effect_models.convert_kind(a.src, k, a.out, fs)
        od = os.path.join(a.out, 'effect', 'enemy', k)
        os.makedirs(od, exist_ok=True)
        if not os.path.exists(f):
            # a bank of effect models only (no particles): an .efc and its model folders, no .ptcl, as the
            # vanilla miienemys bank
            entries, models, meshes, mesh_names = read_efc(open(fe, 'rb').read())
            open(os.path.join(od, '%s.010d0000.efc' % k), 'wb').write(
                write_efc(entries, models, meshes, mesh_names, have))
            print('  models only: %d entries' % len(entries))
            continue
        out, efc_b, made = convert_file(f, fe, templates, base, models_have=have)
        open(os.path.join(od, '%s.010d0000.ptcl' % k), 'wb').write(out)
        open(os.path.join(od, '%s.010d0000.efc' % k), 'wb').write(efc_b)
        print('  %d sets, %d bytes' % (len(made), len(out)))


if __name__ == '__main__':
    main()
