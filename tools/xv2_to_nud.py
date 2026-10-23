#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 effect models (EMO + EMM + EMB + obj.ema + mat.ema) -> Smash 4 effect
model folders (model.nud / .nut / .vbn / .omo / .mta / .xmb), see docs/xv2-model-conversion.md.

  python3 tools/xv2_to_nud.py SRC_DIR NAME OUT_DIR [--prefix EffSupamarioKame] [--scale 8.5]
                              [--tex-base 0x15141A00] [--anim 0] [--matcol1 mean|rgb]
                              [--preview DIR]
      NAME: an EMO's base name in SRC_DIR (Kmh_Fire), a glob (Kmh_*) or `all`. Each EMO becomes
      OUT_DIR/<prefix><Name>/ (Kmh_Fire -> EffSupamarioKameFire: the text after the first '_';
      without --prefix, Eff<Name>). --preview: verify the written folders and render them there.
      --matcol1 rgb: MatCol1 as an RGB multiplier (default mean: its RGB as one brightness).
      --skip PART,...: leave these EMO parts out. --plain 1: only material settings the game's
      effect models use (cull none, no alpha test, subtractive drawn additive).
  python3 tools/xv2_to_nud.py verify MODEL_DIR... [--preview DIR] [--src SRC_DIR]
      re-read every file with the repo readers (nud / nut / omo / mta / xmb / vbn), check the round
      trips (and, with --src, the textures and the bone animation against the XV2 files), render.

Mapping (details and what is approximated in the doc):
- skeleton: TopN + the EMO's bones (same names, parent + 1), every bone at the origin in the
  little-endian model.vbn as the game's effect models; the animation gives every bone its full
  local transform each frame (model.omo: obj.ema sampled per frame, Bezier keys evaluated, Euler
  degrees -> quaternions, translations x SCALE).
- meshes: one NUD mesh per EMO part / EMG mesh / submesh group, single-bound (bind 8) to the
  part's bone; positions x SCALE, normals, vertex colour (255 -> 127), UV; triangle lists.
- materials: effect shader 0xB0201100 (UV transform + vertex colour), | 0x40000 (angle fade,
  NU_angleFadeParams) when the XV2 material fades with incidence (IncidenceAlphaBias < 1); blend
  from AlphaBlendType: 0 normal -> src 5 / dst 1, 1 additive -> 5 / 2, 2 subtractive -> 5 / 3;
  cull: BackFace 1 -> none, else 1029 (back); NU_effColorGain = MatCol1 (its RGB as one
  brightness) x MatCol2, NU_effScaleUV =
  the sampler's scale, NU_effTransUV = TexScrl0; NU_materialHash links the model.mta, which carries
  NU_effColorGain / NU_effTransUV per frame from mat.ema.
- textures: the EMB's DDS decoded and re-encoded as GX2 (NTWU) BC1 (opaque) / BC3, one mip, ids
  TEX_BASE + 0x10 x (the EMO's index among SRC_DIR's sorted EMOs) + EMB index.
- model.xmb: the game's effect_near layout (as Mario's EffMarioSmashImpact).
"""
import fnmatch
import glob
import os
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import mta  # noqa: E402
import nud  # noqa: E402
import nut  # noqa: E402
import omo  # noqa: E402
import xmb  # noqa: E402
import xv2model as xv2  # noqa: E402
from xv2emb import Emb, dds_rgba  # noqa: E402

# Smash 4 units per XV2 unit: Mario's model is ~15 units tall (HeadN at 10.2, hat top ~15-16,
# model.vbn / the body .nud's bounding sphere), Goku in XV2 ~1.75 (metres): 15 / 1.75 ~ 8.6.
SCALE = 8.5
# texture ids: 0x151 KK nnn is the game's fighter effect range (KK the fighter: Mario 0x11, Pit
# 0x1D, ... Kamui 0x49; Final Smash banks 0x153 KK nnn); 0x1514 1nnn (KK 0x41, Supamario's kind)
# is used by no vanilla effect model. 0x15141A00-0x15141AFF: the XV2 conversions.
TEX_BASE = 0x15141A00

FLAG_BASE = 0xB0201100          # effect shader, UV transform (0x100), vertex colour (0x1000)
FLAG_ANGLE_FADE = 0x00040000    # NU_angleFadeParams (needs normals)
BLEND = {0: (5, 1), 1: (5, 2), 2: (5, 3)}       # XV2 AlphaBlendType -> NUD src / dst
WRAP = {0: 1, 1: 2, 2: 3}                        # XV2 address mode (wrap, mirror, clamp) -> NUD


# ---------------------------------------------------------------- small writers
def vbn_le(bones):
    """[(name, parent or -1, hash)] -> a little-endian model.vbn as every vanilla effect model's
    (' NBV', 2, 1, bones all type 0, at the origin, unrotated, scale 1)"""
    out = struct.pack('<4sHHI4I', b' NBV', 2, 1, len(bones), len(bones), 0, 0, 0)
    for name, parent, h in bones:
        out += name.encode()[:63].ljust(64, b'\0') + struct.pack('<IiI', 0, 0x0FFFFFFF if parent < 0 else parent, h)
    for _ in bones:
        out += struct.pack('<9f', 0, 0, 0, 0, 0, 0, 1, 1, 1)
    return out


def xmb_write(tree):
    """tree: [(name, [(key, value)], [children])] -> .xmb bytes, laid out as the game's: header,
    the names sorted (offsets), entries breadth first (16 bytes: name, prop count, child count,
    first prop, first child, parent, 0xFFFF), properties (key, value offsets), the names pool
    (entry name then its keys, in entry order, each once), the values pool (each once), padded to 4"""
    flat = []                       # (name, props, parent, children indices)
    queue = [(n, p, c, -1) for n, p, c in tree]
    while queue:
        nxt = []
        for n, p, c, parent in queue:
            flat.append([n, p, parent, None, c])
        for i in range(len(flat) - len(queue), len(flat)):
            n, p, parent, _, c = flat[i]
            for cn, cp, cc in c:
                nxt.append((cn, cp, cc, i))
        queue = nxt
    # first child of each entry: children are consecutive in breadth-first order
    for i, e in enumerate(flat):
        kids = [k for k, f in enumerate(flat) if f[2] == i]
        e[3] = kids[0] if kids else None
    names, values = {}, {}
    npool, vpool = bytearray(), bytearray()

    def name_off(s):
        if s not in names:
            names[s] = len(npool)
            npool.extend(s.encode('latin1') + b'\0')
        return names[s]

    def value_off(s):
        if s not in values:
            values[s] = len(vpool)
            vpool.extend(s.encode('latin1') + b'\0')
        return values[s]
    entries, props = bytearray(), bytearray()
    nprops = 0
    for i, (n, p, parent, first_child, _c) in enumerate(flat):
        no = name_off(n)
        for k, v in p:
            name_off(k)
        nkids = sum(1 for f in flat if f[2] == i)
        if first_child is None:
            # childless: the index just past its parent's children (as the game's)
            if parent < 0:
                first_child = sum(1 for f in flat if f[2] < 0)
            else:
                first_child = flat[parent][3] + sum(1 for f in flat if f[2] == parent)
        entries += struct.pack('>IHHHHHH', no, len(p), nkids, nprops if p else 0xFFFF, first_child,
                               0xFFFF if parent < 0 else parent, 0xFFFF)
        for k, v in p:
            props += struct.pack('>II', names[k], value_off(v))
        nprops += len(p)
    srt = sorted(names, key=lambda s: s.encode('latin1'))
    sorted_off = 0x40
    eoff = sorted_off + 4 * len(srt)
    poff = eoff + len(entries)
    s1 = poff + len(props)
    voff = s1 + len(npool)
    head = struct.pack('>4s10I', b'XMB ', len(flat), nprops, len(srt), 0, sorted_off, eoff, poff, s1, s1, voff)
    out = head + b'\0' * (sorted_off - len(head)) + b''.join(struct.pack('>I', names[s]) for s in srt)
    out += bytes(entries) + bytes(props) + bytes(npool) + bytes(vpool)
    return out + b'\0' * (-len(out) % 4)


def effect_xmb(kind='effect_near'):
    """the model.xmb of Mario's EffMarioSmashImpact (effect_near; Final Smash models use
    effect_blend / effect_main)"""
    return xmb_write([
        ('model', [('type', kind)], [
            ('shadow', [('caster', '0')], []),
            ('lightset', [('number', '0')], []),
            ('object', [('type', '0')], []),
            ('this_light', [('action', '0'), ('color', '0.000000, 0.000000, 0.000000'), ('local_offset', '0, 0, 0'),
                            ('offset', '0.0'), ('radius', '20.0')], []),
            ('draw', [], [('draw', [('buffer', '0'), ('type', 'main')], []),
                          ('draw', [('action', '1'), ('type', 'normalmap')], [])]),
            ('posteffect', [], [('reflection', [('search', '100.0')], [])])])])


def omo_new(frames):
    """an empty OMO (the header of the game's effect animations) for omo.Omo"""
    d = b'OMO ' + struct.pack('>HHIH', 1, 3, 0x09091129, 0) + struct.pack('>HHH', 0, frames, 0)
    d += struct.pack('>III', 0x20, 0x20, 0x20)
    return omo.Omo(d)


def omo_node(o, h, pos, rot, scl):
    """bone h: position / rotation (quaternions x y z w) / scale a frame; a track constant over the
    frames is stored as a constant (position 0x20, rotation 7, scale 0x201), else interpolated
    (0x08, 5, 0x081), as the game's"""
    rot = [tuple(-c for c in q) if q[3] < 0 else tuple(q) for q in rot]
    rot = [q[:3] for q in rot]
    flags, consts, keys = 0, b'', [b''] * o.frames
    for vals, bit, interp, const in ((pos, omo.POS, 0x08 << 16, 0x20 << 16), (rot, omo.ROT, 5 << 12, 7 << 12),
                                     (scl, omo.SCL, 0x081, 0x201)):
        vals = [tuple(float(x) for x in v) for v in vals]
        if all(np.allclose(v, vals[0], atol=1e-7) for v in vals):
            flags |= bit | const
            consts += struct.pack('>3f', *vals[0])
            continue
        c, k = omo.interp_track(vals)
        flags |= bit | interp
        consts += c
        keys = [keys[i] + k[i] for i in range(o.frames)]
    o.nodes.append([flags, h, consts, keys])


def float_hash(name):
    """NU_materialHash: a finite float (4096..8192) from the name's CRC, its bits the MTA's hash"""
    bits = 0x45800000 | (zlib.crc32(name.encode()) & 0x7FFFFF)
    return bits, struct.unpack('>f', struct.pack('>I', bits))[0]


# ---------------------------------------------------------------- conversion
def _sample_vec(anim, mat_index, param, comps, frame, static):
    out = list(static)
    if anim is not None:
        for c in range(comps):
            cmd = anim.command(mat_index, param, c)
            if cmd is not None:
                out[c] = cmd.sample(frame, static[c])
    return out


class Model:
    """one EMO with its EMM / EMB / obj.ema / mat.ema, converted"""

    def __init__(self, src, name, folder, tex_base, scale=SCALE, anim_index=0, matcol1='mean', skip=(),
                 plain=False):
        p = os.path.join(src, name)
        self.name, self.folder, self.scale, self.matcol1 = name, folder, scale, matcol1
        self.skip, self.plain = set(skip), plain
        self.emo = xv2.Emo(open(p + '.emo', 'rb').read())
        self.emm = xv2.Emm(open(p + '.emm', 'rb').read()) if os.path.exists(p + '.emm') else None
        self.emb = list(Emb(open(p + '.emb', 'rb').read())) if os.path.exists(p + '.emb') else []
        self.obj = xv2.Ema(open(p + '.obj.ema', 'rb').read()) if os.path.exists(p + '.obj.ema') else None
        self.mat = xv2.Ema(open(p + '.mat.ema', 'rb').read()) if os.path.exists(p + '.mat.ema') else None
        self.obj_anim = self.obj.animations[anim_index] if self.obj and self.obj.animations else None
        self.mat_anim = self.mat.animations[anim_index] if self.mat and self.mat.animations else None
        # XV2 animations end on a key equal to the first (the loop): frames 0 .. end - 1
        ends = [a.end_frame for a in (self.obj_anim, self.mat_anim) if a is not None]
        self.frames = max(max(ends) if ends else 1, 1)
        self.tex_base = tex_base
        sk = self.emo.skeleton
        self.bones = [('TopN', -1)] + [(b.name, (xv2._none(b.parent) + 1) if xv2._none(b.parent) is not None else 0)
                                       for b in sk.bones]
        self.bones = [(n, p, zlib.crc32(n.encode()) & 0xFFFFFFFF) for n, p in self.bones]
        self.notes = []

    # -- bones
    def local_trs(self, xbone, frame):
        """(pos, quaternion xyzw, scale) of XV2 bone index xbone at frame (Smash units)"""
        a = self.obj_anim
        name = self.emo.skeleton.bones[xbone].name
        bi = self.obj.skeleton.index(name) if a is not None and self.obj.skeleton else -1
        trs = a.sample_trs(bi, frame) if bi >= 0 else None
        if trs is None:
            m = self.emo.skeleton.bones[xbone].matrix            # row vectors
            p, q, s = omo.decompose(m.T.tolist())
            return [c * self.scale for c in p], q, list(s)
        pos, rot, scl = trs
        return [c * self.scale for c in pos], xv2.euler_quat(*rot), scl

    def omo(self):
        o = omo_new(self.frames)
        f = self.frames
        omo_node(o, self.bones[0][2], [(0, 0, 0)] * f, [(0, 0, 0, 1)] * f, [(1, 1, 1)] * f)
        for i, (_n, _p, h) in enumerate(self.bones[1:]):
            tr = [self.local_trs(i, fr) for fr in range(f)]
            omo_node(o, h, [t[0] for t in tr], [t[1] for t in tr], [t[2] for t in tr])
        return o

    # -- materials
    def material_curves(self, m):
        """per frame NU_effColorGain [r g b a] and NU_effTransUV [u v 0 0] of EMM material m"""
        mi = m['index']             # the mat.ema's bone index is the EMM material index (EMA_File.cs)
        a = self.mat_anim
        col1 = xv2.mat_vector(m, 'MatCol1', (1.0, 1.0, 1.0, 1.0))
        col2 = xv2.mat_vector(m, 'MatCol2', (1.0, 1.0, 1.0, 1.0))
        scr = xv2.mat_vector(m, 'TexScrl0', (0.0, 0.0))
        animated = set()
        if a is not None:
            animated = {c.component for c in a.commands if c.bone == mi and c.parameter == 4}
        gains, trans = [], []
        for fr in range(self.frames):
            c1 = _sample_vec(a, mi, 1, 4, fr, col1)
            c2 = _sample_vec(a, mi, 2, 4, fr, col2)
            if self.matcol1 == 'mean':
                # MatCol1's RGB as a brightness (their mean), its A the alpha: taken as an RGB
                # multiplier Kmh_Bas's core (MatCol1 G up to 2, B down to 0.5) turns yellow-green
                b = (c1[0] + c1[1] + c1[2]) / 3.0
                c1 = [b, b, b, c1[3]]
            gains.append([c1[k] * c2[k] for k in range(4)])
            s = _sample_vec(a, mi, 4, 2, fr, scr)
            # a scroll component the mat.ema doesn't animate: the EMM's value read as UV / second
            s = [s[k] if k in animated else scr[k] * fr / 60.0 for k in range(2)]
            trans.append([s[0], s[1], 0.0, 0.0])
        return gains, trans

    def material(self, m, samplers, tex_ids):
        p = m['params'] if m else {}
        blend = int(p.get('AlphaBlendType', 0)) if int(p.get('AlphaBlend', 0)) else -1
        src, dst = BLEND.get(blend, (0, 0))
        # BackFace 1 (every open shell here: cones, domes) read as "draw the back faces too";
        # without it (the closed spheres) back faces culled
        cull = 0 if int(p.get('BackFace', 0)) or int(p.get('TwoSidedRender', 0)) else 1029
        bias = float(p.get('IncidenceAlphaBias', 1.0))
        flags = FLAG_BASE | (FLAG_ANGLE_FADE if bias < 1.0 else 0)
        if self.plain:
            # only what the game's own effect models use: no culling, no alpha test, additive
            # instead of subtractive (no vanilla effect model has dst 3 or an alpha test)
            cull = 0
            if dst == 3:
                dst = 2
                self.notes.append('%s: subtractive drawn additive (--plain)' % (m['name'] if m else '-'))
        mat = nud.Material(flags, src, dst, 0, 0, cull, 0, 0)
        alpha_test = 0 if self.plain else int(p.get('AlphaTest', 0))
        if alpha_test:
            mat.alpha_func, mat.ref_alpha = 0x204, alpha_test        # GL_GREATER, as the game's 4
        for s in samplers[:1]:
            mat.textures.append(dict(hash=tex_ids[s.emb_index], map_mode=0, wrap_s=WRAP.get(s.address_u, 1),
                                     wrap_t=WRAP.get(s.address_v, 1), min_f=3, mag_f=2, mip=6, unk=0, unk2=0))
        if len(samplers) > 1:
            self.notes.append('%s: %d samplers, only the first kept' % (m['name'], len(samplers)))
        gains, trans = self.material_curves(m) if m else ([[1.0] * 4] * self.frames, [[0.0] * 4] * self.frames)
        su, sv = (samplers[0].scale_u, samplers[0].scale_v) if samplers else (1.0, 1.0)
        hbits, hval = float_hash('%s/%s' % (self.folder, m['name'] if m else 'none'))
        mat.props = [('NU_effRotUV', [0.0, 0.0, 0.0, 0.0]), ('NU_effScaleUV', [su, sv, 0.0, 0.0]),
                     ('NU_effTransUV', list(trans[0])), ('NU_effColorGain', list(gains[0]))]
        if flags & FLAG_ANGLE_FADE:
            # alpha x (1 - mix(x, y, fresnel)): facing 1, edge-on IncidenceAlphaBias
            mat.props.append(('NU_angleFadeParams', [0.0, 1.0 - bias, 0.0, 0.0]))
        mat.props.append(('NU_materialHash', [hval, 0.0, 0.0, 0.0]))
        anim = dict(name='%s_%s' % (self.folder, m['name'] if m else 'none'), hash=hbits, gains=gains, trans=trans)
        return mat, anim

    # -- textures
    def textures(self):
        """[(tex id, GX2 format, RGBA)] for every EMB entry"""
        out = []
        for i, (name, d) in enumerate(self.emb):
            img = dds_rgba(d)
            fmt = 0x31 if img[..., 3].min() == 255 else 0x33
            out.append((self.tex_base + i, fmt, img))
        return out

    # -- meshes
    def meshes(self):
        sk = self.emo.skeleton
        tex_ids = [self.tex_base + i for i in range(len(self.emb))]
        meshes, anims, seen = [], [], {}
        for part in self.emo.parts:
            if part['name'] in self.skip:
                self.notes.append('%s: left out (--skip)' % part['name'])
                continue
            for g in part['emgs']:
                xb = part['bone'] if part['bone'] is not None else g.bone
                bone = xb + 1 if xb is not None and xb < len(sk.bones) else 0
                for mi, m in enumerate(g.meshes):
                    if m.flags & xv2.VF_BLEND:
                        self.notes.append('%s: skinned vertices bound rigidly to bone %s' % (part['name'], sk.bones[xb].name))
                    pos = m.attr('pos') * self.scale
                    nrm = m.attr('nrm')
                    nrm = nrm[:, :3] / np.maximum(np.linalg.norm(nrm[:, :3], axis=1, keepdims=True), 1e-9) \
                        if nrm is not None else None
                    col = m.attr('col')
                    col = np.round(col * 127.0 / 255.0) if col is not None else np.full((len(pos), 4), 127.0)
                    uv = m.attr('uv')
                    uv = uv if uv is not None else np.zeros((len(pos), 2))
                    groups = {}
                    for s in m.submeshes:
                        groups.setdefault((s.material, s.texture_list), []).append(s)
                    for (matname, tl), subs in groups.items():
                        tris = np.concatenate([s.triangles(m.strips) for s in subs])
                        if nrm is not None and len(tris):
                            fn = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
                            if ((fn * nrm[tris].sum(1)).sum(1) > 0).mean() < 0.5:
                                tris = tris[:, [0, 2, 1]]       # front faces counter-clockwise, as GL
                                self.notes.append('%s: winding flipped to match the normals' % matname)
                        used = np.unique(tris)
                        remap = np.full(len(pos), -1)
                        remap[used] = np.arange(len(used))
                        poly = nud.Polygon()
                        poly.pos, poly.col, poly.uvs = pos[used], col[used], [uv[used]]
                        poly.nrm = nrm[used] if nrm is not None else np.tile([0.0, 1.0, 0.0], (len(used), 1))
                        poly.idx = remap[tris].reshape(-1)
                        emm_mat = self.emm.find(matname) if self.emm else None
                        if emm_mat is None:
                            self.notes.append('%s: no EMM material, defaults used' % matname)
                        key = (matname, tl)
                        if key not in seen:
                            samplers = m.texture_lists[tl] if tl < len(m.texture_lists) else []
                            seen[key] = self.material(emm_mat, samplers, tex_ids)
                            anims.append(seen[key][1])
                        poly.materials = [seen[key][0].copy()]
                        mname = part['name'] if len(groups) == 1 and len(g.meshes) == 1 else '%s_%d_%s' % (part['name'], mi, matname)
                        meshes.append(nud.Mesh(mname, [poly], bone=bone, bind=8))
        return meshes, anims

    def posed(self, meshes, o):
        """[frames] of [all vertices posed (world)], via the written animation"""
        bones = [(n, p, h) for n, p, h in self.bones]
        out = []
        for fr in range(self.frames):
            w = omo.world(o, bones, fr)
            pts = []
            for m in meshes:
                M = np.array(w[bones[m.bone][0]])
                for p in m.polygons:
                    pts.append(p.pos @ M[:3, :3].T + M[:3, 3])
            out.append(np.concatenate(pts))
        return out

    def write(self, out_dir):
        d = os.path.join(out_dir, self.folder)
        os.makedirs(d, exist_ok=True)
        meshes, anims = self.meshes()
        o = self.omo()
        posed = self.posed(meshes, o)
        allp = np.concatenate(posed)
        # culling spheres: every mesh / the model over the whole animation (the meshes scale up)
        for m in meshes:
            pts = []
            bones = self.bones
            for fr in range(0, self.frames, max(1, self.frames // 30)):
                M = np.array(omo.world(o, bones, fr)[bones[m.bone][0]])
                pts.append(m.polygons[0].pos @ M[:3, :3].T + M[:3, 3])
            m.sphere = nud._sphere(np.concatenate(pts + [m.polygons[0].pos]))
        data = bytearray(nud.write(meshes))
        struct.pack_into('>4f', data, 0x20, *nud._sphere(np.concatenate([allp] + [m.polygons[0].pos for m in meshes])))
        open(d + '/model.nud', 'wb').write(bytes(data))
        open(d + '/model.nut', 'wb').write(nut.write_ntwu(self.textures()))
        open(d + '/model.vbn', 'wb').write(vbn_le(self.bones))
        open(d + '/model.omo', 'wb').write(o.encode())
        mats = []
        for a in anims:
            props = []
            if any(g != a['gains'][0] for g in a['gains']):
                props.append(dict(name='NU_effColorGain', values=a['gains'], u2=0))
            if any(t != a['trans'][0] for t in a['trans']):
                props.append(dict(name='NU_effTransUV', values=a['trans'], u2=0))
            if props:
                mats.append(dict(name=a['name'], hash=a['hash'], props=props))
        # no material animation: an empty model.mta, as 148 of the game's effect models
        open(d + '/model.mta', 'wb').write(mta.write(self.frames, mats, rate=60, unk=1) if mats else b'')
        open(d + '/model.xmb', 'wb').write(effect_xmb())
        self.meshes_written, self.mta_mats = meshes, mats
        return d


# ---------------------------------------------------------------- verify / preview
def _load_folder(d):
    meshes = nud.read(d + '/model.nud')
    nd, texs = nut.load(d + '/model.nut')
    tex = {t.tex_id: nut.decode(nd, t) for t in texs}
    o = omo.Omo(open(d + '/model.omo', 'rb').read())
    bones = omo.vbn_read(d + '/model.vbn')
    md = open(d + '/model.mta', 'rb').read()
    anim = mta.read(md) if md else None
    return meshes, tex, o, bones, anim


def _sample_tex(img, uv, wrap_s, wrap_t):
    h, w = img.shape[:2]

    def wrap(x, mode, n):
        if mode == 3:
            return np.clip(x, 0, 1 - 1e-6)
        if mode == 2:
            f = np.mod(x, 2.0)
            return np.where(f > 1, 2 - f, f).clip(0, 1 - 1e-6)
        return np.mod(x, 1.0)
    u = wrap(uv[:, 0], wrap_s, w)
    v = wrap(uv[:, 1], wrap_t, h)
    return img[(v * h).astype(int), (u * w).astype(int)].astype(np.float64) / 255.0


VIEWS = {'side': (2, 1, np.array([-1.0, 0, 0])),      # camera at -X: screen x = Z, y = Y
         'front': (0, 1, np.array([0, 0, 1.0]))}     # camera at +Z: screen x = X, y = Y


def render(meshes, tex, o, bones, anim, frame, view, size, bounds, only=None, bg=0.12):
    """orthographic preview: effect colour = texture x vertex colour x NU_effColorGain (the
    model.mta's value at frame), UV x NU_effScaleUV + NU_effTransUV, alpha x angle fade; blended
    additive / alpha / subtractive as the material's dst factor, no depth (as z-write-off effects)"""
    ax, ay, cam = VIEWS[view]
    img = np.full((size, size, 3), bg)
    (x0, y0), span = bounds
    w = omo.world(o, bones, frame)
    hashes = {}
    if anim:
        for e in anim['mats']:
            hashes[e['hash']] = {p['name']: p['values'][min(frame, len(p['values']) - 1)] for p in e['props']}
    for mi, m in enumerate(meshes):
        if only is not None and mi != only:
            continue
        M = np.array(w[bones[m.bone][0]])
        for p in m.polygons:
            mat = p.materials[0]
            props = dict(mat.props)
            hb = struct.unpack('>I', struct.pack('>f', props.get('NU_materialHash', [0.0])[0]))[0]
            props.update(hashes.get(hb, {}))
            gain = np.array(props.get('NU_effColorGain', [1, 1, 1, 1]))
            su, sv = props.get('NU_effScaleUV', [1, 1])[:2]
            tu, tv = props.get('NU_effTransUV', [0, 0])[:2]
            fade = props.get('NU_angleFadeParams') if mat.flags & FLAG_ANGLE_FADE else None
            t = mat.textures[0] if mat.textures else None
            timg = tex.get(t['hash']) if t else None
            P = p.pos @ M[:3, :3].T + M[:3, 3]
            N = p.nrm @ np.linalg.inv(M[:3, :3]) if p.nrm is not None else np.zeros_like(P)
            N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
            sx = (P[:, ax] - x0) / span * size
            sy = size - (P[:, ay] - y0) / span * size
            uv = p.uvs[0] * [su, sv] + [tu, tv]
            col = (p.col / 127.0) if p.col is not None else np.ones((len(P), 4))
            tri = p.idx.reshape(-1, 3)
            for a, b, c in tri:
                xa, ya = sx[[a, b, c]], sy[[a, b, c]]
                area = (xa[1] - xa[0]) * (ya[2] - ya[0]) - (xa[2] - xa[0]) * (ya[1] - ya[0])
                if abs(area) < 1e-9:
                    continue
                if mat.cull == 1029 and area > 0:        # screen y down: counter-clockwise = area < 0
                    continue
                if mat.cull == 1028 and area < 0:
                    continue
                lo_x, hi_x = int(max(0, np.floor(xa.min()))), int(min(size - 1, np.ceil(xa.max())))
                lo_y, hi_y = int(max(0, np.floor(ya.min()))), int(min(size - 1, np.ceil(ya.max())))
                if lo_x > hi_x or lo_y > hi_y:
                    continue
                yy, xx = np.mgrid[lo_y:hi_y + 1, lo_x:hi_x + 1]
                px, py = xx.ravel() + 0.5, yy.ravel() + 0.5
                w1 = ((xa[2] - xa[0]) * (py - ya[0]) - (ya[2] - ya[0]) * (px - xa[0])) / -area
                w2 = ((xa[1] - xa[0]) * (py - ya[0]) - (ya[1] - ya[0]) * (px - xa[0])) / area
                w0 = 1 - w1 - w2
                inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
                if not inside.any():
                    continue
                bw = np.stack([w0, w1, w2], 1)[inside]
                idx = [a, b, c]
                fuv = bw @ uv[idx]
                fc = bw @ col[idx]
                rgba = _sample_tex(timg, fuv, t['wrap_s'], t['wrap_t']) if timg is not None else np.ones((len(bw), 4))
                rgba = rgba * fc * gain
                if fade is not None:
                    n = bw @ N[idx]
                    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
                    fres = 1 - np.abs(n @ cam)
                    rgba[:, 3] *= np.maximum(1 - (fade[0] + (fade[1] - fade[0]) * fres), 0)
                ys, xs = yy.ravel()[inside], xx.ravel()[inside]
                if mat.alpha_func == 0x204:                 # alpha test: greater than ref / 255
                    keep = rgba[:, 3] * 255 > mat.ref_alpha
                    ys, xs, rgba = ys[keep], xs[keep], rgba[keep]
                src = rgba[:, :3] * rgba[:, 3:4]
                if mat.dst == 2:
                    img[ys, xs] += src
                elif mat.dst == 3:
                    img[ys, xs] -= src
                elif mat.dst == 1:
                    img[ys, xs] = img[ys, xs] * (1 - rgba[:, 3:4]) + src
                else:
                    img[ys, xs] = rgba[:, :3]
    return np.clip(img, 0, 1)


def preview(d, out_png, size=256):
    from PIL import Image, ImageDraw
    meshes, tex, o, bones, anim = _load_folder(d)
    frames = o.frames
    shots = sorted({0, frames // 4, frames // 2, (3 * frames) // 4})
    # common bounds over the frames and both views
    pts = []
    for fr in shots:
        w = omo.world(o, bones, fr)
        for m in meshes:
            M = np.array(w[bones[m.bone][0]])
            for p in m.polygons:
                pts.append(p.pos @ M[:3, :3].T + M[:3, 3])
    pts = np.concatenate(pts)
    rows = []
    labels = []
    for only in [None] + list(range(len(meshes))):
        row = []
        for view in ('side', 'front'):
            ax, ay, _ = VIEWS[view]
            lo, hi = pts[:, [ax, ay]].min(0), pts[:, [ax, ay]].max(0)
            span = (hi - lo).max() * 1.1 + 1e-6
            c = (lo + hi) / 2
            bounds = ((c[0] - span / 2, c[1] - span / 2), span)
            for fr in (shots if view == 'side' else shots[len(shots) // 2:len(shots) // 2 + 1]):
                row.append((render(meshes, tex, o, bones, anim, fr, view, size, bounds, only) * 255).astype(np.uint8))
                labels.append('%s %s f%d' % ('all' if only is None else meshes[only].name, view, fr))
        rows.append(np.concatenate(row, 1))
    sheet = Image.fromarray(np.concatenate(rows, 0))
    dr = ImageDraw.Draw(sheet)
    ncol = len(rows[0][0]) // size
    for i, lab in enumerate(labels):
        dr.text(((i % ncol) * size + 3, (i // ncol) * size + 2), lab, fill=(255, 255, 0))
    sheet.save(out_png)
    return out_png


def verify(d, src_model=None, log=print):
    """re-read everything written in folder d with the repo's readers; round trips; returns
    a summary dict"""
    ok = True
    res = {}
    raw = open(d + '/model.nud', 'rb').read()
    meshes = nud.read(d + '/model.nud')
    again = nud.write(meshes)
    same = again[:0x20] == raw[:0x20] and again[0x30:] == raw[0x30:]
    log('  nud: %d meshes, %d verts, %d tris; rewrite identical (header sphere aside): %s' % (
        len(meshes), sum(p.nv for m in meshes for p in m.polygons),
        sum(len(p.idx) // 3 for m in meshes for p in m.polygons), same))
    ok &= same
    nd, texs = nut.load(d + '/model.nut')
    res['textures'] = []
    for t in texs:
        img = nut.decode(nd, t)
        line = '  nut: 0x%08X %dx%d fmt 0x%X' % (t.tex_id, t.w, t.h, t.fmt)
        if src_model is not None:
            i = t.tex_id - src_model.tex_base
            ref = dds_rgba(src_model.emb[i][1]).astype(float)
            err = np.abs(img.astype(float) - ref)
            mse = (err ** 2).mean()
            psnr = 10 * np.log10(255 ** 2 / max(mse, 1e-9))
            line += ' vs EMB %s: PSNR %.1f dB, max err %d' % (src_model.emb[i][0], psnr, err.max())
            ok &= psnr > 28
        log(line)
        res['textures'].append(t.tex_id)
    ids = {t.tex_id for t in texs}
    for m in meshes:
        for p in m.polygons:
            for mat in p.materials:
                for t in mat.textures:
                    ok &= t['hash'] in ids
    od = open(d + '/model.omo', 'rb').read()
    o = omo.Omo(od)
    rt = o.encode() == od
    bones = omo.vbn_read(d + '/model.vbn')
    hb = {h for _n, _p, h in bones}
    nodes_ok = all(n[1] in hb for n in o.nodes) and len(o.nodes) == len(bones)
    log('  omo: %d frames, %d nodes (flags %s); re-encode identical: %s; every node a vbn bone: %s' % (
        o.frames, len(o.nodes), ' '.join('%08X' % n[0] for n in o.nodes), rt, nodes_ok))
    ok &= rt and nodes_ok
    if src_model is not None:
        # the bone animation against the XV2 one, as world matrices (row vectors there)
        sk = src_model.emo.skeleton
        worst = 0.0
        for fr in range(0, o.frames, max(1, o.frames // 10)):
            local = {}
            for b in sk.bones:
                bi = src_model.obj.skeleton.index(b.name) if src_model.obj_anim is not None else -1
                trs = src_model.obj_anim.sample_trs(bi, fr) if bi >= 0 else None
                local[b.index] = xv2.trs_rowmat(*trs) if trs is not None else b.matrix
            xw = sk.world(local)
            sw = omo.world(o, bones, fr)
            for b in sk.bones:
                m_s = np.array(sw[b.name])
                m_x = xw[b.index].T.copy()
                m_x[:3, 3] *= src_model.scale
                worst = max(worst, np.abs(m_s - m_x).max() / max(1.0, np.abs(m_x).max()))
        log('  omo vs obj.ema world matrices: worst relative error %.4f' % worst)
        ok &= worst < 0.01
    md = open(d + '/model.mta', 'rb').read()
    if md:
        a = mta.read(md)
        mhash = set()
        for m in meshes:
            for p in m.polygons:
                for mat in p.materials:
                    h = dict(mat.props).get('NU_materialHash')
                    if h:
                        mhash.add(struct.unpack('>I', struct.pack('>f', h[0]))[0])
        linked = all(e['hash'] in mhash for e in a['mats'])
        again = mta.write(a['frames'], [dict(name=e['name'], hash=e['hash'], props=[
            dict(name=p['name'], values=p['values'], u1=p['u1'], u2=p['u2'], type=p['type']) for p in e['props']])
            for e in a['mats']], rate=a['rate'], unk=a['unk'])
        log('  mta: %d frames, %d materials (%s); every material a NUD NU_materialHash: %s; rewrite identical: %s' % (
            a['frames'], len(a['mats']), ', '.join('%s: %s' % (e['name'], '+'.join(p['name'][3:] for p in e['props']))
                                                   for e in a['mats']), linked, again == md))
        ok &= linked and again == md
    else:
        log('  mta: empty (no material animation)')
    x = xmb.parse(open(d + '/model.xmb', 'rb').read())
    log('  xmb: %s' % [(n, p) for n, p in x if p][:2])
    vb = open(d + '/model.vbn', 'rb').read()
    log('  vbn: %d bones %s' % (len(bones), [n for n, _p, _h in bones]))
    ok &= vb[:4] == b' NBV'
    res['ok'] = bool(ok)
    return res


# ---------------------------------------------------------------- CLI
def folder_name(name, prefix):
    tail = name.split('_', 1)[1] if '_' in name else name
    tail = ''.join(w[:1].upper() + w[1:] for w in tail.replace('-', '_').split('_') if w)
    return (prefix or 'Eff') + tail


def convert(src, pattern, out, prefix=None, scale=SCALE, tex_base=TEX_BASE, anim=0, preview_dir=None, matcol1='mean',
            skip=(), plain=False):
    emos = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(src, '*.emo')))
    names = emos if pattern == 'all' else [n for n in emos if fnmatch.fnmatch(n, pattern)]
    if not names:
        sys.exit('no EMO matching %r in %s' % (pattern, src))
    done = []
    for name in names:
        k = emos.index(name)
        m = Model(src, name, folder_name(name, prefix), tex_base + 0x10 * k, scale, anim, matcol1, skip, plain)
        d = m.write(out)
        meshes = m.meshes_written
        print('%s -> %s' % (name, d))
        print('  %d bones, %d frames, textures %s' % (len(m.bones), m.frames,
                                                       ['0x%08X' % (m.tex_base + i) for i in range(len(m.emb))]))
        for mesh in meshes:
            p = mesh.polygons[0]
            mat = p.materials[0]
            print('  mesh %-12s bone %-12s verts %4d tris %4d flags 0x%08X src/dst %d/%d cull %d tex 0x%08X %s' % (
                mesh.name, m.bones[mesh.bone][0], len(p.pos), len(p.idx) // 3, mat.flags, mat.src, mat.dst, mat.cull,
                mat.textures[0]['hash'] if mat.textures else 0,
                ' '.join('%s=%s' % (n[3:], [round(v, 3) for v in vals[:4]]) for n, vals in mat.props
                         if n != 'NU_materialHash' and n != 'NU_effRotUV')))
        for n in sorted(set(m.notes)):
            print('  note:', n)
        if preview_dir:
            verify(d, m)
            os.makedirs(preview_dir, exist_ok=True)
            print('  preview:', preview(d, os.path.join(preview_dir, m.folder + '.png')))
        done.append((m, d))
    return done


def main():
    args = sys.argv[1:]
    opts = {}
    pos = []
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if pos[:1] == ['verify']:
        for d in pos[1:]:
            d = d.rstrip('/')
            print(d)
            src_model = None
            if 'src' in opts:
                # find the EMO this folder came from by its texture ids
                emos = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(opts['src'], '*.emo')))
                _nd, texs = nut.load(d + '/model.nut')
                base = int(opts.get('tex-base', '0'), 0) or TEX_BASE
                k = (texs[0].tex_id - base) // 0x10 if texs else -1
                if 0 <= k < len(emos):
                    src_model = Model(opts['src'], emos[k], os.path.basename(d), base + 0x10 * k,
                                      float(opts.get('scale', SCALE)))
            r = verify(d, src_model)
            print('  ok' if r['ok'] else '  PROBLEMS')
            if 'preview' in opts:
                os.makedirs(opts['preview'], exist_ok=True)
                print('  preview:', preview(d, os.path.join(opts['preview'], os.path.basename(d) + '.png')))
        return
    if len(pos) != 3:
        sys.exit(__doc__)
    convert(pos[0], pos[1], pos[2], opts.get('prefix'), float(opts.get('scale', SCALE)),
            int(opts.get('tex-base', hex(TEX_BASE)), 0), int(opts.get('anim', 0)), opts.get('preview'),
            opts.get('matcol1', 'mean'), [x for x in opts.get('skip', '').split(',') if x], opts.get('plain') == '1')


if __name__ == '__main__':
    main()
