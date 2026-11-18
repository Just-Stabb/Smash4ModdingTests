#!/usr/bin/env python3
"""Supamario's Ultra Instinct (fighters/supamario/README.md "Ultra Instinct v1"; Dragon Ball Xenoverse 2's Awoken Skill
1510_GKS_MGT, "Ultra Instinct -Sign-"): three motions retargeted from the skill's own EAN as the earlier ports'
(`xv2ean.retarget`, 5.04 units a metre, no TransN: the MSC places him; the pelvis's height on RotN, Fake Death's
floor_fix).

  python3 -I tools/supamario_ui_anim.py BODY_MOTION_DIR MODEL_VBN 1510_GKS_MGT.ean OUT_DIR

The EAN (the default body "_C"; `_F` / `_MAM` the other builds) has two animations:
  #0 GKS_MET_MGT_00_C (325 frames), BAC entry 0: the stance (0-30 into it, the counter window 30-151), the power-up
     (151-228: the burst at 220), then back.
  #1 GKS_MET_MGT_01_C (500 frames), BAC entries 1 / 2 (the counter): #0's first 151 frames, then the vanish (151-176:
     the root 3.3 m forward at 159-161, invulnerable), the rush (176-282: hits every 5 frames, the finisher BDM #2 at
     280), the recovery to 350.
The user's spec is about 60 frames for the transformation and one strike for the counter, so (motion, EAN animation,
source frames, output frames):
  SpecialLwLight (0x231, the transformation, 60 frames): #0 0-30 in 12, 30-151 in 18, 151-229 in 30 (the burst at 57).
  SpecialLwHeavy (0x235, the counter's strike, 58 frames): #1 151-176 in 8 (the vanish / reappearance), 270-320 1:1
     (the finisher: XV2's 280 at frame 18).
  SpecialAirLwLight (0x241, the autododge, 16 frames): #1 151-167 1:1 (the vanish's first frames).
They were F.L.U.D.D.'s shoot motions (unreachable since Fake Death / Sledgehammer).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402
import supamario_fakedeath_anim as FA  # noqa: E402

SCALE = 5.04
FORM, STRIKE, DODGE = 'SpecialLwLight.omo', 'SpecialLwHeavy.omo', 'SpecialAirLwLight.omo'
MOTIONS = (FORM, STRIKE, DODGE)
PAC_TAG = {FORM: 'D03', STRIKE: 'D03', DODGE: 'D03'}
# (name, motion, EAN animation, source start, source end (exclusive), output frames)
SEGMENTS = [
    ('stance', FORM, 0, 0, 30, 12),
    ('window', FORM, 0, 30, 151, 18),
    ('powerup', FORM, 0, 151, 229, 30),
    ('vanish', STRIKE, 1, 151, 176, 8),
    ('finisher', STRIKE, 1, 270, 320, 50),
    ('dodge', DODGE, 1, 151, 167, 16),
]
EAN_FRAMES = [325, 500]


def timeline(motion=None):
    out, f = {}, {}
    for s in SEGMENTS:
        a = f.get(s[1], 0)
        out.setdefault(s[1], []).append((s[0], a, a + s[5], s))
        f[s[1]] = a + s[5]
    return out if motion is None else out[motion]


def frames_of(motion):
    return sum(s[5] for s in SEGMENTS if s[1] == motion)


def source(motion, f):
    """(segment, EAN animation, EAN frame) shown on motion frame f"""
    for _name, a, b, s in timeline(motion):
        if a <= f < b:
            return s, s[2], s[3] + (s[4] - s[3]) * (f - a) / float(s[5])
    s = [x for x in SEGMENTS if x[1] == motion][-1]
    return s, s[2], float(s[4] - 1)


def frame_of(motion, anim, xv2):
    """the motion frame showing XV2 frame `xv2` of EAN animation `anim` (the first segment holding it)"""
    for _name, a, b, s in timeline(motion):
        if s[2] == anim and s[3] <= xv2 < s[4]:
            return int(round(a + (xv2 - s[3]) * s[5] / float(s[4] - s[3])))
    raise ValueError((motion, anim, xv2))


def _local(ean, anim, name, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi[name], f)


def body_frames(ean, smash, motion):
    frames, base = [], []
    a0 = ean.animations[0]
    pel_ref = _local(ean, a0, 'b_C_Pelvis', 0)[0][1] + _local(ean, a0, 'b_C_Base', 0)[0][1]
    for f in range(frames_of(motion)):
        _s, ai, sf = source(motion, f)
        a = ean.animations[ai]
        frames.append(X.retarget(ean, a, smash, at=[sf], root_scale=SCALE)[0])
        by = _local(ean, a, 'b_C_Base', sf)[0][1]
        base.append((_local(ean, a, 'b_C_Pelvis', sf)[0][1] + by, by))
    rot_rest = frames[0]['RotN'][0]
    for f, fr in enumerate(frames):
        fr['TransN'] = ((0.0, 0.0, 0.0), fr['TransN'][1], fr['TransN'][2])     # the MSC places him
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (base[f][0] - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1],
                      fr['RotN'][2])
    return frames, [b[1] for b in base]


def build(motion_dir, vbn_path, ean_path, out_dir):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    assert [a.frames for a in ean.animations] == EAN_FRAMES, [(a.name, a.frames) for a in ean.animations]
    smash = X.vbn_rest(vbn_path)
    info, per = {}, {}
    for m in MOTIONS:
        frames, base_y = body_frames(ean, smash, m)
        offs, contact = FA.floor_fix(frames, smash, base_y)
        per[m] = frames
        info[m] = {'rotn_offsets': offs, 'contact': contact,
                   'source': [round(source(m, f)[2], 3) for f in range(frames_of(m))]}
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for part, prefix in (('main', 'FitMarioBodyMain'), ('mariopt1', 'FitMarioBodyMariopt1'),
                         ('lhand', 'FitMarioBodyLhand'), ('rhand', 'FitMarioBodyRhand')):
        entries = omo.pac_read(os.path.join(motion_dir, part + '.pac'))
        e = dict(entries)
        repl = {}
        for m in MOTIONS:
            names = [n for n in e if n.startswith(prefix) and n.endswith(PAC_TAG[m] + m)]
            assert len(names) == 1, (part, m, names)
            o = X.to_omo(per[m], e[names[0]], smash)
            assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[names[0]]).nodes]
            assert o.frames == frames_of(m), (m, o.frames)
            repl[names[0]] = o.encode()
            out[(part, m)] = o
        omo.pac_write(os.path.join(out_dir, part + '.pac'), [(n, repl.get(n, d)) for n, d in entries])
    return out, omo.vbn_read(vbn_path), {'info': info, 'frames': per, 'smash': smash}


def joints(frames, smash):
    return FA.joints(frames, smash)


def main():
    a = sys.argv[1:]
    if len(a) != 4:
        sys.exit(__doc__)
    out, _bones, info = build(*a)
    for m in MOTIONS:
        o = out[('main', m)]
        print('%s: %d frames; RotN moved %.2f .. %.2f' % (m, o.frames, min(info['info'][m]['rotn_offsets']),
                                                         max(info['info'][m]['rotn_offsets'])))


if __name__ == '__main__':
    main()
