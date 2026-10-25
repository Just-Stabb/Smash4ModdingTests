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

## Fix 9 (`build/hero_steve_fix9.zip`, with Hero's): his head, his stats

- Head: Pit's `model.jtb` table 1 (the bones Pit's own code drives: `Lwing01-04N` / `Rwing01-04N`,
  `LBitN` / `RBitN`, `WeaponLN` / `WeaponRN`, `WpnYumiLN` / `WpnYumiRN` / `WpnNagiRN`, `FaceN`) had been
  pointed at the nearest bone Steve has (wings -> BustN, Orbitars -> RotN, bow -> the Have bones,
  FaceN -> HeadN: in game his head floated off his body). `ultimate_fighter.py` now gives each a bone
  of its own (`Skeleton.add_joint_bones`: the base's name, at that bone, nothing skinned to
  it): 46 bones. Only `model.vbn` / `model.jtb` change (the motions bind by hash; the new bones have no
  tracks and stay put).
- Stats (fighter_param kind 0x44; they were Pit's): Ultimate's `fighter_param.prc`, as Sephiroth's:
```
python3 tools/fighter_param.py set fighter_param.bin OUT 68 1=0 2=0.85 3=0.85 7=0.043 8=1.45 9=0 10=0.115 11=1.45 13=0.85 \
    14=0.8 15=1.0 16=1 17=13.5 18=9 19=22.5 20=0.04 21=0.01 22=0.86 23=0.0075 24=0.07 25=1.42 27=2.272 28=6 29=12 30=12 31=10 \
    32=18 33=92 34=2
```
  2 jumps (Pit's 4), ground / short hop heights Ultimate's x0.82 / x0.9 (Sephiroth's ratios, for
  Ultimate's faster full hop), the double jump's as it is; ground friction x0.45 (Smash 4's values are
  about that share of Ultimate's: Mario, Zelda, Pit, Robin); jump squat left at Pit's.

## Fix 10 (`build/steve_fix10.zip`)

- Fix 9's bones of his own for Pit's wings / Orbitars / bow gave Pit's `pitpt1.pac` (330 layer
  animations on exactly those 15 bones) something to drive, and in game Steve didn't animate at all
  and crashed jumping. The `pit` profile's `own_joints` is now `FaceN` only (the rest stood in as
  before fix 9: 31 bones); the new bones' hashes are new ones (CRC32 of `<name>#jtb`) so no base pac
  binds them. `--own-joints all` builds the other way (the package's optional folder).
- fighter_param 268 (aerial jump type) 2 -> 1: Pit's multi-jump (his own aerial jump status 0xD, a
  motion per jump: `func_499`) off, a normal double jump (status 0xC) as Ultimate's.

## Fix 12 (`build/steve_fix12.zip`)

- Ultimate's walks / run / dash / jumps move only his root (`a01walkmiddle`: 1 of 68 tracks changes);
  his limbs swing by `a01walk`, a layer. `ultimate_fighter.py` profile `layers` (`PIT_LAYERS`,
  `add_layers`): a01walk over the walks (one cycle), run and dash (two), jumps / step jump (weight 0.6).
- Tools out of Pit's bow / blade slots (Pit's `Model_Changer` / `VIS_SET_DEFAULT` groups switch those:
  the sword showed always) into four mouth slots (`Pit_Mouth_Ouch / Talk / Down / HeavyAttack`); the
  base's own face keys for the slots we drive are dropped per motion.
- `pickel_build.py with_removal`: side tilt / jab, neutral / forward / back air never removed their
  hitboxes (the dump keeps the materials' shared `wait; clear_all` in the last nested branch only);
  added at the dump's own wait after the last hitbox (frames 7, 7, 13, 15).
- `own_joints` back to all for Pit (fresh hashes, so `pitpt1.pac` binds none: fix 10's optional).

## Fix 13 (`build/fix13_diag.zip`): double jump

Jump type 1 (fix 10) plays motion slots 0x1D / 0x1E (jump aerial front / back, Mario's table); Pit's
have no animation (his multi-jumps are 0x1F-0x21): he T-posed. `extra_kinds.json` `motions` points both
at `FitPitBodyMainA03JumpAerialF`; the shipped executable was patched with the same words (Steve's
motion table `0x04BA4520`, entries `+0xE8` / `+0xF0`).
