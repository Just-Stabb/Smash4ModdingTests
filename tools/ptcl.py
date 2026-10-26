#!/usr/bin/env python3
"""Smash 4 (Wii U) particle files: .ptcl, magic EFTF, version 0x42 (NintendoWare for Cafe eft).

  python3 tools/ptcl.py info FILE.ptcl                    header, sections, emitter sets / emitters
  python3 tools/ptcl.py dump FILE.ptcl OUTDIR             info + every emitter's main params (json) + textures (png)
  python3 tools/ptcl.py roundtrip FILE.ptcl...            parse and rebuild: byte-exact?

Format: docs/ptcl-format.md. The structure (sections, emitter sets, emitters and their
sizes, every offset field the runtime resolves) is exact (round trip of all 117 vanilla fighter
files); the emitter's parameter fields are named in FIELDS with a confidence each.

Editing (the Ptcl object, then .build()):
  p.set_index(name) / p.find_set(name)          emitter sets by name
  p.field(em, 'ptcl_life') / p.set_field(...)   named emitter fields (FIELDS)
  p.color_keys(em, 0) / p.set_color_keys(em, 0, [(r, g, b, a), ...], typ=2)
  p.decode_texture(em, slot) -> RGBA            the slot's native texture, mip 0
  p.add_texture(rgba, fmt) -> (pos, size, meta) GX2 data appended to the texture table (one mip)
  p.set_texture(em, slot, rgba, fmt=None)       a new texture for the slot (same format family
                                                by default; one mip)
  p.add_name(s) -> name offset
  p.clone_set(src, new_name) -> set index       a copy of a set (its emitters, sharing textures,
                                                shaders, key animations, shader params)
  p.new_set(name, [emitter bytes...]) -> index  a set from template emitters (e.g. p.emitter_bytes(...))
  p.import_shader(other_ptcl, index) -> index   a shader (GFX2 binary + key entry) from another file
"""
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import nut  # noqa: E402  (GX2 addressing, BC encode / decode)

MAGIC, VERSION = b'EFTF', 0x42
HEADER_SIZE, SET_SIZE, TBL_ENTRY = 0x48, 0x1C, 0x10
SIMPLE_SIZE = 0x8BC
TEXRES, TEXRES_SIZE, TEX_SLOTS = 0x40, 0xD8, 3
CHILD_TEXRES = 0x920                 # complex emitter + child block (0x8D4) + 0x4C
SHADER_ENTRY = 0x78
PRIM_ENTRY = 0x50

# eft texture format (TexRes +0x2C native / +0x20 original) -> GX2 surface format
EFT_GX2 = {2: 0x1A, 3: 0x31, 4: 0x431, 5: 0x32, 6: 0x432, 7: 0x33, 8: 0x433, 9: 0x34, 10: 0x234,
           11: 0x35, 12: 0x235}
GX2_EFT = {0x1A: 2, 0x31: 3, 0x32: 5, 0x33: 7, 0x34: 9, 0x35: 11}
GX2_ALIGN = {0x1A: 0x800, 0x31: 0x1000, 0x32: 0x2000, 0x33: 0x2000, 0x34: 0x1000, 0x35: 0x2000}
# channel selectors (TexRes +0x14, one byte per output channel: 0 R 1 G 2 B 3 A 4 zero 5 one)
COMP_SEL = {0x1A: 0x00010203, 0x31: 0x00010203, 0x32: 0x00010203, 0x33: 0x00010203,
            0x34: 0x00000005, 0x35: 0x00000001}


def be32(d, o):
    return struct.unpack_from('>I', d, o)[0]


def align(v, a):
    return -(-v // a) * a


# ------------------------------------------------------------------ emitter fields
# (offset, struct format, name, confidence: 'runtime' = the game's code resolves / reads it as such,
#  'corpus' = from the 117 vanilla files' values, 'guess' = by analogy with NintendoWare eft)
FIELDS = [
    (0x000, '>I', 'type', 'runtime'),            # 0 simple (0x8BC bytes), 1 complex (+ 0x8BC header)
    (0x004, '>I', 'flags', 'corpus'),
    (0x008, '>I', 'random_seed', 'guess'),        # 0xFFFFFFFF = random
    (0x038, '>I', 'name_pos', 'runtime'),         # into the name table
    # 3 texture records (TexRes, 0xD8 each) at 0x40 / 0x118 / 0x1F0: see TEX_FIELDS
    (0x2CC, '>I', 'keyanim_pos', 'runtime'),      # into the key animation table
    (0x2D0, '>I', 'keyanim_size', 'runtime'),
    (0x2DC, '>i', 'primitive_index', 'runtime'),  # -1 none; else into the primitive table
    (0x2EC, '>I', 'shader_param_size', 'runtime'),
    (0x2F0, '>I', 'shader_param_pos', 'runtime'),  # into the shader parameter table
    (0x2FF, '>B', 'one_time', 'runtime'),         # 1: emits from start_frame for end_frame frames (vanilla: 1 <=> finite end)
    (0x30C, '>I', 'enum_30c', 'corpus'),          # 0x30C-0x33C: small enums, shader-keyed (see doc)
    (0x31C, '>I', 'enum_31c', 'corpus'),
    (0x324, '>I', 'blend_type', 'corpus'),         # 0 alpha, 1 add, 2 subtract (names: *_alpha 0, *add* 1)
    (0x340, '>I', 'volume_type', 'corpus'),       # 0 point, 2.. shapes (sphere / cylinder / box...)
    (0x348, '>3f', 'volume_radius', 'corpus'),
    (0x354, '>f', 'volume_sweep_start', 'corpus'),
    (0x358, '>f', 'volume_sweep_param', 'corpus'),
    (0x3D8, '>12f', 'emitter_matrix', 'corpus'),  # 3x4 rows: Rz.Ry.Rx(rotation) . diag(scale) | translation
    (0x408, '>3f', 'emitter_scale', 'corpus'),    # (the matrix is derived from these three: all 8115 vanilla
    (0x414, '>3f', 'emitter_rotation', 'corpus'),  # emitters agree; set_emitter_srt writes all four)
    (0x420, '>3f', 'emitter_translation', 'corpus'),
    (0x444, '>f', 'emit_rate', 'corpus'),
    (0x448, '>i', 'start_frame', 'corpus'),       # after the set starts
    (0x44C, '>i', 'emit_start', 'runtime'),       # first emission, frames after start_frame
    (0x450, '>i', 'end_frame', 'runtime'),        # one_time: emission ends this many frames after
                                                  # start_frame; 0x7FFFFFFF (never) without one_time
    (0x454, '>i', 'emit_interval', 'corpus'),
    (0x458, '>i', 'emit_interval_random', 'guess'),
    (0x45C, '>f', 'figure_velocity', 'guess'),    # all-direction speed
    (0x460, '>f', 'emitter_velocity', 'runtime'),  # read as a float with the life code
    (0x464, '>f', 'init_velocity_random', 'guess'),
    (0x468, '>3f', 'emit_direction', 'corpus'),
    (0x474, '>f', 'dispersion_angle', 'corpus'),   # degrees
    (0x478, '>3f', 'spread_vec', 'guess'),
    (0x484, '>f', 'air_resistance', 'corpus'),    # velocity x this each frame
    (0x4A4, '>3f', 'gravity', 'corpus'),
    (0x4B0, '>i', 'ptcl_life', 'runtime'),        # frames; 0x7FFFFFFF = infinite
    (0x4B4, '>i', 'ptcl_life_random', 'runtime'),
    (0x4BC, '>I', 'particle_type', 'corpus'),     # billboard / polygon / directional / stripe...: shader-keyed
    (0x4D0, '>f', 'camera_offset', 'verified'),   # depth offset toward the camera (eft2's offset): static CB2 vec4 36 .z
    (0x508, '>2f', 'tex0_uv_scale', 'corpus'),    # texture slot UV params: 3 x 0x7C from 0x4D4
    (0x648, '>I', 'color0_type', 'corpus'),       # 0 constant, 1 random, 2 key animation
    (0x64C, '>I', 'color1_type', 'corpus'),
    (0x650, '>32f', 'color0_keys', 'corpus'),     # 8 keys x (r, g, b, a?)
    (0x6D0, '>32f', 'color1_keys', 'corpus'),
    (0x750, '>2i', 'color_section1', 'corpus'),   # color0 / color1: % of life
    (0x758, '>2i', 'color_section2', 'corpus'),
    (0x760, '>2i', 'color_section3', 'corpus'),
    (0x768, '>2i', 'color_repeat', 'corpus'),
    (0x778, '>f', 'color_scale', 'corpus'),       # brightness multiplier (1.2-1.5 on glows)
    (0x784, '>f', 'alpha_init', 'corpus'),
    (0x788, '>f', 'alpha_diff21', 'guess'),
    (0x78C, '>f', 'alpha_diff32', 'guess'),
    (0x790, '>f', 'alpha_section1', 'corpus'),
    (0x794, '>f', 'alpha_section2', 'corpus'),
    (0x7C4, '>2i', 'scale_sections', 'corpus'),   # % of life
    (0x7CC, '>2f', 'scale_random', 'corpus'),
    (0x7D4, '>2f', 'scale', 'corpus'),            # base particle size x, y
    (0x7DC, '>2f', 'scale_init_ratio', 'corpus'),
    (0x7E4, '>2f', 'scale_diff21', 'guess'),
    (0x7EC, '>2f', 'scale_diff32', 'guess'),
    (0x7F8, '>3f', 'rotation_init', 'corpus'),    # radians
    (0x804, '>3f', 'rotation_random', 'corpus'),
    (0x810, '>3f', 'rotation_velocity', 'corpus'),
    (0x81C, '>3f', 'rotation_velocity_random', 'corpus'),
    (0x828, '>f', 'rotation_attenuation', 'corpus'),
    (0x844, '>I', 'shader_index', 'runtime'),     # into the shader table (shader-keyed fields must match it)
]
FIELD = {f[2]: f for f in FIELDS}
TEX_FIELDS = [            # within a TexRes (only these 0x38 bytes are stored; the rest is runtime)
    (0x00, '>2H', 'size'), (0x04, '>I', 'tile_mode'), (0x08, '>I', 'swizzle'), (0x0C, '>I', 'sampler'),
    (0x10, '>I', 'mip_levels'), (0x14, '>I', 'comp_sel'), (0x18, '>f', 'enable_mip_level'),
    (0x1C, '>f', 'mip_bias'), (0x20, '>I', 'original_format'), (0x24, '>I', 'original_pos'),
    (0x28, '>I', 'original_size'), (0x2C, '>I', 'native_format'), (0x30, '>I', 'native_size'),
    (0x34, '>I', 'native_pos')]


def emitter_size(em):
    """an emitter's own data size: 0x8BC simple, the complex header's size field"""
    return SIMPLE_SIZE if be32(em, 0) != 1 else be32(em, 0x8D0)


class Ptcl:
    def __init__(self, data):
        d = bytes(data)
        assert d[:4] == MAGIC, 'not an EFTF file'
        self.version = be32(d, 4)
        h = struct.unpack_from('>15I', d, 0)
        (_m, _v, nsets, self.file_name_pos, name_pos, tex_pos, tex_size, sh_pos, sh_size, an_pos, an_size,
         pr_pos, pr_size, sp_pos, sp_size) = h
        self.le_totals = list(struct.unpack_from('<3I', d, 0x3C))
        # emitter sets, their tables and emitters
        self.sets = []
        order = []
        for i in range(nsets):
            u, upd, npos, rt0, n, tbl, rt1 = struct.unpack_from('>7I', d, HEADER_SIZE + SET_SIZE * i)
            ems = []
            for k in range(n):
                pos, a, b, c = struct.unpack_from('>4I', d, tbl + TBL_ENTRY * k)
                ems.append({'pos': pos, 'rt': (a, b, c), 'data': None})
            self.sets.append({'user': u, 'updated': upd, 'name_pos': npos, 'rt': (rt0, rt1), 'tbl': tbl, 'emitters': ems})
            order.append(('t', i, tbl))
            for k, e in enumerate(ems):
                if e['pos']:
                    order.append(('e', (i, k), e['pos']))
        order.sort(key=lambda o: o[2])
        # sizes from the data; check the layout is [table, its emitters] per set, in order
        expect = HEADER_SIZE + SET_SIZE * nsets
        self.canonical = True
        for kind, ref, pos in order:
            if pos != expect:
                self.canonical = False
            if kind == 't':
                expect = pos + TBL_ENTRY * len(self.sets[ref]['emitters'])
            else:
                i, k = ref
                size = emitter_size(d[pos:pos + 0x8D4])
                self.sets[i]['emitters'][k]['data'] = bytearray(d[pos:pos + size])
                expect = pos + size
        self.emitter_end = expect
        self.emitter_pad = d[expect:tex_pos]
        assert not any(self.emitter_pad), 'non-zero bytes before the texture table'
        self.tex = bytearray(d[tex_pos:tex_pos + tex_size])
        self.tex_pos_orig = tex_pos
        self.names = bytearray(d[name_pos:sh_pos])
        self.shader = bytearray(d[sh_pos:sh_pos + sh_size])
        self.gap_sh = d[sh_pos + sh_size:an_pos]
        self.keyanim = bytearray(d[an_pos:an_pos + an_size])
        self.gap_an = d[an_pos + an_size:pr_pos]
        self.prim = bytearray(d[pr_pos:pr_pos + pr_size])
        self.gap_pr = d[pr_pos + pr_size:sp_pos]
        self.sparam = bytearray(d[sp_pos:sp_pos + sp_size])
        self.tail = d[sp_pos + sp_size:]              # nothing, or -4 (see eof_short)
        self.eof_short = len(d) - (sp_pos + sp_size)  # -4 when the shader param table is empty
        if self.eof_short < 0:                       # (the stated gap runs past the end: keep it whole)
            self.gap_pr = self.gap_pr + bytes(-self.eof_short)
        self.dirty_layout = False

    # ---------------------------------------------------------------- build
    def build(self):
        out = bytearray(HEADER_SIZE + SET_SIZE * len(self.sets))
        pos = len(out)
        set_tbl = []
        for s in self.sets:
            set_tbl.append(pos)
            pos += TBL_ENTRY * len(s['emitters'])
            for e in s['emitters']:
                if e['data'] is not None:
                    e['_pos'] = pos
                    pos += len(e['data'])
                else:
                    e['_pos'] = 0
        emitter_end = pos
        if not self.dirty_layout and emitter_end == self.emitter_end:
            tex_pos = self.tex_pos_orig
        else:
            tex_pos = align(emitter_end, 0x2000)
        for i, s in enumerate(self.sets):
            struct.pack_into('>7I', out, HEADER_SIZE + SET_SIZE * i, s['user'], s['updated'], s['name_pos'],
                             s['rt'][0], len(s['emitters']), set_tbl[i], s['rt'][1])
        for i, s in enumerate(self.sets):
            out += b''.join(struct.pack('>4I', e['_pos'], *e['rt']) for e in s['emitters'])
            for e in s['emitters']:
                if e['data'] is not None:
                    out += e['data']
        out += bytes(tex_pos - len(out))
        out += self.tex
        name_pos = len(out)
        if self.dirty_layout:                        # the vanilla rule: 1-16 zeros, the shader table 16-aligned
            end = len(self.names.rstrip(b'\0')) + 1
            self.names = bytearray(self.names[:end] + bytes(align(name_pos + end + 1, 0x10) - (name_pos + end)))
        out += self.names
        sh_pos = len(out)
        out += self.shader
        out += self.gap_sh if not self.dirty_layout else bytes(align(len(out) + 4, 0x10) - len(out))
        an_pos = len(out)
        out += self.keyanim
        out += self.gap_an if not self.dirty_layout else bytes(align(len(out) + 4, 0x10) - len(out))
        pr_pos = len(out)
        out += self.prim
        out += self.gap_pr if not self.dirty_layout else bytes(align(len(out) + 4, 0x10) - len(out))
        sp_pos = len(out)
        out += self.sparam
        if self.eof_short < 0:
            del out[len(out) + self.eof_short:]
        else:
            out += self.tail
        struct.pack_into('>15I', out, 0, be32(MAGIC, 0), self.version, len(self.sets), self.file_name_pos,
                         name_pos, tex_pos, len(self.tex), sh_pos, len(self.shader), an_pos, len(self.keyanim),
                         pr_pos, len(self.prim), sp_pos, len(self.sparam))
        totals = self.le_totals if not self.dirty_layout else [
            len(self.tex), len(self.shader) - be32(self.shader, 0x10) - SHADER_ENTRY * be32(self.shader, 0),
            sum(len(e['data']) for s in self.sets for e in s['emitters'] if e['data'] is not None)]
        struct.pack_into('<3I', out, 0x3C, *totals)
        return bytes(out)

    # ---------------------------------------------------------------- names
    def name_at(self, pos):
        return self.names[pos:self.names.index(b'\0', pos)].decode('ascii', 'replace')

    def set_name(self, i):
        return self.name_at(self.sets[i]['name_pos'])

    def emitter_name(self, em):
        return self.name_at(be32(em, 0x38))

    def find_set(self, name):
        for i, s in enumerate(self.sets):
            if self.set_name(i) == name:
                return i
        raise KeyError(name)

    def add_name(self, s):
        """a string in the name table (reused if already there): its offset"""
        b = s.encode('ascii') + b'\0'
        i = self.names.find(b'\0' + b) + 1 if self.names.find(b'\0' + b) >= 0 else -1
        if self.names.startswith(b):
            return 0
        if i > 0:
            return i
        end = len(self.names.rstrip(b'\0')) + 1      # after the last string's terminator
        self.names = bytearray(self.names[:end] + b)  # (padded in build: 1-16 zeros to a 16-byte boundary)
        self.dirty_layout = True
        return end

    # ---------------------------------------------------------------- fields
    def field(self, em, name):
        off, fmt, _n, _c = FIELD[name]
        v = struct.unpack_from(fmt, em, off)
        return v[0] if len(v) == 1 else list(v)

    def set_field(self, em, name, value):
        off, fmt, _n, _c = FIELD[name]
        vals = value if isinstance(value, (list, tuple)) else [value]
        struct.pack_into(fmt, em, off, *vals)

    def set_emitter_srt(self, em, scale=(1, 1, 1), rotation=(0, 0, 0), translation=(0, 0, 0)):
        """the emitter's transform (rotation in radians, applied X then Y then Z) and its matrix"""
        cx, cy, cz = np.cos(rotation)
        sx, sy, sz = np.sin(rotation)
        r = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
             @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])) * np.array(scale, float)[None, :]
        m = np.concatenate([r, np.array(translation, float)[:, None]], 1)
        self.set_field(em, 'emitter_matrix', [float(v) for v in m.ravel()])
        self.set_field(em, 'emitter_scale', [float(v) for v in scale])
        self.set_field(em, 'emitter_rotation', [float(v) for v in rotation])
        self.set_field(em, 'emitter_translation', [float(v) for v in translation])

    def color_keys(self, em, track):
        k = self.field(em, 'color%d_keys' % track)
        return [tuple(k[4 * i:4 * i + 4]) for i in range(8)]

    def set_color_keys(self, em, track, keys, typ=None):
        flat = []
        for i in range(8):
            flat += list(keys[min(i, len(keys) - 1)])
        self.set_field(em, 'color%d_keys' % track, flat)
        if typ is not None:
            self.set_field(em, 'color%d_type' % track, typ)

    def texres(self, em, slot, child=False):
        o = (CHILD_TEXRES if child else TEXRES + TEXRES_SIZE * slot)
        out = {}
        for off, fmt, name in TEX_FIELDS:
            v = struct.unpack_from(fmt, em, o + off)
            out[name] = v[0] if len(v) == 1 else list(v)
        return out

    # ---------------------------------------------------------------- textures
    def surface(self, w, h, gx2fmt, tile_mode=4, swizzle=0):
        bc = nut._is_bc(gx2fmt)
        ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
        pitch = align(ew, 32)
        size = pitch * align(eh, 16) * (nut._bpp(gx2fmt) // 8)

        class S:
            pass
        s = S()
        s.fmt, s.w, s.h, s.tile_mode, s.swizzle, s.pitch, s.image_size = gx2fmt, w, h, tile_mode, swizzle, pitch, size
        s.data_off = 0
        return s

    def decode_texture(self, em, slot, child=False):
        t = self.texres(em, slot, child)
        w, h = t['size']
        if not w or not t['native_size']:
            return None
        gx2 = EFT_GX2.get(t['native_format'])
        if gx2 is None:
            raise NotImplementedError('eft texture format %d' % t['native_format'])
        s = self.surface(w, h, gx2, t['tile_mode'], t['swizzle'])
        s.image_size = min(s.image_size, t['native_size'])
        s.data_off = t['native_pos']
        img = nut.decode(bytes(self.tex), s)
        sel = t['comp_sel']
        chans = [(sel >> (24 - 8 * i)) & 0xFF for i in range(4)]
        src = np.concatenate([img, np.zeros_like(img[..., :1]), np.full_like(img[..., :1], 255)], 2)
        return np.stack([src[..., c if c < 4 else (4 if c == 4 else 5)] for c in chans], 2)

    def add_texture(self, rgba, gx2fmt=0x33):
        """RGBA [h, w, 4] as one GX2 mip (tile mode 4, swizzle 0) appended to the texture table"""
        h, w = rgba.shape[:2]
        s = self.surface(w, h, gx2fmt)
        data = nut.encode(np.ascontiguousarray(rgba, dtype=np.uint8), s)
        # the same image added again (e.g. emitters sharing a texture): the first copy's place
        if not hasattr(self, '_tex_added'):
            self._tex_added = {}
        key = (bytes(data), w, h, gx2fmt)
        if key in self._tex_added:
            return self._tex_added[key], len(data), {'w': w, 'h': h, 'gx2': gx2fmt}
        pos = align(len(self.tex), GX2_ALIGN[gx2fmt])      # vanilla's: BC4 0x1000 (2588 of them), BC3 0x2000
        self._tex_added[key] = pos
        self.tex += bytes(pos - len(self.tex)) + data
        self.dirty_layout = True
        return pos, len(data), {'w': w, 'h': h, 'gx2': gx2fmt}

    def set_texture(self, em, slot, rgba, gx2fmt=None, child=False, comp_sel=None):
        """comp_sel: the channel selectors to store (default: the format's, or the template's own)"""
        o = (CHILD_TEXRES if child else TEXRES + TEXRES_SIZE * slot)
        t = self.texres(em, slot, child)
        if gx2fmt is None:
            gx2fmt = EFT_GX2.get(t['native_format'], 0x33) & 0x3F
        pos, size, m = self.add_texture(rgba, gx2fmt)
        h, w = rgba.shape[:2]
        struct.pack_into('>HHII', em, o, w, h, 4, 0)
        if not t['size'][0]:
            struct.pack_into('>I', em, o + 0x0C, 0x100)           # the common sampler word
            struct.pack_into('>f', em, o + 0x18, 15.99)
        struct.pack_into('>I', em, o + 0x10, 1)                   # one mip
        if comp_sel is None:
            comp_sel = COMP_SEL[gx2fmt] if t['comp_sel'] == 0 or gx2fmt != (
                EFT_GX2.get(t['native_format'], 0) & 0x3F) else t['comp_sel']
        struct.pack_into('>I', em, o + 0x14, comp_sel)
        struct.pack_into('>IIIIII', em, o + 0x20, 2, 0, w * h * 4, GX2_EFT[gx2fmt], size, pos)
        return pos

    # ---------------------------------------------------------------- sets and emitters
    def emitter_bytes(self, set_index, k):
        return bytearray(self.sets[set_index]['emitters'][k]['data'])

    def clone_set(self, src, new_name):
        s = self.sets[src if isinstance(src, int) else self.find_set(src)]
        new = {'user': s['user'], 'updated': s['updated'], 'name_pos': self.add_name(new_name), 'rt': (0, 0),
               'tbl': 0, 'emitters': [{'pos': 0, 'rt': (0, 0, 0), 'data': bytearray(e['data'])
                                       if e['data'] is not None else None} for e in s['emitters']]}
        self.sets.append(new)
        self.dirty_layout = True
        return len(self.sets) - 1

    def new_set(self, name, emitters, emitter_names=None):
        new = {'user': 0, 'updated': 0, 'name_pos': self.add_name(name), 'rt': (0, 0), 'tbl': 0, 'emitters': []}
        for k, em in enumerate(emitters):
            em = bytearray(em)
            if emitter_names:
                struct.pack_into('>I', em, 0x38, self.add_name(emitter_names[k]))
            new['emitters'].append({'pos': 0, 'rt': (0, 0, 0), 'data': em})
        self.sets.append(new)
        self.dirty_layout = True
        return len(self.sets) - 1

    # ---------------------------------------------------------------- shaders / primitives
    def shader_count(self):
        return be32(self.shader, 0)

    def shader_entry(self, i):
        eo = be32(self.shader, 0x14) + SHADER_ENTRY * i
        return self.shader[eo:eo + SHADER_ENTRY]

    def shader_binary(self, i):
        e = self.shader_entry(i)
        size, off = struct.unpack_from('>II', e, 0x68)
        base = be32(self.shader, 0x10)
        return self.shader[base + off:base + off + size]

    def import_shader(self, other, i):
        """shader i of another Ptcl (its key entry + GFX2 binary) appended here: its new index"""
        return self.add_shader(other.shader_entry(i), other.shader_binary(i))

    def add_shader(self, entry, binary):
        """a shader (0x78 key entry, GFX2 vertex + pixel binary) appended: its index"""
        entry = bytearray(entry)
        n, base, eo = be32(self.shader, 0), be32(self.shader, 0x10), be32(self.shader, 0x14)
        bins = self.shader[base:eo]
        entries = self.shader[eo:eo + SHADER_ENTRY * n]
        off = align(len(bins), 0x100)       # GFX2 binaries start 0x100-aligned within the block
        struct.pack_into('>II', entry, 0x68, len(binary), off)
        bins = bins + bytes(off - len(bins)) + binary
        head = bytearray(self.shader[:base])
        struct.pack_into('>I', head, 0, n + 1)
        struct.pack_into('>I', head, 0x14, base + len(bins))
        self.shader = head + bins + entries + entry
        struct.pack_into('>I', self.shader, 4, len(self.shader))
        self.dirty_layout = True
        return n

    def drop_unused_shaders(self, first):
        """shaders from index `first` on that no emitter uses removed and the rest renumbered (a
        converter's imported templates whose pixel program it replaced: 51 of Hero's 320, 0.5 MB):
        how many. Those below `first` stay whatever uses them (complex emitters' children carry
        their own indices)"""
        n = self.shader_count()
        used = {be32(x['data'], 0x844) for s in self.sets for x in s['emitters'] if x['data'] is not None}
        keep = [i for i in range(n) if i < first or i in used]
        if len(keep) == n:
            return 0
        base = be32(self.shader, 0x10)
        head = bytearray(self.shader[:base])
        bins, entries, remap, placed = bytearray(), bytearray(), {}, {}
        for new, i in enumerate(keep):
            entry, binary = bytearray(self.shader_entry(i)), self.shader_binary(i)
            key = struct.unpack_from('>II', entry, 0x68)
            if key not in placed:               # entries sharing a binary keep sharing it
                placed[key] = align(len(bins), 0x100)       # as add_shader
                bins += bytes(placed[key] - len(bins)) + binary
            struct.pack_into('>II', entry, 0x68, len(binary), placed[key])
            entries += entry
            remap[i] = new
        struct.pack_into('>I', head, 0, len(keep))
        struct.pack_into('>I', head, 0x14, base + len(bins))
        self.shader = head + bins + entries
        struct.pack_into('>I', self.shader, 4, len(self.shader))
        for s in self.sets:
            for x in s['emitters']:
                if x['data'] is not None:
                    struct.pack_into('>I', x['data'], 0x844, remap[be32(x['data'], 0x844)])
        self.dirty_layout = True
        return n - len(keep)

    def import_emitter(self, other, set_index, k, skip_slots=(), _shaders={}):
        """emitter k of another Ptcl's set, adapted to this one: its shader imported (once per source
        shader), its shader-parameter range copied, its used texture slots' data copied (not
        skip_slots': the caller replaces them), no key animation, no primitive (-1). Returns the
        bytes (for new_set / set_texture)."""
        em = other.emitter_bytes(set_index, k)
        key = (id(other), be32(em, 0x844))
        if key not in _shaders or _shaders[key][0] is not self:
            _shaders[key] = (self, self.import_shader(other, be32(em, 0x844)))
        struct.pack_into('>I', em, 0x844, _shaders[key][1])
        size, pos = be32(em, 0x2EC), be32(em, 0x2F0)
        if size:
            at = align(len(self.sparam), 4)
            self.sparam += bytes(at - len(self.sparam)) + other.sparam[pos:pos + size]
            struct.pack_into('>I', em, 0x2F0, at)
        struct.pack_into('>II', em, 0x2CC, 0, 0)
        struct.pack_into('>i', em, 0x2DC, -1)
        for slot in range(TEX_SLOTS):
            o = TEXRES + TEXRES_SIZE * slot
            t = self.texres(em, slot)
            if t['native_size'] and slot not in skip_slots:
                data = other.tex[t['native_pos']:t['native_pos'] + t['native_size']]
                at = align(len(self.tex), 0x2000)
                self.tex += bytes(at - len(self.tex)) + data
                struct.pack_into('>I', em, o + 0x34, at)
        self.dirty_layout = True
        return em

    def add_primitive(self, pos, nrm, col, uv, idx):
        """a mesh appended to the primitive table: its index. pos / nrm [n, 3], col [n, 4] (RGBA 0-1),
        uv [n, 2] or [n, 4] (two UV sets), idx [m] triangle list; nrm / col may be None.
        Table: u32 count, u32 total size, u32 entry offset (0xC); 0x50 entries of five
        (float count, components, offset, byte size) attributes: position, normal, colour, UV (4),
        index (u32); offsets from the data after the entries; big-endian floats. The data goes in
        vanilla's order: position, normal, UV, colour, index."""
        pos = np.asarray(pos, '>f4').reshape(-1, 3)
        n = len(pos)
        uv = np.asarray(uv, np.float32).reshape(n, -1)
        if uv.shape[1] == 2:
            uv = np.concatenate([uv, uv], 1)
        attrs = [(pos, 3), (None if nrm is None else np.asarray(nrm, '>f4').reshape(n, 3), 3),
                 (None if col is None else np.asarray(col, '>f4').reshape(n, 4), 4),
                 (uv.astype('>f4'), 4), (np.asarray(idx, '>u4').reshape(-1), 1)]
        if self.prim:
            count, _total, eo = struct.unpack_from('>3I', self.prim, 0)
            entries = bytes(self.prim[eo:eo + 0x50 * count])
            data = bytes(self.prim[eo + 0x50 * count:])
        else:
            count, entries, data = 0, b'', b''
        data = bytearray(data)
        # stored as every vanilla mesh is (all 825: position, normal, UV, colour, index, contiguous),
        # whatever the entry's slot order (eft reads each attribute at its own offset, 0x04A6CF74:
        # the order is only for likeness)
        slots = [None] * 5
        for k in (0, 1, 3, 2, 4):
            arr, comps = attrs[k]
            if arr is None:
                slots[k] = struct.pack('>4I', 0, 0, 0, 0)
                continue
            raw = arr.tobytes()
            slots[k] = struct.pack('>4I', arr.size, comps, len(data), len(raw))
            data += raw
        entry = b''.join(slots)
        body = entries + entry + bytes(data)
        self.prim = bytearray(struct.pack('>3I', count + 1, 12 + len(body), 12)) + body
        self.dirty_layout = True
        return count

    def primitive_count(self):
        return be32(self.prim, 0) if self.prim else 0

    # ---------------------------------------------------------------- checks
    def validate(self):
        """what the runtime resolves (0x04A6CD18 ff.), checked: names, textures (slots and the child's),
        key animations, shader params, shader and primitive indices, complex sizes. [] = fine"""
        errs = []
        nsh, npr = self.shader_count(), self.primitive_count()

        def name_ok(pos):
            return pos < len(self.names) and b'\0' in self.names[pos:]
        if not name_ok(self.file_name_pos):
            errs.append('file name')
        for i, s in enumerate(self.sets):
            if not name_ok(s['name_pos']):
                errs.append('set %d name' % i)
            for k, e in enumerate(s['emitters']):
                em, tag = e['data'], 'set %d emitter %d' % (i, k)
                if em is None:
                    continue
                if len(em) != emitter_size(em):
                    errs.append(tag + ': size')
                if not name_ok(be32(em, 0x38)):
                    errs.append(tag + ': name')
                texs = [(j, False) for j in range(3)]
                if be32(em, 0) == 1 and be32(em, 0x8BC) & 1:
                    texs.append((0, True))
                for j, child in texs:
                    t = self.texres(em, j, child)
                    if t['native_size'] and t['native_pos'] + t['native_size'] > len(self.tex):
                        errs.append(tag + ': texture %d%s past the table' % (j, ' (child)' if child else ''))
                    if not child and j == 0 and not t['native_size'] and not t['original_size']:
                        errs.append(tag + ': no texture in slot 0')
                if be32(em, 0x2D0) and be32(em, 0x2CC) + be32(em, 0x2D0) > len(self.keyanim):
                    errs.append(tag + ': key animation past the table')
                if be32(em, 0x2EC) and be32(em, 0x2F0) + be32(em, 0x2EC) > len(self.sparam):
                    errs.append(tag + ': shader params past the table')
                if be32(em, 0x844) >= nsh:
                    errs.append(tag + ': shader index')
                pi = struct.unpack_from('>i', em, 0x2DC)[0]
                if pi >= npr:
                    errs.append(tag + ': primitive index')
        return errs

    # ---------------------------------------------------------------- dump
    def info(self):
        lines = ['EFTF v0x%X, %d emitter sets, file name %r' % (self.version, len(self.sets), self.name_at(self.file_name_pos)),
                 'textures %d bytes, shaders %d (%d bytes), key anims %d, primitives %d (%d bytes), shader params %d'
                 % (len(self.tex), self.shader_count(), len(self.shader), len(self.keyanim), self.primitive_count(),
                    len(self.prim), len(self.sparam))]
        for i, s in enumerate(self.sets):
            lines.append('set %d %s: %d emitters' % (i, self.set_name(i), len(s['emitters'])))
            for k, e in enumerate(s['emitters']):
                em = e['data']
                if em is None:
                    lines.append('   %d (none)' % k)
                    continue
                tx = ['%dx%d/%d' % (*self.texres(em, j)['size'], self.texres(em, j)['native_format'])
                      for j in range(3) if self.texres(em, j)['size'][0]]
                lines.append('   %d %-24s %s 0x%X shader %d prim %d life %d rate %.3g tex %s' % (
                    k, self.emitter_name(em), 'complex' if be32(em, 0) == 1 else 'simple', len(em),
                    self.field(em, 'shader_index'), self.field(em, 'primitive_index'), self.field(em, 'ptcl_life'),
                    self.field(em, 'emit_rate'), ' '.join(tx)))
        return '\n'.join(lines)

    def emitter_params(self, em):
        out = {'name': self.emitter_name(em)}
        for off, fmt, name, conf in FIELDS:
            v = self.field(em, name)
            out[name] = v
        out['textures'] = [self.texres(em, j) for j in range(3)]
        if be32(em, 0) == 1:
            h = struct.unpack_from('>IHHHHHHHHI', em, 0x8BC)
            out['complex'] = dict(zip(['child_flags', 'field_flags', 'fluctuation_flags', 'stripe_flags', 'pad',
                                       'child_offset', 'field_offset', 'fluctuation_offset', 'stripe_offset',
                                       'size'], h))
        return out


def main():
    cmd = sys.argv[1]
    if cmd == 'info':
        print(Ptcl(open(sys.argv[2], 'rb').read()).info())
    elif cmd == 'roundtrip':
        ok = 0
        for f in sys.argv[2:]:
            d = open(f, 'rb').read()
            p = Ptcl(d)
            same = p.build() == d
            ok += same
            if not same:
                print('DIFF', f)
        print('%d / %d byte-exact' % (ok, len(sys.argv) - 2))
    elif cmd == 'dump':
        from PIL import Image
        p = Ptcl(open(sys.argv[2], 'rb').read())
        out = sys.argv[3]
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, 'info.txt'), 'w').write(p.info())
        params, done = [], {}
        for i, s in enumerate(p.sets):
            for k, e in enumerate(s['emitters']):
                if e['data'] is None:
                    continue
                params.append({'set': p.set_name(i), 'index': k, **p.emitter_params(e['data'])})
                for j in range(3):
                    t = p.texres(e['data'], j)
                    key = (t['native_pos'], t['native_size'])
                    if t['size'][0] and t['native_size'] and key not in done:
                        try:
                            img = p.decode_texture(e['data'], j)
                        except NotImplementedError:
                            continue
                        fn = 'tex_%06x_%dx%d_f%d.png' % (t['native_pos'], t['size'][0], t['size'][1], t['native_format'])
                        Image.fromarray(img).save(os.path.join(out, fn))
                        done[key] = fn
        json.dump(params, open(os.path.join(out, 'emitters.json'), 'w'), indent=1)
        print('%d emitters, %d textures -> %s' % (len(params), len(done), out))


if __name__ == '__main__':
    main()
