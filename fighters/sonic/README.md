# Sonic (sonic)

`sonic.c` is decompiled from the user's `sonic.mscsb` (the zip's `script/msc/sonic.mscsb`; the
`sonicmainmscsb/` copy is identical; first commit: as provided). mscdec can't decompile
`func_2163` (Final Smash `0x14F`, category 6): its compiled code jumps backward into dead code. It's
written by hand from the bytecode with what can actually run. The rest rebuilds and decompiles
back to the same code. Built files: `build/sonic/`. Trait: **Rush** (`docs/character-traits.md`).

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/sonic/sonic.c -o build/sonic/sonic.mscsb
    python3 tools/rolloff_acmd.py "<upload>/script/animcmd/body/game.bin" build/sonic/game.bin --plain --add EscapeF EscapeB

(`<upload>` = the zip's `sonic - Copy`; the top-level `body/game.bin` is the one used; the zip's
older `body/2/…`, `newer/`, `test/` copies all still have the original roll.)

## Universal mechanics (`docs/universal-mechanics.md`)

Same code as Luigi's (the common function numbers match):
- **Reverse up / down tilts:** `func_247` / `func_248`.
- **Tilts / down smash out of run, RunBrake, dash and a turn out of a dash:** Run main
  `func_716`, `run_attack_update()` in `func_715` / `func_717` / `func_722`,
  `dash_turn_attack_update()` in `func_724` / `func_726`.
- **Roll-off:** speed **2.2**, air multiplier **1.0** (defaults: no Sonic values given). Roll pre
  `func_362` / `func_363` (kinetic 0x6), `rolloff_update()` in `func_370` / `func_372`, roll ends
  `func_381` / `func_382`, Fall main `func_501`, Fall end `func_535`. **Momentum into the next
  action** (user): after a slide-off, `global64` keeps `0x20000044` (no air speed cap) on past
  Fall's end until Sonic is on the ground / a ledge (`rolloff_momentum_update()`, main loop
  `func_74`). Globals: `global62` shield-hold count, `global63` slid off, `global64` momentum.
  ACMD: `tools/rolloff_acmd.py --plain --add` (EscapeF loses its `Set_Edge_Slide(5)`; EscapeB is
  created).
