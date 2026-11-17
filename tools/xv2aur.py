#!/usr/bin/env python3
"""Xenoverse 2 aura_setting.aur reader (Supamario Time Skip v3): the auras (id, effect type -> BTL_AURA.eepk effect id) and
the character rows (CMS id, costume, aura, glare).

  python3 -I tools/xv2aur.py aura_setting.aur [CMS_ID ...]
"""
import sys, struct
d = open(sys.argv[1], 'rb').read()
h = struct.unpack_from('<12I', d, 0)
na, oa, nt, ot, nc, oc = h[2], h[3], h[4], h[5], h[6], h[7]
types = []
for i in range(nt):
    p = struct.unpack_from('<I', d, ot + 4 * i)[0]
    types.append(d[p:d.index(b'\0', p)].decode())
print('types', types)
auras = {}
for i in range(na):
    a = struct.unpack_from('<4I', d, oa + 16 * i)
    effs = [struct.unpack_from('<2I', d, a[3] + 8 * k) for k in range(a[2])] if a[2] and a[3] < len(d) else []
    auras[a[0]] = (a, effs)
    if i < 3 or a[0] in (int(x) for x in sys.argv[2:]):
        print('aura', a, [(types[t] if t < len(types) else t, eid) for t, eid in effs])
print('extra', h[8:12], [struct.unpack_from('<I', d, h[11] + 4*k)[0] for k in range(min(h[10], 12))] if h[11] else None)
want = [int(x) for x in sys.argv[2:]]
rows = [struct.unpack_from('<4I', d, oc + 16 * i) for i in range(nc)]
print('chara rows sample', rows[:4])
for r in rows:
    if r[0] in want:
        a = auras.get(r[2])
        print('chara', r, '-> aura', a[0] if a else None, [(types[t] if t < len(types) else t, eid) for t, eid in (a[1] if a else [])])
