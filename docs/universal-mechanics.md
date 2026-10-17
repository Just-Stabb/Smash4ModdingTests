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

Both rolls keep their speed off a ledge instead of stopping at it ("roll-off"). How it works
(the user's design; this implementation improves the user's first version from Captain
Falcon's `captain.mscsb`):

1. **The roll's animation doesn't move the fighter; ACMD sets the speed.** Roll pre (EscapeF
   `0x20` = common `func_362`, EscapeB `0x21` = `func_363`): `StatusModule(0x5, 0, 0x6, 0x2, …)`,
   kinetic `0x6` (the originals use `0xF`, motion movement).
2. **Constant speed from a set frame to a set frame.** ACMD (`EscapeF`, `EscapeB`):
   `Add/Set_Momentum(0, 0, 1)` at frame 0, `(SPEED, 0, 1)` on every frame from 5, `(0, 0, 1)` at
   27. The back roll gets −SPEED. Mode 1 sets the speed, so setting it every frame keeps it
   constant. The forward roll turns around (`Reverse_Direction`, frame 20 / 21); the speed is only
   set up to that frame and the last setting carries on to 27.
   `tools/rolloff_acmd.py IN OUT --hold SPEED EscapeF EscapeB` (Captain Falcon 2.4, Kirby 2.1).
3. **Sliding off from the speed frame.** Every roll frame (`rolloff_update()`, first in the roll
   loops `func_370` / `func_372`): before `rolloff_start_frame()` (5, = the ACMD's speed frame)
   ground correction `0x2` (stops at edges, like crouching / shielding), from then on `0x1` (can
   slide off, like a rebound).
4. **Shield held → no sliding off.** While the shield button is held
   (`ControlModule(0x2712, 3)`) it stays `0x2`.
5. **No air speed cap while falling from it.** Sliding off sends the roll to Fall (`func_374`).
   The roll end (key 2: `func_381` / `func_382`) sets flag `0x20000044` (lifts the max horizontal
   air speed) when the next status (`global6`) is Fall (`0xE`); Fall's end (key 2, `func_535`,
   empty before) clears it, so it lasts until the fighter leaves that Fall.

Changes from the user's first version: the back roll has a speed script and slides off too;
the speed is set every frame instead of added once; edge sliding is decided every roll frame
(it was only set in the roll's end script); the flag is cleared when Fall ends (it was cleared
at the start of Fall); the `0x208000e0` / `0x1000004` save / restore is gone (Fall main wrote the
ID `0x208000e0` itself into `0x1000004`).

Done: Captain Falcon (2.4), Kirby (2.1).
