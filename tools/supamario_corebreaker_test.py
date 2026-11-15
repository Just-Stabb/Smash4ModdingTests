#!/usr/bin/env python3
"""Core Breaker (Supamario's up special) phase 1 checks: the converted effects and the animation.

  python3 -I tools/supamario_corebreaker_test.py FX_OUT_DIR ANIM_OUT_DIR MODEL_VBN

FX_OUT_DIR: tools/supamario_corebreaker_fx.py's OUT_DIR (corebreaker_fx.json, effect/supamario/...). ANIM_OUT_DIR:
tools/supamario_corebreaker_anim.py's OUT_DIR (main.pac, corebreaker_frames.json).
- facing (the God Fist's rule, v6 / v7): every effect call on bone 0 with offsets only up / forward and turns only
  Y 0 / 180, or on a body bone with no offset / turn; every converted emitter unturned at the origin, a full-sphere
  spread when directional or moving; the effect's place the same facing left as right (bone 0 turned 180);
- vibrance: no emitter drawn past the HDR cap; refraction emitters hidden, no refraction model;
- scale: every call's size is XV2's x SIZE;
- animation: SpecialHi and SpecialAirHi the same motion, TransN rising RISE_HEIGHT over the rise, the feet on the floor
  on the ground segments, the vanilla node order.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import ptcl  # noqa: E402
import supamario_corebreaker_anim as A  # noqa: E402
import xv2_smash_fx as FX  # noqa: E402


def main():
    a = sys.argv[1:]
    if len(a) != 3:
        sys.exit(__doc__)
    fx_dir, anim_dir, vbn = a
    probs = []
    doc = json.load(open(os.path.join(fx_dir, 'corebreaker_fx.json')))
    calls = []
    for e in doc['effects']:
        for pt in e['parts']:
            if 'bone' not in pt:
                continue
            calls.append({'name': '%d %s' % (e['bac_effect'], pt['xv2']), 'bone': pt['bone'], 'offset': pt['offset'],
                          'rot': pt['rot']})
            if abs(pt['size'] - pt['xv2_scale'] * FX.SIZE) > 1e-3:
                probs.append('%d %s: size %g, not XV2 %g x %g' % (e['bac_effect'], pt['xv2'], pt['size'],
                                                                  pt['xv2_scale'], FX.SIZE))
            # facing left = bone 0 turned 180 about Y: the place mirrors across his body, the height is the same
            if pt['bone'] == 'bone 0 (TopN)':
                x, y, z = pt['offset']
                right, left = (x, y, z), (-x, y, -z)
                if abs(right[0]) > 1e-6 or right[1] != left[1] or abs(right[2] + left[2]) > 1e-6:
                    probs.append('%d %s: not mirrored alike' % (e['bac_effect'], pt['xv2']))
    probs += FX.facing_check(calls)
    p = ptcl.Ptcl(open(os.path.join(fx_dir, 'effect', 'supamario', 'supamario.010d0000.ptcl'), 'rb').read())
    sets = [p.find_set(s['set']) for v in doc['sets'].values() for s in v]
    probs += FX.facing_emitters(p, sets)
    for si in sets:
        for em in p.sets[si]['emitters']:
            d = em['data']
            if d is None or p.field(d, 'alpha_init') <= 0:
                continue
            peak = max(max(k[:3]) for t in (0, 1) for k in p.color_keys(d, t)) * p.field(d, 'color_scale')
            if peak > FX.HDR_CAP + 1e-3 and p.field(d, 'blend_type') != FX.BLEND_SUB:
                probs.append('set %d: drawn at %.2f, past the cap %.2f' % (si, peak, FX.HDR_CAP))
    hidden = [n for n in doc['emitter_notes'] if 'refraction' in n]
    if any('folder' in m for k, m in doc['models'].items() if k.startswith('Cor_Wev')):
        probs.append('Cor_Wev (refraction) converted')
    # the animation
    fr = json.load(open(os.path.join(anim_dir, 'corebreaker_frames.json')))
    bones = omo.vbn_read(vbn)
    ents = dict(omo.pac_read(os.path.join(anim_dir, 'main.pac')))
    hi = [ents[n] for n in ents if n.endswith('SpecialHi.omo') and 'Air' not in n][0]
    air = [ents[n] for n in ents if n.endswith('SpecialAirHi.omo')][0]
    if hi != air:
        probs.append('SpecialHi and SpecialAirHi differ')
    o = omo.Omo(hi)
    seg = {s['name']: s for s in fr['segments']}
    top = omo.world(o, bones, seg['rise']['end'])['TransN'][1][3]
    if A.ROOT_IN_MOTION and abs(top - A.RISE_HEIGHT) > 0.05:
        probs.append('the rise reaches %.2f, not %.2f' % (top, A.RISE_HEIGHT))
    for s in fr['segments']:
        if not s['ground']:
            continue
        for f in range(s['start'], s['end'] + 1):
            w = omo.world(o, bones, f)
            ty = w['TransN'][1][3]
            low = min(w[n][1][3] for n in ('LFootJ', 'RFootJ')) - ty
            # on the floor, or lifted only as far as a joint needs (the head-first frames: a joint at its FLOOR)
            lift = min((w[n][1][3] - ty) - A.FLOOR[n] for n in A.FLOOR)
            if not (abs(low - A.STAND_FOOT) < 0.05 or (low > A.STAND_FOOT and abs(lift) < 0.05)):
                probs.append('frame %d (%s): his lower foot %.2f over the floor' % (f, s['name'], low - A.STAND_FOOT))
                break
    print('%d effect calls, %d converted sets, %d refraction emitters hidden; %d frames' % (
        len(calls), len(sets), len(hidden), o.frames))
    for x in probs:
        print('PROBLEM', x)
    print('%d problem(s)' % len(probs))
    sys.exit(1 if probs else 0)


if __name__ == '__main__':
    main()
