#!/usr/bin/env python3
"""Byleth's Sword of the Creator whip (Ultimate's `sword` article) on ZSS's whip article (his copy: weapon kind 0x1A0,
article 2). fighters/master/README.md "v6: the whip sword".

  python3 tools/master_whip.py build ULT BASE FIGHTER DUMP     (master_build.py build calls it)
  python3 tools/master_whip.py tips ULT                         the up special's tip / pull table (master.c)
  python3 tools/master_whip.py render ULT FIGHTER SLOT FRAME OUT.png [--body PAC]

ULT: Ultimate's fighter/master (model/sword/c00, motion/sword/c00, motion/body/c00); BASE: ZSS's vanilla fighter folder
(her whip: model/whip/c00, motion/whip, script/animcmd/weapon/whip); FIGHTER: the build's fighter/master; DUMP:
lua2cpp_master (the article's effect scripts).

What Smash 4's whip gives (ZSS's files and the executable, read for v6):
- its descriptor (weapon kind 0x38, copied for 0x1A0): +0 0x7D0 (its joint 2000, HaveN) linked to the owner's joint 0x19
  (RHaveN: Ultimate's HaveR, his converted skeleton's RHaveN is HaveR exactly); +8 its motion info: 60 entries, 15
  animations x 4 custom moves, each the material_anime-list CRC of an .omo name in motion/whip/main.pac
  (FitSZerosuitWhipMainC03AttackS4S ...: MOTIONS below). The names are fixed (the executable's table): the sword's
  motions go in under them;
- ACMD `Set_Anchored_Article_Action(2, motion)` (ZSS's up smash 4, grab 0x14, down taunt 0x2C) plays one of them in
  the FIGHTER's space: her whip's own HaveN track is her RHaveN's world matrix (her E00Catch: equal to 0.0002), its motion
  frame 0 at the frame the command runs. So an anchored motion here keys HaveN with his RHaveN (Ultimate's HaveR) in
  model space, frame by frame, and the sword's bones under it with the sword article's own tracks: the whip is placed as
  Ultimate's article (its root on HaveR) whatever the anchor (the fighter's root with the track, or the hand);
- her tether: `Set_Remote_Article_Action(2, 1)` (status 1: plays WhipShoot, 0x34, at a rate from her params, checks
  joints 2000 - 2001 (HaveN - AttachN: model.jtb) against the stage, LinkModule events to the owner on a ledge),
  `Set_Remote_Article_Action2(2, 3)` (status 3: WhipReverse 0x38 from the mirrored frame), status 5 (hanging: the frame
  set from the distance to the ledge). Those motions are in the HAND's space (her HaveN track: 0): WhipShoot here is
  Ultimate's `extend` with its tip (AttachN) as far from the hand as her AttachN is at that frame, capped at the sword's
  full reach (48: Ultimate's extend; past it the pose holds), so the native ledge check, the hang's frame-from-distance
  and the visible blade agree, and the reach is Ultimate's, not her whip's 64.

The skeleton: ZSS's 18 whip bones first (their names, hashes and order: model.jtb's joints 2000 - 2010 and model.nhb are
hers), HaveN's bind the identity (Ultimate's root), then the sword's 57 bones (sword01 under HaveN, Ultimate's bind
locals, CRC32 hashes). Her chain bones ride on the sword's (CHAIN): PlasmaWhip01H - 08H on sword05 ... sword37, AttachN /
PlasmaWhipEndN on the tip (sword_null), so her joints (effects 0x7D1 - 0x7D9, the ledge check) follow the blade. The
meshes: Ultimate's sword / sword2 / stone in her mesh slot Whip_VIS_O_OBJ_NSC (her Cylinder slot empty), on his body's
materials (ultimate_fighter.templates / material_for), textures in his article block (fighter_texture_ids 'whip').
"""
import argparse
import json
import os
import shutil
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import nud  # noqa: E402
import omo  # noqa: E402
import ultimate_fighter as UF  # noqa: E402

PREFIX = 'FitSZerosuitWhipMain'
# ZSS's whip motion slots (index into its motion info / motion.mtable: x4 custom moves) -> the name the executable hashes
ZSS_NAMES = {0: 'C03AttackS4S', 4: 'C04AttackHi4', 8: 'C05AttackAirN', 12: 'D01SpecialS', 16: 'D01SpecialAirS',
             20: 'E00Catch', 24: 'E00CatchDash', 28: 'E00CatchTurn', 32: 'E00CatchPulled', 36: 'E01ThrowF',
             40: 'J01AppealS', 44: 'J01AppealLw', 48: 'J02Win1', 52: 'WhipShoot', 56: 'WhipReverse'}
# what each slot plays now. Anchored ones: (Ultimate body animation, the body frame of article frame 0, the timeline:
# [(body frame, sword animation, its frame then, loop)]: the sword article's motions as his game scripts change them,
# Ultimate's frames; length). Every game script of his that makes the sword does it on frame 0 (generate_article +
# change_motion), so article frame = body frame; the up smash's charge holds the body at 7 (Ultimate's
# smash_restart_frame), the hold slot plays the sword's charge loop, the up smash slot restarts at 7.
SLOTS = {
    0: dict(move='AttackLw3', body='c02attacklw3', start=0, tl=[(0, 'c02attacklw3', 0)]),
    4: dict(move='AttackHi4', body='c04attackhi4', start=7, tl=[(7, 'c04attackhi4', 7)]),
    8: dict(move='AttackAirHi', body='c05attackairhi', start=0, tl=[(0, 'c05attackairhi', 0)]),
    12: dict(move='LandingAirHi', body='c05landingairhi', start=0, tl=[(0, 'c05landingairhi', 0)]),
    16: dict(move='SpecialHi', body='d02specialhi', start=0,
             tl=[(0, 'd02specialhistart', 0), (1, 'd02specialhistart', 0), (17, 'extend', 0),
                 (27, 'd02specialhiend', 0)]),
    20: dict(move='AttackHi4 (charge)', body='c04attackhi4', start=0, hold=7, frames=7 + 122,
             tl=[(0, 'c04attackhi4', 0), (7, 'c04attackhi4charge', 0, True)]),
    24: dict(move='Attack100Start', body='c00attack100start', start=0, tl=[(0, 'c00attack100start', 0)]),
    28: dict(move='Attack100', body='c00attack100', start=0, tl=[(0, 'c00attack100', 0)]),
    32: dict(move='Attack100End', body='c00attackend', start=0, tl=[(0, 'c00attackend', 0)]),
    36: dict(move='ThrowF', body='e01throwf', start=0, tl=[(0, 'e01throwf', 0)]),
    40: dict(move='ThrowB', body='e01throwb', start=0, tl=[(0, 'e01throwb', 0)]),
    44: dict(move='AppealLw', body='j01appeallwr', start=0, tl=[(0, 'j01appeallwr', 0)]),
    48: dict(move='ThrowLw', body='e01throwlw', start=0, tl=[(0, 'e01throwlw', 0)]),
    52: dict(move='SpecialAirHi (shoot: status 1)', status='shoot'),
    56: dict(move='SpecialAirHi (back: status 3)', status='reverse'),
}
SLOT_OF = {v['move']: k for k, v in SLOTS.items()}
# the body sword's frames (Ultimate's master_sword track) decide when the whip shows: it is drawn while the body's sword
# is hidden (Ultimate generates the article as the body hides its sword and shows the sword again when it folds back)
CHAIN = [('PlasmaWhip01H', 'sword05'), ('PlasmaWhip02H', 'sword10'), ('PlasmaWhip03H', 'sword15'),
         ('PlasmaWhip04H', 'sword20'), ('PlasmaWhip05H', 'sword25'), ('PlasmaWhip06H', 'sword30'),
         ('PlasmaWhip07H', 'sword35'), ('PlasmaWhip08H', 'sword37'), ('AttachN', 'sword_null'),
         ('PlasmaWhipEndN', 'sword_null')]
# the whip's joints (model.jtb: 2000 HaveN, 2001 AttachN, 2002 - 2009 PlasmaWhip01H - 08H, 2010 PlasmaWhipEndN) by the
# sword bone they stand on (its effect scripts' bones)
JOINTS = {'haver': 2000, 'sword_null': 2001, 'sword05': 2002, 'sword10': 2003, 'sword15': 2004, 'sword20': 2005,
          'sword25': 2006, 'sword30': 2007, 'sword35': 2008, 'sword37': 2009}
REACH = 48.0                     # Ultimate's extend: the tip's farthest from the hand (frames 7 - 9)


# ---------------------------------------------------------------- Ultimate's data
class Ult:
    def __init__(self, ult):
        import ssbh_data_py as s
        self.ult, self.s = ult, s
        self._anims = {}
        sk = s.skel_data.read_skel(os.path.join(ult, 'model/sword/c00/model.nusktb'))
        self.names = [b.name for b in sk.bones]
        self.parent = {b.name: (sk.bones[b.parent_index].name if b.parent_index is not None else None) for b in sk.bones}
        self.bind = {b.name: np.array(b.transform, float).T for b in sk.bones}
        self.root = self.names[0]
        assert self.parent[self.root] is None and self.root == 'HaveR'

    def anim(self, folder, name):
        key = (folder, name)
        if key not in self._anims:
            a = self.s.anim_data.read_anim(os.path.join(self.ult, 'motion', folder, 'c00', name + '.nuanmb'))
            n = int(round(a.final_frame_index)) + 1
            tr, vis = UF.ult_tracks(a, n)
            self._anims[key] = (tr, vis, n)
        return self._anims[key]

    def sword_locals(self, name, fr):
        """{bone: local 4x4} of the sword at (fractional) frame fr of its motion `name` (None: the bind)"""
        if name is None:
            return dict(self.bind)
        tr, _v, n = self.anim('sword', name)
        fr = min(max(fr, 0.0), n - 1)
        a, t = int(np.floor(fr)), fr - np.floor(fr)
        b = min(a + 1, n - 1)
        out = {}
        for k in self.names:
            if k not in tr:
                out[k] = self.bind[k]
            elif t < 1e-6:
                out[k] = tr[k][a]
            else:
                out[k] = blend(tr[k][a], tr[k][b], t)
        return out

    def rel(self, loc):
        """{bone: matrix relative to the root} (the root's own transform left out: Ultimate's link replaces it)"""
        out = {self.root: np.eye(4)}

        def w(n):
            if n not in out:
                out[n] = w(self.parent[n]) @ loc[n]
            return out[n]
        for n in self.names:
            w(n)
        return out

    def body_world(self, anim, fr):
        """{bone: world} of Ultimate's body animation (his converted RHaveN is this HaveR exactly), its root Trans's
        translation left out (the fighter's drawn pose)"""
        sk = self._body_skel()
        tr, _v, n = self.anim('body', anim)
        fr = min(fr, n - 1)
        names, par, bind = sk
        W = {}

        def w(i):
            nm = names[i]
            if nm not in W:
                loc = tr[nm][fr] if nm in tr else bind[i]
                W[nm] = loc if par[i] is None else w(par[i]) @ loc
            return W[nm]
        for i in range(len(names)):
            w(i)
        t = W['Trans'][:3, 3].copy()
        if np.abs(t).max() > 1e-3:
            for k in W:
                W[k] = W[k].copy()
                W[k][:3, 3] -= t
        return W

    def _body_skel(self):
        if not hasattr(self, '_bs'):
            sk = self.s.skel_data.read_skel(os.path.join(self.ult, 'model/body/c00/model.nusktb'))
            self._bs = ([b.name for b in sk.bones], [b.parent_index for b in sk.bones],
                        [np.array(b.transform, float).T for b in sk.bones])
        return self._bs

    def body_vis(self, anim, name='master_sword'):
        _tr, vis, n = self.anim('body', anim)
        v = vis.get(name)
        return np.ones(n, bool) if v is None else np.asarray(v, bool)


def blend(a, b, t):
    """two 4x4 locals blended: translation / scale linearly, rotation by slerp"""
    ta, ra, sa = UF.decompose(a)
    tb, rb, sb = UF.decompose(b)
    qa, qb = UF._mat_quat(ra[None])[0], UF._mat_quat(rb[None])[0]
    if np.dot(qa, qb) < 0:
        qb = -qb
    d = np.clip(np.dot(qa, qb), -1, 1)
    if d > 0.9995:
        q = qa + t * (qb - qa)
    else:
        th = np.arccos(d)
        q = (np.sin((1 - t) * th) * qa + np.sin(t * th) * qb) / np.sin(th)
    q /= np.linalg.norm(q)
    m = np.eye(4)
    m[:3, :3] = UF._quat_mat(q[None])[0] * (sa + t * (sb - sa))
    m[:3, 3] = ta + t * (tb - ta)
    return m


def timeline_at(tl, f):
    """(sword animation, its frame) at body frame f on a slot's timeline"""
    cur = tl[0]
    for e in tl:
        if f >= e[0]:
            cur = e
    name, start = cur[1], cur[2]
    fr = f - cur[0] + start
    if len(cur) > 3 and cur[3]:
        return name, fr                         # looped by the caller (frames mod the motion's)
    return name, fr


# ---------------------------------------------------------------- the skeleton
def zss_bones(base):
    """ZSS's whip bones [(name, parent, hash, local 4x4)] from her model.vbn"""
    d = open(os.path.join(base, 'model/whip/c00/model.vbn'), 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    out, off = [], 28
    for _ in range(n):
        name = d[off:off + 64].split(b'\0')[0].decode()
        _t, parent, h = struct.unpack(e + 'IiI', d[off + 64:off + 76])
        out.append([name, parent if 0 <= parent < n else -1, h])
        off += 76
    for b in out:
        v = struct.unpack(e + '9f', d[off:off + 36])
        off += 36
        m = np.eye(4)
        m[:3, :3] = UF.euler_mat(*v[3:6]) * np.array(v[6:9])
        m[:3, 3] = v[:3]
        b.append(m)
    return out


class Skel:
    """the whip's skeleton: ZSS's 18 bones, then the sword's (HaveR = HaveN)"""

    def __init__(self, ult, base):
        z = zss_bones(base)
        assert [b[0] for b in z[:11]] == ['HaveN'] + [c for c, _s in CHAIN], [b[0] for b in z]
        self.bones = [[n, p, h, m] for n, p, h, m in z]
        self.bones[0][3] = np.eye(4)                   # HaveN: Ultimate's root (the link's frame)
        self.index = {b[0]: i for i, b in enumerate(self.bones)}
        for n in ult.names[1:]:
            p = ult.parent[n]
            pi = 0 if p == ult.root else self.index[p]
            h = zlib.crc32(n.encode()) & 0xFFFFFFFF
            self.index[n] = len(self.bones)
            self.bones.append([n, pi, h, ult.bind[n]])
        assert len({b[2] for b in self.bones}) == len(self.bones), 'bone hash collision'
        # her chain's bind on the sword's (folded) bind
        rel = ult.rel(ult.bind)
        for name, loc in self.chain_locals(rel).items():
            self.bones[self.index[name]][3] = loc
        self.ult_index = {n: self.index[n] for n in ult.names[1:]}
        self.ult_index[ult.root] = 0

    @staticmethod
    def chain_locals(rel):
        """her chain bones' locals from the sword's bones relative to the root"""
        out, prev = {}, np.eye(4)
        for name, sb in CHAIN:
            m = np.linalg.inv(prev) @ rel[sb]
            out[name] = m
            prev = rel[sb]
        return out

    def world_bind(self):
        w = []
        for b in self.bones:
            w.append(b[3] if b[1] < 0 else w[b[1]] @ b[3])
        return w

    def vbn(self):
        """little-endian model.vbn as hers (' NBV' 2.1, every bone type 0)"""
        n = len(self.bones)
        out = struct.pack('<4sHHI4I', b' NBV', 2, 1, n, n, 0, 0, 0)
        for name, parent, h, _m in self.bones:
            out += name.encode()[:63].ljust(64, b'\0') + struct.pack('<IiI', 0, 0x0FFFFFFF if parent < 0 else parent, h)
        for _n, _p, _h, m in self.bones:
            t, r, s = UF.decompose(m)
            out += struct.pack('<9f', *t, *UF.euler_of(r), *s)
        return out


# ---------------------------------------------------------------- the model
def build_model(ult, base, body_c00, out, log=print):
    import fighter_texture_ids as T
    U = Ult(ult)
    sk = Skel(U, base)
    T.register('master', articles=['whip'])
    tex = UF.Textures(os.path.join(ult, 'model/sword/c00'), T.article_id('master', 'whip', 0))
    tmpl = UF.templates(nud.read(os.path.join(body_c00, 'model.nud')))
    parts = UF.mesh_parts(os.path.join(ult, 'model/sword/c00'))
    world = sk.world_bind()
    root_inv = np.linalg.inv(U.bind[U.root])          # Ultimate's model space -> ours (root at the identity)

    class _Sk:                                          # what ultimate_fighter.skin needs
        index = sk.ult_index
        ult_parent = U.parent
        by_name = {'HipN': sk.index['sword01']}
    polys = []
    for name in ('sword_VIS_O_OBJShape', 'sword2_VIS_O_OBJShape', 'stone_VIS_O_OBJShape'):
        for part in parts.get(name, []):
            part = dict(part)
            if part['infl']:
                part['pos'] = (np.c_[part['pos'], np.ones(part['n'])] @ root_inv.T)[:, :3]
                part['nrm'] = part['nrm'] @ root_inv[:3, :3].T
                if part['tan'] is not None:
                    part['tan'] = np.c_[part['tan'][:, :3] @ root_inv[:3, :3].T, part['tan'][:, 3:]]
            pos, nrm, tan, bit, idx, bw = UF.skin(part, _Sk, world)
            p = nud.Polygon()
            p.pos, p.nrm, p.tan, p.bit, p.bones, p.weights = pos, nrm, tan, bit, idx, bw
            p.uvs = [part['uvs']['map1']]
            p.col = np.full((part['n'], 4), UF.WHITE)
            p.idx = part['idx']
            p.materials = [UF.material_for(tex, part['mat'], tmpl, part)]
            polys.append(p)
    empty = UF.empty_polygon(tmpl)
    empty.bones = np.full((3, 4), sk.index['sword01'], np.int64)
    meshes = [nud.Mesh('Whip_VIS_O_OBJ_NSC', polys, bone=-1, bind=4),
              nud.Mesh('Cylinder_VIS_O_OBJ_NSC', [empty], bone=-1, bind=4)]
    os.makedirs(out, exist_ok=True)
    src = os.path.join(base, 'model/whip/c00')
    for f in ('model.jtb', 'model.moi', 'model.mta', 'model.nhb', 'model.sb', 'model.xmb'):
        shutil.copy(os.path.join(src, f), os.path.join(out, f))
    open(os.path.join(out, 'model.vbn'), 'wb').write(sk.vbn())
    open(os.path.join(out, 'model.nud'), 'wb').write(nud.write(meshes, top_bone=len(sk.bones) - 1))
    open(os.path.join(out, 'model.nut'), 'wb').write(tex.nut())
    log('whip model: %d bones (her 18 + the sword\'s %d), %d polygons (%d vertices), textures %s' % (
        len(sk.bones), len(U.names) - 1, len(polys), sum(len(p.pos) for p in polys),
        ', '.join('0x%08X %dx%d' % (i, im.shape[1], im.shape[0]) for i, im in tex.images)))
    return sk


# ---------------------------------------------------------------- the motions
def slot_frames(U, slot):
    s = SLOTS[slot]
    if 'frames' in s:
        return s['frames']
    return U.anim('body', s['body'])[2] - s['start']


def anchored_pose(U, slot, f):
    """(HaveN local = his hand in model space, the sword's locals) at article frame f of an anchored slot"""
    s = SLOTS[slot]
    b = s['start'] + f
    hand_frame = min(b, s['hold']) if 'hold' in s else b
    hand = U.body_world(s['body'], hand_frame)['HaveR']
    name, fr = timeline_at(s['tl'], b)
    if name is not None:
        n = U.anim('sword', name)[2]
        e = [x for x in s['tl'] if x[1] == name and b >= x[0]][-1]
        if len(e) > 3 and e[3]:
            fr = fr % n
    return hand, U.sword_locals(name, fr)


def shoot_table(U, base):
    """WhipShoot's frames (her 101): her AttachN's distance from HaveN at each, and the extend frame whose tip is as far
    (capped at REACH)"""
    zb = zss_bones(base)
    ents = dict(omo.pac_read(os.path.join(base, 'motion/whip/main.pac')))
    o = omo.Omo(ents[PREFIX + 'WhipShoot.omo'])
    dist = []
    for fr in range(o.frames):
        W = []
        for b in zb:
            smp = o.sample(b[2], fr)
            loc = np.array(omo.trs(*smp), float).reshape(4, 4) if smp else b[3]
            W.append(loc if b[1] < 0 else W[b[1]] @ loc)
        dist.append(float(np.linalg.norm(W[9][:3, 3] - W[0][:3, 3])))
    # the extend's tip distance, sampled finely on its growing part (frames 1 - 8)
    ts = np.linspace(1.0, 8.0, 701)
    ds = np.array([np.linalg.norm(U.rel(U.sword_locals('extend', t))['sword_null'][:3, 3]) for t in ts])
    ds = np.maximum.accumulate(ds)
    frames = [float(np.interp(min(d, REACH), ds, ts)) for d in dist]
    return dist, frames, o


def status_pose(U, kind, f, table):
    """the tether's motions (hand space): WhipShoot = extend at the matching frame; WhipReverse = WhipShoot backwards,
    folding into the sword's wait pose once shorter than the extend's frame 2 (18 from the hand: there the extend
    curls back, Ultimate's back motion folds the sword)"""
    dist, frames, o = table
    n = o.frames
    g = f if kind == 'shoot' else n - 1 - f
    t = frames[g]
    loc = U.sword_locals('extend', t)
    if kind == 'reverse':
        d2 = float(np.linalg.norm(U.rel(U.sword_locals('extend', 2.0))['sword_null'][:3, 3]))
        if dist[g] < d2:
            k = (d2 - dist[g]) / max(d2 - dist[0], 1e-6)
            a, b = U.sword_locals('extend', 2.0), U.sword_locals('wait', 0)
            loc = {x: blend(a[x], b[x], min(1.0, k)) for x in a}
    return np.eye(4), loc


def build_motions(ult, base, out_pac, log=print):
    U = Ult(ult)
    sk = Skel(U, base)
    ents = dict(omo.pac_read(os.path.join(base, 'motion/whip/main.pac')))
    head = omo.Omo(ents[PREFIX + 'WhipShoot.omo']).head
    table = shoot_table(U, base)
    out = []
    info = {}
    for slot in sorted(SLOTS):
        s = SLOTS[slot]
        n = len(table[0]) if 'status' in s else slot_frames(U, slot)
        locs = [np.zeros((n, 4, 4)) for _ in sk.bones]
        for f in range(n):
            if 'status' in s:
                hand, loc = status_pose(U, s['status'], f, table)
            else:
                hand, loc = anchored_pose(U, slot, f)
            locs[0][f] = hand
            for name, i in sk.ult_index.items():
                if i:
                    locs[i][f] = loc[name]
            rel = U.rel(loc)
            for name, m in Skel.chain_locals(rel).items():
                locs[sk.index[name]][f] = m
            for i, b in enumerate(sk.bones[11:18], 11):     # her billboards: their bind
                locs[i][f] = b[3]
        bones = [(b[0], b[1], b[2], None) for b in sk.bones]

        class _S:
            pass
        _S.bones = bones
        out.append((PREFIX + ZSS_NAMES[slot] + '.omo', UF.omo_bytes(head, locs, _S, n)))
        info[slot] = n
    os.makedirs(os.path.dirname(out_pac), exist_ok=True)
    omo.pac_write(out_pac, out)
    log('whip motions: %s' % ', '.join('%d %s (%s, %d frames)' % (k, ZSS_NAMES[k], SLOTS[k]['move'], v)
                                       for k, v in sorted(info.items())))
    return table


# ---------------------------------------------------------------- the whip's scripts
def shown(U, slot):
    """[(frame, 0 / 1)]: the whip drawn while Ultimate's body sword is hidden"""
    s = SLOTS[slot]
    if 'status' in s:
        return [(0, 1)]
    v = U.body_vis(s['body'])
    n = slot_frames(U, slot)
    st = []
    for f in range(n):
        b = s['start'] + f
        if 'hold' in s and b >= s['hold']:
            b = s['hold']
        st.append(0 if v[min(b, len(v) - 1)] else 1)
    keys = [(0, st[0])] + [(f, st[f]) for f in range(1, n) if st[f] != st[f - 1]]
    return keys


def game_script(U, slot):
    import ultimate_acmd as UA
    cmds, t = [], 0
    items = [(f, UA.cmd('Visibility', st)) for f, st in shown(U, slot)]
    if SLOTS[slot]['move'] == 'SpecialHi':          # the body's FT_MOTION_RATE (his SpecialHi: 0.3 on 1 - 10)
        items += [(1, UA.cmd('Set_Frame_Duration', 0.3)), (10, UA.cmd('Set_Frame_Duration', 1.0))]
    for f, c in sorted(items, key=lambda x: x[0]):
        if f > t:
            cmds.append(UA.cmd('FRAME', f))
            t = f
        cmds.append(c)
    return cmds + [acmd.Command(acmd.END)]


def effect_script(dump, slot, ids, table):
    """the sword article's own effect scripts on the whip's joints: its Extend (master_wire_flash on sword37, _wind on
    sword35) from the up special's frame 17 (ground, anchored) or on WhipShoot at the frames its tip is as far as the
    extend's (the tether)"""
    import ultimate_acmd as UA
    s = SLOTS[slot]
    if s['move'] not in ('SpecialHi', 'SpecialAirHi (shoot: status 1)'):
        return [acmd.Command(acmd.END)]
    body = UA.functions(open(os.path.join(dump, 'master_sword', 'Extend.txt')).read())['effect_extend']
    tr = UA.EffectTranslator(dict(JOINTS), ids, {})
    cmds = tr.script(body)
    if tr.missing:
        raise SystemExit('whip effects without an id: %s' % ', '.join(sorted(tr.missing)))
    if s['move'] == 'SpecialHi':
        remap = lambda f: f + 17                                         # noqa: E731
    else:
        _dist, frames, _o = table
        remap = lambda f: min(int(np.searchsorted(np.array(frames), min(f, 8.0))), len(frames) - 1)   # noqa: E731
    outc = []
    for c in cmds:
        if c.name == 'FRAME':
            outc.append(UA.cmd('FRAME', remap(float(c.params[0]))))
        else:
            outc.append(c)
    return outc


def build_scripts(dump, ult, base, fighter, ids, table, log=print):
    U = Ult(ult)
    src = os.path.join(base, 'script/animcmd/weapon/whip')
    wmt = open(os.path.join(src, 'motion.mtable'), 'rb').read()
    wh = struct.unpack('>%dI' % (len(wmt) // 4), wmt)
    files = {k: {} for k in ('game', 'effect', 'sound', 'expression')}
    for i, h in enumerate(wh):
        if not h:
            continue
        slot = i - i % 4
        sc = {'game': game_script(U, slot) if slot in SLOTS else [acmd.Command(acmd.END)],
              'effect': effect_script(dump, slot, ids, table) if slot in SLOTS else [acmd.Command(acmd.END)]}
        for fn in files:
            files[fn][h] = [acmd.Command(c.ident, list(c.params)) for c in sc.get(fn, [acmd.Command(acmd.END)])]
    ww = os.path.join(fighter, 'script/animcmd/weapon/whip')
    os.makedirs(ww, exist_ok=True)
    for fn, scripts in files.items():
        acmd.ACMDFile(scripts).save(os.path.join(ww, fn + '.bin'))
    open(os.path.join(ww, 'motion.mtable'), 'wb').write(wmt)
    log('whip scripts: %d motions (game: visibility by his body sword\'s track; effect: the sword\'s Extend on the up '
        'special and the tether shot)' % len([h for h in wh if h]))


# ---------------------------------------------------------------- the body's game scripts
def body_scripts(game, log=print):
    """the whip made and moved by his body's game scripts at Ultimate's frames (generate_article / change_motion /
    remove_exist SWORD: his dump), its tether (status 1 / 3) on the air up special"""
    import ultimate_acmd as UA
    G = lambda *a: UA.cmd(*a)                                           # noqa: E731
    gen = lambda slot: [G('GENERATE_ARTICLE', 2), G('Set_Anchored_Article_Action', 2, slot)]   # noqa: E731
    plan = {
        # script: (frame-0 commands, [(frame, commands)]) - Ultimate's remove_exist frames
        'attacklw3': (gen(0), [(59, [G('Remove_Article', 2)])]),
        'attack100start': (gen(24), []),
        'attack100': (gen(28), []),
        'attack100end': (gen(32), [(85, [G('Remove_Article', 2)])]),
        # the charge holds the body at 7 (ON_FLAG 0x2100001B): the hold slot from 0, the up smash's from 7 (FRAME 8:
        # after the charge)
        'attackhi4': (gen(20), [(8, [G('Set_Anchored_Article_Action', 2, 4)]), (79, [G('Remove_Article', 2)])]),
        'attackairhi': (gen(8), [(65, [G('Remove_Article', 2)])]),
        'landingairhi': ([G('Set_Anchored_Article_Action', 2, 12)], [(61, [G('Remove_Article', 2)])]),
        'throwf': (gen(36), [(71, [G('Remove_Article', 2)])]),
        'throwb': (gen(40), [(55, [G('Remove_Article', 2)])]),
        'throwlw': (gen(48), [(52, [G('Remove_Article', 2)])]),
        'appeallwr': (gen(44), [(85, [G('Remove_Article', 2)])]),
        'appeallwl': (gen(44), [(85, [G('Remove_Article', 2)])]),
        'specialhi': (gen(16), [(72, [G('Remove_Article', 2)])]),
        # the air one's hit: the tether pulled back (status 3: WhipReverse), the folded sword kept in his hand to the
        # overtake's end (Ultimate's body sword stays hidden through both); the wall jump: gone at once
        'specialairhihit': ([G('Set_Remote_Article_Action2', 2, 3)], []),
        'specialairhiovertake': ([], [(12, [G('Remove_Article', 2)])]),
        'specialairhiwalljump': ([G('Remove_Article', 2)], []),
    }
    done = []
    for name, (first, later) in plan.items():
        k = acmd.crc(name)
        sc = [c for c in game.scripts.get(k, []) if c.ident != acmd.END]
        if name in ('appeallwr', 'appeallwl'):
            sc = []                       # ZSS's own whip taunt (generate + her action 0x2C + remove at 121) / JUMP
        # her leftover whip commands out (none should be left: the translator writes Ultimate's)
        sc = [c for c in sc if c.name not in ('GENERATE_ARTICLE', 'Set_Anchored_Article_Action', 'Remove_Article')
              or name in ('aircatch',)]
        extra = []
        for f, cs in later:
            extra += [G('FRAME', f)] + cs
        merged = UA.merge_flat(sc + [acmd.Command(acmd.END)], extra + [acmd.Command(acmd.END)]) if extra else \
            sc + [acmd.Command(acmd.END)]
        if merged is None:
            # a looping / branching script: the later commands at its end
            merged = sc + extra + [acmd.Command(acmd.END)]
        game.scripts[k] = first + merged
        done.append(name)
    log('whip in the body scripts: %s' % ', '.join(done))


# ---------------------------------------------------------------- the throw bone: Ultimate's up-special hitboxes
# the up special's sword timeline (his SpecialHi / SpecialAirHi game scripts): generated at 1 with special_hi /
# special_air_hi_start, EXTEND at 17 (the `extend` motion), BACK at 27 (special_hi_end / special_air_hi_end)
UP_TL = {'d02specialhi': SLOTS[16]['tl'],
         'd02specialairhi': [(0, 'd02specialairhistart', 0), (1, 'd02specialairhistart', 0), (17, 'extend', 0),
                             (27, 'd02specialairhiend', 0)]}


def tip_rel(U, body, f):
    """the sword's tip (sword_null) at body frame f of the up special (Ultimate's timeline), in model space"""
    hand = U.body_world(body, f)['HaveR']
    name, fr = timeline_at(UP_TL[body], f)
    return hand @ U.rel(U.sword_locals(name, fr))['sword_null']


def bake_throw(ult, pac_path, vbn_path, log=print):
    """Ultimate's up special puts its hitboxes on `throw` (2, -1, -1 ...), which its status code keeps on the sword's
    tip (his body animations hold Throw at the origin): his converted D02SpecialHi / G04AirCatch get a ThrowN track at
    the tip of the sword as Ultimate's timeline has it (start 1 - 16, extend 17 - 26, end 27 on), its rotation kept"""
    U = Ult(ult)
    bones = omo.vbn_read(vbn_path)
    names = [b[0] for b in bones]
    th = bones[names.index('ThrowN')][2]
    ents = omo.pac_read(pac_path)
    out = []
    for name, data in ents:
        key = name[len('FitSZerosuitBodyMain'):-4]
        ult = {'D02SpecialHi': 'd02specialhi', 'G04AirCatch': 'd02specialairhi'}.get(key)
        if ult is None:
            out.append((name, data))
            continue
        o = omo.Omo(data)
        pos, rots, scl = [], [], []
        for f in range(o.frames):
            W = omo.world(o, bones, f)
            rw = np.array(W['RotN'], float)
            tip = tip_rel(U, ult, f)
            loc = np.linalg.inv(rw) @ tip
            smp = o.sample(th, f)
            p, q, s = smp if smp else ((0, 0, 0), (0, 0, 0, 1), (1, 1, 1))
            pos.append(tuple(loc[:3, 3]))
            rots.append(tuple(q))
            scl.append(tuple(s))
        omo.set_node(o, th, pos, rots, scl)
        out.append((name, o.encode()))
        log('%s: ThrowN on the sword tip (frame 17 %s, 21 %s)' % (
            os.path.relpath(pac_path).split('motion/')[-1] + ':' + key,
            np.round(tip_rel(U, ult, 17)[:3, 3], 1).tolist(), np.round(tip_rel(U, ult, 21)[:3, 3], 1).tolist()))
    omo.pac_write(pac_path, out)


def tips(ult):
    """the air up special's pull per hit frame: toward the tip from his hand (Ultimate's SpecialAirHiHit rewinds him at
    param_special_hi rewind_speed 4.1 a frame, object_dist_max 55)"""
    U = Ult(ult)
    rows = []
    for f in range(16, 26):
        W = U.body_world('d02specialairhi', f)
        tip = tip_rel(U, 'd02specialairhi', f)[:3, 3]
        hand = W['HaveR'][:3, 3]
        d = tip - hand
        dist = min(float(np.hypot(d[1], d[2])), 55.0)
        n = max(1, int(round(dist / 4.1)))
        ang = np.arctan2(d[1], d[2])
        rows.append((f, round(4.1 * float(np.cos(ang)), 3), round(4.1 * float(np.sin(ang)), 3), n,
                     np.round(tip, 1).tolist()))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    for x in ('ult', 'base', 'fighter', 'dump'):
        b.add_argument(x)
    t = sub.add_parser('tips')
    t.add_argument('ult')
    a = ap.parse_args()
    if a.cmd == 'tips':
        for r in tips(a.ult):
            print('frame %d: speed x %.3f y %.3f for %d frames (tip %s)' % r)
        return
    ids = {}
    for p in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(ROOT, 'fighters/master/master_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(p)).items() if not k.startswith('_')})
    build_model(a.ult, a.base, os.path.join(a.fighter, 'model/body/c00'), os.path.join(a.fighter, 'model/whip/c00'))
    table = build_motions(a.ult, a.base, os.path.join(a.fighter, 'motion/whip/main.pac'))
    build_scripts(a.dump, a.ult, a.base, a.fighter, ids, table)


if __name__ == '__main__':
    main()
