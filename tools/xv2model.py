#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 effect models: EMO (+ its EMG meshes and skeleton), EMM materials,
EMA animations (obj = bone TRS, mat = material parameters, light).

  python3 tools/xv2model.py dump FILE.emo|.emm|.ema [OUT.json]   summary on stdout; everything
                                                                as JSON when OUT.json is given

Little-endian. Layouts ported from LazyBone152's XV2-Tools (Xv2CoreLib: EMO/EMO_File.cs,
EMG/EMG_File.cs, EMD/EMD_File.cs (vertices, samplers), EMM/Parser.cs, Animation/EMA/EMA_File.cs,
Animation/EMA/Skeleton.cs); the XML / UI parts are left out.

EMO: +0 "#EMO", +8 version, +12 parts header offset, +16 skeleton offset, +20 vertex data offset
  (the vertices may sit after the skeleton; mesh vertex offsets are relative to the mesh anyway),
  +24 u64. Parts header: u16 part count, u16 material count, u32 names table (relative to the
  header), then a u32 per part (relative to the header). Part: u32 EMG count, u32 per EMG
  (relative to the part). A part's name is its skeleton bone's when a bone links to it.
EMG: +0 "#EMG", +4 u16 linked bone, +6 u16 mesh count, +8 u32 per mesh (relative to the EMG).
  Mesh: +0 vertex flags, +4 texture list count, +8 i32, +12 texture lists (relative to the mesh),
  +16 u16 vertex count, +18 u16 vertex size, +20 vertex offset, +24 u16 strips, +26 u16 submesh
  count, +28 submesh table, +32 AABB (centre, min, max: 12 floats). Texture list: u32 count, 12
  bytes a sampler (u8 flag, u8 EMB index, u8 address U | V << 4 (0 wrap 1 mirror 2 clamp), u8
  filter min | mag << 4, f32 scale U, f32 scale V). Submesh: 4 floats barycentre, u16 texture
  list, u16 index count, u16 bone count, 32-byte material name, u16 indices, u16 bone indices
  (the skeleton bones the vertices' blend indices pick from).
  Vertex (flags): 0x1 position 3f, 0x2 normal, 0x4 UV, 0x8 UV2, 0x80 tangent, 0x40 colour 4 u8
  (RGBA), 0x200 blend 4 u8 indices + 3 weights (the 4th = 1 - the others); 0x8000 = normal /
  UV / tangent / weights as half floats (normal and tangent 4 halves).
  `strips` != 0 is read as triangle strips (an assumption: XV2-Tools always reads the indices as
  a triangle list; every mesh of the Kamehameha has strips 0).
Skeleton (EMO and EMA; the IK data is counted, not read): +0 u16 bones, +2 u16 IK2 count, +4 u32
  IK count, +8 bones, +12 names, +24 extra values, +28 absolute matrices, +32 IK data, +36..+51
  4 u32, +52 u16, +54 u16 flag, +56 u64 id.
  Bone (80 bytes): u16 parent, child, sibling, EMO part (0xFFFF none), u16, u16 IK flag, f32,
  a 4x4 relative matrix (row vectors: translation in the 4th row).
EMM: +0 "#EMM", +8 version, +12 u32 header size / offset of the material table (u32 count, u32 per
  material, relative to the header size). Material: 32-byte name, 32-byte shader, u16 parameter
  count, u16, then 40 bytes a parameter: 32-byte name, u32 type (0 float, 1 bool, 0x10000 float2,
  0x10001 int), a 4-byte value.
EMA: +0 "#EMA", +8 version, +12 skeleton offset, +16 u16 animation count, +18 u16 type (3 obj,
  4 light, 8 mat), +20..+31 3 i32, +32 u32 per animation. Animation: u16 end frame, u16 command
  count, u32 value count, u8 type (0 obj 1 cam 2 light 3 mat), u8, u16 value type (0 vector4 /
  2 float32: f32 values, 1 float16), u32 name offset (the name at +11 from it), u32 values offset,
  u32 per command (all relative to the animation). Command: u16 bone (obj: the EMA skeleton's
  bone; mat: the EMA skeleton's bone index = the EMM material index), u8 parameter (obj 0
  position, 1 rotation (Euler degrees X Y Z), 2 scale; mat 0-3 MatCol0-3, 4-7 TexScrl0-3; light
  2 colour, 3 radii), u8 flags (bits 0-1 component X/R..W/A, bit 2 no-interpolation, bit 3 ?,
  bit 5 u16 times, bit 6 u32 value indices), u16 keyframe count, u16 offset of the value
  indices; the times (u8 or u16); the value indices (u16: index & 0x3FFF, interpolation & 0xC000;
  or u32: index & 0xFFFFFF, interpolation >> 24): 0 linear, 0x40 quadratic Bezier (one control
  value follows the value), 0x80 cubic Bezier (two). Bezier control values are offsets: the curve
  from v0 to v1 runs through v0 + c1 (and v1 - c2) (EMA_File.AddInterpolatedKeyframes).
  A component without keyframes takes its default (position / rotation 0, scale 1, W 1).
"""
import json
import math
import struct
import sys

import numpy as np

EMA_OBJ, EMA_LIGHT, EMA_MAT = 3, 4, 8
LINEAR, QUADRATIC, CUBIC = 0, 0x40, 0x80
MAT_PARAMS = ['MatCol0', 'MatCol1', 'MatCol2', 'MatCol3', 'TexScrl0', 'TexScrl1', 'TexScrl2', 'TexScrl3']
OBJ_PARAMS = ['Position', 'Rotation', 'Scale']


def _u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def _i32(d, o):
    return struct.unpack_from('<i', d, o)[0]


def _cstr(d, o, n=None):
    end = d.index(b'\0', o) if n is None else o + n
    return d[o:end].split(b'\0')[0].decode('utf-8', 'replace')


# ---------------------------------------------------------------- skeleton
class Bone:
    def __init__(self):
        self.index = self.parent = self.child = self.sibling = self.emo_part = 0
        self.i_08 = self.ik_flag = 0
        self.f_12 = 0.0
        self.name = ''
        self.matrix = np.eye(4)         # relative (to the parent) matrix, row vectors
        self.abs_matrix = None

    def to_dict(self):
        return dict(index=self.index, name=self.name, parent=_none(self.parent), child=_none(self.child),
                    sibling=_none(self.sibling), emo_part=_none(self.emo_part), i_08=self.i_08,
                    ik_flag=self.ik_flag, f_12=self.f_12, matrix=self.matrix.tolist(),
                    abs_matrix=None if self.abs_matrix is None else self.abs_matrix.tolist())


def _none(v):
    return None if v == 0xFFFF else v


def _matrix(d, o):
    return np.array(struct.unpack_from('<16f', d, o), dtype=np.float64).reshape(4, 4)


class Skeleton:
    def __init__(self, d, so):
        nb, ik2 = struct.unpack_from('<HH', d, so)
        self.ik_count = _i32(d, so + 4)
        bo, no = _i32(d, so + 8), _i32(d, so + 12)
        extra, absm, self.ik_offset = _i32(d, so + 24), _i32(d, so + 28), _i32(d, so + 32)
        self.has_extra_values = extra > 0
        self.i_36 = struct.unpack_from('<4i', d, so + 36)
        self.i_52, self.flag = struct.unpack_from('<HH', d, so + 52)
        self.skeleton_id = struct.unpack_from('<Q', d, so + 56)[0]
        assert ik2 == 0, 'IK2 data not supported'
        self.bones = []
        for i in range(nb):
            b = Bone()
            o = so + bo + 80 * i
            b.index = i
            b.parent, b.child, b.sibling, b.emo_part, b.i_08, b.ik_flag = struct.unpack_from('<6H', d, o)
            b.f_12 = struct.unpack_from('<f', d, o + 12)[0]
            b.matrix = _matrix(d, o + 16)
            if absm > 0:
                b.abs_matrix = _matrix(d, so + absm + 64 * i)
            b.name = _cstr(d, so + _i32(d, so + no + 4 * i))
            self.bones.append(b)

    def index(self, name):
        for b in self.bones:
            if b.name == name:
                return b.index
        return -1

    def world(self, local=None):
        """{bone index: world matrix (row vectors)} from the relative matrices (or `local`,
        {index: matrix} overrides)"""
        out = {}

        def get(i):
            if i not in out:
                b = self.bones[i]
                m = local[i] if local and i in local else b.matrix
                p = _none(b.parent)
                out[i] = m @ get(p) if p is not None and p < len(self.bones) else m
            return out[i]
        for b in self.bones:
            get(b.index)
        return out

    def to_dict(self):
        return dict(bones=[b.to_dict() for b in self.bones], ik_count=self.ik_count, flag=self.flag,
                    skeleton_id=self.skeleton_id)


# ---------------------------------------------------------------- EMO / EMG
VF_POS, VF_NRM, VF_UV, VF_UV2, VF_COL, VF_TAN, VF_BLEND, VF_HALF = 0x1, 0x2, 0x4, 0x8, 0x40, 0x80, 0x200, 0x8000


def vertex_dtype(flags):
    h = flags & VF_HALF
    f = '<f2' if h else '<f4'
    cols = []
    if flags & VF_POS:
        cols.append(('pos', '<f4', (3,)))
    if flags & VF_NRM:
        cols.append(('nrm', f, (4,) if h else (3,)))
    if flags & VF_UV:
        cols.append(('uv', f, (2,)))
    if flags & VF_UV2:
        cols.append(('uv2', f, (2,)))
    if flags & VF_TAN:
        cols.append(('tan', f, (4,) if h else (3,)))
    if flags & VF_COL:
        cols.append(('col', 'u1', (4,)))
    if flags & VF_BLEND:
        cols.append(('bidx', 'u1', (4,)))
        cols.append(('bw', f, (3,)))
    return np.dtype(cols)


class Sampler:
    def __init__(self, d, o):
        self.flag, self.emb_index, a, f = struct.unpack_from('<4B', d, o)
        self.address_u, self.address_v = a & 15, a >> 4
        self.filter_min, self.filter_mag = f & 15, f >> 4
        self.scale_u, self.scale_v = struct.unpack_from('<2f', d, o + 4)

    def to_dict(self):
        return dict(self.__dict__)


class Submesh:
    def __init__(self, d, o):
        self.barycenter = struct.unpack_from('<4f', d, o)
        self.texture_list, nidx, nbone = struct.unpack_from('<3H', d, o + 16)
        self.material = _cstr(d, o + 22, 32)
        self.indices = np.frombuffer(d, '<u2', nidx, o + 54).astype(np.int64)
        self.bones = list(struct.unpack_from('<%dH' % nbone, d, o + 54 + 2 * nidx))

    def triangles(self, strips):
        """[n, 3] triangle list (strips unrolled, degenerate triangles dropped)"""
        ix = self.indices
        if not strips:
            return ix[:len(ix) // 3 * 3].reshape(-1, 3)
        tris = []
        for i in range(len(ix) - 2):
            a, b, c = ix[i], ix[i + 1], ix[i + 2]
            if a == b or b == c or a == c:
                continue
            tris.append((a, b, c) if i % 2 == 0 else (b, a, c))
        return np.array(tris, dtype=np.int64).reshape(-1, 3)


class EmgMesh:
    def __init__(self, d, o):
        self.flags, ntl = struct.unpack_from('<2i', d, o)
        self.i_08 = _i32(d, o + 8)
        tlo = _i32(d, o + 12) + o
        nv, vs = struct.unpack_from('<HH', d, o + 16)
        vo = _i32(d, o + 20) + o
        self.strips, nsub = struct.unpack_from('<HH', d, o + 24)
        sto = _i32(d, o + 28) + o
        a = struct.unpack_from('<12f', d, o + 32)
        self.aabb = dict(center=a[0:4], min=a[4:8], max=a[8:12])
        self.texture_lists = []
        for i in range(ntl):
            to = _i32(d, tlo + 4 * i) + o
            self.texture_lists.append([Sampler(d, to + 4 + 12 * k) for k in range(_i32(d, to))])
        self.submeshes = [Submesh(d, _i32(d, sto + 4 * i) + o) for i in range(nsub)]
        dt = vertex_dtype(self.flags)
        assert dt.itemsize == vs, 'vertex size %d != %d (flags 0x%X)' % (vs, dt.itemsize, self.flags)
        self.vertices = np.frombuffer(d, dt, nv, vo)

    def attr(self, name):
        """a vertex attribute as float64 (None if absent); 'bw' with the 4th weight"""
        if name not in self.vertices.dtype.names:
            return None
        a = self.vertices[name].astype(np.float64)
        if name == 'bw':
            a = np.concatenate([a, 1 - a.sum(1, keepdims=True)], 1)
        return a


class Emg:
    def __init__(self, d, o):
        assert d[o:o + 4] == b'#EMG', 'no #EMG at 0x%X' % o
        self.bone, nm = struct.unpack_from('<HH', d, o + 4)
        self.meshes = [EmgMesh(d, _i32(d, o + 8 + 4 * i) + o) for i in range(nm)]


class Emo:
    def __init__(self, d):
        assert d[:4] == b'#EMO', 'not an EMO'
        self.version = _i32(d, 8)
        ph, so = _i32(d, 12), _i32(d, 16)
        self.i_24 = struct.unpack_from('<Q', d, 24)[0]
        npart, self.material_count = struct.unpack_from('<HH', d, ph)
        names = _i32(d, ph + 4) + ph
        self.parts = []
        for i in range(npart):
            po = _i32(d, ph + 8 + 4 * i) + ph
            name = _cstr(d, _i32(d, names + 4 * i) + ph)
            emgs = [Emg(d, _i32(d, po + 4 + 4 * k) + po) for k in range(_i32(d, po))]
            self.parts.append(dict(name=name, emgs=emgs, bone=None))
        self.skeleton = Skeleton(d, so) if so else None
        if self.skeleton:
            for b in self.skeleton.bones:
                if b.emo_part != 0xFFFF and b.emo_part < npart:
                    self.parts[b.emo_part]['bone'] = b.index
                    self.parts[b.emo_part]['name'] = b.name

    def to_dict(self, vertices=False):
        parts = []
        for p in self.parts:
            emgs = []
            for g in p['emgs']:
                meshes = []
                for m in g.meshes:
                    md = dict(flags='0x%X' % m.flags, vertex_count=len(m.vertices), strips=m.strips, i_08=m.i_08,
                              aabb=m.aabb, texture_lists=[[s.to_dict() for s in tl] for tl in m.texture_lists],
                              submeshes=[dict(material=s.material, texture_list=s.texture_list,
                                              index_count=len(s.indices), triangles=len(s.triangles(m.strips)),
                                              bones=s.bones, barycenter=s.barycenter) for s in m.submeshes])
                    if vertices:
                        md['vertices'] = {k: m.attr(k).tolist() for k in m.vertices.dtype.names}
                        md['indices'] = [s.indices.tolist() for s in m.submeshes]
                    meshes.append(md)
                emgs.append(dict(bone=g.bone, meshes=meshes))
            parts.append(dict(name=p['name'], bone=p['bone'], emgs=emgs))
        return dict(kind='emo', version='0x%X' % self.version, material_count=self.material_count, parts=parts,
                    skeleton=self.skeleton.to_dict() if self.skeleton else None)


# ---------------------------------------------------------------- EMM
PARAM_FLOAT, PARAM_BOOL, PARAM_FLOAT2, PARAM_INT = 0, 1, 0x10000, 0x10001


class Emm:
    def __init__(self, d):
        assert d[:4] == b'#EMM', 'not an EMM'
        self.version = _i32(d, 8)
        hs = struct.unpack_from('<h', d, 12)[0]
        table = _i32(d, 12)
        self.materials = []
        for i in range(_i32(d, table)):
            o = _i32(d, table + 4 + 4 * i)
            if not o:
                self.materials.append(None)
                continue
            o += hs
            m = dict(index=i, name=_cstr(d, o, 32), shader=_cstr(d, o + 32, 32), i_66=_u16(d, o + 66), params={})
            for k in range(struct.unpack_from('<h', d, o + 64)[0]):
                q = o + 68 + 40 * k
                name, typ = _cstr(d, q, 32), _i32(d, q + 32)
                if typ in (PARAM_FLOAT, PARAM_FLOAT2):
                    v = struct.unpack_from('<f', d, q + 36)[0]
                else:
                    v = _i32(d, q + 36)
                m['params'][name] = v
            self.materials.append(m)

    def find(self, name):
        for m in self.materials:
            if m and m['name'] == name:
                return m
        return None

    def to_dict(self):
        return dict(kind='emm', version='0x%X' % self.version, materials=self.materials)


def mat_vector(m, base, default=(0.0, 0.0, 0.0, 0.0)):
    """an EMM vector parameter group (MatCol0 -> MatCol0R/G/B/A, TexScrl0 -> TexScrl0U/V, MatScale0 ->
    X/Y/Z/W ...) as a list; a parameter named without a component sets them all"""
    p = m['params']
    if base in p:
        return [float(p[base])] * len(default)
    out = list(default)
    comps = ('R', 'G', 'B', 'A') if base.startswith('MatCol') else ('U', 'V') if 'Scrl' in base or 'Scroll' in base \
        else ('X', 'Y', 'Z', 'W')
    for i, c in enumerate(comps):
        if base + c in p and i < len(out):
            out[i] = float(p[base + c])
    return out


# ---------------------------------------------------------------- EMA
class Keyframe:
    __slots__ = ('time', 'value', 'interp', 'cp1', 'cp2', 'index')

    def __init__(self, time, value, interp=LINEAR, cp1=0.0, cp2=0.0, index=0):
        self.time, self.value, self.interp, self.cp1, self.cp2, self.index = time, value, interp, cp1, cp2, index


class Command:
    def __init__(self, d, o, values, ema_type):
        self.bone = _u16(d, o)
        self.parameter = d[o + 2]
        fl = d[o + 3]
        lo, hi = fl & 15, fl >> 4
        self.flags = fl
        self.component = lo & 3
        self.no_interpolation = bool(lo & 4)
        self.i_03_a4 = bool(lo & 8)
        t16, i32 = bool(hi & 2), bool(hi & 4)
        n, io = struct.unpack_from('<HH', d, o + 4)
        self.keys = []
        for i in range(n):
            t = _u16(d, o + 8 + 2 * i) if t16 else d[o + 8 + i]
            if i32:
                raw = struct.unpack_from('<I', d, o + io + 4 * i)[0]
                idx, interp = raw & 0xFFFFFF, (raw >> 24) & 0xFF
            else:
                raw = _u16(d, o + io + 2 * i)
                idx, interp = raw & 0x3FFF, d[o + io + 1 + 2 * i] & 0xC0
                if idx >= len(values):
                    idx = 0
            cp1 = cp2 = 0.0
            if interp == QUADRATIC and idx + 1 < len(values):
                cp1 = values[idx + 1]
            elif interp == CUBIC and idx + 2 < len(values):
                cp1, cp2 = values[idx + 1], values[idx + 2]
            self.keys.append(Keyframe(t, values[idx], interp, cp1, cp2, idx))
        self.keys.sort(key=lambda k: k.time)
        self.ema_type = ema_type

    def name(self):
        if self.ema_type == 0:
            return OBJ_PARAMS[self.parameter] if self.parameter < 3 else str(self.parameter)
        if self.ema_type == 3:
            return MAT_PARAMS[self.parameter] if self.parameter < 8 else str(self.parameter)
        return {2: 'Color', 3: 'Light'}.get(self.parameter, str(self.parameter))

    def sample(self, frame, default=0.0):
        """the value at `frame` (Bezier keys as AddInterpolatedKeyframes: control points v0 + c1,
        v1 - c2; held before the first / after the last key)"""
        ks = self.keys
        if not ks:
            return default
        if frame <= ks[0].time:
            return ks[0].value
        if frame >= ks[-1].time:
            return ks[-1].value
        for a, b in zip(ks, ks[1:]):
            if a.time <= frame <= b.time:
                if b.time == a.time:
                    return b.value
                f = (frame - a.time) / (b.time - a.time)
                if a.interp == CUBIC:
                    p1, p2 = a.value + a.cp1, b.value - a.cp2
                    return ((1 - f) ** 3 * a.value + 3 * (1 - f) ** 2 * f * p1 + 3 * (1 - f) * f * f * p2
                            + f ** 3 * b.value)
                if a.interp == QUADRATIC:
                    p1 = a.value + a.cp1
                    return (1 - f) ** 2 * a.value + 2 * (1 - f) * f * p1 + f * f * b.value
                return a.value + (b.value - a.value) * f
        return ks[-1].value

    def to_dict(self):
        return dict(bone=self.bone, parameter=self.name(), component=self.component, flags='0x%02X' % self.flags,
                    keys=[[k.time, k.value] + ([{0x40: 'quad', 0x80: 'cubic'}[k.interp], k.cp1, k.cp2] if k.interp else [])
                          for k in self.keys])


class Animation:
    def __init__(self, d, o, index):
        self.index = index
        self.end_frame, nc = struct.unpack_from('<HH', d, o)
        nv = _i32(d, o + 4)
        self.type, self.light_unknown = d[o + 8], d[o + 9]
        self.value_type = _u16(d, o + 10)
        no, vo = _i32(d, o + 12), _i32(d, o + 16) + o
        self.name = _cstr(d, no + o + 11) if no else ''
        if self.value_type == 1:
            values = np.frombuffer(d, '<f2', nv, vo).astype(np.float64).tolist()
        else:
            values = np.frombuffer(d, '<f4', nv, vo).astype(np.float64).tolist()
        self.values = values
        self.commands = []
        for i in range(nc):
            co = _i32(d, o + 20 + 4 * i)
            if co:
                self.commands.append(Command(d, co + o, values, self.type))

    def frames(self):
        """frame count (end frame + 1, or past the last key)"""
        last = max([k.time for c in self.commands for k in c.keys] + [0])
        return max(self.end_frame, last) + 1

    def command(self, bone, parameter, component):
        for c in self.commands:
            if c.bone == bone and c.parameter == parameter and c.component == component:
                return c
        return None

    def bones(self):
        return sorted({c.bone for c in self.commands})

    def sample_trs(self, bone, frame):
        """obj: (position xyz, rotation Euler degrees xyz, scale xyz) of `bone` at `frame`, or None
        if it has no command; W components (position W, rotation W, scale W) multiply"""
        if bone not in self.bones():
            return None
        out = []
        for p, dflt in ((0, 0.0), (1, 0.0), (2, 1.0)):
            v = [self._s(bone, p, c, frame, dflt) for c in range(3)]
            w = self._s(bone, p, 3, frame, 1.0)
            out.append([x * w for x in v])
        return out

    def _s(self, bone, p, c, frame, dflt):
        cmd = self.command(bone, p, c)
        return cmd.sample(frame, dflt) if cmd else dflt


class Ema:
    def __init__(self, d):
        assert d[:4] == b'#EMA', 'not an EMA'
        self.version = _i32(d, 8)
        so = _i32(d, 12)
        na, self.type = struct.unpack_from('<HH', d, 16)
        self.i_20 = struct.unpack_from('<3i', d, 20)
        self.skeleton = Skeleton(d, so) if so > 0 else None
        self.animations = []
        for i in range(na):
            ao = _i32(d, 32 + 4 * i)
            if ao:
                self.animations.append(Animation(d, ao, i))

    def bone_name(self, i):
        return self.skeleton.bones[i].name if self.skeleton and i < len(self.skeleton.bones) else None

    def to_dict(self):
        anims = []
        for a in self.animations:
            anims.append(dict(index=a.index, name=a.name, end_frame=a.end_frame, frames=a.frames(), type=a.type,
                              value_type=a.value_type,
                              commands=[dict(c.to_dict(), bone_name=self.bone_name(c.bone)) for c in a.commands]))
        return dict(kind='ema', version='0x%X' % self.version, type={3: 'obj', 4: 'light', 8: 'mat'}.get(self.type, self.type),
                    animations=anims, skeleton=self.skeleton.to_dict() if self.skeleton else None)


# ---------------------------------------------------------------- math
def euler_quat(x, y, z):
    """Euler degrees (X roll, Y pitch, Z yaw) -> quaternion (x, y, z, w), as MathHelpers.EulerToQuaternion"""
    r, p, yw = (math.radians(a) * 0.5 for a in (x, y, z))
    cy, sy, cp, sp, cr, sr = math.cos(yw), math.sin(yw), math.cos(p), math.sin(p), math.cos(r), math.sin(r)
    return (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy)


def quat_rowmat(q):
    """quaternion -> 3x3 rotation for row vectors (v' = v R), as System.Numerics CreateFromQuaternion"""
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                     [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                     [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]])


def trs_rowmat(pos, rot_deg, scl):
    """scale, then rotate, then translate (row vectors): S * R * T"""
    m = np.eye(4)
    m[:3, :3] = np.diag(scl) @ quat_rowmat(euler_quat(*rot_deg))
    m[3, :3] = pos
    return m


# ---------------------------------------------------------------- CLI
def load(path):
    d = open(path, 'rb').read()
    magic = d[:4]
    if magic == b'#EMO':
        return Emo(d)
    if magic == b'#EMM':
        return Emm(d)
    if magic == b'#EMA':
        return Ema(d)
    raise ValueError('%s: unknown magic %r' % (path, magic))


def summary(path, f):
    print(path)
    if isinstance(f, Emo):
        print('  EMO version 0x%X, %d parts, %d materials' % (f.version, len(f.parts), f.material_count))
        for p in f.parts:
            print('  part %r (bone %s)' % (p['name'], p['bone']))
            for g in p['emgs']:
                for m in g.meshes:
                    nt = sum(len(s.triangles(m.strips)) for s in m.submeshes)
                    print('    emg bone %d mesh flags 0x%04X verts %d strips %d tris %d aabb min %s max %s' % (
                        g.bone, m.flags, len(m.vertices), m.strips, nt, [round(x, 3) for x in m.aabb['min'][:3]],
                        [round(x, 3) for x in m.aabb['max'][:3]]))
                    for s in m.submeshes:
                        tl = m.texture_lists[s.texture_list] if s.texture_list < len(m.texture_lists) else []
                        print('      submesh %-24s idx %4d bones %s samplers %s' % (
                            s.material, len(s.indices), s.bones,
                            ['emb%d a%d/%d s%.2gx%.2g' % (t.emb_index, t.address_u, t.address_v, t.scale_u, t.scale_v)
                             for t in tl]))
        if f.skeleton:
            for b in f.skeleton.bones:
                print('  bone %2d %-24s parent %s part %s t %s' % (b.index, b.name, _none(b.parent), _none(b.emo_part),
                                                                 [round(x, 3) for x in b.matrix[3, :3]]))
    elif isinstance(f, Emm):
        for m in f.materials:
            if m:
                print('  mat %d %-24s %s %s' % (m['index'], m['name'], m['shader'],
                                               {k: round(v, 4) if isinstance(v, float) else v for k, v in m['params'].items()}))
    else:
        print('  EMA type %s, %d animations' % (f.type, len(f.animations)))
        for a in f.animations:
            print('  anim %d %r end %d (%d frames) values %d' % (a.index, a.name, a.end_frame, a.frames(), len(a.values)))
            for c in a.commands:
                ks = ' '.join('%d:%.3g%s' % (k.time, k.value, {0: '', 0x40: 'q', 0x80: 'c'}[k.interp]) for k in c.keys[:10])
                print('    %-14s %-9s %s  %s%s' % (f.bone_name(c.bone) or c.bone, c.name(), 'XYZW'[c.component], ks,
                                                  ' ...' if len(c.keys) > 10 else ''))
        if f.skeleton:
            print('  skeleton:', [b.name for b in f.skeleton.bones])


def main():
    if len(sys.argv) < 3 or sys.argv[1] != 'dump':
        sys.exit(__doc__)
    f = load(sys.argv[2])
    summary(sys.argv[2], f)
    if len(sys.argv) > 3:
        d = f.to_dict(vertices=True) if isinstance(f, Emo) else f.to_dict()
        json.dump(d, open(sys.argv[3], 'w'), indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))


if __name__ == '__main__':
    main()
