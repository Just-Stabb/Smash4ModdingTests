#!/usr/bin/env python3
"""Wii BRRES-era models (MDL0 v8 - v11, as BrawlBox / BrawlLib read them) -> a Smash 4 model folder (model.nud /
model.nut / model.vbn / model.jtb / model.sb / model.nhb / model.xmb / model.flp).

  python3 tools/mdl0_to_nud.py MODEL.mdl0 TEX_DIR OUT_DIR [--scale S] [--face +z|+x|...] [--tex-id 0x...]
                              [--env-bake MATERIAL] [--info]
      TEX_DIR: the model's textures as PNG, named as its texture references (met_pata.png ...).
      --scale: positions and bone translations x S (the CHR0 converter takes the same --scale).
      --face AXIS: the model-space axis the model's head (its first child bone of the root, or --head BONE)
               points along in the MDL0; a TransN root is added that turns it to +Z (Smash 4 articles face +Z,
               the game turns them by their facing).
      --info:  print the parsed model (bones, arrays, objects, materials and their TEV stages), write nothing.
  python3 tools/mdl0_to_nud.py verify OUT_DIR       re-read the written files (nud / nut / vbn) and print counts

The file is untrusted input: it is only parsed (bounds checked), nothing in it is run.

MDL0 (BrawlLib MDL0Node and its section headers; big-endian):
- header "MDL0", size, version, bres offset, then the section offsets (v8 / v9: 11, v10 / v11: 14) of the resource
  groups: 0 definitions (NodeTree, DrawOpa / DrawXlu: material, object, bone, priority), 1 bones, 2 vertices,
  3 normals, 4 colours, 5 UVs, 6 / 7 fur (v10+), 8 materials, 9 shaders (TEV), 10 objects, 11 textures,
  12 palettes; the model name offset; the props (vertex / face counts, the node table).
- resource group: total size, count, (count + 1) 16-byte entries {id, flag, left, right, name offset, data offset}
  (offsets from the group), entry 0 the root.
- bone (0xD0): +0xC index, +0x10 node id, +0x14 flags, +0x20 scale, +0x2C rotation (degrees, X then Y then Z:
  R = Rz Ry Rx), +0x38 translation, +0x5C / +0x60 / +0x64 parent / first child / next (offsets from the bone),
  +0x70 its bind (world) matrix 3x4, +0xA0 the inverse.
- vertex / normal / UV / colour arrays: +8 data offset, +0x14 components (XY / XYZ, normal / NBT, S / ST, RGB /
  RGBA), +0x18 type (u8, s8, u16, s16, float; colours: RGB565, RGB8, RGBX8, RGBA4, RGBA6, RGBA8), +0x1C the
  fixed-point divisor (value / 2^divisor), +0x1D the stride, +0x1E the count.
- object (polygon): +8 its single-bind node (-1 weighted), +0xC / +0x10 the vertex descriptor (CP VCD lo / hi:
  which attributes, direct / 8-bit / 16-bit index), +0x18 / +0x24 two display-list headers {buffer size, size,
  offset from the header}: the attribute set-up and the primitives, +0x48 the array ids (position, normal, 2
  colours, 8 UVs), +0x64 the node table (its offset from the object: count, u16 nodes).
- primitives: GX display list: 0x20 / 0x28 / 0x30 indexed matrix loads (node, matrix address: a vertex's
  position matrix index = the load's address / 4), draws 0x80 quads, 0x90 triangles, 0x98 strips, 0xA0 fans (count,
  then each vertex's attributes in the VCD's order).
- material: +0x14 counts (texgens, light channels, TEV stages), +0x18 cull, +0x2C / +0x30 its texture references
  (0x34 each: name, map id, wrap S / T (0 clamp, 1 repeat, 2 mirror), filters), the texture SRTs and their mapping
  (0 UV, 1 EnvCamera, 2 projection, 3 EnvLight, 4 EnvSpec), +0x3C its display list (BP: alpha compare, blend /
  z mode, TEV colour registers; XF texgens: the source of each texture coordinate, UV or the normal).
- shader: its TEV stages (BP 0x28 orders: texture map, coordinate, colour channel; 0xC0 / 0xC1 colour / alpha
  combiners; 0xF6 - 0xFD konstant selections).

Smash 4 model (what is written):
- model.vbn: TransN (the root added here: the turn that makes the model face +Z), then the MDL0 bones in order
  (the bind pose from their SRTs, translations x scale; the converted bones' rotations as XYZ Euler radians),
  little-endian as the game's fighters'. model.jtb: one table, joint i = bone i.
- model.nud: one mesh per object, rigged (every vertex on its node: a single-bound object on its node, a weighted
  one through its PNMTXIDX: one bone each, weight 255; positions in the bind pose's world space), normals,
  tangents, white vertex colour, the UV set 0. Material: Smash 4's skinned fighter body shader (0x9A011063:
  colour, a flat normal map, the shared ramp) lit by the game, the source's wrap and culling.
- Lighting: the source's TEV is decoded (--info prints it). Wii models of this era light themselves with sphere
  maps addressed by the camera-space normal ("lm_01e" diffuse, "lm_02e" specular: EnvCamera texgens): the game's
  own lighting takes their place on the body shader. An environment-mapped material (--env-bake: a TEV stage that
  adds an EnvCamera texture x a register's alpha to a flat colour) is baked: its texture becomes colour + k x env,
  addressed by the sphere-map coordinates GX would generate for each vertex in the bind pose seen from the side
  camera with the model facing right (u = 0.5 + 0.5 nx, v = 0.5 - 0.5 ny of the camera-space normal: GX computes
  texgens per vertex and interpolates them, so this is the same picture for that pose and view; the highlight then
  moves with the model instead of staying on the camera, and is mirrored when it faces left).
- model.nut: the textures (GX2 BC1 / BC3, power-of-two), the flat normal map. model.sb / .nhb / .xmb from
  reference/enemy_model_defaults (tools/s3ds_enemy.py: without sb / nhb the bone-matrix getter crashes, without xmb
  models draw black); model.flp: an empty mirror table (FLIP 1.0, no entries).
"""
import argparse
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

GX_COMPONENT_BYTES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4}        # u8, s8, u16, s16, float
GX_COMPONENT_FMT = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'f'}
CI = ['CPREV', 'APREV', 'C0', 'A0', 'C1', 'A1', 'C2', 'A2', 'TEXC', 'TEXA', 'RASC', 'RASA', 'ONE', 'HALF', 'KONST',
      'ZERO']
AI = ['APREV', 'A0', 'A1', 'A2', 'TEXA', 'RASA', 'KONST', 'ZERO']
DST = ['PREV', 'R0', 'R1', 'R2']
MAP_MODES = {0: 'uv', 1: 'env_camera', 2: 'projection', 3: 'env_light', 4: 'env_spec'}


class Reader:
    """bounds-checked big-endian reads of an untrusted file"""

    def __init__(self, data):
        self.d = data

    def chk(self, o, n):
        if o < 0 or o + n > len(self.d):
            raise ValueError('MDL0: read of %d bytes at 0x%X past the file (0x%X)' % (n, o, len(self.d)))

    def u8(self, o):
        self.chk(o, 1)
        return self.d[o]

    def s8(self, o):
        return struct.unpack('>b', self.blob(o, 1))[0]

    def u16(self, o):
        return struct.unpack('>H', self.blob(o, 2))[0]

    def s16(self, o):
        return struct.unpack('>h', self.blob(o, 2))[0]

    def u32(self, o):
        return struct.unpack('>I', self.blob(o, 4))[0]

    def s32(self, o):
        return struct.unpack('>i', self.blob(o, 4))[0]

    def f32(self, o, n=1):
        v = struct.unpack('>%df' % n, self.blob(o, 4 * n))
        return v if n > 1 else v[0]

    def blob(self, o, n):
        self.chk(o, n)
        return self.d[o:o + n]

    def cstr(self, o):
        self.chk(o, 1)
        e = self.d.index(b'\0', o)
        if e - o > 256:
            raise ValueError('MDL0: name at 0x%X too long' % o)
        return self.d[o:e].decode('latin1')


def group(r, go):
    """a resource group -> [(name, data offset)]"""
    n = r.s32(go + 4)
    if not 0 <= n < 4096:
        raise ValueError('MDL0: group at 0x%X has %d entries' % (go, n))
    out = []
    for k in range(1, n + 1):
        e = go + 8 + 16 * k
        out.append((r.cstr(go + r.s32(e + 8)), go + r.s32(e + 12)))
    return out


def euler_xyz(deg):
    """BrawlLib's rotation (degrees about X, then Y, then Z): Rz Ry Rx"""
    x, y, z = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def srt(scale, rot_deg, trans):
    m = np.eye(4)
    m[:3, :3] = euler_xyz(rot_deg) @ np.diag(scale)
    m[:3, 3] = trans
    return m


def read_array(r, ho, kind):
    """a vertex / normal / UV / colour array -> numpy [count, components]"""
    do = ho + r.s32(ho + 8)
    if kind == 'col':
        rgba, fmt, stride, count = r.s32(ho + 0x14), r.s32(ho + 0x18), r.u8(ho + 0x1C), r.u16(ho + 0x1E)
        out = np.zeros((count, 4))
        for i in range(count):
            o = do + i * stride
            if fmt == 1 or fmt == 2:
                c = list(r.blob(o, 3)) + [255]
            elif fmt == 5:
                c = list(r.blob(o, 4))
            elif fmt == 0:
                v = r.u16(o)
                c = [((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255]
            elif fmt == 3:
                v = r.u16(o)
                c = [((v >> s) & 15) * 17 for s in (12, 8, 4, 0)]
            elif fmt == 4:
                v = int.from_bytes(r.blob(o, 3), 'big')
                c = [((v >> s) & 63) * 255 // 63 for s in (18, 12, 6, 0)]
            else:
                raise ValueError('MDL0: colour format %d' % fmt)
            out[i] = c
        return out
    comp, typ, div, stride, count = r.s32(ho + 0x14), r.s32(ho + 0x18), r.u8(ho + 0x1C), r.u8(ho + 0x1D), r.u16(ho + 0x1E)
    n = {'pos': (2, 3), 'nrm': (3, 9, 3), 'uv': (1, 2)}[kind][comp]
    if typ not in GX_COMPONENT_FMT:
        raise ValueError('MDL0: component type %d' % typ)
    cb = GX_COMPONENT_BYTES[typ]
    if n * cb > stride and stride:
        raise ValueError('MDL0: stride %d for %d x %d bytes' % (stride, n, cb))
    raw = r.blob(do, stride * (count - 1) + n * cb) if count else b''
    out = np.zeros((count, n))
    for i in range(count):
        out[i] = struct.unpack_from('>%d%s' % (n, GX_COMPONENT_FMT[typ]), raw, i * stride)
    if typ != 4:
        out /= float(1 << div)
    return out


def read_dl(r, o, n):
    return r.blob(o, n)


def parse_vcd(lo, hi):
    """the CP vertex descriptor -> [(attribute, mode)] in the display list's order (mode 1 direct, 2 / 3 an 8 / 16-bit
    index)"""
    out = []
    if lo & 1:
        out.append(('pnmtx', 1))
    for t in range(8):
        if lo >> (1 + t) & 1:
            out.append(('texmtx%d' % t, 1))
    for i, nm in enumerate(('pos', 'nrm', 'col0', 'col1')):
        m = (lo >> (9 + 2 * i)) & 3
        if m:
            out.append((nm, m))
    for t in range(8):
        m = (hi >> (2 * t)) & 3
        if m:
            out.append(('uv%d' % t, m))
    return out


def parse_primitives(r, dl, vcd):
    """GX primitives -> (triangles [[vertex dict] x 3], matrix loads seen) with each vertex's attribute values and the
    position matrix slot -> node map in effect at its draw"""
    tris = []
    slots = {}
    i = 0
    end = len(dl)
    loads = 0
    while i < end:
        c = dl[i]
        i += 1
        if c == 0x00:
            continue
        if c in (0x20, 0x28, 0x30, 0x38):
            if i + 4 > end:
                break
            node, word = struct.unpack_from('>HH', dl, i)
            i += 4
            if c == 0x20:
                slots[(word & 0xFFF) // 4] = node        # matrix memory address (words) / 4 = the PNMTXIDX value
                loads += 1
            continue
        if c == 0x08:
            i += 5
            continue
        if c == 0x10:
            nw = (struct.unpack_from('>H', dl, i)[0] & 0xF) + 1
            i += 4 + 4 * nw
            continue
        if c == 0x61:
            i += 4
            continue
        if c & 0x80:
            prim = c & 0xF8
            n = struct.unpack_from('>H', dl, i)[0]
            i += 2
            verts = []
            for _ in range(n):
                v = {}
                for att, mode in vcd:
                    if mode == 1:
                        if att.startswith(('pnmtx', 'texmtx')):
                            v[att] = dl[i]
                            i += 1
                        else:
                            raise ValueError('MDL0: direct %s data is not supported' % att)
                    elif mode == 2:
                        v[att] = dl[i]
                        i += 1
                    else:
                        v[att] = struct.unpack_from('>H', dl, i)[0]
                        i += 2
                v['node'] = slots.get(v.get('pnmtx', 0))
                verts.append(v)
            if prim == 0x90:
                tris += [verts[k:k + 3] for k in range(0, n - 2, 3)]
            elif prim == 0x98:
                for k in range(n - 2):
                    t = verts[k:k + 3]
                    tris.append(t if k % 2 == 0 else [t[1], t[0], t[2]])
            elif prim == 0xA0:
                tris += [[verts[0], verts[k], verts[k + 1]] for k in range(1, n - 1)]
            elif prim == 0x80:
                for k in range(0, n - 3, 4):
                    q = verts[k:k + 4]
                    tris += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
            continue
        raise ValueError('MDL0: display list command 0x%02X at %d' % (c, i - 1))
    return tris, loads


def bp_regs(r, o, n):
    """the BP register writes (0x61 reg value24) of a display list, the mask register (0xFE) applied"""
    regs = {}
    mask = 0xFFFFFF
    d = r.blob(o, n)
    i = 0
    while i + 5 <= len(d):
        if d[i] == 0x61:
            reg, v = d[i + 1], int.from_bytes(d[i + 2:i + 5], 'big')
            if reg == 0xFE:
                mask = v
            else:
                regs[reg] = (regs.get(reg, 0) & ~mask) | (v & mask)
                mask = 0xFFFFFF
            i += 5
        else:
            i += 1
    return regs


def xf_regs(r, o, n):
    """the XF register loads (0x10 count-1 addr words) of a display list"""
    regs = {}
    d = r.blob(o, n)
    i = 0
    while i + 5 <= len(d):
        if d[i] == 0x10:
            cnt = (struct.unpack_from('>H', d, i + 1)[0] & 0xF) + 1
            addr = struct.unpack_from('>H', d, i + 3)[0]
            for k in range(cnt):
                regs[addr + k] = struct.unpack_from('>I', d, i + 5 + 4 * k)[0]
            i += 5 + 4 * cnt
        else:
            i += 1
    return regs


def tev_stages(r, so, nstages):
    regs = bp_regs(r, so + 0x20, 0x1E0)
    out = []
    for s in range(nstages):
        o = regs.get(0x28 + s // 2, 0)
        if s & 1:
            o >>= 12
        c, a = regs.get(0xC0 + 2 * s, 0), regs.get(0xC1 + 2 * s, 0)
        k = regs.get(0xF6 + s // 2, 0)
        out.append(dict(
            tex_map=o & 7, tex_coord=(o >> 3) & 7, tex_on=(o >> 6) & 1, ras=(o >> 7) & 7,
            kcsel=(k >> (4 if s % 2 == 0 else 14)) & 0x1F, kasel=(k >> (9 if s % 2 == 0 else 19)) & 0x1F,
            c=dict(a=CI[(c >> 12) & 15], b=CI[(c >> 8) & 15], c=CI[(c >> 4) & 15], d=CI[c & 15], sub=(c >> 18) & 1,
                   bias=(c >> 16) & 3, scale=(c >> 20) & 3, clamp=(c >> 19) & 1, dest=DST[(c >> 22) & 3]),
            a=dict(a=AI[(a >> 13) & 7], b=AI[(a >> 10) & 7], c=AI[(a >> 7) & 7], d=AI[(a >> 4) & 7], sub=(a >> 18) & 1,
                   bias=(a >> 16) & 3, scale=(a >> 20) & 3, dest=DST[(a >> 22) & 3])))
    return out


def tev_text(st):
    def f(x):
        s = '%s %s (%s x (1 - %s) + %s x %s)' % (x['d'], '-' if x['sub'] else '+', x['a'], x['c'], x['b'], x['c'])
        return s + (' bias %d' % x['bias'] if x['bias'] else '') + (' scale %d' % x['scale'] if x['scale'] else '')
    return 'tex map %d coord %d, ras %d, konst c %X a %X | %s = %s | %s = %s' % (
        st['tex_map'], st['tex_coord'], st['ras'], st['kcsel'], st['kasel'], st['c']['dest'], f(st['c']),
        st['a']['dest'], f(st['a']))


def parse(path):
    """-> the model: {'name', 'version', 'bones', 'arrays', 'objects', 'materials', 'draw'}"""
    data = open(path, 'rb').read()
    r = Reader(data)
    if r.blob(0, 4) != b'MDL0':
        raise ValueError('%s: not an MDL0' % path)
    ver = r.u32(8)
    if ver not in (8, 9, 10, 11):
        raise ValueError('MDL0 version %d' % ver)
    nsec = 14 if ver >= 10 else 11
    secs = [r.u32(0x10 + 4 * i) for i in range(nsec)]
    names = (['defs', 'bones', 'pos', 'nrm', 'col', 'uv', 'furvec', 'furpos', 'mats', 'shaders', 'objs', 'texs',
              'pals', 'extra'] if ver >= 10 else
             ['defs', 'bones', 'pos', 'nrm', 'col', 'uv', 'mats', 'shaders', 'objs', 'texs', 'pals'])
    sec = {nm: (group(r, o) if o else []) for nm, o in zip(names, secs)}
    name_off = 0x10 + 4 * nsec
    model = dict(name=r.cstr(r.u32(name_off)), version=ver)
    # bones
    bones = []
    by_off = {}
    for nm, bo in sec['bones']:
        b = dict(name=nm, off=bo, index=r.s32(bo + 0xC), node=r.s32(bo + 0x10), flags=r.u32(bo + 0x14),
                 scale=r.f32(bo + 0x20, 3), rot=r.f32(bo + 0x2C, 3), pos=r.f32(bo + 0x38, 3),
                 parent_off=r.s32(bo + 0x5C), bind=np.array(r.f32(bo + 0x70, 12)).reshape(3, 4),
                 inv_bind=np.array(r.f32(bo + 0xA0, 12)).reshape(3, 4))
        by_off[bo] = b
        bones.append(b)
    bones.sort(key=lambda b: b['index'])
    for b in bones:
        p = b['off'] + b['parent_off'] if b['parent_off'] else None
        b['parent'] = bones.index(by_off[p]) if p in by_off else -1
    for i, b in enumerate(bones):
        local = srt(b['scale'], b['rot'], b['pos'])
        b['local'] = local
        b['world'] = local if b['parent'] < 0 else bones[b['parent']]['world'] @ local
        assert b['parent'] < i, 'MDL0: bones out of order'
    model['bones'] = bones
    node_of = {b['node']: i for i, b in enumerate(bones)}
    # arrays
    arrays = {}
    for kind in ('pos', 'nrm', 'uv', 'col'):
        arrays[kind] = [(nm, read_array(r, ho, kind)) for nm, ho in sec[kind]]
        for k, (nm, ho) in enumerate(sec[kind]):
            idx = r.s32(ho + 0x10)
            if idx != k:
                arrays[kind].sort(key=lambda e: 0)        # (kept in group order: the ids below are array indices)
    model['arrays'] = arrays
    # textures / materials / shaders
    shaders = {}
    for nm, so in sec['shaders']:
        shaders[so] = dict(stages=r.u8(so + 0xC), off=so)
    mats = []
    for nm, mo in sec['mats']:
        ntex = r.u32(mo + 0x2C)
        if ntex > 8:
            raise ValueError('MDL0: material %s has %d textures' % (nm, ntex))
        ro = mo + r.s32(mo + 0x30)
        texs = []
        for i in range(ntex):
            t = ro + 0x34 * i
            texs.append(dict(name=r.cstr(t + r.s32(t)), map_id=r.u32(t + 0x10), wrap_s=r.u32(t + 0x18),
                             wrap_t=r.u32(t + 0x1C), min_f=r.u32(t + 0x20), mag_f=r.u32(t + 0x24)))
        so = mo + r.s32(mo + 0x28)
        nst = shaders[so]['stages'] if so in shaders else r.u8(mo + 0x16)
        dl = mo + r.s32(mo + 0x3C)
        bp = bp_regs(r, dl, 0x180)
        xf = xf_regs(r, dl, 0x180)
        # TEV colour registers: BP 0xE0 + 2n (RA) / 0xE1 + 2n (BG), n 0 PREV, 1 - 3 C0 - C2 (bit 23 clear) or the
        # konstant colours (bit 23 set: written separately; both appear in the list, the last write of each kept)
        regs_c = {}
        d = r.blob(dl, 0x80)
        i = 0
        while i + 5 <= len(d):
            if d[i] == 0x61 and 0xE0 <= d[i + 1] <= 0xE7:
                v = int.from_bytes(d[i + 2:i + 5], 'big')
                key = ('k' if v >> 23 & 1 else 'c', (d[i + 1] - 0xE0) // 2, d[i + 1] & 1)
                regs_c[key] = v
                i += 5
            else:
                i += 1

        def reg_colour(kind, n):
            ra, bg = regs_c.get((kind, n, 0), 0), regs_c.get((kind, n, 1), 0)
            s11 = lambda v: (v & 0x7FF) - (0x800 if v & 0x400 else 0)  # noqa: E731
            return (s11(ra) / 255.0, s11(bg >> 12) / 255.0, s11(bg) / 255.0, s11(ra >> 12) / 255.0)
        # the texture mapping modes: the SRT effect entries (+0x1A8 + 0x34 x i in v11: s8 camera, s8 light, u8 map
        # mode, u8 identity), found as the 8 words 0xFFFF00xx / 0xFFFF01xx ... after the SRT table
        modes = []
        for k in range(0x40, 0x418, 4):
            w = r.u32(mo + k)
            if (w >> 16) == 0xFFFF and (w >> 8 & 0xFF) <= 4 and (w & 0xFF) <= 1:
                modes.append((w >> 8) & 0xFF)
        texgens = []
        for t in range(8):
            if 0x1040 + t in xf:
                v = xf[0x1040 + t]
                texgens.append(dict(src=(v >> 7) & 0x1F, kind=(v >> 4) & 7, proj=(v >> 1) & 1))
        mats.append(dict(name=nm, index=r.s32(mo + 0xC), ntexgen=r.u8(mo + 0x14), nchan=r.u8(mo + 0x15),
                         nstages=nst, cull=r.u32(mo + 0x18), textures=texs,
                         stages=tev_stages(r, so, nst) if so in shaders else [],
                         regs={'C%d' % (n - 1): reg_colour('c', n) for n in (1, 2, 3)},
                         konst={'K%d' % n: reg_colour('k', n) for n in range(4)},
                         map_modes=modes[:ntex], texgens=texgens,
                         alpha_compare=bp.get(0xF3, 0), blend=bp.get(0x41, 0), zmode=bp.get(0x40, 0)))
    mats.sort(key=lambda m: m['index'])
    model['materials'] = mats
    # objects
    objs = []
    for nm, oo in sec['objs']:
        node = r.s32(oo + 8)
        lo, hi = r.u32(oo + 0xC), r.u32(oo + 0x10)
        prim_size, prim_off = r.s32(oo + 0x28), r.s32(oo + 0x2C)
        dl = read_dl(r, oo + 0x24 + prim_off, prim_size)
        ids = dict(pos=r.s16(oo + 0x48), nrm=r.s16(oo + 0x4A), col0=r.s16(oo + 0x4C), col1=r.s16(oo + 0x4E))
        for t in range(8):
            ids['uv%d' % t] = r.s16(oo + 0x50 + 2 * t)
        nt = oo + r.s32(oo + 0x64) if ver >= 10 else oo + r.s32(oo + 0x60)
        cnt = r.s32(nt)
        if not 0 <= cnt < 256:
            raise ValueError('MDL0: object %s node table count %d' % (nm, cnt))
        table = [r.u16(nt + 4 + 2 * k) for k in range(cnt)]
        vcd = parse_vcd(lo, hi)
        tris, loads = parse_primitives(r, dl, vcd)
        objs.append(dict(name=nm, index=r.s32(oo + 0x3C), node=node, vcd=vcd, ids=ids, tris=tris, node_table=table,
                         nverts=r.s32(oo + 0x40), nfaces=r.s32(oo + 0x44), matrix_loads=loads))
    objs.sort(key=lambda o: o['index'])
    model['objects'] = objs
    # draw lists (definitions): DrawOpa / DrawXlu: 0x04 material u16, object u16, bone u16, priority u8
    draw = []
    for nm, do in sec['defs']:
        if nm in ('DrawOpa', 'DrawXlu'):
            i = do
            while r.u8(i) == 0x04:
                draw.append(dict(list=nm, material=r.u16(i + 1), object=r.u16(i + 3), bone=r.u16(i + 5),
                                 priority=r.u8(i + 7)))
                i += 8
    model['draw'] = draw
    model['node_bone'] = node_of
    return model


def object_vertices(model, obj):
    """an object's triangles as world-space (bind pose) arrays: positions, normals, UV0, bone index per vertex"""
    A = model['arrays']
    pos_a = A['pos'][obj['ids']['pos']][1]
    nrm_a = A['nrm'][obj['ids']['nrm']][1] if obj['ids']['nrm'] >= 0 and A['nrm'] else None
    uv_a = A['uv'][obj['ids']['uv0']][1] if obj['ids']['uv0'] >= 0 and A['uv'] else None
    bones = model['bones']
    out = dict(pos=[], nrm=[], uv=[], bone=[], key=[])
    for tri in obj['tris']:
        for v in tri:
            node = obj['node'] if obj['node'] >= 0 else v['node']
            if node is None:
                raise ValueError('MDL0: object %s: a vertex with no matrix loaded' % obj['name'])
            bi = model['node_bone'][node]
            w = np.vstack([bones[bi]['world'], [0, 0, 0, 1]])
            p = pos_a[v['pos']]
            out['pos'].append((w @ np.r_[p, 1.0])[:3])
            if nrm_a is not None and 'nrm' in v:
                n = w[:3, :3] @ nrm_a[v['nrm']]
                out['nrm'].append(n / max(np.linalg.norm(n), 1e-9))
            else:
                out['nrm'].append(np.array([0.0, 1.0, 0.0]))
            out['uv'].append(uv_a[v['uv0']] if uv_a is not None and 'uv0' in v else np.zeros(2))
            out['bone'].append(bi)
            out['key'].append((v.get('pos'), v.get('nrm'), v.get('uv0'), bi))
    return {k: (np.array(v) if k != 'key' else v) for k, v in out.items()}


# ---------------------------------------------------------------- conversion
FACE_AXES = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}


def turn_to_z(axis):
    """the rotation (about Y when the axis is horizontal) taking AXIS to +Z"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0])
    if np.allclose(a, z):
        return np.eye(3)
    if np.allclose(a, -z):
        return np.diag([-1.0, 1.0, -1.0])
    if abs(a[1]) < 1e-9:
        th = math.atan2(a[0], a[2])                # rotate about Y by -th
        c, s = math.cos(-th), math.sin(-th)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    v = np.cross(a, z)
    s, c = np.linalg.norm(v), float(a @ z)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k * ((1 - c) / s ** 2)


def mat_to_euler_xyz(m):
    """R = Rz Ry Rx -> (x, y, z) radians (the VBN's order)"""
    sy = -m[2, 0]
    sy = max(-1.0, min(1.0, sy))
    y = math.asin(sy)
    if abs(sy) < 0.999999:
        x = math.atan2(m[2, 1], m[2, 2])
        z = math.atan2(m[1, 0], m[0, 0])
    else:
        x = math.atan2(-m[1, 2], m[1, 1])
        z = 0.0
    return x, y, z


def skeleton(model, scale, turn):
    """the converted skeleton: [{'name', 'parent', 'pos', 'rot' (radians XYZ), 'scale', 'world' 4x4}] with TransN
    (the turn) first; a source bone i is converted bone i + 1"""
    out = [dict(name='TransN', parent=-1, pos=[0.0, 0.0, 0.0], rot=list(mat_to_euler_xyz(turn)), scale=[1.0, 1.0, 1.0])]
    T = np.eye(4)
    T[:3, :3] = turn
    out[0]['world'] = T
    for b in model['bones']:
        loc = b['local'].copy()
        loc[:3, 3] *= scale
        sc = np.linalg.norm(loc[:3, :3], axis=0)
        rot = loc[:3, :3] / np.where(sc > 1e-9, sc, 1.0)
        par = b['parent'] + 1 if b['parent'] >= 0 else 0
        e = dict(name=b['name'], parent=par, pos=list(loc[:3, 3]), rot=list(mat_to_euler_xyz(rot)), scale=list(sc))
        e['world'] = out[par]['world'] @ loc
        out.append(e)
    return out


VIEW_RIGHT = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])   # Ry(+90): model +Z -> view +X


def sphere_uv(nrm_view):
    """GX's EnvCamera texgen of a camera-space normal: u = 0.5 + 0.5 x, v = 0.5 - 0.5 y"""
    return np.c_[0.5 + 0.5 * nrm_view[:, 0], 0.5 - 0.5 * nrm_view[:, 1]]


def env_bake(mat, images):
    """an environment-mapped material's look as one texture in sphere-map space, or None. The TEV this handles: a
    flat colour (stage 0: TEXC x C0 into a register), lit by an EnvCamera light map (TEXC x that register) and an
    EnvCamera reflection added (CPREV + TEXC x a register alpha). The light maps (EnvCamera textures multiplied in)
    are left to the game's lighting; the reflections (added) are baked: colour + k x env. -> (image, info)"""
    st = mat['stages']
    base = None
    add = []
    for s in st:
        c = s['c']
        name = mat['textures'][s['tex_map']]['name'] if s['tex_on'] and s['tex_map'] < len(mat['textures']) else None
        mode = mat['map_modes'][s['tex_map']] if s['tex_map'] < len(mat['map_modes']) else 0
        if base is None and mode == 0 and c['b'] == 'TEXC' and c['a'] == 'ZERO' and c['d'] == 'ZERO':
            base = name
        elif mode == 1 and c['d'] == 'CPREV' and c['a'] == 'ZERO' and c['b'] == 'TEXC' and c['c'] in ('A0', 'A1', 'A2'):
            reg = mat['regs']['C' + c['c'][1]]
            add.append((name, reg[3]))
    if base is None or not add:
        return None
    b = images[base].astype(np.float64)[..., :3]
    flat = b.reshape(-1, 3).mean(0)
    env_name, k = add[0]
    env = images[env_name].astype(np.float64)
    out = np.clip(flat[None, None, :] + k * env[..., :3], 0, 255)
    img = np.concatenate([out, np.full(out.shape[:2] + (1,), 255.0)], axis=2).astype(np.uint8)
    return img, dict(base=base, base_colour=tuple(round(x) for x in flat), env=env_name, k=k)


def load_png(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGBA'))


GX_WRAP_NUD = {0: 3, 1: 1, 2: 2}           # GX clamp / repeat / mirror -> NUD (1 repeat, 2 mirror, 3 clamp)
GX_CULL_NUD = {0: 0, 1: 1028, 2: 1029, 3: 0}  # GX cull none / front / back / all -> NUD (0 none, 1028 front, 1029 back)


def convert(src, tex_dir, out_dir, scale=1.0, face='+z', head=None, tex_id=0x15A00000, env_bake_mats=(), log=print):
    """-> info dict; writes the model folder"""
    import nud
    import nut
    import s3ds_enemy as se
    model = parse(src)
    bones = model['bones']
    # the head direction: the head bone's (or the root's first child's) offset from the root in the MDL0's space
    if face == 'auto':
        hb = next((b for b in bones if b['name'] == head), None) if head else \
            next((b for b in bones if b['parent'] == 0), None)
        v = hb['world'][:3, 3] - bones[0]['world'][:3, 3]
        v[1] = 0.0
        face_axis = v / max(np.linalg.norm(v), 1e-9)
    else:
        face_axis = np.array(FACE_AXES[face], float)
    turn = turn_to_z(face_axis)
    skel = skeleton(model, scale, turn)
    images = {}
    for m in model['materials']:
        for t in m['textures']:
            if t['name'] not in images:
                p = os.path.join(tex_dir, t['name'] + '.png')
                images[t['name']] = load_png(p)
    ids = {}
    nut_list = []

    def tex(key, img):
        if key not in ids:
            ids[key] = tex_id + len(nut_list)
            nut_list.append((ids[key], 0x33 if (img[..., 3] < 250).any() else 0x31, se._pow2(img)))
        return ids[key]
    flat = tex('#flat', np.full((64, 64, 4), (128, 128, 255, 255), np.uint8))
    meshes = []
    info = dict(objects=[], bones=len(skel), scale=scale, face_axis=list(face_axis), materials=[])
    by_obj = {d['object']: d for d in model['draw']}
    T4 = np.eye(4)
    T4[:3, :3] = turn
    for oi, obj in enumerate(model['objects']):
        dr = by_obj.get(oi)
        mat = model['materials'][dr['material']] if dr else model['materials'][0]
        ov = object_vertices(model, obj)
        # weld identical (pos, nrm, uv, bone) corners
        keys = {}
        vidx = []
        for k in ov['key']:
            vidx.append(keys.setdefault(k, len(keys)))
        vidx = np.array(vidx)
        first = np.zeros(len(keys), np.int64)
        first[vidx[::-1]] = np.arange(len(vidx))[::-1]
        pos = (ov['pos'][first] * scale) @ turn.T
        nrm = ov['nrm'][first] @ turn.T
        uv = ov['uv'][first]
        bone = ov['bone'][first] + 1
        tri = vidx.reshape(-1, 3)
        baked = mat['name'] in env_bake_mats and env_bake(mat, images)
        tinfo = dict(name=obj['name'], material=mat['name'], vertices=len(first), triangles=len(tri),
                     uv_min=list(np.round(uv.min(0), 4)), uv_max=list(np.round(uv.max(0), 4)))
        if baked:
            img, binfo = baked
            # the sphere-map coordinates GX makes per vertex: the bind-pose normal in the side camera's space, the
            # model (turned to face +Z) seen as the game shows an article facing right (turned +90 degrees about Y:
            # its head to the right, the camera on +Z): view = Ry(90) x turn x normal
            uv = sphere_uv(nrm @ (VIEW_RIGHT @ np.eye(3)).T)
            color = tex(('#bake', mat['name']), img)
            wrap = (3, 3)
            tinfo['baked'] = binfo
            # the GX geometry's UV is no longer used: per-vertex sphere coordinates, so split nothing
        else:
            t0 = mat['textures'][0]
            color = tex(t0['name'], images[t0['name']])
            wrap = (GX_WRAP_NUD.get(t0['wrap_s'], 1), GX_WRAP_NUD.get(t0['wrap_t'], 1))
        p = nud.Polygon()
        p.pos = pos
        p.nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        p.uvs = [uv.copy()]
        p.col = np.full((len(pos), 4), se.WHITE)
        p.idx = tri.reshape(-1)
        p.tan, p.bit = se.tangents(p.pos, p.nrm, p.uvs[0], tri)
        p.bones = np.zeros((len(pos), 4), np.int64)
        p.bones[:, :] = bone[:, None]
        p.weights = np.zeros((len(pos), 4), np.int64)
        p.weights[:, 0] = 255
        m = nud.Material(se.BODY_FLAGS, 0, 0, 0, 0, GX_CULL_NUD.get(mat['cull'], 1029))
        for tid in (color, flat, se.RAMP):
            m.textures.append(dict(hash=tid, map_mode=0, wrap_s=wrap[0], wrap_t=wrap[1], min_f=3, mag_f=2, mip=6,
                                   unk=0, unk2=0))
        m.textures[1]['wrap_s'] = m.textures[1]['wrap_t'] = 1
        m.textures[2]['wrap_s'] = m.textures[2]['wrap_t'] = 3
        _bits, val = se.float_hash(mat['name'])
        m.props = [(n, [val, 0.0, 0.0, 0.0] if n == 'NU_materialHash' else list(v)) for n, v in se.BODY_PROPS]
        p.materials = [m]
        meshes.append(nud.Mesh(obj['name'], [p], -1, 4))
        info['objects'].append(tinfo)
        log('  object %-10s %-20s %4d vertices %4d triangles%s' % (obj['name'], mat['name'], len(pos), len(tri),
                                                                    ' (env baked)' if baked else ''))
    os.makedirs(out_dir, exist_ok=True)
    nud_b = nud.write(meshes, top_bone=len(skel) - 1)
    open(os.path.join(out_dir, 'model.nud'), 'wb').write(nud_b)
    open(os.path.join(out_dir, 'model.nut'), 'wb').write(nut.write_ntwu(nut_list))
    vb = [dict(name=b['name'], parent=b['parent'], pos=b['pos'], rot=b['rot'], scale=b['scale']) for b in skel]
    open(os.path.join(out_dir, 'model.vbn'), 'wb').write(se.vbn_bytes(vb))
    open(os.path.join(out_dir, 'model.jtb'), 'wb').write(struct.pack('>H%dH' % len(skel), len(skel), *range(len(skel))))
    open(os.path.join(out_dir, 'model.flp'), 'wb').write(b'FLIP' + struct.pack('>BBH', 1, 0, 0) + b'\0' * 4)
    for f in se.DEFAULT_FILES:
        open(os.path.join(out_dir, f), 'wb').write(open(os.path.join(se.DEFAULTS, f), 'rb').read())
    allp = np.concatenate([m.polygons[0].pos for m in meshes])
    info.update(min=list(np.round(allp.min(0), 3)), max=list(np.round(allp.max(0), 3)), textures=len(nut_list),
                skeleton=[(b['name'], b['parent']) for b in skel], turn=turn.tolist())
    for m in model['materials']:
        info['materials'].append(dict(name=m['name'], textures=[t['name'] for t in m['textures']],
                                      modes=[MAP_MODES.get(x, x) for x in m['map_modes']],
                                      stages=[tev_text(s) for s in m['stages']], regs=m['regs'],
                                      opaque=not (m['blend'] & 1), alpha_compare=m['alpha_compare']))
    return info


def print_info(model):
    print('MDL0 v%d %s' % (model['version'], model['name']))
    for i, b in enumerate(model['bones']):
        print('  bone %d %-10s parent %2d scale %s rot %s pos %s' % (i, b['name'], b['parent'],
              tuple(round(x, 3) for x in b['scale']), tuple(round(x, 3) for x in b['rot']),
              tuple(round(x, 3) for x in b['pos'])))
        err = np.abs(b['world'][:3] - b['bind']).max()
        print('       world matrix vs the stored bind matrix: max error %.2e' % err)
    for k, arr in model['arrays'].items():
        for nm, a in arr:
            print('  %s %-40s %4d x %d  min %s max %s' % (k, nm, len(a), a.shape[1] if len(a) else 0,
                                                         np.round(a.min(0), 3) if len(a) else '-',
                                                         np.round(a.max(0), 3) if len(a) else '-'))
    for o in model['objects']:
        print('  object %s node %d vcd %s ids %s nodes %s: %d triangles (header %d faces, %d vertices), %d matrix loads'
              % (o['name'], o['node'], o['vcd'], {k: v for k, v in o['ids'].items() if v >= 0}, o['node_table'],
                 len(o['tris']), o['nfaces'], o['nverts'], o['matrix_loads']))
    for m in model['materials']:
        print('  material %s cull %d textures %s modes %s texgens %s regs %s konst %s alpha compare %06X blend %06X '
              'z %06X' % (m['name'], m['cull'], [(t['name'], t['wrap_s'], t['wrap_t']) for t in m['textures']],
                          [MAP_MODES.get(x, x) for x in m['map_modes']], m['texgens'], m['regs'], m['konst'],
                          m['alpha_compare'], m['blend'], m['zmode']))
        for s in m['stages']:
            print('     ' + tev_text(s))
    for d in model['draw']:
        print('  draw %s' % d)


def verify(out_dir):
    import nud
    import nut
    import omo
    ms = nud.read(os.path.join(out_dir, 'model.nud'))
    dn, texs = nut.load(os.path.join(out_dir, 'model.nut'))
    vb = omo.vbn_read(os.path.join(out_dir, 'model.vbn'))
    out = dict(meshes=[(m.name, sum(p.nv for p in m.polygons), sum(len(p.idx) // 3 for p in m.polygons))
                       for m in ms], textures=[(hex(t.tex_id), nut.decode(dn, t).shape) for t in texs],
               bones=[b[0] for b in vb])
    return out


def main():
    if len(sys.argv) > 2 and sys.argv[1] == 'verify':
        print(verify(sys.argv[2]))
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('mdl0')
    ap.add_argument('tex_dir', nargs='?')
    ap.add_argument('out_dir', nargs='?')
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--face', default='auto')
    ap.add_argument('--head', default=None)
    ap.add_argument('--tex-id', type=lambda s: int(s, 0), default=0x15A00000)
    ap.add_argument('--env-bake', action='append', default=[])
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    if a.info:
        print_info(parse(a.mdl0))
        return
    info = convert(a.mdl0, a.tex_dir, a.out_dir, a.scale, a.face, a.head, a.tex_id, a.env_bake)
    print(info)


if __name__ == '__main__':
    main()
