#!/usr/bin/env python3
"""Kirby's Strike neutral air: an air version of jab 2 (attack12) in its ACMD.

  python3 tools/kirby_strike_nair_acmd.py IN_game.bin OUT_game.bin

With the Strike trait, neutral air plays jab 2's motion (0x51) and sets status flag FLAG
(0x21000025, strike_nair_flag() in fighters/kirby/kirby.c). attack12 becomes

  IS_FLAG(FLAG) True(..)  Set_Frame_Duration(1.6)       # frame 0: slower (x1.6 frame duration)
  FRAME(3)
  IS_FLAG(FLAG) True(..)  <air hitbox> SET_FLOAT(1.2, LASTHIT_HITSTUN_MUL)
  IS_FLAG(FLAG) False(..) <jab 2's own hitbox>
  WAIT(2) Remove_All_Hitboxes()
  FRAME(7)
  IS_FLAG(FLAG) True(..)  Set_Frame_Duration(1.4)       # frame 7: x1.4
  ... (the rest of jab 2, unchanged)

The air hitbox is jab 2's with Damage 6, Angle 43, KBG 32, BKB 60, Z 17.5 (the user's numbers; the
rest already matches). SET_FLOAT on 0x0F000052 (last fighter hit, hitstun x, tools/position_vars_cave.py)
gives every hit of the move 1.2x hitstun. Jab 2 on the ground never sets the flag, so it's
unchanged. A script that already has the flag check is left alone (the tool can run again).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x21000025
HITSTUN_MUL_VAR = 0x0F000052      # LASTHIT_HITSTUN_MUL
DURATION_START = 1.6
DURATION_FRAME7 = 1.4
AIR = {"Damage": 6.0, "Angle": 43, "KBG": 32, "BKB": 60, "Z": 17.5}
HITSTUN_MUL = 1.2

HIT = acmd.BY_NAME["extended_special_hitbox"]
IS_FLAG = acmd.BY_NAME["is_flag"]
TRUE = acmd.BY_NAME["true"]
FALSE = acmd.BY_NAME["false"]
FRAME = acmd.BY_NAME["frame"]
DURATION = acmd.BY_NAME["set_frame_duration"]
SET_FLOAT = acmd.BY_NAME["set_float"]


def size(cmds):
    return sum(c.info["size"] for c in cmds)


def when_flag(cmds, true=True):
    """IS_FLAG(FLAG) True/False(offset) + cmds; the offset skips the True/False command and cmds."""
    return [acmd.Command(IS_FLAG, [FLAG]), acmd.Command(TRUE if true else FALSE, [2 + size(cmds)])] + cmds


def edit(s):
    if any(c.ident == IS_FLAG for c in s):
        return False
    out = when_flag([acmd.Command(DURATION, [DURATION_START])])
    hit_done = False
    for c in s:
        if c.ident == HIT and not hit_done:
            air = acmd.Command(HIT, list(c.params))
            syn = c.info["syntax"]
            for k, v in AIR.items():
                air.params[syn.index(k)] = v
            out += when_flag([air, acmd.Command(SET_FLOAT, [HITSTUN_MUL, HITSTUN_MUL_VAR])])
            out += when_flag([c], true=False)
            hit_done = True
            continue
        out.append(c)
        if c.ident == FRAME and c.params[0] == 7:
            out += when_flag([acmd.Command(DURATION, [DURATION_FRAME7])])
    assert hit_done, "attack12 has no Extended_Special_Hitbox"
    s[:] = out
    return True


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    changed = edit(f.script("attack12"))
    f.save(dst)
    print("attack12:", "edited" if changed else "already edited")


if __name__ == "__main__":
    main()
