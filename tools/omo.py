#!/usr/bin/env python3
"""Smash 4 animation files: OMO (bone animation), the KCAP .pac that holds them, and model.vbn
bones. Big-endian (Wii U).

OMO layout (worked out from Kirby's files, see fighters/kirby/specials.md "Marth copy sword"):
  0x00 "OMO "  0x04 u16 1, u16 3  0x08 u32 (kept)  0x0C u16 (kept), u16 node count
  0x10 u16 frame count, u16 frame size  0x14 node table offset  0x18 constants offset
  0x1C frame data offset (frame count x frame size bytes)
Node (16 bytes): flags, bone hash, offset into the constants, offset into each frame's record.
Flags: 0x01000000 position, 0x02000000 rotation, 0x04000000 scale; data in that order.
  position (bits 16-23): 0x08 interpolated (6 floats min / range, 3 u16 a frame),
                         0x20 constant (3 floats), 0x04 a float vector a frame
  rotation (bits 12-15): 5 interpolated quaternion x y z (w >= 0 from them), 7 constant x y z,
                         6 x y constant + z interpolated (4 floats: x, y, z min, z range; 1 u16)
  scale (bits 0-11):     0x081 interpolated, 0x201 constant
"""
import math
import struct

POS, ROT, SCL = 0x01000000, 0x02000000, 0x04000000


# ---------------------------------------------------------------- KCAP .pac
def pac_read(path):
    """[(name, bytes)] in file order"""
    b = open(path, 'rb').read()
    assert b[:4] == b'KCAP', path
    n = struct.unpack('>I', b[8:12])[0]
    names = struct.unpack('>%dI' % n, b[0x10:0x10 + 4 * n])
    offs = struct.unpack('>%dI' % n, b[0x10 + 4 * n:0x10 + 8 * n])
    sizes = struct.unpack('>%dI' % n, b[0x10 + 8 * n:0x10 + 12 * n])
    out = []
    for no, o, s in zip(names, offs, sizes):
        out.append((b[no:b.index(b'\0', no)].decode(), b[o:o + s]))
    return out


def _align(x, a):
    return (x + a - 1) // a * a


def pac_write(path, entries):
    """entries: [(name, bytes)]; written sorted by name (the game looks names up in order)"""
    entries = sorted(entries, key=lambda e: e[0])
    n = len(entries)
    head = 0x10 + 12 * n
    names = b''
    noffs = []
    for name, _ in entries:
        noffs.append(head + len(names))
        names += name.encode() + b'\0'
    pos = _align(head + len(names), 0x10)
    body = b''
    doffs = []
    for i, (_, data) in enumerate(entries):
        doffs.append(pos + len(body))
        body += data
        if i + 1 < n:
            body += b'\0' * (_align(len(body), 0x10) - len(body))
    out = b'KCAP' + struct.pack('>III', 0, n, 0)
    out += struct.pack('>%dI' % n, *noffs) + struct.pack('>%dI' % n, *doffs)
    out += struct.pack('>%dI' % n, *[len(d) for _, d in entries])
    out += names
    out += b'\0' * (pos - len(out))
    out += body
    open(path, 'wb').write(out)


# ---------------------------------------------------------------- VBN
def vbn_read(path):
    """[(name, parent index, hash)]"""
    d = open(path, 'rb').read()
    e = '<' if d[:4] == b' NBV' else '>'
    count = struct.unpack(e + 'I', d[8:12])[0]
    out = []
    off = 28
    for _ in range(count):
        name = d[off:off + 64].split(b'\0')[0].decode()
        _t, parent, h = struct.unpack(e + 'IiI', d[off + 64:off + 76])
        out.append((name, parent, h))
        off += 76
    return out


def vbn_write(bones):
    """[(name, parent index or -1, hash)] -> a big-endian model.vbn as Battlefield's stage ones
    ('VBN ', version 1.2, every bone type 0, at the origin, unrotated, scale 1)"""
    out = struct.pack('>4sHHI4I', b'VBN ', 1, 2, len(bones), len(bones), 0, 0, 0)
    for name, parent, h in bones:
        out += name.encode().ljust(64, b'\0') + struct.pack('>IiI', 0, 0x0FFFFFFF if parent < 0 else parent, h)
    for _ in bones:
        out += struct.pack('>9f', 0, 0, 0, 0, 0, 0, 1, 1, 1)
    return out


# ---------------------------------------------------------------- OMO
def _sizes(flags):
    """(constants bytes, frame bytes) of each present track: [(kind, type, csize, fsize)]"""
    tr = []
    if flags & POS:
        t = (flags >> 16) & 0xFF
        tr.append(('pos', t, {0x08: 24, 0x20: 12, 0x04: 0}[t], {0x08: 6, 0x20: 0, 0x04: 12}[t]))
    if flags & ROT:
        t = (flags >> 12) & 0xF
        tr.append(('rot', t, {5: 24, 7: 12, 6: 16, 10: 0}[t], {5: 6, 7: 0, 6: 2, 10: 8}[t]))
    if flags & SCL:
        t = flags & 0xFFF
        tr.append(('scl', t, {0x081: 24, 0x201: 12}[t], {0x081: 6, 0x201: 0}[t]))
    return tr


def _rot10(kb):
    """rotation type 10 (Smash Forge OMOOld.cs): three 20-bit components in [-1/sqrt2, 1/sqrt2]
    and a 4-bit index of the left-out (largest, positive) one, as a quaternion (x, y, z, w)"""
    b = kb
    f = ((b[0] << 12) | (b[1] << 4) | (b[2] >> 4), ((b[2] & 0xF) << 16) | (b[3] << 8) | b[4],
         (b[5] << 12) | (b[6] << 4) | (b[7] >> 4))
    s1 = 1 / math.sqrt(2.0)
    c = [x * 2 * s1 / 1048575.0 - s1 for x in f]
    miss = b[7] & 0xF
    c.insert(miss, math.sqrt(max(0.0, 1.0 - sum(x * x for x in c))))
    return tuple(c)


class Omo:
    def __init__(self, data):
        d = data
        assert d[:4] == b'OMO ', d[:4]
        self.head = d[4:0x0E]                       # versions, flags, u16 (kept as they are)
        nc, self.frames, fs = struct.unpack('>HHH', d[0x0E:0x14])
        no, co, fo = struct.unpack('>III', d[0x14:0x20])
        self.nodes = []                              # [flags, hash, const bytes, [frame bytes]]
        raw = [struct.unpack('>IIII', d[no + 16 * k:no + 16 * k + 16]) for k in range(nc)]
        for f, h, ci, ki in raw:
            cs = sum(t[2] for t in _sizes(f))
            ks = sum(t[3] for t in _sizes(f))
            consts = d[co + ci:co + ci + cs]
            keys = [d[fo + fr * fs + ki:fo + fr * fs + ki + ks] for fr in range(self.frames)]
            self.nodes.append([f, h, consts, keys])

    def encode(self):
        nc = len(self.nodes)
        fs = sum(sum(t[3] for t in _sizes(n[0])) for n in self.nodes)
        no = 0x20
        co = no + 16 * nc
        consts = b''
        table = b''
        ki = 0
        for f, h, c, k in self.nodes:
            table += struct.pack('>IIII', f, h, len(consts), ki)
            consts += c
            ki += sum(t[3] for t in _sizes(f))
        fo = co + len(consts)
        frames = b''.join(b''.join(n[3][fr] for n in self.nodes) for fr in range(self.frames))
        head = b'OMO ' + self.head + struct.pack('>HHH', nc, self.frames, fs) + struct.pack('>III', no, co, fo)
        return head + table + consts + frames

    def node(self, h):
        for n in self.nodes:
            if n[1] == h:
                return n
        return None

    def sample(self, h, fr):
        """local (pos, quat xyzw, scale) of bone hash h at frame fr, or None"""
        n = self.node(h)
        if n is None:
            return None
        f, _h, c, keys = n
        ci = ki = 0
        k = keys[fr]
        pos, rot, scl = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0)
        for kind, t, cs, ks in _sizes(f):
            cf = struct.unpack('>%df' % (cs // 4), c[ci:ci + cs]) if cs else ()
            kb = k[ki:ki + ks]
            if (kind in ('pos', 'scl') and t in (0x08, 0x081)) or (kind == 'rot' and t == 5):
                u = struct.unpack('>3H', kb)
                v = tuple(cf[i] + cf[3 + i] * u[i] / 65535.0 for i in range(3))
            elif kind == 'pos' and t == 0x04:
                v = struct.unpack('>3f', kb)
            elif kind == 'rot' and t == 10:
                v = _rot10(kb)
            elif kind == 'rot' and t == 6:
                u = struct.unpack('>H', kb)[0]
                v = (cf[0], cf[1], cf[2] + cf[3] * u / 65535.0)
            else:
                v = cf
            if kind == 'pos':
                pos = v
            elif kind == 'rot' and t == 10:
                rot = v
            elif kind == 'rot':
                w2 = 1.0 - (v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
                rot = (v[0], v[1], v[2], math.sqrt(max(0.0, w2)))
            else:
                scl = v
            ci += cs
            ki += ks
        return pos, rot, scl


def interp_track(values):
    """per-frame 3-vectors -> (constants, [frame bytes]) for an interpolated track"""
    lo = [min(v[i] for v in values) for i in range(3)]
    hi = [max(v[i] for v in values) for i in range(3)]
    rng = [hi[i] - lo[i] for i in range(3)]
    c = struct.pack('>6f', *(lo + rng))
    keys = []
    for v in values:
        u = [int(round((v[i] - lo[i]) / rng[i] * 65535)) if rng[i] > 0 else 0 for i in range(3)]
        keys.append(struct.pack('>3H', *u))
    return c, keys


def set_node_full(omo, h, pos, rot, scl):
    """replace bone h's tracks with interpolated position, rotation (x y z of quaternions with
    w >= 0) and scale, one value a frame"""
    set_node(omo, h, pos, rot, scl)


def set_node(omo, h, pos=None, rot=None, scl=None):
    """set_node_full with only the given tracks (None: the bone has no such track)"""
    f = 0
    consts = b''
    keys = [b''] * omo.frames
    for vals, bit, kind in ((pos, POS, 0x08 << 16), (rot, ROT, 5 << 12), (scl, SCL, 0x081)):
        if vals is None:
            continue
        if bit == ROT:
            vals = [(-q[0], -q[1], -q[2]) if q[3] < 0 else q[:3] for q in vals]
        c, k = interp_track(vals)
        f |= bit | kind
        consts += c
        keys = [keys[i] + k[i] for i in range(omo.frames)]
    n = omo.node(h)
    data = [f, h, consts, keys]
    if n is None:
        omo.nodes.append(data)
    else:
        n[:] = data


def tracks(omo, h):
    """the tracks bone h has: a subset of ('pos', 'rot', 'scl')"""
    n = omo.node(h)
    if n is None:
        return ()
    return tuple(k for k, bit in (('pos', POS), ('rot', ROT), ('scl', SCL)) if n[0] & bit)


# ---------------------------------------------------------------- math (4x4 row-major, column vectors)
def qmat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def trs(p, q, s):
    r = qmat(q)
    return [[r[i][0] * s[0], r[i][1] * s[1], r[i][2] * s[2], p[i]] for i in range(3)] + [[0, 0, 0, 1]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inv(m):
    """inverse of an affine matrix"""
    a = [row[:3] for row in m[:3]]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    ia = [[(a[(j + 1) % 3][(i + 1) % 3] * a[(j + 2) % 3][(i + 2) % 3] - a[(j + 1) % 3][(i + 2) % 3] * a[(j + 2) % 3][(i + 1) % 3]) / det
           for j in range(3)] for i in range(3)]
    t = [m[i][3] for i in range(3)]
    it = [-sum(ia[i][k] * t[k] for k in range(3)) for i in range(3)]
    return [ia[i] + [it[i]] for i in range(3)] + [[0, 0, 0, 1]]


def decompose(m):
    """affine matrix (no shear) -> (pos, quat xyzw, scale)"""
    p = tuple(m[i][3] for i in range(3))
    cols = [[m[i][j] for i in range(3)] for j in range(3)]
    s = [math.sqrt(sum(c * c for c in col)) for col in cols]
    r = [[cols[j][i] / s[j] for j in range(3)] for i in range(3)]
    return p, mat2q(r), tuple(s)


def mat2q(r):
    tr = r[0][0] + r[1][1] + r[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s, (r[1][0] - r[0][1]) / s, 0.25 * s)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2
        q = (0.25 * s, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s, (r[2][1] - r[1][2]) / s)
    elif r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2
        q = ((r[0][1] + r[1][0]) / s, 0.25 * s, (r[1][2] + r[2][1]) / s, (r[0][2] - r[2][0]) / s)
    else:
        s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2
        q = ((r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, 0.25 * s, (r[1][0] - r[0][1]) / s)
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def world(omo, bones, fr):
    """{bone name: world matrix} at frame fr (bones from vbn_read; bones the animation lacks use
    identity, which only matters for bones it doesn't animate)"""
    out = {}
    for i, (name, parent, h) in enumerate(bones):
        s = omo.sample(h, fr)
        local = trs(*s) if s else trs((0, 0, 0), (0, 0, 0, 1), (1, 1, 1))
        out[name] = mul(out[bones[parent][0]], local) if 0 <= parent < len(bones) else local
    return out
