#!/usr/bin/env python3
"""Supamario's Core Breaker (up special; Dragon Ball Xenoverse 2's Ultimate skill 2070_FIT_COR, Fu's "Core Breaker"):
the SpecialHi / SpecialAirHi animation (body main / lhand / rhand / mariopt1), retargeted from the skill's own EAN as
the Super God Fist's (tools/supamario_godfist_anim.py: `xv2ean.retarget`, world-space turns, fingers too, XV2's
-Z facing mirrored onto Smash's +Z, 5.04 units a metre).

  python3 -I tools/supamario_corebreaker_anim.py BODY_MOTION_DIR MODEL_VBN 2070_FIT_COR.ean OUT_DIR
          [--png SHEET.png] [--json FRAMES.json]

BODY_MOTION_DIR: his motion/body/ (main / lhand / rhand / mariopt1 .pac). Writes OUT_DIR/{main,...}.pac with
FitMarioBody*SpecialHi.omo and *SpecialAirHi.omo replaced (the same motion in both, as vanilla Mario's), every other
entry byte for byte the input's. --json: the timeline (SEGMENTS' output frames), the root table (his travel per
frame, for an MSC-driven travel as God Fist v16's) and the joints the effects / hitboxes follow.

The EAN (`2070_FIT_COR.ean`: the default body "_C", as the God Fist's `030_GOD_CSA.ean`; `_F` / `_MAM` are the female
/ heavy male builds, `_FIT` the original Fu's own skeleton) has two animations, both read through the BAC
(`tools/xv2bac.py 2070_FIT_COR.bac`, its items' frames = the EAN's own frames):
  #0 FIT_ULT_COR_00_C (256): 0-9 crouch, 10-25 the launch straight up (b_C_Base 0 -> 10.0 m; MoveWithAxis XYZ: the
     root moves him), 25-40 easing to the apex (10.9 m), 40-110 the charge (entry 1; effects 0 at 45), 110-168 the
     flare and the wind-up (entry 2; effects 1 at 110, 5 at 125), 168-195 the dive pose (entries 3 / 4: the BAC's
     Movement (0, -1.0, -1.1) a frame dives him, not the root), 176-195 its loop, 196-255 the landing after a miss
     (entry 5), 190-255 the release in the air (entry 13: the grab's timeout).
  #1 FIT_ULT_COR_01_C (427): 195-281 holding the victim at the chest (entry 10: XV2 bones 18 / 18), 281-295 the dive
     with it (root 10.6 m down, 7.3 m forward), 290-426 the crash (entry 12: crouched, a 6.5 m slide back, standing
     by 426); 220-278 the giant-opponent variant (entry 11, unused).

SEGMENTS below is the PROPOSED Smash timeline (phase 1: the user's answers can move every number): each segment
plays an animation's source frames over a number of output frames; `loop` segments are looped by the MSC (the dive);
`root` scales the segment's b_C_Base travel into TransN (Y, Z) or leaves it to the MSC (None).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402

SCALE = 5.04                # metres -> units: the God Fist's (Mario's hip-to-foot 3.93 / XV2's pelvis-to-foot 0.78)
RISE_HEIGHT = 54.8          # his rise in units (XV2: 10.88 m x 5.04; vanilla Super Jump Punch ~44.8): the MSC's speeds
ROOT_IN_MOTION = False      # phase 2 (user: "The animation movement should become speed values that are set"): TransN 0
                            # on every frame; the MSC sets his speeds (supamario.c cb_*). True: phase 1's TransN rise

# (name, EAN animation, source start, source end, output frames, loop, root (y scale, z scale) or None, ground)
# ground: the lower foot put on the floor (frames he stands on the stage). The loops (the dive, the drive with the
# victim) are written out twice so the motion plays straight through them (the MSC only ever jumps forward)
SEGMENTS = [
    ('crouch',      0,   0,  10,  6, False, None, True),          # XV2 0-9 (x1.7)
    ('rise',        0,  10,  40, 24, False, None, False),         # the launch and the apex (x1.25)
    ('charge',      0,  40, 110, 18, False, None, False),         # XV2's 70-frame charge (x3.9; v1 10 frames: the
                                                                  # charge orb was ended before it had faded in)
    ('flare',       0, 110, 168, 12, False, None, False),         # the flare, the turn, the wind-up (x4.8)
    ('dive',        0, 168, 176,  6, False, None, False),         # into the dive pose
    ('dive_loop',   0, 176, 195, 19, True, None, False),          # the dive (XV2 loops 176-195)
    ('dive_loop2',  0, 176, 195, 19, True, None, False),
    ('land_miss',   0, 196, 255, 60, False, None, True),          # entry 5: the landing after a miss (1:1, the lag)
    ('grab_hold',   1, 195, 281, 36, False, None, False),         # entry 10: the victim held at his fist (x2.4)
    ('grab_dive',   0, 174, 193, 19, True, None, False),          # entry 10 from 286: the drive with it (looped)
    ('grab_dive2',  0, 174, 193, 19, True, None, False),
    ('crash',       1, 290, 426, 68, False, None, True),          # entry 12: the crash, the slide back, standing (x2)
    ('air_release', 0, 190, 255, 44, False, None, False),         # entry 13: the release in the air (x1.5)
]
FLOOR = {'HeadN': 3.0, 'LHandN': 1.0, 'RHandN': 1.0, 'LFootJ': 1.3, 'RFootJ': 1.3, 'LToeN': 0.4, 'RToeN': 0.4,
         'LKneeJ': 1.5, 'RKneeJ': 1.5}
STAND_FOOT = 1.56            # Mario's foot joint standing


def timeline():
    """[(name, out_start, out_end_exclusive, seg)]"""
    out, f = [], 0
    for s in SEGMENTS:
        out.append((s[0], f, f + s[4], s))
        f += s[4]
    return out


FRAMES = sum(s[4] for s in SEGMENTS)


def source(f):
    """(segment, animation, fractional source frame) at output frame f"""
    for name, a, b, s in timeline():
        if a <= f < b:
            n = s[4]
            t = (f - a) / float(n - 1 if not s[5] and n > 1 else n)
            return s, s[1], s[2] + (s[3] - s[2]) * min(1.0, t)
    s = SEGMENTS[-1]
    return s, s[1], float(s[3])


def _bone_local(ean, anim, name, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi[name], f)


def _rise_scale(ean):
    a = ean.animations[0]
    top = _bone_local(ean, a, 'b_C_Base', 40)[0][1] - _bone_local(ean, a, 'b_C_Base', 0)[0][1]
    return RISE_HEIGHT / (top * SCALE)


def root_table(ean):
    """his travel (z forward, y up) at every output frame, accumulated over the segments that move him"""
    rs = _rise_scale(ean)
    out, acc, prev = [], [0.0, 0.0], None
    for f in range(FRAMES):
        s, ai, sf = source(f)
        p = _bone_local(ean, ean.animations[ai], 'b_C_Base', sf)[0]
        if prev is not None and prev[0] is s and s[6] is not None:
            ys, zs = s[6]
            k = rs if s[0] in ('crouch', 'rise') else 1.0
            acc[0] += (p[2] - prev[1][2]) * SCALE * zs * k
            acc[1] += (p[1] - prev[1][1]) * SCALE * ys * k
        out.append((round(acc[0], 4), round(acc[1], 4)))
        prev = (s, p)
    return out


def body_frames(ean, smash):
    frames = []
    for f in range(FRAMES):
        _s, ai, sf = source(f)
        frames.append(X.retarget(ean, ean.animations[ai], smash, at=[sf], root_scale=SCALE)[0])
    a0 = ean.animations[0]
    pel_ref = _bone_local(ean, a0, 'b_C_Pelvis', 0)[0][1]
    rot_rest = frames[0]['RotN'][0]
    roots = root_table(ean)
    for f, fr in enumerate(frames):
        _s, ai, sf = source(f)
        pel = _bone_local(ean, ean.animations[ai], 'b_C_Pelvis', sf)[0][1]
        z, y = roots[f] if ROOT_IN_MOTION else (0.0, 0.0)
        fr['TransN'] = ((0.0, y, z), fr['TransN'][1], fr['TransN'][2])
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (pel - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1], fr['RotN'][2])
    return frames


def world(frames, smash, f):
    """{bone: 4x4} of frame f"""
    par = {b[0]: b[1] for b in smash}
    names = [b[0] for b in smash]
    w = {}
    for n in names:
        p, q, s = frames[f][n]
        local = omo.trs(p, q, s)
        w[n] = omo.mul(w[names[par[n]]], local) if par[n] >= 0 else local
    return w


def floor_fix(frames, smash):
    """RotN moved: on the ground segments the lower foot on the floor (STAND_FOOT, TransN's height left out); in the
    air the pose as XV2's, only lifted where a joint would pass under FLOOR on the rise's first frames (he leaves
    the stage there); the change eased over 3 frames at each ground / air boundary"""
    want = []
    for f in range(len(frames)):
        s, _a, _sf = source(f)
        w = world(frames, smash, f)
        ty = w['TransN'][1][3]
        y = {n: w[n][1][3] - ty for n in FLOOR}
        snap = STAND_FOOT - min(y['LFootJ'], y['RFootJ'])
        least = max(FLOOR[n] - y[n] for n in FLOOR)
        if s[7]:
            want.append(max(snap, least))
        else:
            want.append(None)
    # air frames: keep the offset of the nearest ground frame before, eased to 0 over 3 frames, never under `least`
    offs, last = [], 0.0
    since = 99
    for f, v in enumerate(want):
        if v is not None:
            offs.append(v)
            last, since = v, 0
        else:
            since += 1
            offs.append(last * max(0.0, 1.0 - since / 3.0))
    for f, fr in enumerate(frames):
        p, q, sc = fr['RotN']
        fr['RotN'] = ((p[0], p[1] + offs[f], p[2]), q, sc)
    return offs


MOTIONS = ('SpecialHi.omo', 'SpecialAirHi.omo')


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
        repl = {}
        for m in MOTIONS:
            names = [n for n in e if n.startswith(prefix) and n.endswith(m) and not n.endswith('Air' + m)]
            assert len(names) == 1, (part, m, names)
            o = X.to_omo(frames, e[names[0]], smash)
            assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[names[0]]).nodes]
            repl[names[0]] = o.encode()
            out[(part, m)] = o
        omo.pac_write(os.path.join(out_dir, part + '.pac'), [(n, repl.get(n, d)) for n, d in entries])
    return out, omo.vbn_read(vbn_path), {'rotn_offsets': offs, 'root': root_table(ean), 'frames': frames,
                                         'smash': smash}


def joints(frames, smash, names=('RHandN', 'LHandN', 'HeadN', 'BustN', 'HipN', 'TransN')):
    """per frame {joint: (z ahead of TransN, y above TransN)} and TransN itself"""
    out = []
    for f in range(len(frames)):
        w = world(frames, smash, f)
        tz, ty = w['TransN'][2][3], w['TransN'][1][3]
        out.append({n: (round(w[n][2][3] - tz, 3), round(w[n][1][3] - ty, 3)) for n in names if n != 'TransN'})
        out[-1]['TransN'] = (round(tz, 3), round(ty, 3))
    return out


SKIP = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky', 'Face', 'HLP', 'Have', 'Finger')


def panel(o, bones, fr, label, size=200, scale=6.0):
    """side view (+Z to the right) and front view, centred on TransN; the floor drawn where it is (y 0)"""
    from PIL import Image, ImageDraw
    w = omo.world(o, bones, fr)
    tz, ty = w['TransN'][2][3], w['TransN'][1][3]
    im = Image.new('RGB', (size * 2, size + 16), (245, 245, 245))
    d = ImageDraw.Draw(im)
    for view in (0, 1):
        ox = view * size

        def pt(m):
            x, y, z = m[0][3], m[1][3] - ty, m[2][3] - tz
            return ox + size / 2 + (z if view == 0 else x) * scale, size * 0.62 - y * scale
        fy = size * 0.62 + ty * scale
        if fy < size:
            d.line([(ox, fy), (ox + size, fy)], fill=(150, 150, 150), width=2)
        d.line([(ox + size - 1, 0), (ox + size - 1, size)], fill=(200, 200, 200))
        for n, p, _h in bones:
            if p < 0 or p >= len(bones) or any(k in n for k in SKIP) or n in ('ThrowN', 'RotN', 'HipN'):
                continue
            c = {'L': (40, 90, 230), 'R': (220, 50, 40)}[n[0]] if n[0] in 'LR' and n[1].isupper() else (30, 30, 30)
            d.line([pt(w[bones[p][0]]), pt(w[n])], fill=c, width=3)
        hx, hy = pt(w['HeadN'])
        d.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], outline=(0, 0, 0))
    d.text((4, size), label, fill=(0, 0, 0))
    return im


def sheet(o, bones, out, frames, cols=5):
    from PIL import Image
    ims = []
    for f in frames:
        s = source(f)[0]
        ims.append(panel(o, bones, f, 'f%d %s (XV2 #%d %.0f)  h %.1f' % (
            f, s[0], s[1], source(f)[2], omo.world(o, bones, f)['TransN'][1][3])))
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * w, (i // cols) * h))
    sh.save(out)


def sheet_frames():
    out = []
    for name, a, b, s in timeline():
        n = b - a
        picks = [a, a + n // 3, a + 2 * n // 3, b - 1] if n > 8 else [a, b - 1]
        out += picks
    return sorted(set(out))


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
    o = out[('main', MOTIONS[0])]
    print('SpecialHi / SpecialAirHi: %d frames, %d nodes; RotN moved %.2f .. %.2f; rise %.1f' % (
        o.frames, len(o.nodes), min(info['rotn_offsets']), max(info['rotn_offsets']),
        max(r[1] for r in info['root'])))
    for name, s, e, _seg in timeline():
        print('  %-12s %3d-%3d' % (name, s, e - 1))
    if js:
        doc = {'source': '2070_FIT_COR.ean (_C) via tools/supamario_corebreaker_anim.py; PROPOSED timeline',
               'scale': SCALE, 'rise_height': RISE_HEIGHT, 'root_in_motion': ROOT_IN_MOTION,
               'segments': [{'name': n, 'start': s, 'end': e - 1, 'anim': g[1], 'src': [g[2], g[3]], 'loop': g[5],
                             'ground': g[7]} for n, s, e, g in timeline()],
               'root_z_y': info['root'], 'joints': joints(info['frames'], info['smash'])}
        with open(js, 'w') as fh:
            json.dump(doc, fh)
    if png:
        sheet(o, bones, png, sheet_frames())


if __name__ == '__main__':
    main()
