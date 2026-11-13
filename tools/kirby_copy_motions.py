#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy body motions: Ultimate's kirby/motion/bravebody / edgebody (.nuanmb) as Smash 4
copy packs (fighter/kirby/motion/bravebody / edgebody: main.pac, kirbypt1.pac, kirbypt2.pac).
fighters/kirby/specials.md "Hero / Sephiroth copies" and "Visual fix v1".

  python3 tools/kirby_copy_motions.py ULT_KIRBY_DIR S4_KIRBY_DIR OUT_MOTION_DIR [--check]

ULT_KIRBY_DIR: Ultimate's kirby/ (motion/bravebody/c00, motion/edgebody/c00, model/body/c00/model.nusktb).
S4_KIRBY_DIR: Smash 4's fighter/kirby (model/body/c00/model.vbn, motion/refletbody/*.pac).
--check: the two bind poses bone by bone, and (with OUT_MOTION_DIR) every frame of the built packs against Ultimate's
forward kinematics (world position and turn of every mapped bone).

Both copies are granted as Kirby's Robin copy (kind 0x2C, the executable's copy-resource cave loads these packs in
place of refletbody for a Hero / Sephiroth player: tools/kirby_copy_new_cave.py). A copy motion's animation is found by
the CRC32 of its file name (Kirby's static motion table, 1222 hashes: fighters/kirby/specials.md "How Kirby's motions
pick animations"), so each Ultimate animation is stored under the name of the Robin copy slot that plays it
(FitKirbyRefletBody{Main,Kirbypt1,Kirbypt2}D00<slot>.omo); the slots and their flags (0x2 = looping):

  slot (ground / air)       Robin's            Hero                     Sephiroth
  0x446 / 0x44D             SpecialNStart      SpecialNStart (12)       SpecialNStart (cancel 172)
  0x447 / 0x44E  loop       SpecialNHold       SpecialNCancel (6)       -
  0x448-0x449 / 0x44F-0x450 SpecialNShoot      SpecialN1 (44)           SpecialN1 (56)
  0x44A / 0x451             SpecialNTronStart  SpecialN2 (52)           SpecialN2 (70)
  0x44B / 0x452  loop       SpecialNTronHold   SpecialNHold (loop)      -
  0x44C / 0x453             SpecialNTronEnd    SpecialN3 (68)           SpecialNCancel (8)
(in brackets Ultimate's motion_list cancel frames, kirby/motion/body/c00: vl byte 2.) The MSC
(fighters/kirby/kirby.c "Hero / Sephiroth copies") plays them and ends / cancels them by those frames itself, so a
looping slot holding a one-shot animation is fine.

Bones (Visual fix v1): Kirby's two skeletons have the same bind pose in world space, bone for bone (--check), but not
the same parents everywhere: Ultimate hangs both legs under LegC (Hip + 2.392 along Hip's X, i.e. up) and both
clavicles under ClavicleC (Bust + 0.05), where Smash 4 hangs LLegJ / RLegJ straight on HipN and L/RShoulderN on BustN.
So the local tracks can't be copied as they are (stage 1 did: the legs' local (0, 0, 0.01) on HipN put both legs,
knees, feet and toes 2.392 too low on every frame, the feet in the floor, the clavicles 0.05 off). Each Smash 4 bone
now gets the transform from its Smash 4 parent's counterpart to its own counterpart in Ultimate's posed skeleton
(forward kinematics through LegC / ClavicleC, which don't scale, so it decomposes exactly).
Scale and units: the same in both games. Ultimate's tracks here have no compensate-scale flag, so children inherit
their parent's scale as Smash 4's do (vanilla motions the two games share, e.g. A01Turn / A01WalkFast, have the same
scale values, Waist 0.78-1.08, bone for bone); the bind poses and the body meshes are identical (vertex boxes equal to
0.01), so translations need no ratio.
Smash 4 plays Kirby's body sphere bone (BodyBN, which the whole body mesh, eyes and face are bound to) from the part
pack kirbypt1 and the mouth bones from kirbypt2 (vanilla main.pac motions don't have them, every vanilla part entry has
its main motion's frame count). Those tracks (Ultimate's Body, Mouth1, the lips, MouthD1 / D2, Cheek, Puff:
FACE_BONES) are written there with the main motion's frame count; stage 1 shipped the Robin copy's own part packs
(Robin's body lean, up to ~37 degrees, timed for Robin's 8-76 frame motions) under Ultimate's main motions.
"""
import argparse
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402

BONES = {   # Ultimate bone -> Smash 4 bone: main.pac
    'Trans': 'TransN', 'Rot': 'RotN', 'Hip': 'HipN', 'Waist': 'WaistN', 'Bust': 'BustN', 'Neck': 'NeckN',
    'Head': 'HeadN', 'Throw': 'ThrowN',
    'LegL': 'LLegJ', 'KneeL': 'LKneeJ', 'FootL': 'LFootJ', 'ToeL': 'LToeN',
    'LegR': 'RLegJ', 'KneeR': 'RKneeJ', 'FootR': 'RFootJ', 'ToeR': 'RToeN',
    'ClavicleL': 'LShoulderN', 'ShoulderL': 'LShoulderJ', 'ArmL': 'LArmJ', 'HandL': 'LHandN', 'HaveL': 'LHaveN',
    'ClavicleR': 'RShoulderN', 'ShoulderR': 'RShoulderJ', 'ArmR': 'RArmJ', 'HandR': 'RHandN', 'HaveR': 'RHaveN',
}
FACE_BONES = {   # the part packs, as vanilla Kirby splits them: kirbypt1 the body sphere, kirbypt2 the mouth
    'kirbypt1': {'Body': 'BodyBN'},
    'kirbypt2': {'Mouth1': 'MouthN', 'MouthLa1': 'MouthL1stN', 'MouthRa1': 'MouthR1stN', 'MouthLb': 'MouthL2ndN',
                 'MouthRb': 'MouthR2ndN', 'MouthLc': 'MouthL3rdN', 'MouthRc': 'MouthR3rdN', 'MouthLd': 'MouthL4thN',
                 'MouthRd': 'MouthR4thN', 'MouthLe': 'MouthL5rdN', 'MouthRe': 'MouthR5rdN', 'MouthD1': 'MouthShitaN',
                 'MouthD2': 'MouthShitaNb', 'Cheek': 'CheekN', 'Puff': 'HukumiN'},
}
PACKS = (('main', 'Main', BONES), ('kirbypt1', 'Kirbypt1', FACE_BONES['kirbypt1']),
         ('kirbypt2', 'Kirbypt2', FACE_BONES['kirbypt2']))
ALL_BONES = dict(BONES, **FACE_BONES['kirbypt1'], **FACE_BONES['kirbypt2'])
SLOTS = {   # Robin copy slot name -> {pack: Ultimate animation}
    'bravebody': {
        'SpecialNStart': 'braved00specialnstart', 'SpecialNHold': 'braved00specialncancel',
        'SpecialNShoot': 'braved00specialn1', 'SpecialNTronStart': 'braved00specialn2',
        'SpecialNTronHold': 'braved00specialnhold', 'SpecialNTronEnd': 'braved00specialn3',
        'SpecialAirNStart': 'braved00specialairnstart', 'SpecialAirNHold': 'braved00specialairncancel',
        'SpecialAirNShoot': 'braved00specialairn1', 'SpecialAirNTronStart': 'braved00specialairn2',
        'SpecialAirNTronHold': 'braved00specialairnhold', 'SpecialAirNTronEnd': 'braved00specialairn3',
    },
    'edgebody': {
        'SpecialNStart': 'edged00specialnstart', 'SpecialNShoot': 'edged00specialn1',
        'SpecialNTronStart': 'edged00specialn2', 'SpecialNTronEnd': 'edged00specialncancel',
        'SpecialAirNStart': 'edged00specialairnstart', 'SpecialAirNShoot': 'edged00specialairn1',
        'SpecialAirNTronStart': 'edged00specialairn2', 'SpecialAirNTronEnd': 'edged00specialairncancel',
    },
}
PREFIX = 'FitKirbyRefletBody'


# ---------------------------------------------------------------- matrices (column vectors, [..., 4, 4])
def _quat_mat(q):
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


def trs(p, q, s):
    m = np.zeros(np.shape(p)[:-1] + (4, 4))
    m[..., :3, :3] = _quat_mat(np.asarray(q, np.float64)) * np.asarray(s, np.float64)[..., None, :]
    m[..., :3, 3] = p
    m[..., 3, 3] = 1
    return m


def decompose(m):
    """[F, 4, 4] -> pos, quat xyzw, scale, largest shear (how far the scaled axes are from orthogonal)"""
    pos = m[:, :3, 3]
    a = m[:, :3, :3]
    scl = np.linalg.norm(a, axis=1)
    r = a / scl[:, None, :]
    neg = np.linalg.det(r) < 0
    scl[neg, 0] *= -1
    r[neg, :, 0] *= -1
    shear = np.abs(np.einsum('fij,fik->fjk', r, r) - np.eye(3)).max()
    q = np.array([omo.mat2q(x.tolist()) for x in r])
    return pos, q, scl, shear


# ---------------------------------------------------------------- Ultimate
def ult_skeleton(path):
    """[(name, parent index or None, bind local 4x4)]"""
    import ssbh_data_py as s
    sk = s.skel_data.read_skel(path)
    return [(b.name, b.parent_index, np.array(b.transform, np.float64).T) for b in sk.bones]


def tracks(path):
    """{Ultimate bone: (pos [F,3], quat xyzw [F,4], scale [F,3])}, frame count"""
    import ssbh_data_py as s
    anim = s.anim_data.read_anim(path)
    frames = int(round(anim.final_frame_index)) + 1
    out = {}
    for g in anim.groups:
        if g.group_type.name != 'Transform':
            continue
        for n in g.nodes:
            for t in n.tracks:
                vals = t.values
                assert not t.compensate_scale, (path, n.name, 'compensate scale: not handled')
                idx = np.minimum(np.arange(frames), len(vals) - 1)
                out[n.name] = (np.array([v.translation for v in vals], np.float64)[idx],
                               np.array([v.rotation for v in vals], np.float64)[idx],
                               np.array([v.scale for v in vals], np.float64)[idx])
    return out, frames


def ult_world(skel, tr, frames):
    """{Ultimate bone: [F, 4, 4] world} (bones without a track: their bind)"""
    w = {}
    for name, par, bind in skel:
        loc = trs(*tr[name]) if name in tr else np.broadcast_to(bind, (frames, 4, 4))
        w[name] = w[skel[par][0]] @ loc if par is not None else np.array(loc)
    return w


# ---------------------------------------------------------------- Smash 4
def s4_skeleton(path):
    """[(name, parent index or None, hash, bind local 4x4)] (model.vbn, either endianness)"""
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    base = 28 + 76 * n
    out = []
    for i in range(n):
        o = 28 + 76 * i
        name = d[o:o + 64].split(b'\0')[0].decode()
        _t, par, h = struct.unpack(e + 'IiI', d[o + 64:o + 76])
        v = struct.unpack(e + '9f', d[base + 36 * i:base + 36 * i + 36])
        cx, sx, cy, sy, cz, sz = (np.cos(v[3]), np.sin(v[3]), np.cos(v[4]), np.sin(v[4]), np.cos(v[5]), np.sin(v[5]))
        r = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
             @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))
        m = np.eye(4)
        m[:3, :3] = r * np.array(v[6:9])
        m[:3, 3] = v[:3]
        out.append((name, par if 0 <= par < n else None, h, m))
    return out


def s4_locals(ult_skel, s4_skel, tr, frames):
    """{Smash 4 bone: (pos, quat, scale)} for every mapped bone: its Smash 4 parent's counterpart -> its counterpart,
    in Ultimate's posed skeleton; and the largest shear met"""
    w = ult_world(ult_skel, tr, frames)
    back = {v: k for k, v in ALL_BONES.items()}
    out, worst = {}, 0.0
    for name, par, _h, _b in s4_skel:
        u = back.get(name)
        if u is None:
            continue
        if par is None:
            loc = w[u]
        else:
            pu = back[s4_skel[par][0]]          # every mapped bone's Smash 4 parent is mapped (assert by KeyError)
            loc = np.linalg.inv(w[pu]) @ w[u]
        p, q, s, shear = decompose(loc)
        out[name] = (p, q, s)
        worst = max(worst, shear)
    return out, worst


def node(o, h, pos, rot, scl):
    """the bone's track (ultimate_fighter._node: interpolated or constant position / rotation / scale)"""
    import ultimate_fighter as uf
    uf._node(o, h, pos, rot, scl)


def build(ult, s4, out, log=print):
    us = ult_skeleton(os.path.join(ult, 'model', 'body', 'c00', 'model.nusktb'))
    ss = s4_skeleton(os.path.join(s4, 'model', 'body', 'c00', 'model.vbn'))
    hashes = {n: h for n, _p, h, _b in ss}
    heads = {pk: omo.Omo(omo.pac_read(os.path.join(s4, 'motion', 'refletbody', pk + '.pac'))[0][1]).head
             for pk, _l, _b in PACKS}
    for pack, slots in SLOTS.items():
        src = os.path.join(ult, 'motion', pack, 'c00')
        entries = {pk: [] for pk, _l, _b in PACKS}
        for slot, anim in sorted(slots.items()):
            tr, frames = tracks(os.path.join(src, anim + '.nuanmb'))
            loc, shear = s4_locals(us, ss, tr, frames)
            assert shear < 1e-3, (anim, 'sheared local', shear)
            for pk, label, bones in PACKS:
                o = omo.Omo(b'OMO ' + heads[pk] + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
                for s4n in bones.values():
                    node(o, hashes[s4n], *loc[s4n])
                entries[pk].append(('%s%sD00%s.omo' % (PREFIX, label, slot), o.encode()))
            log('%s/%s <- %s (%d frames)' % (pack, slot, anim, frames))
        d = os.path.join(out, pack)
        os.makedirs(d, exist_ok=True)
        for pk, _l, _b in PACKS:
            if pk != 'main':
                # the Robin copy's own part entries for the slots this copy doesn't play (Sephiroth's two holds), so
                # the part packs keep the entry set stage 1 shipped (and the game ran with)
                have = {n for n, _d in entries[pk]}
                entries[pk] += [(n, b) for n, b in omo.pac_read(os.path.join(s4, 'motion', 'refletbody', pk + '.pac'))
                                if n not in have]
            omo.pac_write(os.path.join(d, pk + '.pac'), sorted(entries[pk]))


# ---------------------------------------------------------------- checks
def check_bind(ult, s4):
    """the two bind poses, bone by bone (world position and turn)"""
    us = ult_skeleton(os.path.join(ult, 'model', 'body', 'c00', 'model.nusktb'))
    ss = s4_skeleton(os.path.join(s4, 'model', 'body', 'c00', 'model.vbn'))
    uw = ult_world(us, {}, 1)
    sw = {}
    for name, par, _h, m in ss:
        sw[name] = sw[ss[par][0]] @ m if par is not None else m
    worst = (0.0, '')
    for u, s4n in ALL_BONES.items():
        dd = np.abs(uw[u][0] - sw[s4n]).max()
        worst = max(worst, (dd, u))
    print('bind poses: largest difference %.4f (%s), %d bones' % (worst + (len(ALL_BONES),)))
    up = {n: (us[p][0] if p is not None else None) for n, p, _b in us}
    for u, s4n in ALL_BONES.items():
        chain, x = [], up[u]
        while x is not None and x not in ALL_BONES:
            chain.append(x)
            x = up[x]
        if chain:
            print('  %s: Ultimate parent chain %s -> %s (Smash 4: %s on its parent directly)' % (u, chain, x, s4n))


def check_built(ult, s4, out):
    """every frame of the built packs (main + the part packs over it) against Ultimate's forward kinematics"""
    us = ult_skeleton(os.path.join(ult, 'model', 'body', 'c00', 'model.nusktb'))
    ss = s4_skeleton(os.path.join(s4, 'model', 'body', 'c00', 'model.vbn'))
    overall = 0.0
    for pack, slots in SLOTS.items():
        packs = {pk: dict(omo.pac_read(os.path.join(out, pack, pk + '.pac'))) for pk, _l, _b in PACKS}
        for slot, anim in sorted(slots.items()):
            tr, frames = tracks(os.path.join(ult, 'motion', pack, 'c00', anim + '.nuanmb'))
            uw = ult_world(us, tr, frames)
            os_ = [omo.Omo(packs[pk]['%s%sD00%s.omo' % (PREFIX, label, slot)]) for pk, label, _b in PACKS]
            assert all(o.frames == frames for o in os_), (pack, slot, 'frame counts')
            worst = (0.0, '', 0)
            for fr in range(frames):
                sw = {}
                for name, par, h, bind in ss:
                    smp = next((o.sample(h, fr) for o in os_ if o.node(h) is not None), None)
                    loc = trs(*(np.array(x) for x in smp)) if smp else bind
                    sw[name] = sw[ss[par][0]] @ loc if par is not None else loc
                for u, s4n in ALL_BONES.items():
                    d = np.abs(uw[u][fr] - sw[s4n]).max()
                    if d > worst[0]:
                        worst = (d, u, fr)
            overall = max(overall, worst[0])
            print('%-9s %-22s %3d frames: largest world difference %.4f (%s, frame %d)' % ((pack, slot, frames) + worst))
    print('overall %.4f' % overall)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('s4')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        check_bind(a.ult, a.s4)
    if a.out:
        build(a.ult, a.s4, a.out)
        if a.check:
            check_built(a.ult, a.s4, a.out)


if __name__ == '__main__':
    main()
