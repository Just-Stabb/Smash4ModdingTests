#!/usr/bin/env python3
"""Shadow Flare's orbit around each fighter, from Ultimate's fighter_param.prc, for Sephiroth's flare1.c.

  python3 tools/edge_flare_targets.py FIGHTER_PARAM_PRC LABELS_CSV VBN_ROOT [--vbn NAME=PATH ...]
          [--write fighters/edge/weapons/flare1.c]

Ultimate (edge_flaredummy, docs: fighters/edge/specials.md "Side special") puts the orb ring on the
target's joint `edge_flare_node` (`waist` for all but ROB `waist3` and Giga Bowser, none) plus
(`edge_flare_offset_x`, `_y`, `_z`) in that joint's own axes, radius `edge_flare_radius` x the target's
PostureModule scale (1 but for size changes: not followed here). These per-fighter values keep the ring
just outside the fighter's body, so the orbiting orbs (7 damage, rehit 45) don't hit their own target.

Smash 4's MSC can't read another fighter's joints, so the centre is taken from the rest pose: the joint's
position in the Smash 4 model (VBN_ROOT/fighter/NAME/model/body/c00/model.vbn; --vbn for the ports'
own models) with the offset in its axes, times the fighter's model size (fighter_param "Character Size
Multiplier", reference/fighter_param_attributes.csv; a port keeps its base's), as height above and
distance in front of the fighter's position (flare1.c adds it to the slot position, by its facing).

--write replaces the block between the `flare targets` markers in flare1.c with the table
(fl_target_shape(kind): fl_rad, fl_up, fl_fwd).
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fbx_anim as FA  # noqa: E402
import fighter_param as FP  # noqa: E402
import omo as O  # noqa: E402
import prc  # noqa: E402

# Smash 4 fighters with no row of their own in Ultimate -> the row used
# (Giga Bowser: Ultimate's row has radius 0 and no joint, Shadow Flare never meets him there: Bowser's, on
# Giga Bowser's own model and size, the radius x his waist height / Bowser's)
ULT_NAME = {'miienemyf': 'miifighter', 'miienemys': 'miiswordsman', 'miienemyg': 'miigunner',
            'warioman': 'wario', 'littlemacg': 'littlemac', 'lucariom': 'lucario', 'supamario': 'mario',
            'lizardon': 'plizardon', 'koopag': 'koopa'}
BEGIN = '// ---- flare targets (generated: tools/edge_flare_targets.py) ----'
END = '// ---- end of flare targets ----'


def sizes():
    """{Smash 4 kind: model size multiplier} (fighter_param 0x0300002C, column 46 of the reference csv)"""
    rows = list(csv.reader(open(os.path.join(HERE, '..', 'reference', 'fighter_param_attributes.csv'))))
    assert 'Size' in rows[2][46], rows[2][46]
    out = {}
    for r in rows[3:]:
        if len(r) > 46 and r[1].strip().isdigit():
            out[int(r[1])] = float(r[46])
    return out


def joint_world(vbn, joint):
    """the joint's rest-pose 4x4 in model space (scale removed), or the identity for no joint"""
    if joint is None:
        return np.eye(4)
    loc = FA.vbn_rest(vbn)
    bones = O.vbn_read(vbn)
    names = [n for n, _p, _h in bones]
    par = {n: p for n, p, _h in bones}
    m = loc[joint]
    p = par[joint]
    while 0 <= p < len(names):
        m = loc[names[p]] @ m
        p = par[names[p]]
    r = m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
    out = np.eye(4)
    out[:3, :3], out[:3, 3] = r, m[:3, 3]
    return out


def table(a):
    labels = prc.load_labels(a.labels)
    rows = {e['fighter_kind'][1].replace('fighter_kind_', ''): e
            for e in prc.Prc(open(a.prc, 'rb').read(), labels).root['fighter_param_table']}
    size = sizes()
    extra = {k['name']: (int(k['kind'], 16), k['base'])
             for k in json.load(open(os.path.join(HERE, 'extra_kinds.json')))['kinds']}
    own = dict(v.split('=', 1) for v in a.vbn)
    out = []
    kinds = [(i, n, i) for i, n in enumerate(FP.KINDS)] + [(k, n, FP.KINDS.index(b)) for n, (k, b) in extra.items()]
    for kind, name, size_of in kinds:
        e = rows.get(ULT_NAME.get(name, name))
        vbn = own.get(name, os.path.join(a.vbn_root, 'fighter', name, 'model', 'body', 'c00', 'model.vbn'))
        if e is None or not os.path.exists(vbn):
            out.append((kind, name, None, 'no %s' % ('Ultimate row' if e is None else 'model')))
            continue
        node = e['edge_flare_node'][1]
        joint = None if node in ('0', '') else node[0].upper() + node[1:] + 'N'
        if joint and joint not in [n for n, _p, _h in O.vbn_read(vbn)]:
            out.append((kind, name, None, 'no joint %s' % joint))
            continue
        off = np.array([e['edge_flare_offset_x'], e['edge_flare_offset_y'], e['edge_flare_offset_z'], 1.0])
        c = joint_world(vbn, joint) @ off * size[size_of]
        r = float(e['edge_flare_radius'])
        if name == 'koopag':        # Bowser's radius grown with the waist's height (Giga Bowser / Bowser)
            r *= c[1] / next(v[1] for k, n, v, _s in out if n == 'koopa')
        out.append((kind, name, (r, float(c[1]), float(c[2])),
                    '%s %s' % (ULT_NAME.get(name, name), joint or 'position')))
    return out


def c_block(rows):
    lines = [BEGIN,
             '// fl_rad: Ultimate\'s edge_flare_radius; fl_up / fl_fwd: the ring centre above / in front of the fighter\'s',
             '// position (its edge_flare_node + offsets on the Smash 4 model\'s rest pose, x its size). Unknown kinds',
             '// keep 14 / 9 / 0.',
             'void fl_target_shape(int k)',
             '{',
             '    fl_rad = 14.0f;',
             '    fl_up = 9.0f;',
             '    fl_fwd = 0;']
    for kind, name, v, src in rows:
        if v is None:
            lines.append('    // 0x%X %s: %s' % (kind, name, src))
            continue
        lines.append('    if (k == 0x%x) { fl_rad = %.2ff; fl_up = %.2ff; fl_fwd = %.2ff; }   // %s (%s)'
                     % (kind, v[0], v[1], v[2], name, src))
    lines += ['}', END]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('prc')
    ap.add_argument('labels')
    ap.add_argument('vbn_root')
    ap.add_argument('--vbn', action='append', default=[])
    ap.add_argument('--write')
    a = ap.parse_args()
    block = c_block(table(a))
    if not a.write:
        print(block)
        return
    s = open(a.write).read()
    i, j = s.index(BEGIN), s.index(END) + len(END)
    open(a.write, 'w').write(s[:i] + block + s[j:])
    print('%s: %d kinds' % (a.write, block.count('if (k ==')))


if __name__ == '__main__':
    main()
