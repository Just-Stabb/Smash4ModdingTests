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
        d = G.sidecar(spec['atlas'])
        plan = G.flip_plan(d['frames'], d['frames_per_cell_at_60fps'], d['playback'] == 'loop')
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
                         p.field(em, 'ptcl_life'), p.field(em, 'start_frame'),
                         [round(x, 3) for x in p.field(em, 'scale')], p.field(em, 'scale_random'),
                         p.field(em, 'figure_velocity'), p.field(em, 'gravity'), p.field(em, 'rotation_velocity'),
                         p.field(em, 'alpha_init'), p.field(em, 'volume_type')))
        want = [(True, False, 0, 0, spec['blend'], (d['atlas_size'], 7, 0x00010203, 0x22000100, 1), run['life'],
                 run['start'], [round(x, 3) for x in spec['size']], [0.0, 0.0], 0.0, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                 1.0, 0) for run in plan]
        check('%s: %d emitter(s) (%d cells, %s): Kirby\'s stone shader, CPU, billboard, follow 0, blend %d, BC3 %s RGBA '
              'clamped, life / start %s, size %.2f x %.2f, still' %
              (name, len(plan), d['frames'], d['playback'], spec['blend'], d['atlas_size'],
               [(r['life'], r['start']) for r in plan], spec['size'][0], spec['size'][1]), rows, want)
        n, k = d['frames'], d['frames_per_cell_at_60fps']
        loop = d['playback'] == 'loop'
        frames = range(0, 2 * n * k + 3) if loop else range(0, n * k)
        got = cells_shown(p, si, frames)
        bad = []
        for fr in frames:
            c = (fr // k) % n
            ok = got[fr] == [c] or (len(plan) > 1 and fr % k == 0 and sorted(got[fr]) == sorted([c, (c - 1) % n]))
            if not ok:
                bad.append((fr, got[fr], c))
        handovers = sum(1 for fr in frames if len(got[fr]) > 1)
        check('%s: the flipbook as eft plays it (latte_exec): each of %d frames shows cell (frame / %d) mod %d%s' %
              (name, len(frames), k, n, ', the hand-overs (%d) also the cell before' % handovers if len(plan) > 1 else ''),
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
              'the trails (firetrail.c tr_fx)', [C.BFX_ID, GB.FIRE_TIP, int(m.group(1), 16) if m else None],
              [ids['PtcGekkougaFireBody'], ids['PtcGekkougaFireTip'], ids['PtcGekkougaFireTrail']])
        for nm, base in (('PtcGekkougaFireBody', 'fire_small_4'), ('PtcGekkougaFireTrail', 'fire_ground_10')):
            spec = dict(sets)[nm]
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
    r = p.decode_texture(p.sets[20]['emitters'][0]['data'], 0).astype(np.float32)
    lft = p.decode_texture(p.sets[21]['emitters'][0]['data'], 0).astype(np.float32)
    dif = np.abs(G.mirror_cells(r, 6, 10) - lft).mean()
    check('skeleton left: its atlas the right\'s with each cell mirrored (mean difference %.2f of 255, BC3)' % dif, dif < 2.0, True)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
