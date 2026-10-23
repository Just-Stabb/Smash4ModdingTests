#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 effect files: EEPK (effect index), EMP (particles), ETR (traces),
EMM (materials), plus a note of the light EMAs. Readers return plain dicts / lists.

  python3 tools/xv2vfx.py dump DIR OUTDIR      the package in DIR (its .eepk and every container /
                                               asset it names) as one JSON per file + summary.txt
  python3 tools/xv2vfx.py check DIR            parse everything, assert sane values, byte coverage,
                                               and that corrupted copies are rejected
  python3 tools/xv2vfx.py show FILE            one .eepk / .emp / .etr / .emm / .ema as JSON

Python API:
  read_eepk(data) / read_emp(data) / read_etr(data) / read_emm(data) / read_ema(data) -> dict
  load_package(DIR) -> dict: eepk, the containers (pbind / tbind EMB -> parsed EMP / ETR by name,
                      their EMM materials and EMB texture names), lights, cross references resolved
  emp_nodes(emp) -> [(depth, node)]  the node tree flattened, depth first

Format: docs/xv2-vfx-format.md. A faithful port of the binary readers of LazyBone152's XV2-Tools
(Xv2CoreLib/EMP_NEW/Parser.cs + "EMP File.cs", ETR/ETR_File.cs, EEPK/EEPK_File.cs, EMM/Parser.cs,
Animation/EMA/EMA_File.cs header); field names are the C# names. Little-endian throughout.
Every reader tracks the bytes it consumed: a byte no field covers must be zero padding, else the
reader raises FormatError (as it does for unknown node / emitter / emission / scroll types,
(parameter, component) pairs it has no name for, flags outside 0/1, offsets out of range).
Units: EMP node times (Lifetime, StartTime, BurstFrequency) are frames (60 / s); EMP keyframe
times are percent of the particle's life (0..100; XV2-Tools divides by 100); ETR keyframe times
are frames; EEPK StartTime is frames; rotations: EEPK / ETR stored in radians (shown in degrees,
as XV2-Tools does), EMP node rotations are degrees; sizes are XV2 world units (1.0 ~ 1 m).
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
from xv2emb import Emb, dds_info  # noqa: E402


class FormatError(Exception):
    pass


def _f(x):
    """a float32 as a short Python float (7 significant digits)"""
    if math.isnan(x) or math.isinf(x):
        return x
    return float('%.7g' % x)


class Bin:
    """bounds-checked little-endian reads that record which bytes were consumed"""

    def __init__(self, data, what):
        self.d = bytes(data)
        self.what = what
        self.seen = bytearray(len(self.d))

    def err(self, msg):
        raise FormatError('%s: %s' % (self.what, msg))

    def _get(self, fmt, o):
        n = struct.calcsize('<' + fmt)
        if o < 0 or o + n > len(self.d):
            self.err('read of %d bytes at 0x%X past the end (0x%X)' % (n, o, len(self.d)))
        self.seen[o:o + n] = b'\1' * n
        return struct.unpack_from('<' + fmt, self.d, o)

    def u8(self, o):
        return self._get('B', o)[0]

    def u16(self, o):
        return self._get('H', o)[0]

    def i16(self, o):
        return self._get('h', o)[0]

    def u32(self, o):
        return self._get('I', o)[0]

    def i32(self, o):
        return self._get('i', o)[0]

    def f32(self, o):
        return _f(self._get('f', o)[0])

    def f32s(self, o, n):
        return [_f(v) for v in self._get('%df' % n, o)]

    def raw(self, o, n):
        return self._get('%ds' % n, o)[0]

    def fixed_str(self, o, n):
        """a fixed-size ASCII field (StringEx.GetString with maxSize)"""
        return self.raw(o, n).split(b'\0')[0].decode('ascii')

    def cstr(self, o):
        """a NUL-terminated ASCII string (StringEx.ReadStringASCII), terminator consumed"""
        if not 0 <= o < len(self.d):
            self.err('string offset 0x%X out of range' % o)
        end = self.d.find(b'\0', o)
        if end < 0:
            self.err('unterminated string at 0x%X' % o)
        self.seen[o:end + 1] = b'\1' * (end + 1 - o)
        return self.d[o:end].decode('ascii')

    def zero(self, o, n, what):
        """bytes the C# writer always leaves 0 (not read by the C# reader)"""
        b = self.raw(o, n)
        if any(b):
            self.err('%s at 0x%X expected zero, found %s' % (what, o, b.hex()))

    def bool8(self, o, what):
        v = self.u8(o)
        if v > 1:
            self.err('%s at 0x%X: boolean byte %d' % (what, o, v))
        return bool(v)

    def coverage(self, strict=True):
        """{size, consumed, zero_padding, unconsumed: [[start, end, hex]]}; strict: raise on
        non-zero unconsumed bytes"""
        gaps, i, n = [], 0, len(self.d)
        while i < n:
            if self.seen[i]:
                i += 1
                continue
            j = i
            while j < n and not self.seen[j]:
                j += 1
            gaps.append((i, j))
            i = j
        zero = [[a, b] for a, b in gaps if not any(self.d[a:b])]
        bad = [[a, b, self.d[a:b][:64].hex()] for a, b in gaps if any(self.d[a:b])]
        if strict and bad:
            self.err('unconsumed non-zero bytes: ' +
                     ', '.join('0x%X-0x%X (%s)' % (a, b, h[:32]) for a, b, h in bad[:8]))
        return {'size': n, 'consumed': sum(self.seen), 'zero_padding': sum(b - a for a, b in zero),
                'zero_gaps': zero, 'unconsumed': bad}


def _flags(v, table):
    names = [name for bit, name in table.items() if v & bit]
    rest = v & ~sum(table)
    if rest:
        names.append('0x%X' % rest)
    return names


def _enum(v, table, what, r):
    if v not in table:
        r.err('unknown %s %d' % (what, v))
    return table[v]


def _int4(b):
    """Int4Converter.ToInt4: (low nibble, high nibble)"""
    return b & 0xF, b >> 4


# ---------------------------------------------------------------------------------------------
# EMM (materials): EMM/Parser.cs
# ---------------------------------------------------------------------------------------------
EMM_PARAM_TYPES = {0: 'Float', 65537: 'Int', 65536: 'Float2', 1: 'Bool'}


def read_emm(data, strict=True):
    """+0 "#EMM", +4 u16 0xFFFE, +6 u16 header size, +8 i32 Version, +12 i32 offset of the
    material count (= header size: 16, or 32 with Unknown_Data), +16 i32 Unknown_Data offset (32-byte
    header); then i32 count, count x i32 material offsets (relative to the header size; 0 = null).
    Material: 32s Name, 32s ShaderProgram, +64 i16 parameter count, +66 u16 I_66, +68 parameters
    of 40 bytes: 32s Name, i32 Type (0 Float, 1 Bool, 65536 Float2, 65537 Int), 4-byte value."""
    r = Bin(data, 'EMM')
    if r.raw(0, 4) != b'#EMM':
        r.err('no #EMM signature')
    out = {'Endian': r.u16(4), 'HeaderSize_06': r.u16(6), 'Version': r.i32(8)}
    count_off = r.i32(12)
    header = count_off & 0xFFFF            # BitConverter.ToInt16(rawBytes, 12)
    if header not in (16, 32):
        r.err('header size %d' % header)
    unk_off = r.i32(16) if header == 32 else 0
    if header == 32:
        r.zero(20, 12, 'header padding')
    count = r.i32(count_off)
    mats = []
    for i in range(count):
        mo = r.i32(count_off + 4 + 4 * i)
        if mo == 0:
            mats.append(None)
            continue
        o = mo + header
        m = {'Index': i, '_offset': o, 'Name': r.fixed_str(o, 32), 'ShaderProgram': r.fixed_str(o + 32, 32),
             'I_66': r.u16(o + 66), 'Parameters': []}
        n = r.i16(o + 64)
        for k in range(n):
            po = o + 68 + 40 * k
            t = r.i32(po + 32)
            if t not in EMM_PARAM_TYPES:
                r.err('material %s parameter %d: unknown type %d' % (m['Name'], k, t))
            tn = EMM_PARAM_TYPES[t]
            if tn in ('Float', 'Float2'):
                val = r.f32(po + 36)
            elif tn == 'Bool':
                val = r.i32(po + 36)
                val = bool(val) if val in (0, 1) else val
            else:
                val = r.i32(po + 36)
            m['Parameters'].append({'Name': r.fixed_str(po, 32), 'Type': tn, 'Value': val})
        mats.append(m)
    out['Materials'] = mats
    if unk_off and len(r.d) - unk_off == 68:
        out['Unknown_Data'] = {'I_%02d' % (4 * k): r.i32(unk_off + 4 * k) for k in range(17)}
    elif unk_off:
        r.err('Unknown_Data at 0x%X is %d bytes, expected 68' % (unk_off, len(r.d) - unk_off))
    out['_coverage'] = r.coverage(strict)
    return out


def emm_params(mat):
    """{name: value} of a material"""
    return {p['Name']: p['Value'] for p in mat['Parameters']} if mat else {}


# ---------------------------------------------------------------------------------------------
# EMP / ETR texture samplers: EMP_TextureSamplerDef.Read
# ---------------------------------------------------------------------------------------------
EMP_VERSIONS = {37568: 'DBXV2', 37632: 'SDBH'}
TEX_REPETITION = {0: 'Wrap', 1: 'Mirror', 2: 'Clamp', 3: 'Border'}
TEX_FILTERING = {0: 'None', 1: 'Point', 2: 'Linear'}
TEX_KEYFRAME_TYPE = {0: 'Sequential', 1: 'SequentialLoop', 2: 'Random', 3: 'Unk3'}
TEX_SYMMETRY = {0: 'Default', 1: 'Inverted', 2: 'Random'}
SCROLL_TYPES = {0: 'Static', 1: 'Speed', 2: 'SpriteSheet'}


def _sampler_size(version):
    return 36 if version == 'SDBH' else 28


def _read_sampler(r, base, i, version):
    """28 bytes (36 SDBH): u8 I_00, u8 EmbIndex (texture in the .emb; 255 = none), u8 KeyframeType
    (low nibble) | I_02_b, u8 I_03_a | I_03_b, u8 FilteringMin, FilteringMag, RepetitionU,
    RepetitionV, SymmetryU, SymmetryV, u16 ScrollType, then by ScrollType:
      Static: f32 ScrollU, ScrollV, ScaleU, ScaleV       (UV offset / repeat, constant)
      Speed: f32 ScrollSpeed_U, ScrollSpeed_V, 8 x 0      (UV units per frame)
      SpriteSheet: 10 x 0, i16 keyframe count, i32 offset (relative to +12) of 20-byte keyframes
                   (i32 Time in frames, f32 ScrollU, ScrollV, ScaleU, ScaleV)"""
    o = base + i * _sampler_size(version)
    b2, b3 = r.u8(o + 2), r.u8(o + 3)
    s = {'Index': i, 'I_00': r.u8(o), 'EmbIndex': r.u8(o + 1),
         'KeyframeType': _enum(_int4(b2)[0], TEX_KEYFRAME_TYPE, 'sampler KeyframeType', r),
         'I_02_b': _int4(b2)[1], 'I_03_a': _int4(b3)[0], 'I_03_b': _int4(b3)[1],
         'FilteringMin': _enum(r.u8(o + 4), TEX_FILTERING, 'FilteringMin', r),
         'FilteringMag': _enum(r.u8(o + 5), TEX_FILTERING, 'FilteringMag', r),
         'RepetitionU': _enum(r.u8(o + 6), TEX_REPETITION, 'RepetitionU', r),
         'RepetitionV': _enum(r.u8(o + 7), TEX_REPETITION, 'RepetitionV', r),
         'SymmetryU': _enum(r.u8(o + 8), TEX_SYMMETRY, 'SymmetryU', r),
         'SymmetryV': _enum(r.u8(o + 9), TEX_SYMMETRY, 'SymmetryV', r)}
    st = _enum(r.i16(o + 10), SCROLL_TYPES, 'ScrollType', r)
    sd = version == 'SDBH'
    scroll = {'ScrollType': st}
    if st == 'Static':
        k = dict(zip(('ScrollU', 'ScrollV', 'ScaleU', 'ScaleV'), r.f32s(o + 12, 4)))
        k['Time'] = 100
        if sd:
            k['I_20'], k['I_24'] = r.i32(o + 28), r.i32(o + 32)
        scroll['Keyframes'] = [k]
    elif st == 'Speed':
        scroll['ScrollSpeed_U'], scroll['ScrollSpeed_V'] = r.f32s(o + 12, 2)
        r.zero(o + 20, 16 if sd else 8, 'Speed scroll padding')
    else:
        r.zero(o + 12, 10, 'SpriteSheet padding')
        n = r.i16(o + 22)
        ko = r.i32(o + 24) + o + 12
        if sd:
            r.zero(o + 28, 8, 'SpriteSheet padding')
        ks = []
        for j in range(n):
            k = {'Time': r.i32(ko)}
            k.update(zip(('ScrollU', 'ScrollV', 'ScaleU', 'ScaleV'), r.f32s(ko + 4, 4)))
            if sd:
                k['I_20'], k['I_24'] = r.i32(ko + 20), r.i32(ko + 24)
            ks.append(k)
            ko += 28 if sd else 20
        scroll['Keyframes'] = ks
    s['ScrollState'] = scroll
    return s


def _texture_refs(r, list_off, count, owner_off, samplers_off, samplers, version, what):
    """a list of u32 sampler pointers (relative to owner_off) -> sampler indices (None = empty)"""
    refs = []
    size = _sampler_size(version)
    for e in range(count):
        p = r.i32(list_off + 4 * e)
        if p == 0:
            refs.append(None)
            continue
        rel = p + owner_off - samplers_off
        if rel % size or not 0 <= rel // size < len(samplers):
            r.err('%s: texture pointer 0x%X does not hit a sampler' % (what, p))
        refs.append(rel // size)
    return refs


# ---------------------------------------------------------------------------------------------
# EMP: EMP_NEW/Parser.cs, "EMP File.cs"
# ---------------------------------------------------------------------------------------------
EMP_NODE_TYPES = {0: 'Null', 1: 'Emitter', 2: 'Emission'}
EMP_BILLBOARD = {0: 'Camera', 1: 'Front', 2: 'None'}
EMP_NODE_FLAGS1 = {0x1: 'Unk1', 0x2: 'Loop', 0x4: 'Unk3', 0x8: 'FlashOnGen', 0x10: 'Unk5', 0x20: 'Unk6',
                   0x40: 'Unk7', 0x80: 'Unk8', 0x100: 'Unk9', 0x200: 'Unk10', 0x400: 'Unk11',
                   0x800: 'Hide', 0x1000: 'EnableScaleXY', 0x2000: 'Unk14',
                   0x4000: 'EnableSecondaryColor', 0x8000: 'Unk16'}
EMP_NODE_FLAGS2 = {0x1: 'Unk1', 0x2: 'Unk2', 0x4: 'Unk3', 0x8: 'Unk4', 0x10: 'RandomRotationDir',
                   0x20: 'Unk6', 0x40: 'RandomUpVector', 0x80: 'Unk8'}
# emitter type byte (+36) -> ParticleEmitterShape / NodeSpecificType (C# names, as is)
EMP_EMITTER_TYPES = {0: ('Point', 'VerticalDistribution'), 1: ('Sphere', 'SphericalDistribution'),
                     2: (None, 'ShapePerimeterDistribution'), 3: (None, 'ShapeAreaDistribution')}
# emission type byte (+36) -> (ParticleEmissionType, NodeSpecificType)
EMP_EMISSION_TYPES = {0: ('Plane', 'AutoOriented'), 1: ('Plane', 'AutoOriented_VisibleOnSpeed'),
                      2: ('Plane', 'Default'), 3: ('ConeExtrude', 'ConeExtrude'), 4: ('Mesh', 'Mesh'),
                      5: ('ShapeDraw', 'ShapeDraw')}
EMP_MODIFIER_TYPES = {4: 'Translation', 5: 'Acceleration', 6: 'AngleTranslation', 7: 'AngleAcceleration',
                      8: 'PointLoop', 9: 'Vortex', 10: 'Jitter', 11: 'Drag', 12: 'Attract'}
ETR_MODIFIER_TYPES = {2: 'Translation', 3: 'Acceleration', 4: 'InverseTranslation',
                      5: 'InverseAcceleration', 7: 'Unk7'}
MODIFIER_FLAGS = {0x1: 'Unk1', 0x2: 'Unk2'}
XYZ, RGBA = 'XYZ', 'RGBA'


def _emp_target(node, param, comp):
    """the KeyframedValueType a node keyframed value (Parameter, Component) animates, as
    "Name[.component]" (EMP File.cs KeyframedValueType comments / Parser.cs decompile)"""
    if param == 0 and comp < 3:
        return 'Position.' + XYZ[comp]
    if param == 1 and comp < 3:
        return 'Rotation.' + XYZ[comp]
    st = node['NodeSpecificType']
    if node['NodeType'] == 'Emission':
        if param == 1 and comp == 3 and st in ('AutoOriented', 'Default', 'Mesh', 'ShapeDraw'):
            return 'ActiveRotation'
        if param == 2:
            if 'EnableScaleXY' in node['NodeFlags_names']:
                return {0: 'ScaleXY.X', 1: 'ScaleXY.Y', 2: 'ScaleBase'}.get(comp)
            return {0: 'ScaleBase'}.get(comp)
        if param in (3, 4) and comp < 4:
            col = 'Color1' if param == 3 else 'Color2'
            return col + '_Transparency' if comp == 3 else col + '.' + 'RGB'[comp]
    elif node['NodeType'] == 'Emitter':
        if st == 'SphericalDistribution':
            if param == 2:
                return {0: 'Size', 1: 'Velocity'}.get(comp)
        else:
            if param == 2:
                return {0: 'Position', 1: 'Velocity', 2: 'Angle'}.get(comp)
            if param == 3 and st in ('ShapePerimeterDistribution', 'ShapeAreaDistribution'):
                return {0: 'Size', 1: 'Size2'}.get(comp)
    return None


def _modifier_target(typ, param, comp):
    """EMP_Modifier.DecompileEmp / DecompileEtr parameter names"""
    if typ in ('Translation', 'Acceleration', 'AngleTranslation', 'AngleAcceleration', 'PointLoop', 'Jitter',
               'Attract', 'InverseTranslation', 'InverseAcceleration', 'ETR:Translation', 'ETR:Acceleration'):
        if param == 0 and comp < 3:
            return 'Axis.' + XYZ[comp]
        if param == 1 and comp == 0:
            return 'Factor'
    elif typ == 'Vortex':
        if param == 0 and comp < 3:
            return 'Axis.' + XYZ[comp]
        if param == 1 and comp < 3:
            return 'Direction.' + XYZ[comp]
        if param == 2:
            return {0: 'Radial', 1: 'RotationRate'}.get(comp)
    elif typ == 'Drag':
        if param == 0 and comp == 0:
            return 'DragStrength'
    elif typ == 'Unk7':
        if param == 1 and comp < 3:
            return 'Axis2.' + XYZ[comp]
        if param == 2:
            return {0: 'Unk7_20', 1: 'Unk7_21'}.get(comp)
    return None


def _emp_keyframed_value(r, o, what):
    """16 bytes: u8 Parameter, u8 Component (low nibble) | Interpolate (high nibble), u8 Loop,
    u8 I_03, f32 DefaultValue (used by modifiers), u16 Duration, i16 keyframe count, i32 offset
    (relative to this entry) of: count x u16 Time, pad to 4, count x f32 Value, then (count > 1)
    a frame -> keyframe index table of Time[-1] + 1 u16 entries, pad to 4"""
    comp, interp = _int4(r.u8(o + 1))
    if interp > 1:
        r.err('%s: Interpolate nibble %d' % (what, interp))
    kv = {'Parameter': r.u8(o), 'Component': comp, 'Interpolate': bool(interp),
          'Loop': r.bool8(o + 2, what + ' Loop'), 'I_03': r.u8(o + 3), 'DefaultValue': r.f32(o + 4),
          'Duration': r.u16(o + 8)}
    n = r.i16(o + 10)
    ko = r.i32(o + 12) + o
    times = [r.u16(ko + 2 * i) for i in range(n)]
    if n % 2:
        r.zero(ko + 2 * n, 2, what + ' time padding')
    vo = ko + 2 * (n + n % 2)
    vals = r.f32s(vo, n)
    kv['Keyframes'] = [{'Time': t, 'Value': v} for t, v in zip(times, vals)]
    io = vo + 4 * n
    if n > 1:
        # the writer's index list: keyframe s repeated (Time[s+1] - Time[s]) times (the first
        # also covers 0..Time[0]), the last once
        exp = []
        for s in range(n):
            if s == n - 1:
                ln = 1
            elif s == 0 and times[0] != 0:
                ln = times[1]
            else:
                ln = times[s + 1] - times[s]
            exp += [s] * max(ln, 0)
        got = [r.u16(io + 2 * i) for i in range(len(exp))]
        if got != exp:
            r.err('%s: keyframe index table differs from the times (%s... vs %s...)' % (what, got[:8], exp[:8]))
        if len(exp) % 2:
            r.zero(io + 2 * len(exp), 2, what + ' index padding')
        kv['_index_table_len'] = len(exp)
    return kv


def _emp_modifiers(r, o, count, what, etr=False):
    """count x 8 bytes: u8 Type, u8 Flags, u16 keyframed value count, i32 offset (relative to this
    entry) of the keyframed values"""
    mods = []
    for a in range(count):
        mo = o + 8 * a
        t = r.u8(mo)
        types = ETR_MODIFIER_TYPES if etr else EMP_MODIFIER_TYPES
        tn = _enum(t, types, '%s modifier type' % what, r)
        flags = r.u8(mo + 1)
        n = r.u16(mo + 2)
        ko = r.i32(mo + 4) + mo
        m = {'Type': t, 'TypeStr': tn, 'Flags': flags, 'Flags_names': _flags(flags, MODIFIER_FLAGS),
             'KeyframedValues': []}
        for d in range(n):
            w = '%s modifier %d value %d' % (what, a, d)
            kv = (_etr_keyframed_value(r, ko + 16 * d, w) if etr else _emp_keyframed_value(r, ko + 16 * d, w))
            tgt = _modifier_target(tn, kv['Parameter'], kv['Component'])
            if tgt is None:
                r.err('%s: no name for modifier %s (Parameter %d, Component %d)' % (w, tn, kv['Parameter'], kv['Component']))
            kv['Target'] = tgt
            m['KeyframedValues'].append(kv)
        mods.append(m)
    return mods


def _emp_vec(r, o, what, node):
    """an XYZ + W vector; W is written as 0"""
    v = r.f32s(o, 3)
    w = r.f32(o + 12)
    if w:
        node.setdefault('_W', {})[what] = w
    return v


def _emp_emitter(r, o, typ, node):
    """ParticleEmitter.Parse: data at node + 160.
      0 Point ("cone"): f32 Position, _Variance, Velocity, _Variance, Angle, _Variance, F_1, F_2 (32 B)
      1 Sphere: f32 Size, _Variance, Velocity, _Variance                                  (16 B)
      2 / 3 Circle or Square (EmitFromArea = type 2): f32 Position, _Variance, Velocity, _Variance,
        Angle, _Variance, Size, _Variance, Size2, _Variance, i32 Shape (0 Circle 1 Square),
        f32 EdgeIncrement                                                                (48 B)
    Position: offset along the up vector; Velocity: along the up vector; Angle: cone half-angle
    (degrees) the particles leave at; Size: radius (Square: width), Size2: Square depth."""
    o += 160
    e = {}
    if typ == 0:
        e['Shape'] = 'Point'
        (e['Position'], e['Position_Variance'], e['Velocity'], e['Velocity_Variance'], e['Angle'],
         e['Angle_Variance'], e['F_1'], e['F_2']) = r.f32s(o, 8)
    elif typ == 1:
        e['Shape'] = 'Sphere'
        e['Size'], e['Size_Variance'], e['Velocity'], e['Velocity_Variance'] = r.f32s(o, 4)
    else:
        shape = r.i32(o + 40)
        if shape not in (0, 1):
            r.err('ParticleEmitter.Parse: invalid Shape %d on Square/Circle type' % shape)
        e['Shape'] = ('Circle', 'Square')[shape]
        e['EmitFromArea'] = typ == 2
        (e['Position'], e['Position_Variance'], e['Velocity'], e['Velocity_Variance'], e['Angle'],
         e['Angle_Variance'], e['Size'], e['Size_Variance'], e['Size2'], e['Size2_Variance']) = r.f32s(o, 10)
        e['EdgeIncrement'] = r.f32(o + 44)
    return e


def _emp_texture(r, o, node_off, ctx):
    """ParticleTexture.Parse: 112 bytes at node + 160:
      +0 u8 I_00..I_03, +4 f32 RenderDepth, +8 i32 I_08, +12 i32 I_12, +16 u16 MaterialID (EMM
      material in the container's .emm; 0xFFFF none), +18 i16 texture count, +20 i32 offset
      (relative to the node) of the texture pointer list, +24 f32 ScaleBase, ScaleBase_Variance,
      +32 ScaleXY.X, ScaleXY_Variance.X, ScaleXY.Y, ScaleXY_Variance.Y, +48 f32 Color1 R G B,
      Color1_Transparency (alpha), +64 Color_Variance R G B A, +80 Color2 R G B,
      Color2_Transparency, +96 F_96, F_100, F_104, F_108"""
    t = {'I_00': r.u8(o), 'I_01': r.u8(o + 1), 'I_02': r.u8(o + 2), 'I_03': r.u8(o + 3),
         'RenderDepth': r.f32(o + 4), 'I_08': r.i32(o + 8), 'I_12': r.i32(o + 12), 'MaterialID': r.u16(o + 16)}
    n = r.i16(o + 18)
    lo = r.i32(o + 20) + node_off
    t['ScaleBase'], t['ScaleBase_Variance'] = r.f32s(o + 24, 2)
    sx, svx, sy, svy = r.f32s(o + 32, 4)
    t['ScaleXY'], t['ScaleXY_Variance'] = [sx, sy], [svx, svy]
    t['Color1'] = r.f32s(o + 48, 3)
    t['Color1_Transparency'] = r.f32(o + 60)
    t['Color_Variance'] = r.f32s(o + 64, 4)
    t['Color2'] = r.f32s(o + 80, 3)
    t['Color2_Transparency'] = r.f32(o + 92)
    t['F_96'], t['F_100'], t['F_104'], t['F_108'] = r.f32s(o + 96, 4)
    t['TextureEntryRef'] = []
    if lo != node_off:
        t['TextureEntryRef'] = _texture_refs(r, lo, n, node_off, ctx['samplers_off'], ctx['samplers'],
                                             ctx['version'], 'node at 0x%X' % node_off)
    return t


def _emp_emission(r, o, typ, node, ctx):
    """ParticleEmission.Parse: ParticleTexture (112 B) at node + 160, then by type at node + 272:
      0 AutoOriented (billboard = node +35): f32 StartRotation, _Variance, ActiveRotation, _Variance
      1 AutoOriented_VisibleOnSpeed (velocity oriented): nothing
      2 Default (no billboard): f32 StartRotation, _Variance, ActiveRotation, _Variance,
        RotationAxis X Y Z, 0
      3 ConeExtrude: u16 Duration, Duration_Variance, StepDuration, point count - 1, I_08, I_10,
        i32 offset (relative to the node) of 16-byte points (f32 WorldScaleFactor, WorldScaleAdd,
        WorldOffsetFactor, WorldOffsetFactor2)
      4 Mesh: f32 StartRotation, _Variance, ActiveRotation, _Variance, RotationAxis XYZ, 0,
        i32 I_32, i32 EMG offset (relative to the node), I_40, I_44 (+ an embedded EMG)
      5 ShapeDraw: f32 StartRotation, _Variance, ActiveRotation, _Variance, u16 point count - 1,
        u16 BillboardType, i32 offset (relative to the node) of 8-byte points (f32 X, Y),
        u16 I_24 I_26 I_28 I_30
    StartRotation degrees; ActiveRotation degrees per second (XV2-Tools)."""
    em = {}
    em['EmissionType'], _ = EMP_EMISSION_TYPES[typ]
    em['BillboardType'] = _enum(r.u8(node + 35), EMP_BILLBOARD, 'BillboardType', r)
    em['Texture'] = _emp_texture(r, node + 160, node, ctx)
    o = node + 160 + 112
    if typ in (0, 2, 4, 5):
        em['StartRotation'], em['StartRotation_Variance'], ar, em['ActiveRotation_Variance'] = r.f32s(o, 4)
        em['ActiveRotation'] = ar
    if typ == 1:
        em['VelocityOriented'] = True
    elif typ == 0:
        em['VelocityOriented'] = False
    if typ in (2, 4):
        em['BillboardType'] = 'None'
        em['RotationAxis'] = r.f32s(o + 16, 3)
        w = r.f32(o + 28)
        if w:
            em['RotationAxis_W'] = w
    if typ == 3:
        em['BillboardType'] = 'None'
        c = {'Duration': r.u16(o), 'Duration_Variance': r.u16(o + 2), 'StepDuration': r.u16(o + 4),
             'I_08': r.u16(o + 8), 'I_10': r.u16(o + 10)}
        cnt = r.i16(o + 6) + 1
        lo = r.i32(o + 12) + node
        c['Points'] = [dict(zip(('WorldScaleFactor', 'WorldScaleAdd', 'WorldOffsetFactor', 'WorldOffsetFactor2'),
                                r.f32s(lo + 16 * i, 4))) for i in range(cnt)]
        em['ConeExtrude'] = c
    elif typ == 4:
        em['BillboardType'] = 'None'
        em['Mesh'] = {'I_32': r.i32(o + 32), 'I_40': r.i32(o + 40), 'I_44': r.i32(o + 44)}
        eo = r.i32(o + 36) + node
        if r.d[eo:eo + 4] == b'#EMG':
            r.err('Mesh emission with an embedded EMG at 0x%X: EMG reading is not ported' % eo)
    elif typ == 5:
        cnt = r.i16(o + 16) + 1
        em['BillboardType'] = _enum(r.u16(o + 18), EMP_BILLBOARD, 'ShapeDraw BillboardType', r)
        lo = r.i32(o + 20) + node
        em['ShapeDraw'] = {'I_24': r.u16(o + 24), 'I_26': r.u16(o + 26), 'I_28': r.u16(o + 28),
                           'I_30': r.u16(o + 30),
                           'Points': [dict(zip('XY', r.f32s(lo + 8 * i, 2))) for i in range(cnt)]}
    return em


def _emp_node(r, o, ctx):
    """ParticleNode, 160 bytes:
      +0 32s Name, +32 u16 NodeFlags, +34 u8 NodeFlags2, +35 u8 BillboardType, +36 u8 emitter /
      emission type, +37 u8 NodeType (0 Null, 1 Emitter, 2 Emission), +38 i16 MaxInstances,
      +40 u16 Lifetime, Lifetime_Variance, +44 u8 StartTime, StartTime_Variance, BurstFrequency,
      BurstFrequency_Variance, +48 u16 I_48, I_50, Burst, Burst_Variance, I_56, I_58, I_60, I_62,
      +64 f32 Position XYZ (W 0), +80 Position_Variance, +96 Rotation, +112 Rotation_Variance,
      +128 u16 I_128, I_130, +132 f32 F_132, +136 u16 I_136 (0 Null / ConeExtrude / ShapeDraw,
      1 emitters, 2 other emissions), +138 u16 keyframed value count, +140 i32 their offset
      (relative to node + 136), +144 u16 modifier count, +146 u16 child count, +148 i32 modifier
      offset (relative to the node), +152 i32 next sibling (relative), +156 i32 first child"""
    sec, typ = r.u8(o + 36), r.u8(o + 37)
    flags, flags2 = r.u16(o + 32), r.u8(o + 34)
    n = {'_offset': o, 'Name': r.fixed_str(o, 32),
         'NodeType': _enum(typ, EMP_NODE_TYPES, 'NodeType', r),
         'NodeFlags': flags, 'NodeFlags_names': _flags(flags, EMP_NODE_FLAGS1),
         'NodeFlags2': flags2, 'NodeFlags2_names': _flags(flags2, EMP_NODE_FLAGS2),
         'MaxInstances': r.i16(o + 38), 'Lifetime': r.u16(o + 40), 'Lifetime_Variance': r.u16(o + 42),
         'StartTime': r.u8(o + 44), 'StartTime_Variance': r.u8(o + 45),
         'BurstFrequency': r.u8(o + 46), 'BurstFrequency_Variance': r.u8(o + 47),
         'I_48': r.u16(o + 48), 'I_50': r.u16(o + 50), 'Burst': r.u16(o + 52), 'Burst_Variance': r.u16(o + 54),
         'I_56': r.u16(o + 56), 'I_58': r.u16(o + 58), 'I_60': r.u16(o + 60), 'I_62': r.u16(o + 62)}
    n['Position'] = _emp_vec(r, o + 64, 'Position', n)
    n['Position_Variance'] = _emp_vec(r, o + 80, 'Position_Variance', n)
    n['Rotation'] = _emp_vec(r, o + 96, 'Rotation', n)
    n['Rotation_Variance'] = _emp_vec(r, o + 112, 'Rotation_Variance', n)
    n['I_128'], n['I_130'], n['F_132'] = r.u16(o + 128), r.u16(o + 130), r.f32(o + 132)
    i136 = r.u16(o + 136)
    kv_n, kv_o = r.u16(o + 138), r.i32(o + 140) + 136 + o
    md_n, ch_n, md_o = r.u16(o + 144), r.u16(o + 146), r.i32(o + 148) + o
    nxt, child = r.i32(o + 152), r.i32(o + 156)
    if typ == 0:
        if sec != 0:
            r.err('Null node %r with type byte %d' % (n['Name'], sec))
        n['NodeSpecificType'] = 'Null'
        if r.u8(o + 35) not in EMP_BILLBOARD:
            r.err('BillboardType %d' % r.u8(o + 35))
    elif typ == 1:
        if sec not in EMP_EMITTER_TYPES:
            r.err('EmitterType %d is not recognized' % sec)
        n['NodeSpecificType'] = EMP_EMITTER_TYPES[sec][1]
        n['EmitterNode'] = _emp_emitter(r, o, sec, n)
        _enum(r.u8(o + 35), EMP_BILLBOARD, 'BillboardType', r)
    else:
        if sec not in EMP_EMISSION_TYPES:
            r.err('EmissionType %d is not recognized' % sec)
        n['NodeSpecificType'] = EMP_EMISSION_TYPES[sec][1]
        n['EmissionNode'] = _emp_emission(r, o, sec, o, ctx)
    exp136 = 0 if n['NodeSpecificType'] in ('Null', 'ConeExtrude', 'ShapeDraw') else 1 if typ == 1 else 2
    n['I_136'] = i136
    if i136 != exp136:
        ctx['notes'].append('%s: I_136 = %d (writer would put %d)' % (n['Name'], i136, exp136))
    n['KeyframedValues'] = []
    for a in range(kv_n):
        w = 'node %r keyframed value %d' % (n['Name'], a)
        kv = _emp_keyframed_value(r, kv_o + 16 * a, w)
        tgt = _emp_target(n, kv['Parameter'], kv['Component'])
        if tgt is None:
            r.err('%s: no name for (Parameter %d, Component %d) on a %s node' % (w, kv['Parameter'], kv['Component'],
                                                                           n['NodeSpecificType']))
        kv['Target'] = tgt
        n['KeyframedValues'].append(kv)
    n['Modifiers'] = _emp_modifiers(r, md_o, md_n, 'node %r' % n['Name']) if md_n else []
    n['_child_count'] = ch_n
    return n, nxt, child


def _emp_nodes(r, o, ctx, depth=0):
    """ParseNodes: a sibling chain (next offsets relative to the current node) with children"""
    out = []
    while True:
        if o in ctx['visited']:
            r.err('node chain loops at 0x%X' % o)
        ctx['visited'].add(o)
        if depth > 32:
            r.err('node tree deeper than 32')
        node, nxt, child = _emp_node(r, o, ctx)
        node['ChildParticleNodes'] = _emp_nodes(r, o + child, ctx, depth + 1) if child > 0 else []
        if len(node['ChildParticleNodes']) != node.pop('_child_count'):
            r.err('node %r: child count field differs from its chain' % node['Name'])
        out.append(node)
        if nxt == 0:
            return out
        o += nxt


def read_emp(data, strict=True):
    """EMP header (32 bytes): +0 "#EMP", +4 u16 0xFFFE, +6 u16 24, +8 u16 Version (37568 DBXV2,
    37632 SDBH), +10 u16 0, +12 i16 root node count, +14 i16 texture sampler count, +16 i32 node
    offset (32), +20 i32 texture sampler offset, +24 8 x 0. Returns {Version, Textures (samplers),
    ParticleNodes (tree)}."""
    r = Bin(data, 'EMP')
    if r.raw(0, 4) != b'#EMP':
        r.err('#EMP file signature not found')
    ver = r.u16(8)
    out = {'Endian': r.u16(4), 'HeaderSize': r.u16(6), 'Version': ver,
           'VersionName': _enum(ver, EMP_VERSIONS, 'version', r)}
    r.zero(10, 2, 'header')
    roots, ntex = r.i16(12), r.i16(14)
    node_off, tex_off = r.i32(16), r.i32(20)
    r.zero(24, 8, 'header padding')
    vn = out['VersionName']
    out['Textures'] = [_read_sampler(r, tex_off, i, vn) for i in range(ntex)]
    ctx = {'samplers': out['Textures'], 'samplers_off': tex_off, 'version': vn, 'visited': set(), 'notes': []}
    out['ParticleNodes'] = _emp_nodes(r, node_off, ctx) if roots > 0 else []
    if len(out['ParticleNodes']) != roots:
        r.err('root node count %d, chain has %d' % (roots, len(out['ParticleNodes'])))
    out['_notes'] = ctx['notes']
    out['_coverage'] = r.coverage(strict)
    return out


def emp_nodes(emp):
    """[(depth, node)] depth first"""
    out = []

    def walk(ns, d):
        for n in ns:
            out.append((d, n))
            walk(n['ChildParticleNodes'], d + 1)
    walk(emp['ParticleNodes'], 0)
    return out


# ---------------------------------------------------------------------------------------------
# ETR: ETR/ETR_File.cs
# ---------------------------------------------------------------------------------------------
ETR_FLAGS = {0x1: 'AutoOrientation', 0x2: 'Unk2', 0x4: 'NoDegrade', 0x8: 'DoublePointOfMiddleSection',
             0x10: 'Unk5', 0x20: 'Unk6', 0x40: 'Unk7', 0x80: 'Unk8', 0x100: 'DisplayMiddleSection',
             0x200: 'UVPauseOnExtrude', 0x400: 'Unk11', 0x800: 'Unk12', 0x1000: 'Unk13', 0x2000: 'Unk14',
             0x4000: 'Unk15', 0x10000: 'UVPauseOnHold', 0x20000: 'Unk17', 0x40000: 'Unk18'}
ETR_INTERPOLATION = {0: 'DefaultEnd', 1: 'Default', 2: 'ShapeStartToEnd'}
ETR_DUMMY = 204     # bytes the writer appends after each keyframed value's floats


def _etr_target(param, comp):
    if param in (0, 1) and comp < 4:
        col = 'Color1' if param == 0 else 'Color2'
        return col + '_Transparency' if comp == 3 else col + '.' + 'RGB'[comp]
    if param == 2 and comp == 0:
        return 'Scale'
    return None


def _etr_keyframed_value(r, o, what):
    """16 bytes: u8 ETR_InterpolationType (0 DefaultEnd: during the hold, 1 Default: over the
    extrude, 2 ShapeStartToEnd: along the trail), u8 Parameter, u8 Component (low nibble) |
    Interpolate (high nibble), u8 I_03 (9), u16 0, u16 keyframe count, i32 times offset, i32
    values offset (both relative to this entry). Times: u16 frames, pad to 4; values f32; the
    writer then appends 204 dummy bytes."""
    comp, interp = _int4(r.u8(o + 2))
    if interp > 1:
        r.err('%s: Interpolate nibble %d' % (what, interp))
    kv = {'ETR_InterpolationType': _enum(r.u8(o), ETR_INTERPOLATION, what + ' ETR_InterpolationType', r),
          'Parameter': r.u8(o + 1), 'Component': comp, 'Interpolate': bool(interp), 'I_03': r.u8(o + 3),
          'I_04': r.u16(o + 4)}
    n = r.u16(o + 6)
    to, vo = r.i32(o + 8) + o, r.i32(o + 12) + o
    times = [r.u16(to + 2 * i) for i in range(n)]
    if n % 2:
        r.zero(to + 2 * n, 2, what + ' time padding')
    vals = r.f32s(vo, n)
    kv['Keyframes'] = [{'Time': t, 'Value': v} for t, v in zip(times, vals)]
    dummy = r.d[vo + 4 * n:vo + 4 * n + ETR_DUMMY]
    if len(dummy) == ETR_DUMMY:
        r.seen[vo + 4 * n:vo + 4 * n + ETR_DUMMY] = b'\1' * ETR_DUMMY
        if any(dummy):
            kv['_dummy_204'] = dummy.hex()
    return kv


def _etr_node(r, o, tex_off, samplers):
    """ETR_Node, 176 bytes:
      +0 32s AttachBone, +32 32s AttachBone2, +64 f32 Position XYZ, +76 f32 Rotation XYZ
      (radians), +88 u8 I_88, +89 u8 extrude path count - 1, +90 u16 StartTime (frames),
      +92 u8 I_92, +93 u8 SegementFrameSize (frames per segment), +94 i16 ExtrudeDuration (frames),
      +96 u32 Flags (ExtrudeFlags), +100 i32 I_100, +104 f32 PositionExtrudeZ, +108 u16 MaterialID,
      +110 u16 texture count, +112 i32 texture pointer list (relative to the node), +116 i32
      extrude paths (relative to the node; 16-byte ConeExtrudePoints, then the shape points),
      +120 f32 Color1 RGB, Color1_Transparency, +136 Color2 RGB, Color2_Transparency, +152 f32
      Scale (width), +156 i32 shape point count - 1 (0 = none), +160 u16 HoldDuration (frames),
      +162 u16 modifier count, +164 i32 modifiers (relative to node + 120), +168 u16 I_168,
      +170 u16 keyframed value count, +172 i32 keyframed values (relative to node + 168)"""
    n = {'_offset': o, 'AttachBone': r.fixed_str(o, 32), 'AttachBone2': r.fixed_str(o + 32, 32),
         'Position': r.f32s(o + 64, 3),
         'Rotation': [_f(math.degrees(v)) for v in r.f32s(o + 76, 3)],
         'I_88': r.u8(o + 88), 'StartTime': r.u16(o + 90), 'I_92': r.u8(o + 92),
         'SegementFrameSize': r.u8(o + 93), 'ExtrudeDuration': r.i16(o + 94)}
    fl = r.u32(o + 96)
    n['Flags'], n['Flags_names'] = fl, _flags(fl, ETR_FLAGS)
    n['I_100'], n['PositionExtrudeZ'], n['MaterialID'] = r.i32(o + 100), r.f32(o + 104), r.u16(o + 108)
    n['Color1'], n['Color1_Transparency'] = r.f32s(o + 120, 3), r.f32(o + 132)
    n['Color2'], n['Color2_Transparency'] = r.f32s(o + 136, 3), r.f32(o + 148)
    n['Scale'] = r.f32(o + 152)
    n['HoldDuration'], n['I_168'] = r.u16(o + 160), r.u16(o + 168)
    tn, tl = r.u16(o + 110), r.i32(o + 112) + o
    n['TextureEntryRef'] = (_texture_refs(r, tl, tn, o, tex_off, samplers, 'DBXV2', 'ETR node at 0x%X' % o)
                            if tl != o else [])
    po = r.i32(o + 116) + o
    pc = r.u8(o + 89) + 1
    n['ExtrudePaths'] = [dict(zip(('WorldScaleFactor', 'WorldScaleAdd', 'WorldOffsetFactor', 'WorldOffsetFactor2'),
                                  r.f32s(po + 16 * i, 4))) for i in range(pc)]
    po += 16 * pc
    sp = r.i32(o + 156)
    n['ExtrudeShapePoints'] = [dict(zip('XY', r.f32s(po + 8 * i, 2))) for i in range(sp + 1 if sp > 0 else 0)]
    kn, ko = r.u16(o + 170), r.i32(o + 172) + 168 + o
    n['KeyframedValues'] = []
    for i in range(kn):
        w = 'ETR node %d keyframed value %d' % ((o - 24) // 176, i)
        kv = _etr_keyframed_value(r, ko + 16 * i, w)
        kv['Target'] = _etr_target(kv['Parameter'], kv['Component'])
        if kv['Target'] is None:
            r.err('%s: no name for (Parameter %d, Component %d)' % (w, kv['Parameter'], kv['Component']))
        n['KeyframedValues'].append(kv)
    mn, mo = r.u16(o + 162), r.i32(o + 164) + 120 + o
    n['Modifiers'] = _emp_modifiers(r, mo, mn, 'ETR node at 0x%X' % o, etr=True) if mn else []
    return n


def read_etr(data, strict=True):
    """ETR header (24 bytes): +0 "#ETR", +4 u16 0xFFFE, +6 u16 24, +8 i32 Version, +12 i16 node
    count, +14 i16 texture sampler count, +16 i32 node offset (24), +20 i32 sampler offset.
    Nodes are 176 bytes each, back to back; samplers as EMP (DBXV2 size)."""
    r = Bin(data, 'ETR')
    if r.raw(0, 4) != b'#ETR':
        r.err('#ETR file signature not found')
    ver = r.i32(8)
    out = {'Endian': r.u16(4), 'HeaderSize': r.u16(6), 'Version': ver,
           'VersionName': _enum(ver, EMP_VERSIONS, 'version', r)}
    nn, nt, no, to = r.i16(12), r.i16(14), r.i32(16), r.i32(20)
    out['Textures'] = [_read_sampler(r, to, i, 'DBXV2') for i in range(nt)]
    out['Nodes'] = [_etr_node(r, no + 176 * i, to, out['Textures']) for i in range(nn)]
    out['_coverage'] = r.coverage(strict)
    return out


# ---------------------------------------------------------------------------------------------
# EEPK: EEPK/EEPK_File.cs
# ---------------------------------------------------------------------------------------------
ASSET_TYPES = {0: 'EMO', 1: 'PBIND', 2: 'TBIND', 3: 'LIGHT', 4: 'CBIND'}
ASSET_FILE_TYPES = {0: 'EMO', 1: 'EMM', 2: 'EMB', 3: 'EMA', 4: 'EMP', 5: 'ETR', 7: 'ECF', 255: 'Null'}
EEPK_FLAGS1 = {0x01: 'PositionUpdate', 0x02: 'RotateUpdate', 0x04: 'InstantUpdate', 0x08: 'OnGroundOnly',
               0x10: 'UseTimeScale', 0x20: 'UseBoneDirection', 0x40: 'EnableRotationValues',
               0x80: 'UseScreenCenterToBoneDirection'}
EEPK_FLAGS2 = {0x01: 'EMA_Loop', 0x1000000: 'NoGlare', 0x4000000: 'InverseTransparentDrawOrder',
               0x8000000: 'RelativePositionZ_To_AbsolutePositionZ', 0x10000000: 'ScaleZ_To_BonePositionZ',
               0x80000000: 'ObjectOrientation_To_XXXX'}
EEPK_FLAGS2.update({1 << b: 'I_%d_%d' % (36 + b // 8, b % 8) for b in list(range(1, 16)) + [25, 29, 30]})
DEACTIVATION = {0: 'Never', 1: 'Immediate', 2: 'LoopCancel'}
ATTACHMENT = {0: 'External', 1: 'Unk1', 2: 'Bone', 3: 'Camera'}
ORIENTATION = {0: 'None', 1: 'User', 2: 'AttachmentBone', 3: 'Camera', 4: 'RotateMovement'}


def read_eepk(data, strict=True):
    """EEPK: header (24): +0 "#EPK", +4 u16 0xFFFE, +6 u16 24, +8 i32 Version, +12 u16 asset
    container count, +14 u16 effect table length, +16 i32 container offset, +20 i32 effect table
    offset (i32 per effect id, 0 = no effect).
    Asset container (48): i32 AssetSpawnLimit, u8 I_04..I_07, i32 AssetListLimit, i32 I_12,
      u16 AssetType (0 EMO 1 PBIND 2 TBIND 3 LIGHT 4 CBIND), 12 x 0, u16 asset count, i32 assets
      (relative to the container), i32 ContainerEmbPath, MaterialEmmPath, TextureEmbPath string
      offsets (relative to the container; 0 = none).
    Asset (12): i16 I_00, u8 AssetType, u8 file count, i32 file type bytes (relative to the asset),
      i32 file name table (relative; i32 per file -> a string relative to the asset).
    Effect (16): u16 id, u16 I_02, 6 x 0, u16 part count, i32 parts (relative to the effect).
    EffectPart (100): see _eepk_part."""
    r = Bin(data, 'EEPK')
    if r.raw(0, 4) != b'#EPK':
        r.err('#EPK signature not found')
    out = {'Endian': r.u16(4), 'HeaderSize': r.u16(6), 'Version': r.i32(8)}
    nc, ne, co, eo = r.u16(12), r.u16(14), r.i32(16), r.i32(20)
    conts = []
    for ci in range(nc):
        o = co + 48 * ci
        c = {'Index': ci, 'AssetSpawnLimit': r.i32(o), 'I_04': r.u8(o + 4), 'I_05': r.u8(o + 5),
             'I_06': r.u8(o + 6), 'I_07': r.u8(o + 7), 'AssetListLimit': r.i32(o + 8), 'I_12': r.i32(o + 12),
             'AssetType': _enum(r.u16(o + 16), ASSET_TYPES, 'AssetType', r)}
        r.zero(o + 18, 12, 'container +18')
        na, ao = r.u16(o + 30), r.i32(o + 32) + o
        for key, at in (('ContainerEmbPath', 36), ('MaterialEmmPath', 40), ('TextureEmbPath', 44)):
            so = r.i32(o + at)
            c[key] = r.cstr(so + o) if so > 0 else None
        assets = []
        for ai in range(na):
            a = ao + 12 * ai
            at = _enum(r.u8(a + 2), ASSET_TYPES, 'asset type', r)
            if at != c['AssetType']:
                r.err('AssetType mismatch; found asset with type %s in %s container' % (at, c['AssetType']))
            nf, numo, fo = r.u8(a + 3), r.i32(a + 4), r.i32(a + 8)
            ftypes = [_enum(r.u8(a + numo + k), ASSET_FILE_TYPES, 'asset file type', r) for k in range(nf)]
            files = []
            if fo > 0:
                for k in range(nf):
                    so = r.i32(a + fo + 4 * k)
                    files.append(r.cstr(so + a) if so > 0 else None)
            assets.append({'Index': ai, 'I_00': r.i16(a), 'FileTypes': ftypes, 'Files': files})
        c['Assets'] = assets
        conts.append(c)
    out['AssetContainers'] = conts
    effects = []
    for ei in range(ne):
        eff = r.i32(eo + 4 * ei)
        if eff <= 0:
            continue
        if r.u16(eff) != ei:
            r.err('EffectID does not match its index')
        r.zero(eff + 4, 6, 'effect +4')
        e = {'IndexNum': ei, 'I_02': r.u16(eff + 2), 'EffectParts': []}
        pn, po = r.u16(eff + 10), r.i32(eff + 12) + eff
        for pi in range(pn):
            e['EffectParts'].append(_eepk_part(r, po + 100 * pi))
        effects.append(e)
    out['Effects'] = effects
    # resolve each part's asset to its file names
    by_type = {c['AssetType']: c for c in conts}
    for e in effects:
        for p in e['EffectParts']:
            c = by_type.get(p['AssetType'])
            if c is None or p['AssetIndex'] >= len(c['Assets']):
                r.err('effect %d: %s asset %d does not exist' % (e['IndexNum'], p['AssetType'], p['AssetIndex']))
            p['Files'] = c['Assets'][p['AssetIndex']]['Files']
    out['_coverage'] = r.coverage(strict)
    return out


def _eepk_part(r, o):
    """EffectPart (100): +0 u16 AssetIndex, +2 u8 AssetType, +3 u8 AttachementType (0 External,
    2 Bone, 3 Camera), +4 u8 Orientation, +5 u8 Deactivation (0 Never, 1 Immediate, 2 LoopCancel),
    +6 u8 I_06, I_07, +8 i32 I_08, I_12, I_16, I_20, +24 f32 AvoidSphere, +28 u16 StartTime
    (frames), +30 u16 EMA_AnimationIndex, +32 u8 Flags1, +33 0, +34 i16 I_34, +36 u32 Flags2
    (bits 16..19 I_38_a, 20..23 I_38_b), +40 f32 Position XYZ, +52 f32 RotationX_Min, X_Max,
    Y_Min, Y_Max, Z_Min, Z_Max (radians), +76 f32 ScaleMin, ScaleMax, NearFadeDistance,
    FarFadeDistance, +92 u16 EMA_LoopStartFrame, EMA_LoopEndFrame, +96 i32 ESK (attach bone name,
    relative to the part)"""
    f36 = r.u32(o + 36)
    f1 = r.u8(o + 32)
    p = {'AssetIndex': r.u16(o), 'AssetType': _enum(r.u8(o + 2), ASSET_TYPES, 'part AssetType', r),
         'AttachementType': _enum(r.u8(o + 3), ATTACHMENT, 'Attachment', r),
         'Orientation': _enum(r.u8(o + 4), ORIENTATION, 'Orientation', r),
         'Deactivation': _enum(r.u8(o + 5), DEACTIVATION, 'Deactivation', r),
         'I_06': r.u8(o + 6), 'I_07': r.u8(o + 7), 'I_08': r.i32(o + 8), 'I_12': r.i32(o + 12),
         'I_16': r.i32(o + 16), 'I_20': r.i32(o + 20), 'AvoidSphere': r.f32(o + 24),
         'StartTime': r.u16(o + 28), 'EMA_AnimationIndex': r.u16(o + 30),
         'Flags1': f1, 'Flags1_names': _flags(f1, EEPK_FLAGS1)}
    r.zero(o + 33, 1, 'part +33')
    p['I_34'] = r.i16(o + 34)
    p['I_38_a'], p['I_38_b'] = (f36 >> 16) & 0xF, (f36 >> 20) & 0xF
    f2 = f36 & ~(0xFF << 16)
    p['Flags2'], p['Flags2_names'] = f2, _flags(f2, EEPK_FLAGS2)
    p['Position'] = r.f32s(o + 40, 3)
    rot = [_f(math.degrees(v)) for v in r.f32s(o + 52, 6)]
    for k, name in enumerate(('RotationX_Min', 'RotationX_Max', 'RotationY_Min', 'RotationY_Max',
                              'RotationZ_Min', 'RotationZ_Max')):
        p[name] = rot[k]
    p['ScaleMin'], p['ScaleMax'], p['NearFadeDistance'], p['FarFadeDistance'] = r.f32s(o + 76, 4)
    p['EMA_LoopStartFrame'], p['EMA_LoopEndFrame'] = r.u16(o + 92), r.u16(o + 94)
    eo = r.i32(o + 96)
    p['ESK'] = r.cstr(o + eo) if eo > 0 else None
    return p


# ---------------------------------------------------------------------------------------------
# EMA (light / obj / mat animations): header and per-animation summary only
# ---------------------------------------------------------------------------------------------
EMA_TYPES = {3: 'obj', 4: 'light', 8: 'mat'}


def read_ema(data):
    """only a note: Animation/EMA/EMA_File.cs header (+8 i32 Version, +12 i32 skeleton offset,
    +16 u16 animation count, +18 u16 EmaType 3 obj / 4 light / 8 mat, +32 i32 animation offsets);
    animation: +0 u16 EndFrame, +2 u16 command count, +4 i32 value count, +8 u8 EmaType, +9 u8
    LightUnknown, +10 u16 FloatPrecision (0 Vector4 f32, 1 f16, 2 f32), +12 i32 name offset (+11), +16 i32 values
    offset, +20 command offsets. Commands / keyframes are not decoded (values listed raw)."""
    if data[:4] != b'#EMA':
        raise FormatError('EMA: no #EMA signature')
    ver, skel, na, typ = struct.unpack_from('<iiHH', data, 8)
    out = {'Version': ver, 'EmaType': EMA_TYPES.get(typ, typ), 'HasSkeleton': skel > 0, 'Animations': []}
    for i in range(na):
        ao = struct.unpack_from('<i', data, 32 + 4 * i)[0]
        if not ao:
            continue
        end, nc, nv = struct.unpack_from('<HHi', data, ao)
        prec = struct.unpack_from('<H', data, ao + 10)[0]
        no, vo = struct.unpack_from('<ii', data, ao + 12)
        name = None
        if no:
            s = ao + no + 11
            name = data[s:data.index(b'\0', s)].decode('utf-8', 'replace')
        if prec not in (0, 1, 2):
            raise FormatError('EMA animation %d: unknown FloatPrecision %d' % (i, prec))
        vals = [_f(v) for v in struct.unpack_from('<%d%s' % (nv, 'e' if prec == 1 else 'f'), data, ao + vo)]
        out['Animations'].append({'Index': i, 'Name': name, 'EndFrame': end, 'Commands': nc,
                                  'FloatPrecision': prec, 'Values': vals})
    return out


# ---------------------------------------------------------------------------------------------
# package
# ---------------------------------------------------------------------------------------------
def _read(path):
    with open(path, 'rb') as fh:
        return fh.read()


def load_package(d, strict=True):
    """the .eepk in d and everything it names (missing files are listed, not fatal)"""
    eepks = sorted(f for f in os.listdir(d) if f.lower().endswith('.eepk'))
    if len(eepks) != 1:
        raise FormatError('%s: expected one .eepk, found %s' % (d, eepks))
    name = eepks[0]
    pkg = {'dir': d, 'eepk_name': name, 'eepk': read_eepk(_read(os.path.join(d, name)), strict),
           'emp': {}, 'etr': {}, 'emm': {}, 'emb_textures': {}, 'ema': {}, 'missing': [], 'other_files': []}
    used = {name}
    for c in pkg['eepk']['AssetContainers']:
        for key in ('ContainerEmbPath', 'MaterialEmmPath', 'TextureEmbPath'):
            fn = c[key]
            if not fn:
                continue
            p = os.path.join(d, fn)
            if not os.path.exists(p):
                pkg['missing'].append(fn)
                continue
            used.add(fn)
            if key == 'MaterialEmmPath':
                pkg['emm'][fn] = read_emm(_read(p), strict)
            elif key == 'TextureEmbPath':
                pkg['emb_textures'][fn] = [(n, dds_info(b)) for n, b in Emb(_read(p))]
            else:
                for n, b in Emb(_read(p)):
                    if n.lower().endswith('.emp'):
                        pkg['emp'][n] = read_emp(b, strict)
                    elif n.lower().endswith('.etr'):
                        pkg['etr'][n] = read_etr(b, strict)
                    else:
                        raise FormatError('%s: unexpected entry %s' % (fn, n))
        for a in c['Assets']:
            for fn in a['Files']:
                if not fn:
                    continue
                if c['AssetType'] in ('PBIND', 'TBIND'):
                    have = pkg['emp'] if c['AssetType'] == 'PBIND' else pkg['etr']
                    if fn not in have:
                        pkg['missing'].append(fn)
                    continue
                p = os.path.join(d, fn)
                if not os.path.exists(p):
                    pkg['missing'].append(fn)
                    continue
                used.add(fn)
                if fn.lower().endswith('.ema'):
                    pkg['ema'][fn] = read_ema(_read(p))
                elif fn.lower().endswith('.emm'):
                    pkg['emm'][fn] = read_emm(_read(p), strict)
    pkg['other_files'] = sorted(f for f in os.listdir(d) if f not in used)
    # cross references, under the C# property names: sampler TextureRef (texture name in the
    # container's texture EMB), emission Texture / ETR node MaterialRef (EMM material name)
    for kind, files in (('PBIND', pkg['emp']), ('TBIND', pkg['etr'])):
        for x in files.values():
            for smp in x['Textures']:
                smp['TextureRef'] = resolve_texture(pkg, kind, smp)
            owners = ([n['EmissionNode']['Texture'] for _, n in emp_nodes(x) if n['NodeType'] == 'Emission']
                      if kind == 'PBIND' else x['Nodes'])
            for t in owners:
                mat = resolve_material(pkg, kind, t['MaterialID'])
                t['MaterialRef'] = mat['Name'] if mat else None
    return pkg


def _container(pkg, typ):
    for c in pkg['eepk']['AssetContainers']:
        if c['AssetType'] == typ:
            return c
    return None


def resolve_texture(pkg, kind, sampler):
    """the texture name a sampler's EmbIndex picks in the PBIND / TBIND container's texture EMB"""
    c = _container(pkg, kind)
    texs = pkg['emb_textures'].get(c['TextureEmbPath']) if c else None
    if sampler['EmbIndex'] == 255 or texs is None:
        return None
    if sampler['EmbIndex'] >= len(texs):
        return '<EmbIndex %d out of range>' % sampler['EmbIndex']
    return texs[sampler['EmbIndex']][0]


def resolve_material(pkg, kind, mid):
    c = _container(pkg, kind)
    emm = pkg['emm'].get(c['MaterialEmmPath']) if c else None
    if mid == 0xFFFF or emm is None:
        return None
    if mid >= len(emm['Materials']):
        return {'Name': '<MaterialID %d out of range>' % mid, 'ShaderProgram': '', 'Parameters': []}
    return emm['Materials'][mid]


def _blend(mat):
    """a short blend description from the EMM parameters (AlphaBlend / AlphaBlendType: 0 normal,
    1 additive, 2 subtractive)"""
    if not mat:
        return '-'
    p = emm_params(mat)
    ab, abt = p.get('AlphaBlend'), p.get('AlphaBlendType')
    kind = {0: 'normal', 1: 'add', 2: 'sub'}.get(abt, abt)
    s = '%s/%s' % (mat['ShaderProgram'], 'blend=%s' % kind if ab in (1, True) else 'noblend')
    return s


def _kv_digest(kvs):
    out = []
    for kv in kvs:
        ks = kv['Keyframes']
        if not ks:
            continue
        pts = ' '.join('%d:%.3g' % (k['Time'], k['Value']) for k in ks[:6])
        more = ' ..' if len(ks) > 6 else ''
        tag = ('L' if kv.get('Loop') else '') + ('' if kv.get('Interpolate') else 'S')
        out.append('%s[%s%s]%s' % (kv['Target'], pts, more, '/' + tag if tag else ''))
    return out


def _col(c, a):
    return '(%.2f,%.2f,%.2f,%.2f)' % (c[0], c[1], c[2], a)


def emp_span(node):
    """a rough upper bound of when a node's last particle dies, in frames after the EMP starts:
    StartTime + StartTime_Variance + Lifetime + Lifetime_Variance, plus the longest child span
    (children are spawned by their parent while it lives); None if the node loops"""
    if 'Loop' in node['NodeFlags_names']:
        return None
    own = node['StartTime'] + node['StartTime_Variance'] + node['Lifetime'] + node['Lifetime_Variance']
    kids = [emp_span(c) for c in node['ChildParticleNodes']]
    if None in kids:
        return None
    return own + max(kids, default=0)


def emp_timing(emp):
    """(span in frames of the non-looping nodes, names of looping root nodes)"""
    spans = [emp_span(n) for n in emp['ParticleNodes']]
    loops = [n['Name'] for n, sp in zip(emp['ParticleNodes'], spans) if sp is None]
    return max([sp for sp in spans if sp is not None], default=0), loops


def summary(pkg):
    L = []
    e = pkg['eepk']
    L.append('EEPK %s  version %d  %d containers  %d effects' % (pkg['eepk_name'], e['Version'],
                                                               len(e['AssetContainers']), len(e['Effects'])))
    for c in e['AssetContainers']:
        L.append('  container %s: emb=%s emm=%s tex=%s  spawn %d list %d  assets:' % (
            c['AssetType'], c['ContainerEmbPath'], c['MaterialEmmPath'], c['TextureEmbPath'],
            c['AssetSpawnLimit'], c['AssetListLimit']))
        for a in c['Assets']:
            L.append('    %2d %s' % (a['Index'], ', '.join(str(f) for f in a['Files'])))
    L.append('')
    L.append('Effects (StartTime in frames; Pos / Rot(deg) / Scale offsets)')
    for ef in e['Effects']:
        L.append('  effect %d (I_02 %d): %d parts' % (ef['IndexNum'], ef['I_02'], len(ef['EffectParts'])))
        for p in ef['EffectParts']:
            rot = (p['RotationX_Min'], p['RotationY_Min'], p['RotationZ_Min'])
            rr = '' if (p['RotationX_Min'], p['RotationY_Min'], p['RotationZ_Min']) == (
                p['RotationX_Max'], p['RotationY_Max'], p['RotationZ_Max']) else ' rand..(%g,%g,%g)' % (
                p['RotationX_Max'], p['RotationY_Max'], p['RotationZ_Max'])
            L.append('    %-5s %-2d %-22s bone=%-10s t=%-3d %s/%s deact=%s pos=(%g,%g,%g) rot=(%g,%g,%g)%s '
                     'scale=%g..%g flags1=%s flags2=%s%s' % (
                         p['AssetType'], p['AssetIndex'], ','.join(f for f in p['Files'] if f)[:22], p['ESK'],
                         p['StartTime'], p['AttachementType'], p['Orientation'], p['Deactivation'],
                         *p['Position'], *rot, rr, p['ScaleMin'], p['ScaleMax'], '|'.join(p['Flags1_names']) or '-',
                         '|'.join(p['Flags2_names']) or '-',
                         ' I_38=%d,%d' % (p['I_38_a'], p['I_38_b']) if p['I_38_a'] or p['I_38_b'] else '') +
                     (' fade=%g..%g' % (p['NearFadeDistance'], p['FarFadeDistance'])
                      if p['NearFadeDistance'] or p['FarFadeDistance'] else '') +
                     (' ema_loop=%d..%d' % (p['EMA_LoopStartFrame'], p['EMA_LoopEndFrame'])
                      if p['EMA_LoopStartFrame'] or p['EMA_LoopEndFrame'] else '') +
                     ''.join(' %s=%s' % (k, p[k]) for k in ('I_06', 'I_07', 'I_08', 'I_12', 'I_16', 'I_20', 'I_34',
                                                            'AvoidSphere', 'EMA_AnimationIndex') if p[k]))
    for fn, emp in sorted(pkg['emp'].items()):
        L.append('')
        span, loops = emp_timing(emp)
        L.append('EMP %s (%s): %d nodes, %d texture samplers; %s%s' % (
            fn, emp['VersionName'], len(emp_nodes(emp)), len(emp['Textures']),
            'non-looping roots end by ~frame %d' % span if span else 'every root loops',
            '; looping roots (run until the EEPK part is deactivated): %s' % ', '.join(loops) if loops else ''))
        for s in emp['Textures']:
            sc = s['ScrollState']
            scs = (('speed %g,%g/frame' % (sc['ScrollSpeed_U'], sc['ScrollSpeed_V'])) if sc['ScrollType'] == 'Speed'
                   else ' '.join('[t%d uv+(%g,%g) x(%g,%g)]' % (k['Time'], k['ScrollU'], k['ScrollV'], k['ScaleU'],
                                                                 k['ScaleV']) for k in sc['Keyframes'][:6]))
            L.append('  sampler %d -> %s  %s/%s %s %s  %s' % (s['Index'], resolve_texture(pkg, 'PBIND', s),
                                                             s['RepetitionU'], s['RepetitionV'], s['FilteringMin'],
                                                             s['KeyframeType'], sc['ScrollType'] + ' ' + scs))
        for depth, n in emp_nodes(emp):
            ind = '  ' + '. ' * depth
            head = '%s%-8s %-26s life=%d~%d start=%d~%d' % (ind, n['NodeType'], repr(n['Name']), n['Lifetime'],
                                                          n['Lifetime_Variance'], n['StartTime'], n['StartTime_Variance'])
            emit = ' burst=%d~%d every %d~%d max=%d%s' % (n['Burst'], n['Burst_Variance'], n['BurstFrequency'],
                                                        n['BurstFrequency_Variance'], n['MaxInstances'],
                                                        ' loop' if 'Loop' in n['NodeFlags_names'] else '')
            pos = ''
            if any(n['Position']) or any(n['Position_Variance']):
                pos += ' pos=(%g,%g,%g)~(%g,%g,%g)' % (*n['Position'], *n['Position_Variance'])
            if any(n['Rotation']) or any(n['Rotation_Variance']):
                pos += ' rot=(%g,%g,%g)~(%g,%g,%g)' % (*n['Rotation'], *n['Rotation_Variance'])
            L.append(head + emit + pos)
            if n['NodeType'] == 'Emitter':
                em = n['EmitterNode']
                L.append('%s    shape=%s(%s) %s' % (ind, em['Shape'], n['NodeSpecificType'], ' '.join(
                    '%s=%g' % (k, v) for k, v in em.items() if k not in ('Shape', 'EmitFromArea'))))
            elif n['NodeType'] == 'Emission':
                em = n['EmissionNode']
                t = em['Texture']
                mat = resolve_material(pkg, 'PBIND', t['MaterialID'])
                texs = [resolve_texture(pkg, 'PBIND', emp['Textures'][i]) if i is not None else None
                        for i in t['TextureEntryRef']]
                extra = ''
                if 'ActiveRotation' in em:
                    extra += ' rot0=%g~%g spin=%g~%g' % (em['StartRotation'], em['StartRotation_Variance'],
                                                         em['ActiveRotation'], em['ActiveRotation_Variance'])
                if 'RotationAxis' in em:
                    extra += ' axis=(%g,%g,%g)' % tuple(em['RotationAxis'])
                if 'ConeExtrude' in em:
                    c = em['ConeExtrude']
                    extra += ' extrude dur=%d~%d step=%d points=%d' % (c['Duration'], c['Duration_Variance'],
                                                                       c['StepDuration'], len(c['Points']))
                if 'ShapeDraw' in em:
                    extra += ' shape points=%d' % len(em['ShapeDraw']['Points'])
                L.append('%s    %s/%s billboard=%s size=%g~%g%s%s' % (
                    ind, em['EmissionType'], n['NodeSpecificType'], em['BillboardType'], t['ScaleBase'],
                    t['ScaleBase_Variance'],
                    ' xy=(%g,%g)~(%g,%g)' % (*t['ScaleXY'], *t['ScaleXY_Variance'])
                    if 'EnableScaleXY' in n['NodeFlags_names'] else '', extra))
                L.append('%s    color1=%s%s var=%s  tex=%s samplers=%s mat=%d:%s %s depth=%g' % (
                    ind, _col(t['Color1'], t['Color1_Transparency']),
                    ' color2=' + _col(t['Color2'], t['Color2_Transparency'])
                    if 'EnableSecondaryColor' in n['NodeFlags_names'] else '',
                    '(%g,%g,%g,%g)' % tuple(t['Color_Variance']), texs, t['TextureEntryRef'], t['MaterialID'],
                    mat['Name'] if mat else None, _blend(mat), t['RenderDepth']))
            fl = [f for f in n['NodeFlags_names'] if f != 'Loop'] + n['NodeFlags2_names']
            if fl:
                L.append('%s    flags=%s' % (ind, '|'.join(fl)))
            for s in _kv_digest(n['KeyframedValues']):
                L.append('%s    kf %s' % (ind, s))
            for m in n['Modifiers']:
                L.append('%s    modifier %s flags=%s: %s' % (ind, m['TypeStr'], m['Flags'],
                                                            '; '.join(_kv_digest(m['KeyframedValues']))))
    for fn, etr in sorted(pkg['etr'].items()):
        L.append('')
        L.append('ETR %s: %d nodes, %d samplers' % (fn, len(etr['Nodes']), len(etr['Textures'])))
        for s in etr['Textures']:
            sc = s['ScrollState']
            L.append('  sampler %d -> %s %s/%s %s %s' % (
                s['Index'], resolve_texture(pkg, 'TBIND', s), s['RepetitionU'], s['RepetitionV'], sc['ScrollType'],
                ('%g,%g/frame' % (sc['ScrollSpeed_U'], sc['ScrollSpeed_V'])) if sc['ScrollType'] == 'Speed' else
                ' '.join('uv+(%g,%g) x(%g,%g)' % (k['ScrollU'], k['ScrollV'], k['ScaleU'], k['ScaleV'])
                         for k in sc['Keyframes'][:4])))
        for i, n in enumerate(etr['Nodes']):
            mat = resolve_material(pkg, 'TBIND', n['MaterialID'])
            L.append('  node %d bone=%s/%s pos=(%g,%g,%g) rot=(%g,%g,%g) start=%d extrude=%d hold=%d (ends frame %d) '
                     'seg=%d extrudeZ=%g scale=%g' % (
                         i, n['AttachBone'], n['AttachBone2'], *n['Position'], *n['Rotation'], n['StartTime'],
                         n['ExtrudeDuration'], n['HoldDuration'],
                         n['StartTime'] + n['ExtrudeDuration'] + n['HoldDuration'], n['SegementFrameSize'],
                         n['PositionExtrudeZ'], n['Scale']))
            L.append('    color1=%s color2=%s flags=%s mat=%d:%s %s tex=%s I_88=%d I_92=%d I_100=%d' % (
                _col(n['Color1'], n['Color1_Transparency']), _col(n['Color2'], n['Color2_Transparency']),
                '|'.join(n['Flags_names']) or '-', n['MaterialID'], mat['Name'] if mat else None, _blend(mat),
                [resolve_texture(pkg, 'TBIND', etr['Textures'][k]) if k is not None else None
                 for k in n['TextureEntryRef']], n['I_88'], n['I_92'], n['I_100']))
            L.append('    paths=%s shape=%d points' % (
                ' '.join('(%g,%g,%g,%g)' % tuple(p.values()) for p in n['ExtrudePaths'][:6]) +
                (' ..%d' % len(n['ExtrudePaths']) if len(n['ExtrudePaths']) > 6 else ''),
                len(n['ExtrudeShapePoints'])))
            for kv in n['KeyframedValues']:
                L.append('    kf %s (%s)' % (_kv_digest([kv])[0] if kv['Keyframes'] else kv['Target'],
                                             kv['ETR_InterpolationType']))
            for m in n['Modifiers']:
                L.append('    modifier %s: %s' % (m['TypeStr'], '; '.join(_kv_digest(m['KeyframedValues']))))
    for fn, emm in sorted(pkg['emm'].items()):
        L.append('')
        L.append('EMM %s: %d materials' % (fn, len(emm['Materials'])))
        for m in emm['Materials']:
            if m:
                L.append('  %2d %-24s %-22s %s' % (m['Index'], m['Name'], m['ShaderProgram'], ' '.join(
                    '%s=%s' % (p['Name'], p['Value']) for p in m['Parameters'])))
    for fn, tex in sorted(pkg['emb_textures'].items()):
        L.append('')
        L.append('EMB %s: %s' % (fn, ', '.join('%d %s %s' % (i, n, '%dx%d %s' % info if info else '?')
                                              for i, (n, info) in enumerate(tex))))
    if pkg['ema']:
        L.append('')
        for fn, ema in sorted(pkg['ema'].items()):
            L.append('EMA %s (%s): %s' % (fn, ema['EmaType'], '; '.join(
                '%s end=%d commands=%d values=%s' % (a['Name'], a['EndFrame'], a['Commands'],
                                                    a['Values'][:12]) for a in ema['Animations'])))
    if pkg['missing'] or pkg['other_files']:
        L.append('')
        L.append('missing: %s' % pkg['missing'])
        L.append('other files in the folder (EMO models etc., not parsed): %s' % pkg['other_files'])
    return '\n'.join(L) + '\n'


def check(pkg):
    """sanity asserts over a loaded package; returns report lines"""
    out = []
    e = pkg['eepk']
    assert not pkg['missing'], 'missing files: %s' % pkg['missing']
    assert e['Effects'], 'no effects'
    for ef in e['Effects']:
        for p in ef['EffectParts']:
            assert all(p['Files']) and p['Files'], 'effect %d: unresolved asset' % ef['IndexNum']
            assert p['ScaleMin'] <= p['ScaleMax'] + 1e-6, 'effect %d: ScaleMin > ScaleMax' % ef['IndexNum']
            assert p['AttachementType'] != 'Bone' or p['ESK'], 'effect %d: bone attachment without a bone' % ef['IndexNum']
    for kind, have in (('PBIND', pkg['emp']), ('TBIND', pkg['etr'])):
        c = _container(pkg, kind)
        if c:
            names = [a['Files'][0] for a in c['Assets']]
            assert sorted(names) == sorted(have), '%s assets %s vs container %s' % (kind, names, sorted(have))
    nn = nk = 0
    for fn, emp in pkg['emp'].items():
        for s in emp['Textures']:
            assert resolve_texture(pkg, 'PBIND', s) and not resolve_texture(pkg, 'PBIND', s).startswith('<'), \
                '%s sampler %d: EmbIndex %d' % (fn, s['Index'], s['EmbIndex'])
        for depth, n in emp_nodes(emp):
            nn += 1
            w = '%s %r' % (fn, n['Name'])
            assert n['Name'] and n['Name'].isprintable(), w + ': name'
            if n['NodeType'] == 'Emission':
                t = n['EmissionNode']['Texture']
                mat = resolve_material(pkg, 'PBIND', t['MaterialID'])
                assert mat and not mat['Name'].startswith('<'), w + ': MaterialID %d' % t['MaterialID']
                assert any(i is not None for i in t['TextureEntryRef']), w + ': no texture'
                for c in t['Color1'] + t['Color2']:
                    assert -0.01 <= c <= 64, w + ': colour %g' % c
                assert t['ScaleBase'] >= 0, w + ': ScaleBase'
            assert n['Lifetime'] < 10000, w + ': lifetime %d' % n['Lifetime']
            for m in [n] + n['Modifiers']:
                for kv in m['KeyframedValues']:
                    nk += 1
                    ts = [k['Time'] for k in kv['Keyframes']]
                    assert ts == sorted(ts), w + ': keyframe times not sorted %s' % ts
                    # EMP keyframe times are percent of the particle life
                    assert not ts or ts[-1] <= max(100, kv['Duration']), w + ': keyframe time %d > 100' % ts[-1]
                    exp = ts[-1] + 1 if len(ts) > 1 else 0
                    if kv['Duration'] != exp:
                        out.append('note: %s %s Duration %d, keyframes end at %s' % (w, kv['Target'], kv['Duration'], ts[-1:]))
                    for k in kv['Keyframes']:
                        assert math.isfinite(k['Value']), w + ': non-finite keyframe'
        out += ['note: %s %s' % (fn, s) for s in emp['_notes']]
    for fn, etr in pkg['etr'].items():
        for i, n in enumerate(etr['Nodes']):
            w = '%s node %d' % (fn, i)
            assert n['AttachBone'], w + ': no bone'
            mat = resolve_material(pkg, 'TBIND', n['MaterialID'])
            assert mat and not mat['Name'].startswith('<'), w + ': MaterialID %d' % n['MaterialID']
            assert any(k is not None for k in n['TextureEntryRef']), w + ': no texture'
            life = n['StartTime'] + max(n['ExtrudeDuration'], 0) + n['HoldDuration']
            for kv in n['KeyframedValues']:
                nk += 1
                ts = [k['Time'] for k in kv['Keyframes']]
                assert ts == sorted(ts), w + ': unsorted keyframes'
                if ts and ts[-1] > life + 1:
                    out.append('note: %s %s keyframe at frame %d past start+extrude+hold %d' % (
                        w, kv['Target'], ts[-1], life))
        for s in etr['Textures']:
            assert resolve_texture(pkg, 'TBIND', s), '%s sampler %d' % (fn, s['Index'])
    files = ([(pkg['eepk_name'], pkg['eepk'])] + sorted(pkg['emp'].items()) + sorted(pkg['etr'].items()) +
             sorted(pkg['emm'].items()))
    for fn, x in files:
        c = x['_coverage']
        assert not c['unconsumed'], fn
        out.append('%-28s %7d bytes, %7d consumed, %5d zero padding' % (fn, c['size'], c['consumed'], c['zero_padding']))
    out.append('OK: 1 EEPK (%d effects, %d parts), %d EMP (%d nodes), %d ETR (%d nodes), %d EMM, %d keyframed values, '
               '%d light EMA' % (len(e['Effects']), sum(len(x['EffectParts']) for x in e['Effects']), len(pkg['emp']),
                                 nn, len(pkg['etr']), sum(len(x['Nodes']) for x in pkg['etr'].values()),
                                 len(pkg['emm']), nk, len(pkg['ema'])))
    return out


def negative_tests(d):
    """corrupt copies of the package's files must raise FormatError; returns report lines"""
    out = []
    pkg = load_package(d)
    pb = _container(pkg, 'PBIND')
    name, emp_bytes = next(iter(Emb(_read(os.path.join(d, pb['ContainerEmbPath'])))))
    emp = read_emp(emp_bytes)
    node0 = emp['ParticleNodes'][0]['_offset']
    gap = emp['_coverage']['zero_gaps'][0][0] if emp['_coverage']['zero_gaps'] else None
    eepk = _read(os.path.join(d, pkg['eepk_name']))
    ef_table = struct.unpack_from('<i', eepk, 20)[0]
    first_ef = next(o for o in struct.unpack_from('<%di' % struct.unpack_from('<H', eepk, 14)[0], eepk, ef_table) if o)
    cases = [('EMP node type 7', read_emp, emp_bytes, node0 + 37, 7),
             ('EMP emitter / emission type 9', read_emp, emp_bytes, node0 + 36, 9),
             ('EMP version', read_emp, emp_bytes, 8, 0x55),
             ('EEPK effect id != its index', read_eepk, eepk, first_ef, 0xEE)]
    if gap is not None:
        cases.append(('EMP non-zero byte in alignment padding', read_emp, emp_bytes, gap, 1))
    for what, fn, data, off, val in cases:
        bad = bytearray(data)
        bad[off] = val
        try:
            fn(bytes(bad))
        except FormatError as e:
            out.append('raises as expected: %s (%s: %s)' % (what, name if fn is read_emp else pkg['eepk_name'], e))
            continue
        raise AssertionError('corruption not detected: ' + what)
    return out


def _dump_json(obj, path):
    with open(path, 'w') as fh:
        json.dump(obj, fh, indent=1)


def main():
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == 'dump':
        pkg = load_package(a[1])
        os.makedirs(a[2], exist_ok=True)
        _dump_json(pkg['eepk'], os.path.join(a[2], pkg['eepk_name'] + '.json'))
        for kind in ('emp', 'etr', 'emm', 'ema'):
            for fn, x in pkg[kind].items():
                _dump_json(x, os.path.join(a[2], fn + '.json'))
        _dump_json({k: [list(e) for e in v] for k, v in pkg['emb_textures'].items()},
                   os.path.join(a[2], 'textures.json'))
        with open(os.path.join(a[2], 'summary.txt'), 'w') as fh:
            fh.write(summary(pkg))
        print('%s: %d EMP, %d ETR, %d EMM, %d EMA -> %s' % (pkg['eepk_name'], len(pkg['emp']), len(pkg['etr']),
                                                           len(pkg['emm']), len(pkg['ema']), a[2]))
    elif len(a) == 2 and a[0] == 'check':
        for line in check(load_package(a[1])) + negative_tests(a[1]):
            print(line)
    elif len(a) == 2 and a[0] == 'show':
        ext = a[1].lower().rsplit('.', 1)[-1]
        fn = {'eepk': read_eepk, 'emp': read_emp, 'etr': read_etr, 'emm': read_emm, 'ema': read_ema}.get(ext)
        if not fn:
            sys.exit('unknown extension: ' + ext)
        print(json.dumps(fn(_read(a[1])), indent=1))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
