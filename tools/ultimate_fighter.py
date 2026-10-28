#!/usr/bin/env python3
"""An Ultimate fighter's model (SSBH: .nusktb / .numshb / .numatb / .nutexb) as a Smash 4 fighter
model folder, on the fighter's own skeleton (docs/ultimate-fighter-port.md).

  python3 tools/ultimate_fighter.py model SRC_cNN BASE_cNN OUT_cNN [--tex-id 0x40EB0000] [--empty DIR]
  python3 tools/ultimate_fighter.py motions SRC_MOTION_DIR SRC_c00 BASE_FIGHTER OUT_FIGHTER

SRC_cNN   Ultimate model/body/cNN (model.nusktb / numshb / numdlb / numatb, the .nutexb)
BASE_cNN  the base fighter's Smash 4 model/body/cNN (Zelda's): material templates, model.ik, the
          joint table it maps, its mesh slots (model.moi) and the metal material
OUT_cNN   gets model.vbn / model.jtb / model.nud / model.nut / metal.nud, model.sb (no swing
          bones), model.nhb (no helper bones), and the base's other files

Skeleton: the base's first 26 bones (TransN ... ThrowN, the ones the game, the IK and the joint
table know) in the base's order with the base's hashes, from Ultimate's Trans ... Throw (STANDARD),
then every other Ultimate bone (its own name, a CRC32 hash), parents first. Ultimate puts LegC
between Hip and the legs and ClavicleC between Bust and the clavicles; Smash 4's legs and shoulders
hang from HipN / BustN, so those two are folded: a leg's bind (and every frame of it) is LegC's
times the leg's, and LegC / ClavicleC stay as extra bones under HipN / BustN for the vertices
weighted to them. Last, the base's joint table 1 bones (the ones its own code drives, e.g. FaceN)
we have nothing for: bones of their own, nothing skinned to them.

Meshes: every mesh skinned (bind 4, four byte weights a vertex, as the base's body), positions in
bind space (a mesh Ultimate binds to one bone is weighted 1.0 to it). The NUD's mesh list is the
base's (MESH_SLOTS): the game names expression meshes by these names (model.moi, the material
animations' visibility entries), so each Ultimate mesh goes into the base mesh that plays its part
(an eye open / blink / mouth shape...) and a base mesh with nothing of Ultimate's gets one empty
triangle. Materials: the base's body / alpha-blended material layouts, textures converted: color
(ambient occlusion and emission baked in), normal (Ultimate's XY, Z rebuilt), the eyes' iris baked
onto the white (Ultimate maps it with a second UV set).
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
sys.path.insert(0, HERE)
import nud  # noqa: E402
import nut  # noqa: E402
import nutexb  # noqa: E402

# Smash 4 name (the base's index order) <- Ultimate name
STANDARD = [('TransN', 'Trans'), ('RotN', 'Rot'), ('HipN', 'Hip'), ('LLegJ', 'LegL'), ('LKneeJ', 'KneeL'),
            ('LFootJ', 'FootL'), ('LToeN', 'ToeL'), ('RLegJ', 'LegR'), ('RKneeJ', 'KneeR'), ('RFootJ', 'FootR'),
            ('RToeN', 'ToeR'), ('WaistN', 'Waist'), ('BustN', 'Bust'), ('LShoulderN', 'ClavicleL'),
            ('LShoulderJ', 'ShoulderL'), ('LArmJ', 'ArmL'), ('LHandN', 'HandL'), ('RShoulderN', 'ClavicleR'),
            ('RShoulderJ', 'ShoulderR'), ('RArmJ', 'ArmR'), ('RHandN', 'HandR'), ('NeckN', 'Neck'),
            ('HeadN', 'Head'), ('RHaveN', 'HaveR'), ('LHaveN', 'HaveL'), ('ThrowN', 'Throw')]
FOLD = ('LegC', 'ClavicleC')


def set_have(left, right):
    """the Ultimate bones that play LHaveN / RHaveN (default HaveL / HaveR). Sephiroth: SwordL1 / SwordR1
    (same parents, HandL / HandR), so the moves' sword hitboxes use the base's joints 24 / 25: every
    vanilla fighter's joint table has 26 entries, and the swords appended as joints 27 / 28 (test 20)
    gave hitboxes that hit the whole stage. A held item then takes the sword's orientation."""
    for i, (s4, _u) in enumerate(STANDARD):
        if s4 == 'LHaveN':
            STANDARD[i] = (s4, left)
        elif s4 == 'RHaveN':
            STANDARD[i] = (s4, right)

# the base's joint-table bones that aren't standard -> the Ultimate bone that plays the part
JOINT_STANDINS = {'Larmor': 'H_ShoulderpadL', 'Rarmor': 'H_ShoulderpadR', 'Bustarmor': 'Bust'}

TEX_ID = 0x40EB0000
PIXEL_ART = 0                   # model --pixel-art N: textures smaller than N blown up to it, nearest
WHITE = 127                     # vertex color 1.0


# ---------------------------------------------------------------- math (column vectors)
def euler_of(r):
    """rotation matrix -> the VBN's (rx, ry, rz): R = Rz Ry Rx (Model.cs EulerToQuat)"""
    sy = -r[2, 0]
    ry = np.arcsin(np.clip(sy, -1, 1))
    if abs(sy) < 0.9999:
        rx = np.arctan2(r[2, 1], r[2, 2])
        rz = np.arctan2(r[1, 0], r[0, 0])
    else:
        rx = np.arctan2(-r[1, 2], r[1, 1])
        rz = 0.0
    return rx, ry, rz


def euler_mat(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    rxm = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rym = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rzm = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rzm @ rym @ rxm


def decompose(m):
    """4x4 (column vectors) -> position, rotation matrix, scale"""
    t = m[:3, 3].copy()
    s = np.linalg.norm(m[:3, :3], axis=0)
    r = m[:3, :3] / s
    if np.linalg.det(r) < 0:
        s[0] = -s[0]
        r[:, 0] = -r[:, 0]
    return t, r, s


# ---------------------------------------------------------------- skeleton
class Skeleton:
    """the Smash 4 skeleton of an Ultimate one: bones [(name, parent, hash, local 4x4)], the
    Ultimate bone each comes from (FOLD's children: [folded, own])"""

    def __init__(self, skel, base_vbn, keep=None):
        ub = skel.bones
        self.ult_names = [b.name for b in ub]
        upar = {b.name: (ub[b.parent_index].name if b.parent_index is not None else None) for b in ub}
        ulocal = {b.name: np.array(b.transform, dtype=np.float64).T for b in ub}   # row -> column vectors
        self.ult_parent, self.ult_local = upar, ulocal
        base_hash = {n: h for n, _p, h in base_vbn}
        to_s4 = {u: s for s, u in STANDARD}
        out = []                         # [s4 name, parent index, hash, [ult chain]]
        index = {}                       # ult name -> our index

        def eff_parent(u):
            p = upar[u]
            chain = []
            while p in FOLD:
                chain.insert(0, p)
                p = upar[p]
            return p, chain

        for s4, u in STANDARD:
            p, chain = eff_parent(u)
            pi = index[p] if p is not None else -1
            want = dict((n, i) for i, (n, _u) in enumerate(STANDARD))
            base_par = [bp for bn, bp, _h in base_vbn if bn == s4][0]
            assert (pi == -1 and base_par in (-1, 0x0FFFFFFF)) or pi == base_par, (s4, p, base_par, want)
            index[u] = len(out)
            out.append([s4, pi, base_hash[s4], chain + [u]])
        # the rest, parents first (Ultimate's order otherwise); the folded ones under their parent;
        # bones nothing is skinned to or hangs from left out (keep)
        rest = [u for u in self.ult_names if u not in index and (keep is None or u in keep)]
        while rest:
            for u in list(rest):
                p = upar[u]
                while p in FOLD and p not in index:
                    p = upar[p]
                if p is None or p in index:
                    if upar[u] in FOLD and upar[u] not in index:
                        continue
                    index[u] = len(out)
                    out.append([u, index[p] if p is not None else -1, zlib.crc32(u.encode()) & 0xFFFFFFFF, [u]])
                    rest.remove(u)
            assert len(set(h for _n, _p, h, _c in out)) == len(out), 'bone hash collision'
        self.bones = out
        self.index = index
        self.by_name = {b[0]: i for i, b in enumerate(out)}

    def local(self, i, ult_local=None):
        """bone i's local matrix (column vectors) from Ultimate locals (default: the bind's)"""
        loc = ult_local or self.ult_local
        m = np.eye(4)
        for u in self.bones[i][3]:
            m = m @ loc[u]
        return m

    def world(self, ult_local=None):
        w = []
        for i, b in enumerate(self.bones):
            m = self.local(i, ult_local)
            w.append(m if b[1] < 0 else w[b[1]] @ m)
        return w

    def vbn(self):
        """little-endian model.vbn as the game's fighters' (' NBV', 2, 1), every bone type 0"""
        n = len(self.bones)
        out = struct.pack('<4sHHI4I', b' NBV', 2, 1, n, n, 0, 0, 0)
        for name, parent, h, _c in self.bones:
            out += name.encode()[:63].ljust(64, b'\0') + struct.pack('<IiI', 0, 0x0FFFFFFF if parent < 0 else parent, h)
        for i in range(n):
            t, r, s = decompose(self.local(i))
            out += struct.pack('<9f', *t, *euler_of(r), *s)
        return out

    def add_joint_bones(self, base_jtb, base_vbn, standins=None, only=None):
        """the bones of the base's joint table 1 (the ones its own code drives: Robin's / Pit's
        FaceN, Pit's wings, Orbitars and bow) we have no bone or stand-in for: leaf bones of their
        own (the base's name, at the nearest kept bone above, no chain: the identity), so what the
        game does to them moves nothing of ours (stood in by HeadN, the game's own turns of FaceN
        pulled the head off the neck). Their hashes are new ones (CRC32 of "<name>#jtb"), not the
        base's: the base's motion pacs (pitpt1.pac: Pit's wings, Orbitars, bow) animate those, and
        Steve with them bound didn't animate at all and crashed jumping. only: these names only (the
        profile's own_joints; the rest stood in as before). Returns their names."""
        standins = JOINT_STANDINS if standins is None else standins
        added = []
        names = [n for n, _p, _h in base_vbn]
        for name in joint_bone_names(base_jtb, base_vbn):
            if name in self.by_name or standins.get(name) in self.index or only is not None and name not in only:
                continue
            b = names.index(name)
            while base_vbn[b][0] not in self.by_name:
                b = base_vbn[b][1]
            self.bones.append([name, self.by_name[base_vbn[b][0]], zlib.crc32((name + '#jtb').encode()) & 0xFFFFFFFF, []])
            self.by_name[name] = len(self.bones) - 1
            added.append(name)
        assert len(set(h for _n, _p, h, _c in self.bones)) == len(self.bones), 'bone hash collision'
        return added

    def jtb(self, base_jtb, base_vbn, standins=None, extra=()):
        """the base's joint table with each bone index moved to ours (same name, else a stand-in,
        else the nearest standard bone above it in the base's skeleton)"""
        standins = JOINT_STANDINS if standins is None else standins
        d = base_jtb
        n1, n2 = struct.unpack('>HH', d[:4])
        vals = list(struct.unpack('>%dh' % (n1 + n2), d[4:4 + 2 * (n1 + n2)]))
        out = []
        for v in vals:
            name = base_vbn[v][0]
            if name in self.by_name:
                out.append(self.by_name[name])
            else:
                stand = standins.get(name)
                if stand in self.index:
                    out.append(self.index[stand])
                    continue
                b = v
                while base_vbn[b][0] not in self.by_name:
                    b = base_vbn[b][1]
                out.append(self.by_name[base_vbn[b][0]])
        # extra joints (bones the moves' scripts name, e.g. Squirtle's tail): appended to table 1, so
        # ACMD joint ID 1000 + n2 + k is extra[k] (a bone this costume lacks: its nearest kept
        # ancestor). Table 0 stays at its 26 (every vanilla fighter's): appended there (Sephiroth's
        # swords, test 20; Squirtle's tail, v2) hitboxes on them hit the whole stage and the tail drew
        # stretched to the stage's origin. Table 1's length differs per fighter (Mario 2, Pit 15) and
        # vanilla hitboxes use its joints (Robin's SwordN, joint 1000)
        add = []
        for name in extra:
            u = name
            while u not in self.index:
                u = self.ult_parent[u]
            add.append(self.index[u])
        t0, t1 = out[:n1], out[n1:] + add
        return struct.pack('>HH', n1, len(t1)) + struct.pack('>%dh' % len(t0 + t1), *(t0 + t1)) + d[4 + 2 * len(vals):]


OWN_JOINTS = None           # --own-joints (None: the profile's own_joints)


class _All:
    def __contains__(self, _name):
        return True


ALL_JOINTS = _All()


def joint_bone_names(base_jtb, base_vbn):
    """the base bones model.jtb's table 1 names (IDs 1000 + n)"""
    n1, n2 = struct.unpack('>HH', base_jtb[:4])
    vals = struct.unpack('>%dh' % (n1 + n2), base_jtb[4:4 + 2 * (n1 + n2)])
    return [base_vbn[v][0] for v in vals[n1:]]


def joint_bone_budget(src_dirs, base_jtb, base_vbn, standins, max_bones, only=None):
    """max_bones less the joint table's bones of their own to come (Skeleton.add_joint_bones), so
    the skeleton stays within max_bones"""
    if not max_bones:
        return max_bones
    import ssbh_data_py as s
    names = set()
    for d in src_dirs:
        names |= set(b.name for b in s.skel_data.read_skel(d + '/model.nusktb').bones)
    return max_bones - sum(1 for n in joint_bone_names(base_jtb, base_vbn)
                           if n not in names and standins.get(n) not in names and (only is None or n in only))


def needed_bones(src_dirs, standins=None, max_bones=None, animated=None, protect=()):
    """the Ultimate bones a Smash 4 skeleton needs: those the meshes of src_dirs are skinned or bound
    to, the standard ones, the shoulder pad helpers (the joint table's stand-ins), their ancestors.
    max_bones: merge bones into their parents until that many are left (the game's fighters go up to
    138 bones; past that it misdraws or crashes): leaves only, first the ones no motion moves
    (animated: the set of bones that do; merging those is exact), then the ones with the fewest
    vertices; never the standard bones, the stand-ins, the folded ones or protect (e.g. the swords)"""
    import ssbh_data_py as s
    standins = JOINT_STANDINS if standins is None else standins
    need = set(u for _s4, u in STANDARD) | set(standins.values())
    par = {}
    verts = {}
    for d in src_dirs:
        sk = s.skel_data.read_skel(d + '/model.nusktb')
        par.update({b.name: (sk.bones[b.parent_index].name if b.parent_index is not None else None) for b in sk.bones})
        for o in s.mesh_data.read_mesh(d + '/model.numshb').objects:
            if o.bone_influences:
                for bi in o.bone_influences:
                    n = sum(1 for w in bi.vertex_weights if w.vertex_weight > 0)
                    if n:
                        need.add(bi.bone_name)
                        verts[bi.bone_name] = verts.get(bi.bone_name, 0) + n
            elif o.parent_bone_name:
                need.add(o.parent_bone_name)
                verts[o.parent_bone_name] = verts.get(o.parent_bone_name, 0) + (len(o.positions[0].data) if o.positions else 0)
    for n in list(need) + list(protect):
        p = par.get(n)
        if n in par:
            need.add(n)
        while p:
            need.add(p)
            p = par.get(p)
    if max_bones and len(need) > max_bones:
        fixed = set(u for _s4, u in STANDARD) | set(standins.values()) | set(FOLD) | set(protect)

        def depth(u):
            k = 0
            while par.get(u):
                u, k = par[u], k + 1
            return k
        while len(need) > max_bones:
            has_child = {par.get(u) for u in need}
            leaves = [u for u in need if u not in has_child and u not in fixed]
            if not leaves:
                break
            leaves.sort(key=lambda u: (animated is None or u in animated, verts.get(u, 0), -depth(u), u))
            need.discard(leaves[0])
    return need


def animated_bones(motion_dir, src_model, cache=None):
    """the Ultimate bones some motion of motion_dir moves away from their bind (or a helper
    constraint turns); cache: a JSON file to keep the answer in"""
    import json
    import ssbh_data_py as s
    if cache and os.path.exists(cache):
        return set(json.load(open(cache)))
    sk = s.skel_data.read_skel(src_model + '/model.nusktb')
    bind = {b.name: np.array(b.transform, dtype=np.float64).T for b in sk.bones}
    moved = set(c.target_bone_name for c in helper_constraints(src_model))
    for f in sorted(os.listdir(motion_dir)):
        if not f.endswith('.nuanmb'):
            continue
        anim = s.anim_data.read_anim(os.path.join(motion_dir, f))
        frames = int(round(anim.final_frame_index)) + 1
        tracks, _vis = ult_tracks(anim, frames)
        for name, m in tracks.items():
            if name in moved:
                continue
            ref = bind.get(name, m[0])
            if not np.allclose(m, ref[None], atol=1e-4):
                moved.add(name)
    if cache:
        json.dump(sorted(moved), open(cache, 'w'))
    return moved


def read_vbn(path):
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    n = struct.unpack(e + 'I', d[8:12])[0]
    out = []
    for i in range(n):
        o = 28 + 76 * i
        name = d[o:o + 64].split(b'\0')[0].decode()
        _t, p, h = struct.unpack(e + 'IiI', d[o + 64:o + 76])
        out.append((name, p, h))
    return out


# ---------------------------------------------------------------- textures
def pow2(v, top=1024):
    return min(top, max(16, 1 << (int(v) - 1).bit_length() if v & (v - 1) else v))


def resized(img, w, h):
    from PIL import Image
    if img.shape[1] == w and img.shape[0] == h:
        return img
    if img.ndim == 2:
        return np.asarray(Image.fromarray(img).resize((w, h), Image.LANCZOS))
    # channel by channel: Pillow resizes RGBA premultiplied by alpha, which wipes the other channels
    # of data maps (PRM: specular in alpha, ~0 on Sephiroth's sword and coat, so its AO came out as
    # noise; normal maps: AO in alpha)
    return np.dstack([np.asarray(Image.fromarray(np.ascontiguousarray(img[..., c])).resize((w, h), Image.LANCZOS))
                      for c in range(img.shape[2])])


def bleed(img, steps=24):
    """the colors of the cut-out (alpha < 128) texels replaced by their opaque neighbours', spread
    outwards step by step (BC7 leaves noise there, which an opaque material or filtering shows)"""
    rgb = img[..., :3].copy()
    known = img[..., 3] >= 128
    for _ in range(steps):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(known.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(known, (dy, dx), (0, 1))
            acc += np.roll(rgb, (dy, dx), (0, 1)) * k[..., None]
            cnt += k
        grow = ~known & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    out = img.copy()
    out[..., :3] = rgb
    return out


class Textures:
    def __init__(self, src, base_id):
        self.src, self.base_id = src, base_id
        self.ids, self.images = {}, []
        self.extra = []                 # other folders to find textures in (held article models)
        self.cache = {}                 # values measured from textures (reflectance)

    def load(self, name):
        for d in [self.src] + self.extra:
            for n in (name, name.lower()):
                p = os.path.join(d, n + '.nutexb')
                if os.path.exists(p):
                    return nutexb.decode(nutexb.Nutexb(p))
        raise FileNotFoundError(name)

    def add(self, key, img, top=1024):
        if key not in self.ids:
            h, w = img.shape[:2]
            if PIXEL_ART and max(w, h) < PIXEL_ART:
                # pixel art (Steve's 64 x 64 skins): blown up with nearest pixels so the game's linear
                # filtering and BC blocks don't blur it (as tools/minecraft_world.py does for blocks)
                k = PIXEL_ART // max(w, h)
                img = np.repeat(np.repeat(img, k, axis=0), k, axis=1)
                h, w = img.shape[:2]
            img = resized(img, pow2(w, top), pow2(h, top))
            self.ids[key] = self.base_id + len(self.ids)
            self.images.append((self.ids[key], img))
        return self.ids[key]

    def color(self, col, prm=None, emi=None, gain=(1.0, 1.0, 1.0)):
        """the colour map times the material's colour gain, with the emissive map over it; the
        ambient occlusion (PRM blue) baked in only when given a PRM (no normal map to carry it)"""
        key = ('col', col, prm, emi, tuple(gain))
        if key in self.ids:
            return self.ids[key]
        img = self.load(col).astype(np.float64)
        img[..., :3] *= np.asarray(gain, np.float64)
        if prm:
            p = resized(self.load(prm), img.shape[1], img.shape[0]).astype(np.float64)
            ao = p[..., 2:3] / 255
            img[..., :3] *= 0.45 + 0.55 * ao
        if emi:
            e = resized(self.load(emi), img.shape[1], img.shape[0]).astype(np.float64)
            img[..., :3] = np.maximum(img[..., :3], e[..., :3])
        if (img[..., 3] < 128).any():
            img = bleed(img)
        return self.add(key, np.clip(np.round(img), 0, 255).astype(np.uint8))

    def reflectance(self, prm):
        """the PRM's mean F0 (0.16 spec^2, alpha) against a plain dielectric's 0.04, at most 1"""
        key = ('refl', prm)
        if key not in self.cache:
            spec = self.load(prm)[..., 3].astype(np.float64) / 255
            self.cache[key] = float(min(1.0, (0.16 * spec * spec).mean() / 0.04))
        return self.cache[key]

    def normal(self, nor, prm=None):
        key = ('nor', nor, prm)
        if key in self.ids:
            return self.ids[key]
        src = self.load(nor).astype(np.float64)
        x, y = src[..., 0] / 127.5 - 1, src[..., 1] / 127.5 - 1
        z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
        img = np.empty(src.shape, np.float64)
        img[..., 0], img[..., 1], img[..., 2] = src[..., 0], src[..., 1], (z + 1) * 127.5
        img[..., 3] = 128
        if prm:
            # Smash 4 reads the normal map's alpha as ambient occlusion (gamma 2.2, floored by
            # NU_aoMinGain; it also masks specular and rim): Ultimate's AO (PRM blue), so the shader
            # sees the same value
            p = resized(self.load(prm), img.shape[1], img.shape[0]).astype(np.float64)
            img[..., 3] = 255 * (p[..., 2] / 255) ** (1 / 2.2)
        return self.add(key, np.clip(np.round(img), 0, 255).astype(np.uint8))

    def eye(self, white, iris, part):
        """the white with the iris drawn on it through the second UV set (part: map1, uvSet, idx)"""
        key = ('eye', white, iris)
        if key in self.ids:
            return self.ids[key]
        w = self.load(white).astype(np.float64)
        ir = self.load(iris).astype(np.float64)
        h, wd = w.shape[:2]
        uv1, uv2, tri = part
        ys, xs = np.mgrid[0:h, 0:wd]
        px = np.c_[(xs.ravel() + 0.5) / wd, (ys.ravel() + 0.5) / h]
        for a, b, c in tri.reshape(-1, 3):
            p0, p1, p2 = uv1[a], uv1[b], uv1[c]
            # the white repeats (Squirtle's map1 V runs -1.85..-1.15): draw in the [0, 1) tile
            o = np.floor(np.minimum(np.minimum(p0, p1), p2))
            p0, p1, p2 = p0 - o, p1 - o, p2 - o
            lo, hi = np.minimum(np.minimum(p0, p1), p2), np.maximum(np.maximum(p0, p1), p2)
            sel = np.where((px[:, 0] >= lo[0]) & (px[:, 0] <= hi[0]) & (px[:, 1] >= lo[1]) & (px[:, 1] <= hi[1]))[0]
            if not len(sel):
                continue
            m = np.array([[p1[0] - p0[0], p2[0] - p0[0]], [p1[1] - p0[1], p2[1] - p0[1]]])
            if abs(np.linalg.det(m)) < 1e-12:
                continue
            l12 = np.linalg.solve(m, (px[sel] - p0).T).T
            inside = (l12[:, 0] >= -1e-4) & (l12[:, 1] >= -1e-4) & (l12.sum(1) <= 1 + 1e-4)
            sel, l12 = sel[inside], l12[inside]
            q = uv2[a] + l12[:, :1] * (uv2[b] - uv2[a]) + l12[:, 1:] * (uv2[c] - uv2[a])
            qx = np.clip((q[:, 0] % 1.0) * ir.shape[1], 0, ir.shape[1] - 1).astype(int)
            qy = np.clip((q[:, 1] % 1.0) * ir.shape[0], 0, ir.shape[0] - 1).astype(int)
            s = ir[qy, qx]
            al = s[:, 3:4] / 255
            yy, xx = sel // wd, sel % wd
            w[yy, xx, :3] = w[yy, xx, :3] * (1 - al) + s[:, :3] * al
        return self.add(key, np.clip(np.round(w), 0, 255).astype(np.uint8))

    def nut(self):
        return nut.write_ntwu([(i, 0x33 if (img[..., 3] < 250).any() else 0x31, img) for i, img in self.images])


# ---------------------------------------------------------------- meshes
# The base's (Zelda's) mesh slots, in its order, and the Ultimate meshes that go into each
# (the moi's VIS flag says which ones the material animations toggle)
MESH_SLOTS = [
    ('skirt_VIS_O_OBJ16', ['edge_swordL_VIS_O_OBJShape']),
    ('group127_O_OBJ', ['def_highShape', 'leg_highShape', 'GamemodelShape', 'hair_frontShape', 'leg_cShape06']),
    ('polySurface5817_VIS_O_OBJ', ['edge_swordR_VIS_O_OBJShape']),
    ('polySurface588_O_OBJ_O_SORTEACHNODE', ['edge_hair_VIS_O_OBJShape']),
    ('Zelda_eye_VIS_O_OBJ', ['edge_Eye_VIS_O_OBJShape']),
    ('Zelda_Openblink_Eye_VIS_O_OBJ', ['edge_Openblink_VIS_O_OBJShape']),
    ('Zelda_Halfblink1_Eye_VIS_O_OBJ', ['edge_Halfblink1_VIS_O_OBJShape']),
    ('Zelda_Halfblink_Eye_VIS_O_OBJ', ['edge_Halfblink2_VIS_O_OBJShape']),
    ('Zelda_Halfblink2_Eye_VIS_O_OBJ', ['edge_Halfblink2_VIS_O_OBJShape']),
    ('Zelda_Blink_Eye_VIS_O_OBJ', ['edge_Blink_VIS_O_OBJShape']),
    ('Zelda_FaceN_Mouse_A_VIS_O_OBJ', ['edge_Mouth_FaceN_VIS_O_OBJShape']),
    ('Zelda_Talk_Eye_B_VIS_O_OBJ', ['edge_Blink_Talk_VIS_O_OBJShape']),
    ('Zelda_Talk_Mouse_B_VIS_O_OBJ', ['edge_Mouth_Talk_VIS_O_OBJShape']),
    ('Zelda_Ouch_Eye_C_VIS_O_OBJ', ['edge_Blink_Ouch_VIS_O_OBJShape']),
    ('Zelda_Ouch_Mouse_C_VIS_O_OBJ', ['edge_Mouth_Ouch_VIS_O_OBJShape']),
    ('Zelda_Down_Eye_C_VIS_O_OBJ', ['edge_Blink_Down_VIS_O_OBJShape']),
    ('Zelda_Down_Mouse_C_VIS_O_OBJ', ['edge_Mouth_Down_VIS_O_OBJShape']),
    ('Zelda_Heavytalk_Eye_B_VIS_O_OBJ', ['edge_Blink_Heavyhit_VIS_O_OBJShape']),
    ('Zelda_Capture_Eye_BC_VIS_O_OBJ', ['edge_Blink_Furafura_VIS_O_OBJShape']),
    ('Zelda_Heavyouch_Eye_C_VIS_O_OBJ', ['edge_Blink_Heavyouch_VIS_O_OBJShape']),
    ('Zelda_Ottotto_Eye_VIS_O_OBJ', ['edge_Blink_Ottotto_VIS_O_OBJShape']),
    ('Zelda_Ottotto_Mouth_D_VIS_O_OBJ', ['edge_Mouth_Furafura_VIS_O_OBJShape']),
    ('Zelda_Cliff_Mouse_B_VIS_O_OBJ', ['edge_Mouth_Heavyattack_VIS_O_OBJShape']),
    ('Zelda_PatternA_Mouth_VIS_O_OBJ', ['edge_Mouth_PatternA_VIS_O_OBJShape']),
    ('Zelda_Hot_VIS_O_OBJ', ['edge_Hot_VIS_O_OBJShape']),
    ('Zelda_DamageFlyFront_VIS_O_OBJ', ['edge_wing_VIS_O_OBJShape']),
    ('group123_O_OBJ', []),
    ('group124_O_OBJ', []),
    ('group125_O_OBJ', []),
    ('group126_O_OBJ', []),
    ('group128_O_OBJ', []),
    ('full_hand', []),
]
# Ultimate mesh -> the base slot whose visibility it takes; ULTIMATE_VIS says which Ultimate
# visibility name drives each slot when the motions are converted
SLOT_OF = {u: s for s, us in MESH_SLOTS for u in us}


def mesh_parts(src):
    import ssbh_data_py as s
    mesh = s.mesh_data.read_mesh(src + '/model.numshb')
    modl = s.modl_data.read_modl(src + '/model.numdlb')
    matl = {e.material_label: e for e in s.matl_data.read_matl(src + '/model.numatb').entries}
    label = {(e.mesh_object_name, e.mesh_object_subindex): e.material_label for e in modl.entries}
    out = {}
    for o in mesh.objects:
        n = len(o.positions[0].data)
        uvs = {t.name: np.array(t.data, dtype=np.float64)[:, :2] for t in o.texture_coordinates}
        p = dict(name=o.name, sub=o.subindex, n=n,
                 pos=np.array(o.positions[0].data, dtype=np.float64)[:, :3],
                 nrm=np.array(o.normals[0].data, dtype=np.float64)[:, :3],
                 tan=np.array(o.tangents[0].data, dtype=np.float64) if o.tangents else None,
                 uvs=uvs, idx=np.array(o.vertex_indices, dtype=np.int64),
                 parent=o.parent_bone_name,
                 infl=[(b.bone_name, [(w.vertex_index, w.vertex_weight) for w in b.vertex_weights])
                       for b in o.bone_influences],
                 mat=matl[label[(o.name, o.subindex)]])
        out.setdefault(o.name, []).append(p)
    return out


def skin(part, sk, world):
    """positions / normals / tangents in bind space, 4 bone indices and byte weights a vertex"""
    n = part['n']
    pos, nrm = part['pos'], part['nrm']
    tan = part['tan'][:, :3] if part['tan'] is not None else np.cross(nrm, [0, 1, 0])
    sign = part['tan'][:, 3:4] if part['tan'] is not None else np.ones((n, 1))
    idx = np.zeros((n, 4), np.int64)
    wt = np.zeros((n, 4))
    def kept(u):
        while u not in sk.index:
            u = sk.ult_parent[u]
        # no vertex on TransN / RotN (no vanilla fighter has any; the model's bone range starts at HipN)
        return sk.index[u] if sk.index[u] >= 2 else sk.by_name['HipN']
    if not part['infl']:
        b = kept(part['parent'])
        m = world[b]
        pos = (np.c_[pos, np.ones(n)] @ m.T)[:, :3]
        nrm = nrm @ m[:3, :3].T
        tan = tan @ m[:3, :3].T
        idx[:, 0], wt[:, 0] = b, 1.0
    else:
        per = [{} for _ in range(n)]
        for bone, ws in part['infl']:
            b = kept(bone)
            for v, w in ws:
                per[v][b] = per[v].get(b, 0.0) + w
        for v, d in enumerate(per):
            lst = sorted(((w, b) for b, w in d.items()), reverse=True)
            lst = lst[:4] or [(1.0, sk.by_name['HipN'])]
            for k, (w, b) in enumerate(lst):
                idx[v, k], wt[v, k] = b, w
    nrm = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
    tan = tan - nrm * (tan * nrm).sum(1, keepdims=True)
    tan = tan / (np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9)
    bit = np.cross(nrm, tan) * sign
    # byte weights summing to 255
    wt = wt / np.maximum(wt.sum(1, keepdims=True), 1e-9)
    bw = np.floor(wt * 255).astype(np.int64)
    bw[:, 0] += 255 - bw.sum(1)
    idx = np.where(bw == 0, idx[:, :1], idx)
    return pos, nrm, tan, bit, idx, bw


def material_for(tex, mat, tmpl, part):
    tx = {str(t.param_id).split('.')[-1].split(':')[0]: t.data for t in mat.textures}
    blend = any(b.data.destination_color.name != 'Zero' for b in mat.blend_states)
    if 'Texture14' in tx and 'Texture0' not in tx:          # the eyes' glint layers: drawn as the white
        tx = {'Texture0': tx.get('Texture5', tx['Texture14'])}
    if 'Texture1' in tx and 'uvSet' in part['uvs']:
        col = tex.eye(tx['Texture0'], tx['Texture1'], (part['uvs']['map1'], part['uvs']['uvSet'], part['idx']))
    else:
        # CustomVector8 / 13: Ultimate's colour / diffuse gain (his def_edge_005: 0.588)
        vec = {str(v.param_id).split('.')[-1].split(':')[0]: v.data for v in mat.vectors}
        gain = [a * b for a, b in zip(vec.get('CustomVector8', [1.0] * 3)[:3], vec.get('CustomVector13', [1.0] * 3)[:3])]
        col = tex.color(tx['Texture0'], None if 'Texture4' in tx else tx.get('Texture6'), tx.get('Texture5'), gain)
    nor = tex.normal(tx['Texture4'], tx.get('Texture6')) if 'Texture4' in tx else None
    # Ultimate's skin (subsurface: CustomVector30 / 11) -> the base's skin material, eyes aside
    skin = ('skin' in tmpl and not blend and any('CustomVector30' in str(v.param_id) for v in mat.vectors)
            and not mat.material_label.lower().startswith('eye'))
    m = (tmpl['skin'] if skin else tmpl['blend'] if blend else tmpl['opaque']).copy()
    if not blend and 'punchthrough' in mat.material_label.lower():
        m.alpha_func, m.ref_alpha = 518, 128             # alpha-tested (fur cards), as stage cut-outs

    m.textures[0]['hash'] = col
    if nor is not None:
        m.textures[1]['hash'] = nor
    else:
        m.textures[1]['hash'] = col
    # Ultimate's own wrap modes (NUD: 1 repeat, 2 mirror, 3 clamp), not the base's: female Robin's
    # body clamps U, and Hero's mirrored halves (Erdrick's leg, Eight's sleeves: U < 0) took the
    # texture's dark edge
    wrap = {}
    for sm in mat.samplers:
        n = str(sm.param_id).split('.')[-1].split(':')[0]
        wrap[n] = [{'Repeat': 1, 'MirroredRepeat': 2}.get(w.name, 3) for w in (sm.data.wraps, sm.data.wrapt)]
    for t, n in zip(m.textures[:2], ('Sampler0', 'Sampler4' if nor is not None else 'Sampler0')):
        if n in wrap:
            t['wrap_s'], t['wrap_t'] = wrap[n]
    bits, val = float_hash(mat.material_label)
    m.props = [(n, ([val, 0.0, 0.0, 0.0] if n == 'NU_materialHash' else v)) for n, v in m.props]
    if skin:
        # the base's skin is human (Mario's: rim (0.96, 0.57, 0.57) x 1.5, specular (1, 0.67, 0.55), AO floor
        # (0.58, 0.32, 0.18), a ramp going red into the shadow): its tints from Ultimate's own instead,
        # the subsurface colour (CustomVector11: Squirtle's body blue, his shell brown) for the AO floor
        # and the ramp (skin_ramp below), the rim colour (CustomVector14) for the rim, a neutral
        # specular; each keeps the base's brightness. Squirtle in Mario's came out pale (user, v1)
        vec = {str(v.param_id).split('.')[-1].split(':')[0]: v.data for v in mat.vectors}
        sss = vec.get('CustomVector11', [0.25, 0.02, 0.01])[:3]
        rim = vec.get('CustomVector14', [1.0, 1.0, 1.0])[:3]
        m.sss = tuple(round(x, 4) for x in sss)

        def lum(c):
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        hue = [x / max(lum(sss), 1e-4) for x in sss]
        tint = {'NU_fresnelColor': rim, 'NU_specularColor': [1.0, 1.0, 1.0], 'NU_aoMinGain': hue}
        m.props = [(n, ([min(1.0, lum(v[:3]) * t) for t in tint[n]] + list(v[3:]) if n in tint else v))
                   for n, v in m.props]
    if not skin and 'Texture6' in tx and 'eye' not in mat.material_label.lower():
        # the base's specular and rim (added over the colour whatever it is: Zelda's white x2, a broad
        # lobe, rim 0.91) scaled by Ultimate's reflectance, F0 = 0.16 spec^2 (PRM alpha), against a
        # plain surface's 0.04 (spec 0.5): Sephiroth's coat (spec 0.08: 1/40) was a light grey sheen.
        # Floors keep some of both (the rim outlines him on dark stages); the eyes keep their glint
        k = tex.reflectance(tx['Texture6'])
        scale = {'NU_specularColor': max(k, 0.1), 'NU_fresnelColor': max(k ** 0.5, 0.35)}
        m.props = [(n, ([x * scale[n] for x in v[:3]] + list(v[3:]) if n in scale else v)) for n, v in m.props]
    return m


def float_hash(name):
    bits = 0x45800000 | (zlib.crc32(name.encode()) & 0x7FFFFF)
    return bits, struct.unpack('>f', struct.pack('>I', bits))[0]


def templates(base_nud):
    """the base's skinned body material (0x9A011063: color, normal, ramp) opaque and alpha-blended,
    and its skin material when it has one (0x9A211067, Zelda's face and arms: color, normal, a skin
    ramp, the ramp; warm rim, specular and AO floor)"""
    out = {}
    for m in base_nud:
        for p in m.polygons:
            for mt in p.materials:
                if 'opaque' not in out and mt.flags in (0x9A011063, 0x9A013063) and mt.src == 0 and len(mt.textures) == 3:
                    out['opaque'] = mt.copy()
                    out['blend'] = mt.copy()
                    out['blend'].src, out['blend'].dst = 1, 1
                if 'skin' not in out and mt.flags == 0x9A211067 and mt.src == 0 and len(mt.textures) == 4:
                    out['skin'] = mt.copy()
    if 'opaque' not in out:
        raise SystemExit('no 0x9A011063 material in the base')
    return out


def empty_polygon(tmpl):
    p = nud.Polygon()
    p.pos = np.zeros((3, 3))
    p.nrm = np.tile([0.0, 1.0, 0.0], (3, 1))
    p.tan = np.tile([1.0, 0.0, 0.0], (3, 1))
    p.bit = np.tile([0.0, 0.0, 1.0], (3, 1))
    p.bones = np.full((3, 4), 2, np.int64)      # HipN: no vertex on TransN / RotN (the header's bone range)
    p.weights = np.tile([255, 0, 0, 0], (3, 1))
    p.uvs = [np.zeros((3, 2))]
    p.col = np.full((3, 4), WHITE)
    p.idx = np.array([0, 1, 2])
    p.materials = [tmpl['opaque'].copy()]
    return p


def build_model(src, base, out, tex_id=TEX_ID, log=print, joints=(), max_bones=None, animated=None):
    import ssbh_data_py as s
    base_vbn = read_vbn(base + '/model.vbn')
    base_nud = nud.read(base + '/model.nud')
    pname, prof = profile_for(m.name for m in base_nud)
    base_jtb = open(base + '/model.jtb', 'rb').read()
    sk = Skeleton(s.skel_data.read_skel(src + '/model.nusktb'), base_vbn,
                  needed_bones([src], prof['joints'], joint_bone_budget([src], base_jtb, base_vbn, prof['joints'], max_bones, OWN_JOINTS or prof.get('own_joints')),
                               animated, joints))
    own = sk.add_joint_bones(base_jtb, base_vbn, prof['joints'], OWN_JOINTS or prof.get('own_joints'))
    world = sk.world()
    parts = mesh_parts(src)
    tmpl = templates(base_nud)
    tex = Textures(src, tex_id)
    # "<article>/<mesh>@<bone>": an article model's mesh held rigidly on a fighter bone (Steve's tools:
    # Ultimate links the article's root bone to the hand's, so the mesh's own positions are relative
    # to that bone), from the article's folder of the same costume; its textures from there too
    for slot, ults in prof['slots']:
        for u in ults:
            if '/' not in u or u in parts:
                continue
            art, rest = u.split('/', 1)
            mname, bone = rest.split('@')
            adir = os.path.join(src, '..', '..', art, os.path.basename(os.path.normpath(src)))
            if not os.path.exists(adir + '/model.numshb'):
                continue
            tex.extra.append(adir)
            for part in mesh_parts(adir).get(mname, []):
                part['parent'], part['infl'] = bone, []
                parts.setdefault(u, []).append(part)
    meshes = []
    used = set()
    for slot, ults in prof['slots']:
        polys = []
        for u in ults:
            for part in parts.get(u, []):
                used.add(u)
                pos, nrm, tan, bit, idx, bw = skin(part, sk, world)
                p = nud.Polygon()
                p.pos, p.nrm, p.tan, p.bit, p.bones, p.weights = pos, nrm, tan, bit, idx, bw
                p.uvs = [part['uvs']['map1']]
                p.col = np.full((part['n'], 4), WHITE)
                p.idx = part['idx']
                p.materials = [material_for(tex, part['mat'], tmpl, part)]
                polys.append(p)
        meshes.append(nud.Mesh(slot, polys or [empty_polygon(tmpl)], bone=-1, bind=4))
    if 'skin' in tmpl:          # the skin ramp is the base's own texture: a copy in ours (one per subsurface
        base_ramp = tmpl['skin'].textures[2]['hash']        # colour, skin_ramp), numbered last
        base_img = base_texture(base + '/model.nut', base_ramp)
        for m in meshes:
            for p in m.polygons:
                mt = p.materials[0]
                for t in mt.textures[2:3]:
                    if mt.flags == 0x9A211067 and t['hash'] == base_ramp:
                        sss = getattr(mt, 'sss', None)
                        t['hash'] = tex.add(('skin ramp', sss), skin_ramp(base_img, sss), 256)
    left = sorted(set(parts) - used)
    log('profile %s; skeleton: %d bones (of %d Ultimate, %s folded; joint table bones of their own: %s); meshes: %d slots, '
        '%d Ultimate meshes used, left out: %s' % (pname, len(sk.bones), len(sk.ult_names), '/'.join(FOLD), ', '.join(own) or '-',
                                                 len(meshes), len(used), ', '.join(left)))
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(base):
        if os.path.isfile(os.path.join(base, f)):
            shutil.copy(os.path.join(base, f), os.path.join(out, f))
    if prof.get('vis'):
        # the base's own: the `motions` command writes this fighter's (the slots it drives, e.g. Hero's
        # shields); shipping these (Hero fix 70) hid them in every motion
        log('NOTE: material_anime_face / eyelid.pac here are the base\'s: ship the `motions` output\'s')
    open(out + '/model.vbn', 'wb').write(sk.vbn())
    open(out + '/model.jtb', 'wb').write(sk.jtb(base_jtb, base_vbn, prof['joints'], joints))
    open(out + '/model.nud', 'wb').write(nud.write(meshes, top_bone=len(sk.bones) - 1))
    # metal: the base's metal material on every polygon (its textures: the base's metal one, ours as normal)
    metal = nud.read(base + '/metal.nud')
    mm = next(p.materials[0] for m in metal for p in m.polygons if len(p.materials[0].textures) >= 4).copy()
    metal_tex = tex.add(('metal',), base_texture(base + '/model.nut', mm.textures[0]['hash']), 256)
    for m in meshes:
        for p in m.polygons:
            q = p.materials[0]
            mt = mm.copy()
            mt.textures[0]['hash'] = metal_tex
            mt.textures[2]['hash'] = q.textures[1]['hash']
            p.metal = [mt]
    open(out + '/metal.nud', 'wb').write(nud.write([nud.Mesh(m.name, [_with(p, p.metal) for p in m.polygons], -1, 4)
                                                     for m in meshes], top_bone=len(sk.bones) - 1))
    open(out + '/model.nut', 'wb').write(tex.nut())
    log('textures: %d (%s)' % (len(tex.images), ', '.join('0x%08X %dx%d' % (i, im.shape[1], im.shape[0])
                                                          for i, im in tex.images)))
    return sk


def _with(p, mats):
    q = nud.Polygon()
    q.__dict__.update(p.__dict__)
    q.materials = mats
    return q


def skin_ramp(img, sss):
    """the base's skin ramp (lit -> shadow along x) with its shadow tint turned to the subsurface colour
    sss: each texel = its luminance x (1 + w (hue - 1)), w its share of the base's most saturated tint,
    hue sss over its luminance scaled to the base tint's strength; None: the base's as it is"""
    if sss is None:
        return img
    f = img[..., :3].astype(np.float64) / 255
    L = f @ np.array([0.2126, 0.7152, 0.0722])
    T = f / np.maximum(L, 1e-3)[..., None] - 1                 # the tint, per texel
    ok = L > 0.02
    k = np.argmax(np.where(ok, np.linalg.norm(T, axis=-1), 0))
    hb = T.reshape(-1, 3)[k]                                   # the base's own tint (Mario's: red)
    w = np.clip((T @ hb) / (hb @ hb), 0, None) * ok
    h = np.array(sss, dtype=np.float64) / max(float(np.dot(sss, [0.2126, 0.7152, 0.0722])), 1e-4) - 1
    h *= np.linalg.norm(hb) / max(np.linalg.norm(h), 1e-6)
    out = img.copy()
    out[..., :3] = np.clip(np.round(L[..., None] * (1 + w[..., None] * h) * 255), 0, 255).astype(np.uint8)
    return out


def base_texture(path, tex_id):
    d, texs = nut.load(path)
    for t in texs:
        if t.tex_id == tex_id:
            return nut.decode(d, t)
    raise SystemExit('texture 0x%08X not in %s' % (tex_id, path))


# ---------------------------------------------------------------- motions
# the base's motion (its main.pac entry name without the FitXBodyMain prefix, lower case) ->
# the Ultimate motion that plays it, where the names differ
MOTION_STANDINS = {
    'a00wait4': 'a00wait3', 'a02runbrakel': 'a02runbraker', 'g02cliffattackquick': 'g02cliffattack',
    'g02cliffclimbquick': 'g02cliffclimb', 'g02cliffescapequick': 'g02cliffescape',
    'g02cliffjumpquick1': 'g02cliffjump1', 'g02cliffjumpquick2': 'g02cliffjump2',
    'f07furasleepend': 'f07sleepend', 'f07furasleeploop': 'f07sleeploop', 'f07furasleepstart': 'f07sleepstart',
    'f03downspotu': 'f04downspotd', 'j01appeallw': 'j01appeallwr',
    'h10itembrakeb': 'h10itemlegswalkb', 'h10itemlegsbrakeb': 'h10itemlegswalkb', 'h10itemlegsbrakef': 'h10itemlegswalkf',
    'h10itemlegsdashb': 'h10itemlegswalkb', 'h10itemlegsdashf': 'h10itemlegswalkf',
    'h10itemlegsfastb': 'h10itemlegswalkb', 'h10itemlegsfastf': 'h10itemlegswalkf',
    'h10itemlegsmiddleb': 'h10itemlegswalkb', 'h10itemlegsmiddlef': 'h10itemlegswalkf',
    'h10itemlegsslowb': 'h10itemlegswalkb', 'h10itemlegsslowf': 'h10itemlegswalkf', 'h10itemlegswait': 'a00wait1',
    # the base's specials -> Ultimate's (the moves themselves come later)
    'd00specialn': 'd00specialn1', 'd00specialairn': 'd00specialairn1',
    'd01specialsstart': 'd01specialsstart', 'd01specialsloop': 'd01specialshold', 'd01specialsend': 'd01specials',
    'd01specialairsstart': 'd01specialairsstart', 'd01specialairsloop': 'd01specialairshold',
    'd01specialairsend': 'd01specialairs',
    'd02specialhistart': 'd02specialhistart', 'd02specialhi': 'd02specialhi1',
    'd02specialairhistart': 'd02specialairhistart', 'd02specialairhi': 'd02specialhi1',
    'd03speciallw': 'd03speciallw', 'd03speciallwloop': 'd03speciallwhit', 'd03speciallwattack': 'd03speciallwend',
    'd03specialairlw': 'd03specialairlw', 'd03specialairlwloop': 'd03specialairlwhit',
    'd03specialairlwattack': 'd03specialairlwend',
    'd04final': 'd04finalstart', 'd04finalair': 'd04finalairstart',
}
# Ultimate visibility -> the mesh slot it drives (MESH_SLOTS); slots listed with None are always hidden
VIS_SLOTS = {'edge_swordL': 'skirt_VIS_O_OBJ16', 'edge_swordR': 'polySurface5817_VIS_O_OBJ'}
# other Ultimate meshes of the same thing: the slot shows while any of them does. Ultimate swaps the
# sword for its bright (or dark) copy during swings (forward smash: 45 of 106 frames); those copies
# aren't converted, so with the plain sword's track alone the sword vanished in attacks (test 22)
VIS_ALSO = {'edge_swordL': ('edge_brightswordL', 'edge_darkswordL'),
            'edge_swordR': ('edge_brightswordR', 'edge_darkswordR')}
HIDDEN_SLOTS = ('Zelda_DamageFlyFront_VIS_O_OBJ',)       # the wing (its own form, later)

# Bowser's mesh slots for Incineroar: Bowser's faces are whole-face meshes, so the open eyelids go
# with the body (always shown) and each mouth shape takes a face
_NAILS = ['gaogaen_handnail_%s%s_VIS_O_OBJShape' % (s, c) for s in 'LR' for c in 'ABCDE'] + \
         ['gaogaen_footnail_LA_VIS_O_OBJShape', 'gaogaen_footnail_RA_VIS_O_OBJShape']
KOOPA_SLOTS = [
    ('koopa_body_VIS_O_OBJ', ['GamemodelShape', 'gaogaen_fur_highShape', 'gaogaen_emissivefur_body_VIS_O_OBJShape',
                              'gaogaen_belt_highShape', 'gaogaen_Openblink_VIS_O_OBJShape'] + _NAILS),
    ('koopa_Eye_VIS_O_OBJ', ['gaogaen_Eye_VIS_O_OBJShape']),
    ('koopa_faceN_VIS_O_OBJ', ['gaogaen_FaceN_Mouth_VIS_O_OBJShape']),
    ('koopa_FaceOuchM_VIS_O_OBJ', ['gaogaen_Ouch_Mouth_VIS_O_OBJShape']),
    ('koopa_FaceTalkM_VIS_O_OBJ', ['gaogaen_Talk_Mouth_VIS_O_OBJShape']),
    ('koopa_FaceDownM_VIS_O_OBJ', ['gaogaen_Bound_Mouth_VIS_O_OBJShape']),
    ('koopa_AttackM_VIS_O_OBJ', ['gaogaen_Attack_Mouth_VIS_O_OBJShape']),
    ('koopa_Capture_VIS_O_OBJ', ['gaogaen_Capture_Mouth_VIS_O_OBJShape']),
    ('koopa_HeavyOuch_VIS_O_OBJ', ['gaogaen_HeavyOuch_Mouth_VIS_O_OBJShape']),
    ('koopa_Cliff_VIS_O_OBJ', ['gaogaen_Heavyattack_Mouth_VIS_O_OBJShape']),
    ('koopa_Furafura_VIS_O_OBJ', ['gaogaen_Furafura_Mouth_VIS_O_OBJShape']),
    ('koopa_Escape_VIS_O_OBJ', ['gaogaen_Escape_Mouth_VIS_O_OBJShape']),
    ('koopa_Ottotto_VIS_O_OBJ', ['gaogaen_Ottotto_Mouth_VIS_O_OBJShape']),
    ('koopa_NeckIron_VIS_O_OBJ', []),
    ('koopa_LhornsM_VIS_O_OBJ', []),
    ('koopa_RhornsM_VIS_O_OBJ', []),
    ('koopa_ArmIron_VIS_O_OBJ', []),
    ('koopa_HairA_VIS_O_OBJ', []),
    ('koopa_ShellBodyM_VIS_O_OBJ', []),
    ('koopa_ShellM1_VIS_O_OBJ', []),
    ('koopa_Harfblink1_VIS_O_OBJ', ['gaogaen_Halfblink_VIS_O_OBJShape']),
    ('koopa_Harfblink2_VIS_O_OBJ', ['gaogaen_Halfblink_VIS_O_OBJShape']),
    ('koopa_Blink_VIS_O_OBJ', ['gaogaen_Blink_VIS_O_OBJShape']),
    ('koopa_Shell_VIS_O_OBJ', []),
]
KOOPA_JOINTS = {'TailNa': 'Tail1', 'TailNb': 'Tail2', 'TailNc': 'Tail3', 'TailNd': 'Tail4',
                'LHornN': 'EarL', 'RHornN': 'EarR', 'LToe1stN': 'ToeL', 'LToe2ndN': 'ToeL', 'LToe3rdN': 'ToeL',
                'RToe1stN': 'ToeR', 'RToe2ndN': 'ToeR', 'RToe3rdN': 'ToeR'}
KOOPA_MOTIONS = {
    'd00specialnstart': 'd00specialn', 'd00specialnend': 'd00specialn',
    'd00specialairnstart': 'd00specialairn', 'd00specialairnend': 'd00specialairn',
    'd01specialssquat': 'd01specialsstart', 'd01specialscatch': 'd01specialslariat',
    'd01specialsaircatch': 'd01specialairslariat', 'd01specialsjump': 'd01specialsthrow',
    'd01specialsfall': 'd01specialairsthrow', 'd01specialslanding': 'd01specialsend',
    'd02specialhi': 'd02specialhistart', 'd02specialairhi': 'd02specialairhistart',
    'd03speciallw': 'd03speciallw', 'd03specialairlw': 'd03specialairlw', 'd03speciallwlanding': 'd03speciallwstart',
    'd04finalstart': 'd04finalstart', 'd04finalend': 'd04finalend',
    'd04finalairstart': 'd04finalairstart', 'd04finalairend': 'd04finalairend',
    'a05squatb': 'a05squat', 'a05squatf': 'a05squat', 'e01specialszitabata': 'e01thrownf',
    'e01specialsdxzitabata': 'e01throwndxf', 'e01specialsgirlzitabata': 'e01throwngirlf',
    'i00swimend': 'i00swimrise', 'i00swimf': 'i00swim', 'j01appealhi': 'j01appealhir', 'j01appeals': 'j01appealsr',
    'j00entry': 'j00entryr',
}
# Pit's mesh slots for Steve: his body is one mesh (the face is in its texture; the eyes open / shut
# are two small meshes); Pit's eyes, half blinks and expression eyes take one or the other; his
# mouths, wings, bow / weapons, bracelets, boots and blush are left empty. Steve's held items (flint,
# buckets, blocks ...) are left out
_PO, _PB = 'pickel_Openblink_VIS_O_OBJShape', 'pickel_Blink_VIS_O_OBJShape'
STEVE_MATERIAL = 'iron'
PIT_SLOTS = [
    ('Boot_HB15_O_OBJ', []), ('Boot_HB16_O_OBJ', []), ('Udewa19_O_OBJ2', []),
    # Pit's bow / blade slots: empty (his own code shows and hides them, model changers: Steve's tools
    # there showed the sword all the time and the others never)
    ('pit_YumiRM_VIS_O_OBJ', []), ('pit_WeaponRM_VIS_O_OBJ', []), ('pit_WpnNagiRM_VIS_O_OBJ', []),
    ('pit_WeaponLM_VIS_O_OBJ', []),
    ('pit_Arm_VIS_O_OBJ', []), ('pit_LBit_VIS_O_OBJ', []), ('pit_RBit_VIS_O_OBJ', []),
    ('polySurface287_O_OBJ', []), ('polySurface286_O_OBJ', []),
    ('Pit_Eye_VIS_O_OBJ', []), ('Pit_FaceN_VIS_O_OBJ', []),
    ('Pit_Openblink_VIS_O_OBJ', [_PO]),
    ('Pit_Halfblink05_VIS_O_OBJ', [_PO]), ('Pit_Halfblink1_VIS_O_OBJ', [_PO]),
    ('Pit_Halfblink15_VIS_O_OBJ', [_PB]), ('Pit_Halfblink2_VIS_O_OBJ', [_PB]), ('Pit_Halfblink25_VIS_O_OBJ', [_PB]),
    ('Pit_Blink_VIS_O_OBJ', [_PB]),
    ('Pit_Eye_Ouch_VIS_O_OBJ', [_PB]), ('Pit_Eye_Talk_VIS_O_OBJ', [_PO]), ('Pit_Eye_Down_VIS_O_OBJ', [_PB]),
    ('Pit_Eye_HeavyAttack_VIS_O_OBJ', [_PO]), ('Pit_Eye_Attack_VIS_O_OBJ', [_PO]), ('Pit_Eye_Capture_VIS_O_OBJ', [_PB]),
    ('Pit_Eye_Ottotto_VIS_O_OBJ', [_PO]), ('Pit_Eye_Furafura_VIS_O_OBJ', [_PB]), ('Pit_Eye_Catch_VIS_O_OBJ', [_PO]),
    ('Pit_Eye_Hot_VIS_O_OBJ', [_PO]),
    # his tools (Ultimate's articles, in the iron version: no material system yet) on his right hand, in
    # four of Pit's mouth slots (Steve has no mouths): shown only by the face material animations, by the
    # moves that hold them (PIT_TOOL_VIS)
    ('Pit_Mouth_Ouch_VIS_O_OBJ', ['axe/axe%s_VIS_O_OBJShape@HaveR' % STEVE_MATERIAL]),
    ('Pit_Mouth_Talk_VIS_O_OBJ', ['sword/sword%s_VIS_O_OBJShape@HaveR' % STEVE_MATERIAL]),
    ('Pit_Mouth_Down_VIS_O_OBJ', ['pick/pick%s_VIS_O_OBJShape@HaveR' % STEVE_MATERIAL]),
    ('Pit_Mouth_HeavyAttack_VIS_O_OBJ', ['shovel/shovel%s_VIS_O_OBJShape@HaveR' % STEVE_MATERIAL]),
    ('Pit_Mouth_Escape_VIS_O_OBJ', []), ('Pit_Mouth_Attack_VIS_O_OBJ', []),
    ('Pit_Mouth_Ottotto_VIS_O_OBJ', []), ('Pit_Mouth_Furafura_VIS_O_OBJ', []), ('Pit_Mouth_VoiceA_VIS_O_OBJ', []),
    ('Pit_Mouth_VoiceB_VIS_O_OBJ', []), ('Pit_Mouth_Catch_VIS_O_OBJ', []), ('Pit_Red_Capture_VIS_O_OBJ', []),
    ('Pit_Red_Hot_VIS_O_OBJ', []), ('Pit_Result_VIS_O_OBJ', []), ('Pit_Mouth_laugh_VIS_O_OBJ', []),
    ('pasted__R_hane_out3_N14_O_OBJ_O_SORTEACHNODE', []), ('pasted__R_hane_out3_N15_O_OBJ_O_SORTEACHNODE', []),
    ('L_Arm_VIS_O_OBJ', []), ('Udewa19_O_OBJ', []),
    ('Gamemodel', ['pickel_VIS_O_OBJ_NSCShape']),
]
# Pit's motions Steve has no animation for (his own kinds that share one resolve through his
# motion_list.bin first: motion_aliases); Pit's glide (unused in Smash 4) -> the Elytra
# Steve's tools: the visibility names tools/pickel_build.py writes (from his scripts' tool requests)
PIT_TOOL_VIS = {'tool_axe': 'Pit_Mouth_Ouch_VIS_O_OBJ', 'tool_sword': 'Pit_Mouth_Talk_VIS_O_OBJ',
                'tool_pick': 'Pit_Mouth_Down_VIS_O_OBJ', 'tool_shovel': 'Pit_Mouth_HeavyAttack_VIS_O_OBJ'}
# Steve's limb swing (Ultimate layers a01walk, his Minecraft walk cycle, over motions that only move his
# root): one cycle a walk (each is one stride), two in the run and the dash, at 0.6 through his jumps
# (they're still in Ultimate's files)
PIT_LAYERS = dict(
    [(w, [('a01walk', 1, 1.0)]) for w in ('a01walkslow', 'a01walkmiddle', 'a01walkfast')] +
    [(w, [('a01walkb', 1, 1.0)]) for w in ('a01walkbslow', 'a01walkbmiddle', 'a01walkbfast')] +
    [(r, [('a01walk', 2, 1.0)]) for r in ('a02run', 'a02dash')] +
    [(j, [('a01walk', 1, 0.6)]) for j in ('a03jumpf', 'a06stepjump')])
PIT_MOTIONS = {
    'a00wait2': 'a00wait1', 'a00wait3': 'a00wait1', 'a03jumpaerialf2': 'a03jumpf', 'a03jumpaerialf3': 'a03jumpf',
    'a04runfalll': 'a03jumpf', 'a04runfallr': 'a03jumpf', 'a04walkfalll': 'a03jumpf', 'a04walkfallr': 'a03jumpf',
    'a06stepfall': 'a03jumpf',
    'a07glidestart': 'd02specialairhistart', 'a07glidewing': 'd02specialairhi', 'a07glidedirection': 'd02specialairhi',
    'a07glideattack': 'd02specialairhimax', 'a07glideend': 'a03jumpf', 'a07glidelanding': 'd02specialairhilanding',
    'c00attack12': 'c00attack11', 'c00attack13': 'c00attack11', 'c00attack100start': 'c00attack11',
    'c00attack100': 'c00attack11', 'c00attackend': 'c00attack11',
    'd00specialnstart': 'd00specialn1', 'd00specialnholds': 'd00specialn1', 'd00specialnholdhi': 'd00specialn1',
    'd00specialnfires': 'd00specialn1', 'd00specialnfirehi': 'd00specialn1', 'd00specialnstos': 'd00specialn1',
    'd00specialnstohi': 'd00specialn1', 'd00specialnhitos': 'd00specialn1',
    'd00specialairnstart': 'd00specialairn3', 'd00specialairnholds': 'd00specialairn3',
    'd00specialairnholdhi': 'd00specialairn3', 'd00specialairnfires': 'd00specialairn3',
    'd00specialairnfirehi': 'd00specialairn3', 'd00specialairnstos': 'd00specialairn3',
    'd00specialairnstohi': 'd00specialairn3', 'd00specialairnhitos': 'd00specialairn3',
    'd01specialsend': 'd01specialsfailure', 'd01specialairsend': 'd01specialairsfailure',
    'd02specialhi': 'd02specialairhi', 'd02specialairhiend': 'd02specialairhilanding',
    'd03speciallwstartl': 'd03speciallw', 'd03speciallwstartr': 'd03speciallw',
    'd03speciallwendl': 'd03speciallwend', 'd03speciallwendr': 'd03speciallwend',
    'd03specialairlwstartl': 'd03specialairlw', 'd03specialairlwstartr': 'd03specialairlw',
    'd03specialairlwendl': 'd03specialairlwfailure', 'd03specialairlwendr': 'd03specialairlwfailure',
    'd04finalstartl': 'd04final', 'd04finalstartr': 'd04final', 'd04finalendl': 'd04finalend',
    'd04finalendr': 'd04finalend', 'd04finalairstartl': 'd04finalair', 'd04finalairstartr': 'd04finalair',
    'd04finalairendl': 'd04finalairend', 'd04finalairendr': 'd04finalairend',
    'j03appealsstartl': 'j01appealsr', 'j03appealsstartr': 'j01appealsr', 'j03appealsendl': 'j01appealsr',
    'j03appealsendr': 'j01appealsr',
    'k00laddercatchairl': 'k00laddercatchairr', 'k00laddercatchendl': 'k00laddercatchendr',
    'k00laddercatchl': 'k00laddercatchr',
}
# Robin's mesh slots for Hero: body, hand, sword and scabbard in her body slot (always shown: Hero keeps
# his sword out); the face meshes by expression; his hair (the other outfits') in hers; her swords and
# tome empty. His shield in hand and the one on his back go in her Final / Result mouths (never shown in
# battle), driven by Ultimate's brave_shield / brave_shieldb (REFLET_VIS: the back one in his smash
# charges, specials, Command Selection...). Not used: the sheathed hilt, the thrown sword, the low-detail meshes
REFLET_SLOTS = [
    ('bronzeswordM_VIS_O_OBJ', []), ('thunderswordM_VIS_O_OBJ', []), ('hair_O_OBJ_O_SORTEACHNODE', ['hair_highShape']),
    ('Reflet_Eye_VIS_O_OBJ', ['brave_Eye_VIS_O_OBJShape']),
    ('Reflet_Openblink_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Openblink_VIS_O_OBJShape']),
    ('Reflet_Mouth_FaceN_VIS_O_OBJ', ['brave_Mouth_FaceN_VIS_O_OBJShape']),
    ('Reflet_Halfblink_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Halfblink02_VIS_O_OBJShape']),
    ('Reflet_Blink_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_VIS_O_OBJShape']),
    ('Reflet_Blink_Talk_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_Talk_VIS_O_OBJShape']),
    ('Reflet_Mouth_Talk_VIS_O_OBJ', ['brave_Mouth_Talk_VIS_O_OBJShape']),
    ('Reflet_Mouth_Final_VIS_O_OBJ', ['brave_shield_VIS_O_OBJShape']),
    ('Reflet_Mouth_Outh_VIS_O_OBJ', ['brave_Mouth_Ouch_VIS_O_OBJShape']),
    ('Reflet_Blink_Outh_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_Ouch_VIS_O_OBJShape']),
    ('Reflet_Blink_Down_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_Down_VIS_O_OBJShape']),
    ('Reflet_Mouth_Down_VIS_O_OBJ', ['brave_Mouth_Down_VIS_O_OBJShape']),
    ('Reflet_Mouth_Heavyattack_VIS_O_OBJ', ['brave_Mouth_Heavyattack_VIS_O_OBJShape']),
    ('Reflet_Mouth_Escape_VIS_O_OBJ', ['brave_Mouth_VoiceB_VIS_O_OBJShape']),
    ('Reflet_Blink_Capture_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_Capture_VIS_O_OBJShape']),
    ('Reflet_Blink_Ottotto_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_Ottotto_VIS_O_OBJShape']),
    ('Reflet_Eye_Ottotto_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Eye_Ottotto_VIS_O_OBJShape']),
    ('Reflet_Mouth_Ottotto_VIS_O_OBJ', ['brave_Mouth_Ottotto_VIS_O_OBJShape']),
    ('Reflet_Blink_Furafura_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Blink_HeavyOuch_VIS_O_OBJShape']),
    ('Reflet_Mouth_VoiceA_VIS_O_OBJ', ['brave_Mouth_Attack_VIS_O_OBJShape']),
    ('Reflet_Mouth_Hot_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE', ['brave_Mouth_HeavyOuch_VIS_O_OBJShape']),
    ('Reflet_Mouth_Bound_VIS_O_OBJ', ['brave_Mouth_Bound_VIS_O_OBJShape1']),
    ('Reflet_Mouth_Result_VIS_O_OBJ', ['brave_shieldb_VIS_O_OBJShape']),
    ('Reflet_Hoho_Hot_VIS_O_OBJ', ['brave_Hot_VIS_O_OBJShape']),
    ('book_VIS_O_OBJ', []),
    ('fullhands', ['body_highShape', 'hand_L1_highShape', 'brave_sword_VIS_O_OBJShape', 'brave_scabbard_VIS_O_OBJShape',
                   # the other outfits' own pieces (capes, headdress, bandana, the slime, rings)
                   'Mantle_highShape', 'mant_emblam_highShape', 'mant_shadow_highShape', 'HeaddressShape',
                   'slime_highShape', 'bandana_highShape', 'topoShape', 'scabbardRingLShape', 'scabbardRingRShape',
                   'sword_RingShape']),
]
# female Robin's (her costumes 1 / 3 / 5 / 7): the same parts under her own names
_RF = 'Reflet_f_%s_VIS_O_OBJ'
_RFS = 'Reflet_f_%s_VIS_O_OBJ_O_NOSORT_FAR_O_SORTEACHNODE'
REFLET_F_SLOTS = [
    ('bronzeswordM_VIS_O_OBJ', []), ('thunderswordM_VIS_O_OBJ', []), ('group7_O_OBJ_O_SORTEACHNODE', ['hair_highShape']),
    (_RF % 'Eye', ['brave_Eye_VIS_O_OBJShape']),
    (_RFS % 'Openblink', ['brave_Openblink_VIS_O_OBJShape']),
    (_RF % 'Mouth_FaceN', ['brave_Mouth_FaceN_VIS_O_OBJShape']),
    (_RFS % 'Halfblink', ['brave_Halfblink02_VIS_O_OBJShape']),
    (_RFS % 'Blink', ['brave_Blink_VIS_O_OBJShape']),
    (_RFS % 'Blink_Talk', ['brave_Blink_Talk_VIS_O_OBJShape']),
    (_RF % 'Mouth_Talk', ['brave_Mouth_Talk_VIS_O_OBJShape']),
    (_RF % 'Mouth_Final', ['brave_shield_VIS_O_OBJShape']),
    (_RF % 'Mouth_Outh', ['brave_Mouth_Ouch_VIS_O_OBJShape']),
    (_RFS % 'Blink_Ouch', ['brave_Blink_Ouch_VIS_O_OBJShape']),
    (_RFS % 'Blink_Down', ['brave_Blink_Down_VIS_O_OBJShape']),
    (_RF % 'Mouth_Down', ['brave_Mouth_Down_VIS_O_OBJShape']),
    (_RF % 'Mouth_Heavyattack', ['brave_Mouth_Heavyattack_VIS_O_OBJShape']),
    (_RFS % 'Blink_Capture', ['brave_Blink_Capture_VIS_O_OBJShape']),
    (_RFS % 'Blink_Ottotto', ['brave_Blink_Ottotto_VIS_O_OBJShape']),
    (_RF % 'Eye_Ottotto', ['brave_Eye_Ottotto_VIS_O_OBJShape']),
    (_RF % 'Mouth_Ottotto', ['brave_Mouth_Ottotto_VIS_O_OBJShape']),
    (_RFS % 'Blink_Furafura', ['brave_Blink_HeavyOuch_VIS_O_OBJShape']),
    (_RF % 'Mouth_Furafura', ['brave_Mouth_Furafura_VIS_O_OBJShape']),
    (_RF % 'Cheek_Hot', ['brave_Hot_VIS_O_OBJShape']),
    (_RF % 'Mouth_Bound', ['brave_Mouth_Bound_VIS_O_OBJShape1']),
    (_RF % 'Eye_Heavyattack', ['brave_Eye_Heavyattack_VIS_O_OBJShape']),
    (_RF % 'Mouth_Result', ['brave_shieldb_VIS_O_OBJShape']),
    ('book_VIS_O_OBJ', []),
    ('fullhands', next(us for sl, us in REFLET_SLOTS if sl == 'fullhands')),
]
REFLET_VIS = {'brave_shield': 'Reflet_Mouth_Final_VIS_O_OBJ', 'brave_shieldb': 'Reflet_Mouth_Result_VIS_O_OBJ'}
REFLET_F_VIS = {'brave_shield': _RF % 'Mouth_Final', 'brave_shieldb': _RF % 'Mouth_Result'}
REFLET_MOTIONS = {
    'c00attack100start': 'c00attack11', 'c00attack100': 'c00attack11', 'c00attackend': 'c00attack11',
    'd00specialnshoot': 'd00specialn1', 'd00specialntronstart': 'd00specialn3', 'd00specialntronhold': 'd00specialnhold',
    'd00specialntronend': 'd00specialn3', 'd00specialairnshoot': 'd00specialairn1',
    'd00specialairntronstart': 'd00specialairn3', 'd00specialairntronhold': 'd00specialairnhold',
    'd00specialairntronend': 'd00specialairn3',
    'd01specials': 'd01specials1', 'd01specialairs': 'd01specialairs1',
    'd02specialhifail': 'd02specialhiempty', 'd02specialairhifail': 'd02specialairhiempty',
    'd03speciallwcapture': 'd03speciallwskill1', 'd03speciallwend': 'd03speciallwcancel',
    'd03specialairlwcapture': 'd03specialairlwskill1', 'd03specialairlwend': 'd03specialairlwcancel',
    'd04finalready': 'd04finalstart', 'd04finaldash': 'd04finalstart', 'd04final': 'd04finalend',
    'd04finalfail': 'd04finalend', 'l00resurrectionbook': 'a00wait1', 'l00resurrectionthundersword': 'a00wait1',
}
# a base fighter's profile: its mesh slots, joint-table stand-ins, motion stand-ins (its specials),
# Ultimate visibility tracks driving slots (with the default where a motion has none), slots hidden
# Mario's mesh slots for Squirtle (pzenigame). Mario's face is driven by his two material animations: the
# eyelid one (the upper face: FaceN, Eye, the blinks and the expression faces) and the face one (the mouth
# shapes). Squirtle's face is likewise in pieces: an eye / eyelid shape per expression (_Blink, the face's
# skin with it), the pupils (Eye1), the mouths. Ultimate's blink (a00defaulteyelid) is Openblink -> Harfblink
# (1 frame) -> Down_Blink (5) -> Harfblink -> Openblink, as Mario's FaceN -> Halfblink -> Blink
_PZ = 'pzenigame_%s_VIS_O_OBJShape'
MARIO_SLOTS = [
    ('Mario_FaceN_VIS_O_OBJ', [_PZ % 'FaceN_Openblink']),
    ('Mario_FaceNMClose_VIS_O_OBJ', [_PZ % 'FaceN_Mouth']),
    ('Mario_FaceNMHalf_VIS_O_OBJ', [_PZ % 'PatternB_Mouth']),
    ('Mario_FaceNMOpen_VIS_O_OBJ', [_PZ % 'VoiceB_Mouth']),
    ('Mario_Hathead_VIS_O_OBJ', []),
    ('Mario_Nohat_VIS_O_OBJ', []),
    ('Mario_Eye_VIS_O_OBJ', [_PZ % 'FaceN_Eye1']),
    ('Mario_Halfblink1_VIS_O_OBJ', [_PZ % 'Harfblink_Blink']),
    ('Mario_Halfblink2_VIS_O_OBJ', [_PZ % 'Harfblink_Blink']),
    ('Mario_Halfblink3_VIS_O_OBJ', [_PZ % 'Harfblink_Blink']),
    ('Mario_Blink_VIS_O_OBJ', [_PZ % 'Down_Blink']),
    ('Mario_Ouch_VIS_O_OBJ', [_PZ % 'Ouch_Blink']),
    ('Mario_OuchMOpen_VIS_O_OBJ', [_PZ % 'HeavyHit_Mouth']),
    ('Mario_OuchMHalf_VIS_O_OBJ', [_PZ % 'Ottoto_Mouth']),
    ('Mario_OuchMClose_VIS_O_OBJ', [_PZ % 'PatternA_Mouth']),
    ('Mario_Down_VIS_O_OBJ', [_PZ % 'Down_Blink']),
    ('Mario_Talk_VIS_O_OBJ', [_PZ % 'Talk_Blink']),
    ('Mario_TalkMOpen_VIS_O_OBJ', [_PZ % 'Heavyattack_Mouth']),
    ('Mario_TalkMHalf_VIS_O_OBJ', [_PZ % 'PatternB_Mouth']),
    ('Mario_TalkMClose_VIS_O_OBJ', [_PZ % 'Talk_Mouth']),
    ('Mario_Attack_VIS_O_OBJ', [_PZ % 'Attack_Blink']),
    ('Mario_Capture_VIS_O_OBJ', [_PZ % 'Capture_Blink']),
    ('Mario_Bound_VIS_O_OBJ', [_PZ % 'Heavyouch_Blink']),
    ('Mario_Heavyouch_VIS_O_OBJ', [_PZ % 'Heavyouch_Blink']),
    ('Mario_Furafura_VIS_O_OBJ', [_PZ % 'Furafura_Blink']),
    ('Mario_Cliff_VIS_O_OBJ', [_PZ % 'Cliff_Blink']),
    ('Mario_Sorori_VIS_O_OBJ', [_PZ % 'PatternA_Blink']),
    ('Mario_Final_VIS_O_OBJ', [_PZ % 'Hot_Blink']),
    ('Mario_Escape_VIS_O_OBJ', [_PZ % 'Heavyattack_Blink']),
    ('Mario_Ottotto_VIS_O_OBJ', [_PZ % 'PatternA_Blink']),
    ('Mario_Damageflyfront_VIS_O_OBJ', [_PZ % 'Heavyhit_Blink']),
    ('Mario_Result_VIS_O_OBJ', [_PZ % 'Catch_Mouth']),
    ('Mario_Hair_VIS_O_OBJ', []),
    ('Gamemodel', ['GamemodelShape']),
]
# Mario's specials -> Squirtle's: Fireball -> Water Gun (its shot), Cape -> Withdraw (its start), Super Jump
# Punch -> Waterfall, F.L.U.D.D. -> Pokemon Change (out, then back in: no swap); appeals: the facing-right ones
MARIO_MOTIONS = {
    # Water Gun's start in Mario's fireball slots (the hold / shot in its custom-move slots: extra_kinds.json
    # "motions", fighters/pzenigame/README.md); Withdraw's start; Pokemon Change's out / in in FLUDD's
    # start / hold slots (light / heavy: the in, unused)
    'd00specialn': 'd00specialnstart', 'd00specialairn': 'd00specialairnstart',
    'd01specials': 'd01specialsstart', 'd01specialairs': 'd01specialairsstart',
    'd01specialsloop': 'd01specials', 'd01specialairsloop': 'd01specials',
    'd02specialhi': 'd02specialhi', 'd02specialairhi': 'd02specialairhi',
    'd03speciallwstart': 'd03speciallwout', 'd03speciallwhold': 'd03speciallwin',
    'd03speciallwlight': 'd03speciallwin', 'd03speciallwheavy': 'd03speciallwin',
    'd03specialairlwstart': 'd03specialairlwout', 'd03specialairlwhold': 'd03specialairlwin',
    'd03specialairlwlight': 'd03specialairlwin', 'd03specialairlwheavy': 'd03specialairlwin',
    'd04final': 'd04final', 'd04finalair': 'd04finalair',
    'j01appealhi': 'j01appealhir', 'j01appeals': 'j01appealsr', 'j01appeallw': 'j01appeallwr',
}

PROFILES = {
    'zelda': dict(slots=MESH_SLOTS, joints=JOINT_STANDINS, motions=MOTION_STANDINS, vis=VIS_SLOTS,
                  vis_default={'skirt_VIS_O_OBJ16': 1}, hidden=HIDDEN_SLOTS),
    'koopa': dict(slots=KOOPA_SLOTS, joints=KOOPA_JOINTS, motions=dict(MOTION_STANDINS, **KOOPA_MOTIONS), vis={},
                  vis_default={}, hidden=()),
    # own_joints: the joint table bones that get a bone of their own (Skeleton.add_joint_bones; default
    # all). layers: Ultimate motions with another one baked over them (add_layers)
    'pit': dict(slots=PIT_SLOTS, joints={}, motions=dict(MOTION_STANDINS, **PIT_MOTIONS), vis=PIT_TOOL_VIS,
                vis_default={}, hidden=(), layers=PIT_LAYERS),
    'reflet': dict(slots=REFLET_SLOTS, joints={}, motions=dict(MOTION_STANDINS, **REFLET_MOTIONS),
                   vis=REFLET_VIS, vis_default={REFLET_VIS['brave_shield']: 1}, hidden=()),
    'mario': dict(slots=MARIO_SLOTS, joints={}, motions=dict(MOTION_STANDINS, **MARIO_MOTIONS), vis={},
                  vis_default={}, hidden=()),
    'reflet_f': dict(slots=REFLET_F_SLOTS, joints={}, motions=dict(MOTION_STANDINS, **REFLET_MOTIONS),
                     vis=REFLET_F_VIS, vis_default={REFLET_F_VIS['brave_shield']: 1}, hidden=()),
}


def profile_for(base_mesh_names):
    base_mesh_names = list(base_mesh_names)
    for name, p in PROFILES.items():
        if [n for n, _ in p['slots']] == list(base_mesh_names):
            return name, p
    raise SystemExit('no profile with the base mesh list %s' % list(base_mesh_names))


def _quat_mat(q):
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    r = np.empty((len(q), 3, 3))
    r[:, 0, 0] = 1 - 2 * (y * y + z * z); r[:, 0, 1] = 2 * (x * y - z * w); r[:, 0, 2] = 2 * (x * z + y * w)  # noqa: E702
    r[:, 1, 0] = 2 * (x * y + z * w); r[:, 1, 1] = 1 - 2 * (x * x + z * z); r[:, 1, 2] = 2 * (y * z - x * w)  # noqa: E702
    r[:, 2, 0] = 2 * (x * z - y * w); r[:, 2, 1] = 2 * (y * z + x * w); r[:, 2, 2] = 1 - 2 * (x * x + y * y)  # noqa: E702
    return r


def _mat_quat(r):
    """rotation matrices [F, 3, 3] -> quaternions x y z w (w >= 0)"""
    q = np.empty((len(r), 4))
    t = r[:, 0, 0] + r[:, 1, 1] + r[:, 2, 2]
    for i in range(len(r)):
        m = r[i]
        if t[i] > 0:
            s = np.sqrt(t[i] + 1.0) * 2
            q[i] = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
        elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
            s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
            q[i] = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
        elif m[1, 1] > m[2, 2]:
            s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
            q[i] = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
        else:
            s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
            q[i] = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    q[q[:, 3] < 0] *= -1
    return q


def _euler_xyz(r):
    """[F,3,3] -> intrinsic angles with R = Rz Ry Rx"""
    ry = np.arcsin(np.clip(-r[:, 2, 0], -1, 1))
    rx = np.arctan2(r[:, 2, 1], r[:, 2, 2])
    rz = np.arctan2(r[:, 1, 0], r[:, 0, 0])
    return rx, ry, rz


def _euler_mats(rx, ry, rz):
    return np.stack([euler_mat(a, b, c) for a, b, c in zip(rx, ry, rz)])


def ult_tracks(anim, frames):
    """{bone: [F, 4, 4] local (column vectors)}, {visibility name: [F] bool}"""
    out, vis = {}, {}
    for g in anim.groups:
        kind = g.group_type.name
        for n in g.nodes:
            for t in n.tracks:
                vals = t.values
                idx = np.minimum(np.arange(frames), len(vals) - 1)
                if kind == 'Transform':
                    sc = np.array([v.scale for v in vals])[idx]
                    q = np.array([v.rotation for v in vals])[idx]
                    tr = np.array([v.translation for v in vals])[idx]
                    m = np.zeros((frames, 4, 4))
                    m[:, :3, :3] = _quat_mat(q) * sc[:, None, :]
                    m[:, :3, 3] = tr
                    m[:, 3, 3] = 1
                    out[n.name] = m
                elif kind == 'Visibility':
                    vis[n.name] = np.array(vals, dtype=bool)[idx]
    return out, vis


def _blend(a, b, t):
    """[F, 4, 4] locals a -> b by t ([F] or a number): translation and scale lerped, rotation nlerped"""
    t = np.broadcast_to(np.asarray(t, dtype=np.float64), (len(a),))[:, None]
    sa, sb = np.linalg.norm(a[:, :3, :3], axis=1), np.linalg.norm(b[:, :3, :3], axis=1)
    qa, qb = _mat_quat(a[:, :3, :3] / sa[:, None, :]), _mat_quat(b[:, :3, :3] / sb[:, None, :])
    qb[np.sum(qa * qb, axis=1) < 0] *= -1
    q = qa * (1 - t) + qb * t
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    m = np.zeros(a.shape)
    m[:, :3, :3] = _quat_mat(q) * (sa * (1 - t) + sb * t)[:, None, :]
    m[:, :3, 3] = a[:, :3, 3] * (1 - t) + b[:, :3, 3] * t
    m[:, 3, 3] = 1
    return m


def add_layers(tracks, frames, layers, motion_dir, have):
    """Ultimate's layers baked in: [(layer animation, cycles, weight)] played over the motion's frames
    (looping, cycles times), on the bones the layer moves, weight of the way from the motion's own pose.
    Steve's walks, run, dash and jumps move only his root: his limbs swing by a separate walk cycle
    (a01walk) the game layers on (PIT_LAYERS)"""
    import ssbh_data_py as s
    for lname, cycles, weight in layers:
        la = s.anim_data.read_anim(os.path.join(motion_dir, have[lname]))
        lf = int(round(la.final_frame_index)) + 1
        ltr, _ = ult_tracks(la, lf)
        pos = (np.arange(frames) * cycles * (lf - 1) / float(frames)) % (lf - 1)
        i0 = np.floor(pos).astype(int)
        for b, m in ltr.items():
            if np.allclose(m, m[0], atol=1e-4) or b not in tracks:
                continue
            lm = _blend(m[i0], m[i0 + 1], pos - i0)
            tracks[b] = lm if weight >= 1 else _blend(np.array(tracks[b]), lm, weight)
    return tracks


def helper_constraints(src):
    import ssbh_data_py as s
    path = os.path.join(src, 'model.nuhlpb')
    if not os.path.exists(path):
        return []
    return list(s.hlpb_data.read_hlpb(path).orient_constraints)


def pose(sk, tracks, frames, constraints):
    """our bones' [F, 4, 4] locals for one motion: Ultimate's animated locals (the bind where a bone
    has no track), the folded chains multiplied, the helper bones turned by their orient constraints
    (a share of the source bone's turn away from its bind, axis by axis, in the parent bone's frame)"""
    loc = {u: tracks.get(u, np.broadcast_to(sk.ult_local[u], (frames, 4, 4))) for u in sk.ult_names}

    def ult_world(name, cache):
        if name not in cache:
            p = sk.ult_parent[name]
            cache[name] = loc[name] if p is None else ult_world(p, cache) @ loc[name]
        return cache[name]
    if constraints:
        bind_loc = {u: np.broadcast_to(sk.ult_local[u], (1, 4, 4)) for u in sk.ult_names}
        cache = {}
        for c in constraints:
            if c.target_bone_name not in loc:
                continue
            wb = {}

            def bw(name):
                if name not in wb:
                    p = sk.ult_parent[name]
                    wb[name] = bind_loc[name] if p is None else bw(p) @ bind_loc[name]
                return wb[name]
            rel = np.linalg.inv(ult_world(c.parent_bone_name1, cache)) @ ult_world(c.source_bone_name, cache)
            rel0 = np.linalg.inv(bw(c.parent_bone_name1)) @ bw(c.source_bone_name)
            d = np.linalg.inv(rel0[:, :3, :3]) @ rel[:, :3, :3]
            rx, ry, rz = _euler_xyz(d)
            ax = c.constraint_axes
            turn = _euler_mats(rx * ax[0], ry * ax[1], rz * ax[2])
            m = np.array(loc[c.target_bone_name], copy=True)
            m[:, :3, :3] = m[:, :3, :3] @ turn
            loc[c.target_bone_name] = m
    out = []
    for name, _p, _h, chain in sk.bones:
        if not chain:           # a joint table bone of its own (Skeleton.add_joint_bones)
            out.append(np.broadcast_to(np.eye(4), (frames, 4, 4)))
            continue
        m = loc[chain[0]]
        for u in chain[1:]:
            m = m @ loc[u]
        out.append(m)
    return out


def omo_bytes(head, locals_, sk, frames):
    import omo
    o = omo.Omo(b'OMO ' + head + struct.pack('>HHH', 0, frames, 0) + struct.pack('>III', 0x20, 0x20, 0x20))
    for (name, _p, h, _c), m in zip(sk.bones, locals_):
        m = np.broadcast_to(m, (frames, 4, 4))
        t = m[:, :3, 3]
        sc = np.linalg.norm(m[:, :3, :3], axis=1)
        r = m[:, :3, :3] / sc[:, None, :]
        q = _mat_quat(r)
        _node(o, h, t, q, sc)
    return o.encode()


def _node(o, h, pos, rot, scl):
    import omo
    flags, consts, keys = 0, b'', [b''] * o.frames
    rot = [tuple(-c for c in q) if q[3] < 0 else tuple(q) for q in rot]
    for vals, bit, interp, const in ((pos, omo.POS, 0x08 << 16, 0x20 << 16),
                                     ([q[:3] for q in rot], omo.ROT, 5 << 12, 7 << 12),
                                     (scl, omo.SCL, 0x081, 0x201)):
        vals = np.asarray(vals, dtype=np.float64)
        if np.allclose(vals, vals[0], atol=1e-6):
            flags |= bit | const
            consts += struct.pack('>3f', *vals[0])
            continue
        c, k = omo.interp_track([tuple(v) for v in vals])
        flags |= bit | interp
        consts += c
        keys = [keys[i] + k[i] for i in range(o.frames)]
    o.nodes.append([flags, h, consts, keys])


def vis_keys(states):
    keys = [(0, int(states[0]))]
    for f in range(1, len(states)):
        if states[f] != states[f - 1]:
            keys.append((f, int(states[f])))
    if keys[-1][0] != len(states) - 1:
        keys.append((len(states) - 1, int(states[-1])))
    return keys


def motion_aliases(motion_dir):
    """{motion kind without underscores (e.g. 'fall', 'jumpaerialf'): the animation file (stem) it plays}
    from the fighter's motion_list.bin: Ultimate's motion kinds can share an animation (Steve's fall,
    jump_b and jump_aerial_f all play a03jumpf), which then has no file of their own name. Names:
    reference/ultimate_motion_kinds.txt (motion list keys are hash40s of them)"""
    import ultimate_acmd
    path = os.path.join(motion_dir, 'motion_list.bin')
    if not os.path.exists(path):
        return {}
    files = {}
    for f in os.listdir(motion_dir):
        if f.endswith('.nuanmb'):
            files[ultimate_acmd.hash40(f)] = f[:-7]
            files[ultimate_acmd.hash40(f[:-7])] = f[:-7]
    by_key = {e['key']: e for e in ultimate_acmd.read_motion_list(path)}
    out = {}
    for line in open(os.path.join(HERE, '..', 'reference', 'ultimate_motion_kinds.txt')):
        name = line.strip()
        if not name or name.startswith('#'):
            continue
        e = by_key.get(ultimate_acmd.hash40(name))
        if e and e['anims'] and e['anims'][0] in files:
            out.setdefault(name.replace('_', ''), files[e['anims'][0]])
    return out


def build_motions(motion_dir, src_model, base, out, log=print, add=(), max_bones=None, animated=None, joints=(),
                  extra_vis=None):
    """the base's motion/body pacs with Ultimate's motions on our skeleton (main.pac), its hand-pose
    layers emptied (they turn the base's HandN / HaveN), and the material_anime face / eyelid pacs
    of every costume with the swords' (and the wing's) visibility added. add: motions the base has
    no animation for (e.g. C00Attack12), added to body/main.pac as <prefix><name>.omo (the kind's
    motion table must point at them: extra_kinds.json "motions"). extra_vis: {Ultimate animation:
    {visibility name: [[frame, 0 / 1], ...]}}, visibility the motions don't carry themselves (Steve's
    tools, which his scripts ask for: tools/pickel_build.py), for the profile's "vis" slots"""
    import omo
    import mta
    import ssbh_data_py as s
    base_vbn = read_vbn(base + '/model/body/c00/model.vbn')
    _pn, prof = profile_for(m.name for m in nud.read(base + '/model/body/c00/model.nud'))
    costumes = [os.path.join(os.path.dirname(src_model), c) for c in sorted(os.listdir(os.path.dirname(src_model)))
                if os.path.exists(os.path.join(os.path.dirname(src_model), c, 'model.numshb'))]
    base_jtb = open(base + '/model/body/c00/model.jtb', 'rb').read()
    keep = set()
    for c in costumes:
        keep |= needed_bones([c], prof['joints'], joint_bone_budget([c], base_jtb, base_vbn, prof['joints'], max_bones, OWN_JOINTS or prof.get('own_joints')),
                             animated, joints)
    sk = Skeleton(s.skel_data.read_skel(src_model + '/model.nusktb'), base_vbn, keep)
    sk.add_joint_bones(base_jtb, base_vbn, prof['joints'], OWN_JOINTS or prof.get('own_joints'))
    log('motion skeleton: %d bones (every costume\'s)' % len(sk.bones))
    constraints = helper_constraints(src_model)
    have = {f[:-7]: f for f in os.listdir(motion_dir) if f.endswith('.nuanmb')}
    aliases = motion_aliases(motion_dir)
    frames_of, vis_of = {}, {}
    for folder in ('body', 'bodyentry', 'bodyresult', 'bodyroutemap'):
        mdir = base + '/motion/' + folder
        if not os.path.exists(mdir + '/main.pac'):
            continue
        main = omo.pac_read(mdir + '/main.pac')
        prefix = os.path.commonprefix([n for n, _ in main] + [main[0][0][:main[0][0].index('Main') + 4]])
        prefix = prefix[:prefix.index('Main') + 4]
        entries, missing = [], []
        head = omo.Omo(main[0][1]).head
        if folder == 'body':
            main = main + [(prefix + n + '.omo', None) for n in add if prefix + n + '.omo' not in dict(main)]
        for name, data in main:
            key = name[len(prefix):-4].lower()
            ult = key if key in have else prof['motions'].get(key)
            if ult not in have:
                ult = aliases.get(key[3:])          # a motion kind playing another's animation
            if ult not in have:
                missing.append(key)
                ult = 'a00wait1'
            anim = s.anim_data.read_anim(os.path.join(motion_dir, have[ult]))
            frames = int(round(anim.final_frame_index)) + 1
            tracks, vis = ult_tracks(anim, frames)
            if ult in prof.get('layers', {}):
                tracks = add_layers(tracks, frames, prof['layers'][ult], motion_dir, have)
            for uname, keys in (extra_vis or {}).get(ult, {}).items():
                st = np.zeros(frames, bool)
                for f, on in sorted(keys):
                    st[min(int(f), frames - 1):] = bool(on)
                vis[uname] = st
            locs = pose(sk, tracks, frames, constraints)
            entries.append((name, omo_bytes(head, locs, sk, frames)))
            if folder == 'body':
                frames_of[name[:-4]] = frames
                vis_of[name[:-4]] = vis
        os.makedirs(out + '/motion/' + folder, exist_ok=True)
        omo.pac_write(out + '/motion/%s/main.pac' % folder, entries)
        log('%s/main.pac: %d motions, %d stood in by a00wait1: %s' % (folder, len(entries), len(missing),
                                                                       ', '.join(missing)))
        # hand-pose layers: one constant node on a bone we don't have, so they turn nothing
        for layer in ('lhand', 'rhand'):
            p = mdir + '/%s.pac' % layer
            if not os.path.exists(p):
                continue
            dummy = [b for b in base_vbn if b[0] not in sk.by_name][0][2]
            ents = []
            for name, data in omo.pac_read(p):
                o = omo.Omo(data)
                o.nodes = [[omo.ROT | (7 << 12), dummy, struct.pack('>3f', 0, 0, 0), [b''] * o.frames]]
                ents.append((name, o.encode()))
            omo.pac_write(out + '/motion/%s/%s.pac' % (folder, layer), ents)
    # visibility: the base's eyelid / face material animations, plus the swords and the wing
    for cdir in sorted(os.listdir(base + '/model/body')):
        cpath = base + '/model/body/' + cdir
        if not cdir.startswith('c') or not os.path.isdir(cpath):
            continue
        # each costume's own slot names (female Robin's: reflet_f)
        cprof = profile_for(m.name for m in nud.read(cpath + '/model.nud'))[1] \
            if os.path.exists(cpath + '/model.nud') else prof
        for pac in ('material_anime_face.pac', 'material_anime_eyelid.pac'):
            src = os.path.join(cpath, pac)
            if not os.path.exists(src):
                continue
            old = {n: d for n, d in omo.pac_read(src)}
            ents = []
            for mname, frames in frames_of.items():
                vis = []
                d = old.get(mname + '.mta')
                if d is not None and d[:4] == b'MTA4':
                    m = mta.read(d)
                    for v in m['vis']:
                        ks = [(min(k[0], frames - 1), k[1]) for k in v['keys']]
                        vis.append((v['name'], sorted(set(ks))))
                if pac == 'material_anime_face.pac':
                    if d is None and cprof['vis'] and old.get('default.mta', b'')[:4] == b'MTA4':
                        # a motion the base has no entry for plays default.mta; an entry of ours (for the
                        # slots below) replaces it, so it starts from the default's keys (else no mouth)
                        vis = [(v['name'], [(0, v['keys'][0][1])]) for v in mta.read(old['default.mta'])['vis']]
                    # the base's own keys for the slots we drive go (Pit's mouths: they'd show the tools)
                    vis = [v for v in vis if v[0] not in cprof['vis'].values()]
                    for uname, slot in cprof['vis'].items():
                        st = vis_of[mname].get(uname)
                        for other in VIS_ALSO.get(uname, ()):
                            o = vis_of[mname].get(other)
                            if o is not None:
                                st = o if st is None else (np.asarray(st) | np.asarray(o))
                        vis.append((slot, vis_keys(st) if st is not None else [(0, cprof['vis_default'].get(slot, 0))]))
                    for slot in cprof['hidden']:
                        vis = [v for v in vis if v[0] != slot] + [(slot, [(0, 0)])]
                if vis:
                    ents.append((mname + '.mta', mta.write(frames, [], 60, 21, vis)))
            # the base's other entries (default / default_temporarily / display.mta, material_anime.lst:
            # its own hash of the motion names, which are the base's): kept, the defaults with the swords'
            # (and the wing's) keys too. Left out up to test 20 (the sword didn't show in attacks)
            for name, d in omo.pac_read(src):
                if name[:-4] in frames_of:
                    continue
                if name.endswith('.mta') and d[:4] == b'MTA4' and pac == 'material_anime_face.pac':
                    m = mta.read(d)
                    vis = [(v['name'], sorted(set((min(k[0], m['frames'] - 1), k[1]) for k in v['keys'])))
                           for v in m['vis'] if v['name'] not in cprof['hidden'] and v['name'] not in cprof['vis'].values()]
                    vis += [(slot, [(0, cprof['vis_default'].get(slot, 0))]) for slot in cprof['vis'].values()]
                    vis += [(slot, [(0, 0)]) for slot in cprof['hidden']]
                    d = mta.write(m['frames'], [], m['rate'], m['unk'], vis)
                ents.append((name, d))
            os.makedirs(out + '/model/body/' + cdir, exist_ok=True)
            omo.pac_write(os.path.join(out, 'model/body', cdir, pac), ents)
    return sk


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('model')
    m.add_argument('src')
    m.add_argument('base')
    m.add_argument('out')
    m.add_argument('--tex-id', type=lambda v: int(v, 0), default=TEX_ID)
    m.add_argument('--empty', help='a folder with an empty model.sb / model.nhb to use')
    m.add_argument('--pixel-art', type=int, default=0, help='blow textures smaller than this up to it with nearest '
                   'pixels (Steve: 512)')
    mo = sub.add_parser('motions')
    mo.add_argument('motion_dir')
    mo.add_argument('src_model')
    mo.add_argument('base')
    mo.add_argument('out')
    mo.add_argument('--add', default='', help='motions to add to body/main.pac (comma separated, e.g. C00Attack12)')
    mo.add_argument('--extra-vis', help='JSON {Ultimate animation: {visibility: [[frame, 0/1], ...]}} (Steve\'s tools)')
    for q in (m, mo):
        q.add_argument('--joints', default='', help='Ultimate bones to add to the joint table, table 1 (ACMD joint '
                                                       'IDs 1000 + its base length + k; comma separated)')
        q.add_argument('--own-joints', help='the base joint table bones to give bones of their own (comma separated, '
                                            'or "all"; default: the profile\'s own_joints, else all)')
        q.add_argument('--max-bones', type=int, help='merge bones into their parents down to this many per costume '
                                                     '(fighters go up to 138; use 136)')
        q.add_argument('--anim-cache', help='JSON file keeping which bones the motions move')
        q.add_argument('--have', help='LEFT,RIGHT: the Ultimate bones that play LHaveN / RHaveN (set_have)')
    m.add_argument('--motions', help='with --max-bones: the motion folder (the bones no motion moves merge first)')
    a = ap.parse_args()
    joints = [j for j in a.joints.split(',') if j]
    global OWN_JOINTS
    if a.own_joints:
        OWN_JOINTS = ALL_JOINTS if a.own_joints == 'all' else tuple(a.own_joints.split(','))
    if a.have:
        set_have(*a.have.split(','))
    animated = None
    if a.max_bones:
        mdir = a.motion_dir if a.cmd == 'motions' else a.motions
        if mdir:
            animated = animated_bones(mdir, a.src_model if a.cmd == 'motions' else a.src, a.anim_cache)
    if a.cmd == 'motions':
        build_motions(a.motion_dir, a.src_model, a.base, a.out, add=[n for n in a.add.split(',') if n],
                      max_bones=a.max_bones, animated=animated, joints=joints,
                      extra_vis=json.load(open(a.extra_vis)) if a.extra_vis else None)
    if a.cmd == 'model':
        global PIXEL_ART
        PIXEL_ART = a.pixel_art
        build_model(a.src, a.base, a.out, a.tex_id, joints=joints, max_bones=a.max_bones, animated=animated)
        if a.empty:
            for f in ('model.sb', 'model.nhb'):
                shutil.copy(os.path.join(a.empty, f), os.path.join(a.out, f))


if __name__ == '__main__':
    main()
