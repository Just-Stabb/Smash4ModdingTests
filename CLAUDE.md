# Notes for Claude

- **Character traits:** the first time we work on a character, ask the user for its trait (Rush,
  Shooter, Strike, Juggernaut, Normal, Technical or Barrage) if they haven't given one, and add it to
  `docs/character-traits.md` and `kirby_copy_trait()` in `fighters/kirby/kirby.c` (rebuild
  `kirby.mscsb`). Kirby's copy of that character gets the trait's changes.
- **Roll-off: Hero's (`brave`) implementation is the main universal version.** Its momentum mechanics
  are the reference for every fighter; the roll-off stats (speed, air multiplier) stay as given below.
- **Roll-off** (`docs/universal-mechanics.md`), **reverse tilts** and **up / down tilt, down smash
  and shield out of run** (tilts / down smash, not shield, also out of the initial dash and of
  turns out of a dash or a run) are wanted on every character;
  default roll-off speed 2.2 and air speed multiplier 1.0 (`rolloff_air_speed_mult()`) unless the
  user gives them.
- Fighter stat (`fighter_param`) names and indices: `reference/fighter_param_attributes.csv`.
- **Community parameter spreadsheets:** `reference/spreadsheets/` (`Sm4sh_params.xlsx`: every param file,
  the ACMD events list, hitbox field values, item / enemy ids, stages; `animcmd_item_params.xlsx`;
  `Item_Common_Param.xlsx`; CSV per sheet in `csv/`). Check them before guessing a parameter or an
  ACMD command's arguments (e.g. vanilla `Change_Hitbox_Size` resizes a live hitbox).
- **New ACMD commands are documented in Sm4shCommand.** Every new ACMD command (or new variable / flag a
  command accepts) goes under "New Commands" in Sm4shCommand's Command tab with a thorough explanation
  (what it does, every parameter and its values, what it sets or returns, gotchas) and complete, realistic
  examples: add its GROUP / HELP / EXAMPLES in `tools/acmd_ext_help.py`, regenerate Events.cfg, rebuild
  Sm4shCommand, and check every example compiles and round-trips.
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
- **Ultimate ports: the cancel windows must be Ultimate's.** Every move's cancel (IASA) frame is Ultimate's motion_list
  cancel frame: vl group 1 byte 2 (`ultimate_acmd.py` writes it; ship the vl file whenever the build writes it), and every
  status the port writes in MSC tests it in its loop (`CancelModule(0x2713)` or the frame, then `func_39` / `func_41`).
  `port_check` C1 checks both.
- **Ultimate ports: shield damage is never negative.** Ultimate gives some hitboxes negative shield damage (magic:
  Hero's spells, Sephiroth's flares); Smash 4 reads it unsigned, so a negative value breaks a shield in one hit. 0 at
  least (`ultimate_acmd.py` clamps it; anything written by hand too); `port_check` S9 is an ERROR.
- **Ultimate effect colours must match Ultimate's.** When adding an Ultimate character's effects, every effect's
  colour has to come out as Ultimate draws it: the emitters' own colours AND the colour / alpha the effect
  scripts set on the call (`LAST_EFFECT_SET_COLOR`, `EFFECT_FOLLOW_COLOR`, `..._ALPHA` etc.), including on
  effects drawn by Ultimate's own shaders (the universal path). Compare each move's colours with Ultimate's
  (fx_render, the user's clips) before sending a package.
- **Smash Run enemy ports: read the 3DS code for every enemy.** Each enemy's behaviour comes from its own 3DS
  code (enemy_fs.cro state enter / update / exit functions and helpers, code.bin for framework calls), not from the
  generated spec summaries or guesses: movement and speeds, search / turn / facing, contact damage per state (P2
  set_attack_data entries, explicit attack calls, ACMD), stomp / damage / immunity / stun, death, leave timers,
  effects. Record each reading with code addresses in `reference/smashrun_enemy_specs/hand_read.json`, flag every
  approximation, and test behaviour (not only call sequences) where the game code can be run.
