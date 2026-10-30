# Notes for Claude

- **Character traits:** the first time we work on a character, ask the user for its trait (Rush,
  Shooter, Strike, Juggernaut, Normal, Technical or Barrage) if they haven't given one, and add it to
  `docs/character-traits.md` and `kirby_copy_trait()` in `fighters/kirby/kirby.c` (rebuild
  `kirby.mscsb`). Kirby's copy of that character gets the trait's changes.
- **Roll-off** (`docs/universal-mechanics.md`), **reverse tilts** and **up / down tilt, down smash
  and shield out of run** (tilts / down smash, not shield, also out of the initial dash and of
  turns out of a dash or a run) are wanted on every character;
  default roll-off speed 2.2 and air speed multiplier 1.0 (`rolloff_air_speed_mult()`) unless the
  user gives them.
- Fighter stat (`fighter_param`) names and indices: `reference/fighter_param_attributes.csv`.
- **Script names:** every script or motion slot a mod adds (game / effect / sound / expression, any
  fighter) gets its name in `tools/Sm4shCommand/SM4SHCommand/ModAnimNames.txt` (under the fighter's
  heading), so Sm4shCommand labels it; rebuild Sm4shCommand when it changes. A script that plays
  an animation from another motion folder (or shows a held model) gets a `Name -> folder/File.omo
  [+ held@Bone]` line there too, so the Hitbox Viewer plays it.
- **Ultimate ports: check the game files for full accuracy.** For every new Ultimate port (and every
  fix to one), take effects, moveset, hitboxes, parameters etc. from Ultimate's own files rather than
  eyeballing: the fighter's scripts (lua2cpp dumps), motion_list, `vl.prc` / fighter params, the effect
  files (`.eff`) and `fighter/common/param/*.prc` (e.g. `effect.prc`'s run-time effect colours), and
  the ExeFS (`exefs/main.bin`, docs/ultimate-fighter-port.md) for behaviour the data doesn't hold.
  Note in the fighter's README where each value came from, and anything still approximated.
- **Ultimate ports go through the framework** (`docs/ultimate-port-guide.md`): `tools/ultimate_port.py`
  (init / plan / run, `fighters/NAME/port.json`), stats from `tools/ultimate_stats.py`, the base's traps in
  `reference/port_bases.json`. Before sending any port package, run `tools/port_check.py NAME` over the
  install as the user will have it (the full package, then every fix package after it, in order): no ERROR
  goes out. A new bug found in game gets a check in `port_check.py` (or a default in the pipeline) and a
  row in the guide's bug catalogue, so the next port can't repeat it.
