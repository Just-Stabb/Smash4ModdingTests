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

Rolls keep their speed off a ledge instead of stopping at it ("roll-off"). Holding the shield
button changes how the roll's end sets the edge handling. This is the user's own version (from
Captain Falcon's latest `captain.mscsb`); an earlier ACMD-flag version of mine didn't work as
intended and was removed.

- **ACMD:** the forward roll (`EscapeF`) sets a speed with `Add/Set_Momentum`: `(0, 0, 1)` at
  frame 0, `(SPEED, 0, 0)` at frame 5, `(0, 0, 1)` at frame 27 (Captain Falcon 2.4, Kirby 2.1),
  and the original `Set_Edge_Slide(5)` is removed. The back roll (`EscapeB`) has no script.
  `tools/rolloff_acmd.py IN OUT --plain --add SPEED EscapeF` adds that to a roll without it.
- **MSC, roll pre** (EscapeF `0x20` = common `func_362`, EscapeB `0x21` = `func_363`):
  `WorkModule(0, 0, 0x208000e0)` first, and `StatusModule(0x5, 0, 0x6, 0x1, …)` (forward) /
  `StatusModule(0x5, 0, 0x6, 0x2, …)` (back): kinetic `0x6`, ground correction `0x1` / `0x2`
  (the originals are `0xF`, `0x2`).
- **MSC, roll end** (key 2: `func_381` forward, `func_382` back):

```c
float var0;
var0 = WorkModuleF(0x6, 0x1000004);
WorkModule(0, var0, 0x208000e0);
if (ControlModule(0x2712, 0x3) == 0x1) { GroundModule(0x2710, 0x5); } // shield held (back roll: 0x2)
if (ControlModule(0x2713, 0x3))        { GroundModule(0x2710, 0x9); } // shield not held (back roll: 0x1)
if (global6 == 0xe) { WorkModule(0x13, 0x1, 0x20000044); }           // next status Fall: lift the air speed cap
func_383();
```

- **MSC, Fall main** (`0xE` key 1, common `func_501`), first:

```c
if (global5 == 0x20 || global5 == 0x21) { WorkModule(0, 0x208000e0, 0x1000004); } // came from a roll
WorkModule(0x14, 0x20000044);
```

`global5` = previous status, `global6` = next status. `ControlModule(0x2712, b)` = button held,
`0x2713` = not held (button 3 = shield). Flag `0x20000044` lifts the max horizontal air speed.

Done: Captain Falcon (user); Kirby (ported, speed 2.1).
