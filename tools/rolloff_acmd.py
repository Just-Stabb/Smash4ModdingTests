#!/usr/bin/env python3
"""Roll-off ACMD edit: holding shield during a roll keeps the fighter from rolling off a ledge.

  python3 tools/rolloff_acmd.py IN_game.bin OUT_game.bin [--add SPEED [START END]] [script ...]
                                                                       (default script: EscapeF)

--add gives each listed roll that doesn't have its own roll-off speed one first (like Captain
Falcon's): Add/Set_Momentum(0, 0, 1) at frame 0, (SPEED, 0, 0) at START (5), (0, 0, 1) at END
(27); EscapeB (the back roll, which moves away from the facing direction) gets -SPEED. A missing
script is created (EscapeB often has none). A Set_Edge_Slide in the script is removed (the
original roll's edge stop). Usually: --add SPEED EscapeF EscapeB. With no SPEED, --add uses
DEFAULT_SPEED (2.2), the default for any character without a specified roll-off speed.

--hold SPEED [START END] (the current roll-off, docs/universal-mechanics.md): replaces the
roll's speed commands (and any Set_Edge_Slide) with a constant speed: Add/Set_Momentum(0, 0, 1)
at frame 0, (SPEED, 0, 1) on every frame from START (5), (0, 0, 1) at END (27). Mode 1 sets the
speed (the rolls' own (0, 0, 1) stop shows that), so setting it every frame keeps it constant.
EscapeB gets -SPEED. If the roll turns around (Reverse_Direction, the forward roll at frame
20 / 21) the speed is only set up to that frame, so the turn can't flip it; the last setting
carries on to END. A missing script is created. No shield-flag checks: the fighter's MSC
handles edges (rolloff_update).

--plain (with --add): only add the speed, no shield-flag checks. That's the user's roll-off
(Captain Falcon's latest MSC does the shield part itself, in the roll end scripts; see
docs/universal-mechanics.md): e.g. --plain --add 2.1 EscapeF.

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
DEFAULT_SPEED = 2.2  # roll-off speed for a character without its own (--add with no SPEED)
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
    script[:] = out + [acmd.Command(acmd.END)]


EDGE = acmd.BY_NAME["set_edge_slide"]


def add_speed(script, speed, start, end):
    """Give the roll a roll-off speed (Captain Falcon's pattern) and drop Set_Edge_Slide."""
    tl = [(f, c) for f, c in timeline(script) if c.ident != EDGE]
    tl += [(0.0, acmd.Command(MOM, [0.0, 0.0, 1])), (float(start), acmd.Command(MOM, [speed, 0.0, 0])),
           (float(end), acmd.Command(MOM, [0.0, 0.0, 1]))]
    tl.sort(key=lambda x: x[0])
    out = []
    cur = 0.0
    for f, c in tl:
        if f != cur:
            out.append(acmd.Command(FRAME, [f]))
            cur = f
        out.append(c)
    script[:] = out + [acmd.Command(acmd.END)]


REVERSE = acmd.BY_NAME["reverse_direction"]


def hold_speed(script, speed, start=5.0, end=27.0):
    tl = [(f, c) for f, c in timeline(script) if c.ident not in (MOM, EDGE)]
    rev = [f for f, c in tl if c.ident == REVERSE and f > start]
    last = min(rev[0], end) if rev else end
    tl.append((0.0, acmd.Command(MOM, [0.0, 0.0, 1])))
    f = float(start)
    while f < last:
        tl.append((f, acmd.Command(MOM, [speed, 0.0, 1])))
        f += 1
    tl.append((float(end), acmd.Command(MOM, [0.0, 0.0, 1])))
    tl.sort(key=lambda x: x[0])
    out, cur = [], 0.0
    for fr, c in tl:
        if fr != cur:
            out.append(acmd.Command(FRAME, [fr]))
            cur = fr
        out.append(c)
    script[:] = out + [acmd.Command(acmd.END)]


def main():
    args = sys.argv[1:]
    src, dst = args[0], args[1]
    rest = args[2:]
    if rest and rest[0] == "--hold":
        rest = rest[1:]
        nums = []
        while rest and rest[0].replace(".", "", 1).isdigit():
            nums.append(float(rest.pop(0)))
        f = acmd.ACMDFile.load(src)
        for n in rest or ["EscapeF", "EscapeB"]:
            key = int(n, 16) if n.startswith("0x") else acmd.crc(n)
            sc = f.scripts.setdefault(key, [])
            sp = -nums[0] if n.lower() == "escapeb" else nums[0]
            hold_speed(sc, sp, *nums[1:])
        f.save(dst)
        return
    plain = False
    if rest and rest[0] == "--plain":
        plain = True
        rest = rest[1:]
    add = None
    if rest and rest[0] == "--add":
        nums = []
        rest = rest[1:]
        while rest and rest[0].replace(".", "", 1).isdigit():
            nums.append(float(rest.pop(0)))
        if not nums:
            nums = [DEFAULT_SPEED]
        add = (nums + [5.0, 27.0])[:3] if len(nums) == 1 else nums
    names = rest or ["EscapeF"]
    f = acmd.ACMDFile.load(src)
    for n in names:
        key = int(n, 16) if n.startswith("0x") else acmd.crc(n)
        sc = f.scripts.get(key)
        if sc is None:
            if not add:
                raise SystemExit("%s has no script (use --add)" % n)
            sc = f.scripts[key] = []
        has_speed = any(c.ident == MOM and float(c.params[0]) != 0 for _, c in timeline(sc))
        if add and not has_speed:
            speed = -add[0] if n.lower() == "escapeb" else add[0]
            add_speed(sc, speed, *add[1:])
        if not plain:
            edit(sc)
    f.save(dst)


if __name__ == "__main__":
    main()
