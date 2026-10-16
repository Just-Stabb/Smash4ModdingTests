# Giga Mac (littlemacg)

`littlemacg.c` is decompiled from the user's `littlemacg.mscsb` (mscdec) and rebuilt with:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/littlemacg/littlemacg.c -o build/littlemacg.mscsb

## Added: no permanent super armor, grabbable

`gigamac_update()` (end of the file, called every frame from `func_74`) is the same as Mega
Lucario's `megalucario_update()` (see `fighters/lucariom/README.md`):
- armor state none (`DamageModule(0xB, 0, 0)`), damage-based armor threshold 0
  (`DamageModule(0x11, 0)`) and knockback taken x1 (`DamageModule(0xA, 1.0)`) every frame;
- `BattleObject(0x26)` (disable Final Smash state) every frame.

Settings: `gigamac_no_armor()` and `gigamac_grabbable()` (1 = on, 0 = off). Untested in game.
