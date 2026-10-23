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
