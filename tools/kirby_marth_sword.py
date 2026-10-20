#!/usr/bin/env python3
"""Kirby with Marth's copy: Marth's sword in Strike neutral air, back air and up air, and Marth's
forward smash with the sword.

  python3 tools/kirby_marth_sword.py [--marth MARTH_DIR] KIRBY_DIR ANIMCMD_DIR VL_BIN RPX OUT_DIR [GAME_BIN]

MARTH_DIR   the fighter/marth folder (model/body/c00/model.vbn, motion/body/main.pac and
            marthsw1.pac): the F-smash becomes Marth's own AttackS4S / AttackS4Charge retargeted
            onto Kirby (marth_retarget()); without it, Kirby's Roy-copy Flare Blade, retimed

KIRBY_DIR   the fighter/kirby folder (model/body/c00/model.vbn, motion/body, motion/marthbody,
            motion/roybody)
ANIMCMD_DIR script/animcmd/body (motion.mtable, effect.bin, sound.bin, expression.bin)
VL_BIN      fighter_param_vl_kirby.bin
RPX         the RPX the motion tables are read from (build/cave_fix_s4/cross_f.rpx)
OUT_DIR     gets motion/marthbody/{main,kirbypt1,kirbypt2}.pac, script/animcmd/body/
            {motion.mtable,game.bin,effect.bin,sound.bin,expression.bin}, fighter_param_vl_kirby.bin
            and rpx_args.txt (rpx_patch.py args for the motion tables)
GAME_BIN    the game.bin to add the F-smash's script to (default ANIMCMD_DIR's; build/game.bin)

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
SLOT_NAMES = {0x380: 'MarthSpecialNEndMax', 0x384: 'MarthSpecialAirNEndMax', 0x382: 'MarthSpecialAirNLoop',
              0x383: 'MarthSpecialAirNEnd', 0x381: 'MarthSpecialAirNStart'}
SWORD_FROM = 'marthspecialnendmax'      # the effect script whose Sword_Trace is used
FORWARD = (0.0, 0.0, 1.0)  # model +Z: where Kirby faces
BACK = (0.0, 0.0, -1.0)
SIZE = 2.0                 # the sword's size (user: double)
DEPTH = (1.0, 0.0, 0.0)   # model X: toward / away from the camera (Kirby faces +Z)

# F-smash (user: Marth's, with his sword). Kirby's own Roy-copy Flare Blade animations (start, charge
# loop, overhead slash ending in a lunge; the sword on LHaveN, blade +Y) retimed to Marth's forward
# smash: charge at frame 3, hits on frames 10-13, 50 frames (Kirby's own is 50). Two more Marth slots:
# 0x383 (air end) plays it, 0x381 (air start) the charge loop; Shield Breaker in the air plays the
# ground start / end (func_2919) and binds those slots' own effects (marth_full_charge_fx()).
FS_SLOT, FS_ORIG = 0x383, 0x5F                  # AttackS4 (0x5E / 0x61, the angled ones, too)
FS_HOLD_SLOT, FS_HOLD_ORIG = 0x381, 0x62        # AttackS4Hold
FS_FX = (0x304, 'MarthSwordAttackS4')           # game (hitboxes), effect and sound scripts
FS_HOLD_FX = (0x305, 'MarthSwordAttackS4Hold')  # effect and sound scripts
FS_NAME, FS_HOLD_NAME = 'AttackS4', 'AttackS4Hold'      # FitKirbyMarthBody<part>D00<name>
ROY = 'FitKirbyRoyBody%sD00SpecialN%s.omo'
FS_FRAMES = 50
FS_HOLD = 3                # Marth's charge frame (ON_FLAG 0x2100001B)
FS_SHRINK, FS_GONE = 44, 50
FS_SLASH = {4: 2, 5: 4, 6: 6, 7: 8, 8: 9, 9: 10, 10: 10.5, 11: 11, 12: 11.5, 13: 12}  # frame: End's
FS_BLEND = {4: 0.7, 5: 0.8}    # from the charge pose (Start's last frame) into End's
FS_HITS = (10, 11, 12, 13)
BLADE = 10.75              # the blade's end along LHaveN +Y (Marth's Sword_Trace), sword units
HOLD_FLAG = 0x2100001B
# Marth's AttackS4 hitboxes (his game.bin): (ID, where, damage, angle, KBG, BKB, size, hitlag, SDI, SFX)
# where: a point along the blade (0 grip, 1 end), 'hand' or 'body'. Marth's are on his sword (Z 2 and
# 7.3, the tipper), arm and body bones; here capsules / points at the same places on Kirby's sword.
FS_HITBOXES = [
    (0, (0.1, 0.55), 13.0, 361, 80, 55, 3.5, 0.7, 1.0, 3),
    (1, 'hand', 13.0, 361, 80, 55, 3.0, 0.7, 1.0, 3),
    (2, 'body', 13.0, 361, 80, 55, 2.0, 0.7, 1.0, 3),
    (3, 0.85, 18.0, 0xA5, 80, 80, 3.5, 1.5, 0.0, 8),
]
SFX_CHARGE = 0xBF          # Kirby's smash charge sound (AttackS4Hold)
SFX_SWING = 0x160040       # the Marth copy's sword swing (MarthSpecialNEnd)
SFX_VOICE = 0x3F0016       # Kirby's F-smash voice


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


def apply3(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def local_for(parent, origin, blade, length):
    """LHaveN local (pos, quat, scale) putting the grip at origin and the blade (+Y) along blade
    with world length `length`, exactly even when the parent's matrix is squashed (Kirby's body
    scales unevenly): the local axes are the parent-space images of the wanted ones, each scaled
    to the wanted world length (the cross-section may skew a little)."""
    ip = omo.inv(parent)
    p = tuple(ip[i][3] + sum(ip[i][k] * origin[k] for k in range(3)) for i in range(3))
    want = frame_with_y((0.0, 0.0, 0.0), blade)
    axes = [tuple(want[i][j] for i in range(3)) for j in range(3)]     # world X, Y, Z of the sword
    loc = [norm(apply3(ip, a)) for a in axes]
    y = loc[1]
    x = norm(tuple(loc[0][i] - sum(loc[0][k] * y[k] for k in range(3)) * y[i] for i in range(3)))
    z = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0])
    rot = [[x[i], y[i], z[i]] for i in range(3)]
    scale = tuple(length / math.sqrt(sum(c * c for c in apply3(parent, ax))) for ax in (x, y, z))
    return p, omo.mat2q(rot), scale


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
            elif place == 'legs':      # between the legs: grip between the knees, blade straight back
                g = mid(pos(w['LKneeJ']), pos(w['RKneeJ']))
                root, tip = (0.0, 0.0, 0.0), BACK
            else:                    # left leg: grip at the knee, blade along the leg past the foot
                g = pos(w['LKneeJ'])
                tip = pos(w['LFootJ'])
                root = pos(w['LLegJ'])
            lp, lq, ls = local_for(w['LHandN'], g, tuple(tip[i] - root[i] for i in range(3)), SIZE * s)
        else:
            ls = tuple(c * s * SIZE for c in ls)
        P.append(lp)
        R.append(lq)
        S.append(ls)
    return have, P, R, S


def slerp(a, b, t):
    d = sum(a[i] * b[i] for i in range(4))
    if d < 0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return norm(tuple(a[i] + (b[i] - a[i]) * t for i in range(4)))
    th = math.acos(d)
    sa, sb = math.sin((1 - t) * th), math.sin(t * th)
    return tuple((a[i] * sa + b[i] * sb) / math.sin(th) for i in range(4))


def blend(x, y, t):
    lerp = lambda u, v: tuple(u[i] + (v[i] - u[i]) * t for i in range(3))  # noqa: E731
    return lerp(x[0], y[0]), slerp(x[1], y[1], t), lerp(x[2], y[2])


def sample_at(anim, h, f):
    """(pos, quat, scale) of bone h at a fractional frame (clamped to the animation), or None"""
    f = min(max(f, 0.0), anim.frames - 1.0)
    a = int(math.floor(f))
    b = min(a + 1, anim.frames - 1)
    sa = anim.sample(h, a)
    return None if sa is None else blend(sa, anim.sample(h, b), f - a)


def resample(srcs, specs):
    """a new animation, frame i the blend of specs[i] = [(source name, frame, weight)]"""
    out = omo.Omo(next(iter(srcs.values())).encode())
    out.frames = len(specs)
    out.nodes = []
    hashes = []
    for a in srcs.values():
        hashes += [n[1] for n in a.nodes if n[1] not in hashes]
    for h in hashes:
        kinds = set()
        for a in srcs.values():
            kinds |= set(omo.tracks(a, h))
        vals = []
        for spec in specs:
            v, wsum = None, 0.0
            for name, f, w in spec:
                s = sample_at(srcs[name], h, f) if w > 0 else None
                if s is not None:
                    v = s if v is None else blend(v, s, w / (wsum + w))
                    wsum += w
            if v is None:
                v = next(sample_at(a, h, 0) for a in srcs.values() if a.node(h))
            vals.append(v)
        omo.set_node(out, h, *[[v[i] for v in vals] if k in kinds else None
                               for i, k in enumerate(('pos', 'rot', 'scl'))])
    return out


def fs_specs():
    """the F-smash's frames from Roy's Start / End, and the charge loop's from Loop"""
    attack = []
    for o in range(FS_FRAMES):
        if o <= FS_HOLD:
            attack.append([('Start', o * 11.0 / FS_HOLD, 1.0)])
            continue
        f = FS_SLASH.get(o, 12 + (o - 13) * 56.0 / (FS_FRAMES - 1 - 13))
        w = FS_BLEND.get(o, 1.0)
        attack.append([('Start', 11.0, 1.0 - w), ('End', f, w)])
    return attack, [[('Loop', float(o), 1.0)] for o in range(31)]


# ---------------------------------------------------------------- Marth's own F-smash on Kirby
# Retargeting: each body bone Kirby shares with Marth (the standard rig: TransN .. LHaveN) turns
# in the world the way Marth's does from his bind pose (a T-pose for both): Kirby world rotation =
# Marth's world rotation x Marth's bind world rotation^-1 x Kirby's bind world rotation. Bone
# lengths stay Kirby's; the root's and the hips' movement (TransN, RotN, HipN) is Marth's scaled
# by their heights (head 6.37 / 17.5) along the ground and by their leg lengths (hip to ankle)
# up and down. Kirby's own bones (body, mouth, cheeks) and the face parts
# come from Kirby's own F-smash, stretched to Marth's length. The sword (LHaveN, as before) is put
# in Kirby's right hand (Marth's RHaveN holds his SwordN) pointing where Marth's blade (SwordN
# +Z, marthsw1.pac) points.
MARTH_FS = ('AttackS4S', 'AttackS4Charge')       # Marth's animations (FitMarthBody<part>C03<name>)
KIRBY_FS = ('AttackS4S', 'AttackS4Charge')       # Kirby's own, for his extra bones and face
SHARED = ('TransN', 'RotN', 'HipN', 'LLegJ', 'LKneeJ', 'LFootJ', 'LToeN', 'RLegJ', 'RKneeJ', 'RFootJ',
          'RToeN', 'WaistN', 'BustN', 'LShoulderN', 'LShoulderJ', 'LArmJ', 'LHandN', 'RShoulderN',
          'RShoulderJ', 'RArmJ', 'RHandN', 'NeckN', 'HeadN', 'RHaveN', 'ThrowN')
ROOTS = ('TransN', 'RotN', 'HipN')
# The body, hips and legs move the way Marth's do from his standing pose (Wait1 frame 0), measured
# in his own frame and put on Kirby's standing pose, instead of from the T-pose: Marth stands
# side-on and his leg bones point down, Kirby's point out and back, so T-pose deltas spun Kirby
# and swung his feet up. The arms follow Marth's T-pose deltas (both hold them straight out), so
# the sword arm ends up where Marth's is. Kirby's own bones (body size, mouth, cheeks) stay as he
# stands.
BODY = ('RotN', 'HipN', 'WaistN', 'BustN', 'NeckN', 'HeadN')
LEGS = ('LLegJ', 'LKneeJ', 'LFootJ', 'LToeN', 'RLegJ', 'RKneeJ', 'RFootJ', 'RToeN')
# Kirby's body is one ball over all of BODY: turning those bones separately (Marth's spine, neck
# and head bend on their own) pulls the ball out of shape and slides the face over it, so they
# turn together, by Marth's chest's change (BODY_TURN of it: a ball tipping over as far as Marth
# bends looks like a somersault). The legs take LEG_MOVE of Marth's leg motion against his hips.
BODY_TURN = 0.5
LEG_MOVE = 0.6


def turn(a, b):
    """the smallest rotation taking unit vector a to b"""
    v = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    c = sum(a[i] * b[i] for i in range(3))
    if c < -0.9999:      # opposite: half a turn about any perpendicular axis
        p = norm((0.0, -a[2], a[1]) if abs(a[0]) < 0.9 else (-a[2], 0.0, a[0]))
        return [[2 * p[i] * p[j] - (1 if i == j else 0) for j in range(3)] for i in range(3)]
    k = 1.0 / (1.0 + c)
    vx = [[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]
    vx2 = m3(vx, vx)
    return [[(1 if i == j else 0) + vx[i][j] + vx2[i][j] * k for j in range(3)] for i in range(3)]


def damp(r, t):
    """rotation r scaled by t (slerp from no rotation)"""
    q = omo.mat2q(r)
    if q[3] < 0:
        q = tuple(-c for c in q)
    return omo.qmat(slerp((0.0, 0.0, 0.0, 1.0), q, t))


def vbn_bind(path):
    """{name: (pos, quat, scale)} the bind pose (Euler XYZ angles, R = Rz Ry Rx)"""
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    bones = omo.vbn_read(path)
    off = 28 + 76 * len(bones)
    out = {}
    for name, _p, _h in bones:
        v = struct.unpack(e + '9f', d[off:off + 36])
        off += 36
        cx, sx = math.cos(v[3] / 2), math.sin(v[3] / 2)
        cy, sy = math.cos(v[4] / 2), math.sin(v[4] / 2)
        cz, sz = math.cos(v[5] / 2), math.sin(v[5] / 2)
        q = (sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz, cx * cy * sz - sx * sy * cz,
             cx * cy * cz + sx * sy * sz)
        out[name] = (v[0:3], q, v[6:9])
    return out


def worlds(bones, local):
    """{name: world matrix} from local(name) -> (pos, quat, scale)"""
    out = {}
    for name, parent, _h in bones:
        m = omo.trs(*local(name))
        out[name] = omo.mul(out[bones[parent][0]], m) if 0 <= parent < len(bones) else m
    return out


def rot3(m):
    """the rotation of a matrix (scale taken out)"""
    cols = [norm(tuple(m[i][j] for i in range(3))) for j in range(3)]
    return [[cols[j][i] for j in range(3)] for i in range(3)]


def m3(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def t3(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def marth_retarget(kdir, mdir, kbones, which, sword):
    """{part: Omo} Marth's animation `which` (0 F-smash, 1 charge loop) on Kirby"""
    mbones = omo.vbn_read(os.path.join(mdir, 'model/body/c00/model.vbn'))
    mbind = vbn_bind(os.path.join(mdir, 'model/body/c00/model.vbn'))
    kbind = vbn_bind(os.path.join(kdir, 'model/body/c00/model.vbn'))
    mh = {n: h for n, _p, h in mbones}
    kh = {n: h for n, _p, h in kbones}
    mname = MARTH_FS[which]
    main = omo.Omo(dict(omo.pac_read(os.path.join(mdir, 'motion/body/main.pac')))[
        'FitMarthBodyMainC03%s.omo' % mname])
    sw = omo.Omo(dict(omo.pac_read(os.path.join(mdir, 'motion/body/marthsw1.pac')))[
        'FitMarthBodyMarthsw1C03%s.omo' % mname])
    n = main.frames
    kparts = {}
    for part in ('Main', 'Kirbypt1', 'Kirbypt2'):
        pac = dict(omo.pac_read(os.path.join(kdir, 'motion/body', part.lower() + '.pac')))
        name = next(n for n in ['FitKirbyBody%sC03%s.omo' % (part, k) for k in (KIRBY_FS[which], KIRBY_FS[0])]
                    if n in pac)     # Kirbypt2 has no charge loop
        kparts[part] = omo.Omo(pac[name])
    kmain = kparts['Main']
    stretch = lambda f: f * (kmain.frames - 1) / float(max(1, n - 1))    # noqa: E731
    mbw = worlds(mbones, lambda b: mbind[b])
    kbw = worlds(kbones, lambda b: kbind[b])
    mwait = omo.Omo(dict(omo.pac_read(os.path.join(mdir, 'motion/body/main.pac')))['FitMarthBodyMainA00Wait1.omo'])
    kwait = omo.Omo(dict(omo.pac_read(os.path.join(kdir, 'motion/body/main.pac')))['FitKirbyBodyMainA00Wait1.omo'])
    mst = worlds(mbones, lambda b: mwait.sample(mh[b], 0) or mbind[b])
    kst = worlds(kbones, lambda b: kwait.sample(kh[b], 0) or kbind[b])
    ratio = kbw['HeadN'][1][3] / mbw['HeadN'][1][3]     # head heights: moving along the ground
    leg = lambda w: w['HipN'][1][3] - (w['LFootJ'][1][3] + w['RFootJ'][1][3]) / 2   # noqa: E731
    yratio = leg(kbw) / leg(mbw)    # hip to ankle: crouching (Kirby's legs are tiny: his hips can't drop far)
    out = {}
    tracks = {name: ([], [], []) for name, _p, _h in kbones}
    I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    nrm = lambda w, b, bw: m3(rot3(w[b]), t3(rot3(bw[b])))     # noqa: E731  (orientation vs the T-pose)
    def foot_low(w):
        """the lowest of each foot's ankle, toe, toe tip and heel (the mesh reaches past the bones)"""
        ys = []
        for a_, t_ in (('LFootJ', 'LToeN'), ('RFootJ', 'RToeN')):
            fa, ft = w[a_][1][3], w[t_][1][3]
            ys += [fa, ft, ft + (ft - fa) * 0.7, fa - (ft - fa) * 0.5]
        return min(ys)
    kfoot = foot_low(kst)        # standing
    for f in range(n):
        def mlocal(b, f=f):
            src = sw if b in ('SwordN', 'SwordHeadN') and sw.node(mh[b]) else main
            v = src.sample(mh[b], f)
            return v if v else mbind[b]
        mw = worlds(mbones, mlocal)
        # the body: Kirby's standing pose, leaning forward / back with BODY_TURN of Marth's chest's
        # lean (its pitch about the sideways X axis; no turning or twisting: a ball that turns
        # with Marth's torso looks like it spins)
        up = m3(nrm(mw, 'BustN', mbw), t3(nrm(mst, 'BustN', mbw)))
        up = (up[0][1], up[1][1], up[2][1])           # the chest's up after its change from standing
        pitch = math.atan2(up[2], up[1]) * BODY_TURN
        c, sn = math.cos(pitch), math.sin(pitch)
        wbody = [[1, 0, 0], [0, c, -sn], [0, sn, c]]

        def marth_arm(side):
            a, b = pos(mw[side + 'ShoulderJ']), pos(mw[side + 'HandN'])
            return norm(tuple(b[i] - a[i] for i in range(3)))

        def pose(lift, aim):
            kw, locs = {}, {}
            for name, parent, h in kbones:
                pr = rot3(kw[kbones[parent][0]]) if 0 <= parent < len(kbones) else I3
                if name in BODY or name in LEGS or name in ('LShoulderJ', 'RShoulderJ'):
                    if name in LEGS:
                        nm = nrm(kst, name, kbw)        # planted: as he stands
                    else:
                        nm = m3(wbody, nrm(kst, name, kbw))
                        if name in aim:                 # the whole arm pointed (shoulder -> hand)
                            nm = m3(aim[name], nm)
                    q = omo.mat2q(m3(t3(pr), m3(nm, rot3(kbw[name]))))
                    if name in ROOTS:
                        mp = mlocal(name)[0]
                        p = tuple(kbind[name][0][i] + (mp[i] - mbind[name][0][i]) * (yratio if i == 1 else ratio)
                                  for i in range(3))
                        if name == 'RotN':
                            p = (p[0], p[1] + lift, p[2])
                    else:
                        p = (kwait.sample(h, 0) or kbind[name])[0]
                    loc = (p, q, kbind[name][2])
                elif name == 'TransN':
                    mp = mlocal(name)[0]
                    loc = (tuple(kbind[name][0][i] + (mp[i] - mbind[name][0][i]) * (yratio if i == 1 else ratio)
                                 for i in range(3)), (0.0, 0.0, 0.0, 1.0), kbind[name][2])
                else:      # the rest of the arms, the head's own bones, Kirby's extra bones: standing
                    loc = kwait.sample(h, 0) or kbind[name]
                m = omo.trs(*loc)
                kw[name] = omo.mul(kw[kbones[parent][0]], m) if 0 <= parent < len(kbones) else m
                locs[name] = loc
            return kw, locs

        def aims(kw):
            out = {}
            for side in ('L', 'R'):
                a, b = pos(kw[side + 'ShoulderJ']), pos(kw[side + 'HandN'])
                out[side + 'ShoulderJ'] = turn(norm(tuple(b[i] - a[i] for i in range(3))), marth_arm(side))
            return out

        kw, locs = pose(0.0, {})
        aim = aims(kw)
        kw, locs = pose(0.0, aim)
        low = foot_low(kw)
        if low < kfoot - 0.05:          # a foot through the floor: lift the body
            kw, locs = pose(kfoot - low, aim)
        for name, _p, _h in kbones:
            for i in range(3):
                tracks[name][i].append(locs[name][i])
        # the sword: grip in Kirby's right hand, blade along Marth's
        s = scale_at(f, *sword)
        if s > EPS:
            blade = tuple(mw['SwordN'][i][2] for i in range(3))
            lp, lq, ls = local_for(kw['LHandN'], pos(kw['RHaveN']), blade, SIZE * s)
        else:
            lp, lq, _ = (tracks['LHaveN'][i][-1] for i in range(3))
            ls = (EPS, EPS, EPS)
        tracks['LHaveN'][0][-1], tracks['LHaveN'][1][-1], tracks['LHaveN'][2][-1] = lp, lq, ls
    anim = omo.Omo(kmain.encode())
    anim.frames = n
    anim.nodes = []
    for name, _p, h in kbones:
        if kmain.node(h) or kwait.node(h) or name in SHARED or name == 'LHaveN':
            omo.set_node_full(anim, h, *tracks[name])
    out['Main'] = anim
    for part in ('Kirbypt1', 'Kirbypt2'):
        k = kparts[part]
        out[part] = resample({'K': k}, [[('K', f * (k.frames - 1) / float(max(1, n - 1)), 1.0)] for f in range(n)])
    return out


def fs_sword(anim, bones, appear, shrink, gone):
    """Roy's sword placement, SIZE times as big, shrinking away at the end"""
    have = next(h for n, p, h in bones if n == 'LHaveN')
    P, R, S = [], [], []
    for fr in range(anim.frames):
        lp, lq, ls = anim.sample(have, fr)
        s = scale_at(fr, appear, shrink, gone)
        P.append(lp)
        R.append(lq)
        S.append(tuple(c * s * SIZE for c in ls))
    omo.set_node(anim, have, P, R, S)


def fs_game(anim, bones):
    """the F-smash's game script: Marth's charge frame and hitboxes, on bone 0 (TransN) at the
    sword's place each active frame"""
    C = acmd.Command
    out = [C(acmd.BY_NAME['frame'], [float(FS_HOLD)]), C(acmd.BY_NAME['on_flag'], [HOLD_FLAG])]
    for fr in FS_HITS:
        w = omo.world(anim, bones, fr)
        it = omo.inv(w['TransN'])
        rel = lambda p: tuple(it[i][3] + sum(it[i][k] * p[k] for k in range(3)) for i in range(3))  # noqa: E731
        m = w['LHaveN']
        along = lambda t: rel(tuple(m[i][3] + m[i][1] * BLADE * t for i in range(3)))  # noqa: E731
        out.append(C(acmd.BY_NAME['frame'], [float(fr)]))
        for hid, where, dmg, ang, kbg, bkb, size, lag, sdi, sfx in FS_HITBOXES:
            if where == 'hand':
                a = b = rel(pos(m))
            elif where == 'body':
                a = b = rel(pos(w['BustN']))
            elif isinstance(where, tuple):
                a, b = along(where[0]), along(where[1])
            else:
                a = b = along(where)
            out.append(C(acmd.BY_NAME['extended_hitbox'],
                         [hid, 0, 0, dmg, ang, kbg, 0, bkb, size, a[0], a[1], a[2], 2, 0.0, lag, sdi,
                          1, 1, 0, 2, sfx, 3, 1, 0xA, b[0], b[1], b[2]]))
    out.append(C(acmd.BY_NAME['frame'], [float(FS_HITS[-1] + 1)]))
    out.append(C(acmd.BY_NAME['remove_all_hitboxes']))
    out.append(C(acmd.END))
    return out


def fs_effects(eff, trace, stop):
    """F-smash: the sword (from frame 0, again after the charge in case the release skips it),
    Kirby's smash flash, Marth's dust; the charge loop: the sword plus Kirby's charge effects"""
    C = acmd.Command
    flash = [c for c in eff.script('AttackS4') if c.name == 'EFFECT_FOLLOW_FLIP'][0]
    dust = C(acmd.BY_NAME['graphic_effect'], [0x1000020, 0] + [0.0] * 6 + [1.0] + [0.0] * 6 + [0])
    dash = C(acmd.BY_NAME['graphic_effect3'], [0x1000020, 0, 8.0, 0.0, 0.0, 0.0, 180.0, 0.0, 0.5] +
             [0.0] * 6 + [0])
    attack = merge([C(acmd.END)], [(0.0, copy.deepcopy(trace)), (1.0, copy.deepcopy(flash)),
                                   (float(FS_HOLD + 1), copy.deepcopy(trace)), (5.0, dust),
                                   (13.0, dash), (float(FS_GONE - 1), copy.deepcopy(stop))])
    hold = [copy.deepcopy(trace)] + copy.deepcopy(eff.script('AttackS4Hold'))
    return attack, hold


def fs_sounds(snd):
    C = acmd.Command
    attack = merge([C(acmd.END)], [(float(FS_HOLD + 1), C(acmd.BY_NAME['stop_sound_effect'], [SFX_CHARGE])),
                                   (8.0, C(acmd.BY_NAME['sound_effect'], [SFX_SWING])),
                                   (9.0, C(acmd.BY_NAME['sound_effect'], [SFX_VOICE]))])
    return attack, copy.deepcopy(snd.script('AttackS4Hold'))


def main():
    global FS_FRAMES, FS_SHRINK, FS_GONE
    args = sys.argv[1:]
    marth_dir = None
    if args[:1] == ['--marth']:
        marth_dir, args = args[1], args[2:]
    if len(args) not in (5, 6):
        sys.exit(__doc__)
    kdir, adir, vl_in, rpx, out = args[:5]
    game_in = args[5] if len(args) == 6 else os.path.join(adir, 'game.bin')
    bones = omo.vbn_read(os.path.join(kdir, 'model/body/c00/model.vbn'))
    mdir = os.path.join(out, 'motion/marthbody')
    sdir = os.path.join(out, 'script/animcmd/body')
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(sdir, exist_ok=True)

    # animations
    retarget = None
    if marth_dir:
        attack = marth_retarget(kdir, marth_dir, bones, 0, (1, 0, 0))   # length first
        FS_FRAMES = attack['Main'].frames
        FS_SHRINK, FS_GONE = FS_FRAMES - 6, FS_FRAMES
        retarget = (marth_retarget(kdir, marth_dir, bones, 0, (1, FS_SHRINK, FS_GONE)),
                    marth_retarget(kdir, marth_dir, bones, 1, (1, 999, 1000)))
    for part in ('Main', 'Kirbypt1', 'Kirbypt2'):
        fn = part.lower() + '.pac'
        body = dict(omo.pac_read(os.path.join(kdir, 'motion/body', fn)))
        ours = [m[2] for m in MOVES] + [FS_NAME, FS_HOLD_NAME]
        marth = [e for e in omo.pac_read(os.path.join(kdir, 'motion/marthbody', fn))
                 if not any(e[0].endswith('D00%s.omo' % n) for n in ours)]
        for slot, new, src, code, place, a, s, g, orig in MOVES:
            data = body['FitKirbyBody%s%s%s.omo' % (part, code, src)]
            if part == 'Main':
                anim = omo.Omo(data)
                have, P, R, S = sword_track(anim, bones, place, a, s, g)
                omo.set_node_full(anim, have, P, R, S)
                data = anim.encode()
            marth.append(('FitKirbyMarthBody%sD00%s.omo' % (part, src), data))
        roy = dict(omo.pac_read(os.path.join(kdir, 'motion/roybody', fn)))
        srcs = {k: omo.Omo(roy[ROY % (part, k)]) for k in ('Start', 'Loop', 'End')}
        for i, (name, specs, sword) in enumerate(((FS_NAME, fs_specs()[0], (1, FS_SHRINK, FS_GONE)),
                                                  (FS_HOLD_NAME, fs_specs()[1], (1, 999, 1000)))):
            if retarget:
                anim = retarget[i][part]
            else:
                anim = resample(srcs, specs)
                if part == 'Main':
                    fs_sword(anim, bones, *sword)
            if part == 'Main' and name == FS_NAME:
                fs_attack = anim
            marth.append(('FitKirbyMarthBody%sD00%s.omo' % (part, name), anim.encode()))
        omo.pac_write(os.path.join(mdir, fn), marth)

    # ACMD: effect / sound sets with the sword under the FX slots' names, the slots' expressions
    mt = open(os.path.join(adir, 'motion.mtable'), 'rb').read()
    table = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    for slot, (fx, name) in list(FX.items()) + [(FS_SLOT, FS_FX), (FS_HOLD_SLOT, FS_HOLD_FX)]:
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
    # F-smash
    eff.scripts[crc(FS_FX[1])], eff.scripts[crc(FS_HOLD_FX[1])] = fs_effects(eff, trace, stop)
    snd.scripts[crc(FS_FX[1])], snd.scripts[crc(FS_HOLD_FX[1])] = fs_sounds(snd)
    exp.scripts[crc(SLOT_NAMES[FS_SLOT])] = copy.deepcopy(exp.script(FS_NAME))
    exp.scripts[crc(SLOT_NAMES[FS_HOLD_SLOT])] = copy.deepcopy(exp.script(FS_HOLD_NAME))
    game = acmd.ACMDFile.load(game_in)
    game.scripts[crc(FS_FX[1])] = fs_game(fs_attack, bones)
    game.save(os.path.join(sdir, 'game.bin'))
    eff.save(os.path.join(sdir, 'effect.bin'))
    snd.save(os.path.join(sdir, 'sound.bin'))
    exp.save(os.path.join(sdir, 'expression.bin'))

    # the RPX motion tables
    d, _shoff, _ent, secs = rpx_patch.load(rpx)
    args = []
    for slot, new, src, code, place, a, s, g, orig in MOVES + [(FS_SLOT, None, FS_NAME, 0, 0, 0, 0, 0, FS_ORIG),
                                                              (FS_HOLD_SLOT, None, FS_HOLD_NAME, 0, 0, 0, 0, 0,
                                                               FS_HOLD_ORIG)]:
        flags = rpx_patch.read_u32(d, secs, MAIN_TABLE + 8 * orig + 4)
        for table, size, part in ((MAIN_TABLE, 8, 'Main'), (PT1_TABLE, 4, 'Kirbypt1'), (PT2_TABLE, 4, 'Kirbypt2')):
            args.append('0x%08X=0x%08X' % (table + size * slot, anim_hash('FitKirbyMarthBody%sD00%s' % (part, src))))
        args.append('0x%08X=0x%08X' % (MAIN_TABLE + 8 * slot + 4, flags))
    open(os.path.join(out, 'rpx_args.txt'), 'w').write(' '.join(args) + '\n')

    # per-motion params
    vl = bytearray(open(vl_in, 'rb').read())
    offs = vl_motion_offsets(vl)
    for slot, orig in [(m[0], m[-1]) for m in MOVES] + [(FS_SLOT, FS_ORIG), (FS_HOLD_SLOT, FS_HOLD_ORIG)]:
        for a_, b_ in zip(offs[slot], offs[orig]):
            vl[a_] = vl[b_]
    open(os.path.join(out, 'fighter_param_vl_kirby.bin'), 'wb').write(vl)

    for slot, new, src, code, place, a, s, g, orig in MOVES:
        print('motion 0x%X (for 0x%X %s): sword %s, frames %d / %d / %d' % (slot, orig, src, place, a, s, g))
    print('motion 0x%X (for 0x%X): F-smash, 0x%X (for 0x%X): its charge; scripts 0x%X / 0x%X' %
          (FS_SLOT, FS_ORIG, FS_HOLD_SLOT, FS_HOLD_ORIG, FS_FX[0], FS_HOLD_FX[0]))


if __name__ == '__main__':
    main()
