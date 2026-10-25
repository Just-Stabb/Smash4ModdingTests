#!/usr/bin/env python3
"""A ported fighter's motion blends from Ultimate: fighter_param_vl group 1 byte 1 of every common
motion = the Ultimate motion_list entry's blend (the frames the game interpolates into the motion),
the entry found by its game script (game_<the motion's script name>); where Ultimate's is 0 (its
status code passes one) the base's stays. The base's values were for the
base's animations: Robin's Run 0 (his run starts in his dash's last pose), Ultimate's 3, so the
ports' dash cut into the run.

  python3 tools/ultimate_vl_blend.py VL_IN VL_OUT MOTION_LIST [--vl-kind zelda|reflet|pit|koopa]

Byte 1 in vanilla files: Wait1 / walks 6, brakes 3, DamageFall 10, the rest mostly 0, as Ultimate's
blend values for the same motions (docs/params/fighter_param_vl.md, group 1).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def apply_blends(vf, motion_list, log=print):
    """vf: a loaded fighter_param_vl; motion_list: ultimate_acmd.read_motion_list's entries. Sets
    byte 1 of each common motion found; returns [(index, name, old, new)] of the ones changed"""
    import fighter_param_vl as V
    import mtable
    from ultimate_acmd import hash40
    by = {}
    for e in motion_list:
        for h in (e['game'],) + e['scripts']:
            by.setdefault(h, e)
    changed = []
    for i, n in enumerate(mtable.COMMON):
        s = n.strip('?').lower()
        if not s or s == '-':
            continue
        e = by.get(hash40('game_' + s))
        if e is None or e['blend'] == 0:
            # 0: Ultimate's status code gives the blend itself (its cliff / down waits: Smash 4's 10)
            continue
        (_p, t), = V.find(vf, 'm0[%d].1' % i, '0', {})
        if t.value != e['blend']:
            changed.append((i, s, t.value, e['blend']))
            t.set(e['blend'])
    for i, s, a, b in changed:
        log('  0x%03X %-16s blend %d -> %d' % (i, s, a, b))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vl_in')
    ap.add_argument('vl_out')
    ap.add_argument('motion_list')
    ap.add_argument('--vl-kind', default='zelda', help="the vl file's layout (the base fighter)")
    a = ap.parse_args()
    import fighter_param_vl as V
    from ultimate_acmd import read_motion_list
    vf = V.load(a.vl_in, a.vl_kind)
    apply_blends(vf, read_motion_list(a.motion_list))
    open(a.vl_out, 'wb').write(vf.build())


if __name__ == '__main__':
    main()
