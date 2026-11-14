#!/usr/bin/env python3
"""Supamario's Super God Fist (dash attack): the AttackDash animation (body main / lhand / rhand / mariopt1),
retargeted from Xenoverse 2's own skill animations (030_GOD_CSA.ean) since v3.

  python3 tools/supamario_godfist_anim.py BODY_MOTION_DIR MODEL_VBN GOD_CSA.ean OUT_DIR [--png SHEET.png]

BODY_MOTION_DIR: his motion/body/ (main / lhand / rhand / mariopt1 .pac, Mario's names: the RPX's motion table
finds them by name). Writes OUT_DIR/{main,lhand,rhand,mariopt1}.pac with FitMarioBody*C00AttackDash.omo replaced
(every other entry byte for byte the input's).

The skill's EAN (the default body, `030_GOD_CSA.ean`; `_F` female and `_MAM` heavy male bodies hold the same moves
posed for those builds: C is the one for Mario) has four animations: #1 GOD_SPA_CSA_MISS_C (71 frames: the dash
punch, played by BAC entry 0; it goes on past the target when nothing is hit), #0 GOD_SPA_CSA_C (112: the follow-up,
BAC entry 1 on connect: the fist held in 0-40 at x0.8, a flip away 40-60, back to a stance by 111), #3 / #2 the
same for the other BCM variant. #0 frame 0 is #1 frame 15's pose: the follow-up starts at the contact.

XV2 is left-handed with characters facing -Z: read through `xv2ean.Ean(smash_axes=True)` (mirrored z -> -z: facing
+Z, the right hand still the right), retargeted bone by bone (`xv2ean.retarget`, its world-space turns, the fingers
too) onto Mario's skeleton. The timeline (frames at 60 a second, XV2's too):

  0-44     the dash punch, #1 0-18 at XV2's speed (the hitbox 14-17 as the BAC's, the fist out at 14-15), then
           #1 18-70 twice as fast: the whiff ends at 44 (MSC: GF_WHIFF_END)
  46-166   the God Fist (the MSC jumps here from the hit check at 18, GF_JUMP_TO = 46): #0 0-40 at x0.8 (the BAC's
           TimeScale: 50 frames, the fist held in the victim), the God Fist hit at #0 40 (GF_STRIKE = 96), then
           #0 40-111 at its speed (the flip away 40-60, the stance by 111)
  TransN   #1's dash (b_C_Base) x the body scale up to the contact, x0.3 after (a whiff slides 28 in all, as vanilla
           Mario's dash attack); #0's travel (2.5 m forward, mostly in the flip) x0.5
  RotN     the pelvis' height changes (XV2 crouches, leaps and flips), then the lower foot put on the floor on
           every frame (XV2 fights in the air: its dash leaps and its hold hangs), except over the flip (#0 40-62:
           lifted only where the head, hands, knees or feet would go into the floor)
Every motion keeps the vanilla AttackDash's node order (vbn order, which the game reads the gameplay joints by).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402

PUNCH_ANIM, GODFIST_ANIM = 1, 0       # 030_GOD_CSA.ean (#3 / #2: the other BCM variant's)
SCALE = 5.04                          # metres -> units: Mario's hip-to-foot 3.93 / XV2's pelvis-to-foot 0.78
CONTACT = 15                          # #1's frame where #0 begins (the same pose)
GF_PUNCH = 14                         # the hitbox 14-17 (BAC entry 0)
GF_PUNCH_END = 18                     # the hit check
WHIFF_FAST_FROM, WHIFF_RATE = 18, 2.0
GF_WHIFF_END = int(WHIFF_FAST_FROM + (70 - WHIFF_FAST_FROM) / WHIFF_RATE)      # 44
GF_JUMP_TO = GF_WHIFF_END + 2         # 46
SLOW, HOLD_SRC = 0.8, 40              # BAC entry 1: TimeScale 0.8 for #0 0-40
GF_HOLD = int(round(HOLD_SRC / SLOW))                                         # 50
GF_STRIKE = GF_JUMP_TO + GF_HOLD      # 96: #0 frame 40
GODFIST_END_SRC = 111
FRAMES = GF_STRIKE + (GODFIST_END_SRC - HOLD_SRC) + 1                          # 168
WHIFF_ROOT = 0.3                      # the dash past the contact (whiff)
GODFIST_ROOT = 0.5                    # #0's own travel
# the lowest the joints may go (units above the floor; Mario's foot joint is 1.56 up when standing)
FLOOR = {'HeadN': 3.0, 'LHandN': 1.0, 'RHandN': 1.0, 'LFootJ': 1.3, 'RFootJ': 1.3, 'LToeN': 0.4, 'RToeN': 0.4,
         'LKneeJ': 1.5, 'RKneeJ': 1.5}
STAND_FOOT = 1.56


def source(f):
    """(animation, source frame) at output frame f"""
    if f < GF_JUMP_TO:
        if f <= WHIFF_FAST_FROM:
            return PUNCH_ANIM, float(f)
        return PUNCH_ANIM, min(70.0, WHIFF_FAST_FROM + (min(f, GF_WHIFF_END) - WHIFF_FAST_FROM) * WHIFF_RATE)
    u = f - GF_JUMP_TO
    if u <= GF_HOLD:
        return GODFIST_ANIM, u * SLOW
    return GODFIST_ANIM, min(float(GODFIST_END_SRC), HOLD_SRC + (u - GF_HOLD))


def _pelvis_and_base(ean, anim, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi['b_C_Pelvis'], f)[0], ean.local(anim, bi['b_C_Base'], f)[0]


def root_z(ean, f):
    a, sf = source(f)
    punch = ean.animations[PUNCH_ANIM]
    b0 = _pelvis_and_base(ean, punch, 0)[1][2]
    bc = _pelvis_and_base(ean, punch, CONTACT)[1][2]
    if a == PUNCH_ANIM:
        b = _pelvis_and_base(ean, punch, sf)[1][2]
        if sf <= CONTACT:
            return (b - b0) * SCALE
        return (bc - b0) * SCALE + (b - bc) * SCALE * WHIFF_ROOT
    gf = ean.animations[GODFIST_ANIM]
    g0 = _pelvis_and_base(ean, gf, 0)[1][2]
    return (bc - b0) * SCALE + (_pelvis_and_base(ean, gf, sf)[1][2] - g0) * SCALE * GODFIST_ROOT


def body_frames(ean, smash):
    """[{bone: (pos, quat, scale)}] for every output frame (TransN / RotN set)"""
    out = []
    for f in range(FRAMES):
        a, sf = source(f)
        fr = X.retarget(ean, ean.animations[a], smash, at=[sf], root_scale=SCALE)[0]
        out.append(fr)
    punch = ean.animations[PUNCH_ANIM]
    pel_ref = _pelvis_and_base(ean, punch, 0)[0][1]
    rot_rest = fr['RotN'][0]
    for f, fr in enumerate(out):
        a, sf = source(f)
        pel = _pelvis_and_base(ean, ean.animations[a], sf)[0][1]
        fr['TransN'] = ((0.0, 0.0, root_z(ean, f)), fr['TransN'][1], fr['TransN'][2])
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (pel - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1], fr['RotN'][2])
    return out


def world_y(frames, smash, bones_vbn, f):
    """{bone: world y} of frame f (TransN's own height left out)"""
    import omo as _o
    par = {b[0]: b[1] for b in smash}
    names = [b[0] for b in smash]
    w = {}
    for i, n in enumerate(names):
        p, q, s = frames[f][n]
        local = _o.trs(p, q, s)
        w[n] = _o.mul(w[names[par[n]]], local) if par[n] >= 0 else local
    return {n: w[n][1][3] for n in FLOOR}


FLIP = (GF_STRIKE, GF_STRIKE + 22)    # #0 40-62: XV2's flip (in the air there): only lifted, not put down


def floor_fix(frames, smash):
    """RotN moved so the lower foot stands on the floor (STAND_FOOT) on every frame (XV2 fights in the air: its dash
    leaps, its hold hangs; on Smash's ground he stays on it), except over the flip (FLIP, ramped in / out over 4
    frames) where it is only lifted wherever a joint would go under FLOOR; returns the offsets"""
    offs = []
    for f in range(len(frames)):
        y = world_y(frames, smash, None, f)
        snap = STAND_FOOT - min(y['LFootJ'], y['RFootJ'])
        lift = max(0.0, max(FLOOR[n] - y[n] for n in FLOOR))
        w = 1.0
        if FLIP[0] - 4 < f < FLIP[1] + 4:
            w = max(0.0, min(1.0, (FLIP[0] - f) / 4.0, (f - FLIP[1]) / 4.0))
        offs.append(max(w * snap + (1 - w) * lift, lift))
    for f, fr in enumerate(frames):
        p, q, sc = fr['RotN']
        fr['RotN'] = ((p[0], p[1] + offs[f], p[2]), q, sc)
    return offs


def build(motion_dir, vbn_path, ean_path, out_dir):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    smash = X.vbn_rest(vbn_path)
    frames = body_frames(ean, smash)
    offs = floor_fix(frames, smash)
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for part, prefix in (('main', 'FitMarioBodyMain'), ('mariopt1', 'FitMarioBodyMariopt1'),
                         ('lhand', 'FitMarioBodyLhand'), ('rhand', 'FitMarioBodyRhand')):
        entries = omo.pac_read(os.path.join(motion_dir, part + '.pac'))
        e = dict(entries)
        name = [n for n in e if n.startswith(prefix) and n.endswith('AttackDash.omo')][0]
        o = X.to_omo(frames, e[name], smash)
        assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[name]).nodes]
        omo.pac_write(os.path.join(out_dir, part + '.pac'), [(n, o.encode() if n == name else d) for n, d in entries])
        out[part] = o
    return out, omo.vbn_read(vbn_path), {'rotn_offsets': offs}


def joint_offset(o, bones, joint, f):
    """a joint's (in front of TransN, up) at frame f"""
    w = omo.world(o, bones, f)
    return w[joint][2][3] - w['TransN'][2][3], w[joint][1][3]


SHEET = [0, 6, 9, 12, 14, 15, 18, 30, 44, 46, 66, 86, 96, 100, 104, 108, 112, 120, 140, 167]


def main():
    a = sys.argv[1:]
    png = None
    if '--png' in a:
        i = a.index('--png')
        png = a[i + 1]
        del a[i:i + 2]
    if len(a) != 4:
        sys.exit(__doc__)
    out, bones, info = build(*a)
    print('AttackDash: %d frames, %d nodes; RotN moved %.2f .. %.2f' % (
        out['main'].frames, len(out['main'].nodes), min(info['rotn_offsets']), max(info['rotn_offsets'])))
    if png:
        import supamario_godfist_render
        supamario_godfist_render.sheet(out['main'], bones, png, SHEET)


if __name__ == '__main__':
    main()
