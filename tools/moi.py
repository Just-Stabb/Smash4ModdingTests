#!/usr/bin/env python3
"""model.moi (a fighter model's mesh table; docs/ultimate-fighter-port.md): read / write / add meshes.

Layout (big-endian): header 0x30 bytes: count1, count2, offset1 (0x30), entry1 size (0x20), entry2 size (8), 0x30,
offset2, 0 ...; table 1 at offset1, one 0x20 entry per NUD mesh in NUD order: {name prefix offset (the mesh's name
without its "VIS_O_OBJ" tail), a hash of it, 1 for a _VIS_ mesh (0 otherwise), the mesh's bone (0xFFFF none), the mesh
index, 12 zero bytes}, then their strings (NUL-ended, 4-aligned); table 2 at offset2 (16-aligned), 8-byte entries
{name prefix offset, u16 1, u16 the mesh index or 0xFFFF (names of no mesh in this model)}, then their strings;
the file padded to 16.
Every vanilla model checked has table 1's count = its model.nud's mesh count (tools/supamario_ui_model.py: copies
appended to a NUD get their entries here too). The hash's function isn't known (not CRC32 / FNV / djb2 of the
prefix): an added entry gets the prefix's CRC32 (flagged)."""
import struct
import zlib


def read(d):
    h = struct.unpack('>8I', d[:32])
    n1, n2, o1, s1, s2, _x, o2 = h[:7]
    assert (s1, s2) == (0x20, 8), h

    def cstr(o):
        return d[o:d.index(b'\0', o)].decode('latin1')
    t1 = []
    for i in range(n1):
        so, hs, vis, bone, idx = struct.unpack('>IIIII', d[o1 + i * s1:o1 + i * s1 + 20])
        t1.append(dict(name=cstr(so), hash=hs, vis=vis, bone=bone, index=idx))
    t2 = []
    for i in range(n2):
        so, one, idx = struct.unpack('>IHH', d[o2 + i * s2:o2 + i * s2 + 8])
        t2.append(dict(name=cstr(so), one=one, index=idx))
    return dict(head=h, t1=t1, t2=t2)


def _strings(base, names):
    out, offs = b'', []
    for n in names:
        offs.append(base + len(out))
        b = n.encode('latin1') + b'\0'
        out += b + b'\0' * (-len(b) % 4)
    return out, offs


def write(m):
    h = list(m['head'])
    t1, t2 = m['t1'], m['t2']
    o1 = 0x30
    s1_base = o1 + 0x20 * len(t1)
    s1, offs1 = _strings(s1_base, [e['name'] for e in t1])
    o2 = s1_base + len(s1)
    o2 += -o2 % 16
    s2_base = o2 + 8 * len(t2)
    s2, offs2 = _strings(s2_base, [e['name'] for e in t2])
    h[0], h[1], h[2], h[6] = len(t1), len(t2), o1, o2
    out = bytearray(struct.pack('>8I', *h) + b'\0' * 16)
    for e, so in zip(t1, offs1):
        out += struct.pack('>IIIII', so, e['hash'], e['vis'], e['bone'], e['index']) + b'\0' * 12
    out += s1
    out += b'\0' * (o2 - len(out))
    for e, so in zip(t2, offs2):
        out += struct.pack('>IHH', so, e['one'], e['index'])
    out += s2
    out += b'\0' * (-len(out) % 16)
    return bytes(out)


def prefix(mesh_name):
    """the moi's name for a NUD mesh: its name without the VIS_O_OBJ tail (Mario_Hair_VIS_O_OBJ -> Mario_Hair_)"""
    return mesh_name[:-len('VIS_O_OBJ')] if mesh_name.endswith('VIS_O_OBJ') else mesh_name


def add_meshes(d, meshes):
    """the moi's bytes with entries for meshes appended to the NUD: MESHES [(NUD mesh name, its index, its bone)]
    (table 1, and table 2 for a _VIS_ mesh). Every existing entry kept in order"""
    m = read(d)
    for name, idx, bone in meshes:
        assert idx == len(m['t1']), (name, idx, len(m['t1']))
        p = prefix(name)
        vis = 1 if '_VIS_' in name else 0
        m['t1'].append(dict(name=p, hash=zlib.crc32(p.encode()) & 0xFFFFFFFF, vis=vis, bone=bone & 0xFFFF, index=idx))
        if vis:
            m['t2'].append(dict(name=p, one=1, index=idx))
    return write(m)
