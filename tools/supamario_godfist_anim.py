#!/usr/bin/env python3
"""Supamario's Super God Fist (dash attack): a new AttackDash animation (body main / lhand / rhand / mariopt1).

  python3 tools/supamario_godfist_anim.py BODY_MOTION_DIR MODEL_VBN OUT_DIR [--png SHEET.png]

BODY_MOTION_DIR: his motion/body/ (main.pac, lhand.pac, rhand.pac, mariopt1.pac: Mario's animations, under
Mario's names; the RPX's motion table finds them by name). Writes OUT_DIR/{main,lhand,rhand,mariopt1}.pac with
FitMarioBody*C00AttackDash.omo replaced (every other entry byte for byte the input's).

Xenoverse 2's own animations for the skill (030_GOD_CSA's EAN, CMN.ean #96 / #179) were not in the files given, so
this is posed from Mario's own animations, following the user's clip and the BAC timeline (fighters/supamario/
README.md "Super God Fist"): every pose is a frame of one of his animations, played or cross-faded:

  frames 0-38   the dash punch (both paths): a run lean (Run 5 / 10), the wind-up and the straight left (his forward
                smash's thrust, AttackS4S 12 -> 16), out at frame 7 (the hitbox 7-10), held to 22, back to Wait1 by
                38; the whiff ends there (MSC: GF_WHIFF_END, vanilla Mario's dash attack acts from 39)
  frames 40-99  the God Fist (the MSC jumps here from the hit at frame 11, GF_JUMP_TO = 40; below +40): the punch
                held (+0 - +2), pulled back (the charge, +7), thrust again (+10: the God Fist hit), the follow-through
                held while the victim is launched, then a back flip in place (JumpB 2-36, +30 - +46: XV2's attacker
                spins away after the launch) landing into Wait1 (+59); he acts from +55 (GF_IASA: the victim's
                flight is over; v1: +49).
  TransN: the dash, 0 -> 16 by frame 7, 20 by 10, then still (the victim's flight is placed relative to him).
  RotN: up to +14 over the flip (+28 - +50) (a hop: the flip is in the animation only, he stays grounded).
  Hands: fists (Attack11's hands at frame 3), Wait1's at the whiff's end and the move's.

Every motion keeps the vanilla AttackDash's node order (vbn order, which the game reads the gameplay joints by).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import omo  # noqa: E402

GF_PUNCH = 7          # the dash punch's hitbox frames 7-10
GF_WHIFF_END = 38     # the whiff ends here (MSC), as vanilla Mario's dash attack (54 frames, acting from 39)
GF_JUMP_TO = 40       # the God Fist part starts here (the MSC jumps to it from the hit)
G = GF_JUMP_TO
GF_STRIKE = G + 10    # the God Fist hit
GF_IASA = G + 55      # he acts from here: the victim's flight (the strike's freeze, then 44 frames) is over
FRAMES = G + 60
# (out frame, motion, source frame): between two keys of the same motion the source plays (linearly), between
# different motions the poses cross-fade (smoothstep)
KEYS = [
    (0, 'A02Run', 5), (3, 'A02Run', 10),
    (5, 'C03AttackS4S', 12), (7, 'C03AttackS4S', 16), (10, 'C03AttackS4S', 16), (16, 'C03AttackS4S', 20),
    (22, 'C03AttackS4S', 20), (GF_WHIFF_END, 'A00Wait1', 0),
    (G, 'C03AttackS4S', 16), (G + 2, 'C03AttackS4S', 16), (G + 7, 'C03AttackS4S', 12), (G + 9, 'C03AttackS4S', 14),
    (G + 10, 'C03AttackS4S', 16), (G + 17, 'C03AttackS4S', 20), (G + 26, 'C03AttackS4S', 20),
    (G + 30, 'A03JumpB', 2), (G + 46, 'A03JumpB', 36),
    (G + 51, 'A05LandingLight', 4), (G + 59, 'A00Wait1', 0),
]
HAND_KEYS = [(0, 'C00Attack11', 3), (GF_WHIFF_END - 6, 'C00Attack11', 3), (GF_WHIFF_END, 'A00Wait1', 0),
             (G, 'C00Attack11', 3), (G + 49, 'C00Attack11', 3), (G + 59, 'A00Wait1', 0)]


def root_z(f):
    if f <= GF_PUNCH:
        t = f / GF_PUNCH
        return 16.0 * (1 - (1 - t) ** 2)
    if f <= 10:
        return 16.0 + 4.0 * (f - GF_PUNCH) / (10 - GF_PUNCH)
    return 20.0


def rot_y(f):
    """the hop over the back flip (53-75), on top of RotN's own height"""
    if G + 28 <= f <= G + 50:
        return 14.0 * math.sin(math.pi * (f - G - 28) / 22.0)
    return 0.0


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b = tuple(-x for x in b)
        d = -d
    if d > 0.9995:
        q = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(min(1.0, d))
        s = math.sin(th)
        wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
        q = tuple(wa * x + wb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def blend(a, b, t):
    return lerp(a[0], b[0], t), slerp(a[1], b[1], t), lerp(a[2], b[2], t)


class Source:
    def __init__(self, entries, prefix):
        self.e = entries
        self.prefix = prefix
        self.cache = {}

    def anim(self, motion):
        if motion not in self.cache:
            self.cache[motion] = omo.Omo(self.e[self.prefix + motion + '.omo'])
        return self.cache[motion]

    def pose(self, motion, fr, h, rest):
        """bone h's local (pos, quat, scale) at a (fractional) frame of motion; rest when the motion lacks it"""
        o = self.anim(motion)
        fr = max(0.0, min(o.frames - 1.0, fr))
        a = o.sample(h, int(math.floor(fr)))
        if a is None:
            return rest
        b = o.sample(h, min(o.frames - 1, int(math.floor(fr)) + 1))
        return blend(a, b, fr - math.floor(fr))


def at(keys, f):
    """(motion, source frame) pair(s) and the weight at output frame f"""
    for (f0, m0, s0), (f1, m1, s1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            t = (f - f0) / float(f1 - f0) if f1 > f0 else 0.0
            if m0 == m1:
                return [(m0, s0 + (s1 - s0) * t)], 0.0
            return [(m0, s0), (m1, s1)], t * t * (3 - 2 * t)
    f0, m0, s0 = keys[-1]
    return [(m0, s0)], 0.0


def build_motion(src, base_data, keys, frames, extra=None):
    """the motion: base_data's nodes (order, hashes) resampled from the keys; extra(h, f, pose) adjusts a pose"""
    o = omo.Omo(base_data)
    o.frames = frames
    for n in o.nodes:
        n[3] = [b''] * frames
    for n in list(o.nodes):
        h = n[1]
        rest = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0))
        pos, rot, scl = [], [], []
        for f in range(frames):
            pairs, t = at(keys, f)
            p = src.pose(pairs[0][0], pairs[0][1], h, rest)
            if len(pairs) > 1:
                p = blend(p, src.pose(pairs[1][0], pairs[1][1], h, rest), t)
            if extra:
                p = extra(h, f, p)
            pos.append(p[0])
            rot.append(p[1])
            scl.append(p[2])
        tr = omo.tracks(o, h)
        omo.set_node(o, h, pos if 'pos' in tr else None, rot if 'rot' in tr else None,
                     scl if 'scl' in tr else None)
    return o


def build(motion_dir, vbn_path, out_dir):
    bones = omo.vbn_read(vbn_path)
    names = {n: h for n, _p, h in bones}
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for part, prefix, keys in (('main', 'FitMarioBodyMain', KEYS), ('mariopt1', 'FitMarioBodyMariopt1', KEYS),
                               ('lhand', 'FitMarioBodyLhand', HAND_KEYS), ('rhand', 'FitMarioBodyRhand', HAND_KEYS)):
        entries = omo.pac_read(os.path.join(motion_dir, part + '.pac'))
        e = dict(entries)
        name = [n for n in e if n.endswith('AttackDash.omo')][0]
        src = Source(e, prefix)

        def extra(h, f, p, part=part):
            if part != 'main':
                return p
            if h == names['TransN']:
                return (p[0][0], p[0][1], root_z(f)), p[1], p[2]
            if h == names['RotN']:
                return (p[0][0], p[0][1] + rot_y(f), p[0][2]), p[1], p[2]
            return p
        o = build_motion(src, e[name], keys, FRAMES, extra)
        # node order unchanged (vbn order), every node still there
        assert [n[1] for n in o.nodes] == [n[1] for n in omo.Omo(e[name]).nodes]
        new = [(n, o.encode() if n == name else d) for n, d in entries]
        omo.pac_write(os.path.join(out_dir, part + '.pac'), new)
        out[part] = o
    return out, bones


def main():
    a = sys.argv[1:]
    png = None
    if '--png' in a:
        i = a.index('--png')
        png = a[i + 1]
        del a[i:i + 2]
    if len(a) != 3:
        sys.exit(__doc__)
    out, bones = build(*a)
    print('AttackDash: %d frames, %d nodes' % (out['main'].frames, len(out['main'].nodes)))
    if png:
        import supamario_godfist_render
        supamario_godfist_render.sheet(out['main'], bones, png,
                                       [0, 3, 5, 7, 10, 22, 30, 38, 40, 44, 47, 50, 60, 70, 74, 78, 82, 86, 91, 99])


if __name__ == '__main__':
    main()
