#!/usr/bin/env python3
"""Xenoverse 2 EMP particle effects -> Smash 4 ptcl emitter sets (one set per EMP, split at 16
emitters), built from template emitters of the target ptcl.

  python3 tools/xv2_to_ptcl.py PKG_DIR BASE.ptcl OUT.ptcl [--prefix PtcSupamarioKmh] [--unit 8.5]
                               [--emp Kmh_Crg.emp ...] [--preview DIR]

PKG_DIR: the extracted .vfxpackage (the .eepk, its .pbind.emb / .ptcl.emb / .ptcl.emm).
Prints each new set (0-based index; .efc entries name it 1-based) and its emitters.

Mapping (docs/xv2-vfx-format.md for the EMP side, docs/ptcl-format.md for the eft side):
- every EMP Emission node becomes one emitter, cloned from a template emitter in BASE whose shader
  fits: AutoOriented (camera billboard) -> particle type 0, AutoOriented_VisibleOnSpeed (streak along
  its velocity) -> type 3, ShapeDraw (a ring / arc drawn as a strip) -> type 1 (a polygon in the
  emitter's XY plane, turned by the emitter transform) with the ring drawn into the texture.
  ConeExtrude ribbons and Mesh emissions are skipped (listed). Normal-blend camera billboards use a
  normal-blend template; everything else an additive one, blend set from the EMM material
  (normal blend on streaks / rings becomes additive: no normal template of those types in Mario's
  file);
- the texture: the sampler's first sprite-sheet cell (or its static UV rectangle), as BC4 with the
  shape in R (the templates' format: R = G = B, the game's fx textures): R = alpha x brightness, the
  texture's mean tint moved into the particle colour;
- timing: the emitter is active from the sum of its ancestors' StartTime; its parent's Burst every
  BurstFrequency frames for the parent's Lifetime (once if 0; forever if a node above loops), each
  time Burst particles; particle life = Lifetime (+ variance);
- shape: Point -> point volume, velocity along the node's up vector with the cone Angle;
  Sphere -> sphere volume (radius Size), radial velocity; Circle / Square -> circle volume.
  Velocities are XV2 units per second (/ 60), Acceleration modifiers become gravity, Drag the air
  resistance; Vortex / Translation / Jitter / Attract are not converted;
- the node rotations and positions above an emission become the emitter transform;
- curves: Color1 RGB keyframes -> the 3-key colour animation (both colour tracks the same),
  Color1_Transparency -> the 3-key alpha, ScaleBase (or ScaleXY with EnableScaleXY) -> base scale x
  the 3-key scale ratio, fitted by least squares on the keyframed curve (XV2 times are percent of
  the particle's life, as eft's sections);
- sizes and velocities x UNIT Smash units per XV2 unit (8.5, as tools/xv2_to_nud.py; the EEPK's
  per-part scale goes to the ACMD effect size).
"""
import argparse
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import ptcl  # noqa: E402
import xv2emb  # noqa: E402
import xv2vfx  # noqa: E402

UNIT = 8.5
FOREVER = 0x7FFFFFFF
MAX_EMITTERS = 16                  # the most any vanilla set has
# (particle type, blend class) -> (set, emitter) in Mario's / Supamario's ptcl: simple emitters,
# one BC4 texture, no flipbook, both colour tracks key-animated (the normal one: colour 0 only)
TEMPLATES = {(0, 'add'): ('PtcMarioPumpMax', 'flare1'),
             (0, 'nml'): ('PtcMarioFireball', 'PtcMarioFireballSmoke_Copy2'),
             (3, 'add'): ('PtcMarioSupermant2', 'line1'),
             (1, 'add'): ('PtcMarioFireballShoot', 'PtcMarioRireballShoot')}
BLEND = {'normal': 0, 'add': 1, 'sub': 2}
SAMPLER_CLAMP = 0x22000100          # the vanilla sampler word of clamped textures (cross1, flare1)


# ------------------------------------------------------------------ curves
def curve(node, target, default):
    """the keyframed value as 101 samples over the particle's life (percent), else the constant"""
    for kv in node['KeyframedValues']:
        if kv['Target'] == target and kv['Keyframes']:
            ks = sorted((k['Time'], k['Value']) for k in kv['Keyframes'])
            t = np.arange(101.0)
            if not kv.get('Interpolate', True):
                idx = np.searchsorted([k[0] for k in ks], t, side='right') - 1
                return np.array([ks[max(i, 0)][1] for i in idx])
            return np.interp(t, [k[0] for k in ks], [k[1] for k in ks])
    return np.full(101, float(default))


def three_key(f):
    """eft's 3-key ramp (v0 at 0 -> v1 at s1, held to s2, -> v2 at 100) fitted to f (101 samples or
    an [101, n] array): (v0, v1, v2, s1, s2), s in percent"""
    f = np.asarray(f, float)
    if f.ndim == 1:
        f = f[:, None]
    t = np.arange(101.0)[:, None]
    best = None
    for s1 in range(0, 101, 5):
        for s2 in range(s1, 101, 5):
            v0, v2 = f[0], f[100]
            v1 = f[s1:s2 + 1].mean(0)
            up = v0 + (v1 - v0) * t / s1 if s1 else np.broadcast_to(v1, f.shape)
            down = v1 + (v2 - v1) * (t - s2) / (100 - s2) if s2 < 100 else np.broadcast_to(v1, f.shape)
            g = np.where(t < s1, up, np.where(t <= s2, v1, down))
            err = ((g - f) ** 2).sum()
            if best is None or err < best[0] - 1e-9:
                best = (err, v0, v1, v2, s1, s2)
    return best[1:]


def color_fit(rgb):
    """eft's 3-key colour animation (k0 until s1, -> k1 at s2, -> k2 at s3, then k2), fitted to
    [101, 3]: ([k0, k1, k2], [s1, s2, s3])"""
    t = np.arange(101.0)
    best = None
    for s1 in range(0, 101, 10):
        for s2 in range(s1, 101, 10):
            for s3 in range(s2, 101, 10):
                ks = [rgb[s1], rgb[s2], rgb[s3]]
                g = np.array([np.interp(x, [s1, s2, s3], [0, 1, 2]) for x in t])
                model = np.array([ks[0] + (ks[1] - ks[0]) * min(u, 1) + (ks[2] - ks[1]) * max(u - 1, 0)
                                  for u in g])
                err = ((model - rgb) ** 2).sum()
                if best is None or err < best[0] - 1e-9:
                    best = (err, ks, [s1, s2, s3])
    return best[1], best[2]


# ------------------------------------------------------------------ textures
def emb_images(pkg):
    """texture name -> RGBA float array, from the PBIND container's texture EMB"""
    c = xv2vfx._container(pkg, 'PBIND')
    data = open(os.path.join(pkg['dir'], c['TextureEmbPath']), 'rb').read()
    return {n: xv2emb.dds_rgba(b).astype(np.float32) / 255 for n, b in xv2emb.Emb(data)}


def first_cell(img, sampler):
    """the sampler's first sprite-sheet cell, or its static UV rectangle"""
    ks = (sampler.get('ScrollState') or {}).get('Keyframes') or []
    if not ks:
        return img
    k = ks[0]
    h, w = img.shape[:2]
    u0, v0 = k['ScrollU'] % 1.0, k['ScrollV'] % 1.0
    su, sv = abs(k['ScaleU']) or 1.0, abs(k['ScaleV']) or 1.0
    x0, y0 = int(round(u0 * w)), int(round(v0 * h))
    x1, y1 = min(w, x0 + max(4, int(round(su * w)))), min(h, y0 + max(4, int(round(sv * h))))
    return img[y0:y1, x0:x1]


def pow2(n, lo=16, hi=256):
    p = lo
    while p < n and p < hi:
        p *= 2
    return p


def resize(img, w, h):
    from PIL import Image
    chans = [np.array(Image.fromarray(img[..., c]).resize((w, h), Image.BILINEAR)) for c in range(img.shape[2])]
    return np.stack(chans, 2)


def shape_texture(img):
    """(R shape [h, w] in 0..1, tint rgb): the texture's alpha-weighted mean colour (brightest channel
    1) as the tint, and per pixel alpha x the colour's projection on it, so R x tint ~ rgb x alpha"""
    rgb, a = img[..., :3], img[..., 3]
    wsum = a.sum()
    tint = (rgb * a[..., None]).reshape(-1, 3).sum(0) / wsum if wsum > 0 else np.ones(3)
    tint = np.clip(tint / max(tint.max(), 1e-6), 0, 1)
    return np.clip(a * (rgb @ tint) / float(tint @ tint), 0, 1), tint


def ring_texture(strip, radius, width, points, size=256):
    """a ShapeDraw ring drawn into a square: the strip texture's profile across its width (V) around
    the outline's arc; radius / width in the same units"""
    prof = strip.mean(1)                                   # [h] across the strip (V)
    outer = radius + width / 2
    yy, xx = np.mgrid[0:size, 0:size]
    x = (xx + 0.5) / size * 2 - 1
    y = 1 - (yy + 0.5) / size * 2
    r = np.hypot(x, y) * outer
    v = (r - (radius - width / 2)) / max(width, 1e-6)
    inside = (v >= 0) & (v <= 1)
    vi = np.clip((v * (len(prof) - 1)).astype(int), 0, len(prof) - 1)
    img = np.where(inside, prof[vi], 0.0)
    # open arcs: keep the angles the outline covers
    ang = np.degrees(np.arctan2([p['Y'] for p in points], [p['X'] for p in points])) % 360
    closed = len(points) > 2 and math.hypot(points[0]['X'] - points[-1]['X'], points[0]['Y'] - points[-1]['Y']) < 1e-3
    if not closed and len(points) > 1:
        steps = np.diff(np.unwrap(np.radians(ang)))
        span = abs(np.degrees(steps.sum()))
        start = ang[0] if steps.sum() > 0 else ang[-1]
        pa = (np.degrees(np.arctan2(y, x)) - start) % 360
        img = np.where(pa <= span, img, 0.0)
    return img


# ------------------------------------------------------------------ conversion
def emission_kind(node):
    t = node['NodeSpecificType']
    if t == 'AutoOriented':
        return 0
    if t == 'AutoOriented_VisibleOnSpeed':
        return 3
    if t == 'ShapeDraw':
        return 1
    return None


def blend_of(pkg, node):
    mat = xv2vfx.resolve_material(pkg, 'PBIND', node['EmissionNode']['Texture']['MaterialID'])
    if not mat:
        return 'add'
    p = xv2vfx.emm_params(mat)
    if p.get('AlphaBlend') in (1, True):
        return {0: 'normal', 1: 'add', 2: 'sub'}.get(p.get('AlphaBlendType'), 'add')
    return 'normal'


def euler_matrix(deg):
    x, y, z = np.radians(deg)
    cx, cy, cz, sx, sy, sz = math.cos(x), math.cos(y), math.cos(z), math.sin(x), math.sin(y), math.sin(z)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def matrix_euler(m):
    """(x, y, z) radians of Rz.Ry.Rx"""
    y = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 0.9999:
        x = math.atan2(m[2, 1], m[2, 2])
        z = math.atan2(m[1, 0], m[0, 0])
    else:
        x, z = math.atan2(-m[1, 2], m[1, 1]), 0.0
    return x, y, z


HORIZON = 300


def simulate(emp, horizon=HORIZON):
    """{id(emission node): [spawn frame, ...]} for the EMP's tree run for horizon frames: a node is
    active StartTime after its parent spawns it, for Lifetime frames (restarting with Loop); while
    active it spawns Burst of each child every BurstFrequency frames (once if 0), at most
    MaxInstances of a child alive at once; an emission's instance is one particle"""
    spawns = {}

    def run(node, t0, depth=0):
        if depth > 8:
            return
        life = max(1, node['Lifetime'])
        starts = [t0 + node['StartTime']]
        if 'Loop' in node['NodeFlags_names']:
            while starts[-1] + life < horizon:
                starts.append(starts[-1] + life)
        for a in starts:
            if a >= horizon:
                break
            if node['NodeType'] == 'Emission':
                spawns.setdefault(id(node), []).append(a)
            freq = node['BurstFrequency']
            ticks = range(a, min(a + life, horizon), freq) if freq else [a]
            for kid in node['ChildParticleNodes']:
                cap = kid['MaxInstances'] if kid['MaxInstances'] > 0 else None
                alive = []
                for t in ticks:
                    alive = [e for e in alive if e > t]
                    for _ in range(max(1, node['Burst'])):
                        if cap is not None and len(alive) >= cap:
                            break
                        alive.append(t + kid['StartTime'] + max(1, kid['Lifetime']))
                        run(kid, t, depth + 1)

    for n in emp['ParticleNodes']:
        run(n, 0)
    return spawns


def schedule(times, loops):
    """(start, end, interval, rate) in eft terms for spawn frames (an emission every interval + 1
    frames, rate particles each, from start until end)"""
    if not times:
        return 0, 1, 0, 0.0
    ts, counts = np.unique(times, return_counts=True)
    start = int(ts[0])
    if len(ts) == 1:
        return start, start + 1, 0, float(counts[0])
    if loops:                                # the steady state: the later half of the run
        later = ts >= HORIZON / 2
        if later.sum() >= 2:
            ts, counts = ts[later], counts[later]
    gap = int(np.median(np.diff(ts)))
    rate = float(np.median(counts))
    end = FOREVER if loops else int(ts[-1]) + 1
    return start, end, max(0, gap - 1), rate


def convert_emission(p, pkg, images, chain, unit, name, spawn_times):
    node = chain[-1]
    kind = emission_kind(node)
    tex = node['EmissionNode']['Texture']
    blend = blend_of(pkg, node)
    tkey = (kind, 'nml' if blend == 'normal' and kind == 0 else 'add')
    sname, ename = TEMPLATES[tkey]
    si = p.find_set(sname)
    k = [p.emitter_name(e['data']) for e in p.sets[si]['emitters']].index(ename)
    em = p.emitter_bytes(si, k)
    notes = []
    if blend == 'normal' and tkey[1] == 'add':
        notes.append('normal blend drawn additive')

    # ---- texture
    refs = [r for r in tex['TextureEntryRef'] if r is not None and r >= 0]
    emp = chain[0]['_emp']
    smp = emp['Textures'][refs[0]] if refs else None
    img = images.get(smp['TextureRef']) if smp else None
    if img is None:
        img = np.ones((16, 16, 4), np.float32)
        notes.append('no texture: white')
    cell = first_cell(img, smp) if smp else img
    shape, tint = shape_texture(cell)
    scale_xy = 'EnableScaleXY' in node['NodeFlags_names']
    if kind == 1:
        pts = node['EmissionNode']['ShapeDraw']['Points']
        rc = curve(node, 'ScaleBase', tex['ScaleBase'])
        wc = curve(node, 'ScaleXY.Y', tex['ScaleXY'][1])
        k = int(np.argmax(rc))
        shape = ring_texture(shape, rc[k], wc[k], pts)
        sx = sy = 2 * rc + wc
    else:
        if scale_xy:
            sx, sy = curve(node, 'ScaleXY.X', tex['ScaleXY'][0]), curve(node, 'ScaleXY.Y', tex['ScaleXY'][1])
        else:
            sx = sy = curve(node, 'ScaleBase', tex['ScaleBase'])
    h, w = shape.shape
    tw, th = pow2(w, hi=256), pow2(h, hi=256)
    if (tw, th) != (w, h):
        shape = resize(shape[..., None].astype(np.float32), tw, th)[..., 0]
    r8 = (np.clip(shape, 0, 1) * 255 + 0.5).astype(np.uint8)
    rgba = np.stack([r8, r8, r8, np.full_like(r8, 255)], 2)
    p.set_texture(em, 0, rgba, 0x34)
    struct.pack_into('>I', em, ptcl.TEXRES + 0x0C, SAMPLER_CLAMP)
    p.set_field(em, 'tex0_uv_scale', [1.0, 1.0])

    # ---- blend, colour, alpha
    p.set_field(em, 'blend_type', BLEND[blend])
    rgb = np.stack([curve(node, 'Color1.' + c, tex['Color1'][i]) for i, c in enumerate('RGB')], 1)
    rgb = np.clip(rgb * tint[None, :], 0, None)
    keys, secs = color_fit(rgb)
    for track in (0, 1):
        if p.field(em, 'color%d_type' % track) == 2:
            p.set_color_keys(em, track, [(*map(float, k), 1.0) for k in keys])
        else:
            p.set_color_keys(em, track, [(*map(float, rgb.mean(0)), 1.0)])
    p.set_field(em, 'color_section1', [secs[0]] * 2)
    p.set_field(em, 'color_section2', [secs[1]] * 2)
    p.set_field(em, 'color_section3', [secs[2]] * 2)
    p.set_field(em, 'color_repeat', [1, 1])
    p.set_field(em, 'color_scale', 1.0)
    alpha = np.clip(curve(node, 'Color1_Transparency', tex['Color1_Transparency']), 0, 1)
    a0, a1, a2, s1, s2 = (float(np.squeeze(v)) for v in three_key(alpha))
    p.set_field(em, 'alpha_init', a0)
    p.set_field(em, 'alpha_diff21', a1 - a0)
    p.set_field(em, 'alpha_diff32', a2 - a1)
    p.set_field(em, 'alpha_section1', s1 / 100)
    p.set_field(em, 'alpha_section2', s2 / 100)

    # ---- scale
    base = np.array([max(sx.max(), 1e-4), max(sy.max(), 1e-4)])
    v0, v1, v2, s1, s2 = three_key(np.stack([sx / base[0], sy / base[1]], 1))
    p.set_field(em, 'scale', [float(b * unit) for b in base])
    p.set_field(em, 'scale_init_ratio', [float(v) for v in v0])
    p.set_field(em, 'scale_diff21', [float(v) for v in v1 - v0])
    p.set_field(em, 'scale_diff32', [float(v) for v in v2 - v1])
    p.set_field(em, 'scale_sections', [int(s1), int(s2)])
    var = tex['ScaleBase_Variance'] / tex['ScaleBase'] if tex['ScaleBase'] else 0.0
    p.set_field(em, 'scale_random', [float(var), float(var)])

    # ---- rotation (in the particle's plane)
    en = node['EmissionNode']
    r0, rv = en.get('StartRotation', 0.0), en.get('StartRotation_Variance', 0.0)
    a, av = en.get('ActiveRotation', 0.0), en.get('ActiveRotation_Variance', 0.0)
    p.set_field(em, 'rotation_init', [0.0, 0.0, math.radians(r0 - rv / 2 if rv else r0)])
    p.set_field(em, 'rotation_random', [0.0, 0.0, math.radians(rv)])
    p.set_field(em, 'rotation_velocity', [0.0, 0.0, math.radians(a)])
    p.set_field(em, 'rotation_velocity_random', [0.0, 0.0, math.radians(av)])

    # ---- timing
    loops = any('Loop' in n['NodeFlags_names'] for n in chain)
    start, end, interval, rate = schedule(spawn_times.get(id(node), []), loops)
    p.set_field(em, 'start_frame', int(start))
    p.set_field(em, 'end_frame', int(end))
    p.set_field(em, 'emit_interval', int(interval))
    p.set_field(em, 'emit_rate', float(rate))
    p.set_field(em, 'ptcl_life', max(1, int(node['Lifetime'])))
    p.set_field(em, 'ptcl_life_random', int(node['Lifetime_Variance']))

    # ---- shape and motion, from the nearest emitter node above
    src = next((n for n in reversed(chain[:-1]) if n['NodeType'] == 'Emitter'), None)
    p.set_field(em, 'volume_type', 0)
    p.set_field(em, 'volume_radius', [0.0, 0.0, 0.0])
    p.set_field(em, 'figure_velocity', 0.0)
    p.set_field(em, 'emitter_velocity', 0.0)
    p.set_field(em, 'init_velocity_random', 0.0)
    p.set_field(em, 'emit_direction', [0.0, 1.0, 0.0])
    p.set_field(em, 'dispersion_angle', 0.0)
    p.set_field(em, 'gravity', [0.0, 0.0, 0.0])
    p.set_field(em, 'air_resistance', 1.0)
    if src is not None:
        e = src['EmitterNode']
        shape_t = src['NodeSpecificType']
        vel = e.get('Velocity', 0.0) * unit / 60
        vrand = e.get('Velocity_Variance', 0.0) * unit / 60
        if shape_t == 'SphericalDistribution':
            size = e.get('Size', 0.0) * unit
            if size > 0:
                p.set_field(em, 'volume_type', 4)
                p.set_field(em, 'volume_radius', [size] * 3)
            p.set_field(em, 'figure_velocity', vel)
        else:
            if shape_t in ('ShapePerimeterDistribution', 'ShapeAreaDistribution'):
                size = e.get('Size', 0.0) * unit
                if size > 0:
                    p.set_field(em, 'volume_type', 1 if shape_t == 'ShapePerimeterDistribution' else 3)
                    p.set_field(em, 'volume_radius', [size, 0.0, size])
            p.set_field(em, 'emitter_velocity', vel)
            p.set_field(em, 'dispersion_angle', float(e.get('Angle', 0.0)))
        if vrand and vel:
            p.set_field(em, 'init_velocity_random', min(1.0, abs(vrand / vel)))
    grav = np.zeros(3)
    drag = 1.0
    for n in chain:
        for m in n['Modifiers']:
            vals = {kv['Target']: curve(m, kv['Target'], kv['DefaultValue']).mean() for kv in m['KeyframedValues']}
            if m['TypeStr'] == 'Acceleration':
                ax = np.array([vals.get('Axis.' + c, 0.0) for c in 'XYZ'])
                grav += ax * vals.get('Factor', 0.0) * unit / 3600
            elif m['TypeStr'] == 'Drag':
                drag = min(drag, max(0.5, 1 - vals.get('DragStrength', 0.0) / 60))
            else:
                notes.append(m['TypeStr'].lower() + ' not converted')
    p.set_field(em, 'gravity', [float(g) for g in grav])
    p.set_field(em, 'air_resistance', float(drag))

    # ---- emitter transform: the nodes above, root first (rotations in degrees, X then Y then Z)
    m = np.eye(3)
    pos = np.zeros(3)
    for n in chain[:-1]:
        pos = pos + m @ np.array(n['Position'], float)
        m = m @ euler_matrix(n['Rotation'])
        if n['NodeType'] == 'Emitter' and n['NodeSpecificType'] == 'VerticalDistribution':
            pos = pos + m @ np.array([0.0, n['EmitterNode'].get('Position', 0.0), 0.0])
    pos = pos + m @ np.array(node['Position'], float)
    if kind == 1:
        m = m @ euler_matrix(node['Rotation'])
    p.set_emitter_srt(em, (1, 1, 1), matrix_euler(m), [float(v * unit) for v in pos])
    # the template's own key animations (emission rate / scale curves) would fight these values
    if p.field(em, 'keyanim_size'):
        notes.append('template key animation dropped')
        p.set_field(em, 'keyanim_size', 0)
    return em, name, notes


def convert_emp(p, pkg, images, emp_name, prefix, unit, log):
    emp = pkg['emp'][emp_name]
    spawn_times = simulate(emp)
    out = []

    def walk(nodes, chain):
        for n in nodes:
            n['_emp'] = emp
            c = chain + [n]
            if n['NodeType'] == 'Emission':
                kind = emission_kind(n)
                if kind is None or 'Hide' in n['NodeFlags_names']:
                    log.append('  skip %-24s %s' % (n['Name'], n['NodeSpecificType']))
                else:
                    out.append(convert_emission(p, pkg, images, c, unit, n['Name'], spawn_times))
            walk(n['ChildParticleNodes'], c)
    walk(emp['ParticleNodes'], [])
    base = prefix + os.path.splitext(emp_name)[0].replace('Kmh_', '')
    sets = []
    for part in range(0, len(out), MAX_EMITTERS):
        chunk = out[part:part + MAX_EMITTERS]
        name = base if part == 0 else '%s_%d' % (base, part // MAX_EMITTERS + 1)
        si = p.new_set(name, [c[0] for c in chunk], [c[1] for c in chunk])
        sets.append((si, name, chunk))
    return sets


def convert_package(p, pkg_dir, prefix='PtcSupamarioKmh', unit=UNIT, emps=None):
    """add the package's EMPs to the Ptcl p as new sets: ([(set index, name, [(bytes, emitter name,
    notes)])], skipped-node log lines)"""
    pkg = xv2vfx.load_package(pkg_dir)
    images = emb_images(pkg)
    log, made = [], []
    for emp_name in (emps or sorted(pkg['emp'])):
        made += convert_emp(p, pkg, images, emp_name, prefix, unit, log)
    return made, log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pkg')
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--prefix', default='PtcSupamarioKmh')
    ap.add_argument('--unit', type=float, default=UNIT)
    ap.add_argument('--emp', nargs='*')
    ap.add_argument('--preview')
    a = ap.parse_args()
    p = ptcl.Ptcl(open(a.base, 'rb').read())
    made, log = convert_package(p, a.pkg, a.prefix, a.unit, a.emp)
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    open(a.out, 'wb').write(out)
    for si, name, chunk in made:
        print('set %d (efc %d) %s: %d emitters' % (si, si + 1, name, len(chunk)))
        for em, en, notes in chunk:
            d = q.sets[si]['emitters'][[c[1] for c in chunk].index(en)]['data']
            print('   %-22s pt%d bl%d life %3d frames %d..%s every %d x%.3g  scale %s  %s' % (
                en, q.field(d, 'particle_type'), q.field(d, 'blend_type'), q.field(d, 'ptcl_life'),
                q.field(d, 'start_frame'), 'inf' if q.field(d, 'end_frame') == FOREVER else q.field(d, 'end_frame'),
                q.field(d, 'emit_interval'), q.field(d, 'emit_rate'),
                '%.2gx%.2g' % tuple(q.field(d, 'scale')), '; '.join(sorted(set(notes)))))
    for line in log:
        print(line)
    if a.preview:
        from PIL import Image
        os.makedirs(a.preview, exist_ok=True)
        for si, name, chunk in made:
            tiles = []
            for k in range(len(chunk)):
                d = q.sets[si]['emitters'][k]['data']
                img = q.decode_texture(d, 0)
                tiles.append(Image.fromarray(img[..., :3]).resize((96, 96)))
            sheet = Image.new('RGB', (96 * len(tiles), 96))
            for k, t in enumerate(tiles):
                sheet.paste(t, (96 * k, 0))
            sheet.save(os.path.join(a.preview, name + '.png'))
    print('%s: %d sets added, %d -> %d bytes' % (a.out, len(made), len(open(a.base, 'rb').read()), len(out)))


if __name__ == '__main__':
    main()
