#!/usr/bin/env python3
"""Kirby's R.O.B. copy neutral special from R.O.B.'s own (user-edited) SpecialN / SpecialAirN.

  python3 tools/kirby_robot_laser_acmd.py ROB_BODY_DIR KIRBY_BODY_DIR OUT_DIR

ROB_BODY_DIR / KIRBY_BODY_DIR: script/animcmd/body folders (game.bin, effect.bin, expression.bin).
R.O.B.'s specialn / specialairn are written to Kirby's files as robotspecialn / robotspecialairn
(Kirby's motions 0x3A2 / 0x3A3), the rest of each file kept: game.bin (vanilla Kirby has none:
his copy ran R.O.B.'s through MotionAnimcmdModule(0, 0, 0x211, 0x1F); kirby.c's func_3419 /
func_3420 now do that for customs only), effect.bin and expression.bin (replaced). sound.bin is
left alone (R.O.B. has no SpecialN sound script; Kirby's plays his copy laser 0x7F0000).

Joints: R.O.B.'s 0x42B / 0x42C (table 1, his head) -> Kirby's 0x13 (HeadN), as vanilla Kirby's
robotspecialn effect does with R.O.B.'s 0x42B: same offsets and angles, so the laser starts at
Kirby's head (height 6.9 at frame 24) instead of R.O.B.'s (about 13), at the same angle. JUMPs to
specialn are pointed at robotspecialn.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

NAMES = {"specialn": "robotspecialn", "specialairn": "robotspecialairn"}
JOINTS = {0x42B: 0x13, 0x42C: 0x13}
JUMP = acmd.BY_NAME["jump"]


def adapt(cmds):
    out = []
    for c in cmds:
        c = acmd.Command(c.ident, c.params)
        syn = c.info.get("syntax", [])
        for i, p in enumerate(c.params):
            if i < len(syn) and syn[i] == "Bone" and p in JOINTS:
                c.params[i] = JOINTS[p]
        if c.ident == JUMP:
            c.params[0] = {acmd.crc(a): acmd.crc(b) for a, b in NAMES.items()}.get(c.params[0], c.params[0])
        out.append(c)
    return out


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    rob, kirby, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    for f in ("game.bin", "effect.bin", "expression.bin"):
        r = acmd.ACMDFile.load(os.path.join(rob, f))
        k = acmd.ACMDFile.load(os.path.join(kirby, f))
        for src, dst in NAMES.items():
            if acmd.crc(src) in r.scripts:
                k.scripts[acmd.crc(dst)] = adapt(r.scripts[acmd.crc(src)])
                print("%s: %s -> %s" % (f, src, dst))
        k.save(os.path.join(out, f))


if __name__ == "__main__":
    main()
