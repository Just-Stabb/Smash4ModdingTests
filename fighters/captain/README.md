# Captain Falcon (captain)

`captain.c` is decompiled from the user's `captain.mscsb`. Built files: `build/captain/`.

- **Roll-off with shield check:** see `docs/universal-mechanics.md`. MSC: `rolloff_guard_check()`
  (end of `captain.c`) in `func_370` / `func_372`. ACMD: `tools/rolloff_acmd.py` on
  `script/animcmd/body/game.bin` (`EscapeF`; `EscapeB` had no script and gets one with −2.4). `body/2/game.bin` in the upload still has the
  original roll (`Set_Edge_Slide(5)` at frame 8) and isn't edited.
- **Reverse up/down tilts:** the uploaded `captain.mscsb` didn't have them (its `func_247` /
  `func_248` were the original ones); they're copied from Kirby's.

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/captain/captain.c -o build/captain/captain.mscsb
    python3 tools/rolloff_acmd.py "<upload>/script/animcmd/body/game.bin" build/captain/game.bin --add 2.4 EscapeF EscapeB

## Latest upload (`captain_latest.c`)

The user's most recent `captain.mscsb` (decompiled as `captain_latest.c`; `captain.c` is the
older upload with my roll-off shield check). Its own changes include:
- **Holdable, rotating Falcon Punch** (SpecialN `0x152`): `func_2258` (pre: reset angle int
  `0x208000B6`/`0x208000B8`, rotation), `func_2261` (per frame: in the air between motion
  frames 42.5–45.5, special held freezes the animation and stick up/down rotates 3° per frame;
  hitboxes 0–2 get the angle via `AttackModule(0x2739, id, angle)`; release jumps to frame 46;
  rotation resets at 79), `func_2262` (end: rotation reset). Ported to Kirby's Captain Falcon
  copy (status `0x18C`, `falconpunch_hold_*` in `kirby.c`).
- **Roll-off:** the improved version (`docs/universal-mechanics.md`): roll pre `func_362`/`363`,
  `rolloff_update()` in the roll loops `func_370`/`372`, roll ends `func_381`/`382` (air speed cap
  flag), Fall main `func_501` back to the original, Fall end `func_535` clears the flag. ACMD:
  `tools/rolloff_acmd.py <upload>/body/game.bin build/captain/game.bin --hold 2.4 EscapeF EscapeB`.
- **Falcon Punch rotation swapped:** stick up now rotates up (angle −3/frame), down rotates down
  (+3); it was the other way round. That's the only change from the upload.
- The decompiler wrote four `printf` strings with real line breaks; they're `\n` again so the
  file compiles.
- Reverse forward tilt (`func_246`), stick-dependent up/down tilt variants (`func_278`/`281`),
  reverse up/down tilts (`func_247`/`248`), position tracking in `func_74`, and more.
