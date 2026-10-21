#!/usr/bin/env python3
"""Read / edit a model folder's model.xmb (big-endian: header, entries, properties, the names
pool, the values pool at the end of the file). Battlefield's say how a folder is drawn:
lightset, draw_range, drawing_order (far to near: sky 0, moon 2, sun 4, background 5-9, near
objects 12-18), ...

  python3 tools/xmb.py FILE...        the entries and their properties
"""
import struct
import sys


def _cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('latin1')


def _layout(d):
    assert d[:4] == b'XMB ', d[:4]
    _m, ne, _np, _nv, _a, _b, eoff, poff, s1, _s2, voff = struct.unpack('>4s10I', d[:44])
    return ne, eoff, poff, s1, voff


def parse(d):
    """[(entry name, {key: value})]"""
    ne, eoff, poff, s1, voff = _layout(d)
    out = []
    for i in range(ne):
        noff, n, _nch, first = struct.unpack('>IHHH', d[eoff + 16 * i:eoff + 16 * i + 10])
        props = {}
        for k in range(first, first + n):
            ko, vo = struct.unpack('>II', d[poff + 8 * k:poff + 8 * k + 8])
            props[_cstr(d, s1 + ko)] = _cstr(d, voff + vo)
        out.append((_cstr(d, s1 + noff), props))
    return out


def edit(d, changes):
    """changes {entry name: {key: value}}: each property pointed at its new value, a string of
    the values pool or one added at its end (the pool is the end of the file)"""
    d = bytearray(d)
    ne, eoff, poff, s1, voff = _layout(d)
    pool = bytes(d[voff:]).rstrip(b'\0') + b'\0'
    strings = {}
    o = 0
    for s in pool.split(b'\0')[:-1]:
        strings.setdefault(s.decode('latin1'), o)
        o += len(s) + 1
    done = set()
    for i in range(ne):
        noff, n, _nch, first = struct.unpack('>IHHH', d[eoff + 16 * i:eoff + 16 * i + 10])
        name = _cstr(d, s1 + noff)
        for k in range(first, first + n):
            key = _cstr(d, s1 + struct.unpack('>I', d[poff + 8 * k:poff + 8 * k + 4])[0])
            if key in changes.get(name, {}):
                v = changes[name][key]
                if v not in strings:
                    strings[v] = len(pool)
                    pool += v.encode('latin1') + b'\0'
                d[poff + 8 * k + 4:poff + 8 * k + 8] = struct.pack('>I', strings[v])
                done.add((name, key))
    missing = {(n, k) for n, kv in changes.items() for k in kv} - done
    assert not missing, missing
    pool += b'\0' * (-(voff + len(pool)) % 4)
    return bytes(d[:voff]) + pool


def main():
    for f in sys.argv[1:]:
        print(f, [(n, p) for n, p in parse(open(f, 'rb').read()) if p])


if __name__ == '__main__':
    main()
