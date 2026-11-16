#!/usr/bin/env python3
"""Supamario's Sledgehammer (AIR down special; Dragon Ball Xenoverse 2's Super skill 164_VGT_HMR, Vegeta's): two
motions retargeted from the skill's own EAN as the Super God Fist's, Core Breaker's and Fake Death's
(`xv2ean.retarget`: world-space turns, fingers too, XV2's -Z facing mirrored onto Smash's +Z, 5.04 units a metre).

  python3 -I tools/supamario_sledgehammer_anim.py BODY_MOTION_DIR MODEL_VBN 164_VGT_HMR.ean OUT_DIR
          [--png SHEET.png] [--json FRAMES.json]

BODY_MOTION_DIR: his motion/body/ (main / lhand / rhand / mariopt1 .pac). Writes OUT_DIR/{main,...}.pac with
FitMarioBody*SpecialAirLwStart.omo (the wind-up to the charge pose) and *SpecialAirLwHold.omo (the swing and the
recovery) replaced, every other entry byte for byte the input's. These were the air F.L.U.D.D.'s start / hold (Fake
Death took the ground ones): the air down special is Sledgehammer now. Two motions, not one: the charge holds the
start's last frame for as long as the button is held, and the swing's game script must start fresh when it comes out
(the game script keeps its own frame count while the MSC holds a motion's frame: Core Breaker v4 / v5).

The EAN (`164_VGT_HMR.ean`, the default body "_C", as the earlier ports'; `_F` / `_BDK` / `_CL3` / `_SLG` the other
builds) has one animation, #0 VGT_SPA_HMR_C (45 frames), which BAC entries 0 / 1 / 2 / 3 all play (speed 1.0, so the
animation frame is the BAC frame). The BAC's TimeScale items slow the whole entry: entry 0 (uncharged) 0-12 x0.5,
22-26 x0.3, 26-37 x0.5; so its 44 BAC frames take 76.3 real frames. The motions are baked at entry 0's real timing
(Smash frame = XV2 real frame): the MSC changes the swing's rate for the charged entry (2: 22-26 x0.23) and the
on-hit entry (3: 12-32 x1.0, 32-44 x0.5), tools/supamario_sledgehammer_build.py.
  0-12   (BAC 0-6, x0.5)  the hop and the wind-up, both fists raised overhead (the charge pose: BAC 6, ChargeControl
         6-8): SpecialAirLwStart, 13 frames, its last the held pose
  12-..  (BAC 6-44)       the swing: the double-fisted hammer down (the fists at his feet from BAC 16, the hitbox
         16-20), the hold bent over, the recovery: SpecialAirLwHold, 65 frames (frame 0 = BAC 6)
No TransN (XV2's root steps 0.48 m forward and back: dropped, he drifts with the stick); his pelvis's height change
(the hop up, the crouch at the end) moves RotN as Fake Death's does. No floor contact: an air move.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402
import xv2ean as X  # noqa: E402

SCALE = 5.04                # metres -> units (the earlier ports' body scale)
START, HOLD = 'SpecialAirLwStart.omo', 'SpecialAirLwHold.omo'
MOTIONS = (START, HOLD)
# BAC entry 0's TimeScale items (from, to, scale); 1.0 between them
TS_ENTRY0 = [(0, 12, 0.5), (12, 22, 1.0), (22, 26, 0.3), (26, 37, 0.5), (37, 44, 1.0)]
BAC_END = 44                # the entry's last frame (its animations / callbacks end at 44)
CHARGE_BAC = 6              # ChargeControl 6-8 (ChargeTime 30): the pose held while charging
EAN_FRAMES = 45


def real(b, ts=TS_ENTRY0):
    """the real (60 fps) frame at BAC frame b, from BAC 0"""
    t = 0.0
    for a, z, s in ts:
        if b <= a:
            break
        t += (min(b, z) - a) / s
    return t


def bac_at(t, ts=TS_ENTRY0):
    """the BAC frame at real frame t (real's inverse)"""
    acc = 0.0
    for a, z, s in ts:
        d = (z - a) / s
        if t <= acc + d:
            return a + (t - acc) * s
        acc += d
    return float(ts[-1][1]) + (t - acc)


START_FRAMES = int(round(real(CHARGE_BAC))) + 1          # 13: 0-12, the last = BAC 6
HOLD_FROM = real(CHARGE_BAC)                              # 12.0: the swing's frame 0 is this real frame
HOLD_FRAMES = int(real(BAC_END) - HOLD_FROM) + 1          # 65: 0-64 (BAC 6 - 43.7)


def hold_frame(b):
    """the swing motion's frame at BAC frame b (entry 0's timing)"""
    return real(b) - HOLD_FROM


def source(motion, f):
    """the EAN frame a motion frame shows"""
    if motion == START:
        return min(float(CHARGE_BAC), bac_at(float(f)))
    return min(float(EAN_FRAMES - 1), bac_at(HOLD_FROM + f))


def frames_of(motion):
    return START_FRAMES if motion == START else HOLD_FRAMES


def _local(ean, anim, name, f):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    return ean.local(anim, bi[name], f)


def body_frames(ean, smash, motion):
    """the retargeted frames; TransN still; RotN up / down by XV2's pelvis height over its first frame's"""
    a0 = ean.animations[0]
    pel_ref = _local(ean, a0, 'b_C_Pelvis', 0)[0][1] + _local(ean, a0, 'b_C_Base', 0)[0][1]
    frames, lift = [], []
    for f in range(frames_of(motion)):
        sf = source(motion, f)
        frames.append(X.retarget(ean, a0, smash, at=[sf], root_scale=SCALE)[0])
        lift.append((_local(ean, a0, 'b_C_Pelvis', sf)[0][1] + _local(ean, a0, 'b_C_Base', sf)[0][1] - pel_ref) *
                    SCALE)
    rot_rest = frames[0]['RotN'][0]
    par = _par(smash)
    for f, fr in enumerate(frames):
        fr['TransN'] = ((0.0, 0.0, 0.0), fr['TransN'][1], fr['TransN'][2])     # no TransN: he drifts
        fr['RotN'] = ((rot_rest[0], rot_rest[1] + lift[f], rot_rest[2]), fr['RotN'][1], fr['RotN'][2])
        if OVERHEAD:
            overhead(fr, smash, par, overhead_weight(motion, f))               # v4: the fists out of his head
    if OVERHEAD and HEAD is not None:
        rest = world([{b[0]: (b[3], b[4], b[5]) for b in smash}], smash, 0)
        import numpy as np
        rest_inv = {bn: np.linalg.inv(np.array(rest[bn])) for bn in {bn for bn, _v in HEAD}}
        for f in PUSH_FRAMES[motion]:
            push_clear(frames[f], smash, par, HEAD, rest_inv)
    return frames, lift


# ---------------------------------------------------------------- v4: the fists out of his head
# User (Sledgehammer v3 clip): "The charge glow is almost invisible for Sledgehammer because Supamario's hands are
# positioned in his head rather than above his head". Retargeted as it is, XV2's overhead pose puts both hands 0.0-0.6
# from his head's surface, inside it in the side view (Start f12: the hands at 12.4-12.7 up, the head 9.6-16.3 up and
# -6.1..0.6 along). Mario's arm is 3.47 long (ShoulderJ -> ArmJ 1.75, ArmJ -> HandN 1.72) and his shoulders are 10.1
# up in the pose, 6.2 under his cap's top: no bend of his own arms gets a fist above his head (a search over head
# tilts, shoulder raises and IK targets with his arm lengths: no fist centre higher than his eyes clears the head by
# 1.4). So over the overhead frames the arms are stretched (ArmJ / HandN's local positions x ARM_STRETCH: the sleeve
# and forearm lengthen, the fist model doesn't scale), the head tilted back HEAD_TILT more (looking up at the fists, as
# Vegeta), the shoulders raised SHOULDER_RAISE, and both fists put by two-bone IK at HeadN + FIST_AT (forward, up),
# clasped (x +-0.6); the hand bones keep their own turn from the forearm. Blended in over the wind-up (OVERHEAD_IN, by
# Start frame), out at the swing (OVERHEAD_OUT, by Hold frame); the hit frames (Hold 15-19) and everything after are
# XV2's as before. The search (fist centre = HandN + 1.0 along the forearm, its side-view distance to the head mesh's
# points): ARM_STRETCH 1.6, HEAD_TILT 40, SHOULDER_RAISE 20, FIST_AT (2, 4): clear by 2.2 at the charge pose, the fists'
# centres 0.3 above the cap's top (v3: 0.0, inside)
OVERHEAD = True                     # False: v1-v3's pose (the test's before)
HEAD = None                         # head_points(): set by build() (the push needs the head's mesh)
ARM_STRETCH = 1.6
HEAD_TILT = 20.0                    # degrees about world X, back (his face up)
SHOULDER_RAISE = 40.0
FIST_AT = (1.5, 4.5)                # (forward, up) from HeadN
OVERHEAD_IN = {START: [(2, 0.0), (6, 1.0)]}
OVERHEAD_OUT = {HOLD: [(11, 1.0), (13, 0.0)]}


def overhead_weight(motion, f):
    keys = OVERHEAD_IN.get(motion) or OVERHEAD_OUT.get(motion)
    if f <= keys[0][0]:
        return keys[0][1]
    if f >= keys[-1][0]:
        return keys[-1][1]
    (a, wa), (b, wb) = keys
    return wa + (wb - wa) * (f - a) / float(b - a)


def _par(smash):
    names = [b[0] for b in smash]
    return {b[0]: (names[b[1]] if b[1] >= 0 else None) for b in smash}


def _wq(fr, par, n):
    chain = []
    while n is not None:
        chain.append(n)
        n = par[n]
    q = (0.0, 0.0, 0.0, 1.0)
    for c in reversed(chain):
        q = X.qmul(q, fr[c][1])
    return q


def _rot_world(fr, par, n, qr):
    """turn bone n (and what hangs from it) by the world turn qr about its own joint"""
    qp = _wq(fr, par, par[n]) if par[n] else (0.0, 0.0, 0.0, 1.0)
    p, _q, s = fr[n]
    fr[n] = (p, X.qnorm(X.qmul(X.qinv(qp), X.qmul(qr, _wq(fr, par, n)))), s)


def _q_from_to(a, b):
    import numpy as np
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    c = np.cross(a, b)
    return X.qnorm((float(c[0]), float(c[1]), float(c[2]), 1.0 + float(np.dot(a, b))))


def _q_axis(axis, deg):
    import math
    h = math.radians(deg) / 2
    return (axis[0] * math.sin(h), axis[1] * math.sin(h), axis[2] * math.sin(h), math.cos(h))


def _pos(w, n):
    import numpy as np
    return np.array([w[n][i][3] for i in range(3)])


def _ik(fr, smash, par, s, target):
    """two-bone IK: s ShoulderJ / ArmJ turned so s HandN reaches target (as near as it can), the elbow kept in its
    plane"""
    import numpy as np
    w = world([fr], smash, 0)
    sj, e, h = _pos(w, s + 'ShoulderJ'), _pos(w, s + 'ArmJ'), _pos(w, s + 'HandN')
    a, b = np.linalg.norm(e - sj), np.linalg.norm(h - e)
    dv = target - sj
    dl = np.linalg.norm(dv)
    d2 = min(max(dl, abs(a - b) + 1e-3), a + b - 1e-3)
    u = dv / dl
    n = np.cross(e - sj, h - sj)
    n = n / np.linalg.norm(n) if np.linalg.norm(n) > 1e-6 else np.array([1.0, 0.0, 0.0])
    v = np.cross(n, u)
    if np.dot(v, e - sj) < 0:
        v = -v
    ca = (a * a + d2 * d2 - b * b) / (2 * a * d2)
    e2 = sj + a * (ca * u + max(0.0, 1 - ca * ca) ** 0.5 * v)
    _rot_world(fr, par, s + 'ShoulderJ', _q_from_to(e - sj, e2 - sj))
    w = world([fr], smash, 0)
    e3, h3 = _pos(w, s + 'ArmJ'), _pos(w, s + 'HandN')
    _rot_world(fr, par, s + 'ArmJ', _q_from_to(h3 - e3, sj + u * d2 - e3))
    return dl - d2


def overhead(fr, smash, par, wgt):
    """one frame's correction at weight wgt (0: XV2's as retargeted, 1: the full overhead pose); returns the IK's
    shortfall"""
    import numpy as np
    if wgt <= 0.0:
        return 0.0
    k = 1.0 + (ARM_STRETCH - 1.0) * wgt
    for s in 'LR':
        for n in (s + 'ArmJ', s + 'HandN'):
            p, q, sc = fr[n]
            fr[n] = (tuple(c * k for c in p), q, sc)
    _rot_world(fr, par, 'HeadN', _q_axis((1.0, 0.0, 0.0), -HEAD_TILT * wgt))
    for s, sg in (('L', 1.0), ('R', -1.0)):
        _rot_world(fr, par, s + 'ShoulderN', _q_axis((0.0, 0.0, 1.0), sg * SHOULDER_RAISE * wgt))
    w = world([fr], smash, 0)
    hd = _pos(w, 'HeadN')
    miss = 0.0
    for s, sg in (('L', 1.0), ('R', -1.0)):
        cur = _pos(w, s + 'HandN')
        t = hd + np.array([sg * 0.6, FIST_AT[1], FIST_AT[0]])
        miss += _ik(fr, smash, par, s, cur + (t - cur) * wgt)
    return miss


CLEAR_MIN = 1.2                     # the push: a fist's centre at least this far from the head (side view)
PUSH_FRAMES = {START: range(5, START_FRAMES), HOLD: range(0, 17)}


def push_clear(fr, smash, par, head, rest_inv):
    """v4: the wind-up's and the swing's first frames (PUSH_FRAMES): a fist whose centre is nearer the head than
    CLEAR_MIN in the side view is moved straight away from the nearest head point by IK (6 tries), both fists the same
    way (clasped); returns the clearance left"""
    import numpy as np
    left = 0.0
    for _ in range(6):
        w = world([fr], smash, 0)
        pts = np.array([(np.array(w[bn]) @ rest_inv[bn] @ np.array([v[0], v[1], v[2], 1.0]))[:3] for bn, v in head])
        worst, push = None, None
        for s in 'LR':
            h, e = _pos(w, s + 'HandN'), _pos(w, s + 'ArmJ')
            c = h + (h - e) / np.linalg.norm(h - e)
            dd = np.linalg.norm(pts[:, 1:] - c[1:], axis=1)
            i = int(np.argmin(dd))
            if worst is None or dd[i] < worst:
                worst = dd[i]
                d = np.array([0.0, c[1] - pts[i][1], c[2] - pts[i][2]])
                push = d / (np.linalg.norm(d) or 1.0) * (CLEAR_MIN - dd[i] + 0.15)
        left = worst
        if worst >= CLEAR_MIN:
            break
        for s in 'LR':
            _ik(fr, smash, par, s, _pos(w, s + 'HandN') + push)
    return left


def head_points(vbn_path, every=7):
    """his head's mesh points (model.nud's meshes bound to HeadN or a bone under it), rest pose, every 7th:
    [(bone, (x, y, z))]"""
    import nud
    smash = X.vbn_rest(vbn_path)
    names = [b[0] for b in smash]
    par = _par(smash)
    under = set()
    for n in names:
        m = n
        while m is not None and m != 'HeadN':
            m = par[m]
        if m == 'HeadN':
            under.add(n)
    out = []
    for m in nud.read(os.path.join(os.path.dirname(vbn_path), 'model.nud')):
        if m.bone < 0 or names[m.bone] not in under:
            continue
        for p in m.polygons:
            if p.pos is not None:
                out += [(names[m.bone], tuple(float(c) for c in v)) for v in p.pos[::every]]
    return out


def fist_clearance(frames, smash, f, head):
    """the side view's distance from each fist's centre (HandN + 1.0 along the forearm) to the head's points, and the
    fists' height over the head's top, at frame f"""
    import numpy as np
    rest = world([{b[0]: (b[3], b[4], b[5]) for b in smash}], smash, 0)
    w = world(frames, smash, f)
    inv = {}
    pts = []
    for bn, v in head:
        if bn not in inv:
            inv[bn] = np.array(w[bn]) @ np.linalg.inv(np.array(rest[bn]))
        pts.append((inv[bn] @ np.array([v[0], v[1], v[2], 1.0]))[:3])
    pts = np.array(pts)
    out = {}
    for s in 'LR':
        h, e = _pos(w, s + 'HandN'), _pos(w, s + 'ArmJ')
        c = h + (h - e) / np.linalg.norm(h - e)
        out[s] = (round(float(np.min(np.linalg.norm(pts[:, 1:] - c[1:], axis=1))), 3),
                  round(float(c[1] - pts[:, 1].max()), 3))
    return out


def world(frames, smash, f):
    par = {b[0]: b[1] for b in smash}
    names = [b[0] for b in smash]
    w = {}
    for n in names:
        p, q, s = frames[f][n]
        local = omo.trs(p, q, s)
        w[n] = omo.mul(w[names[par[n]]], local) if par[n] >= 0 else local
    return w


def build(motion_dir, vbn_path, ean_path, out_dir):
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    assert len(ean.animations) == 1 and ean.animations[0].frames == EAN_FRAMES, [
        (a.name, a.frames) for a in ean.animations]
    smash = X.vbn_rest(vbn_path)
    global HEAD
    HEAD = head_points(vbn_path)
    info, per = {}, {}
    for m in MOTIONS:
        frames, lift = body_frames(ean, smash, m)
        per[m] = frames
        info[m] = {'rotn_lift': [round(v, 4) for v in lift], 'source': [round(source(m, f), 3)
                                                                         for f in range(frames_of(m))]}
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


def panel(o, bones, fr, label, size=200, scale=6.0, hitbox=None):
    """side view (+Z to the right) and front view; TransN at the cross; hitbox (z, y, r) drawn in the side view"""
    from PIL import Image, ImageDraw
    w = omo.world(o, bones, fr)
    im = Image.new('RGB', (size * 2, size + 16), (245, 245, 245))
    d = ImageDraw.Draw(im)
    for view in (0, 1):
        ox = view * size

        def pt(m):
            x, y, z = m[0][3], m[1][3], m[2][3]
            return ox + size / 2 + (z if view == 0 else x) * scale, size * 0.62 - y * scale
        cx, cy = ox + size / 2, size * 0.62
        d.line([(cx - 4, cy), (cx + 4, cy)], fill=(120, 120, 120))
        d.line([(cx, cy - 4), (cx, cy + 4)], fill=(120, 120, 120))
        d.line([(ox + size - 1, 0), (ox + size - 1, size)], fill=(200, 200, 200))
        for n, p, _h in bones:
            if p < 0 or p >= len(bones) or any(k in n for k in SKIP) or n in ('ThrowN', 'RotN', 'HipN'):
                continue
            c = {'L': (40, 90, 230), 'R': (220, 50, 40)}[n[0]] if n[0] in 'LR' and n[1].isupper() else (30, 30, 30)
            d.line([pt(w[bones[p][0]]), pt(w[n])], fill=c, width=3)
        hx, hy = pt(w['HeadN'])
        d.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], outline=(0, 0, 0))
        if hitbox and view == 0:
            z, y, r = hitbox
            px, py = ox + size / 2 + z * scale, size * 0.62 - y * scale
            d.ellipse([px - r * scale, py - r * scale, px + r * scale, py + r * scale], outline=(230, 120, 0), width=2)
    d.text((4, size), label, fill=(0, 0, 0))
    return im


def pose_sheet(ean_path, vbn_path, out, frames_by=((START, (4, 6, 8, 10, 12)), (HOLD, (4, 10, 11, 12, 13, 14, 16)))):
    """v4: before (v1-v3: XV2's pose as retargeted) / after (the fists out of his head) side views of the given frames:
    his head's mesh points (grey), the arm bones (left blue, right red), each fist's centre (HandN + 1.0 along the
    forearm) with a 1.2 circle (yellow: the charge glow's place on LHandN), the clearance printed"""
    import numpy as np
    from PIL import Image, ImageDraw
    global OVERHEAD, HEAD
    ean = X.Ean(open(ean_path, 'rb').read(), smash_axes=True)
    smash = X.vbn_rest(vbn_path)
    HEAD = head_points(vbn_path)
    rest = world([{b[0]: (b[3], b[4], b[5]) for b in smash}], smash, 0)
    rinv = {bn: np.linalg.inv(np.array(rest[bn])) for bn in {bn for bn, _v in HEAD}}
    par = _par(smash)
    size, sc = 230, 9.0
    tiles = []
    keep = OVERHEAD
    try:
        for on in (False, True):
            OVERHEAD = on
            row = []
            for m, fs in frames_by:
                frames, _ = body_frames(ean, smash, m)
                for f in fs:
                    w = world(frames, smash, f)
                    t = _pos(w, 'TransN')
                    im = Image.new('RGB', (size, size + 30), (250, 250, 250))
                    d = ImageDraw.Draw(im)

                    def pt(v):
                        return size / 2 + (v[2] - t[2]) * sc, size * 0.85 - (v[1] - t[1]) * sc
                    for bn, v in HEAD:
                        q = (np.array(w[bn]) @ rinv[bn] @ np.array([v[0], v[1], v[2], 1.0]))[:3]
                        x, y = pt(q)
                        d.point((x, y), fill=(165, 165, 165))
                    for n in names_of(smash):
                        pn = par[n]
                        if pn is None or any(k in n for k in SKIP) or n in ('ThrowN', 'RotN', 'HipN', 'TransN'):
                            continue
                        c = {'L': (40, 90, 230), 'R': (220, 50, 40)}[n[0]] if n[0] in 'LR' and n[1].isupper() else (30, 30, 30)
                        d.line([pt(_pos(w, pn)), pt(_pos(w, n))], fill=c, width=3)
                    cl = fist_clearance(frames, smash, f, HEAD)
                    for s_ in 'LR':
                        h, e = _pos(w, s_ + 'HandN'), _pos(w, s_ + 'ArmJ')
                        x, y = pt(h + (h - e) / np.linalg.norm(h - e))
                        r = 1.2 * sc
                        d.ellipse([x - r, y - r, x + r, y + r], outline=(230, 170, 0) if s_ == 'L' else (200, 90, 0),
                                  width=2)
                    d.text((4, size), '%s %s f%d' % ('after' if on else 'before', m[7:-4].replace('Special', ''), f),
                           fill=(0, 0, 0))
                    d.text((4, size + 14), 'clear L %.1f R %.1f, over top %.1f' % (cl['L'][0], cl['R'][0],
                                                                                   max(cl['L'][1], cl['R'][1])),
                           fill=(0, 0, 0))
                    row.append(im)
            tiles.append(row)
    finally:
        OVERHEAD = keep
    sh = Image.new('RGB', (size * len(tiles[0]), (size + 30) * 2), (255, 255, 255))
    for r, row in enumerate(tiles):
        for c, im in enumerate(row):
            sh.paste(im, (c * size, r * (size + 30)))
    sh.save(out)


def names_of(smash):
    return [b[0] for b in smash]


def sheet(outs, bones, out, cols=6, every=3, hitbox=None, hit_frames=()):
    from PIL import Image
    ims = []
    for m in MOTIONS:
        o = outs[('main', m)]
        for f in sorted(set(list(range(0, o.frames, every)) + [o.frames - 1] + (list(hit_frames) if m == HOLD
                                                                               else []))):
            hb = hitbox if (m == HOLD and f in hit_frames) else None
            ims.append(panel(o, bones, f, '%s f%d (BAC %.1f)%s' % (m[:-4].replace('Special', ''), f, source(m, f),
                                                                   ' HIT' if hb else ''), hitbox=hb))
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
        lift = info['info'][m]['rotn_lift']
        print('%s: %d frames; RotN lift %.2f .. %.2f' % (m, o.frames, min(lift), max(lift)))
    if js:
        doc = {'source': '164_VGT_HMR.ean (_C) #0 via tools/supamario_sledgehammer_anim.py', 'scale': SCALE,
               'timescale_entry0': TS_ENTRY0, 'info': info['info'],
               'joints': {m: joints(info['frames'][m], info['smash']) for m in MOTIONS}}
        with open(js, 'w') as fh:
            json.dump(doc, fh)
    if png:
        sheet(out, bones, png)


if __name__ == '__main__':
    main()
