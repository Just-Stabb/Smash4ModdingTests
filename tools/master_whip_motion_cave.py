#!/usr/bin/env python3
"""Byleth's whip (weapon kind 0x1A0, ZSS's whip copy: his article 2) gets motion slots past her 15 (exe_v46x_whipmot,
Byleth v15): the up special's own sword motions (tools/master_whip.py NEW_NAMES: Ultimate's hit bend, overtake and
length-tied pull). Prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py exe_v46w_vars_line.rpx exe_v46x_whipmot.rpx \\
      $(python3 tools/master_whip_motion_cave.py --rpx exe_v46w_vars_line.rpx)
  python3 tools/master_whip_motion_cave.py --rpx EXE --info

The motion info (docs/weapon-expansion-code.md 1.3): a weapon descriptor's +8 -> {entries, count, 0, 0, 0, 0, -90.0f,
90.0f}, an entry {zlib.crc32(.omo name without the extension, 0xFFFFFFFF) (the pack loader's key: tools/mtable.py
anim_hash), 0}; the motion index the article is given (ACMD Set_Anchored_Article_Action / its MSC's MotionModule, plus
its custom number: whip.mscsb func_40) picks the entry. 0x1A0's descriptor and motion info are
tools/weapon_expand_append.py's copies (exe_v46q, in its APPEND space: descriptor 0x04B9C680, motion info 0x04B9C438
-> 60 entries at 0x04B9C458, ZSS's 15 animations x 4 custom moves); the table is static (the handover's "built at run
time" was a hash of the wrong form). Here: a new entries table (her 60 entries copied, then 4 per new motion, each the
hash of PREFIX + its name) in the claimed region, and the motion info's +0 / +4 pointed at it. 2 words in place, both
asserted (the original copy's values, or this cave's own: idempotent), the region asserted free (zero) first.

Region (docs/native-notes.md "Whip motion table"): WM_CAVE 0x04BD6000 - 0x04BD7000 (the free gap between acmd_ext's
ts_data and var_reset_cave.py's region; the text region already reaches 0x04BE0000 in exe_v46w_vars, nothing to grow).
Tests: tools/master_whip_motion_test.py (unicorn).
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

KIND = 0x1A0                    # Byleth's whip (extra_kinds.json master "whip")
MINFO = 0x04B9C438              # its motion info (weapon_expand_append.py's copy, exe_v46q)
ENTRIES0 = 0x04B9C458           # ... its 60 entries
COUNT0 = 60
WM_CAVE, WM_LIMIT = 0x04BD6000, 0x04BD7000
PREFIX = 'FitSZerosuitWhipMain'


def anim_hash(name):
    return zlib.crc32(name.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


def new_names():
    """{slot: name} of the new motions (master_whip.NEW_NAMES), checked against its MOTION_COUNT"""
    import master_whip as MW
    assert min(MW.NEW_NAMES) == COUNT0 and MW.MOTION_COUNT == COUNT0 + 4 * len(MW.NEW_NAMES)
    assert sorted(MW.NEW_NAMES) == list(range(COUNT0, MW.MOTION_COUNT, 4))
    return dict(MW.NEW_NAMES)


def build(rpx):
    """{address: word}; asserts the words it replaces"""
    import kind_expand as K
    img = K.Image(rpx)
    names = new_names()
    count = COUNT0 + 4 * len(names)
    ents, cnt = img.w(MINFO), img.w(MINFO + 4)
    assert (ents, cnt) in ((ENTRIES0, COUNT0), (WM_CAVE, count)), \
        'motion info 0x%08X: {0x%08X, %d}, not weapon_expand_append\'s copy or this cave\'s' % (MINFO, ents, cnt)
    assert struct.unpack('>6I', img.blob(MINFO + 8, 24))[:4] == (0, 0, 0, 0)
    old = img.blob(ENTRIES0, 8 * COUNT0)
    # her 60: 15 animations x 4 (the custom moves), the first C03AttackS4S's, the last WhipReverse's
    hs = struct.unpack('>%dI' % (2 * COUNT0), old)
    assert hs[0] == anim_hash(PREFIX + 'C03AttackS4S') and hs[-2] == anim_hash(PREFIX + 'WhipReverse')
    assert all(hs[2 * i + 1] == 0 for i in range(COUNT0))
    words = list(struct.unpack('>%dI' % (2 * COUNT0), old))
    for slot in sorted(names):
        words += [anim_hash(PREFIX + names[slot]), 0] * 4
    assert WM_CAVE + 4 * len(words) <= WM_LIMIT
    if ents == ENTRIES0:
        cur = img.blob(WM_CAVE, WM_LIMIT - WM_CAVE)
        assert not any(cur), 'region 0x%08X-0x%08X not free' % (WM_CAVE, WM_LIMIT)
    out = {WM_CAVE + 4 * i: w for i, w in enumerate(words)}
    out[MINFO] = WM_CAVE
    out[MINFO + 4] = count
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True)
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    out = build(a.rpx)
    if a.info:
        names = new_names()
        print('weapon 0x%X motion info 0x%08X -> {0x%08X, %d}' % (KIND, MINFO, out[MINFO], out[MINFO + 4]))
        for slot in sorted(names):
            print('  slot %3d %-28s 0x%08X' % (slot, names[slot], anim_hash(PREFIX + names[slot])))
        return
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(out.items())))


if __name__ == '__main__':
    main()
