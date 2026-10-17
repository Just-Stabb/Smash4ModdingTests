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
- A weak windbox (ID 3, hit group Part 1 so it doesn't use up the strong hit's hit log) over
  and around Kirby on swing frames 1-10 pushes opponents forward (angle WIND_ANGLE, fixed
  knockback WIND_WBKB, rehit every 2 frames, no damage / hitstun / hitlag / effect), so an
  opponent that's too close doesn't cross over Kirby and out of the strong hit. It's removed
  (Remove_Hitbox(3)) on frame 11, right before the strong hit. Template: Bowser's windboxes.

Each step is skipped if it's already in the script, so the tool can run again on an edited
game.bin.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

HIT = acmd.BY_NAME["hitbox"]
WEAK = {"Angle": 366, "KBG": 30, "BKB": 28}
TIP = {"ID": 2, "Z": 17.0, "Size": 4.5}
SPECIAL = acmd.BY_NAME["special_hitbox"]
REMOVE_ONE = acmd.BY_NAME["remove_hitbox"]
FRAME = acmd.BY_NAME["frame"]
WIND_ANGLE = 0       # straight forward (FacingRestrict 3: always in front of Kirby)
WIND_WBKB = 20       # weak (Bowser's windboxes use 40)
WIND_START, WIND_END = 1.0, 11.0
WIND_BOX = {"Y": 8.0, "Z": 1.0, "Size": 8.0}


def windbox():
    names = acmd.INFO[SPECIAL]["syntax"]
    vals = {"ID": 3, "Part": 1, "Bone": 0, "Damage": 0.0, "Angle": WIND_ANGLE, "KBG": 100,
            "WBKB": WIND_WBKB, "BKB": 0, "Size": WIND_BOX["Size"], "X": 0.0, "Y": WIND_BOX["Y"],
            "Z": WIND_BOX["Z"], "Effect": 0, "Trip": 0, "Hitlag": 0.0, "SDI": 0.0, "Clang": 0,
            "Rebound": 0, "ShieldDamage": 0, "SFXLevel": 1, "SFXType": 0, "Ground/Air": 3,
            "Direct/Indirect": 0, "Type": 0, "HitBits": 0x3F, "Blockability": 1, "Reflectable": 0,
            "Absorbable": 0, "Rehit": 2, "IgnoreInvuln": 0, "FacingRestrict": 3, "TeamDamage": 0,
            "DisableHitlag": 1, "NoGFX": 1, "Flinchless": 1, "StretchToggle": 0}
    params = []
    unknown = [0, 0xF, 0, 0, 0]  # the "Unknown" fields, in order (as in Bowser's windboxes)
    for n in names:
        params.append(unknown.pop(0) if n == "Unknown" else vals[n])
    return acmd.Command(SPECIAL, params)


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
    for k, v in WEAK.items():  # (setting them again is harmless)
        setp(weak[0], k, v)

    swing = f.script("specials")
    hits = [c for c in swing if c.ident == HIT]
    if [getp(c, "ID") for c in hits] == [0, 1]:
        tip = copy.deepcopy(hits[0])
        for k, v in TIP.items():
            setp(tip, k, v)
        swing.insert(swing.index(hits[1]) + 1, tip)

    if not any(c.ident == SPECIAL for c in swing):
        first = next(i for i, c in enumerate(swing) if c.ident == FRAME)  # FRAME(11), the strong hit
        assert float(swing[first].params[0]) == WIND_END
        swing[first:first + 1] = [acmd.Command(FRAME, [WIND_START]), windbox(),
                                  acmd.Command(FRAME, [WIND_END]), acmd.Command(REMOVE_ONE, [3])]

    f.save(dst)


if __name__ == "__main__":
    main()
