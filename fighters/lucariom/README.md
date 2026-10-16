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
- Settings: `megalucario_no_armor()` and `megalucario_grabbable()` (1 = on, 0 = off).
- **Untested**: if the native armor isn't the armor state, the first part does nothing. If the
  flag doesn't mean what the notes say, the second part never runs. If disabling the Final
  Smash state also ends Mega Evolution, set `megalucario_grabbable()` to 0.
