#!/usr/bin/env python3
"""Ultimate fighter effects (ef_<name>.eff, VFXB: tools/vfxb.py) -> Smash 4 emitter sets added to a
fighter's ptcl (one set per Ultimate emitter set), its .efc entries, and an ids file for
tools/ultimate_acmd.py --effects.

  python3 tools/vfxb_to_ptcl.py EFF BASE_DIR OUT_DIR KIND IDS.json [EFFECT ...] [--prefix PtcEdge]
                                [--templates VANILLA.ptcl ...]

BASE_DIR: the base fighter's effect folder (<base>.010d0000.ptcl / .efc, e.g. Zelda's: the new
fighter's bank is a copy of it, the base's specials still use its sets). OUT_DIR gets
<name>.010d0000.ptcl / .efc (named after BASE_DIR's files: rename for the fighter); KIND: the
fighter kind (ids 0x3KKnnnn). EFFECT: Ultimate effect names (default: all).

Mapping (eft2 v22 -> eft 0x42), per emitter, from a template emitter, as tools/xv2_to_ptcl.py:
- template: Templates (the base's own or one imported from --templates files) of the eft particle
  type (eft2's numbers: 0 billboard, 1 / 2 plate XY / XZ, 3 directional, 4 directional polygon, 8 Y
  billboard; 7 primitive as a billboard mesh), blend and mesh-ness. Stripes (5 / 6) are skipped;
- meshes (a primitive id): the VFXB's model (G3PR BFRES, tools/bfres_switch.py; first shape)
  written to the primitive table (Ptcl.add_primitive, once per id);
- texture: the first sampler that isn't an indirect / grade / noise / mask helper, its BNTX channel
  selection applied (tools/vfxb.py images), the first flipbook cell (uv_div), as a BC4 shape with
  the mean colour moved into the particle colour (xv2_to_ptcl.shape_texture); clamped when the
  sampler clamps;
- colour: colour 0 (constant, or its keys) x the emitter colour, the 3-key colour fit; alpha 0
  (constant or keys, clamped to 1) as the 3-key alpha; colour scale as eft's;
- scale: the particle scale x the scale keys (3-key fit), random % -> fraction;
- life (+ random % -> frames; infinite -> 0x7FFFFFFF, emitted once), emission (start, duration when one-time, else
  forever, interval, rate), velocity (all-direction -> figure velocity, designated direction x
  scale -> emitter velocity / direction, diffusion angle, random %), gravity (scale x direction),
  air resistance, volume (same 0-14 shape list; radius x form scale), rotation (init / random /
  add, radians), the emitter transform (translate / rotate / scale);
- not converted: texture scroll / pattern animation, the second colour track and multi-texture
  combiners, alpha / scale fades at the end, emitter animations (EAA0 / EAA1 ...), child emitters.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import efc  # noqa: E402
import ptcl  # noqa: E402
import vfxb  # noqa: E402
from xv2_to_ptcl import (BLEND, FOREVER, MAX_EMITTERS, MAX_LIVE, SAMPLER_CLAMP, buffer_count, color_fit,  # noqa: E402
                         pow2, resize, sanitize, shape_texture, three_key)

NONE64 = 2 ** 64 - 1
# eft2 vertex transform -> eft particle type (the same numbers: 0 billboard, 1 / 2 plate XY / XZ,
# 3 directional, 4 directional polygon, 8 Y billboard); 7 (primitive) as a billboard mesh; 5 / 6
# (stripes) have no eft counterpart here
TYPES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 7: 0, 8: 8}
BASE_FIRST = 2          # a template of the base's own beats an imported one this much


class Templates:
    """template emitters by (eft particle type, blend 0 / 1 / 2, mesh): simple emitters with one BC4
    texture (slot 0; slots 1 / 2 unused), preferring animated colour tracks (2 / 2, then 2 / x) and
    the base's own (no import); others are imported from the corpus (Ptcl.import_emitter: their
    shader, shader parameters and textures copied)"""

    def __init__(self, base, corpus):
        self.base, self.files, self.found = base, {}, {}
        for path in [None] + list(corpus):
            p = base if path is None else ptcl.Ptcl(open(path, 'rb').read())
            if path is not None:
                self.files[path] = p
            for si, s in enumerate(p.sets):
                for k, x in enumerate(s['emitters']):
                    em = x['data']
                    if em is None or len(em) != ptcl.SIMPLE_SIZE:
                        continue
                    t = [p.texres(em, j) for j in range(3)]
                    if t[0]['native_format'] != 9 or t[1]['native_size'] or t[2]['native_size']:
                        continue
                    key = (p.field(em, 'particle_type'), p.field(em, 'blend_type'), p.field(em, 'primitive_index') >= 0)
                    c = (p.field(em, 'color0_type'), p.field(em, 'color1_type'))
                    score = (2 if c == (2, 2) else 1 if c[0] == 2 else 0) + (BASE_FIRST if path is None else 0) \
                        - (1 if p.field(em, 'keyanim_size') else 0)
                    if key not in self.found or score > self.found[key][0]:
                        self.found[key] = (score, path, si, k)

    def get(self, typ, blend, mesh, notes):
        for key in ((typ, blend, mesh), (typ, 1, mesh), (0, blend, mesh), (0, 1, mesh)):
            if key in self.found:
                if key != (typ, blend, mesh):
                    notes.append('no template (type %d blend %d%s): type %d blend %d' % (
                        typ, blend, ' mesh' if mesh else '', key[0], key[1]))
                _score, path, si, k = self.found[key]
                if path is None:
                    em = self.base.emitter_bytes(si, k)
                    struct.pack_into('>II', em, 0x2CC, 0, 0)
                    return em
                return self.base.import_emitter(self.files[path], si, k, skip_slots=(0,))
        raise KeyError((typ, blend, mesh))


def mesh(model):
    """(pos, nrm, col, uv, idx) of a BFRES model's first shape"""
    shp = model['shapes'][0]
    a = model['vertex_buffers'][shp['vertex_buffer']]['attrs']
    n = len(a['_p0'])
    uv0 = a.get('_u0', np.zeros((n, 2), np.float32))[:, :2]
    uv1 = a.get('_u1', uv0)[:, :2]
    return (a['_p0'][:, :3], a['_n0'][:, :3] if '_n0' in a else None, a['_c0'][:, :4] if '_c0' in a else None,
            np.concatenate([uv0, uv1], 1), shp['meshes'][0]['indices'])


HELPER_TEXTURES = ('indirect', 'grade', 'noise', 'mask')


def keys(table, n, comps=3):
    """an eft2 key table (8 x (x, y, z, time 0-1)) -> [101, comps] samples over the particle's life"""
    k = np.array(table['keys'], float).reshape(8, 4)[:max(1, n)]
    t = np.linspace(0, 1, 101)
    return np.stack([np.interp(t, k[:, 3], k[:, c]) for c in range(comps)], 1)


def main_texture(e, names):
    smp = [(i, s) for i, s in enumerate(e['sampler']) if s['texture_id'] != NONE64]
    for i, s in smp:
        if not any(h in names.get(s['texture_id'], '') for h in HELPER_TEXTURES):
            return i, s
    return smp[0] if smp else (None, None)


def first_cell(img, scroll):
    nx, ny = (int(round(v)) if v and v >= 1 else 1 for v in scroll['uv_div'])
    h, w = img.shape[:2]
    return img[:max(4, h // ny), :max(4, w // nx)]


def convert_emitter(p, e, names, images, notes, templates, prims, prim_index):
    pt = e['particle']
    typ = TYPES.get(pt['billboard_type'])
    if typ is None:
        notes.append('billboard type %d (stripe): skipped' % pt['billboard_type'])
        return None
    is_mesh = pt['primitive_id'] != NONE64
    if is_mesh and pt['primitive_id'] not in prims:
        notes.append('primitive %d not in the file: skipped' % pt['primitive_id'])
        return None
    blend = {0: 'normal', 1: 'add', 2: 'sub'}.get(e['render']['blend_type'], 'add')
    em = templates.get(typ, BLEND[blend], is_mesh, notes)
    if is_mesh:
        pid = pt['primitive_id']
        if pid not in prim_index:
            prim_index[pid] = p.add_primitive(*mesh(prims[pid]))
        struct.pack_into('>i', em, 0x2DC, prim_index[pid])
    # the blend is shader-keyed: the template's (the same unless none had this one)
    blend = {0: 'normal', 1: 'add', 2: 'sub'}[p.field(em, 'blend_type')]

    # ---- texture
    ti, smp = main_texture(e, names)
    img = images.get(smp['texture_id']) if smp else None
    if img is None:
        img = np.full((16, 16, 4), 255, np.uint8)
        notes.append('no texture: white')
    else:
        img = first_cell(img, e['static']['tex_scroll'][ti])
    shape, tint = shape_texture(img.astype(np.float32) / 255)
    h, w = shape.shape
    tw, th = pow2(w, hi=256), pow2(h, hi=256)
    if (tw, th) != (w, h):
        shape = resize(shape[..., None].astype(np.float32), tw, th)[..., 0]
    r8 = (np.clip(shape, 0, 1) * 255 + 0.5).astype(np.uint8)
    p.set_texture(em, 0, np.stack([r8, r8, r8, np.full_like(r8, 255)], 2), 0x34)
    if smp and smp['wrap_u'] == 2 and smp['wrap_v'] == 2:
        struct.pack_into('>I', em, ptcl.TEXRES + 0x0C, SAMPLER_CLAMP)
    p.set_field(em, 'tex0_uv_scale', [1.0, 1.0])

    # ---- blend, colour, alpha
    st, col = e['static'], e['color']
    p.set_field(em, 'blend_type', BLEND[blend])
    rgb = keys(st['color0'], st['num_color0_keys']) if col['color0_type'] == 2 else \
        np.tile(np.array(col['color0'][:3], float), (101, 1))
    rgb = np.clip(rgb * np.array(e['info']['color0'][:3]) * tint[None, :], 0, None)
    cks, secs = color_fit(rgb)
    for track in (0, 1):
        if p.field(em, 'color%d_type' % track) == 2:
            p.set_color_keys(em, track, [(*map(float, c), 1.0) for c in cks])
        else:
            p.set_color_keys(em, track, [(*map(float, rgb.mean(0)), 1.0)])
    p.set_field(em, 'color_section1', [secs[0]] * 2)
    p.set_field(em, 'color_section2', [secs[1]] * 2)
    p.set_field(em, 'color_section3', [secs[2]] * 2)
    p.set_field(em, 'color_repeat', [1, 1])
    p.set_field(em, 'color_scale', float(st['color_scale'] or 1.0))
    alpha = keys(st['alpha0'], st['num_alpha0_keys'], 1)[:, 0] if col['alpha0_type'] == 2 else \
        np.full(101, float(col['color0'][3]))
    alpha = np.clip(alpha * e['info']['color0'][3], 0, 1)
    a0, a1, a2, s1, s2 = (float(np.squeeze(v)) for v in three_key(alpha))
    p.set_field(em, 'alpha_init', a0)
    p.set_field(em, 'alpha_diff21', a1 - a0)
    p.set_field(em, 'alpha_diff32', a2 - a1)
    p.set_field(em, 'alpha_section1', s1 / 100)
    p.set_field(em, 'alpha_section2', s2 / 100)

    # ---- scale
    sc = e['scale']
    curve = keys(st['scale_anim'], st['num_scale_keys'], 2)
    base = np.array([max(sc['scale'][0], 1e-4), max(sc['scale'][1], 1e-4)])
    peak = np.maximum(curve.max(0), 1e-4)
    v0, v1, v2, s1, s2 = three_key(curve / peak)
    p.set_field(em, 'scale', [float(b * m) for b, m in zip(base, peak)])
    p.set_field(em, 'scale_init_ratio', [float(v) for v in v0])
    p.set_field(em, 'scale_diff21', [float(v) for v in v1 - v0])
    p.set_field(em, 'scale_diff32', [float(v) for v in v2 - v1])
    p.set_field(em, 'scale_sections', [int(s1), int(s2)])
    p.set_field(em, 'scale_random', [min(1.0, sc['scale_random'][0] / 100), min(1.0, sc['scale_random'][1] / 100)])

    # ---- rotation
    p.set_field(em, 'rotation_init', [float(v) for v in st['rotate_init'][:3]])
    p.set_field(em, 'rotation_random', [float(v) for v in st['rotate_init_rand'][:3]])
    p.set_field(em, 'rotation_velocity', [float(v) for v in st['rotate_add']])
    p.set_field(em, 'rotation_velocity_random', [float(v) for v in st['rotate_add_rand'][:3]])

    # ---- shape and motion
    sh, vel, ems = e['shape'], e['velocity'], e['emission']
    vt = sh['volume_type'] if sh['volume_type'] <= 14 else 0
    p.set_field(em, 'volume_type', vt)
    p.set_field(em, 'volume_radius', [float(r * f) for r, f in zip(sh['volume_radius'], sh['volume_form_scale'])])
    p.set_field(em, 'figure_velocity', float(vel['all_direction']))
    d = np.array(vel['designated_dir'], float)
    n = np.linalg.norm(d)
    p.set_field(em, 'emit_direction', [float(v) for v in (d / n if n else np.array([0.0, 1.0, 0.0]))])
    p.set_field(em, 'emitter_velocity', float(vel['designated_dir_scale']))
    p.set_field(em, 'dispersion_angle', float(vel['diffusion_dir_angle']))
    p.set_field(em, 'init_velocity_random', min(1.0, vel['vel_random'] / 100))
    p.set_field(em, 'gravity', [float(ems['gravity_scale'] * g) for g in ems['gravity_dir']])
    p.set_field(em, 'air_resistance', float(st['air_res']))
    info = e['info']
    p.set_emitter_srt(em, tuple(info['scale']), tuple(info['rotate']), tuple(info['trans']))

    # ---- timing
    one = bool(ems['one_time'])
    if pt['infinite_life'] and not one:
        # a particle that lives until the effect ends (a held glow): emitted once (eft sizes the
        # buffer from life x rate / interval, unbounded for an endless emitter)
        one, ems = True, dict(ems, duration=1)
        notes.append('infinite life: emitted once')
    p.set_field(em, 'start_frame', int(ems['start']))
    p.set_field(em, 'end_frame', max(1, int(ems['duration'])) if one else FOREVER)
    p.set_field(em, 'one_time', 1 if one else 0)
    p.set_field(em, 'emit_start', 0)
    p.set_field(em, 'emit_interval', int(ems['interval']))
    p.set_field(em, 'emit_rate', float(max(ems['rate'], 0.01)))
    life = FOREVER if pt['infinite_life'] else max(1, int(pt['life']))
    p.set_field(em, 'ptcl_life', life)
    p.set_field(em, 'ptcl_life_random', 0 if life == FOREVER else int(pt['life'] * pt['life_random'] / 100))
    if p.field(em, 'keyanim_size'):
        p.set_field(em, 'keyanim_size', 0)
    if e['children']:
        notes.append('%d child emitters not converted' % len(e['children']))
    if e['subsections']:
        notes.append('not converted: ' + ', '.join(sorted(e['subsections'])))
    n = buffer_count(p, em)
    if n > 4 * MAX_LIVE:
        # fewer particles a burst (eft sizes the emitter's buffer from it; vanilla stays far below)
        p.set_field(em, 'emit_rate', max(1.0, p.field(em, 'emit_rate') * 4 * MAX_LIVE / n))
        notes.append('buffer %d: rate lowered' % n)
    notes += sanitize(p, em)
    return em


def set_name(prefix, ult):
    return prefix + ult[len('P_Edge'):] if ult.startswith('P_Edge') else prefix + ult.replace('P_', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('eff')
    ap.add_argument('base_dir')
    ap.add_argument('out_dir')
    ap.add_argument('kind', type=lambda v: int(v, 0))
    ap.add_argument('ids')
    ap.add_argument('effects', nargs='*')
    ap.add_argument('--prefix', default='PtcEdge')
    ap.add_argument('--templates', nargs='*', default=[],
                    help='vanilla .ptcl files to take template emitters from (the base\'s own first)')
    a = ap.parse_args()
    eff = vfxb.Eff(a.eff)
    names, _ = eff.textures()
    images = eff.images()
    base = [f for f in os.listdir(a.base_dir) if f.endswith('.010d0000.ptcl')][0][:-len('.ptcl')]
    p = ptcl.Ptcl(open(os.path.join(a.base_dir, base + '.ptcl'), 'rb').read())
    ef = efc.Efc(open(os.path.join(a.base_dir, base + '.efc'), 'rb').read())
    templates = Templates(p, a.templates)
    prims, prim_index = eff.primitives(), {}
    ids, done = {}, {}
    for name in (a.effects or sorted(eff.effects)):
        si_ult = eff.effects[name]
        if si_ult in done:
            ids[name] = done[si_ult]
            continue
        made, log = [], []
        for e in eff.emitters(si_ult):
            notes = []
            em = convert_emitter(p, e, names, images, notes, templates, prims, prim_index)
            if em is not None:
                made.append((em, e['name']))
            log.append('    %-24s %s' % (e['name'], '; '.join(dict.fromkeys(notes))))
        if not made:
            print('%-30s %s: nothing convertible' % (name, eff.sets[si_ult]))
            print('\n'.join(log))
            continue
        if len(made) > MAX_EMITTERS:
            log.append('    %d emitters: the first %d kept' % (len(made), MAX_EMITTERS))
            made = made[:MAX_EMITTERS]
        sname = set_name(a.prefix, eff.sets[si_ult])
        si = p.new_set(sname, [m[0] for m in made], [m[1] for m in made])
        ids[name] = done[si_ult] = (0x300 + a.kind) << 16 | ef.add(si + 1)
        print('%-30s %-28s -> %-28s 0x%07X  %d emitters' % (name, eff.sets[si_ult], sname, ids[name], len(made)))
        print('\n'.join(log))
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(a.out_dir, base + '.efc'), 'wb').write(ef.build())
    old = json.load(open(a.ids)) if os.path.exists(a.ids) else {}
    old.update({k: '0x%07X' % v for k, v in ids.items()})
    json.dump(old, open(a.ids, 'w'), indent=1)
    print('%d effects -> %d sets; %s' % (len(ids), len(set(done.values())), a.ids))


if __name__ == '__main__':
    main()
