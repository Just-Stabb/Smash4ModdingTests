#!/usr/bin/env python3
"""Smash 4 models (.nud, NDP3 big-endian): read and write.

  python3 tools/nud.py info FILE.nud     meshes, polygons (vertex / index formats) and materials

Layout as Smash Forge's NUD.cs (MIT): a 0x30 header, a 0x30 entry per mesh, a 0x30 entry per
polygon, the materials (0x20 + 0x18 a texture + properties), then the index, vertex, "vertex add"
(bone weights) sections and the names. Written polygons are unrigged triangle lists: positions
as floats, normals as half floats (vertex type 6) or none (0), byte vertex colors (127 = 1.0),
half float UVs, and single-bound to a bone (mesh bind method 0 / bone index) like Battlefield's
static models.
"""
import struct
import sys
import zlib

import numpy as np


class Material:
    def __init__(self, flags=0, src=0, dst=0, alpha_func=0, ref_alpha=0, cull=0, unk2=0, zbuf=0):
        self.flags, self.src, self.dst = flags, src, dst
        self.alpha_func, self.ref_alpha, self.cull, self.unk2, self.zbuf = alpha_func, ref_alpha, cull, unk2, zbuf
        self.textures = []      # [dict(hash, map_mode, wrap_s, wrap_t, min_f, mag_f, mip, unk, unk2)]
        self.props = []         # [(name, [floats])]

    def copy(self):
        m = Material(self.flags, self.src, self.dst, self.alpha_func, self.ref_alpha, self.cull, self.unk2, self.zbuf)
        m.textures = [dict(t) for t in self.textures]
        m.props = [(n, list(v)) for n, v in self.props]
        return m


class Polygon:
    def __init__(self):
        self.pos = None         # [n, 3] float
        self.nrm = None         # [n, 3] or None
        self.col = None         # [n, 4] 0-255 (128 = 1.0) or None
        self.uvs = []           # [[n, 2]]
        self.idx = None         # [m] triangle list
        self.materials = []
        self.vert_size = 0      # as read
        self.uv_size = 0
        self.strip = 0x40


class Mesh:
    def __init__(self, name, polygons=None, bone=-1, bind=0, sort_bias=0.0):
        self.name = name
        self.polygons = polygons or []
        self.bone, self.bind, self.sort_bias = bone, bind, sort_bias
        self.sphere = None


def _half(a):
    return np.asarray(a, dtype='>f2')


def _sphere(pos):
    lo, hi = pos.min(0), pos.max(0)
    c = (lo + hi) / 2
    return [float(c[0]), float(c[1]), float(c[2]), float(np.sqrt(((pos - c) ** 2).sum(1)).max())]


# ---------------------------------------------------------------- read
def read(path):
    d = open(path, 'rb').read()
    if d[:2] == b'\x78\x9c':
        d = zlib.decompress(d)
    assert d[:4] == b'NDP3', d[:4]
    _, version, nmesh, bstart, bend, pstart, psize, vsize, vasize = struct.unpack('>IHhhhiiii', d[4:0x20])
    poly_base = 0x30 + pstart
    vert_base = poly_base + psize
    va_base = vert_base + vsize
    str_base = va_base + vasize
    meshes = []
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        f = struct.unpack('>8f', d[o:o + 32])
        name_off, _, bind, bone, npoly, obj = struct.unpack('>iHHhhi', d[o + 32:o + 48])
        name = d[str_base + name_off:d.index(b'\0', str_base + name_off)].decode()
        m = Mesh(name, bone=bone, bind=bind, sort_bias=f[7])
        m.sphere = f[:4]
        for j in range(npoly):
            p = Polygon()
            q = obj + j * 0x30
            poff, voff, vaoff, nv, vs, us = struct.unpack('>iiiHBB', d[q:q + 16])
            texoffs = struct.unpack('>4i', d[q + 16:q + 32])
            nidx, sf = struct.unpack('>HH', d[q + 32:q + 36])
            p.vert_size, p.uv_size, p.strip = vs, us, sf >> 8
            p.idx = np.frombuffer(d, '>u2', nidx, poly_base + poff).astype(np.int64)
            p.nv, p.voff, p.vaoff = nv, vert_base + voff, va_base + vaoff
            if vs >> 4 == 0:
                _read_vertices(d, p)
            for to in texoffs:
                if to:
                    p.materials.append(_read_material(d, to, str_base))
            m.polygons.append(p)
        meshes.append(m)
    return meshes


def _read_vertices(d, p):
    """unrigged vertices (bone type 0): positions, normals, colors, UVs"""
    vt, ct, nuv, half = p.vert_size & 0xF, p.uv_size & 0xE, p.uv_size >> 4, not p.uv_size & 1
    cols = [('pos', '>f4', (3,))]
    cols += {0: [('w', '>f4')], 1: [('nrm', '>f4', (5,))], 3: [('nrm', '>f4', (13,))],
             6: [('nrm', '>f2', (4,))], 7: [('nrm', '>f2', (12,))]}[vt]
    if ct == 2:
        cols.append(('col', 'u1', (4,)))
    elif ct == 4:
        cols.append(('col', '>f2', (4,)))
    for i in range(nuv):
        cols.append(('uv%d' % i, '>f2' if half else '>f4', (2,)))
    a = np.frombuffer(d, np.dtype(cols), p.nv, p.voff)
    p.pos = a['pos'].astype(np.float64)
    if vt:
        n = a['nrm'].astype(np.float64)
        p.nrm = n[:, 1:4] if vt in (1, 3) else n[:, :3]
    if ct:
        p.col = a['col'].astype(np.float64) * (255 if ct == 4 else 1)
    p.uvs = [a['uv%d' % i].astype(np.float64) for i in range(nuv)]


def _read_material(d, o, str_base):
    flags, _, src, ntex, dst, af, ra, cull, _, unk2, zbuf = struct.unpack('>IIHHHHHHIIi', d[o:o + 0x20])
    m = Material(flags, src, dst, af, ra, cull, unk2, zbuf)
    o += 0x20
    for _ in range(ntex):
        h, _, _, mm, ws, wt, mn, mg, mip, unk, _, unk2t = struct.unpack('>IIHHBBBBBBIH', d[o:o + 0x18])
        m.textures.append(dict(hash=h, map_mode=mm, wrap_s=ws, wrap_t=wt, min_f=mn, mag_f=mg, mip=mip, unk=unk, unk2=unk2t))
        o += 0x18
    while True:
        nxt, name_off, _, cnt, _ = struct.unpack('>iiHHi', d[o:o + 0x10])
        cnt &= 0xFF
        if name_off or cnt:
            name = d[str_base + name_off:d.index(b'\0', str_base + name_off)].decode()
            m.props.append((name, list(struct.unpack('>%df' % cnt, d[o + 0x10:o + 0x10 + 4 * cnt]))))
        if nxt == 0:
            break
        o += nxt
    return m


# ---------------------------------------------------------------- write
def _vertex_bytes(p):
    n = len(p.pos)
    cols = [('pos', '>f4', (3,))]
    if p.nrm is not None:
        cols.append(('nrm', '>f2', (4,)))
    else:
        cols.append(('w', '>f4'))
    if p.col is not None:
        cols.append(('col', 'u1', (4,)))
    for i in range(len(p.uvs)):
        cols.append(('uv%d' % i, '>f2', (2,)))
    a = np.zeros(n, dtype=cols)
    a['pos'] = p.pos
    if p.nrm is not None:
        nn = np.ones((n, 4))
        nn[:, :3] = p.nrm
        a['nrm'] = nn
    else:
        a['w'] = 1
    if p.col is not None:
        a['col'] = np.clip(np.round(p.col), 0, 255)
    for i, uv in enumerate(p.uvs):
        a['uv%d' % i] = uv
    vs = 6 if p.nrm is not None else 0
    us = (len(p.uvs) << 4) | (2 if p.col is not None else 0)
    return a.tobytes(), vs, us


def write(meshes):
    strs = bytearray()
    name_offs = []
    for m in meshes:
        name_offs.append(len(strs))
        strs += m.name.encode() + b'\0'
        strs += b'\0' * (-len(strs) % 16)
    npoly = sum(len(m.polygons) for m in meshes)
    head_len = 0x30 + 0x30 * len(meshes) + 0x30 * npoly
    objs, mats, polys, verts = bytearray(), bytearray(), bytearray(), bytearray()
    mesh_entries = bytearray()
    all_pos = []
    for m, no in zip(meshes, name_offs):
        pos = np.concatenate([p.pos for p in m.polygons])
        all_pos.append(pos)
        sph = m.sphere or _sphere(pos)
        mesh_entries += struct.pack('>8f', *sph, sph[0], sph[1], sph[2], m.sort_bias)
        mesh_entries += struct.pack('>iHHhhi', no, 0, m.bind, m.bone, len(m.polygons), 0x30 + 0x30 * len(meshes) + len(objs))
        for p in m.polygons:
            vb, vs, us = _vertex_bytes(p)
            texoffs = []
            for mat in p.materials[:4]:
                texoffs.append(head_len + len(mats))
                mats += _material_bytes(mat, strs)
            texoffs += [0] * (4 - len(texoffs))
            assert len(p.pos) < 0x10000 and p.idx.max() < len(p.pos)
            objs += struct.pack('>iiiHBB4iHHiii', len(polys), len(verts), 0, len(p.pos), vs, us, *texoffs,
                                len(p.idx), 0x40 << 8, 0, 0, 0)
            polys += np.asarray(p.idx, dtype='>u2').tobytes()
            verts += vb
    body = bytes(objs) + bytes(mats)
    body += b'\0' * (-(0x30 + len(mesh_entries) + len(body)) % 16)
    pstart = len(mesh_entries) + len(body)
    polys += b'\0' * (-len(polys) % 16)
    verts += b'\0' * (-len(verts) % 16)
    sph = _sphere(np.concatenate(all_pos))
    out = bytearray(b'NDP3' + struct.pack('>IHhhhiiii4f', 0, 0x0200, len(meshes), 0, 0, pstart, len(polys), len(verts), 0, *sph))
    out += mesh_entries + body + polys + verts + strs
    struct.pack_into('>I', out, 4, len(out))
    return bytes(out)


def _material_bytes(mat, strs):
    b = bytearray(struct.pack('>IIHHHHHHIIi', mat.flags, 0, mat.src, len(mat.textures), mat.dst, mat.alpha_func,
                              mat.ref_alpha, mat.cull, 0, mat.unk2, mat.zbuf))
    for t in mat.textures:
        b += struct.pack('>IIHHBBBBBBIH', t['hash'], 0, 0, t['map_mode'], t['wrap_s'], t['wrap_t'], t['min_f'],
                         t['mag_f'], t['mip'], t['unk'], 0, t['unk2'])
    if not mat.props:
        b += b'\0' * 16
    for i, (name, vals) in enumerate(mat.props):
        strs += b'\0' * (-len(strs) % 16)
        b += struct.pack('>iiBBBBi', 0 if i == len(mat.props) - 1 else 16 + 4 * len(vals), len(strs), 0, 0, 0, len(vals), 0)
        strs += name.encode() + b'\0'
        b += struct.pack('>%df' % len(vals), *vals)
    return bytes(b)


def main():
    if sys.argv[1] == 'info':
        for m in read(sys.argv[2]):
            print('mesh %s bone %d bind %d sort %.1f sphere %s' % (m.name, m.bone, m.bind, m.sort_bias,
                                                                   [round(x, 1) for x in m.sphere]))
            for p in m.polygons:
                print('  poly verts %d idx %d vert 0x%02X uv 0x%02X strip 0x%X' % (p.nv, len(p.idx), p.vert_size, p.uv_size, p.strip))
                for mat in p.materials:
                    print('    mat flags 0x%08X src %d dst %d af %d ref %d cull %d unk2 %d zbuf %d' %
                          (mat.flags, mat.src, mat.dst, mat.alpha_func, mat.ref_alpha, mat.cull, mat.unk2, mat.zbuf))
                    for t in mat.textures:
                        print('      tex 0x%08X map %d wrap %d/%d filt %d/%d mip %d unk %d/%d' % (
                            t['hash'], t['map_mode'], t['wrap_s'], t['wrap_t'], t['min_f'], t['mag_f'], t['mip'], t['unk'], t['unk2']))
                    for n, v in mat.props:
                        print('      %s %s' % (n, [round(x, 3) for x in v]))


if __name__ == '__main__':
    main()
