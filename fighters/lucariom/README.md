# Mega Lucario (lucariom)

`lucariom.c` is decompiled from the user's `lucariom.mscsb` (mscdec) and rebuilt with:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/lucariom/lucariom.c -o build/lucariom.mscsb

## Added: no permanent super armor, grabbable

The script itself has no Mega-specific armor or grab code: its module calls match a normal
fighter's (Meta Knight). So both come from outside the MSC (native code / the Final Smash state).
`megalucario_update()` (end of the file, called every frame from `func_74`):

- **Armor**: `DamageModule(0xB, 0, 0)` every frame. That's "set armor state" with W = 0, no
  armor (1 = super armor, 2 = knockback based, 3 = damage based; see
  `reference/msc-note-sheet/Complex_CMDs.csv`). It's skipped only in the smash attack statuses
  when the fighter has smash-charge armor (float `0x25` > 0), which `func_344` handles.
- **Grabs**: fighters in the Final Smash state can't be grabbed. While flag `0x20000007`
  ("Final Smash state enabled?") is on, it calls `BattleObject(0x26)` (disable Final Smash
  state, which Kirby's final uses to end it).
- Also every frame (second try, since the first left the armor): `DamageModule(0x11, 0)`
  (damage-based super armor threshold) and `DamageModule(0xA, 1.0)` (knockback taken x1).
  The first version did make Mega Lucario grabbable.
- Settings: `megalucario_no_armor()` and `megalucario_grabbable()` (1 = on, 0 = off).
- **Untested**: if the native armor isn't the armor state, the first part does nothing. If the
  flag doesn't mean what the notes say, the second part never runs. If disabling the Final
  Smash state also ends Mega Evolution, set `megalucario_grabbable()` to 0.

## Native (cross_f.rpx) test patch

The MSC resets didn't remove the armor or the grab immunity, so they come from the executable.
Test build: `build/transform_test/cross_f.rpx` = the usual build with the transform-fighter check
in the hit result builder `0x02704F44` disabled for Giga Bowser (`0x3A`), Giga Mac (`0x3C`) and
Mega Lucario (`0x3D`). Each `cmpwi r0, kind` becomes `cmpwi r0, 0x7FFF`. Wario-Man (`0x3B`) was
never in that check. See `docs/native-notes.md`.

    python3 tools/rpx_patch.py build/cave_fix_s4/cross_f.rpx build/cross_f.rpx $(python3 tools/starcopy_cave.py) 0x02704FC4=0x2C007FFF 0x02704FCC=0x2C007FFF 0x02704FD4=0x2C007FFF

(The first test only patched `0x02704FD4`, Mega Lucario.)

**Result:** the `0x02704F44` test patch didn't remove the armor or the grab immunity. Use the
normal `cross_f.rpx`. More notes are in `docs/native-notes.md` (DamageModule armor slots).

**Third try:** Mega Lucario comes from Lucario's Final Smash (the user's up-taunt code). The
Final Smash state is the likely source, so `megalucario_update()` now calls `BattleObject(0x26)`
(disable Final Smash state) every frame instead of only while flag `0x20000007` is on. Risk: it
may end the Mega Evolution early or affect its timer. If so, set `megalucario_grabbable()` to 0.

**Result of the third try:** the armor stays. Grabs weren't tested yet, so it's unknown whether
disabling the Final Smash state removed the grab immunity. The armor is native and outside what MSC can clear (see `docs/native-notes.md`,
"Armor check"). Diagnostic RPX: `build/armor_test/cross_f.rpx`.
