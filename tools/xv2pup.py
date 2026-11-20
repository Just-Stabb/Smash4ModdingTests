#!/usr/bin/env python3
"""Xenoverse 2 power-up parameters (powerup_parameter.pup, "#PUP", little-endian): the stat changes a transformation /
buff applies, by PUP id (a skill's CUS entry names one: Ultra Instinct -Sign-'s tail u16s 3, 2, 122, 30, 1, ... read as
part set 122, PUP 30, CUS aura 1). Written for Supamario's Ultra Instinct v3; read-only.

Layout (the user's file, 11720 bytes):
  header  +0x00 "#PUP", +0x04 u16 0xFFFE (endianness), +0x06 u16 0x10 (header size), +0x08 u32 entry count (77),
          +0x0C u32 0; the entries follow at 0x10
  entry   0x98 bytes: +0x00 u32 the PUP id (1 ... 2326, not contiguous), +0x04 / +0x08 / +0x0C u32 (ids or -1; +0x08 200 -
          905 on every entry: not decoded), then floats (0 unset): +0x14 1.0 on every entry, +0x18 .. +0x60 the
          multipliers / additions (+0x1C on 20 entries e.g. -0.35 / -0.5, +0x34 .. +0x60 on 28 - 39), +0x64 / +0x68
          (800, 500 / 1200 ...), +0x94 1.0. No field holds a colour or a BCS colour index: the transformed
          hair / eye colours are not in this file (XV2 keeps them in the executable's CUS aura table: bcs_hair_color /
          bcs_eyes_color per CUS aura; XV2 Patcher's CusAuraData).

  python3 -I tools/xv2pup.py FILE.pup [ID ...]     every entry (or these PUP ids): its non-zero fields
"""
import struct
import sys

ENTRY = 0x98


def entries(d):
    """{pup id: [u32 words]} (0x98 / 4 words each; floats via words_as_floats)"""
    assert d[:4] == b'#PUP', d[:4]
    n = struct.unpack_from('<I', d, 8)[0]
    assert 0x10 + ENTRY * n == len(d), (n, len(d))
    out = {}
    for i in range(n):
        w = list(struct.unpack_from('<%dI' % (ENTRY // 4), d, 0x10 + ENTRY * i))
        out[w[0]] = w
    return out


def fields(w):
    """[(offset, value)] of an entry's non-zero words: ints where small or -1, floats otherwise"""
    out = []
    for k, x in enumerate(w):
        if not x:
            continue
        if x == 0xFFFFFFFF:
            v = -1
        elif x < 0x100000:
            v = x
        else:
            v = round(struct.unpack('<f', struct.pack('<I', x))[0], 4)
        out.append((4 * k, v))
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    es = entries(open(a[0], 'rb').read())
    want = [int(x) for x in a[1:]] or sorted(es)
    for i in want:
        print(i, ' '.join('%02X:%s' % f for f in fields(es[i])) if i in es else 'none')


if __name__ == '__main__':
    main()
