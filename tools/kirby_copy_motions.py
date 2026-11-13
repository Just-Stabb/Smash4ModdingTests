#!/usr/bin/env python3
"""Kirby's Hero / Sephiroth copy body motions: Ultimate's kirby/motion/bravebody / edgebody (.nuanmb) as Smash 4
copy packs (fighter/kirby/motion/bravebody / edgebody: main.pac, kirbypt1.pac, kirbypt2.pac).
fighters/kirby/specials.md "Hero / Sephiroth copies".

  python3 tools/kirby_copy_motions.py ULT_KIRBY_DIR S4_KIRBY_DIR OUT_MOTION_DIR [--check]

ULT_KIRBY_DIR: Ultimate's kirby/ (motion/bravebody/c00, motion/edgebody/c00, model/body/c00/model.nusktb).
S4_KIRBY_DIR: Smash 4's fighter/kirby (model/body/c00/model.vbn, motion/refletbody/*.pac).

Both copies are granted as Kirby's Robin copy (kind 0x2C, the executable's copy-resource cave loads these packs in
place of refletbody for a Hero / Sephiroth player: tools/kirby_copy_new_cave.py). A copy motion's animation is found by
the CRC32 of its file name (Kirby's static motion table, 1222 hashes: fighters/kirby/specials.md "How Kirby's motions
pick animations"), so each Ultimate animation is stored under the name of the Robin copy slot that plays it
(FitKirbyRefletBodyMainD00<slot>.omo); the slots and their flags (0x2 = looping):

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

Bones: Kirby's two skeletons have the same bind pose bone for bone (Head, Neck, Bust, Hip ... at the same place and
turn: --check prints the largest difference), so Ultimate's local tracks go over as they are, mapped by name (BONES);
Smash 4's face is part animations: kirbypt1 / kirbypt2 are the Robin copy's own (same names; their face timing is
Robin's motions', an approximation).
"""
import argparse
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import omo  # noqa: E402

BONES = {
    'Trans': 'TransN', 'Rot': 'RotN', 'Hip': 'HipN', 'Waist': 'WaistN', 'Bust': 'BustN', 'Neck': 'NeckN',
    'Head': 'HeadN', 'Body': 'BodyBN', 'Mouth1': 'MouthN', 'Cheek': 'CheekN', 'Puff': 'HukumiN', 'Throw': 'ThrowN',
    'LegL': 'LLegJ', 'KneeL': 'LKneeJ', 'FootL': 'LFootJ', 'ToeL': 'LToeN',
    'LegR': 'RLegJ', 'KneeR': 'RKneeJ', 'FootR': 'RFootJ', 'ToeR': 'RToeN',
    'ClavicleL': 'LShoulderN', 'ShoulderL': 'LShoulderJ', 'ArmL': 'LArmJ', 'HandL': 'LHandN', 'HaveL': 'LHaveN',
    'ClavicleR': 'RShoulderN', 'ShoulderR': 'RShoulderJ', 'ArmR': 'RArmJ', 'HandR': 'RHandN', 'HaveR': 'RHaveN',
}
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


def _quat_mat(q):
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], 1)


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
                idx = np.minimum(np.arange(frames), len(vals) - 1)
                out[n.name] = (np.array([v.translation for v in vals], np.float64)[idx],
                               np.array([v.rotation for v in vals], np.float64)[idx],
                               np.array([v.scale for v in vals], np.float64)[idx])
    return out, frames


def node(o, h, pos, rot, scl):
    """the bone's track (ultimate_fighter._node: interpolated or constant position / rotation / scale)"""
    import ultimate_fighter as uf
    uf._node(o, h, pos, rot, scl)


def vbn_hashes(path):
    return {n: h for n, _p, h in omo.vbn_read(path)}


def build(ult, s4, out, log=print):
    hashes = vbn_hashes(os.path.join(s4, 'model', 'body', 'c00', 'model.vbn'))
    ref = omo.pac_read(os.path.join(s4, 'motion', 'refletbody', 'main.pac'))
    head = omo.Omo(ref[0][1]).head
    for pack, slots in SLOTS.items():
        src = os.path.join(ult, 'motion', pack, 'c00')
        entries = []
        for slot, anim in sorted(slots.items()):
            tr, frames = tracks(os.path.join(src, anim + '.nuanmb'))
            o = omo.Omo(b'OMO ' + head + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
            for u, s4n in BONES.items():
                if u in tr and s4n in hashes:
                    p, q, sc = tr[u]
                    node(o, hashes[s4n], p, q, sc)
            name = '%sMainD00%s.omo' % (PREFIX, slot)
            entries.append((name, o.encode()))
            log('%s/%s <- %s (%d frames, %d bones)' % (pack, name, anim, frames, len(o.nodes)))
        d = os.path.join(out, pack)
        os.makedirs(d, exist_ok=True)
        omo.pac_write(os.path.join(d, 'main.pac'), sorted(entries))
        for pt in ('kirbypt1.pac', 'kirbypt2.pac'):
            shutil.copy(os.path.join(s4, 'motion', 'refletbody', pt), os.path.join(d, pt))


def check(ult, s4):
    """the two bind poses, bone by bone (world position and turn)"""
    import ssbh_data_py as s
    sk = s.skel_data.read_skel(os.path.join(ult, 'model', 'body', 'c00', 'model.nusktb'))
    uw = {b.name: np.array(sk.calculate_world_transform(b)).T for b in sk.bones}
    d = open(os.path.join(s4, 'model', 'body', 'c00', 'model.vbn'), 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    names, par = [], []
    for i in range(n):
        o = 28 + 76 * i
        names.append(d[o:o + 64].split(b'\0')[0].decode())
        par.append(struct.unpack(e + 'IiI', d[o + 64:o + 76])[1])
    base = 28 + 76 * n
    sw = {}
    for i in range(n):
        v = struct.unpack(e + '9f', d[base + 36 * i:base + 36 * i + 36])
        rx, ry, rz = v[3:6]
        cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
        r = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
             @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))
        m = np.eye(4)
        m[:3, :3] = r * np.array(v[6:9])
        m[:3, 3] = v[:3]
        sw[names[i]] = sw[names[par[i]]] @ m if 0 <= par[i] < n else m
    worst = (0.0, '')
    for u, s4n in BONES.items():
        dd = np.abs(uw[u] - sw[s4n]).max()
        print('%-10s %-12s %.4f' % (u, s4n, dd))
        worst = max(worst, (dd, u))
    print('largest difference %.4f (%s)' % worst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ult')
    ap.add_argument('s4')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        check(a.ult, a.s4)
    if a.out:
        build(a.ult, a.s4, a.out)


if __name__ == '__main__':
    main()
