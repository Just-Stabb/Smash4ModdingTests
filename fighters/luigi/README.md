# Luigi (luigi)

`luigi.c` is decompiled from the user's unmodified `luigi.mscsb` (first commit: as provided; it
rebuilds and decompiles back to the same code). Built files: `build/luigi/`. Trait: **Technical**
(`docs/character-traits.md`).

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/luigi/luigi.c -o build/luigi/luigi.mscsb
    python3 tools/rolloff_acmd.py "<upload>/script/animcmd/body/game.bin" build/luigi/game.bin --plain --add EscapeF EscapeB
    python3 tools/luigi_airdodge_acmd.py build/luigi/game.bin build/luigi/game.bin

(`<upload>` = the zip's `luigi - Copy`; its top-level `body/` ACMD is vanilla Luigi's, `body/2/` is
the modded one, see below.)

## Universal mechanics (`docs/universal-mechanics.md`)

Same code as Captain Falcon's (the common function numbers match):
- **Reverse up / down tilts:** `func_247` / `func_248`.
- **Tilts / down smash out of run, RunBrake, dash and a turn out of a dash:** Run main
  `func_716` (transition terms), `run_attack_update()` in `func_715` / `func_717` / `func_722`,
  `dash_turn_attack_update()` in `func_724` / `func_726`.
- **Roll-off:** speed **2.2** (default), air multiplier **1.0**. Roll pre `func_362` / `func_363`
  (kinetic 0x6), `rolloff_update()` in `func_370` / `func_372`, roll ends `func_381` / `func_382`,
  Fall main `func_501` (`rolloff_fall_speed()`), Fall end `func_535` (clears `0x20000044`).
  Globals: `global62` shield-hold count, `global63` slid off. ACMD: `tools/rolloff_acmd.py`.

## Melee air dodge / wavedash (from the modded MSC)

The user's zip had a modded `luigi.mscsb` (Melee mechanics, by others, years ago); only its air
dodge / wavedash and momentum were wanted. Decompiling it needed a patched mscdec (its
analysis pass is exponential on this file and it rejects `try` blocks around syscalls); the
pieces below are ported from that decompile (and the bytecode where it still failed).

- **Directional dodge** (`melee_airdodge_dir()` → `melee_airdodge_xy(x, y)`, the mod's `func_819`): kinetic type `0xA`, gravity
  and brake off, all speed 0, then `melee_airdodge_speed()` (**3.1**) in the stick's direction
  (stick length ≥ 0.125; otherwise none). Flag `0x20000044` (no air speed cap) is on.
- **From the air** (`func_62`): also moves the ECB bottom 2.5 down with the stick under 0.01
  (`GroundModule(0x1A, …)`), and with the stick down right after a jump (Jump `0xB`, first 4
  frames) moves Luigi down toward the ground (attributes `0x158` / `0x159`), so the dodge lands
  at once (wavedash). Not with next status `0x46` / `0x47`.
- **EscapeAir** pre `func_365` (kinetic `0xA`, no gravity / brake), main `func_375` (flag
  `0x2100001F`), loop `func_378`: while the flag is on, 10% of the X speed (brake) and Y speed
  (gravity) off each frame; at frame 30 normal kinetics again. No interrupt check (the original
  `CancelModule` one is gone), fastfall allowed, item throw / link exits clear `0x20000044`,
  **can grab a ledge** (`func_56`), and the animation's end gives **helpless** (SpecialFall
  `0x10`) instead of Fall. Exec `func_379`: items are caught by pressing A / Z (Melee) instead of
  the first frames' window.
- **Wavedash on landing** (`wavedash_landing()` in the Landing pres `func_478` / `func_479`):
  landing from `0xB`–`0xF` with the air dodge input, no grab and the stick down: the dodge's speed
  and EscapeAir instead of the landing. Every landing also starts with no vertical speed.
- **Wavedash out of jumpsquat** (`jumpsquat_airdodge()`, first in the JumpSquat loop `func_488`):
  **buffered** (user): a shield press at any point of the jumpsquat (`global65`, reset by the
  JumpSquat main `func_487`) gives EscapeAir with the dodge's speed on the jumpsquat's last frame
  (status frame ≥ jump startup frames − 1). A held shield doesn't count, so jumping out of shield
  stays a jump. **Straight left / right** (|stick Y| < `wavedash_straight_y()` 0.25, |X| ≥
  `wavedash_straight_x()` 0.5): aimed **89° from straight down** (just under horizontal:
  `melee_airdodge_xy(±sin 89°, −cos 89°)`), a perfect wavedash, without the mod's 0.1 raise so it
  lands at once. Other directions: the stick's, as in the mod. (The mod only did it on a press
  exactly on the last frame, and only for a jumpsquat of 6+ frames: Luigi's is 5.)
- **No shield from the dodge's own press** (user: a buffered wavedash went into shield unless shield
  was let go at once, which stopped the slide): `global66` is set when a dodge starts and cleared
  when shield is released (`wavedash_shield_update()`, main loop `func_74`); while it's set, the
  shield-held check `func_50` (used by `func_49`, the only way into GuardOn `0x1B`) ignores the held
  shield in a dodge / wavedash landing (Landing `0x16` / `0x17` after EscapeAir or with
  `0x200000B5`, `wavedash_shield_blocked()`). A new press shields as usual.
- **A new walk input after a wavedash** (user: holding the stick, the walk came right away and
  stopped the slide): every dodge sets `global67` (`melee_airdodge_xy`), cleared once the stick is
  back to neutral (|X| < `wavedash_walk_reset_x()` 0.2, `wavedash_shield_update()`); while it's set,
  the ground movement check `func_52` doesn't turn (`0x6`) or walk (`0x1`)
  (`wavedash_walk_blocked()`). Dash, crouch and the rest still work.
- **Dodge / wavedash landing** (flag `0x200000B5`): normal landing lag (`func_509`, attribute
  `0x3000028`) and the dodge landing's motion rate (`func_586`), A / Z item catch while wavedashing
  (`func_511`); a helpless fall after the dodge lands the same way (SpecialFall pre `func_977`,
  end `func_988`). Cleared by Landing's end (`func_537`) and the ledge statuses (`func_141`,
  `func_147`, `func_213`).
- **Fall after the dodge** (`func_502`, `global64`): `0x20000044` off and normal kinetics; the
  double jump (`func_473`) also clears `0x20000044`. `global64` is separate from the flag so a
  roll-off's no-cap Fall isn't cut short.
- **ACMD** (`tools/luigi_airdodge_acmd.py`): EscapeAir's `Set_Kinetic_Handler(0)` at frame 19 and
  its two `Add/Subtract_Momentum(0, -0.2)` removed (the MSC handles the movement to frame 30);
  `Set_Frame_Duration(1.25)` from frame 28, as in the modded script.

## Momentum (from the modded MSC)

- **Jump** (Jump pre `func_472`): the jump's horizontal speed is the ground speed + the stick ×
  attribute `0x0D`, capped at the max jump speed (`0x0F`) (and set first to ground speed ×
  `0x0E`); with the stick back it can't go past 0.
- **Roll → item throw** (roll end `func_383`): a roll that ends in an item throw (`0x8C`) keeps
  its speed, capped at the run speed (`0x300000B`); any other roll end stops as before.

## Not ported from the modded MSC

- Its Melee ECB shift (`func_535` / `func_334` and the `body/2/` EscapeAir's float `0x5D` writes):
  it moves every aerial status.
- The ledge regrab limit (`func_187` and the ledge statuses): it stores ledge positions in
  common params (`0x02000077`…), which every fighter shares.
- 0.95 `DamageModule(0xA)` in the dodge's first frames (user: no).
- Everything else Melee: jumpsquat kinetics and grab / JC changes, ledge snap mode in jumps,
  other landings / landing lag (`0x46`), roll speed 2.0, double jump from Fall, the effect / sound
  / expression ACMD changes, etc.
