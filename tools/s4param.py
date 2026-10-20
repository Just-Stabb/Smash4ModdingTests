#!/usr/bin/env python3
"""Read / write Smash 4 param files (fighter_param*, ui_*_db.bin, ...).

Layout: FF FF 00 00 and 4 more header bytes, then values, each a type byte and its data (big-endian):
1 u8, 2 s8, 3 u16, 4 s16, 5 u32, 6 s32, 7 float, 8 string (u32 length + bytes), 0x20 = group (u32 entry count; the values up to the next group
or the end split evenly into that many entries).

  python3 tools/s4param.py FILE              dump
"""
import struct
import sys

SIZES = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 4}
UNPACK = {1: '>B', 2: '>b', 3: '>H', 4: '>h', 5: '>I', 6: '>i', 7: '>f'}


def parse(data):
    """[('group', count, [entries: [(type, value)]])] or loose [(type, value)] items"""
    assert data[:4] == b'\xff\xff\x00\x00', 'not a param file'
    i = 8
    items = []
    while i < len(data):
        t = data[i]
        i += 1
        if t == 0x20:
            n = struct.unpack('>I', data[i:i + 4])[0]
            i += 4
            items.append(['group', n, []])
            continue
        if t == 8:
            ln = struct.unpack('>I', data[i:i + 4])[0]
            v = data[i + 4:i + 4 + ln]
            i += 4 + ln
        else:
            sz = SIZES[t]
            raw = data[i:i + sz]
            i += sz
            v = struct.unpack(UNPACK[t], raw)[0]
        if items and items[-1][0] == 'group':
            items[-1][2].append((t, v))
        else:
            items.append((t, v))
    # split each group's values into entries
    for it in items:
        if it[0] == 'group':
            vals, n = it[2], it[1]
            assert n and len(vals) % n == 0, 'group of %d values in %d entries' % (len(vals), n)
            k = len(vals) // n
            it[2] = [vals[j * k:(j + 1) * k] for j in range(n)]
    return items


def build(items, header=b'\xff\xff\x00\x00\x00\x00\x00\x00'):
    out = bytearray(header)
    for it in items:
        vals = []
        if isinstance(it, list) and it[0] == 'group':
            out += b'\x20' + struct.pack('>I', len(it[2]))
            for e in it[2]:
                vals += e
        else:
            vals = [it]
        for t, v in vals:
            out.append(t)
            if t == 8:
                out += struct.pack('>I', len(v)) + v
            else:
                out += struct.pack(UNPACK[t], v)
    return bytes(out)


def main():
    data = open(sys.argv[1], 'rb').read()
    items = parse(data)
    assert build(items, data[:8]) == data, 'round trip differs'
    for it in items:
        if isinstance(it, list):
            print('group: %d entries of %d values' % (it[1], len(it[2][0])))
            for j, e in enumerate(it[2]):
                print('%3d:' % j, ' '.join(('"%s"' % v.decode('latin1').rstrip('\0')) if t == 8 else
                                           ('%g' % v if t == 7 else str(v)) for t, v in e))
        else:
            print(it)


if __name__ == '__main__':
    main()
