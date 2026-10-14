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
