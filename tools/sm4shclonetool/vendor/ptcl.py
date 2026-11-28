"""Particle files (.ptcl, EFTF v0x42, NintendoWare for Cafe eft): read and rebuild byte for byte; emitter sets,
emitters, textures, shaders, key animations and primitives; copy an emitter set from another file (its textures,
shader, shader parameters and mesh with it).

Adapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; the tool
sets the code addresses itself, see its README "The executable")."""
import json
import os
import struct
import sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import nut
MAGIC, VERSION = (b'EFTF', 66)
HEADER_SIZE, SET_SIZE, TBL_ENTRY = (72, 28, 16)
SIMPLE_SIZE = 2236
TEXRES, TEXRES_SIZE, TEX_SLOTS = (64, 216, 3)
CHILD_TEXRES = 2336
SHADER_ENTRY = 120
PRIM_ENTRY = 80
EFT_GX2 = {2: 26, 3: 49, 4: 1073, 5: 50, 6: 1074, 7: 51, 8: 1075, 9: 52, 10: 564, 11: 53, 12: 565}
GX2_EFT = {26: 2, 49: 3, 50: 5, 51: 7, 52: 9, 53: 11, 1073: 4, 1074: 6, 1075: 8}
GX2_ALIGN = {26: 2048, 49: 4096, 50: 8192, 51: 8192, 52: 4096, 53: 8192, 1073: 4096, 1074: 8192, 1075: 8192}
COMP_SEL = {26: 66051, 49: 66051, 50: 66051, 51: 66051, 52: 5, 53: 1, 1073: 66051, 1074: 66051, 1075: 66051}

def be32(d, o):
    return struct.unpack_from('>I', d, o)[0]

def align(v, a):
    return -(-v // a) * a
FIELDS = [(0, '>I', 'type', 'runtime'), (4, '>I', 'flags', 'corpus'), (8, '>I', 'random_seed', 'guess'), (56, '>I', 'name_pos', 'runtime'), (716, '>I', 'keyanim_pos', 'runtime'), (720, '>I', 'keyanim_size', 'runtime'), (732, '>i', 'primitive_index', 'runtime'), (748, '>I', 'shader_param_size', 'runtime'), (752, '>I', 'shader_param_pos', 'runtime'), (760, '>B', 'world_gravity', 'verified'), (767, '>B', 'one_time', 'runtime'), (780, '>I', 'enum_30c', 'corpus'), (796, '>I', 'enum_31c', 'corpus'), (800, '>I', 'display_side', 'corpus'), (804, '>I', 'blend_type', 'corpus'), (832, '>I', 'volume_type', 'corpus'), (840, '>3f', 'volume_radius', 'corpus'), (852, '>f', 'volume_sweep_start', 'corpus'), (856, '>f', 'volume_sweep_param', 'runtime'), (860, '>f', 'volume_surface_random', 'runtime'), (771, '>B', 'volume_sweep_start_random', 'runtime'), (984, '>12f', 'emitter_matrix', 'corpus'), (1032, '>3f', 'emitter_scale', 'corpus'), (1044, '>3f', 'emitter_rotation', 'corpus'), (1056, '>3f', 'emitter_translation', 'corpus'), (1092, '>f', 'emit_rate', 'corpus'), (1096, '>i', 'emit_rate_random', 'runtime'), (1100, '>i', 'emit_start', 'runtime'), (1104, '>i', 'end_frame', 'runtime'), (1108, '>i', 'emit_interval', 'corpus'), (1112, '>i', 'emit_interval_random', 'runtime'), (1116, '>f', 'figure_velocity', 'guess'), (1120, '>f', 'init_velocity_random', 'corpus'), (1124, '>f', 'emitter_velocity', 'corpus'), (1128, '>3f', 'emit_direction', 'corpus'), (1140, '>f', 'dispersion_angle', 'corpus'), (1144, '>3f', 'spread_vec', 'guess'), (1156, '>f', 'air_resistance', 'corpus'), (1188, '>3f', 'gravity', 'corpus'), (1200, '>i', 'ptcl_life', 'runtime'), (1204, '>i', 'ptcl_life_random', 'runtime'), (1212, '>I', 'particle_type', 'corpus'), (1232, '>f', 'camera_offset', 'verified'), (1288, '>2f', 'tex0_uv_scale', 'corpus'), (1608, '>I', 'color0_type', 'corpus'), (1612, '>I', 'color1_type', 'corpus'), (1616, '>32f', 'color0_keys', 'corpus'), (1744, '>32f', 'color1_keys', 'corpus'), (1872, '>2i', 'color_section1', 'corpus'), (1880, '>2i', 'color_section2', 'corpus'), (1888, '>2i', 'color_section3', 'corpus'), (1896, '>2i', 'color_repeat', 'corpus'), (1912, '>f', 'color_scale', 'corpus'), (1924, '>f', 'alpha_init', 'corpus'), (1928, '>f', 'alpha_diff21', 'guess'), (1932, '>f', 'alpha_diff32', 'guess'), (1936, '>f', 'alpha_section1', 'corpus'), (1940, '>f', 'alpha_section2', 'corpus'), (1988, '>2i', 'scale_sections', 'corpus'), (1996, '>2f', 'scale_random', 'corpus'), (2004, '>2f', 'scale', 'corpus'), (2012, '>2f', 'scale_init_ratio', 'corpus'), (2020, '>2f', 'scale_diff21', 'guess'), (2028, '>2f', 'scale_diff32', 'guess'), (2036, '>f', 'velocity_stretch', 'verified'), (2040, '>3f', 'rotation_init', 'corpus'), (2052, '>3f', 'rotation_random', 'corpus'), (2064, '>3f', 'rotation_velocity', 'corpus'), (2076, '>3f', 'rotation_velocity_random', 'corpus'), (2088, '>f', 'rotation_attenuation', 'corpus'), (2116, '>I', 'shader_index', 'runtime')]
FIELD = {f[2]: f for f in FIELDS}
FIELD['start_frame'] = FIELD['emit_rate_random']
KEYA_TARGETS = {0: 'emission rate (0x444)', 1: 'particle life (0x4B0)', 2: 'emitter scale x', 3: 'emitter scale y', 4: 'emitter scale z', 5: 'emitter rotation x (radians)', 6: 'emitter rotation y', 7: 'emitter rotation z', 8: 'emitter translation x', 9: 'emitter translation y', 10: 'emitter translation z', 11: 'colour 0 r (0x384)', 12: 'colour 0 g', 13: 'colour 0 b', 14: 'alpha (0x3A4)', 15: 'all-direction velocity (0x45C)', 16: 'directional velocity (0x464)', 17: 'particle scale x (1)', 18: 'particle scale y (1)', 19: 'colour 1 r (0x394)', 20: 'colour 1 g', 21: 'colour 1 b', 22: 'shape scale x (0x378)', 23: 'shape scale y', 24: 'shape scale z', 28: 'random field velocity x', 29: 'random field velocity y', 30: 'random field velocity z', 31: 'magnet field power', 32: 'spin field rate (int)', 33: 'spin field outward speed', 34: 'convergence field ratio', 35: 'position-add field x', 36: 'position-add field y', 37: 'position-add field z'}
INT_TARGETS = {32}
FIELD_BLOCKS = [(0, 'random', 16, '>i3f', ('interval', 'velocity')), (1, 'magnet', 24, '>4fIB3x', ('power', 'position', 'axes', 'follow_emitter')), (2, 'spin', 12, '>IIf', ('rate', 'axis', 'outward')), (3, 'collision', 20, '>BB2xffif', ('type', 'world', 'coord', 'bounce', 'count', 'friction')), (4, 'convergence', 20, '>I4f', ('to_emitter', 'position', 'ratio')), (5, 'position_add', 16, '>3fB3x', ('position', 'world')), (6, 'curl_noise', 36, '>BB2x8f', ('interpolate', 'base_random', 'speed', 'scale', 'offset', 'power'))]
COMPLEX_FLAGS = 12582992
FLUCT_FMT, FLUCT_SIZE, FLUCT_OFF = ('>2fIf2fIf', 32, 14)
CHILD, CHILD_SIZE, CHILD_SHADERS = (2260, 776, (644, 648, 652))
INHERIT = {'velocity': 32, 'scale': 8, 'rotation': 16, 'color0': 2, 'color1': 32768, 'alpha0': 4194304, 'alpha1': 8388608, 'draw_path': 2048, 'pre_draw': 4096}
TEX_FIELDS = [(0, '>2H', 'size'), (4, '>I', 'tile_mode'), (8, '>I', 'swizzle'), (12, '>I', 'sampler'), (16, '>I', 'mip_levels'), (20, '>I', 'comp_sel'), (24, '>f', 'enable_mip_level'), (28, '>f', 'mip_bias'), (32, '>I', 'original_format'), (36, '>I', 'original_pos'), (40, '>I', 'original_size'), (44, '>I', 'native_format'), (48, '>I', 'native_size'), (52, '>I', 'native_pos')]

def emitter_size(em):
    return SIMPLE_SIZE if be32(em, 0) != 1 else be32(em, 2256)

class Ptcl:

    def __init__(self, data):
        d = bytes(data)
        assert d[:4] == MAGIC, 'not an EFTF file'
        self.version = be32(d, 4)
        h = struct.unpack_from('>15I', d, 0)
        _m, _v, nsets, self.file_name_pos, name_pos, tex_pos, tex_size, sh_pos, sh_size, an_pos, an_size, pr_pos, pr_size, sp_pos, sp_size = h
        self.le_totals = list(struct.unpack_from('<3I', d, 60))
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
        expect = HEADER_SIZE + SET_SIZE * nsets
        self.canonical = True
        for kind, ref, pos in order:
            if pos != expect:
                self.canonical = False
            if kind == 't':
                expect = pos + TBL_ENTRY * len(self.sets[ref]['emitters'])
            else:
                i, k = ref
                size = emitter_size(d[pos:pos + 2260])
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
        self.tail = d[sp_pos + sp_size:]
        self.eof_short = len(d) - (sp_pos + sp_size)
        if self.eof_short < 0:
            self.gap_pr = self.gap_pr + bytes(-self.eof_short)
        self.dirty_layout = False

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
            tex_pos = align(emitter_end, 8192)
        for i, s in enumerate(self.sets):
            struct.pack_into('>7I', out, HEADER_SIZE + SET_SIZE * i, s['user'], s['updated'], s['name_pos'], s['rt'][0], len(s['emitters']), set_tbl[i], s['rt'][1])
        for i, s in enumerate(self.sets):
            out += b''.join((struct.pack('>4I', e['_pos'], *e['rt']) for e in s['emitters']))
            for e in s['emitters']:
                if e['data'] is not None:
                    out += e['data']
        out += bytes(tex_pos - len(out))
        out += self.tex
        name_pos = len(out)
        if self.dirty_layout:
            end = len(self.names.rstrip(b'\x00')) + 1
            self.names = bytearray(self.names[:end] + bytes(align(name_pos + end + 1, 16) - (name_pos + end)))
        out += self.names
        sh_pos = len(out)
        out += self.shader
        out += self.gap_sh if not self.dirty_layout else bytes(align(len(out) + 4, 16) - len(out))
        an_pos = len(out)
        out += self.keyanim
        out += self.gap_an if not self.dirty_layout else bytes(align(len(out) + 4, 16) - len(out))
        pr_pos = len(out)
        out += self.prim
        out += self.gap_pr if not self.dirty_layout else bytes(align(len(out) + 4, 16) - len(out))
        sp_pos = len(out)
        out += self.sparam
        if self.eof_short < 0:
            del out[len(out) + self.eof_short:]
        else:
            out += self.tail
        struct.pack_into('>15I', out, 0, be32(MAGIC, 0), self.version, len(self.sets), self.file_name_pos, name_pos, tex_pos, len(self.tex), sh_pos, len(self.shader), an_pos, len(self.keyanim), pr_pos, len(self.prim), sp_pos, len(self.sparam))
        totals = self.le_totals if not self.dirty_layout else [len(self.tex), len(self.shader) - be32(self.shader, 16) - SHADER_ENTRY * be32(self.shader, 0), sum((len(e['data']) for s in self.sets for e in s['emitters'] if e['data'] is not None))]
        struct.pack_into('<3I', out, 60, *totals)
        return bytes(out)

    def name_at(self, pos):
        return self.names[pos:self.names.index(b'\x00', pos)].decode('ascii', 'replace')

    def set_name(self, i):
        return self.name_at(self.sets[i]['name_pos'])

    def emitter_name(self, em):
        return self.name_at(be32(em, 56))

    def find_set(self, name):
        for i, s in enumerate(self.sets):
            if self.set_name(i) == name:
                return i
        raise KeyError(name)

    def add_name(self, s):
        b = s.encode('ascii') + b'\x00'
        i = self.names.find(b'\x00' + b) + 1 if self.names.find(b'\x00' + b) >= 0 else -1
        if self.names.startswith(b):
            return 0
        if i > 0:
            return i
        end = len(self.names.rstrip(b'\x00')) + 1
        self.names = bytearray(self.names[:end] + b)
        self.dirty_layout = True
        return end

    def field(self, em, name):
        off, fmt, _n, _c = FIELD[name]
        v = struct.unpack_from(fmt, em, off)
        return v[0] if len(v) == 1 else list(v)

    def set_field(self, em, name, value):
        off, fmt, _n, _c = FIELD[name]
        vals = value if isinstance(value, (list, tuple)) else [value]
        struct.pack_into(fmt, em, off, *vals)

    def set_emitter_srt(self, em, scale=(1, 1, 1), rotation=(0, 0, 0), translation=(0, 0, 0)):
        cx, cy, cz = np.cos(rotation)
        sx, sy, sz = np.sin(rotation)
        r = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) * np.array(scale, float)[None, :]
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

    def key_anims(self, em):
        pos, size = struct.unpack_from('>II', em, 716)
        if not size:
            return []
        b = bytes(self.keyanim[pos:pos + size])
        assert b[:4] == b'KEYA', b[:4]
        out, o = ([], 8)
        for _ in range(be32(b, 4)):
            nk, interp, target, loop, w4, w5, blk = struct.unpack_from('>7I', b, o)
            fmt = '>fi' if target in INT_TARGETS else '>2f'
            out.append({'target': target, 'interp': interp, 'loop': loop, 'w4': w4, 'w5': w5, 'keys': [struct.unpack_from(fmt, b, o + 28 + 8 * k) for k in range(nk)]})
            o += blk
        return out

    def set_key_anims(self, em, anims):
        if not anims:
            struct.pack_into('>II', em, 716, 0, 0)
            return
        b = b'KEYA' + struct.pack('>I', len(anims))
        for a in anims:
            fmt = '>fi' if a['target'] in INT_TARGETS else '>2f'
            keys = b''.join((struct.pack(fmt, t, v) for t, v in a['keys']))
            b += struct.pack('>7I', len(a['keys']), a.get('interp', 0), a['target'], 1 if a.get('loop') else 0, a.get('w4', 100), a.get('w5', 0), 28 + len(keys)) + keys
        pos = len(self.keyanim) + 3 & ~3
        self.keyanim = bytearray(self.keyanim) + bytes(pos - len(self.keyanim)) + b
        struct.pack_into('>II', em, 716, pos, len(b))
        self.dirty_layout = True

    def fields(self, em):
        if be32(em, 0) != 1:
            return {}
        flags, o = (struct.unpack_from('>H', em, 2240)[0], struct.unpack_from('>H', em, 2250)[0])
        out = {}
        for bit, name, size, _fmt, _names in FIELD_BLOCKS:
            if flags >> bit & 1:
                out[name] = bytes(em[o:o + size])
                o += size
        return out

    @staticmethod
    def with_fields(em, blocks, fluct=None, child=None, inherit=0):
        assert len(em) == SIMPLE_SIZE, 'only a simple emitter'
        flags, body = (0, b'')
        for bit, name, size, _fmt, _names in FIELD_BLOCKS:
            if name in blocks:
                assert len(blocks[name]) == size, name
                flags |= 1 << bit
                body += blocks[name]
        out = bytearray(em) + bytes(2260 - SIMPLE_SIZE)
        if child is not None:
            assert len(child) == CHILD_SIZE
            out += child
        field_pos = len(out)
        out += body
        fl_flags, fl_pos = (FLUCT_OFF, 0)
        if fluct is not None:
            fl_flags, fl_pos = (fluct[0], len(out))
            assert len(fluct[1]) == FLUCT_SIZE
            out += fluct[1]
        struct.pack_into('>I', out, 0, 1)
        struct.pack_into('>IHHHHHHHHI', out, SIMPLE_SIZE, COMPLEX_FLAGS if child is None else inherit | 1, flags, fl_flags, 0, 0, 2260 if child is not None else 0, field_pos if flags else 0, fl_pos, 0, len(out))
        return out

    def texres(self, em, slot, child=False):
        o = CHILD_TEXRES if child else TEXRES + TEXRES_SIZE * slot
        out = {}
        for off, fmt, name in TEX_FIELDS:
            v = struct.unpack_from(fmt, em, o + off)
            out[name] = v[0] if len(v) == 1 else list(v)
        return out

    def surface(self, w, h, gx2fmt, tile_mode=4, swizzle=0):
        bc = nut._is_bc(gx2fmt)
        ew, eh = ((w + 3) // 4, (h + 3) // 4) if bc else (w, h)
        pitch = align(ew, 32)
        size = pitch * align(eh, 16) * (nut._bpp(gx2fmt) // 8)

        class S:
            pass
        s = S()
        s.fmt, s.w, s.h, s.tile_mode, s.swizzle, s.pitch, s.image_size = (gx2fmt, w, h, tile_mode, swizzle, pitch, size)
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
        chans = [sel >> 24 - 8 * i & 255 for i in range(4)]
        src = np.concatenate([img, np.zeros_like(img[..., :1]), np.full_like(img[..., :1], 255)], 2)
        return np.stack([src[..., c if c < 4 else 4 if c == 4 else 5] for c in chans], 2)

    def add_texture(self, rgba, gx2fmt=51):
        h, w = rgba.shape[:2]
        s = self.surface(w, h, gx2fmt)
        data = nut.encode(np.ascontiguousarray(rgba, dtype=np.uint8), s)
        if not hasattr(self, '_tex_added'):
            self._tex_added = {}
        key = (bytes(data), w, h, gx2fmt)
        if key in self._tex_added:
            return (self._tex_added[key], len(data), {'w': w, 'h': h, 'gx2': gx2fmt})
        pos = align(len(self.tex), GX2_ALIGN[gx2fmt])
        self._tex_added[key] = pos
        self.tex += bytes(pos - len(self.tex)) + data
        self.dirty_layout = True
        return (pos, len(data), {'w': w, 'h': h, 'gx2': gx2fmt})

    def set_texture(self, em, slot, rgba, gx2fmt=None, child=False, comp_sel=None):
        o = CHILD_TEXRES if child else TEXRES + TEXRES_SIZE * slot
        t = self.texres(em, slot, child)
        if gx2fmt is None:
            gx2fmt = EFT_GX2.get(t['native_format'], 51) & 63
        pos, size, m = self.add_texture(rgba, gx2fmt)
        h, w = rgba.shape[:2]
        struct.pack_into('>HHII', em, o, w, h, 4, 0)
        if not t['size'][0]:
            struct.pack_into('>I', em, o + 12, 256)
            struct.pack_into('>f', em, o + 24, 15.99)
        struct.pack_into('>I', em, o + 16, 1)
        if comp_sel is None:
            comp_sel = COMP_SEL[gx2fmt] if t['comp_sel'] == 0 or gx2fmt != EFT_GX2.get(t['native_format'], 0) & 63 else t['comp_sel']
        struct.pack_into('>I', em, o + 20, comp_sel)
        struct.pack_into('>IIIIII', em, o + 32, 2, 0, w * h * 4, GX2_EFT[gx2fmt], size, pos)
        return pos

    def emitter_bytes(self, set_index, k):
        return bytearray(self.sets[set_index]['emitters'][k]['data'])

    def clone_set(self, src, new_name):
        s = self.sets[src if isinstance(src, int) else self.find_set(src)]
        new = {'user': s['user'], 'updated': s['updated'], 'name_pos': self.add_name(new_name), 'rt': (0, 0), 'tbl': 0, 'emitters': [{'pos': 0, 'rt': (0, 0, 0), 'data': bytearray(e['data']) if e['data'] is not None else None} for e in s['emitters']]}
        self.sets.append(new)
        self.dirty_layout = True
        return len(self.sets) - 1

    def new_set(self, name, emitters, emitter_names=None):
        new = {'user': 0, 'updated': 0, 'name_pos': self.add_name(name), 'rt': (0, 0), 'tbl': 0, 'emitters': []}
        for k, em in enumerate(emitters):
            em = bytearray(em)
            if emitter_names:
                struct.pack_into('>I', em, 56, self.add_name(emitter_names[k]))
            new['emitters'].append({'pos': 0, 'rt': (0, 0, 0), 'data': em})
        self.sets.append(new)
        self.dirty_layout = True
        return len(self.sets) - 1

    def shader_count(self):
        return be32(self.shader, 0)

    def shader_entry(self, i):
        eo = be32(self.shader, 20) + SHADER_ENTRY * i
        return self.shader[eo:eo + SHADER_ENTRY]

    def shader_binary(self, i):
        e = self.shader_entry(i)
        size, off = struct.unpack_from('>II', e, 104)
        base = be32(self.shader, 16)
        return self.shader[base + off:base + off + size]

    def import_shader(self, other, i):
        return self.add_shader(other.shader_entry(i), other.shader_binary(i))

    def add_shader(self, entry, binary):
        entry = bytearray(entry)
        n, base, eo = (be32(self.shader, 0), be32(self.shader, 16), be32(self.shader, 20))
        bins = self.shader[base:eo]
        entries = self.shader[eo:eo + SHADER_ENTRY * n]
        off = align(len(bins), 256)
        struct.pack_into('>II', entry, 104, len(binary), off)
        bins = bins + bytes(off - len(bins)) + binary
        head = bytearray(self.shader[:base])
        struct.pack_into('>I', head, 0, n + 1)
        struct.pack_into('>I', head, 20, base + len(bins))
        self.shader = head + bins + entries + entry
        struct.pack_into('>I', self.shader, 4, len(self.shader))
        self.dirty_layout = True
        return n

    def drop_unused_shaders(self, first):
        n = self.shader_count()
        used = {be32(em, o) for em in self.shader_users() for o in self.shader_slots(em)}
        keep = [i for i in range(n) if i < first or i in used]
        if len(keep) == n:
            return 0
        base = be32(self.shader, 16)
        head = bytearray(self.shader[:base])
        bins, entries, remap, placed = (bytearray(), bytearray(), {}, {})
        for new, i in enumerate(keep):
            entry, binary = (bytearray(self.shader_entry(i)), self.shader_binary(i))
            key = struct.unpack_from('>II', entry, 104)
            if key not in placed:
                placed[key] = align(len(bins), 256)
                bins += bytes(placed[key] - len(bins)) + binary
            struct.pack_into('>II', entry, 104, len(binary), placed[key])
            entries += entry
            remap[i] = new
        struct.pack_into('>I', head, 0, len(keep))
        struct.pack_into('>I', head, 20, base + len(bins))
        self.shader = head + bins + entries
        struct.pack_into('>I', self.shader, 4, len(self.shader))
        for em in self.shader_users():
            for o in self.shader_slots(em):
                struct.pack_into('>I', em, o, remap[be32(em, o)])
        self.dirty_layout = True
        return n - len(keep)

    def drop_unused_textures(self):
        refs = []
        for em in self.shader_users():
            offs = [TEXRES + TEXRES_SIZE * k for k in range(TEX_SLOTS)] + ([CHILD_TEXRES] if self.has_child(em) else [])
            for o in offs:
                fmt, size, pos = struct.unpack_from('>III', em, o + 44)
                if size:
                    refs.append((em, o, fmt, size, pos))
        old = bytes(self.tex)
        new, placed = (bytearray(), {})
        for _em, _o, fmt, size, pos in sorted(refs, key=lambda r: r[4]):
            if (pos, size) not in placed:
                at = align(len(new), GX2_ALIGN.get(EFT_GX2.get(fmt, 51), 8192))
                new += bytes(at - len(new)) + old[pos:pos + size]
                placed[pos, size] = at
        for em, o, _fmt, size, pos in refs:
            struct.pack_into('>I', em, o + 52, placed[pos, size])
        saved = len(old) - len(new)
        if saved:
            self.tex = new
            self._tex_added = {}
            self.dirty_layout = True
        return saved

    def shader_users(self):
        return [x['data'] for s in self.sets for x in s['emitters'] if x['data'] is not None]

    @staticmethod
    def has_child(em):
        return be32(em, 0) == 1 and be32(em, 2236) & 1 and (struct.unpack_from('>H', em, 2248)[0] == CHILD)

    @classmethod
    def shader_slots(cls, em):
        out = [2116]
        if cls.has_child(em):
            out += [CHILD + o for k, o in enumerate(CHILD_SHADERS) if k == 0 or be32(em, CHILD + o)]
        return out

    def import_emitter(self, other, set_index, k, skip_slots=(), _shaders={}):
        em = other.emitter_bytes(set_index, k)
        key = (id(other), be32(em, 2116))
        if key not in _shaders or _shaders[key][0] is not self:
            _shaders[key] = (self, self.import_shader(other, be32(em, 2116)))
        struct.pack_into('>I', em, 2116, _shaders[key][1])
        size, pos = (be32(em, 748), be32(em, 752))
        if size:
            at = align(len(self.sparam), 4)
            self.sparam += bytes(at - len(self.sparam)) + other.sparam[pos:pos + size]
            struct.pack_into('>I', em, 752, at)
        struct.pack_into('>II', em, 716, 0, 0)
        struct.pack_into('>i', em, 732, -1)
        for slot in range(TEX_SLOTS):
            o = TEXRES + TEXRES_SIZE * slot
            t = self.texres(em, slot)
            if t['native_size'] and slot not in skip_slots:
                data = other.tex[t['native_pos']:t['native_pos'] + t['native_size']]
                at = align(len(self.tex), 8192)
                self.tex += bytes(at - len(self.tex)) + data
                struct.pack_into('>I', em, o + 52, at)
        self.dirty_layout = True
        return em

    def primitive(self, i):
        count, _total, eo = struct.unpack_from('>3I', self.prim, 0)
        assert i < count
        base = eo + 80 * count
        out = []
        for k, (comps_default, dt) in enumerate(((3, '>f4'), (3, '>f4'), (4, '>f4'), (4, '>f4'), (1, '>u4'))):
            n, comps, off, size = struct.unpack_from('>4I', self.prim, eo + 80 * i + 16 * k)
            if not size:
                out.append(None)
                continue
            arr = np.frombuffer(bytes(self.prim[base + off:base + off + size]), dt)
            out.append(arr.reshape(-1, comps) if comps > 1 else arr)
        pos, nrm, col, uv, idx = out
        return (pos, nrm, col, uv, idx)

    def import_set(self, other, set_index, new_name=None):
        prims = self.__dict__.setdefault('_imported_prims', {})
        ems, names = ([], [])
        for k, e in enumerate(other.sets[set_index]['emitters']):
            src = other.emitter_bytes(set_index, k)
            em = self.import_emitter(other, set_index, k)
            pi = struct.unpack_from('>i', src, 732)[0]
            if pi >= 0:
                key = (id(other), pi)
                if key not in prims:
                    prims[key] = self.add_primitive(*other.primitive(pi))
                struct.pack_into('>i', em, 732, prims[key])
            ems.append(em)
            names.append(other.emitter_name(src))
        return self.new_set(new_name or other.set_name(set_index), ems, names)

    def add_primitive(self, pos, nrm, col, uv, idx):
        pos = np.asarray(pos, '>f4').reshape(-1, 3)
        n = len(pos)
        uv = np.asarray(uv, np.float32).reshape(n, -1)
        if uv.shape[1] == 2:
            uv = np.concatenate([uv, uv], 1)
        attrs = [(pos, 3), (None if nrm is None else np.asarray(nrm, '>f4').reshape(n, 3), 3), (None if col is None else np.asarray(col, '>f4').reshape(n, 4), 4), (uv.astype('>f4'), 4), (np.asarray(idx, '>u4').reshape(-1), 1)]
        if self.prim:
            count, _total, eo = struct.unpack_from('>3I', self.prim, 0)
            entries = bytes(self.prim[eo:eo + 80 * count])
            data = bytes(self.prim[eo + 80 * count:])
        else:
            count, entries, data = (0, b'', b'')
        data = bytearray(data)
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

    def validate(self):
        errs = []
        nsh, npr = (self.shader_count(), self.primitive_count())

        def name_ok(pos):
            return pos < len(self.names) and b'\x00' in self.names[pos:]
        if not name_ok(self.file_name_pos):
            errs.append('file name')
        for i, s in enumerate(self.sets):
            if not name_ok(s['name_pos']):
                errs.append('set %d name' % i)
            for k, e in enumerate(s['emitters']):
                em, tag = (e['data'], 'set %d emitter %d' % (i, k))
                if em is None:
                    continue
                if len(em) != emitter_size(em):
                    errs.append(tag + ': size')
                if not name_ok(be32(em, 56)):
                    errs.append(tag + ': name')
                texs = [(j, False) for j in range(3)]
                if be32(em, 0) == 1 and be32(em, 2236) & 1:
                    texs.append((0, True))
                for j, child in texs:
                    t = self.texres(em, j, child)
                    if t['native_size'] and t['native_pos'] + t['native_size'] > len(self.tex):
                        errs.append(tag + ': texture %d%s past the table' % (j, ' (child)' if child else ''))
                    if not child and j == 0 and (not t['native_size']) and (not t['original_size']):
                        errs.append(tag + ': no texture in slot 0')
                if be32(em, 720) and be32(em, 716) + be32(em, 720) > len(self.keyanim):
                    errs.append(tag + ': key animation past the table')
                if be32(em, 748) and be32(em, 752) + be32(em, 748) > len(self.sparam):
                    errs.append(tag + ': shader params past the table')
                if any((be32(em, o) >= nsh for o in self.shader_slots(em))):
                    errs.append(tag + ': shader index')
                pi = struct.unpack_from('>i', em, 732)[0]
                if pi >= npr:
                    errs.append(tag + ': primitive index')
        return errs

    def info(self):
        lines = ['EFTF v0x%X, %d emitter sets, file name %r' % (self.version, len(self.sets), self.name_at(self.file_name_pos)), 'textures %d bytes, shaders %d (%d bytes), key anims %d, primitives %d (%d bytes), shader params %d' % (len(self.tex), self.shader_count(), len(self.shader), len(self.keyanim), self.primitive_count(), len(self.prim), len(self.sparam))]
        for i, s in enumerate(self.sets):
            lines.append('set %d %s: %d emitters' % (i, self.set_name(i), len(s['emitters'])))
            for k, e in enumerate(s['emitters']):
                em = e['data']
                if em is None:
                    lines.append('   %d (none)' % k)
                    continue
                tx = ['%dx%d/%d' % (*self.texres(em, j)['size'], self.texres(em, j)['native_format']) for j in range(3) if self.texres(em, j)['size'][0]]
                lines.append('   %d %-24s %s 0x%X shader %d prim %d life %d rate %.3g tex %s' % (k, self.emitter_name(em), 'complex' if be32(em, 0) == 1 else 'simple', len(em), self.field(em, 'shader_index'), self.field(em, 'primitive_index'), self.field(em, 'ptcl_life'), self.field(em, 'emit_rate'), ' '.join(tx)))
        return '\n'.join(lines)

    def emitter_params(self, em):
        out = {'name': self.emitter_name(em)}
        for off, fmt, name, conf in FIELDS:
            v = self.field(em, name)
            out[name] = v
        out['textures'] = [self.texres(em, j) for j in range(3)]
        if be32(em, 0) == 1:
            h = struct.unpack_from('>IHHHHHHHHI', em, 2236)
            out['complex'] = dict(zip(['child_flags', 'field_flags', 'fluctuation_flags', 'stripe_flags', 'pad', 'child_offset', 'field_offset', 'fluctuation_offset', 'stripe_offset', 'size'], h))
        return out
