#!/usr/bin/env python3
"""Kirby air side B (SpecialAirS) ACMD edit: a reflector from 2 frames before the hitboxes until
the frame they're all removed.

  python3 tools/kirby_sideb_reflect_acmd.py IN_game.bin OUT_game.bin

Air swings (status 0x171): SpecialAirS (motion 0x2C1; the low-charge 0x2B9 JUMPs to it) has its
hitboxes from FRAME(11) to Remove_All_Hitboxes at FRAME(29); the max-charge air swing (motion
0x2C9, hash 0xFFBD29D0) from FRAME(11) to frame 13. In each this adds
  FRAME(9): REFLECTOR(...) + SHIELD_ON(3, 0, GROUP)
  Shield_Off2(3, 0, GROUP) right after the first Remove_All_Hitboxes
kirby.c (sideb_reflect_off) also turns it off when status 0x171 ends early.
Kind 3 = reflector, ID 0, group 3: what Kirby's Zelda copy (Nayru's Love) uses
(ShieldModule(0, 0x3, 0, on/off, 0x3) in kirby.c, func_2887). The box is a capsule along the
hammer's swing (the hitboxes sit at Y 4.3, Z -3.5 to 11.5 on bone 0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

SCRIPTS = ["SpecialAirS", "0xFFBD29D0"]
HIT_FRAME = 11
REFLECT_FRAME = HIT_FRAME - 2
KIND, ID, GROUP = 3, 0, 3
# ID, Bone, Size, X, Y, Z, X2, Y2, Z2, DmgMul, SpdMul, Threshold, Unknown, LifetimeMul, Type(group)
REFLECTOR = [ID, 0, 8.0, 0.0, 5.0, -3.0, 0.0, 5.0, 12.0, 1.5, 1.2, 50.0, 0, 1.0, GROUP]

FRAME = acmd.BY_NAME["frame"]
HITBOX = acmd.BY_NAME["hitbox"]
REMOVE = acmd.BY_NAME["remove_all_hitboxes"]
REFL = acmd.BY_NAME["reflector"]
ON = acmd.BY_NAME["shield_on"]
OFF = acmd.BY_NAME["shield_off2"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    for name in SCRIPTS:
        s = f.script(int(name, 16) if name.startswith("0x") else name)
        if any(c.ident == REFL for c in s):
            sys.exit("%s already has a reflector" % name)
        i = next(i for i, c in enumerate(s) if c.ident == FRAME and c.params[0] == HIT_FRAME)
        assert s[i + 1].ident == HITBOX
        s[i:i] = [acmd.Command(FRAME, [REFLECT_FRAME]), acmd.Command(REFL, REFLECTOR),
                  acmd.Command(ON, [KIND, ID, GROUP])]
        j = next(j for j, c in enumerate(s) if c.ident == REMOVE)
        s.insert(j + 1, acmd.Command(OFF, [KIND, ID, GROUP]))
    f.save(dst)


if __name__ == "__main__":
    main()
