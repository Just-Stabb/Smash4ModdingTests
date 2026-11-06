#!/usr/bin/env python3
"""Smash 3DS models and animations: .mbn (meshes) + .bch (H3D: skeleton, materials, textures, skeletal and
material animations), read into plain Python / numpy.

Layouts (worked out on the Smash Run Goomba, `enemy/kuribo/`, with Ohana3DS-Rebirth's BCH.cs (gdkchan, GPL-3,
read only for the layout) and Smash Forge's MBN.cs as references):

H3D (.bch, little-endian), backward-compatibility byte 0x21 (Smash 3DS):
  "BCH\\0", u8 backward 0x21, u8 forward, u16 version, then the offsets of the main header, string table, GPU
  commands, data, extended data, relocation table, then their lengths, two uninitialised-section lengths,
  u16 flags, u16 address count.
  Every pointer in the file is relative to its section; the relocation table (u32: offset bits 0-24, kind bits
  25-31) says which: kind 0 -> main-header word (at main + 4 * offset) += main; 1 -> (main + offset) += strings;
  2 -> += GPU commands; 7 / 0xC -> += data; and GPU-command words (at gpu + 4 * offset): 0x25 texture += data,
  0x26 vertices += data, 0x27 / 0x28 indices (16 / 8 bit) += data, 0x2B-0x2D the same from extended data.
  Main header: 15 sections (models, materials, shaders, textures, LUTs, lights, cameras, fogs, skeletal, material,
  visibility, light, camera, fog animations, scenes), each {pointer table, count, name tree}.
  Model: u8 flags, u8 skeleton scaling, u16 silhouette materials, 3x4 world matrix, materials {table, count,
  names}, objects {table, count}, 0x28 bytes, skeleton {table, count, names}, node visibility pointer, node count,
  name, object-name count, object-name tree (PATRICIA: a root then per name {s32 bit, u16 left, u16 right,
  name}), 0, metadata.
  Material (0x2C each): parameters pointer, 3 words, texture commands {pointer, words}, mapper pointer, the
  textures' names (unit 0-2), the material's name.
  Object (0x38 each): u16 material, u16 flags (1: silhouette), u16 object-name index, u16 render priority,
  vertex-buffer commands, faces {pointer, count}, extra buffers, centre, flags pointer, 0, bounding box.
  Bone (100 bytes): u32 flags (billboard bits 16-19, segment scale compensate 0x400000), s16 parent, u16, scale,
  rotation (Euler radians, R = Rz Ry Rx), translation, the inverse bind matrix (3x4, rows), name, metadata.
  Texture: unit 0-2 commands {pointer, words}, u32, name. Its commands (PICA200 registers): 0x82 size (width
  << 16 | height), 0x85 address, 0x8E format.
  Skeletal animation: name, u32 flags (bit 0 loop), f32 frame count, bone table {pointer, count}, metadata.
  Its bones: name, u32 type flags (segment type bits 16-19: 4 transform, 7 quaternion, 9 baked matrices), u32
  flags, then per type (see skeletal_animations()).
  Key frame group: f32 start, end, u32 repeat flags, u32 segment flags (interpolation bits 0-3: 0 step, 1 linear,
  2 hermite; quantization bits 8-15; key count bits 16-31), f32 value scale, value offset, frame scale, 1 / end
  frame, keys pointer.

MBN (Smash 3DS meshes, little-endian), formats 4, 5 and 6 (see read_mbn for where 5 / 6 keep the data):
  u16 format, u16 0xFFFF, u32 flags (2: name table), u32 mode, u32 mesh count; per mesh: u32 part count, per part
  {u32 bone count, u32 bones (the model's skeleton indices), u32 index count, u16 indices (triangle list), padded
  to 4}; then its vertex description {u32 attribute count, per attribute {u32 kind (0 position, 1 normal, 2
  colour, 3 / 4 UV 0 / 1, 5 bone index, 6 bone weight), u32 type (0 f32, 1 u8, 2 s8, 3 s16), f32 scale}, u32
  buffer size} and its vertex buffer (each attribute aligned to 2; positions / normals 3 values, colours 4, UVs
  2, bone indices / weights 2; bone indices index the part's bone list). The meshes are the .bch model's objects,
  in order (a silhouette object's mesh is the outline the 3DS draws behind).
"""
import struct
import sys

import numpy as np


# ---------------------------------------------------------------- MBN
def _vertices(buf, desc):
    """a vertex buffer + its description -> ({kind: [n, k] floats}, n)"""
    widths = {0: 3, 1: 3, 2: 4, 3: 2, 4: 2, 5: 2, 6: 2}
    tsize = {0: 4, 1: 1, 2: 1, 3: 2}
    tcode = {0: '<f4', 1: 'u1', 2: 'i1', 3: '<i2'}
    layout, stride = [], 0
    for kind, typ, scale in desc:
        stride += stride % 2
        layout.append((kind, typ, scale, stride))
        stride += widths[kind] * tsize[typ]
    stride += stride % 2
    count = len(buf) // stride
    assert count * stride == len(buf), (len(buf), stride)
    raw = np.frombuffer(buf, np.uint8).reshape(count, stride)
    attrs = {}
    for kind, typ, scale, off in layout:
        w = widths[kind] * tsize[typ]
        col = np.ascontiguousarray(raw[:, off:off + w]).view(tcode[typ]).reshape(count, widths[kind])
        attrs[kind] = col.astype(np.float64) * scale
    return attrs, count


def read_mbn(d):
    """-> [mesh dict(parts=[(bones, indices array)], attrs={kind: [n, k] float array}, count=n)]

    Format 4: each mesh's headers, inline u16 indices (padded to 4), its description and vertex buffer (padded
    to 4). Formats 5 / 6: every mesh's headers and description first (index counts only), then from a 32-byte
    boundary each mesh's vertex buffer and its parts' u16 indices, each block from a 32-byte boundary
    (padding 0xFF)."""
    fmt, _u, flags, mode, nmesh = struct.unpack_from('<HHIII', d, 0)
    assert fmt in (4, 5, 6) and mode == 0, (fmt, mode)
    o = 0x10

    def u32():
        nonlocal o
        v = struct.unpack_from('<I', d, o)[0]
        o += 4
        return v
    heads = []
    for _m in range(nmesh):
        parts = []
        for _p in range(u32()):
            bones = [u32() for _ in range(u32())]
            n = u32()
            if flags & 2:
                u32()
            idx = None
            if fmt == 4:
                idx = np.frombuffer(d, '<u2', n, o).astype(np.int64)
                o += 2 * n
                o += -o % 4
            parts.append([bones, idx, n])
        nd = u32()
        desc = [struct.unpack_from('<IIf', d, o + 12 * k) for k in range(nd)]
        o += 12 * nd
        size = u32()
        buf = None
        if fmt == 4:
            buf, o = d[o:o + size], o + size
            o = min(o + (-o % 4), len(d))                  # the next mesh starts on 4 (the file may end unpadded)
        heads.append([parts, desc, size, buf])
    if fmt != 4:
        for h in heads:
            o += -o % 32
            h[3], o = d[o:o + h[2]], o + h[2]
            for part in h[0]:
                o += -o % 32
                part[1] = np.frombuffer(d, '<u2', part[2], o).astype(np.int64)
                o += 2 * part[2]
        o = min(o + (-o % 32), len(d))
    assert o == len(d), (o, len(d))
    meshes = []
    for parts, desc, _size, buf in heads:
        attrs, count = _vertices(buf, desc)
        for _b, idx, _n in parts:
            assert idx.max() < count, (idx.max(), count)
        meshes.append(dict(parts=[(b, i) for b, i, _n in parts], attrs=attrs, count=count, desc=desc))
    return meshes


def match_objects(objects, mbn):
    """the .mbn mesh of each .bch object. The .mbn keeps the meshes in the order the exporter wrote the objects'
    data (their part records' addresses), not the object table's: the Goomba's are the same, Dekakuribo's
    objects come 0 1 3 2 4, Pokkuri's 1 0, Shandera's 0 1 4 2 3. Checked on every enemy: each object's part
    bone lists (kept in the .bch) equal its mesh's."""
    order = sorted(range(len(objects)), key=lambda k: objects[k]['data'])
    rank = {k: r for r, k in enumerate(order)}
    out = [rank[k] for k in range(len(objects))]
    for o, i in zip(objects, out):
        assert [tuple(b) for b, _ in mbn[i]['parts']] == [tuple(f) for f in o['faces']], o['name']
    return out


# ---------------------------------------------------------------- textures (PICA200)
TILE = [0, 1, 8, 9, 2, 3, 10, 11, 16, 17, 24, 25, 18, 19, 26, 27, 4, 5, 12, 13, 6, 7, 14, 15, 20, 21, 28, 29,
        22, 23, 30, 31, 32, 33, 40, 41, 34, 35, 42, 43, 48, 49, 56, 57, 50, 51, 58, 59, 36, 37, 44, 45, 38, 39,
        46, 47, 52, 53, 60, 61, 54, 55, 62, 63]
FORMATS = ['rgba8', 'rgb8', 'rgba5551', 'rgb565', 'rgba4', 'la8', 'hilo8', 'l8', 'a8', 'la4', 'l4', 'a4',
           'etc1', 'etc1a4']
BPP = [32, 24, 16, 16, 16, 16, 16, 8, 8, 8, 4, 4, 4, 8]
ETC1 = [(2, 8), (5, 17), (9, 29), (13, 42), (18, 60), (24, 80), (33, 106), (47, 183)]


def tex_size(w, h, fmt):
    return w * h * BPP[fmt] // 8


def _etc1_block(v):
    """64-bit ETC1 block -> [4, 4, 3] (y, x)"""
    hi = v >> 32
    diff, flip = (hi >> 1) & 1, hi & 1
    t1, t2 = (hi >> 5) & 7, (hi >> 2) & 7
    if diff:
        def d3(x):
            return x - 8 if x & 4 else x
        r1, g1, b1 = (hi >> 27) & 31, (hi >> 19) & 31, (hi >> 11) & 31
        r2, g2, b2 = r1 + d3((hi >> 24) & 7), g1 + d3((hi >> 16) & 7), b1 + d3((hi >> 8) & 7)
        c1 = [(c << 3) | (c >> 2) for c in (r1, g1, b1)]
        c2 = [(c << 3) | (c >> 2) for c in (r2 & 31, g2 & 31, b2 & 31)]
    else:
        c1 = [((hi >> s) & 15) * 17 for s in (28, 20, 12)]
        c2 = [((hi >> s) & 15) * 17 for s in (24, 16, 8)]
    out = np.zeros((4, 4, 3), np.int32)
    for x in range(4):
        for y in range(4):
            i = x * 4 + y
            msb, lsb = (v >> (16 + i)) & 1, (v >> i) & 1
            second = (y >= 2) if flip else (x >= 2)
            base, table = (c2, t2) if second else (c1, t1)
            m = ETC1[table][lsb]
            if msb:
                m = -m
            out[y, x] = [min(255, max(0, c + m)) for c in base]
    return out


def decode_texture(data, w, h, fmt):
    """PICA200 texture -> RGBA uint8 [h, w, 4] in memory order (the first row first). The 3DS's V counts up from
    the bottom: a UV (u, v) samples row (1 - v) * h of this image, as in Ohana3DS (it flips the bitmap for
    Direct3D and uses V as is) and Smash Forge (V -> 1 - V on the unflipped image)"""
    img = np.zeros((h, w, 4), np.uint8)
    name = FORMATS[fmt]
    if name in ('etc1', 'etc1a4'):
        o = 0
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for by, bx in ((0, 0), (0, 4), (4, 0), (4, 4)):
                    if name == 'etc1a4':
                        a = struct.unpack_from('<Q', data, o)[0]
                        o += 8
                    else:
                        a = None
                    v = struct.unpack_from('<Q', data, o)[0]
                    o += 8
                    blk = _etc1_block(v)
                    img[ty + by:ty + by + 4, tx + bx:tx + bx + 4, :3] = blk
                    if a is None:
                        img[ty + by:ty + by + 4, tx + bx:tx + bx + 4, 3] = 255
                    else:
                        for x in range(4):
                            for y in range(4):
                                img[ty + by + y, tx + bx + x, 3] = ((a >> (4 * (x * 4 + y))) & 15) * 17
        return img
    bpp = BPP[fmt]
    o = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for p in range(64):
                x, y = TILE[p] % 8, TILE[p] // 8
                if bpp == 4:
                    b = data[o + p // 2]
                    v = (b >> 4) if p & 1 else (b & 15)
                    if name == 'l4':
                        img[ty + y, tx + x] = (v * 17, v * 17, v * 17, 255)
                    else:
                        img[ty + y, tx + x] = (255, 255, 255, v * 17)
                    continue
                n = bpp // 8
                px = data[o + p * n:o + p * n + n]
                if name == 'rgba8':
                    c = (px[3], px[2], px[1], px[0])
                elif name == 'rgb8':
                    c = (px[2], px[1], px[0], 255)
                elif name in ('rgba5551', 'rgb565', 'rgba4', 'la8', 'hilo8'):
                    u = px[0] | px[1] << 8
                    if name == 'rgba5551':
                        c = tuple(((u >> s) & 31) * 255 // 31 for s in (11, 6, 1)) + ((u & 1) * 255,)
                    elif name == 'rgb565':
                        c = ((u >> 11) * 255 // 31, ((u >> 5) & 63) * 255 // 63, (u & 31) * 255 // 31, 255)
                    elif name == 'rgba4':
                        c = tuple(((u >> s) & 15) * 17 for s in (12, 8, 4, 0))
                    elif name == 'la8':
                        c = (px[1], px[1], px[1], px[0])
                    else:
                        c = (px[1], px[0], 0, 255)
                elif name == 'l8':
                    c = (px[0], px[0], px[0], 255)
                elif name == 'a8':
                    c = (255, 255, 255, px[0])
                else:                                   # la4
                    c = ((px[0] >> 4) * 17,) * 3 + ((px[0] & 15) * 17,)
                img[ty + y, tx + x] = c
            o += 64 * bpp // 8
    return img


# ---------------------------------------------------------------- H3D
SECTIONS = ['models', 'materials', 'shaders', 'textures', 'luts', 'lights', 'cameras', 'fogs', 'skeletal',
            'material_anims', 'visibility', 'light_anims', 'camera_anims', 'fog_anims', 'scenes']


def _pica(d, off, words):
    """PICA200 command buffer -> {register: last value}"""
    regs = {}
    read = 0
    p = off
    while read < words:
        param, hdr = struct.unpack_from('<II', d, p)
        p += 8
        read += 2
        rid = hdr & 0xFFFF
        extra = (hdr >> 20) & 0x7FF
        regs[rid] = param
        for _ in range(extra):
            if hdr & 0x80000000:
                rid += 1
            regs[rid] = struct.unpack_from('<I', d, p)[0]
            p += 4
            read += 1
        while p & 7:
            p += 4
    return regs


class Bch:
    def __init__(self, data):
        d = bytearray(data)
        assert d[:4] == b'BCH\0'
        self.back = d[4]
        assert self.back == 0x21, hex(self.back)
        (self.main, self.strings, self.gpu, self.data_off, self.ext, self.reloc,
         self.main_len, self.str_len, self.gpu_len, self.data_len, self.ext_len, self.reloc_len) = \
            struct.unpack_from('<12I', d, 8)
        for o in range(self.reloc, self.reloc + self.reloc_len, 4):
            v = struct.unpack_from('<I', d, o)[0]
            off, kind = v & 0x1FFFFFF, v >> 25
            add = {0: self.main, 1: self.strings, 2: self.gpu, 7: self.data_off, 0xC: self.data_off}.get(kind)
            if add is not None:
                at = self.main + (off if kind == 1 else off * 4)
                struct.pack_into('<I', d, at, struct.unpack_from('<I', d, at)[0] + add)
            gadd = {0x25: self.data_off, 0x26: self.data_off, 0x27: self.data_off, 0x28: self.data_off,
                    0x2B: self.ext, 0x2C: self.ext, 0x2D: self.ext}.get(kind)
            if gadd is not None:
                at = self.gpu + off * 4
                struct.pack_into('<I', d, at, struct.unpack_from('<I', d, at)[0] + gadd)
        self.d = bytes(d)
        self.sections = {}
        for k, name in enumerate(SECTIONS):
            self.sections[name] = struct.unpack_from('<3I', self.d, self.main + 12 * k)

    def u32(self, o):
        return struct.unpack_from('<I', self.d, o)[0]

    def f32s(self, o, n):
        return struct.unpack_from('<%df' % n, self.d, o)

    def cstr(self, o):
        if not o:
            return None
        return self.d[o:self.d.index(b'\0', o)].decode('ascii', 'replace')

    def entries(self, section):
        table, count, _names = self.sections[section]
        return [self.u32(table + 4 * k) for k in range(count)]

    # ---- textures
    def textures(self):
        """-> {name: RGBA [h, w, 4]}"""
        out = {}
        for p in self.entries('textures'):
            c0, w0 = self.u32(p), self.u32(p + 4)
            name = self.cstr(self.u32(p + 0x1C))
            regs = _pica(self.d, c0, w0)
            size, addr, fmt = regs[0x82], regs[0x85], regs[0x8E]
            w, h = size >> 16, size & 0xFFFF
            out[name] = decode_texture(self.d[addr:addr + tex_size(w, h, fmt)], w, h, fmt)
            out[name + '#format'] = FORMATS[fmt]
        return out

    # ---- models
    def models(self):
        return [self._model(p) for p in self.entries('models')]

    def _model(self, p):
        d = self.d
        m = {'flags': d[p], 'world': np.array(self.f32s(p + 4, 12)).reshape(3, 4)}
        mat_t, mat_n, _mat_names, obj_t, obj_n = struct.unpack_from('<5I', d, p + 0x34)
        q = p + 0x34 + 20 + 0x28
        skel_t, skel_n, _skel_names, vis_p, _node_n, name_p, oname_n, oname_t, _z, _meta = \
            struct.unpack_from('<10I', d, q)
        m['name'] = self.cstr(name_p)
        names = []
        for k in range(oname_n):
            names.append(self.cstr(self.u32(oname_t + 12 + 12 * k + 8)))
        m['object_names'] = names
        m['visibility'] = self.u32(vis_p) if vis_p else 0xFFFFFFFF
        mats = []
        for k in range(mat_n):
            e = mat_t + 0x2C * k
            params, _a, _b, _c, tcmd, twords, mapper = struct.unpack_from('<7I', d, e)
            tex = [self.cstr(self.u32(e + 0x1C + 4 * j)) for j in range(3)]
            mat = {'name': self.cstr(self.u32(e + 0x28)), 'textures': tex, 'params': params, 'mapper': mapper}
            if params:
                mat['flags'], mat['fragment_flags'] = struct.unpack_from('<HH', d, params + 4)
                coords = []
                for j in range(3):
                    pc = params + 0xC + 0x18 * j
                    pr = self.u32(pc)
                    coords.append(dict(projection=(pr >> 16) & 0xFF, camera=pr >> 24,
                                       scale=self.f32s(pc + 4, 2), rotate=self.f32s(pc + 12, 1)[0],
                                       translate=self.f32s(pc + 16, 2)))
                mat['coords'] = coords
                cp = params + 0xC + 0x18 * 3 + 4
                cols = [tuple(d[cp + 4 * j:cp + 4 * j + 4]) for j in range(12)]
                # the fragment-operation commands (PICA200 registers): 0x101 blend (equation bits 0-15, RGB
                # source / destination functions bits 16-19 / 20-23: 0 zero, 1 one, 6 source alpha, 7 one minus
                # source alpha), 0x104 alpha test (bit 0 on, function bits 4-7: 6 greater, 7 greater or equal,
                # reference bits 8-15), 0x107 depth (bit 12: write), 0x108 culling (0 none, 1 front, 2 back);
                # the material's blend mode (fragment flags bits 10-11): 3 blended
                fsh, fwords = struct.unpack_from('<II', d, params + 0xC8)
                regs = _pica(d, fsh, fwords) if fsh and fwords else {}
                b, at = regs.get(0x101, 0), regs.get(0x104, 0)
                mat['blend'] = dict(on=((mat['fragment_flags'] >> 10) & 3) == 3, src=(b >> 16) & 0xF, dst=(b >> 20) & 0xF)
                mat['alpha_test'] = dict(on=bool(at & 1), func=(at >> 4) & 0xF, ref=(at >> 8) & 0xFF)
                mat['cull'] = regs.get(0x108, 2) & 0xF
                mat['depth_write'] = bool(regs.get(0x107, 0x1000) & 0x1000)
                mat['colors'] = dict(zip(['emission', 'ambient', 'diffuse', 'specular0', 'specular1',
                                          'constant0', 'constant1', 'constant2', 'constant3', 'constant4',
                                          'constant5', 'blend'], cols))
            if mapper:
                # per unit: u32 (wrap U bits 8-15, wrap V bits 16-23: 0 clamp, 1 border, 2 repeat, 3 mirror;
                # mag filter bits 24-31), u32 (min filter, min LOD), f32 LOD bias, border colour
                mat['wrap'] = []
                for j in range(3):
                    w = self.u32(mapper + 0x10 * j)
                    mat['wrap'].append(((w >> 8) & 0xFF, (w >> 16) & 0xFF))
            mats.append(mat)
        m['materials'] = mats
        objs = []
        for k in range(obj_n):
            e = obj_t + 0x38 * k
            mid, fl, node, prio = struct.unpack_from('<4H', d, e)
            fo, fn = struct.unpack_from('<II', d, e + 0x10)
            faces = []
            for f in range(fn):                        # per part: u16 skinning, u16 bone count, the bones
                skin, nn = struct.unpack_from('<HH', d, fo + 0x34 * f)
                faces.append(struct.unpack_from('<%dH' % nn, d, fo + 0x34 * f + 4))
            objs.append(dict(material=mid, silhouette=bool(fl & 1), name=names[node] if node < len(names) else
                             'mesh%d' % k, node=node, priority=prio, center=self.f32s(e + 0x20, 3), faces=faces,
                             data=fo))
        m['objects'] = objs
        bones = []
        for k in range(skel_n):
            e = skel_t + 100 * k
            fl, parent = struct.unpack_from('<Ih', d, e)
            vals = self.f32s(e + 8, 9 + 12)
            bones.append(dict(flags=fl, parent=parent, scale=vals[0:3], rot=vals[3:6], pos=vals[6:9],
                              inv=np.array(vals[9:21]).reshape(3, 4), name=self.cstr(self.u32(e + 0x5C))))
        m['bones'] = bones
        return m

    # ---- skeletal animations
    def keyframes(self, o):
        """key frame group at o -> dict(start, end, interp, keys=[(frame, value, in slope, out slope)])"""
        d = self.d
        start, end, rep, seg = struct.unpack_from('<ffII', d, o)
        vs, vo, fs, fo = self.f32s(o + 16, 4)
        kp = self.u32(o + 32)
        interp, quant, n = seg & 0xF, (seg >> 8) & 0xFF, seg >> 16
        keys = []
        p = kp
        for _ in range(n):
            if quant == 0:
                f, v, i, s = struct.unpack_from('<4f', d, p)
                p += 16
            elif quant == 1:
                w, i, s = struct.unpack_from('<Ihh', d, p)
                p += 8
                f, v, i, s = w & 0xFFF, w >> 12, i / 256, s / 256
            elif quant == 2:
                f, v = d[p], struct.unpack_from('<H', d, p + 1)[0]
                s0, s1, s2 = d[p + 3], d[p + 4], d[p + 5]
                p += 6
                i, s = s0 | (s1 & 15) << 8, s1 >> 4 | s2 << 4
                i, s = (i - 0x1000 if i & 0x800 else i) / 32, (s - 0x1000 if s & 0x800 else s) / 32
            elif quant == 3:
                f, v, i = struct.unpack_from('<3f', d, p)
                s = i
                p += 12
            elif quant == 4:
                f, v, i = struct.unpack_from('<HHh', d, p)
                f, i = f / 32, i / 256
                s = i
                p += 6
            elif quant == 5:
                f = d[p]
                w = struct.unpack_from('<H', d, p + 1)[0]
                v = w & 0xFFF
                i = (w >> 12) | d[p + 3] << 4
                i = (i - 0x1000 if i & 0x800 else i) / 32
                s = i
                p += 4
            elif quant == 6:
                f, v = struct.unpack_from('<2f', d, p)
                i = s = 0
                p += 8
            elif quant == 7:
                w = self.u32(p)
                f, v = w & 0xFFF, w >> 12
                i = s = 0
                p += 4
            else:
                raise ValueError('quantization %d' % quant)
            # the slopes are in value units per frame of the stored (scaled) data. The fourth float (Ohana's
            # frame offset) is 1 / the group's end frame in every one of the Goomba's 576 groups: not an
            # offset (its keys sit on whole frames 0..end without it), so it is left out
            keys.append((f * fs, v * vs + vo, i * vs, s * vs))
        return dict(start=start, end=end, interp=interp, quant=quant, keys=keys, pre=rep & 15, post=(rep >> 8) & 15)

    def skeletal_animations(self):
        out = []
        for p in self.entries('skeletal'):
            name = self.cstr(self.u32(p))
            flags, frames = struct.unpack_from('<If', self.d, p + 4)
            bt, bn = self.u32(p + 12), self.u32(p + 16)
            bones = []
            for k in range(bn):
                bones.append(self._anim_bone(self.u32(bt + 4 * k)))
            out.append(dict(name=name, loop=bool(flags & 1), frames=frames, bones=bones))
        return out

    def _anim_bone(self, o):
        d = self.d
        name = self.cstr(self.u32(o))
        tflags, flags = struct.unpack_from('<II', d, o + 4)
        seg = (tflags >> 16) & 0xF
        b = dict(name=name, type=seg, flags=flags)
        if seg == 4:
            # scale x y z, rotation x y z, translation x y z: each a constant float or a key group pointer.
            # flags: 'absent' bits 16-24 (scale x y z, rotation x y z, translation x y z), 'constant' bits 6-11
            # (scale, rotation) and 13-15 (translation); the 9 slots are there either way
            tracks = {}
            p = o + 0xC
            for vi, kind in enumerate(('scale', 'rot', 'pos')):
                for axis in range(3):
                    absent = flags & (0x10000 << (3 * vi + axis))
                    const = flags & (1 << (6 + 3 * vi + axis + (vi == 2)))
                    if not absent:
                        if const:
                            tracks[(kind, axis)] = dict(const=self.f32s(p, 1)[0])
                        else:
                            tracks[(kind, axis)] = self.keyframes(self.u32(p))
                    p += 4
            b['tracks'] = tracks
        elif seg == 7:
            so, ro, to = struct.unpack_from('<3I', d, o + 0xC)
            for kind, off, absent, const, n in (('scale', so, 0x20, 4, 3), ('quat', ro, 0x10, 2, 4),
                                               ('pos', to, 8, 1, 3)):
                if flags & absent:
                    continue
                if flags & const:
                    b[kind] = dict(start=0, values=[self.f32s(off, n)])
                else:
                    start, end, _f, dp, cnt = struct.unpack_from('<ffIII', d, off)
                    b[kind] = dict(start=start, end=end, values=[self.f32s(dp + 4 * n * j, n) for j in range(cnt)])
        elif seg == 9:
            mp, cnt = struct.unpack_from('<II', d, o + 0x14)
            b['matrices'] = [np.array(self.f32s(mp + 48 * j, 12)).reshape(3, 4) for j in range(cnt)]
        else:
            raise ValueError('segment type %d on %s' % (seg, name))
        return b

    # ---- material animations
    def material_animations(self):
        """name, u32 flags (bit 0 loop), f32 frames, data {table, count}, u32, texture names {table, count}; a
        data entry: name (the material), u32 type flags (property bits 0-7, segment bits 16-19: 5 RGBA, 2
        vector2, 0 float, 6 int), u32 flags (component j: absent 0x100 << j, constant 1 << j), then a constant or
        key pointer a component"""
        out = []
        for p in self.entries('material_anims'):
            name = self.cstr(self.u32(p))
            flags, frames, dt, dn, _z, tt, tn = struct.unpack_from('<IfIIIII', self.d, p + 4)
            mats = []
            for k in range(dn):
                o = self.u32(dt + 4 * k)
                tflags, fl = struct.unpack_from('<II', self.d, o + 4)
                seg = (tflags >> 16) & 0xF
                comps = []
                for j in range({5: 4, 2: 2, 0: 1, 6: 1}.get(seg, 0)):
                    q = o + 0xC + 4 * j
                    if fl & (0x100 << j):
                        comps.append(None)
                    elif fl & (1 << j):
                        comps.append(dict(const=self.f32s(q, 1)[0]))
                    else:
                        comps.append(self.keyframes(self.u32(q)))
                mats.append(dict(name=self.cstr(self.u32(o)), property=tflags & 0xFF, segment=seg, components=comps))
            out.append(dict(name=name, loop=bool(flags & 1), frames=frames, materials=mats,
                            textures=[self.cstr(self.u32(tt + 4 * j)) for j in range(tn)]))
        return out

    # ---- visibility animations
    def visibility_animations(self):
        """name, u32 flags (bit 0 loop), f32 frames, data {table, count}, 2 words; a data entry: name (the object
        name), u32 type flags (segment 8: boolean), u32 flags, then u32 (bit 24: the default), u32, bits
        pointer, frame count: one bit a frame, low bit first"""
        out = []
        for p in self.entries('visibility'):
            name = self.cstr(self.u32(p))
            flags, frames, dt, dn = struct.unpack_from('<IfII', self.d, p + 4)
            tracks = {}
            for k in range(dn):
                o = self.u32(dt + 4 * k)
                tflags = self.u32(o + 4)
                assert (tflags >> 16) & 0xF == 8
                default = (self.u32(o + 0xC) >> 24) & 1
                bp, n = self.u32(o + 0x14), self.u32(o + 0x18)
                bits = [(self.d[bp + j // 8] >> (j % 8)) & 1 for j in range(n)]
                tracks[self.cstr(self.u32(o))] = dict(default=default, frames=bits)
            out.append(dict(name=name, loop=bool(flags & 1), frames=frames, tracks=tracks))
        return out


# ---------------------------------------------------------------- sampling
def hermite(p0, p1, s0, s1, t, dt):
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * s0 * dt + (-2 * t3 + 3 * t2) * p1
            + (t3 - t2) * s1 * dt)


def sample(group, frame):
    """value of a key frame group (or a {'const'} dict) at frame"""
    if group is None:
        return None
    if 'const' in group:
        return group['const']
    keys = group['keys']
    if not keys:
        return 0.0
    if frame <= keys[0][0]:
        return keys[0][1]
    if frame >= keys[-1][0]:
        return keys[-1][1]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= frame <= b[0]:
            dt = b[0] - a[0]
            if dt <= 0:
                return b[1]
            t = (frame - a[0]) / dt
            if group['interp'] == 0:
                return a[1]
            if group['interp'] == 1:
                return a[1] + (b[1] - a[1]) * t
            return hermite(a[1], b[1], a[3], b[2], t, dt)
    return keys[-1][1]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__.split('\n')[0] + '\nusage: s3ds_model.py info FILE.bch|FILE.mbn')
    path = sys.argv[2]
    d = open(path, 'rb').read()
    if d[:4] == b'BCH\0':
        b = Bch(d)
        for name, (t, n, _nm) in b.sections.items():
            if n:
                print('%-15s %d' % (name, n))
        for m in b.models():
            print('model', m['name'], 'bones', [(x['name'], x['parent']) for x in m['bones']])
            for o in m['objects']:
                print('  object', o)
            for mt in m['materials']:
                print('  material', mt['name'], mt['textures'])
        for a in b.skeletal_animations():
            print('anim %-30s frames %5.1f loop %d bones %d' % (a['name'], a['frames'], a['loop'], len(a['bones'])))
        for a in b.material_animations():
            print('mat anim %s frames %.1f %s' % (a['name'], a['frames'],
                                                 [(m['name'], m['segment'], m['property']) for m in a['materials']]))
        for a in b.visibility_animations():
            print('vis anim %s frames %.1f %s' % (a['name'], a['frames'],
                                                 {k: ''.join(map(str, v['frames'])) for k, v in a['tracks'].items()}))
    else:
        for k, m in enumerate(read_mbn(d)):
            print('mesh', k, 'vertices', m['count'], 'parts', [(b, len(i)) for b, i in m['parts']], m['desc'])


if __name__ == '__main__':
    main()
