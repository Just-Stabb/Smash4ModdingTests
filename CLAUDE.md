# Notes for Claude

- **Character traits:** the first time we work on a character, ask the user for its trait (Rush,
  Zoning, Strike, Juggernaut, Normal or Technical) if they haven't given one, and add it to
  `docs/character-traits.md` and `kirby_copy_trait()` in `fighters/kirby/kirby.c` (rebuild
  `kirby.mscsb`). Kirby's copy of that character gets the trait's changes.
- **Roll-off** (`docs/universal-mechanics.md`) and **reverse tilts** are wanted on every character;
  default roll-off speed 2.2 unless the user gives one.
- Fighter stat (`fighter_param`) names and indices: `reference/fighter_param_attributes.csv`.
