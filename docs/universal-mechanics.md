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

## Up tilt and shield out of dash / run

Up tilt (AttackHi3 `0x29`) and shield (GuardOn `0x1B`) can be done straight out of the initial
dash (Dash `0x3`) and the run (Run `0x4`). MSC, in the common Dash / Run scripts (same function
numbers in Kirby and Captain Falcon; check `sv_set_mem(0x1, 0x1, 0x3/0x4, func_N)` per fighter):

- **Dash main** (`func_713`) and **Run main** (`func_716`): turn the up tilt transition on,
  `WorkModule(0x16, 0x1e000056);` (CONT_ATTACK_HI3), after the `0x1e000054` (dash attack) line.
- **Dash loop** (`func_715`), before the dash attack check:

```c
if (global24 & 0x4 && WorkModule(0x15, 0x1e000056)) // up tilt command
{
    func_16(0x29, 0x1);
    return;
}
```

  and the shield check (`ControlModule(0x2712, 0x3) == 0x1 && WorkModule(0x2712, 0x2100000e) == 0`)
  goes to GuardOn, `func_16(0x1b, 0x1)`, instead of a forward roll (EscapeF `0x20`, what shield
  did out of a dash before). Rolls are still done from the shield.
- **Run loop** (`func_717`): nothing to add. It already calls `func_43` (which checks the up tilt
  command with `0x1e000056`, now on) before the dash attack check, and `func_49` (shield,
  `0x1e000029`, on through the Shield group `0x1f000005` that Run main already turns on).

Up tilt is checked before dash attack, so A with the stick held up-forward (the up tilt
command's region) gives up tilt; A with the stick forward is still a dash attack. Up smash
(`0x1e00005c`) is checked before both.

Done: Kirby, Captain Falcon.

## Roll-off

Both rolls keep their speed off a ledge instead of stopping at it ("roll-off"). The user's
design, implemented on top of the user's first version from Captain Falcon's `captain.mscsb`:

1. **The roll's animation doesn't move the fighter; ACMD gives it its speed.** Roll pre (EscapeF
   `0x20` = common `func_362`, EscapeB `0x21` = `func_363`): `StatusModule(0x5, 0, 0x6, 0x2, …)`,
   kinetic `0x6` (the originals use `0xF`, motion movement).
2. **ACMD speed** (`EscapeF`, `EscapeB`): `Add/Set_Momentum(0, 0, 1)` at frame 0,
   `(SPEED, 0, 0)` at frame 5 (added once; the speed then changes however the game changes it),
   `(0, 0, 1)` at 27. The back roll gets −SPEED.
   `tools/rolloff_acmd.py IN OUT --plain --add SPEED EscapeF EscapeB` (Captain Falcon 2.4, Kirby
   2.1; a roll that already has its own speed keeps it).
3. **Sliding off from the speed frame, not while shielding.** Every roll frame
   (`rolloff_update()`, first in the roll loops `func_370` / `func_372`): before
   `rolloff_start_frame()` (5) or while the shield button is held (`ControlModule(0x2712, 3)`),
   ground correction `0x2` (stops at edges, like crouching / shielding); otherwise `0x1` (can
   slide off, like a rebound).
   **Shield lock:** once shield has been held `rolloff_lock_frames()` (10) frames in a row during
   the roll, the roll can't slide off for the rest of it, even after shield is let go. The count
   (an int global: Kirby `global72`, Captain Falcon `global62`) is reset in the roll pre scripts
   and goes back to 0 whenever shield is released before reaching 10.
4. **The speed at the edge carries over on its own.** Sliding off sends the roll to Fall
   (`func_374`), and the fighter keeps the roll's current speed into the fall with no extra code.
   (v3 also stored the speed every roll frame and gave it again in Fall's main; that doubled the
   speed on top of the carried momentum, with no air cap, and could fling fighters to the blast
   zone, so it was removed.)
   **Air speed multiplier:** `rolloff_air_speed_mult()` (default **1.0** = unchanged) scales that
   carried speed. The roll end (`func_381` / `func_382`) marks the slide-off (Kirby `global73`,
   Captain Falcon `global63`), and Fall's main (`func_501`) calls `rolloff_fall_speed()` once:
   kinetic energy 3's X speed (`KineticModuleF(0xa, 0x3)`, the speed the air speed cap applies to)
   × the multiplier, Y kept (`KineticModule(0x11, 0x3, x, y)`, the same way the game scales it, e.g.
   Kirby's `func_1072`). Only once, so the fall then slows it as usual (v3 set the speed every
   frame, which is what flung fighters).
5. **No air speed cap while falling from it.** The roll end (key 2: `func_381` / `func_382`) sets
   flag `0x20000044` (lifts the max horizontal air speed) when the next status (`global6`) is
   Fall (`0xE`); Fall's end (key 2, `func_535`) clears it.

History: v1 (mine) used an ACMD shield flag; v2 set the speed every frame (constant speed). The
user's first version cleared the air speed flag at the start of Fall and only checked shield in
the roll's end; its `0x208000e0` / `0x1000004` save / restore is gone.

**Default speed: 2.2** for any character without a specified roll-off speed (`--add` with no
number uses it). **Default air speed multiplier: 1.0** (`rolloff_air_speed_mult()`). The user confirmed the current version (v3 minus the Fall speed boost) is
right as-is.

Done: Captain Falcon (2.4, air ×1.0), Kirby (2.1, air ×1.0).
