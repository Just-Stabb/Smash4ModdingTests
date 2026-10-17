#!/usr/bin/env python3
"""Kirby rapid jab ACMD edit: air versions of the finisher (65% knockback) and the loop hit (60% damage).

  python3 tools/kirby_rapid_air_acmd.py IN_game.bin OUT_game.bin

Neutral air plays rapid jab's motions (kirby.c, nair_rapid_*), so the finisher attack100end
(motion 0x55) runs the same script on the ground and in the air. Each of its hitboxes becomes

  IS_FLAG(0x21000024) True(..)  <hitbox, KBG / BKB / WBKB x 0.65>
  IS_FLAG(0x21000024) False(..) <original hitbox>

The loop hit subroutine 0xDCD907DA (called by attack100 every 4 frames) gets the same branch,
with Damage x 0.6 for the air version. Each script is edited only once (a script that already
has the branch is left alone), so the tool can run again on an edited game.bin.

Neutral air sets status flag 0x21000024 (nair_rapid_air_flag() in kirby.c) when it starts
(loop) and before it plays the finisher; Attack100 never sets it. Knockback is linear in KBG and BKB, so scaling both
gives 65% of the grounded knockback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x21000024
SCALE = 0.65        # finisher knockback (KBG / BKB / WBKB)
LOOP_HIT = 0xDCD907DA
LOOP_DAMAGE = 0.6   # loop hit damage
HIT = acmd.BY_NAME["hitbox"]
IS_FLAG = acmd.BY_NAME["is_flag"]
TRUE = acmd.BY_NAME["true"]
FALSE = acmd.BY_NAME["false"]


def branch(s, scale):
    """Each hitbox -> IS_FLAG True <scaled copy> / IS_FLAG False <original>."""
    if any(c.ident == IS_FLAG for c in s):
        return
    out = []
    for c in s:
        if c.ident != HIT:
            out.append(c)
            continue
        air = acmd.Command(HIT, list(c.params))
        syn = c.info["syntax"]
        for k, mul, rnd in scale:
            i = syn.index(k)
            air.params[i] = int(round(c.params[i] * mul)) if rnd else round(c.params[i] * mul, 3)
        n = 2 + c.info["size"]
        out += [acmd.Command(IS_FLAG, [FLAG]), acmd.Command(TRUE, [n]), air,
                acmd.Command(IS_FLAG, [FLAG]), acmd.Command(FALSE, [n]), c]
    s[:] = out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    branch(f.script("attack100end"), [(k, SCALE, True) for k in ("KBG", "BKB", "WBKB")])
    branch(f.script(LOOP_HIT), [("Damage", LOOP_DAMAGE, False)])
    f.save(dst)


if __name__ == "__main__":
    main()
