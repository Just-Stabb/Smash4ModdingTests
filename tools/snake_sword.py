#!/usr/bin/env python3
"""The extending sword of Sephiroth's held forward air (fighters/edge/snake_fair.md): bones and meshes added to
his model by `ultimate_fighter.py model --snake` (SPEC below, or a JSON file of the same keys).

  - EdgeBladeL: a bone at SwordL1 (identity) carrying the sword's blade (the hilt stays on SwordL1), so the
    MSC can fold the real blade away (ModelModule scale 0) while the extended one is out.
  - EdgeSnake01..NN: the straight runs of the extended blade, one bone each under TransN, each with a slice of
    the blade (one ring-to-ring section, straightened) one unit long along the bone's +X: the MSC places a
    bone at its run's start (ModelModule 7), turns it along the run (1) and stretches its X to the run's
    length (0).
  - EdgeSnakeTip: the blade's point (from the tip ring on), also one unit long along +X.

Every new bone's bind is the identity under its parent, so the MSC's joint ops mean the same whether they
replace the bind's transform or add to it. The pieces are drawn twice, the second copy turned 90 degrees
about the blade (a "+" section), so a run looks the same width whichever way it is turned. They hang from
the sword's own mesh slot (the same material, its visibility).

Merging bones for room (the 136-bone budget) is the converter's own `--max-bones`, less these bones.
"""
import zlib

import numpy as np

SPEC = {
    'meshes': ['edge_swordL_VIS_O_OBJShape'],   # the sword's meshes (rigid on `bone`)
    'bone': 'SwordL1',
    'root': 'TransN',
    'blade_bone': 'EdgeBladeL',
    'blade_min_x': 5.0,          # a connected piece reaching past this along the sword's X is blade
    'body_rings': [11.8, 14.0],  # the ring-to-ring section used for the runs
    'tip_ring': 22.8,            # the point: from this ring on
    # test 79 drew the runs and the point as bones of his own posed from MSC (13 runs + the point): too many
    # joint overrides for the game (fighters/edge/README.md test 80, port_check C6). Since test 82 they are
    # articles (edge_snake_articles.py, article_pieces below) and his model only gets the blade's bone
    'segments': 0,
    'segment_name': 'EdgeSnake%02d',
    'tip_name': None,
    # never folded to make room (their motions show: the skirt's sides); finger tips and lips go instead
    'protect_prefixes': ['Skirt', 'S_Skirt'],
}


def bone_names(spec=SPEC):
    return ([spec['blade_bone']] + [spec['segment_name'] % (k + 1) for k in range(spec['segments'])]
            + ([spec['tip_name']] if spec.get('tip_name') else []))


def _components(tri, n):
    """connected pieces of a triangle list: a label per vertex"""
    par = list(range(n))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a, b, c in tri:
        for u, v in ((a, b), (b, c)):
            ru, rv = find(u), find(v)
            if ru != rv:
                par[ru] = rv
    return np.array([find(v) for v in range(n)])


def _sub(part, tri, **over):
    """a part of `part` made of the triangles tri (vertices re-indexed)"""
    used = np.unique(tri)
    remap = -np.ones(part['n'], np.int64)
    remap[used] = np.arange(len(used))
    q = dict(part)
    q.update(n=len(used), pos=part['pos'][used], nrm=part['nrm'][used],
             tan=None if part['tan'] is None else part['tan'][used],
             uvs={k: v[used] for k, v in part['uvs'].items()}, idx=remap[tri].reshape(-1), infl=[])
    q.update(over)
    return q


def _ring(pos, x, tol=0.06):
    return np.abs(pos[:, 0] - x) < tol


def _crossed(q):
    """q and its copy turned 90 degrees about X (y, z) -> (-z, y)"""
    rot = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    n = q['n']
    pos = np.vstack([q['pos'], q['pos'] @ rot.T])
    nrm = np.vstack([q['nrm'], q['nrm'] @ rot.T])
    tan = None
    if q['tan'] is not None:
        t2 = q['tan'].copy()
        t2[:, :3] = q['tan'][:, :3] @ rot.T
        tan = np.vstack([q['tan'], t2])
    idx = np.concatenate([q['idx'], q['idx'] + n])
    out = dict(q)
    out.update(n=2 * n, pos=pos, nrm=nrm, tan=tan, uvs={k: np.vstack([v, v]) for k, v in q['uvs'].items()}, idx=idx)
    return out


def pieces(part, spec=SPEC):
    """(hilt part, blade part, run part, tip part) of one sword mesh part; the run and tip in their unit frame"""
    pos = part['pos']
    tri = part['idx'].reshape(-1, 3)
    lab = _components(tri, part['n'])
    blade_lab = {l for l in np.unique(lab) if pos[lab == l, 0].max() > spec['blade_min_x']}
    is_blade = np.array([lab[t[0]] in blade_lab for t in tri])
    hilt = _sub(part, tri[~is_blade]) if (~is_blade).any() else None
    btri = tri[is_blade]
    blade = _sub(part, btri, parent=spec['blade_bone'])
    # one ring-to-ring section, straightened, x 0..1
    xa, xb = spec['body_rings']
    ra, rb = _ring(pos, xa), _ring(pos, xb)
    inside = ra | rb
    sec = btri[np.array([all(inside[v] for v in t) and any(ra[v] for v in t) and any(rb[v] for v in t)
                         for t in btri])]
    assert len(sec), 'no ring-to-ring section at %s - %s' % (xa, xb)
    run = _sub(part, sec)
    ca = pos[ra].mean(0)
    cb = pos[rb].mean(0)
    p = run['pos'].copy()
    t = np.clip((p[:, 0] - ca[0]) / (cb[0] - ca[0]), 0.0, 1.0)
    centre = ca[None, :] + t[:, None] * (cb - ca)[None, :]
    p[:, 1:] -= centre[:, 1:]
    p[:, 0] = t
    run['pos'] = p
    run = _crossed(run)
    # the point, x 0..1 from the tip ring to the end
    x0 = spec['tip_ring']
    r0 = _ring(pos, x0)
    c0 = pos[r0].mean(0)
    keep = np.array([all(pos[v, 0] >= x0 - 0.06 for v in t) for t in btri])
    tip = _sub(part, btri[keep])
    p = tip['pos'].copy()
    end = pos[:, 0].max()
    p[:, 1:] -= c0[None, 1:]
    p[:, 0] = (p[:, 0] - x0) / (end - x0)
    tip['pos'] = p
    tip = _crossed(tip)
    return hilt, blade, run, tip, dict(body_start=float(pos[btri.reshape(-1), 0].min()), tip_ring=x0,
                                       tip_len=float(end - x0), centre_start=c0.tolist())


def extend(sk, parts, spec=SPEC, log=print):
    """add the bones to sk (a ultimate_fighter.Skeleton) and the pieces to parts (mesh_parts); returns the new
    bone names (for the joint table) and the blade's measures"""
    names = bone_names(spec)
    root = sk.by_name[spec['root']]
    sword = sk.index[spec['bone']]
    # at a fixed index, right after the standard bones (the same 26 first in every costume), so the MSC's joint
    # number is every costume's (appended, the blade's was 135 in c00 - c05 and 122 in c06 / c07)
    at = spec.get('at', 26)
    for k, nm in enumerate(names):
        pos = at + k
        parent = sword if nm == spec['blade_bone'] else root
        for b in sk.bones:
            if b[1] >= pos:
                b[1] += 1
        for d in (sk.index, sk.by_name):
            for key, v in d.items():
                if v >= pos:
                    d[key] = v + 1
        if parent >= pos:
            parent += 1
        sk.bones.insert(pos, [nm, parent, zlib.crc32(nm.encode()) & 0xFFFFFFFF, []])
        sk.by_name[nm] = pos
        sk.index[nm] = pos
        sk.ult_parent[nm] = spec['bone'] if nm == spec['blade_bone'] else None
    assert len(set(h for _n, _p, h, _c in sk.bones)) == len(sk.bones), 'bone hash collision'
    info = None
    for mname in spec['meshes']:
        new = []
        for part in parts.get(mname, []):
            assert not part['infl'] and part['parent'] == spec['bone'], (mname, part['parent'])
            hilt, blade, run, tip, info = pieces(part, spec)
            if hilt is not None:
                new.append(hilt)
            new.append(blade)
            for k in range(spec['segments']):
                new.append(dict(run, parent=spec['segment_name'] % (k + 1)))
            if spec.get('tip_name'):
                new.append(dict(tip, parent=spec['tip_name']))
        parts[mname] = new
    log('snake sword: %d bones (%s .. %s), blade from x %.2f, point %.2f long from %.2f'
        % (len(names), names[0], names[-1], info['body_start'], info['tip_len'], info['tip_ring']))
    return names, info


# the sword's frame (+X along the blade) -> an article's (+Z along it, as weapon models: Pit's arrow turns with
# PostureModule(0x2717, -pitch, 90, 0)): X -> Z, Z -> -X, Y kept (a turn about Y)
TO_ARTICLE = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)


def _turned(q, scale_len=1.0):
    q = dict(q)
    p = q['pos'].copy()
    p[:, 0] *= scale_len
    q['pos'] = p @ TO_ARTICLE.T
    q['nrm'] = q['nrm'] @ TO_ARTICLE.T
    if q['tan'] is not None:
        t = q['tan'].copy()
        t[:, :3] = q['tan'][:, :3] @ TO_ARTICLE.T
        q['tan'] = t
    return q


def _uncrossed(q):
    """q without _crossed's turned copy (its second half)"""
    n = q['n'] // 2
    idx = q['idx'][:len(q['idx']) // 2]
    out = dict(q)
    out.update(n=n, pos=q['pos'][:n], nrm=q['nrm'][:n], tan=None if q['tan'] is None else q['tan'][:n],
               uvs={k: v[:n] for k, v in q['uvs'].items()}, idx=idx)
    return out


def article_pieces(part, spec=SPEC):
    """(run, tip, info) for the articles: the run one unit long along +Z (its z = 0 end on the root, z = 1 on the
    end bone), the point its real length along +Z from z = 0, drawn once: the articles turn by pitch about their
    depth axis, so the blade's face stays to the camera, and the point's crossed copy (a curved tip turned 90 degrees)
    drew a dark X across it (Sephiroth test 91, user: "the tip of the sword looks off")"""
    _h, _b, run, tip, info = pieces(part, spec)
    return _turned(run), _turned(_uncrossed(tip), info['tip_len']), info

