#!/usr/bin/env python3
"""Supamario's Fake Death (GROUNDED down special; Dragon Ball Xenoverse 2's Super skill 116_YMC_DIE, Yamcha's "Fake
Death"): two motions retargeted from the skill's own EAN as the Super God Fist's and Core Breaker's
(`xv2ean.retarget`: world-space turns, fingers too, XV2's -Z facing mirrored onto Smash's +Z, 5.04 units a metre).

  python3 -I tools/supamario_fakedeath_anim.py BODY_MOTION_DIR MODEL_VBN 116_YMC_DIE.ean OUT_DIR
          [--png SHEET.png] [--json FRAMES.json]

BODY_MOTION_DIR: his motion/body/ (main / lhand / rhand / mariopt1 .pac). Writes OUT_DIR/{main,...}.pac with
FitMarioBody*SpecialLwStart.omo (the collapse and the lying loop) and *SpecialLwHold.omo (the wake-up attack) replaced,
every other entry byte for byte the input's. Two motions, not one: the wake-up's game script must start fresh when the
attack comes out, however long the lying was held (the game script keeps its own frame count while the MSC loops the
motion, Core Breaker v4 / v5), and a motion change starts a motion's scripts from their frame 0. Why these two slots
(the ground F.L.U.D.D. start and hold): fighters/supamario/README.md "Fake Death".

The EAN (`116_YMC_DIE.ean`, the default body "_C", as the God Fist's / Core Breaker's; `_F` / `_MAM` the female / heavy
male builds) has two animations; the grounded skill (BAC entry 0, BCM #1 "Standing") plays #0 YMC_SPA_DIE_C (158
frames) straight through:
  0-19   the collapse: a hop back (b_C_Base 1.14 m back, up 0.6 m at 8; MoveWithAxis X / Z: the root moves him) and onto
         his back; "All Attacks Miss" 0-19
  20-32  settling; 32-92 lying still (the BAC's "BAC Loop (instant end)" 32-92: looped while the button is held)
  92-108 the wake-up wind-up (tracking 94-108), 108-120 the spring forward off the ground (Movement 0.2 m a frame
         110-116, the hitbox 112-116), 120-157 the recovery to his stance.
#1 YMC_SPA_DIE_C_S (178) is the floating version's (BAC 4 / 5 / 6): not used.

SEGMENTS: (name, motion, EAN animation, source start, source end, output frames, contact) with contact = the frames he
touches the floor (lying or standing: the lowest joint put on it), else only lifted out of it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402

SCALE = 5.04                # metres -> units (the God Fist's / Core Breaker's body scale)
START, HOLD = 'SpecialLwStart.omo', 'SpecialLwHold.omo'
MOTIONS = (START, HOLD)
LIE_LOOP = 20               # the lying loop's frames (XV2 32-92 is still: max quaternion change 4e-5)
SEGMENTS = [
    ('collapse', START, 0, 0, 32, 32),           # XV2 0-31 at 1:1 (32 = the loop's first frame)
    ('lie', START, 0, 32, 32 + LIE_LOOP, LIE_LOOP),  # XV2 32-51 1:1, the MSC loops it while the button is held
    ('wake', HOLD, 0, 92, 158, 66),              # XV2 92-157 at 1:1 (frame 0 = XV2 92)
]
# a joint's clearance over the floor (its centre): the lowest one touches the floor on contact frames
FLOOR = {'HeadN': 2.6, 'HipN': 1.9, 'BustN': 2.1, 'LHandN': 0.9, 'RHandN': 0.9, 'LFootJ': 1.56, 'RFootJ': 1.56,
         'LToeN': 0.45, 'RToeN': 0.45, 'LKneeJ': 1.3, 'RKneeJ': 1.3, 'LArmJ': 1.0, 'RArmJ': 1.0,
         'LShoulderN': 1.6, 'RShoulderN': 1.6}
CONTACT_BASE_Y = 0.05       # XV2's b_C_Base this low (m): he is on the floor (the hops lift it to 0.6 / 0.33)


def timeline(motion=None):
    """[(name, out_start, out_end_exclusive, seg)] within each motion"""
    out, f = {}, {}
    for s in SEGMENTS:
        a = f.get(s[1], 0)
        out.setdefault(s[1], []).append((s[0], a, a + s[5], s))
        f[s[1]] = a + s[5]
    return out if motion is None else out[motion]


def frames_of(motion):
    return sum(s[5] for s in SEGMENTS if s[1] == motion)


def source(motion, f):
    for name, a, b, s in timeline(motion):
        if a <= f < b:
            n = s[5]
            t = (f - a) / float(n)
            return s, s[2], s[3] + (s[4] - s[3]) * t
    s = [x for x in SEGMENTS if x[1] == motion][-1]
    return s, s[2], float(s[4] - 1)


def _local(ean, anim, name, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi[name], f)


def root_z(ean, motion):
    """his travel along his facing (units) at each output frame: b_C_Base's Z (MoveWithAxis Z), from the motion's
    first frame (the collapse: 0 at XV2 0; the wake: 0 at XV2 92)"""
    out = []
    z0 = None
    for f in range(frames_of(motion)):
        _s, ai, sf = source(motion, f)
        z = _local(ean, ean.animations[ai], 'b_C_Base', sf)[0][2] * SCALE
        z0 = z if z0 is None else z0
        out.append(round(z - z0, 4))
    return out


def body_frames(ean, smash, motion):
    frames, heights = [], []
    a0 = ean.animations[0]
    pel_ref = _local(ean, a0, 'b_C_Pelvis', 0)[0][1] + _local(ean, a0, 'b_C_Base', 0)[0][1]
    for f in range(frames_of(motion)):
        _s, ai, sf = source(motion, f)
        frames.append(X.retarget(ean, ean.animations[ai], smash, at=[sf], root_scale=SCALE)[0])
        base_y = _local(ean, ean.animations[ai], 'b_C_Base', sf)[0][1]
        heights.append((_local(ean, ean.animations[ai], 'b_C_Pelvis', sf)[0][1] + base_y, base_y))
    rot_rest = frames[0]['RotN'][0]
    for f, fr in enumerate(frames):
        pel = heights[f][0]
        fr['TransN'] = ((0.0, 0.0, 0.0), fr['TransN'][1], fr['TransN'][2])     # no TransN: the MSC moves him
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + (pel - pel_ref) * SCALE, rot_rest[2]), fr['RotN'][1], fr['RotN'][2])
    return frames, [h[1] for h in heights]


def world(frames, smash, f):
    par = {b[0]: b[1] for b in smash}
    names = [b[0] for b in smash]
    w = {}
    for n in names:
        p, q, s = frames[f][n]
        local = omo.trs(p, q, s)
        w[n] = omo.mul(w[names[par[n]]], local) if par[n] >= 0 else local
    return w


def floor_fix(frames, smash, base_y):
    """RotN moved: on contact frames the lowest joint (by its FLOOR clearance) on the floor, elsewhere only lifted out
    of it; the change eased over 3 frames where contact starts / ends"""
    raw, contact = [], []
    for f in range(len(frames)):
        w = world(frames, smash, f)
        gap = min(w[n][1][3] - FLOOR[n] for n in FLOOR if n in w)
        c = base_y[f] < CONTACT_BASE_Y
        contact.append(c)
        raw.append(-gap if c else max(0.0, -gap))
    offs = list(raw)
    for f in range(len(frames)):               # ease 3 frames either side of a contact change (never under the floor)
        near = [raw[g] for g in range(max(0, f - 3), min(len(frames), f + 4)) if contact[g] != contact[f]]
        if near:
            w = 0.5
            offs[f] = max(raw[f] if not contact[f] else -1e9, (1 - w) * raw[f] + w * sum(near) / len(near))
            if not contact[f]:
                offs[f] = max(offs[f], raw[f])
    for f, fr in enumerate(frames):
        p, q, sc = fr['RotN']
        fr['RotN'] = ((p[0], p[1] + offs[f], p[2]), q, sc)
    return offs, contact


def build(motion_dir, vbn_path, ean_path, out_dir):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    smash = X.vbn_rest(vbn_path)
    info = {}
    per = {}
    for m in MOTIONS:
        frames, base_y = body_frames(ean, smash, m)
        offs, contact = floor_fix(frames, smash, base_y)
        per[m] = frames
        info[m] = {'rotn_offsets': offs, 'contact': contact, 'root_z': root_z(ean, m)}
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for part, prefix in (('main', 'FitMarioBodyMain'), ('mariopt1', 'FitMarioBodyMariopt1'),
                         ('lhand', 'FitMarioBodyLhand'), ('rhand', 'FitMarioBodyRhand')):
        entries = omo.pac_read(os.path.join(motion_dir, part + '.pac'))
        e = dict(entries)
        repl = {}
        for m in MOTIONS:
            names = [n for n in e if n.startswith(prefix) and n.endswith(m)]
            assert len(names) == 1, (part, m, names)
            o = X.to_omo(per[m], e[names[0]], smash)
            assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[names[0]]).nodes]
            repl[names[0]] = o.encode()
            out[(part, m)] = o
        omo.pac_write(os.path.join(out_dir, part + '.pac'), [(n, repl.get(n, d)) for n, d in entries])
    return out, omo.vbn_read(vbn_path), {'info': info, 'frames': per, 'smash': smash}


def joints(frames, smash, names=('RHandN', 'LHandN', 'HeadN', 'BustN', 'HipN', 'RFootJ', 'LFootJ', 'TransN')):
    """per frame {joint: (z ahead of TransN, y above TransN)}"""
    out = []
    for f in range(len(frames)):
        w = world(frames, smash, f)
        tz, ty = w['TransN'][2][3], w['TransN'][1][3]
        out.append({n: (round(w[n][2][3] - tz, 3), round(w[n][1][3] - ty, 3)) for n in names if n != 'TransN'})
    return out


SKIP = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky', 'Face', 'HLP', 'Have', 'Finger')


def panel(o, bones, fr, label, size=200, scale=6.0, travel=0.0):
    """side view (+Z to the right) and front view; the floor at y 0; travel: his root travel (shown as a shift)"""
    from PIL import Image, ImageDraw
    w = omo.world(o, bones, fr)
    im = Image.new('RGB', (size * 2, size + 16), (245, 245, 245))
    d = ImageDraw.Draw(im)
    for view in (0, 1):
        ox = view * size

        def pt(m):
            x, y, z = m[0][3], m[1][3], m[2][3] + (travel if view == 0 else 0.0)
            return ox + size / 2 + (z if view == 0 else x) * scale, size * 0.8 - y * scale
        fy = size * 0.8
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


def sheet(outs, bones, out, roots, cols=6, every=4):
    from PIL import Image
    ims = []
    for m in MOTIONS:
        o = outs[('main', m)]
        for f in list(range(0, o.frames, every)) + [o.frames - 1]:
            s, _a, sf = source(m, f)
            ims.append(panel(o, bones, f, '%s f%d %s (XV2 %.0f) z%+.1f' % (m[:-4].replace('Special', ''), f, s[0], sf,
                                                                             roots[m][f]), travel=roots[m][f]))
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
        doc = {'source': '116_YMC_DIE.ean (_C) #0 via tools/supamario_fakedeath_anim.py', 'scale': SCALE,
               'segments': [{'name': n, 'motion': s[1], 'start': a0, 'end': b0 - 1, 'src': [s[3], s[4]]}
                            for m in MOTIONS for n, a0, b0, s in timeline(m)],
               'root_z': {m: info['info'][m]['root_z'] for m in MOTIONS},
               'joints': {m: joints(info['frames'][m], info['smash']) for m in MOTIONS}}
        with open(js, 'w') as fh:
            json.dump(doc, fh)
    if png:
        sheet(out, bones, png, {m: info['info'][m]['root_z'] for m in MOTIONS})


if __name__ == '__main__':
    main()
