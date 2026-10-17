#!/usr/bin/env python3
"""Kirby forward air ACMD edit: the first hit gets the second hit's autolink.

  python3 tools/kirby_fair_autolink_acmd.py IN_game.bin OUT_game.bin

AttackAirF (motion 0x69) has three hits: frame 10 (two Extended_Hitbox, angles 45 / 80, KBG 50,
BKB 35), frame 17 (autolink angle 366, KBG 30, BKB 28) and frame 25 (the 361 finisher). Every
hitbox of the first hit gets the second hit's Angle, KBG, WBKB and BKB (damage, size and
position stay).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

EXT = acmd.BY_NAME["extended_hitbox"]
HIT = acmd.BY_NAME["hitbox"]
REMOVE = acmd.BY_NAME["remove_all_hitboxes"]
COPY = ("Angle", "KBG", "WBKB", "BKB")


def groups(script):
    out, cur = [], []
    for c in script:
        if c.ident in (EXT, HIT):
            cur.append(c)
        elif c.ident == REMOVE and cur:
            out.append(cur)
            cur = []
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("AttackAirF")
    g = groups(s)
    first, second = g[0], g[1]
    ref = second[0]
    syn = ref.info["syntax"]
    for c in first:
        for k in COPY:
            c.params[c.info["syntax"].index(k)] = ref.params[syn.index(k)]
    f.save(dst)


if __name__ == "__main__":
    main()
