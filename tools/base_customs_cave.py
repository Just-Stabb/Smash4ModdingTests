#!/usr/bin/env python3
"""Custom special moves for new character ids (59+): they share their base's (Supamario gets Mario's).

  python3 tools/base_customs_cave.py [--kinds tools/extra_kinds.json] [--rpx build/cross_f.rpx]   (rpx_patch.py args)

The game keys the custom-move save bits by UI character id, in a bitfield with room for 51 ids:
  0x02A51368(id, slot 0-3, variant 1-3) -> 0x02A4D40C(id) * 12 + slot * 3 + variant - 1, -1 unless
              < 0x264 (612 = 51 ids x 12); 0x02A4D40C(id) = id - 1 (0 -> -1); its only caller.
              The owned / new bits (5 a move) of every set / get (0x02A513E0, 0x02A514B0, 0x02A5156C)
              go through it; the Customize menu's list (0x0301BF84 -> 0x02A514B0) shows a move only when
              its bit is set (variant 0, the default, always). Id 59 -> 58 * 12 + ... >= 0x264: never
              owned, nothing to equip ("no custom moves").
  0x02946468(db, skill id) -> linear index (skill id = (id - 1) << 4 | slot << 2 | variant), used by
              the prize code (0x0280A038 / 0x0280A77C candidate lists, 0x0287D844 / 0x0287DC58) with
              a second bitfield of the same size (0x02A52DE8 ... bounds-checked: id 59 reads 0).
Both are rewritten in place to jump (ctr) to a cave that maps a new id to its base's id first, so a
new character owns exactly what its base owns (unlocking one unlocks both). The skill ids themselves
stay the new character's (its ui_skill_db row 59, names MmenSpN__<Name>_*, icons spi_10_<Name>_*).
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm, ha  # noqa: E402
import rpx_patch  # noqa: E402

CAVE = 0x04B8A000
LIMIT = 0x04B8B000
FIRST_NEW_ID = 59
OWN_INDEX = 0x02A4D40C          # id -> id - 1 (0 -> -1); 5 words: or. r12,r3,r3 / li r3,-1 / beqlr / addi r3,r12,-1 / blr
OWN_ORIG = [0x7C6C1B79, 0x3860FFFF, 0x4D820020, 0x386CFFFF, 0x4E800020]
LINEAR = 0x02946468             # skill id -> linear index; 13 words
LINEAR_ORIG = [0x548C07BF, 0x548AF7BE, 0x548BE63E, 0x4082000C, 0x3860FFFF, 0x4E800020,
               0x398CFFFF, 0x1D4A0003, 0x558C063E, 0x1D6B000C, 0x7D8A6214, 0x7C6B6214, 0x4E800020]
CHR_TABLE, CHR_COUNT = 0x1033BE68, 0x53     # {u32 id, char *name} (kind_expand.py)
SPEC = os.path.join(HERE, 'extra_kinds.json')
RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class Img:
    def __init__(self, path):
        d, _o, _e, secs = rpx_patch.load(path)
        self.mem = [(s[3], bytes(rpx_patch.section_data(d, s))) for s in secs if s[1] == 1 and s[3] and s[5]]

    def blob(self, a, n):
        for base, data in self.mem:
            if base <= a and a + n <= base + len(data):
                return data[a - base:a - base + n]
        raise KeyError('0x%08X' % a)

    def w(self, a):
        return struct.unpack('>I', self.blob(a, 4))[0]

    def cstr(self, a):
        out = b''
        while self.blob(a + len(out), 1) != b'\0':
            out += self.blob(a + len(out), 1)
        return out.decode('latin1')


def base_ids(spec_path, img):
    """{new ui id: base ui id}; the base's id from the game's id -> UI name table (or ui.base_id)"""
    spec = json.load(open(spec_path))
    names = {}
    for i in range(1, CHR_COUNT):
        cid, p = img.w(CHR_TABLE + 8 * i), img.w(CHR_TABLE + 8 * i + 4)
        names.setdefault(img.cstr(p).lower(), cid)
    out = {}
    for r in spec['kinds']:
        ui = r.get('ui') or {}
        if ui.get('id') is None:
            continue
        b = ui.get('base_id')
        if b is None:
            b = names.get(r['base'].lower())
            assert b is not None, 'no UI id for base %s (give ui.base_id)' % r['base']
        out[int(str(ui['id']), 0)] = int(str(b), 0)
    return out


def build(spec_path=SPEC, rpx=RPX):
    img = Img(rpx)
    for i, w in enumerate(OWN_ORIG):
        assert img.w(OWN_INDEX + 4 * i) == w, 'unexpected code at 0x%08X' % (OWN_INDEX + 4 * i)
    for i, w in enumerate(LINEAR_ORIG):
        assert img.w(LINEAR + 4 * i) == w, 'unexpected code at 0x%08X' % (LINEAR + 4 * i)
    m = base_ids(spec_path, img)
    assert m and min(m) >= FIRST_NEW_ID
    n = max(m) - FIRST_NEW_ID + 1
    table = bytes(m.get(FIRST_NEW_ID + i, 0) for i in range(n))
    table += b'\0' * (-len(table) % 4)

    # map: r3 = id -> base id when it has one (r9, r10 scratch)
    def remap(tag):
        return """
        addi r9, r3, -%(first)d
        cmplwi r9, %(n)d
        bge %(tag)s
        lis r10, tbl@ha
        addi r10, r10, tbl@l
        add r9, r10, r9
        lbz r9, 0(r9)
        cmpwi r9, 0
        beq %(tag)s
        mr r3, r9
%(tag)s:""" % dict(first=FIRST_NEW_ID, n=n, tag=tag)

    a = Asm(CAVE)
    a.asm("""
own_index:                      # 0x02A4D40C: id -> bitfield row (id - 1), 0 -> -1
        cmpwi r3, 0
        beq none
""" + remap('own_mapped') + """
        addi r3, r3, -1
        blr
none:   li r3, -1
        blr
linear:                         # 0x02946468: (db, skill id r4) -> linear index, variant 0 -> -1
        clrlwi. r12, r4, 30
        bne have
        li r3, -1
        blr
have:   rlwinm r3, r4, 28, 24, 31
        addi r3, r3, 1
""" + remap('lin_mapped') + """
        addi r11, r3, -1
        clrlwi r11, r11, 24
        rlwinm r10, r4, 30, 30, 31
        addi r12, r12, -1
        mulli r10, r10, 3
        clrlwi r12, r12, 24
        mulli r11, r11, 12
        add r12, r10, r12
        add r3, r11, r12
        blr
tbl:
""")
    for i in range(0, len(table), 4):
        a.asm('.word 0x%08X' % struct.unpack('>I', table[i:i + 4])[0])
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT

    def jump(to):
        j = Asm(0)
        j.asm('lis r12, 0x%X\naddi r12, r12, %d\nmtctr r12\nbctr' % (ha(to), slo(to)))
        return j.words()
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}
    for site, lab in ((OWN_INDEX, 'own_index'), (LINEAR, 'linear')):
        for i, w in enumerate(jump(a.labels[lab])):
            patches[site + 4 * i] = w
    return patches, a.labels, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kinds', default=SPEC)
    ap.add_argument('--rpx', default=RPX)
    x = ap.parse_args()
    patches, labels, m = build(x.kinds, x.rpx)
    print(' '.join(['grow:0x%08X' % LIMIT] + ['0x%08X=0x%08X' % kv for kv in sorted(patches.items())]))
    sys.stderr.write('custom moves: ids %s share their base\'s (%s); cave 0x%08X-0x%08X\n'
                     % (sorted(m), ', '.join('%d -> %d' % kv for kv in sorted(m.items())), CAVE,
                        max(k for k in patches if k >= CAVE) + 4))


if __name__ == '__main__':
    main()
