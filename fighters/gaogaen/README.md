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

## Texture-id fix v1 (`$S/fighters_texid_fix_v1.zip`, with the other new fighters)

Install over everything. User: with two new fighters in a match one drew with the other's textures (a P1 Steve, a P2
Squirtle in Steve's). Every port's model.nut used 0x40EB0000 + k in every costume and the game keys loaded textures
by id. His textures now have their own block, 0x40C30000 + 0x400 per costume (`tools/fighter_texture_ids.py`, registry
`reference/port_bases.json` `_texture_ids`): body c00-c07 (he has no low models: port_check M6). Only the ids changed (pixels and every other byte the same:
`tools/fighter_texture_ids_test.py --package`); built with `fighter_texture_ids.py fix-package` over the installed
packages; `port_check` T1 / T2.

## Ported sound ids v1 (`$S/ported_sound_ids_v1.zip`): his own sound bank ids

nus3 loads one bank an id (docs/native-notes.md "Fighter sound banks: one bank an id"); a port keeping its base's bank
ids silenced the later player with the base (or another port on those ids) in the match. Every bank of a new kind
now has its own id (`tools/sound_bank_ids.own_id`, `reference/port_sound_ids.json`), its rows keep the base's ids
and the executable (`tools/sound_alias_cave.py` v2) gives his banks those ids as aliases; nothing else changes
(soundlabeltable, scripts, MSC, sequences: the same).
- **Banks:** Bowser's vanilla banks under his names (his folder had them unchanged: tools/add_fighter.py) with
  his ids: se 46064, vc 46065, cheer 46066, Final Smash se_common 46067; aliases Bowser's 2016 / 6013 / 6091 / 2017.
  Check: Incineroar vs Bowser.
