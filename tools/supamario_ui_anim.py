#!/usr/bin/env python3
"""Supamario's Ultra Instinct (fighters/supamario/README.md "Ultra Instinct v1"; Dragon Ball Xenoverse 2's Awoken Skill
1510_GKS_MGT, "Ultra Instinct -Sign-"): three motions retargeted from the skill's own EAN as the earlier ports'
(`xv2ean.retarget`, 5.04 units a metre, no TransN: the MSC places him; the pelvis's height on RotN, Fake Death's
floor_fix).

  python3 -I tools/supamario_ui_anim.py BODY_MOTION_DIR MODEL_VBN 1510_GKS_MGT.ean OUT_DIR CMN.ean 1352_HIK_DSH.ean

The EAN (the default body "_C"; `_F` / `_MAM` the other builds) has two animations:
  #0 GKS_MET_MGT_00_C (325 frames), BAC entry 0: the stance (0-30 into it, the counter window 30-151), the power-up
     (151-228: the burst at 220), then back.
  #1 GKS_MET_MGT_01_C (500 frames), BAC entries 1 / 2 (the counter): #0's first 151 frames, then the vanish (151-176:
     the root 3.3 m forward at 159-161, invulnerable), the rush (176-282: hits every 5 frames, the finisher BDM #2 at
     280), the recovery to 350.
v2 (the user's XV2 clips: XV2's own length, the rush counter):
  SpecialLwLight (0x231, the transformation, 325 frames): #0 0-324 1:1 (the window 30-151, the burst at 220).
  SpecialLwHeavy (0x235, the counter, 349 frames): #1 151-499 1:1 (the vanish, the rush 210-275, the finisher at 280:
     motion frame 129, the end 350).
  SpecialAirLwLight (0x241, the autododge, 16 frames): #1 151-167 1:1 (the vanish's first frames).
  SpecialAirLwHeavy (0x245, Secret Sensation's stance, 45 frames): #0 0-40 in 18 (into the stance), 40-151 in 27 (the
     counter stance held: XV2's window). Its slide is Mario's own spot dodge (EscapeN), the user's.
They were F.L.U.D.D.'s shoot motions (unreachable since Fake Death / Sledgehammer).
v7 (the user: the autododge "XV2 Sway", "Different motion"; its counter): SpecialAirLwLight (0x241; its custom-move
slots 0x242 / 0x243 play the same animation, the game's motion table: one hash for 0x241-0x244) holds three parts, from
XV2's CMN.ean (`--cmn-ean`, the user's chara/CMN) and the skill's EAN:
  frames 0-36   the back sway: CMN #189 CMN_SPA_ASW_B_L_S (CMN.bac 260 / 765): its frames 0-7 in one (TimeScale x7), then
                7-42 1:1 (37 frames); motion 0x241 from 0;
  frames 37-73  the forward sway: CMN #191 CMN_SPA_ASW_F_L_S, the same timeline; motion 0x243 from 37;
  frames 74-95  the counter (CMN.bac 706's 6-frame strike; its own animation, the character EAN's #30 / #31, isn't in the
                files; this skill's EAN #1 270-350 is the rush's arm held out sideways, no strike): XV2's straight
                right punch of Hit's Time Skip (1352_HIK_DSH.ean #1 HIK_SPA_DSH_01_C, `--hit-ean`): 8-14 in 3 (the
                fist out), 14-20 in 3 (held), 50-81 in 16 (back to the stance); motion 0x242 from 74.
The sways keep their own root lean (TransN's X / Z: up to 0.9 units back / 2.4 forward, back to 0 at the end: XV2's
Movement is none, the MSC doesn't move him).
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
FORM, STRIKE, DODGE, SS = 'SpecialLwLight.omo', 'SpecialLwHeavy.omo', 'SpecialAirLwLight.omo', 'SpecialAirLwHeavy.omo'
MOTIONS = (FORM, STRIKE, DODGE, SS)
PAC_TAG = {FORM: 'D03', STRIKE: 'D03', DODGE: 'D03', SS: 'D03'}
# (name, motion, EAN animation, source start, source end (exclusive), output frames)
# (name, motion, EAN animation, source start, source end (exclusive), output frames[, 'cmn': CMN.ean])
SEGMENTS = [
    ('form', FORM, 0, 0, 325, 325),          # v2 (the user's XV2 clip): entry 0's whole 325 frames, 1:1 at 60 fps
    ('counter', STRIKE, 1, 151, 500, 349),   # v2: entry 1 (the rush) from 151 to its end 499, 1:1
    ('sway_b_in', DODGE, 189, 0, 7, 1, 'cmn'),       # v7: XV2's sway, frames 0-7 at x7 (one frame)
    ('sway_b', DODGE, 189, 7, 43, 36, 'cmn'),        # 7-42 1:1
    ('sway_f_in', DODGE, 191, 0, 7, 1, 'cmn'),
    ('sway_f', DODGE, 191, 7, 43, 36, 'cmn'),
    ('ctr_out', DODGE, 1, 8, 14, 3, 'hit'),          # v7: the counter: Hit's straight punch (1352_HIK_DSH #1)
    ('ctr_hold', DODGE, 1, 14, 20, 3, 'hit'),
    ('ctr_back', DODGE, 1, 50, 81, 16, 'hit'),
    ('ss_in', SS, 0, 0, 40, 18),
    ('ss_hold', SS, 0, 40, 151, 27),
]
EAN_FRAMES = [325, 500]
CMN_ANIMS = {189: 'CMN_SPA_ASW_B_L_S', 191: 'CMN_SPA_ASW_F_L_S'}
HIT_ANIMS = {1: 'HIK_SPA_DSH_01_C'}
KEEP_TRANS = ('sway_b_in', 'sway_b', 'sway_f_in', 'sway_f')   # their root lean kept (TransN X / Z)


def part_start(name):
    """the motion frame a segment starts on"""
    s = [x for x in SEGMENTS if x[0] == name][0]
    return [a for n, a, _b, _s in timeline(s[1]) if n == name][0]


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


def body_frames(ean, smash, motion, cmn=None, hit=None):
    frames, base, keep = [], [], []
    a0 = ean.animations[0]
    pel_ref = _local(ean, a0, 'b_C_Pelvis', 0)[0][1] + _local(ean, a0, 'b_C_Base', 0)[0][1]
    for f in range(frames_of(motion)):
        s, ai, sf = source(motion, f)
        e = {'cmn': cmn, 'hit': hit}.get(s[6], ean) if len(s) > 6 else ean
        a = e.animations[ai]
        if len(s) > 6:
            assert a.name == {'cmn': CMN_ANIMS, 'hit': HIT_ANIMS}[s[6]][ai], (ai, a.name)
        frames.append(X.retarget(e, a, smash, at=[sf], root_scale=SCALE)[0])
        by = _local(e, a, 'b_C_Base', sf)[0][1]
        base.append((_local(e, a, 'b_C_Pelvis', sf)[0][1] + by, by))
        keep.append(s[0] in KEEP_TRANS)
    rot_rest = frames[0]['RotN'][0]
    for f, fr in enumerate(frames):
        t = fr['TransN'][0]
        fr['TransN'] = (((t[0], 0.0, t[2]) if keep[f] else (0.0, 0.0, 0.0)), fr['TransN'][1], fr['TransN'][2])
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (base[f][0] - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1],
                      fr['RotN'][2])
    return frames, [b[1] for b in base]


def build(motion_dir, vbn_path, ean_path, out_dir, cmn_ean_path=None, hit_ean_path=None):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    assert [a.frames for a in ean.animations] == EAN_FRAMES, [(a.name, a.frames) for a in ean.animations]
    cmn = X.Ean(open(cmn_ean_path, 'rb').read(), smash_axes=True) if cmn_ean_path else None
    hit = X.Ean(open(hit_ean_path, 'rb').read(), smash_axes=True) if hit_ean_path else None
    assert cmn is not None and hit is not None or not any(len(s) > 6 for s in SEGMENTS), \
        'v7: the sways need CMN.ean, the counter 1352_HIK_DSH.ean'
    smash = X.vbn_rest(vbn_path)
    info, per = {}, {}
    for m in MOTIONS:
        frames, base_y = body_frames(ean, smash, m, cmn, hit)
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
    if len(a) != 6:
        sys.exit(__doc__)
    out, _bones, info = build(*a)
    for m in MOTIONS:
        o = out[('main', m)]
        print('%s: %d frames; RotN moved %.2f .. %.2f' % (m, o.frames, min(info['info'][m]['rotn_offsets']),
                                                         max(info['info'][m]['rotn_offsets'])))


if __name__ == '__main__':
    main()
