#!/usr/bin/env python3
"""A Blender FBX animation of a Smash 4 fighter's armature -> that motion's .omo in each motion pac.

  python3 tools/fbx_anim.py ANIM.fbx MODEL.vbn PACDIR MOTION OUTDIR [--check]

PACDIR: the fighter's motion/body folder (main.pac and its part pacs: Bowser's koopapt1 / koopapt2 /
lhand / rhand). MOTION: the motion's name as in the omo names (Attack11 -> FitKoopaBodyMainC00Attack11.omo,
FitKoopaBodyLhandC00Attack11.omo...). Every pac holding that motion gets it rebuilt from the FBX with
the same bones (the vanilla split: main = the joint table's 26 in vbn order, the others theirs), at
the FBX's length; written to OUTDIR/<pac>.pac (everything else in the pac kept), and each new omo also
to OUTDIR/omo/. --check: the largest difference from the pac's current motion on the frames both
have (an unedited stretch should be ~0).

A part pac (not main) whose bones all stay at the model's rest pose for the whole FBX keeps its
current motion: Blender imports only main.pac's motion, so bones nobody animated sit at rest there
(Bowser's fists, toes and tail would open / straighten); --all writes those too.

The FBX (binary, 7.x: tools/fbx_bin.py; the Blender FBX exporter, a Smash 4 armature imported into
Blender): bone channels Lcl Translation / Rotation (Euler XYZ, degrees) / Scaling, linear keys at 60
fps. Blender turned each bone's local axes 90 degrees about Z (game (x, y, z) = FBX (y, -x, z)): a
bone's game local = C^-1 L C; the root (TransN) also carries the scene's axis change, its rest
transform (identity in the game): game local = (L_rest C)^-1 L C. Checked on Bowser's Attack11: the
user's edit matches vanilla's frames 0-5 to 0.003. Bones Blender added (*_end) are skipped.
"""
import bisect
import math
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbx_bin as F  # noqa: E402
import omo as O  # noqa: E402

TICKS = 46186158000          # FBX time units per second
FPS = 60.0
C = np.eye(4)
C[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]


def load(path):
    """({bone: {parent, rest, sample(frame)}}, frame count)"""
    _ver, nodes = F.load(path)
    objs = F.find(nodes, 'Objects')[0][2]
    byid = {n[1][0]: n for n in objs}
    conns = F.find(nodes, 'Connections')[0][2]
    models = {n[1][0]: n for n in objs if n[0] == 'Model' and n[1][2] == b'LimbNode'}
    name = {i: n[1][1].split(b'\x00')[0].decode() for i, n in models.items()}
    kind = {i: n[0] for i, n in byid.items()}
    parent, cnode, curves = {}, {}, {}
    for c in conns:
        if c[0] != 'C':
            continue
        how, a, b = c[1][0], c[1][1], c[1][2]
        if how == b'OO' and a in models and b in models:
            parent[a] = b
        elif how == b'OP' and b in models and kind.get(a) == 'AnimationCurveNode':
            cnode.setdefault(b, {})[c[1][3].decode()] = a
        elif how == b'OP' and kind.get(b) == 'AnimationCurveNode' and kind.get(a) == 'AnimationCurve':
            curves.setdefault(b, {})[c[1][3].decode()] = a

    def curve(cid):
        d = {k[0]: k[1] for k in byid[cid][2]}
        flags = set(d.get('KeyAttrFlags', [[0x4]])[0])
        assert all(f & 0xE == 0x4 for f in flags), 'non-linear keys (KeyAttrFlags %s)' % flags
        return [t / TICKS * FPS for t in d['KeyTime'][0]], d['KeyValueFloat'][0]

    def value(cv, f):
        ts, vs = cv
        if f <= ts[0]:
            return vs[0]
        if f >= ts[-1]:
            return vs[-1]
        i = bisect.bisect_right(ts, f) - 1
        return vs[i] + (vs[i + 1] - vs[i]) * (f - ts[i]) / (ts[i + 1] - ts[i])

    stack = [n for n in objs if n[0] == 'AnimationStack'][0]
    frames = round(F.props70(stack)['LocalStop'][0] / TICKS * FPS) + 1
    bones = {}
    for mid, m in models.items():
        p = F.props70(m)
        assert not any(k in p for k in ('PreRotation', 'PostRotation', 'RotationOffset', 'RotationPivot')), name[mid]
        assert p.get('RotationOrder', [0])[0] == 0, name[mid]
        rest = [p.get('Lcl Translation', [0, 0, 0]), p.get('Lcl Rotation', [0, 0, 0]), p.get('Lcl Scaling', [1, 1, 1])]
        ch = {prop: {ax: curve(cid) for ax, cid in curves.get(cn, {}).items()} for prop, cn in cnode.get(mid, {}).items()}

        def sample(f, rest=rest, ch=ch):
            out = []
            for prop, base in zip(('Lcl Translation', 'Lcl Rotation', 'Lcl Scaling'), rest):
                out.append([value(ch[prop][ax], f) if ax in ch.get(prop, {}) else base[k]
                            for k, ax in enumerate(('d|X', 'd|Y', 'd|Z'))])
            return out
        bones[name[mid]] = dict(parent=name.get(parent.get(mid)), rest=rest, sample=sample)
    return bones, frames


def vbn_rest(path):
    """{bone: rest local 4x4} from model.vbn (translation, Euler XYZ radians, scale)"""
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    off = 28 + 76 * n
    out = {}
    for i, (name, _p, _h) in enumerate(O.vbn_read(path)):
        v = struct.unpack(e + '9f', d[off + 36 * i:off + 36 * i + 36])
        out[name] = _matrix(v[0:3], [math.degrees(x) for x in v[3:6]], v[6:9])
    return out


def _matrix(t, r, s):
    x, y, z = (math.radians(a) for a in r)
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    m = np.eye(4)
    m[:3, :3] = rz @ ry @ rx @ np.diag(s)
    m[:3, 3] = t
    return m


def game_locals(bones, f):
    """{bone: its game-space local 4x4} at frame f"""
    root = np.linalg.inv(_matrix(*bones['TransN']['rest']) @ C)
    ic = np.linalg.inv(C)
    return {n: (root if b['parent'] is None else ic) @ _matrix(*b['sample'](f)) @ C for n, b in bones.items()}


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) != 5:
        sys.exit(__doc__)
    fbx, vbn, pacdir, motion, out = a
    check = '--check' in sys.argv
    every = '--all' in sys.argv
    import ultimate_fighter as U
    bones, frames = load(fbx)
    locs = [game_locals(bones, f) for f in range(frames)]
    vb = O.vbn_read(vbn)
    byh = {h: n for n, _p, h in vb}
    rest = vbn_rest(vbn)
    os.makedirs(os.path.join(out, 'omo'), exist_ok=True)
    for pac in sorted(p for p in os.listdir(pacdir) if p.endswith('.pac')):
        ents = O.pac_read(os.path.join(pacdir, pac))
        hit = [i for i, (n, _d) in enumerate(ents) if re.search(r'[A-Z]\d\d%s\.omo$' % re.escape(motion), n)]
        if not hit:
            continue
        for i in hit:
            name, data = ents[i]
            old = O.Omo(data)
            names = [byh[nd[1]] for nd in old.nodes]
            if not every and pac != 'main.pac' and all(np.abs(lc[b] - rest[b]).max() < 1e-4 for lc in locs for b in names):
                print('  %s: kept (its bones stay at rest in the FBX)' % name)
                continue
            new = O.Omo(data)
            new.nodes, new.frames = [], frames
            for nd in old.nodes:
                bone = byh[nd[1]]
                ms = np.array([locs[f][bone] for f in range(frames)])
                t = ms[:, :3, 3]
                sc = np.linalg.norm(ms[:, :3, :3], axis=1)
                q = U._mat_quat(ms[:, :3, :3] / sc[:, None, :])
                U._node(new, nd[1], t, q, sc)
            blob = new.encode()
            if check:
                chk = O.Omo(blob)
                worst = max((np.abs(np.array(O.trs(*chk.sample(nd[1], f))) - np.array(O.trs(*old.sample(nd[1], f)))).max(), f)
                            for nd in old.nodes for f in range(min(frames, old.frames)))
                print('  %s: %d -> %d frames, %d bones; largest difference from the current on frames both have: '
                      '%.3f (frame %d)' % (name, old.frames, frames, len(old.nodes), worst[0], worst[1]))
            ents[i] = (name, blob)
            open(os.path.join(out, 'omo', name), 'wb').write(blob)
        O.pac_write(os.path.join(out, pac), ents)
        print('%s: %s' % (pac, ', '.join(ents[i][0] for i in hit)))


if __name__ == '__main__':
    main()
