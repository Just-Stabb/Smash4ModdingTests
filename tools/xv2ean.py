#!/usr/bin/env python3
"""Dragon Ball Xenoverse 2 animations: EAN (an ESK skeleton + keyframed bone animations), and their retargeting
onto a Smash 4 skeleton (model.vbn) as OMO motions.

  python3 -I tools/xv2ean.py dump FILE.ean                       skeleton and animations (index, name, frames)
  python3 -I tools/xv2ean.py omo FILE.ean INDEX MODEL.vbn BASE.omo OUT.omo [--fps-scale S]
        animation INDEX retargeted onto the vbn's skeleton (BASE.omo: a motion of that fighter whose node list /
        order is kept, e.g. its AttackDash), XV2_TO_MARIO's bone map
  python3 -I tools/xv2ean.py --selftest                           a written EAN read back, the retarget's checks

STATUS: written for the Super God Fist (fighters/supamario/README.md) without an EAN file to read: the skill's
030_GOD_CSA.ean and CMN.ean were not among the files given. The layout below is LazyBone152's XV2-Tools
(Xv2CoreLib EAN/EAN_File.cs, ESK/ESK_File.cs) as remembered, not yet checked against a real file: the self-test
only proves this reader and its own writer agree. Check `dump` on a real EAN first (bone names b_C_Base,
b_C_Pelvis, ... and a sensible frame count are the sign the offsets are right).

Little-endian.
EAN: +0 "#EAN", +4 u16 0xFFFE, +6 u16 header size, +8 u32 version, +0x10 u8 camera flag, +0x11 u8, +0x12 u16
  animation count, +0x14 u32 skeleton offset, +0x18 u32 animation table (u32 per animation, absolute; 0 = none),
  +0x1C u32 name table (u32 per animation, absolute, to a 0-terminated name).
ESK (at the skeleton offset; its offsets relative to it): +0 u16 bone count, +2 u16 flags, +4 u32 bone index
  table (u16 parent, child, sibling, IK index per bone; 0xFFFF none), +8 u32 name table (u32 per bone, relative
  to the ESK), +0xC u32 relative transforms (12 floats per bone: position xyzw, rotation quaternion xyzw, scale
  xyzw), +0x10 u32 absolute matrices (0 = none), +0x14 u32 IK data, +0x18 u32 extra bone info, +0x1C u64 id.
Animation (at its offset; offsets relative to it): +0 u16, +2 u8 index size (0 u8, 1 u16, 2 u32), +3 u8 value size
  (1 half floats, 2 floats), +4 u32 frame count, +8 u32 node count, +0xC u32 node table (u32 per node).
  Node: +0 u16 bone index (the EAN's ESK), +2 u16 component count, +4 u32 component table (u32 per component,
  relative to the node). Component: +0 u8 type (0 position, 1 rotation (quaternion xyzw), 2 scale), +1 u8 flags,
  +2 u16, +4 u32 keyframe count, +8 u32 frame indices (relative to the component), +0xC u32 values (4 a keyframe).
  Between keyframes values are interpolated (linear; quaternions slerped).
XV2 characters face +Z, Y up, in metres; Smash 4 fighters face +Z, Y up; Mario is ~10 units to the head.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

# XV2's human skeleton (b_C_* centre, b_L_* / b_R_* sides) -> Mario's (and every Smash 4 human's) bones
XV2_TO_MARIO = {
    'b_C_Pelvis': 'HipN', 'b_C_Spine1': 'WaistN', 'b_C_Chest': 'BustN', 'b_C_Neck1': 'NeckN', 'b_C_Head': 'HeadN',
    'b_L_Shoulder': 'LShoulderN', 'b_L_Arm1': 'LShoulderJ', 'b_L_Arm2': 'LArmJ', 'b_L_Hand': 'LHandN',
    'b_R_Shoulder': 'RShoulderN', 'b_R_Arm1': 'RShoulderJ', 'b_R_Arm2': 'RArmJ', 'b_R_Hand': 'RHandN',
    'b_L_Leg1': 'LLegJ', 'b_L_Leg2': 'LKneeJ', 'b_L_Foot': 'LFootJ', 'b_L_Toe': 'LToeN',
    'b_R_Leg1': 'RLegJ', 'b_R_Leg2': 'RKneeJ', 'b_R_Foot': 'RFootJ', 'b_R_Toe': 'RToeN',
}
ROOT_XV2, ROOT_SMASH = 'b_C_Base', 'TransN'


def _half(h):
    return struct.unpack('<e', struct.pack('<H', h))[0]


def _cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('ascii', 'replace')


class Bone:
    def __init__(self, name, parent, pos, rot, scl):
        self.name, self.parent, self.pos, self.rot, self.scl = name, parent, pos, rot, scl


class Component:
    def __init__(self, kind, frames, values):
        self.kind, self.frames, self.values = kind, frames, values

    def sample(self, f):
        fr, vs = self.frames, self.values
        if not fr:
            return None
        if f <= fr[0]:
            return vs[0]
        if f >= fr[-1]:
            return vs[-1]
        for i in range(1, len(fr)):
            if f <= fr[i]:
                t = (f - fr[i - 1]) / float(fr[i] - fr[i - 1])
                return slerp(vs[i - 1], vs[i], t) if self.kind == 1 else tuple(
                    a + (b - a) * t for a, b in zip(vs[i - 1], vs[i]))
        return vs[-1]


class Animation:
    def __init__(self, name, frames, nodes):
        self.name, self.frames, self.nodes = name, frames, nodes     # nodes: {bone index: {kind: Component}}


class Ean:
    def __init__(self, data):
        d = data
        assert d[:4] == b'#EAN', d[:4]
        count, = struct.unpack_from('<H', d, 0x12)
        esk, atab, ntab = struct.unpack_from('<III', d, 0x14)
        self.bones = self._esk(d, esk)
        self.animations = []
        for i in range(count):
            ao, = struct.unpack_from('<I', d, atab + 4 * i)
            no, = struct.unpack_from('<I', d, ntab + 4 * i) if ntab else (0,)
            name = _cstr(d, no) if no else ''
            self.animations.append(self._anim(d, ao, name) if ao else None)

    @staticmethod
    def _esk(d, o):
        n, _flags, idx, names, rel = struct.unpack_from('<HHIII', d, o)
        bones = []
        for i in range(n):
            parent = struct.unpack_from('<H', d, o + idx + 8 * i)[0]
            no, = struct.unpack_from('<I', d, o + names + 4 * i)
            t = struct.unpack_from('<12f', d, o + rel + 48 * i)
            bones.append(Bone(_cstr(d, o + no), -1 if parent == 0xFFFF else parent, t[0:3], t[4:8], t[8:11]))
        return bones

    @staticmethod
    def _anim(d, o, name):
        _u, isz, vsz, frames, nn, ntab = struct.unpack_from('<HBBIII', d, o)
        ifmt = {0: 'B', 1: 'H', 2: 'I'}[isz]
        nodes = {}
        for k in range(nn):
            no = o + struct.unpack_from('<I', d, o + ntab + 4 * k)[0]
            bone, cc, ctab = struct.unpack_from('<HHI', d, no)
            comps = {}
            for c in range(cc):
                co = no + struct.unpack_from('<I', d, no + ctab + 4 * c)[0]
                kind, _fl, _u2, kc, fo, vo = struct.unpack_from('<BBHIII', d, co)
                fr = list(struct.unpack_from('<%d%s' % (kc, ifmt), d, co + fo))
                if vsz == 1:
                    raw = struct.unpack_from('<%dH' % (4 * kc), d, co + vo)
                    vals = [tuple(_half(h) for h in raw[4 * j:4 * j + 4]) for j in range(kc)]
                else:
                    raw = struct.unpack_from('<%df' % (4 * kc), d, co + vo)
                    vals = [tuple(raw[4 * j:4 * j + 4]) for j in range(kc)]
                comps[kind] = Component(kind, fr, [v[:4] if kind == 1 else v[:3] for v in vals])
            nodes[bone] = comps
        return Animation(name, frames, nodes)

    def local(self, anim, i, f):
        """bone i's local (pos, quat, scale) at frame f (the ESK's rest for what the animation doesn't key)"""
        b = self.bones[i]
        comps = anim.nodes.get(i, {}) if anim else {}
        p = comps[0].sample(f) if 0 in comps else b.pos
        q = comps[1].sample(f) if 1 in comps else b.rot
        s = comps[2].sample(f) if 2 in comps else b.scl
        return tuple(p), tuple(q), tuple(s)


def write_ean(bones, anims, half=False):
    """an EAN from [Bone] and [Animation] (the layout above; for the self-test and for writing edited files)"""
    out = bytearray(0x20)
    out[0:4] = b'#EAN'
    struct.pack_into('<HHI', out, 4, 0xFFFE, 0x20, 0)
    struct.pack_into('<H', out, 0x12, len(anims))
    # ESK
    esk = len(out)
    n = len(bones)
    hdr = 0x24
    idx = hdr
    names = idx + 8 * n
    rel = names + 4 * n
    strings = rel + 48 * n
    e = bytearray(strings)
    struct.pack_into('<HHIII', e, 0, n, 0, idx, names, rel)
    sdata = bytearray()
    for i, b in enumerate(bones):
        struct.pack_into('<HHHH', e, idx + 8 * i, 0xFFFF if b.parent < 0 else b.parent, 0xFFFF, 0xFFFF, 0xFFFF)
        struct.pack_into('<I', e, names + 4 * i, strings + len(sdata))
        sdata += b.name.encode() + b'\0'
        struct.pack_into('<12f', e, rel + 48 * i, *(tuple(b.pos) + (1.0,) + tuple(b.rot) + tuple(b.scl) + (1.0,)))
    out += e + sdata
    while len(out) % 4:
        out.append(0)
    atab = len(out)
    out += bytes(4 * len(anims))
    ntab = len(out)
    out += bytes(4 * len(anims))
    for k, a in enumerate(anims):
        struct.pack_into('<I', out, ntab + 4 * k, len(out))
        out += a.name.encode() + b'\0'
        while len(out) % 4:
            out.append(0)
    for k, a in enumerate(anims):
        ao = len(out)
        struct.pack_into('<I', out, atab + 4 * k, ao)
        body = bytearray(0x10 + 4 * len(a.nodes))
        struct.pack_into('<HBBIII', body, 0, 0, 1, 1 if half else 2, a.frames, len(a.nodes), 0x10)
        for j, (bi, comps) in enumerate(sorted(a.nodes.items())):
            struct.pack_into('<I', body, 0x10 + 4 * j, len(body))
            node = bytearray(8 + 4 * len(comps))
            struct.pack_into('<HHI', node, 0, bi, len(comps), 8)
            for c, (kind, comp) in enumerate(sorted(comps.items())):
                struct.pack_into('<I', node, 8 + 4 * c, len(node))
                kc = len(comp.frames)
                fbytes = struct.pack('<%dH' % kc, *comp.frames)
                fbytes += bytes((4 - len(fbytes) % 4) % 4)
                vals = [tuple(v) + (1.0,) * (4 - len(v)) for v in comp.values]
                flat = [x for v in vals for x in v]
                vbytes = struct.pack('<%de' % len(flat), *flat) if half else struct.pack('<%df' % len(flat), *flat)
                cbody = struct.pack('<BBHIII', kind, 0, 0, kc, 0x10, 0x10 + len(fbytes)) + fbytes + vbytes
                while len(cbody) % 4:
                    cbody += b'\0'
                node += cbody
            body += node
        out += body
    struct.pack_into('<III', out, 0x14, esk, atab, ntab)
    return bytes(out)


# ---------------------------------------------------------------- quaternions (x, y, z, w)
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def qrot(q, v):
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qinv(q))
    return p[:3]


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-x for x in b), -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(min(1.0, d))
    s = math.sin(th)
    return qnorm(tuple(math.sin((1 - t) * th) / s * x + math.sin(t * th) / s * y for x, y in zip(a, b)))


def euler_xyz(rx, ry, rz):
    """a VBN bone's rest rotation (radians): X first, then Y, then Z (checked on Mario's vbn: the only order that
    makes his rest pose left / right symmetric)"""
    def ax(i, a):
        v = [0.0, 0.0, 0.0]
        v[i] = math.sin(a / 2)
        return (v[0], v[1], v[2], math.cos(a / 2))
    return qmul(ax(2, rz), qmul(ax(1, ry), ax(0, rx)))


def vbn_rest(path):
    """[(name, parent, hash, pos, quat, scale)] of a model.vbn (either endianness)"""
    import omo
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    bones = omo.vbn_read(path)
    off = 28 + 76 * len(bones)
    out = []
    for i, (name, parent, h) in enumerate(bones):
        t = struct.unpack_from(e + '9f', d, off + 36 * i)
        out.append((name, parent if 0 <= parent < len(bones) else -1, h, t[0:3], euler_xyz(*t[3:6]), t[6:9]))
    return out


def world_rots(locals_, parents):
    """world rotations from local ones, parents before children"""
    w = []
    for i, q in enumerate(locals_):
        w.append(q if parents[i] < 0 else qmul(w[parents[i]], q))
    return w


# ---------------------------------------------------------------- retarget
def retarget(ean, anim, smash, bone_map=None, root_scale=None):
    """per frame {smash bone name: (pos, quat, scale)}: each mapped bone turned by its XV2 bone's world-space turn
    from the ESK rest (D = W_xv2(t) W_xv2_rest^-1; W_smash(t) = D W_smash_rest), its local rotation from its parent's;
    other bones at their rest; TransN moved by b_C_Base's movement x root_scale (default: the pelvis heights'
    ratio). smash: vbn_rest()."""
    bone_map = bone_map or XV2_TO_MARIO
    xi = {b.name: i for i, b in enumerate(ean.bones)}
    xpar = [b.parent for b in ean.bones]
    xrest = world_rots([b.rot for b in ean.bones], xpar)
    sname = [b[0] for b in smash]
    spar = [b[1] for b in smash]
    si = {n: i for i, n in enumerate(sname)}
    srest = world_rots([b[4] for b in smash], spar)
    target = {si[s]: xi[x] for x, s in bone_map.items() if x in xi and s in si}
    if root_scale is None:
        def height(bones, i, par, getpos, getrot):
            p, q = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)
            chain = []
            while i >= 0:
                chain.append(i)
                i = par[i]
            for j in reversed(chain):
                lp = getpos(j)
                r = qrot(q, lp)
                p = (p[0] + r[0], p[1] + r[1], p[2] + r[2])
                q = qmul(q, getrot(j))
            return p[1]
        hx = height(ean.bones, xi.get('b_C_Pelvis', 0), xpar, lambda j: ean.bones[j].pos, lambda j: ean.bones[j].rot)
        hs = height(smash, si.get('HipN', 0), spar, lambda j: smash[j][3], lambda j: smash[j][4])
        root_scale = hs / hx if hx else 1.0
    frames = []
    root = xi.get(ROOT_XV2)
    root0 = ean.local(anim, root, 0)[0] if root is not None else (0.0, 0.0, 0.0)
    for f in range(anim.frames):
        xl = [ean.local(anim, i, f) for i in range(len(ean.bones))]
        xw = world_rots([l[1] for l in xl], xpar)
        sw = list(srest)
        out = {}
        for i in range(len(smash)):                 # parents first (vbn order)
            if i in target:
                x = target[i]
                d = qmul(xw[x], qinv(xrest[x]))
                sw[i] = qnorm(qmul(d, srest[i]))
            elif spar[i] >= 0:
                sw[i] = qmul(sw[spar[i]], smash[i][4])
            lq = sw[i] if spar[i] < 0 else qnorm(qmul(qinv(sw[spar[i]]), sw[i]))
            out[sname[i]] = (smash[i][3], lq, smash[i][5])
        if root is not None and ROOT_SMASH in out:
            p = xl[root][0]
            out[ROOT_SMASH] = (tuple((p[k] - root0[k]) * root_scale for k in range(3)), out[ROOT_SMASH][1],
                               out[ROOT_SMASH][2])
        frames.append(out)
    return frames


def to_omo(frames, base_data, smash):
    """an OMO with base_data's node list and order (vbn order: the game reads the gameplay joints by position)"""
    import omo
    o = omo.Omo(base_data)
    o.frames = len(frames)
    for n in o.nodes:
        n[3] = [b''] * o.frames
    byhash = {b[2]: b[0] for b in smash}
    for n in list(o.nodes):
        name = byhash.get(n[1])
        tr = omo.tracks(o, n[1])
        vals = [fr[name] for fr in frames]
        omo.set_node(o, n[1], [v[0] for v in vals] if 'pos' in tr else None,
                     [v[1] for v in vals] if 'rot' in tr else None, [v[2] for v in vals] if 'scl' in tr else None)
    return o


# ---------------------------------------------------------------- self-test
def selftest():
    bad = []

    def check(name, ok):
        print(('ok   ' if ok else 'FAIL ') + name)
        if not ok:
            bad.append(name)
    rx90 = (math.sin(math.pi / 4), 0.0, 0.0, math.cos(math.pi / 4))
    bones = [Bone('b_C_Base', -1, (0, 0, 0), (0, 0, 0, 1), (1, 1, 1)),
             Bone('b_C_Pelvis', 0, (0, 1.0, 0), (0, 0, 0, 1), (1, 1, 1)),
             Bone('b_L_Arm1', 1, (0.2, 0.5, 0), (0, 0, 0, 1), (1, 1, 1))]
    anim = Animation('test', 11, {0: {0: Component(0, [0, 10], [(0, 0, 0), (0, 0, 2.0)])},
                                  2: {1: Component(1, [0, 10], [(0, 0, 0, 1), rx90])}})
    for half in (False, True):
        e = Ean(write_ean(bones, [anim], half=half))
        check('read back (%s): bones, names, parents' % ('half' if half else 'float'),
              [(b.name, b.parent) for b in e.bones] == [(b.name, b.parent) for b in bones])
        a = e.animations[0]
        check('read back: name, frames, keys', (a.name, a.frames, sorted(a.nodes)) == ('test', 11, [0, 2]))
        q = e.local(a, 2, 10)[1]
        check('read back: the end rotation', all(abs(x - y) < 2e-3 for x, y in zip(q, rx90)))
        q5 = e.local(a, 2, 5)[1]
        check('slerp halfway: 45 degrees about X', abs(2 * math.degrees(math.acos(q5[3])) - 45.0) < 0.5)
    # retarget onto a small Smash-like skeleton with a different rest (its arm already turned)
    rz = euler_xyz(0, 0, 0.5)
    smash = [('TransN', -1, 1, (0, 0, 0), (0, 0, 0, 1), (1, 1, 1)), ('HipN', 0, 2, (0, 6.0, 0), (0, 0, 0, 1), (1, 1, 1)),
             ('LShoulderJ', 1, 3, (1, 3, 0), rz, (1, 1, 1))]
    e = Ean(write_ean(bones, [anim]))
    fr = retarget(e, e.animations[0], smash)
    check('retarget frame 0 = the Smash rest', all(abs(x - y) < 1e-6 for x, y in zip(fr[0]['LShoulderJ'][1], rz)))
    w10 = fr[10]['LShoulderJ'][1]
    want = qnorm(qmul(rx90, rz))
    check('retarget: the same world turn (90 about X) on the Smash bone', all(abs(x - y) < 2e-3 for x, y in
                                                                            zip(w10, want)))
    check('retarget: root moved x the pelvis heights (6 / 1)', abs(fr[10]['TransN'][0][2] - 12.0) < 1e-3)
    print('%d problem(s)' % len(bad))
    return not bad


def main():
    a = sys.argv[1:]
    if a == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if len(a) >= 2 and a[0] == 'dump':
        e = Ean(open(a[1], 'rb').read())
        print('%d bones: %s' % (len(e.bones), ', '.join(b.name for b in e.bones)))
        for i, an in enumerate(e.animations):
            if an:
                print('#%d %s: %d frames, %d bones keyed' % (i, an.name, an.frames, len(an.nodes)))
        return
    if len(a) >= 6 and a[0] == 'omo':
        e = Ean(open(a[1], 'rb').read())
        smash = vbn_rest(a[3])
        frames = retarget(e, e.animations[int(a[2])], smash)
        o = to_omo(frames, open(a[4], 'rb').read(), smash)
        open(a[5], 'wb').write(o.encode())
        print('%s: %d frames' % (a[5], o.frames))
        return
    sys.exit(__doc__)


if __name__ == '__main__':
    main()
