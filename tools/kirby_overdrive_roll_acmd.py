#!/usr/bin/env python3
"""Kirby's Overdrive roll speed (Corrin copy, user): the rolls' roll-off speed is 2.8 in Overdrive,
2.1 otherwise. Kirby's MSC (rolloff_update in fighters/kirby/kirby.c) sets status flag 0x2100001F on
every roll frame while Overdrive is on; this makes the rolls' speed command read it:

    Add/Set_Momentum(0, 0, 1)                          // (rolloff_acmd.py --clear-first)
    IS_FLAG(0x2100001F)
    True(Offset=8){ Add/Set_Momentum(±OVERDRIVE, 0, 0) }
    Else(Offset=6){ Add/Set_Momentum(±speed, 0, 0) }    // the roll's own speed, as it was

  python3 tools/kirby_overdrive_roll_acmd.py IN_game.bin OUT_game.bin [OVERDRIVE (2.8)]

EscapeF and EscapeB (the back roll keeps its negative sign). A roll already edited is left as is.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x2100001F
MOM = acmd.BY_NAME["add/set_momentum"]
IS_FLAG = acmd.BY_NAME["is_flag"]
TRUE = acmd.BY_NAME["true"]
ELSE = acmd.BY_NAME["else"]


def edit(script, overdrive):
    if any(c.ident == IS_FLAG and c.params[0] == FLAG for c in script):
        return False
    i = next((k for k, c in enumerate(script) if c.ident == MOM and float(c.params[0]) != 0), None)
    if i is None:
        raise SystemExit("no roll speed (Add/Set_Momentum) in this script")
    own = script[i]
    speed = float(own.params[0])
    fast = acmd.Command(MOM, [overdrive if speed > 0 else -overdrive, 0.0, own.params[2]])
    size = fast.info["size"]
    script[i:i + 1] = [acmd.Command(IS_FLAG, [FLAG]),
                       acmd.Command(TRUE, [2 + size + 2]), fast,
                       acmd.Command(ELSE, [2 + size]), own]
    return True


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    overdrive = float(sys.argv[3]) if len(sys.argv) > 3 else 2.8
    f = acmd.ACMDFile.load(sys.argv[1])
    for n in ("EscapeF", "EscapeB"):
        sc = f.scripts.get(acmd.crc(n))
        if sc is None:
            raise SystemExit("%s has no script" % n)
        print("%s: %s" % (n, "Overdrive speed added" if edit(sc, overdrive) else "already has it"))
    f.save(sys.argv[2])


if __name__ == "__main__":
    main()
