# Incineroar (`gaogaen`)

A port of Ultimate's Incineroar (the user's `gaogaen.zip`: model/body c00-c07, the articles'
models (championbelt, monsterball, rope, rope2), motions, params, AI). New fighter kind `0x43`,
character id 61, UI name `Incineroar` (subtitle "Heel Pokémon"), base Bowser. Trait:
**Juggernaut**. Roll-off: the default 2.2 / 1.0 (Bowser's universal-mechanics scripts).

`fighters/gaogaen/port.json` (since lowmodels_v1: `ultimate_port.py init gaogaen --base koopa --kind 0x43 --ui-name
Incineroar --trait juggernaut`; the texture-id block was already registered, nothing else regenerated). Its
`model.max_bones` is 143, v1's count (below); its effects lists are init's, not used by any build yet.

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
`reference/port_bases.json` `_texture_ids`): body c00-c07 (he had no low models: port_check M6; lowmodels_v1 below). Only the ids changed (pixels and every other byte the same:
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

## Low models v1 (`$S/lowmodels_v1.zip`, with Hero's and Sephiroth's): l00-l07, Ultimate's LOD

He had no `model/body/l00`-`l07` at all (port_check M6 ERROR: the off-screen magnifier and 8-player Smash draw them;
Squirtle was invisible in the magnifier without them). Every Ultimate costume of his has a low model (`lod.xmb`:
`gaogaen_fur_low` for `gaogaen_fur_high`, `gaogaen_belt_low` for `gaogaen_belt_high`); l00-l07 are that model
(40871 triangles for 43789):
- **his c00-c07 rebuilt** from Ultimate's files with today's converter (v1's shipped models aren't on disk): `run
  gaogaen model-c00 ... model-c07 motions` (motions: the face / eyelid packs) then `low-models gaogaen --own-ids`.
  Bowser's koopa profile, no table-1 joints (as v1), `--max-bones 143` (v1's count: today's converter keeps 147
  unlimited and folds Bowser's horn stand-ins HornBRa / HornFL / HornFR / HornR to reach 143). v1's own skeleton
  can't be compared; lNN carries its own skeleton / joint table, so it is consistent in itself, and the motions bind
  by bone hash (the same names);
- **textures under ids of their own** (0x40C32000 + 0x400 x NN): no id shared with his installed c00-c07;
- port_check gaogaen over the rebuilt c00-c07 + lowmodels_v1: M6 gone, no model / texture error. Left: **F1
  face-hidden** on the c00 / c01 face and eyelid packs (Bowser's keys: 11 motions hide every face mesh, his shell
  moves; 82 eyelid motions show no eyelid mesh on some frames, where his open eyes ride with the body, likely
  harmless) and M6 bones (143 > 138) on every folder: v1's own profile, the same in his installed cNN, not new here.
  Renders: `scratchpad/lowmodels/render/gaogaen_c00_c05.png`.
- Vanilla Bowser has no low models (34 vanilla fighters have l00-l07, Bowser, Mario, Kirby ... none), so how the game
  picks lNN for a kind isn't by the base alone (Mario-based Squirtle / Supamario were invisible without them): with
  lNN present he shows either way.

## Results panels v1 (`$S/results_panels_v1.zip`, every added fighter; over Byleth v17)

His loser panel on the results screen was empty: `param/ui/result_param.bin` frames each fighter's loser panel by model name (`gaogaen`, the kind's folder name: the executable's kind-indexed name table) and had no entry for him, so the scene used "missing" (all 0: the camera on its target). Now an entry, from Bowser's (the base):
- framing (APPROXIMATED, no Ultimate equivalent of the file): Bowser's eye (1, 10.5, 18) / to (-2, 13.5, 0) x 1.016 = eye (1.016, 10.67, 18.291), to (-2.032, 13.718, 0) (MVP / team offsets too; team_pos_scale_factor Bowser's 1.25): his head in j02lose (15.74) over Bowser's hunched J02Lose head (15.49; Bowser's bind-pose head is 21.46). His head sits upright, 20 % farther from the camera than Bowser's forward-leaning one: he may look smaller in his panel;
- win1 - 3 (APPROXIMATED: what the scene does at that frame isn't known, vanilla's are 80 - 100 % of each motion): 122 / 108 / 125: Bowser's 132 / 100 / 145 x his j02win1-3 (130 / 131 / 130) over Bowser's (141 / 121 / 151);
- his win cameras, which no package had: Ultimate's `camera/fighter/gaogaen/c00/j02win1-3` (camera-SSBU) converted to `motion/camera/result/gaogaen/1-3/camera_motion.omo` + `.vbn` (`ultimate_camera.py convert-dir`), where the result scene loads the winner's camera; the field of view isn't in the motion (the scene's own is used) and the format is Byleth v3's, not yet confirmed in game.
Built with `tools/result_param.py port` on Byleth v17's file (it keeps every vanilla entry and Byleth's byte for byte); every added kind's entry is in the one file. `port_check` R1 / R2: 0 errors over it. Not yet seen in game.

## Size (fighter_sizes_v1)

fighter_param (`tools/ultimate_stats.py` SIZE, from Ultimate's `fighter/common/param/fighter_param.prc`; until
fighter_sizes_v1 these were Bowser's): 44 scale 0.82 -> 1.0 (Ultimate's `scale`: the model is Ultimate's skeleton 1:1, so the size
in game is this x the model), 45 shield 16 -> 10.296 (Ultimate's shield_radius x 0.88: APPROXIMATED, the median Smash 4 /
Ultimate ratio), 48 tumble hitbox 5.6 -> 3.6036 (= 45 x 0.35), 49 effect_scale 1.7 -> 1.0 and 185 freeze_size 15.3 -> 11.2 (Ultimate's
effect_scale / ice_radius). docs/ultimate-port-guide.md "Stats"; `port_check` P4.
