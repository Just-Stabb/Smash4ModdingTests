#!/usr/bin/env python3
"""Effects on a bone keep their angles through Smash 4's facing flip: the angles go into a turned copy
of the effect set, and the script sends 0.

  python3 tools/effect_variants.py scan EFFECT_BIN IDS_JSON VARIANTS_JSON
  python3 tools/vfxb_to_ptcl.py ... --variants VARIANTS_JSON         (adds "name@rx,ry,rz" ids)
  python3 tools/effect_variants.py apply EFFECT_BIN IDS_JSON OUT_EFFECT_BIN

Smash 4 mirrors a followed / placed effect's angles for one facing direction (seen on Sephiroth:
his blade glow, `edge_sword_light3` on joint 24 at (0, 180, -90), lies along the sword facing left
and points back from the hilt facing right, test 48). The flip changes the sign of the bone frame's
X in the effect's turn, so no angles put a mesh along the blade (his joint's +X) for both facings;
vanilla sword effects avoid it by lying along an axis the flip keeps. Angles of 0 are kept by any
such flip, so the turn goes into the effect's emitters instead (`vfxb_to_ptcl.py --variants`:
each emitter's transform turned by R = Rz Ry Rx, the script's own order).

scan: every effect command (Graphic, Bone, X, Y, Z, XRot, YRot, ZRot, ...) in EFFECT_BIN naming one
of the fighter's own effects (IDS_JSON) on a bone other than 0 with a non-zero turn ->
[{"effect", "rot"}]. apply: those commands get the variant's id ("name@rx,ry,rz" in IDS_JSON) and
angles 0 (left as they are when the variant is missing). Effects on bone 0 (his top: the slash arcs)
look right in both facings and are left alone.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

ROT = 5          # XRot, YRot, ZRot follow Graphic, Bone, X, Y, Z


def effect_commands():
    return {i for i, inf in acmd.INFO.items()
            if inf.get('syntax', [])[:8] == ['Graphic', 'Bone', 'X', 'Y', 'Z', 'XRot', 'YRot', 'ZRot']}


def variant_key(name, rot):
    return '%s@%s' % (name, ','.join('%g' % round(float(v), 2) for v in rot))


def turned(f, ids):
    """(command, effect name, rotation) for each effect command to move to a variant"""
    by_id = {}
    for k, v in ids.items():
        if not k.startswith('_') and '@' not in k and isinstance(v, str):
            by_id.setdefault(int(v, 0), k)
    kinds = effect_commands()
    for script in f.scripts.values():
        for c in script:
            if c.ident not in kinds or len(c.params) < ROT + 3:
                continue
            name = by_id.get(int(c.params[0]) & 0xFFFFFFFF)
            rot = [float(v) for v in c.params[ROT:ROT + 3]]
            if name and int(c.params[1]) != 0 and any(abs(v) > 1e-3 for v in rot):
                yield c, name, rot


def main():
    if len(sys.argv) != 5 or sys.argv[1] not in ('scan', 'apply'):
        sys.exit(__doc__)
    f = acmd.ACMDFile.load(sys.argv[2])
    ids = json.load(open(sys.argv[3]))
    if sys.argv[1] == 'scan':
        out = {}
        for _c, name, rot in turned(f, ids):
            out[variant_key(name, rot)] = {'effect': name, 'rot': [round(v, 2) for v in rot]}
        json.dump(list(out.values()), open(sys.argv[4], 'w'), indent=1)
        print('%d variants: %s' % (len(out), ', '.join(sorted(out))))
        return
    n, missing, moved = 0, set(), {}
    for c, name, rot in list(turned(f, ids)):
        key = variant_key(name, rot)
        if key not in ids:
            missing.add(key)
            continue
        moved.setdefault(id(c), (int(c.params[0]) & 0xFFFFFFFF, int(ids[key], 0)))
        c.params[0] = int(ids[key], 0)
        c.params[ROT:ROT + 3] = [0.0, 0.0, 0.0]
        n += 1
    # the other commands naming a moved effect in the same script (Terminate_Graphic_Effect,
    # EFFECT_DETACH_KIND...: by id) name its variants too (down air turns its frame-13 glow off at 17)
    kinds, extra = effect_commands(), 0
    for key in list(f.scripts):
        script = f.scripts[key]
        to = {}
        for c in script:
            if id(c) in moved:
                old, new = moved[id(c)]
                to.setdefault(old, set()).add(new)
        if not to:
            continue
        out = []
        for c in script:
            out.append(c)
            if c.ident not in kinds and c.params and isinstance(c.params[0], int) and c.params[0] in to:
                for new in sorted(to[c.params[0]]):
                    out.append(acmd.Command(c.ident, [new] + list(c.params[1:])))
                    extra += 1
        f.scripts[key] = out
    f.save(sys.argv[4])
    print('%d commands naming a moved effect copied for its variants' % extra)
    print('%d commands moved to turned variants; no variant: %s' % (n, ', '.join(sorted(missing)) or 'none'))


if __name__ == '__main__':
    main()
