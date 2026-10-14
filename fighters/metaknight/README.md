# Meta Knight MSC

`metaknight.c`: Meta Knight's decompiled MSC (first commit is as provided).

## Mach Tornado (neutral B) statuses

| Status | Scripts | What it is |
|---|---|---|
| 0x152 | `func_2278`–`2282` | Start |
| 0x157 | `func_2283`–`2288` | Spin (`"status_SpecialNSpin_Main"`) |
| 0x158 | `func_2289`–`2292` | End (`"status_SpecialNEnd_Main"`) |

## Added: ledge grab at any point during Mach Tornado

Grabbing a ledge takes two things:

1. **The ledge-grab mode and transition must be on.** `func_100(mode)` turns
   on the ledge-grab transition group (`0x1F000009`) and sets the ledge-check
   mode (`GroundModule(0x2711, mode)`; 2 = "can snap to ledge"). The earlier
   edits already called it in 0x152 and 0x157. It's now also called in the
   0x158 main (`func_2290`), which before only set the mode.
2. **Something has to perform the catch.** `func_56` is the game's ledge-catch
   check. When Meta Knight is airborne, touching a ledge, not holding down
   (stick Y above param `0x200006C`), the CLIFF_CATCH transition
   (`0x1E00001F`) is on, and the ledge regrab timer (`0x10000003`) is 0, it
   switches to CliffCatch (`0x72`). Vanilla moves call
   `if (func_56()) return 0x1;` at the start of their per-frame loop. That's
   now added to all three Mach Tornado loops (`func_2280`, `func_2285`,
   `func_2291`).

Grounded Mach Tornado can't grab a ledge until it leaves the ground, and
holding down still prevents grabbing, as everywhere else in the game.
