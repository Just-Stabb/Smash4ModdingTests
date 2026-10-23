#!/usr/bin/env python3
"""Xenoverse 2 ETR traces (the Kamehameha's beam body) -> Smash 4 effect model folders.

  python3 tools/xv2_trace_to_nud.py PKG_DIR OUT_DIR [--prefix EffSupamarioKame] [--speed 2.0]
                                    [--scale 8.5] [--tex-base 0x15141A30] [--preview DIR]

Each .etr in the package (Kmh_Beam.etr -> OUT_DIR/EffSupamarioKameBeam/) becomes one model with a
mesh per trace node. An XV2 trace is drawn behind its bone (TRS, the moving beam head) as the head
travels: it grows for ExtrudeDuration frames, then holds HoldDuration frames while its keyframes
thin and fade it. Smash 4 has no trace emitter, so the trace is a model that does the same in
place, from the spawn point forward (+Z, the head's direction):
- a node with ExtrudeShapePoints (a closed cross-section: the outer tubes) -> a tube of radius
  Scale; a node without (a flat ribbon, AutoOrientation: camera facing) -> two crossed ribbons of
  width 2 Scale, one upright (seen from the side camera) and one flat;
- the mesh is 1 unit long along +Z on its own bone; model.omo scales the bone: Z = speed x frame
  while extruding (speed in Smash units a frame: XV2's comes from the skill, not the effect; the
  move's projectile should match it), then held; X / Y follow the node's Scale keyframes
  (DefaultEnd: over the hold) relative to the base Scale;
- texture: the node's sampler (beam00 / ring_beamCor / T2_UV01) as BC3, U around / across, V along
  the trace, repeated along the length to keep the texture's aspect (NU_effScaleUV V animated with
  the length) and scrolled at the sampler's ScrollSpeed (NU_effTransUV);
- alpha: ShapeStartToEnd keyframes (times 0..HoldDuration read as the start..end of the trace) as
  the vertex alpha along the length; DefaultEnd Color1_Transparency over the hold as
  NU_effColorGain's alpha (model.mta);
- material: XV2 TraceNML / TraceNML2 are normal blend, two-sided: src 5 / dst 1, cull none, the
  effect shader with vertex colour (0xB0201100), as the game's alpha effect models.
"""
import argparse
import math
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
import xv2vfx  # noqa: E402
from xv2_to_nud import SCALE, FLAG_BASE, effect_xmb, float_hash, omo_new, omo_node, vbn_le  # noqa: E402
from xv2emb import Emb, dds_rgba  # noqa: E402

TEX_BASE = 0x15141A30          # after the EMO models' 0x15141A00-0x15141A2F; 0x10 per trace
SPEED = 2.0                    # Smash units a frame the trace grows (the beam head's speed)
SEGMENTS = 16                  # rings along the length


def kf_curve(kv, n, default):
    """a keyframed value sampled at 0..n-1 (frames / positions), held past its ends"""
    if kv is None or not kv['Keyframes']:
        return np.full(n, float(default))
    ks = sorted((k['Time'], k['Value']) for k in kv['Keyframes'])
    return np.interp(np.arange(n, dtype=float), [k[0] for k in ks], [k[1] for k in ks])


def find_kv(node, target, interp=None):
    for kv in node['KeyframedValues']:
        if kv['Target'] == target and (interp is None or kv['ETR_InterpolationType'] == interp):
            return kv
    return None


def tube(points, radius, alpha_along):
    """a tube along +Z (0..1) through the cross-section points (X, Y): pos, nrm, uv, alpha, tris"""
    pts = np.array([[p['X'], p['Y']] for p in points], float)
    closed = np.allclose(pts[0], pts[-1])
    if not closed:
        pts = np.vstack([pts, pts[:1]])
    m = len(pts)
    pos, nrm, uv, al = [], [], [], []
    for s in range(SEGMENTS + 1):
        z = s / SEGMENTS
        for i, (x, y) in enumerate(pts):
            pos.append((x * radius, y * radius, z))
            ln = math.hypot(x, y) or 1.0
            nrm.append((x / ln, y / ln, 0.0))
            uv.append((i / (m - 1), z))
            al.append(alpha_along(z))
    tris = []
    for s in range(SEGMENTS):
        for i in range(m - 1):
            a, b = s * m + i, s * m + i + 1
            c, d = a + m, b + m
            tris += [(a, b, c), (b, d, c)]
    return np.array(pos), np.array(nrm), np.array(uv), np.array(al), np.array(tris)


def ribbon(half, alpha_along):
    """two crossed ribbons along +Z: upright (in the YZ plane, facing the side camera) and flat"""
    pos, nrm, uv, al, tris = [], [], [], [], []
    for axis, normal in (((0, 1, 0), (1, 0, 0)), ((1, 0, 0), (0, 1, 0))):
        base = len(pos)
        for s in range(SEGMENTS + 1):
            z = s / SEGMENTS
            for k, u in ((0, 0.0), (1, 1.0)):
                w = (2 * u - 1) * half
                pos.append((axis[0] * w, axis[1] * w, z))
                nrm.append(normal)
                uv.append((u, z))
                al.append(alpha_along(z))
        for s in range(SEGMENTS):
            a = base + 2 * s
            tris += [(a, a + 1, a + 2), (a + 1, a + 3, a + 2)]
    return np.array(pos, float), np.array(nrm, float), np.array(uv, float), np.array(al), np.array(tris)


class Trace:
    def __init__(self, pkg, etr_name, folder, tex_base, speed=SPEED, scale=SCALE):
        self.etr = pkg['etr'][etr_name]
        self.name, self.folder, self.tex_base, self.speed, self.scale = etr_name, folder, tex_base, speed, scale
        c = xv2vfx._container(pkg, 'TBIND')
        self.emb = list(Emb(open(os.path.join(pkg['dir'], c['TextureEmbPath']), 'rb').read()))
        nodes = self.etr['Nodes']
        self.frames = max(n['StartTime'] + n['ExtrudeDuration'] + n['HoldDuration'] for n in nodes) + 1
        self.bones = [('TopN', -1)] + [('Trace%d' % i, 0) for i in range(len(nodes))]
        self.bones = [(n, p, zlib.crc32(n.encode()) & 0xFFFFFFFF) for n, p in self.bones]

    def node_curves(self, node):
        """per frame: (length, width scale, alpha) of a node"""
        e, h, t0 = node['ExtrudeDuration'], node['HoldDuration'], node['StartTime']
        base = node['Scale'] or 1.0
        scale_hold = kf_curve(find_kv(node, 'Scale', 'DefaultEnd'), h + 1, base)
        alpha_hold = kf_curve(find_kv(node, 'Color1_Transparency', 'DefaultEnd'), h + 1, 1.0)
        out = []
        for fr in range(self.frames):
            t = fr - t0
            if t < 0:
                out.append((0.01, 1.0, 0.0))
                continue
            length = self.speed * max(min(t, e), 0.5)
            k = min(max(t - e, 0), h)
            w = max(scale_hold[k] / base, 0.0)
            a = float(alpha_hold[k]) if t >= e else float(alpha_hold[0])
            if t > e + h:
                w, a = 0.0, 0.0
            out.append((length, w, a))
        return out

    def meshes(self):
        meshes, anims, texs = [], [], {}
        for i, node in enumerate(self.etr['Nodes']):
            h = node['HoldDuration']
            along = kf_curve(find_kv(node, 'Color1_Transparency', 'ShapeStartToEnd'), h + 1, 1.0)

            def alpha_along(z, along=along, h=h):
                return float(np.interp(z * h, np.arange(h + 1), along))
            radius = node['Scale'] * self.scale
            if node.get('ExtrudeShapePoints'):
                pos, nrm, uv, al, tris = tube(node['ExtrudeShapePoints'], radius, alpha_along)
            else:
                pos, nrm, uv, al, tris = ribbon(radius, alpha_along)
            ref = node['TextureEntryRef'][0] if node['TextureEntryRef'] else None
            smp = self.etr['Textures'][ref] if ref is not None else None
            emb_index = smp['EmbIndex'] if smp else 0
            texs[emb_index] = self.tex_base + emb_index
            poly = nud.Polygon()
            poly.pos = pos
            poly.nrm = nrm
            col = np.ones((len(pos), 4)) * 127.0
            col[:, :3] *= np.array(node['Color1'], float)
            col[:, 3] = np.clip(al, 0, 1) * 127.0
            poly.col = np.round(col)
            poly.uvs = [uv]
            poly.idx = tris.reshape(-1)
            # texture repeats along the length: the texture's aspect over the tube's circumference
            # (or the ribbon's width) at full length
            img = dds_rgba(self.emb[emb_index][1])
            across = (2 * math.pi * radius) if node.get('ExtrudeShapePoints') else 2 * radius
            v_per_unit = img.shape[1] / img.shape[0] / max(across, 1e-3)
            curves = self.node_curves(node)
            su, sv = smp['ScrollState'].get('ScrollSpeed_U', 0.0), smp['ScrollState'].get('ScrollSpeed_V', 0.0)
            mat = nud.Material(FLAG_BASE, 5, 1, 0, 0, 0, 0, 0)
            mat.textures.append(dict(hash=self.tex_base + emb_index, map_mode=0, wrap_s=1, wrap_t=1, min_f=3,
                                     mag_f=2, mip=6, unk=0, unk2=0))
            hbits, hval = float_hash('%s/%s' % (self.folder, i))
            gains = [[1.0, 1.0, 1.0, a] for _l, _w, a in curves]
            scales = [[1.0, max(length * v_per_unit, 0.01), 0.0, 0.0] for length, _w, _a in curves]
            trans = [[su * fr, sv * fr, 0.0, 0.0] for fr in range(self.frames)]
            mat.props = [('NU_effRotUV', [0.0, 0.0, 0.0, 0.0]), ('NU_effScaleUV', list(scales[0])),
                         ('NU_effTransUV', list(trans[0])), ('NU_effColorGain', list(gains[0])),
                         ('NU_materialHash', [hval, 0.0, 0.0, 0.0])]
            poly.materials = [mat]
            meshes.append(nud.Mesh('Trace%d_%s' % (i, node['MaterialRef'] or 'mat'), [poly], bone=i + 1, bind=8))
            anims.append(dict(name='%s_trace%d' % (self.folder, i), hash=hbits, props=[
                dict(name='NU_effColorGain', values=gains, u2=0),
                dict(name='NU_effScaleUV', values=scales, u2=0),
                dict(name='NU_effTransUV', values=trans, u2=0)]))
        return meshes, anims, texs

    def omo(self):
        o = omo_new(self.frames)
        f = self.frames
        omo_node(o, self.bones[0][2], [(0, 0, 0)] * f, [(0, 0, 0, 1)] * f, [(1, 1, 1)] * f)
        for i, node in enumerate(self.etr['Nodes']):
            curves = self.node_curves(node)
            omo_node(o, self.bones[i + 1][2], [(0, 0, 0)] * f, [(0, 0, 0, 1)] * f,
                     [(max(w, 1e-3), max(w, 1e-3), length) for length, w, _a in curves])
        return o

    def write(self, out_dir):
        d = os.path.join(out_dir, self.folder)
        os.makedirs(d, exist_ok=True)
        meshes, anims, texs = self.meshes()
        maxlen = max(n['ExtrudeDuration'] for n in self.etr['Nodes']) * self.speed
        for m in meshes:
            p = m.polygons[0].pos.copy()
            p[:, 2] *= maxlen
            m.sphere = nud._sphere(p)
        data = bytearray(nud.write(meshes))
        allp = np.concatenate([m.polygons[0].pos * [1, 1, maxlen] for m in meshes])
        struct.pack_into('>4f', data, 0x20, *nud._sphere(allp))
        open(d + '/model.nud', 'wb').write(bytes(data))
        open(d + '/model.nut', 'wb').write(nut.write_ntwu(
            [(tid, 0x33, dds_rgba(self.emb[ei][1])) for ei, tid in sorted(texs.items())]))
        open(d + '/model.vbn', 'wb').write(vbn_le(self.bones))
        open(d + '/model.omo', 'wb').write(self.omo().encode())
        open(d + '/model.mta', 'wb').write(mta.write(self.frames, anims, rate=60, unk=1))
        open(d + '/model.xmb', 'wb').write(effect_xmb())
        self.meshes_written = meshes
        return d


def convert(pkg_dir, out_dir, prefix='EffSupamarioKame', speed=SPEED, scale=SCALE, tex_base=TEX_BASE):
    pkg = xv2vfx.load_package(pkg_dir)
    done = []
    for k, name in enumerate(sorted(pkg['etr'])):
        folder = prefix + os.path.splitext(name)[0].split('_', 1)[-1]
        t = Trace(pkg, name, folder, tex_base + 0x10 * k, speed, scale)
        d = t.write(out_dir)
        print('%s -> %s: %d frames, %d meshes, %.0f units long' % (
            name, d, t.frames, len(t.meshes_written), speed * max(n['ExtrudeDuration'] for n in t.etr['Nodes'])))
        for m in t.meshes_written:
            p = m.polygons[0]
            print('   %-22s verts %4d tris %4d' % (m.name, len(p.pos), len(p.idx) // 3))
        done.append(d)
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pkg')
    ap.add_argument('out')
    ap.add_argument('--prefix', default='EffSupamarioKame')
    ap.add_argument('--speed', type=float, default=SPEED)
    ap.add_argument('--scale', type=float, default=SCALE)
    ap.add_argument('--tex-base', type=lambda s: int(s, 0), default=TEX_BASE)
    ap.add_argument('--preview')
    a = ap.parse_args()
    done = convert(a.pkg, a.out, a.prefix, a.speed, a.scale, a.tex_base)
    if a.preview:
        import xv2_to_nud
        os.makedirs(a.preview, exist_ok=True)
        for d in done:
            r = xv2_to_nud.verify(d, None)
            print(d, 'ok' if r['ok'] else 'PROBLEMS')
            print('  preview:', xv2_to_nud.preview(d, os.path.join(a.preview, os.path.basename(d) + '.png')))


if __name__ == '__main__':
    main()
