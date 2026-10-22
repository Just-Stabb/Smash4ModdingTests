#!/usr/bin/env python3
"""New series marks (stage / music / trophy series symbols): Minecraft for Minecraft World.
Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py build/cross_f.rpx OUT.rpx ... $(python3 tools/series_cave.py)
  python3 tools/series_cave.py [--rpx RPX] [--add ID:NAME ...]     (default 0x2A:minecraft)

A series ("mark") is an id (ui_stage_db's value [2], ui_mark_db.bin's rows) with a name, which picks
its textures (ui/replace[/append]/mark/mark_NN/mark_NN_<name>.nut, 0x02916DE0) and its text
(Mmen_MarkN_<name>). The names come from the id -> name table at 0x1033CEE0 (204 {u32 id, char*
name} pairs: {-1, ""} then smashbros 0 ... bayonetta 0x29, etc 0x63, the Vault's categories 0x190+,
the items 0x1F4+), read only through 0x0293DD44 (lis / li r4, 0xCC / addi -> the linear search
0x0293E92C(table, count, id & 0xFFFF)), case 7 of 0x0293DDD0(type, id), which ui_mark_db's loader
(0x0293DF98 loop) calls for each row to fill its name records (0x0293E018: +0x38 array, 0xC each).
The table can't grow in place (the next one starts at 0x1033D540), so the cave holds a copy with the
new pairs appended (the strings after it) and the stub points at it with the new count; its two
relocations (at 0x0293DD4A / 0x0293DD52, target 0x1033CEE0) are moved to the dead word. The startup code still fills the old
copy's {-1, ""} name (0x1033CEE4); the copy's is "" (never matched: ids are compared as u16).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402

CAVE = 0x04B8B000
LIMIT = 0x04B8C000
TABLE = 0x1033CEE0
COUNT = 0xCC
STUB = 0x0293DD44               # mr r5, r3 / lis r3, 0x1034 / li r4, 0xCC / addi r3, r3, -0x3120 / b
RELOC_DUMMY = 0x037EE73C
RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')
DEFAULT = [(0x2A, 'minecraft')]


def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def table(rpx):
    d, _so, _se, secs = rpx_patch.load(rpx)
    cache = {}
    return [(rpx_patch.read_u32(d, secs, TABLE + 8 * i, cache), rpx_patch.read_u32(d, secs, TABLE + 8 * i + 4, cache))
            for i in range(COUNT)], d, secs, cache


def build(rpx=RPX, add=DEFAULT):
    pairs, d, secs, cache = table(rpx)
    # the original stub, as expected
    want = [0x7C651B78, 0x3C601034, 0x388000CC, 0x3863CEE0]
    got = [rpx_patch.read_u32(d, secs, STUB + 4 * i, cache) for i in range(4)]
    assert got == want, ['%08X' % w for w in got]
    ids = {i for i, _p in pairs}
    for i, _n in add:
        assert i not in ids and 0 <= i < 0x10000, hex(i)
    strings_at = CAVE + 8 * (COUNT + len(add))
    blob = b''
    names = []
    for _i, n in add:
        names.append(strings_at + len(blob))
        blob += n.encode('ascii') + b'\0'
        blob += b'\0' * (-len(blob) % 4)
    words = []
    for i, (k, p) in enumerate(pairs):
        words += [k, 0 if i == 0 else p]                  # the {-1, ""} name: filled at startup in the old copy
    for (k, _n), p in zip(add, names):
        words += [k, p]
    words += list(struct.unpack('>%dI' % (len(blob) // 4), blob))
    assert CAVE + 4 * len(words) <= LIMIT
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}
    n = COUNT + len(add)
    patches[STUB + 4] = 0x3C600000 | ha(CAVE)                         # lis r3, cave@ha
    patches[STUB + 8] = 0x38800000 | n                                # li r4, count
    patches[STUB + 12] = 0x38630000 | (lo(CAVE) & 0xFFFF)             # addi r3, r3, cave@l
    return patches, n


def args(patches):
    out = ['grow:0x%08X' % LIMIT, 'reloc:0x%08X-0x%08X=0x%08X' % (STUB + 4, STUB + 16, RELOC_DUMMY)]
    out += ['0x%08X=0x%08X' % kv for kv in sorted(patches.items())]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rpx', default=RPX)
    ap.add_argument('--add', action='append', default=[])
    a = ap.parse_args()
    add = [(int(x.split(':')[0], 0), x.split(':')[1]) for x in a.add] or DEFAULT
    patches, n = build(a.rpx, add)
    print(' '.join(args(patches)))
    sys.stderr.write('series marks: %s; table 0x%08X (%d entries), stub 0x%08X\n'
                     % (', '.join('0x%X %s' % x for x in add), CAVE, n, STUB))


if __name__ == '__main__':
    main()
