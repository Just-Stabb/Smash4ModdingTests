#!/usr/bin/env python3
"""Read / write MTA4 material animations (a model folder's model.mta: per material, animated
NUD material properties, e.g. NU_finalColorGain, frame by frame).

Layout (big-endian, as Battlefield's; Smash Forge's MTA.cs for the fields): header 'MTA4', 9,
frame count, start, end, frame rate, material count, its table's offset (0x38), visibility count
and offset, 16 zero bytes; the material table; per material: name offset, hash (the NUD
material's NU_materialHash, its float's bits), property count and table offset, a has-pattern
byte, pattern offset (the end of the file without one), second name offset, second hash; its
name; its property table; per property: name offset, 1, value count, frame count, 0 or 1 (UV
properties 1), type (1 a value a frame, 2 constant), data offset, 8 zero bytes; its name; its
values. Each block from a 32-byte boundary. Texture patterns and visibility entries: read only.

  python3 tools/mta.py FILE...       what each animates
"""
import struct
import sys


def _cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('latin1')


def read(d):
    """{'frames', 'rate', 'unk', 'mats': [{'name', 'hash', 'props': [{'name', 'u1', 'u2', 'type',
    'values': [[floats] a frame]}], 'pattern'}], 'vis': [...]}"""
    assert d[:4] == b'MTA4', d[:4]
    unk, frames, _start, _end, rate, mc, mo, vc, vo = struct.unpack('>9I', d[4:40])
    out = dict(unk=unk, frames=frames, rate=rate, mats=[], vis=[])
    for i in range(mc):
        e = struct.unpack('>I', d[mo + 4 * i:mo + 4 * i + 4])[0]
        no, mh, pc, pp, has_pat = struct.unpack('>IIIIB', d[e:e + 17])
        po, sno, mh2 = struct.unpack('>III', d[e + 20:e + 32])
        m = dict(name=_cstr(d, no), hash=mh, hash2=mh2, name2=_cstr(d, sno) if sno else None, props=[],
                 pattern=None)
        for k in range(pc):
            q = struct.unpack('>I', d[pp + 4 * k:pp + 4 * k + 4])[0]
            pn, u1, count, fc, u2, typ, do = struct.unpack('>IIIIHHI', d[q:q + 24])
            values = [list(struct.unpack('>%df' % count, d[do + j * 4 * count:do + (j + 1) * 4 * count]))
                      for j in range(fc)]
            m['props'].append(dict(name=_cstr(d, pn), u1=u1, u2=u2, type=typ, values=values))
        if has_pat:
            pd = struct.unpack('>I', d[po:po + 4])[0]
            if pd:
                default, kc, ko, pfc, pu = struct.unpack('>iIIIi', d[pd:pd + 20])
                m['pattern'] = dict(default=default, frames=pfc + 1, unk=pu,
                                    keys=[struct.unpack('>ii', d[ko + 8 * j:ko + 8 * j + 8]) for j in range(kc)])
        out['mats'].append(m)
    for i in range(vc):
        e = struct.unpack('>I', d[vo + 4 * i:vo + 4 * i + 4])[0]
        no, u1, do = struct.unpack('>III', d[e:e + 12])
        fc, u2, kc, ko = struct.unpack('>IHhI', d[do:do + 12])
        out['vis'].append(dict(name=_cstr(d, no), u1=u1, frames=fc, u2=u2,
                               keys=[struct.unpack('>hBB', d[ko + 4 * j:ko + 4 * j + 4]) for j in range(kc)]))
    return out


ALIGN = 32


def _pad(b, n=ALIGN):
    return b + b'\0' * (-len(b) % n)


def write(frames, mats, rate=60, unk=9):
    """mats: [{'name', 'hash', 'props': [{'name', 'values', 'u1'=1, 'u2'=0, 'type'=1 or 2}]}]
    (no texture patterns, no visibility)"""
    out = bytearray(b'MTA4' + struct.pack('>9I', unk, frames, 0, frames - 1, rate, len(mats),
                                          0x38 if mats else 0, 0, 0) + b'\0' * 16)
    table = len(out)
    out += b'\0' * (4 * len(mats))

    def align():
        out.extend(b'\0' * (-len(out) % ALIGN))

    def put(at, fmt, *v):
        struct.pack_into(fmt, out, at, *v)

    for i, m in enumerate(mats):
        align()
        e = len(out)
        put(table + 4 * i, '>I', e)
        out += struct.pack('>IIIIB3xIII', e + 0x20, m['hash'] & 0xFFFFFFFF, len(m['props']), 0, 0, 0, 0, 0)
        out += _pad(m['name'].encode('latin1') + b'\0', 4)
        put(e + 12, '>I', len(out))                 # the property table
        ptable = len(out)
        out += b'\0' * (4 * len(m['props']))
        for k, p in enumerate(m['props']):
            vals = p['values']
            count = len(vals[0])
            align()
            q = len(out)
            put(ptable + 4 * k, '>I', q)
            out += struct.pack('>IIIIHHI8x', q + 0x20, p.get('u1', 1), count, len(vals), p.get('u2', 0),
                               p.get('type', 1 if len(vals) > 1 else 2), 0)
            out += _pad(p['name'].encode('latin1') + b'\0')
            put(q + 20, '>I', len(out))             # the values
            out += b''.join(struct.pack('>%df' % count, *v) for v in vals)
        put(e + 20, '>I', len(out))                 # the pattern offset: the material's end, without one
    return bytes(out)


def main():
    for f in sys.argv[1:]:
        m = read(open(f, 'rb').read())
        print('%s: %d frames' % (f, m['frames']))
        for e in m['mats']:
            print('  %s %#010x' % (e['name'], e['hash']), 'pattern' if e['pattern'] else '')
            for p in e['props']:
                print('    %-22s %d frames, type %d' % (p['name'], len(p['values']), p['type']))
        for v in m['vis']:
            print('  visibility', v['name'], v['keys'][:4])


if __name__ == '__main__':
    main()
