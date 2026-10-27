# Squirtle (`pzenigame`)

A port of Ultimate's Squirtle (the user's `pokemon-trainer-SSBU` zip, folder `pzenigame`:
model/body c00-c07, the `water` / `waterfall` article models, motion/body/c00, `vl.prc`,
`expression_vl.prc`, AI). New fighter kind `0x46`, character id 64, UI name `Squirtle` (subtitle
"Tiny Turtle Pokémon"), base Mario. Trait: **Shooter** (`docs/character-traits.md`,
`kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 (Mario's universal-mechanics scripts).
Down special (the user's call): Pokémon Change stays as an animation with no swap.

## v1 (`build/squirtle_v1.zip`)

Slot, model, animations, portraits and the 5-row character select, on Mario's moves:

- executable: Hero fix 64's plus every cave generator again (`kind_expand.py` with 6 kinds, base
  effects / customs, weapons, Kirby copy customs); `kind_expand_test`, `base_effects_test`,
  `base_customs_test`, `copy_custom_cave_test`: 0 failed; `weapon_expand_test`: the one failure Hero
  fix 64's executable has too (fighter 0x45's article-list order).
- data: `add_fighter.py --only pzenigame` on `fighters_latest`'s param / ui with Steve fix 10's
  `fighter_param.bin`; the folder from Mario with his universal-mechanics `game.bin` /
  `mario.mscsb`.
- model: `tools/ultimate_fighter.py model` with the new `mario` profile (`MARIO_SLOTS`): Mario's
  34 mesh slots. The open face rides in `FaceN`, the pupils in `Eye`, each blink / expression face
  in one of Mario's (Halfblink1-3 = Ultimate's Harfblink, Blink / Down = Down_Blink, Ouch, Talk,
  Attack, Capture, Heavyouch, Furafura, Cliff, Final = Hot_Blink...), the mouths in Mario's mouth
  slots; the hat / hair slots are empty. So Mario's `material_anime_eyelid / face.pac` keys (by mesh
  name) blink Squirtle and change his face. 43 bones, all 8 colours.
- eyes: Ultimate draws the iris (`eye_pzenigame_b_col`) over the white through the second UV set;
  `Textures.eye()` bakes it into the white. Squirtle's white UVs run V -1.85..-1.15 (the texture
  repeats), so each triangle is now drawn in its [0, 1) tile (before: no iris, blank white eyes).
- motions: `ultimate_fighter.py motions` (base Mario): 293 body motions (4 item / run-fall ones
  fall back to Wait1), entry, result, route map. Specials (`MARIO_MOTIONS`): neutral = Water Gun's
  shot, side = Withdraw's start, up = Waterfall, down = Pokémon Change's out / in, taunts = the
  right-facing ones.
- portraits: `tools/ultimate_portraits.py --ult pzenigame --ult-base mario --ui-name Squirtle --s4-base
  Mario --cross 3.71,790.8,24.6 --stock-whole` from Ultimate's UI (`ui-SSBU.zip`), framed as Mario's,
  toned as Smash 4's renders (Hero fix 75's curve). `--cross`: Mario's Ultimate face frame in his Smash 4
  chr_90 set by hand (least squares on the eyes, nose and cap emblem, residual up to 33 px): his two
  arts' poses differ too much to match (the search gave scale 1.02 at score 0.50, Squirtle off frame).
  `--stock-whole`: Squirtle's chara_4 is his upper body, turned (it fits chara_3 at 0.74 only), so
  stock_90 is chara_4 whole in Mario's head box. Name plates: no Smash 4 name has a Q; it is the O with
  a tail (`glyph_q`). Mario's `_09` / `_10` and `chr_40` files stay Mario's (Squirtle has 8 colours).
- custom-move labels and icons: `add_fighter_customs.py --only pzenigame` (Mario's).
- character select: `tools/chara_layout.py --style user5 --first 63 --last 72`: from 63 entries the
  icons shrink to 0.75 and the grid takes a 5th row in the 4 rows' height (rows of 13 / 12, centred;
  more columns up to 19, 93 entries, before they shrink again). 58-62 keep the 4-row layout.
- `fighter/kirby/script/msc/kirby.mscsb`: Kirby's copy of Squirtle gets the Shooter trait (only
  `kirby_copy_trait()` differs from Kirby copy customs v1's).

Sources: model, motions, UI art from Ultimate's files as above. Still Mario's: moves, hitboxes,
timings, params (`fighter_param_vl_pzenigame.bin` is Mario's), effects, sounds and voice.

Known / next: Mario's specials run (fireball, cape, Super Jump Punch, FLUDD) under Squirtle's
animations; his own moveset (ACMD from Ultimate's scripts, Water Gun / Withdraw / Waterfall,
Pokémon Change with no swap), params, effects and sounds come next.
