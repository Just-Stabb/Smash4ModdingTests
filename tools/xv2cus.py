#!/usr/bin/env python3
"""Xenoverse 2 custom_skill.cus reader (Supamario Time Skip v3): each skill entry (0x5C bytes: name, ID1, ID2, race lock,
type, files flags, the path fields EAN / camera EAN / EEPK / SE ACB / VOX ACB / after-BAC / after-BCM).

  python3 -I tools/xv2cus.py custom_skill.cus [ID ...]   (entries with those IDs, or a path naming HIK / 1352)
"""
import sys, struct
d = open(sys.argv[1], 'rb').read()
h = struct.unpack_from('<16I', d, 0)
names = ['super', 'ultimate', 'evasive', 'unk', 'blast', 'awoken']
counts = dict(zip(names, h[4:10])); offs = dict(zip(names, h[10:16]))
def s_at(o):
    if not o or o >= len(d): return ''
    return d[o:d.index(b'\0', o)].decode('latin1')
SZ = 0x5C
out = []
for n in names:
    for i in range(counts[n]):
        b = offs[n] + i * SZ
        nm = d[b:b+4].rstrip(b'\0').decode('latin1')
        id1, id2 = struct.unpack_from('<HH', d, b + 8)
        race, typ, flags = struct.unpack_from('<BBH', d, b + 0xC)
        paths = [s_at(struct.unpack_from('<I', d, b + k)[0]) for k in range(0x14, 0x30, 4)]
        out.append((n, i, nm, id1, id2, race, typ, flags, paths, d[b:b+SZ]))
want = [int(x) for x in sys.argv[2:]]
for o in out:
    if o[3] in want or o[4] in want or any('1352' in p or 'HIK' in p for p in o[8]):
        print(o[:8], o[8])
        print('   raw', o[9].hex())
