# Steve (`pickel`)

A port of Ultimate's Steve (the user's `pickel.zip`: model/body c00-c07, motions, params, AI, the
articles' models). New fighter kind `0x44`, character id 62, UI name `Steve` (subtitle
"Minecraft"), base Pit. Trait: **Technical** (no preference given; docs/character-traits.md,
`kirby_copy_trait()`). Roll-off: the default 2.2 / 1.0 (Pit's universal-mechanics scripts).

## v1 (`build/steve_hero_v1.zip`, with Hero)

Slot + model + animations on Pit's moves:
- executable: Sephiroth test 42's + `kind_expand.py` / `weapon_expand.py` / `base_effects_cave.py` /
  `base_customs_cave.py` for all five kinds (`kind_expand_test`, `weapon_expand_test`,
  `base_effects_test`, `base_customs_test`: 0 failed, each with the other three as `--others`).
  Pit's kind (0x18) is one whose vl load tail stores an extra vector for its own kind only
  (`TAIL_EXTRA_KINDS`): it's his equipment-ability data (`+0x2574` object `+0x380`), not glide
  params, so Steve not getting it only matters with equipment;
- data: `add_fighter.py --only pickel brave` on the newest files (UI restore's param/ui, Sephiroth
  v3's fighter_param, Incineroar v1's other params, the user's, vanilla), the user's UI for the
  base portraits; `add_fighter_customs.py`; `chara_layout.py USER_chara.lm --last 62` (with
  `--last 60` it gives the UI restore's file byte for byte); the folder from Pit with his
  universal-mechanics `game.bin` / `pit.mscsb`;
- `tools/ultimate_fighter.py` profile `pit`: Steve's body is one mesh (the face in its texture) in
  Pit's `Gamemodel`; his open / shut eyes in Pit's eye, half-blink and expression-eye slots;
  Pit's mouths, wings, bow and blades, bracelets and boots empty. `--pixel-art 512`: his 64 x 64
  skins blown up with nearest pixels (as the Minecraft stage's blocks). 30 bones, all 8 colours.
- motions: 341, 5 item ones on Wait1. Ultimate motion kinds that share an animation (his fall,
  jump_b, jump_aerial_f all play `a03jumpf`) resolve through his `motion_list.bin`
  (`motion_aliases`, `reference/ultimate_motion_kinds.txt`); Pit's glide (unused in Smash 4) plays
  the Elytra (`d02specialairhi*`).

Not yet: his tools (pickaxe, sword, axe, shovel: article models in Ultimate) and held blocks / items,
his own moves, stats, sounds, effects, portraits. Pit's bow article may show in Pit's specials.
