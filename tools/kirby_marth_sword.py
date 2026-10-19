#!/usr/bin/env python3
"""Kirby with Marth's copy: Marth's sword in Strike neutral air, back air and up air.

  python3 tools/kirby_marth_sword.py KIRBY_DIR ANIMCMD_DIR GAME_BIN OUT_DIR

KIRBY_DIR   the fighter/kirby folder (model/body/c00/model.vbn, motion/body, motion/marthbody)
ANIMCMD_DIR script/animcmd/body (motion.mtable, effect.bin, sound.bin, expression.bin)
GAME_BIN    the game.bin to add to (build/game.bin)
OUT_DIR     gets motion/marthbody/{main,kirbypt1,kirbypt2}.pac and script/animcmd/body/
            {motion.mtable,game.bin,effect.bin,sound.bin,expression.bin}

How the copy's sword shows (fighters/kirby/specials.md "Marth copy sword"): the held model
(model/marthsword, root bone HaveN on Kirby's LHaveN) shows while Kirby plays an animation from
the copy's motion folder (motion/marthbody). A motion's name is its motion.mtable hash, and an
animation FitKirby<Copy>Body<Main|Kirbypt1|Kirbypt2><3 chars><Name>.omo in motion/<copy>body is
found under the name <Copy><Name> (MarthSpecialNStart = FitKirbyMarthBodyMainD00SpecialNStart).
So three empty motion slots get Marth names, marthbody gets those animations (Kirby's own, with
LHaveN moved and scaled each frame) and the ACMD gets the moves' scripts under the new names.
"""
import copy
import math
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402
import omo  # noqa: E402

EPS = 0.001          # "nothing": a zero scale would make a degenerate bone matrix

# motion slot, new name, Kirby's animation (name, code), placement, frames (1 = the first):
# appears, starts shrinking, gone
MOVES = [
    (0x301, 'MarthAttack12', 'Attack12', 'C00', 'hand', 3, 7, 15),        # Strike nair (air jab 2)
    (0x302, 'MarthAttackAirB', 'AttackAirB', 'C05', 'legs', 7, 17, 27),
    (0x303, 'MarthAttackAirHi', 'AttackAirHi', 'C05', 'lleg', 4, 16, 28),
]
DEPTH = (1.0, 0.0, 0.0)   # model X: toward / away from the camera (Kirby faces +Z)


def crc(name):
    return zlib.crc32(name.lower().encode()) & 0xFFFFFFFF


def scale_at(fr, appear, shrink, gone):
    f = fr + 1
    if f < appear or f >= gone:
        return EPS
    if f <= shrink:
        return 1.0
    return max(EPS, 1.0 - (f - shrink) / float(gone - shrink))


def pos(m):
    return tuple(m[i][3] for i in range(3))


def mid(a, b):
    return tuple((a[i] + b[i]) / 2 for i in range(3))


def norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def frame_with_y(origin, y):
    """world matrix at origin whose +Y (the blade) is y and +X faces the camera"""
    y = norm(y)
    d = sum(DEPTH[i] * y[i] for i in range(3))
    x = tuple(DEPTH[i] - d * y[i] for i in range(3))
    if math.sqrt(sum(c * c for c in x)) < 1e-4:
        x = (0.0, 0.0, 1.0)
    x = norm(x)
    z = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0])
    return [[x[i], y[i], z[i], origin[i]] for i in range(3)] + [[0, 0, 0, 1]]


def sword_track(anim, bones, place, appear, shrink, gone):
    have = next(h for n, p, h in bones if n == 'LHaveN')
    P, R, S = [], [], []
    for fr in range(anim.frames):
        s = scale_at(fr, appear, shrink, gone)
        lp, lq, ls = anim.sample(have, fr)
        if place != 'hand' and appear <= fr + 1 < gone:
            w = omo.world(anim, bones, fr)
            if place == 'legs':      # between the legs: grip between the knees, blade toward the feet
                g = mid(pos(w['LKneeJ']), pos(w['RKneeJ']))
                tip = mid(pos(w['LFootJ']), pos(w['RFootJ']))
                root = mid(pos(w['LLegJ']), pos(w['RLegJ']))
            else:                    # left leg: grip at the knee, blade along the leg past the foot
                g = pos(w['LKneeJ'])
                tip = pos(w['LFootJ'])
                root = pos(w['LLegJ'])
            want = frame_with_y(g, tuple(tip[i] - root[i] for i in range(3)))
            lp, lq, ls = omo.decompose(omo.mul(omo.inv(w['LHandN']), want))
        P.append(lp)
        R.append(lq)
        S.append(tuple(c * s for c in ls))
    return have, P, R, S


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    kdir, adir, game_in, out = sys.argv[1:]
    bones = omo.vbn_read(os.path.join(kdir, 'model/body/c00/model.vbn'))
    mdir = os.path.join(out, 'motion/marthbody')
    sdir = os.path.join(out, 'script/animcmd/body')
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(sdir, exist_ok=True)

    # animations
    for part in ('Main', 'Kirbypt1', 'Kirbypt2'):
        fn = part.lower() + '.pac'
        body = dict(omo.pac_read(os.path.join(kdir, 'motion/body', fn)))
        marth = [e for e in omo.pac_read(os.path.join(kdir, 'motion/marthbody', fn))
                 if not any(e[0].endswith('D00%s.omo' % m[2]) for m in MOVES)]
        for slot, new, src, code, place, a, s, g in MOVES:
            data = body['FitKirbyBody%s%s%s.omo' % (part, code, src)]
            if part == 'Main':
                anim = omo.Omo(data)
                have, P, R, S = sword_track(anim, bones, place, a, s, g)
                omo.set_node_full(anim, have, P, R, S)
                data = anim.encode()
            marth.append(('FitKirbyMarthBody%sD00%s.omo' % (part, src), data))
        omo.pac_write(os.path.join(mdir, fn), marth)

    # motion slots
    mt = open(os.path.join(adir, 'motion.mtable'), 'rb').read()
    table = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    for slot, new, *_ in MOVES:
        assert table[slot] in (0, crc(new)), 'motion 0x%X is in use (0x%08X)' % (slot, table[slot])
        table[slot] = crc(new)
    open(os.path.join(sdir, 'motion.mtable'), 'wb').write(struct.pack('>%dI' % len(table), *table))

    # ACMD: the moves' scripts under the new names
    for fn, path in (('game.bin', game_in), ('effect.bin', None), ('sound.bin', None), ('expression.bin', None)):
        f = acmd.ACMDFile.load(path or os.path.join(adir, fn))
        for slot, new, src, *_ in MOVES:
            if crc(src) in f.scripts:
                f.scripts[crc(new)] = copy.deepcopy(f.scripts[crc(src)])
        f.save(os.path.join(sdir, fn))
    for slot, new, src, code, place, a, s, g in MOVES:
        print('motion 0x%X %s (%s): sword %s, frames %d / %d / %d' % (slot, new, src, place, a, s, g))


if __name__ == '__main__':
    main()
