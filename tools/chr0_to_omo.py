#!/usr/bin/env python3
"""Wii BRRES-era bone animations (CHR0 v4 / v5, as BrawlBox / BrawlLib read them) -> Smash 4 OMO animations in a
KCAP main.pac, on the skeleton tools/mdl0_to_nud.py writes from the same model.

  python3 tools/chr0_to_omo.py MODEL.mdl0 OUT_MAIN.pac NAME=FILE.chr0 [NAME=FILE.chr0 ...] [--scale S]
                               [--face +z|auto] [--info]
      NAME: the OMO's name in the pac without .omo (FitGekkougaParabeetleMainA00Wait); the game's motion info keys
            an animation by tools/mtable.py anim_hash(NAME).
      --scale / --face: as given to mdl0_to_nud.py (translations x scale; the TransN root's turn).
      --info: print each CHR0's tracks (bone, component, format, keys) and write nothing.
      --hold BONE:AXIS: that bone's translation on that axis (0 x, 1 y, 2 z) held at 0 in the OMOs; the values taken
            out are returned (convert's info: 'held'), for an object that moves itself by them (the Parabeetle bobs its
            whole article, collision included, by its root's bob).

The files are untrusted input: only parsed (bounds checked).

CHR0 (BrawlLib CHR0Node / CHR0Entry):
- header "CHR0", size, version (4 / 5), bres offset, data offset (a resource group of bone entries), v5 a user data
  offset, the name's offset, its original path, u16 frame count, u16 entries, u32 loop, u32 scaling rule.
- entry: +0 the bone name's offset, +4 its code: bit 1 identity, 2 rotation / translation zero, 3 scale one, 4 / 5 /
  6 scale / rotation / translation isotropic (one value for X Y Z), 7 / 8 / 9 use the model's scale / rotation /
  translation, 13 - 15 scale X / Y / Z constant, 16 - 18 rotation constant, 19 - 21 translation constant, 22 / 23 /
  24 has scale / rotation / translation, 25 - 26 scale format, 27 - 29 rotation format, 30 - 31 translation format;
  then, for each component present (scale, rotation, translation) and axis (X Y Z, or one when isotropic), a float
  when constant, else an offset (from the entry) to its keyframes.
- keyframe formats: 1 I4 (u16 count, pad, float frame scale, step, base; u32 keys: frame 8 bits, value 12 bits (base
  + step x v), tangent 12 bits signed / 32), 2 I6 (u16 count, pad, frame scale, step, base; keys u16 frame / 32,
  u16 value, s16 tangent / 256), 3 I12 (u16 count, pad, frame scale; keys float frame, value, tangent), 4 L1 / 5 L2
  (float step, base; a u8 / u16 a frame), 6 L4 (a float a frame). Interpolated keys are Hermite curves (tangents
  in units a frame); the linear formats hold one value a frame.
- rotations in degrees, R = Rz Ry Rx (as the MDL0's bones).

OMO: every frame 0 .. frame count - 1 sampled (a looping CHR0's last frame is its first again: the game loops the
OMO from its last frame to frame 0), each bone's local translation (x scale), rotation (a quaternion) and scale;
TransN (mdl0_to_nud.py's added root, constant: the turn); bones the CHR0 doesn't name keep their bind pose.
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
import mdl0_to_nud as M  # noqa: E402


def _keys_interp(r, o, fmt):
    """an interpolated track -> [(frame, value, tangent)]"""
    n = r.u16(o)
    if not 0 < n < 4096:
        raise ValueError('CHR0: %d keys at 0x%X' % (n, o))
    out = []
    if fmt == 1:
        step, base = r.f32(o + 8), r.f32(o + 12)
        for k in range(n):
            w = r.u32(o + 16 + 4 * k)
            t = w & 0xFFF
            if t & 0x800:
                t -= 0x1000
            out.append((w >> 24, base + step * ((w >> 12) & 0xFFF), t / 32.0))
    elif fmt == 2:
        step, base = r.f32(o + 8), r.f32(o + 12)
        for k in range(n):
            fr, v, t = struct.unpack('>HHh', r.blob(o + 16 + 6 * k, 6))
            out.append((fr / 32.0, base + step * v, t / 256.0))
    elif fmt == 3:
        for k in range(n):
            out.append(tuple(r.f32(o + 8 + 12 * k, 3)))
    else:
        raise ValueError('CHR0: interpolated format %d' % fmt)
    return out


def _keys_linear(r, o, fmt, frames):
    if fmt == 4:
        step, base = r.f32(o), r.f32(o + 4)
        return [base + step * r.u8(o + 8 + k) for k in range(frames)]
    if fmt == 5:
        step, base = r.f32(o), r.f32(o + 4)
        return [base + step * r.u16(o + 8 + 2 * k) for k in range(frames)]
    if fmt == 6:
        return [r.f32(o + 4 * k) for k in range(frames)]
    raise ValueError('CHR0: linear format %d' % fmt)


def hermite(keys, f):
    """BrawlLib's CHR0 interpolation: Hermite between the keys around f (tangents in units a frame)"""
    if f <= keys[0][0]:
        return keys[0][1]
    if f >= keys[-1][0]:
        return keys[-1][1]
    for (f0, v0, t0), (f1, v1, t1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            span = f1 - f0
            if span <= 0:
                return v1
            s = (f - f0) / span
            s2, s3 = s * s, s * s * s
            return ((2 * s3 - 3 * s2 + 1) * v0 + (s3 - 2 * s2 + s) * span * t0 +
                    (-2 * s3 + 3 * s2) * v1 + (s3 - s2) * span * t1)
    return keys[-1][1]


def parse(path):
    """-> {'name', 'frames', 'loop', 'bones': {name: {'code', 'scale'|'rot'|'trans': [axis tracks]}}}; a track is
    ('const', v) | ('interp', keys) | ('linear', values) | None (absent)"""
    r = M.Reader(open(path, 'rb').read())
    if r.blob(0, 4) != b'CHR0':
        raise ValueError('%s: not a CHR0' % path)
    ver = r.u32(8)
    if ver not in (4, 5):
        raise ValueError('CHR0 version %d' % ver)
    data = r.u32(0x10)
    if ver == 5:
        name_off, frames, n, loop = r.u32(0x18), r.u16(0x20), r.u16(0x22), r.u32(0x24)
    else:
        name_off, frames, n, loop = r.u32(0x14), r.u16(0x18), r.u16(0x1A), r.u32(0x1C)
    out = dict(name=r.cstr(name_off) if name_off else os.path.basename(path), frames=frames, loop=bool(loop), bones={},
               version=ver)
    for nm, eo in M.group(r, data):
        code = r.u32(eo + 4)
        o = eo + 8
        ent = dict(code=code, flags=dict(identity=code >> 1 & 1, rt_zero=code >> 2 & 1, scale_one=code >> 3 & 1,
                                         model_scale=code >> 7 & 1, model_rot=code >> 8 & 1, model_trans=code >> 9 & 1))
        for comp, has_bit, iso_bit, const_bit, fmt_shift, fmt_mask in (('scale', 22, 4, 13, 25, 3),
                                                                         ('rot', 23, 5, 16, 27, 7),
                                                                         ('trans', 24, 6, 19, 30, 3)):
            if not code >> has_bit & 1:
                ent[comp] = None
                continue
            fmt = (code >> fmt_shift) & fmt_mask
            iso = code >> iso_bit & 1
            tracks = []
            for axis in range(1 if iso else 3):
                if code >> (const_bit + axis) & 1:
                    tracks.append(('const', r.f32(o)))
                else:
                    ko = eo + r.s32(o)
                    if fmt in (1, 2, 3):
                        tracks.append(('interp', _keys_interp(r, ko, fmt), fmt))
                    else:
                        tracks.append(('linear', _keys_linear(r, ko, fmt, frames + 1), fmt))
                o += 4
            ent[comp] = tracks * 3 if iso else tracks
        out['bones'][nm] = ent
    return out


def track_value(t, f):
    if t[0] == 'const':
        return t[1]
    if t[0] == 'interp':
        return hermite(t[1], f)
    v = t[1]
    i = int(math.floor(f))
    if i >= len(v) - 1:
        return v[-1]
    a = f - i
    return v[i] * (1 - a) + v[i + 1] * a


def local_at(anim_bone, bind_bone, f):
    """(scale, rotation degrees, translation) of a bone at frame f"""
    fl = anim_bone['flags']
    vals = {}
    for comp, ident, model_bit in (('scale', (1.0, 1.0, 1.0), 'model_scale'), ('rot', (0.0, 0.0, 0.0), 'model_rot'),
                                   ('trans', (0.0, 0.0, 0.0), 'model_trans')):
        tr = anim_bone[comp]
        bind = {'scale': bind_bone['scale'], 'rot': bind_bone['rot'], 'trans': bind_bone['pos']}[comp]
        if tr is not None:
            vals[comp] = tuple(track_value(t, f) for t in tr)
        elif fl[model_bit]:
            vals[comp] = tuple(bind)
        elif fl['identity'] or (comp == 'scale' and fl['scale_one']) or (comp != 'scale' and fl['rt_zero']):
            vals[comp] = ident
        else:
            vals[comp] = tuple(bind)
    return vals['scale'], vals['rot'], vals['trans']


def to_omo(anim, model, scale=1.0, turn=None, hold=None):
    """-> (OMO bytes, frames, per-bone local matrices [bones + 1][frames, 4, 4] (TransN first), held values). hold:
    {bone name: axis}: that bone's translation on that axis held at 0 in the OMO; its values (x scale) returned per frame
    (the object's own movement can take them: an article whose collision must follow the model)"""
    import omo
    import s3ds_enemy as se
    from ultimate_fighter import _mat_quat, _node
    frames = max(1, anim['frames'])
    turn = np.eye(3) if turn is None else np.asarray(turn)
    o = omo.Omo(b'OMO ' + se.OMO_HEAD + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
    locals_ = []
    T = np.eye(4)
    T[:3, :3] = turn
    tn = np.repeat(T[None], frames, 0)
    locals_.append(tn)
    _node(o, se.bone_hash('TransN'), np.zeros((frames, 3)), _mat_quat(tn[:, :3, :3]), np.ones((frames, 3)))
    held = {}
    for b in model['bones']:
        ab = anim['bones'].get(b['name'])
        mats = np.empty((frames, 4, 4))
        for f in range(frames):
            if ab is None:
                sc, rot, tr = b['scale'], b['rot'], b['pos']
            else:
                sc, rot, tr = local_at(ab, b, f)
            tr = np.asarray(tr, float) * scale
            if hold and b['name'] in hold:
                ax = hold[b['name']]
                held.setdefault(b['name'], []).append(float(tr[ax]))
                tr = tr.copy()
                tr[ax] = 0.0
            mats[f] = M.srt(sc, rot, tr)
        locals_.append(mats)
        t, q, s = se.split_trs(mats)
        _node(o, se.bone_hash(b['name']), t, q, s)
    return o.encode(), frames, locals_, held


def print_info(anim):
    print('CHR0 v%d %s: %d frames, loop %s' % (anim['version'], anim['name'], anim['frames'], anim['loop']))
    for nm, e in anim['bones'].items():
        parts = []
        for comp in ('scale', 'rot', 'trans'):
            tr = e[comp]
            if tr is None:
                continue
            for ax, t in zip('XYZ', tr):
                if t[0] == 'const':
                    parts.append('%s%s %.3f' % (comp, ax, t[1]))
                elif t[0] == 'interp':
                    vs = [k[1] for k in t[1]]
                    parts.append('%s%s I%d %d keys %.3f..%.3f' % (comp, ax, {1: 4, 2: 6, 3: 12}[t[2]], len(t[1]), min(vs),
                                                                  max(vs)))
                else:
                    parts.append('%s%s L %d values' % (comp, ax, len(t[1])))
        print('  %-10s code %08X %s' % (nm, e['code'], '; '.join(parts)))


def convert(mdl0, out_pac, pairs, scale=1.0, face='+z', head=None, log=print, hold=None):
    import omo
    model = M.parse(mdl0)
    if face == 'auto':
        bones = model['bones']
        hb = next((b for b in bones if b['name'] == head), None) if head else next(b for b in bones if b['parent'] == 0)
        v = hb['world'][:3, 3] - bones[0]['world'][:3, 3]
        v[1] = 0.0
        axis = v / max(np.linalg.norm(v), 1e-9)
    else:
        axis = M.FACE_AXES[face]
    turn = M.turn_to_z(axis)
    entries, info = [], {}
    for name, path in pairs:
        anim = parse(path)
        b, frames, _l, held = to_omo(anim, model, scale, turn, hold)
        entries.append((name + '.omo', b))
        info[name] = dict(source=os.path.basename(path), frames=frames, loop=anim['loop'],
                          bones=sorted(anim['bones']), held=held)
        log('  %s <- %s: %d frames%s' % (name, os.path.basename(path), frames, ', loop' if anim['loop'] else ''))
    os.makedirs(os.path.dirname(os.path.abspath(out_pac)), exist_ok=True)
    omo.pac_write(out_pac, entries)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mdl0')
    ap.add_argument('out_pac')
    ap.add_argument('pairs', nargs='+')
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--face', default='+z')
    ap.add_argument('--head', default=None)
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--hold', action='append', default=[], help='BONE:AXIS (0 x, 1 y, 2 z): that translation held at 0')
    a = ap.parse_args()
    pairs = [tuple(p.split('=', 1)) for p in a.pairs]
    if a.info:
        for _n, p in pairs:
            print_info(parse(p))
        return
    hold = {h.split(':')[0]: int(h.split(':')[1]) for h in a.hold} or None
    print(convert(a.mdl0, a.out_pac, pairs, a.scale, a.face, a.head, hold=hold))


if __name__ == '__main__':
    main()
