#!/usr/bin/env python3
"""Kirby inhale ACMD edit: remove the grab boxes and the pull windbox, so the inhale neither
catches nor pulls in opponents.

  python3 tools/kirby_inhale_acmd.py IN_game.bin OUT_game.bin

Removes every Grab_Collision2 and Special_Hitbox (the 0-damage, flinchless 160-degree pull
windbox) from SpecialNStart and SpecialNLoop (the air versions JUMP to these). The search box
(items, Sonic homing interplay) and the Throw_Specifier stay.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

DROP = (acmd.BY_NAME["grab_collision2"], acmd.BY_NAME["special_hitbox"])


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    n = 0
    for name in ("SpecialNStart", "SpecialNLoop"):
        s = f.script(name)
        keep = [c for c in s if c.ident not in DROP]
        n += len(s) - len(keep)
        s[:] = keep
    if n == 0:
        sys.exit("nothing to remove (already edited?)")
    f.save(dst)


if __name__ == "__main__":
    main()
