# Captain Falcon (captain)

`captain.c` is decompiled from the user's `captain.mscsb`. Built files: `build/captain/`.

- **Roll-off with shield check:** see `docs/universal-mechanics.md`. MSC: `rolloff_guard_check()`
  (end of `captain.c`) in `func_370` / `func_372`. ACMD: `tools/rolloff_acmd.py` on
  `script/animcmd/body/game.bin` (`EscapeF`). `body/2/game.bin` in the upload still has the
  original roll (`Set_Edge_Slide(5)` at frame 8) and isn't edited.
- **Reverse up/down tilts:** the uploaded `captain.mscsb` didn't have them (its `func_247` /
  `func_248` were the original ones); they're copied from Kirby's.

Build:

    python3 tools/msclang/msclang.py -x tools/mscinfo.xml fighters/captain/captain.c -o build/captain/captain.mscsb
    python3 tools/rolloff_acmd.py "<upload>/script/animcmd/body/game.bin" build/captain/game.bin
