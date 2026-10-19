#!/usr/bin/env python3
"""Kirby with Marth's copy: Marth's sword in Strike neutral air, back air and up air.

  python3 tools/kirby_marth_sword.py KIRBY_DIR ANIMCMD_DIR VL_BIN RPX OUT_DIR

KIRBY_DIR   the fighter/kirby folder (model/body/c00/model.vbn, motion/body, motion/marthbody)
ANIMCMD_DIR script/animcmd/body (motion.mtable, effect.bin, sound.bin, expression.bin)
VL_BIN      fighter_param_vl_kirby.bin
RPX         the RPX the motion tables are read from (build/cave_fix_s4/cross_f.rpx)
OUT_DIR     gets motion/marthbody/{main,kirbypt1,kirbypt2}.pac, script/animcmd/body/
            {motion.mtable,effect.bin,sound.bin,expression.bin}, fighter_param_vl_kirby.bin and
            rpx_args.txt (rpx_patch.py args for the motion tables)

(fighters/kirby/specials.md "Marth copy sword".) The copy's sword (model marthsword on Kirby's
LHaveN) shows only in the Marth copy's own motions, 0x37D-0x384 (in game: Kirby's own slots
0x301-0x303 played the sword animations without it). Which animation a motion plays: Kirby's
static motion tables in the RPX's data, 1222 entries each, of animation file-name hashes (CRC32
from 0 of the full name without .omo, case kept): MAIN_TABLE (8 bytes a motion: hash, flags word)
for the main body, PT1_TABLE / PT2_TABLE (4 bytes) for Kirbypt1 / Kirbypt2.

So three Marth slots get the sword animations: 0x380 (full-charge ground end), 0x384 (full-charge
air end) and 0x382 (air charge loop); Shield Breaker (MSC func_2919) plays 0x37F / 0x383 / 0x37E
instead, which already had the same animations for the full-charge ends (and the ground loop for
the air charge), and binds the full-charge effects itself. The slots get the hashes of
FitKirbyMarthBody<part>D00<Name> (Kirby's own animations with LHaveN moved and scaled each frame)
and the original moves' flags; fighter_param_vl_kirby group 1 (6 bytes a motion; the first is 0
on loop motions) gets the original moves' values. The MSC binds the original moves' game
scripts after the motion change (marth_sword_play()).

The sword itself is switched on by the copy's effect script (in game: the slots' animations alone
didn't show it, Strike nair with the full-charge end's effects did): Sword_Trace on LHaveN
(Marth's, from MarthSpecialNEndMax) from the appear frame to Terminate_Sword_Glow at the gone
frame. So effect.bin / sound.bin get the moves' own scripts plus those two commands under the
names of the empty slots 0x301-0x303 (FX, motion.mtable), which the MSC binds as the effect /
sound set (copy_fx set 0x10). The slots' expression scripts (the MSC can't rebind those) become
the moves' own (the air charge loop's rumbled on in up air).
"""
import math
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omo  # noqa: E402

import acmd  # noqa: E402
import copy  # noqa: E402
import struct  # noqa: E402
import rpx_patch  # noqa: E402

EPS = 0.001          # "nothing": a zero scale would make a degenerate bone matrix
MAIN_TABLE = 0x103850A4
PT1_TABLE = 0x10382A0C
PT2_TABLE = 0x10383D24

# Marth copy slot, (unused), Kirby's animation (name, code), placement, frames (1 = the first):
# appears, starts shrinking, gone; the original motion
MOVES = [
    (0x380, None, 'Attack12', 'C00', 'hand', 3, 7, 15, 0x51),     # Strike nair (air jab 2)
    (0x384, None, 'AttackAirB', 'C05', 'legs', 7, 17, 27, 0x6A),
    (0x382, None, 'AttackAirHi', 'C05', 'lleg', 4, 16, 28, 0x6B),
]
FX = {0x380: (0x301, 'MarthSwordAttack12'), 0x384: (0x302, 'MarthSwordAttackAirB'),
      0x382: (0x303, 'MarthSwordAttackAirHi')}
SLOT_NAMES = {0x380: 'MarthSpecialNEndMax', 0x384: 'MarthSpecialAirNEndMax', 0x382: 'MarthSpecialAirNLoop'}
SWORD_FROM = 'marthspecialnendmax'      # the effect script whose Sword_Trace is used
FORWARD = (0.0, 0.0, 1.0)  # model +Z: where Kirby faces
DEPTH = (1.0, 0.0, 0.0)   # model X: toward / away from the camera (Kirby faces +Z)


def crc(name):
    return zlib.crc32(name.lower().encode()) & 0xFFFFFFFF


def timeline(cmds):
    """[(frame, command)] of a script with only FRAME / WAIT timing"""
    t = 0.0
    out = []
    for c in cmds:
        if c.ident == acmd.END:
            continue
        assert c.name not in ('Set_Loop', 'Goto'), 'loops in the script'
        if c.ident == acmd.BY_NAME['frame']:
            t = float(c.params[0])
        elif c.ident == acmd.BY_NAME['wait']:
            t += float(c.params[0])
        else:
            out.append((t, c))
    return out


def merge(cmds, extra):
    """the script with extra [(frame, command)] added, as FRAME-timed commands"""
    items = timeline(cmds) + extra
    items.sort(key=lambda x: x[0])        # stable: the script's own first at the same frame
    out = []
    t = 0.0
    for when, c in items:
        if when > t:
            out.append(acmd.Command(acmd.BY_NAME['frame'], [when]))
            t = when
        out.append(c)
    out.append(acmd.Command(acmd.END))
    return out


def anim_hash(name):
    """the motion tables' key of an animation file (name without .omo)"""
    return zlib.crc32(name.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


def vl_motion_offsets(data):
    """file offsets of the 6 s8 values of each motion in fighter_param_vl group 1"""
    i = 8
    assert data[i] == 0x20, 'no group at the start'
    i += 5
    out = []
    while i < len(data) and data[i] == 2:     # s8 values
        out.append(i + 1)
        i += 2
    assert len(out) % 6 == 0
    return [out[k:k + 6] for k in range(0, len(out), 6)]


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
        if appear <= fr + 1 < gone:
            w = omo.world(anim, bones, fr)
            if place == 'hand':      # in the left hand, blade straight forward
                g = pos(w['LHaveN'])
                root, tip = (0.0, 0.0, 0.0), FORWARD
            elif place == 'legs':      # between the legs: grip between the knees, blade toward the feet
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
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    kdir, adir, vl_in, rpx, out = sys.argv[1:]
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
        for slot, new, src, code, place, a, s, g, orig in MOVES:
            data = body['FitKirbyBody%s%s%s.omo' % (part, code, src)]
            if part == 'Main':
                anim = omo.Omo(data)
                have, P, R, S = sword_track(anim, bones, place, a, s, g)
                omo.set_node_full(anim, have, P, R, S)
                data = anim.encode()
            marth.append(('FitKirbyMarthBody%sD00%s.omo' % (part, src), data))
        omo.pac_write(os.path.join(mdir, fn), marth)

    # ACMD: effect / sound sets with the sword under the FX slots' names, the slots' expressions
    mt = open(os.path.join(adir, 'motion.mtable'), 'rb').read()
    table = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    for slot, (fx, name) in FX.items():
        assert table[fx] in (0, crc(name)), 'motion 0x%X is in use (0x%08X)' % (fx, table[fx])
        table[fx] = crc(name)
        assert table[slot] == crc(SLOT_NAMES[slot]), hex(slot)
    open(os.path.join(sdir, 'motion.mtable'), 'wb').write(struct.pack('>%dI' % len(table), *table))
    eff = acmd.ACMDFile.load(os.path.join(adir, 'effect.bin'))
    trace = [c for c in eff.script(SWORD_FROM) if c.name == 'Sword_Trace'][0]
    stop = [c for c in eff.script(SWORD_FROM) if c.name == 'Terminate_Sword_Glow'][0]
    snd = acmd.ACMDFile.load(os.path.join(adir, 'sound.bin'))
    exp = acmd.ACMDFile.load(os.path.join(adir, 'expression.bin'))
    for slot, new, src, code, place, a, s, g, orig in MOVES:
        fx, name = FX[slot]
        eff.scripts[crc(name)] = merge(eff.script(src) or [], [(float(a - 1), copy.deepcopy(trace)),
                                                              (float(g - 1), copy.deepcopy(stop))])
        snd.scripts[crc(name)] = copy.deepcopy(snd.script(src) or [acmd.Command(acmd.END)])
        exp.scripts[crc(SLOT_NAMES[slot])] = copy.deepcopy(exp.script(src) or [acmd.Command(acmd.END)])
    eff.save(os.path.join(sdir, 'effect.bin'))
    snd.save(os.path.join(sdir, 'sound.bin'))
    exp.save(os.path.join(sdir, 'expression.bin'))

    # the RPX motion tables
    d, _shoff, _ent, secs = rpx_patch.load(rpx)
    args = []
    for slot, new, src, code, place, a, s, g, orig in MOVES:
        flags = rpx_patch.read_u32(d, secs, MAIN_TABLE + 8 * orig + 4)
        for table, size, part in ((MAIN_TABLE, 8, 'Main'), (PT1_TABLE, 4, 'Kirbypt1'), (PT2_TABLE, 4, 'Kirbypt2')):
            args.append('0x%08X=0x%08X' % (table + size * slot, anim_hash('FitKirbyMarthBody%sD00%s' % (part, src))))
        args.append('0x%08X=0x%08X' % (MAIN_TABLE + 8 * slot + 4, flags))
    open(os.path.join(out, 'rpx_args.txt'), 'w').write(' '.join(args) + '\n')

    # per-motion params
    vl = bytearray(open(vl_in, 'rb').read())
    offs = vl_motion_offsets(vl)
    for slot, *_rest in MOVES:
        orig = _rest[-1]
        for a_, b_ in zip(offs[slot], offs[orig]):
            vl[a_] = vl[b_]
    open(os.path.join(out, 'fighter_param_vl_kirby.bin'), 'wb').write(vl)

    for slot, new, src, code, place, a, s, g, orig in MOVES:
        print('motion 0x%X (for 0x%X %s): sword %s, frames %d / %d / %d' % (slot, orig, src, place, a, s, g))


if __name__ == '__main__':
    main()
