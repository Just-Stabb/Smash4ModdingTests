#!/usr/bin/env python3
"""Xenoverse 2 race body / colour files (.bcs, "#BCS", little-endian): the part sets, their parts and colour selectors,
and the colour groups (the palettes the character creator's colour choices index). Written for Supamario's Ultra
Instinct v3 (his silver hair / eyes: the user's HUM.bcs); read-only.

Layout (read from HUM.bcs; field names as far as this file confirms them):
  header   +0x00 "#BCS", +0x0C u16 part-set slots, +0x0E u16 colour groups, +0x10 u16 bodies, +0x18 the part-set offset
           table (u32 each, 0 an empty slot), +0x1C the colour-group offset table, +0x20 the bodies, +0x28 the skeleton
  part set +0x14 u32 part count (10), +0x18 u32 the part table's offset (relative to the set): u32 each, relative to
           the set, 0 no part. The parts in order: face base, forehead, eye, nose, ear, hair, bust, pants, rist, boots
  part     0x58 bytes before its colour selectors: +0x00 u16 model, +0x02 u16 model 2, +0x04 u16 texture, +0x12 u16
           colour selector count, +0x14 u32 their offset (relative to the part), +0x34 the model's 3-letter name
           ("HUM"), +0x40.. u32 offsets of its file names (EMD / EMM / EMB / DYT; not decoded here)
  selector u16 colour group (an index of the colour-group table), u16 the colour's index in it. Confirmed on
           HUM.bcs (`selector_check`, printed by `sets`): 131 of the 135 selectors of hair / eye / face base / forehead /
           nose / ear parts name the part's own group (HAIR_ / eye_ / SKIN_); the 4 others are two skin-coloured hair
           parts (sets 37, 105: SKIN_ 17) and set 1200's forehead / hair (HAIR_ 5 / eye_ 11)
  colour group  the header's +0x1C table: a u32 offset per group slot (the header's count, 25; 0 an empty slot: HUM's
           1-3), the slot is the group's number in the selectors. A group (0x10 bytes): +0x00 u32 its name's offset, +0x0A u16 colour count, +0x0C u32 the colours' offset
           (both relative to the group); a colour is 0x50 bytes: five RGBA float colours (0x10 each). HUM's groups:
           SKIN_ (112 colours), HAIR_ (98), eye_ (98), CC00-CC03 (bust / pants / rist / boots), PAINT_A / B / C.
           HAIR_ uses colours 1-4 of the five (the main tone and the shading), eye_ colour 4.

  python3 -I tools/xv2bcs.py FILE.bcs groups                 the colour groups
  python3 -I tools/xv2bcs.py FILE.bcs colours GROUP [I...]   a group's colours (all, or these indices)
  python3 -I tools/xv2bcs.py FILE.bcs set N                  a part set's parts and colour selectors
  python3 -I tools/xv2bcs.py FILE.bcs sets                   the selector check over every part set
"""
import struct
import sys

PARTS = ['face_base', 'forehead', 'eye', 'nose', 'ear', 'hair', 'bust', 'pants', 'rist', 'boots']
PART_GROUP = {'face_base': 'SKIN_', 'forehead': 'SKIN_', 'nose': 'SKIN_', 'ear': 'SKIN_', 'hair': 'HAIR_',
              'eye': 'eye_'}


def _u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def _u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def _cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('latin1')


class Bcs:
    def __init__(self, d):
        assert d[:4] == b'#BCS', d[:4]
        self.d = d
        self.n_sets, self.n_groups, self.n_bodies = struct.unpack_from('<3H', d, 0x0C)
        self.sets_at, self.groups_at = _u32(d, 0x18), _u32(d, 0x1C)

    # ---- colour groups
    def groups(self):
        """[(name, colour count, colours' absolute offset)] per slot (('', 0, 0) an empty one)"""
        out = []
        for i in range(self.n_groups):
            g = _u32(self.d, self.groups_at + 4 * i)
            if not g:
                out.append(('', 0, 0))
                continue
            out.append((_cstr(self.d, g + _u32(self.d, g)), _u16(self.d, g + 0xA), g + _u32(self.d, g + 0xC)))
        return out

    def group_index(self, name):
        return [g[0] for g in self.groups()].index(name)

    def colour(self, group, i):
        """the five RGBA float colours of colour I of GROUP (a name or an index)"""
        gi = self.group_index(group) if isinstance(group, str) else group
        _n, count, at = self.groups()[gi]
        assert 0 <= i < count, (group, i, count)
        return [struct.unpack_from('<4f', self.d, at + 0x50 * i + 0x10 * k) for k in range(5)]

    # ---- part sets
    def part_set(self, n):
        """{part name: {'model', 'model2', 'texture', 'name', 'selectors': [(group, colour)]}} of part set N ({} empty)"""
        s = _u32(self.d, self.sets_at + 4 * n)
        if not s:
            return {}
        count, table = _u32(self.d, s + 0x14), _u32(self.d, s + 0x18)
        out = {}
        for k in range(count):
            q = _u32(self.d, s + table + 4 * k)
            if not q:
                continue
            p = s + q
            nsel, so = _u16(self.d, p + 0x12), _u32(self.d, p + 0x14)
            out[PARTS[k] if k < len(PARTS) else 'part%d' % k] = dict(
                model=_u16(self.d, p), model2=_u16(self.d, p + 2), texture=_u16(self.d, p + 4),
                name=self.d[p + 0x34:p + 0x38].split(b'\0')[0].decode('latin1'),
                selectors=[struct.unpack_from('<2H', self.d, p + so + 4 * j) for j in range(nsel)])
        return out

    def selector_check(self):
        """(checked, [mismatches]): every selector of a hair / eye / skin part names its part's colour group"""
        names = [g[0] for g in self.groups()]
        n, bad = 0, []
        for s in range(self.n_sets):
            for part, p in self.part_set(s).items():
                for g, c in p['selectors']:
                    if part in PART_GROUP:
                        n += 1
                        if g >= len(names) or names[g] != PART_GROUP[part] or c >= self.groups()[g][1]:
                            bad.append((s, part, g, c))
        return n, bad


def main():
    a = sys.argv[1:]
    b = Bcs(open(a[0], 'rb').read())
    if a[1] == 'groups':
        for i, (n, c, at) in enumerate(b.groups()):
            print('%2d %-8s %3d colours at 0x%X' % (i, n, c, at))
    elif a[1] == 'colours':
        g = int(a[2]) if a[2].isdigit() else a[2]
        count = b.groups()[g if isinstance(g, int) else b.group_index(g)][1]
        for i in [int(x) for x in a[3:]] or range(count):
            print(i, ' '.join('(%s)' % ', '.join('%.3f' % v for v in c) for c in b.colour(g, i)))
    elif a[1] == 'set':
        for part, p in b.part_set(int(a[2])).items():
            print(part, p)
    elif a[1] == 'sets':
        n, bad = b.selector_check()
        print('%d selectors on hair / eye / skin parts, %d naming another group' % (n, len(bad)), bad[:10])


if __name__ == '__main__':
    main()
