#!/usr/bin/env python3
"""Luigi's Melee air dodge, ACMD part: replaces EscapeAir's game script.

  python3 tools/luigi_airdodge_acmd.py IN_game.bin OUT_game.bin

The MSC (fighters/luigi/luigi.c, melee_airdodge_dir / func_378) gives the dodge its speed and
slows it down until frame 30, then restores normal kinetics itself. The original script's
Set_Kinetic_Handler(0) at frame 19 would end the dodge's movement early and its two
Add/Subtract_Momentum(0, -0.2) would push it down, so they go. As in the modded Luigi's script,
the end of the dodge plays slower: Set_Frame_Duration(1.25) from frame 28. (The modded script
also wrote float 0x5D (3, 2, 1, 0 on frames 0-5) for its Melee ECB shift, which isn't ported.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FRAME = acmd.BY_NAME["frame"]
DURATION = acmd.BY_NAME["set_frame_duration"]
END_FRAME = 28
END_DURATION = 1.25


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = acmd.ACMDFile.load(src)
    s = f.script("escapeair")
    s[:] = [acmd.Command(FRAME, [END_FRAME]), acmd.Command(DURATION, [END_DURATION]), acmd.Command(acmd.END)]
    f.save(dst)
    print("escapeair: FRAME(%d) Set_Frame_Duration(%g)" % (END_FRAME, END_DURATION))


if __name__ == "__main__":
    main()
