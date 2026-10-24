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

## v2 (`build/steve_v2.zip`): his tools and hitboxes

`tools/pickel_build.py` (scripts, cancel frames, tool visibility) then `ultimate_fighter.py model` /
`motions --extra-vis` (models with the tools, animations with their visibility):
- tools: Ultimate's `pick` / `sword` / `axe` / `shovel` article models (their iron meshes,
  `STEVE_MATERIAL`) held rigidly on `HaveR` (RHaveN) in Pit's bow / blade slots (`"<article>/<mesh>@<bone>"`
  in a profile's slot list; Ultimate links the article's root to the hand, so the mesh positions
  are the hand's frame: checked at side tilt's swing, the blade along the bone the sword hitboxes
  use). Shown per animation from the frame his game script asks for the tool (`set_int
  CRAFT_WEAPON_KIND_*`) to a removal request (`PIT_TOOL_VIS`, the face material animations): sword
  in 9 moves, pickaxe in dash attack / up smash / forward and back air, axe in up tilt / up air.
- hitboxes: `ultimate_acmd.py` with `--cond MATERIAL_KIND_IRON) --cond SITUATION_KIND_GROUND)`. His
  dump needed: `if(` without a space; the decompiler's stub tests (`if(M){ operatorbool()... }`, the
  real block in its else) taken as false; an `else` the dump hangs on an inner `if is_excute` moved
  back to the material test it belongs to (`fix_misplaced_else`). Side tilt / neutral air have no
  iron branch in the dump: wood x1.2 (the ratio where both are there: forward smash 15 / 18,
  forward air 10.5 / 12.6).
- jab = side tilt (user: as Mega Man's, he can walk during it in Ultimate; `game_attack11` isn't in
  the dump): attack11 gets attacks3's scripts and tool, fighter_param 263 = 1 / 264 = 0 (one jab, no
  rapid jab).
- article moves: down tilt's fire (9 in front, from frame 5), down smash's lava (frame 8 in front,
  frame 26 behind, mirrored), down air's anvil (falling under him from frame 12) put on his own
  top bone: estimates, the articles aren't made.

Not yet: walking during jab / up tilt (user; Ultimate's arm / upper-body layer animations), the
material system (mining / crafting), the articles themselves, his specials, effects, sounds.
