#!/usr/bin/env python3
"""Kirby with Luigi's copy uses Luigi's Melee air dodge (fighters/kirby/kirby.c, kirby_melee_dodge):
its MSC drives the dodge's movement to frame 30. Kirby's EscapeAir script ends the dodge's movement at
frame 19 (Set_Kinetic_Handler(0)); this puts that command under IS_FLAG(0x2100001F) False, the
status flag the Luigi dodge sets (EscapeAir main) and clears at frame 30, so Kirby's own dodge is
unchanged.

  python3 tools/kirby_luigi_airdodge_acmd.py IN_game.bin OUT_game.bin
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x2100001F
IS_FLAG = acmd.BY_NAME["is_flag"]
FALSE = acmd.BY_NAME["false"]
HANDLER = acmd.BY_NAME["set_kinetic_handler"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("escapeair")
    if any(c.ident == IS_FLAG for c in s):
        print("escapeair: already edited")
    else:
        out = []
        for c in s:
            if c.ident == HANDLER:
                out += [acmd.Command(IS_FLAG, [FLAG]), acmd.Command(FALSE, [2 + c.info["size"]])]
            out.append(c)
        assert len(out) > len(s), "escapeair has no Set_Kinetic_Handler"
        s[:] = out
        print("escapeair: Set_Kinetic_Handler only without flag 0x%08X" % FLAG)
    f.save(dst)


if __name__ == "__main__":
    main()
