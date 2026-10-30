#!/usr/bin/env python3
"""A ported fighter's collision shapes from Ultimate's param/vl.prc into its fighter_param_vl: the
hurtboxes (hit_data -> group 5) with their hit points (virtual_node_data_hit -> group 10: joint ids
11000 + n, one per hurtbox, bone + offset + rotation in degrees), the ground box (ECB) points
(map_coll_data -> group 4) and the ledge-grab boxes (cliff_hang_data -> group 7). The rest of the
file is kept byte for byte.

  python3 tools/ultimate_vl_shapes.py VL_IN VL_OUT VL_PRC MODEL_DIR [--json OUT.json]

MODEL_DIR: the converted model/body/c00 (model.vbn + model.jtb): Ultimate's bones keep their local
axes in the conversion (tools/ultimate_fighter.py Skeleton), so offsets carry over; a bone is
written by its joint id (model.jtb table 0), as the base's shapes are.
- hurtboxes: node, offset1 / offset2 (capsule ends), size (radius); part: body / head 0,
  etc (arms) 1, body_legs 3 (the base's: Robin's forearms 1, knees 3); height low / center / high
  0 / 1 / 2; pool 2.
- ECB: node + offset (Ultimate's list is the same kind of point list: Hero's head (-0.5 x),
  shoulders, knees, hip).
- ledge boxes: Ultimate's box p1 (front, top) / p2 (back, bottom) -> Smash 4's (x, y, w, h) = (0,
  bottom, front reach, height); the reach behind is w x fighter_param_common 0x75 (0.6). The
  tumbling box (entry 1) as every vanilla fighter's: (0, 4, 0.6 w, 0.6 h). Entries past 1 (tether
  boxes) are kept.
"""
import argparse
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import prc  # noqa: E402
import vl_shapes  # noqa: E402

KEYS = ['hit_data', 'map_coll_data', 'cliff_hang_data', 'virtual_node_data_hit', 'node_parent', 'x', 'y', 'z',
        'rot_x', 'rot_y', 'rot_z', 'node_id', 'node', 'size', 'part', 'height',
        'offset_x', 'offset_y', 'offset_z', 'p1_x', 'p1_y', 'p2_x', 'p2_y'] + \
       ['offset%d_%s' % (i, a) for i in (1, 2) for a in 'xyz'] + \
       ['collision_part_' + p for p in ('body', 'head', 'body_legs', 'etc', 'legs', 'arm')] + \
       ['hit_height_' + h for h in ('low', 'center', 'high')]
PART = {'collision_part_body': 0, 'collision_part_head': 0, 'collision_part_etc': 1, 'collision_part_arm': 1,
        'collision_part_body_legs': 3, 'collision_part_legs': 3}
HEIGHT = {'hit_height_low': 0, 'hit_height_center': 1, 'hit_height_high': 2}
TUMBLE = 0.6
HITPOINTS, HITPOINT_KEYS = 10, ('bone', 'x', 'y', 'z', 'rx', 'ry', 'rz')


def hash40(s):
    return zlib.crc32(s.encode()) | (len(s) << 32)


def joint_ids(model_dir):
    """{Ultimate bone name hash40: joint id} for the bones in model.jtb table 0"""
    import ultimate_fighter as U
    names, tables = vl_shapes.load_bones(model_dir)
    to_ult = {s: u for s, u in U.STANDARD}
    out = {}
    # table 1 (1000 + k, as ACMD: tools/vl_shapes.py): the port's own joints (Squirtle's tail, --joints)
    for k, idx in enumerate(tables[1] if len(tables) > 1 else []):
        if 0 <= idx < len(names):
            out.setdefault(hash40(to_ult.get(names[idx], names[idx]).lower()), 1000 + k)
    for k, idx in enumerate(tables[0]):
        if 0 <= idx < len(names):
            out[hash40(to_ult.get(names[idx], names[idx]).lower())] = k + 1
    return out


def ultimate_shapes(vl_prc, model_dir):
    import ultimate_fighter as U
    labels = {hash40(k): k for k in KEYS}
    names, _t = vl_shapes.load_bones(model_dir)
    labels.update({hash40(u.lower()): u.lower() for _s, u in U.STANDARD})
    labels.update({hash40(n.lower()): n.lower() for n in names})
    root = prc.Prc(open(vl_prc, 'rb').read(), labels).root
    ids = joint_ids(model_dir)

    def jid(node):
        h = hash40(node[1])
        assert h in ids, 'bone %s is not in the joint table' % node[1]
        return ids[h]
    hurt = [dict(x1=e['offset1_x'], y1=e['offset1_y'], z1=e['offset1_z'], x2=e['offset2_x'], y2=e['offset2_y'],
                 z2=e['offset2_z'], radius=e['size'], bone=jid(e['node_id']), part=PART[e['part'][1]],
                 height=HEIGHT[e['height'][1]], unk=0, pool=2, ult_node=e['node_id'][1])
            for e in root['hit_data']]
    ecb = [dict(bone=jid(e['node']), x=e['offset_x'], y=e['offset_y'], z=e['offset_z'], ult_node=e['node'][1])
           for e in root['map_coll_data']]
    c = root['cliff_hang_data'][0]
    w, h = c['p1_x'], c['p1_y'] - c['p2_y']
    ledge = [dict(x=0.0, y=c['p2_y'], w=w, h=h), dict(x=0.0, y=4.0, w=TUMBLE * w, h=TUMBLE * h)]
    points = [dict(bone=jid(e['node_parent']), x=e['x'], y=e['y'], z=e['z'], rx=e['rot_x'], ry=e['rot_y'],
                   rz=e['rot_z'], ult_node=e['node_parent'][1]) for e in root.get('virtual_node_data_hit', [])]
    return dict(hurtboxes=hurt, ecb_bones=ecb, ledge_boxes=ledge, hit_points=points)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vl_in')
    ap.add_argument('vl_out')
    ap.add_argument('vl_prc')
    ap.add_argument('model_dir')
    ap.add_argument('--json', help='write the shapes as vl_shapes.py --json does')
    a = ap.parse_args()
    header, groups = vl_shapes.parse(open(a.vl_in, 'rb').read())
    old = vl_shapes.shapes(groups)
    new = ultimate_shapes(a.vl_prc, a.model_dir)
    new['ledge_boxes'] += old['ledge_boxes'][2:]          # tether boxes stay
    strip = {k: [{kk: vv for kk, vv in e.items() if kk != 'ult_node'} for e in v] for k, v in new.items()}
    old_points = vl_shapes.entries(groups[HITPOINTS]) or []
    if strip['hit_points']:
        vl_shapes.set_entries(groups[HITPOINTS], strip['hit_points'], HITPOINT_KEYS, old_points[0])
    vl_shapes.apply(groups, {k: v for k, v in strip.items() if k != 'hit_points'})
    open(a.vl_out, 'wb').write(vl_shapes.build(header, groups))
    if a.json:
        json.dump(new, open(a.json, 'w'), indent=1)
    for k in ('hurtboxes', 'ecb_bones', 'ledge_boxes'):
        print('%s: %d -> %d' % (k, len(old[k]), len(new[k])))
    print('hit points (group 10): %d -> %d' % (len(old_points), len(new['hit_points'])))


if __name__ == '__main__':
    main()
