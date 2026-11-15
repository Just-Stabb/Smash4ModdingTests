#!/usr/bin/env python3
"""Shared settings and helpers for putting Dragon Ball Xenoverse 2 skill effects on a Smash 4 fighter, from the Super
God Fist's lessons (fighters/supamario/README.md, Super God Fist v4-v9) and the repo's HDR finding (fighters/brave/
README.md fixes 21-27: Smash 4 blooms colours drawn past 1; far past ~2.5 it hazes purple). Used by the Core Breaker
(tools/supamario_corebreaker_fx.py); the God Fist's own build (supamario_godfist_build.py) keeps its settings.

The defaults, and why:
- UNIT 5.04 units a metre (the body's retarget scale), SIZE x1.75 on top (God Fist v8: v6's x1.5 too small, v7's
  x2 "slightly too large"; XV2's effects read against a ~1.75 m character, Supamario ~12 units tall).
- Vibrance: XV2 draws with glare (each material's Glare flag and GlareCol, 1.0-1.6). `hdr_emitter` multiplies the
  emitter's colour keys by its material's GlareCol (XV2's glare tint, per channel) and its colour scale by HDR_GAIN
  (God Fist v5-v7's x2), then caps the brightest drawn channel at HDR_CAP (2.0: into Smash 4's bloom, below the
  purple haze Hero's fixes hit) by lowering the colour scale (the hue kept); alpha x ALPHA (capped at 1).
  `hdr='flat'`: the God Fist's way (colour scale x2, no cap).
- Models: colour gain x MODEL_GAIN x GlareCol per material (xv2_to_nud --tint; the God Fist's aura ended at
  x2.5 / x2 / x1.5 for its orange: the same brightness, XV2's hue kept).
- Facing: every converted emitter's own transform at the effect's origin, unturned, any spread / emitter speed a
  full sphere (`facing_safe`, God Fist v7); every effect called on bone 0 (TopN) with offsets only up (Y) and
  forward (Z) and turns only Y 0 / 180, or on a body bone with no offset and no turn (`facing_check`, God Fist v6).
  A model whose front must point elsewhere (a camera-facing disc, a cone along a dive) has the turn baked into its
  own animation (`bake_model_turn`), so its ACMD call stays unturned.
- XV2 refraction materials (ScreenRefract / *REFRACT*: a heat haze) have no Smash 4 equivalent: their emitters are
  hidden (alpha 0) and such models left out, instead of drawing them as coloured light; subtractive materials keep
  blend 2 (subtract) rather than the converter's additive stand-in.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

UNIT = 5.04
SIZE = 1.75
HDR_GAIN = 2.0
HDR_CAP = 2.0
ALPHA = 2.0
MODEL_GAIN = 2.0
BLEND_SUB = 2


def facing_safe(p, d):
    """God Fist v7: its own transform at the effect's origin, unturned, any spread or emitter speed a full sphere"""
    p.set_emitter_srt(d, tuple(p.field(d, 'emitter_scale')), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    if p.field(d, 'particle_type') in (1, 3) or p.field(d, 'dispersion_angle') > 0 or \
            p.field(d, 'emitter_velocity') or p.field(d, 'figure_velocity'):
        p.set_field(d, 'dispersion_angle', 180.0)


def emm_params(mat):
    return {(q['Name'] if isinstance(q, dict) else q[0]): (q['Value'] if isinstance(q, dict) else q[1])
            for q in mat.get('Parameters', [])}


def material_table(pkg):
    """{emp file: {emission node name: (material name, shader, params)}} from an xv2vfx.load_package"""
    import xv2vfx
    mats = {}
    for emm in pkg['emm'].values():
        for m in emm.get('Materials', []):
            mats.setdefault(m['Name'], (m.get('ShaderProgram'), emm_params(m)))
    out = {}
    for fn, emp in pkg['emp'].items():
        t = {}
        for _d, n in xv2vfx.emp_nodes(emp):
            if n['NodeType'] == 'Emission':
                ref = (n.get('EmissionNode') or {}).get('Texture', {}).get('MaterialRef')
                if ref in mats:
                    t.setdefault(n.get('Name'), (ref,) + mats[ref])
        out[fn] = t
    return out


def is_refraction(shader, name=''):
    return 'REFRACT' in (shader or '').upper() or (name or '').startswith('Ref_')


def glare(params):
    """XV2's glare tint of a material: GlareCol RGB when its Glare flag is on, else 1"""
    if not params.get('Glare'):
        return (1.0, 1.0, 1.0)
    return tuple(float(params.get('GlareCol' + c, 1.0)) for c in 'RGB')


def hdr_emitter(p, d, material=None, hdr='glare'):
    """the emitter's colour for Smash 4 (module doc): returns a note"""
    if material is not None and is_refraction(material[1], material[0]):
        p.set_field(d, 'alpha_init', 0.0)
        p.set_field(d, 'alpha_diff21', 0.0)
        p.set_field(d, 'alpha_diff32', 0.0)
        return 'refraction (%s): hidden' % material[0]
    notes = []
    if material is not None and int(material[2].get('AlphaBlendType', 0)) == 2:
        p.set_field(d, 'blend_type', BLEND_SUB)
        return 'subtractive kept (XV2\'s darkening: no glare gain)'
    p.set_field(d, 'alpha_init', min(1.0, p.field(d, 'alpha_init') * ALPHA))
    if hdr == 'flat':
        p.set_field(d, 'color_scale', p.field(d, 'color_scale') * HDR_GAIN)
        return '; '.join(notes + ['flat x%g' % HDR_GAIN])
    g = glare(material[2]) if material is not None else (1.0, 1.0, 1.0)
    peak = 0.0
    for track in (0, 1):
        keys = [(k[0] * g[0], k[1] * g[1], k[2] * g[2], k[3]) for k in p.color_keys(d, track)]
        p.set_color_keys(d, track, keys)
        peak = max(peak, max(max(k[:3]) for k in keys))
    scale = p.field(d, 'color_scale') * HDR_GAIN
    if peak * scale > HDR_CAP:
        scale = HDR_CAP / max(peak, 1e-6)
    p.set_field(d, 'color_scale', scale)
    notes.append('glare %s, peak %.2f' % ('/'.join('%g' % x for x in g), peak * scale))
    return '; '.join(notes)


def model_tints(emm):
    """xv2_to_nud --tint for an EMO's materials: MODEL_GAIN x GlareCol (None: a refraction model, leave it out)"""
    out = {}
    for m in emm.get('Materials', []):
        prm = emm_params(m)
        if is_refraction(m.get('ShaderProgram')):
            return None
        g = glare(prm)
        out[m['Name']] = tuple(round(MODEL_GAIN * x, 3) for x in g)
    return out


def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def _qrot(q, v):
    x, y, z, w = q
    t = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return t[:3]


def euler_q(rx, ry, rz):
    """a turn about X, then Y, then Z (degrees), as a quaternion (x, y, z, w)"""
    def ax(i, a):
        h = math.radians(a) / 2
        v = [0.0, 0.0, 0.0]
        v[i] = math.sin(h)
        return (v[0], v[1], v[2], math.cos(h))
    return _qmul(ax(2, rz), _qmul(ax(1, ry), ax(0, rx)))


def bake_model_turn(folder, q):
    """turn an effect model (xv2_to_nud folder) by q in its own animation: every bone under TopN gets q before its
    own transform (position turned, rotation premultiplied) on every frame; the ACMD call then needs no turn"""
    import omo
    bones = omo.vbn_read(os.path.join(folder, 'model.vbn'))
    path = os.path.join(folder, 'model.omo')
    o = omo.Omo(open(path, 'rb').read())
    tops = [b[2] for b in bones if b[1] == 0]
    for h in tops:
        vals = [o.sample(h, f) for f in range(o.frames)]
        pos = [_qrot(q, v[0]) for v in vals]
        rot = [_qmul(q, v[1]) for v in vals]
        omo.set_node(o, h, pos, rot, [v[2] for v in vals])
    open(path, 'wb').write(o.encode())


def facing_check(calls):
    """the God Fist's facing rule on ACMD effect calls [{'bone': 0 or name, 'offset': (x, y, z), 'rot': (x, y, z)}]:
    bone 0: no X offset, turns about Y by 0 / 180 only; any other bone: no offset, no turn. Returns the problems."""
    bad = []
    for c in calls:
        x, y, z = c['offset']
        rx, ry, rz = c['rot']
        if c['bone'] in (0, 'bone 0 (TopN)', 'TopN'):
            if abs(x) > 1e-6 or abs(rx) > 1e-6 or abs(rz) > 1e-6 or min(abs(ry % 360), abs(ry % 360 - 180),
                                                                          abs(ry % 360 - 360)) > 1e-6:
                bad.append('%s: bone 0 with offset %s / turn %s' % (c.get('name', '?'), c['offset'], c['rot']))
        elif any(abs(v) > 1e-6 for v in (x, y, z, rx, ry, rz)):
            bad.append('%s: bone %s with offset %s / turn %s' % (c.get('name', '?'), c['bone'], c['offset'], c['rot']))
    return bad


def facing_emitters(p, set_indices):
    """every emitter of the sets facing-safe (God Fist v7's check): no own turn or offset, and a full-sphere spread
    whenever it is directional or moves"""
    bad = []
    for si in set_indices:
        for k, em in enumerate(p.sets[si]['emitters']):
            d = em['data']
            if d is None:
                continue
            raw = bytes(d[0x408:0x408 + 36])
            vals = struct.unpack('>9f', raw)
            if any(abs(v) > 1e-6 for v in vals[3:]):
                bad.append('set %d emitter %d: turned / offset %s' % (si, k, vals[3:]))
            if (p.field(d, 'particle_type') in (1, 3) or p.field(d, 'emitter_velocity') or
                    p.field(d, 'figure_velocity')) and p.field(d, 'dispersion_angle') < 180.0:
                bad.append('set %d emitter %d: directional, spread %.0f' % (si, k, p.field(d, 'dispersion_angle')))
    return bad
