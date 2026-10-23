# Incineroar (`gaogaen`)

A port of Ultimate's Incineroar (the user's `gaogaen.zip`: model/body c00-c07, the articles'
models (championbelt, monsterball, rope, rope2), motions, params, AI). New fighter kind `0x43`,
character id 61, UI name `Incineroar` (subtitle "Heel Pokémon"), base Bowser. Trait:
**Juggernaut**. Roll-off: the default 2.2 / 1.0 (Bowser's universal-mechanics scripts).

## v1 (`build/incineroar_v1_test.zip`)

Slot + model + animations on Bowser's moves, built on Sephiroth v1's data:
- executable: the current pack's + `kind_expand.py` (3 kinds) + base effects / customs + weapons;
  `kind_expand_test`, `weapon_expand_test`, `base_effects_test`, `base_customs_test`: 0 failed;
- data: `add_fighter.py --only gaogaen` on Sephiroth v1's param / ui, `add_fighter_customs.py
  --only gaogaen`, `chara_layout.py --last 60`; the folder from Bowser with his universal-mechanics
  `game.bin` / `koopa.mscsb`;
- `tools/ultimate_fighter.py` with the `koopa` profile (Bowser's 24 mesh slots: the open eyelids
  ride with the body, each mouth shape takes one of Bowser's faces; Bowser's tail / horn / toe
  joints -> Incineroar's tail / ears / toes): 143 bones, all 8 colours, 300 motions (3 item ones
  fall back to Wait1).

Known: Bowser's up special hides the body (his shell); no fur physics or effects.
