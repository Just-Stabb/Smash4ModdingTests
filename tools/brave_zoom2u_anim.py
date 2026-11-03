#!/usr/bin/env python3
"""Hero's Zoom 2 U (fix 79, the user's spell 23): Zoom's flight (SpecialLw16Hi, his body straight up) turned
on its side, head first along his facing, as a new animation in his body main.pac.

  python3 tools/brave_zoom2u_anim.py MAIN_PAC MODEL_VBN OUT_PAC

MAIN_PAC: his motion/body/main.pac (with FitRefletBodyMainD03SpecialLwSpell9Hi.omo, Ultimate's
d03speciallwspell9hi); MODEL_VBN: his model/body/c00/model.vbn (the bone hashes). Writes OUT_PAC = MAIN_PAC
plus FitRefletBodyMainD03SpecialLwSpell9Side.omo (extra_kinds.json "motions" 0x280): RotN's rotation
pre-multiplied by +90 degrees about X (the model faces +Z, so up becomes forward), and RotN moved back along
Z so his body's middle (hip to head, frame 0) stays over his position. Every other bone as it was, so the
flight effect (brave_flying_line on `rot`, EFFECT_FOLLOW) turns with him.
"""
import math
import struct
import sys

import omo

SRC = 'FitRefletBodyMainD03SpecialLwSpell9Hi.omo'
DST = 'FitRefletBodyMainD03SpecialLwSpell9Side.omo'
ANGLE = 90.0


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def rotx(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)


def build(entries, bones):
    e = dict(entries)
    src = omo.Omo(e[SRC])
    names = {n: h for n, _p, h in bones}
    rot_h = names['RotN']
    a = math.radians(ANGLE)
    qx = (math.sin(a / 2), 0.0, 0.0, math.cos(a / 2))
    # the body's middle at frame 0, relative to RotN, turned: moved back so it stays over his position
    w = omo.world(src, bones, 0)
    piv = [w['RotN'][i][3] for i in range(3)]
    mid = [(w['HipN'][i][3] + w['HeadN'][i][3]) / 2 - piv[i] for i in range(3)]
    shift_z = -rotx(mid, a)[2]
    pos, rot, scl = [], [], []
    for fr in range(src.frames):
        p, q, s = src.sample(rot_h, fr)
        pos.append((p[0], p[1], p[2] + shift_z))
        rot.append(qmul(qx, q))
        scl.append(s)
    out = omo.Omo(e[SRC])
    omo.set_node(out, rot_h, pos, rot, scl)
    return out.encode(), shift_z


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    entries = [x for x in omo.pac_read(sys.argv[1]) if x[0] != DST]
    data, shift = build(entries, omo.vbn_read(sys.argv[2]))
    omo.pac_write(sys.argv[3], entries + [(DST, data)])
    print('%s: RotN +%g deg about X, back %.2f along Z; %d entries' % (DST, ANGLE, -shift, len(entries) + 1))


if __name__ == '__main__':
    main()
