#!/usr/bin/env python3
"""Ultimate param files (.prc, 'paracobn'): read into Python values, dump as text.

  python3 tools/prc.py FILE.prc [LABELS.csv] [PATH ...]      e.g. vl.prc ParamLabels.csv param_special_n

Layout: 'paracobn', u32 hash table size, u32 reference table size, the hash table (u64 Hash40s), the
reference table, then the root value (a struct). A value is a type byte then: 1 bool, 2 s8, 3 u8,
4 s16, 5 u16, 6 s32, 7 u32, 8 f32, 9 hash40 (u32 index into the hash table), 10 string (u32 offset
into the reference table), 11 list (u32 count, then count u32 offsets from the list's type byte),
12 struct (u32 count, u32 offset into the reference table of count {u32 hash index, u32 offset from
the struct's type byte} pairs). Little endian. Labels: the community ParamLabels.csv
(github.com/ultimate-research/param-labels: 'hash,label' lines); unlabelled hashes print as hex.
"""
import struct
import sys

SCALARS = {1: '<?', 2: '<b', 3: '<B', 4: '<h', 5: '<H', 6: '<i', 7: '<I', 8: '<f'}


def load_labels(path):
    out = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        h, _, name = line.rstrip('\n').partition(',')
        if name:
            out[int(h, 16)] = name
    return out


class Prc:
    def __init__(self, data, labels=None):
        assert data[:8] == b'paracobn', 'not a prc file'
        hsize, rsize = struct.unpack_from('<II', data, 8)
        self.hashes = list(struct.unpack_from('<%dQ' % (hsize // 8), data, 0x10))
        self.ref = 0x10 + hsize
        self.data, self.labels = data, labels or {}
        self.root = self.value(self.ref + rsize)

    def name(self, h):
        return self.labels.get(h, '0x%010x' % h)

    def value(self, o):
        d = self.data
        t = d[o]
        if t in SCALARS:
            return struct.unpack_from(SCALARS[t], d, o + 1)[0]
        if t == 9:
            return ('hash40', self.name(self.hashes[struct.unpack_from('<I', d, o + 1)[0]]))
        if t == 10:
            s = self.ref + struct.unpack_from('<I', d, o + 1)[0]
            return d[s:d.index(b'\0', s)].decode()
        if t == 11:
            n = struct.unpack_from('<I', d, o + 1)[0]
            return [self.value(o + v) for v in struct.unpack_from('<%dI' % n, d, o + 5)]
        if t == 12:
            n, r = struct.unpack_from('<II', d, o + 1)
            pairs = struct.unpack_from('<%dI' % (2 * n), d, self.ref + r)
            return {self.name(self.hashes[pairs[2 * i]]): self.value(o + pairs[2 * i + 1]) for i in range(n)}
        raise ValueError('prc type %d at 0x%X' % (t, o))


def dump(v, indent=''):
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, (dict, list)):
                print('%s%s:' % (indent, k))
                dump(x, indent + '  ')
            else:
                print('%s%s = %s' % (indent, k, x))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            if isinstance(x, (dict, list)):
                print('%s[%d]:' % (indent, i))
                dump(x, indent + '  ')
            else:
                print('%s[%d] = %s' % (indent, i, x))
    else:
        print(indent + str(v))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    labels = load_labels(sys.argv[2]) if len(sys.argv) > 2 else {}
    p = Prc(open(sys.argv[1], 'rb').read(), labels)
    v = p.root
    for key in sys.argv[3:]:
        v = v[key] if isinstance(v, dict) else v[int(key)]
    dump(v)


if __name__ == '__main__':
    main()
