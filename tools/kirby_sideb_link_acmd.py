#!/usr/bin/env python3
"""Kirby ground side B ACMD edit: the weak start hit links into the strong swing.

  python3 tools/kirby_sideb_link_acmd.py IN_game.bin OUT_game.bin

specialsstart (ground SpecialS, motion 0x289) has one weak hitbox from frame 3 (5%, angle 58,
KBG 30, BKB 30). When it hits, the side-B loop goes straight to the swing, whose strong hit
(specials, motion 0x2BD/0x2B5) comes out on swing frame 11 at Z 5.5 / 11.5. The 58 degree
launch carried opponents out of the strong hit by then.

- The weak hit gets autolink angle 366 (follows Kirby's forward slide), KBG 30, BKB 28 (the
  same values as forward air's linking hit).
- The ground swing gets a third strong hitbox (ID 2, a copy of ID 0) further out at Z 17,
  size 4.5, to catch opponents that still drift a little.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

HIT = acmd.BY_NAME["hitbox"]
WEAK = {"Angle": 366, "KBG": 30, "BKB": 28}
TIP = {"ID": 2, "Z": 17.0, "Size": 4.5}


def setp(c, key, val):
    c.params[c.info["syntax"].index(key)] = val


def getp(c, key):
    return c.params[c.info["syntax"].index(key)]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)

    start = f.script("specialsstart")
    weak = [c for c in start if c.ident == HIT]
    assert len(weak) == 1, "specialsstart: expected one hitbox"
    for k, v in WEAK.items():
        setp(weak[0], k, v)

    swing = f.script("specials")
    hits = [c for c in swing if c.ident == HIT]
    assert [getp(c, "ID") for c in hits] == [0, 1], "specials: expected hitboxes 0 and 1 (already patched?)"
    tip = copy.deepcopy(hits[0])
    for k, v in TIP.items():
        setp(tip, k, v)
    swing.insert(swing.index(hits[1]) + 1, tip)

    f.save(dst)


if __name__ == "__main__":
    main()
