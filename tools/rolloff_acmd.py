#!/usr/bin/env python3
"""Roll-off ACMD edit: holding shield during a roll keeps the fighter from rolling off a ledge.

  python3 tools/rolloff_acmd.py IN_game.bin OUT_game.bin [script ...]   (default: EscapeF)

Roll-off (the user's change, see docs/universal-mechanics.md): the roll's ACMD sets a speed
(Add/Set_Momentum with Horizontal != 0, Captain Falcon: 2.4 at frame 5) and the original
Set_Edge_Slide(5) is removed, so the roll keeps going off a ledge. The fighter's MSC sets roll
status flag FLAG (0x21000014) on every frame the shield button is held (rolloff_guard_check).
This edit:
  - runs the speed command only if FLAG isn't set (IS_FLAG + False);
  - on every later frame until the roll's own speed reset, sets the speed back to 0 if FLAG is
    set (IS_FLAG + True + Add/Set_Momentum(0, 0, 1), the reset the roll already uses).
Without the added speed the roll moves like the original, which stops at the ledge.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

FLAG = 0x21000014
FRAME = acmd.BY_NAME["frame"]
WAIT = acmd.BY_NAME["wait"]
MOM = acmd.BY_NAME["add/set_momentum"]
IS_FLAG = acmd.BY_NAME["is_flag"]
TRUE = acmd.BY_NAME["true"]
FALSE = acmd.BY_NAME["false"]


def timeline(script):
    """[(frame, command)] with FRAME/WAIT turned into absolute frames."""
    t, out = 0.0, []
    for c in script:
        if c.ident == FRAME:
            t = float(c.params[0])
        elif c.ident == WAIT:
            t += float(c.params[0])
        elif c.name != "Script_End":
            out.append((t, c))
    return out


def edit(script):
    tl = timeline(script)
    if any(c.ident == IS_FLAG and c.params[0] == FLAG for _, c in tl):
        raise SystemExit("already edited")
    adds = [(f, c) for f, c in tl if c.ident == MOM and float(c.params[0]) != 0]
    if not adds:
        raise SystemExit("no roll speed (Add/Set_Momentum) in this script")
    f_add = adds[0][0]
    resets = [f for f, c in tl if c.ident == MOM and float(c.params[0]) == 0 and f > f_add]
    f_end = resets[0] if resets else max(f for f, _ in tl)
    zero = acmd.Command(MOM, [0.0, 0.0, 1])
    events = {}
    for f, c in tl:
        if c is adds[0][1]:
            events.setdefault(f, []).extend([acmd.Command(IS_FLAG, [FLAG]),
                                             acmd.Command(FALSE, [2 + c.info["size"]]), c])
        else:
            events.setdefault(f, []).append(c)
    f = f_add + 1
    while f < f_end:
        events.setdefault(f, []).extend([acmd.Command(IS_FLAG, [FLAG]),
                                         acmd.Command(TRUE, [2 + zero.info["size"]]), zero])
        f += 1
    out = []
    for f in sorted(events):
        if f > 0:
            out.append(acmd.Command(FRAME, [f]))
        out.extend(events[f])
    script[:] = out + [c for c in script if c.name == "Script_End"]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or ["EscapeF"]
    f = acmd.ACMDFile.load(src)
    for n in names:
        edit(f.script(int(n, 16) if n.startswith("0x") else n))
    f.save(dst)


if __name__ == "__main__":
    main()
