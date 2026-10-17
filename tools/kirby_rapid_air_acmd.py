#!/usr/bin/env python3
"""Kirby rapid jab finisher ACMD edit: 65% knockback when neutral air plays it.

  python3 tools/kirby_rapid_air_acmd.py IN_game.bin OUT_game.bin

Neutral air plays rapid jab's motions (kirby.c, nair_rapid_*), so the finisher attack100end
(motion 0x55) runs the same script on the ground and in the air. Each of its hitboxes becomes

  IS_FLAG(0x21000024) True(..)  <hitbox, KBG / BKB / WBKB x 0.65>
  IS_FLAG(0x21000024) False(..) <original hitbox>

The air finisher sets status flag 0x21000024 (nair_rapid_air_flag() in kirby.c) before it
plays the motion; Attack100 never sets it. Knockback is linear in KBG and BKB, so scaling both
gives 65% of the grounded knockback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x21000024
SCALE = 0.65
HIT = acmd.BY_NAME["hitbox"]
IS_FLAG = acmd.BY_NAME["is_flag"]
TRUE = acmd.BY_NAME["true"]
FALSE = acmd.BY_NAME["false"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("attack100end")
    if any(c.ident == IS_FLAG for c in s):
        sys.exit("attack100end already edited")
    out = []
    for c in s:
        if c.ident != HIT:
            out.append(c)
            continue
        air = acmd.Command(HIT, list(c.params))
        syn = c.info["syntax"]
        for k in ("KBG", "BKB", "WBKB"):
            i = syn.index(k)
            air.params[i] = int(round(c.params[i] * SCALE))
        n = 2 + c.info["size"]
        out += [acmd.Command(IS_FLAG, [FLAG]), acmd.Command(TRUE, [n]), air,
                acmd.Command(IS_FLAG, [FLAG]), acmd.Command(FALSE, [n]), c]
    s[:] = out
    f.save(dst)


if __name__ == "__main__":
    main()
