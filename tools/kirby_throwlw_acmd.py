#!/usr/bin/env python3
"""Kirby down throw (throwlw) ACMD edit: lower stomp damage during the air down throw landing loop.

  python3 tools/kirby_throwlw_acmd.py IN_game.bin OUT_game.bin

The stomp in the Set_Loop body (Special_Hitbox, 0.8 damage) becomes two conditional hitboxes:
  Kirby int 0x10000099 == 1 (landing loop running, set by throwlw_land_update in kirby.c)
      -> LOOP_DAMAGE
  Kirby int 0x10000099 == 0 -> the original hitbox
and the loop's Goto is fixed for the longer body. With 9 stomps per pass and 9 jumps back
(about 81-90 stomps), 0.27 gives about 22-24 damage for the whole loop section.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

LOOP_VAR = 0x10000099
LOOP_DAMAGE = 0.27

IVC = acmd.BY_NAME["int_var_compare"]
TRUE = acmd.BY_NAME["true"]
HITBOX = acmd.BY_NAME["special_hitbox"]
SETLOOP = acmd.BY_NAME["set_loop"]
GOTO = acmd.BY_NAME["goto"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("throwlw")
    if any(c.ident == IVC for c in s):
        sys.exit("throwlw already edited")
    i = next(i for i, c in enumerate(s) if c.ident == SETLOOP)
    h = i + 1
    assert s[h].ident == HITBOX
    g = next(j for j in range(h, len(s)) if s[j].ident == GOTO)
    orig = s[h]
    loop = acmd.Command(HITBOX, list(orig.params))
    loop.params[orig.info["syntax"].index("Damage")] = LOOP_DAMAGE
    size = orig.info["size"]
    block = [
        acmd.Command(IVC, [LOOP_VAR, 0, 1]), acmd.Command(TRUE, [2 + size]), loop,
        acmd.Command(IVC, [LOOP_VAR, 0, 0]), acmd.Command(TRUE, [2 + size]), orig,
    ]
    s[h:h + 1] = block
    g += len(block) - 1
    body = sum(c.info["size"] for c in s[h:g])
    s[g].params[0] = (-body) & 0xFFFFFFFF
    f.save(dst)


if __name__ == "__main__":
    main()
