# Ryu MSC

`ryu.c`: Ryu's decompiled MSC (first commit is as provided).

## Focus Attack (down B) statuses

| Status | Scripts | What it is |
|---|---|---|
| 0x155 | `func_2364`–`2371` | Charge. `func_2369` (per frame) handles the charge level and dash cancels |
| 0x161 / 0x162 | `func_2372`–`2385` | The strike (0x162 = turn-around version when holding back) |
| 0x163 / 0x164 | `func_2386`–`2391` | Focus dash forward / back (the back dash moves opposite to the facing direction) |

## Added: shield cancels into the Focus dash

Ryu could already dash-cancel Focus Attack with a dash input (forward or back
double-tap, `global45 & 0x10 / 0x20`). Pressing shield now does the same:

- `focus_shield_dash()` (end of the file) returns `0x164` (back dash) if
  shield was pressed this frame (`ControlModule(0x2710, 0x3)`) while the
  stick is held away from the facing direction (`func_88() <=`
  param `0x2000006`, the game's own "stick held back" threshold). It returns
  `0x163` (forward dash) if shield was pressed otherwise, or `0` if it
  wasn't pressed. The back dash moves backward, so Ryu dashes the way the
  stick is held.
- **During the charge (`func_2369`):** checked in the same window as the
  vanilla dash cancel (after frame `0x8000011`).
- **During the strike (`func_2377`):** like the vanilla dash cancel, it
  queues the dash once the strike has hit (`0x21000010`). `func_2378` then
  performs it within the vanilla window (`0x8000012` frames after the hit).

To allow the shield dash earlier in the charge, move the `dash =
focus_shield_dash();` check above the `if (global9 + 1.0f > WorkModuleF(0,
0x8000011))` line in `func_2369`.

## Added: command inputs only with the special button

`func_2293` (installed as `global37`) is where Ryu's command specials start,
from the command bits the game puts in `global45`:

| Bit | Command | Status |
|---|---|---|
| `0x1` | `SPECIAL_N_COMMAND` (Hadoken) | 0x157 |
| `0x2` | `SPECIAL_N2_COMMAND` (Shakunetsu) | 0x158 |
| `0x4` | `SPECIAL_S_COMMAND` (Tatsumaki) | 0x15B |
| `0x8` | `SPECIAL_HI_COMMAND` (Shoryuken) | 0x160 |

The game sets these bits whether the motion was finished with A or B. The
hook now returns early when any of them is set but Attack was pressed more
recently than Special. It compares `ControlModule(0x2722, 0x1)` (frames since
Special was pressed) with `ControlModule(0x2722, 0)` (frames since Attack was
pressed). A command finished with A then does nothing special, and the A
press goes on to the normal attack checks. Normal B specials without a
command input are unaffected.

The focus dash commands (`0x10`/`0x20`, double-tap forward/back) are stick
only and unchanged. Kirby's Ryu copy ability has its own code in `kirby.c`
and isn't affected.
