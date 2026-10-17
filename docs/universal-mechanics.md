# Universal mechanics (wanted on every character)

These are the user's own mechanic changes. Every fighter should eventually get them.

## Reverse tilts

Up tilt and down tilt can be done facing the other way: if the stick is held backward
(away from where the fighter faces, |X| > 0.12) when the attack button is pressed, the fighter
turns around before the tilt. MSC, in the common status pre scripts:

- `func_247` (AttackHi3 `0x29` pre) and `func_248` (AttackLw3 `0x2A` pre), after the two
  `StatusModule` calls:

```c
if ((global48 < -0.12f && PostureModuleF(0) == 1.0f) || (global48 > 0.12f && PostureModuleF(0) == -1.0f))
{
    PostureModule(0x2710); // reverse facing direction
}
```

`global48` = stick X. The function numbers are the common ones and are the same in every
fighter checked so far (Kirby, Captain Falcon, Bowser, Meta Knight, Charizard, Greninja,
Corrin...), but check the status table (`sv_set_mem(0x1, 0, 0x29/0x2A, func_N)`) per fighter.
Forward tilt doesn't need it (back + A already turns it around).

Done: Kirby, Meta Knight, Corrin (user); Captain Falcon (copied from Kirby's).

## Roll-off

Rolls keep their speed off a ledge instead of stopping at it ("roll-off"), unless the shield
button is held at any point during the roll before the fighter slides off the edge.

- **ACMD (user's change):** the roll script (`EscapeF`) sets a speed with
  `Add/Set_Momentum` (Captain Falcon: `(0, 0, 1)` at frame 0, `(2.4, 0, 0)` at frame 5,
  `(0, 0, 1)` at frame 27) and the original `Set_Edge_Slide(State=5)` is removed. The roll
  then carries the fighter off the ledge, and the fall keeps the speed.
- **Shield held → no roll-off:** the fighter's MSC sets roll status flag `0x21000014` on every
  roll frame the shield button is held (`rolloff_guard_check()`, `ControlModule(0x2712, 3)` =
  button 3 held; `0x2713` means "not held",
  called first in the EscapeF/EscapeB loops, common `func_370` / `func_372`), and
  `tools/rolloff_acmd.py` makes the roll's ACMD skip the speed while the flag is set (and set it
  back to 0 on later frames). The roll then moves like the original one, which stops at the
  ledge.

Per fighter: the roll's own speed value and frames come from that fighter's ACMD;
`tools/rolloff_acmd.py IN OUT [scripts]` finds them itself (the first `Add/Set_Momentum` with
a horizontal speed, until the next zero-speed one).

For a roll that doesn't have its own roll-off speed yet, `--add SPEED [START END]` adds
Captain Falcon's pattern first (speed 0 at frame 0, SPEED at START (5), 0 at END (27)) and
removes any `Set_Edge_Slide`.

Both rolls get it: the back roll (`EscapeB`) usually has no script, so `--add` creates one with
the speed reversed (it moves away from the facing direction). Run it as
`--add SPEED EscapeF EscapeB`; a roll that already has its own speed (Captain Falcon's
`EscapeF`) keeps it.

Done: Captain Falcon (user's `EscapeF`, speed 2.4; `EscapeB` added with −2.4; + shield check);
Kirby (`--add 2.1 EscapeF EscapeB`, + `rolloff_guard_check()` in `kirby.c`).
