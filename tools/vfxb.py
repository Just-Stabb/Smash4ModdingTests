#!/usr/bin/env python3
"""Ultimate effect files (`ef_<name>.eff`: EFFN header + VFXB, Switch eft2, VFX version 22).

  python3 tools/vfxb.py info FILE.eff                     effects -> emitter sets, emitters
  python3 tools/vfxb.py dump FILE.eff OUT.json [SET ...]   every emitter's parameters

Layout ported from KillzXGaming's EffectLibrary (MIT; FileData/EFT2: EmitterList.cs,
EmitterStructs/Emitter.cs, Textures.cs, Primitives.cs), the version-22 branch of its versioned
structs:
- EFFN: +6 u16 version, +8 u32 effect count; then 16 bytes an effect (+0 u16 flags?, +4 u32 emitter
  set index + 1; the rest 0), then the effect names (upper case, zero-terminated, in order), then the
  VFXB at 0x2000 (aligned).
- VFXB: header 0x40 ('VFXB    ', u16 graphics version, u16 VFX version 22, BOM, ...), then sections
  from +0x40. A section: magic, u32 size, children / next / attribute / binary offsets (relative to
  the section, 0xFFFFFFFF none), u32, u16 child count, u16. Top level: ESTA (emitter sets: ESET ->
  EMTR, an emitter's children are child emitters, its attributes sub-sections such as EAA0 / EAA1
  emitter animations, CADP / CSDP / EAER), GRTF (textures: a BNTX and a GTNT table id -> name),
  PRMA / G3PR (primitives: BFRES models), GRSN (shaders, not used here).
- ESET binary: 16 bytes, name (64), u32 emitter count, 3 u32, 2 u32.
- EMTR binary: EmitterData (EMITTER below, 0xAC0 bytes at version 22).
"""
import json
import struct
import sys

NONE = 0xFFFFFFFF

# (name, format) or (name, [sub-layout]) or (name, [sub-layout], count); little endian
TEXPAT = [('num', 'f'), ('frequency', 'f'), ('num_random', 'f'), ('_pad', 'f'), ('table', '32i')]
TEXSCROLL = [('scroll_add', '2f'), ('scroll', '2f'), ('scroll_random', '2f'), ('scale_add', '2f'), ('scale', '2f'),
             ('scale_random', '2f'), ('rotation_add', 'f'), ('rotation', 'f'), ('rotation_random', 'f'),
             ('rotation_type', 'f'), ('uv_scale', '2f'), ('uv_div', '2f')]
KEYS = [('keys', '32f')]            # 8 keys of (x, y, z, time 0-1)
STATIC = [
    ('flags', '4I'), ('num_color0_keys', 'I'), ('num_alpha0_keys', 'I'), ('num_color1_keys', 'I'),
    ('num_alpha1_keys', 'I'), ('num_scale_keys', 'I'), ('num_param_keys', 'I'), ('_unk', '2I'),
    ('loop_rate', '5f'), ('loop_random', '5f'), ('_unk2', '2f'),
    ('gravity_dir', '3f'), ('gravity_scale', 'f'), ('air_res', 'f'), ('_val74', '3f'),
    ('center', '2f'), ('offset', 'f'), ('_pad', 'f'), ('amplitude', '2f'), ('cycle', '2f'), ('phase_rnd', '2f'),
    ('phase_init', '2f'), ('coefficient', '2f'), ('_valB8', '2f'),
    ('tex_pat', TEXPAT, 3), ('tex_scroll', TEXSCROLL, 3),
    ('color_scale', 'f'), ('_val364', '3f'),
    ('color0', KEYS), ('alpha0', KEYS), ('color1', KEYS), ('alpha1', KEYS),
    ('soft_edge', '2f'), ('fresnel_alpha', '2f'), ('near_dist_alpha', '2f'), ('far_dist_alpha', '2f'),
    ('decal', '2f'), ('alpha_threshold', 'f'), ('_pad2', 'f'), ('add_vel_to_scale', 'f'),
    ('soft_particle_dist', 'f'), ('soft_particle_volume', 'f'), ('_pad3', 'f'),
    ('scale_anim', KEYS), ('param_anim', KEYS),
    ('rotate_init', '4f'), ('rotate_init_rand', '4f'), ('rotate_add', '3f'), ('rotate_regist', 'f'),
    ('rotate_add_rand', '4f'), ('scale_limit_dist', '2f'), ('_pad5', '2f')]
INFO = [
    ('is_particle_draw', 'B'), ('sort_type', 'B'), ('calc_type', 'B'), ('follow_type', 'B'),
    ('is_fade_emit', 'B'), ('is_fade_alpha_fade', 'B'), ('is_scale_fade', 'B'), ('random_seed_type', 'B'),
    ('is_update_matrix_by_emit', 'B'), ('test_always', 'B'), ('interpolate_emission', 'B'),
    ('is_alpha_fade_in', 'B'), ('is_scale_fade_in', 'B'), ('_pad', '3B'),
    ('random_seed', 'I'), ('draw_path', 'I'), ('alpha_fade_time', 'i'), ('fade_in_time', 'i'),
    ('trans', '3f'), ('trans_rand', '3f'), ('rotate', '3f'), ('rotate_rand', '3f'), ('scale', '3f'),
    ('color0', '4f'), ('color1', '4f'), ('emission_range', '3f')]
INHERIT = [('flags', '13B'), ('_pad', '3B'), ('velocity_rate', 'f'), ('scale_rate', 'f')]
EMISSION = [
    ('one_time', 'B'), ('world_gravity', 'B'), ('emit_dist_enabled', 'B'), ('world_oriented_velocity', 'B'),
    ('start', 'I'), ('timing', 'I'), ('duration', 'I'), ('rate', 'f'), ('rate_random', 'f'), ('interval', 'i'),
    ('interval_random', 'f'), ('position_random', 'f'), ('gravity_scale', 'f'), ('gravity_dir', '3f'),
    ('dist_unit', 'f'), ('dist_min', 'f'), ('dist_max', 'f'), ('dist_marg', 'f'), ('dist_particles_max', 'i')]
SHAPE = [
    ('volume_type', 'B'), ('sweep_start_random', 'B'), ('arc_type', 'B'), ('latitude_enabled', 'B'),
    ('volume_tbl_index', 'B'), ('volume_tbl_index64', 'B'), ('latitude_dir', 'B'), ('gpu_emitter', 'B'),
    ('sweep_longitude', 'f'), ('sweep_latitude', 'f'), ('sweep_start', 'f'), ('surface_pos_rand', 'f'),
    ('caliber_ratio', 'f'), ('line_center', 'f'), ('line_length', 'f'), ('volume_radius', '3f'),
    ('volume_form_scale', '3f'), ('prim_emit_type', 'i'), ('primitive_index', 'Q'),
    ('num_divide_circle', 'i'), ('num_divide_circle_random', 'i'), ('num_divide_line', 'i'),
    ('num_divide_line_random', 'i'), ('_another_binary', '4B'), ('_pad', 'I')]
RENDER = [('blend_enable', 'B'), ('depth_test', 'B'), ('depth_func', 'B'), ('depth_mask', 'B'),
          ('alpha_test', 'B'), ('alpha_func', 'B'), ('blend_type', 'B'), ('display_side', 'B'),
          ('alpha_threshold', 'f'), ('_pad', 'I')]
PARTICLE = [
    ('infinite_life', 'B'), ('triming', 'B'), ('billboard_type', 'B'), ('rot_type', 'B'), ('offset_type', 'B'),
    ('rot_rev_rand', '3B'), ('is_rotate', '3B'), ('primitive_scale_type', 'B'), ('texture_common_random', 'B'),
    ('connect_scale_z_offset', 'B'), ('avoid_z_fighting', 'B'), ('_valF', 'B'),
    ('life', 'i'), ('life_random', 'i'), ('momentum_random', 'f'), ('primitive_vertex_flags', 'I'),
    ('primitive_id', 'Q'), ('primitive_ex_id', 'Q'), ('loop', '10B'), ('prim_flags', '2B'), ('loop_rate', '5i')]
COMBINER = [('color_process', 'B'), ('alpha_process', 'B'), ('tex1_color_blend', 'B'), ('tex2_color_blend', 'B'),
            ('prim_color_blend', 'B'), ('tex1_alpha_blend', 'B'), ('tex2_alpha_blend', 'B'),
            ('prim_alpha_blend', 'B'), ('tex_color_input', '3B'), ('tex_alpha_input', '3B'),
            ('prim_color_input', 'B'), ('prim_alpha_input', 'B'), ('shader_type', 'B'), ('apply_alpha', 'B'),
            ('distortion_by_camera_distance', 'B'), ('_pad', 'B'), ('_pad2', 'I')]
SHADER = [('type', '4B'), ('shader_index', 'i'), ('compute_shader_index', 'i'), ('user_shader_index', '2i'),
          ('custom_shader_index', 'i'), ('custom_shader_flag', 'Q'), ('custom_shader_switch', 'Q'),
          ('extra_shader_index2', 'i'), ('_val34', 'i'), ('user_shader_define', '32B')]
VELOCITY = [('all_direction', 'f'), ('designated_dir_scale', 'f'), ('designated_dir', '3f'),
            ('diffusion_dir_angle', 'f'), ('xz_diffusion', 'f'), ('diffusion', '3f'), ('vel_random', 'f'),
            ('em_vel_inherit', 'f')]
COLOR = [('soft', 'B'), ('fresnel_alpha', 'B'), ('near_dist_alpha', 'B'), ('far_dist_alpha', 'B'), ('decal', 'B'),
         ('_val5', '3B'), ('color0_type', 'B'), ('color1_type', 'B'), ('alpha0_type', 'B'), ('alpha1_type', 'B'),
         ('color0', '4f'), ('color1', '4f')]          # (r, g, b, alpha0) / (r, g, b, alpha1)
SCALE = [('scale', '3f'), ('scale_random', '3f'), ('camera_dist_near', 'B'), ('camera_dist_far', 'B'),
         ('add_scale_y', 'B'), ('link_fovy', 'B'), ('scale_min', 'f'), ('scale_max', 'f')]
FLUC = [('apply_alpha', 'B'), ('apply_scale', 'B'), ('apply_scale_y', 'B'), ('wave_type', 'B'),
        ('phase_random', '2B'), ('_pad', '2B'), ('_pad2', 'I')]
SAMPLER = [('texture_id', 'Q'), ('wrap_u', 'B'), ('wrap_v', 'B'), ('filter', 'B'), ('sphere_map', 'B'),
           ('max_lod', 'f'), ('lod_bias', 'f'), ('mip_level_limit', 'B'), ('density_fixed', '2B'),
           ('square_rgb', 'B'), ('_another_binary', '4B'), ('_pad', 'I')]
TEXANIM = [('pattern_type', 'B'), ('scroll', 'B'), ('rotate', 'B'), ('scale', 'B'), ('repeat', 'B'),
           ('inv_rand', '2B'), ('pat_loop_random', 'B'), ('uv_channel', 'B'), ('crossfade', 'B'), ('_pad', '2B'),
           ('_pad2', 'I')]
EMITTER = [
    ('flag', 'I'), ('random_seed', 'I'), ('_pad', '2I'), ('name', '64s'),
    ('static', STATIC), ('info', INFO), ('inherit', INHERIT), ('emission', EMISSION), ('shape', SHAPE),
    ('render', RENDER), ('particle', PARTICLE), ('combiner', COMBINER), ('shader', SHADER),
    ('action_index', 'I'), ('velocity', VELOCITY), ('color', COLOR), ('scale', SCALE), ('fluc', FLUC),
    ('sampler', SAMPLER, 3), ('tex_anim', TEXANIM, 3), ('_reserved', '64B')]
EMITTER_SIZE = 0xAC0
# ColorType: 0 constant, 1 random, 2 8-key animation; WrapMode / BlendType / billboard types as eft2


def layout_size(lay):
    n = 0
    for item in lay:
        if isinstance(item[1], list):
            n += layout_size(item[1]) * (item[2] if len(item) > 2 else 1)
        else:
            n += struct.calcsize('<' + item[1])
    return n


def read_layout(d, o, lay):
    out = {}
    for item in lay:
        name, fmt = item[0], item[1]
        if isinstance(fmt, list):
            cnt = item[2] if len(item) > 2 else 1
            sz = layout_size(fmt)
            vals = [read_layout(d, o + i * sz, fmt) for i in range(cnt)]
            out[name] = vals if len(item) > 2 else vals[0]
            o += sz * cnt
            continue
        sz = struct.calcsize('<' + fmt)
        v = struct.unpack_from('<' + fmt, d, o)
        if fmt.endswith('s'):
            v = v[0].split(b'\0')[0].decode('latin1')
        elif len(v) == 1:
            v = v[0]
        else:
            v = list(v)
        if not name.startswith('_'):
            out[name] = v
        o += sz
    return out


assert layout_size(EMITTER) == EMITTER_SIZE, hex(layout_size(EMITTER))


class Section:
    def __init__(self, v, o):
        self.o, self.magic = o, v[o:o + 4].decode('latin1')
        (self.size, self.child, self.next, self.attr, self.data, _p, self.count,
         _u) = struct.unpack_from('<IIIIIIHH', v, o + 4)

    def children(self, v):
        if self.child == NONE:
            return []
        out, o = [], self.o + self.child
        for _ in range(self.count):
            s = Section(v, o)
            out.append(s)
            if s.next == NONE:
                break
            o += s.next
        return out

    def attrs(self, v):
        out = []
        if self.attr in (NONE, 0):
            return out
        o = self.o + self.attr
        while True:
            s = Section(v, o)
            out.append(s)
            if s.next == NONE:
                break
            o += s.next
        return out


def top_sections(v):
    out, o = {}, 0x40
    while True:
        s = Section(v, o)
        out[s.magic] = s
        if s.next == NONE:
            break
        o += s.next
    return out


def read_emitter(v, s):
    e = read_layout(v, s.o + s.data, EMITTER)
    e['children'] = [read_emitter(v, c) for c in s.children(v)]
    e['subsections'] = {a.magic: v[a.o + a.data:a.o + a.size].hex() for a in s.attrs(v)}
    return e


class Eff:
    def __init__(self, path):
        d = open(path, 'rb').read()
        assert d[:4] == b'EFFN', d[:4]
        n = struct.unpack_from('<I', d, 8)[0]
        idx = [struct.unpack_from('<I', d, 0x10 + 16 * i + 4)[0] for i in range(n)]
        names = d[0x10 + 16 * n:].split(b'\0')[:n]
        # emitter set indices are 1-based (0: none)
        try:
            self.effects = {nm.decode().lower(): i - 1 for nm, i in zip(names, idx)}
        except UnicodeDecodeError:
            self.effects = None         # ef_common.eff: effects named by hash only, no name table
        self.vfxb = d[d.find(b'VFXB'):]
        assert struct.unpack_from('<H', self.vfxb, 10)[0] == 22, 'VFX version'
        self.top = top_sections(self.vfxb)
        self.set_sections = self.top['ESTA'].children(self.vfxb)
        self.sets = [self.vfxb[s.o + s.data + 16:s.o + s.data + 80].split(b'\0')[0].decode() for s in self.set_sections]
        if self.effects is None:
            # by emitter set name instead (P_CmnAttackLine), lower case
            self.effects = {n.lower(): i for i, n in enumerate(self.sets)}

    def emitters(self, set_index):
        v = self.vfxb
        return [read_emitter(v, s) for s in self.set_sections[set_index].children(v)]

    def textures(self):
        """{texture id: name} from GRTF's GTNT table, and the BNTX bytes"""
        v = self.vfxb
        g = self.top['GRTF']
        bntx = v[g.o + g.data:g.o + g.data + g.size]
        names = {}
        for a in [g] + g.children(v) + g.attrs(v):
            if a.magic == 'GTNT':
                o, end = a.o + a.data, a.o + a.size
                while o + 16 <= end:
                    tid, nxt, ln = struct.unpack_from('<QII', v, o)
                    name = v[o + 16:o + 16 + ln].split(b'\0')[0].decode('latin1')
                    names[tid] = name
                    if not nxt:
                        break
                    o += nxt
        return names, bntx

    def primitives(self):
        """{primitive id: model} from G3PR: its descriptor table (G3NT: 0x18 bytes each: u64 id, u32 next,
        u32, then the attribute slots) gives the model by order; the models are a BFRES
        (tools/bfres_switch.py)"""
        import bfres_switch
        v = self.vfxb
        g = self.top['G3PR']
        res = bfres_switch.Bfres(v[g.o + g.data:g.o + g.data + g.size])
        d = Section(v, g.o + g.child)
        out, o, end, i = {}, d.o + d.data, d.o + d.data + d.size, 0
        while o + 0x18 <= end and i < len(res.models):
            pid, nxt = struct.unpack_from('<QI', v, o)
            out[pid] = res.models[i]
            i += 1
            if not nxt:
                break
            o += nxt
        return out

    def images(self):
        """{texture id: RGBA uint8} with each texture's BNTX channel selection applied (BRTI +0x58: per
        output channel 0 zero, 1 one, 2-5 R G B A: the BC5 ones are (R, R, R, G), luminance + alpha;
        the BC4 ones (R, R, R, R)). A format tools/bntx.py can't decode leaves its texture out (ef_common.eff
        has a few, kind 7)"""
        import numpy as np
        import bntx
        names, b = self.textures()
        d = b[b.index(b'BNTX'):]
        by_name = {}
        i = d.find(b'BRTI')
        while i >= 0:
            name_ptr, = struct.unpack('<Q', d[i + 0x60:i + 0x68])
            n, = struct.unpack('<H', d[name_ptr:name_ptr + 2])
            try:
                img = bntx._brti(d, i)
            except KeyError:
                i = d.find(b'BRTI', i + 4)
                continue
            src = [np.zeros_like(img[..., 0]), np.full_like(img[..., 0], 255)] + [img[..., c] for c in range(4)]
            by_name[d[name_ptr + 2:name_ptr + 2 + n].decode()] = np.stack([src[s] for s in d[i + 0x58:i + 0x5C]], 2)
            i = d.find(b'BRTI', i + 4)
        return {tid: by_name[name] for tid, name in names.items() if name in by_name}


def main():
    a = sys.argv[1:]
    eff = Eff(a[1])
    if a[0] == 'info':
        print('%d effects, %d emitter sets' % (len(eff.effects), len(eff.sets)))
        for name, i in eff.effects.items():
            ems = eff.emitters(i)
            print('%-34s set %3d %-28s %s' % (name, i, eff.sets[i], [e['name'] for e in ems]))
    elif a[0] == 'dump':
        want = set(a[3:])
        out = {eff.sets[i]: eff.emitters(i) for i in range(len(eff.sets)) if not want or eff.sets[i] in want}
        json.dump(out, open(a[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
