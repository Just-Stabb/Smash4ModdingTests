#!/usr/bin/env python3
"""Tests for tools/gekkouga_fx.py (Greninja's flipbook effects, fighters/gekkouga/README.md "Skeleton v1.2" on).

  python3 -I tools/gekkouga_fx_test.py VANILLA_EFFECT_DIR KIRBY_PTCL FX_PKG BUILT_EFFECT_DIR [--skeleton-only]

--skeleton-only: skeleton v1.2's bank (its four sets); else burn v2's too (the fire on burning fighters, at his water's
ends and in the smashes' trails: their ids in the executable / build / trail MSC, their bases).

BUILT_EFFECT_DIR: gekkouga_fx.build's output (the package's fighter/gekkouga/effect/gekkouga). Checks:
- his 20 vanilla sets and 22 vanilla .efc entries unchanged; the new entries (flags 0x100) name the new sets in order,
  their ids those gekkouga_fx.ids_of gives and the MSC sources use; Ptcl.validate clean;
- every new emitter: Kirby's stone's shader (key and binary), the CPU's particles, a camera billboard, follow type 0,
  its set's blend, one BC3 RGBA texture of the atlas's size (clamped U / V), no motion / rotation / random size, alpha 1;
- the flipbook as eft plays it: each emitter's particles as fx_render models eft's emission (birth, life), their cell
  from Kirby's stone vertex program run in tools/latte_exec.py on the uniform block Smash 4's own code fills
  (tools/eft_static.py): every frame of two loops (a one-shot: its life) shows cell (frame / frames a cell) mod cells,
  and at a hand-over between two emitters (more than 32 cells) also the cell before;
- the placement: the skeleton's feet on the call's point and its body 28 tall, the explosion's base on it and 44 wide
  at its widest; the left skeleton's atlas = the right's, each cell mirrored.
"""
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import efc as EFC  # noqa: E402
import gekkouga_fx as G  # noqa: E402
import ptcl as P  # noqa: E402

fails = checks = 0


def check(what, got, want):
    global fails, checks
    checks += 1
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


def vanilla_same(v, p):
    """his vanilla sets' emitters as they were (their parameters, texture formats / sizes, shader keys)"""
    bad = []
    for si in range(len(v.sets)):
        if v.set_name(si) != p.set_name(si):
            bad.append(('name', si))
            continue
        for a, b in zip(v.sets[si]['emitters'], p.sets[si]['emitters']):
            pa, pb = v.emitter_params(a['data']), p.emitter_params(b['data'])
            for d in (pa, pb):
                for t in d['textures']:
                    t.pop('native_pos', None)
                d.pop('name_pos', None)
                d.pop('keyanim_pos', None)
                d.pop('shader_param_pos', None)
            if pa != pb or bytes(v.shader_entry(v.field(a['data'], 'shader_index'))) != \
                    bytes(p.shader_entry(p.field(b['data'], 'shader_index'))):
                bad.append((v.set_name(si), pa['name']))
    return bad


def cells_shown(p, si, frames):
    """{frame: sorted cells drawn} for set si: fx_render's eft emission, the cells from the vertex program"""
    import fx_render as F
    import eft_static
    import latte_exec
    ems = F.s4_emitters(p, si, None)
    data = [e['data'] for e in p.sets[si]['emitters']]
    cm = F.call_matrix((0, 0, 0), (0, 0, 0), 1.0)
    sims = [F.simulate(em, (0, cm, 1.0, None), list(frames), seed=1) for em in ems]
    progs, cb2s = [], []
    for d in data:
        progs.append(latte_exec.VertexProgram(bytes(p.shader_binary(p.field(d, 'shader_index')))))
        cb2s.append(np.frombuffer(eft_static.build(d), np.float32).copy())
    out = {}
    for fr in frames:
        shown = []
        for j, em in enumerate(ems):
            vs, d = progs[j], data[j]
            nx, ny = d[0x4D7], d[0x4D8]
            for q in sims[j][fr]:
                t, b = q[2], q[9]
                age = t * b.get('life', em.life)
                A = np.zeros((4, len(vs.attributes), 4), np.float32)
                for k, n in enumerate(vs.attributes):
                    if n == 'v_inPos':
                        A[:, k] = F.EFT_QUAD
                    elif n == 'v_inWldPos':
                        A[:, k] = (0, 0, 0, age + 1)          # a CPU particle: its age after this frame's step
                    elif n == 'v_inScl':
                        A[:, k] = (1, 1, 1, 1)
                    elif n == 'v_inRandom':
                        A[:, k] = np.append(b['random'], em.life)
                    elif n == 'v_inColor0':
                        A[:, k] = (1, 1, 1, 1)
                cb3 = np.zeros(48, np.float32)
                cb3[0:8] = 1
                cb3[8:12] = (fr + 1, 1, 1, 1)                 # emp0: w the step (1)
                cb3[16:32] = np.eye(4).ravel()
                cb3[32:48] = np.eye(4).ravel()
                _gp, par = vs.run(A, {1: F.s4_view_block(), 2: cb2s[j], 3: cb3}, np.arange(4))
                uv = par[:, [k for k, s in vs.params.items() if s == 9][0], :2]
                u0, v0 = uv.min(0)
                shown.append(int(round(u0 * nx)) + nx * int(round(v0 * ny)))
        out[fr] = sorted(shown)
    return out


def ring_checks(p, si, name, spec, kirby, ksh):
    """burn v2.3: neutral air's ring of flames: one emitter a flame, each its own footage, at its place round the
    circle, flying out along it, turned so its flame's tip points out from his centre"""
    import math
    import fx_render as F
    r = spec['ring']
    fl = G.ring_flames(spec['left'])
    ems = [x['data'] for x in p.sets[si]['emitters']]
    rnd = lambda v: [round(x, 3) for x in v] if isinstance(v, (list, tuple)) else round(v, 3)   # noqa: E731
    rows, want = [], []
    for em, f in zip(ems, fl):
        d = G.sidecar(f['atlas'])
        n = min(d['frames'], G.TABLE - 1)
        sh = p.field(em, 'shader_index')
        ph = math.radians(f['phi'])
        rows.append((bytes(p.shader_binary(sh)) == bytes(kirby.shader_binary(ksh)),
                     bool(struct.unpack_from('>I', em, 4)[0] & 0x00800000), p.field(em, 'particle_type'),
                     struct.unpack_from('>I', em, 0x310)[0], p.field(em, 'blend_type'), p.texres(em, 0)['size'],
                     p.field(em, 'volume_type'), p.field(em, 'emit_rate'), (p.field(em, 'one_time'), p.field(em, 'end_frame')),
                     p.field(em, 'ptcl_life'), rnd(p.field(em, 'emit_direction')), rnd(p.field(em, 'emitter_velocity')),
                     rnd(p.field(em, 'figure_velocity')), rnd(p.field(em, 'air_resistance')),
                     rnd(p.field(em, 'emitter_translation')), rnd(p.field(em, 'rotation_init')), em[0x4E0],
                     struct.unpack_from('>h', em, 0x506)[0], em[0x4D9], struct.unpack_from('>f', em, 0x82C)[0]))
        want.append((True, False, 0, 0, 1, d['atlas_size'], 0, 1.0, (1, 1), r['life'],
                     rnd([0.0, math.sin(ph), math.cos(ph)]), r['v'], 0.0, r['air'],
                     rnd([0.0, r['r0'] * math.sin(ph), r['r0'] * math.cos(ph)]), rnd([0.0, 0.0, math.radians(f['rot'])]),
                     f['start'] % n, n, 1, 0.0))
    check('%s: %d emitters, one a flame: Kirby\'s stone shader, CPU billboard, follow 0, additive, its own footage\'s atlas; '
          'one particle at radius %g at its angle round the YZ plane, flying out along it at %g (air %g), life %d, its '
          'billboard turned (rotation Z), its table from its own start cell, played out' % (
              name, r['n'], r['r0'], r['v'], r['air'], r['life']), rows, want)
    assets = [f['atlas'] for f in fl]
    check('%s: neighbouring flames differ (%s in turn)' % (name, ', '.join(a for a, _h in G.RING_ASSETS)),
          [i for i in range(len(fl)) if assets[i] == assets[(i + 1) % len(fl)]], [])
    out = []
    for f in fl:
        seen = (180.0 - f['phi']) if spec['left'] else f['phi']
        tipdir = f['tip'] + f['rot']
        out.append(abs((tipdir - seen + 180) % 360 - 180) <= G.RING_JITTER + 1e-6)
    check('%s: every flame\'s tip (its footage\'s own direction, measured on its atlas, + its turn, counter-clockwise on '
          'screen) points out from his centre as seen %s, within %g degrees (the jitter)' % (
              name, 'facing left (the places mirrored, 180 - angle)' if spec['left'] else 'facing right', G.RING_JITTER),
          all(out), True)
    ems_r = F.s4_emitters(p, si, None)
    cm = F.call_matrix((0, 0, 0), (0, 0, 0), 1.0)
    frames = [0, 10, r['life'] + 2]
    pts = {fr: [] for fr in frames}
    for j, e in enumerate(ems_r):
        sim = F.simulate(e, (0, cm, 1.0, None), frames, seed=3 + j)
        for fr in frames:
            pts[fr] += [np.asarray(q[0]) for q in sim[fr]]

    def rad(fr):
        q = pts[fr]
        rr = [math.hypot(x[1], x[2]) for x in q]
        return (len(q), round(max(abs(x[0]) for x in q), 3) if q else None, round(float(np.mean(rr)), 1) if q else None,
                round(float(np.ptp(rr)), 3) if q else None)
    r0, r10 = rad(0), rad(10)
    check('%s: (fx_render\'s eft) %d flames in the YZ plane, %g out at birth, ~9 by frame 10 (x the call\'s 1.45: the '
          'burst\'s edge, ~13), all at one radius, gone after %d frames' % (name, r['n'], r['r0'], r['life']),
          (r0[0], r0[1], r0[2], r0[3], 8.0 <= r10[2] <= 10.0, r10[3] < 0.01, rad(r['life'] + 2)[0]),
          (r['n'], 0.0, r['r0'], 0.0, True, True, 0))

def eft_timing(p, em, frames, u=0.5):
    """eft's own emission timing for one emitter (cross_f, skeleton v1.3: 0x04A64F00 - 0x04A65378, the count in the
    volume functions 0x04A4B2C4 ...): {frame: [ages of its live particles]}. Its clock t = frames since the effect was
    made (the set's +0x2AC is 0); emits while emit_start (0x44C) <= t, and with one_time while t <= end_frame (the
    previous frame's t under it: 0x04A65040), the first at once, then every interval + 1 frames; each emission's count
    accumulates rate x (1 - u x 0x448 / 100) (u: the LCG's draw), t 0 always one; the buffer holds one_time ? ((end -
    emit_start) / (interval + 1) + 1) x rate : (life / (interval + 1)) x rate + rate (0x04A5BE94); a particle lives its
    life frames (ages 0 ... life - 1)"""
    f = lambda n: p.field(em, n)                      # noqa: E731
    one, es, end, iv, life = f('one_time'), f('emit_start'), f('end_frame'), f('emit_interval'), f('ptcl_life')
    rate, pct = f('emit_rate'), f('emit_rate_random')
    cap = int(((end - es) // (iv + 1) + 1) * rate) if one else int((life // (iv + 1)) * rate + rate)
    alive, acc, nxt, out = [], 0.0, None, {}
    for t in range(max(frames) + 1):
        alive = [b for b in alive if t - b < life]
        if t >= es and (not one or t <= end) and (nxt is None or t >= nxt):
            acc += rate * (1.0 - u * pct / 100.0)
            if t == 0 and acc < 1.0:
                acc = 1.0
            n = int(acc)
            acc -= n
            for _ in range(n):
                if len(alive) < cap:
                    alive.append(t)
            nxt = t + iv + 1
        out[t] = [t - b for b in alive]
    return {t: out[t] for t in frames}


def set_visible(p, si, frames, u=0.5):
    """frames on which the set draws nothing (no live particle on any emitter)"""
    per = [eft_timing(p, x['data'], frames, u) for x in p.sets[si]['emitters']]
    return [t for t in frames if not any(pe[t] for pe in per)]


def timing_checks(p, sets, names):
    """skeleton v1.3 (the user: the skeleton "blinks out and back in", "have the fire effects be visible the entire time"):
    every looping set, as eft times it, draws something on every frame of 600 (its runs hand over: the next born on the
    last frame of the one before); the v1.2 - aerial chain v1 placement (a run's birth in 0x448) left gaps"""
    loops = [n for n, sp in sets if (sp.get('layers') or sp.get('blade') or
                                     (sp.get('atlas') and G.sidecar(sp['atlas'])['playback'] == 'loop'))]
    frames = list(range(600))
    gaps = {n: set_visible(p, 20 + names.index(n), frames) for n in loops}
    check('every looping set (%s) draws on every one of 600 frames (eft\'s timing)' % ', '.join(loops),
          {n: g[:5] for n, g in gaps.items() if g}, {})
    si = 20 + names.index('PtcGekkougaSkeletonR')
    ems = [bytearray(x['data']) for x in p.sets[si]['emitters']]
    for em in ems:                                     # the old placement: its birth in 0x448, emit start 0
        st = p.field(em, 'emit_start')
        p.set_field(em, 'emit_rate_random', st)
        p.set_field(em, 'emit_start', 0)
    per = [eft_timing(p, em, frames) for em in ems]
    old_gap = [t for t in frames if not any(pe[t] for pe in per)]
    both = [t for t in frames if all(pe[t] for pe in per)]
    check('the v1.2 placement in the same model: both runs from frame 0 (two cells drawn at once, frames 0 - 54), nothing '
          'from frame 57 to 109 (the user\'s clip: the skeleton seen ~58 frames, gone ~48, back)',
          (both[:1], both[-1:], old_gap[:1], old_gap[-1:] if old_gap and old_gap[-1] < 110 else [x for x in old_gap if x < 110][-1:]),
          ([0], [both[-1]] if both else [], [p.field(ems[0], 'ptcl_life')], [109]))   # (skeleton v1.7's slowed run: its
                                                   # first run lives 45, v1.2 - v1.6's 57)
    for n in loops:
        si = 20 + names.index(n)
        lives = [p.field(x['data'], 'ptcl_life') for x in p.sets[si]['emitters']]
        per = [eft_timing(p, x['data'], frames) for x in p.sets[si]['emitters']]
        dup = [t for t in frames if sum(len(pe[t]) for pe in per) > (len(per) if n in ('PtcGekkougaFireBlade',) or
                                                                       dict(sets)[n].get('layers') else 2)]
        if dup:
            check('%s: never more particles than its hand-overs allow' % n, dup[:5], [])


def base_step(img, d):
    """the median, over the cells, of the biggest alpha drop between two rows at the flame's base (its lowest row with
    alpha over 8 and the 8 rows above it)"""
    nx, ny = d['columns'], d['rows']
    h, w = img.shape[:2]
    out = []
    for k in range(d['frames']):
        i, j = k % nx, k // nx
        a = img[int(round(j * h / ny)):int(round((j + 1) * h / ny)), int(round(i * w / nx)):int(round((i + 1) * w / nx)),
                3].astype(float)
        m = a.max(1)
        rows = np.nonzero(m > 8)[0]
        if not len(rows):
            continue
        b = rows[-1]
        out.append(max(m[r] - m[r + 1] for r in range(max(0, b - 8), min(len(m) - 1, b + 2))))
    return float(np.median(out))


def soft_checks(p, sets, names):
    """fire trail fix v1 (the user: the trail flames' "hard, flat, cut-off bottom edge"): the fire sets' textures (as
    built: BC3 decoded) have soft bases (G.soften_bottom): the base's biggest row-to-row alpha drop, median over the
    cells, under 30 of 255 (the footage's own: 80 - 130; fire_torch_012's wisps 23 already)"""
    got, raw = {}, {}
    for n in ('PtcGekkougaFireBody', 'PtcGekkougaFireTip', 'PtcGekkougaFireTrail', 'PtcGekkougaFireBody1',
              'PtcGekkougaFireBody3'):
        sp = dict(sets)[n]
        sp = sp['layers'][0] if 'layers' in sp else sp   # (tuning v1: the trail's first layer)
        d = G.sidecar(sp['atlas'])
        em = p.sets[20 + names.index(n)]['emitters'][0]['data']
        got[n] = round(base_step(p.decode_texture(em, 0), d), 1)
        raw[n] = round(base_step(G.atlas(sp['atlas']), d), 1)
    check('fire trail fix v1: the fires\' flame bases soft (base alpha step, median, as built: %s; the footage\'s own %s)' %
          (got, raw), {n: v for n, v in got.items() if v >= 30}, {})


def tier_blade_checks(p, sets, names):
    """skeleton v1.3: the burn tiers' fires (the exe's BFX_TIER_IDS) and forward air's blade flames"""
    import gekkouga_clone_cave as C
    import gekkouga_build as GB
    ids = G.ids_of(sets)
    check('burn tiers: the exe\'s ids per tier 1 - 4 = FireBody1, FireBody (burn v2\'s), FireBody3, FireBody4',
          list(C.BFX_TIER_IDS[1:]), [ids[n] for n in ('PtcGekkougaFireBody1', 'PtcGekkougaFireBody', 'PtcGekkougaFireBody3',
                                                      'PtcGekkougaFireBody4')])
    hs = []
    for n in ('PtcGekkougaFireBody1', 'PtcGekkougaFireBody', 'PtcGekkougaFireBody3', 'PtcGekkougaFireBody4'):
        si = 20 + names.index(n)
        hs.append(max(round(p.field(x['data'], 'scale')[1], 1) for x in p.sets[si]['emitters']))
    check('burn tiers: each tier\'s fire taller than the one before (quad heights %s)' % hs, hs == sorted(hs) and len(set(hs)) == 4, True)
    si = 20 + names.index('PtcGekkougaFireBody4')
    ems = [x['data'] for x in p.sets[si]['emitters']]
    check('burn tier 4: two fires layered (fire_ground_10 and fire_small_5: 2 runs each), brighter (colour scale %s)' % G.FIRE_TIER4[0][2],
          (len(ems), sorted({round(p.field(x, 'color_scale'), 2) for x in ems})), (4, [G.FIRE_TIER4[0][2]]))
    for n in ('PtcGekkougaFireBody1', 'PtcGekkougaFireBody3', 'PtcGekkougaFireBody4'):
        si = 20 + names.index(n)
        fades = {round(struct.unpack('>f', bytes(x['data'][0x82C:0x830]))[0], 4) for x in p.sets[si]['emitters']}
        check('%s: fades over %d frames when the burns end (0x2723 (id, 0, 0))' % (n, G.FIRE_FADE), fades, {round(1.0 / G.FIRE_FADE, 4)})
    check('forward air\'s blade flames: the id gekkouga_build uses (FIRE_BLADE)', GB.FIRE_BLADE, ids['PtcGekkougaFireBlade'])
    si = 20 + names.index('PtcGekkougaFireBlade')
    fl = G.blade_flames()
    ems = [x['data'] for x in p.sets[si]['emitters']]
    feet = [round(-(p.field(e_, 'emitter_translation')[1] - (G.feet_cell_v(f_['atlas']) - 0.5) * p.field(e_, 'scale')[1]), 2)
            for e_, f_ in zip(ems, fl)]
    check('blade: %d flames, the clips in turn, their bases along the blade (%s down the joint), %.1fx the tip flame\'s '
          'clips\' ring heights, looping for ever (ended with the sword), at once when ended' % (
              len(fl), feet, G.FIRE_BLADE['size']),
          (len(ems), [f_['atlas'] for f_ in fl] == [G.RING_ASSETS[i % len(G.RING_ASSETS)][0] for i in range(len(fl))],
           feet == [round(f_['y'], 2) for f_ in fl], {p.field(e_, 'ptcl_life') for e_ in ems},
           {round(struct.unpack('>f', bytes(e_[0x82C:0x830]))[0], 2) for e_ in ems}),
          (G.FIRE_BLADE['n'], True, True, {G.FOREVER}, {1.0}))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) != 4:
        sys.exit(__doc__)
    van_dir, kirby_path, fx_pkg, built = a
    G.FX_PKG = fx_pkg
    burn2 = '--skeleton-only' not in sys.argv
    sets = G.all_sets(burn2)
    v = P.Ptcl(open(os.path.join(van_dir, 'gekkouga.010d0000.ptcl'), 'rb').read())
    ve = EFC.Efc(open(os.path.join(van_dir, 'gekkouga.010d0000.efc'), 'rb').read())
    p = P.Ptcl(open(os.path.join(built, 'gekkouga.010d0000.ptcl'), 'rb').read())
    e = EFC.Efc(open(os.path.join(built, 'gekkouga.010d0000.efc'), 'rb').read())
    kirby = P.Ptcl(open(kirby_path, 'rb').read())
    check('the bank: Ptcl.validate clean', p.validate(), [])
    check('his 20 vanilla sets unchanged (parameters, textures, shader keys)', vanilla_same(v, p), [])
    check('his 22 vanilla .efc entries unchanged', e.entries[:G.VANILLA_ENTRIES], ve.entries)
    names = [n for n, _s in sets]
    check('new sets after his 20, in order: %s' % ', '.join(names), [p.set_name(20 + i) for i in range(len(sets))], names)
    check('new .efc entries: flags 0x100, each its set (1-based)', e.entries[G.VANILLA_ENTRIES:],
          [[0x100, 21 + i, 0, 0, 0] for i in range(len(sets))])
    ids = G.ids_of(sets)
    src = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'skeleton.c')).read()
    used = {m.group(1): int(m.group(2), 16) for m in re.finditer(r'int (sk_fx_\w+)\(\) \{ return (0x[0-9a-f]+); \}', src)}
    check('skeleton.c\'s ids: body right / left, hit, explosion',
          [used.get(n) for n in ('sk_fx_body_r', 'sk_fx_body_l', 'sk_fx_spark', 'sk_fx_boom')],
          [ids[n] for n in names[:4]])
    ksi = kirby.find_set(G.TEMPLATE[0])
    ksh = kirby.field(kirby.sets[ksi]['emitters'][G.TEMPLATE[1]]['data'], 'shader_index')
    for i, (name, spec) in enumerate(sets):
        si = 20 + i
        if spec.get('ring'):
            ring_checks(p, si, name, spec, kirby, ksh)
            continue
        if spec.get('layers') or spec.get('blade'):
            continue                               # (timing_checks / tier_checks)
        d = G.sidecar(spec['atlas'])
        seq = G.flip_seq(d['frames'], spec.get('rate', 1.0))
        plan = G.flip_plan(d['frames'], d['frames_per_cell_at_60fps'], d['playback'] == 'loop', seq)
        ems = [x['data'] for x in p.sets[si]['emitters']]
        rows = []
        for em, run in zip(ems, plan):
            sh = p.field(em, 'shader_index')
            t = p.texres(em, 0)
            rows.append((bytes(p.shader_entry(sh))[:0x68] == bytes(kirby.shader_entry(ksh))[:0x68] and
                         bytes(p.shader_binary(sh)) == bytes(kirby.shader_binary(ksh)),
                         bool(struct.unpack_from('>I', em, 4)[0] & 0x00800000), p.field(em, 'particle_type'),
                         struct.unpack_from('>I', em, 0x310)[0], p.field(em, 'blend_type'),
                         (t['size'], t['native_format'], t['comp_sel'], t['sampler'], t['mip_levels']),
                         p.field(em, 'ptcl_life'), (p.field(em, 'emit_start'), p.field(em, 'emit_rate_random')),
                         [round(x, 3) for x in p.field(em, 'scale')], p.field(em, 'scale_random'),
                         p.field(em, 'figure_velocity'), p.field(em, 'gravity'), p.field(em, 'rotation_velocity'),
                         p.field(em, 'alpha_init'), p.field(em, 'volume_type')))
        want = [(True, False, 0, 0, spec['blend'], (d['atlas_size'], 7, 0x00010203, 0x22000100, 1), run['life'],
                 (run['start'], 0), [round(x, 3) for x in spec['size']], [0.0, 0.0], 0.0, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                 1.0, 0) for run in plan]
        check('%s: %d emitter(s) (%d cells, %s): Kirby\'s stone shader, CPU, billboard, follow 0, blend %d, BC3 %s RGBA '
              'clamped, life / emit start (0x44C; 0x448, the count\'s random, 0) %s, size %.2f x %.2f, still' %
              (name, len(plan), d['frames'], d['playback'], spec['blend'], d['atlas_size'],
               [(r['life'], r['start']) for r in plan], spec['size'][0], spec['size'][1]), rows, want)
        n, k = d['frames'], d['frames_per_cell_at_60fps']
        m = len(seq)                       # (skeleton v1.7: the run's slowed sequence, SK_RUN_RATE)
        loop = d['playback'] == 'loop'
        frames = range(0, 2 * m * k + 3) if loop else range(0, m * k)
        got = cells_shown(p, si, frames)
        bad = []
        for fr in frames:
            c = seq[(fr // k) % m]
            ok = got[fr] == [c] or (len(plan) > 1 and fr % k == 0 and sorted(set(got[fr])) == sorted({c, seq[(fr // k - 1) % m]}))
            if not ok:
                bad.append((fr, got[fr], c))
        handovers = sum(1 for fr in frames if len(got[fr]) > 1)
        check('%s: the flipbook as eft plays it (latte_exec): each of %d frames shows entry (frame / %d) mod %d of its %s%s' %
              (name, len(frames), k, m, 'cells' if m == n else 'slowed sequence (%d cells, every %dth twice: rate %.3f)' % (
                  n, n // (m - n) if m > n else 0, spec.get('rate', 1.0)), ', the hand-overs (%d) also the cell before' % handovers if len(plan) > 1 else ''),
              bad[:5], [])
        if not loop:
            check('%s: a one-shot: nothing drawn after its %d frames' % (name, n * k),
                  cells_shown(p, si, [n * k + 1, n * k + 30]), {n * k + 1: [], n * k + 30: []})
    # placement
    _n, body = sets[0]
    h = body['size'][1]
    tr = p.field(p.sets[20]['emitters'][0]['data'], 'emitter_translation')
    feet = tr[1] + h / 2 - G.feet_cell_v('skeleton_run') * h
    check('skeleton: its feet on the call\'s point (y %.3f) and its body (alpha >= 0.5 rows %.3f - %.3f of a cell) %.2f tall'
          % (feet, G.SK_BODY_TOP_V, G.SK_BODY_BOTTOM_V, (G.SK_BODY_BOTTOM_V - G.SK_BODY_TOP_V) * h),
          (round(feet, 3), round((G.SK_BODY_BOTTOM_V - G.SK_BODY_TOP_V) * h, 2)), (0.0, G.SK_BODY_H))
    _n, boom = sets[3]
    tb = p.field(p.sets[23]['emitters'][0]['data'], 'emitter_translation')
    check('explosion: its base on the call\'s point, %.1f wide at its widest (the hitbox\'s 22 x 2)' %
          (boom['size'][0] * G.SK_BOOM_WIDEST_U),
          (round(tb[1] + boom['size'][1] / 2 - G.SK_BOOM_BASE_V * boom['size'][1], 3), round(boom['size'][0] * G.SK_BOOM_WIDEST_U, 2)),
          (0.0, G.SK_BOOM_DIAMETER))
    if burn2:
        import gekkouga_clone_cave as C
        import gekkouga_build as GB
        tsrc = open(os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'firetrail.c')).read()
        m = re.search(r'int tr_fx\(\) \{ return (0x[0-9a-f]+); \}', tsrc)
        check('burn v2 ids: the fire on burning fighters (the exe\'s BFX_ID), at his water\'s ends (gekkouga_build FIRE_TIP), '
              'the trails (firetrail.c tr_fx), v2.2: neutral air\'s ring (FIRE_RING)',
              [C.BFX_ID, GB.FIRE_TIP, int(m.group(1), 16) if m else None, GB.FIRE_RING, GB.FIRE_RING_L],
              [ids['PtcGekkougaFireBody'], ids['PtcGekkougaFireTip'], ids['PtcGekkougaFireTrail'], ids['PtcGekkougaFireRing'],
               ids['PtcGekkougaFireRingL']])
        for nm, base in (('PtcGekkougaFireBody', 'fire_small_4'), ('PtcGekkougaFireTrail', 'fire_ground_10')):
            spec = dict(sets)[nm]
            if 'layers' in spec:          # tuning v1: the trail's first layer (its wide fire_ground_10)
                spec = spec['layers'][0]
            si = 20 + names.index(nm)
            t = p.field(p.sets[si]['emitters'][0]['data'], 'emitter_translation')
            h = spec['size'][1]
            check('%s: the flame\'s base (%s\'s anchor) on the call\'s point, %.0f units tall, additive, fade 1 / %d' % (
                nm, base, h, G.FIRE_FADE), (round(t[1] + h / 2 - G.feet_cell_v(base) * h, 3), spec['blend'],
                round(struct.unpack('>f', bytes(p.sets[si]['emitters'][0]['data'][0x82C:0x830]))[0], 4)),
                  (0.0, 1, round(1.0 / G.FIRE_FADE, 4)))
        si = 20 + names.index('PtcGekkougaFireTip')
        check('PtcGekkougaFireTip: centred on the call (the sword\'s tip), additive, %.0f tall at size 1' % G.FIRE_TIP_H,
              (p.field(p.sets[si]['emitters'][0]['data'], 'emitter_translation'), dict(sets)['PtcGekkougaFireTip']['blend']),
              ([0.0, 0.0, 0.0], 1))
    if burn2 and G.TRAIL_FULL:
        si = 20 + names.index('PtcGekkougaFireTrail')
        ly = dict(sets)['PtcGekkougaFireTrail']['layers']
        ems = p.sets[si]['emitters']
        sc = [p.field(em['data'], 'scale') for em in ems]
        w0 = G.FIRE_TRAIL_H * G.cell_aspect('fire_ground_10')
        check('tuning v1 (the user: "make the trail fire more full"): PtcGekkougaFireTrail two layers: fire_ground_10 %.2f wide '
              '(x%.1f), %g tall; fire_small_5 mirrored, %g tall (x%.1f wide), slower (0.8)' % (
                  w0 * G.TRAIL_WIDE, G.TRAIL_WIDE, G.FIRE_TRAIL_H, G.FIRE_TRAIL_H * G.TRAIL_SECOND, G.TRAIL_WIDE),
              ([l_['atlas'] for l_ in ly], [round(x, 3) for x in sc[0][:2]], ly[1].get('mirror'), ly[1].get('rate')),
              (['fire_ground_10', 'fire_small_5'], [round(w0 * G.TRAIL_WIDE, 3), G.FIRE_TRAIL_H], True, 0.8))
    timing_checks(p, sets, names)
    if burn2:
        tier_blade_checks(p, sets, names)
        soft_checks(p, sets, names)
    r = p.decode_texture(p.sets[20]['emitters'][0]['data'], 0).astype(np.float32)
    lft = p.decode_texture(p.sets[21]['emitters'][0]['data'], 0).astype(np.float32)
    dif = np.abs(G.mirror_cells(r, 6, 10) - lft).mean()
    check('skeleton left: its atlas the right\'s with each cell mirrored (mean difference %.2f of 255, BC3)' % dif, dif < 2.0, True)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
