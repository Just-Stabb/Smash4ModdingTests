#!/usr/bin/env python3
"""Supamario's Time Skip (SIDE special; Dragon Ball Xenoverse 2's Super skill 1352_HIK_DSH, Hit's "Time-Skip"): two
motions retargeted from the skill's own EAN as the earlier ports' (`xv2ean.retarget`: world-space turns, fingers too,
XV2's -Z facing mirrored onto Smash's +Z, 5.04 units a metre).

  python3 -I tools/supamario_timeskip_anim.py BODY_MOTION_DIR MODEL_VBN 1352_HIK_DSH.ean OUT_DIR
          [--png SHEET.png] [--json FRAMES.json]

BODY_MOTION_DIR: his motion/body/ (main / lhand / rhand / mariopt1 .pac). Writes OUT_DIR/{main,...}.pac with
FitMarioBody*SpecialS.omo (the dash: the wind-up, the time-skip dash, the stop on a whiff) and *SpecialAirS.omo (the
connect: the punch held in the stopped time, the strike, the recovery) replaced, every other entry byte for byte the
input's. They were the Cape's ground / air motions: the side special is Time Skip on the ground and in the air alike
(XV2's skill has no airborne entry), so the two slots are the two parts of the move, played in either situation. The
connect is its own motion so its scripts start at its frame 0 whenever the dash connects.

The EAN (the default body "_C", as the earlier ports'; `_F` / `_HIK` / `_MAM` the other builds) has two animations:
  #0 HIK_SPA_DSH_00_C (121 frames), BAC entry 0 (uncharged) / 2 (charged): 0-20 the wind-up (a crouch, a small step
     back), 20-50 the hold pose (played at x6: the TimeScale, 5 real frames; the charge pauses at 20), 50-60 the launch
     into the horizontal dash pose (the root 1.5 m forward), 60-84 the dash pose (still; the charged entry plays 60-85
     three times), 84-100 the stop (the root 1.7 m more), 100-120 back to his stance.
  #1 HIK_SPA_DSH_01_C (81 frames), BAC entry 4 (the user on connect): from the dash pose the right fist punched
     straight ahead (extended 12-36: the strike at 16 in the stopped time), the recovery to the stance by 80.
SpecialS = #0 at entry 0's real timing (96 frames: 0-19 = 0-19, 20-24 = 20-50 at x6, 25-95 = 50-120);
SpecialAirS = #1 1:1 (81 frames). No TransN (the MSC moves him: the root's Z travel is its speed table, `root_z`); the
pelvis's height change moves RotN, lifted out of the floor where a joint would go under it (Fake Death's floor_fix:
XV2's b_C_Base never comes under 0.05 m here, so no frame is pressed onto the floor: the dash pose skims it as XV2's).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402
import supamario_fakedeath_anim as FA  # noqa: E402

SCALE = 5.04
DASH, CONNECT = 'SpecialS.omo', 'SpecialAirS.omo'
MOTIONS = (DASH, CONNECT)
# (name, motion, EAN animation, source start, source end (exclusive), output frames)
SEGMENTS = [
    ('windup', DASH, 0, 0, 20, 20),          # BAC 0-19 at 1:1
    ('flash', DASH, 0, 20, 50, 5),           # BAC 20-49 at x6 (the TimeScale 20-50)
    ('dash', DASH, 0, 50, 121, 71),          # BAC 50-120 at 1:1 (frame 25 = BAC 50, 95 = BAC 120)
    ('connect', CONNECT, 1, 0, 81, 81),      # #1 0-80 at 1:1
]


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


def bac_of_dash(f):
    """the BAC frame (entry 0) of SpecialS frame f"""
    return source(DASH, f)[2]


def _local(ean, anim, name, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi[name], f)


def root_z(ean, motion):
    """his travel along his facing (units) at each motion frame: b_C_Base's Z (MoveWithAxis Z), from frame 0"""
    out, z0 = [], None
    for f in range(frames_of(motion)):
        _s, ai, sf = source(motion, f)
        z = _local(ean, ean.animations[ai], 'b_C_Base', sf)[0][2] * SCALE
        z0 = z if z0 is None else z0
        out.append(round(z - z0, 4))
    return out


def root_speed(ean, motion=DASH):
    """the root's speed at each motion frame: the travel to the next frame (units a frame, + forward)"""
    z = root_z(ean, motion)
    return [round(z[f + 1] - z[f], 4) for f in range(len(z) - 1)] + [0.0]


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
        fr['TransN'] = ((0.0, 0.0, 0.0), fr['TransN'][1], fr['TransN'][2])     # the MSC moves him
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (base[f][0] - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1],
                      fr['RotN'][2])
    return frames, [b[1] for b in base]


def build(motion_dir, vbn_path, ean_path, out_dir):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    assert [(a.frames) for a in ean.animations] == [121, 81], [(a.name, a.frames) for a in ean.animations]
    smash = X.vbn_rest(vbn_path)
    info, per = {}, {}
    for m in MOTIONS:
        frames, base_y = body_frames(ean, smash, m)
        offs, contact = FA.floor_fix(frames, smash, base_y)
        per[m] = frames
        info[m] = {'rotn_offsets': offs, 'contact': contact, 'root_z': root_z(ean, m),
                   'source': [round(source(m, f)[2], 3) for f in range(frames_of(m))]}
    info[DASH]['root_speed'] = root_speed(ean, DASH)
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for part, prefix in (('main', 'FitMarioBodyMain'), ('mariopt1', 'FitMarioBodyMariopt1'),
                         ('lhand', 'FitMarioBodyLhand'), ('rhand', 'FitMarioBodyRhand')):
        entries = omo.pac_read(os.path.join(motion_dir, part + '.pac'))
        e = dict(entries)
        repl = {}
        for m in MOTIONS:
            names = [n for n in e if n.startswith(prefix) and n.endswith('D01' + m)]
            assert len(names) == 1, (part, m, names)
            o = X.to_omo(per[m], e[names[0]], smash)
            assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[names[0]]).nodes]
            repl[names[0]] = o.encode()
            out[(part, m)] = o
        omo.pac_write(os.path.join(out_dir, part + '.pac'), [(n, repl.get(n, d)) for n, d in entries])
    return out, omo.vbn_read(vbn_path), {'info': info, 'frames': per, 'smash': smash}


def joints(frames, smash):
    return FA.joints(frames, smash)


def sheet(outs, bones, out, roots, cols=6, every=4, hitboxes=None):
    """side / front views every `every` frames (hitboxes: {motion: {frame: (z, y, r)}} drawn in the side view)"""
    from PIL import Image, ImageDraw
    ims = []
    for m in MOTIONS:
        o = outs[('main', m)]
        for f in sorted(set(list(range(0, o.frames, every)) + [o.frames - 1] + list((hitboxes or {}).get(m, {})))):
            s, _a, sf = source(m, f)
            im = FA.panel(o, bones, f, '%s f%d %s (XV2 %.0f) z%+.1f' % (m[:-4].replace('Special', ''), f, s[0], sf,
                                                                       roots[m][f]), travel=roots[m][f])
            hb = (hitboxes or {}).get(m, {}).get(f)
            if hb:
                d = ImageDraw.Draw(im)
                z, y, r = hb
                cx, cy = 100 + (z + roots[m][f]) * 6.0, 160 - y * 6.0
                d.ellipse([cx - r * 6, cy - r * 6, cx + r * 6, cy + r * 6], outline=(230, 120, 0), width=2)
            ims.append(im)
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * w, (i // cols) * h))
    sh.save(out)


def main():
    a = sys.argv[1:]
    png = js = None
    if '--png' in a:
        i = a.index('--png')
        png = a[i + 1]
        del a[i:i + 2]
    if '--json' in a:
        i = a.index('--json')
        js = a[i + 1]
        del a[i:i + 2]
    if len(a) != 4:
        sys.exit(__doc__)
    out, bones, info = build(*a)
    for m in MOTIONS:
        o = out[('main', m)]
        print('%s: %d frames; RotN moved %.2f .. %.2f; root z %.2f .. %.2f' % (
            m, o.frames, min(info['info'][m]['rotn_offsets']), max(info['info'][m]['rotn_offsets']),
            min(info['info'][m]['root_z']), max(info['info'][m]['root_z'])))
    if js:
        with open(js, 'w') as fh:
            json.dump({'source': '1352_HIK_DSH.ean (_C) via tools/supamario_timeskip_anim.py', 'scale': SCALE,
                       'info': info['info'], 'joints': {m: joints(info['frames'][m], info['smash']) for m in MOTIONS}},
                      fh)
    if png:
        sheet(out, bones, png, {m: info['info'][m]['root_z'] for m in MOTIONS})


if __name__ == '__main__':
    main()
