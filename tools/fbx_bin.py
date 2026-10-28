#!/usr/bin/env python3
"""Minimal binary FBX (7.x) reader: the node tree with properties, arrays decompressed.

  python3 tools/fbx_bin.py FILE.fbx [--tree DEPTH]

Node = (name, [properties], [children]). Properties: ints, floats, strings (bytes), raw
(bytes) and arrays (lists). Enough to read animation exports (Objects / Connections /
GlobalSettings); no writing.
"""
import struct
import sys
import zlib

ARRAY = {b'f': ('f', 4), b'd': ('d', 8), b'l': ('q', 8), b'i': ('i', 4), b'b': ('b', 1)}


def _prop(d, o):
    t = d[o:o + 1]
    o += 1
    if t == b'Y':
        return struct.unpack_from('<h', d, o)[0], o + 2
    if t == b'C':
        return d[o] != 0, o + 1
    if t == b'I':
        return struct.unpack_from('<i', d, o)[0], o + 4
    if t == b'F':
        return struct.unpack_from('<f', d, o)[0], o + 4
    if t == b'D':
        return struct.unpack_from('<d', d, o)[0], o + 8
    if t == b'L':
        return struct.unpack_from('<q', d, o)[0], o + 8
    if t in (b'S', b'R'):
        n = struct.unpack_from('<I', d, o)[0]
        return d[o + 4:o + 4 + n], o + 4 + n
    if t in ARRAY:
        n, enc, clen = struct.unpack_from('<III', d, o)
        o += 12
        raw = d[o:o + clen]
        if enc == 1:
            raw = zlib.decompress(raw)
        fmt, _sz = ARRAY[t]
        return list(struct.unpack('<%d%s' % (n, fmt), raw)), o + clen
    raise ValueError('property type %r at 0x%x' % (t, o - 1))


def _node(d, o, wide):
    if wide:
        end, nprops, _plen = struct.unpack_from('<QQQ', d, o)
        o += 24
    else:
        end, nprops, _plen = struct.unpack_from('<III', d, o)
        o += 12
    nl = d[o]
    name = d[o + 1:o + 1 + nl].decode('latin-1')
    o += 1 + nl
    if end == 0:
        return None, o
    props = []
    for _ in range(nprops):
        v, o = _prop(d, o)
        props.append(v)
    kids = []
    null = 25 if wide else 13
    while o < end - null:
        k, o = _node(d, o, wide)
        if k is None:
            break
        kids.append(k)
    return (name, props, kids), end


def load(path):
    d = open(path, 'rb').read()
    assert d[:20] == b'Kaydara FBX Binary  ', 'not a binary FBX'
    ver = struct.unpack_from('<I', d, 23)[0]
    wide = ver >= 7500
    o, nodes = 27, []
    while o < len(d):
        n, o = _node(d, o, wide)
        if n is None:
            break
        nodes.append(n)
    return ver, nodes


def find(nodes, name):
    return [n for n in nodes if n[0] == name]


def props70(node):
    """Properties70 P entries -> {name: [values]}"""
    out = {}
    for p70 in find(node[2], 'Properties70'):
        for p in p70[2]:
            if p[0] == 'P':
                out[p[1][0].decode('latin-1')] = p[1][4:]
    return out


def _tree(nodes, depth, ind=0):
    for name, props, kids in nodes:
        ps = [(p if not isinstance(p, list) else '[%d]' % len(p)) for p in props][:6]
        print('  ' * ind + name, ps)
        if depth > 1:
            _tree(kids, depth - 1, ind + 1)


if __name__ == '__main__':
    ver, nodes = load(sys.argv[1])
    print('FBX', ver)
    _tree(nodes, int(sys.argv[3]) if len(sys.argv) > 3 else 2)
