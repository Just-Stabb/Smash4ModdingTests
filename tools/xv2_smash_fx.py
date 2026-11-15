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


def retime_model(folder, frames):
    """play an effect model's own animation (model.omo, model.mta) in `frames` frames: every node and material value
    sampled at its time scaled (nearest frame). Core Breaker v2: XV2 plays the charge orb's 72-frame animation over
    its 66-frame charge; the Smash hover shows it ~18 frames, so in v1 only its fade-in was seen before it was ended"""
    import omo
    import mta
    bones = omo.vbn_read(os.path.join(folder, 'model.vbn'))
    path = os.path.join(folder, 'model.omo')
    o = omo.Omo(open(path, 'rb').read())
    src = o.frames
    pick = [min(src - 1, int(round(f * (src - 1) / float(max(1, frames - 1))))) for f in range(frames)]
    vals = {h: [o.sample(h, f) for f in range(src)] for _n, _p, h in bones if o.node(h) is not None}
    o.frames = frames
    for n in o.nodes:
        n[3] = [b''] * frames
    for h, v in vals.items():
        tr = omo.tracks(o, h)
        omo.set_node(o, h, [v[k][0] for k in pick] if 'pos' in tr else None,
                     [v[k][1] for k in pick] if 'rot' in tr else None, [v[k][2] for k in pick] if 'scl' in tr else None)
    open(path, 'wb').write(o.encode())
    mp = os.path.join(folder, 'model.mta')
    md = open(mp, 'rb').read()
    if md:
        a = mta.read(md)
        mats = [dict(name=e['name'], hash=e['hash'], props=[
            dict(name=p['name'], values=[p['values'][min(len(p['values']) - 1, k)] for k in pick] if p['type'] == 1
                 else p['values'], u1=p['u1'], u2=p['u2'], type=p['type']) for p in e['props']]) for e in a['mats']]
        open(mp, 'wb').write(mta.write(frames, mats, rate=a['rate'], unk=a['unk']))
    return src


# ---------------------------------------------------------------- fake glow halos (test)
# XV2 glares its glowing materials (EMM Glare / GlareCol); Smash 4 draws colours past white with no visible bloom
# (the God Fist glow test: glow_3 / 4 / 5 looked alike). A halo fakes it: for each converted emitter whose material
# glows, a copy drawn additive with a soft round falloff, HALO_SIZE x larger, at HALO_ALPHA of its alpha (same timing,
# emission and motion, so it follows the particle); for a glowing model, one soft particle at its centre for its life.
HALO_ALPHA = 0.45               # the strength: the halo's alpha x the emitter's
HALO_SIZE = 2.5                 # billboards x this; rings (polygons) x HALO_RING, streaks x HALO_SIZE wide
HALO_RING = 1.2
HALO_SUFFIX = 'H'


def soft_glow_rgba(n=64):
    """a soft round falloff (a blurred radial gradient), white in RGB (the BC4 shape the converter's templates use)"""
    import numpy as np
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot((xx + 0.5) / n * 2 - 1, (yy + 0.5) / n * 2 - 1)
    f = np.clip(1.0 - r, 0.0, 1.0) ** 2.2
    v = (f * 255 + 0.5).astype(np.uint8)
    return np.stack([v, v, v, np.full_like(v, 255)], 2)


def _halo_texture(p, em, cache):
    import ptcl
    o = ptcl.TEXRES
    if 'block' in cache:
        em[o:o + ptcl.TEXRES_SIZE] = cache['block']
        return
    p.set_texture(em, 0, soft_glow_rgba(), 0x34)
    struct.pack_into('>I', em, o + 0x0C, 0x22000100)          # clamped (the converter's SAMPLER_CLAMP)
    cache['block'] = bytes(em[o:o + ptcl.TEXRES_SIZE])


def halo_emitter(p, d, alpha=None, cache=None):
    """an additive soft copy of emitter bytes d (its timing / emission / motion kept)"""
    alpha = HALO_ALPHA if alpha is None else alpha
    em = bytearray(d)
    p.set_field(em, 'blend_type', 1)
    _halo_texture(p, em, cache if cache is not None else {})
    t = p.field(em, 'particle_type')
    sx, sy = p.field(em, 'scale')
    if t == 1:
        p.set_field(em, 'scale', [sx * HALO_RING, sy * HALO_RING])
    elif t == 3:
        p.set_field(em, 'scale', [sx * HALO_SIZE, sy * HALO_RING])
    else:
        p.set_field(em, 'scale', [sx * HALO_SIZE, sy * HALO_SIZE])
    for k in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
        p.set_field(em, k, p.field(em, k) * alpha)
    peak = max(max(k[:3]) for tr in (0, 1) for k in p.color_keys(em, tr)) * p.field(em, 'color_scale')
    if peak > HDR_CAP:
        p.set_field(em, 'color_scale', p.field(em, 'color_scale') * HDR_CAP / peak)
    return em


def model_halo_emitter(p, template, radius, rgb, frames, loop, alpha=None, cache=None):
    """one soft additive particle at a model's centre: `radius` x HALO_SIZE across, colour rgb, `frames` long (a
    looping model: one every `frames` frames until its effect is ended)"""
    alpha = HALO_ALPHA if alpha is None else alpha
    em = bytearray(template)
    p.set_field(em, 'blend_type', 1)
    _halo_texture(p, em, cache if cache is not None else {})
    p.set_field(em, 'scale', [radius * HALO_SIZE] * 2)
    p.set_field(em, 'scale_init_ratio', [1.0, 1.0])
    p.set_field(em, 'scale_diff21', [0.0, 0.0])
    p.set_field(em, 'scale_diff32', [0.0, 0.0])
    p.set_field(em, 'scale_random', [0.0, 0.0])
    p.set_field(em, 'alpha_init', alpha)
    p.set_field(em, 'alpha_diff21', 0.0)
    p.set_field(em, 'alpha_diff32', 0.0)
    for tr in (0, 1):
        p.set_color_keys(em, tr, [(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)])
    p.set_field(em, 'color_scale', min(HDR_CAP / max(max(rgb), 1e-6), 1.5))
    p.set_field(em, 'start_frame', 0)
    p.set_field(em, 'one_time', 0 if loop else 1)
    p.set_field(em, 'end_frame', 0x7FFFFFFF if loop else 1)
    p.set_field(em, 'emit_start', 0)
    p.set_field(em, 'emit_interval', int(frames) if loop else 0)
    p.set_field(em, 'emit_rate', 1.0)
    p.set_field(em, 'ptcl_life', max(1, int(frames)))
    p.set_field(em, 'ptcl_life_random', 0)
    p.set_field(em, 'volume_type', 0)
    p.set_field(em, 'volume_radius', [0.0, 0.0, 0.0])
    for k in ('figure_velocity', 'emitter_velocity', 'init_velocity_random', 'dispersion_angle'):
        p.set_field(em, k, 0.0)
    p.set_field(em, 'gravity', [0.0, 0.0, 0.0])
    p.set_field(em, 'rotation_velocity', [0.0, 0.0, 0.0])
    p.set_field(em, 'rotation_velocity_random', [0.0, 0.0, 0.0])
    facing_safe(p, em)
    return em


def add_halos(p, e, glowing, alpha=None, cache=None):
    """glowing: {set index: [emitter indices]}. Each glowing emitter gets a halo copy: in its own set while it has room
    (16 emitters at most), else in a companion set '<name>H' (returned: {its .efc index: [companion .efc indices]},
    for every script call of the set to call the companion too: add_halo_calls)"""
    cache = {} if cache is None else cache
    companions = {}
    efc_of = {ent[1] - 1: i for i, ent in enumerate(e.entries) if ent[1]}
    for si, ks in sorted(glowing.items()):
        halos = [halo_emitter(p, p.sets[si]['emitters'][k]['data'], alpha, cache) for k in ks]
        room = 16 - len(p.sets[si]['emitters'])
        inside, outside = halos[:max(0, room)], halos[max(0, room):]
        for em in inside:
            p.sets[si]['emitters'].append({'pos': 0, 'rt': (0, 0, 0), 'data': em})
            p.dirty_layout = True
        if outside:
            ns = p.new_set(p.set_name(si) + HALO_SUFFIX, outside)
            companions.setdefault(efc_of[si], []).append(e.add(ns + 1))
    return companions


def add_halo_calls(script, mapping):
    """every Graphic_Effect / External_Graphic / Terminate_Graphic_Effect of an effect id in mapping ({id: [ids]})
    followed by the same call with each mapped id; the enclosing True blocks' offsets grown to match. Returns the new
    list (raises on a script with other branching: Else / Goto / loops / threads)"""
    import acmd
    names = {'Graphic_Effect', 'External_Graphic', 'Terminate_Graphic_Effect'}
    branch = {'Else', 'Goto', 'Set_Loop', 'Thread_Start', 'Script_Run_Subroutine'}
    pos, w = [], 0
    for c in script:
        pos.append(w)
        w += acmd.INFO[c.ident]['size']
    blocks = []                                              # (index of True, its end word)
    for i, c in enumerate(script):
        n = acmd.INFO[c.ident]['name']
        if n in branch:
            raise ValueError('add_halo_calls: %s in the script' % n)
        if n == 'True':
            blocks.append((i, pos[i] + int(c.params[0])))
    out, grow = [], {i: 0 for i, _e in blocks}
    for i, c in enumerate(script):
        out.append(c)
        if acmd.INFO[c.ident]['name'] in names and c.params and c.params[0] in mapping:
            for hid in mapping[c.params[0]]:
                dup = acmd.Command(c.ident, [hid] + list(c.params[1:]))
                out.append(dup)
                at = pos[i]
                for bi, end in blocks:
                    if pos[bi] < at < end:
                        grow[bi] += acmd.INFO[c.ident]['size']
    idx_of = {id(c): i for i, c in enumerate(script)}
    final = []
    for c in out:
        if acmd.INFO[c.ident]['name'] == 'True':
            idx = idx_of.get(id(c))
            if idx is not None and grow.get(idx):
                c = acmd.Command(c.ident, [int(c.params[0]) + grow[idx]] + list(c.params[1:]))
        final.append(c)
    return final


def inflate_discs(folder):
    """an effect model's flat discs (meshes lying in their XY plane, as XV2's camera-facing charge orb Cor_Crg) made
    into closed shells: every vertex lifted onto the sphere of the disc's radius, a front and a back copy (same UVs,
    colours, triangles; the back one wound the other way), normals outward. Seen face-on it draws as the disc did,
    from any other side it surrounds what is inside it (Core Breaker v3, user: "the initial circle looks flat. It
    should cover around supamario like the auras")"""
    import numpy as np
    import nud
    path = os.path.join(folder, 'model.nud')
    meshes = nud.read(path)
    n = 0
    for m in meshes:
        for p in m.polygons:
            pos = np.asarray(p.pos, dtype=np.float64)
            if pos.shape[0] < 3 or np.abs(pos[:, 2]).max() > 1e-4:
                continue
            r = np.hypot(pos[:, 0], pos[:, 1]).max()
            if r <= 0:
                continue
            z = np.sqrt(np.clip(r * r - pos[:, 0] ** 2 - pos[:, 1] ** 2, 0.0, None))
            front = np.stack([pos[:, 0], pos[:, 1], z], 1)
            back = np.stack([pos[:, 0], pos[:, 1], -z], 1)
            k = len(pos)
            p.pos = np.concatenate([front, back]).astype(np.float32)
            p.nrm = (p.pos / r).astype(np.float32)
            if p.col is not None:
                p.col = np.concatenate([p.col, p.col])
            p.uvs = [np.concatenate([u, u]) for u in p.uvs]
            tri = np.asarray(p.idx).reshape(-1, 3)
            p.idx = np.concatenate([tri.ravel(), (tri[:, ::-1] + k).ravel()]).astype(p.idx.dtype)
            for attr in ('tan', 'bit'):
                v = getattr(p, attr)
                if v is not None:
                    setattr(p, attr, np.concatenate([v, v]))
            n += 1
    open(path, 'wb').write(nud.write(meshes))
    return n
